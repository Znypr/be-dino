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
    ImageIds = {paint_bucket = "", egg_splat = "", egg_shell = ""}, TextStyle = {apply = function() return inst("UIStroke") end}}
function Theme.decorate() end
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
local clientNames = {ModalCompact = true, EggsScreen = true, EggPicture = true, ConditionStage = true, HatchSequence = true, ModalClose = true, InspectView = true,
    HatchFx = true, MutationReveal = true, HatchEggV2 = true, PrivateState = true}
stubs.ClassBadge = {create = function(parent) return inst("Frame", "ClassBadge", parent) end}
stubs.Sfx = {play = function() end, playLayers = function() end, playCue = function() end, revealName = function() return "hatch_reveal" end}
stubs.SfxRules = {hatchCues = function(cues) return cues end}
stubs.InspectView = {attach = function() return {destroy = function() end, wasDrag = function() return false end} end}
stubs.HatchFx = {ensure = function() return {} end, begin = function() return {} end, update = function() end, hide = function() end, style = function() end, rainbow = function() end,
    splash = function() end, paintStyle = function() end}
stubs.PatternColourIndex = {ribbons = function() return {} end}
stubs.PrivateState = {str = function(_, fallback) return fallback or "" end}
stubs.MutationReveal = {begin = function() return {} end, update = function() end, hide = function() end}
stubs.HatchEggV2 = {create = function() return nil end, stop = function() end}
Services.HttpService = {JSONDecode = function() return {} end}
Services.TweenService = {Create = function(_, target, _, goals) return {Play = function() for k, v in goals do target[k] = v end end, Cancel = function() end, Completed = signal()} end}
Services.UserInputService = {InputBegan = inputBegan}
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
        speciesId = "compy", remaining = result.remaining or 0, paintColors = {color(1, 1, 1), color(1, 1, 1)}}
    if result.genes then
        res.genes = result.genes
        res.colorReveal = {name = "Cream", tier = 1, tierName = "Common", rgb = {247, 234, 196}, id = "white"}
        res.secondReveal = {name = "Blue", tier = 1, tierName = "Common", rgb = {36, 132, 211}, id = "blue"}
        res.patternReveal = {name = "Dots", tier = 1, tierName = "Common", plain = false}
    end
    handle.supply(res)
    return handle, args, dino
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
    local skip = modal.gui:FindFirstChild("SkipAll", true)
    if skip and skip.Visible then check(inside(rectOf(skip), gui), string.format("%s: Skip the rest %s is outside the window", tag, describe(rectOf(skip)))) end
    handle.cancel()
    modal.gui:Destroy()
end
local HATCH_STAGES = {
    {name = "egg and colour chips", seconds = 2.6, zoom = 18, result = {rarity = 2, remaining = 5, genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "dino shown, tap line", seconds = 8, align = true, result = {rarity = 2, remaining = 5, big = true, shiny = true, genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}}},
    {name = "last egg, buttons", seconds = 9, result = {rarity = 1, remaining = 0}},
    {name = "cracked egg splat", seconds = 9, result = {rarity = 1, remaining = 0, failed = true}},
}
for _, stage in HATCH_STAGES do
    for _, size in SIZES do
        hatchChecks(size[1], size[2], true, stage)
        hatchChecks(size[1], size[2], false, stage)
    end
end

if failures > 0 then error(failures .. " small-window check(s) failed") end
print("Small window smoke passed: " .. #SIZES .. " sizes")
