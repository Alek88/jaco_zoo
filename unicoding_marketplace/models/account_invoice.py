# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _



class AccountMove(models.Model):
    _inherit = 'account.move'

    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )

    def make_payment(self):
        for invoice_id in self:
            if invoice_id.unicoding_marketplace_id and invoice_id.amount_residual:
                #company_id = self._context.get('default_company_id', invoice_id.unicoding_marketplace_id.company_id.id)
                #Payment_method = self.env['account.payment.method']
                #payment_method_id = Payment_method.search([("payment_type", "=", "inbound")], limit=1)

                # res = self.env['account.payment.register'].with_context(active_model='account.move',
                #                                                         active_ids=[invoice_id.id]).create({
                #     'amount': invoice_id.amount_residual,
                #     'payment_type': 'inbound',
                #     'partner_type': 'customer',
                #     'journal_id': invoice_id.unicoding_marketplace_id.journal_id.id,
                #     'currency_id': invoice_id.currency_id.id,
                #     'partner_id': invoice_id.partner_id.id,
                #     #'partner_bank_id': invoice_id.partner_bank_id.id,
                #     'payment_method_id': payment_method_id.id,
                #     #'company_id': company_id,

                # })
                                                                        
                #res._create_payments()
                
                payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=[invoice_id.id]).create({
                    'currency_id': invoice_id.currency_id.id,
                    'payment_type': 'inbound',
                    'amount': invoice_id.amount_residual,
                    #'payment_date': '2017-01-01',
                })._create_payments()
                                                                        
              


