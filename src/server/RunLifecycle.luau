--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Config = require(ReplicatedStorage.Shared.Config)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)

local RunLifecycle = {}
local PrivateState = require(script.Parent.PrivateState)
local lastExitRequest: {[Player]: number} = {}
local requestEndRun: RemoteEvent? = nil
local settleRun = nil
-- BD-090: server-side run start times (server clock); never replicated, never client-reported.
local runStartedAt: {[string]: number} = {}

function RunLifecycle.prepareSanctuary(player: Player, character: Model)
    character:SetAttribute("RunState", "Sanctuary")
    character:SetAttribute("GrowthScore", 0)
    character:SetAttribute("CatchScore", 0)
    character:SetAttribute("FoodCatchCarry", 0)
    character:SetAttribute("WeatherLootCarry",0)
    character:SetAttribute("RunEggEvents","[]")
    player:SetAttribute("Location", "Sanctuary")
end

local function activeCharacter(player: Player): Model?
    local character = player.Character
    if not character or character:GetAttribute("RunState") ~= "Active" then return nil end
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not humanoid or humanoid.Health <= 0 then return nil end
    return character
end

-- BD-210 run-start gate: server terrain built, and the client confirmed its local terrain (or the timeout passed).
function RunLifecycle.worldReady(player: Player): boolean
    if workspace:GetAttribute("IslandTerrainReady") ~= true then return false end
    if player:GetAttribute("WorldReady") == true then return true end
    local joinedAt = player:GetAttribute("JoinedAt")
    return typeof(joinedAt) == "number" and os.clock() - joinedAt >= Config.WorldReadyTimeoutSeconds
end

function RunLifecycle.configureSettlement(callback)
    settleRun = callback
end

function RunLifecycle.begin(player: Player, character: Model)
    if player:GetAttribute("ProfileState") ~= "Loaded" then return end
    -- BD-044: a run starts only when the egg bank and pending-nest list have room for a
    -- maximum run, so settlement never has to drop or refuse earned eggs/nests.
    local blocked = PrivateState.get(player, "RunStartBlocked")
    if typeof(blocked) == "string" and blocked ~= "" then
        player:SetAttribute("LastRunStartStatus", blocked)
        return
    end
    if character:GetAttribute("RunId") ~= nil then return end
    local newRunId = HttpService:GenerateGUID(false)
    character:SetAttribute("RunId", newRunId)
    runStartedAt[newRunId] = workspace:GetServerTimeNow()
    player:SetAttribute("Location", "Island")
    character:SetAttribute("RunState", "Active")
    character:SetAttribute("GrowthScore", 0)
    character:SetAttribute("CatchScore", 0)
    character:SetAttribute("FoodCatchCarry", 0)
    character:SetAttribute("WeatherLootCarry",0)
    character:SetAttribute("RunEggEvents","[]")
    character:SetAttribute("SpawnProtectionEndsAt", workspace:GetServerTimeNow() + Config.SpawnProtectionSeconds)

    task.spawn(function()
        local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
        if not humanoid or player.Character ~= character then return end
        humanoid.Died:Connect(function()
            RunLifecycle.tryEnd(player, character, "Death")
        end)
    end)
end

function RunLifecycle.isActive(character: Model): boolean
    return character:GetAttribute("RunState") == "Active"
end

function RunLifecycle.isProtected(character: Model, now: number?): boolean
    local raw = character:GetAttribute("SpawnProtectionEndsAt")
    local endsAt = if typeof(raw) == "number" then raw else 0
    return endsAt > (now or workspace:GetServerTimeNow())
end

local function settlementSnapshot(character: Model)
    local runId = character:GetAttribute("RunId")
    local catchScore = character:GetAttribute("CatchScore")
    if typeof(runId) ~= "string" then return nil end
    if typeof(catchScore) ~= "number" or catchScore % 1 ~= 0 then return nil end
    local ok,events=pcall(function() return HttpService:JSONDecode(character:GetAttribute("RunEggEvents") or "[]") end)
    local startedAt = runStartedAt[runId]
    runStartedAt[runId] = nil
    return {
        runId = runId,
        runSeconds = if startedAt then math.max(0, workspace:GetServerTimeNow() - startedAt) else 0, -- unknown start = 0 s = no nest
        catchScore = math.clamp(catchScore, 0, Config.RunEggMaxPerRun), -- one run egg per catch
        eggEvents=if ok and typeof(events)=="table" then events else {},
    }
end

local function respawnAfterSettlement(player: Player, character: Model, snapshot, reason: string)
    task.spawn(function()
        local ok = true
        if settleRun then
            ok = settleRun(player, snapshot.runId, snapshot.catchScore, reason, snapshot.eggEvents, snapshot.runSeconds)
        end
        if not ok then
            if player.Parent and player:GetAttribute("ProfileState") == "Loaded" then
                player:SetAttribute("ProfileState", "SaveFailed")
            end
            return
        end

        character:SetAttribute("RunState", "Settled")
        if not player.Parent then return end
        task.wait(Config.RespawnDelaySeconds)
        if player.Parent and player:GetAttribute("ProfileState") == "Loaded" then
            local loaded, err = pcall(function()
                player:LoadCharacterAsync()
            end)
            if not loaded then
                warn("[Be Dino] respawn failed: " .. tostring(err))
            end
        end
    end)
end

-- BD-359: the settlement failed its whole retry window and was committed later by the lease renew tick. Finish what
-- respawnAfterSettlement skipped on failure: mark the run Settled and bring the dinosaur back.
function RunLifecycle.recoverAfterSettlement(player: Player)
    local character = player.Character
    if character and character:GetAttribute("RunState") == "Ending" then character:SetAttribute("RunState", "Settled") end
    task.spawn(function()
        task.wait(Config.RespawnDelaySeconds)
        if player.Parent and player:GetAttribute("ProfileState") == "Loaded" then
            local loaded, err = pcall(function() player:LoadCharacterAsync() end)
            if not loaded then warn("[Be Dino] respawn failed: " .. tostring(err)) end
        end
    end)
end

function RunLifecycle.tryEnd(player: Player, character: Model, reason: string, sourceUserId: number?): boolean
    if player.Character ~= character or character:GetAttribute("RunState") ~= "Active" then
        return false
    end
    local snapshot = settlementSnapshot(character)
    if not snapshot then
        return false
    end

    character:SetAttribute("RunState", "Ending")
    player:SetAttribute("LastRunEndReason", reason)
    player:SetAttribute("LastRunCatchScore", snapshot.catchScore)
    local growthScore = character:GetAttribute("GrowthScore")
    player:SetAttribute("LastRunGrowthScore", if typeof(growthScore) == "number" then growthScore else 0)
    player:SetAttribute("LastRunId", snapshot.runId)
    player:SetAttribute("LastRunEndAt", workspace:GetServerTimeNow())
    player:SetAttribute("LastPredatorUserId", sourceUserId or 0)

    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if humanoid and humanoid.Health > 0 then
        humanoid.Health = 0
    end

    respawnAfterSettlement(player, character, snapshot, reason)
    return true
end

function RunLifecycle.endForDisconnect(player: Player): string
    local character = player.Character
    if not character then return "none" end
    if character:GetAttribute("RunState") == "Ending" then
        return "busy"
    end
    if character:GetAttribute("RunState") ~= "Active" then
        return "none"
    end
    local snapshot = settlementSnapshot(character)
    if not snapshot then return "none" end

    character:SetAttribute("RunState", "Ending")
    player:SetAttribute("LastRunEndReason", "Disconnect")
    player:SetAttribute("LastRunCatchScore", snapshot.catchScore)
    local growthScore = character:GetAttribute("GrowthScore")
    player:SetAttribute("LastRunGrowthScore", if typeof(growthScore) == "number" then growthScore else 0)
    if settleRun then
        local ok = settleRun(player, snapshot.runId, snapshot.catchScore, "Disconnect", snapshot.eggEvents, snapshot.runSeconds)
        return if ok then "settled" else "failed"
    end
    return "settled"
end

-- BD-052: without the old stay-still channel, Home must not be an instant escape from a
-- predator that is already closing in. Mirrors PredationService's size rule.
local function predatorNearby(player: Player, character: Model): boolean
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root or not root:IsA("BasePart") then return false end
    local rawScore = character:GetAttribute("GrowthScore")
    local score = if typeof(rawScore) == "number" then rawScore else 0
    local now = workspace:GetServerTimeNow()
    if RunLifecycle.isProtected(character, now) then return false end
    for _, other in Players:GetPlayers() do
        local otherCharacter = if other ~= player then activeCharacter(other) else nil
        local otherRoot = if otherCharacter then otherCharacter:FindFirstChild("HumanoidRootPart") else nil
        if otherCharacter and otherRoot and otherRoot:IsA("BasePart") and not RunLifecycle.isProtected(otherCharacter, now) then
            local rawOther = otherCharacter:GetAttribute("GrowthScore")
            local otherScore = if typeof(rawOther) == "number" then rawOther else 0
            if otherScore > score and otherScore >= score * Config.PredationScoreMultiplier
                and (otherRoot.Position - root.Position).Magnitude <= Config.HomeThreatRadius then
                return true
            end
        end
    end
    return false
end

-- The one run-start path: the RequestStartRun remote and the cave Island Gate (BD-290) both call this, so every check and
-- the exactly-once begin() live in one place. Returns true when the run began.
function RunLifecycle.requestStart(player: Player): boolean
    if player:GetAttribute("ProfileState") ~= "Loaded" then return false end
    local character = player.Character
    if not character or character:GetAttribute("RunState") ~= "Sanctuary" or not character:GetAttribute("DinoAttached") then return false end
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not humanoid or humanoid.Health <= 0 then return false end
    -- BD-210: never drop a dinosaur onto the island before the terrain exists on the server and, unless the
    -- client is unusually slow, before this client reports the terrain under the spawn as loaded.
    if not RunLifecycle.worldReady(player) then
        player:SetAttribute("LastRunStartStatus", "WorldLoading")
        return false
    end
    require(script.Parent.FallRecovery).teleport(player, character, CFrame.new(SpawnGeometry.islandPoint(Layout)))
    RunLifecycle.begin(player, character)
    return true
end

function RunLifecycle.start()
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local startRemote = Instance.new("RemoteEvent")
    startRemote.Name = "RequestStartRun"
    startRemote.Parent = folder
    startRemote.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 0 then return end
        RunLifecycle.requestStart(player)
    end)

    local readyRemote = Instance.new("RemoteEvent")
    readyRemote.Name = "ClientWorldReady"
    readyRemote.Parent = folder
    readyRemote.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 0 then return end
        player:SetAttribute("WorldReady", true)
    end)
    local function joined(player: Player) player:SetAttribute("JoinedAt", os.clock()) end
    Players.PlayerAdded:Connect(joined)
    for _, player in Players:GetPlayers() do if player:GetAttribute("JoinedAt") == nil then joined(player) end end

    local existing = folder:FindFirstChild("RequestEndRun")
    if existing and existing:IsA("RemoteEvent") then
        requestEndRun = existing
    else
        if existing then existing:Destroy() end
        local remote = Instance.new("RemoteEvent")
        remote.Name = "RequestEndRun"
        remote.Parent = folder
        requestEndRun = remote
    end

    local remote = requestEndRun :: RemoteEvent
    remote.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 0 then return end
        if player:GetAttribute("ProfileState") ~= "Loaded" then return end
        local now = os.clock()
        local last = lastExitRequest[player] or -math.huge
        if now - last < Config.ExitRequestCooldownSeconds then return end
        lastExitRequest[player] = now
        local character = activeCharacter(player)
        if not character then return end
        if predatorNearby(player, character) then
            player:SetAttribute("LastExitStatus", "predator_nearby")
            player:SetAttribute("LastExitStatusAt", workspace:GetServerTimeNow())
            return
        end
        player:SetAttribute("LastExitStatus", "returning")
        player:SetAttribute("LastExitStatusAt", workspace:GetServerTimeNow())
        -- BD-052: the client already showed a Return/Cancel confirmation, so Home ends the
        -- run immediately (no stay-still channel). tryEnd is the same idempotent path as
        -- death and predation: the first caller flips Active -> Ending and settles once.
        RunLifecycle.tryEnd(player, character, "ManualExit")
    end)

    Players.PlayerRemoving:Connect(function(player)
        lastExitRequest[player] = nil
    end)
end

return RunLifecycle
