"""BD-1238 (docs/241 W6 + W7): the V3 food map with the food at matching hosts (tools/food_hosts.py, src/shared/FoodLayerDataV3Hosts.luau)."""
from pathlib import Path
import math
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import compare_food_layers as cmp  # noqa: E402
import food_hosts as fh  # noqa: E402
import food_layer_data_v3 as v3data  # noqa: E402
import food_layer_data_v3_hosts as data  # noqa: E402
import generate_food_layer as gen  # noqa: E402
import worldlayer  # noqa: E402

CENTRE = (0.0, 30.0)


class CommittedHostsMapTests(unittest.TestCase):
    def test_python_copy_matches_the_luau_module(self):
        self.assertEqual(gen.committed_text(fh.LUAU_PATH), data.TEXT)
        self.assertNotEqual(data.TEXT, v3data.TEXT)

    def test_same_foods_kinds_and_zone_counts_as_the_v3_map(self):
        pts = cmp.layer_points(worldlayer.decode(data.TEXT))
        v3 = cmp.layer_points(worldlayer.decode(v3data.TEXT))
        self.assertEqual({k: sum(1 for p in pts if p[2] == k) for k in gen.COUNTS}, gen.COUNTS)
        self.assertEqual(fh.zone_counts([p + (None,) for p in pts], CENTRE), fh.zone_counts([p + (None,) for p in v3], CENTRE))

    def test_starter_patches_are_untouched(self):
        pts = cmp.layer_points(worldlayer.decode(data.TEXT))
        v3 = cmp.layer_points(worldlayer.decode(v3data.TEXT))
        for cx, cz in v3data.STARTER_CENTRES:
            near = lambda P: sorted(p for p in P if math.hypot(p[0] - cx, p[1] - cz) <= v3data.STARTER_RADIUS)  # noqa: E731
            self.assertEqual(near(pts), near(v3))


class PieceTests(unittest.TestCase):
    def test_zones_follow_the_worldv3_sectors(self):
        src = (ROOT / 'src/shared/WorldV3.luau').read_text(encoding='utf-8')
        found = re.findall(r'\{id = "(\w+)", name = "[^"]+", biome = "\w+", from = (-?\d+), to = (-?\d+)\}', src)
        self.assertEqual(tuple((i, float(a), float(b)) for i, a, b in found), fh.ZONES)
        self.assertEqual(fh.zone_of(CENTRE, 100.0, 30.0), 'meadow')      # angle 0
        self.assertEqual(fh.zone_of(CENTRE, 0.0, 130.0), 'forest')       # angle 90
        self.assertEqual(fh.zone_of(CENTRE, -100.0, 29.0), 'beach')      # angle just past 180
        self.assertEqual(fh.zone_of(CENTRE, 10.0, -70.0), 'volcano')     # angle about 276

    def test_ring_spaces_slots_round_the_ellipse(self):
        pts = fh.ring(10.0, 20.0, 4.0, 4.0, 0.0)
        self.assertGreaterEqual(len(pts), 7)
        for x, z in pts:
            self.assertAlmostEqual(math.hypot(x - 10.0, z - 20.0), 4.0, places=6)
        gaps = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pts, pts[1:] + pts[:1])]
        self.assertGreater(min(gaps), fh.MIN_SPACING)

    def test_every_kind_has_hosts_and_a_cap(self):
        for kind, hosts in fh.KIND_HOSTS.items():
            for host in hosts:
                self.assertIn((host, kind), fh.CAP)

    def test_flag_is_off_by_default_and_needs_the_toon_island(self):
        cfg = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
        self.assertIn('FoodHostsEnabled = false,', cfg)
        reader = (ROOT / 'src/shared/FoodLayer.luau').read_text(encoding='utf-8')
        self.assertIn('FoodHostsEnabled == true', reader)
        self.assertIn('ToonWorldEnabled == true', reader)
        self.assertIn('FoodLayerDataV3Hosts', reader)


if __name__ == '__main__':
    unittest.main()
