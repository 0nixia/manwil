from abc import ABC, abstractmethod

from ..classes.siatobject import SiatObject

class InvoiceHeader(ABC, SiatObject):
	
	def __init__(self):
		pass

	#@abstractmethod
	def validate(self):
		if not self.nitEmisor:
			raise Exception('Invalid data [nitEmisor]')
		if not self.cufd:
			raise Exception('Invalid data [cufd]')
		if not self.cuf:
			raise Exception('Invalid data [cuf]')
		if not self.codigoDocumentoSector:
			raise Exception('Invalid data [codigoDocumentoSector]')
		if not self.telefono:
			raise Exception('Invalid data [telefono]')
		if not self.direccion:
			raise Exception('Invalid data [direccion]')
		if not self.numeroDocumento:
			raise Exception('Datos invalidos [numeroDocumento]')
		if not self.leyenda:
			raise Exception('Datos invalidos [leyenda]')
		if self.montoTotal <= 0:
			raise Exception('Datos invalidos, [montoTotal]')

	def check_amounts(self):
		pass