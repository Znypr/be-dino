#!/usr/bin/env python3
"""BD-1192 (docs/234, polish finding P-9283ac): the crystal icon and the price on a shop button never overlap and are centred as ONE group.

Studio at 1274 x 481 showed "3700 Crystals" and "470 Crystals" running into the icon on the Aura cards. The icon sat at a fixed spot while the button centred the text
alone. PriceGroup (src/shared/PriceGroup.luau) now places icon + gap + text as one group from the measured text width, steps the text size down when the group is
wider than the button, and UIFormat.number writes "3,700". This check runs the REAL PriceGroup and UIFormat in the pinned Luau runtime:
 * UIFormat.number: 0, 60, 470, 999, 1000, 3700, 12345, 1000000 -> "0" "60" "470" "999" "1,000" "3,700" "12,345" "1,000,000";
 * for every button width the shops use (design 248 px: aura and trail cards, 200 to 400 for other cards), every icon size (24 to 40), every price of the aura and
   trail catalogue (read from ProgressionConfig) written as the button writes it, and text-width estimates from .5 to .75 em per character (a real font is in between):
   the icon starts at or after the margin; the text starts at least `gap` px after the icon ends (never overlapping); the text ends before the margin on the right
   when the layout says it fits; the group is centred (left space = right space) when it fits; the size never goes under 14 px; a group that cannot fit even at 14 px
   is reported as not fitting (and the shops use none, the check counts them).
 * the source: ShopCards measures with TextService (with an estimate when it is not there) and places the icon at group.iconX.
The mutants put each defect back and the check must fail. NOT Studio evidence: no real font was measured here (a Studio look at 1274 x 481 is the follow-up).
Usage: python tools/verify_price_group.py --runner luau.exe [--no-mutants]
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
local failures = {}
local function check(ok, msg) if not ok and #failures < 12 then table.insert(failures, msg) end end

for _, case in {{0, "0"}, {60, "60"}, {470, "470"}, {999, "999"}, {1000, "1,000"}, {3700, "3,700"}, {12345, "12,345"}, {1000000, "1,000,000"}} do
    check(UIFormat.number(case[1]) == case[2], "UIFormat.number(" .. case[1] .. ") = " .. UIFormat.number(case[1]))
end

local prices = {}
for _, list in {ProgressionConfig.Auras, ProgressionConfig.Trails} do
    for _, item in list do prices[#prices + 1] = item.price end
end
prices[#prices + 1] = 3700 prices[#prices + 1] = 470 prices[#prices + 1] = 12500
check(#prices > 5, "the catalogue prices were read")

local gapPx, margin, cases, tight = 8, 8, 0, 0
for _, buttonW in {200, 248, 264, 300, 400} do
    for iconSize = 24, 40, 4 do
        for _, price in prices do
            local text = UIFormat.number(price) .. " Crystals"
            for _, em in {.5, .6, .75} do
                cases += 1
                local function measure(size: number): number return #text * size * em end
                local g = PriceGroup.layout(measure, 25, 14, buttonW, iconSize, gapPx, margin)
                local tag = string.format("w%d icon%d '%s' em%.2f", buttonW, iconSize, text, em)
                local textW = measure(g.size)
                check(g.size >= 14 and g.size <= 25, tag .. ": size out of range " .. g.size)
                check(g.iconX >= margin - 1e-6, tag .. ": the icon starts left of the margin")
                check(g.textLeft >= g.iconX + iconSize + gapPx - 1e-6, tag .. ": the text touches the icon")
                if g.fits then
                    check(g.textLeft + textW <= buttonW - margin + 1e-6, tag .. ": the text runs out of the button")
                    local left, right = g.iconX, buttonW - (g.iconX + g.groupW)
                    check(math.abs(left - right) < 1e-6, tag .. ": the group is not centred (" .. left .. " / " .. right .. ")")
                else
                    tight += 1
                    check(g.size == 14, tag .. ": not fitting but not at the smallest size")
                end
            end
        end
    end
end
-- the shops' own button (248 design px, icon 32, the longest catalogue price) fits at a real-font width
do
    local function measure(size: number): number return #"3,700 Crystals" * size * .6 end
    local g = PriceGroup.layout(measure, 25, 14, 248, 32, gapPx, margin)
    check(g.fits, "the shop button (248 px) fits the longest aura price")
end

if #failures > 0 then print(table.concat(failures, "\n")) error("price group check failed") end
print(string.format("price group passed: %d cases (5 widths x 5 icon sizes x %d prices x 3 font widths), %d only fit by 14 px text in the narrowest buttons; icon and price never touch, centred as one group", cases, #prices, tight))
'''


def script(replacements=None):
    replacements = replacements or {}
    return ('local UIFormat = ' + wrapped('src/shared/UIFormat.luau', replacements.get('UIFormat', ())) + '\n'
            + 'local PriceGroup = ' + wrapped('src/shared/PriceGroup.luau', replacements.get('PriceGroup', ())) + '\n'
            + 'local ProgressionConfig = ' + wrapped('src/shared/ProgressionConfig.luau') + '\n'
            + LUAU)


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify_price_group.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


def check_sources():
    cards = read('src/client/ShopCards.luau')
    assert 'GetTextSize' in cards and 'PriceGroup.layout(measure' in cards, 'ShopCards measures the price text'
    assert 'ui.art(act, "amber", group.iconX' in cards and 'UDim.new(0, group.textLeft)' in cards, 'ShopCards places the icon and the text from the group'
    assert 'iconSize + 14' not in cards, 'the fixed icon spot is gone'


PG = 'PriceGroup'
MUTANTS = {
    'the group is not centred (it starts at the margin)': {PG: [('local iconX = math.max(margin, (buttonW - groupW) / 2)', 'local iconX = margin')]},
    'the text starts on the icon (no gap)': {PG: [('textLeft = iconX + iconSize + gap,', 'textLeft = iconX + iconSize,')]},
    'the text never steps down': {PG: [('if groupW <= room or size <= minSize then', 'if true then')]},
    'the text steps down under 14 px': {PG: [('size <= minSize', 'size <= 8')]},
    'the icon may start left of the margin': {PG: [('local iconX = math.max(margin, (buttonW - groupW) / 2)', 'local iconX = (buttonW - groupW) / 2')]},
    'no thousands comma': {'UIFormat': [('    local out=text:reverse():gsub("(%d%d%d)","%1,"):reverse()', '    local out=text')]},
}


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
    print('Price group passed: UIFormat.number, PriceGroup sweep, source wiring, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
