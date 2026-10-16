--!strict
-- Small circular class badge (Ground / Flyer / Water / Armored), owner 2026-10-16. One component for the hatch reveal card and,
-- later, the dino picker and index. The final art is 4 owner-made icons in AssetSlots.Images (class_ground, class_flyer,
-- class_water, class_armored). Until a slot is bound, a clean PLACEHOLDER draws instead: a circle in the class colour (ClassInfo.Colors,
-- docs/114 5.11) with a 1-letter label. PLACEHOLDER: remove the fallback branch only when all 4 icons are bound.
local ClassInfo = require(script.Parent.ClassInfo)
local AssetSlots = require(script.Parent.AssetSlots)
local ClassBadge = {}
ClassBadge.PlaceholderRing = Color3.fromRGB(235, 238, 245)

-- Pure: what to draw for a species. image = "rbxassetid://N" when the owner icon is bound, else nil (placeholder + letter).
function ClassBadge.spec(speciesId: any): { class: string, label: string, letter: string, color: Color3, image: string?, placeholder: boolean }
    local info = ClassInfo.forSpecies(speciesId)
    local image = AssetSlots.image(ClassInfo.IconSlots[info.class])
    return { class = info.class, label = info.label, letter = ClassInfo.Letters[info.class], color = ClassInfo.Colors[info.class], image = image, placeholder = image == nil }
end

-- Builds a circle `size` px wide inside `parent`; the caller positions it. Returns the root Frame (Name "ClassBadge").
function ClassBadge.create(parent: Instance, speciesId: any, size: number): Frame
    local spec = ClassBadge.spec(speciesId)
    local root = Instance.new("Frame")
    root.Name, root.BorderSizePixel = "ClassBadge", 0
    root.Size = UDim2.fromOffset(size, size)
    root:SetAttribute("Class", spec.class)
    root:SetAttribute("Placeholder", spec.placeholder)
    local round = Instance.new("UICorner")
    round.CornerRadius = UDim.new(.5, 0)
    round.Parent = root
    if spec.image then
        root.BackgroundTransparency = 1
        local icon = Instance.new("ImageLabel")
        icon.Name, icon.BackgroundTransparency, icon.Size, icon.Image = "Icon", 1, UDim2.fromScale(1, 1), spec.image
        icon.ScaleType = Enum.ScaleType.Fit
        icon.Parent = root
    else
        root.BackgroundColor3 = ClassInfo.Colors[spec.class]
        local ring = Instance.new("UIStroke")
        ring.Color, ring.Thickness, ring.Parent = ClassBadge.PlaceholderRing, 2, root
        local letter = Instance.new("TextLabel")
        letter.Name, letter.BackgroundTransparency, letter.Size = "PlaceholderLetter", 1, UDim2.fromScale(1, 1)
        letter.Text, letter.TextColor3, letter.Font, letter.TextScaled = spec.letter, Color3.new(1, 1, 1), Enum.Font.FredokaOne, true
        letter.Parent = root
    end
    root.Parent = parent
    return root
end
return ClassBadge
