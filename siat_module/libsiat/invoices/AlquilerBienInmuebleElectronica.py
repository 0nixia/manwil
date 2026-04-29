from .siatinvoice import SiatInvoice
from .AlquilerBienInmueble import AlquilerBienInmueble
from .. import constants

class AlquilerBienInmuebleElectronica(AlquilerBienInmueble):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaElectronicaAlquilerBienInmueble'
		self._namespaces['xsi:noNamespaceSchemaLocation'] = "facturaElectronicaAlquilerBienInmueble.xsd"
			
		
	def validate(self):
		super().validate()
