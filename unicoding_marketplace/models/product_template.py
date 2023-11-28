from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )
