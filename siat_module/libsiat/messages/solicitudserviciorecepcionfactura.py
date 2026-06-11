import gzip
import hashlib
import tarfile
from datetime import datetime
from io import BytesIO, StringIO
# import StringIO

from ..services.service_siat import ServiceSiat
from .. import constants

class SolicitudServicioRecepcionFactura():
	
	def __init__(self):
		self.codigoAmbiente = None
		self.codigoDocumentoSector = None
		self.codigoEmision = 1
		self.codigoModalidad = 1
		self.codigoPuntoVenta = 0
		self.codigoSistema = None
		self.codigoSucursal = 0
		self.cufd = None
		self.cuis = None
		self.nit = None
		self.tipoFacturaDocumento = None
		
		self.archivo = None
		self.fechaEnvio = None
		self.hashArchivo = None
	
	def validate(self):
		pass
		
	def setBuffer(self, buff, compress=True):
		self.archivo = gzip.compress(buff) if compress == True else buff
		self.hashArchivo = hashlib.sha256(str(buff).encode('utf-8')).hexdigest()
	
	def setBufferFromFiles(self, files):
		pass
		
	def setBufferFromArray(self, invoicesXml: list):
		time = datetime.timestamp( datetime.now() )
		filename = 'invoices-{0}.tar.gz'.format(time)
		tmp_file = '{0}{1}{2}'.format(constants.TMP_DIR, constants.SB_DS, filename)
		buff = BytesIO()
		# print('TOTAL INVOICES: ', len(invoicesXml))
		with tarfile.open(tmp_file, 'w:gz', fileobj=buff) as f:
			i = 0
			for invoice in invoicesXml:
				# print(invoice)
				# stringXml = StringIO.StringIO()
				stringXml = BytesIO()
				stringXml.write( invoice )
				stringXml.seek(0)
				info = tarfile.TarInfo(name='factura-{0}.xml'.format(i))
				info.size = stringXml.getbuffer().nbytes # len(stringXml.buf)
				f.addfile(tarinfo=info, fileobj=stringXml)
				i += 1
		'''		
		with open(tmp_file, 'r') as f:
			buff = f.read()
			self.setBuffer(buff, False)
		'''
		self.setBuffer(buff.getbuffer(), False)
