"""BD-1038 / docs/186 s6: the pattern + colour boost (src/shared/GeneBoost.luau), proved with the REAL tables in Luau, plus the server wiring.
Covers: points per tier (Common 0, Uncommon 1, Rare 2, Epic 4, Legendary 6, Mythic 10), pattern + 0.7 x main colour + 1.0 x accent colour,
the two same-colour case, growth +1% a point capped at +15%, walking +0.5% a point capped at +7% (totals per dino), monotonic, a dino with
no genes or junk genes = exactly 1, the flag off = exactly 1, the version constant, and (static) that ProgressionService applies it from the
SERVER-held equipped genes behind Config.GeneBoostEnabled, which ships false. Mocks check numbers, not feel, Studio or a phone.
"""
from pathlib import Path
import argparse, re, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local function near(a, b, e) assert(math.abs(a - b) <= (e or 1e-9), tostring(a) .. " vs " .. tostring(b)) end
local P, C = PC.EggPatterns, PC.EggColors
local function genes(pattern, main, accent) return {patternId = pattern, primaryColorId = main, secondaryColorId = accent} end
local function pts(pattern, main, accent) return B.points(P, C, genes(pattern, main, accent)) end
assert(B.Version == "bd1038-geneboost-v1" and #B.Version > 0, "the formula has a version")
-- 1. Points per tier and the weights.
local want = {Common = 0, Uncommon = 1, Rare = 2, Epic = 4, Legendary = 6, Mythic = 10}
for tier, n in want do assert(B.TierPoints[Curve.index(tier) + 1] == n, tier) end
assert(B.MainColourWeight == 0.7 and B.AccentColourWeight == 1.0 and B.GrowthPerPoint == 0.01 and B.GrowthCap == 0.15 and B.WalkPerPoint == 0.005 and B.WalkCap == 0.07)
for _, row in P do assert(B.patternPoints(P, row.id) == want[row.rarity], row.id) end
for _, row in C do assert(B.colourPoints(C, row.id) == want[row.rarity], row.id) end
-- Real tables: Plain/Dots/Freckles 0, Patches/Bands 1, Waves 2, Islands 4, Diamonds 6; Cream/Blue 0, Green 1, Pink/Teal 2, Amber 4, Purple 6, Red/Black 10.
assert(B.patternPoints(P, "01_blank") == 0 and B.patternPoints(P, "04_bold_patches") == 1 and B.patternPoints(P, "06_wavy_stripes") == 2
    and B.patternPoints(P, "02_emerald_islands") == 4 and B.patternPoints(P, "07_diamond_scales") == 6)
-- 2. pattern + 0.7 main + 1.0 accent.
near(pts("01_blank", "white", "white"), 0)
near(pts("06_wavy_stripes", "green", "gold"), 2 + 0.7 * 1 + 1.0 * 4) -- 6.7
near(pts("07_diamond_scales", "red", "black"), 6 + 0.7 * 10 + 1.0 * 10) -- 23
assert(pts("01_blank", "white", "black") > pts("01_blank", "black", "white"), "an accent colour is worth more than the same main colour")
near(pts("01_blank", "white", "black"), 10) near(pts("01_blank", "black", "white"), 7)
-- 3. Same colour on both sides counts both (once as main, once as accent); a missing accent counts the same way.
near(pts("01_blank", "violet", "violet"), 1.7 * 6)
near(B.points(P, C, {patternId = "01_blank", primaryColorId = "violet"}), 1.7 * 6)
-- 4. Caps are totals for one dino.
near(B.growthMultiplier(0), 1) near(B.growthMultiplier(1), 1.01) near(B.growthMultiplier(6.7), 1.067) near(B.growthMultiplier(15), 1.15) near(B.growthMultiplier(1000), 1.15)
near(B.walkMultiplier(0), 1) near(B.walkMultiplier(1), 1.005) near(B.walkMultiplier(6.7), 1.0335) near(B.walkMultiplier(14), 1.07) near(B.walkMultiplier(1000), 1.07)
local best, bestWalk = 0, 0
for _, p in P do for _, a in C do for _, b in C do
    local g, w, n = B.multipliers(true, P, C, genes(p.id, a.id, b.id))
    assert(g >= 1 and g <= 1.15 + 1e-12 and w >= 1 and w <= 1.07 + 1e-12, "within the caps")
    best, bestWalk = math.max(best, g), math.max(bestWalk, w)
    assert(n == pts(p.id, a.id, b.id))
end end end
near(best, 1.15) near(bestWalk, 1.07) -- the best dino reaches both caps and nothing goes past them
-- 5. Monotonic: a rarer tier never lowers the points or either multiplier.
for _, p1 in P do for _, p2 in P do
    if B.patternPoints(P, p1.id) <= B.patternPoints(P, p2.id) then
        for _, a in C do for _, b in C do assert(pts(p1.id, a.id, b.id) <= pts(p2.id, a.id, b.id) + 1e-12) end end
    end
end end
for _, c1 in C do for _, c2 in C do
    if B.colourPoints(C, c1.id) <= B.colourPoints(C, c2.id) then
        for _, p in P do for _, o in C do
            assert(pts(p.id, c1.id, o.id) <= pts(p.id, c2.id, o.id) + 1e-12 and pts(p.id, o.id, c1.id) <= pts(p.id, o.id, c2.id) + 1e-12)
        end end
    end
end end
local lastG, lastW = 1, 1
for n = 0, 40 do
    local g, w = B.growthMultiplier(n * .5), B.walkMultiplier(n * .5)
    assert(g >= lastG and w >= lastW, "monotonic in the points") lastG, lastW = g, w
end
-- 6. A dino with no genes, junk genes or unknown ids = exactly 1.
do
    local g, w, n = B.multipliers(true, P, C, nil) assert(g == 1 and w == 1 and n == 0, "nil genes -> 1")
end
for _, junk in {{}, "x", 5, true, {patternId = 5, primaryColorId = {}, secondaryColorId = false}, genes("99_none", "nope", "nope")} do
    local g, w, n = B.multipliers(true, P, C, junk)
    assert(g == 1 and w == 1 and n == 0, "no genes -> 1")
end
assert(B.points(nil, nil, genes("07_diamond_scales", "red", "red")) == 0 and B.points(P, C, nil) == 0, "missing tables / genes -> 0")
assert(B.growthMultiplier(0 / 0) == 1 and B.walkMultiplier(-3) == 1 and B.growthMultiplier(nil :: any) == 1)
-- 7. The flag off = EXACTLY 1 (and 0 points), even for the best dino; only a literal true switches it on.
local top = genes("07_diamond_scales", "black", "red")
for _, off in {false, 0, "true", 1, {}} do
    local g, w, n = B.multipliers(off, P, C, top)
    assert(g == 1 and w == 1 and n == 0, "flag off -> exactly 1")
end
do local g, w, n = B.multipliers(nil, P, C, top) assert(g == 1 and w == 1 and n == 0, "flag unset -> exactly 1") end
local g, w, n = B.multipliers(true, P, C, top) assert(g > 1 and w > 1 and n > 0)
print(string.format("GeneBoost passed: points 0/1/2/4/6/10 per tier, pattern + 0.7 main + 1.0 accent, caps +15%% growth +7%% walk (best dino %.2f / %.2f), monotonic, no genes = 1, flag off = exactly 1",
    best, bestWalk))
'''


def script():
    return ('local Curve=' + module('src/shared/RarityCurve.luau') + '\n'
            'local PC=' + module('src/shared/ProgressionConfig.luau') + '\n'
            'local script={Parent={RarityCurve=Curve}}\nlocal require=function(x) return x end\n'
            'local B=' + module('src/shared/GeneBoost.luau') + '\n' + BODY)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_wiring():
    """Source-level wiring (Roblox services cannot run in plain Luau)."""
    config = read('src/shared/Config.luau')
    assert re.search(r'^\s*GeneBoostEnabled = false,', config, re.M), 'Config.GeneBoostEnabled must ship false'
    service = read('src/server/ProgressionService.luau')
    assert 'require(ReplicatedStorage.Shared.GeneBoost)' in service, 'the server module is used'
    assert 'GameConfig.GeneBoostEnabled~=true' in service, 'the boost reads nothing and is exactly 1 while the flag is off'
    assert 'GeneBoost.multipliers(true,Config.EggPatterns,Config.EggColors' in service, 'pattern and colour tables come from the config'
    assert 'player:GetAttribute("EquippedGenesJson")' in service, 'genes are the SERVER-held equipped genes'
    assert 'boostWalk' in service and 'GameConfig.WalkSpeed*classX*boostWalk' in service, 'walk speed is set on the server'
    assert 'growth*=if GameConfig.GeneBoostEnabled==true then boostGrowth else colourMultiplier' in service, 'growth: gene boost replaces BD-172, never stacks'
    mod = read('src/shared/GeneBoost.luau')
    assert 'HttpService' not in mod and 'game:GetService' not in mod, 'GeneBoost is pure'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    check_wiring()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'boost.luau'
        path.write_text(script(), encoding='utf-8')
        r = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
    print(r.stdout, end='')
    print(r.stderr, end='')
    if r.returncode == 0:
        print('Wiring passed: Config.GeneBoostEnabled ships false; ProgressionService applies the boost from the server-held genes behind the flag, replacing (not stacking with) the BD-172 colour bonus')
    raise SystemExit(r.returncode)
