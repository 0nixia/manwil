class SiatException(Exception):
	
	def __init__(self, data):
		self.response = data
	
	def getMessage(self):
		if 'mensajesList' not in self.response:
			return 'No error message'
		
		msg = ''
		for msgItem in self.response['mensajesList']:
			msg += '{0}: {1}, '.format(msgItem['codigo'], msgItem['descripcion'])
			
		return msg
		
	
class SiatExceptionInvalidNit(SiatException):

	def __init__(self, data, error=''):
		super(SiatExceptionInvalidNit, self).__init__(data)
		self.error = error
		self.error_code = 'error_nit'
