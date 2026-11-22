--!strict
-- BD-1296 (docs/246 slice 2): with Config.MenusSaeFrameEnabled the POTION SHOP is the shop menu kit window (client/KitWindow, slice 1's
-- Crystal Shop window): the green header "Potion Shop" with the red X, THREE potions per page as kit rarity cards (the name, "Lasts 5 min",
-- the bound potion picture, a kid line "Grow faster!" on the dark strip, the green price button with the orange crystal; "Sold out" grey),
-- "New in 2 min" as one 22 px line with the grey More / Back page button beside it, and the "Yours" strip with the potions the player
-- owns (tap one to drink it). The shop tabs sit outside the window on the right (Potions selected). Numbers: Shared/SaeMenuRules
-- (potionLayout); art: Shared/ShopKit2 through the kit pieces. Client presentation only: no remote, no price and no stock rule here; a buy
-- tap opens the purchase confirm (ShopScreens), a use tap goes through ShopScreens' use path, the server decides both.
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

-- body: the Bootstrap panel body. d = {p (progression), window (shop window number), onBuy(item), onUse(item), onTab(tab), close(),
-- restocked()}. Returns false when the kit window cannot open (the caller then draws the old page).
function M.build(body: GuiObject, d: any): boolean
    if state.window ~= d.window then state.window, state.page = d.window, 1 end
    local p = d.p
    local offers = ProgressionRules.shopOffers(d.window)
    local first, last, pages = Menu.page(#offers, state.page, Menu.Potion.perPage)
    state.page = math.clamp(state.page, 1, pages)
    local gem = ShopArt.validId(require(Shared.UIIconAssets).amber)
    local cards = {}
    for i = first, last do
        local offer = offers[i]
        local item = ProgressionRules.item(ProgressionConfig.Potions, offer.id)
        if item then
            local left = ProgressionRules.shopRemaining(p, d.window, item.id)
            local function buy() if left > 0 then d.onBuy(item) end end
            table.insert(cards, {
                key = item.id, rarity = item.rarity, name = item.name, rarityWord = Menu.lasts(item.duration),
                picture = icon(item), effect = Menu.kindWord(item.kind),
                price = if left > 0 then item.price else nil, word = if left > 0 then nil else Menu.SoldOut, grey = left <= 0,
                gem = gem, onPick = buy,
            })
        end
    end
    local live: {restock: TextLabel?} = {restock = nil}
    local spec: any
    spec = {
        title = Menu.PotionTitle, colour = Menu.PotionColour, cards = cards,
        layout = function(w: number, h: number, _: number, inset: number?) return Menu.potionLayout(w, h, inset) end,
        onClose = function() if d.close then d.close() end end,
        rail = {
            tabs = FrameRules.RailTabs, words = FrameRules.RailWords, selected = "potions", icon = Landing.tabIcon,
            onTab = function(tab: string) if tab ~= "potions" then d.onTab(tab) end end,
        },
        content = function(window: Frame, lay: any, _: Frame)
            local r, m = lay.restock, lay.more
            local line = Art.words(window, "Restock", TimerWords.potionsIn(math.max(0, math.ceil(ProgressionRules.shopEndsAt(d.window) - workspace:GetServerTimeNow()))),
                r.x, r.y, r.w, r.h, r.size, 36)
            line.TextXAlignment = Enum.TextXAlignment.Left
            live.restock = line
            if pages > 1 then
                KitButton.draw(window, "PageButton", m.x, m.y, m.w, m.h, 36, {word = if state.page < pages then Menu.MoreWord else Menu.BackWord,
                    grey = true, textSize = lay.buttonText, onPress = function()
                        state.page = if state.page < pages then state.page + 1 else 1
                        d.rerender()
                    end})
            end
            local b = lay.band
            if not b then return end
            local strip = Art.studded(window, "Yours", Kit2.StripSlot, b.x, b.y, b.w, b.h, 34, b.h / Kit2.Studded[Kit2.StripSlot].h, b.h / Kit2.Studded[Kit2.StripSlot].h)
            if not strip then strip = Art.box(window, "Yours", b.x, b.y, b.w, b.h, 34) end
            local x = 14
            local label = Art.words(strip, "YoursWord", Menu.YoursWord, x, 0, 90, b.h, b.text, 36)
            label.TextXAlignment = Enum.TextXAlignment.Left
            x += FrameRules.textWidth(Menu.YoursWord, b.text) + 16
            local any = false
            for _, item in ProgressionConfig.Potions do
                local n = (p.potions or {})[item.id] or 0
                local id = icon(item)
                local countW = FrameRules.textWidth(Menu.count(n), b.text) + 8
                if n > 0 and id and x + b.icon + countW <= b.w - 8 then
                    any = true
                    Art.picture(strip, "Own_" .. item.id, id, x, math.floor((b.h - b.icon) / 2), b.icon, b.icon, 36)
                    local count = Art.words(strip, "OwnCount_" .. item.id, Menu.count(n), x + b.icon - 6, 0, countW, b.h, b.text, 37)
                    count.TextXAlignment = Enum.TextXAlignment.Left
                    Art.tap(strip, "Use_" .. item.id, x, 0, b.icon + countW - 6, b.h, 38, function() d.onUse(item) end)
                    x += b.icon + countW + 4
                end
            end
            if not any then
                local none = Art.words(strip, "NoneWord", Menu.NoneWord, x, 0, b.w - x - 8, b.h, FrameRules.fitSize(Menu.NoneWord, b.w - x - 12, b.text), 36)
                none.TextXAlignment = Enum.TextXAlignment.Left
            end
        end,
    }
    if not KitWindow.open(body, spec) then return false end
    -- the restock line counts down; a new shop window redraws the page (the caller re-renders the screen)
    local mark = body:FindFirstChild("KitWindowMark")
    task.spawn(function()
        while mark and mark.Parent do
            task.wait(1)
            if not mark.Parent then return end
            local now = workspace:GetServerTimeNow()
            if ProgressionRules.shopWindow(now) ~= d.window then d.restocked() return end
            setWords(live.restock, TimerWords.potionsIn(math.max(0, math.ceil(ProgressionRules.shopEndsAt(d.window) - now))))
        end
    end)
    return true
end

return M
