--!strict
-- BD-080 (docs/45 F, BD-056 spec): pure rules for the gameplay HUD. Bottom-left egg icon "EGGS N" with a pop when N grows,
-- top-center slim SIZE bar. No Roblox services here: tools/verify_hud.py runs this file offline.
-- Words follow docs/72 (short, no "5m 0s", no "1.25x"). Nothing here changes any reward or growth number.
local Rules = {}

Rules.EggsWord = "EGGS"
Rules.SizeWord = "SIZE"
Rules.PopScale = 1.18 -- the egg icon swells by this much, then settles (soft overshoot, docs/87)
Rules.PopSeconds = 0.32
Rules.MinPopGap = 0.12 -- seconds: fast pickups merge into one pop instead of a buzzing icon
Rules.MaxSize = 4 -- the biggest dino scale (matches Dinosaur.scaleForScore's cap)
Rules.MinTarget = 44 -- px: nothing tappable is smaller

local function whole(value: any): number
    if typeof(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then return 0 end
    return math.max(0, math.floor(value))
end

-- 0..999 plain, 1,000..9,999 with a comma, then 12.3K, capped at 999K+ so the plate never grows past its width.
function Rules.formatCount(value: any): string
    local n = whole(value)
    if n < 1000 then return tostring(n) end
    if n < 10000 then return string.format("%d,%03d", n // 1000, n % 1000) end
    if n >= 999500 then return "999K+" end
    local tenths = n // 100
    local text = string.format("%d.%d", tenths // 10, tenths % 10)
    if string.sub(text, -2) == ".0" then text = string.sub(text, 1, -3) end
    return text .. "K"
end

function Rules.eggsText(value: any): string
    return Rules.EggsWord .. " " .. Rules.formatCount(value)
end

-- Dino scale for a growth score: same curve the server uses (Dinosaur.scaleForScore), so the bar never disagrees with the body.
function Rules.sizeFor(growth: any): number
    local g = if typeof(growth) == "number" and growth == growth then math.max(0, growth) else 0
    return math.min(Rules.MaxSize, math.sqrt(1 + g / 50))
end

-- Bar fill 0..1: 0 at the starting size, 1 at the biggest size. Bad input is an empty bar, never an error.
-- BD-386: growth per food is 5x slower, so the bar is measured against a normal five-minute run of about 500 food = 50 growth (BarFullGrowth 60),
-- not the 4x size cap; the body still follows sizeFor. Otherwise the bar would sit near empty all run.
Rules.BarFullGrowth = 60
function Rules.barFill(growth: any): number
    return math.clamp((Rules.sizeFor(growth) - 1) / (Rules.sizeFor(Rules.BarFullGrowth) - 1), 0, 1)
end

-- Should the egg icon pop? Only when the count really grew and the player is in a run (not when a new run resets to 0,
-- not on the first reading after joining), and never with Reduce Motion. `sinceLast` is seconds since the last pop.
function Rules.shouldPop(previous: any, current: any, running: boolean, motion: boolean, sinceLast: number?): boolean
    if not motion or not running then return false end
    if previous == nil then return false end
    if whole(current) <= whole(previous) then return false end
    if sinceLast ~= nil and sinceLast < Rules.MinPopGap then return false end
    return true
end

-- The FOOD debug line is for the Studio test view and admins only; every shipped player sees nothing.
function Rules.showFoodDebug(isStudio: boolean, isAdmin: boolean, touch: boolean): boolean
    return (isStudio or isAdmin) and not touch
end

return Rules
