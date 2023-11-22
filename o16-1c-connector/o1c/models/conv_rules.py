# Copyright © 2019-2023 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.
# pylint: disable=no-else-return,too-many-locals,too-many-return-statements

import logging

from odoo import api, models, fields, _
# html2plaintext used in rules
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class ConversionRulesAbstract(models.AbstractModel):
    _name = 'o1c.conversion.common'
    _description = 'Conversion Common'

    name = fields.Char('Name')
    code = fields.Char(index=True, copy=False, required=True, help='1C Rule Код')
    order = fields.Integer(index=True)
    sync_by_uuid = fields.Boolean('Sync by UUID', help='1C tag СинхронизироватьПоИдентификатору')
    source_name = fields.Char()
    destin_name = fields.Char()
    disabled = fields.Boolean()

    # WARNING: 'before_processing' used in before_processing_field and in before_processing_obj!
    #   be careful for not execute this rule twice!
    #   Example: use have field with type ТабличнаяЧасть as o2m.
    #       Code 'before_processing' can execute before export o2m field
    #       AND executed on each row! of o2m list! This is incorrect!
    before_processing = fields.Text(help='Run this code before processing data.')
    before_export = fields.Text(help='Run this code before export data')


class ConversionRules(models.Model):
    _name = 'conv.rule'
    _inherit = ['o1c.conversion.common']
    _order = 'conv_id, order'
    _description = 'Conversion Rules'

    conv_id = fields.Many2one('o1c.conv', ondelete='cascade', required=True)
    rule_line_ids = fields.One2many('conv.rule.line', 'owner_id')
    dont_refill = fields.Boolean(
        'Do not refill',
        help='Не Замещать существующие объекты в приемнике,'
             ' а только создавать новые и заполнять их')
    fields_search = fields.Boolean('Search by Keys', help='1C Продолжить поиск по полям поиска, если по Идентификатору не нашли')
    dont_create = fields.Boolean('Do not create', help='1C НеСоздаватьЕслиНеНайден')
    create_new_code = fields.Boolean('Create new ID', help='1C ГенерироватьНовыйНомерИлиКодЕслиНеУказан')
    dont_fill = fields.Boolean('Only GUID', help='1С ПриПереносеОбъектаПоСсылкеУстанавливатьТолькоGIUD')
    after_import = fields.Text('Run after import', help='Run this code after import object')

    _sql_constraints = [
        ('code_uniq', 'unique(code, conv_id)', 'The RuleCode of the Database Item must be unique!'),
    ]


class ConversionRulesLine(models.Model):
    _name = 'conv.rule.line'
    _inherit = ['o1c.conversion.common']
    _order = 'owner_id, order'
    _description = 'Conversion Rule of the Field'

    owner_id = fields.Many2one('conv.rule', string='Owner Rule', ondelete='cascade')
    conv_id = fields.Many2one('o1c.conv', related='owner_id.conv_id')
    is_group = fields.Boolean(help='1C ТабличнаяЧасть')
    parent_rule_id = fields.Many2one('conv.rule.line', string='Folder', ondelete='cascade')
    source_vid_id = fields.Many2one('o1c.vid', ondelete='set null')
    source_tip_id = fields.Char()
    destin_vid_id = fields.Many2one('o1c.vid', ondelete='set null')
    destin_tip_id = fields.Char()
    search_field = fields.Boolean(index=True, help='Search by this field.')
    conv_rule_id = fields.Many2one(
        'conv.rule', ondelete='cascade',
        help='Rule for conversion data in Source before export')
    dont_refill_field = fields.Boolean(
        'Do not refill',
        help='Не Замещать значение поля если оно уже заполнено')
    export_to_param = fields.Char(help='Export data to Parameter')
