# Copyright © 2021 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import logging

from odoo import api, SUPERUSER_ID
from odoo.tests.common import SingleTransactionCase
from odoo.tests import tagged


_logger = logging.getLogger(__name__)
CONV_UID = '646150c1-f1ae-4a93-a591-44363dcf76ec'


@tagged('post_install', '-at_install')
class O1CTestPrepareDataForExport(SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super(O1CTestPrepareDataForExport, cls).setUpClass()

        need_mods = cls.env['ir.module.module'].search([
            ('name', 'in', ['sale', 'stock', 'purchase']),  # TODO >>>> add 'account', 'mrp'
            ('state', '=', 'uninstalled'),
        ])
        _logger.info("Modules to install: %s" % [x.name for x in need_mods])
        # ERROR: setUpClass (odoo.addons.o1c.tests.test_prepare_export_data.O1CTestPrepareDataForExport)
        # Traceback (most recent call last):
        #   File "/home/odoo/src/odoo/odoo/tests/common.py", line 191, in _handleClassSetUp
        #     setUpClass()
        #   File "/home/odoo/src/user/o1c/tests/test_prepare_export_data.py", line 28, in setUpClass
        #     need_mods.button_immediate_install()
        #   File "<decorator-gen-61>", line 2, in button_immediate_install
        #   File "/home/odoo/src/odoo/odoo/addons/base/models/ir_module.py", line 73, in check_and_log
        #     return method(self, *args, **kwargs)
        #   File "/home/odoo/src/odoo/odoo/addons/base/models/ir_module.py", line 464, in button_immediate_install
        #     return self._button_immediate_function(type(self).button_install)
        #   File "/home/odoo/src/odoo/odoo/addons/base/models/ir_module.py", line 576, in _button_immediate_function
        #     self._cr.commit()
        #   File "/home/odoo/src/odoo/odoo/sql_db.py", line 172, in wrapper
        #     raise psycopg2.OperationalError(msg)
        # psycopg2.OperationalError: Unable to use a closed cursor.
        need_mods.button_immediate_install()
        # Now that new modules are installed, we have to reset the environment
        api.Environment.reset()
        cls.env = api.Environment(cls.cr, SUPERUSER_ID, {})

    def test_prepare_data_for_export(self):
        """ Test marking records and convert data by Rules

        :return:
        """
        # Update field 'model_unavailable' in Export Rules
        conv_id = self.env['o1c.conv'].search([('o1c_uuid', '=', CONV_UID)])
        conv_id.update_models_available()

        marked_to_export_ids = conv_id.changed_rec_ids.filtered(
            lambda r: r.model == 'sale.order')
        self.assertEqual(len(marked_to_export_ids), 0)

        so_ids = self.env['sale.order'].search([
            ('id', 'in', [1, 2, 3, 4, 5])])
        # Simulate change records
        so_ids.write({})

        marked_to_export_ids = conv_id.changed_rec_ids.filtered(
            lambda r: r.model == 'sale.order')
        self.assertEqual(len(marked_to_export_ids), 5,
                         "SO does not marked for export")

        # TODO rewrite rules from 'account.invoice' into 'account.move'
        # ai_ids = self.env['account.invoice'].search([('id', 'in', [1, 2, 3, 4, 5])])
        # # Simulate change records
        # ai_ids.write({})
        #
        # marked_to_export_ids = conv_id.changed_rec_ids.filtered(
        #     lambda r: r.model == 'account.invoice')
        # self.assertEqual(len(marked_to_export_ids), 5, "Account Invoices does not marked for export")

        ai_ids = self.env['purchase.order'].search([
            ('id', 'in', [1, 2, 3, 4, 5])])
        # Simulate change records
        ai_ids.write({})

        marked_to_export_ids = conv_id.changed_rec_ids.filtered(
            lambda r: r.model == 'purchase.order')
        self.assertEqual(len(marked_to_export_ids), 5,
                         "PO does not marked for export")

        ai_ids = self.env['stock.picking'].search([
            ('id', 'in', [1, 2, 3, 4, 5])])
        # Simulate change records
        ai_ids.write({})

        marked_to_export_ids = conv_id.changed_rec_ids.filtered(
            lambda r: r.model == 'stock.picking')
        self.assertEqual(len(marked_to_export_ids), 5,
                         "stock.picking does not marked for export")
        # __________________________________________________________
        # Fix error: 'key_1c' not in Model product.product
        conv_id.rule_ids.mapped('rule_line_ids').\
            filtered(lambda x: x.source_name == 'key_1c').\
            write({'disabled': True})

        # *********************************************************
        xml_text, exported = conv_id.get_xml_text(cron_mode=True)
        # *********************************************************

        # __________________________________________________________
        # TODO compare xml_text with etalon
        _logger.info('Fin testing convert data')
