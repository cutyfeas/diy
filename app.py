from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file, session
import uuid
import json
from pathlib import Path
import datetime
import os
import io
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / 'DB'
UPLOAD_DIR = BASE_DIR / 'static' / 'uploads'
ALLOWED_EXT = {'png', 'jpg', 'jpeg'}
WHATSAPP_BILL_DIR = UPLOAD_DIR / 'whatsapp_bills'
WHATSAPP_INVOICE_DIR = UPLOAD_DIR / 'invoice_whatsapp'

for d in (DB_DIR, UPLOAD_DIR, WHATSAPP_BILL_DIR, WHATSAPP_INVOICE_DIR):
    d.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.datetime.utcnow().isoformat()


def read_json(path: Path):
    if not path.exists():
        path.write_text('[]', encoding='utf-8')
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8') or '[]')
    except Exception:
        # corrupt or empty -> reset
        path.write_text('[]', encoding='utf-8')
        return []


def write_json_atomic(path: Path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(str(tmp), str(path))


CUSTOMERS_FILE = DB_DIR / 'customers.json'
PRODUCTS_FILE = DB_DIR / 'products.json'
BILLS_FILE = DB_DIR / 'bills.json'
ORDERS_FILE = DB_DIR / 'orderreceived.json'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def generate_whatsapp_bill_image(order):
    """Create a PNG bill image using the order data so WhatsApp can share it."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    customer_name = (order or {}).get('customer_name', 'Customer')
    total = float((order or {}).get('total', 0) or 0)
    invoice_no = (order or {}).get('invoice_no') or (order or {}).get('id', '')[:8].upper()
    items = (order or {}).get('items', []) or []

    width, height = 900, 1200
    bg = (255, 255, 255)
    accent = (37, 99, 235)
    dark = (24, 24, 27)
    soft = (90, 90, 90)
    border = (230, 230, 230)
    img = Image.new('RGB', (width, height), bg)
    draw = ImageDraw.Draw(img)

    margin = 40
    y = margin
    draw.rounded_rectangle([(margin, margin), (width - margin, height - margin)], radius=26, fill=(255, 255, 255), outline=border, width=3)

    try:
        title_font = ImageFont.truetype('arial.ttf', 30)
        body_font = ImageFont.truetype('arial.ttf', 22)
        small_font = ImageFont.truetype('arial.ttf', 18)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw.rectangle([(margin + 18, margin + 16), (width - margin - 18, margin + 90)], fill=accent)
    draw.text((margin + 32, margin + 28), 'DIY HUE Studio', fill=(255, 255, 255), font=title_font)

    y = margin + 120
    draw.text((margin + 24, y), f'Bill for: {customer_name}', fill=dark, font=body_font)
    y += 42
    draw.text((margin + 24, y), f'Invoice No: {invoice_no}', fill=soft, font=small_font)
    y += 44
    draw.text((margin + 24, y), 'Item', fill=soft, font=small_font)
    draw.text((width - 200, y), 'Amount', fill=soft, font=small_font)

    y += 28
    line_y = y
    draw.line([(margin + 24, line_y), (width - margin - 24, line_y)], fill=border, width=2)
    y += 18

    for it in items:
        item_name = str(it.get('product_name') or it.get('product_id') or 'Item')
        qty = it.get('qty', 1)
        amount = float(it.get('amount', 0) or 0)
        draw.text((margin + 24, y), f'{item_name} x {qty}', fill=dark, font=small_font)
        draw.text((width - 200, y), f'₹{amount:.2f}', fill=dark, font=small_font)
        y += 30

    y += 20
    draw.line([(margin + 24, y), (width - margin - 24, y)], fill=border, width=2)
    y += 24
    draw.text((margin + 24, y), 'Total', fill=dark, font=body_font)
    draw.text((width - 200, y), f'₹{total:.2f}', fill=accent, font=body_font)
    y += 54
    draw.text((margin + 24, y), 'Thank you for choosing DIY HUE Studio!', fill=soft, font=small_font)

    image_name = f"whatsapp_bill_{uuid.uuid4().hex}.png"
    image_path = WHATSAPP_BILL_DIR / image_name
    img.save(image_path, format='PNG')
    return f'/static/uploads/whatsapp_bills/{image_name}'


def generate_invoice_whatsapp_image(bill):
    """Create a PNG invoice image named with the invoice number and save it locally."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    customer_name = bill.get('customer_name', 'Customer')
    invoice_no = bill.get('invoice_no', '000')
    items = bill.get('items', []) or []
    total = float(bill.get('total', 0) or 0)

    width, height = 900, 1200
    bg = (255, 255, 255)
    accent = (98, 58, 150)
    dark = (20, 20, 20)
    soft = (88, 88, 88)
    border = (230, 230, 230)
    img = Image.new('RGB', (width, height), bg)
    draw = ImageDraw.Draw(img)
    margin = 50

    draw.rounded_rectangle([(margin, margin), (width - margin, height - margin)], radius=24, outline=border, width=3, fill=(255, 255, 255))
    draw.rectangle([(margin + 15, margin + 15), (width - margin - 15, margin + 90)], fill=accent)
    draw.text((margin + 30, margin + 30), 'DIY HUE Studio', fill=(255, 255, 255), font=ImageFont.truetype('arial.ttf', 28))
    draw.text((margin + 30, margin + 110), f'Invoice: {invoice_no}', fill=dark, font=ImageFont.truetype('arial.ttf', 22))
    draw.text((margin + 30, margin + 150), f'Customer: {customer_name}', fill=soft, font=ImageFont.truetype('arial.ttf', 20))
    draw.text((margin + 30, margin + 185), f'Date: {bill.get("date", "")}', fill=soft, font=ImageFont.truetype('arial.ttf', 18))

    y = margin + 240
    draw.text((margin + 30, y), 'Item', fill=soft, font=ImageFont.truetype('arial.ttf', 18))
    draw.text((width - 180, y), 'Amount', fill=soft, font=ImageFont.truetype('arial.ttf', 18))
    y += 24
    draw.line([(margin + 30, y), (width - margin - 30, y)], fill=border, width=2)
    y += 20

    for it in items:
        item_name = str(it.get('product_name') or it.get('product_id') or 'Item')
        amount = float(it.get('amount', 0) or 0)
        qty = it.get('qty', 1)
        draw.text((margin + 30, y), f'{item_name} x {qty}', fill=dark, font=ImageFont.truetype('arial.ttf', 18))
        draw.text((width - 180, y), f'₹{amount:.2f}', fill=dark, font=ImageFont.truetype('arial.ttf', 18))
        y += 28

    y += 16
    draw.line([(margin + 30, y), (width - margin - 30, y)], fill=border, width=2)
    y += 30
    draw.text((margin + 30, y), 'Total', fill=dark, font=ImageFont.truetype('arial.ttf', 22))
    draw.text((width - 180, y), f'₹{total:.2f}', fill=accent, font=ImageFont.truetype('arial.ttf', 22))
    y += 80
    draw.text((margin + 30, y), 'Thanks for buying from DIY HUE Studio.', fill=soft, font=ImageFont.truetype('arial.ttf', 18))

    image_name = f"invoice_{invoice_no}.png"
    image_path = WHATSAPP_INVOICE_DIR / image_name
    img.save(image_path, format='PNG')
    return f'/static/uploads/invoice_whatsapp/{image_name}'


def make_thumbnail(src_path: Path, dest_path: Path, size=(400, 400)):
    try:
        img = Image.open(src_path)
        img.thumbnail(size)
        img.save(dest_path)
    except Exception:
        # If PIL fails, just copy
        from shutil import copyfile
        copyfile(src_path, dest_path)


app = Flask(__name__)
app.secret_key = 'dev-key-diy-hue'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'


@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session['admin_username'] = username
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('is_admin', None)
    session.pop('admin_username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    customers = read_json(CUSTOMERS_FILE)
    products = read_json(PRODUCTS_FILE)
    bills = read_json(BILLS_FILE)
    # simple stats
    total_customers = len(customers)
    total_active_products = len([p for p in products if not p.get('is_deleted')])
    total_bills = len(bills)
    revenue = sum(b.get('total', 0) for b in bills)
    return render_template('dashboard.html', stats={
        'customers': total_customers,
        'products': total_active_products,
        'bills': total_bills,
        'revenue': revenue,
    }, products=products)


### Customers


@app.route('/customers')
def customers():
    q = request.args.get('q', '').strip().lower()
    customers = read_json(CUSTOMERS_FILE)
    if q:
        customers = [c for c in customers if q in c.get('name', '').lower() or q in c.get('mobile_number', '')]
    return render_template('customers.html', customers=customers)


@app.route('/customers/add', methods=['POST'])
def add_customer():
    name = request.form.get('name', '').strip()
    mobile = request.form.get('mobile_number', '').strip()
    address = request.form.get('address', '').strip()
    if not name:
        flash('Name is required', 'error')
        return redirect(url_for('customers'))
    if not (mobile.isdigit() and len(mobile) == 10):
        flash('Mobile number must be 10 digits', 'error')
        return redirect(url_for('customers'))
    customers = read_json(CUSTOMERS_FILE)
    new = {
        'id': str(uuid.uuid4()),
        'name': name,
        'mobile_number': mobile,
        'address': address,
        'created_at': now_iso(),
        'updated_at': now_iso(),
    }
    customers.append(new)
    write_json_atomic(CUSTOMERS_FILE, customers)
    flash('Customer added', 'success')
    return redirect(url_for('customers'))


@app.route('/customers/edit/<id>', methods=['GET', 'POST'])
def edit_customer(id):
    customers = read_json(CUSTOMERS_FILE)
    cust = next((c for c in customers if c['id'] == id), None)
    if not cust:
        flash('Customer not found', 'error')
        return redirect(url_for('customers'))
    if request.method == 'GET':
        return render_template('customers_edit.html', customer=cust)
    # POST -> update
    name = request.form.get('name', '').strip()
    mobile = request.form.get('mobile_number', '').strip()
    address = request.form.get('address', '').strip()
    if not name:
        flash('Name required', 'error')
        return redirect(url_for('customers'))
    if not (mobile.isdigit() and len(mobile) == 10):
        flash('Mobile number must be 10 digits', 'error')
        return redirect(url_for('customers'))
    cust['name'] = name
    cust['mobile_number'] = mobile
    cust['address'] = address
    cust['updated_at'] = now_iso()
    write_json_atomic(CUSTOMERS_FILE, customers)
    flash('Customer updated', 'success')
    return redirect(url_for('customers'))


@app.route('/customers/delete/<id>', methods=['POST'])
def delete_customer(id):
    # block if referenced
    bills = read_json(BILLS_FILE)
    for b in bills:
        if b.get('customer_id') == id:
            flash('Cannot delete customer referenced by existing bills', 'error')
            return redirect(url_for('customers'))
    customers = read_json(CUSTOMERS_FILE)
    customers = [c for c in customers if c['id'] != id]
    write_json_atomic(CUSTOMERS_FILE, customers)
    flash('Customer deleted', 'success')
    return redirect(url_for('customers'))


### Products


@app.route('/products')
def products():
    products = read_json(PRODUCTS_FILE)
    return render_template('products.html', products=products)


@app.route('/products/add', methods=['POST'])
def add_product():
    name = request.form.get('name', '').strip()
    price = request.form.get('price', '0').strip()
    try:
        price = float(price)
    except Exception:
        price = 0.0
    image = request.files.get('image')
    image_path = ''
    if image and allowed_file(image.filename):
        filename = secure_filename(f"{uuid.uuid4().hex}_{image.filename}")
        dest = UPLOAD_DIR / filename
        image.save(dest)
        thumb = UPLOAD_DIR / f"thumb_{filename}"
        make_thumbnail(dest, thumb, size=(600, 600))
        image_path = f"/static/uploads/{thumb.name}"
    products = read_json(PRODUCTS_FILE)
    new = {
        'id': str(uuid.uuid4()),
        'name': name,
        'price': price,
        'image': image_path,
        'is_deleted': False,
        'created_at': now_iso(),
        'updated_at': now_iso(),
    }
    products.append(new)
    write_json_atomic(PRODUCTS_FILE, products)
    flash('Product added', 'success')
    return redirect(url_for('products'))


@app.route('/products/edit/<id>', methods=['GET', 'POST'])
def edit_product(id):
    products = read_json(PRODUCTS_FILE)
    p = next((x for x in products if x['id'] == id), None)
    if not p:
        flash('Product not found', 'error')
        return redirect(url_for('products'))
    if request.method == 'GET':
        return render_template('products_edit.html', product=p)
    name = request.form.get('name', '').strip()
    price = request.form.get('price', '0').strip()
    try:
        price = float(price)
    except Exception:
        price = p.get('price', 0)
    image = request.files.get('image')
    if image and allowed_file(image.filename):
        filename = secure_filename(f"{uuid.uuid4().hex}_{image.filename}")
        dest = UPLOAD_DIR / filename
        image.save(dest)
        thumb = UPLOAD_DIR / f"thumb_{filename}"
        make_thumbnail(dest, thumb, size=(600, 600))
        p['image'] = f"/static/uploads/{thumb.name}"
    p['name'] = name
    p['price'] = price
    p['updated_at'] = now_iso()
    write_json_atomic(PRODUCTS_FILE, products)
    flash('Product updated', 'success')
    return redirect(url_for('products'))


@app.route('/products/toggle_delete/<id>', methods=['POST'])
def toggle_delete_product(id):
    products = read_json(PRODUCTS_FILE)
    for p in products:
        if p['id'] == id:
            p['is_deleted'] = not p.get('is_deleted', False)
            p['updated_at'] = now_iso()
            write_json_atomic(PRODUCTS_FILE, products)
            flash('Product status changed', 'success')
            return redirect(url_for('products'))
    flash('Product not found', 'error')
    return redirect(url_for('products'))


@app.route('/api/products_active')
def api_products_active():
    products = read_json(PRODUCTS_FILE)
    active = [p for p in products if not p.get('is_deleted')]
    return jsonify(active)


### Billing


def next_invoice_no():
    bills = read_json(BILLS_FILE)
    if not bills:
        return '001'
    try:
        nums = [int(b.get('invoice_no', '0')) for b in bills if b.get('invoice_no')]
        n = max(nums) + 1 if nums else 1
    except Exception:
        n = len(bills) + 1
    return str(n).zfill(3)


@app.route('/billing')
def bills_list():
    bills = read_json(BILLS_FILE)
    customers = read_json(CUSTOMERS_FILE)
    cust_map = {c['id']: c for c in customers}
    for b in bills:
        customer = cust_map.get(b.get('customer_id'))
        b['customer_name'] = customer.get('name', b.get('customer_name', b.get('customer_id'))) if customer else b.get('customer_name', b.get('customer_id'))
        b['customer_mobile'] = customer.get('mobile_number', '') if customer else ''
    return render_template('billing.html', bills=bills)





### Cart and orders (session-based customer cart)


def _cart_items():
    return session.get('cart', [])


@app.route('/cart/add', methods=['POST'])
def cart_add():
    data = request.get_json() or request.form
    pid = data.get('product_id')
    qty = int(data.get('quantity', 1))
    if not pid:
        return jsonify({'ok': False, 'error': 'no product_id'}), 400
    cart = session.get('cart', [])
    # increment qty if exists
    found = next((it for it in cart if it['product_id'] == pid), None)
    if found:
        found['quantity'] = found.get('quantity', 1) + qty
    else:
        cart.append({'product_id': pid, 'quantity': qty})
    session['cart'] = cart
    session.modified = True
    return jsonify({'ok': True, 'count': sum(i['quantity'] for i in cart)})


@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    data = request.get_json() or request.form
    pid = data.get('product_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'no product_id'}), 400
    cart = session.get('cart', [])
    cart = [it for it in cart if it['product_id'] != pid]
    session['cart'] = cart
    session.modified = True
    return jsonify({'ok': True, 'count': sum(i['quantity'] for i in cart)})


@app.route('/cart')
def cart_view():
    cart = session.get('cart', [])
    products = read_json(PRODUCTS_FILE)
    enriched = []
    total = 0
    for it in cart:
        prod = next((p for p in products if p['id'] == it['product_id']), None)
        if not prod:
            continue
        qty = int(it.get('quantity', 1))
        subtotal = qty * float(prod.get('price', 0))
        total += subtotal
        enriched.append({'product': prod, 'quantity': qty, 'subtotal': subtotal})
    return render_template('cart.html', items=enriched, total=total)


@app.route('/api/cart_count')
def api_cart_count():
    cart = session.get('cart', [])
    count = sum(int(i.get('quantity', 0)) for i in cart)
    return jsonify({'count': count})


@app.route('/orders')
def orders_list():
    orders = read_json(ORDERS_FILE)
    bills = read_json(BILLS_FILE)
    bill_map = {b['id']: b for b in bills}
    products = read_json(PRODUCTS_FILE)
    prod_map = {p['id']: p for p in products}
    # format dates and ensure fields
    for o in orders:
        ca = o.get('created_at')
        try:
            dt = datetime.datetime.fromisoformat(ca)
            o['created_at_fmt'] = dt.strftime('%d-%m-%Y')
        except Exception:
            o['created_at_fmt'] = ca or ''
        # ensure customer fields exist
        o['customer_name'] = o.get('customer_name', '')
        o['customer_mobile'] = o.get('customer_mobile', '')
        # attach bill if exists
        if o.get('bill_id'):
            o['_bill'] = bill_map.get(o.get('bill_id'))
            # enrich bill items with product names if available
            if o['_bill'] and o['_bill'].get('items'):
                for it in o['_bill']['items']:
                    pid = it.get('product_id')
                    it['product_name'] = prod_map.get(pid, {}).get('name', pid)
    return render_template('orders.html', orders=orders, bills=bills, products=products)


@app.route('/orders/add', methods=['GET', 'POST'])
def orders_add():
    if request.method == 'GET':
        customers = read_json(CUSTOMERS_FILE)
        products = [p for p in read_json(PRODUCTS_FILE) if not p.get('is_deleted')]
        return render_template('orders_add.html', customers=customers, products=products)
    # POST -> create order
    data = request.form
    cust_id = data.get('customer_id')
    customers = read_json(CUSTOMERS_FILE)
    cust = next((c for c in customers if c['id'] == cust_id), None)
    name = cust.get('name') if cust else data.get('customer_name','')
    mobile = cust.get('mobile_number') if cust else data.get('customer_mobile','')
    items = []
    products = read_json(PRODUCTS_FILE)
    idx = 0
    total = 0
    while True:
        pid = data.get(f'item_product_{idx}')
        if not pid:
            break
        qty = int(data.get(f'item_qty_{idx}', '1'))
        prod = next((p for p in products if p['id'] == pid), None)
        price = float(prod.get('price',0)) if prod else 0
        amt = qty * price
        items.append({'product_id': pid, 'product_name': prod.get('name') if prod else '', 'qty': qty, 'unit_price': price, 'amount': amt})
        total += amt
        idx += 1
    # enforce: customer selected and at least one product
    if not cust_id or len(items) == 0:
        flash('Please select a customer and add at least one product.', 'danger')
        return redirect(url_for('orders_add'))

    order = {
        'id': str(uuid.uuid4()),
        'customer_name': name,
        'customer_mobile': mobile,
        'customer_address': cust.get('address','') if cust else '',
        'items': items,
        'total': total,
        'created_at': now_iso(),
    }
    if cust:
        order['customer_id'] = cust['id']
    else:
        # no customer selected
        pass
    order['orderid'] = order['id']
    order['customerid'] = order.get('customer_id')
    orders = read_json(ORDERS_FILE)
    orders.append(order)
    write_json_atomic(ORDERS_FILE, orders)
    flash('Order created', 'success')
    return redirect(url_for('orders_list'))


@app.route('/orders/edit/<id>', methods=['GET', 'POST'])
def orders_edit(id):
    orders = read_json(ORDERS_FILE)
    order = next((o for o in orders if o['id'] == id), None)
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('orders_list'))
    if order.get('bill_id'):
        flash('This order already has a bill and cannot be edited.', 'error')
        return redirect(url_for('orders_list'))

    customers = read_json(CUSTOMERS_FILE)
    products = read_json(PRODUCTS_FILE)

    if request.method == 'GET':
        return render_template('orders_edit.html', order=order, customers=customers, products=products)

    data = request.form
    cust_id = data.get('customer_id')
    cust = next((c for c in customers if c['id'] == cust_id), None)
    if not cust_id or not cust:
        flash('Please select a valid customer.', 'error')
        return redirect(url_for('orders_edit', id=id))

    items = []
    idx = 0
    total = 0
    while True:
        pid = data.get(f'item_product_{idx}')
        if not pid:
            break
        qty = int(data.get(f'item_qty_{idx}', '1'))
        if qty <= 0:
            qty = 1
        prod = next((p for p in products if p['id'] == pid), None)
        if not prod:
            idx += 1
            continue
        price = float(prod.get('price', 0))
        amount = qty * price
        items.append({
            'product_id': prod['id'],
            'product_name': prod.get('name', ''),
            'qty': qty,
            'unit_price': price,
            'amount': amount,
        })
        total += amount
        idx += 1

    if not items:
        flash('Please add at least one product to the order.', 'error')
        return redirect(url_for('orders_edit', id=id))

    order['customer_id'] = cust['id']
    order['customer_name'] = cust.get('name', '')
    order['customer_mobile'] = cust.get('mobile_number', '')
    order['customer_address'] = cust.get('address', '')
    order['items'] = items
    order['total'] = total
    order['updated_at'] = now_iso()
    order['orderid'] = order['id']
    order['customerid'] = order['customer_id']

    write_json_atomic(ORDERS_FILE, orders)
    flash('Order updated', 'success')
    return redirect(url_for('orders_list'))


@app.route('/orders/delete/<id>', methods=['POST'])
def orders_delete(id):
    orders = read_json(ORDERS_FILE)
    orders = [o for o in orders if o['id'] != id]
    write_json_atomic(ORDERS_FILE, orders)
    flash('Order deleted', 'success')
    return redirect(url_for('orders_list'))


@app.route('/orders/create_bill/<id>', methods=['POST'])
def orders_create_bill(id):
    orders = read_json(ORDERS_FILE)
    order = next((o for o in orders if o['id'] == id), None)
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('orders_list'))
    # server-side: prevent creating more than one bill per order
    if order.get('bill_id'):
        flash('This order already has a bill and cannot be billed again.', 'error')
        return redirect(url_for('orders_list'))
    # create a bill from order items
    bills = read_json(BILLS_FILE)
    items = []
    for it in order.get('items', []):
        items.append({'product_id': it.get('product_id'), 'qty': it.get('qty'), 'unit_price': it.get('unit_price'), 'amount': it.get('amount')})
    # try to link to existing customer by id or by mobile+address
    customer_id = order.get('customer_id')
    if not customer_id:
        customers = read_json(CUSTOMERS_FILE)
        # match by mobile only
        match = next((c for c in customers if c.get('mobile_number') == order.get('customer_mobile')), None)
        if match:
            customer_id = match['id']

    bill = {
        'id': str(uuid.uuid4()),
        'invoice_no': next_invoice_no(),
        'date': datetime.date.today().isoformat(),
        'customer_id': customer_id,
        'order_id': order.get('id'),
        'customer_name': order.get('customer_name'),
        'items': items,
        'total': order.get('total'),
        'notes': '',
        'created_at': now_iso(),
    }
    bills.append(bill)
    write_json_atomic(BILLS_FILE, bills)
    # mark order as billed
    for o in orders:
        if o['id'] == id:
            o['bill_id'] = bill['id']
            o['bill_created_at'] = now_iso()
            break
    write_json_atomic(ORDERS_FILE, orders)
    flash('Bill created from order', 'success')
    return redirect(url_for('orders_list'))


@app.route('/orders/whatsapp-image/<id>')
def whatsapp_bill_image(id):
    orders = read_json(ORDERS_FILE)
    order = next((o for o in orders if o['id'] == id), None)
    if not order:
        return '', 404

    order_copy = dict(order)
    order_copy['invoice_no'] = order.get('bill_id') or order.get('id', '')[:8].upper()
    image_path = generate_whatsapp_bill_image(order_copy)
    if not image_path:
        return '', 500

    abs_path = BASE_DIR / image_path.lstrip('/')
    if abs_path.exists():
        return send_file(abs_path, mimetype='image/png')

    return '', 404


@app.route('/billing/whatsapp-invoice/<id>')
def billing_whatsapp_invoice(id):
    bills = read_json(BILLS_FILE)
    bill = next((b for b in bills if b['id'] == id), None)
    if not bill:
        return '', 404

    customer = next((c for c in read_json(CUSTOMERS_FILE) if c['id'] == bill.get('customer_id')), {})
    bill_copy = dict(bill)
    bill_copy['customer_name'] = customer.get('name', bill.get('customer_name', 'Customer'))
    image_path = generate_invoice_whatsapp_image(bill_copy)
    if not image_path:
        return '', 500

    abs_path = BASE_DIR / image_path.lstrip('/')
    if abs_path.exists():
        return send_file(abs_path, mimetype='image/png')

    return '', 404


@app.route('/cart/place', methods=['POST'])
def cart_place():
    name = request.form.get('name', '').strip()
    mobile = request.form.get('mobile', '').strip()
    address = request.form.get('address', '').strip()
    if not name or not mobile:
        flash('Name and mobile are required', 'error')
        return redirect(url_for('cart_view'))
    cart = session.get('cart', [])
    products = read_json(PRODUCTS_FILE)
    if not cart:
        flash('Cart is empty', 'error')
        return redirect(url_for('cart_view'))
    items = []
    total = 0
    for it in cart:
        prod = next((p for p in products if p['id'] == it['product_id']), None)
        if not prod:
            continue
        qty = int(it.get('quantity', 1))
        subtotal = qty * float(prod.get('price', 0))
        items.append({'product_id': prod['id'], 'product_name': prod['name'], 'qty': qty, 'unit_price': float(prod.get('price', 0)), 'amount': subtotal})
        total += subtotal
    order = {
        'id': str(uuid.uuid4()),
        'customer_name': name,
        'customer_mobile': mobile,
        'customer_address': address,
        'items': items,
        'total': total,
        'created_at': now_iso(),
    }
    # ensure customer exists; if not add and link to order
    customers = read_json(CUSTOMERS_FILE)
    # match by mobile only (ignore address)
    match = next((c for c in customers if c.get('mobile_number') == mobile), None)
    if match:
        order['customer_id'] = match['id']
    else:
        newc = {
            'id': str(uuid.uuid4()),
            'name': name,
            'mobile_number': mobile,
            'address': address,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        }
        customers.append(newc)
        write_json_atomic(CUSTOMERS_FILE, customers)
        order['customer_id'] = newc['id']

    # expose legacy-friendly fields required by downstream code / DB expectations
    order['orderid'] = order['id']
    order['customerid'] = order['customer_id']

    orders = read_json(ORDERS_FILE)
    orders.append(order)
    write_json_atomic(ORDERS_FILE, orders)
    session['cart'] = []
    session.modified = True
    flash('Order placed — thank you!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/billing/edit/<id>', methods=['GET', 'POST'])
def billing_edit(id):
    bills = read_json(BILLS_FILE)
    bill = next((b for b in bills if b['id'] == id), None)
    if not bill:
        flash('Bill not found', 'error')
        return redirect(url_for('bills_list'))
    if request.method == 'GET':
        customers = read_json(CUSTOMERS_FILE)
        products = [p for p in read_json(PRODUCTS_FILE) if not p.get('is_deleted')]
        # enrich items with product names for form display
        return render_template('billing_edit.html', bill=bill, customers=customers, products=products)
    # POST -> update existing bill
    data = request.form
    customer_id = data.get('customer_id')
    notes = data.get('notes', '')
    items = []
    products = read_json(PRODUCTS_FILE)
    idx = 0
    while True:
        pid = data.get(f'item_product_{idx}')
        if not pid:
            break
        qty = float(data.get(f'item_qty_{idx}', '1'))
        prod = next((p for p in products if p['id'] == pid), None)
        price = float(prod.get('price', 0)) if prod else 0
        amt = qty * price
        items.append({'product_id': pid, 'qty': qty, 'unit_price': price, 'amount': amt})
        idx += 1
    total = sum(i['amount'] for i in items)
    bill['customer_id'] = customer_id
    bill['items'] = items
    bill['total'] = total
    bill['notes'] = notes
    bill['updated_at'] = now_iso()
    write_json_atomic(BILLS_FILE, bills)
    flash('Bill updated', 'success')
    return redirect(url_for('bills_list'))


@app.route('/invoice/<id>')
def invoice_view(id):
    bills = read_json(BILLS_FILE)
    bill = next((b for b in bills if b['id'] == id), None)
    if not bill:
        flash('Invoice not found', 'error')
        return redirect(url_for('bills_list'))
    customers = read_json(CUSTOMERS_FILE)
    products = read_json(PRODUCTS_FILE)
    customer = next((c for c in customers if c['id'] == bill.get('customer_id')), {})
    # enrich items with product names
    enriched = []
    for it in bill.get('items', []):
        prod = next((p for p in products if p['id'] == it.get('product_id')), None)
        enriched.append({**it, 'product_name': prod['name'] if prod else it.get('description')})
    return render_template('invoice.html', bill=bill, customer=customer, items=enriched, new=False)


@app.route('/billing/delete/<id>', methods=['POST'])
def billing_delete(id):
    bills = read_json(BILLS_FILE)
    bills = [b for b in bills if b['id'] != id]
    write_json_atomic(BILLS_FILE, bills)
    # remove bill linkage from orders that referenced this bill
    try:
        orders = read_json(ORDERS_FILE)
        changed = False
        for o in orders:
            if o.get('bill_id') == id:
                o.pop('bill_id', None)
                o.pop('bill_created_at', None)
                changed = True
        if changed:
            write_json_atomic(ORDERS_FILE, orders)
    except Exception:
        # if orders file missing or corrupt, ignore to avoid blocking deletion
        pass
    flash('Bill deleted', 'success')
    return redirect(url_for('bills_list'))


if __name__ == '__main__':
    app.run(debug=True)
