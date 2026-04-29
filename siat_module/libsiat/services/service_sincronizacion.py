from .service_siat import ServiceSiat
import sys

class ServiceSincronizacion(ServiceSiat):

	def __init__(self):
		super().__init__()
		self.wsdl = None

	def setConfig(self, data):
		super().setConfig(data)
		if self.ambiente == 1:
			self.wsdl = 'https://siatrest.impuestos.gob.bo/v2/FacturacionSincronizacion?wsdl'
		else:
			self.wsdl = 'https://pilotosiatservicios.impuestos.gob.bo/v2/FacturacionSincronizacion?wsdl'
	
	def buildData(self, sucursal, puntoventa):
		return [{
			# 'SolicitudSincronizacion': {
				'codigoAmbiente' 	: self.ambiente,
				'codigoPuntoVenta'	: puntoventa,
				'codigoSistema'		: self.codigoSistema,
				'codigoSucursal'	: sucursal,
				'cuis'				: self.cuis,
				'nit'				: self.nit,
			#}
		}]
		
	def doCall(self, method, data=None):
		res = self.callAction(method, self.buildData())
		
		return res
		
	def sincronizarParametricaMotivoAnulacion(self, sucursal, puntoventa):
		res = self.callAction('sincronizarParametricaMotivoAnulacion', self.buildData(sucursal, puntoventa))
		
		return res

	def sincronizarListaActividadesDocumentoSector(self, sucursal, puntoventa):
		# print('METHOD', sys._getframe().f_code.co_name)
		res = self.callAction('sincronizarListaActividadesDocumentoSector', self.buildData(sucursal, puntoventa))
		
		return res
		
	def sincronizarParametricaTipoDocumentoSector(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaTiposFactura(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarListaMensajesServicios(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def verificarComunicacion(self):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, {})
		
	def sincronizarParametricaEventosSignificativos(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaTipoPuntoVenta(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarListaProductosServicios(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaTipoMoneda(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarActividades(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
	
	def sincronizarParametricaTipoEmision(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaTipoDocumentoIdentidad(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarListaLeyendasFactura(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaTipoMetodoPago(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaUnidadMedida(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaPaisOrigen(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarFechaHora(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		
	def sincronizarParametricaTipoHabitacion(self, sucursal, puntoventa):
		method = sys._getframe().f_code.co_name
		return self.callAction(method, self.buildData(sucursal, puntoventa))
		

