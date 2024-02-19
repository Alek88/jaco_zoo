from odoo import models, fields, api


class RelatedProductTemplate(models.Model):
    _inherit='product.template'

    its_related_product_ids = fields.Many2many(string='Related product',
                                    comodel_name='product.template',
                                    relation='related_product_ids',
                                    column1='r_prod_1',
                                    column2='r_prod_2',
                                    )

    its_attribute_line_id = fields.Many2one(string='Attribute line',
                                            comodel_name='product.template.attribute.line', readonly=False)

    is_variant = fields.Boolean()
    its_attribute_id = fields.Many2one(string='Attribute', comodel_name='product.attribute', store=True)
    its_value_id = fields.Many2one(string='Value',  comodel_name='product.attribute.value')

    prevent_recursive_write = fields.Boolean(name='Revent recursive write', compute='_compute_rec')

    def get_product(self, id_product):
        return self.env['product.template'].browse(id_product)

    def change_product(self, product_linc, ids):
        fields_dict = {'its_related_product_ids': [(6, 0, ids)]}
        product_linc.write(fields_dict)

    def remove_rel_product(self, current_id, rem_id, other_ids):
        rem_prod = self.get_product(current_id)
        if rem_prod:
            rem_elated_product_val = rem_prod.its_related_product_ids.ids
            if rem_id in rem_elated_product_val:
                rem_elated_product_val.remove(rem_id)
            self.change_product(rem_prod, rem_elated_product_val)

    @api.onchange('attribute_line_ids')
    def change_attribute_line_ids(self):
        for rec in self:
            if rec.prevent_recursive_write:
                attr_lines = rec.attribute_line_ids
                n = 0
                current_attr_line = None
                for attr_line in attr_lines:
                    if attr_line.is_variant:
                        current_attr_line = attr_line
                        n += 1
                if n > 1:
                    for attr_line in attr_lines:
                        if not attr_line.is_current_variant:
                            self.its_attribute_line_id = None
                            self.its_attribute_id = None
                            self.its_value_id = None
                            attr_lines.is_variant = False
                else:
                    if current_attr_line:
                        self.its_attribute_line_id = current_attr_line
                        self.its_attribute_id = current_attr_line.attribute_id
                        if current_attr_line.value_ids:
                            self.its_value_id = current_attr_line.value_ids.ids[0]
                        for its_related_product_id in rec.its_related_product_ids:
                            its_related_product_id.its_attribute_id = current_attr_line.attribute_id
                            its_related_product_id.its_value_id = None

                for attr_line in attr_lines:
                    if attr_line.is_current_variant:
                        attr_line.is_current_variant = False

    @api.depends('its_attribute_line_id', 'attribute_line_ids')
    def _compute_rec(self):
        for rec in self:
            rec.prevent_recursive_write = True

    @api.model
    def action_open_product_template(self, record_id):
        model = self.env['product.template']
        record = model.browse(record_id)
        action = self.env.ref('stock.product_template_action_product')
        return {
            'type': action.type,
            'name': "Product template",
            'res_model': action.res_model,
            'res_id': record.id,
            'view_id': False,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'create': False, 'active_id': self.id}
        }

    @api.model
    def action_copy_product_attribute(self, record_id):
        model = self.env['product.template']
        record = model.browse(record_id)  # поточна модель
        attr_lines_ids = record.attribute_line_ids.ids  # атребути поточної поделі
        for rel_prod in record.its_related_product_ids.ids:
            lines = []
            prod_id = model.browse(rel_prod)  # повʼязана модель
            if attr_lines_ids:
                if prod_id.attribute_line_ids.ids:  # якщо є записи атребутів очистим
                    fields_dict = {
                        'attribute_line_ids': []}
                    prod_id.write(fields_dict)

                for line in attr_lines_ids:
                    browse_line = self.env['product.template.attribute.line'].browse(line)
                    is_variant = False
                    value_ids = browse_line.value_ids.ids
                    if browse_line.attribute_id == prod_id.its_attribute_id and prod_id.its_value_id:
                        value_ids.clear()
                        value_ids.append(prod_id.its_value_id.id)
                        is_variant = True

                    new_line = self.env['product.template.attribute.line'].create({
                        'attribute_id': browse_line.attribute_id.id,
                        'value_ids': [(6, 0, value_ids)],
                        'product_tmpl_id': prod_id.id,
                        'is_variant': is_variant,
                    })
                    lines.append(new_line.id)
                if lines:
                    prod_id.write({'attribute_line_ids': [(6, 0, lines)]})

    @api.model
    def write(self, vals):
        if self.prevent_recursive_write:
            line_ids = self.attribute_line_ids.ids.copy()
            if 'its_related_product_ids' in vals:
                self.prevent_recursive_write = False
                related_product_ids = vals['its_related_product_ids'][0][2]
                use_this_product = self.env['product.template'].search([('its_related_product_ids', 'in', self.ids)])
                use_this_product_ids = use_this_product.ids
                if use_this_product:
                    for current_id in use_this_product_ids:
                        if current_id not in related_product_ids:
                            self.remove_rel_product(current_id, self.ids[0], related_product_ids)
                for related_product_id in related_product_ids:
                    self.prevent_recursive_write = False
                    if related_product_id in use_this_product.ids:
                        continue
                    else:
                        add_prod = self.get_product(related_product_id)
                        add_related_product_val = add_prod.its_related_product_ids.ids
                        add_related_product_val.append(self.ids[0])
                        for product_id in related_product_ids:
                            if product_id not in add_related_product_val and product_id != related_product_id:
                                add_related_product_val.append(product_id)
                        self.change_product(add_prod, add_related_product_val)
        super().write(vals)
        return True

    @api.model
    def create(self, vals):
        record = super(RelatedProductTemplate, self).create(vals)
        try:
            related_product_ids = vals['its_related_product_ids'][0][2]
            object_id = record.id
            for related_product_id in related_product_ids:
                add_prod = self.get_product(related_product_id)
                add_related_product_val = add_prod.its_related_product_ids.ids
                add_related_product_val.append(object_id)
                self.change_product(add_prod, add_related_product_val)
        except Exception:
            pass
        return record
