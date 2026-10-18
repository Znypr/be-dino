#!/usr/bin/env python3
"""BD-1130 (docs/205 pictures 434, 435, 440): the playtest "Tell us!" button and the Admin button never cover Explore, HOME or a menu.

Studio round 8 at 516 x 481: both buttons lay over the green Explore button at home, over HOME in a run (HOME was hidden but for its right edge, and a first
click on it did nothing once) and over the bottom of the Fusion menu. Two causes, both found with the real code:

1. LAYOUT: Tell us! (120 px) and Admin (120 px) sit side by side in the bottom-left corner, 256 px in all; Home starts at x 222 in a 516 px window (any window
   under about 620 px wide). TouchLayout now shrinks Admin to fit before Home (at least 72 px: still a 44 px target), and stacks it above Tell us! when even
   that does not fit; the "Back to the middle" chip rises above them. A window under about 520 px wide with the desktop layout centres the Studio build badge
   over Admin's old top-left spot: Admin then takes the first free spot beside / above Tell us!.
2. HIDING: both buttons are meant to hide while a menu is open, but the Fusion menu is a ScreenGui of its own (BeDinoFusionUI) that is created the first time it
   opens, and the old code looked it up once at start-up (a 30 s WaitForChild that timed out, and held the scrim hook back with it). MenuWatch hooks
   PlayerGui.ChildAdded instead; PlaytestFeedback.showButton hides Tell us! for the Fusion menu at every size.

This check runs the REAL TouchLayout, PhoneScale, Config, PlaytestFeedback and MenuWatch in the pinned Luau runtime:
 * 20 widths (440 to 1920) x 16 heights x mouse and touch x with and without the hub Goals header (and the objectives pill): Tell us! and Admin are on the
   canvas, 44 px or more, and touch no other piece (egg plate, wallet, goal line, Goals header, objectives pill, weather, LEAP, Home / Explore, every rail
   button, the build badge, the "Back to the middle" chip, the SIZE bar) and not each other. Windows under 440 px wide are out of scope (the whole layout is
   a last resort there); the mock reports how many canvases were checked.
 * the old spot is kept where it was already clear (800 x 360 phone: Admin at x 136, 120 px; a wide desktop: Admin at 14, 8);
 * MenuWatch in a mock PlayerGui: a Fusion menu that appears later is seen, a scrim menu is seen, another ScreenGui is ignored, every change calls back;
 * PlaytestFeedback.showButton: the Fusion menu hides Tell us! at every size, the older rules are unchanged;
 * the source: both scripts use MenuWatch, nobody waits for BeDinoFusionUI once, Bootstrap is untouched.
The mutants put each defect back and the checks must fail. NOT Studio evidence: nobody saw a pixel (the Studio re-check is a new row).
Usage: python tools/verify_hud_clearance.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def wrapped(path, replacements=()):
    text = read(path)
    for old, new in replacements:
        assert old in text, 'mutant target missing in %s: %s' % (path, old)
        text = text.replace(old, new)
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local script = {Parent = {Config = "Config", PhoneScale = "PhoneScale"}}
local require = function(name) if name == "PhoneScale" then return PhoneScale end return Config end
local function rect(e) return TouchLayout.rendered(e) end

-- every piece of the HUD that a tester button must not touch (the same list the movement check uses, plus the in-run SIZE bar and its hint)
local function pieces(l)
    local list = {}
    local t = l.timers
    local function child(name, y, h) list[#list + 1] = {name = name, r = {x = t.x, y = t.y + y * t.scale, w = t.w * t.scale, h = h * t.scale}} end
    child("leap", t.leapY, TouchLayout.LEAP_H)
    if t.weatherVisible then child("weather", t.weatherY, TouchLayout.WEATHER_H) end
    if t.buffsVisible then child("buffs", t.buffsY, t.buffsH) end
    list[#list + 1] = {name = "hud", r = rect(l.hud)}
    list[#list + 1] = {name = "crystal", r = rect(l.crystal)}
    list[#list + 1] = {name = "goalline", r = {x = l.crystal.x, y = l.crystal.y + l.crystal.h * l.crystal.scale + TouchLayout.GOAL_GAP, w = l.crystal.w * l.crystal.scale, h = TouchLayout.GOAL_H * l.crystal.scale}}
    list[#list + 1] = {name = "action", r = rect(l.action)}
    list[#list + 1] = {name = "badge", r = rect(l.badge)}
    list[#list + 1] = {name = "notice", r = rect(l.notice)}
    if l.goals then list[#list + 1] = {name = "goals", r = l.goals} end
    if l.objectives then list[#list + 1] = {name = "objectives", r = l.objectives} end
    if l.goalsPanel then list[#list + 1] = {name = "goalspanel", r = l.goalsPanel} end
    list[#list + 1] = {name = "chip", r = l.chip}
    if not l.goals and not l.objectives then
        list[#list + 1] = {name = "sizebar", r = rect(l.sizeBar)}
        list[#list + 1] = {name = "sizehint", r = rect(l.sizeHint)}
    end
    for i, p in l.rail.positions do
        list[#list + 1] = {name = "nav" .. i, r = {x = l.rail.x + p.x * l.rail.scale, y = l.rail.y + p.y * l.rail.scale, w = l.rail.button.w * l.rail.scale, h = l.rail.button.h * l.rail.scale}}
    end
    return list
end

local widths = {440, 460, 480, 500, 516, 560, 600, 640, 667, 700, 740, 800, 844, 848, 915, 1024, 1156, 1280, 1445, 1920}
local heights = {339, 354, 375, 390, 400, 423, 445, 465, 481, 500, 560, 600, 720, 793, 841, 1080}
local checked, stacked, shrunk, beside = 0, 0, 0, 0
for _, w in widths do
    for _, h in heights do
        for _, touch in {true, false} do
            for _, mode in {"run", "hub", "hub+objectives"} do
                local l = TouchLayout.compute({width = w, height = h, touch = touch, navCount = 6, goals = mode ~= "run", objectives = mode == "hub+objectives"})
                local label = string.format("%dx%d %s %s", w, h, if l.touch then "phone layout" else "desktop layout", mode)
                local fb, ad = l.feedback, l.admin
                for _, pair in {{"Tell us!", fb}, {"Admin", ad}} do
                    local name, r = pair[1], pair[2]
                    assert(r.x >= 0 and r.y >= 0 and r.x + r.w <= w + 1e-6 and r.y + r.h <= h + 1e-6, label .. ": " .. name .. " leaves the canvas")
                    assert(r.w >= Config.TouchMinTargetPx and r.h >= Config.TouchMinTargetPx, label .. ": " .. name .. " is under 44 px")
                    for _, p in pieces(l) do
                        assert(not TouchLayout.overlaps(r, p.r), label .. ": " .. name .. " lies over " .. p.name)
                    end
                end
                assert(not TouchLayout.overlaps(fb, ad), label .. ": Tell us! and Admin touch each other")
                checked += 1
                if l.touch then
                    if ad.y < fb.y then stacked += 1 elseif ad.w < TouchLayout.ADMIN.w then shrunk += 1 else beside += 1 end
                end
            end
        end
    end
end
assert(stacked > 0 and shrunk > 0 and beside > 0, "probe lost sensitivity: stacked/shrunk/beside = " .. stacked .. "/" .. shrunk .. "/" .. beside)

-- the owner's picture: 516 x 481 (a short window: the phone layout, mouse or touch). Admin is the narrow one, beside Tell us!, ending before Home.
for _, touch in {true, false} do
    local l = TouchLayout.compute({width = 516, height = 481, touch = touch, navCount = 6, goals = true})
    local home = rect(l.action)
    assert(l.touch and l.admin.x + l.admin.w <= home.x - 4 and l.admin.w >= 72 and l.admin.w < 120 and l.admin.y == l.feedback.y, "516 x 481: Admin shrinks to fit before Home")
    assert(l.feedback.x + l.feedback.w <= l.admin.x, "516 x 481: Tell us! first, then Admin")
end
-- where the old spot was already clear nothing moved
do
    local phone = TouchLayout.compute({width = 800, height = 360, touch = true, navCount = 6})
    assert(phone.admin.x == phone.feedback.x + phone.feedback.w + 8 and phone.admin.w == 120 and phone.admin.y == phone.feedback.y, "800 x 360 phone: Admin keeps its old spot and size")
    for _, v in {{1156, 841}, {1280, 720}, {1920, 1080}, {1024, 768}} do
        local d = TouchLayout.compute({width = v[1], height = v[2], touch = false, navCount = 6})
        assert(d.admin.x == 14 and d.admin.y == 8 and d.admin.w == 120 and d.admin.h == 48, "desktop " .. v[1] .. ": Admin keeps its top-left spot")
    end
    local narrow = TouchLayout.compute({width = 516, height = 600, touch = false, navCount = 6})
    assert(not narrow.touch and not (narrow.admin.x == 14 and narrow.admin.y == 8), "516 x 600 desktop layout: the build badge sits over the old Admin spot, so Admin moved")
end

-- ---- PlaytestFeedback.showButton: the Fusion menu hides Tell us! at every size; the older rules are unchanged
local F = PlaytestFeedback
local base = {sawRunEnd = true, runActive = false}
local function info(extra) local i = {} for k, v in base do i[k] = v end for k, v in extra do i[k] = v end return i end
assert(F.showButton(info({})) == true)
assert(F.showButton(info({fusionOpen = true, compact = true})) == false and F.showButton(info({fusionOpen = true, compact = false})) == false, "the Fusion menu hides Tell us! at every size")
assert(F.showButton(info({fusionOpen = false})) == true and F.showButton(info({fusionOpen = nil})) == true)
assert(F.showButton(info({menuOpen = true, compact = true})) == false and F.showButton(info({menuOpen = true, compact = false})) == true, "the older menu rule is unchanged")

-- ---- MenuWatch in a mock PlayerGui
local function signal()
    local s = {fns = {}}
    function s.Connect(self, fn) self.fns[#self.fns + 1] = fn return {Disconnect = function() end} end
    function s.Fire(self, ...) for _, fn in table.clone(self.fns) do fn(...) end end
    return s
end
local function new(name, class)
    local o = {Name = name, ClassName = class, Children = {}, sig = {}, ChildAdded = signal()}
    local data = {}
    setmetatable(o, {
        __index = function(t, k)
            if k == "IsA" then return function(self, c) return c == self.ClassName or (c == "GuiObject" and self.ClassName ~= "ScreenGui" and self.ClassName ~= "PlayerGui") end end
            if k == "GetPropertyChangedSignal" then return function(self, prop) self.sig[prop] = self.sig[prop] or signal() return self.sig[prop] end end
            if k == "GetChildren" then return function(self) return table.clone(self.Children) end end
            if k == "WaitForChild" or k == "FindFirstChild" then return function(self, n) for _, c in self.Children do if c.Name == n then return c end end return nil end end
            return data[k]
        end,
        __newindex = function(t, k, v)
            data[k] = v
            if (k == "Visible" or k == "Enabled") and t.sig[k] then t.sig[k]:Fire() end
        end,
    })
    return o
end
local function add(parent, child) parent.Children[#parent.Children + 1] = child parent.ChildAdded:Fire(child) return child end

local gui = new("PlayerGui", "PlayerGui")
local calls = 0
local watch = MenuWatch.watch(gui, function() calls += 1 end)
assert(not watch.scrimOpen() and not watch.fusionOpen() and not watch.anyOpen(), "nothing yet: nothing open")
local ui = new("BeDinoUI", "ScreenGui")
local scrim = new("ModalScrim", "TextButton") scrim.Visible = false
ui.Children[1] = scrim
add(gui, ui)
assert(not watch.anyOpen())
local before = calls
scrim.Visible = true
assert(watch.scrimOpen() and watch.anyOpen() and not watch.fusionOpen() and calls > before, "a scrim menu opens")
scrim.Visible = false
assert(not watch.anyOpen())
-- the Fusion menu is made later, the first time it opens (BD-1130): it must still be seen
local other = new("SomeOtherGui", "ScreenGui") other.Enabled = true -- an enabled gui that is not a menu
add(gui, other)
assert(not watch.fusionOpen(), "another ScreenGui is not the Fusion menu")
local fusion = new("BeDinoFusionUI", "ScreenGui") fusion.Enabled = false
add(gui, fusion)
before = calls
assert(not watch.fusionOpen() and not watch.anyOpen(), "the Fusion gui exists but is closed")
fusion.Enabled = true
assert(watch.fusionOpen() and watch.anyOpen() and not watch.scrimOpen() and calls > before, "the Fusion menu opens: seen although its gui was made after start-up")
fusion.Enabled = false
assert(not watch.anyOpen())
-- a Fusion gui that was there before the watch started
local gui2 = new("PlayerGui", "PlayerGui")
local early = new("BeDinoFusionUI", "ScreenGui") early.Enabled = true gui2.Children[1] = early
local w2 = MenuWatch.watch(gui2, function() end)
assert(w2.fusionOpen() and w2.anyOpen(), "a Fusion gui that already exists is seen")

print(string.format("hud clearance passed: %d canvases (stacked %d, shrunk %d, beside %d), Admin and Tell us! clear of every piece; MenuWatch sees the Fusion menu made later", checked, stacked, shrunk, beside))
'''


def script(replacements=None):
    replacements = replacements or {}
    return ('local Config = ' + wrapped('src/shared/Config.luau', replacements.get('Config', ())) + '\n'
            + 'local PhoneScale = ' + wrapped('src/shared/PhoneScale.luau') + '\n'
            + 'local TouchLayout = (function()\nlocal script = {Parent = {Config = "Config", PhoneScale = "PhoneScale"}}\n'
            + 'local require = function(name) if name == "PhoneScale" then return PhoneScale end return Config end\n'
            + 'return ' + wrapped('src/shared/TouchLayout.luau', replacements.get('TouchLayout', ())) + '\nend)()\n'
            + 'local PlaytestFeedback = ' + wrapped('src/shared/PlaytestFeedback.luau', replacements.get('PlaytestFeedback', ())) + '\n'
            + 'local task = {spawn = function(fn, ...) fn(...) end}\n'
            + 'local MenuWatch = ' + wrapped('src/client/MenuWatch.luau', replacements.get('MenuWatch', ())) + '\n'
            + LUAU)


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify_hud_clearance.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


TL = 'TouchLayout'
MUTANTS = {
    'Admin stays 120 px wide beside Tell us! (it covers Explore / HOME again)': {
        TL: [('    if room >= A.w then return {x = x, y = feedback.y, w = A.w, h = A.h} end\n', '    if true then return {x = x, y = feedback.y, w = A.w, h = A.h} end\n')]},
    'Admin may shrink below a 44 px target': {TL: [('desktopY = 8, minW = 72}', 'desktopY = 8, minW = 20}')]},
    'Admin never stacks: it only shrinks (a narrow window covers Home)': {
        TL: [('    if room >= A.minW then return {x = x, y = feedback.y, w = math.floor(room), h = A.h} end\n    return {x = feedback.x, y = feedback.y - gap - A.h, w = A.w, h = A.h}\n', '    return {x = x, y = feedback.y, w = math.max(A.minW, math.floor(room)), h = A.h}\n')]},
    'the chip does not rise above a stacked Admin': {TL: [('y = math.min(y, b.y - C.gap - C.h)', 'y = y')]},
    'the desktop Admin has no second spot (the build badge covers it in a narrow window)': {
        TL: [('local candidates: {Rect} = {default, {x = fb.x + fb.w + gap, y = fb.y, w = A.w, h = A.h}, {x = fb.x, y = fb.y - gap - A.h, w = A.w, h = A.h}}', 'local candidates: {Rect} = {default}')]},
    'the Fusion menu does not hide Tell us!': {'PlaytestFeedback': [('    if info.fusionOpen == true then return false end', '')]},
    'MenuWatch misses a ScreenGui made after start-up': {'MenuWatch': [('    playerGui.ChildAdded:Connect(look)\n', '')]},
    'MenuWatch ignores the Fusion menu': {'MenuWatch': [('local function fusionOpen(): boolean return fusion ~= nil and fusion.Enabled == true end', 'local function fusionOpen(): boolean return false end')]},
    'MenuWatch never calls back when the Fusion menu opens': {'MenuWatch': [("        child:GetPropertyChangedSignal(\"Enabled\"):Connect(onChange)\n", '')]},
    'MenuWatch takes any ScreenGui for the Fusion menu': {'MenuWatch': [('child.Name ~= "BeDinoFusionUI" or not child:IsA("ScreenGui")', 'not child:IsA("ScreenGui")')]},
}


def check_sources():
    fb = read('src/client/FeedbackClient.client.luau')
    ad = read('src/client/AdminPanel.client.luau')
    for name, text in (('FeedbackClient', fb), ('AdminPanel', ad)):
        assert 'MenuWatch' in text, name + ' uses MenuWatch'
        assert 'WaitForChild("BeDinoFusionUI"' not in text and 'FindFirstChild("BeDinoFusionUI")' not in text, name + ': no one-time look-up of the Fusion gui (it is made on first use)'
    assert 'fusionOpen = fusionOpen()' in fb, 'FeedbackClient passes the Fusion state to the rule'
    assert 'watch.anyOpen()' in ad, 'AdminPanel hides for any open menu'
    boot = read('src/client/Bootstrap.client.luau')
    assert 'MenuWatch' not in boot, 'Bootstrap is untouched by BD-1130 (docs/160 s10)'
    src = read('src/client/MenuWatch.luau')
    assert 'ChildAdded' in src and 'BeDinoFusionUI' in src and 'ModalScrim' in src


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_sources()
    result = run(args.runner, script())
    print(result.stdout, end='')
    if result.returncode or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            assert run(args.runner, script(replacements)).returncode != 0, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
    print('Hud clearance passed: source guards, layout sweep, MenuWatch, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
