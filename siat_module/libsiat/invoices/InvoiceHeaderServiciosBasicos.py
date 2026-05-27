from .invoiceheader import InvoiceHeader
from .. import constants


class InvoiceHeaderServiciosBasicos(InvoiceHeader):

    def __init__(self):
        super().__init__()
        self.nitEmisor=None
        self.razonSocialEmisor=None
        self.municipio=None
        self.telefono=None
        self.numeroFactura=None
        self.cuf=None
        self.cufd=None
        self.codigoSucursal=None
        self.direccion=None
        self.codigoPuntoVenta=None
        self.mes=None
        self.gestion=None
        self.ciudad=None
        self.zona=None
        self.numeroMedidor=None
        self.fechaEmision=None
        self.nombreRazonSocial=None
        self.domicilioCliente=None
        self.codigoTipoDocumentoIdentidad=None
        self.numeroDocumento=None
        self.complemento=None
        self.codigoCliente=None
        self.codigoMetodoPago=None
        self.numeroTarjeta=None
        self.montoTotal=None
        self.montoTotalSujetoIva=None
        self.consumoPeriodo=None
        self.beneficiarioLey1886=None
        self.montoDescuentoLey1886=None
        self.montoDescuentoTarifaDignidad=None
        self.tasaAseo=None
        self.tasaAlumbrado=None
        self.ajusteNoSujetoIva=None
        self.detalleAjusteNoSujetoIva=None
        self.ajusteSujetoIva=None
        self.detalleAjusteSujetoIva=None
        self.otrosPagosNoSujetoIva=None
        self.detalleOtrosPagosNoSujetoIva=None
        self.otrasTasas=None
        self.codigoMoneda=None
        self.tipoCambio=None
        self.montoTotalMoneda=None
        self.descuentoAdicional=None
        self.codigoExcepcion=None
        self.cafc=None
        self.leyenda='Ley Nro 453: Tienes derecho a recibir información sobre las características y contenidos de los servicios que utilices.'
        self.usuario=None
        self.codigoDocumentoSector=constants.TiposDocumentoSector.FACTURA_SERV_BASICOS

        nullables = [
            'mes', 'gestion', 'ciudad', 'zona', 'domicilioCliente', 'consumoPeriodo', 'beneficiarioLey1886',
            'montoDescuentoLey1886', 'montoDescuentoTarifaDignidad', 'tasaAseo', 'tasaAlumbrado',
            'ajusteNoSujetoIva', 'detalleAjusteNoSujetoIva', 'ajusteSujetoIva', 'detalleAjusteSujetoIva',
            'otrosPagosNoSujetoIva', 'detalleOtrosPagosNoSujetoIva', 'otrasTasas'
        ]
        for prop in nullables:
            self._propsAttr[prop] = {'nullable': True}

    def validate(self):
        super().validate()

