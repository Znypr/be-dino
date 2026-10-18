"""tools/label_grid_sheet.py on a synthetic image (BD-1034)."""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import label_grid_sheet as lg  # noqa: E402


def sheet():
    img = Image.new("RGB", (200, 120), (30, 160, 60))
    ImageDraw.Draw(img).rectangle([10, 10, 90, 50], fill=(200, 30, 30))
    return img


class LabelGridSheetTest(unittest.TestCase):
    def test_art_is_untouched_and_margin_is_added(self):
        img = sheet()
        out = lg.label_sheet(img, 4, 2, margin=50)
        self.assertEqual(out.size, (250, 170))
        self.assertEqual(out.crop((50, 50, 250, 170)).tobytes(), img.tobytes())

    def test_margin_has_ink_over_each_column_and_row(self):
        out = lg.label_sheet(sheet(), 4, 2, margin=50)
        bg = out.getpixel((0, 0))
        for c in range(4):
            x0, x1 = 50 + c * 50, 50 + (c + 1) * 50
            self.assertTrue(any(out.getpixel((x, y)) != bg for x in range(x0 + 5, x1 - 5) for y in range(5, 40)), "column %d" % c)
        for r in range(2):
            y0, y1 = 50 + r * 60, 50 + (r + 1) * 60
            self.assertTrue(any(out.getpixel((x, y)) != bg for x in range(5, 40) for y in range(y0 + 5, y1 - 5)), "row %d" % r)

    def test_names(self):
        self.assertEqual(lg.tile_id(3, 2), "D3")
        self.assertEqual(lg.tile_id(0, 0), "A1")
        self.assertEqual(lg.column_name(26), "AA")

    def test_cli_keeps_original_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "s.png"
            sheet().save(src)
            before = src.read_bytes()
            self.assertEqual(lg.main([str(src), "--cols", "4", "--rows", "2"]), 0)
            self.assertTrue((Path(t) / "s-labelled.png").exists())
            self.assertEqual(src.read_bytes(), before)
            self.assertEqual(lg.main([str(src), "--cols", "4", "--rows", "2", "--out", str(src)]), 2)

    def test_bad_grid(self):
        with self.assertRaises(ValueError):
            lg.label_sheet(sheet(), 0, 2)


if __name__ == "__main__":
    unittest.main()
