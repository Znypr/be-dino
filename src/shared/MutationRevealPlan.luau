--!strict
-- BD-162: mutation reveal in the hatch, PURE plan (no Instances, no time source). When an egg hatches a dino with an event mutation
-- the hatch plays ONE soft burst (a bloom, thin rings, mist puffs, a few motif sprites) and then a calm loop until the player taps on.
-- Feel (docs/114 vibe words): bubbly, calm, vibrant, never an explosion. Each mutation has its own motion; colours come from
-- MutationLook and textures from EffectAssets keys (no new art, no invented ids). client/MutationReveal.luau draws it with pooled
-- sprites; tools/verify_mutation_reveal.py audits budgets, calm limits, Effects Full/Lite/Off and Reduce Motion.
-- Presentation only: it never reads or changes the server-committed outcome.
local P = {}

-- Body coordinates of the hatch panel (824 x 402 virtual px), the same space as HatchFxPlan.
P.Center = {412, 118}
P.Panel = {824, 402}

-- Motion per mutation. key = EffectAssets key for the motif sprite; shape = native fallback while the key has no real upload.
-- motion: rise (bubbles / embers), fall (snow, pebbles), zip (short tingly hops), orbit (slow dance), drift (ribbons).
P.Motifs = {
    dewdrop   = {key = "sparkSheet", shape = "disc",  motion = "rise",  size = 12, spin = 0},
    charged   = {key = "starFour",   shape = "spark", motion = "zip",   size = 14, spin = 0},
    frost     = {key = "starFour",   shape = "spark", motion = "fall",  size = 13, spin = 0.5},
    seismic   = {key = "smokeSheet", shape = "disc",  motion = "fall",  size = 11, spin = 0},
    ember     = {key = "flameSheet", shape = "disc",  motion = "rise",  size = 13, spin = 0},
    aurora    = {key = "swirl",      shape = "disc",  motion = "drift", size = 22, spin = 0},
    bloodmoon = {key = "sparkSheet", shape = "disc",  motion = "orbit", size = 12, spin = 0},
}
-- Aurora and Blood Moon are the top-rarity events: a little richer (more motif sprites), never louder (docs/88). LEAD choice.
P.Richness = {dewdrop = 1, charged = 1, frost = 1, seismic = 1, ember = 1, aurora = 1.25, bloodmoon = 1.25}

P.Base = {motifs = 10, puffs = 2, rings = 2}
P.DeviceScale = {phone = 0.5, tablet = 0.75, desktop = 1}
P.ModeScale = {full = 1, lite = 0.5}
P.Floors = {motifs = 3, puffs = 1, rings = 1}
-- Hard cap on every sprite this effect owns (glow disc + rings + puffs + motifs), per device.
P.Caps = {phone = 14, tablet = 20, desktop = 28}
P.LoopShare = 0.4 -- after the burst only this share of the motif sprites keep playing
P.StillGlow = {300, 0.22} -- Reduce Motion: one still glow (diameter px, opacity)

P.Limits = {
    maxAlpha = 0.85, puffAlpha = 0.5, glowAlpha = 0.3,
    burstLife = 1.6, ringLife = 0.9, puffLife = 1.2, motifLife = 2.4,
    maxRadius = 190, -- px from the dino centre: stays inside the panel
    maxSize = 24, maxSpin = 0.9, -- rad/s
}

local function scaled(n: number, f: number, floor: number): number
    return math.max(floor, math.ceil(n * f - 1e-9))
end

-- Counts for one mutation. mode = Effects "full" | "lite" | "off". Reduce Motion: ONE still glow disc, nothing else.
-- Off keeps the event cue (docs/103) as the glow plus one soft ring, no motif sprites.
function P.counts(id: string, device: string, mode: string, reduce: boolean?)
    if not P.Motifs[id] then return {glow = 0, motifs = 0, puffs = 0, rings = 0} end
    if reduce then return {glow = 1, motifs = 0, puffs = 0, rings = 0} end
    if mode == "off" then return {glow = 1, motifs = 0, puffs = 0, rings = 1} end
    local f = (P.DeviceScale[device] or 1) * (P.ModeScale[mode] or 1)
    local c = {glow = 1}
    for name, base in P.Base do
        c[name] = scaled(if name == "motifs" then base * (P.Richness[id] or 1) else base, f, P.Floors[name])
    end
    local cap = P.Caps[device] or P.Caps.desktop
    for _, name in {"puffs", "motifs", "rings"} do
        while P.total(c) > cap and c[name] > P.Floors[name] do c[name] -= 1 end
    end
    return c
end
function P.total(c): number
    return c.glow + c.motifs + c.puffs + c.rings
end
-- How many motif sprites keep playing in the calm loop.
function P.loopCount(c): number
    if c.motifs <= 0 then return 0 end
    return math.max(1, math.floor(c.motifs * P.LoopShare + 0.5))
end

local function clamp01(x: number): number return math.clamp(x, 0, 1) end
local function easeOut(x: number): number local k = 1 - clamp01(x) return 1 - k * k * k end

-- Glow disc behind the dino: pops in over 0.4 s with a soft overshoot, then breathes. since = seconds after the reveal.
-- Returns diameter px and opacity.
function P.glow(id: string, since: number): (number, number)
    if not P.Motifs[id] or since < 0 then return 0, 0 end
    local k = clamp01(since / 0.4)
    local pop = easeOut(k) * (1 + 0.12 * math.sin(k * math.pi))
    local breathe = 1 + 0.04 * math.sin(since * 2.2)
    return 300 * pop * breathe, P.Limits.glowAlpha * clamp01(since / 0.3)
end

-- Soft ring i (1-based, staggered 0.16 s): diameter px and opacity.
function P.ring(i: number, since: number): (number, number)
    local a = since - (i - 1) * 0.16
    local life = P.Limits.ringLife
    if a < 0 or a >= life then return 0, 0 end
    local k = a / life
    return 90 + 330 * easeOut(k), P.Limits.maxAlpha * 0.6 * (1 - k)
end

-- Smoke puff i of n: dx, dy, size, opacity. A soft puff of the mutation's mist colour that floats up and fades.
function P.puff(i: number, n: number, since: number): (number, number, number, number)
    local life = P.Limits.puffLife
    if since < 0 or since >= life then return 0, 0, 0, 0 end
    local k = since / life
    local ang = -math.pi / 2 + ((i - 0.5) / math.max(n, 1) - 0.5) * 2.2
    local dist = 20 + 60 * easeOut(k)
    local opacity = P.Limits.puffAlpha * math.sin(math.pi * k) ^ 0.8
    return math.cos(ang) * dist, math.sin(ang) * dist * 0.8 - 8 * k, 70 + 60 * easeOut(k), math.min(opacity, P.Limits.puffAlpha)
end

-- Motif sprite i of n at `since` seconds after the reveal: dx, dy (px from the dino centre), size, opacity, rotation (deg).
-- The burst spreads them wider, then they settle; each loops on its own offset.
function P.motif(id: string, i: number, n: number, since: number): (number, number, number, number, number)
    local entry = P.Motifs[id]
    if not entry or since < 0 then return 0, 0, 0, 0, 0 end
    local L = P.Limits
    local life = L.motifLife
    local age = (since + (i - 1) / math.max(n, 1) * life) % life
    local k = age / life
    local fade = math.sin(math.pi * k) ^ 0.7
    local arrive = clamp01(since / 0.5)
    local burst = 1 + 0.5 * (1 - clamp01(since / L.burstLife))
    local base = (i * 2.399) % (2 * math.pi) -- golden angle: even spread
    local radius = (86 + 12 * ((i * 5) % 4)) * burst
    local dx, dy
    local m = entry.motion
    if m == "rise" then
        dx, dy = math.cos(base) * radius * 0.9 + math.sin(since * 1.4 + i) * 8, 70 - 190 * k
    elseif m == "fall" then
        dx, dy = math.cos(base) * radius * 0.9 + math.sin(since * 0.8 + i) * 10, -110 + 200 * k
    elseif m == "zip" then
        local hop = math.floor(since * 2.5 + i) -- a tiny hop to a new spot every 0.4 s
        local a = (hop * 2.399 + i) % (2 * math.pi)
        dx, dy = math.cos(a) * radius, math.sin(a) * radius * 0.7 - 10
        fade = 0.5 + 0.5 * math.sin(since * 7 + i * 1.9) ^ 2 -- twinkle, soft, never a flash
    elseif m == "orbit" then
        local a = base + since * 0.7
        dx, dy = math.cos(a) * radius, math.sin(a) * radius * 0.6 - 10
        fade = 0.6 + 0.4 * math.sin(since * 2 + i)
    else -- drift: slow ribbons wandering around the dino
        local a = base + since * 0.45
        dx, dy = math.cos(a) * radius * 1.05, math.sin(a * 1.3) * radius * 0.7
        fade = 0.55 + 0.35 * math.sin(since * 1.3 + i)
    end
    local r = math.sqrt(dx * dx + dy * dy)
    if r > L.maxRadius then dx, dy = dx * L.maxRadius / r, dy * L.maxRadius / r end
    local size = math.min(entry.size * (0.8 + 0.1 * (i % 5)), L.maxSize)
    local opacity = math.min(L.maxAlpha, L.maxAlpha * fade * arrive)
    local rot = math.deg(math.min(entry.spin, L.maxSpin) * since + i)
    return dx, dy, size, opacity, rot
end

-- Colour for sprite i: aurora cycles green, blue, violet, magenta (docs/84); the rest alternate rim and spark.
P.AuroraCycle = {{81, 233, 187}, {110, 190, 255}, {170, 130, 255}, {240, 130, 230}}
function P.colorIndex(id: string, i: number): number
    if id == "aurora" then return (i - 1) % #P.AuroraCycle + 1 end
    return (i - 1) % 2 + 1
end

return P
