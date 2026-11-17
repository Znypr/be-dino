--!strict
-- BD-1247 (owner 2026-11-16 "game still looks empty": the light is flat and even, the scene reads plain): a warmer, slightly more saturated
-- colour grade, gentle bloom on highlights, soft sun rays and slow floating pollen / light motes per World V3 zone. Calm (docs/87): small
-- numbers, slow motes, nothing flashes. Played by src/client/WarmLight.client.luau ONLY while Config.WarmLightEnabled and WorldV3Enabled.
-- The look is its own post effects (WarmGrade / WarmBloom / WarmRays) that fade to nothing in other weather (the weather owns the mood then),
-- off the island (cave hub) and, for the motes, with Reduce Motion. Pure data and rules, no Instances (tools/verify_warm_light.py runs it).
-- Motes use textures already uploaded for the FX (Shared/EffectAssets glowPlate, ashFlake); nothing new is drawn by code.
local WarmLight = {}

function WarmLight.enabled(config: any): boolean
    return type(config) == "table" and config.WarmLightEnabled == true and config.WorldV3Enabled == true
end

WarmLight.FadeSeconds = 3
-- Added on top of the weather grade (ColorCorrection effects stack). Clear weather's own grade is saturation +.04, contrast 0 (WeatherLooks).
WarmLight.Grade = {tint = {255, 239, 216}, saturation = .2, contrast = .08, brightness = .02} -- Studio A/B: .12 / 245,230 was hard to see
WarmLight.Bloom = {intensity = .4, size = 26, threshold = .86} -- only the brightest highlights (sun on water, white petals) glow a little
WarmLight.Rays = {intensity = .06, spread = .35} -- soft rays when the sun is in view

-- Motes per zone: texture key (EffectAssets), colours, rate per second (desktop), lifetime range (s), size range (studs), light emission.
WarmLight.Motes = {
    meadow = {texture = "glowPlate", colors = {{255, 236, 140}, {255, 250, 210}}, rate = 10, life = {8, 12}, size = {.2, .34}, emission = .45},
    forest = {texture = "glowPlate", colors = {{214, 240, 150}, {255, 244, 190}}, rate = 9, life = {9, 13}, size = {.2, .32}, emission = .5},
    pine = {texture = "glowPlate", colors = {{250, 250, 240}, {226, 238, 255}}, rate = 7, life = {9, 13}, size = {.22, .36}, emission = .3},
    beach = {texture = "glowPlate", colors = {{255, 246, 214}, {255, 255, 255}}, rate = 6, life = {7, 10}, size = {.18, .3}, emission = .4},
    volcano = {texture = "ashFlake", colors = {{150, 140, 136}, {255, 170, 110}}, rate = 7, life = {7, 10}, size = {.26, .44}, emission = .15},
}
WarmLight.Order = table.freeze({"meadow", "forest", "pine", "beach", "volcano"})
WarmLight.Box = {x = 64, y = 18, z = 64} -- emission volume around the camera (studs); particles stay in the world (not locked to it)
WarmLight.Ahead = 18 -- the box sits this far ahead of the camera, so most motes are in view
WarmLight.Density = {Desktop = 1, Tablet = .75, Phone = .5}

-- 0..1 target of the whole look: on the island in clear weather only.
function WarmLight.target(weatherId: any, onIsland: boolean): number
    return if onIsland and (weatherId == nil or weatherId == "clear") then 1 else 0
end
-- Eased step of a level toward its target over FadeSeconds.
function WarmLight.step(level: number, target: number, dt: number): number
    local rate = dt / WarmLight.FadeSeconds
    if level < target then return math.min(target, level + rate) end
    return math.max(target, level - rate)
end
-- Rate of one zone's motes for a device class and the zone's 0..1 weight.
function WarmLight.rateFor(zone: string, deviceClass: string, weight: number): number
    local m = WarmLight.Motes[zone]
    if not m then return 0 end
    return m.rate * (WarmLight.Density[deviceClass] or WarmLight.Density.Phone) * math.clamp(weight, 0, 1)
end
-- Particles alive at once at full weight in the busiest zone (rate x mean lifetime): the FX budget input (docs/126, fx_budget_report).
function WarmLight.liveParticles(deviceClass: string): number
    local worst = 0
    for _, zone in WarmLight.Order do
        local m = WarmLight.Motes[zone]
        worst = math.max(worst, WarmLight.rateFor(zone, deviceClass, 1) * (m.life[1] + m.life[2]) / 2)
    end
    return worst
end

return WarmLight
