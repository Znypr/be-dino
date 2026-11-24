#!/usr/bin/env python3
"""BD-1320 ground patches (src/shared/GroundPatches.luau, docs/251 s5), owner 2026-11-24 "Yes, start BD-1320".

Runs the REAL GroundPatches and WorldV3 in the pinned Luau runtime over the island on the 4-stud terrain grid and checks:
  * only grass picks change (Grass, LeafyGrass); every other pick stays;
  * never on the plaza, a path (path > .5), in the sea, soil never above 30 studs (rock may run up the hill) or in the beach and volcano zones;
  * the outputs are the island's own materials (Ground, Rock, LeafyGrass), each with its mask name;
  * coverage per zone stays natural: patches (worn, floor, shade, rock) cover 3-30 % of the grass of each grass zone, slope rock at most
    15 % of any zone (the pine hill is steep; its flanks may show rock), and every mask shows up somewhere;
  * no confetti: at least 60 % of the connected patches of each mask are bigger than 2 cells (the lead review of #623 rejected one-voxel
    brown spots as hard hexagons);
  * deterministic (two runs give the same counts).
Source guards: IslandTerrain calls GroundPatches only inside the GroundDetailEnabled branch, the toon greens stay soft and distinct.
Usage: python tools/verify_ground_patches.py --runner luau.exe"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local failed = {}
local function check(ok, what) if not ok and not failed[what] then failed[what] = true table.insert(fails, what) end end
local R, E = 4, 412
local MATERIAL = {worn = "Ground", floor = "Ground", shade = "LeafyGrass", rock = "Rock"}
local function run()
  local grid, total, by, rockBy, kinds = {}, {}, {}, {}, {}
  for i = -E // R, E // R do for j = -E // R, E // R do
    local x, z = i * R, j * R
    local h = V3.height(x, z)
    local gx = (V3.height(x + 3, z) - V3.height(x - 3, z)) / 6
    local gz = (V3.height(x, z + 3) - V3.height(x, z - 3)) / 6
    local slope = math.sqrt(gx * gx + gz * gz)
    for _, pick in {"Mud", "Sandstone", "Slate"} do
      check(GP.surface(V3, x, z, h, slope, pick) == nil, "non-grass pick " .. pick .. " kept")
    end
    local m, kind = GP.surface(V3, x, z, h, slope, "Grass")
    local zone = V3.zoneAt(x, z).id
    if kind then
      check(MATERIAL[kind] == m, "material of " .. tostring(kind))
      check(not V3.inPlaza(x, z) and V3.path(x, z) <= .5 and (h <= 30 or kind == "rock") and V3.inland(x, z) > 0, "patch off plaza, path, sea; soil below 30 studs")
      check(zone ~= "beach" and zone ~= "volcano", "patch only in grass zones")
      grid[i * 1000 + j] = kind
      kinds[kind] = true
    end
    if V3.inland(x, z) > 0 and not V3.surface(x, z, h) and GP.Zones[zone] then
      total[zone] = (total[zone] or 0) + 1
      if kind then by[zone] = (by[zone] or 0) + 1 end
      if kind == "rock" then rockBy[zone] = (rockBy[zone] or 0) + 1 end
    end
  end end
  return grid, total, by, rockBy, kinds
end
local grid, total, by, rockBy, kinds = run()
for zone, n in total do
  local share = (by[zone] or 0) / n
  check(share >= .03 and share <= .30, string.format("%s patch share %.3f in 3-30 %%", zone, share))
  check((rockBy[zone] or 0) / n <= .15, zone .. " slope rock at most 15 %")
  print(string.format("%s grass cells %d, patches %.1f %%, rock %.1f %%", zone, n, 100 * share, 100 * (rockBy[zone] or 0) / n))
end
for _, k in {"worn", "floor", "shade", "rock"} do check(kinds[k], "mask " .. k .. " appears") end
local seen, big, all = {}, {}, {}
for k, kind in grid do if not seen[k] then
  local stack, n = {k}, 0 seen[k] = true
  while #stack > 0 do
    local c = table.remove(stack) n += 1
    local i, j = c // 1000, c % 1000
    if j > 500 then j -= 1000 i += 1 end
    for _, d in {{1, 0}, {-1, 0}, {0, 1}, {0, -1}} do
      local nk = (i + d[1]) * 1000 + (j + d[2])
      if grid[nk] == kind and not seen[nk] then seen[nk] = true table.insert(stack, nk) end
    end
  end
  all[kind] = (all[kind] or 0) + 1
  if n > 2 then big[kind] = (big[kind] or 0) + 1 end
end end
for kind, n in all do
  print(string.format("%s: %d patches, %d bigger than 2 cells", kind, n, big[kind] or 0))
  check((big[kind] or 0) / n >= .6, kind .. " patches mostly bigger than 2 cells")
end
local _, _, by2 = run()
for zone, n in by do check(by2[zone] == n, "deterministic " .. zone) end
if #fails > 0 then print("FAIL") for _, f in fails do print(" - " .. f) end else print("PASS") end
'''


def source_checks():
    errors = []
    terrain = read('src/server/IslandTerrain.luau')
    if 'if not fixed and fillGround then fixed = Patches.surface(' not in terrain:
        errors.append('IslandTerrain must call GroundPatches only inside the GroundDetailEnabled branch')
    toon = read('src/shared/WorldToon.luau')
    greens = {k: tuple(int(v) for v in m) for k, *m in re.findall(r'\n    (Grass|LeafyGrass) = \{(\d+), (\d+), (\d+)\}', toon)}
    if set(greens) != {'Grass', 'LeafyGrass'}:
        errors.append('toon greens not found')
    else:
        if any(c < 40 or c > 245 for g in greens.values() for c in g):
            errors.append('toon greens must stay soft (40-245)')
        if sum(abs(a - b) for a, b in zip(greens['Grass'], greens['LeafyGrass'])) < 30:
            errors.append('Grass and LeafyGrass must differ enough to read (BD-1320)')
    if 'GroundPatches' in read('src/client/Bootstrap.client.luau'):
        errors.append('Bootstrap.client must not use GroundPatches')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    errors = source_checks()
    source = ('local V3=' + module(read('src/shared/WorldV3.luau')) + '\nlocal GP=' + module(read('src/shared/GroundPatches.luau')) + '\n' + LUAU)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'ground_patches.luau'
        path.write_text(source, encoding='utf-8')
        out = subprocess.run([args.runner, str(path)], capture_output=True, text=True, timeout=600)
    print(out.stdout.strip())
    if out.returncode != 0 or 'PASS' not in out.stdout.splitlines():
        errors.append('Luau checks failed' + (': ' + out.stderr.strip()[-800:] if out.stderr.strip() else ''))
    for e in errors:
        print('ERROR', e)
    print('verify_ground_patches: ' + ('FAIL' if errors else 'OK'))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
