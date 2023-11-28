from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )

    def _create_invoices(self, grouped=False, final=False, date=None):
        for order in self:
            res = super()._create_invoices(grouped=grouped, final=final, date=date)

            for invoice in order.invoice_ids:
                invoice.write({
                    'unicoding_marketplace_id': order.unicoding_marketplace_id.id
                })
            return res

    def make_delivery(self):
        pass