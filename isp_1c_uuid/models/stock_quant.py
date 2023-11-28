from odoo import models, fields


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    uuid_1c = fields.Char(string='1C UUID', index=True)