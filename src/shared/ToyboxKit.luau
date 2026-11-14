--!strict
-- BD-1177 (docs/228 board 1, docs/230): the "Toybox" UI kit as plain numbers. No engine call, no clock, no RNG: tools/verify_toybox_ui.py
-- runs this file with the pinned Luau runtime and measures every slice rect below against the real PNGs.
-- The art is Blender renders (resources/ui/v2/toybox/final, source assets/blender/ui/toybox-kit-v1.blend; the owner picked draft A on
-- 2026-11-13). Code only places and slices the pictures; it draws none of them (docs/72). Ids live in AssetSlots.Images ("" until the
-- upload is bound with tools/bind_assets.py); a group whose ids are not all bound keeps today's look (Kit.ready).
local Kit = {}

Kit.MinText = 14 -- docs/72 floor: no text under 14 px
Kit.MinClose = 48 -- docs/202 R6 / BD-1117: the X is a square of at least 48 px on screen
Kit.StrokeSmall, Kit.StrokeBig, Kit.StrokeBigFrom = 3, 3, 28 -- owner 2026-11-14 (C-57): text outline 3 px at every size (picked 4 px, then after seeing it in Studio: "3px was better")
Kit.DropPixels = 3 -- the dark copy of a title or button word sits this far under it
Kit.Outline = {13, 15, 20} -- the same dark as Theme.Colors.outline / TextStyle.Dark

Kit.HeaderColours = {"amber", "green", "blue", "purple", "dark", "cream", "red"}
Kit.ButtonColours = {"green", "grey", "gold", "blue", "red", "purple", "dark"}
Kit.CardRarities = {"common", "uncommon", "rare", "epic", "legendary", "mythic"}

type Asset = {slot: string, file: string, w: number, h: number, slice: {number}?, fit: string?}
-- slice = {x0, y0, x1, y1}: the stretching centre of the 9-slice in picture pixels (Roblox Rect.new(x0, y0, x1, y1)).
--   header (512x128): the centre is the stripe-free band between the first and the second shine stripe, so no stripe is ever stretched;
--     fit = "height": the slice scale is height / 128, so nothing stretches up or down either. Corner 21 px, outline 5 px, drop 11 px.
--   button (256x112): corner 16 px, outline 4 px, drop 8 px; the two flat tones meet at y 51..52 inside the centre and stretch as flat colour.
--   card (256x320): the centre is a stud-free patch of the light top band, so the studs keep their shape (they stay in the right and bottom caps).
--   frame (256x256): corner 30 px, edge 10 px (bottom 14 px with the drop); flat centre.
local HEADER_SLICE, BUTTON_SLICE, CARD_SLICE, FRAME_SLICE = {150, 30, 224, 98}, {24, 20, 232, 88}, {70, 34, 108, 92}, {36, 36, 220, 220}
local assets: {[string]: Asset} = {}
local function add(slot: string, file: string, w: number, h: number, slice: {number}?, fit: string?)
    assets[slot] = {slot = slot, file = file, w = w, h = h, slice = slice, fit = fit}
end
for _, colour in Kit.HeaderColours do add("toybox_header_" .. colour, "header-" .. colour .. ".png", 512, 128, HEADER_SLICE, "height") end
for _, colour in Kit.ButtonColours do add("toybox_button_" .. colour, "button-" .. colour .. ".png", 256, 112, BUTTON_SLICE) end
for _, rarity in Kit.CardRarities do add("toybox_card_" .. rarity, "card-" .. rarity .. ".png", 256, 320, CARD_SLICE) end
add("toybox_close", "close.png", 128, 128) -- drawn whole (Fit), never sliced
add("toybox_panel_frame", "panel-frame.png", 256, 256, FRAME_SLICE)
add("toybox_studs_tile", "studs-tile.png", 256, 256) -- tiled, never sliced
Kit.Assets = assets
Kit.Folder = "resources/ui/v2/toybox/final"

Kit.SliceScale = 0.5 -- buttons, cards and the frame are drawn at half picture size: button corner 8 px, frame corner 15 px
Kit.StudTile = 128 -- px of one studs-tile repeat on a window (4 x 4 studs, 32 px apart)
Kit.StudInset = {left = 5, top = 5, right = 5, bottom = 7} -- the frame edge at half size: the studs stay inside it
Kit.StudCorner = 10

-- The groups: a group is used only when every id of it is bound, so a window never shows half a kit.
Kit.Groups = {"header", "button", "card", "close", "panel"}
function Kit.slots(group: string): {string}
    local out = {}
    if group == "header" then for _, c in Kit.HeaderColours do table.insert(out, "toybox_header_" .. c) end
    elseif group == "button" then for _, c in Kit.ButtonColours do table.insert(out, "toybox_button_" .. c) end
    elseif group == "card" then for _, r in Kit.CardRarities do table.insert(out, "toybox_card_" .. r) end
    elseif group == "close" then out = {"toybox_close"}
    elseif group == "panel" then out = {"toybox_panel_frame", "toybox_studs_tile"} end
    return out
end
local function valid(id: any): boolean
    return type(id) == "string" and string.match(id, "^rbxassetid://%d+$") ~= nil
end
-- The bound id of a slot, or nil while it is empty or malformed (never an invented id).
function Kit.image(images: {[string]: any}, slot: string): string?
    local id = images[slot]
    return if assets[slot] ~= nil and valid(id) then id else nil
end
function Kit.ready(images: {[string]: any}, group: string): boolean
    local list = Kit.slots(group)
    if #list == 0 then return false end
    for _, slot in list do if Kit.image(images, slot) == nil then return false end end
    return true
end

-- Places and their header colour (owner, docs/228): amber Crystal Shop, green Potions, blue Dinos / Index, purple Fusion, cream Eggs,
-- dark Settings. Red is kept for the X only, so no place uses the red header.
Kit.PlaceHeader = {shop = "amber", potions = "green", dinos = "blue", fusion = "purple", eggs = "cream", settings = "dark"}
Kit.DefaultPlace = "dinos" -- an unknown screen keeps blue, the colour the window header has today before a screen sets one
-- Every screen name the menu window opens (Bootstrap open(name)) and the place it belongs to.
-- PROVISIONAL (LEAD fill-ins, docs/228 names six places only): home = dinos, results / starter / batchSummary = eggs, exit and the Food page = settings.
Kit.ScreenPlace = {
    auras = "shop", auraConfirm = "shop", auraInfo = "shop", conditionConfirm = "shop", eggPurchase = "shop", crystalReveal = "shop",
    eggOdds = "shop", eggOutcomes = "shop", oddsSimple = "shop",
    potions = "potions", potionConfirm = "potions", potionReplace = "potions",
    collection = "dinos", detail = "dinos", home = "dinos", tutorial = "dinos",
    fusion = "fusion",
    eggs = "eggs", hatch = "eggs", results = "eggs", batchSummary = "eggs", starter = "eggs",
    settings = "settings", food = "settings", exit = "settings",
}
function Kit.placeOf(screen: string?): string
    return (if screen then Kit.ScreenPlace[screen] else nil) or Kit.DefaultPlace
end
-- Owner 2026-11-14 (C-58): the dino detail page keeps its rarity colour under the skin. Rarity tier 1..6 (Common .. Mythic) -> header picture,
-- the nearest kit colour to Theme.RarityColors. PROVISIONAL (LEAD): Common = cream (the kit has no grey header), Mythic = red.
Kit.RarityHeader = {"cream", "green", "blue", "purple", "amber", "red"}
function Kit.raritySlot(tier: number): string
    return "toybox_header_" .. (Kit.RarityHeader[tier] or Kit.RarityHeader[1])
end
function Kit.headerOf(place: string): string
    return Kit.PlaceHeader[place] or Kit.PlaceHeader[Kit.DefaultPlace]
end
-- The header picture of a screen of the menu window (nil or unknown = blue) ...
function Kit.headerSlot(screen: string?): string
    return "toybox_header_" .. Kit.headerOf(Kit.placeOf(screen))
end
-- ... and of a window that always belongs to one place (the Fusion Menu).
function Kit.placeSlot(place: string): string
    return "toybox_header_" .. Kit.headerOf(place)
end

-- Which gloss button a flat button colour becomes: the nearest of the seven (0..255 rgb). The anchors are the Theme colours the screens use.
Kit.ButtonAnchors = {
    green = {93, 237, 31}, grey = {128, 142, 158}, gold = {255, 210, 43}, blue = {46, 206, 255},
    red = {247, 57, 48}, purple = {194, 86, 255}, dark = {61, 58, 73},
}
function Kit.buttonKey(r: number, g: number, b: number): string
    -- a colourless button (white, grey, black, the card and panel colours) is grey when light and dark when dark, never a colour
    if math.max(r, g, b) - math.min(r, g, b) < 40 then return if (r + g + b) / 3 >= 100 then "grey" else "dark" end
    local best, bestDistance = "dark", math.huge
    for _, key in Kit.ButtonColours do -- fixed order: a tie always gives the same button
        local a = Kit.ButtonAnchors[key]
        local d = (a[1] - r) ^ 2 + (a[2] - g) ^ 2 + (a[3] - b) ^ 2
        if d < bestDistance then best, bestDistance = key, d end
    end
    return best
end
function Kit.buttonSlot(r: number, g: number, b: number): string
    return "toybox_button_" .. Kit.buttonKey(r, g, b)
end

-- Text: one outlined style. 3 px outline, 4 px from 28 px text up; never under 14 px.
function Kit.stroke(textSize: number): number
    local size = if textSize == textSize then textSize else Kit.MinText
    return if size >= Kit.StrokeBigFrom then Kit.StrokeBig else Kit.StrokeSmall
end
function Kit.textSize(size: number): number
    local wanted = if size == size then size else Kit.MinText
    return math.max(wanted, Kit.MinText)
end

-- The X: a square. absW / absH = the button's size on screen, scale = the window's UIScale. Returns the side in design px (before the
-- UIScale), so that the square is the short side of the button but never under 48 px on screen.
function Kit.closeSide(absW: number, absH: number, scale: number): number
    local s = if scale == scale and scale > 0.01 then scale else 1
    local short = math.min(absW, absH)
    if short ~= short then short = 0 end
    return math.max(short, Kit.MinClose) / s
end

-- BD-1189 (owner 2026-11-14): the X sits fully INSIDE the header strip, centred, with the same inset on the right, top and bottom (8 px, the 8 px
-- grid), square, at least 48 px on screen. headerH = the strip height in design px. Returns side, inset (design px; the inset only drops under 8 on
-- a strip so short that the 48 px X could not fit, then it is still equal on all three sides).
Kit.CloseInset = 8
function Kit.closeBox(headerH: number, scale: number): (number, number)
    local s = if scale == scale and scale > 0.01 then scale else 1
    local h = if headerH == headerH and headerH > 0 then headerH else 0
    local side = math.max(h - 2 * Kit.CloseInset, Kit.MinClose / s)
    return side, math.max((h - side) / 2, 0)
end

-- ---- BD-1189 (docs/232): layout numbers every Toybox screen shares (design px, multiples of 4). Screens place nothing by hand any more: they ask
-- ToyboxSkin's helpers (panel, row, actionButton, emptySlot) that read these. OWNER TARGET (clean like top Roblox games); numbers PROVISIONAL (LEAD).
Kit.Inset = 16 -- frame to content on every side (the menu body keeps its older 18 / 20 px until the window itself moves; recorded in docs/115)
Kit.Gutter = 12 -- between panels, cards, buttons
Kit.PanelPad = 12 -- inside a panel
Kit.PanelCorner, Kit.PreviewCorner, Kit.CardCorner, Kit.PanelStroke = 14, 10, 12, 3
Kit.ButtonH, Kit.ButtonSmallH = 48, 40
Kit.RowH = 24 -- one label / value row (16 px text)
Kit.Type = {title = 28, heading = 20, body = 16, small = 14} -- the type scale; 14 is the floor
Kit.Tone = { -- bright cream (owner pick A, 2026-11-14), 0..255 rgb
    panel = {255, 247, 227}, card = {255, 253, 246}, previewTop = {255, 233, 184}, previewBottom = {246, 213, 140},
    label = {122, 106, 78}, value = {58, 47, 30}, slot = {235, 224, 196},
    ready = {221, 243, 205}, busy = {255, 236, 190}, silhouette = {206, 190, 158}, -- BD-1195 / BD-1194: soft card tints (nest ready / growing, undiscovered dino)
}
Kit.CardStroke, Kit.ChipCorner = 2, 8
Kit.DashLength, Kit.DashGap, Kit.DashThickness = 10, 8, 3 -- an empty slot: dashes round a rounded card
-- Button heights for a window scaled by `scale`: the design size, but never under 44 px on screen (the touch rule, docs/72).
function Kit.buttonHeights(scale: number): (number, number)
    local s = if scale == scale and scale > 0.01 then scale else 1
    local touch = math.ceil(44 / s)
    return math.max(Kit.ButtonH, touch), math.max(Kit.ButtonSmallH, touch)
end
-- "Your Compies (3)": the heading of a copies list never repeats the window title (docs/232 rule "no repeats").
function Kit.plural(name: string): string
    if string.match(name, "[^aeiouAEIOU]y$") then return string.sub(name, 1, -2) .. "ies" end
    if string.match(name, "[sxz]$") or string.match(name, "[cs]h$") then return name .. "es" end
    return name .. "s"
end
function Kit.copiesHeading(name: string, count: number): string
    return "Your " .. Kit.plural(name) .. " (" .. count .. ")"
end
-- Equal cells: the width of one of `columns` cells that fill `width` with `gutter` between them.
function Kit.cellWidth(width: number, columns: number, gutter: number): number
    return math.floor((width - gutter * (columns - 1)) / math.max(columns, 1))
end
-- Empty slots that finish the last row of a grid (and give it at least `minRows` rows), so a grid never looks unfinished.
function Kit.emptySlots(count: number, columns: number, minRows: number): number
    local total = math.max(math.ceil(count / columns), minRows) * columns
    return total - count
end

-- The rects of the dino detail page (design px, inside the menu body: 824 x 402 on a desktop window, wider / shorter on a compact one):
-- a fixed 296 px left panel, a 12 px gutter, a right panel that takes the rest. `scale` = the window's UIScale (buttons never under 44 px on
-- screen), `filterRowH` = height of the chosen-filter chips row (0 = none), `dupRow` = whether the "3 of 6 for Gold!" bars are shown,
-- bodyW / bodyH = the body that is really on screen (default 824 x 402). One place for the numbers, so the page and
-- tools/verify_toybox_layout.py agree. Short body: the preview shrinks first (never under 120), then the rows box (never under 2 rows, it scrolls);
-- the button stays at the foot. Wide body: the grid gets 4 to 6 equal columns.
Kit.Detail = {leftW = 296, rightW = 516, height = 402, columns = 4, maxColumns = 6, minCell = 114, cardH = 160, rowCount = 6, minPreview = 120, backW = 96, sortW = 96, sortWFilter = 128}
function Kit.columnsFor(contentWidth: number): number
    local D = Kit.Detail
    return math.max(D.columns, math.min(D.maxColumns, math.floor((contentWidth + Kit.Gutter) / (D.minCell + Kit.Gutter))))
end
function Kit.detailLayout(scale: number, filterRowH: number, dupRow: boolean, sortActive: boolean?, bodyW: number?, bodyH: number?)
    local D = Kit.Detail
    local W, H = math.max(bodyW or 824, D.leftW + Kit.Gutter + 300), bodyH or D.height
    local big, small = Kit.buttonHeights(scale)
    local pad, gut = Kit.PanelPad, Kit.Gutter
    local rightW = W - D.leftW - gut
    local leftContent, rightContent = D.leftW - 2 * pad, rightW - 2 * pad
    local rowsH = math.max(2 * Kit.RowH, math.min(D.rowCount * Kit.RowH, H - 3 * pad - gut - D.minPreview - big))
    local previewH = math.max(D.minPreview, H - 3 * pad - gut - rowsH - big)
    local layout: any = {big = big, small = small, height = H, width = W}
    layout.leftPanel = {x = 0, y = 0, w = D.leftW, h = H}
    layout.preview = {x = pad, y = pad, w = leftContent, h = previewH}
    layout.rows = {x = pad, y = pad + previewH + gut, w = leftContent, h = rowsH}
    layout.equip = {x = pad, y = H - pad - big, w = leftContent, h = big}
    layout.rightPanel = {x = D.leftW + gut, y = 0, w = rightW, h = H}
    local sortW = if sortActive then D.sortWFilter else D.sortW
    local backX = pad + rightContent - D.backW
    layout.back = {x = backX, y = pad, w = D.backW, h = small}
    layout.sort = {x = backX - gut - sortW, y = pad, w = sortW, h = small}
    layout.heading = {x = pad, y = pad, w = rightContent - D.backW - sortW - 2 * gut, h = small}
    local top = pad + small + gut
    if filterRowH > 0 then
        layout.filters = {x = pad, y = top, w = rightContent, h = filterRowH}
        top += filterRowH + gut
    end
    local bottom = H - pad
    if dupRow then
        layout.dup = {x = pad, y = bottom - small, w = rightContent, h = small}
        bottom -= small + gut
    end
    layout.grid = {x = pad, y = top, w = rightContent + 8, h = math.max(bottom - top, 0)} -- 8 px wider: the scroll bar sits in the right padding
    layout.columns = Kit.columnsFor(rightContent)
    layout.cellW = Kit.cellWidth(rightContent, layout.columns, gut)
    layout.cellH = D.cardH
    return layout
end

-- BD-1195 (docs/232): the rects of the Eggs screen (design px inside the menu body: 824 x 402 desktop, wider / a little taller on a compact window).
-- Top panel = the nests (heading, "Nests 0/5" chip, `capacity` equal cards); bottom row = the stage panel (egg picture) on the left and the info
-- panel on the right (status line, up to two note lines, ONE 48 px button, the small AUTO toggle). `noteLines` = how many note lines show (0..2).
-- One place for the numbers, so the screen and tools/verify_toybox_layout.py agree.
Kit.Eggs = {headH = 28, chipW = 112, statusH = 28, noteH = 24, nestCardMax = 132, nestCardMin = 48, stageMaxW = 300, stageMinW = 200, infoMinW = 300, autoW = 150}
function Kit.eggsLayout(scale: number, bodyW: number?, bodyH: number?, noteLines: number?, capacity: number?)
    local E = Kit.Eggs
    local W, H = bodyW or 824, bodyH or 402
    local cap = capacity or 5
    local big, small = Kit.buttonHeights(scale)
    local pad, gut = Kit.PanelPad, Kit.Gutter
    local notes = math.clamp(noteLines or 0, 0, 2) * E.noteH
    local infoMin = pad + E.statusH + notes + gut + big + gut + small + pad
    local nestsH = math.max(pad + E.headH + gut + E.nestCardMin + pad, math.min(pad + E.headH + gut + E.nestCardMax + pad, H - gut - infoMin))
    local bottomH = H - gut - nestsH
    local layout: any = {big = big, small = small, width = W, height = H, capacity = cap}
    layout.nests = {x = 0, y = 0, w = W, h = nestsH}
    layout.nestHead = {x = pad, y = pad, w = W - 2 * pad - E.chipW - gut, h = E.headH}
    layout.nestChip = {x = W - pad - E.chipW, y = pad, w = E.chipW, h = E.headH}
    local cellW = Kit.cellWidth(W - 2 * pad, cap, gut)
    local cardY = pad + E.headH + gut
    layout.cellW, layout.cellH = cellW, nestsH - cardY - pad
    layout.nestCards = {}
    for i = 1, cap do table.insert(layout.nestCards, {x = pad + (i - 1) * (cellW + gut), y = cardY, w = cellW, h = layout.cellH}) end
    local by = nestsH + gut
    local stageW = math.clamp(math.floor(W * 0.38), E.stageMinW, E.stageMaxW)
    layout.stagePanel = {x = 0, y = by, w = stageW + 2 * pad, h = bottomH}
    layout.stage = {x = pad, y = pad, w = stageW, h = bottomH - 2 * pad} -- inside the stage panel
    local infoX = stageW + 2 * pad + gut
    local infoW = W - infoX
    layout.infoPanel = {x = infoX, y = by, w = infoW, h = bottomH}
    layout.status = {x = pad, y = pad, w = infoW - 2 * pad, h = E.statusH}
    layout.notes = {x = pad, y = pad + E.statusH, w = infoW - 2 * pad, h = notes}
    layout.action = {x = pad, y = bottomH - pad - small - gut - big, w = infoW - 2 * pad, h = big}
    layout.auto = {x = pad, y = bottomH - pad - small, w = E.autoW, h = small}
    layout.autoLine = {x = pad + E.autoW + gut, y = bottomH - pad - small, w = infoW - 2 * pad - E.autoW - gut, h = small}
    return layout
end

-- BD-1194 (docs/232): the rects of the Dino Index list. The bottom bar (progress meter, page arrows, FUSION) is ALWAYS inside the body, one
-- button high at its foot; the card grid above it scrolls and fills the body width in equal columns (the 8 px scroll-bar strip stays on the right).
Kit.Index = {minCard = 190, maxColumns = 6, minColumns = 3, cardH = 176, fusionW = 140, arrowW = 48, pageW = 64, minMeter = 120, scrollBar = 8}
function Kit.indexLayout(scale: number, bodyW: number?, bodyH: number?, paged: boolean?)
    local I = Kit.Index
    local W, H = bodyW or 824, bodyH or 402
    local big = Kit.buttonHeights(scale)
    local gut = Kit.Gutter
    local layout: any = {big = big, width = W, height = H}
    layout.bar = {x = 0, y = H - big, w = W, h = big}
    layout.grid = {x = 0, y = 0, w = W, h = math.max(H - big - gut, 0)}
    layout.fusion = {x = W - I.fusionW, y = H - big, w = I.fusionW, h = big}
    local right = layout.fusion.x - gut
    if paged then
        layout.next = {x = right - I.arrowW, y = H - big, w = I.arrowW, h = big}
        layout.page = {x = layout.next.x - gut - I.pageW, y = H - big, w = I.pageW, h = big}
        layout.prev = {x = layout.page.x - gut - I.arrowW, y = H - big, w = I.arrowW, h = big}
        right = layout.prev.x - gut
    end
    layout.meter = {x = 0, y = H - big, w = right, h = big}
    local content = W - I.scrollBar
    layout.columns = math.clamp(math.floor((content + gut) / (I.minCard + gut)), I.minColumns, I.maxColumns)
    layout.cellW = Kit.cellWidth(content, layout.columns, gut)
    layout.cellH = I.cardH
    return layout
end

-- docs/232: the rects of the Fusion Menu body. Three cream panels (dino list | slots | result) 12 px apart fill the body width; when the
-- three tier chips do not fit above the list (`wide`) they take one row across the top and the panels start 12 px under it. Everything inside a
-- panel sits 12 px from its edge; the bottom of the centre panel holds the two small grey buttons, the bottom of the result panel the ONE
-- primary FUSE button. The dino list, the slot grid and the odds list scroll or share what is left, never overflow the body.
Kit.Fusion = {headH = 28, noteH = 20, guaranteeH = 24, filterW = 96, leftFrac = 0.38, centreFrac = 0.28, fillFrac = 0.6, minResult = 48}
function Kit.fusionLayout(scale: number, bodyW: number?, bodyH: number?, wide: boolean?)
    local F = Kit.Fusion
    local W, H = bodyW or 1160, bodyH or 390
    local big, small = Kit.buttonHeights(scale)
    local pad, gut = Kit.PanelPad, Kit.Gutter
    local top = if wide then big + gut else 0
    local PH = H - top
    local avail = W - 2 * gut
    local leftW = math.floor(avail * F.leftFrac)
    local centreW = math.floor(avail * F.centreFrac)
    local rightW = avail - leftW - centreW
    local layout: any = {big = big, small = small, width = W, height = H, wide = wide == true}
    layout.tabRow = if wide then {x = 0, y = 0, w = W, h = big} else nil
    layout.left = {x = 0, y = top, w = leftW, h = PH}
    layout.centre = {x = leftW + gut, y = top, w = centreW, h = PH}
    layout.right = {x = leftW + centreW + 2 * gut, y = top, w = rightW, h = PH}
    -- inside the dino list panel (coordinates of the panel's inner box, 12 px in)
    local li = {w = leftW - 2 * pad, h = PH - 2 * pad}
    layout.leftIn = li
    local ly = 0
    if not wide then layout.tabs = {x = 0, y = 0, w = li.w, h = big} ly = big + gut end
    layout.goal = {x = 0, y = ly, w = li.w - F.filterW - gut, h = small}
    layout.filter = {x = li.w - F.filterW, y = ly, w = F.filterW, h = small}
    layout.grid = {x = 0, y = ly + small + gut, w = li.w, h = math.max(li.h - ly - small - gut, 0)}
    -- inside the slots panel
    local ci = {w = centreW - 2 * pad, h = PH - 2 * pad}
    layout.centreIn = ci
    layout.head = {x = 0, y = 0, w = ci.w, h = F.headH}
    local fillW = math.floor((ci.w - gut) * F.fillFrac)
    layout.fill = {x = 0, y = ci.h - small, w = fillW, h = small}
    layout.clear = {x = fillW + gut, y = ci.h - small, w = ci.w - fillW - gut, h = small}
    layout.slots = {x = 0, y = F.headH + gut, w = ci.w, h = math.max(ci.h - F.headH - gut - gut - small, 0)}
    -- inside the result panel
    local ri = {w = rightW - 2 * pad, h = PH - 2 * pad}
    layout.rightIn = ri
    layout.fuse = {x = 0, y = ri.h - big, w = ri.w, h = big}
    layout.note = {x = 0, y = ri.h - big - gut - F.noteH, w = ri.w, h = F.noteH}
    local free = math.max(layout.note.y - gut, 0)
    local resultH = math.max(F.minResult, math.floor((free - F.guaranteeH - 2 * gut) * 0.5))
    layout.result = {x = 0, y = 0, w = ri.w, h = math.min(resultH, free)}
    layout.guarantee = {x = 0, y = layout.result.h + gut, w = ri.w, h = F.guaranteeH}
    local oddsY = layout.guarantee.y + F.guaranteeH + gut
    layout.odds = {x = 0, y = oddsY, w = ri.w, h = math.max(free - oddsY, 0)}
    return layout
end

-- The slice scale of a picture drawn `width` x `height` px. A header never stretches up or down (scale = height / 128). The others use
-- half size, less when the box is so small that the caps would not fit.
function Kit.sliceScale(slot: string, width: number, height: number): number
    local asset = assets[slot]
    if asset == nil or asset.slice == nil then return 1 end
    local slice = asset.slice
    if asset.fit == "height" then return math.max(height, 1) / asset.h end
    local capsW, capsH = asset.w - (slice[3] - slice[1]), asset.h - (slice[4] - slice[2])
    return math.max(0.05, math.min(Kit.SliceScale, width / capsW, height / capsH))
end

return Kit
