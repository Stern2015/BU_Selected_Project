import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

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
    q = request.args.get('q', '').lower()
    cat = request.args.get('category', '')
    vid = request.args.get('vendor_id', '')
    
    # Get active vendors
    active_vendor_ids = {v['id'] for v in DB['vendors'] if v['status'] == 'Active'}
    
    filtered = []
    for p in DB['products']:
        if p['status'] != 'Active': continue
        if p['vendor_id'] not in active_vendor_ids: continue
        if q and q not in p['title'].lower() and not any(q in t.lower() for t in p['tags']): continue
        if cat and p['category'] != cat: continue
        if vid and p['vendor_id'] != vid: continue
        filtered.append(p)
        
    return render_template('index.html', products=filtered, categories=DB['categories'], vendors=DB['vendors'], request=request)

@app.route('/product/<pid>')
def product_detail(pid):
    p = get_product(pid)
    if not p: return "Product not found", 404
    
    v = next((v for v in DB['vendors'] if v['id'] == p['vendor_id']), None)
    if not v or v['status'] != 'Active':
        flash('This product is currently unavailable.')
        return redirect(url_for('index'))
        
    return render_template('product.html', product=p)

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
    if 'user' not in session or session.get('login_type') != 'customer': return redirect(url_for('login', type='customer'))
    uid = session['user']['id']
    cart = DB['carts'].get(uid, [])
    if not cart: return redirect(url_for('view_cart'))
    
    # Pre-check stock and availability
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
    
    order_id = 'ORD-' + str(uuid.uuid4())[:8].upper()
    total_amount = 0
    sub_orders_map = {} # vendor_id -> items
    
    for item in cart:
        p = get_product(item['product_id'])
        if p:
            p['stock'] -= item['quantity'] # Deduct stock
            total_amount += p['price'] * item['quantity']
            vid = p['vendor_id']
            if vid not in sub_orders_map: sub_orders_map[vid] = []
            sub_orders_map[vid].append({'product_id': p['id'], 'quantity': item['quantity'], 'price': p['price']})
            
    order = {
        'id': order_id, 'user_id': uid, 'total_amount': total_amount,
        'status': 'Pending', 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    DB['orders'].append(order)
    
    for vid, items in sub_orders_map.items():
        sub_amount = sum(i['price'] * i['quantity'] for i in items)
        sub_order = {
            'id': f"SUB-{order_id}-{vid}", 'order_id': order_id, 'vendor_id': vid,
            'items': items, 'amount': sub_amount, 'payment_status': 'Paid', 'logistics_status': 'Pending'
        }
        DB['sub_orders'].append(sub_order)
        
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
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR): return redirect(url_for('login', type='backend'))
    vid = session['user']['id']
    tab = request.args.get('tab', 'products')
    my_products = [p for p in DB['products'] if p['vendor_id'] == vid]
    my_subs = [s for s in DB['sub_orders'] if s['vendor_id'] == vid and s['items']]
    return render_template('vendor.html', products=my_products, sub_orders=my_subs, tab=tab)

@app.route('/vendor/product/save', methods=['POST'])
def save_product():
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR): return redirect(url_for('login', type='backend'))
    vid = session['user']['id']
    pid = request.form.get('id')
    
    title = request.form.get('title')
    try:
        price = float(request.form.get('price') or 0)
    except ValueError:
        price = 0.0
    try:
        stock = int(request.form.get('stock') or 0)
    except ValueError:
        stock = 0
    image = request.form.get('image')
    tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
    
    if pid:
        p = get_product(pid)
        if p and p['vendor_id'] == vid:
            p.update({'title': title, 'price': price, 'stock': stock, 'image': image, 'tags': tags})
            flash('Product updated.')
    else:
        new_p = {
            'id': 'p' + str(uuid.uuid4())[:6],
            'title': title, 'price': price, 'stock': stock, 'image': image, 'tags': tags,
            'vendor_id': vid, 'category': 'General', 'status': 'Active', 'rating': 0.0
        }
        DB['products'].append(new_p)
        flash('Product added.')
        
    return redirect(url_for('vendor_dashboard', tab='products'))

@app.route('/vendor/product/<pid>/toggle', methods=['POST'])
def toggle_product(pid):
    if 'user' not in session or session.get('login_type') != 'backend' or not has_role(session['user'], ROLE_VENDOR): return redirect(url_for('login', type='backend'))
    p = get_product(pid)
    if p and p['vendor_id'] == session['user']['id']:
        p['status'] = 'Inactive' if p['status'] == 'Active' else 'Active'
    return redirect(url_for('vendor_dashboard', tab='products'))

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
