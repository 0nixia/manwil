from .siatinvoice import SiatInvoice
from .Hoteles import Hoteles
from .. import constants


class HotelesElectronica(Hoteles):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaElectronicaHotel'
		self._namespaces['xsi:noNamespaceSchemaLocation'] = "facturaElectronicaHotel.xsd"

		

