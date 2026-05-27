from ..classes.siatobject import SiatObject

class InvoiceDetail(SiatObject):
	
	def __init__(self):
		self.actividadEconomica=None
		self.codigoProductoSin=None
		self.codigoProducto=None
		self.descripcion=None
		self.cantidad=None
		self.unidadMedida=None
		self.precioUnitario=None
		self.montoDescuento=None
		self.subTotal=None
		self.numeroSerie=None
		self.numeroImei=None
		self.unidadMedida = 58
		
		self._propsAttr = {
			'numeroSerie': {'nullable': True},
			'numeroImei': {'nullable': True},
		}

		
	def validate(self):
		if not self.descripcion:
			raise Exception('Error de datos en el detalle [descripcion]')
		if not self.codigoProducto:
			raise Exception('Error de datos en el detalle "{0}" [codigoProducto]'.format(self.descripcion))
		if int(self.codigoProductoSin) <= 0:
			raise Exception('Error de datos en el detalle "{0}" [codigoProductoSin]'.format(self.descripcion))
		if not self.actividadEconomica:
			raise Exception('Error de datos en el detalle "{0}" [actividadEconomica]'.format(self.descripcion))
		if int(self.unidadMedida) <= 0:
			raise Exception('Error de datos en el detalle "{0}" [unidadMedida]'.format(self.descripcion))
		if float(self.cantidad) <= 0:
			raise Exception('Error de datos en el detalle "{0}" [cantidad]'.format(self.descripcion))
		if float(self.precioUnitario) <= 0:
			raise Exception('Error de datos en el detalle "{0}" [precioUnitario]'.format(self.descripcion))
		if float(self.subTotal) <= 0:
			raise Exception('Error de datos en el detalle "{0}" [subTotal]'.format(self.descripcion))
		if float(self.montoDescuento) >= float(self.subTotal):
			raise Exception('Error de datos en el detalle "{0}" [montoDescuento] no puede ser mayor o igual a [subTotal]'.format(self.descripcion))
