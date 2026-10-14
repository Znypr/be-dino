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
assert(W.Looks.blizzard.vis >= 40 and W.Looks.blizzard.vis <= 60)
for _, id in IDS do assert(W.Looks[id].vis >= W.Looks.blizzard.vis) end
assert(W.Looks.aurora.vis >= 250 and W.Looks.aurora.vis <= 600)
-- denser fog = shorter view
local byDensity = table.clone(IDS) table.sort(byDensity, function(a, b) return W.Looks[a].density > W.Looks[b].density end)
for i = 2, #byDensity do assert(W.Looks[byDensity[i - 1]].vis <= W.Looks[byDensity[i]].vis + 100, "density and visibility disagree") end
assert(W.Looks.blizzard.density == W.Looks[byDensity[1]].density)
-- stronger than v2 (recorded v2 densities): every event at least 1.3x denser than before
local V2 = {rain = .28, thunder = .3, blizzard = .68, volcano = .4, aurora = .24, quake = .34, bloodmoon = .16}
for id, old in V2 do assert(W.Looks[id].density >= old * 1.3, id .. " must be stronger than v2") end
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
local s1, e1 = W.fog(W.Looks.blizzard, 1, 0, 100000) assert(s1 == 12 and math.abs(e1 - 50) < 1e-6)
local _, eh = W.fog(W.Looks.blizzard, .5, 0, 100000) assert(eh > 50 and eh < 200, "fog closes in smoothly (1/distance blend): " .. eh)
print("WeatherLooks passed")
'''


def script():
    return 'local W=' + module('src/shared/WeatherLooks.luau') + '\n' + BODY


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
