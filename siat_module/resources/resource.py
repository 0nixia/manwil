import json

class SiatResource:
	
	_serializable	= []
	_object = None
	
	def bind(self, data):
		
		for key in data:
			setattr(self, key, data[key])
			
	def dict(self):
		data = {}
		# print('_serializable', self._serializable)
		for attr in self._serializable:
			if attr[0] == '_':
				continue
			obj_attr = getattr(self, attr, '')
			if callable( obj_attr ):
				continue
			if str(type(obj_attr)) == "<type 'classobj'>" and callable(obj_attr, 'json'):
				data[attr] = obj_attr.json()
			else:
				data[attr] = getattr(self, attr)
			
		return data
		
	def json(self):
		return json.dumps(self.dict())
		
	def toJSON(self):
		return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

	def __str__(self):
		return self.dict()