--!strict
-- BD-1214 (docs/240 order step 3): Run complete, Home (Sanctuary) and the Welcome steps on the style rules R1-R8 (style tile v2 board 6,
-- v3 boards 9 and 10): cream panels with an ink outline on the window body (no text on the studs), dark ink on cream, one green main button
-- (every other button grey), real pictures only (bound AssetSlots / UIIconAssets ids and the 3D dino; nothing drawn in code), the
-- 28 / 20 / 16 / 14 type scale, and every rect from Shared/ScreensCohesionLayout so nothing sits outside the body or on top of another thing.
-- Required only while Config.ScreensCohesionEnabled is true (RunComplete, HomeScreen and SmallScreens ask for it); false = never required.
-- Client presentation only: nothing is stored, sent or decided here; the buttons call the same callbacks the old screens used.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Layout = require(Shared.ToyboxLayout)
local Rects = require(Shared.ScreensCohesionLayout)
local Copy = require(Shared.FtueCopy)
local AssetSlots = require(Shared.AssetSlots) :: any
local UIIconAssets = require(Shared.UIIconAssets) :: any
local ModalCompact = require(script.Parent.ModalCompact)
local Kit = Layout.Kit

local S = {}
S.Green = Color3.fromRGB(93, 237, 31) -- Kit button anchors: green = the one main button, grey = every other one (R3)
S.Grey = Color3.fromRGB(128, 142, 158)

local function size(r: Rects.Rect): UDim2 return UDim2.fromOffset(r.w, r.h) end
local function pos(r: Rects.Rect): UDim2 return UDim2.fromOffset(r.x, r.y) end
local function body(): (number, number, number) return ModalCompact.bodyWidth(), ModalCompact.bodyHeight(), ModalCompact.bodyScale() end

-- A real picture from a bound slot (AssetSlots.Images first, then the UI icons); nil while the slot is empty (R5: never a stand-in).
function S.pictureId(slot: string): string?
    for _, map in {AssetSlots.Images, UIIconAssets} do
        local id = map[slot]
        if typeof(id) == "string" and string.match(id, "^rbxassetid://%d+$") then return id end
    end
    return nil
end
local function picture(parent: GuiObject, slot: string, r: Rects.Rect): ImageLabel?
    local id = S.pictureId(slot)
    if not id then return nil end
    local image = Instance.new("ImageLabel")
    image.Name, image.BackgroundTransparency, image.Image, image.ScaleType = "Picture_" .. slot, 1, id, Enum.ScaleType.Fit
    image.Size, image.Position, image.ZIndex = size(r), pos(r), parent.ZIndex + 1
    image.Parent = parent
    return image
end

-- Fact rows: label left in the muted tone, value right in the dark tone, both at the heading size (R2 ink on cream, R6 scale).
local function factRows(panel: Frame, top: number, inner: number, panelH: number, rows: {{string}}): number
    local count = Rects.rowsThatFit(panelH, top, #rows)
    for i = 1, count do
        local y = top + (i - 1) * Rects.FactRowH
        local label = Layout.text(panel, rows[i][1], UDim2.fromOffset(math.floor(inner * 0.6), Rects.FactRowH), UDim2.fromOffset(Kit.PanelPad, y), Kit.Type.heading, "label")
        label.Name = "Label_" .. i
        local value = Layout.text(panel, rows[i][2], UDim2.fromOffset(math.floor(inner * 0.4) - Kit.Gutter, Rects.FactRowH), UDim2.fromOffset(Kit.PanelPad + math.floor(inner * 0.6) + Kit.Gutter, y), Kit.Type.heading, "value", Enum.TextXAlignment.Right)
        value.Name = "Value_" .. i
    end
    return top + count * Rects.FactRowH
end

-- R8 on a resize: the screen is drawn for the body that is on screen now; when the window is laid out for another size while it is open (a phone
-- turned, a window dragged), it is drawn again for the new body (the pattern of ShopScreens, BD-1178). draw() returns its first panel, the mark:
-- once another screen has replaced it, the listener stops.
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

local function buttons(parent: GuiObject, rects: {Rects.Rect}, list: {{any}})
    for i, b in list do
        local r = rects[i]
        Layout.actionButton(parent, b[1], size(r), pos(r), if b[3] then S.Green else S.Grey, false, b[2]).Name = "Action_" .. b[1]
    end
end

-- Run complete. d: {body, num, oops, hasEggs, mode, eggsWaiting, streak, back, openEggs}. mode = StarterRunClient.resultsMode.
function S.results(d: any)
    local parent: Frame = d.body
    for _, child in parent:GetChildren() do -- Bootstrap's defeat line sits on the studs: its words move into the facts panel
        if child:IsA("TextLabel") and child.Text == "Your eggs are safe!" then child:Destroy() end
    end
    live(parent, function() return S.drawResults(d) end)
end
function S.drawResults(d: any): GuiObject
    local parent: Frame = d.body
    local list = {}
    if d.mode == "normal" then table.insert(list, {"Back home", d.back, not d.hasEggs}) end
    if d.hasEggs then table.insert(list, {"OPEN EGGS", d.openEggs, true}) end
    local w, h, scale = body()
    local lay = Rects.split(w, h, scale, 0.44, #list)
    local facts = Layout.panel(parent, "Facts", size(lay.left), pos(lay.left))
    local inner = lay.left.w - Kit.PanelPad * 2
    local top = Kit.PanelPad
    if (d.oops or 0) > 0 then
        Layout.text(facts, "Your eggs are safe!", UDim2.fromOffset(inner, 28), UDim2.fromOffset(Kit.PanelPad, top), Kit.Type.heading).Name = "Safe"
        top += 36
    end
    local rows = Copy.runCompleteFacts({
        eggs = d.num("LastRunCatchScore"), crystals = d.num("LastRunCrystals"), nests = d.num("LastRunNestCount"),
        nestCrystals = d.num("LastRunNestCrystals"), growth = d.num("LastRunGrowthScore"), killEggs = d.num("LastRunKillEggs"),
    })
    table.insert(rows, {"Level", tostring(math.floor(d.num("AccountLevel")))})
    if d.streak then table.insert(rows, {"Streak", string.match(d.streak, "%d+") or ""}) end
    local cheer = Rects.tip(lay.left, factRows(facts, top, inner, lay.left.h, rows) + Kit.Gutter)
    if cheer then -- the free room: the trophy and one cheer (style tile v2 board 6 "Great run!")
        picture(facts, "trophy", cheer.picture)
        Layout.text(facts, if (d.oops or 0) > 0 then Copy.runCheerDefeat else Copy.runCheer, size(cheer.line), pos(cheer.line), Kit.Type.heading, "value", Enum.TextXAlignment.Center).Name = "Cheer"
    end
    local eggs = Layout.panel(parent, "Eggs", size(lay.right), pos(lay.right))
    local waiting = if d.hasEggs then math.max(1, d.eggsWaiting or 0) else 0
    local inside = Rects.eggsPanel(lay.right, if waiting > 0 then waiting else 1)
    for _, r in inside.pictures do picture(eggs, if waiting > 0 then "egg_green_spotted" else "golden_drumstick_icon", r) end
    local line = Layout.text(eggs, Copy.eggsReadyLine(waiting), size(inside.line), pos(inside.line), Kit.Type.heading, "value", Enum.TextXAlignment.Center)
    line.Name = "EggsLine"
    buttons(parent, lay.buttons, list)
    return facts
end

-- Home (Sanctuary). d: {body, hero, bestMutation, id, name, eggsWaiting, nests, level, explore, openEggs}.
function S.home(d: any)
    live(d.body, function() return S.drawHome(d) end)
end
function S.drawHome(d: any): GuiObject
    local parent: Frame = d.body
    local list = {}
    if d.eggsWaiting > 0 then table.insert(list, {"OPEN EGGS", d.openEggs, false}) end
    table.insert(list, {"Explore", d.explore, true})
    local w, h, scale = body()
    local lay = Rects.split(w, h, scale, 0.4, #list)
    local dino = Layout.panel(parent, "Dino", size(lay.left), pos(lay.left))
    local pad = Kit.PanelPad
    local box = Layout.preview(dino, UDim2.fromOffset(lay.left.w - pad * 2, lay.left.h - pad * 2), UDim2.fromOffset(pad, pad))
    box.ZIndex = dino.ZIndex + 1
    d.hero(box, d.id, 0, 0, lay.left.w - pad * 2, lay.left.h - pad * 2 - 40, d.bestMutation(d.id))
    local chipW = math.min(lay.left.w - pad * 4, 200)
    local chip = Layout.chip(box, d.name, UDim2.fromOffset(chipW, 28), UDim2.fromOffset((lay.left.w - pad * 2 - chipW) / 2, lay.left.h - pad * 2 - 36))
    chip.Name, chip.ZIndex = "NameChip", box.ZIndex + 4
    for _, c in chip:GetChildren() do if c:IsA("GuiObject") then c.ZIndex = chip.ZIndex + 1 end end
    local info = Layout.panel(parent, "Info", size(lay.right), pos(lay.right))
    local inner = lay.right.w - pad * 2
    Layout.text(info, "Ready for an adventure?", UDim2.fromOffset(inner, 32), UDim2.fromOffset(pad, pad), Kit.Type.heading).Name = "Title"
    local rows = {{"Eggs to open", tostring(d.eggsWaiting)}, {"Nests", string.format("%d of 5", d.nests)}, {"Level", tostring(d.level)}}
    local tip = Rects.tip(lay.right, factRows(info, 52, inner, lay.right.h, rows) + Kit.Gutter)
    if tip then -- the free room: what to do next, with a real picture
        picture(info, if d.eggsWaiting > 0 then "egg_green_spotted" else "golden_drumstick_icon", tip.picture)
        Layout.text(info, if d.eggsWaiting > 0 then Copy.eggsReadyLine(d.eggsWaiting) else Copy.homeTip, size(tip.line), pos(tip.line), Kit.Type.heading, "value", Enum.TextXAlignment.Center).Name = "Tip"
    end
    buttons(parent, lay.buttons, list)
    return dino
end

-- The Welcome steps. d: {body, play}.
function S.tutorial(d: any)
    live(d.body, function() return S.drawTutorial(d) end)
end
function S.drawTutorial(d: any): GuiObject
    local parent: Frame = d.body
    local first: GuiObject? = nil
    local w, h, scale = body()
    local steps = Copy.welcomeSteps
    local lay = Rects.cards(w, h, scale, #steps)
    for i, step in steps do
        local r = lay.cards[i]
        local card = Layout.panel(parent, "Step" .. i, size(r), pos(r))
        first = first or card
        local inside = Rects.card(r)
        local chip = Layout.chip(card, tostring(i), size(inside.chip), pos(inside.chip))
        chip.Name = "Number"
        picture(card, step[3], inside.picture)
        Layout.text(card, step[1], size(inside.title), pos(inside.title), Kit.Type.heading, "value", Enum.TextXAlignment.Center).Name = "Title"
        local line = Layout.text(card, step[2], size(inside.line), pos(inside.line), Kit.Type.body, "label", Enum.TextXAlignment.Center)
        line.Name, line.TextWrapped, line.TextYAlignment = "Line", true, Enum.TextYAlignment.Top
    end
    buttons(parent, lay.buttons, {{"Let's play", d.play, true}})
    return first :: GuiObject
end

return S
