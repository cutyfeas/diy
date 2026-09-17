import importlib
import pytest
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import app` works when pytest runs
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Import app module and monkeypatch its DB paths to tmp_path locations
    mod = importlib.import_module('app')
    tmp_db = tmp_path / 'DB'
    tmp_static = tmp_path / 'static'
    tmp_db.mkdir()
    (tmp_static / 'uploads').mkdir(parents=True)

    monkeypatch.setattr(mod, 'DB_DIR', tmp_db)
    monkeypatch.setattr(mod, 'CUSTOMERS_FILE', tmp_db / 'customers.json')
    monkeypatch.setattr(mod, 'PRODUCTS_FILE', tmp_db / 'products.json')
    monkeypatch.setattr(mod, 'BILLS_FILE', tmp_db / 'bills.json')
    monkeypatch.setattr(mod, 'ORDERS_FILE', tmp_db / 'orderreceived.json')
    monkeypatch.setattr(mod, 'UPLOAD_DIR', tmp_static / 'uploads')

    # initialize files
    (mod.CUSTOMERS_FILE).write_text('[]', encoding='utf-8')
    (mod.PRODUCTS_FILE).write_text('[]', encoding='utf-8')
    (mod.BILLS_FILE).write_text('[]', encoding='utf-8')
    (mod.ORDERS_FILE).write_text('[]', encoding='utf-8')

    mod.app.config['TESTING'] = True
    client = mod.app.test_client()
    return client
