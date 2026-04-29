from .resource import SiatResource
from ..libsiat.invoices.siatinvoice import SiatInvoice

class ResourceInvoice(SiatResource):
	
	_serializable = ['id', 'invoice_id', 'invoice_number', 'total', 'tax', 'codigo_sucursal', 
		'punto_venta', 'codigo_documento_sector', 'evento_id', 'ambiente', 'nit_ruc_nif', 'control_code', 'status', 'cufd', 'cuf',
		'siat_id', 'leyenda', 'subtotal', 'total_tax', 'invoice_datetime', 'customer', 'print_url', 'print_url_ticket', 'siat_url'
	]
	
	def __init__(self, obj):
		
		self._object = obj
		
		self.setData()
		
	def setData(self):
		self.bind(self._object.read()[0])
		#self.id = self._object.id
		self.invoice_id = self._object.id
		self.tax = self._object.total_tax
		self.customer = self._object.customer_name
		self.print_url = '/report/pdf/siat.siat_invoice_report/{0}'.format(self.invoice_id)
		self.print_url_ticket = '/report/pdf/siat.siat_invoice_report_ticket/{0}'.format(self.invoice_id)
		self.siat_url = SiatInvoice.buildUrl(self._object.nit_emisor, self._object.cuf, self._object.invoice_number, self._object.ambiente)
