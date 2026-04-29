from .resource import SiatResource


class ResourceProduct(SiatResource):
	
	_serializable = ['id', 'user_id', 'code', 'name', 'description', 'price', 'imei', 'numeroserie', 'codigo_sin', 
		'codigo_actividad', 'unidad_medida'
	]
	
	def __init__(self, obj):
		self._object = obj
		self.setData()
	
	def setData(self):
		self.id = self._object.id
		self.user_id = 0
		self.code = self._object.default_code
		self.name = self._object.name
		self.description = ''
		self.price = self._object.list_price
		self.standar_price = self._object.standard_price
		self.barcode = self._object.barcode
		self.imei = ''
		self.numeroserie = ''
		self.codigo_sin = self._object.codigo_producto_sin
		self.codigo_actividad = self._object.actividad_economica
		self.unidad_medida = self._object.unidad_medida
		
	
