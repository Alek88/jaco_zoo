# Copyright © 2022-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.
# flake8: noqa: E501

import zlib
import logging

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.modules.module import get_module_resource, get_module_path

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class O1CTestImport(TransactionCase):

    def setUp(self):
        super(O1CTestImport, self).setUp()

        # set_param = self.env['ir.config_parameter'].sudo().set_param
        # set_param('o1c.o1c_create_direction_dir', False)

        # need_mods = cls.env['ir.module.module'].search([
        #     ('name', 'in', ['product', 'sale', 'stock', 'account']),
        #     ('state', '=', 'uninstalled'),
        # ])
        # _logger.info("Modules to install: %s" % [x.name for x in need_mods])
        # # ERROR: setUpClass (odoo.addons.o1c.tests.test_prepare_export_data.O1CTestPrepareDataForExport)
        # # Traceback (most recent call last):
        # #   File "/home/odoo/src/odoo/odoo/tests/common.py", line 191, in _handleClassSetUp
        # #     setUpClass()
        # #   File "/home/odoo/src/user/o1c/tests/test_prepare_export_data.py", line 28, in setUpClass
        # #     need_mods.button_immediate_install()
        # #   File "<decorator-gen-61>", line 2, in button_immediate_install
        # #   File "/home/odoo/src/odoo/odoo/addons/base/models/ir_module.py", line 73, in check_and_log
        # #     return method(self, *args, **kwargs)
        # #   File "/home/odoo/src/odoo/odoo/addons/base/models/ir_module.py", line 464, in button_immediate_install
        # #     return self._button_immediate_function(type(self).button_install)
        # #   File "/home/odoo/src/odoo/odoo/addons/base/models/ir_module.py", line 576, in _button_immediate_function
        # #     self._cr.commit()
        # #   File "/home/odoo/src/odoo/odoo/sql_db.py", line 172, in wrapper
        # #     raise psycopg2.OperationalError(msg)
        # # psycopg2.OperationalError: Unable to use a closed cursor.
        # need_mods.button_immediate_install()
        # # Now that new modules are installed, we have to reset the environment
        # api.Environment.reset()
        # cls.env = api.Environment(cls.cr, SUPERUSER_ID, {})

    def test_01_upload_data_from_1c(self):
        """ Testing read xml and upload data to database
        Compare uploaded data with needed data.

        Tested funcs: load_1c_data, non_recurs_load, object_is_changed,
        load_data_to_db, ...

        WARNING: it's NOT TESTING ??

        """
        # FIXME в xml-ях данные не всегда в порядке стоят! Иногда сначала идут ссылки на Объекты,
        #  а помто сами объекты! Нужно этот кейс добавить в test-data-for-odoo.xml !!!!
        filename = get_module_resource(
            'o1c_import', 'tests', 'test-data-for-odoo.xml')
        try:
            with open(filename, 'rb') as f:
                xml_data = f.read()
        except Exception as e:
            _logger.error('Error read from file: %s\nError: %s', filename, e)
            return
        # TODO remove this code
        xml_str = '*'*14 + xml_data.decode().replace('""', '""""')
        compress = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)
        compress.compress(xml_str.encode())
        xml_zipped = compress.flush()

        http_data = type('HTTP_Class', (object,), {'data': xml_zipped})
        self.env['o1c.import'].with_context(test_mode=True).post_data(http_data)

        # *******************************************
        # Check uploaded data
        partner_id = self.env['res.partner'].sudo().search([('vat', '=', '0123456789')])
        self.assertTrue(partner_id, 'Partner not loaded!')
        self.assertEqual(partner_id.name, 'Modool.pro', 'Partner name not "Modool.pro"!')
        self.assertEqual(partner_id.email, 'info@modool.pro', 'Partner email not "Minfo@modool.pro"!')
        self.assertEqual(
            partner_id.website, 'https://modool.pro', 'Partner website not "https://modool.pro"!')
        uuid_id = self.env['o1c.uuid'].search([
            ('model', '=', 'res.partner'),
            ('res_id', '=', partner_id.id)])
        etalon_uuid = 'f111ce75-394b-11de-9e6e-00804829546f'
        self.assertEqual(uuid_id.o1c_uuid, etalon_uuid, 'Partner UUID not "%s"!' % etalon_uuid)

        product_id = self.env['product.product'].sudo().search([('default_code', '=', '00000037')])
        self.assertTrue(product_id, 'Product not loaded!')
        self.assertEqual(product_id.barcode, '1111111111111', 'Product barcode not loaded!')
        self.assertEqual(product_id.type, 'consu', 'Product type not loaded!')
        self.assertEqual(product_id.name, 'Кресло-качалка', 'Product name not loaded!')
        self.assertEqual(
            product_id.description_sale,
            'test run code after upload - OK',
            'Execute code "ПослеЗагрузки" is not work!')

        uuid_id = self.env['o1c.uuid'].search([
            ('model', '=', 'product.product'),
            ('res_id', '=', product_id.id)])
        etalon_uuid = 'cfc0cf80-06f8-11d9-9a46-000d884f5d77'
        self.assertEqual(uuid_id.o1c_uuid, etalon_uuid, 'Product UUID not "%s"!' % etalon_uuid)
        # TODO upload and check picture

        so_id = self.env['sale.order'].sudo().search([('name', '=', 'ДО000000007')])
        self.assertTrue(so_id, 'Sale Order not loaded!')
        self.assertEqual(
            so_id.date_order, fields.Datetime.from_string('2015-03-15 01:54:05'),
            'Date time of SO not loaded! Must be 2015-03-15 01:54:05')
        self.assertEqual(
            so_id.partner_id, partner_id, 'SO partner not set on incorrect!')

        # Lines
        self.assertTrue(len(so_id.order_line) == 1, 'Sale Order Lines count not one!')
        line_id = so_id.order_line[0]
        self.assertEqual(
            line_id.product_id, product_id,
            'SO line.Product not a "%s"!' % product_id.display_name)
        self.assertEqual(
            line_id.product_uom_qty, 15, 'SO line.product_uom_qty not a 15!')
        self.assertEqual(
            line_id.price_unit, 42.15, 'SO line.product_uom_qty not a 15!')
        # TODO fill and check tax_ids

        uuid_id = self.env['o1c.uuid'].search([
            ('model', '=', 'sale.order'),
            ('res_id', '=', so_id.id)])
        etalon_uuid = 'f111ce78-394b-11de-9e6e-00804829546f'
        self.assertEqual(uuid_id.o1c_uuid, etalon_uuid, 'SO UUID not "%s"!' % etalon_uuid)

        curr_id = self.env.ref('base.AUD')
        self.assertTrue(curr_id.active, 'Currency status active is not loaded!')
        # This is check 'НеЗамещать' Field attribute
        self.assertFalse(
            curr_id.full_name == 'Австралийский Доллар тест',
            'Field attribute НеЗамещать is not work!')

        # Check 'НеЗамещать' Object attribute
        country_id = self.env['res.country'].search([('name', '=', 'Italy')])
        self.assertEqual(
            country_id.phone_code, 39,
            'Object attribute "НеЗамещать" didn\'t work! '
            'Check Country phone_code "%s"!' % country_id.phone_code)

        _logger.info('Test import data from xml successfully.')
