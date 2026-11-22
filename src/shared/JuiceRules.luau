--!strict
-- BD-1286 (docs/245 "Juice to add", slice 1): the pure numbers and kid words of the eat pop + "+N" float and the crystal fly-to-counter, used ONLY
-- while Config.JuicePassEnabled is on (playtest profile). No Roblox services and no Instances here: tools/verify_juice_pass.py runs this file offline.
-- Calm (docs/87): short soft motion. Reduce Motion = no flying, no scale pop; the number only changes with a tiny fade.
local Rules = {}

Rules.MaxFlying = 12 -- icons in the air at once (the pool size)
Rules.MinIcons, Rules.MaxIcons = 3, 6
Rules.FlySeconds = 0.7 -- one icon, start to counter
Rules.FlyStagger = 0.06 -- seconds between the icons of one pickup
Rules.IconSize = 28 -- px, one flying crystal
Rules.Bend = 0.22 -- the curve bows this share of the distance to the side, so the icons arc
Rules.PopScale = 1.22 -- the counter swells by this much when a crystal lands (or the SIZE plate when the dino eats)
Rules.PopSeconds = 0.18
Rules.FloatSeconds = 0.7 -- "+N" floats 0.6-0.8 s (docs/245)
Rules.FloatRise = 0.9 -- of the word's own height, how far it rises
Rules.FadeSeconds = 0.2 -- Reduce Motion: the tiny fade on the changed number
Rules.MergeSeconds = 0.25 -- bites closer than this add up into one "+N"
Rules.MaxFloats = 3 -- numbers in the air

-- "+N" for a growth step; N = food points (growth / perFood, rounded, at least 1). Bad input: nil.
function Rules.growthText(delta: any, perFood: any): string?
    if typeof(delta) ~= "number" or delta ~= delta or delta <= 0 or delta == math.huge then return nil end
    if typeof(perFood) ~= "number" or perFood <= 0 then return nil end
    local n = math.max(1, math.floor(delta / perFood + 0.5))
    return "+" .. tostring(math.min(n, 9999))
end

-- How many small crystals fly for a pickup of `gained` crystals: 3 for a few, up to 6 for a lot. Bad input: 0 (nothing flies).
function Rules.iconCount(gained: any): number
    if typeof(gained) ~= "number" or gained ~= gained or gained <= 0 then return 0 end
    if gained < 10 then return Rules.MinIcons end
    if gained < 50 then return Rules.MinIcons + 1 end
    if gained < 200 then return Rules.MinIcons + 2 end
    return Rules.MaxIcons
end

-- Icons the pool may start now: `want` capped by the free slots (never above MaxFlying in the air).
function Rules.canStart(want: number, inAir: number): number
    return math.max(0, math.min(want, Rules.MaxFlying - inAir))
end

-- The point on the curve at t (0..1): a quadratic bezier from (x0,y0) to (x1,y1) whose control point is the middle pushed sideways by Bend
-- (side = 1 or -1, so a bunch of icons does not travel one line). Returns x, y.
function Rules.curve(x0: number, y0: number, x1: number, y1: number, t: number, side: number): (number, number)
    local mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    local dx, dy = x1 - x0, y1 - y0
    local cx, cy = mx - dy * Rules.Bend * side, my + dx * Rules.Bend * side
    local u = 1 - t
    return u * u * x0 + 2 * u * t * cx + t * t * x1, u * u * y0 + 2 * u * t * cy + t * t * y1
end

-- The size of one flying icon at t (1 = IconSize): it grows a little in the first part, then shrinks into the counter.
function Rules.iconScale(t: number): number
    if t < 0.25 then return 0.6 + 1.6 * t end
    return 1 - 0.6 * ((t - 0.25) / 0.75)
end

-- How much a value rose (0 when it did not rise or either side is not a number: the first read of a value is no pickup).
function Rules.rose(before: any, after: any): number
    if typeof(before) ~= "number" or typeof(after) ~= "number" then return 0 end
    if after <= before then return 0 end
    return after - before
end

return Rules
