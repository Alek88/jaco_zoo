# Copyright © 2020-2022 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import base64
import logging
# TODO bandit [B410:blacklist] Using etree to parse untrusted XML data
#  is known to be vulnerable to XML attacks. Replace etree
#  with the equivalent defusedxml package.
from lxml import etree as ET  # nosec

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

from . import demo_data_set_1


_logger = logging.getLogger(__name__)
CONV_UID = '646150c1-f1ae-4a93-a591-44363dcf76ec'


@tagged('post_install', '-at_install')
class O1CTestExport(TransactionCase):

    def setUp(self):
        super(O1CTestExport, self).setUp()

        self.rules_loaded = False
        self.upload_conv()

    def upload_conv(self):
        filename = get_module_resource('o1c', 'tests', 'demo-rules-v2.0.zip')
        try:
            with open(filename, 'rb') as f:
                zip_data = f.read()
        except Exception as e:
            _logger.error('Error read from file: %s\nError: %s', filename, e)
            return

        LoadWiz = self.env['o1c.load.conv']
        Conversion = self.env['o1c.conv']

        # Search and remove old Conversions
        Conversion.search([
            ('o1c_uuid', '=', CONV_UID)]).unlink()

        # Create new empty Conversion
        self.conv_id = Conversion.create({'name': 'test'})
        load_wiz_id = LoadWiz.create({
            'conv_id': self.conv_id.id,
            'xml_file': base64.b64encode(zip_data),
        })
        load_wiz_id.import_file()

        if self.conv_id.name == 'Odoo --> БухгалтерияПредприятия' and \
                self.conv_id.o1c_uuid == CONV_UID and \
                len(self.conv_id.rule_ids) == 18 and \
                len(self.conv_id.export_rule_ids) == 7:
            self.rules_loaded = True

    def search_rule(self, rule_code):
        if not rule_code:
            return
        rule_id = self.conv_id.rule_ids.filtered(
            lambda r: r.code == rule_code.strip())
        self.assertTrue(rule_id, "Can't find Rule with code '%s'" % rule_code)
        self.assertTrue(
            len(rule_id) == 1,
            "Error! More than one Rule with code '%s'" % rule_code)
        return rule_id

    def add_rules_in_data(self, dirty_dict):
        """
        1. Change '<Recursion on list with id=140185244063240>' with link
        2. fill 'rile_id'

        :param dirty_dict:
        :return:
        """
        if not isinstance(dirty_dict, dict):
            return
        for k, v in dirty_dict.items():
            if k == 'rule_id':
                dirty_dict[k] = self.search_rule(v)
                self.assertTrue(
                    dirty_dict[k],
                    "Can't find Rule with code '%s'."
                    " Tip: %s Data: %s" % (v, k, i))
            elif isinstance(v, (list, set)):
                for i in v:
                    self.add_rules_in_data(i)
            else:
                self.add_rules_in_data(v)

    def get_objs_id_keys(self, dirty_dict, keys_cache):
        if not isinstance(dirty_dict, dict):
            return
        id_key = dirty_dict.get('id-key')
        if id_key:
            attrs = dirty_dict.get('attrs')
            if attrs and isinstance(attrs, list):
                if keys_cache.get(id_key):
                    if keys_cache[id_key] != attrs:
                        _logger.error(
                            'Already exist data for id-key: %s in keys_cache.'
                            '\n\t > Current data:\n%s'
                            '\n\tOther data:\n%s\n',
                            id_key, keys_cache[id_key], attrs)
                    else:
                        _logger.debug(
                            'Already exist data for id-key: %s in keys_cache.'
                            '\n\t > data:\n%s',
                            id_key, keys_cache[id_key])
                keys_cache[id_key] = attrs

        for k, v in dirty_dict.items():
            if isinstance(v, (list, set)):
                for i in v:
                    self.get_objs_id_keys(i, keys_cache)
            else:
                self.get_objs_id_keys(v, keys_cache)

    def scan_recursions_in_data(self, dirty_dict, keys_cache, nodes_to_change):

        if not isinstance(dirty_dict, dict):
            return
        attrs = dirty_dict.get('attrs')
        if attrs and isinstance(attrs, str) \
                and attrs[:27] == '<Recursion on list with id=':
            id_key = dirty_dict['id-key']
            nodes_to_change[dirty_dict['attrs']] = keys_cache[id_key]

        for k, v in dirty_dict.items():
            if isinstance(v, (list, set)):
                for i in v:
                    self.scan_recursions_in_data(i, keys_cache, nodes_to_change)
            else:
                self.scan_recursions_in_data(v, keys_cache, nodes_to_change)

    def restore_recursion_in_data(self, dirty_dict, nodes_to_change):

        if not isinstance(dirty_dict, dict):
            return
        attrs = dirty_dict.get('attrs')
        if attrs and isinstance(attrs, str) \
                and attrs[:27] == '<Recursion on list with id=':
            dirty_dict['attrs'] = nodes_to_change[dirty_dict['attrs']]
            return

        for k, v in dirty_dict.items():
            if isinstance(v, (list, set)):
                for i in v:
                    self.restore_recursion_in_data(i, nodes_to_change)
            else:
                self.restore_recursion_in_data(v, nodes_to_change)

    def test_export_data_in_xml(self):
        """ Testing create xml from prepared data
            and compare this xml with etalon data

            WARNING: it's NOT TESTING algorithm of preparing data!
                It's get already created data from demo_data_set_1.py
                It's NOT TESTING conv.get_xml_text func!

        :return:
        """
        if not self.rules_loaded:
            return
        root = self.conv_id.add_rules_node()
        data = [
            demo_data_set_1.t1,
            demo_data_set_1.t2,
            demo_data_set_1.t3,
            demo_data_set_1.t4,
            demo_data_set_1.t5
        ]
        # Ready for make xml
        obj_cache = {}  # Cache for add Objects in XML
        for dc in data:
            self.add_rules_in_data(dc)

            # *********************************************************************
            # Restore recursion in data:
            #   convert and replace text '<Recursion on list with id=140185244063240>'
            #   into link in massive
            keys_cache = {}
            self.get_objs_id_keys(dc, keys_cache)
            nodes_to_change = {}
            # Search attrs with text '<Recursion on list with id=...'
            self.scan_recursions_in_data(dc, keys_cache, nodes_to_change)
            # Replace text '<Recursion on list with id=140185244063240>' to list
            self.restore_recursion_in_data(dc, nodes_to_change)
            # *********************************************************************

            self.conv_id.exp_add_node_to_xml(root, dc, obj_cache, [])

        xml_text = ET.tostring(root, encoding='unicode', pretty_print=True)
        xml_header = b'\xEF\xBB\xBF<?xml version="1.0" encoding="UTF-8"?>\n'
        # file_name = 'data_for_1c-test.xml'
        # f = open(file_name, "wb+")
        # f.write(xml_header)
        # f.write(str.encode(xml_text))
        # f.close()

        del root
        del dc
        del obj_cache
        del data

        # Compare with etalon xml
        filename = get_module_resource('o1c', 'tests', 'demo_data_set_1_result.xml')
        try:
            f = open(filename, "r")
        except Exception as e:
            _logger.error('Error read from file: %s\nError: %s', filename, e)
            return
        rows_list = (xml_header.decode() + xml_text).split('\n')
        rows_list_len = len(rows_list)
        i = -1
        diffs = []
        max_line = 0
        while True:
            e_row = f.readline()
            if not e_row:
                break
            i += 1
            if i >= rows_list_len:
                max_line = max(max_line, len(e_row[:-1]), 11)
                diffs.append((e_row[:-1], ' * absent *'))
                continue
            # Skip: rows with: DB UID, 'ДатаВремяСоздания' and 'ДатаВыгрузки'
            if i not in [1, 4, 6] and \
                    e_row[:-1] != rows_list[i]:
                max_line = max(max_line, len(e_row[:-1]), len(rows_list[i]))
                diffs.append((e_row[:-1], rows_list[i]))

        max_line = min(max_line, 100)
        r_spaces = ' ' * (max_line+1)
        self.assertTrue(
            len(diffs) == 0,
            'Incorrect export data in xml. \nDifferents with etalon XML:\n'
            '%s | %s\n%s' % (
                (' Etalon data' + r_spaces)[:max_line],
                ('Current data' + r_spaces)[:max_line],
                '\n'.join(['%s | %s' % (
                    (e_r+r_spaces)[:max_line],
                    (c_r+r_spaces)[:max_line]) for e_r, c_r in diffs])))
        _logger.info('Test export data into xml successfully.')
