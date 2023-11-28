from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    uuid_1c = fields.Char(string='1C UUID', index=True)