{
    'name': 'Manwil - Reportes Personalizados (Media Carta)',
    'version': '18.0.1.0.0',
    'summary': 'Nota de Almacén y Factura Boliviana en formato Media Carta Horizontal',
    'description': """
Reportes imprimibles independientes para Embutidos Manwil Ticona S.R.L.

- Nota de Entrada/Salida de Almacén (stock.picking)
- Factura de Venta Boliviana (account.move)

Ambos en formato Media Carta Horizontal (216 x 140 mm). Los campos del
módulo SIAT se referencian de forma defensiva: si el módulo SIAT no está
instalado, los reportes se autoadaptan sin fallar.
""",
    'author': 'Onixia',
    'category': 'Onixia/Onixia',
    'license': 'LGPL-3',
    'depends': ['stock', 'account'],
    'data': [
        'report/paperformat.xml',
        'report/report_picking.xml',
        'report/report_invoice.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
