import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from driver.sql_executor import SQL_Executor
from dao.ProductDAO import ProductDAO
from dao.TagDAO import TagDAO
from dao.UserDAO import UserDAO
from services.vendor_service import VendorService
from services.order_service import OrderService
from services.auth_service import Auth_Service

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_bu_selected'

product_dao = ProductDAO()
tag_dao = TagDAO()
user_dao = UserDAO()
vendor_service = VendorService()
sql_executor = SQL_Executor()

# Role Bitmasks
ROLE_CUSTOMER = 1
ROLE_VENDOR = 2
ROLE_ADMIN = 4

def has_role(user, role_flag):
    return bool(user.get('role', 0) & role_flag)

def get_vendor_name(vid):
    return product_dao.get_vendor_name(vid)

def get_product(pid):
    return product_dao.get_public_product_detail(pid)


@app.context_processor
def inject_globals():
    return dict(
        get_vendor_name=get_vendor_name, 
        get_product=get_product,
        ROLE_CUSTOMER=ROLE_CUSTOMER,
        ROLE_VENDOR=ROLE_VENDOR,
        ROLE_ADMIN=ROLE_ADMIN,
        has_role=has_role
    )

# --- PUBLIC & AUTH ROUTES ---

@app.route('/')
def index():
    """Home page redirects to product browsing page"""
    return redirect(url_for('products'))

@app.route('/product/<pid>')
def product_detail(pid):
    product = product_dao.get_public_product_detail(pid)
    if not product:
        return "Product not found", 404

    return render_template('product.html', product=product)


@app.route('/products')
def products():
    keyword = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    min_price_raw = request.args.get('min_price', '').strip()
    max_price_raw = request.args.get('max_price', '').strip()
    tags_raw = request.args.get('tags', '').strip()

    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (TypeError, ValueError):
        page = 1

    min_price = float(min_price_raw) if min_price_raw else None
    max_price = float(max_price_raw) if max_price_raw else None
    tag_list = [tag.strip() for tag in tags_raw.split(',') if tag.strip()]

    page_size = 20
    offset = (page - 1) * page_size

    if tag_list and not keyword and not category and min_price is None and max_price is None:
        products = tag_dao.get_products_by_tags(
            tag_names=tag_list,
            operator='OR',
            limit=page_size,
            offset=offset
        )
        total_products = tag_dao.count_products_by_tags(
            tag_names=tag_list,
            operator='OR'
        )
    else:
        products = product_dao.list_public_products(
            keyword=keyword or None,
            category=category or None,
            min_price=min_price,
            max_price=max_price,
            tags=tag_list or None,
            limit=page_size,
            offset=offset
        )
        total_products = product_dao.count_public_products(
            keyword=keyword or None,
            category=category or None,
            min_price=min_price,
            max_price=max_price,
            tags=tag_list or None
        )

    categories = product_dao.get_all_categories()
    popular_tags = tag_dao.get_popular_tags(limit=20)
    total_pages = (total_products + page_size - 1) // page_size if total_products else 0

    return render_template(
        'products.html',
        products=products,
        categories=categories,
        popular_tags=popular_tags,
        total_products=total_products,
        page=page,
        total_pages=total_pages,
        request=request
    )


auth = Auth_Service()

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_type = request.args.get('type', 'customer') # 'customer' or 'backend'
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        ret = auth.verify_user_account(username, password)
        if not ret:
            flash('Invalid username or password')
            return render_template('login.html', login_type=login_type)

        user_obj = auth.get_user_info(username)
        if not user_obj:
            flash('User info not found')
            return render_template('login.html', login_type=login_type)

        user = user_obj.get_dict()
        if user:
            if login_type == 'customer' and not has_role(user, ROLE_CUSTOMER):
                flash('Please use the backend login for admin/vendor accounts.')
            elif login_type == 'backend' and not has_role(user, ROLE_VENDOR | ROLE_ADMIN):
                flash('Please use the customer login.')
            else:
                session['user'] = user
                session['login_type'] = login_type
                if login_type == 'customer':
                    return redirect(url_for('index'))
                else:
                    if has_role(user, ROLE_ADMIN): return redirect(url_for('admin_dashboard'))
                    elif has_role(user, ROLE_VENDOR): return redirect(url_for('vendor_dashboard'))
                    else: return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html', login_type=login_type)

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('login_type', None)
    return redirect(url_for('index'))

# --- CUSTOMER ROUTES ---

@app.route('/cart')
def view_cart():
    if 'user' not in session or session.get('login_type') != 'customer' or not has_role(session['user'], ROLE_CUSTOMER): return redirect(url_for('login', type='customer'))
    cart_items = session.get('cart', [])
    
    if not cart_items:
        return render_template('cart.html', cart_items=[], total=0)

    # Batch fetch product details
    pids = [item['product_id'] for item in cart_items]
    product_details = product_dao.get_products_by_ids(pids)
    
    # Map for easy lookup in template
    product_map = {p['id']: p for p in product_details}
    
    enriched_items = []
    total = 0
    for item in cart_items:
        p_info = product_map.get(item['product_id'])
        if p_info:
            item_with_details = item.copy()
            item_with_details['product'] = p_info
            enriched_items.append(item_with_details)
            total += p_info['price'] * item['quantity']
            
    return render_template('cart.html', cart_items=enriched_items, total=total)

@app.route('/cart/add/<pid>', methods=['POST'])
def add_to_cart(pid):
    if 'user' not in session or session.get('login_type') != 'customer' or not has_role(session['user'], ROLE_CUSTOMER): return redirect(url_for('login', type='customer'))
    try:
        qty_to_add = int(request.form.get('quantity') or 1)
    except ValueError:
        qty_to_add = 1
    
    p = get_product(pid)
    if not p: return "Not found", 404
    
    vendor = vendor_service.get_vendor_by_id(p['vendor_id'])
    if not vendor or vendor['status'] != 'Active' or p['status'] != 'Active':
        flash('This product is currently unavailable.')
        return redirect(request.referrer or url_for('index'))
    
    if 'cart' not in session: session['cart'] = []
    cart = session['cart']
    
    existing = next((i for i in cart if i['product_id'] == pid), None)
    current_qty = existing['quantity'] if existing else 0
    new_qty = current_qty + qty_to_add
    
    if new_qty > p['stock']:
        flash(f"Insufficient stock! Only {p['stock']} available.")
        new_qty = p['stock']
        
    if new_qty <= 0:
        if existing: cart.remove(existing)
    else:
        if existing:
            existing['quantity'] = new_qty
        else:
            cart.append({'product_id': pid, 'quantity': new_qty})
        if new_qty > current_qty:
            flash('Added to cart!')
            
    session.modified = True
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/update/<pid>', methods=['POST'])
def update_cart(pid):
    if 'user' not in session or session.get('login_type') != 'customer' or not has_role(session['user'], ROLE_CUSTOMER): return redirect(url_for('login', type='customer'))
    action = request.form.get('action')
    
    p = get_product(pid)
    cart = session.get('cart', [])
    existing = next((i for i in cart if i['product_id'] == pid), None)
    
    if existing and p:
        if action == 'increase':
            if existing['quantity'] + 1 > p['stock']:
                flash('Insufficient stock!')
            else:
                existing['quantity'] += 1
        elif action == 'decrease':
            existing['quantity'] -= 1
            if existing['quantity'] <= 0:
                cart.remove(existing)
        session.modified = True
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<pid>', methods=['POST'])
def remove_from_cart(pid):
    if 'user' not in session or session.get('login_type') != 'customer': return redirect(url_for('login', type='customer'))
    if 'cart' in session:
        session['cart'] = [i for i in session['cart'] if i['product_id'] != pid]
        session.modified = True
    return redirect(url_for('view_cart'))

@app.route('/cart/checkout', methods=['POST'])
def checkout():
    if 'user' not in session or session.get('login_type') != 'customer':
        return redirect(url_for('login', type='customer'))
    uid  = session['user']['id']
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('view_cart'))

    shipping_address = request.form.get('shipping_address', '').strip()
    if not shipping_address:
        flash('Shipping address is required.')
        return redirect(url_for('view_cart'))

    # Check stock and vendor status
    for item in cart:
        p = get_product(item['product_id'])
        if not p:
            flash(f"A product in your cart is no longer available.")
            return redirect(url_for('view_cart'))
        
        vendor = vendor_service.get_vendor_by_id(p['vendor_id'])
        if not vendor or vendor['status'] != 'Active' or p['status'] != 'Active':
            flash(f"Sorry, {p['title']} is currently unavailable.")
            return redirect(url_for('view_cart'))
        if item['quantity'] > p['stock']:
            flash(f"Sorry, {p['title']} only has {p['stock']} left in stock.")
            return redirect(url_for('view_cart'))

    # Write to MySQL via OrderService
    try:
        order_service = OrderService()
        order_id = order_service.create_order(
            customer_id=uid,
            shipping_address=shipping_address,
            cart_items=cart,
            get_product_fn=get_product
        )
        if not order_id:
            flash('Failed to create order. Please try again.')
            return redirect(url_for('view_cart'))
    except Exception as e:
        flash(f'Failed to place order: {str(e)}')
        return redirect(url_for('view_cart'))

    # Clear cart (OrderDAO already handles stock update in transaction)
    session['cart'] = []
    session.modified = True

    flash('Order placed successfully!')
    return redirect(url_for('order_detail', oid=order_id))

@app.route('/orders')
def order_list():
    if 'user' not in session or session.get('login_type') != 'customer' or not has_role(session['user'], ROLE_CUSTOMER): 
        return redirect(url_for('login', type='customer'))
    uid = session['user']['id']
    
    # Get from MySQL
    order_service = OrderService()
    my_orders = order_service.get_customer_orders(uid)
    return render_template('orders.html', orders=my_orders)

@app.route('/orders/<oid>')
def order_detail(oid):
    if 'user' not in session: 
        return redirect(url_for('login'))
    
    # Get from MySQL
    order_service = OrderService()
    order = order_service.get_order_details(oid)
    if not order: 
        return "Order not found", 404
        
    user = session['user']
    login_type = session.get('login_type')

    # 1. Admin: can see everything
    if has_role(user, ROLE_ADMIN):
        return render_template('order_detail.html', order=order)

    # 2. Backend / Vendor View
    if login_type == 'backend' and has_role(user, ROLE_VENDOR):
        # Filter sub_orders: only keep items belonging to this vendor
        original_count = len(order.get('sub_orders', []))
        order['sub_orders'] = [so for so in order.get('sub_orders', []) if so['merchant_id'] == user['id']]
        
        # If this vendor has no sub-orders in this main order, deny access
        if not order['sub_orders'] and original_count > 0:
            flash("Permission denied: No items from your store in this order.")
            return redirect(url_for('vendor_dashboard'))
            
        return render_template('order_detail.html', order=order)

    # 3. Customer View
    if order['customer_id'] != user['id']:
        flash("Permission denied.")
        return redirect(url_for('index'))
            
    return render_template('order_detail.html', order=order)

@app.route('/orders/<oid>/cancel', methods=['POST'])
def cancel_order(oid):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    order_service = OrderService()
    success = order_service.cancel_order(oid)
    if success:
        flash('Order cancelled successfully.')
    else:
        flash('Cannot cancel order. It might already be shipped.')
        
    return redirect(url_for('order_detail', oid=oid))

@app.route('/orders/<oid>/remove_item/<item_id>', methods=['POST'])
def remove_order_item(oid, item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    order_service = OrderService()
    success = order_service.remove_item_from_order(item_id)
    if success:
        flash('Item removed from order.')
    else:
        flash('Cannot remove item. Order might already be shipped or item not found.')
        
    return redirect(url_for('order_detail', oid=oid))

# --- VENDOR ROUTES ---

@app.route('/vendor')
def vendor_dashboard():
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return redirect(url_for('login', type='backend'))

    vid = session['user']['id']
    tab = request.args.get('tab', 'overview')

    # Get vendor information from database
    vendor_data = vendor_service.get_vendor_by_id(vid)
    if not vendor_data:
        flash('Vendor profile not found.')
        return redirect(url_for('index'))

    vendor_status = vendor_data['status']
    
    vendor_info = {
        'id': vid,
        'vendor_id': vid,
        'business_name': vendor_data['business_name'],
        'average_rating': vendor_data['average_rating'],
        'geographical_presence': vendor_data['geographical_presence'],
        'status': vendor_status
    }

    # Calculate statistics from database efficiently
    db_stats = product_dao.get_vendor_stats(vid)
    
    stats = {
        'total_products': int(db_stats['total_products'] or 0),
        'active_products': int(db_stats['active_products'] or 0),
        'total_stock': int(db_stats['total_stock'] or 0),
        'out_of_stock': int(db_stats['out_of_stock'] or 0)
    }

    # Display different content based on tab
    if tab == 'recent_products':
        recent_products = product_dao.list_vendor_products(vid, limit=10)
        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             recent_products=recent_products,
                             tab=tab)

    elif tab == 'orders':
        # Get orders from database
        order_service = OrderService()
        vendor_orders = order_service.get_vendor_orders(vid)
        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             recent_orders=vendor_orders[:10],
                             tab=tab)

    elif tab == 'analytics':
        order_service = OrderService()
        vendor_orders = order_service.get_vendor_orders(vid)
        analytics = {
            'total_sales': sum(float(o['sub_total_amount']) for o in vendor_orders if o['status'] != 'cancelled'),
            'total_orders': len(vendor_orders),
            'avg_order_value': 0.0,
            'top_products': []
        }
        if analytics['total_orders'] > 0:
            analytics['avg_order_value'] = analytics['total_sales'] / analytics['total_orders']

        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             analytics=analytics,
                             tab=tab)

    else:
        # Overview tab
        total_p = stats['total_products']
        product_status = []
        status_map = [
            ('Active', stats['active_products'], 'bg-green-500'),
            ('OutOfStock', stats['out_of_stock'], 'bg-yellow-500'),
            ('Inactive', int(db_stats['inactive_products'] or 0), 'bg-gray-500')
        ]

        for status, count, color in status_map:
            percentage = (count / total_p * 100) if total_p > 0 else 0
            product_status.append({
                'status': status,
                'count': count,
                'percentage': percentage,
                'color': color
            })

        # Efficiently get low stock products
        sql_low_stock = "SELECT Product_ID as id, Name as name, Stock as stock FROM Product WHERE Vendor_ID = %s AND Stock > 0 AND Stock < 10 LIMIT 5"
        low_stock_products = sql_executor.execute_query(sql_low_stock, (vid,))

        recent_activity = [
            {
                'icon': 'package',
                'icon_bg': 'bg-blue-50',
                'icon_color': 'text-blue-600',
                'title': 'System Optimized',
                'description': 'Database connection pooling and query optimization enabled',
                'time': 'Just now'
            }
        ]

        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             product_status=product_status,
                             low_stock_products=low_stock_products,
                             recent_activity=recent_activity,
                             tab=tab)

# --- NEW VENDOR ROUTES ---

@app.route('/vendor/dashboard', methods=['GET'])
def vendor_dashboard_alt():
    """GET /vendor/dashboard - Render vendor dashboard page"""
    return vendor_dashboard()

@app.route('/vendor/onboard', methods=['POST'])
def vendor_onboard():
    """POST /vendor/onboard - Vendor onboarding"""
    if 'user' not in session or session.get('login_type') != 'backend':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    user_id = session['user']['id']
    
    # Get form data
    business_name = request.form.get('business_name', '').strip()
    geographical_presence = request.form.get('geographical_presence', '').strip()
    
    # Validate input
    if not business_name:
        flash('Business name is required.')
        return redirect(request.referrer or url_for('index'))
    
    if not geographical_presence:
        flash('Location is required.')
        return redirect(request.referrer or url_for('index'))
    
    # Check if user is already a vendor
    try:
        result = vendor_service.onboard_new_vendor(
            user_id=user_id,
            business_name=business_name,
            geographical_presence=geographical_presence
        )
        if not result.get('success'):
            flash(result.get('message') or 'Failed to onboard vendor.')
            return redirect(url_for('vendor_dashboard'))

        user = session['user']
        user['role'] |= ROLE_VENDOR
        session.modified = True

        flash(result.get('message') or f'Vendor onboarded successfully: {business_name}')
        return redirect(url_for('vendor_dashboard'))
    except Exception as e:
        flash(f'Error onboarding vendor: {str(e)}')
        return redirect(request.referrer or url_for('index'))

@app.route('/vendor/update', methods=['POST'])
def vendor_update():
    """POST /vendor/update - Update vendor information"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    vid = session['user']['id']
    
    # Get form data
    business_name = request.form.get('business_name', '').strip()
    geographical_presence = request.form.get('geographical_presence', '').strip()
    
    if not business_name and not geographical_presence:
        flash('No changes to update.')
        return redirect(url_for('vendor_dashboard'))

    result = vendor_service.update_vendor_info(
        vendor_id=vid,
        business_name=business_name if business_name else None,
        geographical_presence=geographical_presence if geographical_presence else None
    )

    if not result.get('success'):
        return jsonify({'success': False, 'message': result.get('message') or 'Update failed'}), 400

    flash(result.get('message') or 'Vendor information updated successfully.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Vendor updated successfully'})
    
    return redirect(url_for('vendor_dashboard'))

@app.route('/vendor/update-info', methods=['POST'])
def vendor_update_info():
    return vendor_update()

@app.route('/vendor/products/add', methods=['POST'])
def add_vendor_product():
    """POST /vendor/products/add - Create a new product"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    vid = session['user']['id']
    
    # Get form data
    product_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', 'General').strip()
    image_url = request.form.get('image_url', '').strip()
    tags = request.form.get('tags', '').strip()
    
    try:
        price = float(request.form.get('price', 0))
    except (ValueError, TypeError):
        flash('Invalid price value.')
        return redirect(url_for('vendor_products'))
    
    try:
        stock = int(request.form.get('stock', 0))
    except (ValueError, TypeError):
        flash('Invalid stock value.')
        return redirect(url_for('vendor_products'))
    
    if not product_name:
        flash('Product name is required.')
        return redirect(url_for('vendor_products'))
    
    # Create new product via DAO
    try:
        product_id = 'p' + str(uuid.uuid4().hex[:8]).lower()
        product_dao.add_product(
            product_id=product_id,
            name=product_name,
            description=description,
            price=price,
            stock=stock,
            category=category,
            image_url=image_url if image_url else 'https://picsum.photos/seed/product/400/300',
            vendor_id=vid,
            tags_text=tags
        )
        
        flash(f'Product "{product_name}" added successfully.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Product created successfully',
                'product_id': product_id
            })
        
        return redirect(url_for('vendor_products'))
    except Exception as e:
        flash(f'Error creating product: {str(e)}')
        return redirect(url_for('vendor_products'))

@app.route('/vendor/products')
def vendor_products():
    """Vendor product management page"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return redirect(url_for('login', type='backend'))

    vid = session['user']['id']
    tab = request.args.get('tab', 'all')
    page = int(request.args.get('page', 1))
    edit_product_id = request.args.get('edit')

    page_size = 20
    offset = (page - 1) * page_size
    
    products_list = product_dao.list_vendor_products(vid, tab=tab, limit=page_size, offset=offset)
    total_products = product_dao.count_vendor_products(vid, tab=tab)
    
    total_pages = (total_products + page_size - 1) // page_size if total_products > 0 else 0
    categories = product_dao.get_all_categories()
    popular_tags = tag_dao.get_popular_tags(limit=10)

    start_item = offset + 1 if total_products > 0 else 0
    end_item = min(offset + page_size, total_products)

    return render_template('vendor_products.html',
                         products=products_list,
                         categories=categories,
                         popular_tags=popular_tags,
                         total_products=total_products,
                         page=page,
                         total_pages=total_pages,
                         start_item=start_item,
                         end_item=end_item,
                         tab=tab,
                         edit_product_id=edit_product_id)

@app.route('/vendor/product/save', methods=['POST'])
def save_product():
    """Save product (create or update)"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return redirect(url_for('login', type='backend'))

    vid = session['user']['id']
    pid = request.form.get('product_id')

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', 'General').strip()

    try:
        price = float(request.form.get('price', 0))
        stock = int(request.form.get('stock', 0))
    except ValueError:
        flash('Invalid price or stock.')
        return redirect(url_for('vendor_products'))

    image_url = request.form.get('image_url', '').strip()
    tags_text = request.form.get('tags', '').strip()
    status = request.form.get('status', 'Active')

    if not name:
        flash('Product name is required')
        return redirect(url_for('vendor_products'))

    try:
        if pid:
            # Check ownership and update
            p = product_dao.get_public_product_detail(pid) # Also gets for vendor if exists
            if not p: # Might be inactive
                sql = "SELECT Vendor_ID FROM Product WHERE Product_ID = %s"
                row = sql_executor.execute_query_one(sql, (pid,))
                if row and row['Vendor_ID'] == vid:
                    product_dao.update_product(pid, name, description, price, stock, category, image_url, tags_text, status)
                    flash('Product updated successfully.')
                else:
                    flash('Product not found or permission denied.')
            elif p['vendor_id'] == vid:
                product_dao.update_product(pid, name, description, price, stock, category, image_url, tags_text, status)
                flash('Product updated successfully.')
            else:
                flash('Permission denied.')
        else:
            new_pid = 'p' + str(uuid.uuid4().hex[:8]).lower()
            product_dao.add_product(new_pid, name, description, price, stock, category, image_url, vid, tags_text)
            flash('Product added successfully.')
    except Exception as e:
        flash(f'Error saving product: {str(e)}')

    return redirect(url_for('vendor_products'))

@app.route('/vendor/product/<product_id>/toggle', methods=['POST'])
def toggle_product_status(product_id):
    """Toggle product status"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return redirect(url_for('login', type='backend'))

    vid = session['user']['id']
    # Check ownership
    sql = "SELECT Vendor_ID FROM Product WHERE Product_ID = %s"
    row = sql_executor.execute_query_one(sql, (product_id,))
    
    if row and row['Vendor_ID'] == vid:
        product_dao.toggle_status(product_id)
        flash('Product status toggled.')
    else:
        flash('Product not found or permission denied.')

    return redirect(url_for('vendor_products'))

@app.route('/vendor/product/<product_id>/stock', methods=['POST'])
def update_product_stock(product_id):
    """Update product stock (AJAX interface)"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    vid = session['user']['id']
    
    # Secure check: ensure product belongs to vendor
    sql = "SELECT Vendor_ID FROM Product WHERE Product_ID = %s"
    row = sql_executor.execute_query_one(sql, (product_id,))

    if not row or row['Vendor_ID'] != vid:
        return jsonify({'success': False, 'message': 'Product not found or permission denied'}), 404

    try:
        data = request.get_json()
        action = data.get('action')
        amount = int(data.get('amount', 0))

        if action not in ['increase', 'decrease']:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400

        product_dao.update_stock(product_id, amount, action)
        
        # Get updated info with explicit aliases to avoid case-sensitivity issues
        new_row = sql_executor.execute_query_one("SELECT Stock as stock, Status as status FROM Product WHERE Product_ID = %s", (product_id,))
        return jsonify({
            'success': True, 
            'stock': int(new_row['stock']), 
            'status': str(new_row['status'])
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/vendor/transaction/<sub_id>/ship', methods=['POST'])
def ship_order(sub_id):
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR): 
        return redirect(url_for('login', type='backend'))
    
    order_service = OrderService()
    # In a real system, we'd have a specific ship_sub_order method
    # For now, we use existing DAO method via service if available or direct SQL
    sql = "UPDATE sub_orders SET shipping_status = 'Shipped', status = 'shipped' WHERE sub_order_id = %s AND merchant_id = %s"
    sql_executor.execute_update(sql, (sub_id, session['user']['id']))
    
    flash('Order marked as shipped.')
    return redirect(url_for('vendor_dashboard', tab='orders'))

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_ADMIN): return redirect(url_for('login', type='backend'))
    
    vendors = vendor_service.get_all_vendors()
    # Format for template
    formatted_vendors = []
    for v in vendors:
        formatted_vendors.append({
            'id': v['Vendor_ID'],
            'name': v['Store_Name'],
            'location': v['Location'],
            'status': v['Status'],
            'rating': float(v['Rating']) if v['Rating'] is not None else 0.0
        })
        
    all_users = user_dao.get_all_users()
    available_users = [u for u in all_users if not has_role(u, ROLE_VENDOR) and not has_role(u, ROLE_ADMIN)]
    
    return render_template('admin.html', vendors=formatted_vendors, available_users=available_users)

@app.route('/admin/vendor/save', methods=['POST'])
def save_vendor():
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_ADMIN): return redirect(url_for('login', type='backend'))
    vid = request.form.get('id')
    name = request.form.get('name')
    location = request.form.get('location')
    user_id = request.form.get('user_id')
    
    if vid:
        result = vendor_service.update_vendor_info(
            vendor_id=vid,
            business_name=name if name else None,
            geographical_presence=location if location else None
        )
        if result.get('success'):
            flash('Vendor updated.')
        else:
            flash(result.get('message') or 'Failed to update vendor.')
    else:
        if not user_id:
            flash('Please select a user to bind to the new vendor.')
            return redirect(url_for('admin_dashboard'))
            
        result = vendor_service.onboard_new_vendor(user_id=user_id, business_name=name, geographical_presence=location)
        if not result.get('success'):
            flash(result.get('message') or 'Failed to create vendor.')
        else:
            # Upgrade user role in database
            sql = "UPDATE UserAccount SET Role_Bits = Role_Bits | %s WHERE User_ID = %s"
            sql_executor.execute_update(sql, (ROLE_VENDOR, user_id))
            flash('Vendor added and user role upgraded.')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/vendor/<vid>/toggle', methods=['POST'])
def toggle_vendor(vid):
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_ADMIN): return redirect(url_for('login', type='backend'))
    
    vendor = vendor_service.get_vendor_by_id(vid)
    if not vendor:
        flash('Vendor not found.')
        return redirect(url_for('admin_dashboard'))

    try:
        if vendor['status'] == 'Active':
            vendor_service.deactivate_vendor(vid)
            flash('Vendor deactivated.')
        else:
            vendor_service.activate_vendor(vid)
            flash('Vendor activated.')
    except Exception as e:
        flash(f'Failed to toggle vendor: {str(e)}')
        
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
