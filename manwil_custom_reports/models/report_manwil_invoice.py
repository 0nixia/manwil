import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Modelo del parser del reporte oficial del SIAT. Se referencia por nombre
# (no por import) para no acoplar este módulo a siat_module: si el SIAT no
# está instalado, el reporte cae al modo fallback con datos de account.move.
SIAT_REPORT_MODEL = 'report.siat_module.siat_invoice_template'


class ReportManwilInvoice(models.AbstractModel):
    """Parser del reporte de Factura Boliviana (Media Carta).

    Cuando la factura tiene una Factura SIAT asociada (`siat_invoice_id`),
    construye los datos reutilizando **exactamente** la misma lógica de
    negocio del módulo SIAT (parser `report.siat_module.siat_invoice_template`
    + campos del modelo `siat.invoice`): CUF, número de factura SIAT, punto de
    venta, leyenda, QR, montos e importe base crédito fiscal.

    Si no hay SIAT (borradores, facturas previas, módulo no instalado), usa los
    datos nativos de `account.move` y marca la factura como SIN VALOR FISCAL.
    """

    _name = 'report.manwil_custom_reports.report_manwil_invoice_document'
    _description = 'Factura Boliviana (Media Carta) - Manwil'

    # ── Helpers ────────────────────────────────────────────────────────────

    def _rep_grafica_text(self, siat):
        """Leyenda de representación gráfica (en línea / fuera de línea)."""
        if siat and siat.evento_id:
            return ('"Este documento es la Representación Gráfica de un Documento '
                    'Fiscal Digital emitido en una modalidad de facturación fuera '
                    'de línea, verifique su envío con su proveedor o en la página '
                    'web www.impuestos.gob.bo"')
        return ('Este documento es la Representación Gráfica de un Documento Fiscal '
                'Digital emitido en una modalidad de facturación en línea.')

    # ── Datos desde el SIAT (lógica idéntica al módulo siat_module) ─────────

    def _info_siat(self, move):
        siat = move.siat_invoice_id
        # Reutiliza el parser oficial: amount_text, qr_buffer, razon_social,
        # sucursal, ciudad, telefono, cufd, get_unidad_medida, get_invoice_datetime.
        vals = self.env[SIAT_REPORT_MODEL].sudo()._get_report_values(move.ids)

        get_um = vals.get('get_unidad_medida')
        get_dt = vals.get('get_invoice_datetime')
        cufd = vals.get('cufd')

        items = []
        for it in siat.items:
            items.append({
                'codigo': it.product_code or '',
                'cantidad': it.quantity,
                'unidad': get_um(it.unidad_medida) if get_um else '',
                'descripcion': it.get_report_description(),
                'precio': it.price,
                'descuento': it.discount,
                'subtotal': it.total,
            })

        nit_ci_cex = siat.nit_ruc_nif or ''
        if siat.complemento:
            nit_ci_cex = '{}-{}'.format(siat.nit_ruc_nif or '', siat.complemento)

        return {
            'has_siat': True,
            # Encabezado emisor
            'razon_social': vals.get('razon_social') or move.company_id.name,
            'sucursal': vals.get('sucursal') or 'CASA MATRIZ',
            'punto_venta': siat.punto_venta,
            'address': (cufd.address if cufd else '') or move.company_id.street or '',
            'telefono': vals.get('telefono') or move.company_id.phone or '',
            'ciudad': vals.get('ciudad') or move.company_id.city or '',
            # Recuadro fiscal
            'nit_emisor': siat.nit_emisor or '',
            'invoice_number': siat.invoice_number,
            'cuf': siat.cuf or '',
            'cuf_chunked': siat.get_cuf_chunked(False) if siat.cuf else '',
            # Cliente
            'fecha': get_dt(siat.invoice_datetime) if get_dt else (siat.invoice_datetime or ''),
            'nit_ci_cex': nit_ci_cex,
            'customer_name': siat.customer_name or '',
            'cod_cliente': (siat.partner_id.company_registry or siat.partner_id.vat or '') if siat.partner_id else '',
            # Líneas
            'items': items,
            # Totales (motor de impuestos del SIAT)
            'subtotal': siat.subtotal,
            'descuento': siat.discount,
            'total': siat.total,
            'giftcard': siat.monto_giftcard,
            'payamount': siat.total - siat.monto_giftcard,
            # Pie
            'amount_text': vals.get('amount_text') or '',
            'qr': vals.get('qr_buffer'),
            'leyenda': siat.leyenda or '',
            'rep_grafica': self._rep_grafica_text(siat),
        }

    # ── Datos nativos de account.move (sin SIAT) ────────────────────────────

    def _info_fallback(self, move):
        lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')

        # Precios con impuesto incluido (misma lógica que sales_order_report):
        # el unitario sale de compute_all(...)['total_included'] y el total de
        # línea de price_total, para que las columnas y los totales cuadren
        # cuando hay IVA (price_include en Bolivia).
        items = []
        subtotal = 0.0
        descuento = 0.0
        for l in lines:
            qty = l.quantity
            pu = l.tax_ids.compute_all(
                l.price_unit, move.currency_id, 1.0, l.product_id, move.partner_id,
            )['total_included']
            line_total = l.price_total  # con impuesto, ya con descuento aplicado
            bruto = pu * qty
            desc = bruto - line_total
            items.append({
                'codigo': l.product_id.default_code or '',
                'cantidad': qty,
                'unidad': l.product_uom_id.name or '',
                'descripcion': l.name or l.product_id.display_name or '',
                'precio': pu,
                'descuento': desc,
                'subtotal': line_total,
            })
            subtotal += bruto
            descuento += desc
        try:
            amount_text = (move.currency_id.amount_to_text(move.amount_total) or '').upper()
        except Exception:
            amount_text = ''

        return {
            'has_siat': False,
            'razon_social': move.company_id.name,
            'sucursal': 'CASA MATRIZ',
            'punto_venta': move.codigo_sucursal if 'codigo_sucursal' in move._fields else 0,
            'address': move.company_id.street or '',
            'telefono': move.company_id.phone or '',
            'ciudad': move.company_id.city or 'EL ALTO',
            'nit_emisor': move.company_id.vat or '',
            'invoice_number': move.name or '',
            'cuf': '',
            'cuf_chunked': '',
            'fecha': move.invoice_date.strftime('%d/%m/%Y') if move.invoice_date else '',
            'nit_ci_cex': move.partner_id.vat or '',
            'customer_name': move.partner_id.name or '',
            'cod_cliente': move.partner_id.company_registry or move.partner_id.vat or '',
            'items': items,
            'subtotal': subtotal,
            'descuento': descuento,
            'total': move.amount_total,
            'giftcard': 0.0,
            'payamount': move.amount_total,
            'amount_text': amount_text,
            'qr': None,
            'leyenda': '',
            'rep_grafica': self._rep_grafica_text(None),
        }

    def _info(self, move):
        siat = move.siat_invoice_id if 'siat_invoice_id' in move._fields else False
        if siat and SIAT_REPORT_MODEL in self.env:
            try:
                return self._info_siat(move)
            except Exception:
                _logger.warning(
                    'manwil_custom_reports: no se pudo construir datos SIAT para '
                    'la factura %s, se usa fallback de account.move', move.id,
                    exc_info=True,
                )
        return self._info_fallback(move)

    @api.model
    def _get_report_values(self, docids, data=None):
        moves = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': moves,
            'info_map': {m.id: self._info(m) for m in moves},
        }
