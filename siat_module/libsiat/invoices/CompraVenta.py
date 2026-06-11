from .siatinvoice import SiatInvoice
from .InvoiceHeaderCompraVenta import InvoiceHeaderCompraVenta
from .invoicedetail import InvoiceDetail
from .. import constants

class CompraVenta(SiatInvoice):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaComputarizadaCompraVenta' # self.__class__.__name__
		self.cabecera = self.instanceHeader()
		#self.cabecera.codigoDocumentoSector = constants.TiposDocumentoSector.FACTURA_COMPRA_VENTA
		
	def validate(self):
		super().validate()

	def check_amounts(self):
		pass

	def instanceHeader(self):

		header = InvoiceHeaderCompraVenta()
		# header.codigoDocumentoSector = constants.TiposDocumentoSector.FACTURA_COMPRA_VENTA
		return header

	def instanceDetail(self):
	
		detail = InvoiceDetail()
		
		return detail
