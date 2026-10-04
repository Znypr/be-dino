--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Resources = require(ReplicatedStorage.Shared.ResourceModels)
local FoodService = {}
local TYPES = {
    {id = "berry", weight = 82, points = 1, size = 0.5, color = Color3.fromRGB(224, 99, 118)},
    {id = "fruit", weight = 15, points = 4, size = 0.85, color = Color3.fromRGB(244, 186, 83)},
    {id = "amber", weight = 3, points = 12, size = 1.15, color = Color3.fromRGB(255, 219, 139)},
}
function FoodService.start(dinosaur)
    local folder = Instance.new("Folder")
    folder.Name = "Food"
    folder.Parent = workspace
    local foods = {}
    local random = Random.new(Config.FoodSeed)
    local groundParams = RaycastParams.new()
    groundParams.FilterType = Enum.RaycastFilterType.Include
    groundParams.FilterDescendantsInstances = {workspace.BeDinoArena}
    local extent = Config.ArenaHalfWidth - 8
    local sectorWidth = 2 * extent / Config.FoodSectorCount
    local function groundAt(x: number, z: number): Vector3?
        -- Safe spawn remains clear. Ground's top is y=0.
        if (Vector2.new(x, z) - Vector2.new(0, 30)).Magnitude < 11 then return nil end
        local hit = workspace:Raycast(Vector3.new(x, 40, z), Vector3.new(0, -50, 0), groundParams)
        if not hit or hit.Instance.Name ~= "Ground" then return nil end
        -- A second horizontal check keeps pickups away from solid rock/trunk edges.
        for _, direction in {Vector3.xAxis, -Vector3.xAxis, Vector3.zAxis, -Vector3.zAxis} do
            if workspace:Raycast(hit.Position + Vector3.new(0, 1, 0), direction * 1.25, groundParams) then
                return nil
            end
        end
        return hit.Position
    end
    local function relocate(food): boolean
        for _ = 1, 24 do
            local angle = random:NextNumber(0, 2 * math.pi)
            local radius = math.sqrt(random:NextNumber()) * Config.FoodClusterRadius
            local x = math.clamp(food.center.X + math.cos(angle) * radius, food.minX + 1, food.maxX - 1)
            local z = math.clamp(food.center.Y + math.sin(angle) * radius, food.minZ + 1, food.maxZ - 1)
            local ground = groundAt(x, z)
            if ground then
                food.part.Position = ground + Vector3.new(0, food.kind.size / 2 + 0.08, 0)
                if food.visual then food.visual:PivotTo(CFrame.new(ground)) end
                return true
            end
        end
        return false
    end
    local function show(food, visible: boolean)
        if food.visual then
            for _, item in food.visual:GetDescendants() do
                if item:IsA("BasePart") then item.Transparency = if visible then 0 else 1 end
            end
        else
            food.part.Transparency = if visible then 0 else 1
        end
    end
    for sx = 0, Config.FoodSectorCount - 1 do
        for sz = 0, Config.FoodSectorCount - 1 do
            local minX, minZ = -extent + sx * sectorWidth, -extent + sz * sectorWidth
            local center = Vector2.new(minX + sectorWidth / 2, minZ + sectorWidth / 2)
            -- Jitter cluster centers, including edge sectors; no one central food island.
            for _ = 1, 20 do
                local proposed = Vector2.new(random:NextNumber(minX + 3, minX + sectorWidth - 3), random:NextNumber(minZ + 3, minZ + sectorWidth - 3))
                if groundAt(proposed.X, proposed.Y) then center = proposed break end
            end
            for _ = 1, Config.FoodClusterItems do
                local roll, kind = random:NextInteger(1, 100), TYPES[1]
                if roll > 97 then kind = TYPES[3] elseif roll > 82 then kind = TYPES[2] end
                local pickup = Instance.new("Part")
                pickup.Name = kind.id
                pickup.Shape = Enum.PartType.Ball
                pickup.Size = Vector3.one * kind.size
                pickup.Color = kind.color
                pickup.Material = Enum.Material.SmoothPlastic
                pickup.Anchored = true
                pickup.CanCollide = false
                pickup.CanTouch = false
                pickup.CanQuery = false
                pickup:SetAttribute("Points", kind.points)
                pickup:SetAttribute("Sector", string.format("%d:%d", sx, sz))
                local visual = Resources.clone(kind.id)
                local food = {part = pickup, visual = visual, readyAt = 0, hidden = false, kind = kind,
                    center = center, minX = minX, maxX = minX + sectorWidth, minZ = minZ, maxZ = minZ + sectorWidth}
                if relocate(food) then
                    pickup.Parent = folder
                    if visual then
                        pickup.Transparency = 1
                        for _, item in visual:GetDescendants() do
                            if item:IsA("BasePart") then item.Anchored = true end
                        end
                        visual.Parent = folder
                    end
                    table.insert(foods, food)
                else
                    pickup:Destroy()
                    if visual then visual:Destroy() end
                end
            end
        end
    end
    workspace:SetAttribute("FoodCount", #foods)
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
                if character and root and root:IsA("BasePart") and humanoid and humanoid.Health > 0
                    and character:GetAttribute("DinoAttached") and character:GetAttribute("RunState") == "Active" then
                    local last, position = previous[player], root.Position
                    local plausible = last and last.character == character
                        and (position - last.position).Magnitude <= Config.WalkSpeed * (now - last.time) * 2 + 2
                    previous[player] = {character = character, position = position, time = now}
                    if plausible then table.insert(candidates, {player = player, character = character, root = root, gained = 0}) end
                else previous[player] = nil end
            end
            for _, food in foods do
                if now < food.readyAt then continue end
                if food.hidden then
                    relocate(food) -- original valid location remains if no replacement succeeds
                    show(food, true)
                    food.hidden = false
                end
                local winner, nearest = nil, math.huge
                for _, candidate in candidates do
                    local delta = food.part.Position - candidate.root.Position
                    local horizontal = Vector3.new(delta.X, 0, delta.Z).Magnitude
                    local scale = candidate.character:GetAttribute("VisualScale") or 1
                    local radius = math.min(5, Config.FoodPickupRadius + (scale - 1) * 0.75)
                    if horizontal <= radius and math.abs(delta.Y) < 6 then
                        local blocked = workspace:Raycast(candidate.root.Position, delta, groundParams)
                        if not blocked and (horizontal < nearest or (horizontal == nearest and winner and candidate.player.UserId < winner.player.UserId)) then
                            nearest, winner = horizontal, candidate
                        end
                    end
                end
                if winner then
                    food.readyAt = now + Config.FoodRespawnSeconds
                    food.hidden = true
                    show(food, false)
                    winner.gained += food.kind.points
                end
            end
            for _, candidate in candidates do
                if candidate.gained > 0 then dinosaur.addGrowth(candidate.character, candidate.gained) end
            end
        end
    end)
end
return FoodService
