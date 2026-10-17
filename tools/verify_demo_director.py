"""Trailer clip director checks (docs/133).

* Config.DemoDirectorEnabled exists and is false; release_profiles pins it off in the default AND playtest profiles.
* The client director returns before doing anything unless RunService:IsStudio() and Config.DemoDirectorEnabled, and fires only
  remotes from the DemoShots allow-list (existing, separately gated test harness remotes); no server script mentions the director.
* Every tools/demo/shots/*.json passes the real Luau DemoShots.validate in the pinned runtime; bad lists are rejected; easing and
  camera maths behave. Not Studio evidence.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (docs/150: ProfileRepository plus its parts)
sys.path.insert(0, str(ROOT / "tools"))
import release_profiles  # noqa: E402


def lua(value, indent=0):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "{" + ",".join(lua(v) for v in value) + "}"
    return "{" + ",".join(f"[{json.dumps(k)}]={lua(v)}" for k, v in value.items()) + "}"


BODY = r'''
local function approx(a, b) return math.abs(a - b) < 1e-6 end
assert(S.ease("linear", 0.3) == 0.3 and S.ease(nil, 2) == 1 and S.ease("inQuad", -1) == 0)
for name in S.Easings do assert(approx(S.ease(name, 0), 0) and approx(S.ease(name, 1), 1), "easing endpoints " .. name) end
assert(approx(S.ease("inOutSine", 0.5), 0.5) and approx(S.ease("inOutCubic", 0.5), 0.5))
local p = S.cameraPose({kind = "dolly", from = {0, 0, 0}, to = {10, 0, 0}, look = {0, 0, 5}}, 0.5)
assert(approx(p[1], 5))
local o1 = S.cameraPose({kind = "orbit", center = {0, 0, 0}, radius = 10, height = 2, startDeg = 0, endDeg = 90}, 1)
assert(approx(o1[1], 0) and approx(o1[3], 10) and approx(o1[2], 2))
local push = S.cameraPose({kind = "pushin", from = {0, 0, 0}, look = {0, 0, 20}, distance = 8}, 1)
assert(approx(push[3], 8))
local tp, tl = S.cameraPose({kind = "track", offset = {0, 5, 10}}, 0.2, {1, 2, 3})
assert(approx(tp[1], 1) and approx(tp[2], 7) and approx(tp[3], 13) and approx(tl[2], 4))

for name, list in SHOTS do
    local err = S.validate(list)
    assert(err == nil, "shot list " .. name .. ": " .. tostring(err))
end

local good = function() return {version = 1, name = "x", aspect = "16:9", shots = {{duration = 3, camera = {kind = "static", pos = {0, 0, 0}, look = {0, 0, 1}}}}} end
assert(S.validate(good()) == nil)
local function bad(mutate, label) local l = good() mutate(l) assert(S.validate(l) ~= nil, "should reject: " .. label) end
bad(function(l) l.aspect = "4:3" end, "aspect")
bad(function(l) l.version = 2 end, "version")
bad(function(l) l.shots = {} end, "empty shots")
bad(function(l) l.shots[1].duration = 0 end, "zero duration")
bad(function(l) l.shots[1].camera.kind = "crane" end, "camera kind")
bad(function(l) l.shots[1].camera.ease = "bounce" end, "easing")
bad(function(l) l.shots[1].title = string.rep("a", 41) end, "long title")
bad(function(l) l.shots[1].triggers = {{kind = "remote", at = 0, remote = "AdminGrantEverything"}} end, "remote not on allow-list")
bad(function(l) l.shots[1].triggers = {{kind = "teleport", at = 9}} end, "trigger time and target")
bad(function(l) l.shots = {{duration = 60, camera = good().shots[1].camera}, {duration = 60, camera = good().shots[1].camera}, {duration = 60, camera = good().shots[1].camera}, {duration = 1, camera = good().shots[1].camera}} end, "too long")
bad(function(l) l.shots[1].triggers = {{kind = "move", at = 0, seconds = 2}} end, "move needs dir")
bad(function(l) l.shots[1].triggers = {{kind = "glide", at = 0, seconds = 60}} end, "glide too long")
bad(function(l) l.shots[1].blackout = 3 end, "blackout not shorter than shot")
bad(function(l) l.hideChrome = "yes" end, "hideChrome type")
do
    local l = good()
    l.hideChrome = true
    l.shots[1].blackout = 1
    l.shots[1].triggers = {{kind = "move", at = 0, dir = {0, -1}, seconds = 2}, {kind = "jump", at = 1}, {kind = "glide", at = 1, seconds = 1}, {kind = "dash", at = 2}, {kind = "closeModal", at = 2}, {kind = "teleport", at = 0, pos = {0, 0, 0}, ground = true, face = {0, -1}}}
    assert(S.validate(l) == nil, tostring(S.validate(l)))
end
assert(S.SafeInsets["9:16"].y > S.SafeInsets["16:9"].y, "9:16 keeps more top/bottom room")
print("demo director luau OK")
'''


def run_luau(runner):
    shots = {}
    for path in sorted((ROOT / "tools/demo/shots").glob("*.json")):
        shots[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    assert {"hatching_showcase", "class_feel", "cave_tour", "weekly_update_template"} <= set(shots), "required shot lists missing"
    source = (ROOT / "src/shared/DemoShots.luau").read_text(encoding="utf-8")
    program = "local S = (function()\n" + source + "\nend)()\nlocal SHOTS = " + lua(shots) + "\n" + BODY
    with tempfile.NamedTemporaryFile("w", suffix=".luau", delete=False, encoding="utf-8") as f:
        f.write(program)
    result = subprocess.run([runner, f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if result.returncode != 0:
        raise SystemExit("Luau demo checks failed:\n" + result.stdout + result.stderr)
    return result.stdout.strip()


def static_checks():
    config = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    assert re.search(r"^    DemoDirectorEnabled = false,", config, re.M), "Config.DemoDirectorEnabled must exist and be false"
    for name in ("default", "playtest"):
        rules = [r for r in release_profiles.rules_for(name) if r.key == "DemoDirectorEnabled"]
        assert rules and rules[0].mode == "require" and rules[0].value is False, f"{name} profile must pin DemoDirectorEnabled off"
    client = (ROOT / "src/client/DemoDirector.client.luau").read_text(encoding="utf-8")
    head = client.split("local Players", 1)[0]
    assert "RunService:IsStudio()" in head and "return end" in head, "director must bail out outside Studio before doing anything"
    assert head.index("IsStudio") < head.index("DemoDirectorEnabled"), "Studio check first"
    assert re.search(r"Config\.DemoDirectorEnabled ~= true then return end", head), "director must bail out when the flag is off"
    # Server side (docs/133): only DemoTriggerService (+ the guarded demo* repository functions) may mention the flag.
    allowed_server = {"DemoTriggerService.luau", "ProfileRepository.luau", "ProfileTestGrants.luau", "Bootstrap.server.luau"}
    for path in (ROOT / "src/server").glob("*.luau"):
        if path.name not in allowed_server:
            assert "DemoDirector" not in path.read_text(encoding="utf-8"), f"server script {path.name} must not reference the director"
    service = (ROOT / "src/server/DemoTriggerService.luau").read_text(encoding="utf-8")
    start = service.split("function DemoTriggerService.start", 1)[1]
    first = start.split("\n", 2)[1].strip()
    assert first == "if not (RunService:IsStudio() and game.GameId == 0 and Config.DemoDirectorEnabled == true) then return end", \
        "service start() must bail out first unless unpublished Studio and the flag"
    assert start.index("then return end") < start.index('Instance.new("RemoteFunction")'), "remote must only be created after the guard"
    assert service.count('Instance.new("RemoteFunction")') == 1 and "RemoteEvent" not in service, "one RemoteFunction only"
    assert 'remote.Name = "DemoTrigger"' in service
    assert "player ~= owner" in service, "owner-local check"
    repo = profile_sources.repository_text()
    assert re.search(r"^local demoActive = localPreview and Config\.DemoDirectorEnabled == true", repo, re.M), "demoActive must require localPreview"
    assert re.search(r"^local localPreview = RunService:IsStudio\(\) and game\.GameId == 0 and Config\.StudioLocalProfilesEnabled", repo, re.M)
    demo_fns = re.findall(r"^function ProfileRepository\.(demo\w+)\(", repo, re.M)
    assert set(demo_fns) == {"demoGrantEggs", "demoEquip", "demoAddCrystals"}, demo_fns
    for name in demo_fns:
        body = repo.split(f"function ProfileRepository.{name}(", 1)[1].split("\n", 2)[1].strip()
        assert body == 'if not demoActive then return false, "disabled" end', f"{name} must check demoActive first"
    # docs/150: lines naming it = the declaration + the hand-over to the part + the part's local alias + the first line of each demo function
    assert len(re.findall(r"^.*demoActive.*$", repo, re.M)) == 3 + len(demo_fns), "demoActive used nowhere else"
    grant = repo.split("function ProfileRepository.demoGrantEggs", 1)[1].split("function ProfileRepository.demoEquip", 1)[0]
    assert "bankEggs(profileValue, batch, now)" in grant, "party eggs must use the real bankEggs path"
    # release gate: the flag is a Studio-local flag (guard enforced by verify_release) and a stray unguarded read is caught.
    assert "DemoDirectorEnabled" in release_profiles.STUDIO_LOCAL_FLAGS
    import verify_release
    assert verify_release.studio_guard_errors() == [], verify_release.studio_guard_errors()
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "Bad.luau").write_text("if Config.DemoDirectorEnabled then end\n", encoding="utf-8")
        assert verify_release.studio_guard_errors(Path(tmp)), "unguarded flag read must fail verify_release"
        Path(tmp, "Bad.luau").write_text("if RunService:IsStudio() and game.GameId == 0 and Config.DemoDirectorEnabled then end\n", encoding="utf-8")
        assert verify_release.studio_guard_errors(Path(tmp)) == []
    # shot lists: remote triggers only use DemoTrigger with a known request kind and valid egg specs.
    rarities = {"Common", "Uncommon", "Rare", "Epic", "Legendary"}
    for path in (ROOT / "tools/demo/shots").glob("*.json"):
        for shot in json.loads(path.read_text(encoding="utf-8"))["shots"]:
            for trig in shot.get("triggers", []):
                if trig["kind"] != "remote":
                    continue
                assert trig["remote"] == "DemoTrigger", f"{path.name}: only DemoTrigger"
                req = trig["args"][0]
                assert req["kind"] in {"hatchParty", "equipSpecies", "setWeather", "giveCrystals", "startRun"}, req
                if req["kind"] == "hatchParty":
                    assert 1 <= len(req["eggs"]) <= 60 and all(e["rarity"] in rarities for e in req["eggs"])
    boot = (ROOT / "src/client/Bootstrap.client.luau").read_text(encoding="utf-8")
    assert "DemoDirector" not in boot, "director must not be wired into Bootstrap"
    shots_src = (ROOT / "src/shared/DemoShots.luau").read_text(encoding="utf-8")
    allow = re.findall(r"(\w+) = true", re.search(r"AllowedRemotes = \{(.*?)\}", shots_src).group(1))
    assert allow == ["DemoTrigger"], allow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runner", default="luau")
    args = ap.parse_args()
    static_checks()
    print(run_luau(args.runner))
    print("demo director checks OK")


if __name__ == "__main__":
    main()
