--!strict
-- Audio mixer (docs/87: sounds are calm and quiet). Three SoundGroups under SoundService: Master, with Sfx and Ambience
-- inside it, so master x channel always multiplies. Every game sound (Sfx.play, WeatherAudio, HatchPresentation) sets
-- sound.SoundGroup from AudioMixer.group(...), so nothing bypasses the sliders. Levels are SESSION-ONLY (not saved to the
-- profile: no migration); the defaults come back on every join. The maths below is pure; only group() touches Instances.
local Mixer = {}

local defaults: {[string]: number} = {master = 0.8, sfx = 0.7, ambience = 0.6}
local labels: {[string]: string} = {master = "Everything", sfx = "Sounds", ambience = "Weather"}
local groupNames: {[string]: string} = {master = "BeDinoMaster", sfx = "BeDinoSfx", ambience = "BeDinoAmbience"}
Mixer.Defaults = table.freeze(defaults)
Mixer.Order = table.freeze({"master", "sfx", "ambience"})
Mixer.Labels = table.freeze(labels)
Mixer.GroupNames = table.freeze(groupNames)

local levels: {[string]: number} = {master = defaults.master, sfx = defaults.sfx, ambience = defaults.ambience}
local groups: {[string]: any} = {}

-- Pure: clamp to 0..1 and snap to Step; non-numbers and NaN fall back to `fallback` (or 0).
function Mixer.clamp(value: any, fallback: number?): number
    if typeof(value) ~= "number" or value ~= value then return fallback or 0 end
    local v = math.clamp(value, 0, 1)
    return math.clamp(math.floor(v * 10 + 0.5) / 10, 0, 1) -- tenths: dividing (not multiplying by 0.1) keeps 0.6 exactly 0.6
end
-- Pure: what a sound with base volume `base` is finally heard at (master x channel x base).
function Mixer.effective(master: number, channel: number, base: number): number
    return math.clamp(master, 0, 1) * math.clamp(channel, 0, 1) * base
end
-- Pure: percent text for the Settings screen.
function Mixer.percent(value: number): string
    return string.format("%d%%", math.floor(value * 100 + 0.5))
end
-- Pure: slider fraction (0..1 across the track) to a snapped level.
function Mixer.fromFraction(fraction: number): number
    return Mixer.clamp(fraction, 0)
end

function Mixer.get(key: string): number
    return levels[key] or 0
end

local function sync()
    for key, group in groups do
        local ok = pcall(function() group.Volume = levels[key] end)
        if not ok then groups[key] = nil end
    end
end

-- Returns (creating on first use) the SoundGroup for "master" | "sfx" | "ambience", or nil outside Roblox. Never throws.
function Mixer.group(key: string): any
    local existing = groups[key]
    if existing and existing.Parent then return existing end
    local ok, result = pcall(function()
        local soundService = game:GetService("SoundService")
        local function make(k: string, parent: Instance): any
            local found = groups[k]
            if found and found.Parent then return found end
            local g = parent:FindFirstChild(Mixer.GroupNames[k])
            if not g then
                g = Instance.new("SoundGroup")
                g.Name = Mixer.GroupNames[k]
                g.Parent = parent
            end
            g.Volume = levels[k]
            groups[k] = g
            return g
        end
        local master = make("master", soundService)
        if key == "master" then return master end
        return make(key, master)
    end)
    return if ok then result else nil
end

function Mixer.set(key: string, value: any): number
    if levels[key] == nil then return 0 end
    levels[key] = Mixer.clamp(value, levels[key])
    sync()
    return levels[key]
end
function Mixer.reset()
    for key, value in Mixer.Defaults do levels[key] = value end
    sync()
end

-- Assign a sound to a channel. Safe to call anywhere; a missing group just leaves the sound ungrouped.
function Mixer.attach(sound: any, key: string)
    local group = Mixer.group(key)
    if group then pcall(function() sound.SoundGroup = group end) end
end

return Mixer
