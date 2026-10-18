--!strict
-- BD-207: rare special dino foods, behind Config.SpecialFoodsEnabled (false). Pure data and rules; FoodService does the
-- placement and the server-side pickup (same PointGrid lookup and award path as every other food).
-- Effect on raw food points is EXPLICIT and PROVISIONAL: a special pickup is worth Config.SpecialFoodPoints raw food points
-- (a "big meal"). It feeds the same FoodCatchRules.award conversion, so FoodCatchRate is NOT changed here.
local Config = require(script.Parent.Config)
local ScaleLadder = require(script.Parent.ScaleLadder) -- BD-407: the pickup size lives in the one scale ladder
local SpecialFoods = {}
-- Kid-friendly name and one-line benefit. Art: existing registered food_drumstick mesh (BD-387); no new art needed.
SpecialFoods.GOLDEN_DRUMSTICK = {id = "golden_drumstick", name = "Golden Drumstick", benefit = "A giant tasty snack!", size = ScaleLadder.Food.goldenDrumstick.size, rgb = {255, 205, 80}}
-- All special foods by id (the id is the pickup's kind id and the "SpecialFoodId" character attribute).
SpecialFoods.All = {SpecialFoods.GOLDEN_DRUMSTICK}
function SpecialFoods.byId(id: any): any?
    if typeof(id) ~= "string" then return nil end
    for _, food in SpecialFoods.All do
        if food.id == id then return food end
    end
    return nil
end
-- BD-1002: the toast shown when a special food is eaten (title <= NotifyQueue.MaxText, body <= NotifyQueue.MaxBody; docs/72). nil for an
-- unknown id, so ordinary food (which never sets the attribute) and forged values show nothing. No sound of its own.
function SpecialFoods.pickupNote(id: any): (string?, string?)
    local food = SpecialFoods.byId(id)
    if food == nil then return nil, nil end
    return food.name .. "!", food.benefit
end
function SpecialFoods.enabled(): boolean
    return Config.SpecialFoodsEnabled == true
end
-- randomValue in [0,1). Returns true when a regular food slot becomes a special one.
function SpecialFoods.rolls(randomValue: number): boolean
    return SpecialFoods.enabled() and randomValue < Config.SpecialFoodChance
end
-- Raw food points a special pickup gives (before WeatherLootMultiplier and the admin multiplier, same as other foods).
function SpecialFoods.points(): number
    return Config.SpecialFoodPoints
end
return SpecialFoods
