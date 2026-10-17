#!/usr/bin/env python3
"""Static guards for the switch-on rehearsal (docs/152). No Luau needed.

    python tools/verify_switch_on.py

  1. The all-on-rehearsal profile: scratch (never shipped), keeps CrystalPacksEnabled and PaidRandomItemsEnabled pinned false, and
     turns EVERY boolean Config flag that is off in the committed Config on, unless it is listed below as excluded WITH a reason.
     A new built-but-off flag therefore fails this check until it is added to REHEARSAL_ON (tools/release_profiles.py) or excluded here.
  2. Remote names are unique across src/server (ChestService-style getRemote() destroys a remote of another class with the same name,
     so a collision silently deletes the other feature's remote).
  3. Every `Config.X` read in src exists in Config.luau (a typo reads nil and silently switches a feature off).
  4. Every `require(script.Parent.Y)` in src/server and src/client names a module that exists next to the script (the flag-gated lazy
     requires are the ones an offline harness never loads).
  5. Documented exclusivity and ordering rules that a flag combination relies on (each is a text rule, checked where it lives).
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_playtest  # noqa: E402
import release_profiles as profiles  # noqa: E402

PROFILE = "all-on-rehearsal"

# Boolean Config flags that are false in the committed Config and stay false in the rehearsal, with the reason.
EXCLUDED = {
    "CrystalPacksEnabled": "paid: Robux crystal packs (docs/43); the rehearsal never opens the paid line",
    "PaidRandomItemsEnabled": "paid: random items for Robux (docs/43)",
    "CollectionTestGrantEnabled": "test-only species grant",
    "ChestTestGrantEnabled": "test-only egg grant",
    "MutationTestSetupEnabled": "test-only copy setup",
    "SecurityTestHarnessEnabled": "security test harness",
    "ArtTestHarnessEnabled": "art preview harness",
    "QaOverlayEnabled": "owner phone QA overlay, measurement builds only",
    "DemoDirectorEnabled": "trailer director, Studio-only",
    "HatchV2Preview": "Studio-only preview toggle with placeholders",
    "DuplicateSettlementProbe": "historical settlement probe",
    "AutoOpenRequiresPass": "a tuning switch, not a feature",
}

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def config_source() -> str:
    return (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")


def check_profile() -> None:
    source = config_source()
    entries = profiles.config_entries(source)
    if PROFILE not in profiles.PROFILES:
        fail(f"profile {PROFILE!r} is missing from tools/release_profiles.py")
        return
    rewritten, report = profiles.apply_profile(source, PROFILE)
    for error in report.errors:
        fail(f"{PROFILE}: {error}")
    after = profiles.config_entries(rewritten)
    setting = profiles.streaming_for(PROFILE)
    if not setting.scratch:
        fail(f"{PROFILE} must be a scratch profile (Streaming(..., scratch=True)): it is never published or uploaded")
    if PROFILE in release_playtest.shipped_profiles():
        fail(f"{PROFILE} is listed as a shipped profile")
    if profiles.streaming_config_errors(PROFILE):
        fail(f"{PROFILE}: {profiles.streaming_config_errors(PROFILE)}")
    for flag in release_playtest.PAID_FLAGS:
        if after[flag][-1][1] is not False:
            fail(f"{PROFILE} turns {flag} on: the paid line stays closed")
        if not any(rule.key == flag and rule.mode == "require" and rule.value is False for rule in profiles.rules_for(PROFILE)):
            fail(f"{PROFILE} must require {flag} = false (a rule, so the build fails if a local edit turns it on)")
    for flag in ("CollectionTestGrantEnabled", "ChestTestGrantEnabled", "MutationTestSetupEnabled", "SecurityTestHarnessEnabled",
                 "ArtTestHarnessEnabled", "QaOverlayEnabled", "DemoDirectorEnabled", "HatchV2Preview"):
        if after[flag][-1][1] is not False:
            fail(f"{PROFILE} turns the test/demo switch {flag} on")
    for key, why in profiles.REHEARSAL_ON:
        if key not in entries:
            fail(f"REHEARSAL_ON names {key} but Config.luau has no such key")
        elif after[key][-1][1] is not True:
            fail(f"{PROFILE} does not turn {key} on ({why})")
    # Completeness: every committed-false boolean is on in the rehearsal, or excluded with a reason.
    for key, found in sorted(entries.items()):
        value = found[-1][1]
        if value is not False:
            continue
        if after[key][-1][1] is True:
            continue
        if key not in EXCLUDED:
            fail(f"Config.{key} is false and stays false in {PROFILE}: add it to REHEARSAL_ON in tools/release_profiles.py, or to "
                 "EXCLUDED in tools/verify_switch_on.py with the reason (a new built-but-off feature must be rehearsed)")
    for key in EXCLUDED:
        if key not in entries:
            fail(f"EXCLUDED lists {key} but Config.luau has no such key")
        elif after[key][-1][1] is True:
            fail(f"EXCLUDED lists {key} but {PROFILE} turns it on")


def server_files() -> list[Path]:
    return sorted((ROOT / "src/server").glob("*.luau"))


def check_remote_names() -> None:
    seen: dict[str, list[str]] = {}

    def add(name: str, where: str) -> None:
        seen.setdefault(name, []).append(where)

    admin_gift = re.search(r'RemoteName = "(\w+)"', (ROOT / "src/shared/AdminGiftRules.luau").read_text(encoding="utf-8"))
    for path in server_files():
        text = path.read_text(encoding="utf-8")
        variables = {m.group(1) for m in re.finditer(r"\b(\w+)\s*=\s*(?:\w+\s+or\s+)?Instance\.new\(\"Remote(?:Event|Function)\"\)", text)}
        for m in re.finditer(r"\b(\w+)\.Name\s*=\s*\"(\w+)\"", text):
            if m.group(1) in variables:
                add(m.group(2), path.name)
        for m in re.finditer(r"getRemote\([^,)]*,\s*\"(\w+)\"\)", text):
            add(m.group(1), path.name)
        if "PageRules.RemoteName" in text and admin_gift:
            add(admin_gift.group(1), path.name)
    if len(seen) < 20:
        fail(f"remote-name scan found only {len(seen)} names; the scan pattern no longer matches the code")
    for name, where in sorted(seen.items()):
        if len(where) > 1:
            fail(f"remote name {name!r} is created in {', '.join(where)}: a second creator replaces or destroys the first")


def check_config_reads() -> None:
    keys = set(profiles.config_entries(config_source()))
    for folder in ("src/server", "src/client", "src/shared"):
        for path in sorted((ROOT / folder).glob("*.luau")):
            text = path.read_text(encoding="utf-8")
            if not re.search(r"local (?:Config|GameConfig) = require\([^)\n]*\bShared\.Config\)|local (?:Config|GameConfig) = require\(script\.Parent\.Config\)", text):
                continue
            for m in re.finditer(r"(?<![\w.])(?:Config|GameConfig)\.([A-Za-z_]\w*)", text):
                if m.group(1) not in keys:
                    fail(f"{path.relative_to(ROOT).as_posix()} reads Config.{m.group(1)} which Config.luau does not define (nil: a typo switches the feature off)")


def check_lazy_requires() -> None:
    for folder in ("src/server", "src/client"):
        names = {p.stem for p in (ROOT / folder).glob("*.luau")}
        names |= {p.name.split(".")[0] for p in (ROOT / folder).glob("*.luau")}
        for path in sorted((ROOT / folder).glob("*.luau")):
            for m in re.finditer(r"require\(script\.Parent\.(\w+)\)", path.read_text(encoding="utf-8")):
                if m.group(1) not in names:
                    fail(f"{path.relative_to(ROOT).as_posix()} requires script.Parent.{m.group(1)} but {folder}/{m.group(1)}.luau does not exist")


def between(text: str, start: str, end: str) -> str:
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:b if b > a else len(text)]


def repository_text() -> str:
    """ProfileRepository and the Profile*.luau modules it was split into (BD-607): the transactions live in all of them."""
    paths = [ROOT / "src/server/ProfileRepository.luau"] + sorted((ROOT / "src/server").glob("Profile*.luau"))
    return chr(10).join(dict.fromkeys(p.read_text(encoding="utf-8") for p in paths))


def check_rules() -> None:
    repo = repository_text()
    # Gifts and objectives never share a transaction: the gift claim is its own UpdateAsync and reports nothing to ObjectiveService.
    gifts = between((ROOT / "src/server/ProfileGifts.luau").read_text(encoding="utf-8"), "function ProfileRepository.applyGifts", chr(10) + "end" + chr(10))
    if not gifts:
        fail("ProfileRepository.applyGifts not found")
    elif "objectives()" in gifts or "ObjectiveService" in gifts:
        fail("applyGifts calls ObjectiveService: a gift would count inside the gift transaction (objective hooks run only AFTER their own commit)")
    # Every objective hook is a post-commit call behind the flag (full table: verify_objective_hooks); here only the count of call sites.
    sites = len(re.findall(r"objectives\(\)\.", repo))
    guards = len(re.findall(r"Config\.ObjectivesEnabled == true", repo))
    if sites < 5 or guards < sites:
        fail(f"the repository modules have {sites} objective hook sites but {guards} ObjectivesEnabled guards")
    # CombatEnabled replaces instant predation, so PredationAtMouth is moot while combat is on (documented in docs/152).
    predation = (ROOT / "src/server/PredationService.luau").read_text(encoding="utf-8")
    if "if Config.CombatEnabled then return end" not in predation:
        fail("PredationService no longer returns while CombatEnabled: PredationAtMouth + CombatEnabled would both act")
    # The fast-travel perk needs the cave hub (HubTravel is not created without it).
    if not re.search(r'action==\"buyPerk\" and \(Config\.FastTravelPerk~=true or Config\.CaveHub~=true\)', repo):
        fail("buyPerk is no longer refused while FastTravelPerk or CaveHub is off")
    # The mouth rule is defined for the low-poly dinos only.
    food = (ROOT / "src/server/FoodService.luau").read_text(encoding="utf-8")
    if "Config.FoodPickupAtMouth == true and lowPolyOn()" not in food:
        fail("FoodService: FoodPickupAtMouth must stay tied to LowPolyDinos")
    # A kit food clone that raises must not leave an error string where a model is expected (docs/152).
    if "if not ok then model = nil end" not in food:
        fail("FoodService: a raising Resources.clone must set model = nil before :Destroy() is called")
    # The load harness must really hatch (BD-360 moved NextChestId out of Player attributes).
    load = (ROOT / "tools/verify_load.py").read_text(encoding="utf-8")
    if 'PrivateState.get(p, "NextChestId")' not in load:
        fail("tools/verify_load.py reads NextChestId from player attributes again: no hatch claim would ever run (docs/152)")


def main() -> int:
    check_profile()
    check_remote_names()
    check_config_reads()
    check_lazy_requires()
    check_rules()
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"Switch-on checks FAILED: {len(errors)} problem(s).")
        return 1
    print(f"Switch-on checks passed: {PROFILE} is a scratch profile, the paid line is closed, every off flag is rehearsed or excluded "
          f"({len(EXCLUDED)} excluded), remote names are unique, every Config read exists, lazy requires resolve, flag-order rules hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
