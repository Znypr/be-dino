"""tools/cut_icon_sheet.py and tools/art_contact_sheet.py on a synthetic sheet (art batch 1, BD-1094)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import art_contact_sheet as acs  # noqa: E402
import cut_icon_sheet as ci  # noqa: E402

BG = (229, 228, 228)


def make_sheet(path, cols=4, rows=2, clip_first=False, noisy=False):
    w, h = 800, 400
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    cw, ch = w // cols, h // rows
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * cw + 20, r * ch + 20
            d.ellipse([x0, y0, x0 + 160, y0 + 160], fill=(200 - c * 30, 40 + r * 60, 90))
            d.rectangle([x0 + 60, y0 + 60, x0 + 100, y0 + 100], fill=(255, 255, 255))  # inside: kept
    if clip_first:
        d.rectangle([0, 0, 60, 60], fill=(10, 10, 200))
    if noisy:
        import random
        random.seed(3)
        for _ in range(120000):
            d.point((random.randrange(w), random.randrange(h)), fill=(random.randrange(256),) * 3)
    img.save(path)


class CutIconSheetTest(unittest.TestCase):
    def test_cuts_every_cell_and_makes_background_transparent(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet = os.path.join(tmp, "s.png")
            make_sheet(sheet)
            res = ci.process_sheet(sheet, os.path.join(tmp, "out"), "t", 4, 2, size=64)
            self.assertEqual(len(res), 8)
            self.assertEqual(sorted(res)[0], "t-A1")
            for cid, info in res.items():
                self.assertTrue(info["transparent"], cid)
                self.assertEqual(info["flags"], [], cid)
                im = Image.open(os.path.join(tmp, "out", cid + ".png"))
                self.assertEqual(im.size, (64, 64))
                self.assertEqual(im.getpixel((0, 0))[3], 0)  # corner is transparent
                self.assertEqual(im.getpixel((32, 32))[3], 255)  # centre is solid (white square inside kept)

    def test_row_names_become_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet = os.path.join(tmp, "s.png")
            make_sheet(sheet)
            res = ci.process_sheet(sheet, os.path.join(tmp, "out"), "food", 4, 2, size=32, ids=["berry", "fruit"])
            self.assertIn("food-berry-A", res)
            self.assertIn("food-fruit-D", res)

    def test_object_at_sheet_edge_is_flagged_clipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet = os.path.join(tmp, "s.png")
            make_sheet(sheet, cols=4, rows=2)
            img = Image.open(sheet)
            ImageDraw.Draw(img).ellipse([0, 0, 160, 160], fill=(10, 10, 200))  # replaces the first ball, touching the corner
            img.save(sheet)
            res = ci.process_sheet(sheet, os.path.join(tmp, "out"), "t", 4, 2, size=32)
            self.assertTrue(any("CLIPPED" in v["flags"] for v in res.values()))

    def test_noisy_background_keeps_cells_and_flags_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet = os.path.join(tmp, "s.png")
            make_sheet(sheet, noisy=True)
            res = ci.process_sheet(sheet, os.path.join(tmp, "out"), "t", 4, 2, size=32)
            self.assertEqual(len(res), 8)
            self.assertTrue(all("BG-NOT-CLEAN" in v["flags"] and not v["transparent"] for v in res.values()))

    def test_contact_sheet_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet = os.path.join(tmp, "s.png")
            make_sheet(sheet)
            outdir = os.path.join(tmp, "out")
            ci.process_sheet(sheet, outdir, "t", 4, 2, size=64, ids=["a", "b"])
            png = os.path.join(tmp, "contact.png")
            code = acs.main([outdir, png, "--group", "A=t-a-*", "--group", "B=t-b-*", "--tile", "80", "--perrow", "8"])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.getsize(png) > 500)


if __name__ == "__main__":
    unittest.main()
