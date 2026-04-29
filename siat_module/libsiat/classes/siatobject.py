from xml.etree.ElementTree import Element,tostring

class SiatObject:
	
	_propsAttr = {}
	_namespaces = {}
	_skipProperties = []
	
	def toDict(self):
		
		return vars(self)
		
	def toXml(self, tag=None):
		
		tag = tag if tag is not None else self.__class__.__name__
		
		data = self.toDict()
		
		attrib = {}
		if len(self._namespaces) > 0:
			attrib = self._namespaces
			
		element = Element(tag, attrib=attrib)
		
		for key, val in data.items():
			if key[0] == '_' or key in self._skipProperties:
				continue
			# print(key, ' -> ', type(val), isinstance(val, list), callable( getattr(val, "toXml", None)))
			
			if isinstance(val, SiatObject) and callable( getattr(val, "toXml", None) ):
				child = val.toXml(key)
				element.append( child )
				
			elif isinstance(val, list):
				for item in val:
					el = item.toXml(key)
					element.append(el)
			else:
				child = Element(key, attrib=self.buildXmlElementAttribs(key, val))
				child.text = str(val) if val is not None else '' # .encode('utf8')
				element.append( child )
		
		return element
	
	def buildXmlElementAttribs(self, propName :str, propVal=None):
		
		if propName not in self._propsAttr:
			return {}
		
		attrs = {}
		
		if 'nullable' in self._propsAttr[propName]:
			# print(propName, ' -> nullable : ', propVal)
			if self._propsAttr[propName]['nullable'] == True and propVal is None:
				attrs['xsi:nil'] = 'true'
		
		return attrs

	def skipProperty(self, prop):
		self._skipProperties.append( prop )
		
	@staticmethod
	def dictToXml(dictData, tag):
		
		element = Element(tag)
		
		for key, val in dictDta.items():
			child = Element(key)
			child.text = str(val)
			element.append( child )
		
		return element
		
