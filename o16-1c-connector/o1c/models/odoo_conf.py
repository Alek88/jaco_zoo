# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.
# flake8: noqa: E501

import logging
import base64
import zlib
import requests
import zipfile
from io import BytesIO

from odoo import release
from uuid import uuid4


from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
MASTER_TS = ['Число', 'Строка', 'Дата', 'Булево', 'ХранилищеЗначения', 'УникальныйИдентификатор', 'КонстантыНабор',
             'Справочники', 'Документы', 'Перечисления', 'ПланыСчетов', 'РегистрыСведений', 'РегистрыБухгалтерии',
             'ПланыОбмена', 'ПланыВидовХарактеристик', 'ПланыВидовРасчета', 'РегистрыНакопления', ]


class OdooConf(models.Model):
    _name = 'odoo.conf'
    _description = 'Configuration'

    name = fields.Char(default='Odoo ')
    update_date = fields.Datetime(readonly=True)
    comment = fields.Char()
    obj_ids = fields.One2many('odoo.obj', 'odoo_conf_id', string='Childs')
    attach_ids = fields.One2many('ir.attachment', compute='_compute_attachment_ids', string='1c XML files')
    version = fields.Char()
    o1c_uuid = fields.Char('1C UUID', readonly=True)  # TODO make required=True

    def _compute_attachment_ids(self):
        for conf in self:
            conf.attach_ids = self.env['ir.attachment'].search([
                ('res_id', '=', conf.id),
                ('res_model', '=', 'odoo.conf')]).ids or False

    def convert_to_1c(self):
        self.ensure_one()
        if not self or len(self) > 1:
            raise UserError(_('Configuration is not set.'))
        if not self.o1c_uuid:
            self.write({
                'o1c_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')
            })
        if not self.o1c_uuid:
            raise UserError(_("Can't convert Configuration."))
        data_to_convert = {
            'Конфигурация': {
                'name': self.name,
                'version': self.version,
                'update_date': self.update_date.strftime("%Y-%m-%dT%H:%M:%S"),
                'o1c_uuid': self.o1c_uuid,
                'comment': self.comment
            }
        }
        objs = self.env['odoo.obj'].search([('odoo_conf_id', '=', self.id), ('del_mark', '=', False)])
        new_exist = objs.filtered(lambda obj: obj.is_updated)
        if not new_exist:
            raise UserError(_("Don't exist modified objects."))
            # FIXME TODO question in master...
            # raise UserError(_("Don't exist modified objects. Do you want to continue"))
        del new_exist
        obj_fields = self.env['odoo.obj'].sudo()._fields
        exclude_fields = ['display_name', 'create_uid', 'create_date',
                          'write_uid', 'write_date', '__last_update', 'child_ids',
                          'odoo_conf_id', 'is_updated']
        for obj in objs:
            this_obj = {}
            for f_name in obj_fields:
                if f_name in exclude_fields:
                    continue
                f_val = False
                if f_name == 'parent_id' or f_name == 'owner_id' or f_name == 'comodel_id':
                    if obj[f_name]:
                        f_val = obj[f_name].id
                else:
                    f_val = obj[f_name]
                if f_val:
                    this_obj[f_name] = str(f_val)
            data_to_convert[obj.id] = this_obj
        # ? zlib.compress(dump(encode( dict_data )))) ?
        # odoo_conf_text = json.dumps(data_to_convert, indent=2, ensure_ascii=False).encode('utf-8')

        try:
            response = requests.get(
                'https://modool.pro/o1c/odoo-config',
                json=data_to_convert,
                headers={
                    'Content-type': 'application/json',
                    'Accept': 'text/plain'
                })
            # timeout=(3, 300))  # 3sec-read, 5min-wait answer
            del data_to_convert
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise UserError(_("Connection error: %s") % e.response.content)
        except requests.exceptions.ConnectionError as e:
            raise UserError(_("Connection error: %s") % e)
        except Exception as e:
            raise UserError(_("Request error: %s") % e)

        try:
            # try json str to dict
            json_data = response.json()
        except Exception as e:
            raise UserError(_("Parse response. Error: %s") % e)
        if not json_data:
            raise UserError(_("Empty response: %s") % response.text)
        if 'result' not in json_data.keys() or not json_data['result'].get('odoo_conf_1c_xml'):
            if 'error' in json_data.keys():
                raise UserError(_("Server error: %s") % json_data['error'])
            raise UserError(_("Incorrect response: %s") % response.text)
        del response
        result = json_data['result']

        self.obj_ids.search([('is_updated', '=', True)]).write({'is_updated': False})
        file_name = 'odoo-conf(%s)' % fields.Datetime.now()

        self.env['ir.attachment'].create({
            'datas': result['odoo_conf_1c_xml'],
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
            'name': file_name+'.zip',
            'store_fname': file_name+'.zip',
            'description': result.get('Errors', '')
        })

        return  # FIXME "base64.b64encode(xml_data)" generate error: Failed on request of size ...
        # TODO return ir.attachment
        save_conf = self.env['o1c.save.conf'].create({
            'file_name': file_name,
            'xml_file': base64.b64encode(xml_data),
            'description': result.get('Errors', '?'),
        })

        return {
            'name': _('Save Configuration'),
            'res_id': save_conf.id,
            'res_model': 'o1c.save.conf',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('o1c.save_conf_master_view_xml_done').id, 'form')],
        }

    def fill_conf(self):
        self.ensure_one()

        def not_process_model(this_md):
            if this_md._transient or this_md._abstract:
                return 'Skip: Transient or Abstract: %s'
            if not this_md._setup_done:
                return 'Skip: did not setup done: %s'
            # TODO _register is always False in 15.0
            # if not this_md._register:
            #     return 'Skip: did not Register: %s'
            if str(this_md)[:3] == 'ir.':
                return 'Skip base model: %s'
            return False

        def get_field_data(this_f, f_name, f_type, obj_id):
            f_comment = this_f.help or ''
            if this_f.required:
                f_comment = '(REQUIRED) ' + f_comment
            if this_f.compute:
                if this_f.required and this_f.inherited:
                    # _logger.debug('Add inherited and required field: %s in model: %s\n\t base_field: %s\n\t depends: %s'
                    #       '\n\t inherited_field: %s\n\t related: %s\n\t related_field: %s' % (f_name, md, this_f.base_field, this_f.depends,
                    #       this_f.inherited_field, this_f.related, this_f.related_field))
                    f_comment = '[Inherited %s] %s' % (
                        this_f.inherited_field if 'inherited_field' in dir(this_f) else this_f.base_field,  # this_f.related_field
                        f_comment)
                else:
                    f_comment = '[COMPUTED] ' + f_comment
            # _logger.debug('\t\t* models: %s \tfield(%s): %s', this_md, f_type, this_f)
            obj_data = {
                'odoo_conf_id': self.id,
                'name': f_name,
                'parent_id': obj_id.id,
                'f_type': f_type,
                'comment': f_comment,
                'description': this_f.string,
                'del_mark': False,
                'is_updated': True,
                'obj_type': 'field',
            }
            # add extra field options
            if f_type in ['char', 'text', 'html']:
                if f_type == 'char' and this_f.size:
                    obj_data['size'] = this_f.size
            elif f_type in ['one2many', 'many2many', 'many2one']:
                comodel_name_id = OdooObj.search([('odoo_conf_id', '=', self.id),
                                                  ('name', '=', this_f.comodel_name), ('parent_id', '=', False), ('obj_type', '=', 'model')])
                if not comodel_name_id:
                    _logger.error('Cant find Model name: %s f_type: %s self: %s field: %s', this_f.comodel_name, f_type, self, this_f)
                    return
                obj_data['comodel_id'] = comodel_name_id.id
            elif f_type == 'reference':
                # FIXME TODO check: is it work?
                obj_data['model_name'] = this_f.model_name
            return obj_data

        # force = False  # FIXME TODO make button 'Force Update' !!!
        OdooObj = self.env['odoo.obj']
        used_obj = []
        statis = {
            'models add': 0,
            'models updated': 0,
            'fields add': 0,
            'fields updated': 0,
        }

        # Create 1C parent classes item
        owner_id = 0
        for item_name in MASTER_TS:
            obj_data = {
                'odoo_conf_id': self.id,
                'name': item_name,
                'comment': item_name,
                'description': item_name,
                'del_mark': False,
                'is_updated': True,
                'obj_type': 'model',
            }
            obj_id = OdooObj.search([('odoo_conf_id', '=', self.id), ('name', '=', item_name), ('parent_id', '=', False), ('obj_type', '=', 'model')])
            if obj_id:
                if obj_id.odoo_obj_is_changed(obj_data):
                    _logger.debug('Update model: %s', item_name)
                    obj_id.write(obj_data)
            else:
                obj_data['o1c_uuid'] = str(uuid4())
                _logger.debug('New model: %s', item_name)
                obj_id = OdooObj.create(obj_data)
            used_obj.append(obj_id.id)
            if item_name == 'Справочники':
                owner_id = obj_id.id

        _logger.info('Models count: %s', len(self.env))
        # Create odoo models
        for md in self.env:
            this_md = self.env[md].sudo()
            text_skip = not_process_model(this_md)
            if text_skip:
                _logger.info(text_skip, md)
                # _logger.debug(text_skip, md)
                continue
            # _logger.debug('model: %s\n\t\tmodule: %s\n\t\ttable: %s', md, this_md._module, this_md._table)
            comment = '[%s%s] %s' % (
                this_md._original_module,
                '-'+this_md._module if this_md._original_module != this_md._module else '',
                this_md._description or '')
            obj_data = {
                'odoo_conf_id': self.id,
                'name': md,
                'comment': comment,
                'description': this_md._description,
                'del_mark': False,
                'is_updated': True,
                'obj_type': 'model',
            }
            obj_id = OdooObj.search([('odoo_conf_id', '=', self.id), ('name', '=', md), ('obj_type', '=', 'model')])
            if obj_id:
                if obj_id.odoo_obj_is_changed(obj_data):
                    _logger.debug('Update model: %s', md)
                    obj_id.write(obj_data)
                    statis['models updated'] += statis['models updated']
            else:
                obj_data['o1c_uuid'] = str(uuid4())
                obj_data['owner_id'] = owner_id
                _logger.debug('New model: %s', md)
                obj_id = OdooObj.create(obj_data)
                statis['models add'] += statis['models add']
            used_obj.append(obj_id.id)

        # Create Model Fields
        for md in self.env:
            this_md = self.env[md].sudo()
            text_skip = not_process_model(this_md)
            if text_skip:
                # _logger.debug(text_skip, md)
                continue
            obj_id = OdooObj.search([('odoo_conf_id', '=', self.id), ('name', '=', md), ('obj_type', '=', 'model')])
            # _logger.debug('model fields: %s', md)

            for f_name in this_md._fields:
                this_f = this_md._fields[f_name]
                f_type = this_f.type

                obj_data = get_field_data(this_f, f_name, f_type, obj_id)
                if not obj_data:
                    _logger.error('Field: %s skipped! Model: %s f_type: %s', f_name, this_md, f_type)
                    continue

                field_id = OdooObj.search([('odoo_conf_id', '=', self.id), ('parent_id', '=', obj_id.id), ('name', '=', f_name), ('obj_type', '=', 'field')])
                if field_id:
                    if field_id.odoo_obj_is_changed(obj_data):
                        _logger.debug('Update model field: %s', f_name)
                        field_id.write(obj_data)
                        statis['fields updated'] += statis['fields updated']
                else:
                    obj_data['o1c_uuid'] = str(uuid4())
                    _logger.debug('New model field: %s', f_name)
                    field_id = OdooObj.create(obj_data)
                    statis['fields add'] += statis['fields add']
                used_obj.append(field_id.id)

                # add selection items
                if f_type == 'selection':
                    # field_type Selection -> add Перечисление and link with his Ref
                    if '__' in md or '__' in f_name:
                        # TODO me! Example 2'__' -> 3'___'
                        raise UserError(_('Incorrect Selection name: %s with "__". Model: %s') % (md, f_name))
                    this_selection = this_f._description_selection(this_md.env)
                    for selection_f_key, selection_f_name in this_selection:
                        obj_data = {
                            'name': str(selection_f_key),
                            'description': selection_f_name,
                            'parent_id': field_id.id,
                            'odoo_conf_id': self.id,
                            'obj_type': 'val',
                        }
                        sel_id = OdooObj.search([('odoo_conf_id', '=', self.id), ('parent_id', '=', field_id.id), ('name', '=', selection_f_key), ('obj_type', '=', 'val')])
                        if sel_id:
                            if sel_id.odoo_obj_is_changed(obj_data):
                                _logger.debug('Update model field selection: %s', selection_f_key)
                                sel_id.write(obj_data)
                                statis['fields updated'] += statis['fields updated']
                        else:
                            obj_data['o1c_uuid'] = str(uuid4())
                            _logger.debug('New model field selection: %s', selection_f_key)
                            sel_id = OdooObj.create(obj_data)
                            statis['fields add'] += statis['fields add']
                        used_obj.append(sel_id.id)

        # removed models and fields mark as deleted
        OdooObj.search([('id', 'not in', used_obj)]).write({'del_mark': True})

        # TODO create Model Values from /data/*.xml
        # TODO export 'ir.config_parameter' to 'Константы'. Выборочно!

        # Fill \ update Configuration data
        conf_data = {}
        if not self.version:
            conf_data['version'] = release.version
        if not self.o1c_uuid:
            conf_data['o1c_uuid'] = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if statis['models add'] > 0 or statis['models updated'] > 0 \
                or statis['fields add'] > 0 or statis['fields updated'] > 0:
            conf_data['update_date'] = fields.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conf_data['comment'] = 'Odoo %s (conf. get: %s)' % (release.version, fields.Datetime.now())
        else:
            if not self.update_date:
                conf_data['update_date'] = fields.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not self.comment:
                conf_data['comment'] = 'Odoo %s (conf. get: %s)' % (release.version, fields.Datetime.now())

        if conf_data:
            self.write(conf_data)

        message = _('Statistic:\n'
                    'Models added: %(models add)s\n'
                    'Models updated: %(models updated)s\n'
                    'Fields added: %(fields add)s\n'
                    'Fields updated: %(fields updated)s\n') % statis
        _logger.debug('Update conf %s', message)
        # FIXME message don't worked :'-(
        return {'warning': {
            'title': _('Warning!'),
            'message': message,
        }}
