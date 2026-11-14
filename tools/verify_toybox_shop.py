#!/usr/bin/env python3
"""BD-1178 (docs/228 board 3, docs/231): the Crystal Shop in the "Toybox" look behind Config.ToyboxUIEnabled.
Runs the REAL ShopScreens, ShopCards, ShopToyboxCard, ShopPreview, ShopCardState, RarityWord, ToyboxShop, ToyboxKit, EffectAssets, ModalCompact and
PhoneScale in the geometry mock of tools/menu_layout_smoke.luau (tools/toybox_shop_smoke.luau) at the 12 window sizes of the small-window check, mouse and
touch, and checks: flag off, ids unbound or ONE card id missing = the old card and the old CANCEL page (nothing Toybox exists); flag on with ids bound = the
tier picture of each card, name, rarity word, cream art box, slow rays only while shaftGradient is uploaded, benefit band, ONE wide button, the equipped
ring and glow, a locked Legendary as a question mark with a hint, the "Buy X?" popup with NOT NOW. Source guards: client presentation only (no server call,
no price, no save), no code-drawn art (only the allowed instance classes), the hooks in ShopCards and ShopScreens sit behind the flag and the bound card group.
The mutants put each defect back and the smoke or the guards must fail.
NOT Studio evidence: nobody saw a pixel; the card pictures are not bound yet (the lead binds them after the upload).
Usage: python tools/verify_toybox_shop.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import text_style_floors as tf  # noqa: E402

BODY = 'tools/toybox_shop_smoke.luau'
EXTRA = {
    'RarityWord': 'src/shared/RarityWord.luau', 'UIFormat': 'src/shared/UIFormat.luau', 'ToyboxShop': 'src/shared/ToyboxShop.luau',
    'ToyboxKit': 'src/shared/ToyboxKit.luau', 'EffectAssets': 'src/shared/EffectAssets.luau', 'ShopToyboxCard': 'src/client/ShopToyboxCard.luau', 'ShopToyboxPage': 'src/client/ShopToyboxPage.luau', 'PriceGroup': 'src/shared/PriceGroup.luau',
}
HOOK_CARDS = ('    local Toybox = Theme.Toybox -- BD-1178 (docs/231): the Toybox card, only while the flag is on and the six card pictures are bound\n'
              '    if Toybox and Toybox.Kit.ready(require(Shared.AssetSlots).Images, "card") then return require(script.Parent.ShopToyboxCard).build(ui, parent, spec) end\n')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def code_only(text):
    return '\n'.join(line.split('--', 1)[0] for line in text.splitlines())


MUTANTS = {
    'the card picture is always the Common one': {'ToyboxShop': [('return "toybox_card_" .. lower end', 'return "toybox_card_common" end')]},
    'an unknown rarity has no picture': {'ToyboxShop': [('    return "toybox_card_common"\nend\n\n-- A locked Legendary', '    return "toybox_card_unknown"\nend\n\n-- A locked Legendary')]},
    'every locked card is a question mark': {'ToyboxShop': [('return tone == "locked" and (rarity == "Legendary" or rarity == "Mythic")', 'return tone == "locked"')]},
    'a Legendary you own is a question mark too': {'ToyboxShop': [('return tone == "locked" and (rarity == "Legendary" or rarity == "Mythic")', 'return rarity == "Legendary" or rarity == "Mythic"')]},
    'the hint is empty': {'ToyboxShop': [('if level > 1 then return "Reach level " .. level end', 'if level > 1 then return "" end')]},
    'the rays turn under Reduce Motion': {'ToyboxShop': [('return if reduceMotion then 0 else S.RaySeconds', 'return S.RaySeconds')]},
    'the rays race (4 s a turn)': {'ToyboxShop': [('S.RaySeconds = 40', 'S.RaySeconds = 4')]},
    'the popup still says Cancel': {'ToyboxShop': [('cancel = "NOT NOW",', 'cancel = "CANCEL",')]},
    'the popup title has no name': {'ToyboxShop': [('title = "Buy " .. name .. "?",', 'title = "Buy?",')]},
    'unequip is green': {'ToyboxShop': [('if tone == "unequip" then return "card" end', 'if tone == "unequip" then return "accent" end')]},
    'the card ignores the bound pictures (old card with the flag on)': {'ShopCards': [('if Toybox and Toybox.Kit.ready(require(Shared.AssetSlots).Images, "card") then return', 'if false then return')]},
    'the card is drawn while one picture id is missing': {'ShopCards': [('if Toybox and Toybox.Kit.ready(require(Shared.AssetSlots).Images, "card") then return', 'if Toybox then return')]},
    'the card is drawn with the flag off': {'ShopCards': [('if Toybox and Toybox.Kit.ready(require(Shared.AssetSlots).Images, "card") then return', 'if require(Shared.AssetSlots).Images.toybox_card_common ~= "" then return')]},
    'the popup is Toybox with the flag off': {'ShopScreens': [('local toybox=Theme.Toybox and Theme.Toybox.Kit.ready(', 'local toybox=true and Theme.Toybox.Kit.ready(')]},
    'the popup keeps the old title': {'ShopScreens': [('if toybox then heading.Text=toybox.title end\n', '')]},
    'the popup keeps CANCEL': {'ShopScreens': [('button(body,if toybox then toybox.cancel else "CANCEL"', 'button(body,"CANCEL"')]},
    'the card shows the picture of Common whatever the item': {'ShopToyboxCard': [('picture(card, Rules.cardSlot(data.rarity))', 'picture(card, "toybox_card_common")')]},
    'the rays draw without an uploaded texture': {'ShopToyboxCard': [('    if not Effects.isRealUi(Rules.RaysKey) then return end\n', '')]},
    'one ray only': {'ShopToyboxCard': [('for i, angle in Rules.RayAngles do', 'for i, angle in {0} do')]},
    'the glow is drawn without glowPlate': {'ShopToyboxCard': [('if Effects.isRealUi(Rules.GlowKey) then', 'if true then')]},
    'the equipped ring is gone': {'ShopToyboxCard': [('ring.Name, ring.Color, ring.Thickness, ring.ApplyStrokeMode, ring.Parent = "EquippedRing", C.gold, 4, Enum.ApplyStrokeMode.Border, card', 'ring.Name = "Gone"')]},
    'the rarity word is not on the card': {'ShopToyboxCard': [('pill.Name, pill.BackgroundTransparency, pill.BackgroundColor3 = "RarityWord", 0, tone("panel")', 'pill.Name = "Other"')]},
    'the rarity word is white': {'ShopToyboxCard': [('local pill = ui.label(card, word, plan.pill.x, plan.pill.y, pillW, plan.pill.h, textPx, tierColour)', 'local pill = ui.label(card, word, plan.pill.x, plan.pill.y, pillW, plan.pill.h, textPx, Color3.new(1, 1, 1))')]},
    'the art box runs under the button': {'ShopToyboxCard': [('local plan = Rules.layout(W, spec.height, spec.targetHeight, scale)', 'local plan = Rules.layout(W, spec.height + 60, spec.targetHeight, scale)')]},
    'the art box is not clipped to the card (no ArtBox)': {'ShopToyboxCard': [('art.Name, art.ClipsDescendants = "ArtBox", true', 'art.Name = "Box2"')]},
    'the benefit band is empty': {'ShopToyboxCard': [('local words = if mystery then Rules.hint(item) else data.benefit', 'local words = ""')]},
    'a locked Legendary still shows its picture': {'ShopToyboxCard': [('local mystery = Rules.mystery(data.rarity, buttonTone)', 'local mystery = false')]},
    'the price caption comes back': {'ShopToyboxCard': [('    -- ONE wide button\n', '    ui.label(card, item.price .. " Crystals", 4, spec.buyY - 26, 256, 24, 21, C.gold)\n    -- ONE wide button\n')]},
    'the old chip comes back': {'ShopToyboxCard': [('    -- the cream art box; a tap on it opens the read-only details page\n', '    ui.box(card, 8, 60, 90, 28, tierColour, card.ZIndex + 1).Name = "Chip_old"\n    -- the cream art box; a tap on it opens the read-only details page\n')]},
    'the button is the old 240 px one': {'ShopToyboxCard': [('plan.button.x, plan.button.y, plan.button.w, plan.button.h, colours', '12, plan.button.y, 190, plan.button.h, colours')]},
    'the price group padding is a fixed 10 px (icon over the number)': {'ShopToyboxCard': [('UDim.new(0, place.padLeft), act', 'UDim.new(0, 10), act')]},
    'the cards keep a fixed 150 px width': {'ToyboxShop': [('local cellW = math.floor((content - P.gutter * (columns - 1)) / columns)', 'local cellW = 150')]},
    'four columns on every window': {'ToyboxShop': [('    return P.minColumns\nend', '    return 4\nend')]},
    'a compact body is used at full width': {'ToyboxShop': [('return if compact then bodyWidth - 12 else bodyWidth', 'return bodyWidth')]},
    'the locked word is LEVEL': {'ToyboxShop': [('S.LockedWord = "LOCKED"', 'S.LockedWord = "LEVEL"')]},
    'the secret card shows its name': {'ShopToyboxCard': [('if mystery then Rules.MysteryName else data.name', 'data.name')]},
    'the wallet is not drawn': {'ShopScreens': [('ToyboxPage.wallet({art=art,label=label},header,mark,num("Crystals"),', 'local _skip=(function(...) end)({art=art,label=label},header,mark,num("Crystals"),')]},
    'the Styling chip is gone': {'ShopScreens': [('styling=if cosmeticTab=="auras" or cosmeticTab=="trails" then', 'styling=if false then')]},
    'the selected tab is not amber': {'ShopToyboxPage': [('b.BackgroundColor3 = if selected then AMBER else tone("panel")', 'b.BackgroundColor3 = tone("panel")')]},
    'Eggs and Crystals have no cream panel': {'ShopScreens': [('if cosmeticTab~="auras" and cosmeticTab~="trails" then ToyboxPage.panel(', 'if false then ToyboxPage.panel(')]},
    'the popup has no cream panel': {'ShopScreens': [('if onPanel then ToyboxPage.panel(body,0,', 'if false then ToyboxPage.panel(body,0,')]},
    'the aura card draws the old assembled art, not the ring': {'ShopToyboxCard': [('if type(ring) == "string" and ring ~= "" then', 'if false then')]},
    'the tab word is drawn outlined white': {'ShopToyboxPage': [('    ink(word)\n', '    word.TextColor3 = Color3.new(1, 1, 1)\n')]},
    'a tap on the price buys at once (no popup)': {'ShopScreens': [('                    else chosenAura=item.id open("auraConfirm") end\n                end,\n                onInfo=', '                    else transact(if isTrail then "buyTrail" else "buyAura",item.id) end\n                end,\n                onInfo=')]},
}


def check_sources():
    cfg = read('src/shared/Config.luau')
    assert len(re.findall(r'^    ToyboxUIEnabled = false,$', cfg, re.M)) == 1, 'the Toybox flag still ships false in Config'
    assert 'ToyboxShopEnabled' not in cfg, 'no second flag: the Crystal Shop follows ToyboxUIEnabled'
    cards = read('src/client/ShopCards.luau')
    assert cards.count(HOOK_CARDS) == 1, 'ShopCards.build hands over to ShopToyboxCard behind the flag and the bound card group (one hook line pair)'
    assert cards.index(HOOK_CARDS) < cards.index('if MainConfig.ShopCardPriceButtonEnabled == true then return Cards.buildPrice'), 'the Toybox hook comes before the price-card flag'
    assert code_only(cards).count('Toybox') == 5, 'ShopCards mentions Toybox only in its two hook lines'
    screens = read('src/client/ShopScreens.luau')
    assert screens.count('require(Shared.ToyboxShop).confirm(item.name,isTrail)') == 1 and screens.count('Theme.Toybox and Theme.Toybox.Kit.ready(require(Shared.AssetSlots).Images,"card")') == 1, 'ShopScreens asks for the popup words once, behind the flag and the bound group'
    assert code_only(screens).count('Toybox') <= 44, 'ShopScreens mentions Toybox only in the page, hint, wallet, panel, popup and (BD-1205) Potion Shop lines'
    for line in code_only(screens).splitlines():
        if 'Toybox' in line:
            for needle in ('FireServer', 'transact(', 'shopAction'):
                assert needle not in line, 'a Toybox line of ShopScreens sends or buys: ' + line.strip()
    assert screens.count('ToyboxPage.active()') == 2, 'the page asks ShopToyboxPage.active() (flag and bound card group) in the shop and in the popup'
    shop = code_only(read('src/shared/ToyboxShop.luau'))
    for needle in ('game', 'Instance', 'TweenService', 'task.', 'os.', 'tick(', 'math.random', 'require(', 'Enum.', 'Color3', 'UDim', 'FireServer'):
        assert needle not in shop, 'ToyboxShop is pure (no engine, clock, RNG or server): ' + needle
    card = code_only(read('src/client/ShopToyboxCard.luau'))
    page = code_only(read('src/client/ShopToyboxPage.luau'))
    for source, label in ((card, 'ShopToyboxCard'), (page, 'ShopToyboxPage')):
        for needle in ('FireServer', 'InvokeServer', 'RemoteEvent', 'RemoteFunction', 'DataStore', 'price =', '.price ='):
            assert needle not in source, label + ' is presentation only: ' + needle
    assert card.count('Instance.new("Frame")') == 1, 'the one Frame of the card is the ray fan (a rotating holder), nothing else is built from frames'
    made = set(re.findall(r'Instance\.new\("(\w+)"\)', card))
    assert made == {'ImageLabel', 'Frame', 'UICorner', 'UIStroke', 'UIPadding', 'UIGradient', 'TextButton'}, 'ShopToyboxCard draws no art itself (pictures, one ray holder, flat cream boxes and the art tap only): %s' % sorted(made)
    made = set(re.findall(r'Instance\.new\("(\w+)"\)', page))
    assert made == {'Frame', 'TextButton', 'TextLabel', 'ScrollingFrame', 'UICorner', 'UIStroke'}, 'ShopToyboxPage draws flat cream boxes and chips only (no picture): %s' % sorted(made)
    assert 'ImageLabel' not in page and 'rbxassetid' not in page, 'the page draws no picture itself'
    assert 'Images' in card and 'Kit.image(Slots.Images' in card, 'the card picture id is read from AssetSlots.Images (never an invented id)'
    assert not re.search(r'rbxassetid://\d', read('src/client/ShopToyboxCard.luau') + read('src/client/ShopToyboxPage.luau') + read('src/shared/ToyboxShop.luau')), 'no asset id is written in the new files'
    slots = read('src/shared/AssetSlots.luau')
    for rarity in ('common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic'):
        assert re.search(r'toybox_card_%s = "(rbxassetid://\d+)?",' % rarity, slots), 'AssetSlots has the slot toybox_card_' + rarity
    ci = read('.github/workflows/build-generated-place.yml')
    assert 'python tools/verify_toybox_shop.py --runner /tmp/luau/luau' in ci, 'CI runs this verifier'
    for name in ('ShopToyboxCard', 'ToyboxShop'):
        assert (ROOT / ('src/client/%s.luau' % name if name == 'ShopToyboxCard' else 'src/shared/%s.luau' % name)).exists(), name


def run(runner, replacements=None):
    source = tf.build(replacements, [], BODY, EXTRA, False)
    result = tf.sw.run(runner, source)
    return result.returncode == 0 and 'passed' in result.stdout, result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_sources()
    ok, out = run(args.runner)
    tail = [l for l in out.splitlines() if l.startswith(('FAIL', 'Toybox shop'))]
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
    print('Toybox shop passed: source guards, 12 sizes x mouse and touch x Auras and Trails, the old card when the flag is off or an id is missing, '
          'the question mark, the Buy X? popup, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
