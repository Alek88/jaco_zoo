# Copyright © 2019-2022 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    o1c_upload_path = fields.Char(
        'Custom exchange path',
        config_parameter='o1c.o1c_upload_path',
        help="Folder used for upload and export xml-files from|to 1C")
    o1c_default_upload_path = fields.Char(
        'Uploaded data stored in', store=False,
        help="Folder used for upload and export xml-files from|to 1C"
             " used when 'Exchange folder' is not set.")
    o1c_create_direction_dir = fields.Boolean(
        'Create folder with Direction',
        help="Automatic create folder with this 'DB name' in Folder 'Upload path'")
    o1c_create_dbname_dir = fields.Boolean(
        'Create folder with DB-name',
        help="Automatic create folder named 'from_1c' in Folder 'Upload path'")
    o1c_objects_to_commit = fields.Integer(
        'Objects to commit',
        config_parameter='o1c.o1c_objects_to_commit',
        required=True, default=500,
        help="On upload each X objects will make commit")
    # TODO add compute field "result path" which
    #  include settings o1c_create_direction_dir and o1c_create_dbname_dir
    #  and show them in settings

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        # TODO check: path not empty but not exist(not enough rights)
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('o1c_create_direction_dir', 1 if self.o1c_create_direction_dir else 0)
        set_param('o1c_create_dbname_dir', 1 if self.o1c_create_dbname_dir else 0)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            o1c_create_direction_dir=bool(int(get_param('o1c_create_direction_dir', default=1))),
            o1c_create_dbname_dir=bool(int(get_param('o1c_create_dbname_dir', default=1))),
            o1c_default_upload_path=self.env['o1c.connector'].get_default_upload_path()
        )
        return res
