-- Offline smoke for the shop card with the price on the button (BD-1118 / BD-1144; driven by tools/verify_shop_card_price.py; docs/202 R3, docs/213).
-- tools/text_style_floors.build puts the head of tools/menu_layout_smoke.luau in front of this file (the geometry mock, the stubs, the Bootstrap-shaped
-- world, mountShop, showMenu) and swaps in the real modules: the REAL ShopScreens, ShopCards, ShopCard, ShopPreview, ShopCardState, RarityWord,
-- ModalCompact and PhoneScale run here. What is checked:
--   1. the flag is false in source; with it off the Build 020 card draws (chips, BUY, no Info);
--   2. with it on, at the 12 window sizes with a mouse and with touch, on the Auras and the Trails page: no chips and no price caption; the name in its
--      tier colour; an Info button of at least 44 px on screen; the stage higher than half the card on a desktop window and never under the button;
--      the benefit band along the bottom of the stage with the real words; ONE button as wide as the card minus the margins, saying the price while the
--      item can be bought (green), UNEQUIP on the equipped card (card colour), LEVEL n on a locked trail (grey, no price), every button text at least
--      16 px on screen (14 in a small window);
--   3. behaviour: a tap on the price opens the confirm page and sends NOTHING to the server; BUY on the confirm page sends exactly one buyAura; Info opens
--      the read-only page (name, lines, Back, NO buy button) and Back returns to the shop; a tap on a locked trail stays on the shop and sends nothing.
-- Text is not measured in the mock (no font): this is about rectangles and the words asked for. NOT Studio evidence (the Studio look is its own row).
-- @@PREFIX@@ is already replaced by the head of menu_layout_smoke.
local ALLOW = @@ALLOW@@
local _ = ALLOW
local ShopCardReal = requireModule(ClientFolder.ShopCard)
local ShopPreviewReal = requireModule(SharedFolder.ShopPreview)
local RarityWordReal = requireModule(SharedFolder.RarityWord)
local ProgressionReal = requireModule(SharedFolder.ProgressionConfig)
local TextStyleReal = requireModule(SharedFolder.TextStyle)
local UIFormatReal = requireModule(SharedFolder.UIFormat)

check(ConfigReal.ShopCardPriceButtonEnabled == false, "Config.ShopCardPriceButtonEnabled must be false in source")
local ConfigOn = table.clone(ConfigReal)
ConfigOn.ShopCardPriceButtonEnabled = true
local function withFlag(on) -- ShopCards reads Shared.Config once when it loads: swap the copy and load it again (AFTER buildWorld, which puts the real Config back)
    loaded.Config, loaded.ShopCards = if on then ConfigOn else ConfigReal, nil
end

local fired = {}
methods.FireServer = function(_, action, id) table.insert(fired, {action = action, id = id}) end

local function pxOf(d)
    local size = d.TextSize or 14
    local _, _, k = layout(d)
    return size * k
end
local function cardsOf(world, prefix)
    local out = {}
    for _, d in world.body:GetChildren() do
        if d:IsA("GuiObject") and d.Visible and string.find(d.Name, prefix, 1, true) == 1 then table.insert(out, d) end
    end
    table.sort(out, function(a, b) return a.Position.X.Offset < b.Position.X.Offset end)
    return out
end
local function childNamed(parent, name) return parent:FindFirstChild(name) end
local function hasChip(card)
    for _, d in card:GetChildren() do if string.find(d.Name, "Chip_", 1, true) == 1 or d.Name == "TierBadge" then return true end end
    return false
end
local function itemOf(list, id) for _, it in list do if it.id == id then return it end end return nil end
local function openTrails(world) for _, tab in tabsOf(world) do if tab.Text == "TRAILS" then tab.Activated:Fire() end end end

-- ===== 1. the flag off: the Build 020 card =====
do
    local world = buildWorld(1156, 793, false)
    withFlag(false)
    local shop = mountShop(world, {touch = false})
    showMenu(world) shop.open("auras") ModalCompact.enforce()
    local cards = cardsOf(world, "AuraCard_")
    check(#cards == 3, "flag off: three aura cards (" .. #cards .. ")")
    for _, card in cards do
        check(hasChip(card), "flag off: the old card keeps its chips (" .. card.Name .. ")")
        check(childNamed(card, "Info") == nil, "flag off: no Info button (" .. card.Name .. ")")
        local act = childNamed(card, "Action")
        check(act ~= nil and (act.Text == "BUY" or act.Text == "UNEQUIP"), "flag off: the button says BUY or UNEQUIP (" .. tostring(act and act.Text) .. ")")
    end
    world.gui:Destroy()
end

-- ===== 2. the flag on: every size, mouse and touch, Auras then Trails =====
local seen = {buy = 0, unequip = 0, locked = 0}
for _, touch in {false, true} do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        for _, page in {"auras", "trails"} do
            local world = buildWorld(w, h, touch)
            withFlag(true)
            local shop = mountShop(world, {touch = touch, level = 1})
            showMenu(world) shop.open("auras")
            if page == "trails" then openTrails(world) end
            ModalCompact.enforce()
            local compact = ModalCompact.model().mode == "compact"
            local tag = string.format("Price card %s %dx%d%s", page, w, h, if touch then " touch" else "")
            local isTrail = page == "trails"
            local cards = cardsOf(world, if isTrail then "TrailCard_" else "AuraCard_")
            check(#cards == 3, tag .. ": three cards (" .. #cards .. ")")
            for _, card in cards do
                local id = string.sub(card.Name, (if isTrail then #"TrailCard_" else #"AuraCard_") + 1)
                local item = itemOf(if isTrail then ProgressionReal.Trails else ProgressionReal.Auras, id)
                local ctag = tag .. " " .. id
                check(item ~= nil, ctag .. ": a known item")
                if item == nil then continue end
                check(not hasChip(card), ctag .. ": no chips on the price card")
                local cr = rectOf(card)
                -- row 1: the name in its tier colour, the Info button a real tap target
                local name, info = childNamed(card, "Name"), childNamed(card, "Info")
                local _, tierColour = RarityWordReal.get(item.rarity)
                check(name ~= nil and name.Text == item.name and name.TextColor3 == tierColour, ctag .. ": the name in its tier colour")
                check(info ~= nil and info.Text == ShopPreviewReal.InfoWord, ctag .. ": an Info button")
                if info then
                    local ir = rectOf(info)
                    check(ir.w >= 43.5 and ir.h >= 43.5, string.format("%s: the Info button is %dx%d px on screen (needs 44)", ctag, ir.w + .5, ir.h + .5))
                    check(inside(ir, cr, 1.5), ctag .. ": the Info button is inside the card")
                    if name then check(not overlaps(rectOf(name), ir), ctag .. ": the name runs under the Info button") end
                    check(TextStyleReal.onScreenOk("card", pxOf(info), compact), string.format("%s: the Info word is %.1f px on screen", ctag, pxOf(info)))
                end
                -- the stage: more than half the card on a desktop window, clear of the button, the benefit band along its bottom
                local stage, act = childNamed(card, "PreviewStage"), childNamed(card, "Action")
                check(stage ~= nil and act ~= nil, ctag .. ": a stage and one Action button")
                if stage == nil or act == nil then continue end
                local sr, ar = rectOf(stage), rectOf(act)
                if not compact then check(sr.h > cr.h / 2, string.format("%s: the stage is %d of %d px high (needs more than half)", ctag, sr.h + .5, cr.h + .5)) end
                check(sr.h >= 56 * (ModalCompact.bodyScale()) - 1, ctag .. ": the stage keeps room for a picture")
                check(sr.y + sr.h <= ar.y + .5, ctag .. ": the stage runs under the button")
                check(info == nil or rectOf(info).y + rectOf(info).h <= sr.y + .5, ctag .. ": the stage runs up over the Info button")
                local band = childNamed(stage, "BenefitBand")
                local benefit = band and childNamed(band, "Benefit")
                local words = if isTrail then ShopPreviewReal.speedWords(item.speed) else (UIFormatReal.boost("Growth", item.growth) or "Growth")
                check(benefit ~= nil and benefit.Text == words, ctag .. ": the benefit band says '" .. words .. "' (" .. tostring(benefit and benefit.Text) .. ")")
                if band then
                    local br = rectOf(band)
                    check(math.abs(br.y + br.h - (sr.y + sr.h)) < 1.5 and math.abs(br.w - sr.w) < 1.5, ctag .. ": the benefit band lies along the bottom of the stage")
                    if benefit then check(TextStyleReal.onScreenOk("card", pxOf(benefit), compact), string.format("%s: the benefit is %.1f px on screen", ctag, pxOf(benefit))) end
                end
                -- ONE wide button with the price, EQUIP / UNEQUIP or LEVEL n
                local buttons = 0
                for _, d in card:GetChildren() do if d:IsA("TextButton") and d.Name ~= "Info" then buttons += 1 end end
                check(buttons == 1, ctag .. ": exactly one action button (" .. buttons .. ")")
                check(math.abs(ar.w - (cr.w - 16 * ModalCompact.bodyScale())) < 2, string.format("%s: the button is %d px wide on a %d px card (needs the card minus the margins)", ctag, ar.w + .5, cr.w + .5))
                check(inside(ar, cr, 1.5), ctag .. ": the button is inside the card")
                check(TextStyleReal.onScreenOk("card", pxOf(act), compact), string.format("%s: the button text is %.1f px on screen", ctag, pxOf(act)))
                local equipped = not isTrail and id == "meadow"
                local locked = isTrail and item.level > 1
                if equipped then
                    seen.unequip += 1
                    check(act.Text == "UNEQUIP" and act.BackgroundColor3 == Colors.card and act.Active == true, ctag .. ": the equipped card says UNEQUIP in the card colour (" .. act.Text .. ")")
                    check(card:FindFirstChild("EquippedRing") ~= nil, ctag .. ": the equipped ring stays")
                elseif locked then
                    seen.locked += 1
                    check(act.Text == "LEVEL " .. item.level and act.BackgroundColor3 == ShopCardReal.SoldOutColor, ctag .. ": a locked trail says LEVEL n on a grey button (" .. act.Text .. ")")
                    check(not string.find(act.Text, "Crystals", 1, true), ctag .. ": no price on a locked button")
                else
                    seen.buy += 1
                    check(act.Text == item.price .. " Crystals" and act.BackgroundColor3 == Colors.accent and act.Active == true, ctag .. ": the price is on the green button (" .. act.Text .. ")")
                end
                -- nothing else writes the price on the card
                for _, d in card:GetDescendants() do
                    if d:IsA("TextLabel") and string.find(d.Text, "Crystals", 1, true) then check(false, ctag .. ": a price caption is still on the card ('" .. d.Text .. "')") end
                end
            end
            world.gui:Destroy()
        end
    end
end
check(seen.buy > 0 and seen.unequip > 0 and seen.locked > 0, string.format("the sweep saw every button kind (buy %d, unequip %d, locked %d)", seen.buy, seen.unequip, seen.locked))

-- ===== 3. behaviour: the price only opens the confirm page; Info opens the read-only page =====
for _, size in {{1156, 793}, {516, 481}} do
    local world = buildWorld(size[1], size[2], false)
    withFlag(true)
    local shop = mountShop(world, {touch = false, level = 1})
    showMenu(world) shop.open("auras") ModalCompact.enforce()
    local tag = string.format("Behaviour %dx%d", size[1], size[2])
    check(shop.Shop.names.auraInfo == true, tag .. ": auraInfo is a shop page (Bootstrap routes open() by Shop.names)")
    local cards = cardsOf(world, "AuraCard_")
    local tidal = nil
    for _, c in cards do if c.Name ~= "AuraCard_meadow" and tidal == nil then tidal = c end end
    check(tidal ~= nil, tag .. ": an aura the player does not own")
    if tidal then
        local id = string.sub(tidal.Name, #"AuraCard_" + 1)
        fired = {}
        childNamed(tidal, "Action").Activated:Fire()
        check(shop.name == "auraConfirm", tag .. ": a tap on the price opens the confirm page (" .. shop.name .. ")")
        check(#fired == 0, tag .. ": a tap on the price sends nothing to the server (" .. #fired .. " sent)")
        local buy = nil
        for _, d in world.body:GetChildren() do if d:IsA("TextButton") and string.find(d.Text, "BUY", 1, true) == 1 then buy = d end end
        check(buy ~= nil, tag .. ": the confirm page keeps its BUY button")
        if buy then
            buy.Activated:Fire()
            check(#fired == 1 and fired[1].action == "buyAura" and fired[1].id == id, tag .. ": BUY on the confirm page sends one buyAura (" .. #fired .. ")")
        end
        -- Info: the read-only page
        shop.open("auras") ModalCompact.enforce()
        tidal = nil
        for _, c in cardsOf(world, "AuraCard_") do if c.Name == "AuraCard_" .. id then tidal = c end end
        fired = {}
        childNamed(tidal, "Info").Activated:Fire()
        check(shop.name == "auraInfo", tag .. ": Info opens the details page (" .. shop.name .. ")")
        check(#fired == 0, tag .. ": Info sends nothing to the server")
        local item = itemOf(ProgressionReal.Auras, id)
        local nameLabel = world.body:FindFirstChild("InfoName")
        local _, tierColour = RarityWordReal.get(item.rarity)
        check(nameLabel ~= nil and nameLabel.Text == item.name and nameLabel.TextColor3 == tierColour, tag .. ": the details page names the aura in its tier colour")
        local lines = ShopPreviewReal.infoLines(item, false, {owned = false, equipped = false}, UIFormatReal.boost("Growth", item.growth))
        check(#lines >= 3, tag .. ": at least three info lines (" .. #lines .. ")")
        for i, line in lines do
            local l = world.body:FindFirstChild("InfoLine" .. i)
            local plain = l and (if l.RichText then string.gsub(string.gsub(l.Text, "<[^>]+>", ""), "&amp;", "&") else l.Text)
            check(l ~= nil and plain == line, tag .. ": info line " .. i .. " is '" .. line .. "' (" .. tostring(plain) .. ")")
            if l and RarityWordReal.has(line) then check(l.RichText == true and string.find(l.Text, "<font", 1, true) ~= nil, tag .. ": the rarity word on line " .. i .. " is coloured") end
        end
        for _, d in world.body:GetDescendants() do
            if d:IsA("TextButton") then check(string.find(string.upper(d.Text), "BUY", 1, true) == nil and not string.find(d.Text, "Crystals", 1, true), tag .. ": no buy button on the details page ('" .. d.Text .. "')") end
        end
        local back = world.body:FindFirstChild("InfoBack")
        check(back ~= nil, tag .. ": a Back button")
        if back then
            local br = rectOf(back)
            check(br.h >= 43.5, string.format("%s: Back is %d px high on screen (needs 44)", tag, br.h + .5))
            back.Activated:Fire()
            check(shop.name == "auras", tag .. ": Back returns to the shop (" .. shop.name .. ")")
        end
    end
    -- a locked trail: the tap stays on the shop and sends nothing
    shop.open("auras") openTrails(world) ModalCompact.enforce()
    local lockedCard = nil
    for _, c in cardsOf(world, "TrailCard_") do
        local item = itemOf(ProgressionReal.Trails, string.sub(c.Name, #"TrailCard_" + 1))
        if item and item.level > 1 and lockedCard == nil then lockedCard = c end
    end
    check(lockedCard ~= nil, tag .. ": a locked trail on page 1")
    if lockedCard then
        fired = {}
        childNamed(lockedCard, "Action").Activated:Fire()
        check(shop.name == "auras" and #fired == 0, tag .. ": a tap on a locked trail stays on the shop and sends nothing")
    end
    world.gui:Destroy()
end

if failures > 0 then
    print(string.format("Shop card price smoke FAILED: %d problem(s)", failures))
    error("shop card price smoke failed")
end
print(string.format("Shop card price smoke passed: %d sizes x 2 inputs x 2 pages, buttons seen: %d price, %d unequip, %d locked; price -> confirm page, Info -> read-only page", #SIZES, seen.buy, seen.unequip, seen.locked))
