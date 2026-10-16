"""BD-460 (docs/138): offline checks for the island environment polish pass, with the pinned Luau runtime.
Covers: the contact-shadow rules (soft, capped, cheap on phones), the softer clear-daylight grade and light, the warm terrain greens,
the per-asset foliage tone ranges, the built-in grass decision (BeDino_Meadow unbound), and the owner's no-haze rule (docs/114 s6).
Instances are not executed here; the Studio look is checked by the lead (kanban BD-460).
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
-- ---- contact shadow rules
assert(#R.Layers == 3, "three stacked soft discs")
local lastSize = 2
for i, l in R.Layers do
    assert(l.size < lastSize and l.size > .3, "discs shrink outer to inner") lastSize = l.size
    assert(l.alpha > 0 and l.alpha <= .32, "each disc is translucent, the stack is what darkens")
    assert(R.transparency(i, 1) == 1 - l.alpha and R.transparency(i, 0) == 1, "opacity 0 hides, 1 is the disc alpha")
end
local dark = R.centreDarkness()
assert(dark >= .45 and dark <= .65, "clearly visible but soft contact shadow (round 1 at .33 was invisible in Studio): " .. dark)
assert(R.Thickness <= .1 and R.Lift >= .03 and R.Lift <= .15 and R.LayerStep > 0 and R.LayerStep < R.Lift, "flat, just above the ground, no z-fighting")
assert(R.Color[1] > 0 or R.Color[2] > 0 or R.Color[3] > 0, "never pure black")
local w1, l1 = R.footprint(1) local w4, l4 = R.footprint(4) local wn = R.footprint(0 / 0)
assert(w1 >= 5 and w4 > w1 and l4 > l1 and l1 > w1 and w4 <= 18 and wn == w1, "footprint is wider than the 3.5-stud starting body, grows with the dino, is bounded, NaN safe")
-- phone budget: <= 2 others, tablet <= 4, desktop <= 6; Lite halves, Off keeps only the local dino
assert(R.maxOthers("Phone", "full") == 2 and R.maxOthers("Tablet", "full") == 4 and R.maxOthers("Desktop", "full") == 6)
assert(R.maxOthers("Phone", "lite") == 1 and R.maxOthers("Desktop", "lite") == 3 and R.maxOthers("Phone", "off") == 0 and R.maxOthers("Desktop", "off") == 0)
assert(R.MaxOthers.Phone <= R.MaxOthers.Tablet and R.MaxOthers.Tablet <= R.MaxOthers.Desktop and R.Range.Phone <= R.Range.Desktop)
assert(#R.Layers * (1 + R.MaxOthers.Phone) <= 9, "phone: at most 9 shadow parts in the scene")
local cands = {}
for i = 1, 20 do table.insert(cands, {id = i, distance = 100 - i * 4}) end -- ids 1..20, distances 96 .. 20
local pick = R.pick(cands, "Desktop", "full")
assert(#pick == 6 and pick[1] == 20 and pick[6] == 15, "desktop: six nearest")
local far = R.pick(cands, "Phone", "full") assert(#far == 2 and far[1] == 20 and far[2] == 19, "phone: two nearest inside 40 studs")
assert(#R.pick({{id = 1, distance = 500}}, "Desktop", "full") == 0 and #R.pick({{id = 1, distance = 0 / 0}}, "Desktop", "full") == 0 and #R.pick({}, "Phone", "full") == 0, "range and NaN")
assert(#R.pick(cands, "Desktop", "off") == 0, "Effects Off drops the others")
local o0, s0 = R.airborne(0) local o5, s5 = R.airborne(4.5) local o9, s9 = R.airborne(40) local on = R.airborne(0 / 0)
assert(o0 == 1 and s0 == 1 and o5 > 0 and o5 < 1 and s5 < 1 and o9 == 0 and s9 >= .6 and on == 1, "a jump fades and shrinks the shadow")

-- ---- softer clear daylight (no haze, less saturation, no extra contrast)
local C = W.Looks.clear
assert(C.sat >= .02 and C.sat <= .06, "clear grade saturation slightly positive (was +.08, +.02 made the built-in grass pale, BD-460): " .. C.sat)
assert(C.contrast == 0, "clear grade adds no contrast (was +.04): " .. C.contrast)
assert(C.bloom == 0 and C.dof == 0 and C.rays == 0 and C.glare == 0, "no bloom, depth of field, sun rays or glare in clear daylight")
assert(C.density == 0 and C.haze == 0, "the clear look itself adds no atmosphere (owner 2026-10-16: no haze)")
assert(C.fogStart >= 150 and C.vis >= 900, "fog distances stay far (PR #302)")
assert(W.ClearFog.Desktop.fogStart >= 400 and W.ClearFog.Desktop.fogEnd >= 1400 and W.ClearFog.Tablet.fogStart >= 250, "far clear fog distances stay (PR #302)")
local L = Cfg.IslandLight
assert(L.Brightness >= 1.6 and L.Brightness < 2, "sun brightness a little below the old 2: " .. L.Brightness)
for _, key in {"Ambient", "OutdoorAmbient"} do
    local a = L[key] for i = 1, 3 do assert(a[i] >= 120 and a[i] <= 180, key .. " stays a daylight fill") end
    assert(a[1] >= 130 and a[2] >= 143 and a[3] >= 140, key .. " is not below the old ambient floor")
end
assert(L.Ambient[3] - L.Ambient[1] <= 20, "neutral-ish fill, no strong blue cast")

-- ---- terrain greens (built-in Grass is pale and grey-green: the colour multiplier must be rich and warm; old Grass 132,170,84, LeafyGrass 62,124,78)
local function sat(c) local hi, lo = math.max(c[1], c[2], c[3]), math.min(c[1], c[2], c[3]) return (hi - lo) / hi end
local function val(c) return math.max(c[1], c[2], c[3]) / 255 end
local grass, leafy = B.Colors.Grass, B.Colors.LeafyGrass
assert(sat(grass) >= .5 and sat(grass) <= .65 and val(grass) >= .58 and val(grass) <= .72, "meadow grass rich, not grey (BD-460)")
assert(grass[3] <= grass[1] * .65 and grass[2] > grass[1], "meadow grass is warm: low blue, green leads")
assert(sat(leafy) >= .45 and val(leafy) >= .45 and leafy[3] < leafy[1] and leafy[2] > leafy[1], "leafy grass warm green, no dark teal patches")

-- ---- per-asset foliage tone
local seenTone = 0
for key, t in G.Tone do
    assert(G.Assets[key], "tone for an unknown generated mesh " .. key)
    for i = 1, 3 do assert(t[i] >= .75 and t[i] <= 1, key .. " tone channel in [.75, 1]") end
    assert(t[3] < t[1] and t[2] <= t[1] + 1e-9, key .. " tone takes the blue (mint) out first")
    assert(key:sub(1, 5) == "tree_" or key == "bush", key .. " only foliage is toned")
    assert(key ~= "tree_burnt", "the burnt tree keeps its art colours")
    seenTone += 1
end
assert(seenTone >= 5, "all green foliage keys are toned")
for _, key in {"tree_broadleaf", "tree_birch", "tree_jungle_giant", "bush", "tree_pine", "tree_palm"} do assert(G.Tone[key], key .. " must be toned") end
for _, rock in {"rock_mossy_boulder", "rock_pillar", "rock_sand_cliff", "rock_crystal", "rock_lava", "rock_pebbles", "landmark_dino_statue"} do assert(G.Tone[rock] == nil, rock .. " keeps its art colours") end
print("environment polish passed")
'''


def script():
    cfg = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    m = re.search(r'IslandLight = \{(.*?)\},\n', cfg, re.S)
    assert m, 'Config.IslandLight not found'
    light = 'local Cfg={IslandLight={' + m.group(1) + '}}\n'
    return (light + 'local R=' + module('src/shared/ContactShadowRules.luau') + '\nlocal W=' + module('src/shared/WeatherLooks.luau')
            + '\nlocal B=' + module('src/shared/BiomeMap.luau') + '\nlocal G=' + module('src/shared/WorldGeneratedMeshes.luau') + '\n' + BODY)


def scan():
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    # No-haze rule (owner 2026-10-16, PR #302): the base atmosphere stays at density .1 / haze .3 / glare 0.
    assert 'atmosphere.Density, atmosphere.Offset, atmosphere.Glare, atmosphere.Haze = .1, .1, 0, .3' in boot, 'base atmosphere must stay .1/.1/0/.3 (no haze)'
    assert 'Config.IslandLight' in boot and 'OutdoorAmbient' in boot, 'Bootstrap applies Config.IslandLight'
    prog = (ROOT / 'src/server/ProgressionService.luau').read_text(encoding='utf-8')
    assert 'GameConfig.IslandLight.Brightness' in prog, 'clear weather restores the island base brightness'
    shadow = (ROOT / 'src/client/ContactShadow.client.luau').read_text(encoding='utf-8')
    for needle in ('CanCollide, part.CanQuery, part.CanTouch, part.CastShadow', 'Parent = camera', 'Rules.pick(', 'Settings.effects()', 'Rules.airborne('):
        assert needle in shadow, 'ContactShadow.client.luau lacks ' + needle
    assert shadow.count('Instance.new') == 2, 'only the folder and the pooled disc parts are created, never per frame'
    assert 'Instance.new("Part")' in shadow and shadow.index('local function newShadow') < shadow.index('Instance.new("Part")') < shadow.index('local function hide'), 'discs are built only in newShadow'
    # Grass: owner decision 2026-10-16 = Roblox's built-in Grass. BeDino_Meadow stays in MaterialService with all its IDs but is NOT bound.
    root = ET.fromstring((ROOT / 'resources/world-materials.rbxmx').read_text(encoding='utf-8'))
    assert root.find("Item/Properties/string[@name='GrassName']") is None, 'MaterialService.GrassName must stay unset (built-in Grass, BD-460)'
    meadow = next(v for v in root.iter('Item') if v.attrib.get('referent') == 'BeDino_Meadow')
    names = {c.attrib['name'] for c in meadow.findall('Properties/Content')}
    assert names == {'ColorMap', 'NormalMap', 'RoughnessMap', 'MetalnessMap'}, 'the unbound variant keeps all four map IDs: ' + str(names)
    assert 'rbxassetid://94202355146046' in (ROOT / 'resources/world-materials.rbxmx').read_text(encoding='utf-8')
    assert root.find("Item/Properties/string[@name='RockName']") is not None and root.find("Item/Properties/string[@name='WoodName']") is not None, 'rock and wood overrides unchanged'
    reg = (ROOT / 'docs/77-asset-registry.md').read_text(encoding='utf-8')
    assert 'BD-460' in reg, 'docs/77 records the grass art task (BD-460)'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'env_polish.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
