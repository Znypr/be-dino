#!/usr/bin/env python3
"""BD-1017 (docs/180 option A): the stall message bubble. Offline proof, no Studio, no phone.

Owner request 2026-10-18: "the shop interactions should be like messages with buttons to click, like E to interact". Behind
Config.ShopPromptBubbleEnabled (false in the default profile, true in the playtest profile). This check runs the REAL pure rules in the pinned
Luau runtime:

1. WORDS: every stall that has a walk-up prompt (read from HubWalkUpRules.stations()) plus the Heart has a name and ONE warm line; the
   words pass the child-copy rules (no digits, no jargon words, short); keyboard shows the key "E" and "Open", a phone shows "Tap to open" and
   no key, a gamepad shows "X" and "Open".
2. KEYS: with the flag on the stall key is E and the gamepad button X; with the flag off (or anything but true) it is G and L1 as before.
3. FIT: at the big layout and at the small one (640 x 360 phone views and every short screen) every word fits on one line at 14 px or more,
   the whole bubble is at least 96 px wide and 44 px tall, and the rows do not overlap.
4. WHICH AND WHEN: one bubble, the nearest; nothing outside the walk-up range; hidden while a window is open (and for a moment after it
   closes), while the stall cannot open, and for a moment after a press.
5. WHERE (BD-1128, docs/205 picture 421): the bubble is a screen layer ABOVE the HUD, placed clear of every HUD rectangle (HubPromptBubbleRules.place /
   layoutFor, on the REAL TouchLayout rectangles at 20 widths x 16 heights x mouse and touch x run / hub / hub with objectives): on the screen, no hard HUD piece
   covered (rail, weather column, Home, egg plate, Crystals block, Tell us!, Admin), the small bubble tried when the big one has no room; the few tight windows
   are listed, not hidden.
   BD-1132 (docs/205 picture 447): the soft weather title line (WeatherTitleSlot) slides clear of the same HUD pieces at the same window sizes.
6. CLIENT SMOKE (tools/shop_prompt_bubble_smoke.luau): the REAL src/client/HubPromptBubble.luau runs against a tiny mock Roblox: what it builds (name,
   line, key cap, "Open"), one bubble at a time, the key press (sunk, nearest prompt, one soft click, hidden for a moment), a tap on the bubble,
   hidden while a window is open (the key still works), hidden when the stall cannot open, phone / gamepad / short-screen versions, Reduce Motion;
   BD-1128: a screen layer above the HUD (DisplayOrder 10, no billboard), centred on the projected stall point, clear of the HUD rectangles, offset by the
   layer origin, back on the screen when the stall is off to the side, hidden behind the camera, glides (jumps with Reduce Motion), one per-frame update only
   while it shows.
7. SOURCE GUARDS: nothing opens by walking near (no Heartbeat / padAt / Touched in the client files, one InputHoldBegin, from a tap or the key),
   the old round button stays for the flag-off path, the Heart prompt is flag-gated, Bootstrap is untouched, the flag is pinned in every profile.
8. MUTANTS: the checks must FAIL when a rule is broken (window ignored, no return delay, farthest wins, range ignored, phone shows a key, flag
   key stays G, always the big layout, long or numbered copy, no hide after a press, fit check always true).

Not Studio evidence: nobody saw the bubble, pressed E or tapped it on a phone here. Usage: python tools/verify_shop_prompt_bubble.py --runner luau.exe
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
    text = (ROOT / path).read_text(encoding='utf-8')
    for old, new in replacements:
        assert old in text, 'mutant target missing in %s: %s' % (path, old)
        text = text.replace(old, new)
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local R, Walk, Copy = HubPromptBubbleRules, HubWalkUpRules, HubSignCopy
local function close(a, b) return math.abs(a - b) < 1e-9 end

-- ---- 1. words for every stall that has a prompt, and the Heart
local ids = R.stations()
local want = {}
for _, s in Walk.stations() do want[#want + 1] = s.id end
want[#want + 1] = "heart"
assert(table.concat(ids, ",") == table.concat(want, ","), "the bubble covers every walk-up stall and the Heart: " .. table.concat(ids, ","))
assert(#ids == 6, "five menu stalls and the Heart")
local seenLines = {}
for _, id in ids do
    local title, line = Copy.bubbleTitle(id), Copy.bubbleLine(id)
    assert(title and line, id .. " has a name and a line")
    assert(#title <= Copy.BubbleTitleMax and #line <= Copy.BubbleLineMax and #title >= 2 and #line >= 8, id .. " words are short")
    assert(Copy.acceptable(title) and Copy.acceptable(line), id .. " passes the child-copy rules (no digits, no jargon)")
    assert(not line:find("[%[%]<>{}|_\\]"), id .. " has no technical punctuation")
    assert(line:sub(-1) == "!", id .. " is a warm line")
    assert(not seenLines[line], id .. " has its own line")
    seenLines[line] = true
    -- BD-1129: a stall opens a window ("Open"); the Heart shows your dino off ("Show off"), it never says Open (docs/205 picture 432)
    local go, goTouch = if id == "heart" then "Show off" else "Open", if id == "heart" then "Tap to show off" else "Tap to open"
    local k = R.words(id, "Keyboard", "E", "E")
    assert(k and k.title == title and k.line == line and k.keyLabel == "E" and k.buttonText == go, id .. " keyboard words")
    local t = R.words(id, "Touch", "E", "E")
    assert(t and t.keyLabel == nil and t.buttonText == goTouch, id .. " phone words: no key, tap to " .. goTouch)
    local g = R.words(id, "Gamepad", "ButtonX", "E")
    assert(g and g.keyLabel == "X" and g.buttonText == go, id .. " gamepad words: the X button")
end
for _, bad in {"settings", "gate", "fame", "", 5, false} do
    assert(R.words(bad, "Keyboard", "E", "E") == nil, "no bubble for " .. tostring(bad))
end
assert(Copy.bubbleLine(nil) == nil and Copy.bubbleTitle({}) == nil)
-- input kind
assert(R.inputKind("Touch") == "Touch" and R.inputKind("Gamepad") == "Gamepad" and R.inputKind("Gamepad1") == "Gamepad" and R.inputKind("Gamepad4") == "Gamepad")
assert(R.inputKind("Keyboard") == "Keyboard" and R.inputKind("MouseMovement") == "Keyboard" and R.inputKind("MouseButton1") == "Keyboard")
assert(R.inputKind(nil) == "Keyboard" and R.inputKind(5) == "Keyboard" and R.inputKind("") == "Keyboard", "unknown counts as a keyboard")
-- key label
assert(R.keyLabel("Keyboard", "E", "e") == "E" and R.keyLabel("Keyboard", "E", nil) == "E" and R.keyLabel("Keyboard", "E", "") == "E")
assert(R.keyLabel("Keyboard", "E", "ButtonX") == "E", "a long engine label is ignored")
assert(R.keyLabel("Keyboard", nil, nil) == "E", "default key")
assert(R.keyLabel("Gamepad", "ButtonX", nil) == "X" and R.keyLabel("Gamepad", "ButtonA", nil) == "A" and R.keyLabel("Gamepad", "ButtonL1", nil) == "L1" and R.keyLabel("Gamepad", "Nonsense", nil) == "X")
assert(R.keyLabel("Touch", "E", "E") == nil)

-- ---- 2. keys
assert(Walk.keyFor(true) == "E" and Walk.gamepadFor(true) == "ButtonX", "flag on: E and X")
for _, off in {false, nil, 1, "true", {}} do
    assert(Walk.keyFor(off) == "G" and Walk.gamepadFor(off) == "ButtonL1", "flag off or junk: G and L1")
end
assert(Walk.PromptKey == "G", "the flag-off key constant is unchanged")

-- ---- 3. fit
local function layoutOk(l, where)
    assert(l.w >= 96 and l.h >= 44, where .. " whole bubble is a big target")
    assert(l.titleSize >= 14 and l.lineSize >= 14 and l.buttonSize >= 14, where .. " text at least 14 px")
    assert(l.buttonH >= 40, where .. " button height")
    assert(l.titleY >= 0 and l.titleY + l.titleH <= l.lineY and l.lineY + l.lineH <= l.buttonY and l.buttonY + l.buttonH <= l.h, where .. " rows do not overlap and stay inside")
    assert(l.innerW == l.w - 2 * l.pad, where .. " inner width")
end
local big, small = R.layout(900), R.layout(300)
layoutOk(big, "big") layoutOk(small, "small")
assert(big.small == false and small.small == true)
for _, h in {1080, 841, 793, 500, 480} do assert(R.layout(h).small == false, "tall screen " .. h) end
for _, h in {479, 465, 400, 390, 375, 360, 354, 339} do assert(R.layout(h).small == true, "short screen " .. h) end
assert(R.layout(nil).small == false and R.layout(0 / 0).small == false and R.layout("x").small == false, "unknown height gets the big one")
for _, id in ids do for _, kind in {"Keyboard", "Touch", "Gamepad"} do
    assert(R.fits(id, kind, big), id .. " " .. kind .. " fits big")
    assert(R.fits(id, kind, small), id .. " " .. kind .. " fits small (a 640 x 360 phone view)")
end end
local tiny = {w = 100, h = 60, pad = 8, titleSize = 20, lineSize = 16, buttonSize = 20, innerW = 60}
assert(R.fits("nests", "Keyboard", tiny) == false, "a bubble too narrow for the words does not fit")
assert(R.fits("nests", "Keyboard", {w = 248, h = 116, pad = 10, titleSize = 12, lineSize = 12, buttonSize = 12, innerW = 228}) == false, "text under 14 px never passes")
assert(R.fits("settings", "Keyboard", big) == false and R.fits("nests", "Keyboard", nil) == false)
assert(R.textWidth("abc", 10) > 0 and R.textWidth(5, 10) == math.huge and R.textWidth("a", 0 / 0) == math.huge)

-- ---- 4. which bubble, and when
local function cand(id, d, range) return {id = id, distance = d, range = range} end
assert(R.nearest({cand("a", 8), cand("b", 3), cand("c", 5)}) == "b", "the nearest wins")
assert(R.nearest({cand("a", 3), cand("b", 3)}) == "a", "a tie goes to the first")
assert(R.nearest({cand("a", 20)}) == nil, "outside the range: no bubble")
assert(R.nearest({cand("a", 10), cand("b", 12.9)}) == "a" and R.nearest({cand("b", 12.9)}) == "b" and R.nearest({cand("b", 13.1)}) == nil, "range 10 plus the small slack")
assert(R.nearest({cand("heart", 12.5, 9)}) == nil and R.nearest({cand("heart", 8, 9)}) == "heart", "each prompt keeps its own range")
assert(R.nearest({cand("far", 9), cand("near", 2, 30)}) == "near")
assert(R.nearest({}) == nil and R.nearest(nil) == nil and R.nearest({5, "x", {}, {id = 1, distance = 2}, {id = "n", distance = 0 / 0}, {id = "n", distance = -1}}) == nil, "junk is skipped")
local function input(over)
    local i = {candidates = {cand("nests", 4)}, canShow = true, windowOpen = false}
    for k, v in over or {} do i[k] = v end
    return i
end
local s = R.newState()
assert(R.step(s, input(), 100) == "nests", "in range, at home, nothing open: the bubble shows")
assert(R.step(s, input({windowOpen = true}), 101) == nil, "a window is open: hidden (no tap can fall through)")
assert(R.step(s, input({windowOpen = true}), 103) == nil)
assert(R.step(s, input(), 103.1) == nil, "the window just closed: still hidden")
assert(R.step(s, input(), 103.25) == nil)
assert(R.step(s, input(), 103.4) == "nests", "it returns after the short delay")
assert(R.step(s, input({canShow = false}), 110) == nil, "the stall cannot open now (in a run, trip, loading): no dead button")
assert(R.step(s, input({canShow = "yes"}), 110.1) == nil)
assert(R.step(s, input({candidates = {}}), 111) == nil, "walked away: gone")
assert(R.step(s, input({candidates = {cand("nests", 40)}}), 112) == nil, "too far: gone")
assert(R.step(s, input(), 120) == "nests")
R.pressed(s, 120.05)
assert(R.step(s, input(), 120.1) == nil and R.step(s, input(), 120.3) == nil, "right after a press the bubble is hidden")
assert(R.step(s, input(), 120.4) == "nests", "a blocked press: it comes back")
assert(R.step(R.newState(), input({candidates = {cand("potions", 9), cand("nests", 5)}}), 1) == "nests", "one bubble at a time: the nearest")
assert(R.step(R.newState(), nil, 1) == nil and R.step(R.newState(), 5, 1) == nil)
-- a window that opens and closes again quickly keeps the delay each time
local s2 = R.newState()
assert(R.step(s2, input({windowOpen = true}), 1) == nil and R.step(s2, input(), 1.1) == nil and R.step(s2, input({windowOpen = true}), 1.2) == nil)
assert(R.step(s2, input(), 1.3) == nil and R.step(s2, input(), 1.7) == "nests")

-- ---- 5. where on the screen (BD-1128)
local function ov(a, b) return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h end
local function boxOf(p, size) return {x = p.x, y = p.y, w = size.w, h = size.h} end
local size = {w = 248, h = 116}
-- no HUD: centred on the point; slid onto the screen when the point is near or past an edge
local p0 = R.place({w = 1000, h = 700, point = {x = 500, y = 350}, size = size, blockers = {}})
assert(p0.clear and p0.x == 376 and p0.y == 292, "centred on the point")
local pe = R.place({w = 1000, h = 700, point = {x = -300, y = 900}, size = size, blockers = {}})
assert(pe.x == R.Edge and pe.y == 700 - R.Edge - 116, "slid onto the screen: " .. pe.x .. ", " .. pe.y)
-- a HUD rectangle where the bubble would be: the bubble goes to the nearest free spot, a gap away
local rail = {x = 380, y = 240, w = 300, h = 120}
local pr = R.place({w = 1000, h = 700, point = {x = 540, y = 315}, size = size, blockers = {rail}})
assert(pr.clear and not ov(boxOf(pr, size), {x = rail.x - R.Gap, y = rail.y - R.Gap, w = rail.w + 2 * R.Gap, h = rail.h + 2 * R.Gap}), "off the rail with a gap")
local pr2 = R.place({w = 1000, h = 700, point = {x = 540, y = 315}, size = size, blockers = {{x = 0, y = 0, w = 1000, h = 250}}})
assert(pr2.clear and pr2.y >= 256, "below a wide block")
-- the nearest free spot, not a far one
local pn = R.place({w = 1000, h = 700, point = {x = 540, y = 315}, size = size, blockers = {rail}})
assert(math.abs(pn.y - 366) < 1e-6 or math.abs(pn.y - 118) < 1e-6 or math.abs(pn.x - 126) < 1e-6 or math.abs(pn.x - 686) < 1e-6, "a spot beside the rail")
local pfar = R.place({w = 1000, h = 700, point = {x = 540, y = 315}, size = size, blockers = {rail}})
assert((pfar.x - 416) ^ 2 + (pfar.y - 257) ^ 2 <= 110 ^ 2 + 1, "the nearest free spot (109 px away), not the farthest")
-- soft pieces: avoided while a spot exists that also clears the hard ones; covered rather than a hard piece
local softBox = {x = 380, y = 240, w = 300, h = 120}
local ps = R.place({w = 1000, h = 700, point = {x = 540, y = 315}, size = size, blockers = {}, soft = {softBox}})
assert(ps.clear and not ps.softCovered and not ov(boxOf(ps, size), softBox), "a soft piece is avoided when there is room")
local wall = {x = 0, y = 0, w = 1000, h = 700}
local pw = R.place({w = 1000, h = 700, point = {x = 500, y = 350}, size = size, blockers = {}, soft = {wall}})
assert(pw.clear and pw.softCovered, "only soft pieces left: covering a soft piece counts as clear")
local ph = R.place({w = 1000, h = 700, point = {x = 500, y = 350}, size = size, blockers = {wall}, soft = {}})
assert(not ph.clear, "no free spot at all: not clear")
-- junk is survived
for _, junk in {{}, {w = 0 / 0}, {w = 100, h = 100, point = "x", size = 5, blockers = "x"}, {w = 1000, h = 700, size = size, blockers = {5, "x", {x = 1}, {x = 0, y = 0, w = -4, h = 5}}}} do
    local r = R.place(junk)
    assert(r.x == r.x and r.y == r.y, "no NaN from junk")
end
assert(R.place(nil).x == R.place(nil).x)
-- layoutFor: the small bubble when the big one has no room; the big one when it has
local tallWall = {x = 0, y = 0, w = 1000, h = 590}
local lf, lfClear = R.layoutFor(1000, 700, {tallWall}, {})
assert(lf.small == true and lfClear == true, "110 px of room: the small bubble (100 px) fits, the big one (116 px) does not")
local lf2, clear2 = R.layoutFor(1000, 700, {}, {})
assert(lf2.small == false and clear2 == true, "room: the big bubble")
local lf3, clear3 = R.layoutFor(1000, 700, {{x = 0, y = 0, w = 1000, h = 640}}, {})
assert(lf3.small == true and clear3 == false, "no room even for the small one")
assert(select(1, R.layoutFor(1000, 400, {}, {})).small == true, "a short screen keeps the small bubble")
assert(select(1, R.layoutFor(nil, nil, nil, nil)) ~= nil and select(2, R.layoutFor(0, 0, {}, {})) == true, "unknown canvas: still a layout")
-- rectOf: a Roblox Rect or a table with Min and Max; junk is nil
local rr = R.rectOf({Min = {X = 10, Y = 20}, Max = {X = 110, Y = 60}})
assert(rr and rr.x == 10 and rr.y == 20 and rr.w == 100 and rr.h == 40)
assert(R.rectOf(nil) == nil and R.rectOf(5) == nil and R.rectOf({}) == nil and R.rectOf({Min = {X = 5, Y = 5}, Max = {X = 5, Y = 9}}) == nil and R.rectOf({Min = {X = 0 / 0, Y = 0}, Max = {X = 5, Y = 9}}) == nil)
-- follow: Reduce Motion jumps; motion eases and never overshoots
local jumped = R.follow({x = 0, y = 0}, {x = 100, y = 50}, 1 / 60, false)
assert(jumped.x == 100 and jumped.y == 50, "Reduce Motion: at once")
local eased = R.follow({x = 0, y = 0}, {x = 100, y = 50}, 1 / 60, true)
assert(eased.x > 0 and eased.x < 100 and eased.y > 0 and eased.y < 50, "motion: part of the way")
assert(R.follow(nil, {x = 7, y = 8}, 1 / 60, true).x == 7, "the first spot is taken at once")
assert(R.follow({x = 0, y = 0}, {x = 100, y = 0}, 100, true).x <= 100, "a long frame never overshoots")
assert(R.follow({x = 0, y = 0}, {x = 100, y = 0}, 0 / 0, true).x == 100, "a junk frame time jumps")
for _, name in R.HardRects do assert(type(name) == "string") end
local attrs = {}
for _, n in R.HardRects do attrs[n] = true end
for _, n in R.SoftRects do assert(not attrs[n], "a piece is hard or soft, not both") end
-- the attributes the bubble reads are the ones the HUD publishes: HudV2.layout publishes TouchLayout.hudRects, Bootstrap the tester buttons and the chip
local published = {RailRect = true, FeedbackRect = true, AdminRect = true, ChipRect = true}
for name in TouchLayout.hudRects(TouchLayout.compute({width = 800, height = 600, touch = false, navCount = 6})) do published[name] = true end
for _, n in R.HardRects do assert(published[n], "nobody publishes " .. n) end
for _, n in R.SoftRects do assert(published[n], "nobody publishes " .. n) end

-- the real HUD rectangles at every window size
local function rectOf(e) return TouchLayout.rendered(e) end
-- the full sweep (FAST = false) is the check; the mutant runs use a short list of the same kind of windows (500 to 1156 wide, 339 to 841 high) to stay quick
local widths = if FAST then {500, 516, 667, 848, 1156} else {440, 480, 500, 516, 600, 667, 740, 800, 848, 915, 1156, 1445, 1920}
local heights = if FAST then {339, 423, 481, 600, 841} else {339, 375, 400, 423, 465, 481, 500, 600, 793, 841, 1080}
local TIGHT = {["500x500"] = true, ["500x560"] = true, ["516x500"] = true, ["600x500"] = true} -- desktop layout + objectives pill, about 500 to 600 px wide: no free spot
local canvases, spots, softCovered, tight, tightSeen, visited = 0, 0, 0, 0, {}, {}
for _, w in widths do
    for _, h in heights do
        for _, touch in {true, false} do
            for _, mode in {"run", "hub", "hub+objectives"} do
                local l = TouchLayout.compute({width = w, height = h, touch = touch, navCount = 6, goals = mode ~= "run", objectives = mode == "hub+objectives"})
                -- what the bubble is told to avoid comes from the rule's own name lists (the attributes the HUD publishes); what must stay clear is fixed here
                local byName = {RailRect = rectOf(l.rail), TimersRect = rectOf(l.timers), ActionRect = rectOf(l.action), HudRect = rectOf(l.hud),
                    WalletBlockRect = TouchLayout.walletPlates(l), FeedbackRect = l.feedback, AdminRect = l.admin, BadgeRect = rectOf(l.badge), NoticeRect = rectOf(l.notice), ChipRect = l.chip}
                local hard, softs = {}, {}
                for _, n in R.HardRects do table.insert(hard, byName[n]) end
                for _, n in R.SoftRects do table.insert(softs, byName[n]) end
                local mustClear = {byName.RailRect, byName.TimersRect, byName.ActionRect, byName.HudRect, byName.WalletBlockRect, byName.FeedbackRect, byName.AdminRect}
                local label = string.format("%dx%d %s %s", w, h, if l.touch then "phone layout" else "desktop layout", mode)
                local layout, clear = R.layoutFor(w, h, hard, softs)
                canvases += 1
                if w >= 500 then
                    local key = w .. "x" .. h
                    visited[key] = true
                    if not clear then
                        assert(TIGHT[key] and not l.touch and mode == "hub+objectives", label .. ": no free spot for the bubble")
                        tight += 1
                        tightSeen[key] = true
                    end
                    for ix, fx in (if FAST then {-0.1, 0.5, 1.1} else {-0.1, 0, 0.3, 0.5, 0.8, 1.1}) do
                        for iy, fy in (if FAST then {-0.1, 0.5, 1.1} else {-0.1, 0, 0.3, 0.6, 1, 1.1}) do
                            -- half of the points are placed with the soft pieces, half without them (then only the hard pieces keep the bubble off Home and the rail)
                            local withSoft = (ix + iy) % 2 == 0
                            local r = R.place({w = w, h = h, point = {x = w * fx, y = h * fy}, size = {w = layout.w, h = layout.h}, blockers = hard, soft = if withSoft then softs else {}})
                            spots += 1
                            assert(r.x >= R.Edge - 1e-6 and r.y >= R.Edge - 1e-6 and r.x + layout.w <= w - R.Edge + 1e-6 and r.y + layout.h <= h - R.Edge + 1e-6, label .. ": the bubble leaves the screen")
                            if clear then
                                assert(r.clear, label .. ": free spots exist but place did not find one")
                                for _, b in mustClear do
                                    assert(not ov({x = r.x - R.Gap + 1e-6, y = r.y - R.Gap + 1e-6, w = layout.w + 2 * R.Gap - 2e-6, h = layout.h + 2 * R.Gap - 2e-6}, b), label .. ": the bubble touches a HUD piece")
                                end
                                if r.softCovered then softCovered += 1 elseif withSoft then
                                    for _, b in softs do assert(not ov(boxOf(r, layout), b), label .. ": the bubble covers a soft piece") end
                                end
                            end
                        end
                    end
                end
            end
        end
    end
end
for key in TIGHT do assert(not visited[key] or tightSeen[key], "probe lost sensitivity: " .. key .. " is no longer tight (shrink the TIGHT list)") end

-- ---- 5b. the soft weather title (BD-1132, picture 447): the box of the small line never lies over a HUD piece
local function slotCheck()
    local Slot, WL = WeatherTitleSlot, WeatherLooks
    -- pure basics
    assert(Slot.centreY({w = 1000, h = 700, boxW = 240, boxH = 24, wantY = 217, blockers = {}}) == 217, "nothing in the way: it keeps its place")
    local down = Slot.centreY({w = 1000, h = 700, boxW = 240, boxH = 24, wantY = 240, blockers = {{x = 300, y = 190, w = 400, h = 60}}})
    assert(down - 12 >= 250 + Slot.Gap and math.abs(down - 240) < 40, "slides to the nearest free place, below the block: " .. down)
    local up = Slot.centreY({w = 1000, h = 700, boxW = 240, boxH = 24, wantY = 240, blockers = {{x = 300, y = 190, w = 400, h = 60}, {x = 300, y = 250, w = 400, h = 200}}})
    assert(up < 190 - Slot.Gap, "the way down is blocked: it goes above: " .. up)
    assert(Slot.centreY({w = 1000, h = 700, boxW = 240, boxH = 24, wantY = 217, blockers = {{x = 0, y = 0, w = 1000, h = 700}}}) == 217, "no free place: the old spot")
    assert(Slot.centreY({w = 1000, h = 700, boxW = 240, boxH = 24, wantY = 217, blockers = {{x = 700, y = 0, w = 100, h = 700}}}) == 217, "a block beside the title does not matter")
    assert(Slot.centreY(nil) == 0 and Slot.centreY({wantY = 5}) == 5 and Slot.centreY({w = 1, h = 1, boxW = 1, boxH = 1, wantY = 3, blockers = {5, {x = 1}}}) == 3, "junk is survived")
    -- every window: the real HUD rectangles, offset by a top bar of 0 / 36 / 58 px (the HUD canvas starts below it, the title layer does not)
    local rects, checked, moved = 0, 0, 0
    for _, w in widths do
        for _, h in heights do
            for _, touch in {true, false} do
                for _, mode in {"run", "hub", "hub+objectives"} do
                    if w >= 500 then
                        local l = TouchLayout.compute({width = w, height = h, touch = touch, navCount = 6, goals = mode ~= "run", objectives = mode == "hub+objectives"})
                        for _, bar in {0, 36, 58} do
                            local screenH = h + bar
                            local byName = {RailRect = TouchLayout.rendered(l.rail), TimersRect = TouchLayout.rendered(l.timers), ActionRect = TouchLayout.rendered(l.action), HudRect = TouchLayout.rendered(l.hud),
                                WalletBlockRect = TouchLayout.walletPlates(l), FeedbackRect = l.feedback, AdminRect = l.admin}
                            local hard = {}
                            for _, n in R.HardRects do
                                local r = byName[n]
                                table.insert(hard, {x = r.x, y = r.y + bar, w = r.w, h = r.h})
                            end
                            local boxW, boxH = w * WL.Title.width * 0.4, screenH * WL.Title.height * 0.4
                            local want = screenH * WL.Title.y
                            local cy = Slot.centreY({w = w, h = screenH, boxW = boxW, boxH = boxH, wantY = want, blockers = hard})
                            checked += 1
                            if cy ~= want then moved += 1 end
                            local box = {x = w / 2 - boxW / 2, y = cy - boxH / 2, w = boxW, h = boxH}
                            -- the check is on a fixed list of HUD pieces (not the rule's own list)
                            local clearOfAll = true
                            for _, n in {"RailRect", "TimersRect", "ActionRect", "HudRect", "WalletBlockRect", "FeedbackRect", "AdminRect"} do
                                local r = byName[n]
                                if ov(box, {x = r.x, y = r.y + bar, w = r.w, h = r.h}) then clearOfAll = false end
                            end
                            -- the soft title only appears at home (hub); in a run the big card is used and is not moved
                            if mode ~= "run" then
                                assert(clearOfAll, string.format("%dx%d %s %s: the soft weather title lies over a HUD piece (centre %d of %d)", w, h, if touch then "touch" else "mouse", mode, cy, screenH))
                            end
                        end
                    end
                end
            end
        end
    end
    assert(moved > 0, "probe lost sensitivity: the title never had to move")
    return checked, moved
end
local titleChecked, titleMoved = slotCheck()

print("shop prompt bubble passed: words, keys, fit, which and when, where (" .. canvases .. " canvases, " .. spots .. " stall positions, " .. softCovered .. " over a soft piece, " .. tight .. " tight; soft title " .. titleMoved .. " of " .. titleChecked .. " moved)")
'''


def prefix(replacements, fast=False):
    return ('local FAST = ' + ('true' if fast else 'false') + chr(10) + 'local mods={}\n'
            + 'local script={Parent={CaveHubLayout="CaveHubLayout",HubTravelClientRules="HubTravelClientRules",HubSignCopy="HubSignCopy",HubWalkUpRules="HubWalkUpRules",Config="Config",PhoneScale="PhoneScale"}}\n'
            + 'local require=function(name) return mods[name] end\n'
            + 'local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau') + '\nmods.CaveHubLayout=CaveHubLayout\n'
            + 'local HubTravelClientRules=' + wrapped('src/shared/HubTravelClientRules.luau') + '\nmods.HubTravelClientRules=HubTravelClientRules\n'
            + 'local HubSignCopy=' + wrapped('src/shared/HubSignCopy.luau', replacements.get('HubSignCopy', ())) + '\nmods.HubSignCopy=HubSignCopy\n'
            + 'local HubWalkUpRules=' + wrapped('src/shared/HubWalkUpRules.luau', replacements.get('HubWalkUpRules', ())) + '\nmods.HubWalkUpRules=HubWalkUpRules\n'
            + 'local Config=' + wrapped('src/shared/Config.luau') + '\nmods.Config=Config\n'
            + 'local PhoneScale=' + wrapped('src/shared/PhoneScale.luau') + '\nmods.PhoneScale=PhoneScale\n'
            + 'local TouchLayout=' + wrapped('src/shared/TouchLayout.luau', replacements.get('TouchLayout', ())) + '\nmods.TouchLayout=TouchLayout\n'
            + 'local WeatherLooks=' + wrapped('src/shared/WeatherLooks.luau') + '\nmods.WeatherLooks=WeatherLooks\n'
            + 'local WeatherTitleSlot=' + wrapped('src/shared/WeatherTitleSlot.luau', replacements.get('WeatherTitleSlot', ())) + '\nmods.WeatherTitleSlot=WeatherTitleSlot\n'
            + 'local HubPromptBubbleRules=' + wrapped('src/shared/HubPromptBubbleRules.luau', replacements.get('HubPromptBubbleRules', ())) + '\n')


def script(replacements=None, fast=False):
    return prefix(replacements or {}, fast) + LUAU


def client_script(replacements=None):
    """The real client module running against a tiny mock Roblox (tools/shop_prompt_bubble_smoke.luau)."""
    replacements = replacements or {}
    source = read('src/client/HubPromptBubble.luau')
    for old, new in replacements.get('HubPromptBubble', ()):
        assert old in source, 'mutant target missing in HubPromptBubble: ' + old
        source = source.replace(old, new)
    smoke = read('tools/shop_prompt_bubble_smoke.luau')
    assert smoke.count('CLIENT_SOURCE') == 1
    return prefix(replacements) + smoke.replace('CLIENT_SOURCE', source)


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify_shop_prompt_bubble.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


RULES = 'HubPromptBubbleRules'
MUTANTS = {
    'a window open does not hide the bubble': {RULES: [('if input.windowOpen == true then', 'if false then')]},
    'no delay after a window closes': {RULES: [('    if now - state.windowClosedAt < Rules.ReturnDelay then return nil end\n', '')]},
    'the stall may be unable to open and the bubble still shows': {RULES: [('    if input.canShow ~= true then return nil end\n', '')]},
    'a press does not hide the bubble': {RULES: [('    state.pressedAt = now', '    state.pressedAt = -math.huge')]},
    'the last stall in range wins instead of the nearest': {RULES: [('and (c.distance :: number) < bestDistance then', 'then')]},
    'the range is ignored': {RULES: [('if (c.distance :: number) <= (range :: number) + Rules.RangeSlack and', 'if true and')]},
    'a phone shows a key chip': {RULES: [('    if kind == "Touch" then return nil end\n', '')]},
    'a phone says Open instead of Tap to open': {RULES: [('return if touch then "Tap to open" else "Open"', 'return "Open"')]},
    'the Heart button says Open instead of Show off (picture 432)': {RULES: [('    if station == "heart" then return if touch then "Tap to show off" else "Show off" end\n', '')]},
    'a gamepad shows no button name': {RULES: [('return if typeof(keyName) == "string" and GAMEPAD_LABELS[keyName] then GAMEPAD_LABELS[keyName] else GAMEPAD_LABELS[Walk.PromptGamepadBubble]', 'return nil')]},
    'the flag-on key stays G': {'HubWalkUpRules': [('return if bubbleOn == true then HubWalkUpRules.PromptKeyBubble else HubWalkUpRules.PromptKey', 'return HubWalkUpRules.PromptKey')]},
    'the flag-off key becomes E': {'HubWalkUpRules': [('return if bubbleOn == true then HubWalkUpRules.PromptKeyBubble else HubWalkUpRules.PromptKey', 'return HubWalkUpRules.PromptKeyBubble')]},
    'a short screen still gets the big bubble': {RULES: [('< Rules.ShortScreen then', '< -1 then')]},
    'the fit check always passes': {RULES: [('    return Rules.textWidth(words.title, layout.titleSize) <= layout.innerW\n', '    do return true end\n    return Rules.textWidth(words.title, layout.titleSize) <= layout.innerW\n')]},
    'a stall line is too long': {'HubSignCopy': [('nests = "Come and see your eggs!",\n    potions', 'nests = "Come and see all of your wonderful eggs here!",\n    potions')]},
    'a stall line has a number': {'HubSignCopy': [('potions = "Fresh potions here!"', 'potions = "Fresh potions 4 you!"')]},
    'a stall line uses a jargon word': {'HubSignCopy': [('index = "Meet all your dinos!"', 'index = "Open the menu here!"')]},
    'the Heart has no words': {'HubSignCopy': [('    heart = "Let everyone see you!",\n', '')]},
    # BD-1128: where the bubble goes
    'place ignores the HUD pieces (the bubble lies over the rail again)': {RULES: [('total += overlapArea(r, b)', 'total += 0')]},
    'place does not keep the bubble on the screen': {RULES: [('local function clampX(x: number): number return math.max(edge, math.min(maxX, x)) end', 'local function clampX(x: number): number return x end')]},
    'place takes a far free spot instead of the nearest': {RULES: [('(math.abs(touch - bestTouch) <= 1e-6 and d < bestDistance)', '(math.abs(touch - bestTouch) <= 1e-6 and d > bestDistance)')]},
    'place never gives up a soft piece (no room means no spot)': {RULES: [('    if #soft > 0 then\n        x, y, touch = search(hard)', '    if false then\n        x, y, touch = search(hard)')]},
    'place ignores the soft pieces': {RULES: [('    for _, s in soft do table.insert(all, s) end\n', '')]},
    'the small bubble is never tried when the big one has no room': {RULES: [('    if not big.small then\n        local small = Rules.layout(0)', '    if false then\n        local small = Rules.layout(0)')]},
    'follow ignores Reduce Motion': {RULES: [('if motion ~= true or typeof(current)', 'if false or typeof(current)')]},
    'rectOf takes an empty rectangle': {RULES: [('    if hi.X <= lo.X or hi.Y <= lo.Y then return nil end\n', '')]},
    'the rail is not a hard piece': {RULES: [('Rules.HardRects = {"RailRect", ', 'Rules.HardRects = {')]},
    'Home and Explore are not a hard piece': {RULES: [('"TimersRect", "ActionRect", ', '"TimersRect", ')]},
    'the weather column is not a hard piece': {RULES: [('"RailRect", "TimersRect", ', '"RailRect", ')]},
    'the Crystals block is not a hard piece': {RULES: [('"WalletBlockRect", ', '')]},
    # BD-1132: the soft weather title
    'the soft weather title never moves (it lies over the Potions button again)': {'WeatherTitleSlot': [('    if free(boxAt(want), blockers) then return want end', '    if true then return want end')]},
    'the soft weather title moves to a place that is not free': {'WeatherTitleSlot': [('if onScreen(cy) and free(boxAt(cy), blockers) and', 'if onScreen(cy) and')]},
    'the soft weather title may leave the screen': {'WeatherTitleSlot': [('if onScreen(cy) and free(boxAt(cy), blockers) and', 'if free(boxAt(cy), blockers) and')]},
}


def code_only(text):
    """Luau source without -- comments (good enough for the guards: no string in this code contains --)."""
    return '\n'.join(re.sub(r'--.*$', '', line) for line in text.split('\n'))


CLIENT = 'HubPromptBubble'
CLIENT_MUTANTS = {
    'client: the key press is not sunk (Leap would also fire)': {CLIENT: [('return Enum.ContextActionResult.Sink\n        end, false', 'return Enum.ContextActionResult.Pass\n        end, false')]},
    'client: a window being open does not hide the bubble': {CLIENT: [('windowOpen = ctx.windowOpen() == true', 'windowOpen = false')]},
    'client: a stall that cannot open still shows a bubble': {CLIENT: [('canShow = ctx.canShow() == true', 'canShow = true')]},
    'client: letting go of the key presses again': {CLIENT: [('            if inputState == Enum.UserInputState.Begin then', '            if true then')]},
    'client: the key stays bound after walking away': {CLIENT: [('if next(active) == nil then ContextActionService:UnbindAction(ACTION) end', 'local unused = 0')]},
    'client: a press does not hide the bubble': {CLIENT: [('        Rules.pressed(state, os.clock())\n', '')]},
    'client: a tap on the bubble does nothing': {CLIENT: [('        button.Activated:Connect(function()\n            press(prompt)\n        end)', '        button.Activated:Connect(function() end)')]},
    'client: a phone still shows the key chip': {CLIENT: [('if words.keyLabel then', 'if true then')]},
    'client: the bubble is a world billboard again (drawn under the HUD)': {CLIENT: [('local board = Instance.new("Frame")', 'local board = Instance.new("BillboardGui")')]},
    'client: the bubble layer is under the HUD': {CLIENT: [('local LAYER = 10', 'local LAYER = -1')]},
    'client: the bubble is not placed clear of the HUD': {CLIENT: [('                blockers = hard, soft = soft})\n            mine.pos', '                blockers = {}, soft = {}})\n            mine.pos')]},
    'client: the layer origin (the top bar) is ignored': {CLIENT: [('y = projected.Y - origin.Y}', 'y = projected.Y}')]},
    'client: the bubble shows when the stall is behind the camera': {CLIENT: [('if projected.Z <= 0 then board.Visible = false return end', 'if false then board.Visible = false return end')]},
    'client: the per-frame update keeps running after the bubble is hidden': {CLIENT: [('        if s.step then s.step:Disconnect() end\n', '')]},
    'client: Reduce Motion is ignored (it always glides)': {CLIENT: [('Rules.follow(mine.pos, spot, dt, Theme.MotionEnabled)', 'Rules.follow(mine.pos, spot, dt, true)')]},
    'client: it never glides': {CLIENT: [('Rules.follow(mine.pos, spot, dt, Theme.MotionEnabled)', 'Rules.follow(mine.pos, spot, dt, false)')]},
    'client: a prompt of a stranger gets a bubble': {CLIENT: [('if typeof(prompt:GetAttribute("BubbleStation")) ~= "string" or active[prompt] then return end', 'if active[prompt] then return end')]},
}


def check_sources():
    config = read('src/shared/Config.luau')
    assert re.search(r'^\s*ShopPromptBubbleEnabled = false,', config, re.M), 'Config.ShopPromptBubbleEnabled must ship false'
    profiles = read('tools/release_profiles.py')
    assert '_flag_off("ShopPromptBubbleEnabled"' in profiles, 'the default profile pins the flag off'
    assert 'Rule("ShopPromptBubbleEnabled", "set", True' in profiles, 'the playtest profile turns it on (docs/157 standing rule)'
    assert '("ShopPromptBubbleEnabled",' in profiles, 'the rehearsal list has it'
    assert '"ShopPromptBubbleEnabled"' in read('tools/release_playtest.py'), 'the manifest shows the flag'

    walk = read('src/client/HubWalkUpClient.luau')
    wc = code_only(walk)
    assert 'Config.ShopPromptBubbleEnabled == true' in wc, 'the client reads the flag'
    assert 'if bubbleOn then' in wc and 'HubPromptBubble' in wc, 'the bubble replaces the round button only with the flag on'
    assert 'Rules.keyFor(true)' in wc and 'Rules.gamepadFor(bubbleOn)' in wc, 'the key comes from the rules'
    assert 'prompt:SetAttribute("BubbleStation", s.id)' in wc, 'every stall prompt carries its station id for the bubble'
    assert 'Enum.ProximityPromptStyle.Custom' in wc, 'the prompt has no default look'
    # the old round button is still there for the flag-off path, after the bubble branch
    assert wc.index('if bubbleOn then') < wc.index('board.Name, board.Adornee, board.Size, board.AlwaysOnTop = "HubWalkUpFace"'), 'old round button kept for the flag-off path'
    assert 'Heartbeat' not in wc and 'padAt' not in wc and 'Touched' not in wc, 'nothing opens by walking near (docs/114 s6.2)'
    assert wc.count('openStation(') == 2, 'a screen opens only from the prompt Triggered handler'

    bubble = read('src/client/HubPromptBubble.luau')
    bc = code_only(bubble)
    assert bc.count(':InputHoldBegin()') == 1, 'one place presses the prompt (a tap or the key)'
    assert 'Activated:Connect' in bc and bc.count('Activated:Connect') == 1, 'one tap handler (the whole bubble)'
    assert 'ContextActionService:BindAction(ACTION' in bc and 'Enum.ContextActionResult.Sink' in bc, 'the key is sunk so Leap never sees the E press'
    assert 'Walk.keyFor(true)' in bc and 'Walk.gamepadFor(true)' in bc, 'E and X come from HubWalkUpRules'
    assert 'ctx.canShow()' in bc and 'ctx.windowOpen()' in bc and 'Rules.step(' in bc, 'visibility comes from the pure rules'
    assert 'Theme.MotionEnabled' in bc, 'Reduce Motion: instant fade, no squash'
    assert 'Chip.apply(' in bc, 'the handbook chip style (docs/114 s4, ChipStyle)'
    for banned in ('Heartbeat', 'padAt', 'Touched', 'rbxassetid', 'FireServer', 'InvokeServer', 'DataStore'):
        assert banned not in bc, 'the bubble module has no ' + banned
    assert 'Rules.pressed(' in bc, 'a press hides the bubble for a moment'
    assert 'Instance.new("ImageLabel")' not in bc and 'Instance.new("ImageButton")' not in bc, 'no pictures, no code-drawn art'
    assert 'BillboardGui' not in bc and 'AlwaysOnTop' not in bc, 'BD-1128: no world billboard (it is drawn under the HUD)'
    assert 'RenderStepped:Connect(' in bc and 'Rules.place(' in bc and 'Rules.layoutFor(' in bc and 'WorldToViewportPoint' in bc, 'BD-1128: placed each frame by the pure rule'
    title = code_only(read('src/client/WeatherTitle.luau'))
    assert 'Slot.centreY(' in title and title.count('softY()') >= 3 and 'pcall(' in title, 'BD-1132: the soft weather title is placed by WeatherTitleSlot, with a fallback to the old spot'
    hud = read('src/client/HudV2.luau')
    assert 'TouchLayout.hudRects(layout)' in code_only(hud) and 'canvas:SetAttribute(name' in code_only(hud), 'BD-1128: HudV2.layout publishes the HUD rectangles the bubble reads'

    show = read('src/server/CaveShowOff.luau')
    sc = code_only(show)
    assert 'if Config.ShopPromptBubbleEnabled == true then' in sc, 'the Heart prompt changes only with the flag'
    gate = sc.index('if Config.ShopPromptBubbleEnabled == true then')
    for needle in ('prompt.Style = Enum.ProximityPromptStyle.Custom', 'Enum.KeyCode.E, Enum.KeyCode.ButtonX', 'SetAttribute("BubbleStation", "heart")'):
        assert sc.index(needle) > gate, 'flag-gated: ' + needle
    assert sc.count('Triggered:Connect') == 1, 'the Heart handler is unchanged (one handler, server side)'

    boot = read('src/client/Bootstrap.client.luau')
    assert 'HubPromptBubble' not in boot and 'ShopPromptBubble' not in boot, 'Bootstrap is untouched (docs/160 s10)'

    handbook = read('docs/114-handbook.md')
    section = handbook[handbook.index('### 6.2'):handbook.index('## 7. Sound rules')]
    assert 'ShopPromptBubbleEnabled' in section and '**E**' in section, 'handbook 6.2 names the E key and the flag'


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
    client = run(args.runner, client_script())
    print(client.stdout, end='')
    if client.returncode or 'passed' not in client.stdout:
        print(client.stderr)
        sys.exit(client.returncode or 1)
    if not args.no_mutants:
        for name, replacements in CLIENT_MUTANTS.items():
            assert run(args.runner, client_script(replacements)).returncode != 0, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
        for name, replacements in MUTANTS.items():
            assert run(args.runner, script(replacements, True)).returncode != 0, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
    print('Shop prompt bubble passed: source guards, rules, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS) + len(CLIENT_MUTANTS)))


if __name__ == '__main__':
    main()
