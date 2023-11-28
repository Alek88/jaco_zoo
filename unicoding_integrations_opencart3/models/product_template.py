from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)
class ProductTemplate(models.Model):
    _inherit = "product.template"

    opencartid = fields.Char('OpenCart ID')

    opencart_url = fields.Char('Opencart URL')

    categ_id_opencartid = fields.Char('OpenCart ID', related="categ_id.opencartid")


    @api.onchange('list_price', 'type', 'name', 'description')
    def onchange_list_price(self):
        for product in self:
            if product.unicoding_marketplace_id and product.opencartid:
                self.env['unicoding.marketplace'].browse(product.unicoding_marketplace_id.id).opencart_update_product(product.opencartid, {
                    'price': product.list_price,
                    'type': product.type,
                    'name': product.name,
                    'description': product.description
                })
              