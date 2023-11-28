{
    "name": "OpenCart Odoo Connector",
    "summary": "Get orders, products, categories from OpenCart",
    "version": "16.0.1.0.0",
    "author": "Unicoding.by",
    "website": "https://unicoding.by",
    "license": "OPL-1",
    'category': 'Connectors',
    "depends": ["base", "sale", "account", "sales_team", "mail", "sale_crm", "crm", "purchase", "stock", "sale_stock", "delivery", "unicoding_marketplace"],
    'data':[
        'data/unicoding_marketplace.xml',
        'views/unicoding_marketplace.xml',
        'views/res_config_settings_views.xml',
        'views/sale_view.xml',
        'views/res_partner_view.xml',
        'views/crm_lead_views.xml',
        'views/product_views.xml',
        'views/unicoding_opencart_status.xml',
        'views/unicoding_marketplace_menu_views.xml',
        'security/ir.model.access.csv',
    ],
    "price": 399.99,
    'currency': 'EUR',
    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
        'static/src/img/opencart.png',
    ],
    'installable': True,
    'application': True,
}
