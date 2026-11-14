#!/usr/bin/env python3
"""BD-1189 (docs/232): the Toybox layout rules, checked on the dino detail page (the pilot) behind Config.ToyboxUIEnabled.

What is checked (pinned Luau runtime, the REAL ToyboxKit / ToyboxSkin / ToyboxLayout / UITheme with the engine mock of verify_toybox_ui.py):
  1. the page rects (Kit.detailLayout) at a 1280x720 window (scale 1.38) and a small phone window (scale 0.56), with and without the chosen-filter
     row and the "3 of 6 for Gold!" bars: every element sits inside its panel with 12 px padding, neighbours are exactly 12 px apart
     (panels, heading / SORT / BACK, filters, grid, bars), both panels fill the 824 px body, buttons are 48 / 40 px and never under 44 px on screen;
  2. the helpers build real instances (panel, preview, six label / value rows, equal cells, empty slots, buttons) and every one lies inside its
     parent, no text is under 14 px, label and value never overlap, the dashes of an empty slot stay inside the slot;
  3. rows: sample values (the longest the page can show) fit their value box at the 14 px floor, so nothing is clipped;
  4. the X sits inside the header strip (see verify_toybox_ui.py, run first);
  5. static: at most ONE coloured button on the page (EQUIP); every other action button is grey; the page code reaches the layout helpers only behind
     `Theme.Toybox` (flag off = the page as before: no ToyboxLayout require, no new branch taken); the grid still scrolls (many copies reachable),
     pages with SHOW MORE, and the existing functions (equip, fusion bars, sort/filter sheet, egg badge, drag-to-turn, secret species) are still wired;
  6. mutants put each defect back and the checks must fail.
NOT Studio evidence: how the page looks in the game is unverified here.
Usage: python tools/verify_toybox_layout.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_toybox_ui as U  # noqa: E402

ROOT = U.ROOT
LAYOUT = U.LAYOUT
PANELS = U.PANELS

CHECKS = r'''
local Layout = require("ToyboxLayout")
local Kit = Layout.Kit
local function rect(o) return {x = o.Position.X.Offset, y = o.Position.Y.Offset, w = o.Size.X.Offset, h = o.Size.Y.Offset} end
local function inside(a, w, h, pad, what, extraRight)
    assert(a.x >= pad - 1e-6 and a.y >= pad - 1e-6 and a.x + a.w <= w - pad + (extraRight or 0) + 1e-6 and a.y + a.h <= h - pad + 1e-6, what .. string.format(" (%g,%g %gx%g in %gx%g)", a.x, a.y, a.w, a.h, w, h))
end
local function every(node, f) f(node) for _, child in node.__children do every(child, f) end end
local function texts(root, what)
    local n = 0
    every(root, function(node)
        if node.ClassName == "TextLabel" or node.ClassName == "TextButton" then
            if node.Text ~= "" and node.Name ~= "ToyboxText" and node.Name ~= "ToyboxTextDrop" then
                n += 1
                assert(node.TextSize >= 14, what .. ": text under 14 px: " .. node.Text)
                for _, c in node.__children do if c.ClassName == "UITextSizeConstraint" then assert(c.MinTextSize >= 14, what .. ": a text constraint under 14 px") end end
            end
        end
    end)
    return n
end
local PhoneScale = require("PhoneScale")
-- the windows: 1280x720 (desktop), 1274x481 (the lead's Studio viewport, compact), a small phone, full HD; body = what is really on screen (design px)
local windows = {}
for _, size in {{1280, 720}, {1274, 481}, {667, 375}, {1920, 1080}} do
    local m = PhoneScale.modal(size[1], size[2], nil)
    table.insert(windows, {name = size[1] .. "x" .. size[2], scale = m.effScale, w = math.floor(m.innerW), h = math.floor(m.innerH)})
end
table.insert(windows, {name = "824x402 at scale 0.56", scale = 0.56, w = 824, h = 402})
for _, win in windows do
    for _, variant in {{0, false, false}, {48, true, true}, {83, false, true}} do
        local scale = win.scale
        local tag = string.format("%s (body %dx%d, scale %.2f) filters %d bars %s: ", win.name, win.w, win.h, scale, variant[1], tostring(variant[2]))
        local lay = Kit.detailLayout(scale, variant[1], variant[2], variant[3], win.w, win.h)
        local D = Kit.Detail
        local BW, BH = lay.width, lay.height
        assert(BW == math.max(win.w, 608) and BH == win.h, tag .. "the page uses the whole body")
        local big, small = Kit.buttonHeights(scale)
        assert(big >= 48 and small >= 40 and big * scale >= 44 - 1e-6 and small * scale >= 44 - 1e-6, tag .. "buttons 48 / 40 px, never under 44 px on screen")
        assert(lay.rightPanel.x == lay.leftPanel.w + Kit.Gutter and lay.rightPanel.x + lay.rightPanel.w == BW, tag .. "panels 12 px apart, filling the body width")
        -- left panel
        for _, name in {"preview", "rows", "equip"} do inside(lay[name], D.leftW, BH, Kit.PanelPad, tag .. name .. " inside the left panel with 12 px") end
        assert(lay.preview.y + lay.preview.h + Kit.Gutter == lay.rows.y, tag .. "preview to rows is 12 px")
        assert(lay.rows.y + lay.rows.h + Kit.Gutter <= lay.equip.y, tag .. "rows to button at least 12 px")
        assert(lay.equip.y + lay.equip.h + Kit.PanelPad == BH and lay.equip.w == D.leftW - 2 * Kit.PanelPad, tag .. "one full-width button at the foot")
        assert(lay.preview.h >= 120 and lay.rows.h >= 2 * Kit.RowH and lay.rows.h <= 6 * Kit.RowH, tag .. "preview stays big, rows keep at least two lines (and scroll)")
        if BH >= 3 * Kit.PanelPad + Kit.Gutter + 120 + 6 * Kit.RowH + big then assert(lay.rows.h == 6 * Kit.RowH, tag .. "all six rows show when the body is tall enough") end
        assert(lay.equip.y >= lay.rows.y + lay.rows.h and lay.equip.y + lay.equip.h <= BH, tag .. "EQUIP is always visible below the rows, inside the body")
        -- right panel
        for _, name in {"heading", "sort", "back"} do inside(lay[name], lay.rightPanel.w, BH, Kit.PanelPad, tag .. name .. " inside the right panel with 12 px") end
        inside(lay.grid, lay.rightPanel.w, BH, Kit.PanelPad, tag .. "grid inside the right panel", 8) -- the scroll bar sits in the right padding
        assert(lay.grid.x + lay.grid.w <= lay.rightPanel.w - 4, tag .. "grid never touches the panel edge")
        assert(lay.heading.x + lay.heading.w + Kit.Gutter == lay.sort.x and lay.sort.x + lay.sort.w + Kit.Gutter == lay.back.x and lay.back.x + lay.back.w + Kit.PanelPad == lay.rightPanel.w, tag .. "heading, SORT, BACK 12 px apart")
        assert(lay.heading.w >= 120, tag .. "the heading has room")
        local top = Kit.PanelPad + small + Kit.Gutter
        if variant[1] > 0 then
            inside(lay.filters, lay.rightPanel.w, BH, Kit.PanelPad, tag .. "filters inside")
            assert(lay.filters.y == top and lay.grid.y == top + variant[1] + Kit.Gutter, tag .. "filters 12 px above the grid")
        else assert(lay.grid.y == top, tag .. "grid 12 px under the heading bar") end
        if variant[2] then
            inside(lay.dup, lay.rightPanel.w, BH, Kit.PanelPad, tag .. "bars inside")
            assert(lay.grid.y + lay.grid.h + Kit.Gutter == lay.dup.y and lay.dup.y + lay.dup.h + Kit.PanelPad == BH, tag .. "bars 12 px under the grid and 12 px from the panel foot")
        else assert(lay.grid.y + lay.grid.h + Kit.PanelPad == BH, tag .. "grid ends 12 px from the panel foot") end
        assert(lay.grid.h >= 0 and lay.grid.y + lay.grid.h <= BH - Kit.PanelPad, tag .. "the grid stays inside its panel and scrolls (many copies stay reachable)")
        if BH >= 400 and variant[1] == 0 and not variant[2] then assert(lay.grid.h >= 60, tag .. "the grid shows part of a row") end
        local columns = lay.columns
        local content = lay.rightPanel.w - 2 * Kit.PanelPad
        assert(columns >= 4 and columns <= 6, tag .. "4 to 6 columns")
        assert(columns == Kit.columnsFor(content), tag .. "as many columns as fit, up to 6")
        assert(lay.cellW >= Kit.Detail.minCell or columns == 4, tag .. "cells never narrower than the card")
        assert(lay.cellW * columns + (columns - 1) * Kit.Gutter <= content and lay.cellW * columns + (columns - 1) * Kit.Gutter >= content - columns, tag .. "equal cells fill the width")
        if win.w >= 1200 then assert(lay.rightPanel.x + lay.rightPanel.w == win.w and columns >= 6, tag .. "a wide window: the page fills it, 6 columns") end
        -- the helpers build real instances at these rects
        local root = Instance.new("Frame")
        local left = Layout.panel(root, "Left", UDim2.fromOffset(lay.leftPanel.w, lay.leftPanel.h), UDim2.fromOffset(0, 0))
        local pv = Layout.preview(left, UDim2.fromOffset(lay.preview.w, lay.preview.h), UDim2.fromOffset(lay.preview.x, lay.preview.y))
        local host = Instance.new("Frame")
        host.Size, host.Position, host.Parent = UDim2.fromOffset(lay.rows.w, 6 * Kit.RowH), UDim2.fromOffset(lay.rows.x, lay.rows.y), left
        for i, row in {{"Pattern", "Plain"}, {"Class", "Fast"}, {"Stage", "Base"}, {"Found in", "36% of eggs"}, {"Boost", "+3% growth"}, {"Special", "Shiny • BIG"}} do
            local r = Layout.row(host, i, lay.rows.w, row[1], row[2])
            inside(rect(r), lay.rows.w, 6 * Kit.RowH, 0, tag .. "a row inside the rows box")
            local label, value = r:FindFirstChild("Label"), r:FindFirstChild("Value")
            assert(label.Position.X.Offset + label.Size.X.Offset + Kit.Gutter <= value.Position.X.Offset, tag .. "label and value never overlap")
            assert(value.Position.X.Offset + value.Size.X.Offset <= lay.rows.w, tag .. "the value stays inside its row")
        end
        local equip = Layout.actionButton(left, "EQUIP", UDim2.fromOffset(lay.equip.w, lay.equip.h), UDim2.fromOffset(lay.equip.x, lay.equip.y), C.accent, false, function() end)
        local right = Layout.panel(root, "Right", UDim2.fromOffset(lay.rightPanel.w, lay.rightPanel.h), UDim2.fromOffset(lay.rightPanel.x, 0))
        Layout.text(right, Kit.copiesHeading("Compy", 12), UDim2.fromOffset(lay.heading.w, lay.heading.h), UDim2.fromOffset(lay.heading.x, lay.heading.y), Kit.Type.heading)
        local grey = Color3.fromRGB(128, 142, 158)
        local sort = Layout.actionButton(right, "SORT", UDim2.fromOffset(lay.sort.w, lay.sort.h), UDim2.fromOffset(lay.sort.x, lay.sort.y), grey, true, function() end)
        local back = Layout.actionButton(right, "BACK", UDim2.fromOffset(lay.back.w, lay.back.h), UDim2.fromOffset(lay.back.x, lay.back.y), grey, true, function() end)
        local coloured = 0
        for _, b in {equip, sort, back} do
            local c = b.BackgroundColor3
            if Kit.buttonKey(math.floor(c.R * 255 + .5), math.floor(c.G * 255 + .5), math.floor(c.B * 255 + .5)) ~= "grey" then coloured += 1 end
        end
        assert(coloured == 1, tag .. "exactly one coloured (primary) button: EQUIP, got " .. coloured)
        local count = 5
        for k = 1, Kit.emptySlots(count, columns, 2) do
            local slot = Layout.emptySlot(right, lay.cellW, lay.cellH, count + k)
            every(slot, function(node)
                if node ~= slot then inside(rect(node), lay.cellW, lay.cellH, 0, tag .. "a dash inside its empty slot") end
            end)
        end
        local n = texts(root, tag .. "page")
        assert(n >= 10, tag .. "the helpers drew their texts: " .. n)
    end
end
-- rows never clip: the longest values the page can show, at the 14 px floor (about 0.56 of the size per character)
local lay = Kit.detailLayout(1, 0, false, false, 824, 402)
local valueWidth = lay.rows.w - math.floor(lay.rows.w * 0.3) - Kit.Gutter
for _, value in {"Rainbow Zebra", "Found in", "0.004% of eggs", "36% of eggs", "+3% growth", "3 of 5", "Shiny • BIG • Aurora", "Diamond", "Unknown pattern"} do
    assert((utf8.len(value) :: number) * 0.56 * Kit.MinText <= valueWidth, "a row value would clip at 14 px: " .. value)
end
-- grids and headings
assert(Kit.emptySlots(1, 4, 2) == 7 and Kit.emptySlots(8, 4, 2) == 0 and Kit.emptySlots(9, 4, 2) == 3 and Kit.emptySlots(0, 4, 2) == 8, "empty slots finish the last row, two rows at least")
assert(Kit.copiesHeading("Compy", 1) == "Your Compies (1)" and Kit.copiesHeading("Rex", 3) == "Your Rexes (3)" and Kit.copiesHeading("Raptor", 2) == "Your Raptors (2)", "the heading never repeats the window title")
assert(Kit.cellWidth(492, 4, 12) == 114, "equal cells")
assert(Kit.Type.title == 28 and Kit.Type.heading == 20 and Kit.Type.body == 16 and Kit.Type.small == 14, "type scale 28 / 20 / 16 / 14")
print("layout ok")
'''


def static_checks(read):
    panels = read(PANELS)
    code = U.code_only(panels)
    assert code.count('require(Shared.ToyboxLayout)') == 1 and 'if TB then require(Shared.ToyboxLayout)' in code.replace('local L: any = ', '') or \
        'local L: any = if TB then require(Shared.ToyboxLayout) else nil' in code, 'ToyboxLayout is required behind Theme.Toybox only'
    assert 'local TB: any = Theme.Toybox' in code, 'the page reads the flag through Theme.Toybox'
    for name in ('buildLeftT', 'buildRightT', 'fillRows'):
        assert len(re.findall(r'\b%s\(' % name, code)) >= 2, name + ' is called'
    assert re.search(r'if TB then fillRows\(d\) return end', code), 'fillRows only behind the flag'
    assert re.search(r'if TB then buildLeftT\(\) return end', code) and re.search(r'if TB then buildRightT\(\) return end', code), 'flag off keeps the old builders'
    buttons = re.findall(r'L\.actionButton\((?:[^\n]*?), (GREY|C\.accent|[A-Za-z.]+), (?:true|false), function', code)
    assert len(buttons) >= 6, 'the page builds its buttons with the helper (%d found)' % len(buttons)
    assert buttons.count('C.accent') == 1 and all(b in ('GREY', 'C.accent') for b in buttons), 'at most ONE coloured button (EQUIP); every other button is grey: %r' % buttons
    assert 'W.scroll(panel, UDim2.fromOffset(lay.grid.w' in code, 'the copies grid scrolls (many copies stay reachable)'
    assert 'SHOW MORE' in code and 'Kit.emptySlots' in code and 'L.emptySlot' in code, 'SHOW MORE kept; empty slots drawn'
    for needle in ('MyDinos.equipRequest', 'ctx.equip(', 'ctx.dupRow', 'openSheet()', 'InspectView.attach', 'paintEggButton', 'eggPopup(', 'ctx.onBack()', 'MyDinos.activeChips'):
        assert code.count(needle) >= 2, 'still wired in both builds: ' + needle
    assert 'SecretSpeciesConfig' in code, 'secret species names still resolve'
    # no inline coloured words, no text on studs: the page only uses the Layout text (ink on cream), never W.label with a colour on the panel
    tb_part = code[code.index('local function buildLeftT'):code.index('buildLeft = function()')]
    assert 'W.label' not in tb_part, 'the new left panel draws no old outlined labels'
    # BD-1189 studio review 2026-11-14: fills the body, hint pill below the model, dark ink on the egg chip, no empty colour bar
    assert 'ctx.bodySize' in code and 'bodyW, bodyH = ctx.bodySize()' in code and 'UDim2.fromOffset(bodyW, bodyH)' in code, 'the page fills the body that is on screen (offsets, so a short body grows no scroll bar)'
    assert 'UDim2.new(1, 0, 1, -34)' in code and 'uiParent = stage' in code, 'the Drag-to-turn pill sits in a band under the model, never over the head'
    assert 'L.tone("card"), 0' in code and 'Theme.Toybox.Kit.Tone.value' in code, 'the egg badge is a cream chip with dark ink'
    assert 'g.primaryColorId ~= nil' in code, 'a copy without colours draws no empty colour bar'
    assert 'ScrollingFrame") -- a very short window' in panels, 'the facts list scrolls on a very short window'
    layout = U.code_only(read(LAYOUT))
    for number in re.findall(r'TextSize\s*=\s*(\d+)', layout):
        assert int(number) >= 14, 'no text under 14 px in the layout helpers'
    assert 'Instance.new("ImageLabel")' not in layout and 'rbxassetid' not in layout and 'ViewportFrame' not in layout, 'the helpers draw flat colours only (no code-drawn texture)'


MUTANTS = {
    'the heading ignores the 12 px gutter': (U.KIT, 'layout.heading = {x = pad, y = pad, w = rightContent - D.backW - sortW - 2 * gut, h = small}', 'layout.heading = {x = pad, y = pad, w = rightContent - D.backW - sortW - gut, h = small}'),
    'the grid loses its bottom padding': (U.KIT, 'layout.grid = {x = pad, y = top, w = rightContent + 8, h = bottom - top}', 'layout.grid = {x = pad, y = top, w = rightContent + 8, h = bottom - top + 12}'),
    'a button under 44 px on a phone': (U.KIT, 'return math.max(Kit.ButtonH, touch), math.max(Kit.ButtonSmallH, touch)', 'return Kit.ButtonH, Kit.ButtonSmallH'),
    'panels drift apart': (U.KIT, 'layout.rightPanel = {x = D.leftW + gut, y = 0, w = D.rightW, h = D.height}', 'layout.rightPanel = {x = D.leftW + gut + 4, y = 0, w = D.rightW, h = D.height}'),
    'the rows drift off the 12 px gutter': (U.KIT, 'layout.rows = {x = pad, y = pad + previewH + gut, w = leftContent, h = rowsH}', 'layout.rows = {x = pad, y = pad + previewH + gut + 4, w = leftContent, h = rowsH}'),
    'a row label overlaps its value': (LAYOUT, 'UDim2.fromOffset(labelWidth + Kit.Gutter, 0)', 'UDim2.fromOffset(labelWidth, 0)'),
    'text under the floor': (LAYOUT, 'label.Font, label.TextSize, label.TextScaled, label.TextWrapped = Enum.Font.FredokaOne, Kit.textSize(textSize)', 'label.Font, label.TextSize, label.TextScaled, label.TextWrapped = Enum.Font.FredokaOne, 12'),
    'dashes poke out of the slot': (LAYOUT, 'bar(0, y, t, h) bar(width - t, y, t, h)', 'bar(0, y, t, h) bar(width, y, t, h)'),
    'a second coloured button': (PANELS, 'L.actionButton(panel, "BACK", UDim2.fromOffset(lay.back.w, lay.back.h), UDim2.fromOffset(lay.back.x, lay.back.y), GREY', 'L.actionButton(panel, "BACK", UDim2.fromOffset(lay.back.w, lay.back.h), UDim2.fromOffset(lay.back.x, lay.back.y), C.accent'),
    'the page requires the layout without the flag': (PANELS, 'local L: any = if TB then require(Shared.ToyboxLayout) else nil', 'local L: any = require(Shared.ToyboxLayout)'),
    'the hint pill goes back over the head': (PANELS, 'UDim2.new(1, 0, 1, -34), UDim2.new()', 'UDim2.fromScale(1, 1), UDim2.new()'),
    'the egg word is white again': (PANELS, 'Theme.Toybox.Kit.Tone.value', 'nil'),
    'the empty colour bar comes back': (PANELS, 'if not TB or g.primaryColorId ~= nil then', 'if true then'),
    'the page ignores the body size': (PANELS, 'if TB and ctx.bodySize then bodyW, bodyH = ctx.bodySize() end', ''),
    'EQUIP can fall below the body': (U.KIT, 'layout.equip = {x = pad, y = H - pad - big, w = leftContent, h = big}', 'layout.equip = {x = pad, y = 402 - pad - big, w = leftContent, h = big}'),
    'the grid stops at 4 columns': (U.KIT, 'math.min(D.maxColumns, math.floor((contentWidth + Kit.Gutter) / (D.minCell + Kit.Gutter)))', 'D.columns'),
    'the grid no longer scrolls': (PANELS, 'W.scroll(panel, UDim2.fromOffset(lay.grid.w', 'W.box(panel, UDim2.fromOffset(lay.grid.w'),
}


def run_all(runner, mutant=None):
    read = U.reader(mutant)
    static_checks(read)
    source = U.SCENE.replace('    UIMotion = __MOTION__,', '    UIMotion = __MOTION__,\n    ToyboxLayout = __LAYOUT__,\n    PhoneScale = __PHONE__,')
    source = source.replace('__CHECKS__', CHECKS).replace('__LAYOUT__', U.wrap(read(LAYOUT))).replace('__PHONE__', U.wrap(read('src/shared/PhoneScale.luau')))
    for key, value in (('__FLAG__', 'true'), ('__BOUND__', 'all'), ('__KIT__', U.wrap(read(U.KIT))), ('__SKIN__', U.wrap(read(U.SKIN))),
                       ('__SLOTS__', U.wrap(read(U.SLOTS))), ('__STYLE__', U.wrap(read(U.STYLE))), ('__MOTION__', U.wrap(read(U.MOTION))),
                       ('__THEME__', U.wrap(read(U.THEME)))):
        source = source.replace(key, value)
    ok, out = U.run(runner, source, 'layout')
    assert ok, out[-1500:]
    assert 'layout ok' in out, out[-500:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    try:
        run_all(args.runner)
    except AssertionError as error:
        print('Toybox layout check failed:', error)
        return 1
    print('layout ok: detail page rects at 1280x720 and a phone window, helpers, static rules')
    if not args.no_mutants:
        for name, (path, old, new) in MUTANTS.items():
            try:
                run_all(args.runner, (path, old, new))
            except AssertionError:
                print('  mutant caught:', name)
            else:
                print('Toybox layout check failed: mutant survived:', name)
                return 1
    print('Toybox layout passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
