from .siatinvoice import SiatInvoice
from .SectorEducativo import SectorEducativo
from .. import constants

class SectorEducativoElectronica(SectorEducativo):
	
	def __init__(self):
		super().__init__()
		self._classAlias = 'facturaElectronicaSectorEducativo'
		self._namespaces['xsi:noNamespaceSchemaLocation'] = self._classAlias + ".xsd"
			
		
	def validate(self):
		super().validate()
