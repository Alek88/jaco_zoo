# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.
# pylint: disable=no-else-return,too-many-locals,too-many-return-statements

import logging
import base64
from collections import OrderedDict
from os.path import join as path_join
# TODO bandit [B410:blacklist] Using etree to parse untrusted XML data
#  is known to be vulnerable to XML attacks. Replace etree
#  with the equivalent defusedxml package.
from lxml import etree as ET  # nosec

from odoo import api, models, fields, _
from odoo.exceptions import UserError
# html2plaintext used in rules
from odoo.tools import format_datetime, html2plaintext

_logger = logging.getLogger(__name__)


class Conversions(models.Model):
    _name = 'o1c.conv'
    _inherit = ['o1c.conv', 'o1c.connector']

    rule_ids = fields.One2many('conv.rule', 'conv_id', string='Rules')
    format_version = fields.Char()
    source_name = fields.Char()
    destin_name = fields.Char()
    o1c_uuid = fields.Char('UUID', help='Conversion UUID')  # TODO make required=True
    source_file_name = fields.Char(help='This Conversion are uploaded from file name')
    conv_upload_date = fields.Datetime(help='This Conversion are uploaded id this date')

    def exp_add_node_to_xml(self, root, data, obj_cache, parents, subobj_mode=False, parent_is_object=False):
        """ Recursively add data to xml
        This func have two circles:
        1. recursively scan dictionary node
            and FIRST OF ALL - add Objects in xml
        2. add attributes of Objects

        WARN 1: forbidden to add Object inside Object
        WARN 2: forbidden to add Object Attribute outside Object
        WARN 3: data contain circles! But in XML data we can't add them!
        WARN 4: in XML data order of Objects is important!
            Because some Objects can have depends from other Objects!

        """

        def get_create_obj_id(obj_id, obj_cache):
            this_npp = obj_cache.get(obj_id)
            if not this_npp:
                this_npp = str(len(obj_cache) + 1)
                obj_cache[obj_id] = this_npp
            #     _logger.debug('New Нпп created: %s for object id: %s', this_npp, obj_id)
            # else:
            #     _logger.debug('Get added Нпп: %s for object id: %s', this_npp, obj_id)
            return this_npp

        def add_att(data, this_attrs, attr_name, o1c_name, log_err=True):
            attr_val = data.get(attr_name, None)
            if attr_val is not None:
                if isinstance(attr_val, str):
                    this_attrs[o1c_name] = attr_val
            else:
                if not log_err:
                    return
                # FIXME Tip MUST DETERMINE BY "SOURCE Тип", instead "Internal Тип"!!!!! <<<<<
                # FIXME standalone test error:
                #  Incorrect xml-attribute: tip data type: None type: <class 'NoneType'>
                #   saleOrderLine -> 'ДокументСсылка.КомплектацияНоменклатуры' -> keys -> Свойство "Номер"
                #   or Свойство "Дата"
                _logger.error(
                    'Incorrect xml-attribute: %s'
                    ' data type: %s type: %s',
                    attr_name, attr_val, type(attr_val))

        def exit_this_step(val=None):
            # _logger.info('< exit XML')
            return val

        if not data:
            return exit_this_step()
        elif not isinstance(data, dict):
            _logger.error('Node data is incorrect: %s', data)
            return exit_this_step()
        _logger.debug(
            '> start XML data: %s - %s subobj_mode: %s parent_is_object: %s',
            data.get('xml'), data.get('name'), subobj_mode, parent_is_object)
        node_type = data.get('xml', False)
        if not node_type:
            _logger.debug('Skipped empty node data: %s', data)
            return exit_this_step()
        # In 'keys' data can also contain Objects!
        obj_in_keys = [o for o in data.get('keys', []) if o.get('xml', '-') == 'Объект']
        sub_objs = (data.get('attrs') or []) + obj_in_keys  # FIXME <<<<< how about dupplicates????

        obj_key = data.get('id-key', None)

        # WARNING: xml tag 'Табличная часть' and 'Запись' DON'T have 'id-key'!
        if obj_key and obj_key in parents:  # 0. Check cyclic scan recursion
            return exit_this_step()
        elif sub_objs:  # 1. add links first
            for k in sub_objs:
                # Warning: start scan recursion
                self.exp_add_node_to_xml(
                    root, k, obj_cache,
                    parents+([obj_key] if obj_key else []),
                    parent_is_object=parent_is_object,
                    subobj_mode=True)

        if not node_type:
            raise UserError(_("Error in code! Node without Type: %s\n") % data)
            # TODO disable raise errors
            return exit_this_step()

        # _logger.info(' >> ADD XML data: %s - %s', data.get('xml'), data.get('name'))
        # 2. start node
        this_attr = OrderedDict()
        this_is_object = node_type == 'Объект'
        if this_is_object:
            # added Object become Attribute
            if data.get('export_to_param', False):
                data['xml'] = 'ЗначениеПараметра'
                add_att(data, this_attr, 'export_to_param', 'Имя')
            else:
                data['xml'] = 'Свойство'
            # clear Object attributes
            attrs = data.pop('attrs', False)
            if obj_cache.get(obj_key):
                return exit_this_step()  # already added
            if obj_key is None:
                raise UserError(_("Object without Key! Node data: %s") % data)
            this_attr['Нпп'] = get_create_obj_id(obj_key, obj_cache)
            # # Перечисление is not Object
            # if node_type == 'Объект' and this_attr.get('Тип', '')[0:19] == 'ПеречислениеСсылка.':
            #     return exit_this_step()
            if not data.get('keys'):
                _logger.error('Object without keys! Node data: %s', data)
                # return needed for exclude situation of empty object:
                #   <Объект Нпп="4" Тип="СправочникСсылка.ЕдиницыИзмерения" ИмяПравила="ЕдиницыИзмерения" НеЗамещать="1"/>
                return exit_this_step()
        else:
            if subobj_mode:
                return exit_this_step()
            # Warning: do NOT(!) move this line before "if subobj_mode: return".
            attrs = data.pop('attrs', False)
            attr_log_err = node_type not in ['Запись']
            add_att(data, this_attr, 'name', 'Имя', attr_log_err)

        rule_id = data.get('rule_id')
        if rule_id:
            # TODO TODO: determine 'Тип' not in function 'export_object'
            # это нужно, чтобы иметь возможность управлять заданием типа поля
            # в функциях ПередПриЭкспорте. Т.к. в 1С есть поля множественных типов!
            # Чтобы для таких полей мы могли выгружать данные программно,
            # и программно задавать Тип
            this_attr['Тип'] = rule_id.destin_name
            this_attr['ИмяПравила'] = rule_id.code
        else:
            attr_log_err = node_type not in ['ТабличнаяЧасть', 'Запись']
            add_att(data, this_attr, 'tip', 'Тип', attr_log_err)

        # WARN: we have 'dont_refill' for Objects
        #   and we have 'dont_refill_field' for Attributes of Objects!
        if this_is_object:
            add_att(data, this_attr, 'dont_refill', 'НеЗамещать', False)
        else:
            add_att(data, this_attr, 'dont_refill_field', 'НеЗамещать', False)

        # Little test before start write xml
        if this_is_object and parent_is_object:
            _logger.error(
                'Error creating XML: Объект inside Объект!\n'
                'Rule[%s]: %s Current data: %s\n'
                'Current XML data: %s',
                rule_id.code, rule_id.display_name, data,
                ET.tostring(root, encoding="unicode", pretty_print=True))
            raise UserError(_(
                "Error creating XML:"
                " Объект inside Объект! Rule[%s]: %s Data: %s"
            ) % (rule_id.code, rule_id.display_name, data))
        elif not this_is_object and not parent_is_object:
            _logger.error(
                'Error creating XML: Свойство outside Объект!\n'
                'Rule[%s]: %s Current data: %s',
                rule_id.code, rule_id.display_name, data)
            raise UserError(_(
                "Error creating XML: Свойство outside Объект!"
                "Rule[%s]: %s Data: %s"
            ) % (rule_id.code, rule_id.display_name, data))
        # write node
        # _logger.info('XML %s %s', node_type, this_is_object and 'Нпп %s ' % this_attr['Нпп'] or '')
        newe = ET.SubElement(root, node_type, this_attr)
        # 3. add node value (if it Attribute)
        attr_val = data.get('val', None)
        if attr_val is not None:
            sub_e = ET.SubElement(newe, 'Значение')
            if isinstance(attr_val, bool):
                attr_val = 'true' if attr_val else 'false'
            elif isinstance(attr_val, (float, int)):
                # FIXME round float with two digits after decimal part
                attr_val = str(attr_val)
            if isinstance(attr_val, str):
                sub_e.text = attr_val
            elif isinstance(attr_val, fields.datetime):
                sub_e.text = attr_val.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                _logger.error('Incorrect data type: %s type: %s', attr_val, type(attr_val))
                sub_e.text = str(attr_val)
        # 4. add node keys (if it Object)
        if data.get('keys'):
            this_attr = OrderedDict()
            if obj_key is not None:
                this_attr['Нпп'] = get_create_obj_id(obj_key, obj_cache)
            if rule_id and rule_id.dont_create:
                this_attr['НеСоздаватьЕслиНеНайден'] = 'true'
            if rule_id and rule_id.dont_fill:
                this_attr['ПриПереносеОбъектаПоСсылкеУстанавливатьТолькоGIUD'] = 'true'
            links = ET.SubElement(newe, 'Ссылка', this_attr)
            for k in data['keys']:
                # warning: start add recursion
                self.exp_add_node_to_xml(
                    links, k, obj_cache, parents+[obj_key],
                    parent_is_object=this_is_object or parent_is_object)
        # 5. add node Attributes (if it Object)
        if attrs:
            for k in attrs:
                # warning: start add recursion
                self.exp_add_node_to_xml(
                    newe, k, obj_cache, parents+[obj_key],
                    parent_is_object=this_is_object or parent_is_object)
        return exit_this_step(newe)

    def add_rules_node(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        db_detect = ' '.join([
            get_param('mail.catchall.domain', ''),
            get_param('web.base.url', ''),
            get_param('database.uuid', '')])
        root = ET.Element(
            'ФайлОбмена',
            {
                "ВерсияФормата": "2.0",
                "ДатаВыгрузки": fields.Datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                # "НачалоПериодаВыгрузки": "2016-05-01T00:00:00",
                # "ОкончаниеПериодаВыгрузки": "2017-05-01T23:59:59",
                "ИмяКонфигурацииИсточника": self.source_name,  # Odoo
                "ИмяКонфигурацииПриемника": self.destin_name,  # БухгалтерияПредприятия
                "ИдПравилКонвертации": self.o1c_uuid,
                "Комментарий": 'Export from: %s' % db_detect,
            })

        rules_root = ET.SubElement(root, 'ПравилаОбмена')

        this_node = ET.SubElement(rules_root, 'ВерсияФормата')
        this_node.text = self.format_version
        this_node = ET.SubElement(rules_root, 'Ид')
        this_node.text = self.o1c_uuid  # UUID of Conversion rules
        this_node = ET.SubElement(rules_root, 'Наименование')
        this_node.text = self.name  # Example 'Conversion rules export Odoo to 1C'
        this_node = ET.SubElement(rules_root, 'ДатаВремяСоздания')
        this_node.text = fields.Datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        this_node = ET.SubElement(rules_root, 'Источник')
        this_node.text = self.source_name
        this_node = ET.SubElement(rules_root, 'Приемник')
        this_node.text = self.destin_name
        ET.SubElement(rules_root, 'Параметры')
        ET.SubElement(rules_root, 'Обработки')
        rules_root = ET.SubElement(rules_root, 'ПравилаКонвертацииОбъектов')
        for rule in self.rule_ids:
            if not rule.destin_name:
                continue
            this_rule = ET.SubElement(rules_root, 'Правило')
            this_node = ET.SubElement(this_rule, 'Код')
            this_node.text = rule.code
            if rule.after_import:
                this_node = ET.SubElement(this_rule, 'ПослеЗагрузки')
                this_node.text = rule.after_import
            if rule.sync_by_uuid:
                this_node = ET.SubElement(this_rule, 'СинхронизироватьПоИдентификатору')
                this_node.text = 'true'
            if rule.source_name:
                this_node = ET.SubElement(this_rule, 'Источник')
                this_node.text = rule.source_name
            if rule.fields_search:
                this_node = ET.SubElement(this_rule, 'ПродолжитьПоискПоПолямПоискаЕслиПоИдентификаторуНеНашли')
                this_node.text = 'true'
            if rule.dont_fill:
                this_node = ET.SubElement(this_rule, 'ПриПереносеОбъектаПоСсылкеУстанавливатьТолькоGIUD')
                this_node.text = 'true'
            if rule.dont_refill:
                this_node = ET.SubElement(this_rule, 'НеЗамещать')
                this_node.text = 'true'
            if rule.create_new_code:
                this_node = ET.SubElement(this_rule, 'ГенерироватьНовыйНомерИлиКодЕслиНеУказан')
                this_node.text = 'true'

            this_node = ET.SubElement(this_rule, 'Приемник')
            this_node.text = rule.destin_name
            # FIXME TODO add other keys
        return root

    @api.model
    def cron_export_data_to_1c(self, cron_mode=False):
        for cr_id in self.search([]):
            cr_id.export_data_to_1c(cron_mode=True)

    def get_xml_text(self, cron_mode):
        root = self.add_rules_node()
        exported = self.env['changed.record']
        # *********************************************************************
        obj_cache = {}  # Cache for Objects added in XML
        obj_cache_get = {}  # Cache for get Objects from DB
        # WARN: 'export_object' have OWN(!)recursion for getting Obj's from DB
        #   and 'exp_add_node_to_xml' have OWN(!) recursion for scan Obj's in Tree
        #   IT'S TWO(!) SEPARATE(!) NON-INTERSECTING(!) RECUSRIONS!
        # > That's why we use TWO variables:  obj_cache and obj_cache_get.
        # DON'T UNITE THEM INTO ONE VARIABLE!
        # *********************************************************************
        for er in self.export_rule_ids.filtered(lambda x: not x.disabled):
            if not er.model or er.model not in self.env:
                _logger.error('Cant export unexisted Model: %s', er.model)
                continue
            export_ids = self.env['changed.record'].sudo().search([
                ('model', '=', er.model),
                ('conv_id', '=', self.id)])
            if not export_ids:
                continue
            db_objs = self.env[er.model].sudo().search([('id', 'in', export_ids.mapped('res_id'))])
            if len(db_objs) > 0:
                exported += export_ids
                _logger.info(
                    'Export Rule[%s]: %s start export: %s ',
                    er.id, er.display_name, db_objs)
            for so_id in db_objs:
                rule_id = self.get_next_rule(er)
                item_data = self.export_object(so_id, rule_id, rule_id, root,
                                               obj_cache_get, used_subrule=True)
                # import pprint
                # pprint.pprint(item_data)
                self.exp_add_node_to_xml(root, item_data, obj_cache, [])
        if len(obj_cache) == 0:
            if cron_mode:
                return '', exported
            raise UserError(_(
                "Nothing to export.\n"
                "Mark objects to export first.\n\n"
                "Note: see marked in 'changed.record' model."))
        xml_text = ET.tostring(root, encoding='unicode', pretty_print=True)
        _logger.info(
            'Export data to 1C is finished. '
            'Exported: %s objects. '
            'Data length: %s', len(obj_cache),
            len(xml_text) if xml_text else 0)
        return xml_text, exported

    @staticmethod
    def get_xml_header():
        return b'\xEF\xBB\xBF<?xml version="1.0" encoding="UTF-8"?>\n'

    def export_data_to_1c(self, cron_mode=False):
        self.ensure_one()
        if not self.destin_name or not self.source_name or not self.o1c_uuid \
                or not self.format_version or not self.name:
            if cron_mode:
                return
            raise UserError(_('Fill fields: Destination, Source, UUID, Format version and name'))
        exchange_dir = False
        if cron_mode:
            exchange_dir = self.env['o1c.connector'].\
                get_create_exchange_dirs(cron_mode, 'export')
            if not exchange_dir:
                _logger.error(
                    'Can\'t export data to 1C. '
                    'Check exchange folder and settings in General Settings!')
                return
        _logger.info(
            'Export data to 1C. Cron mode: %s exchange_dir: %s',
            cron_mode, exchange_dir)
        xml_text, exported = self.get_xml_text(cron_mode)
        if not xml_text:
            # Remove objs from table 'changed.record'
            exported.unlink()  # TODO add load check

            # If len(exported) > 0 then it's not error.
            # Maybe all objects are skipped by rule conditions
            _logger.info('No data for export. Exported: %s objects', len(exported))
            return
        file_name = 'data_for_1c (%s).xml' % format_datetime(
            self.env, fields.datetime.now(), dt_format='YYYY-MM-dd HH_mm_ss')
        xml_header = self.get_xml_header()
        if cron_mode:
            file_path = path_join(exchange_dir, file_name)
            try:
                with open(file_path, 'wb+') as f:
                    f.write(xml_header)
                    f.write(str.encode(xml_text))
                # Remove objs from table 'changed.record'
                exported.unlink()
            except Exception as e:
                _logger.error('Write data to 1C error: %s. Path: %s', e, file_path)
            return
        save_conf = self.env['o1c.save.conf'].create({
            'file_name': file_name.replace('\\', '').replace('/', '').replace(':', ''),
            'xml_file': base64.b64encode(xml_header+str.encode(xml_text)),
        })
        # Remove objs from table 'changed.record'
        exported.unlink()

        return {
            'name': _('Export data to 1C'),
            'res_id': save_conf.id,
            'res_model': 'o1c.save.conf',
            'views': [(self.env.ref('o1c.save_conf_master_view_xml_done').id, 'form')],
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def export_object(self, obj, rule_id, parent_rule, xml_file, obj_cache_get,
                      used_subrule=None):
        """
        1. Export Model-Object:
        2. Export Folders
        3. Export Fields of model
        4. Export Fields of Folders
        ?. Export Object-Fields by link(recursion: make control Depth and Circles!)
        ?. Order Objects Tree (Нпп)
        add data to xml

        :param obj: Object for export
        :param rule_id: Rule for convert Object
        :param parent_rule: Parent Rule of Rule
        :param xml_file: link to XML writer
        :param obj_cache_get: cache of exported objects
        :param used_subrule: used subrules now?
        :return:
        """

        # def get_odoo_name_parth(rule_obj_name):
        #     if '.' not in rule_obj_name:
        #         return rule_obj_name # raise UserError('Incorrect Source name: %s\nRule ID: %s' % (rule_id.source_name, rule_id.id))
        #     return rule_obj_name.split('.')[1]

        def before_processing_field(data, export_with_rule, xml_file, obj_cache_get):
            """ Run code before processing field value

            Example 1 programming creationg field value:
                From ??
                to 'ДокументСсылка.КомплектацияНоменклатуры': Table 'Комплектующие' Поле 'Количество'
                > data['field_type'] = 'float'      # <--= REQUIRED !!!
                > data['field_val'] = obj.product_qty

            Example 2 programming creationg field value:
                From 'sale.order.line': 'product_id.bom_ids.bom_line_ids'
                to 'ДокументСсылка.КомплектацияНоменклатуры': Table 'Комплектующие'
                >    bom_id = obj.product_id and obj.product_id.bom_ids and obj.product_id.bom_ids.filtered(lambda b: b.type=='phantom')
                >    if bom_id:
                >        # print('bom_id : %s bom_line_ids: %s' % (bom_id, bom_id.bom_line_ids))
                >        data['field_val'] = bom_id.bom_line_ids
                >        data['field_type'] = 'one2many'

            Example 2 from one row into many rows:
                From 'account.invoice' -> 'account.invoice.line' ->
                    -> product -> Sale.Orders -> Delivery Orders ->
                    -> Stock Move Lines -> Lot name

                into 'ДокументСсылка.РеализацияТоваровИУслуг' -> Table 'Товары' ->
                    -> field 'НомераГТД'
                Task: in Account Invoice we have one row with some 'Product'
                    but in Delivery we have many(!) Lot's for this Product.
                    In РеализацияТоваровИУслуг.Товары we must(!) make
                    the same rows as we delivered Lot names.
                    Because as a Lot's names we use 'НомераГТД'.
                Example: AI INV/2020/0001 Product 'My product' Quantity 3 ->
                    Delivery WH/OUT/0001 -> Stock Move Lines:
                        'My product' Quantity 1 Lot's 'ГТД-001'
                        'My product' Quantity 1 Lot's 'ГТД-002'
                    in 1C we must get:
                    'ДокументСсылка.РеализацияТоваровИУслуг' -> Table 'Товары':
                        Prod: 'My product' Quantity: 1 НомерГТД: 'ГТД-001'
                        Prod: 'My product' Quantity: 1 НомерГТД: 'ГТД-002'

                > code:
                # **************************************************************
                # print('Get Product Lot number when export Account Invoice Line')
                #
                # def get_sml(obj, sp_ids, product_id, quantity):
                #     sml_ids = obj.env['stock.move.line']
                #     if not sp_ids:
                #         print('empty Stock Picking list')
                #         return sml_ids
                #     # Filter by non-cancelled SP
                #     sp_ids = sp_ids.filtered(lambda x: x.state not in ['cancel'])
                #     all_sml_ids = obj.env['stock.move.line'].search([
                #         ('picking_id', 'in', sp_ids.ids),
                #         ('product_id', '=', product_id.id),
                #     ])
                #     print('\t >> Stock Move lines: %s with Product: %s' % (all_sml_ids, product_id))
                #     accounted = 0
                #     for sml_id in all_sml_ids:
                #         if accounted >= quantity:
                #             break
                #         if not sml_id.lot_id or not sml_id.lot_id.name:
                #             print('\t\t\t Skip lot **>> sp_id: %s lot_name: %s', sml_id, sml_id.lot_id)
                #             continue
                #         accounted += sml_id.product_qty
                #         # Need to check: sml_id.product_qty != 0 ?
                #         sml_ids += sml_id
                #         print('\t\t\t SML: %s lot_name: %s product_qty: %s qty done: %s' % (sml_id.id, sml_id.lot_id.name, sml_id.product_qty, sml_id.qty_done))
                #     return sml_ids
                #
                # def add_field(data, ai_line_id, sml_ids):
                #
                #     def add_new_aml(data, ai_line_id, lot_id, need_to_export):
                #         coeff = ai_line_id.quantity / (1 if need_to_export == 0 else need_to_export)
                #         print('\t\t\t >>> add new AML. Coef: %s AML Qty: %s need_to_export: %s' % (coeff, ai_line_id.quantity, need_to_export))
                #         data['field_val'].append(ai_line_id.with_context(
                #             # STORE Lot in AML context
                #             export_lot=lot_id,                                   # <<<<<---=== THAT"s WHY WE USE THIS!
                #             export_quantity=need_to_export,                      # <<<--== Don't forget correct Qty
                #             export_price_total=ai_line_id.price_total / coeff,   # <<<--== Don't forget correct Summ
                #             export_price_tax=ai_line_id.price_tax / coeff        # <<<--== Don't forget correct Summ
                #         ))
                #
                #     exported_qty = 0
                #     for sml_id in sml_ids:
                #         if not sml_id.lot_id:
                #             print('SML %s without Lot' % sml_id)
                #             continue
                #         need_to_export = sml_id.qty_done  # ??? or sml_id.product_qty or sml_id.product_uom_qty
                #         print("\t\tAML: %s lot name: '%s' qty: %s qty done: %s " % (ai_line_id.id, sml_id.lot_id.name, ai_line_id.quantity, need_to_export))
                #         if need_to_export == 0:
                #             print('SML %s without qty' % sml_id)
                #             continue
                #         if exported_qty == ai_line_id.quantity:
                #             break
                #         elif exported_qty > ai_line_id.quantity:
                #             print('ERROR!!! Exported more then needed!!! AML qty %s exported: %s' % (ai_line_id.quantity, exported_qty))
                #             break
                #         exported_qty += min(need_to_export, ai_line_id.quantity - exported_qty)
                #         add_new_aml(data, ai_line_id, sml_id.lot_id, need_to_export)
                #     residue_qty = ai_line_id.quantity - exported_qty
                #     if residue_qty != 0 or ai_line_id.quantity == 0:
                #         print('Add residual AML qty: %s AML qty: %s exported qty: %s' % (residue_qty, ai_line_id.quantity, exported_qty))
                #         add_new_aml(data, ai_line_id, False, residue_qty)
                #     print(' Fin: ****>> sml Lots: ', sml_ids.mapped('lot_id').mapped('name'))
                #
                # if obj and obj.invoice_line_ids:
                #     data['field_val'] = []
                #     for ai_line_id in obj.invoice_line_ids:
                #         if not ai_line_id.product_id:
                #             data['field_val'].append(ai_line_id)
                #             continue
                #         print('1: Account Invoice line %s Product[%s]: %s quantity: %s' % (
                #             ai_line_id.id, ai_line_id.product_id.id, ai_line_id.product_id.display_name, ai_line_id.quantity))
                #         so_line_id = obj.env['sale.order.line'].search([('invoice_lines', 'in', [ai_line_id.id])])
                #         sp_ids = so_line_id.order_id.picking_ids
                #         print('2. SO line %s SO: %s Stock Pickings: %s' % (so_line_id, so_line_id.order_id, sp_ids))
                #         sml_ids = get_sml(ai_line_id, sp_ids, ai_line_id.product_id, ai_line_id.quantity)
                #         add_field(data, ai_line_id, sml_ids)
                # print(' Success export.')

            Example 3 From Odoo o2m field into 1C Selection field:
                From 'account.invoice.line': 'account_line_tax_ids'
                to 'ДокументСсылка.РеализацияТоваровИУслуг': Table 'Товары': Колонка: 'СтавкаНДС'
                     :type Переисление.СтавкиНДС
                Mapping by Tax ID
                > if obj and obj.invoice_line_tax_ids.filtered(lambda x: x.id == 1):
                >     export_attr['val'] = 'НДС20'

            Example 4 From Odoo into 1C DISCARD EXPORT field if some conditions:
                From 'sale.order.line': 'tax_ids'
                to 'ДокументСсылка.РеализацияТоваровИУслуг': Table 'Товары': Колонка: 'СтавкаНДС'
                Do NOT EXPORT Taxes if sale.order->Company not a main Company
                > if obj.sale_id.fiscal_position_id.id == 5 or obj.sale_id.company_id.id != 1:
                >     del data['export_attr']  # <<<<<---=== Just remove 'export_attr'
                >     # export_attr.clear()  # <<<<<---=== or clear 'export_attr' like this

            :param data: dictionary
                data = {
                    'obj':
                    'export_attr':
                    'rl':
                    'is_folder':
                    'field_type': not required
                    'field_val': can be empty
                }

            :param export_with_rule:
            :param xml_file:
            :param obj_cache_get:
            :return:
            """
            rl = data['rl']
            if not rl.before_processing:
                return
            # Make separate params for ease and simply program code of processing
            # flake8: noqa: F841
            # pylint: disable=unused-variable
            export_attr = data['export_attr']
            obj = data['obj']
            try:
                # bandit: B102
                exec(rl.before_processing)  # nosec
            except Exception as e:
                _logger.error(
                    'Cant processing Field Rule[%s][code %s]: %s.\n'
                    'Before processing:\n%s\n'
                    ' >>> Error: %s\n'
                    '\tobj: %s\n'
                    '\tdata: %s', rl.id, rl.name, rl.code,
                    rl.before_processing, e, obj, data)

        def before_export_field(export_attr, obj, field_val, rl, odoo_name,
                                vid_folder_id, export_with_rule, xml_file,
                                obj_cache_get):
            """ Run python Code Before export Field

                Warning: this code work even(!) if field is not filled
                Warning: you to use only(!) 'export_attr' param. You can't change Object 'export_data'.

                Example to use: Object is 'sale.order.line' odoo_name is 'tax_id'
                 >   if obj.name == 'Tax 18%':
                 >       export_attr['val'] = 'НДС18'
                 >   else:
                 >       export_attr['val'] = 'БезНДС'

                Example 2 to use:
                Object is 'res.partner' odoo_name is 'is_company'
                Destination type is 'ПеречислениеСсылка.ЮридическоеФизическоеЛицо'
                 >   if obj.is_company:
                 >       export_attr['val'] = 'ЮридическоеЛицо'
                 >   else:
                 >       export_attr['val'] = 'ФизическоеЛицо'

                Example 3 to use export_with_rule:
                Object is 'sale.order'.'order_line'
                Destination type is 'ДокументСсылка.КомплектацияНоменклатуры'
                 >   if obj and obj.product_id and obj.product_id.bom_ids[0].type == 'kit':
                 >      for o in export_attr['attrs']:
                 >          if o['xml'] == 'Объект':
                 >              export_with_rule(xml_file, export_attr['attrs'], obj_cache_get)
                 >   export_attr['val'] = None

            :param export_attr:
            :param obj:
            :param rl:
            :param odoo_name:
            :param vid_folder_id:
            :return:
            """
            if not rl.before_export:
                return
            try:
                # bandit: B102
                exec(rl.before_export)  # nosec
            except Exception as e:
                _logger.error('Cant execute Rule(id %s)[code %s]: %s.\nError: %s', rl, rl.code, rl.before_export, e)

        def before_processing_obj(data, export_with_rule, xml_file, obj_cache_get):
            """ Run code before processing Object value

            Example 1:
                From 'sale.order.line'
                to 'ДокументСсылка.КомплектацияНоменклатуры'
                Check: "Product is a Kit?" and disable export if Not.
                 >   if obj.product_id and  obj.product_id.bom_ids \
                 >       and obj.product_id.bom_ids.filtered(lambda b: b.type == 'phantom'):
                 >         pass
                 >   else:
                 >         export_data.clear()

            :param data: dictionary
                data = {
                    'obj':
                    'export_data':
                    'rl':
                }
            :param export_with_rule: - self.exp_add_node_to_xml
            :param xml_file:
            :param obj_cache_get:
            :return:
            """
            rl = data['rl']
            if not rl.before_processing:
                return
            # Make separate params for ease and simply program code of processing
            # flake8: noqa: F841
            # pylint: disable=unused-variable
            export_data = data['export_data']
            obj = data['obj']
            try:
                # bandit: B102
                exec(rl.before_processing)  # nosec
            except Exception as e:
                _logger.error('Cant processing Obj Rule(id %s)[code %s]: %s.\nError: %s', rl, rl.code, rl.before_processing, e)

        def before_export_obj(export_data, obj, rule_id):
            """ Run python Code Before export Object

            Warning: this code work only(!) if Object is filled
            Warning: you can use only(!) 'export_data' param in before_export code.

            Example 1 to use: Destination field is 'СправочникСсылка.Организации'
             >   export_data['keys'] = {
             >       'xml': 'Свойство',
             >       'name': 'ИНН',
             >       'tip': 'Строка',
             >       'val': '123456789001',
             >   }

            Example 2 to use: Object is 'sale.order.line' odoo_name is 'tax_id'
            Destination type is 'ПеречислениеСсылка.СтавкиНДС'
            >    if obj.name == 'Tax 18%':
            >        val = 'НДС18'
            >    else:
            >        val = 'БезНДС'
            >    export_data = {
            >        'xml': 'Свойство',
            >        'name': obj_rule.destin_name,
            >        'tip': rule_id.destin_name,
            >        'val': val
            >    }

            Example 3: Disable export Object
            >    export_data.clear()

            Example 5: when marked one Obj-t export other Object.
            Export bankStatementLine BSL when acc.part.reconcile marked.
            acc_part_reconcile have fields debit_move_id and credit_move_id
            with type account.move.line.
            Then AML have filed statement_id with type bank.statement.line.
            We must create SubRule for get data: APR.xxbit_move_id.statement_id

            For object APR we use code below:
            >   # Example for change Object data to Object with other type!
            >   # export_data['attrs'] contain statement data. In this way
            >   # we change Parent Object APR into his field object BSL
            > 	export_data.update(export_data.pop('attrs')[0])
            >
            >   # We must also change field xml type 'Свойство' into 'Объект'
            >   export_data['xml'] = 'Объект'

            :return:
            """
            if not rule_id.before_export:
                return
            try:
                # bandit: B102
                exec(rule_id.before_export)  # nosec
            except Exception as e:
                _logger.error('Cant execute Rule(id %s)[code %s]: %s.\n'
                              'Error: %s', rule_id, rule_id.code,
                              rule_id.before_export, e)

        vid_folder_id = self.env.ref('o1c.data_o1c_vid_folder').id
        try:
            # Export NOT a Odoo Model as Object
            #    isinstance(obj, (dict, str, int, float, list, set)):
            # For example: Object created in 'before_processing_field'
            #  string -> 1C Object
            #  int    -> 1C Object
            #  dict   -> 1C Object
            #  ...
            model_name = obj._name
        except:
            model_name = 'PROGRAMMATICALLY.GENERATED.OBJECT'
        if not rule_id or rule_id.disabled:
            if not rule_id:
                _logger.error('Conversion Rule dont set.'
                              ' Parent Rule: %s Object name: %s %s',
                              parent_rule, model_name)
            return

        # 1. Export Model-Object:
        # <Объект Нпп="56" Тип="СправочникСсылка.СтатьиЗатрат" ИмяПравила="СтатьиЗатрат">
        if rule_id._name == 'conv.rule.line':
            # it's Folder
            rule_dom_search = [
                ('disabled', '=', False),
                ('parent_rule_id', '=', rule_id.id)]
            export_data = {
                'xml': 'Запись',
                'attrs': [],
            }
        else:
            rule_dom_search = [
                ('disabled', '=', False),
                ('owner_id', '=', rule_id.id),
                ('parent_rule_id', '=', False)]
            if model_name == 'PROGRAMMATICALLY.GENERATED.OBJECT':
                # Warning: we convert Object into String! and use at as a Object Key!
                id_key = 'r: %s o: %s id: %s' % (rule_id.id, model_name, str(obj))
            else:
                id_key = 'r: %s o: %s id: %s' % (rule_id.id, model_name, obj.id)
            # Check cyclic recursion:
            already_export_data = obj_cache_get.get(id_key)
            if already_export_data:
                logging.debug('Cyclic recursion detected. Key %s Obj: %s data:\n\t %s', id_key, obj, already_export_data)
                # ************************************************************
                # Warning: dict make a copy of dictionary already_export_data
                # but already_export_data contain a values with other dict-ry!
                # So we get 'recursion links inside result data'.
                # 'Recursion links inside result data' is NOT a problem
                #   for current algorithm.
                #     You can rewrite 'dict' func into deepcopy,
                #     but it's not needed.
                #
                # Warning 2: obj_cache_get get data from export_data,
                # but after export objects by some rule, the export_data
                # is removed in func. exp_add_node_to_xml.
                # So in this dict we get only 'keys' on Object.
                # But this is not a problem, because Object and they fields
                # are already exported
                update_export_data = dict(already_export_data)
                update_export_data['name'] = parent_rule.destin_name
                # ************************************************************
                return update_export_data
            # New container for Object data
            export_data = {
                'xml': 'Объект',
                'id-key': id_key,
                # Use 'parent_rule.destin_name'! Don't use 'rule_id.destin_name'.
                # Because in node <Объект Имя="ИмяРеквизита"> tag "Имя" will become contains
                # incorrect value. Example <Объект Имя="ДокументСсылка.КомплектацияНоменклатуры">
                'name': parent_rule.destin_name,
                'rule_id': rule_id,
                'keys': [],
                'attrs': [],
            }
            if rule_id.dont_refill:
                # '1' or 'true', but '1' is shorter
                # and with '1' we don't have problems when lang in 1C
                export_data['dont_refill'] = '1'
            obj_cache_get[id_key] = export_data

        this_obj_data = {
            'obj': obj,
            'export_data': export_data,
            'rl': rule_id,
        }
        # ********************************************************************
        # WARNING: 'used_subrule' needed for protect
        #   run code 'before_processing' twice!
        #    Because 'before_processing' used in 'before_processing_field'
        #     AND(!) in 'before_processing_obj'!
        #   Be careful for not execute this rule TWICE!
        #   Example: you have field with type ТабличнаяЧасть as o2m.
        #       Code 'before_processing' can execute before export o2m field
        #       AND(!) executed on each row! of o2m list! This is incorrect!
        #   That is why we use 'used_subrule' marker.
        if used_subrule is None:
            used_subrule = parent_rule != rule_id
        # ********************************************************************
        if used_subrule:
            before_processing_obj(
                this_obj_data, self.exp_add_node_to_xml, xml_file, obj_cache_get)
            # Update Object after processing
            obj = this_obj_data.get('obj')
            export_data = this_obj_data.get('export_data')
        else:
            _logger.debug('Skipped run before_processing_obj twice. '
                          'Rule: %s Parent Rule: %s', rule_id, parent_rule)

        # Obj and export_data can be cleared in 'before_processing' procedure
        if not this_obj_data.get('obj') or not this_obj_data.get('export_data'):
            return

        if this_obj_data['export_data'].get('xml') == 'Объект':
            # 1.2. Create "Ссылка"
            # 1.2.1. get UUID
            o1c_uuid = self.env['o1c.uuid']. \
                get_create_obj_uuid(obj, model_name)
            if o1c_uuid:
                export_data['keys'].append({
                    'xml': 'Свойство',
                    'name': '{УникальныйИдентификатор}',
                    'tip': 'Строка',
                    'val': o1c_uuid,
                })

        # TODO rewrite 'search' to get rule_field_ids. For what this 'search' needed?
        attrs_rules = self.env['conv.rule.line'].search(rule_dom_search)
        for rl in attrs_rules:
            export_attr = {
                'name': rl.destin_name,
                'val': None
            }
            if rl.is_group:
                export_attr['xml'] = 'ТабличнаяЧасть'
            elif rl.export_to_param:
                export_attr['xml'] = 'ЗначениеПараметра'
                export_attr['export_to_param'] = rl.export_to_param
            else:
                export_attr['xml'] = 'Свойство'
            if rl.destin_tip_id:
                export_attr['tip'] = rl.destin_tip_id
            if rl.dont_refill_field:
                # '1' or 'true', but '1' is shorter
                # and with '1' we don't have problems when lang in 1C
                export_attr['dont_refill_field'] = '1'
            this_data = {
                'obj': obj,
                'export_attr': export_attr,
                'rl': rl,
                'is_folder': rl.source_vid_id.id == vid_folder_id or rl.is_group,
            }
            if not rl.source_name:
                if not rl.destin_name and not rl.export_to_param:
                    _logger.error(
                        'Rule[%s] without destination name. '
                        'Rule code: %s', rl.id, rl.code)
                    continue
                if not rl.before_processing and not rl.before_export:
                    _logger.error(
                        'Rule[%s] without source name. '
                        'Destination name: %s', rl.id, rl.destin_name)
                    continue
                odoo_name = None
                this_data['field_val'] = None
            else:
                odoo_name, field_name = self.env['o1c.connector'].\
                    from_1c_to_odoo_name(rl.source_name)  # ? get_odoo_name_parth(rl.source_name)
                if not hasattr(obj, odoo_name):
                    raise UserError(_(
                        "ERROR: field: '%s' not in Model: '%s' "
                        "fields. Rule: %s") % (odoo_name, model_name, rl))
                    return
                this_data.update({
                    'field_type': obj._fields[odoo_name].type,
                    'field_val': obj[odoo_name],
                })
            # Used code in this_data['rl'].before_processing
            before_processing_field(
                this_data, self.exp_add_node_to_xml, xml_file, obj_cache_get)

            # ****************************************************
            # Fill this_data['export_attr'] with converted data
            self.get_attr_data(this_data, xml_file, obj_cache_get)
            # ****************************************************

            # USed code in before_export
            before_export_field(
                export_attr, obj, this_data['field_val'], rl,
                odoo_name, vid_folder_id, self.exp_add_node_to_xml,
                xml_file, obj_cache_get)
            if export_attr:
                # TODO use OrderedDict !!!
                export_data['keys' if rl.search_field else 'attrs'].\
                    append(export_attr)

        before_export_obj(export_data, obj, rule_id)

        # ________________________________________________________________________________________________________________________________
        # TODO remove code:
        # auto convert Object to different types
        # convert m2m->Свойство or o2m->Перечисление
        if export_data and export_data['xml'] != 'Свойство' and rule_id.destin_name and rule_id.destin_name[0:19] == 'ПеречислениеСсылка.':
            # Перечисление is not Object. Change data to Attribute.
            # Instead use this, you can use your 'Before export Object' algorithm like:
            # >    if obj.name == 'Tax 18%':
            # >        val = 'НДС18'
            # >    else:
            # >        val = 'БезНДС'
            # >    export_data = {
            # >        'xml': 'Свойство',
            # >        'name': parent_rule.destin_name,
            # >        'tip': rule_id.destin_name,
            # >        'val': val
            # >    }
            attr = export_data.get('val')
            if not attr:
                attr = export_data.get('attrs')
                attr = attr and attr[0] and attr[0].get('val') or None
            if not attr:
                attr = export_data.get('keys')
                attr = attr and attr[0] and attr[0].get('val') or None
            export_data = {
                'xml': 'Свойство',
                'name': parent_rule.destin_name,
                'tip': rule_id.destin_name,
                'val': attr
            }
            _logger.debug('Warning: auto-convert Object: %s to %s value: %s. Please use "Before Export algorithms"!',
                          rule_id.source_name, rule_id.destin_name, export_data.get('val'))
        # ________________________________________________________________________________________________________________________________
        return export_data

    def get_next_rule(self, obj_rule):
        # If Conversion Rule installed in Current Rule then Use them
        if hasattr(obj_rule, 'conv_rule_id'):
            return obj_rule.conv_rule_id or obj_rule
        return obj_rule

    def get_attr_data(self, this_data, xml_file, obj_cache_get):
        """
            Need to return dictionary with similar structure for creation XML:
            Example:
            <Свойство Имя="ДокументОснование" Тип="ДокументСсылка.АвансовыйОтчет">
              <Ссылка Нпп="1">
                    <Свойство Имя="{УникальныйИдентификатор}" Тип="Строка">
                            <Значение>a9e8b422-1cda-11e6-a31d-14dae9b19a48</Значение>
                    </Свойство>
                    <Свойство Имя="Дата" Тип="Дата">
                            <Значение>2016-03-09T00:00:00</Значение>
                    </Свойство>
                    <Свойство Имя="Номер" Тип="Строка">
                            <Значение>КП00-000001</Значение>
                    </Свойство>
              </Ссылка>
            </Свойство>

            Example 2:
            <Свойство Имя="ИННКонтрагентаДоИзменения" Тип="Строка">
                    <Пусто/>
            </Свойство>

        :param this_data:
        :param xml_file:
        :param obj_cache_get:
        :return:
        """
        rl = this_data['rl']
        # If 'export_attr' is cleared(in before_processing_field proc) then we don't export this field
        if not this_data.get('export_attr'):
            # cancel export this field
            return
        elif this_data['export_attr'].get('val', '-') is not None:
            # Skip if value already determined in
            #  before_processing_field procedure
            return
        elif 'field_type' not in this_data:
            # FIXME Tip MUST DETERMINE BY "SOURCE Тип", instead "Internal Тип"!!!!! <<<<<
            # TODO try to determine field type by rl.source_tip_id.  <<----== !!!!
            # TODO try to determine field type by value type. And this error will be not actually.
            # TODO try to determine field type by destination field type: Строка, Справочник, Документ,...
            _logger.error(
                'ERROR: can\'t determine value type! Value can\'t be exported!\n'
                ' 1. Programming determine value, but value type is not determined.\n'
                ' 2. And in Rule[%s] %s source field not determined!'
                ' PLEASE:\n'
                ' add in before_processing_field code:\n'
                '\tdata[\'field_type\'] = field_value_type  # Example one2many, integer, char,...'
                ' OR\n'
                '\tadd Source Field in Rule!\n >> Data: %s', rl, rl.name, this_data)
            return

        export_attr = this_data['export_attr']
        field_val = this_data['field_val']
        field_type = this_data['field_type']

        # _logger.debug('Export field type: %s val: %s rule: %s' % (field_type, field_val, rl))
        if field_type == 'many2one':
            rule_id = self.get_next_rule(rl)
            if rule_id:
                export_attr.update(
                    self.export_object(
                        field_val, rule_id, rl, xml_file, obj_cache_get) or {})
                return
            else:
                _logger.error('Cant convert field type: %s val: %s rule: %s' % (field_type, field_val, rl))
                # TODO what to do??? Skip???
                o1c_f_val = field_val.name_get()[0][1]  # FIXME TODO try to get 'obj.name' obj._name_field
        elif field_type == 'many2many' or field_type == 'one2many':
            o1c_f_val = []
            is_folder = this_data['is_folder']
            rule_id = self.get_next_rule(rl)
            # FIXME ошибка когда выгрузка например из тегов Контакта в "Родителя" Контрагента
            # в таком случае в XML-е получается "Свойство" внутри "Свойства"!
            # И после загрузки в 1С Контрагент превращается в группу! Это нужно исправить!
            # Исправить, НО ПРИ ЭТОМ НЕ СЛОМАТЬ выгрузку "Таблица-в-Таблицу", "Таблица-в-ПолеТипаЧар",...
            if field_val is None or field_val is False:
                _logger.error(
                    'Incorrect value: %s of field type: %s '
                    'Rule[%s]: %s. Data:\n%s', field_val, field_type,
                    rule_id, rule_id.name, this_data)
                return
            for this_row in field_val:
                attr = self.export_object(
                    this_row, rule_id, rl, xml_file, obj_cache_get)
                if not is_folder:
                    # FIXME if m2m or o2m have many rows then HOW TO export them to ONE(!) field!?
                    if len(field_val) > 1:
                        _logger.error('Export field type: %s contain MANY(!) rows: %s '
                                      'into ONE(!) field: %s type: %s vid: %s val: %s rule: %s' %
                                      (field_type, len(field_val),
                                       rl.destin_name, rl.destin_tip_id, rl.destin_vid_id.name,
                                       this_row, rule_id))
                    # Warning: change type 'ТабличнаяЧасть' to type 'Свойство' and change data
                    export_attr.update(attr or {})
                    this_data['field_val'] = this_row  # FIXME: WARNING: only FIRST row used!
                    return
                if attr:
                    o1c_f_val.append(attr)
            if not rl.destin_name:
                if rl.before_export and 'export_with_rule' in rl.before_export:
                    # It's okay, because we use 'export_with_rule' in source code
                    # TODO write debug log message
                    pass
                else:
                    _logger.error('Folder without destination name! Rule: %s', rl)
            this_data['field_val'] = field_val
            if not o1c_f_val:
                return
            export_attr.update({
                # 'name': rl.destin_name or None,
                'attrs': o1c_f_val
            })
            return
        elif field_type in ['bool', 'boolean']:
            o1c_f_val = field_val
        else:
            if isinstance(field_val, bool) and not field_val:
                # non-boolead type field with bool type value
                o1c_f_val = None
            else:
                o1c_f_val = field_val
        if not rl.destin_name:
            _logger.error('Field without destination name! Rule[%s]: %s', rl.id, rl.source_name)

        export_attr.update({
            # 'name': rl.destin_name or None,
            # 'tip': rl.destin_tip_id or None,
            'val': o1c_f_val
        })
        this_data['field_val'] = field_val
        return

    def upload_f(self, xml_text=None, filename=None):
        self.ensure_one()

        if not xml_text:
            if not filename:
                return  # FIXME TODO create wizard
            try:
                with open(filename, 'r') as f:
                    xml_text = f.read()
            except Exception as e:
                _logger.error('Error read from file: %s\nError: %s', filename, e)
                return
        try:
            exchange_rules = ET.fromstring(xml_text)
        except Exception as e:
            _logger.error('Error parse XML: %s', e)
            return

        r_level = 0
        load_later = {}
        self.rule_ids.write({'disabled': True})
        self.export_rule_ids.write({'disabled': True})
        self.recurse_load_rules_data(exchange_rules, r_level, load_later, filename=filename)

        # load links to rules
        for rule_name, rules in load_later.items():
            for rule_line_code, rule_link in rules.items():
                owner_id = self.env['conv.rule'].search([('code', '=', rule_name), ('conv_id', '=', self.id)])
                if not owner_id or len(owner_id) > 1:
                    _logger.error('XML structure error. Rule: %s. Code: %s Conversion: %s', owner_id, rule_name, self.id)
                    continue
                rule_line_id = self.env['conv.rule.line'].search([('code', '=', rule_line_code), ('owner_id', '=', owner_id.id), ('conv_id', '=', self.id)])
                rule_id = self.env['conv.rule'].search([('code', '=', rule_link), ('conv_id', '=', self.id)])
                if not rule_id:
                    _logger.error('XML structure error. Rule name: %s. Owner: %s Conversion: %s', rule_name, owner_id, self.id)
                    continue
                rule_line_id.write({
                    'conv_rule_id': rule_id.id
                })

    def recurse_load_rules_data(self, tree_node, r_level, load_later,
                                parent_node='', rule_data=None, rule_line_data=None, rule_group_data=None,
                                filename=False):
        self.ensure_one()

        def read_conversion_data(conv_data, node_data):
            add_to_data = {}
            if node_data.tag == 'ВерсияФормата':
                add_to_data['format_version'] = node_data.text
            elif node_data.tag == 'Ид':
                # TODO add check "is equile to this.o1c_uuid and warning if not equil"
                add_to_data['o1c_uuid'] = node_data.text.strip()
            elif node_data.tag == 'Наименование':
                add_to_data['name'] = node_data.text
            elif node_data.tag == 'Источник':
                add_to_data['source_name'] = node_data.text
            elif node_data.tag == 'Приемник':
                add_to_data['destin_name'] = node_data.text

            for k, v in add_to_data.items():
                if k in conv_data.keys():
                    raise UserError(_(
                        "Can't update Rules key: %s "
                        "old data: %s "
                        "new data: %s") % (k, rule_data[k], v))
                else:
                    conv_data[k] = v

        def read_rule_data(rule_data, node_data):
            add_to_data = {}
            if not node_data.text:
                return
            if node_data.tag == 'Код':
                if node_data.text:
                    add_to_data['code'] = node_data.text
            elif node_data.tag == 'Наименование':
                if node_data.text:
                    add_to_data['name'] = node_data.text
            elif node_data.tag == 'Источник':
                add_to_data['source_name'] = node_data.text
            elif node_data.tag == 'Приемник':
                add_to_data['destin_name'] = node_data.text
            elif node_data.tag == 'СинхронизироватьПоИдентификатору':
                add_to_data['sync_by_uuid'] = node_data.text == 'true'
            elif node_data.tag == 'Порядок':
                # TODO из-за того что в 1С правила лежат в разніх группах: Справочники и Документы
                # то они не имеют общей сквозной нумерации\порядок. У них порядок задается внутри группы
                # а в оду у нас сплошной список и из-за этого порядок не корректный.
                try:
                    if node_data.text:
                        add_to_data['order'] = int(node_data.text)
                except Exception as e:
                    _logger.error('Cant parse Order: %s. Error: %s',
                                  node_data.text, e)
            elif node_data.tag == 'КодПравилаКонвертации':
                rule_name = node_data.text and node_data.text.strip()
                if rule_name:
                    rule_id = self.env['conv.rule'].search([('code', '=', rule_name), ('conv_id', '=', self.id)], limit=1)
                    if not rule_id:
                        # Warning: this code used only for 'ПравилаВыгрузкиДанных'! So in this moment we already uploaded ALL! Rules.
                        raise UserError(_(
                            "Can't find Rule with Code: %s") % rule_name)
                    add_to_data['conv_rule_id'] = rule_id.id
            elif node_data.tag == 'ПослеЗагрузки':
                add_to_data['after_import'] = node_data.text
            elif node_data.tag == 'ПродолжитьПоискПоПолямПоискаЕслиПоИдентификаторуНеНашли':
                add_to_data['fields_search'] = node_data.text == 'true'
            elif node_data.tag == 'НеСоздаватьЕслиНеНайден':
                add_to_data['dont_create'] = node_data.text == 'true'
            elif node_data.tag == 'НеЗамещать':
                add_to_data['dont_refill'] = node_data.text == 'true'
            elif node_data.tag == 'ГенерироватьНовыйНомерИлиКодЕслиНеУказан':
                add_to_data['create_new_code'] = node_data.text == 'true'
            elif node_data.tag == 'ПриПереносеОбъектаПоСсылкеУстанавливатьТолькоGIUD':
                add_to_data['dont_fill'] = node_data.text == 'true'
            elif node_data.tag == 'Группа' or node_data.tag == 'Свойство' or node_data.tag == 'Свойства':
                pass
            elif node_data.tag == 'ОбъектВыборки':
                # Example: 'СправочникСсылка.saleOrder'
                add_to_data['model'] = self.env['o1c.connector'].from_1c_to_odoo_name(node_data.text)[0]
            elif node_data.tag == 'ПередВыгрузкой':
                add_to_data['before_processing'] = node_data.text
            elif node_data.tag == 'ПриВыгрузке':
                add_to_data['before_export'] = node_data.text
            else:
                # Example: СпособОтбораДанных,
                _logger.debug('Unknown tag: %s ', node_data.tag)

            for k, v in add_to_data.items():
                if k in rule_data.keys():
                    raise UserError(_(
                        "Can't update Rule key: %s "
                        "old data: %s "
                        "new data: %s") % (k, rule_data[k], v))
                else:
                    rule_data[k] = v

        def read_rule_line_data(rule_line_data, node_data, load_later, rule_data):
            add_to_data = {}
            if node_data.tag == 'Код':
                if node_data.text:
                    add_to_data['code'] = node_data.text
            elif node_data.tag == 'Наименование':
                if node_data.text:
                    add_to_data['name'] = node_data.text
            elif node_data.tag == 'Источник':
                if node_data.attrib.get('Имя'):
                    add_to_data['source_name'] = node_data.attrib['Имя']
                if node_data.attrib.get('Вид'):
                    vid_id = self.env['o1c.vid'].search([('name', '=', node_data.attrib['Вид'])], limit=1)
                    if vid_id:
                        add_to_data['source_vid_id'] = vid_id.id
                if node_data.attrib.get('Тип'):
                    add_to_data['source_tip_id'] = node_data.attrib['Тип']
            elif node_data.tag == 'Приемник':
                if node_data.attrib.get('Имя'):
                    add_to_data['destin_name'] = node_data.attrib['Имя']
                if node_data.attrib.get('Вид'):
                    vid_id = self.env['o1c.vid'].search([('name', '=', node_data.attrib['Вид'])], limit=1)
                    if vid_id:
                        add_to_data['destin_vid_id'] = vid_id.id
                if node_data.attrib.get('Тип'):
                    add_to_data['destin_tip_id'] = node_data.attrib['Тип']
            elif node_data.tag == 'КодПравилаКонвертации':
                rule_name = node_data.text and node_data.text.strip()
                if rule_name:
                    rule_id = self.env['conv.rule'].search([('code', '=', rule_name), ('conv_id', '=', self.id)], limit=1)
                    if rule_id:
                        add_to_data['conv_rule_id'] = rule_id.id
                    else:
                        # Some rules can loaded later then links to them. That is why we needed 'load_later'
                        if not rule_line_data.get('code') or not rule_data.get('code'):
                            _logger.error('Cant find Rule with Code: %s. '
                                          'Rule line[%s] and/or Rule[%s] without code! ',
                                          rule_name, rule_line_data.get('code'), rule_data.get('code'))
                        else:
                            _logger.info(
                                'Load RuleLine but Rule[code: %s] not exist.'
                                ' This RuleLine will be loaded later.', rule_name)
                            if not load_later.get(rule_data['code']):
                                load_later[rule_data['code']] = {}
                            load_later[rule_data['code']].update({rule_line_data['code']: rule_name})
            elif node_data.tag == 'Порядок':
                # TODO из-за того что в 1С правила лежат в разных группах: Справочники и Документы
                # то они не имеют общей сквозной нумерации\порядок.
                # У них порядок задается внутри группы,
                # а в оду у нас сплошной список и из-за этого порядок не корректный.
                # Нужно сделать конвертацию "порядка 1С" в "порядок оду"
                if node_data.text:
                    try:
                        add_to_data['order'] = int(node_data.text)
                    except Exception as e:
                        _logger.error('Cant parse Order: %s. Error: %s',
                                      node_data.text, e)
            elif node_data.tag == 'ПередВыгрузкой' or node_data.tag == 'ПередОбработкойВыгрузки':
                add_to_data['before_processing'] = node_data.text
            elif node_data.tag == 'ПриВыгрузке':
                add_to_data['before_export'] = node_data.text
            elif node_data.tag == 'НеЗамещать':
                add_to_data['dont_refill_field'] = node_data.text == 'true'
            elif node_data.tag == 'ИмяПараметраДляПередачи':
                add_to_data['export_to_param'] = node_data.text

            for k, v in add_to_data.items():
                if k in rule_line_data.keys():
                    raise UserError(_(
                        "Can't update Rule line key: %s "
                        "old data: %s "
                        "new data: %s") % (k, rule_line_data[k], v))
                else:
                    rule_line_data[k] = v

        r_level += 1
        conv_data = None
        if tree_node.tag == 'ПравилаОбмена' and r_level == 1:
            parent_node = tree_node.tag
            conv_data = {}   # start getting data
        elif tree_node.tag == 'Правило':
            # start getting data
            rule_data = {
                'disabled': tree_node.attrib.get('Отключить', '-') == 'true',
            }
        elif tree_node.tag == 'Свойство':
            if rule_data is not None:
                rule_line_data = {}   # start getting data
                if tree_node.attrib.get('Отключить', '-') == 'true':
                    rule_line_data['disabled'] = True
                if tree_node.attrib.get('Поиск', '-') == 'true':
                    rule_line_data['search_field'] = True
        elif tree_node.tag == 'Группа':
            if rule_data is not None:
                rule_group_data = {'is_group': True, 'group_child': []}   # start getting data
                if tree_node.attrib.get('Отключить', '-') == 'true':
                    rule_group_data['disabled'] = True
        elif tree_node.tag == 'ПравилаВыгрузкиДанных' and r_level == 2:
            parent_node = tree_node.tag
        elif tree_node.tag == 'ПравилаКонвертацииОбъектов' and r_level == 2:
            parent_node = tree_node.tag

        allowed_items = ['ПравилаОбмена', 'ПравилаКонвертацииОбъектов',
                         'Правило', 'Свойства', 'Свойство', 'Группа',
                         'ПравилаВыгрузкиДанных']
        if tree_node.tag not in allowed_items:
            return
        for child in tree_node.iterchildren():
            if rule_line_data is not None:
                read_rule_line_data(rule_line_data, child, load_later, rule_data)
            elif rule_group_data is not None:
                read_rule_line_data(rule_group_data, child, load_later, rule_data)
            elif rule_data is not None:
                read_rule_data(rule_data, child)
            elif conv_data is not None:
                read_conversion_data(conv_data, child)

            self.recurse_load_rules_data(child, r_level, load_later, parent_node, rule_data, rule_line_data, rule_group_data)

        if tree_node.tag == 'Свойство':
            if not rule_line_data:
                return
            if rule_group_data:
                rule_group_data['group_child'].append((0, 0, rule_line_data))
            else:
                rule_data.update({
                    'rule_line_ids': rule_data.get('rule_line_ids', []) + [(0, 0, rule_line_data)]
                })
        elif tree_node.tag == 'Группа':
            if not rule_group_data:
                return
            group_child = rule_group_data.pop('group_child')
            new_group_id = self.env['conv.rule.line'].create(rule_group_data)
            for c in group_child:
                c[2].update({'parent_rule_id': new_group_id.id})
            rule_data.update({
                'rule_line_ids': rule_data.get('rule_line_ids', []) + [(4, new_group_id.id)] + group_child
            })
        elif tree_node.tag == 'Правило':
            if not rule_data:
                return
            rule_code = rule_data.get('code')
            if not rule_code:
                _logger.error('Rule without Code!')
                return
            rule_data['conv_id'] = self.id
            if parent_node == 'ПравилаКонвертацииОбъектов':
                Rule = self.env['conv.rule']

                # ********************************************************************
                # Warning: if Rule Attribute is False - then it not added to XML!
                # But when we have 'True' in some Attr in Odoo, we nead to clear it!
                # This is why we do this:
                add_to_data = {
                    'sync_by_uuid': False,
                    'after_import': '',
                    'fields_search': False,
                    'dont_create': False,
                    'dont_refill': False,
                    'create_new_code': False,
                    'dont_fill': False,
                    'before_processing': False,
                    'before_export': False,
                    # TODO ? 'export_to_param': '',
                }
                # Setup attrib, getted from XML
                add_to_data.update(rule_data)
                # Create full dictionary with ALL attributes
                rule_data.update(add_to_data)
                # ********************************************************************
            elif parent_node == 'ПравилаВыгрузкиДанных':
                Rule = self.env['o1c.export.rule']
            # FIXME тут поиск не всегда корректно срабатывает, когда есть два правила
            #  с одинаковым rule_code
            this_rule = Rule.search([('code', '=', rule_code), ('conv_id', '=', self.id)], limit=1)
            if not this_rule:
                Rule.create(rule_data)
            else:
                if parent_node == 'ПравилаКонвертацииОбъектов':
                    this_rule.rule_line_ids.unlink()
                this_rule.write(rule_data)
        elif tree_node.tag == 'ПравилаОбмена':
            if not conv_data:
                return
            conv_data['source_file_name'] = filename
            conv_data['conv_upload_date'] = fields.Datetime.now()
            rule_code = conv_data.get('o1c_uuid')
            if not rule_code:
                _logger.error('Conversion without UUID!')
                return
            # self.rule_ids.unlink()
            self.write(conv_data)
