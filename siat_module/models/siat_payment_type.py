from odoo import models, fields
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatPaymentTypes(models.Model):
    _name = 'siat.payment_type'
    _description = 'Modelo para almacenar la lista de Tipos de Pago(sync)'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    code = fields.Integer(string="Código")
    description = fields.Char(string="Descripción")
    pos_id = fields.Integer()

    _sql_constraints = [
        (
            'code_company_unique',
            'unique(code, company_id)',
            'El código de tipo de pago ya existe para esta compañía.',
        )
    ]

    def _compute_display_name(self):
        for record in self:
            record.display_name = record.description

    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        ctx = self._context
        if 'order_display' in ctx:
            order = ctx['order_display']
        if name:
            domain += [('description', operator, name)]
        return self._search(domain, limit=limit, order=order)

    def sync_model(self, service=None):
        """Get the list of Payment Types from SIAT (once per company)."""
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
        labels = service.sync_payment_type(sucursal, pos)
        self.__sync_model(labels['listaCodigos'], pos)

    def __sync_model(self, data, pos):
        """Synchronize Payment Types from SIAT on the database."""
        new_payment_types = []
        company_id = self.env.company.id
        existing_codes = set(
            self.env['siat.payment_type']
            .search([('company_id', '=', company_id)])
            .mapped('code')
        )
        for payment_type in data:
            code = int(payment_type['codigoClasificador'])
            if code not in existing_codes:
                new_payment_types.append({
                    'code': code,
                    'description': payment_type['descripcion'],
                    'pos_id': pos,
                    'company_id': company_id,
                })
                existing_codes.add(code)
        if new_payment_types:
            self.env['siat.payment_type'].create(new_payment_types)
            _logger.info('New payment types created: %s', new_payment_types)