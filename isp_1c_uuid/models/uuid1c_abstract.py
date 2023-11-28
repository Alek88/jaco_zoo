from odoo import models, fields


class ISP1CUUID(models.AbstractModel):
    _name = 'isp.1c.uuid'
    _description = '1C UUID'
    uuid_1c = fields.Char(string='1C UUID', index=True)