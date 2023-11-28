

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class UnicodingOpencartStatus(models.Model):
    _name = 'unicoding.opencart.status'
    _description = 'Opencart statuses'

    opencartid = fields.Char('OpenCart ID')
    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )

    name = fields.Char(
        string='Name',
        store=True,
        readonly=False,
        translate = True,
    )


    status = fields.Selection([
        ('AWAITING_PROCESSING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('PAID', 'Paid'),
        ('SHIPPED', 'Shipped'),
        ('CANCELLED', 'Cancelled'),
        ('DELIVERED', 'Delivered'),
        ('RETURNED', 'Returned'),
        ('REFUNDED', 'Refunded'),
        ('COMPLETE', 'Complete'),
    ], string='Statuses', index=True, help="""Pending - When an order is made its status might be pending. In Odoo Sale order will not be confirmed!\n
Processing - Once the payment has been confirmed the status might be set to processing. Sale order is confirmed, but not paid. Invoice and delivery will be created. But delivery is not confirmed and Invoice is not paid.\n
Paid - When you will get confirmation from payment that order is paid, system order status will be change in opencart on "Paid" and in Odoo invoice will be in status Paid\n
Shipped - When you send order to customer you will change status in Opencart to Shipped, that means in Odoo that Delivery order will be confirm!\n
Cancelled - If you change in opencart status order to cancel that means that SO in Odoo will be canceled.\n
Delivered - When your customer will receive the goods to customer door or the goods will be delivered to the point of issue of the goods. In odoo Delviery order will be change to "Done"\n
Returned - Thats means that customer is returned order, you must change status to Returened. In odoo delviery order will be returned. \n
Refunded - When you give back order  from client and everything is ok with goods, after you must return money to customer, order must be set to Refunded. In odoo thats mean Invoice Order status will be change to Refunded and system """)


