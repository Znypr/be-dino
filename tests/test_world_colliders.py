"""BD-1098: unit tests for tools/world_colliders.py (the solid world as footprints on the ground plane) without a Luau runner.

The dump itself needs the pinned Luau runner and is exercised by tools/verify_food_layer.py in CI; here the geometry, the parser and the
copied Arena constants are checked."""
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import world_colliders as wc  # noqa: E402


def extent(poly):
    xs, zs = [p[0] for p in poly], [p[1] for p in poly]
    return round(max(xs) - min(xs), 3), round(max(zs) - min(zs), 3)


class FootprintTests(unittest.TestCase):
    def test_a_box_without_rotation_keeps_its_size(self):
        poly = wc.box_footprint((10.0, 0.0, -5.0), wc.mul(wc.ry(0.0), wc.rz(0.0)), (0.0, 1.0, 0.0), (4.0, 2.0, 2.0))
        self.assertEqual(extent(poly), (4.0, 2.0))
        self.assertAlmostEqual(sum(p[0] for p in poly) / len(poly), 10.0)
        self.assertAlmostEqual(sum(p[1] for p in poly) / len(poly), -5.0)

    def test_yaw_turns_the_long_side(self):
        poly = wc.box_footprint((0.0, 0.0, 0.0), wc.ry(math.pi / 2), (0.0, 1.0, 0.0), (4.0, 2.0, 2.0))
        self.assertEqual(extent(poly), (2.0, 4.0))

    def test_yaw_moves_the_offset_like_roblox(self):
        # Roblox CFrame.Angles(0, yaw, 0): local +x goes to (cos, 0, -sin). A quarter turn sends an offset of +3 on x to -3 on z.
        poly = wc.box_footprint((0.0, 0.0, 0.0), wc.ry(math.pi / 2), (3.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        self.assertAlmostEqual(sum(p[0] for p in poly) / len(poly), 0.0, places=6)
        self.assertAlmostEqual(sum(p[1] for p in poly) / len(poly), -3.0, places=6)

    def test_a_fallen_log_lies_flat(self):
        # a box 1 x 10 x 1 standing on its pivot, rolled a quarter turn about z: it now lies along x
        poly = wc.box_footprint((0.0, 0.0, 0.0), wc.mul(wc.ry(0.0), wc.rz(math.pi / 2)), (0.0, 5.0, 0.0), (1.0, 10.0, 1.0))
        self.assertEqual(extent(poly), (10.0, 1.0))

    def test_hull_drops_inner_points(self):
        self.assertEqual(len(wc.hull([(0, 0), (4, 0), (4, 4), (0, 4), (2, 2), (1, 1)])), 4)


class DistanceTests(unittest.TestCase):
    square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]

    def test_inside_edge_corner_and_disc(self):
        box = wc.Obstacle('box', self.square)
        self.assertEqual(box.distance(2.0, 2.0), 0.0)
        self.assertAlmostEqual(box.distance(7.0, 2.0), 3.0)
        self.assertAlmostEqual(box.distance(7.0, 8.0), 5.0)
        disc = wc.Obstacle('disc', centre=(0.0, 0.0), radius=2.0)
        self.assertAlmostEqual(disc.distance(5.0, 0.0), 3.0)
        self.assertEqual(disc.distance(1.0, 1.0), 0.0)

    def test_hash_finds_the_nearest_within_the_cap(self):
        items = [wc.Obstacle('box', self.square, label='a'),
                 wc.Obstacle('box', [(x + 100.0, z) for x, z in self.square], label='b'),
                 wc.Obstacle('disc', centre=(-200.0, 50.0), radius=10.0, label='c')]
        obs = wc.Obstacles(items)
        self.assertAlmostEqual(obs.distance(6.0, 2.0, 6.0), 2.0)
        self.assertEqual(obs.nearest(6.0, 2.0, 6.0)[1], 'a')
        self.assertEqual(obs.distance(50.0, 50.0, 6.0), 6.0)        # nothing within the cap: the cap
        self.assertEqual(obs.nearest(50.0, 50.0, 6.0), (6.0, None))
        self.assertAlmostEqual(obs.distance(-185.0, 50.0, 6.0), 5.0)
        self.assertAlmostEqual(obs.distance(103.0, 3.0, 6.0), 0.0)


class DumpTests(unittest.TestCase):
    TEXT = ('P\ttree\tt1\t10.0000\t3.0000\t20.0000\t0.000000\t0.000000\t2.000000\n'
            'P\tlog\tl1\t-30.0000\t1.0000\t5.0000\t0.000000\t1.570796\t1.000000\n'
            'P\tshrub\tbush\t0.0000\t0.0000\t0.0000\t0.000000\t0.000000\t1.000000\n'
            'C\tt1\t0.0000\t2.0000\t0.0000\t1.0000\t4.0000\t1.0000\t0.000000\n'
            'C\tl1\t0.0000\t2.0000\t0.0000\t1.0000\t4.0000\t1.0000\t0.000000\n'
            'E\tt1\ttree\t4.0\t6.0\t4.0\nE\tl1\ttree\t4.0\t10.0\t4.0\nE\tbush\tshrub\t2.0\t1.0\t2.0\n'
            'H\ttrue\n')

    def test_parse_and_footprints(self):
        props, cols, ext, hub = wc.parse(self.TEXT)
        self.assertEqual((len(props), hub), (3, True))
        items = wc.prop_obstacles(props, cols, ext)
        self.assertEqual(len(items), 2)                      # the bush has no collider
        tree, log = items
        self.assertEqual(extent(tree.poly), (2.0, 2.0))      # trunk 1 x 1 at scale 2
        self.assertAlmostEqual(tree.distance(10.0, 20.0), 0.0)
        self.assertAlmostEqual(tree.distance(13.0, 20.0), 2.0)
        # the log is one box (c[3], extent.y * .9, c[5]) * scale lying along x after the quarter turn about z: 9 long, 1 wide
        self.assertEqual(extent(log.poly), (9.0, 1.0))
        self.assertAlmostEqual(log.distance(-29.0, 5.0), 1.0, places=5)   # the rolled log reaches from x = -39 to the pivot at -30
        self.assertAlmostEqual(log.distance(-40.0, 5.0), 1.0, places=5)


class ArenaConstantsTests(unittest.TestCase):
    """tools/world_colliders.py copies the numbers of the parts Arena.build() always makes; a change in the source must fail here."""

    def test_the_copied_numbers_are_still_in_arena_luau(self):
        arena = (ROOT / 'src' / 'server' / 'Arena.luau').read_text(encoding='utf-8')
        for text in ('local slots = if kitMode then 5 else 11', 'Vector3.new(t, 0, -extent - 5)', 'Vector3.new(t, 0, extent + 5)',
                     'Vector3.new(-extent - 5, 0, t)', 'Vector3.new(extent + 5, 0, t)', 'random:NextNumber(1.6, 2.6)',
                     '"world_boulder_bare_l" else "world_boulder_mossy_l"', 'local archZ = -15 * S', '{-96 * S, -64 * S}',
                     'Vector3.new(7,23,8) * S', 'Vector3.new(42,6,9) * S', '-80*S', 'local x,z = 30+i*10,-30', 'Vector3.new(6,1.2+i*.4,6)'):
            self.assertIn(text, arena, text)
        self.assertEqual((wc.RING_SLOTS, wc.RING_OFFSET, wc.RING_MAX_SCALE, wc.SCALE, wc.ARENA_HALF), (5, 5.0, 2.6, 1.6, 416.0))
        self.assertEqual((wc.ARCH_PILLAR, wc.ARCH_TOP), ((7 * 1.6, 23 * 1.6, 8 * 1.6), (42 * 1.6, 6 * 1.6, 9 * 1.6)))

    def test_arena_obstacles_cover_the_ring_the_arch_and_the_stones(self):
        cols = {i: [(0.0, 1.0, 0.0, 6.0, 5.0, 5.0, 0.0)] for i in wc.RING_IDS}
        items = wc.arena_obstacles(cols)
        self.assertEqual(len(items), 4 * 6 + 3 + 4)
        ring = [o for o in items if o.kind == 'disc']
        self.assertEqual(len(ring), 24)
        self.assertTrue(all(abs(o.r - 2.6 * .5 * math.hypot(6.0, 5.0)) < 1e-9 for o in ring))   # reach x the largest scale
        pillar = next(o for o in items if o.label == 'arch pillar')
        self.assertAlmostEqual(pillar.distance(-96 * 1.6, -15 * 1.6), 0.0)


if __name__ == '__main__':
    unittest.main()
