"""BD-1217: proof of the authored low-poly dino clips (eat, happy, look) in the pinned Luau runner.

    python tools/verify_lowpoly_clips.py --runner <luau.exe>

1. src/shared/LowPolyClips.luau is generated from tools/blender/dino_clips.py and up to date, and every key is inside the calm limits
   (tools/blender/gen_dino_clips_luau.py --check).
2. The real module, run bare: every clip starts and ends at rest, stays inside the limits between keys (no overshoot), a wing / flipper / arm
   roll mirrors by side, a neck follows the head at NeckShare, bob comes only from the root, an unknown clip or role gives all zero.
3. BD-1217 rig follow-up (Config.DinoRigClipsEnabled): the idle / walk / run LOOPS (Clips.Gait) are seamless (value and slope across the seam),
   bounded, never turn the body, wings or flippers; src/shared/LowPolyGait.luau blends them by speed (weights add to 1), phases the legs
   (left / right half a stride apart, diagonal pairs together), shortens Armored steps, holds tail up / head low in the run, is exactly rest
   under Reduce Motion, and its follow-through springs swing out, overshoot, settle, stay bounded on junk and reset under Reduce Motion.
   The flag ships false in Config, the playtest profile turns it on, Bootstrap carries none of it.
4. The animator plays them: LowPolyAnimator requires LowPolyClips, triggers eat / happy / look from the replicated attributes and clears the
   clip under Reduce Motion (amp 0). The full animator run with the clips loaded is tools/verify_motion_poses.py.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import gen_dino_clips_luau  # noqa: E402

BODY = r'''
local ns = DATA
local maxRad = MAX_DEG * math.pi / 180 + 1e-6
local o = Clips.new()
local names = {}
for name, clip in Clips.Data do
    table.insert(names, name)
    assert(Clips.length(name) == clip.length and clip.length > 0.5 and clip.length <= 4, name .. ": length")
    for _, role in {"root", "head", "neck", "tail", "arm", "leg", "wing", "flipper", "body"} do
        for _, side in {-1, 1} do
            for _, t in {0, clip.length, clip.length + 1, -1} do
                Clips.sample(name, role, side, t, o)
                assert(math.abs(o.pitch) + math.abs(o.yaw) + math.abs(o.roll) + math.abs(o.bob) + math.abs(o.fwd) < 1e-9, name .. "." .. role .. " not at rest at " .. t)
            end
            local steps = math.floor(clip.length * 120)
            for i = 0, steps do
                local t = clip.length * i / steps
                Clips.sample(name, role, side, t, o)
                for _, v in {o.pitch, o.yaw, o.roll} do assert(v == v and math.abs(v) <= maxRad, name .. "." .. role .. " angle over the limit at " .. t) end
                assert(o.bob >= -1e-9 and o.bob <= MAX_BOB + 1e-6, name .. " bob out of range at " .. t)
                assert(o.fwd >= -1e-9 and o.fwd <= MAX_FWD + 1e-6, name .. " fwd out of range at " .. t)
                if role ~= "head" then assert(o.fwd == 0, "fwd only on the head") end
                if role == "body" then assert(o.pitch == 0 and o.yaw == 0 and o.roll == 0, "the body never turns (bob moves it)") end
            end
        end
    end
end
table.sort(names)
assert(table.concat(names, ",") == "eat,happy,jump,land,look", "clips: " .. table.concat(names, ","))
-- side mirror and neck share
local a, b = Clips.new(), Clips.new()
Clips.sample("happy", "wing", -1, 0.2, a) Clips.sample("happy", "wing", 1, 0.2, b)
assert(b.roll > 0.3 and math.abs(a.roll + b.roll) < 1e-9, "a wing opens on both sides")
Clips.sample("happy", "leg", -1, 0.3, a) Clips.sample("happy", "leg", 1, 0.3, b)
assert(a.pitch ~= 0 and a.pitch == b.pitch, "legs swing together in the hop")
Clips.sample("eat", "head", 1, 0.3, a) Clips.sample("eat", "neck", 1, 0.3, b)
assert(a.pitch < -0.3 and math.abs(b.pitch - a.pitch * Clips.NeckShare) < 1e-9, "eat: nose down, neck follows at NeckShare")
assert(a.fwd > 0 and b.fwd == 0, "eat: only the head reaches forward")
Clips.sample("happy", "root", 1, 0.3, a)
assert(a.bob > 0.05 and a.pitch == 0, "happy hops (bob from the root)")
Clips.sample("look", "head", 1, 1.2, a)
assert(a.yaw > 0.3, "look turns the head")
Clips.sample("nope", "head", 1, 0.3, a)
assert(a.pitch == 0 and a.bob == 0, "unknown clip = rest")
Clips.sample("eat", "head", 1, 0 / 0, a)
assert(a.pitch == 0, "NaN time = rest")
print("clip checks passed")
'''

# BD-1217 rig follow-up: the locomotion loops (Clips.Gait) and the pure LowPolyGait module (Config.DinoRigClipsEnabled)
GAIT_BODY = r'''
-- ---------------------------------------------------------------------------------------------------------------- BD-1217 rig follow-up
-- the loops (LowPolyClips.Gait) and the pure LowPolyGait module
local o2 = Clips.new()
local loops = {}
for name, cyc in Clips.Gait do
    table.insert(loops, name)
    local L = cyc.length
    for _, role in {"root", "head", "neck", "tail", "arm", "leg", "body", "wing", "flipper"} do
        for _, side in {-1, 1} do
            -- seamless: value and slope match across the loop seam, and one loop later is the same pose
            Clips.sampleCycle(name, role, side, 0, o) Clips.sampleCycle(name, role, side, L, o2)
            for _, k in {"pitch", "yaw", "roll", "bob", "fwd"} do assert(math.abs(o[k] - o2[k]) < 1e-9, name .. "." .. role .. "." .. k .. " loop seam value") end
            local h = L * 1e-4
            Clips.sampleCycle(name, role, side, L - h, o) Clips.sampleCycle(name, role, side, L + h, o2)
            for _, k in {"pitch", "yaw", "roll", "bob", "fwd"} do
                assert(math.abs(o[k] - o2[k]) < 1e-3, name .. "." .. role .. "." .. k .. " jumps at the loop seam")
            end
            Clips.sampleCycle(name, role, side, 0.37 * L, o) Clips.sampleCycle(name, role, side, 3.37 * L, o2)
            assert(math.abs(o.pitch - o2.pitch) < 1e-9 and math.abs(o.yaw - o2.yaw) < 1e-9, name .. " repeats every loop")
            for i = 0, 240 do
                Clips.sampleCycle(name, role, side, L * i / 240, o)
                for _, v in {o.pitch, o.yaw, o.roll} do assert(v == v and math.abs(v) <= maxRad, name .. "." .. role .. " angle over the limit") end
                assert(o.bob >= -1e-9 and o.bob <= MAX_BOB + 1e-6, name .. " bob out of range")
                assert(o.fwd >= -1e-9 and o.fwd <= MAX_FWD + 1e-6, name .. " fwd out of range")
                if role == "body" or role == "wing" or role == "flipper" then
                    assert(o.pitch == 0 and o.yaw == 0 and o.roll == 0, name .. ": " .. role .. " has no loop (body never turns; wings / flippers keep the sine poses)")
                end
            end
        end
    end
end
table.sort(loops)
assert(table.concat(loops, ",") == "idle,run,walk", "loops: " .. table.concat(loops, ","))
assert(Clips.Gait.idle.clock == "time" and Clips.Gait.walk.clock == "stride" and Clips.Gait.run.clock == "stride", "clocks")
Clips.sampleCycle("walk", "leg", 1, 0 / 0, o)
assert(o.pitch == 0, "NaN loop time = rest")
Clips.sampleCycle("nope", "leg", 1, 0.2, o)
assert(o.pitch == 0, "unknown loop = rest")

local G = Gait
local P = G.sample
local out = {pitch = 0, roll = 0, yaw = 0, dy = 0, dz = 0, fwd = 0}
-- weights
for i = 0, 100 do
    local wi, ww, wr = G.weights(i / 100)
    assert(math.abs(wi + ww + wr - 1) < 1e-9 and wi >= 0 and ww >= 0 and wr >= 0, "weights add up to 1")
end
local wi, ww, wr = G.weights(0) assert(wi == 1 and ww == 0 and wr == 0, "standing = idle")
wi, ww, wr = G.weights(0.35) assert(ww == 1, "a walk at 0.35")
wi, ww, wr = G.weights(1) assert(wr == 1, "full speed = run")
wi, ww, wr = G.weights(0 / 0) assert(wi == 1, "NaN speed = idle")
-- uses
assert(G.uses("leg", "Ground") and G.uses("tail", "Fly") and G.uses("head", "Armored"), "ground, fly, armored use the loops")
assert(not G.uses("leg", "Water") and not G.uses("wing", "Fly") and not G.uses("flipper", "Ground") and not G.uses("body", "Ground"), "Water, wings, flippers, body keep the sine poses")
-- leg phasing: left / right half a stride apart, diagonal pairs of a quadruped together
local function legPitch(side, lead, phase) return P("leg", side, lead, 0, phase, 0.4, 1, 6, out, "Ground").pitch end
local alt, diag = 0, 0
for i = 0, 63 do
    local ph = i / 64 * 2 * math.pi
    alt = math.max(alt, math.abs(legPitch(-1, true, ph) - legPitch(1, true, ph + math.pi)))
    diag = math.max(diag, math.abs(legPitch(-1, true, ph) - legPitch(1, false, ph)))
end
assert(alt < 1e-9, "the right leg is the left leg half a stride later")
assert(diag < 1e-9, "left front and right back move together")
assert(math.abs(legPitch(-1, true, 0) - legPitch(1, true, 0)) > 0.5, "left and right legs are apart (opposite in the stride)")
-- walk vs run: the run swings wider... and the leg reaches forward when its loop starts
local walkMax, runMax = 0, 0
for i = 0, 63 do
    local ph = i / 64 * 2 * math.pi
    walkMax = math.max(walkMax, math.abs(P("leg", -1, true, 0, ph, 0.35, 1, 6, out, "Ground").pitch))
    runMax = math.max(runMax, math.abs(P("leg", -1, true, 0, ph, 1, 1, 6, out, "Ground").pitch))
end
assert(walkMax > math.rad(18) and runMax > walkMax, "the run swings wider than the walk: " .. walkMax .. " / " .. runMax)
local armoredMax = 0
for i = 0, 63 do armoredMax = math.max(armoredMax, math.abs(P("leg", -1, true, 0, i / 64 * 2 * math.pi, 1, 1, 6, out, "Armored").pitch)) end
assert(math.abs(armoredMax - runMax * G.ArmoredStride) < 1e-6, "Armored takes shorter steps")
-- the run holds the tail up and the head low (whole loop average)
local tailRun, headRun = 0, 0
for i = 0, 63 do
    tailRun += P("tail", 1, false, 0, i / 64 * 2 * math.pi, 1, 1, 6, out, "Ground").pitch
    headRun += P("head", 1, false, 0, i / 64 * 2 * math.pi, 1, 1, 6, out, "Ground").pitch
end
assert(tailRun < 0 and headRun < 0, "running: tail up (pitch < 0), nose down")
-- Reduce Motion, bounds, junk
for _, role in {"head", "neck", "tail", "arm", "leg", "body", "wing"} do
    for _, w in {0, 0.3, 0.7, 1} do
        for i = 0, 15 do
            local r = P(role, 1, true, i * 0.3, i * 0.7, w, 0, 6, out, "Ground")
            assert(r.pitch == 0 and r.yaw == 0 and r.roll == 0 and r.fwd == 0 and r.dy == 0 and r.dz == 0, "Reduce Motion = rest")
            r = P(role, -1, false, i * 0.3, i * 0.7, w, 1, 6, out, "Fly")
            for _, v in {r.pitch, r.yaw, r.roll} do assert(v == v and math.abs(v) <= G.MaxAngle, "bounded") end
            assert(r.fwd >= 0 and r.fwd <= G.PeckStuds, "head reach bounded")
        end
    end
    assert(G.bob(1, 1, 0.5, 0) == 0, "Reduce Motion: no bob")
end
local junk = P("leg", 1, true, 0 / 0, math.huge, 0 / 0, 1, 0 / 0, out, "Ground")
assert(junk.pitch == junk.pitch and junk.fwd == junk.fwd, "junk inputs are safe")
for i = 0, 200 do
    local b = G.bob(i * 0.05, i * 0.11, (i % 11) / 10, 1)
    assert(b >= 0 and b <= G.MaxBob, "bob never sinks the feet and stays small")
end
-- follow-through spring
local f = G.newFollow()
for _ = 1, 120 do G.stepFollow(f, 1 / 60, 3, 0, 0, 1) end
assert(f.tailYaw > 0.1 and f.headYaw > 0.05, "a left turn: tail out, head in")
local over = 0
for _ = 1, 180 do G.stepFollow(f, 1 / 60, 0, 0, 0, 1) over = math.min(over, f.tailYaw) end
assert(over < 0, "the tail swings past rest (follow-through)")
assert(math.abs(f.tailYaw) < 1e-3, "and settles")
G.stepFollow(f, 1 / 60, 0, 0, 40, 1)
local peak = 0
for _ = 1, 30 do G.stepFollow(f, 1 / 60, 0, 0, 0, 1) peak = math.max(peak, f.tailPitch) end
assert(peak > 0.05 and peak <= G.Follow.max, "a landing kicks the tail down, bounded")
for _ = 1, 20 do G.stepFollow(f, 1 / 0, 0 / 0, math.huge, -5, 1) end
for _, k in {"tailYaw", "tailPitch", "headYaw", "headPitch"} do assert(f[k] == f[k] and math.abs(f[k]) <= G.Follow.max, "junk keeps the springs bounded") end
G.stepFollow(f, 1 / 60, 3, 20, 30, 0)
for _, k in {"tailYaw", "tailPitch", "headYaw", "headPitch"} do assert(f[k] == 0 and f[k .. "V"] == 0, "Reduce Motion puts the springs at rest") end
local r = G.addFollow({tailYaw = 0.2, tailPitch = 0.1, headYaw = 0.1, headPitch = 0.05}, "neck", 1, {pitch = 0, roll = 0, yaw = 0, dy = 0, dz = 0, fwd = 0})
assert(math.abs(r.yaw - 0.1 * Clips.NeckShare) < 1e-9, "the neck follows the head at NeckShare")
r = G.addFollow({tailYaw = 0.2, tailPitch = 0.1, headYaw = 0.1, headPitch = 0.05}, "leg", 1, {pitch = 0, roll = 0, yaw = 0, dy = 0, dz = 0, fwd = 0})
assert(r.yaw == 0 and r.pitch == 0, "legs get no follow-through")
assert(math.abs(G.turnRate(3.1, -3.1, 0.1) - (2 * math.pi - 6.2) / 0.1) < 1e-6, "turn rate wraps across +-pi")
assert(G.turnRate(0, 1, 0) == 0 and G.turnRate(0 / 0, 1, 0.1) == 0, "turn rate junk = 0")
print("gait checks passed")
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runner", required=True)
    args = ap.parse_args()
    fails = []
    if gen_dino_clips_luau.main(["--check"]) != 0:
        fails.append("LowPolyClips.luau is out of date or a key breaks the limits")
    ns = gen_dino_clips_luau.load()
    clips = (ROOT / "src/shared/LowPolyClips.luau").read_text(encoding="utf-8")
    gait = (ROOT / "src/shared/LowPolyGait.luau").read_text(encoding="utf-8").replace("require(script.Parent.LowPolyClips)", "Clips")
    prelude = "local Clips = (function()\n%s\nend)()\nlocal Gait = (function()\n%s\nend)()\nlocal MAX_DEG, MAX_BOB, MAX_FWD = %r, %r, %r\nlocal DATA = nil\n" % (
        clips, gait, ns["MAX_DEG"], ns["MAX_BOB"], ns["MAX_FWD"])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "clips.luau"
        path.write_text(prelude + BODY.replace('print("clip checks passed")', 'print("clip checks passed")\ndo\n' + GAIT_BODY + '\nend'), encoding="utf-8")
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding="utf-8")
    print((result.stdout + result.stderr).strip())
    if result.returncode != 0 or "clip checks passed" not in result.stdout:
        fails.append("Luau clip checks")
    if "gait checks passed" not in result.stdout:
        fails.append("Luau gait checks (LowPolyGait, the loops)")
    anim = (ROOT / "src/client/LowPolyAnimator.client.luau").read_text(encoding="utf-8")
    for needle, why in [
        ("require(Shared.LowPolyClips)", "the animator loads the clips"),
        ('playClip(rig, "eat", now)', "eat plays when the dino eats"),
        ('playClip(rig, "happy", now)', "happy plays on growth / a new species"),
        ('playClip(rig, "look", now)', "look plays after standing still"),
        ('"GrowthScore"', "eat trigger reads GrowthScore"),
        ('"VisualScale"', "happy trigger reads VisualScale"),
        ("if amp == 0 then rig.act, rig.clip = nil, nil", "Reduce Motion clears the clip"),
        ("require(Shared.LowPolyGait)", "the animator loads the gait loops"),
        ("local RIG = (Config :: any).DinoRigClipsEnabled == true", "the loops, hops, follow-through and Animate switch-off sit behind DinoRigClipsEnabled"),
        ('local name = if phase == "air" then "jump" elseif phase == "land" then "land" else nil', "jump / land clips start on the humanoid state"),
        ("if RIG and not rig.animateOff then rig.animateOff = muteDefaultAnimate(character) end", "the local default Animate is switched off"),
    ]:
        if needle not in anim:
            fails.append("LowPolyAnimator: " + why)
    config = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    if len(re.findall(r"^    DinoRigClipsEnabled = false,$", config, re.M)) != 1:
        fails.append("Config.DinoRigClipsEnabled must ship false exactly once")
    profiles = (ROOT / "tools/release_profiles.py").read_text(encoding="utf-8")
    for needle in ('_flag_off("DinoRigClipsEnabled",', 'Rule("DinoRigClipsEnabled", "set", True,', '("DinoRigClipsEnabled", "BD-1217'):
        if needle not in profiles:
            fails.append("tools/release_profiles.py misses " + needle)
    boot = (ROOT / "src/client/Bootstrap.client.luau").read_text(encoding="utf-8")
    if "DinoRigClips" in boot or "LowPolyGait" in boot:
        fails.append("no rig code in Bootstrap.client.luau")
    for f in fails:
        print("FAIL:", f)
    if fails:
        return 1
    print("verify_lowpoly_clips ok: %d clips (%s), %d loops (%s)" % (len(ns["CLIPS"]), ", ".join(ns["CLIPS"]), len(ns["GAIT"]), ", ".join(ns["GAIT"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
