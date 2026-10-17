--!nonstrict
-- docs/93 anime-style FX recipes (BD-161 / BD-162 / BD-163). PURE data and maths (RGB triples, no Roblox types), so it is
-- verified offline by tools/verify_fx.py. The client builds instances from it (client FxRig for the world dino,
-- shared FxUi for menu/shop previews). Rarity -> layers: more layers, more colours, slightly livelier, never louder than
-- the budget: layers are added in PRIORITY order and the first one that does not fit the device budget stops the list.
local R = {}

R.Tiers = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}
R.TierIndex = {Common = 1, Uncommon = 2, Rare = 3, Epic = 4, Legendary = 5, Mythic = 6}
R.LayerCount = {2, 3, 4, 5, 6, 7}   -- how many priority layers a tier shows
R.LayerCountByKind = {aura = {2, 3, 4, 6, 7, 8}} -- auras: Epic gains flame AND rays (FX v3)
R.ColorCount = {2, 3, 3, 4, 5, 6}   -- how many palette colours a tier may use (anime: more hues with rarity)
R.MutationTier = "Rare"             -- weather mutations read as Rare-level looks (4 layers + a one-shot pop)

-- Per-device budgets, PER DINO (docs/93 section 6). `alive` = particles alive at once (rate * lifetime, after rateScale).
R.Devices = {
    phone   = {sprites = 1, emitters = 3, beams = 3, trails = 2, parts = 1, lights = 1, alive = 18, rateScale = 0.5,  burst = 6,  fullDinos = 1, liteLights = false, liteRingBeams = 1},
    tablet  = {sprites = 1, emitters = 5, beams = 5, trails = 3, parts = 1, lights = 1, alive = 30, rateScale = 0.75, burst = 10, fullDinos = 2},
    desktop = {sprites = 1, emitters = 6, beams = 8, trails = 4, parts = 1, lights = 1, alive = 45, rateScale = 1.0,  burst = 14, fullDinos = 3},
}
R.DeviceOrder = {"phone", "tablet", "desktop"}
R.LiteLayers = 2 -- distant / extra dinos: only the first two priority layers, rates x0.6
R.MutationLiteLayers = 3 -- BD-353: a mutation keeps glow + ground ring + motes even in the lite look (aura / trail drop layers instead)

-- Calm timing limits the verifier enforces (docs/87).
R.Timing = {
    pulseHz = 0.55,      -- breathing glow, slower than a heartbeat
    ringSpinMax = 1.0,   -- radians per second, any orbit
    maxLife = 2.2,       -- seconds, any particle
    maxSpeed = 3.5,      -- studs per second, any particle
    fadeIn = 0.35,       -- effect fade-in on equip / appear
    burstSeconds = 0.6,  -- one-shot pop length
    maxMistAlpha = 0.5,  -- peak opacity of any smoke layer (dino stays readable)
    maxSparkAlpha = 0.9,
    minRingRadius = 1.2, -- rings stay outside the body (scale 1 studs)
    maxParticleSize = 1.6,
}

-- Named curves: lists of {t, value}. Particle/UI code samples them; values are multipliers 0..1+ or transparency.
R.Curves = {
    fadeInOut = {{0, 1}, {0.18, 0.3}, {0.55, 0.5}, {1, 1}},      -- transparency: fast ease-in, long soft fade-out
    sizeGrow  = {{0, 0.4}, {0.35, 1}, {1, 1.25}},                -- smoke puffs swell as they rise
    sizePop   = {{0, 0}, {0.2, 1}, {1, 0}},                      -- sparkles pop then shrink away
    taper     = {{0, 1}, {1, 0}},                                -- trail width
    trailAlpha = {{0, 0.12}, {0.5, 0.5}, {1, 1}},                -- trail transparency along its length
}

function R.sample(curve, t: number): number
    if t <= curve[1][1] then return curve[1][2] end
    for i = 2, #curve do
        local a, b = curve[i - 1], curve[i]
        if t <= b[1] then
            local f = (t - a[1]) / math.max(b[1] - a[1], 1e-6)
            return a[2] + (b[2] - a[2]) * f
        end
    end
    return curve[#curve][2]
end
function R.easeOutCubic(t: number): number local u = 1 - math.clamp(t, 0, 1) return 1 - u * u * u end
function R.easeInOutSine(t: number): number return -(math.cos(math.pi * math.clamp(t, 0, 1)) - 1) / 2 end
function R.pulse(time: number, hz: number?): number return 0.5 + 0.5 * math.sin(time * 2 * math.pi * (hz or R.Timing.pulseHz)) end

-- ---------------------------------------------------------------- colour maths (RGB 0..255)
local function mix(a, b, f) return {a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f} end
local function toHsv(c)
    local r, g, b = c[1] / 255, c[2] / 255, c[3] / 255
    local mx, mn = math.max(r, g, b), math.min(r, g, b)
    local d = mx - mn
    local h = 0
    if d > 0 then
        if mx == r then h = ((g - b) / d) % 6 elseif mx == g then h = (b - r) / d + 2 else h = (r - g) / d + 4 end
        h /= 6
    end
    return h, (if mx == 0 then 0 else d / mx), mx
end
local function fromHsv(h, s, v)
    h = h % 1
    local i = math.floor(h * 6)
    local f = h * 6 - i
    local p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    local r, g, b
    local k = i % 6
    if k == 0 then r, g, b = v, t, p elseif k == 1 then r, g, b = q, v, p elseif k == 2 then r, g, b = p, v, t
    elseif k == 3 then r, g, b = p, q, v elseif k == 4 then r, g, b = t, p, v else r, g, b = v, p, q end
    return {r * 255, g * 255, b * 255}
end
local function hueShift(c, turns)
    local h, s, v = toHsv(c)
    return fromHsv(h + turns, math.clamp(s, 0.45, 0.9), math.max(v, 0.85))
end
R.mix = mix
function R.distance(a, b) return math.abs(a[1] - b[1]) + math.abs(a[2] - b[2]) + math.abs(a[3] - b[3]) end

-- Palette: ordered by importance. Anime shading rule: the SHADOW colour is a cooler, darker shift (not black), the GLINT is
-- a near-white tint. Tier t may use the first ColorCount[t] entries.
R.PaletteNames = {"primary", "accent", "deep", "light", "hueA", "hueB"}
function R.palette(primary, accent, tierIndex: number)
    local acc = accent or mix(primary, {255, 255, 255}, 0.65)
    local all = {
        primary = primary,
        accent = acc,
        deep = mix(primary, {28, 36, 92}, 0.45),
        light = mix(primary, {255, 255, 255}, 0.55),
        hueA = hueShift(primary, 0.11),
        hueB = hueShift(primary, 0.33),
    }
    local count = R.ColorCount[math.clamp(tierIndex, 1, 6)]
    local list = {}
    for i = 1, count do list[i] = all[R.PaletteNames[i]] end
    return list, all, count
end

-- ---------------------------------------------------------------- layer templates (PRIORITY order, tier-1 values)
-- kind: glow (PointLight) | emitter (ParticleEmitter) | ring (orbiting beams) | spiral (rising beams) | trail | burst (one shot)
-- grad: palette names used for the colour gradient (names beyond the tier's ColorCount fall back to primary).
-- onlyMoving: trail / run effects, emitted only while the dino moves.
R.Templates = {
    -- FX v3 (owner 2026-10-16): every aura tier has anime smoke puffs; Rare+ sparkles; Epic+ flame wisps and a slow-pulsing rays
    -- pillar behind the dino; Legendary+ a swirl at the feet. minTier layers are skipped (not counted) below their tier.
    aura = {
        {id = "glow", kind = "glow", brightness = 0.42, range = 7, grad = {"primary"}},
        {id = "mist", kind = "emitter", tex = "smokeSheet", rate = 3, life = 1.6, size = 1.0, speed = 0.3, rise = 0.7, alpha = 0.4,
            light = 0.1, shape = "Cylinder", grad = {"deep", "primary"}, curve = "sizeGrow", spin = 18},
        {id = "motes", kind = "emitter", tex = "sparkSheet", minTier = 3, rate = 8, life = 1.1, size = 0.3, speed = 0.8, rise = 1.3, alpha = 0.8,
            light = 0.85, shape = "Cylinder", grad = {"primary", "accent"}, curve = "sizePop"},
        {id = "flame", kind = "emitter", tex = "flameSheet", minTier = 4, rate = 2, life = 0.9, size = 0.55, speed = 0.6, rise = 1.6, alpha = 0.75,
            light = 0.8, shape = "Cylinder", grad = {"light", "primary"}, curve = "sizePop"},
        {id = "rays", kind = "pillar", tex = "rays", minTier = 4, width = 3.2, height = 5.2, alpha = 0.5, hz = 0.25, grad = {"light", "primary"}},
        {id = "swirl", kind = "emitter", tex = "swirl", minTier = 5, rate = 0.6, life = 2.0, size = 1.25, speed = 0.05, rise = 0, alpha = 0.6,
            light = 1, shape = "Cylinder", flat = true, grad = {"accent", "primary"}, curve = "sizeGrow"},
        {id = "ring", kind = "ring", beams = 3, radius = 2.1, height = -1.55, spin = 0.45, width = 0.1, alpha = 0.7, grad = {"primary", "accent"}},
        {id = "ripple", kind = "emitter", tex = "ringShock", rate = 1.1, life = 1.4, size = 1.3, grow = 2.2, speed = 1.4, rise = 0, alpha = 0.5,
            light = 0.6, shape = "Disc", outward = true, grad = {"accent", "light"}, curve = "sizeGrow"},
        {id = "ribbon", kind = "spiral", beams = 2, radius = 1.5, low = -1.5, high = 1.0, spin = 0.7, width = 0.16, alpha = 0.65, grad = {"deep", "primary", "light"}},
        {id = "crown", kind = "ring", beams = 3, radius = 1.25, height = 0.65, spin = -0.6, width = 0.07, alpha = 0.6, grad = {"hueA", "accent", "hueB"}},
    },
    trail = {
        {id = "ribbon", kind = "trail", width = 1, life = 1, alpha = 0.88, light = 0.8, grad = {"primary", "accent"}},
        {id = "shed", kind = "emitter", tex = "sparkSheet", rate = 3, life = 0.9, size = 0.2, speed = 1.0, rise = 0.2, alpha = 0.85,
            light = 0.85, onlyMoving = true, grad = {"primary", "accent"}, curve = "sizePop"},
        {id = "under", kind = "trail", width = 1.9, life = 0.8, alpha = 0.38, light = 0.5, grad = {"deep", "primary"}},
        {id = "puffs", kind = "emitter", tex = "smokeSheet", rate = 3, life = 1.2, size = 0.8, speed = 0.4, rise = 0.3, alpha = 0.35,
            light = 0.1, onlyMoving = true, grad = {"deep", "primary"}, curve = "sizeGrow", spin = 20},
        {id = "lines", kind = "trail", count = 2, width = 0.22, life = 0.7, alpha = 0.7, light = 0.9, offset = 0.9, grad = {"light", "accent"}},
        {id = "stars", kind = "emitter", tex = "starFour", rate = 1.5, life = 1.6, size = 0.42, speed = 0.5, rise = 0.5, alpha = 0.9,
            light = 1, onlyMoving = true, grad = {"accent", "light", "hueA"}, curve = "sizePop", spin = 40},
        {id = "pop", kind = "burst", tex = "sparkSheet", count = 6, life = 0.6, size = 0.34, speed = 3, alpha = 0.9, light = 0.9, grad = {"accent", "light", "hueB"}},
    },
    -- BD-353: calm but clearly visible from ~20 studs. Priority: glow, a soft coloured GROUND RING (wider, brighter than before),
    -- slow rising motes, a little mist. Even the lite look (aura equipped / far dino, MutationLiteLayers) keeps glow + ring + motes.
    mutation = {
        {id = "glow", kind = "glow", brightness = 0.5, range = 8, grad = {"primary"}},
        {id = "ring", kind = "ring", beams = 3, radius = 2.2, height = -1.55, spin = 0.3, width = 0.24, alpha = 0.8, grad = {"primary", "accent"}},
        {id = "motif", kind = "emitter", tex = "sparkSheet", rate = 4, life = 1.8, size = 0.3, speed = 0.4, rise = 0.5, alpha = 0.85,
            light = 0.8, shape = "Cylinder", grad = {"primary", "accent"}, curve = "sizePop"},
        {id = "mist", kind = "emitter", tex = "smokeSheet", rate = 3, life = 1.7, size = 1.1, speed = 0.3, rise = 0.5, alpha = 0.42,
            light = 0.12, shape = "Cylinder", grad = {"deep", "primary"}, curve = "sizeGrow", spin = 15},
        {id = "ripple", kind = "emitter", tex = "ringShock", rate = 1.0, life = 1.4, size = 1.2, grow = 2.0, speed = 1.2, rise = 0, alpha = 0.45,
            light = 0.6, shape = "Disc", outward = true, grad = {"accent", "light"}, curve = "sizeGrow"},
        {id = "ribbon", kind = "spiral", beams = 2, radius = 1.4, low = -1.4, high = 1.0, spin = 0.6, width = 0.14, alpha = 0.55, grad = {"deep", "primary", "light"}},
        {id = "pop", kind = "burst", tex = "sparkSheet", count = 8, life = 0.6, size = 0.3, speed = 2.6, alpha = 0.9, light = 0.9, grad = {"accent", "light", "hueB"}},
    },
}

-- Per-mutation motif: tweaks the shared "motif" layer so each mutation reads differently (shape of motion, texture, mood).
R.Motifs = {
    dewdrop = {tex = "sparkSheet", rise = 0.5, speed = 0.5, size = 1.15, rate = 1.0},   -- slow round droplets / bubbles
    charged = {tex = "starFour", rise = 0.3, speed = 1.6, size = 0.8, rate = 1.3},       -- zippy small zig sparks
    frost = {tex = "crystalSheet", rise = -0.4, speed = 0.4, size = 1.1, rate = 1.0},    -- crystals drift DOWN gently
    seismic = {tex = "crystalSheet", rise = 0.2, speed = 0.6, size = 1.2, rate = 0.8},   -- pebbles and dust
    ember = {tex = "flameSheet", rise = 1.8, speed = 0.9, size = 1.0, rate = 1.1},       -- embers rise
    aurora = {tex = "sparkSheet", rise = 0.8, speed = 0.7, size = 1.0, rate = 1.0, hues = true}, -- ribbons drift green/blue/violet
    bloodmoon = {tex = "glowPlate", rise = 0.3, speed = 0.3, size = 1.3, rate = 0.7},    -- slow round crimson motes
}

-- BD-186..189 / docs/92: which Blender texture each mutation uses, per slot. Semantic EffectAssets keys only. A key is used ONLY while
-- its slot holds a valid upload (the caller passes `real`); otherwise the layer keeps exactly today's key and look.
--   glow  = the soft plate behind the hatch dino (hatch reveal only: the world glow is a PointLight, it has no texture)
--   ring  = the ground ring (world: a Disc ripple emitter; hatch: the thin expanding ring)
--   smoke = the mist puffs (world mist layer; hatch puffs)
--   motif = the floating details (world motif emitter; hatch motif sprites)
R.MutationTex = {
    dewdrop   = {glow = "glowPlateDroplet",                                         motif = "motifDroplets"},
    charged   = {glow = "glowPlateRound",                                           motif = "motifSoftSparks"},
    frost     = {glow = "glowPlateRound",                      smoke = "smokeWispy", motif = "motifSnowCrystals"},
    seismic   = {glow = "glowPlateRound", ring = "ringSeismic", smoke = "smokeDense", motif = "motifPebbles"},
    ember     = {glow = "glowPlateRound",                      smoke = "smokeDense", motif = "motifEmbers"},
    aurora    = {glow = "glowPlateRound",                                           motif = "motifAurora"},
    bloodmoon = {glow = "glowPlateCrescent",                                        motif = "motifCrimson"},
}
-- Coloured textures are drawn white (no tint); every other mutation texture is white or neutral and is tinted from MutationLook.
R.MutationTexColoured = {motifAurora = true}
-- Pure: the mapped key for (mutation, slot) when `real(key)` says its slot holds a valid upload; nil keeps today's look.
function R.mutationTex(id: string, slot: string, real: ((string) -> boolean)?): string?
    local entry = R.MutationTex[id]
    local key = if entry then entry[slot] else nil
    if key and real and real(key) then return key end
    return nil
end

-- ---------------------------------------------------------------- cost and resolve
local function newCost() return {emitters = 0, beams = 0, trails = 0, parts = 0, lights = 0, alive = 0, burst = 0, sprites = 0} end
function R.layerCost(layer)
    local c = newCost()
    local k = layer.kind
    if k == "glow" then c.lights = 1
    elseif k == "emitter" then c.emitters = 1 c.alive = layer.rate * layer.life
    elseif k == "burst" then c.emitters = 1 c.burst = layer.count
    elseif k == "ring" or k == "spiral" then c.beams = layer.beams
    elseif k == "trail" then c.trails = layer.count or 1
    elseif k == "pillar" then c.sprites = 1 end
    return c
end
local function needsAnchor(layer) return layer.shape ~= nil or layer.kind == "ring" or layer.kind == "spiral" or layer.kind == "pillar" end
function R.totalCost(layers)
    local total = newCost()
    local anchor = false
    for _, layer in layers do
        local c = R.layerCost(layer)
        for k, v in c do total[k] += v end
        if needsAnchor(layer) then anchor = true end
    end
    total.parts = if anchor then 1 else 0
    return total
end
local function fits(total, budget)
    return total.emitters <= budget.emitters and total.beams <= budget.beams and total.trails <= budget.trails
        and total.parts <= budget.parts and total.lights <= budget.lights and total.alive <= budget.alive + 1e-6
        and total.burst <= budget.burst and total.sprites <= (budget.sprites or 0)
end

local function copy(t) local o = {} for k, v in t do o[k] = v end return o end

-- item: the ProgressionConfig row (aura/trail: id, rarity, color, accent, width, lifetime, particles) or a MutationLook entry
-- (mutation: id, spark, rim, mist). kind: "aura" | "trail" | "mutation". opts: {device="desktop", reduce=bool, detail="full"|"lite",
-- real=function(key)->bool}. `real` (mutations only) says which texture keys hold a valid upload; without it, or while a slot is
-- empty, the mutation keeps exactly today's layers (R.MutationTex).
function R.resolve(kind: string, item, opts)
    opts = opts or {}
    local device = R.Devices[opts.device or "desktop"] or R.Devices.desktop
    local tierName = if kind == "mutation" then R.MutationTier else (item.rarity or "Common")
    local tier = R.TierIndex[tierName] or 1
    local primary, accent
    if kind == "mutation" then primary, accent = item.spark, item.rim
        if item.mist then accent = mix(item.rim, {255, 255, 255}, 0.45) end
    else
        primary = item.color
        accent = item.accent or (if item.id == "royal" then {255, 215, 115} else nil)
    end
    local palette, named, colorCount = R.palette(primary, accent, tier)
    if kind == "mutation" and item.mist then named.deep = item.mist end -- the look table owns the shadow colour
    local out = {kind = kind, id = item.id, tier = tier, tierName = tierName, device = opts.device or "desktop", palette = palette,
        named = named, colorCount = colorCount, reduced = opts.reduce == true, layers = {}}
    local templates = R.Templates[kind]
    if not templates then return out end

    -- Every layer needs a colour table (names beyond the tier's palette fall back to primary). The Reduce Motion layers used to
    -- skip this, so FxRig.colorSeq(nil) threw "attempt to get length of a nil value" (weather QA 2026-10-16).
    local function colorize(layer)
        layer.color = {}
        for i, name in layer.grad do
            local usable = false
            for j = 1, colorCount do if R.PaletteNames[j] == name then usable = true end end
            layer.color[i] = if usable then named[name] else named.primary
        end
    end
    if opts.reduce then
        -- Reduce Motion: no particles, no beams, no looping. Aura/mutation keep one still, soft glow; trails keep ONE short ribbon
        -- (it only follows the dino, it never animates by itself).
        if kind == "trail" then
            local t = copy(templates[1])
            t.life = 0.45 t.width *= (item.width or 0.5) t.alpha = 0.7 t.grad = {"primary", "accent"}
            colorize(t)
            table.insert(out.layers, t)
        else
            local g = copy(templates[1])
            g.brightness = math.min(g.brightness, 0.4)
            colorize(g)
            table.insert(out.layers, g)
            if kind == "mutation" then
                -- BD-353: Reduce Motion keeps the mutation readable: the same ground ring, standing still (spin 0), no particles.
                local ring = copy(templates[2])
                ring.spin, ring.alpha = 0, 0.7
                colorize(ring)
                table.insert(out.layers, ring)
            end
        end
        out.cost = R.totalCost(out.layers)
        return out
    end

    local lite = opts.detail == "lite"
    local limit = if lite then (if kind == "mutation" then R.MutationLiteLayers else R.LiteLayers) else (R.LayerCountByKind[kind] or R.LayerCount)[tier]
    -- docs/130: on a phone the OTHER players' lite effects (the local dino is always full) keep no aura glow light or aura beams and
    -- a single-beam mutation ring, so 12 players stay inside the phone light/beam budget. Mutation keeps its glow (it must stay readable).
    local phoneLite = lite and device.liteLights == false
    local skipped = 0 -- dropped layers still use up a lite slot, so a phone never shows MORE than before
    local rateF = (1 + 0.1 * (tier - 1)) * (if lite then 0.6 else 1) * device.rateScale
    local sizeF = 1 + 0.05 * (tier - 1)
    local motif = if kind == "mutation" then R.Motifs[item.id] else nil
    local real = if kind == "mutation" then opts.real else nil
    for _, tpl in templates do
        if kind == "mutation" and tpl.id == "ripple" then
            -- Only a real ring texture (Seismic: ringSeismic) earns the ground ripple, as one EXTRA full-look layer. The lite look stops
            -- at its layer limit before it gets here, so lite and Reduce Motion are exactly as before. The device budget still applies.
            if not R.mutationTex(item.id, "ring", real) then continue end
        elseif #out.layers + skipped >= limit then break end
        if tpl.minTier and tier < tpl.minTier then continue end
        if phoneLite and kind == "aura" and (tpl.kind == "glow" or tpl.kind == "ring" or tpl.kind == "spiral") then skipped += 1 continue end
        local layer = copy(tpl)
        if phoneLite and layer.kind == "ring" then layer.beams = math.min(layer.beams, device.liteRingBeams or layer.beams) layer.width *= 1.5 end
        if layer.rate then layer.rate *= rateF end
        if layer.size then layer.size *= sizeF end
        if layer.id == "shed" then layer.rate = math.max(2, (item.particles or 2) * 1.2) * rateF end
        if kind == "trail" and layer.kind == "trail" then
            layer.width *= (item.width or 0.5)
            layer.life *= (item.lifetime or 0.7)
        end
        if layer.id == "motif" and motif then
            layer.tex, layer.rise, layer.speed = motif.tex, motif.rise, motif.speed
            layer.size *= motif.size layer.rate *= motif.rate
            if motif.hues then layer.grad = {"primary", "hueA", "hueB"} end
        end
        local mapped = if kind == "mutation" then R.mutationTex(item.id, if layer.id == "motif" then "motif" elseif layer.id == "mist" then "smoke" elseif layer.id == "ripple" then "ring" else "", real) else nil
        if mapped then layer.tex = mapped end
        if tier >= 5 and layer.kind == "emitter" and layer.id ~= "mist" and #layer.grad >= 2 then
            layer.grad = {"light", "primary", "accent", "deep"} -- full-spectrum cycle for the top tiers
        end
        layer.color = {}
        for i, name in layer.grad do
            local base = named[name]
            local usable = false
            for j = 1, colorCount do if R.PaletteNames[j] == name then usable = true end end
            layer.color[i] = if usable then base else named.primary
        end
        if mapped and R.MutationTexColoured[mapped] then
            layer.grad, layer.color, layer.coloured = {"primary"}, {{255, 255, 255}}, true -- coloured art: no tint
        end
        local candidate = copy(out.layers)
        table.insert(candidate, layer)
        if not fits(R.totalCost(candidate), device) then
            if tpl.minTier then continue end -- a tier extra that does not fit this device is skipped, the core layers go on
            break
        end
        table.insert(out.layers, layer)
    end
    out.cost = R.totalCost(out.layers)
    return out
end

-- Which device class: phone = touch and no mouse; tablet = touch with a big screen; desktop otherwise (pure: caller passes facts).
function R.deviceClass(touch: boolean, mouse: boolean, shortSidePixels: number): string
    if touch and not mouse then return if shortSidePixels >= 700 then "tablet" else "phone" end
    return "desktop"
end

-- BD-431 / BD-433 (docs/123 s3): the optional shell mesh (slot aura_shell_mesh) around the dino. Pure, so it is verified offline.
-- It needs the real mesh (meshReady), and never shows with Reduce Motion or in the lite look (Effects Lite, extra or distant dinos).
-- Auras wear it from Epic up for as long as the aura lives; an event mutation wears it only for ShellSeconds.mutation after it
-- appears (the reveal), then it fades away. An empty slot means no shell at all, exactly as before.
R.ShellMinTier = 4
R.ShellSeconds = {mutation = 6}
function R.wantsShell(kind: string, tier: number?, reduced: boolean?, detail: string?, meshReady: boolean?): boolean
    if not meshReady or reduced or detail == "lite" then return false end
    if kind == "aura" then return (tier or 0) >= R.ShellMinTier end
    return kind == "mutation"
end
-- Opacity multiplier 0..1 of a shell `age` seconds after it appeared: fades in over fadeIn, and (mutation only) fades out over its last second.
function R.shellFade(kind: string, age: number): number
    local fadeIn = math.clamp(age / R.Timing.fadeIn, 0, 1)
    local life = R.ShellSeconds[kind]
    if not life then return fadeIn end
    return fadeIn * math.clamp((life - age) / 1.0, 0, 1)
end

return R
