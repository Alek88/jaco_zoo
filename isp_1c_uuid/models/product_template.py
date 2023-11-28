from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    uuid_1c = fields.Char(string='1C UUID', index=True)