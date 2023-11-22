# Copyright © 2019-2021 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import base64
import zipfile
import io
import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LoadConvToFile(models.TransientModel):
    _name = 'o1c.load.conv'
    _description = 'Load Configuration'

    file_name = fields.Char()
    xml_file = fields.Binary('Conversion as XML', required=True)
    conv_id = fields.Many2one('o1c.conv', required=False, string='Conversion')

    def import_file(self):
        self.ensure_one()
        if not self.conv_id:
            raise UserError(_('Coversion id is empty.'))
        xml_text = base64.b64decode(self.xml_file)

        f = io.BytesIO(xml_text)
        if zipfile.is_zipfile(f):
            zf = zipfile.ZipFile(f)
            filename_in_zip = zf.filelist[0]
            xml_text = zf.read(filename_in_zip)

        self.conv_id.upload_f(xml_text, self.file_name)

        # TODO return Ok
        # action = self.env.ref('account.action_bank_reconcile_bank_statements')
        # return {
        #     'name': action.name,
        #     'tag': action.tag,
        #     'context': {
        #         'statement_ids': statement_ids,
        #         'notifications': notifications
        #     },
        #     'type': 'ir.actions.client',
        # }
