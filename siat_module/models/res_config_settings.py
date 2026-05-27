from odoo import models, fields, api
from odoo.exceptions import UserError
from ..services.service_siat_sync import ServiceSiatSync
from ..libsiat.classes.siat_exception import SiatException
from .company import _env_values, _bill_types_values, _mode_siat_values
import traceback
import logging

_logger = logging.getLogger(__name__)


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    siat_nit = fields.Char(
        string="NIT",
        related='company_id.vat',
        readonly=False,
    )
    social_reason = fields.Char(
        string="Razón Social",
        related='company_id.name',
        readonly=False,
    )
    delegated_token = fields.Char(
        string="Token SIAT",
        related='company_id.delegated_token',
        readonly=False,
    )
    system_name = fields.Char(
        string="Nombre del Sistema",
        related='company_id.siat_system_name',
        readonly=False,
    )
    url_siat = fields.Char(
        string="SIAT URL base",
        related='company_id.siat_url',
        readonly=False,
    )
    siat_email = fields.Char(
        string="Correo de Envío Facturas",
        related='company_id.siat_email',
        readonly=False,
    )
    siat_email_name = fields.Char(
        string="Nombre Remitente Facturas",
        related='company_id.siat_email_name',
        readonly=False,
    )
    system_code = fields.Char(
        string="Código del Sistema",
        related='company_id.siat_system_code',
        readonly=False,
    )
    environment = fields.Selection(
        related='company_id.siat_environment',
        readonly=False,
    )
    siat_mode = fields.Selection(
        related='company_id.siat_mode',
        readonly=False,
    )
    mode_siat = fields.Selection(
        related='company_id.siat_mode_siat',
        readonly=False,
    )
    cafc = fields.Char(
        string="CAFC",
        related='company_id.siat_cafc',
        readonly=False,
    )
    pk_file = fields.Binary(
        string="Llave Privada",
        related='company_id.siat_pk_file',
        readonly=False,
    )
    pk_file_name = fields.Char(
        related='company_id.siat_pk_file_name',
        readonly=False,
    )
    cert_file = fields.Binary(
        string="Certificado",
        related='company_id.siat_cert_file',
        readonly=False,
    )
    cert_file_name = fields.Char(
        related='company_id.siat_cert_file_name',
        readonly=False,
    )
    cuis = fields.Char(
        string="CUIS",
        related='company_id.siat_cuis',
        readonly=True,
    )
    cuis_exp = fields.Char(
        string="Expira",
        related='company_id.siat_cuis_exp',
        readonly=True,
    )
    pos_siat_pos_id = fields.Many2one(
        'siat.point_of_sale',
        related='pos_config_id.siat_pos_id',
        readonly=False,
    )
    siat_pos_configured = fields.Boolean(
        compute='_compute_siat_pos_configured',
        string='SIAT POS sincronizados',
    )

    @api.depends('pos_siat_pos_id')
    def _compute_siat_pos_configured(self):
        has_pos = bool(self.env['siat.point_of_sale'].search_count([('active', '=', True)]))
        for rec in self:
            rec.siat_pos_configured = has_pos

    def _build_cfg_override(self, company):
        return {
            'token':           company.delegated_token or '',
            'nit':             company.vat or '',
            'razonSocial':     company.name or '',
            'ciudad':          company.city or '',
            'telefono':        company.phone or company.mobile or 'S/N',
            'codigoSistema':   company.siat_system_code or '',
            'codigoAmbiente':  int(company.siat_environment) if company.siat_environment else 2,
            'nombreSistema':   company.siat_system_name or '',
            'codigoModalidad': int(company.siat_mode) if company.siat_mode else 2,
            'cafc':            company.siat_cafc or '',
            'siat_email':      company.siat_email or '',
            'siat_email_name': company.siat_email_name or '',
        }

    def request_cuis(self):
        try:
            company = self.company_id or self.env.company
            if not company:
                raise UserError("No se pudo determinar la compañía activa.")
            if self:
                self.execute()
            company_env = self.with_company(company).env
            cfg_override = self._build_cfg_override(company)
            _logger.info('Iniciando request_cuis para: %s (NIT: %s)', company.name, cfg_override['nit'])
            service = ServiceSiatSync(env=company_env, cfg_override=cfg_override)
            cuis_req = service.sync_cuis(0, 0)
            if not cuis_req or not cuis_req.get('codigo'):
                raise UserError("El SIAT no devolvió un código CUIS válido.")
            company.write({
                'siat_cuis': cuis_req['codigo'],
                'siat_cuis_exp': str(cuis_req['fechaVigencia']),
            })
            _logger.info('Sincronizando Puntos de Venta...')
            branches = company_env['siat.branch'].search([('company_id', '=', company.id)])
            if branches:
                for branch in branches:
                    company_env['siat.point_of_sale'].sync_model(
                        sucursal=branch.branch_code, service=service
                    )
            else:
                company_env['siat.point_of_sale'].sync_model(sucursal=0, service=service)
            active_pos_list = company_env['siat.point_of_sale'].search([
                ('company_id', '=', company.id),
                ('active', '=', True)
            ])
            for pos_rec in active_pos_list:
                try:
                    service.sync_fecha_hora(pos_rec.codigo_sucursal, pos_rec.pos_siat_id)
                except Exception as e:
                    _logger.warning("No se pudo sincronizar fecha/hora para POS %s: %s", pos_rec.name, e)
            _logger.info('Sincronizando catálogos SIAT...')
            catalog_models = [
                'siat.cuis_code', 'siat.cufd_code', 'siat.activity', 
                'siat.document_sector', 'siat.type_document_sector', 
                'siat.invoice_label', 'siat.cancellation_reason', 
                'siat.country', 'siat.currency_type', 'siat.emission_type', 
                'siat.identity_document', 'siat.invoice_type', 'siat.measure_unit', 
                'siat.payment_type', 'siat.pos_type', 'siat.product_service', 
                'siat.room_type', 'siat.service_message', 'siat.significant_event'
            ]
            for model_name in catalog_models:
                try:
                    company_env[model_name].sync_model(service=service)
                except Exception as e:
                    _logger.error("Error sincronizando catálogo %s: %s", model_name, e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sincronización Exitosa',
                    'message': f"Los datos de {company.name} han sido actualizados con el SIAT.",
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        except SiatException as e:
            _logger.error('SIAT ERROR: %s', e.getMessage())
            raise UserError(f"Error desde Impuestos: {e.getMessage()}")
        except Exception as e:
            _logger.error('GENERAL ERROR: %s\n%s', e, traceback.format_exc())
            raise UserError(f"Error de sistema: {str(e)}")