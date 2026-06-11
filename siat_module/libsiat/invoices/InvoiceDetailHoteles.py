from ..classes.siatobject import SiatObject
from .invoicedetail import InvoiceDetail

class InvoiceDetailHoteles(InvoiceDetail):
	
	def __init__(self):
		self.detalleHuespedes=None
		self._propsAttr = {
			'detalleHuespedes': {'nullable': True},
		}
		self._skipProperties.append('numeroSerie')
		self._skipProperties.append('numeroImei')
		
	def validate(self):
		super().validate()
		if not self.descripcion:
			raise Exception('Error de datos en el detalle [descripcion]')
