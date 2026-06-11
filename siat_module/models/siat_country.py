from odoo import models, fields
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatCountries(models.Model):
    _name = 'siat.country'
    _description = 'Modelo para almacenar la lista de Paises(sync)'

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
            'El código de país ya existe para esta compañía.',
        )
    ]

    def sync_model(self, service=None):
        """Get the list of Countries from SIAT (once per company)."""
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
        values = service.sync_country(sucursal, pos)
        self.__sync_model(values['listaCodigos'], pos)

    def __sync_model(self, data, pos):
        """Synchronize Countries from SIAT on the database."""
        new_countries = []
        company_id = self.env.company.id
        existing_codes = set(
            self.env['siat.country']
            .search([('company_id', '=', company_id)])
            .mapped('code')
        )
        for country in data:
            code = str(country['codigoClasificador'])
            if code not in existing_codes:
                new_countries.append({
                    'code': code,
                    'description': country['descripcion'],
                    'pos_id': pos,
                    'company_id': company_id,
                })
                existing_codes.add(code)
        if new_countries:
            self.env['siat.country'].create(new_countries)
            _logger.info('New countries created: %s', new_countries)