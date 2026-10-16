--!strict
-- BD-131 reader: which Blender weather texture a weather rig uses, and how that rig is tuned FOR that texture.
-- Pure data and rules (no Roblox types, no services), so tools/verify_weather.py runs it offline with the real EffectAssets.
--
-- Rule (AGENTS.md / docs/120): a slot in EffectAssets.Requested holds "" until the owner uploads the PNG. While it is empty
-- plan() returns nil and WeatherVisuals keeps EXACTLY the built-in sprite and settings it had before (same Texture, Size, Squash,
-- Transparency, LightEmission, rate; no extra Instance is created). Once the id is valid, plan() returns the texture, the
-- flipbook layout / mode from EffectAssets.Sheets / FlipbookMode, and the tuning below.
--
-- Tuning[textureKey][rigName] is applied ONLY while that texture is in use. Fields (all optional; a missing field keeps the built-in value):
--   sizeScale      multiplies every keypoint of the rig's built-in Size sequence (the Blender cells carry padding around the shape)
--   squash         {a, b} replaces the Squash sequence (the rain art is already a thin streak, so it needs far less stretch than the smoke blob)
--   transparency   {a, b[, c]} replaces the Transparency sequence
--   lightEmission  replaces LightEmission
--   rate           multiplier of the built-in rate. Never above 1: the Blender art may cost fewer particles, never more (verify_weather)
-- Bolt / moon fields are listed with their rig. ALL numbers are PROVISIONAL: they are first guesses from the 128 px cells and need a
-- lead Studio look per event (BD-131), and the squash values assume the 1:4 rain art maps onto the square particle quad.
local WT = {}

-- Textures read by the weather rigs, in the order WeatherVisuals builds them. rig names are the WeatherLooks.Rigs names (or a pooled one-shot).
WT.Keys = table.freeze({"rainStreak", "lightningBolt", "snowFlakeSheet", "ashFlake", "emberSpark", "dustSand", "auroraCurtain", "bloodMoonMotes", "bloodMoonDisc"})

WT.Tuning = table.freeze({
    -- 64x256 thin streak, bright head at the bottom, tail fades up. Rain and Thunderstorm share the numbers (thunder keeps its larger built-in size through sizeScale).
    rainStreak = table.freeze({
        streaks = table.freeze({sizeScale = 2.2, squash = {-4, -4}, transparency = {.2, .05}, lightEmission = .6, rate = 1}),
        near = table.freeze({sizeScale = 2.2, squash = {-4, -4}, transparency = {.15, .04}, lightEmission = .7, rate = 1}),
    }),
    -- 512x128 strip, jagged bolt with glow and forks, tiles along the beam. ONE trunk Beam (instead of 18 segment beams) plus the 2 forks per bolt.
    -- tile = studs of beam per texture repeat, as a multiple of the width (the strip is 4:1, so 4 keeps the art undistorted).
    lightningBolt = table.freeze({
        trunk = table.freeze({width = 26, tile = 4, color = {205, 195, 255}, transparency = .08, lightEmission = 1, curve = 14, segments = 8}),
        fork = table.freeze({width = 11, tile = 4, color = {225, 215, 255}, transparency = .12, lightEmission = 1}),
    }),
    -- 16 flakes (dendrites, plates, needles, pellets), a random one per particle
    snowFlakeSheet = table.freeze({
        snow = table.freeze({sizeScale = 1.7, rate = .8}),
    }),
    -- 16 charred flakes with mottled alpha; the built-in tint stays dark grey
    ashFlake = table.freeze({
        ash = table.freeze({sizeScale = 1.6, rate = .9, transparency = {.4, .25, .9}}),
    }),
    -- 16 glowing beads / streaks; the volcano embers and the lava impact sparks
    emberSpark = table.freeze({
        embers = table.freeze({sizeScale = 1.8, lightEmission = 1, rate = .9}),
        sparks = table.freeze({sizeScale = 1.6, lightEmission = 1, rate = 1}),
    }),
    -- 16 dust and sand sprays; replaces the fx3 smoke flipbook in the quake dust (ambient dust, crack puffs, feet puff)
    dustSand = table.freeze({
        dust = table.freeze({sizeScale = 1, transparency = {.7, .55, 1}, rate = .9}),
        crackDust = table.freeze({sizeScale = 1, transparency = {.5, .62, 1}, rate = 1}),
        feetPuff = table.freeze({sizeScale = 1, transparency = {.45, .6, 1}, rate = 1}),
    }),
    -- 16-frame looping curtain: a NEW sky emitter (the Beam ribbons stay). Only built while the texture is in use.
    auroraCurtain = table.freeze({
        curtain = table.freeze({size = {120, 170, 210}, transparency = {1, .8, 1}, lightEmission = 1, rate = 1}),
    }),
    -- 16 soft orbs, bubble rings, teardrops; replaces the blood moon sparkle motes
    bloodMoonMotes = table.freeze({
        motes = table.freeze({sizeScale = 2, lightEmission = 1, rate = .9}),
    }),
    -- 512 px moon disc with craters, crimson tint. Replaces the Neon ball core (halos stay). scale = disc size as a multiple of Moon.core.
    bloodMoonDisc = table.freeze({
        disc = table.freeze({scale = 1.5, color = {255, 120, 110}, transparency = .06, beat = .05}),
    }),
})

-- Beam counts the textured bolt costs per slot (the built-in bolt costs 2 layers x 9 segments + 2 forks = 20). verify_weather checks
-- bolts x (trunk + forks) against the phone beam budget in tools/qa/phone_budgets.json.
WT.BoltBeams = table.freeze({trunk = 1, forks = 2})

export type Tune = {[string]: any}
export type Plan = {
    key: string, rig: string, texture: string,
    layout: string, -- Enum.ParticleFlipbookLayout name: "Grid4x4" for a sheet, "None" for a single image
    mode: string?, framerate: number?, startRandom: boolean?, -- sheets only (Enum.ParticleFlipbookMode name)
    tune: Tune,
}

-- nil while the slot is empty (built-in look unchanged). assets = EffectAssets.
function WT.plan(assets: any, key: string, rig: string): Plan?
    if not assets.isReal(key) then return nil end
    local keyTune = (WT.Tuning :: any)[key]
    local tune: Tune = if keyTune and keyTune[rig] then keyTune[rig] else {}
    local sheet = assets.isSheet(key)
    local mode = if sheet then assets.mode(key) else nil
    return {
        key = key, rig = rig, texture = assets.resolve(key),
        layout = if sheet then "Grid4x4" else "None",
        mode = mode, framerate = if mode == "Loop" then assets.LoopFps else nil, startRandom = if sheet then mode ~= "OneShot" else nil,
        tune = tune,
    }
end

-- Multiplier of the rig's built-in rate while the texture is in use (1 without a plan).
function WT.rate(plan: Plan?): number
    if not plan then return 1 end
    return plan.tune.rate or 1
end

-- Effective emit rate of a rig: built-in rate x tuning x Weather level factor (Full 1, Lite .5, Off 0; SettingsModel.factor) x phone density.
-- Reduce Motion (motion = false) emits nothing, exactly like the built-in particles.
function WT.emitRate(base: number, plan: Plan?, levelFactor: number, density: number, motion: boolean): number
    if not motion or levelFactor <= 0 then return 0 end
    return base * WT.rate(plan) * levelFactor * density
end

return WT
