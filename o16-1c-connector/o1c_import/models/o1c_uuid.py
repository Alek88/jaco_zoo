# Copyright © 2019-2021 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import logging
from uuid import uuid4

from odoo import api, models, fields, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class O1C_UUID(models.Model):
    _name = 'o1c.uuid'
    _description = '1C Object UUID'
    _rec_name = 'res_choice'

    o1c_uuid = fields.Char('1C UUID', index=True, required=True)
    model = fields.Char('Model', required=True, index=True)
    res_id = fields.Integer('Res ID', required=True, index=True)
    create_in_odoo = fields.Boolean('Create in Odoo', index=True)
    # TODO add field 'conv_1c'.
    #  Then add this field into sql_constraints
    #  Then customize get_create_obj_uuid, update_UUID,...
    # TODO add field 'db_1c'.
    #  Then add this field into sql_constraint model_res_id_uniq
    #  Then customize get_create_obj_uuid, update_UUID,...

    def get_models(self):
        return [(this_model, this_model) for this_model in self.env]

    res_choice = fields.Reference(
        get_models, string='Record', compute_sudo=True,
        store=False, ondelete='cascade', readonly=False, compute='_compute_res_choice')

    _sql_constraints = [
        ('o1c_uuid_uniq', 'unique(o1c_uuid, model, res_id)', 'The 1c UUID must be unique per Record!'),
        ('model_res_id_uniq', 'unique(model, res_id)', 'Reference must be unique per Model, ID!'),
    ]

    @api.onchange('res_choice')
    def onchange_res_choice(self):
        self.model = self.res_choice and self.res_choice._name or ''
        self.res_id = self.res_choice and self.res_choice.id or 0

    def _compute_res_choice(self):
        # Warning: with search_read because _prefetch_field get other records and then raise AccessError
        data = self.sudo().search_read([('id', 'in', self.ids)], ['model', 'res_id', 'res_choice'])
        cs_data = {rec['id']: [rec['model'], rec['res_id'], rec['res_choice']] for rec in data}
        for rec in self:
            this_model = cs_data[rec.id][0]
            this_id = cs_data[rec.id][1]
            res_choice = False
            if this_model and this_id:
                try:
                    res_choice = self.env[this_model].sudo().browse(this_id)
                    res_choice.check_access_rights('read')
                    res_choice.check_access_rule('read')
                except AccessError:
                    _logger.debug('Record: %s Access denied to with missing Model: %s or Res ID: %s', rec.id, this_model, this_id)
                    res_choice = False
                except:
                    _logger.error('Record: %s with missing Model: %s or Res ID: %s', rec.id, this_model, this_id)
                    res_choice = False
            rec.res_choice = res_choice

    @api.model
    def update_UUID(self, this_obj_uuid, this_obj, model_name, uuid, xml_line, force_upload):
        """ Before use this func:
                search UUID by UUID like this:
                    this_uuid = self.env['o1c.uuid'].search([('o1c_uuid', '=', uuid)], limit=1)
                and then run:
                    update_UUID(this_uuid, this_obj, model_name, uuid, xml_line)

        :param this_obj_uuid: UUID record, which find by 'uuid'
            note: this_obj_uuid.o1c_uuid is always == uuid
            note: this_obj_uuid can be empty! AND in the same time uuid can be not empty
            WARN: before run this function - search this_obj_uuid by uuid!
        :param this_obj: Odoo record, which find
        :param model_name: record model name
        :param uuid: UUID of record
        :param xml_line:
        :return:
        """
        if not this_obj:
            # Example: don't Create nad don't update
            #  and can't find existed in odoo
            _logger.info('[%s] Object did not find and not loaded.', xml_line)
            # TODO: remote this_obj_uuid.unlink() if is_exist
            return
        if not uuid:
            return
        if not model_name:
            model_name = this_obj._name
        elif this_obj._name != model_name:
            raise UserError(
                _('[%s] this_obj._name(%s) != model_name(%s)') % (
                    xml_line, this_obj._name, model_name))

        # 1. search record by 'model' and 'res_id'
        exist_uuid = self.search([
            ('model', '=', model_name),
            ('res_id', '=', this_obj.id),
        ], limit=1)
        # 1.2. update UUID
        if exist_uuid:
            if this_obj_uuid and exist_uuid != this_obj_uuid:
                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # We have two UUID records with different uuids.
                # * this_obj_uuid.uuids != exist_uuid.uuid
                # * 'this_obj_uuid' is bind with record,
                #    which searched by UUID
                #    which have other model\res_id
                # * 'exist_uuid' is bind with other record,
                #    which have other uuid
                #
                # Example 1:
                #   export Odoo->1C: product.product -> Номенклатура
                #     in Odoo for product.product stored UUID 1!
                #     in 1C created new 'Номенклатура' with UUID 1!
                #   export 1C->Odoo: the same Номенклатура -> product.TEMPLATE
                #     from 1C we got 'Номенклатура' with UUID 1!
                #     in Odoo we find UUID 1.
                #       BUT UUID.MODEL IS product.PRODUCT! <<--==
                # Example 2:
                #   1. upload Obj1 with UUID. Search by fields.
                #   2. user change data in search fields
                #   3. upload Obj1, search by fields - find Obj2!
                #       with other UUID.
                # Example 3:
                #   In ConversionRule change model1 into model2
                # Example 4:
                #   In ConversionRules we have two Rules with different models
                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # Remove UUID, which bind with other Record
                if this_obj_uuid.exists():
                    _logger.warning(
                        '[%s] Different UUIDs! UUID will be re-bind to current Object.\n'
                        ' UUID this      : %s\n'
                        ' UUID model [%s]: %s model %s id: %s\n'
                        ' UUID object[%s]: %s model %s id: %s  <<-- will REMOVED!',
                        xml_line, uuid,
                        exist_uuid.id, exist_uuid.o1c_uuid, exist_uuid.model, exist_uuid.res_id,
                        this_obj_uuid.id, this_obj_uuid.o1c_uuid, this_obj_uuid.model, this_obj_uuid.res_id)
                    this_obj_uuid.unlink()
            if exist_uuid.o1c_uuid != uuid:
                _logger.warning(
                    '[%s] Change UUID: exist_uuid[%s]! UUID: %s -> %s',
                    xml_line, exist_uuid, exist_uuid.o1c_uuid, uuid)
                exist_uuid.write({'o1c_uuid': uuid})
            return

        # this_obj_uuid already contain record with this UUID
        if this_obj_uuid:
            if this_obj_uuid.o1c_uuid != uuid:
                raise UserError(_(
                    '[%s] uuid(%s) != link_to_obj.o1c_uuid(%s). '
                    'Incorrect using function: update_UUID.'
                ) % (xml_line, uuid, this_obj_uuid.o1c_uuid))
            # Update 'model' and 'res_id'
            update_model_or_id = False
            if this_obj_uuid.model != model_name:
                # it can happened
                # after change 'Destination model' in 1C: Conversation
                _logger.debug(
                    '[%s] Model CHANGED for UUID: %s! '
                    'Old Model: %s new Model: %s res_id: %s',
                    xml_line, this_obj_uuid.o1c_uuid, this_obj_uuid.model,
                    model_name, this_obj.id)
                update_model_or_id = True
            if this_obj_uuid.res_id != this_obj.id:
                # it can happened
                # when Object was removed and created again in Odoo
                _logger.debug(
                    '[%s] Res_ID CHANGED for UUID: %s! '
                    'Old ID: %s new ID: %s Model: %s',
                    xml_line, this_obj_uuid.o1c_uuid, this_obj_uuid.res_id,
                    this_obj.id, model_name)
                update_model_or_id = True
            if update_model_or_id:
                # update model and res_id
                this_obj_uuid.write({
                    'model': model_name,
                    'res_id': this_obj.id,
                })
        else:
            # ================================================================
            # This search is not necessary if this function
            # always run after get_obj_by_uuid
            # this_obj_uuid = self.search([('o1c_uuid', '=', uuid)], limit=1)
            # ================================================================

            # 3. create new record
            this_obj_uuid = self.create({
                'o1c_uuid': uuid,
                'model': model_name,
                'res_id': this_obj.id,
                'create_in_odoo': True,
            })
            _logger.debug('[%s] Add 1C UUID[%s]: %s model: %s id: %s',
                          xml_line, this_obj_uuid.id, uuid, model_name,
                          this_obj.id)
        # Control checks:
        # if this_obj_uuid:
        #     if this_obj._name != this_obj_uuid.model:
        #         raise UserError(_('[%s] this_obj._name(%s) != link_to_obj.model(%s)') % (xml_line, this_obj._name, this_obj_uuid.model))
        #     if this_obj.id != this_obj_uuid.res_id:
        #         raise UserError(_('[%s] this_obj.id(%s) != link_to_obj.res_id(%s)') % (xml_line, this_obj.id, this_obj_uuid.res_id))

    def get_create_obj_uuid(self, obj, model_name):
        if not obj:
            return
        if model_name == 'PROGRAMMATICALLY.GENERATED.OBJECT':
            return
        uuid_id = self.search([
            ('model', '=', model_name),
            ('res_id', '=', obj.id)])
        if not uuid_id:
            # obj created in Odoo?
            # Create new UUID in Odoo
            uuid_id = self.sudo().create({
                'o1c_uuid': str(uuid4()),
                'model': model_name,
                'res_id': obj.id,
                'create_in_odoo': True,
            })
            _logger.debug('Object(%s) created in Odoo. '
                          'New UUID created: %s', obj, uuid_id.o1c_uuid)
        return uuid_id.o1c_uuid

    def get_obj_by_uuid(self, uuid, model_name):
        """ Get object by UUID
            The 'UUID' is unique!
            But one Record can have many UUID's.

        # ******************************************************************
        # Warning: if users create Objects in Odoo,
        #   then this Objects don't contain 1C UUID!
        #  So when you will load data from 1C then you can get Duplicate!
        # ******************************************************************

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        WARN: 'model' in Rule can be changed!
        WARN: in Rules one 1C model can be linked
          with two different models!
        WARN: case:
          export Odoo->1C: product.product -> Номенклатура
            in Odoo for product.product stored UUID 1!
            in 1C created new 'Номенклатура' with UUID 1!
          export 1C->Odoo: the same Номенклатура -> product.TEMPLATE
            in 1C created new 'Номенклатура' with UUID 1!
            in Odoo we find UUID 1. BUT MODEL IS product.PRODUCT!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        :param uuid:
        :param model_name:
            WARN: model_name MUST be exist in env!
        :return:
        """
        this_obj = None
        if not uuid:
            _logger.warning('Search Record by empty UUID! Model %s!', model_name)
            return None, None
        dom = [('o1c_uuid', '=', uuid)]
        if model_name:
            dom += [
                ('model', '=', model_name),
            ]
        else:
            _logger.error('UUID %s without model!', uuid)
        link_to_obj = self.sudo().search(dom)
        if not link_to_obj:
            # _logger.debug('Object with UUID: %s dont exist. New Object?', uuid)
            return None, None
        # WARN: Model can be removed from DB! Check it.
        # TODO write code which remove uuids of removed models
        link_to_obj = link_to_obj.filtered(
            lambda r: self.sudo().env.get(r.model) is not None)
        if not link_to_obj:
            _logger.warning('Object with UUID: %s dont exist. The Model was removed?', uuid)
            return None, None
        if len(link_to_obj) > 1:
            _logger.error(
                'More then one Record with UUID: %s. Records: %s',
                uuid, ['m: %s id %s' % (l.model, l.res_id) for l in link_to_obj])
            link_to_obj = link_to_obj[0]

        # 'browse' better than 'search' ?
        this_obj = self.env[link_to_obj.model].sudo().search([
            ('id', '=', link_to_obj.res_id)
        ], limit=1)
        if not this_obj:
            _logger.debug('Object with UUID: %s was removed. But it can be created again.', uuid)
        return this_obj, link_to_obj
