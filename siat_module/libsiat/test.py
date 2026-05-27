# -*- coding: utf-8 -*-
# GNU General Public License v3

import json
import io
from os import *
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element,tostring
import traceback

import constants
# import services.service_siat
from services.service_siat import ServiceSiat
from services.service_sincronizacion import ServiceSincronizacion
from services.service_codigos import ServiceCodigos
from test_functions import *
from classes.siat_exception import SiatException

__log_file__ = ''

def log(data):
	global __log_file__

	mode = ('a' if path.exists(__log_file__) else 'w')
	
	fh = io.open(__log_file__, mode)
	_json_ = json.dumps(data, default=str) if type(data) is dict else data
	fh.write(_json_ + '\n')
	fh.close()
	print(_json_)

def getConfig():
	'''
	cfg = {
		'modalidad': constants.MOD_COMPUTARIZADA_ENLINEA,
		# 'modalidad': constants.MOD_ELECTRONICA_ENLINEA,
		'ambiente': constants.AMBIENTE_PRUEBAS,
		'codigoSistema': '722A170272B644A27ED6F67',
		'nombreSistema': 'Factura 1Byte',
		'nit': 13492810016,
		'razonSocial': 'HUAYCHO CUIZA MANUEL ALFREDO',
		'tipo': 'PROVEEDOR',
		'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJNYW51ZWxBSEMiLCJjb2RpZ29TaXN0ZW1hIjoiNzIyQTE3MDI3MkI2NDRBMjdFRDZGNjciLCJuaXQiOiJINHNJQUFBQUFBQUFBRE0wTnJFMHNqQTBNREEwQXdBVTZzdC1Dd0FBQUE9PSIsImlkIjozMDE0ODIxLCJleHAiOjE2OTYxMTg0MDAsImlhdCI6MTY2NTA4ODU3NCwibml0RGVsZWdhZG8iOjEzNDkyODEwMDE2LCJzdWJzaXN0ZW1hIjoiU0ZFIn0.7WvPt7JmTmK94G1LONeaTuszfj4jsbfG2J3DOVtsPDigKVpmDD75LD1PPr-4uIiniQW7st_E_FDjez1EnXzNwQ',
		'pubCert': '{0}{1}certs{1}{2}'.format(constants.BASE_DIR, constants.SB_DS, 'NUBETIC_SRL_CER.pem'),
		'privCert': '{0}{1}certs{1}{2}'.format(constants.BASE_DIR, constants.SB_DS, 'RUBEN_BALTAZAR_BALDERRAMA.pem')
	}
	'''
	'''
	cfg = {
		# 'modalidad': constants.MOD_COMPUTARIZADA_ENLINEA,
		'modalidad': constants.MOD_ELECTRONICA_ENLINEA,
		'ambiente': constants.AMBIENTE_PRUEBAS,
		'codigoSistema': '71CB9992332DC481EA9D567',
		# 'codigoSistema': '76F8AEACA292284E1AF3567',
		'nombreSistema': 'GEMGLOO',
		'nit': 398134028,
		'razonSocial': 'GEMGLOO',
		'tipo': 'PROVEEDOR',
		# 'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJHZW1nbG9vMjAyMCIsImNvZGlnb1Npc3RlbWEiOiI3NkY4QUVBQ0EyOTIyODRFMUFGMzU2NyIsIm5pdCI6Ikg0c0lBQUFBQUFBQUFETzJ0REEwTmpFd3NnQUFEVHRNUndrQUFBQT0iLCJpZCI6MzAxNDQ5OSwiZXhwIjoxNzAzODk0NDAwLCJpYXQiOjE2NzQ2MDA4NzEsIm5pdERlbGVnYWRvIjozOTgxMzQwMjgsInN1YnNpc3RlbWEiOiJTRkUifQ.p7DpdJRHlIJMrWJ940pwFKKJidbCbAqKLXadsvtb2YOc6K0cyMxOkR5hgBDzw-TmCUn5t9AkObiDXjaf6k7q8A',
		'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJHZW1nbG9vMjAyMCIsImNvZGlnb1Npc3RlbWEiOiI3MUNCOTk5MjMzMkRDNDgxRUE5RDU2NyIsIm5pdCI6Ikg0c0lBQUFBQUFBQUFETzJ0REEwTmpFd3NnQUFEVHRNUndrQUFBQT0iLCJpZCI6MzAxNDQ5OSwiZXhwIjoxNzAzOTgwODAwLCJpYXQiOjE2NzI3OTA3MDksIm5pdERlbGVnYWRvIjozOTgxMzQwMjgsInN1YnNpc3RlbWEiOiJTRkUifQ.LUckRQVRfOQKQxrcc_mWh_N7lIr6DC3pEqYMITH5gSlWC2Hf0FUKJzCHnaUUcug7qNyizb-67kwk3a2zArdo-w',
		'pubCert': '{0}/certs/gemgloo/certificado.pem'.format('/Users/marcelo/secondary/eclipse-workspace/SBFramework/modules/mod_invoices/Classes/Siat'),
		'privCert': '{0}/certs/gemgloo/llave_privada.pem'.format('/Users/marcelo/secondary/eclipse-workspace/SBFramework/modules/mod_invoices/Classes/Siat')
	}
	'''
	cfg = {
		# 'modalidad': constants.MOD_COMPUTARIZADA_ENLINEA,
		'modalidad': constants.MOD_ELECTRONICA_ENLINEA,
		'ambiente': constants.AMBIENTE_PRUEBAS,
		'codigoSistema': '76F8AEACA292284E1AF3567',
		'nombreSistema': 'GEMGLOO V2.0',
		'nit': 398134028,
		'razonSocial': 'GEMGLOO',
		'tipo': 'PROVEEDOR',
		# 'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJHZW1nbG9vMjAyMCIsImNvZGlnb1Npc3RlbWEiOiI3NkY4QUVBQ0EyOTIyODRFMUFGMzU2NyIsIm5pdCI6Ikg0c0lBQUFBQUFBQUFETzJ0REEwTmpFd3NnQUFEVHRNUndrQUFBQT0iLCJpZCI6MzAxNDQ5OSwiZXhwIjoxNzAzODk0NDAwLCJpYXQiOjE2NzQ2MDA4NzEsIm5pdERlbGVnYWRvIjozOTgxMzQwMjgsInN1YnNpc3RlbWEiOiJTRkUifQ.p7DpdJRHlIJMrWJ940pwFKKJidbCbAqKLXadsvtb2YOc6K0cyMxOkR5hgBDzw-TmCUn5t9AkObiDXjaf6k7q8A',
		'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJHZW1nbG9vMjAyMCIsImNvZGlnb1Npc3RlbWEiOiI3NkY4QUVBQ0EyOTIyODRFMUFGMzU2NyIsIm5pdCI6Ikg0c0lBQUFBQUFBQUFETzJ0REEwTmpFd3NnQUFEVHRNUndrQUFBQT0iLCJpZCI6MzAxNDQ5OSwiZXhwIjoxNzAzODk0NDAwLCJpYXQiOjE2NzQ2MDA4NzEsIm5pdERlbGVnYWRvIjozOTgxMzQwMjgsInN1YnNpc3RlbWEiOiJTRkUifQ.p7DpdJRHlIJMrWJ940pwFKKJidbCbAqKLXadsvtb2YOc6K0cyMxOkR5hgBDzw-TmCUn5t9AkObiDXjaf6k7q8A',
		'pubCert': '{0}/certs/gemgloo/certificado.pem'.format('/Users/marcelo/secondary/eclipse-workspace/SBFramework/modules/mod_invoices/Classes/Siat'),
		'privCert': '{0}/certs/gemgloo/llave_privada.pem'.format('/Users/marcelo/secondary/eclipse-workspace/SBFramework/modules/mod_invoices/Classes/Siat')
	}
	return cfg

def testCatalogos():
	cfg = getConfig()
	sucursal = 0
	puntoventa = 0
	resCuis = obtenerCuis(sucursal, puntoventa)
	resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	service = ServiceSincronizacion()
	service.setConfig(cfg)
	service.cuis = resCuis['codigo']
	print(resCuis)
	print(resCufd)
	# resEvents = service.sincronizarParametricaEventosSignificativos(sucursal, puntoventa)
	resEvents = service.sincronizarListaProductosServicios(sucursal, puntoventa)
	print(resEvents)
	
def testRecepcionFactura():
	cfg = getConfig()
	sucursal = 0
	puntoventa = 0
	# codigoActividad = '620900'
	# codigoProductoSin	= '83141'
	codigoActividad = '620100'
	codigoProductoSin	= '83141'
	
	tipoFactura = constants.TIPO_FACTURA_CREDITO_FISCAL
	# documentoSector = constants.TiposDocumentoSector.FACTURA_COMPRA_VENTA
	documentoSector = constants.TiposDocumentoSector.FACTURA_SECTOR_EDUCATIVO
	# documentoSector = constants.TiposDocumentoSector.FACTURA_ALQUILER_INMUEBLES
	
	# resCuis = obtenerCuis(sucursal, puntoventa)
	# resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	factura = construirFactura(
		sucursal, 
		puntoventa, 
		cfg['modalidad'], 
		documentoSector,
		codigoActividad, 
		codigoProductoSin
	)
	
	#xml = factura.toXml()
	#print( tostring(xml, encoding='utf8', method='xml') )
	#dom = parseString( tostring(xml, encoding='utf8', method='xml') )
	#print(dom.toprettyxml())
	try:
		res = recepcionFactura(sucursal, puntoventa, factura, tipoFactura)
		print('RESPONSE RECEPCION', res)
		print('FACTURA CUFD:', factura.cabecera.cuf)
		print('SIAT URL: ', 'https://pilotosiat.impuestos.gob.bo/consulta/QR?nit={0}&cuf={1}&numero={2}&t=1'.format(
			cfg['nit'],
			factura.cabecera.cuf,
			factura.cabecera.numeroFactura
		))
	except SiatException as e:
		print('SIAT ERROR', e.getMessage())
		print('SIAT RESPONSE', e.response)
	except Exception as e:
		print('GENERAL ERROR', e)
		print(traceback.print_exc())

def pruebasEventos():
	cufdAntiguo = 'BQUFDRnFuQUE=NzkZCODY1MzA2Qzc=Q0E3NTdVSUdXVUFFFNzYzOEZGQkUwQ'
	codigoControlAntiguo = '7445D5ADF886D74'
	fechaInicio = datetime.strptime('2022-06-08 09:00:00', '%Y-%m-%d %H:%M:%S')
	fechaFin = datetime.strptime('2022-06-08 09:09:00', '%Y-%m-%d %H:%M:%S')
	sucursal = 0
	puntoventa = 0
	codigoEvento = 1
	resCuis = obtenerCuis(sucursal, puntoventa)
	resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
	evento = obtenerListadoEventos(sucursal, puntoventa, codigoEvento)
	
	res = registroEvento(sucursal, puntoventa, evento, cufdAntiguo, fechaInicio, fechaFin)
	
	print(res)
	
def pruebasPaquetes():
	cufdAntiguo = 'BQUFDRnFuQUE=NzkZCODY1MzA2Qzc=Q0E3NTdVSUdXVUFFFNzYzOEZGQkUwQ'
	codigoControlAntiguo = '7445D5ADF886D74'
	fechaInicio = datetime.strptime('2022-06-08 12:30:00', '%Y-%m-%d %H:%M:%S')
	fechaFin 	= datetime.strptime('2022-06-08 12:39:00', '%Y-%m-%d %H:%M:%S')
	cantidad = 50
	sucursal = 0
	puntoventa = 0
	codigoEvento = 1
	cafc = None
	resEvento = None
	tipoFactura = constants.TIPO_FACTURA_CREDITO_FISCAL
	documentoSector = constants.TiposDocumentoSector.FACTURA_COMPRA_VENTA
	codigoActividad	= '620100';
	codigoProductoSin	= '83141';

	try:
		pvfechaInicio 	= fechaInicio;
		resCuis = obtenerCuis(sucursal, puntoventa)
		resCufd = obtenerCufd(sucursal, puntoventa, resCuis['codigo'])
		evento = obtenerListadoEventos(sucursal, puntoventa, codigoEvento)
		if evento is None:
			raise Exception('No se encontro el evento')
			
		print(evento)
		resEvento = registroEvento(sucursal, puntoventa, evento, cufdAntiguo, fechaInicio, fechaFin)
		if resEvento is None or resEvento['codigoRecepcionEventoSignificativo'] is None:
			raise SiatException(resEvento)
			
		print(resEvento)
		facturas, pvfechaInicio = construirFacturas(
			sucursal, 
			puntoventa,
			cantidad,
			documentoSector,
			codigoActividad,
			codigoProductoSin,
			pvfechaInicio,
			cufdAntiguo,
			cafc
		)
		
		
		res = recepcionPaqueteFactura(sucursal, puntoventa, facturas, codigoControlAntiguo, tipoFactura, resEvento, cafc)
		print(res)
		if res['codigoDescripcion'] == 'PENDIENTE':
			resRecepcion = validacionRecepcionPaquete(sucursal, puntoventa, documentoSector, tipoFactura, res['codigoRecepcion'])
			print(resRecepcion)
		
	except SiatException as e:
		print('SIAT ERROR', e.getMessage())
		print('SIAT RESPONSE', e.response)
	except Exception as e:
		print('GENERAL ERROR', e)
		print(traceback.print_exc())


def test_compras():
	from .classes.siat_compras import SiatCompras
	url = 'https://pilotosiat.impuestos.gob.bo/consulta/QR?nit=1265992017&cuf=569F688AE5DB14FDB32FEC32AE2AC793A86B0206A2729EFB8214AFD74&numero=1&t=2'
	compras = SiatCompras()
	data = compras.parse_url(url)


if __name__ == '__main__':

	print('TMP_DIR: ', constants.TMP_DIR)
	sucursal = 0
	puntoventa = 0
	cfg = getConfig()
	
	__log_file__ = 'nit-{0}.log'.format(cfg['nit'])
	# check for temp directory
	if path.exists(constants.TMP_DIR) == False:
		makedirs(constants.TMP_DIR)
	
	# testCatalogos()
	# testRecepcionFactura()
	# pruebasEventos()
	# pruebasPaquetes()
	test_compras()
