--!strict
-- BD-352: the readable mutation badge for Index cards, species page and My dinos. A rounded chip in the mutation's OWN
-- colour (MutationLook.badge, rim outline) with the mutation name in dark text, never under MinTextSize px. No new art:
-- a round colour dot plus the word, so the badge is never colour-only. Pure UI, safe to call again (replaces the old chip).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Look = require(Shared.MutationLook)
local AssetSlots = require(Shared.AssetSlots)
local Chip = require(Shared.ChipStyle)
local Badge = {}
Badge.MinTextSize = 14
Badge.Height = 22
local INK = Color3.fromRGB(26, 28, 38)

-- BD-190: the 128 px icon (AssetSlots.Images.mutation_<id>, a Blender render with its own light rim) replaces the plain dot. While the
-- slot is empty (nothing uploaded yet) this returns nil and every caller keeps the colour dot, so nothing changes until upload.
function Badge.iconImage(mutationId: any): string?
    local look = Look.get(mutationId)
    if not look then return nil end
    return AssetSlots.image("mutation_" .. look.id)
end
Badge.IconSize = 22 -- icon px inside the chip (chip height); the dot stays 9 px

-- Chip width for a name at MinTextSize (FredokaOne is about 0.62 em per capital).
function Badge.width(name: string, withIcon: boolean?): number
    return math.max(72, math.ceil(#name * Badge.MinTextSize * 0.62) + (if withIcon then 34 else 26))
end

function Badge.chip(parent: GuiObject, mutationId: any, position: UDim2, anchor: Vector2?): Frame?
    local look = Look.get(mutationId)
    if not look then return nil end
    local old = parent:FindFirstChild("MutationChip")
    if old then old:Destroy() end
    local name = string.upper(look.name)
    local chip = Instance.new("Frame")
    chip.Name = "MutationChip"
    Chip.apply(chip, Look.color(look.badge), Look.color(look.rim), true) -- BD-1077: the shared small chunky tag; the mutation's own rim colour is its outline
    local image = Badge.iconImage(look.id)
    chip.AnchorPoint, chip.Position, chip.Size = anchor or Vector2.zero, position, UDim2.fromOffset(Badge.width(name, image ~= nil), Badge.Height)
    chip.ZIndex = parent.ZIndex + 6
    chip:SetAttribute("MutationId", look.id)
    local textX = 19
    if image then
        local icon = Instance.new("ImageLabel")
        icon.Name, icon.BackgroundTransparency, icon.BorderSizePixel, icon.Image = "Icon", 1, 0, image
        icon.ScaleType = Enum.ScaleType.Fit
        icon.AnchorPoint, icon.Position, icon.Size, icon.ZIndex = Vector2.new(0, 0.5), UDim2.new(0, 2, 0.5, 0), UDim2.fromOffset(Badge.IconSize, Badge.IconSize), chip.ZIndex + 1
        icon.Parent = chip
        textX = Badge.IconSize + 6
    else
        local dot = Instance.new("Frame")
        dot.Name, dot.BackgroundColor3, dot.BorderSizePixel = "Dot", Color3.new(1, 1, 1), 0
        dot.AnchorPoint, dot.Position, dot.Size, dot.ZIndex = Vector2.new(0, 0.5), UDim2.new(0, 7, 0.5, 0), UDim2.fromOffset(9, 9), chip.ZIndex + 1
        local dotCorner = Instance.new("UICorner") dotCorner.CornerRadius = UDim.new(0.5, 0) dotCorner.Parent = dot
        dot.Parent = chip
    end
    local text = Instance.new("TextLabel")
    text.Name, text.BackgroundTransparency, text.Text, text.Font = "Name", 1, name, Enum.Font.FredokaOne
    text.TextSize, text.TextColor3, text.ZIndex = Badge.MinTextSize, INK, chip.ZIndex + 1
    text.Position, text.Size = UDim2.fromOffset(textX, 0), UDim2.new(1, -(textX + 4), 1, 0)
    text.TextXAlignment = Enum.TextXAlignment.Left
    text.Parent = chip
    chip.Parent = parent
    return chip
end

return Badge
