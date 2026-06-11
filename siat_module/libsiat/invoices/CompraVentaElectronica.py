from .siatinvoice import SiatInvoice
from .CompraVenta import CompraVenta
from .. import constants

class CompraVentaElectronica(CompraVenta):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaElectronicaCompraVenta'
		self._namespaces['xsi:noNamespaceSchemaLocation'] = "facturaElectronicaCompraVenta.xsd"

		

