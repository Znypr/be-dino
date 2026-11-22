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
BD-1296 (docs/246 slice 2): the Potion Shop (client/PotionSaeShop) and the Dino Index Dinos page (client/DinoIndexKit) on the same kit,
numbers in Shared/SaeMenuRules (run here at 720 p against the docs/246 targets and at every size against the floors), the same flag:
ShopScreens and DinoIndexScreens hand over only with the flag on (flag off = the old pages: the hand-over line does nothing), kid words
(no "%", no multiplier), kit pictures only, no remote and no Robux path in the screens; MUTANTS put each defect back and the checks must
fail (--no-mutants skips them).
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


# ---- BD-1296 slice 2 ------------------------------------------------------------------------------------------------------------------
SLICE2 = {'rules': 'src/shared/SaeMenuRules.luau', 'potion': 'src/client/PotionSaeShop.luau', 'index': 'src/client/DinoIndexKit.luau',
          'shops': 'src/client/ShopScreens.luau', 'screens': 'src/client/DinoIndexScreens.luau', 'window': 'src/client/KitWindow.luau',
          'kit2': 'src/shared/ShopKit2.luau', 'tabs': 'src/client/IndexTabs.luau', 'boot': 'src/client/Bootstrap.client.luau',
          'rail': 'src/client/KitRail.luau', 'timer': 'src/shared/TimerWords.luau', 'preview': 'src/shared/DinosaurPreview.luau'}

LUAU2 = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local function near(v, lo, hi) return v >= lo and v <= hi end
-- 720 p: the docs/246 targets
local P = M.potionLayout(1280, 720, 0)
local w = P.window -- BD-1298: the Potion Shop's own numbers (the proposed picture) are checked in LUAU_POTION
local I = M.indexLayout(1280, 720, 0)
w = I.window
check(near(w.w / 1280, .49, .51) and near(w.h / 720, .62, .64), "Dino Index window 50 x 63 %")
check(#I.cards == 8 and I.cards[5].y > I.cards[1].y and I.cards[4].x > I.cards[3].x and I.cards[5].x == I.cards[1].x, "four columns x two rows")
for _, c in I.cards do check(near(c.h / 720, .14, .16), "index cards 14-16 % H") end
check(near(I.cardRender / 720, .09, .11), "the dino render 9-11 % H")
check(near(I.panel.w / w.w, .26, .30), "the selected-dino panel about 28 % of the window width")
check(near(I.bar.h, 24, 28), "the progress bar 24-28 px at 720 p (lead polish 2026-11-23; docs/246 said 5 % H)")
check(M.LookWord == "View" and M.NotFoundWord == "Not found yet!" and M.NoneWord == "No potions yet!" and string.find(M.MoreWord, "Next", 1, true) ~= nil, "polish words: View, Not found yet!, No potions yet!, Next")
check(M.CardZoom >= .25 and M.PanelZoom >= .25 and M.SilhouetteZoom >= .2, "the dino previews fill their cards (zoomed preview boxes)")
check(I.panelParts.badge >= 19 + 6 and I.panelParts.renderTop >= I.panelParts.edge + I.panelParts.nameText + I.panelParts.badge, "the rarity badge under the name, above the dino")
check(near(I.bar.minFill, 10, 12), "a found dino shows at least 10-12 px of fill at 720 p (lead polish round 2)")
check(M.PanelZoom >= .4 and M.SilhouetteZoom >= .28, "lead polish round 2: the panel dino and the silhouettes bigger")
check(near(I.headerH / 720, .095, .105) and near(I.titleSize, 36, 40), "Index header 9.5-10 % H, title 36-40 px")
check(M.IndexTitle == "Dino Index" and M.IndexColour == "cyan" and M.IndexRail[1] == "dinos" and M.IndexRail[2] == "patterns" and M.IndexRail[3] == "colours", "one cyan title; Dinos / Patterns / Colours on the rail")
for _, L in {P, I} do
    local r = L.rail
    check(near((r.x - L.window.x - L.window.w) / 1280, .009, .016) and near(r.icon / 720, .07, .08) and near(r.gap / 720, .008, .012), "rail 1-1.5 % W right of the window, icons 7-8 % H, 1 % apart")
end
-- kid words
check(M.lasts(300) == "Lasts 5 min" and M.lasts(420) == "Lasts 7 min" and M.lasts(45) == "Lasts 45 s", "Lasts 7 min")
for kind, word in M.KindWords do check(not string.find(word, "[%d%%]"), "kid line without numbers: " .. kind) end
check(M.kindWord("growth") == "Grow faster!" and M.count(3) == "x3", "Grow faster!, x3")
local f, l, n = M.page(6, 2, 3)
check(f == 4 and l == 6 and n == 2, "page 2 of six offers = 4..6")
f, l, n = M.page(6, 9, 3)
check(f == 4 and n == 2, "a page past the end is the last page")
-- every size: floors, inside the window and the screen
for _, size in {{1280, 720, 0}, {1920, 1080, 0}, {1366, 768, 36}, {1024, 768, 36}, {1274, 423, 58}, {844, 390, 0}, {812, 375, 0}, {667, 375, 0}, {932, 430, 0}, {1180, 820, 36}, {740, 360, 0}} do
    local sw, sh, inset = size[1], size[2], size[3]
    local tag = sw .. "x" .. sh
    for _, L in {M.potionLayout(sw, sh, inset), M.indexLayout(sw, sh, inset)} do
        local win = L.window
        check(win.x >= 0 and win.y >= 0 and win.x + win.w <= sw and win.y + win.h <= sh, tag .. ": window on screen")
        check(L.close >= 48 and L.close <= L.headerH and L.titleSize >= 19, tag .. ": X >= 48 px inside the header")
        check(L.rail.icon >= 44 and L.rail.labelSize >= 19, tag .. ": rail icons >= 44 px, words >= 19 px")
        for _, s in L.rail.slots do check(s.x >= win.x + win.w and s.x + s.w <= sw and s.y >= 0 and s.y + s.h <= sh, tag .. ": rail right of the window, on screen") end
        for _, c in L.cards do
            check(c.x >= 4 and c.y >= L.headerInset + L.headerH and c.x + c.w <= win.w - 4 and c.y + c.h <= win.h - 4, tag .. ": card inside the window")
            check(c.w >= 44 and c.h >= 44, tag .. ": card is a tap target")
        end
    end
    local i = M.indexLayout(sw, sh, inset)
    local pp = i.panelParts
    check(i.panel.x >= i.cards[4].x + i.cards[4].w and i.panel.x + i.panel.w <= i.window.w - 4 and i.panel.y + i.panel.h <= i.window.h - 4, tag .. ": panel right of the grid, inside")
    check(i.bar.y >= i.cards[8].y + i.cards[8].h and i.bar.x + i.bar.w <= i.prev.x and i.prev.x + i.prev.w <= i.next.x, tag .. ": bar under the grid, left of the page buttons")
    check(i.prev.h >= 44 and i.prev.w >= 44 and i.bar.text >= 19 and i.countText >= 19, tag .. ": page buttons 44+, bar and count text 19+")
    check(i.cardRender >= 40 and i.cardRender + i.countText <= i.cards[1].h, tag .. ": render 40+ px and its count fit the card")
    check(pp.nameText >= 19 and pp.wordText >= 19 and pp.button >= 44 and pp.buttonText >= 19, tag .. ": panel text 19+, button 44+")
    check(pp.renderTop + 40 + pp.gap + pp.line + pp.gap + pp.button + pp.edge <= i.panel.h, tag .. ": panel parts fit (render 40+ px)")
end
if #fails > 0 then error("sae menus FAILED:\n" .. table.concat(fails, "\n")) end
print("sae menus passed")
'''

# BD-1298: the Potion Shop follows the owner's proposed picture (docs/evidence/2026-11-23-potion-proposal/proposal.jpg; ChatGPT's ranked
# differences): a 1.40 : 1 window 71.5 % H, three tall cards ~30 % W x 70-73 % H, 2-3 % apart, the bottle 45-48 % of the card (lead review), the
# name 10-12 %, the rarity word 55 % of the name (19 px floor), the timer inside the header at ~63 %, the X and the title ~15 % bigger, no row under the cards.
LUAU_POTION = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local function near(v, lo, hi) return v >= lo and v <= hi end
local P = M.potionLayout(1280, 720, 0)
local w = P.window
check(near(w.w / w.h, 1.36, 1.44) and near(w.h / 720, .70, .73), "Potion Shop window 1.40 : 1, 71.5 % H (the picture)")
check(math.abs(w.x + w.w / 2 - 640) <= 1 and near(w.y / 720, .15, .18), "Potion Shop centred, top at 15-18 %")
check(near(P.close, 78, 86) and near(P.titleSize, 44, 48) and P.close + 8 <= P.headerH, "the picture's X (~82 px) and title (~46 px), the X inside the header")
check(near(P.headerH / w.h, .16, .19), "header 16-19 % of the window (the picture)")
check(#P.cards == 3 and M.Potion.perPage == 3, "three potions per page")
for _, c in P.cards do check(near(c.w / w.w, .28, .32) and near(c.h / w.h, .70, .74), "tall cards ~30 % of the window width, 70-74 % of its height") end
local gap = P.cards[2].x - P.cards[1].x - P.cards[1].w
check(near(gap / w.w, .02, .03), "cards 2-3 % of the window apart")
check(math.abs(P.cards[1].x - (w.w - P.cards[3].x - P.cards[3].w)) <= 1, "the card row centred")
local c = P.cards[1]
check(near(P.art / c.h, .48, .52), "the bottle ~50 % of the card (owner 2026-11-23: the picture's card)")
check(near(P.cardTitle / c.h, .10, .12) and P.rarityText == math.max(19, math.floor(P.cardTitle * 0.55 + 0.5)), "the name 10-12 % of the card, the rarity word 55 % of it (19 px floor)")
check(c.y + c.h + 6 <= w.h and w.h - c.y - c.h <= 30, "nothing under the cards (no restock row, no Yours strip)")
check(P.restock == nil and P.more == nil and P.band == nil, "no restock row, page row or Yours strip in the layout")
local hw = w.w - 2 * P.headerInset
local tc = P.timer.x + P.timer.w / 2 - P.headerInset
check(near(tc / hw, .58, .66), "the restock timer inside the header at ~63 % of its width")
check(P.timer.size >= 19 and P.timer.y + P.timer.h <= P.headerInset + P.headerH + 4, "the timer text 19+ px, in the header")
check(M.TimerColour[1] >= 240 and M.TimerColour[2] >= 220 and M.TimerColour[3] < 200, "the timer yellow-white")
check(P.stripeAt >= .45 and P.stripeAt <= .55, "the header stripes from about half the header (the picture)")
check(P.badge.x + P.badge.w <= c.w - 4 and P.badge.x >= c.w * 0.6 and P.badge.y == P.artTop and near(P.badge.size, 19, 22), "the small x3 count top right under the rarity word (the picture)")
check(P.lasts == nil and P.artTop + P.art + 2 + P.lineH + P.innerGap + P.button + P.edge <= c.h, "no Lasts line on the card; the bottle between the rarity word and the strip")
check(P.artGap == nil and M.shortName("Swift Sip") == "Swift" and M.shortName("Titan") == "Titan", "short names: the first word (the picture)")
check(M.PotionTitle == "Potions" and M.YoursTitle == "My Potions" and M.DrinkWord == "Drink!", "title Potions; the owned page My Potions with Drink!")
check(M.PotionRail[1] == "featured" and M.PotionRail[2] == "potions" and M.PotionRail[3] == "trails" and M.PotionRail[4] == "auras" and M.PotionRail[5] == "eggs", "rail Featured, Potions, Trails, Auras, Eggs (the picture)")
check(near((P.rail.x - w.x - w.w) / 1280, .009, .016) and near(P.rail.icon / 720, .07, .08), "rail 1-1.5 % W right of the window, icons 7-8 % H")
-- kid words: no numbers, "3 left" not "x3", Legendary growth "Grow super fast!"
check(M.kindWord("growth") == "Grow faster!" and M.kindWord("speed") == "Run faster!" and M.kindWord("growth", "Legendary") == "Grow super fast!", "Grow faster! / Run faster! / Grow super fast!")
for kind, word in M.SuperWords do check(not string.find(word, "[%d%%]"), "super kid line without numbers: " .. kind) end
check(M.count(3) == "x3" and M.lasts(300) == "Lasts 5 min", "x3 (a count), Lasts 5 min")
-- the Studio canvas: the bottle still big
local S = M.potionLayout(1274, 423, 58)
check(S.art >= 125 and near(S.art / S.cards[1].h, .45, .52), "Studio canvas: the bottle 125+ px, 45-52 % of the card")
-- every size: floors, everything fits, inside the window and the screen
for _, size in {{1280, 720, 0}, {1920, 1080, 0}, {1366, 768, 36}, {1024, 768, 36}, {1274, 423, 58}, {844, 390, 0}, {812, 375, 0}, {667, 375, 0}, {932, 430, 0}, {1180, 820, 36}, {740, 360, 0}} do
    local sw, sh, inset = size[1], size[2], size[3]
    local tag = sw .. "x" .. sh
    local p = M.potionLayout(sw, sh, inset)
    local win, k = p.window, p.cards[1]
    check(win.x >= 0 and win.y >= 0 and win.x + win.w <= sw and win.y + win.h <= sh, tag .. ": window on screen")
    check(k.w >= 120, tag .. ": potion card wide enough for its button")
    check(p.art >= 60, tag .. ": the bottle 60+ px")
    check(p.artTop + p.art + 2 + p.lineH + p.innerGap + p.button + p.edge <= k.h, tag .. ": potion card parts fit")
    for _, t in {p.cardTitle, p.rarityText, p.lineText, p.buttonText, p.timer.size, p.badge.size, p.titleSize} do check(t >= 19, tag .. ": potion text >= 19 px") end
    check(p.button >= 44 and p.page.w >= 44 and p.page.h >= 44 and p.close >= 48, tag .. ": buy button, page arrow 44+ px, X 48+")
    local closeX = win.w - p.headerInset - math.floor((p.headerH - p.close) / 2) - p.close
    check(p.page.x + p.page.w <= closeX and p.page.y >= p.headerInset and p.page.y + p.page.h <= p.headerInset + p.headerH, tag .. ": the page arrow in the header, left of the X")
    check(p.timer.x + p.timer.w <= p.page.x, tag .. ": the timer clear of the page arrow")
    check(p.timer.x >= p.headerInset + math.floor(p.headerH * 0.2) + M.textWidth(M.YoursTitle, p.titleSize), tag .. ": the timer clear of the title")
    check(p.badge.w >= M.textWidth("x3", p.badge.size), tag .. ": the badge fits x3")
    for _, s in p.rail.slots do check(s.x >= win.x + win.w and s.x + s.w <= sw and s.y >= 0 and s.y + s.h <= sh, tag .. ": rail right of the window, on screen") end
end
if #fails > 0 then error("potion shop FAILED:\n" .. table.concat(fails, "\n")) end
print("potion shop passed")
'''


def scan2(src):
    """Source guards of slice 2. src: {key: text} (a mutant changes one of them). Returns the failures."""
    errors = []

    def need(ok, what):
        if not ok:
            errors.append(what)
    shops, screens, potion, index = src['shops'], src['screens'], src['potion'], src['index']
    need(shops.count('MenusSaeFrameEnabled==') == 1 and 'if Config.MenusSaeFrameEnabled==true and require(script.Parent.PotionSaeShop).build(body,{' in shops,
         'ShopScreens hands the Potion Shop to PotionSaeShop only with the flag on')
    need(screens.count('MenusSaeFrameEnabled==') == 1 and 'if Config.MenusSaeFrameEnabled==true and require(script.Parent.DinoIndexKit).build(body,{' in screens,
         'DinoIndexScreens hands the Dinos page to DinoIndexKit only with the flag on')
    need('DinoIndexKit).build(' in screens and screens.index('DinoIndexKit).build(') < screens.index('IndexTabs).mount(open)'),
         'the kit Index is tried before the old tab bar mounts')
    kit_part = shops.split('PotionSaeShop).build(')[1].split('then return end')[0] if 'PotionSaeShop).build(' in shops else ''
    need('onBuy=function(item) potionChoice.id=item.id open("potionConfirm") end' in kit_part, 'a buy tap opens the purchase confirm (the server decides)')
    need('if buff and buff.expiresAt>workspace:GetServerTimeNow() then open("potionReplace") else transact("usePotion",item.id,false) end' in kit_part,
         'a use tap goes through the old use path (the replace confirm)')
    need('openDetail=function() open("detail") end' in screens and 'close=closeModal}) then return end' in screens and 'closeModal = d.close' in screens,
         'the Index opens the old dino page and closes with Bootstrap close')
    need(',open=open,close=close,notify=notify,' in src['boot'], 'Bootstrap passes its close to the Index screens')
    need('KitWindow.open(body, spec)' in potion and 'KitWindow.open(body, spec)' in index, 'both screens are the kit window')
    need('Menu.potionLayout(w, h, inset)' in potion and 'Menu.indexLayout(w, h, inset, words)' in index, 'both screens take their rects from SaeMenuRules')
    need('ProgressionRules.shopOffers(d.window)' in potion and 'ProgressionRules.shopRemaining(p, d.window, item.id)' in potion, 'the offers and stock come from the shared shop rules')
    need('Kit.potionIconSlot(Slots.Images :: any, item.id, item.kind)' in potion, 'the bound potion pictures')
    need('Menu.lasts(item.duration)' in potion and 'Menu.kindWord(item.kind, item.rarity)' in potion and 'multiplier' not in potion, 'kid words: what it does and how long, never the multiplier')
    need('if ProgressionRules.shopWindow(now) ~= d.window then d.restocked() return end' in potion and 'TimerWords.restockIn(' in potion, 'New in 3 min counts down; a new window redraws')
    # BD-1298: the proposed picture
    need('badge = if left > 0 then Menu.count(left) else nil' in potion and potion.count('name = Menu.shortName(item.name)') == 2 and 'Lasts_' not in potion, 'the card: short name, the x3 count, no Lasts line (the picture)')
    need('live.restock = Art.words(window, "Restock", restockWords(d.window), t.x, t.y, t.w, t.h, t.size, 36, Color3.fromRGB(c[1], c[2], c[3]))' in potion,
         'the restock timer in the header, yellow-white')
    need('word = Menu.DrinkWord, grey = false, onPick = function() d.onUse(item) end' in potion and 'state.page = if state.page < pages then state.page + 1 else 1' in potion
         and 'local pages = shopPages + ownPages' in potion, 'drinking stays reachable: the page arrow reaches My Potions with Drink! buttons')
    need('tabs = Menu.PotionRail, words = Menu.PotionRailWords, selected = "potions"' in potion, 'the rail in the picture order, Potions selected')
    need('Kit2.headerPieces(w, h, stripeAt)' in src['window'] and 'header2(header, spec.colour, headerW, lay.headerH, lay.stripeAt)' in src['window'], 'KitWindow: a screen may place the header stripes')
    need('IndexTabs.lastTab() ~= "dinos" then return false end' in index and 'IndexTabs.choose(tab) d.open("collection")' in index, 'Patterns / Colours keep their own pages (the rail picks the tab)')
    need('d.hero(card, id, rx, ry, render, render, d.bestMutation(id))' in index and 'Preview.add(card, id, "silhouette", CHARCOAL)' in index and 'Color3.fromRGB(32, 33, 39)' in index, 'found dinos are the game preview in colour, the others a silhouette')
    need('if found then rarityWord(d.speciesIndex(id)) else "Common"' in index, 'found dinos on their rarity card, not found on the grey card')
    need('TimerWords.found(unlocked, total)' in index and 'i <= #Config.SpeciesOrder and info(id, false)' in index, 'the bar counts the normal dinos only (secrets apart)')
    need('Config.PatternColourIndexEnabled == true then table.insert(out, tab)' in index, 'Patterns / Colours on the rail only while their pages exist')
    for name in ('potion', 'index'):
        text = src[name]
        need('rbxassetid' not in text and 'BackgroundColor3' not in text and 'Marketplace' not in text and 'PromptProductPurchase' not in text,
             f'{name}: kit pictures only, no colour fills, no ids, no Robux path')
        need('FireServer' not in text and 'InvokeServer' not in text, f'{name}: no remote (the screen modules only call back)')
    need('if not table.find(Kit2.HeaderColours, colour) then return false end' in src['window'] and 'headerCard(header, spec.colour, headerW, lay.headerH)' in src['window'],
         'KitWindow: a colour with no kit 2 strip is the kit 2 card piece, never the green strip')
    need('if spec.content then spec.content(window, lay, holder) end' in src['window'] and 'spec.refresh = redraw' in src['window'], 'KitWindow draws a screen part and redraws in place')
    need('Art.studded(holder, "KitTabTile_" .. tab, Kit2.buttonSlot(false),' in src['rail'] and '        if selected then\n            -- BD-1296' in src['rail'], 'KitRail: the active tab sits on the lime kit tile (every kit screen)')
    need('function W.potionsIn(secondsLeft: number): string' in src['timer'] and 'return "New in " .. UIFormat.duration(secondsLeft)' in src['timer'], 'New potions in 2 min is its own function; the Toybox page keeps restockIn')
    need('if shade and gold=="silhouette" then viewport:SetAttribute("SilhouetteShade",shade) end' in src['preview'], 'the charcoal silhouette is opt-in (the old Index keeps black)')
    need('local fill = if total > 0 then math.floor(B.w * unlocked / total + 0.5) else 0' in index and 'if unlocked > 0 then fill = math.max(fill, B.minFill) end' in index
         and 'piece.ImageColor3 = TRACK' in index, 'the progress fill is exact with a visible minimum, on a darker track')
    need('K.HeaderCards = {cyan = "rare"}' in src['kit2'], 'the cyan header is the kit 2 Rare card piece')
    need('function Tabs.choose(tab: string) lastTab = Index.validTab(tab) end' in src['tabs'], 'IndexTabs.choose keeps the tab valid')
    need('M.Potion = {h = 0.715, aspect = 1.40,' in src['rules'] and 'M.Index = {w = 0.50, h = 0.63,' in src['rules'], 'window sizes: the Potion Shop as the proposed picture (BD-1298), the Index docs/246')
    return errors


MUTANTS = {
    'the Potion Shop hand-over ignores the flag': ('shops', 'if Config.MenusSaeFrameEnabled==true and require(script.Parent.PotionSaeShop)', 'if require(script.Parent.PotionSaeShop)'),
    'the Index hand-over ignores the flag': ('screens', 'if Config.MenusSaeFrameEnabled==true and require(script.Parent.DinoIndexKit)', 'if require(script.Parent.DinoIndexKit)'),
    'a buy tap buys at once': ('shops', 'onBuy=function(item) potionChoice.id=item.id open("potionConfirm") end', 'onBuy=function(item) transact("buyPotion",item.id,false) end'),
    'the card shows the multiplier': ('potion', 'Menu.kindWord(item.kind, item.rarity)', 'tostring(item.multiplier)'),
    'the full catalog name': ('potion', 'key = item.id, rarity = item.rarity, name = Menu.shortName(item.name),', 'key = item.id, rarity = item.rarity, name = item.name,'),
    'the timer leaves the header': ('potion', 'live.restock = Art.words(window, "Restock", restockWords(d.window), t.x, t.y,', 'live.restock = Art.words(window, "Restock", restockWords(d.window), 8, w.h - 30,'),
    'no way to drink': ('potion', 'local pages = shopPages + ownPages', 'local pages = shopPages'),
    'the rail back in the old order': ('potion', 'tabs = Menu.PotionRail, words = Menu.PotionRailWords,', 'tabs = FrameRules.RailTabs, words = FrameRules.RailWords,'),
    'the timer never restocks': ('potion', 'if ProgressionRules.shopWindow(now) ~= d.window then d.restocked() return end', 'if false then return end'),
    'the kit Index hides the Patterns page': ('index', 'IndexTabs.lastTab() ~= "dinos" then return false end', 'false then return false end'),
    'not found dinos in colour': ('index', 'if found then rarityWord(d.speciesIndex(id)) else "Common"', 'rarityWord(d.speciesIndex(id))'),
    'the cyan Index header turns green': ('window', 'if not table.find(Kit2.HeaderColours, colour) then return false end', ''),
    'a colour fill in the potion screen': ('potion', 'local M = {}', 'local M = {}\nlocal _x = Instance.new("Frame") _x.BackgroundColor3 = Color3.new(1, 0, 0)'),
    'the active rail tab loses its tile': ('rail', '        if selected then\n            -- BD-1296', '        if false then\n            -- BD-1296'),
    'the progress fill rounds up to a square': ('index', 'local fill = if total > 0 then math.floor(B.w * unlocked / total + 0.5) else 0', 'local fill = math.max(B.h, math.floor(B.w * unlocked / total + 0.5))'),
    'one found dino shows no fill': ('index', 'if unlocked > 0 then fill = math.max(fill, B.minFill) end', ''),
    'the Index window at shop size': ('rules', 'M.Index = {w = 0.50, h = 0.63,', 'M.Index = {w = 0.58, h = 0.67,'),
}
LUAU_MUTANTS = {
    'the potion window back at 1.85 : 1': ('M.Potion = {h = 0.715, aspect = 1.40,', 'M.Potion = {h = 0.715, aspect = 1.85,'),
    'the bottle at 25 % of the card': ('bottle = 0.50,', 'bottle = 0.25,'),
    'the count in the middle': ('local badge = {x = cardW - c.edge - 4 - badgeW,', 'local badge = {x = math.floor((cardW - badgeW) / 2),'),
    'the rarity word as big as the name': ('local rarityText = math.clamp(round(cardTitle * 0.55), M.MinText, 32)', 'local rarityText = math.clamp(round(cardTitle * 0.9), M.MinText, 32)'),
    'the buy button under 44 px': ('local button = if small then M.MinTap else math.max(M.MinTap, round(cH * P.button))', 'local button = if small then 36 else round(cH * 0.09)'),
    'the timer back at the left': ('timerAt = 0.63,', 'timerAt = 0.25,'),
    'the X at the shared kit size': ('local close = math.max(round(M.MinClose * 1.15), round(h * P.close))', 'local close = math.max(M.MinClose, round(h * 0.078))'),
    'the page arrow over the X': ('local page = {x = closeX - math.max(6, round(close * 0.15)) - pageS,', 'local page = {x = closeX - 10,'),
    'the long name': ('function M.shortName(name: string): string return string.match(name, "^(%S+)") or name end', 'function M.shortName(name: string): string return name end'),
    'Legendary growth with a number': ('growth = "Grow super fast!"', 'growth = "x2 Growth"'),
    'kid line with a number': ('growth = "Grow faster!"', 'growth = "+40% growth"'),
    'the Index panel at 40 %': ('panel = 0.28,', 'panel = 0.40,'),
    'the rail inside the window': ('local x = win.x + win.w + math.max(6, round(w * 0.0125))', 'local x = win.x + win.w - 40'),
    'text under 19 px on a phone': ('local rarityText = math.clamp(round(cardTitle * 0.55), M.MinText, 32)', 'local rarityText = math.clamp(round(cardTitle * 0.55), 14, 32)'),
}


def run_luau2(runner, rules_text):
    out = ''
    with tempfile.TemporaryDirectory() as tmp:
        for name, body, word in (('sae_menus', LUAU2, 'sae menus passed'), ('potion_shop', LUAU_POTION, 'potion shop passed')):  # BD-1298
            path = Path(tmp) / (name + '.luau')
            path.write_text('local M=(function()\n' + rules_text.replace('export type', 'type') + '\nend)()\n' + body, encoding='utf-8')
            result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
            out += result.stdout + result.stderr
            if result.returncode != 0 or word not in result.stdout:
                return False, out
    return True, out


def slice2(runner, mutants=True):
    src = {k: read(v) for k, v in SLICE2.items()}
    errors = scan2(src)
    ok, out = run_luau2(runner, src['rules'])
    if not ok:
        errors.append('SaeMenuRules: ' + out.strip())
    if errors:
        print('sae menus FAILED:\n' + '\n'.join(errors))
        return False
    print('sae menus passed (source + numbers)')
    if not mutants:
        return True
    survived = []
    for name, (key, old, new) in MUTANTS.items():
        assert old in src[key], f'mutant {name!r}: the text is not in {SLICE2[key]}'
        bad = dict(src)
        bad[key] = src[key].replace(old, new, 1)
        if not scan2(bad) and run_luau2(runner, bad['rules'])[0]:
            survived.append(name)
    for name, (old, new) in LUAU_MUTANTS.items():
        assert old in src['rules'], f'mutant {name!r}: the text is not in SaeMenuRules'
        if run_luau2(runner, src['rules'].replace(old, new, 1))[0]:
            survived.append(name)
    if survived:
        print('sae menus: MUTANTS SURVIVED (the checks did not catch them):\n' + '\n'.join(survived))
        return False
    print(f'sae menus: {len(MUTANTS) + len(LUAU_MUTANTS)} mutants caught')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    scan()
    measure()
    if not slice2(args.runner, not args.no_mutants):
        sys.exit(1)
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
