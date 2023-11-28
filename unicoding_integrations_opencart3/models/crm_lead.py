from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    opencartid = fields.Char('OpenCart ID')


    def action_set_won(self):
        for crm_lead_id in self:
            res = super().action_set_won()
            if res and crm_lead_id.opencartid and not self.env.context.get('no_send_status_update', False):
                status_id = self.env['unicoding.opencart.status'].search(
                    [('status', '=', 'COMPLETE'),
                     ('unicoding_marketplace_id.id', '=', crm_lead_id.unicoding_marketplace_id.id)],
                    limit=1)
                if status_id:
                    self.env['unicoding.marketplace'].browse(crm_lead_id.unicoding_marketplace_id.id).opencart_update_order(
                        crm_lead_id.opencartid, {'order_status_id': status_id.opencartid})
            return res