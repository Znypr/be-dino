--!strict
-- BD-1314 (docs/250 S1; owner 2026-11-23: "Yes, build S1"; decisions docs/250 s7): the WHOLE World V3 island is one biome at a time. Every
-- `Seconds` the biome changes in a fixed loop (Order). A warning comes first, then a short storm themed by the arriving biome hides the swap.
-- Server time drives it (workspace:GetServerTimeNow / os.time), so every server and every client agrees without messages.
-- Pure data and math, no Instances: BiomeService (server: attributes, terrain colours), WeatherVisuals (client: light, fog, grade, storm,
-- title cards), PhoneHud (banner words) and tools/verify_biome_rotation.py all read this module.
-- Active only while Config.WorldV3Enabled and Config.BiomeRotationEnabled are both true; off = nothing changes anywhere.
-- Every colour and timing is PROVISIONAL (docs/250); the looks come from ChatGPT's preset table (docs/evidence/2026-11-23-biome-overhaul),
-- with fog and haze pushed back after the first Studio pass (2026-11-23: ChatGPT's distances hid the island beyond about 150 studs).
local BiomeRotation = {}

BiomeRotation.Order = {"meadow", "jungle", "desert", "tundra", "volcano"}
BiomeRotation.Names = {meadow = "Sunny Meadow", jungle = "Jungle", desert = "Desert Canyon", tundra = "Frozen Tundra", volcano = "Volcano"}
BiomeRotation.Seconds = 480 -- owner pick: 8 minutes per biome
BiomeRotation.Warn = 30 -- the "STORM INCOMING" warning before the storm starts
BiomeRotation.StormHalf = 12 -- the storm runs this long either side of the change
BiomeRotation.BlendHalf = 6 -- the look (light, fog, terrain colours) blends this long either side of the change, inside the storm
-- The storm that brings each biome in: an existing weather look and rig (docs/84). A real sandstorm rig is S4 (BD-1317).
BiomeRotation.StormFor = {meadow = "rain", jungle = "rain", desert = "quake", tundra = "blizzard", volcano = "volcano"}
-- Featured dinos (S3, BD-1316, not used yet): about x2 hatch chance in their biome, every dino stays hatchable everywhere.
BiomeRotation.Featured = {
    meadow = {"triceratops", "pachycephalosaurus", "compy"},
    jungle = {"raptor", "parasaurolophus", "brachiosaurus", "microraptor"},
    desert = {"stegosaurus", "gallimimus", "ankylosaurus"},
    tundra = {"therizinosaurus", "pteranodon", "ichthyosaurus"},
    volcano = {"tyrannosaurus", "spinosaurus", "baryonyx"},
}

-- Look per biome, {r,g,b} 0..255 (ChatGPT text table, docs/250 s5, toned for Roblox):
--   sun = Lighting.ColorShift_Top (sunlit side), horizon = Atmosphere.Color, skyTop = Atmosphere.Decay, ambient = Ambient / OutdoorAmbient,
--   fog = FogColor with fogStart / fogEnd in studs (the near 25 studs stay clear, docs/84), tint / sat / contrast = the colour grade,
--   bloom = BloomEffect intensity, density / haze = Atmosphere.
export type Look = {sun: {number}, horizon: {number}, skyTop: {number}, ambient: {number}, fog: {number}, fogStart: number, fogEnd: number,
    tint: {number}, sat: number, contrast: number, bloom: number, density: number, haze: number}
BiomeRotation.Looks = {
    meadow = {sun = {255, 240, 184}, horizon = {216, 244, 255}, skyTop = {90, 174, 255}, ambient = {166, 201, 179}, fog = {198, 233, 216},
        fogStart = 160, fogEnd = 900, tint = {255, 252, 242}, sat = .1, contrast = .02, bloom = .15, density = .25, haze = .3},
    jungle = {sun = {184, 255, 242}, horizon = {188, 235, 221}, skyTop = {19, 127, 134}, ambient = {57, 122, 104}, fog = {123, 185, 168},
        fogStart = 90, fogEnd = 520, tint = {232, 255, 246}, sat = .08, contrast = .04, bloom = .15, density = .3, haze = .7},
    desert = {sun = {255, 224, 161}, horizon = {255, 207, 141}, skyTop = {101, 156, 218}, ambient = {220, 167, 120}, fog = {231, 176, 120},
        fogStart = 120, fogEnd = 700, tint = {255, 236, 210}, sat = -.04, contrast = .06, bloom = 0, density = .3, haze = .6},
    tundra = {sun = {226, 245, 255}, horizon = {232, 248, 255}, skyTop = {121, 195, 245}, ambient = {156, 199, 232}, fog = {213, 236, 250},
        fogStart = 110, fogEnd = 620, tint = {236, 246, 255}, sat = -.08, contrast = .02, bloom = .15, density = .3, haze = .5},
    volcano = {sun = {255, 148, 91}, horizon = {242, 105, 54}, skyTop = {87, 52, 79}, ambient = {117, 80, 87}, fog = {144, 93, 84},
        fogStart = 80, fogEnd = 460, tint = {255, 226, 214}, sat = -.1, contrast = .08, bloom = .35, density = .36, haze = 1},
}
-- Terrain colours per biome over the toon flat map (WorldToon.Palette keys; meadow = the toon palette itself). Paths and the plaza (Limestone)
-- stay a readable warm sand in every biome (ChatGPT rule: keep the sandy path). Channels stay <= 245 (the soft-colour rule, verify_world_look).
BiomeRotation.Terrain = {
    jungle = {Grass = {58, 170, 72}, LeafyGrass = {40, 140, 70}, Sand = {206, 182, 122}, Limestone = {226, 186, 118}, Ground = {120, 90, 60},
        Mud = {96, 74, 52}, Rock = {112, 134, 112}, Slate = {104, 124, 112}, Basalt = {84, 92, 84}, Sandstone = {170, 150, 100}},
    desert = {Grass = {226, 170, 98}, LeafyGrass = {208, 152, 86}, Sand = {245, 198, 122}, Limestone = {245, 205, 140}, Ground = {204, 124, 76},
        Mud = {170, 106, 70}, Rock = {198, 114, 78}, Slate = {172, 112, 92}, Basalt = {150, 96, 80}, Sandstone = {216, 122, 76}},
    tundra = {Grass = {226, 240, 245}, LeafyGrass = {204, 226, 244}, Sand = {236, 240, 245}, Limestone = {226, 216, 196}, Ground = {172, 182, 198},
        Mud = {152, 162, 178}, Rock = {162, 186, 208}, Slate = {152, 172, 198}, Basalt = {122, 132, 152}, Sandstone = {202, 212, 226}},
    volcano = {Grass = {98, 86, 82}, LeafyGrass = {86, 76, 74}, Sand = {152, 122, 102}, Limestone = {206, 156, 112}, Ground = {92, 72, 68},
        Mud = {72, 58, 56}, Rock = {72, 66, 72}, Slate = {66, 62, 70}, Basalt = {44, 38, 44}, Sandstone = {132, 82, 66}},
}

function BiomeRotation.enabled(config: any): boolean
    return type(config) == "table" and config.WorldV3Enabled == true and config.BiomeRotationEnabled == true
end

local function finite(x: number): number return if x == x and math.abs(x) < 1e12 then x else 0 end

-- The biome clock's time: server time plus a Studio-only test offset (workspace attribute BiomeTestOffset, seconds) so QA can picture every
-- biome without waiting; outside Studio the offset is always ignored, so a live server can never be shifted.
function BiomeRotation.clock(serverNow: number, offset: any, isStudio: boolean): number
    return finite(serverNow) + (if isStudio and type(offset) == "number" then finite(offset) else 0)
end

-- The biome loop at server time t (seconds): current biome, the next one, when it changes, and the phase.
-- phase: "storm" within StormHalf of a change (arriving = the biome the storm brings), "warning" the Warn seconds before that, else "calm".
export type State = {id: string, next: string, previous: string, changeAt: number, phase: string, arriving: string, left: number}
function BiomeRotation.state(t: number): State
    t = finite(t)
    local n, len = #BiomeRotation.Order, BiomeRotation.Seconds
    local cycle = math.floor(t / len)
    local i = cycle % n
    local id = BiomeRotation.Order[i + 1]
    local nextId = BiomeRotation.Order[(i + 1) % n + 1]
    local previous = BiomeRotation.Order[(i - 1) % n + 1]
    local changeAt = (cycle + 1) * len
    local since, left = t - cycle * len, changeAt - t
    local phase, arriving = "calm", id
    if since < BiomeRotation.StormHalf then
        phase = "storm"
    elseif left <= BiomeRotation.StormHalf then
        phase, arriving = "storm", nextId
    elseif left <= BiomeRotation.StormHalf + BiomeRotation.Warn then
        phase, arriving = "warning", nextId
    end
    return {id = id, next = nextId, previous = previous, changeAt = changeAt, phase = phase, arriving = arriving, left = left}
end

-- The weather id the storm shows at time t (nil outside a storm).
function BiomeRotation.storm(t: number): string?
    local s = BiomeRotation.state(t)
    return if s.phase == "storm" then BiomeRotation.StormFor[s.arriving] else nil
end

-- (from, to, s): the look at time t is from:lerp(to, s). s rises 0 -> 1 across BlendHalf either side of a change; far from a change from = to.
function BiomeRotation.mix(t: number): (string, string, number)
    local s = BiomeRotation.state(t)
    local since = BiomeRotation.Seconds - s.left
    local h = BiomeRotation.BlendHalf
    if s.left < h then return s.id, s.next, (h - s.left) / (2 * h) end
    if since < h then return s.previous, s.id, .5 + since / (2 * h) end
    return s.id, s.id, 1
end

local function lerp(a: number, b: number, s: number): number return a + (b - a) * s end
local function lerpRgb(a: {number}, b: {number}, s: number): {number}
    return {lerp(a[1], b[1], s), lerp(a[2], b[2], s), lerp(a[3], b[3], s)}
end

-- The blended look at time t.
function BiomeRotation.look(t: number): Look
    local from, to, s = BiomeRotation.mix(t)
    local a, b = BiomeRotation.Looks[from], BiomeRotation.Looks[to]
    s = math.clamp(s, 0, 1)
    return {sun = lerpRgb(a.sun, b.sun, s), horizon = lerpRgb(a.horizon, b.horizon, s), skyTop = lerpRgb(a.skyTop, b.skyTop, s),
        ambient = lerpRgb(a.ambient, b.ambient, s), fog = lerpRgb(a.fog, b.fog, s), fogStart = lerp(a.fogStart, b.fogStart, s),
        fogEnd = lerp(a.fogEnd, b.fogEnd, s), tint = lerpRgb(a.tint, b.tint, s), sat = lerp(a.sat, b.sat, s),
        contrast = lerp(a.contrast, b.contrast, s), bloom = lerp(a.bloom, b.bloom, s), density = lerp(a.density, b.density, s),
        haze = lerp(a.haze, b.haze, s)}
end

-- Terrain colour of one material at time t; meadow = `base` (the toon palette colour the terrain painter set).
function BiomeRotation.terrainColor(material: string, base: {number}, t: number): {number}
    local from, to, s = BiomeRotation.mix(t)
    local function of(id: string): {number}
        local kit = BiomeRotation.Terrain[id]
        return (kit and kit[material]) or base
    end
    return lerpRgb(of(from), of(to), math.clamp(s, 0, 1))
end

-- HUD banner words while the weather is clear: "Jungle!" and "Desert Canyon in 3 min" (kid timer words, docs/72; duration = PhoneHudLayout.duration).
function BiomeRotation.bannerWords(t: number, duration: (number) -> string): (string, string)
    local s = BiomeRotation.state(t)
    if s.phase == "storm" then return "Storm!", BiomeRotation.Names[s.arriving] .. " is coming" end
    return BiomeRotation.Names[s.id] .. "!", BiomeRotation.Names[s.next] .. " in " .. duration(s.left)
end

return BiomeRotation
