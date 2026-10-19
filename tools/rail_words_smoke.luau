-- Offline rail-with-words smoke (BD-1116, docs/212; driven by tools/verify_rail_words.py).
-- The REAL TouchLayout / PhoneScale / Config / RailRun / HubTravelClientRules / HudPanelStack / ToastSlot run here. Part 1 sweeps the layout at 20 widths x 16 heights x mouse and
-- touch x 3 modes (in a run: Potions + the gear; at home: the five buttons + the gear; at home with the objectives pill) and checks rectangles. Part 2 puts the
-- REAL RailRun.place on a rail shaped like Bootstrap's (buttons with an icon, a word and an ActiveTab marker) in the geometry mock of tools/close_paths_smoke.luau and
-- reads the absolute rectangles. Part 3 checks the pieces that read the rail rect (open panels, toasts). NOT Studio: nothing here draws a pixel or measures a real font
-- (a letter is estimated at 0.6 em, wider than the real face).
-- @@PREFIX@@

local sources = MODULE_SOURCES
local loaded, stubs = {}, {}
local failures = 0
local function check(ok, message)
    if not ok then failures += 1 if failures <= 100000 then print("FAIL " .. message) end end
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
function methods.GetPropertyChangedSignal(self, property)
    local e = rawget(self, "__ev")
    e["prop:" .. property] = e["prop:" .. property] or signal()
    return e["prop:" .. property]
end
function methods.GetAttributeChangedSignal(self, property)
    local e = rawget(self, "__ev")
    e["attr:" .. property] = e["attr:" .. property] or signal()
    return e["attr:" .. property]
end
events.DescendantAdded, events.ChildAdded, events.CharacterAdded = true, true, true
workspace = {GetServerTimeNow = function() return 1000 end}
do local realNew = Instance.new Instance.new = function(class) local o = realNew(class) if class == "UIScale" then o.Scale = 1 end return o end end
Rect = {new = function(x0, y0, x1, y1) return {Min = {X = x0, Y = y0}, Max = {X = x1, Y = y1}, Width = x1 - x0, Height = y1 - y0} end}

local Players = {LocalPlayer = inst("Folder", "LocalPlayer")}
Services.Players = Players
local clientNames = {RailRun = true}
local function register(name)
    local m = Instance.new("ModuleScript") m.Name = name
    m.Parent = if clientNames[name] then ClientFolder else SharedFolder
end
for name in sources do register(name) end
local function requireModule(m)
    local name = m.Name
    if stubs[name] then return stubs[name] end
    if loaded[name] == nil then loaded[name] = sources[name](m, requireModule) end
    return loaded[name]
end
local Config = requireModule(SharedFolder.Config)
local PhoneScale = requireModule(SharedFolder.PhoneScale)
local TouchLayout = requireModule(SharedFolder.TouchLayout)
local HudPanelStack = requireModule(SharedFolder.HudPanelStack)
local ToastSlot = requireModule(SharedFolder.ToastSlot)

local function rendered(e) return {x = e.x, y = e.y, w = e.w * e.scale, h = e.h * e.scale} end
local function overlaps(a, b) return a.x < b.x + b.w - 1e-6 and b.x < a.x + a.w - 1e-6 and a.y < b.y + b.h - 1e-6 and b.y < a.y + a.h - 1e-6 end
local function describe(r) return string.format("%.0f,%.0f %.0fx%.0f", r.x, r.y, r.w, r.h) end

local WORDS = {"DINOS", "EGGS", "FUSION", "SHOP", "POTIONS"} -- the five word buttons, in Bootstrap's order
local LONGEST = 7
local EM = 0.6 -- an estimated letter, in em (wider than the real face)

-- every other piece of the HUD the rail must not touch (the list of tools/verify_hud_clearance.py, plus the toast-free pieces)
local function pieces(l)
    local list = {}
    local t = l.timers
    local function child(name, y, h) list[#list + 1] = {name = name, r = {x = t.x, y = t.y + y * t.scale, w = t.w * t.scale, h = h * t.scale}} end
    child("leap", t.leapY, TouchLayout.LEAP_H)
    if t.weatherVisible then child("weather", t.weatherY, TouchLayout.WEATHER_H) end
    if t.buffsVisible then child("buffs", t.buffsY, t.buffsH) end
    list[#list + 1] = {name = "hud", r = rendered(l.hud)}
    list[#list + 1] = {name = "crystal", r = rendered(l.crystal)}
    list[#list + 1] = {name = "goalline", r = {x = l.crystal.x, y = l.crystal.y + l.crystal.h * l.crystal.scale + TouchLayout.GOAL_GAP, w = l.crystal.w * l.crystal.scale, h = TouchLayout.GOAL_H * l.crystal.scale}}
    list[#list + 1] = {name = "action", r = rendered(l.action)}
    list[#list + 1] = {name = "badge", r = rendered(l.badge)}
    list[#list + 1] = {name = "notice", r = rendered(l.notice)}
    if l.goals then list[#list + 1] = {name = "goals", r = l.goals} end
    if l.objectives then list[#list + 1] = {name = "objectives", r = l.objectives} end
    if l.goalsPanel then list[#list + 1] = {name = "goalspanel", r = l.goalsPanel} end
    list[#list + 1] = {name = "chip", r = l.chip}
    list[#list + 1] = {name = "tellus", r = l.feedback}
    list[#list + 1] = {name = "admin", r = l.admin}
    if not l.goals and not l.objectives then
        list[#list + 1] = {name = "sizebar", r = rendered(l.sizeBar)}
        list[#list + 1] = {name = "sizehint", r = rendered(l.sizeHint)}
    end
    return list
end

-- the rectangles of a words rail on the canvas: five cells (or one) and the gear
local function railCells(l)
    local rail = l.rail
    local out = {}
    for i, p in rail.positions do
        out[#out + 1] = {name = "cell" .. i, r = {x = rail.x + p.x * rail.scale, y = rail.y + p.y * rail.scale, w = rail.button.w * rail.scale, h = rail.button.h * rail.scale}, cell = rail.button, word = true}
    end
    local g = rail.gear
    out[#out + 1] = {name = "gear", r = {x = rail.x + g.x * rail.scale, y = rail.y + g.y * rail.scale, w = rail.gearCell.w * rail.scale, h = rail.gearCell.h * rail.scale}, cell = rail.gearCell, word = false}
    return out
end

local widths = {440, 460, 480, 500, 516, 560, 600, 640, 667, 700, 740, 800, 844, 848, 915, 1024, 1156, 1280, 1445, 1920}
local heights = {339, 354, 375, 390, 400, 423, 445, 465, 481, 500, 560, 600, 720, 793, 841, 1080}
local MODES = {{"run", 1}, {"hub", 5}, {"hub+objectives", 5}}
local FALLBACK_BELOW_PHONE, FALLBACK_BELOW_DESKTOP = 516, 600 -- px: a window narrower than this may keep the old rail when the words do not fit (policy, docs/212)
local fallbacks = {}

-- ===== 1. the layout sweep =====
local checked, desktops, phones, grids, rows1 = 0, 0, 0, 0, 0
local smallest = {w = 1e9, h = 1e9}
for _, w in widths do
    for _, h in heights do
        for _, touch in {true, false} do
            for _, mode in MODES do
                local name, count = mode[1], mode[2]
                local args = {width = w, height = h, touch = touch, navCount = count, goals = name ~= "run", objectives = name == "hub+objectives"}
                local old = TouchLayout.compute(args)
                args.railWords = true
                local l = TouchLayout.compute(args)
                local tag = string.format("%dx%d %s %s", w, h, if l.touch then "phone layout" else "desktop layout", name)
                local rail = l.rail
                if l.railWordsFallback then
                    fallbacks[#fallbacks + 1] = string.format("%dx%d %s %s", w, h, if l.touch then "phone" else "desktop", name)
                    check(rail.gear == nil and #rail.positions == count + 1, tag .. ": a fallback is the old rail with " .. (count + 1) .. " buttons")
                    local limit = if l.touch then FALLBACK_BELOW_PHONE else FALLBACK_BELOW_DESKTOP
                    check(w < limit, tag .. ": the rail with words fell back at a window " .. w .. " px wide (policy: only under " .. limit .. ")")
                    checked += 1
                    continue
                end
                -- the rail with words never has more than five buttons
                check(#rail.positions == count and count <= 5, tag .. ": " .. #rail.positions .. " word buttons")
                check(rail.gear ~= nil and rail.gearCell ~= nil and rail.gearCell.iconOnly == true, tag .. ": the gear")
                check(rail.button.iconOnly ~= true, tag .. ": a word button is icon-only (the word would be hidden)")
                local box = rendered(rail)
                check(box.x >= -1e-6 and box.y >= -1e-6 and box.x + box.w <= w + 1e-6 and box.y + box.h <= h + 1e-6, tag .. ": the rail leaves the canvas " .. describe(box))
                local cells = railCells(l)
                for i, c in cells do
                    local r = c.r
                    check(r.x >= box.x - 1e-6 and r.y >= box.y - 1e-6 and r.x + r.w <= box.x + box.w + 1e-6 and r.y + r.h <= box.y + box.h + 1e-6, tag .. ": " .. c.name .. " is outside the rail rect")
                    check(r.w >= Config.TouchMinTargetPx - 1e-6 and r.h >= Config.TouchMinTargetPx - 1e-6, tag .. ": " .. c.name .. " is under 44 px (" .. describe(r) .. ")")
                    for j = i + 1, #cells do check(not overlaps(r, cells[j].r), tag .. ": " .. c.name .. " touches " .. cells[j].name) end
                    for _, p in pieces(l) do check(not overlaps(r, p.r), tag .. ": " .. c.name .. " lies over " .. p.name .. " " .. describe(r) .. " / " .. describe(p.r)) end
                    -- the icon and the word inside the cell
                    local k = c.cell
                    check(k.iconX >= -1e-6 and k.iconY >= -1e-6 and k.iconX + k.icon <= (k.w or rail.button.w) + 1e-6 and k.iconY + k.icon <= (k.h or rail.button.h) + 1e-6, tag .. ": " .. c.name .. " icon leaves its cell")
                    if c.word then
                        local px = k.textSize * rail.scale
                        local floor = if l.touch then PhoneScale.MinText else 16
                        check(px >= floor - 1e-6, string.format("%s: the word renders %.1f px (floor %d)", tag, px, floor))
                        check(LONGEST * EM * k.textSize <= k.labelW + 1e-6, string.format("%s: the longest word (%.0f design px) does not fit its box (%.0f)", tag, LONGEST * EM * k.textSize, k.labelW))
                        check(k.textSize <= k.labelH + 1e-6 and k.labelX + k.labelW <= k.w + 1e-6 and k.labelY + k.labelH <= k.h + 1e-6, tag .. ": " .. c.name .. " word box leaves its cell")
                        local sideBySide = k.labelX >= k.iconX + k.icon - 1e-6
                        local stacked = k.labelY >= k.iconY + k.icon - 1e-6
                        check(sideBySide or stacked, tag .. ": " .. c.name .. " word lies over its icon")
                    end
                end
                if l.touch then
                    phones += 1
                    if rail.rows == 1 then rows1 += 1 else grids += 1 end
                else
                    desktops += 1
                    check(rail.scale >= TouchLayout.RAILWORDS.minScale - 1e-9 and rail.scale <= 1, tag .. ": rail scale " .. rail.scale)
                    check(rail.gearCell.w * rail.scale >= 48 - 1e-6, tag .. ": the gear is under 48 px")
                end
                -- the old layout is what it was: flag nil/false gives the same table as before (no gear, six cells)
                check(old.rail.gear == nil and old.rail.gearCell == nil, tag .. ": the old rail got a gear")
                check(w > 0, tag)
                checked += 1
                if not (name == "run") then smallest.w = math.min(smallest.w, w) end
            end
        end
    end
end
do
    local seen, lines = {}, {}
    for _, f in fallbacks do
        local size, kind = string.match(f, "^(%d+x%d+) (%a+)")
        local key = kind .. " " .. size
        if not seen[key] then seen[key] = true table.insert(lines, key) end
    end
    table.sort(lines)
    print("fallbacks to the old rail: " .. #fallbacks .. " layouts, on " .. #lines .. " window sizes: " .. table.concat(lines, ", "))
end
check(phones > 0 and desktops > 0 and grids > 0 and rows1 > 0, "the sweep lost sensitivity: phones " .. phones .. " desktops " .. desktops .. " grids " .. grids .. " rows " .. rows1)

-- the flag off: the rail table of the old layout, unchanged (numbers of the BD-1105 era)
do
    local d = TouchLayout.compute({width = 1156, height = 841, touch = false, navCount = 6})
    check(d.rail.w == 186 and d.rail.h == 6 * 62 + 10 and d.rail.button.w == 172 and d.rail.button.h == 54 and d.rail.button.textSize == 19 and d.rail.scale == 1 and #d.rail.positions == 6, "flag off: the desktop rail changed")
    local p = TouchLayout.compute({width = 800, height = 360, touch = true, navCount = 6})
    check(#p.rail.positions == 6 and p.rail.gear == nil, "flag off: the phone rail changed")
    local a = TouchLayout.compute({width = 800, height = 360, touch = true, navCount = 6})
    local b = TouchLayout.compute({width = 800, height = 360, touch = true, navCount = 6, railWords = false})
    check(a.rail.x == b.rail.x and a.rail.w == b.rail.w and a.rail.h == b.rail.h and a.action.x == b.action.x, "railWords = false is not the same as nil")
    check(Config.HudRailWordsEnabled == false, "Config.HudRailWordsEnabled must be false in source")
end

-- ===== 2. RailRun.place on a rail shaped like Bootstrap's =====
local NAV = {"collection", "eggs", "fusion", "auras", "potions", "settings"}
local LABELS = {"DINOS", "EGGS", "FUSION", "SHOP", "POTIONS", "SETTINGS"}
local function rectOf(o) return {x = o.AbsolutePosition.X, y = o.AbsolutePosition.Y, w = o.AbsoluteSize.X, h = o.AbsoluteSize.Y} end
local function buildRail(w, h, touch, runState, words)
    local cfg = table.clone(Config)
    cfg.CaveHub, cfg.HudRailWordsEnabled = true, words
    loaded.RailRun, loaded.Config = nil, cfg
    local RailRun = requireModule(ClientFolder.RailRun)
    loaded.Config = Config
    local character = inst("Model", "Character")
    character:SetAttribute("RunState", runState)
    Players.LocalPlayer.Character = character
    local gui = inst("ScreenGui", "BeDinoUI", PlayerGui, {ViewSize = Vector2.new(w, h)})
    local rail = inst("Frame", "Rail", gui, {})
    inst("UIScale", "Scale", rail, {Scale = 1})
    local buttons = {}
    for i, dest in NAV do
        local b = inst("TextButton", "Rail_" .. dest, rail, {})
        b:SetAttribute("Destination", dest)
        inst("Frame", "Art", b, {})
        inst("TextLabel", "Word", b, {Text = LABELS[i], TextSize = 19})
        inst("Frame", "ActiveTab", b, {})
        buttons[i] = b
    end
    local layout = TouchLayout.compute({width = w, height = h, touch = touch, navCount = RailRun.count(buttons), goals = runState == "Sanctuary", railWords = words})
    local r = layout.rail
    rail.Position, rail.Size = UDim2.fromOffset(r.x, r.y), UDim2.fromOffset(r.w, r.h)
    rail:FindFirstChild("Scale").Scale = r.scale
    RailRun.place(buttons, layout)
    for _, b in buttons do b.Visible = not RailRun.hidden(b) end
    return {gui = gui, rail = rail, buttons = buttons, layout = layout, RailRun = RailRun}
end
local SIZES = {{516, 481}, {848, 423}, {848, 481}, {844, 390}, {844, 354}, {667, 375}, {667, 339}, {500, 465}, {500, 400}, {740, 340}, {1156, 793}, {1445, 841}, {1920, 1080}, {600, 700}, {480, 400}, {516, 500}}
local placed, fellBack = 0, 0
for _, size in SIZES do
    local w, h = size[1], size[2]
    for _, touch in {false, true} do
        for _, state in {"Sanctuary", "Active"} do
            local world = buildRail(w, h, touch, state, true)
            local tag = string.format("RailRun.place %dx%d %s %s", w, h, if touch then "touch" else "mouse", state)
            local box = rectOf(world.rail)
            local fallback = world.layout.railWordsFallback == true
            if fallback then fellBack += 1 end
            local shown = {}
            for _, b in world.buttons do
                local dest = b:GetAttribute("Destination")
                local gear = dest == "settings" and not fallback
                if b.Visible then
                    local r = rectOf(b)
                    shown[#shown + 1] = {dest = dest, r = r, b = b}
                    check(r.x >= box.x - .75 and r.y >= box.y - .75 and r.x + r.w <= box.x + box.w + .75 and r.y + r.h <= box.y + box.h + .75, tag .. ": " .. dest .. " outside the rail frame")
                    if not fallback or world.layout.touch then -- the old desktop rail shrinks with the window (28 px buttons at 516 px): that is the old behaviour, not a regression
                        check(r.w >= 44 - .75 and r.h >= 44 - .75, tag .. ": " .. dest .. " is under 44 px " .. describe(r))
                    end
                    local word = b:FindFirstChild("Word")
                    if gear then
                        check(word.Visible == false, tag .. ": the gear still shows its word")
                        check(world.RailRun.isGear(b), tag .. ": settings is not the gear")
                    elseif not fallback then
                        check(word.Visible == true, tag .. ": " .. dest .. " has no word")
                        local k = world.layout.rail.scale
                        local px = word.TextSize * k
                        check(px >= (if world.layout.touch then 14 else 16) - 1e-6, string.format("%s: %s word is %.1f px", tag, dest, px))
                        local wr = rectOf(word)
                        check(wr.x >= r.x - .75 and wr.x + wr.w <= r.x + r.w + .75 and wr.y >= r.y - .75 and wr.y + wr.h <= r.y + r.h + .75, tag .. ": " .. dest .. " word box leaves its button")
                        check(#word.Text * EM * word.TextSize * k <= wr.w + .75, tag .. ": " .. dest .. " word does not fit its box")
                    end
                end
            end
            local expectedWords = if state == "Sanctuary" then 5 else 1
            check(world.RailRun.count(world.buttons) == expectedWords and #world.layout.rail.positions == expectedWords + (if fallback then 1 else 0), tag .. ": RailRun.count " .. world.RailRun.count(world.buttons) .. " / layout cells " .. #world.layout.rail.positions)
            local wordsShown = 0
            for _, s in shown do if s.dest ~= "settings" then wordsShown += 1 end end
            check(wordsShown == expectedWords and #shown == expectedWords + 1, tag .. ": " .. wordsShown .. " word buttons + gear (or Settings) shown")
            for i = 1, #shown do for j = i + 1, #shown do check(not overlaps(shown[i].r, shown[j].r), tag .. ": " .. shown[i].dest .. " touches " .. shown[j].dest) end end
            if state == "Active" then
                local dests = {}
                for _, s in shown do dests[s.dest] = true end
                check(dests.potions and dests.settings and not dests.collection and not dests.eggs and not dests.fusion and not dests.auras, tag .. ": in a run only Potions and the gear show")
            end
            placed += 1
            world.gui:Destroy()
        end
    end
end
check(fellBack >= 2, "part 2 lost its fallback cases (" .. fellBack .. ")")
-- flag off: all six buttons as before, none of them a gear
do
    local world = buildRail(1156, 793, false, "Sanctuary", false)
    local n = 0
    for _, b in world.buttons do if b.Visible then n += 1 end check(not world.RailRun.isGear(b), "flag off: a gear") end
    check(n == 6 and world.RailRun.count(world.buttons) == 6, "flag off: six buttons at home")
    local settings = world.buttons[6]
    check(settings:FindFirstChild("Word").Visible == true, "flag off: SETTINGS lost its word on a wide desktop")
    world.gui:Destroy()
    local run = buildRail(1156, 793, false, "Active", false)
    check(run.RailRun.count(run.buttons) == 2, "flag off: two buttons in a run")
    run.gui:Destroy()
end

-- ===== 3. the pieces that read the rail rect: open panels, toasts =====
local panelsChecked = 0
for _, w in {516, 848, 1156} do
    for _, h in {423, 481, 600, 841} do
        for _, count in {1, 5} do
            local l = TouchLayout.compute({width = w, height = h, touch = false, navCount = count, goals = true, objectives = true, railWords = true})
            local r = rendered(l.rail)
            -- a panel placed over the middle of the rail must be moved by clearRail when there is room under the rail
            local panel = {x = r.x - 4, y = r.y + 4, w = 260, h = 214}
            local dy, clear = HudPanelStack.clearRail(panel, r, h)
            check(type(dy) == "number", "clearRail answers a number")
            if clear and dy ~= 0 then check(panel.y + dy >= r.y + r.h - 1e-6, string.format("clearRail %dx%d: the panel still covers the rail", w, h)) end
            if clear then check(not overlaps({x = panel.x, y = panel.y + dy, w = panel.w, h = panel.h}, r), string.format("clearRail %dx%d count %d: reported clear but the panel covers the rail", w, h, count)) end
            panelsChecked += 1
        end
    end
end

-- toasts (no menu open): the stack must clear the rail rect (the rail with words is bigger than the old one: it must not make the toasts worse than they were)
local toastCases, toastWorse, toastBadWords, toastBadOld = 0, 0, 0, 0
for _, w in widths do
    for _, h in {375, 423, 481, 600, 841} do
        for _, touch in {true, false} do
            for _, count in {1, 5} do
                local function stackHits(words)
                    local l = TouchLayout.compute({width = w, height = h, touch = touch, navCount = if words then count else count + 1, goals = true, railWords = words})
                    local wp = TouchLayout.walletPlates(l)
                    local r = rendered(l.rail)
                    local place = ToastSlot.place({canvasW = w, canvasH = h, scale = l.toastScale, keepClear = {wp, r}, menu = nil, shift = 0})
                    local cw = ToastSlot.W * place.scale
                    local box = {x = w / 2 + place.x - cw / 2, y = place.y, w = cw, h = ToastSlot.stackHeight(place.cards, place.scale)}
                    return overlaps(box, r) or overlaps(box, wp) or box.y + box.h > h + 0.5 or box.x < -0.5 or box.x + box.w > w + 0.5
                end
                local old, new = stackHits(false), stackHits(true)
                toastCases += 1
                if old then toastBadOld += 1 end
                if new then toastBadWords += 1 end
                if new and not old then
                    toastWorse += 1
                    check(false, string.format("toasts %dx%d %s count %d: the stack is clear with the old rail but covers the rail with words", w, h, if touch then "touch" else "mouse", count))
                end
            end
        end
    end
end

print(string.format("Rail words smoke: %d layouts (%d phone, %d desktop; %d one-row, %d grids), %d rails placed by RailRun.place, %d panel checks, %d toast cases (stack off the rail: old rail %d bad, rail with words %d bad), %d failures", checked, phones, desktops, rows1, grids, placed, panelsChecked, toastCases, toastBadOld, toastBadWords, failures))
if failures > 0 then error("rail words smoke failed: " .. failures) end
print("Rail words smoke passed")
