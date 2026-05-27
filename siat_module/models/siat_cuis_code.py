import logging
from datetime import datetime, timezone, timedelta

from odoo import models, fields

from ..services.service_siat_sync import ServiceSiatSync

_logger = logging.getLogger(__name__)


class SiatCuisCode(models.Model):
    _name = 'siat.cuis_code'
    _description = 'Código Único de Inicio de Sistemas (CUIS)'
    _order = 'valid_until desc'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    cuis_code        = fields.Char(string='Código CUIS')
    valid_until      = fields.Datetime(string='Fecha Vigencia')
    branch_id        = fields.Integer(string='Sucursal', default=0, index=True)
    point_of_sale_id = fields.Integer(string='Punto de Venta', default=0, index=True)
    message_list     = fields.Char(string='Mensajes')
    transaction      = fields.Boolean(string='Transacción')
    service_response = fields.Text(string='Respuesta SIAT', required=True)

    # ── Vigencia ──────────────────────────────────────────────────────────────

    def is_expired(self):
        """
        True si el CUIS está vencido.
        El CUIS tiene vigencia de 365 días según RND 102100000011.
        """
        self.ensure_one()
        if not self.valid_until:
            return True
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        return now_utc >= self.valid_until

    # ── Sincronización ────────────────────────────────────────────────────────

    def sync_model(self, service=None):
        """
        Sincroniza CUIS desde el SIN para todos los PV activos de la compañía.

        Itera sobre registros completos de siat.point_of_sale para disponer
        de pos.codigo_sucursal (sucursal) y pos.pos_siat_id (puntoventa)
        juntos en cada iteración.
        """
        if service is None:
            service = ServiceSiatSync(self.env)

        point_of_sales = self.env['siat.point_of_sale'].search([
            ('company_id', '=', self.env.company.id),
            ('active',     '=', True),
        ])

        if not point_of_sales:
            _logger.warning(
                'sync_model [cuis] | company=%d | sin puntos de venta activos',
                self.env.company.id,
            )
            return

        _logger.info(
            'sync_model [cuis] | company=%d | sincronizando %d PV(s)',
            self.env.company.id, len(point_of_sales),
        )

        for pos in point_of_sales:
            sucursal   = pos.codigo_sucursal
            puntoventa = pos.pos_siat_id

            try:
                current_cuis = self.env['siat.cuis_code'].search([
                    ('company_id',       '=', self.env.company.id),
                    ('branch_id',        '=', sucursal),
                    ('point_of_sale_id', '=', puntoventa),
                ], order='valid_until desc', limit=1)

                if current_cuis and not current_cuis.is_expired():
                    _logger.debug(
                        'sync_model [cuis] | company=%d branch=%d pos=%d | '
                        'CUIS vigente id=%d — omitiendo renovación',
                        self.env.company.id, sucursal, puntoventa, current_cuis.id,
                    )
                    continue

                # CUIS vencido o inexistente → renovar
                cuis_response = service.sync_cuis(sucursal, puntoventa)
                new_cuis = self._create_from_response(cuis_response, sucursal, puntoventa)
                _logger.info(
                    'sync_model [cuis] | company=%d branch=%d pos=%d | '
                    'CUIS renovado id=%d vigencia=%s',
                    self.env.company.id, sucursal, puntoventa,
                    new_cuis.id, new_cuis.valid_until,
                )

            except Exception:
                _logger.exception(
                    'sync_model [cuis] | company=%d branch=%d pos=%d | '
                    'ERROR al sincronizar CUIS — se continúa con el siguiente PV',
                    self.env.company.id, sucursal, puntoventa,
                )

    def _create_from_response(self, cuis_response, sucursal, puntoventa):
        """
        Persiste en BD el CUIS recibido del SIN.

        Args:
            cuis_response (dict): respuesta del SIN con codigo, fechaVigencia, etc.
            sucursal   (int): código de sucursal.
            puntoventa (int): código del PV.

        Returns:
            siat.cuis_code: registro creado.
        """
        raw_date = cuis_response.get('fechaVigencia')
        valid_until = None

        if raw_date:
            if isinstance(raw_date, str):
                from datetime import datetime as _dt
                try:
                    dt_with_tz = _dt.fromisoformat(raw_date)
                    valid_until = dt_with_tz.astimezone(timezone.utc).replace(tzinfo=None)
                except ValueError:
                    _logger.warning(
                        '_create_from_response [cuis] | '
                        'fechaVigencia string no parseable: %r', raw_date
                    )
            elif hasattr(raw_date, 'astimezone'):
                valid_until = raw_date.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                _logger.warning(
                    '_create_from_response [cuis] | '
                    'fechaVigencia tipo inesperado: %r', type(raw_date)
                )

        record = self.create({
            'company_id':        self.env.company.id,
            'cuis_code':         cuis_response.get('codigo'),
            'valid_until':       valid_until,
            'branch_id':         sucursal,
            'point_of_sale_id':  puntoventa,
            'message_list':      str(cuis_response.get('mensajesList', '')),
            'transaction':       cuis_response.get('transaccion', False),
            'service_response':  str(cuis_response),
        })

        _logger.info(
            '_create_from_response [cuis] | '
            'company=%d branch=%d pos=%d | cuis_id=%d vigencia=%s',
            self.env.company.id, sucursal, puntoventa,
            record.id, valid_until,
        )
        return record

    # ── Consultas ─────────────────────────────────────────────────────────────

    def get_latest(self, branch_id=0, point_of_sale_id=0):
        """CUIS más reciente para la compañía/sucursal/PV activos."""
        domain = [
            ('company_id',       '=', self.env.company.id),
            ('branch_id',        '=', branch_id),
            ('point_of_sale_id', '=', point_of_sale_id),
        ]
        record = self.search(domain, order='valid_until desc', limit=1)
        _logger.debug(
            'get_latest [cuis] | company=%d branch=%d pos=%d | found=%s',
            self.env.company.id, branch_id, point_of_sale_id, bool(record),
        )
        return record if record else None