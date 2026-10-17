--!strict
-- BD-210 safety net: a character whose root drops below the floor under it (SpawnGeometry.fallen) is put back at a safe
-- point: the island spawn during a run, the hub otherwise. Server-side, so it also covers clients whose local terrain
-- collision is late or missing. MovementGuard skips fallen characters so it never "corrects" them to mid-air baselines.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)
local StreamingTeleport = require(script.Parent.StreamingTeleport)
local FallRecovery = {}
local started = false
local checking: {[Player]: boolean} = {} -- BD-503: a recovery whose stream request is still running (one at a time per player)

-- Server teleport of a client-owned character without the ownership race: the server takes physics ownership, moves
-- the still assembly, and hands it back a moment later. (A plain server PivotTo let the client keep simulating from its
-- stale state: Studio showed the root 50 studs off target for a frame right after the run-start teleport.)
-- BD-503: the ONE server teleport of a dino. With StreamingEnabled it first asks the client to stream the target area in (StreamingTeleport.request,
-- a short pcall'd wait, only for a far target), then re-checks the player and character. `streamed` = the caller already did that (RunLifecycle.requestStart).
-- Returns false when the teleport was dropped because the player or the character went away during the wait.
function FallRecovery.teleport(player: Player, character: Model, target: CFrame, streamed: boolean?): boolean
    if streamed ~= true and StreamingTeleport.needed(character, target.Position) then
        StreamingTeleport.request(player, target.Position)
        if player.Parent == nil or player.Character ~= character or character.Parent == nil then return false end
    end
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root or not root:IsA("BasePart") then character:PivotTo(target) return true end
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
    return true
end

function FallRecovery.check(player: Player): boolean
    if checking[player] then return false end
    local character = player.Character
    local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
    local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
    if not character or not root or not root:IsA("BasePart") or not humanoid or humanoid.Health <= 0 then return false end
    if not SpawnGeometry.fallen(Config, Layout, root.Position) then return false end
    local active = character:GetAttribute("RunState") == "Active"
    local target = SpawnGeometry.recoveryPoint(Config, Layout, active)
    local fellAt = root.Position
    checking[player] = true
    local ran, moved = pcall(FallRecovery.teleport, player, character, CFrame.new(target))
    checking[player] = nil
    if not ran then warn("[Be Dino] fall recovery teleport failed: " .. tostring(moved)) return false end
    if not moved then return false end
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
                if workspace.StreamingEnabled then -- BD-503: check() may wait for a stream request; never hold up the other players
                    task.spawn(function() if FallRecovery.check(player) and onRecovered then onRecovered(player) end end)
                elseif FallRecovery.check(player) and onRecovered then
                    onRecovered(player)
                end
            end
        end
    end)
end
return FallRecovery
