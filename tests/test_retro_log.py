"""tools/retro_log.py (docs/168): validation, list, summary numbers, render, and the shipped log + page."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import retro_log as rl  # noqa: E402


def entry(**kw):
    e = dict(date="2026-10-18", task="Task", agent_kind="worker", pr=1, duration_min=10, tool_calls=5, tokens_k=100,
             quality_verdict="good", fact_check="checked", steps=["a"], problems=[], lesson="", action="none",
             action_ref="", rework_cycles=0, lost_min=None)
    e.update(kw)
    return e


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rl.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Validate(unittest.TestCase):
    def test_good_entry(self):
        self.assertEqual(rl.validate(entry()), [])

    def test_bad_values(self):
        self.assertTrue(rl.validate(entry(quality_verdict="great")))
        self.assertTrue(rl.validate(entry(date="18/10/2026")))
        self.assertTrue(rl.validate(entry(agent_kind="robot")))
        self.assertTrue(rl.validate(entry(duration_min=-1)))
        self.assertTrue(rl.validate(entry(action="tool")))  # needs action_ref
        self.assertTrue(rl.validate(entry(quality_verdict="rework")))  # needs rework_cycles

    def test_problem_tags(self):
        self.assertEqual(rl.validate(entry(problems=["conflict", "ci-red: kanban title"])), [])
        self.assertTrue(rl.validate(entry(problems=["mystery"])))
        self.assertEqual(rl.problem_tag("conflict: kanban row 612"), "conflict")


class Summary(unittest.TestCase):
    def setUp(self):
        self.es = [
            entry(task="A", duration_min=10, tokens_k=100),
            entry(task="B", duration_min=20, tokens_k=200, quality_verdict="ok", rework_cycles=2,
                  problems=["conflict: x", "ci-red"], lost_min=6, action="tool", action_ref="tools/x.py"),
            entry(task="C", duration_min=60, tokens_k=300, rework_cycles=1, problems=["stacked-pr"], lost_min=2),
            entry(task="D", agent_kind="lead", duration_min=None, quality_verdict="rework", rework_cycles=1,
                  problems=["studio-window"], lost_min=30, action="memory", action_ref="m"),
        ]

    def test_numbers(self):
        s = rl.summary(self.es)
        self.assertIn("Entries: 4 (3 agent tasks, 1 lead entries)", s)
        self.assertIn("total 90 min, median 20 min, longest 60 min", s)
        self.assertIn("agent tasks: 2 of 3 (67%); redo rounds: 3", s)
        self.assertIn("lead entries: 1 of 1 (100%); redo rounds: 1", s)

    def test_time_sinks_use_first_tag_and_rank_by_minutes(self):
        s = rl.summary(self.es)
        sinks = s.split("Top 3 time sinks")[1].splitlines()[1:4]
        self.assertTrue(sinks[0].strip().startswith("studio-window"))
        self.assertTrue(sinks[1].strip().startswith("conflict"))
        self.assertTrue(sinks[2].strip().startswith("stacked-pr"))
        self.assertNotIn("ci-red", "\n".join(sinks))  # not the first tag of any entry

    def test_unfixed_problems_listed(self):
        self.assertIn("no fix yet (action none): 1", rl.summary(self.es))

    def test_empty(self):
        self.assertIn("empty", rl.summary([]))


class Cli(unittest.TestCase):
    def test_add_list_summary_render(self):
        with tempfile.TemporaryDirectory() as d:
            log, doc = Path(d) / "retro" / "log.jsonl", Path(d) / "doc.md"
            doc.write_text("# t\n%s\n%s\nend\n" % (rl.START, rl.END), encoding="utf-8")
            base = ["--log", str(log), "--doc", str(doc)]
            code, _, _ = run(*base, "add", "--task", "First | thing", "--pr", "7", "--duration-min", "12.5",
                             "--verdict", "good", "--step", "x", "--problem", "conflict: y", "--lost-min", "3")
            self.assertEqual(code, 0)
            code, _, err = run(*base, "add", "--task", "Bad", "--verdict", "good", "--problem", "nonsense")
            self.assertEqual(code, 2)
            self.assertIn("unknown problem tag", err)
            self.assertEqual(len(rl.load(log)), 1)
            code, out, _ = run(*base, "list")
            self.assertIn("First / thing", out)  # pipe cannot break the table
            self.assertIn("#7", out)
            code, out, _ = run(*base, "summary")
            self.assertIn("conflict", out)
            self.assertEqual(run(*base, "render", "--check")[0], 1)
            self.assertEqual(run(*base, "render")[0], 0)
            self.assertEqual(run(*base, "render", "--check")[0], 0)
            self.assertIn("First / thing", doc.read_text(encoding="utf-8"))
            self.assertTrue(doc.read_text(encoding="utf-8").endswith("end\n"))

    def test_render_needs_markers(self):
        with tempfile.TemporaryDirectory() as d:
            doc = Path(d) / "doc.md"
            doc.write_text("no markers\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                rl.render(doc, Path(d) / "none.jsonl")


class ShippedLog(unittest.TestCase):
    def test_log_is_valid_and_json_per_line(self):
        entries = rl.load(rl.LOG)
        self.assertGreaterEqual(len(entries), 20)
        for e in entries:
            self.assertEqual(rl.validate(e), [], e.get("task"))
            self.assertEqual(set(e), set(rl.FIELDS), e.get("task"))
        for line in rl.LOG.read_text(encoding="utf-8").splitlines():
            json.loads(line)

    def test_page_table_is_current(self):
        self.assertTrue(rl.render(rl.DOC, rl.LOG, check=True),
                        "docs/168 table is stale: run python tools/retro_log.py render")


if __name__ == "__main__":
    unittest.main()
