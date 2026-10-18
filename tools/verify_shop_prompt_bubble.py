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
5. CLIENT SMOKE (tools/shop_prompt_bubble_smoke.luau): the REAL src/client/HubPromptBubble.luau runs against a tiny mock Roblox: what it builds (name,
   line, key cap, "Open"), one bubble at a time, the key press (sunk, nearest prompt, one soft click, hidden for a moment), a tap on the bubble,
   hidden while a window is open (the key still works), hidden when the stall cannot open, phone / gamepad / short-screen versions, Reduce Motion.
6. SOURCE GUARDS: nothing opens by walking near (no Heartbeat / padAt / Touched in the client files, one InputHoldBegin, from a tap or the key),
   the old round button stays for the flag-off path, the Heart prompt is flag-gated, Bootstrap is untouched, the flag is pinned in every profile.
7. MUTANTS: the checks must FAIL when a rule is broken (window ignored, no return delay, farthest wins, range ignored, phone shows a key, flag
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
    local k = R.words(id, "Keyboard", "E", "E")
    assert(k and k.title == title and k.line == line and k.keyLabel == "E" and k.buttonText == "Open", id .. " keyboard words")
    local t = R.words(id, "Touch", "E", "E")
    assert(t and t.keyLabel == nil and t.buttonText == "Tap to open", id .. " phone words: no key, tap to open")
    local g = R.words(id, "Gamepad", "ButtonX", "E")
    assert(g and g.keyLabel == "X" and g.buttonText == "Open", id .. " gamepad words: the X button")
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

print("shop prompt bubble passed: words, keys, fit, which and when")
'''


def prefix(replacements):
    return ('local mods={}\n'
            + 'local script={Parent={CaveHubLayout="CaveHubLayout",HubTravelClientRules="HubTravelClientRules",HubSignCopy="HubSignCopy",HubWalkUpRules="HubWalkUpRules"}}\n'
            + 'local require=function(name) return mods[name] end\n'
            + 'local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau') + '\nmods.CaveHubLayout=CaveHubLayout\n'
            + 'local HubTravelClientRules=' + wrapped('src/shared/HubTravelClientRules.luau') + '\nmods.HubTravelClientRules=HubTravelClientRules\n'
            + 'local HubSignCopy=' + wrapped('src/shared/HubSignCopy.luau', replacements.get('HubSignCopy', ())) + '\nmods.HubSignCopy=HubSignCopy\n'
            + 'local HubWalkUpRules=' + wrapped('src/shared/HubWalkUpRules.luau', replacements.get('HubWalkUpRules', ())) + '\nmods.HubWalkUpRules=HubWalkUpRules\n'
            + 'local HubPromptBubbleRules=' + wrapped('src/shared/HubPromptBubbleRules.luau', replacements.get('HubPromptBubbleRules', ())) + '\n')


def script(replacements=None):
    return prefix(replacements or {}) + LUAU


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
    'a phone says Open instead of Tap to open': {RULES: [('buttonText = if k == "Touch" then "Tap to open" else "Open"', 'buttonText = "Open"')]},
    'a gamepad shows no button name': {RULES: [('return if typeof(keyName) == "string" and GAMEPAD_LABELS[keyName] then GAMEPAD_LABELS[keyName] else GAMEPAD_LABELS[Walk.PromptGamepadBubble]', 'return nil')]},
    'the flag-on key stays G': {'HubWalkUpRules': [('return if bubbleOn == true then HubWalkUpRules.PromptKeyBubble else HubWalkUpRules.PromptKey', 'return HubWalkUpRules.PromptKey')]},
    'the flag-off key becomes E': {'HubWalkUpRules': [('return if bubbleOn == true then HubWalkUpRules.PromptKeyBubble else HubWalkUpRules.PromptKey', 'return HubWalkUpRules.PromptKeyBubble')]},
    'a short screen still gets the big bubble': {RULES: [('< Rules.ShortScreen then', '< -1 then')]},
    'the fit check always passes': {RULES: [('    return Rules.textWidth(words.title, layout.titleSize) <= layout.innerW\n', '    do return true end\n    return Rules.textWidth(words.title, layout.titleSize) <= layout.innerW\n')]},
    'a stall line is too long': {'HubSignCopy': [('nests = "Come and see your eggs!",\n    potions', 'nests = "Come and see all of your wonderful eggs here!",\n    potions')]},
    'a stall line has a number': {'HubSignCopy': [('potions = "Fresh potions here!"', 'potions = "Fresh potions 4 you!"')]},
    'a stall line uses a jargon word': {'HubSignCopy': [('index = "Meet all your dinos!"', 'index = "Open the menu here!"')]},
    'the Heart has no words': {'HubSignCopy': [('    heart = "Let everyone see you!",\n', '')]},
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
            assert run(args.runner, script(replacements)).returncode != 0, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
    print('Shop prompt bubble passed: source guards, rules, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS) + len(CLIENT_MUTANTS)))


if __name__ == '__main__':
    main()
