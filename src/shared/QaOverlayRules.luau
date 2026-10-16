--!strict
-- BD-085 / BD-322 phone QA kit (docs/127). Pure rules for the owner-only QA overlay: who may see it, the tour step labels,
-- and the validation of a client snapshot before the server prints it as a [BD-QA] line. No Roblox services here.
-- The overlay changes no gameplay; it is OFF in every committed build (Config.QaOverlayEnabled, pinned by release_profiles.py).
local Rules = {}

Rules.LogTag = "[BD-QA]"
Rules.MaxLabel = 40
Rules.MinSecondsBetweenMarks = 0.5

-- Tour steps in the order of docs/127 section 3. The overlay's "Step" button cycles through these; "Mark" logs the current one.
Rules.Steps = table.freeze({
    "start_hub", "run_start", "food_field", "egg_reveal_15", "rare_hatch", "goals_panel", "peaceful_button",
    "settings", "sound_lab", "class_picker", "shops", "end",
})

-- Numeric fields of a snapshot: {lo, hi}. Anything outside is clamped, NaN or non-numbers are dropped to nil.
Rules.Fields = (table.freeze({
    fps = {0, 1000}, memMb = {0, 100000}, instances = {0, 5e7}, parts = {0, 5e7}, emitters = {0, 1e6},
    particleRate = {0, 1e7}, beams = {0, 1e6}, lights = {0, 1e6}, editableMiB = {0, 100000}, editableLive = {0, 100000},
    pingMs = {0, 60000}, dinos = {0, 1000}, viewW = {0, 20000}, viewH = {0, 20000},
}) :: any) :: {[string]: {number}}
Rules.FieldOrder = table.freeze({
    "fps", "memMb", "instances", "parts", "emitters", "particleRate", "beams", "lights", "editableMiB", "editableLive",
    "pingMs", "dinos", "viewW", "viewH",
})

export type Identity = {userId: number, allowedIds: {number}?, unpublishedStudio: boolean, enabled: boolean}

-- Studio (unpublished) or an explicit UserId, and only while the flag is on. Nobody otherwise, including the place owner.
function Rules.allowed(identity: Identity): boolean
    if not identity.enabled or typeof(identity.userId) ~= "number" then return false end
    if identity.unpublishedStudio then return true end
    if identity.userId <= 0 then return false end
    return identity.allowedIds ~= nil and table.find(identity.allowedIds, identity.userId) ~= nil
end

local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end

-- Returns a clean snapshot or nil. Label is cut to MaxLabel and limited to [A-Za-z0-9_ .-] so the log line stays one safe JSON line.
function Rules.sanitize(raw: any): {[string]: any}?
    if typeof(raw) ~= "table" then return nil end
    local label = raw.label
    if typeof(label) ~= "string" then label = "mark" end
    label = string.sub(string.gsub(label :: string, "[^%w_%.%- ]", ""), 1, Rules.MaxLabel)
    if label == "" then label = "mark" end
    local out: {[string]: any} = {label = label}
    for _, key in Rules.FieldOrder do
        local value = raw[key]
        if finite(value) then
            local spec = Rules.Fields[key]
            out[key] = math.floor(math.clamp(value :: number, spec[1], spec[2]) * 100 + 0.5) / 100
        end
    end
    if typeof(raw.touch) == "boolean" then out.touch = raw.touch end
    return out
end

-- Rate limit: true when this mark may be logged.
function Rules.mayMark(lastMarkClock: number?, now: number): boolean
    return lastMarkClock == nil or now - lastMarkClock >= Rules.MinSecondsBetweenMarks
end

-- Overlay display lines (short, monospace friendly).
function Rules.lines(s: {[string]: any}): {string}
    local function n(key: string, fmt: string): string return if s[key] ~= nil then string.format(fmt, s[key]) else "?" end
    return {
        string.format("fps %s  ping %s ms", n("fps", "%.0f"), n("pingMs", "%.0f")),
        string.format("mem %s MB  inst %s  parts %s", n("memMb", "%.0f"), n("instances", "%.0f"), n("parts", "%.0f")),
        string.format("emit %s  rate %s/s  beams %s  lights %s", n("emitters", "%.0f"), n("particleRate", "%.0f"), n("beams", "%.0f"), n("lights", "%.0f")),
        string.format("EditableImage %s MiB (%s live)  dinos %s", n("editableMiB", "%.1f"), n("editableLive", "%.0f"), n("dinos", "%.0f")),
    }
end

return table.freeze(Rules)
