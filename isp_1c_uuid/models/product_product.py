from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'
    uuid_1c = fields.Char(string='1C UUID', index=True)