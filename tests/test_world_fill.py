"""BD-1245 + BD-1246 world fill: offline source checks (the Luau checks are tools/verify_world_fill.py, in CI)."""
import importlib.util
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


class WorldFillTests(unittest.TestCase):
    def test_flags_ship_off_and_playtest_turns_them_on(self):
        text = read('src/shared/Config.luau')
        spec = importlib.util.spec_from_file_location('release_profiles', ROOT / 'tools' / 'release_profiles.py')
        profiles = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(profiles)
        playtest = profiles.apply_profile(text, 'playtest')[0]
        for flag in ('GroundDetailEnabled', 'ThingsToDoEnabled'):
            self.assertIn(f'    {flag} = false,\n', text)
            self.assertIn(f'{flag} = true', playtest)
            self.assertIn(flag, [key for key, _ in profiles.REHEARSAL_ON])
        self.assertEqual(profiles.verify_source(text, 'default').errors, [])

    def test_nine_published_ids_with_registry_lines(self):
        items = re.findall(r'((?:fill|set)_\w+) = \{assetId = "(\d+)"', read('src/shared/WorldFill.luau'))
        self.assertEqual(len(items), 9)
        self.assertEqual(len({i for _, i in items}), 9)
        registry = read('docs/77-asset-registry.md')
        for key, aid in items:
            self.assertIn(f'| world_gen_{key} |', registry)
            self.assertIn(f'| {aid} |', registry)

    def test_gated_and_bootstrap_untouched(self):
        self.assertIn('if not V3 or not (ground or things) then return end', read('src/server/Arena.luau'))
        self.assertIn('if layer and text == nil and v3 and thingsOn() then', read('src/shared/FoodLayer.luau'))
        self.assertIn('if not fixed and fillGround then', read('src/server/IslandTerrain.luau'))
        boot = read('src/client/Bootstrap.client.luau')
        self.assertNotIn('WorldFill', boot)
        fill = read('src/shared/WorldFill.luau')
        self.assertIn('c.VegetationV2Enabled == true and c[key] == true', fill)


if __name__ == '__main__':
    unittest.main()
