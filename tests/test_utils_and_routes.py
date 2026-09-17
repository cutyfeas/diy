import json
from pathlib import Path
import importlib


def test_read_write_json(tmp_path):
    mod = importlib.import_module('app')
    p = tmp_path / 't.json'
    data = [{'a': 1, 'b': 'x'}]
    mod.write_json_atomic(p, data)
    assert mod.read_json(p) == data


def test_allowed_file():
    mod = importlib.import_module('app')
    assert mod.allowed_file('a.png')
    assert mod.allowed_file('photo.JPG')
    assert not mod.allowed_file('doc.pdf')


def test_customer_crud(client):
    import app as mod
    # add customer
    resp = client.post('/customers/add', data={'name': 'Alice', 'mobile_number': '9999999999', 'address': 'Home'}, follow_redirects=True)
    assert b'Customer added' in resp.data
    customers = json.loads(mod.CUSTOMERS_FILE.read_text(encoding='utf-8'))
    assert len(customers) == 1
    cid = customers[0]['id']

    # delete customer
    resp = client.post(f'/customers/delete/{cid}', follow_redirects=True)
    assert b'Customer deleted' in resp.data
    customers = json.loads(mod.CUSTOMERS_FILE.read_text(encoding='utf-8'))
    assert len(customers) == 0


def test_product_add_and_toggle(client):
    import app as mod
    # add product
    resp = client.post('/products/add', data={'name': 'Widget', 'price': '49.5'}, follow_redirects=True)
    assert b'Product added' in resp.data
    products = json.loads(mod.PRODUCTS_FILE.read_text(encoding='utf-8'))
    assert len(products) == 1
    pid = products[0]['id']
    assert products[0]['is_deleted'] is False

    # toggle delete
    resp = client.post(f'/products/toggle_delete/{pid}', follow_redirects=True)
    assert b'Product status changed' in resp.data
    products = json.loads(mod.PRODUCTS_FILE.read_text(encoding='utf-8'))
    assert products[0]['is_deleted'] is True


def test_billing_create(client):
    import app as mod
    # create customer
    client.post('/customers/add', data={'name': 'Bob', 'mobile_number': '8888888888', 'address': 'Addr'}, follow_redirects=True)
    customers = json.loads(mod.CUSTOMERS_FILE.read_text(encoding='utf-8'))
    cid = customers[0]['id']

    # create product
    client.post('/products/add', data={'name': 'Space Kit', 'price': '120.00'}, follow_redirects=True)
    products = json.loads(mod.PRODUCTS_FILE.read_text(encoding='utf-8'))
    pid = products[0]['id']
    # create bill programmatically (no UI)
    bills = json.loads(mod.BILLS_FILE.read_text(encoding='utf-8'))
    items = [{'product_id': pid, 'qty': 2, 'unit_price': 120.0, 'amount': 240.0}]
    bill = {
        'id': str(mod.uuid.uuid4()),
        'invoice_no': mod.next_invoice_no(),
        'date': mod.datetime.date.today().isoformat(),
        'customer_id': cid,
        'order_id': None,
        'items': items,
        'total': 240.0,
        'notes': 'Thank you',
        'created_at': mod.now_iso(),
    }
    bills.append(bill)
    mod.write_json_atomic(mod.BILLS_FILE, bills)
    bills = json.loads(mod.BILLS_FILE.read_text(encoding='utf-8'))
    assert len(bills) >= 1
    b0 = bills[-1]
    assert b0['total'] == 240.0
    assert 'invoice_no' in b0


def test_orders_page(client):
    # visits the orders page (empty) and checks the content
    resp = client.get('/orders')
    assert resp.status_code == 200
    assert b'Orders Received' in resp.data


def test_place_order_creates_orderrecord(client):
    import app as mod
    # create product
    client.post('/products/add', data={'name': 'Gizmo', 'price': '10.00'}, follow_redirects=True)
    products = json.loads(mod.PRODUCTS_FILE.read_text(encoding='utf-8'))
    pid = products[0]['id']

    # add to cart (JSON) -> uses session
    resp = client.post('/cart/add', json={'product_id': pid, 'quantity': 2})
    assert resp.status_code == 200
    # place order
    resp = client.post('/cart/place', data={'name': 'Carol', 'mobile': '7777777777', 'address': 'Addr'}, follow_redirects=True)
    assert b'Order placed' in resp.data
    orders = json.loads(mod.ORDERS_FILE.read_text(encoding='utf-8'))
    assert len(orders) == 1
    o = orders[0]
    # check required fields
    assert 'id' in o
    assert 'orderid' in o and o['orderid'] == o['id']
    assert 'customer_id' in o
    assert 'customerid' in o and o['customerid'] == o['customer_id']
    assert o['customer_name'] == 'Carol'
    assert o['customer_mobile'] == '7777777777'
    assert isinstance(o.get('items'), list) and len(o['items']) == 1


def test_create_bill_from_order(client):
    import app as mod
    # create product
    client.post('/products/add', data={'name': 'Widget2', 'price': '15.00'}, follow_redirects=True)
    products = json.loads(mod.PRODUCTS_FILE.read_text(encoding='utf-8'))
    pid = products[0]['id']

    # add to cart and place order
    client.post('/cart/add', json={'product_id': pid, 'quantity': 1})
    client.post('/cart/place', data={'name': 'Dan', 'mobile': '6666666666', 'address': 'Addr'}, follow_redirects=True)
    orders = json.loads(mod.ORDERS_FILE.read_text(encoding='utf-8'))
    assert len(orders) == 1
    oid = orders[0]['id']

    # create bill from order
    resp = client.post(f'/orders/create_bill/{oid}', follow_redirects=True)
    assert b'Bill created from order' in resp.data

    bills = json.loads(mod.BILLS_FILE.read_text(encoding='utf-8'))
    assert len(bills) == 1
    b = bills[0]
    assert b.get('order_id') == oid

    # billing page should list the bill
    resp = client.get('/billing')
    assert resp.status_code == 200
    assert b'Invoice' in resp.data or bytes(b.get('invoice_no', ''), 'utf-8') in resp.data


def test_orders_add_page_and_post(client):
    import app as mod
    # create customer and product
    client.post('/customers/add', data={'name': 'Eve', 'mobile_number': '5555555555', 'address': 'Addr'}, follow_redirects=True)
    client.post('/products/add', data={'name': 'ProdX', 'price': '9.50'}, follow_redirects=True)
    customers = json.loads(mod.CUSTOMERS_FILE.read_text(encoding='utf-8'))
    products = json.loads(mod.PRODUCTS_FILE.read_text(encoding='utf-8'))
    cid = customers[0]['id']
    pid = products[0]['id']

    # GET add page
    resp = client.get('/orders/add')
    assert resp.status_code == 200

    # POST create order
    data = {
        'customer_id': cid,
        'item_product_0': pid,
        'item_qty_0': '3'
    }
    resp = client.post('/orders/add', data=data, follow_redirects=True)
    assert b'Order created' in resp.data
    orders = json.loads(mod.ORDERS_FILE.read_text(encoding='utf-8'))
    assert len(orders) >= 1
    o = orders[-1]
    assert o['customer_id'] == cid
    assert isinstance(o['items'], list) and o['items'][0]['product_id'] == pid
