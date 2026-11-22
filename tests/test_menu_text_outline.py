"""tools/menu_spec_check.measure_text: the outline around kid-style words is measured (owner proposal pictures), anti-aliased edges and
dark panels behind a word don't fool it. Regression for 2026-11-23: the first version read 0 px outline on every proposal word."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import menu_spec_check as m  # noqa: E402


def stroke(screen, key):
    spec = json.loads((ROOT / "docs" / "menu-specs" / screen / "spec.json").read_text(encoding="utf-8"))
    elems = m.expand(spec)
    img = np.asarray(Image.open(ROOT / "docs" / "menu-specs" / screen / "proposal.jpg").convert("RGB"))
    box = m.abs_box(elems, key, spec["proposal_window_px"])
    return m.measure_text(m.crop(img, box), spec["proposal_window_px"][3], elems[key].get("color"))


class TextOutline(unittest.TestCase):
    def test_thick_outline_on_green_header(self):
        r = stroke("potion-shop", "title")
        self.assertGreaterEqual(r["stroke_px"], 5)
        self.assertLess(max(r["stroke_col"]), 40)  # black outline

    def test_yellow_timer_has_outline(self):
        self.assertGreaterEqual(stroke("potion-shop", "timer")["stroke_px"], 3)

    def test_dark_panel_is_not_outline(self):
        self.assertLessEqual(stroke("dino-index", "selected.name")["stroke_px"], 6)

    def test_grey_word_without_outline(self):
        self.assertLessEqual(stroke("dino-index", "selected.rarity")["stroke_px"], 1)


if __name__ == "__main__":
    unittest.main()
