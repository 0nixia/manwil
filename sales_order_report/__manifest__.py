# -*- coding: utf-8 -*-
{
    'name': 'Sales Order Report - Hide Taxes',
    'version': '1.0',
    'category': 'Onixia/Onixia',
    'summary': 'Oculta la columna de impuestos en el reporte de ventas, '
               'muestra precios con IVA incluido y simplifica la tabla de totales.',
    'description': """
    Este módulo personaliza el reporte PDF de Cotizaciones y Órdenes de Venta:
    
    • Oculta la columna "Taxes" en líneas de producto (PDF y portal)
    • Muestra price_total (con IVA) en la columna Amount
    • Muestra únicamente el Total final (sin desglose de subtotal/impuestos)

    Compatible con Odoo 17, 18 y 19 usando archivos de vistas separados.
    No modifica lógica contable ni cálculo de impuestos. 
    """,
    'author': 'ONIXIA S.R.L.',
    'website': '',
    'depends': ['sale'],
    'data': [
        'views/report_sale_views.xml',
        'views/sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}