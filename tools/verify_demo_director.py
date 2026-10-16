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
    for path in (ROOT / "src/server").glob("*.luau"):
        assert "DemoDirector" not in path.read_text(encoding="utf-8"), f"server script {path.name} must not reference the director"
    boot = (ROOT / "src/client/Bootstrap.client.luau").read_text(encoding="utf-8")
    assert "DemoDirector" not in boot, "director must not be wired into Bootstrap"
    shots_src = (ROOT / "src/shared/DemoShots.luau").read_text(encoding="utf-8")
    for remote in re.findall(r"(\w+) = true", re.search(r"AllowedRemotes = \{(.*?)\}", shots_src).group(1)):
        server = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "src/server").glob("*.luau"))
        assert f'"{remote}"' in server, f"allow-listed remote {remote} must be an existing server test remote"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runner", default="luau")
    args = ap.parse_args()
    static_checks()
    print(run_luau(args.runner))
    print("demo director checks OK")


if __name__ == "__main__":
    main()
