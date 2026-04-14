"""
Vendor Data Access Object (DAO)
Handles all database operations for vendor management
Implements CRUD operations and vendor-related queries
"""

from driver.sql_executor import SQL_Executor
from driver.transaction_manager import Transaction_Manager
from dao.BaseDAO import BaseDAO

# DAO class for handling vendor-related database operations.
class VendorDAO(BaseDAO):
    def __init__(self):
        super().__init__()
    
    # ===== CREATE OPERATIONS =====
    
    def insert(self, vendor_id, store_name, location, status='Active', rating=0.00):
        try:
            sql = """
                INSERT INTO Vendor (Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """
            affected = self.executor.execute_update(sql, (vendor_id, store_name, location, status, rating))
            return affected > 0
        except Exception as e:
            print(f"Error inserting vendor: {str(e)}")
            return False
    
    # ===== READ OPERATIONS =====
    def select_by_id(self, vendor_id):
        try:
            sql = """
                SELECT Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At
                FROM Vendor
                WHERE Vendor_ID = %s
            """
            result = self.executor.execute_query_one(sql, (vendor_id,))
            
            if result:
                return self._map_row_to_dict(result)
            return None
        except Exception as e:
            print(f"Error selecting vendor by ID: {str(e)}")
            return None
    
    def select_all(self, offset=0, limit=None):
        try:
            if limit:
                sql = """
                    SELECT Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At
                    FROM Vendor
                    ORDER BY Created_At DESC
                    LIMIT %s OFFSET %s
                """
                results = self.executor.execute_query(sql, (limit, offset))
            else:
                sql = """
                    SELECT Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At
                    FROM Vendor
                    ORDER BY Created_At DESC
                """
                results = self.executor.execute_query(sql)
            
            return [self._map_row_to_dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error selecting all vendors: {str(e)}")
            return []
    
    def select_by_status(self, status):
        try:
            sql = """
                SELECT Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At
                FROM Vendor
                WHERE Status = %s
                ORDER BY Created_At DESC
            """
            results = self.executor.execute_query(sql, (status,))
            return [self._map_row_to_dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error selecting vendors by status: {str(e)}")
            return []
    
    def select_by_location(self, location):
        try:
            sql = """
                SELECT Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At
                FROM Vendor
                WHERE Location LIKE %s
                ORDER BY Created_At DESC
            """
            results = self.executor.execute_query(sql, (f"%{location}%",))
            return [self._map_row_to_dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error selecting vendors by location: {str(e)}")
            return []
    
    def count_all(self):
        try:
            sql = "SELECT COUNT(*) FROM Vendor"
            result = self.executor.execute_query_one(sql)
            return result[0] if result else 0
        except Exception as e:
            print(f"Error counting vendors: {str(e)}")
            return 0
    
    def count_by_status(self, status):
        try:
            sql = "SELECT COUNT(*) FROM Vendor WHERE Status = %s"
            result = self.executor.execute_query_one(sql, (status,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error counting vendors by status: {str(e)}")
            return 0
    
    # ===== UPDATE OPERATIONS =====
    
    def update(self, vendor_id, **fields):
        try:
            if not fields:
                return False
            
            update_parts = []
            values = []
            
            # Map field names to database column names
            field_mapping = {
                'store_name': 'Store_Name',
                'location': 'Location',
                'status': 'Status',
                'rating': 'Rating'
            }
            
            # Build dynamic SQL query
            for field, value in fields.items():
                if field in field_mapping:
                    update_parts.append(f"{field_mapping[field]} = %s")
                    values.append(value)
            
            if not update_parts:
                return False
            
            # Always update the Updated_At timestamp
            update_parts.append("Updated_At = NOW()")
            values.append(vendor_id)
            
            sql = f"UPDATE Vendor SET {', '.join(update_parts)} WHERE Vendor_ID = %s"
            affected = self.executor.execute_update(sql, tuple(values))
            return affected > 0
        except Exception as e:
            print(f"Error updating vendor: {str(e)}")
            return False
    
    def update_rating(self, vendor_id, new_rating):
        try:
            # Validate rating range
            if new_rating < 0.00 or new_rating > 5.00:
                raise ValueError("Rating must be between 0.00 and 5.00")
            
            sql = "UPDATE Vendor SET Rating = %s, Updated_At = NOW() WHERE Vendor_ID = %s"
            affected = self.executor.execute_update(sql, (new_rating, vendor_id))
            return affected > 0
        except Exception as e:
            print(f"Error updating rating: {str(e)}")
            return False
    
    def update_status(self, vendor_id, status):
        try:
            if status not in ['Active', 'Inactive']:
                raise ValueError("Status must be 'Active' or 'Inactive'")
            
            sql = "UPDATE Vendor SET Status = %s, Updated_At = NOW() WHERE Vendor_ID = %s"
            affected = self.executor.execute_update(sql, (status, vendor_id))
            return affected > 0
        except Exception as e:
            print(f"Error updating status: {str(e)}")
            return False
    
    # ===== DELETE OPERATIONS =====
    
    def delete(self, vendor_id):

        try:
            sql = "DELETE FROM Vendor WHERE Vendor_ID = %s"
            affected = self.executor.execute_update(sql, (vendor_id,))
            return affected > 0
        except Exception as e:
            print(f"Error deleting vendor: {str(e)}")
            return False
    
    # ===== RELATIONSHIP QUERIES =====
    
    def get_vendor_products_count(self, vendor_id):
        try:
            sql = "SELECT COUNT(*) FROM Product WHERE Vendor_ID = %s"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting product count: {str(e)}")
            return 0
    
    def get_vendor_active_products_count(self, vendor_id):
        try:
            sql = "SELECT COUNT(*) FROM Product WHERE Vendor_ID = %s AND Status = 'Active'"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting active product count: {str(e)}")
            return 0
    
    def get_vendor_out_of_stock_count(self, vendor_id):
        try:
            sql = "SELECT COUNT(*) FROM Product WHERE Vendor_ID = %s AND Stock = 0"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting out of stock count: {str(e)}")
            return 0
    
    def get_vendor_total_stock(self, vendor_id):
        try:
            sql = "SELECT COALESCE(SUM(Stock), 0) FROM Product WHERE Vendor_ID = %s"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting total stock: {str(e)}")
            return 0
    
    def get_vendor_orders_count(self, vendor_id):
        try:
            sql = """
                SELECT COUNT(DISTINCT o.Order_ID)
                FROM Order o
                JOIN OrderItem oi ON o.Order_ID = oi.Order_ID
                JOIN Product p ON oi.Product_ID = p.Product_ID
                WHERE p.Vendor_ID = %s
            """
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting orders count: {str(e)}")
            return 0
    
    # ===== UTILITY METHODS =====
    
    def exists(self, vendor_id):
        try:
            sql = "SELECT 1 FROM Vendor WHERE Vendor_ID = %s LIMIT 1"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result is not None
        except Exception as e:
            print(f"Error checking vendor existence: {str(e)}")
            return False
    
    def get_vendor_stats(self, vendor_id):
        try:
            # Check if vendor exists first
            if not self.exists(vendor_id):
                return None
            
            return {
                'total_products': self.get_vendor_products_count(vendor_id),
                'active_products': self.get_vendor_active_products_count(vendor_id),
                'out_of_stock': self.get_vendor_out_of_stock_count(vendor_id),
                'total_stock': self.get_vendor_total_stock(vendor_id),
                'orders_count': self.get_vendor_orders_count(vendor_id)
            }
        except Exception as e:
            print(f"Error getting vendor stats: {str(e)}")
            return None
    
    def activate_all_in_location(self, location):
        try:
            sql = """
                UPDATE Vendor 
                SET Status = 'Active', Updated_At = NOW() 
                WHERE Location LIKE %s AND Status = 'Inactive'
            """
            affected = self.executor.execute_update(sql, (f"%{location}%",))
            return affected
        except Exception as e:
            print(f"Error activating vendors: {str(e)}")
            return 0
    
    def deactivate_all_in_location(self, location):
        try:
            sql = """
                UPDATE Vendor 
                SET Status = 'Inactive', Updated_At = NOW() 
                WHERE Location LIKE %s AND Status = 'Active'
            """
            affected = self.executor.execute_update(sql, (f"%{location}%",))
            return affected
        except Exception as e:
            print(f"Error deactivating vendors: {str(e)}")
            return 0
    
    # ===== HELPER METHODS =====
    
    def _map_row_to_dict(self, row):
        if not row:
            return None
        
        return {
            'vendor_id': row[0],
            'store_name': row[1],
            'location': row[2],
            'status': row[3],
            'rating': float(row[4]),
            'created_at': row[5],
            'updated_at': row[6]
        }
