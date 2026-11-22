"""tools/ci_shard.py: the CI Luau list is split into shards without losing or repeating a line, and the pull-request gate only
skips the Luau shards when nothing they use changed (BD-1302)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ci_shard as cs  # noqa: E402


class ShardTests(unittest.TestCase):
    def test_block_is_found_and_has_the_checks(self):
        lines = cs.check_lines()
        self.assertGreater(len(lines), 150)
        self.assertTrue(all(not l.startswith("#") for l in lines))
        self.assertIn("python tools/verify_sources.py --compiler /tmp/luau/luau-compile", lines)

    def test_four_shards_cover_every_line_once(self):
        lines = cs.check_lines()
        got = [l for k in range(1, 5) for l in cs.shard(lines, k, 4)]
        self.assertEqual(sorted(got), sorted(lines))
        sizes = [len(cs.shard(lines, k, 4)) for k in range(1, 5)]
        self.assertLessEqual(max(sizes) - min(sizes), 1)

    def test_bad_shard_is_refused(self):
        with self.assertRaises(SystemExit):
            cs.shard(["a"], 5, 4)

    def test_block_parsing_stops_at_the_next_key(self):
        text = "x:\n  CI_LUAU_CHECKS: |\n    python a.py\n    # note\n\n    python b.py\n  run: python c.py\n"
        self.assertEqual(cs.check_lines(text), ["python a.py", "python b.py"])

    def test_the_workflow_runs_the_shards_and_keeps_the_required_check(self):
        wf = cs.WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python tools/ci_shard.py --shard", wf)
        self.assertIn("shard: [1, 2, 3, 4]", wf)
        self.assertIn("\n  build:\n", wf, "the ruleset requires a check named build")


class GateTests(unittest.TestCase):
    def test_game_input_needs_luau(self):
        for path in ("src/shared/Config.luau", "resources/ui/x.png", "default.project.json", ".github/workflows/x.yml"):
            self.assertTrue(cs.needs_luau([path])[0], path)

    def test_files_the_list_uses_need_luau(self):
        self.assertTrue(cs.needs_luau(["tools/build.py"])[0])
        self.assertTrue(cs.needs_luau(["tools/release_playtest.py"])[0])
        self.assertTrue(cs.needs_luau(["docs/catalog/Home.md"])[0], "verify_catalog reads docs/catalog")

    def test_unrelated_changes_skip_luau(self):
        needed, why = cs.needs_luau(["CLAUDE.md", "docs/kanban/rows/BD-9999.md", "tests/test_ci_shard.py"])
        self.assertFalse(needed, why)

    def test_no_file_list_runs_everything(self):
        self.assertTrue(cs.needs_luau([])[0])


if __name__ == "__main__":
    unittest.main()
