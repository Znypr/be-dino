--!strict
-- BD-433 (docs/123 s2 T6, docs/87 calm): the 1.5 s rim light on the player's OWN dino when a mutation is revealed or hatched. Pure rules, no
-- Roblox services, verified offline (tools/verify_fx_moments.py); client/MomentRim.luau draws it.
--   * ONE Highlight, in the mutation's rim colour (or the fused tier's tint, or a warm default), fading in and out over Life seconds.
--   * Never stacked on the fused-tier rim: a dino that already wears a tier rim (Highlight "LPTierRim") gets THAT one brightened for the same
--     time instead, and put back exactly afterwards (no second Highlight, so the 31-Highlight engine cap is never pressured twice).
--   * Effects Full: outline + soft fill. Lite: outline only, fainter, a gentler brighten. Off: nothing at all.
--   * Reduce Motion: nothing pulses. A new rim holds still for Life seconds at the Lite look (switches on and off, no fade), and an existing
--     tier rim is left alone.
--   * The budget is EffectsLod.RimHighlights / RimHighlightHardCap (EffectsLod.rimFits), checked by the client against the Highlights alive.
local P = {}

P.Life = 1.5 -- seconds the moment lasts, in and out included
P.FadeIn = 0.25
P.FadeOut = 0.6
P.Name = "MomentRim" -- the Highlight this module owns
P.TierRimName = "LPTierRim" -- the fused-tier rim (LowPolyDinos); never touched except for the brighten
P.Gap = 1.5 -- seconds between two moments on one client (a repeat inside it is ignored)
P.DefaultColour = table.freeze({255, 236, 170}) -- warm, when neither a mutation nor a tier gives a colour

-- Transparencies (0 = solid): outline and fill of a NEW rim at its peak; brighten = how much a tier rim's fill transparency drops at the peak,
-- whiten = how far its outline colour moves toward white (0..1).
P.Looks = table.freeze({
    full = table.freeze({outline = 0.1, fill = 0.82, brighten = 0.3, whiten = 0.5}),
    lite = table.freeze({outline = 0.4, fill = 1, brighten = 0.15, whiten = 0.3}),
})

export type Look = {outline: number, fill: number, brighten: number, whiten: number, still: boolean}

-- nil = no rim at all (Effects Off). An unknown level plays as Full. Reduce Motion: the Lite look held still, nothing brightens.
function P.look(effects: string, calm: boolean): Look?
    if effects == "off" then return nil end
    local base = if calm or effects == "lite" then P.Looks.lite else P.Looks.full
    return {outline = base.outline, fill = base.fill, brighten = if calm then 0 else base.brighten, whiten = if calm then 0 else base.whiten, still = calm}
end

-- What to do with this dino: "new" (add the one Highlight), "brighten" (a tier rim already exists) or "none".
function P.mode(effects: string, calm: boolean, hasTierRim: boolean): string
    local look = P.look(effects, calm)
    if not look then return "none" end
    if hasTierRim then return if look.brighten > 0 then "brighten" else "none" end
    return "new"
end

-- age (seconds) -> strength 0..1. Smooth in over FadeIn, hold, smooth out over the last FadeOut; `still` = a plain switch (1 until Life, then 0).
function P.envelope(age: number, still: boolean): number
    if age < 0 or age >= P.Life then return 0 end
    if still then return 1 end
    local up = math.clamp(age / P.FadeIn, 0, 1)
    local down = math.clamp((P.Life - age) / P.FadeOut, 0, 1)
    local u, d = up * up * (3 - 2 * up), down * down * (3 - 2 * down)
    return math.min(u, d)
end

-- Colour 0..255: the mutation's rim first, else the tier's tint, else the warm default. Callers pass the tables from MutationLook / LowPolyTier.
function P.colour(mutationRim: {number}?, tierTint: {number}?): {number}
    if mutationRim and #mutationRim >= 3 then return mutationRim end
    if tierTint and #tierTint >= 3 then return tierTint end
    return P.DefaultColour :: any
end

-- Transparencies of a NEW rim at strength e (0..1): fully clear at 0, the look's own values at 1.
function P.newTransparency(look: Look, e: number): (number, number)
    local k = math.clamp(e, 0, 1)
    return 1 - (1 - look.outline) * k, 1 - (1 - look.fill) * k
end

-- Fill transparency and outline whiten amount of an existing tier rim at strength e: base fill drops by brighten * e (never below 0).
function P.brightenFill(baseFill: number, look: Look, e: number): number
    return math.max(0, baseFill - look.brighten * math.clamp(e, 0, 1))
end
function P.brightenWhite(look: Look, e: number): number
    return look.whiten * math.clamp(e, 0, 1)
end

return P
