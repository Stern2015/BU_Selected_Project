"""
Tag DAO
Handles tag data access
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


class TagDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    # Basic tag operations
    def get_tag_by_id(self, tag_id):
        """Get tag by ID"""
        sql = "SELECT * FROM Tag WHERE Tag_ID = %s"
        params = (tag_id,)
        return self.executor.execute_query_one(sql, params)

    def get_tag_by_name(self, tag_name):
        """Get tag by name"""
        sql = "SELECT * FROM Tag WHERE Name = %s"
        params = (tag_name,)
        return self.executor.execute_query_one(sql, params)

    def get_all_tags(self, limit=100):
        """Get all tags"""
        sql = "SELECT * FROM Tag ORDER BY Name LIMIT %s"
        params = (limit,)
        return self.executor.execute_query(sql, params)

    def search_tags(self, keyword, limit=20):
        """Search tags"""
        sql = "SELECT * FROM Tag WHERE Name LIKE %s ORDER BY Name LIMIT %s"
        params = (f"%{keyword}%", limit)
        return self.executor.execute_query(sql, params)

    def create_tag(self, tag_name):
        """Create new tag"""
        sql = "INSERT INTO Tag (Name) VALUES (%s)"
        params = (tag_name,)
        return self.executor.execute_update(sql, params)

    def delete_tag(self, tag_id):
        """Delete tag"""
        sql = "DELETE FROM Tag WHERE Tag_ID = %s"
        params = (tag_id,)
        return self.executor.execute_update(sql, params)

    # Product-tag association operations
    def get_tags_by_product(self, product_id):
        """Get all tags for a product (sorted by position)"""
        sql = """
            SELECT t.*, tg.Position
            FROM Tag t
            LEFT JOIN Tagging tg ON t.Tag_ID = tg.Tag_ID
            WHERE tg.Product_ID = %s
            ORDER BY tg.Position
        """
        params = (product_id,)
        return self.executor.execute_query(sql, params)

    def get_products_by_tag(self, tag_id, limit=50):
        """Get all products with specified tag"""
        sql = """
            SELECT p.*, v.Store_Name
            FROM Product p
            LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
            LEFT JOIN Tagging tg ON p.Product_ID = tg.Product_ID
            WHERE tg.Tag_ID = %s AND p.Status = 'Active' AND v.Status = 'Active'
            ORDER BY p.Created_At DESC
            LIMIT %s
        """
        params = (tag_id, limit)
        return self.executor.execute_query(sql, params)

    def add_tag_to_product(self, product_id, tag_id, position=None):
        """Add tag to product"""
        # If position not specified, auto-assign next available position
        if position is None:
            # Get current maximum position
            sql = "SELECT MAX(Position) as max_pos FROM Tagging WHERE Product_ID = %s"
            result = self.executor.execute_query_one(sql, (product_id,))
            position = (result['max_pos'] or 0) + 1

        # Check if exceeds 3-tag limit
        if position > 3:
            raise ValueError("Each product can have at most 3 tags")

        sql = """
            INSERT INTO Tagging (Product_ID, Tag_ID, Position)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE Position = VALUES(Position)
        """
        params = (product_id, tag_id, position)
        return self.executor.execute_update(sql, params)

    def remove_tag_from_product(self, product_id, tag_id):
        """Remove tag from product"""
        sql = "DELETE FROM Tagging WHERE Product_ID = %s AND Tag_ID = %s"
        params = (product_id, tag_id)
        return self.executor.execute_update(sql, params)

    def update_tag_position(self, product_id, tag_id, new_position):
        """Update tag position in product"""
        if new_position < 1 or new_position > 3:
            raise ValueError("Tag position must be between 1-3")

        # Check if new position is already occupied
        sql = "SELECT Tag_ID FROM Tagging WHERE Product_ID = %s AND Position = %s"
        existing = self.executor.execute_query_one(sql, (product_id, new_position))

        if existing and existing['Tag_ID'] != tag_id:
            # Swap positions
            old_sql = "SELECT Position FROM Tagging WHERE Product_ID = %s AND Tag_ID = %s"
            old_result = self.executor.execute_query_one(old_sql, (product_id, tag_id))
            old_position = old_result['Position'] if old_result else None

            if old_position:
                # Start transaction
                self.tx_manager.begin_transaction()
                try:
                    # Move occupying tag to old position
                    update1_sql = "UPDATE Tagging SET Position = %s WHERE Product_ID = %s AND Tag_ID = %s"
                    self.executor.execute_update(update1_sql, (old_position, product_id, existing['Tag_ID']))

                    # Move current tag to new position
                    update2_sql = "UPDATE Tagging SET Position = %s WHERE Product_ID = %s AND Tag_ID = %s"
                    self.executor.execute_update(update2_sql, (new_position, product_id, tag_id))

                    self.tx_manager.commit_transaction()
                    return 2
                except Exception as e:
                    self.tx_manager.rollback_transaction()
                    raise e
        else:
            # Directly update position
            sql = "UPDATE Tagging SET Position = %s WHERE Product_ID = %s AND Tag_ID = %s"
            params = (new_position, product_id, tag_id)
            return self.executor.execute_update(sql, params)

    def set_product_tags(self, product_id, tag_names):
        """Set product tags (replace existing tags)"""
        if len(tag_names) > 3:
            raise ValueError("Each product can have at most 3 tags")

        # Start transaction
        self.tx_manager.begin_transaction()
        try:
            # Delete existing tags
            delete_sql = "DELETE FROM Tagging WHERE Product_ID = %s"
            self.executor.execute_update(delete_sql, (product_id,))

            # Add new tags
            for position, tag_name in enumerate(tag_names, 1):
                tag_name = tag_name.strip()
                if tag_name:
                    # Ensure tag exists
                    tag = self.get_tag_by_name(tag_name)
                    if not tag:
                        self.create_tag(tag_name)
                        tag = self.get_tag_by_name(tag_name)

                    # Associate tag to product
                    self.add_tag_to_product(product_id, tag['Tag_ID'], position)

            self.tx_manager.commit_transaction()
            return len(tag_names)
        except Exception as e:
            self.tx_manager.rollback_transaction()
            raise e

    def get_popular_tags(self, limit=20):
        """Get popular tags (most used tags)"""
        sql = """
            SELECT t.*, COUNT(tg.Product_ID) as usage_count
            FROM Tag t
            LEFT JOIN Tagging tg ON t.Tag_ID = tg.Tag_ID
            LEFT JOIN Product p ON tg.Product_ID = p.Product_ID
            WHERE p.Status = 'Active'
            GROUP BY t.Tag_ID
            ORDER BY usage_count DESC, t.Name
            LIMIT %s
        """
        params = (limit,)
        return self.executor.execute_query(sql, params)

    def get_tag_cloud_data(self, min_font_size=12, max_font_size=36):
        """Get tag cloud data"""
        tags = self.get_popular_tags(limit=50)

        if not tags:
            return []

        # Calculate usage frequency range
        usage_counts = [tag['usage_count'] or 0 for tag in tags]
        min_count = min(usage_counts)
        max_count = max(usage_counts)

        # Calculate font size
        result = []
        for tag in tags:
            count = tag['usage_count'] or 0
            if max_count > min_count:
                # Linear interpolation to calculate font size
                font_size = min_font_size + (count - min_count) * (max_font_size - min_font_size) / (max_count - min_count)
            else:
                font_size = (min_font_size + max_font_size) / 2

            result.append({
                'tag_id': tag['Tag_ID'],
                'name': tag['Name'],
                'count': count,
                'font_size': round(font_size, 1)
            })

        return result

    def get_related_tags(self, tag_id, limit=10):
        """Get related tags (frequently used together)"""
        sql = """
            SELECT t2.*, COUNT(*) as cooccurrence_count
            FROM Tagging tg1
            LEFT JOIN Tagging tg2 ON tg1.Product_ID = tg2.Product_ID
            LEFT JOIN Tag t2 ON tg2.Tag_ID = t2.Tag_ID
            WHERE tg1.Tag_ID = %s AND tg2.Tag_ID != %s
            GROUP BY t2.Tag_ID
            ORDER BY cooccurrence_count DESC
            LIMIT %s
        """
        params = (tag_id, tag_id, limit)
        return self.executor.execute_query(sql, params)

    def get_tag_statistics(self):
        """Get tag statistics"""
        sql = """
            SELECT
                COUNT(DISTINCT t.Tag_ID) as total_tags,
                COUNT(DISTINCT tg.Product_ID) as tagged_products,
                AVG(tag_count_per_product.avg_tags) as avg_tags_per_product
            FROM Tag t
            LEFT JOIN Tagging tg ON t.Tag_ID = tg.Tag_ID
            LEFT JOIN (
                SELECT Product_ID, COUNT(*) as avg_tags
                FROM Tagging
                GROUP BY Product_ID
            ) tag_count_per_product ON tg.Product_ID = tag_count_per_product.Product_ID
        """
        return self.executor.execute_query_one(sql)