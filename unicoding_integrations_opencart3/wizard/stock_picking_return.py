# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        res = super()._create_returns()
        if self.picking_id.sale_id.unicoding_marketplace_id:
            self.env['unicoding.marketplace'].browse(self.picking_id.sale_id.unicoding_marketplace_id.id).update_order(self.picking_id.sale_id.opencartid, {'opencart_fulfillment_status': 'RETURNED'})

        return res