#!/usr/bin/env python3
"""BD-1237 (docs/240 order step 4): Egg chances, the Food guide, the weather title card, the toast cards and the Fusion colour bar on the style
rules R1-R8, behind Config.MenusCohesionEnabled.

What is checked:
  1. pure (pinned Luau runtime, the REAL ToyboxKit / MenusCohesionRules / PhoneScale / OddsCopy inputs): the kid chances ("1 in 4", "9 in 10",
     never "10 in 10" under 100%, two figures, grouped), the trimmed percents (36.4000% -> 36.4%, nothing else changes), every odds and food
     rect inside its body at five window sizes, nothing overlapping, buttons never under 44 px on screen (R8, docs/72), the food copy short;
  2. static: the flag ships false (once), the default profile pins it off, the playtest profile sets it on, the rehearsal list and the playtest
     manifest have it; MenusCohesion / MenusCohesionRules are required only behind the flag; no green and no cyan button on the odds pages (R3);
     no dark navy colour in the new code (R1); one font (R6); the food pictures are the bound V3 food meshes (R5); the weather word is white (R4)
     and every weather has a bound icon; the toast cards turn cream; Bootstrap holds no cohesion code; CI runs this check;
  3. mutants put each defect back and the checks must fail.
NOT Studio evidence: how the screens look in the game is in docs/evidence/2026-11-16-menus-style.
Usage: python tools/verify_menus_cohesion.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KIT = 'src/shared/ToyboxKit.luau'
RULES = 'src/shared/MenusCohesionRules.luau'
PHONE = 'src/shared/PhoneScale.luau'
MENUS = 'src/client/MenusCohesion.luau'
SHOP = 'src/client/ShopScreens.luau'
SMALL = 'src/client/SmallScreens.luau'
TOASTS = 'src/client/Toasts.luau'
WEATHER = 'src/client/WeatherTitle.luau'
FUSIONW = 'src/client/FusionWidgets.luau'
BOOT = 'src/client/Bootstrap.client.luau'
CONFIG = 'src/shared/Config.luau'
ICONS = 'src/shared/UIIconAssets.luau'
MESHES = 'src/shared/WorldGeneratedMeshes.luau'
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
__mods.MenusCohesionRules = __RULES__
__mods.PhoneScale = __PHONE__
local Kit, R, PhoneScale = __req("ToyboxKit"), __req("MenusCohesionRules"), __req("PhoneScale")
-- kid chances
local want = {{100, "Always"}, {0, "Never"}, {80, "8 in 10"}, {99.5, "9 in 10"}, {50, "5 in 10"}, {36.4, "1 in 3"}, {26, "1 in 4"},
    {12, "1 in 8"}, {7, "1 in 14"}, {9.6, "1 in 10"}, {0.4, "1 in 250"}, {0.083, "1 in 1,200"}, {0.02, "1 in 5,000"}, {49.9, "1 in 2"}}
for _, case in want do
    local got = R.kidChance(case[1])
    assert(got == case[2], string.format("kidChance(%s) = %s, want %s", tostring(case[1]), got, case[2]))
end
for p = 0.01, 99.99, 0.37 do
    local s = R.kidChance(p)
    assert(not string.find(s, "%.") and not string.find(s, "%%") and #s <= 12, "kid words, no decimals: " .. s)
    assert(s ~= "10 in 10", "never 10 in 10 under 100%")
end
-- trimmed percents
local trims = {{"Compy: 36.4000%", "Compy: 36.4%"}, {"Raptor: 26.0000%", "Raptor: 26%"}, {"Blue (Rare): 0.0125% per slot", "Blue (Rare): 0.0125% per slot"},
    {"Cracked: 20%; hatch 20%", "Cracked: 20%; hatch 20%"}, {"1 dinosaur: 70.5000%", "1 dinosaur: 70.5%"}, {"Species (bought egg, no run boost):", "Species (bought egg, no run boost):"}}
for _, case in trims do assert(R.trimPercents(case[1]) == case[2], "trim " .. case[1] .. " -> " .. R.trimPercents(case[1])) end
-- rects at five windows
local function inside(r, w, h, what) assert(R.inside(r, w, h), what .. string.format(" (%d,%d %dx%d in %dx%d)", r.x, r.y, r.w, r.h, w, h)) end
local function apart(list, what)
    for i = 1, #list do for j = i + 1, #list do assert(not R.overlap(list[i], list[j]), what .. ": " .. i .. " overlaps " .. j) end end
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
    assert(bh * win.scale >= 44 - 1e-6, tag .. "buttons never under 44 px on screen")
    local odds = R.odds(win.w, win.h, win.scale, 2)
    inside(odds.panel, win.w, win.h, tag .. "odds panel inside the body")
    inside(odds.list, odds.panel.w, odds.panel.h, tag .. "odds list inside its panel")
    local all = {odds.panel}
    for i, b in odds.buttons do
        inside(b, win.w, win.h, tag .. "odds button " .. i .. " inside the body")
        assert(b.h == bh and b.w >= 120, tag .. "odds button " .. i .. " is a full button")
        table.insert(all, b)
    end
    apart(all, tag .. "odds: nothing overlaps")
    assert(odds.list.h >= R.GroupH + R.RowH * 2, tag .. "a group and two rows show without scrolling")
    local food = R.food(win.w, win.h, #R.Food)
    local parts = {food.footer}
    inside(food.footer, win.w, win.h, tag .. "food footer inside the body")
    for i, c in food.cards do
        inside(c, win.w, win.h, tag .. "food card " .. i .. " inside the body")
        table.insert(parts, c)
        local inner = R.foodCard(c)
        local list = {}
        for _, key in {"picture", "name", "chip"} do inside(inner[key], c.w, c.h, tag .. "food card " .. i .. " " .. key .. " inside its card") table.insert(list, inner[key]) end
        apart(list, tag .. "food card " .. i .. " parts")
        assert(inner.picture.w >= 32, tag .. "a food picture you can see")
    end
    apart(parts, tag .. "food: nothing overlaps")
    checked += 1
end
-- food copy
assert(#R.Food == 4, "four food kinds")
local function words(s) local n = 0 for _ in string.gmatch(s, "%S+") do n += 1 end return n end
for _, f in R.Food do assert(words(f.name) == 1 and words(R.growChip(f.growth)) == 2, "short food words: " .. f.name) end
assert(words(R.foodFooter(12)) <= 10, "the footer is one short line")
assert(R.grouped(1234567) == "1,234,567" and R.grouped(250) == "250", "grouped numbers")
print("MENUS_COHESION_OK " .. checked)
'''


def layout_source():
    src = LUAU
    for key, path in (('__KIT__', KIT), ('__RULES__', RULES), ('__PHONE__', PHONE)):
        src = src.replace(key, module(path))
    return src


def run_pure(runner):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'menus_cohesion.luau'
        path.write_text(layout_source(), encoding='utf-8')
        done = subprocess.run([runner, str(path)], capture_output=True, text=True, timeout=120)
    out = done.stdout + done.stderr
    return done.returncode == 0 and 'MENUS_COHESION_OK' in out, out


def gated(path, needle, gate, window=700):
    text = read(path).replace(' == ', '==')
    hits = list(re.finditer(re.escape(needle), text))
    assert hits, '%s uses %s' % (path, needle)
    for m in hits:
        assert gate in text[max(0, m.start() - window):m.start() + 20], '%s requires %s only behind the flag' % (path, needle)


def static_checks():
    cfg = read(CONFIG)
    assert len(re.findall(r'^    MenusCohesionEnabled = false,$', cfg, re.M)) == 1, 'MenusCohesionEnabled ships false in Config (once)'
    profiles = read(PROFILES)
    assert '_flag_off("MenusCohesionEnabled",' in profiles, 'the default profile pins the flag off'
    assert 'Rule("MenusCohesionEnabled", "set", True,' in profiles, 'the playtest profile sets it on (docs/157)'
    assert '("MenusCohesionEnabled", "BD-1237' in profiles, 'the rehearsal list has it'
    assert '"MenusCohesionEnabled"' in read(PLAYTEST), 'the playtest manifest records it'
    gated(SHOP, 'require(script.Parent.MenusCohesion)', 'Config.MenusCohesionEnabled==true')
    gated(SMALL, 'require(script.Parent.MenusCohesion)', 'Config.MenusCohesionEnabled==true')
    for path in (TOASTS, WEATHER):
        gated(path, 'require(Shared.MenusCohesionRules)', 'MenusCohesionEnabled==true', 200)
    assert 'MenusCohesionEnabled==true' in read(FUSIONW).replace(' == ', '==') and 'W.knownColour(' in read(FUSIONW), 'Fusion: no empty colour bar (R8), behind the flag'
    menus = read(MENUS)
    assert 'M.Grey' in menus and 'C.blue' not in menus and 'C.red' not in menus, 'grey buttons, no cyan or red button (R3)'
    for fn in ('function M.drawChances', 'function M.drawExact'):
        body = menus.split(fn, 1)[1].split('\nfunction M.', 1)[0]
        assert ', true}' not in body, fn + ': no green button on the odds pages (R3)'
    assert 'buttons(d.body' not in menus.split('function M.drawFood', 1)[1].split('\nreturn M', 1)[0], 'the food guide has no button (the X closes it)'
    small, shop = read(SMALL), read(SHOP)
    exit_ = small.split('MenusCohesion).confirm(', 1)[1].split('}}})', 1)[0] + '}'
    assert exit_.count(',true}') == 1 and '{"CANCEL",close,false}' in exit_, 'Go home?: GO HOME green, CANCEL grey'
    buy = shop.split('MenusCohesion).confirm(', 1)[1].split('}}})', 1)[0] + '}'
    assert buy.count(',true}') == 1 and buy.count(',false}') == 2, 'Buy egg: CONFIRM the one green button, Chances and CANCEL grey'
    assert 'if menus then C.card else C.blue' in shop, 'the shop egg card: a grey Chances button (R3)'
    assert 'if Config.MenusCohesionEnabled==true then C.card else C.gold' in small, 'Settings Help: How to play grey beside the green FOOD GUIDE (R3)'
    assert '{"EXACT %", d.exact}' in menus and 'Rules.kidChance(row.percent)' in menus, 'kid chances with the exact numbers one tap away (R6)'
    assert 'Rules.trimPercents(raw)' in menus, 'the exact page shows trimmed percents (R6)'
    assert 'Layout.panel(' in menus and 'ScrollingFrame' in menus, 'the lists sit in a cream panel, not on the studs (R1, R2)'
    assert 'GeneratedWorld' in menus and 'foodView(card, food.mesh' in menus, 'food pictures are the real V3 food meshes (R5)'
    assert 'art(' not in menus and '"leaf"' not in menus, 'no code-drawn leaf (R5)'
    assert 'Chip.new(' in menus, 'the grow tag is a chunky chip (verify_chip_style)'
    assert 'return M.drawChances(d)' in menus and 'return M.drawFood(d)' in menus and 'ModalCompact.onLayout(' in menus, 'drawn again on a resize (R8)'
    rules = read(RULES)
    meshes = read(MESHES)
    for mesh in re.findall(r'mesh = "(\w+)"', rules):
        assert re.search(r'^\s*%s = \{assetId = "\d+"' % mesh, meshes, re.M), 'food mesh %s is a bound V3 mesh' % mesh
    icons = read(ICONS)
    for weather in ('rain', 'thunder', 'blizzard', 'volcano', 'aurora', 'quake', 'bloodmoon'):
        assert re.search(r'%s = "%s"' % (weather, weather), rules), 'the weather %s has its icon' % weather
        assert re.search(r'^\s*%s = "rbxassetid://\d+"' % weather, icons, re.M), 'the %s icon is bound' % weather
    weather = read(WEATHER)
    assert 'title.TextColor3=if card then Color3.new(1,1,1)' in weather, 'the weather word is white with the flag (R4)'
    toasts = read(TOASTS)
    assert 'card.BackgroundColor3=rgb(Cohesion.Cream)' in toasts and 'rgb(Cohesion.Card) else C.panel:Lerp' in toasts, 'toast cards turn cream (R1)'
    for path in (MENUS, RULES):
        text = read(path)
        for dark in re.findall(r'fromRGB\((\d+),\s*(\d+),\s*(\d+)\)', text):
            r, g, b = (int(x) for x in dark)
            assert not (max(r, g, b) < 90 and b >= r), '%s uses a dark navy / slate colour (R1): %s' % (path, dark)
        assert 'Gotham' not in text, '%s uses one font (R6)' % path
    assert 'MenusCohesion' not in read(BOOT), 'Bootstrap holds no cohesion code'
    assert 'python tools/verify_menus_cohesion.py --runner /tmp/luau/luau' in read('.github/workflows/build-generated-place.yml'), 'CI runs this check'


MUTANTS = {
    'the flag ships on': (CONFIG, '    MenusCohesionEnabled = false,', '    MenusCohesionEnabled = true,'),
    'the playtest profile forgets it': (PROFILES, 'Rule("MenusCohesionEnabled", "set", True,', 'Rule("MenusCohesionEnabledX", "set", True,'),
    'the food guide without the flag': (SMALL, 'if Config.MenusCohesionEnabled==true then return require(script.Parent.MenusCohesion).food(', 'if true then return require(script.Parent.MenusCohesion).food('),
    'a cyan button': (MENUS, 'M.Grey = Color3.fromRGB(128, 142, 158)', 'M.Grey = C.blue'),
    'a green button on the odds page': (MENUS, '{{"EXACT %", d.exact}, {"BACK", d.back}}', '{{"EXACT %", d.exact, true}, {"BACK", d.back}}'),
    'a navy panel': (MENUS, 'M.Grey = Color3.fromRGB(128, 142, 158)', 'M.Grey = Color3.fromRGB(28, 40, 64)'),
    '10 in 10': (RULES, 'math.clamp(math.floor(percent / 10 + 0.5), 5, 9)', 'math.clamp(math.floor(percent / 10 + 0.5), 5, 10)'),
    'percents not trimmed': (RULES, 'return if frac == "" then whole .. "%" else whole .. "." .. frac .. "%"', 'return whole .. "." .. frac .. "0000%"'),
    'buttons overflow the body': (RULES, 'table.insert(out, rect(bodyW - rowW + (i - 1)', 'table.insert(out, rect(bodyW - rowW + 20 + (i - 1)'),
    'the odds panel runs under the buttons': (RULES, 'local panel = rect(0, 0, bodyW, bodyH - Kit.Gutter - h)', 'local panel = rect(0, 0, bodyW, bodyH - h + 8)'),
    'the food name over the picture': (RULES, 'local name = rect(pad, picture.y + pic + 4, card.w - pad * 2, nameH)', 'local name = rect(pad, picture.y + pic - 12, card.w - pad * 2, nameH)'),
    'an unbound food mesh': (RULES, 'mesh = "food_v3_fruit_a"', 'mesh = "food_v3_fruit_z"'),
    'a purple weather word': (WEATHER, 'title.TextColor3=if card then Color3.new(1,1,1)', 'title.TextColor3=if card then TITLE_COLOR[id]'),
    'a green CANCEL on Go home?': (SMALL, '{"CANCEL",close,false}', '{"CANCEL",close,true}'),
    'a second green button on Buy egg': (SHOP, '{"CANCEL",function() open("auras") end,false}', '{"CANCEL",function() open("auras") end,true}'),
    'a cyan Chances button': (SHOP, 'if menus then C.card else C.blue', 'if menus then C.blue else C.blue'),
    'navy toasts': (TOASTS, 'card.BackgroundColor3=rgb(Cohesion.Cream)', 'card.BackgroundColor3=C.card'),
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
    ok, out = run_pure(args.runner)
    if not ok:
        print('FAIL pure:\n' + out)
        sys.exit(1)
    print(out.strip())
    if not args.no_mutants:
        survived = []
        for name, mutant in MUTANTS.items():
            MUTANT = mutant
            try:
                static_checks()
                caught = not run_pure(args.runner)[0]
            except AssertionError:
                caught = True
            MUTANT = None
            if not caught:
                survived.append(name)
        if survived:
            print('FAIL mutants survived:', ', '.join(survived))
            sys.exit(1)
        print('mutants: %d of %d caught' % (len(MUTANTS), len(MUTANTS)))
    print('PASS verify_menus_cohesion')


if __name__ == '__main__':
    main()
