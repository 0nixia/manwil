from odoo import fields, models


class SiatPosConfig(models.Model):
    _inherit = 'pos.config'

    siat_pos_id = fields.Many2one(
        'siat.point_of_sale',
        string='Punto de Venta SIAT',
        index=True,
    )