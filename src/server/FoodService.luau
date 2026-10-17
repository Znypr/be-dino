--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local MovementEnvelope = require(ReplicatedStorage.Shared.MovementEnvelope)
local Resources = require(ReplicatedStorage.Shared.ResourceModels)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local FoodCatchRules = require(ReplicatedStorage.Shared.FoodCatchRules)
local PointGrid = require(ReplicatedStorage.Shared.PointGrid) -- BD-361: pickups are found per player through a grid, not by scanning every food
local SpecialFoods = require(ReplicatedStorage.Shared.SpecialFoods) -- BD-207 (flag off by default)
local MouthReach = require(ReplicatedStorage.Shared.MouthReach) -- BD-515: eating happens at the mouth (the same pure function a client preview can use)
-- BD-381 rule: the LowPolyDinos flag is read only through LowPoly.enabled (verify_lowpoly_views); a test harness without it falls back to the root rule
local lowPolyModule: any = false
local function lowPolyOn(): boolean
    if lowPolyModule == false then
        local ok, lp = pcall(function() local shared: any = ReplicatedStorage.Shared return require(shared.LowPolyDinos) end)
        lowPolyModule = if ok and type(lp) == "table" and type(lp.enabled) == "function" then lp else nil
    end
    return lowPolyModule ~= nil and lowPolyModule.enabled() == true
end
local ScaleLadder = require(ReplicatedStorage.Shared.ScaleLadder) -- BD-407: food sizes in studs live in the one scale ladder
local RunEggTags = require(ReplicatedStorage.Shared.RunEggTags) -- BD-236: pure catch-time tag glue (tested)
local AdminMutationScale = require(ReplicatedStorage.Shared.AdminMutationScale) -- BD-237: per-player admin Mutation chance (docs/115)
local RunLifecycle = require(script.Parent.RunLifecycle) -- BD-479
local Http = game:GetService("HttpService")
local eventRandom = Random.new()
local FoodService = {}
-- BD-120 owner admin panel: runtime-only food worth multiplier (AdminService validates and clamps it).
local adminFoodMultiplier = 1
function FoodService.setAdminFoodMultiplier(value: number) adminFoodMultiplier = value end
-- BD-237: playtest-only admin multiplier on the per-egg weather mutation chance. It is PER PLAYER (LEAD decision, docs/115):
-- only the admin who set it rolls at that scale, everyone else is x1, so friends in a playtest never get boosted tags saved to
-- their profiles. Server memory only (never saved), weak-keyed so a left Player is dropped, cleared when the player leaves
-- and on admin reset / server start; AdminService (which authorizes the caller) is the only writer.
local adminMutationScales = AdminMutationScale.new()
function FoodService.setAdminMutationMultiplier(player: Player, value: number) AdminMutationScale.set(adminMutationScales, player, value) end
function FoodService.clearAdminMutationMultiplier(player: Player) AdminMutationScale.clear(adminMutationScales, player) end
function FoodService.clearAllAdminMutationMultipliers() AdminMutationScale.clearAll(adminMutationScales) end
function FoodService.adminMutationScale(player: Player): number return AdminMutationScale.get(adminMutationScales, player) end
local TYPES = {
    {id = "berry", weight = 70, points = 1, size = ScaleLadder.Food.berry.size, color = Color3.fromRGB(224, 99, 118)},
    {id = "fruit", weight = 20, points = 4, size = ScaleLadder.Food.fruit.size, color = Color3.fromRGB(244, 186, 83)},
    {id = "egg", weight = 7, points = 15, size = ScaleLadder.Food.egg.size, color = Color3.fromRGB(245, 230, 187)},
    {id = "amber", weight = 3, points = 50, size = ScaleLadder.Food.amber.size, color = Color3.fromRGB(255, 219, 139)},
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
    local kitVisuals = 0
    local generated = game:GetService("ReplicatedStorage"):FindFirstChild("GeneratedWorld") -- BD-387 drumstick mesh, nil while WorldGeneratedMeshes is off
    local obstacleParams = RaycastParams.new()
    obstacleParams.FilterType = Enum.RaycastFilterType.Include
    obstacleParams.FilterDescendantsInstances = {workspace.BeDinoArena}
    local extent = Config.ArenaHalfWidth - 8
    local sectorWidth = 2 * extent / Config.FoodSectorCount
    local function groundAt(x: number, z: number): Vector3?
        -- Safe spawn remains clear. Ground's top is y=0.
        if (Vector2.new(x, z) - Vector2.new(0, 30)).Magnitude < 11 then return nil end
        if Layout.inPool(x, z, 1.5) then return nil end -- marsh pools and the spring are decorative water
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
                food.part.Position = ground + Vector3.new(0, food.part.Size.Y / 2 + 0.35, 0)
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
            local half = Config.FoodSectorCount // 2
            local starter = (sx == half - 1 or sx == half) and sz == half
            if starter then center = Vector2.new(if sx == 7 then -15 else 15, 24) end
            for itemIndex = 1, Config.FoodClusterItems do
                local roll, kind = random:NextInteger(1, 100), TYPES[1]
                -- BD-207: better mix (owner "food still low quality"): berry 70 / fruit 20 / egg 7 / amber 3 (was 78/15/5/2); points per kind unchanged
                if roll > 97 then kind = TYPES[4] elseif roll > 90 then kind = TYPES[3] elseif roll > 70 then kind = TYPES[2] end
                if starter then kind = if itemIndex % 3 == 0 then TYPES[2] else TYPES[1] end
                -- BD-207: rare special food. The random stream is only consumed while the flag is on, so off keeps placement identical.
                local special = false
                if not starter and SpecialFoods.enabled() and SpecialFoods.rolls(random:NextNumber()) then
                    special = true
                    kind = {id = "golden_drumstick", points = SpecialFoods.points(), size = SpecialFoods.GOLDEN_DRUMSTICK.size, color = Color3.fromRGB(table.unpack(SpecialFoods.GOLDEN_DRUMSTICK.rgb))}
                end
                local kitMode = Config.FoodArtMode == "Kit"
                local artId = if kitMode then string.format("food_%s_%s", kind.id, if (sx + sz + itemIndex) % 2 == 0 then "a" else "b") else kind.id
                -- Kit mode: the uploaded food MeshPart IS the pickup part (one part, replaces the ball), scaled so its
                -- largest side equals the old ball diameter (same readability, points, attributes and validation).
                local pickup: BasePart
                local meshPickup = false
                if kitMode then
                    local ok, model = pcall(Resources.clone, artId)
                    local mesh = if ok and model then model:FindFirstChildWhichIsA("MeshPart") else nil
                    -- BD-387: every second fruit is the generated drumstick (WorldGeneratedMeshes.food_drumstick, same 4 points).
                    -- Missing/failed load keeps the kit fruit; the roll is deterministic so placement never changes.
                    local drum = generated and generated:FindFirstChild("food_drumstick")
                    if (special or (kind.id == "fruit" and (sx + sz + itemIndex) % 2 == 1)) and drum and drum:IsA("MeshPart") then
                        if model then model:Destroy() end
                        model, mesh = nil, drum:Clone()
                        mesh:SetAttribute("Drumstick", true)
                    end
                    if mesh then
                        mesh.Parent = nil
                        mesh.Size *= kind.size * (if mesh:GetAttribute("Drumstick") then ScaleLadder.Food.drumstickScale else 1) * random:NextNumber(ScaleLadder.Food.variety[1], ScaleLadder.Food.variety[2]) / math.max(mesh.Size.X, mesh.Size.Y, mesh.Size.Z) -- natural size variety
                        mesh.CFrame = CFrame.Angles(0, random:NextNumber(0, math.pi * 2), 0)
                        mesh.Name = kind.id
                        mesh.Color = Color3.new(1, 1, 1)
                        if not mesh:GetAttribute("Drumstick") then mesh.Material = Enum.Material.SmoothPlastic end
                        pickup, meshPickup = mesh, true
                    end
                    if model then model:Destroy() end
                end
                if not meshPickup then
                    local ball = Instance.new("Part")
                    ball.Name = kind.id
                    ball.Shape = Enum.PartType.Ball
                    ball.Size = Vector3.one * kind.size
                    ball.Color = kind.color
                    ball.Material = Enum.Material.SmoothPlastic
                    pickup = ball
                end
                pickup.Anchored = true
                pickup.CanCollide = false
                pickup.CanTouch = false
                pickup.CanQuery = false
                pickup:SetAttribute("Points", kind.points)
                if special then
                    pickup:SetAttribute("SpecialFood", true)
                    local glow = Instance.new("Highlight") -- tinted glow from a stock instance, not drawn art
                    glow.FillTransparency = 0.7
                    glow.FillColor, glow.OutlineColor = kind.color, kind.color
                    glow.Parent = pickup
                end
                pickup:SetAttribute("StarterFood", starter)
                pickup:SetAttribute("Sector", string.format("%d:%d", sx, sz))
                local visual = nil
                -- BD-050 Kit mode is visual only: same TYPES points, pickup part and server validation.
                -- With the uploaded MeshParts every pickup (berry, fruit, egg, amber) is its own kit mesh. Only when a kit
                -- mesh is missing does it fall back: berry/fruit keep the ball and native egg/amber models replace the
                -- ball on a deterministic stride (amber 1/4, egg 1/20) up to Config.FoodKitVisualCap (part budget, docs/68).
                pickup:SetAttribute("ArtId", artId)
                pickup:SetAttribute("KitMesh", meshPickup)
                local useModel = (kind.id == "egg" or kind.id == "amber") and not meshPickup
                if kitMode and useModel then
                    local stride = if kind.id == "amber" then 4 else 20
                    useModel = kitVisuals < Config.FoodKitVisualCap and (sx * 16 + sz + itemIndex * 7) % stride == 0
                end
                if useModel then
                    local ok, result = pcall(function()
                        local model = Resources.clone(artId)
                        if model and artId == kind.id then model:ScaleTo(kind.size / (if kind.id == "egg" then 2.4 else 1.3)) end
                        return model
                    end)
                    if ok and result and kitMode then kitVisuals += 1 end
                    if ok then visual = result end -- visible native pickup survives any art failure
                end
                local food = {part = pickup, visual = visual, readyAt = 0, hidden = false, kind = kind,
                    center = center, minX = minX, maxX = minX + sectorWidth, minZ = minZ, maxZ = minZ + sectorWidth}
                if relocate(food) then
                    pickup.Parent = folder
                    if visual then
                        pickup.Transparency = 1 -- only while the kit model is the visible pickup; show() mirrors it
                        for _, item in visual:GetDescendants() do
                            if item:IsA("BasePart") then item.Anchored = true end
                        end
                        visual.Parent = pickup
                    end
                    table.insert(foods, food)
                    workspace:SetAttribute("FoodCount", #foods)
                    -- Owner 2026-10-15: no floating point numbers over food (they cluttered the world).
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
    local grid = PointGrid.new(8)
    local hiddenFoods = {} -- foods waiting to respawn (small set), so the tick never walks all 2,400 just to look at readyAt
    for _, food in foods do local p = food.part.Position PointGrid.insert(grid, food, p.X, p.Z) end
    Players.PlayerRemoving:Connect(function(player) previous[player] = nil AdminMutationScale.clear(adminMutationScales, player) end)
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
                    if plausible then
                        -- BD-354: per-candidate values hoisted out of the food loop (was 2,400 foods x players GetAttribute calls per tick).
                        local scale = character:GetAttribute("VisualScale") or 1
                        -- BD-515 (docs/115 MR1): the pickup point is the HEAD point (root + forward x head offset of the species), the radius follows the
                        -- head size. Only for the low-poly dinos (the sizes in ScaleLadder are theirs); the legacy visual keeps the root and 2.25 + 0.75 per scale.
                        local speciesId = if Config.FoodPickupAtMouth == true and lowPolyOn() then character:GetAttribute("SpeciesId") else nil
                        local look = root.CFrame.LookVector
                        local headX, headZ = MouthReach.point(position.X, position.Z, look.X, look.Z, speciesId, scale)
                        local radius = MouthReach.radius(speciesId, scale)
                        table.insert(candidates, {player = player, character = character, root = root, gained = 0, position = position, headX = headX, headZ = headZ, radius = radius, radiusSq = radius * radius})
                    end
                else previous[player] = nil end
            end
            for food in hiddenFoods do
                if now >= food.readyAt then
                    relocate(food) -- original valid location remains if no replacement succeeds
                    local p = food.part.Position
                    PointGrid.move(grid, food, p.X, p.Z)
                    show(food, true)
                    food.hidden = false
                    hiddenFoods[food] = nil
                end
            end
            -- BD-361: each player looks only at foods in nearby grid cells (about 4 cells of 8 studs), then picks the nearest claimant per food.
            local claims = {}
            for _, candidate in candidates do
                local position = candidate.position
                local headX, headZ = candidate.headX, candidate.headZ
                local headPoint = Vector3.new(headX, position.Y, headZ) -- BD-515: reach and line of sight are measured from the mouth
                PointGrid.query(grid, headX, headZ, candidate.radius, function(food)
                    if food.hidden then return end
                    local foodPosition = food.part.Position
                    local dx, dz = foodPosition.X - headX, foodPosition.Z - headZ
                    if dx * dx + dz * dz <= candidate.radiusSq and math.abs(foodPosition.Y - position.Y) < MouthReach.VerticalLimit then
                        local horizontal = math.sqrt(dx * dx + dz * dz)
                        local blocked = workspace:Raycast(headPoint, foodPosition - headPoint, pickupParams)
                        local held = claims[food]
                        if not blocked and (not held or horizontal < held.distance or (horizontal == held.distance and candidate.player.UserId < held.candidate.player.UserId)) then
                            claims[food] = {distance = horizontal, candidate = candidate}
                        end
                    end
                end)
            end
            for food, claim in claims do
                food.readyAt = now + Config.FoodRespawnSeconds
                food.hidden = true
                hiddenFoods[food] = true
                show(food, false)
                claim.candidate.gained += food.kind.points * adminFoodMultiplier
            end
            for _, candidate in candidates do
                if candidate.gained > 0 then
                    local c = candidate.character
                    local whole, carry = FoodCatchRules.award(candidate.gained, c:GetAttribute("FoodCatchCarry") or 0, c:GetAttribute("WeatherLootMultiplier") or 1)
                    c:SetAttribute("FoodCatchCarry", carry)
                    local before=c:GetAttribute("CatchScore") or 0
                    local after=RunEggTags.nextScore(before,whole,Config.MaxCatchScore,Config.RunEggMaxPerRun)
                    c:SetAttribute("CatchScore",after)
                    if after>before then RunLifecycle.noteNestWeather(c) end -- BD-479: a nest newly earned by this catch is stamped with the weather NOW (clear too)
                    -- BD-044: every catch is one run egg. Only eggs caught during weather carry a
                    -- compact catch-time tag {eventId, mutationId, n=catch ordinal}; clear-weather
                    -- eggs need none. Genes/traits are committed once at settlement.
                    local weatherId=workspace:GetAttribute("WeatherId") or "clear"
                    if after>before and weatherId~="clear" then
                        local ok,events=pcall(function() return Http:JSONDecode(c:GetAttribute("RunEggEvents") or "[]") end)
                        if not ok or typeof(events)~="table" then events={} end
                        RunEggTags.apply(events,weatherId,before,after,function() return eventRandom:NextNumber() end,FoodService.adminMutationScale(candidate.player))
                        c:SetAttribute("RunEggEvents",Http:JSONEncode(events))
                    end
                    dinosaur.addGrowth(c, candidate.gained * Config.GrowthPerFood)
                end
            end
        end
    end)
end
return FoodService
