--!strict
-- BD-064/BD-065 server surface: the FusionAction RemoteFunction in
-- ReplicatedStorage.BeDinoRemotes. Contract: docs/52-fusion-remote-contract.md.
-- Every argument is validated here; ownership, recipes, odds and commits stay in
-- ProfileRepository/IdentityFusion. Clients never supply traits, odds or result IDs.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local FusionService = {}
FusionService.MaxListLimit = 200
FusionService.DefaultListLimit = 100
FusionService.MaxDonorIds = 6 -- largest recipe (Gold = 6 Base); IdentityFusion enforces the exact per-recipe count
FusionService.MaxIdLength = 120
FusionService.MaxDigestLength = 64
FusionService.MaxTokenLength = 80
FusionService.MaxStageLength = 16

local repository: any = nil
local windows: {[any]: {startedAt: number, count: number}} = {}
local clock = os.clock

-- Allowed keys per action; anything else is a bad request.
local Shapes = {
    list = {action = true, cursor = true, limit = true},
    details = {action = true, instanceId = true},
    quote = {action = true, targetStage = true, donorIds = true},
    fuse = {action = true, token = true, targetStage = true, donorIds = true, quoteDigest = true, consentDigest = true},
}

local function fail(reason: string)
    return {ok = false, reason = reason}
end

local function boundedString(value: any, maxLength: number): boolean
    return type(value) == "string" and #value >= 1 and #value <= maxLength
end

local function integer(value: any, min: number, max: number): boolean
    return type(value) == "number" and value == value and value % 1 == 0 and value >= min and value <= max
end

local function donorList(value: any): boolean
    if type(value) ~= "table" then return false end
    local n = #value
    if n < 1 or n > FusionService.MaxDonorIds then return false end
    local count = 0
    for key, id in value do
        count += 1
        if type(key) ~= "number" or not boundedString(id, FusionService.MaxIdLength) then return false end
    end
    return count == n
end

-- Fixed-window per-player limiter (PROVISIONAL Config values).
local function allowed(player: any): boolean
    local now = clock()
    -- BD-618 (f): keyed by UserId and kept after the player leaves, so a rejoin does not give a fresh window (memory only; stale windows are pruned below).
    local okId, userId = pcall(function() return player.UserId end)
    local key = if okId and type(userId) == "number" then userId else player
    local window = windows[key]
    if not window or now - window.startedAt >= Config.FusionRateWindowSeconds then
        for other, old in windows do
            if now - old.startedAt >= 2 * Config.FusionRateWindowSeconds then windows[other] = nil end
        end
        window = {startedAt = now, count = 0}
        windows[key] = window
    end
    window.count += 1
    return window.count <= Config.FusionRequestsPerWindow
end

local function validate(request: any): string?
    if type(request) ~= "table" then return "bad_request" end
    local shape = Shapes[request.action]
    if type(request.action) ~= "string" or not shape then return "bad_request" end
    for key in request do
        if type(key) ~= "string" or not shape[key] then return "bad_request" end
    end
    local action = request.action
    if action == "list" then
        if request.cursor ~= nil and not integer(request.cursor, 0, 2 ^ 53) then return "bad_request" end
        if request.limit ~= nil and not integer(request.limit, 1, FusionService.MaxListLimit) then return "bad_request" end
    elseif action == "details" then
        if not boundedString(request.instanceId, FusionService.MaxIdLength) then return "bad_request" end
    else
        if not boundedString(request.targetStage, FusionService.MaxStageLength) or not donorList(request.donorIds) then
            return "bad_request"
        end
        if action == "fuse" then
            if not boundedString(request.token, FusionService.MaxTokenLength)
                or not boundedString(request.quoteDigest, FusionService.MaxDigestLength)
                or (request.consentDigest ~= nil and not boundedString(request.consentDigest, FusionService.MaxDigestLength)) then
                return "bad_request"
            end
        end
    end
    return nil
end

local function copyList(list: {string}): {string}
    local result = {}
    for i, id in list do result[i] = id end
    return result
end

local function exactOdds(odds: any)
    return {shiny = odds.shiny, big = odds.big, mutation = table.clone(odds.mutation), noMutation = odds.noMutation,
        primaryColor = table.clone(odds.primaryColor),
        secondaryColor = table.clone(odds.secondaryColor)}
end

local function handleAction(player: any, request: any)
    local action = request.action
    if action == "list" then
        local page, reason = repository.listDinosaurs(player, request.cursor, request.limit or FusionService.DefaultListLimit)
        if not page then return fail(reason or "fusion_disabled") end
        return {ok = true, dinosaurs = page.dinosaurs, nextCursor = page.nextCursor}
    elseif action == "details" then
        local details, reason = repository.fusionDetails(player, request.instanceId)
        if not details then return fail(reason or "donor_missing") end
        return {ok = true, dinosaur = details}
    elseif action == "quote" then
        local quote, reason = repository.quoteFusion(player, request.targetStage, copyList(request.donorIds))
        if not quote then return fail(reason or "bad_request") end
        if type(quote.odds) ~= "table" or type(quote.oddsVersion) ~= "string" then return fail("odds_not_approved") end
        if Config.ObjectivesEnabled == true then require(script.Parent.ObjectiveService).recordFusionUse(player) end -- BD-074: the server priced a full, owned donor set (the menu asks only then)
        return {ok = true, quote = {speciesId = quote.speciesId, patternId = quote.patternId, targetStage = quote.targetStage,
            donorIds = quote.donorIds, lossManifest = quote.lossManifest, consentRequired = quote.consentRequired,
            consentDigest = quote.consentDigest, quoteDigest = quote.quoteDigest, recipeVersion = quote.recipeVersion,
            oddsVersion = quote.oddsVersion, odds = exactOdds(quote.odds), cosmeticNotice = quote.cosmeticNotice}}
    end
    -- fuse: only whitelisted fields reach the repository.
    local ok, result, status = repository.fuseDinosaurs(player, {token = request.token, targetStage = request.targetStage,
        donorIds = copyList(request.donorIds), quoteDigest = request.quoteDigest, consentDigest = request.consentDigest})
    if not ok or type(result) ~= "table" then return fail(status or "save_failed") end
    return {ok = true, status = status, result = {resultId = result.resultId, targetStage = result.targetStage,
        speciesId = result.speciesId, patternId = result.patternId,
        traits = {genes = table.clone(result.traits.genes), big = result.traits.big, shiny = result.traits.shiny,
            mutationId = result.traits.mutationId}, oddsVersion = result.oddsVersion}}
end

-- Entry point for OnServerInvoke (and offline tests). Never throws to the client.
function FusionService.handle(player: any, request: any, ...)
    if not repository then return fail("fusion_disabled") end
    if select("#", ...) ~= 0 then return fail("bad_request") end
    if not allowed(player) then return fail("rate_limited") end
    local invalid = validate(request)
    if invalid then return fail(invalid) end
    local ok, response = pcall(handleAction, player, request)
    if not ok then
        warn("[Be Dino] FusionAction failed: " .. tostring(response))
        return fail("save_failed")
    end
    return response
end

-- Test hook: deterministic clock for the rate limiter.
function FusionService.setClock(fn: () -> number)
    clock = fn
    windows = {}
end

function FusionService.start(profileRepository)
    repository = profileRepository
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local existing = folder:FindFirstChild("FusionAction")
    if existing and not existing:IsA("RemoteFunction") then existing:Destroy() existing = nil end
    local remote = existing or Instance.new("RemoteFunction")
    remote.Name = "FusionAction"
    remote.Parent = folder
    remote.OnServerInvoke = function(player, ...)
        return FusionService.handle(player, ...)
    end
    return remote
end

return FusionService
