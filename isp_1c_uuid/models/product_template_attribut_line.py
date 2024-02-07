from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'product.template.attribute.line'
    uuid_1c = fields.Char(string='1C UUID', index=True)