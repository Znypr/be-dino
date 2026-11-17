--!strict
-- BD-1213 (docs/240 step 2, style tile v2 board 1, cohesion matrix rows "HUD in the world" and "World labels"): the in-run HUD and the world labels
-- on the style rules R1-R8, ONLY while Config.HudCohesionEnabled is on (flag off: this script returns on its first line and nothing changes).
-- It finds what Bootstrap, HudV2, GoalHud, HudTimers and HudToybox built and restyles it; it never moves a layout slot or resizes a button
-- (TouchLayout keeps its numbers), adds no code to Bootstrap (size ceiling) and never touches the hatch screen.
--   R1  the egg plate, the SIZE bar, the crystal plate and the goal line become cream plates with an ink outline (no navy plates);
--   R2  their words are dark ink on cream; the debug lines (BUILD id, FOOD count, STUDIO PREVIEW) leave the HUD, the preview warning becomes one
--       small cream chip "Test game: not saved" (unsaved Studio preview only);
--   R3  LEAP is grey like HOME, CHOMP is the one green button;
--   R6  the crystal count is a grouped number ("12,450") beside the crystal picture;
--   R8  the key badges hang on the top edge of their button (never on the word), HOME's grey face covers its icon (the icon no longer floats
--       outside the button), and "+3 Crystals" floats above its amber instead of behind it.
-- Client presentation only: nothing is stored, sent or decided.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).HudCohesionEnabled ~= true then return end

local Rules = require(Shared:WaitForChild("HudCohesionRules"))
local Kit = require(Shared:WaitForChild("ToyboxKit"))
local Theme = require(Shared:WaitForChild("UITheme"))

local player = Players.LocalPlayer
local gui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI")
local C = Theme.Colors
local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
local CREAM, INK, LINE, SLOT = rgb(Kit.Tone.panel), rgb(Kit.Tone.value), rgb(Kit.Outline), rgb(Kit.Tone.slot)
local done: {[Instance]: boolean} = setmetatable({}, {__mode = "k"}) :: any

-- R1: a flat cream plate with a 3 px ink outline (an old gradient goes, an old stroke is reused).
local function plate(frame: GuiObject, corner: number)
    frame.BackgroundColor3, frame.BackgroundTransparency, frame.BorderSizePixel = CREAM, 0, 0
    local gradient = frame:FindFirstChildOfClass("UIGradient")
    if gradient then gradient:Destroy() end
    local round = frame:FindFirstChildOfClass("UICorner") or Instance.new("UICorner")
    round.CornerRadius, round.Parent = UDim.new(0, corner), frame
    local line = frame:FindFirstChildOfClass("UIStroke") or Instance.new("UIStroke")
    line.Color, line.Thickness, line.Transparency, line.ApplyStrokeMode, line.Enabled = LINE, Kit.PanelStroke, 0, Enum.ApplyStrokeMode.Border, true
    line.Parent = frame
    frame:GetPropertyChangedSignal("BackgroundColor3"):Connect(function() if frame.BackgroundColor3 ~= CREAM then frame.BackgroundColor3 = CREAM end end)
    frame:GetPropertyChangedSignal("BackgroundTransparency"):Connect(function() if frame.BackgroundTransparency ~= 0 then frame.BackgroundTransparency = 0 end end)
end

-- R2: dark ink on cream, no outline; kept ink when a screen sets another colour (the goal line turns green / gold on every refresh).
local function ink(label: TextLabel)
    local function apply()
        if label.TextColor3 ~= INK then label.TextColor3 = INK end
        label.TextStrokeTransparency = 1
        for _, child in label:GetChildren() do
            if child:IsA("UIStroke") then child.Transparency = 1 end
        end
    end
    apply()
    label:GetPropertyChangedSignal("TextColor3"):Connect(apply)
end

local function keepHidden(object: GuiObject)
    object.Visible = false
    object:GetPropertyChangedSignal("Visible"):Connect(function() if object.Visible then object.Visible = false end end)
end

local function once(object: Instance?, work: (any) -> ()): boolean
    if object == nil then return false end
    if done[object] then return true end
    done[object] = true
    work(object)
    return true
end

-- The test chip: one small cream chip in kid words, only in an unsaved Studio preview. It sits in the slot TouchLayout reserves for the old preview
-- line (layout.notice, kept clear of every other HUD piece by tools/verify_hud_clearance.py) and follows it on every layout pass.
local function makeTestChip(notice: TextLabel)
    local chip = Instance.new("Frame")
    chip.Name, chip.ZIndex = "TestChip", 6
    plate(chip, Kit.ChipCorner)
    local word = Instance.new("TextLabel")
    word.Name, word.BackgroundTransparency, word.Size, word.ZIndex = "Text", 1, UDim2.fromScale(1, 1), 7
    word.Font, word.TextSize, word.Text = Enum.Font.FredokaOne, Rules.Text.chip, Rules.TestChip
    word.Parent = chip
    ink(word)
    local function follow()
        local w, h = Rules.chipSize(notice.Size.X.Offset, notice.Size.Y.Offset)
        local centred = notice.TextXAlignment == Enum.TextXAlignment.Center
        chip.AnchorPoint, chip.Size = notice.AnchorPoint, UDim2.fromOffset(w, h)
        chip.Position = notice.Position + UDim2.fromOffset(if centred then (notice.Size.X.Offset - w) // 2 * (1 - 2 * notice.AnchorPoint.X) else 0, 0)
    end
    local function show() chip.Visible = Rules.testChipVisible(player:GetAttribute("ProfileMode")) end
    follow()
    show()
    for _, property in {"Position", "Size", "AnchorPoint", "TextXAlignment"} do notice:GetPropertyChangedSignal(property):Connect(follow) end
    player:GetAttributeChangedSignal("ProfileMode"):Connect(show)
    chip.Parent = gui
end

local function crystals(frame: Frame)
    plate(frame, Kit.PanelCorner)
    for _, child in frame:GetChildren() do
        if child:IsA("TextLabel") then
            ink(child)
            child.TextSize, child.TextXAlignment = Rules.Text.crystals, Enum.TextXAlignment.Left -- the number sits beside the crystal picture
            local function group()
                local amount = Rules.crystalsFrom(child.Text)
                if amount then child.Text = Rules.grouped(amount) end
            end
            group()
            child:GetPropertyChangedSignal("Text"):Connect(group)
        end
    end
end

local function sizeBar(bar: Frame)
    plate(bar, Kit.PanelCorner)
    local word = bar:FindFirstChild("SizeWord")
    if word and word:IsA("TextLabel") then ink(word) end
    local track = bar:FindFirstChild("Track")
    if track and track:IsA("Frame") then
        track.BackgroundColor3 = SLOT
        local line = track:FindFirstChildOfClass("UIStroke") or Instance.new("UIStroke")
        line.Color, line.Thickness, line.Parent = LINE, 2, track
    end
end

local function eggs(eggPlate: Frame)
    plate(eggPlate, Kit.PanelCorner)
    local word = eggPlate:FindFirstChild("EggsText")
    if word and word:IsA("TextLabel") then ink(word) end
end

local function goal(goalHud: Frame)
    plate(goalHud, Kit.ChipCorner)
    for _, child in goalHud:GetChildren() do
        if child:IsA("TextLabel") then ink(child) end
    end
end

-- R8: the key badge hangs on the top edge of its button, half above it, never on the word.
local function badge(button: Instance)
    local hint = button:FindFirstChild("KeyHint")
    if not (hint and hint:IsA("GuiObject")) or done[hint] then return end
    done[hint] = true
    local anchor, x, y = Rules.badgeSpot(Kit.Hud.badgeInset)
    local function place() hint.AnchorPoint, hint.Position = anchor, UDim2.new(1, x, 0, y) end
    place()
    hint:GetPropertyChangedSignal("Position"):Connect(function() if hint.Position ~= UDim2.new(1, x, 0, y) then place() end end)
end

-- R3: LEAP grey (Bootstrap paints it blue whenever it is ready; the skin swaps the gloss picture by colour).
local function leap(button: TextButton)
    local function grey()
        local want = Rules.leapColour(button.BackgroundColor3, C.blue, C.card)
        if want ~= button.BackgroundColor3 then button.BackgroundColor3 = want end
    end
    grey()
    button:GetPropertyChangedSignal("BackgroundColor3"):Connect(grey)
end

-- R8: HOME's grey face covers the padding too, so the home icon sits inside the button instead of floating at its left.
local function home(button: Instance)
    local face = button:FindFirstChild("ToyboxFace")
    local pad = button:FindFirstChildOfClass("UIPadding")
    if not (face and face:IsA("GuiObject") and pad) then return end
    local function fit()
        local l, r, t, b = pad.PaddingLeft.Offset, pad.PaddingRight.Offset, pad.PaddingTop.Offset, pad.PaddingBottom.Offset
        face.Position, face.Size = UDim2.fromOffset(-l, -t), UDim2.new(1, l + r, 1, t + b)
    end
    fit()
    for _, property in {"PaddingLeft", "PaddingRight", "PaddingTop", "PaddingBottom"} do pad:GetPropertyChangedSignal(property):Connect(fit) end
    face:GetPropertyChangedSignal("Size"):Connect(function()
        if face.Size ~= UDim2.new(1, pad.PaddingLeft.Offset + pad.PaddingRight.Offset, 1, pad.PaddingTop.Offset + pad.PaddingBottom.Offset) then fit() end
    end)
end

-- R1/R2 (BD-1241 emulator pass 2026-11-17): the home menu rail (DINOS, EGGS, FUSION, SHOP, POTIONS) was the last dark navy plate on the
-- home HUD; it becomes a cream plate and its words dark ink like the other plates (the gold active-tab bar and the red dot stay).
local function rail(frame: Frame)
    plate(frame, Kit.PanelCorner)
    for _, item in frame:GetDescendants() do
        if item:IsA("TextLabel") and item.Name == "TextLabel" and item.Parent and item.Parent:IsA("TextButton") then ink(item) end
    end
end
local function findRail(): Frame?
    for _, child in gui:GetChildren() do
        if child:IsA("Frame") then
            for _, button in child:GetChildren() do
                if button:IsA("TextButton") and button:FindFirstChild("Art_dinos") then return child end
            end
        end
    end
    return nil
end

local function startsWith(text: string, prefix: string): boolean return string.sub(text, 1, #prefix) == prefix end

-- One pass over the HUD; every piece is styled once, the pass repeats until all are found (Bootstrap builds them in steps).
local function pass(): boolean
    local all = true
    for _, child in gui:GetChildren() do
        if child:IsA("TextLabel") then
            if child.Name == "BuildBadge" or startsWith(child.Text, "FOOD:") then
                once(child, keepHidden)
            elseif startsWith(child.Text, "STUDIO PREVIEW") then
                once(child, function(notice) keepHidden(notice) makeTestChip(notice) end)
            end
        elseif child:IsA("Frame") and child:FindFirstChild("OpenShop") then
            once(child, crystals)
        end
    end
    local buildBadge = gui:FindFirstChild("BuildBadge")
    if not (buildBadge and done[buildBadge]) then all = false end
    all = once(gui:FindFirstChild("SizeBar"), sizeBar) and all
    all = once(gui:FindFirstChild("NextGoal"), goal) and all
    all = once(gui:FindFirstChild("EggsPlate", true), eggs) and all
    local homeButton = gui:FindFirstChild("HomeButton")
    all = once(homeButton, home) and all
    all = once(findRail(), rail) and all
    local bite = gui:FindFirstChild("BiteButton", true)
    if bite then badge(bite) end
    local leapFound = false
    for _, item in gui:GetDescendants() do -- LEAP has no name: it is the button whose word says LEAP (or its countdown)
        if item:IsA("TextLabel") and item.Name ~= "ToyboxText" and item.Name ~= "ToyboxTextDrop" and item.Parent and item.Parent:IsA("TextButton")
            and item.Parent ~= bite and (startsWith(item.Text, "LEAP") or string.match(item.Text, "^%d+ s$") ~= nil) then
            once(item.Parent, leap)
            badge(item.Parent)
            leapFound = true
        end
    end
    return all and leapFound
end

local boards: {BillboardGui} = {}
-- World labels: "+3 Crystals" floats above the top of its amber (server-built BillboardGui on a CrystalPickup part; the change is local only).
local function crystalLabel(board: BillboardGui)
    local part = board.Parent
    if not (part and part:IsA("BasePart") and part.Name == "CrystalPickup") or done[board] then return end
    done[board] = true
    table.insert(boards, board)
    local function lift()
        local model = part:FindFirstChildWhichIsA("Model") or part:FindFirstChildWhichIsA("BasePart")
        local top = part.Position.Y + part.Size.Y / 2
        if model and model:IsA("Model") then
            local frame, size = model:GetBoundingBox()
            top = frame.Position.Y + size.Y / 2
        elseif model and model:IsA("BasePart") then
            top = model.Position.Y + model.Size.Y / 2
        end
        board.StudsOffset = Vector3.zero
        board.StudsOffsetWorldSpace = Vector3.new(0, Rules.labelLift(top, part.Position.Y), 0)
    end
    lift()
    part:GetPropertyChangedSignal("Position"):Connect(function() task.defer(lift) end)
    for _, label in board:GetChildren() do
        if label:IsA("TextLabel") then label.TextSize = Rules.Text.worldLabel end
    end
end

task.spawn(function()
    for _ = 1, 240 do -- up to 2 minutes while Bootstrap builds the HUD in steps (LEAP shows its word only once a character exists)
        if pass() then break end
        task.wait(0.5)
    end
end)
for _, item in workspace:GetDescendants() do
    if item:IsA("BillboardGui") then crystalLabel(item) end
end
workspace.DescendantAdded:Connect(function(item)
    if item:IsA("BillboardGui") then task.defer(crystalLabel, item) end
end)
-- R8: two labels that would print on top of each other on the screen (an amber behind another): the nearer one shows its words (4 times a second).
task.spawn(function()
    while true do
        task.wait(0.25)
        for i = #boards, 1, -1 do
            if boards[i].Parent == nil then table.remove(boards, i) end
        end
        local camera = workspace.CurrentCamera
        if camera then
            local spots = {}
            for i, board in boards do
                local part = board.Parent :: BasePart
                local at = part.Position + board.StudsOffsetWorldSpace
                local point, onScreen = camera:WorldToViewportPoint(at)
                local depth = (camera.CFrame.Position - at).Magnitude
                spots[i] = {x = point.X, y = point.Y, depth = depth, on = board.Enabled and onScreen and depth <= board.MaxDistance}
            end
            local show = Rules.declutter(spots, Rules.LabelBox.w, Rules.LabelBox.h)
            for i, board in boards do
                for _, label in board:GetChildren() do
                    if label:IsA("TextLabel") and label.Visible ~= (show[i] == true) then label.Visible = show[i] == true end
                end
            end
        end
    end
end)
