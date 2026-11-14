--!strict
-- BD-1177 (docs/228 board 1, docs/230): the "Toybox" skin. It places and slices the kit pictures (Blender renders, ids in
-- AssetSlots.Images) on what the game already builds: the menu window (stud body, frame, glossy header in the colour of the place, red
-- gloss X) and every button made by Theme.decorate (two-tone gloss). It draws nothing itself (docs/72).
-- UITheme requires this file only while Config.ToyboxUIEnabled is true (default false, on only in the playtest profile) and offers it as
-- Theme.Toybox; with the flag off this file is never loaded and every window and button is built exactly as before.
-- A group of pictures whose ids are not all bound (Kit.ready) is skipped: that part keeps today's look. Numbers and rules: Shared/ToyboxKit
-- (pure, tested offline by tools/verify_toybox_ui.py).
local Kit = require(script.Parent.ToyboxKit)
local Slots = require(script.Parent.AssetSlots)

local Skin = {}
Skin.Kit = Kit

local OUTLINE = Color3.fromRGB(Kit.Outline[1], Kit.Outline[2], Kit.Outline[3])
local TEXT_PROPERTIES = {"Text", "Font", "TextXAlignment", "TextYAlignment", "TextWrapped", "TextScaled", "RichText", "TextTruncate", "LineHeight"}

local function id(slot: string): string?
    return Kit.image(Slots.Images, slot)
end
local function ready(group: string): boolean
    return Kit.ready(Slots.Images, group)
end
-- The size a box is laid out at, before any UIScale: its offsets when it is sized in px, else what is on screen now.
local function designSize(object: GuiObject): (number, number)
    local size = object.Size
    if size.X.Scale == 0 and size.Y.Scale == 0 then return size.X.Offset, size.Y.Offset end
    return object.AbsoluteSize.X, object.AbsoluteSize.Y
end
local function picture(parent: GuiObject, name: string, slot: string, z: number): ImageLabel
    local image = Instance.new("ImageLabel")
    image.Name, image.BackgroundTransparency, image.BorderSizePixel = name, 1, 0
    image.Size, image.ZIndex, image.Image = UDim2.fromScale(1, 1), z, id(slot) or ""
    image:SetAttribute("ToyboxSlot", slot)
    image.Parent = parent
    return image
end
-- 9-slice a picture to its box. The rect comes from the kit; the scale follows the box (a header never stretches up or down).
local function slice(image: ImageLabel, slot: string, box: GuiObject)
    local rect = Kit.Assets[slot].slice :: {number}
    image.ScaleType = Enum.ScaleType.Slice
    image.SliceCenter = Rect.new(rect[1], rect[2], rect[3], rect[4])
    local function fit()
        local width, height = designSize(box)
        image.SliceScale = Kit.sliceScale(slot, width, height)
    end
    fit()
    box:GetPropertyChangedSignal("Size"):Connect(fit)
    box:GetPropertyChangedSignal("AbsoluteSize"):Connect(fit)
end
local function outline(label: TextLabel): UIStroke
    local stroke = Instance.new("UIStroke")
    stroke.LineJoinMode, stroke.Color, stroke.Thickness = Enum.LineJoinMode.Round, OUTLINE, Kit.stroke(label.TextSize)
    stroke.Parent = label
    return stroke
end
local function hideOld(box: GuiObject)
    local studs = box:FindFirstChild("FossilTexture") -- the old code-built stud dots (Theme.texture)
    if studs and studs:IsA("GuiObject") then studs.Visible = false end
    for _, child in box:GetChildren() do
        if child:IsA("UIStroke") then child.Enabled = false end -- the picture carries its own black edge
    end
    box.BackgroundTransparency = 1
end
local function copyTextLimit(from: Instance, to: {TextLabel})
    if not from:IsA("UITextSizeConstraint") then return end
    for _, label in to do
        local limit = Instance.new("UITextSizeConstraint")
        limit.MinTextSize, limit.MaxTextSize = math.max(from.MinTextSize, 1), from.MaxTextSize
        limit.Parent = label
    end
end

-- The drop of a word: a dark copy 3 px under it, behind it. It follows the word (text, size, place, visibility).
function Skin.drop(label: TextLabel): TextLabel
    local shadow = Instance.new("TextLabel")
    shadow.Name, shadow.BackgroundTransparency, shadow.TextColor3 = "ToyboxDrop", 1, OUTLINE
    shadow.ZIndex = label.ZIndex - 1
    local stroke = outline(shadow)
    local function follow()
        for _, property in TEXT_PROPERTIES do (shadow :: any)[property] = (label :: any)[property] end
        shadow.TextSize = Kit.textSize(label.TextSize)
        shadow.Size, shadow.AnchorPoint, shadow.Rotation, shadow.Visible = label.Size, label.AnchorPoint, label.Rotation, label.Visible
        shadow.Position = label.Position + UDim2.fromOffset(0, Kit.DropPixels)
        shadow.TextTransparency, stroke.Transparency = label.TextTransparency, label.TextTransparency
        stroke.Thickness = Kit.stroke(shadow.TextSize)
    end
    follow()
    for _, property in TEXT_PROPERTIES do label:GetPropertyChangedSignal(property):Connect(follow) end
    for _, property in {"TextSize", "Size", "Position", "AnchorPoint", "Rotation", "Visible", "TextTransparency"} do
        label:GetPropertyChangedSignal(property):Connect(follow)
    end
    for _, child in label:GetChildren() do copyTextLimit(child, {shadow}) end
    shadow.Parent = label.Parent
    return shadow
end

type Face = {image: ImageLabel, word: TextLabel, drop: TextLabel, close: boolean}
local faces: {[TextButton]: Face} = setmetatable({}, {__mode = "k"}) :: any

-- A TextButton draws its own word under its children, so the word moves to a label above the gloss picture ("ToyboxText", with its dark
-- copy "ToyboxTextDrop") and follows the button's Text, size, colour and dimming. The button stays the thing that is pressed.
local function build(button: TextButton, border: UIStroke?): Face
    local function rgb(): (number, number, number)
        local c = button.BackgroundColor3
        return math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5)
    end
    local slot = Kit.buttonSlot(rgb())
    local image = picture(button, "ToyboxFace", slot, -3)
    slice(image, slot, button)
    local word = Instance.new("TextLabel")
    word.Name, word.BackgroundTransparency, word.Size, word.ZIndex = "ToyboxText", 1, UDim2.fromScale(1, 1), -1
    local wordStroke = outline(word)
    local drop = Instance.new("TextLabel")
    drop.Name, drop.BackgroundTransparency, drop.Size, drop.ZIndex = "ToyboxTextDrop", 1, UDim2.fromScale(1, 1), -2
    drop.Position, drop.TextColor3 = UDim2.fromOffset(0, Kit.DropPixels), OUTLINE
    local dropStroke = outline(drop)
    local face: Face = {image = image, word = word, drop = drop, close = false}
    local function text()
        for _, property in TEXT_PROPERTIES do
            (word :: any)[property] = (button :: any)[property];
            (drop :: any)[property] = (button :: any)[property]
        end
        local size = Kit.textSize(button.TextSize)
        word.TextSize, drop.TextSize, word.TextColor3 = size, size, button.TextColor3
        wordStroke.Thickness, dropStroke.Thickness = Kit.stroke(size), Kit.stroke(size)
    end
    text()
    for _, property in TEXT_PROPERTIES do button:GetPropertyChangedSignal(property):Connect(text) end
    button:GetPropertyChangedSignal("TextSize"):Connect(text)
    button:GetPropertyChangedSignal("TextColor3"):Connect(text)
    -- Dimming: a screen that dims the button's word (TextTransparency .25) dims the label; the button's own word stays hidden.
    local function dim()
        local value = button.TextTransparency
        if value == 1 then return end
        word.TextTransparency, drop.TextTransparency, wordStroke.Transparency, dropStroke.Transparency = value, value, value, value
        button.TextTransparency = 1
    end
    dim()
    button:GetPropertyChangedSignal("TextTransparency"):Connect(dim)
    local function noThinStroke() if button.TextStrokeTransparency ~= 1 then button.TextStrokeTransparency = 1 end end
    noThinStroke()
    button:GetPropertyChangedSignal("TextStrokeTransparency"):Connect(noThinStroke)
    -- The flat colour becomes the nearest gloss button; a later colour change (a disabled or selected state) swaps the picture.
    local function fade()
        local value = button.BackgroundTransparency
        if value == 1 then return end
        image.ImageTransparency = value
        button.BackgroundTransparency = 1
    end
    fade()
    button:GetPropertyChangedSignal("BackgroundTransparency"):Connect(fade)
    button:GetPropertyChangedSignal("BackgroundColor3"):Connect(function()
        if face.close then return end
        local nextSlot = Kit.buttonSlot(rgb())
        image.Image = id(nextSlot) or image.Image
        image:SetAttribute("ToyboxSlot", nextSlot)
    end)
    if border then border.Enabled = false end -- the picture carries its own black edge and drop
    -- What the screen puts on the button: a text size limit is copied to the label, a padding must not shrink the picture.
    local function child(added: Instance)
        copyTextLimit(added, {word, drop})
        if added:IsA("UIPadding") and not face.close then
            local left, right, top, bottom = added.PaddingLeft.Offset, added.PaddingRight.Offset, added.PaddingTop.Offset, added.PaddingBottom.Offset
            image.Position, image.Size = UDim2.fromOffset(-left, -top), UDim2.new(1, left + right, 1, top + bottom)
        end
    end
    for _, existing in button:GetChildren() do child(existing) end
    button.ChildAdded:Connect(child)
    drop.Parent, word.Parent = button, button
    faces[button] = face
    return face
end

-- Called by Theme.decorate for every TextButton (flag on). Nothing happens while the seven button ids are not all bound, or for a
-- button that is an invisible touch area.
function Skin.button(button: TextButton, border: UIStroke?)
    if faces[button] or not ready("button") then return end
    if button.BackgroundTransparency >= 1 then return end
    build(button, border)
end

-- The red gloss X: the close picture drawn whole as a square at the right of the button, at least 48 px on screen.
function Skin.close(button: TextButton, scale: UIScale?)
    local closeId = id("toybox_close")
    if not closeId then return end
    local face = faces[button] or build(button, button:FindFirstChildOfClass("UIStroke"))
    face.close = true
    face.word.Visible, face.drop.Visible = false, false -- the X is in the picture
    local image = face.image
    image.ScaleType, image.Image = Enum.ScaleType.Fit, closeId
    image:SetAttribute("ToyboxSlot", "toybox_close")
    image.AnchorPoint, image.Position = Vector2.new(1, 0.5), UDim2.new(1, 0, 0.5, 0)
    local function size()
        local side = Kit.closeSide(button.AbsoluteSize.X, button.AbsoluteSize.Y, if scale then scale.Scale else 1)
        image.Size = UDim2.fromOffset(side, side)
    end
    size()
    button:GetPropertyChangedSignal("AbsoluteSize"):Connect(size)
    if scale then scale:GetPropertyChangedSignal("Scale"):Connect(size) end
end

type Window = {panel: GuiObject, header: GuiObject, heading: TextLabel?, closeButton: TextButton?, scale: UIScale?, place: string?}
local mainHeader: ImageLabel? = nil -- the header strip of the menu window: Skin.place(screen) recolours it

-- Skins a window: stud body in a frame, glossy header, title drop, red gloss X. `place` fixes the header colour (the Fusion Menu);
-- without it the window is the menu window and follows Skin.place(screen).
function Skin.window(window: Window)
    if ready("panel") then
        local panel = window.panel
        hideOld(panel)
        local frame = picture(panel, "ToyboxFrame", "toybox_panel_frame", -3)
        slice(frame, "toybox_panel_frame", panel)
        local studs = picture(panel, "ToyboxStuds", "toybox_studs_tile", -2)
        local inset = Kit.StudInset
        studs.ScaleType, studs.TileSize = Enum.ScaleType.Tile, UDim2.fromOffset(Kit.StudTile, Kit.StudTile)
        studs.Position, studs.Size = UDim2.fromOffset(inset.left, inset.top), UDim2.new(1, -(inset.left + inset.right), 1, -(inset.top + inset.bottom))
        local round = Instance.new("UICorner")
        round.CornerRadius, round.Parent = UDim.new(0, Kit.StudCorner), studs
    end
    if ready("header") then
        local header = window.header
        hideOld(header)
        local slot = if window.place then Kit.placeSlot(window.place) else Kit.headerSlot(nil)
        local strip = picture(header, "ToyboxHeader", slot, -2)
        slice(strip, slot, header)
        if window.place == nil then mainHeader = strip end
        if window.heading then Skin.drop(window.heading) end
    end
    if window.closeButton then Skin.close(window.closeButton, window.scale) end
end

-- The menu window shows another screen: its header takes the colour of the screen's place.
function Skin.place(screen: string)
    local image = mainHeader
    if not image then return end
    local slot = Kit.headerSlot(screen)
    image.Image = id(slot) or image.Image
    image:SetAttribute("ToyboxSlot", slot)
end

-- The dino detail page: its header takes the colour of the dino's rarity (owner 2026-11-14, C-58), not the blue of the Dinos place.
function Skin.rarity(tier: number)
    local image = mainHeader
    if not image then return end
    local slot = Kit.raritySlot(tier)
    image.Image = id(slot) or image.Image
    image:SetAttribute("ToyboxSlot", slot)
end

return Skin
