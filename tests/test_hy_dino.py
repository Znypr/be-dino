"""tools/hy_dino_lib.py and tools/hy_dino.py (BD-1304): spike tip choice, sheet view finding, generated species configs."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hy_dino_lib as lib  # noqa: E402


class TipTests(unittest.TestCase):
    def test_strongest_first_merged_and_capped(self):
        cands = [(0.30, (0.5, 0, 2), (1, 0, 0)), (0.29, (0.52, 0, 2), (1, 0, 0)), (0.20, (0.5, 1, 2), (1, 0, 0)), (0.10, (0.5, 2, 2), (1, 0, 0))]
        tips = lib.select_tips(cands, merge=0.1)
        self.assertEqual([p for p, _ in tips], [(0.5, 0, 2), (0.5, 1, 2), (0.5, 2, 2)])
        self.assertEqual(len(lib.select_tips(cands, merge=0.1, count=2)), 2)
        self.assertEqual(len(lib.select_tips(cands, merge=0.1, floor=0.15)), 2)

    def test_mirror_skips_the_centre_line(self):
        tips = [((0.5, 0, 2), (1, 0, 0)), ((0.0, 1, 3), (0, 0, 1))]
        out = lib.mirror_tips(tips)
        self.assertEqual(len(out), 3)
        self.assertIn(((-0.5, 0, 2), (-1, 0, 0)), out)


class SheetTests(unittest.TestCase):
    def test_runs_join_small_gaps(self):
        self.assertEqual(lib.runs([1, 1, 0, 1, 0, 0, 0, 1, 1], gap=1), [(0, 4), (7, 9)])

    def test_columns_merge_to_four_figures(self):
        cols = [0] * 5 + [9] * 30 + [0] * 2 + [9] * 5 + [0] * 20 + [9] * 40 + [0] * 25 + [9] * 50 + [0] * 25 + [9] * 30 + [0] * 5
        got = lib.panels_from_columns(cols, want=4)
        self.assertEqual(len(got), 4)
        self.assertEqual(got[0], (5, 42), "the spike 2 px away joins the first figure")

    def test_label_pill_is_not_part_of_the_figure(self):
        rows = [0] * 10 + [5] * 80 + [0] * 8 + [5] * 12 + [0] * 10
        self.assertEqual(lib.figure_rows(rows), (10, 90))

    def test_sheet_command_finds_four_views(self):
        try:
            from PIL import Image, ImageDraw
            import hy_dino
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as d:
            im = Image.new("RGB", (1024, 682), (220, 220, 220))
            dr = ImageDraw.Draw(im)
            for x0, w in ((20, 160), (230, 200), (470, 320), (830, 160)):
                dr.ellipse((x0, 90, x0 + w, 260), fill=(90, 110, 200))
                dr.rounded_rectangle((x0 + 20, 285, x0 + w - 20, 305), 8, fill=(90, 90, 90))   # label pill
            p = Path(d) / "sheet.png"
            im.save(p)
            self.assertEqual(hy_dino.cmd_sheet(p, Path(d) / "out"), 0)
            for v in ("front", "side", "back"):
                with Image.open(Path(d) / "out" / f"proj-{v}.png") as crop:
                    self.assertLess(crop.height, 180, f"{v} crop must stop above the label pill")
            self.assertTrue((Path(d) / "out" / "q34.png").exists())


class ConfigTests(unittest.TestCase):
    QUAD = {"size": [3.3, 5.4, 3.0], "y": [-2.7, 2.7], "legs": [[0.5, 1.6], [-1.1, 0.0]], "leg_top": 0.8, "leg_inner": 0.15,
            "head_z": 2.2, "head_y": 1.7, "tail_y": -1.5}
    BIPED = {"size": [1.5, 3.5, 3.0], "y": [-1.8, 1.8], "legs": [[-0.5, 0.4]], "leg_top": 1.2, "leg_inner": 0.18, "head_z": 1.72,
             "head_y": 1.0, "tail_y": -0.55}

    def labels(self, plan, a):
        from types import SimpleNamespace as P
        cfg = {}
        exec(lib.species_config("X", plan, a), cfg)
        lab = lambda x, y, z: cfg["label"](P(x=x, y=y, z=z))
        return cfg, lab

    def test_quadruped(self):
        cfg, lab = self.labels("quadruped", self.QUAD)
        self.assertEqual(lab(0, 2.3, 1.5), "Head")
        self.assertEqual(lab(0, -2.3, 1.2), "Tail")
        self.assertEqual(lab(-0.8, 1.0, 0.2), "LegFL")
        self.assertEqual(lab(0.8, -0.5, 0.2), "LegBR")
        self.assertEqual(lab(0, 0.3, 1.5), "Body")
        self.assertEqual(set(cfg["BUDGET"]), set(cfg["PARTS"]))

    def test_biped_and_flyer(self):
        cfg, lab = self.labels("biped", self.BIPED)
        self.assertEqual(lab(0, 0.5, 2.5), "Head")
        self.assertEqual(lab(-0.4, 0.0, 0.3), "LegL")
        self.assertIn("ArmL", cfg["PARTS"])
        cfg, lab = self.labels("flyer", self.BIPED)
        self.assertIn("WingR", cfg["PARTS"])
        self.assertTrue(lab(0.9, 0.0, 1.5).startswith("Wing"))

    def test_unknown_plan(self):
        with self.assertRaises(ValueError):
            lib.species_config("X", "snake", self.QUAD)


if __name__ == "__main__":
    unittest.main()
