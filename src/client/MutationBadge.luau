--!strict
-- BD-352: the readable mutation badge for Index cards, species page and My dinos. A rounded chip in the mutation's OWN
-- colour (MutationLook.badge, rim outline) with the mutation name in dark text, never under MinTextSize px. No new art:
-- a round colour dot plus the word, so the badge is never colour-only. Pure UI, safe to call again (replaces the old chip).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Look = require(Shared.MutationLook)
local Badge = {}
Badge.MinTextSize = 14
Badge.Height = 22
local INK = Color3.fromRGB(26, 28, 38)

-- Chip width for a name at MinTextSize (FredokaOne is about 0.62 em per capital).
function Badge.width(name: string): number
    return math.max(72, math.ceil(#name * Badge.MinTextSize * 0.62) + 26)
end

function Badge.chip(parent: GuiObject, mutationId: any, position: UDim2, anchor: Vector2?): Frame?
    local look = Look.get(mutationId)
    if not look then return nil end
    local old = parent:FindFirstChild("MutationChip")
    if old then old:Destroy() end
    local name = string.upper(look.name)
    local chip = Instance.new("Frame")
    chip.Name, chip.BackgroundColor3, chip.BorderSizePixel = "MutationChip", Look.color(look.badge), 0
    chip.AnchorPoint, chip.Position, chip.Size = anchor or Vector2.zero, position, UDim2.fromOffset(Badge.width(name), Badge.Height)
    chip.ZIndex = parent.ZIndex + 6
    chip:SetAttribute("MutationId", look.id)
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0.5, 0) corner.Parent = chip
    local rim = Instance.new("UIStroke") rim.Color, rim.Thickness, rim.Transparency = Look.color(look.rim), 2, 0.1 rim.Parent = chip
    local dot = Instance.new("Frame")
    dot.Name, dot.BackgroundColor3, dot.BorderSizePixel = "Dot", Color3.new(1, 1, 1), 0
    dot.AnchorPoint, dot.Position, dot.Size, dot.ZIndex = Vector2.new(0, 0.5), UDim2.new(0, 7, 0.5, 0), UDim2.fromOffset(9, 9), chip.ZIndex + 1
    local dotCorner = Instance.new("UICorner") dotCorner.CornerRadius = UDim.new(0.5, 0) dotCorner.Parent = dot
    dot.Parent = chip
    local text = Instance.new("TextLabel")
    text.Name, text.BackgroundTransparency, text.Text, text.Font = "Name", 1, name, Enum.Font.FredokaOne
    text.TextSize, text.TextColor3, text.ZIndex = Badge.MinTextSize, INK, chip.ZIndex + 1
    text.Position, text.Size = UDim2.fromOffset(19, 0), UDim2.new(1, -23, 1, 0)
    text.TextXAlignment = Enum.TextXAlignment.Left
    text.Parent = chip
    chip.Parent = parent
    return chip
end

return Badge
