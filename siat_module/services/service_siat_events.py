# -*- coding: utf-8 -*-
"""
ServiceSiatEvents
=================
Capa de servicio que contiene TODA la lógica SIAT de eventos:

  • evento_activo / resolver_cufd_evento  — consultas y CUFD lookup
  • close                                 — registro ante el SIN + envío de paquetes
  • verify_event_reception / verify_package — verificación de recepción
  • void                                  — anulación de eventos

El modelo siat.event solo valida campos y llama a estos métodos.
El modelo siat.package es un contenedor ORM puro (sin lógica de negocio SIAT).
"""
import json
import logging
from datetime import datetime, timezone
from odoo.exceptions import UserError
from .service_siat_sync import ServiceSiatSync
from ..libsiat.classes.siat_factory import SiatFactory
from ..libsiat import functions as siat_functions
from ..libsiat import constants as siat_constants
from ..libsiat.services.service_operaciones import ServiceOperaciones
from ..libsiat.classes.siat_exception import SiatException
from . import service_invoices
from ..models.siat_utils import get_siat_employee_config

_logger = logging.getLogger(__name__)


class ServiceSiatEvents(ServiceSiatSync):
    """
    All SIAT event operations.

    Construction: ServiceSiatEvents(self.env)
    The base class (ServiceSiat) raises ValueError if env is falsy,
    so no extra guard is needed here.
    """

    def __init__(self, env):
        super().__init__(env)
        _logger.debug(
            'ServiceSiatEvents.init | company=%s (%d)',
            self.env.company.name, self.env.company.id,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Queries / lookups  (called by model.create and by action buttons)
    # ─────────────────────────────────────────────────────────────────────────

    def evento_activo(self, sucursal: int = 0, puntoventa: int = 0):
        """
        Return the open siat.event for (sucursal, puntoventa) or None.
        Company isolation is handled by Odoo record rules on siat.event.
        Alias eventoActivo kept for backwards-compat with existing callers.
        """
        event = self.env['siat.event'].search([
            ('sucursal_id',      '=',     sucursal),
            ('point_of_sale_id', '=',     f'T{puntoventa}'),
            ('status',           'ilike', siat_constants.EventStatus.STATUS_OPEN),
        ], limit=1)

        found = bool(event)
        _logger.debug(
            'evento_activo | company=%d sucursal=%d pv=%d found=%s',
            self.env.company.id, sucursal, puntoventa, found,
        )
        return event if found else None

    # Backwards-compatible alias
    eventoActivo = evento_activo

    def resolver_cufd_evento(
        self,
        evento_id: int,
        sucursal: int,
        puntoventa,
        fecha_fin=None,
        cufd_manual: str = None,
    ) -> str:
        """
        Resolve the CUFD that must be used for a new event.

        - Eventos 1-4 (contingencia corta):  sincroniza con el SIAT y devuelve el CUFD activo.
        - Eventos 5-7 (contingencia larga):  usa el cufd_manual provisto por el usuario.

        Returns the CUFD string; raises UserError if it cannot be resolved or validated.
        """
        if evento_id <= 4:
            current_cufd = self.sync_cufd(sucursal, puntoventa)
            cufd_value   = current_cufd.cufd_code
            _logger.debug(
                'resolver_cufd_evento | evento=%d | cufd_from_siat=%s',
                evento_id, cufd_value,
            )
        else:
            if not fecha_fin:
                raise UserError(
                    'Debe indicar una fecha fin para el evento de contingencia.'
                )
            cufd_value = cufd_manual
            _logger.debug(
                'resolver_cufd_evento | evento=%d | cufd_manual=%s',
                evento_id, cufd_value,
            )

        if not cufd_value:
            raise UserError('CUFD para el evento inválido.')

        if not self.env['siat.cufd_code'].get_by_code(cufd_value):
            raise UserError(f'El CUFD "{cufd_value}" no existe o es inválido.')

        return cufd_value

    # ─────────────────────────────────────────────────────────────────────────
    # Core operations
    # ─────────────────────────────────────────────────────────────────────────

    def close(self, event_id: int):
        """
        Close an event end-to-end:
          1. Register the significant event with the SIN (idempotent).
          2. Group pending offline invoices into packages.
          3. Send each package to SIAT.
          4. Verify reception status.
        """
        event = self._get_event(event_id)

        if siat_constants.EventStatus.STATUS_CLOSED in str(event.status):
            raise UserError('El evento ya se encuentra cerrado.')

        evento_siat = self.env['siat.significant_event'].search(
            [('code', '=', event.evento_id)], limit=1
        )
        if not evento_siat:
            raise UserError(
                'El código de evento no existe; no se puede registrar el evento.'
            )

        if not event.get_pending_invoices():
            event.write({'status': siat_constants.EventStatus.STATUS_CLOSED})
            _logger.info('close | event=%d | no pending invoices — closed directly', event_id)
            return event

        pos_siat = int(event.point_of_sale_id[1:])
        cuis     = self.sync_cuis(event.sucursal_id, pos_siat)
        cufd     = self.sync_cufd(event.sucursal_id, pos_siat)

        # Step 1 — register significant event (skip if already done)
        if not event.codigo_reception:
            event = self._register_significant_event(event, evento_siat, cuis, cufd, pos_siat)

        # Step 2+3 — build packages and send them
        self._send_packages(event, cuis, cufd)

        # Step 4 — verify
        self.verify_event_reception(event.id)

        _logger.info('close | event=%d | completed', event_id)
        return event

    def verify_event_reception(self, event_id: int):
        """
        Poll SIAT for the validation status of all packages in this event.
        Marks the event CLOSED once every package is validated.
        """
        event = self._get_event(event_id)

        if not event.codigo_reception:
            raise UserError(
                'El evento no tiene código de recepción; no se puede verificar.'
            )

        all_closed = True
        for pkg in event.get_packages():
            pkg = self.verify_package(pkg)
            if pkg.status != siat_constants.PackageStatus.STATUS_CLOSED:
                all_closed = False
                self._notify(
                    'warning',
                    'Confirmación Paquete',
                    'Paquete pendiente de validación. '
                    'Revise el estado del paquete en el detalle del evento.',
                )

        if all_closed:
            event.write({'status': siat_constants.EventStatus.STATUS_CLOSED})
            self._notify('success', 'Confirmación Paquete', 'Paquetes recibidos y validados.')
            _logger.info(
                'verify_event_reception | event=%d | all packages closed', event_id
            )

        return event

    def verify_package(self, package):
        """
        Ask SIAT for the validation result of a single package.
        Updates package.status to CLOSED and marks invoices when SIAT replies VALIDADA.
        """
        if not package.reception_code:
            raise UserError(
                f'El paquete #{package.id} no tiene código de recepción; '
                'no se puede validar.'
            )

        if package.status == siat_constants.PackageStatus.STATUS_CLOSED:
            _logger.debug('verify_package | pkg=%d already closed', package.id)
            return package

        pos_siat = int(package.event_id.point_of_sale_id[1:])
        cuis     = self.sync_cuis(package.event_id.sucursal_id, pos_siat)
        cufd     = self.sync_cufd(package.event_id.sucursal_id, pos_siat, renew=0)

        svc = SiatFactory.obtenerServicioFacturacion(
            self.getConfig(),
            cuis.get('codigo'),
            cufd.cufd_code,
            cufd.cufd.control_code,
        )
        svc.debug = True

        res = svc.validacionRecepcionPaqueteFactura(
            0,
            pos_siat,
            package.reception_code,
            package.invoice_type,
            package.sector_document,
        )

        validated  = res.get('codigoDescripcion') == 'VALIDADA'
        new_status = (
            siat_constants.PackageStatus.STATUS_CLOSED
            if validated
            else siat_constants.PackageStatus.STATUS_PENDING
        )

        data                = package.get_data()
        data['reception']   = res

        package.write({
            'reception_status': res.get('codigoDescripcion'),
            'status':           new_status,
            'data':             json.dumps(data),
        })

        if validated:
            package.invoices.write({'siat_id': package.reception_code})

        _logger.info(
            'verify_package | pkg=%d | new_status=%s | validated=%s',
            package.id, new_status, validated,
        )
        return package

    def void(self, event_id: int):
        """Mark an event VOID (local only, no SIN call required)."""
        event = self._get_event(event_id)

        if event.status == siat_constants.EventStatus.STATUS_VOID:
            raise UserError('El evento ya está anulado.')

        event.write({'status': siat_constants.EventStatus.STATUS_VOID})
        _logger.info('void | event=%d', event_id)
        return event

    # ─────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_event(self, event_id: int):
        """Browse a siat.event by id and raise UserError if not found."""
        event = self.env['siat.event'].browse(event_id)
        if not event.exists():
            raise UserError(f'El evento #{event_id} no existe.')
        return event

    def _register_significant_event(self, event, evento_siat, cuis, cufd, pos_siat):
        """
        POST the significant event to the SIN and persist the reception code.
        Returns the (now-updated) event record.
        """
        evento_id_int = int(event.evento_id)
        if evento_id_int < 5:
            fecha_fin = siat_functions.sb_siat_localize_datetime(datetime.now())
        else:
            fecha_fin = siat_functions.sb_siat_localize_datetime(event.fecha_fin)

        f_inicio = siat_functions.sb_siat_localize_datetime(event.fecha_inicio)

        svc_ops = ServiceOperaciones()
        svc_ops.setConfig(self.getConfig())
        svc_ops.cuis  = cuis.get('codigo')
        svc_ops.cufd  = cufd.cufd_code
        svc_ops.debug = True

        res = svc_ops.registroEventoSignificativo(
            evento_siat.code,
            evento_siat.description,
            event.cufd_evento,
            f_inicio,
            fecha_fin,
            event.sucursal_id,
            pos_siat,
        )

        _logger.info(
            '_register_significant_event | event=%d | transaccion=%s | codigo=%s',
            event.id,
            res.get('transaccion'),
            res.get('codigoRecepcionEventoSignificativo'),
        )

        if not res.get('codigoRecepcionEventoSignificativo') or res.get('transaccion') is False:
            raise SiatException(res)

        event.write({
            'cufd':             cufd.cufd_code,
            'status':           siat_constants.EventStatus.STATUS_PENDING,
            'fecha_fin':        fecha_fin.astimezone(timezone.utc).replace(tzinfo=None),
            'codigo_reception': res['codigoRecepcionEventoSignificativo'],
        })
        return event

    def _send_packages(self, event, cuis, cufd):
        """
        Convert pending offline invoices into SIAT XML objects and send each
        package group to the SIN.
        """
        svc_invoices = service_invoices.ServiceInvoices(self.env)
        svc_fact     = SiatFactory.obtenerServicioFacturacion(
            self.getConfig(),
            cuis.get('codigo'),
            cufd.cufd_code,
            cufd.cufd.control_code,
        )
        svc_fact.debug   = True
        is_cafc_event    = str(event.evento_id) in ('5', '6', '7')

        for pkg in event.get_packages():
            if pkg.status == siat_constants.PackageStatus.STATUS_CLOSED:
                _logger.debug('_send_packages | pkg=%d already closed — skip', pkg.id)
                continue

            siat_invoices = []
            for inv in pkg.get_pending_invoices():
                siat_inv = svc_invoices.invoiceToSiatInvoice(inv)
                _logger.debug(
                    '_send_packages | pkg=%d invoice=%d | xml_len=%d',
                    pkg.id, inv.id, len(siat_inv.toXmlString()),
                )
                siat_invoices.append(siat_inv)

            if not siat_invoices:
                _logger.debug('_send_packages | pkg=%d no pending invoices', pkg.id)
                continue

            res = svc_fact.recepcionPaqueteFactura(
                siat_invoices,
                event.codigo_reception,
                siat_constants.TIPO_EMISION_OFFLINE,
                pkg.invoice_type,
                svc_fact.cafc if is_cafc_event else None,
            )

            _logger.info(
                '_send_packages | event=%d pkg=%d | codigoEstado=%s',
                event.id, pkg.id, res.get('codigoEstado'),
            )
            self._process_package_response(pkg, res)

    def _process_package_response(self, pkg, res: dict):
        """
        Persist the SIAT reception response for a package.
        Sends a bus notification to the current user.
        """
        accepted = res.get('codigoEstado') == 901  # 901 = PENDIENTE DE VALIDACIÓN

        data = pkg.get_data()
        if accepted:
            data['reception'] = res
            pkg.write({
                'status':           siat_constants.PackageStatus.STATUS_PENDING,
                'reception_code':   res.get('codigoRecepcion'),
                'reception_status': res.get('codigoDescripcion'),
                'reception_date':   datetime.now(),
                'data':             json.dumps(data),
            })
            self._notify(
                'success',
                'Confirmación Paquete',
                'Paquete recibido — pendiente de validación.',
            )
        else:
            data['reception_error'] = res
            pkg.write({'data': json.dumps(data)})
            self._notify(
                'danger',
                'Error de Paquete',
                f'Error en recepción: {res.get("codigoDescripcion", "sin descripción")}',
            )

        _logger.info(
            '_process_package_response | pkg=%d | accepted=%s | codigoEstado=%s',
            pkg.id, accepted, res.get('codigoEstado'),
        )

    def _notify(self, ntype: str, title: str, message: str):
        """
        Deliver a bus notification to the current user.
        Failures are caught and logged so they never interrupt the main flow.
        """
        try:
            employee, _pos_rec, _pos_code, _sucursal, _login = get_siat_employee_config(self.env)
            partner = employee.work_contact_id if employee else self.env.user.partner_id
            self.env['bus.bus']._sendone(
                partner,
                'simple_notification',
                {
                    'type': ntype,
                    'title': title,
                    'message': message,
                }
            )
        except Exception:
            _logger.warning(
                '_notify | failed to send bus notification | type=%s title=%s',
                ntype, title, exc_info=True,
            )