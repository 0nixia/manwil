from odoo import models, fields, api
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatProductServices(models.Model):
    _name = 'siat.product_service'
    _description = 'Modelo para almacenar la lista de Productos y servicios(sync)'
    _rec_name = 'desc_prod'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,)
    code = fields.Char(string="Código Actividad")
    code_prod = fields.Char(string="Código Producto")
    desc_prod = fields.Char(string="Descripción Producto")
    pos_id = fields.Integer()
    active = fields.Boolean('Active', default=True)
    
    _sql_constraints = [
        (
            'product_service_unique',
            'unique(code, code_prod, company_id)',
            'El producto/servicio ya existe para esta compañía.'
        )
    ]

    def _compute_display_name(self):
        for record in self:
            record.display_name = record.desc_prod

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('code_prod', operator, name), ('desc_prod', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    def sync_model(self, service=None):
        """Get the list of Products and Services from SIAT for each Point of Sale."""
        if service is None:
            service = ServiceSiatSync(self.env)
        point_of_sales = self.env['siat.point_of_sale'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ])
        if not point_of_sales:
            _logger.warning(
                'sync_model [product_service] | company=%d | sin PV activos, usando fallback (0,0)',
                self.env.company.id,
            )
            from collections import namedtuple
            _FakePOS = namedtuple('FakePOS', ['codigo_sucursal', 'pos_siat_id'])
            point_of_sales = [_FakePOS(0, 0)]
        for pos_rec in point_of_sales:
            pos = pos_rec.pos_siat_id
            sucursal = pos_rec.codigo_sucursal
            labels = service.sync_product_service(sucursal, pos)
            lista = labels.get('listaCodigos', [])
            _logger.info('=== SIAT siat_product_service | pos=%s | total registros=%s | primeros 3=%s',
                         pos, len(lista), lista[:3])
            self._sync_model(lista, pos)

    def _sync_model(self, data, pos):   
        """Synchronize Products and Services from SIAT."""
        existing = set(
            self.with_context(active_test=False)
            .search([('company_id', '=', self.env.company.id)])
            .mapped(lambda r: (r.code, r.code_prod))
        )
        _logger.info(
            '=== siat_product_service._sync_model | company_id=%s | en BD=%s | recibidos de SIAT=%s',
            self.env.company.id, len(existing), len(data)
        )
        new_records = []
        seen = set()
        for item in data:
            key = (
                str(item['codigoActividad']),
                str(item['codigoProducto'])
            )
            if key not in existing and key not in seen:
                seen.add(key)
                new_records.append({
                    'code': key[0],
                    'code_prod': key[1],
                    'desc_prod': item['descripcionProducto'],
                    'pos_id': pos,
                    'active': True,
                    'company_id': self.env.company.id,
                })
        _logger.info(
            '=== siat_product_service._sync_model | a insertar=%s',
            len(new_records)
        )
        if new_records:
            self.create(new_records)
            _logger.info('New products/services created: %s', len(new_records))