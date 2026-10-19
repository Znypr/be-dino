#!/usr/bin/env python3
"""BD-1067 (docs/195): the Eggs screen and the hatch card fit a SMALL window. Owner/QA round 4 (pictures 268 to 271): in a small Studio window (848 x 423
usable) the Eggs header "Nests 5/5" sat behind the nest slots, OPEN EGG was half cut, the hatch card was pushed down and cut, the dino reveal lost its
tap line. This verifier runs the REAL ModalCompact, PhoneScale, EggsScreen and HatchSequence in the geometry mock of tools/close_paths_smoke.luau
(tools/small_window_smoke.luau) at the window sizes in the row (848 x 423, 848 x 481, 844 x 390, 667 x 375, 500 x 465 and more, with and without
the top bar) and checks the absolute rectangles: nothing is cut, nothing overlaps, buttons are 44 px, text is 14 px on screen.
The mutants put each old defect back and the smoke must fail. It is NOT Studio evidence: a Studio look at small sizes is still needed (BD-1067 follow-up row).
Usage: python tools/verify_small_window.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_close_paths as cp  # noqa: E402

MODULES = {
    'PhoneScale': 'src/shared/PhoneScale.luau',
    'ModalCompact': 'src/client/ModalCompact.luau',
    'EggsScreen': 'src/client/EggsScreen.luau',
    'EggsLogic': 'src/shared/EggsLogic.luau',
    'NestQueue': 'src/shared/NestQueue.luau',
    'RevealSkip': 'src/shared/RevealSkip.luau',
    'FtueP1': 'src/shared/FtueP1.luau',
    'Config': 'src/shared/Config.luau',
    'ProgressionConfig': 'src/shared/ProgressionConfig.luau',
    'ProgressionRules': 'src/shared/ProgressionRules.luau',
    'EggGenetics': 'src/shared/EggGenetics.luau',
    'UIFormat': 'src/shared/UIFormat.luau',
    'ConditionStageRules': 'src/shared/ConditionStageRules.luau',
    'MutationLook': 'src/shared/MutationLook.luau',
    'ChipStyle': 'src/shared/ChipStyle.luau',
    'RarityWord': 'src/shared/RarityWord.luau',
    'HubTravelClientRules': 'src/shared/HubTravelClientRules.luau',
    'IndexTabs': 'src/client/IndexTabs.luau',
}
MODULES.update({k: v for k, v in cp.MODULES.items() if k not in MODULES})


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def build_script(replacements=None, harness_path='tools/small_window_smoke.luau', modules=None):
    smoke = read('tools/close_paths_smoke.luau')
    marker = '-- ===== modules: REAL pure ones'
    assert marker in smoke, 'close_paths_smoke.luau lost its module marker'
    prefix = smoke[:smoke.index(marker)]
    harness = read(harness_path)
    assert '-- @@PREFIX@@' in harness and harness.count('MODULE_SOURCES') == 1
    parts = []
    for name, path in (modules or MODULES).items():
        source = read(path)
        for old, new in (replacements or {}).get(name, []):
            assert old in source, 'mutant target missing in %s: %s' % (name, old)
            source = source.replace(old, new)
        parts.append(name + '=function(script, require)\n' + source + '\nend,\n')
    harness = harness.replace('-- @@PREFIX@@', prefix)
    return harness.replace('local sources = MODULE_SOURCES', 'local sources = {\n' + ''.join(parts) + '}')


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'small_window_smoke.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


MUTANTS = {
    'a narrow moment grows buttons for good (the floor pass forgets the design height)': {
        'ModalCompact': [('local base = designValue(d, "CmBaseH", "CmH", height)', 'local base = height')],
    },
    'a narrow moment grows text for good (the floor pass forgets the design text size)': {
        'ModalCompact': [('local base = designValue(d, "CmBaseText", "CmText", size)', 'local base = size')],
    },
    'the body keeps the desktop home after the window turns compact (picture 268)': {
        'ModalCompact': [('    if lastMode ~= "compact" then', '    if false then')],
    },
    'the Eggs screen is not drawn again when the window changes size': {
        'EggsScreen': [('if h == drawnH and s == drawnScale then return end', 'do return end')],
    },
    'the Eggs header sits on the nest slots again (picture 268)': {
        'PhoneScale': [('local slotY, nestH = 30, 68', 'local slotY, nestH = 12, 68')],
    },
    'OPEN EGG hangs below the visible body again (picture 269)': {
        'PhoneScale': [('local cardH = bodyH - cardY', 'local cardH = bodyH - cardY + 70')],
    },
    'a tall small-width window ignores its extra height': {
        'EggsScreen': [('local fullH = math.max(402, bodyH)', 'local fullH = 402')],
    },
    'tag text can render under 14 px': {
        'EggsScreen': [('PhoneScale.floorText(size, bodyScale), 14, text', 'size, 14, text')],
    },
    'the hatch card is pushed 98 px down in the phone scroller (picture 270)': {
        'HatchSequence': [('local bodyCenter = home + (BODY_CENTER - BODY_HOME) * fit', 'local bodyCenter = BODY_CENTER')],
    },
    'the hatch card is not shrunk to the visible body (picture 271)': {
        'HatchSequence': [('fit = math.clamp(fit, .5, 1)', 'fit = 1')],
    },
    'the hatch effect layers stay at the desktop spot': {
        'HatchSequence': [('    placeLayers(fx, a.panel, a.body, fit) -- the effect layers sit exactly over the card (they used to assume the desktop home)', '')],
    },
    'the hatch effect layers ignore the phone scroller scale': {
        'HatchSequence': [('math.round(fit * rel * 10000) / 10000', 'fit')],
    },
    # BD-1107 (docs/200 picture 416): the ribbons, the stop tag and the class badge of the reveal card
    'a ribbon word shrinks to fit again (TextScaled, cut at the left edge, picture 416)': {
        'HatchSequence': [('WHITE, false, p.size, f.ZIndex + 1, 0, Color3.new(0, 0, 0)', 'WHITE, true, p.size, f.ZIndex + 1, 0, Color3.new(0, 0, 0)')],
    },
    'the tags are not stacked (every tag of a side sits on the same spot)': {
        'HatchTagLayout': [('        local cy = if top == nil then L.FirstCy else top + hh', '        local cy = L.FirstCy')],
    },
    'a tag reaches past the left edge of the card': {
        'HatchTagLayout': [('p.cx = if side == "left" then L.Margin + hw else L.BodyW - L.Margin - hw', 'p.cx = if side == "left" then hw - 60 else L.BodyW - L.Margin - hw')],
    },
    'a tag that does not fit its side is not moved to the other side (the stack runs into the name)': {
        'HatchTagLayout': [('            if cy2 + hh <= L.Bottom + 1e-6 then side, cy, nextY = other, cy2, next2 else ok = false end', '            ok = false')],
    },
    'a tag reaches past the right edge of the card': {
        'HatchTagLayout': [('p.cx = if side == "left" then L.Margin + hw else L.BodyW - L.Margin - hw', 'p.cx = if side == "left" then L.Margin + hw else L.BodyW + 40 - hw')],
    },
    'a long tag word is not wrapped, it is cut short': {
        'HatchTagLayout': [('local fit = TagFit.fit(item.text, roomW, {maxSize = R.textMax, minSize = floor, maxLines = 2})', 'local fit = TagFit.fit(item.text, roomW, {maxSize = R.textMax, minSize = floor, maxLines = 1})')],
    },
    'the tags are laid out for 14 design px, not 14 px on screen': {
        'TagFit': [('    return math.max(f, math.ceil(f / math.max(screenScale, TagFit.MinScale) - 1e-9))', '    return f')],
    },
    'a word is measured far too small (it runs out of its tag)': {
        'TagFit': [('    return math.ceil(math.max(em, TagFit.FlatEm * count) * size)', '    return math.ceil(0.2 * count * size)')],
    },
    'the tags are stacked with a huge gap (the last one reaches the name)': {
        'HatchTagLayout': [('L.Gap = 6 ', 'L.Gap = 70 ')],
    },
    'the name stays centred beside the class badge (the badge lies over its first letters)': {
        'HatchSequence': [('            a.nameLabel.TextXAlignment = Enum.TextXAlignment.Left', '            a.nameLabel.TextXAlignment = nameBase.align')],
    },
    'the class badge is placed for a badge a tenth as wide as it is': {
        'HatchSequence': [('            if not icon and not word then badgeW = badgeSize end', '            badgeW = 4')],
    },
    'the name box keeps its old place, so the class badge lies inside it': {
        'HatchSequence': [('            a.nameLabel.Position = UDim2.fromOffset(left + badgeW + gap, labelY)', '            a.nameLabel.Position = nameBase.pos')],
    },
    # BD-1083 (docs/197 picture 350): a tap on an Index tab closed the Index and opened Eggs
    'the rail routing looks at the position only, not at what is on top (a tap on the Patterns tab presses the rail EGGS button)': {
        'HubTravelClientRules': [(' or onBackdrop ~= true', '')],
    },
    'the backdrop answer is always yes': {
        'ModalClose': [('    return top ~= nil and M.BackdropNames[top.Name] == true', '    return true')],
    },
    'any control counts as the backdrop': {
        'ModalClose': [('    return top ~= nil and M.BackdropNames[top.Name] == true', '    return top ~= nil')],
    },
}


def check_mutants(runner):
    for name, replacements in MUTANTS.items():
        result = run(runner, build_script(replacements))
        assert result.returncode != 0, 'MUTANT SURVIVED (the smoke did not notice): ' + name
        print('  mutant caught: ' + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    result = run(args.runner, build_script())
    print(result.stdout, end='')
    if result.returncode != 0 or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        check_mutants(args.runner)
    print('Small window passed: Eggs and hatch geometry at every size, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
