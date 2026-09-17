import json
from pathlib import Path
import os

BASE = Path(__file__).resolve().parents[1]
DB = BASE / 'DB'


def read(p: Path):
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding='utf-8') or '[]')
    except Exception:
        return []


def write_atomic(p: Path, data):
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(str(tmp), str(p))


def ensure_bill_order_tag(bills_file: Path):
    bills = read(bills_file)
    changed = False
    added = 0
    for b in bills:
        if 'order_id' not in b:
            b['order_id'] = None
            changed = True
            added += 1
    if changed:
        write_atomic(bills_file, bills)
    return added


def ensure_orders_customer_product(order_file: Path, customers_file: Path, products_file: Path):
    orders = read(order_file)
    customers = read(customers_file)
    products = read(products_file)
    cust_map = {c.get('mobile_number'): c.get('id') for c in customers}
    prod_map_by_name = {p.get('name'): p.get('id') for p in products}
    changed = False
    cust_assigned = 0
    prod_assigned = 0
    for o in orders:
        if 'customer_id' not in o or not o.get('customer_id'):
            mobile = o.get('customer_mobile') or o.get('mobile')
            cid = cust_map.get(mobile)
            if cid:
                o['customer_id'] = cid
                cust_assigned += 1
            else:
                o['customer_id'] = o.get('customer_id') if 'customer_id' in o else None
            changed = True
        # ensure items have product_id
        for it in o.get('items', []):
            if 'product_id' not in it or not it.get('product_id'):
                pname = it.get('product_name') or it.get('name')
                pid = prod_map_by_name.get(pname)
                if pid:
                    it['product_id'] = pid
                    prod_assigned += 1
                else:
                    it['product_id'] = it.get('product_id') if 'product_id' in it else None
                changed = True
    if changed:
        write_atomic(order_file, orders)
    return cust_assigned, prod_assigned


def link_bills_orders(bills_file: Path, orders_file: Path):
    bills = read(bills_file)
    orders = read(orders_file)
    order_map = {o.get('id'): o for o in orders}
    linked = 0
    changed = False
    for b in bills:
        oid = b.get('order_id')
        if oid:
            o = order_map.get(oid)
            if o and o.get('bill_id') != b.get('id'):
                o['bill_id'] = b.get('id')
                changed = True
                linked += 1
    if changed:
        write_atomic(orders_file, orders)
    return linked


def main():
    bills_file = DB / 'bills.json'
    orders_file = DB / 'orderreceived.json'
    customers_file = DB / 'customers.json'
    products_file = DB / 'products.json'

    print('Ensuring bills have order_id...')
    a = ensure_bill_order_tag(bills_file)
    print(f'Added order_id field to {a} bills')

    print('Ensuring orders have customer_id and items have product_id...')
    ca, pa = ensure_orders_customer_product(orders_file, customers_file, products_file)
    print(f'Assigned customer_id to {ca} orders, assigned product_id to {pa} order items')

    print('Linking bills -> orders (setting order.bill_id where possible)...')
    l = link_bills_orders(bills_file, orders_file)
    print(f'Linked {l} orders to bills')


if __name__ == '__main__':
    main()
