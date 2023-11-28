# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    unicoding_marketplace_webhookurl_opencart = fields.Char(string="Webhook URL", related='unicoding_marketplace_id.opencart_webhookurl',
                                                   readonly=True)
    unicoding_marketplace_api_username = fields.Char(string="API Name", related='unicoding_marketplace_id.api_username', readonly=False)
    unicoding_marketplace_api_key = fields.Text(string="API Key", related='unicoding_marketplace_id.api_key', readonly=False)

    unicoding_marketplace_pricelist_ids = fields.Many2many('product.pricelist', string = 'Pricelists imported to OC', related='unicoding_marketplace_id.pricelist_ids', readonly=False)