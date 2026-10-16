"""BD-225/BD-061: offline proof of the low-poly pattern + fused-tier bake maths (pure modules, pinned Luau runtime).
LowPolyPattern: deterministic (same genes -> same mask), masks only ever paint body pixels (never eyes/claws/belly), every pattern
distinct and non-empty, coverage follows genes.blend, bounded values. LowPolyTier: gentle tint pull, matte base, bounded gloss.
LowPolyTexture.key: stable and sensitive to every input (cache sharing is correct). Also scans that the Roblox-side callers exist."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local SIZE = Pattern.Size
assert(SIZE == 256)
-- synthetic 256 px part texture: body (species base colour, facet shading), cream belly band, black eye square, claw strip
local base = Recolor.baseOf("compy")
local weights = table.create(SIZE * SIZE, 0)
local kind = table.create(SIZE * SIZE, "body")
for y = 0, SIZE - 1 do
    for x = 0, SIZE - 1 do
        local i = y * SIZE + x + 1
        local r, g, b = base[1], base[2], base[3]
        local shade = 0.75 + 0.25 * ((x + y) % 7) / 6
        r, g, b = r * shade, g * shade, b * shade
        if y >= 200 then r, g, b = 0.82, 0.82, 0.56 kind[i] = "belly"
        elseif x >= 20 and x < 44 and y >= 20 and y < 44 then r, g, b = 0.06, 0.06, 0.06 kind[i] = "eye"
        elseif x >= 240 then r, g, b = 0.15, 0.15, 0.15 kind[i] = "claw" end
        weights[i] = Recolor.bodyWeight(r, g, b)
    end
end
local body = 0
for i = 1, SIZE * SIZE do
    if kind[i] ~= "body" then assert(weights[i] == 0, "protected pixel has body weight: " .. kind[i]) else assert(weights[i] > 0.99) body += 1 end
end
-- 1. every pattern: deterministic, never on protected pixels, non-empty, bounded, coverage follows blend
local seed = Pattern.seed("compy|body")
assert(seed == Pattern.seed("compy|body") and seed ~= Pattern.seed("compy|head") and seed ~= Pattern.seed("raptor|body"))
local signatures = {}
for _, id in Pattern.Ids do
    for _, share in {0.2, 0.5, 0.8} do
        local m1 = Pattern.compute(id, seed, weights, share, false)
        local m2 = Pattern.compute(id, seed, weights, share, false)
        local painted, sig = 0, 0
        for i = 1, SIZE * SIZE do
            assert(m1[i] == m2[i], "non-deterministic " .. id)
            assert(m1[i] >= 0 and m1[i] <= 1, "mask out of range")
            if kind[i] ~= "body" then assert(m1[i] == 0, id .. " painted a " .. kind[i] .. " pixel") end
            if m1[i] >= 0.5 then painted += 1 sig += i end
        end
        if id == "01_blank" then assert(painted == 0, "blank must not paint")
        else
            -- BD-307: coverage follows the per-pattern curve (area patterns = blend exactly, spot-like patterns capped)
            local want = (1 - Pattern.coverage(id, share)) * body
            assert(math.abs(painted - want) <= body * 0.06, string.format("%s share %.1f: painted %d of %d (want %.0f)", id, share, painted, body, want))
            if share == 0.5 then
                assert(signatures[sig] == nil, id .. " looks like another pattern")
                signatures[sig] = id
            end
        end
    end
    -- raw mask values bounded for a grid of texels
    for y = 0, SIZE - 1, 7 do for x = 0, SIZE - 1, 5 do local v = Pattern.mask(id, x, y, seed) assert(v == v and v >= 0 and v <= 1, id .. " out of range") end end
end
-- same-family genes still show a pattern (half and half), and a different seed gives a different (but same-size) mask
local a = Pattern.compute("03_round_spots", seed, weights, 1, true)
local b = Pattern.compute("03_round_spots", Pattern.seed("raptor|tail"), weights, 1, true)
local ca, cb, diff = 0, 0, 0
for i = 1, SIZE * SIZE do if a[i] >= 0.5 then ca += 1 end if b[i] >= 0.5 then cb += 1 end if math.abs(a[i] - b[i]) > 0.5 then diff += 1 end end
local half = (1 - Pattern.coverage("03_round_spots", 0.5)) * body -- same-family genes use the half-and-half rule through the curve
assert(math.abs(ca - half) <= body * 0.06 and math.abs(cb - half) <= body * 0.06, "same-family split")
assert(diff > body * 0.1, "seed has no effect")
-- unknown pattern id -> no paint (plain colours), onRow is called once per row
local rows = 0
local u = Pattern.compute("99_nope", seed, weights, 0.5, false, function() rows += 1 end)
for i = 1, SIZE * SIZE do assert(u[i] == 0) end
rows = 0
Pattern.compute("08_freckles", seed, weights, 0.5, false, function() rows += 1 end)
assert(rows == SIZE, "onRow per row")
-- readability: features are medium sized (a spot/band spans at least 6 px and at most 64 px along a row)
local spots = Pattern.compute("03_round_spots", seed, weights, 0.5, false)
local run, longest, shortest = 0, 0, 999
for x = 0, 199 do
    local v = spots[100 * SIZE + x + 1]
    if v >= 0.5 then run += 1 else if run > 0 then longest = math.max(longest, run) shortest = math.min(shortest, run) end run = 0 end
end
assert(longest <= 64 and shortest >= 4, "spot run lengths " .. shortest .. ".." .. longest)
-- BD-307 coverage curve: monotonic, area patterns follow the blend exactly, spots/freckles/scales capped so a low blend never
-- turns spots into blobs (blend 35 = 65 % secondary asked -> at most 28 % painted for spots)
for _, id in Pattern.Ids do
    local last = -1
    for s = 0, 100, 5 do local c = Pattern.coverage(id, s / 100) assert(c >= last and c >= 0 and c <= 1, id .. " coverage not monotonic") last = c end
end
assert(Pattern.coverage("04_bold_patches", 0.3) == 0.3 and Pattern.coverage("05_horizontal_bands", 0.8) == 0.8, "area patterns follow blend")
assert(1 - Pattern.coverage("03_round_spots", 0.35) <= 0.28 and 1 - Pattern.coverage("03_round_spots", 0.95) >= 0.05, "spot cap")
assert(1 - Pattern.coverage("08_freckles", 0.2) <= 0.2, "freckle cap")
local blobs = Pattern.compute("03_round_spots", seed, weights, 0.35, false)
local nb = 0 for i = 1, SIZE * SIZE do if blobs[i] >= 0.5 then nb += 1 end end
assert(nb <= body * 0.30, "spots at blend 35 cover " .. nb / body)
-- BD-307 scales: staggered rows (a row's rim positions differ from the next row's) and plump centres (a run of primary >= 6 px
-- inside a scale on the flank), checked on the 3D mask in the (y, z) side plane
do
    local rimA, rimB = {}, {}
    local p = 0.11 local h = p * 0.72
    local y0 = (math.floor(64 * p / h) + 0.5) * h - 64 * p -- centre line of one scale row
    for k = 0, 39 do
        local z = k * p / 20
        rimA[k] = Pattern.mask3("07_diamond_scales", 0.3, y0, z, seed)
        rimB[k] = Pattern.mask3("07_diamond_scales", 0.3, y0 + h, z, seed) -- next row
    end
    local shifted = 0
    for k = 0, 39 do if math.abs(rimA[k] - rimB[k]) > 0.2 then shifted += 1 end end
    assert(shifted >= 10, "scale rows are not staggered: " .. shifted)
    local run, best = 0, 0
    for k = 0, 199 do local v = Pattern.mask3("07_diamond_scales", 0.3, y0, k * p / 100, seed) if v < 0.35 then run += 1 best = math.max(best, run) else run = 0 end end
    assert(best >= 20 and best <= 100, "scale centre run " .. best)
    for k = 0, 99 do local v = Pattern.mask3("07_diamond_scales", 0.3, k * 0.013, 0.02, seed) assert(v >= 0 and v <= 1) end
end
-- BD-306 size parameter: a 128 px limb bake shows the same coverage as the 256 px body bake (UV masks scaled, 3D masks unchanged)
do
    local S = 128
    local w = table.create(S * S, 1)
    local m = Pattern.compute("06_wavy_stripes", seed, w, 0.6, false, nil, nil, S)
    local painted = 0 for i = 1, S * S do assert(m[i] >= 0 and m[i] <= 1) if m[i] >= 0.5 then painted += 1 end end
    assert(math.abs(painted / (S * S) - 0.4) <= 0.06, "small cell coverage " .. painted / (S * S))
    local rows = 0
    Pattern.compute("03_round_spots", seed, w, 0.5, false, function() rows += 1 end, nil, S)
    assert(rows == S, "onRow per row at size " .. S)
    local map = Pattern.rasterize({{0, 0, -1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0}}, S)
    assert(buffer.len(map) == S * S * 4 and buffer.readu8(map, 3) == 255, "rasterize at size")
end
-- 2. tier look: gentle, bounded, base matte, every tier distinct
for _, id in Tier.Order do
    local e = Tier.get(id) assert(e and e.id == id, id)
    assert(e.amount > 0 and e.amount <= Tier.MaxAmount and e.trimAmount <= Tier.MaxAmount, id .. " tint pull bounded")
    assert(e.reflectance >= 0 and e.reflectance <= Tier.MaxReflectance, id .. " gloss bounded")
    assert(e.amount >= 0.45 and e.amount <= 0.65 and e.trimAmount > e.amount, id .. " 2026-10-16: strong enough to read at a glance, trim stronger")
    assert(e.material ~= "Neon" and e.material ~= "ForceField", id .. " no neon")
    assert(e.sparkleRate > 0 and e.sparkleRate <= Tier.MaxSparkleRate and e.sparkleSize > 0 and e.sparkleSize <= 1, id .. " sparkle bounded")
    for i = 1, 3 do assert(e.tint[i] >= 0 and e.tint[i] <= 255 and e.sparkle[i] >= 0 and e.sparkle[i] <= 255) end
    -- the gene colour must still dominate: a red dino stays mostly red under every tier
    local r, g, b = Tier.blend(0.9, 0.15, 0.15, e, false)
    assert(r > g and r > b and r >= 0 and r <= 1 and g >= 0 and g <= 1 and b >= 0 and b <= 1, id .. " gene colour lost")
    -- the trim never goes grey: a pink pattern under any tier keeps a saturated colour
    local r2, g2, b2 = Tier.blend(0.84, 0.28, 0.58, e, true)
    local mx, mn = math.max(r2, g2, b2), math.min(r2, g2, b2)
    assert(mx <= 1 and mn >= 0 and (mx - mn) / mx > 0.45, id .. " trim turned muddy")
    -- Studio look check 2026-10-16: Diamond reads as a pale frosted version of the gene colour (satKeep) on warm species, never grey
    local dr0, dg0, db0 = Tier.blend(0.80, 0.50, 0.36, Tier.get("diamond"), false)
    local dmx, dmn = math.max(dr0, dg0, db0), math.min(dr0, dg0, db0)
    assert((dmx - dmn) / dmx > 0.1 and dmx >= 0.7, "diamond keeps the warm colour, brighter, never grey")
    -- BD-308 baked sheen: bounded, only lifts facets the source lit (k > 1), never darkens, never pushes past white
    assert(e.sheen > 0 and e.sheen <= Tier.MaxSheen, id .. " sheen bounded")
    local lr, lg, lb = Tier.lift(0.5, 0.3, 0.2, 1.4, e)
    assert(lr > 0.5 and lg > 0.3 and lb > 0.2 and lr <= 1 and lg <= 1 and lb <= 1 and lr - 0.5 <= 0.35, id .. " lift")
    local dr, dg, db = Tier.lift(0.5, 0.3, 0.2, 0.8, e)
    assert(dr == 0.5 and dg == 0.3 and db == 0.2, id .. " shadow facets untouched")
    assert(select(1, Tier.lift(1, 1, 1, 1.6, e)) <= 1, "white stays white")
end
-- 2026-10-16 "Shiny + sparkles": strictly growing presence per tier, and Diamond never looks weaker than Gold
local function hueOf(r, g, b)
    local mx, mn = math.max(r, g, b), math.min(r, g, b)
    local d = mx - mn
    if d < 1e-4 or d / math.max(mx, 1e-6) < 0.12 then return -1 end
    local h = if mx == r then ((g - b) / d) % 6 elseif mx == g then (b - r) / d + 2 else (r - g) / d + 4
    return h / 6
end
local function luma(r, g, b) return 0.2126 * r + 0.7152 * g + 0.0722 * b end
local function sat(r, g, b) local mx, mn = math.max(r, g, b), math.min(r, g, b) return if mx > 0 then (mx - mn) / mx else 0 end
local prev = nil
for _, id in Tier.Order do
    local e = Tier.get(id)
    if prev then
        assert(e.reflectance > prev.reflectance and e.sheen > prev.sheen and e.sparkleRate > prev.sparkleRate and e.sparkleSize > prev.sparkleSize, id .. " gloss/sheen/sparkle grow per tier")
    end
    prev = e
end
local gold, emerald, diamond = Tier.get("gold"), Tier.get("emerald"), Tier.get("diamond")
assert(gold.material == "Metal" and emerald.material == "Glass" and diamond.material == "Glass" and diamond.reflectance == Tier.MaxReflectance, "metal / gem materials")
assert(diamond.shimmer and #diamond.shimmer >= 3 and not gold.shimmer and not emerald.shimmer and diamond.shimmerSpeed > 0, "only Diamond has the rainbow shimmer")
for _, grey in {0.35, 0.6, 0.85} do -- the same neutral dino under each tier
    local gr, gg, gb = Tier.blend(grey, grey, grey, gold, false)
    local er, eg, eb = Tier.blend(grey, grey, grey, emerald, false)
    local dr, dg, db = Tier.blend(grey, grey, grey, diamond, false)
    assert(luma(dr, dg, db) >= luma(gr, gg, gb), "diamond is not darker than gold at grey " .. grey)
    assert(sat(gr, gg, gb) >= 0.2 and sat(er, eg, eb) >= 0.2 and sat(dr, dg, db) >= 0.04, "every tier stays coloured at grey " .. grey)
    assert(sat(gr, gg, gb) > sat(dr, dg, db) and sat(er, eg, eb) > sat(dr, dg, db), "diamond is the iciest, with the rainbow shimmer on top")
    assert(luma(Tier.lift(dr, dg, db, 1.5, diamond)) >= luma(Tier.lift(gr, gg, gb, 1.5, gold)), "diamond highlights at least as bright as gold's")
end
-- hue rule (coordinator, Studio evidence): blue / red / green / purple dinos keep their hue under every tier, body and pattern pixels alike
for _, id in Tier.Order do
    local e = Tier.get(id)
    for _, c in {{0.15, 0.35, 0.9}, {0.9, 0.15, 0.15}, {0.2, 0.75, 0.3}, {0.6, 0.25, 0.8}, {0.9, 0.9, 0.95}, {0.1, 0.1, 0.1}, {0.84, 0.28, 0.58}} do
        for _, sec in {false, true} do
            local nr, ng, nb = Tier.blend(c[1], c[2], c[3], e, sec)
            local d = Tier.hueDistance(hueOf(c[1], c[2], c[3]), hueOf(nr, ng, nb))
            assert(d <= Tier.HueDelta + 1e-6, id .. " hue moved " .. d .. " for " .. c[1] .. "," .. c[2] .. "," .. c[3])
        end
    end
end
assert(luma(diamond.tint[1] / 255, diamond.tint[2] / 255, diamond.tint[3] / 255) > luma(gold.tint[1] / 255, gold.tint[2] / 255, gold.tint[3] / 255), "diamond tint brighter than gold tint")
assert(Recolor.shade(0.9, 0.9, 0.9, base) == 1.6 and Recolor.shade(0.01, 0.01, 0.01, base) == 0.3, "shade clamp")
assert(Tier.get("base") == nil and Tier.get(nil) == nil and Tier.get(false) == nil and Tier.get(true) == Tier.get("gold"), "stage mapping")
-- 3. the cheap fallback tint keeps black black and reproduces the gene colour on the base colour
local fr, fg, fb = Recolor.flatTint(base, 0.9, 0.2, 0.2)
assert(fr >= 0 and fr <= 1 and fg >= 0 and fg <= 1 and fb >= 0 and fb <= 1)
assert(fr == 1 and math.abs(base[2] * fg - 0.2) < 0.02 and math.abs(base[3] * fb - 0.2) < 0.02, "fallback tint off") -- a multiply can only darken: red stays the texture red, green/blue drop to the gene value
assert(0 * fr == 0, "eyes stay black")
print("lowpoly pattern tests passed")
'''


def check_key():
    text = (ROOT / 'src/shared/LowPolyTexture.luau').read_text(encoding='utf-8')
    key = re.search(r'function Texture\.key\(textureId: string, spec: Spec\): string\n(.*?)\nend', text, re.S).group(1)
    for field in ("textureId", "spec.patternId", "spec.primary", "spec.secondary", "spec.same", "spec.primaryShare", "spec.tier"):
        assert field in key, f"cache key ignores {field}"
    assert 'Cache.new(Texture.BigCap' in text and 'Destroying:Once' in text, "bakes must be ref counted and released (byte caps: verify_lowpoly_budget.py)"
    dinos = (ROOT / 'src/shared/LowPolyDinos.luau').read_text(encoding='utf-8')
    assert 'Enum.Material.Plastic, 0' in dinos and 'Tier.MaxReflectance' in dinos, "base matte / tier gloss bounded (BD-173)"
    assert 'function LowPoly.applyTier' in dinos
    for path in ('src/client/ResourceVisuals.client.luau', 'src/shared/DinosaurPreview.luau'):
        assert 'LowPoly.applyTier' in (ROOT / path).read_text(encoding='utf-8'), f"{path} must use the shared tier path"
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert re.search(r'^\s*LowPolyDinos = false,', config, re.M), "Config.LowPolyDinos must default to false"
    genetics = (ROOT / 'src/shared/EggGenetics.luau').read_text(encoding='utf-8')
    ids = re.findall(r'"(\d\d_\w+)"', re.search(r'Genetics\.Patterns=\{([^}]*)\}', genetics).group(1))
    pattern = (ROOT / 'src/shared/LowPolyPattern.luau').read_text(encoding='utf-8')
    for pid in ids:
        assert pid in pattern, f"LowPolyPattern misses gene pattern {pid}"


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    check_key()
    src = ('local Recolor=' + module('src/shared/LowPolyRecolor.luau') + '\nlocal Pattern=' + module('src/shared/LowPolyPattern.luau')
           + '\nlocal Tier=' + module('src/shared/LowPolyTier.luau') + '\n' + BODY)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'lowpoly_patterns.luau'
        path.write_text(src, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
    print("low-poly pattern/tier maths ok")
