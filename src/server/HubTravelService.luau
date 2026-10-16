--!strict
-- BD-287 (docs/104 s7): server side of "teleport to a Cave hub station". The `HubTravel` RemoteFunction exists ONLY while
-- Config.CaveHub is true (it ships false: start() then does nothing, so nothing changes). Rules live in the pure
-- HubTravelRules; the character moves only through FallRecovery.teleport. The ack {ok, station | reason} is returned to the
-- client; the player's HubStation attribute is set on arrival (cleared by the later hub tick, BD-288/289).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Rules = require(ReplicatedStorage.Shared.HubTravelRules)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)
local FallRecovery = require(script.Parent.FallRecovery)
local HubTravelService = {}
local sessions: {[Player]: {lastAt: number?}} = {}

local function gather(player: Player, character: Model?): any
    local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
    local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
    local inHub = false
    if root and root:IsA("BasePart") then
        local p = root.Position
        inHub = p.X == p.X and p.Z == p.Z and SpawnGeometry.inHub(Config, p.X, p.Z)
    end
    local occupied = {}
    for _, other in Players:GetPlayers() do
        local c = other.Character
        local r = if other ~= player and c then c:FindFirstChild("HumanoidRootPart") else nil
        if r and r:IsA("BasePart") then occupied[#occupied + 1] = {x = r.Position.X, z = r.Position.Z} end
    end
    return {
        caveHub = Config.CaveHub == true,
        profileState = player:GetAttribute("ProfileState"),
        runState = if character then character:GetAttribute("RunState") else nil,
        dinoAttached = character ~= nil and character:GetAttribute("DinoAttached") == true,
        alive = humanoid ~= nil and humanoid.Health > 0,
        inHub = inHub,
        now = os.clock(),
        occupied = occupied,
    }
end

-- Entry point for OnServerInvoke and tests. Never throws to the client.
function HubTravelService.handle(player: Player, ...: any): any
    local session = sessions[player]
    if not session then
        session = {lastAt = nil}
        sessions[player] = session
    end
    if select("#", ...) ~= 1 then return {ok = false, reason = "bad_request"} end
    local request = ...
    local ran, ack = pcall(function()
        local character = player.Character
        local result, target = Rules.process(session, request, gather(player, character))
        if target and character and player.Character == character then
            FallRecovery.teleport(player, character, CFrame.new(target.x, target.y, target.z) * CFrame.Angles(0, target.yaw, 0))
            player:SetAttribute("HubStation", result.station)
            print(string.format("[Be Dino] hub travel %s -> %s (spot %d)", player.Name, tostring(result.station), target.index))
        end
        return result
    end)
    if not ran then return {ok = false, reason = "error"} end
    return ack
end

function HubTravelService.start()
    if Config.CaveHub ~= true then return end -- flag off: no remote, nothing observable changes
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteFunction")
    remote.Name = "HubTravel"
    remote.Parent = folder
    remote.OnServerInvoke = HubTravelService.handle
    Players.PlayerRemoving:Connect(function(player) sessions[player] = nil end)
end
return HubTravelService
