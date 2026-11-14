#!/usr/bin/env python3
"""BD-1193 (docs/234, polish finding P-3ccb6b): a SHORT but WIDE window with a mouse (Studio at 1274 x 481) shows the left menu as a column on the left edge.

The polish loop saw only POTIONS and a shield icon floating at the top centre over the SIZE bar (the phone layout's top row, in a run). This check runs the REAL
TouchLayout, PhoneScale and Config in the pinned Luau runtime, for widths 900 to 1920 and heights 339 to 499 (all under the compact limit of 500), mouse, at home
(6 buttons, or 5 word buttons + the gear) and in a run (2, or 1 + the gear):
 * the rail is a column (rail.column), on the left edge (x <= the safe margin), every cell 44 px or more tall, and every cell inside the canvas;
 * no cell touches the egg plate, build badge, notice, wallet, goal line, Goals header, objectives pill, weather / LEAP, Home, chip, Tell us!, Admin, SIZE bar or hint
   (TouchLayout.railFits);
 * the SIZE bar is no longer pushed down under a rail at the top centre (it starts at the top margin);
 * a touch phone (same sizes, touch = true) and a narrow mouse window (under 900 px) keep the old top row, unchanged.
The mutants put each defect back and the check must fail. NOT Studio evidence: nobody saw a pixel (a Studio re-look at 1274 x 481 is the follow-up).
Usage: python tools/verify_rail_column.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
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
local m = Config.TouchSafeMargin
local failures, checked, columns = {}, 0, 0
local function fail(msg) if #failures < 12 then table.insert(failures, msg) end end

local function lay(w, h, touch, count, words, goals)
    return TouchLayout.compute({width = w, height = h, touch = touch, navCount = count, railWords = words, goals = goals, objectives = goals})
end

local widths, heights = {}, {}
for w = 900, 1920, 60 do table.insert(widths, w) end
table.insert(widths, 1274)
for h = 339, 499, 20 do table.insert(heights, h) end
table.insert(heights, 481) table.insert(heights, 499)

for _, w in widths do
    for _, h in heights do
        for _, words in {false, true} do
            for _, count in (if words then {5, 1} else {6, 2}) do
                for _, goals in {false, true} do
                    local l = lay(w, h, false, count, words, goals)
                    checked += 1
                    local tag = string.format("%dx%d words=%s count=%d goals=%s", w, h, tostring(words), count, tostring(goals))
                    local r = l.rail
                    if r.column ~= true then
                        if w == 1274 and h == 481 then fail(tag .. ": 1274 x 481 has no column") end
                    else
                        columns += 1
                        if r.x > m + 1e-6 then fail(tag .. ": the column is not on the left edge, x = " .. r.x) end
                        if r.button.h < 44 then fail(tag .. ": a cell is under 44 px tall: " .. r.button.h) end
                        if r.gearCell and r.gearCell.h < 44 then fail(tag .. ": the gear cell is under 44 px") end
                        if r.y + r.h > h + 1e-6 or r.x + r.w > w then fail(tag .. ": the column leaves the canvas") end
                        for i, p in r.positions do
                            if p.y + r.button.h > r.h + 1e-6 then fail(tag .. ": cell " .. i .. " leaves the rail") end
                        end
                        if not TouchLayout.railFits(l, w, h) then fail(tag .. ": the column touches another HUD piece") end
                        local bar = TouchLayout.rendered(l.sizeBar)
                        if math.abs(bar.y - m) > 1e-6 then fail(tag .. ": the SIZE bar is not at the top margin: " .. bar.y) end
                    end
                end
            end
        end
    end
end

-- the picture: 1274 x 481, mouse, in a run and at home, with and without words
for _, case in {{false, 6}, {false, 2}, {true, 5}, {true, 1}} do
    local l = lay(1274, 481, false, case[2], case[1], false)
    if l.rail.column ~= true then fail("1274x481 case " .. tostring(case[1]) .. "/" .. case[2] .. " is not a column") end
end
do -- the six buttons at home: six cells, none cut off
    local l = lay(1274, 481, false, 6, false, true)
    if l.rail.column ~= true or #l.rail.positions ~= 6 then fail("1274x481 at home: not six buttons in a column") end
    local last = l.rail.positions[6]
    if last and l.rail.y + last.y + l.rail.button.h > 481 - m then fail("1274x481 at home: the sixth button is cut off") end
end

-- unchanged: a touch phone and a narrow mouse window keep the top row
for _, w in {667, 740, 844, 899} do
    if lay(w, 390, false, 6, false, false).rail.column == true then fail("narrow mouse window " .. w .. " got a column") end
end
for _, size in {{1274, 481}, {844, 390}, {932, 430}} do
    if lay(size[1], size[2], true, 6, false, false).rail.column == true then fail("touch " .. size[1] .. "x" .. size[2] .. " got a column") end
end

if #failures > 0 then
    print(table.concat(failures, "\n"))
    error("rail column check failed")
end
print(string.format("rail column passed: %d layouts checked, %d columns on the left edge (every cell 44 px or more, clear of every HUD piece, SIZE bar at the top), touch and narrow windows keep the top row", checked, columns))
'''


def script(replacements=None):
    replacements = replacements or {}
    return ('local Config = ' + wrapped('src/shared/Config.luau') + '\n'
            + 'local PhoneScale = ' + wrapped('src/shared/PhoneScale.luau') + '\n'
            + 'local TouchLayout = (function()\nlocal script = {Parent = {Config = "Config", PhoneScale = "PhoneScale"}}\n'
            + 'local require = function(name) if name == "PhoneScale" then return PhoneScale end return Config end\n'
            + 'return ' + wrapped('src/shared/TouchLayout.luau', replacements.get('TouchLayout', ())) + '\nend)()\n'
            + LUAU)


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify_rail_column.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


TL = 'TouchLayout'
MUTANTS = {
    'the column never happens (the old top row at 1274 x 481)': {TL: [('minWidth = 900,', 'minWidth = 99999,')]},
    'cells are 30 px tall': {TL: [('narrowW = 96, cellH = 44,', 'narrowW = 96, cellH = 30,'), ('math.max(target, R.cellH)', 'R.cellH')]},
    'the column is allowed on a touch phone': {TL: [('if not params.touch and width >= TouchLayout.RAILCOLUMN.minWidth then', 'if width >= TouchLayout.RAILCOLUMN.minWidth then')]},
    'the SIZE bar stays under a rail that is not there': {TL: [('(if leftColumn then m else rail.y + rail.h * rail.scale + 4)', '(rail.y + rail.h * rail.scale + 4)')]},
    'the column ignores the room above Tell us! and Admin': {TL: [('if y0 + railH <= height - m - R.bottomReserve then', 'if true then')]},
    'the column starts at the top (over the egg plate)': {TL: [('local y0 = hud.y + hud.h * hud.scale + 2 + 20 + 22 + 2', 'local y0 = m')]},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    result = run(args.runner, script())
    print(result.stdout, end='')
    if result.returncode or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            assert run(args.runner, script(replacements)).returncode != 0, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
    print('Rail column passed: layout sweep, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
