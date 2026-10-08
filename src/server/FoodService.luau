--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local MovementEnvelope = require(ReplicatedStorage.Shared.MovementEnvelope)
local Resources = require(ReplicatedStorage.Shared.ResourceModels)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local FoodCatchRules = require(ReplicatedStorage.Shared.FoodCatchRules)
local ProgressionRules = require(ReplicatedStorage.Shared.ProgressionRules)
local RewardMath = require(script.Parent.RewardMath)
local Http = game:GetService("HttpService")
local eventRandom = Random.new()
local FoodService = {}
local TYPES = {
    {id = "berry", weight = 78, points = 1, size = 0.7, color = Color3.fromRGB(224, 99, 118)},
    {id = "fruit", weight = 15, points = 4, size = 1.0, color = Color3.fromRGB(244, 186, 83)},
    {id = "egg", weight = 5, points = 15, size = 1.3, color = Color3.fromRGB(245, 230, 187)},
    {id = "amber", weight = 2, points = 50, size = 1.5, color = Color3.fromRGB(255, 219, 139)},
}
function FoodService.start(dinosaur,repository)
    workspace:SetAttribute("FoodSpawnStatus", "Building")
    workspace:SetAttribute("FoodCount", 0)
    workspace:SetAttribute("FoodStartupError", "")
    local folder = Instance.new("Folder")
    folder.Name = "Food"
    folder.Parent = workspace
    local foods = {}
    local random = Random.new(Config.FoodSeed)
    local groundParams = RaycastParams.new()
    groundParams.FilterType = Enum.RaycastFilterType.Include
    groundParams.FilterDescendantsInstances = {workspace.Terrain}
    local pickupParams = RaycastParams.new()
    pickupParams.FilterType = Enum.RaycastFilterType.Include
    pickupParams.FilterDescendantsInstances = {workspace.BeDinoArena, workspace.Terrain}
    local fallbackCount = 0
    local obstacleParams = RaycastParams.new()
    obstacleParams.FilterType = Enum.RaycastFilterType.Include
    obstacleParams.FilterDescendantsInstances = {workspace.BeDinoArena}
    local extent = Config.ArenaHalfWidth - 8
    local sectorWidth = 2 * extent / Config.FoodSectorCount
    local function groundAt(x: number, z: number): Vector3?
        -- Safe spawn remains clear. Ground's top is y=0.
        if (Vector2.new(x, z) - Vector2.new(0, 30)).Magnitude < 11 then return nil end
        local hit = workspace:Raycast(Vector3.new(x, Config.TerrainTop + 20, z), Vector3.new(0, -Config.TerrainTop - 60, 0), groundParams)
        local ground: Vector3
        if hit then
            if hit.Material == Enum.Material.Water or hit.Normal.Y < 0.62 then return nil end
            ground = hit.Position
        else
            -- Same authored heightfield that produced the terrain; never silently empty the map.
            fallbackCount += 1
            ground = Vector3.new(x, Layout.height(x,z) + Config.TerrainResolution*.5, z)
        end
        -- A second horizontal check keeps pickups away from solid rock/trunk edges.
        for _, direction in {Vector3.xAxis, -Vector3.xAxis, Vector3.zAxis, -Vector3.zAxis} do
            if workspace:Raycast(ground + Vector3.new(0, 1, 0), direction * 1.25, obstacleParams) then
                return nil
            end
        end
        return ground
    end
    local function relocate(food): boolean
        for _ = 1, 24 do
            local angle = random:NextNumber(0, 2 * math.pi)
            local radius = math.sqrt(random:NextNumber()) * Config.FoodClusterRadius
            local x = math.clamp(food.center.X + math.cos(angle) * radius, food.minX + 1, food.maxX - 1)
            local z = math.clamp(food.center.Y + math.sin(angle) * radius, food.minZ + 1, food.maxZ - 1)
            local ground = groundAt(x, z)
            if ground then
                food.part.Position = ground + Vector3.new(0, food.kind.size / 2 + 0.35, 0)
                if food.visual then food.visual:PivotTo(CFrame.new(ground + Vector3.new(0,.35,0))) end
                return true
            end
        end
        return false
    end
    local function show(food, visible: boolean)
        local hint = food.part:FindFirstChild("FoodHint")
        if hint and hint:IsA("BillboardGui") then hint.Enabled = visible end
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
            local starter = (sx == 7 or sx == 8) and sz == 8
            if starter then center = Vector2.new(if sx == 7 then -15 else 15, 24) end
            for itemIndex = 1, Config.FoodClusterItems do
                local roll, kind = random:NextInteger(1, 100), TYPES[1]
                if roll > 98 then kind = TYPES[4] elseif roll > 93 then kind = TYPES[3] elseif roll > 78 then kind = TYPES[2] end
                if starter then kind = if itemIndex % 3 == 0 then TYPES[2] else TYPES[1] end
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
                pickup:SetAttribute("StarterFood", starter)
                pickup:SetAttribute("Sector", string.format("%d:%d", sx, sz))
                local visual = nil
                if kind.id == "egg" or kind.id == "amber" then
                    local ok, result = pcall(function()
                        local model = Resources.clone(kind.id)
                        if model then model:ScaleTo(kind.size / (if kind.id == "egg" then 2.4 else 1.3)) end
                        return model
                    end)
                    if ok then visual = result end -- visible native pickup survives any art failure
                end
                local food = {part = pickup, visual = visual, readyAt = 0, hidden = false, kind = kind,
                    center = center, minX = minX, maxX = minX + sectorWidth, minZ = minZ, maxZ = minZ + sectorWidth}
                if relocate(food) then
                    pickup.Parent = folder
                    if visual then
                        pickup.Transparency = 1
                        for _, item in visual:GetDescendants() do
                            if item:IsA("BasePart") then item.Anchored = true end
                        end
                        visual.Parent = pickup
                    end
                    table.insert(foods, food)
                    workspace:SetAttribute("FoodCount", #foods)
                    if starter then
                        local hint = Instance.new("BillboardGui")
                        hint.Name, hint.Size, hint.StudsOffset = "FoodHint", UDim2.fromOffset(74,24), Vector3.new(0,1.2,0)
                        hint.MaxDistance, hint.AlwaysOnTop, hint.Parent = 45,false,pickup
                        local label = Instance.new("TextLabel")
                        label.Size,label.BackgroundTransparency,label.Text = UDim2.fromScale(1,1),1,"+"..kind.points
                        label.Font,label.TextSize,label.TextColor3 = Enum.Font.FredokaOne,16,kind.color
                        label.TextStrokeTransparency,label.TextStrokeColor3,label.Parent = 0,Color3.new(0,0,0),hint
                    end
                else
                    pickup:Destroy()
                    if visual then visual:Destroy() end
                end
            end
        end
        task.wait() -- avoid one long startup frame while instancing pickup art
    end
    workspace:SetAttribute("FoodPlacementFallbacks", fallbackCount)
    workspace:SetAttribute("FoodCount", #foods)
    workspace:SetAttribute("FoodSpawnStatus", if #foods > 0 then "Ready" else "No valid ground")
    if #foods == 0 then warn("[Be Dino] Food placement failed: no valid terrain hits") end
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
                        and MovementEnvelope.plausible(position - last.position, now - last.time, 2, 2, root.AssemblyLinearVelocity.Y, character:GetAttribute("MovementSpeedLimit") or humanoid.WalkSpeed)
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
                        local blocked = workspace:Raycast(candidate.root.Position, delta, pickupParams)
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
                if candidate.gained > 0 then
                    local c = candidate.character
                    local whole, carry = FoodCatchRules.award(candidate.gained, c:GetAttribute("FoodCatchCarry") or 0, c:GetAttribute("WeatherLootMultiplier") or 1)
                    c:SetAttribute("FoodCatchCarry", carry)
                    local before=c:GetAttribute("CatchScore") or 0
                    local after=math.min(Config.MaxCatchScore,before+whole)
                    c:SetAttribute("CatchScore",after)
                    local ok,events=pcall(function() return Http:JSONDecode(c:GetAttribute("RunEggEvents") or "[]") end)
                    if not ok or typeof(events)~="table" then events={} end
                    for i=1,RewardMath.earnedChests(after) do
                        if not events[i] then
                            events[i]=ProgressionRules.eventEgg(if i>RewardMath.earnedChests(before) then workspace:GetAttribute("WeatherId") or "clear" else "clear",eventRandom:NextNumber())
                            if repository then events[i]=repository.prepareEgg(candidate.player,events[i]) end
                        end
                    end
                    c:SetAttribute("RunEggEvents",Http:JSONEncode(events))
                    dinosaur.addGrowth(c, candidate.gained)
                end
            end
        end
    end)
end
return FoodService
