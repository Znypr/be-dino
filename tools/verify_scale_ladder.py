"""BD-407 (docs/114 section 8.1): offline verifier for the numeric scale ladder src/shared/ScaleLadder.luau.

It runs the REAL source modules in Luau (LowPolyDinoAssets, HubScaleRules, Config, WorldKitData, BiomePlacement, WorldGeneratedMeshes,
CaveHubLayout, ScaleLadder) and fails when:
  1. DRIFT: a size in the code no longer equals the ladder (species model scale, hub scale, growth stages, BIG multiplier, torso
     collider, kit tree/rock/landmark/ground-cover heights, Small band, colossal band, ancient mesh heights, ground rocks, gate mouth,
     tunnels, station pads, hub props and signs), or a WIRED place (FoodService, SpecialFoods, Arena legacy hub) hardcodes a size again;
  2. ORDER: the ladder order breaks (food taller than the smallest dino, a colossal tree not clearly above a normal tree or the tallest
     maxed dino, a normal-run dino taller than the biggest normal tree, the dino door lower than the largest hub dino, ...);
  3. DOC: the table in docs/114 section 8.1.1 differs from the one generated from the Lua table (rewrite it with --write-doc).
  4. SIZING (BD-232): every species is within 2% of the owner rule (about 10% growth per unlock tier: ground by height from the 6.6 Compy,
     fly and water by bulk, the T-Rex on top), higher tiers are bigger, no ground dino is below the Compy or above the T-Rex.
Not Studio evidence: heights of unmeasured species are ESTIMATES (see Dino.species[..].measured); all 22 are measured since BD-471.
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
# Studio bounding boxes of LowPolyDinos.clone(species) at spawn (growth scale 1), playtest build, template pose, Model:GetBoundingBox
# (width, height, length) in studs: BD-471 (2026-10-17) measured them at the BD-225 scales, BD-232 (2026-10-17) re-measured them after the
# per-species scale change (docs/evidence/2026-10-17-species-sizes/). C-39 (docs/116): the three Water species are now sized by BULK; their boxes
# below were re-read in Studio after the change (docs/evidence/2026-10-17-water-bulk/).
MEASURED = {
    'compy': (3.49, 6.60, 7.69),
    'triceratops': (5.79, 8.00, 8.58),
    'tyrannosaurus': (5.83, 10.62, 11.43),  # BD-992: SCALED_FROM_STUDIO (the BD-232 Studio box 5.31 x 9.67 x 10.41 at scale 3.47, now scale 3.81)
    'raptor': (3.49, 6.60, 7.74),
    'stegosaurus': (5.25, 7.25, 11.70),
    'ankylosaurus': (5.77, 6.51, 10.68),  # BD-992: SCALED_FROM_STUDIO (the BD-232 Studio box 7.78 x 8.78 x 14.40 at scale 3.6, now scale 2.67)
    'archaeopteryx': (7.17, 5.31, 5.92),
    'baryonyx': (3.99, 7.99, 9.33),
    'brachiosaurus': (3.73, 8.00, 8.73),
    'dimorphodon': (5.76, 5.13, 5.73),
    'elasmosaurus': (3.95, 8.78, 10.74),
    'gallimimus': (2.42, 6.61, 7.78),
    'ichthyosaurus': (4.89, 5.57, 11.13),
    'microraptor': (7.11, 4.56, 5.29),
    'mosasaurus': (5.48, 5.77, 16.92),
    'pachycephalosaurus': (4.51, 7.25, 8.43),
    'parasaurolophus': (5.30, 7.27, 9.09),
    'plesiosaurus': (4.66, 7.74, 8.34),
    'pteranodon': (7.07, 4.62, 6.89),
    'quetzalcoatlus': (8.20, 6.12, 8.04),
    'spinosaurus': (5.53, 9.66, 12.06),
    'therizinosaurus': (4.91, 8.78, 10.24),
}
# BD-606 (docs/115 SS8): the seven SECRET species (Shared/SecretSpeciesConfig). No mesh exists yet, so these boxes (width, height, length at spawn)
# are DESIGN ESTIMATES with bird proportions, the very numbers in ScaleLadder.Dino.secret.species (drift-checked below). When a secret gets its
# mesh, its row is re-read from the Studio bounding box, this table is updated and the row's `measured` turns true. Also used by the camera,
# hit size and mouth reach verifiers, so the secrets are covered by every sizing rule with their model slot empty or filled.
SECRET_BOXES = {
    'chickosaurus': (3.92, 6.61, 6.12),  # MEASURED at scale 1 1.28 x 2.16 x 2 (docs/173) x 3.06
    'pigeon': (5.21, 6.61, 5.72),  # MEASURED at scale 1 1.82 x 2.31 x 2 (docs/173) x 2.86
    'dodo': (3.81, 6.61, 6.92),  # MEASURED at scale 1 1.1 x 1.91 x 2 (docs/173) x 3.46
    'duck': (4.39, 6.61, 6.06),  # MEASURED at scale 1 1.45 x 2.18 x 2 (docs/173) x 3.03
    'penguin': (5.81, 6.19, 4.76),  # MEASURED at scale 1 2.44 x 2.6 x 2 (docs/173) x 2.38
    'budgiesaurus': (3.60, 6.60, 7.12),  # MEASURED at scale 1 4 x 7.33 x 7.91 (docs/173) x 0.9
    'foxosaurus': (3.00, 6.64, 6.32),  # MEASURED (BD-602 v2 Place 1 box 3.8 x 8.4 x 8.0 at scale 1) x 0.79
    'cockatoosaurus': (3.80, 6.66, 6.74),  # MEASURED at scale 1 3.427 x 6 x 6.07 (docs/173) x 1.11
    'eaglesaurus': (4.00, 5.52, 7.75),  # MEASURED at scale 1 4 x 5.518 x 7.747 (docs/173) x 1.0
}
SECRET_SIZE_TIER = 1  # SS8: every secret is sized as a tier 1 (Compy-sized) find
# BD-992 (owner 2026-10-18, "T-Rex must be the biggest"): two rows changed scale and were NOT re-read in Studio (no window). Their box is the last Studio
# box times new scale / old scale (the method that matched Studio to 2 decimals for the C-39 water change). Row: species -> (Studio box at the old scale,
# old scale, new scale). Their `measured` flag in ScaleLadder is false until a Studio re-read; MEASURED above holds the SCALED box so the camera and hit
# verifiers keep one source of boxes. Remove the entry here (and set measured = true) once the real box is read.
SCALED_FROM_STUDIO = {
    'tyrannosaurus': ((5.31, 9.67, 10.41), 3.47, 3.81),
    'ankylosaurus': ((7.78, 8.78, 14.40), 3.6, 2.67),
}
ALL_BOXES = {**MEASURED, **SECRET_BOXES}  # the 22 shipped species + the 7 secrets
TOLERANCE = 0.02  # BD-232: allowed relative gap between a species size and the 10%-per-tier rule
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
-- BD-606: the secret roster, its class, its model slot and whether it is ready (a filled, positive whole asset id)
out("secret.order", table.concat(Secret.Order, ","))
local ready = Secret.readyIds()
out("secret.ready", table.concat(ready, ","))
for _, id in Secret.Order do
    local s = Secret.Species[id]
    out("secretcfg." .. id .. ".class", s.class)
    out("secretcfg." .. id .. ".assetId", s.assetId)
    out("secretcfg." .. id .. ".ready", Secret.modelReady(id))
    local entry = LowPoly[id]
    out("secretlow." .. id .. ".present", entry ~= nil)
    if entry then
        out("secretlow." .. id .. ".assetId", entry.assetId)
        out("secretlow." .. id .. ".scale", entry.scale)
        out("secretlow." .. id .. ".tier", entry.tier)
        out("secretlow." .. id .. ".class", entry.class)
    end
end
out("order", table.concat(Config.SpeciesOrder, ","))
for id, row in LowPoly do
    out("species." .. id .. ".scale", row.scale)
    out("species." .. id .. ".class", row.class)
    out("species." .. id .. ".tier", row.tier)
    out("species." .. id .. ".rarity", Config.SpeciesRarities[id])
end
for _, basis in {"height", "bulk", "length"} do
    for tier = 1, 5 do out("rule." .. basis .. "." .. tier, Ladder.targetSize(basis, tier)) end
end
out("rule.sizeOf.bulk", Ladder.sizeOf("bulk", 2, 3, 4))
out("sizing.tier.tyrannosaurus", Ladder.sizingTier("tyrannosaurus"))
out("sizing.tier.compy", Ladder.sizingTier("compy"))
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
        + 'local Secret=' + wrapped('src/shared/SecretSpeciesConfig.luau') + '\n'
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
    # BD-606: LowPolyDinoAssets lists the 22 shipped species, plus exactly the secret species whose model slot is filled (never an invented entry)
    ready = [x for x in code['secret.ready'].split(',') if x]
    if code['lowpoly.ids'] != ','.join(sorted(ladder_order + ready)):
        errors.append('DRIFT species: LowPolyDinoAssets lists different species than the ladder (the 22 plus the secrets with a filled model slot)')
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
        if sid in SCALED_FROM_STUDIO:
            old_box, old_scale, new_scale = SCALED_FROM_STUDIO[sid]
            want_box = tuple(round(x * new_scale / old_scale + 1e-9, 2) for x in old_box)
            box = tuple(num(ladder, f'Dino.species.{sid}.{k}') for k in ('width', 'height', 'length'))
            if measured:
                errors.append(f'{sid}: the box is scaled from the Studio box, not re-read (BD-992), so measured must be false')
            if not close(new_scale, row_s, 1e-9):
                errors.append(f'{sid}: SCALED_FROM_STUDIO says scale {new_scale} but the ladder says {row_s}')
            if any(not close(x, y, 0.011) for x, y in zip(box, want_box)) or any(not close(x, y, 1e-9) for x, y in zip(box, MEASURED[sid])):
                errors.append(f'{sid}: ladder box {box} is not the Studio box {old_box} x {new_scale}/{old_scale} = {want_box} (BD-992)')
        elif measured != (sid in MEASURED):
            errors.append(f'{sid}: measured flag {measured} disagrees with the Studio-measured list {sorted(MEASURED)}')
        elif measured:
            box = tuple(num(ladder, f'Dino.species.{sid}.{k}') for k in ('width', 'height', 'length'))
            if any(not close(x, y, 1e-9) for x, y in zip(box, MEASURED[sid])):
                errors.append(f'{sid}: ladder box {box} differs from the Studio bounding box {MEASURED[sid]}')
        elif not close(row_h, row_s * est, 0.05 + 1e-9):
            errors.append(f'{sid}: estimated height {row_h} is not scale {row_s} x {est} (rounded to 0.1)')
    # Arena colossal and growth formula text checks for the parts that need a require chain
    terrain = (ROOT / 'src/shared/CaveTerrainRules.luau').read_text(encoding='utf-8')
    m = re.search(r'^Rules\.GateHeight = ([\d.]+)', terrain, re.M)
    if not m or not close(float(m.group(1)), num(ladder, 'Hub.gate.mouthHeight'), 1e-9):
        errors.append(f'DRIFT Hub.gate.mouthHeight: ladder {ladder["Hub.gate.mouthHeight"]} but CaveTerrainRules.GateHeight is {m.group(1) if m else "missing"}')


def size_of(basis, box):
    w, h, l = box
    return {'height': h, 'length': l, 'bulk': (w * h * l) ** (1 / 3)}[basis]


def check_sizing(ladder, code, errors):
    """BD-232 owner rule: about 10% growth per unlock tier (ground by height, fly by bulk, water by length, T-Rex on top)."""
    g = lambda k: num(ladder, k)
    order = [ladder[f'Dino.order.{i}'] for i in range(1, 23)]
    growth, tol, top = g('Sizing.growthPerTier'), g('Sizing.tolerance'), int(g('Sizing.topTier'))
    if not close(growth, 1.1, 1e-9) or not close(tol, TOLERANCE, 1e-9) or top != 5:
        errors.append(f'SIZING the rule constants must be growth 1.1, tolerance {TOLERANCE}, top tier 5 (owner BD-232), found {growth}, {tol}, {top}')
    king, steps = ladder.get('Sizing.kingSpecies'), int(g('Sizing.kingSteps'))
    if king != 'tyrannosaurus' or steps != 1:
        errors.append(f'SIZING the king must be the tyrannosaurus one growth step above the top tier (owner 2026-10-18, BD-992), found {king}, {steps}')
    if not close(num(code, f'sizing.tier.{king}'), int(g(f'Dino.species.{king}.tier')) + steps, 1e-9):
        errors.append('SIZING ScaleLadder.sizingTier(king) must be its unlock tier plus kingSteps')
    if not close(num(code, 'sizing.tier.compy'), int(g('Dino.species.compy.tier')), 1e-9):
        errors.append('SIZING ScaleLadder.sizingTier of an ordinary species must be its unlock tier')
    rule = {
        'height': lambda t: g('Sizing.height.tier1') * growth ** (t - 1),
        'bulk': lambda t: g('Sizing.bulk.top') / growth ** (top - t),
        'length': lambda t: g('Sizing.length.top') / growth ** (top - t),
    }
    # the Lua helper equals the rule, and growth between tiers is the owner's 10%
    for basis, fn in rule.items():
        for tier in range(1, 6):
            if not close(num(code, f'rule.{basis}.{tier}'), fn(tier), 1e-9):
                errors.append(f'SIZING ScaleLadder.targetSize({basis}, {tier}) differs from the rule')
        for tier in range(1, 5):
            ratio = fn(tier + 1) / fn(tier)
            if not close(ratio, 1.1, 0.005):
                errors.append(f'SIZING {basis} targets must grow 10% per tier, tier {tier} to {tier + 1} is x{ratio:.3f}')
    if not close(num(code, 'rule.sizeOf.bulk'), 24 ** (1 / 3), 1e-9):
        errors.append('SIZING ScaleLadder.sizeOf bulk must be the cube root of width x height x length')
    if not close(g('Sizing.height.tier1'), g('Dino.species.compy.height'), 0.005):
        errors.append('SIZING Compy (tier 1) must be the height anchor 6.6')
    box = {sid: tuple(g(f'Dino.species.{sid}.{k}') for k in ('width', 'height', 'length')) for sid in order}
    rex = box['tyrannosaurus']
    king_f = growth ** steps
    if not close(size_of('bulk', rex), g('Sizing.bulk.top') * king_f, 0.005 * g('Sizing.bulk.top') * king_f) or not close(rex[2], g('Sizing.length.top') * king_f, 0.03):
        errors.append('SIZING the T-Rex is the king: its bulk and length equal Sizing.bulk.top and Sizing.length.top times the king step')
    # BD-992 (owner 2026-10-18, "T-Rex must be the biggest"): the T-Rex is the biggest dinosaur by volume (bulk) and the tallest, with a margin so a rounding
    # of a scale can never flip it. LENGTH is deliberately not asserted: a long low swimmer and the Spinosaurus are longer (fly/water by bulk, owner BD-232).
    rex_bulk, rex_height = size_of('bulk', rex), rex[1]
    for sid in order:
        if sid == 'tyrannosaurus':
            continue
        if size_of('bulk', box[sid]) > rex_bulk * 0.98:
            errors.append(f'BIGGEST {sid} bulk {size_of("bulk", box[sid]):.2f} is not at least 2% below the T-Rex {rex_bulk:.2f} (owner 2026-10-18: the T-Rex must be the biggest)')
        if box[sid][1] > rex_height * 0.95:
            errors.append(f'BIGGEST {sid} height {box[sid][1]:.2f} is not at least 5% below the T-Rex {rex_height:.2f}')
    for sid, b in SECRET_BOXES.items():
        if size_of('bulk', b) > rex_bulk * 0.98 or b[1] > rex_height * 0.95:
            errors.append(f'BIGGEST secret {sid} is not clearly smaller than the T-Rex')
    expect_basis = {'Fly': 'bulk', 'Water': 'bulk', 'Armored': 'bulk'}
    by_tier = {}
    for sid in order:
        tier, basis = int(g(f'Dino.species.{sid}.tier')), ladder[f'Dino.species.{sid}.basis']
        if tier != int(num(code, f'species.{sid}.rarity')) or tier != int(num(code, f'species.{sid}.tier')):
            errors.append(f'SIZING {sid}: tier {tier} differs from Config.SpeciesRarities {code[f"species.{sid}.rarity"]} / LowPolyDinoAssets tier {code[f"species.{sid}.tier"]}')
        if basis != expect_basis.get(code[f'species.{sid}.class'], 'height'):
            errors.append(f'SIZING {sid}: basis {basis} does not fit class {code[f"species.{sid}.class"]} (Ground height, Fly, Water and Armored bulk)')
        size_tier = tier + (steps if sid == king else 0)  # BD-992: the king is sized one growth step above its unlock tier
        want = rule[basis](size_tier)
        target = g(f'Dino.species.{sid}.target')
        if not close(target, want, 0.006):
            errors.append(f'SIZING {sid}: target {target} is not the rule value {want:.3f} for {basis} tier {tier}')
        got = size_of(basis, box[sid])
        if abs(got - want) > tol * want:
            errors.append(f'SIZING {sid} ({basis}, tier {size_tier}): size {got:.2f} is more than {tol:.0%} from the rule {want:.2f}; set its LowPolyDinoAssets scale')
        by_tier.setdefault((basis, size_tier), []).append(got)
    # unlock order: every higher tier is bigger than every lower tier by about 10% per step (ground height; fly and water bulk)
    for basis in ('height', 'bulk', 'length'):
        tiers = sorted(t for b, t in by_tier if b == basis)
        for lo, hi in zip(tiers, tiers[1:]):
            small, big = max(by_tier[(basis, lo)]), min(by_tier[(basis, hi)])
            floor = (growth ** (hi - lo)) * (1 - tol) / (1 + tol)
            if big < small * floor - 1e-9:
                errors.append(f'SIZING {basis}: tier {hi} smallest {big:.2f} is not about {growth ** (hi - lo):.2f}x tier {lo} largest {small:.2f} (needs >= x{floor:.3f})')
    # the starter is the smallest ground dino, the T-Rex is the tallest ground dino
    ground = [sid for sid in order if ladder[f'Dino.species.{sid}.basis'] == 'height']
    compy_h, rex_h = box['compy'][1], box['tyrannosaurus'][1]
    for sid in ground:
        if box[sid][1] < compy_h * (1 - tol):
            errors.append(f'SIZING ground {sid} ({box[sid][1]:.2f}) is below the starter Compy ({compy_h})')
        if box[sid][1] > rex_h * (1 + tol):
            errors.append(f'SIZING ground {sid} ({box[sid][1]:.2f}) is taller than the T-Rex ({rex_h})')
    for sid in order:  # fly, water and armored: never above the Legendary level (and so below the T-Rex king) on their own basis
        basis = ladder[f'Dino.species.{sid}.basis']
        top_v = {'bulk': g('Sizing.bulk.top'), 'length': g('Sizing.length.top')}.get(basis) if sid != king else None
        if top_v and size_of(basis, box[sid]) > top_v * (1 + tol):
            errors.append(f'SIZING {sid} {basis} {size_of(basis, box[sid]):.2f} is above the T-Rex top {top_v}')


def check_secret(ladder, code, errors):
    """BD-606 (docs/115 SS8): the seven secret species follow the SZ1 rule with a Compy-sized tier 1, their rows equal SECRET_BOXES, and a
    secret with a filled model slot has a LowPolyDinoAssets entry that equals its ladder row and a MEASURED box (never an estimate in the game)."""
    g = lambda k: num(ladder, k)
    growth, top = g('Sizing.growthPerTier'), int(g('Sizing.topTier'))
    rule = {
        'height': lambda t: g('Sizing.height.tier1') * growth ** (t - 1),
        'bulk': lambda t: g('Sizing.bulk.top') / growth ** (top - t),
    }
    tol = g('Sizing.tolerance')
    order = [ladder[f'Dino.secret.order.{i}'] for i in range(1, 12) if f'Dino.secret.order.{i}' in ladder]
    if ','.join(order) != code['secret.order']:
        errors.append('SECRET ScaleLadder.Dino.secret.order differs from SecretSpeciesConfig.Order')
    if sorted(order) != sorted(SECRET_BOXES):
        errors.append('SECRET the verifier SECRET_BOXES list differs from the ladder secret roster')
    ready = {x for x in code['secret.ready'].split(',') if x}
    expect_basis = {'Fly': 'bulk', 'Water': 'bulk'}
    for sid in order:
        key = f'Dino.secret.species.{sid}'
        cls = code[f'secretcfg.{sid}.class']
        tier, basis, target = int(g(f'{key}.tier')), ladder[f'{key}.basis'], g(f'{key}.target')
        if tier != SECRET_SIZE_TIER:
            errors.append(f'SECRET {sid}: size tier {tier}, SS8 says {SECRET_SIZE_TIER} (Compy-sized)')
        if basis != expect_basis.get(cls, 'height'):
            errors.append(f'SECRET {sid}: basis {basis} does not fit class {cls} (Ground height, Fly and Water bulk, SZ1)')
        want = rule[basis](tier)
        if not close(target, want, 0.006):
            errors.append(f'SECRET {sid}: target {target} is not the rule value {want:.3f} for {basis} tier {tier}')
        box = tuple(g(f'{key}.{k}') for k in ('width', 'height', 'length'))
        if sid in SECRET_BOXES and any(not close(x, y, 1e-9) for x, y in zip(box, SECRET_BOXES[sid])):
            errors.append(f'SECRET {sid}: ladder box {box} differs from SECRET_BOXES {SECRET_BOXES[sid]} (update both when a mesh is measured)')
        got = size_of(basis, box)
        if abs(got - want) > tol * want:
            errors.append(f'SECRET {sid} ({basis}, tier {tier}): size {got:.2f} is more than {tol:.0%} from the rule {want:.2f}')
        length, snout, head = box[2], g(f'{key}.snout'), g(f'{key}.headLength')
        if abs(snout - length / 2) > 0.03 or not 0 < head <= length:
            errors.append(f'SECRET {sid}: snout {snout} / head length {head} out of range for a body {length} long')
        scale = g(f'{key}.scale')
        if not 0.5 <= scale <= 6:
            errors.append(f'SECRET {sid}: scale {scale} outside the sane range 0.5 to 6')
        measured = ladder[f'{key}.measured'] == 'true'
        has_model = sid in ready
        if has_model != (code[f'secretcfg.{sid}.ready'] == 'true'):
            errors.append(f'SECRET {sid}: ready list disagrees with modelReady')
        if has_model and not measured:
            errors.append(f'SECRET {sid}: the model slot is filled but the ladder row is still an ESTIMATE; measure the real mesh in Studio (docs/149 s3) and set measured = true')
        if measured and not has_model:
            errors.append(f'SECRET {sid}: the row says measured but the model slot is empty')
        if code[f'secretlow.{sid}.present'] == 'true':
            if not has_model:
                errors.append(f'SECRET {sid}: LowPolyDinoAssets has an entry but the SecretSpeciesConfig model slot is empty (never invent ids)')
            else:
                if code[f'secretlow.{sid}.assetId'] != code[f'secretcfg.{sid}.assetId']:
                    errors.append(f'SECRET {sid}: LowPolyDinoAssets assetId {code[f"secretlow.{sid}.assetId"]} differs from the SecretSpeciesConfig slot {code[f"secretcfg.{sid}.assetId"]}')
                if not close(num(code, f'secretlow.{sid}.scale'), scale, 1e-9):
                    errors.append(f'SECRET {sid}: LowPolyDinoAssets scale {code[f"secretlow.{sid}.scale"]} differs from the ladder {scale}')
                if int(num(code, f'secretlow.{sid}.tier')) != tier or code[f'secretlow.{sid}.class'] != cls:
                    errors.append(f'SECRET {sid}: LowPolyDinoAssets tier/class differ from the ladder tier {tier} / class {cls}')
        elif has_model:
            errors.append(f'SECRET {sid}: the model slot is filled but LowPolyDinoAssets has no entry (the hatch would show no dino)')


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
    n_measured = sum(1 for sid in order if ladder[f'Dino.species.{sid}.measured'] == 'true')
    add(f'**Dinosaurs (MIRRORED scale; the box at spawn is MEASURED in Studio for {n_measured} of {len(order)} species, BD-471 and BD-232, 2026-10-17{"" if n_measured == len(order) else ", the rest are ESTIMATES"}).** Drawn height = height at spawn x the growth scale. Sizes follow the BD-232 rule (docs/115): about 10% growth per unlock tier, ground by height from the 6.6 Compy, fly and water by bulk (cube root of W x H x L), Armored by bulk too, and the T-Rex one growth step above the top tier so it is the biggest and tallest dino (BD-992, owner 2026-10-18; the Ankylosaurus and T-Rex boxes are scaled from the Studio boxes, not re-read; C-39: water was by length until 2026-10-17). In the cave hub every dinosaur is exactly 1x (docs/115).')
    add('')
    head = '| Species | Tier | Basis | Target | Model scale | W x H x L at spawn | Source | ' + ' | '.join(f'{name} height x{fmt(stages[name])}' for name in STAGE_COLUMNS) + ' |'
    add(head)
    add('| --- | ---: | --- | ---: | ---: | --- | --- | ' + ' | '.join('---:' for _ in STAGE_COLUMNS) + ' |')
    for sid in order:
        h = g(f'Dino.species.{sid}.height')
        src = 'MEASURED' if ladder[f'Dino.species.{sid}.measured'] == 'true' else 'ESTIMATE'
        cells = ' | '.join(f'{h * stages[name]:.1f}' for name in STAGE_COLUMNS)
        dims = ' x '.join(f'{g(f"Dino.species.{sid}.{k}"):.2f}' for k in ('width', 'height', 'length'))
        add(f'| {sid} | {int(g(f"Dino.species.{sid}.tier"))} | {ladder[f"Dino.species.{sid}.basis"]} | {g(f"Dino.species.{sid}.target"):.2f} | {fmt(g(f"Dino.species.{sid}.scale"))} | {dims} | {src} | {cells} |')
    add('')
    sec = [ladder[f'Dino.secret.order.{i}'] for i in range(1, 12) if f"Dino.secret.order.{i}" in ladder]
    n_sec = sum(1 for sid in sec if ladder[f'Dino.secret.species.{sid}.measured'] == 'true')
    add(f'**Secret species (BD-606, docs/115 SS8; behind `SecretSpeciesEnabled`: off in the default profile, on in the playtest; only a species with a bound model can drop, docs/173).** Sized by the same rule as tier 1 (Compy-sized); {n_sec} of {len(sec)} are measured. A row stays an ESTIMATE (design box, bird proportions) until its mesh exists; a secret whose model slot is filled must be MEASURED.')
    add('')
    add('| Secret species | Tier | Basis | Target | Model scale | W x H x L at spawn | Source |')
    add('| --- | ---: | --- | ---: | ---: | --- | --- |')
    for sid in sec:
        k = f'Dino.secret.species.{sid}'
        dims = ' x '.join(f'{g(f"{k}.{x}"):.2f}' for x in ('width', 'height', 'length'))
        add(f'| {sid} | {int(g(f"{k}.tier"))} | {ladder[f"{k}.basis"]} | {g(f"{k}.target"):.2f} | {fmt(g(f"{k}.scale"))} | {dims} | {"MEASURED" if ladder[f"{k}.measured"] == "true" else "ESTIMATE"} |')
    add('')
    add('Growth stages (growth = food x 0.1, `s = min(4, sqrt(1 + growth / 50))`): ' + ', '.join(
        f'{ladder[f"Dino.stages.{i}.id"]} x{fmt(g(f"Dino.stages.{i}.scale"))} (growth {fmt(g(f"Dino.stages.{i}.growth"))}{", BIG" if ladder[f"Dino.stages.{i}.big"] == "true" else ""})'
        for i in range(1, 7)) + f'. Hub scale {fmt(g("Dino.hubScale"))}. BIG multiplier {fmt(g("Dino.bigMultiplier"))}. Torso collider {fmt(g("Dino.collider.width"))} wide x {fmt(g("Dino.collider.length"))} long, top {fmt(g("Dino.collider.topPerScale"))} x scale above the floor. Size rule: growth {fmt(g("Sizing.growthPerTier"))} per tier, tolerance {g("Sizing.tolerance"):.0%}, height tier 1 = {fmt(g("Sizing.height.tier1"))}, bulk top {fmt(g("Sizing.bulk.top"))}, length top {fmt(g("Sizing.length.top"))}.')
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
    check_sizing(ladder, code, errors)
    check_secret(ladder, code, errors)
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
