import logging
import datetime
import os
import time
import json
import random
from ..libsiat import constants as siat_constants
from ..libsiat.classes.siat_exception import SiatException
from ..libsiat.services.service_codigos import ServiceCodigos
from ..libsiat.services.service_sincronizacion import ServiceSincronizacion
from .service_siat import ServiceSiat

_logger = logging.getLogger(__name__)


class ServiceSiatSync(ServiceSiat):

	def __init__(self, env, cfg_override=None):
		if not env:
			raise ValueError("ServiceSiatSync requires a valid env")
		super().__init__(env)
		cfg = cfg_override if cfg_override else self.getConfig()
		self._serviceCodes = ServiceCodigos()
		self._serviceCodes.setConfig(cfg)
		self._serviceSync = ServiceSincronizacion()
		self._serviceSync.setConfig(cfg)
	
	def getSiatServiceCodes(self):
		return self._serviceCodes
	
	def file_needs_sync(self, filename):
		if os.path.isfile(filename) is False:
			return True
		HOUR_SECONDS = 3600
		DAY_SECONDS = HOUR_SECONDS * 24
		modification_time = os.path.getmtime(filename)
		modification_datetime = datetime.datetime.fromtimestamp(modification_time)
		unix_modification_time = int(time.mktime(modification_datetime.timetuple()))
		unix_current_time = int(time.mktime(datetime.datetime.now().timetuple()))
		time_diff = unix_current_time - unix_modification_time
		if time_diff > DAY_SECONDS:
			return True	
		return False
	
	def write_json_file(self, dicData, filename):
		json_str = json.dumps(dicData, default=str)
		with open(filename, 'w', encoding='utf-8') as f_out:
			f_out.write( json_str )
			
	def sync_cuis(self, sucursal=0, puntoventa=0):
		_logger.info(
			'sync_cuis | company=%d branch=%d pos=%d',
			self.env.company.id, sucursal, puntoventa,
		)
		CiusModel = self.env['siat.cuis_code']
		latest = CiusModel.get_latest(sucursal, puntoventa)
		if latest and not latest.is_expired():
			_logger.info(
				'sync_cuis | company=%d branch=%d pos=%d | '
				'reutilizando CUIS id=%d (vigente hasta %s)',
				self.env.company.id, sucursal, puntoventa,
				latest.id, latest.valid_until,
			)
			return {
				'codigo': latest.cuis_code,
				'transaccion': latest.transaction,
				'fechaVigencia': latest.valid_until,
				'mensajesList': latest.message_list,
			}
		_logger.info(
			'sync_cuis | company=%d branch=%d pos=%d | '
			'solicitando nuevo CUIS al SIN',
			self.env.company.id, sucursal, puntoventa,
		)
		cuis_response = self._serviceCodes.getCuis(sucursal, puntoventa)
		if cuis_response is None or (
			cuis_response.get('transaccion') is False
			and cuis_response.get('codigo') is None
		):
			raise SiatException(cuis_response)
		new_cuis = self._persist_cuis(cuis_response, sucursal, puntoventa)
		_logger.info(
			'sync_cuis | company=%d branch=%d pos=%d | '
			'CUIS creado id=%d vigente hasta %s',
			self.env.company.id, sucursal, puntoventa,
			new_cuis.id, new_cuis.valid_until,
		)
		return {
			'codigo': new_cuis.cuis_code,
			'transaccion': new_cuis.transaction,
			'fechaVigencia': new_cuis.valid_until,
			'mensajesList': new_cuis.message_list,
		}

	def _persist_cuis(self, cuis_response, sucursal, puntoventa):
		import datetime as _dt
		raw_date = cuis_response.get('fechaVigencia')
		if raw_date is None:
			valid_until = _dt.datetime.now() + _dt.timedelta(hours=48)
			_logger.warning(
				'_persist_cuis | branch=%d pos=%d | fechaVigencia ausente, se asigna 48h',
				sucursal, puntoventa,
			)
		elif hasattr(raw_date, 'astimezone'):
			valid_until = (
				raw_date
				.astimezone(_dt.timezone.utc)
				.replace(tzinfo=None)
			)
		else:
			try:
				valid_until = _dt.datetime.strptime(raw_date, siat_constants.DATETIME_FORMAT)
			except (TypeError, ValueError):
				valid_until = _dt.datetime.now() + _dt.timedelta(hours=48)
				_logger.error(
					'_persist_cuis | branch=%d pos=%d | '
					'fechaVigencia en formato inesperado %r → se asigna 48h',
					sucursal, puntoventa, raw_date,
				)
		vals = {
			'company_id': self.env.company.id,
			'branch_id': sucursal,
			'point_of_sale_id': puntoventa,
			'cuis_code': cuis_response.get('codigo'),
			'transaction': cuis_response.get('transaccion', False),
			'valid_until': valid_until,
			'message_list': str(cuis_response.get('mensajesList', '')),
			'service_response': str(cuis_response),
		}
		_logger.debug('_persist_cuis | vals=%s', vals)
		record = self.env['siat.cuis_code'].create(vals)
		_logger.info(
			'_persist_cuis | cuis_id=%d company=%d branch=%d pos=%d vigencia=%s',
			record.id, self.env.company.id, sucursal, puntoventa, valid_until,
		)
		return record

	def get_cufd_from_siat(self, branch=0, point_of_sale=0):
		cuis_latest = self.env['siat.cuis_code'].get_latest(branch, point_of_sale)
		if cuis_latest is None or cuis_latest.is_expired():
			_logger.info(
				'get_cufd_from_siat | branch=%d pos=%d | CUIS vencido o ausente → renovando',
				branch, point_of_sale,
			)
			self.env['siat.cuis_code'].sync_model()
			cuis_latest = self.env['siat.cuis_code'].get_latest(branch, point_of_sale)
		if not cuis_latest:
			raise SiatException({'mensajesList': [
				{'descripcion': f'No se pudo obtener CUIS para branch={branch} pos={point_of_sale}'}
			]})
		cufd_response = self._serviceCodes.get_cufd(branch, point_of_sale, cuis_latest.cuis_code)
		if not cufd_response or (
			cufd_response.get('transaccion') is False
			and cufd_response.get('codigo') is None
		):
			raise SiatException(cufd_response)
		return self._persist_cufd(cufd_response, branch, point_of_sale)

	def sync_cufd(self, sucursal=0, puntoventa=0, renew=0):
		_logger.info(
			'sync_cufd | company=%d branch=%d pos=%d renew=%d',
			self.env.company.id, sucursal, puntoventa, renew,
		)
		if renew == 0:
			CufdModel = self.env['siat.cufd_code']
			if hasattr(CufdModel, 'get_valid'):
				latest = CufdModel.get_valid(sucursal, puntoventa)
			else:
				latest = CufdModel.get_latest(sucursal, puntoventa)
				if latest and latest.is_expired():
					_logger.warning(
						'sync_cufd | CUFD id=%d vencido (ended=%s) → renovando',
						latest.id, latest.ended_date,
					)
					latest = None
			if latest:
				_logger.info(
					'sync_cufd | company=%d branch=%d pos=%d | '
					'reutilizando CUFD id=%d (vigente hasta %s)',
					self.env.company.id, sucursal, puntoventa,
					latest.id, latest.ended_date,
				)
				return latest
		cuis = self.sync_cuis(sucursal, puntoventa)
		self._serviceCodes.cuis = cuis['codigo']
		cufd_response = self._serviceCodes.get_cufd(sucursal, puntoventa)
		if not cufd_response or (
			cufd_response.get('transaccion') is False
			and cufd_response.get('codigo') is None
		):
			raise SiatException(cufd_response)
		new_cufd = self._persist_cufd(cufd_response, sucursal, puntoventa)
		_logger.info(
			'sync_cufd | company=%d branch=%d pos=%d | '
			'CUFD creado id=%d vigente hasta %s',
			self.env.company.id, sucursal, puntoventa,
			new_cufd.id, new_cufd.ended_date,
		)
		return new_cufd


	def _persist_cufd(self, cufd_response, sucursal, puntoventa):
		import datetime as _dt
		raw_date = cufd_response.get('fechaVigencia')
		if raw_date is None:
			fecha_vigencia = None
			_logger.warning(
				'_persist_cufd | branch=%d pos=%d | fechaVigencia ausente en respuesta SIN',
				sucursal, puntoventa,
			)
		elif hasattr(raw_date, 'astimezone'):
			fecha_vigencia = (
				raw_date
				.astimezone(_dt.timezone.utc)
				.replace(tzinfo=None)
			)
		else:
			fecha_vigencia = None
			_logger.error(
				'_persist_cufd | branch=%d pos=%d | '
				'fechaVigencia de tipo inesperado %r → se guarda None',
				sucursal, puntoventa, type(raw_date),
			)
		vals = {
			'company_id':        self.env.company.id,
			'branch_id':         sucursal,
			'point_of_sale_id':  puntoventa,

			'cufd_code':         cufd_response.get('codigo'),
			'control_code':      cufd_response.get('codigoControl'),
			'address':           cufd_response.get('direccion'),
			'ended_date':        fecha_vigencia,
			'message_list':      str(cufd_response.get('mensajesList', '')),
			'transaction':       cufd_response.get('transaccion', False),
			'service_response':  str(cufd_response),
		}
		_logger.debug(
			'_persist_cufd | vals=%s',
			{k: v for k, v in vals.items() if k != 'service_response'},
		)
		record = self.env['siat.cufd_code'].create(vals)
		_logger.info(
			'_persist_cufd | cufd_id=%d company=%d branch=%d pos=%d vigencia=%s',
			record.id, self.env.company.id, sucursal, puntoventa, fecha_vigencia,
		)
		return record

	def sync_measure_unit(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaUnidadMedida(branch, point_of_sale)
		return res

	def sync_currency_type(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTipoMoneda(branch, point_of_sale)
		return res
	
	def sync_identity_document(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTipoDocumentoIdentidad(branch, point_of_sale)
		return res
		
	def sync_product_service(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarListaProductosServicios(branch, point_of_sale)
		return res
		
	def sync_payment_type(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTipoMetodoPago(branch, point_of_sale)
		return res
		
	def sync_activities(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarActividades(branch, point_of_sale)
		return res
		
	def sync_document_sector(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarListaActividadesDocumentoSector(branch, point_of_sale)
		return res
		
	def sync_legends(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarListaLeyendasFactura(branch, point_of_sale)
		return res
		
	def sync_significant_events(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaEventosSignificativos(
			branch, point_of_sale)
		return res
		
	def sync_cancellation_reason(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaMotivoAnulacion(branch, point_of_sale)
		return res
		
	def sync_type_documents_sector(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTipoDocumentoSector(branch, point_of_sale)
		return res
		
	def sync_emission_type(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTipoEmision(branch, point_of_sale)
		return res
		
	def sync_pos_type(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTipoPuntoVenta(branch, point_of_sale)
		return res
		
	def sync_invoice_type(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTiposFactura(branch, point_of_sale)
		return res
		
	def sync_room_type(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		res = self._serviceSync.sincronizarParametricaTipoHabitacion(branch, point_of_sale)
		return res

	def sync_fecha_hora(self, sucursal=0, puntoventa=0):
		cuis = self.sync_cuis(sucursal, puntoventa)
		self._serviceSync.cuis = cuis['codigo']
		data = self._serviceSync.sincronizarFechaHora(sucursal, puntoventa)
		return data
		
	def sync_service_message(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		data = self._serviceSync.sincronizarListaMensajesServicios(branch, point_of_sale)
		return data

	def sync_country(self, branch=0, point_of_sale=0):
		cuis_code = self.env['siat.cuis_code'].get_latest(branch, point_of_sale).cuis_code
		self._serviceSync.cuis = cuis_code
		data = self._serviceSync.sincronizarParametricaPaisOrigen(branch, point_of_sale)
		return data
	
	def leyenda_aleatoria(self, codigo_actividad):
		random_legend = self.env['siat.invoice_label'].get_random_legend(codigo_actividad)
		if random_legend:
			_logger.debug("Leyenda en DB: %s", random_legend.description)
			return random_legend.description
		else:
			data = self.sync_legends()
			total_items = len( data['listaLeyendas'] )
			index = int( random.randint(0, total_items - 1) )
			leyendas = []
			for item in data['listaLeyendas']:
				if item['codigoActividad'] == codigo_actividad:
					leyendas.append( item )
			total_items = len( leyendas )
			if total_items <= 0:
				return data['listaLeyendas'][index]['descripcionLeyenda']
			index = int( random.randint(0, total_items - 1) )
			return leyendas[index]['descripcionLeyenda']
		
	def buscar_evento(self, codigo_evento):
		eventos = self.sync_significant_events()
		evento = None
		for item in eventos['listaCodigos']:
			if item['codigoClasificador'] == codigo_evento:
				evento = item
				break
		return evento

	def buscar_unidad_medida(self, codigo_unidad_medida: int):
		unidad = self.env['siat.measure_unit'].search([('code', '=', codigo_unidad_medida)], limit=1)
		if unidad:
			return unidad.description
		unidades = self.sync_measure_unit()
		unidad = None
		for item in unidades['listaCodigos']:
			if item['codigoClasificador'] == codigo_unidad_medida:
				unidad = item
				break
		return unidad['descripcion']