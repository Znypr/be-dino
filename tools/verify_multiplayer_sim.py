"""BD-354 / BD-319 prep: offline 12-player multiplayer simulation (no Roblox servers, no Studio).

Runs the REAL src/server/ProfileRepository.luau, RunLifecycle.luau, LeaveCoordinator.luau, RewardMath.luau and the pure
shared modules CombatRules / NestQueue inside the pinned Luau runtime, on the verify_load.py scheduler (virtual clock,
cooperative coroutines, mocked DataStore with latency, transient failures, repeated transforms and the per-server
UpdateAsync budget). 12 mock players join, run, die, get eaten, settle, hatch, leave and rejoin concurrently, in several
orders. The body is tools/multiplayer_sim.luau; this file builds the harness, runs it and fails on any broken invariant:

  * every run settles at most once and credits its eggs exactly once, also when the player leaves mid-settlement
  * no duplicated egg id, no cross-player operation, leases released, no leaked/resurrected profile
  * a same-user rejoin is not broken by the old session's late release; a leave mid-load frees the lease
  * SaveFailed is recoverable and the run settlement of a leaving player is still committed
  * outcomes are identical for three different join/leave orderings (deterministic under reordering)
  * CombatRules: defeat and settle fire once per (userId, runId) for 12 players; NestQueue is per user and order independent
  * a join storm of 12 completes inside the DataStore budget
  * BD-358: one client spamming settings / reveal-skip / nest-claim remotes (3 x 10 Hz) cannot starve the 11 other players'
    settlements; its own key takes at most burst + 1 write/s; the latest preference is still saved (coalesced); any 60 s window
    stays under 60 + 10 x players requests; also at 30% store failure; a budget-off contrast run shows what the old code did
  * BD-359: a 15 s store outage loses nothing (12 settlements inside the retry window); a 60 s outage records SaveFailed
    pendings that the lease renew tick commits later (players respawn, nothing doubled); 12 players leaving over a 15 s outage
    settle and release inside the BindToClose bound; 20% and 40% failing stores credit every run exactly once

Limits: mocks prove transaction and ordering behaviour only. Roblox networking, replication, physics, real DataStore
latency, BindToClose timing and memory are NOT covered; docs/111 lists what the owner must still check in Studio.

    python tools/verify_multiplayer_sim.py --runner /path/to/luau
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
import verify_load  # noqa: E402

HEAD_MARKER = "-------------------------------------------------------------------- simulated players"
REPORT_MARKER = "-------------------------------------------------------------------- report"


def patch_head(head: str) -> str:
    def swap(old: str, new: str) -> None:
        nonlocal head
        if head.count(old) != 1:
            raise SystemExit(f"harness patch target changed in verify_load.py: {old!r}")
        head = head.replace(old, new)

    swap("local SCENARIOS = __SCENARIOS__", "local SCENARIOS = {}")
    swap("Players = {GetPlayers = function() return table.clone(server.players) end},", "Players = setmetatable({}, {__index = function(_, k) return server.PlayersService[k] end}),")
    swap("setfenv(chunk, setmetatable({script = n, game = server.game, require = load, task = task, os = vos,",
         "setfenv(chunk, setmetatable({script = n, game = server.game, require = load, task = task, os = vos, workspace = server.workspace, Instance = server.Instance,")
    swap('    server.Repository = load(node("src/server/ProfileRepository"))\n',
         '    server.require = load\n    server.Repository = load(node("src/server/ProfileRepository"))\n')
    return head


def build_harness() -> str:
    marker_at = verify_load.HARNESS.index(HEAD_MARKER)
    head = patch_head(verify_load.HARNESS[:marker_at])
    # BD-319 round 2: modules are loaded inside newServer, before boot() installs the mocks. A late-bound proxy lets a module loaded
    # early (PrivateState, required by ProfileRepository) see the mock workspace / Instance that boot() creates and a scenario may
    # replace. Done here and not in patch_head, because verify_session1_smoke patches the same text its own way.
    for old, new in (
        ("workspace = server.workspace, Instance = server.Instance,", "workspace = server.proxy('workspace'), Instance = server.proxy('Instance'),"),
        ("    local function load(n)" + chr(10), "    function server.proxy(name) return setmetatable({}, {__index = function(_, k) local target = server[name] return if target then target[k] else nil end}) end" + chr(10) + "    local function load(n)" + chr(10)),
    ):
        if head.count(old) != 1:
            raise SystemExit(f"harness patch target changed in verify_load.py: {old!r}")
        head = head.replace(old, new)
    sources = []
    for folder in ("src/server", "src/shared"):
        for path in sorted((ROOT / folder).glob("*.luau")):
            if path.stat().st_size > verify_load.MAX_EMBED_BYTES:
                continue
            sources.append(f"[{verify_load.json.dumps(f'{folder}/{path.stem}')}] = "
                           f"{verify_load.long_string(path.read_text(encoding='utf-8'))}")
    head = head.replace("__SOURCES__", "{\n" + ",\n".join(sources) + "\n}")
    body = (ROOT / "tools" / "multiplayer_sim.luau").read_text(encoding="utf-8")
    # BD-319 round 2: tools/multiplayer_cross_player.luau (2/4/8 players, cross-player leakage, per-client caps) runs in the
    # same chunk, just before the report, so it shares the scheduler, the mocks and the helpers of the body.
    cross = (ROOT / "tools" / "multiplayer_cross_player.luau").read_text(encoding="utf-8")
    if body.count(REPORT_MARKER) != 1:
        raise SystemExit("multiplayer_sim.luau lost its report marker")
    body = body.replace(REPORT_MARKER, cross + "\n" + REPORT_MARKER)
    return "local SCENARIO_FAIL_RATE = 0\n" + head + "\n" + body


STATIC = [
    ("src/server/Bootstrap.server.luau", r"LeaveCoordinator\.new\(", "Bootstrap builds the LeaveCoordinator"),
    ("src/server/Bootstrap.server.luau", r"Players\.PlayerRemoving:Connect\(leaving\.leave\)", "PlayerRemoving uses leaving.leave"),
    ("src/server/Bootstrap.server.luau", r"leaving\.leaveAll\(Players:GetPlayers\(\)\)[\s\S]{0,120}leaving\.waitIdle", "BindToClose leaves in parallel and waits"),
    ("src/server/Bootstrap.server.luau", r"leaving\.settlementFinished\(player\)\s*\n\s*return false", "a failed settlement still releases a departed player"),
    ("src/server/Bootstrap.server.luau", r"SessionBusy[\s\S]{0,200}task\.wait\(5\)", "load retries while another session holds the lease"),
    ("src/server/CombatService.luau", r"BiteCooldownSeconds[\s\S]{0,260}local candidates", "bite cooldown is checked before the O(players) scan"),
    ("src/server/ProgressionService.luau", r"pcall\(repository\.progressionAction", "the busy flag cannot stick after a thrown error"),
    # BD-319: replicated features added after BD-358.
    ("src/server/HubTravelService.luau", r"sessions\[player\] = session[\s\S]*PlayerRemoving:Connect\(function\(player\) sessions\[player\] = nil end\)", "HubTravel keeps one rate-limit session per player and frees it on leave"),
    ("src/server/HubTravelService.luau", r"select\(\"#\", \.\.\.\) ~= 1", "HubTravel refuses extra arguments"),
    ("src/server/HubTravelService.luau", r"hasPerk\(progress, \"fastTravel\"\)", "HubTravel reads the perk from the caller's own profile"),
    ("src/server/ChestService.luau", r"lastSettings, player, 0\.5[\s\S]{0,80}setSettings\(player, selection\)", "SetSettings is throttled per player and writes only the caller's profile"),
    ("src/server/ChestService.luau", r"CooldownMemory\.new\(120\)", "SetSettings throttle lives in UserId-keyed CooldownMemory that prunes itself (BD-363)"),
    ("src/server/ProfileRepository.luau", r"action==\"buyPerk\" and \(Config\.FastTravelPerk~=true or Config\.CaveHub~=true\)", "buyPerk is refused while the perk or cave flag is off"),
    ("src/server/RunLifecycle.luau", r"SetAttribute\(\"HubStation\", nil\)", "the public HubStation marker is cleared on respawn and run start"),
    ("src/server/Leaderboards.luau", r"Writes\.shouldWrite\(writeState,definition\.id,userId", "leaderboard writes go through the per-user write gate"),
    # BD-319 round 2: cross-player wiring that the offline cases above rely on.
    ("src/server/AdminService.luau", r"local function handle\(player: Player, action: any, a: any, b: any\): \(boolean, string\)\n    if admins\[player\] ~= true then return false, \"not_admin\" end", "the admin remote refuses non-admins before anything else"),
    ("src/server/AdminService.luau", r"admins\[player\] = nil lastRequest\[player\] = nil", "admin state is dropped when the player leaves"),
    ("src/server/FoodService.luau", r"RunEggTags\.apply\(events,weatherId,before,after,function\(\) return eventRandom:NextNumber\(\) end,adminMutationMultiplier\)", "the admin mutation scale reaches only the per-catch weather roll"),
    ("src/server/ProfileRepository.luau", r"ProgressionRules\.eventEgg\(nest\.weatherId, rng:NextNumber\(\)\)", "nest eggs roll at the shipped chance (no admin scale)"),
    ("src/server/RunLifecycle.luau", r"local runNestWeather: \{\[string\]: \{string\}\} = \{\}", "the nest weather ledger is server-only and keyed by run id"),
    ("src/server/RunLifecycle.luau", r"runNestWeather\[runId\] = nil\n    local killEggs", "settlement consumes (clears) the run's nest weather ledger"),
    ("src/server/Dinosaur.luau", r"caveHub = Config\.CaveHub == true, inHub = inHub, score = character:GetAttribute\(\"GrowthScore\"\)", "the drawn size is decided per character from its own position and attributes"),
]

# BD-319 round 2: these are client-side render caps. If a server script required them, a cap could become a count across players.
CLIENT_ONLY_MODULES = ("EffectsLod", "ContactShadowRules", "MomentRimPlan", "FxRecipes", "CameraOcclusion", "ConditionOverlays")


def static_checks() -> list[str]:
    problems = []
    for rel, pattern, label in STATIC:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if not re.search(pattern, text):
            problems.append(f"static: {label} ({rel})")
    for path in sorted((ROOT / "src/server").glob("*.luau")):
        text = path.read_text(encoding="utf-8")
        for name in CLIENT_ONLY_MODULES:
            if re.search(r"require\([^)\n]*\b" + name + r"\b", text):
                problems.append(f"static: server script {path.name} requires client render-cap module {name} (caps must stay per client)")
    repo = (ROOT / "src/server/ProfileRepository.luau").read_text(encoding="utf-8")
    # BD-358: routine remote-triggered writes are admitted through the per-player bucket; priority writes never are.
    parts = re.split(r"\n(?=function ProfileRepository\.)", repo)
    bodies = {}
    for part in parts:
        found = re.match(r"function ProfileRepository\.(\w+)", part)
        if found:
            bodies[found.group(1)] = part
    for name in ("fuseDinosaurs", "claimNest", "equipSpecies", "claimChest", "mutateSpecies", "progressionAction", "setSettings", "setRevealSkip"):
        if "admit(player)" not in bodies.get(name, ""):
            problems.append(f"static: routine write {name} is not admitted through the write budget")
    for name in ("commitRunSettlement", "renew", "release", "load", "purchase"):
        if "admit(" in bodies.get(name, ""):
            problems.append(f"static: priority write {name} must never use the routine write budget")
    if 'retrySettlement("run settlement"' not in repo:
        problems.append("static: run settlement does not use the longer retrySettlement policy")
    stale = re.findall(r"if not profiles\[player\] or updated\.revision *>= *profiles\[player\]\.revision then profiles\[player\] *= *updated end", repo)
    if len(stale) != 1:  # exactly one: ProfileRepository.load, which is the only place that may create the entry
        problems.append(f"static: {len(stale)} unguarded 'profiles[player] = updated' sites (expected 1, in load)")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True, help="path to the pinned luau executable")
    parser.add_argument("--verbose", action="store_true", help="print every passing check")
    args = parser.parse_args(argv)
    problems = static_checks()
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "multiplayer.luau"
        script.write_text(build_harness(), encoding="utf-8")
        completed = subprocess.run([args.runner, str(script)], capture_output=True, text=True)
    lines = completed.stdout.splitlines()
    done = [line for line in lines if line.startswith("DONE|")]
    if completed.returncode != 0 or not done:
        print(completed.stdout[-3000:])
        print(completed.stderr[-3000:])
        print("Multiplayer simulation did not complete.")
        return 1
    total, failed = (int(x) for x in done[0].split("|")[1:3])
    for line in lines:
        if line.startswith("METRIC|"):
            print("  " + line.replace("|", "  ", 1).replace("|", ": ", 1).replace("|", " = ", 1))
        elif line.startswith("CHECK|FAIL|"):
            _, _, scenario, name, detail = line.split("|", 4)
            print(f"[FAIL] {scenario}: {name} ({detail})")
        elif args.verbose and line.startswith("CHECK|PASS|"):
            _, _, scenario, name, _ = line.split("|", 4)
            print(f"[pass] {scenario}: {name}")
    for problem in problems:
        print("[FAIL] " + problem)
    ok = failed == 0 and not problems
    print(f"Multiplayer simulation {'passed' if ok else 'FAILED'}: {total - failed}/{total} checks, {len(problems)} static problem(s).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
