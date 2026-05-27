from odoo import models, fields, api


class SiatProductHomologation(models.Model):
    _name = 'siat.product.homologation'
    _description = 'Homologación SIAT por producto y compañía'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True,
    )
    siat_measure_id = fields.Many2one(
        'siat.measure_unit',
        string='Unidad de Medida SIAT',
    )
    siat_activity_id = fields.Many2one(
        'siat.activity',
        string='Actividad Económica SIAT',
    )
    siat_activity_caeb = fields.Char(
        string='CAEB Actividad',
        compute='_compute_activity_caeb',
        store=False,
    )
    siat_prod_id = fields.Many2one(
        'siat.product_service',
        string='Tipo de Producto SIAT',
    )
    _sql_constraints = [
        (
            'unique_product_company',
            'UNIQUE(product_tmpl_id, company_id)',
            'Ya existe una homologación para este producto en esta compañía.',
        )
    ]

    @api.depends('siat_activity_id')
    def _compute_activity_caeb(self):
        for rec in self:
            rec.siat_activity_caeb = rec.siat_activity_id.caeb or False

    @api.onchange('siat_activity_id')
    def _onchange_siat_activity_id(self):
        """Limpiar el producto seleccionado cuando cambia la actividad,
        para evitar que quede un producto de una actividad diferente."""
        self.siat_prod_id = False