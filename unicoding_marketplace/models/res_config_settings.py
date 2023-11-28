# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        store=True,
        readonly = False,
        config_parameter = 'unicoding_marketplace_id'
    )

    unicoding_marketplace_type = fields.Selection(string='Connector type', related='unicoding_marketplace_id.type', readonly=False)

    unicoding_marketplace_url = fields.Char(string="API URL", related='unicoding_marketplace_id.url', readonly=False)

    unicoding_marketplace_sync_orders = fields.Boolean(string="Sync Orders",
                                                       related='unicoding_marketplace_id.sync_orders',
                                                       readonly=False)
    unicoding_marketplace_sync_products = fields.Boolean(string="Sync Products",
                                                         related='unicoding_marketplace_id.sync_products',
                                                         readonly=False)
    
    unicoding_marketplace_sync_odoo_products = fields.Boolean(string="Sync Products From Odoo",
                                                         related='unicoding_marketplace_id.sync_odoo_products',
                                                         readonly=False)
    
    

    
    unicoding_marketplace_sync_categories = fields.Boolean(string="Sync Categories",
                                                           related='unicoding_marketplace_id.sync_categories',
                                                           readonly=False)

    unicoding_marketplace_sync_product_images = fields.Boolean(string="Sync Product Images",
                                                               related='unicoding_marketplace_id.sync_product_images',
                                                               readonly=False)

    unicoding_marketplace_team_id = fields.Many2one(string="Sales Team",
                                                    related='unicoding_marketplace_id.team_id',
                                                    readonly=False)

    unicoding_marketplace_service_categ_id = fields.Many2one(string="Service Category",
                                                             related='unicoding_marketplace_id.service_categ_id',
                                                             readonly=False)

    unicoding_marketplace_delivery_categ_id = fields.Many2one(string="Default Delivery Category",
                                                              related='unicoding_marketplace_id.delivery_categ_id',
                                                              readonly=False)

    unicoding_marketplace_location_dest_id = fields.Many2one(string="Destination Location",
                                                             related='unicoding_marketplace_id.location_dest_id',
                                                             readonly=False)

    unicoding_marketplace_allow_update_price_oc = fields.Boolean(string="Update product price",
                                                                 related='unicoding_marketplace_id.allow_update_price_oc',
                                                                 readonly=False)

    unicoding_marketplace_default_pricelist_ids = fields.Many2many('product.pricelist', string = 'Pricelists', related='unicoding_marketplace_id.default_pricelist_ids', readonly=False)

    unicoding_marketplace_currency_id = fields.Many2one(string="Currency",
                                                        related='unicoding_marketplace_id.currency_id',
                                                        readonly=False)

    unicoding_marketplace_delivery_set_to_done = fields.Boolean(string="Auto st to Done delivery",
                                                                related='unicoding_marketplace_id.delivery_set_to_done',
                                                                readonly=False)
    unicoding_marketplace_create_invoice = fields.Boolean(string='Auto create Invoice?',
                                                          related='unicoding_marketplace_id.create_invoice',
                                                          readonly=False)
    unicoding_marketplace_validate_invoice = fields.Boolean(string='Auto validate invoice?',
                                                            related='unicoding_marketplace_id.validate_invoice',
                                                            readonly=False)

    unicoding_marketplace_journal_id = fields.Many2one('account.journal', string='Journal', readonly=False,
                                                       related='unicoding_marketplace_id.journal_id')
    unicoding_marketplace_company_id = fields.Many2one('res.company', string='Company', readonly=False,
                                                       related='unicoding_marketplace_id.company_id')

    unicoding_marketplace_page_products_num = fields.Integer(string="Products Per Page", related='unicoding_marketplace_id.page_products_num', readonly=False)
    unicoding_marketplace_page_orders_num = fields.Integer(string="Orders Per Page", related='unicoding_marketplace_id.page_orders_num', readonly=False)
    unicoding_marketplace_page_customer_num = fields.Integer(string="Customers Per Page", related='unicoding_marketplace_id.page_customer_num', readonly=False)
    

    unicoding_marketplace_category_batch_num =fields.Integer(string="Quantity in the batch", related='unicoding_marketplace_id.category_batch_num', readonly=False)

    unicoding_marketplace_logging = fields.Boolean(string="Logging", default=True,
                                                           related='unicoding_marketplace_id.logging',
                                                           readonly=False)
    
    unicoding_marketplace_sync_stock = fields.Boolean(related='unicoding_marketplace_id.sync_stock',
                                                           readonly=False)
    
    unicoding_marketplace_sync_customers = fields.Boolean(related='unicoding_marketplace_id.sync_customers',
                                                           readonly=False)
    

    unicoding_marketplace_parent_default_categ_id = fields.Many2one(string="Parent Default Category",
                                                              related='unicoding_marketplace_id.parent_default_categ_id',
                                                              readonly=False)

    