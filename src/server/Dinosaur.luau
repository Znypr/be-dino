--!strict
-- Cosmetic shell over Roblox's standard controller. Collider does NOT scale.
local Dinosaur = {}
local RunService = game:GetService("RunService")

local PALETTES = {
    compy = {
        primary = Color3.fromRGB(100, 178, 117),
        light = Color3.fromRGB(201, 221, 154),
        dark = Color3.fromRGB(63, 112, 80),
    },
    triceratops = {
        primary = Color3.fromRGB(104, 151, 190),
        light = Color3.fromRGB(188, 218, 226),
        dark = Color3.fromRGB(62, 96, 132),
    },
    tyrannosaurus = {
        primary = Color3.fromRGB(190, 126, 78),
        light = Color3.fromRGB(232, 190, 132),
        dark = Color3.fromRGB(121, 75, 53),
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

function Dinosaur.render(character: Model, scale: number, requestedSpeciesId: string?)
    local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not root or not humanoid then return end

    local speciesId = normalizedSpecies(requestedSpeciesId or character:GetAttribute("SpeciesId"))
    local palette = PALETTES[speciesId]
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
    local shift = Vector3.new(0, 3 * scale - groundHeight, 0)

    local function piece(name: string, size: Vector3, position: Vector3, color: Color3, tilt: number?)
        local part = Instance.new("Part")
        part.Name = name
        part.Size = size * scale
        part.Color = color
        part.Material = Enum.Material.SmoothPlastic
        part.CanCollide = false
        part.CanTouch = false
        part.CanQuery = false
        part.Massless = true
        part.CastShadow = true
        local offset = CFrame.new(position * scale + shift) * CFrame.Angles(tilt or 0, 0, 0)
        part.CFrame = root.CFrame * offset
        part.Parent = visual
        local weld = Instance.new("Weld")
        weld.Name = "VisualWeld"
        weld.Part0 = root
        weld.Part1 = part
        weld.C0 = offset
        weld.Parent = part
    end

    local bodySize = Vector3.new(2.4, 1.8, 3.2)
    local headSize = Vector3.new(2.3, 1.65, 2.1)
    local snoutSize = Vector3.new(2.05, 0.75, 1.2)
    if speciesId == "triceratops" then
        bodySize = Vector3.new(3.0, 1.75, 3.5)
        headSize = Vector3.new(2.7, 1.6, 2.0)
        snoutSize = Vector3.new(2.35, 0.72, 1.05)
    elseif speciesId == "tyrannosaurus" then
        bodySize = Vector3.new(2.7, 2.0, 3.5)
        headSize = Vector3.new(2.75, 1.9, 2.4)
        snoutSize = Vector3.new(2.45, 0.9, 1.45)
    end

    piece("Body", bodySize, Vector3.new(0, -0.8, 0.2), palette.primary)
    piece("Belly", Vector3.new(1.8, 0.35, 2.6), Vector3.new(0, -1.75, 0), palette.light)
    piece("Head", headSize, Vector3.new(0, 0.3, -1.7), palette.primary)
    piece("Snout", snoutSize, Vector3.new(0, -0.1, -3), palette.light)
    piece("Tail", Vector3.new(1.25, 1.0, 2.6), Vector3.new(0, -0.65, 2.7), palette.primary, math.rad(-12))
    piece("TailTip", Vector3.new(0.65, 0.65, 1.8), Vector3.new(0, -0.15, 4.55), palette.dark, math.rad(-18))

    for _, side in {-1, 1} do
        piece("Leg" .. side, Vector3.new(0.85, 1.4, 1.0), Vector3.new(side * 0.95, -2.1, 0.5), palette.dark)
        piece("Foot" .. side, Vector3.new(1.0, 0.4, 1.6), Vector3.new(side * 0.95, -2.8, 0.1), palette.primary)
        local armSize = if speciesId == "tyrannosaurus" then Vector3.new(0.38, 0.45, 0.72) else Vector3.new(0.5, 0.6, 1.05)
        piece("Arm" .. side, armSize, Vector3.new(side * 1.3, -0.9, -1.1), palette.primary)
        piece("Eye" .. side, Vector3.new(0.13, 0.6, 0.65), Vector3.new(side * 1.18, 0.65, -2), Color3.new(1, 1, 1))
        piece("Pupil" .. side, Vector3.new(0.15, 0.32, 0.3), Vector3.new(side * 1.25, 0.65, -2.12), Color3.fromRGB(25, 35, 31))
    end

    if speciesId == "triceratops" then
        piece("Frill", Vector3.new(3.6, 2.5, 0.45), Vector3.new(0, 0.45, -0.75), palette.dark)
        piece("NoseHorn", Vector3.new(0.28, 0.28, 1.15), Vector3.new(0, 0.45, -3.85), palette.light, math.rad(-18))
        for _, side in {-1, 1} do
            piece("BrowHorn" .. side, Vector3.new(0.32, 0.32, 1.35), Vector3.new(side * 0.72, 1.1, -2.55), palette.light, math.rad(-28))
        end
    elseif speciesId == "tyrannosaurus" then
        piece("Jaw", Vector3.new(2.45, 0.45, 1.5), Vector3.new(0, -0.6, -3.05), palette.dark)
    end

    character:SetAttribute("SpeciesId", speciesId)
    character:SetAttribute("VisualScale", scale)
end

function Dinosaur.setSpecies(character: Model, speciesId: string)
    local scaleValue = character:GetAttribute("VisualScale")
    local scale = if typeof(scaleValue) == "number" then scaleValue else 1
    Dinosaur.render(character, scale, speciesId)
end

function Dinosaur.addGrowth(character: Model, points: number)
    if points <= 0 or character:GetAttribute("RunState") ~= "Active" then return end
    local current = character:GetAttribute("GrowthScore")
    local score = (if typeof(current) == "number" then current else 0) + points
    character:SetAttribute("GrowthScore", score)
    local scale = scaleForScore(score)
    if character:GetAttribute("VisualScale") ~= scale then
        Dinosaur.render(character, scale)
    end
end

function Dinosaur.attach(character: Model, walkSpeed: number, player: Player)
    local deadline = os.clock() + 10
    while not character:IsDescendantOf(workspace) do
        if player.Character ~= character or not player.Parent then return end
        if os.clock() >= deadline then
            warn("[Be Dino] Character never entered Workspace: " .. player.Name)
            return
        end
        RunService.Heartbeat:Wait()
    end
    local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
    local root = character:WaitForChild("HumanoidRootPart", 10) :: BasePart?
    if player.Character ~= character or not character:IsDescendantOf(workspace) then return end
    if not humanoid or not root then
        warn("[Be Dino] Missing Humanoid/root for " .. player.Name)
        return
    end
    if character:GetAttribute("DinoAttached") then return end

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

    local equipped = player:GetAttribute("EquippedSpeciesId")
    Dinosaur.render(character, 1, if typeof(equipped) == "string" then equipped else "compy")
    character:SetAttribute("DinoAttached", true)
    print("[Be Dino] Dinosaur attached: " .. player.Name)
end

return Dinosaur
