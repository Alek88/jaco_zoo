from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.attribute.value'
    uuid_1c = fields.Char(string='1C UUID', index=True)