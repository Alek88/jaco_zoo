from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    uuid_1c = fields.Char(string='1C UUID', index=True)