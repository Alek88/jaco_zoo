# Copyright © 2019-2021 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import logging

from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class OdooObj(models.Model):
    _name = 'odoo.obj'
    _description = 'Objects'

    name = fields.Char(index=True)
    comment = fields.Char(help="1C Комментарий")
    description = fields.Char(help="1C Синоним")
    del_mark = fields.Boolean('Deletion Mark', index=True)
    f_type = fields.Char('Field type', readonly=True)
    owner_id = fields.Many2one('odoo.obj', 'Class', index=True, ondelete='cascade')
    parent_id = fields.Many2one('odoo.obj', 'Parent', index=True, ondelete='cascade')
    child_ids = fields.One2many('odoo.obj', 'parent_id', 'Childs', index=True, readonly=True)
    odoo_conf_id = fields.Many2one('odoo.conf', 'Configuration', index=True, readonly=True, required=True, ondelete='cascade')
    is_updated = fields.Boolean(index=True, help="models|fields added later. This models needed to recreate conf-file")
    comodel_id = fields.Many2one('odoo.obj', index=True, ondelete='cascade')
    model_name = fields.Char('Ref model', readonly=True, help="Used for Fields with reference types o2m, m2o,...")
    size = fields.Integer(index=True, readonly=True, help="String fields size")
    o1c_uuid = fields.Char('1C UUID', required=True, readonly=True)
    obj_type = fields.Selection([
        ('model', 'Model'),
        ('field', 'Field'),
        ('val', 'Value'),
    ], readonly=True)
    is_folder = fields.Boolean(compute='_compute_is_folder')

    _sql_constraints = [
        ('name_uniq', 'unique(name, parent_id, odoo_conf_id)', 'The Name of the Database Item must be unique per Parent per Configuration!'),
    ]

    def _compute_is_folder(self):
        for obj in self:
            if obj.obj_type == 'model' and obj.parent_id:
                obj.is_folder = True
            else:
                obj.is_folder = False

    @api.model
    def odoo_obj_is_changed(self, update_data):
        # TODO this func is similar as 'object_is_changed' in o1c.connector.
        #  Make one func.
        object_changed = False
        obj_fields = self.sudo()._fields
        for f_name, new_val in update_data.items():
            if f_name == 'is_updated' or f_name not in obj_fields:
                continue
            # fields with link types must compare value with ID\IDS!!!
            field_type = obj_fields[f_name].type
            if field_type == 'many2one':
                field_value = self[f_name].id
            elif field_type in ['many2many', 'one2many']:
                field_value = self[f_name].ids
                # TODO  Update(Add) values or Replace IDS with new value ???
                # FIXME new_val must [4, (id)] or [1, (id)] or...?
                # FIXME And how it compare with ids list? v_for_compare = [i[1] for i on new_val] ..??
                _logger.error('Incorrect comparing odoo object(id %s) field: %s data: %s', self, f_name, new_val)
            else:
                field_value = self[f_name]
                # in empty string fields we get value=False
                if not field_value and isinstance(field_value, bool):
                    new_val = new_val or False  # < from string '' to False
            if new_val != field_value:
                # WARN: None is not equal to False!
                object_changed = True
                _logger.debug(
                    '\t\tWarning: change data in field: %s type: %s model: %s '
                    'name: %s! Old: %s New: %s', f_name, field_type, self._name,
                    self.name, field_value, new_val)
                break
        return object_changed

    def unlink(self):
        child_ids = self.mapped('child_ids')
        if child_ids:
            child_ids.unlink()
        return super(OdooObj, self).unlink()
