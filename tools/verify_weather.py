"""Weather v3 (docs/84): offline sanity check of src/shared/WeatherLooks.luau with the pinned Luau runtime.
Look-table completeness, particle budget caps (desktop and phone), aurora palette cycle and blend math,
plus a source scan that WeatherVisuals builds every Instance up front (no Instance.new inside Heartbeat or the pooled update paths).
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local IDS = {"rain", "thunder", "blizzard", "volcano", "aurora", "quake", "bloodmoon"}
assert(#W.Ids == #IDS)
local REQUIRED = {"tint", "sat", "contrast", "bright", "fog", "decay", "density", "offset", "haze", "glare", "bloom", "rays", "rayTint",
    "shiftTop", "shiftBottom", "dof", "dofFocus", "exposure", "lamp", "glow", "glowBright", "glowRange", "vis", "stars"}
local function rgbOk(c) assert(type(c) == "table" and #c == 3) for i = 1, 3 do assert(c[i] >= 0 and c[i] <= 255, "rgb out of range") end end
-- every event has a complete look and a rig budget; clear has no weather at all
for _, id in IDS do
    local look = W.Looks[id] assert(look, "missing look " .. id)
    for _, key in REQUIRED do assert(look[key] ~= nil, id .. " lacks " .. key) end
    for _, key in {"tint", "fog", "decay", "rayTint", "shiftTop", "shiftBottom", "glow"} do rgbOk(look[key]) end
    if look.amb then rgbOk(look.amb) end
    -- BD-055: every event sets Terrain.Clouds; thunder is the heaviest cover, aurora and clear sky stay open
    assert(look.cloudCover >= 0 and look.cloudCover <= 1 and look.cloudDensity >= 0 and look.cloudDensity <= 1, id .. " cloud range")
    rgbOk(look.cloudColor)
    assert(look.density > 0 and look.density <= 1, id .. " density")
    assert(look.haze > 0 and look.haze <= 10, id .. " haze")
    assert(look.vis >= 40 and look.vis <= 600 and look.fogStart < look.vis, id .. " fog distances")
    assert(look.fogStart >= 25 or id == "blizzard", id .. " near area (25 studs) stays clear")
    assert(look.dof >= 0 and look.dof <= 1 and look.dofFocus >= 30)
    assert(look.exposure <= 0 and look.exposure >= -1, id .. " exposure")
    assert(look.lamp >= 0 and look.lamp <= 2 and look.glowBright <= 4)
    assert(look.bloom <= 1.5 and look.sat <= 1 and look.sat >= -1)
    assert(W.Rigs[id], "missing rig budget " .. id)
    local c, big = W.concurrent(id)
    assert(c <= W.Budget.concurrent, id .. " concurrent particles " .. c)
    assert(big <= W.Budget.bigConcurrent, id .. " big sprites " .. big)
    -- fog banks limit the view in every event
    assert(W.Rigs[id].bank, id .. " lacks distance fog banks")
end
assert(W.Looks.clear.density == 0 and W.Looks.clear.dof == 0)
-- blizzard whiteout is 40..60 studs; the densest events are the shortest views; aurora keeps the widest view
assert(W.Looks.blizzard.vis >= 80 and W.Looks.blizzard.vis <= 120, "blizzard view distance 80..120 (owner: must stay readable)")
for _, id in IDS do assert(W.Looks[id].vis >= W.Looks.blizzard.vis) end
assert(W.Looks.aurora.vis >= 250 and W.Looks.aurora.vis <= 600)
-- denser fog = shorter view
local byDensity = table.clone(IDS) table.sort(byDensity, function(a, b) return W.Looks[a].density > W.Looks[b].density end)
for i = 2, #byDensity do assert(W.Looks[byDensity[i - 1]].vis <= W.Looks[byDensity[i]].vis + 100, "density and visibility disagree") end
assert(W.Looks.blizzard.density == W.Looks[byDensity[1]].density)
-- stronger than v2 (recorded v2 densities): every event at least 1.3x denser than before
-- readability (owner 2026-10-15: volcano, blizzard and quake were opaque walls): at 30 studs the fog may cover at most 10%,
-- the dino and ground stay visible to at least 40 studs in volcano, quake, rain and thunder
for _, id in IDS do
    local look = W.Looks[id]
    local at30 = math.max(0, 30 - look.fogStart) / (look.vis - look.fogStart)
    assert(at30 <= .1, id .. " fog at 30 studs " .. at30)
end
for _, id in {"volcano", "quake", "rain", "thunder", "bloodmoon", "aurora"} do assert(W.Looks[id].fogStart >= 40, id .. " keeps 40 studs clear") end
assert(W.Looks.volcano.fog[1] <= 170 and W.Looks.volcano.sat <= .3 and W.Looks.volcano.bloom <= .7, "volcano is a brown-orange haze, not a red wall")
assert(W.Looks.volcano.density <= .45 and W.Looks.quake.density <= .5 and W.Looks.blizzard.density <= .85, "atmosphere density stays readable")
-- phone density halves every rate, so the phone budget is half
for _, id in IDS do local c = W.concurrent(id) assert(c * .5 <= W.Budget.concurrent / 2) end
assert(W.Budget.bolts >= 3 and W.Budget.bombs >= 5 and W.Budget.beams <= 160)
-- earthquake v2 (owner 2026-10-15): a world event, not an aura. No falling rubble streaks; capped, pooled cracks away from the dino
assert(W.Rigs.quake.rubble == nil, "no falling rubble sticks in the air")
assert(W.Budget.cracks <= 4 and W.Budget.cracksPhone <= 2 and W.Budget.cracksPhone >= 1 and W.Budget.rocksPerCrack <= 4, "crack and rock caps")
-- QA 2026-10-16: the blood moon stays a soft sky prop (not a third of a phone screen) and the title card sits below the toast
assert(W.Moon.core <= 48 and W.Moon.halos[3] <= 150 and W.Moon.distance >= 140, "blood moon is a moderate sky prop")
assert(W.Title.y - W.Title.height / 2 >= .26 and W.Title.width <= .62 and W.Title.height <= .1, "title card below the toast, soft and narrow")
local Q = W.Quake
assert(Q.grow >= .3 and Q.grow <= .8, "cracks grow over about half a second")
assert(Q.life[1] >= 2 and Q.life[2] <= 6 and Q.close > 0, "cracks close after a few seconds")
assert(Q.pulseEvery[1] >= 2 and Q.pulseEvery[2] <= 8 and Q.pulseSeconds <= 1.5, "short tremor pulses every few seconds")
assert(Q.shake > 0 and Q.shake <= .5, "gentle camera rumble")
assert(Q.clearOfDino >= 8 and Q.minDist > Q.clearOfDino and Q.maxDist <= 90 and Q.viewCone <= 70, "cracks open in view, never under the dino")
assert(Q.width[1] >= 1 and Q.wobbleDegrees <= 4 and Q.wobbleMax <= 12 and Q.propMaxSize <= 10, "readable cracks, slight wobble of small props only")

-- BD-348 (QA 2026-10-16): rain is denser with long streaks near the camera, aurora ribbons start at the horizon, quake has a cue at the dino
assert(W.Rigs.rain.near and W.Rigs.thunder.near and W.Rigs.rain.streaks.rate >= 2000 and W.Rigs.rain.splash.rate >= 500, "rain is clearly visible at phone size")
assert(W.Looks.rain.tint[3] > W.Looks.rain.tint[1] + 60 and W.Looks.rain.sat <= -.2, "rain grade is slightly cooler")
assert(W.Aurora.baseY <= 0 and W.Aurora.alpha <= .65 and W.Aurora.horizonGlow >= .7, "aurora ribbons reach the horizon and the horizon glows")
assert(W.Rigs.aurora.bank.rate >= 12, "aurora horizon band")
assert(W.Quake.feetPuff >= 4 and W.Quake.feetPuffPhone >= 2 and W.Quake.decalAhead[1] >= 6 and W.Quake.decalAhead[2] < W.Quake.minDist, "quake puff at the feet, decal close and in front")
assert(W.Quake.shake <= .3, "tiny camera shake")
-- BD-349: emitted rate and steady-state concurrent particles per Weather level (Full 1, Lite .5, Off 0) and device (phone .5 of desktop)
local LEVEL = {full = 1, lite = .5, off = 0}
for _, id in IDS do
    local c = W.concurrent(id)
    for level, f in LEVEL do
        assert(c * f <= W.Budget.concurrent and c * f * .5 <= W.Budget.concurrent / 2, id .. " " .. level .. " within budget")
    end
    print(("weather particles %-9s desktop full %5d lite %5d off 0 | phone full %5d lite %5d"):format(id, c, c * .5, c * .5, c * .25))
end
-- aurora: palette loops, stays bright, passes through green, teal, violet and magenta, and cycles in 20..30 s
assert(W.AuroraPeriod >= 20 and W.AuroraPeriod <= 30)
local a, b = W.palette(0), W.palette(1)
for i = 1, 3 do assert(math.abs(a[i] - b[i]) < 1e-6, "palette must loop") end
local seen = {green = false, teal = false, violet = false, magenta = false}
for step = 0, 1000 do
    local c = W.palette(step / 1000) rgbOk(c)
    assert(math.max(c[1], c[2], c[3]) >= 200, "aurora colours stay bright")
    if c[2] > 230 and c[1] < 90 and c[3] < 180 then seen.green = true end
    if c[2] > 200 and c[3] > 200 and c[1] < 90 then seen.teal = true end
    if c[3] > 240 and c[1] > 130 and c[1] < 180 and c[2] < 120 then seen.violet = true end
    if c[1] > 240 and c[3] > 190 and c[2] < 110 then seen.magenta = true end
end
for name, ok in seen do assert(ok, "aurora palette never reaches " .. name) end
-- slow, continuous motion: no jump bigger than 25 per channel between frames 1/30 s apart, and noise keeps cycles from repeating exactly
local worst = 0
for step = 0, 30 * 120 do
    local c0, c1 = W.aurora(step / 30, .4), W.aurora((step + 1) / 30, .4)
    for i = 1, 3 do worst = math.max(worst, math.abs(c0[i] - c1[i])) end
end
assert(worst < 25, "aurora hue jump " .. worst)
local c0, c1 = W.aurora(1, 0), W.aurora(1 + W.AuroraPeriod, 0)
assert(math.abs(c0[1] - c1[1]) + math.abs(c0[2] - c1[2]) + math.abs(c0[3] - c1[3]) > 0.5, "noise must vary the cycle")
-- offsets spread hue across the sky
local s0, s1 = W.aurora(5, 0), W.aurora(5, .5)
assert(math.abs(s0[1] - s1[1]) + math.abs(s0[2] - s1[2]) + math.abs(s0[3] - s1[3]) > 100, "offsets spread the hue")

-- blend math
local m = W.mix({0, 100, 200}, {100, 200, 0}, .5) assert(m[1] == 50 and m[2] == 150 and m[3] == 100)
assert(W.lerp(2, 4, .25) == 2.5 and W.scale({100, 50, 0}, .5)[1] == 50)
assert(W.strength(1, true) == 1 and W.strength(1, false) == .5 and W.strength(0, false) == 0, "Reduce Motion halves the grade")
local C = W.Looks.clear
local s0, e0 = W.fog(W.Looks.blizzard, 0, C, math.huge) assert(s0 == C.fogStart and math.abs(e0 - C.vis) < 1e-3)
local s1, e1 = W.fog(W.Looks.blizzard, 1, C, math.huge) assert(s1 == 25 and math.abs(e1 - 110) < 1e-6)
local _, eh = W.fog(W.Looks.blizzard, .5, C, math.huge) assert(eh > 110 and eh < 400, "fog closes in smoothly (1/distance blend): " .. eh)
-- BD-213 soft visibility: clear weather keeps a gentle far haze; per device class the fog end stays inside the prop cull
-- radius (props detach/attach only where they are already fully fogged), the fade spans >= 55% of the view, the near
-- 25 studs stay clear (blizzard whiteout excepted) and FogEnd only ever closes in smoothly over the event ramp.
assert(C.fogStart >= 150 and C.vis >= 900 and C.vis <= 1500, "clear weather: fog starts far, no milky wash")
assert(W.ClearFog.Desktop.fogStart >= 400 and W.ClearFog.Desktop.fogEnd >= 1400, "desktop clear fog 400..1400")
assert(W.ClearFog.Tablet.fogStart >= 250 and W.ClearFog.Tablet.fogEnd >= 700, "tablet clear fog 250..700")
assert(W.capFor("Desktop", 440) >= 1400 and W.capFor("Phone", 190) == W.fogCap(190), "phone stays cull-capped")
assert(W.clearFor("Phone") == W.Looks.clear and W.clearFor("Desktop").vis == 1400)
assert(C.sat >= 0 and C.sat <= .15 and C.contrast >= 0 and C.bloom == 0 and C.dof == 0 and C.haze == 0, "clear grade crisp: saturation >= 0, no bloom, no DoF")
assert(W.CullMargin < 1 and W.SoftRatio <= .5)
for class, radius in CULL do
    local cap = W.fogCap(radius)
    for _, id in {"clear", table.unpack(IDS)} do
        local prevEnd = math.huge
        for step = 0, 20 do
            local s, e = W.fog(W.Looks[id], step / 20, C, cap)
            assert(e < radius, class .. " " .. id .. ": fog end " .. e .. " must be inside the cull radius " .. radius)
            assert(e - s >= e * (1 - W.SoftRatio) - 1e-6, class .. " " .. id .. ": fog fade too short (reads as a wall)")
            assert(s >= 25 or (id == "blizzard" and s >= 12), class .. " " .. id .. ": near area must stay clear, start " .. s)
            assert(math.max(0, 30 - s) / (e - s) <= .12, class .. " " .. id .. ": fog at 30 studs")
            assert(e <= prevEnd + 1e-6, class .. " " .. id .. ": view must close in smoothly") prevEnd = e
        end
    end
end
assert(W.Looks.thunder.cloudCover == 1 and W.Looks.aurora.cloudCover <= .2 and W.Looks.clear.cloudCover < 0, "cloud cover per event")
assert(W.Swell.peak <= .15 and W.Swell.rate <= 1, "Reduce Motion thunder swell is slow and soft")
print("WeatherLooks passed")

-- weather audio table: ids stay empty until uploaded, volumes are kids-quiet, every event has a bed, fades are bounded
assert(WS.MaxBed <= .3 and WS.MaxAccent <= .5 and WS.FadeSeconds >= 1.5)
for name, entry in WS.Sounds do
    assert(type(entry.id) == "string" and entry.volume > 0, name)
    assert(entry.volume <= (if entry.loop then WS.MaxBed else WS.MaxAccent), name .. " too loud")
    assert(entry.id == "" or WS.normalizeId(entry.id), name .. " malformed id")
end
for _, id in IDS do
    local event = WS.Events[id] assert(event and WS.Sounds[event.bed] and WS.Sounds[event.bed].loop, id .. " needs a looping bed")
    for cue, list in event.cues or {} do for _, item in list do assert(WS.Sounds[item[1]] and not WS.Sounds[item[1]].loop and item[2] >= 0, cue) end end
end
assert(WS.normalizeId("") == nil and WS.normalizeId("rbxassetid://0") == nil and WS.normalizeId("abc") == nil and WS.normalizeId("rbxassetid://12") == "rbxassetid://12")
assert(WS.bedTarget("rain_bed", "rain", 1, true) == WS.Sounds.rain_bed.volume and WS.bedTarget("rain_bed", "thunder", 1, true) == 0 and WS.bedTarget("rain_bed", "rain", 1, false) == 0)
assert(WS.bedTarget("rain_bed", "rain", .5, true) == WS.Sounds.rain_bed.volume * .5)
local lvl = WS.step(0, .2, 1) assert(lvl > 0 and lvl < .2 and WS.step(.2, 0, 100) == 0 and WS.step(0, .2, 100) == .2, "fades are rate limited")
assert(#WS.cue("thunder", "strike") == 2 and #WS.cue("rain", "strike") == 0 and #WS.cue("volcano", "eruption") == 1)
local fired = {} WS.connect(function(n) table.insert(fired, n) end) WS.fire("quake") assert(fired[1] == "quake")
print("WeatherSounds passed")

-- BD-131 reader (WeatherTextures + the real EffectAssets): an EMPTY slot gives the built-in look unchanged, a valid id gives the texture plus
-- the flipbook layout / mode, and the Weather level (Full / Lite / Off), Reduce Motion, phone density and the phone beam budget are respected.
local FAKE = "rbxassetid://123456789"
local function withIds(ids, fn)
    local saved = {}
    for key, id in ids do saved[key] = Assets.Requested[key].id Assets.Requested[key].id = id end
    local ok, err = pcall(fn)
    for key, id in saved do Assets.Requested[key].id = id end
    assert(ok, err)
end
local function allSlots(id) local t = {} for _, key in WT.Keys do t[key] = id end return t end
assert(#WT.Keys == 9)
for _, key in WT.Keys do assert(Assets.Requested[key], key .. " is an EffectAssets slot") assert(WT.Tuning[key], key .. " has a tuning table") end
-- rigs a tuning entry may name: a WeatherLooks rig, or one of the pooled one-shots built by WeatherVisuals
local POOLED = {sparks = true, crackDust = true, feetPuff = true, trunk = true, fork = true, disc = true}
for _, key in WT.Keys do
    for rig, tune in WT.Tuning[key] do
        local inRigs = false
        for _, id in IDS do if W.Rigs[id][rig] then inRigs = true end end
        assert(inRigs or POOLED[rig], key .. "." .. rig .. " names no weather rig")
        assert((tune.rate or 1) <= 1, key .. "." .. rig .. " never emits more than the built-in rig (budget)")
        if tune.sizeScale then assert(tune.sizeScale >= .5 and tune.sizeScale <= 3, key .. "." .. rig .. " size scale") end
        if tune.squash then assert(#tune.squash == 2 and tune.squash[1] <= 0 and tune.squash[1] >= -30, key .. "." .. rig .. " squash") end
        if tune.transparency and type(tune.transparency) == "table" then for _, v in tune.transparency do assert(v >= 0 and v <= 1, key .. "." .. rig .. " transparency") end end
        if tune.lightEmission then assert(tune.lightEmission >= 0 and tune.lightEmission <= 1) end
    end
end
-- 1. empty id (also malformed ids): no plan, rate 1, nothing changes
for _, bad in {"", "rbxassetid://", "abc", "12345"} do
    withIds(allSlots(bad), function()
        for _, key in WT.Keys do
            for rig in WT.Tuning[key] do
                assert(WT.plan(Assets, key, rig) == nil, key .. "." .. rig .. " with id '" .. bad .. "' must keep the built-in sprite")
                assert(WT.rate(WT.plan(Assets, key, rig)) == 1)
            end
            assert(not Assets.isReal(key))
        end
        assert(WT.emitRate(100, nil, 1, 1, true) == 100 and WT.emitRate(100, nil, 1, .5, true) == 50, "no plan: built-in rate")
    end)
end
-- 2. valid id: the texture, the right flipbook layout and mode, tuning attached; 3. Weather level and motion
withIds(allSlots(FAKE), function()
    for _, key in WT.Keys do
        local sheet = Assets.Sheets[key] ~= nil
        for rig, tune in WT.Tuning[key] do
            local plan = WT.plan(Assets, key, rig)
            assert(plan and plan.texture == FAKE and plan.key == key and plan.rig == rig, key .. "." .. rig .. " uses the texture")
            assert(plan.tune == tune)
            if sheet then
                assert(plan.layout == "Grid4x4" and Assets.Sheets[key].grid == 4 and Assets.Sheets[key].size == 512, key .. " is a 4x4 sheet of 128 px cells")
                assert(plan.mode == Assets.FlipbookMode[key], key .. " flipbook mode")
                assert(plan.startRandom == (plan.mode ~= "OneShot"))
                assert((plan.framerate ~= nil) == (plan.mode == "Loop"), key .. " framerate only for Loop")
            else
                assert(plan.layout == "None" and plan.mode == nil and plan.framerate == nil and plan.startRandom == nil, key .. " is a single image")
            end
        end
    end
    for _, key in {"snowFlakeSheet", "ashFlake", "emberSpark", "dustSand", "bloodMoonMotes"} do assert(WT.plan(Assets, key, next(WT.Tuning[key])).mode == "Random") end
    local curtain = WT.plan(Assets, "auroraCurtain", "curtain")
    assert(curtain and curtain.layout == "Grid4x4" and curtain.mode == "Loop" and curtain.framerate == Assets.LoopFps, "aurora curtain loops its 16 frames")
    for _, key in {"rainStreak", "lightningBolt", "bloodMoonDisc"} do assert(not Assets.Sheets[key] and WT.plan(Assets, key, next(WT.Tuning[key])).layout == "None") end
    -- a rig without a tuning entry still gets the texture with empty tuning (never an error)
    local plain = WT.plan(Assets, "rainStreak", "nothing") assert(plain and next(plain.tune) == nil and WT.rate(plain) == 1)
    -- Weather level: Full 1, Lite .5, Off 0; Calm / Reduce Motion emits nothing; phone density halves; never above the built-in rate
    local checked = 0
    for _, id in IDS do
        for rig, spec in W.Rigs[id] do
            for _, key in WT.Keys do
                local plan = WT.plan(Assets, key, rig)
                if plan and WT.Tuning[key][rig] then
                    checked += 1
                    local full, lite = WT.emitRate(spec.rate, plan, 1, 1, true), WT.emitRate(spec.rate, plan, .5, 1, true)
                    assert(full <= spec.rate + 1e-9, id .. "." .. rig .. " textured rate stays within the built-in rate")
                    assert(math.abs(lite - full * .5) < 1e-9, id .. "." .. rig .. " Lite is half of Full")
                    assert(WT.emitRate(spec.rate, plan, 0, 1, true) == 0, id .. "." .. rig .. " Weather Off emits nothing")
                    assert(WT.emitRate(spec.rate, plan, 1, 1, false) == 0, id .. "." .. rig .. " Reduce Motion emits nothing")
                    assert(math.abs(WT.emitRate(spec.rate, plan, 1, .5, true) - full * .5) < 1e-9, id .. "." .. rig .. " phone density halves")
                end
            end
        end
    end
    assert(checked >= 8, "level checks ran for the textured rigs: " .. checked)
end)
-- 4. one slot filled, the rest empty: only that texture is in use
local onlyRain = allSlots("") onlyRain.rainStreak = FAKE -- 2026-10-17: the other slots are bound to real uploads now, so empty them explicitly
withIds(onlyRain, function()
    assert(WT.plan(Assets, "rainStreak", "streaks") and not WT.plan(Assets, "snowFlakeSheet", "snow") and not WT.plan(Assets, "lightningBolt", "trunk"))
end)
-- 5. phone beam budget: a textured bolt is 1 trunk + 2 forks (the built-in bolt is 18 + 2); all bolts together fit the phone budget
assert(WT.BoltBeams.trunk == 1 and WT.BoltBeams.forks == 2)
assert(W.Budget.bolts * (WT.BoltBeams.trunk + WT.BoltBeams.forks) <= PHONE_BEAMS, "textured bolts fit the phone beam budget")
assert(WT.BoltBeams.trunk + WT.BoltBeams.forks < 2 * 9 + 2, "a textured bolt uses fewer beams than the built-in one")
assert(WT.Tuning.lightningBolt.trunk.tile >= 2 and WT.Tuning.lightningBolt.trunk.width <= 40, "bolt strip tiles undistorted and stays a calm width")
assert(WT.Tuning.bloodMoonDisc.disc.scale * W.Moon.core <= 80, "moon disc stays a moderate sky prop")
assert(W.Rigs.aurora.curtain and W.Rigs.aurora.curtain.big, "the aurora curtain is in the particle budget")
print("WeatherTextures passed")
'''


def cull_radii():
    cfg = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    radii = {k: int(v) for k, v in re.findall(r'(Phone|Tablet|Desktop) = \{radius = (\d+)', cfg)}
    assert set(radii) == {'Phone', 'Tablet', 'Desktop'}, 'WorldCulling radii not found in Config'
    return 'local CULL={' + ','.join(f'{k}={v}' for k, v in radii.items()) + '}\n'


def phone_beams():
    return int(json.loads((ROOT / 'tools/qa/phone_budgets.json').read_text(encoding='utf-8'))['phone']['beams']['value'])


def script():
    return (cull_radii() + f'local PHONE_BEAMS={phone_beams()}\n' + 'local W=' + module('src/shared/WeatherLooks.luau') + '\nlocal WS=' + module('src/shared/WeatherSounds.luau')
            + '\nlocal Assets=' + module('src/shared/EffectAssets.luau') + '\nlocal WT=' + module('src/shared/WeatherTextures.luau') + '\n' + BODY)


def scan():
    src = (ROOT / 'src/client/WeatherVisuals.client.luau').read_text(encoding='utf-8')
    assert 'WeatherLooks' in src and 'Theme.MotionEnabled' in src
    # everything runtime-created must sit before the main loop: no Instance.new / :Clone() after the Heartbeat connection
    loop = src.index('RunService.Heartbeat:Connect')
    tail = src[loop:]
    assert 'Instance.new' not in tail and ':Clone()' not in tail, 'no Instance creation inside the per-frame loop'
    # pooled updates must not create Instances either
    for name in ('local function updateBolts', 'local function updateRings', 'local function updateBursts', 'local function updateBombs', 'local function updateAurora'):
        start = src.index(name)
        end = src.index('\nend\n', start)
        assert 'Instance.new' not in src[start:end], name + ' creates Instances'
    assert 'Debris' not in src, 'one-shots are pooled, not Debris items'
    for name in ('local function updateQuake',):
        start = src.index(name)
        assert 'Instance.new' not in src[start:src.index('\nend\n', start)], name + ' creates Instances'
    # earthquake v2: no radial lines/rings around the dino, no spark-stick chips; cracks are wedge shapes, rumble only with motion
    for gone in ('QuakeRing', 'quakeChips', 'quakeBurst(', 'rubble'):
        assert gone not in src, 'old quake effect still present: ' + gone
    assert 'Instance.new("WedgePart")' in src and 'QuakeCrackGlow' in src and 'cracksPhone' in src, 'quake cracks are pooled wedge shapes with a glow'
    assert 'if motion and now<quakeUntil then shake=' in src, 'quake rumble is synced to pulses and off with Reduce Motion'
    assert 'openCrack(root,not motion)' in src, 'Reduce Motion keeps static cracks'
    stop = src[src.index('local function stopOneShots()'):]
    assert 'stopQuake()' not in stop[:stop.index('\nend\n')],'Reduce Motion must not hide the (static) quake cracks'
    assert 'WS.fire("quake")' in src, 'quake sound hook kept'
    # FX v3: quake dust puffs (ambient + crack bursts) use the anime smoke flipbook through EffectAssets, never a raw id here
    assert src.count('Texture=DUST_FX.Texture,FlipbookLayout=DUST_FX.FlipbookLayout,FlipbookMode=DUST_FX.FlipbookMode') == 3, 'quake dust uses smoke-anime'
    assert 'Assets.resolve("smokeSheet")' in src and 'Assets.isAdditive("smokeSheet")' in src and not re.search(r'rbxassetid://\d+', src), 'dust texture comes from EffectAssets'
    assert 'auroraRing' not in src and 'SurfaceGui' not in src, 'no ground ring or square sky shell around the dino (owner 2026-10-15)'
    # BD-213: no opaque geometry inside FogEnd: no fog-coloured sky box, nothing sized from the fog distance
    assert 'WeatherSkyBox' not in src and 'updateDome' not in src, 'no opaque sky box inside FogEnd (reads as a wall)'
    assert not re.search(r'Size\s*=[^\n]*fog(End|Cap)', src, re.I), 'no part sized from the fog distance'
    # BD-348/349: rain near-streaks, aurora horizon, quake feet puff + decal; Calm motion = no particles, no shake; Off = rate 0
    assert 'emitter(nearSky,id,"near"' in src and 'WL.Aurora.baseY' in src and 'QuakeCrackDecal' in src and 'QuakeFeetDust' in src
    assert 'weatherFactor' in src and 'on=motion and weatherId==activeId' in src and 'item.e.Enabled=on and weatherFactor>0' in src, 'Weather Off / Calm turn the particles off'
    assert 'if motion then feetHolder.CFrame' in src, 'no feet puff with Reduce Motion'
    assert 'WL.fog(look,t,CLEAR,fogCap)' in src and 'WorldCulling' in src, 'fog end must be capped by the device cull radius'
    assert 'CelestialBodiesShown' in src, 'default sun and moon hidden during events (one moon only)'
    # BD-131 reader: every texture is read through WeatherTextures; an empty slot changes nothing (no plan = props returned untouched, no extra Instance)
    wt = (ROOT / 'src/shared/WeatherTextures.luau').read_text(encoding='utf-8')
    keys = re.findall(r'"(\w+)"', wt[wt.index('WT.Keys'):wt.index('WT.Tuning')])
    assert len(keys) == 9
    for key in keys:
        assert f'"{key}"' in src, key + ' slot has no reader in WeatherVisuals'
    assert 'if not plan then return props end' in src and 'rateOf' in src, 'tex() leaves the built-in props alone while the slot is empty'
    assert 'if WT.plan(Assets,"auroraCurtain","curtain") then' in src, 'curtain emitter exists only with a texture'
    assert 'if MOON_DISC then' in src and 'if BOLT_TRUNK then' in src, 'moon disc and bolt trunk exist only with a texture'
    assert 'for i=2,(if BOLT_TRUNK then 1 else 10) do' in src, 'built-in segment beams are skipped only for a textured bolt'
    assert 'SPARK_SCALE' in src and 'rbxassetid' not in src
    assert 'moonCore.Transparency=if moonImage then 1 else lerpNum(1,.04,k)' in src, 'built-in moon ball unchanged without a disc'
    assert 'Enum.TextureMode.Wrap' in src and 'tune.width*tune.tile' in src, 'bolt strip tiles along the beam'
    assert '(Enum.ParticleFlipbookLayout::any)[plan.layout]' in src and 'FlipbookFramerate' in src, 'flipbook layout, mode and loop rate come from the plan'
    audio = (ROOT / 'src/client/WeatherAudio.client.luau').read_text(encoding='utf-8')
    assert 'WeatherSounds' in audio and 'normalizeId' in audio
    sfx = (ROOT / 'src/shared/Sfx.luau').read_text(encoding='utf-8')
    volume = float(re.search(r'weather_start = \{id = "[^"]*", volume = ([\d.]+)', sfx).group(1))
    assert volume <= .25, 'weather_start must stay quiet'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'weather.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
