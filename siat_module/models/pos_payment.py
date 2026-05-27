from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        _logger.info("Executing check method in pos.make.payment")
        res = super(PosMakePayment, self).check()
        for _ in self:
            order = self.env['pos.order'].browse(self.env.context.get('active_id'))
            if order and order.amount_total < 0:
                _logger.info("Processing refund for order: %s", order.name)
                original_order = self.env['pos.order'].search([
                    ('id', '!=', order.id ),
                    ('partner_id', '=', order.partner_id.id),
                    ('amount_total', '>', 0),
                    ('account_move', '!=', False),
                ], order='date_order desc', limit=1)
                if original_order:
                    _logger.info("Found original order: %s with invoice %s", original_order.name, original_order.account_move.id)

                    order.write({'account_move': original_order.account_move.id, 'to_invoice_siat': False})
                    _logger.info("Linked refund order %s to invoice %s", order.name, original_order.account_move.id)
                else:
                    _logger.warning("No original order found for refund order: %s", order.name)
        return res