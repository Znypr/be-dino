#!/usr/bin/env python3
"""BD-1019 (docs/181): close paths. Owner bug 2026-10-18: "when hatching the egg, pressing X doesnt work", and a tap outside the hatching screen
did nothing either. Root cause: the hatch tap catcher was a full-screen button above the whole menu, so X, the dark backdrop and the end
buttons (DONE / TRY AGAIN) never got a tap. This verifier proves it cannot come back, offline, with the pinned Luau runtime:

1. SMOKE: tools/close_paths_smoke.luau runs the REAL hatch screen (src/client/HatchSequence.luau) and the REAL helper (src/client/ModalClose.luau,
   src/shared/ModalCloseRules.luau) in a mock GUI that has geometry and Roblox's Sibling ZIndex rules. Every tap goes to whatever the hit test says
   gets it. It checks that X, the dark backdrop, DONE / TRY AGAIN and "Skip the rest" are reachable at every moment of the hatch on four screen
   shapes (with and without Reduce Motion), what a backdrop tap does at each moment, that closing never advances or claims an egg, that the abort
   is reported exactly once and that input is released.
2. MUTANTS: the smoke must FAIL when the old bug is put back (a full-screen catcher; a catcher that starts at the top of the card).
3. SOURCE GUARDS: Bootstrap routes the backdrop through ModalClose.outsideTap, Escape and gamepad B close the open menu (and only an open one), the hatch
   screen passes its header and an abort hook, the Fusion menu closes on the backdrop and on B, and every full-screen button in src/client is on a reviewed list.
Not Studio evidence: nothing here shows a tap on a phone, a gamepad, or the real layout. Usage: python tools/verify_close_paths.py --runner luau.exe
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

MODULES = {
    'ModalCloseRules': 'src/shared/ModalCloseRules.luau',
    'HatchTimeline': 'src/shared/HatchTimeline.luau',
    'RevealSkip': 'src/shared/RevealSkip.luau',
    'HatchV2Plan': 'src/shared/HatchV2Plan.luau',
    'FtueP1': 'src/shared/FtueP1.luau',
    'HatchFxPlan': 'src/shared/HatchFxPlan.luau',
    'FxRecipes': 'src/shared/FxRecipes.luau',
    'EggGenetics': 'src/shared/EggGenetics.luau',
    'ProgressionConfig': 'src/shared/ProgressionConfig.luau',
    'Config': 'src/shared/Config.luau',
    'HatchV2Assets': 'src/shared/HatchV2Assets.luau',
    'ChipStyle': 'src/shared/ChipStyle.luau',
    'ModalClose': 'src/client/ModalClose.luau',
    'HatchSequence': 'src/client/HatchSequence.luau',
}

# Every full-screen button / Active frame in src/client was reviewed for BD-1019. (file, instance name or variable) -> why it cannot cover a close control.
# A NEW full-screen button must be reviewed and added here, with the reason.
FULL_SCREEN_REVIEWED = {
    ('Bootstrap.client.luau', 'shade'): 'ModalScrim (ZIndex 20): the menu itself; its panel and X sit above it',
    ('Bootstrap.client.luau', 'tap'): 'a toast card tap (inside the card)',
    ('Bootstrap.client.luau', 'crystalOpen'): 'OpenShop inside the crystal plate',
    ('DinoIndexPanels.luau', 'scrim'): 'EggPopup inside the Dino Index body (OK button + tap outside the card)',
    ('FusionMenu.luau', 'scrim'): 'FusionScrim (the Fusion menu itself; its panel and X sit above it)',
    ('HubWalkUpClient.luau', 'button'): 'the proximity prompt button inside its own prompt',
}


def build_script(replacements=None):
    parts = []
    for name, path in MODULES.items():
        source = (ROOT / path).read_text(encoding='utf-8')
        for old, new in (replacements or {}).get(name, []):
            assert old in source, 'mutant target missing in %s: %s' % (name, old)
            source = source.replace(old, new)
        parts.append(name + '=function(script, require)\n' + source + '\nend,\n')
    harness = (ROOT / 'tools/close_paths_smoke.luau').read_text(encoding='utf-8')
    assert harness.count('MODULE_SOURCES') == 2
    return harness.replace('local sources = MODULE_SOURCES', 'local sources = {\n' + ''.join(parts) + '}')


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'close_paths_smoke.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


# The old bug, and a second way to lose X: the catcher starts at the top of the card (covers the header strip where X lives).
MUTANTS = {
    'old full-screen catcher above the whole menu': {
        'ModalClose': [('overlay.Size, overlay.ZIndex, overlay.Visible, overlay.Parent = UDim2.fromOffset(Rules.MinTarget, Rules.MinTarget), 46, false, gui',
                        'overlay.Size, overlay.ZIndex, overlay.Visible, overlay.Parent = UDim2.fromScale(1, 1), 46, true, gui'),
                       ('        if x ~= lx or y ~= ly or zone.w ~= lw or zone.h ~= lh then', '        if false then')],
    },
    'catcher starts at the top of the card (covers X)': {
        'ModalCloseRules': [('local top = math.max(panel.y, headerBottom)', 'local top = panel.y')],
    },
    'catcher ignores the end-button row (covers DONE / TRY AGAIN)': {
        'ModalCloseRules': [('if endRowTop ~= nil then bottom', 'if false then bottom')],
    },
    'backdrop always closes (no moment rules)': {
        'ModalCloseRules': [('    if pending then return "ignore" end\n    if readySince ~= nil then', '    if true then return "close" end\n    if readySince ~= nil then')],
    },
    'backdrop never closes': {
        'ModalCloseRules': [('return if readySince >= Rules.ReadyGrace then "close" else "ignore"', 'return "ignore"')],
    },
    'catcher offset taken from gui.AbsolutePosition (breaks under a ScreenGui inset)': {
        'ModalClose': [('local origin = layer.AbsolutePosition', 'local origin = gui.AbsolutePosition')],
    },
    'catcher stays after finish': {
        'ModalClose': [('        if overlay.Parent then overlay:Destroy() end\n        if layer.Parent then layer:Destroy() end', '        if layer.Parent then layer:Destroy() end')],
    },
}


def check_mutants(runner):
    for name, replacements in MUTANTS.items():
        result = run(runner, build_script(replacements))
        assert result.returncode != 0, 'MUTANT SURVIVED (the smoke did not notice): ' + name
        print('  mutant caught: ' + name)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_sources():
    boot = read('src/client/Bootstrap.client.luau')
    assert 'shade.Activated:Connect(function() if require(script.Parent.ModalClose).outsideTap() then close() end end)' in boot, \
        'the backdrop must go through ModalClose.outsideTap (the smoke mirrors this exact line)'
    assert re.search(r'KeyCode==Enum\.KeyCode\.Escape or input\.KeyCode==Enum\.KeyCode\.ButtonB\) and shade\.Visible then close\(\)', boot), \
        'Escape and gamepad B close the open menu, and only an open one (a stray close would cancel the run-end results screen)'
    assert 'header=header' in boot and 'onAbort=function()' in boot, 'the hatch screen gets the header strip and the abort hook'
    onabort = boot[boot.index('onAbort=function()'):][:200]
    assert 'skipAllReveals=false' in onabort and 'emitHatchSummary()' in onabort and 'batchReset' in onabort, 'an aborted hatch resets Skip-the-rest and keeps the summary'
    hatch = read('src/client/HatchSequence.luau')
    assert 'ModalClose.hatchZone(a.gui, a.panel, a.header, a.body)' in hatch, 'the tap catcher comes from ModalClose.hatchZone'
    assert 'UDim2.fromScale(1, 1), 46, a.gui' not in hatch and '"HatchTapCatcher"' not in hatch, 'no full-screen catcher in HatchSequence any more'
    assert 'ModalClose.setOutside(outsideFn)' in hatch and 'ModalClose.clearOutside(outsideFn)' in hatch, 'the backdrop decision is registered and cleared'
    assert 'zone.destroy()' in hatch and 'zone.step()' in hatch and 'a.onAbort' in hatch
    assert 'uiParent = layer' in hatch and 'Theme.Colors.text, 47, layer' in hatch, 'Skip the rest and the inspect hint live on the non-Active layer'
    fusion = read('src/client/FusionMenu.luau')
    assert 'scrim.Activated:Connect' in fusion and 'CloseRules.fusionOutsideCloses(state.mode)' in fusion, 'Fusion: the backdrop closes where allowed'
    assert 'Enum.KeyCode.ButtonB' in fusion, 'Fusion: gamepad B closes'
    modal = read('src/client/ModalClose.luau')
    assert 'layer.Name, layer.BackgroundTransparency, layer.BorderSizePixel, layer.Active = "HatchUiLayer", 1, 0, false' in modal, 'the layer must NOT sink taps (only the catcher button does)'


def full_screen_buttons():
    """(file, variable) for every Instance.new("TextButton") / ImageButton in src/client that is given a full-screen Size in the next few lines."""
    found = set()
    for path in sorted((ROOT / 'src' / 'client').glob('*.luau')):
        lines = path.read_text(encoding='utf-8').split('\n')
        for i, line in enumerate(lines):
            m = re.search(r'local (\w+)(?:: \w+)? *= *Instance\.new\("(TextButton|ImageButton)"\)', line)
            if not m:
                continue
            var = m.group(1)
            for follow in lines[i + 1:i + 6]:
                if re.search(r'\b%s\.Size\b' % var, follow) and re.search(r'UDim2\.fromScale\(1, ?1\)|UDim2\.new\(1, ?0, ?1, ?0\)', follow):
                    found.add((path.name, var))
    return found


def check_full_screen():
    found = full_screen_buttons()
    unknown = sorted(f for f in found if f not in FULL_SCREEN_REVIEWED)
    assert not unknown, 'a NEW full-screen button in src/client: review that it cannot cover X / the end buttons, then list it in tools/verify_close_paths.py: %s' % unknown
    print('  full-screen buttons reviewed: %d' % len(found))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_sources()
    check_full_screen()
    result = run(args.runner, build_script())
    print(result.stdout, end='')
    if result.returncode or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        check_mutants(args.runner)
    print('Close paths passed: source guards, %d full-screen buttons reviewed, smoke green, %d mutants caught' % (len(full_screen_buttons()), 0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
