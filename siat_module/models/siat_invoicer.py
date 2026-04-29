import logging

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from ..libsiat import constants as siat_constants
from datetime import datetime
from ..services.service_siat_events import ServiceSiatEvents
from ..services.service_invoices import ServiceInvoices
from ..libsiat import functions as siat_functions
import requests

_logger = logging.getLogger(__name__)

class SiatInvoicer(models.Model):
    _name        = 'siat.invoicer'
    _description = 'Facturador manual SIAT'
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    def _default_pos(self):
        return self.env['siat.point_of_sale'].search([
            ('company_id', '=', self.env.company.id),
            ('active',     '=', True),
        ], limit=1)

    pos_ids = fields.Many2one(
        'siat.point_of_sale',
        string='Punto de Venta',
        required=True,
        default=_default_pos,
    )

    tipo_documento = fields.Many2one('siat.identity_document', 'Documento de Identidad')
    nit_ci         = fields.Char('NIT/CI')
    complement     = fields.Char('Complemento')
    nombre_razon   = fields.Char('Nombre o Razón Social')
    correo         = fields.Char('Correo Electrónico')
    readonly_razon = fields.Boolean('readonly razon', default=False)

    productos_ids = fields.One2many(
        'siat.invoicer.product', 'invoicer_id', string='Productos'
    )

    metodo_pago    = fields.Many2one('siat.payment_type', 'Método de Pago')
    except_nit     = fields.Selection([('1', 'SI'), ('2', 'NO')], string='Exceptuar NIT')
    pago_efectivo  = fields.Float('Monto en Efectivo',    required=False)
    gift_card_code = fields.Char('Número de Gift Card',   required=False)
    pago_gift_card = fields.Float('Monto con Gift Card',  required=False, default=0)
    num_tarjeta    = fields.Char('Número Tarjeta',        required=False)
    pago_tarjeta   = fields.Float('Monto con Tarjeta',    required=False, default=0)

    descuento          = fields.Float('Descuento Adicional')
    total_discount_sum = fields.Float(
        string='Precio Total',
        compute='_compute_total_discount_sum',
        store=True,
    )

    date             = fields.Datetime('Fecha Factura (contingencia)')
    event_nro_factura = fields.Char('Nro de Factura (contingencia)')

    has_payment   = fields.Boolean(compute='_compute_has_efectivo')
    has_gift_card = fields.Boolean(compute='_compute_has_gift')
    has_card      = fields.Boolean(compute='_compute_has_card')
    has_check     = fields.Boolean(compute='_compute_has_check')
    has_check_gif = fields.Boolean(compute='_compute_has_gift_check')
    has_event     = fields.Integer('Evento Activo', compute='_compute_event_cont')
    show_complement    = fields.Boolean(compute='_compute_tipo_documento')
    show_validate_nit  = fields.Boolean(compute='_compute_show_nit')
    active_event_lab   = fields.Char('Evento Activo detectado', compute='_compute_event_lab')

    siat_connection_ok = fields.Boolean(
        string='Conexión SIAT activa',
        default=False,
        store=True,
        help='Actualizado manualmente con el botón "Verificar Conexión SIAT".',
    )

    siat_invoice_id = fields.Many2one('siat.invoice')

    @api.depends('productos_ids.price_total', 'descuento')
    def _compute_total_discount_sum(self):
        for record in self:
            total = sum(record.productos_ids.mapped('price_total'))
            record.total_discount_sum = total - record.descuento

    @api.depends('tipo_documento')
    def _compute_tipo_documento(self):
        for record in self:
            record.show_complement = (
                record.tipo_documento and record.tipo_documento.code in '1'
            )

    @api.depends('tipo_documento')
    def _compute_show_nit(self):
        for record in self:
            record.show_validate_nit = (
                record.tipo_documento and record.tipo_documento.code in '5'
            )

    @api.depends('metodo_pago')
    def _compute_has_efectivo(self):
        payment_types = self.env['siat.payment_type'].search([
            ('description', 'ilike', 'EFECTIVO'),
            ('code', '!=', 1),
        ])
        efectivo_codes = set(payment_types.mapped('code'))
        for record in self:
            record.has_payment = (
                bool(record.metodo_pago)
                and record.metodo_pago.code in efectivo_codes
            )

    @api.depends('metodo_pago')
    def _compute_has_gift_check(self):
        for record in self:
            record.has_check_gif = (
                bool(record.metodo_pago) and record.metodo_pago.code == 27
            )

    @api.depends('metodo_pago')
    def _compute_has_gift(self):
        payment_types = self.env['siat.payment_type'].search([
            ('description', 'ilike', 'CARD'),
            ('code', '!=', 27),
        ])
        card_codes = set(payment_types.mapped('code'))
        for record in self:
            record.has_gift_card = (
                bool(record.metodo_pago)
                and record.metodo_pago.code in card_codes
            )

    @api.depends('metodo_pago')
    def _compute_has_card(self):
        payment_types = self.env['siat.payment_type'].search([
            ('description', 'ilike', 'TARJETA'),
            ('code', '!=', 2),
        ])
        tarjeta_codes = set(payment_types.mapped('code'))
        for record in self:
            record.has_card = (
                bool(record.metodo_pago)
                and record.metodo_pago.code in tarjeta_codes
            )

    @api.depends('metodo_pago')
    def _compute_has_check(self):
        for record in self:
            record.has_check = (
                bool(record.metodo_pago) and record.metodo_pago.code == 2
            )

    @api.depends('pos_ids')
    def _compute_event_cont(self):
        """
        Detecta si hay un evento de contingencia activo para el PV.
        Solo consulta la BD — sin llamadas al SIN.
        """
        service = ServiceSiatEvents(self.env)
        for record in self:
            if not record.pos_ids:
                record.has_event = 0
                continue
            evento = service.evento_activo(
                record.pos_ids.codigo_sucursal,
                record.pos_ids.pos_siat_id,
            )
            record.has_event = int(evento.evento_id) if evento else 0

    @api.depends('has_event', 'pos_ids')
    def _compute_event_lab(self):
        """
        Construye el label descriptivo del evento activo.
        Solo lee de BD — sin llamadas al SIN.
        """
        service = ServiceSiatEvents(self.env)
        for record in self:
            if not record.has_event:
                record.active_event_lab = False
                continue
            record.except_nit = '1'
            evento = service.evento_activo(
                record.pos_ids.codigo_sucursal,
                record.pos_ids.pos_siat_id,
            )
            if not evento:
                record.active_event_lab = False
                continue
            sig_event = self.env['siat.significant_event'].search(
                [('code', '=', record.has_event)], limit=1
            )
            inicio = siat_functions.sb_siat_localize_datetime(
                evento.fecha_inicio
            ).strftime('%d-%m-%Y %H:%M')
            fin = (
                siat_functions.sb_siat_localize_datetime(
                    evento.fecha_fin
                ).strftime('%d-%m-%Y %H:%M')
                if evento.fecha_fin else ''
            )
            desc = sig_event.description if sig_event else f'Evento {record.has_event}'
            record.active_event_lab = f'{desc}  {inicio} — {fin}'.strip()

    @api.onchange('metodo_pago')
    def _onchange_metodo_pago(self):
        if self.metodo_pago:
            self.pago_efectivo  = 0
            self.num_tarjeta    = ''
            self.pago_tarjeta   = 0
            self.gift_card_code = ''
            self.pago_gift_card = 0

    @api.onchange('tipo_documento')
    def _onchange_tipo_documento(self):
        if self.tipo_documento:
            self.nit_ci      = ''
            self.nombre_razon = ''
            self.correo      = ''
            self.complement  = ''

    @api.onchange('nit_ci')
    def _onchange_nit_ci(self):
        if not self.nit_ci:
            return
        self.nombre_razon  = ''
        self.readonly_razon = False
        nit = self.nit_ci
        if nit == siat_constants.NIT_CONSULADO:
            self.nombre_razon = 'Consulado'
        elif nit == siat_constants.NIT_CONTROL_TRIB:
            self.nombre_razon  = 'Control Tributario'
            self.readonly_razon = True
        elif nit == siat_constants.NIT_VENTAS_MENORES:
            self.nombre_razon  = 'VENTAS MENORES DEL DÍA'
            self.readonly_razon = True
        elif nit == siat_constants.NIT_SIN_NOMBRE:
            self.nombre_razon = 'Sin nombre'

    def action_check_connection(self):
            """
            Verifica la conexión con el SIN y actualiza siat_connection_ok.
            Gestiona apertura/cierre de eventos de contingencia según el resultado.
            Llamar desde botón en la vista.
            """
            self.ensure_one()
            service    = ServiceSiatEvents(self.env)
            has_conn   = self._call_siat_url()
            sucursal   = self.pos_ids.codigo_sucursal if self.pos_ids else 0
            puntoventa = self.pos_ids.pos_siat_id     if self.pos_ids else 0

            self.siat_connection_ok = has_conn

            if not self.pos_ids:
                return self._notify(
                    'warning', 'Sin Punto de Venta',
                    'Seleccione un punto de venta antes de verificar la conexión.'
                )

            evento_activo = service.evento_activo(sucursal, puntoventa)

            if has_conn:
                if evento_activo and evento_activo.evento_id == '2':
                    evento_activo.action_close()
                return self._notify(
                    'success', 'Conexión SIAT',
                    'El servicio del SIN está accesible.'
                )
            else:
                if evento_activo is None:
                    self.env['siat.event'].create({
                        'point_of_sale_id': f'T{puntoventa}',
                        'sucursal_id':      sucursal,
                        'fecha_inicio':     datetime.now(),
                        'evento_id':        '2',
                        'descripcion':      'INACCESIBILIDAD AL SERVICIO WEB DE LA ADMINISTRACIÓN TRIBUTARIA',
                        'company_id':       self.env.company.id,
                    })
                return self._notify(
                    'warning', 'Sin conexión SIAT',
                    'No se pudo contactar al servicio del SIN. Se registró un evento de contingencia.'
                )

    def action_simulate_offline(self):
        """
        Simula corte de internet creando un evento tipo 1.
        Solo para entornos de prueba/piloto.
        """
        self.ensure_one()
        if not self.pos_ids:
            raise UserError(_('Seleccione un punto de venta.'))

        sucursal   = self.pos_ids.codigo_sucursal
        puntoventa = self.pos_ids.pos_siat_id

        self.env['siat.event'].create({
            'point_of_sale_id': f'T{puntoventa}',
            'sucursal_id':      sucursal,
            'fecha_inicio':     datetime.now(),
            'evento_id':        '1',
            'descripcion':      'CORTE DEL SERVICIO DE INTERNET',
            'company_id':       self.env.company.id,
        })
        _logger.info(
            'action_simulate_offline | company=%d PV=%d | evento offline simulado',
            self.env.company.id, puntoventa,
        )
        return self._notify('warning', 'Offline simulado', 'Evento de corte de internet creado.')

    # ── Conexión ──────────────────────────────────────────────────────────────

    def _call_siat_url(self):
        """
        Verifica accesibilidad del SIN con timeout acotado.
        Solo debe llamarse desde action_check_connection() — nunca desde compute.
        """
        siat_url = (
            self.env['ir.config_parameter'].get_param('siat_config.url_siat')
            or 'https://pilotosiatservicios.impuestos.gob.bo/v2/FacturacionSincronizacion?wsdl'
        )
        try:
            response = requests.get(siat_url, timeout=5)
            return response.status_code == 200
        except Exception:
            _logger.warning('_call_siat_url | SIN inaccesible en %s', siat_url)
            return False

    # ── Validación NIT ────────────────────────────────────────────────────────

    def validate_nit(self):
        """
        Verifica el NIT ante el SIN y notifica al usuario.
        Usa la compañía del PV seleccionado para obtener el CUIS correcto.
        """
        self.ensure_one()
        if not self.pos_ids:
            raise UserError(_('Seleccione un punto de venta antes de verificar el NIT.'))

        # FIX: usar la compañía del PV, no la del env, para contexto correcto
        company_env = self.with_company(self.pos_ids.company_id).env
        service     = ServiceInvoices(company_env)

        service_codes = service.serviceSync.getSiatServiceCodes()
        cuis = service.serviceSync.sync_cuis(
            self.pos_ids.codigo_sucursal,
            self.pos_ids.pos_siat_id,
        )
        service_codes.cuis = cuis['codigo']
        res      = service_codes.verificarNit(self.nit_ci)
        msg_list = res['mensajesList'][0]

        self._buscar_nit_ci()
        self.except_nit = '2' if msg_list['codigo'] == 986 else '1'

        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type':    'success' if msg_list['codigo'] == 986 else 'warning',
                'title':   'Verificación NIT',
                'message': msg_list['descripcion'],
            },
        )

    def validate_doc(self):
        for record in self:
            return record._buscar_nit_ci()

    def _buscar_nit_ci(self):
        if not self.nit_ci:
            return
        cliente = self.env['siat.client'].search([
            ('ci',         '=', self.nit_ci),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if cliente:
            self.correo       = cliente.email
            self.nombre_razon = cliente.nombre_razon
            self.complement   = cliente.complemento

    # ── Facturar ──────────────────────────────────────────────────────────────

    def facturar(self):
        siat_client = self.env['siat.client']

        for record in self:
            # ── Validaciones previas ──────────────────────────────────────────
            if record.has_event in [5, 6, 7]:
                if not record.event_nro_factura:
                    raise ValidationError(_('Debe ingresar un número de factura para el evento.'))
                if not record.date:
                    raise ValidationError(_('Debe ingresar una fecha de factura para el evento.'))

            if record.total_discount_sum > siat_constants.LIMITE_VENTAS_MENORES and record.nit_ci == siat_constants.NIT_VENTAS_MENORES:
                raise ValidationError(_(
                    'Ventas menores (99003) deben ser inferiores a %.2f Bs.'
                ) % siat_constants.LIMITE_VENTAS_MENORES)

            if not record.metodo_pago:
                raise ValidationError(_('Debe seleccionar un método de pago.'))

            if record.has_payment or record.has_card or record.has_gift_card:
                total_pagado = (
                    record.pago_efectivo
                    + record.pago_tarjeta
                    + record.pago_gift_card
                )
                if round(total_pagado, 2) != round(record.total_discount_sum, 2):
                    raise ValidationError(_(
                        'Los pagos (%.2f Bs) deben coincidir con el Precio Total (%.2f Bs).'
                    ) % (total_pagado, record.total_discount_sum))

            if record.has_check_gif:
                record.pago_gift_card = record.total_discount_sum

            # ── Caché de clientes ─────────────────────────────────────────────
            client = siat_client.search([
                ('ci',         '=', record.nit_ci),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

            client_vals = {
                'nombre_razon': record.nombre_razon,
                'email':        record.correo,
                'complemento':  record.complement,
            }
            if client:
                client.write(client_vals)
            else:
                client = siat_client.create({
                    **client_vals,
                    'ci':         record.nit_ci,
                    'company_id': self.env.company.id,
                })

            # ── Construcción de invoiceData ───────────────────────────────────
            # FIX: usar la compañía del PV para el contexto correcto del servicio
            company_env = self.with_company(record.pos_ids.company_id).env
            service     = ServiceInvoices(company_env)

            invoiceData = {
                'codigo_documento_sector':  1,
                'codigo_sucursal':          record.pos_ids.codigo_sucursal if record.pos_ids else 0,
                'punto_venta':              record.pos_ids.pos_siat_id,
                'customer_id':              client.id,
                'customer':                 client.nombre_razon,
                'tipo_documento_identidad': record.tipo_documento.code,
                'nit_ruc_nif':              client.ci,
                'complemento': (
                    client.complemento
                    if record.tipo_documento.code == '1' and client.complemento
                    else None
                ),
                'codigo_metodo_pago':  record.metodo_pago.code,
                'numero_tarjeta':      record.num_tarjeta.replace(' ', '') if record.num_tarjeta else None,
                'total':               round(record.total_discount_sum, 2),
                'codigo_moneda':       1,
                'tipo_cambio':         1,
                'monto_giftcard':      record.pago_gift_card or 0,
                'discount':            record.descuento,
                'data':                {
                    'excepcion': (
                        0 if record.except_nit == '2'
                        or record.tipo_documento.code == '1'
                        else 1
                    )
                },
                'items':               [],
                'siat_num_invoice':    record.event_nro_factura,
                'siat_date_invoice':   record.date,
                'is_invoicer':         True,
            }

            # ── Líneas de producto ────────────────────────────────────────────
            for line in record.productos_ids:
                product = line.product_id
                homol   = product.product_tmpl_id.siat_current_homologation_id

                if not homol or not homol.siat_activity_id \
                        or not homol.siat_measure_id or not homol.siat_prod_id:
                    raise ValidationError(_(
                        'El producto "%s" no está homologado con el SIAT '
                        'para la compañía actual.'
                    ) % product.name)

                invoiceData['items'].append({
                    'product_id':          product.id,
                    'product_code':        product.default_code or '',
                    'product_name':        product.name,
                    'quantity':            line.quantity,
                    'unidad_medida':       homol.siat_measure_id.code,
                    'codigo_actividad':    homol.siat_activity_id.caeb,
                    'codigo_producto_sin': homol.siat_prod_id.code_prod,
                    'price': round(line.price_unit, 2),
                    'discount':            line.custom_discount,
                    'numero_serie':        '',
                    'numero_imei':         '',
                })

            # ── Envío al SIN ──────────────────────────────────────────────────
            try:
                invoice = service.create(invoiceData)
            finally:
                service.cleanup()

            if invoice is not None:
                record.siat_invoice_id = invoice.id
                _logger.info(
                    'facturar | company=%d PV=%d | factura SIAT id=%d nro=%s creada',
                    self.env.company.id,
                    record.pos_ids.pos_siat_id,
                    invoice.id,
                    invoice.invoice_number,
                )

        return {
            'type':      'ir.actions.act_window',
            'res_model': 'siat.invoicer',
            'view_mode': 'form',
            'view_type': 'form',
            'target':    'current',
            'context':   {},
        }

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _notify(self, notif_type, title, message):
        """Devuelve una acción de notificación cliente para mostrar al usuario."""
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'type':    notif_type,
                'title':   title,
                'message': message,
                'sticky':  False,
            },
        }


# =============================================================================
# SiatInvoicerProduct
# =============================================================================

class SiatInvoicerProduct(models.Model):
    _name        = 'siat.invoicer.product'
    _description = 'Líneas de producto del facturador SIAT'

    company_id = fields.Many2one(
        'res.company',
        related='invoicer_id.company_id',
        store=True,
        index=True,
    )
    invoicer_id    = fields.Many2one('siat.invoicer', 'Factura', ondelete='cascade')
    product_id     = fields.Many2one(
        'product.product',
        string='Producto',
        domain=lambda self: self._compute_product_domain(),
    )
    quantity       = fields.Integer(string='Cantidad', default=1)
    custom_discount = fields.Float(string='Descuento', default=0.0)
    price_unit     = fields.Float(string='Precio Unitario')
    price_total    = fields.Float(string='Precio Total', compute='_compute_price_total')

    def _compute_product_domain(self):
        company = self.env.company
        activities = self.env['siat.activity'].search([('company_id', '=', company.id)])
        if not activities:
            return [('id', '=', False)]
        return [('economic_activity', 'in', activities.ids)]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price

    @api.depends('price_unit', 'quantity', 'custom_discount')
    def _compute_price_total(self):
        for record in self:
            record.price_total = (
                (record.price_unit * record.quantity) - record.custom_discount
            )

    @api.onchange('custom_discount')
    def _onchange_custom_discount(self):
        for record in self:
            if record.custom_discount != 0 and record.price_total == 0:
                raise ValidationError(_(
                    'El producto "%s" no puede tener un descuento del 100%%.'
                ) % record.product_id.name)


# =============================================================================
# SiatClient
# =============================================================================

class SiatClient(models.Model):
    _name        = 'siat.client'
    _description = 'Caché de clientes del facturador SIAT'

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    ci            = fields.Char('CI/NIT')
    nombre_razon  = fields.Char('Nombre o Razón Social')
    email         = fields.Char('Correo')
    complemento   = fields.Char('Complemento')

    _sql_constraints = [
        (
            'unique_ci_company',
            'UNIQUE(ci, company_id)',
            'Ya existe un cliente con ese CI en esta compañía.',
        )
    ]