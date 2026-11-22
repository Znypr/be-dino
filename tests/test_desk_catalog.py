"""BD-1292 (docs/247): tools/desk_catalog.py lists repo pictures by tab and group, with repo-relative ids."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import desk_catalog  # noqa: E402

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


class DeskCatalogTest(unittest.TestCase):
    def run_catalog(self, root):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(desk_catalog.main(["--root", str(root)]), 0)
        return json.loads(buf.getvalue())

    def test_lists_pictures_with_relative_ids(self):
        old = desk_catalog.ROOT
        try:
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / "resources/ui/v2/icons").mkdir(parents=True)
                (root / "resources/ui/v2/icons/star.png").write_bytes(PNG)
                (root / "resources/ui/v2/icons/notes.txt").write_text("not a picture")
                (root / "docs/evidence/2026-11-20-vegetation-v9").mkdir(parents=True)
                (root / "docs/evidence/2026-11-20-vegetation-v9/oak.jpg").write_bytes(PNG)
                cat = self.run_catalog(root)
        finally:
            desk_catalog.ROOT = old
        tabs = {t["name"]: t for t in cat["tabs"]}
        icons = next(g for g in tabs["UI kit"]["groups"] if g["name"] == "Icons")
        self.assertEqual([i["id"] for i in icons["items"]], ["resources/ui/v2/icons/star.png"])
        veg = next(g for g in tabs["World"]["groups"] if g["name"] == "Vegetation (screenshots)")
        self.assertEqual(veg["items"][0]["src"], "docs/evidence/2026-11-20-vegetation-v9/oak.jpg")
        self.assertIn("Text and buttons", tabs)
        for t in cat["tabs"]:
            for g in t["groups"]:
                for it in g["items"]:
                    self.assertFalse(it["id"].startswith("/") or ":" in it["id"], it["id"])
        self.assertEqual(cat["menus"], [])

    def test_menus_newest_check_per_screen(self):
        """BD-1301: one entry per docs/menu-specs/<screen>; the newest report.json from build/menu-check or docs/evidence."""
        old = desk_catalog.ROOT
        try:
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                spec_dir = root / "docs/menu-specs/potion-shop"
                spec_dir.mkdir(parents=True)
                (spec_dir / "proposal.png").write_bytes(PNG)   # 1 x 1 px
                spec = {"screen": "potion-shop", "proposal": "docs/menu-specs/potion-shop/proposal.png",
                        "proposal_window_px": [0, 0, 1, 1], "steps": [{"name": "1 window", "elements": ["window"]}],
                        "elements": {"window": {"box": [0, 0, 100, 100]}, "card1": {"box": [10, 20, 30, 40]},
                                     "card*.name": {"box": [0, 0, 50, 50], "kind": "text", "parent": "card"}}}
                (spec_dir / "spec.json").write_text(json.dumps(spec))
                old_check = root / "build/menu-check/potion-shop"
                old_check.mkdir(parents=True)
                (old_check / "report.json").write_text(json.dumps({"screen": "potion-shop", "at": "2001-01-01T08:00:00",
                                                                   "misses": [], "rows": [{"id": "window"}]}))
                step = root / "docs/evidence/2026-11-23-potion-steps/step2"
                step.mkdir(parents=True)
                (step / "capture.png").write_bytes(PNG)
                (step / "geom.json").write_text(json.dumps({"viewport": [100, 50], "elements": {"window": {"rect": [10, 5, 50, 25]}}}))
                # an older report (no at / shot / pct fields): date from the file, capture and boxes from the folder
                (step / "report.json").write_text(json.dumps({"misses": ["window: x 0.0 -> 2.0 %", "card1: MISSING in the build (no SpecId)"],
                                                              "rows": [{"id": "window"}, {"id": "card1", "missing": True}]}))
                (root / "docs/evidence/2026-11-23-hud/report.json").parent.mkdir(parents=True)
                (root / "docs/evidence/2026-11-23-hud/report.json").write_text(json.dumps({"misses": ["x"], "rows": []}))
                cat = self.run_catalog(root)
        finally:
            desk_catalog.ROOT = old
        self.assertEqual(len(cat["menus"]), 1)
        m = cat["menus"][0]
        self.assertEqual(m["screen"], "potion-shop")
        self.assertEqual(m["proposal_size"], [1, 1])
        self.assertEqual([e["id"] for e in m["elements"]], ["window", "card1", "card1.name"])
        self.assertEqual(next(e for e in m["elements"] if e["id"] == "card1.name")["pct"], [10.0, 20.0, 15.0, 20.0])
        last = m["latest"]
        self.assertEqual(last["report"], "docs/evidence/2026-11-23-potion-steps/step2/report.json")   # file date (now) beats 2001
        self.assertEqual(last["shot"], "docs/evidence/2026-11-23-potion-steps/step2/capture.png")
        rows = {r["id"]: r for r in last["rows"]}
        self.assertEqual(rows["window"]["status"], "miss")
        self.assertEqual(rows["window"]["pct_game"], [10.0, 10.0, 50.0, 50.0])
        self.assertEqual(rows["window"]["pct_ref"], [0.0, 0.0, 100.0, 100.0])
        self.assertEqual(rows["card1"]["status"], "missing")
        self.assertEqual(len(m["history"]), 2)

    def test_image_size_reads_png_and_jpeg(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.png"
            p.write_bytes(PNG)
            self.assertEqual(desk_catalog.image_size(p), [1, 1])
            jpg = Path(__file__).resolve().parent.parent / "docs/menu-specs/potion-shop/proposal.jpg"
            if jpg.is_file():
                self.assertEqual(desk_catalog.image_size(jpg), [1544, 720])


if __name__ == "__main__":
    unittest.main()
