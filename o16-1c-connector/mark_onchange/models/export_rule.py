# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import logging
from collections import defaultdict

from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class ExportRules(models.Model):
    _name = 'o1c.export.rule'
    _description = 'Export Rules'

    conv_id = fields.Many2one('o1c.conv', ondelete='cascade', required=True)
    name = fields.Char('Rule name')
    order = fields.Integer(index=True)
    disabled = fields.Boolean()
    active = fields.Boolean(
        related='conv_id.active',
        help="When unchecked, the Conversion Rules is hidden and will not be executed.")
    model = fields.Char('Odoo model', index=True, required=True, store=True)
    model_unavailable = fields.Boolean(compute='_compute_model_unavailable', store=True, index=True)
    allow_add_model_action = fields.Boolean(compute='_compute_allow_add_model_action')
    model_export_action_exist = fields.Boolean(compute='_compute_model_export_action_exist')

    @api.depends('model')
    def _compute_model_unavailable(self):
        for exp_rule_id in self:
            if exp_rule_id.model and exp_rule_id.model in self.env:
                exp_rule_id.model_unavailable = False
            else:
                exp_rule_id.model_unavailable = True

    def update_models_available(self):
        self._compute_model_unavailable()

    def _compute_model_export_action_exist(self):
        for exp_rule_id in self:
            exp_rule_id.model_export_action_exist = bool(exp_rule_id.get_model_action())

    def get_model_action(self):
        if not self.model or self.model not in self.env:
            return
        return self.env['ir.actions.server'].sudo().search([
            ('type', '=', 'ir.actions.server'),
            ('code', 'like', '%add_obj_for_export_to_1c(%'),
            ('state', '=', 'code'),
            ('model_id', '=', self.env['ir.model']._get(self.model).id,),
        ])

    @api.depends('model')
    def _compute_allow_add_model_action(self):
        for exp_rule_id in self:
            exp_rule_id.allow_add_model_action = not exp_rule_id.get_model_action()

    def add_model_action(self):
        self.ensure_one()
        o1c_group_ids = self.env.ref('mark_onchange.group_o1c_user') + self.env.ref('mark_onchange.group_o1c_manager')
        # o1c_common_model_id = self.env['ir.model']._get('o1c.export.rule').id
        code_text = "if records:" \
                    "   env['o1c.export.rule'].sudo().add_obj_for_export_to_1c(records, True)"
        for exp_rule_id in self:
            if exp_rule_id.get_model_action():
                continue
            model_id = self.env['ir.model']._get(exp_rule_id.model)
            if not model_id:
                continue
            self.env['ir.actions.server'].sudo().create({
                'name': 'Export to 1C',
                'type': 'ir.actions.server',
                'state': 'code',
                'groups_id': [(4, group) for group in o1c_group_ids.ids],
                # TODO 'some_field': o1c_connector_model_id,
                'model_id': model_id.id,
                'binding_model_id': model_id.id,
                'code': code_text,
                'binding_view_types': 'list,form',
            })
            # TODO add external id: for automatic remove all actions
            #  when module uninstalling
            _logger.info('Create export action: model: %s', exp_rule_id.model)

    def remove_model_action(self):
        for exp_rule_id in self:
            act_id = exp_rule_id.get_model_action()
            if not act_id:
                continue
            _logger.info('Remove export action: model: %s', exp_rule_id.model)
            act_id.unlink()

    def unlink(self):
        self.remove_model_action()
        return super(ExportRules, self).unlink()

    @api.model
    def add_obj_for_export_to_1c(self, rows, check_exist=False):
        """
            Warn: call this func with sudo always!

        :param rows: recordset of objects ONE model type!
        :param check_exist:
        :return:
        """
        model_name = rows._name
        rules_ids = self.search([
            ('model', '=', model_name),
            ('model_unavailable', '=', False),  # Needed ???
            ('disabled', '=', False),
            ('active', '=', True)
        ])
        if not rules_ids:
            return
        conv_ids = rules_ids.mapped('conv_id')
        added = []
        for conv_id in conv_ids:
            if check_exist:
                already_in_export = self.env['changed.record'].search([
                    ('model', '=', model_name),
                    ('res_id', 'in', rows.ids),
                    ('conv_id', '=', conv_id.id),
                ])
                need_to_add = set(rows.ids) - set(already_in_export.mapped('res_id'))
                if not need_to_add:
                    continue
            else:
                need_to_add = rows.ids

            self.env['changed.record'].create([{
                'res_id': row_id,
                'model': model_name,
                'conv_id': conv_id.id
            } for row_id in need_to_add])
            added += need_to_add
        _logger.info(
            "Marked for export to 1c[%s]: %s", model_name, added)

    def _register_hook(self):

        def make_write(export_obj_id):
            """ Instanciate a write method that mark Records for export to 1C. """
            def write(self, vals, **kw):
                rows = write.origin(self, vals, **kw)
                # WARN: don't check 'rows' because sometimes 'write' finished ok, BUT...
                #  BUT it's contain error in 'write process',
                #  and there we get 'rows' = False,
                #  although data was writed in record.
                #  That's why we don't check 'rows', because in this case
                #  record didn't export to 1C.
                if not self.env.context.get('o1c_load'):
                    self.env['o1c.export.rule'].sudo().add_obj_for_export_to_1c(self, check_exist=True)
                return rows
            _logger.info('>>> method WRITE will patch for: %s', export_obj_id.model)
            return write

        def make_create(export_obj_id):
            """ Instanciate a create method that mark Records for export to 1C. """
            @api.model_create_multi
            def create(self, vals, **kw):
                rows = create.origin(self, vals, **kw)
                if not self.env.context.get('o1c_load'):
                    # 'check_exist=True' will become unnecessary
                    # when func 'unlink()' was writed.
                    # Warning: don't remove check_exist=True before it!
                    # Because we get error when object removed and we try to add new one
                    # with the same ID into 'changed.record'. Look 'changed.record' sql constraints.
                    #
                    # WARN: don't use 'self'! Use 'rows'! Because self can be empty, instead rows.
                    self.env['o1c.export.rule'].sudo().\
                        add_obj_for_export_to_1c(rows, check_exist=True)
                return rows
            _logger.info('>>> method CREATE will patch for: %s', export_obj_id.model)
            return create

        def make_unlink(export_obj_id):
            """ Instanciate an unlink method that mark Records for export to 1C. """
            def unlink(self, **kwargs):
                # FIXME TODO >>>> Add records into 'changed.record' marked as removed.
                return unlink.origin(self, **kwargs)
            # _logger.info(' >>> method UNLINK will patch for: %s', export_obj_id.model)
            return unlink

        patched_models = defaultdict(set)

        def patch(model, name, method):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                model._patch_method(name, method)

        # retrieve all actions, and patch their corresponding model
        for export_obj_id in self.with_context({}).search([]):
            Model = self.env.get(export_obj_id.model)

            # Don't crash if the model of the export_obj_id was uninstalled
            if Model is None:
                _logger.warning("Conversion rule with ID %d "
                                "depends on unavailable model %s",
                                export_obj_id.id, export_obj_id.model)
                continue

            patch(Model, 'create', make_create(export_obj_id))
            patch(Model, 'write', make_write(export_obj_id))
            patch(Model, 'unlink', make_unlink(export_obj_id))

    # FIXME TODO add
    # def _unregister_hook(self):
    #     """ Remove the patches installed by _register_hook() """
    #     NAMES = ['create', 'write', '_compute_field_value', 'unlink', '_onchange_methods']
    #     for Model in self.env.registry.values():
    #         for name in NAMES:
    #             try:
    #                 delattr(Model, name)
    #             except AttributeError:
    #                 pass
