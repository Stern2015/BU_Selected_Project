"""
Vendor Data Access Object (DAO)
Handles all database operations for vendor management
Implements CRUD operations and vendor-related queries
"""

from driver.sql_executor import SQL_Executor
from driver.transaction_manager import Transaction_Manager
from dao.BaseDAO import BaseDAO

class VendorDAO(BaseDAO):
    """
    DAO class for handling vendor-related database operations.
    Provides methods for creating, reading, updating, and deleting vendor records.
    """
    
    def __init__(self):
        super().__init__()
    
    # ===== CREATE OPERATIONS =====
    
    def insert(self, vendor_id, store_name, location, status='Active', rating=0.00):
        """
        Create a new vendor record in the database.
        
        Args:
            vendor_id (str): Unique vendor identifier
            store_name (str): Name of the store/business
            location (str): Geographic location of the vendor
            status (str): Status of the vendor ('Active' or 'Inactive'). Default: 'Active'
            rating (float): Initial rating score (0.00-5.00). Default: 0.00
        
        Returns:
            bool: True if insert was successful, False otherwise
        
        Example:
            >>> vendor_dao = VendorDAO()
            >>> success = vendor_dao.insert('v1', 'Tech Store', 'New York', 'Active', 4.5)
        """
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
        """
        Retrieve a single vendor by its ID.
        
        Args:
            vendor_id (str): The vendor ID to query
        
        Returns:
            dict: Dictionary containing vendor information or None if not found.
                  Keys: vendor_id, store_name, location, status, rating, created_at, updated_at
        
        Example:
            >>> vendor = vendor_dao.select_by_id('v1')
            >>> if vendor:
            ...     print(vendor['store_name'])
        """
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
        """
        Retrieve all vendors with optional pagination.
        
        Args:
            offset (int): Starting position for pagination. Default: 0
            limit (int): Maximum number of records to return. If None, returns all records
        
        Returns:
            list: List of vendor dictionaries, empty list if no vendors found
        
        Example:
            >>> vendors = vendor_dao.select_all(limit=10)
            >>> for vendor in vendors:
            ...     print(vendor['store_name'])
        """
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
        """
        Retrieve all vendors with a specific status.
        
        Args:
            status (str): Vendor status to filter by ('Active' or 'Inactive')
        
        Returns:
            list: List of vendor dictionaries with matching status
        
        Example:
            >>> active_vendors = vendor_dao.select_by_status('Active')
        """
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
        """
        Retrieve all vendors in a specific location (partial match).
        
        Args:
            location (str): Location to search for (supports partial matching)
        
        Returns:
            list: List of vendor dictionaries for the location
        
        Example:
            >>> vendors_in_ny = vendor_dao.select_by_location('New York')
        """
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
        """
        Get the total count of vendors in the database.
        
        Returns:
            int: Total number of vendors, 0 if query fails
        
        Example:
            >>> total = vendor_dao.count_all()
            >>> print(f"Total vendors: {total}")
        """
        try:
            sql = "SELECT COUNT(*) FROM Vendor"
            result = self.executor.execute_query_one(sql)
            return result[0] if result else 0
        except Exception as e:
            print(f"Error counting vendors: {str(e)}")
            return 0
    
    def count_by_status(self, status):
        """
        Get the count of vendors with a specific status.
        
        Args:
            status (str): Status to filter by
        
        Returns:
            int: Count of vendors with the specified status
        """
        try:
            sql = "SELECT COUNT(*) FROM Vendor WHERE Status = %s"
            result = self.executor.execute_query_one(sql, (status,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error counting vendors by status: {str(e)}")
            return 0
    
    # ===== UPDATE OPERATIONS =====
    
    def update(self, vendor_id, **fields):
        """
        Update vendor information with dynamic field mapping.
        Only updates the fields that are provided.
        
        Args:
            vendor_id (str): The vendor ID to update
            **fields: Keyword arguments representing fields to update.
                     Supported fields: store_name, location, status, rating
        
        Returns:
            bool: True if update was successful, False otherwise
        
        Example:
            >>> success = vendor_dao.update('v1', store_name='New Name', location='San Francisco')
        """
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
        """
        Update the rating of a specific vendor.
        
        Args:
            vendor_id (str): The vendor ID to update
            new_rating (float): The new rating value (must be between 0.00 and 5.00)
        
        Returns:
            bool: True if update was successful, False otherwise
        
        Raises:
            ValueError: If rating is outside the valid range
        
        Example:
            >>> success = vendor_dao.update_rating('v1', 4.8)
        """
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
        """
        Update the status of a vendor (Active/Inactive).
        
        Args:
            vendor_id (str): The vendor ID to update
            status (str): New status value ('Active' or 'Inactive')
        
        Returns:
            bool: True if update was successful, False otherwise
        
        Raises:
            ValueError: If status is not 'Active' or 'Inactive'
        
        Example:
            >>> success = vendor_dao.update_status('v1', 'Inactive')
        """
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
        """
        Delete a vendor record from the database.
        
        Args:
            vendor_id (str): The vendor ID to delete
        
        Returns:
            bool: True if delete was successful, False otherwise
        
        Warning:
            This operation is permanent. Use with caution.
            Consider using update_status to deactivate instead of deleting.
        
        Example:
            >>> success = vendor_dao.delete('v1')
        """
        try:
            sql = "DELETE FROM Vendor WHERE Vendor_ID = %s"
            affected = self.executor.execute_update(sql, (vendor_id,))
            return affected > 0
        except Exception as e:
            print(f"Error deleting vendor: {str(e)}")
            return False
    
    # ===== RELATIONSHIP QUERIES =====
    
    def get_vendor_products_count(self, vendor_id):
        """
        Get the total count of products for a specific vendor.
        
        Args:
            vendor_id (str): The vendor ID to query
        
        Returns:
            int: Number of products for the vendor, 0 if no products found
        
        Example:
            >>> product_count = vendor_dao.get_vendor_products_count('v1')
        """
        try:
            sql = "SELECT COUNT(*) FROM Product WHERE Vendor_ID = %s"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting product count: {str(e)}")
            return 0
    
    def get_vendor_active_products_count(self, vendor_id):
        """
        Get the count of active products for a specific vendor.
        
        Args:
            vendor_id (str): The vendor ID to query
        
        Returns:
            int: Number of active products for the vendor
        
        Example:
            >>> active_count = vendor_dao.get_vendor_active_products_count('v1')
        """
        try:
            sql = "SELECT COUNT(*) FROM Product WHERE Vendor_ID = %s AND Status = 'Active'"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting active product count: {str(e)}")
            return 0
    
    def get_vendor_out_of_stock_count(self, vendor_id):
        """
        Get the count of out-of-stock products for a vendor.
        
        Args:
            vendor_id (str): The vendor ID to query
        
        Returns:
            int: Number of products with stock = 0
        
        Example:
            >>> out_of_stock = vendor_dao.get_vendor_out_of_stock_count('v1')
        """
        try:
            sql = "SELECT COUNT(*) FROM Product WHERE Vendor_ID = %s AND Stock = 0"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting out of stock count: {str(e)}")
            return 0
    
    def get_vendor_total_stock(self, vendor_id):
        """
        Get the total stock quantity for all products of a vendor.
        
        Args:
            vendor_id (str): The vendor ID to query
        
        Returns:
            int: Total stock quantity, 0 if no products found
        
        Example:
            >>> total_stock = vendor_dao.get_vendor_total_stock('v1')
        """
        try:
            sql = "SELECT COALESCE(SUM(Stock), 0) FROM Product WHERE Vendor_ID = %s"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting total stock: {str(e)}")
            return 0
    
    def get_vendor_orders_count(self, vendor_id):
        """
        Get the count of orders for a vendor.
        
        Args:
            vendor_id (str): The vendor ID to query
        
        Returns:
            int: Number of distinct orders for the vendor
        
        Example:
            >>> order_count = vendor_dao.get_vendor_orders_count('v1')
        """
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
        """
        Check if a vendor exists in the database.
        
        Args:
            vendor_id (str): The vendor ID to check
        
        Returns:
            bool: True if vendor exists, False otherwise
        
        Example:
            >>> if vendor_dao.exists('v1'):
            ...     print("Vendor exists")
        """
        try:
            sql = "SELECT 1 FROM Vendor WHERE Vendor_ID = %s LIMIT 1"
            result = self.executor.execute_query_one(sql, (vendor_id,))
            return result is not None
        except Exception as e:
            print(f"Error checking vendor existence: {str(e)}")
            return False
    
    def get_vendor_stats(self, vendor_id):
        """
        Get comprehensive statistics for a vendor.
        
        Args:
            vendor_id (str): The vendor ID to query
        
        Returns:
            dict: Dictionary containing vendor statistics with keys:
                  - total_products: Total number of products
                  - active_products: Number of active products
                  - out_of_stock: Number of out-of-stock products
                  - total_stock: Total stock quantity
                  - orders_count: Number of orders
        
        Returns None if vendor not found.
        
        Example:
            >>> stats = vendor_dao.get_vendor_stats('v1')
            >>> print(f"Active products: {stats['active_products']}")
        """
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
        """
        Activate all vendors in a specific location.
        
        Args:
            location (str): The location to filter by (partial match)
        
        Returns:
            int: Number of vendors activated
        
        Example:
            >>> count = vendor_dao.activate_all_in_location('New York')
        """
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
        """
        Deactivate all vendors in a specific location.
        
        Args:
            location (str): The location to filter by (partial match)
        
        Returns:
            int: Number of vendors deactivated
        
        Example:
            >>> count = vendor_dao.deactivate_all_in_location('New York')
        """
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
        """
        Convert a database row tuple to a dictionary.
        
        Args:
            row (tuple): Database row returned from query
        
        Returns:
            dict: Dictionary with vendor data, or None if row is empty
        
        Internal method not intended for direct use.
        """
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
