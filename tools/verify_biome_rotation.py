"""BD-1314 (docs/250 S1): proof of the biome rotation (src/shared/BiomeRotation.luau) in the pinned Luau runner, plus its wiring.

    python tools/verify_biome_rotation.py --runner <luau.exe>

1. The real module, run bare:
   - the loop is Meadow, Jungle, Desert Canyon, Frozen Tundra, Volcano, 8 minutes each, deterministic from the time;
   - the phases are calm, then warning (Warn s), then storm (StormHalf s either side of the change);
   - the storm always brings the arriving biome;
   - the look and the terrain colours blend continuously across every change (no jump), and far from a change from == to;
   - every look is complete and every terrain colour stays inside the soft-colour rule (channels 0..245);
   - the banner words name the current and the next biome.
2. Every storm is a real weather look (Shared/WeatherLooks), so the existing rigs draw it.
3. Wiring:
   - Config ships BiomeRotationEnabled = false, the playtest profile turns it on, and enabled() needs WorldV3Enabled too;
   - Bootstrap starts BiomeService;
   - WeatherVisuals and PhoneHud gate every biome line on the flag.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def wrapped(rel):
    return '(function()\n' + read(rel) + '\nend)()'


BODY = r'''
local B = Biome
assert(table.concat(B.Order, ",") == "meadow,jungle,desert,tundra,volcano", "order")
assert(B.Seconds == 480, "8 minutes per biome (owner pick)")
assert(not B.enabled({BiomeRotationEnabled = true}) and not B.enabled({WorldV3Enabled = true}) and B.enabled({WorldV3Enabled = true, BiomeRotationEnabled = true}), "flag needs World V3")
assert(not B.enabled(nil), "nil config")
local keys = {"sun", "horizon", "skyTop", "ambient", "fog", "tint"}
for _, id in B.Order do
    local L = B.Looks[id]
    assert(L, id .. " look")
    for _, k in keys do
        local c = L[k]
        assert(type(c) == "table" and #c == 3, id .. "." .. k)
        for _, v in c do assert(v >= 0 and v <= 255, id .. "." .. k .. " range") end
    end
    assert(L.fogStart >= 25 and L.fogEnd > L.fogStart + 100, id .. ": the near 25 studs stay clear and the fog has depth")
    assert(math.abs(L.sat) <= .2 and math.abs(L.contrast) <= .2 and L.bloom >= 0 and L.bloom <= .5, id .. " grade range")
    assert(B.Names[id] and B.StormFor[id] and B.Featured[id], id .. " name, storm, featured")
    assert(WeatherLooks.Looks[B.StormFor[id]], id .. ": storm '" .. B.StormFor[id] .. "' is a real weather look")
    local T = B.Terrain[id]
    if id ~= "meadow" then
        assert(T, id .. " terrain")
        for _, m in Toon.materials() do
            local c = T[m]
            assert(c, id .. " terrain " .. m)
            for _, v in c do assert(v >= 0 and v <= 245, id .. " terrain " .. m .. " is inside the soft-colour rule") end
        end
    end
end
-- phases over two full loops, at 0.25 s steps around every change
local len, n = B.Seconds, #B.Order
local seen = {}
local t0 = 1700000000 - (1700000000 % len) -- a change
for cycle = 0, 2 * n - 1 do
    local c = t0 + cycle * len
    local s = B.state(c + 1)
    seen[s.id] = true
    assert(s.changeAt == c + len and math.abs(s.left - (len - 1)) < 1e-6, "changeAt")
    assert(s.phase == "storm" and s.arriving == s.id, "the storm runs just after a change, bringing the new biome")
    assert(B.state(c + B.StormHalf + 1).phase == "calm", "calm after the storm")
    local w = B.state(c + len - B.StormHalf - 5)
    assert(w.phase == "warning" and w.arriving == w.next, "warning before the storm, naming the next biome")
    local st = B.state(c + len - 2)
    assert(st.phase == "storm" and B.storm(c + len - 2) == B.StormFor[st.next], "the storm before a change already brings the next biome")
    assert(B.storm(c + 100) == nil, "no storm in the calm")
    assert(B.state(c + len).id == s.next, "the loop advances")
    -- continuity of the look across the change
    local prev = B.look(c - .02)
    for k = 0, 40 do
        local tt = c - .01 + k * .0005
        local l = B.look(tt)
        for _, key in {"fog", "ambient", "sun"} do
            for i = 1, 3 do assert(math.abs(l[key][i] - prev[key][i]) < 2, "look jumps at the change (" .. key .. ")") end
        end
        prev = l
    end
    local f, to, mix = B.mix(c + 200)
    assert(f == to and mix == 1, "far from a change the look is one biome")
    local a = B.terrainColor("Grass", {110, 227, 66}, c - .001)
    local b = B.terrainColor("Grass", {110, 227, 66}, c + .001)
    for i = 1, 3 do assert(math.abs(a[i] - b[i]) < 1, "terrain colour jumps at the change") end
end
for _, id in B.Order do assert(seen[id], "every biome comes round: " .. id) end
-- meadow keeps the painter's own colours
local m = B.terrainColor("Grass", {1, 2, 3}, t0 + 200)
assert(B.state(t0 + 200).id ~= "meadow" or (m[1] == 1 and m[2] == 2 and m[3] == 3), "meadow = base colours")
-- banner words
local dur = function(s) return math.ceil(s / 60) .. " min" end
local line, timer = B.bannerWords(t0 + 100, dur)
local s = B.state(t0 + 100)
assert(line == B.Names[s.id] .. "!" and timer == B.Names[s.next] .. " in 7 min", "banner: " .. line .. " / " .. timer)
local l2 = B.bannerWords(t0 + 2, dur)
assert(l2 == "Storm!", "storm banner")
-- the Studio-only test offset
assert(B.clock(100, 50, true) == 150 and B.clock(100, 50, false) == 100 and B.clock(100, "x", true) == 100, "test offset only in Studio")
-- junk time
for _, junk in {0/0, math.huge, -math.huge} do local js = B.state(junk) assert(js.id and js.next, "junk time") end
print("biome rotation ok")
'''


def run(runner):
    script = ('local WeatherLooks = ' + wrapped('src/shared/WeatherLooks.luau') + '\n'
              + 'local Toon = ' + wrapped('src/shared/WorldToon.luau') + '\n'
              + 'local Biome = ' + wrapped('src/shared/BiomeRotation.luau') + '\n' + BODY)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'biome.luau'
        path.write_text(script, encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
    if out.returncode or 'biome rotation ok' not in out.stdout:
        return ['Luau: ' + (out.stdout + out.stderr).strip()[-1500:]]
    return []


def static_checks():
    errors = []
    config, profiles = read('src/shared/Config.luau'), read('tools/release_profiles.py')
    if len(re.findall(r'^    BiomeRotationEnabled = false,$', config, re.M)) != 1:
        errors.append('Config.BiomeRotationEnabled must ship false exactly once')
    for needle in ('_flag_off("BiomeRotationEnabled",', 'Rule("BiomeRotationEnabled", "set", True,', '("BiomeRotationEnabled", "BD-1314'):
        if needle not in profiles:
            errors.append('release_profiles.py is missing ' + needle)
    if 'require(script.Parent.BiomeService).start()' not in read('src/server/Bootstrap.server.luau'):
        errors.append('Bootstrap does not start BiomeService')
    service = read('src/server/BiomeService.luau')
    if 'if not Biome.enabled(Config) then return end' not in service:
        errors.append('BiomeService must return at once while the flag is off')
    for attr in ('CurrentBiome', 'NextBiome', 'BiomeChangeAt', 'BiomePhase'):
        if '"%s"' % attr not in service:
            errors.append('BiomeService does not publish ' + attr)
    wv = read('src/client/WeatherVisuals.client.luau')
    for needle in ('local biomeOn=Biome.enabled(', 'if biomeOn then Biome.storm(', 'local C=biomeClear or CLEAR', 'if not biomeStorm then showTitle(', 'Biome.clock(workspace:GetServerTimeNow(),workspace:GetAttribute("BiomeTestOffset"),RunService:IsStudio())'):
        if needle not in wv:
            errors.append('WeatherVisuals is missing ' + needle)
    hud = read('src/client/PhoneHud.client.luau')
    if 'if biomeOn and (id == "clear" or id == "") then line, timer = Biome.bannerWords(Biome.clock(' not in hud:
        errors.append('PhoneHud does not gate the biome banner on the flag')
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    errors = static_checks() + run(args.runner)
    for e in errors:
        print('FAIL:', e)
    if errors:
        sys.exit(1)
    print('Biome rotation checks passed: 5 biomes x 8 min, warning / storm / calm phases, smooth look and terrain blends, soft colours, real storm looks, flag wiring')


if __name__ == '__main__':
    main()
