#!/usr/bin/env python3
"""BD-1049: dump today's food positions (x, z, kind) without Roblox Studio.

src/server/FoodService.luau places food with Roblox's seeded Random and raycasts against the voxel terrain. Neither can run
outside Roblox, so this tool re-creates the same placement logic offline with the REAL pure modules (Config, IslandLayout) and
the pinned Luau runner (docs/160):

  * 20 x 20 sectors over Config.ArenaHalfWidth - 8, one jittered cluster centre per sector (20 tries, valid ground only),
    Config.FoodClusterItems foods per cluster inside Config.FoodClusterRadius, clamped to the sector (1 stud margin);
  * kind roll berry 70 / fruit 20 / egg 7 / amber 3; the fixed starter patch (same literal numbers as FoodService, including its
    old `sx == 7` quirk); the safe-spawn disc, marsh pools and slope >= 0.62 rejection (the terrain raycast is replaced by the
    same authored heightfield, which is what FoodService itself falls back to);
  * the random stream is consumed in the same ORDER as FoodService (centre tries, then per item: kind roll, relocate tries).

HOW CLOSE IT IS (say this out loud when you quote the numbers):
  * the dice differ: Roblox's Random cannot run here, so a small xorshift generator is used. The exact coordinates therefore
    differ from the game's, but the SHAPE (sector grid, cluster size, kind mix, rejection rules) is the same, so clump and
    empty-zone statistics are the same kind of number. That is why the tool can write several seeds (--seeds N): if the
    statistics agree across seeds, they do not depend on the dice.
  * not modelled: rejection near rock and trunk edges (1.25 studs, a few percent of tries), and the voxel terrain slope
    (Terrain is 4-stud voxels; the formula slope is slightly smoother). Respawns move a food inside its own cluster only.

Usage:
  python tools/dump_food_layout.py --runner C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe [--seeds 8] [--out build/food_layout]
Writes <out>_<seed>.json ({"seed":..,"arena":..,"points":[[x,z,kind],..],"mask":{..}}) and <out>_<seed>.csv for each seed (seed = Config.FoodSeed + i).
build/ is not committed.
"""
from pathlib import Path
import argparse
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local Config = (function()
@CONFIG@
end)()
local Layout = (function()
@LAYOUT@
end)()

-- xorshift32 (the game's Roblox Random cannot run here); seeded through a few warm-up draws
local function newRng(seed: number)
    local s = (seed * 2654435761 + 12345) % 4294967296
    if s == 0 then s = 88172645 end
    local function step(): number
        s = bit32.bxor(s, bit32.lshift(s, 13))
        s = bit32.bxor(s, bit32.rshift(s, 17))
        s = bit32.bxor(s, bit32.lshift(s, 5))
        return s
    end
    for _ = 1, 12 do step() end
    return {
        number = function(lo: number?, hi: number?): number
            local u = step() / 4294967296
            if lo then return lo + u * ((hi :: number) - lo) end
            return u
        end,
        integer = function(lo: number, hi: number): number
            return lo + math.floor(step() / 4294967296 * (hi - lo + 1))
        end,
    }
end

local KINDS = {"berry", "fruit", "egg", "amber"}

@GROUND@

local function layout(seed: number)
    local random = newRng(seed)
    local points = {}
    local extent = Config.ArenaHalfWidth - 8
    local sectorWidth = 2 * extent / Config.FoodSectorCount
    for sx = 0, Config.FoodSectorCount - 1 do
        for sz = 0, Config.FoodSectorCount - 1 do
            local minX, minZ = -extent + sx * sectorWidth, -extent + sz * sectorWidth
            local cx, cz = minX + sectorWidth / 2, minZ + sectorWidth / 2
            for _ = 1, 20 do
                local px = random.number(minX + 3, minX + sectorWidth - 3)
                local pz = random.number(minZ + 3, minZ + sectorWidth - 3)
                if groundAt(px, pz) then cx, cz = px, pz break end
            end
            local half = Config.FoodSectorCount // 2
            local starter = (sx == half - 1 or sx == half) and sz == half
            if starter then cx, cz = (if sx == 7 then -15 else 15), 24 end
            for item = 1, Config.FoodClusterItems do
                local roll, kind = random.integer(1, 100), 1
                if roll > 97 then kind = 4 elseif roll > 90 then kind = 3 elseif roll > 70 then kind = 2 end
                if starter then kind = if item % 3 == 0 then 2 else 1 end
                for _ = 1, 24 do
                    local angle = random.number(0, 2 * math.pi)
                    local radius = math.sqrt(random.number()) * Config.FoodClusterRadius
                    local x = math.clamp(cx + math.cos(angle) * radius, minX + 1, minX + sectorWidth - 1)
                    local z = math.clamp(cz + math.sin(angle) * radius, minZ + 1, minZ + sectorWidth - 1)
                    if groundAt(x, z) then
                        points[#points + 1] = {x, z, KINDS[kind], starter}
                        break
                    end
                end
            end
        end
    end
    return points
end

print("A\t" .. tostring(Config.ArenaHalfWidth) .. "\t" .. tostring(Config.FoodSeed))
-- walkable mask: groundAt at the centre of every 4-stud cell of the arena (the same rule the foods obey), one row of 0/1 per z
local MASK_CELL = 4
local maskCells = math.floor(2 * Config.ArenaHalfWidth / MASK_CELL)
for iz = 0, maskCells - 1 do
    local row = table.create(maskCells)
    for ix = 0, maskCells - 1 do
        row[ix + 1] = if groundAt(-Config.ArenaHalfWidth + (ix + 0.5) * MASK_CELL, -Config.ArenaHalfWidth + (iz + 0.5) * MASK_CELL) then "1" else "0"
    end
    print("M\t" .. table.concat(row))
end
for i = 0, @SEEDS@ - 1 do
    local seed = Config.FoodSeed + i
    for _, p in layout(seed) do
        print(string.format("P\t%d\t%.3f\t%.3f\t%s\t%d", seed, p[1], p[2], p[3], if p[4] then 1 else 0))
    end
end
print("OK")
'''


# The ground rule of FoodService.groundAt (safe-spawn disc, pools, slope) as Luau text; BD-1047's generator reads the same rule (ground_model).
GROUND_LUAU = '''local function groundAt(x: number, z: number): boolean
    if math.sqrt(x * x + (z - 30) ^ 2) < 11 then return false end
    if Layout.inPool(x, z, 1.5) then return false end
    local gx = (Layout.height(x + 2, z) - Layout.height(x - 2, z)) / 4
    local gz = (Layout.height(x, z + 2) - Layout.height(x, z - 2)) / 4
    return 1 / math.sqrt(1 + gx * gx + gz * gz) >= 0.62
end
'''

GROUND_BODY = r'''
local Config = (function()
@CONFIG@
end)()
local Layout = (function()
@LAYOUT@
end)()
@GROUND@
print("A\t" .. tostring(Config.ArenaHalfWidth) .. "\t" .. tostring(Config.FoodSeed))
local CELL = @CELL@
local HCELL = @HCELL@
local cells = math.floor(2 * Config.ArenaHalfWidth / CELL)
for iz = 0, cells - 1 do
    local row = table.create(cells)
    for ix = 0, cells - 1 do
        row[ix + 1] = if groundAt(-Config.ArenaHalfWidth + (ix + 0.5) * CELL, -Config.ArenaHalfWidth + (iz + 0.5) * CELL) then "1" else "0"
    end
    print("M\t" .. table.concat(row))
end
local hcells = math.floor(2 * Config.ArenaHalfWidth / HCELL)
for iz = 0, hcells - 1 do
    local row = table.create(hcells)
    for ix = 0, hcells - 1 do
        row[ix + 1] = string.format("%.2f", Layout.height(-Config.ArenaHalfWidth + (ix + 0.5) * HCELL, -Config.ArenaHalfWidth + (iz + 0.5) * HCELL))
    end
    print("H\t" .. table.concat(row, ","))
end
print("OK")
'''


# BD-1208 (docs/241 W8): the same ground rule on the redesigned round island. The offline runner has no `script`, so IslandLayout / BiomeMap stay on the old
# island here; this body reads WorldV3 directly (height, inPool, path) and runs BiomePlacement.useV3 for the keep-out discs and landmark sites.
GROUND_BODY_V3 = r'''
local Config = (function()
@CONFIG@
end)()
local V3 = (function()
@WORLDV3@
end)()
local BP = (function()
@BIOMEPLACEMENT@
end)()
local Layout = V3
@GROUND@
BP.useV3(V3)
print("A	" .. tostring(Config.ArenaHalfWidth) .. "	" .. tostring(Config.FoodSeed))
print(string.format("V3	%g	%g	%g	%g	%g", V3.CenterX, V3.CenterZ, V3.PlazaRadius, V3.RingRadius, V3.PathHalfWidth))
for _, s in V3.Spokes do print(string.format("SP	%g	%g", s.angle, s.to)) end
for _, k in BP.KeepOuts do print(string.format("KO	%.3f	%.3f	%.3f	%s", k.x, k.z, k.radius, tostring(k.all))) end
for _, s in V3.Landmarks do local x, z = V3.polar(s.angle, s.r) print(string.format("LM	%s	%.3f	%.3f", s.id, x, z)) end
for _, g in V3.Groves do local x, z = V3.polar(g[1], g[2]) print(string.format("GR	%.3f	%.3f", x, z)) end
for _, p in V3.Pools do print(string.format("PO	%.3f	%.3f	%.3f	%.3f", p.x, p.z, p.rx, p.rz)) end
local CELL = @CELL@
local HCELL = @HCELL@
local cells = math.floor(2 * Config.ArenaHalfWidth / CELL)
for iz = 0, cells - 1 do
    local row, prow = table.create(cells), table.create(cells)
    for ix = 0, cells - 1 do
        local x, z = -Config.ArenaHalfWidth + (ix + 0.5) * CELL, -Config.ArenaHalfWidth + (iz + 0.5) * CELL
        row[ix + 1] = if groundAt(x, z) then "1" else "0"
        prow[ix + 1] = if V3.path(x, z) > 0.02 then "1" else "0"
    end
    print("M	" .. table.concat(row))
    print("Q	" .. table.concat(prow))
end
local hcells = math.floor(2 * Config.ArenaHalfWidth / HCELL)
for iz = 0, hcells - 1 do
    local row = table.create(hcells)
    for ix = 0, hcells - 1 do
        row[ix + 1] = string.format("%.2f", Layout.height(-Config.ArenaHalfWidth + (ix + 0.5) * HCELL, -Config.ArenaHalfWidth + (iz + 0.5) * HCELL))
    end
    print("H	" .. table.concat(row, ","))
end
print("OK")
'''


def build(seeds):
    src = BODY.replace('@GROUND@', GROUND_LUAU)
    for token, path in (('@CONFIG@', 'src/shared/Config.luau'), ('@LAYOUT@', 'src/shared/IslandLayout.luau')):
        src = src.replace(token, (ROOT / path).read_text(encoding='utf-8'))
    return src.replace('@SEEDS@', str(seeds))


def ground_model(runner, cell=1.0, height_cell=8.0, world=None):
    """BD-1047: FoodService's ground rule evaluated on a fine lattice, from the real Config and IslandLayout.
    Returns {"arena": half width, "cell": studs, "mask": [row strings of 0/1, rows[iz][ix], x = -arena + (ix + 0.5) cell],
    "hcell": studs, "height": rows[iz][ix] of the island height in studs, same x/z rule}.
    world='v3' (BD-1208): the redesigned island instead (src/shared/WorldV3.luau read directly); the model also holds "path" (rows of 0/1:
    WorldV3.path above 0.02) and "v3": {"centre", "plaza", "ring", "half_width", "spokes", "keepouts", "landmarks", "groves", "pools"}."""
    if world == 'v3':
        src = GROUND_BODY_V3.replace('@GROUND@', GROUND_LUAU)
        for token, path in (('@CONFIG@', 'src/shared/Config.luau'), ('@WORLDV3@', 'src/shared/WorldV3.luau'), ('@BIOMEPLACEMENT@', 'src/shared/BiomePlacement.luau')):
            src = src.replace(token, (ROOT / path).read_text(encoding='utf-8'))
    else:
        src = GROUND_BODY.replace('@GROUND@', GROUND_LUAU)
        for token, path in (('@CONFIG@', 'src/shared/Config.luau'), ('@LAYOUT@', 'src/shared/IslandLayout.luau')):
            src = src.replace(token, (ROOT / path).read_text(encoding='utf-8'))
    src = src.replace('@CELL@', repr(float(cell))).replace('@HCELL@', repr(float(height_cell)))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'ground_model.luau'
        path.write_text(src, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if result.returncode or 'OK' not in result.stdout:
        print(result.stdout[-2000:], result.stderr[-2000:])
        raise SystemExit(result.returncode or 1)
    arena, mask, heights, paths = 416.0, [], [], []
    info = {'spokes': [], 'keepouts': [], 'landmarks': [], 'groves': [], 'pools': []}
    for line in result.stdout.splitlines():
        p = line.split('	')
        if p[0] == 'A':
            arena = float(p[1])
        elif p[0] == 'M':
            mask.append(p[1])
        elif p[0] == 'Q':
            paths.append(p[1])
        elif p[0] == 'H':
            heights.append([float(v) for v in p[1].split(',')])
        elif p[0] == 'V3':
            info.update(centre=(float(p[1]), float(p[2])), plaza=float(p[3]), ring=float(p[4]), half_width=float(p[5]))
        elif p[0] == 'SP':
            info['spokes'].append((float(p[1]), float(p[2])))
        elif p[0] == 'KO':
            info['keepouts'].append((float(p[1]), float(p[2]), float(p[3]), p[4] == 'true'))
        elif p[0] == 'LM':
            info['landmarks'].append((p[1], float(p[2]), float(p[3])))
        elif p[0] == 'GR':
            info['groves'].append((float(p[1]), float(p[2])))
        elif p[0] == 'PO':
            info['pools'].append((float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    model = {'arena': arena, 'cell': 2 * arena / len(mask), 'mask': mask, 'hcell': 2 * arena / len(heights), 'height': heights}
    if world == 'v3':
        model['path'] = paths
        model['v3'] = info
    return model


def dump(runner, seeds):
    """Returns {seed: {"arena": half width, "points": [[x, z, kind], ...]}} (starter foods included)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'food_layout.luau'
        path.write_text(build(seeds), encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if result.returncode or 'OK' not in result.stdout:
        print(result.stdout[-2000:], result.stderr[-2000:])
        raise SystemExit(result.returncode or 1)
    arena, out, mask = 416.0, {}, []
    for line in result.stdout.splitlines():
        p = line.split('\t')
        if p[0] == 'A':
            arena = float(p[1])
        elif p[0] == 'M':
            mask.append(p[1])
        elif p[0] == 'P':
            out.setdefault(int(p[1]), {'arena': arena, 'points': []})['points'].append([float(p[2]), float(p[3]), p[4]])
    for item in out.values():
        item['arena'] = arena
        item['mask'] = {'cell': 2 * arena / len(mask), 'rows': mask}  # rows[iz][ix] == '1' where food may be placed (x = -arena + (ix + 0.5) cell)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    parser.add_argument('--seeds', type=int, default=1, help='how many layouts (Config.FoodSeed, +1, +2, ...)')
    parser.add_argument('--out', default=str(ROOT / 'build' / 'food_layout'), help='path prefix, <prefix>_<seed>.json/.csv')
    args = parser.parse_args()
    layouts = dump(args.runner, args.seeds)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    for seed, item in sorted(layouts.items()):
        Path(f'{args.out}_{seed}.json').write_text(json.dumps({'seed': seed, **item}), encoding='utf-8')
        rows = ['x,z,kind'] + [f'{x:.3f},{z:.3f},{kind}' for x, z, kind in item['points']]
        Path(f'{args.out}_{seed}.csv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
        kinds = {}
        for _, _, kind in item['points']:
            kinds[kind] = kinds.get(kind, 0) + 1
        print(f'seed {seed}: {len(item["points"])} foods {kinds} -> {args.out}_{seed}.json')


if __name__ == '__main__':
    main()
