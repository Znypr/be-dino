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
        self.assertEqual(len(changed), 17)  # +RunTelemetryEnabled (BD-426), +ClassMovementEnabled (BD-423), +CaveHub (owner 2026-10-16), +PlaytestFeedbackEnabled (docs/128), +5 docs/157: Objectives, Combat, SpecialFoods, PerDinoCosmetics, FastTravelPerk
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


class PlaytestOnFlagTests(unittest.TestCase):
    """docs/157 (owner directive 2026-10-18): the playtest turns the built player-facing features on; the default build (Build 020 mirror) keeps them off."""

    ON = ("ObjectivesEnabled", "CombatEnabled", "SpecialFoodsEnabled", "PerDinoCosmeticsEnabled", "FastTravelPerk",
          "IdentityPersistentEnabled", "IdentityFusionPreviewEnabled", "CaveHub", "ClassMovementEnabled", "LowPolyDinos")

    def test_playtest_sets_each_feature_true_and_default_requires_it_false(self):
        playtest = {r.key: r for r in profiles.rules_for("playtest")}
        default = {r.key: r for r in profiles.rules_for("default")}
        for key in self.ON:
            self.assertEqual((playtest[key].mode, playtest[key].value), ("set", True), key)
            self.assertEqual((default[key].mode, default[key].value), ("require", False), key)

    def test_the_playtest_build_writes_them_and_the_committed_source_is_untouched(self):
        rewritten, report = profiles.apply_profile(with_ids(CONFIG), "playtest")
        self.assertEqual(report.errors, [])
        values = {k: v[-1][1] for k, v in profiles.config_entries(rewritten).items()}
        committed = {k: v[-1][1] for k, v in profiles.config_entries(CONFIG).items()}
        for key in self.ON:
            self.assertIs(values[key], True, key)
            self.assertIs(committed[key], False, key)  # src/ is never modified: the default build and Build 020 behaviour are unchanged

    def test_the_default_profile_refuses_each_of_them(self):
        for key in self.ON:
            report = profiles.verify_source(with_value(with_ids(CONFIG), key, "true"), "default")
            self.assertTrue(any(e.startswith(key) for e in report.errors), key)


class PlaytestStayOffTests(unittest.TestCase):
    """docs/157: the flags the playtest keeps off are REQUIRED false (a local edit before a playtest build fails the build), each with a reason."""

    OFF = ("GiftClaimEnabled", "GiftingEnabled", "AdminGiftsEnabled", "FoodPickupAtMouth", "PredationAtMouth", "HatchV2", "HatchV2Preview",
           "SecretSpeciesEnabled", "DinoSkinsEnabled", "PaidRandomItemsEnabled", "CrystalPacksEnabled", "ChestTestGrantEnabled",
           "CollectionTestGrantEnabled", "MutationTestSetupEnabled", "SecurityTestHarnessEnabled", "ArtTestHarnessEnabled",
           "QaOverlayEnabled", "DemoDirectorEnabled", "DuplicateSettlementProbe", "AutoOpenRequiresPass")

    def test_playtest_requires_each_flag_false_with_a_reason(self):
        rules = {r.key: r for r in profiles.rules_for("playtest")}
        for key in self.OFF:
            self.assertEqual((rules[key].mode, rules[key].value), ("require", False), key)
            self.assertTrue(rules[key].reason.strip(), key)

    def test_the_movement_guard_window_is_not_a_release_rule(self):
        for name in ("default", "playtest", "all-on-rehearsal"):
            self.assertFalse([r for r in profiles.rules_for(name) if r.key == "MovementGuardWindowEnabled"], name)

    def test_committed_source_passes_playtest_off_flags(self):
        report = profiles.verify_source(with_ids(CONFIG), "playtest")
        self.assertFalse([e for e in report.errors if any(e.startswith(k) for k in self.OFF)], report.errors)

    def test_flipping_any_off_flag_fails_playtest(self):
        for key in self.OFF:
            report = profiles.verify_source(with_value(with_ids(CONFIG), key, "true"), "playtest")
            self.assertTrue(any(key in e for e in report.errors), key)

    def test_playtest_build_refuses_a_flipped_off_flag(self):
        for key in self.OFF:
            _, report = profiles.apply_profile(with_value(with_ids(CONFIG), key, "true"), "playtest")
            self.assertTrue(any(key in e for e in report.errors), key)

    def test_every_false_boolean_is_decided(self):
        """A new false flag must be a playtest ON rule, a playtest required-false rule, or be listed here with the reason it is neither."""
        decided = {r.key for r in profiles.rules_for("playtest")}
        neither: dict = {}  # nothing is exempt: every false boolean is a playtest rule
        for key, found in profiles.config_entries(CONFIG).items():
            if found[-1][1] is False:
                self.assertTrue(key in decided or key in neither, f"{key} is false in Config and has no playtest rule (docs/157)")


class OldMutatePathClosedTests(unittest.TestCase):
    """docs/155 s6 item 1 / docs/157: the 50-copy MutateSpecies shortcut is refused on the server while the identity fusion path is on."""

    def test_the_handler_returns_before_it_reads_anything_when_fusion_is_on(self):
        text = (ROOT / "src/server/MutationService.luau").read_text(encoding="utf-8")
        handler = text.index("mutate.OnServerEvent:Connect")
        guard = text.index("Config.IdentityFusionPreviewEnabled == true", handler)
        self.assertIn('"fusion_moved"', text[guard:guard + 200])
        self.assertLess(guard, text.index("invalid_species", handler))
        self.assertLess(guard, text.index("profileRepository.mutateSpecies", handler))


class StreamingProfileTests(unittest.TestCase):
    """BD-502 gate 4: the build writes Workspace streaming properties per profile; shipped profiles keep them off."""

    def workspace_project(self, folder):
        project = temp_project(folder, with_ids(CONFIG))
        spec = json.loads(project.read_text())
        spec["tree"]["Workspace"] = {"$className": "Workspace"}
        project.write_text(json.dumps(spec))
        return project

    def test_shipped_profiles_have_streaming_off(self):
        for name in ("default", "playtest"):
            self.assertFalse(profiles.streaming_for(name).enabled, name)
            self.assertEqual(profiles.workspace_properties(name), [], name)
            self.assertEqual(profiles.streaming_config_errors(name), [], name)

    def test_scratch_profile_turns_it_on_with_the_proposal_radii(self):
        setting = profiles.streaming_for("playtest-streaming")
        self.assertEqual((setting.enabled, setting.scratch, setting.target_radius, setting.min_radius), (True, True, 256, 128))
        self.assertEqual(profiles.streaming_config_errors("playtest-streaming"), [])
        # same release rules as the playtest, so the game behaves as the playtest build
        self.assertEqual(profiles.PROFILES["playtest-streaming"], profiles.PROFILES["playtest"])

    def test_build_writes_workspace_properties_only_when_on(self):
        with tempfile.TemporaryDirectory() as folder:
            project = self.workspace_project(folder)
            off, _, off_report = packager.build_profile("playtest", project)
            on, _, on_report = packager.build_profile("playtest-streaming", project)
            self.assertEqual((off_report.errors, on_report.errors), ([], []))
            self.assertNotIn(b"StreamingEnabled", off)
            self.assertFalse(verify_release.workspace_streaming_from_place(off)["enabled"])
            actual = verify_release.workspace_streaming_from_place(on)
            self.assertEqual((actual["enabled"], actual["target_radius"], actual["min_radius"], actual["integrity_mode"]), (True, 256, 128, 0))
            self.assertEqual(verify_release.streaming_place_errors(off, "playtest")[0], [])
            self.assertEqual(verify_release.streaming_place_errors(on, "playtest-streaming")[0], [])

    def test_verify_release_rejects_streaming_in_a_shipped_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            project = self.workspace_project(folder)
            on, _, _ = packager.build_profile("playtest-streaming", project)
            errors, warnings = verify_release.streaming_place_errors(on, "playtest")
            self.assertTrue(any("StreamingEnabled" in e and "declares False" in e for e in errors), errors)
            self.assertTrue(any("SCRATCH" in w for w in verify_release.streaming_place_errors(on, "playtest-streaming")[1]))

    def test_shipped_profile_may_opt_in_only_with_a_gate_naming_existing_evidence(self):
        original = profiles.STREAMING["playtest"]
        try:
            profiles.STREAMING["playtest"] = profiles.Streaming(enabled=True)
            self.assertTrue(profiles.streaming_config_errors("playtest"))
            profiles.STREAMING["playtest"] = profiles.Streaming(enabled=True, gate="BD-502:docs/does-not-exist.md")
            self.assertTrue(any("does not exist" in e for e in profiles.streaming_config_errors("playtest")))
            profiles.STREAMING["playtest"] = profiles.Streaming(enabled=True, gate="BD-502:docs/147-streaming-experiment-2026-10-17.md")
            self.assertEqual(profiles.streaming_config_errors("playtest"), [])
            profiles.STREAMING["playtest"] = profiles.Streaming(enabled=True, scratch=True)
            self.assertTrue(any("cannot be marked scratch" in e for e in profiles.streaming_config_errors("playtest")))
        finally:
            profiles.STREAMING["playtest"] = original

    def test_bad_radii_are_rejected(self):
        original = profiles.STREAMING["playtest-streaming"]
        try:
            profiles.STREAMING["playtest-streaming"] = profiles.Streaming(enabled=True, scratch=True, target_radius=100, min_radius=200)
            self.assertTrue(profiles.streaming_config_errors("playtest-streaming"))
            profiles.STREAMING["playtest-streaming"] = profiles.Streaming(enabled=True, scratch=True, integrity_mode="Nope")
            self.assertTrue(profiles.streaming_config_errors("playtest-streaming"))
        finally:
            profiles.STREAMING["playtest-streaming"] = original


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
                 "maxKeyBytesPerMinute": 200000, "maxProfileBytes": 15000, "ops": {"claim": 12, "settle": 10}}
        self.assertEqual(verify_load.gate(clean), [])
        self.assertEqual(len(verify_load.gate(dict(clean, failures={"claim:save_failed": 1}, ratioA=1.2))), 2)
        # docs/152: a run that never hatched would leave the hatch writes out of every request number
        self.assertTrue(any("no hatch claim" in p for p in verify_load.gate(dict(clean, ops={"settle": 10}))))


if __name__ == "__main__":
    unittest.main()
