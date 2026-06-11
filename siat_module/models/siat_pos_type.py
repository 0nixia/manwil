from odoo import models, fields
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatPosTypes(models.Model):
    _name = 'siat.pos_type'
    _description = 'Modelo para almacenar la lista de Tipos Punto de venta(sync)'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    code = fields.Char(string="Código")
    description = fields.Char(string="Descripción")
    pos_id = fields.Integer()

    _sql_constraints = [
        (
            'code_company_unique',
            'unique(code, company_id)',
            'El código ya existe para esta compañía.',
        )
    ]

    def sync_model(self, service=None):
        """Get the list of Tipos Punto de venta from SIAT (once per company)."""
        if service is None:
            service = ServiceSiatSync(self.env)
        point_of_sales = self.env['siat.point_of_sale'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ])
        if not point_of_sales:
            _logger.warning(
                'sync_model | company=%d | sin PV activos, usando fallback (0,0)',
                self.env.company.id,
            )
            from collections import namedtuple
            _FakePOS = namedtuple('FakePOS', ['codigo_sucursal', 'pos_siat_id'])
            point_of_sales = [_FakePOS(0, 0)]
        pos_rec = point_of_sales[0]
        pos = pos_rec.pos_siat_id
        sucursal = pos_rec.codigo_sucursal
        labels = service.sync_pos_type(sucursal, pos)
        self.__sync_model(labels['listaCodigos'], pos)

    def __sync_model(self, data, pos):
        """Synchronize Tipos Punto de venta from SIAT on the database."""
        new_records = []
        company_id = self.env.company.id
        existing_codes = set(
            self.env['siat.pos_type']
            .search([('company_id', '=', company_id)])
            .mapped('code')
        )
        for item in data:
            code = str(item['codigoClasificador'])
            if code not in existing_codes:
                new_records.append({
                    'code': code,
                    'description': item['descripcion'],
                    'pos_id': pos,
                    'company_id': company_id,
                })
                existing_codes.add(code)
        if new_records:
            self.env['siat.pos_type'].create(new_records)
            _logger.info('New Tipos Punto de venta created: %s', new_records)
