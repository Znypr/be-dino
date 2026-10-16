import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build as packager  # noqa: E402
import release_profiles as profiles  # noqa: E402
import verify_load  # noqa: E402
import verify_release  # noqa: E402

CONFIG = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")


# Config may already define the future key; these tests need it absent to exercise "missing".
ABSENT = chr(10).join(l for l in CONFIG.splitlines() if not l.startswith("    IdentityPersistentEnabled =")) + chr(10)


def with_value(source, key, literal):
    pattern = re.compile(rf"^(    {key} = )[^,\n]*(,.*)$", re.M)
    assert pattern.search(source), key
    return pattern.sub(lambda m: m.group(1) + literal + m.group(2), source, count=1)


def with_ids(source):
    return with_value(with_value(source, "PlaytestUniverseId", "123456789"), "PlaytestPlaceId", "987654321")


def temp_project(folder, config_source):
    folder = Path(folder)
    (folder / "src/shared").mkdir(parents=True)
    (folder / "src/server").mkdir(parents=True)
    (folder / "src/shared/Config.luau").write_text(config_source, encoding="utf-8")
    (folder / "src/server/Example.luau").write_text("return {}\n", encoding="utf-8")
    project = folder / "default.project.json"
    project.write_text(json.dumps({"name": "t", "tree": {"$className": "DataModel",
        "ReplicatedStorage": {"$className": "ReplicatedStorage", "Shared": {"$path": "src/shared"}},
        "ServerScriptService": {"$className": "ServerScriptService", "Server": {"$path": "src/server"}}}}))
    return project


class ReleaseProfileTests(unittest.TestCase):
    def test_committed_source_satisfies_default_invariants(self):
        report = profiles.verify_source(CONFIG, "default")
        self.assertEqual(report.errors, [])
        self.assertEqual(verify_release.studio_guard_errors(), [])

    def test_forbidden_flags_fail(self):
        for key in ("PaidRandomItemsEnabled", "CrystalPacksEnabled", "ChestTestGrantEnabled",
                    "CollectionTestGrantEnabled", "MutationTestSetupEnabled",
                    "DuplicateSettlementProbe", "SecurityTestHarnessEnabled", "ArtTestHarnessEnabled"):
            for profile in ("default", "playtest"):
                report = profiles.verify_source(with_value(with_ids(CONFIG), key, "true"), profile)
                self.assertTrue(any(e.startswith(key) for e in report.errors), (key, profile, report.errors))

    def test_duplicate_key_shadowing_fails(self):
        source = CONFIG.replace("    CrystalPacksEnabled = false,", "    CrystalPacksEnabled = false,\n    CrystalPacksEnabled = true,", 1)
        report = profiles.verify_source(source, "default")
        self.assertTrue(any("defined 2 times" in e for e in report.errors))

    def test_playtest_requires_recorded_ids(self):
        # The committed Config now records the real IDs (BD-004); zero them to exercise the gate.
        zeroed = with_value(with_value(CONFIG, "PlaytestUniverseId", "0"), "PlaytestPlaceId", "0")
        _, report = profiles.apply_profile(zeroed, "playtest")
        self.assertFalse(report.ok)
        self.assertTrue(any(e.startswith("PlaytestUniverseId") and "BD-004" in e for e in report.errors))
        self.assertTrue(any(e.startswith("PlaytestPlaceId") for e in report.errors))

    def test_playtest_rewrites_release_values_only(self):
        rewritten, report = profiles.apply_profile(with_ids(CONFIG), "playtest")
        self.assertEqual(report.errors, [])
        values = {k: v[-1][1] for k, v in profiles.config_entries(rewritten).items()}
        self.assertEqual(values["ProfileDataStoreName"], values["PlaytestProfileDataStoreName"])
        self.assertNotEqual(values["ProfileDataStoreName"], profiles.DEVELOPMENT_STORE_NAME)
        self.assertEqual(values["ReleaseProfile"], "playtest")
        self.assertIs(values["IdentityPersistentEnabled"], True)
        self.assertIs(values["IdentityFusionPreviewEnabled"], True)
        changed = [a for a, b in zip(with_ids(CONFIG).splitlines(), rewritten.splitlines()) if a != b]
        self.assertEqual(len(changed), 9)  # +1 RunTelemetryEnabled (BD-426)
        self.assertIs(values["LowPolyDinos"], True)
        self.assertEqual((values["WorldArtMode"], values["FoodArtMode"], values["WorldArtDensity"]), ("BiomeKit", "Kit", 1.25))
        self.assertEqual(profiles.verify_source(CONFIG, "default").errors, [])

    def test_fusion_flags_stay_off_in_committed_builds(self):
        for key in ("IdentityPersistentEnabled", "IdentityFusionPreviewEnabled"):
            report = profiles.verify_source(with_value(CONFIG, key, "true"), "default")
            self.assertTrue(any(e.startswith(key) for e in report.errors), key)

    def test_missing_identity_key_fails_playtest(self):
        _, report = profiles.apply_profile(with_ids(ABSENT), "playtest")
        self.assertTrue(any(e.startswith("IdentityPersistentEnabled: missing") for e in report.errors))

    def test_missing_warn_key_does_not_block(self):
        original = profiles.PROFILES["playtest"]
        try:
            profiles.PROFILES["playtest"] = original + [profiles.Rule("FutureFlag", "set", True, missing="warn", reason="t")]
            _, report = profiles.apply_profile(with_ids(CONFIG), "playtest")
            self.assertEqual(report.errors, [])
            self.assertTrue(any(w.startswith("FutureFlag: missing") for w in report.warnings))
        finally:
            profiles.PROFILES["playtest"] = original

    def test_safety_flags_are_not_silently_patched(self):
        source = with_value(with_ids(CONFIG), "ChestTestGrantEnabled", "true")
        rewritten, report = profiles.apply_profile(source, "playtest")
        self.assertFalse(report.ok)
        self.assertIn("    ChestTestGrantEnabled = true,", rewritten)

    def test_missing_required_key_is_reported(self):
        source = "\n".join(l for l in with_ids(CONFIG).splitlines() if not l.startswith("    PlaytestPlaceId ="))
        _, report = profiles.apply_profile(source, "playtest")
        self.assertTrue(any(e.startswith("PlaytestPlaceId: missing") for e in report.errors))

    def test_store_name_rules(self):
        check = profiles._playtest_store_name
        self.assertIsNone(check("BeDino_Playtest_M1_v2"))
        for bad in ("", "BeDino_PrivateTest_v1", "Playtest", "BeDino_Playtest_M1", "x" * 60, 5):
            self.assertIsNotNone(check(bad), bad)

    def test_profile_build_changes_only_generated_config(self):
        with tempfile.TemporaryDirectory() as folder:
            project = temp_project(folder, with_ids(CONFIG))
            plain, _ = packager.build(project)
            data, sources, report = packager.build_profile("playtest", project)
            self.assertEqual(report.errors, [])
            self.assertNotEqual(plain, data)
            self.assertEqual(project.parent.joinpath("src/shared/Config.luau").read_text(encoding="utf-8"), with_ids(CONFIG))
            packaged = verify_release.config_from_place(data)
            self.assertIn('ProfileDataStoreName = "BeDino_Playtest_M1_v1"', packaged)
            self.assertEqual(verify_release.verify_place(data, "playtest").errors, [])
            self.assertTrue(verify_release.verify_place(plain, "playtest").errors)
            self.assertEqual(packager.build(project, lambda _path, source: source)[0], plain)

    def test_built_place_with_forbidden_flag_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            project = temp_project(folder, with_value(CONFIG, "PaidRandomItemsEnabled", "true"))
            data, _ = packager.build(project)
            errors = verify_release.verify_place(data, "default").errors
            self.assertTrue(any(e.startswith("PaidRandomItemsEnabled") for e in errors))

    def test_studio_guard_detection(self):
        with tempfile.TemporaryDirectory() as folder:
            server = Path(folder)
            (server / "Bad.luau").write_text("local wallet = Config.StudioTestWalletEnabled\n", encoding="utf-8")
            (server / "Good.luau").write_text(
                "local localPreview = RunService:IsStudio() and game.GameId == 0 and Config.StudioLocalProfilesEnabled\n"
                "if localPreview and Config.StudioTestWalletEnabled then end\n", encoding="utf-8")
            errors = verify_release.studio_guard_errors(server)
            self.assertEqual(len(errors), 1)
            self.assertIn("Bad.luau", errors[0])

    def test_current_delivery_passes_default_release_check(self):
        errors, _ = verify_release.run("default")
        self.assertEqual(errors, [])


class LowPolyProfileTests(unittest.TestCase):
    """docs/107: playtest ships the cheap low-poly dinos, default keeps them off."""

    def test_default_requires_false_playtest_sets_true(self):
        rules = {p: {r.key: r for r in profiles.rules_for(p)} for p in ("default", "playtest")}
        self.assertEqual((rules["default"]["LowPolyDinos"].mode, rules["default"]["LowPolyDinos"].value), ("require", False))
        self.assertEqual((rules["playtest"]["LowPolyDinos"].mode, rules["playtest"]["LowPolyDinos"].value), ("set", True))

    def test_default_source_with_flag_on_fails(self):
        report = profiles.verify_source(with_value(CONFIG, "LowPolyDinos", "true"), "default")
        self.assertTrue(any("LowPolyDinos" in e for e in report.errors))


class LoadHarnessTests(unittest.TestCase):
    def test_harness_embeds_real_repository(self):
        script = verify_load.harness()
        self.assertIn('["src/server/ProfileRepository"]', script)
        self.assertIn("function ProfileRepository.claimChest", script)

    def test_projection_matches_budget_formula(self):
        result = verify_load.projection(8, 400)
        self.assertEqual(result["budget"], 140)
        # BD-044: one write per egg at 1 s reveals busts the budget; 10-egg hatch pages fit.
        self.assertGreater(verify_load.projection(8, 400, page_size=1)["ratio"], 1.0)
        self.assertLess(result["ratio"], 1.0)
        self.assertLess(verify_load.projection(12, 400)["ratio"], 1.0)
        self.assertEqual(verify_load.projection(12, 40)["budget"], 180)

    def test_gate_flags_problems(self):
        clean = {"crashes": 0, "failures": {}, "queueDrops": 0, "undrainedEggs": 0, "leasedAtEnd": 0,
                 "ratioA": 0.5, "ratioB": 0.2, "peakWindowA": 70, "budgetA": 140, "peakWindowB": 10, "budgetB": 80,
                 "maxKeyBytesPerMinute": 200000, "maxProfileBytes": 15000}
        self.assertEqual(verify_load.gate(clean), [])
        self.assertEqual(len(verify_load.gate(dict(clean, failures={"claim:save_failed": 1}, ratioA=1.2))), 2)


if __name__ == "__main__":
    unittest.main()
