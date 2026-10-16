--!strict
-- docs/133 DEMO TRIGGERS (trailer clips). DEV ONLY: start() returns before creating anything unless this is an UNPUBLISHED Studio
-- session (RunService:IsStudio() and game.GameId == 0) AND Config.DemoDirectorEnabled (false in every committed build, pinned off
-- by tools/release_profiles.py). Owner-local: only the first player in the session may use it. The remote is a RemoteFunction
-- 'DemoTrigger' (created only when active). Eggs go through ProfileRepository.demoGrantEggs, which banks them with the same
-- bankEggs/queue path a real run settlement uses, so the real HatchSequence, reveal ladder, RareHatchService and NEW! ribbon play.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local HttpService = game:GetService("HttpService")
local Config = require(ReplicatedStorage.Shared.Config)
local ProgressionConfig = require(ReplicatedStorage.Shared.ProgressionConfig)
local EggGenetics = require(ReplicatedStorage.Shared.EggGenetics)

local DemoTriggerService = {}

local MAX_EGGS = 60

local function rarityIndex(name: any): number?
    if typeof(name) ~= "string" then return nil end
    return table.find(Config.SpeciesRarityNames, name)
end

local function conditionFor(name: any)
    if name == nil then name = "Normal" end
    if typeof(name) ~= "string" then return nil end
    for _, row in ProgressionConfig.Conditions do
        if string.lower(row.name) == string.lower(name) or row.id == string.lower(name) then return row end
    end
    return nil
end

local function weatherForMutation(mutationId: string): string?
    for _, event in ProgressionConfig.Weather do
        if event.mutation == mutationId then return event.id end
    end
    return nil
end

-- Pure and deterministic: spec list -> egg metadata list (nil + reason when anything is invalid).
function DemoTriggerService.buildEggs(specs: any, runId: string): ({any}?, string)
    if typeof(specs) ~= "table" or #specs < 1 or #specs > MAX_EGGS then return nil, "bad_eggs" end
    local perRarity: {[number]: number} = {}
    local built = {}
    for i, spec in specs do
        if typeof(spec) ~= "table" then return nil, "bad_egg" end
        local rank = rarityIndex(spec.rarity)
        if not rank then return nil, "bad_rarity" end
        if (spec.shiny ~= nil and typeof(spec.shiny) ~= "boolean") or (spec.big ~= nil and typeof(spec.big) ~= "boolean") then return nil, "bad_flag" end
        local mutationId = spec.mutationId or ""
        if typeof(mutationId) ~= "string" then return nil, "bad_mutation" end
        local eventId = "clear"
        if mutationId ~= "" then
            local found = weatherForMutation(mutationId)
            if not found then return nil, "bad_mutation" end
            eventId = found
        end
        local condition = conditionFor(spec.condition)
        if not condition then return nil, "bad_condition" end
        -- Species of that rarity, cycled in config order so repeated rarities show different dinosaurs.
        local pool = {}
        for _, speciesId in Config.SpeciesOrder do
            if Config.SpeciesRarities[speciesId] == rank then table.insert(pool, speciesId) end
        end
        if #pool == 0 then return nil, "no_species" end
        local seen = perRarity[rank] or 0
        perRarity[rank] = seen + 1
        local speciesId = pool[seen % #pool + 1]
        local colors, patterns = ProgressionConfig.EggColors, EggGenetics.Patterns
        local primary = colors[(i - 1) % #colors + 1].id
        local secondary = colors[(i * 3) % #colors + 1].id
        local eggId = string.format("%s-%d", runId, i)
        table.insert(built, {
            eggId = eggId, kind = "run_egg",
            eventId = eventId, mutationId = mutationId,
            reward = {rewardConfigVersion = Config.RunRewardConfigVersion, speciesId = speciesId, mutationId = "base", count = 1},
            shiny = spec.shiny == true, big = spec.big == true,
            genes = {conditionId = condition.id, hatchSuccess = condition.hatchChance == 1,
                primaryColorId = primary, secondaryColorId = secondary,
                blend = if primary == secondary then 100 else 60, patternId = patterns[(i - 1) % #patterns + 1]},
            traitRollVersion = "bd045-genes-v2",
            source = {kind = "run", runId = runId, ordinal = i, originalEggId = eggId},
        })
    end
    table.sort(built, function(a, b) -- same order rule as a real settlement: rarity ascending, then ordinal
        local ar, br = Config.SpeciesRarities[a.reward.speciesId], Config.SpeciesRarities[b.reward.speciesId]
        return if ar == br then a.source.ordinal < b.source.ordinal else ar < br
    end)
    return built, "ok"
end

-- Waits (up to `seconds`) for the freshly spawned dinosaur, then starts a run through the one real start path (RunLifecycle.requestStart:
-- the same call the Explore Island button uses), so the character is Active on the island with class movement rules live.
local function startRunWhenReady(player: Player, seconds: number): boolean
    local RunLifecycle = require(script.Parent.RunLifecycle)
    local deadline = os.clock() + seconds
    while os.clock() < deadline and player.Parent do
        if RunLifecycle.requestStart(player) then return true end
        task.wait(0.4)
    end
    return false
end

function DemoTriggerService.start(profileRepository)
    if not (RunService:IsStudio() and game.GameId == 0 and Config.DemoDirectorEnabled == true) then return end
    local ProgressionService = require(script.Parent.ProgressionService)
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteFunction")
    remote.Name = "DemoTrigger"
    remote.Parent = folder

    local owner: Player? = nil -- owner-local: the first player of this Studio session
    local last = 0
    remote.OnServerInvoke = function(player: Player, request: any): (boolean, string)
        if not owner then owner = player end
        if player ~= owner then return false, "not_owner" end
        if typeof(request) ~= "table" or typeof(request.kind) ~= "string" then return false, "bad_request" end
        if os.clock() - last < 0.25 then return false, "rate_limited" end
        last = os.clock()
        local kind = request.kind
        if kind == "hatchParty" then
            local eggs, reason = DemoTriggerService.buildEggs(request.eggs, "demo-" .. string.sub(HttpService:GenerateGUID(false), 1, 8))
            if not eggs then return false, reason end
            return profileRepository.demoGrantEggs(player, eggs, request.newFind == true)
        elseif kind == "equipSpecies" then
            local ok, status = profileRepository.demoEquip(player, request.speciesId)
            if ok then
                local runAfter = request.startRun == true
                task.spawn(function()
                    local loaded, err = pcall(function() player:LoadCharacterAsync() end)
                    if not loaded then warn("[DemoTrigger] respawn failed: " .. tostring(err)) return end
                    if runAfter and not startRunWhenReady(player, 15) then warn("[DemoTrigger] run did not start") end
                end)
            end
            return ok, status
        elseif kind == "startRun" then
            return startRunWhenReady(player, 10), "run"
        elseif kind == "setWeather" then
            if request.id == "clear" then ProgressionService.adminStopWeather() return true, "cleared" end
            if typeof(request.id) ~= "string" then return false, "bad_weather" end
            return ProgressionService.adminStartWeather(request.id, ProgressionConfig.WeatherDuration), "weather"
        elseif kind == "giveCrystals" then
            return profileRepository.demoAddCrystals(player, request.amount)
        end
        return false, "unknown_kind"
    end
    print("[DemoTrigger] active (unpublished Studio, demo flag on): RemoteFunction BeDinoRemotes.DemoTrigger")
end

return DemoTriggerService
