import json
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class Package(models.Model):
    _name        = 'siat.package'
    _description = 'SIAT Event Package'
    _order       = 'id'

    event_id         = fields.Many2one('siat.event', ondelete='cascade', index=True, required=True)
    invoice_type     = fields.Integer(required=True)
    sector_document  = fields.Integer(required=True)
    reception_code   = fields.Char(size=128)
    reception_status = fields.Char(size=64)
    reception_date   = fields.Datetime()
    status           = fields.Char(size=32)
    data             = fields.Text()
    invoices         = fields.One2many('siat.invoice', 'package_id', string='Facturas')

    def _mark_invoices(self):
        for pkg in self:
            invoices = self.env['siat.invoice'].search([
                ('evento_id',               '=', pkg.event_id.id),
                ('codigo_documento_sector', '=', pkg.sector_document),
                ('tipo_factura_documento',  '=', pkg.invoice_type),
            ])
            if invoices:
                invoices.write({'package_id': pkg.id})
            _logger.debug(
                'Package._mark_invoices | pkg=%d event=%d sector=%d type=%d linked=%d',
                pkg.id, pkg.event_id.id,
                pkg.sector_document, pkg.invoice_type, len(invoices),
            )

    def get_pending_invoices(self):
        self.ensure_one()
        return self.env['siat.invoice'].search([
            ('package_id', '=', self.id),
            '|',
            ('siat_id', '=', False),
            ('siat_id', '=', ''),
        ])

    def get_data(self) -> dict:
        self.ensure_one()
        if not self.data:
            return {}
        try:
            return json.loads(self.data)
        except (ValueError, TypeError):
            _logger.warning(
                'Package.get_data | pkg=%d | invalid JSON — returning {}', self.id
            )
            return {}