import logging
from datetime import datetime, timezone, timedelta
from odoo import models, fields, api
from ..services.service_siat_sync import ServiceSiatSync
from ..libsiat import functions as siat_functions

_logger = logging.getLogger(__name__)
_EXPIRY_SAFETY_MARGIN_MINUTES = 5


class SiatCufdCode(models.Model):
    _name = 'siat.cufd_code'
    _description = 'Código Único de Facturación Diaria (CUFD)'
    _order = 'ended_date desc'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    cufd_code        = fields.Char(string='Código CUFD')
    control_code     = fields.Char(string='Código de Control')
    address          = fields.Char(string='Dirección')
    branch_id        = fields.Integer(string='Sucursal', default=0, index=True)
    point_of_sale_id = fields.Integer(string='Punto de Venta', index=True)
    started_date     = fields.Datetime(string='Fecha Inicio', default=fields.Datetime.now)
    ended_date       = fields.Datetime(string='Fecha Vigencia')
    message_list     = fields.Text(string='Mensajes')
    transaction      = fields.Boolean(string='Transacción')
    service_response = fields.Text(string='Respuesta SIAT', required=True)

    def is_expired(self, safety_margin_minutes=_EXPIRY_SAFETY_MARGIN_MINUTES):
        self.ensure_one()
        if not self.ended_date:
            return True
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        return now_utc >= (self.ended_date - timedelta(minutes=safety_margin_minutes))

    def minutes_remaining(self):
        self.ensure_one()
        if not self.ended_date:
            return 0
        delta = self.ended_date - datetime.now(timezone.utc).replace(tzinfo=None)
        return int(delta.total_seconds() / 60)

    def sync_model(self, service=None):
        if service is None:
            service = ServiceSiatSync(self.env)
        point_of_sales = self.env['siat.point_of_sale'].search([
            ('company_id', '=', self.env.company.id),
            ('active',     '=', True),
        ])
        if not point_of_sales:
            _logger.warning(
                'sync_model [cufd] | company=%d | sin puntos de venta activos',
                self.env.company.id,
            )
            return
        _logger.info(
            'sync_model [cufd] | company=%d | sincronizando %d PV(s)',
            self.env.company.id, len(point_of_sales),
        )
        for pos in point_of_sales:
            sucursal   = pos.codigo_sucursal
            puntoventa = pos.pos_siat_id
            try:
                cufd_response = service.get_cufd_from_siat(sucursal, puntoventa)
                new_cufd = self._create_from_response(cufd_response, sucursal, puntoventa)
                _logger.info(
                    'sync_model [cufd] | company=%d branch=%d pos=%d | '
                    'CUFD renovado id=%d vigencia=%s',
                    self.env.company.id, sucursal, puntoventa,
                    new_cufd.id, new_cufd.ended_date,
                )
            except Exception:
                _logger.exception(
                    'sync_model [cufd] | company=%d branch=%d pos=%d | '
                    'ERROR al sincronizar CUFD — se continúa con el siguiente PV',
                    self.env.company.id, sucursal, puntoventa,
                )

    def _create_from_response(self, cufd_response, sucursal, puntoventa):
        raw_date = cufd_response.get('fechaVigencia')
        ended_date = None
        if raw_date and hasattr(raw_date, 'astimezone'):
            ended_date = raw_date.astimezone(timezone.utc).replace(tzinfo=None)
        elif raw_date:
            _logger.warning(
                '_create_from_response | fechaVigencia no es datetime: %r', raw_date
            )
        record = self.create({
            'company_id':        self.env.company.id,
            'cufd_code':         cufd_response.get('codigo'),
            'control_code':      cufd_response.get('codigoControl'),
            'address':           cufd_response.get('direccion'),
            'branch_id':         sucursal,     # ← FIX crítico: antes siempre faltaba
            'point_of_sale_id':  puntoventa,
            'ended_date':        ended_date,
            'message_list':      str(cufd_response.get('mensajesList', '')),
            'transaction':       cufd_response.get('transaccion', False),
            'service_response':  str(cufd_response),
        })
        return record

    def get_latest(self, branch_id=0, point_of_sale_id=0):
        domain = [
            ('company_id',       '=', self.env.company.id),
            ('branch_id',        '=', branch_id),
            ('point_of_sale_id', '=', point_of_sale_id),
        ]
        record = self.search(domain, order='ended_date desc', limit=1)
        return record if record else None

    def get_valid(self, branch_id=0, point_of_sale_id=0):
        safety_limit = (
            datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(minutes=_EXPIRY_SAFETY_MARGIN_MINUTES)
        )
        domain = [
            ('company_id',       '=', self.env.company.id),
            ('branch_id',        '=', branch_id),
            ('point_of_sale_id', '=', point_of_sale_id),
            ('ended_date',       '>',  safety_limit),
        ]
        record = self.search(domain, order='ended_date desc', limit=1)
        return record if record else None

    def get_by_code(self, code):
        return self.search([('cufd_code', '=', code)], limit=1) or None

    def _compute_display_name(self):
        for record in self:
            ts = (
                siat_functions.sb_siat_localize_datetime(record.started_date)
                .strftime('%d-%m-%Y %H:%M')
                if record.started_date else '—'
            )
            status = '✓' if not record.is_expired() else '✗ Vencido'
            record.display_name = (
                f"CUFD [{ts}] — Control [{record.control_code}] {status}"
            )

    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain += ['|',
                ('control_code', operator, name),
                ('started_date', operator, name),
            ]
        return self._search(domain, limit=limit, order=order)