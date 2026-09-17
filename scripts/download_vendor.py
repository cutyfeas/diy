import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'static' / 'vendor'

ASSETS = [
    ('https://code.jquery.com/jquery-3.5.1.min.js', VENDOR / 'jquery' / 'jquery.min.js'),
    ('https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js', VENDOR / 'popper' / 'popper.min.js'),
    ('https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css', VENDOR / 'bootstrap' / 'css' / 'bootstrap.min.css'),
    ('https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js', VENDOR / 'bootstrap' / 'js' / 'bootstrap.min.js'),
]


def ensure(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path):
    ensure(dest)
    print(f'Downloading {url} -> {dest}')
    try:
        urllib.request.urlretrieve(url, dest)
        print('OK')
    except Exception as e:
        print('FAILED', e)


def main():
    for url, dest in ASSETS:
        download(url, dest)


if __name__ == '__main__':
    main()
