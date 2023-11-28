

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class Unicodingmarketplace(models.Model):
    _name = 'unicoding.marketplace'
    _inherit = ['mail.thread']
    _description = 'Unicoding marketplace'



    image_128 = fields.Image("Logo", max_width=128, max_height=128)

    name = fields.Char(
        string='Name',
        store=True,
        readonly=False
    )

    url = fields.Char(string="API URL")
    

    _token_datetime = fields.Datetime(string="Token Datetime")

    #
    # def get_marketplace_details(self, name='OpenCart3'):
    #     return self.search([('name', '=', name)], limit=1)

    state = fields.Selection([
        ('off', 'Stopped'),
        ('on', 'Running'),
    ], string='Status', index=True, copy=False, default='off', tracking=True)

    type = fields.Selection([
        ('ecwid', 'Ecwid'),
        ('opencart', 'Opencart'),
        ('squarespace', 'Squarespace'),
    ], string='Connector type', index=True, default='ecwid')

    products_ids = fields.One2many('product.template', 'unicoding_marketplace_id', 'Products')
    order_ids = fields.One2many('sale.order', 'unicoding_marketplace_id', 'Sale Orders')
    partner_ids = fields.One2many('res.partner', 'unicoding_marketplace_id', 'Customers')

    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Orders Count', store=True)
    products_count = fields.Integer(compute='_compute_products_count', string='Products Count', store=True)
    customers_count = fields.Integer(compute='_compute_customers_count', string='Customers Count', store=True)


    sync_orders = fields.Boolean('Sync Orders', default=True)
    sync_products = fields.Boolean('Sync Products', default=True)
    sync_categories = fields.Boolean('Sync Categories', default=True)
    

    sync_stock = fields.Boolean('Sync Stock', default=True)

    sync_odoo_products = fields.Boolean('Sync Products From Odoo', default=True)

    logging = fields.Boolean('Logging', default=True)

    last_item_date = fields.Datetime(string='Update Date', default='2000-01-01')

    sync_product_images = fields.Boolean('Sync Product Images', default=True)
    
    sync_customers = fields.Boolean('Sync Customers', default=True)

    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company.id)

    team_id = fields.Many2one('crm.team', 'Sales Team')

    service_categ_id = fields.Many2one(
        'product.category', 'Service Category',
        change_default=True, default="", help="Select Service Category")

    parent_default_categ_id = fields.Many2one(
        'product.category', 'Parent Default Category',
        change_default=True, default="", help="Select Parent Default Category For Pdofucts and Categories")

    delivery_categ_id = fields.Many2one(
        'product.category', 'Default Delivery Category',
        change_default=True, default="", help="Select Delivery Category")

    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        domain="[('usage','=','internal')]",
        help="Location where you want to send the components resulting from the unbuild order.")

    currency_id = fields.Many2one(
        'res.currency', string='Currency')

    pages = fields.Integer(string="Product Pages", default=0)
    order_pages = fields.Integer(string="Order Pages", default=0)
    customers_pages = fields.Integer(string="Customers Pages", default=0)
    page_products_num = fields.Integer(string="Products Per Page", default=50)
    page_orders_num = fields.Integer(string="Orders Per Page", default=100)
    page_customer_num = fields.Integer(string="Customers Per Page", default=50)
    category_batch_num = fields.Integer(string="Quantity in the batch", default=10)

    allow_update_price_oc = fields.Boolean('Update product price in OC', default=True)

    default_pricelist_ids = fields.Many2many(comodel_name = 'product.pricelist', string='Pricelist', relation="default_pricelist_oc", store=True)
    
    delivery_set_to_done = fields.Boolean(string="Auto st to Done delivery", default=True)
    create_invoice = fields.Boolean(string='Auto create Invoice?', default=True)
    validate_invoice = fields.Boolean(string='Auto validate invoice?', default=True)

    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")

    



    @api.depends('order_ids')
    def _compute_sale_order_count(self):
        for object in self:
            object.sale_order_count = len(object.order_ids)

    @api.depends('products_ids')
    def _compute_products_count(self):
        for object in self:
            object.products_count = len(object.products_ids)

    @api.depends('partner_ids')
    def _compute_customers_count(self):
        for object in self:
            object.customers_count = len(object.partner_ids)
    
    def cron_sync_categories(self):
        for object in self.env['unicoding.marketplace'].search([]):
            if object.state == "on":
                if object.sync_categories:
                    object.action_sync_categories()
                    
    
    def cron_sync_customers(self):
        for object in self.env['unicoding.marketplace'].search([]):
            if object.state == "on":
                if object.sync_customers:
                    object.action_sync_customers()

    def cron_sync_products(self):
        for object in self.env['unicoding.marketplace'].search([]):
            if object.state == "on":
                if object.sync_products:
                    object.action_sync_products()

    def cron_sync_odoo_products(self):
        for object in self.env['unicoding.marketplace'].search([]):
            if object.state == "on":
                if object.sync_odoo_products:
                    object.action_sync_odoo_products()

    def cron_sync_orders(self):
        for object in self.env['unicoding.marketplace'].search([]):

            if object.state == "on":
                #now = datetime.datetime.now().timestamp()
                #nextcall_orders = fields.Datetime.context_timestamp(cron, fields.Datetime.from_string(object.nextcall_orders))
                if object.sync_orders:
                    object.action_getorders()


    def action_start(self):
        for object in self:
            object.state  = 'on'

    def action_stop(self):
        for object in self:
            object.state  = 'off'


    def action_sync_categories(self):
        pass
    def action_sync_products(self):
        pass
    def action_sync_odoo_products(self):
        pass
    def action_getorders(self):
        pass
    def action_update_product_prices(self):
        pass
    def action_sync_customers(self):
        pass
        

    # nextcall_orders = fields.Datetime(string='Next Execution Date', default=fields.Datetime.now, help="Next planned execution date for this job.")
    # nextcall_products = fields.Datetime(string='Next Execution Date', default=fields.Datetime.now, help="Next planned execution date for this job.")
    # nextcall_categories = fields.Datetime(string='Next Execution Date', default=fields.Datetime.now, help="Next planned execution date for this job.")

    # interval_number_orders = fields.Integer(default=1, help="Repeat every x.")
    # interval_type_orders = fields.Selection([('minutes', 'Minutes'),
    #                                   ('hours', 'Hours'),
    #                                   ('days', 'Days'),
    #                                   ('weeks', 'Weeks'),
    #                                   ('months', 'Months')], string='Interval Unit', default='months')
    #
    # interval_number_products = fields.Integer(default=1, help="Repeat every x.")
    # interval_type_products = fields.Selection([('minutes', 'Minutes'),
    #                                   ('hours', 'Hours'),
    #                                   ('days', 'Days'),
    #                                   ('weeks', 'Weeks'),
    #                                   ('months', 'Months')], string='Interval Unit', default='months')
    #
    # interval_number_categories = fields.Integer(default=1, help="Repeat every x.")
    # interval_type_categories = fields.Selection([('minutes', 'Minutes'),
    #                                   ('hours', 'Hours'),
    #                                   ('days', 'Days'),
    #                                   ('weeks', 'Weeks'),
    #                                   ('months', 'Months')], string='Interval Unit', default='months')