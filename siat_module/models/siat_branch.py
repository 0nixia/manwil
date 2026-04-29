from odoo import fields, models


class SiatBranch(models.Model):
    _name = 'siat.branch'
    _description = 'SIAT Branch'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True)
    branch_code = fields.Integer(string='Branch Code', required=True, default=0)
    name = fields.Char(string='Branch name', required=True, default='Main Branch')
    description = fields.Char(string='Branch description', required=True, default='Description branch')
    address = fields.Char(string='Address')
    siat_point_of_sale_ids = fields.One2many(
        comodel_name='siat.point_of_sale',
        inverse_name='siat_branch',
        string='Points of Sale'
    )