from ..classes.siatobject import SiatObject
from .invoiceheader import InvoiceHeader
from .. import constants

class InvoiceHeaderHoteles(InvoiceHeader):
	
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
		self.cantidadHuespedes=None
		self.cantidadHabitaciones=None
		self.cantidadMayores=None
		self.cantidadMenores=None
		self.fechaIngresoHospedaje=None
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
		self.leyenda='Ley Nro 453: Tienes derecho a recibir informacion sobre las caracteristicas y contenidos de los servicios que utilices.'
		self.usuario=None
		self.codigoDocumentoSector = constants.TiposDocumentoSector.FACTURA_HOTELES

		self._propsAttr = {
			'codigoPuntoVenta': {'nullable': True},
			'complemento': {'nullable': True},
			'numeroTarjeta': {'nullable': True},
			'montoGiftCard': {'nullable': True},
			'codigoExcepcion': {'nullable': True},
			'cafc': {'nullable': True},
			'cantidadHuespedes': {'nullable': True},
			'cantidadHabitaciones': {'nullable': True},
			'cantidadMayores': {'nullable': True},
			'cantidadMenores': {'nullable': True},
		}

	def validate(self):
		super().validate()

	
