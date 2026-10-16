--!strict
-- BD-061 / BD-173: the ONE look table for fused tiers (Gold, Emerald, Diamond) on the low-poly dinos. Pure data + maths
-- (no Roblox types; tools/verify_lowpoly_patterns.py) plus one small applier. docs/46: a tier is an ADDITIVE material
-- mask over the NEW output's own genes: the gene colours and pattern stay dominant (tint pull capped like MutationLook),
-- eyes/claws/belly are untouched, and only fused tiers get gloss/metal (base dinos stay matte Plastic, docs/87).
-- Kid-friendly, not garish: one soft sparkle emitter on the body (existing fx3 sparkle sheet WITH alpha), low rate, no Neon.
local Tier = {}
export type Entry = {
    id: string, name: string,
    tint: {number},        -- 0..255 colour the BODY pixels are pulled toward (belly/eyes never)
    amount: number,        -- 0..1 pull on primary-colour pixels
    trimAmount: number,    -- 0..1 pull on the pattern (secondary-colour) pixels: the "selective trim" of docs/46
    material: string,      -- Enum.Material name for body-colour parts
    reflectance: number,   -- 0..0.3
    sparkle: {number},     -- sparkle colour
    sparkleRate: number,   -- particles per second on the body part (0 = none) at dino size 3 studs; Reduce Motion -> 0
    satKeep: number?, gain: number?, satGain: number?, -- hue-safe brightness / saturation gain after the tint (docs/114)
    sheen: number,
    accent: {number}, accentAmount: number, -- tier metal / gem colour for horns, claws, frill and pattern pixels (body colour untouched)
    sparkleCount: number,  -- concurrent twinkles at normal size (rate = count / lifetime)
    sparkleSize: number,   -- relative size of one spark (grows per tier)
    shimmer: {{number}}?, shimmerSpeed: number?, -- Diamond only: rainbow colours the sparks cycle through (static colours under Reduce Motion)
            -- BD-308: 0..MaxSheen lift of the facets the source texture already lit (reads as gloss in flat light)
}
Tier.Order = {"gold", "emerald", "diamond"}
Tier.MaxAmount = 0.8
Tier.MaxSparkleRate = 10
Tier.MaxSparkleCount = 8
Tier.MaxAccentAmount = 0.95
Tier.AccentWords = {"claw", "toe", "horn", "spike", "frill", "crest", "tooth", "teeth", "nail"}
Tier.MaxReflectance = 0.3
Tier.MaxSheen = 0.7
Tier.Entries = {
    -- 2026-10-16 owner decision "Shiny + sparkles" (docs/115): tiers must read Base < Gold < Emerald < Diamond at a glance, in daylight AND the dim cave.
    -- Gold = rich warm gold, Emerald = deep jewel green, Diamond = icy white-blue with a rainbow shimmer. Gloss, sheen, sparkle rate and sparkle size all grow per tier.
    gold = {id = "gold", name = "Gold", tint = {255, 190, 30}, amount = 0.55, trimAmount = 0.8, material = "Metal", reflectance = 0.18,
        sparkle = {255, 232, 140}, sparkleRate = 2.5, sparkleCount = 3, sparkleSize = 1.2, accent = {255, 200, 30}, accentAmount = 0.9, sheen = 0.5, gain = 1.1, satGain = 1.2},
    emerald = {id = "emerald", name = "Emerald", tint = {16, 190, 96}, amount = 0.45, trimAmount = 0.8, material = "Glass", reflectance = 0.23,
        sparkle = {150, 255, 195}, sparkleRate = 4.2, sparkleCount = 5, sparkleSize = 1.4, accent = {10, 235, 120}, accentAmount = 0.9, sheen = 0.6, gain = 0.97, satGain = 1.25},
    diamond = {id = "diamond", name = "Diamond", tint = {205, 240, 255}, amount = 0.6, trimAmount = 0.8, material = "Glass", reflectance = 0.3,
        sparkle = {235, 250, 255}, sparkleRate = 5, sparkleCount = 7, sparkleSize = 1.6, accent = {225, 245, 255}, accentAmount = 0.92, sheen = 0.7, gain = 1.14, satGain = 0.9,
        shimmer = {{255, 170, 215}, {170, 220, 255}, {190, 255, 215}, {255, 245, 170}}, shimmerSpeed = 0.5},
}
-- BD-308 baked sheen: the generated textures carry flat facet shading (k = pixel luma / species body luma, 0.3..1.6). On a fused
-- tier the facets that the source already lit (k > 1) are lifted toward white by (k - 1) * sheen, so the gem/metal look reads
-- even under flat Edit-mode or viewport lighting where Metal/Glass reflectance barely shows. Base dinos never get it (matte).
function Tier.lift(r: number, g: number, b: number, k: number, entry: Entry): (number, number, number)
    local a = math.clamp((k - 1) * math.clamp(entry.sheen, 0, Tier.MaxSheen), 0, 0.35)
    if a <= 0 then return r, g, b end
    return r + (1 - r) * a, g + (1 - g) * a, b + (1 - b) * a
end
-- Accepts the stage strings used around the codebase ("gold", "emerald", "diamond", true = gold). "base"/nil/false -> nil.
function Tier.get(stage: any): Entry?
    if stage == true then stage = "gold" end
    if type(stage) ~= "string" then return nil end
    return (Tier.Entries :: any)[stage]
end
-- Pure: pull a 0..1 colour toward the tier tint. secondary=true is the pattern trim (strong pull: the pattern becomes the gem /
-- metal). The result keeps at least the colour's own saturation, so complementary mixes (pink toward emerald) never turn grey.
local function hueOf(r: number, g: number, b: number): number -- 0..1, -1 for greys
    local mx, mn = math.max(r, g, b), math.min(r, g, b)
    local d = mx - mn
    if d < 1e-4 or d / math.max(mx, 1e-6) < 0.12 then return -1 end
    local h = if mx == r then ((g - b) / d) % 6 elseif mx == g then (b - r) / d + 2 else (r - g) / d + 4
    return h / 6
end
Tier.HueDelta = 0.04 -- 2026-10-16: a coloured pixel's hue moves by at most ~14 degrees under any tier (blue stays blue, red stays red)
function Tier.hueDistance(h1: number, h2: number): number
    if h1 < 0 or h2 < 0 then return 0 end
    local d = math.abs(h1 - h2) % 1
    return math.min(d, 1 - d)
end
-- Pure: the tier identity on a 0..1 colour. 2026-10-16 owner rule: the dino keeps its OWN colours and pattern; the tier adds metal/gem
-- lustre. So the pull toward the tier tint is limited until the hue has moved no more than Tier.HueDelta (grey / near-neutral pixels
-- take the full tint, so neutral belly-less greys still read gold / green / icy), then a brightness and saturation "gain" makes the facets glow.
function Tier.blend(r: number, g: number, b: number, entry: Entry, secondary: boolean): (number, number, number)
    local full = math.clamp(if secondary then entry.trimAmount else entry.amount, 0, Tier.MaxAmount)
    local t = entry.tint
    local h0 = hueOf(r, g, b)
    local sat0 = if math.max(r, g, b) > 0 then (math.max(r, g, b) - math.min(r, g, b)) / math.max(r, g, b) else 0
    local nr, ng, nb = r, g, b
    for _, f in {1, 0.75, 0.5, 0.35, 0.25, 0.15, 0.08, 0} do
        local a = full * f
        nr, ng, nb = r + (t[1] / 255 - r) * a, g + (t[2] / 255 - g) * a, b + (t[3] / 255 - b) * a
        local nmx, nmn = math.max(nr, ng, nb), math.min(nr, ng, nb)
        local keepsColour = h0 < 0 or (nmx > 0 and (nmx - nmn) / nmx >= 0.75 * sat0) -- never wash a coloured pixel out to white / grey
        if keepsColour and Tier.hueDistance(h0, hueOf(nr, ng, nb)) <= Tier.HueDelta then break end
    end
    -- gain: lift the lustre without changing hue (scale about the max channel for sat, then multiply for brightness)
    local gain, satGain = entry.gain or 1, entry.satGain or 1
    local mx, mn = math.max(nr, ng, nb), math.min(nr, ng, nb)
    if mx > 0 then
        local sat = math.clamp(((mx - mn) / mx) * satGain, 0, 1)
        local k = (1 - sat) * mx
        local scale = if mx - mn > 1e-6 then (mx - k) / (mx - mn) else 1
        nr, ng, nb = k + (nr - mn) * scale, k + (ng - mn) * scale, k + (nb - mn) * scale
    end
    return math.clamp(nr * gain, 0, 1), math.clamp(ng * gain, 0, 1), math.clamp(nb * gain, 0, 1)
end
-- Pure: tier accent (horns, frill, claws, pattern-secondary pixels): the tier's metal / gem colour, lit by the source facet shade k.
-- u (0..1, position across the texture) walks Diamond's prismatic list so the accents shift icy pink / blue / mint / gold.
function Tier.accent(r: number, g: number, b: number, entry: Entry, k: number, u: number?): (number, number, number)
    local c = entry.accent
    local ar, ag, ab = c[1] / 255, c[2] / 255, c[3] / 255
    local sh = entry.shimmer
    if sh and u then
        local f = (u % 1) * #sh
        local i = math.floor(f)
        local a, bb = sh[i % #sh + 1], sh[(i + 1) % #sh + 1]
        local t = f - i
        -- icy base pulled toward the prismatic colour: still the lightest tier, but clearly not plain white
        ar, ag, ab = ar * 0.55 + (a[1] + (bb[1] - a[1]) * t) / 255 * 0.45, ag * 0.55 + (a[2] + (bb[2] - a[2]) * t) / 255 * 0.45, ab * 0.55 + (a[3] + (bb[3] - a[3]) * t) / 255 * 0.45
    end
    local shade = math.clamp(0.8 + (k - 1) * 0.6, 0.65, 1.2)
    local m = math.clamp(entry.accentAmount, 0, Tier.MaxAccentAmount)
    return math.clamp(r + (ar * shade - r) * m, 0, 1), math.clamp(g + (ag * shade - g) * m, 0, 1), math.clamp(b + (ab * shade - b) * m, 0, 1)
end
function Tier.isAccentName(name: string): boolean
    local n = string.lower(name)
    for _, w in Tier.AccentWords do if string.find(n, w, 1, true) then return true end end
    return false
end
return Tier
