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


if __name__ == "__main__":
    unittest.main()
