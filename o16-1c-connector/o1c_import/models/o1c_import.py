# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.
# pylint: disable=no-else-return,too-many-locals,too-many-return-statements
# flake8: noqa: E501

import os
import logging
import re
import shutil
import base64
import zlib

# WARNING: don't use 'lxml.etree'!
# Because it can't upload large xml-files.
import xml.etree.ElementTree as ET

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class O1CImport(models.AbstractModel):
    _name = 'o1c.import'
    _inherit = 'o1c.connector'

    @staticmethod
    def get_node_key(node_dict, search_tag_type, search_tag_name, return_key, raise_error=False, log_error=True):
        if not node_dict:
            return
        for t in node_dict:
            if search_tag_type and t['tag_type'] != search_tag_type:
                continue
            if search_tag_name and t.get('tag_name', 'tag-name-is-absent') != search_tag_name:
                continue
            return t.get(return_key)
        else:
            if not raise_error and not log_error:
                return
            text_error = _("Can't find node")
            if search_tag_type:
                text_error += _(' with type: %s') % search_tag_type
            if search_tag_name:
                text_error += _(' with name: %s') % search_tag_name
            text_error += _(' in data: %s') % node_dict

            if raise_error:
                raise UserError(text_error)
            if log_error:
                _logger.debug(text_error)
            # else:
            #     _logger.debug(text_error)

    def get_prepared_obj_data(
            self, convert_rules, rule_name, obj_data, tag_dont_refill,
            model_name, obj_cache, xml_line, force_upload, recursion_level):
        """ Search Object and convert data from XML to odoo dictionary
        used for 'write' or 'create' methods

        WARN: this func run recursively when link to other object:
            obj_data['childs'] contain 'Ссылка'

        :return: dict with data for 'write' or 'create' method
        """

        def get_rule(convert_rules, rule_name):
            if not rule_name:
                return
            rules = convert_rules.get('childs')
            if not rules:
                return
            rule = None
            for t in rules:
                if t['tag_type'] == 'Правило' and t['childs']:
                    for tt in t['childs']:
                        if tt.get('tag_type') == 'Код' and tt.get('value') == rule_name:
                            rule = t['childs']
                            break
            if not rule:
                raise UserError(_(
                    'Error: Can\'t find "Правило" in Rules for %s') % rule_name)
            return rule

        def get_item_uuid(keys):
            uuid = ''
            for i in keys:
                if i['tag_name'] == '{УникальныйИдентификатор}' and i['tag_type'] == 'Свойство':
                    # Note: UUID can be empty if Object generated
                    uuid = i.get('tag_value', '')
                    break
            else:
                _logger.debug('Cant find tag "{УникальныйИдентификатор}" in Keys')
            return uuid

        def get_object(convert_rules, rule_name, keys, model_name, xml_line):
            rule = get_rule(convert_rules, rule_name)

            uuid = get_item_uuid(keys)
            if rule:
                uuid_sync = self.get_node_key(rule, 'СинхронизироватьПоИдентификатору', False, 'value', log_error=False) == 'true'
                keys_sync = self.get_node_key(rule, 'ПродолжитьПоискПоПолямПоискаЕслиПоИдентификаторуНеНашли', False, 'value', log_error=False) == 'true'
            else:
                uuid_sync = True  # default search by UUID
                keys_sync = True if keys else False
                # It's not error if it object field, which exported with flag: "ВыгружатьТолькоСсылку"
                _logger.debug('Cant determine Rule. Cant determine Object sync type: by UUID or by Keys! Search data: %s', keys)

            if not uuid_sync and not keys_sync:
                # Example: export from Перечисление
                _logger.warning('[%s] Object not searchable! UUID search and Keys search are disabled! %s', xml_line, keys)
                # We have to fix this, therwise Object will not be found
                # TODO before set 'True' to 'keys_sunc': check is fields search exist in 'keys'?
                #  WARN: in 'keys' can be only one key: УникальныйИдентификатор
                #  so be careful when you will write this search
                keys_sync = True

            # search model item by UUID or name
            link_to_obj = False
            this_obj = False
            if uuid_sync:
                if uuid:
                    # search by 1C 'UUID'
                    this_obj, link_to_obj = self.env['o1c.uuid'].get_obj_by_uuid(uuid, model_name)
                else:
                    _logger.debug('[%s] Item sync by UUID but UUID is not exist in %s', xml_line, keys)

            if not this_obj and keys_sync:
                # search by fields

                # ************************************************************************************
                # WARNING: in this case you get many Objects in Odoo and only one Object in 1C!
                #  So when you will load data from Odoo to 1C - you fill get problem with erased data
                #   because in Odoo different Objects containe different info,
                #   but in 1C you have only one(!) Object and you can't put different data in one field!
                #  So use this Search type only for oneway integration: from 1C to Odoo.
                #   But we don't recommend to use this Search...
                # ************************************************************************************
                this_model_sudo = self.env[model_name].sudo()
                model_fields = this_model_sudo._fields
                dom = []
                for key_field in keys:
                    key_field_name = key_field.get('tag_name')
                    if not key_field_name:
                        _logger.error(
                            '[%s] tag_name not in key_field "%s". model "%s"',
                            xml_line, key_field, model_name)
                        continue
                    if key_field_name == '{УникальныйИдентификатор}':
                        continue
                    if key_field_name not in model_fields:
                        _logger.error(
                            '[%s] Field name "%s" not in model "%s" fields',
                            xml_line, key_field_name, model_name)
                        continue
                    key_field_val = key_field.get('tag_value')
                    if key_field_val is not None:
                        # TODO make search with operators: 'like', 'ilike', ... Not only by '='.
                        # FIXME convert types: o2m, m2o, m2m, data, ...?
                        dom += [(key_field_name, '=', key_field_val)]
                    elif key_field.get('childs') and key_field.get('tag_o1c_type'):
                        # Example: find by field with type: m2o, o2m, m2m,
                        sub_model_name, ff = self.from_1c_to_odoo_name(key_field['tag_o1c_type'])
                        if not sub_model_name or sub_model_name not in self.env:
                            _logger.error('[%s] Incorrect model name %s', xml_line, key_field['tag_o1c_type'])
                            continue

                        sub_keys = self.get_node_key(key_field['childs'], 'Ссылка', None, 'childs', log_error=False)
                        if not sub_keys:
                            _logger.error(
                                '[%s] Can\'t search by field %s \n'
                                '\tkeys_sync=True key_field_name=%s',
                                xml_line, key_field, key_field_name)
                            continue

                        # Note: rule_name dont exist in key_field. Skip them.
                        rule_name = False
                        # WARN: start recursion!
                        this_obj_dict = get_object(convert_rules, rule_name, sub_keys, sub_model_name, xml_line)
                        if not this_obj_dict or not this_obj_dict['this_obj']:
                            _logger.error(
                                '[%s] Object not find. Cant search by object field name %s \n'
                                '\tkeys_sync=True search_field=%s',
                                xml_line, key_field_name, key_field)
                            continue
                        # TODO check len(this_obj_dict['this_obj']) > 1
                        dom += [(key_field_name, 'in', this_obj_dict['this_obj'].ids)]

                    else:
                        _logger.error(
                            '[%s] Can\'t read value %s \n'
                            '\tkeys_sync=True key_field_name=%s',
                            xml_line, key_field, key_field_name)

                if len(dom) == 0:
                    # This situation emerge when set flag 'Continue search by fields' and not set any field for search.
                    # Examples:
                    #   Search by fields but fields is not determined in keys data:
                    #       [{'tag_type': 'Свойство', 'tag_value': '1ef2e179-c411-11e9-81a0-00e081e3a0a2', 'tag_name': '{УникальныйИдентификатор}', 'tag_o1c_type': 'Строка'}]
                    #    ^-- only UID is set.
                    #   Search by fields but fields is not determined in keys data:
                    #       [{'tag_type': 'Свойство', 'tag_value': '6cac1269-c4c3-11e9-81a0-00e081e3a0a2', 'tag_name': '{УникальныйИдентификатор}', 'tag_o1c_type': 'Строка'}]
                    #    ^-- only UID is set.
                    # Just ignore this message. Or remove flag 'Continue search by fields'.
                    _logger.debug('[%s] Search by fields but fields is not determined in keys data: %s', xml_line, keys)
                else:
                    # search in Active and Non-active records
                    # TODO make two searches: 1. search in actives -> if not found 2. search in non-actives
                    if 'active' in model_fields:
                        dom += ['|', ('active', '=', False), ('active', '=', True)]
                    this_obj = this_model_sudo.search(dom)
                    if len(this_obj) > 1:
                        _logger.error('[%s] Find more then one row: %s in model: %s', xml_line, this_obj, model_name)
                        # Когда в базе уже есть дубликаты, то варианты поведения:
                        # 0. Не создавать новую запись!
                        #   Это правильное поведение для всех кейсов. Мы же не хотим добавлять дубликаты
                        # ______________________________________________________________________________________________
                        # Существующие дубликаты Использование:
                        # 1. Не использовать.
                        #   В таком случае например при загрузке документа, где есть обязательное поле Контрагент
                        #   документ не загрузиться! Потому что мы не заполнили Контрагента.
                        #   Загрузка прервется! Загрузить можно будет только в Force режиме.
                        # 2. Использовать первый попавшийся или определять одного, по какому-то алгоритму,
                        # например кого последнего изменяли.
                        #   В таком случае документы будут создаваться, но если дубликаты - это реально разные записи,
                        #   то может подставляться не корректный Контрагент.
                        #   Но тут уж нужно либо почистить дубликаты, либо уточнить ключ уникалности.
                        #   В любом случае алгоритм интеграции работает корректно.
                        # ВЫВОД: возможно лучше использовать не верный, но загрузить документ
                        #   Чем не спользовать ни один и не загрузить документ да к тому же еще и прервать загрузку!!!
                        #    Только для серьезных проектов, где корректность данных - критична, лучше прервать загрузку,
                        #    чем загрузить не корректные данные.
                        #   Так же не плохой будет гибридный алгоритм:
                        #    не использовать Запииси-дубликаты, но при ошибке загрузки Документа, пропускать этот документ.
                        #    и не прерывать загрузку. Только из-за таких пропуской нарушается целостность данных.
                        #    Поэтому не понятно что хуже:
                        #       прервать загрузку или загрузить не корректные данные.
                        # ______________________________________________________________________________________________
                        # Существующие дубликаты Обновление:
                        # 1. Не обновлять:
                        #   Тогда будут недогружать некоторые данные.
                        # 2. Обновлять какой-то один. Определить алгоритм по которому будет определяться этот "один".
                        #   Если дубликаты - это реально разные записи, то при неправильном выборе алгоритма
                        #   (а его нельзя выбрать один правильный для всех кейсов)
                        #   может обновиться(замениться) не та запись что нужно!!
                        #   А это хуже чем удалить запись!
                        # 3. Обновлять все
                        #   Если дубликаты - это реально разные записи, то при неправильном выборе алгоритма
                        #   (а его нельзя выбрать один правильный для всех кейсов)
                        #   может обновиться(замениться) не та запись что нужно!!
                        #   А это хуже чем удалить запись несколько записей!
                        # ВЫВОД: лучше не обновлять!!!

                        # ==========================================
                        # Don't create new one, because we already have duplicates
                        #  BUT! we GET ERROR WHEN filed is required!
                        return
                        # ==========================================

                        this_obj = False  # FIXME >>>> we already have duplicates!!! AND this code make create new one!!
                    else:
                        _logger.debug('[%s] Find object: %s by: %s', xml_line, this_obj, dom)
            return {
                'this_obj': this_obj,
                'link_to_obj': link_to_obj,
                'rule': rule,
                'uuid_sync': uuid_sync,
                'uuid': uuid,
                'obj_name': self.get_node_key(keys, 'Свойство', 'name', 'tag_value', log_error=False) or '',
            }

        def get_img_header_len(img):
            # example: {+1 {+2 {+3 -3} {+3 -3} -2} {+2 -2}...  -1}
            # return   ^+1.....................................-1^
            level = 0
            cut_len = 0
            while True:
                first_k = img[cut_len:].find('{')
                if first_k == -1:
                    # UPS: error can't find "}"
                    add_level = -1
                else:
                    end_kx = img[cut_len:].find('}')
                    if end_kx == -1:
                        # UPS: error can't find "}"
                        cut_len += first_k
                        add_level = -1
                    elif end_kx < first_k:
                        # }...{
                        cut_len += end_kx+1
                        add_level = -1
                    else:
                        # {??????}
                        add_level = 1
                        cut_len += first_k+1
                level += add_level
                if level == 0:
                    break
            return cut_len

        if recursion_level > 100:
            _logger.error("ERROR: recursion depth > 100. "
                          "Something wrong. Obj. data: %s", obj_data)
            return
        if model_name not in self.env:
            if force_upload:
                _logger.error("ERROR: can't find model: %s", model_name)
                return
            raise UserError(_("ERROR: can't find model: %s") % model_name)

        update_data = {}
        keys = self.get_node_key(obj_data, 'Ссылка', None, 'childs', log_error=False)
        if keys:
            if not rule_name:
                # example: ConversionRule 'ВыгружатьПоСсылке' = False or try to find Object by keys
                _logger.debug('[%s] Object with <Ссылка>, but without(!) Rule name in model: %s! Object data: %s', xml_line, model_name, obj_data)
                # FIXME TODO ???
            this_obj_dict = get_object(convert_rules, rule_name, keys, model_name, xml_line)
            if not this_obj_dict:
                return this_obj_dict, update_data
            # add search fields from 'Ссылка' to Object fields
            obj_data += keys
        else:
            this_obj_dict = None
            # example: <ТабличнаяЧасть><Запись>...
            if rule_name:
                # FIXME what is it???
                _logger.error('[%s] Object without <Ссылка>, but with(!) Rule name in model: %s! Object data: %s', xml_line, model_name, obj_data)

        # Add object number to cache if it already exist in DB. Before create Object.
        tag_o1c_obj_number = self.get_node_key(obj_data, 'Ссылка', None, 'tag_o1c_obj_number', log_error=False)
        if tag_o1c_obj_number:
            if obj_cache.get(tag_o1c_obj_number):
                if force_upload:
                    _logger.error('[%s] Object changed in cache!!!', xml_line)
                    return this_obj_dict, update_data
                raise UserError(_('[%s] Object changed in cache!!!') % xml_line)
            obj_cache[tag_o1c_obj_number] = this_obj_dict and this_obj_dict.get('this_obj') and this_obj_dict['this_obj'].id or -1
        else:
            if rule_name:  # TODO find better determine 'if not is_folder'.
                tag_dont_create = self.get_node_key(
                    obj_data, 'Ссылка', None, 'tag_dont_create', log_error=False)
                if tag_dont_refill and tag_dont_create:
                    # Don't Update and Don't Create! Only search.
                    # Note: we can read 'Нпп' in <Объект Нпп="77">, search Object and store link in Cache for seadup import.
                    # But in the lines below XML don't contain 'Нпп' in <Ссылка>,
                    #  that's why we don't try store Link to founede Object in Cache.
                    pass
                else:
                    # This is Model. This is NOT 'ТабличнаяЧасть' and NOT 'Запись'. Where his number???
                    _logger.error('[%s] Cant add Object to cache without XML Number!', xml_line)

        for i in obj_data:
            if i['tag_type'] == 'Свойство':
                tag_name = i.get('tag_name')
                if tag_name and tag_name == '{УникальныйИдентификатор}':
                    continue
                tag_dont_refill_field = i.get('tag_dont_refill_field')
                if tag_dont_refill_field and this_obj_dict and this_obj_dict.get('this_obj'):
                    _logger.debug(
                        'Skip field %s because it locked to refill for exist object %s',
                        tag_name, this_obj_dict['this_obj'])
                    continue
                i_keys = i.keys()
                if tag_name and 'tag_value' in i_keys:
                    # TODO recode: don't use 'tag_o1c_type' instead 'fields[this_field].type'
                    tag_o1c_type = i.get('tag_o1c_type', '?')
                    if tag_o1c_type == 'Булево':
                        update_data[tag_name] = i['tag_value']
                    elif tag_o1c_type == 'Дата':
                        if i['tag_value']:
                            update_data[tag_name] = i['tag_value']
                    elif tag_o1c_type == 'ХранилищеЗначения':
                        # TODO сделать отдельню функцию для чтения ХранилищеЗначения,
                        #  т.к. этот код повторяется 2 раза. Ищи тут по "0iI3BTqDV67a9oKcN"
                        # 1 b64decode
                        try:
                            # TODO сделать чтение символов "AgFTS2/0iI3BTqDV67a9oKcN"
                            file_data = base64.b64decode(i['tag_value'].replace('\n', '').replace('AgFTS2/0iI3BTqDV67a9oKcN', ''))
                        except Exception as e:
                            _logger.error('[%s] Cant b64decode and clear 1C ХранилищеЗначения. Error: %s', xml_line, e)
                            continue
                        # 2. unzip and decode
                        try:
                            file_data = zlib.decompress(file_data, -zlib.MAX_WBITS).decode('koi8-r')
                        except Exception as e:
                            _logger.error('[%s] Cant decompress 1C ХранилищеЗначения. Error: %s', xml_line, e)
                            del file_data  # clear mem
                            continue
                        # 3. remove 1C HEADER and encode
                        cut_str = get_img_header_len(file_data)
                        if cut_str > 0:
                            file_data = file_data[cut_str + 12:].encode('koi8-r')
                        else:
                            _logger.warning('[%s] Cant skip 1C Header in data file field!', xml_line)
                            file_data = file_data.encode('koi8-r')
                        # 4. base64.encodestring
                        try:
                            update_data[tag_name] = base64.encodestring(file_data)
                            # remove unnecessary string
                        except Exception as e:
                            _logger.error('[%s] Cant encodestring 1C ХранилищеЗначения. Error: %s', xml_line, e)
                            del file_data  # clear mem
                            continue
                        del file_data  # clear mem
                    else:
                        update_data[tag_name] = i['tag_value']
                elif 'childs' in i_keys:
                    # this is links

                    # ***************************************************************
                    # Преамбула:
                    # 1. данные в файле загрузки расположены в произвольном порядке!
                    # 2. Данные в файле загрузки имеют ссылки друг на друга.
                    #     Например: sale.order и res.partner
                    # 3. Теоретически данные могу ссылаться друг на друга циклически.
                    #  TODO нужно реализовать определение циклических зависимостей и их загрузку
                    # 4. может случиться так, что сначала начнет грузиться Sale.Order,
                    #    а затем res.partner! Но, например Sale.order нельзя создать
                    #    с незаполненным res.partner - иначе будет сгенерировано Исключение.
                    #
                    # Внимание: если мы тут будем создавать пустой объект(наприм.res.partner) только ради ссылки!
                    #  В надежде его обновить(т.е. заполнить его поля данными) ПОЗЖЕ, то можем получить Исключение!
                    #  Т.к. возможно res.partner нельзя создать с пустями обязательными полями(напр.name)
                    #
                    # Вывод: мы получили Проблему:
                    #  загрузить SO не можем пока не создадим res.partner,
                    #  а res.partner мы не можем создать без дополнительных полей,
                    #  значения которых мы получим ПОЗЖЕ(при дальнейшем чтении файла загрузки).
                    #  PS: весь файл загрузки мы не можем загрузить в память, т.к. он может быть слишком большой,
                    #   из-за чего мы вынуждены читать его порциями.
                    #
                    # Решение: лучше отложить создание Объекта Sale.Order пока на будет создан res.partner
                    # а сам res.partner создавать только когда у нас убудут все его данные,
                    # полученные из файла загрузки. Т.е. позже.
                    #  TODO Но чтобы реализовать эту схему нужно:
                    #   1. сделать хранилище незагруженных объектов
                    #    1.2. выстроить объекты в виде дерева зависимостей
                    #     чтобы когда наступит время их до-загрузки - загружать их в порядке подчинения
                    #     иначе даже в момент до-загрузки мы можем получить эту же коллизию
                    #
                    #   2. сделать алгоритм до-загрузки незагруженных объектов
                    #   3. реализовать отслеживание ситуации когда объекты циклически ссылаются
                    #
                    # Решение 2: реализовать поиск данных XML через объект tree,
                    #  используя поисковые функции типа xpath! Это обходит проблему загрузки
                    #  больших файлов в память целиком.
                    #  Минус в уменьшении скорости загрузки из файла,
                    #   т.к. такой поиск будет сильно замедлять загр-у
                    # ***************************************************************

                    # determine Object Number in XML data
                    tag_o1c_obj_number = self.get_node_key(i['childs'], 'Ссылка', None, 'tag_o1c_obj_number')
                    if tag_o1c_obj_number:
                        # get Object from cache by his Number
                        sub_obj_id = obj_cache.get(tag_o1c_obj_number)
                    else:
                        sub_obj_id = False

                    if not sub_obj_id:
                        if tag_o1c_obj_number:
                            # It's normal case with flag: "ВыгрузитьТолькоСсылку = Истина" in "ПриВыгрузке"
                            _logger.debug(
                                "[%s] Can't find Object(N: %s) from cache!\n"
                                "Probably the sub-object is export with a flag: ВыгрузитьТолькоСсылку.\n"
                                "Model: %s", xml_line, tag_o1c_obj_number, model_name)
                            pass
                        elif not self.get_node_key(i['childs'], 'Ссылка', None, 'tag_dont_create', log_error=False):
                            # Object created on export.
                            # Example: we need search Account Journal by name or id
                            tag_o1c_obj_number = self.get_node_key(obj_data, 'Ссылка', None, 'tag_o1c_obj_number')
                            _logger.warning(
                                '[%s] Object(N: %s) with Link to Other Object '
                                'without Tag "Нпп"! Model: %s', xml_line, tag_o1c_obj_number, model_name)

                        bind_field_name = i.get('tag_name')
                        if not bind_field_name:
                            _logger.error('xml Item without tag "Имя"!')
                            continue
                        sub_model_name = self.env[model_name]._fields[bind_field_name].comodel_name
                        if not sub_model_name:
                            _logger.error("Can't load Item to field '%s' model '%s'. Field must be O2M or M2M type!", bind_field_name, model_name)
                            continue
                        # Warning: start recursion!!!
                        child_id, child_data = self.get_prepared_obj_data(
                            convert_rules, None, i['childs'], True, sub_model_name,
                            obj_cache, tag_o1c_obj_number, force_upload,
                            recursion_level+1)
                        if child_id and child_id.get('this_obj'):
                            # FIXME if len(child_id['this_obj']) > 1 then get error on getting id: must by singleton
                            sub_obj_id = child_id['this_obj'].id
                        else:
                            sub_obj_id = -1

                    if not sub_obj_id:
                        tag_o1c_obj_number = self.get_node_key(obj_data, 'Ссылка', None, 'tag_o1c_obj_number')
                        if force_upload:
                            _logger.error(
                                "[%s] Can't find Object(N: %s) from cache!\n"
                                "Possibly the sub-object is located in XML below than this object.!\n"  # TODO read description below!
                                "Model: %s", xml_line, tag_o1c_obj_number, model_name)
                            continue
                        raise UserError(_(
                            "[%s] Can't find Object(N: %s) from cache!\n"
                            "Possibly the sub-object is located in XML below than this object.!\n"  # TODO read description below!
                            "Model: %s") % (xml_line, tag_o1c_obj_number, model_name))
                    if sub_obj_id == -1:
                        tag_o1c_obj_number = self.get_node_key(obj_data, 'Ссылка', None, 'tag_o1c_obj_number')
                        _logger.debug("Warning: [%s] can't fill field '%s' of '%s' "
                                      "because object Нпп='%s' don't find in DB and don't created",
                                      xml_line, tag_name, model_name, tag_o1c_obj_number)
                        continue
                    field_type = self.env[model_name]._fields[tag_name].type
                    if field_type in ['many2many', 'one2many']:
                        # TODO create 'Add' mode without clearing all other data.
                        # но чтобы реализовать "загрузку без очистки" нужно придумать алгоритм поиска строк!
                        # иначе при каждой загрузке строк будет становиться все больше, т.е. записи начнут дублироваться!
                        # Можно задействовать в ПравилахКонвертации флаг "Не замещать" в ТабличнойЧасти! Может он поможет.
                        #  но без "алгоритма поиска строк" - записи все равно будут дублироваться!!!
                        update_data[tag_name] = [(6, 0, [sub_obj_id])]
                    else:
                        # TODO if field_type != 'many2one'...? make convert to string....?
                        update_data[tag_name] = sub_obj_id

                elif not tag_name:
                    _logger.debug('[%s] Error: Object|Field name is empty. Skip loading data: %s', xml_line, i)
                else:
                    _logger.error('[%s] Error: incorrect tag name: %s', xml_line, tag_name)
            elif i['tag_type'] == 'Ссылка':
                pass
            elif i['tag_type'] == 'ТабличнаяЧасть':
                bind_field_name = i.get('tag_name')
                if not bind_field_name:
                    _logger.error('xml Item "ТабличнаяЧасть" without tag "Имя"!')
                    continue
                sub_model_name = self.env[model_name]._fields[bind_field_name].comodel_name
                if not sub_model_name:
                    _logger.error("Can't load 'ТабличнаяЧасть' to field '%s' model '%s'. Field must be O2M or M2M type!", bind_field_name, model_name)
                    continue

                update_data[bind_field_name] = []
                # get data for new rows
                for obj_row in i.get('childs', []):
                    if obj_row.get('tag_type', '') != 'Запись' or not obj_row.get('childs'):
                        # raise or add log error ???
                        continue
                    # Warning: start recursion!!!
                    child_id, child_data = self.get_prepared_obj_data(
                        convert_rules, None, obj_row['childs'], True, sub_model_name,
                        obj_cache, xml_line, force_upload,
                        recursion_level+1)
                    # 4. add row data to update_data
                    # new Sub_Object will be generated
                    update_data[bind_field_name] += [(0, 0, child_data)]

                # Clear rows in Parent Object (if Parent Obj already exist?)
                if this_obj_dict and this_obj_dict.get('this_obj'):
                    rs = this_obj_dict['this_obj'][bind_field_name]
                    if not rs:
                        continue
                    need_remove_records = False
                    if len(rs) == 1 and len(update_data[bind_field_name]) == 1:
                        # FIXME rewrite this call as "self.object_is_changed(this_obj, update_data)"
                        # and write code for comparison o2m and m2m field types
                        if self.object_is_changed(rs[0], update_data[bind_field_name][0][2]):
                            # warning: maybe only ONE(!) records is changed, but we remove all(!) records.
                            # it would be better to update(!) only changed(!) record(without any 'removing').
                            need_remove_records = True
                        else:
                            del update_data[bind_field_name]
                    else:
                        # *********************************************************************************
                        # TODO make 'update' mode without clear all existing rows.
                        #  But how to find row without UUID??? What will be the Key???
                        #  Because in 1C the type 'Табличная часть' don't have UUID(!) It's Main Problem!
                        #   But(!) we have rows numbers...
                        #    But in Odoo rows not always have 'order line' and 'row_number'...
                        #         update_data[bind_field_name] = [(5, 0, 0)]
                        #           ...
                        #         child_id = child_id.get('link_to_obj')
                        #         if child_id:
                        #             update_data[bind_field_name] += [(4, child_id.id)]
                        #         else:
                        #             # new Sub_Object will be generated
                        #             update_data[bind_field_name] += [(0, 0, child_data)]
                        # for r in rs:
                        #     if r.number... ???
                        need_remove_records = True
                        # *********************************************************************************
                    if need_remove_records:
                        # WARNING: Object is CHANGED after unlink()! So Object will be rewrited even if it not changed!
                        #   TODO This make 'loading process' slowly! It would be better check: "Object is changed?"
                        #   and if it changed - then remove rows.
                        try:
                            this_obj_dict['this_obj'][bind_field_name].unlink()
                        except Exception as e:
                            if this_obj_dict['this_obj'][bind_field_name]:
                                _logger.error(
                                    'Cant clear rows[%s] in object: %s. Error: %s\n ',
                                    bind_field_name, this_obj_dict['this_obj'], e)
                                # remove data for adding
                                del update_data[bind_field_name]
                            else:
                                # Sometimes rows removed and error
                                _logger.warning(
                                    'Clear rows[%s] in object: %s, but get error: %s\n ',
                                    bind_field_name, this_obj_dict['this_obj'], e)
            else:
                _logger.error('[%s] Error: unknown tag_type: %s', xml_line, i['tag_type'])
        return this_obj_dict, update_data

    def load_data_to_db(self, convert_rules, node_data, obj_cache, force_upload):
        obj_data = node_data['childs']
        xml_line = node_data['Нпп']
        model_name = node_data['model_name']
        this_obj_dict, update_data = self.get_prepared_obj_data(
            convert_rules, node_data['rule_name'], obj_data,
            node_data['tag_dont_refill'], model_name,
            obj_cache, xml_line, force_upload, 1)

        if len(update_data) == 0:
            _logger.debug('[%s] Object without data. XML item data: %s', xml_line, obj_data)
            return
        if not this_obj_dict:
            _logger.error('[%s] Cant determine DB Model. Skip loading Item: %s', xml_line, obj_data)
            return
        if 'name' not in update_data and this_obj_dict['obj_name']:
            update_data['name'] = this_obj_dict['obj_name']
            # TODO проверить: если установить поиск по нескольким полям, то все они попадут в тэг "Ссылка"?
            #  если да, то тут их тоже нужно вытянуть. Либо доработать процедуру get_prepared_obj_data

        this_obj = this_obj_dict['this_obj']
        # Create or Update Model
        if this_obj:
            # Update Model record
            if node_data['tag_dont_refill']:
                _logger.debug('Skip update object %s because "НеЗамещать"', this_obj)
            elif not self.object_is_changed(this_obj, update_data):
                _logger.debug('Object(%s) data not changed. Skipped.', this_obj)
            else:
                _logger.debug(
                    '[%s] Update exist Object(%s[id: %s]). UUID: %s Name: %s',
                    xml_line, model_name, this_obj.id, this_obj_dict['uuid'],
                    this_obj_dict.get('name'))
                try:
                    if force_upload:
                        with self.env.cr.savepoint():
                            this_obj.sudo().with_context(o1c_load=True).write(update_data)
                    else:
                        this_obj.sudo().with_context(o1c_load=True).write(update_data)
                except Exception as e:
                    if force_upload:
                        _logger.error(
                            "[%s] Can't write data: %s \n"
                            "to model: '%s'\n"
                            "Error: %s", xml_line, update_data, model_name, e)
                    else:
                        raise UserError(_(
                            "[%s] Can't write data: %s \n"
                            "to model: '%s'\n"
                            "Error: %s") % (xml_line, update_data, model_name, e))
        else:
            # Create Model record
            if not self.get_node_key(obj_data, 'Ссылка', False, 'tag_dont_create'):
                try:
                    if force_upload:
                        with self.env.cr.savepoint():
                            this_obj = self.env[model_name].sudo().with_context(o1c_load=True).create(update_data)
                    else:
                        this_obj = self.env[model_name].sudo().with_context(o1c_load=True).create(update_data)
                except Exception as e:
                    # Example: ValueError: time data '2021-10-01T12:29:26' does not match format '%Y-%m-%d %H:%M:%S'
                    if force_upload:
                        _logger.error(
                            "[%s] Can't create model record: '%s' "
                            "with data: %s\nError: %s", xml_line, model_name, update_data, e)
                    else:
                        raise UserError(_(
                            "[%s] Can't create model record: '%s' "
                            "with data: %s\nError: %s") % (xml_line, model_name, update_data, e))

                # Add created Object ID with his XML-number to cache. After created Object.
                if this_obj:
                    _logger.debug(
                        '[%s] Create new %s[id: %s]. UUID: %s Name: %s Data: %s',
                        xml_line, model_name, this_obj.id, this_obj_dict['uuid'],
                        this_obj_dict.get('name'), obj_data)
                    tag_o1c_obj_number = self.get_node_key(obj_data, 'Ссылка', None, 'tag_o1c_obj_number')
                    if tag_o1c_obj_number:
                        if obj_cache.get(tag_o1c_obj_number, -1) != -1:
                            raise UserError(_(
                                '[%s] Object changed in cache!!!') % xml_line)
                        obj_cache[tag_o1c_obj_number] = this_obj.id
        self.env['o1c.uuid'].sudo().update_UUID(
            this_obj_dict.get('link_to_obj'),
            this_obj, model_name, this_obj_dict['uuid'],
            xml_line, force_upload)
        self.run_after_upload(this_obj, this_obj_dict)
        return

    def run_after_upload(self, obj, obj_data):
        """ Run code after upload object

        Example 1 fill description in uploaded Product after upload them
            > obj.description_sale = 'some data'

        TODO: needed to make use 'Параметр' ('ПередачаВПараметр') inside execution code

        """
        rule = obj_data.get('rule')
        if not rule:
            return
        after_upload_code = self.get_node_key(rule, 'ПослеЗагрузки', False, 'value')
        if not after_upload_code:
            return
        # Make separate params for ease and simply program code of processing
        # flake8: noqa: F841
        # pylint: disable=unused-variable
        link_to_obj = obj_data.get('link_to_obj')
        try:
            # bandit: B102
            exec(after_upload_code)  # nosec
        except Exception as e:
            _logger.error(
                'Object %s Rule %s. Can\'t execute After Upload code:\n'
                '%s\n\n'
                ' >>> Error: %s\n', obj, rule,
                after_upload_code, e)

    @staticmethod
    def object_is_changed(this_obj, update_data):
        # WARNING: this func is similar, but NOT the same
        #  as func 'odoo_obj_is_changed' in odoo_obj.py!
        # Because this self can be any Odoo-Model.
        object_changed = False
        # check is field value already filled
        for f_name, new_val in update_data.items():
            if f_name not in this_obj._fields:
                # TODO remove this field from model data?
                #  But this func is not for this needed.
                _logger.error(
                    'Warning: field: %s dont exists in model: %s',
                    f_name, this_obj._name)
                continue
            # fields with link types must compare value with ID\IDS!!!
            field_type = this_obj._fields[f_name].type
            if field_type == 'many2one':
                field_value = this_obj[f_name].id
            elif field_type in ['many2many', 'one2many']:
                # Warning: for this moment rows as already unlinked with 'get_object'
                #  and Object will be always marked as "changed" even it not changed.
                #  For Fixing it need to change algorithm in 'get_object' which unlink rows...
                #   but fow make this is need create algorithm for determine "Row is changed?"...
                field_value = this_obj[f_name].ids
                # TODO  Update(Add) vlues or Replace IDS with new value ???
                # FIXME new_val must [4, (id)] or [1, (id)] or...?
                # FIXME And how it compare with ids list? v_for_compare = [i[1] for i on new_val] ..??
            elif field_type == 'date':
                field_value = this_obj[f_name]
                if new_val:
                    if ' ' in new_val:
                        # example: '2019-04-30 12:53:02'
                        new_val = new_val.split(' ')[0]
                    new_val = fields.Date.from_string(new_val)
            elif field_type == 'datetime':
                field_value = this_obj[f_name]
                new_val = new_val.replace('T', ' ')
            elif field_type == 'float':
                # field_value can be '22.0' but new_val can be '22' and we get new_val != field_value. So fixing it:
                field_value = this_obj[f_name] and ('%f' % this_obj[f_name]).rstrip('0').rstrip('.')
            elif field_type == 'char':
                field_value = this_obj[f_name] and this_obj[f_name].strip() or ''
                new_val = new_val and str(new_val).strip() or ''
            elif field_type == 'text':
                field_value = this_obj[f_name] and this_obj[f_name].strip() or ''
                new_val = new_val and str(new_val).strip() or ''
            else:
                field_value = this_obj[f_name]
                # FIXME field_value can be float, int, bool,... but data from xml is string type
                # FIXME ...and this func determine Object as "changed", instead "not changed"
            if new_val != field_value:
                # WARN: None is not equal to False!
                object_changed = True
                _logger.debug(
                    '\t\tWarning: change data in field: %s type: %s model: %s '
                    'name: %s! Old: %s New: %s', f_name, field_type, this_obj._name,
                    this_obj.name_get()[0][1], field_value, new_val)
                break
        return object_changed

    def non_recurs_load(self, tree, level, hierarhy_list, force_upload):
        if tree.tag == 'Объект':
            if not tree.attrib.get('Тип'):
                if force_upload:
                    return
                raise UserError(_('ERROR: Объект without Тип! %s obj: %s') % (tree, tree.get('Нпп', '?')))
            model_name, field_name = self.from_1c_to_odoo_name(tree.attrib.get('Тип'))

            rule_name = tree.attrib.get('ИмяПравила')
            if not rule_name:
                _logger.error('Tag %s without rule_name in Obj: %s!', tree, tree.get('Нпп', '?'))
                return

            # # Update Model field
            # if field_name:
            #     this_model = self.env[model_name]
            #     if field_name not in this_model._fields:
            #         print('ERROR: model dont have field: %s obj: %s' % (field_name, tree.get('Нпп', '?')))
            #     else:
            #         print('????')

            # Check control
            # hierarhy_list must equil to {'0': [{'tag_type': 'ФайлОбмена'}], '1': []}
            if level != 1 or len(hierarhy_list.keys()) != 2:
                _logger.error('Объект в Объекте! Непредвиденная ситуация! Алгоритм на такое не рассчитан. Data: %s', hierarhy_list)
                if force_upload:
                    return
                raise UserError(_('Объект в Объекте! Непредвиденная ситуация! Алгоритм на такое не рассчитан. Data: %s') % hierarhy_list)
            hierarhy_list[str(level)].append({
                'tag_dont_refill': self.xml_attr_to_bool(tree.attrib.get('НеЗамещать')),
                'model_name': model_name,
                'rule_name': rule_name,
                'Нпп': tree.get('Нпп', '?'),
            })
        else:
            # TODO needed to rewrite node_dict arhitecture
            #  from: [{
            #   'tag_type': 'ПравилаОбмена',
            #   'childs': [
            #       {'tag_type': 'ВерсияФормата', 'value': '2.01'},
            #       {'tag_type': 'ДатаВремяСоздания', 'value': '2019-06-18T11:28:47'},
            #       {'tag_type': 'Источник', 'value': 'БухгалтерияДляУкраины'},
            #   }]}]
            #  to: [{
            #   'ПравилаОбмена': {
            #       'attrs': {...},
            #       'childs': [{
            #           'ВерсияФормата': '2.01',
            #           'ДатаВремяСоздания': '2019-06-18T11:28:47',
            #           'Источник': 'БухгалтерияДляУкраины',
            #       }]
            #    }]
            this_et = {
                'tag_type': tree.tag,
            }
            if tree.attrib:
                if 'Имя' in tree.attrib and tree.attrib['Имя']:
                    this_et['tag_name'] = tree.attrib['Имя']
                if 'Тип' in tree.attrib and tree.attrib['Тип']:
                    this_et['tag_o1c_type'] = tree.attrib['Тип']
                if 'Нпп' in tree.attrib and tree.attrib['Нпп']:
                    # Warning: <Объект> have attr 'Нпп' in his attributes,
                    #  and tag <Ссылка>(of this <Объект>) also have the same 'Нпп' in attributes.
                    #  But 'Нпп' of <Ссылка> sometimes is MISSING!!!
                    #  If Obj importing in mode 'НеЗамещать' then his <Ссылка> DON'T contain 'Нпп'!!
                    #  And in the same time: <Объект> attributes contain 'Нпп' attr!
                    # Note: we use Object 'Нпп' for search object in DB and store his link in Cache
                    #  for seadup process of import.
                    this_et['tag_o1c_obj_number'] = tree.attrib['Нпп']
                if 'НеСоздаватьЕслиНеНайден' in tree.attrib and tree.attrib['НеСоздаватьЕслиНеНайден']:
                    this_et['tag_dont_create'] = tree.attrib['НеСоздаватьЕслиНеНайден'] == 'true'
                if 'НеЗамещать' in tree.attrib and tree.attrib['НеЗамещать']:
                    this_et['tag_dont_refill_field'] = self.xml_attr_to_bool(tree.attrib['НеЗамещать'])

            if tree.text is not None:
                vl = tree.text.strip()
                if vl:
                    this_et['value'] = vl
            # if this_et.get('tag_name', False) == False and this_et.get('tag_value', False) != False:
            #     _logger.debug('Warning: tag_value without tag_name. Tree: %s xml obj: %s', tree, tree.get('Нпп', '?'))
            hierarhy_list[str(level)].append(this_et)

    @staticmethod
    def xml_attr_to_bool(str_val):
        # WARN: str_val can contain None!
        if not str_val:
            return False
        if str_val == '1':
            return True
        if str_val.lower() in ['true', 'истина', 'істина']:
            return True
        return False

    @staticmethod
    def run_expression(expression, element_data):
        """ Run python Code Before upload

        Example:
        In 1C:
        Выражение = "write odoo code here!"

        In xml:
        <Свойство Имя="company_id" Тип="СправочникСсылка.resCompany">
            <Выражение>write odoo code here!</Выражение>
        </Свойство>

        """
        if not expression:
            return
        try:
            return eval(expression)
        except Exception as e:
            _logger.error(
                'Cant execute Expression: %s.\n'
                '\tData: %s\n'
                '\tError: %s', expression, element_data, e)

    @staticmethod
    def val_to_type(val, val_type):
        """ From readed value to declared val

        :param val:
        :param element_data:
        :return:
        """
        if not val_type:
            return val
        elif val_type == 'Число':
            if isinstance(val, str):
                if '.' in val or ',' in val:
                    try:
                        return float(val)
                    except Exception as e:
                        _logger.error('Can\'t transform value %s to float. Error: %s', val, e)
                else:
                    try:
                        return int(val)
                    except Exception as e:
                        _logger.error('Can\'t transform value %s to int. Error: %s', val, e)
            elif isinstance(val, [int, float]):
                return val
            else:
                _logger.warning('Can\'t transform value(type %s) %s to int.', type(val), val)
        elif val_type == 'Булево':
            if isinstance(val, str):
                if val == '1':
                    return True
                if val == '0':
                    return False
                if val.lower() in ['true', 'истина', 'істина']:
                    return True
                if val.lower() in ['false', 'ложь', 'хибне']:
                    return False
                # value is incorrect
                _logger.debug(
                    "Bool value '%s' are incorrect. Must be one of "
                    "['0', '1', True, False, Истина, Ложь, Істина, Хибне]", val)
                return
            elif isinstance(val, bool):
                return val
            else:
                _logger.warning('Can\'t transform value(type %s) %s to int.', type(val), val)
        elif val_type == 'Строка':
            if not isinstance(val, str):
                try:
                    # WARN: transform to str some types may lead to unpredictable results!
                    # TODO check types
                    return str(val)
                except Exception as e:
                    _logger.error('Can\'t transform value %s to bool. Error: %s', val, e)
        elif val_type == 'Дата':
            # example: '2019-04-30T12:53:02'
            # FIXME timezone
            return val and val.replace('T', ' ') or val
        else:
            # Example 1: selected type:
            # val_type == 'productProduct__Type' val == 'consu'
            # Example 2: ХранилищеЗначения
            _logger.debug('Unknown value type %s. Value: %s', val_type, val)
        return val

    def read_xml_node(self, element_data, childs, element):
        if not childs:
            return
        if len(childs) == 1:
            if childs[0]['tag_type'] == 'Значение':
                if 'value' in childs[0]:
                    element_data['tag_value'] = self.val_to_type(
                        childs[0]['value'],
                        element_data.get('tag_o1c_type'))
                elif element.text is not None:
                    element_data['tag_value'] = self.val_to_type(
                        element.text.strip(),
                        element_data.get('tag_o1c_type'))
            elif childs[0]['tag_type'] == 'Пусто':
                element_data['tag_value'] = None
            elif childs[0]['tag_type'] == 'Выражение':
                element_data['tag_value'] = self.run_expression(
                    childs[0]['value'], element_data)
            else:
                if 'childs' not in element_data:
                    element_data['childs'] = []
                element_data['childs'] += childs
        elif len(childs) > 1:
            if 'childs' not in element_data:
                element_data['childs'] = []
            element_data['childs'] += childs

    @api.model
    def load_1c_data(self, cron_mode=False, force_upload=False):
        upload_path, uploaded_dir = self.env['o1c.connector'].\
            get_create_exchange_dirs(cron_mode, 'upload')
        if not upload_path or not uploaded_dir:
            comment_txt = 'Can\'t load data from 1C. Check upload folders and settings in General Settings!'
            if not cron_mode:
                raise UserError(comment_txt)
            _logger.error(comment_txt)
            return
        objects_to_commit = int(self.env['ir.config_parameter'].sudo().get_param(
            'o1c.o1c_objects_to_commit', 500))
        test_mode = self._context.get('test_mode')
        for f_name in [i for i in os.listdir(upload_path) if re.search('xml$', i[-3:], re.IGNORECASE)]:
            file_path = os.path.join(upload_path, f_name)
            level = -1
            correct_format = False
            hierarhy_list = {}
            convert_rules = {}
            obj_cache = {}
            loaded = [0]
            try:
                for event, element in ET.iterparse(file_path, events=['start', 'end']):
                    if not correct_format and element.tag != 'ФайлОбмена':
                        continue
                    if element.tag == 'ФайлОбмена' and event == 'start':
                        correct_format = True  # TODO >> element.get('ВерсияФормата', '?') == '2.0'
                        _logger.info('Start uploading file: %s. Info: %s', file_path, element.attrib)
                    if not correct_format:
                        continue

                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    # FIXME TODO make check Destination Odoo-DB UUID
                    # FIXME TODO  for make PROTECTION(!!!) uploading data "FROM Odoo to 1C.xml" in Odoo! (incorrect!)
                    # FIXME TODO  instead "From 1C to Odoo.xml" in Odoo (correct)
                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                    if event == 'start':
                        level += 1
                        hierarhy_list[str(level)] = []
                        self.non_recurs_load(element, level, hierarhy_list, force_upload)
                    else:
                        if element.tag == 'Объект':
                            element_data = hierarhy_list.pop(str(level))[0]
                            self.load_data_to_db(convert_rules, element_data, obj_cache, force_upload)

                            # Commit after X objects. For free memory and make transaction less!
                            if not test_mode and loaded[0] != 0 and loaded[0] % objects_to_commit == 0:
                                # FIXME pylint error [E8102(invalid-commit), O1CCommon.non_recurs_load] Use of cr.commit() directly -
                                #  More info https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst#never-commit-the-transaction
                                self.env.cr.commit()
                                _logger.info('\t  Uploaded: %s Current object: %s', loaded[0], element_data['Нпп'])
                            loaded[0] += 1
                        elif element.tag == 'ПравилаОбмена':
                            element_data = hierarhy_list.pop(str(level))[0]
                            for t in element_data['childs']:
                                if t['tag_type'] == 'ПравилаКонвертацииОбъектов':
                                    convert_rules.update(t)
                        elif element.tag == 'ФайлОбмена':
                            _logger.info('End of data file.')
                        else:
                            childs = hierarhy_list.pop(str(level))
                            element_data = hierarhy_list[str(level-1)][-1]
                            self.read_xml_node(element_data, childs, element)
                        level -= 1
                # *****************************************************************************************************************************
                # Make commit after upload each file
                # FIXME pylint error [E8102(invalid-commit), O1CCommon.non_recurs_load] Use of cr.commit() directly -
                #  More info https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst#never-commit-the-transaction
                if not test_mode:
                    self.env.cr.commit()
                    _logger.info('\t  Committed last.')
                # *****************************************************************************************************************************
            except Exception as e:
                comment_txt = 'File: %s upload error: %s\nData: %s' % (
                    file_path, e, hierarhy_list)
                if not force_upload:
                    raise UserError(comment_txt)
                _logger.error(comment_txt, exc_info=True)
                # FIXME >>>>> MOVE FILE TO "INCORRECT" sub-folder
                continue

            try:
                shutil.move(
                    file_path,
                    os.path.join(uploaded_dir, f_name))
                _logger.info('File: %s uploaded', file_path)
            except Exception as e:
                comment_txt = 'Cant move file: %s to "uploaded" folder. Error: %s' % (file_path, e)
                if not cron_mode:
                    raise UserError(comment_txt)
                _logger.error(comment_txt, exc_info=True)
                continue

    @api.model
    def post_data(self, xml_data):
        """ Get data from 1C by http(s),
        store them to upload folder,
        read xml-data and upload in DB

        """
        _logger.debug('Load data from 1C. Getted data from 1C XML. Data: %s', xml_data)
        # 1. Cut prefix
        try:
            i = str(base64.b64encode(xml_data.data)).\
                replace(r'\r\n', '').\
                replace('AgFTS2/0iI3BTqDV67a9oKcN', '')
        except Exception as e:
            user_message = "Prepare data error: %s" % e
            _logger.error(user_message)
            return user_message
        # 2. b64decode
        try:
            file_data = base64.b64decode(i[1:])
            del i
        except Exception as e:
            user_message = 'Cant b64decode data from 1C ХранилищеЗначения. Error: %s' % e
            _logger.error(user_message)
            return user_message
        # 3. Decompress data
        try:
            file_data = zlib.decompress(file_data, -zlib.MAX_WBITS)
        except Exception as e:
            user_message = 'Cant decompress 1C ХранилищеЗначения. Error: %s' % e
            _logger.error(user_message)
            return user_message
        # 4. Change '""' to '"'
        try:
            # this code looks strange
            file_data = file_data[17:-2].decode('utf-8').replace('""', '"').encode('utf-8')
        except Exception as e:
            user_message = 'Cant decode-encode xml data. Error: %s' % e
            _logger.error(user_message)
            return user_message

        upload_path, uploaded_dir = self.env['o1c.connector'].\
            get_create_exchange_dirs(
                True,  # cron mode
                'upload')

        f_name = fields.datetime.now().strftime("%Y-%m-%d %H_%M_%S") + '.xml'
        f = open(os.path.join(upload_path, f_name), "wb+")
        f.write(file_data)
        f.close()

        self.load_1c_data(
            cron_mode=True,
            force_upload=False)  # Add option 'force_upload'

        return 'ok'
