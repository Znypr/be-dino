"""BD-1279: tools/ref_compare.py measures pieces in % of height from their own edge, outline, gloss, and writes the report."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ref_compare as rc  # noqa: E402


def button(img, box, fill, outline=6, gloss=False):
    d = ImageDraw.Draw(img)
    x, y, w, h = box
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=(10, 10, 10))
    ix, iy, iw, ih = x + outline, y + outline, w - 2 * outline, h - 2 * outline
    for k in range(ih):
        t = k / max(ih - 1, 1)
        c = tuple(int(v * (1.35 - 0.7 * t)) if gloss else v for v in fill)
        c = tuple(max(0, min(255, v)) for v in c)
        d.line([ix, iy + k, ix + iw - 1, iy + k], fill=c)


class RefCompareTests(unittest.TestCase):
    def test_measure_is_edge_anchored_in_percent_of_height(self):
        m = rc.measure_box([1000, 72, 100, 72], W=1280)  # a right piece, 180 px from the right edge
        self.assertEqual(m["col"], "right")
        self.assertAlmostEqual(m["edge"], 25.0)
        self.assertAlmostEqual(m["top"], 10.0)
        self.assertAlmostEqual(m["h"], 10.0)

    def test_outline_and_gloss(self):
        img = Image.new("RGB", (400, 720), (240, 220, 170))
        button(img, (50, 100, 300, 120), (60, 200, 40), outline=5, gloss=True)
        s = rc.box_stats(img, (50, 100, 300, 120))
        self.assertAlmostEqual(s["outline_px"], 5, delta=1)
        self.assertGreater(s["shade"], 40)
        flat = Image.new("RGB", (400, 720), (240, 220, 170))
        button(flat, (50, 100, 300, 120), (60, 200, 40), outline=2)
        f = rc.box_stats(flat, (50, 100, 300, 120))
        self.assertLess(abs(f["shade"]), 5)
        self.assertAlmostEqual(f["outline_px"], 2, delta=1)

    def test_report_finds_the_size_padding_and_gloss_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ref = Image.new("RGB", (1500, 720), (240, 210, 160))
            button(ref, (40, 200, 300, 115), (60, 200, 40), outline=5, gloss=True)
            game = Image.new("RGB", (1800, 720), (230, 220, 180))  # wider screen: left piece still lines up
            button(game, (25, 240, 300, 100), (60, 200, 40), outline=2)
            ref.save(tmp / "ref.png")
            game.save(tmp / "game.png")
            boxes = {"unit": "px", "ref": {"shop": [40, 200, 300, 115]}, "game": {"shop": [25, 240, 300, 100]}}
            rep = rc.compare(tmp / "ref.png", tmp / "game.png", tmp / "out", boxes=boxes)
            self.assertTrue((tmp / "out" / "report.html").exists())
            self.assertTrue((tmp / "out" / "2-zone-middle-left.png").exists())
            shop = next(e for e in rep["elements"] if e["name"] == "shop")
            self.assertAlmostEqual(shop["ref"]["edge"] - shop["game"]["edge"], (40 - 25) / 7.2, places=1)
            whats = {(c["name"], c["what"]) for c in rep["changes"]}
            self.assertIn(("shop", "height"), whats)
            self.assertIn(("shop", "top"), whats)
            self.assertIn(("shop", "edge padding"), whats)
            self.assertIn(("shop", "outline"), whats)
            self.assertIn(("shop", "shading (top minus bottom brightness)"), whats)
            json.loads((tmp / "out" / "report.json").read_text(encoding="utf-8"))

    def test_bad_usage(self):
        self.assertEqual(rc.main(["missing-ref.png", "missing-game.png"]), 2)


if __name__ == "__main__":
    unittest.main()
