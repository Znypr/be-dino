#!/usr/bin/env python3
"""BD-1214 (docs/240 order step 3): Run complete, Home (Sanctuary), the Welcome steps and the Loading screen on the style rules R1-R8,
behind Config.ScreensCohesionEnabled.

What is checked:
  1. layout (pinned Luau runtime, the REAL ToyboxKit / ScreensCohesionLayout / PhoneScale / FtueCopy): at a 1280x720 window, the lead's Studio
     viewport, a small phone, full HD and a shrunk desktop body, every panel, card, picture, text box and button of the three menu screens lies
     inside the body or its panel (R8), nothing overlaps, buttons are 48 px and never under 44 px on screen (docs/72), panels are 12 px apart,
     the label / value rows that are drawn fit their panel;
  2. copy: the Welcome steps are three short cards with a bound real picture each (R5, R6 kid copy: at most 4 words a title, 7 a line),
     the Run complete facts are the same facts as the old rows (same numbers, Growth hidden at 0), the eggs line counts right;
  3. static: the flag ships false (once), the default profile pins it off, the playtest profile sets it on, the rehearsal list and the playtest
     manifest have it; ScreensCohesion is required only behind the flag (RunComplete, HomeScreen, SmallScreens); one green button per screen
     (R3); no dark navy / slate colour in the new code (R1); every text uses FredokaOne (R6); the warm loading look is built only with the flag
     and the old dark look is still there; Bootstrap holds no screen code for Home (only the HomeScreen call) and CI runs this check;
  4. mutants put each defect back and the checks must fail.
NOT Studio evidence: how the screens look in the game is in docs/evidence/2026-11-16-screens-cohesion.
Usage: python tools/verify_screens_cohesion.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KIT = 'src/shared/ToyboxKit.luau'
RECTS = 'src/shared/ScreensCohesionLayout.luau'
PHONE = 'src/shared/PhoneScale.luau'
COPY = 'src/shared/FtueCopy.luau'
SCREENS = 'src/client/ScreensCohesion.luau'
HOME = 'src/client/HomeScreen.luau'
COMPLETE = 'src/client/RunComplete.luau'
SMALL = 'src/client/SmallScreens.luau'
LOADING = 'src/loading/Loading.client.luau'
BOOT = 'src/client/Bootstrap.client.luau'
CONFIG = 'src/shared/Config.luau'
SLOTS = 'src/shared/AssetSlots.luau'
ICONS = 'src/shared/UIIconAssets.luau'
PROFILES = 'tools/release_profiles.py'
PLAYTEST = 'tools/release_playtest.py'

MUTANT = None  # (path, old, new) while a mutant runs


def read(path):
    text = (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')
    if MUTANT and MUTANT[0] == path:
        assert MUTANT[1] in text, 'mutant text not found in %s: %r' % (path, MUTANT[1][:60])
        text = text.replace(MUTANT[1], MUTANT[2], 1)
    return text


def module(path):
    src = read(path)
    src = re.sub(r'require\(script\.Parent\.(\w+)\)', r'__req("\1")', src)
    return '(function()\n' + src + '\nend)'


LUAU = r'''
local __mods = {}
local __loaded = {}
local function __req(name) if __loaded[name] == nil then __loaded[name] = __mods[name]() end return __loaded[name] end
__mods.ToyboxKit = __KIT__
__mods.ScreensCohesionLayout = __RECTS__
__mods.PhoneScale = __PHONE__
__mods.FtueCopy = __COPY__
local Kit, L, PhoneScale, Copy = __req("ToyboxKit"), __req("ScreensCohesionLayout"), __req("PhoneScale"), __req("FtueCopy")
local SLOTS = __SLOTS__
local function inside(r, w, h, what) assert(L.inside(r, w, h), what .. string.format(" (%d,%d %dx%d in %dx%d)", r.x, r.y, r.w, r.h, w, h)) end
local function apart(list, what)
    for i = 1, #list do for j = i + 1, #list do assert(not L.overlap(list[i], list[j]), what .. ": " .. i .. " overlaps " .. j) end end
end
local windows = {}
for _, size in {{1280, 720}, {1274, 481}, {667, 375}, {1920, 1080}} do
    local m = PhoneScale.modal(size[1], size[2], nil)
    local w = if m.mode == "compact" then math.floor(m.innerW) else 824
    local h = if m.mode == "compact" then math.floor(m.innerH) else 402
    table.insert(windows, {name = size[1] .. "x" .. size[2], scale = m.effScale, w = w, h = h})
end
table.insert(windows, {name = "824x402 at 0.56", scale = 0.56, w = 824, h = 402})
local checked = 0
for _, win in windows do
    local tag = string.format("%s (body %dx%d, scale %.2f): ", win.name, win.w, win.h, win.scale)
    local bh = Kit.buttonHeights(win.scale)
    assert(bh >= 48 and bh * win.scale >= 44 - 1e-6, tag .. "buttons 48 px, never under 44 px on screen")
    -- Run complete and Home: two panels over a button row
    for _, case in {{"run complete", 0.44, 2}, {"run complete, one button", 0.44, 1}, {"home", 0.4, 2}, {"home, explore only", 0.4, 1}} do
        local lay = L.split(win.w, win.h, win.scale, case[2], case[3])
        local t = tag .. case[1] .. ": "
        local all = {lay.left, lay.right}
        inside(lay.left, win.w, win.h, t .. "left panel inside the body") inside(lay.right, win.w, win.h, t .. "right panel inside the body")
        assert(lay.right.x - (lay.left.x + lay.left.w) == Kit.Gutter, t .. "panels 12 px apart")
        assert(lay.right.x + lay.right.w == win.w, t .. "the panels fill the body width")
        assert(#lay.buttons == case[3], t .. "button count")
        for i, b in lay.buttons do
            inside(b, win.w, win.h, t .. "button " .. i .. " inside the body")
            assert(b.h == bh and b.w >= 120, t .. "button " .. i .. " is a full button")
            assert(b.y - (lay.left.y + lay.left.h) >= Kit.Gutter, t .. "button " .. i .. " under the panels")
            table.insert(all, b)
        end
        apart(all, t .. "nothing overlaps")
        assert(lay.left.h >= 160, t .. "the panels keep room for content")
        local rows = L.rowsThatFit(lay.left.h, Kit.PanelPad + 36, 9)
        assert(rows >= 3, t .. "at least three fact rows fit")
        assert(Kit.PanelPad + 36 + rows * L.FactRowH <= lay.left.h - Kit.PanelPad, t .. "the drawn rows stay inside the panel")
        local homeRows = L.rowsThatFit(lay.right.h, 52, 3)
        local tip = L.tip(lay.right, 52 + homeRows * L.FactRowH + Kit.Gutter)
        if tip then
            inside(tip.picture, lay.right.w, lay.right.h, t .. "tip picture inside its panel") inside(tip.line, lay.right.w, lay.right.h, t .. "tip line inside its panel")
            apart({tip.picture, tip.line, L.rect(0, 52, lay.right.w, homeRows * L.FactRowH)}, t .. "tip, rows")
        end
        local eggs = L.eggsPanel(lay.right, 3)
        local parts = {eggs.line}
        for i, p in eggs.pictures do inside(p, lay.right.w, lay.right.h, t .. "egg picture " .. i .. " inside its panel") table.insert(parts, p) end
        inside(eggs.line, lay.right.w, lay.right.h, t .. "eggs line inside its panel")
        apart(parts, t .. "egg pictures and line")
        checked += 1
    end
    -- Welcome: three cards over one centred button
    local cards = L.cards(win.w, win.h, win.scale, 3)
    local t = tag .. "welcome: "
    local all = {}
    for i, c in cards.cards do
        inside(c, win.w, win.h, t .. "card " .. i .. " inside the body")
        table.insert(all, c)
        local parts = L.card(c)
        local list = {}
        for _, key in {"chip", "picture", "title", "line"} do inside(parts[key], c.w, c.h, t .. "card " .. i .. " " .. key .. " inside the card") table.insert(list, parts[key]) end
        apart(list, t .. "card " .. i .. " parts")
        assert(parts.picture.w >= 32, t .. "a picture you can see")
        assert(parts.line.h >= Kit.Type.body * 2, t .. "two lines of 16 px text fit")
    end
    local b = cards.buttons[1]
    inside(b, win.w, win.h, t .. "button inside") table.insert(all, b)
    assert(math.abs((b.x + b.w / 2) - win.w / 2) <= 1, t .. "the button is centred")
    apart(all, t .. "nothing overlaps")
    checked += 1
end
-- copy
assert(#Copy.welcomeSteps == 3, "three Welcome steps")
local function words(s) local n = 0 for _ in string.gmatch(s, "%S+") do n += 1 end return n end
for i, step in Copy.welcomeSteps do
    assert(words(step[1]) <= 4 and words(step[2]) <= 7, "step " .. i .. " is short kid copy")
    local id = SLOTS[step[3]]
    assert(type(id) == "string" and string.match(id, "^rbxassetid://%d+$"), "step " .. i .. " has a bound real picture: " .. step[3])
end
local facts = Copy.runCompleteFacts({eggs = 15, crystals = 30, nests = 1, nestCrystals = 0, growth = 0, killEggs = 2})
local want = {{"Eggs found", "15"}, {"Crystals", "+30"}, {"Hunting bonus", "+2 eggs"}, {"Nests", "+1"}}
assert(#facts == #want, "the facts are the old facts (growth hidden at 0, no extra nests line)")
for i, row in want do assert(facts[i][1] == row[1] and facts[i][2] == row[2], "fact " .. i .. ": " .. facts[i][1] .. " " .. facts[i][2]) end
local old = Copy.runCompleteRows({eggs = 4, crystals = 9, nests = 0, nestCrystals = 50, growth = 12, killEggs = 0})
local new = Copy.runCompleteFacts({eggs = 4, crystals = 9, nests = 0, nestCrystals = 50, growth = 12, killEggs = 0})
assert(#old == #new, "the same number of facts as the old rows")
assert(Copy.eggsReadyLine(0) == "Eat more food to find eggs!" and Copy.eggsReadyLine(1) == "1 egg is ready to hatch!" and Copy.eggsReadyLine(15) == "15 eggs are ready to hatch!", "eggs line")
print("SCREENS_COHESION_OK " .. checked)
'''


def slots_table():
    found = {}
    for path in (SLOTS, ICONS):
        for name, value in re.findall(r'^\s*(\w+) = "(rbxassetid://\d+|)"', read(path), re.M):
            found.setdefault(name, value)
    return '{' + ', '.join('%s = "%s"' % (k, v) for k, v in found.items()) + '}'


def layout_source():
    src = LUAU
    for key, path in (('__KIT__', KIT), ('__RECTS__', RECTS), ('__PHONE__', PHONE), ('__COPY__', COPY)):
        src = src.replace(key, module(path))
    return src.replace('__SLOTS__', slots_table())


def run_layout(runner):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'screens_cohesion.luau'
        path.write_text(layout_source(), encoding='utf-8')
        done = subprocess.run([runner, str(path)], capture_output=True, text=True, timeout=120)
    out = done.stdout + done.stderr
    return done.returncode == 0 and 'SCREENS_COHESION_OK' in out, out


def static_checks():
    cfg = read(CONFIG)
    assert len(re.findall(r'^    ScreensCohesionEnabled = false,$', cfg, re.M)) == 1, 'ScreensCohesionEnabled ships false in Config (once)'
    profiles = read(PROFILES)
    assert '_flag_off("ScreensCohesionEnabled",' in profiles, 'the default profile pins the flag off'
    assert 'Rule("ScreensCohesionEnabled", "set", True,' in profiles, 'the playtest profile sets it on (docs/157)'
    assert '("ScreensCohesionEnabled", "BD-1214' in profiles, 'the rehearsal list has it'
    assert '"ScreensCohesionEnabled"' in read(PLAYTEST), 'the playtest manifest records it'
    gate = 'Config.ScreensCohesionEnabled==true'
    for path in (COMPLETE, HOME, SMALL):
        text = read(path).replace(' == ', '==')
        for m in re.finditer(r'require\(script\.Parent\.ScreensCohesion\)', text):
            assert gate in text[max(0, m.start() - 700):m.start()], '%s requires ScreensCohesion only behind the flag' % path
        assert 'ScreensCohesion' in text, '%s hands its screen to ScreensCohesion' % path
    screens = read(SCREENS)
    for fn in ('function S.drawResults', 'function S.drawHome', 'function S.drawTutorial'):
        body = screens.split(fn, 1)[1].split('\nfunction S.', 1)[0].split('\nreturn S', 1)[0]
        greens = len(re.findall(r'\{"[^"]+", [^{}]*, (true|not d\.hasEggs)\}', body))
        assert greens >= 1, fn + ': a green main button'
    assert 'S.Grey' in screens and 'S.Green' in screens, 'green main button, grey others (R3)'
    for fn in ('S.drawResults(d)', 'S.drawHome(d)', 'S.drawTutorial(d)'):
        assert 'live(' in screens and ('return ' + fn) in screens, fn + ' is drawn again when the window is laid out for another size (R8)'
    assert 'ModalCompact.onLayout(' in screens and 'ModalCompact.signature()' in screens, 'the resize hook (R8)'
    results = screens.split('function S.results', 1)[1].split('\nfunction S.home', 1)[0]
    assert '{"Back home", d.back, not d.hasEggs}' in results and '{"OPEN EGGS", d.openEggs, true}' in results, 'Run complete: OPEN EGGS is the one green button when there are eggs, else Back home'
    home = screens.split('function S.home', 1)[1].split('\nfunction S.tutorial', 1)[0]
    assert '{"OPEN EGGS", d.openEggs, false}' in home and '{"Explore", d.explore, true}' in home, 'Home: Explore is the one green button'
    for path in (SCREENS, RECTS):
        text = read(path)
        for dark in re.findall(r'fromRGB\((\d+),\s*(\d+),\s*(\d+)\)', text):
            r, g, b = (int(x) for x in dark)
            assert not (max(r, g, b) < 90 and b >= r), '%s uses a dark navy / slate colour (R1): %s' % (path, dark)
        assert 'Enum.Font.' not in text or 'FredokaOne' in text, '%s uses one font (R6)' % path
        assert 'Gotham' not in text, '%s uses one font (R6)' % path
    assert 'C.blue' not in screens and 'C.gold' not in screens, 'no blue / amber words on the new screens (R2, R4)'
    assert 'Text == "Your eggs are safe!"' in screens, 'the defeat line moves off the studs into the facts panel'
    loading = read(LOADING)
    assert 'ScreensCohesionEnabled==true' in loading, 'the loading screen reads the flag'
    warm = loading.split('if warm then', 1)[1].split('\nReplicatedFirst:RemoveDefaultLoadingScreen()', 1)[0]
    assert 'Enum.Font.FredokaOne' in warm and 'Gotham' not in warm, 'the warm loading look uses the one font'
    assert 'Kit.Tone.panel' in warm and 'UIStroke' in warm, 'the warm bar is a cream panel with an ink outline'
    assert 'icons.dinos' in warm and 'rbxassetid' in warm, 'the warm loading look shows a real bound picture'
    assert loading.index('local warm=false') < loading.index('ReplicatedFirst:RemoveDefaultLoadingScreen()'), 'the look is decided before the Roblox screen goes'
    assert 'Color3.fromRGB(18, 40, 49)' in loading and '"BE DINO!\\n\\n"' in loading, 'flag off: the old dark look is still there'
    boot = read(BOOT)
    assert 'require(script.Parent.HomeScreen).render(' in boot, 'Bootstrap hands Home to HomeScreen'
    assert 'heroCard' not in boot and 'sanctuaryTip' not in boot, 'no Home screen code left in Bootstrap (size ceiling)'
    assert 'ScreensCohesion' not in boot, 'Bootstrap holds no cohesion code'
    workflow = read('.github/workflows/build-generated-place.yml')
    assert 'python tools/verify_screens_cohesion.py --runner /tmp/luau/luau' in workflow, 'CI runs this check'


MUTANTS = {
    'the flag ships on': (CONFIG, '    ScreensCohesionEnabled = false,', '    ScreensCohesionEnabled = true,'),
    'the playtest profile forgets it': (PROFILES, 'Rule("ScreensCohesionEnabled", "set", True,', 'Rule("ScreensCohesionEnabledX", "set", True,'),
    'Home requires the screens without the flag': (HOME, '    if Config.ScreensCohesionEnabled==true then\n', '    if true then\n'),
    'a second green button on Home': (SCREENS, '{"OPEN EGGS", d.openEggs, false}', '{"OPEN EGGS", d.openEggs, true}'),
    'a navy panel': (SCREENS, 'S.Grey = Color3.fromRGB(128, 142, 158)', 'S.Grey = Color3.fromRGB(28, 40, 64)'),
    'buttons overflow the body': (RECTS, '    local x0 = if centred or n == 1 then (bodyW - rowW) / 2 else bodyW - rowW', '    local x0 = if centred or n == 1 then (bodyW - rowW) / 2 else bodyW - rowW + 20'),
    'panels touch the buttons': (RECTS, '    local panelH = bodyH - Kit.Gutter - h', '    local panelH = bodyH - h + 4'),
    'the card picture runs into the title': (RECTS, '    local title = rect(pad, picture.y + pic + Kit.Gutter / 2,', '    local title = rect(pad, picture.y + pic - 10,'),
    'a long welcome line': (COPY, '"Walk into food to eat it."', '"Walk into any food you see to eat it up and grow."'),
    'a welcome picture that is not bound': (COPY, '"egg_green_spotted" }', '"egg_purple_sparkle" }'),
    'growth shown at 0': (COPY, '    if math.floor(s.growth or 0) > 0 then table.insert(rows, {"Growth"', '    if true then table.insert(rows, {"Growth"'),
    'the dark loading screen with the flag': (LOADING, '    background.BackgroundColor3=Color3.fromRGB(104,178,64)\n', '    background.BackgroundColor3=Color3.fromRGB(104,178,64)\n    local slate=Color3.fromRGB(18,40,49)\n    message.Font=Enum.Font.GothamBold\n'),
}


def main():
    global MUTANT
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    try:
        static_checks()
    except AssertionError as e:
        print('FAIL static:', e)
        sys.exit(1)
    ok, out = run_layout(args.runner)
    if not ok:
        print('FAIL layout:\n' + out)
        sys.exit(1)
    print(out.strip())
    if not args.no_mutants:
        survived = []
        for name, mutant in MUTANTS.items():
            MUTANT = mutant
            try:
                static_checks()
                caught = not run_layout(args.runner)[0]
            except AssertionError:
                caught = True
            MUTANT = None
            if not caught:
                survived.append(name)
        if survived:
            print('FAIL mutants survived:', ', '.join(survived))
            sys.exit(1)
        print('mutants: %d of %d caught' % (len(MUTANTS), len(MUTANTS)))
    print('PASS verify_screens_cohesion')


if __name__ == '__main__':
    main()
