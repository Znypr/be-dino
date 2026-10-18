-- Offline smoke for the BD-1039 Pattern and Colour Index client modules (driven by tools/verify_pattern_colour_index.py).
-- The same minimal Roblox mock as fusion_ui_smoke.luau (Instance tree, signals, scheduler) runs the REAL IndexTabs and PatternColourCards
-- (and the real PatternColourIndex, GeneBoost, RarityCurve, ProgressionConfig, AssetSlots) against a fake Index screen (header with title
-- and X, body) and fake owner-only values. UITheme, PrivateState, ModalCompact and the config are stubs. This proves control flow, the words
-- and numbers on the cards, the tabs, the dot and the flag-off identity. It does NOT prove layout, drawing, touch or phone fit: that is Studio.
-- MODULE_SOURCES is injected by the verifier.

-- ===== Scheduler =====
local now = 0
local queue = {}
local seq = 0
local function push(t, co) seq += 1 table.insert(queue, {t = t, co = co, seq = seq}) end
local function resume(co, ...)
    local ok, err = coroutine.resume(co, ...)
    if not ok then error(debug.traceback(co, tostring(err)), 0) end
end
local task = {}
function task.spawn(f, ...)
    local co = if type(f) == "thread" then f else coroutine.create(f)
    resume(co, ...)
    return co
end
task.defer = task.spawn
function task.delay(t, f, ...)
    local args = table.pack(...)
    push(now + (t or 0), coroutine.create(function() f(table.unpack(args, 1, args.n)) end))
end
function task.wait(t)
    push(now + (t or .03), coroutine.running())
    return coroutine.yield()
end
local function runFor(seconds)
    local stop, steps = now + seconds, 0
    while true do
        table.sort(queue, function(a, b) if a.t ~= b.t then return a.t < b.t end return a.seq < b.seq end)
        local item = queue[1]
        if not item or item.t > stop then break end
        table.remove(queue, 1)
        now = math.max(now, item.t)
        steps += 1
        assert(steps < 200000, "scheduler runaway")
        if coroutine.status(item.co) == "suspended" then resume(item.co) end
    end
    now = stop
end
os = {clock = function() return now end, time = function() return 0 end}

-- ===== Datatypes =====
local function signal()
    local s = {conns = {}}
    function s:Connect(f) table.insert(self.conns, f) return {Disconnect = function() end} end
    s.Once = s.Connect
    function s:Fire(...) for _, f in table.clone(self.conns) do f(...) end end
    return s
end
local function vec(x, y) return {X = x, Y = y} end
Vector2 = {new = vec, zero = vec(0, 0)}
local udimMt = {}
udimMt.__add = function(a, b)
    return setmetatable({X = {Scale = a.X.Scale + b.X.Scale, Offset = a.X.Offset + b.X.Offset},
        Y = {Scale = a.Y.Scale + b.Y.Scale, Offset = a.Y.Offset + b.Y.Offset}}, udimMt)
end
UDim = {new = function(s, o) return {Scale = s, Offset = o} end}
UDim2 = {new = function(a, b, c, d) return setmetatable({X = {Scale = a or 0, Offset = b or 0}, Y = {Scale = c or 0, Offset = d or 0}}, udimMt) end}
UDim2.fromScale = function(x, y) return UDim2.new(x, 0, y, 0) end
UDim2.fromOffset = function(x, y) return UDim2.new(0, x, 0, y) end
local function color(r, g, b) return {R = r, G = g, B = b, Lerp = function(self) return self end} end
Color3 = {new = color, fromRGB = function(r, g, b) return color(r / 255, g / 255, b / 255) end}
ColorSequence = {new = function() return {} end}
TweenInfo = {new = function() return {} end}
Enum = setmetatable({}, {__index = function(_, k) return setmetatable({}, {__index = function(_, v) return k .. "." .. v end}) end})

-- ===== Instances =====
Instance = {}
local instanceMt = {}
local methods = {}
local events = {Activated = true, MouseEnter = true, MouseLeave = true, SelectionGained = true, SelectionLost = true,
    InputBegan = true, InputEnded = true, Destroying = true, Changed = true}
local guiClasses = {Frame = true, TextLabel = true, TextButton = true, ScrollingFrame = true, ViewportFrame = true, ImageLabel = true}
local created = 0
function Instance.new(class)
    created += 1
    return setmetatable({__props = {ClassName = class, Name = class, Visible = true, Enabled = true, ZIndex = 1,
        AbsoluteSize = vec(1280, 720), Text = ""}, __children = {}, __attrs = {}, __events = {}}, instanceMt)
end
instanceMt.__index = function(self, key)
    local m = methods[key]
    if m then return m end
    if events[key] then
        local e = rawget(self, "__events")
        e[key] = e[key] or signal()
        return e[key]
    end
    local p = rawget(self, "__props")[key]
    if p ~= nil then return p end
    for _, child in rawget(self, "__children") do if child.Name == key then return child end end
    return nil
end
instanceMt.__newindex = function(self, key, value)
    local props = rawget(self, "__props")
    if key == "Parent" then
        local old = props.Parent
        if old then
            local list = rawget(old, "__children")
            local i = table.find(list, self)
            if i then table.remove(list, i) end
        end
        props.Parent = value
        if value then table.insert(rawget(value, "__children"), self) end
        return
    end
    props[key] = value
end
function methods.IsA(self, class) return self.ClassName == class or (class == "GuiObject" and guiClasses[self.ClassName] == true) or class == "Instance" end
function methods.GetChildren(self) return table.clone(rawget(self, "__children")) end
function methods.GetDescendants(self)
    local r = {}
    local function walk(i) for _, c in rawget(i, "__children") do table.insert(r, c) walk(c) end end
    walk(self)
    return r
end
function methods.FindFirstChild(self, name)
    for _, c in rawget(self, "__children") do if c.Name == name then return c end end
    return nil
end
function methods.WaitForChild(self, name) return assert(methods.FindFirstChild(self, name), "WaitForChild " .. name) end
function methods.FindFirstChildOfClass(self, class)
    for _, c in rawget(self, "__children") do if c.ClassName == class then return c end end
    return nil
end
function methods.ClearAllChildren(self) for _, c in methods.GetChildren(self) do c:Destroy() end end
function methods.Destroy(self)
    local e = rawget(self, "__events").Destroying
    if e then e:Fire() end
    for _, c in methods.GetChildren(self) do c:Destroy() end
    self.Parent = nil
end
function methods.SetAttribute(self, k, v) rawget(self, "__attrs")[k] = v end
function methods.GetAttribute(self, k) return rawget(self, "__attrs")[k] end
function methods.GetPropertyChangedSignal() return signal() end


-- ===== Services and tree =====
local function folder(name, parent)
    local f = Instance.new("Folder")
    f.Name = name
    if parent then f.Parent = parent end
    return f
end
local Replicated = folder("ReplicatedStorage")
local SharedFolder = folder("Shared", Replicated)
local ClientFolder = folder("Client")
local registry = {} -- raw JSON token -> decoded table (the mock has no JSON parser; the stub PrivateState hands out tokens)
local Services = {
    ReplicatedStorage = Replicated,
    HttpService = {JSONDecode = function(_, raw) return assert(registry[raw], "unknown raw value " .. tostring(raw)) end},
}
game = {GetService = function(_, name) return assert(Services[name], "service " .. name) end}

-- ===== Stubs =====
local sources = MODULE_SOURCES
local loaded = {}
local Theme = {MotionEnabled = true, Colors = {panel = color(0, 0, 0), card = color(.2, .2, .3), outline = color(0, 0, 0),
    text = color(1, 1, 1), accent = color(0, 1, 0), gold = color(1, 1, 0), blue = color(0, 0, 1), purple = color(1, 0, 1), red = color(1, 0, 0)}}
Theme.RarityColors = {color(.5, .55, .6), color(.1, .9, .1), color(.2, .8, 1), color(.8, .3, 1), color(1, .8, .2), color(.9, .2, .2)}
for i, n in {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"} do Theme.RarityColors[n] = Theme.RarityColors[i] end
Theme.TextStyle = {apply = function(label) label.TextStrokeTransparency = 1 local stroke = Instance.new("UIStroke") stroke.Parent = label return stroke end}
function Theme.decorate(object) Instance.new("UIStroke").Parent = object Instance.new("UICorner").Parent = object end
function Theme.icon() return nil end
function Theme.animate(target, _, goals) for k, v in goals do target[k] = v end end
local Config = {PatternColourIndexEnabled = false, SecretSpeciesEnabled = false,
    SpeciesOrder = {"compy", "raptor", "triceratops", "stegosaurus", "tyrannosaurus"},
    SpeciesDisplayNames = {compy = "Compy", raptor = "Raptor", triceratops = "Triceratops", stegosaurus = "Stegosaurus", tyrannosaurus = "T-Rex"}}
local values = {}
local listeners = {}
local PrivateState = {ready = true}
function PrivateState.isReady() return PrivateState.ready end
function PrivateState.str(name, fallback) return values[name] or fallback or "" end
function PrivateState.onChanged(name, fn) listeners[name] = listeners[name] or {} table.insert(listeners[name], fn) end
local function changed(name) for _, fn in listeners[name] or {} do fn(values[name]) end end
local partsOn = true
local bodyHeight = 402
local panel, header, heading, closeButton, body
local Compact = {}
function Compact.parts() return if partsOn then {gui = panel, panel = panel, header = header, heading = heading, body = body, closeButton = closeButton} else nil end
function Compact.bodyHeight() return bodyHeight end
local stubs = {
    UITheme = Theme, Config = Config, PrivateState = PrivateState, ModalCompact = Compact,
    SecretSpeciesConfig = {indexOrder = function(base) return base end, name = function(id) return id end},
    NavigationArtwork = {collection = "dinos"},
}
local function requireModule(inst)
    local name = inst.Name
    if stubs[name] then return stubs[name] end
    if loaded[name] == nil then loaded[name] = sources[name](inst, requireModule) end
    return loaded[name]
end
for _, name in {"Config", "ProgressionConfig", "RarityCurve", "GeneBoost", "PatternColourIndex", "AssetSlots", "UITheme", "SecretSpeciesConfig", "NavigationArtwork"} do
    local m = Instance.new("ModuleScript") m.Name = name m.Parent = SharedFolder
end
for _, name in {"IndexTabs", "PatternColourCards", "PrivateState", "ModalCompact"} do
    local m = Instance.new("ModuleScript") m.Name = name m.Parent = ClientFolder
end
local PC = requireModule(SharedFolder.ProgressionConfig)
local Slots = requireModule(SharedFolder.AssetSlots)

-- ===== Helpers =====
local function byName(root, name)
    for _, i in root:GetDescendants() do if i.Name == name then return i end end
    return nil
end
local function allNamed(root, prefix)
    local list = {}
    for _, i in root:GetDescendants() do if string.sub(i.Name, 1, #prefix) == prefix then table.insert(list, i) end end
    return list
end
local function textOf(root, name) local i = assert(byName(root, name), "missing " .. name) return i.Text end
local function press(b) assert(b, "missing button") b.Activated:Fire() end
local function clearBody() -- what Bootstrap's open() does before it draws a screen
    body:ClearAllChildren()
end
local function freshScreen()
    panel = Instance.new("Frame") panel.Name = "Panel"
    header = Instance.new("Frame") header.Name, header.ZIndex, header.Parent = "Header", 22, panel
    heading = Instance.new("TextLabel") heading.Name, heading.Text, heading.Parent = "Heading", "Dino Index", header
    closeButton = Instance.new("TextButton") closeButton.Name, closeButton.Parent = "X", header
    closeButton.Position, closeButton.Size = UDim2.fromOffset(770, 1), UDim2.fromOffset(80, 62)
    body = Instance.new("Frame") body.Name, body.ZIndex, body.Parent = "Body", 23, panel
end
local tokenN = 0
local function setValue(name, tbl)
    tokenN += 1
    local token = name .. "#" .. tokenN
    registry[token] = tbl
    values[name] = token
    changed(name)
end
local function variant(pattern, main, accent, count)
    return {count = count or 1, genes = {patternId = pattern, primaryColorId = main, secondaryColorId = accent}}
end
local Tabs = requireModule(ClientFolder.IndexTabs)
local opened = {}
local function openFn(name) table.insert(opened, name) end
local function tabButtons()
    local bar = assert(byName(header, "IndexTabs"), "tab bar")
    local list = {}
    for _, name in {"dinos", "patterns", "colours"} do list[name] = assert(byName(bar, "Tab_" .. name), "tab " .. name) end
    return list
end
local function cardMap()
    local map = {}
    for _, card in allNamed(assert(byName(body, "IndexGrid")), "Card_") do map[string.sub(card.Name, 6)] = card end
    return map
end
local function pipsOn(card) local n = 0 for _, d in card:GetDescendants() do if d.Name == "PipOn" then n += 1 end end return n end
local function pipsOff(card) local n = 0 for _, d in card:GetDescendants() do if d.Name == "PipOff" then n += 1 end end return n end
local function strokeOf(card) for _, c in card:GetChildren() do if c.ClassName == "UIStroke" then return c end end return nil end

-- ===== 1. Flag off = identity =====
freshScreen()
local before = #body:GetDescendants() + #header:GetDescendants()
assert(Tabs.mount(openFn) == false, "flag off: mount draws nothing")
assert(#body:GetDescendants() + #header:GetDescendants() == before and heading.Visible == true, "flag off: no instance, the title stays")
local fakeButton = Instance.new("TextButton") fakeButton:SetAttribute("Destination", "collection")
Tabs.attachDot({fakeButton})
assert(#fakeButton:GetDescendants() == 0 and next(listeners) == nil, "flag off: no dot, no listener")

-- ===== 2. Flag on, nothing found: tab bar on the Dinos tab =====
Config.PatternColourIndexEnabled = true
setValue("CollectionJson", {compy = {base = 1, variants = {}}})
setValue("DiscoveryJson", {colours = 0, patterns = 0, mutations = 0})
freshScreen()
assert(Tabs.mount(openFn) == false, "Dinos tab: Bootstrap draws the Dino Index itself")
local bar = assert(byName(header, "IndexTabs"), "tab bar in the header")
assert(heading.Visible == false, "the title makes room for the tabs")
local tabs = tabButtons()
assert(textOf(tabs.dinos, "TabText") == "Dinos" and textOf(tabs.patterns, "TabText") == "Patterns" and textOf(tabs.colours, "TabText") == "Colours")
assert(bar.Size.Y.Offset == closeButton.Size.Y.Offset and bar.Size.Y.Offset >= 44, "tabs are as tall as X (thumb size)")
for _, b in tabs do assert(b.Size.Y.Scale == 1 and b.Size.Y.Offset == 0, "tab fills the bar height") end
assert(tabs.dinos:GetAttribute("Active") == true and tabs.patterns:GetAttribute("Active") == false)
assert(byName(bar, "PlaceholderGlyph") ~= nil, "placeholder glyphs until the tab icons are bound")
assert(byName(body, "IndexTabsMark") ~= nil)

-- ===== 3. Patterns tab, nothing found: grey cards, dim tier colours =====
press(tabs.patterns)
assert(Tabs.lastTab() == "patterns" and tabs.patterns:GetAttribute("Active") == true)
assert(textOf(body, "IndexHeader") == "Patterns 0 / 8", textOf(body, "IndexHeader"))
local grid = assert(byName(body, "IndexGrid"))
local cardFrames = allNamed(grid, "Card_")
assert(#cardFrames == #PC.EggPatterns and #cardFrames == 8, "one card per pattern in the config table")
local legendaryBorder
for _, card in cardFrames do
    assert(card:GetAttribute("Found") == false)
    assert(textOf(card, "Name") == "???" and textOf(card, "Line") == "Not found yet", "hidden name, plain line")
    assert(byName(card, "Question") and byName(card, "Question").Text == "?", "question mark tile")
    assert(textOf(card, "Tier") ~= "")
    assert(byName(card, "PlaceholderTile") == nil, "no tile art on a card not found")
    if card:GetAttribute("Tier") == "Legendary" then legendaryBorder = strokeOf(card).Color end
end
assert(legendaryBorder and legendaryBorder.R ~= Theme.RarityColors.Legendary.R, "the tier colour is dimmed on a card not found")
assert(grid.CanvasSize.Y.Offset == 3 * (176 + 12) and grid.Size.X.Offset == 824, "three across, one scroll")
for _, card in cardFrames do assert(card.Size.X.Offset >= 264 and card.Size.Y.Offset >= 150, "at least as big as a Dino Index card") end
for _, d in grid:GetDescendants() do if d.ClassName == "TextLabel" then assert(d.TextSize >= 18, "card text " .. d.Text) end end

-- ===== 4. The player owns dinos: found cards, kid words, Found on =====
setValue("CollectionJson", {
    compy = {base = 0, variants = {a = variant("03_round_spots", "blue", "red", 2), b = variant("07_diamond_scales", "white", "white")}},
    raptor = {base = 0, variants = {c = variant("03_round_spots", "blue", "blue")}},
    triceratops = {base = 0, variants = {d = variant("06_wavy_stripes", "green", "teal", 0)}}, -- count 0: not owned
})
setValue("DiscoveryJson", {colours = 3, patterns = 2, mutations = 0, ids = {patterns = {"02_emerald_islands"}, colours = {"black"}}}) -- Islands and Black were found, then fused away
clearBody()
assert(byName(header, "IndexTabs") == nil and heading.Visible == true, "the old bar is gone and the title is back")
assert(Tabs.mount(openFn) == true, "the last tab (Patterns) is remembered: this module draws it")
assert(textOf(body, "IndexHeader") == "Patterns 3 / 8", textOf(body, "IndexHeader"))
local found = cardMap()
assert(textOf(found["03_round_spots"], "Name") == "Dots" and textOf(found["03_round_spots"], "Line") == "Found on: Compy, Raptor", textOf(found["03_round_spots"], "Line"))
assert(textOf(found["07_diamond_scales"], "Name") == "Diamonds" and textOf(found["07_diamond_scales"], "Line") == "Found on: Compy")
assert(textOf(found["02_emerald_islands"], "Name") == "Islands" and textOf(found["02_emerald_islands"], "Line") == "Found before", "found in the log, no dino of it left")
assert(found["06_wavy_stripes"]:GetAttribute("Found") == false and textOf(found["06_wavy_stripes"], "Name") == "???", "a count-0 variant is not owned")
assert(found["03_round_spots"]:GetAttribute("Found") == true and found["03_round_spots"]:GetAttribute("Tier") == "Common")
assert(pipsOn(found["03_round_spots"]) == 0 and pipsOff(found["03_round_spots"]) == 5 and textOf(found["03_round_spots"], "Boost") == "No boost")
assert(pipsOn(found["02_emerald_islands"]) == 3 and textOf(found["02_emerald_islands"], "Boost") == "Boost 3 of 5")
assert(pipsOn(found["07_diamond_scales"]) == 4 and pipsOn(found["06_wavy_stripes"]) == 2, "pips are shown on cards not found too")
assert(byName(found["03_round_spots"], "PlaceholderTile") ~= nil and byName(found["03_round_spots"], "PatternPicture") == nil, "no icon yet: a plain tinted tile")
Slots.Images["pattern_03_round_spots"] = "rbxassetid://123456789"
clearBody() Tabs.mount(openFn)
local dots = cardMap()["03_round_spots"]
assert(byName(dots, "PatternPicture") ~= nil and byName(dots, "PatternPicture").Image == "rbxassetid://123456789" and byName(dots, "PlaceholderTile") == nil, "a bound slot shows the picture")
Slots.Images["pattern_03_round_spots"] = ""

-- ===== 5. Colours tab: the real rgb, main AND accent colour count =====
tabs = tabButtons()
press(tabs.colours)
assert(Tabs.lastTab() == "colours" and textOf(body, "IndexHeader") == "Colours 4 / 9", textOf(body, "IndexHeader")) -- blue, red (accent), white, black (log)
local colourCards = cardMap()
assert(#PC.EggColors == 9)
assert(colourCards["red"]:GetAttribute("Found") == true and textOf(colourCards["red"], "Name") == "Red" and textOf(colourCards["red"], "Line") == "Found on: Compy", "the accent colour counts")
assert(colourCards["blue"]:GetAttribute("Found") == true and textOf(colourCards["blue"], "Line") == "Found on: Compy, Raptor")
assert(colourCards["black"]:GetAttribute("Found") == true and textOf(colourCards["black"], "Line") == "Found before")
assert(colourCards["green"]:GetAttribute("Found") == false and textOf(colourCards["green"], "Name") == "???")
local swatch = byName(colourCards["blue"], "Tile")
assert(swatch.BackgroundColor3.R == 36 / 255 and swatch.BackgroundColor3.B == 211 / 255, "the swatch is the real colour")
assert(pipsOn(colourCards["red"]) == 5 and textOf(colourCards["red"], "Tier") == "Mythic" and pipsOn(colourCards["blue"]) == 0)
assert(byName(colourCards["green"], "Tile").BackgroundColor3.R ~= 29 / 255, "a colour not found is a grey tile, not its real colour")

-- ===== 6. Back to Dinos asks Bootstrap to open the collection =====
press(tabs.dinos)
assert(Tabs.lastTab() == "dinos" and opened[#opened] == "collection" and #opened == 1)
clearBody() -- Bootstrap's open() clears the body, then draws the Dino Index
assert(byName(header, "IndexTabs") == nil and heading.Visible == true)
assert(Tabs.mount(openFn) == false and byName(header, "IndexTabs") ~= nil and heading.Visible == false, "Dinos tab: bar back, Bootstrap draws the list")
clearBody() -- any other screen
assert(byName(header, "IndexTabs") == nil and heading.Visible == true, "another screen: no tabs left behind")
partsOn = false
assert(Tabs.mount(openFn) == false, "before the modal exists nothing happens")
partsOn = true

-- ===== 7. The dot on the Dinos button =====
freshScreen()
local dinosButton = Instance.new("TextButton") dinosButton:SetAttribute("Destination", "collection")
local otherButton = Instance.new("TextButton") otherButton:SetAttribute("Destination", "eggs")
Tabs.attachDot({otherButton, dinosButton})
local dot = byName(dinosButton, "IndexDot")
assert(dot and dot.Visible == false and byName(otherButton, "IndexDot") == nil, "no dot at first: what you already found is not new")
setValue("DiscoveryJson", {colours = 5, patterns = 3, mutations = 0, ids = {patterns = {"02_emerald_islands", "04_bold_patches"}, colours = {"black", "green"}}})
assert(dot.Visible == true, "a new find shows the dot")
Tabs.mount(openFn)
press(tabButtons().patterns)
assert(dot.Visible == false, "looking at the Patterns tab clears the dot")
setValue("CollectionJson", {compy = {base = 0, variants = {a = variant("03_round_spots", "blue", "red", 2), b = variant("07_diamond_scales", "white", "white"), z = variant("05_horizontal_bands", "pink", "pink")}}, raptor = {base = 0, variants = {c = variant("03_round_spots", "blue", "blue")}}})
assert(dot.Visible == true, "another new find, dot again")
PrivateState.ready = false
setValue("DiscoveryJson", {colours = 5, patterns = 3, mutations = 0})
PrivateState.ready = true

print("Pattern and Colour Index smoke passed: flag off draws nothing, tabs in the header as tall as X, remembered tab, grey cards with dim tier colours, found cards with kid names + Found on + pips, main and accent colours count, fused-away finds stay found, bound icon slot, Dinos tab hands back to Bootstrap, other screens remove the bar, the dot")
