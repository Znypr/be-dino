"""BD-407 (docs/114 section 8.1): offline verifier for the numeric scale ladder src/shared/ScaleLadder.luau.

It runs the REAL source modules in Luau (LowPolyDinoAssets, HubScaleRules, Config, WorldKitData, BiomePlacement, WorldGeneratedMeshes,
CaveHubLayout, ScaleLadder) and fails when:
  1. DRIFT: a size in the code no longer equals the ladder (species model scale, hub scale, growth stages, BIG multiplier, torso
     collider, kit tree/rock/landmark/ground-cover heights, Small band, colossal band, ancient mesh heights, ground rocks, gate mouth,
     tunnels, station pads, hub props and signs), or a WIRED place (FoodService, SpecialFoods, Arena legacy hub) hardcodes a size again;
  2. ORDER: the ladder order breaks (food taller than the smallest dino, a colossal tree not clearly above a normal tree or the tallest
     maxed dino, a normal-run dino taller than the biggest normal tree, the dino door lower than the largest hub dino, ...);
  3. DOC: the table in docs/114 section 8.1.1 differs from the one generated from the Lua table (rewrite it with --write-doc).
Not Studio evidence: heights of unmeasured species are ESTIMATES until BD-471 measures them (see Dino.species[..].measured).
Usage: python tools/verify_scale_ladder.py --runner luau.exe [--write-doc] [--print]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/114-handbook.md'
BEGIN, END = '<!-- scale-ladder:begin -->', '<!-- scale-ladder:end -->'
# Studio bounding boxes (docs/07-kanban.md BD-329/BD-337, docs/108): the only species heights that are measured, not estimated.
MEASURED = {'compy': 6.6, 'gallimimus': 4.9, 'tyrannosaurus': 10.3}
STAGE_COLUMNS = ('run', 'mid', 'long', 'max', 'bigMax')


def wrapped(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


LUAU = r'''
local function r1(x) return math.floor(x * 10 + 0.5) / 10 end
local function r2(x) return math.floor(x * 100 + 0.5) / 100 end
local function flat(prefix, v)
    if type(v) == "table" then
        for k, x in v do flat(prefix .. "." .. tostring(k), x) end
    elseif type(v) ~= "function" then
        print("L\t" .. prefix .. "\t" .. tostring(v))
    end
end
local function out(k, v) print("C\t" .. k .. "\t" .. tostring(v)) end
flat("", Ladder)
local ids = {}
for id in LowPoly do ids[#ids + 1] = id end
table.sort(ids)
out("lowpoly.ids", table.concat(ids, ","))
out("order", table.concat(Config.SpeciesOrder, ","))
for id, row in LowPoly do out("species." .. id .. ".scale", row.scale) end
out("Dino.hubScale", Hub.HubScale)
out("Dino.maxScale", Hub.MaxGrowthScale)
out("Dino.bigMultiplier", Config.BigScaleMultiplier)
out("Dino.collider.width", Config.DinoColliderWidth)
out("Dino.collider.length", Config.DinoColliderLength)
out("Dino.collider.topPerScale", Config.DinoColliderTopPerScale)
for i, st in Ladder.Dino.stages do out("Dino.stages." .. i .. ".scale", r2(Hub.growthScale(st.growth) * (if st.big then Config.BigScaleMultiplier else 1))) end
out("Food.pickupRadius", Config.FoodPickupRadius)
-- kit heights
local tmin, tmax, gmin, gmax, rmin, bmax, fmax, lmin, lmax = math.huge, 0, math.huge, 0, math.huge, 0, 0, math.huge, 0
for _, d in Kit do
    local y = d.extent[2]
    if d.kind == "tree" then tmin, tmax = math.min(tmin, y), math.max(tmax, y)
    elseif d.kind == "groundcover" then gmin, gmax = math.min(gmin, y), math.max(gmax, y)
    elseif d.kind == "rock" then
        rmin = math.min(rmin, y)
        if d.family:sub(1, 7) == "boulder" then bmax = math.max(bmax, y) else fmax = math.max(fmax, y) end
    elseif d.kind == "landmark" then lmin, lmax = math.min(lmin, y), math.max(lmax, y) end
end
local S = Biome.Scales
out("Trees.normal.scale.1", S.tree[1]) out("Trees.normal.scale.2", S.tree[2])
out("Trees.normal.kitHeight.1", tmin) out("Trees.normal.kitHeight.2", tmax)
out("Trees.normal.minHeight", r1(tmin * S.tree[1])) out("Trees.normal.maxHeight", r1(tmax * S.tree[2]))
out("Trees.v3.minHeight", r1(tmin * S.tree[1])) out("Trees.v3.maxHeight", r1(tmax * S.tree[2]))
out("Plants.groundcover.minHeight", r1(gmin * S.groundcover[1])) out("Plants.groundcover.maxHeight", r1(gmax * S.groundcover[2]))
out("Plants.small.minHeight", Biome.SmallBand.minHeight) out("Plants.small.maxHeight", Biome.SmallBand.maxHeight)
out("Trees.colossal.minHeight", Biome.Colossal.minHeight) out("Trees.colossal.maxHeight", Biome.Colossal.maxHeight)
out("Trees.colossal.maxCrown", Biome.Colossal.maxCrown)
out("Trees.colossal.ancientMesh.broadleaf", Gen.Colossal.tree_colossal_broadleaf_v3.size[3])
out("Trees.colossal.ancientMesh.pine", Gen.Colossal.tree_colossal_pine_v3.size[3])
out("Trees.colossal.ancientMesh.palm", Gen.Colossal.tree_colossal_palm_v3.size[3])
out("Rocks.island.scale.1", S.rock[1]) out("Rocks.island.scale.2", S.rock[2])
out("Rocks.island.minHeight", r1(rmin * S.rock[1])) out("Rocks.island.boulderMaxHeight", r1(bmax * S.rock[2])) out("Rocks.island.maxHeight", r1(math.max(bmax, fmax) * S.rock[2]))
out("Rocks.groundV3.small", Gen.Props.ground_rock_small_v3.size[2])
out("Rocks.groundV3.medium", Gen.Props.ground_rock_medium_v3.size[2])
out("Rocks.groundV3.mossy", Gen.Props.ground_rock_mossy_v3.size[2])
out("Landmarks.scale", Biome.LandmarkScale)
out("Landmarks.minHeight", r1(lmin * Biome.LandmarkScale)) out("Landmarks.maxHeight", r1(lmax * Biome.LandmarkScale))
-- cave hub
local L = Cave.get()
out("Hub.gate.mouthWidth", L.gate.mouthWidth)
for i = 1, 3 do out("Hub.gate.frame." .. i, Cave.Kinds.cave_gate_frame[i]) end
out("Hub.tunnel.width", Cave.TunnelRadius * 2)
out("Hub.tunnel.ceiling", L.tunnels[1].h)
out("Hub.tunnel.pathWidth", Cave.PathHalf * 2)
for id, st in L.byId do out("Hub.stationPadRadius." .. id, st.r) end
local KIND = {["Nest.pad"] = "nest", ["Nest.ledge"] = "hub_nest_ledge", ["Hub.sign.stone"] = "hub_sign_stone", ["Hub.sign.arrow"] = "hub_sign_arrow",
    ["Hub.station.stallPotion"] = "hub_stall_potion", ["Hub.station.forgeAltar"] = "hub_forge_altar", ["Hub.station.counterStone"] = "hub_counter_stone",
    ["Hub.station.lecternBook"] = "hub_lectern_book", ["Hub.station.wallFrame"] = "hub_wall_frame"}
for key, kind in KIND do for i = 1, 3 do out(key .. "." .. i, Cave.Kinds[kind][i]) end end
'''


def script():
    return (
        'local Ladder=' + wrapped('src/shared/ScaleLadder.luau') + '\n'
        + 'local LowPoly=' + wrapped('src/shared/LowPolyDinoAssets.luau') + '\n'
        + 'local Hub=' + wrapped('src/shared/HubScaleRules.luau') + '\n'
        + 'local Config=' + wrapped('src/shared/Config.luau') + '\n'
        + 'local Kit=' + wrapped('src/shared/WorldKitData.luau') + '\n'
        + 'local Biome=' + wrapped('src/shared/BiomePlacement.luau') + '\n'
        + 'local Gen=' + wrapped('src/shared/WorldGeneratedMeshes.luau') + '\n'
        + 'local Cave=' + wrapped('src/shared/CaveHubLayout.luau') + '\n'
        + LUAU)


def run_luau(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_scale_ladder.luau'
        path.write_text(script(), encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(out.stdout[-2500:] + out.stderr[-2500:])
    ladder, code = {}, {}
    for line in out.stdout.splitlines():
        f = line.split('\t')
        if len(f) == 3 and f[0] == 'L':
            ladder[f[1].lstrip('.')] = f[2]
        elif len(f) == 3 and f[0] == 'C':
            code[f[1]] = f[2]
    return ladder, code


def num(d, k):
    return float(d[k])


def close(a, b, tol):
    return abs(a - b) <= tol


def check_drift(ladder, code, errors):
    def same(path, key=None, tol=1e-9):
        key = key or path
        if path not in ladder:
            errors.append(f'ladder has no value {path}')
        elif key not in code:
            errors.append(f'code value {key} was not read')
        elif not close(num(ladder, path), num(code, key), tol):
            errors.append(f'DRIFT {path}: ladder {ladder[path]} but the code says {code[key]}')
    # species: same set, same order, same model scale
    ladder_order = ladder['Dino.order.1'] and [ladder[f'Dino.order.{i}'] for i in range(1, 23)]
    if ','.join(ladder_order) != code['order']:
        errors.append('DRIFT Dino.order: ladder species order differs from Config.SpeciesOrder')
    if code['lowpoly.ids'] != ','.join(sorted(ladder_order)):
        errors.append('DRIFT species: LowPolyDinoAssets lists different species than the ladder')
    for sid in ladder_order:
        same(f'Dino.species.{sid}.scale', f'species.{sid}.scale')
    for key in ('Dino.hubScale', 'Dino.maxScale', 'Dino.bigMultiplier', 'Dino.collider.width', 'Dino.collider.length',
                'Dino.collider.topPerScale', 'Food.pickupRadius'):
        same(key)
    for i in range(1, 7):
        same(f'Dino.stages.{i}.scale', tol=0.005)
    for key in ('Trees.normal.scale.1', 'Trees.normal.scale.2', 'Trees.normal.kitHeight.1', 'Trees.normal.kitHeight.2',
                'Rocks.island.scale.1', 'Rocks.island.scale.2', 'Landmarks.scale', 'Plants.small.minHeight', 'Plants.small.maxHeight',
                'Trees.colossal.minHeight', 'Trees.colossal.maxHeight', 'Trees.colossal.maxCrown'):
        same(key, tol=0.0006)
    for key in ('Trees.normal.minHeight', 'Trees.normal.maxHeight', 'Trees.v3.minHeight', 'Trees.v3.maxHeight',
                'Plants.groundcover.minHeight', 'Plants.groundcover.maxHeight', 'Rocks.island.minHeight', 'Rocks.island.boulderMaxHeight',
                'Rocks.island.maxHeight', 'Landmarks.minHeight', 'Landmarks.maxHeight'):
        same(key, tol=1e-6)
    for key in ('broadleaf', 'pine', 'palm'):
        same(f'Trees.colossal.ancientMesh.{key}', tol=0.006)
    for key in ('small', 'medium', 'mossy'):
        same(f'Rocks.groundV3.{key}', tol=0.006)
    for key in ('Hub.gate.mouthWidth', 'Hub.tunnel.width', 'Hub.tunnel.ceiling', 'Hub.tunnel.pathWidth'):
        same(key)
    for i in (1, 2, 3):
        same(f'Hub.gate.frame.{i}', tol=0.006)
        for key in ('Nest.pad', 'Nest.ledge', 'Hub.sign.stone', 'Hub.sign.arrow', 'Hub.station.stallPotion', 'Hub.station.forgeAltar',
                    'Hub.station.counterStone', 'Hub.station.lecternBook', 'Hub.station.wallFrame'):
            same(f'{key}.{i}', tol=0.006)
    for pad in [k for k in ladder if k.startswith('Hub.stationPadRadius.')]:
        same(pad)
    if sorted(k.rsplit('.', 1)[1] for k in ladder if k.startswith('Hub.stationPadRadius.')) != sorted(
            k.rsplit('.', 1)[1] for k in code if k.startswith('Hub.stationPadRadius.')):
        errors.append('DRIFT Hub.stationPadRadius: the ladder lists different stations than CaveHubLayout')
    # species heights: measured rows are the Studio numbers, the rest follow the documented estimate rule
    est = num(ladder, 'HeightPerScaleEstimate')
    for sid in ladder_order:
        row_h, row_s = num(ladder, f'Dino.species.{sid}.height'), num(ladder, f'Dino.species.{sid}.scale')
        measured = ladder[f'Dino.species.{sid}.measured'] == 'true'
        if measured != (sid in MEASURED):
            errors.append(f'{sid}: measured flag {measured} disagrees with the Studio-measured list {sorted(MEASURED)}')
        elif measured and not close(row_h, MEASURED[sid], 1e-9):
            errors.append(f'{sid}: measured height {row_h} differs from the Studio bounding box {MEASURED[sid]}')
        elif not measured and not close(row_h, row_s * est, 0.05 + 1e-9):
            errors.append(f'{sid}: estimated height {row_h} is not scale {row_s} x {est} (rounded to 0.1)')
    # Arena colossal and growth formula text checks for the parts that need a require chain
    terrain = (ROOT / 'src/shared/CaveTerrainRules.luau').read_text(encoding='utf-8')
    m = re.search(r'^Rules\.GateHeight = ([\d.]+)', terrain, re.M)
    if not m or not close(float(m.group(1)), num(ladder, 'Hub.gate.mouthHeight'), 1e-9):
        errors.append(f'DRIFT Hub.gate.mouthHeight: ladder {ladder["Hub.gate.mouthHeight"]} but CaveTerrainRules.GateHeight is {m.group(1) if m else "missing"}')


def check_wiring(errors):
    def src(p):
        return (ROOT / p).read_text(encoding='utf-8')
    ladder_src = src('src/shared/ScaleLadder.luau')
    for banned in ('Instance.new', 'game:GetService', 'Vector3', 'CFrame', 'workspace', 'require('):
        if banned in ladder_src:
            errors.append('ScaleLadder stays pure data: found ' + banned)
    food = src('src/server/FoodService.luau')
    if 'require(ReplicatedStorage.Shared.ScaleLadder)' not in food:
        errors.append('FoodService does not require ScaleLadder')
    for kind in ('berry', 'fruit', 'egg', 'amber'):
        if not re.search(r'\{id = "%s", weight = \d+, points = \d+, size = ScaleLadder\.Food\.%s\.size,' % (kind, kind), food):
            errors.append(f'FoodService food kind {kind} must read ScaleLadder.Food.{kind}.size (hardcoded size?)')
    if 'ScaleLadder.Food.drumstickScale' not in food or 'ScaleLadder.Food.variety[1]' not in food or 'ScaleLadder.Food.variety[2]' not in food:
        errors.append('FoodService drumstick scale / size variety must read ScaleLadder.Food')
    if re.search(r'\.45 else 1\)|NextNumber\(\.86', food):
        errors.append('FoodService hardcodes the drumstick scale or size variety again')
    sp = src('src/shared/SpecialFoods.luau')
    if 'size = ScaleLadder.Food.goldenDrumstick.size' not in sp or 'require(script.Parent.ScaleLadder)' not in sp:
        errors.append('SpecialFoods.GOLDEN_DRUMSTICK.size must read ScaleLadder.Food.goldenDrumstick.size')
    arena = src('src/server/Arena.luau')
    if 'require(ReplicatedStorage.Shared.ScaleLadder)' not in arena:
        errors.append('Arena does not require ScaleLadder')
    if 'ScaleLadder.Nest.pad[1]' not in arena or '"EggNest",Vector3.new(5,1,5)' in arena.replace(' ', ''):
        errors.append('Arena legacy-hub EggNest must read ScaleLadder.Nest.pad')
    if 'ScaleLadder.Hub.sign.legacyBoard[1]' not in arena or '"SanctuarySign",Vector3.new(30,7,1)' in arena.replace(' ', ''):
        errors.append('Arena legacy-hub SanctuarySign must read ScaleLadder.Hub.sign.legacyBoard')
    # V3 trees: the ladder says they share the normal range because Arena.generatedProp fits every tree inside the kit extent box
    if 'fit = math.min(extent[2] / size.Y, math.max(extent[1], extent[3]) * 1.15 / math.max(size.X, size.Z))' not in arena:
        errors.append('Arena.generatedProp no longer fits trees by kit extent height: Trees.v3 would not equal Trees.normal')


def check_order(ladder, errors):
    g = lambda k: num(ladder, k)
    order = [ladder[f'Dino.order.{i}'] for i in range(1, 23)]
    h1 = {sid: g(f'Dino.species.{sid}.height') for sid in order}
    scale = {st: g(f'Dino.stages.{i}.scale') for i, st in enumerate(('spawn', 'run', 'mid', 'long', 'max', 'bigMax'), 1)}
    stage_big = {ladder[f'Dino.stages.{i}.id']: ladder[f'Dino.stages.{i}.big'] == 'true' for i in range(1, 7)}
    tallest = max(h1.values())
    tallest_id = max(h1, key=h1.get)
    smallest = min(h1.values())
    hub = g('Dino.hubScale')
    ids = [ladder[f'Dino.stages.{i}.id'] for i in range(1, 7)]
    if ids != ['spawn', 'run', 'mid', 'long', 'max', 'bigMax']:
        errors.append(f'ORDER stage ids {ids}')
    if any(scale[a] > scale[b] for a, b in zip(ids, ids[1:])):
        errors.append('ORDER growth stage scales must not shrink')
    if not close(scale['bigMax'], g('Dino.maxScale') * g('Dino.bigMultiplier'), 0.005) or not stage_big['bigMax']:
        errors.append('ORDER bigMax must equal maxScale x bigMultiplier')
    if not close(scale['max'], g('Dino.maxScale'), 1e-9):
        errors.append('ORDER the max stage must be the growth cap')
    if hub != 1:
        errors.append('ORDER every dinosaur is exactly 1x in the cave hub (docs/115, BD-480)')
    # R1 food is smaller than every dino at spawn (an adult Compy included), also the biggest drawn drumstick mesh
    var_hi = g('Food.variety.2')
    food = {k: g(f'Food.{k}.size') for k in ('berry', 'fruit', 'egg', 'amber', 'goldenDrumstick')}
    drawn = {k: v * var_hi for k, v in food.items()}
    drawn['goldenDrumstick'] = food['goldenDrumstick'] * g('Food.drumstickScale') * var_hi
    for k, v in drawn.items():
        if v >= h1['compy']:
            errors.append(f'ORDER food {k} drawn {v:.2f} is not smaller than a spawn Compy ({h1["compy"]})')
        if v >= smallest:
            errors.append(f'ORDER food {k} drawn {v:.2f} is not smaller than the smallest species at spawn ({smallest})')
    if not (food['berry'] <= food['fruit'] <= food['egg'] <= food['amber'] <= food['goldenDrumstick']):
        errors.append('ORDER food sizes must grow berry <= fruit <= egg <= amber <= golden drumstick (value is read by size, docs/56)')
    # R2 egg pickup and nest
    if food['egg'] >= min(g('Nest.pad.1'), g('Nest.pad.3')):
        errors.append('ORDER the egg pickup must be smaller than the nest pad')
    if g('Nest.pad.2') >= g('Nest.ledge.2'):
        errors.append('ORDER the nest pad must be lower than the nest ledge')
    # R3 plants: a new dino stands in the Small band, ground cover is below it
    if not g('Plants.small.minHeight') < h1['compy'] < g('Plants.small.maxHeight'):
        errors.append('ORDER a spawn Compy must stand inside the Small band')
    if g('Plants.groundcover.maxHeight') >= h1['compy']:
        errors.append('ORDER ground cover must stay below a spawn Compy (it is texture, not jungle, docs/139 G0)')
    if g('Plants.small.maxHeight') >= g('Trees.normal.maxHeight'):
        errors.append('ORDER the Small band must be below the tallest normal tree')
    # R4 trees
    n_max, c_min, c_max = g('Trees.normal.maxHeight'), g('Trees.colossal.minHeight'), g('Trees.colossal.maxHeight')
    if not (g('Trees.normal.minHeight') < n_max < c_min < c_max):
        errors.append('ORDER trees must go normal min < normal max < colossal min < colossal max')
    if g('Trees.v3.maxHeight') > n_max + 1e-9 or g('Trees.v3.minHeight') < g('Trees.normal.minHeight') - 1e-9:
        errors.append('ORDER V3 trees must stay inside the normal tree range')
    big_max = tallest * scale['bigMax']
    if c_min < 1.5 * big_max - 1e-9:
        errors.append(f'ORDER a colossal tree ({c_min}) must be at least 1.5x the tallest BIG-max dino ({big_max:.1f}, {tallest_id}), docs/139 s5')
    for sid in order:
        if h1[sid] * scale['max'] >= c_min:
            errors.append(f'ORDER maxed {sid} ({h1[sid] * scale["max"]:.1f}) must stay below the colossal minimum ({c_min})')
        if h1[sid] * scale['run'] >= n_max:
            errors.append(f'ORDER a normal-run {sid} ({h1[sid] * scale["run"]:.1f}) must be shorter than the tallest normal tree ({n_max})')
    for k in ('broadleaf', 'pine', 'palm'):
        if not c_min <= g(f'Trees.colossal.ancientMesh.{k}') <= c_max:
            errors.append(f'ORDER the ancient {k} mesh height must lie inside the colossal band')
    # rocks and landmarks
    if not g('Rocks.island.minHeight') <= g('Rocks.island.boulderMaxHeight') <= g('Rocks.island.maxHeight') < c_min:
        errors.append('ORDER rocks must stay below the colossal band and boulders below formations')
    if g('Landmarks.maxHeight') >= c_min:
        errors.append('ORDER landmarks must stay below the colossal band')
    # R7 the dino door
    mouth_h, mouth_w = g('Hub.gate.mouthHeight'), g('Hub.gate.mouthWidth')
    hub_tallest = tallest * hub
    if mouth_h < 1.5 * hub_tallest - 1e-9:
        errors.append(f'ORDER the dino gate ({mouth_h} high) must clear 1.5x the tallest hub dino {tallest_id} ({hub_tallest:.1f})')
    if g('Dino.collider.topPerScale') * hub >= mouth_h:
        errors.append('ORDER the hub torso collider must pass under the gate mouth')
    if g('Hub.tunnel.ceiling') < mouth_h:
        errors.append('ORDER the tunnel ceiling must not be lower than the gate mouth')
    if g('Hub.gate.frame.2') < mouth_h or g('Hub.gate.frame.1') < mouth_w:
        errors.append('ORDER the gate frame mesh must be at least as big as the mouth it stands in')
    if g('Hub.tunnel.width') < mouth_w * 0.5:
        errors.append('ORDER tunnels must not be narrower than half the gate mouth')
    if g('Hub.tunnel.pathWidth') > g('Hub.tunnel.width'):
        errors.append('ORDER the walking path must fit inside the tunnel')
    # signs and stations: a sign must be taller than the nest pad and food, and no station prop taller than the tunnel ceiling
    for key in ('Hub.sign.stone.2', 'Hub.sign.arrow.2'):
        if g(key) <= g('Nest.pad.2'):
            errors.append(f'ORDER {key} must be taller than the nest pad')
    for key in [k for k in ladder if k.startswith('Hub.station.') and k.endswith('.2')] + ['Nest.ledge.2']:
        if g(key) >= g('Hub.tunnel.ceiling'):
            errors.append(f'ORDER {key} reaches the tunnel ceiling')


# ---------------------------------------------------------------- doc table
def fmt(x):
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s if s else '0'


def render(ladder):
    g = lambda k: float(ladder[k])
    order = [ladder[f'Dino.order.{i}'] for i in range(1, 23)]
    stages = {ladder[f'Dino.stages.{i}.id']: g(f'Dino.stages.{i}.scale') for i in range(1, 7)}
    lines = []
    add = lines.append
    add('All sizes in studs. Generated from `src/shared/ScaleLadder.luau` by `tools/verify_scale_ladder.py --write-doc`; CI fails when this block, the Lua table or the code that builds the things drift apart. **WIRED** = the game code reads the table; **MIRRORED** = the owner module stays the source and the verifier recomputes the value from it.')
    add('')
    add('**Dinosaurs (MIRRORED scale; height at scale 1 is MEASURED for three species and an ESTIMATE for the other 19 until BD-471 measures them in Studio).** Drawn height = height at 1 x the growth scale. In the cave hub every dinosaur is exactly 1x (docs/115).')
    add('')
    head = '| Species | Model scale | Height at 1 | Source | ' + ' | '.join(f'{name} x{fmt(stages[name])}' for name in STAGE_COLUMNS) + ' |'
    add(head)
    add('| --- | ---: | ---: | --- | ' + ' | '.join('---:' for _ in STAGE_COLUMNS) + ' |')
    for sid in order:
        h = g(f'Dino.species.{sid}.height')
        src = 'MEASURED' if ladder[f'Dino.species.{sid}.measured'] == 'true' else 'ESTIMATE'
        cells = ' | '.join(f'{h * stages[name]:.1f}' for name in STAGE_COLUMNS)
        add(f'| {sid} | {fmt(g(f"Dino.species.{sid}.scale"))} | {h:.1f} | {src} | {cells} |')
    add('')
    add('Growth stages (growth = food x 0.1, `s = min(4, sqrt(1 + growth / 50))`): ' + ', '.join(
        f'{ladder[f"Dino.stages.{i}.id"]} x{fmt(g(f"Dino.stages.{i}.scale"))} (growth {fmt(g(f"Dino.stages.{i}.growth"))}{", BIG" if ladder[f"Dino.stages.{i}.big"] == "true" else ""})'
        for i in range(1, 7)) + f'. Hub scale {fmt(g("Dino.hubScale"))}. BIG multiplier {fmt(g("Dino.bigMultiplier"))}. Torso collider {fmt(g("Dino.collider.width"))} wide x {fmt(g("Dino.collider.length"))} long, top {fmt(g("Dino.collider.topPerScale"))} x scale above the floor. Estimate rule: model scale x {fmt(g("HeightPerScaleEstimate"))}.')
    add('')
    add('**World, food and hub (height in studs unless stated).**')
    add('')
    add('| Rung | Size | Where it comes from |')
    add('| --- | --- | --- |')
    food = {k: g(f'Food.{k}.size') for k in ('berry', 'fruit', 'egg', 'amber', 'goldenDrumstick')}
    var_lo, var_hi = g('Food.variety.1'), g('Food.variety.2')
    add(f'| Food berry / fruit / egg / amber (largest side) | {fmt(food["berry"])} / {fmt(food["fruit"])} / {fmt(food["egg"])} / {fmt(food["amber"])}, drawn x{fmt(var_lo)} to x{fmt(var_hi)} | WIRED: `FoodService.TYPES` |')
    add(f'| Golden Drumstick (flag off) | {fmt(food["goldenDrumstick"])}; the drumstick mesh is drawn x{fmt(g("Food.drumstickScale"))}, so up to {food["goldenDrumstick"] * g("Food.drumstickScale") * var_hi:.1f} | WIRED: `SpecialFoods`, `FoodService` |')
    add(f'| Food pickup reach | {fmt(g("Food.pickupRadius"))} | MIRRORED: `Config.FoodPickupRadius` |')
    add(f'| Egg Nest pad (w x h x d) | {fmt(g("Nest.pad.1"))} x {fmt(g("Nest.pad.2"))} x {fmt(g("Nest.pad.3"))} | WIRED: Arena legacy hub; MIRRORED: `CaveHubLayout.Kinds.nest` |')
    add(f'| Nest ledge behind the station (w x h x d) | {fmt(g("Nest.ledge.1"))} x {fmt(g("Nest.ledge.2"))} x {fmt(g("Nest.ledge.3"))} | MIRRORED: `CaveHubLayout.Kinds.hub_nest_ledge` |')
    add(f'| Ground cover (grass, flowers) | {fmt(g("Plants.groundcover.minHeight"))} to {fmt(g("Plants.groundcover.maxHeight"))} | MIRRORED: kit extent x `BiomePlacement.Scales.groundcover` |')
    add(f'| Small band plants (ferns, bushes, mushrooms) | {fmt(g("Plants.small.minHeight"))} to {fmt(g("Plants.small.maxHeight"))} | MIRRORED: `BiomePlacement.SmallBand` |')
    add(f'| Rocks (boulders to {fmt(g("Rocks.island.boulderMaxHeight"))}, spires and ledges to the top) | {fmt(g("Rocks.island.minHeight"))} to {fmt(g("Rocks.island.maxHeight"))} | MIRRORED: kit extent x `BiomePlacement.Scales.rock` ({fmt(g("Rocks.island.scale.1"))} to {fmt(g("Rocks.island.scale.2"))}) |')
    add(f'| Ground rocks, Blender (small / medium / mossy; ids empty) | {fmt(g("Rocks.groundV3.small"))} / {fmt(g("Rocks.groundV3.medium"))} / {fmt(g("Rocks.groundV3.mossy"))} | MIRRORED: `WorldGeneratedMeshes.Props` |')
    add(f'| Landmarks (statue, fossil, arch, altar) | {fmt(g("Landmarks.minHeight"))} to {fmt(g("Landmarks.maxHeight"))} | MIRRORED: kit extent x `BiomePlacement.LandmarkScale` {fmt(g("Landmarks.scale"))} |')
    add(f'| Normal trees | {fmt(g("Trees.normal.minHeight"))} to {fmt(g("Trees.normal.maxHeight"))} | MIRRORED: kit extent {fmt(g("Trees.normal.kitHeight.1"))} to {fmt(g("Trees.normal.kitHeight.2"))} x `Scales.tree` {fmt(g("Trees.normal.scale.1"))} to {fmt(g("Trees.normal.scale.2"))} |')
    add(f'| V3 Blender trees (broadleaf, conifer, palm) | {fmt(g("Trees.v3.minHeight"))} to {fmt(g("Trees.v3.maxHeight"))} | fitted inside the same kit box (`Arena.generatedProp`), so the same range |')
    add(f'| Colossal ancient trees | {fmt(g("Trees.colossal.minHeight"))} to {fmt(g("Trees.colossal.maxHeight"))}, crown at most {fmt(g("Trees.colossal.maxCrown"))}; ancient mesh {fmt(g("Trees.colossal.ancientMesh.broadleaf"))} / {fmt(g("Trees.colossal.ancientMesh.pine"))} / {fmt(g("Trees.colossal.ancientMesh.palm"))} | MIRRORED: `BiomePlacement.Colossal`, `WorldGeneratedMeshes.Colossal` |')
    add(f'| Dino door: gate mouth (w x h) | {fmt(g("Hub.gate.mouthWidth"))} x {fmt(g("Hub.gate.mouthHeight"))}; frame mesh {fmt(g("Hub.gate.frame.1"))} x {fmt(g("Hub.gate.frame.2"))} x {fmt(g("Hub.gate.frame.3"))} | MIRRORED: `CaveHubLayout.get().gate`, `CaveTerrainRules.GateHeight`, `Kinds.cave_gate_frame` |')
    add(f'| Hub tunnel (width, ceiling, path) | {fmt(g("Hub.tunnel.width"))}, {fmt(g("Hub.tunnel.ceiling"))}, {fmt(g("Hub.tunnel.pathWidth"))} | MIRRORED: `CaveHubLayout.TunnelRadius`, tunnel height, `PathHalf` |')
    pads = sorted(k.rsplit('.', 1)[1] for k in ladder if k.startswith('Hub.stationPadRadius.'))
    add('| Station pad radius | ' + ', '.join(f'{p} {fmt(g("Hub.stationPadRadius." + p))}' for p in pads) + ' | MIRRORED: `CaveHubLayout` stations |')
    add(f'| Signs (w x h x d): stone / arrow / legacy board | {fmt(g("Hub.sign.stone.1"))} x {fmt(g("Hub.sign.stone.2"))} x {fmt(g("Hub.sign.stone.3"))} / {fmt(g("Hub.sign.arrow.1"))} x {fmt(g("Hub.sign.arrow.2"))} x {fmt(g("Hub.sign.arrow.3"))} / {fmt(g("Hub.sign.legacyBoard.1"))} x {fmt(g("Hub.sign.legacyBoard.2"))} x {fmt(g("Hub.sign.legacyBoard.3"))} | MIRRORED: `CaveHubLayout.Kinds`; the legacy board is WIRED in `Arena` |')
    names = (('stallPotion', 'Potion stall'), ('forgeAltar', 'Forge altar'), ('counterStone', 'Shop counter'), ('lecternBook', 'Lectern'), ('wallFrame', 'Wall frame'))
    add('| Station props (w x h x d) | ' + '; '.join(f'{label} {fmt(g(f"Hub.station.{k}.1"))} x {fmt(g(f"Hub.station.{k}.2"))} x {fmt(g(f"Hub.station.{k}.3"))}' for k, label in names) + ' | MIRRORED: `CaveHubLayout.Kinds` |')
    return '\n'.join(lines)


def check_doc(ladder, write, errors):
    text = DOC.read_text(encoding='utf-8')
    block = render(ladder)
    if BEGIN not in text or END not in text:
        errors.append(f'docs/114 has no {BEGIN} ... {END} block in section 8.1.1')
        return
    head, rest = text.split(BEGIN, 1)
    old, tail = rest.split(END, 1)
    if old.strip('\n') != block:
        if write:
            DOC.write_text(head + BEGIN + '\n' + block + '\n' + END + tail, encoding='utf-8', newline='')
            print('docs/114 section 8.1.1 rewritten from the Lua table')
        else:
            errors.append('DOC docs/114 section 8.1.1 differs from the table generated from src/shared/ScaleLadder.luau (run: python tools/verify_scale_ladder.py --runner luau.exe --write-doc)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--write-doc', action='store_true')
    parser.add_argument('--print', action='store_true')
    args = parser.parse_args()
    ladder, code = run_luau(args.runner)
    if args.print:
        print(render(ladder))
    errors = []
    check_drift(ladder, code, errors)
    check_wiring(errors)
    check_order(ladder, errors)
    check_doc(ladder, args.write_doc, errors)
    if errors:
        print('scale ladder FAILED:', file=sys.stderr)
        for e in errors:
            print(' - ' + e, file=sys.stderr)
        raise SystemExit(1)
    print(f'scale ladder ok: {len(ladder)} table values checked against the code, order rules and docs/114 section 8.1.1')


if __name__ == '__main__':
    main()
