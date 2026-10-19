"""tools/tile_seam_strict.py on tiles made on the spot (BD-1034 part 1b)."""
import sys
import unittest
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import tile_seam_strict as tss  # noqa: E402

N = 128


def dots(period, n=N, shift=0):
    y, x = np.indices((n, n))
    cx, cy = ((x + shift) % period) - period / 2, (y + shift) % period - period / 2
    return (cx * cx + cy * cy) < (period / 4) ** 2


class StrictTest(unittest.TestCase):
    def test_lattice_is_clean(self):
        w = dots(32)
        self.assertFalse(tss.frame_ring(w))
        cs = tss.cut_shapes(w)
        self.assertEqual((cs["white"], cs["black"]), (0, 0))

    def test_frame_ring_is_found(self):
        w = dots(32).copy()
        w[0, :] = True
        w[-1, :] = True
        w[:, 0] = True
        w[:, -1] = True
        self.assertTrue(tss.frame_ring(w))

    def test_all_black_and_all_white_have_no_frame(self):
        self.assertFalse(tss.frame_ring(np.zeros((N, N), bool)))
        self.assertFalse(tss.frame_ring(np.ones((N, N), bool)))

    def test_label_counts_blobs(self):
        m = np.zeros((8, 8), bool)
        m[1:3, 1:3] = True
        m[5:7, 5:7] = True
        lab, n = tss.label(m)
        self.assertEqual(n, 2)

    def blobs(self):
        w = np.zeros((N, N), bool)
        for (y, x) in ((10, 20), (10, 60), (90, 40)):
            w[y:y + 20, x:x + 20] = True  # three whole 20 x 20 shapes
        return w

    def test_whole_shapes_are_clean(self):
        w = self.blobs()
        w[40:60, 108:128] = True  # one more whole shape, touching the right edge, continuing on the left edge
        w[40:60, 0:1] = True
        # the shape across the seam is 21 wide: close enough to the others, not cut
        self.assertEqual(sum(tss.cut_shapes(w).values()), 0)

    def test_cut_shape_is_found(self):
        w = self.blobs()
        w[40:80, 100:128] = True  # a tall shape at the right edge ...
        w[40:80, 0:4] = True  # ... glued to a piece at the left edge: one blob 3 times the others
        cs = tss.cut_shapes(w)
        self.assertGreater(cs["white"] + cs["black"], 0)


if __name__ == "__main__":
    unittest.main()
