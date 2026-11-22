--!strict
-- BD-1288 slice 1 (owner OK 2026-11-22): the hatch on the stage follows storyboard 1 (docs/evidence/2026-11-22-hatch-storyboard/
-- storyboard-1-normal-flow.jpg). Runs on top of Client/HatchStage (the full-screen stage) and is driven by HatchStageWatch, only while
-- Config.HatchStoryboardEnabled and Config.HatchStageEnabled are on (flag off = this file is never required):
--   1. its own stage: every HUD piece hides (the crystals too), the world blurs, a purple kit bar says "Egg 1 of 3";
--   2. the egg is big (HatchStoryboardRules.EggShare of the screen) on the glowing pedestal; a big green TAP while the egg waits for the tap;
--   3. / 4. the colour splash and the pattern splash each get a big plate with the name in white outlined letters and a rarity chip;
--   5. the build-up: the rays take the rarity colour, the glow grows, the egg shakes (Reduce Motion: the colour only, no shake, no pulse);
--   6. the reveal adds colour + pattern chips and NEW! (new colour / pattern / mutation, or a species not owned before the batch);
--   7. a batch of 2+ eggs ends on a BEST FIND! summary: the best dino big, the others as kit cards, PLAY AGAIN / HOME (the game's own buttons,
--      moved here: they do exactly what they did).
-- The art is the game's own: the Toybox kit (header, buttons, cards), the hatch reveal pieces and rays (docs/77). Nothing is drawn as final art
-- in code; plates and chips use the one chip style (Shared/ChipStyle). Pure numbers: Shared/HatchStoryboardRules (tools/verify_hatch_storyboard.py).
local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local Lighting = game:GetService("Lighting")
local HttpService = game:GetService("HttpService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local R = require(Shared:WaitForChild("HatchStoryboardRules"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Chip = require(Shared:WaitForChild("ChipStyle"))
local Kit = require(Shared:WaitForChild("ToyboxKit"))
local Slots = require(Shared:WaitForChild("AssetSlots"))
local Timeline = require(Shared:WaitForChild("HatchTimeline"))
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))

local SB = {}
local INK = Color3.fromRGB(Kit.Outline[1], Kit.Outline[2], Kit.Outline[3])
local CREAM = Color3.fromRGB(255, 247, 227)
local WHITE = Color3.new(1, 1, 1)
local GREEN = Color3.fromRGB(88, 200, 64)
local PURPLE = Theme.Colors.purple
-- other ScreenGuis that are HUD, not hatch: they step aside while the stage is up (BeDinoUI's own pieces are hidden by HatchStage)
SB.HideGuis = {FriendBonusGui = true, GiftsGui = true, GrowthBanner = true, HubGuideArrow = true, HubPromptBubbleUI = true, PlaytestFeedback = true, TouchGui = true}
SB.Blur = 14 -- px of the world blur behind the stage
SB.Veil = .64 -- the stage veil over the world (HatchStage uses .78): darker, so the egg and the words stand out

local Stage: any = nil
local ctx: any = nil -- one hatch batch on the stage
local known: {[string]: boolean} = {} -- species owned before the batch (refreshed while nothing hatches)

local function refreshKnown()
    if ctx then return end
    local ok, collection = pcall(function() return HttpService:JSONDecode(PrivateState.str("CollectionJson", "{}")) end)
    if not ok or type(collection) ~= "table" then return end
    local rules = require(Shared:WaitForChild("FtueRules"))
    local list: {[string]: boolean} = {}
    for id, entry in collection do
        if type(id) == "string" and rules.collectionCopies({entry}) > 0 then list[id] = true end
    end
    known = list
end

local function reduceMotion(): boolean
    local player = Players.LocalPlayer
    return game:GetService("GuiService").ReducedMotionEnabled == true or (player and player:GetAttribute("ReduceMotion") == true)
end

-- small builders -------------------------------------------------------------------------------------------------------------------
local function add(list: {Instance}, o: Instance): any
    table.insert(list, o)
    return o
end
local function frame(parent: Instance, name: string, cx: number, cy: number, w: number, h: number, z: number): Frame
    local f = Instance.new("Frame")
    f.Name, f.BackgroundTransparency, f.BorderSizePixel, f.AnchorPoint = name, 1, 0, Vector2.new(.5, .5)
    f.Position, f.Size, f.ZIndex = UDim2.fromOffset(cx, cy), UDim2.fromOffset(w, h), z
    f.Parent = parent
    return f
end
local function words(parent: GuiObject, text: string, size: number, color: Color3, outline: Color3?, z: number?): TextLabel
    local l = Instance.new("TextLabel")
    l.Name, l.BackgroundTransparency, l.Size, l.Font = "Words", 1, UDim2.fromScale(1, 1), Enum.Font.FredokaOne
    l.Text, l.TextSize, l.TextColor3, l.ZIndex, l.TextWrapped = text, math.max(R.MinText, size), color, z or (parent.ZIndex + 1), false
    l.TextScaled = true
    local limit = Instance.new("UITextSizeConstraint")
    limit.MaxTextSize, limit.MinTextSize = math.max(R.MinText, size), R.MinText
    limit.Parent = l
    if outline then
        local s = Instance.new("UIStroke")
        s.Color, s.Thickness, s.LineJoinMode = outline, Kit.stroke(size), Enum.LineJoinMode.Round
        s.Parent = l
    end
    l.Parent = parent
    return l
end
local function kitImage(parent: GuiObject, slot: string, z: number): ImageLabel?
    local id = Kit.image(Slots.Images, slot)
    if not id then return nil end
    local image = Instance.new("ImageLabel")
    image.Name, image.BackgroundTransparency, image.Size, image.ZIndex, image.Image = "Kit", 1, UDim2.fromScale(1, 1), z, id
    local asset = Kit.Assets[slot]
    if asset and asset.slice then
        local s = asset.slice
        image.ScaleType, image.SliceCenter = Enum.ScaleType.Slice, Rect.new(s[1], s[2], s[3], s[4])
        image.SliceScale = Kit.sliceScale(slot, parent.AbsoluteSize.X > 0 and parent.AbsoluteSize.X or parent.Size.X.Offset,
            parent.AbsoluteSize.Y > 0 and parent.AbsoluteSize.Y or parent.Size.Y.Offset)
    end
    image.Parent = parent
    return image
end
-- a kit gloss button (Toybox skin) in our own layer; the word stays >= 19 px
local function kitButton(parent: Instance, name: string, text: string, cx: number, cy: number, w: number, h: number, size: number, fill: Color3, z: number): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.AutoButtonColor, b.AnchorPoint = name, text, false, Vector2.new(.5, .5)
    b.Position, b.Size, b.ZIndex, b.BackgroundColor3 = UDim2.fromOffset(cx, cy), UDim2.fromOffset(w, h), z, fill
    b.Font, b.TextSize, b.TextColor3 = Enum.Font.FredokaOne, math.max(R.MinText, size), WHITE
    b.Parent = parent
    local ok, Skin = pcall(require, Shared:WaitForChild("ToyboxSkin"))
    if ok and Skin.ready("button") then
        pcall(Skin.button, b, nil)
    else
        Chip.apply(b, fill, INK)
        local s = Instance.new("UIStroke")
        s.Color, s.Thickness, s.ApplyStrokeMode = INK, 3, Enum.ApplyStrokeMode.Contextual
        s.Parent = b
    end
    return b
end
local function pop(o: GuiObject, delay: number?)
    if reduceMotion() then return end
    local sc = Instance.new("UIScale")
    sc.Scale = .2
    sc.Parent = o
    task.delay(delay or 0, function()
        if sc.Parent then TweenService:Create(sc, TweenInfo.new(.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play() end
    end)
end
local function pulse(o: GuiObject)
    if reduceMotion() then return end
    local sc = Instance.new("UIScale")
    sc.Name = "Pulse"
    sc.Parent = o
    TweenService:Create(sc, TweenInfo.new(.55, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {Scale = 1.07}):Play()
end
local function clear(list: {Instance})
    for i = #list, 1, -1 do local o = list[i] if o then o:Destroy() end end
    table.clear(list)
end

-- geometry -------------------------------------------------------------------------------------------------------------------------
local function screen(): Vector2
    return if ctx then ctx.shade.AbsoluteSize else Vector2.new(1280, 720)
end
-- the egg's centre on the screen (shade coordinates) and its drawn height
local function eggRect(): (Vector2, number)
    local size = screen()
    local egg = ctx and ctx.body:FindFirstChild("PremiumHatchEgg", true)
    local base = ctx.shade.AbsolutePosition
    local centre = Vector2.new(size.X / 2, size.Y * R.EggCentreY)
    if egg and egg:IsA("GuiObject") and egg.AbsoluteSize.X > 0 then centre = egg.AbsolutePosition + egg.AbsoluteSize / 2 - base end
    return centre, size.Y * R.EggShare.want
end
-- the egg's zoom so it is EggShare.want of the screen tall (HatchSequence multiplies its own zoom by the body attribute HatchEggBoost)
local function setBoost()
    if not ctx then return end
    local body = ctx.body
    local design = body.Size.Y.Offset
    if design <= 0 or body.AbsoluteSize.Y <= 0 then return end
    local px = body.AbsoluteSize.Y / design -- screen px per design px of the card (its fit scale included)
    body:SetAttribute("HatchEggBoost", R.eggBoost(R.FlatEggH * px, screen().Y))
end

-- 1. the stage -----------------------------------------------------------------------------------------------------------------------
function SB.init(stage: any)
    Stage = stage
    Stage.HideCrystals = true
    Stage.Veil = SB.Veil
    for k, v in R.Reveal do Stage.Layout[k] = v end
    -- the paint flipbook sits on the big egg (its egg is EggShare.want of the screen tall)
    Stage.eggRect = function(_s: any): any
        if not ctx then return nil end
        local c, h = eggRect()
        return {x = c.X, y = c.Y, side = R.flipbookSide(h / R.EggShare.want)}
    end
    Stage.isNew = function(): boolean
        local e = ctx and ctx.entries[#ctx.entries]
        return e ~= nil and R.isNew(e.newFind, e.newSpecies)
    end
    Stage.revealExtras = function(s: any, plate: any, restore: {() -> ()}, popAt: (GuiObject, number) -> ()) SB.revealChips(s, plate, restore, popAt) end
    Stage.onEnds = function(s: any, ends: GuiObject, restore: {() -> ()}) SB.ends(s, ends, restore) end
    Stage.onRestore = function() SB.finish() end
    refreshKnown()
    PrivateState.onChanged("CollectionJson", function() refreshKnown() end)
end

function SB.begin(p: any)
    SB.finish()
    local gui: ScreenGui = p.gui
    local layer = Instance.new("ScreenGui")
    layer.Name, layer.ResetOnSpawn, layer.DisplayOrder, layer.IgnoreGuiInset = "HatchStoryboardUI", false, gui.DisplayOrder + 1, gui.IgnoreGuiInset
    pcall(function() (layer :: any).ScreenInsets = (gui :: any).ScreenInsets end)
    layer.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    layer.Parent = gui.Parent
    ctx = {gui = gui, shade = p.shade, panel = p.panel, body = p.body, layer = layer, restore = {}, egg = {}, words = {}, entries = {}, conns = {},
        total = nil, index = nil, buildTween = nil, summary = false, seen = {}}
    local restore = ctx.restore
    -- the world blurs behind the stage
    local blur = Instance.new("BlurEffect")
    blur.Name, blur.Size = "HatchStoryboardBlur", SB.Blur
    blur.Parent = Lighting
    table.insert(restore, function() blur:Destroy() end)
    -- HUD in other ScreenGuis steps aside (BeDinoUI's own HUD is hidden by HatchStage)
    local playerGui = gui.Parent
    if playerGui then
        for _, g in playerGui:GetChildren() do
            if g:IsA("ScreenGui") and SB.HideGuis[g.Name] and g.Enabled then
                g.Enabled = false
                local conn = g:GetPropertyChangedSignal("Enabled"):Connect(function() if ctx and g.Enabled then g.Enabled = false end end)
                table.insert(restore, function() conn:Disconnect() if g.Parent then g.Enabled = true end end)
            end
        end
    end
    -- the purple kit bar with "Egg 1 of 3" (the counter HatchSequence writes stays hidden; its words come here)
    local size = screen()
    local bar = R.topBar(size.X, size.Y)
    local strip = frame(layer, "StoryboardBar", size.X / 2, bar.h / 2, size.X + 8, bar.h, 2)
    if not kitImage(strip, "toybox_header_purple", 2) then
        strip.BackgroundTransparency, strip.BackgroundColor3 = 0, PURPLE
    end
    local chip = frame(strip, "CounterChip", (size.X + 8) / 2, bar.h / 2, bar.chipW, bar.chipH, 4)
    chip.BackgroundTransparency = 0
    Chip.apply(chip, CREAM, INK)
    local counterWords = words(chip, "", bar.text, INK, nil, 5)
    local title = words(strip, "", bar.titleText, WHITE, INK, 5)
    title.Name, title.Visible = "Title", false
    ctx.bar, ctx.barChip, ctx.barWords, ctx.barTitle = strip, chip, counterWords, title
    chip.Visible = false
    local function mirror(o: Instance)
        if o.Name ~= "EggCounter" or not o:IsA("TextLabel") then return end
        local function sync()
            if not ctx then return end
            local i, n = R.counter(o.Text)
            ctx.index, ctx.total = i, n
            counterWords.Text = o.Text
            chip.Visible = i ~= nil and not ctx.summary
            if o.Visible then o.Visible = false end
        end
        table.insert(ctx.conns, o:GetPropertyChangedSignal("Text"):Connect(sync))
        table.insert(ctx.conns, o:GetPropertyChangedSignal("Visible"):Connect(function() if ctx and o.Visible then o.Visible = false end end))
        sync()
    end
    for _, o in p.panel:GetDescendants() do mirror(o) end
    table.insert(ctx.conns, p.panel.DescendantAdded:Connect(function(o) task.defer(mirror, o) end))
    -- the TAP while the egg waits (HatchSequence: body attribute HatchTapWait)
    table.insert(ctx.conns, p.body:GetAttributeChangedSignal("HatchTapWait"):Connect(function() SB.tapState() end))
    SB.newEgg()
end

-- 2. the egg on its pedestal, the TAP -----------------------------------------------------------------------------------------------
function SB.newEgg()
    if not ctx then return end
    clear(ctx.egg)
    clear(ctx.words)
    if ctx.buildTween then ctx.buildTween:Cancel() ctx.buildTween = nil end
    ctx.colourShown, ctx.patternShown, ctx.built = false, false, false
    ctx.bar.Visible = not ctx.summary
    setBoost()
    task.defer(function()
        if not ctx then return end
        setBoost() -- the body has its final fit scale one frame later
        local c, h = eggRect()
        local size = screen()
        local ped = R.eggPedestal(size.X, size.Y, c.Y, h)
        local s = Stage.parts and Stage.parts()
        if s and Stage.Art and Stage.Art.pedestal then
            local pedestal = Instance.new("ImageLabel")
            pedestal.Name, pedestal.BackgroundTransparency, pedestal.Image, pedestal.ScaleType = "StoryboardEggPedestal", 1, Stage.Art.pedestal, Enum.ScaleType.Fit
            pedestal.AnchorPoint, pedestal.Position, pedestal.Size = Vector2.new(.5, .5), UDim2.fromOffset(c.X, ped.cy), UDim2.fromOffset(ped.w, ped.h)
            pedestal.ImageColor3, pedestal.ZIndex = Color3.fromRGB(180, 235, 255), s.panel.ZIndex - 1 -- behind the egg (the shade draws under the panel)
            pedestal.Parent = s.shade
            add(ctx.egg, pedestal)
        end
        SB.tapState()
    end)
end
function SB.tapState()
    if not ctx then return end
    local waiting = ctx.body:GetAttribute("HatchTapWait") == true
    local tap = ctx.tap
    if waiting and not tap then
        local c, h = eggRect()
        local size = screen()
        local spec = R.tapButton(size.X, size.Y, c.Y, h)
        tap = kitButton(ctx.layer, "StoryboardTap", R.Words.tap, spec.cx, spec.cy, spec.w, spec.h, spec.text, GREEN, 20)
        ctx.tap = tap
        pulse(tap)
        tap.Activated:Connect(function()
            -- the same tap as on the egg (HatchSequence's StageTap): it opens the waiting egg
            local catcher = ctx and ctx.gui:FindFirstChild("HatchTapCatcher")
            local fire = catcher and catcher:FindFirstChild("StageTap", true)
            if fire and fire:IsA("BindableEvent") then fire:Fire() end
        end)
        pop(tap)
    elseif not waiting and tap then
        ctx.tap = nil
        tap:Destroy()
    end
end

-- 3. / 4. the colour and the pattern: a big plate with the name and a rarity chip -----------------------------------------------------
local function plate(kind: string, word: string, tier: number, fill: Color3)
    if not ctx then return end
    clear(ctx.words)
    local c, h = eggRect()
    local size = screen()
    local spec = R.label(size.X, size.Y, c.X, c.Y, h, word)
    local p = frame(ctx.layer, "Storyboard" .. kind, spec.plate.cx, spec.plate.cy, spec.plate.w, spec.plate.h, 10)
    p.BackgroundTransparency = 0
    Chip.apply(p, fill, INK)
    words(p, word, spec.plate.text, WHITE, INK, 12)
    add(ctx.words, p)
    local t = math.clamp(tier, 1, 6)
    local chip = frame(ctx.layer, "Storyboard" .. kind .. "Tier", spec.chip.cx, spec.chip.cy, spec.chip.w, spec.chip.h, 10)
    chip.BackgroundTransparency = 0
    Chip.apply(chip, Theme.RarityColors[t], INK)
    words(chip, R.tierWord(Timeline.TierNames[t]), spec.chip.text, WHITE, INK, 12)
    add(ctx.words, chip)
    pop(p)
    pop(chip, .08)
end
function SB.colour()
    if not ctx or ctx.colourShown then return end
    ctx.colourShown = true
    local body = ctx.body
    local fill = body:GetAttribute("HatchColourRgb")
    plate("Colour", R.colourWord(body:GetAttribute("HatchColourName")), body:GetAttribute("HatchColourTier") or 1, if typeof(fill) == "Color3" then fill else WHITE)
    local mine = ctx
    task.delay(R.Hold.colour + .6, function() -- no pattern bucket came (a plain v2 egg): the build-up starts anyway
        if ctx == mine and not ctx.patternShown then SB.buildUp() end
    end)
end
function SB.pattern()
    if not ctx or ctx.patternShown then return end
    ctx.patternShown = true
    local body = ctx.body
    local name = body:GetAttribute("HatchPatternName")
    local fill = body:GetAttribute("HatchPatternRgb")
    plate("Pattern", R.patternWord(name, name == ""), body:GetAttribute("HatchPatternTier") or 1, if typeof(fill) == "Color3" then fill else WHITE)
    local mine = ctx
    task.delay(R.Hold.pattern, function() if ctx == mine then SB.buildUp() end end)
end

-- 5. the build-up: rays in the rarity colour, a growing glow, the shake (Legendary and up keep HatchStage's own gold build-up) -----------
function SB.buildUp()
    if not ctx or ctx.built then return end
    ctx.built = true
    clear(ctx.words)
    local s = Stage.parts and Stage.parts()
    local rank = ctx.body:GetAttribute("HatchStageRarity")
    rank = if type(rank) == "number" and rank > 0 then rank else 1
    local look = R.buildUpLook(rank, reduceMotion())
    if s and look.own then
        local tint = Theme.RarityColors[math.clamp(rank, 1, 6)]:Lerp(WHITE, look.lerpWhite)
        s.sun.ImageColor3, s.sun.ImageTransparency = tint, look.raysTo
        s.glow.ImageColor3 = tint
        local grow = UDim2.fromOffset(760 * look.glowGrow, 760 * look.glowGrow)
        if reduceMotion() then
            s.glow.ImageTransparency = look.glowTo
        else
            if s.breathe then s.breathe:Cancel() end
            ctx.buildTween = TweenService:Create(s.glow, TweenInfo.new(R.BuildUp + Timeline.anticipation(rank), Enum.EasingStyle.Quad, Enum.EasingDirection.In),
                {Size = grow, ImageTransparency = look.glowTo})
            ctx.buildTween:Play()
        end
    elseif s then
        pcall(Stage.buildUp)
    end
    pcall(Stage.crackCharge) -- the egg shakes and a white glow swells (it does nothing with Reduce Motion)
end

-- 6. the reveal --------------------------------------------------------------------------------------------------------------------------
local function plain(text: string?): string
    return (string.gsub(string.gsub(text or "", "<[^>]->", ""), "^%s*(.-)%s*$", "%1"))
end
function SB.reveal(info: any)
    if not ctx then return end
    clear(ctx.words)
    if ctx.tap then ctx.tap:Destroy() ctx.tap = nil end
    if ctx.buildTween then ctx.buildTween:Cancel() ctx.buildTween = nil end
    clear(ctx.egg)
    ctx.bar.Visible = false -- the rarity ribbon takes the top of the screen
    local body = ctx.body
    local id = body:GetAttribute("HatchSpeciesId")
    id = if type(id) == "string" and id ~= "" then id else nil
    local failed = info.failed == true
    local newSpecies = false
    if id and not failed then
        newSpecies = not known[id] and not ctx.seen[id]
        ctx.seen[id] = true
    end
    local entry = {rarity = if failed then 0 else info.rarity, name = plain(info.nameLabel and info.nameLabel.Text), speciesId = id, failed = failed,
        newFind = body:GetAttribute("HatchNewFind") == true, newSpecies = newSpecies, colour = body:GetAttribute("HatchColourRgb"),
        colourName = body:GetAttribute("HatchColourName"), patternName = body:GetAttribute("HatchPatternName"), patternColour = body:GetAttribute("HatchPatternRgb"),
        fast = body:GetAttribute("HatchFast") == true}
    table.insert(ctx.entries, entry)
    -- keep a copy of the dino view for the BEST FIND! summary (the model loads a moment after the burst)
    task.spawn(function()
        local mine = ctx
        for _ = 1, 20 do
            task.wait(.15)
            if ctx ~= mine or failed then return end
            local view = body:FindFirstChild("DinosaurPreview", true)
            if view and view:IsA("ViewportFrame") and view:FindFirstChildOfClass("WorldModel") then
                local ok, copy = pcall(function() return view:Clone() end)
                if ok and copy then entry.view = copy end
                return
            end
        end
    end)
end
-- the colour and pattern chips under the name plate (Stage.reveal calls this instead of drawing its colour dots)
function SB.revealChips(s: any, plateRect: any, restore: {() -> ()}, popAt: (GuiObject, number) -> ())
    local e = ctx and ctx.entries[#ctx.entries]
    if not e or e.failed then return end
    local size = s.shade.AbsoluteSize
    local spec = R.revealChips(size.X, size.Y)
    local items = {}
    if type(e.colourName) == "string" and e.colourName ~= "" then table.insert(items, {e.colourName, e.colour}) end
    table.insert(items, {if type(e.patternName) == "string" and e.patternName ~= "" then e.patternName else "Plain", e.patternColour})
    local widths, total = {}, 0
    for i, item in items do
        widths[i] = R.chipWidth(item[1], spec.text, spec.swatch)
        total += widths[i] + (if i > 1 then spec.gap else 0)
    end
    local x = plateRect.x - total / 2
    for i, item in items do
        local w = widths[i]
        local chip = Instance.new("Frame")
        chip.Name, chip.AnchorPoint, chip.BackgroundTransparency = "StoryboardRevealChip" .. i, Vector2.new(0, .5), 0
        chip.Position, chip.Size, chip.ZIndex = UDim2.fromOffset(x, spec.y), UDim2.fromOffset(w, spec.h), s.panel.ZIndex + 31
        Chip.apply(chip, CREAM, INK)
        local sw = Chip.swatch(chip, spec.swatch, nil, chip.ZIndex + 1)
        sw.AnchorPoint, sw.Position = Vector2.new(0, .5), UDim2.new(0, 8, .5, 0)
        sw.BackgroundColor3 = if typeof(item[2]) == "Color3" then item[2] else WHITE
        local label = Instance.new("TextLabel")
        label.BackgroundTransparency, label.Font, label.Text, label.TextColor3 = 1, Enum.Font.FredokaOne, item[1], INK
        label.TextSize, label.ZIndex, label.TextXAlignment = spec.text, chip.ZIndex + 1, Enum.TextXAlignment.Left
        label.Position, label.Size = UDim2.fromOffset(spec.swatch + 16, 0), UDim2.new(1, -(spec.swatch + 20), 1, 0)
        label.Parent = chip
        chip.Parent = s.shade
        table.insert(restore, function() chip:Destroy() end)
        popAt(chip, .18 + i * .06)
        x += w + spec.gap
    end
end

-- 7. the end of a batch: NEXT on the last egg opens the BEST FIND! summary, which holds the game's PLAY AGAIN / HOME -------------------
function SB.ends(s: any, ends: GuiObject, restore: {() -> ()})
    if not ctx or ctx.summary or ctx.next or not R.wantsSummary(ctx.total) or #ctx.entries < 2 then return end
    -- PLAY AGAIN / HOME wait off screen (still the game's buttons: Enter / A still means PLAY AGAIN) until the summary shows them
    local before = ends.Position
    ends.Position = before + UDim2.fromOffset(0, 4000)
    table.insert(restore, function() if ends.Parent == s.body or ends:IsDescendantOf(s.body) then ends.Position = before end end)
    ctx.ends, ctx.endsPosition = ends, before
    local size = s.shade.AbsoluteSize
    local fitY = math.min(1, size.Y / 793)
    local b = kitButton(ctx.layer, "StoryboardNext", R.Words.next, size.X / 2, size.Y * R.Reveal.nextY, 250 * fitY, math.max(44, 66 * fitY), math.max(R.MinText + 3, math.floor(34 * fitY)), GREEN, 20)
    ctx.next = b
    pop(b, .05)
    b.Activated:Connect(function() SB.summary() end)
end
local function dinoView(entry: any, parent: GuiObject, w: number, h: number, z: number)
    local view: ViewportFrame? = nil
    if entry.view then
        view = entry.view
    elseif entry.speciesId then
        local ok, made = pcall(function() return require(Shared:WaitForChild("DinosaurPreview")).add(parent, entry.speciesId, "base") end)
        if ok then view = made end
    end
    if not view then return end
    for _, d in view:GetChildren() do
        if d:IsA("UIScale") or d:IsA("GuiObject") then d:Destroy() end
    end
    if not view.CurrentCamera then view.CurrentCamera = view:FindFirstChildOfClass("Camera") end
    view.AnchorPoint, view.Position, view.Size, view.ZIndex, view.Visible = Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromOffset(w, h), z, true
    view.ImageTransparency, view.Rotation = 0, 0
    view.Parent = parent
end
function SB.summary()
    if not ctx or ctx.summary then return end
    ctx.summary = true
    if ctx.next then ctx.next:Destroy() ctx.next = nil end
    local s = Stage.parts and Stage.parts()
    if s and s.reveal then Stage.clearReveal(s) end
    -- the last dino's own reveal steps aside (the panel holds it); the stage veil, rays and blur stay
    local panel = ctx.panel
    if panel.Visible then
        panel.Visible = false
        table.insert(ctx.restore, function() if panel.Parent then panel.Visible = true end end)
    end
    local layer = ctx.layer
    local size = screen()
    local entries = {}
    for _, e in ctx.entries do if not e.failed then table.insert(entries, e) end end
    if #entries == 0 then entries = ctx.entries end
    local bestIndex = R.best(entries)
    local best = entries[bestIndex]
    local others = {}
    for i, e in entries do if i ~= bestIndex then table.insert(others, e) end end
    local L = R.summary(size.X, size.Y, #others)
    -- a still blocker: a tap on the summary is never a tap on the egg behind it
    local blocker = frame(layer, "StoryboardSummary", size.X / 2, size.Y / 2, size.X, size.Y, 1)
    blocker.Active = true
    -- the bar: BEST FIND!
    ctx.bar.Visible = true
    ctx.barChip.Visible = false
    ctx.barTitle.Text, ctx.barTitle.Visible = R.Words.best, true
    -- the best dino big, on the pedestal, with its rarity ribbon and name plate (the hatch reveal pieces)
    if best then
        local rank = math.clamp(best.rarity or 1, 1, 6)
        local tint = Theme.RarityColors[rank]
        local big = frame(blocker, "Best", L.big.cx, L.big.cy, L.big.h * 1.1, L.big.h, 3)
        local ped = Instance.new("ImageLabel")
        ped.Name, ped.BackgroundTransparency, ped.Image, ped.ScaleType = "Pedestal", 1, Stage.Art.pedestal, Enum.ScaleType.Fit
        ped.AnchorPoint, ped.Position, ped.Size, ped.ZIndex = Vector2.new(.5, .5), UDim2.new(.5, 0, 1, -L.big.h * .06), UDim2.fromOffset(L.big.h * .8, L.big.h * .4), 3
        ped.ImageColor3 = tint:Lerp(WHITE, .35)
        ped.Parent = big
        local glow = Instance.new("ImageLabel")
        glow.Name, glow.BackgroundTransparency, glow.Image = "Glow", 1, require(Shared:WaitForChild("EffectAssets")).Requested.glowPlate.id
        glow.AnchorPoint, glow.Position, glow.Size, glow.ZIndex = Vector2.new(.5, .5), UDim2.fromScale(.5, .45), UDim2.fromOffset(L.big.h * 1.5, L.big.h * 1.5), 2
        glow.ImageColor3, glow.ImageTransparency = tint:Lerp(WHITE, .3), .25
        glow.Parent = big
        dinoView(best, big, L.big.h * 1.05, L.big.h * .82, 4)
        local bw = math.min(L.big.h * 1.05, size.X * .3)
        local ribbon = Instance.new("ImageLabel")
        ribbon.Name, ribbon.BackgroundTransparency, ribbon.Image, ribbon.ScaleType = "Ribbon", 1, Stage.Art.ribbon, Enum.ScaleType.Fit
        ribbon.AnchorPoint, ribbon.Position, ribbon.Size, ribbon.ZIndex = Vector2.new(.5, .5), UDim2.new(.5, 0, 0, 0), UDim2.fromOffset(bw, bw * 167 / 444), 6
        ribbon.ImageColor3 = tint:Lerp(WHITE, .12)
        ribbon.Parent = big
        local word = words(ribbon, R.tierWord(Timeline.TierNames[rank]), math.floor(bw * .12), WHITE, INK, 7)
        word.Position, word.Size, word.AnchorPoint = UDim2.fromScale(.5, .4), UDim2.fromScale(.66, .5), Vector2.new(.5, .5)
        local pw = math.min(L.big.h * .75, size.X * .22)
        local namePlate = Instance.new("ImageLabel")
        namePlate.Name, namePlate.BackgroundTransparency, namePlate.Image, namePlate.ScaleType = "NamePlate", 1, Stage.Art.plate, Enum.ScaleType.Fit
        namePlate.AnchorPoint, namePlate.Position, namePlate.Size, namePlate.ZIndex = Vector2.new(.5, .5), UDim2.new(.5, 0, 1, L.big.h * .04), UDim2.fromOffset(pw, pw * 137 / 439), 6
        namePlate.Parent = big
        local nameWords = words(namePlate, best.name or "", math.floor(pw * 137 / 439 * .5), INK, nil, 7)
        nameWords.Position, nameWords.Size, nameWords.AnchorPoint = UDim2.fromScale(.5, .47), UDim2.fromScale(.8, .62), Vector2.new(.5, .5)
        pop(big)
    end
    -- the others as kit cards in their rarity
    for i, cell in L.cards do
        local card = frame(blocker, "Card" .. i, cell.cx, cell.cy, cell.w, cell.h, 3)
        local e = others[i]
        if i > L.shown or not e then
            card.BackgroundTransparency = 0
            Chip.apply(card, CREAM, INK)
            words(card, "+" .. L.more, math.floor(cell.w * .3), INK, nil, 5)
        else
            local rank = math.clamp(e.rarity or 1, 1, 6)
            if not kitImage(card, "toybox_card_" .. Kit.CardRarities[rank], 3) then
                card.BackgroundTransparency = 0
                Chip.apply(card, Theme.RarityColors[rank]:Lerp(WHITE, .5), INK)
            end
            local holder = frame(card, "Dino", cell.w / 2, cell.h * .38, cell.w * .9, cell.h * .58, 4)
            dinoView(e, holder, cell.w * .9, cell.h * .58, 5)
            local name = frame(card, "Name", cell.w / 2, cell.h * .74, cell.w * .94, L.cardText + 6, 6)
            words(name, e.name or "", L.cardText, WHITE, INK, 7)
            local chipH = L.chipText + 10
            local tier = frame(card, "Tier", cell.w / 2, cell.h - chipH / 2 - cell.h * .04, math.min(cell.w * .9, R.wordWidth("UNCOMMON", L.chipText) + 14), chipH, 6)
            tier.BackgroundTransparency = 0
            Chip.apply(tier, Theme.RarityColors[rank], INK)
            words(tier, R.tierWord(Timeline.TierNames[rank]), L.chipText, WHITE, INK, 7)
        end
        pop(card, .1 + i * .06)
    end
    -- PLAY AGAIN (green) / HOME (purple): the game's own buttons, moved onto the summary (they do exactly what they did)
    local ends = ctx.ends
    if ends and ends.Parent then
        local home, parent, before = ends.Parent, ends.Parent, ctx.endsPosition
        local k = if ctx.body.Size.X.Offset > 0 then ctx.body.AbsoluteSize.X / ctx.body.Size.X.Offset else 1
        local scale = Instance.new("UIScale")
        scale.Name, scale.Scale = "StoryboardScale", math.max(.5, k)
        scale.Parent = ends
        ends.Parent = layer
        ends.AnchorPoint, ends.Position, ends.ZIndex = Vector2.new(.5, .5), UDim2.fromOffset(size.X / 2, L.buttonsY), 30
        for _, b in ends:GetDescendants() do
            if b:IsA("GuiObject") then b.ZIndex = math.max(b.ZIndex, 31) end
            if b:IsA("TextButton") and b.Name == "End_home" then b.BackgroundColor3 = PURPLE end
        end
        table.insert(ctx.restore, function()
            scale:Destroy()
            if ends.Parent == layer and home.Parent then ends.Parent = parent ends.Position = before end
        end)
    end
end

-- next egg / the stage closes -------------------------------------------------------------------------------------------------------
function SB.nextEgg()
    if not ctx then return end
    if ctx.next then ctx.next:Destroy() ctx.next = nil end
    SB.newEgg()
end
function SB.finish()
    local c = ctx
    if not c then return end
    ctx = nil
    for _, conn in c.conns do conn:Disconnect() end
    clear(c.egg)
    clear(c.words)
    if c.buildTween then c.buildTween:Cancel() end
    for i = #c.restore, 1, -1 do pcall(c.restore[i]) end
    if c.body.Parent then c.body:SetAttribute("HatchEggBoost", nil) end
    c.layer:Destroy()
    refreshKnown()
end
SB.reduceMotion = reduceMotion
SB.enabled = Config.HatchStoryboardEnabled == true and Config.HatchStageEnabled == true
return SB
