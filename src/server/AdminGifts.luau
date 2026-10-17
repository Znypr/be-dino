--!strict
-- BD-452 (docs/134 s5, docs/79): the admin "Gift" page, server side. Free gifts from the team to any Roblox user, online, offline or never
-- played, through the SAME inbox as every gift: this module only calls GiftService.send / revoke / auditFor / allowLookup, it never opens a
-- store, a profile or a currency itself.
--
-- ORDER OF CHECKS in handle(): (1) is this player an admin (the server list built from AdminRules.isAdmin, i.e. the UserId allow-list, the
-- owner, group rank 255 or unpublished Studio), THEN (2) the flags, THEN the request shape, THEN the throttle. A non-admin is refused before
-- anything else runs, so there is no store request, no lookup and no log line for them.
--
-- FLAG-OFF IDENTITY: start() returns nil at once unless GiftClaimEnabled, AdminGiftsEnabled and AdminPanelEnabled are all true. Nothing is
-- created (no remote), so the client never builds the Gift page. tools/verify_gifts.py proves it.
--
-- LABEL: every admin gift reads "A gift from the Be Dino team!" (GiftRules.TeamLine). No request key can set a label or a sender: the shape
-- check rejects unknown keys and the gift is built from the caller's own UserId. Admin gifts bypass the recipient setting and mute, NOT a
-- Roblox block (GiftService.send enforces that and answers the one public refusal code).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local GiftRules = require(ReplicatedStorage.Shared.GiftRules)
local PageRules = require(ReplicatedStorage.Shared.AdminGiftRules)
local GiftService = require(script.Parent.GiftService)

local AdminGifts = {}

local isAdmin: ((any) -> boolean)? = nil
local lookupFn: ((string) -> (number?, string?, string?))? = nil
local clock: () -> number = function() return os.clock() end
-- Per admin: who they picked (pending until they tap Yes) and who they confirmed. Weak keys: a leaving admin takes both with them.
local pending: {[any]: {userId: number, displayName: string, username: string}} = setmetatable({}, {__mode = "k"}) :: any
local confirmed: {[any]: {userId: number, displayName: string, username: string}} = setmetatable({}, {__mode = "k"}) :: any
local lastRequest: {[any]: number} = setmetatable({}, {__mode = "k"}) :: any

local function giftsOn(): boolean
    return Config.GiftClaimEnabled == true and Config.AdminGiftsEnabled == true and Config.AdminPanelEnabled == true
end
local function fail(reason: string): any
    return {ok = false, reason = reason}
end
local function log(admin: any, action: string, detail: string)
    print("[BD-GIFT] admin-page " .. action .. " admin=" .. tostring(admin.UserId) .. " " .. detail)
end

-- Username to public profile. UserIds only leave this function through the answer to the admin; nothing here is stored or logged.
local function resolve(name: string): (number?, string?, string?)
    if lookupFn ~= nil then return lookupFn(name) end
    local okId, userId = pcall(function() return Players:GetUserIdFromNameAsync(name) end)
    if not okId or not GiftRules.validUserId(userId) then return nil, "not_found", nil end
    local okInfo, info = pcall(function() return game:GetService("UserService"):GetUserInfosByUserIdsAsync({userId}) end)
    local first = if okInfo and type(info) == "table" then info[1] else nil
    if first == nil or type(first.DisplayName) ~= "string" or type(first.Username) ~= "string" then return nil, "try_again", nil end
    return userId :: number, first.DisplayName, first.Username
end

local function pickTarget(admin: any, request: any): any
    if not GiftRules.validUserId(request.userId) then return fail("bad_request") end
    local other = Players:GetPlayerByUserId(request.userId)
    if other == nil then return fail("not_here") end
    confirmed[admin] = nil
    pending[admin] = {userId = request.userId, displayName = other.DisplayName, username = other.Name}
    return {ok = true, userId = request.userId, displayName = other.DisplayName, username = other.Name}
end

local function lookupTarget(admin: any, request: any): any
    if not PageRules.validName(request.name) then return fail("bad_name") end
    local allowed, why = GiftService.allowLookup(admin.UserId)
    if not allowed then return fail(why) end
    local userId, second, third = resolve(request.name)
    -- (nil, code, nil) is a failure; (id, displayName, username) is a hit.
    if userId == nil or second == nil or third == nil then return fail(second or "not_found") end
    confirmed[admin] = nil
    pending[admin] = {userId = userId, displayName = second, username = third}
    return {ok = true, userId = userId, displayName = second, username = third}
end

-- "Yes, that's them": only the person the admin just picked or looked up can be confirmed, and only that person can be sent a gift.
local function confirmTarget(admin: any, request: any): any
    local chosen = pending[admin]
    if chosen == nil or chosen.userId ~= request.userId then return fail("not_confirmed") end
    confirmed[admin] = chosen
    pending[admin] = nil
    return {ok = true, userId = chosen.userId, displayName = chosen.displayName, username = chosen.username}
end

local function sendGift(admin: any, request: any): any
    local who = confirmed[admin]
    if who == nil or who.userId ~= request.to then return fail("not_confirmed") end
    if type(request.item) ~= "string" or GiftRules.ById[request.item] == nil then return fail("unknown_item") end
    local crystals = request.crystals
    if request.item == GiftRules.CustomCrystalsId then
        if not PageRules.amountOk(crystals) then return fail("bad_amount") end
    elseif crystals ~= nil then
        return fail("bad_amount")
    end
    if not GiftRules.validMessage(request.msg) then return fail("bad_message") end
    -- Built from the admin's own UserId; the client can set none of source, sender, id or label.
    local ok, code, giftId = GiftService.send({
        source = "admin", from = admin.UserId, to = who.userId, item = request.item, crystals = crystals, msg = request.msg,
    })
    log(admin, "send", "to=" .. tostring(who.userId) .. " item=" .. request.item .. " result=" .. tostring(code))
    if not ok then return fail(code) end
    return {ok = true, status = code, giftId = giftId, label = GiftRules.TeamLine}
end

local function revokeGift(admin: any, request: any): any
    if not GiftRules.validUserId(request.to) or not GiftRules.validId(request.giftId) then return fail("bad_request") end
    if request.item ~= nil and (type(request.item) ~= "string" or GiftRules.ById[request.item] == nil) then return fail("bad_request") end
    local ok, status = GiftService.revoke(admin.UserId, request.to, request.giftId, request.item)
    log(admin, "revoke", "to=" .. tostring(request.to) .. " id=" .. tostring(request.giftId) .. " result=" .. tostring(status))
    if not ok then return fail(status) end
    return {ok = true, status = status}
end

local function auditUser(admin: any, request: any): any
    if not GiftRules.validUserId(request.userId) then return fail("bad_request") end
    local ok, trail = GiftService.auditFor(request.userId)
    log(admin, "audit", "user=" .. tostring(request.userId) .. " result=" .. (if ok then "ok" else tostring(trail)))
    if not ok then return fail(tostring(trail)) end
    return {ok = true, events = PageRules.cleanHistory(trail)}
end

function AdminGifts.handle(player: any, request: any, ...: any): any
    if isAdmin == nil or isAdmin(player) ~= true then return fail("not_admin") end
    if not giftsOn() then return fail("disabled") end
    if select("#", ...) > 0 then return fail("bad_request") end
    local action = PageRules.shapeOk(request)
    if action == nil then return fail("bad_request") end
    local now = clock()
    if now - (lastRequest[player] or -1) < PageRules.MinGapSeconds then return fail("busy") end
    lastRequest[player] = now
    if action == "pick" then return pickTarget(player, request)
    elseif action == "lookup" then return lookupTarget(player, request)
    elseif action == "confirm" then return confirmTarget(player, request)
    elseif action == "send" then return sendGift(player, request)
    elseif action == "revoke" then return revokeGift(player, request)
    end
    return auditUser(player, request)
end

-- Test hooks.
function AdminGifts.setLookup(fn: ((string) -> (number?, string?, string?))?) lookupFn = fn end
function AdminGifts.setClock(fn: () -> number) clock = fn end

-- Called by AdminService.start with the folder for the remote and the server's admin test. Returns nil (creating nothing) unless all
-- three flags are on.
function AdminGifts.start(folder: Instance, admin: (any) -> boolean): any
    if not giftsOn() then return nil end
    isAdmin = admin
    local remote = Instance.new("RemoteFunction")
    remote.Name = PageRules.RemoteName
    remote.OnServerInvoke = function(player: any, request: any, ...: any)
        local ok, response = pcall(AdminGifts.handle, player, request, ...)
        return if ok then response else fail("error")
    end
    remote.Parent = folder
    return remote
end

return AdminGifts
