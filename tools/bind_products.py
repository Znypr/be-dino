"""Bind verified Creator Hub products without enabling their release gates."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def render(manifest):
    assert manifest['universeId'] == 10769812255
    assert manifest['ownerType'] == 'User' and manifest['ownerId'] == 7285577648
    products = manifest['products']
    ids = [p['productId'] for p in products]
    assert len(ids) == len(set(ids)) and all(type(i) is int and i > 0 for i in ids)
    assert all(type(p['crystals']) is int and p['crystals'] > 0 for p in products)
    return '    DeveloperProducts = { ' + ', '.join(
        f"[{p['productId']}] = {p['crystals']}" for p in products
    ) + ' },'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'resources/monetization/crystal-products.json').read_text())
    path = ROOT / 'src/shared/Config.luau'
    source = path.read_text()
    generated, count = re.subn(r'^    DeveloperProducts = .*$', render(manifest), source, flags=re.M)
    assert count == 1, 'Config binding anchor must be unique'
    if args.check:
        assert generated == source, 'Run tools/bind_products.py to refresh bindings'
    else:
        path.write_text(generated)
    print('Verified developer product bindings; release gates unchanged')


if __name__ == '__main__':
    main()
