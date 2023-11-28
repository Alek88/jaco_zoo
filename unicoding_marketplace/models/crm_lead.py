from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'


    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )