"""docs/152: the all-on-rehearsal profile, its scratch-tree runner and the static switch-on guards."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build as packager  # noqa: E402
import release_playtest as rp  # noqa: E402
import release_profiles as profiles  # noqa: E402
import run_rehearsal  # noqa: E402
import verify_release  # noqa: E402
import verify_switch_on  # noqa: E402

CONFIG = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
PROFILE = "all-on-rehearsal"


class RehearsalProfileTests(unittest.TestCase):
    def values(self, profile):
        rewritten, report = profiles.apply_profile(CONFIG, profile)
        self.assertEqual(report.errors, [], profile)
        return {k: v[-1][1] for k, v in profiles.config_entries(rewritten).items()}

    def test_every_built_but_off_gameplay_flag_is_on(self):
        values = self.values(PROFILE)
        for key, _why in profiles.REHEARSAL_ON:
            self.assertIs(values[key], True, key)
        for key in ("ObjectivesEnabled", "GiftClaimEnabled", "AdminGiftsEnabled", "GiftingEnabled", "FoodPickupAtMouth", "PredationAtMouth",
                    "CombatEnabled", "SpecialFoodsEnabled", "PerDinoCosmeticsEnabled", "FastTravelPerk", "HatchV2",
                    "CaveHub", "ClassMovementEnabled", "LowPolyDinos", "IdentityPersistentEnabled", "IdentityFusionPreviewEnabled",
                    "SecretSpeciesEnabled", "DinoSkinsEnabled"):
            self.assertIs(values[key], True, key)

    def test_the_paid_line_and_the_test_switches_stay_closed(self):
        values = self.values(PROFILE)
        for key in ("CrystalPacksEnabled", "PaidRandomItemsEnabled", "CollectionTestGrantEnabled", "ChestTestGrantEnabled",
                    "MutationTestSetupEnabled", "SecurityTestHarnessEnabled", "ArtTestHarnessEnabled", "QaOverlayEnabled",
                    "DemoDirectorEnabled", "HatchV2Preview"):
            self.assertIs(values[key], False, key)
            self.assertTrue(any(r.key == key and r.mode == "require" and r.value is False for r in profiles.rules_for(PROFILE)), key)

    def test_it_is_a_scratch_profile_and_not_a_shipped_one(self):
        self.assertTrue(profiles.streaming_for(PROFILE).scratch)
        self.assertNotIn(PROFILE, rp.shipped_profiles())
        self.assertEqual(sorted(rp.shipped_profiles()), ["default", "playtest"])
        self.assertEqual(rp.shipped_flag_problems(CONFIG), [])

    def test_the_default_and_playtest_hard_stops_are_unchanged(self):
        for flag in ("ObjectivesEnabled", "GiftClaimEnabled", "AdminGiftsEnabled", "GiftingEnabled"):
            for name in ("default", "playtest"):
                self.assertTrue(any(r.key == flag and r.mode == "require" and r.value is False for r in profiles.rules_for(name)), (flag, name))
        rehearsal_config = profiles.apply_profile(CONFIG, PROFILE)[0]
        for name in ("default", "playtest"):
            report = profiles.verify_source(rehearsal_config, name)
            self.assertTrue(any("ObjectivesEnabled" in e for e in report.errors), f"{name} must refuse a Config with the rehearsal values")

    def test_the_rehearsal_place_builds_and_verifies_offline(self):
        data, _, report = packager.build_profile(PROFILE, ROOT / "default.project.json")
        self.assertEqual(report.errors, [])
        checked = verify_release.verify_place(data, PROFILE)
        self.assertEqual(checked.errors, [])
        self.assertTrue(any("SCRATCH" in w for w in checked.warnings))


class OverlayTests(unittest.TestCase):
    def test_overlay_keeps_every_committed_line_and_overrides_the_returned_table(self):
        text, errors, overrides = run_rehearsal.overlay_config(CONFIG, PROFILE)
        self.assertEqual(errors, [])
        self.assertIn("    CombatEnabled = false,", text)  # static "ships false" checks still see the committed line
        self.assertIn("Rehearsal.CombatEnabled = true", text)
        self.assertIn("local BaseConfig = table.freeze({", text)
        self.assertTrue(text.rstrip().endswith("return table.freeze(Rehearsal)"))
        self.assertIs(overrides["ObjectivesEnabled"], True)
        self.assertNotIn("CrystalPacksEnabled", overrides)
        self.assertNotIn("PaidRandomItemsEnabled", overrides)
        self.assertEqual(text.count("return table.freeze("), 1)

    def test_profile_none_is_the_committed_source(self):
        text, errors, overrides = run_rehearsal.overlay_config(CONFIG, "none")
        self.assertEqual((text, errors, overrides), (CONFIG, [], {}))

    def test_a_config_without_the_expected_shape_is_refused(self):
        _text, errors, _ = run_rehearsal.overlay_config(CONFIG.replace("return table.freeze({", "return ({", 1), PROFILE)
        self.assertTrue(errors)

    def test_expected_failures_need_the_signature_and_nothing_else_failing(self):
        entry = {"signature": "pinned", "only": "pinned"}
        self.assertTrue(run_rehearsal.expected_failure({"output": "FAIL: pinned\nok line"}, entry))
        self.assertFalse(run_rehearsal.expected_failure({"output": "FAIL: pinned\nFAIL: something real"}, entry))
        self.assertFalse(run_rehearsal.expected_failure({"output": "FAIL: other"}, entry))
        self.assertFalse(run_rehearsal.expected_failure({"output": "FAIL: pinned"}, None))

    def test_every_expected_entry_names_a_real_verifier_with_a_reason(self):
        for name, entry in run_rehearsal.load_expected().items():
            self.assertTrue((ROOT / "tools" / name).is_file(), name)
            self.assertTrue(entry["reason"].strip(), name)
            self.assertTrue(entry["signature"].strip(), name)


class StaticGuardTests(unittest.TestCase):
    def run_checks(self, **patches):
        saved = {}
        verify_switch_on.errors.clear()
        try:
            for name, value in patches.items():
                saved[name] = getattr(verify_switch_on, name)
                setattr(verify_switch_on, name, value)
            verify_switch_on.check_profile()
            verify_switch_on.check_remote_names()
            return list(verify_switch_on.errors)
        finally:
            for name, value in saved.items():
                setattr(verify_switch_on, name, value)
            verify_switch_on.errors.clear()

    def test_the_committed_tree_passes(self):
        verify_switch_on.errors.clear()
        self.assertEqual(verify_switch_on.main(), 0)

    def test_a_new_flag_that_nobody_rehearsed_is_reported(self):
        errors = self.run_checks(config_source=lambda: CONFIG.replace("    CaveHub = false,", "    CaveHub = false,\n    BrandNewThingEnabled = false,", 1))
        self.assertTrue(any("BrandNewThingEnabled" in e for e in errors), errors)

    def test_two_creators_of_one_remote_name_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            files = []
            for index in range(2):
                path = Path(folder) / f"S{index}.luau"
                path.write_text('local r = Instance.new("RemoteEvent")\nr.Name = "Dup"\n', encoding="utf-8")
                files.append(path)
            real = verify_switch_on.server_files()
            errors = self.run_checks(server_files=lambda: real + files)
        self.assertTrue(any("'Dup'" in e for e in errors), errors)

    def test_turning_a_paid_flag_on_in_the_profile_is_reported(self):
        saved = list(profiles.PROFILES[PROFILE])
        try:
            profiles.PROFILES[PROFILE] = [r for r in saved if r.key != "CrystalPacksEnabled"] + [profiles.Rule("CrystalPacksEnabled", "set", True)]
            errors = self.run_checks()
        finally:
            profiles.PROFILES[PROFILE] = saved
        self.assertTrue(any("CrystalPacksEnabled" in e for e in errors), errors)


@unittest.skipUnless(os.environ.get("LUAU_RUNNER"), "LUAU_RUNNER is not set")
class RunnerEndToEnd(unittest.TestCase):
    def test_the_runner_runs_a_few_real_verifiers_against_the_all_on_values(self):
        done = subprocess.run([sys.executable, str(ROOT / "tools/run_rehearsal.py"), "--runner", os.environ["LUAU_RUNNER"],
                               "--only", "verify_mouth_reach,verify_gifts.py,verify_fusion.py,verify_rewards", "--jobs", "4"],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stdout[-3000:] + done.stderr[-2000:])
        self.assertIn("expected: verify_mouth_reach.py", done.stdout)
        self.assertIn("[ok  ] verify_rewards.py", done.stdout)


if __name__ == "__main__":
    unittest.main()
