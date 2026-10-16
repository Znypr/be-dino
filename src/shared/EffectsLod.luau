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

-- Does this dino get any effect rig at all? (cheap check before building anything)
function Lod.visible(mode: string, distance: number, own: boolean, rank: number): boolean
    return Lod.detail(mode, "mutation", distance, own, rank, 0) ~= "none"
end

return Lod
