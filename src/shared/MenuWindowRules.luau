--!strict
-- BD-1266 / BD-1267 / BD-1270 (docs/244 s2.12 to s2.14, owner 2026-11-17 "Yes, build it"): the ONE standard menu window as plain numbers.
-- Every size is a share of the screen: "h" = of the screen height, "w" = of the screen width (docs/244 s2.14: the phone canvas is about 480
-- design px tall, so 1 % h is about 4.8 px). No engine call, no clock, no RNG: tools/verify_menu_window.py runs this file in the pinned Luau
-- runtime. src/client/MenuWindow.luau builds what this returns; the shop pages (src/client/ShopWindowPages.luau) fill it.
-- Paid lines stay off (docs/43): every price here is crystals, there is no Robux word, no gift button and no crossed-out price.
local R = {}

-- ---- colours (docs/244 s2.14 point 2; rarity colours docs/114 s5). 0..255 rgb.
R.Colours = {
    green = {93, 237, 31}, purple = {194, 86, 255}, yellow = {255, 210, 43}, cyan = {46, 206, 255}, grey = {128, 142, 158},
}
-- The striped title bar is the Toybox header picture (Blender art, docs/77 "toybox_header_*") nearest to the window colour. Code draws no stripe.
R.HeaderArt = {green = "green", purple = "purple", yellow = "amber", cyan = "blue", grey = "dark"}
R.Rarities = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}
R.RarityColours = {
    Common = {128, 142, 158}, Uncommon = {93, 237, 31}, Rare = {46, 206, 255}, Epic = {194, 86, 255}, Legendary = {255, 210, 43}, Mythic = {247, 57, 48},
}
R.Green = {124, 255, 74} -- the highlighted number of a card line ("Speed +20%"): green, black outline
R.Body = {28, 26, 38} -- the dark patterned body (the stud picture on top, tinted dark)
R.Strip = {14, 16, 24} -- the dark effect strip of an item card

function R.colour(name: string?): {number}
    return R.Colours[name or ""] or R.Colours.grey
end
function R.headerSlot(name: string?): string
    return "toybox_header_" .. (R.HeaderArt[name or ""] or R.HeaderArt.grey)
end
-- Rarity word -> card picture slot (toybox_card_<rarity>, Blender art) and colour. Unknown = Common.
function R.rarity(word: any): string
    if type(word) == "string" then
        for _, name in R.Rarities do
            if string.lower(name) == string.lower(word) then return name end
        end
    end
    return "Common"
end
function R.cardSlot(word: any): string
    return "toybox_card_" .. string.lower(R.rarity(word))
end
function R.rarityColour(word: any): {number}
    return R.RarityColours[R.rarity(word)]
end

-- ---- window kinds (docs/244 s2.14 table): width = share of the screen width, height = share of the screen height.
-- minW / maxW in px of the gui (design px on the phone): only the long window has them in the spec; the item window keeps a floor so 3 cards fit.
R.Kinds = {
    long = {w = 0.58, h = 0.67, minW = 540, maxW = 1100}, -- Crystal Shop: sections and offer cards
    item = {w = 0.43, h = 0.56, minW = 420, maxW = 900}, -- Potion Shop, auras, trails, eggs: item cards
    fusion = {w = 0.35, h = 0.62, minW = 380, maxW = 800},
    index = {w = 0.49, h = 0.60, minW = 480, maxW = 1000},
    settings = {w = 0.34, h = 0.68, minW = 380, maxW = 800},
}
-- The screens built on the window now (the Index, Fusion, My dinos and Settings follow in a later session on the same API).
R.Screens = {
    crystalShop = {title = "Crystal Shop", colour = "green", kind = "long"},
    potionShop = {title = "Potion Shop", colour = "purple", kind = "item"},
}

-- ---- sizes, share of the screen height (docs/244 s2.12 / s2.14)
R.H = {
    below = 0.03, -- the window is centred 3 % h below the middle
    titleBar = 0.10, title = 0.045, close = 0.08, pad = 0.025,
    section = 0.038, gap = 0.035,
    offerCard = 0.28, offerIcon = 0.15, offerTitle = 0.035, offerLine = 0.031, priceButton = 0.066,
    itemCard = 0.44, itemName = 0.035, itemRarity = 0.028, itemEffect = 0.031, itemStrip = 0.06, itemButton = 0.05,
    tabIcon = 0.095, tabWord = 0.03, tabGap = 0.015, tabLeft = 0.02,
    smallest = 0.028,
}
R.Blur = 12 -- BlurEffect.Size while a window is open
R.MinText = 14 -- docs/72 floor
R.MinTarget = 44 -- docs/72 touch floor
R.CapRatio = 0.72 -- FredokaOne: cap height is about 0.72 of TextSize (docs/244 s2.14 table: 4.5 % h of 480 = 21.6 cap = TextSize 30)
R.WordStroke, R.CounterStroke = 2.5, 3

local function sane(n: number?, fallback: number): number
    if type(n) ~= "number" or n ~= n or n <= 0 then return fallback end
    return n
end

-- The TextSize that gives a cap height of `share` of the screen height, never under the 14 px floor.
function R.textSize(screenH: number, share: number): number
    return math.max(R.MinText, math.floor(sane(screenH, 480) * share / R.CapRatio + 0.5))
end
-- A share of the screen height in px (rounded).
function R.px(screenH: number, share: number): number
    return math.floor(sane(screenH, 480) * share + 0.5)
end

-- The window rect in gui px: {w, h, x, y} with x / y the top-left corner. Centred, 3 % h below the middle.
function R.rect(screenW: number, screenH: number, kind: string?): {w: number, h: number, x: number, y: number}
    local W, H = sane(screenW, 960), sane(screenH, 480)
    local k = R.Kinds[kind or ""] or R.Kinds.item
    local w = math.clamp(math.floor(W * k.w + 0.5), math.min(k.minW, W - 8), k.maxW)
    local h = math.floor(H * k.h + 0.5)
    local x = math.floor((W - w) / 2 + 0.5)
    local y = math.floor((H - h) / 2 + H * R.H.below + 0.5)
    return {w = w, h = h, x = x, y = y}
end

-- The side tab column, OUTSIDE the window on the right (docs/244 s2.14 point 3). n = how many tabs. Returns the column rect and the pitch.
-- A tab is the icon plus its word under it; the whole tab is the tap target (never under 44 px).
function R.tabs(screenW: number, screenH: number, kind: string?, n: number)
    local H = sane(screenH, 480)
    local win = R.rect(screenW, H, kind)
    local icon, word, gap = R.px(H, R.H.tabIcon), R.px(H, R.H.tabWord), R.px(H, R.H.tabGap)
    local tabH = math.max(R.MinTarget, icon + math.floor(word * 1.25 + 0.5))
    local tabW = math.max(R.MinTarget, icon + 2 * word)
    local count = math.max(n, 0)
    return {
        x = win.x + win.w + R.px(H, R.H.tabLeft), y = win.y, w = tabW, h = count * tabH + math.max(count - 1, 0) * gap,
        tabW = tabW, tabH = tabH, icon = icon, word = word, pitch = tabH + gap,
    }
end

-- Columns of a card grid: offer cards 2 per row on a phone (a short screen), 3 on a desktop; item cards 3 per row.
R.PhoneMaxH = 600 -- a gui shorter than this is a phone (PhoneScale.isCompact uses the same idea)
function R.columns(card: string, screenH: number): number
    if card == "offer" then return if sane(screenH, 480) < R.PhoneMaxH then 2 else 3 end
    return 3
end
-- Equal cells across `width` px with `gap` px between them.
function R.cell(width: number, columns: number, gap: number): number
    local c = math.max(columns, 1)
    return math.max(math.floor((sane(width, 1) - gap * (c - 1)) / c), 1)
end

-- "-- AURAS --": the section header word, upper case with dashes on both sides.
function R.section(name: string): string
    return "-- " .. string.upper(name) .. " --"
end

-- ONE card line with the key word coloured: "Speed +20%" -> rich text with "+20%" green. The first number-ish word ("+20%", "x2", "5 min")
-- is the key; a line without one stays plain. Text is escaped for RichText.
local function escape(text: string): string
    return (string.gsub(string.gsub(string.gsub(text, "&", "&amp;"), "<", "&lt;"), ">", "&gt;"))
end
function R.hex(rgb: {number}): string
    return string.format("#%02X%02X%02X", rgb[1], rgb[2], rgb[3])
end
function R.highlight(line: string): string
    local safe = escape(line)
    local s, e = string.find(safe, "[x%+%-]?%d[%d%.,]*%%?")
    if not s then return safe end
    return string.sub(safe, 1, s - 1) .. '<font color="' .. R.hex(R.Green) .. '">' .. string.sub(safe, s, e) .. "</font>" .. string.sub(safe, e + 1)
end

-- A price button word: just the number with thousands commas (the crystal icon sits beside it). Never a Robux sign.
function R.price(amount: any): string
    local n = if type(amount) == "number" and amount == amount then math.max(math.floor(amount), 0) else 0
    local text = tostring(n)
    while true do
        local changed
        text, changed = string.gsub(text, "^(%d+)(%d%d%d)", "%1,%2")
        if changed == 0 then break end
    end
    return text
end
-- The one button of a card: what it says and whether it is green. state: "buy", "short" (not enough crystals), "owned", "equipped",
-- "use", "locked", "soldout", "chances", "max", "soon".
function R.button(state: string, price: number?, level: number?): {text: string, green: boolean, active: boolean, icon: boolean}
    if state == "buy" then return {text = R.price(price), green = true, active = true, icon = true} end
    if state == "short" then return {text = R.price(price), green = false, active = true, icon = true} end
    if state == "owned" then return {text = "Equip", green = true, active = true, icon = false} end
    if state == "equipped" then return {text = "Equipped", green = false, active = true, icon = false} end
    if state == "use" then return {text = "Use", green = true, active = true, icon = false} end
    if state == "locked" then return {text = "Level " .. tostring(level or 1), green = false, active = true, icon = false} end
    if state == "soldout" then return {text = "Sold out", green = false, active = false, icon = false} end
    if state == "chances" then return {text = "Chances", green = false, active = true, icon = false} end
    if state == "max" then return {text = "Top level", green = false, active = false, icon = false} end
    return {text = "Soon", green = false, active = false, icon = false}
end

-- ---- side tabs (BD-1267). Icons are existing art slots (AssetSlots.Images, docs/77): never code-drawn.
R.TabArt = {
    featured = "notify_star", auras = "shop_tab_auras", trails = "shop_tab_trails", eggs = "egg_green_spotted", conditions = "shop_tab_conditions",
    potions = "potion_icon_speed_common", owned = "potion_icon_growth_common",
}
R.TabWords = {featured = "Featured", auras = "Auras", trails = "Trails", eggs = "Eggs", conditions = "Luck", potions = "Potions", owned = "Yours"}
function R.tabWord(tab: string): string
    return R.TabWords[tab] or (string.upper(string.sub(tab, 1, 1)) .. string.sub(tab, 2))
end
-- The Crystal Shop tabs: Featured first (BD-1270, its own flag), then the shop tabs the player's level allows (FtueP1.shopTabs).
-- The Crystals tab (Robux packs) never shows on this window: paid lines are off (docs/43).
function R.shopTabs(levelTabs: {string}, featured: boolean): {string}
    local out = {}
    if featured then table.insert(out, "featured") end
    for _, tab in levelTabs do
        if tab ~= "crystals" and tab ~= "featured" then table.insert(out, tab) end
    end
    return out
end
function R.firstTab(tabs: {string}, wanted: string?): string
    for _, tab in tabs do if tab == wanted then return tab end end
    return tabs[1] or "auras"
end

-- ---- BD-1270: the Featured page. One big card for this week's thing and two more under "-- NEW --". Weekly, the same for everyone:
-- picked from the server clock (workspace:GetServerTimeNow on the client, os.time on the server), from items that are sold for crystals
-- today (price > 0). No Robux, no crossed-out "worth" price, no countdown under a day shown in seconds.
R.Week = 7 * 24 * 3600
R.WeekStart = 345600 -- 1970-01-05 00:00 UTC, a Monday: weeks turn over on Monday 00:00 UTC
function R.week(now: number): number
    return math.floor((sane(now, 0) - R.WeekStart) / R.Week)
end
-- pool = {{kind, id, price}} in a fixed order (auras, then trails, config order). Returns up to 3 entries: [1] the big card, [2..3] NEW.
function R.featured(pool: {any}, now: number): {any}
    local priced = {}
    for _, item in pool do
        if type(item) == "table" and type(item.price) == "number" and item.price > 0 then table.insert(priced, item) end
    end
    local out = {}
    local n = #priced
    if n == 0 then return out end
    local start = R.week(now) % n
    for i = 0, math.min(n, 3) - 1 do
        table.insert(out, priced[(start + i) % n + 1])
    end
    return out
end
-- "3 days left" / "1 day left" / "Last day": kid words, whole days only (docs/72: never "2:59" or "4m 26s").
function R.daysLeft(now: number): string
    local t = sane(now, 0)
    local ends = R.WeekStart + (R.week(t) + 1) * R.Week
    local days = math.floor((ends - t) / 86400)
    if days >= 2 then return days .. " days left" end
    if days == 1 then return "1 day left" end
    return "Last day"
end

-- ---- card parts (px inside a card), so the client places nothing by hand and the verifier can measure them.
-- Offer card: icon on the left third, title and ONE line on the right, the green price button under them.
function R.offerParts(cardW: number, screenH: number)
    local H = sane(screenH, 480)
    local cardH = R.px(H, R.H.offerCard)
    local pad = R.px(H, R.H.pad)
    local icon = math.min(R.px(H, R.H.offerIcon), math.floor(cardW / 3))
    local textX = pad + icon + pad
    local textW = math.max(cardW - textX - pad, 1)
    local titleH = math.max(R.textSize(H, R.H.offerTitle) + 4, 1)
    local lineH = math.max(R.textSize(H, R.H.offerLine) + 4, 1)
    local buttonH = math.max(R.px(H, R.H.priceButton), R.MinTarget)
    return {
        h = cardH,
        icon = {x = pad, y = math.floor((cardH - icon) / 2), w = icon, h = icon},
        title = {x = textX, y = pad, w = textW, h = titleH},
        line = {x = textX, y = pad + titleH, w = textW, h = lineH},
        button = {x = textX, y = cardH - pad - buttonH, w = textW, h = buttonH},
    }
end
-- Item card: name and rarity word on top, the big render, the dark effect strip, ONE full-width button at the foot.
-- noButton = a card that only shows (the egg luck chances): the strip sits at the foot.
function R.itemParts(cardW: number, screenH: number, cardH: number?, noButton: boolean?)
    local H = sane(screenH, 480)
    local h = cardH or R.px(H, R.H.itemCard)
    local pad = math.max(math.floor(R.px(H, R.H.pad) * 0.6), 4)
    local nameH = R.textSize(H, R.H.itemName) + 2
    local rarityH = R.textSize(H, R.H.itemRarity) + 2
    local buttonH = if noButton then 0 else math.max(R.px(H, R.H.itemButton), R.MinTarget)
    local stripH = math.max(R.px(H, R.H.itemStrip), R.textSize(H, R.H.itemEffect) + 6)
    local innerW = math.max(cardW - 2 * pad, 1)
    local buttonY = h - pad - buttonH
    local stripY = if noButton then h - pad - stripH else buttonY - pad - stripH
    local renderY = pad + nameH + rarityH
    return {
        h = h,
        name = {x = pad, y = pad, w = innerW, h = nameH},
        rarity = {x = pad, y = pad + nameH, w = innerW, h = rarityH},
        render = {x = pad, y = renderY, w = innerW, h = math.max(stripY - renderY, 0)},
        strip = {x = pad, y = stripY, w = innerW, h = stripH},
        button = {x = pad, y = buttonY, w = innerW, h = buttonH},
    }
end

return R
