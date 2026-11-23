--!strict
-- BD-1296 (docs/246 slice 2): with Config.MenusSaeFrameEnabled the POTION SHOP is the shop menu kit window (client/KitWindow, slice 1's
-- Crystal Shop window). BD-1298: built element by element from the spec of the owner's PROPOSED PICTURE (docs/menu-specs/potion-shop/
-- spec.json; Shared/SaeMenuRules.PotionSpec and potionLayout): the green header "Potions" with the red X, the yellow restock words "New
-- in 2 min" INSIDE the header and a small grey page arrow left of the X; THREE tall kit rarity cards with the picture's words only (the
-- short name "Swift", the rarity word, the "x3" count top right, the bound potion picture, a kid line "Grow faster!" on the dark strip,
-- the green price button with the orange crystal; "Sold out" grey). Nothing under the cards. The arrow pages the shop, then "My Potions"
-- (the potions the player owns, "x2", "Lasts 5 min" on the strip, a green "Drink!" button: the only place to drink one), then the shop
-- again. The shop tabs sit outside the window on the right in the picture's order (Potions selected). Every element carries the
-- attribute SpecId (the spec's name: "card2.price", "rail.eggs") for tools/studio/dump_menu_geometry.luau + tools/menu_spec_check.py.
-- Client presentation only: no remote, no price and no stock rule here; a buy tap opens the purchase confirm (ShopScreens), a drink tap
-- goes through ShopScreens' use path, the server decides both.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Kit2 = require(Shared.ShopKit2)
local ShopArt = require(Shared.ShopArt)
local Menu = require(Shared.SaeMenuRules)
local FrameRules = require(Shared.SaeFrameRules)
local ProgressionConfig = require(Shared.ProgressionConfig)
local ProgressionRules = require(Shared.ProgressionRules)
local TimerWords = require(Shared.TimerWords)
local Art = require(script.Parent.KitArt)
local KitWindow = require(script.Parent.KitWindow)
local KitButton = require(script.Parent.KitButton)
local KitRail = require(script.Parent.KitRail)
local Landing = require(script.Parent.ShopSaeLanding)

local M = {}

local state = {window = -1, page = 1}

local function icon(item: any): string?
    local slot = Kit.potionIconSlot(Slots.Images :: any, item.id, item.kind)
    return if slot then (Slots.Images :: any)[slot] else nil
end

-- The kit words of a line, main and drop copy (KitArt.words draws both): change both together.
local function setWords(label: TextLabel?, text: string)
    if not label or not label.Parent then return end
    label.Text = text
    local drop = label.Parent:FindFirstChild(label.Name .. "Drop")
    if drop and drop:IsA("TextLabel") then drop.Text = text end
end

local function restockWords(window: number): string
    return TimerWords.restockIn(math.max(0, math.ceil(ProgressionRules.shopEndsAt(window) - workspace:GetServerTimeNow())))
end

-- The rail icons: the picture's purple swirl (Trails) and purple ring (Auras) on this screen, the shop tab icons otherwise (Featured keeps
-- the crystals: there is no red %-tag art).
local RailArt = {trails = "potion_rail_trails", auras = "potion_rail_auras"}
local RailCrop = {trails = {38, 37, 435}, auras = {37, 38, 435}} -- x, y, side in picture px of the 512 px art (its drawn part)
local function railIcon(tab: string): string?
    local slot = RailArt[tab]
    return (if slot then ShopArt.validId((Slots.Images :: any)[slot]) else nil) or Landing.tabIcon(tab)
end

-- The picture's outline thickness on a kit word (KitArt.words draws a main and a drop copy, both outlined).
local function outline(label: TextLabel?, px: number): TextLabel?
    if not label or not label.Parent then return label end
    for _, l in {label, label.Parent:FindFirstChild(label.Name .. "Drop")} do
        local s = if l then l:FindFirstChildOfClass("UIStroke") else nil
        if s then s.Thickness = px end
    end
    return label
end

local function mark(o: Instance?, id: string)
    if o then o:SetAttribute("SpecId", id) end
end

-- One potion card at r (window px) with the parts of lay.parts (card px): the kit 2 rarity card, the name, the rarity word, the count,
-- the picture, the strip, the button. c = {key, rarity, name, picture, effect, count?, price?, word?, grey?, gem?, onPick}.
local function card(window: Frame, i: number, r: any, P: any, O: any, c: any)
    local id = "card" .. i
    local holder = Art.box(window, "KitCard_" .. c.key, r.x, r.y, r.w, r.h, 34)
    mark(holder, id)
    local slot = Kit2.cardSlot(c.rarity)
    local studK = r.w / Kit2.Studded[slot].w
    Art.studded(holder, "Face", slot, 0, 0, r.w, r.h, 34, studK * 0.2, studK) -- the picture's thin dark card edge (about a third of the kit outline)
    Art.tap(holder, "Tap", 0, 0, r.w, r.h, 35, c.onPick)
    local n, rw, b, a, s, p = P.name, P.rarity, P.badge, P.art, P.strip, P.price
    mark(outline(Art.words(holder, "Name", c.name, n.x, n.y, n.w, n.h, FrameRules.fitSize(c.name, n.w, n.size), 38), O.name), id .. ".name")
    mark(outline(Art.words(holder, "Rarity", c.rarity, rw.x, rw.y, rw.w, rw.h, FrameRules.fitSize(c.rarity, rw.w + 20, rw.size), 38), O.rarity), id .. ".rarity")
    if c.count then
        local count = Art.words(holder, "Badge", c.count, b.x, b.y, b.w, b.h, b.size, 38)
        outline(count, O.badge)
        count.TextXAlignment = Enum.TextXAlignment.Right
        mark(count, id .. ".badge")
    end
    if c.picture then
        -- the picture's box; the potion art has a clear margin round the bottle, so it is drawn a little bigger than the box (centred) to
        -- fill the box height like the picture
        local box = Art.box(holder, "Art", a.x, a.y, a.w, a.h, 36)
        mark(box, id .. ".art")
        local side = math.floor(a.h / 0.845 + 0.5)
        Art.picture(box, "Picture", c.picture, math.floor((a.w - side) / 2), math.floor((a.h - side) / 2), side, side, 36)
    end
    -- the dark kit strip with the picture's thin, nearly square edge (the kit outline at half size), the kid words on it
    local strip = Art.box(holder, "Strip", s.x, s.y, s.w, s.h, 37)
    local k = s.h / Kit2.Studded[Kit2.StripSlot].h
    Art.studded(strip, "Face", Kit2.StripSlot, 0, 0, s.w, s.h, 37, k * 0.5, k)
    Art.words(strip, "Line", c.effect, 0, -math.floor(s.h * 0.05), s.w, s.h, FrameRules.fitSize(c.effect, s.w - 14, s.size), 38)
    mark(strip, id .. ".strip")
    mark(KitButton.draw(holder, "Button", p.x, p.y, p.w, p.h, 37, {price = c.price, word = c.word, grey = c.grey, gem = c.gem,
        textSize = p.size, iconSize = math.floor(p.h * 0.72), onPress = c.onPick}), id .. ".price")
end

-- body: the Bootstrap panel body. d = {p (progression), window (shop window number), onBuy(item), onUse(item), onTab(tab), close(),
-- rerender(), restocked()}. Returns false when the kit window cannot open (the caller then draws the old page).
function M.build(body: GuiObject, d: any): boolean
    if state.window ~= d.window then state.window, state.page = d.window, 1 end
    local p = d.p
    local offers = ProgressionRules.shopOffers(d.window)
    local owned = {}
    for _, item in ProgressionConfig.Potions do
        local n = (p.potions or {})[item.id] or 0
        if n > 0 then table.insert(owned, {item = item, n = n}) end
    end
    -- the pages: the shop pages first, then the player's own potions (at least one page, so drinking is always one arrow away)
    local _, _, shopPages = Menu.page(#offers, 1, Menu.Potion.perPage)
    local _, _, ownPages = Menu.page(#owned, 1, Menu.Potion.perPage)
    local pages = shopPages + ownPages
    state.page = math.clamp(state.page, 1, pages)
    local mine = state.page > shopPages
    local gem = ShopArt.validId(require(Shared.UIIconAssets).amber)
    local cards = {}
    if not mine then
        local first, last = Menu.page(#offers, state.page, Menu.Potion.perPage)
        for i = first, last do
            local item = ProgressionRules.item(ProgressionConfig.Potions, offers[i].id)
            if item then
                local left = ProgressionRules.shopRemaining(p, d.window, item.id)
                local function buy() if left > 0 then d.onBuy(item) end end
                table.insert(cards, {
                    key = item.id, rarity = item.rarity, name = Menu.shortName(item.name), picture = icon(item),
                    effect = Menu.kindWord(item.kind, item.rarity), count = if left > 0 then Menu.count(left) else nil,
                    price = if left > 0 then item.price else nil, word = if left > 0 then nil else Menu.SoldOut, grey = left <= 0, gem = gem, onPick = buy,
                })
            end
        end
    else
        local first, last = Menu.page(#owned, state.page - shopPages, Menu.Potion.perPage)
        for i = first, math.min(last, #owned) do
            local item, n = owned[i].item, owned[i].n
            table.insert(cards, {
                key = item.id, rarity = item.rarity, name = Menu.shortName(item.name), picture = icon(item),
                effect = Menu.lasts(item.duration), count = Menu.count(n), word = Menu.DrinkWord, grey = false, onPick = function() d.onUse(item) end,
            })
        end
    end
    local live: {restock: TextLabel?} = {restock = nil}
    local spec: any
    spec = {
        title = if mine then Menu.YoursTitle else Menu.PotionTitle, colour = Menu.PotionColour, cards = {},
        layout = function(w: number, h: number, _: number, inset: number?) return Menu.potionLayout(w, h, inset) end,
        onClose = function() if d.close then d.close() end end,
        content = function(window: Frame, lay: any, _: Frame)
            -- the kit window's own parts, named as the spec names them; the title in the picture's box
            mark(window, "window")
            local header = window:FindFirstChild("KitHeader")
            mark(header, "header")
            if header then
                mark(header:FindFirstChild("CloseArt"), "close")
                local t, hi = lay.title, lay.headerInset
                local main, drop = header:FindFirstChild("Title"), header:FindFirstChild("TitleDrop")
                if main and main:IsA("TextLabel") then
                    local dy = if drop and drop:IsA("TextLabel") then drop.Position.Y.Offset - main.Position.Y.Offset else 0
                    main.Position, main.Size = UDim2.fromOffset(t.x - hi, t.y - hi), UDim2.fromOffset(t.w, t.h)
                    if drop and drop:IsA("TextLabel") then drop.Position, drop.Size = UDim2.fromOffset(t.x - hi, t.y - hi + dy), UDim2.fromOffset(t.w, t.h) end
                    mark(outline(main, lay.outline.title), "title")
                end
            end
            -- in the header: the yellow restock words, the page arrow left of the X
            local t = if mine then lay.timerMine else lay.timer
            local c = Menu.TimerColour
            live.restock = Art.words(window, "Restock", restockWords(d.window), t.x, t.y, t.w, t.h, t.size, 36, Color3.fromRGB(c[1], c[2], c[3]))
            mark(outline(live.restock, lay.outline.timer), "timer")
            local g = if mine then lay.pageMine else lay.page
            KitButton.draw(window, "PageButton", g.x, g.y, g.w, g.h, 36, {word = Menu.PageWord, grey = true, textSize = g.text, onPress = function()
                state.page = if state.page < pages then state.page + 1 else 1
                d.rerender()
            end})
            for i, data in cards do
                local r = lay.cards[i]
                if r then card(window, i, r, lay.parts, lay.outline, data) end
            end
            if mine and #cards == 0 then
                local r1, r3 = lay.cards[1], lay.cards[3]
                Art.words(window, "NoneWord", Menu.NoneWord, r1.x, r1.y, r3.x + r3.w - r1.x, r1.h, lay.parts.name.size, 38)
            end
            -- the rail outside the window, one slot per tab (the spec's rail.<tab> box: the icon with its word under it)
            for _, tab in Menu.PotionRail do
                local s = lay.rail[tab]
                local slot = Art.box(window, "KitTabSlot_" .. tab, s.x, s.y, s.w, s.h, 31)
                mark(slot, "rail." .. tab)
                KitRail.draw(slot, {slots = {{x = 0, y = 0, w = s.w, h = s.h}}, icon = s.icon, labelSize = s.label}, {
                    tabs = {tab}, words = Menu.PotionRailWords, selected = "potions", icon = railIcon,
                    onTab = function(picked: string) if picked ~= "potions" then d.onTab(picked) end end,
                })
                -- the purple swirl / ring art has a wide clear margin: show its square middle so it reads as big as the other icons
                local crop = RailCrop[tab]
                local art = slot:FindFirstChild("KitTabIcon_" .. tab)
                if crop and art and art:IsA("ImageLabel") and RailArt[tab] and art.Image == ShopArt.validId((Slots.Images :: any)[RailArt[tab]]) then
                    art.ImageRectOffset, art.ImageRectSize = Vector2.new(crop[1], crop[2]), Vector2.new(crop[3], crop[3])
                end
            end
        end,
    }
    if not KitWindow.open(body, spec) then return false end
    -- the restock words count down; a new shop window redraws the page (the caller re-renders the screen)
    local markFrame = body:FindFirstChild("KitWindowMark")
    task.spawn(function()
        while markFrame and markFrame.Parent do
            task.wait(1)
            if not markFrame.Parent then return end
            local now = workspace:GetServerTimeNow()
            if ProgressionRules.shopWindow(now) ~= d.window then d.restocked() return end
            setWords(live.restock, restockWords(d.window))
        end
    end)
    return true
end

return M
