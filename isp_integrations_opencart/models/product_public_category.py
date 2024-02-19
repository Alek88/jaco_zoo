from odoo import models, fields, api


class IspIntegrationsOpencart(models.Model):
    _inherit = 'product.public.category'

    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )
    opencartid = fields.Char('OpenCart ID')
    opencart_url = fields.Char('Opencart URL')
    is_change = fields.Boolean(compute='_set_is_change', store=True, readonly=False)

    @api.depends('name', 'parent_id', 'unicoding_marketplace_id')
    def _set_is_change(self):
        for rec in self:
            rec.is_change = True
