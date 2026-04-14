from dao.BaseDAO import BaseDAO


class TagDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    def get_products_by_tags(self, tag_names, operator='OR', limit=20, offset=0):
        cleaned_tags = [tag.strip().lower() for tag in (tag_names or []) if tag and tag.strip()]
        if not cleaned_tags:
            return []

        placeholders = ", ".join(["%s"] * len(cleaned_tags))

        if operator.upper() == 'AND':
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
                    COALESCE(GROUP_CONCAT(DISTINCT t_all.Name ORDER BY tg_all.Position SEPARATOR '||'), '') AS tag_names
                FROM Product p
                JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
                JOIN Tagging tg_filter ON tg_filter.Product_ID = p.Product_ID
                JOIN Tag t_filter ON t_filter.Tag_ID = tg_filter.Tag_ID
                LEFT JOIN Tagging tg_all ON tg_all.Product_ID = p.Product_ID
                LEFT JOIN Tag t_all ON t_all.Tag_ID = tg_all.Tag_ID
                WHERE p.Status = 'Active'
                  AND v.Status = 'Active'
                  AND LOWER(t_filter.Name) IN ({placeholders})
                GROUP BY
                    p.Product_ID, p.Name, p.Description, p.Price, p.Stock,
                    p.Category, p.Image_URL, p.Vendor_ID, p.Status, p.Rating, v.Store_Name
                HAVING COUNT(DISTINCT CASE WHEN LOWER(t_filter.Name) IN ({placeholders}) THEN t_filter.Name END) = %s
                ORDER BY p.Created_At DESC
                LIMIT %s OFFSET %s
            """
            params = tuple(cleaned_tags + cleaned_tags + [len(cleaned_tags), limit, offset])
        else:
            # Discovery mode: matches tag names OR product names
            # Build OR clauses for each tag to match either Tag.Name or Product.Name
            discovery_clauses = []
            for _ in cleaned_tags:
                discovery_clauses.append("(LOWER(t_filter.Name) = %s OR p.Name LIKE %s)")
            
            where_discovery = " OR ".join(discovery_clauses)
            
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
                    COALESCE(GROUP_CONCAT(DISTINCT t_all.Name ORDER BY tg_all.Position SEPARATOR '||'), '') AS tag_names
                FROM Product p
                JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
                LEFT JOIN Tagging tg_filter ON tg_filter.Product_ID = p.Product_ID
                LEFT JOIN Tag t_filter ON t_filter.Tag_ID = tg_filter.Tag_ID
                LEFT JOIN Tagging tg_all ON tg_all.Product_ID = p.Product_ID
                LEFT JOIN Tag t_all ON t_all.Tag_ID = tg_all.Tag_ID
                WHERE p.Status = 'Active'
                  AND v.Status = 'Active'
                  AND ({where_discovery})
                GROUP BY
                    p.Product_ID, p.Name, p.Description, p.Price, p.Stock,
                    p.Category, p.Image_URL, p.Vendor_ID, p.Status, p.Rating, v.Store_Name
                ORDER BY p.Created_At DESC
                LIMIT %s OFFSET %s
            """
            discovery_params = []
            for tag in cleaned_tags:
                discovery_params.extend([tag, f"%{tag}%"])
            params = tuple(discovery_params + [limit, offset])

        rows = self.executor.execute_query(sql, params)

        products = []
        for row in rows:
            tag_list = row["tag_names"].split("||") if row["tag_names"] else []
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

            products.append({
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
                "tag_names": tag_list,
                "status_class": status_class,
                "status_label": status_label,
                "stock_status": stock_status,
                "stock_class": stock_class,
                "price_formatted": f"${float(row['price']):.2f}",
            })

        return products

    def count_products_by_tags(self, tag_names, operator='OR'):
        cleaned_tags = [tag.strip().lower() for tag in (tag_names or []) if tag and tag.strip()]
        if not cleaned_tags:
            return 0

        placeholders = ", ".join(["%s"] * len(cleaned_tags))

        if operator.upper() == 'AND':
            sql = f"""
                SELECT COUNT(*) AS total
                FROM (
                    SELECT p.Product_ID
                    FROM Product p
                    JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
                    JOIN Tagging tg ON tg.Product_ID = p.Product_ID
                    JOIN Tag t ON t.Tag_ID = tg.Tag_ID
                    WHERE p.Status = 'Active'
                      AND v.Status = 'Active'
                      AND LOWER(t.Name) IN ({placeholders})
                    GROUP BY p.Product_ID
                    HAVING COUNT(DISTINCT t.Name) = %s
                ) matched_products
            """
            params = tuple(cleaned_tags + [len(cleaned_tags)])
        else:
            discovery_clauses = []
            for _ in cleaned_tags:
                discovery_clauses.append("(LOWER(t.Name) = %s OR p.Name LIKE %s)")
            where_discovery = " OR ".join(discovery_clauses)

            sql = f"""
                SELECT COUNT(DISTINCT p.Product_ID) AS total
                FROM Product p
                JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
                LEFT JOIN Tagging tg ON tg.Product_ID = p.Product_ID
                LEFT JOIN Tag t ON t.Tag_ID = tg.Tag_ID
                WHERE p.Status = 'Active'
                  AND v.Status = 'Active'
                  AND ({where_discovery})
            """
            discovery_params = []
            for tag in cleaned_tags:
                discovery_params.extend([tag, f"%{tag}%"])
            params = tuple(discovery_params)

        result = self.executor.execute_query_one(sql, params)
        return int(result["total"] or 0) if result else 0

    def get_popular_tags(self, limit=20):
        sql = """
            SELECT
                t.Name AS name,
                COUNT(DISTINCT tg.Product_ID) AS usage_count
            FROM Tag t
            JOIN Tagging tg ON tg.Tag_ID = t.Tag_ID
            JOIN Product p ON p.Product_ID = tg.Product_ID
            JOIN Vendor v ON v.Vendor_ID = p.Vendor_ID
            WHERE p.Status = 'Active' AND v.Status = 'Active'
            GROUP BY t.Tag_ID, t.Name
            ORDER BY usage_count DESC, t.Name ASC
            LIMIT %s
        """
        rows = self.executor.execute_query(sql, (limit,))
        return [
            {
                "name": row["name"],
                "usage_count": int(row["usage_count"] or 0)
            }
            for row in rows
        ]

    def get_tags_by_product(self, product_id):
        sql = """
            SELECT t.Name
            FROM Tag t
            JOIN Tagging tg ON tg.Tag_ID = t.Tag_ID
            WHERE tg.Product_ID = %s
            ORDER BY tg.Position
        """
        rows = self.executor.execute_query(sql, (product_id,))
        return [row["Name"] for row in rows]
