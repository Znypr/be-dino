"""BD-647: tools/reference_sheet.py builds a labelled contact sheet and references.md from generated images (docs/167)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import reference_sheet as rs  # noqa: E402


def make_image(path, size=(120, 80), colour=(200, 120, 60), mode="RGB"):
    Image.new(mode, size, colour if mode == "RGB" else colour + (128,)).save(path)


def entry(name, **extra):
    base = {"file": name, "kind": "photo", "title": f"Title {name}", "source_url": "https://commons.wikimedia.org/wiki/File:X.jpg",
            "license": "CC BY-SA 4.0, Jane Doe", "date_read": "2026-10-18", "copy": "crest swept back"}
    base.update(extra)
    return base


class Case(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.folder = Path(self._tmp.name) / "cockatoo"
        self.folder.mkdir()

    def write(self, entries, wrap=True):
        data = {"creature": "cockatoo", "images": entries} if wrap else entries
        (self.folder / "sources.json").write_text(json.dumps(data), encoding="utf-8")


class BuildTests(Case):
    def test_builds_sheet_and_markdown(self):
        make_image(self.folder / "a.png", (400, 200))
        make_image(self.folder / "b.png", (100, 300), mode="RGBA")
        make_image(self.folder / "c.webp", (64, 64))
        self.write([entry("a.png"), entry("b.png", kind="cartoon", license="CC0"), entry("c.webp", kind="3d", copy="")])
        code, messages = rs.run(self.folder, date="2026-10-18")
        self.assertEqual(code, 0, messages)
        sheet = Image.open(self.folder / "contact-sheet.png")
        self.assertEqual(sheet.size[0], 3 * (320 + 10) + 10)  # 3 columns for 3 pictures
        self.assertGreater(sheet.size[1], 320)
        md = (self.folder / "references.md").read_text(encoding="utf-8")
        self.assertIn("# References: cockatoo", md)
        self.assertIn("REFERENCE ONLY", md)
        self.assertIn("AGENTS.md art rule", md)
        self.assertIn("Source: https://commons.wikimedia.org/wiki/File:X.jpg", md)
        self.assertIn("Date read: 2026-10-18", md)
        self.assertIn("What to copy: crest swept back", md)
        self.assertIn("What to copy: not written yet", md)
        self.assertTrue(any("no \"copy\" note" in m for m in messages))

    def test_sheet_has_labels_not_blank(self):
        make_image(self.folder / "a.png", (50, 50), (255, 255, 255))
        self.write([entry("a.png")])
        rs.run(self.folder)
        sheet = Image.open(self.folder / "contact-sheet.png").convert("RGB")
        colours = sheet.getcolors(maxcolors=100000)
        self.assertGreater(len(colours), 6)  # caption text and the red footer, not one flat fill

    def test_bare_list_and_owner_picture_need_no_url(self):
        make_image(self.folder / "o.png")
        self.write([{"file": "o.png", "kind": "owner", "license": "owner's own picture", "copy": "pose"}], wrap=False)
        code, messages = rs.run(self.folder, name="Cockatoosaurus")
        self.assertEqual(code, 0, messages)
        self.assertIn("# References: Cockatoosaurus", (self.folder / "references.md").read_text(encoding="utf-8"))
        self.assertIn("the owner's own picture", (self.folder / "references.md").read_text(encoding="utf-8"))

    def test_restricted_licence_gets_a_warning_line(self):
        make_image(self.folder / "a.png")
        make_image(self.folder / "b.png")
        self.write([entry("a.png", license="All rights reserved, Some Studio"), entry("b.png", license="CC0")])
        rs.run(self.folder)
        md = (self.folder / "references.md").read_text(encoding="utf-8")
        self.assertEqual(md.count("Licence warning"), 1)

    def test_licence_class(self):
        self.assertEqual(rs.licence_class("CC BY 4.0"), "free")
        self.assertEqual(rs.licence_class("Public domain (copyright expired)"), "free")
        self.assertEqual(rs.licence_class("Copyright 2020 Studio"), "restricted")
        self.assertEqual(rs.licence_class("unknown"), "restricted")
        self.assertEqual(rs.licence_class("some blog"), "check")

    def test_check_writes_nothing(self):
        make_image(self.folder / "a.png")
        self.write([entry("a.png")])
        code, _ = rs.run(self.folder, check=True)
        self.assertEqual(code, 0)
        self.assertFalse((self.folder / "contact-sheet.png").exists())
        self.assertFalse((self.folder / "references.md").exists())


class ValidationTests(Case):
    def test_missing_sources_json(self):
        code, messages = rs.run(self.folder)
        self.assertEqual(code, 1)
        self.assertIn("sources.json is missing", messages[0])

    def test_broken_json(self):
        (self.folder / "sources.json").write_text("{nope", encoding="utf-8")
        self.assertEqual(rs.run(self.folder)[0], 1)

    def test_missing_file_url_and_licence_are_errors(self):
        make_image(self.folder / "a.png")
        self.write([entry("a.png", source_url="not a url"), entry("gone.png"), entry("a.png", license=" ")])
        code, messages = rs.run(self.folder)
        text = "\n".join(messages)
        self.assertEqual(code, 1)
        self.assertIn("source_url must be the real web address", text)
        self.assertIn("file not found", text)
        self.assertIn("license is empty", text)
        self.assertIn("listed twice", text)
        self.assertFalse((self.folder / "contact-sheet.png").exists())

    def test_too_many_images(self):
        names = []
        for i in range(9):
            make_image(self.folder / f"{i}.png", (10, 10))
            names.append(entry(f"{i}.png"))
        self.write(names)
        code, messages = rs.run(self.folder)
        self.assertEqual(code, 1)
        self.assertIn("at most 8", "\n".join(messages))
        self.assertEqual(rs.run(self.folder, max_images=9)[0], 0)

    def test_bad_kind_and_date(self):
        make_image(self.folder / "a.png")
        self.write([entry("a.png", kind="painting", date_read="yesterday")])
        text = "\n".join(rs.run(self.folder)[1])
        self.assertIn("kind must be one of", text)
        self.assertIn("date_read must look like", text)

    def test_unlisted_image_is_a_warning_and_left_out(self):
        make_image(self.folder / "a.png")
        make_image(self.folder / "extra.png")
        self.write([entry("a.png")])
        code, messages = rs.run(self.folder)
        self.assertEqual(code, 0)
        self.assertTrue(any("extra.png is in the folder but not in sources.json" in m for m in messages))
        self.assertNotIn("extra.png", (self.folder / "references.md").read_text(encoding="utf-8"))

    def test_path_traversal_is_refused(self):
        self.write([entry("../secret.png")])
        code, messages = rs.run(self.folder)
        self.assertEqual(code, 1)
        self.assertIn("directly in the folder", "\n".join(messages))

    def test_not_a_folder(self):
        self.assertEqual(rs.run(self.folder / "nothing")[0], 1)

    def test_main_returns_exit_code(self):
        make_image(self.folder / "a.png")
        self.write([entry("a.png")])
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rs.main([str(self.folder), "--check"]), 0)
            self.assertEqual(rs.main([str(self.folder / "x")]), 1)


if __name__ == "__main__":
    unittest.main()
