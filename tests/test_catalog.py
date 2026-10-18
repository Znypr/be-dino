"""BD-1052 (docs/188): the team catalogue is generated from the code and keeps its shape.

Numbers are re-read here with plain regular expressions from the Luau source files (not through the Luau dump the tool uses), so a page
that shows a number different from the code fails. Needs the pinned Luau runner (LUAU_RUNNER); skipped without one.
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_catalog  # noqa: E402
import catalog_core as core  # noqa: E402
import verify_catalog  # noqa: E402


def runner():
    try:
        return core.find_runner()
    except SystemExit:
        return None


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


@unittest.skipUnless(runner(), "no Luau runner (set LUAU_RUNNER)")
class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build_catalog.build(ROOT, runner(), public=False)
        cls.gaps = build_catalog.build.last_gaps
        cls.public = build_catalog.build(ROOT, runner(), public=True)

    # -- shape (owner answer 3: six pages, hard cap eight, never a page for one item)
    def test_page_count_is_within_the_cap(self):
        self.assertLessEqual(len(self.pages), 8)
        self.assertEqual(sorted(self.pages), sorted(f"{n}.md" for n in build_catalog.PAGE_ORDER))
        self.assertLessEqual(len(build_catalog.PAGE_ORDER), build_catalog.MAX_PAGES)

    def test_no_page_is_for_a_single_item(self):
        for name, text in self.pages.items():
            sections = re.findall(r'^## ', text, re.M)
            self.assertGreaterEqual(len(sections), 3, f"{name} has too few sections to be a category page")
            self.assertGreaterEqual(len(re.findall(r'<a id="', text)), 5, f"{name} has too few item anchors")

    def test_every_page_has_a_contents_list(self):
        for name, text in self.pages.items():
            self.assertIn("## Contents", text, name)
            contents = text.split("## Contents", 1)[1].split("<a id=", 1)[0]
            self.assertGreaterEqual(len(re.findall(r"\]\(#", contents)), 3, f"{name}: contents list has no anchor links")

    def test_headings_have_no_internal_ids(self):
        for name, text in self.pages.items():
            for heading in re.findall(r"^#{1,6} (.+)$", text, re.M):
                self.assertNotRegex(heading, r"_|rbxassetid|^\d", f"{name}: heading looks like an id: {heading!r}")

    def test_all_links_land_on_an_anchor(self):
        anchors = {n: set(re.findall(r'<a id="([^"]+)"></a>', t)) for n, t in self.pages.items()}
        for name, text in self.pages.items():
            for target in re.findall(r"\]\(#([^)]+)\)", text):
                self.assertIn(target, anchors[name], f"{name}: link to #{target} has no anchor")
            for other, target in re.findall(r"\]\(([A-Za-z-]+\.md)#([^)]+)\)", text):
                self.assertIn(other, anchors, f"{name}: link to unknown page {other}")
                self.assertIn(target, anchors[other], f"{name}: link to {other}#{target} has no anchor")

    def test_every_item_section_has_an_id_line(self):
        for name, text in self.pages.items():
            for block in re.split(r'<a id="[^"]+"></a>\n### ', text)[1:]:
                self.assertRegex(block, r"id: `[^`]+`|<a id=|\n- ", f"{name}: item section without details")

    # -- numbers equal the code
    def test_species_odds_equal_the_code(self):
        config = read("src/shared/Config.luau")
        rows = re.findall(r'\{speciesId = "(\w+)", weight = ([\d.]+)\}', config)
        self.assertEqual(len(rows), 22)
        total = sum(float(w) for _, w in rows)
        names = dict(re.findall(r'^\s{8}(\w+) = "([^"]+)",$', config.split("SpeciesDisplayNames = {", 1)[1].split("}", 1)[0], re.M))
        text = self.pages["Dinosaurs.md"]
        for species, weight in rows:
            expected = core.pct(100 * float(weight) / total)
            section = text.split(f'<a id="dino-{species}"></a>', 1)[1].split('<a id="', 1)[0]
            self.assertIn(f"**Chance per egg:** {expected} from a shop egg", section, species)
            self.assertIn(f"| [{names[species]}](#dino-{species}) |", text)

    def test_colour_weights_equal_the_code(self):
        prog = read("src/shared/ProgressionConfig.luau")
        scale = int(re.search(r"EggColorWeightScale=(\d+)", prog).group(1))
        rows = re.findall(r'\{id="(\w+)",name="([^"]+)",rarity="(\w+)",weight=(\d+),rgb=\{(\d+),(\d+),(\d+)\}\}', prog)
        self.assertGreaterEqual(len(rows), 9)
        text = self.pages["Eggs-and-looks.md"]
        for cid, name, rarity, weight, r, g, b in rows:
            section = text.split(f'<a id="colour-{cid}"></a>', 1)[1].split('<a id="', 1)[0]
            self.assertIn(f"**Chance for one slot:** {core.pct(100 * int(weight) / scale)}", section, cid)
            self.assertIn(f"**Rarity:** {rarity}", section, cid)
            self.assertIn("#%02X%02X%02X" % (int(r), int(g), int(b)), section, cid)

    def test_potion_prices_equal_the_code(self):
        prog = read("src/shared/ProgressionConfig.luau")
        rows = re.findall(r'\{id="(\w+)",name="([^"]+)",kind="\w+",rarity="(\w+)",duration=(\d+),multiplier=([\d.]+),price=(\d+)\}', prog)
        self.assertEqual(len(rows), 12)
        text = self.pages["Shop-items.md"]
        for pid, name, rarity, duration, mult, price in rows:
            section = text.split(f'<a id="potion-{core.kebab(pid)}"></a>', 1)[1].split('<a id="', 1)[0]
            self.assertIn(f"**Price:** {core.num(int(price))} crystals", section, pid)
            self.assertIn(f"### {name}", section, pid)
            self.assertIn(f"**Power:** {core.plus(float(mult))}", section, pid)

    def test_condition_tier_zero_equals_the_code(self):
        prog = read("src/shared/ProgressionConfig.luau")
        first = [int(x) for x in re.search(r"ConditionWeights=\{\s*\{([\d, ]+)\}", prog).group(1).split(",")]
        total = sum(first)
        text = self.pages["Eggs-and-looks.md"]
        row = [l for l in text.splitlines() if l.startswith("| 0 |")][0]
        cells = [c.strip() for c in row.strip("|").split("|")]
        for weight, cell in zip(first, cells[1:6]):
            self.assertEqual(cell, core.pct(100 * weight / total))

    def test_fusion_inputs_equal_the_code(self):
        source = read("src/server/IdentityFusion.luau")
        counts = dict(re.findall(r'(\w+) = \{targetStage = "\w+", sourceStage = "\w+", donorCount = (\d+)', source))
        text = self.pages["Mutations-and-fusion.md"]
        for stage, n in counts.items():
            self.assertRegex(text, rf"\| \[{stage.capitalize()}\]\(#fusion-{stage}\) \| {n} x ", stage)

    # -- gaps
    def test_every_gap_names_a_folder_or_file(self):
        self.assertTrue(self.gaps.rows)
        home = self.pages["Home.md"]
        for gap in self.gaps.rows:
            self.assertTrue(gap.file, f"gap without a file name: {gap}")
            self.assertTrue(gap.folder or gap.kind in ("not in code",), f"gap without a folder: {gap}")
            self.assertIn(f"`{gap.file}`", home, f"gap not listed on the Home page: {gap}")

    def test_wind_is_listed_as_not_data_driven(self):
        self.assertIn("Not data-driven yet", self.pages["World-and-food.md"])
        self.assertTrue(any(g.category == "Wind" for g in self.gaps.rows))

    def test_status_tables_exist_for_every_category(self):
        for name in ("Dinosaurs.md", "Eggs-and-looks.md", "Mutations-and-fusion.md", "Shop-items.md", "World-and-food.md"):
            self.assertIn("**STATUS**", self.pages[name], name)

    # -- markers and the public switch
    def test_secret_and_provisional_are_marked(self):
        text = self.pages["Dinosaurs.md"]
        self.assertIn("SECRET, internal only", text)
        self.assertIn("PROVISIONAL", text)

    def test_public_copy_drops_secrets_flags_and_provisional_odds(self):
        joined = "\n".join(self.public.values())
        for word in ("Chickosaurus", "Eaglesaurus", "SECRET", "PROVISIONAL", "Golden Drumstick", "Statues in the cave hub"):
            self.assertNotIn(word, joined, word)
        self.assertNotIn("<a id=\"fusion\">", joined)
        self.assertIn(build_catalog.HIDDEN, joined)
        self.assertNotIn("## Missing", self.public["Home.md"])
        self.assertLessEqual(len(self.public), 8)

    def test_provisional_markers_still_exist_in_the_source(self):
        for key, (path, marker) in build_catalog.PROVISIONAL.items():
            text = read(path)
            self.assertIn(marker, text, f"{key}: marker moved in {path}")
            at = text.index(marker)
            window = text[max(0, at - 300): at + len(marker) + 300]
            self.assertRegex(window, r"(?i)provisional", f"{key}: no PROVISIONAL near the marker in {path}")

    # -- verify tool
    def test_verify_reports_stale_missing_and_extra_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name, text in self.pages.items():
                (folder / name).write_text(text, encoding="utf-8", newline="\n")
            self.assertEqual(verify_catalog.problems(ROOT, runner(), folder), [])
            (folder / "Home.md").write_text(self.pages["Home.md"].replace("Missing", "Mising", 1), encoding="utf-8")
            (folder / "Shop-items.md").unlink()
            (folder / "Compy.md").write_text("# one item\n", encoding="utf-8")
            errors = "\n".join(verify_catalog.problems(ROOT, runner(), folder))
            self.assertIn("Home.md is out of date", errors)
            self.assertIn("Shop-items.md is missing", errors)
            self.assertIn("Compy.md is not produced", errors)
            self.assertIn("python tools/build_catalog.py", errors)

    def test_the_committed_catalogue_is_wired_in(self):
        workflow = read(".github/workflows/build-generated-place.yml")
        self.assertIn("python tools/verify_catalog.py", workflow)
        self.assertIn("docs/catalog/Home.md", read("docs/160-agent-brief.md"))
        self.assertIn("tools/build_catalog.py", read("docs/160-agent-brief.md"))
        self.assertIn("docs/catalog/Home.md", read("AGENTS.md"))


class FormatTests(unittest.TestCase):
    def test_numbers_are_plain(self):
        self.assertEqual(core.pct(26), "26%")
        self.assertEqual(core.pct(0.0366), "0.0366%")
        self.assertEqual(core.num(1200), "1,200")
        self.assertEqual(core.plus(1.2), "+20%")
        self.assertEqual(core.one_in(0.04), "1 in 2,500")
        self.assertNotIn("e", core.pct(0.00001))


if __name__ == "__main__":
    unittest.main()
