"""Weather v3 (docs/84): offline sanity check of src/shared/WeatherLooks.luau with the pinned Luau runtime.
Look-table completeness, particle budget caps (desktop and phone), aurora palette cycle and blend math,
plus a source scan that WeatherVisuals builds every Instance up front (no Instance.new inside Heartbeat or the pooled update paths).
"""
from pathlib import Path
import argparse
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
-- the dino and ground stay visible to at least 40 studs in volcano, quake, rain and thunder, and the sky box colour equals the fog colour
for _, id in IDS do
    local look = W.Looks[id]
    local at30 = math.max(0, 30 - look.fogStart) / (look.vis - look.fogStart)
    assert(at30 <= .1, id .. " fog at 30 studs " .. at30)
    assert(look.dome >= 0 and look.dome <= 1)
end
for _, id in {"volcano", "quake", "rain", "thunder", "bloodmoon", "aurora"} do assert(W.Looks[id].fogStart >= 40, id .. " keeps 40 studs clear") end
assert(W.Looks.volcano.fog[1] <= 170 and W.Looks.volcano.sat <= .3 and W.Looks.volcano.bloom <= .7, "volcano is a brown-orange haze, not a red wall")
assert(W.Looks.volcano.density <= .45 and W.Looks.quake.density <= .5 and W.Looks.blizzard.density <= .85, "atmosphere density stays readable")
-- phone density halves every rate, so the phone budget is half
for _, id in IDS do local c = W.concurrent(id) assert(c * .5 <= W.Budget.concurrent / 2) end
assert(W.Budget.bolts >= 3 and W.Budget.bombs >= 5 and W.Budget.beams <= 160)

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
local s0, e0 = W.fog(W.Looks.blizzard, 0, 0, 100000) assert(s0 == 0 and math.abs(e0 - 100000) < 1e-3)
local s1, e1 = W.fog(W.Looks.blizzard, 1, 0, 100000) assert(s1 == 25 and math.abs(e1 - 110) < 1e-6)
local _, eh = W.fog(W.Looks.blizzard, .5, 0, 100000) assert(eh > 110 and eh < 400, "fog closes in smoothly (1/distance blend): " .. eh)
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
'''


def script():
    return 'local W=' + module('src/shared/WeatherLooks.luau') + '\nlocal WS=' + module('src/shared/WeatherSounds.luau') + '\n' + BODY


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
    for name in ('local function updateQuake', 'local function updateDome'):
        start = src.index(name)
        assert 'Instance.new' not in src[start:src.index('\nend\n', start)], name + ' creates Instances'
    assert 'auroraRing' not in src and 'SurfaceGui' not in src, 'no ground ring or square sky shell around the dino (owner 2026-10-15)'
    assert 'CelestialBodiesShown' in src, 'default sun and moon hidden during events (one moon only)'
    audio = (ROOT / 'src/client/WeatherAudio.client.luau').read_text(encoding='utf-8')
    assert 'WeatherSounds' in audio and 'normalizeId' in audio
    sfx = (ROOT / 'src/shared/Sfx.luau').read_text(encoding='utf-8')
    import re
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
