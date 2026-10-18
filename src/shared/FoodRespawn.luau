--!strict
-- BD-1081 (docs/115 LEAD decision 2026-10-18): how long a food stays gone after it is eaten, by food kind.
-- Pure, no Roblox services, so the offline tests run it directly. FoodService calls seconds() once per eaten food.
-- Flag off (Config.FoodRespawnTiersEnabled ~= true): every kind uses the one old time (Config.FoodRespawnSeconds), byte-identical to Build 020.
-- Flag on: Config.FoodRespawnByKind[kind id]; a kind that is not in the table (or has a bad number) falls back to the old time.
local FoodRespawn = {}

function FoodRespawn.seconds(kindId: string, tiersEnabled: boolean?, byKind: {[string]: number}?, defaultSeconds: number): number
    if tiersEnabled ~= true or type(byKind) ~= "table" then return defaultSeconds end
    local value = byKind[kindId]
    if type(value) ~= "number" or value ~= value or value <= 0 or value == math.huge then return defaultSeconds end
    return value
end

return FoodRespawn
