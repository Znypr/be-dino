--!strict
-- BD-1233 (docs/242 gap 18, flag Config.CodesEnabled): pure rules for the code box and the group gift chest. No Roblox services
-- (tools/verify_social.py drives them). The CODE TABLE itself is server-only (src/server/CodeTable.luau), so a client never sees unreleased codes.
-- One use per player: the server stores the token ("code:BEDINO", "group:chest") in the additive profile field `redeemedCodes`.
-- Rewards are free crystals only (PROVISIONAL amounts), never Robux, never random.
local C = {}

C.MaxLength = 20 -- letters and digits a code may have
C.MaxStored = 300 -- tokens kept per save; past this the server refuses (fail closed, never grants what it cannot record)
C.TryGap = 1.5 -- seconds between two tries of one player
C.MaxWrongPerMinute = 8 -- wrong codes per minute before "Try again soon"
C.GroupToken = "group:chest"

-- Kid words for every answer the server can give (docs/72: short, obvious).
C.Words = table.freeze({
    applied = "You got %d crystals!",
    already = "You used this code already.",
    wrong = "That code is not right.",
    expired = "That code has ended.",
    slow = "Try again soon.",
    full = "Your crystals are full!",
    group_join = "Join the group to open it!",
    group_done = "You opened it already!",
    group_off = "No group yet.",
    busy = "Please wait a moment.",
})

-- What the player typed -> the code key (upper case, letters and digits only), or nil when it cannot be a code.
function C.normalize(text: any): string?
    if type(text) ~= "string" or #text > 64 then return nil end
    local s = string.upper((string.gsub(text, "[%s%-_]", "")))
    if #s < 1 or #s > C.MaxLength or not string.find(s, "^[%u%d]+$") then return nil end
    return s
end

function C.token(code: string): string return "code:" .. code end

-- Is a code table entry usable now? entry = {crystals = n, endsAt = unix time or nil}.
function C.state(entry: any, now: number): string
    if type(entry) ~= "table" or type(entry.crystals) ~= "number" or entry.crystals < 1 or entry.crystals % 1 ~= 0 then return "wrong" end
    if type(entry.endsAt) == "number" and now >= entry.endsAt then return "expired" end
    return "ok"
end

-- The message for a status; applied takes the crystal amount.
function C.message(status: string, crystals: number?): string
    local w = C.Words[status] or C.Words.busy
    if status == "applied" then return string.format(w, crystals or 0) end
    return w
end

-- Wrong-try limiter: times = recent wrong tries (os.clock values). Returns the kept list and whether another try is allowed.
function C.allowTry(times: {number}, now: number): ({number}, boolean)
    local keep = {}
    for _, t in times do if now - t < 60 then table.insert(keep, t) end end
    return keep, #keep < C.MaxWrongPerMinute
end

return C
