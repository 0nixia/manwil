from .CompraVenta import CompraVenta
from .. import constants


class TasaCero(CompraVenta):

    def __init__(self):
        super().__init__();
        self._classAlias = 'facturaComputarizadaTasaCero'
        self._namespaces['xsi:noNamespaceSchemaLocation'] = "facturaComputarizadaTasaCero.xsd"
        self.cabecera = self.instanceHeader()
        self.cabecera.codigoDocumentoSector = constants.TiposDocumentoSector.FACTURA_TASA_CERO_LIBROS

    def instanceDetail(self):
        detail = super().instanceDetail()
        detail.skipProperty('numeroImei')
        detail.skipProperty('numeroSerie')

        return detail