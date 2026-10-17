"""BD-608 (docs/151): adversarial remote audit, offline. Every server entry point a client can reach is attacked with the real handler code.

Runs the REAL src/server modules (ProfileRepository and its parts, ChestService, CollectionService, MutationService, ProgressionService, FusionService,
ObjectiveService, GiftService, AdminService, AdminGifts, RunLifecycle, HubTravelService, LeapService, ClassMovementService, CombatService,
FeedbackService, QaService, VisualTestService, DemoTriggerService, PrivateState, CaveShowOff, the ProcessReceipt path) inside the
verify_load virtual-clock harness style (mock DataStore with latency, the per-server request budget, failed writes and lost acknowledgements).
tools/remote_fuzz.luau is the harness, tools/remote_fuzz_cases*.luau the scenarios:

  slot-fuzz         a valid request for every handler, then every argument slot replaced by 50+ hostile values (NaN, inf, huge, wrong
                    type, 100 KB strings, deep and wide tables, another player's instance), extra arguments, no arguments
  empty-handed      every pair of hostile values at every handler for a player with nothing: nothing is paid out
  races             40 parallel requests with ONE token, 60 with distinct tokens, claim/mutate/fuse/buy/use/upgrade in parallel, with the
                    write budget on, off, and on a lossy store (failed writes + lost acknowledgements)
  storm-N-hostile   N of 12 players flood every handler for a minute while the others play: honest refusals are MEASURED, hostile writes are
                    bounded, an honest run settlement always commits, no DataStore queue drop
  published-pins    the remote inventory of a published playtest server is exactly the reviewed list; DemoTrigger, QaMark, CombatBite,
                    ObjectiveAction, GiftAction, AdminGiftAction, PreviewDinosaurArt and the three test grants do not exist there
  fusion-and-isolation / cross-player   another player's ids, eggs, nests and variants change nothing; no answer or attribute leaks
  run-lifecycle / movement-handlers / show-off-prompt / dormant-* / sequence-N   the run, leap, dash, hub travel, the pedestal prompt, the
                    handlers behind off flags (switched on) and random request sequences on a lossy store
  claim-lost-ack    BD-609: a lost acknowledgement in the middle of a hatch page no longer drops the page's reveals
  findings          reproductions printed as FINDING lines for the audit document (not failures)

Static checks: every OnServerEvent / OnServerInvoke / Triggered / ProcessReceipt site in src/server is on the reviewed list below; every
reviewed entry has a row in docs/151; the debug flags are pinned off in tools/release_profiles.py; the Studio-only guards are still in source.

    python tools/verify_remote_fuzz.py --runner /path/to/luau            # everything (about a minute)
    python tools/verify_remote_fuzz.py --runner /path/to/luau --only races
    python tools/verify_remote_fuzz.py --runner /path/to/luau --selftest  # five mutants must each make a named check fail

Limits: mocks prove validation, ordering, idempotency and budget behaviour of the server code. They do not prove Roblox networking, the
client-owned character physics (speed and teleport limits are Studio work), real DataStore latency, or anything about a phone.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (BD-607: the repository is split into parts)
import release_profiles  # noqa: E402
import verify_load  # noqa: E402

DOC = "docs/151-remote-audit-2026-10-17.md"

# The reviewed remote inventory of a PUBLISHED playtest server. A new remote fails the "published-pins" check until it is reviewed,
# added here and given a row in the audit document. ProgressionResult and RareHatch are server -> client only (no handler).
EXPECTED_PLAYTEST_REMOTES = [
    "AdminAction", "ClaimChest", "ClaimNest", "ClassDash", "ClassGlide", "ClientWorldReady", "EquipSpecies", "FusionAction", "HubTravel",
    "MutateSpecies", "PlaytestFeedback", "PrivateState", "ProgressionAction", "ProgressionResult", "RareHatch", "RequestEndRun",
    "RequestLeap", "RequestStartRun", "SetRevealSkip", "SetSettings",
]
SERVER_TO_CLIENT_ONLY = ["ProgressionResult", "RareHatch"]
# Behind a flag that is off in every release profile (or Studio-only): they exist only when the flag is on.
DORMANT_REMOTES = ["ObjectiveAction", "GiftAction", "AdminGiftAction", "SkinAction", "CombatBite", "QaMark", "PreviewDinosaurArt", "DemoTrigger",
                   "TestGrantChests", "TestGrantSpecies", "TestSetMutationCopies"]
OTHER_ENTRY_POINTS = ["ProcessReceipt", "ShowOffSpot"]

# (file, kind) -> number of code sites. Counted with the regexes below (comments are stripped first).
REVIEWED_SITES = {
    ("AdminGifts.luau", "invoke"): 1, ("AdminService.luau", "invoke"): 1, ("DemoTriggerService.luau", "invoke"): 1,
    ("FusionService.luau", "invoke"): 1, ("GiftService.luau", "invoke"): 1, ("HubTravelService.luau", "invoke"): 1,
    ("ObjectiveService.luau", "invoke"): 1, ("SkinService.luau", "invoke"): 1,
    ("ChestService.luau", "event"): 5, ("ClassMovementService.luau", "event"): 2, ("CollectionService.luau", "event"): 2,
    ("CombatService.luau", "event"): 1, ("FeedbackService.luau", "event"): 1, ("LeapService.luau", "event"): 1,
    ("MutationService.luau", "event"): 2, ("PrivateState.luau", "event"): 1, ("ProgressionService.luau", "event"): 1,
    ("QaService.luau", "event"): 1, ("RunLifecycle.luau", "event"): 3, ("VisualTestService.luau", "event"): 1,
    ("CaveShowOff.luau", "prompt"): 1, ("Bootstrap.server.luau", "receipt"): 1,
}
SITE_PATTERNS = {
    "invoke": re.compile(r"\.OnServerInvoke\s*="),
    "event": re.compile(r"\.OnServerEvent\s*:\s*Connect\s*\("),
    "prompt": re.compile(r"\.Triggered\s*:\s*Connect\s*\("),
    "receipt": re.compile(r"\.ProcessReceipt\s*="),
}

# Debug and dormant switches that must be false in EVERY release profile (tools/release_profiles.py is the single place).
PINNED_OFF = ["ChestTestGrantEnabled", "CollectionTestGrantEnabled", "MutationTestSetupEnabled", "SecurityTestHarnessEnabled",
              "ArtTestHarnessEnabled", "QaOverlayEnabled", "DemoDirectorEnabled", "ObjectivesEnabled", "GiftingEnabled",
              "AdminGiftsEnabled", "GiftClaimEnabled", "DinoSkinsEnabled"]
# Source guards that keep a debug path out of a published server even if a flag were flipped by mistake.
GUARDS = [
    ("src/server/DemoTriggerService.luau", r"RunService:IsStudio\(\)\s+and\s+game\.GameId\s*==\s*0\s+and\s+Config\.DemoDirectorEnabled\s*==\s*true", "DemoTrigger needs unpublished Studio AND the flag"),
    ("src/server/ProfileRepository.luau", r"demoActive\s*=\s*localPreview\s+and\s+Config\.DemoDirectorEnabled\s*==\s*true", "the demo profile writes need localPreview AND the flag"),
    ("src/server/ChestService.luau", r"if\s+Config\.ChestTestGrantEnabled\s*==\s*true\s+then\s+getRemote\(folder,\s*\"TestGrantChests\"\)", "TestGrantChests exists only with its flag"),
    ("src/server/CollectionService.luau", r"if\s+Config\.CollectionTestGrantEnabled\s*==\s*true\s+then\s+getRemote\(folder\s*::\s*Folder,\s*\"TestGrantSpecies\"\)", "TestGrantSpecies exists only with its flag"),
    ("src/server/MutationService.luau", r"if\s+Config\.MutationTestSetupEnabled\s*==\s*true\s+then\s+getRemote\(folder,\s*\"TestSetMutationCopies\"\)", "TestSetMutationCopies exists only with its flag"),
    ("src/server/QaService.luau", r"if\s+not\s+Config\.QaOverlayEnabled\s+then\s+return\s+end", "QaMark exists only with its flag"),
    ("src/server/AdminService.luau", r"if\s+admins\[player\]\s*~=\s*true\s+then\s+return\s+false,\s*\"not_admin\"\s+end", "AdminAction refuses a non-admin first"),
]

# The real FallRecovery moves a Humanoid with engine physics; the handlers only need "the character is placed at the CFrame".
FALL_RECOVERY_STUB = "\n".join([
    "return {teleport = function(player, character, cf)",
    "    local root = character:FindFirstChild(\"HumanoidRootPart\")",
    "    if root then root.Position = cf.Position root.CFrame = cf end",
    "end, check = function() return false end, start = function() end, reset = function() end}",
])
CASE_FILES = ["remote_fuzz_cases.luau", "remote_fuzz_cases2.luau", "remote_fuzz_cases3.luau", "remote_fuzz_cases4.luau", "remote_fuzz_cases5.luau", "remote_fuzz_tail.luau"]
# Every scenario that a full run must have produced (a deleted scenario must not pass silently).
SCENARIOS = ["slot-fuzz", "sanity", "empty-handed", "races", "races-no-write-budget", "races-lossy-store", "storm-1-hostile-of-12",
             "storm-2-hostile-of-12", "storm-4-hostile-of-12", "published-pins", "test-grants-flag-on", "test-grants-one-flag",
             "demo-trigger-studio", "dormant-handlers", "fusion-and-isolation", "cross-player", "run-lifecycle", "findings",
             "show-off-prompt", "dormant-valid", "movement-handlers", "claim-lost-ack", "sequence-11", "sequence-4242", "sequence-90210", "skin-action"]


def lua_literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def playtest_overrides() -> dict:
    source = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    rewritten, report = release_profiles.apply_profile(source, "playtest")
    return dict(report.applied)


def build_script(only: str = "", mutants: dict | None = None, storm: int = 60) -> str:
    """mutants: {"src/server/X": (old, new)} applied to the embedded source (selftest only)."""
    sources = []
    for folder in ("src/server", "src/shared"):
        for path in sorted((ROOT / folder).glob("*.luau")):
            # generated art tables are skipped: no handler reads them
            text = "return {}" if path.stat().st_size > verify_load.MAX_EMBED_BYTES else path.read_text(encoding="utf-8")
            if path.stem == "FallRecovery":
                text = FALL_RECOVERY_STUB
            key = f"{folder}/{path.stem}"
            if mutants and key in mutants:
                old, new = mutants[key]
                if text.count(old) < 1:
                    raise SystemExit(f"selftest mutant target not found in {key}: {old!r}")
                text = text.replace(old, new)
            sources.append(f"[{verify_load.json.dumps(key)}] = {verify_load.long_string(text)}")
    head = (ROOT / "tools" / "remote_fuzz.luau").read_text(encoding="utf-8")
    cases = "\n".join((ROOT / "tools" / name).read_text(encoding="utf-8") for name in CASE_FILES)
    table = lambda d: "{" + ", ".join(f"{k} = {lua_literal(v)}" for k, v in sorted(d.items())) + "}"
    head = head.replace("__SOURCES__", "{\n" + ",\n".join(sources) + "\n}")
    head = head.replace("__PLAYTEST__", table(playtest_overrides()))
    head = head.replace("__FLAGS_ON__", "{}")
    head = head.replace("__EXPECTED__", "{" + ", ".join(lua_literal(n) for n in EXPECTED_PLAYTEST_REMOTES) + "}")
    head = head.replace("__ONLY__", lua_literal(only)).replace("__STORM__", str(storm))
    return head + "\n" + cases


def run_luau(runner: str, only: str = "", mutants: dict | None = None, keep: str | None = None, storm: int = 60):
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "remote_fuzz.luau"
        script.write_text(build_script(only, mutants, storm), encoding="utf-8")
        if keep:
            Path(keep).write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
        completed = subprocess.run([runner, str(script)], capture_output=True, text=True)
    checks, report, times, done = [], [], {}, None
    for line in completed.stdout.splitlines():
        if line.startswith("CHECK|"):
            _, state, name, detail = (line.split("|", 3) + [""])[:4]
            checks.append((state == "PASS", name, detail))
        elif line.startswith("REPORT|"):
            report.append(line[7:])
        elif line.startswith("TIME|"):
            _, name, seconds = line.split("|")
            times[name] = float(seconds)
        elif line.startswith("DONE|"):
            done = line
    return completed, checks, report, times, done


# ------------------------------------------------------------------ static checks
def strip_comments(text: str) -> str:
    text = re.sub(r"--\[(=*)\[.*?\]\1\]", "", text, flags=re.S)
    lines = []
    for line in text.splitlines():
        at = 0
        while True:
            at = line.find("--", at)
            if at < 0:
                break
            if line[:at].count('"') % 2 == 0:  # not inside a string
                line = line[:at]
                break
            at += 2
        lines.append(line)
    return "\n".join(lines)


# Every profile write (a `store:UpdateAsync(` in ProfileRepository) is classified. A new write must be put in one set on purpose:
ROUTINE_WRITES_WITH_ADMIT = {"fuseDinosaurs", "claimNest", "equipSpecies", "claimChest", "mutateSpecies", "progressionAction", "objectiveFlush", "objectiveClaim"}
ADMIT_AT_CALLER = {"writeRevealSkip", "writeSettings"}  # setRevealSkip / setSettings / the coalescing flush call admit() first
PRIORITY_WRITES = {"load", "commitRunSettlement", "purchase", "renew", "release", "applyGifts"}  # never starved by a flooding client
FLAG_GATED_WRITES = {"grantCollectionTestSpecies", "grantChestTest", "setMutationTestCopies", "demoGrantEggs", "demoEquip", "demoAddCrystals"}
KNOWN_UNBUDGETED = {"applySkin": "BD-618 (i): flag off; limited by SkinService's own 10-per-10-s window"}
NO_LEASE_CHECK = {"load"}  # load ACQUIRES the lease


def write_problems() -> list[str]:
    """Every profile write is lease-checked and either budgeted or deliberately not (docs/151 section 3)."""
    problems: list[str] = []
    lines = profile_sources.repository_text().splitlines()  # the main file followed by every part (docs/150)
    func, start = None, 0
    seen: set[str] = set()
    for i, line in enumerate(lines):
        m = re.match(r"^(?:local )?function (?:ProfileRepository\.)?(\w+)", line)
        if m:
            func, start = m.group(1), i
        if "store:UpdateAsync(" in line and not line.strip().startswith("--") and func:
            seen.add(func)
            body = "\n".join(lines[start:i])
            if func not in NO_LEASE_CHECK and "ownSession(" not in "\n".join(lines[i:i + 16]):
                problems.append(f"static: ProfileRepository.{func} writes the profile without an ownSession (lease) check")
            if func in ROUTINE_WRITES_WITH_ADMIT:
                if "admit(" not in body:
                    problems.append(f"static: ProfileRepository.{func} is a routine write and no longer calls admit() before the store request")
            elif func not in ADMIT_AT_CALLER | PRIORITY_WRITES | FLAG_GATED_WRITES | set(KNOWN_UNBUDGETED):
                problems.append(f"static: ProfileRepository.{func} is a new profile write: classify it in verify_remote_fuzz.py (budgeted, priority or flag-gated) and add it to docs/151")
    for name in ROUTINE_WRITES_WITH_ADMIT | ADMIT_AT_CALLER | PRIORITY_WRITES | FLAG_GATED_WRITES | set(KNOWN_UNBUDGETED):
        if name not in seen:
            problems.append(f"static: classified write {name} no longer exists in ProfileRepository (update the lists)")
    return problems


def static_problems() -> list[str]:
    problems: list[str] = write_problems()
    counted: dict[tuple[str, str], int] = {}
    for path in sorted((ROOT / "src/server").glob("*.luau")):
        text = strip_comments(path.read_text(encoding="utf-8"))
        for kind, pattern in SITE_PATTERNS.items():
            n = len(pattern.findall(text))
            if n:
                counted[(path.name, kind)] = n
    for key, n in sorted(counted.items()):
        want = REVIEWED_SITES.get(key)
        if want is None:
            problems.append(f"static: {key[0]} has {n} {key[1]} handler site(s) that are not on the reviewed list (review it, add it to REVIEWED_SITES and give it a row in {DOC})")
        elif want != n:
            problems.append(f"static: {key[0]} has {n} {key[1]} site(s), reviewed {want} (a handler was added or removed: review it and update REVIEWED_SITES and {DOC})")
    for key in REVIEWED_SITES:
        if key not in counted:
            problems.append(f"static: reviewed site {key} no longer exists (update REVIEWED_SITES and {DOC})")
    doc = ROOT / DOC
    if not doc.is_file():
        problems.append(f"static: {DOC} is missing")
    else:
        rows = [line for line in doc.read_text(encoding="utf-8").splitlines() if line.startswith("|")]
        for name in EXPECTED_PLAYTEST_REMOTES + DORMANT_REMOTES + OTHER_ENTRY_POINTS:
            if name in SERVER_TO_CLIENT_ONLY:
                continue  # no handler to review
            if not any(f"`{name}`" in row for row in rows):
                problems.append(f"static: {DOC} has no table row for `{name}`")
    # release profiles: every debug switch is a `require false` rule in the common set
    rules = {r.key: r for r in release_profiles.COMMON_RULES}
    for key in PINNED_OFF:
        r = rules.get(key)
        if r is None or r.mode != "require" or r.value is not False:
            problems.append(f"static: tools/release_profiles.py does not pin {key} to false in every profile")
    for profile in ("default", "playtest"):
        combat = [r for r in release_profiles.PROFILES[profile] if r.key == "CombatEnabled"]
        if not combat or combat[0].mode != "require" or combat[0].value is not False:
            problems.append(f"static: profile {profile} does not pin CombatEnabled to false")
    config = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    for key in PINNED_OFF + ["CombatEnabled"]:
        if not re.search(rf"^\s*{key}\s*=\s*false\b", config, flags=re.M):
            problems.append(f"static: Config.luau does not set {key} = false")
    for rel, pattern, label in GUARDS:
        if not re.search(pattern, (ROOT / rel).read_text(encoding="utf-8")):
            problems.append(f"static: guard missing - {label} ({rel})")
    demo_guards = len(re.findall(r'if\s+not\s+demoActive\s+then\s+return\s+false,\s*"disabled"\s+end', profile_sources.repository_text()))
    if demo_guards != 3:
        problems.append(f"static: demoGrantEggs, demoEquip and demoAddCrystals must each start with the demoActive guard (found {demo_guards} of 3)")
    return problems


# ------------------------------------------------------------------ self test: mutants must be caught
MUTANTS = [
    ("lost acknowledgement drops the hatch page again (BD-609 reverted)", "claim-lost", {
        "src/server/ProfileEggs": ("if #pageOutcomes > 0 and not (duplicateOutcome and revealBuffer[player] and #revealBuffer[player] > 0) then",
                                         "if not duplicateOutcome and #pageOutcomes > 0 then")},
     "claim-lost-ack: every credited egg after the head is still waiting"),
    ("ClaimNest stops validating its argument", "slot-fuzz", {
        "src/server/ChestService": ('if typeof(nestId) ~= "string" or #nestId < 1 or #nestId > 80 then', "if #nestId < 1 or #nestId > 80 then")},
     "slot-fuzz: no error escaped from any handler"),
    ("a purchase token no longer makes the purchase idempotent", "races", {
        "src/server/ProfileShop": ("local existing=findOperation(profile,operationId)\n            if existing then\n                if existing.outcome.action~=action",
                                         "local existing=nil\n            if existing then\n                if existing.outcome.action~=action")},
     "races: 20 buyEgg with ONE token buy one egg"),
    ("a test-grant remote is created without its flag", "published-pins", {
        "src/server/ChestService": ('if Config.ChestTestGrantEnabled == true then getRemote(folder, "TestGrantChests") else nil', 'getRemote(folder, "TestGrantChests")')},
     "published-pins: TestGrantChests does not exist on a published server"),
    ("AdminAction answers a non-admin", "published-pins", {
        "src/server/AdminService": ('if admins[player] ~= true then return false, "not_admin" end', "")},
     "published-pins: a non-admin gets not_admin"),
]


def selftest(runner: str) -> int:
    failed = 0
    for label, only, mutants, expect in MUTANTS:
        completed, checks, report, times, done = run_luau(runner, only, mutants)
        broken = [name for ok, name, _ in checks if not ok]
        hit = any(expect in name for name in broken)
        print(f"  mutant {'CAUGHT' if hit else 'MISSED'}: {label} -> {len(broken)} failing check(s)" + ("" if hit else f"; wanted '{expect}', got {broken[:3]}"))
        if not hit:
            failed += 1
    if failed:
        print(f"Remote fuzz self-test FAILED: {failed} mutant(s) were not caught")
        return 1
    print(f"Remote fuzz self-test passed: all {len(MUTANTS)} mutants were caught")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True, help="path to the pinned luau executable")
    parser.add_argument("--only", default="", help="run only scenarios whose name contains this text")
    parser.add_argument("--keep", help="write the generated script here")
    parser.add_argument("--storm-seconds", type=int, default=60, help="length of the request storms (default 60; 120 gives the numbers quoted in docs/151)")
    parser.add_argument("--selftest", action="store_true", help="prove the checks bite: five source mutants must each fail a named check")
    parser.add_argument("--verbose", action="store_true", help="print every check")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest(args.runner)
    problems = static_problems()
    completed, checks, report, times, done = run_luau(args.runner, args.only, None, args.keep, args.storm_seconds)
    if done is None:
        print(completed.stdout[-3000:])
        print(completed.stderr[-3000:])
        print("Remote fuzz did not complete.")
        return 1
    failures = [(name, detail) for ok, name, detail in checks if not ok]
    scenarios = {name.split(":")[0] for _, name, _ in checks}
    if not args.only:
        for scenario in SCENARIOS:
            if scenario not in scenarios:
                problems.append(f"scenario {scenario} produced no checks")
    for line in report:
        if args.verbose or line.startswith("FINDING") or "hostile=" in line or "malformed" in line or "pair combinations" in line:
            print("  " + line)
    if args.verbose:
        for ok, name, detail in checks:
            print(f"  {'PASS' if ok else 'FAIL'} {name} {detail[:160]}")
    for name, detail in failures:
        print(f"FAIL: {name} {detail[:400]}")
    for problem in problems:
        print(f"FAIL: {problem}")
    if failures or problems or completed.returncode != 0:
        print(f"Remote fuzz FAILED: {len(failures)} failing check(s), {len(problems)} static/scenario problem(s)")
        return 1
    handlers = len(EXPECTED_PLAYTEST_REMOTES) - len(SERVER_TO_CLIENT_ONLY) + len(DORMANT_REMOTES)
    print(f"Remote fuzz passed: {len(checks)} checks in {len(scenarios)} scenarios, {handlers} remote handlers + "
          f"{len(OTHER_ENTRY_POINTS)} other entry points reviewed, {len(REVIEWED_SITES)} handler files; {sum(times.values()):.0f} s of CPU")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
