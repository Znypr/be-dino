--!strict
-- BD-1258 / BD-1259 / BD-1260 / BD-1268 / BD-1269 / BD-1271 (docs/244 s2.14, owner phone test 2026-11-17 "ui is really messy and all over the place",
-- approved mock docs/evidence/2026-11-17-ui-hud/mock-01-hud.png): the phone HUD zones, ONLY while Config.PhoneHudZonesEnabled is on (flag off: this
-- script returns on its first line and nothing changes). One job per corner, the middle box empty (Shared/PhoneHudLayout owns every number):
--   top-centre    the event banner (weather icon, one line, "3 min left", a faint strip) and the SIZE plate with the health strip inside it
--   left          SHOP and DINOS word buttons;  right: square tiles (Home, Eggs, Fusion, Potions, gear)
--   bottom-left   crystals and eggs: an icon and a big bold italic number with a thick black stroke, no plate
--   bottom-right  the potion timers left of Roblox's jump button;  bottom-centre: LEAP and CHOMP as dark see-through squares
--   the toast lane above LEAP and CHOMP (Toasts.luau reads the ToastLaneRect attribute this script writes)
-- The buttons are Bootstrap's own (their taps, cooldowns, first-run and in-run hiding are unchanged): they move into this layer and get a new face.
-- The old plates (eggs, crystals, SIZE bar, goal line, weather tile, potion lines, the rail panel) are parked in a hidden frame and drawn here from
-- the same data. Adds no code to Bootstrap (size ceiling); RailRun skips a button marked PhoneHudOwned. Client presentation only: nothing is
-- stored, sent or decided.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local GuiService = game:GetService("GuiService")
local TextService = game:GetService("TextService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).PhoneHudZonesEnabled ~= true then return end

local L = require(Shared:WaitForChild("PhoneHudLayout"))
local Kit = require(Shared:WaitForChild("ToyboxKit"))
local Chip = require(Shared:WaitForChild("ChipStyle"))
local Theme = require(Shared:WaitForChild("UITheme"))
local HudRules = require(Shared:WaitForChild("HudRules"))
local Slots = require(Shared:WaitForChild("AssetSlots"))
local PotionArt = require(Shared:WaitForChild("PotionArt"))
local ProgressionConfig = require(Shared:WaitForChild("ProgressionConfig"))
local ProgressionRules = require(Shared:WaitForChild("ProgressionRules"))
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))
local PotionChips = require(script.Parent:WaitForChild("PotionChips"))
local Nav = require(Shared:WaitForChild("NavigationArtwork"))

local player = Players.LocalPlayer
local gui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI") :: ScreenGui
local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
local INK, CREAM, SLOT = rgb(Kit.Outline), rgb(Kit.Tone.panel), rgb(Kit.Tone.slot)
local A = Kit.ButtonAnchors
local ORANGE = Color3.fromRGB(255, 150, 46) -- docs/244 s2.14 s7: DINOS is orange
local DARK = rgb(A.dark)
local UPRIGHT = Font.new("rbxasset://fonts/families/FredokaOne.json", Enum.FontWeight.Bold, Enum.FontStyle.Normal)
local ITALIC = Font.new("rbxasset://fonts/families/FredokaOne.json", Enum.FontWeight.Bold, Enum.FontStyle.Italic)

-- The layer under the menus (the scrim is ZIndex 20) and the parking frame for the old pieces.
local root = Instance.new("Frame")
root.Name, root.Size, root.BackgroundTransparency, root.ZIndex, root.Active = "PhoneHud", UDim2.fromScale(1, 1), 1, 4, false
root.Parent = gui
local parked = Instance.new("Frame")
parked.Name, parked.Visible, parked.BackgroundTransparency, parked.Size = "PhoneHudParked", false, 1, UDim2.fromScale(1, 1)
parked.Parent = gui
local function park(object: Instance?)
    if object and object.Parent ~= parked then object.Parent = parked end
end

-- One HUD word: FredokaOne, a black stroke (BD-1259: every HUD word over the world has one).
local function word(parent: Instance, name: string, z: number, fill: Color3?, stroke: number?): TextLabel
    local t = Instance.new("TextLabel")
    t.Name, t.BackgroundTransparency, t.Font, t.TextColor3, t.ZIndex = name, 1, Enum.Font.FredokaOne, fill or Color3.new(1, 1, 1), z
    t.TextScaled, t.TextWrapped, t.TextTruncate, t.Text = false, false, Enum.TextTruncate.AtEnd, ""
    local line = Instance.new("UIStroke")
    line.Color, line.Thickness, line.LineJoinMode, line.ApplyStrokeMode = INK, stroke or L.Stroke.word, Enum.LineJoinMode.Round, Enum.ApplyStrokeMode.Contextual
    line.Parent = t
    t.Parent = parent
    return t
end
local function box(parent: Instance, name: string, z: number): Frame
    local f = Instance.new("Frame")
    f.Name, f.BackgroundTransparency, f.BorderSizePixel, f.ZIndex = name, 1, 0, z
    f.Parent = parent
    return f
end
-- v7 (owner 2026-11-21 "icons miss the bold black outline"; ChatGPT spec: 4-5 px #10100B at 720 p): until the icon PNGs get a baked
-- outline (art task), each icon gets 8 black copies behind it, offset by the outline width in the 8 directions.
local ICON_INK = Color3.fromHex("#10100B")
local outlinePx = 3 -- set from the layout (0.6 % of the screen height)
local outlined: {{copy: GuiObject, dx: number, dy: number, base: UDim2}} = {}
local DIRS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {0.71, 0.71}, {-0.71, 0.71}, {0.71, -0.71}, {-0.71, -0.71}}
local function blacken(root: Instance)
    for _, d in root:GetDescendants() do
        if d:IsA("ImageLabel") or d:IsA("ImageButton") then d.ImageColor3 = ICON_INK
        elseif d:IsA("TextLabel") then d.TextColor3 = ICON_INK
        elseif d:IsA("UIGradient") then d:Destroy()
        elseif d:IsA("UIStroke") then d.Color = ICON_INK end
        if d:IsA("GuiObject") and d.BackgroundTransparency < 1 then d.BackgroundColor3 = ICON_INK end
    end
    if root:IsA("ImageLabel") then root.ImageColor3 = ICON_INK end
    if root:IsA("GuiObject") and root.BackgroundTransparency < 1 then root.BackgroundColor3 = ICON_INK end
end
local function addOutline(holder: Frame, made: GuiObject)
    for _, dir in DIRS do
        local copy = made:Clone()
        copy.Name = "Outline"
        copy.ZIndex = made.ZIndex - 1
        for _, d in copy:GetDescendants() do if d:IsA("GuiObject") then d.ZIndex = math.max(d.ZIndex - 1, 1) end end
        blacken(copy)
        copy.Parent = holder
        table.insert(outlined, {copy = copy, dx = dir[1], dy = dir[2], base = made.Position})
    end
end
local function placeOutlines()
    for i = #outlined, 1, -1 do
        local o = outlined[i]
        if o.copy.Parent == nil then table.remove(outlined, i) continue end
        o.copy.Position = o.base + UDim2.fromOffset(math.floor(o.dx * outlinePx + 0.5), math.floor(o.dy * outlinePx + 0.5))
    end
end
-- Theme.icon draws at a fixed design size (its inner pictures are offsets), so the icon keeps that size and a UIScale fits it to its holder.
local function icon(holder: Frame, id: string, noOutline: boolean?): GuiObject?
    for _, child in holder:GetChildren() do if child:IsA("GuiObject") or child:IsA("UIScale") then child:Destroy() end end
    local made = Theme.icon(holder, id)
    if made == nil then return nil end
    local base = math.max(made.Size.X.Offset, 1)
    made.AnchorPoint, made.Position, made.ZIndex = Vector2.zero, UDim2.fromScale(0, 0), holder.ZIndex + 2
    local fit = Instance.new("UIScale")
    fit.Parent = made
    if not noOutline then addOutline(holder, made) end
    local function size()
        local scale = math.max(holder.AbsoluteSize.X, 1) / base
        for _, child in holder:GetChildren() do
            local s = child:FindFirstChildOfClass("UIScale")
            if s then s.Scale = scale end
        end
    end
    size()
    holder:GetPropertyChangedSignal("AbsoluteSize"):Connect(size)
    placeOutlines()
    return made
end
local function image(holder: Frame, id: any): ImageLabel?
    if not (type(id) == "string" and string.match(id, "^rbxassetid://%d+$")) then return nil end
    local pic = Instance.new("ImageLabel")
    pic.Name, pic.BackgroundTransparency, pic.Image, pic.ScaleType, pic.Size, pic.ZIndex = "Picture", 1, id, Enum.ScaleType.Fit, UDim2.fromScale(1, 1), holder.ZIndex + 2
    pic.Parent = holder
    addOutline(holder, pic)
    placeOutlines()
    return pic
end
local function pop(scale: UIScale)
    if not Theme.MotionEnabled then return end -- Reduce Motion: no pop
    scale.Scale = 1.15
    Theme.animate(scale, 0.15, {Scale = 1})
end
local function place(object: GuiObject, r: any)
    object.AnchorPoint, object.Position, object.Size = Vector2.zero, UDim2.fromOffset(math.floor(r.x + 0.5), math.floor(r.y + 0.5)), UDim2.fromOffset(math.floor(r.w + 0.5), math.floor(r.h + 0.5))
end

-- ===== Event banner (BD-1271) =====
local banner = box(root, "EventBanner", 5)
local strip = Instance.new("Frame") -- black at 65 % transparency with soft ends, no plate, no border
-- v5 audit: a bright cyan see-through capsule (#18BBDD at 40 %), fully round ends, a faint light top edge
strip.Name, strip.Size, strip.BackgroundColor3, strip.BackgroundTransparency, strip.BorderSizePixel, strip.ZIndex = "Strip", UDim2.fromScale(1, 1), Color3.fromHex("#149FC7"), 0.65, 0, 5
local capsule = Instance.new("UICorner") capsule.CornerRadius = UDim.new(0.5, 0) capsule.Parent = strip
local rim = Instance.new("UIStroke") rim.Color, rim.Transparency, rim.Thickness, rim.ApplyStrokeMode = Color3.fromHex("#C8FFFF"), 0.7, 1, Enum.ApplyStrokeMode.Border
rim.Parent = strip
strip.Parent = banner
local bannerIcon = box(banner, "Icon", 6)
local bannerLine = word(banner, "Line", 7)
local bannerTimer = word(banner, "Timer", 7)
local lastWeather = ""

-- ===== SIZE plate with health inside (BD-1258) =====
local plate = box(root, "SizePlate", 5)
Chip.apply(plate, CREAM, INK)
local sizeWord = word(plate, "SizeWord", 7, rgb(Kit.Tone.value), 0)
sizeWord.Text, sizeWord.TextXAlignment = HudRules.SizeWord, Enum.TextXAlignment.Center
local function track(name: string, fill: Color3): (Frame, Frame)
    local t = box(plate, name, 6)
    t.BackgroundTransparency, t.BackgroundColor3 = 0, SLOT
    local c = Instance.new("UICorner") c.CornerRadius = UDim.new(0.5, 0) c.Parent = t
    local s = Instance.new("UIStroke") s.Color, s.Thickness, s.Parent = INK, 2, t
    local f = box(t, "Fill", 7)
    f.BackgroundTransparency, f.BackgroundColor3, f.Size = 0, fill, UDim2.fromScale(0, 1)
    local fc = Instance.new("UICorner") fc.CornerRadius = UDim.new(0.5, 0) fc.Parent = f
    return t, f
end
local growthTrack, growthFill = track("Growth", rgb(A.green))
local healthTrack, healthFill = track("Health", rgb(A.green))
local heart = box(plate, "Heart", 7)
image(heart, (Slots.Images :: any).hud_heart)
local combat = (Config :: any).CombatEnabled == true
healthTrack.Visible, heart.Visible = combat, combat
local hintLabel = word(root, "GoalHint", 6)
hintLabel.Visible = false

-- ===== Counters (BD-1268) =====
local function counter(name: string, iconId: string, fill: Color3, italic: boolean?): (Frame, TextLabel, UIScale)
    local row = box(root, name, 5)
    local holder = box(row, "Icon", 6)
    icon(holder, iconId)
    local number = word(row, "Number", 7, fill, L.Stroke.counter)
    number.FontFace, number.TextXAlignment = if italic then ITALIC else UPRIGHT, Enum.TextXAlignment.Left -- round 2: the crystal value slants, EGGS is upright
    -- v3 (owner 2026-11-21 "looks flat"; ref_compare: the mock's numbers are 70 luma lighter on top): a top-light gradient on the words
    number.TextColor3 = Color3.new(1, 1, 1) -- a UIGradient multiplies the text colour, so the colour lives in the gradient
    local shine = Instance.new("UIGradient")
    shine.Color = if italic -- v7 ChatGPT spec: golden crystal number #FFF36A -> #FFD522 (45 %) -> #FF9D00; EGGS white -> #F5F1E8
        then ColorSequence.new({ColorSequenceKeypoint.new(0, Color3.fromHex("#FFF36A")), ColorSequenceKeypoint.new(0.45, Color3.fromHex("#FFD522")), ColorSequenceKeypoint.new(1, Color3.fromHex("#FF9D00"))})
        else ColorSequence.new(Color3.new(1, 1, 1), Color3.fromHex("#F5F1E8"))
    shine.Rotation, shine.Parent = 90, number
    local scale = Instance.new("UIScale") scale.Parent = row
    return row, number, scale
end
local crystalsRow, crystalsText, crystalsPop = counter("Crystals", "amber", Color3.fromHex("#FFDC32"), true)
local eggsRow, eggsText, eggsPop = counter("Eggs", "egg", Color3.new(1, 1, 1))

-- ===== Potion timers (BD-1268) =====
local timers = box(root, "Timers", 5)
local timerRows: {Frame} = {}
local shownPotions = ""

-- ===== Adopted buttons =====
type Owned = {button: GuiButton, face: Frame, word: TextLabel?, holder: Frame?, want: any}
local owned: {[GuiButton]: Owned} = {}
local KEEP = {KeyHint = true, IndexDot = true, PhoneFace = true}
local function hold(o: Owned)
    local b = o.button
    local function fix()
        local w = o.want
        if w == nil then return end
        if b.AnchorPoint ~= Vector2.zero then b.AnchorPoint = Vector2.zero end
        if b.Position ~= w.pos then b.Position = w.pos end
        if b.Size ~= w.size then b.Size = w.size end
    end
    for _, property in {"Position", "Size", "AnchorPoint"} do b:GetPropertyChangedSignal(property):Connect(fix) end
    local function hide(child: Instance)
        if child:IsA("GuiObject") and not KEEP[child.Name] then
            child.Visible = false
            child:GetPropertyChangedSignal("Visible"):Connect(function() if child.Visible then child.Visible = false end end)
        elseif child:IsA("UIStroke") then
            child.Enabled = false
            child:GetPropertyChangedSignal("Enabled"):Connect(function() if child.Enabled then child.Enabled = false end end)
        elseif child:IsA("UIPadding") then -- a padding would shift the new face (CHOMP's WordPad, HOME's icon room)
            local function zero()
                for _, side in {"PaddingLeft", "PaddingRight", "PaddingTop", "PaddingBottom"} do
                    if (child :: any)[side] ~= UDim.new() then (child :: any)[side] = UDim.new() end
                end
            end
            zero()
            for _, side in {"PaddingLeft", "PaddingRight", "PaddingTop", "PaddingBottom"} do child:GetPropertyChangedSignal(side):Connect(zero) end
        elseif child:IsA("UIScale") then -- Bootstrap's layout scale; the press bounce keeps working around UIScaleBase 1
            b:SetAttribute("UIScaleBase", 1)
            child.Scale = 1
        end
    end
    for _, child in b:GetChildren() do hide(child) end
    b.ChildAdded:Connect(function(child) task.defer(hide, child) end)
    b:GetAttributeChangedSignal("UIScaleBase"):Connect(function()
        if b:GetAttribute("UIScaleBase") ~= 1 then
            b:SetAttribute("UIScaleBase", 1)
            local s = b:FindFirstChildOfClass("UIScale")
            if s then s.Scale = 1 end
        end
    end)
    local function clear()
        if b.BackgroundTransparency ~= 1 then b.BackgroundTransparency = 1 end
        if b:IsA("TextButton") and b.TextTransparency ~= 1 then b.TextTransparency = 1 end
    end
    clear()
    b:GetPropertyChangedSignal("BackgroundTransparency"):Connect(clear)
    if b:IsA("TextButton") then b:GetPropertyChangedSignal("TextTransparency"):Connect(clear) end
end

-- kind: "word" (left), "tile" (right), "square" (bottom-centre)
local function adopt(button: GuiButton, kind: string, fill: {Color3}, iconId: string?, picture: string?, text: string?): Owned
    button:SetAttribute("PhoneHudOwned", true)
    local face = box(button, "PhoneFace", button.ZIndex + 1)
    face.Size, face.BackgroundTransparency = UDim2.fromScale(1, 1), 0
    -- every kind is a solid toy face now (v5: LEAP/CHOMP are solid warm brown, not see-through grey)
    Chip.apply(face, fill[3], OUTLINE)
    local gloss = Instance.new("UIGradient")
    gloss.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, fill[1]),
        ColorSequenceKeypoint.new(0.08, fill[2]),
        ColorSequenceKeypoint.new(0.55, fill[3]),
        ColorSequenceKeypoint.new(0.899, fill[4]),
        ColorSequenceKeypoint.new(0.9, fill[5]),
        ColorSequenceKeypoint.new(1, fill[5]),
    })
    gloss.Rotation, gloss.Parent = 90, face
    face.BackgroundColor3 = Color3.new(1, 1, 1) -- a UIGradient MULTIPLIES the background colour: the colour lives in the gradient only
    local holder = box(face, "Icon", face.ZIndex + 1)
    if picture then image(holder, picture) elseif iconId then icon(holder, iconId) end
    local label: TextLabel? = nil
    if text ~= nil then
        label = word(face, "Word", face.ZIndex + 3)
        local made = label :: TextLabel
        made.Text = text
    end
    local o: Owned = {button = button, face = face, word = label, holder = holder, want = nil}
    owned[button] = o
    hold(o)
    button.Parent = root
    return o
end
-- the toy face's outline and corner follow the button's size (v5 audit: corner 29 % of the height on SHOP/DINOS, 24 % on tiles, 17 % on
-- LEAP/CHOMP; outline 6 px at 720 p, 3 px on LEAP/CHOMP)
local function toy(o: Owned, r: any, stroke: number, corner: number)
    local s = o.face:FindFirstChildOfClass("UIStroke")
    if s then s.Thickness, s.Transparency = stroke, 0 end
    local c = o.face:FindFirstChildOfClass("UICorner")
    if c then c.CornerRadius = UDim.new(0, math.floor(r.h * corner + 0.5)) end
end
local function put(o: Owned, r: any)
    o.want = {pos = UDim2.fromOffset(math.floor(r.x + 0.5), math.floor(r.y + 0.5)), size = UDim2.fromOffset(math.floor(r.w + 0.5), math.floor(r.h + 0.5))}
    place(o.button, r)
end

-- ===== Find Bootstrap's pieces (it builds them in steps) =====
local function navButton(destination: string): GuiButton?
    for _, item in gui:GetDescendants() do
        if item:IsA("GuiButton") and item:GetAttribute("Destination") == destination then return item end
    end
    return nil
end
local function leapButton(): (TextButton?, TextLabel?)
    for _, item in gui:GetDescendants() do
        if item:IsA("TextLabel") and item.Parent and item.Parent:IsA("TextButton") and item.Parent.Name ~= "BiteButton" and item.Name ~= "ToyboxText" and item.Name ~= "ToyboxTextDrop"
            and (string.sub(item.Text, 1, 4) == "LEAP" or string.match(item.Text, "^%d+ s$") ~= nil) then
            return item.Parent :: TextButton, item
        end
    end
    return nil, nil
end
local pieces: any = nil
for _ = 1, 240 do -- up to 2 minutes
    local leap, leapText = leapButton()
    local found = {
        shop = navButton("auras"), dinos = navButton("collection"), eggs = navButton("eggs"), fusion = navButton("fusion"),
        potions = navButton("potions"), settings = navButton("settings"), home = gui:FindFirstChild("HomeButton"),
        leap = leap, leapText = leapText, sizeBar = gui:FindFirstChild("SizeBar"), hint = gui:FindFirstChild("GoalHint"),
        eggPlate = gui:FindFirstChild("EggsPlate", true), goal = gui:FindFirstChild("NextGoal"),
    }
    local crystal: Instance? = nil
    for _, child in gui:GetChildren() do if child:IsA("Frame") and child:FindFirstChild("OpenShop") then crystal = child end end
    found.crystal = crystal
    if found.shop and found.dinos and found.eggs and found.fusion and found.potions and found.settings and found.home and found.leap
        and found.sizeBar and found.eggPlate and crystal then
        pieces = found
        break
    end
    task.wait(0.5)
end
if pieces == nil then
    warn("PhoneHud: the HUD pieces did not appear; the old HUD stays")
    root:Destroy()
    parked:Destroy()
    return
end
local bite = gui:FindFirstChild("BiteButton", true) :: GuiButton?
local railFrame = pieces.shop.Parent
local timerFrame = pieces.leap.Parent

-- v5 (ChatGPT art-director audit of v4, 2026-11-21): exact gradient stops per button, top to bottom:
-- highlight 0-8 %, main fill 8 % -> 55 % -> 90 %, then the dark lip 90-100 %. Colours: the audit's reproduction targets from the mock.
local function stops(hi: string, a: string, b: string, c: string, lip: string): {Color3}
    return {Color3.fromHex(hi), Color3.fromHex(a), Color3.fromHex(b), Color3.fromHex(c), Color3.fromHex(lip)}
end
-- v7 (owner 2026-11-21 "reference is far more vibrant and kid friendly, ours is too cool and boring"): ChatGPT's brighter palette,
-- top / middle / bottom, plus the thin darker lip along the bottom (bottom colour 40 % darker)
local function vivid(top: string, mid: string, bottom: string): {Color3}
    local b = Color3.fromHex(bottom)
    return {Color3.fromHex(top), Color3.fromHex(top), Color3.fromHex(mid), b, b:Lerp(Color3.new(0, 0, 0), 0.4)}
end
local MOCK = {
    green = vivid("#C7FF63", "#80F73A", "#43DC12"),
    orange = vivid("#FFDB91", "#FFAE57", "#FF812B"),
    gold = vivid("#FFF08B", "#FFD641", "#FFB323"),
    cyan = vivid("#8BFCFF", "#31E9FA", "#00BDE6"),
    purple = vivid("#F4ADFF", "#CF6CFA", "#9B30DB"),
    grey = vivid("#D5D6D9", "#999DA4", "#585E68"),
    brown = stops("#766751", "#5A4A34", "#544832", "#504330", "#3A3026"),
}
local OUTLINE = Color3.fromHex("#10100C") -- the audit: near-black, not grey
local shop = adopt(pieces.shop, "word", MOCK.green, "amber", nil, "SHOP")
local dinos = adopt(pieces.dinos, "word", MOCK.orange, Nav.collection, nil, "DINOS")
local home = adopt(pieces.home, "tile", MOCK.green, Nav.home, nil, "")
local tileList: {Owned} = {
    home,
    adopt(pieces.eggs, "tile", MOCK.gold, Nav.eggs),
    adopt(pieces.fusion, "tile", MOCK.cyan, Nav.fusion),
    adopt(pieces.potions, "tile", MOCK.purple, Nav.potions),
    adopt(pieces.settings, "tile", MOCK.grey, Nav.settings),
}
local leap = adopt(pieces.leap, "square", MOCK.brown, "leap", nil, "LEAP")
local chomp: Owned? = if bite then adopt(bite, "square", MOCK.brown, "bite", (Slots.Images :: any).hud_bite, "CHOMP") else nil
for _, old in {pieces.crystal, pieces.eggPlate.Parent, pieces.sizeBar, pieces.hint, pieces.goal, railFrame, timerFrame} do park(old) end

-- ===== Layout =====
local function touchMode(): boolean
    -- Studio has no touch screen: a Studio-only attribute lets the phone captures use the phone text floor (never read in a live game)
    if RunService:IsStudio() and gui:GetAttribute("PhoneHudTouchTest") == true then return true end
    local ok, preferred = pcall(function() return (UserInputService :: any).PreferredInput end)
    if ok and preferred ~= nil then return preferred == (Enum :: any).PreferredInput.Touch end
    return UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled
end
local function jumpRect(): any?
    local touchGui = player:FindFirstChildOfClass("PlayerGui") and player.PlayerGui:FindFirstChild("TouchGui")
    local jump = if touchGui then touchGui:FindFirstChild("JumpButton", true) else nil
    if not (jump and jump:IsA("GuiObject") and jump.Visible and jump.AbsoluteSize.X > 0) then return nil end
    local origin = gui.AbsolutePosition
    return {x = jump.AbsolutePosition.X - origin.X, y = jump.AbsolutePosition.Y - origin.Y, w = jump.AbsoluteSize.X, h = jump.AbsoluteSize.Y}
end
local lastJump = ""
local lastRunState: any = nil
local testChipRect: any = nil
-- HudCohesion's Studio-only test chip follows the old notice slot; it is held in the top-left corner instead
local function holdTestChip(chip: Instance)
    if chip.Name ~= "TestChip" or not chip:IsA("GuiObject") then return end
    local function fix() if testChipRect then place(chip, testChipRect) end end
    chip:GetPropertyChangedSignal("Position"):Connect(function()
        local r = testChipRect
        if r and chip.Position ~= UDim2.fromOffset(math.floor(r.x + 0.5), math.floor(r.y + 0.5)) then fix() end
    end)
    fix()
end
for _, child in gui:GetChildren() do holdTestChip(child) end
gui.ChildAdded:Connect(function(child) task.defer(holdTestChip, child) end)
local function inner(parent: GuiObject, r: any)
    parent.Position, parent.Size = UDim2.fromOffset(math.floor(r.x + 0.5), math.floor(r.y + 0.5)), UDim2.fromOffset(math.floor(r.w + 0.5), math.floor(r.h + 0.5))
end
-- The banner: the icon and the two lines as ONE group in the middle of the strip (the words decide its width).
local bannerBox: any, bannerText: any = nil, nil
local function textWidth(text: string, size: number): number
    local ok, bounds = pcall(function() return TextService:GetTextSize(text, size, Enum.Font.FredokaOne, Vector2.new(4000, 200)) end)
    return if ok then bounds.X else #text * size * 0.55
end
local function placeBanner()
    local b, T = bannerBox, bannerText
    if b == nil or T == nil then return end
    local lineH, timerH = math.ceil(T.bannerLine * 0.9), math.ceil(T.bannerTimer * 0.9) -- v5: tight lines, the capsule is 11 % h
    local iconS = math.min(b.h * 0.86, b.icon * 1.4)
    local gap = math.max(4, b.h * 0.12)
    local maxText = b.w - iconS - gap - b.h
    local textW = math.min(maxText, math.max(textWidth(bannerLine.Text, T.bannerLine), textWidth(bannerTimer.Text, T.bannerTimer)) + 6)
    local x0 = (b.w - (iconS + gap + textW)) / 2
    inner(bannerIcon, {x = x0, y = (b.h - iconS) / 2, w = iconS, h = iconS})
    local top = (b.h - lineH - timerH) / 2
    inner(bannerLine, {x = x0 + iconS + gap, y = top, w = textW, h = lineH})
    inner(bannerTimer, {x = x0 + iconS + gap, y = top + lineH, w = textW, h = timerH})
end
local function layout()
    local size = gui.AbsoluteSize
    if size.X <= 0 or size.Y <= 0 then return end
    local visibleTiles = {}
    -- owner 2026-11-21 "remove go": at home the rail is the mock's four tiles (a run starts at the island gate); in a run the Home tile
    -- (the home picture) comes back as the way home
    local character = player.Character
    local inRun = character ~= nil and character:GetAttribute("RunState") == "Active"
    for _, o in tileList do
        local show = o.button.Visible and (o ~= home or inRun)
        if o == home then
            home.face.Visible = show
            if not show then put(home, {x = -2000, y = -2000, w = 1, h = 1}) end -- nothing to tap at home
        end
        if show then table.insert(visibleTiles, o) end
    end
    local jump = jumpRect()
    lastJump = if jump then string.format("%d,%d,%d,%d", jump.x, jump.y, jump.w, jump.h) else ""
    local lay = L.compute({W = size.X, H = size.Y, touch = touchMode(), jump = jump, tiles = #visibleTiles, chomp = chomp ~= nil, timers = 3,
        inset = if gui.IgnoreGuiInset then 0 else GuiService:GetGuiInset().Y})
    local u, T = lay.unit, lay.text
    outlinePx = math.max(2, math.floor(0.6 * u + 0.5)) -- 4-5 px at 720 p
    placeOutlines()
    -- banner: icon left, two centred lines
    place(banner, lay.banner)
    bannerBox, bannerText = lay.banner, T
    bannerLine.TextSize, bannerTimer.TextSize = T.bannerLine, T.bannerTimer
    placeBanner()
    -- SIZE plate: the word left, growth on top, health under it (heart beside it)
    place(plate, lay.sizePlate)
    local p = lay.sizePlate
    local wordW = math.ceil(T.sizeWord * L.CharW * 4 + u * 2)
    inner(sizeWord, {x = u, y = 0, w = wordW, h = p.h})
    sizeWord.TextSize = T.sizeWord
    local trackX, trackW = wordW + u * 1.5, p.w - wordW - u * 3
    if combat then
        inner(growthTrack, {x = trackX, y = p.h * 0.16, w = trackW, h = p.h * 0.36})
        inner(heart, {x = trackX, y = p.h * 0.58, w = p.h * 0.3, h = p.h * 0.3})
        inner(healthTrack, {x = trackX + p.h * 0.36, y = p.h * 0.62, w = trackW - p.h * 0.36, h = p.h * 0.22})
    else
        inner(growthTrack, {x = trackX, y = p.h * 0.3, w = trackW, h = p.h * 0.4})
    end
    place(hintLabel, lay.hint)
    hintLabel.TextSize = T.hint
    -- left word buttons: ONE TextSize for both words, the largest that fits the narrower word box (measured with TextService, v5)
    do
        local r = lay.left[1]
        local pad = L.Spec.left.pad * u
        local room = r.w - r.icon - pad * 2 - u
        local size = T.leftWord
        local floor = if lay.touch then L.PhoneFloor else L.MinText
        while size > floor do
            local wide = 0
            for _, text in {"SHOP", "DINOS"} do
                wide = math.max(wide, TextService:GetTextSize(text, size, Enum.Font.FredokaOne, Vector2.new(10000, 10000)).X + 2 * L.Stroke.word)
            end
            if wide <= room then break end
            size -= 1
        end
        T.leftWord = size
    end
    for i, o in {shop, dinos} do
        local r = lay.left[i]
        put(o, r)
        toy(o, r, lay.buttonStroke, 0.29)
        local pad = L.Spec.left.pad * u
        inner(o.holder :: Frame, {x = pad, y = (r.h - r.icon) / 2, w = r.icon, h = r.icon})
        local w = o.word :: TextLabel
        inner(w, {x = pad + r.icon + u, y = -r.h * 0.05, w = r.w - r.icon - pad * 2 - u, h = r.h}) -- right after the icon, a hair high (the lip)
        w.TextSize, w.TextXAlignment = T.leftWord, Enum.TextXAlignment.Left
    end
    -- right tiles (hidden ones keep their last spot: they are not shown)
    for i, o in visibleTiles do
        local r = lay.tiles[i]
        put(o, r)
        toy(o, r, lay.buttonStroke, 0.19)
        local iconS = r.h * 0.76 -- v4: the mock's icons fill about 80 % of the tile height, centred
        inner(o.holder :: Frame, {x = (r.w - iconS) / 2, y = (r.h - iconS) / 2, w = iconS, h = iconS})
        if o.word then
            inner(o.word :: TextLabel, {x = 0, y = 0, w = r.w, h = r.h})
            ;(o.word :: TextLabel).TextSize = T.homeWord
        end
    end
    -- counters
    for _, c in {{crystalsRow, crystalsText, lay.crystals}, {eggsRow, eggsText, lay.eggs}} do
        local row, number, r = c[1] :: Frame, c[2] :: TextLabel, c[3]
        place(row, r)
        inner(row:FindFirstChild("Icon") :: Frame, {x = 0, y = (r.h - r.icon) / 2, w = r.icon, h = r.icon})
        inner(number, {x = r.icon + 1.4 * u, y = 0, w = r.w - r.icon - 1.4 * u, h = r.h})
        number.TextSize = T.counter
        local line = number:FindFirstChildOfClass("UIStroke")
        if line then line.Thickness = math.max(3, math.floor(0.62 * u + 0.5)) end -- 4.5 px at 720 p
    end
    -- potion timers: rows from the bottom up, the words right-aligned against the icon
    place(timers, lay.timers)
    timers:SetAttribute("Row", lay.timers.row)
    timers:SetAttribute("Icon", lay.timers.icon)
    timers:SetAttribute("Gap", lay.timers.gap)
    timers:SetAttribute("TextSize", T.timer)
    shownPotions = "" -- rebuild at the new size
    -- LEAP and CHOMP squares: the icon in the top 60 %, the word under it
    for i, o in {leap, chomp} do
        local r = lay.squares[i]
        if r == nil then continue end
        put(o :: Owned, r)
        local own = o :: Owned
        toy(own, r, math.max(2, math.floor(lay.buttonStroke / 2 + 0.5)), 0.17)
        inner(own.holder :: Frame, {x = r.w * 0.08, y = r.h * 0.0, w = r.w * 0.84, h = r.h * 0.7}) -- v3: the mock's big icon (ref_compare edge layer)
        inner(own.word :: TextLabel, {x = 2, y = r.h * 0.66, w = r.w - 4, h = r.h * 0.3})
        ;(own.word :: TextLabel).TextSize = T.squareWord
    end
    -- the toast lane (Toasts.luau) and the rects other HUD code keeps clear of
    local lane = lay.lane
    gui:SetAttribute("ToastLaneRect", Rect.new(lane.x, lane.y, lane.x + lane.w, lane.y + lane.h))
    gui:SetAttribute("ToastLaneText", T.toast)
    testChipRect = lay.testChip
    local chip = gui:FindFirstChild("TestChip")
    if chip and chip:IsA("GuiObject") then place(chip, lay.testChip) end
    -- FeedbackClient ("Tell us!") and AdminPanel follow these instead of Bootstrap's FeedbackRect / AdminRect
    for name, r in {PhoneHudFeedbackRect = lay.chips.tellUs, PhoneHudAdminRect = lay.chips.admin} do
        gui:SetAttribute(name, Rect.new(r.x, r.y, r.x + r.w, r.y + r.h))
    end
    -- GiftsPanel's Codes button: in the chip row when it fits, else nil (GiftsPanel then keeps its CodesButtonSpot rule)
    local codes = lay.chips.codes
    gui:SetAttribute("PhoneHudCodesSpot", if codes then Rect.new(codes.x, codes.y, codes.x + codes.w, codes.y + codes.h) else nil)
    for _, item in L.persistent(lay) do
        local r = item.rect
        gui:SetAttribute("PhoneHud_" .. item.name, Rect.new(r.x, r.y, r.x + r.w, r.y + r.h))
    end
end
local queued = false
local function queue()
    if queued then return end
    queued = true
    task.defer(function() queued = false layout() end)
end
gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(queue)
for _, o in tileList do o.button:GetPropertyChangedSignal("Visible"):Connect(queue) end
pcall(function() (UserInputService :: any):GetPropertyChangedSignal("PreferredInput"):Connect(queue) end)
gui:GetAttributeChangedSignal("PhoneHudTouchTest"):Connect(queue)
layout()

-- ===== Live values =====
local lastCrystals: number? = nil
local function refreshCrystals()
    local amount = PrivateState.num("Crystals")
    crystalsText.Text = L.counterText(amount)
    if lastCrystals ~= nil and amount > lastCrystals then pop(crystalsPop) end
    lastCrystals = amount
end
PrivateState.onChanged("Crystals", refreshCrystals)
refreshCrystals()

local function rebuildTimers(buffs: any, now: number)
    local ids, rows = {}, {}
    for _, kind in {"speed", "growth", "loot"} do
        local buff = buffs and buffs[kind]
        if buff and buff.expiresAt > now then table.insert(ids, buff.id) table.insert(rows, buff) end
    end
    local key = table.concat(ids, ",")
    if key ~= shownPotions then
        shownPotions = key
        for _, r in timerRows do r:Destroy() end
        timerRows = {}
        local rowH, iconS, gap = timers:GetAttribute("Row") or 24, timers:GetAttribute("Icon") or 24, timers:GetAttribute("Gap") or 2
        for i, buff in rows do
            -- v7 (owner: "famous Roblox experience style timers"; ChatGPT spec): a dark rounded capsule with a big outlined potion icon
            -- and a big countdown, stacked upward; kid words ("3 min", "40 s"), never "2:59" (docs/72)
            local row = box(timers, "Potion" .. i, 6)
            row.AnchorPoint, row.Position, row.Size = Vector2.new(0, 1), UDim2.new(0, 0, 1, -(i - 1) * (rowH + gap)), UDim2.new(1, 0, 0, rowH)
            row.BackgroundColor3, row.BackgroundTransparency = Color3.fromHex("#382C25"), 0.08
            local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, math.floor(rowH * 0.26 + 0.5)) corner.Parent = row
            local edge = Instance.new("UIStroke") edge.Color, edge.Thickness, edge.ApplyStrokeMode = ICON_INK, 3, Enum.ApplyStrokeMode.Border
            edge.Parent = row
            local pulse = Instance.new("UIScale") pulse.Name = "Pulse" pulse.Parent = row
            iconS = math.max(iconS, rowH * 1.2) -- the potion pops out of the capsule, PS99 style
            local pic = PotionArt.icon(row, buff.id, UDim2.fromOffset(iconS, iconS), UDim2.new(0, math.floor(rowH * 0.1), 0.5, 0), 8)
            if pic then
                for _, dir in DIRS do
                    local copy = pic:Clone()
                    copy.Name, copy.ZIndex, copy.ImageColor3 = "Outline", 7, ICON_INK
                    copy.Position = pic.Position + UDim2.fromOffset(math.floor(dir[1] * outlinePx + 0.5), math.floor(dir[2] * outlinePx + 0.5))
                    copy.Parent = row
                end
            end
            local t = word(row, "Time", 9, Color3.new(1, 1, 1))
            t.FontFace, t.TextXAlignment, t.TextSize = UPRIGHT, Enum.TextXAlignment.Left, timers:GetAttribute("TextSize") or 19
            t.Position, t.Size = UDim2.fromOffset(math.floor(rowH * 0.1 + iconS + 6), 0), UDim2.new(1, -math.floor(rowH * 0.1 + iconS + 10), 1, 0)
            row:SetAttribute("ExpiresAt", buff.expiresAt)
            table.insert(timerRows, row)
        end
    end
    for _, row in timerRows do
        local left = (row:GetAttribute("ExpiresAt") or now) - now
        local t = row:FindFirstChild("Time") :: TextLabel?
        if t then
            t.Text = L.duration(left)
            -- under 10 s: yellow-orange, the last 3 s red, and a soft pulse (none with Reduce Motion)
            t.TextColor3 = if left <= 3 then Color3.fromHex("#FF5757") elseif left <= 10 then Color3.fromHex("#FFCB35") else Color3.new(1, 1, 1)
        end
        local pulse = row:FindFirstChild("Pulse") :: UIScale?
        if pulse then
            pulse.Scale = if left <= 10 and Theme.MotionEnabled then 1 + 0.03 * (1 + math.sin(os.clock() * math.pi * 2 / 0.8)) else 1
        end
    end
end

local lastEggs: number? = nil
local lastGrowth = -1
local lastLeapWord = ""
task.spawn(function()
    while root.Parent do
        local now = workspace:GetServerTimeNow()
        local character = player.Character
        local state = if character then character:GetAttribute("RunState") else nil
        local running = state == "Active"
        -- banner
        local id = workspace:GetAttribute("WeatherId") or "clear"
        local endsAt = if id == "clear" then workspace:GetAttribute("NextWeatherAt") else workspace:GetAttribute("WeatherEndsAt")
        local line, timer = L.bannerWords(id, workspace:GetAttribute("WeatherName"), (if typeof(endsAt) == "number" then endsAt else now) - now)
        if bannerLine.Text ~= line or bannerTimer.Text ~= timer then
            bannerLine.Text, bannerTimer.Text = line, timer
            placeBanner()
        end
        if id ~= lastWeather then
            lastWeather = id
            local event = ProgressionRules.item(ProgressionConfig.Weather, id)
            icon(bannerIcon, if event then event.icon or id else "weather")
        end
        -- SIZE plate (run only), growth and health
        plate.Visible = running
        local growth = if character then character:GetAttribute("GrowthScore") else 0
        local fill = HudRules.barFill(growth)
        if math.abs(fill - lastGrowth) > 0.002 then
            lastGrowth = fill
            Theme.animate(growthFill, 0.25, {Size = UDim2.fromScale(fill, 1)})
        end
        if combat and character then
            local byte = character:GetAttribute("HpByte")
            local hp = if typeof(byte) == "number" then math.clamp(byte / 255, 0, 1) else 1
            healthFill.Size = UDim2.fromScale(hp, 1)
            healthFill.BackgroundColor3 = if hp > 0.5 then rgb(A.green) elseif hp > 0.25 then rgb(A.gold) else ORANGE
        end
        -- the first-run goal hint (HudV2 still decides it; parked, so it is drawn here)
        local hint = pieces.hint :: TextLabel?
        hintLabel.Visible = hint ~= nil and hint.Visible and running
        if hint and hintLabel.Text ~= hint.Text then hintLabel.Text = hint.Text end
        -- eggs
        local eggs = if character then character:GetAttribute("CatchScore") else 0
        local eggCount = if typeof(eggs) == "number" then eggs else 0
        eggsText.Text = HudRules.eggsText(eggs)
        if lastEggs ~= nil and eggCount > lastEggs and running then pop(eggsPop) end
        lastEggs = eggCount
        -- potions
        rebuildTimers(PotionChips.lastBuffs, now)
        -- LEAP word: its countdown while it recharges ("3 s"), else LEAP; dimmed while it cannot be used
        local leapText = pieces.leapText :: TextLabel
        local raw = leapText.Text
        local shown = string.match(raw, "(%d+ %a+)$") or "LEAP"
        if shown ~= lastLeapWord then
            lastLeapWord = shown
            ;(leap.word :: TextLabel).Text = shown
        end
        -- v6 (ChatGPT round 2): solid when ready (it was 30 % see-through, the brown read as light taupe); see-through only on cooldown
        leap.face.BackgroundTransparency = if pieces.leap.Active then 0 else 0.45
        if chomp then chomp.face.BackgroundTransparency = if chomp.button.Active then 0 else 0.45 end
        -- the rail changes between home (4 tiles) and a run (Home tile back): lay out again when the run state flips
        if state ~= lastRunState then lastRunState = state queue() end
        -- Home tile: the home picture in a run (hidden at home since owner 2026-11-21)
        local homeWord = L.homeWord(state)
        local hw = home.word :: TextLabel
        hw.Text, hw.Visible = homeWord or "", homeWord ~= nil
        ;(home.holder :: Frame).Visible = homeWord == nil
        -- Roblox moves its jump button when the touch controls appear
        local jump = jumpRect()
        local key = if jump then string.format("%d,%d,%d,%d", jump.x, jump.y, jump.w, jump.h) else ""
        if key ~= lastJump then queue() end
        task.wait(0.2)
    end
end)
