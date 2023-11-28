from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    uuid_1c = fields.Char(string='1C UUID', index=True)