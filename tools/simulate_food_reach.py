"""BD-521 (docs/115 MR4): offline food-per-minute and eggs-per-run simulator for the pickup reach rule.

It runs the REAL pure modules in Luau (Config, ScaleLadder, MouthReach, IslandLayout, HubScaleRules, CombatConfig) and re-creates
src/server/FoodService.luau offline: 20 x 20 sectors over Config.ArenaHalfWidth - 8, one jittered cluster centre per sector, 9 foods per
cluster inside radius 7 (berry 70 / fruit 20 / egg 7 / amber 3 percent, 1 / 4 / 15 / 50 points), the starter cluster, the safe-spawn disc, pool and
slope rejection from IslandLayout, 8 s respawn into a fresh spot of the same cluster, the 0.08 s pickup tick, an 8 stud grid like BD-361.
One player walks 300 s from the spawn. Policy "greedy": always walk straight at the nearest available food (measured from the body) and eat
everything inside the reach zone every tick. Growth is the real curve: food x GrowthPerFood -> HubScaleRules.growthScale -> scale -> reach.
NOT modelled (they hit every species alike): line of sight, the trees and rocks the real placement rejects, jumping, turning, other players.

Reach rules compared per species:
  old     = the root rule of Build 020, radius min(5, 2.25 + 0.75 x (scale - 1)) around the root;
  new     = the BD-515 mouth rule without a cap (head point, radius follows the head);
  <k>     = the BD-521 cap: front edge and radius <= k x the Compy's at the same scale (MouthReach.zone(species, scale, k)); the plain "capped" column
            is MouthReach.zone with the cap in Config.FoodReachCapCompy, i.e. what the game runs now.
Two speed regimes: "flat" (every species walks Config.WalkSpeed, isolates the reach rule) and "class" (x CombatConfig speedX, what the
friends-playtest profile does with ClassMovementEnabled). Three paces: "full" (walk speed x1), "half" and "quarter" (x0.5, x0.25: the walk is
less efficient, as a real player's is; the greedy full pace makes about 1,100 food/min, far above the docs/119 estimate of 130, so only RATIOS
between rules and species are meaningful, not the absolute food/min).
Eggs per run = food x Config.FoodCatchRate (not floored, so the means are smooth); "eggs15" re-bases every number so that the OLD Compy makes 15.

Usage: python tools/simulate_food_reach.py --runner luau.exe [--seeds 8] [--caps 1.25,1.15] [--markdown out.md] [--json out.json] [--check]
--check fails when the capped rule (Config.FoodReachCapCompy) leaves the parity band (10%) against the Compy at the same pace, speed regime and
layouts, or makes the spread between species wider than the old rule's.
"""
from pathlib import Path
import argparse
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BAND = 0.10

BODY = r'''
local Config = (function()
@CONFIG@
end)()
local ScaleLadder = (function()
@LADDER@
end)()
local MouthReach = (function()
local script = {Parent = {Config = "Config", ScaleLadder = "ScaleLadder"}}
local require = function(id) if id == "ScaleLadder" then return ScaleLadder end return Config end
@MODULE@
end)()
local Layout = (function()
@LAYOUT@
end)()
local Hub = (function()
@HUB@
end)()
local Combat = (function()
@COMBAT@
end)()

local SEEDS = @SEEDS@
local RUN_SECONDS = 300
local TICK = Config.FoodTickSeconds
local RESPAWN = Config.FoodRespawnSeconds
local CELL = 8

-- ---------------------------------------------------------------- tiny deterministic RNG (Park-Miller, exact in doubles)
local function unit(s: number): (number, number)
    s = (s * 48271) % 2147483647
    return (s - 1) / 2147483646, s
end

-- ---------------------------------------------------------------- layout (FoodService.start)
local function groundAt(x: number, z: number): boolean
    if math.sqrt(x * x + (z - Layout.SpawnZ) ^ 2) < 11 then return false end
    if Layout.inPool(x, z, 1.5) then return false end
    local gx = (Layout.height(x + 2, z) - Layout.height(x - 2, z)) / 4
    local gz = (Layout.height(x, z + 2) - Layout.height(x, z - 2)) / 4
    return 1 / math.sqrt(1 + gx * gx + gz * gz) >= 0.62
end

local function relocate(food, state: number): (boolean, number)
    for _ = 1, 24 do
        local a, r
        a, state = unit(state)
        r, state = unit(state)
        local angle = a * 2 * math.pi
        local radius = math.sqrt(r) * Config.FoodClusterRadius
        local x = math.clamp(food.cx + math.cos(angle) * radius, food.minX + 1, food.maxX - 1)
        local z = math.clamp(food.cz + math.sin(angle) * radius, food.minZ + 1, food.maxZ - 1)
        if groundAt(x, z) then food.x, food.z = x, z return true, state end
    end
    return false, state
end

local function buildLayout(seed: number)
    local state = (seed * 7919 + 17) % 2147483647
    local foods = {}
    local extent = Config.ArenaHalfWidth - 8
    local width = 2 * extent / Config.FoodSectorCount
    local half = Config.FoodSectorCount // 2
    for sx = 0, Config.FoodSectorCount - 1 do
        for sz = 0, Config.FoodSectorCount - 1 do
            local minX, minZ = -extent + sx * width, -extent + sz * width
            local cx, cz = minX + width / 2, minZ + width / 2
            for _ = 1, 20 do
                local a, b
                a, state = unit(state)
                b, state = unit(state)
                local px, pz = minX + 3 + a * (width - 6), minZ + 3 + b * (width - 6)
                if groundAt(px, pz) then cx, cz = px, pz break end
            end
            local starter = (sx == half - 1 or sx == half) and sz == half
            if starter then cx, cz = (if sx == 7 then -15 else 15), 24 end
            for item = 1, Config.FoodClusterItems do
                local roll
                roll, state = unit(state)
                roll = math.floor(roll * 100) + 1
                local points = 1
                if roll > 97 then points = 50 elseif roll > 90 then points = 15 elseif roll > 70 then points = 4 end
                if starter then points = if item % 3 == 0 then 4 else 1 end
                local food = {points = points, cx = cx, cz = cz, minX = minX, maxX = minX + width, minZ = minZ, maxZ = minZ + width, x = 0, z = 0,
                    rng = (seed * 104729 + #foods * 7919 + 11) % 2147483647}
                local ok
                ok, state = relocate(food, state)
                if ok then foods[#foods + 1] = food end
            end
        end
    end
    return foods
end

-- ---------------------------------------------------------------- grid of the available foods
local function key(cx: number, cz: number): number return (cx + 1000) * 4096 + (cz + 1000) end
local function cellOf(v: number): number return math.floor(v / CELL) end

local function gridInsert(grid, food)
    local k = key(cellOf(food.x), cellOf(food.z))
    local bucket = grid[k]
    if not bucket then bucket = {} grid[k] = bucket end
    bucket[food] = true
end

local function nearest(grid, px: number, pz: number, dmin: number)
    local ccx, ccz = cellOf(px), cellOf(pz)
    local best, bestD2 = nil, math.huge
    for ring = 0, 120 do
        if best and (ring - 1) * CELL > math.sqrt(bestD2) then break end
        for dx = -ring, ring do
            for dz = -ring, ring do
                if math.max(math.abs(dx), math.abs(dz)) == ring then
                    local bucket = grid[key(ccx + dx, ccz + dz)]
                    if bucket then
                        for food in bucket do
                            local ddx, ddz = food.x - px, food.z - pz
                            local d2 = ddx * ddx + ddz * ddz
                            if d2 < bestD2 and d2 >= dmin * dmin then best, bestD2 = food, d2 end
                        end
                    end
                end
            end
        end
    end
    return best
end

-- ---------------------------------------------------------------- reach rules: (offset of the pickup point ahead of the root, radius)
local function reach(variant: any, species: string, scale: number): (number, number)
    if variant == "old" then return 0, MouthReach.legacyRadius(scale) end
    if variant == "new" then return MouthReach.uncappedHeadOffset(species, scale), MouthReach.uncappedRadius(species, scale) end
    if variant == "capped" then return MouthReach.zone(species, scale) end
    return MouthReach.zone(species, scale, variant :: number)
end

-- ---------------------------------------------------------------- one run
local layouts = {}
local function run(species: string, variant: any, speed: number, layoutSeed: number)
    local foods = layouts[layoutSeed]
    if not foods then foods = buildLayout(layoutSeed) layouts[layoutSeed] = foods end
    local grid, queue, qHead = {}, {}, 1
    for _, f in foods do
        local c = {points = f.points, cx = f.cx, cz = f.cz, minX = f.minX, maxX = f.maxX, minZ = f.minZ, maxZ = f.maxZ, x = f.x, z = f.z, rng = f.rng}
        gridInsert(grid, c)
    end
    local px, pz = 0, Layout.SpawnZ
    local face = -math.pi / 2 -- facing -Z
    local food, scale, eaten = 0, 1, 0
    local target = nil
    local now = 0
    local offset, radius = reach(variant, species, scale)
    local limit = Config.ArenaHalfWidth - 8
    for _ = 1, math.floor(RUN_SECONDS / TICK + 0.5) do
        now += TICK
        while qHead <= #queue and queue[qHead].readyAt <= now do
            local f = queue[qHead]
            qHead += 1
            local _, s = relocate(f, f.rng)
            f.rng = s
            f.hidden = false
            gridInsert(grid, f)
        end
        -- The player walks straight at the nearest food that the head can reach by walking at it (a food closer than offset - radius is under the
        -- body: ignored, the head sweeps it later). The facing is the walking direction, the head point leads the root by `offset` along it.
        if target == nil or target.hidden then target = nearest(grid, px, pz, math.max(0, offset - radius)) end
        if target then
            local dx, dz = target.x - px, target.z - pz
            local d = math.sqrt(dx * dx + dz * dz)
            if d > 1e-6 then
                face = math.atan2(dz, dx)
                local step = math.min(d, speed * TICK)
                px = math.clamp(px + dx / d * step, -limit, limit)
                pz = math.clamp(pz + dz / d * step, -limit, limit)
            end
        end
        hx, hz = px + math.cos(face) * offset, pz + math.sin(face) * offset
        local gained, r2 = 0, radius * radius
        for cx = cellOf(hx - radius), cellOf(hx + radius) do
            for cz = cellOf(hz - radius), cellOf(hz + radius) do
                local bucket = grid[key(cx, cz)]
                if bucket then
                    for f in bucket do
                        local dx, dz = f.x - hx, f.z - hz
                        if dx * dx + dz * dz <= r2 then
                            bucket[f] = nil
                            f.hidden = true
                            f.readyAt = now + RESPAWN
                            queue[#queue + 1] = f
                            gained += f.points
                            eaten += 1
                        end
                    end
                end
            end
        end
        if gained > 0 then
            food += gained
            scale = Hub.growthScale(food * Config.GrowthPerFood)
            offset, radius = reach(variant, species, scale)
        end
    end
    return food, scale, eaten
end

-- ---------------------------------------------------------------- driver
local ids = {}
for id in ScaleLadder.Dino.species do ids[#ids + 1] = id end
table.sort(ids)
local function avg(species: string, variant: any, speed: number, seeds: number)
    local f, f2, s, e = 0, 0, 0, 0
    for seed = 1, seeds do
        local a, b, c = run(species, variant, speed, seed)
        f += a f2 += a * a s += b e += c
    end
    local mean = f / seeds
    local sd = math.sqrt(math.max(0, f2 / seeds - mean * mean))
    return mean, s / seeds, e / seeds, sd / math.sqrt(seeds)
end

print("RATE	" .. string.format("%.6f", Config.FoodCatchRate))
print("CAP	" .. tostring(MouthReach.capFactor()))

local variants = {"old", "new", "capped"@CAPS@}
local classes = Combat.SpeciesClasses
for _, pace in {{"full", 1}, {"half", 0.5}, {"quarter", 0.25}} do
    for _, regime in {"flat", "class"} do
        for _, id in ids do
            local classX = if regime == "class" then Combat.Classes[classes[id] or Combat.DefaultClass].speedX else 1
            local speed = Config.WalkSpeed * classX * pace[2]
            for _, v in variants do
                local food, scale, eaten, se = avg(id, v, speed, SEEDS)
                print(string.format("S\t%s\t%s\t%s\t%s\t%.2f\t%.1f\t%.3f\t%.1f\t%.1f", pace[1], regime, id, tostring(v), speed, food, scale, eaten, se))
            end
        end
    end
end
print("OK")
'''


def build(caps, seeds):
    src = BODY
    for token, path in (('@CONFIG@', 'src/shared/Config.luau'), ('@LADDER@', 'src/shared/ScaleLadder.luau'), ('@MODULE@', 'src/shared/MouthReach.luau'),
                        ('@LAYOUT@', 'src/shared/IslandLayout.luau'), ('@HUB@', 'src/shared/HubScaleRules.luau'), ('@COMBAT@', 'src/shared/CombatConfig.luau')):
        src = src.replace(token, (ROOT / path).read_text(encoding='utf-8'))
    return src.replace('@SEEDS@', str(seeds)).replace('@CAPS@', ''.join(', %s' % c for c in caps))


def simulate(runner, caps, seeds):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'food_reach.luau'
        path.write_text(build(caps, seeds), encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if result.returncode or 'OK' not in result.stdout:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode or 1)
    meta, rows = {}, {}
    for line in result.stdout.splitlines():
        p = line.split('\t')
        if p[0] == 'S':
            rows[(p[1], p[2], p[3], p[4])] = {'speed': float(p[5]), 'food': float(p[6]), 'scale': float(p[7]), 'pickups': float(p[8]), 'se': float(p[9])}
        elif p[0] == 'RATE':
            meta[p[0]] = float(p[1])
        elif p[0] == 'CAP':
            meta['CAP'] = None if p[1] == 'nil' else float(p[1])
    return meta, rows


def per_min(rows, pace, regime, species, variant):
    return rows[(pace, regime, species, variant)]['food'] / 5.0


def spread(rows, pace, regime, species_list, variant):
    values = [per_min(rows, pace, regime, s, variant) for s in species_list]
    return max(values) / max(min(values), 1e-9)


def table(rows, meta, pace, regime, variants, species_list):
    base = rows[(pace, regime, 'compy', 'old')]['food']
    head = ['species', 'speed', 'scale at end'] + ['food/min %s' % v for v in variants] + ['eggs15 %s' % v for v in variants] + ['vs Compy %s' % v for v in variants]
    lines = ['| ' + ' | '.join(head) + ' |', '| --- | ' + ' | '.join('---:' for _ in head[1:]) + ' |']
    for sp in species_list:
        cells = ['%.0f' % per_min(rows, pace, regime, sp, v) for v in variants]
        cells += ['%.1f' % (15.0 * rows[(pace, regime, sp, v)]['food'] / base) for v in variants]
        cells += ['%+.0f%%' % ((per_min(rows, pace, regime, sp, v) / per_min(rows, pace, regime, 'compy', v) - 1) * 100) for v in variants]
        r = rows[(pace, regime, sp, 'old')]
        lines.append('| %s | %.1f | %.2f | %s |' % (sp, r['speed'], rows[(pace, regime, sp, 'capped')]['scale'], ' | '.join(cells)))
    srow = ['**max / min**', '', ''] + ['%.2f' % spread(rows, pace, regime, species_list, v) for v in variants] + [''] * (2 * len(variants))
    lines.append('| ' + ' | '.join(srow) + ' |')
    return '\n'.join(lines)


PACES = ('full', 'half', 'quarter')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--seeds', type=int, default=8)
    parser.add_argument('--caps', default='')
    parser.add_argument('--markdown')
    parser.add_argument('--json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    caps = [c for c in args.caps.split(',') if c]
    meta, rows = simulate(args.runner, caps, args.seeds)
    species_list = sorted({k[2] for k in rows})
    variants = ['old', 'new', 'capped'] + caps
    out = ['# BD-521 food per minute by species (%d layouts, 300 s, greedy walk)' % args.seeds, '',
           'FoodCatchRate = %.4f egg per food. Cap in Config.FoodReachCapCompy: %s. eggs15 = eggs per run re-based so that the OLD Compy makes 15.' % (meta['RATE'], meta['CAP']), '']
    for pace in PACES:
        for regime in ('flat', 'class'):
            out += ['## pace %s, speed %s' % (pace, regime), '', table(rows, meta, pace, regime, variants, species_list), '']
    text = '\n'.join(out)
    print(text)
    if args.markdown:
        Path(args.markdown).write_text(text, encoding='utf-8')
    if args.json:
        Path(args.json).write_text(json.dumps({'meta': meta, 'rows': {'|'.join(k): v for k, v in rows.items()}}, indent=1), encoding='utf-8')
    if args.check:
        problems = []
        for pace in PACES:
            regime = 'flat'
            for sp in species_list:
                d = per_min(rows, pace, regime, sp, 'capped') / per_min(rows, pace, regime, 'compy', 'capped') - 1
                if d > BAND:
                    problems.append('%s %s %s: capped food/min is %+.1f%% against the Compy (band +%.0f%%)' % (pace, regime, sp, d * 100, BAND * 100))
            if spread(rows, pace, regime, species_list, 'capped') > spread(rows, pace, regime, species_list, 'new') + 1e-9:
                problems.append('%s %s: the capped spread is wider than the uncapped one' % (pace, regime))
        if problems:
            print('\n'.join(problems))
            raise SystemExit(1)
        print('Food reach parity passed')


if __name__ == '__main__':
    main()
