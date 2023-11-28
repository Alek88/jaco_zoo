from odoo import api, fields, models

class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )

