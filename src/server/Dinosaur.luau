--!strict
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local PhysicsService = game:GetService("PhysicsService")
local Dinosaur = {}
local Visual = require(ReplicatedStorage.Shared.DinosaurVisual)
function Dinosaur.render(character: Model, scale: number, speciesId: string?, gold: boolean?)
    Visual.render(character, scale, speciesId, gold)
    local collider = character:FindFirstChild("DinoCollider")
    if collider and collider:IsA("BasePart") then
        -- Match the growing torso footprint; keep floor clearance and the tail visual-only.
        collider.Size = Vector3.new(2.6 * scale, 2.4, 3.2 * scale)
    end
end
local function scaleForScore(score: number): number
    return math.min(4, math.sqrt(1 + math.max(0, score) / 50))
end
if not PhysicsService:IsCollisionGroupRegistered("DinoControllers") then
    PhysicsService:RegisterCollisionGroup("DinoControllers")
end
PhysicsService:CollisionGroupSetCollidable("DinoControllers", "DinoControllers", false)

function Dinosaur.setSpecies(character: Model, speciesId: string, isGold: boolean?)
    local scaleValue = character:GetAttribute("VisualScale")
    local scale = if typeof(scaleValue) == "number" then scaleValue else 1
    Dinosaur.render(character, scale, speciesId, isGold)
end

local function playerSpeciesCounts(player: Player, speciesId: string): (number, number)
    if speciesId == "compy" then
        return player:GetAttribute("CompyCopies") or 0, player:GetAttribute("CompyGold") or 0
    elseif speciesId == "triceratops" then
        return player:GetAttribute("TriceratopsCopies") or 0, player:GetAttribute("TriceratopsGold") or 0
    elseif speciesId == "tyrannosaurus" then
        return player:GetAttribute("TyrannosaurusCopies") or 0, player:GetAttribute("TyrannosaurusGold") or 0
    end
    return 0, 0
end

function Dinosaur.refreshForPlayer(character: Model, player: Player)
    local equipped = player:GetAttribute("EquippedSpeciesId")
    local speciesId = if typeof(equipped) == "string" then equipped else "compy"
    local baseCount, goldCount = playerSpeciesCounts(player, speciesId)
    local useGold = baseCount <= 0 and goldCount > 0
    Dinosaur.setSpecies(character, speciesId, useGold)
end

function Dinosaur.addGrowth(character: Model, points: number)
    if points <= 0 or character:GetAttribute("RunState") ~= "Active" then return end
    local current = character:GetAttribute("GrowthScore")
    local score = (if typeof(current) == "number" then current else 0) + points * math.clamp(character:GetAttribute("GrowthMultiplier") or 1,1,8)
    character:SetAttribute("GrowthScore", score)
    local scale = scaleForScore(score)
    if character:GetAttribute("VisualScale") ~= scale then
        local gold = character:GetAttribute("GoldVisual") == true
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
    humanoid.JumpPower = require(ReplicatedStorage.Shared.Config).JumpPower
    humanoid.MaxSlopeAngle = require(ReplicatedStorage.Shared.Config).MaxSlopeAngle
    humanoid.AutoJumpEnabled = false
    humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, true)

    -- Explicit torso collider: decorative mesh triangles never control physics.
    for _, item in character:GetDescendants() do
        if item:IsA("BasePart") then item.CollisionGroup = "DinoControllers" end
    end
    local collider = Instance.new("Part")
    collider.Name = "DinoCollider"
    collider.Size = Vector3.new(2.6, 2.4, 3.2)
    collider.Transparency = 1
    collider.Massless = true
    collider.CanCollide = true
    collider.CanTouch = false
    collider.CollisionGroup = "DinoControllers"
    local groundHeight = root.Size.Y / 2 + humanoid.HipHeight
    if humanoid.RigType == Enum.HumanoidRigType.R6 then
        local leg = character:FindFirstChild("Left Leg")
        groundHeight += if leg and leg:IsA("BasePart") then leg.Size.Y else 2
    end
    collider.CFrame = root.CFrame * CFrame.new(0, -groundHeight + 1.4, 0)
    collider.Parent = character
    local weld = Instance.new("WeldConstraint")
    weld.Part0 = root
    weld.Part1 = collider
    weld.Parent = collider
    Dinosaur.refreshForPlayer(character, player)
    character:SetAttribute("DinoAttached", true)
end

return Dinosaur
