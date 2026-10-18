"""tools/compare_screenshots.py with pictures made on the spot (BD-656, docs/162)."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import compare_screenshots as cs  # noqa: E402

SIZE = (200, 120)


def base():
    img = Image.new("RGB", SIZE, (40, 90, 60))
    ImageDraw.Draw(img).rectangle([10, 10, 60, 40], fill=(200, 180, 40))
    return img


def with_box(img, box, color=(220, 30, 30)):
    out = img.copy()
    ImageDraw.Draw(out).rectangle(box, fill=color)
    return out


class CompareImages(unittest.TestCase):
    def test_same_picture_is_same(self):
        r = cs.compare_images(base(), base())
        self.assertEqual(r["changed_pixels"], 0)
        self.assertEqual(r["regions"], [])
        self.assertTrue(cs.passes(r, 0.5))
        self.assertIn("Same", cs.verdict_words(r, 0.5))

    def test_changed_box_is_counted_and_found(self):
        after = with_box(base(), [100, 50, 119, 69])        # 20 x 20 = 400 px
        r = cs.compare_images(base(), after)
        self.assertEqual(r["changed_pixels"], 400)
        self.assertAlmostEqual(r["changed_percent"], 100.0 * 400 / (SIZE[0] * SIZE[1]), places=6)
        self.assertEqual(len(r["regions"]), 1)
        x0, y0, x1, y1, n = r["regions"][0]
        self.assertEqual((x0, y0, x1, y1, n), (100, 50, 120, 70, 400))
        self.assertFalse(cs.passes(r, 0.5))
        self.assertIn("TOO MUCH CHANGE", cs.verdict_words(r, 0.5))

    def test_two_far_spots_are_two_regions_and_near_spots_join(self):
        far = with_box(with_box(base(), [100, 50, 104, 54]), [170, 100, 174, 104])
        self.assertEqual(len(cs.compare_images(base(), far)["regions"]), 2)
        near = with_box(with_box(base(), [100, 50, 104, 54]), [108, 50, 112, 54])
        self.assertEqual(len(cs.compare_images(base(), near)["regions"]), 1)

    def test_small_change_below_the_limit_passes(self):
        after = with_box(base(), [100, 50, 101, 51])       # 4 px of 24000
        r = cs.compare_images(base(), after)
        self.assertEqual(r["changed_pixels"], 4)
        self.assertTrue(cs.passes(r, 0.5))
        self.assertIn("Small change", cs.verdict_words(r, 0.5))

    def test_threshold_hides_faint_changes(self):
        after = with_box(base(), [100, 50, 119, 69], (45, 95, 65))   # 5 steps off
        self.assertEqual(cs.compare_images(base(), after, threshold=16)["changed_pixels"], 0)
        self.assertEqual(cs.compare_images(base(), after, threshold=2)["changed_pixels"], 400)

    def test_ignore_rectangle_skips_a_clock(self):
        after = with_box(base(), [100, 50, 119, 69])
        r = cs.compare_images(base(), after, ignore=[(95, 45, 40, 40)])
        self.assertEqual(r["changed_pixels"], 0)
        self.assertEqual(r["compared_pixels"], SIZE[0] * SIZE[1] - 40 * 40)
        # a change outside the ignored part still counts
        both = with_box(after, [10, 100, 19, 109])
        r2 = cs.compare_images(base(), both, ignore=[(95, 45, 40, 40)])
        self.assertEqual(r2["changed_pixels"], 100)

    def test_different_sizes_fail(self):
        r = cs.compare_images(base(), Image.new("RGB", (100, 100)))
        self.assertTrue(r["size_changed"])
        self.assertFalse(cs.passes(r, 99.0))
        self.assertIn("not the same size", cs.verdict_words(r, 0.5))

    def test_transparent_pixels_compare_as_black(self):
        a = Image.new("RGBA", (10, 10), (255, 0, 0, 0))
        b = Image.new("RGBA", (10, 10), (0, 255, 0, 0))
        self.assertEqual(cs.compare_images(a, b)["changed_pixels"], 0)

    def test_diff_picture_has_three_panels(self):
        r = cs.compare_images(base(), with_box(base(), [100, 50, 119, 69]))
        pic = cs.make_diff_picture(r)
        self.assertEqual(pic.width, SIZE[0] * 3 + 2 * cs.GAP)
        self.assertEqual(pic.height, SIZE[1] + cs.LABEL_H)
        # the changed pixel is red in the third panel
        px = pic.getpixel((2 * (SIZE[0] + cs.GAP) + 110, cs.LABEL_H + 60))
        self.assertEqual(px, cs.RED)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()):
            return cs.main(argv)

    def save(self, rel, img):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        img.save(p)
        return p

    def test_two_files_same_exit_zero_and_no_picture(self):
        a = self.save("a.png", base())
        b = self.save("b.png", base())
        out = self.dir / "d.png"
        self.assertEqual(self.main([str(a), str(b), "--out", str(out)]), 0)
        self.assertFalse(out.exists())

    def test_two_files_big_change_exit_one_and_writes_picture(self):
        a = self.save("a.png", base())
        b = self.save("b.png", with_box(base(), [100, 50, 159, 99]))
        out = self.dir / "d.png"
        self.assertEqual(self.main([str(a), str(b), "--out", str(out)]), 1)
        self.assertTrue(out.exists())
        with Image.open(out) as shown:
            self.assertEqual(shown.width, SIZE[0] * 3 + 2 * cs.GAP)

    def test_limit_can_be_raised(self):
        a = self.save("a.png", base())
        b = self.save("b.png", with_box(base(), [100, 50, 159, 99]))
        self.assertEqual(self.main([str(a), str(b), "--no-image", "--max-changed-percent", "50"]), 0)

    def test_ignore_option_makes_it_pass(self):
        a = self.save("a.png", base())
        b = self.save("b.png", with_box(base(), [100, 50, 159, 99]))
        self.assertEqual(self.main([str(a), str(b), "--no-image", "--ignore", "100,50,60,50"]), 0)

    def test_folders_match_names_and_report_missing(self):
        self.save("before/menu.png", base())
        self.save("before/shop.png", base())
        self.save("before/gone.png", base())
        self.save("after/menu.png", base())
        self.save("after/shop.png", with_box(base(), [100, 50, 159, 99]))
        self.save("after/new.png", base())
        out = self.dir / "out"
        argv = [str(self.dir / "before"), str(self.dir / "after"), "--out", str(out)]
        self.assertEqual(self.main(argv), 1)
        self.assertTrue((out / "shop_diff.png").exists())
        self.assertFalse((out / "menu_diff.png").exists())
        code, results = cs.run(cs.argparse.Namespace(
            before=argv[0], after=argv[1], out=str(out), no_image=True, threshold=16, max_changed_percent=0.5,
            min_pixels=1, ignore=None, ignore_file=None, allow_missing=False, allow_new=False, json=False))
        self.assertEqual(code, 1)
        self.assertFalse(results["gone.png"]["ok"])
        self.assertFalse(results["new.png"]["ok"])
        self.assertTrue(results["menu.png"]["ok"])
        # with both allowed, only the changed picture fails
        self.assertEqual(self.main(argv + ["--allow-missing", "--allow-new", "--max-changed-percent", "50"]), 0)

    def test_ignore_file_per_picture(self):
        self.save("before/clock.png", base())
        self.save("after/clock.png", with_box(base(), [100, 50, 159, 99]))
        rules = self.dir / "ignore.json"
        rules.write_text(json.dumps({"clock.png": [[100, 50, 60, 50]]}), encoding="utf-8")
        argv = [str(self.dir / "before"), str(self.dir / "after"), "--no-image", "--ignore-file", str(rules)]
        self.assertEqual(self.main(argv), 0)

    def test_mixing_file_and_folder_is_a_usage_error(self):
        a = self.save("a.png", base())
        self.assertEqual(self.main([str(a), str(self.dir)]), 2)

    def test_size_mismatch_exit_one(self):
        a = self.save("a.png", base())
        b = self.save("b.png", Image.new("RGB", (50, 50)))
        out = self.dir / "size.png"
        self.assertEqual(self.main([str(a), str(b), "--out", str(out)]), 1)
        self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
