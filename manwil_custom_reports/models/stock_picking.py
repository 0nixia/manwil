from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    validated_by_id = fields.Many2one(
        'res.users',
        string='Validado por',
        readonly=True,
        copy=False,
    )

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if picking.state == 'done':
                picking.validated_by_id = self.env.user
        return res

    def do_print_picking(self):
        """Redirige el botón 'Print' de la cabecera del picking al reporte
        personalizado Nota de Almacén (Media Carta) de Manwil.

        En Odoo 18 el botón 'Print' en estado 'Listo' (assigned) llama a este
        método. El botón 'Print' en estado 'Hecho' (done) es type="action" y
        apunta directo a `stock.action_report_delivery`; por eso una vista
        heredada (views/stock_picking_views.xml) lo reapunta también a este
        método, de modo que ambos estados impriman el formato de Manwil.
        Sirve igual para notas de ingreso y de salida (el template decide).
        """
        self.write({'printed': True})
        return self.env.ref(
            'manwil_custom_reports.action_report_manwil_picking'
        ).report_action(self)
