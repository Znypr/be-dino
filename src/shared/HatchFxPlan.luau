--!strict
-- Layered 2D hatch effects, PURE plan (BD-162 / BD-171 polish, docs/87 calm and bubbly, docs/93 budgets). No Instances, no time source:
-- counts per rarity tier and device class, curves and positions. client/HatchFx.luau draws it with pooled sprites; the offline
-- verifier (tools/verify_hatch_fx.py) checks budgets, tier monotonicity, calm limits and keep-out zones for the foreground pass.
-- Presentation only: it never reads or changes the server-committed outcome.
local Recipes = require(script.Parent.FxRecipes)
local P = {}

-- Body coordinates of the hatch panel (824 x 402 virtual px), the same space as HatchSequence.
P.Center = {egg = {412, 130}, dino = {412, 118}}
P.Panel = {824, 402}

-- Per tier (Common .. Mythic) counts for a DESKTOP; phone / tablet scale them (never below the floor).
P.Base = {
    sparks = {4, 6, 8, 10, 12, 14},   -- colour-matched rim sparks orbiting the egg, then the dinosaur
    motes  = {6, 7, 8, 10, 12, 14},   -- background floating motes
    puffs  = {2, 2, 3, 3, 4, 5},      -- soft smoke puffs on the burst
    shocks = {1, 1, 2, 2, 3, 3},      -- shock rings on the burst
    fg     = {0, 2, 3, 4, 5, 6},      -- foreground sparkle pass (side margins only)
    drops  = {4, 5, 6, 8, 10, 12},    -- extra droplets per paint bucket splash
}
P.Bloom = 3 -- soft glow discs behind the egg (fixed; the discs grow, they do not multiply)
P.Floors = {sparks = 2, motes = 3, puffs = 1, shocks = 1, fg = 0, drops = 3}
P.DeviceScale = {phone = 0.5, tablet = 0.75, desktop = 1}
-- Hard cap on live sprites the hatch FX may own, per device (everything counted: bloom + sparks + motes + puffs + shocks + fg + 2 x drops).
P.Caps = {phone = 38, tablet = 54, desktop = 72}
-- Trim order if a device is over its cap (least important first).
P.TrimOrder = {"fg", "motes", "puffs", "drops", "sparks", "shocks"}

-- Calm limits (verified).
P.Limits = {
    orbitSpin = 0.9,       -- rad/s rim sparks
    maxAlpha = 0.9,        -- opacity of anything
    puffAlpha = Recipes.Timing.maxMistAlpha, -- smoke stays see-through
    fgAlpha = 0.6,         -- foreground sparkles are gentle
    fgSize = 12,           -- px
    sparkSize = 16, moteSize = 12, dropSize = 10,
    puffLife = 1.2, shockLife = 0.7, dropLife = 0.55,
    maxFall = 140,         -- px a droplet may fall below its splash point
}

local function scaled(n: number, f: number, floor: number): number
    if n <= 0 then return 0 end
    return math.max(floor, math.ceil(n * f - 1e-9))
end

-- counts for a tier (1..6), device and Reduce Motion. Reduce Motion: ONE static glow disc, nothing else.
function P.counts(tier: number, device: string, reduce: boolean?)
    local t = math.clamp(math.floor(tier), 1, 6)
    if reduce then return {bloom = 1, sparks = 0, motes = 0, puffs = 0, shocks = 0, fg = 0, drops = 0, colors = 1, tier = t} end
    local f = P.DeviceScale[device] or 1
    local c = {bloom = P.Bloom, colors = Recipes.ColorCount[t], tier = t}
    for name, list in P.Base do c[name] = scaled(list[t], f, P.Floors[name]) end
    local cap = P.Caps[device] or P.Caps.desktop
    for _, name in P.TrimOrder do
        while P.total(c) > cap and c[name] > 0 do c[name] -= 1 end
    end
    return c
end
function P.total(c): number
    return c.bloom + c.sparks + c.motes + c.puffs + c.shocks + c.fg + 2 * c.drops
end

-- Colour list for a tier: more hues with rarity (Recipes palette rules). primary / accent are RGB 0..255 triples.
function P.palette(primary, tier: number)
    local list = Recipes.palette(primary, Recipes.mix(primary, {255, 255, 255}, 0.88), math.clamp(math.floor(tier), 1, 6))
    return list
end

local function clamp01(x: number): number return math.clamp(x, 0, 1) end
local function ease(x: number): number return Recipes.easeOutCubic(x) end

-- ---------------------------------------------------------------- bloom (grows through the build-up, pops on the burst)
-- p = build progress 0..1; since = seconds after the burst (nil while building). Returns scale 0..1 and the opacity of disc i of 3.
function P.bloomScale(p: number, since: number?): number
    if since then
        local pop = 1 + 0.18 * math.sin(clamp01(since / 0.45) * math.pi)
        return pop * (0.95 + 0.05 * Recipes.pulse(since))
    end
    return 0.3 + 0.7 * clamp01(p) ^ 1.3
end
function P.bloomAlpha(i: number, p: number, since: number?): number
    local base = 0.16 + 0.04 * (4 - i) -- inner disc is the strongest
    if since then return base * (1 - 0.35 * clamp01(since / 2)) end
    return base * clamp01(p * 1.6) -- fades in as the egg starts to glow
end

-- ---------------------------------------------------------------- rim sparks: orbit the egg rim (front/back depth)
-- Returns dx, dy (px from the centre), depth (-1 back .. 1 front), opacity, size.
function P.rimSpark(i: number, n: number, time: number, tier: number, p: number)
    local t = math.clamp(tier, 1, 6)
    local spin = math.min(P.Limits.orbitSpin, 0.5 + 0.06 * t)
    local a = time * spin + (i - 1) * (2 * math.pi / math.max(n, 1))
    local rx = 112 + 6 * ((i * 7) % 5)
    local depth = math.sin(a)
    local twinkle = 0.55 + 0.45 * math.sin(time * 3 + i * 1.7)
    local opacity = math.min(P.Limits.maxAlpha, (0.45 + 0.1 * depth) * twinkle * clamp01(0.25 + p))
    local size = (7 + (i % 3) * 3 + t * 0.6) * (0.8 + 0.2 * depth)
    return math.cos(a) * rx, math.sin(a) * rx * 0.62 - 6, depth, opacity, math.min(size, P.Limits.sparkSize)
end

-- ---------------------------------------------------------------- burst: soft smoke puffs and shock rings
-- age = seconds since the burst. Returns dx, dy, size, opacity (1 - transparency); opacity never above puffAlpha.
function P.puff(i: number, n: number, age: number)
    local life = P.Limits.puffLife
    if age < 0 or age >= life then return 0, 0, 0, 0 end
    local k = age / life
    local ang = -math.pi / 2 + ((i - 0.5) / math.max(n, 1) - 0.5) * 2.4
    local dist = 24 + 70 * ease(k)
    local size = 60 + 70 * ease(k) + i * 6
    local opacity = P.Limits.puffAlpha * math.sin(math.pi * clamp01(k)) ^ 0.8
    return math.cos(ang) * dist, math.sin(ang) * dist * 0.8 - 10 * k, size, math.min(opacity, P.Limits.puffAlpha)
end
-- Shock ring i (1-based, staggered .14 s): returns diameter px and opacity.
function P.shock(i: number, age: number)
    local a = age - (i - 1) * 0.14
    local life = P.Limits.shockLife
    if a < 0 or a >= life then return 0, 0 end
    local k = a / life
    return 80 + 360 * ease(k), P.Limits.maxAlpha * 0.7 * (1 - k)
end

-- ---------------------------------------------------------------- background motes
-- Slow floating motes: returns x, y (panel px), size, opacity. Loops from the bottom to the top.
function P.mote(i: number, time: number, tier: number)
    local speed = 10 + (i * 7) % 16
    local y = (402 + 20 - (time * speed + i * 53) % 440)
    local x = 24 + (i * 67) % 776 + math.sin(time * 0.9 + i * 1.3) * 14
    local size = math.min(P.Limits.moteSize, 5 + (i % 4) * 2 + tier * 0.4)
    local opacity = math.min(P.Limits.maxAlpha, 0.2 + 0.25 * math.abs(math.sin(time * 1.4 + i)))
    return x, y, size, opacity
end

-- ---------------------------------------------------------------- reveal chips (BD-220 / BD-223)
-- Centre x, centre y, width, height in panel px. One colour chip right UNDER each paint bucket (bucket hovers at egg x -/+ HatchTimeline.BucketX),
-- the pattern label just under the egg, the condition chip below it. One line each; none overlap (verified at every phone scale, since the
-- whole panel scales uniformly).
P.Chips = {
    left = {147, 160, 210, 50},
    right = {677, 160, 210, 50},
    pattern = {412, 292, 220, 34},
    condition = {412, 335, 300, 36},
}
function P.chipRect(name: string): {number}
    local c = P.Chips[name]
    return {c[1] - c[3] / 2, c[2] - c[4] / 2, c[1] + c[3] / 2, c[2] + c[4] / 2}
end
function P.overlaps(a: {number}, b: {number}): boolean
    return a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]
end

-- ---------------------------------------------------------------- foreground sparkle pass
-- Keep-out rectangles {x0, y0, x1, y1} in panel px: the dinosaur, the name / rarity area, the paint chips, the tap hint, the ribbons.
P.KeepOut = {
    {212, 0, 612, 262},    -- the dinosaur (and the egg)
    P.chipRect("left"), P.chipRect("right"), -- colour chips under the buckets
    {262, 262, 562, 330},  -- pattern label, condition chip, name / rarity pill
    {152, 327, 672, 373},  -- tap hint
    {11, 26, 221, 132},    -- Shiny / mutation ribbons (left)
    {649, 36, 799, 70},    -- BIG ribbon (right)
}
-- Foreground sparkles live ONLY in the two side margins, below the ribbons: returns x, y, size, opacity.
function P.fgSpark(i: number, n: number, time: number)
    local left = (i % 2) == 1
    local lane = math.floor((i - 1) / 2)
    local x0 = if left then 14 else 732
    local x = x0 + ((lane * 29 + i * 11) % 64) + math.sin(time * 0.8 + i) * 6
    local span = 180
    local y = 200 +((time * (14 + (i % 3) * 5) + i * 71) % span)
    local size = math.min(P.Limits.fgSize, 6 + (i % 3) * 2)
    local opacity = math.min(P.Limits.fgAlpha, 0.12 + 0.4 * math.abs(math.sin(time * 1.6 + i * 2.1)))
    return x, y, size, opacity
end
function P.inKeepOut(x: number, y: number, pad: number?): boolean
    local m = pad or 0
    for _, r in P.KeepOut do
        if x >= r[1] - m and x <= r[3] + m and y >= r[2] - m and y <= r[4] + m then return true end
    end
    return false
end

-- ---------------------------------------------------------------- paint splash droplet burst (BD-171)
-- Extra droplets (in the colour being revealed) around the splash point: j of n, `since` seconds after impact, side -1 left / +1 right.
-- Returns dx, dy, opacity (0 = gone), size. Low, soft arcs: they never reach the chips below.
function P.drop(j: number, n: number, since: number, side: number)
    local life = P.Limits.dropLife
    if since < 0 or since >= life then return 0, 0, 0, 0 end
    local k = since / life
    local a = (-0.05 - 0.9 * ((j - 0.5) / math.max(n, 1))) * math.pi
    local speed = 70 + (j * 29) % 70
    local dx = math.cos(a) * speed * since + side * 28 * since
    local dy = math.sin(a) * speed * since + 260 * since * since
    dy = math.min(dy, P.Limits.maxFall)
    local size = P.Limits.dropSize - 3 * clamp01(k) - (j % 3)
    return dx, dy, math.min(P.Limits.maxAlpha, 1 - k ^ 1.5), math.max(3, size)
end

-- ---------------------------------------------------------------- light shaft (BD-431 / BD-433, docs/123 s3)
-- ONE soft light shaft behind the egg and the dinosaur, from the top of the panel down through the egg, for Epic (tier 4) and up. It is the
-- shaftGradient Blender texture (a vertical gradient, bright at the source) shown by client/HatchFx.luau ONLY while that slot holds a real
-- upload, ONLY in the full Effects look and NEVER with Reduce Motion (docs/87 calm: no flash, it only fades in with the build-up).
-- It is one extra sprite counted against the device cap: when the cap has no room for it, P.withShaft trims the least important sprite
-- (P.TrimOrder) instead, so the total never grows (a tablet Mythic egg is exactly at its cap).
P.Shaft = {minTier = 4, width = 230, height = 330, alpha = 0.34, z = 21}
function P.shaft(tier: number, device: string, reduce: boolean?, mode: string?): number
    if reduce or mode ~= "full" then return 0 end
    if math.floor(tier) < P.Shaft.minTier then return 0 end
    return 1
end
-- counts() plus the shaft: returns the sprite counts (trimmed by TrimOrder only when the shaft would break the cap) and the shaft count 0 / 1.
function P.withShaft(tier: number, device: string, reduce: boolean?, mode: string?)
    local c = P.counts(tier, device, reduce)
    local n = P.shaft(tier, device, reduce, mode)
    local cap = P.Caps[device] or P.Caps.desktop
    if n > 0 then
        for _, name in P.TrimOrder do
            while P.total(c) + n > cap and c[name] > 0 do c[name] -= 1 end
        end
    end
    return c, n
end
-- Height scale (0.65..1) and opacity of the shaft: it fades in over the second half of the build-up (bp 0..1), holds through the burst and
-- eases down to about two thirds of its peak over three seconds (since = seconds after the burst, nil while building). Never above Shaft.alpha.
function P.shaftLook(bp: number, since: number?): (number, number)
    local k = ease(clamp01((bp - 0.35) / 0.65))
    local hold = if since then 1 - 0.35 * clamp01(since / 3) else 1
    return 0.65 + 0.35 * k, P.Shaft.alpha * k * hold
end

return P
