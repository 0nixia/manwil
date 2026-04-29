from .siatinvoice import SiatInvoice
from .InvoiceHeaderEducativo import InvoiceHeaderEducativo
from .invoicedetail import InvoiceDetail
from .. import constants

class SectorEducativo(SiatInvoice):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaComputarizadaSectorEducativo' # self.__class__.__name__
		self._namespaces['xsi:noNamespaceSchemaLocation'] = self._classAlias + ".xsd"
		self.cabecera = self.instanceHeader()
		
	def validate(self):
		super().validate()

	def check_amounts(self):
		pass

	def instanceHeader(self):
		
		return InvoiceHeaderEducativo()
		
	def instanceDetail(self):
		
		detail = InvoiceDetail()
		detail.skipProperty('numeroSerie')
		detail.skipProperty('numeroImei')
		
		return detail
