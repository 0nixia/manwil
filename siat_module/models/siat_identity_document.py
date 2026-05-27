from odoo import models, fields
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatIdentityDocuments(models.Model):
    _name = 'siat.identity_document'
    _description = 'Modelo para almacenar la lista de documentos de Identidad(sync)'
    _rec_name = 'description'

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
            'El código de documento de identidad ya existe para esta compañía.',
        )
    ]

    def _compute_display_name(self):
        for record in self:
            record.display_name = record.description

    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain += [('description', operator, name)]
        return self._search(domain, limit=limit, order=order)

    def sync_model(self, service=None):
        """Get the list of Identity Documents from SIAT (once per company)."""
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
        labels = service.sync_identity_document(sucursal, pos)
        self.__sync_model(labels['listaCodigos'], pos)

    def __sync_model(self, data, pos):
        """Synchronize ID Documents from SIAT on the database."""
        new_id_documents = []
        company_id = self.env.company.id
        existing_codes = set(
            self.env['siat.identity_document']
            .search([('company_id', '=', company_id)])
            .mapped('code')
        )
        for id_document in data:
            code = str(id_document['codigoClasificador'])
            if code not in existing_codes:
                new_id_documents.append({
                    'code': code,
                    'description': id_document['descripcion'],
                    'pos_id': pos,
                    'company_id': company_id,
                })
                existing_codes.add(code)
        if new_id_documents:
            self.env['siat.identity_document'].create(new_id_documents)
            _logger.info('New ID documents created: %s', new_id_documents)