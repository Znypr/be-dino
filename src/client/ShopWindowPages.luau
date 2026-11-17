--!strict
-- BD-1266 / BD-1267 / BD-1270 (docs/244 s2.12 to s2.14, owner 2026-11-17 "Yes, build it"): the Crystal Shop on the ONE
-- standard window (src/client/MenuWindow.luau), behind Config.StandardMenuEnabled (off by default, on in the playtest profile). With the flag
-- off nothing here is ever required and the shop is drawn by ShopScreens exactly as before.
--   Crystal Shop: green long window. Side tabs Featured (BD-1270, its own flag ShopFeaturedEnabled), Auras, Trails, Eggs, Luck (egg conditions,
--     from level 3). Featured = this week's thing on one big offer card plus "-- NEW --" with two more; Auras / Trails = item cards 3 per row;
--     Eggs = offer cards; Luck = the upgrade offer card and the five egg conditions as item cards with their chance.
-- First slice only (owner 2026-11-18: "don't do too much at once"): the Potion Shop, the Aura Shop look and the egg picker follow after the
-- owner has approved this one; the Featured tab is built but its flag stays off in every profile until then.
-- Prices are crystals only (docs/43): no Robux pack tab, no gift, no crossed-out price. Buying goes through the same remote and the same
-- token as before (ShopScreens.transact, the server re-checks everything); the small "Buy X?" confirm sits inside the window.
-- Card pictures are existing art only (docs/72, docs/77): the aura ring renders, the shop tab icons, the egg render.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Theme = require(Shared.UITheme)
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Rules = require(Shared.MenuWindowRules)
local ArtworkAssets = require(Shared.ArtworkAssets)
local ProgressionConfig = require(Shared.ProgressionConfig)
local UIFormat = require(Shared.UIFormat)
local FtueP1 = require(Shared.FtueP1)
local ShopOdds = require(Shared.ShopOdds)
local EggGenetics = require(Shared.EggGenetics)
local MenuWindow = require(script.Parent.MenuWindow)
local C = Theme.Colors

local Pages = {}
Pages.Names = {auras = "crystalShop"}

local window: any = nil
local current: string? = nil -- "auras": which shop the open window shows
local tabs: {[string]: string} = {} -- the open tab per shop, kept between opens
local d: any = nil -- ShopScreens' helpers: {gui, num, progression, notify, open, transact, randomBlocked, openChances, closeMenu}

local function img(slot: string): string? return MenuWindow.image(slot) end
local function now(): number return workspace:GetServerTimeNow() end

-- ---------------------------------------------------------------- pictures (existing art only)
local function auraArt(id: string): string? return (ArtworkAssets :: any)["aura_" .. id .. "_ring"] end
-- Trails have no own render yet (ProgressionConfig.TrailIconAssetIds is empty): the trail tab icon in the trail's colour.
local function trailArt(item: any): (GuiObject) -> ()
    return function(box: GuiObject)
        local own = (ProgressionConfig.TrailIconAssetIds :: any)[item.id]
        local pic = Instance.new("ImageLabel")
        pic.Name, pic.BackgroundTransparency, pic.ScaleType, pic.Size, pic.ZIndex = "TrailPicture", 1, Enum.ScaleType.Fit, UDim2.fromScale(1, 1), box.ZIndex + 1
        pic.Image = own or img("shop_tab_trails") or ""
        if not own then pic.ImageColor3 = Color3.fromRGB(item.color[1], item.color[2], item.color[3]):Lerp(Color3.new(1, 1, 1), 0.35) end
        pic.Parent = box
    end
end
local function eggArt(conditionId: string?): (GuiObject) -> ()
    return function(box: GuiObject)
        local side = math.min(box.AbsoluteSize.X, box.AbsoluteSize.Y)
        if side < 8 then side = math.max(box.Size.X.Offset, box.Size.Y.Offset) end
        if conditionId then
            local pic = require(script.Parent.EggPicture).add(box, EggGenetics.neutral(conditionId), side)
            pic.AnchorPoint, pic.Position = Vector2.new(0.5, 0.5), UDim2.fromScale(0.5, 0.5)
        else
            local pic = Instance.new("ImageLabel")
            pic.Name, pic.BackgroundTransparency, pic.ScaleType, pic.Size, pic.ZIndex = "EggProduct", 1, Enum.ScaleType.Fit, UDim2.fromScale(1, 1), box.ZIndex + 1
            pic.Image, pic.Parent = img("egg_green_spotted") or "", box
        end
    end
end

-- ---------------------------------------------------------------- buying (same remote and token as before)
local function short(price: number): boolean return d.num("Crystals") < price end
local function needMore(price: number) d.notify("Need " .. price .. " Crystals", C.gold) end

local function cosmeticState(item: any, owned: boolean, equipped: boolean, isTrail: boolean): (string, number?)
    if equipped then return "equipped" end
    if owned then return "owned" end
    if isTrail and d.num("AccountLevel") < (item.level or 1) then return "locked", item.level end
    if short(item.price) then return "short" end
    return "buy"
end
local function cosmeticPress(item: any, isTrail: boolean)
    return function()
        local p = d.progression()
        local owned = if isTrail then (p.trails or {})[item.id] == true else (p.auras or {})[item.id] == true
        local equipped = (if isTrail then p.equippedTrail or "" else p.equippedAura) == item.id
        if owned then d.transact(if isTrail then "equipTrail" else "equipAura", if equipped then "" else item.id) return end
        if isTrail and d.num("AccountLevel") < (item.level or 1) then d.notify("Reach level " .. item.level, C.gold) return end
        if short(item.price) then needMore(item.price) return end
        window:confirm({title = "Buy " .. item.name .. "?", price = item.price, image = if isTrail then nil else auraArt(item.id),
            art = if isTrail then trailArt(item) else nil,
            onBuy = function() d.transact(if isTrail then "buyTrail" else "buyAura", item.id) end})
    end
end
local function cosmeticCard(grid: GuiObject, item: any, isTrail: boolean, offer: boolean, order: number?)
    local p = d.progression()
    local owned = if isTrail then (p.trails or {})[item.id] == true else (p.auras or {})[item.id] == true
    local equipped = (if isTrail then p.equippedTrail or "" else p.equippedAura) == item.id
    local state, level = cosmeticState(item, owned, equipped, isTrail)
    local effect = if isTrail then (UIFormat.boost("Speed", item.speed) or "Looks cool") else (UIFormat.boost("Growth", item.growth) or "Growth")
    local spec = {name = item.id, title = item.name, rarity = item.rarity, state = state, price = item.price, level = level, order = order,
        image = if isTrail then nil else auraArt(item.id), art = if isTrail then trailArt(item) else nil, onPress = cosmeticPress(item, isTrail)}
    if offer then
        spec.line = effect
        return window:offerCard(grid, spec)
    end
    spec.effect = effect
    return window:itemCard(grid, spec)
end

-- ---------------------------------------------------------------- Crystal Shop pages
local function featuredPool(): {any}
    local pool = {}
    for _, a in ProgressionConfig.Auras do table.insert(pool, {kind = "aura", id = a.id, price = a.price, item = a}) end
    for _, t in ProgressionConfig.Trails do table.insert(pool, {kind = "trail", id = t.id, price = t.price, item = t}) end
    return pool
end
Pages.featuredPool = featuredPool

local function featured()
    local picks = Rules.featured(featuredPool(), now())
    if #picks == 0 then window:line("Nothing new this week") return end
    window:section("Featured", "yellow")
    local big = window:grid("offer", 1)
    local first = picks[1]
    cosmeticCard(big, first.item, first.kind == "trail", true)
    window:line(Rules.daysLeft(now()), Rules.H.offerLine) -- the timer in kid words ("3 days left"), never seconds
    if #picks > 1 then
        window:section("New", "purple")
        local grid = window:grid("offer")
        for i = 2, #picks do cosmeticCard(grid, picks[i].item, picks[i].kind == "trail", true, i) end
    end
end

local function cosmetics(isTrail: boolean)
    window:section(if isTrail then "Trails" else "Auras", "green")
    local grid = window:grid("item")
    for i, item in (if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras) do
        if (item.price or 0) > 0 then cosmeticCard(grid, item, isTrail, false, i) end -- the free starter trail is never on sale
    end
end

local function eggs()
    window:section("Eggs", "yellow")
    local grid = window:grid("offer")
    local price = ProgressionConfig.RandomEggPrice
    local blocked = d.randomBlocked()
    window:offerCard(grid, {name = "RandomEgg", title = "Random Egg", line = "Hatch a new dino!", rarity = "Uncommon", art = eggArt(nil),
        state = if blocked then "soon" elseif short(price) then "short" else "buy", price = price, order = 1,
        onPress = function()
            if blocked then return end
            if short(price) then needMore(price) return end
            d.open("eggPurchase") -- the egg purchase screen with its odds (Bootstrap's window; this one closes)
        end})
    window:offerCard(grid, {name = "EggChances", title = "Egg chances", line = "See what can hatch", rarity = "Rare", image = img("notify_star"),
        state = "chances", order = 2, onPress = function() d.openChances() end})
end

local function luck()
    local p = d.progression()
    local level = p.conditionLevel or 0
    local upgrade = ProgressionConfig.ConditionUpgrades[level + 1]
    local _, ok = FtueP1.upgradeButton(upgrade, d.num("AccountLevel"), d.num("Crystals"))
    local blocked = d.randomBlocked()
    local state, need = "buy", nil
    if upgrade == nil then state = "max"
    elseif blocked then state = "soon"
    elseif d.num("AccountLevel") < upgrade.requiredLevel then state, need = "locked", upgrade.requiredLevel
    elseif not ok then state = "short" end
    window:section("Egg luck", "yellow")
    local top = window:grid("offer", 1)
    window:offerCard(top, {name = "LuckUpgrade", title = "Better eggs", line = "Luck level " .. tostring(level + (if upgrade then 1 else 0)),
        rarity = "Epic", image = img("shop_tab_conditions"), state = state, price = if upgrade then upgrade.price else 0, level = need,
        onPress = function()
            if state == "short" and upgrade then needMore(upgrade.price) return end
            if state == "locked" then d.notify("Reach level " .. tostring(need), C.gold) return end
            if state == "buy" then d.open("conditionConfirm") end
        end})
    window:section("Chances", "cyan")
    local weights = ShopOdds.conditionPercents(level)
    local tier = {cracked = "Common", dirty = "Common", normal = "Uncommon", rainbow = "Epic", astra = "Legendary"}
    local grid = window:grid("item")
    for i, row in ProgressionConfig.Conditions do
        window:itemCard(grid, {name = row.id, title = row.name, rarity = tier[row.id] or "Common", effect = string.format("%g%%", weights[i]),
            art = eggArt(row.id), state = "none", order = i})
    end
end

local function crystalShop()
    local level = d.num("AccountLevel")
    local list = Rules.shopTabs(FtueP1.shopTabs(level), Config.ShopFeaturedEnabled == true)
    local tab = Rules.firstTab(list, tabs.auras)
    tabs.auras = tab
    window:setTabs(list, tab, function(next) tabs.auras = next window:clear() crystalShop() end)
    window:clear()
    if tab == "featured" then featured()
    elseif tab == "auras" then cosmetics(false)
    elseif tab == "trails" then cosmetics(true)
    elseif tab == "eggs" then eggs()
    elseif tab == "conditions" then luck() end
end

-- ---------------------------------------------------------------- open / close / refresh
local function draw()
    if not window then return end
    if current == "auras" then crystalShop() end
end

-- Open (or switch) the standard window for a shop name ("auras" = Crystal Shop). helpers from ShopScreens.
function Pages.show(name: string, helpers: any)
    d = helpers
    if d.closeMenu then d.closeMenu() end -- two windows never stack: Bootstrap's own window closes first
    local screen = Rules.Screens[Pages.Names[name] or "crystalShop"]
    if window and current ~= name then window:close() end
    current = name
    if not window then
        local gui = d.gui()
        if not gui then return false end
        window = MenuWindow.new({title = screen.title, colour = screen.colour, kind = screen.kind, gui = gui,
            onClose = function() window, current = nil, nil end})
        window.redraw = draw
    end
    draw()
    return true
end
function Pages.isOpen(): boolean return window ~= nil end
function Pages.current(): string? return current end
-- A purchase answered: draw the open page again with the new numbers.
function Pages.refresh() if window then draw() end end
function Pages.close() if window then window:close() end end
-- For tests and captures.
function Pages.window(): any return window end

return Pages
