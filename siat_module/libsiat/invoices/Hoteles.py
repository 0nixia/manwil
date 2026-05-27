from .siatinvoice import SiatInvoice
from .InvoiceHeaderHoteles import InvoiceHeaderHoteles
from .InvoiceDetailHoteles import InvoiceDetailHoteles

class Hoteles(SiatInvoice):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaComputarizadaHotel'
		self._namespaces['xsi:noNamespaceSchemaLocation'] = "facturaComputarizadaHotel.xsd"
		self.cabecera = self.instanceHeader()
		
	def validate(self):
		super().validate()

	def check_amounts(self):
		pass

	def instanceHeader(self):
		
		return InvoiceHeaderHoteles()
		
	def instanceDetail(self):
		detail = InvoiceDetailHoteles()

		return detail
