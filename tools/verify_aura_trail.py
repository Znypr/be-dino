"""Mythic Glow v2 aura/trail plan checks (src/shared/AuraTrailStyle.luau, docs/81) in pinned Luau.

Runs the pure plan for every catalog aura x trail x quality and checks the per-player effect budget,
class/tier mapping, LOD rules, the asset-ready gate (empty or malformed IDs keep v1), and that every
EffectAssets key has a committed texture. Instance building and looks are Studio-only.
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
-- Catalog coverage: every trail has a class, classes 1..6 all used, auras map to tiers 1..3.
local used = {}
for _, trail in Config.Trails do
 local c = Style.trailClass(trail) assert(Style.TrailClass[trail.id] and c >= 1 and c <= 6, trail.id) used[c] = true
end
for c = 1, 6 do assert(used[c], "class " .. c .. " used") end
assert(Style.trailClass(nil) == 0 and Style.auraTier(nil) == 0 and Style.trailClass({id = "new"}) == 1)
assert(Style.auraTier({growth = 1.15}) == 1 and Style.auraTier({growth = 1.35}) == 2 and Style.auraTier({growth = 1.7}) == 3 and Style.auraTier({}) == 1)
for _, aura in Config.Auras do assert(Style.auraTier(aura) >= 1) end

-- Budget for every combination (including none) at every quality.
local auras, trails = {false}, {false}
for _, a in Config.Auras do table.insert(auras, a) end
for _, t in Config.Trails do table.insert(trails, t) end
local combos, maxFull = 0, {emitters = 0, beams = 0, trails = 0, discs = 0, billboards = 0}
for _, a in auras do for _, t in trails do
 local aura, trail = if a then a else nil, if t then t else nil
 for _, q in {"full", "lite", "off"} do
  local layers = Style.plan(aura, trail, q)
  assert(Style.withinBudget(layers, q), "budget " .. q)
  for _, layer in layers do assert(layer.texture == nil or table.find(Style.TextureKeys, layer.texture), "known texture") end
  if q == "off" then assert(#layers == 0) end
  if q == "full" then for k, v in Style.cost(layers) do maxFull[k] = math.max(maxFull[k], v) end end
  combos += 1
 end
end end
-- Top combo shows every layer type; lite keeps exactly the sigil and one trail.
local royal, astra = nil, nil
for _, a in Config.Auras do if a.id == "royal" then royal = a end end
for _, t in Config.Trails do if t.id == "astra" then astra = t end end
local kinds = {} for _, l in Style.plan(royal, astra, "full") do kinds[l.kind] = (kinds[l.kind] or 0) + 1 end
assert(kinds.disc == 2 and kinds.comets == 1 and kinds.pillar == 1 and kinds.halo == 1 and kinds.trail == 4 and kinds.emitter == 3)
local lite = Style.plan(royal, astra, "lite")
assert(#lite == 2 and lite[1].kind == "disc" and lite[2].kind == "trail" and lite[2].rainbow == true)
local electric = nil for _, t in Config.Trails do if t.id == "electric" then electric = t end end
local strand = nil for _, l in Style.plan(nil, electric, "full") do if l.role == "strand" then strand = l.texture end end
assert(strand == "ribbon-lightning", "Electric Arc uses the lightning strand")
local white = nil for _, t in Config.Trails do if t.id == "white" then white = t end end
local w = Style.cost(Style.plan(nil, white, "full")) assert(w.trails == 2 and w.emitters == 0, "Common trail stays simple")

-- LOD rules.
assert(Style.quality(true, 500, 0, true) == "full", "own dino always full")
assert(Style.quality(false, 20, 1, true) == "full" and Style.quality(false, 20, 3, true) == "lite")
assert(Style.quality(false, 60, 1, true) == "lite" and Style.quality(false, 81, 1, true) == "off")
assert(Style.quality(true, 0, 0, false) == "lite", "motion off caps at lite")

-- Asset gate: empty, partial or malformed IDs keep v1.
assert(not Style.ready(Assets), "no IDs bound yet: v1 stays")
assert(not Style.ready(nil) and not Style.ready({}))
local fake = {} for _, k in Style.TextureKeys do fake[k] = "rbxassetid://123" end
assert(Style.ready(fake))
fake.runes = "rbxassetid://abc" assert(not Style.ready(fake))
fake.runes = "" assert(not Style.ready(fake))
local keyCount = 0 for k in Assets do keyCount += 1 assert(table.find(Style.TextureKeys, k), "asset key " .. k) end
assert(keyCount == #Style.TextureKeys)
print(string.format("Aura/trail v2 plan checks passed: %d combos, full max %d emitters / %d beams / %d trails / %d discs / %d halo, LOD and asset gate",
 combos, maxFull.emitters, maxFull.beams, maxFull.trails, maxFull.discs, maxFull.billboards))
'''


def script():
    return ('local Config=' + module('src/shared/ProgressionConfig.luau') + '\n'
            + 'local Style=' + module('src/shared/AuraTrailStyle.luau') + '\n'
            + 'local Assets=' + module('src/shared/EffectAssets.luau') + '\n' + BODY)


def check_files():
    keys = re.findall(r'"([a-z-]+)"', re.search(r'TextureKeys = \{(.*?)\}', (ROOT / 'src/shared/AuraTrailStyle.luau').read_text(), re.S).group(1))
    missing = [k for k in keys if not (ROOT / 'resources/effects/mythic-glow' / (k + '.png')).exists()]
    if missing:
        print('missing textures:', missing)
        return False
    registry = (ROOT / 'docs/77-asset-registry.md').read_text(encoding='utf-8')
    unregistered = [k for k in keys if f'mythic-glow/{k}.png' not in registry]
    if unregistered:
        print('textures missing from docs/77-asset-registry.md:', unregistered)
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    if not check_files():
        sys.exit(1)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'aura_trail.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
