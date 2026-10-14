--!strict
-- BD-120 owner admin panel: pure rules shared by AdminService (server) and AdminPanel (client).
-- The server is the only authority; the client uses these values for display and slider snapping.
local Rules = {}

-- Runtime-only sliders. Values are never written to player profiles and reset when the server restarts.
export type Setting = {label: string, min: number, max: number, step: number, default: number, group: string?, unit: string?}
local settings: {[string]: Setting} = {
    foodMultiplier = {label = "Food worth", min = 0.5, max = 10, step = 0.5, default = 1},
    growthMultiplier = {label = "Growth speed", min = 0.5, max = 5, step = 0.5, default = 1},
    speedMultiplier = {label = "Run speed", min = 0.5, max = 3, step = 0.25, default = 1},
    -- "Feel" tuning (runtime only). Defaults mirror Config so Reset restores the shipped feel.
    gravity = {label = "Gravity", min = 150, max = 400, step = 10, default = 250, group = "feel", unit = ""},
    jumpPower = {label = "Jump power", min = 40, max = 90, step = 2, default = 56, group = "feel", unit = ""},
    moveResponsiveness = {label = "Turn/stop responsiveness", min = 0.5, max = 2, step = 0.25, default = 1, group = "feel"},
    turnLean = {label = "Turn lean", min = 0, max = 3, step = 0.25, default = 1, group = "feel"},
    leapSpeed = {label = "Leap speed", min = 0.5, max = 1.5, step = 0.1, default = 1, group = "feel"},
}
Rules.Settings = table.freeze(settings)
Rules.SettingOrder = table.freeze({"foodMultiplier", "growthMultiplier", "speedMultiplier", "gravity", "jumpPower", "moveResponsiveness", "turnLean", "leapSpeed"})
Rules.WeatherMinSeconds = 15
Rules.WeatherMaxSeconds = 1800
Rules.Actions = table.freeze({"set", "startWeather", "stopWeather", "reset"})

local function finite(value: any): boolean
    return typeof(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end

-- Clamp and snap a slider value. nil for unknown keys or non-finite input.
function Rules.sanitize(key: any, value: any): number?
    if typeof(key) ~= "string" then return nil end
    local spec = Rules.Settings[key]
    if not spec or not finite(value) then return nil end
    local snapped = spec.min + math.floor((math.clamp(value, spec.min, spec.max) - spec.min) / spec.step + 0.5) * spec.step
    return math.clamp(snapped, spec.min, spec.max)
end

-- Slider fraction 0..1 to a snapped value (client display) and back.
function Rules.fromFraction(key: string, fraction: number): number
    local spec = Rules.Settings[key]
    return Rules.sanitize(key, spec.min + math.clamp(fraction, 0, 1) * (spec.max - spec.min)) or spec.default
end
function Rules.toFraction(key: string, value: number): number
    local spec = Rules.Settings[key]
    return (math.clamp(value, spec.min, spec.max) - spec.min) / (spec.max - spec.min)
end

function Rules.weatherSeconds(value: any, fallback: number): number?
    if value == nil then return fallback end
    if not finite(value) then return nil end
    return math.clamp(math.floor(value), Rules.WeatherMinSeconds, Rules.WeatherMaxSeconds)
end

function Rules.format(value: number, key: string?): string
    local spec = if key then Rules.Settings[key] else nil
    if spec and spec.unit then return string.format("%g", value) end
    return if value == math.floor(value) then string.format("x%d", value) else string.format("x%g", value)
end

-- Who may use the panel. groupRank is only consulted for group-owned experiences.
export type Identity = {
    userId: number,
    creatorType: string, -- "User" | "Group"
    creatorId: number,
    groupRank: number?,
    adminIds: {number}?,
    unpublishedStudio: boolean,
    enabled: boolean,
}
function Rules.isAdmin(identity: Identity): boolean
    if not identity.enabled or typeof(identity.userId) ~= "number" then return false end
    -- Unpublished Studio copies (GameId 0) include local test servers whose players have negative ids.
    if identity.unpublishedStudio then return true end
    if identity.userId <= 0 then return false end
    if identity.adminIds and table.find(identity.adminIds, identity.userId) then return true end
    if identity.creatorId <= 0 then return false end
    if identity.creatorType == "User" then return identity.userId == identity.creatorId end
    if identity.creatorType == "Group" then return identity.groupRank == 255 end
    return false
end

return table.freeze(Rules)
