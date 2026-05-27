from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    siat_homologation_ids = fields.One2many(
        'siat.product.homologation',
        'product_tmpl_id',
        string='Homologación SIAT'
    )
    siat_current_homologation_id = fields.Many2one(
        'siat.product.homologation',
        compute='_compute_current_homologation',
        store=False,
    )

    @api.depends_context('company')
    def _compute_current_homologation(self):
        for record in self:
            homologation = record.siat_homologation_ids.filtered(
                lambda h: h.company_id == self.env.company
            )
            record.siat_current_homologation_id = homologation[0] if homologation else False


class ProductProduct(models.Model):
    _inherit = 'product.product'

    siat_measure_id = fields.Many2one(
        'siat.measure_unit',
        string='Unidad de Medida SIAT',
        compute='_compute_siat_homologation_fields',
        inverse='_inverse_siat_homologation_fields',
        store=False,
    )
    siat_activity_id = fields.Many2one(
        'siat.activity',
        string='Actividad Económica SIAT',
        compute='_compute_siat_homologation_fields',
        inverse='_inverse_siat_homologation_fields',
        store=False,
    )
    siat_prod_id = fields.Many2one(
        'siat.product_service',
        string='Tipo de Producto SIAT',
        compute='_compute_siat_homologation_fields',
        inverse='_inverse_siat_homologation_fields',
        store=False,
    )
    siat_activity_caeb = fields.Char(
        string='CAEB Actividad',
        compute='_compute_siat_activity_caeb',
        store=False,
    )

    @api.depends(
        'product_tmpl_id.siat_homologation_ids.siat_measure_id',
        'product_tmpl_id.siat_homologation_ids.siat_activity_id',
        'product_tmpl_id.siat_homologation_ids.siat_prod_id',
        'product_tmpl_id.siat_homologation_ids.company_id',
    )
    def _compute_siat_homologation_fields(self):
        for rec in self:
            homol = rec.product_tmpl_id.siat_homologation_ids.filtered(
                lambda h: h.company_id == self.env.company
            )
            homol = homol[0] if homol else False
            rec.siat_measure_id = homol.siat_measure_id if homol else False
            rec.siat_activity_id = homol.siat_activity_id if homol else False
            rec.siat_prod_id = homol.siat_prod_id if homol else False

    @api.depends(
        'product_tmpl_id.siat_homologation_ids.siat_activity_id',
        'product_tmpl_id.siat_homologation_ids.company_id',
    )
    def _compute_siat_activity_caeb(self):
        for rec in self:
            homol = rec.product_tmpl_id.siat_homologation_ids.filtered(
                lambda h: h.company_id == self.env.company
            )
            homol = homol[0] if homol else False
            rec.siat_activity_caeb = (homol.siat_activity_id.caeb or '') if homol else ''

    def _inverse_siat_homologation_fields(self):
        """Escribe measure, activity y prod en un solo bloque sobre la homologación,
        creándola si no existe. Igual que lo hace product.template con siat_homologation_ids."""
        for rec in self:
            company = rec.company_id or self.env.company
            tmpl = rec.product_tmpl_id
            homol = tmpl.siat_homologation_ids.filtered(
                lambda h: h.company_id == company
            )
            vals = {
                'siat_measure_id': rec.siat_measure_id.id or False,
                'siat_activity_id': rec.siat_activity_id.id or False,
                'siat_prod_id': rec.siat_prod_id.id or False,
            }
            if homol:
                homol[0].write(vals)
            else:
                self.env['siat.product.homologation'].create({
                    'product_tmpl_id': tmpl.id,
                    'company_id': company.id,
                    **vals,
                })

    @api.onchange('siat_activity_id')
    def _onchange_siat_activity_id_product(self):
        self.siat_activity_caeb = self.siat_activity_id.caeb or ''
        self.siat_prod_id = False