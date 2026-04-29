import json
from abc import ABC, abstractmethod
from datetime import datetime
# from dicttoxml import dicttoxml
from xml.etree.ElementTree import Element, tostring

from ..classes.siatobject import SiatObject
from .invoiceheader import InvoiceHeader
from .. import constants
from .. import functions


class SiatInvoice(SiatObject, ABC):
	
	_classAlias=None
	
	def __init__(self):
		self.cabecera = None
		self.detalle = []
		self._classAlias = self.__class__.__name__
		self._namespaces = {
			'xsi:noNamespaceSchemaLocation': "facturaComputarizadaCompraVenta.xsd",
			'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance"
		}
		
	def validate(self):
		self.cabecera.validate()
		for item in self.detalle:
			item.validate()

	@abstractmethod
	def check_amounts(self):
		pass

	def calculaDigitoMod11(self, cadena, numDig: int, limMult: int, x10: bool):
		cadenaSrc = cadena;
		
		mult = suma = i = n = dig = 0
		
		if x10 == False:
			numDig = 1
		
		#for($n = 1; $n <= numDig; $n++) 
		for n in range(1, numDig + 1):
			suma = 0
			mult = 2
			# $i = len(cadena) - 1
			i = len(cadena)
			
			# for($i; $i >= 0; $i--) 
			for i in reversed( range(0, i) ):
				cadestr = cadena[i]
				# print('casestr', cadestr, cadena)
				intNum = int(cadestr)
				suma += (mult * intNum)
				mult += 1
				
				if( mult > limMult):
					mult = 2

			if x10: 
				dig = ((suma * 10) % 11) % 10
			else:
				dig = suma % 11

			if dig == 10: 
				cadena += "1"
				
			if dig == 11: 
				cadena += "0"
				
			if dig < 10:
				cadena += str(dig)
		
		# modulo = substr($cadena, strlen($cadena) - numDig, strlen($cadena));
		modulo = cadena[len(cadena) - numDig:len(cadena)]
		
		return modulo
	
	def buildCuf(self, modalidad, tipoEmision, tipoFactura, codigoControl):
		
		nitEmisor 			= str(self.cabecera.nitEmisor).zfill(13)
		sucursalNro 		= str(self.cabecera.codigoSucursal).zfill(4)
		tipoSector 			= str(self.cabecera.codigoDocumentoSector).zfill(2)
		numeroFactura 		= str(self.cabecera.numeroFactura).zfill(10)
		numeroPuntoVenta 	= str(self.cabecera.codigoPuntoVenta).zfill(4)
		fechaHora 			= datetime.strptime(self.cabecera.fechaEmision, constants.DATETIME_FORMAT).strftime('%Y%m%d%H%M%S%f')
		
		cadena 		= "{0}{1}{2}{3}{4}{5}{6}{7}{8}".format(
			nitEmisor,
			fechaHora[:-3],
			sucursalNro,
			modalidad,
			tipoEmision,
			tipoFactura,
			tipoSector,
			numeroFactura,
			numeroPuntoVenta
		)
		
		verificador 	= self.calculaDigitoMod11(cadena, 1, 9, False)
		b16_str 		= hex( int( cadena + verificador ) )[2:].upper()
		self.cabecera.cuf = b16_str + codigoControl
		'''
		print('CADENA: ', cadena, len(cadena))
		print('VERIFICADOR:', verificador)
		print('HEX: ', b16_str)
		print('CUF:', self.cabecera.cuf)
		'''
		
	'''
	def toXml(self):
		objCabecera = vars(self.cabecera)
		objDetalle = []
		for d in self.detalle:
			objDetalle.append(vars(d))
		obj = {}
		obj['cabecera'] = objCabecera
		obj['detalle'] = objDetalle
		
		my_item_func = lambda x: 'detalle'
		# print(obj)
		xml = dicttoxml(obj, attr_type=False, custom_root=self._classAlias, item_func=my_item_func)
		
		return xml
	'''
	
	def toXml(self, tag=None):
		
		return super().toXml(tag if tag is not None else self._classAlias)

	def toXmlString(self, tag=None):
		xml = self.toXml(tag)
		xml_str = tostring(xml, encoding='utf-8', method='xml')

		return xml_str

	def getEndpoint(self, modalidad, ambiente):
		return SiatInvoice.getWsdl(modalidad, ambiente, self.cabecera.codigoDocumentoSector)

	def format_details(self, json_str):

		data = json.loads(json_str)
		if data is None:
			return json_str;

		obj = {}
		for item in data:
			for key in list(item.keys()):
				obj[key] = item[key]

		return json.dumps(obj)

	@staticmethod
	def buildUrl(nit, cuf, numeroFactura, ambiente):
		if ambiente == 1:
			base = "https://siat.impuestos.gob.bo/consulta/QR?"
		else:
			base = "https://pilotosiatservicios.impuestos.gob.bo/consulta/QR?"
		return f"{base}nit={nit}&cuf={cuf}&num={numeroFactura}"
	
	@staticmethod
	def getWsdl(modalidad, ambiente, documentoSector):
		if documentoSector == constants.TiposDocumentoSector.FACTURA_SERV_BASICOS:
			return 'https://siatrest.impuestos.gob.bo/v2/ServicioFacturacionServicioBasico?wsdl' if ambiente == 1 else "https://pilotosiatservicios.impuestos.gob.bo/v2/ServicioFacturacionServicioBasico?wsdl"
			
		if documentoSector == constants.TiposDocumentoSector.FACTURA_COMPRA_VENTA:
			return 'https://siatrest.impuestos.gob.bo/v2/ServicioFacturacionCompraVenta?wsdl' if ambiente == 1 else "https://pilotosiatservicios.impuestos.gob.bo/v2/ServicioFacturacionCompraVenta?wsdl"
			
		if documentoSector == constants.TiposDocumentoSector.FACTURA_ENT_FINANCIERA:
			return 'https://siatrest.impuestos.gob.bo/v2/ServicioFacturacionEntidadFinanciera?wsdl' if ambiente == 1 else "https://pilotosiatservicios.impuestos.gob.bo/v2/ServicioFacturacionEntidadFinanciera?wsdl"
		
		if constants.MOD_ELECTRONICA_ENLINEA == modalidad:
			return 'https://siatrest.impuestos.gob.bo/v2/ServicioFacturacionElectronica?wsdl' if ambiente == 1 else 'https://pilotosiatservicios.impuestos.gob.bo/v2/ServicioFacturacionElectronica?wsdl'
		
		return 'https://siatrest.impuestos.gob.bo/v2/ServicioFacturacionComputarizada?wsdl' if ambiente == 1 else 'https://pilotosiatservicios.impuestos.gob.bo/v2/ServicioFacturacionComputarizada?wsdl'

	@abstractmethod
	def instanceDetail(self):
		pass
