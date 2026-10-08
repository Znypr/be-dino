import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bind_products', ROOT / 'tools/bind_products.py')
bindings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bindings)


class ProductBindingsTests(unittest.TestCase):
    def test_verified_bindings_and_closed_release(self):
        manifest = json.loads((ROOT / 'resources/monetization/crystal-products.json').read_text())
        config = (ROOT / 'src/shared/Config.luau').read_text()
        self.assertIn(bindings.render(manifest), config)
        self.assertIn('CrystalPacksEnabled = false', config)
        self.assertIn('PaidRandomItemsEnabled = false', config)
        self.assertEqual([p['defaultRobux'] for p in manifest['products']], [49, 129, 299, 699, 1499, 4999])

    def test_duplicate_ids_rejected(self):
        manifest = json.loads((ROOT / 'resources/monetization/crystal-products.json').read_text())
        manifest['products'].append(manifest['products'][0])
        with self.assertRaises(AssertionError):
            bindings.render(manifest)
