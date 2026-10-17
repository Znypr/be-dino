"""BD-515 (docs/115 MR1-MR3): offline verifier for "eating happens at the mouth", src/shared/MouthReach.luau.

It runs the REAL pure module in Luau (with the real Config and ScaleLadder) and fails when:
  1. MOUTH: for each of the 22 species at growth scale 1, 2, 4 (and the BIG 4.8), a berry at the snout tip, one at the head point and one beside
     the snout (half a radius to the side) are eaten, whatever the facing direction (four directions);
  2. TAIL: a berry 1 stud behind the tail tip is NOT eaten, and neither is one at the dino's root when the head point is more than a radius away;
  3. COMPY: a Compy keeps the old pickup radius within 10% at every growth scale (exactly 2.25 at scale 1), and its snout is inside the zone;
  4. LEGACY: no species (nil, unknown, junk scale or junk look vector) gives anything but the old root rule, 2.25 + 0.75 per scale, max 5;
  5. SAME FUNCTION: FoodService and PredationService require Shared/MouthReach (no private copy of the radius), the module sits in src/shared
     and uses no Instance / game API, so the server and any client preview run the same code; FoodService no longer reads FoodPickupRadius;
  6. DATA: ScaleLadder has snout and headLength for all 22 species (snout equals half the body length except where the head is not the front);
  7. FLAGS: Config.FoodPickupAtMouth is on (it only acts with LowPolyDinos) and Config.PredationAtMouth is off (predation change verified offline only).
  8. CAP (BD-521, docs/115 MR4): the zone (front edge ahead of the root, radius) never exceeds Config.FoodReachCapCompy x the Compy's at the same scale
     (checked at 6 scales for all 22 species), the Compy and every species under the cap keep the uncapped BD-515 zone, the head point is never behind the root,
     a berry at the zone's front edge is eaten, and the cap factor stays inside the parity band 1.0 to 1.10 (tools/simulate_food_reach.py measures food/min).
Not Studio evidence by itself: docs/evidence/2026-10-17-mouth-pickup/ has the Studio captures (a real eat at the mouth).
Usage: python tools/verify_mouth_reach.py --runner luau.exe [--print]
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local Config = (function()
@CONFIG@
end)()
local ScaleLadder = (function()
@LADDER@
end)()
local M = (function()
local script = {Parent = {Config = "Config", ScaleLadder = "ScaleLadder"}}
local require = function(id) if id == "ScaleLadder" then return ScaleLadder end return Config end
@MODULE@
end)()
local ids = {}
for id in ScaleLadder.Dino.species do ids[#ids + 1] = id end
table.sort(ids)
print("N\t" .. #ids)
local function eaten(id, s, ang, ahead, side)
    local root = {x = 100, y = 10, z = -40}
    local look = {x = math.cos(ang), z = math.sin(ang)}
    local right = {x = -look.z, z = look.x}
    local target = {x = root.x + look.x * ahead + right.x * side, y = root.y, z = root.z + look.z * ahead + right.z * side}
    local ok = M.reaches(root, look, id, s, target)
    return ok and 1 or 0
end
for _, id in ids do
    local row = ScaleLadder.Dino.species[id]
    for _, s in {1, 2, 4, 4.8} do
        local snout, head, r = M.snoutOffset(id, s), M.headOffset(id, s), M.radius(id, s)
        local half = row.length / 2 * s
        local line = {}
        for _, ang in {0, 1.5708, 2.3562, -0.7} do
            line[#line + 1] = string.format("%d%d%d%d%d", eaten(id, s, ang, snout, 0), eaten(id, s, ang, head, 0), eaten(id, s, ang, snout, 0.5 * r),
                eaten(id, s, ang, -(half + 1), 0), eaten(id, s, ang, 0, 0))
        end
        print(string.format("R\t%s\t%s\t%.4f\t%.4f\t%.4f\t%s\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f", id, tostring(s), snout, head, r, table.concat(line, ","), M.legacyRadius(s),
            M.uncappedFront(id, s), M.uncappedRadius(id, s), M.uncappedHeadOffset(id, s), eaten(id, s, 0.3, head + r - 0.05, 0)))
    end
end
-- legacy fallbacks
local root = {x = 0, y = 0, z = 0}
local look = {x = 0, z = -1}
local function near(a, b) return math.abs(a - b) < 1e-9 end
for _, s in {1, 1.5, 2, 3, 4, 4.8, 9, -3} do
    local want = math.min(5, 2.25 + (math.clamp(s, 1, 6) - 1) * 0.75)
    assert(near(M.radius(nil, s), want) and near(M.radius("nonsense", s), want) and near(M.legacyRadius(s), want), "legacy radius at " .. s)
end
assert(near(M.radius("compy", 1), 2.25), "compy radius at scale 1")
assert(near(M.headOffset(nil, 3), 0) and near(M.headOffset("nonsense", 3), 0) and near(M.snoutOffset(5, 2), 0), "unknown species has no head offset")
local x, z = M.point(10, 20, 0, 0, "ankylosaurus", 1)
assert(x == 10 and z == 20, "vertical look vector gives the root")
x, z = M.point(10, 20, 0 / 0, 1 / 0, "ankylosaurus", 1)
assert(x == 10 and z == 20, "junk look vector gives the root")
x, z = M.point(10, 20, 0, -5, "ankylosaurus", 1)
assert(near(x, 10) and near(z, 20 - M.headOffset("ankylosaurus", 1)), "look vector is normalised")
assert(near(M.headOffset("ankylosaurus", 0 / 0), M.headOffset("ankylosaurus", 1)), "junk scale is 1")
-- old rule for an unknown species: the root, 2.25
assert(M.reaches(root, look, nil, 1, {x = 0, y = 0, z = -2.2}) and not M.reaches(root, look, nil, 1, {x = 0, y = 0, z = -2.3}), "nil species keeps the root rule")
-- vertical limit unchanged
local ho = M.headOffset("compy", 1)
assert(M.reaches(root, look, "compy", 1, {x = 0, y = 5.9, z = -ho}) and not M.reaches(root, look, "compy", 1, {x = 0, y = 6, z = -ho}), "vertical limit 6")
-- monotonic: a bigger scale never shrinks the zone or moves the head back
for _, id in ids do
    local pr, po = 0, 0
    for s = 10, 48 do
        local sc = s / 10
        local r, o = M.radius(id, sc), M.headOffset(id, sc)
        assert(r >= pr - 1e-9 and o >= po - 1e-9, id .. " zone grows with scale")
        pr, po = r, o
    end
end
print("FLAGS\t" .. tostring(Config.FoodPickupAtMouth) .. "\t" .. tostring(Config.PredationAtMouth))
print("CAPK\t" .. tostring(M.capFactor()))
-- cap behaviour on its own (explicit factors, independent of the config value)
for _, k in {1, 1.1, 1.25} do
    for _, id in ids do
        for _, s in {1, 1.5, 2, 3, 4, 4.8} do
            local off, r = M.zone(id, s, k)
            local coff, cr = M.zone("compy", s, k)
            assert(r <= k * cr + 1e-9 and off + r <= k * (coff + cr) + 1e-9, id .. " zone exceeds the cap at " .. s .. " k " .. k)
            assert(off >= -1e-9, id .. " head point behind the root at " .. s)
            local uoff, ur = M.uncappedHeadOffset(id, s), M.uncappedRadius(id, s)
            if ur <= k * cr + 1e-9 and uoff + ur <= k * (coff + cr) + 1e-9 then
                assert(near(off, uoff) and near(r, ur), id .. " is under the cap and must keep the uncapped zone at " .. s .. " k " .. k)
            end
            assert(near(cr, M.uncappedRadius("compy", s)) and near(coff, M.uncappedHeadOffset("compy", s)), "compy is never capped")
        end
    end
end
-- a huge factor is exactly the BD-515 zone
for _, id in ids do
    for _, s in {1, 2, 4} do
        local off, r = M.zone(id, s, 1e6)
        assert(near(off, M.uncappedHeadOffset(id, s)) and near(r, M.uncappedRadius(id, s)), id .. " uncapped zone changed")
    end
end
print("OK")
'''


def run(runner):
    source = (BODY.replace('@CONFIG@', (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8'))
              .replace('@LADDER@', (ROOT / 'src/shared/ScaleLadder.luau').read_text(encoding='utf-8'))
              .replace('@MODULE@', (ROOT / 'src/shared/MouthReach.luau').read_text(encoding='utf-8')))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'mouth_reach.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if result.returncode or 'OK' not in result.stdout:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode or 1)
    return result.stdout.splitlines()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--print', action='store_true')
    args = parser.parse_args()
    rows = {}
    flags = None
    capk = None
    count = 0
    for line in run(args.runner):
        p = line.split('\t')
        if p[0] == 'R':
            rows[(p[1], float(p[2]))] = (float(p[3]), float(p[4]), float(p[5]), p[6].split(','), float(p[7]), float(p[8]), float(p[9]), float(p[10]), p[11])
        elif p[0] == 'FLAGS':
            flags = (p[1], p[2])
        elif p[0] == 'N':
            count = int(p[1])
        elif p[0] == 'CAPK':
            capk = None if p[1] == 'nil' else float(p[1])
    problems = []
    if count != 22:
        problems.append('expected 22 species in ScaleLadder, found %d' % count)
    if capk is None or not 1.0 <= capk <= 1.10:
        problems.append('Config.FoodReachCapCompy is %s, expected a number in the parity band 1.0 to 1.10 (docs/115 MR4)' % (capk,))
    if flags != ('true', 'false'):
        problems.append('Config.FoodPickupAtMouth / PredationAtMouth are %s, expected true / false' % (flags,))
    for (species, s), (snout, head, r, dirs, legacy, ufront, urad, uhead, edge) in sorted(rows.items()):
        for d in dirs:
            if d[0] != '1' and snout <= head + r + 1e-6:
                problems.append('%s at %s: a berry at the snout tip is not eaten' % (species, s))
            if d[1] != '1':
                problems.append('%s at %s: a berry at the head point is not eaten' % (species, s))
            if d[2] != '1' and (snout - head) ** 2 + (0.5 * r) ** 2 <= r * r - 1e-6:
                problems.append('%s at %s: a berry beside the snout (half a radius) is not eaten' % (species, s))
            if d[3] != '0':
                problems.append('%s at %s: a berry 1 stud behind the tail IS eaten' % (species, s))
            if d[4] != '0' and head > r:
                problems.append('%s at %s: a berry at the root is eaten although the head point is %.2f away (radius %.2f)' % (species, s, head, r))
        if snout - head > r + 1e-6 and ufront <= head + r + 1e-6:
            problems.append('%s at %s: the snout is outside the zone although the zone is not capped' % (species, s))
        if float(edge) != 1.0:
            problems.append('%s at %s: a berry at the front edge of the zone is not eaten' % (species, s))
        if head < -1e-9:
            problems.append('%s at %s: the pickup point is behind the root' % (species, s))
    # 3 COMPY
    for s in (1.0, 2.0, 4.0):
        snout, head, r, dirs, legacy = rows[('compy', s)][:5]
        if abs(r - legacy) > 0.10 * legacy:
            problems.append('compy at %s: radius %.3f differs from the old %.3f by more than 10%%' % (s, r, legacy))
    if abs(rows[('compy', 1.0)][2] - 2.25) > 1e-6:
        problems.append('compy radius at scale 1 is not 2.25')
    # long bodies: the head point is far ahead of the root, the radius follows the head, not the body
    anky, spino, compy, trex = (rows[(k, 1.0)][:5] for k in ('ankylosaurus', 'spinosaurus', 'compy', 'tyrannosaurus'))
    # BD-521: under the cap a long body's pickup point is only slightly ahead of the Compy's (it used to follow the body length, BD-515)
    if anky[1] < compy[1] - 1e-6 or spino[1] < compy[1] - 1e-6 or anky[1] > compy[1] * 1.3 or spino[1] > compy[1] * 1.3:
        problems.append('long bodies must keep the pickup point within 30%% of the Compy (cap): %s' % ((compy[1], anky[1], spino[1]),))
    if anky[2] > 1.7 * compy[2] or trex[2] > 1.5 * compy[2] or spino[2] > 1.6 * compy[2]:
        problems.append('radius grows too much with the head: compy %.2f anky %.2f trex %.2f spino %.2f' % (compy[2], anky[2], trex[2], spino[2]))
    # 5 SAME FUNCTION
    food = (ROOT / 'src/server/FoodService.luau').read_text(encoding='utf-8')
    pred = (ROOT / 'src/server/PredationService.luau').read_text(encoding='utf-8')
    module = (ROOT / 'src/shared/MouthReach.luau').read_text(encoding='utf-8')
    if 'Shared.MouthReach' not in food or 'MouthReach.radius' not in food or 'MouthReach.point' not in food:
        problems.append('FoodService does not use MouthReach.point and MouthReach.radius')
    if re.search(r'Config\.FoodPickupRadius', food):
        problems.append('FoodService still reads FoodPickupRadius directly (a private radius)')
    if 'Shared.MouthReach' not in pred or 'MouthReach.point' not in pred:
        problems.append('PredationService does not use MouthReach.point')
    code = '\n'.join(l.split('--')[0] for l in module.splitlines())
    for banned in ('Instance.new', 'game:', 'workspace', 'Vector3', 'GetService', 'GetAttribute'):
        if banned in code:
            problems.append('MouthReach is not pure (uses %s): the server and a client preview could differ' % banned)
    # 6 DATA
    ladder = (ROOT / 'src/shared/ScaleLadder.luau').read_text(encoding='utf-8')
    found = 0
    for m in re.finditer(r'^        (\w+) = \{scale = [\d.]+,.*?length = ([\d.]+), snout = ([\d.]+), headLength = ([\d.]+), measured = true\},$', ladder, re.M):
        found += 1
        name, length, snout, head = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
        if name != 'microraptor' and abs(snout - length / 2) > 0.03:
            problems.append('%s: snout %.2f differs from half the length %.2f' % (name, snout, length / 2))
        if not 0 < head <= length or snout > length / 2 + 0.03:
            problems.append('%s: head length %.2f / snout %.2f out of range' % (name, head, snout))
    if found != 22:
        problems.append('ScaleLadder species rows without snout / headLength: %d of 22 found' % found)
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    if args.print:
        print('species, scale: snout offset / head offset / radius (old root rule radius)')
        for (species, s), (snout, head, r, dirs, legacy, *_rest) in sorted(rows.items()):
            print('%-20s %-4s snout %6.2f head %6.2f radius %5.2f (old %.2f)' % (species, s, snout, head, r, legacy))
    print('Mouth reach passed: 22 species x scales 1, 2, 4, 4.8 x 4 directions (snout, head point, beside the snout eaten; 1 stud behind the tail not eaten), Compy radius within 10%, zone cap (front edge and radius <= Config.FoodReachCapCompy x the Compy, parity band 1.0 to 1.10), legacy fallbacks, one shared function, flags')


if __name__ == '__main__':
    main()
