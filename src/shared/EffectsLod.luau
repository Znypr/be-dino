--!strict
-- Distance LOD for cosmetic effects (BD-095, docs/93, docs/103). Pure rules, no Roblox services: CosmeticVisuals asks
-- "how detailed should this dino's aura/trail be at this distance?" and the Effects setting (Full / Lite / Off) lowers the answer.
-- Detail is "full" | "lite" | "none". Off still keeps the event-mutation cue (kind "mutation") so players can read it.
local Lod = {}

-- Studs from the camera. Lite and Off shrink the bands so phones draw less.
Lod.FullRange = 25 -- only Full mode, nearest dinos, get the full layer count
Lod.CullRange = table.freeze({full = 180, lite = 80, off = 60}) -- beyond this (other players) nothing is drawn
Lod.MaxDinos = table.freeze({full = 12, lite = 6, off = 4}) -- how many dinos may carry effects at once

-- Detail for one effect kind. own = the local player's dino (never culled). rank = 1 for the nearest effect dino.
function Lod.detail(mode: string, kind: string, distance: number, own: boolean, rank: number, fullSlots: number): string
    local m = if Lod.CullRange[mode] then mode else "full"
    if m == "off" and kind ~= "mutation" then return "none" end
    if not own and (distance > Lod.CullRange[m] or rank > Lod.MaxDinos[m]) then return "none" end
    if m == "full" and (own or (distance <= Lod.FullRange and rank <= fullSlots)) then return "full" end
    return "lite"
end

-- 2026-10-16: tier rim Highlights (Roblox allows 31 at once; keep far below). Own dino and previews always get one; other fused
-- dinos get one only while under this cap, the rest use the cheap Neon glow shell. Off = none.
Lod.RimHighlights = table.freeze({full = 8, lite = 4, off = 0})
Lod.RimHighlightHardCap = 31

-- Does this dino get any effect rig at all? (cheap check before building anything)
function Lod.visible(mode: string, distance: number, own: boolean, rank: number): boolean
    return Lod.detail(mode, "mutation", distance, own, rank, 0) ~= "none"
end

-- BD-432 global live-FX budget (docs/126). The WHOLE scene, all dinos together, may not exceed these enabled counts. Distance LOD above
-- picks who gets effects; this picks how much of the shared pool each one may take. beams / lights on phone equal
-- tools/qa/phone_budgets.json (verify_fx checks it). PROVISIONAL until measured on a real phone (BD-085).
Lod.Live = table.freeze({
    phone = table.freeze({beams = 24, trails = 14, lights = 16, shells = 1}),
    tablet = table.freeze({beams = 72, trails = 20, lights = 24, shells = 2}),
    desktop = table.freeze({beams = 160, trails = 40, lights = 24, shells = 3}),
})
Lod.CostKeys = table.freeze({"beams", "trails", "lights", "shells"})

-- Pure: does one more rig (cost = FxRecipes cost plus shells) fit next to what is already live (used)?
function Lod.fits(device: string, used: {[string]: number}, cost: {[string]: number}): boolean
    local cap = Lod.Live[device] or Lod.Live.desktop
    for _, k in Lod.CostKeys do
        if (used[k] or 0) + (cost[k] or 0) > cap[k] then return false end
    end
    return true
end

-- Pure: the richest detail that fits. want = detail from detail(); costOf(detail) = cost of that look. Steps down full -> lite.
-- Never returns "none" when floor is "lite" (own dino, event-mutation cue): those always draw, at the lite look.
function Lod.fit(device: string, want: string, used: {[string]: number}, costOf: (string) -> {[string]: number}, floorLite: boolean): string
    if want == "none" then return "none" end
    if want == "full" and Lod.fits(device, used, costOf("full")) then return "full" end
    if Lod.fits(device, used, costOf("lite")) then return "lite" end
    return if floorLite then "lite" else "none"
end

return Lod
