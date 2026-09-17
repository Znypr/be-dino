--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local FoodService = {}

function FoodService.start(dinosaur)
    local folder = Instance.new("Folder")
    folder.Name = "Food"
    folder.Parent = workspace
    local foods = {}
    local groundParams = RaycastParams.new()
    groundParams.FilterType = Enum.RaycastFilterType.Include
    groundParams.FilterDescendantsInstances = {workspace.BeDinoArena}
    -- Fixed, bounded grid. Skip obstacles, spawn and slope instead of hiding food inside them.
    for x = -70, 70, 20 do
        for z = -70, 70, 20 do
            local hit = workspace:Raycast(Vector3.new(x, 30, z), Vector3.new(0, -40, 0), groundParams)
            if hit and hit.Instance.Name == "Ground" then
                local berry = Instance.new("Part")
                berry.Name = "Berry"
                berry.Shape = Enum.PartType.Ball
                berry.Size = Vector3.new(1.5, 1.5, 1.5)
                berry.Position = hit.Position + Vector3.new(0, 0.9, 0)
                berry.Color = Color3.fromRGB(255, 156, 65)
                berry.Material = Enum.Material.Neon
                berry.Anchored = true
                berry.CanCollide = false
                berry.CanTouch = false
                berry.CanQuery = false
                berry.Parent = folder
                table.insert(foods, {part = berry, readyAt = 0})
            end
        end
    end
    local previous = {}
    Players.PlayerRemoving:Connect(function(player) previous[player] = nil end)
    task.spawn(function()
        while true do
            task.wait(Config.FoodTickSeconds)
            local now = os.clock()
            local candidates = {}
            for _, player in Players:GetPlayers() do
                local character = player.Character
                local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
                local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
                if character and root and root:IsA("BasePart") and humanoid and humanoid.Health > 0 and character:GetAttribute("DinoAttached") then
                    local last = previous[player]
                    local position = root.Position
                    -- Basic teleport rejection, not a complete movement/anti-cheat system.
                    local plausible = last and last.character == character
                        and (position - last.position).Magnitude <= Config.WalkSpeed * (now - last.time) * 2 + 2
                    previous[player] = {character = character, position = position, time = now}
                    if plausible then
                        table.insert(candidates, {player = player, character = character, root = root, gained = 0})
                    end
                else
                    previous[player] = nil
                end
            end
            for _, food in foods do
                if now < food.readyAt then continue end
                food.part.Transparency = 0
                local winner = nil
                local nearest = math.huge
                for _, candidate in candidates do
                    local delta = food.part.Position - candidate.root.Position
                    local horizontal = Vector3.new(delta.X, 0, delta.Z).Magnitude
                    if horizontal <= Config.FoodPickupRadius and math.abs(delta.Y) < 6 then
                        -- Arena-only occlusion prevents eating through solid geometry.
                        local blocked = workspace:Raycast(candidate.root.Position, delta, groundParams)
                        if not blocked and (horizontal < nearest or (horizontal == nearest and winner and candidate.player.UserId < winner.player.UserId)) then
                            nearest = horizontal
                            winner = candidate
                        end
                    end
                end
                if winner then
                    -- No yield between claiming and awarding: one winner per berry.
                    food.readyAt = now + Config.FoodRespawnSeconds
                    food.part.Transparency = 1
                    winner.gained += Config.FoodPoints
                end
            end
            for _, candidate in candidates do
                if candidate.gained > 0 then
                    local score = (candidate.character:GetAttribute("GrowthScore") or 0) + candidate.gained
                    candidate.character:SetAttribute("GrowthScore", score)
                    local scale = math.min(4, math.sqrt(1 + score / 50))
                    if candidate.character:GetAttribute("VisualScale") ~= scale then
                        dinosaur.render(candidate.character, scale)
                    end
                end
            end
        end
    end)
end

return FoodService
