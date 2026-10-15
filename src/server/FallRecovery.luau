--!strict
-- BD-210 safety net: a character whose root drops below the floor under it (SpawnGeometry.fallen) is put back at a safe
-- point: the island spawn during a run, the hub otherwise. Server-side, so it also covers clients whose local terrain
-- collision is late or missing. MovementGuard skips fallen characters so it never "corrects" them to mid-air baselines.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)
local FallRecovery = {}
local started = false

-- Server teleport of a client-owned character without the ownership race: the server takes physics ownership, moves
-- the still assembly, and hands it back a moment later. (A plain server PivotTo let the client keep simulating from its
-- stale state: Studio showed the root 50 studs off target for a frame right after the run-start teleport.)
function FallRecovery.teleport(player: Player, character: Model, target: CFrame)
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root or not root:IsA("BasePart") then character:PivotTo(target) return end
    local owned = pcall(function() root:SetNetworkOwner(nil) end)
    root.AssemblyLinearVelocity = Vector3.zero
    root.AssemblyAngularVelocity = Vector3.zero
    character:PivotTo(target)
    if owned then
        task.delay(.25, function()
            if root.Parent and player.Parent and player.Character == character then
                pcall(function() root:SetNetworkOwner(player) end)
            end
        end)
    end
end

function FallRecovery.check(player: Player): boolean
    local character = player.Character
    local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
    local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
    if not character or not root or not root:IsA("BasePart") or not humanoid or humanoid.Health <= 0 then return false end
    if not SpawnGeometry.fallen(Config, Layout, root.Position) then return false end
    local active = character:GetAttribute("RunState") == "Active"
    local target = SpawnGeometry.recoveryPoint(Config, Layout, active)
    local fellAt = root.Position
    FallRecovery.teleport(player, character, CFrame.new(target))
    local count = player:GetAttribute("FallRecoveries")
    player:SetAttribute("FallRecoveries", (if typeof(count) == "number" then count else 0) + 1)
    warn(string.format("[Be Dino] %s fell out of the world at %s; returned to %s", player.Name, tostring(fellAt), if active then "island spawn" else "hub"))
    return true
end

function FallRecovery.start(onRecovered: ((Player) -> ())?)
    if started then return end
    started = true
    task.spawn(function()
        while true do
            task.wait(Config.FallRecoveryTickSeconds)
            for _, player in Players:GetPlayers() do
                if FallRecovery.check(player) and onRecovered then onRecovered(player) end
            end
        end
    end)
end
return FallRecovery
