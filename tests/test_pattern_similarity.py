"""tools/pattern_similarity.py on synthetic tiles (BD-1034)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import pattern_similarity as ps  # noqa: E402

N = 64


def dots(period, n=N, r=0.28):
    y, x = np.indices((n, n))
    cx, cy = (x % period) - period / 2, (y % period) - period / 2
    return (cx * cx + cy * cy) < (period * r) ** 2


def stripes(period=16, n=N):
    return ((np.arange(n)[None, :] % period) < period // 2).repeat(n, 0)


def checks(period=16, n=N):
    y, x = np.indices((n, n))
    return ((x // (period // 2)) + (y // (period // 2))) % 2 == 0


def feats(tiles, existing=()):
    out = [ps.Features("E:" + k, v, existing=True) for k, v in existing]
    out += [ps.Features(k, v) for k, v in tiles]
    for f in out:
        f.flags = ps.tile_flags(f)
    return out


class SimilarityTest(unittest.TestCase):
    def test_turned_and_slid_copy_is_a_duplicate(self):
        b = np.roll(np.rot90(stripes(16)), 5, axis=1)
        fs = feats([("a", stripes(16)), ("b", b)])
        self.assertGreater(ps.pair_scores(fs[0], fs[1])["sim"], 0.95)

    def test_different_shapes_are_not(self):
        fs = feats([("dots", dots(16)), ("stripes", stripes(16)), ("checks", checks(32))])
        for (i, j), s in ps.compare_all(fs).items():
            self.assertLess(s["sim"], 0.75, (fs[i].name, fs[j].name, s))

    def test_same_shape_at_another_size_is_flagged_as_scale(self):
        fs = feats([("big", dots(32)), ("small", dots(16))])
        self.assertGreater(ps.pair_scores(fs[0], fs[1])["scale"], 0.85)

    def test_clusters_and_shortlist_keep_one_of_a_group(self):
        fs = feats([("d1", dots(16)), ("d2", np.roll(dots(16), 7, axis=0)), ("s", stripes(16)), ("c", checks(32))])
        pairs = ps.compare_all(fs)
        groups = ps.clusters(len(fs), ps.flagged_pairs(fs, pairs, 0.75))
        self.assertEqual([sorted(fs[i].name for i in g) for g in groups], [["d1", "d2"]])
        picked = [fs[i].name for i in ps.select(fs, pairs, 0.75)]
        self.assertEqual(len([n for n in picked if n in ("d1", "d2")]), 1)
        self.assertIn("s", picked)
        self.assertIn("c", picked)

    def test_candidate_like_an_existing_pattern_is_dropped(self):
        fs = feats([("cand", stripes(16)), ("other", checks(32))], existing=[("bands", np.roll(stripes(16), 3, axis=1))])
        picked = [fs[i].name for i in ps.select(fs, ps.compare_all(fs), 0.75)]
        self.assertNotIn("cand", picked)
        self.assertIn("other", picked)

    def test_flags_for_empty_noise_and_fine_grey(self):
        empty = np.zeros((N, N), bool)
        empty[10, 10] = True
        noise = np.random.default_rng(1).random((N, N)) > 0.5
        fine = checks(2)  # 1 px checker: pure grey once shrunk
        by = {f.name: f for f in feats([("empty", empty), ("noise", noise), ("fine", fine), ("good", dots(16))])}
        self.assertIn("EMPTY", by["empty"].flags)
        self.assertIn("BUSY", by["noise"].flags)
        self.assertIn("GREY", by["fine"].flags)
        self.assertEqual(by["good"].flags, [])

    def test_seam_failure_blocks_the_shortlist(self):
        fs = feats([("ok", dots(16)), ("cut", dots(24))])
        self.assertEqual(fs[0].flags, [])
        self.assertIn("SEAM", fs[1].flags)
        self.assertNotIn("cut", [fs[i].name for i in ps.select(fs, ps.compare_all(fs), 0.75)])

    def test_owner_group_forces_one_cluster(self):
        fs = feats([("a", dots(16)), ("b", stripes(16)), ("c", checks(32))])
        pairs = ps.compare_all(fs)
        self.assertFalse(ps.expect_cluster(fs, pairs, ["a", "b", "c"], 0.75))
        ps.apply_owner_groups(fs, pairs, [{"tiles": ["a", "b", "c"]}])
        self.assertTrue(ps.expect_cluster(fs, pairs, ["a", "b", "c"], 0.75))
        self.assertEqual(len(ps.select(fs, pairs, 0.75)), 1)

    def test_build_prefers_repaired_copy_and_runs_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "c").mkdir()
            (t / "f").mkdir()
            Image.fromarray(dots(24).astype(np.uint8) * 255).save(t / "c" / "x-A1.png")
            Image.fromarray(dots(16).astype(np.uint8) * 255).save(t / "f" / "x-A1.png")
            Image.fromarray(stripes(16).astype(np.uint8) * 255).save(t / "c" / "x-B1.png")
            (t / "f" / "repairs.json").write_text(json.dumps({"x-A1": {"method": "period-crop"}}))
            by = {f.name: f for f in ps.build([str(t / "c")], [], [str(t / "f")])}
            self.assertEqual(by["x-A1"].fixed, "period-crop")
            self.assertEqual(by["x-A1"].seam["status"], "PASS")
            self.assertIsNone(by["x-B1"].fixed)
            sheet = t / "sheet.png"
            self.assertEqual(ps.main([str(t / "c"), "--fixed", str(t / "f"), "--sheet", str(sheet)]), 0)
            self.assertTrue(sheet.exists())


if __name__ == "__main__":
    unittest.main()
