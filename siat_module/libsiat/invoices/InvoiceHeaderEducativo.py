from ..classes.siatobject import SiatObject
from .invoiceheader import InvoiceHeader
from .. import constants

class InvoiceHeaderEducativo(InvoiceHeader):

	def __init__(self):
		self.nitEmisor=None
		self.razonSocialEmisor=None
		self.municipio=None
		self.telefono=None
		self.numeroFactura=None
		self.cuf=None
		self.cufd=None
		self.codigoSucursal=None
		self.direccion=None
		self.codigoPuntoVenta=None
		self.fechaEmision=None
		self.nombreRazonSocial=None
		self.codigoTipoDocumentoIdentidad=None
		self.numeroDocumento=None
		self.complemento=None
		self.codigoCliente=None
		self.nombreEstudiante = None
		self.periodoFacturado = None
		self.codigoMetodoPago=None
		self.numeroTarjeta=None
		self.montoTotal=None
		self.montoTotalSujetoIva=None
		self.codigoMoneda=None
		self.tipoCambio=None
		self.montoTotalMoneda=None
		self.montoGiftCard=None
		self.descuentoAdicional=None
		self.codigoExcepcion=None
		self.cafc=None
		self.leyenda=None
		self.usuario=None
		self.codigoDocumentoSector = constants.TiposDocumentoSector.FACTURA_SECTOR_EDUCATIVO
		#self.leyenda = u'Ley Nro 453: Tienes derecho a recibir información sobre las caracteristicas y contenidos de los servicios que utilices.'
		self.leyenda = 'Ley Nro 453: Tienes derecho a recibir informacion sobre las caracteristicas y contenidos de los servicios que utilices.'
		
		self._propsAttr = {
			'codigoPuntoVenta': {'nullable': True},
			'complemento': {'nullable': True},
			'numeroTarjeta': {'nullable': True},
			'montoGiftCard': {'nullable': True},
			'codigoExcepcion': {'nullable': True},
			'cafc': {'nullable': True}
		}

	def validate(self):
		if not self.nitEmisor:
			raise Exception('Invalid data [nitEmisor]')
		if not self.cufd:
			raise Exception('Invalid data [cufd]')
		if not self.cuf:
			raise Exception('Invalid data [cuf]')
		if not self.codigoDocumentoSector:
			raise Exception('Invalid data [codigoDocumentoSector]')
		if not self.telefono:
			raise Exception('Invalid data [telefono]')
		if not self.direccion:
			raise Exception('Invalid data [direccion]')
