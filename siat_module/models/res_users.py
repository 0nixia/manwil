from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    puntoventa_id = fields.Many2one(
        'siat.point_of_sale',
        string='Punto de Venta (legacy)',
        domain="[('company_id', 'in', company_ids), ('active', '=', True)]",
        ondelete='set null',
    )
    actividad_id = fields.Many2one(
        'siat.activity',
        string='Actividad (legacy)',
        domain="[('company_id', 'in', company_ids)]",
        required=False,
    )

    siat_employee_pv_display = fields.Char(
        string='Punto de Venta Activo',
        compute='_compute_siat_employee_display',
        store=False,
    )
    siat_employee_act_display = fields.Char(
        string='Actividad Económica Activa',
        compute='_compute_siat_employee_display',
        store=False,
    )

    @api.depends(
        'company_id',
        'employee_ids.siat_pos_ids.puntoventa_id',
        'employee_ids.siat_pos_ids.actividad_id',
        'employee_ids.siat_pos_ids.company_id',
    )
    def _compute_siat_employee_display(self):
        for user in self:
            employee = user.employee_ids.filtered(
                lambda e: e.company_id == user.company_id
            )[:1]

            if not employee:
                pv = user.puntoventa_id.filtered(
                    lambda p: p.company_id == user.company_id
                )[:1] if user.puntoventa_id else False
                user.siat_employee_pv_display = (
                    pv.name if pv else (user.puntoventa_id.name or '')
                )
                user.siat_employee_act_display = (
                    user.actividad_id.display_name or ''
                )
                continue

            config = employee.siat_pos_ids.filtered(
                lambda r: r.company_id == user.company_id
            )[:1]
            user.siat_employee_pv_display = config.puntoventa_id.name or ''
            user.siat_employee_act_display = config.actividad_id.display_name or ''

    def action_open_siat_employee(self):
        """Abre el formulario del empleado en la pestaña SIAT."""
        self.ensure_one()
        employee = self.employee_ids.filtered(
            lambda e: e.company_id == self.company_id
        )[:1]
        if not employee:
            employee = self.employee_ids[:1]
        if not employee:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin empleado vinculado',
                    'message': (
                        'Este usuario no tiene un empleado asociado. '
                        'Créelo desde RRHH → Empleados y vincula este usuario '
                        'en el campo "Usuario relacionado".'
                    ),
                    'sticky': True,
                    'type': 'warning',
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': employee.id,
            'target': 'current',
            'context': {'default_active_tab': 'siat_config'},
        }

    def action_show_select(self):
        for record in self:
            view_id = self.env.ref('siat_module.res_user_pos_form').id
            return {
                'name': 'Configurar Punto de Venta y Actividad',
                'type': 'ir.actions.act_window',
                'res_model': 'res.users',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'res_id': record.id,
            }

    def store_pos(self):
        for record in self:
            record.write({
                'puntoventa_id': record.puntoventa_id.id,
                'actividad_id':  record.actividad_id.id,
            })