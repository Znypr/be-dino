-- Offline close-path smoke (BD-1019, docs/181; driven by tools/verify_close_paths.py).
-- A small Roblox mock WITH GEOMETRY (Position / Size / AnchorPoint / UIScale -> AbsolutePosition / AbsoluteSize, Visible, Active, ZIndex with
-- ZIndexBehavior.Sibling) runs the REAL hatch screen (HatchSequence) and the REAL close-path helper (ModalClose + ModalCloseRules) inside a tree
-- shaped like Bootstrap's menu (ModalScrim 20 > panel > header > X, body > end buttons). A tap is dispatched to whatever the real hit test
-- (ModalClose.topAt) says gets it, exactly as the engine would, so "X does nothing" shows up as a failed check here.
-- Visual-only modules (UITheme, effects, sounds, the dino view) are stubs. This proves layering and control flow. It proves nothing about
-- drawing, touch, a gamepad or Studio. MODULE_SOURCES is injected by the verifier.

-- ===== scheduler (virtual time) =====
local now = 0
local queue, seq = {}, 0
local function push(t, co) seq += 1 table.insert(queue, {t = t, co = co, seq = seq}) end
local function resume(co, ...)
    local ok, err = coroutine.resume(co, ...)
    if not ok then error(debug.traceback(co, tostring(err)), 0) end
end
local task = {}
function task.spawn(f, ...) local co = if type(f) == "thread" then f else coroutine.create(f) resume(co, ...) return co end
task.defer = task.spawn
function task.delay(t, f, ...) local a = table.pack(...) push(now + (t or 0), coroutine.create(function() f(table.unpack(a, 1, a.n)) end)) end
function task.wait(t) push(now + (t or .03), coroutine.running()) return coroutine.yield() end
local function runDue()
    while true do
        table.sort(queue, function(a, b) if a.t ~= b.t then return a.t < b.t end return a.seq < b.seq end)
        local item = queue[1]
        if not item or item.t > now then break end
        table.remove(queue, 1)
        if coroutine.status(item.co) == "suspended" then resume(item.co) end
    end
end
os = {clock = function() return now end, time = function() return 0 end}

-- ===== datatypes =====
local function signal()
    local s = {conns = {}}
    function s:Connect(f) local rec = {f = f} table.insert(self.conns, rec) return {Disconnect = function() rec.dead = true end} end
    s.Once = s.Connect
    function s:Fire(...) for _, rec in table.clone(self.conns) do if not rec.dead then rec.f(...) end end end
    return s
end
local V2 = {}
V2.__index = V2
V2.__add = function(a, b) return setmetatable({X = a.X + b.X, Y = a.Y + b.Y}, V2) end
V2.__sub = function(a, b) return setmetatable({X = a.X - b.X, Y = a.Y - b.Y}, V2) end
V2.__mul = function(a, b) if type(b) == "number" then return setmetatable({X = a.X * b, Y = a.Y * b}, V2) end return setmetatable({X = a.X * b.X, Y = a.Y * b.Y}, V2) end
V2.__div = function(a, b) return setmetatable({X = a.X / b, Y = a.Y / b}, V2) end
Vector2 = {new = function(x, y) return setmetatable({X = x or 0, Y = y or 0}, V2) end}
Vector2.zero = Vector2.new(0, 0)
local UD2 = {}
UD2.__index = UD2
UD2.__add = function(a, b)
    return setmetatable({X = {Scale = a.X.Scale + b.X.Scale, Offset = a.X.Offset + b.X.Offset}, Y = {Scale = a.Y.Scale + b.Y.Scale, Offset = a.Y.Offset + b.Y.Offset}}, UD2)
end
UDim = {new = function(s, o) return {Scale = s, Offset = o} end}
UDim2 = {new = function(a, b, c, d) return setmetatable({X = {Scale = a or 0, Offset = b or 0}, Y = {Scale = c or 0, Offset = d or 0}}, UD2) end}
UDim2.fromScale = function(x, y) return UDim2.new(x, 0, y, 0) end
UDim2.fromOffset = function(x, y) return UDim2.new(0, x, 0, y) end
local C3 = {}
C3.__index = C3
function C3:Lerp() return self end
local function color(r, g, b) return setmetatable({R = r, G = g, B = b}, C3) end
Color3 = {new = color, fromRGB = function(r, g, b) return color(r / 255, g / 255, b / 255) end}
ColorSequence = {new = function() return {} end}
ColorSequenceKeypoint = {new = function() return {} end}
NumberSequence = {new = function() return {} end}
NumberSequenceKeypoint = {new = function() return {} end}
TweenInfo = {new = function(time) return {Time = time or 0} end} -- BD-1153: the pop-in tests step a tween over its duration
Enum = setmetatable({}, {__index = function(_, k) return setmetatable({}, {__index = function(_, v) return k .. "." .. v end}) end})

-- ===== instances with geometry =====
Instance = {}
local imt = {}
local methods = {}
local hierarchy = {
    GuiObject = {Frame = true, TextLabel = true, TextButton = true, ImageLabel = true, ImageButton = true, ScrollingFrame = true, CanvasGroup = true, ViewportFrame = true},
    GuiButton = {TextButton = true, ImageButton = true},
}
local events = {Activated = true, InputBegan = true, InputChanged = true, InputEnded = true, MouseEnter = true, MouseLeave = true, Destroying = true, Changed = true}
local created = 0
function Instance.new(class)
    created += 1
    return setmetatable({__p = {ClassName = class, Name = class, Visible = true, Enabled = true, ZIndex = 1, DisplayOrder = 0, Text = "", Position = UDim2.new(), Size = UDim2.new(),
        AnchorPoint = Vector2.zero, TextBounds = Vector2.new(200, 40), Rotation = 0, Transparency = 0, BackgroundTransparency = 0}, __kids = {}, __attrs = {}, __ev = {}}, imt)
end
local function isGui(o) return hierarchy.GuiObject[rawget(o, "__p").ClassName] == true end
local function scaleOf(o) -- the UIScale child of o (1 when none)
    for _, c in rawget(o, "__kids") do if rawget(c, "__p").ClassName == "UIScale" then return rawget(c, "__p").Scale or 1 end end
    return 1
end
local layout
local function parentOf(o) return rawget(o, "__p").Parent end
local cache = {}
function layout(o) -- AbsolutePosition, AbsoluteSize, k (cumulative UIScale incl. o's own) : Roblox rules for one level
    local p = rawget(o, "__p")
    if p.ClassName == "ScreenGui" then
        local size = p.ViewSize or Vector2.new(1280, 720)
        return p.Origin or Vector2.zero, size, 1
    end
    local parent = p.Parent
    if not parent or (not isGui(parent) and rawget(parent, "__p").ClassName ~= "ScreenGui") then return Vector2.zero, p.ManualSize or Vector2.zero, 1 end
    local pp, ps, pk = layout(parent)
    local own = scaleOf(o)
    local size = Vector2.new(p.Size.X.Scale * ps.X + p.Size.X.Offset * pk, p.Size.Y.Scale * ps.Y + p.Size.Y.Offset * pk) * own
    local pos = Vector2.new(pp.X + p.Position.X.Scale * ps.X + p.Position.X.Offset * pk - p.AnchorPoint.X * size.X,
        pp.Y + p.Position.Y.Scale * ps.Y + p.Position.Y.Offset * pk - p.AnchorPoint.Y * size.Y)
    return pos, size, pk * own
end
imt.__index = function(self, key)
    local m = methods[key]
    if m then return m end
    if events[key] then
        local e = rawget(self, "__ev")
        e[key] = e[key] or signal()
        return e[key]
    end
    local p = rawget(self, "__p")
    if key == "AbsolutePosition" then
        if p.ClassName == "ScreenGui" and p.ReportsZeroOrigin then return Vector2.zero end -- some engines answer (0, 0) for the ScreenGui while its children sit below the inset
        return (layout(self))
    end
    if key == "AbsoluteSize" then local _, s = layout(self) return s end
    if key == "Active" then
        if p.Active ~= nil then return p.Active end
        return hierarchy.GuiButton[p.ClassName] == true
    end
    local v = p[key]
    if v ~= nil then return v end
    for _, c in rawget(self, "__kids") do if rawget(c, "__p").Name == key then return c end end
    return nil
end
imt.__newindex = function(self, key, value)
    local p = rawget(self, "__p")
    if key == "Parent" then
        local old = p.Parent
        if old then local list = rawget(old, "__kids") local i = table.find(list, self) if i then table.remove(list, i) end end
        p.Parent = value
        if value then table.insert(rawget(value, "__kids"), self) end
        return
    end
    if key == "TextSize" and type(value) == "number" then value = math.clamp(value, 1, 100) end -- the engine clamps TextSize to 1 .. 100 (BD-1153: Studio saw 100 where 229112335 was asked)
    p[key] = value
end
function methods.IsA(self, class)
    local c = rawget(self, "__p").ClassName
    return c == class or (hierarchy[class] ~= nil and hierarchy[class][c] == true) or class == "Instance"
end
function methods.GetChildren(self) return table.clone(rawget(self, "__kids")) end
local function walk(i, out) for _, c in rawget(i, "__kids") do table.insert(out, c) walk(c, out) end return out end
function methods.GetDescendants(self) return walk(self, {}) end
function methods.FindFirstChild(self, name, recursive)
    for _, c in (if recursive then walk(self, {}) else rawget(self, "__kids")) do if rawget(c, "__p").Name == name then return c end end
    return nil
end
function methods.WaitForChild(self, name) return assert(methods.FindFirstChild(self, name), "WaitForChild " .. name) end
function methods.FindFirstChildOfClass(self, class) for _, c in rawget(self, "__kids") do if rawget(c, "__p").ClassName == class then return c end end return nil end
function methods.IsDescendantOf(self, ancestor)
    local cur = rawget(self, "__p").Parent
    while cur do if cur == ancestor then return true end cur = rawget(cur, "__p").Parent end
    return false
end
function methods.ClearAllChildren(self) for _, c in methods.GetChildren(self) do c:Destroy() end end
function methods.Destroy(self)
    local e = rawget(self, "__ev").Destroying
    if e then e:Fire() end
    for _, c in methods.GetChildren(self) do c:Destroy() end
    self.Parent = nil
end
function methods.SetAttribute(self, k, v) rawget(self, "__attrs")[k] = v end
function methods.GetAttribute(self, k) return rawget(self, "__attrs")[k] end
function methods.GetPropertyChangedSignal() return signal() end
local function inst(class, name, parent, props)
    local o = Instance.new(class)
    o.Name = name or class
    for k, v in props or {} do o[k] = v end
    if parent then o.Parent = parent end
    return o
end

-- ===== services =====
local heartbeat = signal()
local inputBegan = signal()
local Replicated = inst("Folder", "ReplicatedStorage")
local SharedFolder = inst("Folder", "Shared", Replicated)
local ClientFolder = inst("Folder", "Client")
local PlayerGui = inst("Folder", "PlayerGui")
local Services = {
    ReplicatedStorage = Replicated,
    RunService = {Heartbeat = heartbeat, IsStudio = function() return false end},
    UserInputService = {InputBegan = inputBegan},
    HttpService = {JSONDecode = function() return {} end}, -- BD-1039: HatchSequence decodes LastChestNewJson for the ribbon words
    TweenService = {Create = function(_, target, _, goals) return {Play = function() for k, v in goals do target[k] = v end end, Cancel = function() end, Completed = signal()} end},
}
game = {GetService = function(_, name) return assert(Services[name], "service " .. name) end, GameId = 1}

-- ===== modules: REAL pure ones and the two close-path modules, stubs for the visual ones =====
local sources = MODULE_SOURCES
local loaded = {}
local stubs = {}
local Theme = {MotionEnabled = true, Colors = {panel = color(.2, .2, .2), card = color(.3, .3, .3), outline = color(0, 0, 0), text = color(1, 1, 1), gold = color(1, 1, 0),
    purple = color(1, 0, 1), accent = color(0, 1, 0), blue = color(0, 0, 1), red = color(1, 0, 0)},
    RarityColors = {color(.6, .6, .6), color(.3, .8, .3), color(.3, .5, 1), color(.7, .3, 1), color(1, .8, .2), color(1, .3, .3)},
    ImageIds = {paint_bucket = "", egg_splat = "", egg_shell = ""}, TextStyle = {apply = function() return inst("UIStroke") end, outlined = function() return inst("UIStroke") end}}
function Theme.decorate() end
function Theme.animate(target, _, goals) for k, v in goals do target[k] = v end end
stubs.UITheme = Theme
stubs.Sfx = {play = function() end, playLayers = function() end, playCue = function() end, revealName = function() return "hatch_reveal" end}
stubs.SfxRules = {hatchCues = function(cues) return cues end}
stubs.ClassBadge = {create = function(parent) return inst("Frame", "ClassBadge", parent) end}
stubs.InspectView = {attach = function(_, options) stubs.InspectView.last = options return {destroy = function() end, wasDrag = function() return false end} end}
stubs.HatchFx = {ensure = function() return {} end, begin = function() return {} end, update = function() end, hide = function() end, style = function() end, rainbow = function() end,
    splash = function() end, paintStyle = function() end}
stubs.PatternColourIndex = {ribbons = function() return {"NEW!"} end} -- BD-1039: the real rules are proved by verify_pattern_colour_index.py
stubs.PrivateState = {str = function(_, fallback) return fallback or "" end}
stubs.MutationReveal = {begin = function() return {} end, update = function() end, hide = function() end}
stubs.HatchEggV2 = {create = function() return nil end, stop = function() end}
local clientNames = {ModalClose = true, HatchSequence = true, InspectView = true, HatchFx = true, MutationReveal = true, HatchEggV2 = true, PrivateState = true}
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

local Rules = requireModule(SharedFolder.ModalCloseRules)
local ModalClose = requireModule(ClientFolder.ModalClose)
local Hatch = requireModule(ClientFolder.HatchSequence)

-- ===== a menu shaped like Bootstrap's =====
local failures = 0
local function check(ok, message)
    if not ok then failures += 1 print("FAIL " .. message) end
    return ok
end

local function buildMenu(viewW, viewH, panelW, panelH, scale, origin, zero)
    local gui = inst("ScreenGui", "BeDinoUI", PlayerGui, {ViewSize = Vector2.new(viewW, viewH), Origin = origin or Vector2.zero, DisplayOrder = 0, ReportsZeroOrigin = zero == true})
    local menu = {gui = gui, closed = 0, version = 0, aborts = 0, nexts = 0, agains = 0, skipAlls = 0}
    menu.bx, menu.by = (origin or Vector2.zero).X + 2, (origin or Vector2.zero).Y + 2 -- a point on the dark backdrop (every shape leaves a margin around the card)
    -- the rail is below the menu (ZIndex 2), a toast card sits at the top centre (ZIndex 50)
    menu.rail = inst("Frame", "Rail", gui, {Position = UDim2.fromOffset(14, 120), Size = UDim2.fromOffset(186, 382), ZIndex = 2})
    inst("TextButton", "RailEggs", menu.rail, {Position = UDim2.fromOffset(7, 7), Size = UDim2.fromOffset(172, 54), ZIndex = 4})
    menu.shade = inst("TextButton", "ModalScrim", gui, {Size = UDim2.fromScale(1, 1), ZIndex = 20})
    menu.panel = inst("Frame", "Panel", menu.shade, {Size = UDim2.fromOffset(panelW, panelH), AnchorPoint = Vector2.new(.5, .5), Position = UDim2.fromScale(.5, .5), ZIndex = 21, Active = true})
    inst("UIScale", "Scale", menu.panel, {Scale = scale})
    menu.header = inst("Frame", "Header", menu.panel, {Position = UDim2.fromOffset(4, 4), Size = UDim2.fromOffset(panelW - 8, 78), ZIndex = 22})
    menu.heading = inst("TextLabel", "Heading", menu.header, {Position = UDim2.fromOffset(22, 4), Size = UDim2.fromOffset(panelW - 130, 68), ZIndex = 23})
    menu.x = inst("TextButton", "X", menu.header, {Text = "X", AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -2, 0, 1), Size = UDim2.fromOffset(80, 76), ZIndex = 24})
    menu.body = inst("Frame", "Body", menu.panel, {Position = UDim2.fromOffset(18, 98), Size = UDim2.fromOffset(panelW - 36, panelH - 118), ZIndex = 23})
    menu.toasts = inst("Frame", "Toasts", gui, {AnchorPoint = Vector2.new(.5, 0), Position = UDim2.new(.5, 0, 0, 80), Size = UDim2.fromOffset(440, 186), ZIndex = 50})
    inst("TextButton", "ToastTap", menu.toasts, {Size = UDim2.fromOffset(440, 56), ZIndex = 55, Visible = false})
    -- Bootstrap's own close() and the two lines that route X / the backdrop to it (kept identical to src/client/Bootstrap.client.luau)
    menu.close = function() menu.closed += 1 menu.version += 1 end
    menu.x.Activated:Connect(menu.close)
    menu.shade.Activated:Connect(function() if ModalClose.outsideTap() then menu.close() end end)
    return menu
end

-- Dispatch a tap at (x, y): the real hit test decides who gets it. Returns that object (nil = nothing).
local function tapAt(menu, x, y)
    local top = ModalClose.topAt(menu.gui, x, y)
    if top and top:IsA("GuiButton") then top.Activated:Fire() end
    return top
end
local function centre(o) return o.AbsolutePosition.X + o.AbsoluteSize.X / 2, o.AbsolutePosition.Y + o.AbsoluteSize.Y / 2 end
local function tapOn(menu, o) local x, y = centre(o) return tapAt(menu, x, y) end
local function frames(n, dt) for _ = 1, n do now += dt or 1 / 30 runDue() heartbeat:Fire(dt or 1 / 30) end end

-- ===== the hatch screen, driven like Bootstrap drives it =====
local function playHatch(menu, opts)
    opts = opts or {}
    local eggView = inst("Frame", "EggView", menu.body, {Size = UDim2.fromOffset(304, 260)})
    local function label(name, y) return inst("TextLabel", name, menu.body, {Position = UDim2.fromOffset(80, y), Size = UDim2.fromOffset(660, 40), ZIndex = 30}) end
    local nameLabel, oddsLabel, detailLabel = label("Reward", 236), label("Odds", 288), label("Detail", 316)
    local dino = inst("ViewportFrame", "Dino", menu.body, {Size = UDim2.fromOffset(504, 260), Visible = false})
    inst("WorldModel", "WorldModel", dino)
    local paint = setmetatable({}, {__index = function() return function() end end})
    local version = menu.version
    local args = {
        gui = menu.gui, panel = menu.panel, header = menu.header, body = menu.body, eggView = eggView, animateEgg = function() end, splitEgg = function() end, paint = paint,
        nameLabel = nameLabel, oddsLabel = oddsLabel, detailLabel = detailLabel, motion = opts.motion ~= false,
        alive = function() return menu.version == version end, flash = function() end,
        onSkipAll = function() menu.skipAlls += 1 end, onReveal = function() end,
        onNext = function() menu.nexts += 1 end, onAgain = function() menu.agains += 1 end, onAbort = function() menu.aborts += 1 end,
        eggId = "egg-1",
    }
    if opts.result ~= false then
        args.result = {dino = dino, rarity = opts.rarity or 1, color = color(.3, .8, .3), failed = opts.failed == true, shiny = false, big = false, speciesId = "compy",
            remaining = opts.remaining or 0, paintColors = {color(1, 1, 1), color(1, 1, 1)}}
    end
    local handle = Hatch.play(args)
    return handle, args, dino
end
local function resultFor(dino, opts)
    return {dino = dino, rarity = opts.rarity or 1, color = color(.3, .8, .3), failed = opts.failed == true, shiny = false, big = false, speciesId = "compy",
        remaining = opts.remaining or 0, paintColors = {color(1, 1, 1), color(1, 1, 1)}}
end

local function inside(o, x, y) return Rules.contains({x = o.AbsolutePosition.X, y = o.AbsolutePosition.Y, w = o.AbsoluteSize.X, h = o.AbsoluteSize.Y}, x, y) end

-- ===== 1) Reachability: the menu alone, in several shapes. A full-screen Active sibling above it is detected. =====
local shapes = {
    {name = "desktop 1280x720", w = 1280, h = 720, pw = 860, ph = 520, s = 1, origin = Vector2.zero},
    {name = "desktop with a top inset of 36 px", w = 1280, h = 684, pw = 860, ph = 520, s = 1, origin = Vector2.new(0, 36)},
    {name = "ScreenGui answers origin 0 while children sit below the inset", w = 1280, h = 684, pw = 860, ph = 520, s = 1, origin = Vector2.new(0, 36), zero = true},
    {name = "small window, panel scaled 0.8", w = 800, h = 520, pw = 860, ph = 520, s = .8, origin = Vector2.zero},
    {name = "phone landscape 740x340, panel fills the screen", w = 740, h = 340, pw = 732, ph = 332, s = 1, origin = Vector2.zero},
}
for _, shape in shapes do
    local menu = buildMenu(shape.w, shape.h, shape.pw, shape.ph, shape.s, shape.origin, shape.zero)
    check(ModalClose.coverOf(menu.gui, menu.x) == nil, shape.name .. ": X is reachable in the plain menu")
    check(Rules.closeBigEnough(menu.x.AbsoluteSize.X, menu.x.AbsoluteSize.Y), shape.name .. ": X is at least 48 px on screen (BD-1117)")
    local cover = inst("Frame", "Veil", menu.gui, {Size = UDim2.fromScale(1, 1), ZIndex = 46, Active = true})
    check(ModalClose.coverOf(menu.gui, menu.x) == cover, shape.name .. ": the detector finds a full-screen Active Frame above X")
    cover.Visible = false
    check(ModalClose.coverOf(menu.gui, menu.x) == nil, shape.name .. ": a hidden cover does not count")
    cover.Visible, cover.Active = true, false
    check(ModalClose.coverOf(menu.gui, menu.x) == nil, shape.name .. ": a cover that is not Active lets the tap through")
    cover.Active, cover.ZIndex = true, 10
    check(ModalClose.coverOf(menu.gui, menu.x) == nil, shape.name .. ": a cover below the menu does not matter")
    menu.gui:Destroy()
end

-- ===== 2) The hatch screen: X, the end buttons, the backdrop and the skip button stay reachable at every moment =====
local function stagePoints(menu)
    local ax, ay = centre(menu.x)
    local outsideX = menu.panel.AbsolutePosition.X / 2 -- left of the card
    return ax, ay, outsideX
end
for _, shape in shapes do
    for _, motion in {true, false} do
        local label = shape.name .. (if motion then "" else ", Reduce Motion")
        local menu = buildMenu(shape.w, shape.h, shape.pw, shape.ph, shape.s, shape.origin, shape.zero)
        local handle, args, dino = playHatch(menu, {result = false, motion = motion, remaining = 3})
        frames(2)
        local catcher = menu.gui:FindFirstChild("HatchTapCatcher")
        check(catcher ~= nil and catcher.Parent == menu.gui, label .. ": the tap catcher exists")
        if catcher then
            check(ModalClose.coverOf(menu.gui, menu.x) == nil, label .. ": X is reachable while the egg waits for its answer")
            local px, py = centre(menu.panel)
            check(ModalClose.topAt(menu.gui, px, py + 40) == catcher, label .. ": a tap on the card body reaches the catcher")
            check(not inside(catcher, centre(menu.x)), label .. ": the catcher does not cover X")
            check(math.abs(catcher.AbsolutePosition.Y - (menu.header.AbsolutePosition.Y + menu.header.AbsoluteSize.Y)) < .5, label .. ": the catcher starts exactly below the header")
            check(math.abs(catcher.AbsolutePosition.X - menu.panel.AbsolutePosition.X) < .5 and math.abs(catcher.AbsoluteSize.X - menu.panel.AbsoluteSize.X) < .5,
                label .. ": the catcher is exactly as wide as the card")
            check(math.abs(catcher.AbsolutePosition.Y + catcher.AbsoluteSize.Y - (menu.panel.AbsolutePosition.Y + menu.panel.AbsoluteSize.Y)) < .5, label .. ": the catcher ends at the bottom of the card")
            check(catcher.AbsolutePosition.X >= menu.panel.AbsolutePosition.X - .01 and catcher.AbsolutePosition.X + catcher.AbsoluteSize.X <= menu.panel.AbsolutePosition.X + menu.panel.AbsoluteSize.X + .01,
                label .. ": the catcher stays inside the card, left to right")
            check(ModalClose.topAt(menu.gui, menu.bx, menu.by) == menu.shade, label .. ": the corner of the screen is the dark backdrop")
        end
        -- X closes right away, even before the answer arrived; nothing is advanced or claimed
        local x0, nexts0 = menu.closed, menu.nexts
        local top = tapOn(menu, menu.x)
        check(top == menu.x and menu.closed == x0 + 1, label .. ": a tap on X closes the menu (answer still on its way)")
        frames(3)
        check(menu.aborts == 1 and menu.nexts == nexts0 and menu.agains == 0, label .. ": closing is an abort, never 'next egg' or 'try again'")
        check(menu.gui:FindFirstChild("HatchTapCatcher") == nil and menu.gui:FindFirstChild("HatchUiLayer") == nil, label .. ": the catcher and its layer are gone after X")
        check(ModalClose.outsideTap() == true, label .. ": no hatch handler is left behind after X")
        frames(5)
        check(menu.aborts == 1, label .. ": the abort is reported exactly once")
        -- the next egg opens fine and X works again (input was released)
        local menu2 = menu
        menu2.version += 1
        local handle2 = playHatch(menu2, {result = false, motion = motion, remaining = 2})
        frames(2)
        local catcher2 = menu2.gui:FindFirstChild("HatchTapCatcher")
        check(catcher2 ~= nil and ModalClose.coverOf(menu2.gui, menu2.x) == nil, label .. ": X works on the next egg too")
        handle2.cancel()
        menu.gui:Destroy()
    end
end

-- ===== 3) A normal revealed egg: tap the card = next egg once; X = close; the dark backdrop = close after the grace time =====
local function runToReady(menu, handle, dino, opts, seconds)
    frames(2)
    if handle.pending() then handle.supply(resultFor(dino, opts)) end
    frames(math.floor((seconds or 7) * 30))
end
for _, shape in shapes do
    local label = shape.name
    local menu = buildMenu(shape.w, shape.h, shape.pw, shape.ph, shape.s, shape.origin, shape.zero)
    local handle, args, dino = playHatch(menu, {result = false, remaining = 3})
    frames(2)
    -- pending: a tap on the backdrop does nothing (the answer is on its way)
    check(tapAt(menu, menu.bx, menu.by) == menu.shade and menu.closed == 0, label .. ": a backdrop tap while the answer is pending does not close")
    handle.supply(resultFor(dino, {remaining = 3}))
    frames(30) -- 1 s into the build-up (the 0.5 s tap gate has passed)
    -- building: the backdrop tap speeds the egg up like a tap on the egg, it does not close
    local closed0 = menu.closed
    tapAt(menu, menu.bx, menu.by)
    check(menu.closed == closed0, label .. ": a backdrop tap during the build-up does not close")
    frames(20)
    -- cracking / settling: ignored
    frames(60)
    -- ready (hint shown)
    frames(200)
    local hint = menu.body:FindFirstChild("TapHint")
    check(hint ~= nil and hint.Visible, label .. ": the 'tap for next egg' hint is shown")
    local catcher = menu.gui:FindFirstChild("HatchTapCatcher")
    check(catcher ~= nil and ModalClose.coverOf(menu.gui, menu.x) == nil, label .. ": X is reachable when the egg is shown")
    local skip = menu.gui:FindFirstChild("SkipAll", true)
    check(skip ~= nil and skip.Visible and ModalClose.coverOf(menu.gui, skip) == nil and skip.AbsoluteSize.Y >= Rules.MinTarget, label .. ": 'Skip the rest' is shown, reachable and at least 44 px tall")
    -- inside the ready grace period a backdrop tap does not close
    check(menu.closed == closed0, label .. ": nothing closed yet")
    -- a tap on the card moves on, exactly once
    local px, py = centre(menu.panel)
    local nexts0 = menu.nexts
    local landed = tapAt(menu, px, py + 40)
    check(landed == catcher and menu.nexts == nexts0 + 1, label .. ": a tap on the card goes to the next egg")
    tapAt(menu, px, py + 40)
    frames(3)
    check(menu.nexts == nexts0 + 1, label .. ": a second tap does not advance twice")
    check(menu.aborts == 0, label .. ": moving on is not an abort")
    menu.gui:Destroy()
end

do -- the backdrop closes a shown egg after the grace time, and X closes it at any time
    local menu = buildMenu(1280, 720, 860, 520, 1)
    local handle, _, dino = playHatch(menu, {result = false, remaining = 3})
    runToReady(menu, handle, dino, {remaining = 3}, 8)
    local shownAt = now
    check(menu.body:FindFirstChild("TapHint") and menu.body.TapHint.Visible, "ready: hint shown")
    -- the hint appeared a moment ago: ignore the tap that was probably meant for the egg
    local sinceReady = 0
    local closed0 = menu.closed
    -- find the moment the hint appeared by stepping back: the sequence has been ready for a while in this run, so test the grace separately below
    tapAt(menu, menu.bx, menu.by)
    check(menu.closed == closed0 + 1, "ready for a while: a tap on the dark backdrop closes like X")
    frames(3)
    check(menu.aborts == 1 and menu.nexts == 0, "closing from the backdrop is an abort, not a next egg")
    menu.gui:Destroy()
end

do -- the grace period right after the dino is shown
    local menu = buildMenu(1280, 720, 860, 520, 1)
    local handle, _, dino = playHatch(menu, {result = false, remaining = 3})
    frames(2) handle.supply(resultFor(dino, {remaining = 3}))
    local guard = 0
    while not (menu.body:FindFirstChild("TapHint") and menu.body.TapHint.Visible) do
        frames(1) guard += 1
        assert(guard < 1200, "the hint never appeared")
    end
    local closed0 = menu.closed
    tapAt(menu, menu.bx, menu.by)
    check(menu.closed == closed0, "the first moment after the dino is shown: a backdrop tap is ignored (ReadyGrace)")
    frames(math.ceil((Rules.ReadyGrace + .1) * 30))
    tapAt(menu, menu.bx, menu.by)
    check(menu.closed == closed0 + 1, "after the grace time a backdrop tap closes")
    -- X was never blocked by the grace time
    menu.gui:Destroy()
end

-- ===== 4) The last egg and a splat: the end buttons are real buttons, reachable, and each does its own thing =====
for _, kind in {{name = "last egg", failed = false, labels = {"End_done"}}, {name = "splat, nothing left", failed = true, labels = {"End_done", "End_again"}}} do
    local menu = buildMenu(1280, 720, 860, 520, 1)
    local handle, _, dino = playHatch(menu, {result = false, failed = kind.failed, remaining = 0})
    runToReady(menu, handle, dino, {failed = kind.failed, remaining = 0}, 9)
    local row = menu.body:FindFirstChild("EndButtons")
    check(row ~= nil and row.Visible, kind.name .. ": the end buttons are shown")
    local catcher = menu.gui:FindFirstChild("HatchTapCatcher")
    check(catcher ~= nil and ModalClose.coverOf(menu.gui, menu.x) == nil, kind.name .. ": X is reachable")
    if row and catcher then
        check(catcher.AbsolutePosition.Y + catcher.AbsoluteSize.Y <= row.AbsolutePosition.Y + .01, kind.name .. ": the catcher stops above the end buttons")
        for _, name in kind.labels do
            local b = row:FindFirstChild(name)
            check(b ~= nil and ModalClose.coverOf(menu.gui, b) == nil, kind.name .. ": " .. name .. " is reachable")
            check(b ~= nil and b.AbsoluteSize.X >= Rules.MinTarget and b.AbsoluteSize.Y >= Rules.MinTarget, kind.name .. ": " .. name .. " is at least 44 px")
        end
        if kind.failed then
            local nexts0, agains0 = menu.nexts, menu.agains
            tapOn(menu, row:FindFirstChild("End_again"))
            check(menu.agains == agains0 + 1 and menu.nexts == nexts0, kind.name .. ": TRY AGAIN runs its own handler (it used to act as DONE)")
        else
            local nexts0 = menu.nexts
            tapOn(menu, row:FindFirstChild("End_done"))
            check(menu.nexts == nexts0 + 1, kind.name .. ": DONE goes on")
        end
    end
    menu.gui:Destroy()
end

-- ===== 5) Closing mid-reveal never claims anything: no next-egg, no try-again, input released =====
do
    local menu = buildMenu(1280, 720, 860, 520, 1)
    local handle, _, dino = playHatch(menu, {result = false, remaining = 5})
    frames(2) handle.supply(resultFor(dino, {remaining = 5}))
    frames(40)
    tapOn(menu, menu.x)
    frames(4)
    check(menu.aborts == 1 and menu.nexts == 0 and menu.agains == 0 and menu.skipAlls == 0, "X in the middle of the build-up: abort only")
    check(menu.gui:FindFirstChild("HatchTapCatcher") == nil, "X in the middle of the build-up: catcher gone")
    menu.gui:Destroy()
end

-- ===== 6) Layout follows the card: the card slides (open animation) and the catcher goes with it =====
do
    local menu = buildMenu(1280, 720, 860, 520, 1)
    local handle = playHatch(menu, {result = false, remaining = 3})
    frames(2)
    local catcher = menu.gui:FindFirstChild("HatchTapCatcher")
    menu.panel.Position = UDim2.new(.5, 0, .52, 0)
    frames(1)
    check(catcher.AbsolutePosition.Y >= menu.header.AbsolutePosition.Y + menu.header.AbsoluteSize.Y - .01, "the catcher follows a sliding card")
    check(ModalClose.coverOf(menu.gui, menu.x) == nil, "X stays reachable while the card slides")
    menu.panel.Size = UDim2.fromOffset(0, 0)
    frames(1)
    check(not catcher.Visible, "a card with no size gets no catcher")
    handle.cancel()
    menu.gui:Destroy()
end

-- ===== 6b) Hatch polish (BD-1069..1073, docs/193): exact colours, one chip style, the card layout; driven by tools/verify_hatch_polish.py =====
do
    local function rgb255(c) return math.floor(c.R * 255 + .5), math.floor(c.G * 255 + .5), math.floor(c.B * 255 + .5) end
    local function sameRgb(c, want) local r, g, b = rgb255(c) return r == want[1] and g == want[2] and b == want[3] end
    local function overlap(a, b)
        return a.AbsolutePosition.X < b.AbsolutePosition.X + b.AbsoluteSize.X and b.AbsolutePosition.X < a.AbsolutePosition.X + a.AbsoluteSize.X
            and a.AbsolutePosition.Y < b.AbsolutePosition.Y + b.AbsoluteSize.Y and b.AbsolutePosition.Y < a.AbsolutePosition.Y + a.AbsoluteSize.Y
    end
    local CREAM, BLUE = {247, 234, 196}, {36, 132, 211}
    local TL = requireModule(SharedFolder.HatchTimeline)
    TL.batchReset(TL.session) -- earlier sections counted eggs; this one starts a fresh party
    local menu = buildMenu(1280, 720, 860, 520, 1)
    local handle, args, dino = playHatch(menu, {result = false, remaining = 5})
    inst("TextLabel", "TraitBadge", dino, {Text = "BIG"})
    frames(2)
    local result = resultFor(dino, {remaining = 5, rarity = 2})
    result.genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "blue", blend = 50, patternId = "03_round_spots", hatchSuccess = true}
    -- the blended shell tint that used to reach the swatch and the bucket: a Cream-and-Blue mix, NOT either colour
    result.paintColors = {color(.4, .7, .8), color(.2, .5, .3)}
    result.colorReveal = {name = "Cream", tier = 1, tierName = "Common", rgb = CREAM, id = "white"}
    result.secondReveal = {name = "Blue", tier = 1, tierName = "Common", rgb = BLUE, id = "blue"}
    result.patternReveal = {name = "Dots", tier = 1, tierName = "Common", plain = false}
    handle.supply(result)
    frames(30 * 2.6) -- both buckets have hit the egg, both chips and the pattern chip are shown (the burst, at 3.6 s, hides them)
    local function find(name) return menu.gui:FindFirstChild(name, true) end
    -- 1. the chip swatch is the named colour's own rgb
    for i, want in {CREAM, BLUE} do
        local chip = find("PaintChip" .. i)
        check(chip ~= nil and chip.Visible, "polish: colour chip " .. i .. " is shown")
        local swatch = chip and chip:FindFirstChild("Swatch")
        check(swatch ~= nil and sameRgb(swatch.BackgroundColor3, want), "polish: chip " .. i .. " swatch is exactly the named colour's palette rgb (not the shell tint)")
        local group = find("PaintBucket" .. i)
        local parts = 0
        for _, d in group:GetDescendants() do
            if string.sub(d.Name, 1, 11) == "BucketPaint" then
                parts += 1
                check(sameRgb(d.BackgroundColor3, want), "polish: bucket " .. i .. " paint part " .. d.Name .. " is exactly the palette colour")
            end
        end
        check(parts >= 5, "polish: bucket " .. i .. " has a paint surface, a cap and drips (" .. parts .. " paint parts)")
    end
    -- 2. one chip style: rounded rectangles (never full-round), 3 px outline, text never under 14 px
    local chipNames = {"PaintChip1", "PaintChip2", "PatternChip", "ConditionChip", "RarityPill", "StopTag"}
    local checked = 0
    local function chipLike(o, name)
        local corner, stroke = o:FindFirstChildOfClass("UICorner"), o:FindFirstChildOfClass("UIStroke")
        check(corner ~= nil and corner.CornerRadius.Scale == 0 and corner.CornerRadius.Offset > 0 and corner.CornerRadius.Offset <= 12, "polish: " .. name .. " has a px corner radius (no full-round pill)")
        check(stroke ~= nil and stroke.Thickness == 3, "polish: " .. name .. " has the 3 px outline")
        checked += 1
    end
    for _, name in chipNames do
        local o = find(name)
        check(o ~= nil, "polish: " .. name .. " exists")
        if o then chipLike(o, name) end
    end
    for _, d in menu.gui:GetDescendants() do
        if d.Name == "Swatch" or d.Name == "TierBadge" then chipLike(d, d.Name) end
        if d:IsA("UITextSizeConstraint") and d.Parent and d.Parent.Parent and (d.Parent.Parent.Name == "TierBadge" or string.sub(d.Parent.Parent.Name, 1, 9) == "PaintChip" or d.Parent.Parent.Name == "PatternChip") then
            check(d.MinTextSize >= 14, "polish: chip text is at least 14 px")
        end
    end
    for _, d in menu.gui:GetDescendants() do
        if d.Name == "Ribbon" then
            local corner = d:FindFirstChildOfClass("UICorner")
            check(corner ~= nil and corner.CornerRadius.Scale == 0, "polish: ribbons are rounded rectangles too")
        end
    end
    check(checked >= 10, "polish: enough chips were examined (" .. checked .. ")")
    -- 3. the counter is in the header, left of X, and nowhere near the dinosaur
    local counter = find("EggCounter")
    check(counter ~= nil and counter.Parent == menu.header, "polish: the Egg N of M counter lives in the header strip")
    if counter then
        check(counter.Visible and counter.Text == "Egg 1 of 6", "polish: the counter reads 'Egg 1 of 6' (is '" .. tostring(counter.Text) .. "')")
        check(counter.AbsolutePosition.X + counter.AbsoluteSize.X <= menu.x.AbsolutePosition.X, "polish: the counter ends left of X")
        check(not overlap(counter, dino), "polish: the counter does not touch the dinosaur view")
        check(not overlap(counter, menu.x), "polish: the counter does not touch X")
    end
    -- 4. card layout: the view starts at the top of the body, ends where the name starts; no label of its own; the stop tag names the reason
    frames(30 * 6) -- the reveal has settled (the dinosaur pops in from a small scale)
    check(dino.AbsolutePosition.Y >= menu.body.AbsolutePosition.Y - .5, "polish: the dinosaur view does not start above the card body")
    check(dino.AbsolutePosition.Y + dino.AbsoluteSize.Y <= args.nameLabel.AbsolutePosition.Y + .5, "polish: the dinosaur view ends where the name starts")
    check(dino:FindFirstChild("TraitBadge").Visible == false, "polish: the view's own BIG / SHINY label is hidden")
    check(stubs.InspectView.last ~= nil and stubs.InspectView.last.baseZoom <= 1.2, "polish: the dinosaur is not zoomed so far that the head is cut")
    local tag = find("StopTag")
    check(tag ~= nil and tag.Visible, "polish: a Rainbow egg shows why Skip stops")
    if tag then
        local label = tag:FindFirstChild("Text")
        check(label ~= nil and label.Text == "Rainbow egg!", "polish: the stop tag names the Rainbow egg")
        check(tag:FindFirstChild("StopLine") ~= nil and tag.StopLine.Text == "Skip stops here", "polish: the stop tag says what happens")
        check(not overlap(tag, dino) or tag.AbsolutePosition.X + tag.AbsoluteSize.X <= dino.AbsolutePosition.X + dino.AbsoluteSize.X * .42, "polish: the stop tag stays out of the dinosaur's middle")
    end
    handle.cancel()
    frames(2)
    check(find("EggCounter") == nil, "polish: the counter is removed from the header when the egg ends")
    menu.gui:Destroy()
    -- 5. a plain egg shows no stop tag
    local menu2 = buildMenu(1280, 720, 860, 520, 1)
    local h2, _, dino2 = playHatch(menu2, {result = false, remaining = 5})
    frames(2)
    h2.supply(resultFor(dino2, {remaining = 5}))
    frames(30 * 8)
    check(menu2.gui:FindFirstChild("StopTag", true) == nil, "polish: an ordinary egg shows no stop tag")
    h2.cancel()
    menu2.gui:Destroy()
end

-- ===== 7) The pure rules =====
check(Rules.outsideAction(true, "build", nil) == "ignore", "rule: pending is ignored")
check(Rules.outsideAction(false, "build", nil) == "tap", "rule: build-up counts as a tap")
check(Rules.outsideAction(false, "burst", nil) == "ignore" and Rules.outsideAction(false, "settle", nil) == "ignore", "rule: cracking is ignored")
check(Rules.outsideAction(false, "ready", Rules.ReadyGrace - .01) == "ignore" and Rules.outsideAction(false, "ready", Rules.ReadyGrace) == "close", "rule: close after the grace time")
check(Rules.tapZone({x = 0, y = 0, w = 100, h = 100}, 20, nil).y == 20 and Rules.tapZone({x = 0, y = 0, w = 100, h = 100}, 20, 80).h == 60, "rule: tap zone")
check(Rules.tapZone({x = 0, y = 0, w = 0, h = 100}, 20, nil) == nil and Rules.tapZone({x = 0, y = 0, w = 100, h = 100}, 100, nil) == nil, "rule: empty zone")
check(Rules.contains({x = 10, y = 10, w = 10, h = 10}, 10, 10) and not Rules.contains({x = 10, y = 10, w = 10, h = 10}, 20, 10), "rule: edges")
for _, mode in {"browse", "confirm", "resume", "unavailable"} do check(Rules.fusionOutsideCloses(mode), "fusion backdrop closes " .. mode) end
for _, mode in {"fusing", "reveal", "details", "nonsense"} do check(not Rules.fusionOutsideCloses(mode), "fusion backdrop leaves " .. mode .. " alone") end
check(Rules.bigEnough(44, 44) and not Rules.bigEnough(43, 60), "rule: 44 px")
check(Rules.closeBigEnough(48, 48) and not Rules.closeBigEnough(47, 60) and not Rules.closeBigEnough(60, 44) and Rules.MinClose > Rules.MinTarget, "rule: the X needs 48 px")

if failures > 0 then error(failures .. " close-path checks failed") end
print("Close paths smoke passed: X, the dark backdrop, the end buttons and 'Skip the rest' reachable on " .. #shapes .. " screen shapes (with and without Reduce Motion), backdrop rules by moment, X never claims or advances, exactly-once abort, input released (" .. created .. " mock instances)")
