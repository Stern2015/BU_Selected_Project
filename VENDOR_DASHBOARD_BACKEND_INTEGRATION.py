"""
Vendor Dashboard Backend Integration Guide
Quick implementation guide for Flask route handlers
"""

# ============================================================
# REQUIRED FLASK ROUTE HANDLER
# ============================================================

from flask import render_template, request, redirect, url_for, flash, session
from services.vendor_service import VendorService

vendor_service = VendorService()

# Main dashboard route
@app.route('/vendor/dashboard')
@app.route('/vendor/dashboard/<tab>')
def vendor_dashboard(tab='overview'):
    """
    Render vendor dashboard with business information and statistics
    
    Route: GET /vendor/dashboard
    Optional: /vendor/dashboard/overview | /vendor/dashboard/recent_products | /vendor/dashboard/orders | /vendor/dashboard/analytics
    
    Returns: Rendered vendor_dashboard.html template
    """
    
    # Authentication check - ensure user is logged in and is a vendor
    if 'user' not in session or not has_role(session['user'], ROLE_VENDOR):
        flash('You must be logged in as a vendor to access this page', 'error')
        return redirect(url_for('login', type='backend'))
    
    vendor_id = session['user']['id']
    
    # Get vendor information using VendorService
    vendor_info = vendor_service.get_vendor_by_id(vendor_id)
    
    if not vendor_info:
        flash('Vendor information not found', 'error')
        return redirect(url_for('login', type='backend'))
    
    # Add average rating to vendor_info
    vendor_info['average_rating'] = vendor_service.get_vendor_average_rating(vendor_id)
    
    # Get vendor statistics
    stats = vendor_service.get_vendor_stats(vendor_id)
    
    # Prepare context data
    context = {
        'tab': tab,
        'vendor_info': vendor_info,
        'stats': {
            'total_products': stats['total_products'] if stats else 0,
            'active_products': stats['active_products'] if stats else 0,
            'total_stock': 0,  # TODO: Calculate from product stock
            'out_of_stock': 0,  # TODO: Count products with stock=0
        },
        'recent_activity': [],  # TODO: Fetch from activity log
        'product_status': [],  # TODO: Get product status distribution
        'low_stock_products': [],  # TODO: Products with low inventory
        'recent_products': [],  # TODO: Recently added/modified products
        'recent_orders': [],  # TODO: Recent orders for this vendor
        'analytics': {  # TODO: Calculate analytics
            'total_sales': 0,
            'total_orders': 0,
            'avg_order_value': 0,
            'top_products': []
        }
    }
    
    return render_template('vendor_dashboard.html', **context)


# ============================================================
# UPDATE VENDOR INFORMATION ROUTE
# ============================================================

@app.route('/vendor/update-info', methods=['POST'])
def update_vendor_info():
    """
    Handle vendor information update from dashboard modal form
    
    Route: POST /vendor/update-info
    Expected POST data:
        - business_name (str, optional): New store name
        - geographical_presence (str, optional): New location
    
    Returns: Redirect to /vendor/dashboard with success/error message
    """
    
    # Authentication check
    if 'user' not in session or not has_role(session['user'], ROLE_VENDOR):
        flash('Unauthorized access', 'error')
        return redirect(url_for('login', type='backend'))
    
    vendor_id = session['user']['id']
    
    # Get form data
    business_name = request.form.get('business_name', '').strip()
    geographical_presence = request.form.get('geographical_presence', '').strip()
    
    # Validation
    if not business_name and not geographical_presence:
        flash('Please provide at least one field to update', 'warning')
        return redirect(url_for('vendor_dashboard'))
    
    if business_name and len(business_name) < 3:
        flash('Business name must be at least 3 characters long', 'error')
        return redirect(url_for('vendor_dashboard'))
    
    if geographical_presence and len(geographical_presence) < 2:
        flash('Location must be at least 2 characters long', 'error')
        return redirect(url_for('vendor_dashboard'))
    
    # Update vendor information using VendorService
    result = vendor_service.update_vendor_info(
        vendor_id=vendor_id,
        business_name=business_name if business_name else None,
        geographical_presence=geographical_presence if geographical_presence else None
    )
    
    if result['success']:
        flash('Vendor information updated successfully!', 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('vendor_dashboard'))


# ============================================================
# TODO: ADDITIONAL ROUTES FOR VENDOR FEATURES
# ============================================================

# Product Management
# @app.route('/vendor/products')
# def vendor_products():
#     """Product management page for vendors"""
#     pass

# Order Management  
# @app.route('/vendor/orders')
# def vendor_orders():
#     """Order management page for vendors"""
#     pass

# ============================================================
# EXAMPLE DATABASE QUERIES FOR CONTEXT DATA
# ============================================================

"""
Pseudo-code for fetching additional context data:

Calculate Total Stock:
```python
total_stock_sql = "SELECT SUM(Stock) FROM Product WHERE Vendor_ID = %s AND Status != 'Inactive'"
result = executor.execute_query_one(total_stock_sql, (vendor_id,))
total_stock = result[0] if result and result[0] else 0
```

Count Out of Stock:
```python
out_of_stock_sql = "SELECT COUNT(*) FROM Product WHERE Vendor_ID = %s AND Stock = 0"
result = executor.execute_query_one(out_of_stock_sql, (vendor_id,))
out_of_stock = result[0] if result else 0
```

Get Low Stock Products:
```python
low_stock_sql = '''
    SELECT Product_ID, Name, Stock FROM Product 
    WHERE Vendor_ID = %s AND Stock > 0 AND Stock <= 10
    ORDER BY Stock ASC
'''
low_stock_products = executor.execute_query(low_stock_sql, (vendor_id,))
```

Get Recent Products:
```python
recent_products_sql = '''
    SELECT Product_ID, Name, Price, Stock, Status, Image_URL
    FROM Product
    WHERE Vendor_ID = %s
    ORDER BY Created_At DESC
    LIMIT 10
'''
recent_products = executor.execute_query(recent_products_sql, (vendor_id,))
```

Get Recent Orders (requires Order & OrderItem tables):
```python
recent_orders_sql = '''
    SELECT o.Order_ID, o.Customer_ID, COUNT(oi.OrderItem_ID) as item_count,
           SUM(oi.Price * oi.Quantity) as amount, o.Status, o.Created_At
    FROM Order o
    JOIN OrderItem oi ON o.Order_ID = oi.Order_ID
    JOIN Product p ON oi.Product_ID = p.Product_ID
    WHERE p.Vendor_ID = %s
    GROUP BY o.Order_ID
    ORDER BY o.Created_At DESC
    LIMIT 10
'''
recent_orders = executor.execute_query(recent_orders_sql, (vendor_id,))
```
"""


# ============================================================
# TEMPLATE RENDERING EXAMPLE
# ============================================================

"""
Complete context example for template rendering:

context_data = {
    'tab': 'overview',
    
    # Vendor information (from VendorService)
    'vendor_info': {
        'vendor_id': 'u2',
        'business_name': 'Digital Store',
        'geographical_presence': 'Beijing',
        'average_rating': 4.8,
        'status': 'Active'
    },
    
    # Statistics
    'stats': {
        'total_products': 42,
        'active_products': 38,
        'total_stock': 1250,
        'out_of_stock': 4
    },
    
    # Recent activity
    'recent_activity': [
        {
            'title': 'New Product Added',
            'description': 'High-Performance Laptop added to catalog',
            'time': '2 hours ago',
            'icon': 'package-plus',
            'icon_bg': 'bg-indigo-50',
            'icon_color': 'text-indigo-600'
        },
        {
            'title': 'Order Received',
            'description': 'Customer ordered 2x Wireless Headphones',
            'time': '4 hours ago',
            'icon': 'shopping-cart',
            'icon_bg': 'bg-green-50',
            'icon_color': 'text-green-600'
        }
    ],
    
    # Product status distribution
    'product_status': [
        {'status': 'Active', 'count': 38, 'percentage': 90, 'color': 'bg-green-500'},
        {'status': 'Out of Stock', 'count': 3, 'percentage': 7, 'color': 'bg-yellow-500'},
        {'status': 'Inactive', 'count': 1, 'percentage': 3, 'color': 'bg-gray-500'}
    ],
    
    # Low stock alerts
    'low_stock_products': [
        {
            'id': 'p7',
            'name': 'USB-C Cable',
            'stock': 3
        }
    ],
    
    # Recent products list
    'recent_products': [
        {
            'id': 'p1',
            'name': 'High-Performance Laptop',
            'price': 5999.00,
            'stock': 50,
            'status': 'Active',
            'image_url': 'https://...'
        }
    ],
    
    # Recent orders
    'recent_orders': [
        {
            'id': 'ORDER-001',
            'customer_name': 'John Doe',
            'item_count': 2,
            'amount': 2299.00,
            'status': 'Pending',
            'date': '2024-04-10'
        }
    ],
    
    # Analytics
    'analytics': {
        'total_sales': 48500.00,
        'total_orders': 25,
        'avg_order_value': 1940.00,
        'top_products': [
            {
                'id': 'p1',
                'name': 'High-Performance Laptop',
                'sales_count': 8,
                'total_revenue': 47992.00,
                'image_url': 'https://...'
            }
        ]
    }
}

render_template('vendor_dashboard.html', **context_data)
"""
