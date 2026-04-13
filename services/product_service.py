from dao.ProductDAO import ProductDAO
from dao.TagDAO import TagDAO

class ProductService:
    def __init__(self):
        self.product_dao = ProductDAO()
        self.tag_dao = TagDAO()

    def list_public_products(self, **kwargs):
        return self.product_dao.list_public_products(**kwargs)

    def count_public_products(self, **kwargs):
        return self.product_dao.count_public_products(**kwargs)

    def get_public_product_detail(self, product_id):
        return self.product_dao.get_public_product_detail(product_id)

    def get_all_categories(self):
        return self.product_dao.get_all_categories()

    def get_popular_tags(self, limit=20):
        return self.tag_dao.get_popular_tags(limit)
