# -*- coding: utf-8 -*-
import json
import logging
import pprint
import werkzeug

import base64
import hashlib
import hmac
from odoo import http, _
from odoo.http import request
_logger = logging.getLogger(__name__)


class OpencartController(http.Controller):

	@http.route(['/unicoding-marketplace/opencart/<int:storeId>'], type='json', auth='public', methods=['POST', 'GET'], csrf=False, cors="*")
	def opencart_webhook_json(self, storeId, **kwargs):
		# if request.httprequest.status_code != 200:
		# 	return False

		print("status_id.status")

		if 'eventType' not in request.dispatcher.jsonrequest.keys():
			return False
		print(request.dispatcher.jsonrequest)
		eventType = request.dispatcher.jsonrequest['eventType']
		if eventType != 'order.updated':
			return False


		orderstatus_new = request.dispatcher.jsonrequest['orderstatus_new']
		orderId = request.dispatcher.jsonrequest['orderId']
		no_action = request.dispatcher.jsonrequest['no_action']
		comment = request.dispatcher.jsonrequest['comment']

		order_id = request.env['sale.order'].sudo().search([('opencartid', '=', orderId), ('unicoding_marketplace_id.id', '=', storeId)])

		order_id = order_id.sudo()
		status_id = request.env['unicoding.opencart.status'].sudo().search([("opencartid", "=",orderstatus_new), ('unicoding_marketplace_id.id', '=', storeId)], limit=1)

		#print(order_id)
		if status_id.id == order_id.unicoding_opencart_status_id.id:
			return False

		order_id.write(
			{
				'unicoding_opencart_status_id': status_id.id,
			}
		)

		if order_id:
			#with_context(default_user_id=request.env).
			#order_id = order_id.with_user(request.env.ref('unicoding_marketplace_opencart.unicoding_marketplace_user_opencart_user').id)
			if not no_action:
				
				#message:
				order_id.message_post(body=_(
					"Opencart State %s, Comment: %s." % (status_id.name, comment)
				))

				print("ACTION")
				if status_id.status in ["COMPLETE"]:
					order_id.opportunity_id.with_context(no_send_status_update=True).action_set_won()

				if status_id.status in ['PAID', 'REFUNDED', 'PARTIALLY_REFUNDED', 'SHIPPED', 'DELIVERED',
										'COMPLETE', 'PROCESSING']:
					print(status_id.status)
					if order_id.state in ["draft", "sent"]:
						print(order_id.state)
						print("___action_confirm")
						print(order_id)
						order_id.with_context(no_send_status_update=True).action_confirm()
				if status_id.status in ['PAID']:
					print("__PAID")
					for invoice in order_id.invoice_ids:
						invoice.with_context(default_company_id=order_id.company_id.id, no_send_status_update=True).make_payment()
				if status_id.status in ['CANCELLED']:
					_logger.info("___CANCELLED")
					order_id.with_context(no_send_status_update=True)._action_cancel()

				if status_id.status in ['SHIPPED', 'DELIVERED', 'COMPLETE']:
					if order_id.state not in ["draft", "sent", "cancel", "done"]:
						print("___make_delivery")
						order_id.with_context(no_send_status_update=True).make_delivery()



			request.env['unicoding.marketplace'].sudo().opencart_notification(("Change status Opencart ID <b>%s</b>, sale order <b>%s</b>, order status <b>%s</b> " % (orderId, order_id.name, status_id.name)) )


		return True

