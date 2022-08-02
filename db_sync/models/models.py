from odoo import api, fields, models, _, service, registry, SUPERUSER_ID
import logging
import json
from urllib.parse import urlparse
from urllib.parse import urljoin
from collections import defaultdict
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
_logger = logging.getLogger(__name__)
import xmlrpc.client
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from datetime import datetime, timedelta
import operator as py_operator


class CustomDbSync(models.Model):
    _name = 'db.sync'

    db = fields.Char('DB')
    url = fields.Char('URL')
    port = fields.Integer('Port')
    username = fields.Char('Username')
    password = fields.Char('password')
    sync_saleorder = fields.Boolean('Push Sale order to DB')
    sync_inventory = fields.Boolean("Pull Inventory Quantity")
    sync_product = fields.Boolean("Push Product to DB")
    active = fields.Boolean("Active")
    customer_code = fields.Char("Customer code for creating order in DB")

    @api.model
    def create(self, vals_list):
        if 'active' in vals_list and vals_list['active']:
            check_exist = self._cr.execute("select * from db_sync where active=True")
            fetchreslt = self._cr.fetchone()
            if fetchreslt:
                raise ValidationError("Already found active record ")
        res = super(CustomDbSync, self).create(vals_list)
        return res

    def write(self, vals_list):
        if 'active' in vals_list and vals_list['active']:
            check_exist = self._cr.execute("select * from db_sync where active=True")
            fetchreslt = self._cr.fetchone()
            if fetchreslt:
                raise ValidationError("Already found active record")
        res = super(CustomDbSync, self).write(vals_list)
        return res

    def authenticate(self, url, db, username, password):
        _logger.info(url)
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url), allow_none=True)
        uid = common.authenticate(db, username, password, {})
        common.version()
        return uid

    def create_api_cust(self, url, db, uid, password, model_name, vals, method):
        _logger.info("*******************************************entered into api new")
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
        _logger.info("COMMON ==%s" % common)
        id = common.execute_kw(db, uid, password, model_name, method, [vals])
        return id

    def create_api_cust_1(self, url, db, uid, password, model_name, vals, method, fields_to_get):
        _logger.info("***************************************************entered into create_api_cust_1")
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
        _logger.info("COMMON ==%s" % common)
        c_id = common.execute_kw(db, uid, password, model_name, method, vals)
        count_qty = common.execute_kw(db, uid, password, model_name, 'read', [c_id], {'fields': fields_to_get})
        _logger.info("***********************************************************IDDD =%s" % c_id)
        return count_qty

    def unlink_api_cust(self, url, db, uid, password, model_name, unlink_id, method):
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
        _logger.info("update/unilink product ==%s" % common)
        c_id = common.execute_kw(db, uid, password, model_name, method, unlink_id)
        _logger.info("UPDATE?UNLINK val Result =%s" % c_id)
        return c_id


# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#
#     @api.model
#     def create(self, vals_list):
#         _logger.info("CREATE NEW ENTER")
#         res=super(StockMove,self).create(vals_list)
#         check_con = self.env['db.sync'].search([('active','=',True)],limit=1)
#         if check_con:
#             if check_con.sync_saleorder:
#                 url = check_con.url+':'+str(check_con.port)
#                 db=check_con.db
#                 username = check_con.username
#                 password = check_con.password
#                 authenticate = self.env['db.sync'].authenticate(url,db,username,password)
#                 if authenticate:
#                     create_val = self.env['db.sync'].create_api_cust(url,db,authenticate,password,'stock.move',vals_list)
#                 _logger.info("test")
#         return res
#
#
# class StockQuant(models.Model):
#     _inherit = 'stock.quant'
#
#     @api.model
#     def create_quant_custom_method(self,vals):
#
#         _logger.info("entered into new api call")
#         create_quant = self.env['stock.quant'].sudo().create(vals)
#         _logger.info("EXECUTED")
#         return create_quant.id
#
#
#     @api.model
#     def create(self, vals_list):
#         _logger.info("CREATE NEW ENTER quant")
#         res=super(StockQuant,self).create(vals_list)
#         _logger.info("RESSSSSS =%s"%res)
#         check_con = self.env['db.sync'].search([('active','=',True)],limit=1)
#         if check_con:
#             if check_con.sync_saleorder:
#                 url = check_con.url+':'+str(check_con.port)
#                 db=check_con.db
#                 username = check_con.username
#                 password = check_con.password
#                 authenticate = self.env['db.sync'].authenticate(url,db,username,password)
#                 if authenticate:
#                     create_val = self.env['db.sync'].create_api_cust_1(url,db,authenticate,password,'stock.quant',vals_list,'create_quant_custom_method')
#                 _logger.info("test")
#         _logger.info("EXECCCCCC")
#         return res


class Productproduct(models.Model):
    _inherit = 'product.product'

    x_studio_sku = fields.Char(string="Style", related="product_tmpl_id.x_studio_sku", store=True)
    qty_in_pack = fields.Float(string="Qty in Pack")
    qty_in_stack = fields.Float(string="Qty in Stack")
    gtin = fields.Char(string="GTIN")
    product_type_size = fields.Selection([('small', 'Small'), ('medium', 'Medium'), ('big', 'Big'),('light','Light')],
                                         string="Size Category")

    def write(self, vals_list):
        _logger.info("Entered into new edit product variant vals")
        # _logger.info("OLD SKU of Product Variant is %s"%self.default_code)
        for pdct in self:
            check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)
            update_vals = {}
            domain_val = [['default_code', '=', pdct.default_code]]
            if 'default_code' in vals_list or 'x_studio_sku' in vals_list or 'name' in vals_list or 'gtin' in vals_list or 'active' in vals_list or 'qty_in_pack' in vals_list or 'qty_in_stack' in vals_list:
                if check_con and check_con.sync_product:
                    if 'default_code' in vals_list:
                        update_vals['default_code'] = vals_list['default_code']
                        # if not pdct.default_code:
                        #     _logger.info("Product default code is newly added")
                        #     domain_val.append(['x_studio_sku','=',pdct.x_studio_sku])
                        #     domain_val.append(['product_template_attribute_value_ids','in',pdct.product_template_attribute_value_ids.ids])
                    if 'x_studio_sku' in vals_list:
                        update_vals['x_studio_sku'] = vals_list['x_studio_sku']
                    if 'name' in vals_list:
                        update_vals['name'] = vals_list['name']

                    if 'gtin' in vals_list:
                        update_vals['gtin'] = vals_list['gtin']
                    if 'active' in vals_list:
                        update_vals['active'] = vals_list['active']
                        if vals_list['active'] == True:
                            domain_val.append(['active', '=', False])
                    if 'qty_in_pack' in vals_list:
                        update_vals['qty_in_pack'] = vals_list['qty_in_pack']
                    if 'qty_in_stack' in vals_list:
                        update_vals['qty_in_stack'] = vals_list['qty_in_stack']

                    _logger.info("sync products")
                    url = check_con.url
                    db = check_con.db
                    username = check_con.username
                    password = check_con.password
                    authenticate = self.env['db.sync'].authenticate(url, db, username, password)
                    if authenticate and pdct.default_code:
                        for product in self:
                            res = self.env['db.sync'].create_api_cust_1(url, db, authenticate, password,
                                                                        'product.product',
                                                                        [domain_val],
                                                                        'search',
                                                                        ['id'])
                            _logger.info("RES =%s" % res)
                            if res:
                                create_val = self.env['db.sync'].unlink_api_cust(url, db, authenticate, password,
                                                                                 'product.product',
                                                                                 [[res[0]['id']], update_vals], 'write')
            res = super(Productproduct, self).write(vals_list)
            return res

    def compute_qty_sku(self, product):
        _logger.info("==============================================================ENTERED INTO NEQ COMPUTE QTY")
        prouct_qty = product._compute_quantities()
        res = {'qty_available': product.qty_available, 'virtual_available': product.virtual_available,
               'incoming_qty': product.incoming_qty,
               'outgoing_qty': product.outgoing_qty, 'free_qty': product.free_qty}
        qty_available = product.qty_available
        _logger.info(
            "============================================================================PRODUCT QTY ===%s" % qty_available)
        return res

    def _compute_quantities(self):
        _logger.info("_COMPUTE_QUANTITIES new")
        products = self.filtered(lambda p: p.type != 'service')
        check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)
        if check_con and check_con.sync_inventory:
            _logger.info("ENTEER INTO CHECK SYNC SALE ORDER")
            url = check_con.url
            db = check_con.db
            username = check_con.username
            password = check_con.password
            _logger.info(products)
            for product in self:
                if product.default_code:
                    _logger.info(
                        "==========================================PRODUCT DEFAULT CODE===========================")
                    with registry(db).cursor() as new_cr:
                        print("ENTERED INTO REGISTRY CODE")
                        env = api.Environment(new_cr, SUPERUSER_ID, {})
                        _logger.info(
                            "======================================CONNECTION ESTABLISHED=================================")
                        product_new = env['product.product'].sudo().search(
                            [('default_code', '=', product.default_code)], limit=1)
                        _logger.info(
                            "===================================PRODUCT FOUND IN DB===================================%s" % product_new)
                        temp_qty = env['product.product'].compute_qty_sku(product_new)
                        print("PRODUCT NAMEEEE ====%s" % temp_qty)
                        product.qty_available = temp_qty['qty_available'] if 'qty_available' in temp_qty else 0
                        product.virtual_available = temp_qty[
                            'virtual_available'] if 'virtual_available' in temp_qty else 0
                        product.incoming_qty = temp_qty['incoming_qty'] if 'incoming_qty' in temp_qty else 0
                        product.outgoing_qty = temp_qty['outgoing_qty'] if 'outgoing_qty' in temp_qty else 0
                        product.free_qty = temp_qty['free_qty'] if 'free_qty' in temp_qty else 0
                        env.cr.commit()
                        # env.close()
                else:
                    product.qty_available = 0
                    product.virtual_available = 0
                    product.incoming_qty = 0
                    product.outgoing_qty = 0
                    product.free_qty = 0

            # authenticate = self.env['db.sync'].authenticate(url,db,username,password)
            # if authenticate:
            #     for product in products:
            #         _logger.info("DEFAULT CODE ==%s"%product.default_code)
            #
            #         res = self.env['db.sync'].create_api_cust_1(url,db,authenticate,password,'product.product',[[['default_code','=',product.default_code]]],'search',['qty_available','incoming_qty','outgoing_qty','virtual_available','free_qty'])
            #         _logger.info(res)
            #         # pr_id = self.browse(res)
            #         # _logger.info(pr_id.qty_available)
            #         product.qty_available = res[0]['qty_available'] if res else 0
            #         product.incoming_qty = res[0]['incoming_qty'] if res else 0
            #         product.outgoing_qty = res[0]['outgoing_qty'] if res else 0
            #         product.virtual_available = res[0]['virtual_available'] if res else 0
            #         product.free_qty = res[0]['free_qty'] if res else 0
            # _logger.info(pr_id)
        else:
            _logger.info("ENTERED HERE IN ELSE")
            res = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'),
                                                    self._context.get('package_id'), self._context.get('from_date'),
                                                    self._context.get('to_date'))
            for product in products:
                product.qty_available = res[product.id]['qty_available']
                product.incoming_qty = res[product.id]['incoming_qty']
                product.outgoing_qty = res[product.id]['outgoing_qty']
                product.virtual_available = res[product.id]['virtual_available']
                product.free_qty = res[product.id]['free_qty']
            # Services need to be set with 0.0 for all quantities
            services = self - products
            services.qty_available = 0.0
            services.incoming_qty = 0.0
            services.outgoing_qty = 0.0
            services.virtual_available = 0.0
            services.free_qty = 0.0


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_studio_sku = fields.Char(string="Style")
    qty_in_pack = fields.Float(string="Qty in Pack")
    qty_in_stack = fields.Float(string="Qty in Stack")
    name_sku_combine = fields.Char("Combined name")
    gtin = fields.Char(string="GTIN")

    def compute_qty_sku(self, product):
        _logger.info("ENTERED INTO COMPUTE SKU")
        prouct_qty = product._compute_quantities()
        product_qty = product.qty_available
        _logger.info("**************************************************PRODUCT QTY ===%s" % product_qty)
        return product_qty

        # for product in self:
        #     if product.x_studio_sku:
        #         name = product.x_studio_sku + product.name
        #         product.name = name

        # def get_data_from_database(self):
        #     with registry('another_database_name') as new_cr:
        #         env = api.Environment(new_cr, SUPERUSER_ID, {})
        #         partner = env['res.partner'].search([('name', '=', 'ERP HARBOR CONSULTING SERVICES')], limit=1)
        #         print
        #         partner.name, partner.phone

    @api.depends_context('company_owned', 'force_company')
    def _compute_quantities(self):
        _logger.info("ENTERED IN TO TEMPLATE ONE")
        check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)
        if check_con and check_con.sync_inventory:
            _logger.info("ENTEER INTO CHECK SYNC SALE ORDER")
            url = check_con.url
            db = check_con.db
            for product in self:
                if product.x_studio_sku:
                    with registry(db).cursor() as new_cr:
                        print("ENTERED INTO REGISTRY CODE")
                        Env = api.Environment(new_cr, SUPERUSER_ID, {})
                        product_new = Env['product.template'].search([('x_studio_sku', '=', product.x_studio_sku)],
                                                                     limit=1)
                        temp_qty = Env['product.template'].compute_qty_sku(product_new)
                        _logger.info("******************************************PRODUCT NAMEEEE ====%s" % product_new)
                        product.qty_available = product_new.qty_available if product_new else 0.0
                        product.virtual_available = product_new.virtual_available if product_new else 0.0
                        product.incoming_qty = product_new.incoming_qty if product_new else 0.0
                        product.outgoing_qty = product_new.outgoing_qty if product_new else 0.0
                        # Env.cr.close()
                else:
                    product.qty_available = 0
                    product.virtual_available = 0
                    product.incoming_qty = 0
                    product.outgoing_qty = 0
            # username = check_con.username
            # password = check_con.password
            # authenticate = self.env['db.sync'].authenticate(url, db, username, password)
            # if authenticate:
            #     for product in self:
            #         _logger.info("DEFAULT CODE ==%s" % product.x_studio_sku)
            #         if product.x_studio_sku:
            #             res = self.env['db.sync'].create_api_cust_1(url, db, authenticate, password, 'product.template',
            #                                                     [[['x_studio_sku', '=', product.x_studio_sku]]],
            #                                                  'search',['qty_available','incoming_qty','outgoing_qty','virtual_available'])
            #         else:
            #             res = False
            #         _logger.info("RES =%s"%res)
            #         print("PRODUCT ====%s"%product)
            # product.qty_available = res[0]['qty_available'] if res else 0
            # product.virtual_available = res[0]['virtual_available'] if res else 0
            # product.incoming_qty = res[0]['incoming_qty'] if res else 0
            # product.outgoing_qty = res[0]['outgoing_qty'] if res else 0
        else:
            res = self._compute_quantities_dict()
            for template in self:
                template.qty_available = res[template.id]['qty_available']
                template.virtual_available = res[template.id]['virtual_available']
                template.incoming_qty = res[template.id]['incoming_qty']
                template.outgoing_qty = res[template.id]['outgoing_qty']

    @api.model
    def create(self, vals_list):
        _logger.info("Entered into new create vals")
        _logger.info(vals_list)
        res = super(ProductTemplate, self).create(vals_list)
        check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)
        if check_con and check_con.sync_product:
            url = check_con.url
            db = check_con.db
            username = check_con.username
            password = check_con.password
            authenticate = self.env['db.sync'].authenticate(url, db, username, password)
            if authenticate:
                vals = {'name': vals_list['name']}
                if 'default_code' in vals_list and vals_list['default_code']:
                    vals['default_code'] = vals_list['default_code']
                if 'x_studio_sku' in vals_list and vals_list['x_studio_sku']:
                    vals['x_studio_sku'] = vals_list['x_studio_sku']
                if 'attribute_line_ids' in vals_list and vals_list['attribute_line_ids']:
                    for att in vals_list['attribute_line_ids']:
                        del att[2]['sequence']
                    vals['attribute_line_ids'] = vals_list['attribute_line_ids']

                create_val = self.env['db.sync'].create_api_cust(url, db, authenticate, password, 'product.template',
                                                                 vals, 'create')
        return res

    def unlink(self):
        _logger.info("Entered into new unlink vals")

        check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)
        if check_con and check_con.sync_product:
            _logger.info("sync products")
            url = check_con.url
            db = check_con.db
            username = check_con.username
            password = check_con.password
            authenticate = self.env['db.sync'].authenticate(url, db, username, password)
            if authenticate:
                for product in self:
                    res = self.env['db.sync'].create_api_cust_1(url, db, authenticate, password, 'product.template',
                                                                [[['x_studio_sku', '=', product.x_studio_sku]]],
                                                                'search',
                                                                ['id'])
                    _logger.info("RES =%s" % res)
                    if res:
                        create_val = self.env['db.sync'].unlink_api_cust(url, db, authenticate, password,
                                                                         'product.template',
                                                                         [[res[0]['id']]], 'unlink')
        res = super(ProductTemplate, self).unlink()
        return res

    def write(self, vals_list):
        _logger.info("val list ==%s" % vals_list)
        _logger.info("Entered into new edit product template vals")
        check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)
        update_vals = {}
        for pdct in self:
            _logger.info("SKU ==%s" % pdct.x_studio_sku)
            domain_val = [['x_studio_sku', '=', pdct.x_studio_sku]]
            if 'default_code' in vals_list or 'x_studio_sku' in vals_list or 'name' in vals_list or 'qty_in_pack' in vals_list or 'qty_in_stack' in vals_list or 'gtin' in vals_list or 'active' in vals_list:
                if check_con and check_con.sync_product:
                    if 'default_code' in vals_list:
                        update_vals['default_code'] = vals_list['default_code']
                    if 'x_studio_sku' in vals_list:
                        update_vals['x_studio_sku'] = vals_list['x_studio_sku']
                    if 'name' in vals_list:
                        update_vals['name'] = vals_list['name']
                    if 'active' in vals_list:
                        update_vals['active'] = vals_list['active']
                        if vals_list['active'] == True:
                            domain_val.append(['active', '=', False])
                    if 'qty_in_pack' in vals_list:
                        update_vals['qty_in_pack'] = vals_list['qty_in_pack']
                    if 'qty_in_stack' in vals_list:
                        update_vals['qty_in_stack'] = vals_list['qty_in_stack']
                    # if 'default_code' in vals_list:
                    #     update_vals['default_code'] = vals_list['update_vals']
                    _logger.info("sync products")
                    url = check_con.url
                    db = check_con.db
                    username = check_con.username
                    password = check_con.password
                    authenticate = self.env['db.sync'].authenticate(url, db, username, password)
                    if authenticate:
                        for product in self:
                            _logger.info(product.x_studio_sku)
                            res = self.env['db.sync'].create_api_cust_1(url, db, authenticate, password,
                                                                        'product.template',
                                                                        [domain_val],
                                                                        'search',
                                                                        ['id'])
                            print("PRODUCT ID FOUND ===%s" % res)
                            _logger.info("RES =%s" % res)
                            if res:
                                create_val = self.env['db.sync'].unlink_api_cust(url, db, authenticate, password,
                                                                                 'product.template',
                                                                                 [[res[0]['id']], update_vals], 'write')
            res = super(ProductTemplate, self).write(vals_list)

            return res


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sync_reference = fields.Char("Reference for sync")
    is_synced = fields.Boolean("Synced")
    jespa_customer_name = fields.Char("Jespa Customer Name")

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['jespa_customer_name'] = self.jespa_customer_name
        invoice_vals['jespa_so_number'] = self.sync_reference
        return invoice_vals

    def action_confirm(self):
        check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)
        if check_con and check_con.sync_saleorder:
            if self.state != 'sale':
                url = check_con.url
                db = check_con.db
                username = check_con.username
                password = check_con.password
                authenticate = self.env['db.sync'].authenticate(url, db, username, password)
                line_ids = []
                vals = {'is_synced': True, 'sync_reference': self.name, 'jespa_customer_name': self.partner_id.name or ''}
                for line in self.order_line:
                    sku = line.product_id.default_code
                    _logger.info("SKUU =%s" % sku)
                    qty = line.product_uom_qty
                    res_p = self.env['db.sync'].create_api_cust_1(url, db, authenticate, password, 'res.partner',
                                                                  [[['x_studio_code', '=', check_con.customer_code]]],
                                                                  'search',
                                                                  ['id'])
                    if res_p:
                        vals['partner_id'] = res_p[0]['id']
                    else:
                        raise ValidationError("CUstomer code not matching in database")
                    res = self.env['db.sync'].create_api_cust_1(url, db, authenticate, password, 'product.product',
                                                                [[['default_code', '=', sku]]],
                                                                'search',
                                                                ['id'])
                    _logger.info("TEST CHECK res value=%s" % res)
                    if res:
                        _logger.info(res)
                        product_id = res[0]['id']
                        line_val = [0, 0, {'product_id': product_id, 'product_uom_qty': qty}]
                        line_ids.append(line_val)
                vals['order_line'] = line_ids
                self.write({'state': 'sale','date_order':datetime.now()})
                self.env.cr.commit()
                create_val = self.env['db.sync'].create_api_cust(url, db, authenticate, password, 'sale.order',
                                                                 vals, 'create')
                if create_val:
                    self.is_synced = True
                    # self.sudo()._send_order_confirmation_mail()
                    act_confirm = self.env['db.sync'].create_api_cust(url, db, authenticate, password, 'sale.order',
                                                                      [create_val], 'make_order_confirm')


        else:
            if self._get_forbidden_state_confirm() & set(self.mapped('state')):
                raise UserError(_(
                    'It is not allowed to confirm an order in the following states: %s'
                ) % (', '.join(self._get_forbidden_state_confirm())))

            for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
                order.message_subscribe([order.partner_id.id])
            self.write({
                'state': 'sale',
                'date_order': fields.Datetime.now()
            })
            self._action_confirm()
            # self.sudo()._send_order_confirmation_mail()
            if self.env.user.has_group('sale.group_auto_done_setting'):
                self.action_done()
        return True

    def make_order_confirm(self):
        _logger.info("MAKE SALE ORDER ===%s" % self)
        for order in self:
            confirm = order.action_confirm()
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'customer_lead', 'product_uom_qty', 'order_id.warehouse_id', 'order_id.commitment_date')
    def _compute_qty_at_date(self):
        _logger.info("==============================================================ENTERED HERE IN ORDER LINE value")
        """ Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a commitment_date, we take it as delivery date
         2. The quotation hasn't commitment_date, we compute the estimated delivery
            date based on lead time"""
        check_con = self.env['db.sync'].search([('active', '=', True)], limit=1)

        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
        for line in self:
            if not line.display_qty_widget:
                continue
            line.warehouse_id = line.order_id.warehouse_id
            if line.order_id.commitment_date:
                date = line.order_id.commitment_date
            else:
                confirm_date = line.order_id.date_order if line.order_id.state in ['sale', 'done'] else datetime.now()
                date = confirm_date + timedelta(days=line.customer_lead or 0.0)
            grouped_lines[(line.warehouse_id.id, date)] |= line

        treated = self.browse()
        if check_con and check_con.sync_inventory:
            pass
        else:
            for (warehouse, scheduled_date), lines in grouped_lines.items():
                product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date,
                                                                        warehouse=warehouse).read([
                    'qty_available',
                    'free_qty',
                    'virtual_available',
                ])
                qties_per_product = {
                    product['id']: (product['qty_available'], product['free_qty'], product['virtual_available'])
                    for product in product_qties
                }
                for line in lines:
                    line.scheduled_date = scheduled_date
                    qty_available_today, free_qty_today, virtual_available_at_date = qties_per_product[
                        line.product_id.id]
                    line.qty_available_today = qty_available_today - qty_processed_per_product[line.product_id.id]
                    line.free_qty_today = free_qty_today - qty_processed_per_product[line.product_id.id]
                    line.virtual_available_at_date = virtual_available_at_date - qty_processed_per_product[
                        line.product_id.id]
                    qty_processed_per_product[line.product_id.id] += line.product_uom_qty
                treated |= lines
        remaining = (self - treated)
        remaining.virtual_available_at_date = False
        remaining.scheduled_date = False
        remaining.free_qty_today = False
        remaining.qty_available_today = False
        remaining.warehouse_id = False


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    jespa_so_number = fields.Char("Jespa So Number")
    jespa_customer_name = fields.Char("Jespa Customer")
    check_cus_val = fields.Char(compute='get_jespa_details')

    @api.depends('partner_id','jespa_so_number')
    def get_jespa_details(self):
        _logger.info("=========================get jespa details===================")
        for move in self:
            if move.invoice_origin:
                sale_order = self.env['sale.order'].search([('name','=',move.invoice_origin)],limit=1)
                move.jespa_customer_name = sale_order.jespa_customer_name if sale_order and sale_order.jespa_customer_name else ''
                move.jespa_so_number = sale_order.sync_reference if sale_order and sale_order.sync_reference else ''
            move.check_cus_val = ''






