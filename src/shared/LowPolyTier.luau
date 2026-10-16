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
    sheen: number,         -- BD-308: 0..MaxSheen lift of the facets the source texture already lit (reads as gloss in flat light)
}
Tier.Order = {"gold", "emerald", "diamond"}
Tier.MaxAmount = 0.8
Tier.MaxReflectance = 0.3
Tier.MaxSheen = 0.7
Tier.Entries = {
    gold = {id = "gold", name = "Gold", tint = {255, 206, 92}, amount = 0.22, trimAmount = 0.75, material = "Metal", reflectance = 0.14,
        sparkle = {255, 230, 150}, sparkleRate = 1.5, sheen = 0.45},
    emerald = {id = "emerald", name = "Emerald", tint = {60, 220, 140}, amount = 0.20, trimAmount = 0.75, material = "Glass", reflectance = 0.10,
        sparkle = {170, 255, 205}, sparkleRate = 2, sheen = 0.35},
    diamond = {id = "diamond", name = "Diamond", tint = {215, 244, 255}, amount = 0.26, trimAmount = 0.70, material = "Glass", reflectance = 0.22,
        sparkle = {235, 250, 255}, sparkleRate = 3, sheen = 0.6},
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
function Tier.blend(r: number, g: number, b: number, entry: Entry, secondary: boolean): (number, number, number)
    local a = math.clamp(if secondary then entry.trimAmount else entry.amount, 0, Tier.MaxAmount)
    local t = entry.tint
    local nr, ng, nb = r + (t[1] / 255 - r) * a, g + (t[2] / 255 - g) * a, b + (t[3] / 255 - b) * a
    local mx, mn = math.max(r, g, b), math.min(r, g, b)
    local sat = if mx > 0 then (mx - mn) / mx else 0
    local nmx, nmn = math.max(nr, ng, nb), math.min(nr, ng, nb)
    local nsat = if nmx > 0 then (nmx - nmn) / nmx else 0
    local want = math.min(sat, 0.85)
    if nsat < want and nmx > 0 then -- re-saturate around the new max channel
        local k = (1 - want) * nmx
        local scale = (nmx - k) / math.max(nmx - nmn, 1e-6)
        nr, ng, nb = k + (nr - nmn) * scale, k + (ng - nmn) * scale, k + (nb - nmn) * scale
    end
    return math.clamp(nr, 0, 1), math.clamp(ng, 0, 1), math.clamp(nb, 0, 1)
end
return Tier
