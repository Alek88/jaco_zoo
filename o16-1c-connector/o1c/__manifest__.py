# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

{
    'name': '1C Connector',
    'summary': 'Integration Odoo with 1C + "Exchange Rules Editor"',
    'author': 'Oleksandr Komarov',
    'maintainer': 'info@modool.pro',
    'website': 'https://modool.pro',
    'license': 'Other proprietary',
    'price': '310',
    'currency': "EUR",
    'category': 'Technical Settings',
    'version': '16.0.1.2.0',
    'external_dependencies': {'python': ['zlib']},
    'depends': [
        'base',  # used for ir.attachments, ir.module.module,...
        # 'mail' used for fix error: psycopg2.errors.NotNullViolation:
        #   null value in column "activity_user_type" violates not-null constraint
        #  field 'activity_user_type' in ir.cron from 'data/ir_cron_data.xml'
        'mail',  # used for fix error only
        'o1c_import',
        'mark_onchange',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/o1c_vid.xml',
        'views/o1c_vid_views.xml',
        'views/odoo_obj.xml',
        'views/odoo_conf.xml',
        'views/res_config_settings_views.xml',
        'views/conv_rules_views.xml',
        'wizard/get_conf_file.xml',
        'wizard/load_conv_file.xml',
        'views/o1c_export_rule_views.xml',
        'views/o1c_conv_views.xml',
        'views/o1c_uuid_views.xml',
    ],
    'application': True,
    'images': [
        'static/description/cover.gif',
        'static/description/icon.png',
    ],
    "live_test_url": "http://178.63.30.63:43902/web/login",
}
