--!strict
-- BD-222 food readability (owner playtest 2026-10-15: food was barely visible on grass). Client-only visuals:
-- a soft halo + rim ring under each NEAR food (one pooled BillboardGui per slot, no PointLight, no extra parts),
-- a slow bob and spin, a small sparkle every few seconds and a 1.25x look scale. Rarer food glows stronger in its
-- rarity colour (docs/88 tiers; a server "FoodRarity" attribute wins, ready for BD-207 special foods).
-- Budget: at most SLOTS foods are decorated (nearest within RADIUS); slots are reassigned every REASSIGN seconds,
-- per-frame work touches only assigned slots and allocates nothing. Culled (WorldCulling "Culled" attribute) or eaten
-- (server Transparency 1) food has its slot hidden. Reduce Motion: no bob/spin/sparkle, static glow.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Assets = require(Shared:WaitForChild("EffectAssets"))

local SLOTS, RADIUS, REASSIGN, LOOK_SCALE = 56, 130, .5, 1.3 -- BD-387: more and farther halos so food reads from afar
local BOB, BOB_SPEED, SPIN_SPEED = .22, 1.6, .7
local TIER_BY_NAME = {berry = "Common", fruit = "Uncommon", egg = "Rare", amber = "Epic"}
local CREAM = Color3.fromRGB(255, 244, 200) -- warm base glow: reads on green grass, sand and rock alike
local TIERS: {[string]: {ring: Color3, glow: number, ringT: number, size: number}} = {
    Common = {ring = CREAM, glow = .45, ringT = .55, size = 3.2},
    Uncommon = {ring = Color3.fromRGB(150, 255, 90), glow = .38, ringT = .3, size = 3.6},
    Rare = {ring = Color3.fromRGB(46, 206, 255), glow = .3, ringT = .15, size = 4.2},
    Epic = {ring = Color3.fromRGB(194, 86, 255), glow = .25, ringT = .08, size = 4.8},
    Legendary = {ring = Color3.fromRGB(255, 210, 43), glow = .2, ringT = 0, size = 5.4},
}
local GLOW_IMAGE, RING_IMAGE, STAR_IMAGE = Assets.resolve("glowPlate"), Assets.resolve("ringSoft"), Assets.resolve("starFour")

local player = Players.LocalPlayer
local holder = Instance.new("Folder")
holder.Name = "FoodGlow"
holder.Parent = player:WaitForChild("PlayerGui")

type Slot = {gui: BillboardGui, glow: ImageLabel, ring: ImageLabel, star: ImageLabel, food: BasePart?, phase: number}
type Food = {part: BasePart, target: Instance?, base: CFrame, written: CFrame?, scaled: boolean, tier: string, slot: Slot?, d: number}
local slots: {Slot} = {}
local foods: {[BasePart]: Food} = {}
local order: {Food} = {} -- reused every reassign, never reallocated

local function image(parent: Instance, name: string, id: string, z: number): ImageLabel
    local label = Instance.new("ImageLabel")
    label.Name, label.Image, label.BackgroundTransparency, label.ZIndex = name, id, 1, z
    label.AnchorPoint, label.Position, label.Size = Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromScale(1, 1)
    label.Parent = parent
    return label
end
for i = 1, SLOTS do
    local gui = Instance.new("BillboardGui")
    gui.Name, gui.Enabled, gui.LightInfluence, gui.MaxDistance = "FoodGlow" .. i, false, 0, RADIUS * 1.2
    gui.ResetOnSpawn = false
    gui.Parent = holder
    local glow = image(gui, "Glow", GLOW_IMAGE, 1)
    glow.ImageColor3 = CREAM
    local ring = image(gui, "Ring", RING_IMAGE, 2)
    ring.Size = UDim2.fromScale(.62, .62)
    local star = image(gui, "Sparkle", STAR_IMAGE, 3)
    star.ImageTransparency, star.Size = 1, UDim2.fromScale(.3, .3)
    slots[i] = {gui = gui, glow = glow, ring = ring, star = star, food = nil, phase = i * 1.37}
end

-- The visible art: Legacy mode draws a LocalFoodMesh model (ResourceVisuals); Kit mode / fallback draws the part itself.
-- A server-cloned native model (rare fallback) is not animated, only haloed.
local function targetOf(food: Food): Instance
    local mesh = food.part:FindFirstChild("LocalFoodMesh")
    if mesh then return mesh end
    if food.part:FindFirstChildWhichIsA("Model") then return food.part :: Instance end
    return food.part
end
local function pivotOf(target: Instance): CFrame
    return if target:IsA("Model") then target:GetPivot() else (target :: BasePart).CFrame
end
local function setPivot(target: Instance, cf: CFrame)
    if target:IsA("Model") then target:PivotTo(cf) else (target :: BasePart).CFrame = cf end
end
local function animatable(food: Food, target: Instance): boolean
    return target ~= food.part or not food.part:FindFirstChildWhichIsA("Model")
end
local function hidden(food: Food): boolean
    local part = food.part
    if part:GetAttribute("Culled") == true then return true end
    local native = part:FindFirstChildWhichIsA("Model")
    if native and native.Name ~= "LocalFoodMesh" then
        local piece = native:FindFirstChildWhichIsA("BasePart", true)
        return piece ~= nil and piece.Transparency >= 1
    end
    return part.Transparency >= 1
end
local function restore(food: Food)
    local target = food.target
    if target and food.written and target.Parent then setPivot(target, food.base) end
    food.written = nil
end
local function release(slot: Slot)
    local food = if slot.food then foods[slot.food] else nil
    if food then restore(food) food.slot = nil end
    slot.food, slot.gui.Enabled, slot.gui.Adornee = nil, false, nil
end
local function bind(slot: Slot, food: Food)
    slot.food, food.slot = food.part, slot
    local tier = TIERS[food.tier] or TIERS.Common
    local size = tier.size * math.max(1, food.part.Size.Y)
    slot.gui.Adornee = food.part
    slot.gui.Size = UDim2.fromScale(size, size)
    slot.gui.StudsOffsetWorldSpace = Vector3.new(0, -food.part.Size.Y * .35, 0)
    slot.glow.ImageTransparency, slot.glow.ImageColor3 = tier.glow, CREAM
    slot.ring.ImageTransparency, slot.ring.ImageColor3 = tier.ringT, tier.ring
    slot.star.ImageColor3 = tier.ring
end

local function track(item: Instance)
    if not item:IsA("BasePart") or not item:GetAttribute("Points") or foods[item] then return end
    local rarity = item:GetAttribute("FoodRarity")
    foods[item] = {part = item, target = nil, base = item.CFrame, written = nil, scaled = false,
        tier = if type(rarity) == "string" and TIERS[rarity] then rarity else (TIER_BY_NAME[item.Name] or "Common"), slot = nil, d = 0}
end
local function untrack(item: Instance)
    local food = foods[item :: BasePart]
    if food and food.slot then release(food.slot) end
    foods[item :: BasePart] = nil
end

-- 1.25x look scale, once per food (Legacy mesh model or the part itself). Server Size/points/validation untouched.
local function ensureScaled(food: Food, target: Instance)
    if food.scaled and food.target == target then return end
    if target:IsA("Model") then
        if target:GetAttribute("GlowScaled") ~= true then
            target:ScaleTo(target:GetScale() * LOOK_SCALE)
            target:SetAttribute("GlowScaled", true)
        end
    elseif not food.scaled then
        local part = target :: BasePart
        part.Size *= LOOK_SCALE
    end
    food.scaled, food.target, food.written = true, target, nil
    food.base = pivotOf(target)
end

local function byDistance(a: Food, b: Food): boolean return a.d < b.d end
local function reassign()
    local character = player.Character
    local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
    if not root or not root:IsA("BasePart") then return end
    local origin = root.Position
    local n = 0
    for part, food in foods do
        if part.Parent and not hidden(food) then
            local d = (part.Position - origin).Magnitude
            if d < RADIUS then
                food.d = d
                n += 1
                order[n] = food
            end
        end
    end
    for i = n + 1, #order do order[i] = nil end
    table.sort(order, byDistance)
    -- Free slots whose food fell out of the nearest set, then fill empty slots.
    for _, slot in slots do
        local food = if slot.food then foods[slot.food] else nil
        if slot.food and (not food or not food.part.Parent or hidden(food) or food.d >= RADIUS
            or (n > SLOTS and food.d > order[SLOTS].d)) then release(slot) end
    end
    local free = 1
    for i = 1, math.min(n, SLOTS) do
        local food = order[i]
        if not food.slot then
            while free <= SLOTS and slots[free].food do free += 1 end
            if free > SLOTS then break end
            bind(slots[free], food)
        end
    end
    player:SetAttribute("FoodGlowSlots", math.min(n, SLOTS) .. "/" .. SLOTS)
end

task.spawn(function()
    local folder = workspace:WaitForChild("Food", 60)
    if not folder then return end
    for _, item in folder:GetChildren() do track(item) end
    folder.ChildAdded:Connect(track)
    folder.ChildRemoved:Connect(untrack)
    local sinceAssign, clock = REASSIGN, 0
    local wasMotion = Theme.MotionEnabled
    RunService.Heartbeat:Connect(function(dt)
        clock += dt
        sinceAssign += dt
        if sinceAssign >= REASSIGN then sinceAssign = 0 reassign() end
        local motion = Theme.MotionEnabled
        for _, slot in slots do
            local food = if slot.food then foods[slot.food] else nil
            if not food then continue end
            if hidden(food) then release(slot) continue end
            slot.gui.Enabled = true
            local target = targetOf(food)
            ensureScaled(food, target)
            if not animatable(food, target) then continue end
            -- The server may move the food (respawn relocation): any pivot we did not write becomes the new base.
            local now = pivotOf(target)
            if food.written == nil or now ~= food.written then food.base = now end
            if motion then
                local t = clock + slot.phase
                local cf = food.base * CFrame.new(0, BOB * (1 + math.sin(t * BOB_SPEED)), 0) * CFrame.Angles(0, (t * SPIN_SPEED) % (math.pi * 2), 0)
                setPivot(target, cf)
                food.written = pivotOf(target)
                -- Sparkle: a short soft twinkle once every ~4 s per food, staggered by slot phase.
                local s = (t % 4) / .6
                if s < 1 then
                    slot.star.ImageTransparency = .15 + .85 * math.abs(s * 2 - 1)
                    slot.star.Position = UDim2.fromScale(.5 + .14 * math.sin(slot.phase), .38)
                    slot.star.Size = UDim2.fromScale(.18 + .16 * math.sin(s * math.pi), .18 + .16 * math.sin(s * math.pi))
                elseif slot.star.ImageTransparency < 1 then
                    slot.star.ImageTransparency = 1
                end
            elseif wasMotion or food.written then
                restore(food)
                slot.star.ImageTransparency = 1
            end
        end
        wasMotion = motion
    end)
end)
