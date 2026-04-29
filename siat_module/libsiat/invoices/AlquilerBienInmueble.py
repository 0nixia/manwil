from .siatinvoice import SiatInvoice
from .InvoiceHeaderAlquiler import InvoiceHeaderAlquiler
from .invoicedetail import InvoiceDetail
from .. import constants

class AlquilerBienInmueble(SiatInvoice):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaComputarizadaAlquilerBienInmueble' # self.__class__.__name__
		self.cabecera = self.instanceHeader()
		
	def validate(self):
		super().validate()

	def check_amounts(self):
		pass

	def instanceHeader(self):
		
		return InvoiceHeaderAlquiler()
		
	def instanceDetail(self):
		
		detail = InvoiceDetail()
		detail.skipProperty('numeroSerie')
		detail.skipProperty('numeroImei')
		
		return detail
