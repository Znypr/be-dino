-- Offline small-window smoke (BD-1067, docs/195; driven by tools/verify_small_window.py).
-- The REAL ModalCompact, PhoneScale, EggsScreen and HatchSequence run in the same geometry mock as tools/close_paths_smoke.luau (the datatypes and
-- instances are copied in by the verifier at the marker line below), inside a tree shaped like Bootstrap's modal (ScreenGui > ModalScrim > panel + UIScale >
-- header, body). The panel is laid out by ModalCompact exactly as in the game, then the screen is drawn, then ModalCompact's floor pass runs.
-- Every size is a ScreenGui AbsoluteSize (the Studio window minus the top bar). The checks read the absolute rectangles:
--   * nothing a player must read or press is outside the visible body (the scroller), so nothing is cut and nothing needs a scroll,
--   * the nest header and the hint line never touch the nest slots, the OPEN EGG and AUTO buttons never touch each other or the card edge,
--   * buttons are at least 44 px and text at least 14 px on screen (text that is shrunk to fit is judged at its largest size).
-- It proves layout numbers in a mock. It shows nothing about drawing, the real font or Studio.
-- @@PREFIX@@

local sources = MODULE_SOURCES
local loaded, stubs = {}, {}
local failures = 0
local function check(ok, message)
    if not ok then failures += 1 print("FAIL " .. message) end
    return ok
end
function methods.FindFirstAncestorOfClass(self, class)
    local cur = rawget(self, "__p").Parent
    while cur do
        if rawget(cur, "__p").ClassName == class then return cur end
        cur = rawget(cur, "__p").Parent
    end
    return nil
end
function methods.GetPropertyChangedSignal(self, property) -- one signal per property, so the harness can fire it like the engine does
    local e = rawget(self, "__ev")
    e["prop:" .. property] = e["prop:" .. property] or signal()
    return e["prop:" .. property]
end
events.DescendantAdded, events.ChildAdded = true, true -- the real ModalCompact listens; the mock never fires them (the verifier runs the floor pass by hand)
workspace = {GetServerTimeNow = function() return 1000 end}

local Theme = {MotionEnabled = true, Colors = {panel = color(.2, .2, .2), card = color(.3, .3, .3), outline = color(0, 0, 0), text = color(1, 1, 1), gold = color(1, 1, 0),
    purple = color(1, 0, 1), accent = color(0, 1, 0), blue = color(0, 0, 1), red = color(1, 0, 0)},
    RarityColors = {color(.6, .6, .6), color(.3, .8, .3), color(.3, .5, 1), color(.7, .3, 1), color(1, .8, .2), color(1, .3, .3)},
    ImageIds = {paint_bucket = "", egg_splat = "", egg_shell = ""}, TextStyle = {apply = function() return inst("UIStroke") end, outlined = function() return inst("UIStroke") end}}
function Theme.decorate() end
function Theme.icon() return nil end
function Theme.animate(target, _, goals) for k, v in goals do target[k] = v end end
stubs.UITheme = Theme
stubs.EggPicture = {
    add = function(parent, _, size) return inst("ImageLabel", "Egg", parent, {Size = UDim2.fromOffset(size, size), ZIndex = parent.ZIndex + 1}) end,
    stage = function(parent, w, h) return inst("Frame", "Stage", parent, {Size = UDim2.fromOffset(w, h), ZIndex = parent.ZIndex + 1}) end,
}
stubs.ConditionStage = {hero = function() return nil end}
stubs.FxUi = {mount = function() return nil end}
stubs.FusionSelection = {eggSlotLook = function() return "plain" end}
stubs.ChipStyle = nil
local clientNames = {IndexTabs = true, PatternColourCards = true, PatternColourDetail = true, ModalCompact = true, EggsScreen = true, EggPicture = true, ConditionStage = true, HatchSequence = true, ModalClose = true, InspectView = true,
    HatchFx = true, MutationReveal = true, HatchEggV2 = true, PrivateState = true}
-- BD-1107: a class badge like the real one: an icon and the class word (the real root grows to the right with its word, anchored by its left edge here)
stubs.ClassBadge = {create = function(parent, _, size)
    local root = inst("Frame", "ClassBadge", parent, {Size = UDim2.fromOffset(size, size)})
    inst("ImageLabel", "Icon", root, {Size = UDim2.fromOffset(size, size)})
    inst("TextLabel", "ClassWord", root, {Text = "Ground", TextSize = math.max(14, math.floor(size * .5)), Size = UDim2.fromOffset(0, size)})
    return root
end}
local NEW_WORDS = {} -- BD-1107: the "New pattern!" / "New colour!" ribbon words of the stage being played
stubs.Sfx = {play = function() end, playLayers = function() end, playCue = function() end, revealName = function() return "hatch_reveal" end}
stubs.SfxRules = {hatchCues = function(cues) return cues end}
stubs.InspectView = {attach = function() return {destroy = function() end, wasDrag = function() return false end} end}
stubs.HatchFx = {ensure = function() return {} end, begin = function() return {} end, update = function() end, hide = function() end, style = function() end, rainbow = function() end,
    splash = function() end, paintStyle = function() end}
stubs.PatternColourIndex = {ribbons = function() return NEW_WORDS end, Tabs = {"dinos", "patterns", "colours"}, TabNames = {dinos = "Dinos", patterns = "Patterns", colours = "Colours"},
    validTab = function(t) return t end, foundSets = function() return {patterns = {}, colours = {}} end, foundTotal = function() return 0 end, dotVisible = function() return false end,
    seenBaseline = function() return 0 end, cards = function() return {} end, header = function() return {text = ""} end}
stubs.PrivateState = {str = function(_, fallback) return fallback or "" end, isReady = function() return true end, onChanged = function() end}
-- BD-1083 / BD-1082: the REAL IndexTabs runs here; the cards and the detail it draws are checked elsewhere (verify_pattern_colour_index.py)
stubs.PatternColourCards = {build = function() end}
stubs.PatternColourDetail = {open = function() end}
stubs.SettingsModel = {set = function() end, indexSeen = function() return nil end, onChange = function() end}
stubs.AssetSlots = {image = function() return nil end}
stubs.SecretSpeciesConfig = {indexOrder = function(base) return base end, name = function(id) return id end}
stubs.NavigationArtwork = {collection = "dinos"}
stubs.MutationReveal = {begin = function() return {} end, update = function() end, hide = function() end}
stubs.HatchEggV2 = {create = function() return nil end, stop = function() end}
Services.HttpService = {JSONDecode = function() return {} end}
Services.TweenService = {Create = function(_, target, _, goals) return {Play = function() for k, v in goals do target[k] = v end end, Cancel = function() end, Completed = signal()} end}
Services.UserInputService = {InputBegan = inputBegan}
-- BD-1153: the pop-in cases play the tweens over their duration (frame by frame, linear) instead of jumping to the goal, so a ribbon, tag or chip really passes through
-- UIScale 0 .. 1 while ModalCompact's floor pass runs, like in the engine. POPIN is off for every other check of this file (they judge the settled picture).
local POPIN = false
do
    local instant = Services.TweenService.Create
    Services.TweenService.Create = function(self, target, info, goals)
        if not POPIN then return instant(self, target, info, goals) end
        local duration = math.max((info and info.Time) or 0, 1 / 30)
        local conn = nil
        local tween = {Completed = signal()}
        function tween.Cancel() if conn then conn:Disconnect() conn = nil end end
        function tween.Play()
            local from = {}
            for key in goals do from[key] = target[key] end
            local t = 0
            conn = heartbeat:Connect(function(dt)
                t += dt
                local k = math.min(1, t / duration)
                for key, goal in goals do
                    if type(goal) == "number" and type(from[key]) == "number" then target[key] = from[key] + (goal - from[key]) * k elseif k >= 1 then target[key] = goal end
                end
                if k >= 1 then tween.Cancel() tween.Completed:Fire() end
            end)
        end
        return tween
    end
end
local function register(name)
    local m = Instance.new("ModuleScript") m.Name = name
    m.Parent = if clientNames[name] then ClientFolder else SharedFolder
end
for name in sources do register(name) end
for name in stubs do register(name) end
local function requireModule(m)
    local name = m.Name
    if stubs[name] then return stubs[name] end
    if loaded[name] == nil then loaded[name] = sources[name](m, requireModule) end
    return loaded[name]
end
local PhoneScale = requireModule(SharedFolder.PhoneScale)
local ModalCompact = requireModule(ClientFolder.ModalCompact)
local EggsScreen = requireModule(ClientFolder.EggsScreen)
local Hatch = requireModule(ClientFolder.HatchSequence)
local EggsLogicCopy = requireModule(SharedFolder.FtueP1)
local function frames(n, dt) for _ = 1, n do now += dt or 1 / 30 runDue() heartbeat:Fire(dt or 1 / 30) end end

-- ===== geometry helpers =====
local function rectOf(o) return {x = o.AbsolutePosition.X, y = o.AbsolutePosition.Y, w = o.AbsoluteSize.X, h = o.AbsoluteSize.Y} end
local function inside(r, box, slack) slack = slack or .75 return r.x >= box.x - slack and r.y >= box.y - slack and r.x + r.w <= box.x + box.w + slack and r.y + r.h <= box.y + box.h + slack end
local function overlaps(a, b) return a.x < b.x + b.w - .5 and b.x < a.x + a.w - .5 and a.y < b.y + b.h - .5 and b.y < a.y + a.h - .5 end
local function scaleAt(o) local _, _, k = layout(o) return k end -- cumulative UIScale of o and its parents (own scale already inside the size)
local function describe(r) return string.format("%d,%d %dx%d", r.x + .5, r.y + .5, r.w + .5, r.h + .5) end

-- ===== a modal shaped like Bootstrap's, laid out by the real ModalCompact =====
local function buildModal(viewW, viewH)
    loaded.ModalCompact = nil -- the module keeps its panel and scroller in upvalues: one fresh copy per modal, like a fresh game
    ModalCompact = requireModule(ClientFolder.ModalCompact)
    local gui = inst("ScreenGui", "BeDinoUI", PlayerGui, {ViewSize = Vector2.new(viewW, viewH), DisplayOrder = 0})
    local shade = inst("TextButton", "ModalScrim", gui, {Size = UDim2.fromScale(1, 1), ZIndex = 20})
    local panel = inst("Frame", "Panel", shade, {Size = UDim2.fromOffset(860, 520), AnchorPoint = Vector2.new(.5, .5), Position = UDim2.fromScale(.5, .5), ZIndex = 21, Active = true})
    local scale = inst("UIScale", "Scale", panel, {Scale = 1})
    local header = inst("Frame", "Header", panel, {Position = UDim2.fromOffset(4, 4), Size = UDim2.fromOffset(852, 78), ZIndex = 22})
    local heading = inst("TextLabel", "Heading", header, {Position = UDim2.fromOffset(22, 4), Size = UDim2.fromOffset(730, 68), ZIndex = 23, TextSize = 40})
    local body = inst("Frame", "Body", panel, {Position = UDim2.fromOffset(18, 98), Size = UDim2.fromOffset(824, 402), ZIndex = 23, BackgroundTransparency = 1})
    local closeButton = inst("TextButton", "X", header, {Text = "X", AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -2, 0, 1), Size = UDim2.fromOffset(80, 76), ZIndex = 24})
    ModalCompact.attach({gui = gui, panel = panel, header = header, heading = heading, body = body, closeButton = closeButton, scale = scale})
    -- Bootstrap open(): layout(), the body goes to its settled place, the screen is drawn, then the floor pass
    body.AnchorPoint, body.Position = Vector2.zero, ModalCompact.place(true, false)
    return {gui = gui, panel = panel, header = header, body = body, x = closeButton, scale = scale}
end
local function visibleBox(modal)
    local scroller = modal.panel:FindFirstChild("BodyScroll")
    if scroller and scroller.Visible then return rectOf(scroller), true end
    return rectOf(modal.body), false -- desktop: the 824 x 402 body is the window
end

-- ===== the Eggs screen =====
local Colors = Theme.Colors
local function newCtx(modal, scenario)
    local function label(parent, text, x, y, w, h, size, col)
        return inst("TextLabel", "Label", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(w, h), Text = text, TextSize = size, BackgroundTransparency = 1,
            TextWrapped = true, ZIndex = parent.ZIndex + 1, TextColor3 = col or Colors.text})
    end
    local function box(parent, x, y, w, h, col, z) return inst("Frame", "Box", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(w, h), BackgroundColor3 = col, ZIndex = z}) end
    local function button(parent, text, x, y, w, h, col, callback)
        local b = inst("TextButton", "Button", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(w, h), BackgroundColor3 = col, Text = text, TextSize = 23, ZIndex = parent.ZIndex + 2})
        b.Activated:Connect(function() callback() end)
        return b
    end
    local function art(parent, _, x, y, size) return inst("Frame", "Art", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(size, size), ZIndex = parent.ZIndex + 1}) end
    local values = {NextChestId = scenario.entry and scenario.entry.id or "", QueuedEggsWaiting = scenario.waiting or 0, NextChestReadyAt = 0, ActiveChestCount = scenario.active or 0}
    return {
        body = modal.body, C = Colors, label = label, box = box, button = button, art = art,
        queue = function() return if scenario.entry then {scenario.entry} else {} end,
        str = function(name) return values[name] or "" end, num = function(name) return values[name] or 0 end,
        nestList = scenario.nests, rarityNames = {"Common", "Uncommon", "Rare", "Epic", "Legendary"}, rarityColors = {Colors.text, Colors.accent, Colors.blue, Colors.purple, Colors.gold},
        scale = function() return ModalCompact.model().scale end,
        notify = function() end, openNest = function() end, openEgg = function() end, openSettings = function() end, explore = function() end,
        autoOpenText = function() return "Auto-open is off" end, collectionCopies = function() return scenario.copies or 9 end,
        bodyH = ModalCompact.bodyHeight(), bodyScale = ModalCompact.bodyScale(),
    }
end

local function nestsOf(states)
    local list = {}
    for i, state in states do list[i] = {id = "n" .. i, state = state, readyAt = 1000 + 9000 * i, genes = nil} end
    return list
end
local EGG_PLAIN = {id = "e1", rarity = 2, readyAt = 0}
local EGG_CRACKED = {id = "e2", rarity = 4, readyAt = 0, genes = {patternId = "01_plain", primaryColorId = "green", secondaryColorId = "blue", blend = 20, conditionId = "cracked"}, mutationId = "frost"}
local SCENARIOS = {
    {name = "plain egg, ready", entry = EGG_PLAIN, waiting = 13, active = 1, nests = nestsOf({"incubating", "queued", "queued", "queued", "queued"})},
    {name = "cracked egg with hint, chips and badge", entry = EGG_CRACKED, waiting = 40, active = 1, nests = nestsOf({"ready", "incubating", "queued", "queued", "queued"})},
    {name = "nothing waiting", entry = nil, waiting = 0, active = 0, nests = {}},
}
local SIZES = {
    {848, 423}, {848, 481}, {844, 390}, {844, 354}, {667, 375}, {667, 339}, {500, 465}, {500, 400}, {740, 340}, {1156, 793}, {1445, 841},
}

local function eggsChecks(w, h, scenario)
    local modal = buildModal(w, h)
    local ctx = newCtx(modal, scenario)
    local refresh = EggsScreen.render(ctx)
    ModalCompact.enforce()
    refresh()
    local tag = string.format("Eggs %dx%d (%s)", w, h, scenario.name)
    local box, compact = visibleBox(modal)
    local things = {}
    for _, d in modal.body:GetDescendants() do
        if isGui(d) and d.Visible then
            local p = rawget(d, "__p")
            local text = p.Text
            if p.ClassName == "TextLabel" and string.sub(text, 1, 5) == "Nests" then things.header = d end
            if p.ClassName == "TextLabel" and text == EggsLogicCopy.NestLine then things.luck = d end
            if p.Name == "OpenEggButton" or p.Name == "AutoOpenSettingsButton" or p.Name == "EggStatusPill" or p.Name == "EggsWaiting" or p.Name == "CrackedHint"
                or p.Name == "RarityChip" or p.Name == "ConditionChip" or p.Name == "BadgeChip" then things[p.Name] = d end
            if string.sub(p.Name, 1, 8) == "NestSlot" then things[p.Name] = d end
        end
    end
    check(things.header ~= nil and things.luck ~= nil and things.NestSlot1 ~= nil and things.OpenEggButton ~= nil, tag .. ": the screen drew its parts")
    if not (things.header and things.NestSlot1 and things.OpenEggButton) then return end
    -- 1) nothing cut: every named part sits fully inside the visible body, so nothing needs a scroll
    for name, d in things do
        check(inside(rectOf(d), box), string.format("%s: %s is cut (%s, the visible body is %s)", tag, name, describe(rectOf(d)), describe(box)))
    end
    -- 2) the header line and the hint never touch the nest slots
    for i = 1, 5 do
        local slot = rectOf(things["NestSlot" .. i])
        check(not overlaps(rectOf(things.header), slot), string.format("%s: the 'Nests' header overlaps nest slot %d", tag, i))
        check(not overlaps(rectOf(things.luck), slot), string.format("%s: the nest hint line overlaps nest slot %d", tag, i))
    end
    -- 3) the buttons: OPEN EGG whole, at least 44 px, apart from AUTO and the status pill
    local open, auto = rectOf(things.OpenEggButton), rectOf(things.AutoOpenSettingsButton)
    check(open.h >= 44 - .5 and auto.h >= 44 - .5 and open.w >= 44, string.format("%s: OPEN EGG %s and AUTO %s are at least 44 px tall", tag, describe(open), describe(auto)))
    check(not overlaps(open, auto), tag .. ": OPEN EGG touches AUTO")
    for _, name in {"EggStatusPill", "EggsWaiting", "CrackedHint"} do
        if things[name] then check(not overlaps(open, rectOf(things[name])), tag .. ": OPEN EGG overlaps " .. name) end
    end
    if things.EggStatusPill and things.EggsWaiting then check(not overlaps(rectOf(things.EggStatusPill), rectOf(things.EggsWaiting)), tag .. ": the status pill overlaps the waiting count") end
    for i = 1, 5 do
        local slot = rectOf(things["NestSlot" .. i])
        check(slot.h >= 44, string.format("%s: nest slot %d is a tap target (%d px)", tag, i, slot.h))
        check(not overlaps(slot, open) and not overlaps(slot, auto), string.format("%s: nest slot %d overlaps a button", tag, i))
    end
    -- the hero card and its chips
    for _, name in {"RarityChip", "ConditionChip", "BadgeChip"} do
        local chip = things[name]
        if chip then
            for _, other in {"OpenEggButton", "AutoOpenSettingsButton", "EggStatusPill", "EggsWaiting", "CrackedHint"} do
                if things[other] then check(not overlaps(rectOf(chip), rectOf(things[other])), tag .. ": " .. name .. " overlaps " .. other) end
            end
        end
    end
    -- desktop numbers did not change (docs/114 s8.2: the desktop screen is exactly what it was): the sizes the screen had before this change
    if not compact and scenario.name == "plain egg, ready" then
        local k = scaleAt(things.NestSlot1)
        local function design(d) local r = rectOf(d) return r.w / k, r.h / k end
        local _, slotH = design(things.NestSlot1)
        local _, openH = design(things.OpenEggButton)
        local _, autoH = design(things.AutoOpenSettingsButton)
        check(math.abs(slotH - 96) < .5 and math.abs(openH - 80) < .5 and math.abs(autoH - 52) < .5, string.format("%s: desktop sizes changed: nest %.1f (96), OPEN %.1f (80), AUTO %.1f (52)", tag, slotH, openH, autoH))
    end
    -- 4) text on screen: every label at its design size times the cumulative scale is at least 14 px (shrink-to-fit text counts at its largest size)
    for _, d in modal.body:GetDescendants() do
        if isGui(d) and d.Visible and (d.ClassName == "TextLabel" or d.ClassName == "TextButton") and d.Text ~= "" then
            local size = d.TextSize
            if d.TextScaled then
                local limit = d:FindFirstChildOfClass("UITextSizeConstraint")
                size = if limit then limit.MaxTextSize else size
            end
            local px = size * scaleAt(d)
            check(px >= 14 - .01, string.format("%s: text '%s' is %.1f px on screen (%s)", tag, string.sub(d.Text, 1, 24), px, d.Name))
        end
    end
    modal.gui:Destroy()
end

for _, scenario in SCENARIOS do
    for _, size in SIZES do eggsChecks(size[1], size[2], scenario) end
end



-- ===== a window that changes size while the Eggs screen is open (the QA pictures 268 and 269) =====
-- The screen is drawn at one size, the window is dragged through a very narrow one and ends at another. The result must be exactly what a fresh
-- drawing at the final size gives: nothing stays grown by an earlier, smaller canvas, and nothing keeps the layout of the old size.
local function snapshot(modal)
    local list = {}
    for _, d in modal.body:GetDescendants() do
        if isGui(d) then
            local r = rectOf(d)
            table.insert(list, {name = d.Name, text = d.Text, x = r.x, y = r.y, w = r.w, h = r.h, size = d.TextSize, visible = d.Visible})
        end
    end
    return list
end
local function resizeTo(modal, w, h)
    rawget(modal.gui, "__p").ViewSize = Vector2.new(w, h)
    ModalCompact.layout() -- Bootstrap's scales()
    local e = rawget(modal.gui, "__ev")["prop:AbsoluteSize"]
    if e then e:Fire() end
    frames(2)
    ModalCompact.enforce()
end
local function sameSnapshot(a, b, tag)
    if not check(#a == #b, string.format("%s: %d parts after the resize, %d in a fresh drawing", tag, #a, #b)) then return end
    for i = 1, #a do
        local x, y = a[i], b[i]
        local same = x.name == y.name and x.text == y.text and x.visible == y.visible and math.abs(x.x - y.x) < 1 and math.abs(x.y - y.y) < 1
            and math.abs(x.w - y.w) < 1 and math.abs(x.h - y.h) < 1 and x.size == y.size
        if not same then
            check(false, string.format("%s: part %d (%s '%s') is %s text %s after the resize but %s text %s in a fresh drawing", tag, i, x.name, string.sub(x.text, 1, 16), describe(x), tostring(x.size), describe(y), tostring(y.size)))
            return
        end
    end
end
local RESIZES = {
    {name = "desktop, then a very narrow window, then 848 x 423", start = {1445, 841}, steps = {{300, 400}, {500, 400}, {848, 423}}},
    {name = "848 x 423, then a narrow window, back to 848 x 423", start = {848, 423}, steps = {{320, 380}, {848, 423}}},
    {name = "phone 667 x 375, then desktop", start = {667, 339}, steps = {{1156, 793}}},
    {name = "desktop 1156 x 793, then the phone", start = {1156, 793}, steps = {{667, 339}}},
    {name = "848 x 481 to 844 x 390", start = {848, 481}, steps = {{844, 390}}},
}
-- a screen that does not redraw itself (most screens): only ModalCompact's floor pass can keep it right
local function drawStatic(modal)
    inst("TextLabel", "Title", modal.body, {Position = UDim2.fromOffset(0, 0), Size = UDim2.fromOffset(300, 28), Text = "A screen", TextSize = 17, ZIndex = 24})
    for i = 1, 3 do
        inst("TextButton", "Slot" .. i, modal.body, {Position = UDim2.fromOffset((i - 1) * 170, 36), Size = UDim2.fromOffset(160, 68), Text = "Slot " .. i, TextSize = 18, ZIndex = 25})
    end
    inst("TextButton", "Big", modal.body, {Position = UDim2.fromOffset(0, 120), Size = UDim2.fromOffset(300, 50), Text = "Go", TextSize = 22, ZIndex = 25})
    ModalCompact.enforce()
end
for _, r in RESIZES do
    local modal = buildModal(r.start[1], r.start[2])
    drawStatic(modal)
    for _, step in r.steps do resizeTo(modal, step[1], step[2]) end
    local final = r.steps[#r.steps]
    local after = snapshot(modal)
    local fresh = buildModal(final[1], final[2])
    drawStatic(fresh)
    sameSnapshot(after, snapshot(fresh), "Static screen resize " .. r.name)
    modal.gui:Destroy()
    fresh.gui:Destroy()
end
for _, scenario in {SCENARIOS[2], SCENARIOS[1]} do
    for _, r in RESIZES do
        local modal = buildModal(r.start[1], r.start[2])
        EggsScreen.render(newCtx(modal, scenario))
        ModalCompact.enforce()
        for _, step in r.steps do resizeTo(modal, step[1], step[2]) end
        local final = r.steps[#r.steps]
        local after = snapshot(modal)
        local box = visibleBox(modal)
        local fresh = buildModal(final[1], final[2])
        local ctx2 = newCtx(fresh, scenario)
        local refresh = EggsScreen.render(ctx2)
        ModalCompact.enforce()
        sameSnapshot(after, snapshot(fresh), string.format("Eggs resize %s (%s)", r.name, scenario.name))
        modal.gui:Destroy()
        fresh.gui:Destroy()
    end
end

-- ===== the hatch card and the reveal =====
-- Bootstrap's hatch prelude: the body goes to its settled place, the egg view and the three labels are made at the numbers Bootstrap uses.
local function playHatch(modal, motion, result)
    local body = modal.body
    body.AnchorPoint, body.Position = Vector2.zero, ModalCompact.place(true, motion)
    local eggView = inst("Frame", "EggView", body, {Size = UDim2.fromOffset(304, 260)})
    local function label(name, y, h) return inst("TextLabel", name, body, {Position = UDim2.fromOffset(80, y), Size = UDim2.fromOffset(660, h), ZIndex = 30, TextSize = 24}) end
    local nameLabel, oddsLabel, detailLabel = label("Reward", 236, 54), label("Odds", 288, 28), label("Detail", 316, 28)
    nameLabel.Text, nameLabel.TextWrapped = result.name or "Dimorphodon", true -- BD-1107: Bootstrap sets the dinosaur's name before the sequence starts
    local dino = inst("ViewportFrame", "Dino", body, {Position = UDim2.fromOffset(160, -12), Size = UDim2.fromOffset(504, 260), Visible = false})
    inst("WorldModel", "WorldModel", dino)
    local paint = setmetatable({}, {__index = function() return function() end end})
    local aborts = 0
    local args = {
        gui = modal.gui, panel = modal.panel, header = modal.header, body = body, eggView = eggView, animateEgg = function() end, splitEgg = function() end, paint = paint,
        nameLabel = nameLabel, oddsLabel = oddsLabel, detailLabel = detailLabel, motion = motion, alive = function() return true end, flash = function() end,
        onSkipAll = function() end, onReveal = function() end, onNext = function() end, onAgain = function() end, onAbort = function() aborts += 1 end, eggId = "egg-1",
    }
    local handle = Hatch.play(args)
    frames(2)
    local res = {dino = dino, rarity = result.rarity or 1, color = color(.3, .8, .3), failed = result.failed == true, shiny = result.shiny == true, big = result.big == true,
        speciesId = "compy", remaining = result.remaining or 0, paintColors = {color(1, 1, 1), color(1, 1, 1)},
        mutationName = result.mutationName, mutationId = result.mutationId, mutationColor = if result.mutationName then color(.9, .3, .4) else nil, newFind = result.newFind}
    NEW_WORDS = result.newWords or {}
    if result.genes then
        res.genes = result.genes
        res.colorReveal = result.chipA or {name = "Cream", tier = 1, tierName = "Common", rgb = {247, 234, 196}, id = "white"}
        res.secondReveal = result.chipB or {name = "Blue", tier = 1, tierName = "Common", rgb = {36, 132, 211}, id = "blue"}
        res.patternReveal = {name = "Dots", tier = 1, tierName = "Common", plain = false}
    end
    handle.supply(res)
    return handle, args, dino
end
-- BD-1107 (docs/200 picture 416): the ribbons, the "why Skip stops" tag and the class badge of the reveal card. They are children of the card body, so they are
-- judged in the card's own design px (824 x 402). Text cannot be measured in the mock, so a word is estimated the way the other layout checks do it: 0.5 em
-- per character, one line = 1.05 em. The estimate used by the game (TagFit) is wider, so a layout that passes there passes here with room to spare.
local function designRect(o)
    local p = rawget(o, "__p")
    local w, h = p.Size.X.Offset, p.Size.Y.Offset
    return {x = p.Position.X.Offset - p.AnchorPoint.X * w, y = p.Position.Y.Offset - p.AnchorPoint.Y * h, w = w, h = h}
end
local function turned(r, degrees) -- the box a rectangle turned by `degrees` around its centre covers
    local a = math.rad(math.abs(degrees or 0))
    local w, h = r.w * math.cos(a) + r.h * math.sin(a), r.w * math.sin(a) + r.h * math.cos(a)
    return {x = r.x + r.w / 2 - w / 2, y = r.y + r.h / 2 - h / 2, w = w, h = h}
end
local function flatWidth(text, size) return (utf8.len(text) or #text) * 0.5 * size end
local TAG_MARGIN, NAME_TOP = 4, 236
local function tagChecks(modal, args, tag, stage)
    local body = modal.body
    local items = {}
    for _, d in body:GetChildren() do
        if isGui(d) and d.Visible and (d.Name == "Ribbon" or d.Name == "StopTag") then
            local r = turned(designRect(d), rawget(d, "__p").Rotation)
            table.insert(items, {o = d, r = r, name = d.Name .. " '" .. tostring((d:FindFirstChildOfClass("TextLabel") or {Text = ""}).Text):gsub("\n", " ") .. "'"})
        end
    end
    check(#items >= (stage.tagCount or 1), string.format("%s: %d ribbons / tags drawn, expected at least %d", tag, #items, stage.tagCount or 1))
    local k = scaleAt(body)
    for _, it in items do
        -- inside the card (never cut at the left or right edge) and above the dinosaur's name
        check(it.r.x >= TAG_MARGIN - .01 and it.r.x + it.r.w <= 824 - TAG_MARGIN + .01 and it.r.y >= 0 and it.r.y + it.r.h <= NAME_TOP - 2,
            string.format("%s: %s %s leaves the card (824 wide, the name starts at %d)", tag, it.name, describe(it.r), NAME_TOP))
        -- every word of it fits its box, at a size that is at least 14 px on screen
        for _, d in it.o:GetDescendants() do
            if d.ClassName == "TextLabel" and d.Text ~= "" then
                local kk = scaleAt(d)
                local dw, dh = d.AbsoluteSize.X / kk, d.AbsoluteSize.Y / kk
                local lines = 0
                for line in string.gmatch(d.Text .. "\n", "(.-)\n") do
                    lines += 1
                    check(not d.TextScaled and flatWidth(line, d.TextSize) <= dw + .01,
                        string.format("%s: '%s' (%d px) needs about %d px of its %d px box in %s", tag, line, d.TextSize, flatWidth(line, d.TextSize), dw, it.name))
                end
                check(not string.find(d.Text, "...", 1, true), string.format("%s: the words '%s' were cut short in %s", tag, d.Text, it.name))
                check(lines * d.TextSize * 1.05 <= dh + 2, string.format("%s: '%s' has %d line(s) at %d px but its box is %d high in %s", tag, d.Text, lines, d.TextSize, dh, it.name))
                check(d.TextSize * kk >= 14 - .01, string.format("%s: '%s' is %.1f px on screen in %s", tag, d.Text, d.TextSize * kk, it.name))
            end
        end
    end
    -- two of them never share a spot
    for i = 1, #items do
        for j = i + 1, #items do
            check(not overlaps(items[i].r, items[j].r), string.format("%s: %s %s overlaps %s %s", tag, items[i].name, describe(items[i].r), items[j].name, describe(items[j].r)))
        end
    end
    -- the class badge sits left of the name, which starts right of it (the name is left-aligned there), and neither reaches into a ribbon
    local badge = body:FindFirstChild("ClassBadge")
    local nameBox = designRect(args.nameLabel)
    if badge and badge.Visible then
        local word = badge:FindFirstChild("ClassWord")
        local b = designRect(badge)
        local wordSize = math.max(word.TextSize, math.ceil(14 / k - 1e-9))
        b.w = b.w + 6 + flatWidth(word.Text, wordSize) + 6
        check(string.find(tostring(args.nameLabel.TextXAlignment), "Left", 1, true) ~= nil, tag .. ": the name is not left-aligned beside the class badge")
        check(b.x + b.w <= nameBox.x - 2, string.format("%s: the class badge %s reaches the name text, which starts at %d", tag, describe(b), nameBox.x))
        check(flatWidth(args.nameLabel.Text, args.nameLabel.TextSize) <= nameBox.w + .01, string.format("%s: the name '%s' needs %d px of its %d px box", tag, args.nameLabel.Text, flatWidth(args.nameLabel.Text, args.nameLabel.TextSize), nameBox.w))
        check(b.x >= 0 and nameBox.x + nameBox.w <= 824, tag .. ": the badge and the name leave the card")
        for _, it in items do check(not overlaps(it.r, b), string.format("%s: %s lies over the class badge", tag, it.name)) end
    end
end
local HATCH_NAMES = {"TapHint", "EndButtons", "EggCounter", "PaintChip1", "PaintChip2", "PatternChip", "ConditionChip", "RarityPill", "StopTag", "Ribbon", "TierBadge"}
local function hatchChecks(w, h, motion, stage)
    local modal = buildModal(w, h)
    local handle, args, dino = playHatch(modal, motion, stage.result)
    frames(math.floor(stage.seconds * 30))
    local tag = string.format("Hatch %dx%d (%s%s)", w, h, stage.name, if motion then "" else ", Reduce Motion")
    local box = visibleBox(modal)
    local gui = rectOf(modal.gui)
    -- the whole 824 x 402 card is inside the visible body: the card is never pushed down or cut
    local slack = stage.zoom or .75 -- px: the camera push-in of the build-up makes the card a few percent bigger on purpose
    check(inside(rectOf(modal.body), box, slack), string.format("%s: the hatch card %s is cut (the visible body is %s)", tag, describe(rectOf(modal.body)), describe(box)))
    local parts = {args.nameLabel, args.oddsLabel, args.detailLabel}
    for _, d in modal.body:GetDescendants() do
        if isGui(d) and d.Visible and table.find(HATCH_NAMES, d.Name) then table.insert(parts, d) end
    end
    if dino.Visible then table.insert(parts, dino) end
    for _, d in parts do
        local r = rectOf(d)
        if r.w > 0 and r.h > 0 and (d.ClassName ~= "TextLabel" or d.Text ~= "") then
            check(inside(r, box), string.format("%s: %s %s is cut (the visible body is %s)", tag, d.Name, describe(r), describe(box)))
        end
    end
    if stage.align then -- the effect layers (rings, rays, sparks) sit exactly over the card, not at the desktop spot
        local br, body = rectOf(modal.panel:FindFirstChild("HatchFxBack")), rectOf(modal.body)
        local fr = rectOf(modal.panel:FindFirstChild("HatchFxFront"))
        for _, layerRect in {br, fr} do
            check(math.abs(layerRect.x - body.x) < 1.5 and math.abs(layerRect.y - body.y) < 1.5 and math.abs(layerRect.w - body.w) < 2 and math.abs(layerRect.h - body.h) < 2,
                string.format("%s: the effect layer %s is not over the card %s", tag, describe(layerRect), describe(body)))
        end
    end
    if stage.tags then tagChecks(modal, args, tag, stage) end
    local skip = modal.gui:FindFirstChild("SkipAll", true)
    if skip and skip.Visible then check(inside(rectOf(skip), gui), string.format("%s: Skip the rest %s is outside the window", tag, describe(rectOf(skip)))) end
    handle.cancel()
    modal.gui:Destroy()
end
local HATCH_STAGES = {
    {name = "egg and colour chips", seconds = 2.6, zoom = 18, result = {rarity = 2, remaining = 5, genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "dino shown, tap line", seconds = 8, align = true, result = {rarity = 2, remaining = 5, big = true, shiny = true, genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "last egg, buttons", seconds = 9, result = {rarity = 1, remaining = 0}},
    -- BD-1107: Studio round 7 picture 416. Two or more tags at once, the longest words, and the class badge beside the name
    {name = "Rainbow egg and BIG", seconds = 8, tags = true, tagCount = 2, result = {rarity = 2, remaining = 3, big = true, genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "Rainbow, Shiny, BIG, a mutation and two New ribbons at once", seconds = 8, tags = true, tagCount = 6, result = {rarity = 3, remaining = 3, big = true, shiny = true, mutationName = "Blood Moon", mutationId = "bloodmoon", newFind = true,
        newWords = {"New pattern!", "New colour!"}, name = "Parasaurolophus", genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "New pattern, New colour and the stop tag", seconds = 8, tags = true, tagCount = 3, result = {rarity = 2, remaining = 3, newFind = true, newWords = {"New pattern!", "New colour!"}, genes = {conditionId = "astra", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "the longest words (a long mutation name, two lines)", seconds = 8, tags = true, tagCount = 3, result = {rarity = 4, remaining = 3, shiny = true, mutationName = "Blood Moon Rising", mutationId = "bloodmoon", name = "Pachycephalosaurus"}},
    {name = "a lone Rainbow egg", seconds = 8, tags = true, tagCount = 1, result = {rarity = 1, remaining = 3, genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "cracked egg splat", seconds = 9, result = {rarity = 1, remaining = 0, failed = true}},
}
for _, stage in HATCH_STAGES do
    for _, size in SIZES do
        hatchChecks(size[1], size[2], true, stage)
        hatchChecks(size[1], size[2], false, stage)
    end
end

-- ===== BD-1153 (docs/217): a pop-in UIScale never reaches the floor pass =====
-- Studio round 10: a hatch ribbon or tag is made with a UIScale of 0 and pops in. ModalCompact's floor pass multiplied every UIScale up to the panel, so the floor 14 / ~0
-- became 229112335, the engine clamped the word to TextSize 100 and the clamped 100 was stored as the design size (CmBaseText), so it never came back: every tag word was 100 px
-- big in a 15 px box. Here (a) a label under a UIScale of 0, 1e-8, 0.001, 0.14, 0.3, 0.49, 0.5, 0.7 and 1 goes through the pass, and the word stays in 14 .. 40 with its
-- design size untouched, and once the scale reaches 1 the word is exactly what a fresh label at scale 1 gets; (b) the REAL hatch screen plays with
-- tweens that really run frame by frame, the floor pass runs every frame, and every ribbon and stop-tag word stays in 14 .. 40 with CmBaseText equal to the size it was asked.
local TagFitReal = requireModule(SharedFolder.TagFit)
local POPIN_SIZES = {{516, 481}, {848, 423}, {667, 339}, {500, 465}, {740, 340}, {1156, 793}}
local POP_SCALES = {0, 1e-8, 0.001, 0.14, 0.3, 0.49, 0.5, 0.6, 0.7, 0.9, 1} -- the FusionMenu result holder pops from 0.6 and 0.7, a banner from 0.7, a card from 0
local popChecks = 0
local function designOk(word, asked) -- the remembered design size is what was asked (a desktop window runs no floor pass and remembers nothing)
    local base = word:GetAttribute("CmBaseText")
    return base == asked or (base == nil and ModalCompact.model().mode ~= "compact")
end
local function makeTagWord(modal, size, startScale, nested) -- nested = under a window-scale card
    local holder = modal.body
    if nested then -- a card under a real window scale of 0.3 (a very small window): the floor would be 14 / (0.3 * panel scale), over 50 px, and must stop at 40
        holder = inst("Frame", "Card", holder, {Size = UDim2.fromOffset(300, 120), ZIndex = 25})
        inst("UIScale", "BodyFit", holder, {Scale = 0.3})
    end
    local tag = inst("Frame", "Ribbon", holder, {Size = UDim2.fromOffset(200, 44), ZIndex = 26})
    local u = inst("UIScale", "UIScale", tag, {Scale = startScale})
    local word = inst("TextLabel", "Word", tag, {Size = UDim2.fromOffset(150, 40), Text = "Skip stops here", TextSize = size, ZIndex = 27})
    return word, u
end
for _, win in POPIN_SIZES do
    local w, h = win[1], win[2]
    local fresh = buildModal(w, h)
    local freshWord = makeTagWord(fresh, 14, 1, false)
    ModalCompact.enforce()
    local settled = freshWord.TextSize -- what a label that never popped in gets (the pass is reversible and idempotent: the same on every run)
    local freshNested = makeTagWord(fresh, 14, 1, true)
    ModalCompact.enforce()
    local settledNested = freshNested.TextSize
    fresh.gui:Destroy()
    for _, nested in {false, true} do
        for _, startScale in POP_SCALES do
            local modal = buildModal(w, h)
            local word, u = makeTagWord(modal, 14, startScale, nested)
            local tag = string.format("Pop-in %dx%d%s from UIScale %s", w, h, if nested then " (small window scale)" else "", tostring(startScale))
            for pass = 1, 3 do -- idempotent: the same answer on every pass
                ModalCompact.enforce()
                popChecks += 1
                check(word.TextSize >= 14 and word.TextSize <= 40, string.format("%s: the word is %d px after pass %d (must stay in 14 .. 40, the engine's clamp is 100)", tag, word.TextSize, pass))
                check(designOk(word, 14), string.format("%s: the design size is %s after pass %d, it was asked 14", tag, tostring(word:GetAttribute("CmBaseText")), pass))
            end
            local expect = if nested then settledNested else settled
            check(word.TextSize == expect, string.format("%s: while it pops in the word is %d px, a word that never popped in has %d (a pop-in is not a window)", tag, word.TextSize, expect))
            if startScale < 1 then
                u.Scale = 0.01 -- a tween step on its way up must not change the answer's range
                ModalCompact.enforce()
                check(word.TextSize >= 14 and word.TextSize <= 40 and designOk(word, 14), string.format("%s: on its way up the word is %d px (design %s)", tag, word.TextSize, tostring(word:GetAttribute("CmBaseText"))))
                u.Scale = 1 -- the pop-in finishes
                ModalCompact.enforce()
            end
            check(word.TextSize == expect and designOk(word, 14), string.format("%s: after the pop-in the word is %d px (design %s), a label that never popped in has %d", tag, word.TextSize, tostring(word:GetAttribute("CmBaseText")), expect))
            modal.gui:Destroy()
        end
    end
end

-- (b) the real hatch screen, tweens that run for real, the floor pass on every frame
local function popInHatch(w, h, stage)
    POPIN = true
    local modal = buildModal(w, h)
    local handle, args = playHatch(modal, true, stage.result)
    local asked, kinds = {}, 0
    local tag = string.format("Hatch pop-in %dx%d (%s)", w, h, stage.name)
    local function tagWords()
        local list = {}
        for _, d in modal.body:GetChildren() do
            if isGui(d) and (d.Name == "Ribbon" or d.Name == "StopTag") then
                for _, l in d:GetDescendants() do
                    if l.ClassName == "TextLabel" and not l.TextScaled and l.Text ~= "" then table.insert(list, l) end
                end
            end
        end
        return list
    end
    for _ = 1, math.floor(stage.seconds * 30) do
        frames(1)
        for _, l in tagWords() do
            if asked[l] == nil then asked[l] = l.TextSize kinds += 1 end -- seen before this frame's pass: the size the hatch screen asked for
        end
        ModalCompact.enforce() -- what a new child schedules in the game
        for _, l in tagWords() do
            popChecks += 1
            check(l.TextSize >= 14 and l.TextSize <= 40, string.format("%s: '%s' is %d px (asked %s): must stay in 14 .. 40", tag, l.Text, l.TextSize, tostring(asked[l])))
            local base = l:GetAttribute("CmBaseText") -- nil on a desktop window (no floor pass there)
            check(base == asked[l] or (base == nil and ModalCompact.model().mode ~= "compact"), string.format("%s: '%s' design size is %s but it was asked %s", tag, l.Text, tostring(base), tostring(asked[l])))
        end
    end
    check(kinds >= (stage.tagCount or 1), string.format("%s: %d tag words were drawn, expected at least %d", tag, kinds, stage.tagCount or 1))
    for _, l in tagWords() do -- settled: at least 14 px on screen (the pass raised the word for this window)
        check(l.TextSize * scaleAt(l) >= 14 - .01, string.format("%s: '%s' is %.1f px on screen once it settled", tag, l.Text, l.TextSize * scaleAt(l)))
    end
    handle.cancel()
    modal.gui:Destroy()
    POPIN = false
end
for _, stage in HATCH_STAGES do
    if stage.tags then
        for _, win in POPIN_SIZES do popInHatch(win[1], win[2], stage) end
    end
end

-- ===== BD-1154 (docs/217, pictures 547 and 552): the colour name and the tier tag share the chip =====
-- Every colour with its own tier (and the longest words with the longest tier tags) in both chips, at every window size: the name keeps its
-- own box (not under 14 px on screen, measured with TagFit, not cut), the tier tag lies beside it or under it, the two never overlap, nothing leaves the chip.
local CHIP_COLOURS = {
    {"Cream", 1}, {"Blue", 1}, {"Stone", 1}, {"Clay", 1}, {"Green", 2}, {"Lime", 2}, {"Sky", 2}, {"Teal", 3}, {"Pink", 3}, {"Lilac", 3},
    {"Amber", 4}, {"Navy", 4}, {"Purple", 5}, {"Wine", 5}, {"Red", 6}, {"Black", 6},
    {"Cream", 2}, {"Green", 5}, {"Lilac", 5}, {"Purple", 2}, {"Stone", 5}, {"Cream", 5}, {"Sky", 4}, {"Wine", 2}, {"Amber", 5}, {"Cream", 6},
}
local TIER_WORDS = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}
local chipsJudged = 0
local function chipPair(a, b, w, h, motion, kindTag)
    local function reveal(c) return {name = c[1], tier = c[2], tierName = TIER_WORDS[c[2]], rgb = {200, 200, 200}, id = string.lower(c[1])} end
    local modal = buildModal(w, h)
    local handle = playHatch(modal, motion, {rarity = 2, remaining = 5, chipA = reveal(a), chipB = reveal(b),
        genes = {conditionId = "plain", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}})
    frames(math.floor(2.6 * 30))
    for i, c in {a, b} do
        local chip = modal.panel:FindFirstChild("PaintChip" .. i, true)
        local tag = string.format("Chip %s + %s at %dx%d%s (%s)", c[1], string.upper(TIER_WORDS[c[2]]), w, h, if motion then "" else ", Reduce Motion", kindTag)
        if check(chip ~= nil and chip.Visible, tag .. ": the chip is shown") then
            local nameLabel, badge, swatch = chip:FindFirstChild("Text"), chip:FindFirstChild("TierBadge"), chip:FindFirstChild("Swatch")
            local badgeLabel = badge and badge:FindFirstChild("Text")
            if check(nameLabel ~= nil and badge ~= nil and badgeLabel ~= nil and swatch ~= nil, tag .. ": name, tag and swatch exist") then
                chipsJudged += 1
                local k = scaleAt(nameLabel)
                local chipR = {x = 0, y = 0, w = chip.Size.X.Offset, h = chip.Size.Y.Offset}
                local nameR, tierR, swatchR = designRect(nameLabel), designRect(badge), designRect(swatch)
                local word = string.upper(TIER_WORDS[c[2]])
                check(not nameLabel.TextScaled and not badgeLabel.TextScaled, tag .. ": the words are measured sizes, not shrink-to-fit")
                check(nameLabel.Text == c[1] and badgeLabel.Text == word, tag .. ": the words are the colour and the tier")
                check(nameLabel.TextSize * k >= 14 - .01 and badgeLabel.TextSize * k >= 14 - .01, string.format("%s: %.1f / %.1f px on screen (needs 14)", tag, nameLabel.TextSize * k, badgeLabel.TextSize * k))
                check(nameLabel.TextSize <= 40 and badgeLabel.TextSize <= 40, tag .. ": a word over 40 design px")
                check(TagFitReal.width(c[1], nameLabel.TextSize) <= nameR.w, string.format("%s: '%s' (%d px) needs %d of its %d px box", tag, c[1], nameLabel.TextSize, TagFitReal.width(c[1], nameLabel.TextSize), nameR.w))
                check(TagFitReal.width(word, badgeLabel.TextSize) + 8 <= tierR.w, string.format("%s: '%s' (%d px) needs %d of its %d px tag", tag, word, badgeLabel.TextSize, TagFitReal.width(word, badgeLabel.TextSize) + 8, tierR.w))
                check(not overlaps(nameR, tierR), string.format("%s: the name box %s lies over the tier tag %s", tag, describe(nameR), describe(tierR)))
                check(not overlaps(swatchR, nameR) and not overlaps(swatchR, tierR), tag .. ": the swatch touches a word")
                for _, part in {{"name", nameR}, {"tier tag", tierR}} do
                    check(inside(part[2], chipR, .01), string.format("%s: the %s %s leaves the chip %s", tag, part[1], describe(part[2]), describe(chipR)))
                end
            end
        end
    end
    handle.cancel()
    modal.gui:Destroy()
end
for i = 1, #CHIP_COLOURS, 2 do
    local a, b = CHIP_COLOURS[i], CHIP_COLOURS[i + 1] or CHIP_COLOURS[1]
    for _, size in SIZES do
        chipPair(a, b, size[1], size[2], true, "colours") -- Reduce Motion skips the paint buckets and their chips: nothing to judge there
    end
end

-- ===== BD-1083: a tap on an Index tab must stay the tab's (docs/197 picture 350) =====
-- HubTravelClient turns a raw tap into "close the menu and travel" when it lands on a rail button while a menu is up. It used to look at the
-- position only; at 500 px the Index tabs lie over the EGGS rail button, so a tap on Patterns closed the Index and opened Eggs. The engine's hit
-- test was right all along (the tab is on top); the raw input event did not ask it. Now the route needs ModalClose.onBackdrop (the top thing is the
-- dark backdrop). The same decision as HubTravelClient.routeTap, run at every size on the REAL tabs, the X, and a rail rectangle under each of them.
local ConfigReal = requireModule(SharedFolder.Config)
local ConfigWithIndex = table.clone(ConfigReal) -- the real Config is frozen: IndexTabs gets a copy with the Index flag on (the playtest profile)
ConfigWithIndex.PatternColourIndexEnabled = true
local HubRules = requireModule(SharedFolder.HubTravelClientRules)
local ModalCloseReal = requireModule(ClientFolder.ModalClose)
local function routeOf(x, y, targets) -- what HubTravelClient.routeTap decides for a tap at (x, y) with a menu up
    return HubRules.routeScrimTap(true, true, x, y, targets, ModalCloseReal.onBackdrop(PlayerGui, x, y))
end
local function centerOf(o) local r = rectOf(o) return r.x + r.w / 2, r.y + r.h / 2 end
local function mountIndexTabs(modal)
    loaded.IndexTabs = nil
    loaded.Config = ConfigWithIndex
    local Tabs = requireModule(ClientFolder.IndexTabs)
    loaded.Config = ConfigReal
    -- ModalCompact.parts() knows the modal that attach() was given
    Tabs.mount(function() end)
    ModalCompact.enforce()
    return Tabs
end
for _, size in SIZES do
    local w, h = size[1], size[2]
    local modal = buildModal(w, h)
    mountIndexTabs(modal)
    local tag = string.format("Index tabs %dx%d", w, h)
    local bar = modal.header:FindFirstChild("IndexTabs")
    if check(bar ~= nil, tag .. ": the tab bar is drawn") then
        local controls = {modal.x}
        for _, name in {"Tab_dinos", "Tab_patterns", "Tab_colours"} do
            local b = bar:FindFirstChild(name)
            if check(b ~= nil, tag .. ": " .. name .. " exists") then table.insert(controls, b) end
        end
        for _, ctrl in controls do
            local cx, cy = centerOf(ctrl)
            local top = ModalCloseReal.topAt(PlayerGui, cx, cy)
            check(top == ctrl or (top ~= nil and top:IsDescendantOf(ctrl)), string.format("%s: the hit test at the centre of %s returns %s", tag, ctrl.Name, if top then top.Name else "nothing"))
            -- a rail button right under the control (the worst case), and the Studio rail of picture 350 (EGGS at x 151 to 309, y 12 to 104)
            local under = {{kind = "rail", destination = "eggs", x = cx - 80, y = cy - 27, w = 160, h = 54, enabled = true}}
            local studio = {{kind = "rail", destination = "collection", x = 151, y = 12, w = 158, h = 44, enabled = true}, {kind = "rail", destination = "eggs", x = 151, y = 60, w = 158, h = 44, enabled = true}}
            check(routeOf(cx, cy, under) == nil, string.format("%s: a tap on %s is routed to the rail button under it (it closes the menu and opens Eggs)", tag, ctrl.Name))
            check(routeOf(cx, cy, studio) == nil, string.format("%s: a tap on %s is routed to the Studio rail (picture 350)", tag, ctrl.Name))
        end
        -- control: on the bare dark backdrop a rail tap still routes (the BD-382 behaviour stays)
        local bx, by = 3, 3
        if ModalCloseReal.onBackdrop(PlayerGui, bx, by) then
            local rail = HubRules.routeScrimTap(true, true, bx, by, {{kind = "rail", destination = "eggs", x = 0, y = 0, w = 40, h = 40, enabled = true}}, true)
            local viaClient = routeOf(bx, by, {{kind = "rail", destination = "eggs", x = 0, y = 0, w = 40, h = 40, enabled = true}})
            check(rail ~= nil and viaClient ~= nil and viaClient.destination == "eggs", tag .. ": a tap on the bare dark backdrop over a rail button still travels")
        else
            check(false, tag .. ": the corner (3, 3) should be the bare backdrop")
        end
    end
    modal.gui:Destroy()
end

if failures > 0 then error(failures .. " small-window check(s) failed") end
print("Small window smoke passed: " .. #SIZES .. " sizes, " .. popChecks .. " pop-in readings, " .. chipsJudged .. " colour chips")
