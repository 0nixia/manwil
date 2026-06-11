from odoo import models, fields, api
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


class SiatActivities(models.Model):
  _name = 'siat.activity'
  _description = 'Modelo para almacenar la lista de actividades (sync)'
  _rec_name = 'description'

  company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,)
  caeb = fields.Char(string="Código", required=True, size=8)
  description = fields.Char(string="Descripción", required=True)
  activity_type = fields.Char(string="Tipo Actividad", required=True, size=2)
  pos_id = fields.Integer()
  active = fields.Boolean('Active', default=True)
  _sql_constraints = [
      (
          'caeb_company_unique',
          'unique(caeb, company_id)',
          'El código CAEB ya existe para esta compañía.'
      )
  ]

  def _compute_display_name(self):
    for record in self:
      record.display_name = f"[{record.caeb}] {record.description}"

  @api.model
  def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
      domain = domain or []
      if name:
          domain = ['|', ('caeb', operator, name), ('description', operator, name)] + domain
      return self._search(domain, limit=limit, order=order)

  def sync_model(self, service=None):
    if service is None:
      service = ServiceSiatSync(self.env)
    point_of_sales = self.env['siat.point_of_sale'].search([
        ('company_id', '=', self.env.company.id),
        ('active', '=', True),
    ])
    if not point_of_sales:
      _logger.warning(
          'sync_model [activity] | company=%d | sin PV activos, usando fallback (0,0)',
          self.env.company.id,
      )
      from collections import namedtuple
      _FakePOS = namedtuple('FakePOS', ['codigo_sucursal', 'pos_siat_id'])
      point_of_sales = [_FakePOS(0, 0)]
    for pos_rec in point_of_sales:
      sucursal = pos_rec.codigo_sucursal
      pos = pos_rec.pos_siat_id
      try:
        activities = service.sync_activities(sucursal, pos)
        lista = activities.get('listaActividades', [])
        _logger.info('=== SIAT siat_activity | sucursal=%s pos=%s | total=%s',
                     sucursal, pos, len(lista))
        self._sync_model(lista, pos)
      except Exception as e:
        _logger.error('Error sincronizando actividades sucursal=%s pos=%s: %s', sucursal, pos, e)

  def _sync_model(self, data, pos):
    existing = set(
        self.with_context(active_test=False)
        .search([('company_id', '=', self.env.company.id)])
        .mapped('caeb')
    )
    new_records = []
    for item in data:
        code = item['codigoCaeb']

        if code not in existing:
            new_records.append({
                'caeb': code,
                'description': item['descripcion'],
                'activity_type': item['tipoActividad'],
                'pos_id': pos,
                'active': True,
                'company_id': self.env.company.id,
            })
    if new_records:
        self.create(new_records)
        _logger.info('New activities created: %s', len(new_records))