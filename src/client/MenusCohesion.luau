--!strict
-- BD-1237 (docs/240 order step 4, style tile v3 boards 11 and 12): Egg chances and the Food guide on the style rules R1-R8.
--   Egg chances: one cream panel with an ink outline (no word on the studs, R1/R2), the chances in kid words ("1 in 4", R6) and the exact numbers
--   one tap away on the EXACT % page (trimmed: "36.4%", never "36.4000%"); every button grey (R3: no cyan buttons; the X closes).
--   Food guide: four cream cards, each with the real V3 food mesh (BD-1208, ReplicatedStorage.GeneratedWorld) in a small 3D view instead of the
--   code-drawn leaf (R5), the name and a "+4 grow" chip in ink (R4: no rarity colours as food colours), the footer line in a cream strip.
-- Required only while Config.MenusCohesionEnabled is true (ShopScreens and SmallScreens ask for it). Client presentation only: nothing is stored,
-- sent or decided; the buttons call the same screens the old ones opened. Rects from Shared/MenusCohesionRules (offline-checked).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Layout = require(Shared.ToyboxLayout)
local Rules = require(Shared.MenusCohesionRules)
local Chip = require(Shared.ChipStyle)
local RarityWord = require(Shared.RarityWord)
local ModalCompact = require(script.Parent.ModalCompact)
local Split = require(Shared.ScreensCohesionLayout) -- two cream panels over a button row (the Run complete / Home rule, offline-checked there)
local Screens = require(script.Parent.ScreensCohesion) -- pictureId: a bound picture or nil (R5)
local Kit = Layout.Kit

local M = {}
M.Grey = Color3.fromRGB(128, 142, 158) -- the kit's grey button (R3: every button that is not the one main button)
M.Main = Color3.fromRGB(93, 237, 31) -- the kit's green: only the confirm popups have one (GO HOME, CONFIRM); the odds and food pages have none
local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
local function size(r: Rules.Rect): UDim2 return UDim2.fromOffset(r.w, r.h) end
local function pos(r: Rules.Rect): UDim2 return UDim2.fromOffset(r.x, r.y) end
local function body(): (number, number, number) return ModalCompact.bodyWidth(), ModalCompact.bodyHeight(), ModalCompact.bodyScale() end

-- R8 on a resize: drawn again for the body that is on screen now (the ScreensCohesion pattern); stops once another screen replaced the mark.
local function live(parent: Frame, draw: () -> GuiObject)
    local mark: GuiObject? = draw()
    local signature = ModalCompact.signature()
    local stop: (() -> ())? = nil
    stop = ModalCompact.onLayout(function()
        if not mark or mark.Parent ~= parent then if stop then stop() end return end
        if ModalCompact.signature() == signature then return end
        signature = ModalCompact.signature()
        parent:ClearAllChildren()
        mark = draw()
    end)
end

local function buttons(parent: GuiObject, rects: {Rules.Rect}, list: {{any}})
    for i, b in list do
        Layout.actionButton(parent, b[1], size(rects[i]), pos(rects[i]), if b[3] == true then M.Main else M.Grey, false, b[2]).Name = "Action_" .. b[1]
    end
end

-- A scrolling list inside a cream panel; returns the panel and the list.
local function listPanel(parent: Frame, lay: any): (Frame, ScrollingFrame)
    local panel = Layout.panel(parent, "OddsPanel", size(lay.panel), pos(lay.panel))
    local list = Instance.new("ScrollingFrame")
    list.Name, list.BackgroundTransparency, list.BorderSizePixel = "List", 1, 0
    list.Size, list.Position, list.ZIndex = size(lay.list), pos(lay.list), panel.ZIndex + 1
    list.ScrollBarThickness, list.ScrollBarImageColor3, list.CanvasSize = 6, rgb(Rules.Muted), UDim2.new()
    list.Parent = panel
    return panel, list
end

-- Egg chances in kid words. d: {body, groups, notes, exact = open the exact page, back}. groups: OddsCopy groups ({title, rows = {name, percent}, note}).
function M.chances(d: any)
    live(d.body, function() return M.drawChances(d) end)
end
function M.drawChances(d: any): GuiObject
    local w, h, scale = body()
    local lay = Rules.odds(w, h, scale, 2)
    local panel, list = listPanel(d.body, lay)
    local inner = lay.list.w - 10
    local y = 0
    for gi, group in d.groups do
        Layout.text(list, group.title, UDim2.fromOffset(inner, Rules.GroupH), UDim2.fromOffset(0, y), Kit.Type.heading, "value").Name = "Group_" .. gi
        y += Rules.GroupH
        for ri, row in group.rows do
            Layout.text(list, row.name, UDim2.fromOffset(math.floor(inner * 0.62), Rules.RowH), UDim2.fromOffset(8, y), Kit.Type.body, "label").Name = "Name_" .. gi .. "_" .. ri
            Layout.text(list, Rules.kidChance(row.percent), UDim2.fromOffset(math.floor(inner * 0.36), Rules.RowH), UDim2.fromOffset(inner - math.floor(inner * 0.36), y), Kit.Type.body, "value", Enum.TextXAlignment.Right).Name = "Chance_" .. gi .. "_" .. ri
            y += Rules.RowH
        end
        if group.note then
            local note = Layout.text(list, group.note, UDim2.fromOffset(inner, Rules.NoteLineH * 2), UDim2.fromOffset(0, y), Kit.Type.small, "label")
            note.TextWrapped, note.Name = true, "Note_" .. gi
            y += Rules.NoteLineH * 2
        end
        y += 8
    end
    for i, line in d.notes do
        local note = Layout.text(list, line, UDim2.fromOffset(inner, Rules.NoteLineH * 2), UDim2.fromOffset(0, y), Kit.Type.small, "label")
        note.TextWrapped, note.Name = true, "Tip_" .. i
        y += Rules.NoteLineH * 2
    end
    list.CanvasSize = UDim2.fromOffset(0, y)
    buttons(d.body, lay.buttons, {{"EXACT %", d.exact}, {"BACK", d.back}})
    return panel
end

-- The exact numbers (the long ShopOdds list), trimmed and in ink. d: {body, lines, outcomes, back}.
function M.exact(d: any)
    live(d.body, function() return M.drawExact(d) end)
end
function M.drawExact(d: any): GuiObject
    local w, h, scale = body()
    local lay = Rules.odds(w, h, scale, 2)
    local panel, list = listPanel(d.body, lay)
    local inner = lay.list.w - 10
    local y = 0
    for i, raw in d.lines do
        local line = Rules.trimPercents(raw)
        local heading = string.sub(line, -1) == ":" or i == 1
        local rows = if #line > 70 then 2 else 1
        local label = Layout.text(list, line, UDim2.fromOffset(inner, Rules.RowH * rows), UDim2.fromOffset(if heading then 0 else 8, y), if heading then Kit.Type.heading else Kit.Type.body, if heading then "value" else "label")
        label.TextWrapped, label.Name = true, "Line_" .. i
        if not heading then RarityWord.paintLabel(label) end -- a rarity word keeps its colour (R4: rarity colours on rarity words)
        y += Rules.RowH * rows + (if heading then 6 else 0)
    end
    list.CanvasSize = UDim2.fromOffset(0, y)
    buttons(d.body, lay.buttons, {{"All outcomes", d.outcomes}, {"BACK", d.back}})
    return panel
end

-- A confirm popup (Go home?, Buy Random Egg?, Upgrade Conditions?) on the style rules (style tile v2 board 7): the real picture on a cream panel at
-- the left, the facts as label / value rows and one short line in ink on a cream panel at the right, one green main button, the rest grey
-- (R1, R2, R3: no gold words on the studs, no cyan or red CANCEL). d: {body, picture = a UIIconAssets / AssetSlots slot, title, rows = {{label,
-- value}}, line, buttons = {{text, callback, main}}}. The callbacks are the old screen's own.
function M.confirm(d: any)
    live(d.body, function() return M.drawConfirm(d) end)
end
function M.drawConfirm(d: any): GuiObject
    local w, h, scale = body()
    local lay = Split.split(w, h, scale, 0.34, #d.buttons)
    local left = Layout.panel(d.body, "Picture", size(lay.left), pos(lay.left))
    local id = Screens.pictureId(d.picture)
    if id then
        local pic = math.min(lay.left.w, lay.left.h) - Kit.PanelPad * 2
        local image = Instance.new("ImageLabel")
        image.Name, image.BackgroundTransparency, image.Image, image.ScaleType = "Picture", 1, id, Enum.ScaleType.Fit
        image.Size, image.Position, image.ZIndex = UDim2.fromOffset(pic, pic), UDim2.fromOffset((lay.left.w - pic) // 2, (lay.left.h - pic) // 2), left.ZIndex + 1
        image.Parent = left
    end
    local right = Layout.panel(d.body, "Facts", size(lay.right), pos(lay.right))
    local inner = lay.right.w - Kit.PanelPad * 2
    local top = Kit.PanelPad
    Layout.text(right, d.title, UDim2.fromOffset(inner, 28), UDim2.fromOffset(Kit.PanelPad, top), Kit.Type.heading, "value").Name = "Title"
    top += 36
    for i = 1, Split.rowsThatFit(lay.right.h - 64, top, #d.rows) do
        local row = d.rows[i]
        Layout.text(right, row[1], UDim2.fromOffset(math.floor(inner * 0.55), Split.FactRowH), UDim2.fromOffset(Kit.PanelPad, top), Kit.Type.body, "label").Name = "Label_" .. i
        Layout.text(right, row[2], UDim2.fromOffset(math.floor(inner * 0.45), Split.FactRowH), UDim2.fromOffset(Kit.PanelPad + math.floor(inner * 0.55), top), Kit.Type.body, "value", Enum.TextXAlignment.Right).Name = "Value_" .. i
        top += Split.FactRowH
    end
    if d.line and d.line ~= "" then
        local line = Layout.text(right, d.line, UDim2.fromOffset(inner, math.max(28, lay.right.h - top - Kit.PanelPad)), UDim2.fromOffset(Kit.PanelPad, top + 4), Kit.Type.body, "label")
        line.Name, line.TextWrapped, line.TextYAlignment = "Line", true, Enum.TextYAlignment.Top
    end
    buttons(d.body, lay.buttons, d.buttons)
    return left
end

-- One food mesh in a small 3D view; nil when the mesh is not loaded (R5: never a stand-in picture).
local function foodView(card: Frame, meshName: string, r: Rules.Rect): ViewportFrame?
    local folder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local source = folder and folder:FindFirstChild(meshName)
    if not (source and source:IsA("BasePart")) then return nil end
    local view = Instance.new("ViewportFrame")
    view.Name, view.BackgroundTransparency, view.Size, view.Position, view.ZIndex = "Food", 1, size(r), pos(r), card.ZIndex + 1
    view.Ambient, view.LightColor, view.LightDirection = Color3.fromRGB(200, 200, 200), Color3.new(1, 1, 1), Vector3.new(-1, -1.5, -1)
    local part = source:Clone() :: BasePart
    local rotX = math.rad(tonumber(source:GetAttribute("RotX")) or 0) -- the upright turn FoodService gives it in the world (the nests came in on their side)
    part.Anchored, part.CFrame = true, CFrame.Angles(0, math.rad(-25), 0) * CFrame.Angles(rotX, 0, 0)
    part.Parent = view
    local camera = Instance.new("Camera")
    local radius = part.Size.Magnitude / 2
    local distance = radius / math.tan(math.rad(camera.FieldOfView / 2)) * 1.05
    camera.CFrame = CFrame.lookAt(Vector3.new(0, radius * 0.45, distance), Vector3.zero)
    camera.Parent = view
    view.CurrentCamera = camera
    view.Parent = card
    return view
end

-- The Food guide. d: {body, eggs = eggs for 500 food}.
function M.food(d: any)
    live(d.body, function() return M.drawFood(d) end)
end
function M.drawFood(d: any): GuiObject
    local w, h = ModalCompact.bodyWidth(), ModalCompact.bodyHeight()
    local lay = Rules.food(w, h, #Rules.Food)
    local first: GuiObject? = nil
    for i, food in Rules.Food do
        local r = lay.cards[i]
        local card = Layout.panel(d.body, "Food_" .. food.kind, size(r), pos(r))
        first = first or card
        local inside = Rules.foodCard(r)
        foodView(card, food.mesh, inside.picture)
        Layout.text(card, food.name, size(inside.name), pos(inside.name), Kit.Type.heading, "value", Enum.TextXAlignment.Center).Name = "Name"
        local chip, word = Chip.new(card, {name = "Grow", fill = rgb(Kit.Tone.previewTop), size = size(inside.chip), position = pos(inside.chip), z = card.ZIndex + 1, text = Rules.growChip(food.growth)})
        chip.Name = "Grow"
        Layout.ink(word)
    end
    local strip = Layout.panel(d.body, "Footer", size(lay.footer), pos(lay.footer))
    Layout.text(strip, Rules.foodFooter(d.eggs), UDim2.new(1, -Kit.PanelPad * 2, 1, 0), UDim2.fromOffset(Kit.PanelPad, 0), Kit.Type.body, "value", Enum.TextXAlignment.Center).Name = "Line"
    return first :: GuiObject
end

return M
