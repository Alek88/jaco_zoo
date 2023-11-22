# Copyright © 2019-2022 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.
# flake8: noqa: E501

import os
import re
import logging
from os.path import join as path_join

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import config
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)


class O1CConnector(models.AbstractModel):
    _name = 'o1c.connector'
    _description = '1C connector'

    @staticmethod
    def from_1c_to_odoo_name(o1c_name):
        """ Example: 'СправочникСсылка.productTemplate' -> 'product.template'
            Example 2: 'ПеречислениеСсылка.this_isModelName__FieldName' ->
                model_name: this_is.model.name,
                field_name: field_name

            '.': 'nameName' -> 'name.name'
            '__': 'modelMy_name__Field_name' -> 'model.my_name', 'field_name'
              WARNING: 'F' ------^  must be in UPPER(!) case
              Warning: don't use '__FieldName'. You geted 'fieldName'.
              This form used for field with type 'Selection'
              In 1C it create 'ПеречислениеСсылка.modelName__FieldName'
              with values from selection list
            '_': 'model_name' -> 'model_name' (don't change)

        :param odoo_name:
        :return: (model_name, field_name)
        """
        if not o1c_name:
            return None, None

        # 1. remove 1C type (example: 'СправочникСсылка.')
        odoo_name = re.split(r'(\.)', o1c_name)[-1]

        # 2. get field name if it exist
        field_name = ''
        # TODO get name of parent node and check it: must be 'Свойство'!
        #  'Свойство' = 'Model Field'!
        pp = re.split('(__[QWERTYUIOPASDFGHJKLZXCVBNM])', odoo_name)  # 'fFff__wf__Dff'
        if len(pp) > 1:
            # '__Field_name' -> 'field_name'
            field_name = pp[-2][2:].lower() + pp[-1]
            odoo_name = ''.join(pp[:-2])
        # convert 1C name to Odoo name with dots
        odoo_name = re.sub('[QWERTYUIOPASDFGHJKLZXCVBNM]', lambda m: '.' + m.group(0)[0].lower(), odoo_name)

        return odoo_name, field_name

    @api.model
    def get_default_upload_path(self):
        # Default: home/user-name/.local/share/Odoo/1c_exchange/db-name
        # WARN: o1c will try to create sub-folder 'uploaded' in this folder
        return path_join(config['data_dir'], '1c_exchange', self.env.cr.dbname)

    def get_create_exchange_dirs(self, cron_mode, mode):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        upload_path = get_param('o1c.o1c_upload_path')
        if not upload_path:
            upload_path = self.get_default_upload_path()
        # direction_text = 'from' if mode == 'upload' else 'to'
        # if not upload_path:
        #     if cron_mode:
        #         _logger.error(
        #             "Can't %s data %s 1C. "
        #             "Set/check exchange Path: %s in Settings",
        #             mode, direction_text, upload_path)
        #         return
        #     # TODO make check rights and redirect to settings if user is not a "system"
        #     raise UserError(_("Can't %s data %s 1C. Set exchange Path in Settings") % (mode, direction_text))
        # if not os.path.exists(upload_path):
        #     if cron_mode:
        #         _logger.error(
        #             "Can't store %s ed data. "
        #             "Path is not exist: %s", mode, upload_path)
        #         return
        #     raise UserError(_(
        #         "Can't store %d ed data. "
        #         "Path is not exist: %s") % (mode, upload_path))

        # For example: /opt/odoo/downloads/1c_exchange/from_1c/db_name/uploaded
        splited_path = upload_path.split(os.path.sep)

        # Don't load data in Folder 'uploaded'
        if splited_path[-1] == 'uploaded':
            splited_path = splited_path[:-1]
            upload_path = os.path.join(splited_path)

        # Auto-create dir for direction
        direction_dir = 'from_1c' if mode == 'upload' else 'to_1c'
        if bool(int(get_param('o1c_create_direction_dir', default=1))) \
                and direction_dir not in splited_path:
            # Example: /opt/odoo/downloads/1c_exchange
            upload_path = os.path.join(upload_path, direction_dir)
            splited_path = upload_path.split(os.path.sep)

        # Create folder with DB-name and add them into path
        if bool(int(get_param('o1c_create_dbname_dir', default=1))) \
                and self._cr.dbname not in splited_path:
            # Check if it already exist
            upload_path = os.path.join(upload_path, self._cr.dbname)
            splited_path = upload_path.split(os.path.sep)

        self.create_dir(upload_path, cron_mode, mode)

        # Create folder for uploaded, if not exist
        if mode == 'upload':
            uploaded_dir = os.path.join(upload_path, 'uploaded')
            self.create_dir(uploaded_dir, cron_mode, mode)
            return upload_path, uploaded_dir

        return upload_path

    def get_data(self, conv_id=False):
        self = self.with_context(lang=get_lang(
            self.env, lang_code=self.env.user.lang).code)
        dom = [('active', '=', True)]
        if conv_id:
            dom += [('id', '=', conv_id)]
        conv = self.env['o1c.conv'].search(dom)
        if not conv or len(conv) != 1:
            _logger.error(
                'More then one Conversion!'
                ' Please set Conversion ID in 1C Exchange Plane - Odoo Node.')
            return 'error'
        xml_text, exported = conv.get_xml_text(True)
        _logger.info('Exported to 1C: %s objects', len(exported))
        exported.unlink()  # TODO add load check
        if not xml_text:
            # If len(exported) > 0 then it's not error.
            # Maybe all objects are skipped by rule conditions
            return 'ok'
        xml_header = conv.get_xml_header()

        # FIXME >>> return base64.b64encode(zlib.compress(xml_header + str.encode(xml_text)))
        return xml_header + str.encode(xml_text)

    @staticmethod
    def create_dir(dir, cron_mode, mode):
        if os.path.exists(dir):
            return
        try:
            os.makedirs(dir)
        except Exception as e:
            # TODO make check rights and redirect to settings
            #  if user is not a "system"
            user_message = _(
                "Can't create Dir '%s' in %s. "
                "Error: %s") % (mode, dir, e)
            _logger.error(user_message)
            if not cron_mode:
                raise UserError(user_message)

