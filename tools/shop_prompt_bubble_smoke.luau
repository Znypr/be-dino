-- BD-1017: client smoke for src/client/HubPromptBubble.luau, run by tools/verify_shop_prompt_bubble.py.
-- A tiny mock Roblox (Instances with Parent and signals, services, time, Enum) is just enough to RUN the real client module with the real pure rules.
-- The verifier puts the module sources in front (HubPromptBubbleRules, HubWalkUpRules as locals) and replaces the placeholder line below with the client module.
-- Not Studio: nobody saw a pixel. It proves the wiring: what is built, when it shows and hides, what a key and a tap do, and (BD-1128) that the bubble is a
-- screen layer above the HUD that follows the projected stall point, stays on the screen and stays clear of the HUD rectangles.
local now = 0
local os = {clock = function() return now end}
local methods = {}
local function newSignal()
    local s = {fns = {}}
    function s.Connect(self, fn)
        table.insert(self.fns, fn)
        return {Disconnect = function() local i = table.find(self.fns, fn) if i then table.remove(self.fns, i) end end}
    end
    function s.Once(self, fn) table.insert(self.fns, function(...) self.fns = {} fn(...) end) end
    function s.Fire(self, ...) for _, fn in table.clone(self.fns) do fn(...) end end
    return s
end
local screenSize = {X = 1000, Y = 700}
local screenOrigin = {X = 0, Y = 0}
local function newInstance(class)
    local o = {ClassName = class, Children = {}, attrs = {}}
    if class == "ScreenGui" then rawset(o, "AbsoluteSize", screenSize) rawset(o, "AbsolutePosition", screenOrigin) end
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
local function v3(x, y, z) return setmetatable({x = x, y = y, z = z, X = x, Y = y, Z = z, Magnitude = math.sqrt(x * x + y * y + z * z)}, V3mt) end
V3mt.__sub = function(a, b) return v3(a.x - b.x, a.y - b.y, a.z - b.z) end
V3mt.__add = function(a, b) return v3(a.x + b.x, a.y + b.y, a.z + b.z) end
local Vector3 = {new = v3}
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
local hud = newInstance("Frame") hud.Name = "BeDinoUI" hud.Parent = playerGui
local function rectAttr(x, y, w, h) return {Min = {X = x, Y = y}, Max = {X = x + w, Y = y + h}} end
local uis = {TouchEnabled = false, KeyboardEnabled = true, last = "Keyboard"}
function uis.GetLastInputType(self) return {Name = self.last} end
function uis.GetStringForKeyCode(self, kc) return kc.Name end
local cas = {bound = {}}
function cas.BindAction(self, name, fn, touch, ...) self.bound[name] = fn end
function cas.UnbindAction(self, name) self.bound[name] = nil end
local pps = {PromptShown = newSignal()}
local mods = {}
local renderStepped = newSignal()
local services = {
    Players = {LocalPlayer = player}, UserInputService = uis, ContextActionService = cas, ProximityPromptService = pps, RunService = {RenderStepped = renderStepped},
    ReplicatedStorage = {WaitForChild = function(self, n) return {WaitForChild = function(_, m) return mods[m] end} end},
}
local game = {GetService = function(self, n) return services[n] end}
-- the camera: a stall at world (x, y, z) is at screen (500 + 10 x, 350 - 10 y), 20 studs deep (cameraDepth 0 or less = behind the camera)
local cameraDepth = 20
local workspace = {CurrentCamera = {ViewportSize = {X = 1000, Y = 900}, WorldToViewportPoint = function(self, p) return v3(500 + p.x * 10, 350 - p.y * 10, cameraDepth), true end}}
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

local world = newInstance("Model")
local function newPrompt(id, x)
    local anchor = newInstance("Part") anchor.Name = "Prompt_" .. id anchor.Position = Vector3.new(x, 0, 0)
    anchor.Parent = world
    local prompt = newInstance("ProximityPrompt")
    prompt.Parent = anchor
    prompt.MaxActivationDistance = 10
    prompt.KeyboardKeyCode, prompt.GamepadKeyCode = Enum.KeyCode.E, Enum.KeyCode.ButtonX
    prompt:SetAttribute("BubbleStation", id)
    return prompt
end
local function boards()
    local out = {}
    for _, layer in playerGui.Children do
        if layer.Name == "HubPromptBubbleUI" then
            for _, c in layer.Children do if c.Name == "HubPromptBubble" then out[#out + 1] = c end end
        end
    end
    return out
end
local function layerGui()
    for _, layer in playerGui.Children do if layer.Name == "HubPromptBubbleUI" then return layer end end
    return nil
end
local function overlaps(a, b) return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h end
local function boxOf(board) return {x = board.Position.xo, y = board.Position.yo, w = board.Size.xo, h = board.Size.yo} end
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
assert(b[1].ClassName == "Frame" and b[1].Visible == true, "a frame in a screen layer, not a world billboard")
local layer = layerGui()
assert(layer and layer.ClassName == "ScreenGui" and layer.DisplayOrder == 10 and layer.DisplayOrder > (hud.DisplayOrder or 0) and layer.ResetOnSpawn == false, "the layer is above the HUD (DisplayOrder 10)")
for _, c in playerGui.Children do assert(c.ClassName ~= "BillboardGui", "no billboard: a billboard is always drawn under the HUD (picture 421)") end
assert(node(b[1], "Fade", "Bubble", "Title").Text == "Nests" and node(b[1], "Fade", "Bubble", "Line").Text == "Come and see your eggs!")
assert(node(b[1], "Fade", "Bubble", "Action", "Key", "Letter").Text == "E" and node(b[1], "Fade", "Bubble", "Action", "Words").Text == "Open", "keyboard: the E key and Open")
assert(node(b[1], "Fade").GroupTransparency == 0, "faded in")
assert(b[1].Size.xo == 248 and b[1].Size.yo == 116)
assert(cas.bound.HubPromptBubbleKey ~= nil, "the key is bound while a prompt is shown")
assert((nests.began or 0) == 0, "walking near presses nothing")

pps.PromptShown:Fire(potions)
b = boards()
assert(#b == 1 and node(b[1], "Fade", "Bubble", "Title").Text == "Nests", "one bubble at a time: the nearest (nests at 4, potions at 8)")
root.Position = Vector3.new(9, 0, 0)
advance(0.3)
b = boards()
assert(#b == 1 and node(b[1], "Fade", "Bubble", "Title").Text == "Potions", "walked toward potions: the bubble moved")
root.Position = Vector3.new(0, 0, 0)
advance(0.3)
b = boards()
assert(#b == 1 and node(b[1], "Fade", "Bubble", "Title").Text == "Nests")

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
screenSize.Y = 360
uis.last = "Touch" advance(0.3) uis.last = "Keyboard" advance(0.3)
b = boards()
assert(#b == 1 and b[1].Size.xo == 220 and b[1].Size.yo == 100, "640 x 360 phone view: the smaller bubble")
workspace.CurrentCamera.ViewportSize.Y = 900
screenSize.Y = 700
advance(0.3)
b = boards()
assert(#b == 1 and b[1].Size.xo == 248, "back to a tall screen: the big bubble again (a resized window re-chooses the size)")

-- ---- BD-1128: where the bubble is drawn
do
    local board = boards()[1]
    assert(board ~= nil and board.Visible == true)
    renderStepped:Fire(1 / 60)
    -- no HUD pieces: the bubble is centred on the projected stall point (world (4, 3.5, 0) is at screen (540, 315))
    assert(board.Position.xo == 540 - 124 and board.Position.yo == 315 - 58, "centred on the stall: " .. board.Position.xo .. ", " .. board.Position.yo)
    local box = boxOf(board)
    assert(box.x >= 0 and box.y >= 0 and box.x + box.w <= screenSize.X and box.y + box.h <= screenSize.Y, "on the screen")

    -- a HUD rectangle where the bubble would be (the rail and the weather plate of picture 421): the bubble is clear of it, still on the screen
    hud.attrs.RailRect = rectAttr(380, 240, 300, 120)
    hud.attrs.TimersRect = rectAttr(700, 200, 200, 200)
    Theme.MotionEnabled = false
    renderStepped:Fire(1 / 60)
    box = boxOf(board)
    local rail, timers = {x = 380, y = 240, w = 300, h = 120}, {x = 700, y = 200, w = 200, h = 200}
    assert(not overlaps(box, rail) and not overlaps(box, timers), "clear of the rail and the weather column: " .. box.x .. ", " .. box.y)
    assert(box.x >= 0 and box.y >= 0 and box.x + box.w <= screenSize.X and box.y + box.h <= screenSize.Y, "still on the screen")
    local moved = box.x ~= 416 or box.y ~= 257
    assert(moved, "the bubble moved off the HUD")

    -- the screen layer is offset by the Roblox top bar: coordinates are relative to the layer (AbsolutePosition)
    hud.attrs.RailRect, hud.attrs.TimersRect = nil, nil
    screenOrigin.X, screenOrigin.Y = 0, 36
    renderStepped:Fire(1 / 60)
    assert(board.Position.yo == 315 - 36 - 58, "relative to the layer origin: " .. board.Position.yo)
    screenOrigin.Y = 0

    -- far to the side of the screen: slid back onto it
    cameraDepth = 20
    nests.Parent.Position = Vector3.new(80, 0, 0) -- screen x 1300: off the 1000 px canvas
    renderStepped:Fire(1 / 60)
    box = boxOf(board)
    assert(box.x + box.w <= screenSize.X and box.x >= 0, "a stall off to the side: the bubble stays on the screen")
    nests.Parent.Position = Vector3.new(4, 0, 0)

    -- behind the camera: hidden, and back when it is in front again
    cameraDepth = -5
    renderStepped:Fire(1 / 60)
    assert(board.Visible == false, "behind the camera: nothing to point at")
    cameraDepth = 20
    renderStepped:Fire(1 / 60)
    assert(board.Visible == true)

    -- gliding: with motion on, a changed spot is not reached in one frame; with Reduce Motion it is reached at once
    Theme.MotionEnabled = true
    hud.attrs.RailRect = rectAttr(380, 240, 300, 120)
    renderStepped:Fire(1 / 60)
    box = boxOf(board)
    assert(overlaps(box, rail), "glides: not yet at the new spot after one frame")
    for _ = 1, 40 do renderStepped:Fire(1 / 60) end
    assert(not overlaps(boxOf(board), rail), "glides: there after 40 frames")
    hud.attrs.RailRect = nil
    Theme.MotionEnabled = false
    renderStepped:Fire(1 / 60)
    assert(board.Position.xo == 416 and board.Position.yo == 257, "Reduce Motion: the spot is taken at once")
    Theme.MotionEnabled = true
    renderStepped:Fire(1)

    -- a window opens: the bubble (and its per-frame update) is gone
    local stepsBefore = #renderStepped.fns
    ctx.open = true
    advance(0.3)
    assert(#boards() == 0 and #renderStepped.fns < stepsBefore and #renderStepped.fns == 0, "hidden: the per-frame update is disconnected too")
    ctx.open = false
    advance(1)
    assert(#boards() == 1 and #renderStepped.fns == 1, "back: one per-frame update")
end

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
