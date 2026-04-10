"""
Product DAO
Handles product data access
"""

# Since we are using in-memory database, create a simple BaseDAO mock
class MockBaseDAO:
    def __init__(self):
        self.executor = MockSQLExecutor()
        self.tx_manager = MockTransactionManager()

class MockSQLExecutor:
    def execute_query_one(self, sql, params):
        return None

    def execute_query(self, sql, params):
        return []

    def execute_update(self, sql, params):
        return 0

class MockTransactionManager:
    def begin_transaction(self):
        pass

    def commit_transaction(self):
        pass

    def rollback_transaction(self):
        pass

BaseDAO = MockBaseDAO


class ProductDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    # Basic product operations
    def get_product_by_id(self, product_id):
        """Get product details by ID"""
        sql = """
            SELECT p.*, v.Store_Name, v.Location AS Vendor_Location
            FROM Product p
            LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
            WHERE p.Product_ID = %s AND p.Status != 'Inactive'
        """
        params = (product_id,)
        return self.executor.execute_query_one(sql, params)

    def get_products_by_vendor(self, vendor_id, status=None, limit=None, offset=0):
        """Get product list by vendor"""
        sql = """
            SELECT * FROM Product
            WHERE Vendor_ID = %s
        """
        params = [vendor_id]

        if status:
            sql += " AND Status = %s"
            params.append(status)

        sql += " ORDER BY Created_At DESC"

        if limit:
            sql += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

        return self.executor.execute_query(sql, tuple(params))

    def get_all_products(self, keyword=None, category=None, vendor_id=None,
                        min_price=None, max_price=None, status='Active',
                        limit=50, offset=0):
        """Get all products (supports search and filtering)"""
        sql = """
            SELECT p.*, v.Store_Name
            FROM Product p
            LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
            WHERE p.Status = %s AND v.Status = 'Active'
        """
        params = [status]

        if keyword:
            sql += " AND (p.Name LIKE %s OR p.Description LIKE %s)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if category:
            sql += " AND p.Category = %s"
            params.append(category)

        if vendor_id:
            sql += " AND p.Vendor_ID = %s"
            params.append(vendor_id)

        if min_price is not None:
            sql += " AND p.Price >= %s"
            params.append(min_price)

        if max_price is not None:
            sql += " AND p.Price <= %s"
            params.append(max_price)

        sql += " ORDER BY p.Created_At DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return self.executor.execute_query(sql, tuple(params))

    def count_products(self, vendor_id=None, status='Active'):
        """Count products"""
        sql = "SELECT COUNT(*) as count FROM Product WHERE Status = %s"
        params = [status]

        if vendor_id:
            sql += " AND Vendor_ID = %s"
            params.append(vendor_id)

        result = self.executor.execute_query_one(sql, tuple(params))
        return result['count'] if result else 0

    def create_product(self, product_data):
        """Create new product"""
        sql = """
            INSERT INTO Product (
                Product_ID, Name, Description, Price, Stock, Category,
                Image_URL, Vendor_ID, Status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            product_data.get('product_id'),
            product_data.get('name'),
            product_data.get('description'),
            product_data.get('price'),
            product_data.get('stock'),
            product_data.get('category'),
            product_data.get('image_url'),
            product_data.get('vendor_id'),
            product_data.get('status', 'Active')
        )
        return self.executor.execute_update(sql, params)

    def update_product(self, product_id, product_data):
        """Update product information"""
        # Build dynamic update statement
        update_fields = []
        params = []

        fields_mapping = {
            'name': 'Name',
            'description': 'Description',
            'price': 'Price',
            'stock': 'Stock',
            'category': 'Category',
            'image_url': 'Image_URL',
            'status': 'Status'
        }

        for field, column in fields_mapping.items():
            if field in product_data:
                update_fields.append(f"{column} = %s")
                params.append(product_data[field])

        if not update_fields:
            return 0

        sql = f"UPDATE Product SET {', '.join(update_fields)} WHERE Product_ID = %s"
        params.append(product_id)

        return self.executor.execute_update(sql, tuple(params))

    def update_product_stock(self, product_id, quantity_change):
        """Update product stock (increase or decrease)"""
        sql = """
            UPDATE Product
            SET Stock = Stock + %s
            WHERE Product_ID = %s AND Stock + %s >= 0
        """
        params = (quantity_change, product_id, quantity_change)
        return self.executor.execute_update(sql, params)

    def delete_product(self, product_id):
        """Delete product (soft delete)"""
        sql = "UPDATE Product SET Status = 'Inactive' WHERE Product_ID = %s"
        params = (product_id,)
        return self.executor.execute_update(sql, params)

    def toggle_product_status(self, product_id):
        """Toggle product status (Active/Inactive)"""
        sql = """
            UPDATE Product
            SET Status = CASE
                WHEN Status = 'Active' THEN 'Inactive'
                ELSE 'Active'
            END
            WHERE Product_ID = %s
        """
        params = (product_id,)
        return self.executor.execute_update(sql, params)

    def get_product_categories(self):
        """Get all product categories"""
        sql = "SELECT DISTINCT Category FROM Product WHERE Category IS NOT NULL ORDER BY Category"
        return self.executor.execute_query(sql)

    def get_vendor_product_stats(self, vendor_id):
        """Get vendor product statistics"""
        sql = """
            SELECT
                Status,
                COUNT(*) as count,
                SUM(Stock) as total_stock,
                AVG(Price) as avg_price
            FROM Product
            WHERE Vendor_ID = %s
            GROUP BY Status
        """
        params = (vendor_id,)
        return self.executor.execute_query(sql, params)

    def search_products_by_tags(self, tag_names, operator='AND', limit=50):
        """Search products by tags"""
        if not tag_names:
            return []

        # Build query based on operator
        if operator.upper() == 'AND':
            # Products that contain all tags
            sql = """
                SELECT p.*, v.Store_Name
                FROM Product p
                LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
                WHERE p.Status = 'Active' AND v.Status = 'Active'
                  AND p.Product_ID IN (
                      SELECT tg.Product_ID
                      FROM Tagging tg
                      LEFT JOIN Tag t ON tg.Tag_ID = t.Tag_ID
                      WHERE t.Name IN ({})
                      GROUP BY tg.Product_ID
                      HAVING COUNT(DISTINCT t.Tag_ID) = %s
                  )
                ORDER BY p.Created_At DESC
                LIMIT %s
            """.format(','.join(['%s'] * len(tag_names)))
            params = tag_names + [len(tag_names), limit]
        else:
            # Products that contain any tag
            sql = """
                SELECT DISTINCT p.*, v.Store_Name
                FROM Product p
                LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
                LEFT JOIN Tagging tg ON p.Product_ID = tg.Product_ID
                LEFT JOIN Tag t ON tg.Tag_ID = t.Tag_ID
                WHERE p.Status = 'Active' AND v.Status = 'Active'
                  AND t.Name IN ({})
                ORDER BY p.Created_At DESC
                LIMIT %s
            """.format(','.join(['%s'] * len(tag_names)))
            params = tag_names + [limit]

        return self.executor.execute_query(sql, tuple(params))

    def get_recent_products(self, vendor_id=None, limit=10):
        """Get recently added products"""
        sql = """
            SELECT p.*, v.Store_Name
            FROM Product p
            LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
            WHERE p.Status = 'Active' AND v.Status = 'Active'
        """
        params = []

        if vendor_id:
            sql += " AND p.Vendor_ID = %s"
            params.append(vendor_id)

        sql += " ORDER BY p.Created_At DESC LIMIT %s"
        params.append(limit)

        return self.executor.execute_query(sql, tuple(params))

    def check_product_ownership(self, product_id, vendor_id):
        """Check if product belongs to specified vendor"""
        sql = "SELECT COUNT(*) as count FROM Product WHERE Product_ID = %s AND Vendor_ID = %s"
        params = (product_id, vendor_id)
        result = self.executor.execute_query_one(sql, params)
        return result['count'] > 0 if result else False