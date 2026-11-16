--!strict
-- BD-1047 (docs/187 B): the designed food map. FoodLayerData.Map is a WorldLayer (src/shared/WorldLayer.luau) over the arena where every
-- cell is 0 (no food) or a food kind: 1 berry, 2 fruit, 3 egg, 4 amber (the order of TYPES in FoodService; 5 stays free for special food).
-- tools/generate_food_layer.py makes the text with rules (small clusters of 3 to 5 foods, spacing, hot spots, density near spawn) and tools/verify_food_layer.py checks it.
-- This module is pure (no Instances): it only turns the map into a list of items per FoodService sector. FoodService reads it only while
-- Config.FoodLayerEnabled is true (off in the default profile, on in the playtest profile).
local WorldLayer = require(script.Parent.WorldLayer)
local FoodLayerData = require(script.Parent.FoodLayerData)

local FoodLayer = {}

export type Item = {x: number, z: number, kind: number, starter: boolean}

FoodLayer.Kinds = table.freeze({"berry", "fruit", "egg", "amber"})
-- The starter patches next to the run start (0, 30): nine foods each, two berries to one fruit, same as the old placement.
FoodLayer.StarterCentres = table.freeze({table.freeze({-15, 24}), table.freeze({15, 24})})
FoodLayer.StarterRadius = 14

-- Where an item whose planned spot fails the ground checks may go: a fixed spiral around it (1 to 4 studs), nearest first. Fixed numbers, no dice,
-- so the same map always gives the same result.
local offsets = {}
for k = 1, 24 do
    local radius = 1 + 3 * (k - 1) / 23
    local angle = k * 2.399963229728653 -- golden angle
    table.insert(offsets, table.freeze({math.cos(angle) * radius, math.sin(angle) * radius}))
end
FoodLayer.FallbackOffsets = table.freeze(offsets)

-- BD-1208 (docs/241 W8): while Config.WorldV3Enabled is true the map is the one made for the redesigned round island (FoodLayerDataV3, same format, its own
-- starter patches just outside the plaza edge). Flag off (or an offline runner without `script`): FoodLayerData, exactly as before.
local function v3Data(): any?
    local okConfig, Config = pcall(function() return require((script :: any).Parent.Config) end)
    if okConfig and type(Config) == "table" and (Config :: any).WorldV3Enabled == true then
        return require((script :: any).Parent.FoodLayerDataV3)
    end
    return nil
end

function FoodLayer.isStarter(x: number, z: number): boolean
    local v3 = v3Data()
    local centres: any = if v3 then v3.StarterCentres else FoodLayer.StarterCentres
    local radius: number = if v3 then v3.StarterRadius else FoodLayer.StarterRadius
    for _, centre in centres do
        if (x - centre[1]) ^ 2 + (z - centre[2]) ^ 2 <= radius ^ 2 then return true end
    end
    return false
end

-- The decoded map (nil and a reason when the text is not a valid layer).
-- BD-1238 (docs/241 W6 + W7): with Config.FoodHostsEnabled and ToonWorldEnabled on top of WorldV3Enabled the map is FoodLayerDataV3Hosts: the same
-- foods moved to the bushes, trees, rocks and landmark edges that stand on the toon island (tools/food_hosts.py). Same starter patches as the V3 map.
local function hostsMap(): string?
    local okConfig, Config = pcall(function() return require((script :: any).Parent.Config) end)
    if okConfig and type(Config) == "table" and (Config :: any).FoodHostsEnabled == true and (Config :: any).ToonWorldEnabled == true then
        return require((script :: any).Parent.FoodLayerDataV3Hosts).Map
    end
    return nil
end

function FoodLayer.load(text: string?): (WorldLayer.Layer?, string?)
    local v3 = v3Data()
    return WorldLayer.decode(text or (if v3 then (hostsMap() or v3.Map) else FoodLayerData.Map))
end

-- Items per sector: plan[sx * sectorCount + sz] = {Item} (row by row inside a sector), and the total. Sectors are the FoodService squares:
-- sectorCount squares over [-extent, extent]. Cells with a value outside 1..4 are skipped. Returns nil and a reason when the map is unusable.
function FoodLayer.plan(sectorCount: number, extent: number, text: string?): ({[number]: {Item}}?, number | string)
    local layer, reason = FoodLayer.load(text)
    if not layer then return nil, reason or "unreadable food map" end
    local sectorWidth = 2 * extent / sectorCount
    local plan: {[number]: {Item}} = {}
    local total = 0
    WorldLayer.forEachNonZero(layer, function(ix: number, iz: number, value: number)
        if value < 1 or value > #FoodLayer.Kinds then return end
        local x, z = WorldLayer.centreOf(layer, ix, iz)
        if math.abs(x) > extent or math.abs(z) > extent then return end
        local sx = math.clamp(math.floor((x + extent) / sectorWidth), 0, sectorCount - 1)
        local sz = math.clamp(math.floor((z + extent) / sectorWidth), 0, sectorCount - 1)
        local key = sx * sectorCount + sz
        local list = plan[key]
        if not list then list = {} plan[key] = list end
        table.insert(list, {x = x, z = z, kind = value, starter = FoodLayer.isStarter(x, z)})
        total += 1
    end)
    if total == 0 then return nil, "the food map holds no food" end
    return plan, total
end

return FoodLayer
