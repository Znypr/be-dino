"""BD-1248 plaza shops v2: offline source checks (the Luau checks are tools/verify_plaza_shops.py, in CI)."""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


class PlazaShopsTests(unittest.TestCase):
    def test_flag_ships_off_and_playtest_keeps_it_off(self):  # BD-1312: owner 2026-11-23 'the shops should only be in the cave'
        text = read('src/shared/Config.luau')
        import release_profiles as profiles
        playtest = profiles.apply_profile(text, 'playtest')[0]
        self.assertIn('    PlazaShopsV2Enabled = false,\n', text)
        self.assertIn('PlazaShopsV2Enabled = false', playtest)
        self.assertIn('PlazaHubEnabled = false', playtest)
        self.assertIn('PlazaShopsV2Enabled', [key for key, _ in profiles.REHEARSAL_ON])
        self.assertEqual(profiles.verify_source(text, 'default').errors, [])

    def test_one_label_per_shop_with_the_exact_words(self):
        layout = read('src/shared/PlazaShopsLayout.luau')
        self.assertEqual(re.findall(r'word = "(\w+)"', layout), ['EGGS', 'POTIONS', 'SHOP', 'DINOS'])
        server = read('src/server/PlazaShops.luau')
        self.assertNotIn('Instance.new("BillboardGui")', server)
        self.assertEqual(server.count('Instance.new("SurfaceGui")'), 1)

    def test_published_ids_with_registry_lines(self):
        items = re.findall(r'(shop_\w+) = \{assetId = "(\d+)"', read('src/shared/PlazaShopsLayout.luau'))
        self.assertEqual(len(items), 5)
        self.assertEqual(len({i for _, i in items}), 5)
        registry = read('docs/77-asset-registry.md')
        for key, aid in items:
            self.assertIn('| plaza_%s |' % key, registry)
            self.assertIn(aid, registry)

    def test_static_guards(self):
        import verify_plaza_shops
        self.assertEqual(verify_plaza_shops.static_checks(), [])


if __name__ == '__main__':
    unittest.main()
