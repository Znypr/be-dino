"""Tests for tools/release_playtest.py and tools/verify_release_ids.py (docs/148). Offline: no network, no Roblox, no tag is created."""
import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import release_playtest as rp  # noqa: E402
import release_profiles as profiles  # noqa: E402
import verify_release_ids as ids  # noqa: E402

CONFIG = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")


def with_value(source, key, literal):
    pattern = re.compile(rf"^(    {key} = )[^,\n]*(,.*)$", re.M)
    assert pattern.search(source), key
    return pattern.sub(lambda m: m.group(1) + literal + m.group(2), source, count=1)


def filled_config(universe=222222222, place=333333333, products=False):
    source = with_value(with_value(CONFIG, "PlaytestUniverseId", str(universe)), "PlaytestPlaceId", str(place))
    return source if products else re.sub(r"^    DeveloperProducts = .*$", "    DeveloperProducts = {},", source, flags=re.M)


def slot(universe=222222222, place=333333333, kind="new"):
    return {"PlaytestUniverseId": universe, "PlaytestPlaceId": place, "ExperienceKind": kind, "AnsweredOn": "2026-10-18"}


class IdSlotTests(unittest.TestCase):
    def test_committed_slot_is_well_formed_and_empty_until_the_owner_answers(self):
        errors, _warnings, state = ids.check()
        self.assertEqual(errors, [])
        self.assertEqual(state, "empty")  # BD-004: when the owner answers, this test and docs/148 are updated with the slot

    def test_empty_slot_fails_the_release_gate(self):
        errors, _ = ids.slot_problems(ids.load_slot(), CONFIG, require_filled=True)
        self.assertTrue(any("BD-004 is not answered" in e for e in errors), errors)

    def test_partial_slot_always_fails(self):
        errors, _ = ids.slot_problems(slot(place=None), CONFIG)
        self.assertTrue(any("only one of" in e for e in errors), errors)

    def test_bad_values_fail(self):
        for bad in ({"PlaytestUniverseId": 0}, {"PlaytestUniverseId": True}, {"PlaytestPlaceId": "5"},
                    {"ExperienceKind": "maybe"}, {"Surprise": 1}):
            errors, _ = ids.slot_problems(dict(slot(), **bad), filled_config())
            self.assertTrue(errors, bad)

    def test_filled_new_experience_passes_when_config_matches(self):
        errors, warnings = ids.slot_problems(slot(), filled_config(), require_filled=True)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_kind_is_required_once_filled(self):
        errors, _ = ids.slot_problems(slot(kind=None), filled_config())
        self.assertTrue(any("ExperienceKind is empty" in e for e in errors), errors)

    def test_config_must_match_the_slot(self):
        errors, _ = ids.slot_problems(slot(), filled_config(universe=1, place=2))
        self.assertEqual(len([e for e in errors if e.startswith("Config.")]), 2, errors)

    def test_legacy_experience_with_products_is_a_hard_stop(self):
        legacy = slot(ids.LEGACY_UNIVERSE_ID, ids.LEGACY_PLACE_ID, kind="legacy")
        errors, _ = ids.slot_problems(legacy, filled_config(ids.LEGACY_UNIVERSE_ID, ids.LEGACY_PLACE_ID, products=True), require_filled=True)
        self.assertTrue(any(e.startswith("HARD STOP") and "3717200374" in e for e in errors), errors)
        # declared legacy with other numbers is also a hard stop; the ids alone also trigger it even if kind says 'new' (contradiction)
        errors, _ = ids.slot_problems(slot(kind="legacy"), filled_config(products=True))
        self.assertTrue(any(e.startswith("HARD STOP") for e in errors), errors)
        errors, _ = ids.slot_problems(slot(ids.LEGACY_UNIVERSE_ID, ids.LEGACY_PLACE_ID, kind="new"),
                                      filled_config(ids.LEGACY_UNIVERSE_ID, ids.LEGACY_PLACE_ID, products=True))
        self.assertTrue(any(e.startswith("HARD STOP") for e in errors) and any("one of the two statements" in e for e in errors), errors)

    def test_legacy_experience_without_products_only_warns(self):
        legacy = slot(ids.LEGACY_UNIVERSE_ID, ids.LEGACY_PLACE_ID, kind="legacy")
        errors, warnings = ids.slot_problems(legacy, filled_config(ids.LEGACY_UNIVERSE_ID, ids.LEGACY_PLACE_ID, products=False))
        self.assertEqual(errors, [])
        self.assertTrue(any("LEGACY" in w for w in warnings), warnings)

    def test_new_experience_with_products_in_config_warns_only(self):
        errors, warnings = ids.slot_problems(slot(), filled_config(products=True))
        self.assertEqual(errors, [])
        self.assertTrue(any("inert" in w for w in warnings), warnings)

    def test_developer_product_ids_are_read_from_config(self):
        self.assertEqual(len(ids.developer_product_ids(CONFIG)), 6)
        self.assertEqual(ids.developer_product_ids(filled_config()), [])


class GateTests(unittest.TestCase):
    def test_dirty_tree_is_refused_and_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for command in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"]):
                subprocess.run(["git", "-C", str(folder)] + command, check=True)
            (folder / "a.txt").write_text("1\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(folder), "add", "."], check=True)
            subprocess.run(["git", "-C", str(folder), "commit", "-qm", "x"], check=True)
            self.assertEqual(rp.working_tree_problems(folder), [])
            (folder / "a.txt").write_text("2\n", encoding="utf-8")
            self.assertTrue(rp.working_tree_problems(folder))
            subprocess.run(["git", "-C", str(folder), "checkout", "--", "a.txt"], check=True)
            (folder / "new.txt").write_text("untracked\n", encoding="utf-8")
            self.assertTrue(rp.working_tree_problems(folder), "an untracked file is also dirty")

    def test_shipped_profiles_exclude_scratch_and_pass_today(self):
        self.assertEqual(sorted(rp.shipped_profiles()), ["default", "playtest"])
        self.assertEqual(rp.shipped_flag_problems(CONFIG), [])

    def test_streaming_on_in_a_shipped_profile_is_refused(self):
        original = dict(profiles.STREAMING)
        try:
            profiles.STREAMING["playtest"] = profiles.Streaming(enabled=True, scratch=False)
            problems = rp.shipped_flag_problems(CONFIG)
            self.assertTrue(any("StreamingEnabled ON" in p and "'playtest'" in p for p in problems), problems)
            profiles.STREAMING["playtest"] = profiles.Streaming(enabled=True, scratch=False, gate="BD-502:docs/147-streaming-experiment-2026-10-17.md")
            self.assertTrue(rp.shipped_flag_problems(CONFIG), "even a gated flip is not allowed through the release script")
        finally:
            profiles.STREAMING.clear()
            profiles.STREAMING.update(original)

    def test_scratch_streaming_profile_is_not_a_shipped_profile(self):
        self.assertTrue(profiles.streaming_for("playtest-streaming").enabled)
        self.assertNotIn("playtest-streaming", rp.shipped_profiles())

    def test_paid_random_flags_on_are_refused(self):
        for flag in rp.PAID_FLAGS:
            problems = rp.shipped_flag_problems(with_value(CONFIG, flag, "true"))
            self.assertTrue(any(flag in p for p in problems), (flag, problems))

    def test_paid_flag_missing_is_refused(self):
        source = "\n".join(l for l in CONFIG.splitlines() if not l.startswith("    CrystalPacksEnabled ="))
        self.assertTrue(any("CrystalPacksEnabled is missing" in p for p in rp.shipped_flag_problems(source)))

    def test_ci_classification(self):
        self.assertEqual(rp.classify_runs([])[0], "none")
        self.assertEqual(rp.classify_runs([{"status": "completed", "conclusion": "success"}])[0], "success")
        self.assertEqual(rp.classify_runs([{"status": "in_progress", "conclusion": None}])[0], "pending")
        self.assertEqual(rp.classify_runs([{"status": "completed", "conclusion": "failure"}])[0], "failure")

    def test_evaluate_gates_blocks_on_empty_ids_even_when_everything_else_is_fine(self):
        with mock.patch.object(rp, "working_tree_problems", return_value=[]), mock.patch.object(rp, "on_main_problem", return_value=None):
            gates = rp.evaluate_gates(skip_ci_check=True)
        blocking = [g.name for g in gates if g.blocks]
        self.assertEqual(len(blocking), 1)
        self.assertIn("BD-004", blocking[0])


class MainFlowTests(unittest.TestCase):
    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rp.main(list(argv))
        return code, out.getvalue()

    def test_real_run_is_refused_before_building_anything(self):
        with mock.patch.object(rp, "working_tree_problems", return_value=["x"]), \
                mock.patch.object(rp, "run_command", side_effect=AssertionError("nothing may be built")):
            code, output = self.run_main("--no-fetch", "--skip-ci-check")
        self.assertEqual(code, 2, output)
        self.assertIn("REFUSED", output)
        self.assertIn("[BLOCK] working tree is clean", output)

    def test_skip_verifiers_needs_dry_run(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                rp.main(["--skip-verifiers"])


class TagAndRollbackTests(unittest.TestCase):
    def test_first_tag_has_no_rollback_target(self):
        tag, previous = rp.propose_tag("020", [])
        self.assertEqual((tag, previous), ("playtest-m1-b020-r1", None))
        text = "\n".join(rp.rollback_plan(None, tag))
        self.assertIn("NONE YET", text)
        self.assertIn("never", text.lower())

    def test_k_counts_up_and_previous_is_the_newest_tag(self):
        existing = ["playtest-m1-b019-r1", "playtest-m1-b020-r1", "playtest-m1-b020-r2"]
        self.assertEqual(rp.propose_tag("020", existing), ("playtest-m1-b020-r3", "playtest-m1-b020-r2"))
        self.assertEqual(rp.propose_tag("021", existing), ("playtest-m1-b021-r1", "playtest-m1-b020-r2"))

    def test_rollback_names_the_previous_tag_not_build_020(self):
        with mock.patch.object(rp, "git", return_value=(0, "abc123")):
            text = "\n".join(rp.rollback_plan("playtest-m1-b020-r2", "playtest-m1-b020-r3"))
        self.assertIn("playtest-m1-b020-r2", text)
        self.assertIn("never Build 020", text)

    def test_tag_commands_do_not_push_by_themselves(self):
        commands = rp.tag_commands("playtest-m1-b020-r1", "abc", "msg")
        self.assertTrue(commands[0].startswith("git tag -a playtest-m1-b020-r1"))
        self.assertIn("owner only", commands[1])
        source = (ROOT / "tools/release_playtest.py").read_text(encoding="utf-8")
        self.assertNotRegex(source, r'git\("push"|git\("tag", "(-a|-d|-f|--annotate)|"push",|\["git", "push"')
        self.assertEqual(re.findall(r'git\("tag", "[^"]*"', source), ['git("tag", "--list"'])


class CiListTests(unittest.TestCase):
    def test_commands_come_from_the_real_workflow(self):
        commands = rp.ci_commands(rp.WORKFLOW.read_text(encoding="utf-8"), "LUAU", "LUAUC")
        flat = [" ".join(c[1:]) for c in commands]
        self.assertGreater(len(commands), 100)
        self.assertIn("tools/verify_doc_ids.py", flat)
        self.assertIn("tools/verify_load.py --runner LUAU --gate-playtest", flat)
        self.assertIn("tools/verify_sources.py --compiler LUAUC", flat)
        self.assertIn("tools/verify_release_ids.py", flat)
        self.assertFalse([f for f in flat if "/tmp/luau" in f or "${{" in f])
        names = {Path(c[1]).name for c in commands}
        self.assertFalse(names & rp.CI_EXCLUDED_SCRIPTS)
        for command in commands:
            self.assertTrue((ROOT / command[1]).is_file(), command)

    def test_every_workflow_script_exists_and_smoke_is_run_by_the_script(self):
        self.assertTrue((ROOT / "tools/verify_session1_smoke.py").is_file())
        self.assertIn("verify_session1_smoke.py", rp.CI_EXCLUDED_SCRIPTS)  # run explicitly, once, by main()


class ManifestTests(unittest.TestCase):
    def test_asset_id_stats(self):
        stats = rp.asset_id_stats('"rbxassetid://1" "rbxassetid://1" x rbxassetid://22 rbxasset://textures/x.png')
        self.assertEqual(stats, {"distinct_asset_ids": 2, "asset_id_references": 3})

    def test_release_record_row_has_the_docs55_columns(self):
        row = rp.release_record_row("2026-10-18", "playtest-m1-b020-r1", "a" * 40, "h" * 64, "BeDino_Playtest_M1_v1", 1, 2, "first publish")
        self.assertEqual(row.count("|"), 10)
        self.assertIn("1 / 2", row)

    def test_flag_table_reads_the_built_places(self):
        import build as packager
        data_default, _ = packager.build()
        data_playtest, _, _ = packager.build_profile("playtest")
        table = rp.flag_table(data_default, data_playtest)
        self.assertIs(table["CaveHub"]["default"], False)
        self.assertIs(table["CaveHub"]["playtest"], True)
        self.assertEqual(table["StreamingEnabled"], {"default": False, "playtest": False})
        self.assertIs(table["PaidRandomItemsEnabled"]["playtest"], False)
        self.assertEqual(rp.flag_warnings(table), [])

    def test_docs_runbook_is_linked_to_the_tools(self):
        doc = next((ROOT / "docs").glob("148-publish-runbook.md")).read_text(encoding="utf-8")
        for needle in ("release_playtest.py", "release_ids.json", "Allow Mesh & Image APIs", "**4**", "Publish to Roblox As", "BD-320"):
            self.assertIn(needle, doc)

    def test_workflow_runs_the_id_slot_check(self):
        self.assertIn("python tools/verify_release_ids.py", rp.WORKFLOW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
