--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local MovementGuard = {}
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
                    continue
                end

                local dt = math.max(now - state.sampleAt, Config.MovementGuardTickSeconds * 0.5)
                local distance = (root.Position - state.position).Magnitude
                local allowed = Config.WalkSpeed * dt * Config.MovementGuardSpeedTolerance
                    + Config.MovementGuardBurstStuds

                if distance > allowed then
                    -- Server correction: never promote the impossible location to the trusted baseline.
                    root.CFrame = state.cframe
                    root.AssemblyLinearVelocity = Vector3.zero
                    root.AssemblyAngularVelocity = Vector3.zero
                    state.sampleAt = now
                    state.blockedUntil = now + Config.MovementGuardRejectCooldownSeconds
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
