from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SiatEmployeePos(models.Model):
    _name = 'siat.employee.pos'
    _description = 'SIAT PV por empleado y empresa'
    _rec_name = 'puntoventa_id'

    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade', index=True
    )
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company
    )
    puntoventa_id = fields.Many2one(
        'siat.point_of_sale',
        domain="[('company_id','=',company_id),('active','=',True)]",
        ondelete='set null'
    )
    actividad_id = fields.Many2one(
        'siat.activity',
        domain="[('company_id','=',company_id)]",
    )
    _sql_constraints = [(
        'employee_company_unique',
        'unique(employee_id, company_id)',
        'Ya existe configuración SIAT para este empleado en esta empresa.'
    )]

    @api.constrains('puntoventa_id', 'company_id')
    def _check_pos_company(self):
        for rec in self:
            if rec.puntoventa_id and rec.puntoventa_id.company_id != rec.company_id:
                raise ValidationError(_(
                    'El Punto de Venta debe pertenecer a la misma empresa.'
                ))

    @api.constrains('actividad_id', 'company_id')
    def _check_act_company(self):
        for rec in self:
            if rec.actividad_id and rec.actividad_id.company_id != rec.company_id:
                raise ValidationError(_(
                    'La actividad económica debe pertenecer a la misma empresa.'
                ))

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.puntoventa_id = False
        self.actividad_id = False
        return {
            'domain': {
                'puntoventa_id': [
                    ('company_id', '=', self.company_id.id),
                    ('active', '=', True),
                ],
                'actividad_id': [
                    ('company_id', '=', self.company_id.id),
                ],
            }
        }