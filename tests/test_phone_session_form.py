"""BD-1004: tools/phone_session_form.py turns the owner's phone form into traffic lights (docs/175). Self-contained: no owner-PC files."""
import contextlib
import csv
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import phone_session_form as psf  # noqa: E402

BUDGETS = {"parts": 3000, "memMb": 1200}

GOOD = """\
# a hint line
date: 2026-10-25
tester: owner
device_model: Samsung Galaxy A10
android_version: 9
ram_gb: 2
build_label: BUILD redesign-021
battery_start_pct: 90%
battery_end_pct: 86 %
temperature_feel: Warm
join_seconds: 45 s
ping_ms: 90
spawn_fps: 41
food_fps: 33 fps
hatch_fps: 30
cave_fps: 35
weather_fps: 31
memory_mb_spawn: 700 MB
memory_mb_food: 760
memory_mb_hatch: 800
memory_mb_end: 820
freezes: 0
crashed: no
taps_ok: yes
words_ok: yes
opened_shop: yes
screenshot_1: s1.jpg
screenshot_2: s2.jpg
screenshot_3: s3.jpg
screenshot_4: s4.jpg
"""


def light(result, key):
    return {c["key"]: c["light"] for c in result["checks"]}[key]


class ParseTests(unittest.TestCase):
    def test_numbers_with_units(self):
        self.assertEqual(psf.number("28 fps"), 28)
        self.assertEqual(psf.number("1,050 MB"), 1050)
        self.assertEqual(psf.number("35%"), 35)
        self.assertEqual(psf.number("about 12.5"), 12.5)
        self.assertIsNone(psf.number(""))
        self.assertIsNone(psf.number("none"))
        self.assertIsNone(psf.number(None))

    def test_words(self):
        self.assertEqual(psf.word("Yes, twice"), "yes")
        self.assertEqual(psf.word("NO"), "no")
        self.assertEqual(psf.word("Warm"), "warm")
        self.assertIsNone(psf.word(""))
        self.assertIsNone(psf.word("banana"))

    def test_form_skips_hints_blank_and_reports_unknown_keys(self):
        values, unknown = psf.parse_form("# hint: x\n\ndevice model: Moto\nsped_fps: 20\nspawn_fps:\nnotes: a: b\n")
        self.assertEqual(values["device_model"], "Moto")      # forgiving key: spaces and case
        self.assertEqual(values["spawn_fps"], "")
        self.assertEqual(values["notes"], "a: b")              # only the first colon splits
        self.assertEqual(unknown, ["sped_fps"])

    def test_template_has_every_key_once_and_parses_blank(self):
        keys = re.findall(r"^([a-z0-9_]+):", psf.TEMPLATE, re.M)
        self.assertEqual(sorted(keys), sorted(psf.FORM_KEYS))
        self.assertEqual(len(keys), len(set(keys)))
        values, unknown = psf.parse_form(psf.TEMPLATE)
        self.assertEqual(unknown, [])
        self.assertTrue(all(v == "" for v in values.values()))

    def test_blank_template_is_all_grey(self):
        values, _ = psf.parse_form(psf.TEMPLATE)
        result = psf.evaluate(values, BUDGETS)
        self.assertEqual(result["overall"], psf.GREY)
        self.assertTrue(all(c["light"] == psf.GREY for c in result["checks"]))
        self.assertTrue(result["notes"])


class LightTests(unittest.TestCase):
    def evaluate(self, **kw):
        values, _ = psf.parse_form(GOOD)
        values.update({k: str(v) for k, v in kw.items()})
        return psf.evaluate(values, BUDGETS)

    def test_good_session_is_yellow_only_for_the_warm_phone(self):
        result = self.evaluate()
        self.assertEqual(light(result, "fps_spawn"), psf.GREEN)
        self.assertEqual(light(result, "fps_hatch"), psf.GREEN)      # exactly 30 passes
        self.assertEqual(light(result, "memory_mb"), psf.GREEN)       # 820 <= 900
        self.assertEqual(light(result, "battery_drop_pct"), psf.GREEN)  # 90 - 86 = 4
        self.assertEqual(light(result, "temperature_feel"), psf.YELLOW)
        self.assertEqual(result["overall"], psf.YELLOW)

    def test_cool_phone_and_good_numbers_is_green(self):
        self.assertEqual(self.evaluate(temperature_feel="cool")["overall"], psf.GREEN)

    def test_fps_edges(self):
        self.assertEqual(light(self.evaluate(spawn_fps=29.9), "fps_spawn"), psf.YELLOW)
        self.assertEqual(light(self.evaluate(spawn_fps=24), "fps_spawn"), psf.YELLOW)
        self.assertEqual(light(self.evaluate(spawn_fps=23.9), "fps_spawn"), psf.RED)
        self.assertEqual(self.evaluate(spawn_fps=12, temperature_feel="cool")["overall"], psf.RED)

    def test_frame_milliseconds_become_fps(self):
        result = self.evaluate(spawn_fps="", spawn_frame_ms=50)   # 20 fps
        self.assertEqual(result["numbers"]["fps_spawn"], 20.0)
        self.assertEqual(light(result, "fps_spawn"), psf.RED)
        self.assertEqual(light(self.evaluate(spawn_fps="", spawn_frame_ms=33), "fps_spawn"), psf.GREEN)

    def test_fps_wins_over_frame_ms(self):
        self.assertEqual(self.evaluate(spawn_fps=40, spawn_frame_ms=100)["numbers"]["fps_spawn"], 40)

    def test_memory_uses_the_budget(self):
        self.assertEqual(light(self.evaluate(memory_mb_end=900), "memory_mb"), psf.GREEN)       # 75% of 1,200
        self.assertEqual(light(self.evaluate(memory_mb_end=901), "memory_mb"), psf.YELLOW)
        self.assertEqual(light(self.evaluate(memory_mb_end=1200), "memory_mb"), psf.YELLOW)
        self.assertEqual(light(self.evaluate(memory_mb_end=1201), "memory_mb"), psf.RED)
        # the budget file decides, not a constant in the check
        values, _ = psf.parse_form(GOOD)
        small = psf.evaluate(values, {"parts": 3000, "memMb": 800})
        self.assertEqual(light(small, "memory_mb"), psf.RED)

    def test_memory_growth(self):
        self.assertEqual(self.evaluate()["numbers"]["memory_growth_mb"], 120)
        self.assertEqual(light(self.evaluate(memory_mb_end=1000), "memory_growth_mb"), psf.YELLOW)   # +300
        self.assertEqual(light(self.evaluate(memory_mb_end=1100), "memory_growth_mb"), psf.RED)

    def test_crash_is_always_red(self):
        result = self.evaluate(crashed="yes", temperature_feel="cool")
        self.assertEqual(light(result, "crashed"), psf.RED)
        self.assertEqual(result["overall"], psf.RED)
        self.assertTrue(any("crashed" in n for n in result["notes"]))

    def test_other_checks(self):
        self.assertEqual(light(self.evaluate(join_seconds=61), "join_seconds"), psf.YELLOW)
        self.assertEqual(light(self.evaluate(join_seconds=121), "join_seconds"), psf.RED)
        self.assertEqual(light(self.evaluate(freezes=1), "freezes"), psf.YELLOW)
        self.assertEqual(light(self.evaluate(freezes=3), "freezes"), psf.RED)
        self.assertEqual(light(self.evaluate(battery_end_pct=75), "battery_drop_pct"), psf.RED)   # 15 points
        self.assertEqual(light(self.evaluate(temperature_feel="hot"), "temperature_feel"), psf.RED)
        self.assertEqual(light(self.evaluate(taps_ok="some"), "taps_ok"), psf.YELLOW)
        self.assertEqual(light(self.evaluate(words_ok="no"), "words_ok"), psf.RED)
        self.assertEqual(light(self.evaluate(ping_ms=300), "ping_ms"), psf.RED)

    def test_unread_is_grey_never_green(self):
        result = self.evaluate(weather_fps="", cave_fps="", ping_ms="")
        self.assertEqual(light(result, "fps_weather"), psf.GREY)
        self.assertEqual(light(result, "ping_ms"), psf.GREY)
        self.assertEqual(light(result, "parts_max"), psf.GREY)     # needs a measurement build

    def test_few_readings_is_grey_overall(self):
        values = {"spawn_fps": "40", "temperature_feel": "cool"}
        result = psf.evaluate(values, BUDGETS)
        self.assertEqual(result["overall"], psf.GREY)

    def test_parts_from_qa_marks(self):
        values, _ = psf.parse_form(GOOD)
        marks = [{"label": "food_field", "parts": 3400, "memMb": 1300}, {"label": "end", "parts": 2900, "memMb": 900}]
        result = psf.evaluate(values, BUDGETS, qa_marks=marks)
        self.assertEqual(result["numbers"]["parts_max"], 3400)
        self.assertEqual(light(result, "parts_max"), psf.RED)       # 3,400 > 3,000 and the row has no yellow band (share 1.0)
        self.assertEqual(result["numbers"]["memory_mb"], 1300)      # the larger of form and overlay

    def test_screenshots(self):
        result = self.evaluate(screenshot_3="")
        files = {s["key"]: s["file"] for s in result["screenshots"]}
        self.assertEqual(files["screenshot_3"], "")
        self.assertEqual(files["screenshot_1"], "s1.jpg")
        self.assertEqual(len(result["screenshots"]), 4)


class TableTests(unittest.TestCase):
    def test_every_threshold_row_is_well_formed_and_has_an_action(self):
        for key, row in psf.THRESHOLDS.items():
            self.assertIn(row["kind"], ("min", "max", "band"), key)
            self.assertTrue(row["label"] and row["why"], key)
            if row["kind"] == "band":
                self.assertTrue(row["green"] and row["red"], key)
            elif "budget" in row:
                self.assertIn(row["budget"], BUDGETS, key)
            elif row["kind"] == "min":
                self.assertGreaterEqual(row["green"], row["yellow"], key)
            else:
                self.assertLessEqual(row["green"], row["yellow"], key)
            self.assertIn(key, psf.ACTIONS, "no action text for " + key)
        self.assertEqual(set(psf.ACTIONS) - set(psf.THRESHOLDS), set())

    def test_every_spot_has_a_row_and_form_keys(self):
        for spot, _label in psf.SPOTS:
            self.assertIn("fps_" + spot, psf.THRESHOLDS)
            self.assertIn(spot + "_fps", psf.FORM_KEYS)
            self.assertIn(spot + "_frame_ms", psf.FORM_KEYS)

    def test_budget_file_when_present_agrees_with_the_defaults(self):
        budgets = psf.load_budgets()                       # repo file when it is there, defaults otherwise
        self.assertIsInstance(budgets["memMb"], (int, float))
        self.assertEqual(psf.load_budgets(Path("does-not-exist.json")), psf.DEFAULT_BUDGETS)

    def test_budget_file_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b.json"
            path.write_text(json.dumps({"phone": {"memMb": {"value": 900}}}), encoding="utf-8")
            self.assertEqual(psf.load_budgets(path), {"parts": 3000, "memMb": 900})


class OutputTests(unittest.TestCase):
    def test_evidence_text(self):
        values, unknown = psf.parse_form(GOOD + "crashd: no\n")
        text = psf.render(values, psf.evaluate(values, BUDGETS), unknown)
        self.assertIn("# Phone session 2026-10-25: Samsung Galaxy A10, Android 9, 2 GB RAM", text)
        self.assertIn("## Verdict: YELLOW", text)
        self.assertIn("| Speed at the start (frames per second) | 41 | GREEN |", text)
        self.assertIn("Warm", text.replace("warm", "Warm"))
        self.assertIn("Check the spelling of: crashd", text)
        self.assertIn("MEASURED BY HAND", text)
        self.assertNotIn("MISSING", text)                  # all four screenshots listed

    def test_missing_screenshot_and_actions_are_listed(self):
        values, _ = psf.parse_form(GOOD.replace("screenshot_2: s2.jpg", "screenshot_2:").replace("spawn_fps: 41", "spawn_fps: 20"))
        text = psf.render(values, psf.evaluate(values, BUDGETS))
        self.assertIn("MISSING", text)
        self.assertIn("FoodRadiusFactor", text)            # the spawn action
        self.assertIn("Not read (GREY)", text)

    def test_counts_csv_is_readable_by_the_playtest_report(self):
        values, _ = psf.parse_form(GOOD + "crashed: yes\n")
        rows = list(csv.DictReader(io.StringIO(psf.counts_csv(values))))
        self.assertEqual({r["name"]: r["value"] for r in rows}, {"crashes": "1", "shop_opens": "1"})
        blank, _ = psf.parse_form(psf.TEMPLATE)
        self.assertEqual(psf.counts_csv(blank).strip(), "name,value,note")

    def test_output_dir_uses_the_form_date(self):
        values, _ = psf.parse_form("date: 2026-11-02\n")
        self.assertEqual(psf.output_dir(values, root=Path("R")), Path("R/docs/evidence/2026-11-02-phone-session"))
        import datetime
        self.assertEqual(psf.output_dir({}, root=Path("R"), today=datetime.date(2026, 1, 2)).name, "2026-01-02-phone-session")
        self.assertEqual(psf.output_dir({"date": "next week"}, root=Path("R"), today=datetime.date(2026, 1, 2)).name, "2026-01-02-phone-session")

    def test_command_line_writes_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            form = Path(tmp) / "form.txt"
            form.write_text(GOOD, encoding="utf-8")
            out = Path(tmp) / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(psf.main([str(form), "--out-dir", str(out)]), 0)
            self.assertIn("Verdict", (out / "README.md").read_text(encoding="utf-8"))
            self.assertTrue((out / "counts.csv").read_text(encoding="utf-8").startswith("name,value,note"))

    def test_command_line_reads_a_qa_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            form, log = Path(tmp) / "form.txt", Path(tmp) / "phone.log"
            form.write_text(GOOD, encoding="utf-8")
            log.write_text('12:00:09  [BD-QA] {"label":"food_field","fps":20,"memMb":950,"parts":3500}\n', encoding="utf-8")
            out = Path(tmp) / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(psf.main([str(form), "--qa-log", str(log), "--out-dir", str(out)]), 0)
            text = (out / "README.md").read_text(encoding="utf-8")
            self.assertIn("measurement build", text)
            self.assertIn("| Parts in the world (measurement build only) | 3500 | RED |", text)


class DocTests(unittest.TestCase):
    """docs/175 is in the repo, so it may be checked: the form in the doc is the form the tool reads."""

    def setUp(self):
        self.doc = (ROOT / "docs" / "175-phone-test-kit.md").read_text(encoding="utf-8")

    def test_doc_contains_the_template_exactly(self):
        self.assertIn(psf.TEMPLATE.rstrip("\n"), self.doc)

    def test_doc_names_every_check(self):
        for key in ("memMb", "parts", "THRESHOLDS", "FoodRadiusFactor", "BD-498", "BD-502", "BD-085", "BD-322"):
            self.assertIn(key, self.doc)

    def test_twelve_steps_and_four_screenshots(self):
        steps = re.findall(r"^\| (\d+) \| \*\*", self.doc, re.M)
        self.assertEqual(steps, [str(i) for i in range(1, 13)])
        for key, _ in psf.SCREENSHOTS:
            self.assertIn(key, self.doc)


if __name__ == "__main__":
    unittest.main()
