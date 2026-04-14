"""
Vendor Management Service
"""
import uuid
from datetime import datetime
from driver.sql_executor import SQL_Executor


class VendorService:
    def __init__(self):
        self.executor = SQL_Executor()

    def get_all_vendors(self):
        sql = """
            SELECT Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At
            FROM Vendor
            ORDER BY Created_At DESC
        """
        try:
            results = self.executor.execute_query(sql)
            return results if results else []
        
        except Exception as e:

            print(f"Error retrieving all vendors: {str(e)}")

            return []

    # Generate vendor ID using user ID as base (following database convention)
    def onboard_new_vendor(self, user_id, business_name, geographical_presence):
        try:
            
            vendor_id = user_id
            
            # Check if vendor already exists
            check_sql = "SELECT Vendor_ID FROM Vendor WHERE Vendor_ID = %s"
            existing = self.executor.execute_query_one(check_sql, (vendor_id,))
            
            if existing:
                return {'success': False, 'vendor_id': None, 'message': 'Vendor already exists for this user'}
            
            # Insert new vendor
            insert_sql = """
                INSERT INTO Vendor (Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At)
                VALUES (%s, %s, %s, 'Active', 0.00, NOW(), NOW())
            """
            
            affected = self.executor.execute_update(insert_sql, (vendor_id, business_name, geographical_presence))
            
            if affected > 0:

                return {
                    'success': True,
                    'vendor_id': vendor_id,
                    'message': f'Vendor onboar successfully: {business_name}'
                }
            
            else:

                return {'success': False, 'vendor_id': None, 'message': 'Failed to create vendor'}
                
        except Exception as e:

            print(f"Error onboarding vendor: {str(e)}")

            return {'success': False, 'vendor_id': None, 'message': f'Error: {str(e)}'}

    def get_vendor_by_id(self, vendor_id):
        try:
            sql = """
                SELECT Vendor_ID, Store_Name, Location, Status, Rating, Created_At, Updated_At
                FROM Vendor
                WHERE Vendor_ID = %s
            """

            result = self.executor.execute_query_one(sql, (vendor_id,))
            
            if result:
                return {
                    'vendor_id': result['Vendor_ID'],
                    'business_name': result['Store_Name'],
                    'geographical_presence': result['Location'],
                    'status': result['Status'],
                    'average_rating': float(result['Rating']) if result['Rating'] else 0.0,
                    'created_at': result['Created_At'],
                    'updated_at': result['Updated_At']
                }
            
            return None
            
        except Exception as e:

            print(f"Error retrieving vendor {vendor_id}: {str(e)}")

            return None

    def update_vendor_info(self, vendor_id, business_name=None, geographical_presence=None):

        try:
            # Check if vendor exists
            check_sql = "SELECT Vendor_ID FROM Vendor WHERE Vendor_ID = %s"
            existing = self.executor.execute_query_one(check_sql, (vendor_id,))
            
            if not existing:
                return {'success': False, 'message': 'Vendor not found'}
            
            # Build update query dynamically
            update_parts = ['Updated_At = NOW()']
            params = []
            
            if business_name is not None:
                update_parts.append('Store_Name = %s')
                params.append(business_name)
            
            if geographical_presence is not None:
                update_parts.append('Location = %s')
                params.append(geographical_presence)
            
            # If no updates besides timestamp, return success

            if len(update_parts) == 1:
                return {'success': True, 'message': 'No changes to update'}
            
            params.append(vendor_id)

            update_sql = f"UPDATE Vendor SET {', '.join(update_parts)} WHERE Vendor_ID = %s"
            
            affected = self.executor.execute_update(update_sql, tuple(params))
            
            if affected > 0:

                return {'success': True, 'message': 'Vendor information updated successfully'}
            else:

                return {'success': False, 'message': 'Failed to update vendor'}
                
        except Exception as e:

            print(f"Error updating vendor {vendor_id}: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def get_vendor_products(self, vendor_id):

        try:
            # First verify vendor exists
            check_sql = "SELECT Vendor_ID FROM Vendor WHERE Vendor_ID = %s"
            vendor_exists = self.executor.execute_query_one(check_sql, (vendor_id,))
            
            if not vendor_exists:
                return []
            
            # Get all products for this vendor
            sql = """
                SELECT Product_ID, Name, Description, Price, Stock, Category, Image_URL, Status, Rating, Created_At, Updated_At
                FROM Product WHERE Vendor_ID = %s
                ORDER BY Created_At DESC
            """
            
            results = self.executor.execute_query(sql, (vendor_id,))

            return results if results else []
            
        except Exception as e:

            print(f"Error retrieving products for vendor {vendor_id}: {str(e)}")
            return []

    def get_vendor_average_rating(self, vendor_id):

        try:
            # Get average rating from customer's Rating table
            sql = """
                SELECT AVG(Score) as avg_rating
                FROM Rating
                WHERE Vendor_ID = %s
            """
            
            result = self.executor.execute_query_one(sql, (vendor_id,))
            
            if result and result.get('avg_rating') is not None:
                avg_rating = float(result['avg_rating'])
                # Round to 2 decimal places
                return round(avg_rating, 2)
            
            # Also check the Rating field in Vendor table as fallback
            vendor_sql = "SELECT Rating FROM Vendor WHERE Vendor_ID = %s"
            vendor_result = self.executor.execute_query_one(vendor_sql, (vendor_id,))
            
            if vendor_result and vendor_result.get('Rating') is not None:
                return float(vendor_result['Rating'])
            
            return 0.00
            
        except Exception as e:

            print(f"Error calculating average rating for vendor {vendor_id}: {str(e)}")
            return 0.00

    def get_vendor_orders(self, vendor_id):
        try:
            # Verify vendor exists
            check_sql = "SELECT Vendor_ID FROM Vendor WHERE Vendor_ID = %s"
            vendor_exists = self.executor.execute_query_one(check_sql, (vendor_id,))
            
            if not vendor_exists:
                return []
            
            # Try to fetch orders related to this vendor's products
            # This assumes Order and OrderItem tables exist with proper foreign keys
            sql = """
                SELECT DISTINCT oi.Order_ID, oi.Product_ID, oi.Quantity, oi.Price, 
                       o.Order_Date, o.Status, o.Customer_ID, p.Name as Product_Name
                FROM Order o
                JOIN OrderItem oi ON o.Order_ID = oi.Order_ID
                JOIN Product p ON oi.Product_ID = p.Product_ID
                WHERE p.Vendor_ID = %s
                ORDER BY o.Order_Date DESC
            """
            
            results = self.executor.execute_query(sql, (vendor_id,))

            return results if results else []
            
        except Exception as e:

            # If Order/OrderItem tables don't exist, return empty list gracefully
            print(f"Note: Could not retrieve vendor orders (Order tables may not exist): {str(e)}")
            return []

    # Additional utility methods
    
    def get_vendor_stats(self, vendor_id):
        try:
            vendor = self.get_vendor_by_id(vendor_id)
            if not vendor:
                return None
            
            # Count products
            product_count_sql = "SELECT COUNT(*) as cnt FROM Product WHERE Vendor_ID = %s"
            product_count = self.executor.execute_query_one(product_count_sql, (vendor_id,))

            # Get average rating
            avg_rating = self.get_vendor_average_rating(vendor_id)

            # Count active products
            active_count_sql = "SELECT COUNT(*) as cnt FROM Product WHERE Vendor_ID = %s AND Status = 'Active'"
            active_count = self.executor.execute_query_one(active_count_sql, (vendor_id,))

            return {
                'vendor_id': vendor_id,
                'business_name': vendor['business_name'],
                'total_products': product_count['cnt'] if product_count else 0,
                'active_products': active_count['cnt'] if active_count else 0,
                'average_rating': avg_rating,
                'status': vendor['status']
            }            
        except Exception as e:

            print(f"Error retrieving vendor stats: {str(e)}")
            return None

    def update_vendor_rating(self, vendor_id, new_rating):
        try:
            # Validate rating range
            if new_rating < 0.00 or new_rating > 5.00:
                return {'success': False, 'message': 'Rating must be between 0.00 and 5.00'}
            
            # Check if vendor exists
            check_sql = "SELECT Vendor_ID FROM Vendor WHERE Vendor_ID = %s"
            existing = self.executor.execute_query_one(check_sql, (vendor_id,))
            
            if not existing:
                return {'success': False, 'message': 'Vendor not found'}
            
            # Update rating
            update_sql = """
                UPDATE Vendor 
                SET Rating = %s, Updated_At = NOW()
                WHERE Vendor_ID = %s
            """
            
            affected = self.executor.execute_update(update_sql, (new_rating, vendor_id))
            
            if affected > 0:
                return {'success': True, 'message': f'Vendor rating updated to {new_rating}'}
            else:
                return {'success': False, 'message': 'Failed to update vendor rating'}
                
        except Exception as e:

            print(f"Error updating vendor rating: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def deactivate_vendor(self, vendor_id):
        try:
            # Check if vendor exists
            check_sql = "SELECT Vendor_ID FROM Vendor WHERE Vendor_ID = %s"
            existing = self.executor.execute_query_one(check_sql, (vendor_id,))
            
            if not existing:

                return {'success': False, 'message': 'Vendor not found'}
            
            # Update vendor status to Inactive
            update_sql = """
                UPDATE Vendor 
                SET Status = 'Inactive', Updated_At = NOW()
                WHERE Vendor_ID = %s
            """
            
            affected = self.executor.execute_update(update_sql, (vendor_id,))
            
            if affected > 0:
                return {'success': True, 'message': 'Vendor deactivated successfully'}
            else:
                return {'success': False, 'message': 'Failed to deactivate vendor'}
                
        except Exception as e:

            print(f"Error deactivating vendor: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def activate_vendor(self, vendor_id):

        try:
            # Check if vendor exists
            check_sql = "SELECT Vendor_ID FROM Vendor WHERE Vendor_ID = %s"
            existing = self.executor.execute_query_one(check_sql, (vendor_id,))
            
            if not existing:
                return {'success': False, 'message': 'Vendor not found'}
            
            # Update vendor status to Active
            update_sql = """
                UPDATE Vendor 
                SET Status = 'Active', Updated_At = NOW()
                WHERE Vendor_ID = %s
            """
            
            affected = self.executor.execute_update(update_sql, (vendor_id,))
            
            if affected > 0:

                return {'success': True, 'message': 'Vendor activated successfully'}
            else:

                return {'success': False, 'message': 'Failed to activate vendor'}
                
        except Exception as e:
            
            print(f"Error activating vendor: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}
