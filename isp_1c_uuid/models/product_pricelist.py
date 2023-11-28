from odoo import models, fields


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    uuid_1c = fields.Char(string='1C UUID', index=True)