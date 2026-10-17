"""BD-515 (docs/115 MR1-MR3): offline verifier for "eating happens at the mouth", src/shared/MouthReach.luau.

It runs the REAL pure module in Luau (with the real Config and ScaleLadder) and fails when:
  1. MOUTH: for each of the 22 species at growth scale 1, 2, 4 (and the BIG 4.8), a berry at the snout tip, one at the head point and one beside
     the snout (half a radius to the side) are eaten, whatever the facing direction (four directions);
  2. TAIL: a berry 1 stud behind the tail tip is NOT eaten, and neither is one at the dino's root when the head point is more than a radius away;
  3. COMPY: the Compy zone (BD-522, docs/115 MR5): front edge = snout + SlackStuds, radius = half head x scale + RadiusPad, its snout inside the zone, the radius
     above half a walking step so a berry cannot be skipped between two 0.08 s ticks;
  4. LEGACY: no species (nil, unknown, junk scale or junk look vector) gives anything but the old root rule, 2.25 + 0.75 per scale, max 5;
  5. SAME FUNCTION: FoodService and PredationService require Shared/MouthReach (no private copy of the radius), the module sits in src/shared
     and uses no Instance / game API, so the server and any client preview run the same code; FoodService no longer reads FoodPickupRadius;
  6. DATA: ScaleLadder has snout and headLength for all 22 species (snout equals half the body length except where the head is not the front);
  7. FLAGS: Config.FoodPickupAtMouth is OFF (docs/115 MR6, until the BD-527 pace check; it only acts with LowPolyDinos) and Config.PredationAtMouth is off (predation change verified offline only).
  8. CAP (BD-521, docs/115 MR4): the zone (front edge ahead of the root, radius) never exceeds Config.FoodReachCapCompy x the Compy's at the same scale
     (checked at 6 scales for all 22 species), the Compy and every species under the cap keep the uncapped BD-515 zone, the head point is never behind the root,
     a berry at the zone's front edge is eaten, and the cap factor stays inside the parity band 1.0 to 1.10 (tools/simulate_food_reach.py measures food/min).
  9. PARITY (BD-522, docs/115 MR5): a fast analytic proxy, calibrated against tools/simulate_food_reach.py (food/min ratio = (front edge / old reach)^0.278 x
     (radius / old radius)^0.014 at the run's mean growth scale, no multi-minute sim): the shipped Compy zone must not lift food/min above the recorded limits
     (proxy values of the shipped zone +3 points: full +37%, half +33%, quarter +29%), must stay within 6 points of the lowest lift a zone can have while eating at the snout,
     and the proxy must still reproduce the simulated calibration points within 11 points (rms 3.7). Parity (+-3%) itself is NOT reachable with the snout rule: it needs
     a front edge of about 0.4 to 0.45 x the snout distance (the relaxed variant in docs/115 MR5 / BD-527).
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
for id in ScaleLadder.Dino.secret.species do ids[#ids + 1] = id end -- BD-606: the 7 secret species, same rules
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
    local row = ScaleLadder.dinoRow(id)
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
-- BD-522 parity proxy inputs: the Compy zone at the mean growth scale of a 300 s run at each pace (the simulated Build 020 food/min of tools/simulate_food_reach.py)
local function sbar(perMin)
    local total = 0
    for i = 0, 299 do total += math.sqrt(1 + perMin / 60 * (i + 0.5) * Config.GrowthPerFood / 50) end
    return total / 300
end
for _, pace in {{"full", 1090}, {"half", 580}, {"quarter", 279}} do
    local sb = sbar(pace[2])
    local off, r = M.zone("compy", sb)
    print(string.format("Z\t%s\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f", pace[1], sb, off + r, r, M.legacyRadius(sb), M.snoutOffset("compy", sb)))
end
print("SLACK\t" .. M.slack() .. "\t" .. tostring(M.RadiusPad) .. "\t" .. tostring(M.RadiusFactor) .. "\t" .. Config.WalkSpeed .. "\t" .. Config.FoodTickSeconds)
-- legacy fallbacks
local root = {x = 0, y = 0, z = 0}
local look = {x = 0, z = -1}
local function near(a, b) return math.abs(a - b) < 1e-9 end
for _, s in {1, 1.5, 2, 3, 4, 4.8, 9, -3} do
    local want = math.min(5, 2.25 + (math.clamp(s, 1, 6) - 1) * 0.75)
    assert(near(M.radius(nil, s), want) and near(M.radius("nonsense", s), want) and near(M.legacyRadius(s), want), "legacy radius at " .. s)
end
assert(near(M.radius("compy", 1), 0.825 * M.RadiusFactor + M.RadiusPad), "compy radius at scale 1 = half head + pad")
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


# BD-522 analytic proxy for the simulated food/min lift of a Compy zone over the Build 020 root rule (tools/simulate_food_reach.py, Compy, 48 layouts, 300 s):
#   lift = (front edge / old reach)^A x (radius / old radius)^B - 1, both evaluated at the mean growth scale of a run at that pace (Luau prints them).
# A and B are a least-squares fit of log(food ratio) over 20 zones x 3 paces (slack 0 to 1.425, pad 1 to 2.25, relaxed fronts 0.3 to 1.0 x the snout; rms 3.7 points).
# The forward reach carries it (A); the width hardly matters (B). It is a guard, not the measurement: the real check is the Studio LastRunFood log.
PROXY_A, PROXY_B = 0.278, 0.014
# (label, front = share x snout x scale + slack, slack, radius pad, simulated lift full / half / quarter)
CALIBRATION = (
    ('BD-515 zone (slack 1.425, pad 1.425)', 1.0, 1.425, 1.425, (0.409, 0.289, 0.419)),
    ('BD-522 zone (slack 0.25, pad 1.0)', 1.0, 0.25, 1.0, (0.357, 0.221, 0.320)),
    ('slack 0, pad 1.0', 1.0, 0.0, 1.0, (0.341, 0.212, 0.293)),
    ('relaxed front 0.5 x snout', 0.5, 0.0, 1.0, (0.087, 0.090, -0.007)),
    ('relaxed front 0.4 x snout', 0.4, 0.0, 1.0, (0.047, -0.007, -0.063)),
)
RECORDED_MAX_LIFT = {'full': 0.37, 'half': 0.33, 'quarter': 0.29}  # the proxy values of the shipped zone 34.2 / 30.1 / 25.9 plus 3 points (the simulation says 35.7 / 22.1 / 32.0)
PARITY_BAND = 0.03
CALIBRATION_TOLERANCE = 0.11  # the simulation itself has a standard error of 2 to 6 points per pace
FLOOR_MARGIN = 0.06
PACES = ('full', 'half', 'quarter')


def proxy_lift(front, radius, old):
    return (front / old) ** PROXY_A * (radius / old) ** PROXY_B - 1


def check_parity(zones, problems):
    """Fast offline parity assertions from the zone numbers Luau printed. Returns the report rows."""
    report = []
    if set(zones) != set(PACES):
        problems.append('parity proxy: Luau did not print the Compy zones (%s)' % sorted(zones))
        return report
    for pace in PACES:
        sb, front, radius, old, snout = zones[pace]
        lift = proxy_lift(front, radius, old)
        # the lowest lift a zone can have and still eat a berry at the snout tip: front edge = snout, same radius
        floor = proxy_lift(snout, radius, old)
        report.append((pace, sb, front, radius, old, snout, lift, floor))
        if lift > RECORDED_MAX_LIFT[pace]:
            problems.append('parity proxy %s pace: the Compy zone lifts food/min by %+.1f%% (limit %+.0f%%, docs/115 MR5): the mouth zone got bigger' % (pace, lift * 100, RECORDED_MAX_LIFT[pace] * 100))
        if front < snout - 1e-6:
            problems.append('parity proxy %s pace: the Compy front edge %.2f is behind the snout %.2f (the snout rule)' % (pace, front, snout))
        if lift - floor > FLOOR_MARGIN:
            problems.append('parity proxy %s pace: lift %+.1f%% is %.1f points above the snout-rule floor %+.1f%%: the zone reaches too far past the nose' % (pace, lift * 100, (lift - floor) * 100, floor * 100))
    # the proxy still reproduces the simulation it was calibrated on
    for label, share, slack, pad, simulated in CALIBRATION:
        for pace, sim in zip(PACES, simulated):
            sb, _front, _radius, old, snout = zones[pace]
            front, radius = share * snout + slack, 0.825 * sb + pad
            if abs(proxy_lift(front, radius, old) - sim) > CALIBRATION_TOLERANCE:
                problems.append('parity proxy drifted from the simulation for "%s" at %s pace: proxy %+.1f%% vs simulated %+.1f%%' % (label, pace, proxy_lift(front, radius, old) * 100, sim * 100))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--print', action='store_true')
    args = parser.parse_args()
    rows = {}
    flags = None
    capk = None
    zones = {}
    tune = None
    count = 0
    for line in run(args.runner):
        p = line.split('\t')
        if p[0] == 'R':
            rows[(p[1], float(p[2]))] = (float(p[3]), float(p[4]), float(p[5]), p[6].split(','), float(p[7]), float(p[8]), float(p[9]), float(p[10]), p[11])
        elif p[0] == 'FLAGS':
            flags = (p[1], p[2])
        elif p[0] == 'Z':
            zones[p[1]] = tuple(float(x) for x in p[2:])
        elif p[0] == 'SLACK':
            tune = tuple(float(x) for x in p[1:])
        elif p[0] == 'N':
            count = int(p[1])
        elif p[0] == 'CAPK':
            capk = None if p[1] == 'nil' else float(p[1])
    problems = []
    if count != 29:
        problems.append('expected 22 species + 7 secret species in ScaleLadder, found %d' % count)
    if capk is None or not 1.0 <= capk <= 1.10:
        problems.append('Config.FoodReachCapCompy is %s, expected a number in the parity band 1.0 to 1.10 (docs/115 MR4)' % (capk,))
    if flags != ('false', 'false'):
        problems.append('Config.FoodPickupAtMouth / PredationAtMouth are %s, expected false / false (docs/115 MR6: off until the BD-527 pace check)' % (flags,))
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
    # 3 COMPY (BD-522, MR5): the zone is front = snout + slack, radius = half head x scale + pad; no longer the old 2.25
    slack, pad, factor, walk, tick = tune
    cr = rows[('compy', 1.0)][2]
    if abs(cr - (0.825 * factor + pad)) > 0.05:
        problems.append('compy radius at scale 1 is %.3f, expected half head 0.825 x %.2f + pad %.2f' % (cr, factor, pad))
    for s_ in (1.0, 2.0, 4.0):
        csnout_s, chead_s, cr_s = rows[('compy', s_)][:3]
        if csnout_s > chead_s + cr_s + 1e-6:
            problems.append('compy at %s: the snout tip is outside the zone' % s_)
        if abs((chead_s + cr_s) - (csnout_s + slack)) > 1e-3:
            problems.append('compy at %s: the front edge is not snout + slack %.2f' % (s_, slack))
    if cr < walk * tick / 2 + 0.3:
        problems.append('compy radius %.2f is below half a walking step (%.2f): a berry could be skipped between two pickup ticks' % (cr, walk * tick / 2))
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
    # 9 PARITY proxy (BD-522)
    parity_rows = check_parity(zones, problems)
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    if args.print:
        print('species, scale: snout offset / head offset / radius (old root rule radius)')
        for (species, s), (snout, head, r, dirs, legacy, *_rest) in sorted(rows.items()):
            print('%-20s %-4s snout %6.2f head %6.2f radius %5.2f (old %.2f)' % (species, s, snout, head, r, legacy))
    print('Parity proxy (Compy, mouth zone vs Build 020 root rule, parity target +-%.0f%%):' % (PARITY_BAND * 100))
    for pace, sb, front, radius, old, snout, lift, floor in parity_rows:
        print('  %-8s mean growth %.2f: front edge %.2f (old reach %.2f, snout %.2f), radius %.2f: predicted lift %+.1f%% (snout-rule floor %+.1f%%) -> %s' % (
            pace, sb, front, old, snout, radius, lift * 100, floor * 100, 'PARITY' if abs(lift) <= PARITY_BAND else 'KNOWN GAP (snout rule)'))
    print('Mouth reach passed: 22 species + 7 secret species x scales 1, 2, 4, 4.8 x 4 directions (snout, head point, beside the snout eaten; 1 stud behind the tail not eaten), Compy zone = snout + 0.25 slack, half head + 1.0 radius, analytic food/min parity proxy (known gap, snout rule), zone cap (front edge and radius <= Config.FoodReachCapCompy x the Compy, parity band 1.0 to 1.10), legacy fallbacks, one shared function, flags')


if __name__ == '__main__':
    main()
