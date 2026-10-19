#!/usr/bin/env python3
"""BD-1107 / BD-1103 (docs/203): words in tags, ribbons and tab names are measured BEFORE they are drawn (src/shared/TagFit.luau, HatchTagLayout.luau).

Studio round 6 and 7 (500 px wide windows): the Fusion tabs read "EMERA" and "DIAMO", and on a Rainbow egg the "Rainbow egg!" tag was cut at the left edge of
the hatch card with its chips over each other. A shrink-to-fit label cannot go under its minimum size (14 px), so a long word in a short tag runs out of it.
These checks run the REAL TagFit and HatchTagLayout (pure numbers, no Studio, no drawing) with the plain estimate of the other layout checks (0.5 em per
character) and with the wider estimate TagFit itself uses:

  * TagFit: the size is the biggest that fits, never under the 14 px floor in design px; a too-wide word wraps, then takes a short word, and only the last
    resort is "..." (reported as not fitting); a word is never measured under the plain estimate.
  * Fusion tabs (the real words from FusionSelection): at 14 window sizes, with and without the left rail, every tab holds its words (title and sub line),
    the tabs do not overlap and are at least 44 px wide, the old "a third of the column" rule really failed at 500 px (a probe), a desktop window keeps three
    equal tabs, and a narrow window gets a full-width row instead of cut words.
  * Hatch tags: every subset of the ribbons (Shiny, a mutation, a long mutation, BIG, New pattern!, New colour!) and the stop tag, at the 14 px floor of 7
    window scales: nothing leaves the card (turned boxes included), nothing overlaps, nothing is taller than the room above the name, every word fits its box,
    nothing is cut with "...".
Mutants (each defect put back) must fail. Not Studio evidence: a real look at 500 x 465 and 848 x 423 is still needed (the Studio re-check row).
Usage: python tools/verify_tag_fit.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def wrapped(path, replacements=None):
    source = read(path)
    for old, new in replacements or []:
        assert old in source, 'mutant target missing in %s: %s' % (path, old)
        source = source.replace(old, new)
    return '(function()\n' + source + '\nend)()'


LUAU = r'''
local Mods = {}
local script = {Parent = {Config = "Config", PhoneScale = "PhoneScale", TagFit = "TagFit", ProgressionConfig = "ProgressionConfig"}}
local require = function(name) return Mods[name] end
Rect = nil
Mods.Config = @CONFIG@
Mods.PhoneScale = @PHONE@
Mods.TouchLayout = @TOUCH@
Mods.ProgressionConfig = @PROGRESSION@
Mods.TagFit = @TAGFIT@
local TagFit = Mods.TagFit
script.Parent.TouchLayout = "TouchLayout"
local Layout = @LAYOUT@
local Sel = @SEL@
local TouchLayout = Mods.TouchLayout
local failures = 0
local function check(ok, message) if not ok then failures += 1 print("FAIL " .. message) end return ok end
local function flat(text, size) return (utf8.len(text) or #text) * 0.5 * size end

-- ===== 1. TagFit =====
check(TagFit.floorSize(1) == 14 and TagFit.floorSize(0.57) == 25 and TagFit.floorSize(0.5) == 28 and TagFit.floorSize(2) == 14 and TagFit.floorSize(0) == 14, "floorSize: 14 design px at 1:1, 25 at 0.57, never under 14")
check(TagFit.width("EMERALD", 14) >= 62 and TagFit.width("EMERALD", 14) > TagFit.width("emerald", 14), "capitals are wider than small letters (EMERALD at 14 px is about 63 px: the Studio picture)")
check(TagFit.width("abc", 20) >= flat("abc", 20) and TagFit.width("Skip stops here", 18) >= flat("Skip stops here", 18) and TagFit.width("iii", 30) >= flat("iii", 30), "a word is never measured under the plain 0.5 em estimate")
check(TagFit.width("Rainbow egg!", 28) > TagFit.width("Rainbow egg!", 14) and TagFit.width("Rainbow egg! x", 14) > TagFit.width("Rainbow egg!", 14), "wider with more size and more letters")
local f = TagFit.fit("Rainbow egg!", 400, {maxSize = 24, minSize = 14})
check(f.fits and f.size == 24 and f.lines == 1 and not f.abbreviated, "plenty of room: the biggest size")
f = TagFit.fit("Rainbow egg!", 110, {maxSize = 24, minSize = 14})
check(f.fits and f.size < 24 and f.size >= 14 and f.width <= 110 and f.lines == 1, "a narrower box: a smaller size that holds it")
f = TagFit.fit("Rainbow egg!", 70, {maxSize = 24, minSize = 14, maxLines = 2})
check(f.fits and f.size == 14 and f.lines == 2 and f.width <= 70 and string.find(f.text, "\n", 1, true) ~= nil, "too narrow for one line at 14 px: two lines, still 14 px")
f = TagFit.fit("Rainbow egg!", 70, {maxSize = 24, minSize = 14})
check(not f.fits and f.width <= 70 and string.sub(f.text, -3) == "...", "one line only and no room: cut with '...' and reported as not fitting (never overflowing)")
f = TagFit.fit("Emerald", 40, {maxSize = 22, minSize = 14, short = {"Emer."}})
check(f.fits and f.abbreviated and f.text == "Emer." and f.width <= 40, "a short word is used before the cut")
f = TagFit.fit("SHINY", 1000, {maxSize = 26, minSize = 14})
check(f.size == 26 and f.height == math.ceil(26 * TagFit.LineHeight), "one line is 1.12 em high")

-- ===== 2. Fusion tabs (BD-1103): the real words, many windows =====
local items = {}
for i, s in Sel.Stages do local w = Sel.tabText(s.id) items[i] = {title = w.title, sub = w.sub} end
check(#items == 3 and items[2].title == "EMERALD" and items[3].title == "DIAMOND", "the real tab words are GOLD, EMERALD, DIAMOND")
local OPTS = {gap = 4, pad = 6, titleMax = 22, subMax = 16}
local WINDOWS = {{500, 465}, {500, 400}, {516, 481}, {498, 463}, {667, 375}, {667, 339}, {740, 340}, {844, 390}, {844, 354}, {848, 423}, {848, 481},
    {600, 700}, {700, 600}, {540, 520}, {1024, 768}, {1156, 793}, {1445, 841}, {1920, 1080}}
local wideCount, oldFails = 0, 0
local wideList = {}
for _, v in WINDOWS do
    local w, h = v[1], v[2]
    -- Bootstrap.showFusionMenu: the phone rail is a top bar (inset 0); a desktop-sized window keeps the left rail clear
    local inset = 0
    if h >= 500 then
        local layout = TouchLayout.compute({width = w, height = h, touch = false, navCount = 6, goals = true})
        inset = layout.rail.x + layout.rail.w * layout.rail.scale + 10
    end
    local bodyW = math.min(1180, w * .97 - inset) - 16
    local tag = string.format("Fusion tabs at %dx%d (rail inset %d, body %d)", w, h, inset, bodyW)
    local lay = TagFit.fusionTabs(items, bodyW, .38, OPTS)
    check(lay.fits, tag .. ": the words do not fit even the full-width row")
    check(#lay.tabs == 3, tag .. ": three tabs")
    if lay.wide then wideCount += 1 table.insert(wideList, string.format("%dx%d", w, h)) end
    -- when the row stays above the left column, the words really fit there; when it is wide, they really did not
    local single = TagFit.tabRow(items, bodyW * .38 - 6, OPTS)
    check(lay.wide == not single.fits, tag .. ": a wide row only when the left column cannot hold the words")
    check(lay.rowW == (if lay.wide then bodyW else bodyW * .38 - 6), tag .. ": the row width is the column's or the body's")
    for i, t in lay.tabs do
        local item = items[i]
        check(t.x >= -1e-6 and t.x + t.w <= lay.rowW + 1e-6, string.format("%s: tab %d (%d + %d) leaves the row (%d)", tag, i, t.x, t.w, lay.rowW))
        check(t.w >= 44, string.format("%s: tab %d is %d px wide, under the 44 px touch target", tag, i, t.w))
        if i > 1 then check(t.x >= lay.tabs[i - 1].x + lay.tabs[i - 1].w + OPTS.gap - 1e-6, tag .. ": tabs " .. (i - 1) .. " and " .. i .. " overlap or touch") end
        check(t.titleSize >= 14 and t.titleSize <= OPTS.titleMax and t.subSize >= 14 and t.subSize <= OPTS.subMax, string.format("%s: tab %d sizes %d / %d are outside 14 .. the maximum", tag, i, t.titleSize, t.subSize))
        local room = t.w - 2 * OPTS.pad
        check(flat(item.title, t.titleSize) <= room and TagFit.width(item.title, t.titleSize) <= room, string.format("%s: '%s' (%d px) needs %d of the %d px in its tab", tag, item.title, t.titleSize, TagFit.width(item.title, t.titleSize), room))
        check(flat(item.sub, t.subSize) <= room and TagFit.width(item.sub, t.subSize) <= room, string.format("%s: '%s' (%d px) needs %d of the %d px in its tab", tag, item.sub, t.subSize, TagFit.width(item.sub, t.subSize), room))
    end
    if w >= 1000 then
        check(not lay.wide and math.abs(lay.tabs[1].w - lay.tabs[3].w) < 1e-6 and math.abs(lay.tabs[1].w - lay.tabs[2].w) < 1e-6, tag .. ": a desktop window keeps three equal tabs above the list")
    end
    -- the OLD rule: a third of the left column, minus 4: did its words fit at 14 px? (probe: it did not at 500 px)
    local third = (bodyW * .38 - 6) / 3 - 4
    local fitsOld = true
    for _, item in items do
        if TagFit.width(item.title, 14) > third or TagFit.width(item.sub, 14) > third then fitsOld = false end
    end
    if not fitsOld then oldFails += 1 end
end
check(oldFails >= 4, "probe lost sensitivity: the old third-of-the-column tab rule must fail on the narrow windows (" .. oldFails .. ")")
check(wideCount >= 3 and wideCount < #WINDOWS, "a narrow window gets the wide row, a big one does not (" .. wideCount .. " of " .. #WINDOWS .. ")")

-- ===== 3. Hatch tags (BD-1107): every subset, many scales =====
local SCALES = {1, 0.9, 0.8, 0.71, 0.64, 0.57, 0.5}
local CATALOG = {
    {kind = "ribbon", side = "left", text = "SHINY", minW = 170, tilt = -7},
    {kind = "ribbon", side = "left", text = "BLOOD MOON", minW = 210, tilt = -4},
    {kind = "stop", side = "left", text = "Rainbow egg!", line = "Skip stops here"},
    {kind = "ribbon", side = "right", text = "BIG", minW = 150, tilt = 7},
    {kind = "ribbon", side = "right", text = "New pattern!", minW = 200, tilt = 5},
    {kind = "ribbon", side = "right", text = "New colour!", minW = 200, tilt = 5},
}
local function turned(p) local hw, hh = Layout.halfExtent(p.w, p.h, p.tilt) return {x = p.cx - hw, y = p.cy - hh, w = 2 * hw, h = 2 * hh} end
local function overlaps(a, b) return a.x < b.x + b.w - .5 and b.x < a.x + a.w - .5 and a.y < b.y + b.h - .5 and b.y < a.y + a.h - .5 end
local planned, subsets = 0, 0
local function checkPlan(name, items, scale)
    local floor = TagFit.floorSize(scale)
    local placed, ok = Layout.plan(items, scale)
    local tag = string.format("%s at scale %.2f", name, scale)
    planned += 1
    check(ok and #placed == #items, tag .. ": the tags do not fit above the name")
    for i, p in placed do
        local r = turned(p)
        check(r.x >= Layout.Margin - 1e-6 and r.x + r.w <= Layout.BodyW - Layout.Margin + 1e-6 and r.y >= 4 - 1e-6 and r.y + r.h <= Layout.Bottom + 1e-6,
            string.format("%s: '%s' lies at %d,%d %dx%d, outside the card or over the name", tag, p.text, r.x, r.y, r.w, r.h))
        check(p.size >= floor and p.size >= 14 and (p.lineSize == nil or p.lineSize >= floor), string.format("%s: '%s' is %d px, the floor here is %d", tag, p.text, p.size, floor))
        local room = if p.kind == "stop" then p.w - 2 * Layout.Tag.pad else p.w - Layout.Ribbon.icon - Layout.Ribbon.right
        for line in string.gmatch(p.text .. "\n", "(.-)\n") do
            check(flat(line, p.size) <= room + 1e-6 and TagFit.width(line, p.size) <= room + 1e-6, string.format("%s: '%s' needs %d of %d px", tag, line, TagFit.width(line, p.size), room))
            check(string.sub(line, -3) ~= "...", string.format("%s: '%s' was cut short", tag, line))
        end
        if p.kind == "stop" then
            check(flat(p.line or "", p.lineSize or 14) <= room and string.sub(p.line or "", -3) ~= "...", tag .. ": the line under the stop title does not fit")
            check(p.h >= math.ceil(p.textLines * p.size * TagFit.LineHeight) + math.ceil(p.lineLines * (p.lineSize or 14) * TagFit.LineHeight), tag .. ": the stop tag is shorter than its two parts")
        else
            check(p.h >= math.ceil(p.textLines * p.size * TagFit.LineHeight), string.format("%s: ribbon '%s' is shorter than its words", tag, p.text))
        end
        for j = i + 1, #placed do
            check(not overlaps(r, turned(placed[j])), string.format("%s: '%s' overlaps '%s'", tag, p.text, placed[j].text))
        end
    end
    return placed
end
local N = #CATALOG
for mask = 1, 2 ^ N - 1 do
    local items = {}
    for i = 1, N do if bit32.band(mask, bit32.lshift(1, i - 1)) ~= 0 then table.insert(items, CATALOG[i]) end end
    subsets += 1
    for _, scale in SCALES do checkPlan("tags " .. mask, items, scale) end
end
-- the longest words: a long mutation name wraps onto two lines (ribbon and tag) and still fits
for _, scale in {1, 0.57} do
    local placed = checkPlan("long mutation", {
        {kind = "ribbon", side = "left", text = "BLOOD MOON RISING", minW = 210, tilt = -4},
        {kind = "stop", side = "left", text = "Blood Moon Rising!", line = "Skip stops here"},
    }, scale)
    check(placed[1].textLines == 2 or scale == 1, "the long ribbon word wraps onto two lines in a small window")
end
-- all six at once on the left: the stop tag moves to the right side instead of running into the name
local placed = checkPlan("crowded left", {
    {kind = "ribbon", side = "left", text = "SHINY", minW = 170, tilt = -7},
    {kind = "ribbon", side = "left", text = "BLOOD MOON RISING", minW = 210, tilt = -4},
    {kind = "stop", side = "left", text = "Rainbow egg!", line = "Skip stops here"},
}, 0.57)
check(placed[3].side == "right", "a stop tag that does not fit the left column goes to the right one")
-- a desktop window keeps the old ribbon numbers where the words fit: first ribbon at the old centre line, preset widths, 44 px high, 26 px words
local desktop = Layout.plan({CATALOG[1], CATALOG[4]}, 1)
check(desktop[1].cy == 52 and desktop[1].w == 170 and desktop[1].h == 44 and desktop[1].size == 26 and desktop[2].cy == 52 and desktop[2].w == 150, "desktop: SHINY and BIG keep the old centre line, widths and size")
-- the scale decides the floor: a smaller window never gets smaller words, only bigger ones
local big, small = Layout.plan({CATALOG[3]}, 1), Layout.plan({CATALOG[3]}, 0.5)
check(small[1].size > big[1].size and small[1].size * 0.5 >= 14, "a smaller card gets bigger words (14 px on screen)")
if failures > 0 then error(failures .. " tag-fit check(s) failed") end
print(string.format("Tag fit passed: TagFit maths, Fusion tabs at %d windows (wide row at %d: %s; the old third rule fails at %d), %d tag plans (%d subsets x %d scales + the long and crowded cases)",
    #WINDOWS, wideCount, table.concat(wideList, " "), oldFails, planned, subsets, #SCALES))
'''


def build_script(replacements=None):
    replacements = replacements or {}
    source = LUAU
    for key, path in (('@CONFIG@', 'src/shared/Config.luau'), ('@PHONE@', 'src/shared/PhoneScale.luau'), ('@TOUCH@', 'src/shared/TouchLayout.luau'),
                      ('@PROGRESSION@', 'src/shared/ProgressionConfig.luau'), ('@TAGFIT@', 'src/shared/TagFit.luau'), ('@LAYOUT@', 'src/shared/HatchTagLayout.luau'),
                      ('@SEL@', 'src/shared/FusionSelection.luau')):
        name = Path(path).stem
        source = source.replace(key, wrapped(path, replacements.get(name)))
    return source


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'tag_fit.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


MUTANTS = {
    'a word is measured under the plain estimate (capitals as small letters, no floor of 0.5 em)': {
        'TagFit': [('    return math.ceil(math.max(em, TagFit.FlatEm * count) * size)', '    return math.ceil(0.3 * count * size)')],
    },
    'capital letters are measured as small ones (EMERALD is cut again)': {
        'TagFit': [('elseif (code >= 65 and code <= 90) or (code >= 48 and code <= 57) then em += TagFit.Em.capital', 'elseif false then em += TagFit.Em.capital')],
    },
    'the floor in design px ignores the window scale': {
        'TagFit': [('    return math.max(f, math.ceil(f / screenScale - 1e-9))', '    return f')],
    },
    'a too-wide word is not wrapped': {
        'TagFit': [('        if maxLines > 1 then', '        if false then')],
    },
    'a word that cannot fit is returned as if it fitted': {
        'TagFit': [('    return result({cut .. "..."}, size, true, false)', '    return result({cut .. "..."}, size, true, true)')],
    },
    'the Fusion tabs are always a third of the column (the old rule)': {
        'TagFit': [('    local equal = biggest <= equalW', '    local equal = true')],
    },
    'the Fusion tab row never gets wide': {
        'TagFit': [('    if row.fits then return', '    if true then return')],
    },
    'the tabs ignore the space between them': {
        'TagFit': [('        x += w + opts.gap', '        x += w')],
    },
    'the hatch tags are not stacked (they all sit on the first line)': {
        'HatchTagLayout': [('        local cy = if top == nil then L.FirstCy else top + hh', '        local cy = L.FirstCy')],
    },
    'the hatch tags ignore the card margin (a tag reaches past the left edge)': {
        'HatchTagLayout': [('p.cx = if side == "left" then L.Margin + hw else L.BodyW - L.Margin - hw', 'p.cx = if side == "left" then hw - 40 else L.BodyW - L.Margin - hw')],
    },
    'the tilt of a ribbon is not counted in its size on the card': {
        'HatchTagLayout': [('    return (w * math.cos(r) + h * math.sin(r)) / 2, (w * math.sin(r) + h * math.cos(r)) / 2', '    return w / 2, h / 2')],
    },
    'the tag words are laid out for 14 design px at every scale': {
        'HatchTagLayout': [('    local floor = TagFit.floorSize(screenScale)', '    local floor = 14')],
    },
    'a ribbon word that does not fit is cut instead of wrapped': {
        'HatchTagLayout': [('minSize = floor, maxLines = 2})\n    local w = math.min(L.MaxW, math.max(item.minW or 0', 'minSize = floor, maxLines = 1})\n    local w = math.min(L.MaxW, math.max(item.minW or 0')],
    },
    'the stop tag never moves to the other side': {
        'HatchTagLayout': [('            if cy2 + hh <= L.Bottom + 1e-6 then side, cy, nextY = other, cy2, next2 else ok = false end', '            ok = false')],
    },
    'the stop tag is as short as its title only': {
        'HatchTagLayout': [('    local h = title.height + line.height + 8', '    local h = title.height + 8')],
    },
}


def static_checks():
    fusion = read('src/client/FusionMenu.luau')
    assert 'TagFit.fusionTabs(' in fusion and 'require(Shared.TagFit)' in fusion, 'FusionMenu sizes its tabs with TagFit (BD-1103)'
    assert 'UDim2.new(1 / 3, -4, 0, tabHeight)' not in fusion, 'FusionMenu no longer cuts its tabs to a third of the column (the old rule)'
    hatch = read('src/client/HatchSequence.luau')
    assert 'TagLayout.plan(' in hatch and 'require(Shared.HatchTagLayout)' in hatch, 'HatchSequence places its ribbons and the stop tag with HatchTagLayout (BD-1107)'
    assert 'FxPlan.Card.stopTag' not in hatch and 'addRibbon("' not in hatch, 'HatchSequence has no fixed ribbon or stop-tag spot any more'
    ribbon = hatch[hatch.index('local function ribbon('):hatch.index('-- What the server committed')]
    assert 'TextScaled, label.TextSize, label.ZIndex' in ribbon and 'WHITE, false, p.size' in ribbon, 'a ribbon word is a measured size, never shrink-to-fit'
    layout = read('src/shared/HatchTagLayout.luau')
    tagfit = read('src/shared/TagFit.luau')
    for name, text in (('HatchTagLayout', layout), ('TagFit', tagfit)):
        for banned in ('Instance.new', 'game:GetService', 'workspace', 'os.clock', 'task.'):
            assert banned not in text, name + ' stays pure: ' + banned
    plan = read('src/shared/HatchFxPlan.luau')
    # the column rects the sparkle keep-out uses are the layout's own numbers
    import re
    cols = re.search(r'tagColumns = \{left = \{(\d+), (\d+), (\d+), (\d+)\}, right = \{(\d+), (\d+), (\d+), (\d+)\}\}', plan)
    assert cols, 'HatchFxPlan.Card.tagColumns'
    values = [int(v) for v in cols.groups()]
    margin = int(re.search(r'L\.Margin = (\d+)', layout).group(1))
    maxw = int(re.search(r'L\.MaxW = (\d+)', layout).group(1))
    bodyw = int(re.search(r'L\.BodyW = (\d+)', layout).group(1))
    bottom = int(re.search(r'L\.Bottom = (\d+)', layout).group(1))
    assert values[0] <= margin and values[2] >= margin + maxw, 'the left keep-out column covers the layout\'s left column'
    assert values[4] <= bodyw - margin - maxw and values[6] >= bodyw - margin, 'the right keep-out column covers the layout\'s right column'
    assert values[3] >= bottom and values[7] >= bottom, 'the keep-out columns reach down to the lowest tag'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    static_checks()
    result = run(args.runner, build_script())
    print(result.stdout, end='')
    if result.returncode != 0 or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            outcome = run(args.runner, build_script(replacements))
            assert outcome.returncode != 0, 'MUTANT SURVIVED (the check did not notice): ' + name
            print('  mutant caught: ' + name)
    print('Tag fit: static wiring ok, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
