# -*- coding: utf-8 -*-
{
    'name': "OpenCart ODOO Connector",
    "summary": "Get web-categories from OpenCart",
    'author': "Huryn S.",
    'website': "itspectr.com.ua",
    'category': 'Uncategorized',
    "version": "16.0.1.0.0",
    "license": "OPL-1",
    "depends": ["base", "sale", "account", "sales_team", "mail", "sale_crm", "crm", "purchase", "stock", "sale_stock",
                "delivery", "unicoding_marketplace", "unicoding_integrations_opencart3"],
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_public_category_views.xml',
        'views/unicoding_marketplace.xml',
        'views/isp_integrations_opencart_menu_views.xml',
    ],
}
