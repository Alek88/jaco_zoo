
{
    "name": "Connector with Marketplaces",
    "summary": "Connector with Ecwid, Opencart and etc",
    "version": "16.0.2.0.0",
    "author": "Unicoding.by",
    "website": "https://unicoding.by",
    "license": "OPL-1",
    'category': 'Connectors',
    "depends": ["base", "sale", "account", "sales_team", "mail", "sale_crm", "crm", "purchase", "stock", "sale_stock", "delivery"],
    'data':[
            'data/sync_cron.xml',
            'views/unicoding_marketplace.xml',
            'views/unicoding_marketplace_menu_views.xml',
            'views/res_config_settings_views.xml',
            'views/crm_lead_views.xml',
            'views/product_views.xml',
            'views/res_partner_view.xml',
            'views/sale_view.xml',
            'security/ir.model.access.csv',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    "installable": True,
    'application': True
}
