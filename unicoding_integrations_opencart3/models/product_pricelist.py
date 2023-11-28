from odoo import api, fields, models

class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    opencartid = fields.Char('OpenCart ID')


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    opencartid = fields.Char('OpenCart ID', related="product_tmpl_id.opencartid")