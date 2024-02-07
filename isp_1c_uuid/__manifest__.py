# -*- coding: utf-8 -*-
{
    'name': "Odoo UUID 1C",

    'summary': """
        Add UUID to models:
        - account.payment
        - product.category
        - product.pricelist
        - product.product
        - product.template
        - res.partner
        - sale.order
        - stock.picking
        - stock.quant
        - stock.warehouse
        - uom.uom
        """,

    'description': """
        Add UUID to some models
    """,

    'author': "Oleksandr Huryn",
    'website': "itspectr.com.ua",

    'category': 'Uncategorized',
    'version': '16.0.0.0.1',

    'depends': ['base', 'stock', 'sale', 'account'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/uom_uom_views.xml',
        'views/stock_warehouse_views.xml',
        'views/product_category_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        #'views/stock_quant_views.xml',
        'views/account_payment_views.xml',
        'views/product_pricelist_views.xml',
        'views/product_product_views.xml',
    ],
    'images': ['static/description/baner.jpg', 'static/description/icon.jpg']
}
