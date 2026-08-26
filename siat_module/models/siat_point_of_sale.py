import traceback
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..services.service_siat_operations import ServiceSiatOperations
from ..services.service_siat_sync import ServiceSiatSync
import logging

_logger = logging.getLogger(__name__)


def _get_pos_types(self):
    data = [('0', '-- Tipo Punto de Venta --')]
    try:
        res = self.env['siat.pos_type'].search([])
        if res is None:
            raise UserError(_("Debe sincronizar los datos con el SIAT"))
        for pos in res:
            data.append((str(pos['code']), pos['description']))
    except Exception as e:
        _logger.error('ERROR _get_pos_types: %s', str(e))
    return data


class SiatPointOfSale(models.Model):
    _name = 'siat.point_of_sale'
    _description = 'Punto de venta SIAT'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    siat_branch = fields.Many2one(
        'siat.branch',
        string='Sucursal',
        required=False,
    )
    codigo_sucursal = fields.Integer(
        string='Código Sucursal',
        default=0,
        help='Código de sucursal ante el SIAT (branch_code). '
             'Se llena automáticamente al sincronizar.',
    )
    name = fields.Char(size=256, required=True, string='Nombre Punto de Venta')
    descripcion = fields.Char(size=256, required=False, string='Descripción', default='')
    pos_type = fields.Selection(_get_pos_types, default='0', required=True, string='Tipo Punto de Venta')
    pos_siat_id = fields.Integer(string='Nro')
    point_of_sale_code = fields.Integer(
        string='Código PV',
        related='pos_siat_id',
        store=False,
        readonly=True,
    )
    cuis = fields.Char(string='CUIS POS', default='', required=False)
    valid_for = fields.Date(string='Fecha Vigencia', required=False)
    active = fields.Boolean('Active', default=True)

    def get_all_pos_cufd(self):
        for pos in self.search([]):
            pos.get_cufd()

    @api.model_create_multi
    def create(self, vals_list):
        service = ServiceSiatOperations(self.env)
        new_vals_list = []
        for vals in vals_list:
            if 'pos_siat_id' not in vals and vals.get('pos_type') not in (None, '', '0'):
                sucursal = vals.get('codigo_sucursal', 0)
                descripcion = vals.get('descripcion', '') or ''
                res = service.registrar_puntoventa(
                    sucursal, int(vals['pos_type']), vals['name'], descripcion
                )
                if not res or not res.get('transaccion'):
                    mensajes = res.get('mensajesList', []) if res else []
                    detalle = '; '.join([
                        m.get('descripcion', str(m)) for m in mensajes
                    ]) if mensajes else 'Sin respuesta del SIAT'
                    raise UserError(_(
                        'El SIAT rechazó el registro del Punto de Venta: %s'
                    ) % detalle)
                codigo_pv = res['codigoPuntoVenta']
                vals['pos_siat_id'] = codigo_pv
                vals['_needs_cuis_cufd'] = (sucursal, codigo_pv)
                _logger.info(
                    'create | PV registrado en SIAT | sucursal=%d pv=%d nombre=%s',
                    sucursal, codigo_pv, vals['name']
                )
            new_vals_list.append(vals)
        records = super().create([
            {k: v for k, v in vals.items() if not k.startswith('_')}
            for vals in new_vals_list
        ])
        for record, vals in zip(records, new_vals_list):
            if '_needs_cuis_cufd' not in vals:
                continue
            sucursal, codigo_pv = vals['_needs_cuis_cufd']
            try:
                company_env = record.with_company(record.company_id).env
                svc = ServiceSiatOperations(company_env)
                cuis_res = svc.sync_cuis(sucursal, codigo_pv)
                if cuis_res and cuis_res.get('codigo'):
                    record.write({
                        'cuis': cuis_res['codigo'],
                        'valid_for': cuis_res.get('fechaVigencia'),
                    })
                    _logger.info(
                        'create | CUIS obtenido | sucursal=%d pv=%d cuis=%s',
                        sucursal, codigo_pv, cuis_res['codigo']
                    )
                else:
                    _logger.warning(
                        'create | No se pudo obtener CUIS | sucursal=%d pv=%d',
                        sucursal, codigo_pv
                    )
                svc.sync_cufd(sucursal, codigo_pv, 1)
                _logger.info(
                    'create | CUFD obtenido | sucursal=%d pv=%d',
                    sucursal, codigo_pv
                )
            except Exception:
                _logger.error(
                    'create | Error obteniendo CUIS/CUFD para PV %d | %s',
                    codigo_pv, traceback.format_exc()
                )
        return records

    def sync_model(self, sucursal=None, service=None):
        """
        Llamado por el botón JS 'Sincronizar' (sin argumentos) y también
        internamente con sucursal específica.
        - Sin argumentos → itera todas las sucursales de la company activa.
        - Con sucursal   → sincroniza solo esa sucursal.
        """
        if not isinstance(service, ServiceSiatOperations):
            service = ServiceSiatOperations(self.env)
        company = service.company or self.env.company
        company_env = self.with_company(company).env

        if sucursal is None:
            # Llamado desde el botón JS — sincroniza todas las sucursales
            branches = company_env['siat.branch'].search([
                ('company_id', '=', company.id)
            ])
            sucursales = [b.branch_code for b in branches] if branches else [0]
            for cod in sucursales:
                self._sync_sucursal(cod, service, company, company_env)
        else:
            self._sync_sucursal(sucursal, service, company, company_env)

    def _sync_sucursal(self, sucursal, service, company, company_env):
        try:
            res = service.consulta_puntos_venta(sucursal)
            if not res or not res.get('transaccion'):
                mensajes = res.get('mensajesList', [{'descripcion': 'Error desconocido'}]) if res else []
                codigos = {m.get('codigo') for m in mensajes}
                _logger.warning(
                    '_sync_sucursal | sucursal=%d | Error SIAT: %s', sucursal, mensajes
                )
                if 982 in codigos and sucursal == 0:
                    # SIAT dice que este NIT no tiene ningún PV registrado todavía.
                    # Configuración inicial: registramos el PV 0 / Casa Matriz de una,
                    # para poder facturar de inmediato sin intervención manual.
                    self._auto_register_pv0(service, company, company_env, sucursal)
                return
            lista_siat = res.get('listaPuntosVentas', [])
            if isinstance(lista_siat, dict):
                lista_siat = [lista_siat]
            self._sync_pos_data(lista_siat, company, company_env, sucursal)
        except Exception:
            _logger.error(
                '_sync_sucursal | sucursal=%d | %s', sucursal, traceback.format_exc()
            )

    def _auto_register_pv0(self, service, company, company_env, sucursal):
        """Configuración inicial: garantiza que exista Sucursal 0 (solo local,
        SIAT no tiene endpoint para registrar sucursales) y Punto de Venta 0
        (registrado de verdad en SIAT vía registroPuntoVenta, igual que si se
        creara desde el botón 'Nuevo'). Solo actúa si aún no existe ninguno;
        una vez registrado, SIAT deja de devolver el error 982 y este método
        no se vuelve a ejecutar para esa sucursal.
        """
        try:
            branch_rec = company_env['siat.branch'].search([
                ('company_id', '=', company.id),
                ('branch_code', '=', sucursal),
            ], limit=1)
            if not branch_rec:
                branch_rec = company_env['siat.branch'].create({
                    'company_id':  company.id,
                    'branch_code': sucursal,
                    'name':        'Casa Matriz' if sucursal == 0 else f'Sucursal {sucursal}',
                })
                _logger.info(
                    '_auto_register_pv0 | sucursal=%d | Sucursal local creada id=%d',
                    sucursal, branch_rec.id
                )

            pv_exists = company_env['siat.point_of_sale'].search([
                ('company_id', '=', company.id),
                ('codigo_sucursal', '=', sucursal),
            ], limit=1)
            if pv_exists:
                _logger.info(
                    '_auto_register_pv0 | sucursal=%d | Ya existe un PV local (id=%d), no se auto-registra otro',
                    sucursal, pv_exists.id
                )
                return

            pos_type_code = self._resolve_default_pos_type(company_env, company)
            record = company_env['siat.point_of_sale'].create({
                'company_id':      company.id,
                'name':            f'{company.name} / Casa Matriz',
                'descripcion':     'PV auto-registrado en configuración inicial',
                'pos_type':        pos_type_code,
                'codigo_sucursal': sucursal,
                'siat_branch':     branch_rec.id,
            })
            _logger.info(
                '_auto_register_pv0 | sucursal=%d | PV registrado en SIAT OK | '
                'pos_siat_id=%d pos_type=%s',
                sucursal, record.pos_siat_id, pos_type_code
            )
        except Exception:
            _logger.error(
                '_auto_register_pv0 | sucursal=%d | %s', sucursal, traceback.format_exc()
            )

    def _resolve_default_pos_type(self, company_env, company):
        """Elige el tipo de PV a usar en el auto-registro. Busca uno cuya
        descripción sugiera 'Casa Matriz' / punto físico estándar; si no
        encuentra nada parecido, usa el primero disponible del catálogo
        sincronizado (siat.pos_type) y lo deja registrado en el log para
        que se pueda corregir manualmente si no es el correcto.
        """
        pos_types = company_env['siat.pos_type'].search([
            ('company_id', '=', company.id)
        ], order='code asc')
        if not pos_types:
            _logger.warning(
                '_resolve_default_pos_type | company=%d | catálogo siat.pos_type vacío, '
                'usando "1" como último recurso', company.id
            )
            return '1'
        for pt in pos_types:
            desc = (pt.description or '').upper()
            if 'MATRIZ' in desc or 'FISIC' in desc or 'PRINCIPAL' in desc:
                return str(pt.code)
        chosen = pos_types[0]
        _logger.warning(
            '_resolve_default_pos_type | company=%d | no se encontró tipo tipo '
            '"Casa Matriz"/"Físico" en el catálogo, usando el primero disponible: '
            'code=%s descripcion=%s — VERIFICAR que sea el correcto',
            company.id, chosen.code, chosen.description
        )
        return str(chosen.code)

    @api.model
    def _sync_pos_data(self, data, company, company_env, sucursal=0):
        current_company_id = company.id
        pos_types = company_env['siat.pos_type'].search([
            ('company_id', '=', current_company_id)
        ])
        branch_rec = company_env['siat.branch'].search([
            ('company_id', '=', current_company_id),
            ('branch_code', '=', sucursal),
        ], limit=1)
        # Nota: el fallback que creaba un PV 0 "local" (sin registrarlo en
        # SIAT) fue eliminado — ese registro fantasma es justo lo que causaba
        # que consultaPuntoVenta siguiera devolviendo 982. Si no hay PVs,
        # _sync_sucursal ya se encarga de registrar uno real vía
        # _auto_register_pv0 antes de que este método llegue a ejecutarse.
        existing_records = company_env['siat.point_of_sale'].search([
            ('company_id', '=', current_company_id),
            ('codigo_sucursal', '=', sucursal),
        ])
        set_siat_ids = {0}
        for item in data:
            codigo_siat = int(item['codigoPuntoVenta'])
            set_siat_ids.add(codigo_siat)
            record = company_env['siat.point_of_sale'].search([
                ('pos_siat_id', '=', codigo_siat),
                ('codigo_sucursal', '=', sucursal),
                ('company_id', '=', current_company_id),
            ], limit=1)
            siat_type_desc = str(item.get('tipoPuntoVenta', ''))
            ptype_code = '0'
            for pt in pos_types:
                if str(pt.code) == siat_type_desc or pt.description == siat_type_desc:
                    ptype_code = str(pt.code)
                    break
            vals = {
                'name':            item.get('nombrePuntoVenta', f'POS {codigo_siat}'),
                'pos_type':        ptype_code,
                'active':          True,
                'company_id':      current_company_id,
                'codigo_sucursal': sucursal,
                'siat_branch':     branch_rec.id if branch_rec else False,
            }
            if record:
                record.write(vals)
            else:
                vals['pos_siat_id'] = codigo_siat
                company_env['siat.point_of_sale'].create(vals)
        to_deactivate = existing_records.filtered(
            lambda r: r.pos_siat_id not in set_siat_ids
        )
        if to_deactivate:
            to_deactivate.write({'active': False})
        _logger.info(
            '_sync_pos_data | sucursal=%d | company=%d | procesados=%d | desactivados=%d',
            sucursal, current_company_id, len(set_siat_ids), len(to_deactivate),
        )
        return True

    def sync_cuis(self):
        self.ensure_one()
        company_env = self.with_company(self.company_id).env
        service_sync = ServiceSiatSync(company_env)
        res = service_sync.sync_cuis(self.codigo_sucursal, self.pos_siat_id)
        if not res or not res.get('codigo'):
            raise UserError(_('No se pudo obtener CUIS para el POS.'))
        self.write({'cuis': res['codigo'], 'valid_for': res['fechaVigencia']})
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   _('Éxito'),
                'message': _('CUIS obtenido para %s.') % self.name,
                'sticky':  False,
                'next':    {'type': 'ir.actions.act_window_close'},
            },
        }

    def delete_pos(self):
        for record in self:
            company_env = record.with_company(record.company_id).env
            service = ServiceSiatOperations(company_env)
            service.borrar_puntoventa(record.id)

    def get_cufd(self):
        for record in self:
            company_env = record.with_company(record.company_id).env
            service = ServiceSiatOperations(company_env)
            try:
                cuis_res = service.sync_cuis(record.codigo_sucursal, record.pos_siat_id)
                if cuis_res and cuis_res.get('codigo'):
                    record.write({
                        'cuis': cuis_res['codigo'],
                        'valid_for': cuis_res.get('fechaVigencia'),
                    })
            except Exception:
                _logger.warning(
                    'get_cufd | No se pudo renovar CUIS | sucursal=%d pv=%d',
                    record.codigo_sucursal, record.pos_siat_id
                )
            service.sync_cufd(record.codigo_sucursal, record.pos_siat_id, 1)