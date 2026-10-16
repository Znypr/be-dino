"""Session 1 smoke (docs/125, BD-317): offline end-to-end simulation of the first friends playtest.

Builds the generated-place config with the PLAYTEST profile rules (tools/release_profiles.py applied to src/shared/Config.luau,
plus the owner's playtest values CaveHub = true and FastTravelPerk = true), then runs the REAL server modules (ProfileRepository,
RunLifecycle, LeaveCoordinator, RewardMath, PrivateState, ChestService, RareHatchService, TelemetryService, HubTravelService
and the pure shared rules) inside the verify_load virtual-clock harness (mock DataStore with latency, same as
tools/verify_multiplayer_sim.py). tools/session1_smoke.luau is the scenario:

  4 players join and each equips a species; 5-minute runs of food pickups at the docs/119 rate (food only, nobody eats anybody);
  one player is eaten (eggs kept), one exits home; each run settles exactly once; about 15 eggs each are revealed one by one;
  a rare hatch goes through RareHatchService (celebration, one rate-limited announcement); nests incl. overflow to crystals;
  crystals buy an aura and the Fast travel perk, HubTravel then works; goals panel counts; telemetry events; a second run;
  a rejoin keeps perk, nests, crystals and the UserId-keyed cooldowns. It asserts invariants and prints a short report.

Limits: mocks prove transaction, ordering and rule behaviour only, not Roblox networking, physics, real DataStore latency or
a phone (docs/111 s6). Predation itself (PredationService) needs a physics world: the eaten player ends through the same
RunLifecycle.tryEnd(..., "Predation") call it uses.

    python tools/verify_session1_smoke.py --runner /path/to/luau
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
import release_profiles  # noqa: E402
import verify_load  # noqa: E402
import verify_multiplayer_sim as mp  # noqa: E402

FALL_RECOVERY_STUB = (
    "return {teleport = function(player, character, cf)\n"
    "    local root = character:FindFirstChild(\"HumanoidRootPart\")\n"
    "    if root then root.Position = {X = cf.x, Y = cf.y, Z = cf.z} end\n"
    "end, check = function() return false end, start = function() end}\n"
)

# Mirrors of FoodService / Bootstrap wiring the scenario relies on: if these change the smoke must be revisited.
STATIC = [
    ("src/server/FoodService.luau", r"FoodCatchRules\.award\(candidate\.gained[\s\S]{0,300}RunEggTags\.nextScore\(before,whole,Config\.MaxCatchScore,Config\.RunEggMaxPerRun\)",
     "FoodService still turns pickups into catches with FoodCatchRules.award + RunEggTags.nextScore"),
    ("src/server/Bootstrap.server.luau", r"Telemetry\.runSettled\(player, reason, runSeconds, settledOutcome\)", "Bootstrap still reports settled runs to telemetry"),
    ("src/server/ProfileRepository.luau", r"RareHatchService\.record\(player, committedOutcome\)", "publishHatch still hands settled hatches to RareHatchService"),
]


def lua_literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def playtest_overrides() -> tuple[dict, list[str]]:
    source = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    _, report = release_profiles.apply_profile(source, "playtest")
    overrides = dict(report.applied)
    # docs/125 / owner 2026-10-16: the cave hub is in session 1. Only add what the profile does not already set.
    for key in ("CaveHub", "FastTravelPerk"):
        overrides.setdefault(key, True)
    notes = [e for e in report.errors if "PlaytestUniverseId" not in e and "PlaytestPlaceId" not in e]
    return overrides, notes


def food_kinds() -> str:
    text = (ROOT / "src/server/FoodService.luau").read_text(encoding="utf-8")
    rows = re.findall(r'\{id = "(\w+)", weight = (\d+), points = (\d+),', text)
    if len(rows) < 4:
        raise SystemExit("could not read the food kinds from FoodService.luau")
    return "{" + ", ".join(f'{{id = "{i}", weight = {w}, points = {p}}}' for i, w, p in rows[:4]) + "}"


def build_harness(overrides: dict) -> str:
    marker_at = verify_load.HARNESS.index(mp.HEAD_MARKER)
    head = mp.patch_head(verify_load.HARNESS[:marker_at])

    def swap(old: str, new: str) -> None:
        nonlocal head
        if head.count(old) != 1:
            raise SystemExit(f"harness patch target changed in verify_load.py: {old!r}")
        head = head.replace(old, new)

    # Modules are loaded before the mocks exist: look Instance/workspace up lazily, and expose print/warn to the scenario.
    swap("workspace = server.workspace, Instance = server.Instance,", "")
    swap("{__index = getfenv(0)}))\n        local result = chunk()",
         "{__index = function(_, k) if k == \"Instance\" then return server.Instance elseif k == \"workspace\" then return server.workspace end return getfenv(0)[k] end}))\n        local result = chunk()")
    swap("warn = function() M.warnings += 1 end, Random = Random, print = function() end}",
         "warn = function(...) M.warnings += 1 if SMOKE_WARN then SMOKE_WARN(...) end end, Random = Random, print = function(...) if SMOKE_PRINT then SMOKE_PRINT(...) end end}")
    # A real string round trip for JSONEncode/JSONDecode (settings, genes and the like are stored as strings).
    swap("JSONEncode = function(_, v) return deepcopy(v) end, JSONDecode = function(_, v) return deepcopy(v) end},",
         "JSONEncode = function(_, v) JSON_N += 1 JSON_REG[JSON_N] = deepcopy(v) return \"J#\" .. JSON_N end,\n"
         "            JSONDecode = function(_, s) if s == \"[]\" or s == \"{}\" then return {} end local id = type(s) == \"string\" and string.match(s, \"^J#(%d+)$\") "
         "if not id then error(\"JSONDecode: not a JSON string\") end return deepcopy(JSON_REG[tonumber(id)]) end},")
    head = "local JSON_REG, JSON_N = {}, 0\n" + head

    sources = []
    for folder in ("src/server", "src/shared"):
        for path in sorted((ROOT / folder).glob("*.luau")):
            if path.stat().st_size > verify_load.MAX_EMBED_BYTES:
                continue
            text = FALL_RECOVERY_STUB if path.stem == "FallRecovery" else path.read_text(encoding="utf-8")
            sources.append(f"[{verify_load.json.dumps(f'{folder}/{path.stem}')}] = {verify_load.long_string(text)}")
    head = head.replace("__SOURCES__", "{\n" + ",\n".join(sources) + "\n}")
    body = (ROOT / "tools" / "session1_smoke.luau").read_text(encoding="utf-8")
    table = "{" + ", ".join(f"{k} = {lua_literal(v)}" for k, v in sorted(overrides.items())) + "}"
    body = body.replace("__PLAYTEST__", table).replace("__FOOD_KINDS__", food_kinds())
    return "local SCENARIO_FAIL_RATE = 0\n" + head + "\n" + body


def static_checks() -> list[str]:
    problems = []
    for rel, pattern, label in STATIC:
        if not re.search(pattern, (ROOT / rel).read_text(encoding="utf-8")):
            problems.append(f"static: {label} ({rel})")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True, help="path to the pinned luau executable")
    parser.add_argument("--verbose", action="store_true", help="print every passing check")
    args = parser.parse_args(argv)
    overrides, notes = playtest_overrides()
    problems = static_checks() + [f"playtest profile: {n}" for n in notes]
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "session1.luau"
        script.write_text(build_harness(overrides), encoding="utf-8")
        completed = subprocess.run([args.runner, str(script)], capture_output=True, text=True)
    lines = completed.stdout.splitlines()
    done = [line for line in lines if line.startswith("DONE|")]
    if completed.returncode != 0 or not done:
        print(completed.stdout[-4000:])
        print(completed.stderr[-4000:])
        print("Session 1 smoke did not complete.")
        return 1
    total, failed = (int(x) for x in done[0].split("|")[1:3])
    shown = ("ReleaseProfile", "CaveHub", "FastTravelPerk", "RunTelemetryEnabled", "IdentityPersistentEnabled")
    print("Session 1 smoke report (playtest profile: " + ", ".join(f"{k}={v}" for k, v in sorted(overrides.items()) if k in shown) + ")")
    for line in lines:
        if line.startswith("REPORT|"):
            print("  " + line[7:])
        elif line.startswith("CHECK|FAIL|"):
            _, _, name, detail = line.split("|", 3)
            print(f"[FAIL] {name} ({detail})")
        elif args.verbose and line.startswith("CHECK|PASS|"):
            print("[pass] " + line.split("|", 3)[2])
    for problem in problems:
        print("[FAIL] " + problem)
    ok = failed == 0 and not problems
    print(f"Session 1 smoke {'passed' if ok else 'FAILED'}: {total - failed}/{total} checks, {len(problems)} static problem(s).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
