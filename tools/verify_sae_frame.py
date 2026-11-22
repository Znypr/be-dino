#!/usr/bin/env python3
"""BD-1287 (docs/246 slice 1, owner 2026-11-21/22): the shop menu kit (client KitWindow, KitCard, KitButton, KitStrip, KitRail; numbers in
Shared/SaeFrameRules, art in Shared/ShopKit2) and the Crystal Shop landing built on it behind Config.MenusSaeFrameEnabled, to look like the
owner's APPROVED Aura Shop window.

Runs the REAL SaeFrameRules.luau and ShopKit2.luau in the pinned Luau runtime and checks, at 1280x720: the window keeps the approved shape
(w / h = 1.40), centred, from 16 % to 88 % of the screen; the header about 18.4 % of the window with the X (90 % of it, 48+ px) inside;
three cards taking about 72 % of the window, the name about 10.5 % of the card, the picture up to 55 % of the card, the strip and the
button; the tabs right of the window as icon + word, the selected one bigger. At every size: no text under 19 px, tap targets >= 44 px
(the X 48), everything inside the window / screen. featured(): buy / locked / soon / open, kid words on the buttons. ShopKit2: every
inside, slice and stud crop measured against the real PNGs, the header pieces cover the strip at its height scale with the stripes from
38 %. Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile, the rehearsal list and the
playtest manifest; ShopTiles hands the landing over only with the flag on; Bootstrap only passes its close; the landing passes only data;
the kit uses uploaded pictures only (no colour fills, no ids in code) and each kit 2 piece falls back to the Toybox piece; no Robux path.
Usage: python tools/verify_sae_frame.py --runner luau.exe"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local function near(v, lo, hi) return v >= lo and v <= hi end

-- the 720 p targets (the approved Aura Shop, a 1544x720 phone shot)
local L = R.layout(1280, 720, 3)
local w = L.window
check(near(w.w / w.h, 1.38, 1.42) and near(w.h / 720, .715, .725), "window w / h 1.40 (approved) x 72 % H at 720 p")
check(math.abs((w.x + w.w / 2) - 640) <= 1, "window centred")
check(near(w.y / 720, .155, .165) and near((w.y + w.h) / 720, .875, .885), "window from 16 % to 88 % H")
check(near(L.headerH / w.h, .175, .19) and L.close >= 48 and L.close <= L.headerH and near(L.close / L.headerH, .85, .95), "header 18.4 % of the window, the X 90 % of it")
check(near(L.cards[1].h / w.h, .68, .75), "cards about 72 % of the window height (approved 72.5 %)")
check(near(L.cardTitle / L.cards[1].h, .09, .12) and L.cardTitle >= 23, "name about 10.5 % of the card")
check(near(L.button / L.cards[1].h, .11, .135) and L.buttonText >= 24, "button about 12.3 % of the card, price 24+ px")
check(L.line and near(L.art / L.cards[1].h, .43, .55), "the strip shows and the picture is 43-55 % of the card at 720 p")
check(L.cards[1].y >= L.headerInset + L.headerH, "cards under the header")
check(R.Blur >= 12 and R.Blur <= 16 and R.Cover >= .92 and R.Cover <= .95 and R.OutlinePx == 3, "blur 12-16 px, 5-8 % overlay")
local plain, rich = R.auraLine(1.15)
check(plain == "x1.15 Growth" and string.find(rich, "x1.15</font> Growth", 1, true) ~= nil and R.auraLine(1.7) == "x1.7 Growth", "the approved aura strip words")
check(L.rarityText >= 19 and L.rarityText <= 22, "the rarity word under the name, 19-22 px")
check(L.rail.x > w.x + w.w and L.rail.selectedIcon > L.rail.icon and L.rail.labelSize >= 19, "tabs right of the window, the selected one bigger")
check(R.Title == "Crystal Shop" and R.HeaderColour == "green", "the green Crystal Shop header")
check(#R.RailTabs == 5 and R.RailTabs[1] == "featured" and R.RailTabs[5] == "potions", "tabs: Featured, Auras, Trails, Eggs, Potions")
check(R.grouped(1250) == "1,250" and R.grouped(0) == "0" and R.grouped(1234567) == "1,234,567", "whole numbers with commas")
check(R.fitSize("Meadow Glow", 400, 26) == 26 and R.fitSize("Meadow Glow", 100, 26) == 19, "names shrink to fit, never under 19 px")
for tab, line in R.Lines do check(not string.find(line, "%d"), "kid line without numbers: " .. tab) end
check(R.Lines.auras ~= nil and R.Lines.trails ~= nil and R.Lines.eggs ~= nil, "a strip line for every card")

-- the Studio canvas: 1274x423 under a 58 px top bar: from 16 % to 88 % of the 481 px SCREEN, the approved shape
local T = R.layout(1274, 423, 3, 58)
check(math.abs(T.window.y + 58 - 0.16 * 481) <= 1 and math.abs(T.window.y + T.window.h + 58 - 0.88 * 481) <= 2, "Studio canvas: 16 % to 88 % of the screen (top bar included)")
check(near(T.window.w / T.window.h, 1.38, 1.42), "Studio canvas: the approved window shape")
check(T.art >= .38 * T.cards[1].h and T.line, "Studio canvas: the strip shows, the picture is at least 38 % of the card")

-- featured: every card is an item card (picture + name); only "buy" has a price
local auras = {{id = "meadow", name = "Meadow Glow", rarity = "Common", price = 60}, {id = "tidal", name = "Tidal Halo", rarity = "Rare", price = 470}}
local trails = {{id = "white", name = "Normal White", rarity = "Common", price = 0, level = 1}, {id = "fern", name = "Fern Drift", rarity = "Common", price = 100, level = 3}, {id = "tidal", name = "Tidal Wake", rarity = "Uncommon", price = 280, level = 6}}
local f = R.featured({auras = auras, ownedAuras = {}, trails = trails, ownedTrails = {white = true}, level = 1, eggPrice = 150, eggBlocked = false})
check(f[1].tab == "auras" and f[1].state == "buy" and f[1].item.id == "meadow" and f[1].price == 60, "featured aura: the cheapest one not owned")
check(R.cardSlot(f[1]) == "toybox_card_common" and R.cardRarity(f[1]) == "Common" and R.cardTitle(f[1], "Auras") == "Meadow", "a Common aura on the grey card, titled like the approved card")
check(f[2].tab == "trails" and f[2].state == "locked" and f[2].item.id == "fern" and f[2].price == nil and R.buttonWord(f[2]) == "Level 3", "no trail to buy at level 1: the next one, Level 3, no price")
check(f[3].tab == "eggs" and f[3].state == "buy" and f[3].price == 150 and R.cardSlot(f[3]) == "toybox_card_legendary" and R.cardRarity(f[3]) == "Legendary" and R.cardTitle(f[3], "Eggs") == "Random Egg", "the egg with its price on the gold card")
f = R.featured({auras = auras, ownedAuras = {meadow = true}, trails = trails, ownedTrails = {white = true}, level = 6, eggPrice = 150, eggBlocked = true})
check(f[1].item.id == "tidal" and R.cardSlot(f[1]) == "toybox_card_rare" and R.cardRarity(f[1]) == "Rare" and f[2].item.id == "fern" and f[2].state == "buy" and R.cardTitle(f[2], "Trails") == "Fern", "skips owned items; a Rare aura on the cyan card")
check(f[3].state == "soon" and f[3].item.name == "Random Egg" and f[3].price == nil and R.buttonWord(f[3]) == "Coming soon", "egg the shop cannot sell: Coming soon, no price")
f = R.featured({auras = auras, ownedAuras = {meadow = true, tidal = true}})
check(f[1].state == "open" and f[1].item == nil and R.buttonWord(f[1]) == "OPEN" and f[3].state == "open", "all owned / no data: the category card")

-- ShopKit2: slots, card pictures, header pieces
check(K.cardSlot("Rare") == "shopkit2_card_rare" and K.cardSlot("Legendary") == "shopkit2_card_legendary" and K.cardSlot(nil) == "shopkit2_card_common" and K.cardSlot("Odd") == "shopkit2_card_common", "kit 2 card per rarity")
check(K.headerSlot("purple") == "shopkit2_header_purple" and K.headerSlot("amber") == "shopkit2_header_green" and K.buttonSlot(true) == "shopkit2_button_grey", "kit 2 header and button slots")
check(K.artSlot("auras", {id = "meadow"}) == "shopkit2_card_art_aura_meadow" and K.artSlot("trails", {id = "fern", name = "Fern Drift"}) == "shopkit2_card_art_trail_fern_drift" and K.artSlot("eggs", {}) == nil, "kit 2 card pictures by aura id / trail name")
check(K.image({shopkit2_close = "rbxassetid://123456"}, "shopkit2_close") == "rbxassetid://123456" and K.image({shopkit2_close = ""}, "shopkit2_close") == nil and K.image({toybox_close = "rbxassetid://123456"}, "toybox_close") == nil, "kit 2 ids: bound or nil, never another kit")
for _, size in {{700, 95}, {440, 64}, {260, 52}, {1000, 120}} do
    local pw, ph = size[1], size[2]
    local pieces = K.headerPieces(pw, ph)
    local x = 0
    for _, p in pieces do check(p.x == x and p.w > 0, pw .. ": header pieces side by side") x = p.x + p.w end
    check(x == pw, pw .. ": header pieces cover the strip")
    local k = ph / K.Header.h
    for _, p in pieces do if not p.tile then check(math.abs(p.w - p.cropW * k) <= 1.5, pw .. ": caps and stripes at the height scale (no stretch)") end end
end
local stripe = K.headerPieces(700, 95)[3]
check(stripe.cropX == K.Header.stripes.x and math.abs(stripe.x + (K.Header.stripes.first - K.Header.stripes.x) * 95 / 85 - 0.38 * 700) <= 2, "the first shine stripe at 38 % of the header")

-- every size: text floor, tap targets, inside the window / screen
for _, size in {{1280, 720, 0}, {1920, 1080, 0}, {1366, 768, 36}, {1024, 768, 36}, {1274, 423, 58}, {844, 390, 0}, {812, 375, 0}, {667, 375, 0}, {932, 430, 0}, {1180, 820, 36}, {740, 360, 0}} do
    local sw, sh = size[1], size[2]
    local tag = sw .. "x" .. sh
    local l = R.layout(sw, sh, 3, size[3])
    local win = l.window
    for _, t in {l.titleSize, l.cardTitle, l.buttonText, l.rail.labelSize, l.rarityText} do check(t >= 19, tag .. ": text >= 19 px") end
    if l.line then check(l.lineText >= 19, tag .. ": card line >= 19 px") end
    check(l.close >= 48 and l.close <= l.headerH, tag .. ": X >= 48 px inside the header")
    check(l.button >= 44 and l.rail.icon >= 44, tag .. ": buttons and tab icons >= 44 px")
    check(win.x >= 0 and win.y >= 0 and win.x + win.w <= sw and win.y + win.h <= sh, tag .. ": window on screen")
    for _, c in l.cards do
        check(c.x >= l.frameInset and c.y >= l.headerInset + l.headerH and c.x + c.w <= win.w - l.frameInset and c.y + c.h <= win.h - l.frameInset, tag .. ": card inside the frame")
        check(c.w >= 120, tag .. ": card wide enough for its button")
        local need = l.artTop + l.art + l.innerGap + l.button + l.edge + (if l.line then l.lineH + l.innerGap else 0)
        check(need <= c.h + 1, tag .. ": card parts fit the card")
    end
    check(l.art >= 40, tag .. ": picture at least 40 px")
    check(R.textWidth(R.Title, l.titleSize) + 16 <= win.w - l.close - 30, tag .. ": the title clear of the X")
    for _, s in l.rail.slots do
        check(s.x >= win.x + win.w and s.x + s.w <= sw, tag .. ": tabs right of the window, on screen")
        check(s.y >= 0 and s.y + s.h <= sh, tag .. ": tab on screen vertically")
    end
end
if #fails > 0 then error("sae frame FAILED:\n" .. table.concat(fails, "\n")) end
print("sae frame passed")
'''


def measure():
    """ShopKit2 rects against the real PNGs: the inside starts where the coloured face starts, the slice keeps the whole outline in the caps,
    the stud crop lies inside the coloured face."""
    import re
    from PIL import Image
    import numpy as np
    kit = read('src/shared/ShopKit2.luau')
    files = {'card': 'card-common', 'button': 'button-green', 'effect': 'effect-strip'}
    rows = re.findall(r'add\("shopkit2_([a-z_]+?)_?"(?: \.\. \w+)?, (\d+), (\d+), \{(\d+), (\d+), (\d+), (\d+)\}, \{l = (\d+), t = (\d+), r = (\d+), b = (\d+)\}, '
                      r'\{x = (\d+), y = (\d+), w = (\d+), h = (\d+)\}', kit)
    assert len(rows) == 3, 'ShopKit2: three studded kinds (card, button, effect strip)'
    for row in rows:
        kind = row[0].split('_')[0]
        w, h, s0, s1, s2, s3, il, it, ir, ib, cx, cy, cw, ch = map(int, row[1:])
        a = np.array(Image.open(ROOT / 'resources/ui/v2/shopkit2' / (files[kind] + '.png')).convert('RGBA')).astype(float)
        H, Wd = a.shape[:2]
        assert abs(Wd - w) <= 1 and abs(H - h) <= 1, f'{kind}: picture size {Wd}x{H} vs {w}x{h}'
        lum = a[:, :, :3].mean(2)
        face = np.median(lum[H // 4:3 * H // 4, Wd // 4:3 * Wd // 4])
        row_mid, col_mid = lum[H // 2], lum[:, Wd // 2]
        def first(v):
            return next(i for i, x in enumerate(v) if x > face * 0.75)
        L, T = first(row_mid), first(col_mid)
        R, B = Wd - 1 - first(row_mid[::-1]), H - 1 - first(col_mid[::-1])
        assert abs(il - L) <= 2 and abs(it - T) <= 2 and abs(ir - (Wd - 1 - R)) <= 3 and abs(ib - (H - 1 - B)) <= 3, \
            f'{kind}: inside {il},{it},{ir},{ib} vs the picture {L},{T},{Wd - 1 - R},{H - 1 - B}'
        assert s0 > il and s1 > it and w - s2 > ir and h - s3 > ib, f'{kind}: the slice caps hold the whole outline'
        assert cx >= il and cy >= it and cx + cw <= Wd - ir and cy + ch <= H - ib, f'{kind}: the stud crop inside the coloured face'
        crop = a[cy:cy + ch, cx:cx + cw]
        assert crop[:, :, 3].min() > 200, f'{kind}: the stud crop is opaque'
    hdr = np.array(Image.open(ROOT / 'resources/ui/v2/shopkit2/header-green.png').convert('RGBA'))
    assert hdr.shape[1] == 313 and hdr.shape[0] == 85 and 'K.Header = {w = 313, h = 85, leftCap = 42, tile = {x = 42, w = 25}, stripes = {x = 67, w = 225, first = 87}, rightCap = {x = 292, w = 21}}' in kit, \
        'header pieces match the 313x85 strip'
    assert hdr[5:80, 42:67, 3].min() > 200, 'the header stud column is opaque top to bottom (the outline runs on)'


def scan():
    sys.path.insert(0, str(ROOT / 'tools'))
    import release_profiles as profiles
    cfg = read('src/shared/Config.luau')
    assert '    MenusSaeFrameEnabled = false,\n' in cfg, 'the flag ships false'
    assert 'MenusSaeFrameEnabled = true' in profiles.apply_profile(cfg, 'playtest')[0], 'ON in the playtest profile'
    assert 'MenusSaeFrameEnabled' in [k for k, _ in profiles.REHEARSAL_ON], 'in the rehearsal list'
    assert profiles.verify_source(cfg, 'default').errors == [], 'default profile pins it off'
    assert '"MenusSaeFrameEnabled"' in read('tools/release_playtest.py'), 'the playtest manifest records it'
    tiles = read('src/client/ShopTiles.luau')
    assert tiles.count('.MenusSaeFrameEnabled == true') == 1, 'ShopTiles reads the flag once'
    assert '    if SaeFrame and require(script.Parent.ShopSaeLanding).build(body, spec) then return end\n' in tiles, \
        'ShopTiles hands the landing to ShopSaeLanding only with the flag on'
    screens = read('src/client/ShopScreens.luau')
    assert 'close=closeModal,' in screens and 'press("potions") then return end open("potions")' in screens and 'closeModal = d.close' in screens, \
        'ShopScreens passes Bootstrap close and the HUD POTIONS path to the landing'
    assert 'progress={auras=ProgressionConfig.Auras,ownedAuras=p.auras,trails=ProgressionConfig.Trails,ownedTrails=p.trails,' in screens, \
        'ShopScreens hands the featured cards the shop data the pages use'
    boot = read('src/client/Bootstrap.client.luau')
    assert 'Sae' not in boot and 'Kit' + 'Window' not in boot and 'ShopScreens.attach({body=body,heading=heading,header=header,label=label,box=box,button=button,art=art,open=open,close=close,' in boot, \
        'Bootstrap only passes its close'
    landing = read('src/client/ShopSaeLanding.luau')
    assert 'KitWindow.open(body, {' in landing and 'Instance.new' not in landing, 'the landing passes only data to the kit window'
    assert 'Kit2.artSlot(tab, item)' in landing and 'Kit2.ArtCrop' in landing and 'Art.eggProductId(Slots.Images)' in landing, \
        'featured pictures: the kit 2 card picture (aura, trail), else the uploaded item picture; the egg art'
    kit = {n: read(f'src/client/{n}.luau') for n in ('KitArt', 'KitWindow', 'KitCard', 'KitButton', 'KitStrip', 'KitRail')}
    for n, text in kit.items():
        assert 'rbxassetid' not in text and 'BackgroundColor3' not in text, f'{n}: kit pictures only, no colour fills, no ids in code'
    assert 'Kit2.headerSlot(colour)' in kit['KitWindow'] and 'Kit2.CloseSlot' in kit['KitWindow'] and '"toybox_close"' in kit['KitWindow'] \
        and '"toybox_header_"' in kit['KitWindow'] and '"toybox_panel_frame"' in kit['KitWindow'] and '"toybox_studs_tile"' in kit['KitWindow'], \
        'KitWindow: kit 2 header and X, Toybox fallback; the kit frame and studded body'
    assert 'Kit2.cardSlot(spec.rarity)' in kit['KitCard'] and 'toyboxFace(' in kit['KitCard'] and 'Rules.CardStudCrop' in kit['KitCard'], 'KitCard: kit 2 card, Toybox fallback'
    assert 'Kit2.buttonSlot(spec.grey)' in kit['KitButton'] and '"toybox_button_grey"' in kit['KitButton'] and '"toybox_button_green"' in kit['KitButton'], 'KitButton: kit 2, Toybox fallback'
    assert 'Kit2.StripSlot' in kit['KitStrip'] and '"toybox_button_dark"' in kit['KitStrip'], 'KitStrip: kit 2, Toybox fallback'
    assert 'function A.tiled(' in kit['KitArt'] and 'Enum.ScaleType.Slice' in kit['KitArt'], 'studded pieces: sliced outline, tiled studs'
    assert 'UIIconAssets).amber' in landing, 'the orange crystal on the price buttons'
    win = kit['KitWindow']
    assert 'Kit.ready(Slots.Images, "panel")' in win, 'never half a window: the old landing while the kit frame is not bound'
    for text in (landing,) + tuple(kit.values()):
        assert 'Marketplace' not in text and 'PromptProductPurchase' not in text and 'transact' not in text, 'no Robux path in the kit'
    assert 'panel.Visible = true' in win and 'mark.Destroying' in win, 'the panel comes back when the window is left'
    assert 'local function veil(' in win and 'unveil()' in win and 'mark:Destroy()' in win, 'the HUD is hidden while the window is open and comes back on close'
    assert 'blur.Size = Rules.Blur' in win and 'blur.Size > 0' in win, 'the world behind the window is blurred harder (14 px), only while the menus blur is up'
    assert 'MenusSaeFrameEnabled' not in read('src/client/ModalCompact.luau'), 'the shared window code is unchanged'
    assert not (ROOT / 'src/client/ShopKitCard.luau').exists(), 'one card: KitCard (ShopKitCard is gone)'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    measure()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'sae_frame.luau'
        def module(rel):
            return '(function()\n' + read(rel).replace('export type', 'type') + '\nend)()\n'
        path.write_text('local R=' + module('src/shared/SaeFrameRules.luau') + 'local K=' + module('src/shared/ShopKit2.luau') + LUAU, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            sys.exit(1)
