from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'
    uuid_1c = fields.Char(string='1C UUID', index=True)