#!/usr/bin/env python3
"""BD-1287 (docs/246 slice 1, owner 2026-11-21): the Crystal Shop landing behind Config.MenusSaeFrameEnabled, built from the Toybox art
kit to match the owner's APPROVED art-kit shop window on the Design Board (owner redirect 2026-11-21).

Runs the REAL src/shared/SaeFrameRules.luau in the pinned Luau runtime and checks, at 1280x720: the window 58 % W, centred, from 16 % to
88 % of the screen (the HUD is hidden and the world blurred while it is open, like the approved window); the header about 10 % H with the X 48+ px inside it; the gold "-- FEATURED --" heading 30-34 px; three cards with the
name 23-28 px, the picture at least 40 % of the card, the button 8.5 % H with a 25-30 px price; the tabs right of the window as icon + word
(no box), the selected one bigger. On the Studio canvas (1274x423 under a 58 px top bar) the window runs from 16 % to 88 % of the
screen and the picture keeps 55 % of the card. At every size: no text under 19 px,
tap targets >= 44 px (the X 48), everything inside the window / screen. featured(): buy / locked / soon / open, kid words on the buttons.
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile, the rehearsal list and the playtest
manifest; ShopTiles hands the landing over only with the flag on (flag off: the old tiles); Bootstrap only passes its close; the window uses
the uploaded kit pictures (frame, studs, header, close, cards, buttons) and no new picture id; no Robux path in the landing.
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

-- the 720 p targets
local L = R.layout(1280, 720, 3)
local w = L.window
check(near(w.w / 1280, .48, .505) and near(w.h / 720, .715, .725), "window 49 % W (58 % narrowed by 15 %) x 72 % H at 720 p")
check(math.abs((w.x + w.w / 2) - 640) <= 1, "window centred")
check(near(w.y / 720, .155, .165) and near((w.y + w.h) / 720, .875, .885), "window from 16 % to 88 % H")
check(near(L.headerH / w.h, .19, .2) and L.close >= 48 and L.close <= L.headerH, "header 19-20 % of the window, X inside it")
check(L.showHeading and near(L.headingSize, 30, 34), "-- FEATURED -- 30-34 px")
check(L.heading.y + L.heading.h <= L.cards[1].y, "the heading above the cards")
check(near(L.cardTitle / L.cards[1].w, .17, .21) and near(L.button / w.h, .09, .1) and L.buttonText >= 25, "name about 19 % of the card width (approved titles), button 9-10 % of the window, price 25+ px")
check(L.line and near(L.art / L.cards[1].h, .43, .55), "the strip shows and the picture is 43-55 % of the card at 720 p")
check(R.Blur >= 12 and R.Blur <= 16 and R.Cover >= .92 and R.Cover <= .95 and R.OutlinePx == 3, "blur 12-16 px, 5-8 % overlay")
check(R.CardStudCrop.w == 80 and R.CardStudCrop.h == 75 and R.CardStudCrop.x + R.CardStudCrop.w <= 256 and R.CardStudCrop.y + R.CardStudCrop.h <= 320, "the stud fill = one stud period of the 256x320 kit card")
local plain, rich = R.auraLine(1.15)
check(plain == "x1.15 Growth" and string.find(rich, "x1.15</font> Growth", 1, true) ~= nil and R.auraLine(1.7) == "x1.7 Growth", "the approved aura strip words")
check(L.cards[1].h >= .62 * w.h, "cards take most of the window height")
check(L.rarityText >= 19 and L.rarityText <= 22, "the rarity word under the name, 19-22 px")
check(R.HeaderStripeCrop.x == R.HeaderCaps.left and R.HeaderStripeCrop.w == 160, "header stripe crop = one stripe period from the slice centre")
check(L.line, "the short kid line shows at 720 p")
check(L.rail.x > w.x + w.w and L.rail.selectedIcon > L.rail.icon and L.rail.labelSize >= 19, "tabs right of the window, the selected one bigger")
check(R.Title == "Crystal Shop" and R.Featured == "-- FEATURED --" and R.HeaderSlot == "toybox_header_green", "the mock's title, heading and green header")
check(#R.RailTabs == 5 and R.RailTabs[1] == "featured" and R.RailTabs[5] == "potions", "tabs: Featured, Auras, Trails, Eggs, Potions")
check(R.grouped(1250) == "1,250" and R.grouped(0) == "0" and R.grouped(1234567) == "1,234,567", "whole numbers with commas")
check(R.fitSize("Meadow Glow", 400, 26) == 26 and R.fitSize("Meadow Glow", 100, 26) == 19, "names shrink to fit, never under 19 px")
for tab, line in R.Lines do check(not string.find(line, "%d"), "kid line without numbers: " .. tab) end
check(R.Lines.auras ~= nil and R.Lines.trails ~= nil and R.Lines.eggs ~= nil, "a strip line for every card")

-- keep clear of the phone HUD
-- the Studio canvas: 1274x423 under a 58 px top bar: from 16 % to 88 % of the 481 px SCREEN (the HUD is hidden while it is open)
local T = R.layout(1274, 423, 3, 58)
check(math.abs(T.window.y + 58 - 0.16 * 481) <= 1 and math.abs(T.window.y + T.window.h + 58 - 0.88 * 481) <= 2, "Studio canvas: 16 % to 88 % of the screen (top bar included)")
check(T.art >= .4 * T.cards[1].h and T.line, "Studio canvas: the strip shows, the picture is at least 40 % of the (squat) card")
check(L.cards[1].h >= .6 * w.h, "720 p: the cards take most of the window height")

-- featured: every card is an item card (picture + name); only "buy" has a price
local auras = {{id = "meadow", name = "Meadow Glow", rarity = "Common", price = 60}, {id = "tidal", name = "Tidal Halo", rarity = "Rare", price = 470}}
local trails = {{id = "white", name = "Normal White", rarity = "Common", price = 0, level = 1}, {id = "fern", name = "Fern Drift", rarity = "Common", price = 100, level = 3}, {id = "tidal", name = "Tidal Wake", rarity = "Uncommon", price = 280, level = 6}}
local f = R.featured({auras = auras, ownedAuras = {}, trails = trails, ownedTrails = {white = true}, level = 1, eggPrice = 150, eggBlocked = false})
check(f[1].tab == "auras" and f[1].state == "buy" and f[1].item.id == "meadow" and f[1].price == 60, "featured aura: the cheapest one not owned")
check(R.cardSlot(f[1]) == "toybox_card_common" and R.cardTitle(f[1], "Auras") == "Meadow", "a Common aura on the grey kit card, titled like the approved card")
check(f[2].tab == "trails" and f[2].state == "locked" and f[2].item.id == "fern" and f[2].price == nil and R.buttonWord(f[2]) == "Level 3", "no trail to buy at level 1: the next one, Level 3, no price")
check(f[3].tab == "eggs" and f[3].state == "buy" and f[3].price == 150 and R.cardSlot(f[3]) == "toybox_card_legendary" and R.cardTitle(f[3], "Eggs") == "Random Egg", "the egg with its price on the gold kit card")
f = R.featured({auras = auras, ownedAuras = {meadow = true}, trails = trails, ownedTrails = {white = true}, level = 6, eggPrice = 150, eggBlocked = true})
check(f[1].item.id == "tidal" and R.cardSlot(f[1]) == "toybox_card_rare" and f[2].item.id == "fern" and f[2].state == "buy" and R.cardTitle(f[2], "Trails") == "Fern", "skips owned items; a Rare aura on the cyan kit card")
check(f[3].state == "soon" and f[3].item.name == "Random Egg" and f[3].price == nil and R.buttonWord(f[3]) == "Coming soon", "egg the shop cannot sell: Coming soon, no price")
f = R.featured({auras = auras, ownedAuras = {meadow = true, tidal = true}})
check(f[1].state == "open" and f[1].item == nil and R.buttonWord(f[1]) == "OPEN" and f[3].state == "open", "all owned / no data: the category card")

-- every size: text floor, tap targets, inside the window / screen
for _, size in {{1280, 720, 0}, {1920, 1080, 0}, {1366, 768, 36}, {1024, 768, 36}, {1274, 423, 58}, {844, 390, 0}, {812, 375, 0}, {667, 375, 0}, {932, 430, 0}, {1180, 820, 36}, {740, 360, 0}} do
    local sw, sh = size[1], size[2]
    local tag = sw .. "x" .. sh
    local l = R.layout(sw, sh, 3, size[3])
    local win = l.window
    for _, t in {l.titleSize, l.cardTitle, l.buttonText, l.headingSize, l.rail.labelSize, l.rarityText} do check(t >= 19, tag .. ": text >= 19 px") end
    if l.line then check(l.lineText >= 19, tag .. ": card line >= 19 px") end
    check(l.close >= 48 and l.close <= l.headerH, tag .. ": X >= 48 px inside the header")
    check(l.button >= 44 and l.rail.icon >= 44, tag .. ": buttons and tab icons >= 44 px")
    check(win.x >= 0 and win.y >= 0 and win.x + win.w <= sw and win.y + win.h <= sh, tag .. ": window on screen")
    for _, c in l.cards do
        check(c.x >= l.frameInset and c.y >= l.frameInset + l.headerH and c.x + c.w <= win.w - l.frameInset and c.y + c.h <= win.h - l.frameInset, tag .. ": card inside the frame")
        check(c.w >= 120, tag .. ": card wide enough for its button")
        local need = 2 * l.edge + l.nameH + l.button + 4 + l.art + (if l.line then l.lineH else 0)
        check(need <= c.h, tag .. ": card parts fit the card")
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
    assert 'Sae' not in boot and 'ShopScreens.attach({body=body,heading=heading,header=header,label=label,box=box,button=button,art=art,open=open,close=close,' in boot, \
        'Bootstrap only passes its close'
    landing = read('src/client/ShopSaeLanding.luau')
    assert 'rbxassetid' not in landing and 'Art.tileId(Slots.Images' in landing and 'Art.tabIconId(Slots.Images' in landing, \
        'no new pictures: only the uploaded ShopArt / AssetSlots ids'
    card = read('src/client/ShopKitCard.luau')
    for slot in ('"toybox_panel_frame"', '"toybox_studs_tile"', '"toybox_close"', 'Rules.HeaderSlot', 'Rules.cardSlot(f)', 'Card.draw(', 'UIIconAssets).amber'):
        assert slot in landing, 'the window is built from the uploaded kit: ' + slot
    for slot in ('"toybox_button_green"', '"toybox_button_grey"', '"toybox_button_dark"', 'spec.slot', 'Rules.CardStudCrop'):
        assert slot in card, 'the shared card is built from the uploaded kit: ' + slot
    assert 'rbxassetid' not in card and 'BackgroundColor3' not in card, 'the shared card: kit pictures only, no colour fills'
    assert 'BackgroundColor3' not in landing, 'no colour fills: only kit pictures'
    assert 'Kit.ready(Slots.Images, group)' in landing, 'never half a kit: the old tiles while a kit group is not bound'
    assert 'Marketplace' not in landing and 'PromptProductPurchase' not in landing and 'transact' not in landing, 'no Robux path in the landing'
    assert 'panel.Visible = true' in landing and 'mark.Destroying' in landing, 'the panel comes back when the landing is left'
    assert 'local function veil(' in landing and 'unveil()' in landing and 'mark:Destroy()' in landing, 'the HUD is hidden while the window is open and comes back on close'
    assert 'blur.Size = Rules.Blur' in landing and 'blur.Size > 0' in landing, 'the world behind the window is blurred harder (14 px), only while the menus blur is up'
    assert 'MenusSaeFrameEnabled' not in read('src/client/ModalCompact.luau'), 'the shared window code is unchanged'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'sae_frame.luau'
        path.write_text('local R=(function()\n' + read('src/shared/SaeFrameRules.luau').replace('export type', 'type') + '\nend)()\n' + LUAU, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            sys.exit(1)
