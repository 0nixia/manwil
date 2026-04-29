from odoo import models, fields, _
from odoo.exceptions import UserError, ValidationError
import logging
from ..services.service_invoices import ServiceInvoices

_logger = logging.getLogger(__name__)


def _get_cancellation_reasons(self):
    data = [('0', '-- Motivo Anulación --')]
    try:
        cuis = self.env.company.siat_cuis
        if not cuis:
            return data
        reasons = self.env['siat.cancellation_reason'].search([], order='description')
        if not reasons:
            raise UserError(_("Debe sincronizar los datos con el SIAT"))
        for reason in reasons:
            data.append((str(reason.code), reason.description))
    except Exception:
        _logger.exception("ERROR _get_cancellation_reasons")
    return data

class InvoiceCancellationByCuf(models.Model):
    _name = 'siat.invoice.cancellation.by.cuf'
    _description = 'Invoice Cancellation by CUF from SIAT Invoice'

    cuf = fields.Char(string='CUF', required=True)
    void_reason = fields.Selection(
        selection=_get_cancellation_reasons,
        default='0',
        string='Motivo de Anulación'
    )
    status = fields.Selection(
        [
            ('FAILED', 'Fallo'),
            ('SUCCESS', 'Éxito'),
            ('CANCELLED', 'Cancelado')
        ],
        default='FAILED'
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura',
        required=True,
        domain="[('move_type', 'in', ('out_invoice','out_refund'))]"
    )

    def action_cancel_invoice(self):
        for record in self:
            if record.invoice_id.company_id != record.company_id:
                raise ValidationError(
                    _("La factura no pertenece a la compañía seleccionada.")
                )
            if record.invoice_id.state not in ['draft', 'posted']:
                raise UserError(
                    _("Only draft or posted invoices can be cancelled.")
                )
            record.invoice_id.button_cancel()
            record.status = 'CANCELLED'

    def confirm_cancellation(self):
        for record in self:
            if record.void_reason == '0':
                raise ValidationError(
                    _("Debe seleccionar un motivo de anulación")
                )
            try:
                service = ServiceInvoices(record.with_company(record.company_id).env)
                try:
                    service.void_by_cuf(
                        record.cuf,
                        record.void_reason
                    )
                finally:
                    service.cleanup()
                record.status = 'SUCCESS'

            except Exception:
                _logger.exception(
                    "Error cancelando factura por CUF (company=%s)",
                    record.company_id.id
                )
                record.status = 'FAILED'
                raise UserError(
                    _("La factura no fue anulada.")
                )