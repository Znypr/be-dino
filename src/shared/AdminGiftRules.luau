--!strict
-- BD-452 (docs/134 s5, docs/79): PURE rules of the admin "Gift" page, shared by AdminGifts (server) and AdminGiftPage (client).
-- No Roblox services, no clock, no store: tools/verify_gifts.py runs this exact file offline. The server is the only authority; the
-- client uses these values to build the page and to word the answers.
local GiftRules = require(script.Parent.GiftRules)

local Rules = {}

Rules.RemoteName = "AdminGiftAction"
Rules.MinGapSeconds = 0.15 -- between two requests from one admin (the send itself is limited by GiftService: 10 a minute)
Rules.HistoryMax = 50 -- GiftRules.Limits.AuditUserCap
Rules.NameMin, Rules.NameMax = 3, 20 -- Roblox usernames
Rules.CrystalChips = table.freeze({100, 500, 2000, 10000, 50000})
Rules.Actions = table.freeze({"pick", "lookup", "confirm", "send", "revoke", "audit"})

-- Exactly these keys per action. Anything else (a label, a sender id, a gift id on send) makes the whole request "bad_request", so the
-- label "A gift from the Be Dino team!" and the sender can only ever come from the server.
local shapes: {[string]: {[string]: boolean}} = {
    pick = {action = true, userId = true},
    lookup = {action = true, name = true},
    confirm = {action = true, userId = true},
    send = {action = true, to = true, item = true, crystals = true, msg = true},
    revoke = {action = true, to = true, giftId = true, item = true},
    audit = {action = true, userId = true},
}
Rules.Shapes = table.freeze(shapes)

-- The action name when the request is a table of an allowed shape, else nil.
function Rules.shapeOk(request: any): string?
    if type(request) ~= "table" then return nil end
    local action = request.action
    local shape = if type(action) == "string" then shapes[action] else nil
    if shape == nil then return nil end
    for key in request do
        if type(key) ~= "string" or not shape[key] then return nil end
    end
    return action :: string
end

function Rules.validName(name: any): boolean
    return type(name) == "string" and #name >= Rules.NameMin and #name <= Rules.NameMax and string.match(name, "^[%w_]+$") ~= nil
end

-- A whole number 1..cap. The server REFUSES anything else ("bad_amount"); it never clamps silently.
function Rules.amountOk(amount: any): boolean
    return type(amount) == "number" and amount == amount and amount % 1 == 0 and amount >= 1 and amount <= GiftRules.Limits.AdminMaxCrystals
end
-- Client helper: the typed text to a valid amount, or nil.
function Rules.parseAmount(text: any): number?
    if type(text) ~= "string" then return nil end
    local digits = string.gsub(text, "[,%s]", "")
    if digits == "" or string.match(digits, "^%d+$") == nil or #digits > 7 then return nil end
    local value = tonumber(digits)
    return if value ~= nil and Rules.amountOk(value) then value else nil
end

-- What the page offers: every skin in the catalogue, then Crystals (the custom amount). Fixed crystal packs are covered by the amount.
export type Choice = {id: string, label: string, kind: string}
function Rules.choices(): {Choice}
    local list: {Choice} = {}
    for _, entry in GiftRules.Catalogue do
        if entry.kind == "skin" then table.insert(list, {id = entry.id, label = entry.label, kind = "skin"}) end
    end
    local custom = GiftRules.ById[GiftRules.CustomCrystalsId]
    table.insert(list, {id = custom.id, label = custom.label, kind = "crystals"})
    return list
end

-- Short answers for every code the page can get (docs/72: what happened, what to do next). Unknown codes fall back to the code itself.
local messages: {[string]: string} = {
    not_admin = "Only the team can do this.",
    disabled = "Gifts are off.",
    busy = "One moment, then try again.",
    bad_request = "That did not look right. Try again.",
    bad_action = "That did not look right. Try again.",
    bad_name = "Type a username: 3 to 20 letters, numbers or _.",
    not_found = "We could not find that player.",
    not_here = "That player left. Pick again.",
    not_confirmed = "Pick someone and tap Yes first.",
    bad_amount = "Pick 1 to 50,000 crystals.",
    unknown_item = "Pick a gift first.",
    bad_message = "Pick a message from the list.",
    bad_sender = "This account can not send gifts here.",
    rate_limited = "Slow down. 10 gifts a minute.",
    lookup_minute = "Slow down a little.",
    lookup_day = "That is enough looking up for today.",
    lookup_server = "Slow down a little.",
    try_again = "Try again in a minute.",
    cant_receive = "They can't get gifts right now.",
    revoked = "That gift was taken back.",
    unknown_gift = "No gift with that number.", -- BD-590: Take back of an id that was never sent (or is too old to find in the history)
    store_corrupt = "Their inbox looks broken. Ask the lead.",
    tombstones_full = "Too many taken back for this player.",
    profile_not_loaded = "Wait a moment, then try again.",
    error = "Something went wrong. Try again.",
}
Rules.Messages = table.freeze(messages)
function Rules.explain(code: any): string
    if type(code) ~= "string" then return "Something went wrong. Try again." end
    return messages[code] or ("Failed: " .. string.gsub(code, "_", " "))
end

-- Done lines for the status row.
Rules.Done = table.freeze({
    send = "Gift sent. They get it next time they play.",
    duplicate = "That gift was already sent.",
    revoked = "Taken back.",
    revoked_pending = "Taken back before they opened it.",
    already_revoked = "Already taken back.",
})

-- ------------------------------------------------------------------ history lines (the audit view)
local eventLabels: {[string]: string} = {
    requested = "Asked", refused = "Refused", bought = "Bought", queued = "Queued", claimed = "Opened",
    held = "Held", revoked = "Taken back", admin = "Sent by the team",
}
local function two(n: number): string
    return if n < 10 then "0" .. tostring(n) else tostring(n)
end
-- "10-17 13:02" in UTC from a unix time (pure arithmetic).
function Rules.stamp(at: number): string
    local key = GiftRules.dateKey(at)
    local month, day = (key // 100) % 100, key % 100
    local seconds = at % 86400
    return two(month) .. "-" .. two(day) .. " " .. two(seconds // 3600) .. ":" .. two((seconds % 3600) // 60)
end
-- One event as two short lines: when, what, who; then the gift id (tap to fill the take-back box).
function Rules.historyLine(event: any): string
    if type(event) ~= "table" or type(event.at) ~= "number" then return "?" end
    local label = eventLabels[event.ev] or tostring(event.ev)
    local item = if type(event.item) == "string" and GiftRules.ById[event.item] then GiftRules.ById[event.item].label else "gift"
    local who = ""
    if event.from ~= nil and event.to ~= nil then who = "  " .. tostring(event.from) .. " to " .. tostring(event.to)
    elseif event.to ~= nil then who = "  to " .. tostring(event.to) end
    local code = if type(event.code) == "string" then "  (" .. string.gsub(event.code, "_", " ") .. ")" else ""
    local line = Rules.stamp(event.at) .. "  " .. label .. "  " .. item .. who .. code
    if type(event.giftId) == "string" then line ..= "\nid " .. event.giftId end
    return line
end

-- The newest `HistoryMax` audit events, newest first, each re-validated through GiftRules.auditEvent so only whitelisted ids and codes
-- ever leave the server (never a name, never text). Pure.
function Rules.cleanHistory(trail: any): {{[string]: any}}
    local clean: {{[string]: any}} = {}
    if type(trail) ~= "table" then return clean end
    for _, event in trail do
        if type(event) == "table" then
            local rebuilt = GiftRules.auditEvent(event.ev, event.at, event.from, event.to, event.item, event.giftId, event.purchaseId, event.code)
            if rebuilt ~= nil then table.insert(clean, rebuilt) end
        end
    end
    table.sort(clean, function(a, b) return (a.at :: number) > (b.at :: number) end)
    while #clean > Rules.HistoryMax do table.remove(clean) end
    return clean
end

return table.freeze(Rules)
