"""tools/menu_spec_check.py: the proposal checked against itself passes; a moved element, wrong words and a wrong font fail."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import menu_spec_check as msc  # noqa: E402

SPEC = ROOT / "docs" / "menu-specs" / "potion-shop" / "spec.json"


def geom_from_proposal(move=None, words=None):
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    elems = msc.expand(spec)
    out = {"viewport": [1544, 720], "inset": [0, 0], "ignoreInset": True, "elements": {}}
    texts = {"title": "Potions", "timer": "New in 1:42", "card1.name": "Swift", "card1.rarity": "Common", "card1.badge": "x3"}
    for k in elems:
        x, y, w, h = msc.abs_box(elems, k, spec["proposal_window_px"])
        if move and k == move:
            x += 40
        e = {"rect": [x, y, w, h], "font": "FredokaOne"}
        if k in texts:
            e["text"] = texts[k]
        if k.endswith(".strip"):
            e["innerText"] = "Grow faster!"
        if k.endswith(".price"):
            e["innerText"] = "20"
        if k.startswith("rail."):
            e["innerText"] = k.split(".")[1].capitalize()
        if k.endswith(".name") and "text" not in e:
            e["text"] = "Hearty"
        if k.endswith(".rarity") and "text" not in e:
            e["text"] = "Uncommon"
        if k.endswith(".badge") and "text" not in e:
            e["text"] = "x2"
        out["elements"][k] = e
    if words:
        out["elements"][words[0]][words[1]] = words[2]
    return out


class MenuSpecCheck(unittest.TestCase):
    def run_check(self, geom):
        with tempfile.TemporaryDirectory() as d:
            gp = Path(d) / "geom.json"
            gp.write_text(json.dumps(geom), encoding="utf-8")
            code = msc.compare(SPEC, gp, ROOT / "docs" / "menu-specs" / "potion-shop" / "proposal.jpg", Path(d) / "out", None, False)
            report = json.loads((Path(d) / "out" / "report.json").read_text(encoding="utf-8"))
        return code, report["misses"]

    def test_self_test_passes(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(msc.compare(SPEC, None, None, Path(d), None, True), 0)

    def test_proposal_as_build_passes(self):
        code, misses = self.run_check(geom_from_proposal())
        self.assertEqual(misses, [])
        self.assertEqual(code, 0)

    def test_moved_element_fails(self):
        code, misses = self.run_check(geom_from_proposal(move="close"))
        self.assertEqual(code, 1)
        self.assertTrue(any(m.startswith("close: x") for m in misses), misses)

    def test_multiplier_words_fail(self):
        code, misses = self.run_check(geom_from_proposal(words=("card2.strip", "innerText", "x1.4 Growth")))
        self.assertTrue(any("card2.strip: words" in m for m in misses), misses)

    def test_two_word_name_fails(self):
        code, misses = self.run_check(geom_from_proposal(words=("card1.name", "text", "Swift Sip")))
        self.assertTrue(any("card1.name: words" in m for m in misses), misses)

    def test_wrong_font_fails(self):
        code, misses = self.run_check(geom_from_proposal(words=("title", "font", "GothamBold")))
        self.assertTrue(any("title: font" in m for m in misses), misses)


def notes_file(d, elements=None, pins=None):
    """A docs/feedback/menu-feedback.json as the Be Dino Desk writes it (BD-1301)."""
    p = Path(d) / "menu-feedback.json"
    p.write_text(json.dumps({"screens": {"potion-shop": {"elements": elements or {}, "pins": pins or []}}}), encoding="utf-8")
    return p


def note(tags, text, severity="must", status="open", should=""):
    return {"tags": tags, "note": text, "severity": severity, "should": should, "at": "2026-11-23T10:00:00",
            "check": "2026-11-23T09:00:00", "status": status}


class OwnerNotes(unittest.TestCase):
    """BD-1301: owner notes from the desk are listed per element; an open must-fix note never passes."""

    def run_check(self, fb, owner_flag=False):
        with tempfile.TemporaryDirectory() as d:
            gp = Path(d) / "geom.json"
            gp.write_text(json.dumps(geom_from_proposal()), encoding="utf-8")
            code = msc.compare(SPEC, gp, ROOT / "docs" / "menu-specs" / "potion-shop" / "proposal.jpg", Path(d) / "out", None, False,
                               feedback=fb, owner_flag=owner_flag)
            report = json.loads((Path(d) / "out" / "report.json").read_text(encoding="utf-8"))
            page = (Path(d) / "out" / "report.html").read_text(encoding="utf-8")
        return code, report, page

    def test_must_fix_note_fails_a_passing_element(self):
        with tempfile.TemporaryDirectory() as d:
            fb = notes_file(d, {"title": [note(["Outline"], "outline too thin, like proposal", should="3 px dark")]})
            code, report, page = self.run_check(fb)
        self.assertEqual(code, 1)
        row = next(r for r in report["rows"] if r["id"] == "title")
        self.assertEqual(row["status"], "miss")
        self.assertEqual(row["owner"], ["owner (must fix): Outline - 'outline too thin, like proposal' (should be: 3 px dark)"])
        self.assertIn("title: owner (must fix): Outline - 'outline too thin, like proposal' (should be: 3 px dark)", report["misses"])
        self.assertIn("outline too thin, like proposal", page)

    def test_nice_to_have_listed_but_only_counted_with_flag(self):
        with tempfile.TemporaryDirectory() as d:
            fb = notes_file(d, {"card2.price": [note(["Text size"], "a bit bigger", severity="nice")]},
                            pins=[dict(note(["Missing"], "a sparkle here", severity="nice"), x=40.0, y=12.5, side="proposal")])
            code, report, _ = self.run_check(fb)
            code_flag, report_flag, _ = self.run_check(fb, owner_flag=True)
        self.assertEqual(code, 0)
        self.assertEqual(report["misses"], [])
        row = next(r for r in report["rows"] if r["id"] == "card2.price")
        self.assertEqual(row["status"], "pass")
        self.assertEqual(row["owner"], ["owner (nice to have): Text size - 'a bit bigger'"])
        self.assertEqual(len(report["owner_pins"]), 1)
        self.assertEqual(code_flag, 1)
        self.assertIn("card2.price: owner (nice to have): Text size - 'a bit bigger'", report_flag["misses"])
        self.assertTrue(any(m.startswith("pin 1 (proposal 40 %, 12 % of window): owner (nice to have): Missing") for m in report_flag["misses"]),
                        report_flag["misses"])

    def test_done_notes_and_other_screens_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "menu-feedback.json"
            p.write_text(json.dumps({"screens": {
                "potion-shop": {"elements": {"close": [note(["Colour"], "fixed already", status="done")]}, "pins": []},
                "dino-index": {"elements": {"close": [note(["Colour"], "other screen")]}, "pins": []}}}), encoding="utf-8")
            code, report, _ = self.run_check(p)
        self.assertEqual(code, 0)
        self.assertFalse(any(r.get("owner") for r in report["rows"]))

    def test_missing_or_broken_file_means_no_notes(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "menu-feedback.json"
            bad.write_text("{not json", encoding="utf-8")
            self.assertEqual(msc.load_owner_notes(bad, "potion-shop"), ({}, []))
            self.assertEqual(msc.load_owner_notes(Path(d) / "none.json", "potion-shop"), ({}, []))

    def test_report_has_what_the_desk_draws(self):
        code, report, _ = self.run_check(None)
        self.assertEqual(report["screen"], "potion-shop")
        self.assertEqual(report["proposal"], "docs/menu-specs/potion-shop/proposal.jpg")
        self.assertEqual(report["shot"], "docs/menu-specs/potion-shop/proposal.jpg")
        self.assertTrue(report["at"].startswith("20"))
        win = next(r for r in report["rows"] if r["id"] == "window")
        self.assertEqual(win["status"], "pass")
        for a, b in zip(win["pct_ref"], win["pct_game"]):
            self.assertAlmostEqual(a, b, places=3)


if __name__ == "__main__":
    unittest.main()
