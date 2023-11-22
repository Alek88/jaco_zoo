# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

{
    'name': 'Import from 1C',
    'summary': 'Import data from 1C',
    'author': 'Oleksandr Komarov',
    'maintainer': 'info@modool.pro',
    'website': 'https://modool.pro',
    'license': 'Other proprietary',
    'price': '50',
    'currency': "EUR",
    'category': 'Technical Settings',
    'version': '16.0.1.1.1',
    'depends': [
        'base',  # used for ir.attachments, ir.module.module, ...
        'base_setup',
        # 'mail' used for fix error: psycopg2.errors.NotNullViolation:
        #   null value in column "activity_user_type" violates not-null constraint
        #  field 'activity_user_type' in ir.cron from 'data/ir_cron_data.xml'
        'mail',  # used for fix error only
    ],
    'data': [
        'views/o1c_import_views.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/o1c_uuid_views.xml',
    ],
    'application': True,
    'images': [
        'static/description/cover.gif',
        'static/description/icon.png',
    ],
    "live_test_url": "http://178.63.30.63:43902/web/login",
}
