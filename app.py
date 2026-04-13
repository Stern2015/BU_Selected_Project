import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from services.vendor_service import VendorService
from services.product_service import ProductService
from services.auth_service import Auth_Service
from services.order_service import OrderService

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_bu_selected'

# Role Bitmasks
ROLE_CUSTOMER = 1
ROLE_VENDOR = 2
ROLE_ADMIN = 4

def has_role(user, role_flag):
    return bool(user.get('role', 0) & role_flag)

# In-memory Database
DB = {
    'users': [
        {'id': 'u1', 'username': 'admin', 'password': '123', 'role': ROLE_ADMIN | ROLE_CUSTOMER},
        {'id': 'u2', 'username': 'vendor1', 'password': '123', 'role': ROLE_VENDOR | ROLE_CUSTOMER},
        {'id': 'u3', 'username': 'vendor2', 'password': '123', 'role': ROLE_VENDOR | ROLE_CUSTOMER},
        {'id': 'u4', 'username': 'customer1', 'password': '123', 'role': ROLE_CUSTOMER},
    ],
    'vendors': [
        {'id': 'u2', 'name': 'Digital Store', 'rating': 4.8, 'location': 'Beijing', 'status': 'Active'},
        {'id': 'u3', 'name': 'Home Living', 'rating': 4.5, 'location': 'Shanghai', 'status': 'Active'},
    ],
    'categories': ['Electronics', 'Furniture', 'Clothing', 'Books'],
    'products': [
        {'id': 'p1', 'title': 'High-Performance Laptop', 'price': 5999, 'category': 'Electronics', 'tags': ['Computer', 'Tech'], 'vendor_id': 'u2', 'image': 'https://picsum.photos/seed/laptop/300/200', 'stock': 50, 'status': 'Active'},
        {'id': 'p2', 'title': 'Ergonomic Office Chair', 'price': 899, 'category': 'Furniture', 'tags': ['Office', 'Ergonomic'], 'vendor_id': 'u3', 'image': 'https://picsum.photos/seed/chair/300/200', 'stock': 120, 'status': 'Active'},
        {'id': 'p3', 'title': 'Wireless Headphones', 'price': 1299, 'category': 'Electronics', 'tags': ['Audio'], 'vendor_id': 'u2', 'image': 'https://picsum.photos/seed/headphone/300/200', 'stock': 200, 'status': 'Active'},
    ],
    'carts': {},  # user_id -> [{'product_id': 'p1', 'quantity': 1}]
    'orders': [],
    'sub_orders': []
}

def get_vendor_name(vid):
    for v in DB['vendors']:
        if v['id'] == vid: return v['name']
    return 'Unknown'

def get_product(pid):
    for p in DB['products']:
        if p['id'] == pid: return p
    return None

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
    p = get_product(pid)
    if not p: return "Product not found", 404

    v = next((v for v in DB['vendors'] if v['id'] == p['vendor_id']), None)
    if not v or v['status'] != 'Active':
        flash('This product is currently unavailable.')
        return redirect(url_for('index'))

    return render_template('product.html', product=p)

@app.route('/products')
def products():
    """Product browsing page"""
    # Get query parameters
    keyword = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    tags = request.args.get('tags', '').strip()
    page = int(request.args.get('page', 1))

    # Convert price parameters
    min_price = float(min_price) if min_price and min_price.replace('.', '', 1).isdigit() else None
    max_price = float(max_price) if max_price and max_price.replace('.', '', 1).isdigit() else None

    # Get product data (currently using in-memory database)
    filtered_products = []
    for p in DB['products']:
        if p['status'] != 'Active':
            continue

        # Check if vendor is active
        v = next((v for v in DB['vendors'] if v['id'] == p['vendor_id']), None)
        if not v or v['status'] != 'Active':
            continue

        # Keyword filtering
        if keyword and keyword.lower() not in p['title'].lower():
            continue

        # Category filtering
        if category and p['category'] != category:
            continue

        # Price filtering
        if min_price is not None and p['price'] < min_price:
            continue
        if max_price is not None and p['price'] > max_price:
            continue

        # Tag filtering
        if tags:
            tag_list = [t.strip().lower() for t in tags.split(',')]
            product_tags = [t.lower() for t in p.get('tags', [])]
            if not any(tag in product_tags for tag in tag_list):
                continue

        # Format product data
        product_data = {
            'id': p['id'],
            'name': p['title'],
            'description': '',
            'price': p['price'],
            'stock': p['stock'],
            'category': p['category'],
            'image_url': p['image'],
            'vendor_id': p['vendor_id'],
            'status': p['status'],
            'rating': p.get('rating', 0.0),
            'store_name': get_vendor_name(p['vendor_id']),
            'tags': [{'name': tag} for tag in p.get('tags', [])]
        }

        # Add status classes
        if product_data['stock'] == 0:
            product_data['status_class'] = 'bg-yellow-100 text-yellow-800'
            product_data['status_label'] = 'Out of Stock'
        else:
            product_data['status_class'] = 'bg-green-100 text-green-800'
            product_data['status_label'] = 'Active'

        product_data['stock_status'] = 'Out of Stock' if product_data['stock'] == 0 else 'In Stock'
        product_data['stock_class'] = 'text-red-500 font-bold' if product_data['stock'] == 0 else 'text-green-500'
        product_data['price_formatted'] = f"${product_data['price']:.2f}"
        product_data['tag_names'] = [tag['name'] for tag in product_data['tags']]

        filtered_products.append(product_data)

    # Pagination
    page_size = 20
    total_products = len(filtered_products)
    total_pages = (total_products + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_products)
    paginated_products = filtered_products[start_idx:end_idx]

    # Get popular tags (simulated)
    popular_tags = []
    tag_counts = {}
    for p in DB['products']:
        for tag in p.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    for tag, count in list(tag_counts.items())[:20]:
        popular_tags.append({'name': tag, 'usage_count': count})

    return render_template('products.html',
                         products=paginated_products,
                         categories=DB['categories'],
                         popular_tags=popular_tags,
                         total_products=total_products,
                         page=page,
                         total_pages=total_pages,
                         request=request)

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_type = request.args.get('type', 'customer') # 'customer' or 'backend'
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = next((u for u in DB['users'] if u['username'] == username and u['password'] == password), None)
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
    uid = session['user']['id']
    cart_items = DB['carts'].get(uid, [])
    total = sum(get_product(item['product_id'])['price'] * item['quantity'] for item in cart_items if get_product(item['product_id']))
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<pid>', methods=['POST'])
def add_to_cart(pid):
    if 'user' not in session or session.get('login_type') != 'customer' or not has_role(session['user'], ROLE_CUSTOMER): return redirect(url_for('login', type='customer'))
    uid = session['user']['id']
    try:
        qty_to_add = int(request.form.get('quantity') or 1)
    except ValueError:
        qty_to_add = 1
    
    p = get_product(pid)
    if not p: return "Not found", 404
    
    v = next((v for v in DB['vendors'] if v['id'] == p['vendor_id']), None)
    if not v or v['status'] != 'Active' or p['status'] != 'Active':
        flash('This product is currently unavailable.')
        return redirect(request.referrer or url_for('index'))
    
    if uid not in DB['carts']: DB['carts'][uid] = []
    cart = DB['carts'][uid]
    
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
            
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/update/<pid>', methods=['POST'])
def update_cart(pid):
    if 'user' not in session or session.get('login_type') != 'customer' or not has_role(session['user'], ROLE_CUSTOMER): return redirect(url_for('login', type='customer'))
    uid = session['user']['id']
    action = request.form.get('action')
    
    p = get_product(pid)
    cart = DB['carts'].get(uid, [])
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
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<pid>', methods=['POST'])
def remove_from_cart(pid):
    if 'user' not in session or session.get('login_type') != 'customer': return redirect(url_for('login', type='customer'))
    uid = session['user']['id']
    if uid in DB['carts']:
        DB['carts'][uid] = [i for i in DB['carts'][uid] if i['product_id'] != pid]
    return redirect(url_for('view_cart'))

@app.route('/cart/checkout', methods=['POST'])
def checkout():
    if 'user' not in session or session.get('login_type') != 'customer':
        return redirect(url_for('login', type='customer'))
    uid  = session['user']['id']
    cart = DB['carts'].get(uid, [])
    if not cart:
        return redirect(url_for('view_cart'))

    # 校验库存（原有逻辑不变）
    for item in cart:
        p = get_product(item['product_id'])
        if not p:
            flash(f"A product in your cart is no longer available.")
            return redirect(url_for('view_cart'))
        v = next((v for v in DB['vendors'] if v['id'] == p['vendor_id']), None)
        if not v or v['status'] != 'Active' or p['status'] != 'Active':
            flash(f"Sorry, {p['title']} is currently unavailable.")
            return redirect(url_for('view_cart'))
        if item['quantity'] > p['stock']:
            flash(f"Sorry, {p['title']} only has {p['stock']} left in stock.")
            return redirect(url_for('view_cart'))

    # ★ 写入 MySQL
    try:
        order_service = OrderService()
        order_id, total_amount, sub_orders_map = order_service.create_order(
            customer_id=uid,
            cart_items=cart,
            get_product_fn=get_product
        )
    except Exception as e:
        flash(f'下单失败，请稍后重试：{str(e)}')
        return redirect(url_for('view_cart'))

    # 保留内存操作（让订单详情页能正常显示）
    order = {
        'id': order_id, 'user_id': uid, 'total_amount': total_amount,
        'status': 'Pending', 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    DB['orders'].append(order)
    for vid, items in sub_orders_map.items():
        sub_amount = sum(i['price'] * i['quantity'] for i in items)
        sub_order = {
            'id': f"SUB-{order_id}-{vid}", 'order_id': order_id, 'vendor_id': vid,
            'items': items, 'amount': sub_amount,
            'payment_status': 'Paid', 'logistics_status': 'Pending'
        }
        DB['sub_orders'].append(sub_order)

    # 扣库存、清购物车
    for item in cart:
        p = get_product(item['product_id'])
        if p:
            p['stock'] -= item['quantity']
    DB['carts'][uid] = []

    flash('Order placed successfully!')
    return redirect(url_for('order_detail', oid=order_id))

@app.route('/orders')
def order_list():
    if 'user' not in session or session.get('login_type') != 'customer' or not has_role(session['user'], ROLE_CUSTOMER): return redirect(url_for('login', type='customer'))
    uid = session['user']['id']
    my_orders = [o for o in DB['orders'] if o['user_id'] == uid]
    my_orders.sort(key=lambda x: x['created_at'], reverse=True)
    return render_template('orders.html', orders=my_orders)

@app.route('/orders/<oid>')
def order_detail(oid):
    if 'user' not in session or session.get('login_type') != 'customer': return redirect(url_for('login', type='customer'))
    order = next((o for o in DB['orders'] if o['id'] == oid), None)
    if not order: return "Order not found", 404
    subs = [s for s in DB['sub_orders'] if s['order_id'] == oid]
    return render_template('order_detail.html', order=order, sub_orders=subs)

@app.route('/orders/<oid>/cancel', methods=['POST'])
def cancel_order(oid):
    order = next((o for o in DB['orders'] if o['id'] == oid), None)
    if order and order['status'] == 'Pending':
        subs = [s for s in DB['sub_orders'] if s['order_id'] == oid]
        if any(s['logistics_status'] not in ['Pending', 'Cancelled'] for s in subs):
            flash('Cannot cancel entire order because some items have already been shipped.')
            return redirect(url_for('order_detail', oid=oid))
            
        order['status'] = 'Cancelled'
        for s in subs:
            if s['logistics_status'] != 'Cancelled':
                s['logistics_status'] = 'Cancelled'
                s['payment_status'] = 'Refunded'
                # Restore stock
                for item in s['items']:
                    p = get_product(item['product_id'])
                    if p:
                        p['stock'] += item['quantity']
        flash('Order cancelled.')
    return redirect(url_for('order_detail', oid=oid))

@app.route('/orders/<oid>/remove_item/<sub_id>/<pid>', methods=['POST'])
def remove_order_item(oid, sub_id, pid):
    order = next((o for o in DB['orders'] if o['id'] == oid), None)
    sub = next((s for s in DB['sub_orders'] if s['id'] == sub_id), None)
    
    if order and sub and order['status'] == 'Pending' and sub['logistics_status'] == 'Pending':
        # Remove item
        item_to_remove = next((i for i in sub['items'] if i['product_id'] == pid), None)
        if item_to_remove:
            # Restore stock
            p = get_product(item_to_remove['product_id'])
            if p:
                p['stock'] += item_to_remove['quantity']
                
            sub['items'].remove(item_to_remove)
            deduct_amount = item_to_remove['price'] * item_to_remove['quantity']
            sub['amount'] -= deduct_amount
            order['total_amount'] -= deduct_amount
            
            if not sub['items']:
                sub['logistics_status'] = 'Cancelled'
                sub['payment_status'] = 'Refunded'
                
            active_subs = [s for s in DB['sub_orders'] if s['order_id'] == oid and s['logistics_status'] != 'Cancelled']
            if not active_subs:
                order['status'] = 'Cancelled'
                
            flash('Item removed from order.')
            
    return redirect(url_for('order_detail', oid=oid))

# --- VENDOR ROUTES ---

@app.route('/vendor')
def vendor_dashboard():
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return redirect(url_for('login', type='backend'))

    vid = session['user']['id']
    tab = request.args.get('tab', 'overview')

    # Get vendor information
    vendor = next((v for v in DB['vendors'] if v['id'] == vid), None)
    vendor_status = vendor['status'] if vendor else 'Unknown'
    
    # Create vendor_info dict for template
    vendor_info = {
        'id': vid,
        'vendor_id': vid,
        'business_name': vendor['name'] if vendor else 'Unknown Store',
        'average_rating': vendor['rating'] if vendor else 0.0,
        'geographical_presence': vendor['location'] if vendor else 'Unknown Location',
        'status': vendor_status
    }

    # Calculate statistics
    my_products = [p for p in DB['products'] if p['vendor_id'] == vid]
    total_products = len(my_products)
    active_products = len([p for p in my_products if p['status'] == 'Active'])
    total_stock = sum(p['stock'] for p in my_products)
    out_of_stock = len([p for p in my_products if p['stock'] == 0])

    stats = {
        'total_products': total_products,
        'active_products': active_products,
        'total_stock': total_stock,
        'out_of_stock': out_of_stock
    }

    # Display different content based on tab
    if tab == 'recent_products':
        # Recent products
        recent_products = my_products[:10]  # Take the latest 10
        formatted_products = []
        for p in recent_products:
            formatted_products.append({
                'id': p['id'],
                'name': p['title'],
                'price': p['price'],
                'stock': p['stock'],
                'status': p['status'],
                'image_url': p['image'],
                'category': p['category']
            })
        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             recent_products=formatted_products,
                             tab=tab)

    elif tab == 'orders':
        # Recent orders (simulated data)
        recent_orders = []
        my_subs = [s for s in DB['sub_orders'] if s['vendor_id'] == vid]
        for sub in my_subs[:10]:  # Take the latest 10
            recent_orders.append({
                'id': sub['id'],
                'customer_name': 'Customer',
                'item_count': len(sub['items']),
                'amount': sub['amount'],
                'status': sub['logistics_status'],
                'date': '2024-01-01'  # Simulated date
            })
        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             recent_orders=recent_orders,
                             tab=tab)

    elif tab == 'analytics':
        # Analytics data (simulated)
        analytics = {
            'total_sales': 0.0,
            'total_orders': 0,
            'avg_order_value': 0.0,
            'top_products': []
        }
        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             analytics=analytics,
                             tab=tab)

    else:
        # Overview tab
        # Product status distribution
        product_status = []
        status_counts = {}
        for p in my_products:
            status_counts[p['status']] = status_counts.get(p['status'], 0) + 1

        for status, count in status_counts.items():
            percentage = (count / total_products * 100) if total_products > 0 else 0
            color = 'bg-green-500' if status == 'Active' else 'bg-yellow-500' if status == 'OutOfStock' else 'bg-gray-500'
            product_status.append({
                'status': status,
                'count': count,
                'percentage': percentage,
                'color': color
            })

        # Low stock products
        low_stock_products = []
        for p in my_products:
            if p['stock'] > 0 and p['stock'] < 10:  # Stock less than 10
                low_stock_products.append({
                    'id': p['id'],
                    'name': p['title'],
                    'stock': p['stock']
                })

        # Recent activity (simulated)
        recent_activity = [
            {
                'icon': 'package',
                'icon_bg': 'bg-blue-50',
                'icon_color': 'text-blue-600',
                'title': 'Product Added',
                'description': 'Added "Wireless Headphones" to store',
                'time': '2 hours ago'
            },
            {
                'icon': 'trending-up',
                'icon_bg': 'bg-green-50',
                'icon_color': 'text-green-600',
                'title': 'Stock Updated',
                'description': 'Updated stock for "Ergonomic Office Chair"',
                'time': '1 day ago'
            }
        ]

        return render_template('vendor_dashboard.html',
                             vendor_info=vendor_info,
                             vendor_status=vendor_status,
                             stats=stats,
                             product_status=product_status,
                             low_stock_products=low_stock_products[:5],  # Show at most 5
                             recent_activity=recent_activity,
                             tab=tab)

# --- NEW VENDOR ROUTES ---

@app.route('/vendor/dashboard', methods=['GET'])
def vendor_dashboard_alt():
    """GET /vendor/dashboard - Render vendor dashboard page"""
    # Check authentication and vendor role
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        flash('Please log in as a vendor.')
        return redirect(url_for('login', type='backend'))
    
    vid = session['user']['id']
    
    # Get vendor information from in-memory DB
    vendor = next((v for v in DB['vendors'] if v['id'] == vid), None)
    vendor_info = {
        'id': vid,
        'business_name': vendor['name'] if vendor else 'Unknown Store',
        'average_rating': vendor['rating'] if vendor else 0.0,
        'geographical_presence': vendor['location'] if vendor else 'Unknown Location',
        'status': vendor['status'] if vendor else 'Unknown'
    }
    
    # Calculate statistics
    my_products = [p for p in DB['products'] if p['vendor_id'] == vid]
    stats = {
        'total_products': len(my_products),
        'active_products': len([p for p in my_products if p['status'] == 'Active']),
        'total_stock': sum(p['stock'] for p in my_products),
        'out_of_stock': len([p for p in my_products if p['stock'] == 0])
    }
    
    return render_template('vendor_dashboard.html',
                         vendor_info=vendor_info,
                         stats=stats,
                         products=my_products,
                         tab='overview')


@app.route('/vendor/onboard', methods=['POST'])
def vendor_onboard():
    """POST /vendor/onboard - Vendor onboarding"""
    # Authentication check
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
    existing_vendor = next((v for v in DB['vendors'] if v['id'] == user_id), None)
    if existing_vendor:
        flash('You are already a vendor.')
        return redirect(url_for('vendor_dashboard'))
    
    # Add vendor to in-memory database
    try:
        DB['vendors'].append({
            'id': user_id,
            'name': business_name,
            'rating': 0.0,
            'location': geographical_presence,
            'status': 'Active'
        })
        
        # Update user role to include ROLE_VENDOR
        user = session['user']
        user['role'] |= ROLE_VENDOR
        session.modified = True
        
        flash(f'Vendor onboarded successfully: {business_name}')
        return redirect(url_for('vendor_dashboard'))
        
    except Exception as e:
        flash(f'Error onboarding vendor: {str(e)}')
        return redirect(request.referrer or url_for('index'))


@app.route('/vendor/update', methods=['POST'])
def vendor_update():
    """POST /vendor/update - Update vendor information"""
    # Authentication and vendor role check
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    vid = session['user']['id']
    
    # Get form data
    business_name = request.form.get('business_name', '').strip()
    geographical_presence = request.form.get('geographical_presence', '').strip()
    
    # Find and update vendor
    vendor = next((v for v in DB['vendors'] if v['id'] == vid), None)
    if not vendor:
        return jsonify({'success': False, 'message': 'Vendor not found'}), 404
    
    # Update fields if provided
    if business_name:
        vendor['name'] = business_name
    if geographical_presence:
        vendor['location'] = geographical_presence
    
    flash('Vendor information updated successfully.')
    
    # Check if request is AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Vendor updated successfully'})
    
    return redirect(url_for('vendor_dashboard'))


@app.route('/vendor/products/add', methods=['POST'])
def add_vendor_product():
    """POST /vendor/products/add - Create a new product"""
    # Authentication and vendor role check
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    vid = session['user']['id']
    
    # Get form data
    product_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', 'General').strip()
    image_url = request.form.get('image_url', '').strip()
    tags = request.form.get('tags', '').strip()
    
    # Parse price and stock
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
    
    # Validate required fields
    if not product_name:
        flash('Product name is required.')
        return redirect(url_for('vendor_products'))
    
    if price < 0:
        flash('Price cannot be negative.')
        return redirect(url_for('vendor_products'))
    
    if stock < 0:
        flash('Stock cannot be negative.')
        return redirect(url_for('vendor_products'))
    
    # Parse and limit tags
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    if len(tag_list) > 3:
        tag_list = tag_list[:3]
        flash('Maximum 3 tags allowed. Only first 3 tags were saved.')
    
    # Create new product
    try:
        product_id = 'p' + str(uuid.uuid4().hex[:8]).lower()
        
        new_product = {
            'id': product_id,
            'title': product_name,
            'description': description,
            'price': price,
            'stock': stock,
            'category': category,
            'image': image_url if image_url else 'https://picsum.photos/seed/product/400/300',
            'tags': tag_list,
            'vendor_id': vid,
            'status': 'Active' if stock > 0 else 'OutOfStock',
            'rating': 0.0
        }
        
        DB['products'].append(new_product)
        
        flash(f'Product "{product_name}" added successfully.')
        
        # Return JSON if AJAX request
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

    # Get vendor's products
    my_products = [p for p in DB['products'] if p['vendor_id'] == vid]

    # Filter by tab
    if tab == 'active':
        filtered_products = [p for p in my_products if p['status'] == 'Active']
    elif tab == 'inactive':
        filtered_products = [p for p in my_products if p['status'] == 'Inactive']
    elif tab == 'inventory':
        filtered_products = [p for p in my_products if p['status'] != 'Inactive']
    else:
        filtered_products = my_products

    # Pagination
    page_size = 20
    total_products = len(filtered_products)
    total_pages = (total_products + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_products)
    paginated_products = filtered_products[start_idx:end_idx]

    # Format product data
    formatted_products = []
    for p in paginated_products:
        product_data = {
            'id': p['id'],
            'name': p['title'],
            'price': p['price'],
            'stock': p['stock'],
            'status': p['status'],
            'category': p['category'],
            'image_url': p['image'],
            'tags': [{'name': tag} for tag in p.get('tags', [])]
        }
        formatted_products.append(product_data)

    # Get popular tags (simulated)
    popular_tags = []
    tag_counts = {}
    for p in DB['products']:
        for tag in p.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    for tag, count in list(tag_counts.items())[:10]:
        popular_tags.append({'name': tag, 'usage_count': count})

    # Calculate pagination info
    start_item = start_idx + 1 if total_products > 0 else 0
    end_item = min(end_idx, total_products)

    return render_template('vendor_products.html',
                         products=formatted_products,
                         categories=DB['categories'],
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

    # Get form data
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', 'General').strip()

    try:
        price = float(request.form.get('price', 0))
    except ValueError:
        price = 0.0

    try:
        stock = int(request.form.get('stock', 0))
    except ValueError:
        stock = 0

    image_url = request.form.get('image_url', '').strip()
    tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
    status = request.form.get('status', 'Active')

    # Validate data
    if not name:
        flash('Product name is required')
        return redirect(url_for('vendor_products'))

    if price < 0:
        flash('Price must be non-negative')
        return redirect(url_for('vendor_products'))

    if stock < 0:
        flash('Stock must be non-negative')
        return redirect(url_for('vendor_products'))

    # Limit number of tags
    if len(tags) > 3:
        tags = tags[:3]
        flash('Maximum 3 tags allowed. Only first 3 tags were saved.')

    if pid:
        # Update existing product
        p = get_product(pid)
        if p and p['vendor_id'] == vid:
            p.update({
                'title': name,
                'price': price,
                'stock': stock,
                'category': category,
                'image': image_url if image_url else p.get('image', ''),
                'tags': tags,
                'status': status
            })
            flash('Product updated successfully.')
        else:
            flash('Product not found or you do not have permission to edit it.')
    else:
        # Create new product
        new_p = {
            'id': 'p' + str(uuid.uuid4().hex[:8]).lower(),
            'title': name,
            'price': price,
            'stock': stock,
            'category': category,
            'image': image_url if image_url else 'https://picsum.photos/seed/product/400/300',
            'tags': tags,
            'vendor_id': vid,
            'status': status,
            'rating': 0.0
        }
        DB['products'].append(new_p)
        flash('Product added successfully.')

    return redirect(url_for('vendor_products'))

@app.route('/vendor/product/<product_id>/toggle', methods=['POST'])
def toggle_product_status(product_id):
    """Toggle product status"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return redirect(url_for('login', type='backend'))

    vid = session['user']['id']
    p = get_product(product_id)

    if p and p['vendor_id'] == vid:
        # Toggle status: Active <-> Inactive
        if p['status'] == 'Active':
            p['status'] = 'Inactive'
            flash('Product deactivated.')
        else:
            p['status'] = 'Active'
            flash('Product activated.')
    else:
        flash('Product not found or you do not have permission to update it.')

    return redirect(url_for('vendor_products'))

@app.route('/vendor/product/<product_id>/stock', methods=['POST'])
def update_product_stock(product_id):
    """Update product stock (AJAX interface)"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    vid = session['user']['id']
    p = get_product(product_id)

    if not p or p['vendor_id'] != vid:
        return jsonify({'success': False, 'message': 'Product not found or no permission'}), 404

    try:
        data = request.get_json()
        action = data.get('action')
        amount = int(data.get('amount', 0))

        if action == 'increase':
            p['stock'] += amount
        elif action == 'decrease':
            if p['stock'] - amount < 0:
                return jsonify({'success': False, 'message': 'Insufficient stock'}), 400
            p['stock'] -= amount
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400

        # Update status (if stock is 0)
        if p['stock'] == 0 and p['status'] == 'Active':
            p['status'] = 'OutOfStock'
        elif p['stock'] > 0 and p['status'] == 'OutOfStock':
            p['status'] = 'Active'

        return jsonify({'success': True, 'stock': p['stock'], 'status': p['status']})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/vendor/products/bulk-stock', methods=['POST'])
def bulk_update_stock():
    """Bulk update stock"""
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR):
        return redirect(url_for('login', type='backend'))

    vid = session['user']['id']
    product_ids = request.form.getlist('product_ids')
    action = request.form.get('action')
    amount = int(request.form.get('amount', 0))
    set_value = request.form.get('set_value')

    updated_count = 0

    for pid in product_ids:
        p = get_product(pid)
        if p and p['vendor_id'] == vid:
            if action == 'increase':
                p['stock'] += amount
            elif action == 'decrease':
                if p['stock'] - amount >= 0:
                    p['stock'] -= amount
                else:
                    continue  # Skip products with insufficient stock
            elif action == 'set' and set_value is not None:
                p['stock'] = int(set_value)

            # Update status
            if p['stock'] == 0 and p['status'] == 'Active':
                p['status'] = 'OutOfStock'
            elif p['stock'] > 0 and p['status'] == 'OutOfStock':
                p['status'] = 'Active'

            updated_count += 1

    flash(f'Updated stock for {updated_count} product(s).')
    return redirect(url_for('vendor_products', tab='inventory'))

@app.route('/vendor/transaction/<sub_id>/ship', methods=['POST'])
def ship_order(sub_id):
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR): return redirect(url_for('login', type='backend'))
    sub = next((s for s in DB['sub_orders'] if s['id'] == sub_id), None)
    if sub and sub['vendor_id'] == session['user']['id']:
        sub['logistics_status'] = 'Shipped'
        # Check if all subs for parent order are shipped
        parent = next((o for o in DB['orders'] if o['id'] == sub['order_id']), None)
        if parent:
            all_subs = [s for s in DB['sub_orders'] if s['order_id'] == parent['id']]
            if all(s['logistics_status'] in ['Shipped', 'Delivered', 'Cancelled'] for s in all_subs):
                parent['status'] = 'Shipped'
    return redirect(url_for('vendor_dashboard', tab='transactions'))

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_ADMIN): return redirect(url_for('login', type='backend'))
    available_users = [u for u in DB['users'] if not has_role(u, ROLE_VENDOR) and not has_role(u, ROLE_ADMIN)]
    return render_template('admin.html', vendors=DB['vendors'], available_users=available_users)

@app.route('/admin/vendor/save', methods=['POST'])
def save_vendor():
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_ADMIN): return redirect(url_for('login', type='backend'))
    vid = request.form.get('id')
    name = request.form.get('name')
    location = request.form.get('location')
    user_id = request.form.get('user_id')
    
    if vid:
        v = next((v for v in DB['vendors'] if v['id'] == vid), None)
        if v:
            v.update({'name': name, 'location': location})
            flash('Vendor updated.')
    else:
        if not user_id:
            flash('Please select a user to bind to the new vendor.')
            return redirect(url_for('admin_dashboard'))
            
        user = next((u for u in DB['users'] if u['id'] == user_id), None)
        if not user:
            flash('User not found.')
            return redirect(url_for('admin_dashboard'))
            
        if has_role(user, ROLE_ADMIN):
            flash('Cannot bind a vendor to an Admin account.')
            return redirect(url_for('admin_dashboard'))
            
        if has_role(user, ROLE_VENDOR):
            flash('User is already a vendor.')
            return redirect(url_for('admin_dashboard'))
            
        DB['vendors'].append({
            'id': user_id, 'name': name, 'location': location, 'rating': 0.0, 'status': 'Active'
        })
        
        user['role'] |= ROLE_VENDOR
            
        flash('Vendor added and bound to user.')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/vendor/<vid>/toggle', methods=['POST'])
def toggle_vendor(vid):
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_ADMIN): return redirect(url_for('login', type='backend'))
    v = next((v for v in DB['vendors'] if v['id'] == vid), None)
    if v:
        v['status'] = 'Inactive' if v['status'] == 'Active' else 'Active'
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
