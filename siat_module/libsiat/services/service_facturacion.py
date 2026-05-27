import sys
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element,tostring
from datetime import datetime
from lxml import etree
import os
import logging

from .. import constants
from .. import functions

from .service_siat import ServiceSiat
from ..invoices.siatinvoice import SiatInvoice
from ..messages.solicitudserviciorecepcionfactura import SolicitudServicioRecepcionFactura
from ..messages.recepcionpaquete import SolicitudServicioRecepcionPaquete

_logger = logging.getLogger(__name__)

class ServiceFacturacion(ServiceSiat):
	
	def __init__(self):
		super().__init__()
		
		
	def buildInvoiceXml(self, invoice: SiatInvoice):
		element = invoice.toXml()
		xml = tostring(element, encoding='utf-8', method='xml')
		
		return b'<?xml version="1.0" encoding="utf-8" standalone="yes" ?>' + xml
		
	def recepcionFactura(self, invoice: SiatInvoice, tipoEmision: int, tipoFactura: int):
		
		invoice.cabecera.razonSocialEmisor = self.razonSocial
		invoice.cabecera.nitEmisor = self.nit
		invoice.cabecera.cufd = self.cufd
		invoice.buildCuf(self.modalidad, tipoEmision, tipoFactura, self.codigoControl)
		invoice.validate()
		
		invoiceXml = self.buildInvoiceXml(invoice)
		# print(invoiceXml)
		xsd_path = self._get_xsd_path(invoice.cabecera.codigoDocumentoSector, self.ambiente)
		if xsd_path and os.path.exists(xsd_path):
			try:
				schema_doc = etree.parse(xsd_path)
				schema = etree.XMLSchema(schema_doc)
				xml_doc = etree.fromstring(invoiceXml)
				schema.assertValid(xml_doc)
			except etree.XMLSchemaError as e:
				raise Exception(f"Error en el esquema XSD: {e}")
			except etree.DocumentInvalid as e:
				error_log = schema.error_log
				raise Exception(f"El XML no es válido contra el XSD: {error_log}")
		else:
			_logger.warning("No se encontró el archivo XSD para validación: %s", xsd_path)
		solicitud = SolicitudServicioRecepcionFactura()
		solicitud.cufd = self.cufd
		solicitud.cuis = self.cuis
		solicitud.codigoSistema = self.codigoSistema
		solicitud.nit = self.nit
		solicitud.codigoModalidad = self.modalidad
		solicitud.codigoAmbiente = self.ambiente
		solicitud.codigoDocumentoSector = invoice.cabecera.codigoDocumentoSector
		solicitud.tipoFacturaDocumento = tipoFactura
		solicitud.codigoEmision = tipoEmision
		solicitud.fechaEnvio = functions.sb_siat_format_datetime(datetime.now()) # datetime.now().strftime(constants.DATETIME_FORMAT)
		solicitud.codigoSucursal =  invoice.cabecera.codigoSucursal
		solicitud.codigoPuntoVenta = invoice.cabecera.codigoPuntoVenta
		solicitud.setBuffer(invoiceXml)
		solicitud.validate()
		
		self.wsdl = invoice.getEndpoint(self.modalidad, self.ambiente)
		
		data = [vars(solicitud)]
		# print(data)
		res = self.callAction('recepcionFactura', data)
		
		return res
	
	def _get_xsd_path(self, codigoDocumentoSector, ambiente):
		"""Retorna la ruta al archivo XSD correspondiente."""
		base_dir = os.path.dirname(os.path.dirname(__file__))
		xsd_dir = os.path.join(base_dir, 'data', 'xsd')
		filename = f"factura_ds{codigoDocumentoSector}_{'prod' if ambiente == 1 else 'pilot'}.xsd"
		return os.path.join(xsd_dir, filename)
		
	def anulacionFactura(self, motivo, cuf, sucursal: int, puntoventa: int, tipoFactura: int, tipoEmision: int, 
		documentoSector: int):
		
		solicitud = [{
			'cuis': self.cuis,
			'cufd': self.cufd,
			'nit': self.nit,
			'codigoSistema': self.codigoSistema,
			'codigoAmbiente': self.ambiente,
			'codigoModalidad': self.modalidad,
			'codigoSucursal': sucursal,
			'codigoPuntoVenta': puntoventa,
			'codigoEmision': tipoEmision,
			'tipoFacturaDocumento': tipoFactura,
			'codigoDocumentoSector': documentoSector,
			'codigoMotivo': motivo,
			'cuf': cuf
		}]
		self.wsdl = SiatInvoice.getWsdl(self.modalidad, self.ambiente, documentoSector)
		res = self.callAction('anulacionFactura', solicitud)
		
		return res
		
	def recepcionPaqueteFactura(self, facturas: list, codigoEvento: int, tipoEmision: int, tipoFactura: int, cafc=None):
		
		xmlFacturas = []
		for factura in facturas:
			factura.cabecera.cafc = cafc
			if not factura.cabecera.cuf:
				factura.buildCuf(self.modalidad, tipoEmision, tipoFactura, self.codigoControl)
			factura.validate()
			
			xmlFacturas.append( self.buildInvoiceXml(factura) )
		'''
		solicitud = [{
			'cafc': cafc,
			'cantidadFacturas': len(facturas),
			'codigoEvento': codigoEvento,
			'cufd': self.cufd,
			'cuis': self.cuis,
			'codigoSistema': self.codigoSistema,
			'nit': self.nit,
			'codigoModalidad': self.modalidad,
			'codigoAmbiente': self.ambiente,
			'codigoDocumentoSector': facturas[0].cabecera.codigoDocumentoSector,
			'tipoFacturaDocumento': tipoFactura,
			'fechaEnvio': functions.sb_siat_format_datetime(datetime.now()),
			'codigoEmision': tipoEmision,
			'codigoPuntoVenta': facturas[0].cabecera.codigoPuntoVenta,
			
		}]
		'''
		solicitud = SolicitudServicioRecepcionPaquete()
		solicitud.cafc = cafc
		solicitud.cantidadFacturas = len(facturas)
		solicitud.codigoEvento = int(codigoEvento)
		solicitud.cufd = self.cufd
		solicitud.cuis = self.cuis
		solicitud.codigoSistema = self.codigoSistema
		solicitud.nit = self.nit
		solicitud.codigoModalidad = self.modalidad
		solicitud.codigoAmbiente = self.ambiente
		solicitud.codigoDocumentoSector = facturas[0].cabecera.codigoDocumentoSector
		solicitud.tipoFacturaDocumento = tipoFactura
		solicitud.fechaEnvio =  functions.sb_siat_format_datetime(datetime.now())
		solicitud.codigoEmision = tipoEmision
		solicitud.codigoPuntoVenta = facturas[0].cabecera.codigoPuntoVenta
		solicitud.codigoSucursal = facturas[0].cabecera.codigoSucursal
		solicitud.setBufferFromArray(xmlFacturas)
		
		data = [vars(solicitud)]
		
		self.wsdl = facturas[0].getEndpoint(self.modalidad, self.ambiente)
		res = self.callAction('recepcionPaqueteFactura', data)
		
		return res

	def validacionRecepcionPaqueteFactura(self, sucursal: int, puntoventa: int, codigoRecepcion, tipoFactura: int, documentoSector: int):
		solicitud = [{
			'cuis': self.cuis,
			'cufd': self.cufd,
			'nit': self.nit,
			'codigoSistema': self.codigoSistema,
			'codigoAmbiente': self.ambiente,
			'codigoModalidad': self.modalidad,
			'codigoSucursal': sucursal,
			'codigoPuntoVenta': puntoventa,
			'codigoEmision': constants.TIPO_EMISION_OFFLINE,
			'tipoFacturaDocumento': tipoFactura,
			'codigoDocumentoSector': documentoSector,
			'codigoRecepcion': codigoRecepcion
		}]
		self.wsdl = SiatInvoice.getWsdl(self.modalidad, self.ambiente, documentoSector)
		
		res = self.callAction('validacionRecepcionPaqueteFactura', solicitud)
		
		return res

	def reversionAnulacionFactura(self, sucursal, puntoVenta, documentoSector, tipoEmision, tipoFactura, cuf):
		solicitud = [{
			'codigoAmbiente': self.ambiente,
			'codigoPuntoVenta': puntoVenta,
			'codigoSistema': self.codigoSistema,
			'codigoSucursal': sucursal,
			'nit': self.nit,
			'codigoDocumentoSector': documentoSector,
			'codigoEmision': tipoEmision,
			'codigoModalidad': self.modalidad,
			'cufd': self.cufd,
			'cuis': self.cuis,
			'tipoFacturaDocumento': tipoFactura,
			'cuf': cuf
		}]
		self.wsdl = SiatInvoice.getWsdl(self.modalidad, self.ambiente, documentoSector)
		method = sys._getframe().f_code.co_name
		res = self.callAction(method, solicitud)
		return res

		