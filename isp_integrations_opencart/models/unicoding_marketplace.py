from odoo import _, api, fields, models
import requests
from datetime import datetime
import logging

from odoo.tools import float_repr

_logger = logging.getLogger(__name__)
import base64

URLOPEN_TIMEOUT = 100
# import werkzeug
import html
import threading
from urllib.parse import urlencode
import json


class UnicodingMarketplace(models.Model):
    _inherit = 'unicoding.marketplace'
    _access_token = fields.Char(string="Access token")

    def opencart_export_public_categories(self):
        for opencart_id in self:
            pub_category = self.env['product.public.category'].search_read(
                    [('unicoding_marketplace_id', '=', opencart_id.id), '|', ('opencartid', '=', None), ('is_change', '=', True)],
                     ['id','opencartid', 'parent_id', 'name', "image_512"]
                    )

            for fields_category in pub_category:
                #base_url = opencart_id.env['ir.config_parameter'].sudo().get_param('web.base.url')
                #image_url_1024 = base_url + '/web/image?' + 'model=product.public.category&id=' + str(fields_category.id) + '&field=image_1024'
                fields_category['oc_id'] = fields_category.pop('opencartid')
                fields_category['image'] = fields_category.pop('image_512')
                fields_category['name_en'] = ''
                if not fields_category['oc_id']:
                    fields_category['oc_id'] = 0
                if not fields_category['image']:
                    fields_category['image'] = ''

            if pub_category:
                result = opencart_id.opencart_request(
                    "%s/index.php?route=api/integrations/export-public-categories" % (opencart_id.url),
                           {'api_token': opencart_id._access_token, 'token': opencart_id._access_token,
                            'public_category': pub_category}, 'post')
                if result:
                    return result
                else:
                    return {}
