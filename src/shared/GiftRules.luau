--!strict
-- BD-451 (docs/134, docs/115 GF1b/GF1c/GF9-GF17): PURE gifting rules shared by GiftService. No Roblox services, no clock, no store: every
-- function takes its inputs and returns a value, so tools/verify_gifts.py runs this exact file offline.
--
-- What a gift is: a fixed, named catalogue item (a skin or crystals, nothing else), an optional PRESET message id (never free text), a
-- sender UserId and a source ("robux" = BD-453 later, "admin" = BD-452). Names and message text are never stored (GF13/GF17).
-- Everything marked PROVISIONAL is a number or an item the owner has not approved.
local GiftRules = {}

GiftRules.SchemaVersion = 1

-- GF10 / GF15 / GF17 (PROVISIONAL numbers).
GiftRules.Limits = table.freeze({
    InboxCap = 25, -- pending gifts in one inbox (GF10); corrupt entries count, so a bad record can never grow the store
    PerSenderCap = 3, -- pending gifts from one sender in one inbox (GF10); admin gifts are the team's own and exempt
    PromptsPerMinute = 3, -- per buyer (GF15)
    GiftsPerDay = 10, -- per buyer, durable (GF15)
    PerRecipientPerDay = 3, -- per buyer and recipient, durable (GF15)
    LookupsPerMinute = 10, -- username lookups per player (GF15)
    LookupsPerDay = 60,
    ServerLookupsPerMinute = 30, -- shared Roblox web limit
    AdminGrantsPerMinute = 10, -- per admin (docs/134 s2.1)
    ClaimedGiftsCap = 5000, -- profile.claimedGifts; fails closed like purchaseReceipts
    BlockedCap = 200, -- blocked ids a recipient may report (pref_<id>)
    MutedCap = 50,
    RevokedCap = 1000, -- tombstones kept in one inbox
    AuditDayCap = 5000, -- audit_<yyyymmdd>
    AuditUserCap = 50, -- audituser_<id>
    AdminMaxCrystals = 50000, -- one admin grant, clamped
    ThankYouCrystals = 50, -- PROVISIONAL, owner sets it: a race-duplicate skin becomes this many crystals (GF16)
    PrefCacheSeconds = 30,
    MaxIdLength = 120,
    MaxNameLength = 40,
})
local Limits = GiftRules.Limits

-- ------------------------------------------------------------------ catalogue (PROVISIONAL: skins and crystals only)
-- launch = false: not giftable with Robux yet (crystal packs wait until CrystalPacksEnabled is playtested, GF2); admin may send it.
-- adminOnly: the free-form admin crystal grant ("crystals_custom", amount in the gift, 1..AdminMaxCrystals).
-- Never giftable, by construction (no entry can exist for them): eggs, dinos, species, rarity, luck, stat or fusion advantages.
export type Entry = {id: string, kind: string, label: string, skin: string?, crystals: number?, launch: boolean, adminOnly: boolean?}
local catalogue: {Entry} = {
    {id = "skin_plush", kind = "skin", skin = "Plush", label = "Plushy skin", launch = true},
    {id = "skin_clay", kind = "skin", skin = "Clay", label = "Clay skin", launch = true},
    {id = "skin_bricks", kind = "skin", skin = "Bricks", label = "Bricks skin", launch = true},
    {id = "skin_balloon", kind = "skin", skin = "Balloon", label = "Balloon skin", launch = true},
    {id = "crystals_100", kind = "crystals", crystals = 100, label = "100 crystals", launch = false},
    {id = "crystals_500", kind = "crystals", crystals = 500, label = "500 crystals", launch = false},
    {id = "crystals_2000", kind = "crystals", crystals = 2000, label = "2,000 crystals", launch = false},
    {id = "crystals_custom", kind = "crystals", label = "Crystals", launch = true, adminOnly = true},
}
GiftRules.Catalogue = table.freeze(catalogue)
local byId: {[string]: Entry} = {}
for _, entry in catalogue do byId[entry.id] = entry end
GiftRules.ById = table.freeze(byId)
GiftRules.AllowedKinds = table.freeze({skin = true, crystals = true})
GiftRules.ForbiddenKinds = table.freeze({egg = true, dino = true, dinosaur = true, species = true, nest = true, potion = true, fusion = true})
GiftRules.CustomCrystalsId = "crystals_custom"
GiftRules.Sources = table.freeze({robux = true, admin = true}) :: {[any]: boolean}
GiftRules.FallbackName = "A Be Dino player"
GiftRules.TeamLine = "A gift from the Be Dino team!"

-- ------------------------------------------------------------------ preset messages (GF6/GF14: ids only, never free text)
local presets = {
    {id = "have_fun", text = "Have fun!"},
    {id = "happy_birthday", text = "Happy birthday!"},
    {id = "youre_welcome", text = "You're welcome!"},
    {id = "thank_you", text = "Thank you!"},
    {id = "great_job", text = "Great job!"},
    {id = "enjoy", text = "Enjoy!"},
}
GiftRules.Presets = table.freeze(presets)
local presetById: {[string]: string} = {}
for _, preset in presets do presetById[preset.id] = preset.text end
function GiftRules.presetText(id: any): string?
    return if type(id) == "string" then presetById[id] else nil
end
-- nil = no message (allowed); anything else must be a preset id. A free-text string is simply not an id.
function GiftRules.validMessage(msg: any): boolean
    return msg == nil or (type(msg) == "string" and presetById[msg] ~= nil)
end

-- ------------------------------------------------------------------ small validators
local function wholeNumber(value: any, low: number, high: number): boolean
    return type(value) == "number" and value == value and value % 1 == 0 and value >= low and value <= high
end
function GiftRules.validUserId(value: any): boolean
    return wholeNumber(value, 1, 2 ^ 53)
end
function GiftRules.validId(value: any): boolean
    return type(value) == "string" and #value >= 1 and #value <= Limits.MaxIdLength and string.match(value, "^[%w_%-]+$") ~= nil
end
-- BD-590: the shape of an id that could ever have been issued ("R" or "A" first). A typo or forged id like "nope" is refused as bad input.
function GiftRules.validIssuedId(value: any): boolean
    if not GiftRules.validId(value) then return false end
    local first = string.sub(value :: string, 1, 1)
    return first == "R" or first == "A"
end
-- A gift id comes from the source, never from the client: robux "R" + PurchaseId, admin "A" + GUID (GF16).
function GiftRules.idMatchesSource(id: any, source: any): boolean
    if not GiftRules.validId(id) then return false end
    return (source == "robux" and string.sub(id :: string, 1, 1) == "R") or (source == "admin" and string.sub(id :: string, 1, 1) == "A")
end

-- Whether a catalogue item may be sent from this source. Robux gifts: launch items only, never the admin entry.
function GiftRules.itemAllowed(itemId: any, source: any): (boolean, string)
    if type(itemId) ~= "string" then return false, "unknown_item" end
    local entry = byId[itemId]
    if entry == nil then return false, "unknown_item" end
    if source == "admin" then return true, "ok" end
    if source ~= "robux" then return false, "bad_source" end
    if entry.adminOnly == true or entry.launch ~= true then return false, "not_giftable" end
    return true, "ok"
end

-- Crystals an item delivers; the custom admin entry reads the gift's own amount (clamped 1..AdminMaxCrystals).
function GiftRules.crystalAmount(entry: Entry, amount: any): number?
    if entry.kind ~= "crystals" then return nil end
    if entry.id == GiftRules.CustomCrystalsId then
        return if wholeNumber(amount, 1, Limits.AdminMaxCrystals) then amount :: number else nil
    end
    return entry.crystals
end
function GiftRules.clampAdminCrystals(amount: any): number?
    if type(amount) ~= "number" or amount ~= amount then return nil end
    return math.clamp(math.floor(amount), 1, Limits.AdminMaxCrystals)
end

-- ------------------------------------------------------------------ gifts (the inbox entry)
export type Gift = {id: string, source: string, from: number, item: string, crystals: number?, msg: string?, at: number}

-- Builds a stored gift. Returns nil plus a code when any field is not allowed. Stores ids only: no name, no message text.
function GiftRules.newGift(source: any, from: any, itemId: any, msg: any, crystals: any, at: any, id: any): (Gift?, string)
    if not GiftRules.Sources[source] then return nil, "bad_source" end
    if not GiftRules.validUserId(from) then return nil, "bad_sender" end
    local itemOk, why = GiftRules.itemAllowed(itemId, source)
    if not itemOk then return nil, why end
    if not GiftRules.validMessage(msg) then return nil, "bad_message" end
    if not GiftRules.idMatchesSource(id, source) then return nil, "bad_id" end
    if type(at) ~= "number" or at ~= at or at < 0 then return nil, "bad_time" end
    local entry = byId[itemId :: string]
    local amount: number? = nil
    if entry.id == GiftRules.CustomCrystalsId then
        amount = GiftRules.clampAdminCrystals(crystals)
        if amount == nil then return nil, "bad_amount" end
    elseif crystals ~= nil then
        return nil, "bad_amount"
    end
    return {id = id :: string, source = source :: string, from = from :: number, item = itemId :: string, crystals = amount, msg = msg :: string?, at = at}, "ok"
end

-- Shape check for an entry READ from the store. A newer build's unknown item, a missing field or a wrong type is "corrupt": the
-- claim step skips it and leaves it in place (never applied, never deleted).
function GiftRules.validGift(gift: any, key: any): boolean
    if type(gift) ~= "table" then return false end
    if key ~= nil and gift.id ~= key then return false end
    if not GiftRules.Sources[gift.source] or not GiftRules.idMatchesSource(gift.id, gift.source) then return false end
    if not GiftRules.validUserId(gift.from) then return false end
    local entry = if type(gift.item) == "string" then byId[gift.item] else nil
    if entry == nil then return false end
    if not GiftRules.validMessage(gift.msg) then return false end
    if type(gift.at) ~= "number" or gift.at ~= gift.at or gift.at < 0 then return false end
    if entry.id == GiftRules.CustomCrystalsId then
        if gift.source ~= "admin" or not wholeNumber(gift.crystals, 1, Limits.AdminMaxCrystals) then return false end
    elseif gift.crystals ~= nil then
        return false
    end
    if gift.source == "robux" and (entry.adminOnly == true) then return false end
    return true
end

-- What the profile transaction must do for a valid gift: {kind = "skin", skin} or {kind = "crystals", amount}.
function GiftRules.operationFor(gift: Gift): {[string]: any}?
    local entry = byId[gift.item]
    if entry == nil then return nil end
    if entry.kind == "skin" and entry.skin ~= nil then
        return {id = gift.id, kind = "skin", skin = entry.skin, thankYou = Limits.ThankYouCrystals, source = gift.source, item = gift.item}
    end
    local amount = GiftRules.crystalAmount(entry, gift.crystals)
    if amount == nil then return nil end
    return {id = gift.id, kind = "crystals", amount = amount, source = gift.source, item = gift.item}
end

-- Skin id a catalogue item grants (used by Revoke), nil for crystals or an unknown id.
function GiftRules.skinOf(itemId: any): string?
    local entry = if type(itemId) == "string" then byId[itemId] else nil
    return if entry and entry.kind == "skin" then entry.skin else nil
end

-- ------------------------------------------------------------------ inbox
-- A stored inbox is {gifts = {[id] = Gift}, revoked = {[id] = itemId | true}}. A missing record is an empty inbox. Anything of
-- another shape is "corrupt": the caller refuses to write over it (returns nil).
export type Inbox = {gifts: {[string]: any}, revoked: {[string]: any}}
function GiftRules.normalizeInbox(raw: any): Inbox?
    if raw == nil then return {gifts = {}, revoked = {}} end
    if type(raw) ~= "table" then return nil end
    local gifts, revoked = raw.gifts, raw.revoked
    if gifts ~= nil and type(gifts) ~= "table" then return nil end
    if revoked ~= nil and type(revoked) ~= "table" then return nil end
    -- Fields we do not know (a newer build) ride along untouched.
    local inbox = table.clone(raw)
    inbox.gifts = if gifts then table.clone(gifts) else {}
    inbox.revoked = if revoked then table.clone(revoked) else {}
    return inbox :: any
end
local function count(map: {[any]: any}): number
    local n = 0
    for _ in map do n += 1 end
    return n
end
GiftRules.count = count

-- Can this gift be added to the inbox? "duplicate" is success (idempotent redelivery), the rest are refusals.
function GiftRules.inboxAdmits(inbox: Inbox, gift: Gift): (boolean, string)
    if inbox.revoked[gift.id] ~= nil then return false, "revoked" end
    if inbox.gifts[gift.id] ~= nil then return true, "duplicate" end
    if count(inbox.gifts) >= Limits.InboxCap then return false, "inbox_full" end
    if gift.source == "robux" then
        local fromSender = 0
        for _, other in inbox.gifts do
            if type(other) == "table" and other.from == gift.from and other.source == "robux" then fromSender += 1 end
        end
        if fromSender >= Limits.PerSenderCap then return false, "sender_cap" end
    end
    return true, "ok"
end

-- ------------------------------------------------------------------ recipient setting (GF1c, GF11, GF12)
-- pref_<userId> = {from = "everyone" | "friends" | "nobody", blocked = {userId...}, muted = {userId...}}. A MISSING or unreadable record
-- means Everyone with no blocks and no mutes (a user who never played Be Dino is a valid recipient).
export type Pref = {from: string, blocked: {[number]: boolean}, muted: {[number]: boolean}}
GiftRules.Settings = table.freeze({everyone = true, friends = true, nobody = true}) :: {[any]: boolean}
GiftRules.DefaultSetting = "everyone"

local function idSet(list: any, cap: number): {[number]: boolean}
    local set: {[number]: boolean} = {}
    if type(list) ~= "table" then return set end
    local n = 0
    for _, id in list do
        if GiftRules.validUserId(id) and not set[id] then
            n += 1
            if n > cap then break end
            set[id] = true
        end
    end
    return set
end
function GiftRules.normalizePref(record: any): Pref
    if type(record) ~= "table" then return {from = "everyone", blocked = {}, muted = {}} end
    local from = if type(record.from) == "string" and GiftRules.Settings[record.from] then record.from else "everyone"
    return {from = from, blocked = idSet(record.blocked, Limits.BlockedCap), muted = idSet(record.muted, Limits.MutedCap)}
end
local function sortedList(set: {[number]: boolean}): {number}
    local list = {}
    for id in set do table.insert(list, id) end
    table.sort(list)
    return list
end
-- Back to the JSON-safe stored form (arrays, never numeric keys).
function GiftRules.encodePref(pref: Pref): {[string]: any}
    return {from = pref.from, blocked = sortedList(pref.blocked), muted = sortedList(pref.muted)}
end
function GiftRules.setFrom(pref: Pref, from: any): boolean
    if type(from) ~= "string" or not GiftRules.Settings[from] then return false end
    pref.from = from
    return true
end
function GiftRules.addMuted(pref: Pref, senderId: any): (boolean, string)
    if not GiftRules.validUserId(senderId) then return false, "bad_sender" end
    if pref.muted[senderId :: number] then return true, "already" end
    if count(pref.muted) >= Limits.MutedCap then return false, "muted_full" end
    pref.muted[senderId :: number] = true
    return true, "muted"
end
function GiftRules.setBlocked(pref: Pref, ids: any): (boolean, string)
    if type(ids) ~= "table" or #ids > Limits.BlockedCap then return false, "bad_request" end
    for _, id in ids do
        if not GiftRules.validUserId(id) then return false, "bad_request" end
    end
    pref.blocked = idSet(ids, Limits.BlockedCap)
    return true, "ok"
end

-- Does the recipient's setting accept this sender? isFriend is the recipient/sender friendship, only read for "friends".
-- Roblox blocks beat everything, admin included (docs/134 s5). Admin gifts bypass the setting and mute, not the block.
-- The reason code is for the audit log only: toPublic() turns every recipient-side refusal into ONE code.
function GiftRules.recipientAllows(pref: Pref, senderId: number, isFriend: boolean, source: string): (boolean, string)
    if pref.blocked[senderId] then return false, "blocked" end
    if source == "admin" then return true, "ok" end
    if pref.from == "nobody" then return false, "setting_off" end
    if pref.from == "friends" and not isFriend then return false, "friends_only" end
    if pref.muted[senderId] then return false, "muted" end
    return true, "ok"
end

GiftRules.RecipientSide = table.freeze({blocked = true, setting_off = true, friends_only = true, muted = true, inbox_full = true, sender_cap = true}) :: {[any]: boolean}
GiftRules.PublicRefusal = "cant_receive"
-- GF12 / docs/134 s2.1: the buyer must never learn which rule fired, so every recipient-side reason maps to one code.
function GiftRules.toPublic(code: string): string
    return if GiftRules.RecipientSide[code] then GiftRules.PublicRefusal else code
end
-- The single refusal sentence (byte-identical for every recipient-side reason). name = the recipient's display name, supplied by the UI.
function GiftRules.refusalText(name: string): string
    return name .. " can't get gifts right now."
end

-- ------------------------------------------------------------------ rate limits (GF15)
-- Fixed one-minute window; state = {start, count}, mutated. Returns true when the call is allowed (and counted).
function GiftRules.windowAllow(state: {start: number, count: number}, now: number, limit: number, seconds: number?): boolean
    local span = seconds or 60
    if now - state.start >= span or now < state.start then
        state.start, state.count = now, 0
    end
    if state.count >= limit then return false end
    state.count += 1
    return true
end

function GiftRules.dayNumber(now: number): number
    return math.floor(now / 86400)
end
-- yyyymmdd (UTC) from a unix time: the key suffix of the audit day lists. Pure date arithmetic, no os.date.
function GiftRules.dateKey(now: number): number
    local z = math.floor(now / 86400) + 719468
    local era = z // 146097
    local doe = z - era * 146097
    local yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    local year = yoe + era * 400
    local doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    local mp = (5 * doy + 2) // 153
    local day = doy - (153 * mp + 2) // 5 + 1
    local month = if mp < 10 then mp + 3 else mp - 9
    if month <= 2 then year += 1 end
    return year * 10000 + month * 100 + day
end

-- The durable per-buyer record (intent_<buyerUserId>): {day, dayCount, perRecipient = {[tostring(userId)] = n}}.
function GiftRules.normalizeIntent(raw: any, now: number): {[string]: any}
    local day = GiftRules.dayNumber(now)
    if type(raw) ~= "table" or raw.day ~= day or not wholeNumber(raw.dayCount, 0, 1e9) or type(raw.perRecipient) ~= "table" then
        return {day = day, dayCount = 0, perRecipient = {}}
    end
    local intent = table.clone(raw)
    intent.perRecipient = table.clone(raw.perRecipient)
    return intent
end
function GiftRules.dailyAllows(intent: {[string]: any}, recipientId: number): (boolean, string)
    if intent.dayCount >= Limits.GiftsPerDay then return false, "daily_limit" end
    local perRecipient = intent.perRecipient[tostring(recipientId)]
    if type(perRecipient) == "number" and perRecipient >= Limits.PerRecipientPerDay then return false, "recipient_limit" end
    return true, "ok"
end
function GiftRules.bumpDaily(intent: {[string]: any}, recipientId: number)
    intent.dayCount += 1
    local key = tostring(recipientId)
    local current = intent.perRecipient[key]
    intent.perRecipient[key] = (if type(current) == "number" then current else 0) + 1
end

-- Username lookups (docs/134 s2.1): per player per minute and per day, plus one server-wide bucket. Pure state in, bool out.
function GiftRules.newLookupState(): {player: {start: number, count: number}, day: {start: number, count: number}}
    return {player = {start = 0, count = 0}, day = {start = 0, count = 0}}
end
function GiftRules.lookupAllows(playerState: {player: {start: number, count: number}, day: {start: number, count: number}}, serverState: {start: number, count: number}, now: number): (boolean, string)
    -- Check every bucket before counting any, so a refusal costs nothing.
    local function open(state: {start: number, count: number}, limit: number, seconds: number): boolean
        return now - state.start >= seconds or now < state.start or state.count < limit
    end
    if not open(playerState.player, Limits.LookupsPerMinute, 60) then return false, "lookup_minute" end
    if not open(playerState.day, Limits.LookupsPerDay, 86400) then return false, "lookup_day" end
    if not open(serverState, Limits.ServerLookupsPerMinute, 60) then return false, "lookup_server" end
    GiftRules.windowAllow(playerState.player, now, Limits.LookupsPerMinute, 60)
    GiftRules.windowAllow(playerState.day, now, Limits.LookupsPerDay, 86400)
    GiftRules.windowAllow(serverState, now, Limits.ServerLookupsPerMinute, 60)
    return true, "ok"
end

-- ------------------------------------------------------------------ audit (GF17: UserIds and codes only, never names or text)
GiftRules.AuditEvents = table.freeze({requested = true, refused = true, bought = true, queued = true, claimed = true, held = true, revoked = true, admin = true}) :: {[any]: boolean}
-- Whitelisted fields only; any value of the wrong type or shape turns the whole event into nil (it is simply not written).
function GiftRules.auditEvent(ev: any, at: any, from: any, to: any, item: any, giftId: any, purchaseId: any, code: any): {[string]: any}?
    if type(ev) ~= "string" or not GiftRules.AuditEvents[ev] then return nil end
    if type(at) ~= "number" or at ~= at or at < 0 then return nil end
    local event: {[string]: any} = {at = at, ev = ev}
    if from ~= nil then
        if not GiftRules.validUserId(from) then return nil end
        event.from = from
    end
    if to ~= nil then
        if not GiftRules.validUserId(to) then return nil end
        event.to = to
    end
    if item ~= nil then
        if type(item) ~= "string" or byId[item] == nil then return nil end
        event.item = item
    end
    if giftId ~= nil then
        if not GiftRules.validId(giftId) then return nil end
        event.giftId = giftId
    end
    if purchaseId ~= nil then
        if not GiftRules.validId(purchaseId) then return nil end
        event.purchaseId = purchaseId
    end
    if code ~= nil then
        if type(code) ~= "string" or #code < 1 or #code > 40 or string.match(code, "^[%l%d_]+$") == nil then return nil end
        event.code = code
    end
    return event
end
-- Appends keeping the newest `cap` entries.
function GiftRules.appendCapped(list: any, entry: {[string]: any}, cap: number): {any}
    local result: {any} = {}
    if type(list) == "table" then
        for _, existing in list do table.insert(result, existing) end
    end
    table.insert(result, entry)
    while #result > cap do table.remove(result, 1) end
    return result
end

-- ------------------------------------------------------------------ popup text
-- The sender's display name is resolved fresh at popup time and never stored (GF13). Admin gifts never show an admin name.
-- BD-570: the name the popup shows for a gift from another player (the same cut and fallback as the line). Admin gifts have none.
function GiftRules.shownName(source: string, displayName: any): string
    if source == "admin" then return "" end
    return if type(displayName) == "string" and #displayName >= 1 then string.sub(displayName, 1, Limits.MaxNameLength) else GiftRules.FallbackName
end
function GiftRules.noticeLine(source: string, displayName: any): string
    if source == "admin" then return GiftRules.TeamLine end
    return "You got a gift from " .. GiftRules.shownName(source, displayName) .. "!"
end

return GiftRules
