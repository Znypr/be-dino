--!strict
-- BD-1221 (docs/242 benchmark gap 4, extends BD-1181): the World V3 spawn plaza as a hub. Four stalls with big signs stand on the plaza
-- ring between the spoke paths, one per home station (nests, potions, shop, dinos), so the shops are visible in the world instead of only
-- behind HOME. Real meshes only: the cave home's own generated props (CaveHubProps.Assets ids, docs/77), nothing code-built.
-- Pure data and math, no Instances. Active only while Config.WorldV3Enabled and Config.PlazaHubEnabled are both true.
-- Stall frame: the stall stands at `angle` (degrees, WorldV3 polar) on the ring of radius Radius and faces the plaza centre;
-- local x = to the stall's right as you face it, local z = away from the centre (behind the counter).
local PlazaHubLayout = {}
PlazaHubLayout.Radius = 46 -- studs from the plaza centre (plaza radius 72, spawn at the centre)
PlazaHubLayout.PromptDistance = 12
PlazaHubLayout.PromptKey = "G" -- E is LEAP on the island HUD
PlazaHubLayout.PromptGamepad = "ButtonY"
-- Big sign: the cave's stone sign board at about 2.5x its cave size (5.5 x 5.5 x 2), left of the stall, word from HubSignCopy.
PlazaHubLayout.Sign = {key = "hub_sign_stone", size = {14, 14, 5}, at = {-15, 1}}
-- props: key = CaveHubProps.Assets key, size = target box in studs (w, h, d; the mesh is scaled uniformly to fit), at = local {x, z}, yaw = extra degrees.
-- solid = gets one hidden box collider of its footprint (the big pieces only; small ones stay walk-through like in the cave).
PlazaHubLayout.Stalls = {
    {station = "nests", screen = "eggs", angle = 27.5, props = {
        {key = "hub_nest_ledge", size = {17, 17, 9}, at = {0, 5}, solid = true},
    }},
    {station = "potions", screen = "potions", angle = 107.5, props = {
        {key = "hub_stall_potion", size = {19, 14, 9.5}, at = {0, 4}, solid = true},
    }},
    {station = "style", screen = "auras", angle = 180, props = {
        {key = "hub_counter_stone", size = {12.5, 10, 6.4}, at = {0, 4}, solid = true},
        {key = "hub_gem_chest", size = {5.6, 4.2, 4.2}, at = {9, -1}, yaw = -20},
        {key = "hub_crystal_l", size = {10, 15, 10}, at = {10, 6}},
    }},
    {station = "index", screen = "collection", angle = 312.5, props = {
        {key = "hub_lectern_book", size = {4.5, 6, 4.5}, at = {0, 0}, solid = true},
        {key = "hub_statue_trex", size = {9.5, 10.8, 10.6}, at = {8.5, 5}, yaw = -25},
        {key = "hub_statue_brachiosaurus", size = {9.1, 12.9, 14}, at = {-6, 8}, yaw = 20},
    }},
}

function PlazaHubLayout.enabled(config: any): boolean
    return type(config) == "table" and config.WorldV3Enabled == true and config.PlazaHubEnabled == true
end

-- World (x, z) and facing yaw (radians about +Y, Roblox convention: the stall's front looks toward the plaza centre) of a local
-- point {x, z} of a stall. centre = WorldV3 plaza centre.
function PlazaHubLayout.place(stall: any, at: {number}, centerX: number, centerZ: number): (number, number, number)
    local a = math.rad(stall.angle)
    local ox, oz = centerX + math.cos(a) * PlazaHubLayout.Radius, centerZ + math.sin(a) * PlazaHubLayout.Radius
    local outX, outZ = math.cos(a), math.sin(a) -- local +z (away from the centre)
    local rightX, rightZ = -math.sin(a), math.cos(a) -- local +x
    local x = ox + rightX * at[1] + outX * at[2]
    local z = oz + rightZ * at[1] + outZ * at[2]
    -- CFrame.lookAt(origin, centre) faces -Z toward the centre; yaw = atan2 of the direction the front looks along.
    return x, z, math.atan2(outX, outZ)
end

-- Where the walk-up prompt sits: in front of the stall (toward the centre).
PlazaHubLayout.PromptAt = {0, -6}

return PlazaHubLayout
