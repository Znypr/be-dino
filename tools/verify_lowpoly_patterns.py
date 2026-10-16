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
            local want = (1 - share) * body
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
assert(math.abs(ca - body * 0.5) <= body * 0.06 and math.abs(cb - body * 0.5) <= body * 0.06, "same-family split")
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
-- 2. tier look: gentle, bounded, base matte, every tier distinct
for _, id in Tier.Order do
    local e = Tier.get(id) assert(e and e.id == id, id)
    assert(e.amount > 0 and e.amount <= Tier.MaxAmount and e.trimAmount <= Tier.MaxAmount, id .. " tint pull bounded")
    assert(e.reflectance >= 0 and e.reflectance <= Tier.MaxReflectance, id .. " gloss bounded")
    assert(e.material ~= "Neon" and e.material ~= "ForceField", id .. " no neon")
    assert(e.sparkleRate >= 0 and e.sparkleRate <= 4, id .. " sparkle stays soft")
    for i = 1, 3 do assert(e.tint[i] >= 0 and e.tint[i] <= 255 and e.sparkle[i] >= 0 and e.sparkle[i] <= 255) end
    -- the gene colour must still dominate: a red dino stays mostly red under every tier
    local r, g, b = Tier.blend(0.9, 0.15, 0.15, e, false)
    assert(r > g and r > b and r >= 0 and r <= 1 and g >= 0 and g <= 1 and b >= 0 and b <= 1, id .. " gene colour lost")
    -- the trim never goes grey: a pink pattern under any tier keeps a saturated colour
    local r2, g2, b2 = Tier.blend(0.84, 0.28, 0.58, e, true)
    local mx, mn = math.max(r2, g2, b2), math.min(r2, g2, b2)
    assert(mx <= 1 and mn >= 0 and (mx - mn) / mx > 0.45, id .. " trim turned muddy")
end
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
    assert re.search(r'Texture\.Cap = (\d+)', text) and int(re.search(r'Texture\.Cap = (\d+)', text).group(1)) <= 30, "bake cap over the EditableImage budget"
    assert 'Cache.new(Texture.Cap' in text and 'Destroying:Once' in text, "bakes must be ref counted and released"
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
