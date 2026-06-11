from .resource import SiatResource

class ResourceCustomer(SiatResource):
	
	_serializable = ['id', 'customer_id', 'firstname', 'lastname', 'nit_ruc_nif', 'email', 'text']
	
	def __init__(self, obj):
		
		self._object = obj
		
		self.id = obj.get('id', 0)
		self.customer_id = obj.get('id', 0)
		self.firstname = ''
		self.lastname = obj.get('name', '')
		self.nit_ruc_nif = obj.get('vat', '')
		self.email = obj.get('email', '')
		self.phone = obj.get('phone', '')
		self.company = obj.get('company_name', '')
		self.text = obj.get('name', '')
	
	
