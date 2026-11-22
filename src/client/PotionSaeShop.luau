--!strict
-- BD-1296 (docs/246 slice 2): with Config.MenusSaeFrameEnabled the POTION SHOP is the shop menu kit window (client/KitWindow, slice 1's
-- Crystal Shop window). BD-1298: laid out as the owner's PROPOSED PICTURE (docs/evidence/2026-11-23-potion-proposal/proposal.jpg): the
-- green header "Potions" with the red X, the yellow restock words "New in 2 min" INSIDE the header and a small grey page arrow left of the
-- X; THREE tall kit rarity cards with the picture's words only (the short name "Swift", the rarity word, the "x3" count top right, the
-- bound potion picture half the card, a kid line "Grow faster!" on the dark strip, the green price button with the orange crystal; "Sold
-- out" grey). Nothing under the cards. The arrow pages the shop, then "My Potions" (the potions the player owns, "x2", "Lasts 5 min" on
-- the strip, a green "Drink!" button: the only place to drink one), then the shop again. The shop tabs sit outside the window on the right in the picture's order (Potions selected).
-- Numbers: Shared/SaeMenuRules (potionLayout); art: Shared/ShopKit2 through the kit pieces. Client presentation only: no remote, no price
-- and no stock rule here; a buy tap opens the purchase confirm (ShopScreens), a drink tap goes through ShopScreens' use path, the server
-- decides both.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local ShopArt = require(Shared.ShopArt)
local Menu = require(Shared.SaeMenuRules)
local ProgressionConfig = require(Shared.ProgressionConfig)
local ProgressionRules = require(Shared.ProgressionRules)
local TimerWords = require(Shared.TimerWords)
local Art = require(script.Parent.KitArt)
local KitWindow = require(script.Parent.KitWindow)
local KitButton = require(script.Parent.KitButton)
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
    local cards, extras = {}, {}
    if not mine then
        local first, last = Menu.page(#offers, state.page, Menu.Potion.perPage)
        for i = first, last do
            local item = ProgressionRules.item(ProgressionConfig.Potions, offers[i].id)
            if item then
                local left = ProgressionRules.shopRemaining(p, d.window, item.id)
                local function buy() if left > 0 then d.onBuy(item) end end
                table.insert(cards, {
                    key = item.id, rarity = item.rarity, name = Menu.shortName(item.name), rarityWord = item.rarity, picture = icon(item),
                    effect = Menu.kindWord(item.kind, item.rarity), price = if left > 0 then item.price else nil,
                    word = if left > 0 then nil else Menu.SoldOut, grey = left <= 0, gem = gem, onPick = buy,
                })
                table.insert(extras, {badge = if left > 0 then Menu.count(left) else nil})
            end
        end
    else
        local first, last = Menu.page(#owned, state.page - shopPages, Menu.Potion.perPage)
        for i = first, math.min(last, #owned) do
            local item, n = owned[i].item, owned[i].n
            table.insert(cards, {
                key = item.id, rarity = item.rarity, name = Menu.shortName(item.name), rarityWord = item.rarity, picture = icon(item),
                effect = Menu.lasts(item.duration), word = Menu.DrinkWord, grey = false, onPick = function() d.onUse(item) end,
            })
            table.insert(extras, {badge = Menu.count(n)})
        end
    end
    local live: {restock: TextLabel?} = {restock = nil}
    local spec: any
    spec = {
        title = if mine then Menu.YoursTitle else Menu.PotionTitle, colour = Menu.PotionColour, cards = cards,
        layout = function(w: number, h: number, _: number, inset: number?) return Menu.potionLayout(w, h, inset) end,
        onClose = function() if d.close then d.close() end end,
        rail = {
            tabs = Menu.PotionRail, words = Menu.PotionRailWords, selected = "potions", icon = Landing.tabIcon,
            onTab = function(tab: string) if tab ~= "potions" then d.onTab(tab) end end,
        },
        content = function(window: Frame, lay: any, _: Frame)
            -- in the header: the restock words at 63 % (yellow-white), the page arrow left of the X
            local t = lay.timer
            local c = Menu.TimerColour
            live.restock = Art.words(window, "Restock", restockWords(d.window), t.x, t.y, t.w, t.h, t.size, 36, Color3.fromRGB(c[1], c[2], c[3]))
            local g = lay.page
            KitButton.draw(window, "PageButton", g.x, g.y, g.w, g.h, 36, {word = Menu.PageWord, grey = true, textSize = g.text, onPress = function()
                state.page = if state.page < pages then state.page + 1 else 1
                d.rerender()
            end})
            -- on each card: the small count top right ("x3" in stock / owned), as in the picture
            for i, extra in extras do
                local r = lay.cards[i]
                if not r then break end
                local b = lay.badge
                if extra.badge then
                    local badge = Art.words(window, "Badge_" .. i, extra.badge, r.x + b.x, r.y + b.y, b.w, b.h, b.size, 38)
                    badge.TextXAlignment = Enum.TextXAlignment.Right
                end
            end
            if mine and #cards == 0 then
                local r1, r3 = lay.cards[1], lay.cards[3]
                Art.words(window, "NoneWord", Menu.NoneWord, r1.x, r1.y, r3.x + r3.w - r1.x, r1.h, lay.cardTitle, 38)
            end
        end,
    }
    if not KitWindow.open(body, spec) then return false end
    -- the restock words count down; a new shop window redraws the page (the caller re-renders the screen)
    local mark = body:FindFirstChild("KitWindowMark")
    task.spawn(function()
        while mark and mark.Parent do
            task.wait(1)
            if not mark.Parent then return end
            local now = workspace:GetServerTimeNow()
            if ProgressionRules.shopWindow(now) ~= d.window then d.restocked() return end
            setWords(live.restock, restockWords(d.window))
        end
    end)
    return true
end

return M
