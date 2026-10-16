--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local MovementEnvelope = require(ReplicatedStorage.Shared.MovementEnvelope)
local FoodCatchRules = require(ReplicatedStorage.Shared.FoodCatchRules)
local RunEggTags = require(ReplicatedStorage.Shared.RunEggTags)

local CooldownMemory = require(script.Parent.CooldownMemory)

local PredationService = {}

local function numberAttribute(instance: Instance, name: string, fallback: number): number
    local value = instance:GetAttribute(name)
    return if typeof(value) == "number" then value else fallback
end

local function canEat(attackerScore: number, targetScore: number): boolean
    return attackerScore > targetScore and attackerScore >= targetScore * Config.PredationScoreMultiplier
end

function PredationService.start(runLifecycle, dinosaur)
    -- BD-244: with HP combat on, the instant "bigger eats smaller" rule is replaced by CombatService bites. Flag off = unchanged.
    if Config.CombatEnabled then return end
    local previous = {}
    local victimMemory = CooldownMemory.new(math.max(120, Config.RepeatVictimCatchCooldownSeconds * 2)) -- BD-363: UserId keys, survives a rejoin
    local arenaParams = RaycastParams.new()
    arenaParams.FilterType = Enum.RaycastFilterType.Include
    arenaParams.FilterDescendantsInstances = {workspace.BeDinoArena, workspace.Terrain}

    Players.PlayerRemoving:Connect(function(player)
        previous[player] = nil
    end)

    local function awardCatch(attacker, victimUserId: number, now: number)
        if not victimMemory.allow(attacker.player.UserId, "victim" .. victimUserId, now, Config.RepeatVictimCatchCooldownSeconds) then
            return
        end
        -- BD-439 (owner 2026-10-16): a player kill is a SMALL capped egg bonus (0.25 egg, max 3 per run), not +1. Growth is separate.
        local whole, carry, total = FoodCatchRules.awardKill(numberAttribute(attacker.character, "PredationEggs", 0), numberAttribute(attacker.character, "PredationEggCarry", 0))
        attacker.character:SetAttribute("PredationEggCarry", carry)
        attacker.character:SetAttribute("PredationEggs", total)
        if whole > 0 then
            local catches = numberAttribute(attacker.character, "CatchScore", 0)
            attacker.character:SetAttribute("CatchScore", RunEggTags.nextScore(catches, whole, Config.MaxCatchScore, Config.RunEggMaxPerRun))
            runLifecycle.noteNestWeather(attacker.character) -- BD-479: a nest newly earned by this kill egg is stamped with the weather now
        end
    end

    task.spawn(function()
        while true do
            task.wait(Config.PredationTickSeconds)
            local movementNow = os.clock()
            local serverNow = workspace:GetServerTimeNow()
            local candidates = {}

            for _, player in Players:GetPlayers() do
                local character = player.Character
                local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
                local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
                if character and root and root:IsA("BasePart") and humanoid and humanoid.Health > 0
                    and character:GetAttribute("DinoAttached") and runLifecycle.isActive(character) then
                    local last = previous[player]
                    local position = root.Position
                    local plausible = last and last.character == character
                        and MovementEnvelope.plausible(position - last.position, movementNow - last.time, 2, 2, root.AssemblyLinearVelocity.Y, character:GetAttribute("MovementSpeedLimit") or humanoid.WalkSpeed)
                    previous[player] = {character = character, position = position, time = movementNow}
                    if plausible then
                        table.insert(candidates, {
                            player = player,
                            character = character,
                            root = root,
                            score = numberAttribute(character, "GrowthScore", 0),
                            scale = numberAttribute(character, "VisualScale", 1),
                        })
                    end
                else
                    previous[player] = nil
                end
            end

            table.sort(candidates, function(a, b)
                return a.player.UserId < b.player.UserId
            end)

            for _, victim in candidates do
                if not runLifecycle.isActive(victim.character) or runLifecycle.isProtected(victim.character, serverNow) then
                    continue
                end

                local winner = nil
                local nearest = math.huge
                for _, attacker in candidates do
                    if attacker.player == victim.player or not runLifecycle.isActive(attacker.character)
                        or runLifecycle.isProtected(attacker.character, serverNow) then
                        continue
                    end
                    if not canEat(attacker.score, victim.score) then continue end

                    local delta = victim.root.Position - attacker.root.Position
                    local horizontal = Vector3.new(delta.X, 0, delta.Z).Magnitude
                    local radius = math.min(Config.PredationMaxRadius,
                        Config.PredationBaseRadius + math.max(0, attacker.scale - 1) * 1.25)
                    if horizontal > radius or math.abs(delta.Y) > Config.PredationVerticalLimit then continue end

                    local blocked = workspace:Raycast(attacker.root.Position, delta, arenaParams)
                    if blocked then continue end

                    if horizontal < nearest or (horizontal == nearest and winner and attacker.player.UserId < winner.player.UserId) then
                        nearest = horizontal
                        winner = attacker
                    end
                end

                if winner and runLifecycle.tryEnd(victim.player, victim.character, "Eaten", winner.player.UserId) then
                    winner.character:SetAttribute("BiteSeq", numberAttribute(winner.character, "BiteSeq", 0) + 1) -- BD-079 replicated cue for the client bite lunge
                    awardCatch(winner, victim.player.UserId, serverNow)
                    dinosaur.addGrowth(winner.character, Config.PredationGrowthPoints)
                end
            end
        end
    end)
end

return PredationService
