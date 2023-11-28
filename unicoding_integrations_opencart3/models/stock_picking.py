# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.



from odoo import SUPERUSER_ID, _, api, fields, models




class Picking(models.Model):
    _inherit = "stock.picking"


    def button_validate(self):
        for picking_id in self:

            result = super().button_validate()
            if picking_id.sale_id.unicoding_marketplace_id and picking_id.sale_id.opencartid and not self.env.context.get('opencart_make_delivery'):
                if picking_id.sale_id.unicoding_marketplace_id.delivery_set_to_done:
                    status_id = self.env['unicoding.opencart.status'].search(
                        [('status', '=', 'SHIPPED'),
                         ('unicoding_marketplace_id.id', '=', picking_id.sale_id.unicoding_marketplace_id.id)],
                        limit=1)
                    if status_id and not self.env.context.get('no_send_status_update', False):
                        self.env['unicoding.marketplace'].browse(picking_id.sale_id.unicoding_marketplace_id.id).opencart_update_order(picking_id.sale_id.opencartid,  {'order_status_id': status_id.opencartid})

        return result

    def action_cancel(self):
        for picking_id in self:
            if picking_id.sale_id.unicoding_marketplace_id and picking_id.sale_id.opencartid and not self.env.context.get('opencart_make_delivery'):
                status_id = self.env['unicoding.opencart.status'].search(
                    [('status', '=', 'WILL_NOT_DELIVER'),
                     ('unicoding_marketplace_id.id', '=', picking_id.sale_id.unicoding_marketplace_id.id)],
                    limit=1)
                if picking_id.sale_id.unicoding_marketplace_id.delivery_set_to_done and status_id and not self.env.context.get('no_send_status_update', False):
                    self.env['unicoding.marketplace'].browse(picking_id.sale_id.unicoding_marketplace_id.id).opencart_update_order(picking_id.sale_id.opencartid, {'order_status_id': status_id.opencartid})
        return super().action_cancel()