
from odoo.tests.common import TransactionCase


class TestConvertNames(TransactionCase):

    def setUp(self):
        super(TestConvertNames, self).setUp()

    def test_convert_names(self):

        O1C = self.env['o1c.connector']
        model_name, field_name = O1C.from_1c_to_odoo_name('СправочникСсылка.productTemplate')
        self.assertEqual(model_name, 'product.template')

        model_name, field_name = O1C.from_1c_to_odoo_name('productTemplate')
        self.assertEqual(model_name, 'product.template')

        model_name, field_name = O1C.from_1c_to_odoo_name('ПеречислениеСсылка.irActionsAct_windowView__View_modeType')
        self.assertEqual(model_name, 'ir.actions.act_window.view')
        self.assertEqual(field_name, 'view_modeType')
