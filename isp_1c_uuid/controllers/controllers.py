# -*- coding: utf-8 -*-
# from odoo import http


# class As1cUuid(http.Controller):
#     @http.route('/as_1c_uuid/as_1c_uuid', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/as_1c_uuid/as_1c_uuid/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('as_1c_uuid.listing', {
#             'root': '/as_1c_uuid/as_1c_uuid',
#             'objects': http.request.env['as_1c_uuid.as_1c_uuid'].search([]),
#         })

#     @http.route('/as_1c_uuid/as_1c_uuid/objects/<model("as_1c_uuid.as_1c_uuid"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('as_1c_uuid.object', {
#             'object': obj
#         })
