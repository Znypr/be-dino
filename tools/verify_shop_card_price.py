#!/usr/bin/env python3
"""BD-1118 / BD-1144 (docs/202 R3, docs/213): the Aura and Trail shop card with the PRICE ON THE BUTTON (Config.ShopCardPriceButtonEnabled).
Runs the REAL ShopScreens, ShopCards, ShopCard, ShopPreview, ShopCardState, RarityWord, ModalCompact and PhoneScale in the geometry mock of
tools/menu_layout_smoke.luau (tools/shop_card_price_smoke.luau) at the 12 window sizes of the small-window check, mouse and touch, and checks
rectangles, words and what a tap does (the price only opens the confirm page; nothing is sent before BUY there; Info opens a read-only page).
The mutants put each defect back and the smoke must fail. NOT Studio evidence: nobody saw a pixel (the Studio look is its own row).
Usage: python tools/verify_shop_card_price.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import text_style_floors as tf  # noqa: E402

BODY = 'tools/shop_card_price_smoke.luau'
EXTRA = {'RarityWord': 'src/shared/RarityWord.luau', 'UIFormat': 'src/shared/UIFormat.luau'}


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


MUTANTS = {
    'the flag is ignored (the old card draws with the flag on)': {
        'ShopCards': [('if MainConfig.ShopCardPriceButtonEnabled == true then return Cards.buildPrice(ui, parent, spec) end', '')]},
    'the flag is on in the source': {'Config': [('ShopCardPriceButtonEnabled = false,', 'ShopCardPriceButtonEnabled = true,')]},
    'the button says BUY, not the price': {
        'ShopPreview': [('else button = {text = item.price .. " Crystals", tone = "buy", active = true} end', 'else button = {text = "BUY", tone = "buy", active = true} end')]},
    'the equipped card says EQUIP': {'ShopPreview': [('if data.equipped then button = {text = "UNEQUIP", tone = "unequip", active = true}', 'if data.equipped then button = {text = "EQUIP", tone = "unequip", active = true}')]},
    'a locked trail shows its price on the button': {
        'ShopPreview': [('elseif data.kind == State.Locked then button = {text = data.buttonText, tone = "locked", active = true}', 'elseif data.kind == State.Locked then button = {text = item.price .. " Crystals", tone = "locked", active = true}')]},
    'the locked and sold-out button is green': {
        'ShopCards': [('elseif tone == "unequip" then C.card else ShopCard.SoldOutColor', 'elseif tone == "unequip" then C.card else C.accent')]},
    'the Info button is 36 design px whatever the scale (27 px on a small window)': {'ShopCards': [('local infoH = math.max(36, math.ceil(P.Touch / scale))', 'local infoH = 36')]},
    'the stage stops at half the card': {'ShopCards': [('local previewH = spec.buyY - 6 - previewY', 'local previewH = math.floor(spec.height / 2) - previewY')]},
    'the stage runs under the button': {'ShopCards': [('local previewH = spec.buyY - 6 - previewY', 'local previewH = spec.buyY + 20 - previewY')]},
    'the benefit band is empty': {'ShopCards': [('ui.label(band, data.benefit, 6, 0,', 'ui.label(band, "", 6, 0,')]},
    'the price caption comes back under the stage': {
        'ShopCards': [('    if data.equipped then equippedRing(card) end\n    return card, data\nend\n\n-- spec: {kind="trail"|"aura", item, owned, equipped, level, x, y, height, buyY, targetHeight, onPress, onInfo}',
                       '    ui.label(card, item.price .. " Crystals", 4, spec.buyY - 26, 256, 24, 21, C.gold)\n    if data.equipped then equippedRing(card) end\n    return card, data\nend\n\n-- spec: {kind="trail"|"aura", item, owned, equipped, level, x, y, height, buyY, targetHeight, onPress, onInfo}')]},
    'the rarity chip comes back': {
        'ShopCards': [('    local info = ui.button(card, data.info, Cards.Width - 8 - infoW, 4, infoW, infoH, C.blue, spec.onInfo)',
                       '    chip(ui, card, data.rarity, tierColour, 8, rowH, 104)\n    local info = ui.button(card, data.info, Cards.Width - 8 - infoW, 4, infoW, infoH, C.blue, spec.onInfo)')]},
    'the button is the old 240 px one': {'ShopCards': [('ui.button(card, data.button.text, 8, spec.buyY, Cards.Width - 16, spec.targetHeight, buttonColor, spec.onPress)', 'ui.button(card, data.button.text, 12, spec.buyY, 240, spec.targetHeight, buttonColor, spec.onPress)')]},
    'the name is white, not the tier colour': {'ShopCards': [('local name = ui.label(card, data.name, 8, 4, Cards.Width - 16 - infoW - 6, infoH, 25, tierColour)', 'local name = ui.label(card, data.name, 8, 4, Cards.Width - 16 - infoW - 6, infoH, 25, C.text)')]},
    'the equipped ring is gone': {'ShopCards': [('    if data.equipped then equippedRing(card) end\n    return card, data\nend\n\n-- spec:', '    return card, data\nend\n\n-- spec:')]},
    'a tap on the price buys at once (no confirm page)': {
        'ShopScreens': [('                    else chosenAura=item.id open("auraConfirm") end\n                end,\n                onInfo=', '                    else transact(if isTrail then "buyTrail" else "buyAura",item.id) end\n                end,\n                onInfo=')]},
    'Info opens the confirm page': {'ShopScreens': [('onInfo=function() chosenAura=item.id open("auraInfo") end', 'onInfo=function() chosenAura=item.id open("auraConfirm") end')]},
    'the details page has a buy button': {'ShopScreens': [('button(body,"BACK",290,math.max(lineY+12,261),510,buttonH(45),C.blue,function() open("auras") end).Name="InfoBack"', 'button(body,"BACK",290,math.max(lineY+12,261),510,buttonH(45),C.blue,function() open("auras") end).Name="InfoBack"\n        button(body,"BUY AURA",290,math.max(lineY+70,330),510,buttonH(45),C.accent,function() transact("buyAura",item.id) end)')]},
    'the details page forgets the rarity word colour': {'ShopScreens': [('            RarityWord.paintLabel(l)\n', '')]},
    'Back is a 30 px button': {'ShopScreens': [('button(body,"BACK",290,math.max(lineY+12,261),510,buttonH(45),C.blue', 'button(body,"BACK",290,math.max(lineY+12,261),510,30,C.blue')]},
    'the details page is not a shop page (open does nothing)': {'ShopScreens': [('conditionConfirm = true, auraConfirm = true, auraInfo = true,', 'conditionConfirm = true, auraConfirm = true,')]},
}


def check_sources():
    cfg = read('src/shared/Config.luau')
    assert 'ShopCardPriceButtonEnabled = false,' in cfg, 'the flag is false in source'
    cards = read('src/client/ShopCards.luau')
    assert 'function Cards.buildPrice' in cards and 'if MainConfig.ShopCardPriceButtonEnabled == true then return Cards.buildPrice(ui, parent, spec) end' in cards, 'Cards.build hands the flag-on card to buildPrice'
    assert 'pad.Name, pad.PaddingLeft, pad.Parent = "IconPad", UDim.new(0, iconSize + 14), act' in cards, 'the price text is padded away from the crystal icon'
    screens = read('src/client/ShopScreens.luau')
    assert 'auraInfo = true' in screens and 'elseif name=="auraInfo" then' in screens, 'the read-only details page exists'
    info = screens[screens.index('elseif name=="auraInfo" then'):screens.index('elseif name=="potions" then')]
    assert 'transact(' not in info and 'FireServer' not in info, 'the details page never buys'
    assert 'open("auraConfirm")' in screens, 'the price button still opens the existing confirm page'
    floors = read('tools/text_floor_smoke.luau')
    assert '"auraInfo"' in floors, 'the text-floor smoke covers the details page'
    menu = read('tools/verify_menu_layout.py')
    assert 'price=True' in menu or '(False, True)' in menu, 'the menu-layout smoke runs with the flag on too'


def run(runner, replacements=None):
    return tf.run_smoke(runner, replacements, [], BODY, EXTRA)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_sources()
    ok, out = run(args.runner)
    tail = [l for l in out.splitlines() if l.startswith(('FAIL', 'Shop card price'))]
    print('\n'.join(tail[:40]))
    if not ok:
        print(out[-1500:])
        sys.exit(1)
    if not args.no_mutants:
        from concurrent.futures import ThreadPoolExecutor  # each mutant is its own luau process: run them side by side
        names = list(MUTANTS)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: run(args.runner, MUTANTS[n]), names))
        for name, (passed, _out) in zip(names, results):
            assert not passed, 'MUTANT SURVIVED (the smoke did not notice): ' + name
            print('  mutant caught: ' + name)
    print('Shop card price passed: source guards, 12 sizes x mouse and touch x Auras and Trails, the tap paths, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
