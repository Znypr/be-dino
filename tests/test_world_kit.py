"""BD-049/050 kit: manifest <-> OBJ <-> baked native models, budgets, colliders, food values."""
import json, re
from collections import Counter
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
class WorldKitTests(unittest.TestCase):
    def setUp(self): self.manifest = json.loads((ROOT / 'assets/blender/world/world-kit-manifest.json').read_text())
    def test_assets_closed_within_budget_and_packaged(self):
        ids = [a['id'] for a in self.manifest['assets']]
        self.assertEqual(len(ids), len(set(ids))); self.assertGreaterEqual(len(ids), 41)
        for a in self.manifest['assets']:
            faces = [l for l in (ROOT / a['obj']).read_text().splitlines() if l.startswith('f ')]
            self.assertEqual(len(faces), a['triangles']); self.assertLessEqual(a['triangles'], a['budget'])
            edges = Counter()
            for f in faces:
                idx = [int(x) for x in f.split()[1:]]
                for x, y in zip(idx, idx[1:] + idx[:1]): edges[tuple(sorted((x, y)))] += 1
            self.assertTrue(all(n == 2 for n in edges.values()), a['id'])
            self.assertAlmostEqual(a['bounds'][0][1], 0, places=4)  # pivot: bbox bottom centre
            for axis in (0, 2): self.assertAlmostEqual(a['bounds'][0][axis] + a['bounds'][1][axis], 0, places=3)
            model = ET.parse(ROOT / 'resources/worldkit' / f"{a['id']}.rbxmx").getroot().find('Item')
            parts = model.findall('Item')
            self.assertLessEqual(len(parts), 2 * a['triangles'])
            for p in parts: self.assertEqual(p.find("Properties/bool[@name='CanCollide']").text, 'false')
            if a['kind'] in ('tree', 'rock', 'landmark'): self.assertTrue(a['colliders'], a['id'])
            if a['kind'] in ('shrub', 'groundcover', 'food'): self.assertFalse(a['colliders'], a['id'])
    def test_food_values_and_defaults_unchanged(self):
        food = (ROOT / 'src/server/FoodService.luau').read_text()
        self.assertEqual(re.findall(r'id = "(\w+)", weight = \d+, points = (\d+)', food), [('berry', '1'), ('fruit', '4'), ('egg', '15'), ('amber', '50')])
        self.assertEqual({a['family']: a['points'] for a in self.manifest['assets'] if a['kind'] == 'food'}, {'berry': 1, 'fruit': 4, 'egg': 15, 'amber': 50})
        config = (ROOT / 'src/shared/Config.luau').read_text()
        self.assertIn('FoodArtMode = "Legacy"', config); self.assertIn('WorldArtMode = "Legacy"', config)
        import sys; sys.path.insert(0, str(ROOT / 'tools')); import release_profiles as rp
        out, report = rp.apply_profile(config, 'playtest')
        self.assertIn('WorldArtMode = "BiomeKit"', out); self.assertIn('FoodArtMode = "Kit"', out); self.assertIn('WorldArtDensity = 0.35', out)
    def test_no_roblox_ids_invented(self):
        self.assertNotIn('rbxassetid', json.dumps(self.manifest))
if __name__ == '__main__': unittest.main()
