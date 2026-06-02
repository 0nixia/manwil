from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_print_pdf(self):
        """Redirige el botón 'Print' de la cabecera de la factura.

        En Odoo 18 el botón principal de impresión llama a `action_print_pdf`
        (no `action_invoice_print`, que ya no existe). Para facturas y notas de
        crédito de cliente devolvemos el reporte personalizado Media Carta de
        Manwil; el resto de documentos mantienen el comportamiento estándar.
        """
        self.ensure_one()
        if self.move_type in ('out_invoice', 'out_refund'):
            return self.env.ref(
                'manwil_custom_reports.action_report_manwil_invoice'
            ).report_action(self)
        return super().action_print_pdf()
