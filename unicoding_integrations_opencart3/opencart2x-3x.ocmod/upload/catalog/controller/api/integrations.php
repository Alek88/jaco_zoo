<?php

require_once(DIR_SYSTEM . 'library/ripcord-master/ripcord_client.php');

class ControllerApiIntegrations extends Controller {

    public function syncpricelist(){
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        $this->load->model('tool/image');
        $json = array();

        if (version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if (isset($api['api_id'])) {
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }


        if (!isset($this->session->data['api_id'])) {
            $json['state'] = $this->language->get('error_permission');
        } elseif(!isset($this->request->get['pricelist_ids'])) {
            $json['state'] = 'Errors sync pricelists';
        } else {


            $url = $this->config->get('config_odoo_webhook_url');
            $parse = parse_url($url);
            if (!isset($parse["scheme"])){
                $json['state'] = 'Errors sync add pricelists URL wrong';
            }else{

                $url = $parse["scheme"] . "://" . $parse["host"] . ( (isset($parse["port"]) and $parse["port"]) ? ":" . $parse["port"] : "");
                $db = $this->config->get('config_odoo_db');
                $username = $this->config->get('config_odoo_username');
                $password = $this->config->get('config_odoo_password');

                $common = ripcord::client("$url/xmlrpc/2/common");
                #$common->version();

                $uid = $common->authenticate($db, $username, $password, array());


                $models = ripcord::client("$url/xmlrpc/2/object");
              

                $res_pricelists = $models->execute_kw($db, $uid, $password,
                'product.pricelist', 'search_read',
                #array(array(array('opencartid', '=', false))),
                array(array(array('id', 'in',array_map('intval', explode(",", $this->request->get['pricelist_ids'])) ))),
                array('fields'=>array('name'), 'limit'=>100));

                            

               

              


                require('admin/model/customer/customer_group.php');

                $this->load->model('localisation/language');
                $languages = $this->model_localisation_language->getLanguages();
                

              

                $model_customer_group = new ModelCustomerCustomerGroup( $this->registry );
                $customer_groups = $model_customer_group->getCustomerGroups();

                foreach($res_pricelists as $kp=>$vp){
                    $customer_group_id = False;
                    foreach($customer_groups as $k=>$v){
                        if ($v["name"] == $vp["name"]){
                            $customer_group_id = $v["customer_group_id"];
                            break;
                        }
                    }
                    
                    if (!$customer_group_id){
                        $description = array();
                        foreach ($languages as $language) {
                            $description[$language['language_id']] = array(
                                'name' => $vp["name"],
                                'description' => $vp["name"],
                            );
                        }
                        $data = array();
                        $data["approval"] = 1;
                        $data["sort_order"] = 0;
                        $data["customer_group_description"] = $description;
                        $customer_group_id = $model_customer_group->addCustomerGroup($data);    
                    } 

                    $res = $models->execute_kw($db, $uid, $password,
                        'product.pricelist.item', 'search_read',
                        array(array(array('pricelist_id', '=', (int) $vp["id"] ), array('opencartid', '!=', false))),
                        array('fields'=>array('opencartid', 'min_quantity', 'fixed_price', 'date_start', 'date_end'), 'limit'=>10000));

                    
                    $product_discounts = array();
                    foreach($res as $k=>$v)
                        $product_discounts[] = array(
                                'product_id' => (int)$v['opencartid'],
                                'customer_group_id' => $customer_group_id,
                                'priority' => 1,
                                'price' => (float)$v['fixed_price'],
                                'date_start' => $v['date_start'],
                                'date_end' => $v['date_end']
                        );

                    if (count($product_discounts)){
                        $this->model_account_integrations->clearDiscountPrice($customer_group_id);
                        $this->model_account_integrations->addProductDiscounts($product_discounts);
                    }

                    // $product_specials = array(); 
                    // $res = $models->execute_kw($db, $uid, $password,
                    //     'bi.customer.price', 'search_read',
                    //     array(array()),
                    //     array('fields'=>array('partner_opencartid', 'price', 'product_opencartid'), 'limit'=>10000));


                   
                    // foreach($res as $k=>$v){
                    //     if ($v['product_opencartid'] and $v['partner_opencartid']){
                    //         $product_specials[] = array(
                    //                 'product_id' => (int)$v['product_opencartid'],
                    //                 'customer_group_id' => 22,//(int)$this->config->get('config_customer_group_id'),
                    //                 'priority' => 1,
                    //                 'price' => (float)$v['price'],
                    //                 'customer_id' => $v['partner_opencartid'],
                    //                 'date_start' => '',
                    //                 'date_end' => ''
                    //         );
                    //         $this->model_account_integrations->clearSpecialPriceCustomer( $v['partner_opencartid']);
                    //     }
                    // }

                    // if (count($product_specials)){
                        
                    //     $this->model_account_integrations->addProductSpecials( $product_specials );
                    // }

                     
                }
                $json['state'] = "Success import pricelists";            
            }
        }

        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }

    public function syncproducts(){
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        $this->load->model('tool/image');
        $json = array();

        if (version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if (isset($api['api_id'])) {
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }


        if (!isset($this->session->data['api_id'])) {
            $json['state'] = $this->language->get('error_permission');
        } elseif(!isset($this->request->get['products'])) {
            $json['state'] = 'Errors sync add products';
        } else {

            $url = $this->config->get('config_odoo_webhook_url');
            $parse = parse_url($url);
            if (!isset($parse["scheme"])){
                $json['state'] = 'Errors sync add products URL wrong';
            }else{

                $url = $parse["scheme"] . "://" . $parse["host"] . ( (isset($parse["port"]) and $parse["port"]) ? ":" . $parse["port"] : "");
                $db = $this->config->get('config_odoo_db');
                $username = $this->config->get('config_odoo_username');
                $password = $this->config->get('config_odoo_password');

                $common = ripcord::client("$url/xmlrpc/2/common");
                #$common->version();

                $uid = $common->authenticate($db, $username, $password, array());


                $models = ripcord::client("$url/xmlrpc/2/object");

                $res = $models->execute_kw($db, $uid, $password,
                'product.template', 'search_read',
                #array(array(array('opencartid', '=', false))),
                array(array(array('id', 'in', explode(",", $this->request->get['products'])))),
                array('fields'=>array('name', 'default_code', 'barcode', 'image_1920', 'type', 'categ_id_opencartid', 'description', 'attribute_line_ids', 'list_price', 'taxes_id'), 'limit'=>5));









                require('admin/model/catalog/product.php');
                require('admin/model/catalog/option.php');
                // require('admin/model/localisation/tax_class.php');

                // $model_localisation_tax_class = new ModelLocalisationTaxClass( $this->registry );
                // $results = $this->model_localisation_tax_class->getTaxClasses();




                // foreach($res as $k=>$v){
                //     if isset($v[taxes_id][0]){
                //         $res_value = $models->execute_kw($db, $uid, $password,
                //             'account.tax', 'search_read',
                //                 array(array(array('id', 'in', $v[taxes_id][0]))),
                //                 array('fields'=>array('id', 'name')));
                //         foreach ($results as $result) {
                //             if ($result['title'] == ""){

                //             }
                //         }
                //     }
                // }





                $model_catalog_product = new ModelCatalogProduct( $this->registry );
                $model_catalog_option = new ModelCatalogOption( $this->registry );




                $description = array();

                $this->load->model('localisation/language');
                $languages = $this->model_localisation_language->getLanguages();
                $cat_ids = [];

                foreach($res as $k=>$v){
                    // if (isset($v["categ_id"][0]))
                    //     $cat_ids[] = $v["categ_id"][0];
                    foreach ($languages as $language) {
                        $description[$language['language_id']] = array(
                            'name' => $v["name"],
                            'description' => $v["description"],
                            'meta_title' => $v["name"],
                            'tag' => '',
                            'meta_description' => $v["description"],
                            'meta_keyword' => ''
                        );
                    }
                }

                $this->load->model('setting/store');
                $stores = $this->model_setting_store->getStores();
                $product_stores = array();
                $product_stores[] = 0;
                foreach ($stores as $result) {
                    $product_stores[] = $result['store_id'];
                }




                // $res_cat = [];
                // if(count($cat_ids))
                //     $res_cat = $models->execute_kw($db, $uid, $password,
                //     'product.category', 'search_read',
                //         array(array(array('id', 'in', $cat_ids))),
                //     array('fields'=>array('opencartid')));


                // foreach($res_cat as $k=>$v)
                //     $cats[$v["id"]] = $v["opencartid"];





                foreach($res as $k=>$v){
                    $product_to_category =  $this->model_account_integrations->get_cat_path($v["categ_id_opencartid"]);



                    $id = $v["id"];
                    $brand = "";
                    if (!file_exists(DIR_IMAGE."catalog/odoo/".$brand."/")) {
                        if (!mkdir(DIR_IMAGE."catalog/odoo/".$brand."/", 0777, true)) {
                            die('Не удалось создать директории...');
                        }
                    }
                    if (!file_exists(DIR_IMAGE."catalog/odoo/".$brand."/" . $id)) {
                        if (!mkdir(DIR_IMAGE."catalog/odoo/".$brand."/" . $id, 0777, true)) {
                            die('Не удалось создать директории...');
                        }
                    }

                    $image = "";
                    if ($v["image_1920"]){


                        $decodedImageData = base64_decode($v["image_1920"]);

                        // image file extension
                        $extension = "jpeg";

                        if (!file_exists(DIR_IMAGE."catalog/odoo/".$brand."/" . $id . "/" . $k. "." . $extension)){
                            file_put_contents(DIR_IMAGE."catalog/odoo/".$brand."/" . $id . "/" . $k. "." . $extension, $decodedImageData);
                        }
                        $image = "catalog/odoo/".$brand."/" . $id . "/" .$k. "." . $extension;
                    }


                    $product = array(
                        'model' => $v["default_code"],
                        'product_description' => $description,
                        'image' => $image,  'images' => array(),
                        'sku' => '', 'upc' => '', 'ean' => $v["barcode"], 'jan' => '', 'isbn' => '', 'mpn' => '', 'location' => '',
                        'quantity' => '99',
                        'minimum' => '1',
                        'subtract' => $v['type']=="product" ? '1' : '0',
                        'stock_status_id' => '1',
                        'date_available' => date('Y/m/d'),
                        'manufacturer_id' => '',
                        'product_store' => $product_stores,
                        'product_category' => $product_to_category,
                        'shipping' => $v['type']=="product" ? '1' : '0',
                        'price' => $v['list_price'],
                        'points' => '', 'weight' => '', 'weight_class_id' => '', 'length' => '', 'width' => '', 'height' => '', 'length_class_id' => '',
                        'status' => '1',
                        'tax_class_id' => '',
                        'sort_order' => '',
                        'keyword' => ''
                    );


                    $res_attributes = $models->execute_kw($db, $uid, $password,
                    'product.template.attribute.line', 'search_read',
                        array(array(array('id', 'in', $v["attribute_line_ids"]))),
                        array('fields'=>array('attribute_id', 'value_ids')));

                    $product["product_option"] = [];
                    #print_r($res_attributes);
                    $product_variant_ids_qty = [];
                    foreach($res_attributes as $ak=>$attr_values){

                        $option = $model_catalog_option->getOptions(array(
                            'filter_name'=> $attr_values["attribute_id"][1],
                            'start'=>0,
                            'limit'=>1
                        ));


                        if(!count($option))
                            continue;

                        if ($option[0]['type'] != 'select' and $option[0]['type'] != 'radio' and $option[0]['type'] != 'checkbox')
                            continue;

                        $product["product_option"][$ak] = array(
                            "option_id"=>$option[0]["option_id"],
                            "type"=>$option[0]["type"],
                            'product_option_id'=>'',
                            "name"=>$option[0]["type"],
                            "required"=>0
                        );


                        // $res_value = $models->execute_kw($db, $uid, $password,
                        // 'product.template.attribute.value', 'search_read',
                        //     array(array(array('product_tmpl_id', '=', $v["id"]))),
                        //     array('fields'=>array('id', 'name', 'attribute_id', 'attribute_line_id', 'product_attribute_value_id', 'ptav_product_variant_ids', 'product_tmpl_id')));
                        // print_r($res_value);
                        // exit();

                        $res_value = $models->execute_kw($db, $uid, $password,
                        'product.template.attribute.value', 'search_read',
                            array(array(array('product_tmpl_id', '=', $v["id"]), array('product_attribute_value_id', 'in', $attr_values["value_ids"]))),
                            array('fields'=>array('id', 'name', 'product_tmpl_id', 'ptav_product_variant_ids')));

                            #print_r($attr_values);
                            #print_r($res_value);



                        $option_values = $model_catalog_option->getOptionValueDescriptions($option[0]["option_id"]);


                        foreach($res_value as $rv){


                            $product_product = $models->execute_kw($db, $uid, $password,
                            'product.product', 'search_read',
                            #array(array(array('opencartid', '=', false))),
                            array(array( array('id', 'in', $rv["ptav_product_variant_ids"]))),
                            array('fields'=>array('qty_available')));

                            #print_r($product_product);
                            $sum = 0;
                            foreach($product_product as $ss){
                                $sum += $ss['qty_available'];
                                $product_variant_ids_qty[$ss["id"]] = $ss['qty_available'];
                            }


                            foreach($option_values as $ov)

                                if($rv["name"]==$ov["option_value_description"][1]["name"]){
                                    $product["product_option"][$ak]["product_option_value"][] = array(
                                        "option_value_id"=>$ov["option_value_id"],
                                        'product_option_value'=>'',
                                        'weight_prefix'=>'+',
                                        'weight'=>0,
                                        'points_prefix'=>'+',
                                        'points'=>0,
                                        'price_prefix'=>'+',
                                        'price'=>0,
                                        'subtract'=>1,
                                        'quantity'=>$sum
                                    );

                                }



                        }
                    }
                    $product["quantity"] = array_sum($product_variant_ids_qty);



                    #print_r($product);
                    #exit();




                    $product_id = $model_catalog_product->addProduct( $product );
                    #update odoo product
                    // $id = $models->execute_kw($db, $uid, $password,
                    // 'product.template', 'write',  array(array($v["id"]), array('opencartid'=>$product_id, "opencart_url"=>$this->url->link('product/product', '&product_id=' . $product_id), "unicoding_marketplace_id"=>1)));

                    $id = $models->execute_kw($db, $uid, $password,
                    'product.template', 'write',  array(array($v["id"]), array('opencartid'=>$product_id, "opencart_url"=>$this->url->link('product/product', '&product_id=' . $product_id))));

                    $json['state'] = $this->language->get('text_success');

                }




            }
        }

        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));

    }
    public function orderHistory($route, $input_data) {
        if($route = "checkout/order/addOrderHistory" && $input_data && isset($input_data[0])) {
            $order_id = (int)$input_data[0];
            $order_state_id = (int)$input_data[1];
            $order_comment = isset($input_data[2]) ? $input_data[2] : "";
            if ((int)$this->config->get('config_odoo_status_order') ){

                $this->load->model('checkout/order');
                $order_info = $this->model_checkout_order->getOrder($order_id);
                if ($order_info['order_status_id'] != $order_state_id){

                     //The URL that we want to send a PUT request to.
                    $url = $this->config->get('config_odoo_webhook_url');


                    $fields = array("eventType" => "order.updated", "orderId"=>$order_id, "orderstatus_new"=>$order_state_id, "comment"=>nl2br($order_comment), "no_action"=>($order_comment=="odoo") ? True : False);
                    $data_json = json_encode($fields);

                    $ch = curl_init();

                    curl_setopt($ch, CURLOPT_URL, $url);
                    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json; charset=utf-8','Content-Length: ' . strlen($data_json)));
                    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'POST');
                    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
                    curl_setopt($ch, CURLOPT_POSTFIELDS,$data_json);
                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                    $response  = curl_exec($ch);
                    curl_close($ch);

                    #$this->log->write('ODOO: Updated order status' . $this->session->data['dpd']['city_id']);

                }


            }

        }
    }

    public function orders() {

        $this->load->language('api/integrations');

        $this->load->model('account/integrations');


        $json = array();
        $this->session->data['api_id'] = 100;
        if(version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if(isset($api['api_id'])){
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }



        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {
            $this->load->model('checkout/order');
            $this->load->model('account/order');
            $this->load->model('catalog/product');
            $this->load->model('catalog/category');



            $date = '';
            if (isset($this->request->get['date'])) {
                $date = $this->request->get['date'];
            }

            $limit = 20000;
            if (isset($this->request->get['limit'])) {
                $limit = $this->request->get['limit'];
            }

            $orders = $this->model_account_integrations->getOrdersOdoo($date, $limit);

            $json_orders = [];
            foreach($orders as $key=>$value){
                $json_orders[$value["order_id"]] = $this->model_account_integrations->getOrderOdoo($value["order_id"]);
                $this->tax->unsetRates();
                $this->tax->setShippingAddress($json_orders[$value["order_id"]]['shipping_country_id'], $json_orders[$value["order_id"]]['shipping_zone_id']);
                $this->tax->setPaymentAddress($json_orders[$value["order_id"]]['payment_country_id'], $json_orders[$value["order_id"]]['payment_zone_id']);
                $this->tax->setStoreAddress($this->config->get('config_country_id'), $this->config->get('config_zone_id'));
                $json_orders[$value["order_id"]]["products"] = array();
                $tax_class_id = False;
                foreach($this->model_account_order->getOrderProducts($value["order_id"]) as $v1){

                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]] = $v1;
                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["options"] = $this->model_account_integrations->getOrderOptions($value["order_id"], $v1["order_product_id"]);
                    $product_info = $this->model_account_integrations->getProduct($v1["product_id"]);


                    if (isset($product_info["manufacturer"]))
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["manufacturer"] = $product_info["manufacturer"];
                    else
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["manufacturer"] = "";


                    $cat_ids = [];
                    foreach($this->model_catalog_product->getCategories($v1["product_id"]) as $category){
                        $cat_ids[] = $category["category_id"];
                        //break;
                    }

                    $category_id = count($cat_ids) ? max($cat_ids) : False;
                    if ($category_id){
                        $category_info = $this->model_catalog_category->getCategory($category_id);
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["category"] = $category_info["name"];
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["category_id"] = $category_id;
                    }else {
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["category"] = "Empty";
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["category_id"] = "";
                    }


                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["name"] = utf8_substr(trim(strip_tags(html_entity_decode(preg_replace("/<br\W*?\/>/", "\n", $product_info['name'] ? $product_info['name'] : $v1["name"]), ENT_QUOTES, 'UTF-8'))), 0);
                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["description"] = utf8_substr(trim(strip_tags(html_entity_decode(preg_replace("/<br\W*?\/>/", "\n", $product_info['description'] ? $product_info['description'] : $v1["name"]), ENT_QUOTES, 'UTF-8'))), 0);
                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["ean"] = $product_info['ean'];
                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["sku"] = $product_info['sku'];
                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["model"] = $product_info['model'] ? $product_info['model'] : $v1["name"];

                    $tax_class_id = $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]['tax_class_id'] = $product_info['tax_class_id'] ? $product_info['tax_class_id'] : '';


                    if (!$product_info['tax_class_id'] and $v1['tax']){

                        $totals = $this->model_account_order->getOrderTotals($value['order_id']);

                        foreach($totals as $tk=>$result)
                            if ($result["code"] == "tax")
                                $tax_class_id = $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]['tax_class_id'] = $product_info['tax_class_id'] = $this->model_account_integrations->getTaxClass($result["title"]);

                    }


                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]['price'] = $this->tax->calculate($v1["price"], $product_info['tax_class_id'], $this->config->get('config_tax'));
                    #$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]['price'] = $this->currency->format($json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]['price'], $this->config->get('config_currency'), '', false);


                    if (!empty($product_info['image']) && file_exists(DIR_IMAGE . $product_info['image']))
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["image"] = $product_info['image'];
                    else
                        $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["image"] = "";



                    #$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["tax_class_id"] = $product_info['tax_class_id'];
                    #if (! $tax_class_id)
                    #     $tax_class_id = $product_info['tax_class_id'];




                    $tax_rates = $this->tax->getRates($v1["price"], $tax_class_id);
                    $json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["rates"] = $tax_rates;


                }

                $totals = $this->model_account_order->getOrderTotals($value['order_id']);
                foreach($totals as $tk=>$result){
                    if ($result["code"] == "shipping"){
                        $taxes = explode(".", $json_orders[$value["order_id"]]['shipping_code']);
                        if (isset($taxes[0]) and $taxes[0] and $this->config->get('shipping_'.$taxes[0].'_tax_class_id'))
                            $tax_class_id = $this->config->get('shipping_'.$taxes[0].'_tax_class_id');
                        $totals[$tk]['value'] = $this->tax->calculate($result['value'], $tax_class_id, $this->config->get('config_tax'));
                        #$totals[$tk]['value'] = $this->currency->format($totals[$tk]['value'], $this->config->get('config_currency'), '', false);
                    }
                    if (!in_array($result["code"], array("shipping", "tax", "sub_total", "total")) ){
                        $totals[$tk]['value'] = $this->tax->calculate($result['value'], $tax_class_id, $this->config->get('config_tax'));
                        #$totals[$tk]['value'] = $this->currency->format($totals[$tk]['value'], $this->config->get('config_currency'), '', false);
                    }

                    if (!in_array($result["code"], array("tax")) ) {
                        $totals[$tk]['tax_class_id'] = $tax_class_id;
                        $tax_rates = $this->tax->getRates($result['value'], $tax_class_id);
                        $totals[$tk]["rates"] = $tax_rates;
                    }

                }

                $json_orders[$value["order_id"]]["totals"] = $totals;
                $json_orders[$value["order_id"]]["config_tax"] = $this->config->get('config_tax');

                
                $json_orders[$value["order_id"]]['histories'] = array();
                $results = $this->model_account_order->getOrderHistories($value["order_id"]);

                foreach ($results as $result) {
                    $json_orders[$value["order_id"]]['histories'][] = array(
                        'date_added' => date($this->language->get('date_format_short'), strtotime($result['date_added'])),
                        'status'     => $result['status'],
                        'comment'    => nl2br($result['comment'])
                    );
                }


            }



            $json['orders'] = $json_orders;

            $json['success'] = $this->language->get('text_success');


        }


        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }



    public function customergroups(){
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        $json = array();

        if (version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if (isset($api['api_id'])) {
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }


        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {
            $this->load->model('account/customer_group');

           



            $results = $this->model_account_customer_group->getCustomerGroups();

            $json['customergroups'] = $results;
            $json['success'] = $this->language->get('text_success');


        }

        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }

    public function customers(){
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        $json = array();

        if (version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if (isset($api['api_id'])) {
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }


        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {
            $limit = 50;
            if (isset($this->request->get['limit'])) {
                $limit = $this->request->get['limit'];
            }

            $page = 0;
            if (isset($this->request->get['page'])) {
                $page = $this->request->get['page'];
            }



            require('admin/model/customer/customer.php');

            $model_customer_customer = new ModelCustomerCustomer( $this->registry );
            
            $filter_data = array(
                'start'                    => $page * $limit,
                'limit'                    => $limit
            );



            $results = $model_customer_customer->getCustomers($filter_data);

            foreach ($results as $result) {
                $json[] = array(
                    'customer_id'       => $result['customer_id'],
                    'customer_group_id' => $result['customer_group_id'],
                    'name'              => strip_tags(html_entity_decode($result['name'], ENT_QUOTES, 'UTF-8')),
                    'customer_group'    => $result['customer_group'],
                    'firstname'         => $result['firstname'],
                    'lastname'          => $result['lastname'],
                    'email'             => $result['email'],
                    'telephone'         => $result['telephone'],
                    'custom_field'      => json_decode($result['custom_field'], true),
                    'address'           => $model_customer_customer->getAddresses($result['customer_id']),
                    'date_added' => $result['date_added'],
                );
            }


            

            $json['customers'] = $json;
            $json['success'] = $this->language->get('text_success');


        }

        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }

    public function update_order(){
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        $json = array();

        $this->session->data['api_id'] = "2";

        if (version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if (isset($api['api_id'])) {
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }


        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {

            $order_id = False;
            $order_status_id = False;
            if (isset($this->request->get['order_id']))
                $order_id = $this->request->get['order_id'];
            else{
                $json['error'] = $this->language->get('text_order_not_updated');
            }
            if (isset($this->request->get['order_status_id']))
                $order_status_id = $this->request->get['order_status_id'];
            else{
                $json['error'] = $this->language->get('text_order_not_updated');
            }

                if ($order_id and $order_status_id){
                $this->load->model('checkout/order');
                $order_info = $this->model_checkout_order->getOrder($order_id);
                if ($order_info["order_status_id"]  != $order_status_id) {
                    $this->model_checkout_order->addOrderHistory($order_id, $order_status_id, "odoo", false);
                }
                
                $json['success'] = sprintf($this->language->get('text_order_update_success'), "Order_id ". $order_id. " order_status_id:" . $order_status_id);
                
            }else{
                $json['error'] = $this->language->get('text_order_not_updated');
            }
        }

        $this->log->write('Odoo: update_order ' . $json['success']);
        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }


    public function update_product(){
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        $json = array();

        if (version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if (isset($api['api_id'])) {
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }


        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {

            $data = array();
            if (isset($this->request->get['price']))
                $data["price"] = $this->request->get['price'];

            if (isset($this->request->get['type'])){
                $data["subtract"] = $v['type']=="product" ? '1' : '0';
                $data["shipping"] = $v['type']=="product" ? '1' : '0';
            }
            if (isset($this->request->get['name']) and isset($this->request->get['description'])){

                $this->load->model('localisation/language');
                $languages = $this->model_localisation_language->getLanguages();
                
                
                foreach ($languages as $language) {
                    $description[$language['language_id']] = array(
                        'name' => $this->request->get["name"],
                        'description' => $this->request->get["description"],
                        'meta_title' => $this->request->get["name"],
                        'tag' => '',
                        'meta_description' => $this->request->get["description"],
                        'meta_keyword' => ''
                    );
                }
                
                $data['product_description'] = $description;
            }
            if (isset($this->request->get['quantity']))
                $data["quantity"] = $this->request->get['quantity'];
            if (isset($this->request->get['options']))
                $data["options"] = explode(",", $this->request->get['options']);
            if (isset($this->request->get['values']))
                $data["values"] = explode(",", $this->request->get['values']);

            if (isset($this->request->get['option_qty']))
                $data["option_qty"] = $this->request->get['option_qty'];

            $sql = array();
            foreach ($data as $key=>$value)
                if ( !in_array($key, array('options', 'values')))
                    $sql[] = sprintf("`%s`='%s'", $key, $value);
            if (isset($this->request->get['product_id'])){
                $this->model_account_integrations->editProduct($this->request->get['product_id'], $data);
                $json['success'] = sprintf($this->language->get('text_product_update_success'), "Product_id ". $this->request->get['product_id']. " " . implode(",", $sql));
            }else{
                $json['error'] = $this->language->get('text_product_not_updated');
            }
        }
        $this->log->write('Odoo: update_product ' . serilaize($json));
        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }
    public function categories(){

        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        $json = array();

        if (version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if (isset($api['api_id'])) {
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }


        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {
            $this->load->model('checkout/order');
            $this->load->model('account/order');
            $this->load->model('catalog/product');
            $this->load->model('catalog/category');
            $this->load->model('tool/image');


            $category_id = 0;
            if (isset($this->request->get['category_id'])) {
                $category_id = $this->request->get['category_id'];
            }

            //$results = $this->model_catalog_category->getCategories($category_id);
            $results = $this->model_account_integrations->getCategories($category_id);


            $json['categories'] = $results;

            $json['success'] = $this->language->get('text_success');


        }

        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }
    
    public function orderstatus() {
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');
        
        $json = array();

        if(version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if(isset($api['api_id'])){
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }
        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {

            //$this->load->model('localisation/order_status');

            $json['items'] = $this->model_account_integrations->getOrderStatuses();


            $json['success'] = $this->language->get('text_success');

        
        }
        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }

    public function products() {
        $this->load->language('api/integrations');
        $this->load->model('account/integrations');


        $json = array();

        if(version_compare(VERSION, '3.0.0.0', '<') == true) {
            if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
                $api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
                if(isset($api['api_id'])){
                    $this->session->data['api_id'] = (int)$api['api_id'];
                }
            }
        }



        if (!isset($this->session->data['api_id'])) {
            $json['error'] = $this->language->get('error_permission');
        } else {
            $this->load->model('checkout/order');
            $this->load->model('account/order');
            $this->load->model('catalog/product');
            $this->load->model('catalog/category');
            $this->load->model('tool/image');




            $page = 1;
            if (isset($this->request->get['page'])) {
                $page = $this->request->get['page'];
            }

            $limit = 100;
            if (isset($this->request->get['limit'])) {
                $limit = $this->request->get['limit'];
            }

            $data['products'] = array();

            $filter_data = array(
                'start'              => ($page - 1) * $limit,
                'limit'              => $limit
            );

            $results = $this->model_catalog_product->getProducts($filter_data);
            foreach ($results as $key=>$result) {
                $cat_ids = [];
                foreach($this->model_catalog_product->getCategories($result["product_id"]) as $category)
                    $cat_ids[] = $category["category_id"];
                $results[$key]["category_id"] = count($cat_ids) ? max($cat_ids) : False;

                $category_id = count($cat_ids) ? max($cat_ids) : False;
                if ($category_id){
                    $category_info = $this->model_catalog_category->getCategory($category_id);
                    $results[$key]["category"] = $category_info["name"];
                }else {
                    $results[$key]["category"] = "Empty";
                }

                if (!empty($result['image']) && file_exists(DIR_IMAGE . $result['image']))
                    $results[$key]["image"] = $result['image'];
                else
                    $results[$key]["image"] = "";

                $results[$key]["name"] = utf8_substr(trim(strip_tags(html_entity_decode(preg_replace("/<br\W*?\/>/", "\n", $results[$key]['name']), ENT_QUOTES, 'UTF-8'))), 0);
                $results[$key]["description"] = utf8_substr(trim(strip_tags(html_entity_decode(preg_replace("/<br\W*?\/>/", "\n", $results[$key]['description']), ENT_QUOTES, 'UTF-8'))), 0);

                // discounts all
                $results[$key]["discounts"] = $this->model_catalog_product->getProductDiscounts($result['product_id']);
                $results[$key]["specials"] = $this->model_account_integrations->getProductSpecials($result['product_id']);

                foreach($results[$key]["discounts"] as $k=>$v){
                    $results[$key]["discounts"][$k]["price"] = $this->tax->calculate($v['price'], $result['tax_class_id'], $this->config->get('config_tax'));
                }
                foreach($results[$key]["specials"] as $k=>$v){
                    $results[$key]["specials"][$k]["price"] = $this->tax->calculate($v['price'], $result['tax_class_id'], $this->config->get('config_tax'));
                }

                $results[$key]["options"] = $this->model_catalog_product->getProductOptions($result['product_id']);
                $results[$key]["price"] = $this->tax->calculate($result['price'], $result['tax_class_id'], $this->config->get('config_tax'));
                $results[$key]["special"] = $this->tax->calculate($result['special'], $result['tax_class_id'], $this->config->get('config_tax'));

            }
            $json['products'] = $results;

            $json['success'] = $this->language->get('text_success');

        }



        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));



    }





}