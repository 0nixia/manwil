import logging
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round
from ..services.service_siat_events import ServiceSiatEvents
from ..services.service_invoices import ServiceInvoices
from ..libsiat import constants as siat_constants
from ..libsiat import constants as siat_constants
from ..models.siat_utils import get_siat_employee_config

_logger = logging.getLogger(__name__)
NOMINATIVIDAD_LIMIT = 1000.00
COD_CI              = 1 
COD_NIT             = 5
SPECIAL_NITS = {siat_constants.NIT_CONSULADO, siat_constants.NIT_CONTROL_TRIB, siat_constants.NIT_VENTAS_MENORES}


class SiatAccountMove(models.Model):
    _inherit = "account.move"

    has_event = fields.Integer(
        string="ID Evento SIAT Activo",
        compute="_compute_event_cont",
        help="0 = sin evento activo. Almacena el evento_id del SIN cuando hay contingencia.",
    )
    siat_invoice_id = fields.Many2one(
        "siat.invoice",
        string="Factura SIAT",
    )
    siat_num_invoice = fields.Char(
        string="Nro Factura Evento",
        required=False,
    )
    siat_date_invoice = fields.Datetime(
        string="Fecha Facturado",
        required=False,
    )
    siat_real_invoice_number = fields.Integer(
        related="siat_invoice_id.invoice_number",
        string="Nro. Factura SIAT",
        store=True,
        readonly=True,
    )
    siat_status = fields.Char(
        related="siat_invoice_id.status",
        string="Código SIAT",
        store=True,
        readonly=True,
    )
    siat_status_label = fields.Char(
        related="siat_invoice_id.status_label",
        string="Estado SIAT",
        readonly=True
    )

    @api.depends("state")
    def _compute_event_cont(self):
        _emp, pos_rec, pos_code, sucursal_code, _login = get_siat_employee_config(self.env)
        evento = None
        if pos_code:
            service = ServiceSiatEvents(self.env)
            evento = service.evento_activo(sucursal_code, pos_code)
        for record in self:
            record.has_event = int(evento.evento_id) if evento and evento.evento_id else 0

    def _validate_partner_for_siat(self, partner, amount_total: float) -> dict:
        if partner.is_special_siat_case:
            if not partner.siat_special_case_type:
                raise UserError(
                    _("El partner '%s' está marcado como Caso Especial SIAT "
                      "pero no tiene el tipo de caso seleccionado.")
                    % partner.name
                )
            _logger.debug(
                "_validate_partner_for_siat | partner=%d | special=%s",
                partner.id, partner.siat_special_case_type,
            )
            return {
                "tipo_documento_identidad": COD_NIT,
                "nit_ruc_nif":              str(partner.siat_special_case_type),
                "complemento":              None,
                "customer_name":            partner.name or "",
                "excepcion":                1,
            }
        nombre = (partner.name or "").strip().lower()
        is_sin_nombre = (
            not nombre
            or nombre in ("sin nombre", "s/n")
            or (partner.vat or "") in SPECIAL_NITS
        )
        if is_sin_nombre:
            if amount_total > NOMINATIVIDAD_LIMIT:
                raise UserError(
                    _("Las facturas superiores a Bs %.2f requieren "
                      "identificación del cliente.")
                    % NOMINATIVIDAD_LIMIT
                )
            _logger.debug(
                "_validate_partner_for_siat | partner=%d | sin_nombre | amount=%.2f",
                partner.id, amount_total,
            )
            return {
                "tipo_documento_identidad": COD_NIT,
                "nit_ruc_nif":              "99001",
                "complemento":              None,
                "customer_name":            "S/N",
                "excepcion":                1,
            }
        if not partner.document_type_id or not partner.document_type_code:
            raise UserError(
                _("El cliente '%s' no tiene configurado el Tipo de Documento SIAT.")
                % partner.name
            )
        try:
            codigo_doc_identidad = int(partner.document_type_code)
        except (TypeError, ValueError):
            raise UserError(
                _("El código de tipo de documento SIAT del cliente '%s' no es válido.")
                % partner.name
            )
        if not partner.vat:
            raise UserError(
                _("El cliente '%s' no tiene registrado el NIT/CI (campo NIF).")
                % partner.name
            )
        if amount_total > NOMINATIVIDAD_LIMIT and not partner.vat:
            raise UserError(
                _("El NIT/CI del cliente '%s' es obligatorio "
                  "para facturas superiores a Bs %.2f.")
                % (partner.name, NOMINATIVIDAD_LIMIT)
            )
        complemento = None
        if codigo_doc_identidad == COD_CI and partner.ci_complement:
            complemento = partner.ci_complement
        _logger.debug(
            "_validate_partner_for_siat | partner=%d | cod_doc=%d | vat=%s | compl=%s",
            partner.id, codigo_doc_identidad, partner.vat, complemento,
        )
        return {
            "tipo_documento_identidad": codigo_doc_identidad,
            "nit_ruc_nif":              partner.vat,
            "complemento":              complemento,
            "customer_name":            partner.name or "",
            "excepcion":                0,
        }

    def action_post(self):
        for record in self:
            if record.move_type != "out_refund" or record.state != "draft":
                continue
            if not record.siat_invoice_id:
                continue
            siat_status = record.siat_invoice_id.status
            if siat_status == siat_constants.InvoiceStatus.INVOICE_ISSUED:
                view_id = self.env.ref("siat_module.invoice_cancellation_form").id
                return {
                    "name":      _("Cancelar Factura SIAT"),
                    "type":      "ir.actions.act_window",
                    "res_model": "siat.invoice",
                    "view_mode": "form",
                    "view_id":   view_id,
                    "target":    "new",
                    "context":   {"default_move_id": record.id},
                    "res_id":    record.siat_invoice_id.id,
                }
            if siat_status == siat_constants.InvoiceStatus.INVOICE_REVERTED:
                raise UserError(
                    _("No se puede anular una factura ya revertida en el SIAT.")
                )
        return super().action_post()

    def action_post_siat(self):
        _emp, pos_rec, pos_code, sucursal_code, _login = get_siat_employee_config(self.env)
        for record in self:
            if record.state != "draft":
                continue
            if 'is_move_sent' in record._fields:
                record.is_move_sent = True
            record.action_post()
            invoice = record.create_invoice(record, pos_code, sucursal_code)
            if not invoice:
                raise UserError(_("No se pudo generar la factura en el SIAT."))
            try:
                record._siat_post_invoice_message(invoice, pos_code, sucursal_code)
            except Exception:
                _logger.exception(
                    "action_post_siat | post message+email failed | move=%d | invoice=%d",
                    record.id, invoice.id,
                )
        return True

    def _siat_post_invoice_message(self, invoice, pos_code, sucursal_code):
        """Publica en el Chatter del account.move el correo SIAT con HTML
        rico + XML + PDF adjuntos, y dispara el envío al cliente vía
        message_post(subtype=mt_comment). Helper interno; idempotencia no
        garantizada — llamar exactamente una vez por registro SIAT.
        """
        self.ensure_one()
        import base64
        svc = ServiceInvoices(self.with_company(self.company_id).env)
        xml_bytes = svc.build_xml_for_invoice(invoice)
        if not xml_bytes:
            _logger.warning(
                "_siat_post_invoice_message | XML build failed | move=%d | invoice=%d",
                self.id, invoice.id,
            )
            return
        report = self.env.ref('siat_module.siat_invoicer_report')
        pdf_content, _dummy = self.env['ir.actions.report']._render_qweb_pdf(
            report.id, [invoice.id]
        )
        xml_att = self.env['ir.attachment'].create({
            'name':      'FACTURA_{}_{}.xml'.format(self.company_id.name, invoice.invoice_number),
            'datas':     base64.b64encode(xml_bytes),
            'mimetype':  'application/xml',
            'res_model': 'account.move',
            'res_id':    self.id,
            'type':      'binary',
        })
        pdf_att = self.env['ir.attachment'].create({
            'name':      'FACTURA_{}_{}.pdf'.format(self.company_id.name, invoice.invoice_number),
            'datas':     base64.b64encode(pdf_content),
            'mimetype':  'application/pdf',
            'res_model': 'account.move',
            'res_id':    self.id,
            'type':      'binary',
        })
        template = self.env.ref('siat_module.siat_invoice_email_template')
        body_html = template._render_field('body_html', [invoice.id], compute_lang=True)[invoice.id]
        subject = template._render_field('subject', [invoice.id], compute_lang=True)[invoice.id]
        config = svc.getConfig()
        company_email = (
            config.get('siat_email')
            or self.company_id.email
            or self.company_id.partner_id.email
        )
        sender_name = config.get('siat_email_name') or self.company_id.name
        email_from = "{} <{}>".format(sender_name, company_email)
        customer = invoice.get_customer()
        recipient_ids = [customer.id] if (customer and customer.email) else []
        self.with_context(mail_post_autofollow=True).message_post(
            body=body_html,
            subject=subject,
            partner_ids=recipient_ids,
            attachment_ids=[xml_att.id, pdf_att.id],
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            email_from=email_from,
        )

    def _siat_product_name_with_variant(self, product, fallback_name=''):
        """Nombre del producto con sus atributos de variante, sin el [código]."""
        if not product:
            return fallback_name or ''
        variant = product.product_template_attribute_value_ids._get_combination_name()
        if variant:
            return "%s (%s)" % (product.name, variant)
        return product.name or fallback_name or ''

    def create_invoice(self, to_post, pos=0, sucursal=0):
        service = ServiceInvoices(self.with_company(to_post.company_id).env)
        partner = to_post.partner_id
        amount  = round(
            float_round(
                to_post.amount_untaxed,
                precision_digits=2,
                rounding_method="HALF-EVEN",
            ),
            2,
        )
        id_data = self._validate_partner_for_siat(partner, amount)
        invoiceData = {
            "codigo_documento_sector":  1,
            "codigo_sucursal":          sucursal,
            "punto_venta":              pos,
            "customer_id":              partner.id,
            "customer":                 id_data["customer_name"],
            "tipo_documento_identidad": id_data["tipo_documento_identidad"],
            "nit_ruc_nif":              id_data["nit_ruc_nif"],
            "complemento":              id_data["complemento"],
            "codigo_metodo_pago":       1,
            "numero_tarjeta":           None,
            "total":                    amount,
            "codigo_moneda":            1,
            "tipo_cambio":              1,
            "monto_giftcard":           0,
            "discount":                 0,
            "data":                     {"excepcion": id_data["excepcion"]},
            "items":                    [],
            "siat_num_invoice":         to_post.siat_num_invoice,
            "siat_date_invoice":        to_post.siat_date_invoice,
        }
        activity = None
        for line in to_post.invoice_line_ids:
            homol = line.product_id.product_tmpl_id.siat_current_homologation_id
            if not homol or not homol.siat_activity_id or not homol.siat_measure_id or not homol.siat_prod_id:
                raise UserError(
                    _("El producto '%s' no está homologado con el SIAT "
                      "para la compañía actual.")
                    % line.product_id.name
                )
            if activity and homol.siat_activity_id.id != activity:
                raise UserError(
                    _("Existen productos de diferentes actividades económicas SIAT. "
                      "Revise la homologación del producto '%s'.")
                    % line.product_id.name
                )
            activity = homol.siat_activity_id.id

            qty = float_round(
                line.quantity, precision_digits=2, rounding_method="HALF-EVEN"
            )
            subtotal_line = round(
                float_round(
                    line.price_subtotal, precision_digits=2, rounding_method="HALF-EVEN"
                ),
                2,
            )
            price_neto = round(subtotal_line / qty, 2) if qty else 0.0
            invoiceData["items"].append({
                "product_id":          line.product_id.id,
                "product_code":        line.product_id.default_code or line.product_id.barcode or str(line.product_id.id),
                "product_name":        self._siat_product_name_with_variant(
                    line.product_id, line.name
                ),
                "quantity":            qty,
                "unidad_medida":       homol.siat_measure_id.code,
                "codigo_actividad":    homol.siat_activity_id.caeb,
                "codigo_producto_sin": homol.siat_prod_id.code_prod,
                "price":               price_neto,
                "discount":            0.0,
                "numero_serie":        "",
                "numero_imei":         "",
            })
        try:
            invoice = service.create(invoiceData)
            _logger.info(
                "create_invoice | move=%d | company=%d | invoice=%s",
                to_post.id, to_post.company_id.id, invoice,
            )
            if invoice:
                to_post.write({"siat_invoice_id": invoice.id})
                invoice.write({"account_move_id": to_post.id})
                return invoice
        except Exception:
            _logger.exception(
                "create_invoice ERROR | move=%d | partner=%d",
                to_post.id, partner.id,
            )
            raise
        finally:
            service.cleanup()

    def reset_invoice(self):
        for record in self:
            if not record.siat_invoice_id:
                _logger.warning(
                    "reset_invoice | move=%d | sin siat_invoice_id, se omite",
                    record.id,
                )
                continue
            service = ServiceInvoices(record.with_company(record.company_id).env)
            try:
                service.revert_void(record.siat_invoice_id.id)
            finally:
                service.cleanup()

            if record.state == "draft":
                record.action_post()

            record.message_post(
                body=_("Factura revertida y registrada en el SIAT.")
            )
            _logger.info(
                "reset_invoice | move=%d | siat_invoice=%d | revertida",
                record.id, record.siat_invoice_id.id,
            )