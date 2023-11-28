# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'

    # def reverse_moves(self):
    #
    #     moves = self.move_ids
    #     print(moves)
    #     return super().reverse_moves()

    def _prepare_default_reversal(self, move):

        default_values_list = super()._prepare_default_reversal(move)
        default_values_list['unicoding_marketplace_id'] = move.unicoding_marketplace_id.id
        default_values_list['opencartid'] = move.opencartid
        return default_values_list
