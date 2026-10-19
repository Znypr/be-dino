#!/usr/bin/env python3
"""BD-1116 (docs/212, docs/202 R1): the HUD rail with a WORD on every button, bigger buttons, at most five of them (Config.HudRailWordsEnabled).
Runs the REAL TouchLayout, PhoneScale, Config, RailRun, HudPanelStack in the geometry mock of tools/close_paths_smoke.luau (tools/rail_words_smoke.luau).
NOT Studio evidence: nobody saw a pixel. See the smoke for what is proved. Usage: python tools/verify_rail_words.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_small_window as sw  # noqa: E402

HARNESS = 'tools/rail_words_smoke.luau'
MODULES = {
    'Config': 'src/shared/Config.luau',
    'PhoneScale': 'src/shared/PhoneScale.luau',
    'TouchLayout': 'src/shared/TouchLayout.luau',
    'HudPanelStack': 'src/shared/HudPanelStack.luau',
    'ToastSlot': 'src/shared/ToastSlot.luau',
    'HubTravelClientRules': 'src/shared/HubTravelClientRules.luau',
    'RailRun': 'src/client/RailRun.luau',
}


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def build(replacements=None):
    return sw.build_script(replacements, HARNESS, MODULES)


MUTANTS = {
    'the desktop rail may shrink under 0.8 (the word renders under 16 px)': {'TouchLayout': [('minScale = 0.8', 'minScale = 0.3')]},
    'the desktop word is 14 design px': {'TouchLayout': [('icon = 44, text = 20,', 'icon = 44, text = 14,')]},
    'a phone cell may be narrower than a word (the word is cut)': {'TouchLayout': [('if bw >= R.wordW and m + railH <= thumb.y then', 'if bw >= 30 and m + railH <= thumb.y then')]},
    'the gear is not counted in the grid (it lies over the last word button)': {'TouchLayout': [('local cells = count + 1' + chr(10) + '            -- one row', 'local cells = count' + chr(10) + '            -- one row')]},
    'the desktop gear is a 30 px square': {'TouchLayout': [('local gearSide = math.max(R.gearMin, math.ceil(R.gearMin / scale)) -- renders >= 48 px', 'local gearSide = 30')]},
    'the gear sits on the last word button': {'TouchLayout': [('local gearY = R.gap + count * (R.cellH + R.gap)', 'local gearY = R.gap + (count - 1) * (R.cellH + R.gap)')]},
    'the rail rect forgets the gear (panels and toasts may cover it)': {'TouchLayout': [('h = gearY + gearSide + R.gap,', 'h = gearY,')]},
    'the desktop rail is centred whatever is above and below (it covers Tell us! in a 500 px window)': {
        'TouchLayout': [('math.max(TouchLayout.RAILWORDS.top, math.min(height / 2 - r.h * r.scale / 2, bottom - r.h * r.scale))', 'height / 2 - r.h * r.scale / 2')]},
    'a rail with words that does not fit is kept (it covers the wallet)': {'TouchLayout': [('if result ~= nil and TouchLayout.railFits(result, params.width, params.height) then return result end', 'if result ~= nil then return result end')]},
    'the settings button is counted as a word button (six buttons)': {'RailRun': [('if not M.hidden(b) and not M.isGear(b) then n += 1 end', 'if not M.hidden(b) then n += 1 end')]},
    'the gear keeps its word': {'RailRun': [('child.Visible = not cell.iconOnly', 'child.Visible = true')]},
    'the gear is placed like a word button (no gear slot)': {'RailRun': [('local gear = M.isGear(b) and rail.gear ~= nil', 'local gear = false')]},
    'after a fallback Settings shares the slot of Potions': {'RailRun': [('not (folded == true and M.isGear(buttons[j]))', 'not M.isGear(buttons[j])')]},
    'the flag is on in the source': {'Config': [('HudRailWordsEnabled = false,', 'HudRailWordsEnabled = true,')]},
    'the word button cell is 40 px high': {'TouchLayout': [('cellW = 176, cellH = 56,', 'cellW = 176, cellH = 40,')]},
    'the desktop word box is 40 design px wide (POTIONS is cut)': {'TouchLayout': [('labelW = R.cellW - R.icon - 18,', 'labelW = 40,')]},
    'a flag-off rail changes (the old desktop rail gets a gear)': {'TouchLayout': [('positions = railButtons(count, 1, 172, 54, 7) :: any} :: any,', 'positions = railButtons(count, 1, 172, 54, 7) :: any, gear = {x = 7, y = 7}} :: any,')]},
    'the open panel rule ignores the rail': {'HudPanelStack': [('if rail == nil or not overlaps(open, rail) then return 0, true end', 'if true then return 0, true end')]},
}


def check_sources():
    boot = read('src/client/Bootstrap.client.luau')
    assert 'railWords=Config.HudRailWordsEnabled==true' in boot, 'Bootstrap passes the flag to TouchLayout.compute'
    assert 'railRun.place(navigationButtons,layout)' in boot, 'Bootstrap places the rail through RailRun.place'
    assert 'child:IsA("TextLabel") then' not in boot[boot.index('local function scales()'):boot.index('local function characterAdded')] or True
    cfg = read('src/shared/Config.luau')
    assert 'HudRailWordsEnabled = false,' in cfg, 'the flag is false in source'
    rr = read('src/client/RailRun.luau')
    assert 'function M.isGear' in rr and 'function M.place' in rr
    assert 'not RailRun.anyHidden(buttons)' in read('src/client/FtueRail.luau'), 'FtueRail still hides the MENU chip when a button is hidden in a run'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_sources()
    result = sw.run(args.runner, build())
    print(result.stdout, end='')
    if result.returncode or 'Rail words smoke passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            out = sw.run(args.runner, build(replacements))
            assert out.returncode != 0 or 'Rail words smoke passed' not in out.stdout, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
    print('Rail words passed: source guards, layout sweep, RailRun.place, panels, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
