import json
import importlib


def test_add_and_edit_bill(client, tmp_path):
    mod = importlib.import_module('app')
    # create customer
    client.post('/customers/add', data={'name': 'Charlie', 'mobile_number': '7777777777', 'address': 'Addr'}, follow_redirects=True)
    customers = json.loads(mod.CUSTOMERS_FILE.read_text(encoding='utf-8'))
    cid = customers[0]['id']

    # create product
    client.post('/products/add', data={'name': 'Magnet', 'price': '10.00'}, follow_redirects=True)
    products = json.loads(mod.PRODUCTS_FILE.read_text(encoding='utf-8'))
    pid = products[0]['id']

    # create a bill directly (billing UI removed)
    bills = json.loads(mod.BILLS_FILE.read_text(encoding='utf-8'))
    items = [{'product_id': pid, 'qty': 5, 'unit_price': 10.0, 'amount': 50.0}]
    bill = {
        'id': str(mod.uuid.uuid4()),
        'invoice_no': mod.next_invoice_no(),
        'date': mod.datetime.date.today().isoformat(),
        'customer_id': cid,
        'order_id': None,
        'items': items,
        'total': 50.0,
        'notes': '',
        'created_at': mod.now_iso(),
    }
    bills.append(bill)
    mod.write_json_atomic(mod.BILLS_FILE, bills)

    # edit bill -> change qty
    bill_id = bill['id']
    edit_data = {
        'customer_id': cid,
        'item_product_0': pid,
        'item_qty_0': '3'
    }
    resp = client.post(f'/billing/edit/{bill_id}', data=edit_data, follow_redirects=True)
    assert b'Bill updated' in resp.data
    bills = json.loads(mod.BILLS_FILE.read_text(encoding='utf-8'))
    edited = next((b for b in bills if b['id'] == bill_id), None)
    assert edited is not None
    assert edited['total'] == 30.0
