"""tools/tile_seam_check.py on tiles made on the spot (BD-1034)."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import tile_seam_check as tsc  # noqa: E402

N = 64


def dots(period, n=N):
    """Round dots on a square lattice; True = white."""
    y, x = np.indices((n, n))
    cx, cy = (x % period) - period / 2, (y % period) - period / 2
    return (cx * cx + cy * cy) < (period / 4) ** 2


def stripes(period=16, n=N):
    return ((np.arange(n)[None, :] % period) < period // 2).repeat(n, 0)


def stray_pixels(good, seed):
    """A seamless tile with two random pixels all round, as a bad cut of a sheet leaves."""
    rng = np.random.default_rng(seed)
    padded = np.pad(good, 2, mode="constant")
    mask = np.ones(padded.shape, bool)
    mask[2:-2, 2:-2] = False
    return np.where(mask, rng.random(padded.shape) > 0.5, padded)


class SeamTest(unittest.TestCase):
    def test_seamless_tile_passes(self):
        for t in (dots(16), stripes(16), np.zeros((N, N), bool)):
            a = tsc.analyze(t)
            self.assertEqual(a["status"], "PASS", a)
            self.assertLessEqual(a["H"], tsc.THRESHOLD)
            self.assertLessEqual(a["V"], tsc.THRESHOLD)

    def test_visible_seam_fails(self):
        a = tsc.analyze(dots(24))  # 64 is not a multiple of 20: a dot is cut at the edge
        self.assertEqual(a["status"], "FAIL", a)
        self.assertGreater(max(a["H"], a["V"]), tsc.THRESHOLD)

    def test_hard_cut_through_stripes_fails_one_direction(self):
        a = tsc.analyze(stripes(24))  # vertical stripes whose period does not fit; the one-column edge test cannot see it, the context test must
        self.assertEqual(a["status"], "FAIL")
        self.assertGreater(a["H"], tsc.THRESHOLD)
        self.assertLessEqual(a["V"], tsc.THRESHOLD)

    def test_shifted_crop_passes_at_the_right_offset(self):
        a = tsc.analyze(stray_pixels(dots(16), 3))
        self.assertEqual(a["status"], "PASS-SHIFT", a)
        self.assertEqual(a["H_trim"], (2, 2))
        self.assertEqual(a["V_trim"], (2, 2))
        self.assertGreater(a["H"], tsc.THRESHOLD)
        self.assertLessEqual(a["H_best"], tsc.THRESHOLD)

    def test_repair_makes_a_failing_tile_pass_and_keeps_the_original(self):
        t = dots(24)
        before = t.copy()
        r = tsc.repair(t)
        self.assertIsNotNone(r["method"])
        self.assertEqual(r["analysis"]["status"], "PASS")
        self.assertTrue(np.array_equal(t, before))

    def test_repair_of_shifted_crop_uses_trim(self):
        r = tsc.repair(stray_pixels(dots(16), 5))
        self.assertEqual(r["method"], "trim")
        self.assertGreater(r["look"], 0.8)

    def test_folder_run_never_overwrites_originals(self):
        with tempfile.TemporaryDirectory() as t:
            src, fix = Path(t) / "src", Path(t) / "fixed"
            src.mkdir()
            Image.fromarray(dots(24).astype(np.uint8) * 255).save(src / "x.png")
            Image.fromarray(dots(16).astype(np.uint8) * 255).save(src / "ok.png")
            before = (src / "x.png").read_bytes()
            res = tsc.run_folder(str(src), fix_dir=str(fix))
            by = {r["name"]: r for r in res}
            self.assertEqual(by["ok"]["analysis"]["status"], "PASS")
            self.assertEqual(by["x"]["analysis"]["status"], "FAIL")
            self.assertTrue((fix / "x.png").exists())
            self.assertFalse((fix / "ok.png").exists())
            self.assertEqual((src / "x.png").read_bytes(), before)
            self.assertEqual(by["x"]["repair"]["analysis"]["status"], "PASS")
            self.assertTrue(np.array_equal(np.array(Image.open(fix / "x.png").convert("L")) >= 128, by["x"]["repair"]["tile"]))
            self.assertTrue((fix / "repairs.json").exists())

    def test_fail_sheet_is_written(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "f.png"
            tsc.fail_sheet([("x", dots(24), "H9 V9"), ("y", dots(26), "H8 V8")], str(out))
            self.assertTrue(out.exists())
            with Image.open(out) as im:
                self.assertGreater(im.width, 300)


if __name__ == "__main__":
    unittest.main()
