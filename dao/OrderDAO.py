from dao.BaseDAO import BaseDAO
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Union

class OrderDAO(BaseDAO):
    """
    Data Access Object for order management, including main orders, sub-orders, and order items.
    Handles order creation, query, status update, cancellation, and item management.
    """

    def __init__(self):
        super().__init__()

    def create_order(self, customer_id: str, shipping_address: str, sub_orders_data: List[Dict]) -> Optional[str]:
        """
        Create main order, sub-orders, and order items in a single transaction.
        Ensures data consistency and atomicity for the entire order creation process.
        
        Args:
            customer_id: ID of the customer placing the order
            shipping_address: Shipping address for the order
            sub_orders_data: List of sub-order data grouped by merchant
            
        sub_orders_data structure example:
        [
            {
                'merchant_id': 'm1',
                'items': [
                    {'product_id': 'p1', 'quantity': 2, 'price_per_unit': 10.0},
                    {'product_id': 'p2', 'quantity': 1, 'price_per_unit': 20.0}
                ]
            }
        ]
        
        Returns:
            order_id if successful, None otherwise
        """
        order_id = str(uuid.uuid4())
        order_date = datetime.now()
        
        # Calculate overall total amount first
        total_amount = 0.0
        for sub_order_data in sub_orders_data:
            items = sub_order_data['items']
            for item in items:
                total_amount += float(item['quantity']) * float(item['price_per_unit'])

        actual_ops = []

        # Step 1: Insert main order (parent table first for foreign key constraints)
        order_sql = """
            INSERT INTO orders (order_id, customer_id, order_date, total_amount, status, shipping_address, payment_status)
            VALUES (%s, %s, %s, %s, 'pending', %s, 'unpaid')
        """
        actual_ops.append((order_sql, (order_id, customer_id, order_date, total_amount, shipping_address)))

        # Step 2: Process each sub-order and its items
        for sub_order_data in sub_orders_data:
            sub_order_id = str(uuid.uuid4())
            merchant_id = sub_order_data['merchant_id']
            items = sub_order_data['items']

            # Calculate sub-total for current sub-order
            sub_total = 0.0
            for item in items:
                sub_total += float(item['quantity']) * float(item['price_per_unit'])

            # Insert sub-order
            sub_order_sql = """
                INSERT INTO sub_orders (sub_order_id, order_id, merchant_id, sub_total_amount, status, shipping_status)
                VALUES (%s, %s, %s, %s, 'pending', 'pending')
            """
            actual_ops.append((sub_order_sql, (sub_order_id, order_id, merchant_id, sub_total)))

            # Insert each order item
            for item in items:
                order_item_id = str(uuid.uuid4())
                product_id = item['product_id']
                quantity = item['quantity']
                price_per_unit = item['price_per_unit']
                item_total = quantity * price_per_unit

                item_sql = """
                    INSERT INTO order_items (order_item_id, sub_order_id, product_id, quantity, price_per_unit, total_price, item_status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active')
                """
                actual_ops.append((item_sql, (order_item_id, sub_order_id, product_id, quantity, price_per_unit, item_total)))

                # Update product stock (decrease)
                stock_sql = "UPDATE Product SET Stock = Stock - %s WHERE Product_ID = %s"
                actual_ops.append((stock_sql, (quantity, product_id)))

        # Execute all operations in one transaction
        success = self.tx_manager.execute_transaction(actual_ops)
        return order_id if success else None

    def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """
        Retrieve main order details by order ID.
        
        Args:
            order_id: ID of the main order
            
        Returns:
            Order dict if found, None otherwise
        """
        sql = "SELECT * FROM orders WHERE order_id = %s"
        return self.executor.execute_query_one(sql, (order_id,))

    def get_sub_orders_by_order_id(self, order_id: str) -> List[Dict]:
        """
        Get all sub-orders belonging to a main order.
        
        Args:
            order_id: ID of the main order
            
        Returns:
            List of sub-order dicts
        """
        sql = "SELECT * FROM sub_orders WHERE order_id = %s"
        return self.executor.execute_query(sql, (order_id,))

    def get_order_items_by_sub_order_id(self, sub_order_id: str) -> List[Dict]:
        """
        Get all order items under a specific sub-order, including product details.
        
        Args:
            sub_order_id: ID of the sub-order
            
        Returns:
            List of order item dicts with product names and images
        """
        sql = """
            SELECT oi.*, p.Name as product_name, p.Image_URL as product_image
            FROM order_items oi
            JOIN Product p ON oi.product_id = p.Product_ID
            WHERE oi.sub_order_id = %s
        """
        return self.executor.execute_query(sql, (sub_order_id,))

    def get_full_order_details(self, order_id: str) -> Optional[Dict]:
        """
        Get complete order information including main order, sub-orders, and all items.
        
        Args:
            order_id: ID of the main order
            
        Returns:
            Nested dict with full order details, None if order not found
        """
        order = self.get_order_by_id(order_id)
        if not order:
            return None

        # order is already a dict because of DictCursor
        order_details = order
        sub_orders = self.get_sub_orders_by_order_id(order_id)
        order_details['sub_orders'] = []

        if sub_orders:
            for sub_order in sub_orders:
                # Use a name that doesn't conflict with dict.items()
                sub_order['order_items'] = self.get_order_items_by_sub_order_id(sub_order['sub_order_id'])
                order_details['sub_orders'].append(sub_order)

        return order_details

    def get_customer_orders(self, customer_id: str) -> List[Dict]:
        """
        Get all orders placed by a specific customer, sorted by creation time descending.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            List of order dicts
        """
        sql = "SELECT * FROM orders WHERE customer_id = %s ORDER BY order_date DESC"
        return self.executor.execute_query(sql, (customer_id,))

    def get_vendor_sub_orders(self, merchant_id: str) -> List[Dict]:
        """
        Get all sub-orders belonging to a specific merchant, including item count and customer name.
        
        Args:
            merchant_id: ID of the merchant/vendor
            
        Returns:
            List of sub-order dicts with an additional 'item_count' and 'customer_name' fields
        """
        sql = """
            SELECT so.*, 
                   (SELECT COUNT(*) FROM order_items WHERE sub_order_id = so.sub_order_id) as item_count,
                   u.Username as customer_name
            FROM sub_orders so
            JOIN orders o ON so.order_id = o.order_id
            JOIN UserAccount u ON o.customer_id = u.User_ID
            WHERE so.merchant_id = %s 
            ORDER BY so.created_at DESC
        """
        return self.executor.execute_query(sql, (merchant_id,))

    def update_order_status(self, order_id: str, status: str) -> int:
        """
        Update the status of a main order.
        
        Args:
            order_id: ID of the main order
            status: New status value
            
        Returns:
            Number of rows affected
        """
        sql = "UPDATE orders SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s"
        return self.executor.execute_update(sql, (status, order_id))

    def update_sub_order_status(self, sub_order_id: str, status: str) -> int:
        """
        Update the status of a sub-order.
        
        Args:
            sub_order_id: ID of the sub-order
            status: New status value
            
        Returns:
            Number of rows affected
        """
        sql = "UPDATE sub_orders SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE sub_order_id = %s"
        return self.executor.execute_update(sql, (status, sub_order_id))

    def update_shipping_status(self, sub_order_id: str, shipping_status: str) -> int:
        """
        Update shipping status for a sub-order.
        
        Args:
            sub_order_id: ID of the sub-order
            shipping_status: New shipping status
            
        Returns:
            Number of rows affected
        """
        sql = "UPDATE sub_orders SET shipping_status = %s, updated_at = CURRENT_TIMESTAMP WHERE sub_order_id = %s"
        return self.executor.execute_update(sql, (shipping_status, sub_order_id))

    def update_payment_status(self, order_id: str, payment_status: str) -> int:
        """
        Update payment status of a main order.
        
        Args:
            order_id: ID of the main order
            payment_status: New payment status
            
        Returns:
            Number of rows affected
        """
        sql = "UPDATE orders SET payment_status = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s"
        return self.executor.execute_update(sql, (payment_status, order_id))

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an entire main order and all its sub-orders.
        Only allowed if no sub-order has been shipped.
        
        Args:
            order_id: ID of the main order
            
        Returns:
            True if cancellation succeeded, False otherwise
        """
        # Check if any sub-order has been shipped
        sub_orders = self.get_sub_orders_by_order_id(order_id)
        for so in sub_orders:
            if so['shipping_status'] != 'pending':
                return False

        # Transaction: cancel order, sub-orders, mark items as removed, and restore stock
        operations = [
            ("UPDATE orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s", (order_id,)),
            ("UPDATE sub_orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s", (order_id,)),
            ("UPDATE order_items oi JOIN sub_orders so ON oi.sub_order_id = so.sub_order_id "
             "SET oi.item_status = 'removed', oi.updated_at = CURRENT_TIMESTAMP WHERE so.order_id = %s", (order_id,)),
            # Restore product stock
            ("UPDATE Product p JOIN order_items oi ON p.Product_ID = oi.product_id "
             "JOIN sub_orders so ON oi.sub_order_id = so.sub_order_id "
             "SET p.Stock = p.Stock + oi.quantity WHERE so.order_id = %s AND oi.item_status = 'active'", (order_id,))
        ]

        return self.tx_manager.execute_transaction(operations)

    def remove_order_item(self, order_item_id: str) -> bool:
        """
        Remove a single item from an order and update total amounts.
        
        Args:
            order_item_id: ID of the order item to remove
            
        Returns:
            True if successful, False otherwise
        """
        # Get item details
        item_sql = "SELECT * FROM order_items WHERE order_item_id = %s"
        item = self.executor.execute_query_one(item_sql, (order_item_id,))
        
        if not item or item['item_status'] == 'removed':
            return False

        sub_order_id = item['sub_order_id']
        item_price = item['total_price']

        # Get sub-order to check shipping status
        sub_order_sql = "SELECT order_id, shipping_status FROM sub_orders WHERE sub_order_id = %s"
        sub_order = self.executor.execute_query_one(sub_order_sql, (sub_order_id,))
        
        if not sub_order or sub_order['shipping_status'] != 'pending':
            return False

        order_id = sub_order['order_id']

        # Update item status, adjust totals, and restore product stock
        operations = [
            ("UPDATE order_items SET item_status = 'removed', updated_at = CURRENT_TIMESTAMP WHERE order_item_id = %s",
             (order_item_id,)),
            ("UPDATE sub_orders SET sub_total_amount = sub_total_amount - %s, updated_at = CURRENT_TIMESTAMP WHERE sub_order_id = %s",
             (item_price, sub_order_id)),
            ("UPDATE orders SET total_amount = total_amount - %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
             (item_price, order_id)),
            ("UPDATE Product SET Stock = Stock + %s WHERE Product_ID = %s",
             (item['quantity'], item['product_id'])),
            # Update sub-order status to cancelled if no active items remain
            ("UPDATE sub_orders SET status = 'cancelled' WHERE sub_order_id = %s AND NOT EXISTS (SELECT 1 FROM order_items WHERE sub_order_id = %s AND item_status = 'active')",
             (sub_order_id, sub_order_id)),
            # Update order status to cancelled if no active sub-orders remain
            ("UPDATE orders SET status = 'cancelled' WHERE order_id = %s AND NOT EXISTS (SELECT 1 FROM sub_orders WHERE order_id = %s AND status != 'cancelled')",
             (order_id, order_id))
        ]

        return self.tx_manager.execute_transaction(operations)
