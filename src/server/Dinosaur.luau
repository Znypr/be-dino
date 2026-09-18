--!strict
-- Original procedural dinosaur kit. Visual-only shell over Roblox's fixed controller collider.
local Dinosaur = {}
local RunService = game:GetService("RunService")

local GOLD_PALETTE = {
    primary = Color3.fromRGB(236, 185, 52),
    light = Color3.fromRGB(255, 229, 126),
    dark = Color3.fromRGB(151, 102, 22),
    accent = Color3.fromRGB(255, 244, 183),
}

local PALETTES = {
    compy = {
        primary = Color3.fromRGB(91, 174, 114),
        light = Color3.fromRGB(191, 225, 147),
        dark = Color3.fromRGB(48, 107, 72),
        accent = Color3.fromRGB(245, 198, 92),
    },
    triceratops = {
        primary = Color3.fromRGB(92, 148, 188),
        light = Color3.fromRGB(184, 219, 222),
        dark = Color3.fromRGB(58, 91, 128),
        accent = Color3.fromRGB(239, 205, 135),
    },
    tyrannosaurus = {
        primary = Color3.fromRGB(191, 116, 69),
        light = Color3.fromRGB(232, 176, 116),
        dark = Color3.fromRGB(117, 65, 48),
        accent = Color3.fromRGB(239, 215, 152),
    },
}

local function scaleForScore(score: number): number
    return math.min(4, math.sqrt(1 + math.max(0, score) / 50))
end

local function normalizedSpecies(speciesId: any): string
    if typeof(speciesId) == "string" and PALETTES[speciesId] then
        return speciesId
    end
    return "compy"
end

function Dinosaur.render(character: Model, scale: number, requestedSpeciesId: string?, isGold: boolean?)
    local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not root or not humanoid then return end

    local speciesId = normalizedSpecies(requestedSpeciesId or character:GetAttribute("SpeciesId"))
    local gold = isGold == true
    local palette = if gold then GOLD_PALETTE else PALETTES[speciesId]

    local old = character:FindFirstChild("DinoVisual")
    if old then old:Destroy() end
    local visual = Instance.new("Model")
    visual.Name = "DinoVisual"
    visual.Parent = character

    local groundHeight = root.Size.Y / 2 + humanoid.HipHeight
    if humanoid.RigType == Enum.HumanoidRigType.R6 then
        local leg = character:FindFirstChild("Left Leg") :: BasePart?
        groundHeight += if leg then leg.Size.Y else 2
    end
    local shift = Vector3.new(0, 3.1 * scale - groundHeight, 0)

    local function piece(
        name: string,
        size: Vector3,
        position: Vector3,
        color: Color3,
        rotation: Vector3?,
        shape: Enum.PartType?
    )
        local part = Instance.new("Part")
        part.Name = name
        part.Shape = shape or Enum.PartType.Block
        part.Size = size * scale
        part.Color = color
        part.Material = if gold then Enum.Material.Metal else Enum.Material.SmoothPlastic
        part.CanCollide = false
        part.CanTouch = false
        part.CanQuery = false
        part.Massless = true
        part.CastShadow = true

        local r = rotation or Vector3.zero
        local offset = CFrame.new(position * scale + shift)
            * CFrame.Angles(math.rad(r.X), math.rad(r.Y), math.rad(r.Z))
        part.CFrame = root.CFrame * offset
        part.Parent = visual

        local weld = Instance.new("Weld")
        weld.Name = "VisualWeld"
        weld.Part0 = root
        weld.Part1 = part
        weld.C0 = offset
        weld.Parent = part
        return part
    end

    local function eye(side: number, x: number, y: number, z: number)
        piece("EyeWhite" .. side, Vector3.new(0.34, 0.55, 0.42), Vector3.new(side * x, y, z),
            Color3.fromRGB(249, 247, 226), Vector3.zero, Enum.PartType.Ball)
        piece("Pupil" .. side, Vector3.new(0.22, 0.30, 0.22), Vector3.new(side * (x + 0.10), y, z - 0.14),
            Color3.fromRGB(25, 37, 31), Vector3.zero, Enum.PartType.Ball)
    end

    if speciesId == "compy" then
        piece("Body", Vector3.new(2.2, 1.65, 3.1), Vector3.new(0, -0.75, 0.25), palette.primary, nil, Enum.PartType.Ball)
        piece("Chest", Vector3.new(1.65, 1.15, 1.9), Vector3.new(0, -1.25, -0.65), palette.light, nil, Enum.PartType.Ball)
        piece("Head", Vector3.new(2.15, 1.55, 1.95), Vector3.new(0, 0.15, -1.85), palette.primary, nil, Enum.PartType.Ball)
        piece("Snout", Vector3.new(1.75, 0.75, 1.25), Vector3.new(0, -0.10, -3.0), palette.light, nil, Enum.PartType.Ball)
        piece("Tail", Vector3.new(0.95, 0.95, 3.4), Vector3.new(0, -0.75, 2.85), palette.primary, Vector3.new(-12,0,0))
        piece("TailTip", Vector3.new(0.48, 0.48, 2.0), Vector3.new(0, -0.15, 5.15), palette.dark, Vector3.new(-20,0,0))
        for _, side in {-1, 1} do
            piece("Leg" .. side, Vector3.new(0.68, 1.45, 0.78), Vector3.new(side * 0.78, -2.05, 0.25), palette.dark)
            piece("Foot" .. side, Vector3.new(0.8, 0.32, 1.45), Vector3.new(side * 0.78, -2.82, -0.10), palette.primary)
            piece("Arm" .. side, Vector3.new(0.38, 0.44, 0.95), Vector3.new(side * 1.0, -0.72, -1.18), palette.primary, Vector3.new(18,0,side*12))
            eye(side, 0.92, 0.45, -2.15)
        end
        for i = 1, 4 do
            piece("BackSpike" .. i, Vector3.new(0.30, 0.75, 0.42),
                Vector3.new(0, 0.22, 0.95 + (i - 1) * 0.68), palette.accent, Vector3.new(0,0,45))
        end
        piece("Crest", Vector3.new(0.50, 0.85, 0.75), Vector3.new(0, 1.02, -1.45), palette.accent, Vector3.new(0,0,45))
    elseif speciesId == "triceratops" then
        piece("Body", Vector3.new(3.35, 1.95, 3.75), Vector3.new(0, -0.95, 0.35), palette.primary, nil, Enum.PartType.Ball)
        piece("Belly", Vector3.new(2.35, 0.85, 2.7), Vector3.new(0, -1.70, 0.20), palette.light, nil, Enum.PartType.Ball)
        piece("Head", Vector3.new(2.75, 1.75, 2.0), Vector3.new(0, -0.05, -2.0), palette.primary, nil, Enum.PartType.Ball)
        piece("Muzzle", Vector3.new(2.15, 0.90, 1.25), Vector3.new(0, -0.43, -3.1), palette.light, nil, Enum.PartType.Ball)
        piece("Frill", Vector3.new(3.7, 2.75, 0.42), Vector3.new(0, 0.48, -0.95), palette.dark)
        piece("Tail", Vector3.new(1.05, 1.0, 2.25), Vector3.new(0, -1.05, 2.95), palette.primary, Vector3.new(-8,0,0))
        for _, side in {-1, 1} do
            piece("FrontLeg" .. side, Vector3.new(0.75, 1.45, 0.90), Vector3.new(side * 1.12, -2.15, -1.0), palette.dark)
            piece("RearLeg" .. side, Vector3.new(0.82, 1.55, 0.95), Vector3.new(side * 1.12, -2.15, 1.2), palette.dark)
            piece("FootA" .. side, Vector3.new(0.92, 0.35, 1.15), Vector3.new(side * 1.12, -2.95, -1.18), palette.primary)
            piece("FootB" .. side, Vector3.new(0.92, 0.35, 1.15), Vector3.new(side * 1.12, -2.95, 1.05), palette.primary)
            eye(side, 1.06, 0.33, -2.18)
            piece("BrowHorn" .. side, Vector3.new(0.30, 0.30, 1.55), Vector3.new(side * 0.72, 1.05, -2.62),
                palette.accent, Vector3.new(-26,0,0))
        end
        piece("NoseHorn", Vector3.new(0.28, 0.28, 1.20), Vector3.new(0, 0.32, -3.9), palette.accent, Vector3.new(-14,0,0))
        for _, side in {-1, 1} do
            piece("FrillDot" .. side, Vector3.new(0.35, 0.35, 0.22), Vector3.new(side * 1.25, 0.78, -1.20),
                palette.accent, nil, Enum.PartType.Ball)
        end
    else
        piece("Body", Vector3.new(3.0, 2.2, 3.8), Vector3.new(0, -0.85, 0.35), palette.primary, nil, Enum.PartType.Ball)
        piece("Belly", Vector3.new(2.0, 1.05, 2.75), Vector3.new(0, -1.55, -0.05), palette.light, nil, Enum.PartType.Ball)
        piece("Head", Vector3.new(3.05, 2.05, 2.55), Vector3.new(0, 0.18, -2.1), palette.primary, nil, Enum.PartType.Ball)
        piece("Muzzle", Vector3.new(2.65, 1.05, 1.65), Vector3.new(0, -0.15, -3.55), palette.light, nil, Enum.PartType.Ball)
        piece("Jaw", Vector3.new(2.55, 0.55, 1.65), Vector3.new(0, -0.78, -3.38), palette.dark)
        piece("Tail", Vector3.new(1.15, 1.05, 3.1), Vector3.new(0, -0.82, 3.15), palette.primary, Vector3.new(-10,0,0))
        piece("TailTip", Vector3.new(0.60, 0.60, 2.0), Vector3.new(0, -0.15, 5.35), palette.dark, Vector3.new(-18,0,0))
        for _, side in {-1, 1} do
            piece("Thigh" .. side, Vector3.new(1.0, 1.45, 1.1), Vector3.new(side * 1.05, -1.85, 0.9), palette.dark, nil, Enum.PartType.Ball)
            piece("Leg" .. side, Vector3.new(0.72, 1.35, 0.75), Vector3.new(side * 1.05, -2.70, 0.45), palette.dark)
            piece("Foot" .. side, Vector3.new(1.0, 0.35, 1.55), Vector3.new(side * 1.05, -3.28, -0.05), palette.primary)
            piece("TinyArm" .. side, Vector3.new(0.30, 0.34, 0.72), Vector3.new(side * 1.35, -0.66, -1.30), palette.primary, Vector3.new(24,0,side*8))
            eye(side, 1.24, 0.63, -2.42)
        end
        for i = 1, 3 do
            piece("NeckRidge" .. i, Vector3.new(0.34, 0.65, 0.50),
                Vector3.new(0, 0.82, -0.55 + (i - 1) * 0.72), palette.accent, Vector3.new(0,0,45))
        end
    end

    if gold then
        piece("GoldBadge", Vector3.new(0.52, 0.52, 0.52), Vector3.new(0, 1.45, 0.15),
            GOLD_PALETTE.accent, Vector3.zero, Enum.PartType.Ball)
    end

    character:SetAttribute("SpeciesId", speciesId)
    character:SetAttribute("GoldVisual", gold)
    character:SetAttribute("VisualScale", scale)
end

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
    local score = (if typeof(current) == "number" then current else 0) + points
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
    humanoid.JumpPower = 0
    humanoid.AutoJumpEnabled = false
    humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, false)

    Dinosaur.refreshForPlayer(character, player)
    character:SetAttribute("DinoAttached", true)
end

return Dinosaur
