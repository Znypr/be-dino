--!strict
-- BD-168 distance culling for decorative world props and food (docs/89). Client-only visuals: collision proxies
-- (parts named *Collider), crystals, the hub and server food logic are untouched. Props beyond the radius are parented
-- to nil (not rendered, no scene cost); food is hidden with LocalTransparencyModifier so server writes still land.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local settings = Config.WorldCulling
if not settings or not settings.Enabled then return end
local player = Players.LocalPlayer
local camera = workspace.CurrentCamera

local function deviceClass(): string
    if not UserInputService.TouchEnabled then return "Desktop" end
    local size = camera.ViewportSize
    return if math.min(size.X, size.Y) >= 600 then "Tablet" else "Phone"
end
local class = deviceClass()
local limits = settings[class]
local override = workspace:GetAttribute("PartBudgetOverride") -- admin/test hook, optional
local radius, budget = limits.radius, (if typeof(override) == "number" then override else limits.budget)

type Prop = {item: Instance, folder: Instance, pos: Vector3, parts: number, shown: boolean}
local props: {Prop} = {}
local foods: {[BasePart]: boolean} = {}
local foodShown: {[BasePart]: boolean} = {}
local dirty = true -- new props arrive over several frames: re-evaluate even if the player stands still
local known: {[Instance]: boolean} = {} -- re-parenting a shown prop fires ChildAdded again

local function countParts(item: Instance): number
    local n = if item:IsA("BasePart") then 1 else 0
    for _, d in item:GetDescendants() do if d:IsA("BasePart") then n += 1 end end
    return n
end
local function addProp(folder: Instance, item: Instance, tries: number?)
    if known[item] or string.sub(item.Name, -8) == "Collider" then return end
    -- A model can replicate before its mesh child: locate the first part, retrying briefly if it has not arrived yet.
    local first: BasePart? = if item:IsA("BasePart") then item else item:FindFirstChildWhichIsA("BasePart", true)
    if not first then
        local left = (tries or 0) + 1
        if left <= 8 and item:IsA("Model") then task.delay(.5, function() addProp(folder, item, left) end) end
        return
    end
    known[item] = true
    dirty = true
    table.insert(props, {item = item, folder = folder, pos = first.Position, parts = countParts(item), shown = true})
end
local function setFood(pickup: BasePart, visible: boolean)
    local value = if visible then 0 else 1
    -- Legacy food draws a LocalFoodMesh model (ResourceVisuals); its placeholder ball stays hidden when shown again.
    pickup.LocalTransparencyModifier = if pickup:FindFirstChild("LocalFoodMesh") then 1 else value
    for _, d in pickup:GetDescendants() do if d:IsA("BasePart") then d.LocalTransparencyModifier = value end end
    foodShown[pickup] = visible
    pickup:SetAttribute("Culled", not visible) -- FoodGlow hides its halo with the food
end

task.spawn(function()
    local arena = workspace:WaitForChild("BeDinoArena", 60)
    local kit = if arena then arena:WaitForChild("WorldKit", 20) else nil
    if kit then
        for _, item in kit:GetChildren() do addProp(kit, item) end
        kit.ChildAdded:Connect(function(item) addProp(kit, item) end) -- the server places props over several frames
    end
    local food = workspace:WaitForChild("Food", 60)
    if food then
        for _, item in food:GetChildren() do if item:IsA("BasePart") then foods[item] = true end end
        food.ChildAdded:Connect(function(item) if item:IsA("BasePart") then foods[item] = true end end)
        food.ChildRemoved:Connect(function(item) if item:IsA("BasePart") then foods[item] = nil foodShown[item] = nil end end)
    end
    local last: Vector3? = nil
    local lastBudget = budget
    while true do
        local character = player.Character
        local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
        local override2 = workspace:GetAttribute("PartBudgetOverride")
        if typeof(override2) == "number" then budget = override2 end
        if root and root:IsA("BasePart") and (dirty or not last or (root.Position - last).Magnitude > 6 or budget ~= lastBudget) then
            last, lastBudget, dirty = root.Position, budget, false
            local origin = root.Position
            local inner, outer = radius, radius * settings.Hysteresis
            local candidates: {Prop} = {}
            for _, prop in props do
                local d = (prop.pos - origin).Magnitude
                if d < (if prop.shown then outer else inner) then
                    local loose: any = prop
                    loose.d = d
                    table.insert(candidates, prop)
                elseif prop.shown then
                    prop.shown = false
                    prop.item.Parent = nil
                end
            end
            -- Part budget: nearest props win; the rest of the candidates are culled even inside the radius.
            table.sort(candidates, function(a, b) return (a :: any).d < (b :: any).d end)
            local used, visibleProps = 0, 0
            for _, prop in candidates do
                if used + prop.parts <= budget then
                    used += prop.parts
                    visibleProps += 1
                    if not prop.shown then prop.shown = true prop.item.Parent = prop.folder end
                elseif prop.shown then
                    prop.shown = false
                    prop.item.Parent = nil
                end
            end
            local foodRadius = radius * settings.FoodRadiusFactor
            for pickup in foods do
                local d = (pickup.Position - origin).Magnitude
                local want = d < (if foodShown[pickup] ~= false then foodRadius * settings.Hysteresis else foodRadius)
                if foodShown[pickup] ~= want then setFood(pickup, want) end
            end
            player:SetAttribute("CullClass", class)
            player:SetAttribute("CullRadius", radius)
            player:SetAttribute("CullBudget", budget)
            player:SetAttribute("CullProps", visibleProps .. "/" .. #props)
            player:SetAttribute("CullParts", used)
        end
        task.wait(.4)
    end
end)
