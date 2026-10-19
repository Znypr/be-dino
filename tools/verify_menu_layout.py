#!/usr/bin/env python3
"""BD-1101 / BD-1102 / BD-1103 (docs/201): the shop tab row can be tapped at every window size, toasts never cover the rail or the top of an open menu,
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
    'Toasts': 'src/client/Toasts.luau',
    'RailRun': 'src/client/RailRun.luau',
    'ClassRow': 'src/client/ClassRow.luau',
    'ClassBadge': 'src/shared/ClassBadge.luau',
    'ClassInfo': 'src/shared/ClassInfo.luau',
    'ClassMovement': 'src/shared/ClassMovement.luau',
    'IndexProgress': 'src/shared/IndexProgress.luau',
    'CombatConfig': 'src/shared/CombatConfig.luau',
    'ToastSlot': 'src/shared/ToastSlot.luau',
    'SettingsMenu': 'src/client/SettingsMenu.luau',
    'SettingsModel': 'src/shared/SettingsModel.luau',
    'AudioMixer': 'src/shared/AudioMixer.luau',
})


def build(replacements=None, words=False):
    source = sw.build_script(replacements, HARNESS, MODULES)
    if words:  # BD-1116: the same world with Config.HudRailWordsEnabled on (the six-button rail checks of section 5 are skipped: tools/verify_rail_words.py has the word rail's own)
        assert 'local RAIL_WORDS = false' in source
        source = source.replace('local RAIL_WORDS = false', 'local RAIL_WORDS = true', 1)
    return source


MUTANTS = {
    # BD-1132: the Settings tabs at a small size (docs/205 picture 438)
    'Settings controls ignore the drawn scale (they are 48 design px, so 27 px: the floor pass grows them into each other)': {
        'SettingsMenu': [('BTN = math.max(48, math.ceil(44 / scale))', 'BTN = 48')],
    },
    'the Settings row pitch is 56 design px whatever the scale': {
        'SettingsMenu': [('ROW = BTN + 8', 'ROW = 56')],
    },
    'the first Settings row starts at 64 whatever the scale (it touches the tab row)': {
        'SettingsMenu': [('TOP = BTN + 16', 'TOP = 64')],
    },
    'the Settings tab row is 48 design px high whatever the scale': {
        'SettingsMenu': [('(i - 1) * 209, 0, 197, BTN,', '(i - 1) * 209, 0, 197, 48,')],
    },
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
    # BD-1102: toasts over the rail and over the top of an open menu
    'the toast stack ignores the rail (it lies over the rail buttons)': {
        'Toasts': [('local rail=gui:GetAttribute("RailRect") :: Rect?', 'local rail=nil :: Rect?')],
    },
    'the toast stack never drops under a blocker': {
        'ToastSlot': [('for _, b in p.keepClear do if b.y + b.h + Slot.Gap > Slot.RunY then table.insert(ys, b.y + b.h + Slot.Gap) end end', ''), ('for _, b in p.keepClear do lowest = math.max(lowest, b.y + b.h + Slot.Gap) end', '')],
    },
    'with a menu open the toast takes the top of the menu again (y 4)': {
        'ToastSlot': [('if Slot.MenuY <= clearAbove then', 'if true then'),
                      ('            if onScreen(r) and not hitsAny(r, p.keepClear) then\n                return {x = xOff, y = Slot.MenuY,', '            if onScreen(r) then\n                return {x = xOff, y = Slot.MenuY,')],
    },
    'with a menu open the whole stack of three shows': {
        'Toasts': [('    if oneCard then shown={shown[#shown]} end', '')],
    },
    'a toast along the bottom edge takes the tap (the menu under it cannot be pressed)': {
        'Toasts': [('for _,slot in toastCards do slot.tap.Active=not passThrough end', 'for _,slot in toastCards do slot.tap.Active=true end')],
    },
    # BD-1099: class icons
    'the class icon sits on the dino name (top of the card)': {
        'ClassRow': [('return M.badge(card, id, 8, heroY + 2, not compact, card.ZIndex + 8)', 'return M.badge(card, id, 8, 2, not compact, card.ZIndex + 8)')],
    },
    'the class icon hides behind the picture': {
        'ClassRow': [('return M.badge(card, id, 8, heroY + 2, not compact, card.ZIndex + 8)', 'return M.badge(card, id, 8, heroY + 2, not compact, 1)')],
    },
    'the details list gets a second class row each time it is filled': {
        'ClassRow': [('    if old then old:Destroy() end', '')],
    },
    # BD-1105: the "At home" buttons in a run
    'the "At home" buttons stay shown in a run': {
        'HubTravelClientRules': [('Rules.HideDimmedInRun = true', 'Rules.HideDimmedInRun = false')],
    },
    'a run also hides POTIONS and SETTINGS': {
        'HubTravelClientRules': [('return Rules.HideDimmedInRun == true and Rules.dimmed(destination, caveHub, runState)', 'return Rules.HideDimmedInRun == true and caveHub == true and Rules.inRun(runState)')],
    },
    'the hub hides the buttons too (hub state not checked)': {
        'HubTravelClientRules': [('return Rules.HideDimmedInRun == true and Rules.dimmed(destination, caveHub, runState)', 'return Rules.HideDimmedInRun == true and Rules.RunDimmed[destination] == true')],
    },
    'the rail keeps the six-button slots in a run (a gap between POTIONS and SETTINGS and the top)': {
        'RailRun': [('return positions[math.max(rank, 1)]', 'return positions[i]')],
    },
    'the rail is laid out for six buttons in a run': {
        'RailRun': [('if not M.hidden(b) and not M.isGear(b) then n += 1 end', 'n += 1')],
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    for words in (False, True):
        result = sw.run(args.runner, build(words=words))
        print(('[rail with words] ' if words else '') + result.stdout, end='')
        if result.returncode != 0 or 'passed' not in result.stdout:
            print(result.stderr)
            sys.exit(result.returncode or 1)
    if not args.no_mutants:
        from concurrent.futures import ThreadPoolExecutor  # each mutant is its own luau process: run them side by side
        names = list(MUTANTS)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: sw.run(args.runner, build(MUTANTS[n])), names))
        for name, result in zip(names, results):
            assert result.returncode != 0, 'MUTANT SURVIVED (the smoke did not notice): ' + name
            print('  mutant caught: ' + name)
    print('Menu layout passed, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
