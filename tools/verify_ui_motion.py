#!/usr/bin/env python3
"""BD-1182 (docs/228 board 6, docs/229): the UI motion presets behind Config.MotionPresetsEnabled.

What is checked, with the pinned Luau runtime and the REAL src/shared/UIMotion.luau, src/shared/UITheme.luau and src/client/MotionFx.luau:
  1. the numbers of docs/228 board 6 and the pure timing functions: window open 0.3 s, a back-out that starts at 70%, peaks at 103% and
     rests at 100% (the curve is sampled every millisecond); close 0.15 s, hidden at 0.16 s; cards 70 ms apart, 0.4 s each, at most 8
     staggered (card 9 and card 50 start with card 8); press sinks 5 px in 80 ms, release pops to 103%; news line 2.5 s, a repeat while
     it shows stacks "x2", "x3" and starts the 2.5 s again, a different line or a late repeat is a new line; reward flight 0.5 s, wallet
     bump 118%, a whole-number count-up that never passes the goal and ends exactly on it; shimmer every 2.8 s from Legendary up;
  2. Reduce Motion: every preset gives 0 seconds and the end state (scale 1, sink 0, no drop, the final number, no shimmer);
  3. the button (the real Theme.decorate in an engine mock): flag ON = a press tweens a sink of 5 px in 0.08 s and never shrinks, the
     release tweens it back, pops the scale to 1.03 and settles at rest after 0.12 s; the sink is added to the Position, so a button that
     was moved while pressed keeps its new place; Reduce Motion = no sink object, no movement; flag OFF = exactly today's tweens
     (press .96 in .09 s, release 1) and no sink object;
  4. the window (the real MotionFx with a recording Theme): open = scale starts at 70% of the target, one 0.3 s Back tween to the target;
     close = three 0.15 s tweens and "hide after 0.16 s"; Reduce Motion = it touches nothing;
  5. the flag: false in Config and in the default profile, ON in the playtest profile, in the rehearsal list; Bootstrap asks the flag
     before it requires MotionFx; no server file knows the feature; UIMotion touches no engine service;
  6. mutants put each defect back and the checks must fail.
NOT Studio evidence: nothing is drawn here. How the open pop, the close and the press look and feel (desktop, phone) is unverified.
Usage: python tools/verify_ui_motion.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MOTION = 'src/shared/UIMotion.luau'
THEME = 'src/shared/UITheme.luau'
FX = 'src/client/MotionFx.luau'
BOOT = 'src/client/Bootstrap.client.luau'
CONFIG = 'src/shared/Config.luau'
PROFILES = 'tools/release_profiles.py'


def reader(mutant=None):
    def read(path):
        text = (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')
        if mutant and mutant[0] == path:
            assert text.count(mutant[1]) == 1, 'mutant anchor must match once in %s: %r' % (path, mutant[1])
            text = text.replace(mutant[1], mutant[2])
        return text
    return read


def wrap(source):
    return '(function()\n' + source + '\nend)()'


PURE = r'''
local M = __MOTION__
local function near(a, b, eps) return math.abs(a - b) <= (eps or 1e-9) end
-- ---- the numbers of docs/228 board 6
assert(M.WindowOpenSeconds == 0.3 and M.WindowOpenPeak == 1.03 and M.WindowCloseSeconds == 0.15, "window numbers")
assert(M.CardStaggerSeconds == 0.07 and M.CardSeconds == 0.4 and M.CardStaggerMax == 8, "card numbers")
assert(M.PressSinkPixels == 5 and M.PressSeconds == 0.08 and M.ReleasePop == 1.03, "button numbers")
assert(M.NewsSeconds == 2.5, "news seconds")
assert(M.RewardFlySeconds == 0.5 and M.WalletBump == 1.18, "reward numbers")
assert(M.ShimmerEverySeconds == 2.8 and M.ShimmerMinRarity == 5, "shimmer numbers")

-- ---- window open: one Back tween, starts at 70%, peaks at 103%, rests at 100% after 0.3 s
local open = M.windowOpen(false)
assert(open.seconds == 0.3 and open.to == 1 and open.style == "Back", "open plan")
assert(near(open.from, 0.7, 1e-3), "open starts at 70% so that the back-out peaks at 103%, got " .. open.from)
assert(near(M.backOut(0), 0) and near(M.backOut(1), 1), "back-out ends")
local peak, peakAt, low, after = 0, 0, 9, nil
for i = 0, 300 do
    local t = i / 1000
    local s = M.windowOpenScale(t, false)
    if s > peak then peak, peakAt = s, t end
    low = math.min(low, s)
end
assert(near(peak, 1.03, 5e-4), "the window peaks at 103%, got " .. peak)
assert(peakAt > 0.1 and peakAt < 0.25, "the peak is inside the tween, at " .. peakAt)
assert(near(low, open.from), "never smaller than the start")
assert(near(M.windowOpenScale(0, false), open.from) and M.windowOpenScale(0.3, false) == 1 and M.windowOpenScale(9, false) == 1 and near(M.windowOpenScale(-1, false), open.from), "open ends")
local previous = M.windowOpenScale(peakAt, false)
for i = math.floor(peakAt * 1000) + 1, 300 do
    local s = M.windowOpenScale(i / 1000, false)
    assert(s <= previous + 1e-12 and s >= 1 - 1e-12, "after the peak it only settles down to 100%")
    previous = s
end
-- ---- window close
local close = M.windowClose(false)
assert(close.seconds == 0.15 and near(close.hideAfter, 0.16) and close.hideAfter > close.seconds and close.shrink == 0.96, "close plan")

-- ---- cards
assert(M.card(1, false).delay == 0 and near(M.card(2, false).delay, 0.07) and near(M.card(8, false).delay, 0.49), "card delays")
for _, index in {9, 10, 50, 1000} do assert(M.card(index, false).delay == M.card(8, false).delay, "cards after the 8th appear with the 8th: " .. index) end
assert(M.card(0, false).delay == 0 and M.card(-3, false).delay == 0, "a bad index is the first card")
local distinct, seen = 0, {}
for index = 1, 40 do
    local c = M.card(index, false)
    assert(c.seconds == 0.4, "every card takes 0.4 s")
    if index > 1 then assert(c.delay >= M.card(index - 1, false).delay, "delays never go back") end
    local key = string.format("%.4f", c.delay)
    if not seen[key] then seen[key] = true distinct += 1 end
end
assert(distinct == 8, "at most 8 staggered, got " .. distinct)
assert(M.cardsDone(0, false) == 0 and near(M.cardsDone(1, false), 0.4) and near(M.cardsDone(8, false), 0.89) and near(M.cardsDone(30, false), 0.89), "cardsDone")

-- ---- button
local press, release = M.press(false), M.release(false)
assert(press.sink == 5 and press.seconds == 0.08, "press")
assert(release.pop == 1.03 and release.popSeconds == 0.08 and release.settleSeconds == 0.12, "release")

-- ---- news line
local n = M.newsNew()
assert(M.newsText(n, 0) == nil and not M.newsVisible(n, 0), "nothing shows at first")
assert(M.newsPush(n, "AURORA SKY!", 10) == "new" and M.newsText(n, 10) == "AURORA SKY!", "first line has no counter")
assert(M.newsPush(n, "AURORA SKY!", 11) == "stack" and M.newsText(n, 11) == "AURORA SKY! x2", "a repeat stacks x2")
assert(M.newsPush(n, "AURORA SKY!", 12) == "stack" and M.newsText(n, 12) == "AURORA SKY! x3", "then x3")
assert(M.newsVisible(n, 14.49) and not M.newsVisible(n, 14.5) and M.newsText(n, 14.5) == nil, "2.5 s after the last repeat it is gone")
assert(M.newsPush(n, "AURORA SKY!", 15) == "new" and M.newsText(n, 15) == "AURORA SKY!", "a repeat after the line left is a new line")
assert(M.newsPush(n, "RAIN!", 16) == "new" and M.newsText(n, 16) == "RAIN!" and n.count == 1, "a different line replaces it and starts at 1")
assert(M.newsPush(n, "AURORA SKY!", 16.5) == "new" and n.count == 1, "the old line does not keep its counter")
local m = M.newsNew()
for i = 1, 150 do M.newsPush(m, "A", i * 0.01) end
assert(M.newsText(m, 1.5) == "A x99", "the counter stops at x99")
local single = M.newsNew()
M.newsPush(single, "A", 0)
assert(M.newsVisible(single, 2.49) and not M.newsVisible(single, 2.5), "a line shows 2.5 s")
assert(M.newsDrop(false).seconds > 0 and M.newsDrop(false).offset > 0, "the line drops in")

-- ---- reward
local reward = M.reward(false)
assert(reward.flySeconds == 0.5 and reward.bump == 1.18 and reward.bumpSeconds > 0 and reward.countSeconds > 0, "reward plan")
assert(M.walletScale(0, false) == 1 and M.walletScale(reward.bumpSeconds, false) == 1 and near(M.walletScale(reward.bumpSeconds / 2, false), 1.18), "wallet bump")
local top = 0
for i = 0, 400 do top = math.max(top, M.walletScale(i / 1000, false)) end
assert(near(top, 1.18, 1e-6), "the wallet never grows past 118%")
assert(near(M.walletScale(reward.bumpSeconds * 0.25, false), 1.09) and near(M.walletScale(reward.bumpSeconds * 0.75, false), 1.09), "the wallet goes up and comes back down")
assert(M.countUp(100, 220, 0, false) == 100 and M.countUp(100, 220, reward.countSeconds, false) == 220 and M.countUp(100, 220, 99, false) == 220, "count-up ends")
local last = 100
for i = 0, 600 do
    local v = M.countUp(100, 220, i / 1000, false)
    assert(v == math.floor(v) and v >= last and v <= 220, "count-up: whole, rising, never past the goal")
    last = v
end
assert(last == 220, "count-up reaches the goal")
local mid = M.countUp(0, 1000, reward.countSeconds / 2, false)
assert(mid > 500 and mid < 1000, "count-up eases out (past half-way at half time), got " .. mid)
local down = 220
for i = 0, 600 do
    local v = M.countUp(220, 100, i / 1000, false)
    assert(v == math.floor(v) and v <= down and v >= 100, "count-down: whole, falling, never past the goal")
    down = v
end
assert(down == 100 and M.countUp(7, 7, 0.1, false) == 7, "count-down reaches the goal; no change stays")

-- ---- shimmer
assert(M.shimmerEligible(5) and M.shimmerEligible(6) and not M.shimmerEligible(4) and not M.shimmerEligible(1), "Legendary and above only")
assert(M.shimmerAt(1, false) == 2.8 and near(M.shimmerAt(2, false), 5.6) and near(M.shimmerAt(3, false) - M.shimmerAt(2, false), 2.8) and M.shimmerAt(0, false) == nil, "every 2.8 s")
assert(M.shimmerPhase(1, 5, false) == nil and M.shimmerPhase(2.8, 5, false) == 0 and near(M.shimmerPhase(3.1, 5, false), 0.5, 1e-6), "sweep")
assert(M.shimmerPhase(2.8 + M.ShimmerSweepSeconds + 0.01, 5, false) == nil and M.shimmerPhase(3.0, 4, false) == nil and M.shimmerPhase(3.0, 6, false) ~= nil, "rest; Epic never; Mythic too")
assert(M.ShimmerSweepSeconds < M.ShimmerEverySeconds, "the sweep fits its period")

-- ---- Reduce Motion: the end state at once, no movement
local ro = M.windowOpen(true)
assert(ro.seconds == 0 and ro.from == 1 and ro.to == 1, "reduce: the window is simply there")
for _, t in {-1, 0, 0.1, 0.3, 5} do assert(M.windowOpenScale(t, true) == 1, "reduce: scale 1 at every time") end
local rc = M.windowClose(true)
assert(rc.seconds == 0 and rc.hideAfter == 0 and rc.shrink == 1, "reduce: close at once")
for _, index in {1, 2, 8, 9, 50} do local c = M.card(index, true) assert(c.delay == 0 and c.seconds == 0, "reduce: cards at once") end
assert(M.cardsDone(30, true) == 0, "reduce: all cards at once")
assert(M.press(true).sink == 0 and M.press(true).seconds == 0, "reduce: no sink")
local rr = M.release(true)
assert(rr.pop == 1 and rr.popSeconds == 0 and rr.settleSeconds == 0, "reduce: no pop")
assert(M.newsDrop(true).offset == 0 and M.newsDrop(true).seconds == 0, "reduce: no drop")
local rn = M.newsNew()
assert(M.newsPush(rn, "A", 0) == "new" and M.newsPush(rn, "A", 1) == "stack" and M.newsText(rn, 1) == "A x2" and not M.newsVisible(rn, 3.5), "reduce: the news line still shows 2.5 s and stacks")
local rw = M.reward(true)
assert(rw.flySeconds == 0 and rw.bump == 1 and rw.bumpSeconds == 0 and rw.countSeconds == 0, "reduce: no flight, no bump")
for _, t in {0, 0.1, 1} do assert(M.walletScale(t, true) == 1 and M.countUp(100, 220, t, true) == 220, "reduce: the final number at once") end
assert(M.shimmerAt(1, true) == nil and M.shimmerPhase(3.0, 5, true) == nil, "reduce: no shimmer")
print("ui motion presets ok")
'''

# An engine mock just big enough for the real UITheme: Theme.decorate on a TextButton. Tweens are recorded; finish() lets them end.
ENGINE = r'''
local function signal()
    local s = {handlers = {}}
    function s:Connect(f) table.insert(self.handlers, f) return {Disconnect = function() end} end
    function s:Once(f) table.insert(self.handlers, f) end
    function s:Fire(...) for _, h in self.handlers do h(...) end end
    return s
end
local function names(path)
    local cache = {}
    return setmetatable({}, {__index = function(_, k)
        if cache[k] == nil then cache[k] = names(path .. "." .. tostring(k)) end
        return cache[k]
    end, __tostring = function() return path end})
end
local Enum = names("Enum")
local UDim2 = {}
local udim2 = {__add = function(a, b) return UDim2.new(a.X.Scale + b.X.Scale, a.X.Offset + b.X.Offset, a.Y.Scale + b.Y.Scale, a.Y.Offset + b.Y.Offset) end}
function UDim2.new(xs, xo, ys, yo) return setmetatable({X = {Scale = xs or 0, Offset = xo or 0}, Y = {Scale = ys or 0, Offset = yo or 0}}, udim2) end
function UDim2.fromOffset(x, y) return UDim2.new(0, x, 0, y) end
function UDim2.fromScale(x, y) return UDim2.new(x, 0, y, 0) end
local UDim = {new = function(s, o) return {Scale = s, Offset = o} end}
local Color3 = {new = function(...) return {...} end, fromRGB = function(...) return {...} end, fromHex = function(h) return {h} end}
local ColorSequence = {new = function(...) return {...} end}
local TweenInfo = {new = function(seconds, style, direction) return {seconds = seconds, style = tostring(style), direction = tostring(direction)} end}
local made = {}
local function instance(class)
    local props = {ClassName = class, attributes = {}}
    local signals = {}
    local self
    self = setmetatable({}, {
        __index = function(_, k)
            if k == "IsA" then return function(_, c) return c == class or (c == "GuiObject" and class == "TextButton") end end
            if k == "GetAttribute" then return function(_, name) return props.attributes[name] end end
            if k == "SetAttribute" then return function(_, name, v) props.attributes[name] = v end end
            if k == "Changed" or k == "MouseEnter" or k == "MouseLeave" or k == "SelectionGained" or k == "SelectionLost" or k == "InputBegan"
                or k == "InputEnded" or k == "Destroying" or k == "Activated" then
                if not signals[k] then signals[k] = signal() end
                return signals[k]
            end
            return props[k]
        end,
        __newindex = function(_, k, v)
            props[k] = v
            if class == "NumberValue" and k == "Value" and signals.Changed then signals.Changed:Fire(v) end
        end,
    })
    made[class] = (made[class] or 0) + 1
    return self
end
local Instance = {new = function(class)
    local i = instance(class)
    if class == "UIScale" then i.Scale = 1 end
    if class == "NumberValue" then i.Value = 0 end
    return i
end}
local log, live = {}, {}
local TweenService = {Create = function(_, target, info, goals)
    local tween = {target = target, info = info, goals = goals, Completed = signal()}
    function tween:Play() table.insert(log, {target = target, seconds = info.seconds, style = info.style, goals = goals}) table.insert(live, self) end
    function tween:Cancel() self.cancelled = true end
    return tween
end}
local function finish() -- every running tween reaches its goal (half-way first, so a Changed handler sees more than one step)
    local running = live
    live = {}
    for _, tween in running do
        if not tween.cancelled then
            for property, goal in tween.goals do
                if type(goal) == "number" then tween.target[property] = (tween.target[property] + goal) / 2 end
                tween.target[property] = goal
            end
            tween.Completed:Fire()
        end
    end
end
local delays = {}
local task = {delay = function(seconds, f) table.insert(delays, {seconds = seconds, f = f}) end}
local function runDelays() local due = delays delays = {} for _, d in due do d.f() end return due end
local game = {GetService = function(_, name) assert(name == "TweenService", "UITheme asks for " .. tostring(name)) return TweenService end}
local script = {Parent = setmetatable({}, {__index = function(_, k) return k end})}
'''

BUTTON = ENGINE + r'''
local UIMotion = __MOTION__
local function require(key)
    if key == "Config" then return {MotionPresetsEnabled = __FLAG__} end
    if key == "UIMotion" then return UIMotion end
    if key == "AssetSlots" then return {Images = {}} end
    return {}
end
local Theme = __THEME__
local FLAG = __FLAG__
local function near(a, b) return math.abs(a - b) < 1e-9 end
local function button(base)
    local b = Instance.new("TextButton")
    b.Position, b.Parent = UDim2.new(0, 40, 0, 100), {}
    if base then b:SetAttribute("UIScaleBase", base) end
    Theme.decorate(b, 4)
    return b
end
local function scaleOf() -- the UIScale the last decorate made: the target of the first Scale tween
    for _, entry in log do if entry.goals.Scale ~= nil then return entry.target end end
    error("no scale tween")
end
local MOUSE, TOUCH = {UserInputType = Enum.UserInputType.MouseButton1, KeyCode = Enum.KeyCode.Unknown}, {UserInputType = Enum.UserInputType.Touch, KeyCode = Enum.KeyCode.Unknown}
local function scales() local out = {} for _, e in log do if e.goals.Scale ~= nil then table.insert(out, string.format("%.3f@%.2f", e.goals.Scale, e.seconds)) end end return table.concat(out, " ") end
local function sinks() local out = {} for _, e in log do if e.goals.Value ~= nil then table.insert(out, string.format("%d@%.2f", e.goals.Value, e.seconds)) end end return table.concat(out, " ") end

if not FLAG then
    -- today's behaviour, tween for tween
    local b = button()
    b.InputBegan:Fire(TOUCH)
    assert(scales() == "0.960@0.09" and sinks() == "", "flag off: a press shrinks to 96% in .09 s, got " .. scales() .. " / " .. sinks())
    finish()
    b.InputEnded:Fire(TOUCH)
    assert(scales() == "0.960@0.09 1.000@0.09", "flag off: the release goes back to 1, got " .. scales())
    finish()
    assert(#runDelays() == 0, "flag off: nothing is scheduled")
    b.MouseEnter:Fire() b.InputBegan:Fire(MOUSE) b.InputEnded:Fire(MOUSE) b.MouseLeave:Fire()
    assert(scales() == "0.960@0.09 1.000@0.09 1.035@0.09 0.960@0.09 1.035@0.09 1.000@0.09", "flag off: hover 1.035, press .96, release 1.035, leave 1, got " .. scales())
    assert(made.NumberValue == nil and b.Position.Y.Offset == 100 and sinks() == "", "flag off: no sink object, the button never moves")
    Theme.MotionEnabled = false
    log = {}
    b.InputBegan:Fire(TOUCH) b.InputEnded:Fire(TOUCH)
    assert(#log == 0 and scaleOf == scaleOf and b.Position.Y.Offset == 100, "flag off + Reduce Motion: no tween at all")
    print("button: flag off is today's motion")
    return
end

-- ---- flag on
local b = button()
b.InputBegan:Fire(TOUCH)
assert(sinks() == "5@0.08", "a press sinks 5 px in 80 ms, got " .. sinks())
assert(scales() == "1.000@0.09", "a press does not shrink the button, got " .. scales())
local scale = scaleOf()
finish()
assert(b.Position.Y.Offset == 105 and b.Position.X.Offset == 40, "the button sits 5 px lower while pressed")
b.Position = b.Position + UDim2.fromOffset(0, 200) -- a layout pass moves the button while it is pressed
log = {}
b.InputEnded:Fire(TOUCH)
assert(sinks() == "0@0.08", "the release lifts it in 80 ms, got " .. sinks())
assert(scales() == "1.030@0.08", "the release pops to 103%, got " .. scales())
finish()
assert(near(scale.Scale, 1.03), "popped")
local due = runDelays()
assert(#due == 1 and due[1].seconds == 0.08, "the settle waits for the pop")
assert(scales() == "1.030@0.08 1.000@0.12", "then back to rest in 0.12 s, got " .. scales())
finish()
assert(scale.Scale == 1 and b.Position.Y.Offset == 300, "at rest; the move made while pressed is kept (300), got " .. b.Position.Y.Offset)
assert(made.NumberValue == 1, "one sink object per pressed button")
-- a second press during the pop: the old settle must not fire over it
b.InputBegan:Fire(TOUCH) finish()
b.InputEnded:Fire(TOUCH)
b.InputBegan:Fire(TOUCH)
log = {}
runDelays()
assert(scales() == "", "a stale settle does nothing while the button is pressed again, got " .. scales())
finish()
assert(b.Position.Y.Offset == 305, "pressed again: 5 px down")
b.MouseLeave:Fire() finish()
assert(b.Position.Y.Offset == 300 and scale.Scale == 1, "the finger leaves: back up, no pop")
-- mouse: hover 103.5% stays the rest after the pop; UIScaleBase is honoured
log = {}
local c = button(0.8)
c.MouseEnter:Fire() c.InputBegan:Fire(MOUSE) finish() c.InputEnded:Fire(MOUSE) finish() runDelays()
assert(scales() == "0.828@0.09 0.800@0.09 0.824@0.08 0.828@0.12", "mouse with base .8: hover, press flat, pop 103%, rest at hover, got " .. scales())
-- a release that had no press (the finger came from elsewhere) is the plain rest, no pop
log = {}
local d = button()
d.InputEnded:Fire(TOUCH)
assert(scales() == "1.000@0.09" and sinks() == "", "no press, no pop")
-- Reduce Motion: nothing moves
Theme.MotionEnabled = false
local before = made.NumberValue
local e = button()
log = {}
e.InputBegan:Fire(TOUCH) e.InputEnded:Fire(TOUCH)
assert(#log == 0 and #runDelays() == 0, "Reduce Motion: no tween, nothing scheduled")
assert(made.NumberValue == before and e.Position.Y.Offset == 100, "Reduce Motion: no sink object, the button never moves")
b.InputBegan:Fire(TOUCH) b.InputEnded:Fire(TOUCH)
assert(b.Position.Y.Offset == 300 and scale.Scale == 1 and #log == 0, "Reduce Motion on a button that has a sink object: still no movement")
print("button: sink, pop, settle, Reduce Motion ok")
'''

WINDOW = r'''
local calls = {}
local Theme = {MotionEnabled = __MOTION_ON__}
function Theme.animate(target, seconds, goals, style) table.insert(calls, {op = "animate", target = target, seconds = seconds, goals = goals, style = style}) end
function Theme.cancel(target) table.insert(calls, {op = "cancel", target = target}) end
local Enum = {EasingStyle = {Back = "Back"}}
local Shared = {WaitForChild = function(_, name) return name end}
local game = {GetService = function(_, name) assert(name == "ReplicatedStorage") return {WaitForChild = function() return Shared end} end}
local script = {Parent = {ModalCompact = "ModalCompact"}}
local UIMotion = __MOTION__
local function require(key)
    if key == "UITheme" then return Theme end
    if key == "UIMotion" then return UIMotion end
    if key == "ModalCompact" then return {model = function() return {scale = 0.8} end, home = function(y) return "home " .. y end} end
    error("MotionFx must not require " .. tostring(key))
end
local Fx = __FX__
local scale, shade, panel = {Scale = 0.768}, {name = "shade"}, {name = "panel"}
local function near(a, b) return math.abs(a - b) < 1e-3 end
if Theme.MotionEnabled then
    Fx.open(scale, 0.8)
    assert(near(scale.Scale, 0.8 * 0.7), "the window starts at 70% of its size, got " .. scale.Scale)
    assert(#calls == 2 and calls[1].op == "cancel" and calls[1].target == scale, "the running open tween is stopped first")
    local a = calls[2]
    assert(a.op == "animate" and a.target == scale and a.seconds == 0.3 and a.goals.Scale == 0.8 and a.style == "Back", "one 0.3 s Back tween to the settled size")
    calls = {}
    local hide = Fx.close(scale, shade, panel)
    assert(math.abs(hide - 0.16) < 1e-9, "hide the window 0.16 s after the close starts, got " .. hide)
    assert(#calls == 3, "three close tweens")
    for _, c in calls do assert(c.op == "animate" and c.seconds == 0.15 and c.style == nil, "every close tween takes 0.15 s") end
    assert(calls[1].target == scale and near(calls[1].goals.Scale, 0.8 * 0.96), "the small shrink")
    assert(calls[2].target == shade and calls[2].goals.BackgroundTransparency == 1, "the scrim fades out")
    assert(calls[3].target == panel and calls[3].goals.Position == "home 0.52", "the slide ends where Bootstrap's does")
else
    Fx.open(scale, 0.8)
    assert(#calls == 0 and scale.Scale == 0.768, "Reduce Motion: open touches nothing")
    assert(Fx.close(scale, shade, panel) == 0 and #calls == 0 and scale.Scale == 0.768, "Reduce Motion: close touches nothing and hides at once")
end
print("window: __MOTION_ON__ ok")
'''


def run(runner, source, name='ui_motion'):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / (name + '.luau')
        path.write_text(source, encoding='utf-8')
        done = subprocess.run([runner, str(path)], capture_output=True, text=True, timeout=120)
    return done.returncode == 0, (done.stdout + done.stderr)


def code_only(text):
    return '\n'.join(line.split('--', 1)[0] for line in text.splitlines())


OPEN_HOOK = '    if Config.MotionPresetsEnabled and not wasVisible then require(script.Parent.MotionFx).open(scale,viewportScale()) end -- BD-1182\n'
CLOSE_HOOK = '    local hide=if Config.MotionPresetsEnabled then require(script.Parent.MotionFx).close(scale,shade,panel) else .13 -- BD-1182\n'
CLOSE_USE = '    task.delay(if motion then hide else 0,function() if modalVersion==version then shade.Visible=false end end)\n'


def static_checks(read):
    cfg = read(CONFIG)
    assert len(re.findall(r'^    MotionPresetsEnabled = false,$', cfg, re.M)) == 1, 'MotionPresetsEnabled ships false in Config (once)'
    profiles = read(PROFILES)
    assert '_flag_off("MotionPresetsEnabled",' in profiles, 'the default profile pins the flag off'
    assert 'Rule("MotionPresetsEnabled", "set", True,' in profiles, 'the playtest profile sets it on (docs/157 standing rule)'
    assert '("MotionPresetsEnabled", "BD-1182' in profiles, 'the rehearsal list has it'
    assert '"MotionPresetsEnabled"' in read('tools/release_playtest.py'), 'the playtest manifest records it'
    motion = code_only(read(MOTION))
    for needle in ('game', 'Instance', 'TweenService', 'task.', 'os.', 'tick(', 'math.random', 'require(', 'Enum.'):
        assert needle not in motion, 'UIMotion is pure (no engine, clock or RNG): ' + needle
    boot = read(BOOT)
    assert boot.count(OPEN_HOOK) == 1, 'open() asks the flag, then MotionFx.open, only for a window that was closed'
    assert boot.count(CLOSE_HOOK + CLOSE_USE) == 1, 'close() asks the flag, then MotionFx.close; flag off = the old .13'
    assert boot.count('MotionFx') == 2 and boot.count('MotionPresetsEnabled') == 2, 'Bootstrap requires MotionFx only behind the flag (two hooks)'
    assert boot.index('Theme.animate(scale,.16,{Scale=viewportScale()})') < boot.index(OPEN_HOOK) < boot.index('    render(name)\n'), 'the preset replaces the old open tween, before the screen is drawn'
    assert boot.index('Theme.animate(scale,.12,{Scale=scale.Scale*.96})') < boot.index(CLOSE_HOOK), 'the preset re-times the old close tweens'
    theme = read(THEME)
    assert theme.count('local presets = (Config :: any).MotionPresetsEnabled == true') == 1, 'the button reads the flag once per button'
    assert theme.count('if presets then pressDown() else animate(.96) end') == 1, 'flag off = the old press'
    assert theme.count('if presets and wasPressed then pressUp(rest) else animate(rest) end') == 1, 'flag off = the old release'
    assert theme.count('if presets then pressLost() end') == 2, 'leaving the button lifts it (mouse and gamepad)'
    fx = code_only(read(FX))
    for needle in ('TweenService', 'FireServer', 'InvokeServer', 'Instance.new', 'task.'):
        assert needle not in fx, 'MotionFx only hands numbers to Theme.animate: ' + needle
    for file in (ROOT / 'src').rglob('*.luau'):
        rel = file.relative_to(ROOT).as_posix()
        text = file.read_text(encoding='utf-8')
        if rel.startswith('src/server'):
            for word in ('UIMotion', 'Parent.MotionFx', 'MotionPresetsEnabled'):
                assert word not in text, 'no server change: %s in %s' % (word, rel)
        elif rel not in (BOOT, FX) and 'Parent.MotionFx' in text:
            raise AssertionError('only Bootstrap calls MotionFx: ' + rel)


def check(runner, mutant=None):
    read = reader(mutant)
    try:
        static_checks(read)
    except AssertionError as error:
        return False, 'static: %s\n' % error
    motion = wrap(read(MOTION))
    out = ''
    ok, text = run(runner, PURE.replace('__MOTION__', motion), 'pure')
    out += text
    if not ok:
        return False, out
    for flag in ('false', 'true'):
        ok, text = run(runner, BUTTON.replace('__FLAG__', flag).replace('__MOTION__', motion).replace('__THEME__', wrap(read(THEME))), 'button_' + flag)
        out += text
        if not ok:
            return False, out
    for on in ('true', 'false'):
        ok, text = run(runner, WINDOW.replace('__MOTION_ON__', on).replace('__MOTION__', motion).replace('__FX__', wrap(read(FX))), 'window_' + on)
        out += text
        if not ok:
            return False, out
    return True, out


MUTANTS = {
    'the window opens in 0.5 s': (MOTION, 'M.WindowOpenSeconds = 0.3', 'M.WindowOpenSeconds = 0.5'),
    'the window peaks at 110%': (MOTION, 'M.WindowOpenPeak = 1.03', 'M.WindowOpenPeak = 1.10'),
    'the window starts at 96% (peak only 100.4%)': (MOTION, 'return {from = 1 - (M.WindowOpenPeak - 1) / backPeak(), to = 1,', 'return {from = 0.96, to = 1,'),
    'the open curve has no overshoot': (MOTION, '    return 1 + (s + 1) * u * u * u + s * u * u\nend\n\nlocal function backPeak', '    return 1 - u * u\nend\n\nlocal function backPeak'),
    'the window closes in 0.3 s': (MOTION, 'M.WindowCloseSeconds = 0.15', 'M.WindowCloseSeconds = 0.3'),
    'the window is hidden before the close ends': (MOTION, 'hideAfter = M.WindowCloseSeconds + M.WindowHideGap}', 'hideAfter = M.WindowCloseSeconds - M.WindowHideGap}'),
    'cards are 100 ms apart': (MOTION, 'M.CardStaggerSeconds = 0.07', 'M.CardStaggerSeconds = 0.1'),
    'a card takes 0.2 s': (MOTION, 'M.CardSeconds = 0.4', 'M.CardSeconds = 0.2'),
    'twelve cards are staggered': (MOTION, 'M.CardStaggerMax = 8', 'M.CardStaggerMax = 12'),
    'the stagger has no cap': (MOTION, '    local slot = math.clamp(math.floor(index), 1, M.CardStaggerMax)', '    local slot = math.max(math.floor(index), 1)'),
    'the first card waits one step': (MOTION, '    return {delay = (slot - 1) * M.CardStaggerSeconds, seconds = M.CardSeconds}', '    return {delay = slot * M.CardStaggerSeconds, seconds = M.CardSeconds}'),
    'a press sinks 8 px': (MOTION, 'M.PressSinkPixels = 5', 'M.PressSinkPixels = 8'),
    'a press takes 0.2 s': (MOTION, 'M.PressSeconds = 0.08', 'M.PressSeconds = 0.2'),
    'the release pops to 110%': (MOTION, 'M.ReleasePop = 1.03', 'M.ReleasePop = 1.1'),
    'the news line shows 5 s': (MOTION, 'M.NewsSeconds = 2.5', 'M.NewsSeconds = 5'),
    'a repeat is a new line': (MOTION, '    if M.newsVisible(state, now) and state.text == text then', '    if false then'),
    'a different line stacks too': (MOTION, '    if M.newsVisible(state, now) and state.text == text then', '    if M.newsVisible(state, now) then'),
    'a late repeat still stacks': (MOTION, '    if M.newsVisible(state, now) and state.text == text then', '    if state.text == text then'),
    'a repeat does not start the 2.5 s again': (MOTION, '        state.count = math.min(state.count + 1, M.NewsStackMax)\n        state.shownAt = now\n', '        state.count = math.min(state.count + 1, M.NewsStackMax)\n'),
    'the first line already says x1': (MOTION, '    return if state.count >= 2 then text .. " x" .. state.count else text', '    return text .. " x" .. state.count'),
    'the counter has no cap': (MOTION, '        state.count = math.min(state.count + 1, M.NewsStackMax)', '        state.count = state.count + 1'),
    'the reward flies 1 s': (MOTION, 'M.RewardFlySeconds = 0.5', 'M.RewardFlySeconds = 1'),
    'the wallet bumps to 150%': (MOTION, 'M.WalletBump = 1.18', 'M.WalletBump = 1.5'),
    'the wallet stays big': (MOTION, '    local share = if t <= half then t / half else (plan.bumpSeconds - t) / half', '    local share = math.min(t / half, 1)'),
    'the count-up stops short': (MOTION, '    if seconds <= 0 or t >= seconds then return to end', '    if seconds <= 0 then return to end\n    if t >= seconds then return to - 1 end'),
    'the count-up shows fractions': (MOTION, '    return if to >= from then math.min(to, math.floor(value)) else math.max(to, math.ceil(value))', '    return value'),
    'the count-up is linear': (MOTION, '    local eased = 1 - (1 - share) * (1 - share)', '    local eased = share'),
    'the shimmer comes every 1 s': (MOTION, 'M.ShimmerEverySeconds = 2.8', 'M.ShimmerEverySeconds = 1'),
    'Epic shimmers too': (MOTION, 'M.ShimmerMinRarity = 5', 'M.ShimmerMinRarity = 4'),
    'the shimmer ignores the rarity': (MOTION, '    if reduce or not M.shimmerEligible(rarityRank) or t < M.ShimmerEverySeconds then return nil end', '    if reduce or t < M.ShimmerEverySeconds then return nil end'),
    'the shimmer never rests': (MOTION, '    if into >= M.ShimmerSweepSeconds then return nil end\n', ''),
    'Reduce Motion: the window still pops': (MOTION, '    if reduce then return {from = 1, to = 1, seconds = 0, style = "None"} end\n', ''),
    'Reduce Motion: the close still takes time': (MOTION, '    if reduce then return {seconds = 0, shrink = 1, hideAfter = 0} end\n', ''),
    'Reduce Motion: cards still stagger': (MOTION, '    if reduce then return {delay = 0, seconds = 0} end\n', ''),
    'Reduce Motion: the button still sinks': (MOTION, '    if reduce then return {sink = 0, seconds = 0} end\n', ''),
    'Reduce Motion: the button still pops': (MOTION, '    if reduce then return {pop = 1, popSeconds = 0, settleSeconds = 0} end\n', ''),
    'Reduce Motion: the news line still drops': (MOTION, '    if reduce then return {offset = 0, seconds = 0} end\n', ''),
    'Reduce Motion: the reward still flies': (MOTION, '    if reduce then return {flySeconds = 0, bump = 1, bumpSeconds = 0, countSeconds = 0} end\n', ''),
    'Reduce Motion: the shimmer still runs': (MOTION, '    if reduce or not M.shimmerEligible(rarityRank) or t < M.ShimmerEverySeconds then return nil end', '    if not M.shimmerEligible(rarityRank) or t < M.ShimmerEverySeconds then return nil end'),
    'Reduce Motion: shimmer times are still handed out': (MOTION, '    if reduce or n < 1 then return nil end', '    if n < 1 then return nil end'),
    'UIMotion reads a clock': (MOTION, '    return state.text ~= nil and now - state.shownAt < M.NewsSeconds', '    return state.text ~= nil and (now or os.clock()) - state.shownAt < M.NewsSeconds'),
    'the flag is on in the source': (CONFIG, '    MotionPresetsEnabled = false,', '    MotionPresetsEnabled = true,'),
    'the default profile does not pin the flag off': (PROFILES, '_flag_off("MotionPresetsEnabled",', '_flag_off("MotionPresetsEnabledX",'),
    'the playtest profile does not switch it on': (PROFILES, 'Rule("MotionPresetsEnabled", "set", True,', 'Rule("MotionPresetsEnabled", "set", False,'),
    'the flag is missing from the rehearsal list': (PROFILES, '("MotionPresetsEnabled", "BD-1182', '("MotionPresetsEnabledX", "BD-1182'),
    'the button ignores the flag': (THEME, 'local presets = (Config :: any).MotionPresetsEnabled == true', 'local presets = true'),
    'the button still shrinks on a press (flag on)': (THEME, '            sinkTo(plan.sink, plan.seconds)\n            animate(1)', '            sinkTo(plan.sink, plan.seconds)\n            animate(.96)'),
    'the button never sinks': (THEME, '            sinkTo(plan.sink, plan.seconds)\n            animate(1)', '            animate(1)'),
    'the sink sets the Position instead of adding to it': (THEME, '                    object.Position += UDim2.fromOffset(0, now - sunk)', '                    object.Position = UDim2.new(0, 40, 0, 100 + now)'),
    'the sink adds the whole value at every step': (THEME, '                    object.Position += UDim2.fromOffset(0, now - sunk)', '                    object.Position += UDim2.fromOffset(0, now)'),
    'the release does not pop': (THEME, '            Theme.animate(scale, plan.popSeconds, {Scale = plan.pop * (object:GetAttribute("UIScaleBase") or 1)})', '            Theme.animate(scale, plan.popSeconds, {Scale = (object:GetAttribute("UIScaleBase") or 1)})'),
    'the pop forgets the button base scale': (THEME, '            Theme.animate(scale, plan.popSeconds, {Scale = plan.pop * (object:GetAttribute("UIScaleBase") or 1)})', '            Theme.animate(scale, plan.popSeconds, {Scale = plan.pop})'),
    'the button stays at 103%': (THEME, '                if popSerial == serial and not pressed and object.Parent then', '                if false then'),
    'a stale settle fires over a new press': (THEME, '                if popSerial == serial and not pressed and object.Parent then', '                if object.Parent then'),
    'the button stays down when the finger leaves': (THEME, '        object.MouseLeave:Connect(function() hovered=false pressed=false animate(1) if presets then pressLost() end end)', '        object.MouseLeave:Connect(function() hovered=false pressed=false animate(1) end)'),
    'Reduce Motion makes a sink object anyway': (THEME, '                if pixels == 0 then return end\n', ''),
    'a release without a press pops': (THEME, 'if presets and wasPressed then pressUp(rest) else animate(rest) end', 'if presets then pressUp(rest) else animate(rest) end'),
    'flag off: the press no longer shrinks': (THEME, 'if presets then pressDown() else animate(.96) end', 'if presets then pressDown() else animate(1) end'),
    'the window pops again when a screen changes': (BOOT, 'if Config.MotionPresetsEnabled and not wasVisible then require(script.Parent.MotionFx).open(', 'if Config.MotionPresetsEnabled then require(script.Parent.MotionFx).open('),
    'Bootstrap requires MotionFx with the flag off (open)': (BOOT, 'if Config.MotionPresetsEnabled and not wasVisible then require(script.Parent.MotionFx).open(', 'if not wasVisible then require(script.Parent.MotionFx).open('),
    'Bootstrap requires MotionFx with the flag off (close)': (BOOT, 'local hide=if Config.MotionPresetsEnabled then require(script.Parent.MotionFx).close(scale,shade,panel) else .13', 'local hide=if true then require(script.Parent.MotionFx).close(scale,shade,panel) else .13'),
    'flag off: the window is hidden later than before': (BOOT, 'require(script.Parent.MotionFx).close(scale,shade,panel) else .13', 'require(script.Parent.MotionFx).close(scale,shade,panel) else .16'),
    'the close ignores the hide time': (BOOT, '    task.delay(if motion then hide else 0,function()', '    task.delay(if motion then .13 else 0,function()'),
    'the open uses a plain tween (no overshoot)': (FX, "    Theme.animate(scale, plan.seconds, {Scale = target * plan.to}, Enum.EasingStyle.Back)", "    Theme.animate(scale, plan.seconds, {Scale = target * plan.to})"),
    'the open does not start small': (FX, '    scale.Scale = target * plan.from\n', ''),
    'the open ignores the window size': (FX, '    scale.Scale = target * plan.from\n', '    scale.Scale = plan.from\n'),
    'Reduce Motion: the open still shrinks the window first': (FX, '    if plan.seconds <= 0 then return end -- Reduce Motion: Bootstrap\'s own call already put the window at its end state\n', ''),
    'Reduce Motion: the close still tweens': (FX, '    if plan.seconds <= 0 then return plan.hideAfter end -- Reduce Motion: Bootstrap\'s own calls already set the end state\n', ''),
    'the close keeps the old 0.12 s': (FX, '    Theme.animate(shade, plan.seconds, {BackgroundTransparency = 1})', '    Theme.animate(shade, .12, {BackgroundTransparency = 1})'),
    'the close hides the window at once': (FX, '    Theme.animate(panel, plan.seconds, {Position = ModalCompact.home(.52)})\n    return plan.hideAfter', '    Theme.animate(panel, plan.seconds, {Position = ModalCompact.home(.52)})\n    return 0'),
    'MotionFx ignores Reduce Motion': (FX, '    local plan = UIMotion.windowOpen(not Theme.MotionEnabled)', '    local plan = UIMotion.windowOpen(false)'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    ok, out = check(args.runner)
    print(out, end='')
    if not ok:
        raise SystemExit('UI motion presets check failed')
    print('UI motion presets wiring passed: flag off in Config and the default profile, on in the playtest profile, in the rehearsal list; no server file')
    if args.no_mutants:
        return
    from concurrent.futures import ThreadPoolExecutor
    names = list(MUTANTS)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: check(args.runner, MUTANTS[n]), names))
    survived = [name for name, (passed, _out) in zip(names, results) if passed]
    assert not survived, 'MUTANT SURVIVED (the UI motion check did not notice): ' + '; '.join(survived)
    for name in names:
        print('  mutant caught: ' + name)
    print('UI motion presets passed: %d mutants caught' % len(MUTANTS))


if __name__ == '__main__':
    sys.exit(main())
