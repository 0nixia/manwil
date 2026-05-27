from .resource import SiatResource

class ResourceEvent(SiatResource):

    _serializable =  ['id', 'evento_id', 'sucursal_id', 'puntoventa_id', 'codigo_reception', 'descripcion',
        'cufd', 'cufd_evento', 'codigo_recepcion_paquete', 'estado_recepcion', 'fecha_inicio', 'fecha_fin',
        'status', 'data', 'creation_date', 'last_modification_date', 'packages'
    ]

    def __init__(self, data):
        self.packages = []
        self._object = data
        self.setData()

    def setData(self):
        self.bind(self._object.read()[0])
        self.creation_date = self.create_date
        self.last_modification_date = self.write_date
        self.packages = []
        for pkg in self._object.packages:
            self.packages.append( pkg.read()[0] )

