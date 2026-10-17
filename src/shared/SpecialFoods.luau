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
