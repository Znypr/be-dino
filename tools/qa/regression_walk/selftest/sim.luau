-- BD-541 offline self-test harness for tools/qa/regression_walk (driven by tools/verify_regression_walk.py; never ships, never runs in Studio).
-- A minimal Roblox mock (scheduler with virtual time, Instance tree, signals, vectors, services) plus a tiny Be Dino simulation: the same
-- remote names, attributes, button names and screen titles the real client and server use. The REAL walk scripts run against it as
-- Studio snippets would; the real pure modules (Config, ProgressionRules, CaveGateRules, SettingsModel, ...) are loaded from src/.
-- This proves the scripts parse, run their 13 steps in order and judge PASS / FAIL / ODD as intended. It proves nothing about Studio.
-- Injected by the verifier: SCRIPTS (walk files), MODULES (real src/shared modules), SCENARIO.
local SCRIPTS = SCRIPTS_INJECTED
local MODULES = MODULES_INJECTED
local SCENARIO = SCENARIO_INJECTED
local OUT = {}
local rawprint = print
print = function(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
    local s = table.concat(parts, "\t")
    table.insert(OUT, s)
    rawprint(s)
end

-- ===== scheduler (virtual time) =====
local now = 0
local queue, seq = {}, 0
local function push(t, co) seq += 1 table.insert(queue, {t = t, co = co, seq = seq}) end
local function resume(co, ...)
    local ok, err = coroutine.resume(co, ...)
    if not ok then error(debug.traceback(co, tostring(err)), 0) end
end
task = {}
function task.spawn(f, ...) local co = coroutine.create(f) resume(co, ...) return co end
task.defer = task.spawn
function task.delay(t, f, ...) local a = table.pack(...) push(now + (t or 0), coroutine.create(function() f(table.unpack(a, 1, a.n)) end)) end
function task.wait(t) push(now + (t or 0.03), coroutine.running()) return coroutine.yield() end
function time() return now end
os = {clock = function() return now end, time = function() return 1000 + math.floor(now) end, date = os.date}

-- ===== datatypes =====
local V3 = {}
V3.__index = function(v, k)
    if k == "Magnitude" then return math.sqrt(v.X * v.X + v.Y * v.Y + v.Z * v.Z) end
    if k == "Unit" then local m = math.sqrt(v.X * v.X + v.Y * v.Y + v.Z * v.Z) return if m == 0 then v else setmetatable({X = v.X / m, Y = v.Y / m, Z = v.Z / m}, V3) end
    return nil
end
V3.__add = function(a, b) return setmetatable({X = a.X + b.X, Y = a.Y + b.Y, Z = a.Z + b.Z}, V3) end
V3.__sub = function(a, b) return setmetatable({X = a.X - b.X, Y = a.Y - b.Y, Z = a.Z - b.Z}, V3) end
V3.__mul = function(a, b) if type(b) == "number" then return setmetatable({X = a.X * b, Y = a.Y * b, Z = a.Z * b}, V3) end return setmetatable({X = a * b.X, Y = a * b.Y, Z = a * b.Z}, V3) end
V3.__div = function(a, b) return setmetatable({X = a.X / b, Y = a.Y / b, Z = a.Z / b}, V3) end
Vector3 = {new = function(x, y, z) return setmetatable({X = x or 0, Y = y or 0, Z = z or 0}, V3) end}
Vector3.zero = Vector3.new(0, 0, 0)
local V2 = {}
V2.__add = function(a, b) return setmetatable({X = a.X + b.X, Y = a.Y + b.Y}, V2) end
V2.__sub = function(a, b) return setmetatable({X = a.X - b.X, Y = a.Y - b.Y}, V2) end
V2.__div = function(a, b) return setmetatable({X = a.X / b, Y = a.Y / b}, V2) end
V2.__mul = function(a, b) return setmetatable({X = a.X * b, Y = a.Y * b}, V2) end
Vector2 = {new = function(x, y) return setmetatable({X = x or 0, Y = y or 0}, V2) end}
Vector2.zero = Vector2.new(0, 0)
local CF = {}
CF.__index = function(cf, k)
    if k == "PointToWorldSpace" then return function(self, v) return self.Position + v end end
    return nil
end
CFrame = {new = function(p) return setmetatable({Position = p or Vector3.zero, LookVector = Vector3.new(0, 0, -1)}, CF) end}
Enum = setmetatable({}, {__index = function(_, k) return setmetatable({}, {__index = function(_, v) return k .. "." .. v end}) end})
local function color(r, g, b) return {R = r, G = g, B = b} end
Color3 = {fromRGB = function(r, g, b) return color(r / 255, g / 255, b / 255) end, new = color}
local function signal()
    local s = {conns = {}}
    function s:Connect(f)
        local rec = {f = f}
        table.insert(self.conns, rec)
        return {Disconnect = function() rec.dead = true end}
    end
    function s:Fire(...) for _, rec in table.clone(self.conns) do if not rec.dead then rec.f(...) end end end
    return s
end

-- ===== instances =====
local hierarchy = {
    GuiObject = {Frame = true, TextLabel = true, TextButton = true, ScrollingFrame = true, ImageLabel = true, ViewportFrame = true},
    BasePart = {Part = true, MeshPart = true},
}
local Inst = {}
local methods = {}
Inst.__index = function(self, key)
    local m = methods[key]
    if m then return m end
    local props = rawget(self, "props")
    local v = props[key]
    if v ~= nil then return v end
    for _, c in rawget(self, "kids") do if c.Name == key then return c end end
    return nil
end
Inst.__newindex = function(self, key, value)
    local props = rawget(self, "props")
    if key == "Parent" then
        local old = props.Parent
        if old then local list = rawget(old, "kids") local i = table.find(list, self) if i then table.remove(list, i) end end
        props.Parent = value
        if value then table.insert(rawget(value, "kids"), self) end
        return
    end
    props[key] = value
end
local function new(class, name, parent, props)
    local o = setmetatable({props = {ClassName = class, Name = name or class, Visible = true, Enabled = true, Text = "", ZIndex = 1,
        AbsolutePosition = Vector2.zero, AbsoluteSize = Vector2.zero, Transparency = 0}, kids = {}, attrs = {}, sigs = {}}, Inst)
    for k, v in props or {} do rawget(o, "props")[k] = v end
    if parent then o.Parent = parent end
    return o
end
function methods.IsA(self, cls) return self.ClassName == cls or (hierarchy[cls] and hierarchy[cls][self.ClassName]) == true or cls == "Instance" end
function methods.GetChildren(self) return table.clone(rawget(self, "kids")) end
local function walk(i, out) for _, c in rawget(i, "kids") do table.insert(out, c) walk(c, out) end return out end
function methods.GetDescendants(self) return walk(self, {}) end
function methods.FindFirstChild(self, name, rec)
    if rec then for _, d in walk(self, {}) do if d.Name == name then return d end end return nil end
    for _, c in rawget(self, "kids") do if c.Name == name then return c end end
    return nil
end
methods.WaitForChild = methods.FindFirstChild
function methods.FindFirstChildOfClass(self, cls) for _, c in rawget(self, "kids") do if c.ClassName == cls then return c end end return nil end
function methods.FindFirstChildWhichIsA(self, cls, rec)
    for _, d in (if rec then walk(self, {}) else rawget(self, "kids")) do if d:IsA(cls) then return d end end
    return nil
end
function methods.ClearAllChildren(self) for _, c in table.clone(rawget(self, "kids")) do c.Parent = nil end end
function methods.Destroy(self) self.Parent = nil end
function methods.GetAttribute(self, k) return rawget(self, "attrs")[k] end
function methods.SetAttribute(self, k, v)
    rawget(self, "attrs")[k] = v
    local s = rawget(self, "sigs")["attr:" .. k]
    if s then s:Fire() end
    if SIM and SIM.onAttr then SIM.onAttr(self, k, v) end
end
function methods.GetAttributeChangedSignal(self, k) local s = rawget(self, "sigs") s["attr:" .. k] = s["attr:" .. k] or signal() return s["attr:" .. k] end
function methods.FireServer(self, ...) if self.onFire then self.onFire(...) end end
function methods.InvokeServer(self, ...) return self.onInvoke(...) end
function methods.PivotTo(self, cf) local r = methods.FindFirstChild(self, "HumanoidRootPart") if r then r.Position = cf.Position end end
function methods.MoveTo(self, pos) self.moveTarget = pos end
function methods.GetBoundingBox(self) return CFrame.new(self.Parent and self.Parent.HumanoidRootPart.Position or Vector3.zero), (self.boxSize or Vector3.new(4, 4, 6)) end
function methods.WorldToViewportPoint(self, v)
    if SCENARIO == "clipped" then return Vector3.new(-50, 300, 5), false end
    return Vector3.new(640, 360, 20), true
end
function methods.GetServerTimeNow() return 5000 + now end
function methods.GetGuiInset() return Vector2.new(0, 36), Vector2.zero end

-- ===== services =====
local logHistory = {}
local guid = 0
local inputs = {}
local Services = {}
local function svc(name, t) Services[name] = t return t end
game = {GameId = 0, GetService = function(_, name) return assert(Services[name], "service " .. name) end}
local root = new("Folder", "game")
local RS = svc("ReplicatedStorage", new("Folder", "ReplicatedStorage", root))
local SSS = svc("ServerScriptService", new("Folder", "ServerScriptService", root))
local PlayersSvc = new("Folder", "Players", root)
svc("Players", PlayersSvc)
local player = new("Folder", "Walker", PlayersSvc, {CameraMinZoomDistance = 12, CameraMaxZoomDistance = 110, UserId = 1})
PlayersSvc.LocalPlayer = player
function PlayersSvc.GetPlayers() return {player} end
local heartbeat, renderStepped = signal(), signal()
svc("RunService", {Heartbeat = heartbeat, RenderStepped = renderStepped})
svc("LogService", {GetLogHistory = function() return logHistory end})
svc("GuiService", {GetGuiInset = methods.GetGuiInset})
svc("HttpService", {GenerateGUID = function() guid += 1 return "guid-" .. guid end})
-- JSON (just enough)
local function enc(v)
    local t = type(v)
    if t == "table" then
        if #v > 0 or next(v) == nil then
            local p = {} for _, x in v do table.insert(p, enc(x)) end return "[" .. table.concat(p, ",") .. "]"
        end
        local keys = {} for k in v do table.insert(keys, k) end table.sort(keys)
        local p = {} for _, k in keys do table.insert(p, '"' .. k .. '":' .. enc(v[k])) end return "{" .. table.concat(p, ",") .. "}"
    elseif t == "string" then return '"' .. v .. '"'
    else return tostring(v) end
end
local function dec(s)
    local i = 1
    local function ws() i = string.find(s, "[^%s]", i) or #s + 1 end
    local val
    local function str() local j = string.find(s, '"', i + 1, true) local r = string.sub(s, i + 1, j - 1) i = j + 1 return r end
    function val()
        ws()
        local c = string.sub(s, i, i)
        if c == "{" then
            i += 1 local t = {} ws()
            if string.sub(s, i, i) == "}" then i += 1 return t end
            while true do ws() local k = str() ws() i += 1 t[k] = val() ws() local d = string.sub(s, i, i) i += 1 if d == "}" then return t end end
        elseif c == "[" then
            i += 1 local t = {} ws()
            if string.sub(s, i, i) == "]" then i += 1 return t end
            while true do table.insert(t, val()) ws() local d = string.sub(s, i, i) i += 1 if d == "]" then return t end end
        elseif c == '"' then return str()
        elseif string.sub(s, i, i + 3) == "true" then i += 4 return true
        elseif string.sub(s, i, i + 4) == "false" then i += 5 return false
        elseif string.sub(s, i, i + 3) == "null" then i += 4 return nil
        else local n = string.match(s, "^-?[%d%.eE+-]+", i) i += #n return tonumber(n) end
    end
    return val()
end
svc("HttpService", {GenerateGUID = function() guid += 1 return "guid-" .. guid end, JSONDecode = function(_, s) return dec(s) end, JSONEncode = function(_, v) return enc(v) end})
shared = {BDWalkBudget = 8}

-- ===== the sim =====
SIM = {}
local P = {} -- the server's truth
local priv = {} -- the owner-only values the client mirrors
local PRIVATE = {Crystals = true, CollectionJson = true, ProgressionJson = true, SettingsJson = true, RevealSkipJson = true, ActiveChestCount = true,
    QueuedEggsWaiting = true, NextChestReadyAt = true, NextChestId = true, LastClaimedChestId = true, LastSettledRunId = true, LastRunEggCount = true}
local Remotes = new("Folder", "BeDinoRemotes", RS)
local function remote(name, class) return new(class or "RemoteEvent", name, Remotes) end
for _, n in {"RequestStartRun", "RequestEndRun", "RequestLeap", "EquipSpecies", "ClaimChest", "SetRevealSkip", "SetSettings", "ProgressionAction", "ClaimNest"} do remote(n) end
local ProgressionResult = remote("ProgressionResult")
ProgressionResult.OnClientEvent = signal()
local AdminAction = remote("AdminAction", "RemoteFunction")

-- real pure modules, stubs for the rest
local Shared = new("Folder", "Shared", RS)
local PlayerScripts = new("Folder", "PlayerScripts", player)
local ClientFolder = new("Folder", "Client", PlayerScripts)
local loaded, real, stubs = {}, {}, {}
local function requireModule(inst)
    local name = inst.Name
    if loaded[name] == nil then
        if stubs[name] then loaded[name] = stubs[name]() else loaded[name] = real[name](inst, requireModule) end
    end
    return loaded[name]
end
require = requireModule
for name, fn in MODULES do real[name] = fn new("ModuleScript", name, Shared) end
local caveHub = true
local function colorTable() return {panel = color(0, 0, 0), card = color(.3, .3, .3), outline = color(0, 0, 0), text = color(1, 1, 1), accent = color(0, 1, 0), gold = color(1, 1, 0), blue = color(0, 0, 1), purple = color(1, 0, 1), red = color(1, 0, 0)} end
local ThemeStub = {MotionEnabled = true, Colors = colorTable()}
stubs.UITheme = function() return ThemeStub end
new("ModuleScript", "UITheme", Shared)
local Config, Model, Gate, Spawn, Rules, PC, Ftue, RevealSkip
local menuTab = "sound"
local fusionGui
stubs.CameraFit = function()
    return {box = function(char) local v = char:FindFirstChild("LocalMeshVisual") if not v then return nil, nil end return v.boxSize.Y, v.boxSize.Z end,
        minZoom = function(base, char) local v = char:FindFirstChild("LocalMeshVisual") return base + (if v then v.boxSize.Y else 0) end}
end
stubs.SettingsMenu = function() return {tab = function() return menuTab end} end
stubs.FusionMenu = function()
    return {open = function() fusionGui.Enabled = true end, close = function() fusionGui.Enabled = false end, isOpen = function() return fusionGui.Enabled end}
end
for _, n in {"CameraFit", "SettingsMenu", "FusionMenu"} do new("ModuleScript", n, ClientFolder) end
local Server = new("Folder", "Server", SSS)
local clientPSInst = new("ModuleScript", "PrivateState", ClientFolder)
local serverPSInst = new("ModuleScript", "PrivateState", Server)
local serverPS = {get = function(_, name) if PRIVATE[name] then return priv[name] end return player:GetAttribute(name) end}
local clientPS = {get = function(name) if PRIVATE[name] then return priv[name] end return player:GetAttribute(name) end}
local plainRequire = requireModule
requireModule = function(inst)
    if inst == serverPSInst then return serverPS end
    if inst == clientPSInst then return clientPS end
    return plainRequire(inst)
end
require = requireModule
Config = requireModule(Shared.Config) -- frozen: the verifier flips CaveHub in the source text before loading
Model = requireModule(Shared.SettingsModel)
Gate = requireModule(Shared.CaveGateRules)
Spawn = requireModule(Shared.SpawnGeometry)
Rules = requireModule(Shared.ProgressionRules)
PC = requireModule(Shared.ProgressionConfig)
Ftue = requireModule(Shared.FtueP1)
RevealSkip = requireModule(Shared.RevealSkip)

-- ---- world state
workspace = new("Folder", "Workspace", root, {Gravity = 250, ClockTime = 14})
workspace.GetServerTimeNow = methods.GetServerTimeNow
local camera = new("Camera", "Camera", workspace, {ViewportSize = Vector2.new(1280, 720), CFrame = CFrame.new(Vector3.new(0, 30, 600))})
if SCENARIO == "blind" then camera.ViewportSize = Vector2.new(1, 1) end
workspace.CurrentCamera = camera
workspace:SetAttribute("WeatherId", "clear")
workspace:SetAttribute("FoodSpawnStatus", "Ready")
workspace:SetAttribute("IslandTerrainReady", true)
new("Folder", "BeDinoArena", workspace)
workspace:SetAttribute("Admin_foodMultiplier", 1)
workspace:SetAttribute("FoodCount", 60)
local foodFolder = new("Folder", "Food", workspace)
local foods = {}
for i = 1, 60 do
    local f = new("Part", "berry", foodFolder, {Position = Vector3.new(-40 + (i % 10) * 9, 10, 20 + math.floor(i / 10) * 14)})
    f:SetAttribute("Points", ({1, 1, 4, 1, 15})[i % 5 + 1])
    foods[i] = {part = f, back = 0}
end
local hubSpawn = Spawn.hubPoint(Config)
local level, calm = 1, false
local species = {"compy", "raptor", "trike", "stego", "ankylo"}
local boxes = {compy = Vector3.new(0, 3, 5), raptor = Vector3.new(0, 4, 7), trike = Vector3.new(0, 6, 10), stego = Vector3.new(0, 7, 11), ankylo = Vector3.new(0, 5, 9)}
local eggs, claimed, hatchOpen = 0, 0, false
local pot = {potions = {}, buffs = {}, shop = {window = 0, bought = {}}}
local copiesOf = {compy = 1}
local function pushPriv()
    priv.CollectionJson = enc((function() local t = {} for id, n in copiesOf do t[id] = {base = n} end return t end)())
    priv.ProgressionJson = enc(pot)
    priv.ActiveChestCount = math.min(5, eggs)
    priv.QueuedEggsWaiting = math.max(0, eggs - 5)
    priv.NextChestId = if eggs > 0 then "egg-" .. (claimed + 1) else ""
    priv.NextChestReadyAt = 0
end
priv.Crystals = 1000000
priv.RevealSkipJson = "[]"
priv.SettingsJson = enc({v = 1, calm = false})
priv.LastRunEggCount = 0
priv.LastSettledRunId = ""
for k, v in {ProfileState = "Loading", ProfileMode = "Memory (playtest)", Location = "Sanctuary", IsAdmin = true, AccountLevel = 1, EquippedSpeciesId = "compy",
    LeapReadyAt = 0, MenuOpen = false, LastRunId = "run-0", WorldReady = true} do player:SetAttribute(k, v) end
local char
local function spawnChar()
    if char then char.Parent = nil end
    char = new("Model", "Character", workspace)
    player.Character = char
    local r = new("Part", "HumanoidRootPart", char, {Position = hubSpawn})
    new("Humanoid", "Humanoid", char, {FloorMaterial = "Enum.Material.Plane", Jump = false})
    local v = new("Model", "LocalMeshVisual", char, {boxSize = boxes[player:GetAttribute("EquippedSpeciesId")] or boxes.compy})
    v:SetAttribute("SpeciesId", player:GetAttribute("EquippedSpeciesId"))
    char:SetAttribute("DinoAttached", true)
    char:SetAttribute("RunState", "Sanctuary")
    char:SetAttribute("VisualScale", 1)
    player:SetAttribute("Location", "Sanctuary")
    pushPriv()
end

-- ---- UI
local ui = new("ScreenGui", "BeDinoUI", new("Folder", "PlayerGui", player), {AbsoluteSize = Vector2.new(1280, 684)})
local function box(class, name, parent, x, y, w, h, props)
    local o = new(class, name, parent, props)
    o.AbsolutePosition, o.AbsoluteSize = Vector2.new(x, y), Vector2.new(w, h)
    return o
end
box("TextLabel", "BuildBadge", ui, 515, 36, 250, 24, {Text = "BUILD " .. Config.Build})
local home = box("TextButton", "HomeButton", ui, 518, 606, 244, 60, {Text = "EXPLORE ISLAND"})
local rail = box("Frame", "Rail", ui, 14, 151, 186, 382)
local railButtons = {}
for i, d in {"collection", "eggs", "fusion", "auras", "potions", "settings"} do
    local b = box("TextButton", "Rail" .. d, rail, 21, 158 + (i - 1) * 62, 172, 54, {ZIndex = 2})
    b:SetAttribute("Destination", d)
    railButtons[d] = b
end
local crystals = box("Frame", "Crystals", ui, 1000, 8, 260, 48)
box("TextButton", "OpenShop", crystals, 1000, 8, 260, 48, {ZIndex = 3})
local hud = box("Frame", "Hud", ui, 18, 572, 390, 94)
local plate = box("Frame", "EggsPlate", hud, 18, 586, 210, 64)
local eggsText = box("TextLabel", "EggsText", plate, 92, 586, 130, 64, {Text = "EGGS 0"})
local sizeBar = box("Frame", "SizeBar", ui, 515, 64, 250, 34, {Visible = false})
box("TextLabel", "SizeWord", sizeBar, 527, 64, 60, 34, {Text = "SIZE"})
local timers = box("Frame", "Timers", ui, 974, 364, 286, 220)
local leapBtn = box("TextButton", "LeapButton", timers, 974, 364, 286, 60, {ZIndex = 2})
local leapText = box("TextLabel", "LeapText", leapBtn, 1030, 364, 225, 60, {Text = "LEAP [E] \xE2\x80\xA2 READY"})
local weatherText = box("TextLabel", "WeatherText", timers, 1030, 436, 226, 62, {Text = "Weather in 10:00"})
local buffsText = box("TextLabel", "BuffsText", timers, 974, 510, 286, 68, {Text = ""})
local toasts = box("Frame", "Toasts", ui, 420, 80, 440, 186)
local toastText = box("TextLabel", "Toast", toasts, 430, 84, 400, 30, {Text = "", Visible = false})
local scrim = box("TextButton", "ModalScrim", ui, 0, 0, 1280, 684, {Visible = false, ZIndex = 20})
local feedbackGui = new("ScreenGui", "PlaytestFeedback", player.PlayerGui, {AbsoluteSize = Vector2.new(1280, 684)})
box("TextButton", "Feedback", feedbackGui, 240, 620, 110, 44, {Text = "Tell us!", ZIndex = 5})
if SCENARIO == "overlap" then plate.AbsolutePosition = Vector2.new(30, 590) feedbackGui.Feedback.AbsolutePosition = Vector2.new(60, 600) end
fusionGui = new("ScreenGui", "BeDinoFusionUI", player.PlayerGui, {Enabled = false, AbsoluteSize = Vector2.new(1280, 684)})
local fpanel = box("Frame", "FusionPanel", fusionGui, 216, 30, 1000, 600)
for _, n in {"Browse", "Ingredients", "ResultColumn"} do box("Frame", n, fpanel, 220, 40, 300, 500) end
local fusionX = box("TextButton", "X", fusionGui, 1150, 30, 56, 48, {Text = "X", ZIndex = 5}) -- the real menu has a TextButton "X" (BD-541 run: module close() is a different instance)
fusionX.tap = function() fusionGui.Enabled = false end

local modal
local function mtext(text, x, y, w, h, name, props) local o = box("TextLabel", name or "T", scrim, x, y, w, h, props or {}) o.Text = text o.ZIndex = 30 return o end
local function mbtn(text, x, y, w, h, name, onTap) local o = box("TextButton", name or "B", scrim, x, y, w, h, {Text = text, ZIndex = 30}) o.tap = onTap return o end
local open
local function closeModal() modal = nil scrim.Visible = false player:SetAttribute("MenuOpen", false) end
SIM.onAttr = function(inst, k, v)
    if inst == player and k == "DemoCloseModal" and v == true then player:SetAttribute("DemoCloseModal", nil) task.delay(0.13, closeModal) end
end
local function tokenLine() return "ok" end
local autoSummary = false
function SIM.nextSpecies() return species[((claimed + 1) % #species) + 1] end
local function revealNext(auto)
    -- claim one egg on the server and show it; with Common on AUTO the sim skips Common eggs (species 1) quickly
    claimed += 1 eggs -= 1
    local id = species[(claimed % #species) + 1]
    copiesOf[id] = (copiesOf[id] or 0) + 1
    priv.LastClaimedChestId = "claim-" .. claimed
    pushPriv()
end
local function hatchScreen()
    modal = "hatch"
    scrim.Visible = true scrim:ClearAllChildren()
    mtext("An egg is hatching...", 220, 90, 700, 60)
    local catcher = mbtn("", 0, 0, 1280, 684, "HatchTapCatcher", nil)
    catcher.ZIndex = 46
    local hint = mtext("Tap!", 400, 450, 400, 40, "TapHint", {Visible = false, ZIndex = 47})
    if eggs > 0 then local sk = mbtn("Skip the rest", 1090, 620, 176, 48, "SkipAll", function() end) sk.ZIndex = 47 end
    task.delay(0.8, function() if modal == "hatch" then hint.Visible = true end end)
    catcher.tap = function()
        if not hint.Visible then return end
        if eggs > 0 then revealNext() hint.Visible = false task.delay(0.8, function() if modal == "hatch" then hint.Visible = true end end)
        else open("eggs") end
    end
end
function open(name)
    modal = name
    scrim.Visible = true scrim:ClearAllChildren()
    player:SetAttribute("MenuOpen", true)
    if name == "tutorial" then
        mtext("Welcome to Be Dino!", 220, 90, 700, 60)
        mbtn("LET'S PLAY", 420, 400, 400, 62, "B", function() open("home") end)
    elseif name == "home" then
        mtext("Sanctuary", 220, 90, 700, 60)
        mbtn("EXPLORE ISLAND", 420, 400, 400, 62, "B", function() closeModal() SIM.startRun() end)
    elseif name == "exit" then
        mtext("Go home?", 220, 90, 700, 60)
        mbtn("GO HOME", 500, 420, 244, 68, "B", function() closeModal() Remotes.RequestEndRun.onFire() end)
        mbtn("CANCEL", 756, 420, 244, 68, "B", closeModal)
    elseif name == "results" then
        mtext("Run Complete!", 220, 90, 700, 60)
        mtext("EGGS  " .. string.format("%d", player:GetAttribute("LastRunCatchScore") or 0), 500, 150, 400, 60)
        mtext("+3 Crystals", 500, 220, 400, 60)
        mbtn("BACK TO SANCTUARY", 240, 430, 370, 48, "B", function() open("home") end)
        if eggs > 0 then mbtn("OPEN EGGS", 640, 430, 370, 48, "B", function() SIM.travel("eggs") end) end
    elseif name == "eggs" then
        mtext("Eggs", 220, 90, 700, 60)
        for i = 1, 5 do box("Frame", "NestSlot" .. i, scrim, 230 + (i - 1) * 90, 160, 80, 80, {ZIndex = 30}) end
        if eggs > 0 then mtext("Eggs waiting: " .. eggs, 520, 260, 400, 40, "EggsWaiting") end
        mbtn("OPEN", 520, 330, 300, 80, "OpenEggButton", function()
            if eggs <= 0 then return end
            local skip = dec(priv.RevealSkipJson)
            if table.find(skip, 1) then
                -- Common (compy, raptor) on AUTO: those eggs open without a reveal; the first other egg is shown
                local opened = 0
                while eggs > 0 and (SIM.nextSpecies() == "compy" or SIM.nextSpecies() == "raptor") do revealNext() opened += 1 end
                if opened > 0 and eggs == 0 then open("batchSummary") return end
                if opened == 0 or eggs > 0 then hatchScreen() revealNext() return end
            end
            hatchScreen() revealNext()
        end)
        mbtn("AUTO", 520, 430, 130, 50, "AutoOpenSettingsButton", function() open("settings") end)
    elseif name == "batchSummary" then
        mtext("Auto-opened eggs", 220, 90, 700, 60)
        mbtn("DONE", 520, 430, 300, 60, "B", function() open("eggs") end)
    elseif name == "settings" then
        mtext("Settings", 220, 90, 700, 60)
        for i, id in {"sound", "look", "controls", "help"} do
            mbtn(string.upper(id), 230 + (i - 1) * 209, 150, 197, 48, "Tab_" .. id, function() menuTab = id open("settings") end)
        end
        if menuTab == "sound" then mtext("Hatch sound", 230, 220, 400, 48)
        elseif menuTab == "look" then
            mtext("Calm motion", 230, 220, 400, 48)
            mbtn(if Model.calm() then "ON" else "OFF", 650, 220, 160, 48, "Toggle_Calm motion", function() Model.set("calm", not Model.calm()) open("settings") end)
        elseif menuTab == "controls" then mtext("Camera", 230, 220, 250, 48)
        else
            mbtn("HOW TO PLAY", 230, 220, 400, 76, "B", function() end)
            local chosen = RevealSkip.set(dec(priv.RevealSkipJson))
            for i, n in RevealSkip.Names do
                mbtn(n .. "\n" .. (if chosen[i] then "AUTO" else "SHOW"), 230 + (i - 1) * 170, 380, 158, 76, "B", function()
                    Remotes.SetRevealSkip.onFire(RevealSkip.toggle(priv.RevealSkipJson, i))
                    task.delay(0.1, function() if modal == "settings" then open("settings") end end)
                end)
            end
        end
    elseif name == "potions" then
        mtext("Potion Shop", 220, 90, 700, 60)
        box("ScrollingFrame", "PotionScroll", scrim, 230, 150, 800, 400, {ZIndex = 30})
        mtext("Crystals: " .. priv.Crystals, 230, 120, 600, 30)
    elseif name == "auras" then
        mtext("Crystal Shops", 220, 90, 700, 60)
        local tabs = Ftue.shopTabs(level)
        SIM.shopTab = SIM.shopTab or "auras"
        for i, tab in tabs do
            local b = mbtn(string.upper(tab), 230 + (i - 1) * 165, 150, 155, 40, "B", function() SIM.shopTab = tab open("auras") end)
            b.BackgroundColor3 = if SIM.shopTab == tab then ThemeStub.Colors.blue else ThemeStub.Colors.card
        end
        if SIM.shopTab == "eggs" then mtext("Random Egg", 230, 220, 400, 40) mbtn("BUY EGG", 230, 300, 400, 60, "B", function() end)
        elseif SIM.shopTab == "crystals" then mtext("You have " .. priv.Crystals .. " Crystals", 230, 220, 500, 40)
        elseif SIM.shopTab == "trails" then mtext("Trail cards", 230, 220, 400, 40)
        else mtext("Aura cards", 230, 220, 400, 40) end
    end
end
function SIM.travel(dest) task.delay(1.0, function() if dest == "fusion" then fusionGui.Enabled = true else open(dest) end end) end

-- ---- server side behaviour
local function setEggsText() eggsText.Text = "EGGS " .. string.format("%d", if char then char:GetAttribute("CatchScore") or 0 else 0) end
function SIM.startRun()
    if not char or char:GetAttribute("RunState") ~= "Sanctuary" then return end
    task.delay(0.5, function()
        char:SetAttribute("RunState", "Active") char:SetAttribute("CatchScore", 0) char:SetAttribute("GrowthScore", 0) char.carry = 0
        char.HumanoidRootPart.Position = Vector3.new(0, 10, 30)
        player:SetAttribute("Location", "Island")
        home.Text = "HOME" sizeBar.Visible = true
        eggsText.Text = "EGGS 0"
    end)
end
function SIM.endRun()
    local score = char:GetAttribute("CatchScore") or 0
    char:SetAttribute("RunState", "Ending")
    player:SetAttribute("LastRunEndReason", "ManualExit")
    player:SetAttribute("LastRunCatchScore", score)
    player:SetAttribute("LastRunId", "run-" .. guid .. "-" .. math.floor(now * 10))
    player:SetAttribute("LastRunEndAt", now)
    open("results")
    task.delay(1.5, function()
        eggs += math.min(score, 150)
        priv.LastRunEggCount = math.min(score, 150)
        priv.LastSettledRunId = "settled-" .. math.floor(now * 10)
        spawnChar()
        home.Text = "EXPLORE ISLAND" sizeBar.Visible = false
        task.delay(0.2, function() open("results") end)
    end)
end
Remotes.RequestStartRun.onFire = function() SIM.startRun() end
Remotes.RequestEndRun.onFire = function() if char and char:GetAttribute("RunState") == "Active" then SIM.endRun() end end
Remotes.RequestLeap.onFire = function()
    if not char or char:GetAttribute("RunState") ~= "Active" then return end
    if workspace:GetServerTimeNow() < (player:GetAttribute("LeapReadyAt") or 0) then return end
    player:SetAttribute("LastLeapStatus", "leaping")
    player:SetAttribute("LeapReadyAt", workspace:GetServerTimeNow() + 60)
end
Remotes.EquipSpecies.onFire = function(id)
    if not copiesOf[id] then player:SetAttribute("LastEquipStatus", "not_owned") return end
    player:SetAttribute("EquippedSpeciesId", id) player:SetAttribute("LastEquipStatus", "equipped")
    task.delay(0.5, function()
        local old = char:FindFirstChild("LocalMeshVisual") if old then old.Parent = nil end
        local v = new("Model", "LocalMeshVisual", char, {boxSize = boxes[id]})
        v:SetAttribute("SpeciesId", id)
    end)
end
Remotes.SetRevealSkip.onFire = function(list) priv.RevealSkipJson = enc(list) end
Remotes.SetSettings.onFire = function(store) priv.SettingsJson = enc(store) end
Remotes.ClaimChest.onFire = function() end
Remotes.ProgressionAction.onFire = function(action, id, token, replace)
    task.delay(0.2, function()
        local ok, status = false, "bad"
        if action == "buyPotion" then
            local pid, window = string.match(id, "^([%w_]+)@(%d+)$")
            local item = pid and Rules.item(PC.Potions, pid)
            if item and priv.Crystals >= item.price then
                priv.Crystals -= item.price pot.potions[pid] = (pot.potions[pid] or 0) + 1
                pot.shop = {window = tonumber(window), bought = {[pid] = ((pot.shop.bought or {})[pid] or 0) + 1}}
                ok, status = true, "purchased"
            end
        elseif action == "usePotion" then
            local item = Rules.item(PC.Potions, id)
            if item and (pot.potions[id] or 0) > 0 then
                pot.potions[id] -= 1 pot.buffs[item.kind] = {id = id, expiresAt = workspace:GetServerTimeNow() + item.duration}
                ok, status = true, "activated"
            end
        end
        pushPriv()
        ProgressionResult.OnClientEvent:Fire(token, ok, status)
    end)
end
AdminAction.onInvoke = function(action, a, b)
    if action == "set" then workspace:SetAttribute("Admin_" .. a, b) return true, "x" .. b
    elseif action == "startWeather" then
        workspace:SetAttribute("WeatherId", a) workspace:SetAttribute("WeatherName", "Rain") workspace:SetAttribute("WeatherEndsAt", workspace:GetServerTimeNow() + b)
        task.delay(1, function() if char then char:SetAttribute("WeatherLootMultiplier", 1.1) end end)
        toastText.Text = "Rain started!" toastText.Visible = true
        return true, "started"
    elseif action == "stopWeather" then workspace:SetAttribute("WeatherId", "clear")
workspace:SetAttribute("FoodSpawnStatus", "Ready")
workspace:SetAttribute("IslandTerrainReady", true)
new("Folder", "BeDinoArena", workspace) if char then char:SetAttribute("WeatherLootMultiplier", 1) end return true, "stopped"
    elseif action == "reset" then workspace:SetAttribute("Admin_foodMultiplier", 1) return true, "reset" end
    return false, "bad_action"
end
Model.onChange(function(s)
    ThemeStub.MotionEnabled = not s.calm
    task.delay(0.8, function() Remotes.SetSettings.onFire(Model.toStore(Model.get())) end)
end)

-- ---- client input
local function hit(x, y)
    local best
    for _, d in walk(player.PlayerGui, {}) do
        if d.ClassName == "TextButton" then
            local vis, cur = true, d
            while cur and cur ~= root do
                if cur:IsA("GuiObject") and not cur.Visible then vis = false end
                if cur.ClassName == "ScreenGui" and not cur.Enabled then vis = false end
                cur = cur.Parent
            end
            local p, s = d.AbsolutePosition, d.AbsoluteSize
            if vis and x >= p.X and x <= p.X + s.X and y >= p.Y and y <= p.Y + s.Y and (not best or d.ZIndex >= best.ZIndex) then best = d end
        end
    end
    return best
end
local function requestLeap()
    Remotes.RequestLeap.onFire()
    if char and char:GetAttribute("RunState") == "Active" and workspace:GetServerTimeNow() >= (player:GetAttribute("LeapReadyAt") or 0) - 60 then
        char.leap = {t = 0}
    end
end
local function click(x, y)
    local b = hit(x, y)
    if not b then return end
    if b.tap then b.tap() return end
    if b == home then
        local rs = char and char:GetAttribute("RunState")
        if rs == "Active" then open("exit") elseif rs == "Sanctuary" then SIM.startRun() end
    elseif b == leapBtn then requestLeap()
    elseif b.Name == "OpenShop" then SIM.travel("auras")
    elseif b:GetAttribute("Destination") then SIM.travel(b:GetAttribute("Destination")) end
end
if SCENARIO ~= "novim" then
    svc("VirtualInputManager", {
        SendMouseMoveEvent = function() end,
        SendMouseButtonEvent = function(self, x, y, button, down) if not down then click(x, y - 36) end end,
        SendKeyEvent = function(self, down, code) if down and code == Enum.KeyCode.E then requestLeap() end end,
    })
else
    Services.VirtualInputManager = nil
end
local realGetService = game.GetService
game.GetService = function(self, name)
    if name == "VirtualInputManager" and SCENARIO == "novim" then error("VirtualInputManager is not available here") end
    return realGetService(self, name)
end

-- ---- per-tick world
local welcomed = false
local gateSince
local function tick(dt)
    heartbeat:Fire(dt) renderStepped:Fire(dt)
    if SCENARIO == "blind" then renderStepped.conns = {} end
    if player:GetAttribute("ProfileState") == "Loading" and now > 1.5 then
        player:SetAttribute("ProfileState", "Loaded") spawnChar()
    end
    if not char then return end
    local rs = char:GetAttribute("RunState")
    if rs == "Sanctuary" and player:GetAttribute("ProfileState") == "Loaded" and not welcomed and not modal then welcomed = true open("tutorial") end
    local root = char.HumanoidRootPart
    local hum = char.Humanoid
    if hum.moveTarget then
        local d = hum.moveTarget - root.Position
        local flat = Vector3.new(d.X, 0, d.Z)
        local step = 22 * dt
        if flat.Magnitude <= step then root.Position = Vector3.new(hum.moveTarget.X, root.Position.Y, hum.moveTarget.Z) hum.moveTarget = nil
        else local u = flat.Unit root.Position = root.Position + Vector3.new(u.X * step, 0, u.Z * step) end
    end
    if char.leap then
        char.leap.t += dt
        local t = char.leap.t
        root.Position = Vector3.new(root.Position.X, 10 + math.max(0, 14 * math.sin(math.min(t, 0.7) / 0.7 * math.pi)), root.Position.Z + 20 * dt)
        if t > 0.8 then char.leap = nil root.Position = Vector3.new(root.Position.X, 10, root.Position.Z) end
    end
    if rs == "Sanctuary" then
        local inside = Gate.inZone(root.Position.X, root.Position.Z, root.Position.Y)
        if inside then gateSince = gateSince or now if now - gateSince >= 1.5 then gateSince = nil SIM.startRun() end else gateSince = nil end
    elseif rs == "Active" then
        local mult = workspace:GetAttribute("Admin_foodMultiplier") or 1
        for _, f in foods do
            if f.back > 0 and now >= f.back then f.back = 0 f.part.Transparency = 0 end
            if f.back == 0 then
                local d = f.part.Position - root.Position
                if math.sqrt(d.X * d.X + d.Z * d.Z) < 3.5 then
                    f.back = now + 8 f.part.Transparency = 1
                    local pts = f.part:GetAttribute("Points")
                    char.carry = (char.carry or 0) + pts * mult * Config.FoodCatchRate * (char:GetAttribute("WeatherLootMultiplier") or 1)
                    local whole = math.floor(char.carry) char.carry -= whole
                    char:SetAttribute("CatchScore", (char:GetAttribute("CatchScore") or 0) + whole)
                    char:SetAttribute("GrowthScore", (char:GetAttribute("GrowthScore") or 0) + pts)
                    setEggsText()
                end
            end
        end
    end
    local left = (player:GetAttribute("LeapReadyAt") or 0) - workspace:GetServerTimeNow()
    leapText.Text = if left > 0 then string.format("LEAP 0:%02d", left) else "LEAP [E] \xE2\x80\xA2 READY"
    if workspace:GetAttribute("WeatherId") ~= "clear" then weatherText.Text = string.format("Rain %d:%02d", 1, 20) else weatherText.Text = "Weather in 10:00" end
    local lines = {}
    for kind, b in pot.buffs do if b.expiresAt > workspace:GetServerTimeNow() then table.insert(lines, string.upper(string.sub(kind, 1, 1)) .. string.sub(kind, 2) .. " potion 4:59") end end
    buffsText.Text = table.concat(lines, "\n")
    -- camera follows the dino
    camera.CFrame = CFrame.new(root.Position + Vector3.new(0, 15, 25))
    player.CameraMinZoomDistance = 12 + (char:FindFirstChild("LocalMeshVisual") and char.LocalMeshVisual.boxSize.Y or 0)
    if SCENARIO == "studionoise" and now > 30 and not SIM.errored then
        SIM.errored = true
        for i = 1, 40 do table.insert(logHistory, {message = "Failed to upload TexturePack (" .. i .. "): PublishService AssetUpload failed HTTP 429", messageType = Enum.MessageType.MessageError, timestamp = os.time()}) end
    end
    if SCENARIO == "errors" and now > 30 and not SIM.errored then
        SIM.errored = true table.insert(logHistory, {message = "boom: attempt to index nil", messageType = Enum.MessageType.MessageError, timestamp = os.time()})
    end
end

-- ===== driver =====
local function runFor(seconds)
    local stop = now + seconds
    while true do
        table.sort(queue, function(a, b) if a.t ~= b.t then return a.t < b.t end return a.seq < b.seq end)
        local item = queue[1]
        if not item or item.t > stop then break end
        table.remove(queue, 1)
        now = math.max(now, item.t)
        if coroutine.status(item.co) == "suspended" then resume(item.co) end
    end
    now = stop
end
local function runChunk(name)
    local result
    local co = coroutine.create(function() result = SCRIPTS[name]() end)
    resume(co)
    local guardTime = now + 4000
    while coroutine.status(co) ~= "dead" do
        runFor(0.05) tick(0.05)
        assert(now < guardTime, "script " .. name .. " never finished")
    end
    return result
end
local function runRepeat(name)
    local r
    for _ = 1, 40 do
        r = runChunk(name)
        if not (type(r) == "string" and string.sub(r, 1, 8) == "CONTINUE") then return r end
    end
    error("chunk " .. name .. " kept saying CONTINUE")
end
runFor(0)
print("SIM start scenario " .. SCENARIO)
runChunk("lib")
for _ = 1, 60 do runFor(0.05) tick(0.05) end
runChunk("server")
runRepeat("c1")
runChunk("server")
runRepeat("c2")
runChunk("server")
runRepeat("c3")
runChunk("server")
print("SIM done")
