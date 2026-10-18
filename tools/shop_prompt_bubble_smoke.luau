-- BD-1017: client smoke for src/client/HubPromptBubble.luau, run by tools/verify_shop_prompt_bubble.py.
-- A tiny mock Roblox (Instances with Parent and signals, services, time, Enum) is just enough to RUN the real client module with the real pure rules.
-- The verifier puts the module sources in front (HubPromptBubbleRules, HubWalkUpRules as locals) and replaces the placeholder line below with the client module.
-- Not Studio: nobody saw a pixel. It proves the wiring: what is built, when it shows and hides, what a key and a tap do.
local now = 0
local os = {clock = function() return now end}
local methods = {}
local function newSignal()
    local s = {fns = {}}
    function s.Connect(self, fn) table.insert(self.fns, fn) return {Disconnect = function() end} end
    function s.Once(self, fn) table.insert(self.fns, function(...) self.fns = {} fn(...) end) end
    function s.Fire(self, ...) for _, fn in table.clone(self.fns) do fn(...) end end
    return s
end
local function newInstance(class)
    local o = {ClassName = class, Children = {}, attrs = {}}
    setmetatable(o, {
        __index = function(t, k)
            if k == "Activated" or k == "PromptHidden" or k == "Triggered" then local s = newSignal() rawset(t, k, s) return s end
            return methods[k]
        end,
        __newindex = function(t, k, v)
            if k == "Parent" then
                local old = rawget(t, "Parent")
                if old then local i = table.find(old.Children, t) if i then table.remove(old.Children, i) end end
                rawset(t, "Parent", v)
                if v then table.insert(v.Children, t) end
            else rawset(t, k, v) end
        end,
    })
    return o
end
function methods.Destroy(self) -- a real Destroy: leave the parent; the Parent key must be removed so that a later assignment goes through __newindex again
    local old = rawget(self, "Parent")
    if old then local i = table.find(old.Children, self) if i then table.remove(old.Children, i) end end
    rawset(self, "Parent", nil)
end
function methods.GetAttribute(self, n) return self.attrs[n] end
function methods.SetAttribute(self, n, v) self.attrs[n] = v end
function methods.IsA(self, c) return c == self.ClassName or (c == "BasePart" and self.ClassName == "Part") end
function methods.FindFirstChild(self, n) for _, c in self.Children do if c.Name == n then return c end end return nil end
function methods.WaitForChild(self, n) return methods.FindFirstChild(self, n) end
function methods.InputHoldBegin(self) self.began = (self.began or 0) + 1 end
function methods.InputHoldEnd(self) self.ended = (self.ended or 0) + 1 end
local Instance = {new = newInstance}
local enumItems = {}
local Enum = setmetatable({}, {__index = function(_, enumName)
    return setmetatable({}, {__index = function(_, name) -- one table per item, so == works like the real Enum
        local key = enumName .. "." .. name
        if not enumItems[key] then enumItems[key] = {EnumType = enumName, Name = name} end
        return enumItems[key]
    end})
end})
local V3mt = {}
V3mt.__sub = function(a, b)
    local dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
    return setmetatable({x = dx, y = dy, z = dz, Magnitude = math.sqrt(dx * dx + dy * dy + dz * dz)}, V3mt)
end
local Vector3 = {new = function(x, y, z) return setmetatable({x = x, y = y, z = z, Magnitude = math.sqrt(x * x + y * y + z * z)}, V3mt) end}
local UDim2 = {fromOffset = function(x, y) return {xo = x, yo = y} end, fromScale = function(x, y) return {xs = x, ys = y} end, new = function(a, b, c, d) return {a, b, c, d} end}
local UDim = {new = function(a, b) return {a, b} end}

local pending, waiters = {}, {}
local task = {
    spawn = function(fn) local co = coroutine.create(fn) coroutine.resume(co) if coroutine.status(co) == "suspended" then table.insert(waiters, co) end end,
    wait = function() coroutine.yield() end,
    delay = function(sec, fn) table.insert(pending, {at = now + sec, fn = fn}) end,
}
local function advance(seconds)
    for _ = 1, math.floor(seconds / 0.1 + 0.5) do
        now += 0.1
        for i = #pending, 1, -1 do if pending[i].at <= now + 1e-9 then local d = table.remove(pending, i) d.fn() end end
        for _, co in table.clone(waiters) do
            if coroutine.status(co) == "suspended" then coroutine.resume(co) end
            if coroutine.status(co) == "dead" then table.remove(waiters, table.find(waiters, co)) end
        end
    end
end

local player = newInstance("Player")
local playerGui = newInstance("PlayerGui") playerGui.Name = "PlayerGui" playerGui.Parent = player
player.Character = newInstance("Model")
local root = newInstance("Part") root.Name = "HumanoidRootPart" root.Position = Vector3.new(0, 0, 0) root.Parent = player.Character
local uis = {TouchEnabled = false, KeyboardEnabled = true, last = "Keyboard"}
function uis.GetLastInputType(self) return {Name = self.last} end
function uis.GetStringForKeyCode(self, kc) return kc.Name end
local cas = {bound = {}}
function cas.BindAction(self, name, fn, touch, ...) self.bound[name] = fn end
function cas.UnbindAction(self, name) self.bound[name] = nil end
local pps = {PromptShown = newSignal()}
local mods = {}
local services = {
    Players = {LocalPlayer = player}, UserInputService = uis, ContextActionService = cas, ProximityPromptService = pps,
    ReplicatedStorage = {WaitForChild = function(self, n) return {WaitForChild = function(_, m) return mods[m] end} end},
}
local game = {GetService = function(self, n) return services[n] end}
local workspace = {CurrentCamera = {ViewportSize = {Y = 900}}}
local sfxPlays = 0
local Theme = {MotionEnabled = true, Colors = setmetatable({}, {__index = function() return {} end}),
    animate = function(target, seconds, goals) for k, v in goals do target[k] = v end end}
local Chip = {apply = function(frame) end}
local Sfx = {play = function(name) sfxPlays += 1 return true end}
mods.HubPromptBubbleRules, mods.HubWalkUpRules, mods.UITheme, mods.ChipStyle, mods.Sfx = HubPromptBubbleRules, HubWalkUpRules, Theme, Chip, Sfx
local require = function(x) return x end
local script = {}

local Bubble = (function()
CLIENT_SOURCE
end)()

local function newPrompt(id, x)
    local anchor = newInstance("Part") anchor.Name = "Prompt_" .. id anchor.Position = Vector3.new(x, 0, 0)
    local prompt = newInstance("ProximityPrompt")
    prompt.Parent = anchor
    prompt.MaxActivationDistance = 10
    prompt.KeyboardKeyCode, prompt.GamepadKeyCode = Enum.KeyCode.E, Enum.KeyCode.ButtonX
    prompt:SetAttribute("BubbleStation", id)
    return prompt
end
local function boards()
    local out = {}
    for _, c in playerGui.Children do if c.Name == "HubPromptBubble" then out[#out + 1] = c end end
    return out
end
local function node(board, ...)
    local n = board
    for _, name in {...} do n = n:FindFirstChild(name) assert(n, "missing " .. name) end
    return n
end

local ctx = {open = false, show = true}
ctx.canShow = function() return ctx.show end
ctx.windowOpen = function() return ctx.open end
Bubble.attach(ctx)
local nests, potions = newPrompt("nests", 4), newPrompt("potions", 8)

assert(#boards() == 0 and next(cas.bound) == nil, "nothing before the engine shows a prompt")
pps.PromptShown:Fire(nests)
local b = boards()
assert(#b == 1, "one bubble")
assert(b[1].Adornee == nests.Parent and b[1].AlwaysOnTop == true and b[1].ResetOnSpawn == false)
assert(node(b[1], "Fade", "Bubble", "Title").Text == "Nests" and node(b[1], "Fade", "Bubble", "Line").Text == "Come and see your eggs!")
assert(node(b[1], "Fade", "Bubble", "Action", "Key", "Letter").Text == "E" and node(b[1], "Fade", "Bubble", "Action", "Words").Text == "Open", "keyboard: the E key and Open")
assert(node(b[1], "Fade").GroupTransparency == 0, "faded in")
assert(b[1].Size.xo == 248 and b[1].Size.yo == 116)
assert(cas.bound.HubPromptBubbleKey ~= nil, "the key is bound while a prompt is shown")
assert((nests.began or 0) == 0, "walking near presses nothing")

pps.PromptShown:Fire(potions)
b = boards()
assert(#b == 1 and b[1].Adornee == nests.Parent, "one bubble at a time: the nearest (nests at 4, potions at 8)")
root.Position = Vector3.new(9, 0, 0)
advance(0.3)
b = boards()
assert(#b == 1 and b[1].Adornee == potions.Parent and node(b[1], "Fade", "Bubble", "Title").Text == "Potions", "walked toward potions: the bubble moved")
root.Position = Vector3.new(0, 0, 0)
advance(0.3)
b = boards()
assert(#b == 1 and b[1].Adornee == nests.Parent)

local before = sfxPlays
assert(cas.bound.HubPromptBubbleKey("x", Enum.UserInputState.Begin, {}) == Enum.ContextActionResult.Sink, "the key press is sunk (Leap never sees it)")
assert(nests.began == 1 and nests.ended == 1 and (potions.began or 0) == 0, "the nearest prompt was pressed once")
assert(sfxPlays == before + 1, "one soft click")
assert(cas.bound.HubPromptBubbleKey("x", Enum.UserInputState.End, {}) == Enum.ContextActionResult.Sink and nests.began == 1, "key release presses nothing")
advance(0.2)
assert(#boards() == 0, "hidden right after a press")
advance(0.5)
assert(#boards() == 1, "a press that opened nothing: the bubble comes back")

ctx.open = true
advance(0.3)
assert(#boards() == 0, "hidden while a window is open")
cas.bound.HubPromptBubbleKey("x", Enum.UserInputState.Begin, {})
assert(nests.began == 2, "the key still reaches the prompt while a window is open (it closes the window)")
advance(0.3)
ctx.open = false
advance(0.2)
assert(#boards() == 0, "just closed: still hidden")
advance(0.6)
assert(#boards() == 1, "the bubble returns after the window closed")

ctx.show = false
advance(0.3)
assert(#boards() == 0, "the stall cannot open now: no dead button")
ctx.show = true
advance(0.3)
assert(#boards() == 1)

uis.last = "Touch"
advance(0.3)
b = boards()
assert(#b == 1 and node(b[1], "Fade", "Bubble", "Action", "Words").Text == "Tap to open", "phone words")
assert(node(b[1], "Fade", "Bubble", "Action"):FindFirstChild("Key") == nil, "phone: no key chip")
local tapBefore = nests.began
node(b[1], "Fade", "Bubble").Activated:Fire()
assert(nests.began == tapBefore + 1, "a tap on the bubble presses the prompt once")
advance(1)
uis.last = "Gamepad1"
advance(0.3)
b = boards()
assert(#b == 1 and node(b[1], "Fade", "Bubble", "Action", "Key", "Letter").Text == "X" and node(b[1], "Fade", "Bubble", "Action", "Words").Text == "Open", "gamepad: X Open")
uis.last = "Keyboard"
advance(0.3)

workspace.CurrentCamera.ViewportSize.Y = 360
uis.last = "Touch" advance(0.3) uis.last = "Keyboard" advance(0.3)
b = boards()
assert(#b == 1 and b[1].Size.xo == 220 and b[1].Size.yo == 100, "640 x 360 phone view: the smaller bubble")
workspace.CurrentCamera.ViewportSize.Y = 900
advance(0.3)

Theme.MotionEnabled = false
ctx.show = false
advance(0.2)
assert(#boards() == 0, "Reduce Motion: gone at once")
ctx.show = true
advance(0.6)
b = boards()
assert(#b == 1 and node(b[1], "Fade").GroupTransparency == 0, "Reduce Motion: shown at once")
Theme.MotionEnabled = true

nests.PromptHidden:Fire()
potions.PromptHidden:Fire()
advance(0.3)
assert(#boards() == 0 and cas.bound.HubPromptBubbleKey == nil, "walked away: no bubble, key unbound")
local stranger = newPrompt("nests", 3)
stranger:SetAttribute("BubbleStation", nil)
pps.PromptShown:Fire(stranger)
assert(#boards() == 0 and cas.bound.HubPromptBubbleKey == nil, "a prompt without a station id is ignored")
print("shop prompt bubble client smoke passed: shown, nearest, key, tap, window, phone, gamepad, small screen, Reduce Motion")
