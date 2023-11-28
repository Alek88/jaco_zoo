from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    uuid_1c = fields.Char(string='1C UUID', index=True)