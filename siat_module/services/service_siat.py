# -*- coding: utf-8 -*-
import os
import base64
import tempfile
import logging
import base64

_logger = logging.getLogger(__name__)


class ServiceSiat:

    def __init__(self, env):
        if not env:
            raise ValueError("ServiceSiat requires a valid env")

        if not env.company:
            raise ValueError("No active company in env context")

        self.env = env
        self.company = env.company
        self._tmp_files = []

        _logger.debug(
            "ServiceSiat initialized (company=%s, allowed=%s)",
            self.company.id,
            env.context.get('allowed_company_ids')
        )

    def getConfig(self):
        cfg = {}
        try:
            company = self.env.company
            cfg['token']           = company.delegated_token or ''
            cfg['nit']             = company.vat or ''
            cfg['razonSocial']     = company.name or ''
            cfg['ciudad']          = company.city or ''
            cfg['telefono']        = company.phone or company.mobile or 'S/N'

            cfg['codigoSistema']   = company.siat_system_code or ''
            cfg['codigoAmbiente']  = int(company.siat_environment) if company.siat_environment else 2
            cfg['nombreSistema']   = company.siat_system_name or ''
            cfg['codigoModalidad'] = int(company.siat_mode) if company.siat_mode else 2
            cfg['cafc']            = company.siat_cafc or ''
            cfg['siat_email']      = company.siat_email or ''
            cfg['siat_email_name'] = company.siat_email_name or ''

            cfg['pubCert']  = self._binary_to_tempfile(company.siat_cert_file, 'cert_') if company.siat_cert_file else None
            cfg['privCert'] = self._binary_to_tempfile(company.siat_pk_file,   'pk_')   if company.siat_pk_file   else None

            _logger.info("SIAT CONFIG (company=%s, nit=%s)", company.name, cfg['nit'])

        except Exception:
            _logger.exception("SIAT CONFIG ERROR")
            raise

        return cfg

    def _binary_to_tempfile(self, binary_data, prefix='siat_'):
        if not binary_data:
            raise ValueError("No binary data provided for tempfile creation")
        try:
            if isinstance(binary_data, str):
                data_bytes = binary_data.encode()
            elif isinstance(binary_data, bytes):
                data_bytes = binary_data
            else:
                raise TypeError(f"Unsupported binary_data type: {type(binary_data)}")
            try:
                decoded = base64.b64decode(data_bytes, validate=True)
                if decoded.startswith(b'-----') or decoded[:1] == b'\x30':
                    raw = decoded
                    _logger.debug("SIAT: binary_data detectado como base64 válido")
                else:
                    raw = data_bytes
                    _logger.debug("SIAT: binary_data no parece base64 válido, usando original")
            except Exception:
                raw = data_bytes
                _logger.debug("SIAT: binary_data tratado como binario directo")
            if not (raw.startswith(b'-----') or raw[:1] == b'\x30'):
                _logger.warning(
                    "SIAT: contenido no parece PEM ni DER válido. Inicio: %s",
                    raw[:30]
                )
            tmp = tempfile.NamedTemporaryFile(delete=False, prefix=prefix)
            tmp.write(raw)
            tmp.flush()
            tmp.close()
            self._tmp_files.append(tmp.name)
            _logger.debug("Temporary file created: %s", tmp.name)
            return tmp.name
        except Exception:
            _logger.exception("SIAT _binary_to_tempfile ERROR")
            raise

    def file_get_contents(self, filename):
        if not os.path.isfile(filename):
            return ''
        with open(filename, 'rb') as f:
            return f.read().decode()
        
    def cleanup(self):
        """Clean up temporary files created during initialization."""
        for tmp_file in self._tmp_files:
            try:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
                    _logger.debug("Temporary file deleted: %s", tmp_file)
            except Exception:
                _logger.warning("Failed to delete temporary file: %s", tmp_file, exc_info=True)
        self._tmp_files = []