from odoo import models, fields


class UomUom(models.Model):
    _inherit = 'uom.uom'
    uuid_1c = fields.Char(string='1C UUID', index=True)