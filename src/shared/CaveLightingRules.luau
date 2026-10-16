--!strict
-- BD-286 (docs/104 s4, docs/87 calm and bubbly): the Cave hub lighting as pure data and math: light-shaft beams under the 4 ceiling
-- holes, warm fill / lava / crystal / forge lights (never more than CaveHubLayout.MaxLights), the gate arch light and glow, and
-- the cave-only Lighting / Atmosphere / ColorCorrection look. Pure numbers only (no Instances): src/server/CaveLighting.luau builds
-- the FX parts and lights from this, src/client/CaveAtmosphere.luau applies the look while the player is inside,
-- and tools/verify_cave_lighting.py runs the same functions offline. Everything is PROVISIONAL (docs/104 s4, owner judges by eye).
-- FX NOTE: the light-shaft beams are lighting FX: two camera-facing, soft-edged Beams per hole (BD-296; they were translucent cylinder Parts
-- whose flat edges showed as vertical seams) on one invisible dust-volume Part. No mesh, no Neon. They are NOT model art; the tapered
-- cone mesh (`cave_light_cone`, BD-282) replaces them later.
local Layout = require(script.Parent.CaveHubLayout)
local Rules = {}
Rules.Version = 1
Rules.BeamColor = {255, 236, 190} -- warm cream
Rules.Beam = {outerFrac = 0.82, coreFrac = 0.5, outerAlpha = 0.92, coreAlpha = 0.89, beamsPerShaft = 2, topAbove = 3, bottomAbove = 0.15, motesPerSecond = 4}
Rules.GateGlow = {rate = 4, size = {12, 18}, alpha = 0.7, color = {255, 214, 160}, lift = 8, out = 12} -- out = studs from the pad centre into the mouth (the mouth is open from 10 studs past the pad centre)
Rules.FillColor, Rules.LavaColor, Rules.CrystalColor, Rules.ForgeColor = {255, 214, 170}, {255, 140, 70}, {255, 196, 80}, {255, 190, 90}
Rules.Forge = {period = 4, amplitude = 0.1, base = 0.6}
Rules.ShadowLights = 4
-- Cosy pass (docs/104 s14, owner 2026-10-16: a warm, safe, lamp-lit den). All PROVISIONAL, behind the CaveHub flag.
-- Lamp flicker: the warm fill, Heart and crystal lights breathe by at most `amplitude` (a fraction of their own brightness), slowly and
-- out of step with each other, like oil lamps. Never the lava, the forge (own pulse) or the gate arch (the doorway must stay steady).
-- Reduce Motion (calm) = the steady base brightness, no animation at all.
Rules.Lamp = {amplitude = 0.07, periodMin = 2.6, periodMax = 4.4, steady = {lava = true, forge = true, gate = true}}
-- Soft ambient bed under the cave: ONE quiet loop. No cave loop is registered in docs/110 yet, so `id` stays "" (nothing plays) until the
-- owner uploads one (TODO row cave_ambient_bed_loop, docs/77 and docs/120). Plays on the "ambience" group at `volume` x the cave amount.
Rules.Bed = {id = "", volume = 0.08, group = "ambience", fadeSeconds = 2.5}
-- Show-off spot: the Heart pedestal (collider top = floor + 3.8, CaveProps.colliderHeight clamps 3.5 to 4 minus 0.2). A prompt there steps the player's dino onto the pedestal so everyone can admire it.
Rules.ShowOff = {prompt = "Show off", promptDistance = 9, standHeight = 3.8, cooldown = 1.5}
Rules.FxPartBudget = 6 -- dust volumes (1 Part per hole, carrying that hole's 2 Beams) + the gate glow anchor (BD-296: the 8 cylinder Parts are gone)
-- Cave-only look (applied only while the player is inside the hub, restored on leaving; nothing here touches the island).
Rules.Look = {
    -- BD-398: a lit cave, not a bright hall: low warm-dim ambient, lower Lighting.Brightness and exposure; the lamps and shafts are the main lights
    ambient = {104, 92, 82}, outdoorAmbient = {98, 86, 76}, colorShiftTop = {255, 222, 180}, exposure = -0.2, brightness = 1.3, shadowSoftness = 0.35,
    fogStart = 160, fogEnd = 900, fogColor = {72, 56, 46}, -- owner "why so hazy": fog starts far, near props are never milked
    atmosphere = {density = 0.04, offset = 0, haze = 0, glare = 0, color = {214, 188, 160}, decay = {150, 104, 72}},
    grade = {brightness = -0.05, contrast = 0.08, saturation = 0.05, tint = {255, 226, 196}}, -- one soft shared warm grade warms the props, clear not milky (saturation >= 0) (MeshPart.Color is ignored on textured meshes)
    blendSeconds = 0.8,
}
Rules.EnterNorm, Rules.LeaveNorm = 1.0, 1.12 -- floor-blob norm (hysteresis) for "inside the hub"

local FY = Layout.FloorY
local cache: any = nil

local function station(L: any, id: string): any return L.byId[id] end

function Rules.get(): any
    if cache then return cache end
    local L = Layout.get()
    local cz = Layout.CenterZ
    local shafts = {}
    for _, h in L.holes do
        local top = h.ceilingY + Rules.Beam.topAbove
        local bottom = Layout.floorHeight(h.x, h.z + cz) + Rules.Beam.bottomAbove
        shafts[#shafts + 1] = {station = h.station, x = h.x, z = h.z + cz, holeRadius = h.radius, top = top, bottom = bottom,
            height = top - bottom, outerRadius = h.radius * Rules.Beam.outerFrac, coreRadius = h.radius * Rules.Beam.coreFrac}
    end
    -- lights in the order of Layout.lights (owner lists), so the count is the layout's count: heart 2, lava 3, crystal 2, forge 1, station fills
    local lights = {}
    local taken: {[string]: number} = {}
    local function add(owner: string, x: number, y: number, z: number, color: {number}, range: number, brightness: number, extra: any?)
        local item: any = {owner = owner, x = x, y = y, z = z + cz, color = color, range = range, brightness = brightness}
        if extra then for k, v in extra do item[k] = v end end
        lights[#lights + 1] = item
    end
    local heart = station(L, "heart")
    local style, fusion, gate = station(L, "style"), station(L, "fusion"), station(L, "gate")
    local P, F = Layout.Pool, Layout.Fall
    for _, entry in L.lights do
        local owner = entry.owner
        taken[owner] = (taken[owner] or 0) + 1
        local n = taken[owner]
        if owner == "heart" then
            if n == 1 then add(owner, heart.x, FY + 18, heart.z, Rules.FillColor, 48, 0.9)
            else add(owner, heart.x + 10, FY + 5, heart.z + 10, Rules.FillColor, 34, 0.65) end
        elseif owner == "lava" then
            if n == 1 then add(owner, P.x, FY + 5, P.z, Rules.LavaColor, 42, 0.7)
            elseif n == 2 then add(owner, F.x - 12, FY + 12, F.z - 4, Rules.LavaColor, 42, 0.7)
            else add(owner, F.x + 12, FY + 12, F.z - 4, Rules.LavaColor, 42, 0.7) end
        elseif owner == "crystal" then
            local o = style.outward
            add(owner, style.x + math.cos(o) * style.r * 0.6 + (if n == 1 then -3 else 3), FY + 3, style.z + math.sin(o) * style.r * 0.6, Rules.CrystalColor, 20, 0.45)
        elseif owner == "tunnel" or owner == "heartwall" then
            -- lantern niche in the wall: a warm light at head height beside the path
            add(owner, entry.x, FY + 7, entry.z, Rules.FillColor, 22, 0.8)
        elseif owner == "forge" then
            add(owner, fusion.x, FY + 3, fusion.z, Rules.ForgeColor, 24, Rules.Forge.base, {pulse = true})
        elseif owner == "gate" then
            -- the arch light: stronger and lower so the doorway reads from the Heart
            add(owner, gate.x, FY + 10, gate.z - 4, Rules.GateGlow.color, 46, 2.2, {arch = true})
        else
            local s = station(L, owner)
            local o = s.outward
            add(owner, s.x + math.cos(o) * s.r * 0.45, FY + 8, s.z + math.sin(o) * s.r * 0.45, Rules.FillColor, 34, 0.85)
        end
    end
    -- cosy pass: which lights breathe, each with its own slow period and phase (deterministic by list order)
    for i, l in lights do
        if not Rules.Lamp.steady[l.owner] then
            l.lamp = true
            l.phase = (i * 2.399963) % (2 * math.pi) -- golden angle: neighbours never flicker together
            l.period = Rules.Lamp.periodMin + ((i * 0.618034) % 1) * (Rules.Lamp.periodMax - Rules.Lamp.periodMin)
        end
    end
    -- BD-398: PointLight.Shadows only for the 4 strongest lights (brightness x range), the rest stay shadowless (cheap)
    local order = {}
    for i = 1, #lights do order[i] = i end
    table.sort(order, function(a, b) return lights[a].brightness * lights[a].range > lights[b].brightness * lights[b].range end)
    for i = 1, math.min(Rules.ShadowLights, #order) do lights[order[i]].shadows = true end
    local g = L.gate
    cache = {shafts = shafts, lights = lights,
        gate = {x = gate.x, z = gate.z + cz - Rules.GateGlow.out, y = FY + Rules.GateGlow.lift, mouthWidth = g.mouthWidth},
        fxParts = #shafts + 1, fxBeams = #shafts * Rules.Beam.beamsPerShaft}
    return cache
end

-- Lamp brightness at time `t` (seconds): base x (1 +- amplitude), two slow sines so it breathes instead of ticking. calm = base.
function Rules.lampBrightness(base: number, t: number, phase: number, period: number, calm: boolean): number
    if calm then return base end
    local w = 0.65 * math.sin(2 * math.pi * t / period + phase) + 0.35 * math.sin(2 * math.pi * t / (period * 0.37) + phase * 1.7)
    return base * (1 + Rules.Lamp.amplitude * w)
end

-- Bed volume for the current cave amount (0..1): 0 while no sound is registered (Bed.id == "").
function Rules.bedVolume(amount: number): number
    if Rules.Bed.id == "" then return 0 end
    return Rules.Bed.volume * math.clamp(amount, 0, 1)
end

-- Show-off spot in WORLD x, z, yaw (the Heart pedestal), or nil when the Heart has no pedestal.
function Rules.showOffSpot(): any
    for _, lg in Layout.get().ledges do
        if lg.owner == "heart_plinth" then
            return {x = lg.x, z = lg.z + Layout.CenterZ, yaw = Layout.yawTo(-lg.x, -lg.z), standHeight = Rules.ShowOff.standHeight}
        end
    end
    return nil
end

-- Inside the hub? (hysteresis: enter at the floor-blob edge, leave 12 percent beyond). Used by the client look and the weather gate.
function Rules.insideAt(x: number, y: number, z: number, was: boolean): boolean
    local n = Layout.floorNorm(x, z)
    if y > FY + 90 or y < FY - 40 then return false end
    return n <= (if was then Rules.LeaveNorm else Rules.EnterNorm)
end

-- Fraction 0..1 of the cave look to apply this frame: moves towards `target` (1 inside, 0 outside) over blendSeconds.
function Rules.blend(current: number, target: number, dt: number, calm: boolean): number
    local step = dt / math.max(Rules.Look.blendSeconds, 0.01)
    if calm then step *= 2 end
    if current < target then return math.min(target, current + step) end
    return math.max(target, current - step)
end

return Rules
