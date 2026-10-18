--!nonstrict
-- BD-1052 (docs/188): data dump for tools/build_catalog.py. Python pastes the module sources at the marker line below, then runs this
-- file with the pinned Luau runner. It loads the REAL game modules (no copies of any number) through a tiny require shim and prints
-- one JSON document. Functions and Roblox objects are skipped. The only calls made here are the pure helpers the game itself uses
-- (ShopOdds, RewardMath, EggOutcomeOdds, ClassInfo), so the catalogue shows exactly what the game computes.
local SOURCES = {}
--@MODULES@

local cache, loading, errors = {}, {}, {}
local function proxy(name)
    return setmetatable({__module = name}, {__index = function(_, key)
        if key == "__module" then return name end
        return proxy(key)
    end})
end
local Color3 = {
    fromRGB = function(r, g, b) return {r = r, g = g, b = b} end,
    new = function(r, g, b) return {r = r, g = g, b = b} end,
}
local function load(name)
    if cache[name] ~= nil then return cache[name] end
    local fn = SOURCES[name]
    if fn == nil then error("module not available to the catalogue: " .. tostring(name)) end
    if loading[name] then error("circular module: " .. name) end
    loading[name] = true
    local value = fn(proxy("script"), function(p) return load(rawget(p, "__module")) end,
        function(v) return type(v) end, Color3, {GetService = function(_, n) return proxy(n) end})
    loading[name] = nil
    cache[name] = value
    return value
end
local function try(name)
    local ok, value = pcall(load, name)
    if not ok then errors[name] = tostring(value) return nil end
    return value
end

-- ---------------------------------------------------------------- JSON
local BS = string.char(92)
local escapes = {[string.char(34)] = BS .. string.char(34), [BS] = BS .. BS, [string.char(10)] = BS .. "n", [string.char(13)] = BS .. "r", [string.char(9)] = BS .. "t"}
local function str(s)
    return string.char(34) .. string.gsub(s, "[%c" .. string.char(34) .. "%" .. BS .. "]", function(c) return escapes[c] or string.format(BS .. "u%04x", string.byte(c)) end) .. string.char(34)
end
local function sortedKeys(t)
    local keys = {}
    for k in t do table.insert(keys, k) end
    table.sort(keys, function(a, b)
        if type(a) == type(b) and (type(a) == "number" or type(a) == "string") then return a < b end
        return tostring(a) < tostring(b)
    end)
    return keys
end
local function enc(v, out, depth)
    local t = type(v)
    if t == "nil" then table.insert(out, "null")
    elseif t == "boolean" then table.insert(out, v and "true" or "false")
    elseif t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then table.insert(out, "null")
        elseif v == math.floor(v) and math.abs(v) < 2 ^ 53 then table.insert(out, string.format("%d", v))
        else table.insert(out, string.format("%.17g", v)) end
    elseif t == "string" then table.insert(out, str(v))
    elseif t == "table" then
        if depth > 14 then table.insert(out, "null") return end
        local n, count = #v, 0
        for _ in v do count += 1 end
        if count == 0 then table.insert(out, "[]")
        elseif n == count then
            table.insert(out, "[")
            for i = 1, n do if i > 1 then table.insert(out, ",") end enc(v[i], out, depth + 1) end
            table.insert(out, "]")
        else
            table.insert(out, "{")
            local first = true
            for _, k in sortedKeys(v) do
                local tv = type(v[k])
                if tv ~= "function" and tv ~= "userdata" and tv ~= "thread" then
                    if not first then table.insert(out, ",") end
                    first = false
                    table.insert(out, str(tostring(k))) table.insert(out, ":") enc(v[k], out, depth + 1)
                end
            end
            table.insert(out, "}")
        end
    else table.insert(out, "null") end
end

-- ---------------------------------------------------------------- what the catalogue reads
local data = {}
for _, name in {"Config", "ProgressionConfig", "EggGenetics", "SecretSpeciesConfig", "ScaleLadder", "CombatConfig", "MutationLook",
    "AssetSlots", "LowPolyDinoAssets", "LowPolyPattern", "SpecialFoods", "BiomeMap", "BiomePlacement", "WorldKitData", "CaveHubProps",
    "RarityCurve", "UIIconAssets", "ArtworkAssets", "WorldKitMeshAssets", "IdentityFusion", "FusionOdds", "WeatherLooks", "ClassInfo", "ShopOdds",
    "EggOutcomeOdds", "RewardMath", "FoodCatchRules"} do
    data[name] = try(name)
end
local calls = {}
local Config, Progression = data.Config, data.ProgressionConfig
if data.ShopOdds and Progression then
    calls.conditionPercents = {}
    for level = 0, #Progression.ConditionWeights - 1 do calls.conditionPercents[level + 1] = data.ShopOdds.conditionPercents(level) end
end
if data.EggOutcomeOdds and Progression then
    calls.failure = {}
    for level = 0, #Progression.ConditionWeights - 1 do calls.failure[level + 1] = data.EggOutcomeOdds.failure(level) end
    calls.patterns = data.EggOutcomeOdds.patterns()
    calls.blendMode = data.EggOutcomeOdds.blendMode()
end
if data.RewardMath and Config then
    calls.speciesWeightsOne = data.RewardMath.speciesWeights(1)
    calls.speciesWeightsMax = data.RewardMath.speciesWeights(Config.EggRarityBoostMaxEggs)
end
if data.ClassInfo and Config then
    calls.classInfo = {}
    for _, id in Config.SpeciesOrder do calls.classInfo[id] = data.ClassInfo.forSpecies(id) end
    if data.SecretSpeciesConfig then
        for _, id in data.SecretSpeciesConfig.Order do calls.classInfo[id] = data.ClassInfo.forSpecies(id) end
    end
end
if data.SpecialFoods then calls.specialPoints = data.SpecialFoods.points() end
if data.IdentityFusion then data.IdentityFusion = {Version = data.IdentityFusion.Version, Ladder = data.IdentityFusion.Ladder, Recipes = data.IdentityFusion.Recipes} end
if data.RewardMath then data.RewardMath = nil end

local out = {}
enc({data = data, calls = calls, errors = errors}, out, 0)
print(table.concat(out))
