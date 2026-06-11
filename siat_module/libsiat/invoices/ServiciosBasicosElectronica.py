from .ServiciosBasicos import ServiciosBasicos


class ServiciosBasicosElectronica(ServiciosBasicos):

    def __init__(self):
        super().__init__()
        self._classAlias = 'facturaElectronicaServicioBasico'
        self._namespaces['xsi:noNamespaceSchemaLocation'] = self._classAlias + ".xsd"