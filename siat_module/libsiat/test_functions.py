import random
from datetime import datetime, timedelta

from services.service_codigos import ServiceCodigos
from services.service_sincronizacion import ServiceSincronizacion
from services.service_facturacion_computarizada import ServiceFacturacionComputarizada
from services.service_facturacion_electronica import ServiceFacturacionElectronica
from services.service_operaciones import ServiceOperaciones
from invoices.siatinvoice import SiatInvoice
from invoices.CompraVenta import CompraVenta
from invoices.CompraVentaElectronica import CompraVentaElectronica
from invoices.invoicedetail import InvoiceDetail
from invoices.SectorEducativo import SectorEducativo
from invoices.SectorEducativoElectronica import SectorEducativoElectronica
from invoices.AlquilerBienInmueble import AlquilerBienInmueble
from invoices.AlquilerBienInmuebleElectronica import AlquilerBienInmuebleElectronica
from classes.siat_factory import SiatFactory
from classes.siat_exception import SiatException
from constants import TiposDocumentoSector
import constants
import test
import functions

gResCuis = None
gResCufd = None
gDebug = True

def obtenerCuis(sucursal=0, puntoventa=0, new=False):
	global gResCuis
	
	if gResCuis is not None and new == False:
		return gResCuis
		
	cfg = test.getConfig()
	
	serviceCods = ServiceCodigos()
	serviceCods.setConfig(cfg)
	gResCuis = serviceCods.getCuis(sucursal, puntoventa)
	
	if gResCuis['transaccion'] == False and gResCuis['codigo'] is None:
		raise SiatException(gResCuis)
	
	serviceCods.cuis = gResCuis['codigo']
	
	
	return gResCuis
	
def obtenerCufd(sucursal=0, puntoventa=0, cuis='', new=False):
	global gResCufd
	
	if gResCufd is not None and new == False:
		return gResCufd
		
	cfg = test.getConfig()
	
	serviceCods = ServiceCodigos()
	serviceCods.setConfig(cfg)
	serviceCods.cuis = cuis
	
	gResCufd = serviceCods.get_cufd(sucursal, puntoventa)
	
	if gResCufd['transaccion'] == False and gResCufd['codigo'] is None:
		raise SiatException(gResCufd)
		
	serviceCods.cufd = gResCufd['codigo']
	
	
	return gResCufd
	
'''
Obtiene la lista de eventos significativos de SIAT
En caso de buscar un evento en especifico asignar el parametro buscarId
'''
def obtenerListadoEventos(sucursal, puntoventa, buscarId=None):
	cfg = test.getConfig()
	resCuis = obtenerCuis(sucursal, puntoventa)
	service = ServiceSincronizacion()
	service.setConfig(cfg)
	service.cuis = resCuis['codigo']
	resEvents = service.sincronizarParametricaEventosSignificativos(sucursal, puntoventa)
	
	if buscarId is None:
		return resEvents
		
	event = None
	for parametrica in resEvents['listaCodigos']:
		if parametrica['codigoClasificador'] == buscarId:
			event = parametrica
			break
		
	return event

def construirFactura(codigoSucursal=0, codigoPuntoVenta = 0, modalidad = 0, documentoSector = 1, codigoActividad = '620100', 
		codigoProductoSin = ''
	):
	cfg = test.getConfig()
	
	factura = SiatFactory.construirFactura(documentoSector, modalidad)
	
	if factura is None:
		raise Exception('No se puede construir la factura')
	
	subtotal = 0
	
	for i in range(2):
		detalle = factura.instanceDetail()
		detalle.cantidad = 1
		detalle.actividadEconomica = codigoActividad
		detalle.codigoProducto = 'D001-' + str(random.randrange(1, 4000))
		detalle.codigoProductoSin = codigoProductoSin
		detalle.descripcion = 'Nombre del producto #0' + str(i + 1)
		detalle.precioUnitario = 10 * random.randrange(1, 2000)
		detalle.montoDescuento = 0
		detalle.subTotal = detalle.cantidad * detalle.precioUnitario
		factura.detalle.append(detalle)
		subtotal += detalle.subTotal
		
	factura.cabecera.razonSocialEmisor = cfg['razonSocial']
	factura.cabecera.municipio = 'La Paz'
	factura.cabecera.telefono = '98783937'
	factura.cabecera.numeroFactura = random.randrange(1, 1000)
	factura.cabecera.codigoSucursal = codigoSucursal
	factura.cabecera.direccion = 'Direccion 01'
	factura.cabecera.codigoPuntoVenta = codigoPuntoVenta
	factura.cabecera.fechaEmision = functions.sb_siat_format_datetime(datetime.now())
	factura.cabecera.nombreRazonSocial = 'Pepito Cliente'
	factura.cabecera.codigoTipoDocumentoIdentidad = 1
	factura.cabecera.numeroDocumento = 3245455
	factura.cabecera.codigoCliente = 'CC-3245455'
	factura.cabecera.codigoMetodoPago = 1
	factura.cabecera.montoTotal = subtotal
	factura.cabecera.montoTotalMoneda = subtotal
	factura.cabecera.montoTotalSujetoIva = subtotal
	factura.cabecera.descuentoAdicional = 0
	factura.cabecera.codigoMoneda = 1
	factura.cabecera.tipoCambio = 1
	factura.cabecera.usuario = 'MonoBusiness User 01'
	
	if documentoSector == TiposDocumentoSector.FACTURA_SECTOR_EDUCATIVO:
		factura.cabecera.nombreEstudiante = 'Pepito Junior Jatin'
		factura.cabecera.periodoFacturado = 'Febrero'
	elif documentoSector == TiposDocumentoSector.FACTURA_ALQUILER_INMUEBLES:
		factura.cabecera.periodoFacturado = 'Febrero'
	
	return factura

def construirFacturas(sucursal: int, puntoventa: int, cantidad: int, documentoSector: int, 
	codigoActividad, 
	codigoProductoSin,
	fechaEmision: datetime,
	cufdAntiguo,
	cafc=None
):
	cfg = test.getConfig()
	
	facturas = []
	for i in range(0, cantidad):
		factura = construirFactura(
			sucursal, 
			puntoventa, 
			cfg['modalidad'], 
			documentoSector, 
			codigoActividad, 
			codigoProductoSin
		)
		factura.cabecera.nitEmisor = cfg['nit']
		factura.cabecera.razonSocialEmisor = cfg['razonSocial']
		factura.cabecera.fechaEmision = functions.sb_siat_format_datetime(fechaEmision)
		factura.cabecera.cufd = cufdAntiguo
		factura.cabecera.cafc = cafc
		facturas.append( factura )
		fechaEmision = fechaEmision + timedelta(0, 10)
		
	return facturas, fechaEmision
	
def recepcionFactura(sucursal, puntoventa, factura, tipoFactura):
	
	cfg = test.getConfig()
	resCuis = obtenerCuis(sucursal, puntoventa)
	resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	
	# print(resCuis, resCufd)
	service = SiatFactory.obtenerServicioFacturacion(cfg, resCuis['codigo'], resCufd['codigo'], resCufd['codigoControl'])
	service.debug = gDebug
	res = service.recepcionFactura(factura, constants.TIPO_EMISION_ONLINE, tipoFactura )
	
	return res
	
def registroEvento(sucursal, puntoventa, evento: dict, cufdAntiguo: str, fechaInicio: datetime, fechaFin: datetime):
	cfg = test.getConfig()
	
	resCuis = obtenerCuis(sucursal, puntoventa)
	resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	
	service = ServiceOperaciones()
	service.setConfig(cfg)
	service.cuis = resCuis['codigo']
	service.cufd = resCufd['codigo']
	# service.codigoControl = resCufd['codigoControl']
	res = service.registroEventoSignificativo(
		evento['codigoClasificador'],
		evento['descripcion'],
		cufdAntiguo,
		fechaInicio,
		fechaFin,
		sucursal,
		puntoventa
	)
	
	return res
	
def recepcionPaqueteFactura(sucursal, puntoventa, facturas: list, codigoControlAntiguo, tipoFactura, evento: dict, cafc = None):
	cfg = test.getConfig()
	
	resCuis = obtenerCuis(sucursal, puntoventa)
	resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	
	service = SiatFactory.obtenerServicioFacturacion(cfg, resCuis['codigo'], resCufd['codigo'], resCufd['codigoControl'])
	res = service.recepcionPaqueteFactura(
		facturas, 
		evento['codigoRecepcionEventoSignificativo'], 
		constants.TIPO_EMISION_OFFLINE, 
		tipoFactura, 
		cafc
	)
	
	return res
	
def validacionRecepcionPaquete(sucursal: int, puntoventa: int, documentoSector: int, tipoFactura: int, codigoRecepcion):
	cfg = test.getConfig()
	
	resCuis = obtenerCuis(sucursal, puntoventa)
	resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	
	service = SiatFactory.obtenerServicioFacturacion(cfg, resCuis['codigo'], resCufd['codigo'], resCufd['codigoControl'])
	
	res = service.validacionRecepcionPaqueteFactura(sucursal, puntoventa, codigoRecepcion, tipoFactura, documentoSector)
	while res['codigoDescripcion'] == 'PENDIENTE':
		res = validacionRecepcionPaquete(sucursal, puntoventa, documentoSector, tipoFactura, codigoRecepcion)
		
	return res
	
def recepcionFacturaFirma(sucursal: int, puntoventa: int, factura: SiatInvoice, tipoFactura: int):
	cfg = test.getConfig()
	
	tipoEmision = constants.TIPO_EMISION_ONLINE
	resCuis = obtenerCuis(sucursal, puntoventa)
	resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	service = SiatFactory.obtenerServicioFacturacion(cfg, resCuis['codigo'], resCufd['codigo'], resCufd['codigoControl'])
	service.debug = True
	res = service.recepcionFactura(factura, tipoEmision, tipoFactura)
	
	return res
	
