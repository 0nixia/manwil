from odoo import models, fields, api
from ..services.service_siat_sync import ServiceSiatSync
import random
import logging

_logger = logging.getLogger(__name__)


class SiatInvoiceLabels(models.Model):
    _name = 'siat.invoice_label'
    _description = 'Modelo para almacenar la lista de Leyendas de Factura (sync)'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True)
    code = fields.Char(string="Código Actividad", required=True, size=8)
    description = fields.Char(string="Descripción", required=True)
    pos_id = fields.Integer()

    @api.model
    def get_random_legend(self, code):
        legend_ids = self.search([('code', '=', code)]).ids
        if legend_ids:
            random_id = random.choice(legend_ids)
            return self.browse(random_id)
        return None

    def sync_model(self, service=None):
        """Get the list of Invoice Labels from SIAT for each Point of Sale."""
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
            labels = service.sync_legends(sucursal, pos)
            self.__sync_model(labels['listaLeyendas'], pos)

    def __sync_model(self, data, pos):
        """Synchronize Invoice Labels from SIAT on the database."""
        new_invoice_labels = []
        invoice_labels_from_siat = data
        invoice_labels_from_system = self.env['siat.invoice_label'].search([]).mapped(
            lambda current_invoice_label: (current_invoice_label.code, current_invoice_label.company_id.id)
        )
        for invoice_label in invoice_labels_from_siat:
            if (str(invoice_label['codigoActividad']), self.env.company.id) not in invoice_labels_from_system:
                new_invoice_labels.append({
                    'code': invoice_label['codigoActividad'],
                    'description': invoice_label['descripcionLeyenda'],
                    'pos_id': pos,
                    'company_id': self.env.company.id
                })
        if new_invoice_labels:
            self.env['siat.invoice_label'].create(new_invoice_labels)
            _logger.info('New invoice labels created: %s', new_invoice_labels)