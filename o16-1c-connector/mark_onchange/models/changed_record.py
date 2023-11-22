# Copyright © 2019-2022 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import logging

from odoo import api, models, fields
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class ChangedRecords(models.Model):
    _name = 'changed.record'
    _description = 'Changed records'
    _rec_name = 'res_choice'

    model = fields.Char('Model', required=True, index=True, readonly=True)
    res_id = fields.Integer('Res ID', required=True, index=True, readonly=True)
    updated = fields.Datetime('Updated', default=lambda self: fields.Datetime.now(), readonly=True)
    conv_id = fields.Many2one('o1c.conv', ondelete='cascade', required=True, index=True, readonly=True)

    def get_models(self):
        return [(this_model, this_model) for this_model in self.env]

    res_choice = fields.Reference(
        get_models, string='Record', compute_sudo=True,
        store=False, ondelete='cascade', readonly=True, compute='_compute_res_choice')

    _sql_constraints = [
        ('rec_uniq', 'unique(conv_id,model,res_id)', 'Object(conv_id,model, id) must be unique!'),
    ]

    # Depends - not needed! Because model and res_id - not editable!
    # But when add new record, user allowed to fill model
    @api.onchange('model', 'res_id')
    def _compute_res_choice(self):
        # # Warning: with search_read because _prefetch_field get other records and then raise AccessError
        # data = self.sudo().with_context(active_test=False).search_read(
        #     [('id', 'in', self.ids)],
        #     ['model', 'res_id', 'res_choice'])
        # cs_data = {rec['id']: [rec['model'], rec['res_id'], rec['res_choice']] for rec in data}
        for rec in self:
            # this_model = cs_data[rec.id][0]
            # this_id = cs_data[rec.id][1]
            this_model = rec.model
            this_id = rec.res_id
            res_choice = False
            if this_model and this_id:
                if self.env.get(this_model) is None:
                    rec.res_choice = False
                    continue
                try:
                    res_choice = self.env[this_model].sudo().browse(this_id)
                    res_choice.check_access_rights('read')
                    res_choice.check_access_rule('read')
                except AccessError:
                    _logger.debug(
                        'Record: %s Access denied to with missing Model: %s or Res ID: %s',
                        rec.id, this_model, this_id)
                    res_choice = False
                except Exception as e:
                    _logger.error(
                        'Record: %s Model: %s Res ID: %s ERROR on get: %s',
                        rec.id, this_model, this_id, e)
                    res_choice = False
            rec.res_choice = res_choice
