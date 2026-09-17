--!strict
-- Cosmetic shell over Roblox's standard controller. Collider does NOT scale.
local Dinosaur = {}
local RunService = game:GetService("RunService")
local GREEN = Color3.fromRGB(100, 178, 117)
local LIGHT = Color3.fromRGB(201, 221, 154)
local DARK = Color3.fromRGB(63, 112, 80)

local function scaleForScore(score: number): number
    return math.min(4, math.sqrt(1 + math.max(0, score) / 50))
end

function Dinosaur.render(character: Model, scale: number)
    local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not root or not humanoid then return end
    local old = character:FindFirstChild("DinoVisual")
    if old then old:Destroy() end
    local visual = Instance.new("Model")
    visual.Name = "DinoVisual"
    visual.Parent = character

    -- Match cosmetic feet to the standard R6/R15 ground height.
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
    piece("Body", Vector3.new(2.4, 1.8, 3.2), Vector3.new(0, -0.8, 0.2), GREEN)
    piece("Belly", Vector3.new(1.8, 0.35, 2.6), Vector3.new(0, -1.75, 0), LIGHT)
    piece("Head", Vector3.new(2.3, 1.65, 2.1), Vector3.new(0, 0.3, -1.7), GREEN)
    piece("Snout", Vector3.new(2.05, 0.75, 1.2), Vector3.new(0, -0.1, -3), LIGHT)
    piece("Tail", Vector3.new(1.25, 1.0, 2.6), Vector3.new(0, -0.65, 2.7), GREEN, math.rad(-12))
    piece("TailTip", Vector3.new(0.65, 0.65, 1.8), Vector3.new(0, -0.15, 4.55), DARK, math.rad(-18))
    for _, side in {-1, 1} do
        piece("Leg" .. side, Vector3.new(0.85, 1.4, 1.0), Vector3.new(side * 0.95, -2.1, 0.5), DARK)
        piece("Foot" .. side, Vector3.new(1.0, 0.4, 1.6), Vector3.new(side * 0.95, -2.8, 0.1), GREEN)
        piece("Arm" .. side, Vector3.new(0.5, 0.6, 1.05), Vector3.new(side * 1.3, -0.9, -1.1), GREEN)
        piece("Eye" .. side, Vector3.new(0.13, 0.6, 0.65), Vector3.new(side * 1.18, 0.65, -2), Color3.new(1, 1, 1))
        piece("Pupil" .. side, Vector3.new(0.15, 0.32, 0.3), Vector3.new(side * 1.25, 0.65, -2.12), Color3.fromRGB(25, 35, 31))
    end
    character:SetAttribute("VisualScale", scale)
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
    -- CharacterAdded can arrive before the model is parented to Workspace.
    -- Do not silently abandon that spawn; also stop if a newer spawn replaces it.
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
    Dinosaur.render(character, 1)
    character:SetAttribute("DinoAttached", true)
    print("[Be Dino] Dinosaur attached: " .. player.Name)
end

return Dinosaur
