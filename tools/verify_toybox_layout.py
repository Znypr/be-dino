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
-- ---- BD-1195: the Eggs screen at the four windows ----
local function coloured(buttons)
    local n = 0
    for _, b in buttons do
        local c = b.BackgroundColor3
        if Kit.buttonKey(math.floor(c.R * 255 + .5), math.floor(c.G * 255 + .5), math.floor(c.B * 255 + .5)) ~= "grey" then n += 1 end
    end
    return n
end
local GREYC = Color3.fromRGB(128, 142, 158)
for _, win in windows do
    for _, notes in {0, 1, 2} do
        if win.scale < 0.6 and notes == 2 then continue end -- the artificial 0.56 window cannot hold two note lines (no real window is that small: the lowest real scale is 0.77)
        local tag = string.format("eggs %s (body %dx%d, scale %.2f) notes %d: ", win.name, win.w, win.h, win.scale, notes)
        local lay = Kit.eggsLayout(win.scale, win.w, win.h, notes, 5)
        local W, H, pad, gut = lay.width, lay.height, Kit.PanelPad, Kit.Gutter
        local big, small = Kit.buttonHeights(win.scale)
        assert(W == win.w and H == win.h, tag .. "the screen uses the whole body")
        assert(lay.nests.x == 0 and lay.nests.w == W and lay.nests.y == 0, tag .. "the nests panel fills the width")
        assert(lay.nests.y + lay.nests.h + gut == lay.stagePanel.y and lay.stagePanel.y == lay.infoPanel.y, tag .. "nests to the bottom row is 12 px")
        assert(lay.stagePanel.x == 0 and lay.stagePanel.x + lay.stagePanel.w + gut == lay.infoPanel.x and lay.infoPanel.x + lay.infoPanel.w == W, tag .. "stage and info panels: 12 px apart, filling the width")
        assert(lay.stagePanel.y + lay.stagePanel.h == H and lay.infoPanel.y + lay.infoPanel.h == H, tag .. "nothing below the body")
        assert(lay.infoPanel.w >= Kit.Eggs.infoMinW - 1 and lay.stagePanel.w >= Kit.Eggs.stageMinW, tag .. "both bottom panels have room")
        inside(lay.nestHead, W, lay.nests.h, pad, tag .. "heading inside the nests panel")
        inside(lay.nestChip, W, lay.nests.h, pad, tag .. "count chip inside the nests panel")
        assert(lay.nestHead.x + lay.nestHead.w + gut == lay.nestChip.x and lay.nestChip.x + lay.nestChip.w + pad == W, tag .. "heading and chip 12 px apart")
        assert(#lay.nestCards == 5, tag .. "five nest cards")
        for i, card in lay.nestCards do
            inside(card, W, lay.nests.h, pad, tag .. "nest card " .. i .. " inside the nests panel with 12 px")
            assert(card.w == lay.cellW and card.h == lay.cellH and card.y == pad + Kit.Eggs.headH + gut, tag .. "equal nest cards under the heading, 12 px gap")
            if i > 1 then assert(lay.nestCards[i - 1].x + lay.nestCards[i - 1].w + gut == card.x, tag .. "nest cards 12 px apart") end
        end
        assert(lay.cellH >= Kit.Eggs.nestCardMin and lay.cellW >= 100, tag .. "nest cards big enough for the art")
        local lastCard = lay.nestCards[5]
        assert(W - pad - (lastCard.x + lastCard.w) <= 5, tag .. "the row of cards fills the panel width")
        inside(lay.stage, lay.stagePanel.w, lay.stagePanel.h, pad, tag .. "stage inside its panel with 12 px")
        assert(lay.stage.w + 2 * pad == lay.stagePanel.w and lay.stage.h + 2 * pad == lay.stagePanel.h, tag .. "the stage fills its panel")
        for _, name in {"status", "notes", "action", "auto", "autoLine"} do inside(lay[name], lay.infoPanel.w, lay.infoPanel.h, pad, tag .. name .. " inside the info panel with 12 px") end
        assert(lay.status.y + lay.status.h <= lay.notes.y and lay.notes.y + lay.notes.h + gut <= lay.action.y, tag .. "status, notes, button do not overlap (12 px above the button)")
        assert(lay.action.y + lay.action.h + gut == lay.auto.y and lay.auto.y + lay.auto.h + pad == lay.infoPanel.h, tag .. "AUTO 12 px under the button, 12 px from the foot")
        assert(lay.auto.x + lay.auto.w + gut == lay.autoLine.x and lay.autoLine.w >= 100, tag .. "AUTO toggle and its line 12 px apart")
        assert(lay.action.h == big and lay.auto.h == small and big >= 48 and big * win.scale >= 44 - 1e-6 and small * win.scale >= 44 - 1e-6, tag .. "ONE 48 px primary button, AUTO small, never under 44 px on screen")
        assert(lay.action.w == lay.infoPanel.w - 2 * pad, tag .. "the primary button is full width of its panel")
        local root = Instance.new("Frame")
        local nests = Layout.panel(root, "Nests", UDim2.fromOffset(lay.nests.w, lay.nests.h), UDim2.new())
        Layout.text(nests, "Lucky nests open one at a time.", UDim2.fromOffset(lay.nestHead.w, lay.nestHead.h), UDim2.fromOffset(lay.nestHead.x, lay.nestHead.y), Kit.Type.body, "label")
        local chip = Layout.chip(nests, "Nests 0/5", UDim2.fromOffset(lay.nestChip.w, lay.nestChip.h), UDim2.fromOffset(lay.nestChip.x, lay.nestChip.y))
        for i, card in lay.nestCards do
            local c = Layout.card(nests, "NestSlot" .. i, UDim2.fromOffset(card.w, card.h), UDim2.fromOffset(card.x, card.y), if i == 2 then "ready" else nil)
            Layout.text(c, "Empty", UDim2.fromOffset(card.w - 8, 24), UDim2.fromOffset(4, card.h - 32), Kit.Type.body, "label", Enum.TextXAlignment.Center)
        end
        local info = Layout.panel(root, "Info", UDim2.fromOffset(lay.infoPanel.w, lay.infoPanel.h), UDim2.fromOffset(lay.infoPanel.x, lay.infoPanel.y))
        Layout.text(info, "Go find eggs on the island!", UDim2.fromOffset(lay.status.w, lay.status.h), UDim2.fromOffset(lay.status.x, lay.status.y), Kit.Type.heading)
        local open = Layout.actionButton(info, "Explore", UDim2.fromOffset(lay.action.w, lay.action.h), UDim2.fromOffset(lay.action.x, lay.action.y), C.accent, false, function() end)
        local auto = Layout.actionButton(info, "AUTO: OFF", UDim2.fromOffset(lay.auto.w, lay.auto.h), UDim2.fromOffset(lay.auto.x, lay.auto.y), GREYC, true, function() end)
        assert(coloured({open, auto}) == 1, tag .. "exactly one coloured button (Explore / OPEN)")
        inside(rect(chip), lay.nests.w, lay.nests.h, pad, tag .. "chip instance inside the nests panel")
        assert(texts(root, tag .. "screen") >= 9, tag .. "texts drawn")
    end
end
assert(Kit.Eggs.autoW >= 140, "the AUTO toggle is wide enough for 'AUTO: LOCKED' at 16 px")

-- ---- BD-1194: the Dino Index list at the four windows ----
for _, win in windows do
    for _, paged in {false, true} do
        local tag = string.format("index %s (body %dx%d, scale %.2f) paged %s: ", win.name, win.w, win.h, win.scale, tostring(paged))
        local lay = Kit.indexLayout(win.scale, win.w, win.h, paged)
        local W, H, gut = lay.width, lay.height, Kit.Gutter
        local big = Kit.buttonHeights(win.scale)
        assert(W == win.w and H == win.h, tag .. "the list uses the whole body")
        assert(lay.bar.y + lay.bar.h == H and lay.bar.h == big and big >= 48 and big * win.scale >= 44 - 1e-6, tag .. "the bottom bar sits inside the body, button high, never under 44 px on screen")
        assert(lay.grid.x == 0 and lay.grid.w == W and lay.grid.y == 0 and lay.grid.y + lay.grid.h + gut == lay.bar.y, tag .. "the grid fills the width and ends 12 px above the bar (it scrolls)")
        assert(lay.fusion.x + lay.fusion.w == W and lay.fusion.y == lay.bar.y, tag .. "FUSION at the right end of the bar")
        local right = lay.fusion.x - gut
        if paged then
            assert(lay.next.x + lay.next.w == right and lay.page.x + lay.page.w + gut == lay.next.x and lay.prev.x + lay.prev.w + gut == lay.page.x, tag .. "page arrows 12 px apart")
            right = lay.prev.x - gut
        end
        assert(lay.meter.x == 0 and lay.meter.x + lay.meter.w == right and lay.meter.w >= Kit.Index.minMeter, tag .. "the progress meter takes the rest of the bar (at least 120 px)")
        for _, name in {"meter", "fusion"} do inside(lay[name], W, H, 0, tag .. name .. " inside the body") end
        assert(lay.columns >= 3 and lay.columns <= 6, tag .. "3 to 6 columns")
        local content = W - Kit.Index.scrollBar
        local used = lay.cellW * lay.columns + (lay.columns - 1) * gut
        assert(used <= content and used >= content - lay.columns, tag .. "equal columns fill the body width")
        assert(lay.cellW >= 150 and lay.cellH >= 150, tag .. "cards big enough for the dino")
        if win.w >= 1200 then assert(lay.columns == 6, tag .. "a wide window gets 6 columns") end
        local root = Instance.new("Frame")
        local track = Layout.card(root, "IndexBar", UDim2.fromOffset(lay.meter.w, lay.meter.h), UDim2.fromOffset(lay.meter.x, lay.meter.y), "slot")
        Layout.text(track, "Found 3/22", UDim2.fromOffset(lay.meter.w - 16, lay.meter.h - 4), UDim2.fromOffset(8, 2), Kit.Type.heading, "value", Enum.TextXAlignment.Center)
        local buttons = {Layout.actionButton(root, "FUSION", UDim2.fromOffset(lay.fusion.w, lay.fusion.h), UDim2.fromOffset(lay.fusion.x, lay.fusion.y), C.accent, false, function() end)}
        if paged then
            for _, name in {"prev", "next"} do
                table.insert(buttons, Layout.actionButton(root, if name == "prev" then "<" else ">", UDim2.fromOffset(lay[name].w, lay[name].h), UDim2.fromOffset(lay[name].x, lay[name].y), GREYC, true, function() end))
            end
        end
        assert(coloured(buttons) == 1, tag .. "exactly one coloured button (FUSION)")
        local card = Layout.card(root, "Card", UDim2.fromOffset(lay.cellW, lay.cellH), UDim2.new(), "slot")
        local q = Layout.text(card, "?", UDim2.fromOffset(lay.cellW - 16, 28), UDim2.fromOffset(8, lay.cellH - 36), Kit.Type.heading, "label", Enum.TextXAlignment.Center)
        inside(rect(q), lay.cellW, lay.cellH, 8, tag .. "the one '?' line inside its card")
        assert(texts(root, tag .. "list") >= 3, tag .. "texts drawn")
    end
end

-- ---- docs/232: the Fusion Menu body at four windows (body = the panel the menu really draws: 97% x 95% of the window, max 1180 x 680, minus the header) ----
for _, win in {{1280, 720}, {1274, 481}, {667, 375}, {1920, 1080}} do
    for _, wide in {false, true} do
        local bodyW = math.floor(math.min(1180, win[1] * 0.97) - 16)
        local bodyH = math.floor(math.min(680, win[2] * 0.95) - (44 + 22))
        local tag = string.format("fusion %dx%d (body %dx%d) wide %s: ", win[1], win[2], bodyW, bodyH, tostring(wide))
        local lay = Kit.fusionLayout(1, bodyW, bodyH, wide)
        local pad, gut = Kit.PanelPad, Kit.Gutter
        local big, small = lay.big, lay.small
        assert(big >= 48 and small >= 44, tag .. "buttons 48 px, small never under 44 px on screen")
        assert(lay.left.x == 0 and lay.left.x + lay.left.w + gut == lay.centre.x and lay.centre.x + lay.centre.w + gut == lay.right.x and lay.right.x + lay.right.w == bodyW, tag .. "three panels 12 px apart, filling the body width")
        assert(lay.left.y == lay.centre.y and lay.centre.y == lay.right.y and lay.left.h == lay.centre.h and lay.centre.h == lay.right.h, tag .. "equal panel rows")
        assert(lay.left.y + lay.left.h == bodyH and lay.right.y + lay.right.h == bodyH, tag .. "nothing below the body")
        if wide then
            assert(lay.tabRow and lay.tabRow.w == bodyW and lay.tabRow.y + lay.tabRow.h + gut == lay.left.y, tag .. "the tier chips take one row, 12 px above the panels")
        else
            assert(lay.tabs and lay.tabs.y == 0 and lay.tabs.h == big and lay.tabs.y + lay.tabs.h + gut == lay.goal.y, tag .. "the tier chips sit at the top of the list panel, 12 px above the goal row")
        end
        local li, ci, ri = lay.leftIn, lay.centreIn, lay.rightIn
        assert(li.w == lay.left.w - 2 * pad and li.h == lay.left.h - 2 * pad and ci.w == lay.centre.w - 2 * pad and ri.w == lay.right.w - 2 * pad, tag .. "content 12 px inside each panel")
        for _, name in {"goal", "filter", "grid"} do inside(lay[name], li.w, li.h, 0, tag .. name .. " inside the list panel with 12 px") end
        assert(lay.goal.x + lay.goal.w + gut == lay.filter.x and lay.filter.x + lay.filter.w == li.w, tag .. "goal text and Filter 12 px apart")
        assert(lay.goal.y + lay.goal.h + gut == lay.grid.y and lay.grid.y + lay.grid.h == li.h and lay.grid.h >= 60, tag .. "the dino list fills the rest, 12 px under the goal row")
        for _, name in {"head", "slots", "fill", "clear"} do inside(lay[name], ci.w, ci.h, 0, tag .. name .. " inside the slots panel with 12 px") end
        assert(lay.fill.x + lay.fill.w + gut == lay.clear.x and lay.clear.x + lay.clear.w == ci.w and lay.fill.y == lay.clear.y and lay.clear.y + lay.clear.h == ci.h, tag .. "Fill for me and Clear 12 px apart at the foot")
        assert(lay.head.y + lay.head.h + gut == lay.slots.y and lay.slots.y + lay.slots.h + gut == lay.fill.y and lay.slots.h >= 100, tag .. "slot area 12 px between the heading and the buttons")
        for _, name in {"result", "guarantee", "odds", "note", "fuse"} do inside(lay[name], ri.w, ri.h, 0, tag .. name .. " inside the result panel with 12 px") end
        assert(lay.fuse.y + lay.fuse.h == ri.h and lay.fuse.h == big and lay.fuse.w == ri.w, tag .. "ONE full-width 48 px FUSE button at the foot")
        assert(lay.note.y + lay.note.h + gut == lay.fuse.y, tag .. "the note is 12 px above FUSE")
        assert(lay.result.y + lay.result.h + gut == lay.guarantee.y and lay.guarantee.y + lay.guarantee.h + gut == lay.odds.y, tag .. "result, guarantee, odds stacked 12 px apart")
        assert(lay.odds.y + lay.odds.h + gut == lay.note.y and lay.odds.h >= 0, tag .. "odds list ends 12 px above the note (it scrolls)")
        if bodyH >= 380 then assert(lay.odds.h >= 60 and lay.result.h >= 80, tag .. "odds and the result picture have room") end
        -- the real instances: panels, cream slot cards, dashed empty slots, grey small buttons, ONE green button, dark text >= 14 px
        local root = Instance.new("Frame")
        local panels = {}
        for _, name in {"left", "centre", "right"} do
            panels[name] = Layout.panel(root, name, UDim2.fromOffset(lay[name].w, lay[name].h), UDim2.fromOffset(lay[name].x, lay[name].y))
        end
        Layout.text(panels.left, "You need 6 Base dinos.", UDim2.fromOffset(lay.goal.w, lay.goal.h), UDim2.fromOffset(pad + lay.goal.x, pad + lay.goal.y), Kit.Type.body, "value")
        local cols, rows = 3, 2
        local cellW = math.floor((lay.slots.w - gut * (cols - 1)) / cols)
        local cellH = math.floor((lay.slots.h - gut * (rows - 1)) / rows)
        assert(cellW >= 24 and cellH >= 24, tag .. "slot cells big enough")
        for k = 1, 6 do
            local slot = Layout.emptySlot(panels.centre, cellW, cellH, k)
            every(slot, function(node) if node ~= slot then inside(rect(node), cellW, cellH, 0, tag .. "a dash inside its empty slot") end end)
        end
        local buttons = {
            Layout.actionButton(panels.left, "Filter", UDim2.fromOffset(lay.filter.w, lay.filter.h), UDim2.fromOffset(pad + lay.filter.x, pad + lay.filter.y), GREYC, true, function() end),
            Layout.actionButton(panels.centre, "Fill for me", UDim2.fromOffset(lay.fill.w, lay.fill.h), UDim2.fromOffset(pad + lay.fill.x, pad + lay.fill.y), GREYC, true, function() end),
            Layout.actionButton(panels.centre, "Clear", UDim2.fromOffset(lay.clear.w, lay.clear.h), UDim2.fromOffset(pad + lay.clear.x, pad + lay.clear.y), GREYC, true, function() end),
            Layout.actionButton(panels.right, "FUSE!", UDim2.fromOffset(lay.fuse.w, lay.fuse.h), UDim2.fromOffset(pad + lay.fuse.x, pad + lay.fuse.y), C.accent, false, function() end),
        }
        assert(coloured(buttons) == 1, tag .. "exactly one coloured button (FUSE)")
        local notReady = Layout.actionButton(panels.right, "Pick 6 more", UDim2.fromOffset(lay.fuse.w, lay.fuse.h), UDim2.new(), GREYC, false, function() end)
        assert(coloured({notReady}) == 0, tag .. "FUSE is grey while not ready")
        assert(texts(root, tag .. "fusion") >= 5, tag .. "texts drawn")
    end
end
local tiny = Kit.indexLayout(1, 667, 300, true)
assert(tiny.bar.y + tiny.bar.h == 300 and tiny.meter.w >= Kit.Index.minMeter, "the Index bar stays inside a short 667 x 300 body")
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
    # ---- BD-1195 Eggs screen / BD-1194 Dino Index list: flag off = the old screens, flag on = the new modules ----
    eggs_old, eggs_new = U.code_only(read(U.EGGS)), U.code_only(read(U.EGGSP))
    idx_old, idx_new = U.code_only(read(U.INDEX)), U.code_only(read(U.INDEXL))
    assert re.search(r'if Theme\.Toybox then return require\(script\.Parent\.EggsPanels\)\.build\(', eggs_old), 'EggsScreen loads EggsPanels only behind Theme.Toybox'
    assert eggs_old.count('EggsPanels') == 1, 'EggsPanels is required once, behind the flag'
    assert re.search(r'if Theme\.Toybox then[^\n]*\n\s*local compact=require\(script\.Parent\.ModalCompact\)\n\s*require\(script\.Parent\.DinoIndexList\)\.build\(', idx_old), 'the Index loads DinoIndexList only behind Theme.Toybox'
    assert idx_old.count('DinoIndexList') == 1, 'DinoIndexList is required once, behind the flag'
    for needle in ('local slotW, gap = 156, 11', 'ConditionStage.hero(card', 'art(icon, "egg_nest_single"', 'local gear = button(card, "AUTO"'):
        assert needle in eggs_old, 'flag off keeps the old Eggs screen: ' + needle
    for needle in ('button(card,"VIEW DINO"', 'meter(body,0,if bigBar then 350 else 356', 'button(body,"FUSION",624,350,200,44'):
        assert needle in idx_old, 'flag off keeps the old Index list: ' + needle
    assert 'fromScale(1, 1)' not in eggs_new and 'Active = true' not in eggs_new, 'the new Eggs screen never covers the header (X)'
    for needle in ('ctx.openNest(info.id)', 'ctx.openEgg()', 'ctx.explore()', 'ctx.openSettings("help")', 'EggsLogic.nestSlots', 'NestQueue.project', 'Copy.eggOfText',
                   'Copy.CrackedShellLine', 'Copy.CrackedHint', 'Copy.ChipTypeCaption', 'Copy.ChipShellCaption', 'ConditionStage.hero', 'MutationLook.get', 'ctx.autoOpenText()',
                   'EggsLogic.nestHeader', 'UIFormat.duration', 'Finish a run to earn a nest!', 'EggPicture.add', 'ProgressionRules.item'):
        assert needle in eggs_new, 'the new Eggs screen keeps the function: ' + needle
    for needle in ('IndexProgress.page', 'Secret.indexOrder', 'Secret.summary', 'IndexMilestone', 'MutationBadge', 'd.open("detail")', 'd.openFusion()', 'ScrollingFrame',
                   'FusionSelection.indexCard', 'ColourBonus', 'indexCount', 'IndexProgress.state.page'):
        assert needle in idx_new, 'the new Index list keeps the function: ' + needle
    egg_buttons = re.findall(r'L\.actionButton\(info, [^\n]*?, (if primary\(\) then C\.accent else GREY|GREY|C\.accent), (?:true|false), function', eggs_new)
    assert egg_buttons == ['if primary() then C.accent else GREY', 'GREY'], 'Eggs: ONE coloured button (OPEN / Explore, grey while the egg grows), AUTO grey: %r' % egg_buttons
    idx_buttons = re.findall(r'L\.actionButton\(root, [^\n]*?, (GREY|C\.accent), (?:true|false), function', idx_new)
    assert sorted(idx_buttons) == ['C.accent', 'GREY', 'GREY'], 'Index: ONE coloured button (FUSION), the page arrows grey: %r' % idx_buttons
    assert 'Panels.autoState(' in eggs_new and '"AUTO: OFF"' in eggs_new and '"AUTO: LOCKED"' in eggs_new, 'AUTO shows its state on the toggle'
    assert '"?"' in idx_new and '"???"' not in idx_new and 'look.status' not in idx_new, 'an undiscovered card has ONE "?" line, no "???" twice'
    assert 'Color3.fromRGB(107, 90, 68), 0.35' in idx_new and 'edge.Color = silRarity' in idx_new, 'the undiscovered silhouette is a soft brown tint (0.35) with the rarity colour on the card edge'
    # ---- BD-1202: an empty nest slot never shows the egg ----
    assert 'EmptyNest' in eggs_new and 'v.emptyNest.Visible, v.icon.Visible = empty, not empty' in eggs_new and 'ClipsDescendants' in eggs_new, 'an empty nest slot shows the cropped nest, not the egg art'
    assert 'dim(v.icon, if empty' not in eggs_new, 'the faded egg is no longer the empty look'
    # ---- docs/232: the Fusion Menu on the layout rules, behind the flag ----
    fus = U.code_only(read(U.FUSION))
    assert 'local L: any = if Theme.Toybox then require(Shared.ToyboxLayout) else nil' in fus and fus.count('ToyboxLayout') == 1, 'FusionMenu requires the layout helpers behind Theme.Toybox only'
    assert 'Kit.fusionLayout(1, bodyW, bodyH, wide)' in fus and 'lay = nil' not in fus and 'if L then' in fus, 'the flag-on browse screen uses Kit.fusionLayout'
    for needle in ('Sel.autoFill(', 'Sel.toggle(', 'OddsCopy.fusionCalm', 'oddsSections(', 'state.acknowledged', 'state.mode, state.acknowledged = "confirm"', 'Sel.formatOdds', 'Sel.goalText(',
                   'Sel.filterOptions(', 'FusionMenu.setLeftInset', 'Sel.valuableReasons', 'resultBox(', 'Sel.LockedStageText', 'TagFit.fusionTabs'):
        assert needle in fus, 'the Fusion Menu keeps the function: ' + needle
    assert re.search(r'if L then GREY elseif value ~= nil then C\.blue else C\.card', fus), 'filter chips are grey under the flag'
    assert 'col.fuse.BackgroundColor3 = if ready then C.accent elseif L then GREY else C.card' in fus, 'FUSE is the one green button, grey while not ready'
    for needle in ('"Fill for me", UDim2.new(.62, -8, 0, T), UDim2.new(0, 6, 1, -(T + 6)), if L then GREY else C.accent', '"Clear", UDim2.new(.38, -8, 0, T), UDim2.new(.62, 2, 1, -(T + 6)), if L then GREY else C.red',
                   '"Filter", UDim2.fromOffset(T + 40, T), UDim2.new(1, -(T + 40), 0, y), if filterOn then C.blue else C.card'):
        assert needle in fus, 'flag off keeps the old button colours: ' + needle
    assert 'L.emptySlot(col.slots, cell.w, cell.h, i)' in fus, 'an empty fusion slot is a dashed cream placeholder'
    # ---- Fusion window frame, donor / result cards, one window at a time (lead Studio check 2026-11-14) ----
    compact_src = U.code_only(read(U.COMPACT))
    boot = U.code_only(read(U.BOOT))
    assert 'function M.frame()' in compact_src and 'm.panelW * m.scale' in compact_src and 'm.centerDx' in compact_src, 'ModalCompact.frame gives the shared window size and centre'
    assert 'compact.frame()' in fus and 'UDim2.new(.5, dx, .5, 0)' in fus and 'Vector2.new(.5, .5)' in fus, 'under the flag the Fusion window takes the shared window size and place'
    assert 'if L then applyToyboxFrame() return end' in fus, 'setLeftInset no longer shrinks the Toybox window'
    assert 'fusion.isOpen and fusion.isOpen() then fusion.close() end' in compact_src and compact_src.index('fusion.close()') < compact_src.index('c.scale.Scale = m.scale'), 'opening a shared-window screen closes the Fusion Menu first (flag on and off)'
    assert re.search(r'local function showFusionMenu\(\)\n\s*close\(\)[^\n]*\n(?:[^\n]*\n)*?\s*FusionMenu\.open\(\)', boot.replace('\r', '')) or 'showFusionMenu' in boot and re.search(r'showFusionMenu\(\)\s*close\(\)', boot), 'opening Fusion closes the shared window first'
    assert 'entry.dim.Visible = reason ~= nil and not L' in fus, 'no dark bar over a donor card that cannot be used'
    assert 'if child:IsA("UIStroke") then child.Transparency = 1 end' in fus, 'ink text loses the outline stroke too'
    assert 'if L then L.card(parent, "Result", resultSize, UDim2.new()) else' in fus and '"tier_" .. stageId' in fus and 'TierBadge' in fus, 'the result is a cream card with the tier badge picture'
    assert 'Chip.apply(badge, C.text, nil, true)' in fus, 'flag off keeps the old result badge'
    assert fus.count('C.accent, function') + len(re.findall(r'if L then GREY else C\.accent', fus)) >= 1, 'accent kept for the flag-off Fill button'
    for module in (eggs_new, idx_new):
        assert 'rbxassetid' not in module and 'Instance.new("ImageLabel")' not in module, 'no code-drawn art in the new screens'
        assert not re.search(r'MinTextSize\s*=\s*(\d|1[0-3])\b', module), 'no text floor under 14 px'
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
    'the Eggs bottom row drops below the body': (U.KIT, 'local by = nestsH + gut', 'local by = nestsH + gut + 8'),
    'the Eggs nest cards leave the 12 px gutter': (U.KIT, 'x = pad + (i - 1) * (cellW + gut), y = cardY', 'x = pad + (i - 1) * (cellW + gut + 2), y = cardY'),
    'the Eggs status line overlaps the button': (U.KIT, 'layout.status = {x = pad, y = pad, w = infoW - 2 * pad, h = E.statusH}', 'layout.status = {x = pad, y = pad, w = infoW - 2 * pad, h = bottomH}'),
    'the Eggs AUTO toggle turns coloured': (U.EGGSP, 'size(lay.auto), pos(lay.auto), GREY', 'size(lay.auto), pos(lay.auto), C.blue'),
    'the Eggs screen loads without the flag': (U.EGGS, 'if Theme.Toybox then return require(script.Parent.EggsPanels)', 'if true then return require(script.Parent.EggsPanels)'),
    'the Eggs nest tap is gone': (U.EGGSP, 'ctx.openNest(info.id)', 'nil'),
    'the Index bottom bar is cut off': (U.KIT, 'layout.bar = {x = 0, y = H - big, w = W, h = big}', 'layout.bar = {x = 0, y = 402 - big, w = W, h = big}'),
    'the Index grid leaves the right third empty': (U.KIT, 'layout.cellW = Kit.cellWidth(content, layout.columns, gut)', 'layout.cellW = 190'),
    'the Index grid runs into the bar': (U.KIT, 'layout.grid = {x = 0, y = 0, w = W, h = math.max(H - big - gut, 0)}', 'layout.grid = {x = 0, y = 0, w = W, h = math.max(H - big, 0)}'),
    'the Index FUSION button leaves the body': (U.KIT, 'layout.fusion = {x = W - I.fusionW, y = H - big, w = I.fusionW, h = big}', 'layout.fusion = {x = W - I.fusionW + 20, y = H - big, w = I.fusionW, h = big}'),
    'a second coloured Index button': (U.INDEXL, 'size(lay.prev), pos(lay.prev), GREY', 'size(lay.prev), pos(lay.prev), C.accent'),
    'the Index card says ??? again': (U.INDEXL, 'L.text(card, "?", UDim2.fromOffset(innerW, 28)', 'L.text(card, "???", UDim2.fromOffset(innerW, 28)'),
    'the Index list loads without the flag': (U.INDEX, 'if Theme.Toybox then -- BD-1194', 'if true then -- BD-1194'),
    'the Fusion panels drift apart': (U.KIT, 'layout.centre = {x = leftW + gut, y = top, w = centreW, h = PH}', 'layout.centre = {x = leftW + gut + 3, y = top, w = centreW, h = PH}'),
    'the Fusion body runs below the screen': (U.KIT, 'layout.fuse = {x = 0, y = ri.h - big, w = ri.w, h = big}', 'layout.fuse = {x = 0, y = ri.h - big + 6, w = ri.w, h = big}'),
    'the Fusion note touches FUSE': (U.KIT, 'layout.note = {x = 0, y = ri.h - big - gut - F.noteH, w = ri.w, h = F.noteH}', 'layout.note = {x = 0, y = ri.h - big - F.noteH, w = ri.w, h = F.noteH}'),
    'the Fusion FUSE button stays green when not ready': (U.FUSION, 'col.fuse.BackgroundColor3 = if ready then C.accent elseif L then GREY else C.card', 'col.fuse.BackgroundColor3 = if ready or L then C.accent else C.card'),
    'the Fusion Fill button turns green': (U.FUSION, '"Fill for me", UDim2.new(.62, -8, 0, T), UDim2.new(0, 6, 1, -(T + 6)), if L then GREY else C.accent', '"Fill for me", UDim2.new(.62, -8, 0, T), UDim2.new(0, 6, 1, -(T + 6)), C.accent'),
    'the Fusion empty slot is a black box again': (U.FUSION, 'L.emptySlot(col.slots, cell.w, cell.h, i)', 'W.box(col.slots, UDim2.new(), UDim2.new(), C.outline, 8)'),
    'the Fusion menu loads the layout without the flag': (U.FUSION, 'local L: any = if Theme.Toybox then require(Shared.ToyboxLayout) else nil', 'local L: any = require(Shared.ToyboxLayout)'),
    'the Fusion window stays narrow': (U.FUSION, 'frame.AnchorPoint, frame.Size, frame.Position = Vector2.new(.5, .5), UDim2.fromOffset(size.X, size.Y), UDim2.new(.5, dx, .5, 0)', 'frame.AnchorPoint = Vector2.new(.5, .5)'),
    'Fusion stays open under another screen': (U.COMPACT, 'if ok and type(fusion) == "table" and fusion.isOpen and fusion.isOpen() then fusion.close() end', 'if false then end'),
    'a dark bar covers the donor card': (U.FUSION, 'entry.dim.Visible = reason ~= nil and not L', 'entry.dim.Visible = reason ~= nil'),
    'the result card is yellow again': (U.FUSION, 'local box: Frame = if L then L.card(parent, "Result", resultSize, UDim2.new()) else', 'local box: Frame = if false then L.card(parent, "Result", resultSize, UDim2.new()) else'),
    'the empty nest shows the egg': (U.EGGSP, 'v.emptyNest.Visible, v.icon.Visible = empty, not empty', 'v.emptyNest.Visible, v.icon.Visible = false, true'),
    'the undiscovered silhouette is black again': (U.INDEXL, 'Color3.fromRGB(107, 90, 68), 0.35', 'Color3.new(0, 0, 0), 0'),
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
    print('layout ok: detail page rects at 1280x720 and a phone window, Eggs screen and Dino Index list at four windows, helpers, static rules')
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
