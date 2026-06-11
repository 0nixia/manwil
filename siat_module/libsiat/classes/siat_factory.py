from .. import constants
from ..services.service_facturacion import ServiceFacturacion
from ..services.service_facturacion_electronica import ServiceFacturacionElectronica
from ..invoices.CompraVenta import CompraVenta
from ..invoices.CompraVentaElectronica import CompraVentaElectronica
from ..invoices.SectorEducativo import SectorEducativo
from ..invoices.SectorEducativoElectronica import SectorEducativoElectronica
from ..invoices.AlquilerBienInmueble import AlquilerBienInmueble
from ..invoices.AlquilerBienInmuebleElectronica import AlquilerBienInmuebleElectronica
from ..invoices.ServiciosBasicos import ServiciosBasicos
from ..invoices.ServiciosBasicosElectronica import ServiciosBasicosElectronica

class SiatFactory:

	@staticmethod
	def obtenerServicioFacturacion(config, cuis, cufd, codigo_control=None):
		
		service = ServiceFacturacionElectronica() if config['codigoModalidad'] == constants.MOD_ELECTRONICA_ENLINEA else ServiceFacturacion()
		service.setConfig(config)
		service.cuis = cuis
		service.cufd = cufd
		service.codigoControl = codigo_control
		service.validate()
		
		if config['codigoModalidad'] == constants.MOD_ELECTRONICA_ENLINEA:
			pass
	
		
		return service

	@staticmethod
	def construirFactura(documentoSector, modalidad):
	
		factura = None
		if documentoSector == constants.TiposDocumentoSector.FACTURA_SECTOR_EDUCATIVO:
			factura = SectorEducativoElectronica() if modalidad == constants.MOD_ELECTRONICA_ENLINEA else SectorEducativo()
		elif documentoSector == constants.TiposDocumentoSector.FACTURA_ALQUILER_INMUEBLES:
			factura = AlquilerBienInmuebleElectronica() if modalidad == constants.MOD_ELECTRONICA_ENLINEA else AlquilerBienInmueble()
		elif documentoSector == constants.TiposDocumentoSector.FACTURA_SERV_BASICOS:
			factura = ServiciosBasicosElectronica() if modalidad == constants.MOD_ELECTRONICA_ENLINEA else ServiciosBasicos()
		elif documentoSector == constants.TiposDocumentoSector.FACTURA_COMPRA_VENTA:
			factura = CompraVentaElectronica() if modalidad == constants.MOD_ELECTRONICA_ENLINEA else CompraVenta()

		return factura
