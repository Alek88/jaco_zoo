# Copyright © 2019-2022 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

from odoo import api, models, fields


class Conversions(models.Model):
    _name = 'o1c.conv'
    _description = 'Conversions'

    name = fields.Char()
    export_rule_ids = fields.One2many(
        'o1c.export.rule', 'conv_id', string='Export')
    changed_rec_ids = fields.One2many('changed.record', 'conv_id')
    active = fields.Boolean(
        default=True,
        help="When unchecked, the rules is hidden and will not be executed.")
    changed_rec_count = fields.Integer(
        'Objects', compute="_compute_changed_rec_count")

    @api.depends('changed_rec_ids')
    def _compute_changed_rec_count(self):
        for conv_id in self:
            conv_id.changed_rec_count = len(conv_id.changed_rec_ids)

    def update_models_available(self):
        self.export_rule_ids.update_models_available()
