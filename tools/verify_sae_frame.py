#!/usr/bin/env python3
"""BD-1287 (docs/246 slice 1, owner 2026-11-21): the Crystal Shop landing in the compact Steal-an-Egg window with the outside tab rail,
behind Config.MenusSaeFrameEnabled.

Runs the REAL src/shared/SaeFrameRules.luau in the pinned Luau runtime at desktop and phone sizes and checks: at 1280x720 the window is
about 58 % W x 67 % H, centred, its top at 21-22 % H, the header 9.5-10 % H, the X 52-58 px, the OPEN button 46-52 px with a 25-28 px word,
the card titles 23-26 px, the picture about 14-17 % H, the crystal pill about 5 % H, the rail 1-1.5 % W right of the window with tiles of
7-8 % H 1 % H apart; at every size no text is under 19 px, every tap target is at least 44 px (the X 48), the cards sit inside the window,
the rail inside the screen and never over the window, and labels only show where they fit.
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile and in the rehearsal list and the
playtest manifest; ShopTiles reads it once and hands the landing to ShopSaeLanding only with it on (flag off: the old tiles, unchanged);
Bootstrap only passes its close to ShopScreens; the window uses no new picture (only ShopArt / AssetSlots ids).
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
local labels = {"Auras", "Trails", "Eggs", "Crystals", "Potions"}
local five = {"Auras", "Trails", "Eggs", "Conditions", "Crystals", "Potions"}

-- the 720 p targets (docs/246 shared frame)
local L = R.layout(1280, 720, labels, 3)
local w = L.window
check(near(w.w / 1280, .56, .60) and near(w.h / 720, .65, .69), "window about 58 % W x 67 % H at 720 p")
check(math.abs((w.x + w.w / 2) - 640) <= 1, "window centred")
check(near(w.y / 720, .21, .22), "window top at 21-22 % H")
check(near(L.headerH / 720, .095, .1), "header 9.5-10 % H")
check(near(L.close, 52, 58), "X 52-58 px")
check(near(L.button, 46, 52) and near(L.buttonText, 25, 28), "OPEN 46-52 px, word 25-28 px")
check(near(L.cardTitle, 23, 26), "card title 23-26 px")
check(L.art / 720 >= .14 and near(L.art / L.cards[1].h, .40, .45), "picture 40-45 % of the card, at least 14 % H")
check(near(L.pill.h / 720, .04, .06), "crystal pill about 5 % H")
local gap = L.rail.x - L.rail.stroke - (w.x + w.w + 3)
check(near(gap / 1280, .01, .015), "rail 1-1.5 % W right of the window (outline to outline)")
check(near(L.rail.tile / 720, .07, .08) and near((L.rail.gap - 2 * L.rail.stroke) / 720, .008, .012), "rail tiles 7-8 % H, 1 % H clear between the outlines")
check(L.rail.stroke == 6, "rail outline 6 px at 720 p")
local g = R.gloss(R.Fill.potions)
check(#g == 4 and g[1][1] >= g[2][1] and g[4][3] < g[3][3], "toy gloss: light top, dark lip")
check(L.rail.labels, "labels fit at 720 p")
check(#L.cards == 3, "three cards across")
check(R.grouped(1250) == "1,250" and R.grouped(0) == "0" and R.grouped(1234567) == "1,234,567", "whole numbers with commas")
local tabs = R.cardTabs({"auras", "trails", "eggs", "crystals"})
check(#tabs == 3 and tabs[1] == "auras" and tabs[3] == "eggs", "the first three tabs are the cards")

-- every size: text floor, tap targets, inside the window / screen
for _, size in {{1280, 720}, {1920, 1080}, {1366, 768}, {1024, 768}, {844, 390}, {812, 375}, {667, 375}, {932, 430}, {1180, 820}, {740, 360}} do
    for _, set in {labels, five} do
        local sw, sh = size[1], size[2]
        local tag = sw .. "x" .. sh .. "/" .. #set
        local l = R.layout(sw, sh, set, 3)
        local win = l.window
        for _, t in {l.titleSize, l.cardTitle, l.buttonText, l.pillText, l.closeText} do check(t >= 19, tag .. ": text >= 19 px") end
        if l.sub then check(l.subText >= 19, tag .. ": card line >= 19 px") end
        if l.rail.labels then check(l.rail.labelSize >= 19, tag .. ": rail label >= 19 px") end
        check(l.close >= 48 and l.close <= l.headerH, tag .. ": X >= 48 px inside the header")
        check(l.button >= 44 and l.rail.tile >= 44, tag .. ": OPEN and rail tiles >= 44 px")
        check(win.x >= 0 and win.y >= 0 and win.x + win.w <= sw and win.y + win.h <= sh, tag .. ": window on screen")
        for _, c in l.cards do
            check(c.x >= 0 and c.y >= l.headerH and c.x + c.w <= win.w and c.y + c.h <= win.h, tag .. ": card inside the window")
            check(c.w >= 120, tag .. ": card wide enough for OPEN")
        end
        local need = 10 + (l.cardTitle + 6) + (if l.sub then l.subText + 6 else 0) + 8 + l.button + 10 + l.art
        check(need <= l.cards[1].h, tag .. ": card parts fit the card")
        check(l.art >= 40, tag .. ": picture at least 40 px")
        check(l.art <= l.cards[1].w - 24, tag .. ": picture inside the card width")
        local pw = R.pillWidth("12,345", l)
        check(l.pill.x - pw > 8 + R.textWidth(R.Title, l.titleSize) + l.pad, tag .. ": pill clear of the title")
        check(l.pill.x <= win.w - l.close, tag .. ": pill left of the X")
        check(#l.rail.slots == #set, tag .. ": one rail tile per tab")
        for _, s in l.rail.slots do
            check(s.x - l.rail.stroke >= win.x + win.w + 3 and s.x + l.rail.tile + l.rail.stroke <= sw, tag .. ": rail tile right of the window, on screen")
            check(s.y - l.rail.stroke >= 0 and s.y + s.h + l.rail.stroke <= sh, tag .. ": rail tile on screen vertically")
            if l.rail.labels then local longest = 0 for _, word in set do longest = math.max(longest, R.textWidth(word, l.rail.labelSize)) end check(s.w >= longest, tag .. ": label fits its column") end
        end
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
    assert 'close=closeModal,' in screens and 'press("potions") then return end open("potions")' in screens and 'closeModal = d.close' in screens, 'ShopScreens passes Bootstrap close and the HUD POTIONS path to the landing'
    boot = read('src/client/Bootstrap.client.luau')
    assert 'Sae' not in boot and 'ShopScreens.attach({body=body,heading=heading,header=header,label=label,box=box,button=button,art=art,open=open,close=close,' in boot, \
        'Bootstrap only passes its close'
    landing = read('src/client/ShopSaeLanding.luau')
    assert 'rbxassetid' not in landing and 'Art.tileId(Slots.Images' in landing and 'Art.tabIconId(Slots.Images' in landing, \
        'no new pictures: only the uploaded ShopArt / AssetSlots ids'
    assert 'panel.Visible = true' in landing and 'mark.Destroying' in landing, 'the panel comes back when the landing is left'
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
