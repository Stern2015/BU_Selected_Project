try:
    from dao.BaseDAO import BaseDAO
except ImportError:
    from BaseDAO import BaseDAO


class CustomerDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    # Customer profile
    def get_customer_profile(self, customer_id):
        pass

    # Product browsing
    def get_all_products(self, keyword=None, vendor_id=None, tag_id=None):
        pass

    def get_product_by_id(self, product_id):
        pass

    def get_product_tags(self, product_id):
        pass

    def get_all_tags(self):
        pass

    def get_vendor_by_id(self, vendor_id):
        pass

    # Inventory
    def get_product_stock(self, product_id):
        pass

    def decrease_product_stock(self, product_id, quantity):
        pass

    def restore_product_stock(self, product_id, quantity):
        pass

    # Order
    def create_order(self, order_id, customer_id, order_date, status, total_payment):
        pass

    def get_orders_by_customer(self, customer_id):
        pass

    def get_order_by_id(self, order_id, customer_id=None):
        pass

    def cancel_order(self, order_id, customer_id):
        pass

    # Transaction
    def create_transaction(self, transaction_id, order_id, vendor_id, payment_amount):
        pass

    def get_transactions_by_order_id(self, order_id):
        pass

    def get_transaction_by_id(self, transaction_id):
        pass

    # Order items
    def create_order_item(self, transaction_id, product_id, quantity, price):
        pass

    def get_order_items_by_transaction_id(self, transaction_id):
        pass

    def remove_order_item(self, transaction_id, product_id):
        pass

    # Rating
    def get_rating(self, customer_id, vendor_id):
        pass

    def add_rating(self, customer_id, vendor_id, score):
        pass

    def update_rating(self, customer_id, vendor_id, score):
        pass

    def get_ratings_by_customer(self, customer_id):
        pass
