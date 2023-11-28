# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
import json



class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def marketplace_update_product(self, product_id, quantity):
        if product_id.product_tmpl_id.unicoding_marketplace_id and product_id.product_tmpl_id.opencartid  \
            and product_id.product_tmpl_id.unicoding_marketplace_id.sync_stock  \
            and product_id.product_tmpl_id.unicoding_marketplace_id.allow_update_price_oc and not self.env.context.get(
                'no_send_status_update', False):
            total_available_quantity = quantity
            
            available_quantity = 0
            for sq in self.env['stock.quant'].search(
                    [('product_id', '=', product_id.id), ('quantity', '>', 0),
                     ('location_id.usage', '=', 'internal')]):
                available_quantity += sq.quantity - sq.reserved_quantity

            self.env['unicoding.marketplace'].browse(
                product_id.product_tmpl_id.unicoding_marketplace_id.id).opencart_update_product(
                product_id.product_tmpl_id.opencartid,
                {'quantity': total_available_quantity,
                 'options': ','.join(
                     product_id.product_template_attribute_value_ids.mapped('attribute_id.name')),
                 'values': ','.join(product_id.product_template_attribute_value_ids.mapped('name')),
                 'option_qty': available_quantity})

    def write(self, vals):
        result = super(StockQuant, self).write(vals)

        if self.product_id.opencartid:
            self.product_id._compute_quantities()
            self.marketplace_update_product(self.product_id, self.product_id.free_qty )
        
        return result

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None):
        res =  super()._update_available_quantity(product_id=product_id, location_id=location_id, quantity=quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id, in_date=in_date)
        
        if location_id.usage in ('internal', 'transit') and product_id.product_tmpl_id.unicoding_marketplace_id.sync_stock and res \
            and location_id.parent_path in  product_id.product_tmpl_id.unicoding_marketplace_id.location_dest_id.parent_path: 
            self.marketplace_update_product(product_id, res[0])
        return res
 
 


   