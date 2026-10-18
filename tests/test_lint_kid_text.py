"""tools/lint_kid_text.py on small Luau snippets and a throwaway tree (BD-655, docs/162)."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import lint_kid_text as lk  # noqa: E402


def rules(src, rel="src/client/Example.luau"):
    return sorted({v.rule for v in lk.lint_source(src + "\n", rel)})


class Scanner(unittest.TestCase):
    def test_finds_strings_and_skips_comments(self):
        src = '-- "not me"\nlocal a = "one" --[[ "two" ]] local b = \'three\'\nlocal c = [[four]]\nlocal d = `five {x}`\n'
        lits, masked = lk.scan(src)
        self.assertEqual([l.value for l in lits], ["one", "three", "four", "five %s"])
        self.assertEqual([l.line for l in lits], [2, 2, 3, 4])
        self.assertNotIn("not me", masked)

    def test_escapes(self):
        lits, _ = lk.scan('x = "a\\"b\\n\\u{41}"\n')
        self.assertEqual(lits[0].value, 'a"b\nA')


class Rules(unittest.TestCase):
    def test_time_noise(self):
        self.assertEqual(rules('lbl.Text = "5m 0s left"'), ["TIME_NOISE"])
        self.assertEqual(rules('lbl.Text = string.format("%dh %dm", h, m)'), ["TIME_NOISE"])
        self.assertEqual(rules('lbl.Text = "5 min left"'), [])
        self.assertEqual(rules('notify("Back in 40 s")'), [])

    def test_multiplier_and_decimal(self):
        self.assertIn("MULTIPLIER", rules('lbl.Text = "Speed 1.25x"'))
        self.assertIn("MULTIPLIER", rules('lbl.Text = "Growth x2"'))
        self.assertIn("DECIMAL", rules('lbl.Text = string.format("Score %.1f", s)'))
        self.assertEqual(rules('lbl.Text = "Speed +25%"'), [])
        self.assertEqual(rules('lbl.Text = "Level 3 of 10"'), [])

    def test_raw_ids(self):
        self.assertIn("RAW_ID", rules('notify("Failed: profile_not_loaded")'))
        self.assertIn("RAW_ID", rules('lbl.Text = "See BD-123 now"'))
        self.assertIn("RAW_ID", rules('lbl.Text = "Asset rbxassetid://123"'))

    def test_shouting(self):
        self.assertIn("SHOUTING", rules('lbl.Text = "EAT ALL THE FOOD NOW"'))
        self.assertIn("SHOUTING", rules('lbl.Text = "Wow!!!"'))
        for ok in ("HOME", "GO HOME", "OK", "XP"):
            self.assertEqual(rules(f'lbl.Text = "{ok}"'), [], ok)

    def test_jargon(self):
        self.assertIn("JARGON", rules('notify("Your profile is loading")'))
        self.assertIn("JARGON", rules('notify("Cooldown active")'))
        self.assertEqual(rules('notify("Your dinos are loading")'), [])

    def test_tech_punctuation(self):
        self.assertIn("TECH_PUNCT", rules('lbl.Text = "Open {shop}"'))
        self.assertIn("TECH_PUNCT", rules('lbl.Text = "Go -> shop"'))
        self.assertEqual(rules('lbl.Text = "Shop & Index (new!)"'), [])
        self.assertEqual(rules('lbl.Text = "<b>Big</b> win"'), [])

    def test_length_limits_come_from_one_table(self):
        w, c, s = lk.LIMITS["title"][1], lk.LIMITS["title"][0], lk.LIMITS["title"][2]
        ok = " ".join(["Aa"] * w)
        self.assertLessEqual(len(ok), c)
        self.assertEqual(rules('local t = {title = "%s"}' % ok), [])
        too_many = " ".join(["Aa"] * (w + 1))
        self.assertEqual(rules('local t = {title = "%s"}' % too_many), ["LONG_TEXT"])
        # same long text is fine in a body slot
        body_ok = "Eat food to grow. Jump over hills!"
        self.assertEqual(rules('local t = {body = "%s"}' % body_ok), [])
        three = "One two. Three four. Five six."
        self.assertEqual(rules('notify("%s")' % three), ["LONG_TEXT"])
        self.assertGreaterEqual(s, 1)

    def test_format_codes_count_as_short(self):
        self.assertEqual(rules('lbl.Text = string.format("%d of %d", a, b)'), [])


class WhatIsVisible(unittest.TestCase):
    def test_code_strings_are_ignored(self):
        self.assertEqual(rules('local inst = Instance.new("TextLabel")\ninst.Name = "My profile server"\nif kind == "profile server" then end'), [])
        self.assertEqual(rules('warn("profile server failed")\nprint("cooldown 5m 0s")\nerror("RNG probability")'), [])
        self.assertEqual(rules('x:GetAttribute("profile server")\nremote:FireServer("cooldown timeout")'), [])

    def test_sinks_are_checked(self):
        self.assertTrue(rules('lbl.Text = "Server cooldown"'))
        self.assertTrue(rules('notify("Server cooldown")'))
        self.assertTrue(rules('makeButton(parent, "Server cooldown")'))
        self.assertTrue(rules('local t = {label = "Server cooldown"}'))
        self.assertTrue(rules('lbl.Text = cond and "Server cooldown" or "Fine"'))
        self.assertTrue(rules('a.Text, b.Size = "Server cooldown", 3'))
        self.assertTrue(rules('local function f()\n    return "Server cooldown here"\nend'))

    def test_copy_files_check_every_sentence(self):
        self.assertTrue(rules('Copy.x = "Wait for the server cooldown"', "src/shared/FooCopy.luau"))
        self.assertEqual(rules('local k = "profile server thing"', "src/client/Plain.luau"), [])

    def test_inline_marker_skips_a_line(self):
        self.assertEqual(rules('lbl.Text = "Server cooldown" -- kidtext-ok: shown to admins only'), [])

    def test_excluded_files_are_not_scanned(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src" / "client").mkdir(parents=True)
            (root / "src" / "client" / "AdminPanel.client.luau").write_text('x.Text = "Server cooldown"\n', encoding="utf-8")
            old = lk.ROOT
            lk.ROOT = root
            try:
                found, n, _ = lk.run_lint(["src/client"], [])
            finally:
                lk.ROOT = old
            self.assertEqual((found, n), ([], 0))


class AllowlistAndBaseline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src" / "client").mkdir(parents=True)
        self.old = lk.ROOT
        lk.ROOT = self.root

    def tearDown(self):
        lk.ROOT = self.old
        self.tmp.cleanup()

    def write(self, name, text):
        (self.root / "src" / "client" / name).write_text(text, encoding="utf-8")

    def cli(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lk.main(list(args))
        return code, buf.getvalue()

    def test_allowlist_needs_a_reason_and_matches_text(self):
        allow = self.root / "allow.json"
        allow.write_text(json.dumps({"entries": [{"file": "src/client/A.luau", "rule": "JARGON"}]}), encoding="utf-8")
        with self.assertRaises(SystemExit):
            lk.load_allow(allow)
        allow.write_text(json.dumps({"entries": [{"file": "src/client/*.luau", "rule": "JARGON", "text": "Server cooldown",
                                                  "reason": "test"}]}), encoding="utf-8")
        entries = lk.load_allow(allow)
        self.write("A.luau", 'x.Text = "Server cooldown"\ny.Text = "Profile cooldown"\n')
        found, _, unused = lk.run_lint(["src/client"], entries)
        self.assertEqual([v.text for v in found], ["Profile cooldown"])
        self.assertEqual(unused, [])

    def test_baseline_only_new_problems_fail(self):
        self.write("A.luau", 'x.Text = "Server cooldown"\n')
        base = self.root / "base.json"
        allow = self.root / "none.json"
        args = ["--allow", str(allow)]
        code, _ = self.cli("src/client", "--write-baseline", str(base), *args)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(base.read_text(encoding="utf-8"))["total"], 1)   # JARGON only
        code, out = self.cli("src/client", "--baseline", str(base), *args)
        self.assertEqual(code, 0, out)
        # moving the line does not make it new
        self.write("A.luau", '\n\nx.Text = "Server cooldown"\n')
        self.assertEqual(self.cli("src/client", "--baseline", str(base), *args)[0], 0)
        # a second identical string IS new
        self.write("A.luau", 'x.Text = "Server cooldown"\ny.Text = "Server cooldown"\n')
        code, out = self.cli("src/client", "--baseline", str(base), *args)
        self.assertEqual(code, 1)
        self.assertIn("NEW", out)
        # a different bad string is new
        self.write("A.luau", 'x.Text = "Server cooldown"\ny.Text = "Speed 1.5x"\n')
        self.assertEqual(self.cli("src/client", "--baseline", str(base), *args)[0], 1)
        # fixing the old one is fine
        self.write("A.luau", 'x.Text = "Wait a bit"\n')
        code, out = self.cli("src/client", "--baseline", str(base), *args)
        self.assertEqual(code, 0)
        self.assertIn("fixed", out)

    def test_missing_baseline_is_an_error(self):
        self.write("A.luau", 'x.Text = "Fine"\n')
        self.assertEqual(self.cli("src/client", "--baseline", str(self.root / "nope.json"))[0], 2)

    def test_plain_mode_exit_codes(self):
        self.write("A.luau", 'x.Text = "Fine text"\n')
        self.assertEqual(self.cli("src/client", "--allow", str(self.root / "none.json"))[0], 0)
        self.write("A.luau", 'x.Text = "Speed 1.25x"\n')
        self.assertEqual(self.cli("src/client", "--allow", str(self.root / "none.json"))[0], 1)

    def test_report_lists_worst_files_and_exits_zero(self):
        self.write("A.luau", 'x.Text = "Speed 1.25x"\ny.Text = "Server cooldown"\n')
        self.write("B.luau", 'x.Text = "Speed 2x"\n')
        code, out = self.cli("src/client", "--report", "--top", "5", "--allow", str(self.root / "none.json"))
        self.assertEqual(code, 0)
        self.assertIn("Top 5 files", out)
        self.assertLess(out.index("src/client/A.luau"), out.index("src/client/B.luau"))
        code, md = self.cli("src/client", "--report", "--markdown", "--allow", str(self.root / "none.json"))
        self.assertIn("| 1 | `src/client/A.luau`", md)


class RealTree(unittest.TestCase):
    def test_selftest_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lk.selftest(), 0)

    def test_checked_in_files_are_valid(self):
        entries = lk.load_allow()
        self.assertTrue(all(e["reason"].strip() for e in entries))
        base = lk.load_baseline(lk.BASELINE_FILE)
        self.assertIsNotNone(base, "tools/lint_kid_text_baseline.json is missing")

    def test_real_tree_has_no_new_problems(self):
        found, n, _ = lk.run_lint(lk.DEFAULT_PATHS, lk.load_allow())
        self.assertGreater(n, 100)
        new = lk.new_violations(found, lk.load_baseline(lk.BASELINE_FILE))
        self.assertEqual([v.show() for v in new], [])


if __name__ == "__main__":
    unittest.main()
