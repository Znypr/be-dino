--!strict
-- Playtest feedback (docs/128): pure shape, clamping, rate limit and log line. No Roblox types, no UserIds, no names.
-- Server: src/server/FeedbackService.luau (filters text, prints the line). Client: src/client/FeedbackClient.client.luau.
local PlaytestFeedback = {}

PlaytestFeedback.LogPrefix = "[BD-FEEDBACK] "
PlaytestFeedback.MinSecondsBetween = 120 -- 1 per 2 min per player
PlaytestFeedback.MaxPerSession = 10
PlaytestFeedback.MaxTextLength = 140
PlaytestFeedback.Locations = {Hub = true, Run = true}

local function rating(raw: any): number
    if typeof(raw) ~= "number" or raw ~= raw then return 0 end
    local n = math.floor(raw + 0.5)
    if n < 1 or n > 3 then return 0 end
    return n
end

-- Client payload -> {fun, level, looks, text} or nil. At least one rating or some text is required.
-- fun: 1 sad, 2 ok, 3 happy. level: 1 too easy, 2 just right, 3 too hard. looks: 1 sad, 2 ok, 3 happy.
function PlaytestFeedback.sanitize(raw: any): {[string]: any}?
    if typeof(raw) ~= "table" then return nil end
    local out: {[string]: any} = {fun = rating(raw.fun), level = rating(raw.level), looks = rating(raw.looks), text = ""}
    local text = raw.text
    if typeof(text) == "string" and utf8.len(text) ~= nil then
        out.text = string.sub(text, 1, PlaytestFeedback.MaxTextLength * 4)
    end
    if out.fun == 0 and out.level == 0 and out.looks == 0 and out.text == "" then return nil end
    return out
end

function PlaytestFeedback.newSession(): {[string]: any}
    return {sent = 0, lastAt = nil, runs = 0}
end

-- Returns true and records the send when allowed; false plus a reason ("wait" or "limit").
function PlaytestFeedback.allow(session: {[string]: any}, now: number): (boolean, string?)
    if session.sent >= PlaytestFeedback.MaxPerSession then return false, "limit" end
    if session.lastAt ~= nil and now - session.lastAt < PlaytestFeedback.MinSecondsBetween then return false, "wait" end
    session.sent += 1
    session.lastAt = now
    return true, nil
end

local function whole(value: any, cap: number): number
    if typeof(value) ~= "number" or value ~= value then return 0 end
    return math.clamp(math.floor(value + 0.5), 0, cap)
end

local function species(raw: any): string
    if typeof(raw) ~= "string" then return "unknown" end
    local clean = string.gsub(string.sub(raw, 1, 32), "[^%w_%-]", "")
    if clean == "" then return "unknown" end
    return clean
end

-- filteredText must already have passed TextService; this only trims length and drops control characters.
function PlaytestFeedback.event(input: {fun: any, level: any, looks: any, filteredText: any, runs: any, location: any, species: any}): {[string]: any}
    local text = ""
    if typeof(input.filteredText) == "string" then
        text = string.gsub(input.filteredText, "%c", " ")
        local len = utf8.len(text)
        if len and len > PlaytestFeedback.MaxTextLength then
            text = string.sub(text, 1, (utf8.offset(text, PlaytestFeedback.MaxTextLength + 1) or (#text + 1)) - 1)
        end
    end
    return {
        event = "feedback",
        fun = rating(input.fun), level = rating(input.level), looks = rating(input.looks),
        runs = whole(input.runs, 10000),
        location = if PlaytestFeedback.Locations[input.location] then input.location else "Hub",
        species = species(input.species),
        text = text,
    }
end

local function escape(s: string): string
    local out = string.gsub(s, "[%c\"\\]", function(c)
        if c == "\"" then return "\\\"" elseif c == "\\" then return "\\\\" end
        return string.format("\\u%04x", string.byte(c))
    end)
    return out
end

-- BD-441 (docs/132): "Tell us!" stays hidden on minute zero. Shown only once a run has ended (sawRunEnd), or for a returning
-- player who already has eggs/dinos from before (foundEgg) and is not in a run right now.
-- BD-538: on a phone-landscape canvas (compact) the button sat on the lower-left of every open menu (over the egg card's rarity and condition
-- chips), so it is hidden while a menu is open there (menuOpen and compact). Desktop menus are centred and leave the corner free: unchanged.
function PlaytestFeedback.showButton(info: any): boolean
    if type(info) ~= "table" then return false end
    if info.menuOpen == true and info.compact == true then return false end
    if info.sawRunEnd == true then return true end
    return info.foundEgg == true and info.runActive ~= true
end

local ORDER = {"event", "fun", "level", "looks", "runs", "location", "species", "text"}
function PlaytestFeedback.line(event: {[string]: any}): string
    local parts = {}
    for _, key in ORDER do
        local v = event[key]
        if v ~= nil then
            parts[#parts + 1] = string.format("\"%s\":%s", key, if typeof(v) == "string" then "\"" .. escape(v) .. "\"" else tostring(v))
        end
    end
    return PlaytestFeedback.LogPrefix .. "{" .. table.concat(parts, ",") .. "}"
end

return PlaytestFeedback
