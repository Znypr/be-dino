--!strict
-- Class badge (Ground / Fly / Water / Armored), owner 2026-10-16, art from the owner 2026-10-18. One component for the hatch reveal card
-- and any later picker or index. The art is the 4 owner icons bound in AssetSlots.Images (class_ground, class_flyer, class_water,
-- class_armored; docs/77). The letter badge ("G", "W", "F", "A") is gone (owner 2026-10-18: "do not use just 'G' as label ... unintuitive").
-- Missing or malformed asset id: a clean fallback, a small pill in the class colour that holds the class WORD (never a single letter).
local ClassInfo = require(script.Parent.ClassInfo)
local AssetSlots = require(script.Parent.AssetSlots)
local ClassBadge = {}
ClassBadge.PlaceholderRing = Color3.fromRGB(235, 238, 245)

-- Pure: what to draw for a species. image = "rbxassetid://N" when the owner icon is bound, else nil (word pill fallback).
function ClassBadge.spec(speciesId: any): { class: string, label: string, color: Color3, image: string?, placeholder: boolean }
    local info = ClassInfo.forSpecies(speciesId)
    local image = AssetSlots.image(ClassInfo.IconSlots[info.class])
    return { class = info.class, label = info.label, color = ClassInfo.Colors[info.class], image = image, placeholder = image == nil }
end

-- Builds the badge inside `parent`; the caller positions it. `size` is the icon height in px. withLabel = the class word next to the icon
-- (Ground / Fly / Water / Armored); the root then grows to the right with its content (AutomaticSize), so anchor it by its right edge.
-- Returns the root Frame (Name "ClassBadge").
function ClassBadge.create(parent: Instance, speciesId: any, size: number, withLabel: boolean?): Frame
    local spec = ClassBadge.spec(speciesId)
    local root = Instance.new("Frame")
    root.Name, root.BorderSizePixel, root.BackgroundTransparency = "ClassBadge", 0, 1
    root.Size = UDim2.fromOffset(size, size)
    root:SetAttribute("Class", spec.class)
    root:SetAttribute("Placeholder", spec.placeholder)
    if spec.image then
        local icon = Instance.new("ImageLabel")
        icon.Name, icon.BackgroundTransparency, icon.Size, icon.Image = "Icon", 1, UDim2.fromOffset(size, size), spec.image
        icon.ScaleType = Enum.ScaleType.Fit
        icon.Parent = root
    end
    if withLabel or not spec.image then
        local layout = Instance.new("UIListLayout")
        layout.FillDirection, layout.VerticalAlignment, layout.Padding = Enum.FillDirection.Horizontal, Enum.VerticalAlignment.Center, UDim.new(0, 6)
        layout.SortOrder = Enum.SortOrder.LayoutOrder
        layout.Parent = root
        root.AutomaticSize = Enum.AutomaticSize.X
        local word = Instance.new("TextLabel")
        word.Name, word.LayoutOrder, word.Text = "ClassWord", 2, spec.label
        word.Font, word.TextSize, word.TextColor3 = Enum.Font.FredokaOne, math.max(14, math.floor(size * .5)), Color3.new(1, 1, 1)
        word.AutomaticSize, word.Size = Enum.AutomaticSize.X, UDim2.fromOffset(0, size)
        word.TextXAlignment = Enum.TextXAlignment.Left
        if spec.image then
            word.BackgroundTransparency = 1
            word.TextStrokeColor3, word.TextStrokeTransparency = Color3.new(0, 0, 0), .35
        else
            -- fallback: the word on a pill in the class colour (no art bound)
            word.Size = UDim2.fromOffset(0, math.floor(size * .8))
            word.BackgroundColor3, word.BackgroundTransparency = spec.color, 0
            local round = Instance.new("UICorner")
            round.CornerRadius = UDim.new(.5, 0)
            round.Parent = word
            local pad = Instance.new("UIPadding")
            pad.PaddingLeft, pad.PaddingRight = UDim.new(0, 12), UDim.new(0, 12)
            pad.Parent = word
            local ring = Instance.new("UIStroke")
            ring.Color, ring.Thickness, ring.Parent = ClassBadge.PlaceholderRing, 2, word
        end
        word.Parent = root
        if spec.image then
            local icon = root:FindFirstChild("Icon")
            if icon then (icon :: ImageLabel).LayoutOrder = 1 end
        end
    end
    root.Parent = parent
    return root
end
return ClassBadge
