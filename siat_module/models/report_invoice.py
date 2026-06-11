from odoo import models, _
from odoo.exceptions import UserError
from ..services.service_invoices import ServiceInvoices
from ..libsiat.invoices.siatinvoice import SiatInvoice
from ..libsiat import functions as siat_functions
from ..models.invoice import Invoice


class ReportInvoice(models.AbstractModel):
    _name = 'report.siat_module.siat_invoice_template'
    _description = 'Siat Report Invoice'

    def _get_report_values(self, docids, data=None):
        move = self.env['account.move'].browse(docids).ensure_one()
        invoice = move.siat_invoice_id
        if not invoice:
            raise UserError(_(
                'Esta factura de Odoo no tiene una Factura SIAT asociada. '
                'Usa el reporte estándar de Odoo o verifica que la factura fue emitida al SIAT.'
            ))
        company = move.company_id
        service = ServiceInvoices(self.with_company(company).env)
        config = service.getConfig()
        cufds = self.env['siat.cufd_code'].search(
            [('cufd_code', '=', invoice.cufd)], limit=1
        )
        branch = self.env['siat.branch'].search(
            [('company_id', '=', company.id)], limit=1
        )
        siat_url = SiatInvoice.buildUrl(
            invoice.nit_emisor, invoice.cuf, invoice.invoice_number, invoice.ambiente
        )
        qr64 = siat_functions.sb_build_qr(siat_url)
        amount_text = (
            siat_functions.sb_numeroToLetras(invoice.total - invoice.monto_giftcard)
            + ' BOLIVIANOS'
        )
        return {
            'docs':                 move,
            'amount_text':          amount_text,
            'cufd':                 cufds[0] if cufds else None,
            'razon_social':         config['razonSocial'],
            'sucursal':             branch.name if branch else '',
            'ciudad':               company.city,
            'telefono':             config['telefono'],
            'qr_buffer':            'data:image/png;base64,{}'.format(qr64.decode('utf8')),
            'get_unidad_medida':    service.serviceSync.buscar_unidad_medida,
            'get_invoice_datetime': Invoice.get_invoice_datetime,
            'primary_color':        company.primary_color or '#000000',
            'secondary_color':      company.secondary_color or '#FFFFFF',
            'is_ticket':            False,
        }

class ReportInvoiceTicket(ReportInvoice):
    _name = 'report.siat_module.siat_invoice_template_ticket'
    _description = 'Siat Report Invoice Ticket'

    def _get_report_values(self, docids, data=None):
        values = super()._get_report_values(docids, data)
        if not values:
            return values
        invoice = values['docs'].siat_invoice_id
        siat_url = SiatInvoice.buildUrl(
            invoice.nit_emisor, invoice.cuf, invoice.invoice_number, invoice.ambiente
        )
        qr64 = siat_functions.sb_build_qr(siat_url)
        values['is_ticket'] = True
        values['qr_buffer'] = 'data:image/png;base64,{}'.format(qr64.decode('utf8'))
        return values

class ReportInvoicer(models.AbstractModel):
    _name = 'report.siat_module.siat_invoicer_template'
    _description = 'Siat Report Invoicer'

    def _get_report_values(self, docids, data=None):
        company = self.env.company
        invoice = self.env['siat.invoice'].browse(docids).ensure_one()
        if not invoice:
            raise UserError(_("Factura no disponible"))
        service = ServiceInvoices(self.with_company(company).env)
        config = service.getConfig()
        cufds = self.env['siat.cufd_code'].search(
            [('cufd_code', '=', invoice.cufd)], limit=1
        )
        branch = self.env['siat.branch'].search(
            [('company_id', '=', company.id)], limit=1
        )
        siat_url = SiatInvoice.buildUrl(
            invoice.nit_emisor, invoice.cuf, invoice.invoice_number, invoice.ambiente
        )
        qr64 = siat_functions.sb_build_qr(siat_url)
        amount_text = (
            siat_functions.sb_numeroToLetras(invoice.total - invoice.monto_giftcard)
            + ' BOLIVIANOS'
        )
        return {
            'docs':                 invoice,
            'amount_text':          amount_text,
            'cufd':                 cufds[0] if cufds else None,
            'razon_social':         config['razonSocial'],
            'sucursal':             branch.name if branch else '',
            'ciudad':               company.city,
            'telefono':             config['telefono'],
            'qr_buffer':            'data:image/png;base64,{}'.format(qr64.decode('utf8')),
            'get_unidad_medida':    service.serviceSync.buscar_unidad_medida,
            'get_invoice_datetime': Invoice.get_invoice_datetime,
            'primary_color':        company.primary_color or '#000000',
            'secondary_color':      company.secondary_color or '#FFFFFF',
            'is_ticket':            False,
        }