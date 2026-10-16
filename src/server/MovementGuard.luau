--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local MovementEnvelope = require(ReplicatedStorage.Shared.MovementEnvelope)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)

local CooldownMemory = require(script.Parent.CooldownMemory)

local MovementGuard = {}
local rejects = CooldownMemory.new(math.max(120, Config.MovementGuardRejectCooldownSeconds * 4)) -- BD-363: reject clock by UserId, a rejoin does not wipe it
local states: {[Player]: {
    character: Model,
    cframe: CFrame,
    position: Vector3,
    sampleAt: number,
    blockedUntil: number,
}} = {}
local started = false

local function clear(player: Player)
    states[player] = nil
end

-- BD-210: forget the trusted baseline (after a server teleport such as fall recovery or run start).
function MovementGuard.reset(player: Player)
    clear(player)
end

function MovementGuard.start()
    if started then return end
    started = true
    Players.PlayerRemoving:Connect(clear)

    task.spawn(function()
        while true do
            task.wait(Config.MovementGuardTickSeconds)
            local now = os.clock()

            for _, player in Players:GetPlayers() do
                local character = player.Character
                local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
                local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil

                if not character or not root or not root:IsA("BasePart") or not humanoid
                    or humanoid.Health <= 0 or character:GetAttribute("RunState") ~= "Active" then
                    clear(player)
                    continue
                end
                -- BD-210: a root below the floor is FallRecovery's job. Correcting it here snapped falling characters
                -- back to mid-fall baselines under the map (an endless fall loop instead of a recovery).
                if SpawnGeometry.fallen(Config, Layout, root.Position) then
                    clear(player)
                    continue
                end

                local state = states[player]
                if not state or state.character ~= character then
                    states[player] = {
                        character = character,
                        cframe = root.CFrame,
                        position = root.Position,
                        sampleAt = now,
                        blockedUntil = now + Config.MovementGuardTickSeconds,
                    }
                    player:SetAttribute("MovementSecurityStatus", "WARMUP")
                    local rejectedAt = rejects.last(player.UserId, "reject")
                    if now - rejectedAt < Config.MovementGuardRejectCooldownSeconds then -- rejoined right after a rejection
                        states[player].blockedUntil = rejectedAt + Config.MovementGuardRejectCooldownSeconds
                    end
                    continue
                end

                local dt = math.max(now - state.sampleAt, Config.MovementGuardTickSeconds * 0.5)
                -- Same envelope as the Humanoid: walk speed (incl. potions/trails/leap limit),
                -- slope climb rate up to MaxSlopeAngle, jumps and falls (BD-053).
                if not MovementEnvelope.plausible(root.Position - state.position, dt, Config.MovementGuardSpeedTolerance, Config.MovementGuardBurstStuds, root.AssemblyLinearVelocity.Y, character:GetAttribute("MovementSpeedLimit") or humanoid.WalkSpeed) then
                    -- Server correction: never promote the impossible location to the trusted baseline.
                    root.CFrame = state.cframe
                    root.AssemblyLinearVelocity = Vector3.zero
                    root.AssemblyAngularVelocity = Vector3.zero
                    state.sampleAt = now
                    state.blockedUntil = now + Config.MovementGuardRejectCooldownSeconds
                    rejects.mark(player.UserId, "reject", now)
                    local rejects = player:GetAttribute("MovementRejectCount")
                    player:SetAttribute(
                        "MovementRejectCount",
                        (if typeof(rejects) == "number" then rejects else 0) + 1
                    )
                    player:SetAttribute("MovementSecurityStatus", "REJECTED")
                    continue
                end

                state.cframe = root.CFrame
                state.position = root.Position
                state.sampleAt = now
                if now >= state.blockedUntil then
                    player:SetAttribute("MovementSecurityStatus", "OK")
                end
            end
        end
    end)
end

return MovementGuard
