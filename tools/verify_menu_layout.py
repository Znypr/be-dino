#!/usr/bin/env python3
"""BD-1101 / BD-1102 / BD-1103 (docs/200): the shop tab row can be tapped at every window size, toasts never cover the rail or the top of an open menu,
and the shop pages have no small-window slips. Studio round 6 (docs/199, pictures 361 to 379) found at 500 x 465: a tap on the TRAILS tab opened the shop
landing page, a tap on EGGS closed the shop and pressed the rail EGGS button (the rail buttons lie over the tab row); a toast lay over the whole rail row and
the top of open menus; price lines under BUY, a hint over a card row, text cut.
This verifier runs the REAL ShopScreens, Toasts, TouchLayout, ToastSlot, ModalCompact and PhoneScale in the geometry mock of tools/close_paths_smoke.luau
(tools/menu_layout_smoke.luau) at the 11 window sizes of the small-window check (both with a mouse and with touch) and checks rectangles and the mock's hit test.
The mutants put each defect back and the smoke must fail. NOT Studio evidence (BD-1104 stays the Studio re-check).
Usage: python tools/verify_menu_layout.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_small_window as sw  # noqa: E402

HARNESS = 'tools/menu_layout_smoke.luau'
MODULES = dict(sw.MODULES)
MODULES.update({
    'TouchLayout': 'src/shared/TouchLayout.luau',
    'ShopScreens': 'src/client/ShopScreens.luau',
    'ShopTiles': 'src/client/ShopTiles.luau',
    'ShopCards': 'src/client/ShopCards.luau',
    'ShopCard': 'src/client/ShopCard.luau',
    'ShopCardState': 'src/shared/ShopCardState.luau',
    'ShopPreview': 'src/shared/ShopPreview.luau',
    'ShopForDino': 'src/shared/ShopForDino.luau',
    'ShopArt': 'src/shared/ShopArt.luau',
    'ShopOdds': 'src/shared/ShopOdds.luau',
    'EggOutcomeOdds': 'src/shared/EggOutcomeOdds.luau',
    'OddsCopy': 'src/shared/OddsCopy.luau',
    'FtueRules': 'src/shared/FtueRules.luau',
    'PaidRandomGate': 'src/shared/PaidRandomGate.luau',
    'NotifyQueue': 'src/shared/NotifyQueue.luau',
    'AssetSlots': 'src/shared/AssetSlots.luau',
})


def build(replacements=None):
    return sw.build_script(replacements, HARNESS, MODULES)


MUTANTS = {
    # BD-1083 / BD-1101: a raw tap is routed to the rail button under a menu control
    'the rail routing looks at the position only, not at what is on top (a tap on a shop tab presses the rail button under it)': {
        'HubTravelClientRules': [(' or onBackdrop ~= true', '')],
    },
    'any control counts as the dark backdrop': {
        'ModalClose': [('    return top ~= nil and M.BackdropNames[top.Name] == true', '    return top ~= nil')],
    },
    # BD-1101: the tab row grew over the heading strip (picture 366 / 367)
    'the shop lays its buttons out for the panel scale, not the scale the body really renders at (a tab grows up over the heading)': {
        'ShopScreens': [('viewportScale = function() return require(script.Parent.ModalCompact).bodyScale() end', 'viewportScale = function() return require(script.Parent.ModalCompact).model().scale end')],
    },
    'a small PC window keeps the 40 px desktop tab row': {
        'ShopScreens': [('local touch=Input.TouchEnabled or require(script.Parent.ModalCompact).model().mode=="compact"', 'local touch=Input.TouchEnabled')],
    },
    # BD-1103: price line under BUY, 'Uncommo', hint over the second row, BUY touching CANCEL, text that cannot fit its box
    'the aura card is squeezed into a 402 px body in a small window (the price line sits under BUY)': {
        'ShopScreens': [('return math.max(68+56+52+targetHeight+10,bodyH-y-targetHeight-12)', 'return 402-y-targetHeight-12')],
    },
    'the rarity chip keeps its 104 px width (Uncommon is cut)': {
        'ShopCards': [('local rarityW = wide(data.chip.text, 104)', 'local rarityW = 104')],
    },
    'BUY and CANCEL touch on the aura confirm page': {
        'ShopScreens': [('button(body,"CANCEL",290,261+buyH+19,510,buttonH(45),', 'button(body,"CANCEL",290,337,510,45,')],
    },
    'BUY and CANCEL touch on the potion confirm page': {
        'ShopScreens': [('button(body,"CANCEL",290,263+buyH+18,510,buttonH(44),', 'button(body,"CANCEL",290,339,510,44,')],
    },
    'the potion card keeps 132 px in a small window': {
        'ShopScreens': [('local cardH=2+nameH+descH+leftH+2+btnH+4', 'local cardH=132')],
    },
    'the potion hint sits at the desktop place (over the second card row)': {
        'ShopScreens': [('local hintY,hintH,titleH=2*pitch-2,', 'local hintY,hintH,titleH=278,')],
    },
    'the egg chance notes keep a 28 px box (their text needs two lines)': {
        'ShopScreens': [('local nh=fitH(group.note,OddsCopy.NoteTextSize,790,28)', 'local nh=28')],
    },
    'the For-dino strip keeps 40 px (the note needs two lines)': {
        'ShopScreens': [('math.ceil(28/viewportScale())+8', '0')],
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    result = sw.run(args.runner, build())
    print(result.stdout, end='')
    if result.returncode != 0 or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            result = sw.run(args.runner, build(replacements))
            assert result.returncode != 0, 'MUTANT SURVIVED (the smoke did not notice): ' + name
            print('  mutant caught: ' + name)
    print('Menu layout passed, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
