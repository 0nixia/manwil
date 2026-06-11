# -*- coding: utf-8 -*-
import logging
from lxml import etree
from xml.dom.minidom import parseString
from signxml import XMLSigner, methods

from .service_facturacion import ServiceFacturacion
from ..invoices.siatinvoice import SiatInvoice

_logger = logging.getLogger(__name__)


class ServiceFacturacionElectronica(ServiceFacturacion):

    def __init__(self):
        super().__init__()
        self.privateCertFile = None
        self.publicCertFile = None

    def setConfig(self, data):
        super().setConfig(data)
        self.publicCertFile  = data.get('pubCert')
        self.privateCertFile = data.get('privCert')

    def validate(self):
        super().validate()
        if not self.publicCertFile:
            raise Exception('Archivo de certificado público no configurado')
        if not self.privateCertFile:
            raise Exception('Archivo de llave privada no configurado')

    def _load_private_key(self, file_path):
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key,
            load_der_private_key,
            Encoding,
            PrivateFormat,
            NoEncryption,
        )
        from cryptography.hazmat.backends import default_backend
        with open(file_path, 'rb') as f:
            raw = f.read()
        if raw[:1] == b'\x30' and not raw.lstrip().startswith(b'-----'):
            try:
                from cryptography.hazmat.primitives.serialization.pkcs12 import (
                    load_key_and_certificates,
                )
                private_key, _, _ = load_key_and_certificates(
                    raw, None, default_backend()
                )
                _logger.info("SIAT: clave cargada desde PKCS#12")
                return private_key.private_bytes(
                    Encoding.PEM,
                    PrivateFormat.TraditionalOpenSSL,
                    NoEncryption()
                ).decode('utf-8')
            except Exception as e:
                _logger.warning("SIAT: no es PKCS#12 válido: %s", e)
        if raw.lstrip().startswith(b'-----'):
            try:
                key_obj = load_pem_private_key(
                    raw,
                    password=None,
                    backend=default_backend()
                )
                _logger.info("SIAT: clave PEM cargada")
                return key_obj.private_bytes(
                    Encoding.PEM,
                    PrivateFormat.TraditionalOpenSSL,
                    NoEncryption()
                ).decode('utf-8')
            except Exception as e:
                raise ValueError(
                    "Error cargando clave PEM (¿está cifrada?).\n"
                    f"Detalle: {e}"
                ) from e
        try:
            key_obj = load_der_private_key(
                raw,
                password=None,
                backend=default_backend()
            )
            _logger.info("SIAT: clave DER convertida a PEM")
            return key_obj.private_bytes(
                Encoding.PEM,
                PrivateFormat.TraditionalOpenSSL,
                NoEncryption()
            ).decode('utf-8')
        except Exception:
            pass
        raise ValueError(
            f"Formato de llave privada no reconocido: {file_path}"
        )

    def buildInvoiceXml(self, invoice: SiatInvoice):
        with open(self.publicCertFile, 'rb') as f:
            pubCertBuffer = f.read().decode('utf-8')
        privKeyBuffer = self._load_private_key(self.privateCertFile)
        xml = super().buildInvoiceXml(invoice)
        self.debugData('UNSIGNED XML')
        self.debugData(xml.decode('utf-8'))
        root = etree.fromstring(xml)
        signer = XMLSigner(
            method=methods.enveloped,
            c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
            signature_algorithm='rsa-sha256',
            digest_algorithm='sha256',
        )
        signer.namespaces = None
        signed_root = signer.sign(
            root,
            key=privKeyBuffer,
            cert=pubCertBuffer,
            always_add_key_value=False,
        )
        signed_xml = etree.tostring(
            signed_root,
            encoding='utf-8',
            method='xml',
            xml_declaration=True
        )
        dom = parseString(signed_xml)
        self.debugData('SIGNED XML')
        self.debugData(dom.toprettyxml())
        return signed_xml