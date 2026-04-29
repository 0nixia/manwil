from odoo import models, fields


class HrEmployeeSiat(models.Model):
    _inherit = 'hr.employee'

    siat_pos_ids = fields.One2many(
        'siat.employee.pos', 'employee_id',
    )