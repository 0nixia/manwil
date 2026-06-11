from .solicitudserviciorecepcionfactura import SolicitudServicioRecepcionFactura

class SolicitudServicioRecepcionPaquete(SolicitudServicioRecepcionFactura):
	
	def __init__(self):
		super().__init__()
		
		self.cafc = None
		self.cantidadFacturas = 0
		self.codigoEvento = None
		
	def validate(self):
		super().validate()
		
	
