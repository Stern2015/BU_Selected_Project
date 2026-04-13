from dao.BaseDAO import BaseDAO

import json

class CustomerDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    # Customer profile
    def get_customer_profile(self, customer_id):
        sql = """
            SELECT User_ID, Phone_number, Nick_name, Address, Order_History
            FROM Customer
            WHERE User_ID = %s
        """
        params = (customer_id,)
        return self.executor.execute_query_one(sql, params)

    def update_customer_profile(self, customer_id, nickname=None, address=None, phone_number=None):
        affected = 0

        customer_updates = []
        customer_params = []
        if phone_number is not None:
            customer_updates.append("Phone_number = %s")
            customer_params.append(phone_number)
        if nickname is not None:
            customer_updates.append("Nick_name = %s")
            customer_params.append(nickname)
        if address is not None:
            customer_updates.append("Address = %s")
            customer_params.append(address)

        if customer_updates:
            sql = f"UPDATE Customer SET {', '.join(customer_updates)} WHERE User_ID = %s"
            customer_params.append(customer_id)
            affected += self.executor.execute_update(sql, tuple(customer_params))

        return affected

    # Product browsing
    def get_all_products(self, keyword=None, vendor_id=None, tag_id=None):
        sql = "SELECT DISTINCT p.* FROM Product p"
        params = []

        if tag_id is not None:
            sql += " JOIN Tagging tg ON p.Product_ID = tg.Product_ID"
            sql += " WHERE tg.Tag_ID = %s"
            params.append(tag_id)

            if keyword:
                sql += " AND p.Name LIKE %s"
                params.append(f"%{keyword}%")
            if vendor_id is not None:
                sql += " AND p.Vendor_ID = %s"
                params.append(vendor_id)
        else:
            if keyword:
                sql += " WHERE p.Name LIKE %s"
                params.append(f"%{keyword}%")

                if vendor_id is not None:
                    sql += " AND p.Vendor_ID = %s"
                    params.append(vendor_id)
            else:
                if vendor_id is not None:
                    sql += " WHERE p.Vendor_ID = %s"
                    params.append(vendor_id)

        return self.executor.execute_query(sql, tuple(params) if params else None)

    def get_product_by_id(self, product_id):
        sql = """
            SELECT p.*, v.Store_Name, v.Location AS Vendor_Location
            FROM Product p
            LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
            WHERE p.Product_ID = %s
        """
        params = (product_id,)
        return self.executor.execute_query_one(sql, params)

    def get_product_tags(self, product_id):
        sql = """
            SELECT t.Tag_ID, t.Name, tg.Position
            FROM Tag t
            INNER JOIN Tagging tg ON t.Tag_ID = tg.Tag_ID
            WHERE tg.Product_ID = %s
            ORDER BY tg.Position
        """
        params = (product_id,)
        return self.executor.execute_query(sql, params)

    def get_all_tags(self):
        sql = "SELECT Tag_ID, Name FROM Tag ORDER BY Name"
        return self.executor.execute_query(sql)

    # Order
    def get_order_history(self, customer_id):
        sql = "SELECT Order_History FROM Customer WHERE User_ID = %s"
        result = self.executor.execute_query_one(sql, (customer_id,))
        if not result or not result.get("Order_History"):
            return []
        return json.loads(result["Order_History"])

    def save_order_history(self, customer_id, orders):
        sql = "UPDATE Customer SET Order_History = %s WHERE User_ID = %s"
        return self.executor.execute_update(sql, (json.dumps(orders, ensure_ascii=False), customer_id))

    def create_order(self, order_id, customer_id, order_date, status, total_payment):
        sql = """
            INSERT INTO `Order`
                (Order_ID, Customer_ID, Order_Date, Status, Total_Payment)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.executor.execute_update(
        sql, (order_id, customer_id, order_date, status, total_payment)
    )

    def get_orders_by_customer(self, customer_id):
        return self.get_order_history(customer_id)

    def cancel_order(self, order_id, customer_id):
        orders = self.get_order_history(customer_id)
        updated = False
        for order in orders:
            if str(order.get("Order_ID")) == str(order_id):
                order["Status"] = "Cancelled"
                updated = True
        if not updated:
            return 0
        return self.save_order_history(customer_id, orders)

# Transaction
    def create_transaction(self, transaction_id, order_id, vendor_id, payment_amount):
        sql = """
            INSERT INTO `Transaction`
                (Transaction_ID, Order_ID, Vendor_ID, Payment_Amount)
            VALUES (%s, %s, %s, %s)
     """
        return self.executor.execute_update(
            sql, (transaction_id, order_id, vendor_id, payment_amount)
    )

    def get_transactions_by_order_id(self, order_id):
        sql = "SELECT * FROM `Transaction` WHERE Order_ID = %s"
        return self.executor.execute_query(sql, (order_id,))

    def get_transaction_by_id(self, transaction_id):
        sql = "SELECT * FROM `Transaction` WHERE Transaction_ID = %s"
        return self.executor.execute_query_one(sql, (transaction_id,))

# Order items
    def create_order_item(self, transaction_id, product_id, quantity, price):
        sql = """
            INSERT INTO Order_Items
                (Transaction_ID, Product_ID, Quantity, Price)
            VALUES (%s, %s, %s, %s)
        """
        return self.executor.execute_update(
        sql, (transaction_id, product_id, quantity, price)
    )

    def get_order_items_by_transaction_id(self, transaction_id):
        sql = "SELECT * FROM Order_Items WHERE Transaction_ID = %s"
        return self.executor.execute_query(sql, (transaction_id,))

    def remove_order_item(self, transaction_id, product_id):
        sql = "DELETE FROM Order_Items WHERE Transaction_ID = %s AND Product_ID = %s"
        return self.executor.execute_update(sql, (transaction_id, product_id))

    # Rating
    def get_rating(self, customer_id, vendor_id):
        sql = "SELECT * FROM Rating WHERE Customer_ID = %s AND Vendor_ID = %s"
        params = (customer_id, vendor_id)
        return self.executor.execute_query_one(sql, params)

    def set_rating(self, customer_id, vendor_id, score):
        sql = """
            INSERT INTO Rating (Customer_ID, Vendor_ID, Score)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE Score = %s
        """
        params = (customer_id, vendor_id, score, score)
        return self.executor.execute_update(sql, params)

    def get_rating_from_customer(self, customer_id):
        sql = """
            SELECT r.*, v.Store_Name
            FROM Rating r
            LEFT JOIN Vendor v ON r.Vendor_ID = v.Vendor_ID
            WHERE r.Customer_ID = %s
        """
        params = (customer_id,)
        return self.executor.execute_query(sql, params)
