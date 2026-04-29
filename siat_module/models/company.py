import logging
from odoo import models, fields, api
from ..services.service_siat_sync import ServiceSiatSync

_logger = logging.getLogger(__name__)
_env_values = [
    ('1', 'Producción'),
    ('2', 'Piloto/Pruebas')
]
_bill_types_values = [
    ('1', 'Electrónica en Linea'),
    ('2', 'Computarizada en Linea')
]
_mode_siat_values = [
    ('1', 'Facturador'),
    ('2', 'Odoo SIAT'),
]


class Company(models.Model):
    _inherit = 'res.company'

    delegated_token = fields.Char(string="Token SIAT", default=None)
    siat_system_name = fields.Char(string="Nombre del Sistema")
    siat_system_code = fields.Char(string="Código del Sistema")
    siat_environment = fields.Selection(
        _env_values,
        string="Ambiente", default='2'
    )
    siat_mode = fields.Selection(
        _bill_types_values,
        string="Modalidad", default='2'
    )
    siat_mode_siat = fields.Selection(
        _mode_siat_values,
        string="Modo Facturación", default='1'
    )
    siat_cafc = fields.Char(string="CAFC")
    siat_url = fields.Char(string="SIAT URL base")
    siat_email = fields.Char(string="Correo de Envío Facturas")
    siat_email_name = fields.Char(string="Nombre Remitente Facturas")
    siat_cuis = fields.Char(string="CUIS", readonly=True)
    siat_cuis_exp = fields.Char(string="Expira", readonly=True)
    siat_pk_file = fields.Binary(string="Llave Privada", attachment=False)
    siat_pk_file_name = fields.Char(string="Nombre Llave Privada")
    siat_cert_file = fields.Binary(string="Certificado", attachment=False)
    siat_cert_file_name = fields.Char(string="Nombre Certificado")

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._create_siat_sequence()
        return companies

    def _create_siat_sequence(self):
        IrSequence = self.env['ir.sequence'].sudo()
        for company in self:
            exists = IrSequence.search([
                ('code', '=', 'siat.invoice'),
                ('company_id', '=', company.id),
            ], limit=1)
            if exists:
                _logger.debug(
                    '_create_siat_sequence | company=%s (%d) ya tiene secuencia id=%d',
                    company.name, company.id, exists.id,
                )
                continue
            IrSequence.create({
                'name': f'SIAT Invoice Number [{company.name}]',
                'code': 'siat.invoice',
                'prefix': 'F',
                'padding': 8,
                'number_next': 1,
                'number_increment': 1,
                'implementation': 'no_gap',
                'company_id': company.id,
            })
            _logger.info(
                '_create_siat_sequence | Secuencia SIAT creada para company=%s (%d)',
                company.name, company.id,
            )
    
    def action_siat_sync_all(self):
        """Sincroniza todos los catálogos SIAT para todas las compañías activas."""
        companies = self.search([])
        for company in companies:
            env = self.env(context=self.env.context).with_company(company)
            service = ServiceSiatSync(env)
            service.sync_activities(0, 0)
            service.sync_measure_unit(0, 0)
            service.sync_product_service(0, 0)
            service.sync_payment_type(0, 0)
            service.sync_identity_document(0, 0)
            service.sync_legends(0, 0)
            service.sync_cancellation_reason(0, 0)