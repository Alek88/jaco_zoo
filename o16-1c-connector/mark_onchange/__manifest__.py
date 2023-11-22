# Copyright © 2019-2022 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

{
    'name': 'Mark records',
    'summary': 'Mark records on changed, created, deleted',
    'author': 'Oleksandr Komarov',
    'maintainer': 'info@modool.pro',
    'website': 'https://modool.pro',
    'license': 'Other proprietary',
    'price': '30',
    'currency': "EUR",
    'category': 'Technical Settings',
    'version': '16.0.1.0.3',
    'depends': [
        'base',  # used for ir.attachments, ir.module.module, ...
        # 'mail' used for fix error: psycopg2.errors.NotNullViolation:
        #   null value in column "activity_user_type" violates not-null constraint
        #  field 'activity_user_type' in ir.cron from 'data/ir_cron_data.xml'
        'mail',  # used for fix error only
    ],
    'data': [
        'security/o1c_security.xml',
        'security/ir.model.access.csv',
        'views/o1c_views.xml',
        'views/changed_record_views.xml',
        'views/o1c_conv_views.xml',
    ],
    'images': [
        'static/description/cover.gif',
        'static/description/icon.png',
    ],
    "live_test_url": "http://178.63.30.63:43902/web/login",
}
