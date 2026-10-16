--!strict
-- Settings v2 model (BD-263..266, docs/103). Pure data rules plus a tiny in-memory current value with change listeners.
-- Saved PER PLAYER as the additive profile field `settings` (no schema bump, like revealSkip): old profiles have no field
-- and read as defaults; any bad value falls back to its default. Instances are never touched here: SettingsSync.client
-- applies changes (Theme.MotionEnabled, AudioMixer) and sends them to the server.
local Model = {}

export type Settings = {
    master: number, sfx: number, ambience: number, -- 0..1 in tenths (AudioMixer scale)
    effects: string, weather: string, -- "full" | "lite" | "off"
    calm: boolean, -- Calm motion = Reduce Motion
    jumpSize: string, -- "small" | "normal" | "big" (no consumer yet: stored for the phone jump button)
    teleportShops: boolean, -- BD-288 (docs/104 s7.6): true (default) = rail buttons teleport to the shop; false = just open the menu (moss-trail guide: BD-289)
}

Model.Tabs = table.freeze({"sound", "look", "controls", "help"})
Model.TabLabels = table.freeze({sound = "SOUND", look = "LOOK", controls = "CONTROLS", help = "HELP"})
Model.Levels = table.freeze({"full", "lite", "off"})
Model.JumpSizes = table.freeze({"small", "normal", "big"})
Model.Defaults = table.freeze({master = 0.8, sfx = 0.7, ambience = 0.6, effects = "full", weather = "full", calm = false, jumpSize = "normal", teleportShops = true})
-- Particle share per level (consumers multiply their emitter rate by this).
Model.LevelFactor = table.freeze({full = 1, lite = 0.5, off = 0})

local function oneOf(list: {string}, value: any, fallback: string): string
    if typeof(value) == "string" and table.find(list, value) then return value end
    return fallback
end
-- 0..1 snapped to tenths; non-numbers and NaN give the fallback.
local function volume(value: any, fallback: number): number
    if typeof(value) ~= "number" or value ~= value then return fallback end
    return math.clamp(math.floor(math.clamp(value, 0, 1) * 10 + 0.5) / 10, 0, 1)
end

-- Any value (nil, junk, old profile without the field) to a complete valid settings table.
function Model.normalize(raw: any): Settings
    local d = Model.Defaults
    local t: any = if typeof(raw) == "table" then raw else {}
    local sound: any = if typeof(t.sound) == "table" then t.sound else {}
    return {
        master = volume(sound.master, d.master), sfx = volume(sound.sfx, d.sfx), ambience = volume(sound.ambience, d.ambience),
        effects = oneOf(Model.Levels, t.effects, d.effects),
        weather = oneOf(Model.Levels, t.weather, d.weather),
        calm = t.calm == true,
        jumpSize = oneOf(Model.JumpSizes, t.jumpSize, d.jumpSize),
        teleportShops = t.teleportShops ~= false, -- default ON; only an explicit false turns it off
    }
end

-- The plain primitive table written to profile.settings (and what the client sends).
function Model.toStore(s: Settings): {[string]: any}
    return {
        v = 1,
        sound = {master = s.master, sfx = s.sfx, ambience = s.ambience},
        effects = s.effects, weather = s.weather, calm = s.calm, jumpSize = s.jumpSize, teleportShops = s.teleportShops,
    }
end
function Model.fromStore(raw: any): Settings
    return Model.normalize(raw)
end

function Model.equal(a: Settings, b: Settings): boolean
    return a.master == b.master and a.sfx == b.sfx and a.ambience == b.ambience and a.effects == b.effects
        and a.weather == b.weather and a.calm == b.calm and a.jumpSize == b.jumpSize and a.teleportShops == b.teleportShops
end

-- Fast mode is derived: on exactly when both Effects and Weather are Lite.
function Model.isFast(s: Settings): boolean
    return s.effects == "lite" and s.weather == "lite"
end

function Model.factor(level: any): number
    return Model.LevelFactor[if typeof(level) == "string" then level else "full"] or 1
end

-- In-memory current value, readable from any client module (pure getters; no Roblox services).
local current: Settings = Model.normalize(nil)
local listeners: {(Settings) -> ()} = {}
function Model.get(): Settings return current end
function Model.effects(): string return current.effects end
function Model.weather(): string return current.weather end
function Model.calm(): boolean return current.calm end
function Model.jumpSize(): string return current.jumpSize end
function Model.teleportShops(): boolean return current.teleportShops end
function Model.onChange(fn: (Settings) -> ()) table.insert(listeners, fn) end

-- Replace the current value (e.g. loaded from the server). Returns true when anything changed.
function Model.load(raw: any): boolean
    local n = Model.normalize(raw)
    if Model.equal(n, current) then return false end
    current = n
    for _, fn in listeners do pcall(fn, current) end
    return true
end
-- Change one option by key; bad values are ignored. "fast" is the Fast mode switch (Lite/Lite on, Full/Full off).
function Model.set(key: string, value: any): Settings
    local n: any = table.clone(current)
    if key == "fast" then
        n.effects = if value == true then "lite" else "full"
        n.weather = n.effects
    elseif key == "master" or key == "sfx" or key == "ambience" then n[key] = volume(value, n[key])
    elseif key == "effects" or key == "weather" then n[key] = oneOf(Model.Levels, value, n[key])
    elseif key == "calm" then n.calm = value == true
    elseif key == "jumpSize" then n.jumpSize = oneOf(Model.JumpSizes, value, n.jumpSize)
    elseif key == "teleportShops" then n.teleportShops = value == true end
    Model.load(Model.toStore(n))
    return current
end
function Model.reset() Model.load(nil) end

return Model
