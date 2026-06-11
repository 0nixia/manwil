import pytz
from datetime import datetime, timedelta

from odoo import http, _
from odoo.http import Controller

from .service_siat import ServiceSiat
from .service_siat_sync import ServiceSiatSync
from ..libsiat.classes.siat_factory import SiatFactory
from ..libsiat.services.service_operaciones import ServiceOperaciones
from ..libsiat import functions as siat_functions
from ..libsiat import constants as siat_constants


class ServiceSiatOperations(ServiceSiatSync):
	
	def __init__(self, env):
		super().__init__(env)
		self.serviceOperaciones = ServiceOperaciones()

	@property
	def operaciones(self):
		self.serviceOperaciones.setConfig(self.getConfig())
		return self.serviceOperaciones
		
	def nitValido(self, nit):
		service_codes = self.getSiatServiceCodes()
		cuis = self.sync_cuis(0, 0)
		service_codes.cuis = cuis['codigo']
		return service_codes.verificarNit(nit)
			
	def registrarEvento(self, data: dict):
		ops = self.operaciones

		cuis = self.sync_cuis(data['sucursal'], data['puntoventa'])
		cufd = self.sync_cufd(data['sucursal'], data['puntoventa'])

		ops.cuis = cuis['codigo']
		ops.cufd = cufd.cufd_code
		ops.debug = True

		return ops.registroEventoSignificativo(
			data['evento_id'],
			data['descripcion'],
			data['cufd_evento'],
			data['fecha_inicio'],
			data['fecha_fin'],
			data['sucursal'],
			data['puntoventa']
		)

	def consulta_puntos_venta(self, sucursal=0):
		ops = self.operaciones

		cuis = self.sync_cuis(sucursal)
		ops.cuis = cuis['codigo']

		return ops.consultaPuntoVenta(sucursal)

	def registrar_puntoventa(self, codigo_sucursal: int, tipo: int, nombre: str, descripcion: str):
		ops = self.operaciones

		cuis = self.sync_cuis(codigo_sucursal)
		ops.cuis = cuis['codigo']

		return ops.registroPuntoVenta(
			codigo_sucursal, tipo, nombre, descripcion
		)

	def borrar_puntoventa(self, pid: int):
		ops = self.operaciones

		pos = self.env['siat.point_of_sale'].search([
			('id', '=', pid),
			('company_id', '=', self.env.company.id)
		], limit=1)

		if not pos:
			raise Exception('El punto de venta no existe o no pertenece a la compañía activa')

		cuis = self.sync_cuis(pos.codigo_sucursal)
		ops.cuis = cuis['codigo']

		res = ops.cierrePuntoVenta(pos.codigo_sucursal, pos.pos_siat_id)

		if res['transaccion'] is False:
			mensajes = res.get('mensajesList', [])
			detalle = '; '.join([m.get('descripcion', str(m)) for m in mensajes]) if mensajes else str(res)
			raise Exception(f'SIAT rechazó el cierre del PV {pos.pos_siat_id}: {detalle}')

		pos.write({'active': False})
		return res
			
