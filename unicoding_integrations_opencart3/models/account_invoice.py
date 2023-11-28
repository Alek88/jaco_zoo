# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    opencartid = fields.Char('OpenCart ID')
    def _invoice_paid_hook(self):
        # OVERRIDE
        for invoice_id in self:
            res = super(AccountMove, self)._invoice_paid_hook()

            if invoice_id.reversed_entry_id:
                paymentStatus = 'REFUNDED'
            else:
                paymentStatus = 'PAID'


            status_id = self.env['unicoding.opencart.status'].search(
                [('status', '=', paymentStatus), ('unicoding_marketplace_id.id', '=', invoice_id.unicoding_marketplace_id.id)],
                limit=1)
            if invoice_id.unicoding_marketplace_id and invoice_id.opencartid and status_id and not self.env.context.get('no_send_status_update', False):
                self.env['unicoding.marketplace'].browse(invoice_id.unicoding_marketplace_id.id).opencart_update_order(invoice_id.opencartid, {'order_status_id': status_id.opencartid})

            return res



