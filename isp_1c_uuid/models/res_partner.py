from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'
    uuid_1c = fields.Char(string='1C UUID', index=True)