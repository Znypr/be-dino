"""BD-1320 ground patches: offline source checks (the Luau checks are tools/verify_ground_patches.py, in CI)."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_ground_patches  # noqa: E402


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


class GroundPatchesTests(unittest.TestCase):
    def test_source_guards(self):
        self.assertEqual(verify_ground_patches.source_checks(), [])

    def test_behind_ground_detail_flag_which_ships_off(self):
        self.assertIn('    GroundDetailEnabled = false,\n', read('src/shared/Config.luau'))
        terrain = read('src/server/IslandTerrain.luau')
        self.assertIn('local Patches = require(ReplicatedStorage.Shared.GroundPatches)', terrain)
        self.assertEqual(terrain.count('Patches.surface('), 1)

    def test_pure_module(self):
        text = read('src/shared/GroundPatches.luau')
        for word in ('Instance.new', 'workspace', 'game:GetService'):
            self.assertNotIn(word, text)

    def test_in_ci(self):
        self.assertIn('tools/verify_ground_patches.py --runner', read('.github/workflows/build-generated-place.yml'))


if __name__ == '__main__':
    unittest.main()
