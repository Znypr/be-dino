--!strict
-- BD-1237 (docs/240 order step 4, style tile v3 boards 11-13): the pure half of the menus on the style rules R1-R8: Egg chances (kid words, the exact
-- numbers one tap away), the Food guide (real food art, cream cards), the weather title card and the toast cards. Plain numbers and strings, no
-- engine call, so tools/verify_menus_cohesion.py runs every function with the pinned Luau runtime: the kid chances, the trimmed percents, every
-- rect inside its body and nothing overlapping (R8), buttons never under 44 px on screen. Numbers PROVISIONAL (LEAD), from Shared/ToyboxKit.
-- Read only while Config.MenusCohesionEnabled is true (MenusCohesion, Toasts, WeatherTitle, FusionWidgets ask for it).
local Kit = require(script.Parent.ToyboxKit)

local R = {}
export type Rect = {x: number, y: number, w: number, h: number}

local function rect(x: number, y: number, w: number, h: number): Rect
    return {x = math.floor(x), y = math.floor(y), w = math.max(0, math.floor(w)), h = math.max(0, math.floor(h))}
end

-- The kit colours as 0..255 triples (the client turns them into Color3): cream panel, lighter card, dark ink, muted label ink, the outline.
R.Cream, R.Card, R.Ink, R.Muted, R.Outline = Kit.Tone.panel, Kit.Tone.card, Kit.Tone.value, Kit.Tone.label, Kit.Outline

-- 1234567 -> "1,234,567"
function R.grouped(n: number): string
    local s = tostring(math.floor(n + 0.5))
    local out = s
    while true do
        local next, count = string.gsub(out, "^(-?%d+)(%d%d%d)", "%1,%2")
        out = next
        if count == 0 then break end
    end
    return out
end

-- R6 kid copy: a percent as words a child reads at a glance. 100 -> "Always", 0 -> "Never", 50 and up -> "8 in 10" (never "10 in 10" below 100),
-- under 50 -> "1 in N" with N rounded to two figures ("1 in 4", "1 in 14", "1 in 250", "1 in 1,200"). The exact number stays one tap away.
function R.kidChance(percent: number): string
    if percent >= 100 then return "Always" end
    if percent <= 0 then return "Never" end
    if percent >= 50 then return string.format("%d in 10", math.clamp(math.floor(percent / 10 + 0.5), 5, 9)) end
    local n = 100 / percent
    if n >= 10 then
        local unit = 10 ^ (math.floor(math.log10(n)) - 1)
        n = math.floor(n / unit + 0.5) * unit
    else
        n = math.floor(n + 0.5)
    end
    return "1 in " .. R.grouped(math.max(2, n))
end

-- R6: "Compy: 36.4000%" -> "Compy: 36.4%", "x: 1.0000%" -> "x: 1%". Only trailing zeros go, so the number stays exact.
function R.trimPercents(line: string): string
    local out = string.gsub(line, "(%d+)%.(%d-)0+%%", function(whole: string, frac: string): string
        return if frac == "" then whole .. "%" else whole .. "." .. frac .. "%"
    end)
    return out
end

-- The Food guide (style tile v3 board 12): the four kinds the world has, each with its V3 food mesh (ReplicatedStorage.GeneratedWorld, the
-- approved Roblox meshes of BD-1208) as the picture. growth = the points the server gives (FoodService); words are the kid copy of the mockup.
R.Food = table.freeze({
    table.freeze({kind = "berry", name = "Berries", growth = 1, mesh = "food_v3_berry_a"}),
    table.freeze({kind = "fruit", name = "Fruit", growth = 4, mesh = "food_v3_fruit_a"}),
    table.freeze({kind = "egg", name = "Eggs", growth = 15, mesh = "food_v3_egg_a"}),
    table.freeze({kind = "amber", name = "Amber", growth = 50, mesh = "food_v3_amber_a"}),
})
function R.growChip(growth: number): string return "+" .. growth .. " grow" end
function R.foodFooter(eggs: number): string return string.format("Eat 500 food for about %d eggs. Storms add more!", eggs) end

-- `count` buttons right-aligned at the foot of the body (the ScreensCohesionLayout rule): 220 wide, narrower only when the row would not fit.
function R.buttonRow(bodyW: number, bodyH: number, scale: number, count: number): {Rect}
    local h = Kit.buttonHeights(scale)
    local n = math.max(1, count)
    local w = math.min(220, Kit.cellWidth(bodyW, n, Kit.Gutter))
    local rowW = w * n + Kit.Gutter * (n - 1)
    local out = {}
    for i = 1, count do table.insert(out, rect(bodyW - rowW + (i - 1) * (w + Kit.Gutter), bodyH - h, w, h)) end
    return out
end

-- Egg chances (board 11): one cream panel over the button row; the list scrolls inside the panel, so no word ever sits on the studs (R2).
R.RowH, R.GroupH, R.NoteLineH = 30, 34, 22
function R.odds(bodyW: number, bodyH: number, scale: number, buttons: number)
    local h = Kit.buttonHeights(scale)
    local panel = rect(0, 0, bodyW, bodyH - Kit.Gutter - h)
    local list = rect(Kit.PanelPad, Kit.PanelPad, panel.w - Kit.PanelPad * 2, panel.h - Kit.PanelPad * 2)
    return {panel = panel, list = list, buttons = R.buttonRow(bodyW, bodyH, scale, buttons)}
end

-- Food guide (board 12): four equal cream cards in a row, one cream strip with the footer line under them; no button (the X closes it).
R.FooterH = 40
function R.food(bodyW: number, bodyH: number, count: number)
    local footer = rect(0, bodyH - R.FooterH, bodyW, R.FooterH)
    local cardH = bodyH - R.FooterH - Kit.Gutter
    local w = Kit.cellWidth(bodyW, count, Kit.Gutter)
    local cards = {}
    for i = 1, count do table.insert(cards, rect((i - 1) * (w + Kit.Gutter), 0, w, cardH)) end
    return {cards = cards, footer = footer}
end
-- Inside one food card: the picture (as big as fits, at most 140), the name, the grow chip, centred as one block.
function R.foodCard(card: Rect)
    local pad = Kit.PanelPad
    local nameH, chipH = Kit.Type.heading + 8, 28
    local pic = math.clamp(card.h - pad * 2 - nameH - chipH - 8, 32, math.min(140, card.w - pad * 2))
    local block = pic + 4 + nameH + chipH
    local top = math.max(pad, math.floor((card.h - block) / 2))
    local picture = rect((card.w - pic) / 2, top, pic, pic)
    local name = rect(pad, picture.y + pic + 4, card.w - pad * 2, nameH)
    local chipW = math.min(card.w - pad * 2, 96)
    local chip = rect((card.w - chipW) / 2, name.y + nameH, chipW, chipH)
    return {picture = picture, name = name, chip = chip}
end

-- The weather title card (board 13): the weather's own icon (UIIconAssets) over a white word with an ink outline, the line under it in a cream
-- chip. No colour on the word (R4: purple and gold are rarity colours). Icon ids by weather id; nil = no icon (R5: never a stand-in).
R.WeatherIcon = table.freeze({rain = "rain", thunder = "thunder", blizzard = "blizzard", volcano = "volcano", aurora = "aurora", quake = "quake", bloodmoon = "bloodmoon"})
R.TitleOutline = 4

-- The toast card (style tile v2 board 7): cream with an ink outline, the kind colour only on the thin bar at its left edge; words ink, on the scale.
R.Toast = table.freeze({title = Kit.Type.heading, detail = Kit.Type.small, count = Kit.Type.heading, stroke = Kit.PanelStroke})

-- True when `inner` lies inside a box of w x h; true when two rects overlap (R8).
function R.inside(inner: Rect, w: number, h: number): boolean
    return inner.x >= 0 and inner.y >= 0 and inner.x + inner.w <= w and inner.y + inner.h <= h
end
function R.overlap(a: Rect, b: Rect): boolean
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
end

return R
