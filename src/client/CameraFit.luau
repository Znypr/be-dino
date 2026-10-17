--!strict
-- BD-500 / BD-471: the client half of Shared/CameraFraming. Measures the REAL model box of the local dinosaur so the default camera
-- (minimum zoom, aim lift) frames its actual size instead of only its growth step. The pure numbers live in CameraFraming.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local CameraFraming = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("CameraFraming"))

local CameraFit = {}

-- Box height and length at scale 1 per LocalMeshVisual instance (a species or skin change builds a new instance). Measured once, in the
-- root's frame so it does not depend on which way the dino faces, and divided by the scale the model was drawn at; growth then
-- multiplies it by VisualScale, so there is no per-frame measuring and no jitter from the walk animation.
local baseSize = setmetatable({}, {__mode = "k"}) :: {[Instance]: {number}}

local function measure(visual: Model, root: BasePart): {number}?
    local inverse = root.CFrame:Inverse()
    local lowY, highY, lowZ, highZ = math.huge, -math.huge, math.huge, -math.huge
    for _, part in visual:GetDescendants() do
        if part:IsA("BasePart") and part.Transparency < 1 then
            local half = part.Size / 2
            for _, sx in {-1, 1} do
                for _, sy in {-1, 1} do
                    for _, sz in {-1, 1} do
                        local local_ = inverse:PointToWorldSpace(part.CFrame:PointToWorldSpace(Vector3.new(half.X * sx, half.Y * sy, half.Z * sz)))
                        lowY, highY = math.min(lowY, local_.Y), math.max(highY, local_.Y)
                        lowZ, highZ = math.min(lowZ, local_.Z), math.max(highZ, local_.Z)
                    end
                end
            end
        end
    end
    local drawn = visual:GetAttribute("Scale")
    if typeof(drawn) ~= "number" or drawn <= 0 or highY <= lowY or highZ <= lowZ then return nil end
    return {(highY - lowY) / drawn, (highZ - lowZ) / drawn}
end

-- Height and length of the character's dinosaur at its current VisualScale, or nil while there is no local model yet
-- (the caller then keeps the old growth-only framing).
function CameraFit.box(character: Model): (number?, number?)
    local visual = character:FindFirstChild("LocalMeshVisual")
    local root = character:FindFirstChild("HumanoidRootPart")
    if not visual or not visual:IsA("Model") or not root or not root:IsA("BasePart") then return nil, nil end
    local base = baseSize[visual]
    if not base then
        base = measure(visual, root)
        if not base then return nil, nil end
        baseSize[visual] = base
    end
    local scale = character:GetAttribute("VisualScale")
    if typeof(scale) ~= "number" or scale <= 0 then scale = 1 end
    return base[1] * scale, base[2] * scale
end

function CameraFit.minZoom(base: number, character: Model): number
    local scale = character:GetAttribute("VisualScale")
    local height, length = CameraFit.box(character)
    return CameraFraming.minZoom(base, if typeof(scale) == "number" then scale else 1, height, length)
end

function CameraFit.lift(character: Model): number
    local height = CameraFit.box(character)
    if height then return CameraFraming.lift(height) end
    local scale = character:GetAttribute("VisualScale")
    return 2 * ((if typeof(scale) == "number" then scale else 1) - 1) -- no local model yet: the old growth-only lift
end

return CameraFit
