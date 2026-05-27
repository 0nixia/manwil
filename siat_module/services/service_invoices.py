import base64
import logging
from datetime import datetime, timedelta

from odoo import _, tools, Command
from odoo.exceptions import UserError
from odoo.tools import float_round

from .service_siat import ServiceSiat
from .service_siat_sync import ServiceSiatSync
from ..models.mail_template import SiatMailTemplate
from ..libsiat.classes.siat_factory import SiatFactory
from ..libsiat import functions as siat_functions
from ..libsiat import constants as siat_constants
from ..libsiat.classes.siat_exception import SiatException, SiatExceptionInvalidNit
from ..models.siat_utils import get_siat_employee_config

_logger = logging.getLogger(__name__)


class ServiceInvoices(ServiceSiat):
	
	def __init__(self, env):
		super().__init__(env)
		self.serviceSync = ServiceSiatSync(env)
	
	def siatInvoiceToInvoice(self, facturaSiat):
		total_tax = float_round(facturaSiat.cabecera.montoTotal * 0.13, precision_digits=2, rounding_method='HALF-EVEN')
		#TODO: Remove "activity_economic" field
		invoice = {
			'invoice_number': facturaSiat.cabecera.numeroFactura,
			'codigo_sucursal': facturaSiat.cabecera.codigoSucursal,
			'punto_venta': facturaSiat.cabecera.codigoPuntoVenta,
			'codigo_documento_sector': facturaSiat.cabecera.codigoDocumentoSector,
			'tipo_documento_identidad': facturaSiat.cabecera.codigoTipoDocumentoIdentidad,
			'codigo_metodo_pago': facturaSiat.cabecera.codigoMetodoPago,
			'codigo_moneda': facturaSiat.cabecera.codigoMoneda,
			'package_id': 0,
			'tipo_factura_documento': 0,
			'ambiente': 2,
			'nit_ruc_nif': facturaSiat.cabecera.numeroDocumento,
			'control_code': '',
			'status': siat_constants.InvoiceStatus.INVOICE_ISSUED,
			'cufd': facturaSiat.cabecera.cufd,
			'cuf': facturaSiat.cabecera.cuf,
			'cafc': facturaSiat.cabecera.cafc,
			'complemento': facturaSiat.cabecera.complemento,
			'numero_tarjeta': facturaSiat.cabecera.numeroTarjeta,
			'siat_id': '',
			'tipo_emision': 0,
			'nit_emisor': facturaSiat.cabecera.nitEmisor,
			'leyenda': facturaSiat.cabecera.leyenda,
			'subtotal': 0,
			'total_tax': total_tax,
			'discount': facturaSiat.cabecera.descuentoAdicional,
			'monto_giftcard': facturaSiat.cabecera.montoGiftCard,
			'tipo_cambio': facturaSiat.cabecera.tipoCambio,
			'invoice_datetime': datetime.strptime(facturaSiat.cabecera.fechaEmision, siat_constants.DATETIME_FORMAT),
			'total': facturaSiat.cabecera.montoTotal,
			'customer_name': facturaSiat.cabecera.nombreRazonSocial,
			'data': {
				'excepcion': facturaSiat.cabecera.codigoExcepcion,
				'nro_cafc': None
			}
		}
		
		return invoice
	
	def siatDetailToInvoiceDetail(self, invoiceDetail):
		item = {
			'product_id': 0,
			'product_code': invoiceDetail.codigoProducto,
			'codigo_producto_sin': invoiceDetail.codigoProductoSin,
			'unidad_medida': invoiceDetail.unidadMedida,
			'product_name': invoiceDetail.descripcion,
			'codigo_actividad': invoiceDetail.actividadEconomica,
			'numero_seria': '',
			'numero_imei': '',
			'nandina': '',
			'price': invoiceDetail.precioUnitario,
			'quantity': invoiceDetail.cantidad,
			'subtotal': float_round((invoiceDetail.precioUnitario * invoiceDetail.cantidad), precision_digits=2, rounding_method='HALF-EVEN'),
			'discount': invoiceDetail.montoDescuento,
			'total': invoiceDetail.subTotal,
		}
		
		return item

	def requestDataToSiatInvoice(self, invoiceData, config):
		facturaSiat = SiatFactory.construirFactura(invoiceData['codigo_documento_sector'], config['codigoModalidad'])
		facturaSiat.cabecera.leyenda = None

		for item in invoiceData['items']:
			if not item.get('codigo_actividad', ''):
				raise Exception(
					'El producto {0} no tiene asignado actividad economica'.format(item.get('product_name')))
			if int(item.get('codigo_producto_sin', 0)) <= 0:
				raise Exception('El producto {0} no tiene asignado codigo SIN'.format(item.get('product_name')))
			if int(item.get('unidad_medida', 0)) <= 0:
				raise Exception(
					'El producto {0} no tiene asignado Unidad de Medida SIN'.format(item.get('product_name')))

			detalleSiat = facturaSiat.instanceDetail()
			detalleSiat.actividadEconomica = item['codigo_actividad']
			detalleSiat.codigoProductoSin = item['codigo_producto_sin']
			detalleSiat.codigoProducto = item['product_code']
			detalleSiat.descripcion = item['product_name']
			detalleSiat.cantidad = item['quantity']
			detalleSiat.unidadMedida = item['unidad_medida']
			detalleSiat.precioUnitario = item['price']
			detalleSiat.montoDescuento = item['discount']
			detalleSiat.subTotal = round((float_round((item['quantity'] * item['price']), precision_digits=2, rounding_method='HALF-EVEN')) - (float_round((item['discount']), precision_digits=2)), 2)
			detalleSiat.numeroSerie = item.get('numero_serie', '')
			detalleSiat.numeroImei = item['numero_imei']
			_logger.debug('DETALLE: %s %s %s %s', detalleSiat.subTotal, item['quantity'], item['price'], item['discount'])

			if detalleSiat.montoDescuento >= detalleSiat.subTotal:
				raise Exception(
					'El descuento del item {0} no puede ser igual o mayor al subtotal'.format(item.get('product_name')))

			facturaSiat.detalle.append(detalleSiat)

			if facturaSiat.cabecera.leyenda is None:
				facturaSiat.cabecera.leyenda = self.serviceSync.leyenda_aleatoria(detalleSiat.actividadEconomica)

		facturaSiat.cabecera.nitEmisor = config['nit']
		facturaSiat.cabecera.razonSocialEmisor = config['razonSocial']
		facturaSiat.cabecera.municipio = config['ciudad']
		facturaSiat.cabecera.telefono = config['telefono']
		facturaSiat.cabecera.numeroFactura = self.env['siat.invoice'].nextInvoiceNumber(
			invoiceData['punto_venta'],
			invoiceData['codigo_sucursal'],
		)
		facturaSiat.cabecera.codigoSucursal = invoiceData['codigo_sucursal']
		facturaSiat.cabecera.codigoPuntoVenta = invoiceData['punto_venta']
		facturaSiat.cabecera.nombreRazonSocial = invoiceData['customer']
		facturaSiat.cabecera.codigoTipoDocumentoIdentidad = invoiceData['tipo_documento_identidad']
		facturaSiat.cabecera.numeroDocumento = invoiceData['nit_ruc_nif']
		facturaSiat.cabecera.complemento = invoiceData['complemento']
		facturaSiat.cabecera.codigoMetodoPago = invoiceData['codigo_metodo_pago']
		facturaSiat.cabecera.numeroTarjeta = invoiceData['numero_tarjeta']
		facturaSiat.cabecera.montoTotal = invoiceData['total']
		facturaSiat.cabecera.montoGiftCard = invoiceData['monto_giftcard'] if invoiceData['monto_giftcard'] > 0 else None
		facturaSiat.cabecera.montoTotalSujetoIva = facturaSiat.cabecera.montoTotal - (facturaSiat.cabecera.montoGiftCard if facturaSiat.cabecera.montoGiftCard else 0)
		facturaSiat.cabecera.codigoMoneda = invoiceData['codigo_moneda']
		facturaSiat.cabecera.tipoCambio = invoiceData['tipo_cambio']
		facturaSiat.cabecera.montoTotalMoneda = facturaSiat.cabecera.montoTotal * facturaSiat.cabecera.tipoCambio
		facturaSiat.cabecera.descuentoAdicional = invoiceData['discount']
		facturaSiat.cabecera.codigoExcepcion = invoiceData['data']['excepcion'] if invoiceData['data']['excepcion'] == 1 else 0
		facturaSiat.cabecera.cafc = None
		facturaSiat.cabecera.usuario = None

		return facturaSiat

	def invoiceToSiatInvoice(self, invoice):
		config = self.getConfig()
		siatInvoice = SiatFactory.construirFactura(
			invoice.codigo_documento_sector,
			config.get('codigoModalidad')
		)
		cufd = self.env['siat.cufd_code'].get_by_code(invoice.cufd)
    
		if not cufd:
			raise Exception('No se puede contruir la factura SIAT, el CUFD de la factura no existe')
		
		_emp, _pos_rec, _pos_code, _sucursal, login = get_siat_employee_config(self.env)
		siatInvoice.cabecera.usuario = login
		siatInvoice.cabecera.direccion				= cufd.address
		siatInvoice.cabecera.municipio				= config.get('ciudad')
		siatInvoice.cabecera.telefono				= config.get('telefono')
		siatInvoice.cabecera.nitEmisor				= invoice.nit_emisor
		siatInvoice.cabecera.razonSocialEmisor		= config.get('razonSocial')
		siatInvoice.cabecera.numeroFactura			= invoice.invoice_number
		siatInvoice.cabecera.fechaEmision			= siat_functions.sb_siat_format_datetime(invoice.invoice_datetime, None)
		siatInvoice.cabecera.cufd 					= invoice.cufd
		siatInvoice.cabecera.cuf 					= invoice.cuf
		siatInvoice.cabecera.montoTotal 			= invoice.total
		siatInvoice.cabecera.leyenda				= invoice.leyenda
		siatInvoice.cabecera.cafc					= None if not invoice.cafc else invoice.cafc
		customer = invoice.get_customer()
		siatInvoice.cabecera.codigoCliente = customer.id if customer else None
		siatInvoice.cabecera.nombreRazonSocial 		= invoice.customer_name
		siatInvoice.cabecera.numeroDocumento		= invoice.nit_ruc_nif
		siatInvoice.cabecera.complemento			= None if not invoice.complemento else invoice.complemento
		siatInvoice.cabecera.codigoDocumentoSector 	= invoice.codigo_documento_sector
		siatInvoice.cabecera.codigoMetodoPago		= invoice.codigo_metodo_pago
		siatInvoice.cabecera.codigoMoneda			= invoice.codigo_moneda
		siatInvoice.cabecera.codigoSucursal			= invoice.codigo_sucursal
		siatInvoice.cabecera.codigoPuntoVenta		= invoice.punto_venta
		siatInvoice.cabecera.codigoTipoDocumentoIdentidad	= invoice.tipo_documento_identidad
		siatInvoice.cabecera.montoGiftCard					= invoice.monto_giftcard
		siatInvoice.cabecera.tipoCambio				= invoice.tipo_cambio
		siatInvoice.cabecera.descuentoAdicional		= invoice.discount
		siatInvoice.cabecera.montoTotal				= invoice.total
		siatInvoice.cabecera.montoTotalMoneda		= invoice.total * invoice.tipo_cambio
		siatInvoice.cabecera.montoTotalSujetoIva	= invoice.total - (invoice.monto_giftcard if invoice.monto_giftcard else 0)
		siatInvoice.cabecera.numeroTarjeta			= None if not invoice.numero_tarjeta else invoice.numero_tarjeta
		siatInvoice.cabecera.codigoExcepcion		= invoice.get_data('excepcion')

		for item in invoice.items:
			siatDetalle = siatInvoice.instanceDetail()
			siatDetalle.descripcion 		= item.product_name
			siatDetalle.montoDescuento 		= item.discount
			siatDetalle.precioUnitario 		= item.price
			siatDetalle.subTotal			= item.total
			siatDetalle.unidadMedida		= item.unidad_medida
			siatDetalle.codigoProducto 		= item.product_code
			siatDetalle.actividadEconomica	= item.codigo_actividad
			siatDetalle.codigoProductoSin	= item.codigo_producto_sin
			siatDetalle.cantidad			= item.quantity

			siatInvoice.detalle.append( siatDetalle )

		return siatInvoice

	def create(self, invoiceData):
		current_user = self.env.user
		config 		= self.getConfig()

		sucursal 	= invoiceData['codigo_sucursal']
		puntoventa 	= invoiceData['punto_venta']

		customer_model = 'siat.client' if invoiceData.get('is_invoicer') else 'res.partner'
		customer = self.env[customer_model].browse(invoiceData['customer_id'])
	
		cuis 		= self.serviceSync.sync_cuis(sucursal, puntoventa)
		cufd 		= self.serviceSync.sync_cufd(sucursal, puntoventa)
		if cufd.is_expired():
			raise UserError(
				f'El CUFD para sucursal={sucursal} / PV={puntoventa} está vencido '
				f'(expiró: {cufd.ended_date} UTC). '
				'El sistema no pudo renovarlo automáticamente. '
				'Verifique la conexión con el SIN o contacte al administrador.'
			)

		_logger.info(
			'create | company=%d branch=%d pos=%d | '
			'usando CUFD id=%d (%d min restantes)',
			self.env.company.id, sucursal, puntoventa,
			cufd.id, cufd.minutes_remaining(),
		)

		activeEvent = self._eventoActivo(sucursal, puntoventa)

		facturaSiat = self.requestDataToSiatInvoice(invoiceData, config)
		facturaSiat.cabecera.usuario = current_user.login
		facturaSiat.cabecera.cufd = cufd.cufd_code
		facturaSiat.cabecera.direccion = cufd.address 
		facturaSiat.cabecera.fechaEmision = siat_functions.sb_siat_format_datetime(datetime.now())
		facturaSiat.cabecera.codigoCliente = customer.id

		invoice_dict = None

		if activeEvent is not None:
			if invoiceData['tipo_documento_identidad'] == 5:
				facturaSiat.cabecera.codigoExcepcion = 1
			cufd_evento = activeEvent.get_cufd_evento()
			if not cufd_evento:
				raise UserError(
					"El evento de contingencia activo (código {}) no tiene un CUFD asociado. "
					"Debe registrar manualmente el CUFD de contingencia en el formulario del evento "
					"antes de emitir facturas en este modo.".format(activeEvent.evento_id)
				)
			if activeEvent.evento_id in ['5', '6', '7']:
				if not invoiceData['siat_num_invoice'] or not invoiceData['siat_date_invoice']:
					raise UserError("Se detectó un evento de contingencia, debe ingresar manualmente el número y fecha de la factura en los campos asignados")
				facturaSiat.cabecera.cafc = config['cafc']

				facturaSiat.cabecera.numeroFactura = invoiceData['siat_num_invoice']
				facturaSiat.cabecera.fechaEmision = siat_functions.sb_siat_format_datetime(invoiceData['siat_date_invoice'])
			facturaSiat.buildCuf(
				config['codigoModalidad'],
				siat_constants.TIPO_EMISION_OFFLINE,
				siat_constants.TIPO_FACTURA_CREDITO_FISCAL,
				cufd_evento.control_code
			)
			facturaSiat.validate()
			invoice_dict = self.siatInvoiceToInvoice(facturaSiat)
			invoice_dict['tipo_emision'] = siat_constants.TIPO_EMISION_OFFLINE
			invoice_dict['control_code'] = cufd_evento.control_code
			invoice_dict['evento_id'] = activeEvent.id

		else:
			if invoiceData['tipo_documento_identidad'] == 5 and invoiceData['data'].get('excepcion', 0) != 1:
				service_codes = self.serviceSync.getSiatServiceCodes()
				service_codes.cuis = cuis['codigo']
				res = service_codes.verificarNit(invoiceData['nit_ruc_nif'])
				if res['mensajesList'][0]['codigo'] == 994:
					raise SiatExceptionInvalidNit(res, 'El NIT "{0}" no es valido'.format(invoiceData['nit_ruc_nif']))

			serviceFacturacion = SiatFactory.obtenerServicioFacturacion(
                config, 
                cuis['codigo'], 
                cufd.cufd_code,
                cufd.control_code
            )
			siat_response = serviceFacturacion.recepcionFactura(facturaSiat, siat_constants.TIPO_EMISION_ONLINE, siat_constants.TIPO_FACTURA_CREDITO_FISCAL)
			if siat_response is None:
				raise Exception('SIAT ERROR: Respuesta de impuestos invalida')
			if siat_response['codigoEstado'] != 908:
				_logger.debug('XML de factura: %s', serviceFacturacion.buildInvoiceXml(facturaSiat).decode('utf-8'))
				raise Exception( siat_functions.sb_siat_response_message(siat_response) )
		
			invoice_dict = self.siatInvoiceToInvoice(facturaSiat)
			invoice_dict['siat_id'] 		= siat_response['codigoRecepcion']
			invoice_dict['tipo_emision'] 	= siat_constants.TIPO_EMISION_ONLINE
			invoice_dict['control_code']	= cufd.control_code

		invoice_dict['is_invoicer'] = 'is_invoicer' in invoiceData
		if invoiceData.get('is_invoicer'):
			invoice_dict['client_id'] = customer.id
		else:
			invoice_dict['partner_id'] = customer.id
		invoice_dict['tipo_factura_documento'] = siat_constants.TIPO_FACTURA_CREDITO_FISCAL
		invoice_dict['ambiente'] = config['codigoAmbiente']
		invoice_dict['company_id'] = self.env.company.id
		
		invoice = self.env['siat.invoice'].create(invoice_dict)
		subtotal = 0
		for request_item in invoiceData['items']:
			invoice_item = {
				'invoice_id': invoice.id,
				'product_id': request_item['product_id'],
				'product_code': request_item['product_code'],
				'codigo_producto_sin': request_item['codigo_producto_sin'],
				'unidad_medida': request_item['unidad_medida'],
				'product_name': request_item['product_name'],
				'codigo_actividad': request_item['codigo_actividad'],
				'numero_seria': request_item.get('numero_serie', ''),
				'numero_imei': request_item['numero_imei'],
				'nandina': request_item.get('nandina', ''),
				'price': request_item['price'],
				'quantity': request_item['quantity'],
				'subtotal': float_round((request_item['price'] * request_item['quantity']), precision_digits=2, rounding_method='HALF-EVEN'),
				'discount': request_item['discount'],
				'total': float_round((request_item['price'] * request_item['quantity']), precision_digits=2, rounding_method='HALF-EVEN') - request_item['discount'],
			}
			self.env['siat.invoiceitem'].create(invoice_item)
			subtotal += (float_round((request_item['price'] * request_item['quantity']), precision_digits=2, rounding_method='HALF-EVEN') - request_item['discount'])

		invoice.write({'subtotal': subtotal})
		return invoice

	def build_xml_for_invoice(self, invoice):
		try:
			cufd_record = self.env['siat.cufd_code'].get_by_code(invoice.cufd)
			if not cufd_record:
				cufd_record = self.serviceSync.sync_cufd(invoice.codigo_sucursal, invoice.punto_venta)
			cuis = self.serviceSync.sync_cuis(invoice.codigo_sucursal, invoice.punto_venta)
			service = SiatFactory.obtenerServicioFacturacion(
				self.getConfig(),
				cuis['codigo'],
				cufd_record.cufd_code,	
				cufd_record.control_code,
			)
			siat_invoice = self.invoiceToSiatInvoice(invoice)
			return service.buildInvoiceXml(siat_invoice)
		except Exception:
			_logger.exception('build_xml_for_invoice | invoice=%d | ERROR', invoice.id)
			return None

	def send_customer_email(self, invoice):
		cufd_record = self.env['siat.cufd_code'].get_by_code(invoice.cufd)
		if not cufd_record:
			_logger.warning("CUFD record not found for invoice %s, syncing...", invoice.id)
			cufd_record = self.serviceSync.sync_cufd(invoice.codigo_sucursal, invoice.punto_venta)
			cuis_code = self.serviceSync.sync_cuis(invoice.codigo_sucursal, invoice.punto_venta)['codigo']
		else:
			cuis = self.serviceSync.sync_cuis(invoice.codigo_sucursal, invoice.punto_venta)
			cuis_code = cuis['codigo']

		service = SiatFactory.obtenerServicioFacturacion(
			self.getConfig(),
			cuis_code,
			cufd_record.cufd_code,
			cufd_record.control_code
		)

		config = self.getConfig()
		company_email = config.get('siat_email') or invoice.company_id.email or invoice.company_id.partner_id.email
		sender_name = config.get('siat_email_name') or invoice.company_id.name
		customer = invoice.get_customer()
		siat_invoice = self.invoiceToSiatInvoice(invoice)
		xml = service.buildInvoiceXml(siat_invoice)
		email_from = f"{sender_name} <{company_email}>"

		report_template = self.env.ref('siat_module.siat_invoicer_report')
		pdf_content, _dummy = self.env['ir.actions.report']._render_qweb_pdf(
			report_template.id, [invoice.id]
		)

		email_template = self.env.ref('siat_module.siat_invoice_email_template')
		move = invoice.account_move_id

		if move:
			xml_att = self.env['ir.attachment'].create({
				'name': 'FACTURA_{0}_{1}.xml'.format(invoice.company_id.name, invoice.invoice_number),
				'datas': base64.b64encode(xml),
				'mimetype': 'application/xml',
				'res_model': 'account.move',
				'res_id': move.id,
				'type': 'binary',
			})
			pdf_att = self.env['ir.attachment'].create({
				'name': 'FACTURA_{0}_{1}.pdf'.format(invoice.company_id.name, invoice.invoice_number),
				'datas': base64.b64encode(pdf_content),
				'mimetype': 'application/pdf',
				'res_model': 'account.move',
				'res_id': move.id,
				'type': 'binary',
			})

			body_rendered = email_template._render_field(
				'body_html', [invoice.id], compute_lang=True,
			)[invoice.id]
			subject_rendered = email_template._render_field(
				'subject', [invoice.id], compute_lang=True,
			)[invoice.id]

			recipient_ids = [customer.id] if (customer and customer.email) else []

			move.with_context(mail_post_autofollow=True).message_post(
				body=body_rendered,
				subject=subject_rendered,
				partner_ids=recipient_ids,
				attachment_ids=[xml_att.id, pdf_att.id],
				message_type='comment',
				subtype_xmlid='mail.mt_comment',
				email_from=email_from,
			)
		else:
			xml_att = self.env['ir.attachment'].create({
				'name': 'FACTURA_{0}_{1}.xml'.format(invoice.company_id.name, invoice.invoice_number),
				'datas': base64.b64encode(xml),
				'mimetype': 'application/xml',
				'res_model': 'mail.compose.message',
				'type': 'binary',
			})
			pdf_att = self.env['ir.attachment'].create({
				'name': 'FACTURA_{0}_{1}.pdf'.format(invoice.company_id.name, invoice.invoice_number),
				'datas': base64.b64encode(pdf_content),
				'mimetype': 'application/pdf',
				'res_model': 'mail.compose.message',
				'type': 'binary',
			})
			ctx = {
				'email_from': email_from,
				'email_to': customer.email if customer else False,
				'attachment_ids': [(4, xml_att.id), (4, pdf_att.id)],
			}
			email_template.send_mail(invoice.id, force_send=True, email_values=ctx)
	def void_by_cuf(self, cuf: str, reason_cancellation: int):
		invoice = self.env['siat.invoice'].search([('cuf', '=', cuf)], limit=1)
		if not invoice:
			raise UserError(_('No se encontró ninguna factura con el CUF %s') % cuf)

		self.env = self.env['siat.invoice'].with_company(invoice.company_id).env

		config = self.getConfig()
		cuis = self.serviceSync.sync_cuis(invoice.codigo_sucursal, invoice.punto_venta)
		cufd = self.serviceSync.sync_cufd(invoice.codigo_sucursal, invoice.punto_venta)
		service = SiatFactory.obtenerServicioFacturacion(
			config,
			cuis['codigo'],
			cufd.cufd_code,
			cufd.control_code
		)
		service.debug = True

		res = service.anulacionFactura(
			reason_cancellation,
			cuf,
			invoice.codigo_sucursal,
			invoice.punto_venta,
			invoice.tipo_factura_documento,
			invoice.tipo_emision,
			invoice.codigo_documento_sector
		)

		if res['codigoEstado'] != 905:
			_logger.error('Error anulando factura: %s', res)
			mensajes = res.get('mensajesList', [])
			if isinstance(mensajes, dict):
				mensajes = [mensajes]
			if isinstance(mensajes, list):
				already_voided = any(
					isinstance(m, dict) and m.get('codigo') == 936
					for m in mensajes
				)
				if already_voided:
					raise UserError(_(
						"La factura asociada a este CUF ya se encuentra registrada "
						"como ANULADA en el portal de Impuestos Nacionales (SIAT)."
					))
			raise UserError(_('No se pudo anular la factura: %s') % mensajes)

		_logger.info('Factura anulada exitosamente: %s', res)
		void_datetime = siat_functions.sb_siat_format_datetime(datetime.now())
		invoice.write({
			'status': siat_constants.InvoiceStatus.INVOICE_VOID,
			'void_datetime': datetime.strptime(void_datetime, siat_constants.DATETIME_FORMAT),
			'void_reason': str(reason_cancellation)
		})
		self.send_customer_void_email(invoice)
		return invoice

	def void(self, id: int, motivo_anulacion: int):
		invoices = self.env['siat.invoice'].browse(id)
		if len(invoices) <= 0:
			raise Exception('La factura no existe')
		invoice = invoices[0]

		config = self.getConfig()
		cuis = self.serviceSync.sync_cuis(invoice.codigo_sucursal, invoice.punto_venta)
		cufd = self.serviceSync.sync_cufd(invoice.codigo_sucursal, invoice.punto_venta)
		service = SiatFactory.obtenerServicioFacturacion(
			config,
			cuis['codigo'],
			cufd.cufd_code,
			cufd.control_code
		)
		service.debug = True
		res = service.anulacionFactura(
			motivo_anulacion,
			invoice.cuf,
			invoice.codigo_sucursal,
			invoice.punto_venta,
			invoice.tipo_factura_documento,
			invoice.tipo_emision,
			invoice.codigo_documento_sector
		)

		if res['codigoEstado'] != 905:
			_logger.error('SIAT ANULAR ERROR: %s', res)
			raise Exception('No se puedo anular la factura')

		_logger.info('SIAT VOID RES: %s', res) 
		void_datetime = siat_functions.sb_siat_format_datetime(datetime.now())
		invoice.write({
			'status': siat_constants.InvoiceStatus.INVOICE_VOID,
			'void_datetime': datetime.strptime(void_datetime, siat_constants.DATETIME_FORMAT),
			'void_reason': motivo_anulacion
		})
		self.send_customer_void_email(invoice)

		return invoice

	def send_customer_void_email(self, invoice):
		data = {}
		email_template = self.env.ref('siat_module.siat_invoice_void_email_template')
		email_template[0].send_mail(invoice.id, force_send=True, email_values=data)

	def revert_void(self, id):
		invoices = self.env['siat.invoice'].browse(id)
		if len(invoices) <= 0:
			raise Exception('La factura no existe')
		invoice = invoices[0]

		config = self.getConfig()
		cuis = self.serviceSync.sync_cuis(invoice.codigo_sucursal, invoice.punto_venta)
		cufd = self.serviceSync.sync_cufd(invoice.codigo_sucursal, invoice.punto_venta)
		service = SiatFactory.obtenerServicioFacturacion(
			config,
			cuis['codigo'],
			cufd.cufd_code,
			cufd.control_code
		)
		res = service.reversionAnulacionFactura(
			invoice.codigo_sucursal,
			invoice.punto_venta,
			invoice.codigo_documento_sector,
			siat_constants.TIPO_EMISION_ONLINE,
			invoice.tipo_factura_documento,
			invoice.cuf,
		)
		if res['codigoEstado'] != 907:
			raise Exception('No se pudo revertir la anulacion de factura')
		_logger.info('SIAT REVERSION RES: %s', res)
		invoice.write({
			'status': siat_constants.InvoiceStatus.INVOICE_REVERTED,
		})
		self.send_customer_email(invoice)
		return invoice

	def _eventoActivo(self, sucursal=0, puntoventa=0):
		items = self.env['siat.event'].search([
			('sucursal_id', '=', sucursal),
			('point_of_sale_id', '=', f'T{puntoventa}'),
			('status', 'ilike', siat_constants.EventStatus.STATUS_OPEN),
		], limit=1)
		if len(items) <= 0:
			return None
		return items[0]