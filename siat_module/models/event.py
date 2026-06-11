import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from ..libsiat import constants as siat_constants
from ..services.service_siat_events import ServiceSiatEvents

_logger = logging.getLogger(__name__)


def _get_pos(self):
    res = self.env['siat.point_of_sale'].search(
        [('company_id', '=', self.env.company.id), ('active', '=', True)],
        order='pos_siat_id',
    )
    return [(f'T{r.pos_siat_id}', r.name) for r in res]

def _get_events(self):
    res = self.env['siat.significant_event'].search(
        [('company_id', '=', self.env.company.id)],
        order='code',
    )
    return [(r.code, r.description) for r in res]

class Event(models.Model):
    _name        = 'siat.event'
    _description = 'SIAT Significant Event'
    _order       = 'fecha_inicio desc'
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    evento_id        = fields.Selection(_get_events, string='Evento',          required=True)
    sucursal_id      = fields.Integer(string='Sucursal',                        required=True, default=0)
    point_of_sale_id = fields.Selection(_get_pos,    string='Punto de Venta',  required=True)
    pos_aux_text             = fields.Char(compute='_compute_pos', store=False)
    codigo_reception         = fields.Char(size=256)
    descripcion              = fields.Char(size=256)
    fecha_inicio             = fields.Datetime(required=True)
    fecha_fin                = fields.Datetime()
    cufd                     = fields.Char(size=256)
    cufd_evento              = fields.Char(size=256, required=True)
    cufd_selection           = fields.Many2one(
        'siat.cufd_code',
        string='Selección CUFD',
        domain="[('point_of_sale_id', '=', pos_aux_text)]",
    )
    codigo_recepcion_paquete = fields.Char(size=512)
    estado_recepcion         = fields.Char(size=64)
    status                   = fields.Char(size=64, required=True)
    data                     = fields.Text()
    last_invoices_count      = fields.Integer(default=0)
    invoices = fields.One2many('siat.invoice', 'evento_id', string='Facturas')
    packages = fields.One2many('siat.package', 'event_id', string='Paquetes')

    @api.depends('point_of_sale_id')
    def _compute_pos(self):
        for record in self:
            record.pos_aux_text = (
                record.point_of_sale_id[1:] if record.point_of_sale_id else False
            )

    @api.onchange('point_of_sale_id')
    def _onchange_point_of_sale_id(self):
        self.cufd_selection = False

    @api.onchange('cufd_selection')
    def _onchange_cufd_selection(self):
        for record in self:
            record.cufd_evento = (
                record.cufd_selection.cufd_code if record.cufd_selection else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        service   = ServiceSiatEvents(self.env)
        processed = [self._validate_and_enrich(v, service) for v in vals_list]
        _logger.info(
            'siat.event.create | company=%s | records=%d',
            self.env.company.id,
            len(processed),
        )
        return super().create(processed)

    def _validate_and_enrich(self, vals: dict, service) -> dict:
        vals = dict(vals)
        vals.setdefault('company_id', self.env.company.id)
        vals['status'] = siat_constants.EventStatus.STATUS_OPEN
        pos_raw    = vals.get('point_of_sale_id') or ''
        sucursal   = int(vals.get('sucursal_id') or 0)
        pos_digits = pos_raw[1:] if isinstance(pos_raw, str) and pos_raw.startswith('T') else pos_raw
        puntoventa = int(pos_digits) if pos_digits else 0
        if sucursal < 0:
            raise UserError('Código de sucursal inválido.')
        if puntoventa < 0:
            raise UserError('Código de punto de venta inválido.')
        if not vals.get('fecha_inicio'):
            raise UserError('La fecha de inicio del evento es obligatoria.')
        evento_id = int(vals.get('evento_id') or 0)
        if evento_id <= 0:
            raise UserError('Código de evento inválido.')
        vals['sucursal_id'] = sucursal
        if service.evento_activo(sucursal, puntoventa):
            raise UserError(
                f'Ya existe un evento activo para la sucursal {sucursal} / PV {puntoventa}.'
            )
        cufd_evento = service.resolver_cufd_evento(
            evento_id   = evento_id,
            sucursal    = sucursal,
            puntoventa  = puntoventa,
            fecha_fin   = vals.get('fecha_fin'),
            cufd_manual = vals.get('cufd_evento'),
        )
        vals['cufd_evento'] = cufd_evento
        _logger.debug(
            'siat.event._validate_and_enrich | sucursal=%d pv=%d evento=%d cufd=%s',
            sucursal, puntoventa, evento_id, cufd_evento,
        )
        return vals

    def get_pending_invoices(self):
        self.ensure_one()
        return self.env['siat.invoice'].search([
            ('evento_id', '=', self.id),
            '|',
            ('siat_id', '=', False),
            ('siat_id', '=', ''),
        ])

    def get_packages(self, rebuild=False):
        self.ensure_one()
        if self.packages and not rebuild:
            return self.packages
        self.packages.unlink()
        groups = self.env['siat.invoice'].read_group(
            domain=[
                ('evento_id',    '=',  self.id),
                ('tipo_emision', '=',  str(siat_constants.TIPO_EMISION_OFFLINE)),
            ],
            fields=['codigo_documento_sector', 'tipo_factura_documento', 'id:count'],
            groupby=['codigo_documento_sector', 'tipo_factura_documento'],
            lazy=False,
        )
        new_packages = self.env['siat.package']
        for g in groups:
            if not g.get('id_count'):
                continue
            pkg = self.env['siat.package'].create({
                'event_id':        self.id,
                'invoice_type':    g['tipo_factura_documento'],
                'sector_document': g['codigo_documento_sector'],
                'status':          siat_constants.PackageStatus.STATUS_OPEN,
            })
            new_packages |= pkg
        new_packages._mark_invoices()
        _logger.info(
            'siat.event.get_packages | event=%d | packages=%d',
            self.id, len(new_packages),
        )
        return new_packages

    def get_cufd_evento_record(self):
        self.ensure_one()
        return (
            self.env['siat.cufd_code'].search(
                [('cufd_code', '=', self.cufd_evento)], limit=1
            ) or None
        )

    def get_cufd_evento(self):
        """Alias retrocompatible: retorna el record `siat.cufd_code` asociado
        al CUFD del evento. Delega a `get_cufd_evento_record` para no duplicar
        la lógica del search por code.
        """
        self.ensure_one()
        return self.get_cufd_evento_record()

    def action_close(self):
        service = ServiceSiatEvents(self.env)
        result  = None
        for record in self:
            _logger.info(
                'siat.event.action_close | event=%d company=%d',
                record.id, record.company_id.id,
            )
            if not record.get_pending_invoices():
                service.void(record.id)
            else:
                result = service.close(record.id)
        return result

    def action_verify(self):
        service = ServiceSiatEvents(self.env)
        result  = None
        for record in self:
            _logger.info(
                'siat.event.action_verify | event=%d company=%d',
                record.id, record.company_id.id,
            )
            result = service.verify_event_reception(record.id)
        return result

    def action_void(self):
        service = ServiceSiatEvents(self.env)
        for record in self:
            _logger.info(
                'siat.event.action_void | event=%d company=%d',
                record.id, record.company_id.id,
            )
            if record.get_pending_invoices():
                raise UserError(
                    f'Imposible anular el evento #{record.id}: '
                    'contiene facturas pendientes de confirmación con el SIAT. '
                    'Cierre el evento primero.'
                )
            service.void(record.id)