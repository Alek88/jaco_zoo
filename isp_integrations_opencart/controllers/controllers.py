# -*- coding: utf-8 -*-
# from odoo import http


# class IspIntegrationsOpencart(http.Controller):
#     @http.route('/isp_integrations_opencart/isp_integrations_opencart', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/isp_integrations_opencart/isp_integrations_opencart/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('isp_integrations_opencart.listing', {
#             'root': '/isp_integrations_opencart/isp_integrations_opencart',
#             'objects': http.request.env['isp_integrations_opencart.isp_integrations_opencart'].search([]),
#         })

#     @http.route('/isp_integrations_opencart/isp_integrations_opencart/objects/<model("isp_integrations_opencart.isp_integrations_opencart"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('isp_integrations_opencart.object', {
#             'object': obj
#         })
