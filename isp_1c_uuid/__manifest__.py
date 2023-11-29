# -*- coding: utf-8 -*-
{
    'name': "Odoo UUID 1C",

    'summary': """
        Add UUID to some models""",

    'description': """
        Add UUID to some models
    """,

    'author': "Oleksandr Huryn",
    'website': "itspectr.com.ua",

    'category': 'Uncategorized',
    'version': '16.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'sale', 'account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/uom_uom_views.xml',
        'views/stock_warehouse_views.xml',
        'views/product_category_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'views/stock_quant_views.xml',
        'views/account_payment_views.xml',
        'views/product_pricelist_views.xml',
        'views/product_product_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
