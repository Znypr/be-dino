"""tools/tile_window_cut.py on a fake sheet made on the spot (BD-1034 part 1b)."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import tile_window_cut as twc  # noqa: E402
import tile_seam_check as tsc  # noqa: E402


def dot_cell(size=300, pitch=50, radius=16, lead=28):
    """Round dots in rows, 6 x 6, with an empty margin all round (the 'margin pattern' we ask ChatGPT for)."""
    y, x = np.indices((size, size))
    cx = (x - lead) % pitch - pitch / 2 + pitch / 2
    cy = (y - lead) % pitch
    cx = np.where(cx > pitch / 2, cx - pitch, cx)
    cy = np.where(cy > pitch / 2, cy - pitch, cy)
    white = (cx * cx + cy * cy) < radius ** 2
    white &= (x < lead + 5 * pitch + radius + 1) & (y < lead + 5 * pitch + radius + 1)
    return white


def checks_cell(size=300, squares=6):
    s = size // squares
    y, x = np.indices((size, size))
    return (((x // s) + (y // s)) % 2) == 0


class WindowTest(unittest.TestCase):
    def test_margin_pattern_window_is_seamless(self):
        cell = (dot_cell() * 255).astype(np.uint8)
        x0, wd, y0, ht = twc.best_window(cell)
        self.assertGreaterEqual(wd, int(0.55 * 300))
        self.assertLess(abs(wd - ht) / max(wd, ht), 0.07)
        m = np.array(Image.fromarray(cell[y0:y0 + ht, x0:x0 + wd]).resize((256, 256))) >= 128
        self.assertIn(tsc.analyze(m)["status"], ("PASS", "PASS-SHIFT"))

    def test_checks_window_has_even_square_count(self):
        cell = (checks_cell() * 255).astype(np.uint8)
        x0, wd, y0, ht = twc.checks_window(cell)
        self.assertEqual(wd % 2, 0)
        self.assertGreater(wd, 150)
        self.assertLess(abs(wd - ht), 4)

    def test_square_edges_found(self):
        white = checks_cell(squares=6)
        edges = twc.square_edges(white, 0)
        self.assertEqual(len(edges), 5)  # 6 squares have 5 edges between them


if __name__ == "__main__":
    unittest.main()
