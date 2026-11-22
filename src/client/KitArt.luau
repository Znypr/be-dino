--!strict
-- BD-1287 (docs/246): the small parts every shop menu kit piece builds from (KitWindow, KitCard, KitButton, KitStrip, KitRail): an empty
-- box, an uploaded picture, the kit outlined words, a tap area, a 9-sliced kit 1 picture (the fallback look) and a STUDDED kit 2 piece
-- (Shared/ShopKit2: the picture 9-sliced for its outline, the inside covered by a tile of one stud period, so the studs never stretch).
-- Code only places, slices and tiles uploaded pictures; it draws none of them (docs/72).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Kit2 = require(Shared.ShopKit2)

local A = {}

local INK = Color3.fromRGB(Kit2.Ink[1], Kit2.Ink[2], Kit2.Ink[3])
A.Ink = INK

function A.box(parent: Instance, name: string, x: number, y: number, w: number, h: number, z: number): Frame
    local f = Instance.new("Frame")
    f.Name, f.BackgroundTransparency, f.BorderSizePixel = name, 1, 0
    f.Position, f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    return f
end

-- An uploaded picture drawn whole (Fit) in a w x h box; crop = the part of the picture to show ({x, y, w, h} in picture px).
function A.picture(parent: Instance, name: string, id: string, x: number, y: number, w: number, h: number, z: number, crop: {x: number, y: number, w: number, h: number}?): ImageLabel
    local img = Instance.new("ImageLabel")
    img.Name, img.BackgroundTransparency, img.BorderSizePixel, img.Image, img.ScaleType = name, 1, 0, id, Enum.ScaleType.Fit
    if crop then img.ImageRectOffset, img.ImageRectSize = Vector2.new(crop.x, crop.y), Vector2.new(crop.w, crop.h) end
    img.Position, img.Size, img.ZIndex, img.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    return img
end

-- A kit 1 (Toybox) picture, whole (Fit) or 9-sliced by its kit slice rect. nil while the slot is not bound.
function A.kit(parent: Instance, name: string, slot: string, x: number, y: number, w: number, h: number, z: number): ImageLabel?
    local id = Kit.image(Slots.Images, slot)
    if not id then return nil end
    local img = A.picture(parent, name, id, x, y, w, h, z)
    local asset = Kit.Assets[slot]
    if asset and asset.slice then
        local s = asset.slice
        img.ScaleType, img.SliceCenter, img.SliceScale = Enum.ScaleType.Slice, Rect.new(s[1], s[2], s[3], s[4]), Kit.sliceScale(slot, w, h)
    end
    return img
end

-- One part of a picture (crop) repeated over a w x h box at tileW x tileH each, clipped to the box. Roblox draws ScaleType.Tile with the
-- WHOLE picture (it ignores ImageRectOffset / Size), so a cropped tile is laid out as a grid of cropped pictures instead.
function A.tiled(parent: Instance, name: string, id: string, x: number, y: number, w: number, h: number, z: number, crop: {x: number, y: number, w: number, h: number}, tileW: number, tileH: number): Frame
    local box = A.box(parent, name, x, y, w, h, z)
    box.ClipsDescendants = true
    local tw, th = math.max(4, math.floor(tileW + 0.5)), math.max(4, math.floor(tileH + 0.5))
    for row = 0, math.ceil(h / th) - 1 do
        for col = 0, math.ceil(w / tw) - 1 do
            local img = A.picture(box, "Tile", id, col * tw, row * th, tw, th, z, crop)
            img.ScaleType = Enum.ScaleType.Stretch
        end
    end
    return box
end

-- A studded kit 2 piece (card, button, effect strip) at any size: capScale = picture px -> screen px of the outline, studScale = of the
-- studs. nil while the slot is not bound (the caller then draws the kit 1 piece).
function A.studded(parent: Instance, name: string, slot: string, x: number, y: number, w: number, h: number, z: number, capScale: number, studScale: number): Frame?
    local id = Kit2.image(Slots.Images, slot)
    local d = Kit2.Studded[slot]
    if not id or not d then return nil end
    local holder = A.box(parent, name, x, y, w, h, z)
    local s, i, c = d.slice, d.inner, d.crop
    local k = math.max(0.05, math.min(capScale, w / (d.w - (s[3] - s[1])), h / (d.h - (s[4] - s[2]))))
    local edge = A.picture(holder, "Edge", id, 0, 0, w, h, z)
    edge.ScaleType, edge.SliceCenter, edge.SliceScale = Enum.ScaleType.Slice, Rect.new(s[1], s[2], s[3], s[4]), k
    local l, t, r, b = math.floor(i.l * k), math.floor(i.t * k), math.floor(i.r * k), math.floor(i.b * k)
    A.tiled(holder, "Studs", id, l, t, math.max(0, w - l - r), math.max(0, h - t - b), z, c, c.w * studScale, c.h * studScale)
    return holder
end

-- Kit words: heavy FredokaOne, the kit outline and a dark copy under it (the kit title drop). With `plain` the main words are RichText (a
-- coloured part) and the drop shows the same words without tags.
function A.words(parent: Instance, name: string, text: string, x: number, y: number, w: number, h: number, size: number, z: number, color: Color3?, plain: string?): TextLabel
    local function one(n: string, dy: number, c: Color3, zz: number, t: string, rich: boolean): TextLabel
        local label = Instance.new("TextLabel")
        label.Name, label.Text, label.RichText, label.BackgroundTransparency, label.Font, label.TextSize = n, t, rich, 1, Enum.Font.FredokaOne, size
        label.TextColor3, label.TextWrapped = c, false
        label.Position, label.Size, label.ZIndex, label.Parent = UDim2.fromOffset(x, y + dy), UDim2.fromOffset(w, h), zz, parent
        local s = Instance.new("UIStroke")
        s.Color, s.Thickness, s.LineJoinMode, s.ApplyStrokeMode, s.Parent = INK, Kit.stroke(size), Enum.LineJoinMode.Round, Enum.ApplyStrokeMode.Contextual, label
        return label
    end
    local drop = one(name .. "Drop", Kit.DropPixels, INK, z, plain or text, false)
    local main = one(name, 0, color or Color3.new(1, 1, 1), z + 1, text, plain ~= nil)
    main:GetPropertyChangedSignal("TextXAlignment"):Connect(function() drop.TextXAlignment = main.TextXAlignment end)
    return main
end

function A.tap(parent: Instance, name: string, x: number, y: number, w: number, h: number, z: number, fn: () -> ()): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.BackgroundTransparency, b.AutoButtonColor = name, "", 1, false
    b.Position, b.Size, b.ZIndex, b.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    b.Activated:Connect(fn)
    return b
end

return A
