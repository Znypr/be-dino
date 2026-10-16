--!strict
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local PhysicsService = game:GetService("PhysicsService")
local Dinosaur = {}
local PrivateState = require(script.Parent.PrivateState)
local Visual = require(ReplicatedStorage.Shared.DinosaurVisual)
local Config = require(ReplicatedStorage.Shared.Config)
local MovementEnvelope = require(ReplicatedStorage.Shared.MovementEnvelope)
local HubScale = require(ReplicatedStorage.Shared.HubScaleRules)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)
local function groundHeight(character: Model, root: BasePart, humanoid: Humanoid): number
    local height = root.Size.Y / 2 + humanoid.HipHeight
    if humanoid.RigType == Enum.HumanoidRigType.R6 then
        local leg = character:FindFirstChild("Left Leg")
        height += if leg and leg:IsA("BasePart") then leg.Size.Y else 2
    end
    return height
end

-- BD-053: the footprint follows the growing torso, but the box is lifted by the slope
-- clearance from MovementEnvelope so it never wedges into walkable hills (the previous
-- fixed 0.2-stud clearance snagged on any slope above ~5 degrees and slid dinosaurs back).
local function placeCollider(character: Model, scale: number)
    local collider = character:FindFirstChild("DinoCollider")
    local root = character:FindFirstChild("HumanoidRootPart")
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not collider or not collider:IsA("BasePart") or not root or not root:IsA("BasePart") or not humanoid then return end
    local width, height, length, offsetY = MovementEnvelope.collider(scale, groundHeight(character, root, humanoid))
    collider.Size = Vector3.new(width, height, length)
    local weld = collider:FindFirstChild("ColliderWeld")
    if weld and weld:IsA("Weld") then weld.C0 = CFrame.new(0, offsetY, 0) end
end

function Dinosaur.render(character: Model, scale: number, speciesId: string?, gold: (boolean | string)?)
    Visual.render(character, scale, speciesId, gold)
    placeCollider(character, scale)
end
-- BD-480 (OWNER 2026-10-16): the one place a character's drawn size is decided. Growth curve x BIG on the island; exactly 1 in
-- the cave hub (flag Config.CaveHub, root inside the hub footprint), whatever the BIG trait, potions or growth. Every render
-- path below (equip refresh, growth, attach, run-state change, hub tick) goes through here, so the hub size cannot drift.
local function desiredScale(character: Model): number
    local root = character:FindFirstChild("HumanoidRootPart")
    local inHub = false
    if root and root:IsA("BasePart") then
        local p = root.Position
        inHub = SpawnGeometry.inHub(Config, p.X, p.Z)
    end
    return HubScale.scale({
        caveHub = Config.CaveHub == true, inHub = inHub, score = character:GetAttribute("GrowthScore"),
        big = character:GetAttribute("BigDinosaur") == true, bigMultiplier = Config.BigScaleMultiplier,
    })
end

-- Re-render at the size the character should have right now (cheap no-op when it already has it). Returns true when it rendered.
function Dinosaur.syncScale(character: Model): boolean
    if character:GetAttribute("DinoAttached") ~= true then return false end
    local scale = desiredScale(character)
    local current = character:GetAttribute("VisualScale")
    if typeof(current) == "number" and math.abs(current - scale) < 1e-6 then return false end
    Dinosaur.render(character, scale, nil, character:GetAttribute("MutationVisual") or "base")
    return true
end
if not PhysicsService:IsCollisionGroupRegistered("DinoControllers") then
    PhysicsService:RegisterCollisionGroup("DinoControllers")
end
PhysicsService:CollisionGroupSetCollidable("DinoControllers", "DinoControllers", false)

function Dinosaur.setSpecies(character: Model, speciesId: string, isGold: (boolean | string)?)
    local scaleValue = character:GetAttribute("VisualScale")
    local scale = if typeof(scaleValue) == "number" then scaleValue else 1
    Dinosaur.render(character, scale, speciesId, isGold)
end

function Dinosaur.refreshForPlayer(character: Model, player: Player)
    local equipped = player:GetAttribute("EquippedSpeciesId")
    local speciesId = if typeof(equipped) == "string" then equipped else "compy"
    local ok, collection = pcall(function() return game:GetService("HttpService"):JSONDecode(PrivateState.get(player, "CollectionJson") or "{}") end)
    local entry = if ok then collection[speciesId] else nil
    local mutation = if entry and (entry.diamond or 0) > 0 then "diamond" elseif entry and (entry.emerald or 0) > 0 then "emerald" elseif entry and (entry.gold or 0) > 0 then "gold" else "base"
    if player:GetAttribute("EquippedGenesJson") and player:GetAttribute("EquippedGenesJson")~="null" then mutation="base" end
    -- Genes first so the client repaint triggered by SpeciesId/MutationVisual already sees the new equip.
    character:SetAttribute("GenesJson", player:GetAttribute("EquippedGenesJson") or "null")
    character:SetAttribute("BigDinosaur", player:GetAttribute("EquippedBig") == true)
    Dinosaur.render(character, desiredScale(character), speciesId, mutation)
end

function Dinosaur.addGrowth(character: Model, points: number)
    if points <= 0 or character:GetAttribute("RunState") ~= "Active" then return end
    local current = character:GetAttribute("GrowthScore")
    local score = (if typeof(current) == "number" then current else 0) + points * math.clamp(character:GetAttribute("GrowthMultiplier") or 1,.1,8)
    character:SetAttribute("GrowthScore", score)
    local scale = desiredScale(character)
    if character:GetAttribute("VisualScale") ~= scale then
        local gold = character:GetAttribute("MutationVisual") or "base"
        Dinosaur.render(character, scale, nil, gold)
    end
end

function Dinosaur.attach(character: Model, walkSpeed: number, player: Player)
    local deadline = os.clock() + 10
    while not character:IsDescendantOf(workspace) do
        if player.Character ~= character or not player.Parent then return end
        if os.clock() >= deadline then return end
        RunService.Heartbeat:Wait()
    end
    local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
    local root = character:WaitForChild("HumanoidRootPart", 10) :: BasePart?
    if player.Character ~= character or not character:IsDescendantOf(workspace) then return end
    if not humanoid or not root or character:GetAttribute("DinoAttached") then return end

    local function hide(instance: Instance)
        if instance:FindFirstAncestor("DinoVisual") then return end
        if instance:IsA("BasePart") then instance.Transparency = 1 end
        if instance:IsA("Decal") then instance.Transparency = 1 end
    end
    for _, descendant in character:GetDescendants() do hide(descendant) end
    character.DescendantAdded:Connect(hide)

    humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
    humanoid.WalkSpeed = walkSpeed
    humanoid.UseJumpPower = true
    humanoid.JumpPower = (workspace:GetAttribute("Admin_jumpPower") :: number?) or Config.JumpPower
    humanoid.MaxSlopeAngle = Config.MaxSlopeAngle
    humanoid.AutoJumpEnabled = false
    humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, true)

    -- Explicit torso collider: decorative mesh triangles never control physics.
    for _, item in character:GetDescendants() do
        if item:IsA("BasePart") then item.CollisionGroup = "DinoControllers" end
    end
    local collider = Instance.new("Part")
    collider.Name = "DinoCollider"
    collider.Transparency = 1
    collider.Massless = true
    collider.CanCollide = true
    collider.CanTouch = false
    collider.CollisionGroup = "DinoControllers"
    local width, height, length, offsetY = MovementEnvelope.collider(1, groundHeight(character, root, humanoid))
    collider.Size = Vector3.new(width, height, length)
    collider.CFrame = root.CFrame * CFrame.new(0, offsetY, 0)
    collider.Parent = character
    -- A rigid Weld (not WeldConstraint) so growth can move the box by editing C0.
    local weld = Instance.new("Weld")
    weld.Name = "ColliderWeld"
    weld.Part0 = root
    weld.Part1 = collider
    weld.C0 = CFrame.new(0, offsetY, 0)
    weld.Parent = collider
    Dinosaur.refreshForPlayer(character, player)
    character:SetAttribute("DinoAttached", true)
    -- BD-480: entering the island (RunState Sanctuary -> Active, after the teleport) restores the growth/BIG size at once.
    character:GetAttributeChangedSignal("RunState"):Connect(function() Dinosaur.syncScale(character) end)
end

return Dinosaur
