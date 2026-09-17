--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Config = require(ReplicatedStorage.Shared.Config)

local RunLifecycle = {}
local lastExitRequest: {[Player]: number} = {}
local requestEndRun: RemoteEvent? = nil

local function activeCharacter(player: Player): Model?
    local character = player.Character
    if not character or character:GetAttribute("RunState") ~= "Active" then return nil end
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not humanoid or humanoid.Health <= 0 then return nil end
    return character
end

function RunLifecycle.begin(player: Player, character: Model)
    if character:GetAttribute("RunId") ~= nil then return end
    character:SetAttribute("RunId", HttpService:GenerateGUID(false))
    character:SetAttribute("RunState", "Active")
    character:SetAttribute("GrowthScore", 0)
    character:SetAttribute("CatchScore", 0)
    character:SetAttribute("SpawnProtectionEndsAt", workspace:GetServerTimeNow() + Config.SpawnProtectionSeconds)
    character:SetAttribute("ExitChannelEndsAt", 0)

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

function RunLifecycle.tryEnd(player: Player, character: Model, reason: string, sourceUserId: number?): boolean
    if player.Character ~= character or character:GetAttribute("RunState") ~= "Active" then
        return false
    end

    -- The state flip happens before any yield/death signal, so competing terminal paths lose deterministically.
    character:SetAttribute("RunState", "Ending")
    character:SetAttribute("ExitChannelEndsAt", 0)
    player:SetAttribute("LastRunEndReason", reason)
    player:SetAttribute("LastRunId", character:GetAttribute("RunId"))
    player:SetAttribute("LastRunEndAt", workspace:GetServerTimeNow())
    player:SetAttribute("LastPredatorUserId", sourceUserId or 0)

    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if humanoid and humanoid.Health > 0 then
        humanoid.Health = 0
    end
    return true
end

local function cancelExit(character: Model)
    if character:GetAttribute("RunState") == "Active" then
        character:SetAttribute("ExitChannelEndsAt", 0)
    end
end

local function startExitChannel(player: Player, character: Model)
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root or not root:IsA("BasePart") then return end
    local currentEnd = character:GetAttribute("ExitChannelEndsAt")
    if typeof(currentEnd) == "number" and currentEnd > workspace:GetServerTimeNow() then return end

    local origin = root.Position
    character:SetAttribute("ExitChannelEndsAt", workspace:GetServerTimeNow() + Config.ExitChannelSeconds)
    task.spawn(function()
        local deadline = os.clock() + Config.ExitChannelSeconds
        while os.clock() < deadline do
            task.wait(0.1)
            if player.Character ~= character or character:GetAttribute("RunState") ~= "Active" then
                return
            end
            local currentRoot = character:FindFirstChild("HumanoidRootPart")
            if not currentRoot or not currentRoot:IsA("BasePart") then
                cancelExit(character)
                return
            end
            if (currentRoot.Position - origin).Magnitude > Config.ExitMoveCancelDistance then
                cancelExit(character)
                return
            end
        end
        RunLifecycle.tryEnd(player, character, "ManualExit")
    end)
end

function RunLifecycle.start()
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

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
        -- This remote has no payload. Reject unexpected arguments rather than expanding the trust boundary.
        if select("#", ...) ~= 0 then return end
        local now = os.clock()
        local last = lastExitRequest[player] or -math.huge
        if now - last < Config.ExitRequestCooldownSeconds then return end
        lastExitRequest[player] = now
        local character = activeCharacter(player)
        if not character then return end
        startExitChannel(player, character)
    end)

    Players.PlayerRemoving:Connect(function(player)
        lastExitRequest[player] = nil
    end)
end

return RunLifecycle
