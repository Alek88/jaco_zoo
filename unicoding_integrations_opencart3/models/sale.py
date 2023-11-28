from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    opencartid = fields.Char('OpenCart ID')

    unicoding_opencart_status_id = fields.Many2one(
        string='Opencart Order Status',
        comodel_name='unicoding.opencart.status',
        ondelete='restrict',
        copy=False,
    )

    unicoding_opencart_status_id_status = fields.Selection(
        string='Opencart Status',
        related="unicoding_opencart_status_id.status",
        copy=False,
        readonly=True
    )

    def _action_cancel(self):
        for order in self:
            print(order)
            if order.unicoding_marketplace_id and order.opencartid:
                status_id = self.env['unicoding.opencart.status'].search(
                    [('status', '=', 'CANCELLED'),
                     ('unicoding_marketplace_id.id', '=', order.unicoding_marketplace_id.id)],
                    limit=1)
                _logger.info(self.env.context.get('no_send_status_update', False))
                if status_id and not self.env.context.get('no_send_status_update', False):
                    self.env['unicoding.marketplace'].browse(order.unicoding_marketplace_id.id).opencart_update_order(order.opencartid, {'order_status_id': status_id.opencartid})
            return super()._action_cancel()


    def make_delivery(self):
        for order in self:

            if order.unicoding_marketplace_id and order.opencartid:
                if order.unicoding_marketplace_id.delivery_set_to_done and order.picking_ids:
                    for picking in order.picking_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                        picking.action_assign()
                        picking.action_confirm()
                        for mv in picking.move_ids_without_package:
                            mv.quantity_done = mv.product_uom_qty
                        picking.with_context(skip_immediate=True, skip_backorder=True, opencart_make_delivery=True, no_send_status_update=self.env.context.get('no_send_status_update', False)).button_validate()
        return super().make_delivery()
    
    def action_confirm(self):
        for order in self:
            res = super().action_confirm()

            if order.unicoding_marketplace_id and order.opencartid and order.unicoding_marketplace_id.create_invoice:

                if not self.env.context.get('no_send_status_update', False):
                    status_id = self.env['unicoding.opencart.status'].search(
                        [('status', '=', 'PROCESSING'),
                         ('unicoding_marketplace_id.id', '=', order.unicoding_marketplace_id.id)],
                        limit=1)
                    if status_id:
                        print(status_id)
                        print(order.state)
                        self.env['unicoding.marketplace'].browse(order.unicoding_marketplace_id.id).opencart_update_order(order.opencartid, {'order_status_id': status_id.opencartid})


                if order.unicoding_opencart_status_id.id in \
                        self.env['unicoding.opencart.status'].search([('status', 'in', ['SHIPPED', 'DELIVERED', 'COMPLETE']), ('unicoding_marketplace_id.id', '=', order.unicoding_marketplace_id.id)]).ids:
                    order.with_context(no_send_status_update=self.env.context.get('no_send_status_update', False)).make_delivery()

                if not order.invoice_ids:
                    order._create_invoices()

                    for invoice in order.invoice_ids:
                        invoice.write({
                            'opencartid': order.opencartid
                        })

                if order.unicoding_marketplace_id.validate_invoice and order.invoice_ids:
                    for invoice in order.invoice_ids:
                        invoice.action_post()
            return res
    # def write(self, values):
    #     result = super().write(values)
    #
    #     if 'state' in values and values['state'] == 'sale':
    #         for order in self:
    #             if order.unicoding_marketplace_id and order.opencartid and order.unicoding_marketplace_id.create_invoice:
    #                 status_id = self.env['unicoding.opencart.status'].search(
    #                     [('status', '=', 'PROCESSING'),
    #                      ('unicoding_marketplace_id', '=', order.unicoding_marketplace_id.id)],
    #                     limit=1)
    #                 if status_id:
    #                     print("0000000000000000000000000000000")
    #                     print(status_id)
    #                     print(order.state)
    #                     self.env['unicoding.marketplace'].browse(order.unicoding_marketplace_id.id).opencart_update_order(
    #                         order.opencartid, {'order_status_id': status_id.opencartid})
    #
    #     return result