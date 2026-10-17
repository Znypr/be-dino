--!strict
-- BD-168 distance culling for decorative world props and food (docs/89). Client-only visuals: collision proxies
-- (parts named *Collider), crystals, the hub and server food logic are untouched. Props beyond the radius are parented
-- to nil (not rendered, no scene cost); food is hidden with LocalTransparencyModifier so server writes still land.
-- BD-497 (docs/146 risk 2): on a PHONE only, the invisible prop colliders are culled by the same radius (PhoneGuards.colliderWanted). They only block trees,
-- rocks, logs and landmarks for the local dino, which never reaches one beyond the radius; the ground is Terrain and stays. Other devices: unchanged.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local ColossalRules = require(ReplicatedStorage.Shared:WaitForChild("ColossalRules"))
local PhoneGuards = require(ReplicatedStorage.Shared:WaitForChild("PhoneGuards"))
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
-- BD-475 (docs/142): colossal ancient trees (BD-474 meshes, ids pasted) carry two meshes, LOD0 near and LOD1 far; exactly one is parented at a
-- time. They are decided by ColossalRules (own radius, swap distance, LOD0 cap, triangle budget) and never enter `props`. With empty mesh ids no
-- model has the ColossalKey attribute, `colossals` stays empty and nothing below changes.
type Colossal = {item: Model, folder: Instance, lod0: BasePart, lod1: BasePart, pos: Vector3, tris0: number, tris1: number, state: string, alpha: number}
local colossals: {Colossal} = {}
local colossalSettings = ColossalRules.settings(settings, class)
type Collider = {part: BasePart, folder: Instance, pos: Vector3, shown: boolean}
local cullColliders = PhoneGuards.cullColliders(class)
local colliders: {Collider} = {} -- stays empty off the phone class, so nothing below changes there
local foods: {[BasePart]: boolean} = {}
local foodShown: {[BasePart]: boolean} = {}
local dirty = true -- new props arrive over several frames: re-evaluate even if the player stands still
local known: {[Instance]: boolean} = {} -- re-parenting a shown prop fires ChildAdded again

local function countParts(item: Instance): number
    local n = if item:IsA("BasePart") then 1 else 0
    for _, d in item:GetDescendants() do if d:IsA("BasePart") then n += 1 end end
    return n
end
local addProp: (folder: Instance, item: Instance, tries: number?) -> () -- forward: addColossal retries through it
local function addColossal(folder: Instance, item: Model, tries: number?): boolean
    -- Both meshes must have replicated; retry briefly, then give up and let the model be a plain prop (LOD0 only).
    local lod1 = item:FindFirstChild("ColossalLod1")
    local lod0: BasePart? = nil
    for _, child in item:GetChildren() do
        if child:IsA("BasePart") and child ~= lod1 then lod0 = child break end
    end
    if not (lod1 and lod1:IsA("BasePart") and lod0 and colossalSettings) then
        local left = (tries or 0) + 1
        if left <= 8 then
            task.delay(.5, function() addProp(folder, item, left) end)
            return true
        end
        return false
    end
    known[item] = true
    dirty = true
    lod1.Parent = nil -- LOD0 is the shown one until the first evaluation
    table.insert(colossals, {item = item, folder = folder, lod0 = lod0, lod1 = lod1, pos = item:GetPivot().Position,
        tris0 = tonumber(item:GetAttribute("ColossalTris0")) or 4000, tris1 = tonumber(item:GetAttribute("ColossalTris1")) or 1000,
        state = "lod0", alpha = 0})
    return true
end
addProp = function(folder: Instance, item: Instance, tries: number?)
    if string.sub(item.Name, -8) == "Collider" then
        if cullColliders and not known[item] and item:IsA("BasePart") then
            known[item] = true
            dirty = true
            table.insert(colliders, {part = item, folder = folder, pos = item.Position, shown = true})
        end
        return
    end
    if known[item] then return end
    if item:IsA("Model") and item:GetAttribute("ColossalKey") ~= nil and addColossal(folder, item, tries) then return end
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
    -- BD-475: colossal trees fade out over the last share of their radius instead of popping (docs/139 Q12), a few times a second. This uses
    -- Transparency (client-local), the camera occlusion fade uses LocalTransparencyModifier, so the two never fight over one property.
    task.spawn(function()
        while true do
            task.wait(.15)
            local character = player.Character
            local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
            if colossalSettings and #colossals > 0 and root and root:IsA("BasePart") then
                local at = root.Position
                for _, tree in colossals do
                    if tree.state ~= "off" then
                        local dx, dz = tree.pos.X - at.X, tree.pos.Z - at.Z
                        local alpha = ColossalRules.fadeAlpha(math.sqrt(dx * dx + dz * dz), colossalSettings.radius, colossalSettings.fade)
                        if alpha ~= tree.alpha then
                            tree.alpha = alpha
                            local mesh = if tree.state == "lod0" then tree.lod0 else tree.lod1
                            mesh.Transparency = alpha
                        end
                    end
                end
            end
        end
    end)
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
            -- BD-475 colossal ancient trees: after the ordinary props, so a far one only gets in while the part budget still allows it.
            if colossalSettings and #colossals > 0 then
                local items: {ColossalRules.Item} = {}
                for i, tree in colossals do
                    local dx, dz = tree.pos.X - origin.X, tree.pos.Z - origin.Z -- horizontal: the pivot is the trunk base, a 100 stud tree is not "50 up"
                    items[i] = {d = math.sqrt(dx * dx + dz * dz), state = tree.state, tris0 = tree.tris0, tris1 = tree.tris1}
                end
                local states, stats = ColossalRules.assign(items, colossalSettings, settings.Hysteresis, budget - used)
                for i, tree in colossals do
                    local want = states[i]
                    if want ~= tree.state then
                        if want == "off" then
                            tree.item.Parent = nil
                        else
                            local shown, hidden = if want == "lod0" then tree.lod0 else tree.lod1, if want == "lod0" then tree.lod1 else tree.lod0
                            hidden.Parent = nil
                            shown.Parent = tree.item
                            shown.Transparency = tree.alpha
                            if tree.item.Parent == nil then tree.item.Parent = tree.folder end
                        end
                        tree.state = want
                    end
                end
                used += stats.parts
                player:SetAttribute("CullColossal", stats.lod0 .. "/" .. stats.lod1 .. "/" .. #colossals .. " " .. stats.tris)
            end
            if cullColliders then
                local keptColliders = 0
                for _, c in colliders do
                    local want = PhoneGuards.colliderWanted(class, c.shown, (c.pos - origin).Magnitude, radius, settings.Hysteresis)
                    if want ~= c.shown then
                        c.shown = want
                        c.part.Parent = if want then c.folder else nil
                    end
                    if want then keptColliders += 1 end
                end
                player:SetAttribute("CullColliders", keptColliders .. "/" .. #colliders)
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
