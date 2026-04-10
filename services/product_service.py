"""
Product & Tag Service
Handles business logic related to products and tags.

Note: Currently using in-memory database, all business logic is handled directly in app.py.
This file is reserved as a service layer interface for future migration to MySQL.
"""

import uuid
from datetime import datetime
from driver.sql_executor import SQL_Executor


class ProductService:
    """Product service class for handling product-related operations"""

    def __init__(self):
        self.executor = SQL_Executor()

    def browse_products(self, **kwargs):
        """
        Browse products with filtering options
        
        Args:
            **kwargs: Filter parameters (category, min_price, max_price, search, etc.)
        
        Returns:
            list: Filtered product list
        """
        try:
            # Build query with filters
            sql = "SELECT * FROM Product WHERE Status = 'Active'"
            params = []
            
            # Add filters based on kwargs
            if kwargs.get('category'):
                sql += " AND Category = %s"
                params.append(kwargs['category'])
            
            if kwargs.get('min_price'):
                sql += " AND Price >= %s"
                params.append(kwargs['min_price'])
            
            if kwargs.get('max_price'):
                sql += " AND Price <= %s"
                params.append(kwargs['max_price'])
            
            if kwargs.get('search'):
                sql += " AND (Name LIKE %s OR Description LIKE %s)"
                search_term = f"%{kwargs['search']}%"
                params.append(search_term)
                params.append(search_term)
            
            if kwargs.get('vendor_id'):
                sql += " AND Vendor_ID = %s"
                params.append(kwargs['vendor_id'])
            
            sql += " ORDER BY Created_At DESC"
            
            results = self.executor.execute_query(sql, tuple(params) if params else ())
            return results if results else []
            
        except Exception as e:
            print(f"Error browsing products: {str(e)}")
            return []

    def get_product_detail(self, product_id):
        """
        Get detailed information about a specific product
        
        Args:
            product_id (str): The product ID to retrieve
        
        Returns:
            dict: Product details or None if not found
        """
        try:
            sql = """
                SELECT Product_ID, Name, Description, Price, Stock, Category,
                       Image_URL, Status, Rating, Vendor_ID, Created_At, Updated_At
                FROM Product
                WHERE Product_ID = %s
            """
            
            result = self.executor.execute_query_one(sql, (product_id,))
            
            if result:
                return {
                    'product_id': result[0],
                    'name': result[1],
                    'description': result[2],
                    'price': float(result[3]),
                    'stock': result[4],
                    'category': result[5],
                    'image_url': result[6],
                    'status': result[7],
                    'rating': float(result[8]) if result[8] else 0.0,
                    'vendor_id': result[9],
                    'created_at': result[10],
                    'updated_at': result[11]
                }
            
            return None
            
        except Exception as e:
            print(f"Error retrieving product {product_id}: {str(e)}")
            return None

    def create_product(self, vendor_id, product_data, tag_names=None):
        """
        Create a new product
        
        Args:
            vendor_id (str): The vendor ID creating the product
            product_data (dict): Product information
                - name (str): Product name (required)
                - description (str): Product description
                - price (float): Product price (required)
                - stock (int): Initial stock quantity (required)
                - category (str): Product category
                - image_url (str): Image URL
            tag_names (list): List of tag names to associate with product
        
        Returns:
            dict: {'success': bool, 'product_id': str, 'message': str}
        """
        try:
            # Validate required fields
            name = product_data.get('name', '').strip()
            if not name:
                return {'success': False, 'product_id': None, 'message': 'Product name is required'}
            
            price = float(product_data.get('price', 0))
            if price < 0:
                return {'success': False, 'product_id': None, 'message': 'Price cannot be negative'}
            
            stock = int(product_data.get('stock', 0))
            if stock < 0:
                return {'success': False, 'product_id': None, 'message': 'Stock cannot be negative'}
            
            # Extract optional fields
            description = product_data.get('description', '').strip()
            category = product_data.get('category', 'General').strip()
            image_url = product_data.get('image_url', 'https://picsum.photos/seed/product/400/300').strip()
            status = 'Active' if stock > 0 else 'OutOfStock'
            
            # Generate product ID
            product_id = str(uuid.uuid4())
            
            # Insert product into database
            insert_sql = """
                INSERT INTO Product 
                (Product_ID, Vendor_ID, Name, Description, Price, Stock, Category, 
                 Image_URL, Status, Rating, Created_At, Updated_At)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0.0, NOW(), NOW())
            """
            
            affected = self.executor.execute_update(
                insert_sql,
                (product_id, vendor_id, name, description, price, stock, category, image_url, status)
            )
            
            if affected > 0:
                # Add tags if provided
                if tag_names:
                    self._add_product_tags(product_id, tag_names)
                
                return {
                    'success': True,
                    'product_id': product_id,
                    'message': f'Product "{name}" created successfully'
                }
            else:
                return {'success': False, 'product_id': None, 'message': 'Failed to create product'}
                
        except Exception as e:
            print(f"Error creating product: {str(e)}")
            return {'success': False, 'product_id': None, 'message': f'Error: {str(e)}'}

    def update_product(self, product_id, vendor_id, product_data, tag_names=None):
        """
        Update an existing product
        
        Args:
            product_id (str): The product ID to update
            vendor_id (str): The vendor ID (for permission check)
            product_data (dict): Updated product information
            tag_names (list): Updated tag names
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            # Check if product exists and belongs to vendor
            check_sql = "SELECT Vendor_ID FROM Product WHERE Product_ID = %s"
            result = self.executor.execute_query_one(check_sql, (product_id,))
            
            if not result:
                return {'success': False, 'message': 'Product not found'}
            
            if result[0] != vendor_id:
                return {'success': False, 'message': 'Permission denied: Product belongs to another vendor'}
            
            # Build update query
            update_parts = []
            params = []
            
            if 'name' in product_data and product_data['name']:
                update_parts.append('Name = %s')
                params.append(product_data['name'].strip())
            
            if 'description' in product_data:
                update_parts.append('Description = %s')
                params.append(product_data['description'].strip())
            
            if 'price' in product_data:
                price = float(product_data['price'])
                if price < 0:
                    return {'success': False, 'message': 'Price cannot be negative'}
                update_parts.append('Price = %s')
                params.append(price)
            
            if 'stock' in product_data:
                stock = int(product_data['stock'])
                if stock < 0:
                    return {'success': False, 'message': 'Stock cannot be negative'}
                update_parts.append('Stock = %s')
                params.append(stock)
                
                # Update status based on stock
                if stock == 0:
                    update_parts.append('Status = %s')
                    params.append('OutOfStock')
                elif stock > 0:
                    update_parts.append('Status = %s')
                    params.append('Active')
            
            if 'category' in product_data:
                update_parts.append('Category = %s')
                params.append(product_data['category'].strip())
            
            if 'image_url' in product_data:
                update_parts.append('Image_URL = %s')
                params.append(product_data['image_url'].strip())
            
            if 'status' in product_data:
                update_parts.append('Status = %s')
                params.append(product_data['status'].strip())
            
            if not update_parts:
                return {'success': True, 'message': 'No changes to update'}
            
            # Always update timestamp
            update_parts.append('Updated_At = NOW()')
            
            # Execute update
            params.append(product_id)
            update_sql = f"UPDATE Product SET {', '.join(update_parts)} WHERE Product_ID = %s"
            
            affected = self.executor.execute_update(update_sql, tuple(params))
            
            if affected > 0:
                # Update tags if provided
                if tag_names is not None:
                    self._update_product_tags(product_id, tag_names)
                
                return {'success': True, 'message': 'Product updated successfully'}
            else:
                return {'success': False, 'message': 'Failed to update product'}
                
        except Exception as e:
            print(f"Error updating product {product_id}: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    def _add_product_tags(self, product_id, tag_names):
        """
        Internal method to add tags to a product
        
        Args:
            product_id (str): Product ID
            tag_names (list): List of tag names
        """
        try:
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if not tag_name:
                    continue
                
                # Get or create tag
                tag_sql = "SELECT Tag_ID FROM Tag WHERE Name = %s"
                tag_result = self.executor.execute_query_one(tag_sql, (tag_name,))
                
                if tag_result:
                    tag_id = tag_result[0]
                else:
                    tag_id = str(uuid.uuid4())
                    insert_tag_sql = "INSERT INTO Tag (Tag_ID, Name, Created_At) VALUES (%s, %s, NOW())"
                    self.executor.execute_update(insert_tag_sql, (tag_id, tag_name))
                
                # Add product-tag association
                assoc_sql = "INSERT INTO Product_Tag (Product_ID, Tag_ID) VALUES (%s, %s)"
                self.executor.execute_update(assoc_sql, (product_id, tag_id))
                
        except Exception as e:
            print(f"Error adding tags to product: {str(e)}")
    
    def _update_product_tags(self, product_id, tag_names):
        """
        Internal method to update tags for a product
        
        Args:
            product_id (str): Product ID
            tag_names (list): New list of tag names
        """
        try:
            # Remove existing tags
            delete_sql = "DELETE FROM Product_Tag WHERE Product_ID = %s"
            self.executor.execute_update(delete_sql, (product_id,))
            
            # Add new tags
            self._add_product_tags(product_id, tag_names)
            
        except Exception as e:
            print(f"Error updating product tags: {str(e)}")