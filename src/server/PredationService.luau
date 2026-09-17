--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)

local PredationService = {}

local function numberAttribute(instance: Instance, name: string, fallback: number): number
    local value = instance:GetAttribute(name)
    return if typeof(value) == "number" then value else fallback
end

local function canEat(attackerScore: number, targetScore: number): boolean
    return attackerScore > targetScore and attackerScore >= targetScore * Config.PredationScoreMultiplier
end

function PredationService.start(runLifecycle, dinosaur)
    local previous = {}
    local recentPairs: {[number]: {[number]: number}} = {}
    local arenaParams = RaycastParams.new()
    arenaParams.FilterType = Enum.RaycastFilterType.Include
    arenaParams.FilterDescendantsInstances = {workspace.BeDinoArena}

    Players.PlayerRemoving:Connect(function(player)
        previous[player] = nil
        recentPairs[player.UserId] = nil
        for _, victims in recentPairs do
            victims[player.UserId] = nil
        end
    end)

    local function awardCatch(attacker, victimUserId: number, now: number)
        local victims = recentPairs[attacker.player.UserId]
        if not victims then
            victims = {}
            recentPairs[attacker.player.UserId] = victims
        end
        local last = victims[victimUserId] or -math.huge
        if now - last < Config.RepeatVictimCatchCooldownSeconds then
            return
        end
        victims[victimUserId] = now
        local catches = numberAttribute(attacker.character, "CatchScore", 0)
        if catches < Config.MaxCatchScore then
            attacker.character:SetAttribute("CatchScore", catches + 1)
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
                        and (position - last.position).Magnitude <= Config.WalkSpeed * (movementNow - last.time) * 2 + 2
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
                    awardCatch(winner, victim.player.UserId, serverNow)
                    dinosaur.addGrowth(winner.character, Config.PredationGrowthPoints)
                end
            end
        end
    end)
end

return PredationService
