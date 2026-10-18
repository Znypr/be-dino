"""BD-1047 (docs/187 B): unit tests for the designed food map generator, its data files and the before/after tools. Offline, no Luau runner needed
(tools/verify_food_layer.py and tools/verify_gameplay.py cover the Luau side)."""
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import compare_food_layers as cmp  # noqa: E402
import food_layer_data  # noqa: E402
import generate_food_layer as gen  # noqa: E402
import layer_stats  # noqa: E402
import worldlayer  # noqa: E402


def flat_ground(size=832, hole=True):
    """A synthetic ground model: all ground except the safe-spawn disc, two gentle hills (heights every 4 studs)."""
    arena = size / 2
    mask = []
    for iz in range(size):
        z = -arena + iz + 0.5
        row = ''.join('0' if hole and math.hypot(-arena + ix + 0.5, z - 30) < 11 else '1' for ix in range(size))
        mask.append(row)
    n = size // 4
    heights = []
    for iz in range(n):
        z = -arena + (iz + 0.5) * 4
        heights.append([60 * math.exp(-((-arena + (ix + 0.5) * 4 - 250) ** 2 + (z + 200) ** 2) / 8000)
                        + 40 * math.exp(-((-arena + (ix + 0.5) * 4 + 250) ** 2 + (z - 180) ** 2) / 8000) for ix in range(n)])
    return {'arena': arena, 'cell': 1.0, 'mask': mask, 'hcell': 4.0, 'height': heights}


class CommittedMapTests(unittest.TestCase):
    def test_python_copy_decodes_and_counts(self):
        layer = worldlayer.decode(food_layer_data.TEXT)
        self.assertEqual((layer.width, layer.height, layer.world_half_width), (1000, 1000, 416.0))
        for kind, value in gen.KIND_IDS.items():
            self.assertEqual(layer.count(value), gen.COUNTS[kind], kind)
        self.assertEqual(layer.count(), 3600)
        self.assertEqual(sum(gen.COUNTS.values()), 3600)

    def test_luau_module_holds_the_same_text(self):
        self.assertEqual(gen.committed_text(), food_layer_data.TEXT)
        self.assertEqual(food_layer_data.COUNTS, gen.COUNTS)

    def test_text_is_small(self):
        self.assertLess(len(food_layer_data.TEXT), 20000)  # a ModuleScript holds it easily (docs/187 D)

    def test_kind_mix_is_todays_mix(self):
        shares = {k: v / 3600 for k, v in gen.COUNTS.items()}
        for kind, want in (('berry', 0.70), ('fruit', 0.20), ('egg', 0.07), ('amber', 0.03)):
            self.assertAlmostEqual(shares[kind], want, delta=0.005)

    def test_starter_radius_matches_the_luau_reader(self):
        luau = (ROOT / 'src/shared/FoodLayer.luau').read_text(encoding='utf-8')
        self.assertIn('StarterRadius = %g' % gen.STARTER_RADIUS, luau)
        for cx, cz in gen.STARTER_CENTRES:
            self.assertIn('{%g, %g}' % (cx, cz), luau)

    def test_flag_is_off_by_default(self):
        config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
        self.assertRegex(config, r'FoodLayerEnabled = false,')


class GeneratorPieceTests(unittest.TestCase):
    def test_hash_nearest(self):
        h = gen.Hash()
        h.add(0, 0)
        h.add(30, 0)
        self.assertAlmostEqual(h.nearest(10, 0, 50), 10)
        self.assertAlmostEqual(h.nearest(100, 100, 20), 20)  # nothing within the cap: the cap

    def test_snap_is_a_cell_centre(self):
        layer = worldlayer.WorldLayer(gen.WIDTH, gen.WIDTH, gen.ARENA)
        x, z = gen.snap(layer, 12.34, -56.78)
        self.assertEqual(layer.cell_of(x, z), layer.cell_of(12.34, -56.78))
        self.assertEqual(gen.snap(layer, x, z), (x, z))

    def test_density_is_gentle_and_never_zero(self):
        far = gen.density(-400, -400)
        self.assertEqual(far, 1.0)
        self.assertGreater(gen.density(0, 30), far)
        for zone in gen.ZONES:
            self.assertGreater(gen.density(zone['x'], zone['z']), gen.density(zone['x'] + 5 * zone['r'], zone['z']))
        self.assertLess(max(gen.density(x, z) for x in range(-400, 401, 40) for z in range(-400, 401, 40)), 3.0)

    def test_starter_patch_has_nine_spaced_sites_outside_the_spawn_disc(self):
        ground = gen.Ground(flat_ground())
        layer = worldlayer.WorldLayer(gen.WIDTH, gen.WIDTH, gen.ARENA)
        for centre in gen.STARTER_CENTRES:
            sites = gen.starter_patch(ground, layer, centre)
            self.assertEqual(len(sites), 9)
            for x, z in sites:
                self.assertTrue(ground.ok(x, z))
                self.assertLessEqual(math.hypot(x - centre[0], z - centre[1]), gen.STARTER_RADIUS)
            for i, a in enumerate(sites):
                for b in sites[i + 1:]:
                    self.assertGreaterEqual(math.hypot(a[0] - b[0], a[1] - b[1]), gen.MIN_SPACING - 0.9)  # snapping to cells moves a site up to 0.6

    def test_cover_select_beats_random_picks(self):
        rng = random.Random(5)
        pts = [(rng.uniform(-200, 200), rng.uniform(-200, 200)) for _ in range(600)]
        samples = [(x, z) for x in range(-190, 200, 20) for z in range(-190, 200, 20)]

        def worst(chosen):
            return max(min(math.hypot(sx - pts[i][0], sz - pts[i][1]) for i in chosen) for sx, sz in samples)
        picked = gen.cover_select(pts, range(len(pts)), samples, 20, [])
        self.assertEqual(len(set(picked)), 20)
        self.assertLess(worst(picked), worst(rng.sample(range(len(pts)), 20)))
        relaxed = gen.lloyd(pts, range(len(pts)), samples, picked, [], 3)
        self.assertEqual(len(set(relaxed)), 20)
        self.assertLessEqual(worst(relaxed), worst(picked) * 1.1)

    def test_poisson_pick_keeps_its_distance(self):
        rng = random.Random(9)
        pts = [(rng.uniform(0, 300), rng.uniform(0, 300)) for _ in range(900)]
        chosen = gen.poisson_pick(pts, range(len(pts)), 40, [], rng, 30.0)
        self.assertEqual(len(chosen), 40)
        for i, a in enumerate(chosen):
            for b in chosen[i + 1:]:
                self.assertGreaterEqual(math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1]), 30.0 - 4.0 * 6)  # radius may relax in steps of 4


class SmallGenerationTests(unittest.TestCase):
    """The whole generator on a synthetic island, with a smaller total so it runs in seconds."""

    def run_small(self):
        saved = (gen.TOTAL, dict(gen.COUNTS))
        gen.TOTAL, gen.COUNTS.update({'berry': 420, 'fruit': 120, 'egg': 42, 'amber': 18})
        gen.TOTAL = sum(gen.COUNTS.values())
        try:
            return gen.generate(flat_ground())
        finally:
            gen.TOTAL = saved[0]
            gen.COUNTS.clear()
            gen.COUNTS.update(saved[1])

    def test_rules_hold_and_result_is_deterministic(self):
        a = self.run_small()
        b = self.run_small()
        self.assertEqual(a['layer'].encode(), b['layer'].encode())
        pts = a['points']
        self.assertEqual(len(pts), 600)
        for kind, want in (('berry', 420), ('fruit', 120), ('egg', 42), ('amber', 18)):
            self.assertEqual(sum(1 for p in pts if p[2] == kind), want, kind)
        self.assertEqual(a['layer'].count(), 600)  # one food per cell
        ground = a['ground']
        for x, z, _ in pts:
            self.assertTrue(ground.ok(x, z))
            self.assertGreater(math.hypot(x - gen.SPAWN[0], z - gen.SPAWN[1]), 11)
        nearest = min(math.hypot(p[0] - q[0], p[1] - q[1]) for i, p in enumerate(pts) for q in pts[i + 1:])
        self.assertGreaterEqual(nearest, gen.MIN_SPACING - 0.9)
        self.assertEqual(len(a['tops']), 4)

    def test_a_clumped_layout_breaks_the_spread_rules(self):
        rng = random.Random(3)
        clumped = [(rng.uniform(-60, 60), rng.uniform(-60, 60), 'berry') for _ in range(600)]
        result = layer_stats.analyse(clumped, 416.0, 256, (10, 20, 30))
        broken = layer_stats.check_targets(result, {'rules': [{'kind': 'all', 'block': 20, 'metric': 'empty_share', 'max': 0.02},
                                                              {'kind': 'all', 'metric': 'empty_zone_count', 'max': 0}]})
        self.assertEqual(len(broken), 2)


class CompareToolTests(unittest.TestCase):
    def test_layer_points_round_trip(self):
        layer = worldlayer.WorldLayer(100, 100, 416.0)
        layer.set_cell(3, 4, 2)
        layer.set_cell(50, 60, 4)
        pts = cmp.layer_points(layer)
        self.assertEqual(sorted(p[2] for p in pts), ['amber', 'fruit'])

    def test_greedy_walk_eats_the_closest_food_first(self):
        eaten, points = cmp.greedy_walk([(0.0, 52.0, 'egg'), (0.0, 400.0, 'amber')], 0.5, 'nearest')
        self.assertEqual((eaten, points), (1, 15))

    def test_block_points_use_the_points_of_each_kind(self):
        grid = cmp.block_points([(-400.0, -400.0, 'amber'), (-399.0, -399.0, 'berry')], 65.0)
        self.assertEqual(grid[0][0], 51)

    def test_the_old_and_new_layouts_share_one_total(self):
        self.assertEqual(sum(gen.COUNTS.values()), 3600)


if __name__ == '__main__':
    unittest.main()
