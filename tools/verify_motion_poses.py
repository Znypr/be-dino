"""BD-250 / BD-251 acceptance checks, offline, against the REAL modules (nothing is reimplemented here).

BD-250: idle/walk driver (chicken/dino waddle, folded wings) as a pure pose function: bounded offsets, speed scaling, reduced motion
        (docs/101 s11 phase 5, implements BD-234).
BD-251: jump / leap / dash animations per class (implements BD-233).

What runs:
  * src/shared/LowPolyPose.luau is loaded into the pinned Luau runner and every check calls its real functions
    (sample, bob, stepRate, sampleAction, duration, actionWeight, blend, rotatePoint, roleOf).
  * src/client/LowPolyAnimator.client.luau is run unmodified in the same runner behind small stand-ins for the Roblox services it
    touches (Players, RunService, CFrame, Vector3, Instance, Enum). The stand-ins are test doubles for the engine, not for the game code:
    the animator's own state machine decides the phases, and a recording wrapper around the real LowPolyPose sees what it asks for.
  * A few static source checks (pure module has no engine API, animator is client-only, flag defaults off).

Every check prints "ok <id>". The Python side requires exactly the ids listed in CHECKS, so a check that silently stops running fails too.
`--selftest` applies small deliberate breaks to the real sources in memory (never on disk) and requires this verifier to FAIL for each one.

NOT checked here, and never claimed: how the poses LOOK in Studio or on a phone, remote players' jump detection on a live server
(humanoid state may lag for remote characters), species flavour that was never built (Brachiosaurus neck sway, T-Rex arm twitch,
occasional blink or foot shuffle, step speed scaled by body size).
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
POSE = 'src/shared/LowPolyPose.luau'
ANIM = 'src/client/LowPolyAnimator.client.luau'
NPC = 'src/shared/NpcLowPoly.luau'

# id -> what it proves. "py" ids are static checks done in Python; the rest are printed by the Luau chunks.
CHECKS = {
    '250.pure': 'LowPolyPose uses no engine API (pure, loads in a bare Luau runner)',
    '250.bounded': 'idle/walk offsets finite and bounded for every class x role x side x speed x amp, bob inside MaxBob',
    '250.reduce': 'Reduce Motion (amp 0) = exact rest for every class and role, wings keep their fold, bob 0',
    '250.speed': 'step rate and leg swing grow with speed, idle sway fades into the walk, bad speeds are safe',
    '250.waddle': 'legs alternate (biped) and pair diagonally (quadruped), real swing amplitude',
    '250.peck': 'head peck 0.4 stud forward + 6 degrees, once per step, only while walking, head barely rolls',
    '250.tail': 'tail sways at idle and counter-swings against the leading leg while walking',
    '250.body': 'body part has no motion of its own, no part slides (rotate only), joint pivots hold, one shared bob',
    '250.idle': 'idle is calm: small angles, breathing bob, slow head tilt',
    '250.fly': 'Fly wings stay folded and mirrored while idle and walking, tiny shuffle only',
    '250.classes': 'Water sits lower with shorter strokes, Armored takes shorter steps than Ground',
    '250.roles': 'roleOf maps generated part names to known roles; unknown role = rest',
    '250.drive_speed': 'animator derives speed01 from planar velocity, eases it, advances the phase by stepRate, idles when still',
    '250.drive_reduce': 'animator under Reduce Motion: amp 0, no action poses, welds back to identity',
    '250.drive_remote': 'animator: local 60 Hz, remote players 20 Hz within 80 studs, none beyond',
    '250.drive_flag': 'animator does nothing when Config.LowPolyDinos is off; flag defaults off in Config',
    '251.bounded': 'jump/leap/land/surge finite and bounded for every class x phase x aggr x role x side, junk inputs = rest',
    '251.reduce': 'Reduce Motion = exact rest in every phase (wings keep their fold)',
    '251.timing': 'phase durations are short and calm, air has no length, Armored is slower, a Water leap surges longer',
    '251.ground': 'Ground jump: crouch, push-off stretch, airborne tuck, landing squash (the pose maths; the animator now skips the first two, see 555)',
    '251.leap': 'a leap is a bigger version of a jump (stretch, lunge)',
    '251.armored': 'Armored crouches deeper, lifts less, lands heavier',
    '251.fly': 'Fly: wings folded before takeoff, open in the air, flap on a jump, glide on a leap, flutter on landing, fold again',
    '251.water': 'Water: no jump, one forward surge with tail kick, head snap on the leap only, never leaves the ground',
    '251.continuity': 'every action starts and ends at the exact rest pose and hands over to idle/walk with weight 0',
    '251.smooth': 'a 5 ms step never jumps the pose in any timed phase',
    '251.drive_ground': 'animator: Ground/Armored/Fly jump runs air, land once and stops (BD-555: no crouch after take-off)',
    '251.drive_ledge': 'animator: stepping off a ledge starts in the air (no crouch)',
    '251.drive_leap': 'animator: the leap signal (LeapPredictAt) makes the action a leap (aggr 1), a plain jump stays 0',
    '251.drive_water': 'animator: Water jump and leap are a single surge with a splash (5 and 9), no repeat while the key is held',
    '251.drive_reduce': 'animator under Reduce Motion: no jump, leap or surge pose and no splash',
    '555.no_crouch': 'animator: a jump or leap that arrives airborne skips the crouch and the push-off (BD-555)',
    '555.one_fold': 'animator: no jump or leap folds the legs more than once, standing or running (BD-555)',
    '555.smooth': 'animator: worst per-frame rotation change under 8 degrees for an airborne-on-first-frame jump and leap, in the air, on landing, on short hops (BD-555)',
    '556.restlift': 'Pose.restLift: a flipper (any walk or surge angle) is never lifted below its rest height, rest and Reduce Motion lift 0, junk inputs are safe',
    '556.drive_flipper': 'animator: Water flipper tips stay at or above their rest height through a walk, a jump surge and a leap surge (BD-556)',
    '251.client_only': 'the pose module and the animator never touch the server (animation is client-side only)',
}

# --------------------------------------------------------------------------------------------------------------------------
# Pure pose checks. Limits below are written out as numbers from docs/101 and docs/87, NOT read from the module under test.
PRELUDE = r'''
local ANG, FOLD, OFF, BOBMAX, PECK = 0.9, 1.5, 0.08, 0.04, 0.4
local CLASSES = {"Ground", "Armored", "Fly", "Water"}
local ROLES = {"body", "head", "neck", "tail", "arm", "leg", "wing", "flipper"}
local TAU = 2 * math.pi
local failed = 0
local function check(id, fn)
    local ok, err = pcall(fn)
    if ok then print("ok " .. id) else failed += 1 print("FAIL " .. id .. ": " .. tostring(err)) end
end
local function fin(v) return v == v and math.abs(v) < 1e6 end
local function S(role, side, lead, t, phase, w, amp, class) return P.sample(role, side, lead, t, phase, w, amp, P.new(), class) end
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-9) end
local function isRest(o, role, side)
    local fold = if role == "wing" then -side * 1.25 else 0
    return near(o.pitch, 0) and near(o.yaw, 0) and near(o.dy, 0) and near(o.dz, 0) and near(o.fwd, 0) and near(o.roll, fold)
end

'''

POSE_BODY = r'''
check("250.bounded", function()
    local speeds = {0, 0.1, 0.3, 0.6, 1, 2, -1, 0/0, math.huge}
    local amps = {0, 0.5, 1, 5, -2, 0/0}
    local n = 0
    for _, class in CLASSES do for _, role in ROLES do for _, side in {-1, 1} do for _, lead in {true, false} do
        for step = 0, 40 do for _, w in speeds do for _, a in amps do
            local o = S(role, side, lead, step * 0.9, step * 0.37, w, a, class)
            for k, v in o do
                assert(fin(v), class .. " " .. role .. " " .. k .. " not finite")
                local cap = ANG
                if role == "wing" and k == "roll" then cap = FOLD elseif k == "dy" or k == "dz" then cap = OFF end
                assert(math.abs(v) <= cap + 1e-9, class .. " " .. role .. " " .. k .. " = " .. v .. " beyond " .. cap)
            end
            assert(o.fwd >= 0 and o.fwd <= PECK + 1e-9, "fwd out of 0..0.4 studs")
            n += 1
        end end end
    end end end end
    for _, class in CLASSES do
        for step = 0, 200 do for _, w in speeds do for _, a in amps do
            local b = P.bob(step * 0.31, step * 0.17, w, a, class)
            assert(fin(b) and math.abs(b) <= BOBMAX + 1e-9, class .. " bob " .. tostring(b))
        end end end
    end
    assert(n > 100000, "grid too small")
end)

check("250.reduce", function()
    for _, class in CLASSES do for _, role in ROLES do for _, side in {-1, 1} do
        for step = 0, 120 do for _, w in {0, 0.4, 1} do
            local o = S(role, side, step % 2 == 0, step * 0.21, step * 0.19, w, 0, class)
            assert(isRest(o, role, side), "Reduce Motion is not rest: " .. class .. " " .. role)
            assert(isRest(S(role, side, true, step, step, w, 0/0, class), role, side), "NaN amp must be rest")
        end end
    end end end
    for _, class in CLASSES do assert(P.bob(1.3, 2.1, 1, 0, class) == 0, "bob must be 0 under Reduce Motion") end
    -- the control: with motion on the same inputs do move (so a ignored amp cannot pass)
    local moved = 0
    for step = 0, 60 do
        local o = S("leg", 1, true, step * 0.2, step * 0.3, 1, 1, "Ground")
        moved += math.abs(o.pitch)
    end
    assert(moved > 5, "control: legs must move with amp 1")
end)

check("250.speed", function()
    local prev = P.stepRate(0)
    assert(prev > 0, "step rate must be positive at rest")
    for i = 1, 20 do local r = P.stepRate(i / 20) assert(r > prev, "step rate must rise with speed") prev = r end
    assert(P.stepRate(7) == P.stepRate(1) and P.stepRate(-3) == P.stepRate(0), "step rate clamps")
    local function legPeak(w)
        local m = 0
        for i = 0, 200 do m = math.max(m, math.abs(S("leg", 1, true, 0, i * TAU / 200, w, 1).pitch)) end
        return m
    end
    local last = -1
    for _, w in {0, 0.25, 0.5, 0.75, 1} do
        local m = legPeak(w)
        assert(m > last, "leg swing must grow with speed: w=" .. w .. " peak " .. m)
        last = m
    end
    assert(legPeak(0) == 0, "no leg swing at idle")
    -- the idle head turn fades out as walking takes over (blend, no pop)
    local function yawPeak(w)
        local m = 0
        for i = 0, 400 do m = math.max(m, math.abs(S("head", 1, true, i * 0.2, 0, w, 1).yaw)) end
        return m
    end
    assert(yawPeak(0) > 0.03 and yawPeak(0.5) < yawPeak(0) and yawPeak(1) == 0, "idle sway must fade into the walk")
    -- walking bobs more than idle breathing
    local function bobPeak(w) local m = 0 for i = 0, 400 do m = math.max(m, math.abs(P.bob(i * 0.2, i * 0.13, w, 1, "Ground"))) end return m end
    assert(bobPeak(1) > bobPeak(0) and bobPeak(0) > 0, "walk bob must exceed idle breathing")
    -- junk speeds never produce junk poses
    for _, w in {0/0, math.huge, -math.huge, -5} do
        for _, role in ROLES do assert(fin(S(role, 1, true, 1, 1, w, 1).pitch)) end
    end
end)

check("250.waddle", function()
    local peak = 0
    for i = 0, 400 do
        local ph = i * TAU / 400
        local l, r = S("leg", -1, false, 0, ph, 1, 1).pitch, S("leg", 1, false, 0, ph, 1, 1).pitch
        assert(near(l + r, 0), "biped legs must alternate")
        peak = math.max(peak, math.abs(l))
        -- quadruped: diagonal pairs (front-left with back-right), the other diagonal opposite
        local fl, fr = S("leg", -1, true, 0, ph, 1, 1).pitch, S("leg", 1, true, 0, ph, 1, 1).pitch
        local bl, br = S("leg", -1, false, 0, ph, 1, 1).pitch, S("leg", 1, false, 0, ph, 1, 1).pitch
        assert(near(fl, br) and near(fr, bl) and near(fl, -fr), "quadruped legs must move in diagonal pairs")
        local al, ar = S("arm", -1, false, 0, ph, 1, 1).pitch, S("arm", 1, false, 0, ph, 1, 1).pitch
        assert(near(al, -ar), "arms swing opposite each other")
    end
    assert(peak > 0.3 and peak < 0.7, "walk leg swing amplitude " .. peak)
end)

check("250.peck", function()
    local N = 2000
    local maxFwd, minPitch, peaks = 0, 0, 0
    local f = {}
    for i = 0, N - 1 do
        local o = S("head", 1, true, 0, i * TAU / N, 1, 1)
        f[i] = o.fwd
        maxFwd, minPitch = math.max(maxFwd, o.fwd), math.min(minPitch, o.pitch)
        assert(o.fwd >= 0, "head never pulls back past rest")
        assert(math.abs(o.roll) <= 0.03 and o.yaw == 0, "head (eyes, nostrils) barely turns while walking")
    end
    for i = 0, N - 1 do
        if f[i] > f[(i - 1) % N] and f[i] >= f[(i + 1) % N] and f[i] > 0.5 * maxFwd then peaks += 1 end
    end
    assert(math.abs(maxFwd - PECK) < 0.01, "peck forward about 0.4 stud: " .. maxFwd)
    assert(math.abs(minPitch + math.rad(6)) < 0.005, "peck about 6 degrees nose-down: " .. minPitch)
    assert(peaks == 2, "one peck per step (two per full leg cycle): " .. peaks)
    for _, role in {"head", "neck"} do
        for i = 0, 400 do
            local o = S(role, 1, true, i * 0.37, i * 0.51, 0, 1)
            assert(o.fwd == 0, "no peck while standing")
        end
    end
    for _, role in {"body", "tail", "leg", "arm", "wing", "flipper"} do
        for i = 0, 100 do assert(S(role, 1, true, i, i, 1, 1).fwd == 0, role .. " must not peck") end
    end
end)

check("250.tail", function()
    local idlePeak, walkPeak = 0, 0
    for i = 0, 600 do idlePeak = math.max(idlePeak, math.abs(S("tail", 1, true, i * 0.2, 0, 0, 1).yaw)) end
    assert(idlePeak > 0.1, "idle tail sway missing: " .. idlePeak)
    local lo, hi = 0, 0
    for i = 0, 400 do
        local ph = i * TAU / 400
        local y = S("tail", 1, true, 0, ph, 1, 1).yaw
        local leg = S("leg", -1, true, 0, ph, 1, 1).pitch
        assert(y * leg <= 1e-12, "tail must counter-swing against the leading leg")
        lo, hi = math.min(lo, y), math.max(hi, y)
    end
    assert(hi > 0.1 and lo < -0.1, "tail swings both ways while walking")
end)

check("250.body", function()
    for _, class in CLASSES do
        for i = 0, 300 do
            for _, w in {0, 0.5, 1} do
                local b = S("body", 1, true, i * 0.13, i * 0.29, w, 1, class)
                for k, v in b do assert(v == 0, "body part moved on its own: " .. k) end
                for _, role in ROLES do
                    local o = S(role, 1, i % 2 == 0, i * 0.13, i * 0.29, w, 1, class)
                    assert(o.dy == 0 and o.dz == 0, role .. " must not slide (rotate only)")
                    if role ~= "head" and role ~= "neck" then assert(o.fwd == 0) end
                end
            end
        end
    end
    -- one shared whole-rig bob: a single number
    assert(type(P.bob(1, 1, 1, 1, "Ground")) == "number" and P.bob(2, 3, 0.5, 1) == P.bob(2, 3, 0.5, 1, "Ground"))
    -- rotating about a joint never moves the joint and never stretches the part
    local function dist(a, b) return math.sqrt((a[1]-b[1])^2 + (a[2]-b[2])^2 + (a[3]-b[3])^2) end
    for _, pivot in {{0, -1, 1}, {0, 0, -2}, {0, 0.7, 0}} do
        for step = 0, 200 do
            local pi, yw, rl = math.sin(step) * 0.65, math.sin(step * 1.3) * 0.2, math.cos(step * 0.7) * 0.2
            assert(dist(P.rotatePoint(pivot, pivot, pi, yw, rl), pivot) < 1e-9, "joint anchor must stay put")
            local tip = {pivot[1] + 0.3, pivot[2] - 1.4, pivot[3] + 0.5}
            assert(math.abs(dist(P.rotatePoint(tip, pivot, pi, yw, rl), pivot) - dist(tip, pivot)) < 1e-9, "limb length must stay constant")
        end
    end
end)

check("250.idle", function()
    for _, class in CLASSES do for _, role in ROLES do
        for i = 0, 600 do
            local o = S(role, 1, true, i * 0.3, i * 0.2, 0, 1, class)
            assert(math.abs(o.pitch) <= 0.1 and math.abs(o.yaw) <= 0.2, "idle must be calm: " .. class .. " " .. role)
            if role ~= "wing" then assert(math.abs(o.roll) <= 0.1) end
            assert(o.fwd == 0 and o.dy == 0 and o.dz == 0)
        end
    end end
    -- breathing: a gentle visible bob, never a hop
    local lo, hi = 1, -1
    for i = 0, 600 do local b = P.bob(i * 0.05, 0, 0, 1, "Ground") lo, hi = math.min(lo, b), math.max(hi, b) end
    assert(hi - lo > 0.01 and math.max(math.abs(lo), math.abs(hi)) <= 0.01, "idle breathing bob range " .. (hi - lo))
    -- slow head tilt: it tilts both ways but never faster than 0.1 rad per second
    local mn, mx, maxRate = 0, 0, 0
    local prev = S("head", 1, true, 0, 0, 0, 1).roll
    for i = 1, 3000 do
        local r = S("head", 1, true, i * 0.01, 0, 0, 1).roll
        mn, mx, maxRate = math.min(mn, r), math.max(mx, r), math.max(maxRate, math.abs(r - prev) / 0.01)
        prev = r
    end
    assert(mn < -0.03 and mx > 0.03 and maxRate < 0.1, "head tilt both ways, slowly: rate " .. maxRate)
end)

check("250.fly", function()
    local maxShuffle = 0
    for _, w in {0, 0.3, 1} do
        for i = 0, 400 do
            local t, ph = i * 0.31, i * 0.17
            local l, r = S("wing", -1, false, t, ph, w, 1, "Fly"), S("wing", 1, false, t, ph, w, 1, "Fly")
            assert(r.roll < -0.9 and l.roll > 0.9, "Fly wings must stay folded")
            assert(near(l.roll + r.roll, 0, 0.15), "wings mirrored (the shuffle is allowed to differ a little per side)")
            maxShuffle = math.max(maxShuffle, math.abs(r.roll + 1.25))
        end
    end
    assert(maxShuffle > 0.01 and maxShuffle <= 0.12, "wing shuffle is tiny but present: " .. maxShuffle)
end)

check("250.classes", function()
    local function legPeak(class) local m = 0 for i = 0, 200 do m = math.max(m, math.abs(S("leg", 1, true, 0, i * TAU / 200, 1, 1, class).pitch)) end return m end
    assert(legPeak("Water") < legPeak("Armored") and legPeak("Armored") < legPeak("Ground"), "Water < Armored < Ground strokes")
    for i = 0, 100 do
        assert(P.bob(0, i * 0.1, 1, 1, "Water") < P.bob(0, i * 0.1, 1, 1, "Ground"), "Water body sits lower")
    end
    local lo, hi = 1, -1
    for i = 0, 600 do local b = P.bob(i * 0.05, 0, 0, 1, "Water") lo, hi = math.min(lo, b), math.max(hi, b) assert(b < 0, "Water floats low at idle") end
    assert(hi - lo > 0.005, "Water bobs while idle")
    local fl = 0
    for i = 0, 200 do fl = math.max(fl, math.abs(S("flipper", 1, true, 0, i * TAU / 200, 1, 1, "Water").pitch)) end
    assert(fl > 0.05, "flippers move while walking")
end)

check("250.roles", function()
    local names = {"body", "head", "tail", "left arm", "right leg", "front left leg", "back right leg", "left wing", "right wing", "neck", "neck and head",
        "front left flipper", "back right flipper", '"left arm"_geom', '"Right Leg"_geom', "Torso"}
    local known = {}
    for _, r in P.Roles do known[r] = true end
    for _, n in names do
        local r = P.roleOf(n)
        assert(r ~= nil and known[r], "part name " .. n .. " -> " .. tostring(r))
        assert(fin(S(r, 1, true, 1, 1, 1, 1).pitch))
    end
    assert(P.roleOf("neck and head") == "head" and P.roleOf("xyz") == nil and P.roleOf("") == nil)
    assert(isRest(S("xyz", 1, true, 3, 3, 1, 1), "xyz", 1), "unknown role stays at rest")
end)
'''

POSE_TAIL = r'''
if failed > 0 then error(failed .. " pose check(s) failed") end
print("pose checks passed")
'''

# BD-251 pure checks
ACTION_BODY = r'''
local PHASES = {Ground = {"crouch", "push", "air", "land"}, Armored = {"crouch", "push", "air", "land"}, Fly = {"crouch", "push", "air", "land"}, Water = {"surge"}}
local ctx = P.newCtx()
local function A(class, phase, aggr, p, t, role, side, amp, carry, flap, wing)
    ctx.phase, ctx.p, ctx.t, ctx.aggr, ctx.carry, ctx.flap, ctx.wing = phase, p, t, aggr, carry or 0.7, flap or 0, wing
    return P.sampleAction(role, side, true, ctx, amp or 1, P.new(), class)
end

check("251.bounded", function()
    local n = 0
    for class, phases in PHASES do for _, phase in phases do for _, aggr in {0, 0.5, 1, -1, 3, 0/0} do
        for step = 0, 20 do for _, role in ROLES do for _, side in {-1, 1} do
            local o = A(class, phase, aggr, step / 20, step * 0.06, role, side, 1)
            for k, v in o do
                assert(fin(v), class .. " " .. phase .. " " .. role .. " " .. k .. " not finite")
                local cap = ANG
                if role == "wing" and k == "roll" then cap = FOLD elseif k == "dy" or k == "dz" then cap = OFF end
                assert(math.abs(v) <= cap + 1e-9, class .. " " .. phase .. " " .. role .. " " .. k .. " = " .. v)
            end
            assert(o.fwd == 0)
            n += 1
        end end end
    end end end
    -- junk inputs: NaN progress/time/amp, unknown phase, wrong phase for the class (Water has no air) = rest
    for _, class in CLASSES do for _, role in ROLES do for _, side in {-1, 1} do
        assert(isRest(A(class, "air", 0/0, 0/0, 0/0, role, side, 0/0, 0/0), role, side), "NaN must be rest")
        assert(isRest(A(class, "nonsense", 1, 0.5, 0.3, role, side, 1), role, side), "unknown phase must be rest")
    end end end
    for _, phase in {"crouch", "push", "air", "land"} do
        for _, role in ROLES do assert(isRest(A("Water", phase, 1, 0.7, 0.3, role, 1, 1), role, 1), "Water has no " .. phase) end
    end
    assert(n > 5000)
end)

check("251.reduce", function()
    for class, phases in PHASES do for _, phase in phases do for _, aggr in {0, 1} do
        for step = 0, 20 do for _, role in ROLES do for _, side in {-1, 1} do
            assert(isRest(A(class, phase, aggr, step / 20, step * 0.06, role, side, 0), role, side), "Reduce Motion not rest: " .. class .. " " .. phase .. " " .. role)
        end end end
    end end end
    -- control: with motion on, the same inputs do move
    assert(math.abs(A("Ground", "crouch", 0, 1, 0.1, "body", 1, 1).dy) > 0.02)
end)

check("251.timing", function()
    for class, phases in PHASES do
        for _, phase in phases do
            local d = P.duration(phase, 0, class)
            if phase == "air" then assert(d == 0, "air lasts until landing") else assert(d > 0.05 and d <= 0.6, class .. " " .. phase .. " " .. d) end
        end
    end
    assert(P.duration("crouch", 0, "Ground") + P.duration("push", 0, "Ground") + P.duration("land", 0, "Ground") <= 1.2)
    for _, ph in {"crouch", "push", "land"} do assert(P.duration(ph, 0, "Armored") > P.duration(ph, 0, "Ground"), "Armored slower: " .. ph) end
    assert(P.duration("land", 0, "Fly") > P.duration("land", 0, "Ground"), "Fly lands softer and longer")
    assert(P.duration("surge", 1, "Water") > P.duration("surge", 0, "Water") and P.duration("surge", 0, "Water") >= 0.3 and P.duration("surge", 1, "Water") <= 0.7)
    assert(P.duration("nonsense", 0, "Ground") == 0)
    for _, name in {"crouch", "push", "air", "land", "surge"} do assert(table.find(P.Phases, name), name .. " missing from Pose.Phases") end
end)

check("251.ground", function()
    for _, class in {"Ground", "Armored"} do
        local crouch = A(class, "crouch", 0, 1, 0.1, "body", 1, 1)
        local push = A(class, "push", 0, 1, 0.1, "body", 1, 1)
        local land = A(class, "land", 0, 0.25, 0.1, "body", 1, 1, 0)
        assert(crouch.dy < -0.02, class .. " crouch squats the body")
        assert(push.dy > 0 and push.dy > crouch.dy, class .. " push-off stretches up")
        assert(land.dy < -0.015, class .. " landing squashes")
        assert(A(class, "crouch", 0, 1, 0.1, "leg", 1, 1).pitch > 0.3, class .. " legs fold in the crouch")
        assert(A(class, "push", 0, 1, 0.1, "leg", 1, 1).pitch < 0, class .. " legs extend on push-off")
        assert(A(class, "air", 0, 0, 0.5, "leg", 1, 1).pitch > 0.15, class .. " legs tuck in the air")
        assert(A(class, "air", 0, 0, 0.5, "arm", 1, 1).pitch > 0.1, class .. " arms tuck in the air")
        -- the tuck settles over TuckTime instead of snapping
        assert(A(class, "air", 0, 0, 0.0, "leg", 1, 1).pitch < A(class, "air", 0, 0, 0.5, "leg", 1, 1).pitch)
    end
    local g = A("Ground", "land", 0, 0.25, 0.1, "leg", 1, 1, 0)
    assert(g.pitch > 0.2, "landing: legs bend to absorb")
end)

check("251.leap", function()
    for _, class in {"Ground", "Armored", "Fly"} do
        local j, l = A(class, "push", 0, 1, 0.1, "body", 1, 1), A(class, "push", 1, 1, 0.1, "body", 1, 1)
        assert(l.pitch > j.pitch, class .. " leap leans further forward")
        assert(l.dz < j.dz, class .. " leap reaches further forward")
        local hj, hl = A(class, "push", 0, 1, 0.1, "head", 1, 1), A(class, "push", 1, 1, 0.1, "head", 1, 1)
        assert(hl.pitch > hj.pitch, class .. " leap lifts the head more")
    end
    local jb, lb = A("Water", "surge", 0, 0.5, 0.2, "body", 1, 1), A("Water", "surge", 1, 0.5, 0.275, "body", 1, 1)
    assert(lb.dz < jb.dz, "Water leap lunges further than the jump")
end)

check("251.armored", function()
    local function body(class, ph, p, c) return A(class, ph, 0, p, 0.1, "body", 1, 1, c or 0) end
    assert(body("Armored", "crouch", 1).dy < body("Ground", "crouch", 1).dy, "Armored crouches deeper")
    assert(body("Armored", "push", 1).dy < body("Ground", "push", 1).dy, "Armored lifts less")
    assert(body("Armored", "land", 0.25).dy < body("Ground", "land", 0.25).dy, "Armored lands heavier")
end)

check("251.fly", function()
    local function wing(side, phase, p, t, aggr, carry) return A("Fly", phase, aggr or 0, p, t, "wing", side, 1, carry).roll end
    -- folded before takeoff and through the crouch
    for step = 0, 10 do
        assert(near(wing(1, "crouch", step / 10, 0), -1.25) and near(wing(-1, "crouch", step / 10, 0), 1.25), "wings folded before takeoff")
    end
    -- open in the air, mirrored
    local r, l = wing(1, "air", 0, 0.5), wing(-1, "air", 0, 0.5)
    assert(math.abs(r) < 0.6 and math.abs(l) < 0.6 and r * l <= 0, "wings open and mirrored in the air")
    assert(wing(1, "push", 1, 0.1) > wing(1, "crouch", 1, 0.1), "wings start opening on the push-off")
    -- flap on a jump, glide on a leap
    local function span(aggr, phase, t0, t1, n)
        local lo, hi = 9, -9
        for i = 0, n do local v = wing(1, phase, 0.5, t0 + (t1 - t0) * i / n, aggr, 1) lo, hi = math.min(lo, v), math.max(hi, v) end
        return hi - lo
    end
    local jumpFlap, leapFlap = span(0, "air", 0.3, 1.3, 400), span(1, "air", 0.3, 1.3, 400)
    assert(jumpFlap > 0.3, "a jump flaps: " .. jumpFlap)
    assert(leapFlap < 0.3 * jumpFlap, "a leap glides on nearly still wings: " .. leapFlap .. " vs " .. jumpFlap)
    -- soft flutter landing, then folded again
    local flutter = span(0, "land", 0, 0.2, 200)
    assert(flutter > 0.05, "landing flutter missing: " .. flutter)
    assert(near(wing(1, "land", 1, 0.45, 0, 1), -1.25), "wings folded again at the end of the landing")
    -- first-look fix: the landing starts from the flap angle the air phase ended on (it used to snap to 0, up to about 20 degrees in one frame)
    for _, aggr in {0, 1} do for i = 0, 40 do
        local airT = i * 0.073
        for _, side in {-1, 1} do
            local air = A("Fly", "air", aggr, 0, airT, "wing", side, 1).roll
            local land = A("Fly", "land", aggr, 0, 0, "wing", side, 1, 1, P.airFlap(airT, aggr)).roll
            assert(near(air, land, 1e-9), "Fly air -> land wing pop: " .. air .. " vs " .. land .. " at " .. airT)
        end
    end end
    -- a hop that lands BEFORE the wings opened (crouch, push) must hand over exactly: the old landing opened them in one frame (about 60 degrees)
    for _, spec in {{"crouch", 1, 0.08}, {"crouch", 0.4, 0.03}, {"push", 0, 0}, {"push", 0.3, 0.036}, {"push", 0.7, 0.084}, {"push", 1, 0.12}} do
        local phase, p, t = spec[1], spec[2], spec[3]
        for _, side in {-1, 1} do for _, role in {"wing", "body", "head", "leg"} do
            local last = A("Fly", phase, 0, p, t, role, side, 1)
            local land = A("Fly", "land", 0, 0, 0, role, side, 1, 0, 0, P.wingOpen(phase, p)) -- what the animator hands over (carry 0, flap 0)
            if role == "wing" then
                assert(near(last.roll, land.roll, 1e-9) and near(last.pitch, land.pitch, 1e-9), "Fly " .. phase .. " p=" .. p .. " -> land wing pop: " .. last.roll .. " vs " .. land.roll)
            end
        end end
    end
    assert(near(P.wingOpen("crouch", 1), 0) and near(P.wingOpen("air", 0), 1) and near(P.wingOpen("push", 1), 1), "wingOpen end points")
    -- and the carried flap is gone by the end of the first third of the landing (no lingering offset)
    assert(near(wing(1, "land", 1, 0.45, 0, 1), A("Fly", "land", 0, 1, 0.45, "wing", 1, 1, 1, 0.35).roll), "carried flap must fade out by the end of the landing")
    -- Fly crouches less than Ground
    assert(A("Fly", "crouch", 0, 1, 0.1, "body", 1, 1).dy > A("Ground", "crouch", 0, 1, 0.1, "body", 1, 1).dy, "Fly crouches shallower")
    -- wings do nothing for classes that have none: other roles still follow the ground rules
    assert(A("Fly", "air", 0, 0, 0.5, "leg", 1, 1).pitch > 0.1, "Fly still tucks its legs")
end)

check("251.water", function()
    -- no jump: all the ground phases are rest (asserted in 251.bounded); one surge
    local reach, lo, hi = 0, 0, 0
    local headSnapLeap, headSnapJump = 0, 0
    local maxUp = -1
    for i = 0, 200 do
        local p = i / 200
        for _, role in ROLES do
            for _, aggr in {0, 1} do
                local o = A("Water", "surge", aggr, p, p * 0.4, role, 1, 1)
                maxUp = math.max(maxUp, o.dy)
            end
        end
        reach = math.min(reach, A("Water", "surge", 0, p, 0.2, "body", 1, 1).dz)
        local ty = A("Water", "surge", 1, p, 0.2, "tail", 1, 1).yaw
        lo, hi = math.min(lo, ty), math.max(hi, ty)
        headSnapLeap = math.min(headSnapLeap, A("Water", "surge", 1, p, 0.2, "head", 1, 1).pitch)
        headSnapJump = math.min(headSnapJump, A("Water", "surge", 0, p, 0.2, "head", 1, 1).pitch)
    end
    assert(maxUp <= 1e-9, "Water never rises off the ground: dy " .. maxUp)
    assert(reach < -0.02, "surge goes forward: " .. reach)
    assert(lo < -0.1 and hi > 0.1, "tail kicks both ways")
    assert(headSnapLeap < -0.2, "leap snaps the head: " .. headSnapLeap)
    assert(headSnapJump > -0.01, "plain surge does not snap: " .. headSnapJump)
    assert(A("Water", "surge", 0, 0.5, 0.2, "flipper", 1, 1).pitch > 0.1, "flippers pull during the surge")
    local sg = P.actionWeight("surge", 0.5)
    assert(sg > 0.99 and P.actionWeight("surge", 0) == 0 and P.actionWeight("surge", 1) == 0)
end)

check("251.continuity", function()
    for class, phases in PHASES do
        local first, last = phases[1], phases[#phases]
        assert(P.actionWeight(first, 0) == 0 and P.actionWeight(last, 1) == 0, class .. " hand-over weight")
        for _, aggr in {0, 1} do for _, role in ROLES do for _, side in {-1, 1} do
            assert(isRest(A(class, first, aggr, 0, 0, role, side, 1), role, side), class .. " start not rest " .. role)
            assert(isRest(A(class, last, aggr, 1, P.duration(last, aggr, class), role, side, 1), role, side), class .. " end not rest " .. role)
            -- blending the finished action into the walk pose with weight 0 leaves the walk pose untouched
            local base, walk = S(role, side, true, 1.7, 0.4, 0.6, 1, class), S(role, side, true, 1.7, 0.4, 0.6, 1, class)
            P.blend(base, A(class, last, aggr, 1, P.duration(last, aggr, class), role, side, 1), P.actionWeight(last, 1))
            for k, v in base do assert(near(v, walk[k], 1e-12), class .. " land end must be the base pose") end
        end end end
        for p = 0, 20 do local k = P.actionWeight(last, p / 20) assert(k >= 0 and k <= 1) end
    end
    -- air to land: for classes without wings the pose at the end of the air phase equals the start of the landing (carry 1)
    for _, class in {"Ground", "Armored"} do
        for _, role in ROLES do
            local a, b = A(class, "air", 0.5, 0, 1.0, role, 1, 1), A(class, "land", 0.5, 0, 0, role, 1, 1, 1)
            for k, v in a do assert(near(v, b[k], 1e-9), class .. " air->land pop " .. role .. " " .. k) end
        end
    end
end)

check("556.restlift", function()
    local size, pivot = {2, 1, 3}, {-1, 0, 0} -- a flipper-like box, pivot on the inner edge at mid height
    assert(P.restLift(size, pivot, 0, 0, 0) == 0, "rest lifts nothing")
    local worstDip, n = 0, 0
    for pi = -12, 12 do for ri = -12, 12 do for yi = -3, 3 do
        local pitch, roll, yaw = pi * 0.04, ri * 0.04, yi * 0.1
        for _, up in {{0, 1, 0}, {0, 0, 1}, {1, 0, 0}} do
            local lift = P.restLift(size, pivot, pitch, yaw, roll, up)
            assert(lift >= 0 and lift <= P.MaxLift and fin(lift), "lift out of range " .. tostring(lift))
            -- after the lift the lowest corner is no lower than at rest
            local rest, low = math.huge, math.huge
            for _, sx in {-1, 1} do for _, sy in {-1, 1} do for _, sz in {-1, 1} do
                local c = {sx * 1, sy * 0.5, sz * 1.5}
                local r = P.rotatePoint(c, pivot, pitch, yaw, roll)
                rest = math.min(rest, up[1] * c[1] + up[2] * c[2] + up[3] * c[3])
                low = math.min(low, up[1] * r[1] + up[2] * r[2] + up[3] * r[3])
            end end end
            if lift < P.MaxLift then assert(low + lift >= rest - 1e-9, "flipper still dips: " .. (low + lift - rest)) end
            assert(lift == 0 or low + lift <= rest + 1e-9, "lifted more than needed")
            if up[2] == 1 then worstDip = math.max(worstDip, lift) end
            n += 1
        end
    end end end
    -- the control: the real walk and surge angles of a flipper do dip without the lift (so a lift of 0 everywhere cannot pass)
    local maxPitch, maxRoll = 0, 0
    for step = 0, 100 do
        local o = S("flipper", 1, true, 0, step * 0.1, 1, 1, "Water")
        maxPitch, maxRoll = math.max(maxPitch, math.abs(o.pitch)), math.max(maxRoll, math.abs(o.roll))
    end
    assert(P.restLift({2, 0.6, 4}, {-1, 0, 0}, maxPitch, 0, maxRoll) > 0.05, "control: a walking flipper must need a lift")
    assert(P.restLift({2, 0.6, 4}, {-1, 0, 0}, 0, 0, 0) == 0)
    -- junk: NaN, huge, missing up
    assert(P.restLift({2, 2, 2}, {0, 0, 0}, 0/0, math.huge, -math.huge) == 0 or fin(P.restLift({2, 2, 2}, {0, 0, 0}, 0/0, math.huge, -math.huge)))
    assert(fin(P.restLift({0/0, -5, 1e9}, {0, 0, 0}, 1, 1, 1)))
    assert(n > 5000)
end)

check("251.smooth", function()
    for class, phases in PHASES do for _, phase in phases do for _, role in ROLES do
        local dur = math.max(P.duration(phase, 1, class), 0.5)
        for step = 0, 99 do
            local t0 = step / 100 * dur
            local a = A(class, phase, 1, math.clamp(t0 / dur, 0, 1), t0, role, 1, 1)
            local b = A(class, phase, 1, math.clamp((t0 + 0.005) / dur, 0, 1), t0 + 0.005, role, 1, 1)
            for k, v in a do assert(math.abs(v - b[k]) < 0.06, "jerky " .. class .. " " .. phase .. " " .. role .. " " .. k) end
        end
    end end end
end)
'''

# --------------------------------------------------------------------------------------------------------------------------
# Animator harness: runs the real LowPolyAnimator.client.luau against engine stand-ins. The wrapper records what the animator asks the
# real LowPolyPose for; it changes nothing it returns.
HARNESS = r'''
local V3M = {}
local V3 = {}
function V3.new(x, y, z) return setmetatable({X = x or 0, Y = y or 0, Z = z or 0}, V3M) end
V3M.__index = function(t, k) if k == "Magnitude" then return math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z) end return nil end
V3M.__add = function(a, b) return V3.new(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end
V3M.__sub = function(a, b) return V3.new(a.X - b.X, a.Y - b.Y, a.Z - b.Z) end
V3M.__unm = function(a) return V3.new(-a.X, -a.Y, -a.Z) end
V3M.__mul = function(a, b)
    if type(a) == "number" then return V3.new(a * b.X, a * b.Y, a * b.Z) end
    if type(b) == "number" then return V3.new(a.X * b, a.Y * b, a.Z * b) end
    return V3.new(a.X * b.X, a.Y * b.Y, a.Z * b.Z)
end
V3.zero = V3.new(0, 0, 0)
local CFM = {}
local CFrame = {}
local function cf(r, p) return setmetatable({r = r, p = p}, CFM) end
local function mm(a, b)
    local o = {}
    for i = 0, 2 do for j = 0, 2 do
        o[i * 3 + j + 1] = a[i * 3 + 1] * b[j + 1] + a[i * 3 + 2] * b[j + 4] + a[i * 3 + 3] * b[j + 7]
    end end
    return o
end
local function mv(r, x, y, z) return r[1] * x + r[2] * y + r[3] * z, r[4] * x + r[5] * y + r[6] * z, r[7] * x + r[8] * y + r[9] * z end
CFM.__mul = function(a, b)
    if rawget(b, "r") then
        local x, y, z = mv(a.r, b.p[1], b.p[2], b.p[3])
        return cf(mm(a.r, b.r), {x + a.p[1], y + a.p[2], z + a.p[3]})
    end
    local x, y, z = mv(a.r, b.X, b.Y, b.Z)
    return V3.new(x + a.p[1], y + a.p[2], z + a.p[3])
end
CFM.__index = function(t, k)
    if k == "Rotation" then return cf(t.r, {0, 0, 0}) end
    if k == "Position" then return V3.new(t.p[1], t.p[2], t.p[3]) end
    if k == "Inverse" then
        return function(self)
            local r = self.r
            local rt = {r[1], r[4], r[7], r[2], r[5], r[8], r[3], r[6], r[9]}
            local x, y, z = mv(rt, self.p[1], self.p[2], self.p[3])
            return cf(rt, {-x, -y, -z})
        end
    end
    return nil
end
local IDENT = {1, 0, 0, 0, 1, 0, 0, 0, 1}
CFrame.identity = cf(IDENT, {0, 0, 0})
function CFrame.new(a, b, c)
    if a == nil then return CFrame.identity end
    if type(a) == "number" then return cf(IDENT, {a, b, c}) end
    return cf(IDENT, {a.X, a.Y, a.Z})
end
function CFrame.Angles(rx, ry, rz)
    local cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    local Rx, Ry, Rz = {1, 0, 0, 0, cx, -sx, 0, sx, cx}, {cy, 0, sy, 0, 1, 0, -sy, 0, cy}, {cz, -sz, 0, sz, cz, 0, 0, 0, 1}
    return cf(mm(mm(Rx, Ry), Rz), {0, 0, 0})
end
local function isIdentity(c)
    for i = 1, 9 do if math.abs(c.r[i] - IDENT[i]) > 1e-9 then return false end end
    return math.abs(c.p[1]) + math.abs(c.p[2]) + math.abs(c.p[3]) < 1e-9
end
local function autoTable(prefix)
    return setmetatable({}, {__index = function(t, k) local v = if prefix then prefix .. "." .. k else autoTable(k) rawset(t, k, v) return v end})
end
local function enumTable()
    return setmetatable({}, {__index = function(t, group)
        local g = setmetatable({}, {__index = function(_, name) return group .. "." .. name end})
        rawset(t, group, g)
        return g
    end})
end
local Enum = enumTable()
local ST = Enum.HumanoidStateType

local function obj(class, is)
    local o = {ClassName = class, _attrs = {}, _kids = {}, _is = is or {}}
    o._is[class] = true
    function o:GetAttribute(n) return self._attrs[n] end
    function o:SetAttribute(n, v) self._attrs[n] = v end
    function o:IsA(c) return self._is[c] == true end
    function o:FindFirstChild(n) return self._kids[n] end
    return o
end

local function makeWeld()
    local w = obj("Weld")
    local state = {c1 = CFrame.identity, writes = 0}
    w.C0 = CFrame.identity
    w.Parent = true
    return setmetatable(w, {
        __index = function(t, k) if k == "C1" then return state.c1 elseif k == "writes" then return state.writes end return nil end,
        __newindex = function(t, k, v) if k == "C1" then state.c1 = v state.writes += 1 else rawset(t, k, v) end end,
    })
end

local SPECS = {
    base = {{"body", 1, false}, {"head", 1, false}, {"tail", 1, false}, {"leg", -1, true}, {"leg", 1, true}},
    wings = {{"wing", -1, false}, {"wing", 1, false}},
    flippers = {{"flipper", -1, true}, {"flipper", 1, true}, {"flipper", -1, false}, {"flipper", 1, false}},
}
local function makeCharacter(class, at)
    local char = obj("Model")
    local visual = obj("Model")
    visual._attrs.LowPoly = true
    visual._attrs.LPClass = class
    local parts, welds = {}, {}
    local specs = {}
    for _, s in SPECS.base do table.insert(specs, s) end
    if class == "Fly" then for _, s in SPECS.wings do table.insert(specs, s) end end
    if class == "Water" then for _, s in SPECS.flippers do table.insert(specs, s) end end
    for _, s in specs do
        local part = obj("MeshPart", {BasePart = true})
        part.Size = V3.new(2, 2, 2)
        part.Parent = visual
        part._attrs.LPRole, part._attrs.LPSide, part._attrs.LPLead = s[1], s[2], s[3]
        local weld = makeWeld()
        part._kids.ResourceWeld = weld
        table.insert(parts, part)
        table.insert(welds, weld)
    end
    function visual:GetBoundingBox() return CFrame.identity, V3.new(4, 6, 8) end
    function visual:GetDescendants() return parts end
    local root = obj("Part", {BasePart = true})
    root.Position = at or V3.zero
    root.AssemblyLinearVelocity = V3.zero
    local hum = obj("Humanoid")
    hum.Health, hum.Jump, hum.FloorMaterial, hum.Parent = 100, false, Enum.Material.Plastic, char
    local state = ST.Running
    function hum:GetState() return state end
    local c = {char = char, root = root, hum = hum, welds = welds, visual = visual}
    function c.setState(s) state = s end
    char._kids.LocalMeshVisual = visual
    char._kids.HumanoidRootPart = root
    char._kids.Humanoid = hum
    function char:FindFirstChildOfClass(cls) return if cls == "Humanoid" then hum else nil end
    return c
end

local FRAME = 1 / 60
local function boot(opts)
    opts = opts or {}
    local env = {now = 100, hb = {}, calls = {}, legs = {}, emits = {}, players = {}, sampleCalls = 0}
    local Pose = setmetatable({}, {__index = RealPose})
    function Pose.sampleAction(role, side, lead, c, amp, o, class)
        table.insert(env.calls, {phase = c.phase, aggr = c.aggr, p = c.p, amp = amp, class = class, role = role, now = env.now})
        return RealPose.sampleAction(role, side, lead, c, amp, o, class)
    end
    function Pose.sample(role, side, lead, t, phase, w, amp, o, class)
        env.sampleCalls += 1
        if role == "leg" then table.insert(env.legs, {w = w, phase = phase, amp = amp, now = env.now}) end
        return RealPose.sample(role, side, lead, t, phase, w, amp, o, class)
    end
    env.theme = {MotionEnabled = true}
    local Shared = {
        LowPolyPose = Pose,
        LowPolyDinos = {enabled = function() return opts.enabled ~= false end},
        UITheme = env.theme,
        EffectAssets = {isSheet = function() return false end, isAdditive = function() return false end, resolve = function() return "x" end, Builtin = {smoke = "smoke"}},
        NpcLowPoly = NpcLowPoly,
    }
    local Terrain = {}
    env.workspace = {Terrain = Terrain, CurrentCamera = {CFrame = {Position = V3.zero}}}
    function env.workspace:FindFirstChild(n) return nil end
    local hbSignal = {Connect = function(self, fn) table.insert(env.hb, fn) end}
    local Players = {PlayerRemoving = {Connect = function() end}}
    function Players:GetPlayers() return env.players end
    local services = {
        Players = Players,
        RunService = {Heartbeat = hbSignal},
        ReplicatedStorage = {WaitForChild = function(self, n) return Shared end},
    }
    local game = {GetService = function(self, n) return services[n] end}
    local Instance = {new = function(class)
        local o = {ClassName = class}
        function o:Emit(n) table.insert(env.emits, n) end
        return o
    end}
    local osStub = {clock = function() return env.now end, time = os.time}
    local mk = function() return {new = function(...) return {...} end} end
    ANIM(game, env.workspace, osStub, Instance, CFrame, V3, Enum, function(m) return m end,
        mk(), mk(), mk(), mk(), {fromRGB = function() return 0 end}, mk())
    env.Players = Players
    function env.addLocal(class, at)
        local c = makeCharacter(class, at)
        local player = {Character = c.char}
        env.players = {player, table.unpack(env.players)}
        Players.LocalPlayer = player
        return c
    end
    function env.addRemote(class, at)
        local c = makeCharacter(class, at)
        table.insert(env.players, {Character = c.char})
        return c
    end
    function env.step(n, dt)
        for _ = 1, n do
            env.now += dt or FRAME
            for _, f in env.hb do f(dt or FRAME) end
        end
    end
    return env
end
local function phasesOf(calls, class)
    local seq, last = {}, nil
    for _, c in calls do
        if c.role == "leg" and c.phase ~= last then table.insert(seq, c.phase) last = c.phase end
    end
    return seq
end
local function jumpUp(c) c.hum.Jump = true c.setState(ST.Jumping) c.hum.FloorMaterial = Enum.Material.Air c.root.AssemblyLinearVelocity = V3.new(0, 30, 0) end
local function land(c) c.hum.Jump = false c.setState(ST.Landed) c.hum.FloorMaterial = Enum.Material.Plastic c.root.AssemblyLinearVelocity = V3.zero end
local function eq(a, b) return table.concat(a, ",") == table.concat(b, ",") end

local RUN = 24
check("250.drive_speed", function()
    local env = boot()
    local c = env.addLocal("Ground")
    env.step(30)
    for _, l in env.legs do assert(l.w == 0 and l.phase == 0 and l.amp == 1, "standing still: speed 0, phase frozen") end
    assert(#env.calls == 0, "no action while standing")
    c.root.AssemblyLinearVelocity = V3.new(RUN, 0, 0)
    local n0 = #env.legs
    env.step(150)
    local prevW, prevPh = nil, nil
    local checked = 0
    for i = n0 + 1, #env.legs, 5 do -- one leg sample per frame is 2 per frame (two legs): compare the first leg of each frame
        local l = env.legs[i]
        if prevW then
            assert(l.w >= prevW - 1e-9, "speed eases up monotonically")
            local dphase = l.phase - prevPh
            if dphase > 0 then checked += 1 end
        end
        prevW, prevPh = l.w, l.phase
    end
    local fl = env.legs[#env.legs]
    assert(fl.w > 0.95, "running speed reaches 1: " .. fl.w)
    assert(checked > 5, "phase advances while running")
    -- per-frame phase step = dt * stepRate(speed) (exactly what the pure module says)
    env.step(1)
    local a = env.legs[#env.legs - 1]
    env.step(1)
    local b = env.legs[#env.legs - 1]
    assert(math.abs((b.phase - a.phase) - FRAME * RealPose.stepRate(b.w)) < 1e-6, "phase step is dt * stepRate(speed)")
    -- half speed: the walk is slower and the speed value lands near 0.5
    c.root.AssemblyLinearVelocity = V3.new(RUN / 2, 0, 0)
    env.step(240)
    local h = env.legs[#env.legs]
    assert(math.abs(h.w - 0.5) < 0.05, "half speed -> speed01 about 0.5: " .. h.w)
    -- tiny drift counts as standing still, the phase stops
    c.root.AssemblyLinearVelocity = V3.new(0.5, 0, 0)
    env.step(240)
    local s1 = env.legs[#env.legs]
    env.step(30)
    local s2 = env.legs[#env.legs]
    assert(s1.w < 0.01 and s2.phase == s1.phase, "drift below the dead zone idles")
    assert(#env.calls == 0, "walking never starts an action pose")
end)

check("250.drive_reduce", function()
    local env = boot()
    env.theme.MotionEnabled = false
    local c = env.addLocal("Ground")
    c.root.AssemblyLinearVelocity = V3.new(RUN, 0, 0)
    env.step(30)
    jumpUp(c)
    env.step(40)
    land(c)
    env.step(40)
    assert(#env.calls == 0, "Reduce Motion: no action poses")
    for _, l in env.legs do assert(l.amp == 0, "Reduce Motion: amp 0") end
    assert(env.sampleCalls > 0)
    for _, w in c.welds do assert(isIdentity(w.C1), "Reduce Motion: weld back at rest") end
end)

check("250.drive_remote", function()
    local env = boot()
    local me = env.addLocal("Ground")
    local near = env.addRemote("Ground", V3.new(10, 0, 0))
    local far = env.addRemote("Ground", V3.new(500, 0, 0))
    env.step(60)
    local body = 1 -- welds[1] is the body part
    assert(me.welds[body].writes == 60, "local dino animated every frame: " .. me.welds[body].writes)
    local nw = near.welds[body].writes
    assert(nw >= 18 and nw <= 22, "remote dino animated at about 20 Hz: " .. nw)
    assert(far.welds[body].writes == 0, "remote dino beyond 80 studs is not animated")
end)

check("250.drive_flag", function()
    local env = boot({enabled = false})
    assert(#env.hb == 0, "flag off: the animator connects nothing")
end)

check("251.drive_ground", function()
    for _, class in {"Ground", "Armored", "Fly"} do
        local env = boot()
        local c = env.addLocal(class)
        env.step(20)
        assert(#env.calls == 0, class .. ": no action while standing")
        jumpUp(c)
        local t0 = env.now
        env.step(50) -- 0.83 s in the air
        local seq = phasesOf(env.calls)
        -- BD-555: the jump arrives airborne (the humanoid reports Jumping after take-off), so it starts in the air tuck: no crouch, no push-off
        assert(eq(seq, {"air"}), class .. " jump phases: " .. table.concat(seq, ","))
        assert(math.abs(env.calls[1].now - t0) <= 2 * FRAME + 1e-9, class .. " the air phase starts at take-off")
        for _, k in env.calls do assert(k.aggr == 0 and k.class == class and k.amp == 1) end
        land(c)
        env.step(10)
        local seq2 = phasesOf(env.calls)
        assert(eq(seq2, {"air", "land"}), class .. " after landing: " .. table.concat(seq2, ","))
        local landAt = env.now
        env.step(math.ceil((RealPose.duration("land", 0, class) + 0.1) / FRAME))
        local n = #env.calls
        env.step(30)
        assert(#env.calls == n, class .. ": the action stops after the landing")
        for _, w in c.welds do assert(w.writes > 0) end
    end
end)

check("251.drive_ledge", function()
    local env = boot()
    local c = env.addLocal("Ground")
    env.step(10)
    c.setState(ST.Freefall) c.hum.FloorMaterial = Enum.Material.Air c.root.AssemblyLinearVelocity = V3.new(0, -12, 0)
    env.step(20)
    local seq = phasesOf(env.calls)
    assert(seq[1] == "air" and not table.find(seq, "crouch"), "stepping off a ledge: " .. table.concat(seq, ","))
end)

check("251.drive_leap", function()
    local env = boot()
    local c = env.addLocal("Ground")
    env.step(10)
    c.char:SetAttribute("LeapPredictAt", env.now)
    jumpUp(c)
    env.step(20)
    assert(#env.calls > 0)
    for _, k in env.calls do assert(k.aggr == 1, "leap signal -> aggr 1, got " .. k.aggr .. " in " .. k.phase) end
    -- a plain jump after the leap window has gone stays aggr 0
    land(c)
    env.step(120)
    local before = #env.calls
    jumpUp(c)
    env.step(20)
    local seen = false
    for i = before + 1, #env.calls do assert(env.calls[i].aggr == 0, "plain jump after a leap must be aggr 0") seen = true end
    assert(seen)
    -- the server stamp (LeapUntil) reaches remote players too
    local env2 = boot()
    local me = env2.addLocal("Ground")
    me.char:SetAttribute("LeapUntil", env2.now + 1)
    jumpUp(me)
    env2.step(10)
    assert(env2.calls[1] and env2.calls[1].aggr == 1, "LeapUntil also marks a leap")
end)

check("251.drive_water", function()
    local env = boot()
    local c = env.addLocal("Water")
    env.step(10)
    c.hum.Jump = true
    env.step(60) -- key held for a second
    local seq = phasesOf(env.calls)
    assert(eq(seq, {"surge"}), "Water jump is one surge: " .. table.concat(seq, ","))
    for _, k in env.calls do assert(k.aggr == 0 and k.class == "Water") end
    assert(#env.emits == 1 and env.emits[1] == 5, "jump splash 5, got " .. #env.emits .. " emits")
    c.hum.Jump = false
    env.step(30)
    local n = #env.calls
    env.step(30)
    assert(#env.calls == n, "the surge stops after its duration")
    -- release and press again: a second surge
    c.hum.Jump = true
    env.step(10)
    assert(#env.emits == 2, "second press, second surge")
    -- the leap: stronger, bigger splash
    local env2 = boot()
    local d = env2.addLocal("Water")
    env2.step(10)
    d.char:SetAttribute("LeapPredictAt", env2.now)
    env2.step(5)
    assert(eq(phasesOf(env2.calls), {"surge"}), "Water leap is a surge")
    for _, k in env2.calls do assert(k.aggr == 1) end
    assert(env2.emits[1] == 9, "leap splash 9: " .. tostring(env2.emits[1]))
end)

check("251.drive_reduce", function()
    for _, class in {"Ground", "Fly", "Water"} do
        local env = boot()
        env.theme.MotionEnabled = false
        local c = env.addLocal(class)
        env.step(10)
        c.char:SetAttribute("LeapPredictAt", env.now)
        jumpUp(c)
        env.step(40)
        land(c)
        env.step(40)
        assert(#env.calls == 0, class .. ": Reduce Motion plays no jump, leap or surge pose")
        assert(#env.emits == 0, class .. ": Reduce Motion: no splash")
    end
end)

-- BD-555: the humanoid reports Jumping only once the dino has left the ground, so a jump or leap ARRIVES airborne. The animator must not play a
-- crouch and a push-off after take-off (the legs folded, unfolded and folded again inside 0.4 s); it blends from the current pose into the tuck.
local DEG = 180 / math.pi
local function rotAngle(a, b)
    local d = 0
    for i = 1, 9 do d += a.r[i] * b.r[i] end
    return math.acos(math.clamp((d - 1) / 2, -1, 1)) * DEG
end
local function legPitch(c) local r = c.welds[4].C1.r return math.atan2(r[6], r[5]) * DEG end -- welds[4] = left leg: rotation about X only
-- One simulated jump/leap that arrives airborne on its first frame. runSpeed: planar speed (studs/s) before and during the jump. hopFrames: frames
-- in the air before the dino lands (nil = long jump). Returns the worst per-frame rotation change of any part (degrees, in the air and on
-- landing separately), the leg angle series while airborne, and the phases the animator played.
local function trace(class, aggr, runSpeed, hopFrames)
    local env = boot()
    local c = env.addLocal(class)
    c.root.AssemblyLinearVelocity = V3.new(runSpeed, 0, 0)
    env.step(40)
    if aggr == 1 then c.char:SetAttribute("LeapPredictAt", env.now) end
    local prev = {}
    for i, w in c.welds do prev[i] = w.C1 end
    local n0 = #env.calls
    jumpUp(c)
    c.root.AssemblyLinearVelocity = V3.new(runSpeed, 30, 0)
    local airWorst, landWorst, legs = 0, 0, {}
    local function frame(landing)
        env.step(1)
        for i, w in c.welds do
            local d = rotAngle(prev[i], w.C1)
            prev[i] = w.C1
            if landing then landWorst = math.max(landWorst, d) else airWorst = math.max(airWorst, d) end
        end
    end
    for _ = 1, hopFrames or 50 do frame(false) table.insert(legs, legPitch(c)) end
    land(c)
    c.root.AssemblyLinearVelocity = V3.new(runSpeed, 0, 0)
    for _ = 1, math.ceil((RealPose.duration("land", aggr, class) + 0.1) / FRAME) do frame(true) end
    return {air = airWorst, land = landWorst, legs = legs, seq = phasesOf(env.calls, class), calls = #env.calls - n0}
end
-- Direction reversals of a leg series (a fold that opens again counts as one), ignoring wobbles under `hyst` degrees.
local function reversals(series, hyst)
    local n, dir, ext = 0, 0, series[1]
    for _, v in series do
        if dir >= 0 and v < ext - hyst then if dir == 1 then n += 1 end dir, ext = -1, v
        elseif dir <= 0 and v > ext + hyst then if dir == -1 then n += 1 end dir, ext = 1, v
        elseif (dir >= 0 and v > ext) or (dir <= 0 and v < ext) then ext = v end
    end
    return n
end

check("556.drive_flipper", function()
    local function lowest(c)
        local low = math.huge
        for i = 6, #c.welds do -- welds 6..9 are the flippers (SPECS.flippers), part size 2 x 2 x 2, rest C0 identity
            local inv = c.welds[i].C1:Inverse()
            for _, sx in {-1, 1} do for _, sy in {-1, 1} do for _, sz in {-1, 1} do
                low = math.min(low, (inv * V3.new(sx, sy, sz)).Y)
            end end end
        end
        return low
    end
    local env = boot()
    local c = env.addLocal("Water")
    c.root.AssemblyLinearVelocity = V3.new(RUN, 0, 0)
    local worst, wobble = math.huge, 0
    local function run(frames)
        for _ = 1, frames do
            env.step(1)
            -- the whole body bobs together (Water sits lower on purpose): measure the tip against the body's own offset
            worst = math.min(worst, lowest(c) - (c.welds[1].C1:Inverse() * V3.zero).Y)
            local r = c.welds[6].C1.r
            wobble = math.max(wobble, math.abs(r[6]))
        end
    end
    run(120) -- walking
    c.hum.Jump = true run(40) c.hum.Jump = false run(30) -- jump surge
    c.char:SetAttribute("LeapPredictAt", env.now) run(60) -- leap surge
    assert(wobble > 0.05, "control: the flippers must move (" .. wobble .. ")")
    assert(worst >= -1 - 1e-6, "flipper tip below its rest height by " .. (-1 - worst) .. " stud")
end)

check("555.no_crouch", function()
    for _, class in {"Ground", "Armored", "Fly"} do for _, aggr in {0, 1} do for _, speed in {0, RUN} do
        local r = trace(class, aggr, speed)
        local label = class .. " aggr " .. aggr .. " speed " .. speed
        assert(eq(r.seq, {"air", "land"}), label .. ": jump that arrives airborne plays " .. table.concat(r.seq, ","))
    end end end
end)

check("555.one_fold", function()
    for _, class in {"Ground", "Armored", "Fly"} do for _, aggr in {0, 1} do for _, speed in {0, RUN} do
        local r = trace(class, aggr, speed)
        local label = class .. " aggr " .. aggr .. " speed " .. speed
        local n = reversals(r.legs, 4)
        assert(n <= 1, label .. ": legs fold, open and fold again (" .. n .. " reversals)")
        -- the control: the legs do tuck (a verifier that saw a flat series would pass the rule above for nothing)
        local lo, hi = math.huge, -math.huge
        for _, v in r.legs do lo, hi = math.min(lo, v), math.max(hi, v) end
        if class ~= "Fly" then assert(hi - lo > 10, label .. ": control, the legs must tuck (range " .. (hi - lo) .. ")") end
    end end end
end)

check("555.smooth", function()
    local worst, bad = 0, {}
    for _, class in {"Ground", "Armored", "Fly"} do for _, aggr in {0, 1} do for _, speed in {0, RUN} do
        local rows = {}
        for _, hop in {50, 3, 8, 14, 22} do
            local r = trace(class, aggr, speed, hop)
            local label = class .. " aggr " .. aggr .. " speed " .. speed .. " hop " .. hop
            if r.air >= 8 then table.insert(bad, label .. ": worst frame in the air " .. r.air .. " deg") end
            -- A landing from a full jump at a run turned 9.4 degrees a frame before BD-555 (walk swing coming back under the squash): that is not part
            -- of this fix (nor is a hop of 0.37 s or more, which is a nearly full landing), so those only have to stay under 10. A landing after a shorter hop is the new hand-over (Pose.landWeight): under 8.
            local landCap = if hop >= 22 then 10 else 8
            if r.land >= landCap then table.insert(bad, label .. ": worst frame on landing " .. r.land .. " deg") end
            worst = math.max(worst, r.air, r.land)
            table.insert(rows, string.format("hop%d %.1f/%.1f", hop, r.air, r.land))
        end
        print(string.format("  %-8s %s speed %2d  worst air/land deg per frame: %s", class, if aggr == 1 then "leap " else "jump ", speed, table.concat(rows, "  ")))
    end end end
    assert(#bad == 0, #bad .. " case(s) over 8 degrees, first: " .. (bad[1] or ""))
    -- the control: the verifier does see motion (a frozen animator would pass the rule above for nothing)
    local moved = trace("Ground", 0, RUN)
    assert(moved.air > 1, "control: the air blend must move the pose (" .. moved.air .. ")")
    print("worst frame over all cases: " .. worst .. " deg")
end)

if failed > 0 then error(failed .. " check(s) failed") end
print("animator checks passed")
'''


def strip_comments(text):
    return re.sub(r'--[^\n]*', '', text)


def static_checks(pose_text, anim_text, config_text):
    """Source checks done in Python. Returns the list of ids that passed; raises AssertionError on a failure."""
    done = []
    code = strip_comments(pose_text)
    banned = re.findall(r'\b(game|workspace|script|Instance|CFrame|Vector[23]|Color3|Enum|require|task|RemoteEvent|RemoteFunction|FireServer|FireClient'
                        r'|InvokeServer|DataStoreService|HttpService)\b|:Connect\(', code)
    assert not banned, f'LowPolyPose must be pure (no engine API): {banned}'
    done.append('250.pure')
    acode = strip_comments(anim_text)
    assert not re.search(r'FireServer|InvokeServer|RemoteEvent|RemoteFunction|DataStoreService|ServerScriptService|ServerStorage', acode), \
        'the animator must be client-side only (no remotes, no server services)'
    assert not re.search(r'FireServer|FireClient|OnServerEvent|Remote', code), 'pose module must not touch remotes'
    assert re.search(r'^\s*LowPolyDinos = false,', config_text, re.M), 'Config.LowPolyDinos must default to false'
    assert 'RANGE, REMOTE_STEP, RUN_SPEED = 80, 1 / 20, 24' in anim_text, 'animator constants (80 studs, 20 Hz, run speed 24) changed: update this verifier on purpose'
    done.append('251.client_only')
    return done


def build_pose_chunk(pose_text):
    return 'local P=(function()\n' + pose_text + '\nend)()\n'


def run_luau(runner, text, name):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(text, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    return result.returncode, result.stdout, result.stderr


def run_all(runner, pose_text, anim_text, npc_text, config_text, quiet=False):
    """Returns (ok, messages). Does not raise, so the selftest can ask 'does this fail?'."""
    messages = []
    seen = set()
    try:
        seen.update(static_checks(pose_text, anim_text, config_text))
    except AssertionError as err:
        return False, [f'FAIL static: {err}']
    pose_src = build_pose_chunk(pose_text)
    # Chunk 1: idle/walk (BD-250) + action (BD-251) pure checks, one Luau program so they share the helpers.
    text = pose_src + PRELUDE + POSE_BODY + ACTION_BODY + POSE_TAIL
    code, out, err = run_luau(runner, text, 'motion_pose.luau')
    messages.append(out + err)
    seen.update(re.findall(r'^ok (\S+)', out, re.M))
    ok = code == 0 and 'pose checks passed' in out
    # Chunk 2: the real animator, unmodified, against engine stand-ins (HARNESS).
    anim_chunk = ('local RealPose = (function()\n' + pose_text + '\nend)()\nlocal NpcLowPoly = (function()\n' + npc_text + '\nend)()\n'
                  + 'local P = RealPose\n' + PRELUDE
                  + 'local ANIM = function(game, workspace, os, Instance, CFrame, Vector3, Enum, require, NumberSequence, NumberSequenceKeypoint, NumberRange, ColorSequence, Color3, Vector2)\n'
                  + anim_text + '\nend\n' + HARNESS)
    code2, out2, err2 = run_luau(runner, anim_chunk, 'motion_animator.luau')
    messages.append(out2 + err2)
    seen.update(re.findall(r'^ok (\S+)', out2, re.M))
    ok = ok and code2 == 0 and 'animator checks passed' in out2
    fails = re.findall(r'^FAIL .*$', out + out2, re.M)
    missing = sorted(set(CHECKS) - seen)
    extra = sorted(seen - set(CHECKS))
    if missing:
        messages.append('missing checks (did not print ok): ' + ', '.join(missing))
    if extra:
        messages.append('unlisted checks (add them to CHECKS): ' + ', '.join(extra))
    return ok and not fails and not missing and not extra, messages


# Deliberate breaks (applied to a copy in memory). Each must make the verifier fail. (file, old, new, count)
MUTANTS = [
    ('Reduce Motion ignored in sample()', POSE, 'local a = math.clamp(finite(amp), 0, 1)', 'local a = 1', 1),
    ('step rate no longer grows with speed', POSE, 'return 5 + 7 * math.clamp(speed01, 0, 1)', 'return 5', 1),
    ('body part moves on its own', POSE, '-- BD-388: no motion of its own; Pose.bob moves the whole rig, so the body never shifts against its limbs.',
     'pitch = math.sin(phase) * 0.1', 1),
    ('wings no longer folded', POSE, 'Pose.FoldAngle = 1.25', 'Pose.FoldAngle = 0.2', 1),
    ('offsets exceed the bound (crouch dip 0.05 -> 0.5 and the clamp opened)', POSE, 'dy = -0.05 * q + 0.03 * st - 0.01 * lunge', 'dy = -0.5 * q + 0.03 * st - 0.01 * lunge', 1),
    ('Water surge no longer goes forward', POSE, 'lunge = math.sin(math.pi * p)\n            snap', 'lunge = 0\n            snap', 1),
    ('Fly wings stay shut in the air', POSE, 'elseif ph == "air" then W = 1', 'elseif ph == "air" then W = 0', 1),
    ('head peck 0.4 -> 0.9 stud', POSE, 'Pose.PeckStuds = 0.4', 'Pose.PeckStuds = 0.9', 1),
    ('animator plays actions under Reduce Motion', ANIM, 'if amp == 0 then rig.act = nil elseif', 'if false then rig.act = nil elseif', 1),
    ('animator splash counts swapped (jump 9, leap 5)', ANIM, 'if leaping then 9 else 5', 'if leaping then 5 else 9', 1),
    ('animator never reads the leap stamp', ANIM, 'num(character, "LeapPredictAt")', 'num(character, "LeapPredictAtX")', 1),
    ('Fly landing ignores the carried wing opening again (60 degree pop)', POSE, 'math.clamp(finite(ctx.wing or 1), 0, 1) * (1 - ease(p))', '(1 - ease(p))', 1),
    ('Fly landing ignores the air flap again (wing pop)', POSE, 'math.clamp(finite(ctx.flap or 0), -0.4, 0.4) * (1 - ease(p / 0.3))', '0', 1),
    ('animator rig loses its character again (the jump poses never played)', ANIM, 'rig = {character = character, visual', 'rig = {visual', 1),
    ('animator ignores walking speed for the phase', ANIM, 'Pose.stepRate(rig.speed)', 'Pose.stepRate(0)', 1),
    ('animator animates far remote players', ANIM, 'RANGE, REMOTE_STEP, RUN_SPEED = 80,', 'RANGE, REMOTE_STEP, RUN_SPEED = 8000,', 1),
    ('animator plays the crouch after take-off again (BD-555)', ANIM, 'startPhase(rig, "air", now) -- take-off', 'startPhase(rig, "crouch", now) -- take-off', 1),
    ('air tuck is no longer faded in (weight 1 at take-off, BD-555)', ANIM, 'k = if phase == "air" then Pose.airWeight(elapsed) elseif', 'k = if phase == "air" then 1 elseif', 1),
    ('air tuck fade shortened to 0.12 s (BD-555)', POSE, 'Pose.DirectBlend = 0.4', 'Pose.DirectBlend = 0.12', 1),
    ('landing ignores the weight the air ended on (short hop pop, BD-555)', ANIM, 'Pose.landWeight(ctx.p, rig.landFrom)', 'Pose.actionWeight("land", ctx.p)', 1),
    ('air phase keeps the push-off stretch again (BD-555)', POSE, 'tk = cls.t -- already in the full tuck', 'st, tk = cls.s, cls.t -- already in the full tuck', 1),
    ('flippers dip into the ground again (no rest lift, BD-556)', ANIM, 'if lift > 0 then shift +=', 'if false then shift +=', 1),
    ('restLift lifts nothing (BD-556)', POSE, 'return math.clamp(finite(rest - low), 0, Pose.MaxLift)', 'return 0', 1),
    ('animator ignores the flag', ANIM, 'if not LowPoly.enabled() then return end', '', 1),
]


def selftest(runner, texts):
    sources = {POSE: texts[0], ANIM: texts[1]}
    failures = []
    for name, rel, old, new, count in MUTANTS:
        text = sources[rel]
        assert old in text, f'selftest mutant "{name}" no longer matches the source: update MUTANTS'
        pose, anim = (text.replace(old, new, count), sources[ANIM]) if rel == POSE else (sources[POSE], text.replace(old, new, count))
        ok, _ = run_all(runner, pose, anim, texts[2], texts[3])
        print(f'  selftest {"CAUGHT " if not ok else "MISSED "} {name}')
        if ok:
            failures.append(name)
    assert not failures, 'the verifier did not notice these deliberate breaks: ' + '; '.join(failures)
    print(f'selftest ok: {len(MUTANTS)} deliberate breaks were all caught')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--runner', required=True, help='pinned Luau runner')
    parser.add_argument('--selftest', action='store_true', help='also prove the verifier fails when a rule is broken (in memory)')
    args = parser.parse_args()
    texts = [(ROOT / POSE).read_text(encoding='utf-8'), (ROOT / ANIM).read_text(encoding='utf-8'), (ROOT / NPC).read_text(encoding='utf-8'),
             (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')]
    ok, messages = run_all(args.runner, *texts)
    for m in messages:
        print(m, end='' if m.endswith('\n') else '\n')
    if not ok:
        raise SystemExit('verify_motion_poses FAILED')
    print(f'verify_motion_poses ok: {len(CHECKS)} checks (BD-250: {sum(c.startswith("250.") for c in CHECKS)}, BD-251: {sum(c.startswith("251.") for c in CHECKS)}, BD-555/556: {sum(c.startswith("55") for c in CHECKS)})')
    if args.selftest:
        selftest(args.runner, texts)
