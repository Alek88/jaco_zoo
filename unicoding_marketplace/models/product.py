from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = "product.product"

    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )



class ProductCategory(models.Model):
    _inherit = "product.category"


    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )
    
    unicoding_marketplace_updated_date = fields.Datetime(string='Marketplace Update Date', default='2000-01-01')
