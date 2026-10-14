-- Offline smoke harness for the BD-065 Fusion Menu client modules (driven by
-- tools/verify_fusion_ui.py). A minimal Roblox mock (Instance tree, signals, task
-- scheduler, services) runs the REAL FusionMenu / DinoDetails / FusionWidgets /
-- FusionSelection code against a fake FusionAction server. Visual-only modules
-- (UITheme, DinosaurPreview, PreviewTraits) are stubbed. This proves control flow,
-- not layout, rendering, touch or Studio behavior. MODULE_SOURCES is injected.

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
local Remotes = folder("BeDinoRemotes", Replicated)
local ClientFolder = folder("Client")
local LocalPlayer = folder("LocalPlayer")
local PlayerGui = folder("PlayerGui", LocalPlayer)
local guid = 0
local Services = {
    Players = {LocalPlayer = LocalPlayer},
    ReplicatedStorage = Replicated,
    UserInputService = {InputBegan = signal(), TouchEnabled = false},
    HttpService = {GenerateGUID = function() guid += 1 return "guid-" .. guid end},
    TweenService = {Create = function(_, target, _, goals)
        return {Play = function() for k, v in goals do target[k] = v end end, Completed = signal()}
    end},
}
game = {GetService = function(_, name) return assert(Services[name], "service " .. name) end}

-- ===== Modules =====
local sources = MODULE_SOURCES
local loaded = {}
local Theme = {MotionEnabled = true, Colors = {panel = color(0, 0, 0), card = color(0, 0, 0), outline = color(0, 0, 0),
    text = color(1, 1, 1), accent = color(0, 1, 0), gold = color(1, 1, 0), blue = color(0, 0, 1), purple = color(1, 0, 1), red = color(1, 0, 0)}}
function Theme.decorate(object)
    Instance.new("UIStroke").Parent = object
    Instance.new("UICorner").Parent = object
end
function Theme.animate(target, _, goals) for k, v in goals do target[k] = v end end
local stubs = {
    UITheme = Theme,
    DinosaurPreview = {add = function(parent, species, stage)
        local v = Instance.new("ViewportFrame")
        v.Name = "DinosaurPreview"
        v:SetAttribute("Species", species)
        v:SetAttribute("Stage", stage)
        v.Parent = parent
        return v
    end},
    PreviewTraits = {add = function(view, traits) view:SetAttribute("Shiny", traits and traits.shiny) end},
}
local function requireModule(inst)
    local name = inst.Name
    if stubs[name] then return stubs[name] end
    if loaded[name] == nil then loaded[name] = sources[name](inst, requireModule) end
    return loaded[name]
end
for _, name in {"Config", "ProgressionConfig", "EggGenetics", "FusionSelection", "UITheme", "DinosaurPreview"} do
    local m = Instance.new("ModuleScript") m.Name = name m.Parent = SharedFolder
end
for _, name in {"FusionWidgets", "DinoDetails", "PreviewTraits", "FusionMenu"} do
    local m = Instance.new("ModuleScript") m.Name = name m.Parent = ClientFolder
end

-- ===== Fake FusionAction server (contract from the BD-065 brief) =====
local fuseTokens = {}
local dropNextFuse = true
local committed = nil
local function dino(i, over)
    local d = {instanceId = "u:1/d:" .. i, speciesId = "compy", stage = "base",
        genes = {patternId = "06_wavy_stripes", primaryColorId = "green", secondaryColorId = "blue", blend = 20, conditionId = "normal"},
        big = false, shiny = false, mutationId = "", originKind = "hatch", locked = false, favorited = false,
        auraCount = 0, trailCount = 0, equippedAuraId = "", equippedTrailId = ""}
    for k, v in over or {} do d[k] = v end
    return d
end
local owned = {}
for i = 1, 60 do table.insert(owned, dino(i)) end
table.insert(owned, dino(61, {shiny = true}))
table.insert(owned, dino(62, {auraCount = 1, equippedAuraId = "meadow"}))
table.insert(owned, dino(63, {speciesId = "raptor"}))
-- Higher-tier donors: fused records carry genes (pattern comes from saved genes.patternId).
for i = 70, 79 do table.insert(owned, dino(i, {stage = "gold", originKind = "fusion"})) end
for i = 80, 82 do table.insert(owned, dino(i, {stage = "emerald", originKind = "fusion"})) end
local legacy = dino(83, {originKind = "legacy_unknown"}) legacy.genes = nil -- legacy copy: DNA never saved
table.insert(owned, legacy)
local function find(id) for _, d in owned do if d.instanceId == id then return d end end return nil end
local function handle(payload)
    if payload.action == "list" then
        -- Real contract: cursor = last instance sequence received (exclusive, number), limit <= 200.
        assert(payload.cursor == nil or type(payload.cursor) == "number", "numeric cursor")
        assert(payload.limit == nil or (payload.limit >= 1 and payload.limit <= 200))
        local page, last = {}, nil
        for _, d in owned do
            local n = tonumber(string.match(d.instanceId, "/d:(%d+)$"))
            if n > (payload.cursor or 0) and #page < 8 then table.insert(page, d) last = n end
        end
        local more = false
        for _, d in owned do if tonumber(string.match(d.instanceId, "/d:(%d+)$")) > (last or 0) then more = true end end
        return {ok = true, dinosaurs = page, nextCursor = if more then last else nil}
    elseif payload.action == "details" then
        if payload.instanceId == "u:1/d:99" then
            return {ok = true, dinosaur = {instanceId = "u:1/d:99", speciesId = "compy", stage = "gold", genes = committed.traits.genes,
                shiny = true, big = false, mutationId = "", origin = {kind = "fusion", recipeVersion = "r1", oddsVersion = "o1", parents = {}},
                lineage = {parentIds = {"u:1/d:1"}, recipeVersion = "r1", oddsVersion = "o1", parentEggs = {}}, cosmetics = {}}}
        end
        local d = find(payload.instanceId)
        if not d then return {ok = false, reason = "donor_missing"} end
        local copy = table.clone(d)
        copy.origin = {kind = "hatch", eggId = "egg-1"}
        copy.originalEgg = {eggId = "egg-1", kind = "alpha_chest", eventId = "rain", genes = d.genes}
        copy.cosmetics = {ownedAuraIds = {}, ownedTrailIds = {}}
        return {ok = true, dinosaur = copy}
    elseif payload.action == "quote" then
        local need = ({gold = 50, emerald = 10, diamond = 3})[payload.targetStage]
        assert(need and #payload.donorIds == need, "quote only requested at exactly the recipe count: " .. tostring(payload.targetStage) .. " " .. #payload.donorIds)
        local manifest, consent, shinyCount = {}, false, 0
        for _, id in payload.donorIds do
            local d = assert(find(id), "quoted missing donor")
            if d.shiny then shinyCount += 1 end
            if d.auraCount > 0 or d.shiny then
                consent = true
                table.insert(manifest, {instanceId = id, auraIds = if d.auraCount > 0 then {"meadow"} else {}, trailIds = {}, shiny = d.shiny})
            end
        end
        return {ok = true, quote = {speciesId = "compy", patternId = "06_wavy_stripes", targetStage = payload.targetStage, donorIds = table.clone(payload.donorIds),
            lossManifest = manifest, consentRequired = consent, consentDigest = "cd", quoteDigest = "qd-" .. table.concat(payload.donorIds, ","),
            recipeVersion = "r1", oddsVersion = "o1",
            odds = {shiny = .05 * shinyCount, big = 0, mutation = {}, noMutation = 1, condition = {normal = .7, rainbow = .3},
                primaryColor = {green = .6, blue = .4}, secondaryColor = {blue = 1}}}}
    elseif payload.action == "fuse" then
        table.insert(fuseTokens, payload.token)
        if dropNextFuse then dropNextFuse = false return nil end -- lost response
        if committed then return {ok = true, status = "duplicate", result = committed} end
        local needsConsent = false
        for _, id in payload.donorIds do
            local d = find(id)
            if d and (d.shiny or d.auraCount > 0) then needsConsent = true end
        end
        assert(payload.consentDigest == (if needsConsent then "cd" else nil), "consent digest echoed only when required")
        committed = {resultId = "u:1/d:99", targetStage = "gold", speciesId = "compy", patternId = "06_wavy_stripes", oddsVersion = "o1",
            traits = {big = false, shiny = true, mutationId = "", genes = {patternId = "06_wavy_stripes", primaryColorId = "blue",
                secondaryColorId = "blue", blend = 100, conditionId = "rainbow"}}}
        local consumed = {}
        for _, id in payload.donorIds do consumed[id] = true end
        local kept = {}
        for _, d in owned do if not consumed[d.instanceId] then table.insert(kept, d) end end
        owned = kept
        return {ok = true, status = "fused", result = committed}
    end
    return {ok = false, reason = "unknown"}
end
local fusionRemote = Instance.new("RemoteFunction")
fusionRemote.Name = "FusionAction"
fusionRemote.InvokeServer = function(_, payload) return handle(payload) end

-- ===== Helpers =====
local function byText(root, needle)
    for _, i in root:GetDescendants() do
        if i.ClassName == "TextButton" and string.find(i.Text, needle, 1, true) then return i end
    end
    return nil
end
local function byName(root, name)
    for _, i in root:GetDescendants() do if i.Name == name then return i end end
    return nil
end
local function texts(root)
    local r = {}
    for _, i in root:GetDescendants() do if i.ClassName == "TextLabel" or i.ClassName == "TextButton" then table.insert(r, i.Text) end end
    return table.concat(r, "\n")
end
local function has(root, needle) return string.find(texts(root), needle, 1, true) ~= nil end
local function press(button) assert(button, "missing button") button.Activated:Fire() end
local function cards(screen)
    local list = {}
    for _, c in byName(screen, "DinoGrid"):GetChildren() do if string.sub(c.Name, 1, 5) == "Dino_" then table.insert(list, c) end end
    return list
end

-- ===== Scenario =====
local Menu = requireModule(ClientFolder.FusionMenu)
-- 1) Remote missing: graceful "Fusion unavailable", no error.
assert(Menu.available() == false)
Menu.open() runFor(1)
local screen = PlayerGui.BeDinoFusionUI
assert(screen.Enabled and has(screen, "Fusion unavailable"), "unavailable screen")
press(byName(screen, "Close"))
assert(not screen.Enabled)

-- 2) Remote present: paged list -> individual cards.
fusionRemote.Parent = Remotes
assert(Menu.available())
Menu.open() runFor(8)
assert(#cards(screen) == 77, "paged list: " .. #cards(screen))
assert(has(screen, "Egg pattern unknown"), "legacy copy with nil genes explained")
-- All three tiers ACTIVE: Emerald = 10 Gold, Diamond = 3 Emerald (quotes only at exactly N).
press(byName(screen, "Stage_emerald")) runFor(1)
assert(not has(screen, "EMERALD LOCKED") and has(screen, "10 Gold -> 1 NEW Emerald"), "emerald active")
press(byText(screen, "AUTO-FILL PLAIN")) runFor(.1)
assert(has(screen, "INGREDIENTS 10/10"), "emerald auto-fills 10 plain Golds")
assert(byName(screen, "Slots") and #byName(screen, "Slots"):GetChildren() > 0 and byName(screen, "Counter") == nil, "10 slots, no counter")
runFor(1)
assert(byName(screen, "Fuse").Text == "REVIEW & FUSE", "emerald quote at 10")
press(byName(screen, "Stage_diamond")) runFor(1)
assert(not has(screen, "DIAMOND LOCKED") and has(screen, "3 Emerald -> 1 NEW Diamond"), "diamond active")
press(byText(screen, "AUTO-FILL PLAIN")) runFor(.1)
assert(has(screen, "INGREDIENTS 3/3"), "diamond auto-fills 3 plain Emeralds")
runFor(1)
assert(byName(screen, "Fuse").Text == "REVIEW & FUSE", "diamond quote at 3")
press(byName(screen, "Stage_gold")) runFor(1)
-- Auto-fill: 50 plain copies (compact counter), debounced quote, exact odds.
press(byText(screen, "AUTO-FILL PLAIN")) runFor(.1)
assert(has(screen, "INGREDIENTS 50/50"))
assert(byName(screen, "Counter") and has(screen, "50/50 selected"), "compact n/N counter for 50 donors")
assert(has(screen, "Calculating exact odds"), "debounce pending")
runFor(1)
assert(byName(screen, "Fuse").Text == "REVIEW & FUSE", "quote ready")
assert(has(screen, "Shiny: Shiny 0% • Not Shiny 100%") and has(screen, "Condition: Normal 70% • Rainbow 30%"), "exact odds shown")
assert(has(screen, "Different species"), "raptor card explains ineligibility")
-- Swap two plain donors for the aura and Shiny dinos: tap selected cards to remove them.
local removed = 0
for _, c in cards(screen) do
    if removed < 2 and has(c, "SELECTED") and not has(c, "VALUABLE") then press(c) removed += 1 end
end
runFor(.1)
assert(has(screen, "INGREDIENTS 48/50") and has(screen, "48/50 selected"), "counter follows removal")
assert(not byName(screen, "Fuse") or byName(screen, "Fuse").Text ~= "REVIEW & FUSE", "no quote below 50")
local auraCard, shinyCard
for _, c in cards(screen) do
    if has(c, "1 FX") then auraCard = c end
    if has(c, "SHINY") then shinyCard = c end
end
press(auraCard) press(shinyCard) runFor(1)
assert(has(screen, "SELECTED (VALUABLE)"), "valuable donors highlighted")
assert(has(screen, "Shiny: Shiny 5% • Not Shiny 95%"), "fresh quote after selection change")
-- Confirmation: itemized loss + explicit acknowledgement before FUSE NOW exists.
press(byName(screen, "Fuse")) runFor(.1)
assert(has(screen, "ALL 50 DINOS BELOW ARE CONSUMED") and has(screen, "1 aura and 0 trails will be lost: Meadow Glow"), "itemized loss")
assert(has(screen, "Valuable donors consumed: Compy (Shiny)"))
assert(byName(screen, "FuseNow") == nil, "acknowledgement required first")
press(byName(screen, "Acknowledge")) runFor(.1)
press(byName(screen, "FuseNow"))
runFor(10)
assert(#fuseTokens == 2 and fuseTokens[1] == fuseTokens[2], "lost response retried with the SAME token")
-- Reveal: pattern locked card first, then skip to the committed final card.
assert(has(screen, "PATTERN LOCKED: WAVY STRIPES") or has(screen, "COLOR 1") or has(screen, "CONDITION"), "reveal running")
press(byName(screen, "Skip")) runFor(.1)
assert(has(screen, "NEW WAVY STRIPES COMPY") and has(screen, "Crafted Gold (earned)") and has(screen, "Condition: Rainbow"), "final card")
local preview = byName(screen, "DinosaurPreview")
assert(preview:GetAttribute("Stage") == "gold" and preview:GetAttribute("Shiny") == true, "gold preview with committed traits")
-- BD-062 details of the new Gold.
press(byName(screen, "ResultDetails")) runFor(1)
assert(has(screen, "Gold Wavy Stripes Compy") and has(screen, "PRESTIGE: Crafted Gold (earned)") and has(screen, "Fused from 1 dinos"), "fused details")
press(byText(screen, "BACK")) runFor(2)
assert(#cards(screen) == 27, "donors consumed and list refreshed: " .. #cards(screen))
-- Hatched dino details from a card info button.
press(byName(cards(screen)[1], "Details")) runFor(1)
assert(has(screen, "ORIGINAL EGG") and has(screen, "Event: Rain") and has(screen, "Run reward egg"), "hatched details")
press(byText(screen, "BACK")) runFor(1)
Menu.close()
assert(not screen.Enabled)

-- 3) Lost response while the menu is closed -> re-open offers CHECK RESULT (same token)
-- and the duplicate result is shown without replaying the odds wheels.
committed = nil
dropNextFuse = false
for i = 100, 149 do table.insert(owned, dino(i)) end
Menu.open() runFor(8)
press(byText(screen, "AUTO-FILL PLAIN")) runFor(1)
press(byName(screen, "Fuse")) runFor(.1)
local before = #fuseTokens
dropNextFuse = true
press(byName(screen, "FuseNow"))
Menu.close() -- player closes while the first request is lost
runFor(.5)
-- Simulate all automatic retries failing by keeping the server unreachable.
local realHandle = fusionRemote.InvokeServer
fusionRemote.InvokeServer = function() return nil end
runFor(20)
fusionRemote.InvokeServer = realHandle
Menu.open() runFor(.5)
assert(byName(screen, "CheckResult"), "resume offered for unanswered confirmed attempt")
press(byName(screen, "CheckResult")) runFor(3)
local token = fuseTokens[before + 1]
for i = before + 1, #fuseTokens do assert(fuseTokens[i] == token, "resume reused the same token") end
press(byName(screen, "Skip")) runFor(.1)
assert(has(screen, "NEW WAVY STRIPES COMPY"), "result shown after resume")
Menu.close()

-- 4) Phone landscape safe area (740x340): compact read-only slot strip and a 44 px
-- touch-target audit of every button the browse/confirm screens create.
screen.AbsoluteSize = vec(740, 340)
for i = 200, 249 do table.insert(owned, dino(i)) end
Menu.open() runFor(8)
press(byText(screen, "AUTO-FILL PLAIN")) runFor(1)
for _, s in byName(screen, "Slots"):GetChildren() do assert(s.ClassName ~= "TextButton", "50-donor counter has no tiny slot buttons") end
assert(byName(screen, "Counter") and byName(screen, "Slots"):FindFirstChildOfClass("UIGridLayout").CellSize.Y.Scale == 1, "counter fills the compact strip")
local function audit()
    local checked = 0
    for _, b in screen:GetDescendants() do
        if b.ClassName == "TextButton" and b.Name ~= "FusionScrim" then
            local layout = b.Parent and b.Parent:FindFirstChildOfClass("UIGridLayout")
            local size = if layout then layout.CellSize else b.Size
            if size.Y.Scale == 0 then assert(size.Y.Offset >= 44, "touch height " .. b.Name .. " " .. size.Y.Offset) end
            if size.X.Scale == 0 then assert(size.X.Offset >= 44, "touch width " .. b.Name .. " " .. size.X.Offset) end
            checked += 1
        end
    end
    return checked
end
local audited = audit()
press(byName(screen, "Fuse")) runFor(.1)
audited += audit()
Menu.close()

print("Fusion UI smoke passed: " .. audited .. " buttons >= 44 px in phone layout, unavailable fallback, paged list, 50/10/3 stage tabs, 50-donor counter, plain auto-fill, debounced exact odds, valuable highlight, itemized consent, same-token retry and resume, skippable reveal, fused/hatched details (" .. created .. " mock instances)")
