try:
    from dao.BaseDAO import BaseDAO
except ImportError:
    from BaseDAO import BaseDAO


class CustomerDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    # Customer profile
    def get_customer_profile(self, customer_id):
        sql = """
            SELECT ua.User_ID,ua.Username,ua.Phone_number,ua.Role,c.Nick_name,c.Address
            FROM Customer c,UserAccount ua
            WHERE c.User_ID = ua.User_ID AND c.User_ID = %s;
        """
        params = (customer_id,)
        return self.executor.execute_query_one(sql, params)

    def update_customer_profile(self, customer_id, nickname=None, address=None, phone_number=None):
        affected = 0

        customer_updates = []
        customer_params = []
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

        if phone_number is not None:
            sql = "UPDATE UserAccount SET Phone_number = %s WHERE User_ID = %s"
            params = (phone_number, customer_id)
            affected += self.executor.execute_update(sql, params)

        return affected
    # Product browsing
    def get_all_products(self, keyword=None, vendor_id=None, tag_id=None):
        sql = """
            SELECT DISTINCT p.*
            FROM Product p
            LEFT JOIN Tagging tg ON p.Product_ID = tg.Product_ID
            WHERE 1=1
        """
        params = []

        if keyword:
            sql += " AND p.Name LIKE %s"
            params.append(f"%{keyword}%")

        if vendor_id is not None:
            sql += " AND p.Vendor_ID = %s"
            params.append(vendor_id)

        if tag_id is not None:
            sql += " AND tg.Tag_ID = %s"
            params.append(tag_id)

        return self.executor.execute_query(sql, tuple(params))

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

    def get_vendor_by_id(self, vendor_id):
        sql = "SELECT * FROM Vendor WHERE Vendor_ID = %s"
        params = (vendor_id,)
        return self.executor.execute_query_one(sql, params)

    # Inventory
    def get_product_stock(self, product_id):
        sql = "SELECT Stock FROM Product WHERE Product_ID = %s"
        params = (product_id,)
        return self.executor.execute_query_one(sql, params)

    def decrease_product_stock(self, product_id, quantity):
        sql = """
            UPDATE Product
            SET Stock = Stock - %s
            WHERE Product_ID = %s AND Stock >= %s
        """
        params = (quantity, product_id, quantity)
        return self.executor.execute_update(sql, params)

    def restore_product_stock(self, product_id, quantity):
        sql = "UPDATE Product SET Stock = Stock + %s WHERE Product_ID = %s"
        params = (quantity, product_id)
        return self.executor.execute_update(sql, params)

    # Order
    def create_order(self, order_id, customer_id, order_date, status, total_payment):
        sql = """
            INSERT INTO `Order` (Order_ID, Customer_ID, Order_Date, Status, Total_Payment)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (order_id, customer_id, order_date, status, total_payment)
        return self.executor.execute_update(sql, params)

    def get_orders_by_customer(self, customer_id):
        sql = """
            SELECT *
            FROM `Order`
            WHERE Customer_ID = %s
            ORDER BY Order_Date DESC
        """
        params = (customer_id,)
        return self.executor.execute_query(sql, params)

    def get_order_by_id(self, order_id, customer_id=None):
        sql = "SELECT * FROM `Order` WHERE Order_ID = %s"
        params = [order_id]
        if customer_id is not None:
            sql += " AND Customer_ID = %s"
            params.append(customer_id)
        return self.executor.execute_query_one(sql, tuple(params))

    def cancel_order(self, order_id, customer_id):
        sql = """
            UPDATE `Order`
            SET Status = 'Cancelled'
            WHERE Order_ID = %s AND Customer_ID = %s
        """
        params = (order_id, customer_id)
        return self.executor.execute_update(sql, params)

    # Transaction
    def create_transaction(self, transaction_id, order_id, vendor_id, payment_amount):
        sql = """
            INSERT INTO `Transaction` (Transaction_ID, Order_ID, Vendor_ID, Payment_Amount)
            VALUES (%s, %s, %s, %s)
        """
        params = (transaction_id, order_id, vendor_id, payment_amount)
        return self.executor.execute_update(sql, params)

    def get_transactions_by_order_id(self, order_id):
        sql = """
            SELECT *
            FROM `Transaction`
            WHERE Order_ID = %s
            ORDER BY Transaction_ID
        """
        params = (order_id,)
        return self.executor.execute_query(sql, params)

    def get_transaction_by_id(self, transaction_id):
        sql = "SELECT * FROM `Transaction` WHERE Transaction_ID = %s"
        params = (transaction_id,)
        return self.executor.execute_query_one(sql, params)

    # Order items
    def create_order_item(self, transaction_id, product_id, quantity, price):
        sql = """
            INSERT INTO Order_Items (Transaction_ID, Product_ID, Quantity, Price)
            VALUES (%s, %s, %s, %s)
        """
        params = (transaction_id, product_id, quantity, price)
        return self.executor.execute_update(sql, params)

    def get_order_items_by_transaction_id(self, transaction_id):
        sql = """
            SELECT oi.*, p.Name AS Product_Name, p.Image_URL
            FROM Order_Items oi
            LEFT JOIN Product p ON oi.Product_ID = p.Product_ID
            WHERE oi.Transaction_ID = %s
        """
        params = (transaction_id,)
        return self.executor.execute_query(sql, params)

    def remove_order_item(self, transaction_id, product_id):
        sql = "DELETE FROM Order_Items WHERE Transaction_ID = %s AND Product_ID = %s"
        params = (transaction_id, product_id)
        return self.executor.execute_update(sql, params)

    # Rating
    def get_rating(self, customer_id, vendor_id):
        sql = "SELECT * FROM Rating WHERE Customer_ID = %s AND Vendor_ID = %s"
        params = (customer_id, vendor_id)
        return self.executor.execute_query_one(sql, params)

    def add_rating(self, customer_id, vendor_id, score):
        sql = "INSERT INTO Rating (Customer_ID, Vendor_ID, Score) VALUES (%s, %s, %s)"
        params = (customer_id, vendor_id, score)
        return self.executor.execute_update(sql, params)

    def update_rating(self, customer_id, vendor_id, score):
        sql = "UPDATE Rating SET Score = %s WHERE Customer_ID = %s AND Vendor_ID = %s"
        params = (score, customer_id, vendor_id)
        return self.executor.execute_update(sql, params)

    def get_ratings_by_customer(self, customer_id):
        sql = """
            SELECT r.*, v.Store_Name
            FROM Rating r
            LEFT JOIN Vendor v ON r.Vendor_ID = v.Vendor_ID
            WHERE r.Customer_ID = %s
        """
        params = (customer_id,)
        return self.executor.execute_query(sql, params)
