from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging
from ..libsiat import constants as siat_constants
from ..libsiat.invoices.siatinvoice import SiatInvoice
from ..services.service_invoices import ServiceInvoices

_logger = logging.getLogger(__name__)


def _get_cancellation_reasons(self):
    data = [('0', '-- Motivo Anulación --')]
    try:
        cuis = self.env.company.siat_cuis
        if not cuis:
            return data
        res = self.env['siat.cancellation_reason'].search([], order='description')
        if not res:
            raise UserError(_("Debe sincronizar los datos con el SIAT"))
        for actividad in res:
            data.append((str(actividad.code), actividad.description))
    except Exception:
        _logger.exception("ERROR _get_cancellation_reasons")
    return data


class Invoice(models.Model):
    _name = 'siat.invoice'
    _description = 'Invoice data model'

    customer_name           = fields.Char()
    nit_ruc_nif             = fields.Char()
    subtotal                = fields.Float(digits=(12, 2))
    total_tax               = fields.Float(digits=(12, 2))
    discount                = fields.Float(digits=(12, 2))
    monto_giftcard          = fields.Float(digits=(12, 2))
    total                   = fields.Float()
    invoice_number          = fields.Integer()
    control_code            = fields.Char()
    invoice_datetime        = fields.Datetime()
    void_datetime           = fields.Datetime()
    status                  = fields.Char()
    codigo_sucursal         = fields.Integer()
    punto_venta             = fields.Integer()
    codigo_documento_sector = fields.Integer()
    tipo_documento_identidad= fields.Integer()
    codigo_metodo_pago      = fields.Integer()
    codigo_moneda           = fields.Integer()
    cufd                    = fields.Char()
    cuf                     = fields.Char()
    cafc                    = fields.Char()
    complemento             = fields.Char()
    numero_tarjeta          = fields.Char()
    tipo_cambio             = fields.Float(digits=(12, 2))
    evento_id = fields.Many2one('siat.event', string='Event', ondelete='set null')
    package_id = fields.Many2one('siat.package', string='Package', ondelete='set null')
    siat_id                 = fields.Char()
    tipo_emision            = fields.Char()
    tipo_factura_documento  = fields.Integer()
    nit_emisor              = fields.Char()
    ambiente                = fields.Integer()
    leyenda                 = fields.Char()
    data                    = fields.Text()
    items                   = fields.One2many('siat.invoiceitem', 'invoice_id')
    account_move_id         = fields.Many2one('account.move', string='Account Move', index=True)
    is_invoicer             = fields.Boolean("Is Invoicer")
    display_note            = fields.Html(string='Detalle', compute='_compute_display_note')
    void_reason             = fields.Selection(_get_cancellation_reasons, default='0')
    partner_id = fields.Many2one('res.partner', string='Customer (Partner)', ondelete='restrict')
    client_id = fields.Many2one('siat.client', string='Customer (Invoicer)', ondelete='restrict')

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        store=True,
        index=True,
        default=lambda self: self.env.company,
    )
    status_label = fields.Char(string='Estado SIAT', compute='_compute_status_label')

    @api.depends('status')
    def _compute_status_label(self):
        statuses = {
            siat_constants.InvoiceStatus.INVOICE_ISSUED:   'Emitida',
            siat_constants.InvoiceStatus.INVOICE_ERROR:    'Error',
            siat_constants.InvoiceStatus.INVOICE_VOID:     'Anulada',
            siat_constants.InvoiceStatus.INVOICE_REVERTED: 'Revertida',
        }
        for record in self:
            record.status_label = statuses.get(record.status, record.status or '—')


    @api.depends('invoice_number')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"Nro. {record.invoice_number}"
    
    def get_customer(self):
        """Return the partner or client record based on is_invoicer."""
        if self.is_invoicer:
            return self.client_id
        else:
            return self.partner_id

    def get_customer_code(self):
        """Código de cliente para el reporte.

        Muestra el 'Company ID' (campo company_registry, pestaña
        Sales & Purchase → Misc) del cliente; si está vacío, cae al
        NIT/VAT. getattr defensivo porque el cliente en modo facturador
        (siat.client) puede no exponer esos campos.
        """
        customer = self.get_customer()
        if not customer:
            return ''
        return getattr(customer, 'company_registry', '') or getattr(customer, 'vat', '') or ''

    def _compute_display_note(self):
        statuses = {
            siat_constants.InvoiceStatus.INVOICE_ISSUED:   'Emitida',
            siat_constants.InvoiceStatus.INVOICE_ERROR:    'Error',
            siat_constants.InvoiceStatus.INVOICE_VOID:     'Anulada',
            siat_constants.InvoiceStatus.INVOICE_REVERTED: 'Revertida',
        }
        for record in self:
            status_label = statuses.get(record.status, record.status or '—')
            record.display_note = (
                f"<p><strong>Factura Nro:</strong> {record.invoice_number}</p>"
                f"<p><strong>Fecha Emisión:</strong> {record.invoice_datetime}</p>"
                f"<p><strong>CUF:</strong> {record.cuf}</p>"
                f"<p><strong>Estado:</strong> {status_label}</p>"
            )

    def confirm_cancellation(self):
        for record in self:
            if record.void_reason == '0':
                raise UserError(_("Debe seleccionar un motivo de anulación"))
            try:
                service = ServiceInvoices(record.with_company(record.company_id).env)
                try:
                    service.void(record.id, record.void_reason)
                finally:
                    service.cleanup()
                if not record.is_invoicer and record.account_move_id:
                    if record.account_move_id.state == 'draft':
                        record.account_move_id.action_post()
                    else:
                        _logger.info("La factura Odoo %s ya estaba publicada, saltando action_post", record.account_move_id.name)

            except Exception:
                _logger.exception(
                    "Error cancelando factura SIAT id=%s company=%s",
                    record.id, record.company_id.id,
                )
                raise UserError(_("La factura no fue anulada."))

    def nextInvoiceNumber(self, pos_id, sucursal_id=0):
        company = self.env.company
        seq_code = f'siat.invoice.{company.id}.{sucursal_id}.{pos_id}'
        sequence = self.env['ir.sequence'].search([
            ('code', '=', seq_code),
            ('company_id', '=', company.id),
        ], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name':              f'SIAT Nro. Factura - {company.name} Suc.{sucursal_id} PV.{pos_id}',
                'code':              seq_code,
                'prefix':           '',
                'padding':          8,
                'number_next':      1,
                'number_increment': 1,
                'implementation':   'no_gap',
                'company_id':       company.id,
            })
        return int(sequence.next_by_id())

    def get_data(self, key=None):
        if not self.data:
            data = {}
        else:
            try:
                data = json.loads(self.data)
            except (json.JSONDecodeError, TypeError):
                _logger.warning("get_data | invalid JSON in siat.invoice id=%d", self.id)
                data = {}
        if not isinstance(data, dict):
            data = {}
        return data.get(key) if key else data

    def set_data(self, key, value):
        data = self.get_data()
        data[key] = value
        self.data = json.dumps(data)
        return True

    def _prepare_data(self, data):
        if isinstance(data, (dict, list)):
            return json.dumps(data)
        return data

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'data' in vals:
                vals['data'] = self._prepare_data(vals['data'])
        return super().create(vals_list)

    def write(self, values):
        if 'data' in values:
            values['data'] = self._prepare_data(values['data'])
        return super().write(values)

    def get_date_invoiced(self):
        return self.invoice_datetime.strftime("%d-%m-%Y %H:%M:%S") if self.invoice_datetime else ""

    def get_date_void(self):
        return self.void_datetime.strftime("%d-%m-%Y %H:%M:%S") if self.void_datetime else ""

    def get_total(self):
        return '{0:,.2f}'.format(self.total)

    def get_invoice_number(self):
        return self.invoice_number

    def get_cuf_chunked(self, is_ticket=False):
        length = 41 if is_ticket else 15
        chunks = [self.cuf[i:i + length] for i in range(0, len(self.cuf), length)]
        return "\n".join(chunks)

    def get_activity(self):
        if not self.items:
            return ""
        code = self.items[0].codigo_actividad
        act = self.env['siat.activity'].search([('caeb', '=', code)], limit=1)
        return act.description if act else ""

    @staticmethod
    def get_invoice_datetime(invoice_datetime):
        return invoice_datetime.strftime('%d/%m/%Y %I:%M %p') if invoice_datetime else ""

    def print_ticket(self):
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_('Esta factura no tiene un comprobante contable asociado.'))
        return self.env.ref('siat_module.siat_invoice_report_ticket').report_action(
            self.account_move_id
        )

    def print_paper(self):
        self.ensure_one()
        return self.env.ref('siat_module.siat_account_invoices').report_action(
            self.account_move_id
        )

    def open_siat_page(self):
        self.ensure_one()
        if not self.cuf:
            raise UserError(_('Esta factura no tiene CUF generado.'))
        url = SiatInvoice.buildUrl(
            self.nit_emisor, self.cuf, self.invoice_number, self.ambiente
        )
        if not url:
            raise UserError(_('No se pudo generar la URL del SIAT.'))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def set_to_void(self):
        return self.env['account.move'].action_reverse()

    def reset_to_issued(self):
        self.ensure_one()
        return self.env['account.move'].browse(self.account_move_id.id).reset_invoice()

    def print_invoicer_report(self):
        self.ensure_one()
        return self.env.ref('siat_module.siat_invoicer_report').report_action(self)

    def void_invoicer(self):
        self.ensure_one()
        if self.status == siat_constants.InvoiceStatus.INVOICE_ISSUED:
            view_id = self.env.ref('siat_module.invoice_cancellation_form').id
            return {
                'name':      'Cancelar Factura SIAT',
                'type':      'ir.actions.act_window',
                'res_model': 'siat.invoice',
                'view_mode': 'form',
                'view_id':   view_id,
                'target':    'new',
                'res_id':    self.id,
            }
        if self.status == siat_constants.InvoiceStatus.INVOICE_REVERTED:
            raise UserError(_("No se puede anular una factura ya revertida en el SIAT"))

    def reset_void_invoicer(self):
        for record in self:
            service = ServiceInvoices(record.with_company(record.company_id).env)
            try:
                service.revert_void(record.id)
            finally:
                service.cleanup()