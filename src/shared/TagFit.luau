--!strict
-- BD-1107 / BD-1103 (docs/203): the ONE text-fit helper for tags, ribbons and tab names. Pure numbers, no Instances, no services.
-- Why it exists: a label that shrinks to fit (TextScaled) cannot go under its minimum size, so a long word in a short tag simply runs out of the tag and is cut
-- (Studio round 6 and 7: "EMERA / DIAMO" on the Fusion tabs, "Rainbow egg!" cut at the left edge of the hatch card). A caller that uses this helper
-- measures the words with the estimate below BEFORE it draws: the text size is the biggest size that fits the box, never under the floor (14 px on screen),
-- then the words wrap onto two lines, then a kid-friendly short word is used, and only the very last resort is "...". The answer always says whether it fits.
--
-- Width estimate (the real font is not available offline): FredokaOne is wide, capital letters and digits most of all. Every character costs a fraction of
-- the text size (an "em"). The numbers below are deliberately a little ABOVE the real ones (measured on the Studio pictures: "EMERA" at 14 px is about 45 px
-- wide, 0.64 em a capital), so a tag sized with them has room to spare. The offline layout checks judge with the plainer flat estimate of the other checks
-- (0.5 em for every character, tools/menu_layout_smoke.luau), which is always smaller than this one.
local TagFit = {}

TagFit.MinText = 14 -- px on screen (docs/114 s4.4)
TagFit.Em = {small = 0.55, capital = 0.64, narrow = 0.34, space = 0.32}
TagFit.FlatEm = 0.5 -- the plain estimate of tools/menu_layout_smoke.luau and tools/small_window_smoke.luau: a word is never measured under it
TagFit.LineHeight = 1.12 -- one line is this many times the text size high
local NARROW = {i = true, l = true, j = true, t = true, f = true, r = true, ["!"] = true, ["."] = true, [","] = true, [":"] = true, [";"] = true, ["'"] = true, ["|"] = true}

function TagFit.chars(text: string): number
    return utf8.len(text) or #text
end

-- Width of one line of `text` at `size` px (design px), estimated.
function TagFit.width(text: string, size: number): number
    local em = 0
    local count = 0
    for _, code in utf8.codes(text) do
        count += 1
        local c = utf8.char(code)
        if c == " " then em += TagFit.Em.space
        elseif NARROW[c] then em += TagFit.Em.narrow
        elseif (code >= 65 and code <= 90) or (code >= 48 and code <= 57) then em += TagFit.Em.capital
        else em += TagFit.Em.small end
    end
    return math.ceil(math.max(em, TagFit.FlatEm * count) * size) -- never under the plain 0.5 em per character that the layout checks use
end

-- The design size that renders at least `floorPx` on screen where one design px is `screenScale` screen px (ModalCompact's floor rule for text).
function TagFit.floorSize(screenScale: number, floorPx: number?): number
    local f = floorPx or TagFit.MinText
    if screenScale <= 0 then return f end
    return math.max(f, math.ceil(f / screenScale - 1e-9))
end

export type Fit = {text: string, size: number, lines: number, width: number, height: number, fits: boolean, abbreviated: boolean}
export type Options = {maxSize: number, minSize: number, maxLines: number?, short: {string}?}

-- Greedy word wrap at `size` into at most `maxLines` lines no wider than `boxW`. Returns the lines, or nil when the words do not fit.
local function wrap(text: string, boxW: number, size: number, maxLines: number): {string}?
    local lines: {string} = {}
    local current = ""
    for word in string.gmatch(text, "%S+") do
        local try = if current == "" then word else current .. " " .. word
        if TagFit.width(try, size) <= boxW then
            current = try
        else
            if current == "" then return nil end -- one word alone is wider than the box
            table.insert(lines, current)
            current = word
            if TagFit.width(current, size) > boxW then return nil end
        end
    end
    if current ~= "" then table.insert(lines, current) end
    if #lines > maxLines then return nil end
    return lines
end

local function result(lines: {string}, size: number, abbreviated: boolean, fits: boolean): Fit
    local widest = 0
    for _, l in lines do widest = math.max(widest, TagFit.width(l, size)) end
    return {text = table.concat(lines, "\n"), size = size, lines = #lines, width = widest, height = math.ceil(#lines * size * TagFit.LineHeight), fits = fits, abbreviated = abbreviated}
end

-- Fit `text` into a box `boxW` wide: the biggest whole size in [minSize, maxSize] that holds it on one line; else wrapped onto up to maxLines lines at the
-- smallest size; else the same two steps for each short word in opts.short (in the order given); else the text cut with "..." (fits = false).
function TagFit.fit(text: string, boxW: number, opts: Options): Fit
    local maxLines = opts.maxLines or 1
    local candidates: {string} = {text}
    for _, alt in opts.short or {} do table.insert(candidates, alt) end
    for index, candidate in candidates do
        local abbreviated = index > 1
        for size = math.floor(opts.maxSize), math.ceil(opts.minSize), -1 do
            if TagFit.width(candidate, size) <= boxW then return result({candidate}, size, abbreviated, true) end
        end
        if maxLines > 1 then
            local lines = wrap(candidate, boxW, math.ceil(opts.minSize), maxLines)
            if lines then return result(lines, math.ceil(opts.minSize), abbreviated, true) end
        end
    end
    -- last resort: cut the words (never overflow the box); this is reported as not fitting
    local size = math.ceil(opts.minSize)
    local cut = text
    while #cut > 1 and TagFit.width(cut .. "...", size) > boxW do cut = string.sub(cut, 1, #cut - 1) end
    return result({cut .. "..."}, size, true, false)
end

-- A row of tabs {title, sub} in `availW` px. When every tab has what its longer line needs at the floor size (plus `pad` px each side) in an equal share of
-- the row, the tabs are equal (the old look). Otherwise every tab gets what it needs and the spare room is shared equally. fits = false when even the floor
-- sizes need more than `availW` (the caller then uses a wider row). Returns the tabs' x and w (px from the left of the row, a `gap` between tabs) and the
-- biggest sizes that fit each tab.
export type Tab = {x: number, w: number, titleSize: number, subSize: number}
export type TabOptions = {gap: number, pad: number, titleMax: number, subMax: number, minText: number?}
function TagFit.tabRow(items: {{title: string, sub: string}}, availW: number, opts: TabOptions): {fits: boolean, need: number, tabs: {Tab}}
    local floor = opts.minText or TagFit.MinText
    local count = #items
    local needs: {number} = {}
    local total = opts.gap * (count - 1)
    local biggest = 0
    for i, item in items do
        needs[i] = 2 * opts.pad + math.max(TagFit.width(item.title, floor), TagFit.width(item.sub, floor))
        total += needs[i]
        biggest = math.max(biggest, needs[i])
    end
    local equalW = (availW - opts.gap * (count - 1)) / count
    local equal = biggest <= equalW
    local spare = availW - total
    local tabs: {Tab} = {}
    local x = 0
    for i, item in items do
        local w = if equal then equalW else needs[i] + math.max(spare, 0) / count
        local inner = w - 2 * opts.pad
        local t = TagFit.fit(item.title, inner, {maxSize = opts.titleMax, minSize = floor})
        local s = TagFit.fit(item.sub, inner, {maxSize = opts.subMax, minSize = floor})
        tabs[i] = {x = x, w = w, titleSize = t.size, subSize = s.size}
        x += w + opts.gap
    end
    return {fits = equal or spare >= 0, need = total, tabs = tabs}
end

-- The Fusion menu's tab row (BD-1103). bodyW = the width of the Fusion body in px; the tabs sit above the left column (`leftShare` of the body less 6 px)
-- when their words fit there, else the row takes the whole body width and the three columns start under it (wide = true).
export type TabLayout = {wide: boolean, rowW: number, fits: boolean, tabs: {Tab}}
function TagFit.fusionTabs(items: {{title: string, sub: string}}, bodyW: number, leftShare: number, opts: TabOptions): TabLayout
    local leftW = bodyW * leftShare - 6
    local row = TagFit.tabRow(items, leftW, opts)
    if row.fits then return {wide = false, rowW = leftW, fits = true, tabs = row.tabs} end
    local whole = TagFit.tabRow(items, bodyW, opts)
    return {wide = true, rowW = bodyW, fits = whole.fits, tabs = whole.tabs}
end

return TagFit
