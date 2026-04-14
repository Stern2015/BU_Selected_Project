"""
Order & Transaction Service
Handles business logic related to orders and transactions
"""
from dao.OrderDAO import OrderDAO
from typing import List, Dict, Optional, Union

class OrderService:
    def __init__(self):
        self.order_dao = OrderDAO()

    def create_order(self, customer_id: str, shipping_address: str, cart_items: List[Dict], get_product_fn):
        
        # Group items by merchant
        merchant_items = {}
        for item in cart_items:
            product = get_product_fn(item['product_id'])
            if not product:
                continue
            
            merchant_id = product['vendor_id']
            if merchant_id not in merchant_items:
                merchant_items[merchant_id] = []
            
            merchant_items[merchant_id].append({
                'product_id': item['product_id'],
                'quantity': item['quantity'],
                'price_per_unit': float(product['price'])
            })
        
        # Format for OrderDAO
        sub_orders_data = []
        for merchant_id, items in merchant_items.items():
            sub_orders_data.append({
                'merchant_id': merchant_id,
                'items': items
            })
        
        if not sub_orders_data:
            return None
            
        return self.order_dao.create_order(customer_id, shipping_address, sub_orders_data)

    def get_customer_orders(self, customer_id: str):

        return self.order_dao.get_customer_orders(customer_id)

    def get_order_details(self, order_id: str):

        return self.order_dao.get_full_order_details(order_id)

    def cancel_order(self, order_id: str):

        return self.order_dao.cancel_order(order_id)

    def remove_item_from_order(self, order_item_id: str):

        return self.order_dao.remove_order_item(order_item_id)

    def get_vendor_orders(self, vendor_id: str):

        return self.order_dao.get_vendor_sub_orders(vendor_id)
