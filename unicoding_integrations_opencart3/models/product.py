from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = "product.product"

    opencartid = fields.Char('OpenCart ID', related="product_tmpl_id.opencartid")


class ProductCategory(models.Model):
    _inherit = "product.category"


    opencartid = fields.Char('OpenCart ID')
 
