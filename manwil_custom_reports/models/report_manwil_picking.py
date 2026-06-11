from odoo import api, models


class ReportManwilPicking(models.AbstractModel):
    """Parser de la Nota de Almacén (Media Carta).

    Calcula los precios de cada línea con **impuesto incluido** (misma lógica
    que el módulo `sales_order_report`): el precio unitario y los totales se
    obtienen vía `tax_id.compute_all(...)['total_included']`, de modo que las
    columnas P.U. / PRECIO / DESCTO. / TOTAL y la caja de totales cuadren
    visualmente cuando el producto lleva IVA (típicamente price_include en
    Bolivia). Sin impuestos, `compute_all` devuelve el mismo precio base.
    """

    _name = 'report.manwil_custom_reports.report_manwil_picking_document'
    _description = 'Nota de Almacén (Media Carta) - Manwil'

    def _line_prices(self, picking, move):
        """Devuelve precios con impuesto incluido para la cantidad movida.

        Usa `move.quantity` (lo realmente despachado en la nota), no la
        cantidad pedida en la venta, para que el total cuadre con lo impreso.
        """
        sline = move.sale_line_id if 'sale_line_id' in move._fields else False
        if not sline:
            return None
        qty = move.quantity
        currency = picking.company_id.currency_id
        partner = picking.partner_id
        taxes = sline.tax_id
        disc = sline.discount or 0.0
        # Precio unitario con impuesto (cantidad 1).
        pu = taxes.compute_all(
            sline.price_unit, currency, 1.0, sline.product_id, partner,
        )['total_included']
        precio = pu * qty
        # Total de línea con impuesto, ya con el descuento aplicado.
        total = taxes.compute_all(
            sline.price_unit * (1.0 - disc / 100.0), currency, qty,
            sline.product_id, partner,
        )['total_included']
        return {
            'pu': pu,
            'precio': precio,
            'descuento': precio - total,
            'total': total,
        }

    def _picking_info(self, picking):
        has_sale = 'sale_id' in picking._fields and bool(picking.sale_id)
        lines = []
        sub_total = descuento = total = 0.0
        for move in picking.move_ids_without_package:
            prices = self._line_prices(picking, move) if has_sale else None
            lines.append({
                'codigo': move.product_id.default_code or '',
                'descripcion': move.product_id.display_name or move.description_picking or '',
                'cantidad': move.quantity,
                'unidad': move.product_uom.name or '',
                'prices': prices,
            })
            if prices:
                sub_total += prices['precio']
                descuento += prices['descuento']
                total += prices['total']
        return {
            'has_sale': has_sale,
            'lines': lines,
            'sub_total': sub_total,
            'descuento': descuento,
            'total': total,
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        pickings = self.env['stock.picking'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': pickings,
            'info_map': {p.id: self._picking_info(p) for p in pickings},
        }
