from odoo import models, fields
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatDocumentSector(models.Model):
    _name = 'siat.document_sector'
    _description = 'Modelo para almacenar la lista de Documentos de sector (sync)'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True)
    code_doc_sector = fields.Integer(string="Documento Sector", required=True)
    code_activity = fields.Char(string="Código Actividad", required=True, size=8)
    type_doc_sector = fields.Char(string="Tipo Documento Sector", required=True)
    pos_id = fields.Integer()

    def sync_model(self, service=None):
        """Get the list of Document Sectors from SIAT each Point of Sale."""
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
        for pos_rec in point_of_sales:
            pos = pos_rec.pos_siat_id
            sucursal = pos_rec.codigo_sucursal
            docs = service.sync_document_sector(sucursal, pos)
            self.__sync_model(docs['listaActividadesDocumentoSector'], pos)

    def __sync_model(self, data, pos):
        """Synchronize Document Sectors from SIAT on the database."""
        new_document_sectors = []
        document_sectors_from_siat = data
        document_sectors_from_system = self.env['siat.document_sector'].search([('company_id', '=', self.env.company.id)]).mapped(
            lambda current_document_sector: (
                current_document_sector.code_doc_sector,
                current_document_sector.code_activity,
                current_document_sector.type_doc_sector,
                current_document_sector.company_id.id)
        )
        for document_sector in document_sectors_from_siat:
            if (document_sector['codigoDocumentoSector'],
                 document_sector['codigoActividad'],
                 document_sector['tipoDocumentoSector'],
                 self.env.company.id) not in document_sectors_from_system:

                new_document_sectors.append({
                    'code_doc_sector': document_sector['codigoDocumentoSector'],
                    'code_activity': document_sector['codigoActividad'],
                    'type_doc_sector': document_sector['tipoDocumentoSector'],
                    'pos_id': pos,
                    'company_id': self.env.company.id
                })
        if new_document_sectors:
            self.env['siat.document_sector'].create(new_document_sectors)
            _logger.info('New document sectors created: %s', new_document_sectors)