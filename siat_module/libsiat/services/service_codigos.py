from .service_siat import ServiceSiat

class ServiceCodigos(ServiceSiat):

	def __init__(self):
		super().__init__()
		self.wsdl = None

	def setConfig(self, data):
		super().setConfig(data)
		if self.ambiente == 1:
			self.wsdl = 'https://siatrest.impuestos.gob.bo/v2/FacturacionCodigos?wsdl'
		else:
			self.wsdl = 'https://pilotosiatservicios.impuestos.gob.bo/v2/FacturacionCodigos?wsdl'
	
	def buildData(self, sucursal, puntoventa):
		return [
			{
				#'SolicitudCuis': {
					'codigoAmbiente'	: self.ambiente,
					'codigoModalidad'	: self.modalidad,
					'codigoPuntoVenta'	: puntoventa,
					'codigoSistema'		: self.codigoSistema,
					'codigoSucursal'	: sucursal,
					'nit'				: self.nit,
				#}
			}
		]
		
	def getCuis(self, sucursal, puntoventa):
		return self.callAction('cuis', self.buildData(sucursal, puntoventa))
	
	def get_cufd(self, sucursal, puntoventa, cuis_code=None):
		data = self.buildData(sucursal, puntoventa)

		if cuis_code is not None:
			data[0]['cuis'] = cuis_code
		else:
			data[0]['cuis'] = self.cuis
		return self.callAction('cufd', data)

	def verificarNit(self, nit, sucursal=0, puntoventa=0):
		data = self.buildData(sucursal, puntoventa)
		data[0]['cuis'] = self.cuis
		data[0]['nitParaVerificacion'] = nit
		
		return self.callAction('verificarNit', data)
		
