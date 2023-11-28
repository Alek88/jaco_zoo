# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    unicoding_marketplace_id = fields.Many2one('unicoding.marketplace', 'Unicoding marketplace ID', readonly=True)

    def _group_by_sale(self):
        groupby = super()._group_by_sale()
        groupby += ', s.unicoding_marketplace_id'
        return groupby
    
    
    def _select_additional_fields(self):
        fields = super()._select_additional_fields()
        fields['unicoding_marketplace_id'] = "s.unicoding_marketplace_id"
        return fields