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
    Sfx = {play = function() return false end},
    DinosaurPreview = {add = function(parent, species, stage)
        local v = Instance.new("ViewportFrame")
        v.Name = "DinosaurPreview"
        v:SetAttribute("Species", species)
        v:SetAttribute("Stage", stage)
        v.Parent = parent
        return v
    end},
    OddsCopy = {fusionCalm = "Odds are shown before you fuse", fusionDetails = "Fusion uses no real money in this version. The chances above are exact and are shown before you fuse."},
    PreviewTraits = {add = function(view, traits) view:SetAttribute("Shiny", traits and traits.shiny) end},
}
local function requireModule(inst)
    local name = inst.Name
    if stubs[name] then return stubs[name] end
    if loaded[name] == nil then loaded[name] = sources[name](inst, requireModule) end
    return loaded[name]
end
for _, name in {"Config", "ProgressionConfig", "RarityCurve", "ColourBonus", "EggGenetics", "FusionSelection", "UITheme", "DinosaurPreview", "Sfx", "OddsCopy"} do
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
        genes = {patternId = "06_wavy_stripes", primaryColorId = "green", secondaryColorId = "blue", blend = 20},
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
        local need = ({gold = 6, emerald = 3, diamond = 2})[payload.targetStage]
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
            odds = {shiny = .05 * shinyCount, big = 0, mutation = {}, noMutation = 1,
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
                secondaryColorId = "blue", blend = 100}}}
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

-- 2) Remote present: paged list -> big cards, auto-filtered to the tier's source stage
-- (Gold shows only the 64 Base copies; the 10 Gold and 3 Emerald are hidden, not explained).
fusionRemote.Parent = Remotes
assert(Menu.available())
Menu.open() runFor(8)
assert(#cards(screen) == 64, "paged list filtered to Base: " .. #cards(screen))
assert(has(screen, "No pattern: can't fuse") and not has(screen, "Unknown pattern"), "legacy copy with nil genes explained in plain words")
assert(not has(screen, "Not the right stage"), "wrong-stage copies are hidden, never listed")
assert(has(screen, "Tap 6 Compy, or Fill for me."), "goal sentence: " .. byName(screen, "Goal").Text)
assert(byName(screen, "Filters") == nil, "filter chips collapsed behind the Filter button")
assert(byName(screen, "Result") and has(screen, "Guaranteed: Gold!") and has(screen, "Pick 6 more to see your chances."), "result preview + simple empty state")
for _, word in {"ROLLED", "UPGRADED", "exact odds from the server", "INGREDIENTS"} do assert(not has(screen, word), "jargon gone: " .. word) end
-- Filter button reveals chips (Sort + 8 chips + Clear); pressing again hides them.
press(byName(screen, "Filter")) runFor(.1)
assert(byName(screen, "Filters") and byText(screen, "Sort:") and byText(screen, "Dino: All"), "chips shown")
press(byName(screen, "Filter")) runFor(.1)
assert(byName(screen, "Filters") == nil, "chips hidden")
-- All three tiers ACTIVE: Emerald = 3 Gold, Diamond = 2 Emerald (quotes only at exactly N).
press(byName(screen, "Stage_emerald")) runFor(1)
assert(#cards(screen) == 10 and has(screen, "Make an Emerald dino") and has(screen, "Put in 3 Gold"), "emerald lists the 10 Golds")
press(byName(screen, "AutoFill")) runFor(.1)
assert(byName(screen, "SlotCount").Text == "3 of 3", "emerald auto-fills 3 plain Golds")
assert(byName(screen, "Slot_3") and byName(screen, "Empty_1") == nil and byName(screen, "Slot_4") == nil, "3 slots")
runFor(1)
assert(byName(screen, "Fuse").Text == "FUSE!", "emerald quote at 3")
press(byName(screen, "Stage_diamond")) runFor(1)
assert(#cards(screen) == 3 and has(screen, "Put in 2 Emerald"), "diamond lists the 3 Emeralds")
press(byName(screen, "AutoFill")) runFor(.1)
assert(byName(screen, "SlotCount").Text == "2 of 2" and byName(screen, "Slot_2") and byName(screen, "Slot_3") == nil, "diamond auto-fills 2 plain Emeralds")
runFor(1)
assert(byName(screen, "Fuse").Text == "FUSE!", "diamond quote at 2")
press(byName(screen, "Stage_gold")) runFor(1)
assert(byName(screen, "Empty_6") and byName(screen, "Fuse").Text == "Pick 6 more", "6 empty numbered slots")
-- Fill for me: 6 plain copies in slots, debounced quote, exact odds as chips.
press(byName(screen, "AutoFill")) runFor(.1)
assert(byName(screen, "SlotCount").Text == "6 of 6" and byName(screen, "Slot_6"), "6 slots filled")
assert(has(screen, "Working out your chances..."), "debounce pending")
assert(has(screen, "Ready! Tap FUSE."), "goal sentence when full")
runFor(1)
assert(byName(screen, "Fuse").Text == "FUSE!", "quote ready")
assert(has(screen, "Yes 0%") and has(screen, "No 100%") and has(screen, "Green 60%") and has(screen, "Blue 40%") and not has(screen, "Condition"), "exact odds as chips, no condition")
assert(has(screen, "Different dino"), "raptor card explains ineligibility in plain words")
-- Tap a filled slot to take that dino out; tap a selected card to take another out.
press(byName(screen, "Slot_1")) runFor(.1)
assert(byName(screen, "SlotCount").Text == "5 of 6" and has(screen, "Tap 1 more Compy."), "slot tap removes")
local removed = 0
for _, c in cards(screen) do
    if removed < 1 and has(c, "In slot") and not has(c, "Special") then press(c) removed += 1 end
end
runFor(.1)
assert(byName(screen, "SlotCount").Text == "4 of 6", "slots follow removal")
assert(byName(screen, "Fuse").Text == "Pick 2 more", "no quote below 6")
local auraCard, shinyCard
for _, c in cards(screen) do
    if has(c, "Effects") then auraCard = c end
    if has(c, "Shiny") then shinyCard = c end
end
press(auraCard) press(shinyCard) runFor(1)
assert(has(screen, "(Special)"), "special donors highlighted")
assert(has(screen, "Yes 5%") and has(screen, "No 95%"), "fresh quote after selection change")
-- BD-344 / BD-347: every chip group has a heading, the calm odds line sits by FUSE, the toast rides the top.
for _, heading in {"Colour 1", "Colour 2", "Pattern", "Shiny", "Event", "BIG"} do assert(has(screen, heading), "odds heading " .. heading) end
assert(byName(screen, "OddsNote") and byName(screen, "OddsNote").Text == "Odds are shown before you fuse", "calm line beside FUSE")
assert(byName(screen, "FusionToast").Position.Y.Scale == 0, "toast rides the top")
-- Confirmation: itemized loss + explicit acknowledgement before FUSE exists.
press(byName(screen, "Fuse")) runFor(.1)
assert(has(screen, "All 6 dinos go away. You get 1 new Gold Compy.") and has(screen, "1 aura and 0 trails will be lost: Meadow Glow"), "itemized loss")
assert(has(screen, "Special dinos going away: Compy (Shiny)"))
assert(has(screen, "Yes 5%") and byName(screen, "Result"), "confirm repeats the chances and the result preview")
assert(has(screen, "Fusion uses no real money in this version") and has(screen, "Colour 1"), "BD-347 details line + headings on confirm")
assert(byName(screen, "FuseNow") == nil, "acknowledgement required first")
press(byName(screen, "Acknowledge")) runFor(.1)
press(byName(screen, "FuseNow"))
runFor(6)
assert(#fuseTokens == 2 and fuseTokens[1] == fuseTokens[2], "lost response retried with the SAME token")
-- Reveal: pattern card first, then skip to the committed final card.
assert(has(screen, "Pattern: Wavy Stripes") or has(screen, "Colour 1"), "reveal running")
press(byName(screen, "Skip")) runFor(.1)
assert(has(screen, "NEW WAVY STRIPES COMPY!") and has(screen, "Gold stage: guaranteed") and has(screen, "Shiny!") and not has(screen, "Condition"), "final card shows no condition")
local preview = byName(screen, "DinosaurPreview")
assert(preview:GetAttribute("Stage") == "gold" and preview:GetAttribute("Shiny") == true, "gold preview with committed traits")
-- BD-062 details of the new Gold.
press(byName(screen, "ResultDetails")) runFor(1)
assert(has(screen, "Gold Wavy Stripes Compy") and has(screen, "PRESTIGE: Crafted Gold (earned)") and has(screen, "Fused from 1 dinos"), "fused details")
press(byText(screen, "BACK")) runFor(2)
assert(#cards(screen) == 58, "donors consumed and list refreshed: " .. #cards(screen))
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
press(byName(screen, "AutoFill")) runFor(1)
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

-- 4) Phone landscape safe area (740x340): same three columns, smaller cards, and a 44 px
-- touch-target audit of every button the browse (chips open) / confirm screens create.
screen.AbsoluteSize = vec(740, 340)
for i = 200, 249 do table.insert(owned, dino(i)) end
Menu.open() runFor(8)
press(byName(screen, "Filter")) runFor(.1)
press(byName(screen, "AutoFill")) runFor(1)
local slotButtons = 0
for _, s in byName(screen, "Slots"):GetChildren() do if s.ClassName == "TextButton" then slotButtons += 1 end end
assert(slotButtons == 6, "6 tappable slots on the phone too: " .. slotButtons)
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

print("Fusion UI smoke passed: " .. audited .. " buttons >= 44 px in phone layout, unavailable fallback, paged list auto-filtered per tier, 6/3/2 tier tabs, tappable slots, Fill for me, collapsed filters, debounced odds chips, special highlight, itemized consent, same-token retry and resume, skippable reveal, fused/hatched details (" .. created .. " mock instances)")
