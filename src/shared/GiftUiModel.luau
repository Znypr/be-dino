--!strict
-- BD-570 (docs/134 s13): PURE rules for the gifting player UI: the Settings row "Gifts from: Everyone / Friends / Nobody" and the real gift popup.
-- No Roblox services, no Instances, no clock: tools/verify_gift_ui.py runs this exact file offline against a mock GiftAction remote.
-- Behind Config.GiftClaimEnabled (default false, pinned off in every release profile): the client modules that use this file return before
-- they read it, so with the flag off nothing here ever runs.
--
-- Copy follows docs/72 (children: short, plain). The popup has exactly three buttons: "Nice!" (close), "Mute <name>" and "Turn gifts off".
-- There is NO refuse / decline button (owner, 2026-10-17: gifts are not refused one by one): Model.ButtonIds is the whole list and the
-- controller refuses to send any other action. Sizes are REAL pixels (the popup is never scaled): text >= 14, buttons >= 44 high.
local Model = {}

Model.MinText = 14 -- docs/72 floor, px on screen
Model.MinButton = 44 -- docs/72 touch floor, px on screen
Model.GlyphWidth = 0.55 -- average Fredoka glyph width in em, used to size buttons and clip names (conservative)

-- ------------------------------------------------------------------ the Settings row
Model.RowLabel = "Gifts from"
Model.Options = table.freeze({"everyone", "friends", "nobody"})
Model.OptionLabels = table.freeze({everyone = "EVERYONE", friends = "FRIENDS", nobody = "NOBODY"})
Model.Default = "everyone" -- same default as GiftRules.DefaultSetting (a gift is not contact; owner 2026-10-17)

function Model.normalizeSetting(value: any): string
    if type(value) == "string" and Model.OptionLabels[value] ~= nil then return value end
    return Model.Default
end

-- ------------------------------------------------------------------ popup copy
Model.Copy = table.freeze({
    ack = "Nice!",
    turnOff = "Turn gifts off",
    mutePrefix = "Mute ",
    titlePrefix = "You got a gift from ",
    titleSuffix = "!",
    converted = "You had it: crystals!",
    fallbackName = "A Be Dino player",
})

-- The ONLY buttons the popup may have, and the request each one sends. Anything else is not a gift action.
Model.ButtonIds = table.freeze({"ack", "mute", "turnOff"})
local requests = {
    get = {action = "get"},
    ack = {action = "ack"},
    mute = {action = "mute"},
    turnOff = {action = "turnOff"},
}
-- A fresh table every call (a caller can never edit the shared copy). nil for anything that is not a known request.
function Model.request(id: any): {[string]: any}?
    local found = if type(id) == "string" then requests[id] else nil
    return if found then table.clone(found) else nil
end
function Model.setFromRequest(from: any): {[string]: any}?
    if type(from) ~= "string" or Model.OptionLabels[from] == nil then return nil end
    return {action = "setFrom", from = from}
end

-- Shortens a name to `maxChars` characters (UTF-8 aware) with an ellipsis. Invalid UTF-8 gives the plain fallback name.
function Model.clip(text: string, maxChars: number): string
    local length = utf8.len(text)
    if length == nil then return Model.Copy.fallbackName end
    maxChars = math.max(1, math.floor(maxChars))
    if length <= maxChars then return text end
    if maxChars <= 1 then return "…" end
    local stop = utf8.offset(text, maxChars) -- start of character maxChars: keep the characters before it, then the ellipsis
    return string.sub(text, 1, (stop :: number) - 1) .. "…"
end

-- ------------------------------------------------------------------ the notice (server payload, GiftNoticeJson)
export type Notice = {id: string, line: string, name: string, item: string, message: string, kind: string, canMute: boolean, converted: boolean}

-- nil for anything that is not a well-formed payload (the popup then stays hidden). Text fields are length-capped.
function Model.parseNotice(decoded: any): Notice?
    if type(decoded) ~= "table" then return nil end
    local line, id = decoded.line, decoded.id
    if type(line) ~= "string" or line == "" or #line > 200 then return nil end
    if type(id) ~= "string" or #id > 120 then return nil end
    local function text(value: any, cap: number): string
        return if type(value) == "string" and #value <= cap then value else ""
    end
    local kind = if decoded.kind == "crystals" then "crystals" else "skin"
    return {
        id = id,
        line = line,
        name = text(decoded.name, 200),
        item = text(decoded.item, 80),
        message = text(decoded.message, 80),
        kind = kind,
        canMute = decoded.canMute == true,
        converted = decoded.converted == true,
    }
end

-- Registered icons only (docs/77): crystals use the amber icon, skins the dinos icon. No new art.
function Model.iconFor(notice: Notice): string
    return if notice.kind == "crystals" then "amber" else "dinos"
end

-- ------------------------------------------------------------------ variants (real px; TouchLayout.GIFT must list the same w x h)
-- roomy: desktop and tablets. compact: most phones. tight: narrow phones. stacked: the last resort on a very narrow canvas.
-- row variants put Nice! / Mute / Turn gifts off side by side; the stacked one puts Nice! on its own row.
type Variant = {name: string, w: number, h: number, titleSize: number, detailSize: number, buttonSize: number, buttonH: number, row: boolean,
    titleY: number, titleH: number, detailY: number, detailH: number, buttonsY: number, widths: {ack: number, mute: number, turnOff: number}}
local variants: {Variant} = {
    {name = "roomy", w = 480, h = 146, titleSize = 22, detailSize = 18, buttonSize = 20, buttonH = 48, row = true,
        titleY = 10, titleH = 30, detailY = 42, detailH = 26, buttonsY = 86, widths = {ack = 110, mute = 170, turnOff = 170}},
    {name = "compact", w = 420, h = 104, titleSize = 18, detailSize = 16, buttonSize = 16, buttonH = 44, row = true,
        titleY = 6, titleH = 22, detailY = 28, detailH = 20, buttonsY = 52, widths = {ack = 84, mute = 140, turnOff = 140}},
    {name = "tight", w = 372, h = 104, titleSize = 16, detailSize = 16, buttonSize = 16, buttonH = 44, row = true,
        titleY = 6, titleH = 22, detailY = 28, detailH = 20, buttonsY = 52, widths = {ack = 72, mute = 130, turnOff = 136}},
    {name = "stacked", w = 340, h = 156, titleSize = 16, detailSize = 16, buttonSize = 16, buttonH = 44, row = false,
        titleY = 6, titleH = 22, detailY = 28, detailH = 20, buttonsY = 52, widths = {ack = 320, mute = 156, turnOff = 156}},
}
Model.Variants = table.freeze(variants)
local byName: {[string]: Variant} = {}
for _, variant in variants do byName[variant.name] = variant end
Model.PadX = 10
Model.IconSize = 44
Model.TextX = Model.PadX * 2 + Model.IconSize - 2 -- text column starts right of the icon
Model.ButtonGap = 8
Model.ButtonPad = 12 -- horizontal padding a button needs around its text

export type Box = {x: number, y: number, w: number, h: number}
export type Layout = {variant: string, w: number, h: number, icon: Box, title: Box & {size: number}, detail: Box & {size: number},
    buttons: {[string]: Box & {size: number}}, order: {string}}

-- Where everything inside one popup goes. `canMute` false (an admin gift) leaves out the Mute button.
function Model.layout(name: string, canMute: boolean): Layout
    local v = byName[name] or byName.compact
    local textW = v.w - Model.TextX - Model.PadX
    local buttons: {[string]: Box & {size: number}} = {}
    local order: {string} = {}
    local function put(id: string, x: number, y: number, w: number)
        buttons[id] = {x = x, y = y, w = w, h = v.buttonH, size = v.buttonSize}
        table.insert(order, id)
    end
    if v.row then
        local ids = if canMute then {"ack", "mute", "turnOff"} else {"ack", "turnOff"}
        local total = Model.ButtonGap * (#ids - 1)
        for _, id in ids do total += (v.widths :: any)[id] end
        local x = (v.w - total) / 2
        for _, id in ids do
            local w = (v.widths :: any)[id]
            put(id, x, v.buttonsY, w)
            x += w + Model.ButtonGap
        end
    else
        put("ack", Model.PadX, v.buttonsY, v.w - 2 * Model.PadX)
        local y2 = v.buttonsY + v.buttonH + Model.ButtonGap
        if canMute then
            local half = (v.w - 2 * Model.PadX - Model.ButtonGap) / 2
            put("mute", Model.PadX, y2, half)
            put("turnOff", Model.PadX + half + Model.ButtonGap, y2, half)
        else
            put("turnOff", Model.PadX, y2, v.w - 2 * Model.PadX)
        end
    end
    return {
        variant = v.name, w = v.w, h = v.h,
        icon = {x = Model.PadX, y = v.titleY, w = Model.IconSize, h = Model.IconSize},
        title = {x = Model.TextX, y = v.titleY, w = textW, h = v.titleH, size = v.titleSize},
        detail = {x = Model.TextX, y = v.detailY, w = textW, h = v.detailH, size = v.detailSize},
        buttons = buttons, order = order,
    }
end

-- Characters that fit a box of this width at this text size (never under 3).
local function charsFor(width: number, size: number): number
    return math.max(3, math.floor(width / (size * Model.GlyphWidth)))
end

-- "You got a gift from <name>!" for a player's gift (the name is clipped to the room the variant has); the server's own line for a team gift.
function Model.title(notice: Notice, layout: Layout): string
    if notice.name == "" then return notice.line end
    local fixed = #Model.Copy.titlePrefix + #Model.Copy.titleSuffix
    local room = charsFor(layout.title.w, layout.title.size) - fixed
    return Model.Copy.titlePrefix .. Model.clip(notice.name, math.max(3, room)) .. Model.Copy.titleSuffix
end

-- The item name, then the preset message (or the "you had it" note when the skin turned into crystals).
function Model.detail(notice: Notice): string
    if notice.converted then return Model.Copy.converted end -- the skin was already theirs: say so, in one short line
    local text = notice.item
    if notice.message ~= "" then text = text .. " - " .. notice.message end
    return text
end

-- Button texts for this notice and layout. "Mute <name>" clips the name to the room the button has.
function Model.buttonText(id: string, notice: Notice, layout: Layout): string
    if id == "ack" then return Model.Copy.ack end
    if id == "turnOff" then return Model.Copy.turnOff end
    local button = layout.buttons[id]
    local width = if button then button.w else 100
    local size = if button then button.size else 16
    local room = charsFor(width - Model.ButtonPad, size) - #Model.Copy.mutePrefix
    local name = if notice.name ~= "" then notice.name else Model.Copy.fallbackName
    return Model.Copy.mutePrefix .. Model.clip(name, math.max(3, room))
end

-- Which buttons this notice shows, in order. Mute only for a gift from another player; there is no refuse button.
function Model.buttonsFor(notice: Notice): {string}
    if notice.canMute then return {"ack", "mute", "turnOff"} end
    return {"ack", "turnOff"}
end

-- ------------------------------------------------------------------ controller (setting + popup buttons), exercised offline with a mock remote
-- invoke(request) -> response table ({ok = true, ...} or {ok = false, reason}) or nil when the call failed. It yields in the game
-- (RemoteFunction:InvokeServer); callers run it inside task.spawn. The controller never sends anything that is not in `requests`.
export type Controller = {
    current: () -> string,
    loaded: () -> boolean,
    refresh: () -> boolean,
    choose: (any) -> boolean,
    press: (any) -> boolean,
}
function Model.controller(invoke: ({[string]: any}) -> any): Controller
    local from = Model.Default
    local isLoaded = false
    local function okResponse(response: any): boolean
        return type(response) == "table" and response.ok == true
    end
    local self: Controller = {
        current = function(): string return from end,
        loaded = function(): boolean return isLoaded end,
        -- Reads the saved value once. Returns true when the shown value changed.
        refresh = function(): boolean
            local response = invoke({action = "get"})
            if not okResponse(response) then return false end
            local value = Model.normalizeSetting(response.from)
            isLoaded = true
            local changed = value ~= from
            from = value
            return changed
        end,
        -- Picks a setting: shown at once, saved through setFrom, and put back when the save fails.
        choose = function(value: any): boolean
            local request = Model.setFromRequest(value)
            if request == nil then return false end
            local before = from
            from = value :: string
            if okResponse(invoke(request)) then
                isLoaded = true
                return true
            end
            from = before
            return false
        end,
        -- A popup button. Unknown ids are refused here, before anything is sent.
        press = function(id: any): boolean
            local request = Model.request(id)
            if request == nil or id == "get" then return false end
            local ok = okResponse(invoke(request))
            if ok and id == "turnOff" then from = "nobody" end
            return ok
        end,
    }
    return self
end

return Model
