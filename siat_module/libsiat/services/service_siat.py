from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object
from requests import Session
import json
import traceback

class ServiceSiat:
	
	
	def __init__(self):
		
		self.debug			= True
		self.modalidad		= None
		self.ambiente		= None
		self.codigoSistema	= None
		self.nit			= None
		self.razonSocial	= None
		self.token			= None
		self.wsdl			= None
		self.cuis			= None
		self.cufd			= None
		self.cafc			= None
		self.codigoControl	= None
		
	def setConfig(self, data):
		self.modalidad	= int(data['codigoModalidad']) if 'codigoModalidad' in data else None
		self.ambiente	= int(data['codigoAmbiente']) if 'codigoAmbiente' in data else None
		self.codigoSistema	= data['codigoSistema'] if 'codigoSistema' in data else None
		self.nit	= data['nit'] if 'nit' in data else None
		self.razonSocial = data['razonSocial'] if 'razonSocial' in data else None
		self.token	= data['token'] if 'token' in data else None
		self.cafc	= data['cafc'] if 'cafc' in data else None
		
	def validate(self):
		pass
		
	def callAction(self, action, data):
		if self.wsdl is None:
			raise Exception('Invalid wsdl endpoint')
		
		try:
			self.debugData(self.wsdl)
			self.debugData('REQUEST DATA => ACTION: {0}\n========================='.format(action))
			self.debugData(data)
			
			session = Session()
			session.headers.update({'apikey': 'TokenApi {0}'.format(self.token)})
			transport = Transport(session=session)
			
			client = Client(self.wsdl, transport=transport)
			result = client.service[action](data)
			
			self.debugData('RESPONSE DATA\n==================')
			self.debugData(result)
				
			# return json.loads(json.dumps(serialize_object(result)))
			return serialize_object(result, dict)
			
		except Exception as e:
			print('CALL ACTION ERROR:', e)
			print(traceback.print_exc())
			raise e
	
	def debugData(self, data):
		if self.debug == False:
			return
			
		print(data, "\n")

