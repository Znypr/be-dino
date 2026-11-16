--!strict
-- BD-1220 (docs/242 benchmark gap 5, rule W9 "no haze"): a real sea around the World V3 island instead of the flat 6000-stud square
-- plate with a hard corner. Pure data and math, no Instances:
--   * the sea floor of WorldV3.height drops from the beach to SeaFloor (deep water reads blue, the shelf by the beach stays turquoise);
--   * terrain water continues past the island square out to Radius in Tile-sized blocks (far past the clear fog end, so no edge shows);
--   * clear weather drops the classic distance fog (its flat pale colour never matches the sky, so fogged sea read as a pale square
--     plate) and lets the Atmosphere give the depth instead: it blends the sea into the sky at the horizon. Phones keep their tight
--     classic fog (it hides the prop cull edge, BD-213); weather events still bring their own fog in.
-- Active only while Config.WorldV3Enabled and Config.RealSeaEnabled are both true (off = the sea exactly as before).
local WorldSea = {}
WorldSea.SeaFloor = -22 -- lowest sea floor (WorldV3 default -6: a pale shallow plate everywhere)
WorldSea.SeaSlope = .3 -- floor drop per stud out from the coast (WorldV3 default .22)
WorldSea.FloorLow = -24 -- lowest terrain cell written (the island square used -16)
WorldSea.Radius = 2600 -- terrain sea radius around the plaza centre (desktop clear fog ends at 1400, lifted 2520 from high up)
WorldSea.Tile = 212 -- studs per far-sea block: 848 / 4, so the blocks line up with the island square (-424..424) on the 4-stud grid
WorldSea.FlatFrom = 480 -- past this distance from the plaza centre every column is at SeaFloor (coast max 390 + 22.4 / .3)
WorldSea.Atmosphere = {density = .3, haze = 0, offset = 0, glare = 0} -- clear day (was density .1, haze .3, offset .1 in Bootstrap)
WorldSea.ClearFog = {fogStart = 8000, fogEnd = 20000} -- desktop and tablet clear weather: classic fog pushed past the sea (was 400 / 1400)

function WorldSea.enabled(config: any): boolean
    return type(config) == "table" and config.WorldV3Enabled == true and config.RealSeaEnabled == true
end

-- The clear-weather classic fog for a device class: nil = keep the normal one (phones), else {fogStart, fogEnd}.
function WorldSea.clearFog(deviceClass: string): {fogStart: number, fogEnd: number}?
    if deviceClass == "Phone" then return nil end
    return WorldSea.ClearFog
end

-- Far-sea blocks: the minimum corner {x, z} of every Tile x Tile block whose centre lies within Radius of (cx, cz) and that is outside
-- the island square [-half, half] (the island terrain writes that square itself).
function WorldSea.tiles(cx: number, cz: number, half: number): {{number}}
    local tile, out = WorldSea.Tile, {}
    local reach = math.ceil((WorldSea.Radius + math.max(math.abs(cx), math.abs(cz))) / tile) + 1
    for i = -reach, reach do
        for j = -reach, reach do
            local x, z = -half + i * tile, -half + j * tile
            local inside = x >= -half and x + tile <= half and z >= -half and z + tile <= half
            local mx, mz = x + tile / 2 - cx, z + tile / 2 - cz
            if not inside and mx * mx + mz * mz <= WorldSea.Radius * WorldSea.Radius then table.insert(out, {x, z}) end
        end
    end
    return out
end

-- The home's terrain box {minX, minZ, maxX, maxZ} (the cave hall shell, CaveTerrainRules XMin/ZMin/XMax/ZMax; verify_world_look checks they match).
WorldSea.HomeBox = {-148, 452, 148, 708}
-- True when a block (minimum corner {x, z}, Tile wide) overlaps the box {minX, minZ, maxX, maxZ} (the home's terrain box).
function WorldSea.overlaps(tile: {number}, box: {number}): boolean
    return tile[1] < box[3] and tile[1] + WorldSea.Tile > box[1] and tile[2] < box[4] and tile[2] + WorldSea.Tile > box[2]
end

-- Voxel column for a floor height (cells of `resolution` from FloorLow up to sea level 0), the same rule as the island terrain:
-- a cell at least half under the floor is Sand, otherwise the part of it under sea level is Water. Returns material names ("Sand" / "Water") and occupancies.
function WorldSea.column(floor: number, resolution: number): ({string}, {number})
    local materials, occupancy = {}, {}
    local cells = math.floor(-WorldSea.FloorLow / resolution)
    for y = 1, cells do
        local wy = WorldSea.FloorLow + (y - .5) * resolution
        local solid = math.clamp((floor - wy) / resolution + .5, 0, 1)
        if solid < .5 then
            materials[y], occupancy[y] = "Water", math.clamp((0 - (wy - resolution / 2)) / resolution, 0, 1)
        else
            materials[y], occupancy[y] = "Sand", solid
        end
    end
    return materials, occupancy
end

return WorldSea
