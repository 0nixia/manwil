from odoo import models, api, fields, _
from odoo.exceptions import UserError
from ..libsiat import constants as siat_constants
import logging

_logger = logging.getLogger(__name__)


class SiatPosOrder(models.Model):
    _inherit = 'pos.order'

    to_invoice_siat = fields.Boolean('Facturar con SIAT', default=False)

    @api.model
    def _order_fields(self, ui_order):
        res = super()._order_fields(ui_order)
        res['to_invoice_siat'] = ui_order.get('to_invoice_siat', False)
        return res

    def _generate_pos_order_invoice(self):
        self.ensure_one()
        if not self.to_invoice_siat:
            return super()._generate_pos_order_invoice()
        invoice_values = {
            'move_type':        'out_invoice',
            'partner_id':       self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'quantity':   line.qty,
                    'price_unit': line.price_unit,
                    'discount':   line.discount,
                })
                for line in self.lines
            ],
        }
        invoice = self.env['account.move'].create(invoice_values)
        invoice.with_company(self.company_id).action_post_siat()
        self.write({'account_move': invoice.id, 'state': 'invoiced'})
        self._apply_invoice_payments()
        _logger.info(
            "_generate_pos_order_invoice | order=%s | invoice=%d | siat OK",
            self.name, invoice.id,
        )
        return True

    def void_invoicer(self):
        for record in self:
            siat_inv = record.account_move.siat_invoice_id
            if siat_inv.status == siat_constants.InvoiceStatus.INVOICE_ISSUED:
                view_id = self.env.ref('siat_module.invoice_cancellation_form').id
                return {
                    'name':      'Cancelar Factura SIAT',
                    'type':      'ir.actions.act_window',
                    'res_model': 'siat.invoice',
                    'view_mode': 'form',
                    'view_id':   view_id,
                    'target':    'new',
                    'res_id':    siat_inv.id,
                }
            elif siat_inv.status == siat_constants.InvoiceStatus.INVOICE_REVERTED:
                raise UserError(_(
                    "No se puede anular una factura ya revertida en el SIAT."
                ))