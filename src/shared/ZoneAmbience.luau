--!strict
-- BD-1225 (docs/242 gap 14, flag Config.ZoneAmbienceEnabled): one soft ambient loop per World V3 zone (Shared/WorldV3 Zones), crossfaded by
-- where the local dino stands. Data and pure rules here (tools/verify_social.py), the player in src/client/ZoneAmbience.client.luau.
-- Every id is Roblox-licensed Creator Store audio (creator checked in Studio, listed in docs/77). Quiet on purpose (docs/124: soft, under the
-- music); the loops go through the "ambience" group (the Weather slider), so the player's volume settings and the sound switch apply.
-- Unheard by agents: the owner judges by ear (docs/87); a wrong loop is fixed by changing its id or volume below.
local Z = {}

Z.FadeSeconds = 3 -- seconds for a full crossfade between two zones
Z.SeaMargin = 10 -- studs past the coast still count as the beach (waves)
Z.Order = table.freeze({"meadow", "forest", "pine", "beach", "volcano"})

-- zone id -> loop. An empty id is skipped (no sound for that zone).
Z.Loops = table.freeze({
    meadow = {id = "rbxassetid://9113444532", volume = .18}, -- ProSoundEffects "Birds Peaceful 2": chirping, peaceful, light wind, 70.8 s
    forest = {id = "rbxassetid://9112805925", volume = .16}, -- ProSoundEffects "Jungle Dawn 1": leaves rustling, wind, birds, dove, loop, 56 s
    pine = {id = "rbxassetid://9112832297", volume = .16}, -- ProSoundEffects "Mountain Birds 2": light distant birds, heavy air, loop, 40.2 s
    beach = {id = "rbxassetid://9120621776", volume = .2}, -- ProSoundEffects "Waves Rolling 2": distant ocean, rolling, coast, 33.1 s
    volcano = {id = "rbxassetid://9112795571", volume = .1}, -- ProSoundEffects "Hollow Rumble 2": deep steady drone, loop, 76.8 s (kept very low: it reads dark when loud)
})

-- A loop id is a usable "rbxassetid://n"; anything else is nil (skipped).
function Z.normalizeId(id: any): string?
    if type(id) ~= "string" then return nil end
    local n = string.match(id, "^rbxassetid://(%d+)$")
    return if n then id else nil
end

-- Which zone loop plays at (x, z). zoneAt = Shared/WorldV3.zoneAt; coast = WorldV3.coast; centre = the plaza (WorldV3.CenterX, CenterZ).
-- Out at sea (past the coast) it is the beach (waves); the spawn plaza is always the meadow (its centre sits on the sector borders).
function Z.zoneFor(x: number, z: number, world: any): string?
    if type(world) ~= "table" or type(world.zoneAt) ~= "function" then return nil end
    local dx, dz = x - (world.CenterX or 0), z - (world.CenterZ or 0)
    if type(world.coast) == "function" then
        local angle = math.deg(math.atan2(dz, dx))
        if math.sqrt(dx * dx + dz * dz) > world.coast(angle) + Z.SeaMargin then return "beach" end
    end
    if type(world.inPlaza) == "function" and world.inPlaza(x, z) then return "meadow" end -- the spawn plaza: birds, never the volcano rumble
    local zone = world.zoneAt(x, z)
    return if type(zone) == "table" and Z.Loops[zone.id] then zone.id else nil
end

-- Target level per loop: the active zone at its volume, everything else 0. Off the island, in a menu that hides the world (screen ~= ""),
-- or with the sound switch off, every loop fades to 0.
function Z.targets(active: string?, onIsland: boolean, screen: any, soundOn: boolean): {[string]: number}
    local out = {}
    local playing = soundOn and onIsland and (screen == nil or screen == "") and active ~= nil
    for _, name in Z.Order do
        out[name] = if playing and name == active then Z.Loops[name].volume else 0
    end
    return out
end

-- Move a level toward its target: a full loop's volume per FadeSeconds.
function Z.step(level: number, target: number, dt: number, full: number): number
    local delta = math.max(full, .01) * dt / Z.FadeSeconds
    if level < target then return math.min(target, level + delta) end
    return math.max(target, level - delta)
end

return Z
