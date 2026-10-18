"""BD-648: tools/playtest_report.py reads the fixture files and judges them with traffic lights (docs/167)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import playtest_report as pr  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
SAMPLE = FIXTURES / "playtest_sample.jsonl"
COUNTS = FIXTURES / "playtest_counts.csv"


def by_name(report):
    return {c["name"]: c for c in report["checks"]}


def run_line(duration, eggs, reason="ManualExit", food_raw=None):
    return json.dumps({"event": "run_end", "duration_s": duration, "reason": reason, "eggs": eggs, "nests": 0, "crystals": 0,
                       "food": 0, "food_raw": food_raw if food_raw is not None else eggs * 500 / 12})


def session_line(runs, total=600):
    return json.dumps({"event": "session_end", "total_s": total, "runs": runs, "hub_s": total // 4, "run_s": total * 3 // 4})


class ReadingTests(unittest.TestCase):
    def test_sample_file_counts(self):
        data = pr.read_files([SAMPLE, COUNTS])
        self.assertEqual(len(data["runs"]), 10)
        self.assertEqual(len(data["sessions"]), 6)
        self.assertEqual(len(data["feedback"]), 4)
        self.assertEqual(data["counts"]["movement_rejects"], 9)
        self.assertEqual(data["meta"]["testers"], 6)
        self.assertEqual(data["bad_lines"], 1)        # the broken [BD-TELEMETRY] line
        self.assertEqual(data["unknown_events"], 1)   # "hologram"

    def test_plain_log_noise_is_ignored(self):
        data = pr.read_lines(["hello", "17:00 Server: ok", "", "[Output] not json"])
        self.assertEqual((data["bad_lines"], data["unknown_events"], len(data["runs"])), (0, 0, 0))

    def test_missing_fields_do_not_crash(self):
        data = pr.read_lines(['{"event":"run_end"}', '{"event":"session_end","runs":"two"}', '{"event":"count","name":"crashes"}'])
        self.assertEqual(data["runs"][0]["eggs"], 0)
        self.assertEqual(data["sessions"][0]["runs"], 0)
        self.assertEqual(data["bad_lines"], 1)  # count without a value
        pr.analyse(data)

    def test_csv_rows_add_up(self):
        data = pr.read_csv("name,value\ncrashes,1\ncrashes,2\nbad,x\n,3\n")
        self.assertEqual(data["counts"], {"crashes": 3})
        self.assertEqual(data["bad_lines"], 2)

    def test_counts_from_log_lines_and_csv_combine(self):
        data = pr.read_lines(['{"event":"count","name":"hatches","value":4}'])
        pr.read_csv("name,value\nhatches,6\n", data)
        self.assertEqual(data["counts"]["hatches"], 10)


class JudgingTests(unittest.TestCase):
    def setUp(self):
        self.rate = (12.0, 500.0)

    def report(self, lines, extra_counts=None):
        data = pr.read_lines(lines)
        data["counts"].update(extra_counts or {})
        return pr.analyse(data, rate=self.rate)

    def test_sample_numbers(self):
        report = pr.analyse(pr.read_files([SAMPLE, COUNTS]), rate=self.rate)
        checks = by_name(report)
        self.assertEqual(checks["Eggs in a 5-minute run"]["status"], pr.GREEN)
        self.assertAlmostEqual(report["summary"]["eggs_per_5min"], 14.55, places=1)
        self.assertEqual(checks["Run length"]["status"], pr.GREEN)
        self.assertEqual(checks["Runs per visit"]["status"], pr.YELLOW)
        self.assertEqual(checks["Left before a first run"]["number"], "2 of 6")
        self.assertEqual(checks["Set back by the anti-cheat"]["status"], pr.YELLOW)
        self.assertEqual(checks["Players: fun"]["status"], pr.GREEN)
        self.assertEqual(report["overall"], pr.YELLOW)
        self.assertEqual([f[0] for f in report["funnel"]][:2], ["Came into the game", "Finished 1 run"])

    def test_without_counts_the_gaps_are_grey_and_listed(self):
        report = pr.analyse(pr.read_files([SAMPLE]), rate=self.rate)
        checks = by_name(report)
        for name in ("Set back by the anti-cheat", "Told \"too fast\"", "Errors and crashes", "Shop use", "Hatching"):
            self.assertEqual(checks[name]["status"], pr.GREY, name)
        rows = {row for _, row in report["gaps"]}
        self.assertTrue({"BD-649", "BD-650", "BD-651", "BD-652", "BD-653"} <= rows)

    def test_egg_target_lights(self):
        sessions = [session_line(1)]
        cases = ((15, pr.GREEN), (8, pr.YELLOW), (3, pr.RED), (40, pr.RED), (25, pr.YELLOW))
        for eggs, status in cases:
            report = self.report([run_line(300, eggs)] + sessions)
            self.assertEqual(by_name(report)["Eggs in a 5-minute run"]["status"], status, eggs)

    def test_short_runs_are_not_rated(self):
        report = self.report([run_line(10, 0, "Death"), session_line(1)])
        self.assertEqual(by_name(report)["Eggs in a 5-minute run"]["status"], pr.GREY)

    def test_crash_is_always_red(self):
        report = self.report([run_line(300, 15), session_line(2)], {"crashes": 1, "script_errors": 0})
        self.assertEqual(by_name(report)["Errors and crashes"]["status"], pr.RED)
        self.assertEqual(report["overall"], pr.RED)
        self.assertIn("Crashes first", by_name(report)["Errors and crashes"]["words"])

    def test_rate_limited_and_rejects_scale_with_visits(self):
        lines = [run_line(300, 15)] + [session_line(2) for _ in range(4)]
        quiet = self.report(lines, {"movement_rejects": 1, "rate_limited": 2})
        loud = self.report(lines, {"movement_rejects": 40, "rate_limited": 40})
        self.assertEqual(by_name(quiet)["Set back by the anti-cheat"]["status"], pr.GREEN)
        self.assertEqual(by_name(quiet)["Told \"too fast\""]["status"], pr.GREEN)
        self.assertEqual(by_name(loud)["Set back by the anti-cheat"]["status"], pr.RED)
        self.assertEqual(by_name(loud)["Told \"too fast\""]["status"], pr.RED)

    def test_unused_shop_is_yellow(self):
        report = self.report([session_line(1)], {"shop_opens": 0, "hatches": 5})
        self.assertEqual(by_name(report)["Shop use"]["status"], pr.YELLOW)
        self.assertEqual(by_name(report)["Hatching"]["status"], pr.GREEN)

    def test_quitting_mid_run_is_flagged(self):
        lines = [run_line(300, 15, "Disconnect") for _ in range(4)] + [session_line(4)]
        self.assertEqual(by_name(self.report(lines))["Quit in the middle of a run"]["status"], pr.RED)

    def test_feedback_needs_three_answers(self):
        fb = json.dumps({"event": "feedback", "fun": 1, "level": 3, "looks": 1, "location": "Hub", "species": "compy", "text": ""})
        one = by_name(self.report([fb, session_line(1)]))
        self.assertEqual(one["Players: fun"]["status"], pr.GREY)
        three = by_name(self.report([fb, fb, fb, session_line(1)]))
        self.assertEqual(three["Players: fun"]["status"], pr.RED)
        self.assertEqual(three["Players: difficulty"]["status"], pr.RED)
        self.assertIn("too hard", three["Players: difficulty"]["words"])

    def test_empty_input_gives_grey_not_a_crash(self):
        report = pr.analyse(pr.read_lines([]), rate=self.rate)
        self.assertEqual(report["overall"], pr.GREY)
        self.assertIn("funnel", pr.render(report).lower())

    def test_hand_written_funnel_steps_are_appended(self):
        lines = [session_line(1), session_line(0), '{"event":"funnel","step":"Saw the hatch party","players":1}']
        report = self.report(lines)
        self.assertEqual(report["funnel"][-1], ("Saw the hatch party", 1))
        self.assertNotIn(("Steps before the first run (first food, first egg, first hatch)", "BD-653"), report["gaps"])

    def test_small_sample_warning(self):
        report = self.report([session_line(1), run_line(300, 15)])
        self.assertTrue(report["small_sample"])
        self.assertIn("hint, not a result", pr.render(report))


class OutputTests(unittest.TestCase):
    def test_render_sections_and_footer(self):
        text = pr.render(pr.analyse(pr.read_files([SAMPLE, COUNTS]), rate=(12.0, 500.0)))
        for part in ("# Playtest report", "| Light | Check |", "## Where players drop off", "## Problems in plain words",
                     "## What players wrote", "## The game does not record these yet", "docs/119", "FoodCatchRate 12/500"):
            self.assertIn(part, text)
        self.assertIn("The shop door is hard to find", text)
        self.assertNotIn("\t", text)

    def test_worst_lights_come_first(self):
        text = pr.render(pr.analyse(pr.read_files([SAMPLE, COUNTS]), rate=(12.0, 500.0)))
        table = [l for l in text.splitlines() if l.startswith("| ") and "Light" not in l and "---" not in l]
        order = [pr.ORDER[l.split("|")[1].strip()] for l in table]
        self.assertEqual(order, sorted(order))

    def test_json_output_is_valid(self):
        report = pr.analyse(pr.read_files([SAMPLE, COUNTS]), rate=(12.0, 500.0))
        loaded = json.loads(json.dumps(pr.to_json(report)))
        self.assertEqual(loaded["overall"], pr.YELLOW)
        self.assertNotIn("per_run", loaded["summary"])

    def test_rate_comes_from_config(self):
        self.assertEqual(pr.current_rate(ROOT), (12.0, 500.0))
        self.assertEqual(pr.current_rate(ROOT / "does-not-exist"), (12.0, 500.0))

    def test_command_line_writes_the_file(self):
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = Path(tmp) / "report.md"
            self.assertEqual(pr.main([str(SAMPLE), str(COUNTS), "--out", str(out)]), 0)
            self.assertIn("# Playtest report", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
