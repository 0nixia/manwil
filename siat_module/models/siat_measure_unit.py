from odoo import models, fields, api
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatMeasureUnits(models.Model):
    _name = 'siat.measure_unit'
    _description = 'Modelo para almacenar la lista de Unidades de Medida(sync)'
    _rec_name = 'description'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,)
    code = fields.Char(string="Código")
    description = fields.Char(string="Descripción")
    pos_id = fields.Integer()
    active = fields.Boolean('Active', default=True)
    _sql_constraints = [
        (
            'code_company_unique',
            'unique(code, company_id)',
            'El código de Unidad de Medida ya existe para esta compañía.'
        )
    ]

    def _compute_display_name(self):
        for record in self:
            record.display_name = record.description
    
    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('code', operator, name), ('description', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    def sync_model(self, service=None):
        """Get the list of Measure Units from SIAT each Point of Sale."""
        if service is None:
            service = ServiceSiatSync(self.env)
        point_of_sales = self.env['siat.point_of_sale'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ])
        if not point_of_sales:
            _logger.warning(
                'sync_model [measure_unit] | company=%d | sin PV activos, usando fallback (0,0)',
                self.env.company.id,
            )
            from collections import namedtuple
            _FakePOS = namedtuple('FakePOS', ['codigo_sucursal', 'pos_siat_id'])
            point_of_sales = [_FakePOS(0, 0)]
        for pos_rec in point_of_sales:
            pos = pos_rec.pos_siat_id
            sucursal = pos_rec.codigo_sucursal
            labels = service.sync_measure_unit(sucursal, pos)
            lista = labels.get('listaCodigos', [])
            _logger.info('=== SIAT siat_measure_unit | pos=%s | total registros=%s | primeros 3=%s',
                         pos, len(lista), lista[:3])
            self._sync_model(lista, pos)

    def _sync_model(self, data, pos):
        """Synchronize Measure Units from SIAT on the database."""
        existing = set(
            self.with_context(active_test=False)
            .search([('company_id', '=', self.env.company.id)])
            .mapped('code')
        )
        new_records = []
        seen = set()
        for item in data:
            code = str(item['codigoClasificador'])
            if code not in existing and code not in seen:
                seen.add(code)
                new_records.append({
                    'code': code,
                    'description': item['descripcion'],
                    'pos_id': pos,
                    'active': True,
                    'company_id': self.env.company.id,
                })
        if new_records:
            self.create(new_records)
            _logger.info('New measure units created: %s', len(new_records))