# Copyright © 2021,2022 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.
# flake8: noqa: E501

import base64
import logging
from os.path import join as path_join

from odoo.tests import standalone
from odoo.modules.module import get_module_resource, get_module_path

_logger = logging.getLogger(__name__)
CONV_UID = '646150c1-f1ae-4a93-a591-44363dcf76ec'


@standalone('all_o1c')
def test_prepare_data_for_export(env):
    """ Test marking records and convert data by Rules

    For run use: python /.../odoo/odoo/tests/test_module_operations.py
        --standalone=all_o1c
        --database=o16-o1c-test
        --addons-path=/.../o1c/repo
        --data-dir=/home/.../.local/share/Odoo

    :return:
    """

    need_mods = env['ir.module.module'].search([
        ('name', 'in', ['sale', 'stock', 'purchase', 'account', 'mrp']),
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
    env.reset()     # clear the set of environments
    env = env()     # get an environment that refers to the new registry

    upload_conv(env)

    # Update field 'model_unavailable' in Export Rules
    conv_id = env['o1c.conv'].search([('o1c_uuid', '=', CONV_UID)])
    assert conv_id, 'Conversion not found by UUID'

    conv_id.update_models_available()

    marked_to_export_ids = conv_id.changed_rec_ids.filtered(
        lambda r: r.model == 'sale.order')
    assert len(marked_to_export_ids) == 0, 'SO not exported'

    # TODO create own SO's. Because PEP sed: generate data for your unit-tests!
    #  Don't use DB data! Don't use (even!)demo-data for your unit-tests!
    so_ids = env['sale.order'].search([
        ('id', 'in', [1, 2, 3, 4, 5])])
    assert len(so_ids) > 0, "SO not exist. Please start test with demo-data"
    # Simulate change records
    so_ids.write({})

    marked_to_export_ids = conv_id.changed_rec_ids.filtered(
        lambda r: r.model == 'sale.order')
    assert len(marked_to_export_ids) == 5, "SO does not marked for export"

    # TODO rewrite rules from 'account.invoice' into 'account.move'
    # ai_ids = env['account.invoice'].search([('id', 'in', [1, 2, 3, 4, 5])])
    # # Simulate change records
    # ai_ids.write({})
    #
    # marked_to_export_ids = conv_id.changed_rec_ids.filtered(
    #     lambda r: r.model == 'account.invoice')
    # assert len(marked_to_export_ids) == 5, "Account Invoices does not marked for export"

    ai_ids = env['purchase.order'].search([
        ('id', 'in', [1, 2, 3, 4, 5])])
    # Simulate change records
    ai_ids.write({})

    marked_to_export_ids = conv_id.changed_rec_ids.filtered(
        lambda r: r.model == 'purchase.order')
    assert len(marked_to_export_ids) == 5, "PO does not marked for export"

    ai_ids = env['stock.picking'].search([
        ('id', 'in', [1, 2, 3, 4, 5])])
    # Simulate change records
    ai_ids.write({})

    marked_to_export_ids = conv_id.changed_rec_ids.filtered(
        lambda r: r.model == 'stock.picking')
    assert len(marked_to_export_ids) == 5, "stock.picking does not marked for export"
    # __________________________________________________________
    # Fix error: 'key_1c' not in Model product.product
    conv_id.rule_ids.mapped('rule_line_ids').\
        filtered(lambda x: x.source_name == 'key_1c').\
        write({'disabled': True})

    # *********************************************************
    xml_text, exported = conv_id.get_xml_text(cron_mode=True)
    # *********************************************************

    # # Please allow to write data on disk, before run
    # filename = path_join(
    #     get_module_path('o1c'), 'tests', 'prepared_export_dataset_received.xml')
    # f = open(filename, "w")
    # f.write(xml_text)
    # f.close()

    # __________________________________________________________
    # Compare xml_text with etalon
    filename = get_module_resource('o1c', 'tests', 'prepared_export_dataset_standard.xml')
    try:
        f = open(filename, "r")
    except Exception as e:
        _logger.error('Error read from file: %s\nError: %s', filename, e)
        return
    rows_list = xml_text.split('\n')
    rows_list_len = len(rows_list)
    i = -1
    diffs = []
    max_line = 0
    while True:
        e_row = f.readline()
        # Remove last symbol of '\n' and spaces
        etalon_str = e_row and e_row.strip()
        if not etalon_str:
            break
        i += 1
        curr_str = rows_list[i].strip()
        if i >= rows_list_len:
            max_line = max(max_line, len(etalon_str), 11)
            diffs.append((etalon_str, ' * absent *'))
            continue
        # First 6 rows are skipped: DB UID, 'ДатаВремяСоздания' and 'ДатаВыгрузки'
        # TODO check header
        if i not in [0, 5] and etalon_str != curr_str:
            # *************************************************************
            # Skip UUID's, because UUID's are different in each DB,
            # because UUID's generated when data exported
            if len(curr_str) == 57 and '>{?}</' in etalon_str \
                    and curr_str[:10] == etalon_str[:10] == '<Значение>' \
                    and curr_str[-11:] == etalon_str[-11:] == '</Значение>' \
                    and curr_str[18:19] == '-' \
                    and curr_str[23:24] == '-' \
                    and curr_str[28:29] == '-' \
                    and curr_str[33:34] == '-':
                # TODO check UUID id correct:
                #  get record->o1c.uuid->check with this UUID
                continue
            # *************************************************************

            max_line = max(max_line, len(etalon_str), len(curr_str))
            diffs.append((etalon_str, curr_str))

    max_line = min(max_line, 100)
    r_spaces = ' ' * (max_line + 1)

    max_line = min(max_line, 100)
    r_spaces = ' ' * (max_line + 1)
    assert len(diffs) == 0, \
        'Incorrect export data in xml. \nDifferents with etalon XML:\n' \
        '%s | %s\n%s' % (
            (' Etalon data' + r_spaces)[:max_line],
            ('Current data' + r_spaces)[:max_line],
            '\n'.join(['%s | %s' % (
                (e_r + r_spaces)[:max_line],
                (c_r + r_spaces)[:max_line]) for e_r, c_r in diffs]))

    _logger.info('Fin testing convert data - OK')


def upload_conv(env):
    filename = get_module_resource('o1c', 'tests', 'demo-rules-v2.0.zip')
    try:
        f = open(filename, "rb")
        zip_data = f.read()
    except Exception as e:
        _logger.error('Error read from file: %s\nError: %s', filename, e)
        return

    LoadWiz = env['o1c.load.conv']
    Conversion = env['o1c.conv']

    # Search and remove old Conversions
    Conversion.search([
        ('o1c_uuid', '=', CONV_UID)]).unlink()

    # Create new empty Conversion
    conv_id = Conversion.create({'name': 'test'})
    load_wiz_id = LoadWiz.create({
        'conv_id': conv_id.id,
        'xml_file': base64.b64encode(zip_data),
    })
    load_wiz_id.import_file()

    if conv_id.name == 'Odoo --> БухгалтерияПредприятия' and \
            conv_id.o1c_uuid == CONV_UID and \
            len(conv_id.rule_ids) == 18 and \
            len(conv_id.export_rule_ids) == 7:
        return
    assert False, 'Can\'t upload Conversion'
