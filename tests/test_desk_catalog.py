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
        veg = next(g for g in tabs["World"]["groups"] if g["name"] == "Vegetation")
        self.assertEqual(veg["items"][0]["src"], "docs/evidence/2026-11-20-vegetation-v9/oak.jpg")
        self.assertIn("Text and buttons", tabs)
        for t in cat["tabs"]:
            for g in t["groups"]:
                for it in g["items"]:
                    self.assertFalse(it["id"].startswith("/") or ":" in it["id"], it["id"])


if __name__ == "__main__":
    unittest.main()
