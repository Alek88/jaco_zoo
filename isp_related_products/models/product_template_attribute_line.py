from odoo import models, fields, api


class ISPProductTemplateAttributeLine(models.Model):
    _inherit='product.template.attribute.line'

    is_variant = fields.Boolean(string='Is variant')
    is_current_variant = fields.Boolean(storage=True)

    @api.onchange('is_variant')
    def _reset_is_variant(self):
        for rec in self:
            if rec.is_variant:
                rec.is_current_variant = True

    @api.model
    def write(self, vals):
        if 'is_variant' in vals and vals['is_variant']:
            other_rec = self.search([('product_tmpl_id', '=', self.product_tmpl_id.ids),
                                     ('id', '!=', self.id)])
            other_rec.write({'is_variant': False})
        return super(ISPProductTemplateAttributeLine, self).write(vals)
