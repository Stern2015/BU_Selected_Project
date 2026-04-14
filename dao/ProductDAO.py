from dao.BaseDAO import BaseDAO


class ProductDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    def _build_public_filters(self, keyword=None, category=None, min_price=None, max_price=None, tags=None):
        clauses = [
            "p.Status = 'Active'",
            "v.Status = 'Active'"
        ]
        params = []

        if category:
            clauses.append("p.Category = %s")
            params.append(category)

        if min_price is not None:
            clauses.append("p.Price >= %s")
            params.append(min_price)

        if max_price is not None:
            clauses.append("p.Price <= %s")
            params.append(max_price)

        # Unified Search/Discovery Logic:
        # "where the tag matches any part of the product's name or its associated tags"
        search_terms = []
        if keyword:
            search_terms.append(keyword)
        if tags:
            search_terms.extend(tags)

        if search_terms:
            term_clauses = []
            for term in search_terms:
                like_pattern = f"%{term}%"
                # Matches Name OR associated tags
                term_clauses.append(f"""
                    (p.Name LIKE %s OR EXISTS (
                        SELECT 1 FROM Tagging tg_s
                        JOIN Tag t_s ON t_s.Tag_ID = tg_s.Tag_ID
                        WHERE tg_s.Product_ID = p.Product_ID
                          AND (t_s.Name LIKE %s OR LOWER(t_s.Name) = LOWER(%s))
                    ))
                """)
                params.extend([like_pattern, like_pattern, term])
            
            # Combine multiple terms with OR for broader discovery
            clauses.append("(" + " OR ".join(term_clauses) + ")")

        return " AND ".join(clauses), params

    def _format_product_card(self, row):
        tag_names = row["tag_names"].split("||") if row["tag_names"] else []
        stock = int(row["stock"] or 0)
        rating = float(row["rating"] or 0)

        if stock == 0 or row["status"] == "OutOfStock":
            status_class = "bg-yellow-100 text-yellow-800"
            status_label = "Out of Stock"
            stock_status = "Out of Stock"
            stock_class = "text-red-500 font-bold"
        else:
            status_class = "bg-green-100 text-green-800"
            status_label = "Active"
            stock_status = "In Stock"
            stock_class = "text-green-500"

        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"] or "",
            "price": float(row["price"]),
            "stock": stock,
            "category": row["category"],
            "image_url": row["image_url"],
            "vendor_id": row["vendor_id"],
            "status": row["status"],
            "rating": rating,
            "store_name": row["store_name"],
            "tag_names": tag_names,
            "status_class": status_class,
            "status_label": status_label,
            "stock_status": stock_status,
            "stock_class": stock_class,
            "price_formatted": f"${float(row['price']):.2f}",
        }

    def list_public_products(self, keyword=None, category=None, min_price=None, max_price=None,
                             tags=None, limit=20, offset=0):
        where_sql, params = self._build_public_filters(
            keyword=keyword,
            category=category,
            min_price=min_price,
            max_price=max_price,
            tags=tags
        )

        sql = f"""
            SELECT
                p.Product_ID AS id,
                p.Name AS name,
                COALESCE(p.Description, '') AS description,
                p.Price AS price,
                p.Stock AS stock,
                p.Category AS category,
                p.Image_URL AS image_url,
                p.Vendor_ID AS vendor_id,
                p.Status AS status,
                COALESCE(p.Rating, 0) AS rating,
                v.Store_Name AS store_name,
                COALESCE(GROUP_CONCAT(t.Name ORDER BY tg.Position SEPARATOR '||'), '') AS tag_names
            FROM Product p
            JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
            LEFT JOIN Tagging tg ON tg.Product_ID = p.Product_ID
            LEFT JOIN Tag t ON t.Tag_ID = tg.Tag_ID
            WHERE {where_sql}
            GROUP BY
                p.Product_ID, p.Name, p.Description, p.Price, p.Stock,
                p.Category, p.Image_URL, p.Vendor_ID, p.Status, p.Rating, v.Store_Name
            ORDER BY p.Created_At DESC
            LIMIT %s OFFSET %s
        """
        rows = self.executor.execute_query(sql, tuple(params + [limit, offset]))
        return [self._format_product_card(row) for row in rows]

    def count_public_products(self, keyword=None, category=None, min_price=None, max_price=None, tags=None):
        where_sql, params = self._build_public_filters(
            keyword=keyword,
            category=category,
            min_price=min_price,
            max_price=max_price,
            tags=tags
        )

        sql = f"""
            SELECT COUNT(DISTINCT p.Product_ID) AS total
            FROM Product p
            JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
            WHERE {where_sql}
        """
        result = self.executor.execute_query_one(sql, tuple(params))
        return int(result["total"] or 0) if result else 0

    def get_public_product_detail(self, product_id):
        sql = """
            SELECT
                p.Product_ID AS id,
                p.Name AS title,
                COALESCE(p.Description, '') AS description,
                p.Price AS price,
                p.Stock AS stock,
                p.Category AS category,
                p.Image_URL AS image,
                p.Vendor_ID AS vendor_id,
                p.Status AS status,
                COALESCE(p.Rating, 0) AS rating,
                v.Store_Name AS store_name,
                COALESCE(GROUP_CONCAT(t.Name ORDER BY tg.Position SEPARATOR '||'), '') AS tag_names
            FROM Product p
            JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
            LEFT JOIN Tagging tg ON tg.Product_ID = p.Product_ID
            LEFT JOIN Tag t ON t.Tag_ID = tg.Tag_ID
            WHERE p.Product_ID = %s
              AND p.Status != 'Inactive'
              AND v.Status = 'Active'
            GROUP BY
                p.Product_ID, p.Name, p.Description, p.Price, p.Stock,
                p.Category, p.Image_URL, p.Vendor_ID, p.Status, p.Rating, v.Store_Name
        """
        row = self.executor.execute_query_one(sql, (product_id,))
        if not row:
            return None

        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"] or "",
            "price": float(row["price"]),
            "stock": int(row["stock"] or 0),
            "category": row["category"],
            "image": row["image"],
            "vendor_id": row["vendor_id"],
            "status": row["status"],
            "rating": float(row["rating"] or 0),
            "store_name": row["store_name"],
            "tags": row["tag_names"].split("||") if row["tag_names"] else [],
        }

    def get_all_categories(self):
        sql = "SELECT Name FROM Category ORDER BY Name"
        rows = self.executor.execute_query(sql)
        return [row["Name"] for row in rows]

    def get_vendor_name(self, vendor_id):
        sql = "SELECT Store_Name FROM Vendor WHERE Vendor_ID = %s"
        result = self.executor.execute_query_one(sql, (vendor_id,))
        return result["Store_Name"] if result else "Unknown"

    ## List products for a specific vendor with status filtering.
    def list_vendor_products(self, vendor_id, tab='all', limit=20, offset=0):
        clauses = ["p.Vendor_ID = %s"]
        params = [vendor_id]

        if tab == 'active':
            clauses.append("p.Status = 'Active'")
        elif tab == 'inactive':
            clauses.append("p.Status = 'Inactive'")
        elif tab == 'inventory':
            clauses.append("p.Status != 'Inactive'")

        where_sql = " AND ".join(clauses)
        sql = f"""
            SELECT
                p.Product_ID AS id,
                p.Name AS name,
                COALESCE(p.Description, '') AS description,
                p.Price AS price,
                p.Stock AS stock,
                p.Category AS category,
                p.Image_URL AS image_url,
                p.Vendor_ID AS vendor_id,
                p.Status AS status,
                COALESCE(p.Rating, 0) AS rating,
                v.Store_Name AS store_name,
                COALESCE(GROUP_CONCAT(t.Name ORDER BY tg.Position SEPARATOR '||'), '') AS tag_names
            FROM Product p
            JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
            LEFT JOIN Tagging tg ON tg.Product_ID = p.Product_ID
            LEFT JOIN Tag t ON t.Tag_ID = tg.Tag_ID
            WHERE {where_sql}
            GROUP BY
                p.Product_ID, p.Name, p.Description, p.Price, p.Stock,
                p.Category, p.Image_URL, p.Vendor_ID, p.Status, p.Rating, v.Store_Name
            ORDER BY p.Created_At DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        rows = self.executor.execute_query(sql, tuple(params))
        return [self._format_product_card(row) for row in rows]
    
    ## Count products for a specific vendor with status filtering.
    def count_vendor_products(self, vendor_id, tab='all'):
        
        clauses = ["Vendor_ID = %s"]
        params = [vendor_id]

        if tab == 'active':
            clauses.append("Status = 'Active'")
        elif tab == 'inactive':
            clauses.append("Status = 'Inactive'")
        elif tab == 'inventory':
            clauses.append("Status != 'Inactive'")

        where_sql = " AND ".join(clauses)
        sql = f"SELECT COUNT(*) AS total FROM Product WHERE {where_sql}"
        result = self.executor.execute_query_one(sql, tuple(params))
        return int(result["total"] or 0) if result else 0

    # Add a new product with tags using a robust transaction.
    def add_product(self, product_id, name, description, price, stock, category, image_url, vendor_id, tags_text):
        operations = []
        
        # 1. Add product insert operation
        sql_product = """
            INSERT INTO Product (Product_ID, Name, Description, Price, Stock, Category, Image_URL, Vendor_ID, Status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Active')
        """
        params_product = (product_id, name, description, price, stock, category, image_url, vendor_id)
        
        # We'll use a manual transaction approach to handle the dynamic Tag IDs
        conn = self.executor.conn_manager.get_connection()
        cursor = conn.cursor()
        try:
            conn.ping(reconnect=True)
            conn.autocommit(False)
            
            # Insert product
            cursor.execute(sql_product, params_product)
            
            # Process tags
            if tags_text:
                tag_list = [t.strip() for t in tags_text.split(',') if t.strip()][:3]
                for i, tag_name in enumerate(tag_list):
                    # Ensure tag exists
                    cursor.execute("INSERT IGNORE INTO Tag (Name) VALUES (%s)", (tag_name,))
                    # Get ID
                    cursor.execute("SELECT Tag_ID FROM Tag WHERE Name = %s", (tag_name,))
                    row = cursor.fetchone()
                    if row:
                        tag_id = row['Tag_ID']
                        # Link tag to product
                        cursor.execute(
                            "INSERT INTO Tagging (Product_ID, Tag_ID, Position) VALUES (%s, %s, %s)",
                            (product_id, tag_id, i + 1)
                        )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error in add_product transaction: {e}")
            raise e
        finally:
            cursor.close()

    # Update existing product details and tags using a single transaction
    def update_product(self, product_id, name, description, price, stock, category, image_url, tags_text, status):
        conn = self.executor.conn_manager.get_connection()
        cursor = conn.cursor()
        try:
            conn.ping(reconnect=True)
            conn.autocommit(False)

            # 1. Update basic info
            sql_update = """
                UPDATE Product SET 
                    Name = %s, Description = %s, Price = %s, Stock = %s, 
                    Category = %s, Image_URL = %s, Status = %s, Updated_At = NOW()
                WHERE Product_ID = %s
            """
            params_update = (name, description, price, stock, category, image_url, status, product_id)
            cursor.execute(sql_update, params_update)

            # 2. Update tags: remove and re-add
            cursor.execute("DELETE FROM Tagging WHERE Product_ID = %s", (product_id,))
            
            if tags_text:
                tag_list = [t.strip() for t in tags_text.split(',') if t.strip()][:3]
                for i, tag_name in enumerate(tag_list):
                    cursor.execute("INSERT IGNORE INTO Tag (Name) VALUES (%s)", (tag_name,))
                    cursor.execute("SELECT Tag_ID FROM Tag WHERE Name = %s", (tag_name,))
                    row = cursor.fetchone()
                    if row:
                        cursor.execute(
                            "INSERT INTO Tagging (Product_ID, Tag_ID, Position) VALUES (%s, %s, %s)",
                            (product_id, row['Tag_ID'], i + 1)
                        )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error in update_product transaction: {e}")
            raise e
        finally:
            cursor.close()
    # Toggle product status between Active and Inactive
    def toggle_status(self, product_id):
        sql = """
            UPDATE Product 
            SET Status = CASE WHEN Status = 'Active' THEN 'Inactive' ELSE 'Active' END,
                Updated_At = NOW()
            WHERE Product_ID = %s
        """
        return self.executor.execute_update(sql, (product_id,))

    ## Update product stock quantity and manage Status
    def update_stock(self, product_id, amount, action):
        if action == 'increase':
            sql = """
                UPDATE Product 
                SET Stock = Stock + %s, 
                    Status = CASE WHEN Status = 'OutOfStock' THEN 'Active' ELSE Status END,
                    Updated_At = NOW() 
                WHERE Product_ID = %s
            """
        elif action == 'decrease':
            sql = """
                UPDATE Product 
                SET Stock = GREATEST(0, Stock - %s), 
                    Status = CASE WHEN Stock - %s <= 0 AND Status = 'Active' THEN 'OutOfStock' ELSE Status END,
                    Updated_At = NOW() 
                WHERE Product_ID = %s
            """
            return self.executor.execute_update(sql, (amount, amount, product_id))
        else:
            return 0
        return self.executor.execute_update(sql, (amount, product_id))

    ## Fetch multiple product details in one query.
    def get_products_by_ids(self, pids):
        
        if not pids:
            return []
        
        format_strings = ','.join(['%s'] * len(pids))
        sql = f"""
            SELECT p.Product_ID as id, p.Name as title, p.Price as price, 
                   p.Image_URL as image, p.Vendor_ID as vendor_id, v.Store_Name as vendor_name
            FROM Product p
            JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
            WHERE p.Product_ID IN ({format_strings})
        """
        return self.executor.execute_query(sql, tuple(pids))

    # Get aggregate stats for a vendor in one query.
    def get_vendor_stats(self, vendor_id):
        
        sql = """
            SELECT 
                COUNT(*) as total_products,
                SUM(CASE WHEN Status = 'Active' THEN 1 ELSE 0 END) as active_products,
                SUM(Stock) as total_stock,
                SUM(CASE WHEN Stock = 0 THEN 1 ELSE 0 END) as out_of_stock,
                SUM(CASE WHEN Status = 'Inactive' THEN 1 ELSE 0 END) as inactive_products
            FROM Product
            WHERE Vendor_ID = %s
        """
        return self.executor.execute_query_one(sql, (vendor_id,))
