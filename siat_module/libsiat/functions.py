import io
import pytz
import qrcode
import base64
from datetime import datetime

from . import constants
from . import numero_a_letra

def sb_siat_format_datetime(dt: datetime, timezone=pytz.timezone('America/La_Paz')):
	if timezone is None:
		return datetime.strftime(dt, constants.DATETIME_FORMAT)[:-3]

	if not dt.tzinfo:
		return sb_siat_localize_datetime(dt).strftime(constants.DATETIME_FORMAT)[:-3]

	return dt.strftime(constants.DATETIME_FORMAT)[:-3]

def sb_siat_parse_datetime(dt_str, format=None, timezone=pytz.timezone('America/La_Paz')):
	dt = datetime.fromisoformat(dt_str) if format is None else datetime.strptime(dt_str, format)
	
	return sb_siat_localize_datetime(dt, timezone)

def sb_siat_localize_datetime(dt, timezone=pytz.timezone('America/La_Paz')):
	local_dt = dt.astimezone(pytz.utc).astimezone(timezone) if timezone is not None else dt.astimezone(pytz.utc)
	return local_dt
	
def sb_siat_response_message(response):
	message = ''
	
	if response is None or 'mensajesList' not in response:
		message = ''
	else:
		for msg in response['mensajesList']:
			message += '({0}) {1}'.format(msg['codigo'], msg['descripcion'])
	
	return message

def sb_build_qr(text: str):
	qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=30, border=4)
	qr.add_data(text)
	qr.make(fit=True)

	img = qr.make_image(ill_color="black", back_color="white")
	temp = io.BytesIO()
	img.save(temp, format='PNG')
	qr_image = base64.b64encode(temp.getvalue())

	return qr_image

def sb_numeroToLetras(numero):
	if numero == 0:
		return 'CERO ' +  numero_a_letra.to_word(numero)
	return numero_a_letra.to_word(numero)
