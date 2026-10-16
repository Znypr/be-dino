--!strict
-- BD-286 (docs/104 s4, docs/87 calm and bubbly): the Cave hub lighting as pure data and math: light-shaft beams under the 4 ceiling
-- holes, warm fill / lava / crystal / forge lights (never more than CaveHubLayout.MaxLights), the gate arch light and glow, and
-- the cave-only Lighting / Atmosphere / ColorCorrection look. Pure numbers only (no Instances): src/server/CaveLighting.luau builds
-- the FX parts and lights from this, src/client/CaveAtmosphere.luau applies the look while the player is inside,
-- and tools/verify_cave_lighting.py runs the same functions offline. Everything is PROVISIONAL (docs/104 s4, owner judges by eye).
-- FX NOTE: the light-shaft beams are lighting FX built from neutral, 90 percent transparent Parts (no mesh, no Neon). They are NOT
-- model art; the tapered cone mesh (`cave_light_cone`, BD-282) replaces them later.
local Layout = require(script.Parent.CaveHubLayout)
local Rules = {}
Rules.Version = 1
Rules.BeamColor = {255, 236, 190} -- warm cream
Rules.Beam = {outerFrac = 0.82, coreFrac = 0.5, outerAlpha = 0.95, coreAlpha = 0.9, topAbove = 3, bottomAbove = 0.15, motesPerSecond = 4}
Rules.GateGlow = {rate = 4, size = {12, 18}, alpha = 0.7, color = {255, 214, 160}, lift = 8, out = 12} -- out = studs from the pad centre into the mouth (the mouth is open from 10 studs past the pad centre)
Rules.FillColor, Rules.LavaColor, Rules.CrystalColor, Rules.ForgeColor = {255, 214, 170}, {255, 140, 70}, {255, 196, 80}, {255, 190, 90}
Rules.Forge = {period = 4, amplitude = 0.1, base = 0.6}
Rules.ShadowLights = 4
Rules.FxPartBudget = 16 -- shaft beams (2 per hole) + dust volumes (1 per hole) + the gate glow anchor
-- Cave-only look (applied only while the player is inside the hub, restored on leaving; nothing here touches the island).
Rules.Look = {
    -- BD-398: a lit cave, not a bright hall: low warm-dim ambient, lower Lighting.Brightness and exposure; the lamps and shafts are the main lights
    ambient = {70, 62, 60}, outdoorAmbient = {66, 58, 56}, colorShiftTop = {255, 222, 180}, exposure = -0.25, brightness = 1.3, shadowSoftness = 0.35,
    fogStart = 110, fogEnd = 400, fogColor = {72, 56, 46},
    atmosphere = {density = 0.22, offset = 0, haze = 0.25, glare = 0, color = {214, 188, 160}, decay = {150, 104, 72}},
    grade = {brightness = -0.1, contrast = 0.1, saturation = -0.12, tint = {255, 226, 196}}, -- one soft shared warm grade tames the pastel props (MeshPart.Color is ignored on textured meshes)
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
    -- BD-398: PointLight.Shadows only for the 4 strongest lights (brightness x range), the rest stay shadowless (cheap)
    local order = {}
    for i = 1, #lights do order[i] = i end
    table.sort(order, function(a, b) return lights[a].brightness * lights[a].range > lights[b].brightness * lights[b].range end)
    for i = 1, math.min(Rules.ShadowLights, #order) do lights[order[i]].shadows = true end
    local g = L.gate
    cache = {shafts = shafts, lights = lights,
        gate = {x = gate.x, z = gate.z + cz - Rules.GateGlow.out, y = FY + Rules.GateGlow.lift, mouthWidth = g.mouthWidth},
        fxParts = #shafts * 3 + 1}
    return cache
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
