"""BD-1239 vegetation v2: offline source checks (the Luau checks are tools/verify_vegetation_v2.py, in CI)."""
import importlib.util
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


class VegetationV2Tests(unittest.TestCase):
    def test_flag_ships_off_and_playtest_turns_it_on(self):
        self.assertIn('    VegetationV2Enabled = false,\n', read('src/shared/Config.luau'))
        spec = importlib.util.spec_from_file_location('release_profiles', ROOT / 'tools' / 'release_profiles.py')
        profiles = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(profiles)
        text = read('src/shared/Config.luau')
        playtest = profiles.apply_profile(text, 'playtest')[0]
        self.assertIn('VegetationV2Enabled = true', playtest)
        self.assertIn('VegetationV2Enabled', [key for key, _ in profiles.REHEARSAL_ON])

    def test_eighteen_published_ids_with_registry_lines(self):
        veg = read('src/shared/VegetationV2.luau')
        items = re.findall(r'(veg2_\w+) = \{assetId = "(\d+)"', veg)
        self.assertGreaterEqual(len(items), 18)  # BD-1311: 18 sheet objects, then the tree variants (two cone pines retired)
        self.assertEqual(len({i for _, i in items}), len(items))
        registry = read('docs/77-asset-registry.md')
        for key, aid in items:
            self.assertIn(f'| world_gen_{key} |', registry)
            self.assertIn(f'| {aid} |', registry)

    def test_gated_and_bootstrap_untouched(self):
        arena = read('src/server/Arena.luau')
        self.assertIn('local veg2On = Veg2.enabled(Config)', arena)
        self.assertIn('if veg2On then placed = Veg2.thin(placed) end', arena)
        self.assertNotIn('Veg2', read('src/client/Bootstrap.client.luau'))
        self.assertIn('config.VegetationV2Enabled == true', read('src/shared/VegetationV2.luau'))


if __name__ == '__main__':
    unittest.main()
