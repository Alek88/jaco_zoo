# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

from odoo import api, models, fields


class ExportRules(models.Model):
    _inherit = 'o1c.export.rule'

    code = fields.Char(index=True, copy=False, required=True, help='1C Rule Код')
    conv_rule_id = fields.Many2one(
        'conv.rule', ondelete='cascade',
        help='Rule for conversion data in Source before export')
    changed_rec_ids = fields.One2many(
        related='conv_id.changed_rec_ids',
        domain="[('model', '=', model)]")

    _sql_constraints = [
        ('code_uniq', 'unique(code, conv_id)', 'The Export Rule Code must be unique in Conversion!'),
    ]

    def fill_model(self, vals):
        if vals.get('model'):
            return
        if not vals.get('conv_rule_id'):
            return
        conv_rule_id = self.env['conv.rule'].sudo().browse(vals['conv_rule_id'])
        if not conv_rule_id or not conv_rule_id.source_name:
            return

        # WARN: using determine odoo 'model' from 'conv_rule_id.source_name' is NOT CORRECT
        # in cases: when we try to export different object as in tracking.
        # For example:
        #   task: export SO into РасходнаяНакладная when SO.stock picking stage change to 'Done'.
        #   solution: export_rule tracking model is 'stock.picking',
        #       BUT! Object to export is 'sale.order'!
        # TODO That's we it needed to:
        #  1. add new field 'Tracking model' and write data to them
        #   on importing Conversion rules xml-file -> ПравилаВыгрузкиДанных -> ОбъектВыборки!!!
        #  2. rewrite this code of determine model from 'Tracking model' field
        #   instead 'conv_rule_id.source_name'
        model_name, f = self.env['o1c.connector'].from_1c_to_odoo_name(conv_rule_id.source_name)
        if model_name not in self.env:
            # this model do not exist in odoo code
            return
        vals['model'] = model_name

    @api.model
    def create(self, vals):
        self.fill_model(vals)
        return super(ExportRules, self).create(vals)

    def write(self, vals):
        self.fill_model(vals)
        return super(ExportRules, self).write(vals)
