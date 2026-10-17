--!strict
-- BD-451 (docs/134, docs/115 GF1b..GF17): the gift inbox. SERVER AND DATA ONLY: no Robux (BD-453 will call send()/preflight() from
-- ProcessReceipt), no admin page (BD-452 will call send()/revoke()), no player UI beyond the "You got a gift from <name>!" notice.
--
-- FLAG-OFF IDENTITY. Config.GiftClaimEnabled is the master switch (both senders also need their own flag). While it is false:
--   * start() returns at once: no remote, no connection, no loop;
--   * every function below returns (false, "disabled") BEFORE it touches DataStoreService, a profile or PrivateState;
--   * ProfileRepository.applyGifts is inert for the same reason.
-- tools/verify_gifts.py proves that against a counting mock (zero DataStore requests, zero profile transforms, zero Instance.new).
--
-- DATA (the "Gifts" DataStore, name = <ProfileDataStoreName cut to 43>_Gifts so the playtest store stays isolated; profiles are never
-- written from another server):
--   inbox_<recipientUserId>   {gifts = {[giftId] = Gift}, revoked = {[giftId] = itemId | true}}   no expiry (GF10)
--   pref_<userId>             {from, blocked = {ids}, muted = {ids}}                              missing = Everyone (GF1c, GF11)
--   intent_<buyerUserId>      {day, dayCount, perRecipient}                                       durable daily counters (GF15)
--   audit_<yyyymmdd>, audituser_<userId>   events by UserId and code only, never a name or text (GF17)
--
-- CLAIM (the recipient's own server, on join and every ClaimSeconds): read the inbox, decide apply or hold per gift, then ONE
-- lease-checked ProfileRepository transaction (applyGifts) with profile.claimedGifts[giftId] as the exactly-once token, then remove the
-- applied ids from the inbox. A crash between those two steps only causes a harmless "already" on the next claim.
--
-- ONE refusal copy (GF12): every recipient-side refusal leaves send()/preflight() as the same public code, so a buyer cannot probe
-- blocks, mutes or settings.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local GiftRules = require(ReplicatedStorage.Shared.GiftRules)
local PrivateState = require(script.Parent.PrivateState)

local Limits = GiftRules.Limits
local GiftService = {}
GiftService.ClaimSeconds = 60
GiftService.ActionWindowSeconds = 10
GiftService.ActionsPerWindow = 12

local repository: any = nil
local clock: () -> number = function() return os.time() end
local nameResolver: ((number) -> string?)? = nil
local friendChecker: ((any, number) -> boolean)? = nil
local giftStore: any = nil
local stats = {reads = 0, writes = 0, failures = 0}
local prefCache: {[number]: {at: number, pref: any}} = {}
local promptWindows: {[number]: {start: number, count: number}} = {}
local adminWindows: {[number]: {start: number, count: number}} = {}
local lookupStates: {[number]: any} = {}
local serverLookups = {start = 0, count = 0}
local claiming: {[any]: boolean} = setmetatable({}, {__mode = "k"}) :: any
local notices: {[any]: {any}} = setmetatable({}, {__mode = "k"}) :: any
local actionWindows: {[any]: {start: number, count: number}} = setmetatable({}, {__mode = "k"}) :: any
local heldLogged: {[string]: boolean} = {}
local blockedReported: {[any]: boolean} = setmetatable({}, {__mode = "k"}) :: any -- the client has sent its Roblox block list this session
local reportLogged = false

-- ------------------------------------------------------------------ flags (one boolean test each, before anything else)
local function claimOn(): boolean
    return Config.GiftClaimEnabled == true
end
local function sendOn(source: any): boolean
    if not claimOn() then return false end
    if source == "admin" then return Config.AdminGiftsEnabled == true and Config.AdminPanelEnabled == true end
    return source == "robux" and Config.GiftingEnabled == true
end

-- ------------------------------------------------------------------ the Gifts store (created lazily, on first use with a flag on)
local function store(): any
    if giftStore ~= nil then return giftStore end
    local RunService = game:GetService("RunService")
    if RunService:IsStudio() and game.GameId == 0 and Config.StudioLocalProfilesEnabled then
        -- Unpublished Studio has no DataStore: an in-memory store with deep copies mirrors transaction boundaries (like ProfileRepository).
        local HttpService = game:GetService("HttpService")
        local memory: {[string]: any} = {}
        giftStore = {
            GetAsync = function(_, key: string) return if memory[key] ~= nil then HttpService:JSONDecode(HttpService:JSONEncode(memory[key])) else nil end,
            UpdateAsync = function(_, key: string, transform: (any) -> any)
                local current = if memory[key] ~= nil then HttpService:JSONDecode(HttpService:JSONEncode(memory[key])) else nil
                local updated = transform(current)
                if updated == nil then return nil end
                memory[key] = HttpService:JSONDecode(HttpService:JSONEncode(updated))
                return updated
            end,
        }
    else
        giftStore = game:GetService("DataStoreService"):GetDataStore(string.sub(Config.ProfileDataStoreName, 1, 43) .. "_Gifts")
    end
    return giftStore
end

local function attempt(label: string, fn: () -> any): (boolean, any)
    local lastError: any = nil
    for tryNumber = 1, 3 do
        local ok, result = pcall(fn)
        if ok then return true, result end
        lastError = result
        stats.failures += 1
        if tryNumber < 3 then task.wait(0.5 * (2 ^ (tryNumber - 1))) end
    end
    warn("[BD-GIFT] store " .. label .. " failed: " .. tostring(lastError))
    return false, lastError
end
local function readKey(key: string): (boolean, any)
    stats.reads += 1
    return attempt("read", function() return store():GetAsync(key) end)
end
local function updateKey(key: string, transform: (any) -> any): (boolean, any)
    stats.writes += 1
    return attempt("update", function() return store():UpdateAsync(key, transform) end)
end

local function inboxKey(userId: number): string return "inbox_" .. tostring(userId) end
local function prefKey(userId: number): string return "pref_" .. tostring(userId) end
local function intentKey(userId: number): string return "intent_" .. tostring(userId) end

-- ------------------------------------------------------------------ audit (GF17): UserIds and codes only; a failure never blocks a gift
local function audit(ev: string, from: any, to: any, item: any, giftId: any, purchaseId: any, code: any)
    local at = clock()
    local event = GiftRules.auditEvent(ev, at, from, to, item, giftId, purchaseId, code)
    if event == nil then return end
    pcall(function()
        updateKey("audit_" .. tostring(GiftRules.dateKey(at)), function(list: any)
            return GiftRules.appendCapped(list, event, Limits.AuditDayCap)
        end)
        local seen: {[number]: boolean} = {}
        for _, userId in {from, to} do
            if GiftRules.validUserId(userId) and not seen[userId] then
                seen[userId] = true
                updateKey("audituser_" .. tostring(userId), function(list: any)
                    return GiftRules.appendCapped(list, event, Limits.AuditUserCap)
                end)
            end
        end
    end)
end

-- ------------------------------------------------------------------ recipient preference (pref_<userId>)
-- nil when the store could not be read. A missing record is Everyone with no blocks (a never-played user is a valid recipient).
local function readPref(userId: number, fresh: boolean?): any
    local cached = prefCache[userId]
    if not fresh and cached ~= nil and clock() - cached.at < Limits.PrefCacheSeconds then return cached.pref end
    local ok, raw = readKey(prefKey(userId))
    if not ok then return nil end
    local pref = GiftRules.normalizePref(raw)
    prefCache[userId] = {at = clock(), pref = pref}
    return pref
end
local function changePref(userId: number, change: (any) -> (boolean, string)): (boolean, string)
    local status = "ok"
    local ok = updateKey(prefKey(userId), function(raw: any)
        local pref = GiftRules.normalizePref(raw)
        local changed, why = change(pref)
        status = why
        if not changed then return nil end
        return GiftRules.encodePref(pref)
    end)
    prefCache[userId] = nil
    if not ok then return false, "save_failed" end
    return status == "ok" or status == "muted" or status == "already", status
end

-- Recipient settings. Reached only through the GiftAction remote (player) or the future admin page.
function GiftService.setFrom(userId: number, from: any): (boolean, string)
    if not claimOn() then return false, "disabled" end
    if not GiftRules.validUserId(userId) then return false, "bad_request" end
    return changePref(userId, function(pref: any)
        if not GiftRules.setFrom(pref, from) then return false, "bad_request" end
        return true, "ok"
    end)
end
function GiftService.mute(userId: number, senderId: any): (boolean, string)
    if not claimOn() then return false, "disabled" end
    if not GiftRules.validUserId(userId) then return false, "bad_request" end
    return changePref(userId, function(pref: any)
        local ok, why = GiftRules.addMuted(pref, senderId)
        return ok and why == "muted", why
    end)
end
function GiftService.reportBlocked(userId: number, ids: any): (boolean, string)
    if not claimOn() then return false, "disabled" end
    if not GiftRules.validUserId(userId) then return false, "bad_request" end
    return changePref(userId, function(pref: any)
        local ok, why = GiftRules.setBlocked(pref, ids)
        return ok, why
    end)
end
function GiftService.getPref(userId: number): any
    if not claimOn() then return nil end
    return readPref(userId, true)
end

-- ------------------------------------------------------------------ sending (called by BD-452 admin and BD-453 receipts)
-- Everything that can be refused BEFORE a Robux prompt: flags, ids, item, message, recipient setting, block, inbox space and the
-- rate limits. Nothing is written except the durable daily counters, and only when the whole request passes.
-- req = {source = "robux", from = buyerUserId, to = recipientUserId, item, msg?, isFriend = boolean}.
-- Returns ok, publicCode: a recipient-side refusal is always GiftRules.PublicRefusal.
function GiftService.preflight(req: any): (boolean, string)
    if type(req) ~= "table" then return false, "bad_request" end
    local request = req
    if not sendOn("robux") or request.source ~= "robux" then return false, "disabled" end
    if not GiftRules.validUserId(request.from) or not GiftRules.validUserId(request.to) then return false, "bad_request" end
    if request.from == request.to then return false, "self" end
    local itemOk, why = GiftRules.itemAllowed(request.item, "robux")
    if not itemOk then return false, why end
    if not GiftRules.validMessage(request.msg) then return false, "bad_message" end
    local from, to = request.from :: number, request.to :: number
    local now = clock()
    local window = promptWindows[from]
    if window == nil then window = {start = 0, count = 0} promptWindows[from] = window end
    if not GiftRules.windowAllow(window, now, Limits.PromptsPerMinute, 60) then return false, "rate_limited" end
    local pref = readPref(to)
    if pref == nil then return false, "try_again" end
    local allowed, reason = GiftRules.recipientAllows(pref, from, request.isFriend == true, "robux")
    if not allowed then
        audit("refused", from, to, request.item, nil, nil, reason)
        return false, GiftRules.toPublic(reason)
    end
    local okInbox, rawInbox = readKey(inboxKey(to))
    if not okInbox then return false, "try_again" end
    local inbox = GiftRules.normalizeInbox(rawInbox)
    if inbox == nil then return false, "try_again" end
    local probe = {id = "R-probe", source = "robux", from = from, item = request.item, at = now}
    local admitted, admitReason = GiftRules.inboxAdmits(inbox, probe)
    if not admitted then
        audit("refused", from, to, request.item, nil, nil, admitReason)
        return false, GiftRules.toPublic(admitReason)
    end
    -- Durable daily counters (survive a server hop): checked and bumped in ONE transaction.
    local daily = "ok"
    local okIntent = updateKey(intentKey(from), function(raw: any)
        local intent = GiftRules.normalizeIntent(raw, now)
        local allowedToday, dailyReason = GiftRules.dailyAllows(intent, to)
        daily = dailyReason
        if not allowedToday then return nil end
        GiftRules.bumpDaily(intent, to)
        return intent
    end)
    if not okIntent then return false, "try_again" end
    if daily ~= "ok" then
        audit("refused", from, to, request.item, nil, nil, daily)
        return false, daily
    end
    audit("requested", from, to, request.item, nil, nil, nil)
    return true, "ok"
end

-- Adds one gift to the recipient's inbox, idempotently (the same gift id twice is one entry). Works for ANY valid UserId, including
-- one that has never played Be Dino: the key is simply created, with no expiry. Returns ok, code, giftId.
-- req = {source = "robux", giftId = "R"..PurchaseId, from, to, item, msg?, isFriend}  or  {source = "admin", from = adminUserId, to, item, msg?, crystals?, giftId?}.
-- The caller (BD-452 / BD-453) has already authorised the sender; for "admin" the caller must run AdminRules.isAdmin first.
function GiftService.send(req: any): (boolean, string, string?)
    if type(req) ~= "table" then return false, "bad_request", nil end
    if not sendOn(req.source) then return false, "disabled", nil end
    local request = req
    local source = request.source
    local now = clock()
    if source == "admin" then
        if not GiftRules.validUserId(request.from) then return false, "bad_request", nil end
        local window = adminWindows[request.from :: number]
        if window == nil then window = {start = 0, count = 0} adminWindows[request.from :: number] = window end
        if not GiftRules.windowAllow(window, now, Limits.AdminGrantsPerMinute, 60) then return false, "rate_limited", nil end
    end
    local giftId = request.giftId
    if giftId == nil and source == "admin" then
        giftId = "A" .. string.gsub(game:GetService("HttpService"):GenerateGUID(false), "[^%w]", "")
    end
    if not GiftRules.validUserId(request.to) then return false, "bad_request", nil end
    if source == "robux" and request.from == request.to then return false, "self", nil end
    local gift, why = GiftRules.newGift(source, request.from, request.item, request.msg, request.crystals, now, giftId)
    if gift == nil then return false, why, nil end
    local to = request.to :: number
    -- Recipient-side rules. After a Robux payment (receipt) the gift is queued even if the setting or a block changed since the prompt:
    -- preflight() refused BEFORE the prompt, claim re-checks and HOLDS it, so paid Robux are never refused here and never lost.
    -- An admin gift has no payment to protect and does not bypass a Roblox block (docs/134 s5), so it is refused here.
    if source == "admin" then
        local pref = readPref(to)
        if pref == nil then return false, "try_again", nil end
        if pref.blocked[gift.from] then
            audit("refused", gift.from, to, gift.item, gift.id, nil, "blocked")
            return false, GiftRules.toPublic("blocked"), nil
        end
    end
    local outcome = "ok"
    local ok = updateKey(inboxKey(to), function(raw: any)
        local inbox = GiftRules.normalizeInbox(raw)
        if inbox == nil then outcome = "store_corrupt" return nil end -- never write over a record we cannot read
        local admitted, admitReason = GiftRules.inboxAdmits(inbox, gift)
        outcome = admitReason
        if not admitted or admitReason == "duplicate" then return nil end
        inbox.gifts[gift.id] = gift
        return inbox
    end)
    if not ok then return false, "try_again", nil end
    if outcome == "duplicate" then return true, "duplicate", gift.id end
    if outcome ~= "ok" then
        audit("refused", gift.from, to, gift.item, gift.id, nil, outcome)
        return false, GiftRules.toPublic(outcome), nil
    end
    audit(if source == "admin" then "admin" else "queued", gift.from, to, gift.item, gift.id, nil, nil)
    print("[BD-GIFT] " .. tostring(source) .. " from=" .. tostring(gift.from) .. " to=" .. tostring(to) .. " item=" .. tostring(gift.item) .. " id=" .. tostring(gift.id))
    return true, "queued", gift.id
end

-- Username lookups are rate limited here so BD-452/BD-453 share one budget (docs/134 s2.1). Pure state, no store.
function GiftService.allowLookup(userId: number): (boolean, string)
    if not claimOn() then return false, "disabled" end
    if not GiftRules.validUserId(userId) then return false, "bad_request" end
    local state = lookupStates[userId]
    if state == nil then state = GiftRules.newLookupState() lookupStates[userId] = state end
    return GiftRules.lookupAllows(state, serverLookups, clock())
end

-- ------------------------------------------------------------------ revoke (GF16): refunds and chargebacks, admin only, idempotent
-- A pending gift is removed; a claimed one is taken back on the recipient's next claim (their server removes the skin and sets
-- claimedGifts[id] = "revoked"). The tombstone also stops a re-delivered receipt from re-adding the gift. Crystals already spent are not clawed back.
-- The caller (BD-452) has run AdminRules.isAdmin. itemHint = the catalogue id when the gift is no longer pending (the audit trail has it).
function GiftService.revoke(adminId: any, recipientId: any, giftId: any, itemHint: any): (boolean, string)
    if not claimOn() or Config.AdminGiftsEnabled ~= true then return false, "disabled" end
    if not GiftRules.validUserId(adminId) or not GiftRules.validUserId(recipientId) or not GiftRules.validId(giftId) then return false, "bad_request" end
    if itemHint ~= nil and (type(itemHint) ~= "string" or GiftRules.ById[itemHint] == nil) then return false, "bad_request" end
    local item: any = itemHint
    if item == nil then
        local ok, trail = readKey("audituser_" .. tostring(recipientId))
        if ok and type(trail) == "table" then
            for _, event in trail do
                if type(event) == "table" and event.giftId == giftId and type(event.item) == "string" then item = event.item end
            end
        end
    end
    local status = "revoked"
    local pendingItem: any = nil
    local ok = updateKey(inboxKey(recipientId :: number), function(raw: any)
        local inbox = GiftRules.normalizeInbox(raw)
        if inbox == nil then status = "store_corrupt" return nil end
        if inbox.revoked[giftId] ~= nil then status = "already_revoked" return nil end
        if GiftRules.count(inbox.revoked) >= Limits.RevokedCap then status = "tombstones_full" return nil end
        local pending = inbox.gifts[giftId]
        if type(pending) == "table" and type(pending.item) == "string" and GiftRules.ById[pending.item] ~= nil then pendingItem = pending.item end
        inbox.gifts[giftId] = nil
        inbox.revoked[giftId] = pendingItem or item or true
        status = if pending ~= nil then "revoked_pending" else "revoked"
        return inbox
    end)
    if not ok then return false, "try_again" end
    if status == "revoked" or status == "revoked_pending" then
        audit("revoked", adminId, recipientId, pendingItem or item, giftId, nil, nil)
        print("[BD-GIFT] revoke admin=" .. tostring(adminId) .. " to=" .. tostring(recipientId) .. " id=" .. tostring(giftId) .. " status=" .. status)
        return true, status
    end
    return status == "already_revoked", status
end

-- One read for the admin page (BD-452): the last AuditUserCap events where this user was sender or recipient.
function GiftService.auditFor(userId: number): (boolean, any)
    if not claimOn() or Config.AdminGiftsEnabled ~= true then return false, "disabled" end
    if not GiftRules.validUserId(userId) then return false, "bad_request" end
    local ok, trail = readKey("audituser_" .. tostring(userId))
    if not ok then return false, "try_again" end
    return true, if type(trail) == "table" then trail else {}
end

-- ------------------------------------------------------------------ the notice (minimal popup payload through the owner-only channel)
local function resolveName(userId: number): string?
    if nameResolver ~= nil then
        local ok, name = pcall(nameResolver, userId)
        return if ok and type(name) == "string" then name else nil
    end
    local ok, name = pcall(function()
        local info = game:GetService("UserService"):GetUserInfosByUserIdsAsync({userId})
        return info[1] and info[1].DisplayName
    end)
    return if ok and type(name) == "string" and name ~= "" then name else nil
end

local function showNext(player: any)
    local queue = notices[player]
    local notice = if queue then queue[1] else nil
    if notice == nil then
        PrivateState.set(player, "GiftNoticeJson", "")
        return
    end
    local entry = GiftRules.ById[notice.item]
    PrivateState.set(player, "GiftNoticeJson", game:GetService("HttpService"):JSONEncode({
        id = notice.id,
        line = GiftRules.noticeLine(notice.source, notice.name),
        name = GiftRules.shownName(notice.source, notice.name), -- BD-570: for "Mute <name>"; "" for a team gift. Resolved fresh, never stored.
        kind = if entry then entry.kind else "skin", -- BD-570: picks the registered icon
        item = if entry then entry.label else "",
        message = GiftRules.presetText(notice.msg) or "",
        more = #(queue :: {any}) - 1,
        canMute = notice.source == "robux",
        converted = notice.converted == true,
    }))
end

-- Queues every notice of one claim first, then shows the first one only if nothing was on screen (so "more" counts the rest).
local function queueNotices(player: any, list: {any})
    local queue = notices[player]
    if queue == nil then queue = {} notices[player] = queue end
    local wasEmpty = #queue == 0
    for _, notice in list do
        if #queue < Limits.InboxCap then table.insert(queue, notice) end
    end
    if wasEmpty then showNext(player) end
end

-- ------------------------------------------------------------------ claim
local function friendOf(player: any, senderId: number): boolean
    if friendChecker ~= nil then
        local ok, result = pcall(friendChecker, player, senderId)
        return ok and result == true
    end
    local ok, result = pcall(function() return player:IsFriendsWith(senderId) end)
    return ok and result == true
end

-- Returns ok, status, summary. Safe to call any time; one inbox read when the inbox is empty.
function GiftService.claim(player: any): (boolean, string, any)
    if not claimOn() then return false, "disabled", nil end
    if repository == nil or not repository.isLoaded(player) then return false, "profile_not_loaded", nil end
    if claiming[player] then return false, "busy", nil end
    claiming[player] = true
    local ok, a, b, c = pcall(function(): (boolean, string, any)
        local userId = player.UserId :: number
        local okRead, raw = readKey(inboxKey(userId))
        if not okRead then return false, "try_again", nil end
        if raw == nil then return true, "empty", nil end
        local inbox = GiftRules.normalizeInbox(raw)
        if inbox == nil then return false, "corrupt_inbox", nil end -- left exactly as it is
        if next(inbox.gifts) == nil and next(inbox.revoked) == nil then return true, "empty", nil end
        local pref = readPref(userId, true)
        if pref == nil then return false, "try_again", nil end
        local plan = {apply = {}, revoke = {}, claimedCap = Limits.ClaimedGiftsCap}
        local giftOf: {[string]: any} = {}
        local ordered: {any} = {}
        local summary: {[string]: number} = {applied = 0, converted = 0, already = 0, held = 0, revoked = 0, corrupt = 0}
        for id, gift in inbox.gifts do
            if inbox.revoked[id] ~= nil then continue end
            if not GiftRules.validGift(gift, id) then summary.corrupt += 1 continue end -- skipped, left in place, never applied
            table.insert(ordered, gift)
        end
        table.sort(ordered, function(x: any, y: any) if x.at ~= y.at then return x.at < y.at end return x.id < y.id end)
        for _, gift in ordered do
            local isFriend = pref.from == "friends" and gift.source == "robux" and friendOf(player, gift.from)
            local allowed, reason = GiftRules.recipientAllows(pref, gift.from, isFriend, gift.source)
            if allowed then
                local operation = GiftRules.operationFor(gift)
                if operation ~= nil then
                    table.insert(plan.apply, operation)
                    giftOf[gift.id] = gift
                end
            else
                summary.held += 1
                if not heldLogged[gift.id] then
                    heldLogged[gift.id] = true
                    audit("held", gift.from, userId, gift.item, gift.id, nil, reason)
                end
            end
        end
        local revokeIds: {string} = {}
        for id in inbox.revoked do table.insert(revokeIds, id) end
        table.sort(revokeIds)
        for _, id in revokeIds do
            table.insert(plan.revoke, {id = id, skin = GiftRules.skinOf(inbox.revoked[id])})
        end
        if #plan.apply == 0 and #plan.revoke == 0 then return true, "held", summary end
        local okApply, results = repository.applyGifts(player, plan)
        if not okApply then return false, tostring(results), nil end
        local clear: {string} = {}
        local clearTombstones: {string} = {}
        local newlyApplied: {any} = {}
        for _, operation in plan.apply do
            local result = results[operation.id]
            local gift = giftOf[operation.id]
            if result == "applied" or result == "converted" then
                summary[result] += 1
                table.insert(clear, operation.id)
                table.insert(newlyApplied, {gift = gift, converted = result == "converted"})
                audit("claimed", gift.from, userId, gift.item, gift.id, nil, if result == "converted" then "converted" else nil)
            elseif result == "already" then
                summary.already += 1
                table.insert(clear, operation.id)
            elseif result ~= nil then
                summary.held += 1
                if not heldLogged[operation.id] then
                    heldLogged[operation.id] = true
                    audit("held", gift.from, userId, gift.item, gift.id, nil, result)
                end
            end
        end
        for _, operation in plan.revoke do
            local result = results[operation.id]
            if result == "revoked" or result == "revoked_pending" or result == "already_revoked" then
                table.insert(clear, operation.id)
                table.insert(clearTombstones, operation.id)
                if result ~= "already_revoked" then
                    summary.revoked += 1
                    audit("revoked", nil, userId, nil, operation.id, nil, result)
                end
            end
        end
        if #clear > 0 then
            -- Harmless if this fails: the next claim answers "already" and removes them.
            updateKey(inboxKey(userId), function(rawNow: any)
                local current = GiftRules.normalizeInbox(rawNow)
                if current == nil then return nil end
                local changed = false
                for _, id in clear do
                    if current.gifts[id] ~= nil then current.gifts[id] = nil changed = true end
                end
                for _, id in clearTombstones do
                    if current.revoked[id] ~= nil then current.revoked[id] = nil changed = true end
                end
                return if changed then current else nil
            end)
        end
        local fresh: {any} = {}
        for _, applied in newlyApplied do
            local gift = applied.gift
            table.insert(fresh, {
                id = gift.id, source = gift.source, item = gift.item, msg = gift.msg, fromId = gift.from, converted = applied.converted,
                name = if gift.source == "robux" then resolveName(gift.from) else nil,
            })
        end
        if #fresh > 0 then queueNotices(player, fresh) end
        return true, "claimed", summary
    end)
    claiming[player] = nil
    if not ok then
        warn("[BD-GIFT] claim failed: " .. tostring(a))
        return false, "error", nil
    end
    return a, b, c
end

-- ------------------------------------------------------------------ the GiftAction remote (recipient controls only)
local Shapes: {[string]: {[string]: boolean}} = {
    get = {action = true}, -- BD-570: the Settings row reads the saved "Gifts from" value
    ack = {action = true},
    mute = {action = true},
    turnOff = {action = true},
    setFrom = {action = true, from = true},
    blocked = {action = true, ids = true},
}
local function fail(reason: string): any return {ok = false, reason = reason} end

function GiftService.handle(player: any, request: any, ...: any): any
    if not claimOn() then return fail("disabled") end
    if select("#", ...) > 0 or type(request) ~= "table" then return fail("bad_request") end
    local shape = if type(request.action) == "string" then Shapes[request.action] else nil
    if shape == nil then return fail("bad_request") end
    for key in request do
        if type(key) ~= "string" or not shape[key] then return fail("bad_request") end
    end
    local now = clock()
    local window = actionWindows[player]
    if window == nil then window = {start = 0, count = 0} actionWindows[player] = window end
    if not GiftRules.windowAllow(window, now, GiftService.ActionsPerWindow, GiftService.ActionWindowSeconds) then return fail("rate_limited") end
    if repository == nil or not repository.isLoaded(player) then return fail("profile_not_loaded") end
    local userId = player.UserId :: number
    local action = request.action :: string
    local queue = notices[player]
    local current = if queue then queue[1] else nil
    if action == "get" then
        local pref = readPref(userId)
        if pref == nil then return fail("try_again") end
        return {ok = true, from = pref.from}
    elseif action == "setFrom" then
        local ok, status = GiftService.setFrom(userId, request.from)
        return if ok then {ok = true} else fail(status)
    elseif action == "blocked" then
        local ok, status = GiftService.reportBlocked(userId, request.ids)
        if ok then blockedReported[player] = true end
        return if ok then {ok = true} else fail(status)
    end
    if action == "turnOff" then
        local ok, status = GiftService.setFrom(userId, "nobody")
        if not ok then return fail(status) end
    elseif action == "mute" then
        -- The client names nobody: the server mutes the sender of the notice that is on screen. Admin gifts cannot be muted.
        if current == nil or current.source ~= "robux" then return fail("nothing_to_mute") end
        local ok, status = GiftService.mute(userId, current.fromId)
        if not ok then return fail(status) end
    end
    if current ~= nil then
        table.remove(queue :: {any}, 1)
        showNext(player)
    end
    return {ok = true}
end

-- ------------------------------------------------------------------ test and admin hooks
function GiftService.setClock(fn: () -> number) clock = fn end
function GiftService.setNameResolver(fn: ((number) -> string?)?) nameResolver = fn end
function GiftService.setFriendChecker(fn: ((any, number) -> boolean)?) friendChecker = fn end
function GiftService.stats(): any return table.clone(stats) end
function GiftService.reset()
    giftStore, repository = nil, nil
    table.clear(prefCache) table.clear(promptWindows) table.clear(adminWindows) table.clear(lookupStates) table.clear(heldLogged)
    serverLookups = {start = 0, count = 0}
    stats.reads, stats.writes, stats.failures = 0, 0, 0
end

-- ------------------------------------------------------------------ start
function GiftService.start(repo: any): any
    if not claimOn() then return nil end -- flag off: no remote, no connection, no loop, no store
    repository = repo
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if folder == nil then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteFunction")
    remote.Name = "GiftAction"
    remote.OnServerInvoke = function(player: any, request: any, ...: any)
        local ok, response = pcall(GiftService.handle, player, request, ...)
        return if ok then response else fail("error")
    end
    remote.Parent = folder
    local function claimWhenLoaded(player: any)
        local waited = 0
        while player.Parent and player:GetAttribute("ProfileState") ~= "Loaded" and waited < 180 do
            task.wait(1)
            waited += 1
        end
        -- The first claim waits (briefly) for the client's Roblox block list, so a never-played recipient is protected at first join (GF12).
        -- If the list never comes (GetCore unavailable) the fallbacks are Mute and Nobody; that is logged once per server.
        local reportWait = 0
        while player.Parent and not blockedReported[player] and reportWait < 8 do
            task.wait(1)
            reportWait += 1
        end
        if player.Parent and not blockedReported[player] and not reportLogged then
            reportLogged = true
            warn("[BD-GIFT] no blocked-id report from a client; falling back to Mute and Nobody")
        end
        if player.Parent and player:GetAttribute("ProfileState") == "Loaded" then GiftService.claim(player) end
    end
    Players.PlayerAdded:Connect(function(player: any) task.spawn(claimWhenLoaded, player) end)
    Players.PlayerRemoving:Connect(function(player: any)
        notices[player], claiming[player], actionWindows[player], blockedReported[player] = nil, nil, nil, nil -- PrivateState values go with the profile release
    end)
    for _, player in Players:GetPlayers() do task.spawn(claimWhenLoaded, player) end
    task.spawn(function()
        while true do
            task.wait(GiftService.ClaimSeconds)
            for _, player in Players:GetPlayers() do
                if player:GetAttribute("ProfileState") == "Loaded" then task.spawn(GiftService.claim, player) end
            end
        end
    end)
    return remote
end

return GiftService
