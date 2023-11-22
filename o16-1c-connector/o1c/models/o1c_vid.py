# Copyright © 2019 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class O1CVid(models.Model):
    _name = 'o1c.vid'
    _description = '1c Vids'

    name = fields.Char('Name', index=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The 1C Vid Name must be unique!'),
    ]
