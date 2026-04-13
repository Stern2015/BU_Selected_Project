"""
Order & Transaction Service
Handles business logic related to orders and transactions
"""
import uuid
from datetime import datetime
from dao.CustomerDAO import CustomerDAO
from driver.sql_executor import SQL_Executor

class OrderService:
    def __init__(self):
        self.dao = CustomerDAO()
        self.executor = SQL_Executor()

    def create_order(self, customer_id, cart_items, get_product_fn):
        """
        结账核心逻辑：
        1. 生成主订单
        2. 按商户拆分，每个商户生成一条 Transaction
        3. 每个商品生成一条 Order_Items
        返回 order_id
        """
        order_id = 'ORD-' + str(uuid.uuid4())[:8].upper()
        total_amount = 0
        sub_orders_map = {}

        # 按商户分组，计算总金额
        for item in cart_items:
            p = get_product_fn(item['product_id'])
            if not p:
                continue
            total_amount += p['price'] * item['quantity']
            vid = p['vendor_id']
            if vid not in sub_orders_map:
                sub_orders_map[vid] = []
            sub_orders_map[vid].append({
                'product_id': p['id'],
                'quantity': item['quantity'],
                'price': p['price']
            })

        # 写主订单到数据库
        self._create_order_db(order_id, customer_id, total_amount)

        # 为每个商户写 Transaction + Order_Items
        for vid, items in sub_orders_map.items():
            txn_id = 'TXN-' + str(uuid.uuid4())[:8].upper()
            txn_amount = sum(i['price'] * i['quantity'] for i in items)
            self._create_transaction_db(txn_id, order_id, vid, txn_amount)
            for item in items:
                self._create_order_item_db(txn_id, item['product_id'],
                                           item['quantity'], item['price'])

        return order_id, total_amount, sub_orders_map

    def _create_order_db(self, order_id, customer_id, total_payment):
        sql = """
            INSERT INTO `Order`
                (Order_ID, Customer_ID, Order_Date, Status, Total_Payment)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.executor.execute_update(
            sql, (order_id, customer_id, datetime.now(), 'Pending', total_payment)
        )

    def _create_transaction_db(self, txn_id, order_id, vendor_id, amount):
        sql = """
            INSERT INTO `Transaction`
                (Transaction_ID, Order_ID, Vendor_ID, Payment_Amount)
            VALUES (%s, %s, %s, %s)
        """
        self.executor.execute_update(sql, (txn_id, order_id, vendor_id, amount))

    def _create_order_item_db(self, txn_id, product_id, quantity, price):
        sql = """
            INSERT INTO Order_Items
                (Transaction_ID, Product_ID, Quantity, Price)
            VALUES (%s, %s, %s, %s)
        """
        self.executor.execute_update(sql, (txn_id, product_id, quantity, price))

    def get_transactions_by_order(self, order_id):
        sql = "SELECT * FROM `Transaction` WHERE Order_ID = %s"
        return self.executor.execute_query(sql, (order_id,))

    def get_items_by_transaction(self, transaction_id):
        sql = """
            SELECT oi.*, p.Name, p.Image_URL
            FROM Order_Items oi
            JOIN Product p ON oi.Product_ID = p.Product_ID
            WHERE oi.Transaction_ID = %s
        """
        return self.executor.execute_query(sql, (transaction_id,))