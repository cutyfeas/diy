# DIY HUE STUDIO

DIY HUE STUDIO is a lightweight Flask application for a craft and design studio shop. It helps manage customers, products, orders, and billing using local JSON files instead of a database.

## Features

- Customer management with add/edit/delete flows
- Product catalog with image upload support and thumbnail generation
- Cart-based ordering with session storage
- Order creation and tracking
- Billing and invoice generation
- Dashboard showing key sales and catalog metrics
- Local static asset support for Bootstrap, jQuery, and Popper

## Tech stack

- Python 3
- Flask
- Pillow for image processing
- JSON-based persistence for app data
- Bootstrap for the front-end UI

## Prerequisites

- Python 3.10+
- pip
- Git (optional, for version control)

## Local setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Vendor assets

The app expects local Bootstrap and JavaScript vendor files in `static/vendor`. You can download them with the included script:

```powershell
cd scripts
.\download_vendor.ps1
```

This populates the vendor folder so the app can load local assets without relying on a CDN.

## Application structure

```text
app.py                 # Flask application and routes
DB/                    # JSON storage for customers, products, bills, orders
static/                # CSS, JS, uploads, vendor libraries
templates/             # HTML templates
scripts/               # helper scripts
tests/                 # pytest test suite
requirements.txt       # Python dependencies
README.md              # project documentation
```

## Data storage

The project stores data in JSON files under the `DB` folder:

- `customers.json`
- `products.json`
- `bills.json`
- `orderreceived.json`

This is intentionally simple and makes the project easy to run locally, but it is not a production-grade database solution.

## Testing

Run the test suite with:

```bash
pytest
```

## Notes

- The app uses a Flask secret key for session management.
- Product images are stored in `static/uploads`.
- Orders are tracked in session-based cart flow and then persisted to JSON.
- This project is meant as a demo/shop management application and is best suited for local development and learning.
