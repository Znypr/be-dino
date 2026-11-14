-- Offline smoke for the Crystal Shop in the "Toybox" look (BD-1178; driven by tools/verify_toybox_shop.py; docs/228 board 3, docs/231).
-- tools/text_style_floors.build puts the head of tools/menu_layout_smoke.luau in front of this file (the geometry mock, the stubs, the Bootstrap-shaped
-- world, mountShop, showMenu) and swaps in the real modules: the REAL ShopScreens, ShopCards, ShopToyboxCard, ShopPreview, ShopCardState, RarityWord,
-- ToyboxShop, ToyboxKit, EffectAssets, ModalCompact and PhoneScale run here. The skin itself is a stub (Theme.Toybox = {Kit = the real kit}), the way the
-- flag turns it on in the game; picture ids are bound by writing into AssetSlots.Images, one distinct id per slot. What is checked:
--   1. the pure rules (ToyboxShop): the card slot of each of the six rarities, the Common fallback, the "?" only for a LOCKED Legendary or Mythic, the
--      hint, the button colours, the rays stand still under Reduce Motion, the "Buy X?" popup words;
--   2. flag off (Theme.Toybox nil), or ids unbound (the state of this change), or ONE card id missing: the old card draws, no Toybox part exists, the old
--      CANCEL word stays on the confirm page;
--   3. flag on and ids bound, at the 12 window sizes with a mouse and with touch, Auras and Trails: every card has the picture of ITS tier, the name,
--      the rarity word, a cream art box that lies between the name row and the button, slow rays (three, from shaftGradient) only while that texture
--      is uploaded, the benefit band with the real words, ONE wide action button inside the card, the equipped card has its ring, the Info word is a
--      44 px target, no chips and no price caption, every word at least 14 px on screen;
--   4. a locked Legendary trail shows "?" and a hint and no picture; a locked trail of a lower tier shows its picture;
--   5. behaviour: a tap on the price opens the confirm page and sends nothing; the page says "Buy <name>?" and NOT NOW; BUY sends one buyAura; NOT NOW
--      returns to the shop and sends nothing.
-- Text is not measured in the mock (no font): this is about rectangles and the words asked for. NOT Studio evidence: nobody saw a pixel.
-- @@PREFIX@@ is already replaced by the head of menu_layout_smoke.
local ALLOW = @@ALLOW@@
local _ = ALLOW
local ShopPreviewReal = requireModule(SharedFolder.ShopPreview)
local RarityWordReal = requireModule(SharedFolder.RarityWord)
local ProgressionReal = requireModule(SharedFolder.ProgressionConfig)
local UIFormatReal = requireModule(SharedFolder.UIFormat)
local Rules = requireModule(SharedFolder.ToyboxShop)
local KitReal = requireModule(SharedFolder.ToyboxKit)
local SlotsReal = requireModule(SharedFolder.AssetSlots)
local EffectsReal = requireModule(SharedFolder.EffectAssets)
local ShopCardReal = requireModule(ClientFolder.ShopCard)

check(ConfigReal.ToyboxUIEnabled == false or ConfigReal.ToyboxUIEnabled == true, "Config.ToyboxUIEnabled exists")

local fired = {}
methods.FireServer = function(_, action, id) table.insert(fired, {action = action, id = id}) end

-- ===== 1. the pure rules =====
do
    local seen = {}
    for i, name in {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"} do
        local slot = Rules.cardSlot(name)
        check(slot == "toybox_card_" .. string.lower(name), "card slot of " .. name .. " is " .. slot)
        check(KitReal.Assets[slot] ~= nil, "the kit has the picture " .. slot)
        check(not seen[slot], "each rarity has its own picture (" .. slot .. ")")
        seen[slot] = true
        check(Rules.cardSlot(string.lower(name)) == slot, "the rarity is read in any case: " .. name)
        check(Rules.Rarities[i] == name, "rarity order " .. name)
    end
    check(Rules.cardSlot("nonsense") == "toybox_card_common" and Rules.cardSlot(nil) == "toybox_card_common" and Rules.cardSlot(7) == "toybox_card_common", "an unknown rarity is Common")
    check(Rules.mystery("Legendary", "locked") and Rules.mystery("Mythic", "locked"), "a locked Legendary or Mythic is a secret")
    check(not Rules.mystery("Legendary", "buy") and not Rules.mystery("Legendary", "equip") and not Rules.mystery("Legendary", "unequip") and not Rules.mystery("Legendary", "soldOut"), "a Legendary you can buy or own shows its picture")
    check(not Rules.mystery("Rare", "locked") and not Rules.mystery("Common", "locked") and not Rules.mystery("Epic", "locked"), "a locked card of a lower tier shows its picture")
    check(Rules.hint({level = 12}) == "Reach level 12" and Rules.hint({level = 1}) == "Keep playing to find it" and Rules.hint({}) == "Keep playing to find it", "the hint")
    check(Rules.buttonColour("buy") == "accent" and Rules.buttonColour("equip") == "accent" and Rules.buttonColour("unequip") == "card"
        and Rules.buttonColour("locked") == "soldOut" and Rules.buttonColour("soldOut") == "soldOut", "button colours")
    check(Rules.raySeconds(true) == 0 and Rules.raySeconds(false) >= 30, "rays stand still under Reduce Motion and turn slowly otherwise")
    check(#Rules.RayAngles == 3, "three rays")
    local confirm = Rules.confirm("Royal", false)
    check(confirm.title == "Buy Royal?" and confirm.cancel == "NOT NOW" and confirm.buy == "BUY AURA", "the Buy popup words")
    check(Rules.confirm("Ember Trail", true).buy == "BUY TRAIL", "the trail popup says BUY TRAIL")
    local layout = Rules.layout(230, 48, 28, 28)
    check(layout.artY > layout.pillY and layout.artY + layout.artH <= 230 and layout.bandY + 28 == layout.artH, "layout: the art box ends above the button and the band lies along its bottom")
end

-- ===== helpers =====
local function bind(on, except)
    for _, rarity in Rules.Rarities do
        local slot = "toybox_card_" .. string.lower(rarity)
        SlotsReal.Images[slot] = if on and slot ~= except then "rbxassetid://" .. (900000 + #slot * 7 + string.byte(slot, -1)) else ""
    end
end
local function toybox(on) -- the skin is a stub: ModalCompact and Theme.decorate call its hooks, which draw nothing here
    local function none() end
    Theme.Toybox = if on then {Kit = KitReal, window = none, place = none, button = none, close = none} else nil
end
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
local function toyboxPicture(card)
    local image = card:FindFirstChild("ToyboxCard")
    return image, image and image:GetAttribute("ToyboxSlot")
end

-- ===== 2. flag off / ids unbound / one id missing: the old card =====
for _, mode in {"flag off, ids bound", "flag on, ids unbound", "flag on, one card id missing"} do
    local world = buildWorld(1156, 793, false)
    if mode == "flag off, ids bound" then toybox(false) bind(true)
    elseif mode == "flag on, ids unbound" then toybox(true) bind(false)
    else toybox(true) bind(true, "toybox_card_rare") end
    local shop = mountShop(world, {touch = false})
    showMenu(world) shop.open("auras") ModalCompact.enforce()
    local cards = cardsOf(world, "AuraCard_")
    check(#cards == 3, mode .. ": three aura cards (" .. #cards .. ")")
    for _, card in cards do
        check(hasChip(card), mode .. ": the old card keeps its chips (" .. card.Name .. ")")
        check(toyboxPicture(card) == nil and childNamed(card, "ArtBox") == nil and childNamed(card, "RarityWord") == nil, mode .. ": no Toybox part on " .. card.Name)
    end
    -- the confirm page keeps its old words
    local target = nil
    for _, c in cards do if c.Name ~= "AuraCard_meadow" and target == nil then target = c end end
    if target then
        childNamed(target, "Action").Activated:Fire()
        check(shop.name == "auraConfirm", mode .. ": the price opens the confirm page")
        check(world.heading.Text == "Buy Aura?", mode .. ": the old title (" .. tostring(world.heading.Text) .. ")")
        local cancel, notNow = false, false
        for _, d in world.body:GetChildren() do
            if d:IsA("TextButton") and d.Text == "CANCEL" then cancel = true end
            if d:IsA("TextButton") and d.Text == "NOT NOW" then notNow = true end
        end
        check(cancel and not notNow, mode .. ": CANCEL stays, no NOT NOW")
    end
    world.gui:Destroy()
end

-- ===== 3. flag on, ids bound: every size, mouse and touch, Auras then Trails =====
local seen = {buy = 0, unequip = 0, locked = 0, tiers = {}}
for _, touch in {false, true} do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        for _, page in {"auras", "trails"} do
            local world = buildWorld(w, h, touch)
            toybox(true) bind(true)
            local shop = mountShop(world, {touch = touch, level = 1})
            showMenu(world) shop.open("auras")
            if page == "trails" then openTrails(world) end
            ModalCompact.enforce()
            local compact = ModalCompact.model().mode == "compact"
            local tag = string.format("Toybox %s %dx%d%s", page, w, h, if touch then " touch" else "")
            local isTrail = page == "trails"
            local cards = cardsOf(world, if isTrail then "TrailCard_" else "AuraCard_")
            check(#cards == 3, tag .. ": three cards (" .. #cards .. ")")
            for _, card in cards do
                local id = string.sub(card.Name, (if isTrail then #"TrailCard_" else #"AuraCard_") + 1)
                local item = itemOf(if isTrail then ProgressionReal.Trails else ProgressionReal.Auras, id)
                local ctag = tag .. " " .. id
                check(item ~= nil, ctag .. ": a known item")
                if item == nil then continue end
                check(not hasChip(card), ctag .. ": no chips on the Toybox card")
                local cr = rectOf(card)
                -- the picture of ITS tier
                local image, slot = toyboxPicture(card)
                local wanted = "toybox_card_" .. string.lower(item.rarity or "Common")
                check(image ~= nil and slot == wanted, ctag .. ": the card picture is " .. wanted .. " (" .. tostring(slot) .. ")")
                if image then
                    check(image.Image == SlotsReal.Images[wanted] and string.find(image.Image, "rbxassetid://", 1, true) == 1, ctag .. ": the picture id is the bound one")
                    check(image.ScaleType == "ScaleType.Slice" and image.SliceCenter ~= nil and image.SliceCenter.Min.X == KitReal.Assets[wanted].slice[1], ctag .. ": the picture is 9-sliced with the kit rect")
                    seen.tiers[wanted] = true
                end
                -- name, rarity word, Info
                local name, info, word = childNamed(card, "Name"), childNamed(card, "Info"), childNamed(card, "RarityWord")
                check(name ~= nil and name.Text == item.name, ctag .. ": the name")
                local expectWord = RarityWordReal.get(item.rarity)
                local _, tierColour = RarityWordReal.get(item.rarity)
                check(word ~= nil and word.Text == expectWord and word.TextColor3 == tierColour, ctag .. ": the rarity word in its tier colour")
                if word then check(pxOf(word) >= 13.5, string.format("%s: the rarity word is %.1f px on screen", ctag, pxOf(word))) end
                if name then check(pxOf(name) >= 13.5, string.format("%s: the name is %.1f px on screen", ctag, pxOf(name))) end
                check(info ~= nil and info.Text == ShopPreviewReal.InfoWord, ctag .. ": the Info word")
                if info then
                    local ir = rectOf(info)
                    check(ir.w >= 43.5 and ir.h >= 43.5, string.format("%s: the Info button is %dx%d px on screen (needs 44)", ctag, ir.w + .5, ir.h + .5))
                    check(inside(ir, cr, 1.5), ctag .. ": the Info button is inside the card")
                    if name then check(not overlaps(rectOf(name), ir), ctag .. ": the name runs under the Info button") end
                end
                -- the cream art box between the name row and the button
                local art, act = childNamed(card, "ArtBox"), childNamed(card, "Action")
                check(art ~= nil and act ~= nil, ctag .. ": an art box and one Action button")
                if art == nil or act == nil then continue end
                local ar, br = rectOf(art), rectOf(act)
                check(inside(ar, cr, 1.5), ctag .. ": the art box is inside the card")
                check(ar.y + ar.h <= br.y + .5, ctag .. ": the art box runs under the button")
                if word then check(rectOf(word).y + rectOf(word).h <= ar.y + 1.5, ctag .. ": the art box runs up over the rarity word") end
                if info then check(rectOf(info).y + rectOf(info).h <= ar.y + 1.5, ctag .. ": the art box runs up over the Info button") end
                check(ar.h >= 48 * ModalCompact.bodyScale() - 1, ctag .. ": the art box keeps room for a picture")
                -- rays: three, from the uploaded shaft texture
                local fan = childNamed(art, "Rays")
                check(fan ~= nil and #fan:GetChildren() == 3, ctag .. ": three slow rays behind the art")
                if fan then
                    for _, ray in fan:GetChildren() do check(ray.Image == EffectsReal.resolveUi("shaftGradient"), ctag .. ": a ray is the shaftGradient texture") end
                end
                -- the benefit band
                local band = childNamed(art, "BenefitBand")
                local benefit = band and childNamed(band, "Benefit")
                local words = if isTrail then ShopPreviewReal.speedWords(item.speed) else (UIFormatReal.boost("Growth", item.growth) or "Growth")
                check(benefit ~= nil and benefit.Text == words, ctag .. ": the benefit band says '" .. words .. "' (" .. tostring(benefit and benefit.Text) .. ")")
                if band then
                    local bbr = rectOf(band)
                    check(math.abs(bbr.y + bbr.h - (ar.y + ar.h)) < 1.5 and math.abs(bbr.w - ar.w) < 1.5, ctag .. ": the benefit band lies along the bottom of the art box")
                    if benefit then check(pxOf(benefit) >= 13.5, string.format("%s: the benefit is %.1f px on screen", ctag, pxOf(benefit))) end
                end
                -- ONE wide button
                local buttons = 0
                for _, d in card:GetChildren() do if d:IsA("TextButton") and d.Name ~= "Info" then buttons += 1 end end
                check(buttons == 1, ctag .. ": exactly one action button (" .. buttons .. ")")
                check(inside(br, cr, 1.5) and br.w >= cr.w - 24 * ModalCompact.bodyScale(), string.format("%s: the button is %d px wide inside a %d px card", ctag, br.w + .5, cr.w + .5))
                check(pxOf(act) >= 13.5, string.format("%s: the button text is %.1f px on screen", ctag, pxOf(act)))
                local equipped = not isTrail and id == "meadow"
                local locked = isTrail and item.level > 1
                if equipped then
                    seen.unequip += 1
                    check(act.Text == "UNEQUIP" and act.BackgroundColor3 == Colors.card, ctag .. ": the equipped card says UNEQUIP (" .. act.Text .. ")")
                    check(card:FindFirstChild("EquippedRing") ~= nil, ctag .. ": the equipped card has its gold ring")
                    local glow = card:FindFirstChild("EquippedGlow")
                    check(glow ~= nil and glow.Image == EffectsReal.resolveUi("glowPlate"), ctag .. ": the equipped card has the soft glow (glowPlate)")
                else
                    check(card:FindFirstChild("EquippedRing") == nil and card:FindFirstChild("EquippedGlow") == nil, ctag .. ": only the equipped card glows")
                end
                if not equipped and locked then
                    seen.locked += 1
                    check(act.Text == "LEVEL " .. item.level and act.BackgroundColor3 == ShopCardReal.SoldOutColor, ctag .. ": a locked trail says LEVEL n on a grey button (" .. act.Text .. ")")
                elseif not equipped then
                    seen.buy += 1
                    check(act.Text == item.price .. " Crystals" and act.BackgroundColor3 == Colors.accent, ctag .. ": the price is on the green button (" .. act.Text .. ")")
                end
                for _, d in card:GetDescendants() do
                    if d:IsA("TextLabel") and string.find(d.Text, "Crystals", 1, true) then check(false, ctag .. ": a price caption is on the card ('" .. d.Text .. "')") end
                end
                -- a locked Legendary would be a secret: none of the real items is both (section 4 builds one)
                check(childNamed(art, "Mystery") == nil or Rules.mystery(item.rarity, if equipped then "unequip" elseif locked then "locked" else "buy"), ctag .. ": the question mark only on a locked Legendary")
            end
            world.gui:Destroy()
        end
    end
end
check(seen.buy > 0 and seen.unequip > 0 and seen.locked > 0, string.format("the sweep saw every button kind (buy %d, unequip %d, locked %d)", seen.buy, seen.unequip, seen.locked))
local tierCount = 0
for _ in seen.tiers do tierCount += 1 end
check(tierCount >= 3, "the sweep saw at least three different tier pictures (" .. tierCount .. ")")

-- ===== rays only while the texture is uploaded; glow only while glowPlate is =====
do
    local world = buildWorld(1156, 793, false)
    toybox(true) bind(true)
    local shaft, glowReq = EffectsReal.Requested.shaftGradient.id, EffectsReal.Requested.glowPlate.id
    EffectsReal.Requested.shaftGradient.id, EffectsReal.Requested.glowPlate.id = "", ""
    local shop = mountShop(world, {touch = false})
    showMenu(world) shop.open("auras") ModalCompact.enforce()
    for _, card in cardsOf(world, "AuraCard_") do
        local art = childNamed(card, "ArtBox")
        check(art ~= nil and childNamed(art, "Rays") == nil, card.Name .. ": no texture uploaded, no rays (nothing is drawn in code)")
        check(card:FindFirstChild("EquippedGlow") == nil, card.Name .. ": no glowPlate uploaded, no glow image")
    end
    EffectsReal.Requested.shaftGradient.id, EffectsReal.Requested.glowPlate.id = shaft, glowReq
    world.gui:Destroy()
end

-- ===== 4. a locked Legendary is a question mark =====
do
    local world = buildWorld(1156, 793, false)
    toybox(true) bind(true)
    local Cards = requireModule(ClientFolder.ShopCards)
    local function ui() return {label = uiLabel, box = uiBox, button = uiButton, art = uiArt} end
    local function trailOf(rarity, locked)
        for _, t in ProgressionReal.Trails do if t.rarity == rarity and (t.level > 1) == locked then return t end end
        return nil
    end
    local lockedLegendary = {id = "secret", name = "Secret Trail", rarity = "Legendary", price = 900, level = 30, speed = 1.2, color = {255, 200, 60}, accent = {255, 255, 255}}
    local card, data = Cards.build(ui(), world.body, {kind = "trail", item = lockedLegendary, owned = false, equipped = false, level = 1, x = 0, y = 0, height = 270, buyY = 216, targetHeight = 44, scale = 1, onPress = function() end, onInfo = function() end})
    check(data.button.tone == "locked", "the test item is locked (" .. data.button.tone .. ")")
    local art = childNamed(card, "ArtBox")
    local mark = art and childNamed(art, "Mystery")
    check(mark ~= nil and mark.Text == "?", "a locked Legendary shows a question mark")
    local hint = art and childNamed(art, "BenefitBand") and childNamed(childNamed(art, "BenefitBand"), "Hint")
    check(hint ~= nil and hint.Text == "Reach level 30", "and a short hint (" .. tostring(hint and hint.Text) .. ")")
    check(art ~= nil and childNamed(childNamed(art, "BenefitBand"), "Benefit") == nil and childNamed(art, "TrailIcon") == nil and childNamed(art, "DinoSilhouette") == nil, "no benefit words and no picture on the secret card")
    local image, slot = toyboxPicture(card)
    check(slot == "toybox_card_legendary" and image ~= nil, "the secret card still wears the Legendary card")
    check(childNamed(card, "Action").Text == "LEVEL 30", "and its button says what is needed")
    -- the same item once it is bought shows its picture again
    local owned = Cards.build(ui(), world.body, {kind = "trail", item = lockedLegendary, owned = true, equipped = false, level = 1, x = 300, y = 0, height = 270, buyY = 216, targetHeight = 44, scale = 1, onPress = function() end, onInfo = function() end})
    check(childNamed(childNamed(owned, "ArtBox"), "Mystery") == nil, "an owned Legendary shows its picture")
    local plainLocked = trailOf("Rare", true) or trailOf("Uncommon", true)
    if plainLocked then
        local c2 = Cards.build(ui(), world.body, {kind = "trail", item = plainLocked, owned = false, equipped = false, level = 1, x = 600, y = 0, height = 270, buyY = 216, targetHeight = 44, scale = 1, onPress = function() end, onInfo = function() end})
        check(childNamed(childNamed(c2, "ArtBox"), "Mystery") == nil, "a locked card of a lower tier shows its picture, not a question mark")
    end
    world.gui:Destroy()
end

-- ===== 5. behaviour: the confirm popup =====
for _, size in {{1156, 793}, {516, 481}} do
    local world = buildWorld(size[1], size[2], false)
    toybox(true) bind(true)
    local shop = mountShop(world, {touch = false, level = 1})
    showMenu(world) shop.open("auras") ModalCompact.enforce()
    local tag = string.format("Popup %dx%d", size[1], size[2])
    local target = nil
    for _, c in cardsOf(world, "AuraCard_") do if c.Name ~= "AuraCard_meadow" and target == nil then target = c end end
    check(target ~= nil, tag .. ": an aura the player does not own")
    if target then
        local id = string.sub(target.Name, #"AuraCard_" + 1)
        local item = itemOf(ProgressionReal.Auras, id)
        fired = {}
        childNamed(target, "Action").Activated:Fire()
        check(shop.name == "auraConfirm" and #fired == 0, tag .. ": a tap on the price opens the confirm page and sends nothing (" .. shop.name .. ", " .. #fired .. " sent)")
        check(world.heading.Text == "Buy " .. item.name .. "?", tag .. ": the title is 'Buy " .. item.name .. "?' (" .. tostring(world.heading.Text) .. ")")
        local price = false
        for _, d in world.body:GetChildren() do
            if d:IsA("TextLabel") and string.find(d.Text, item.price .. " Crystals", 1, true) then price = true end
        end
        check(price, tag .. ": the price is on the page")
        local buy, notNow, cancel = nil, nil, false
        for _, d in world.body:GetChildren() do
            if d:IsA("TextButton") and d.Text == "BUY AURA" then buy = d end
            if d:IsA("TextButton") and d.Text == "NOT NOW" then notNow = d end
            if d:IsA("TextButton") and d.Text == "CANCEL" then cancel = true end
        end
        check(buy ~= nil and notNow ~= nil and not cancel, tag .. ": BUY AURA and NOT NOW, no CANCEL")
        if notNow then
            check(rectOf(notNow).h >= 43.5, string.format("%s: NOT NOW is %d px high on screen (needs 44)", tag, rectOf(notNow).h + .5))
            notNow.Activated:Fire()
            check(shop.name == "auras" and #fired == 0, tag .. ": NOT NOW returns to the shop and sends nothing (" .. shop.name .. ", " .. #fired .. " sent)")
        end
        shop.open("auraConfirm")
        shop.open("auras") ModalCompact.enforce()
        for _, c in cardsOf(world, "AuraCard_") do if c.Name == target.Name then target = c end end
        childNamed(target, "Action").Activated:Fire()
        for _, d in world.body:GetChildren() do if d:IsA("TextButton") and d.Text == "BUY AURA" then buy = d end end
        fired = {}
        if buy then buy.Activated:Fire() end
        check(#fired == 1 and fired[1].action == "buyAura" and fired[1].id == id, tag .. ": BUY sends exactly one buyAura (" .. #fired .. ")")
    end
    world.gui:Destroy()
end
toybox(false) bind(false)

if failures > 0 then
    print(string.format("Toybox shop smoke FAILED: %d problem(s)", failures))
    error("toybox shop smoke failed")
end
print(string.format("Toybox shop smoke passed: %d sizes x 2 inputs x 2 pages, buttons seen: %d price, %d unequip, %d locked, %d tier pictures; a locked Legendary is a question mark; Buy X? / NOT NOW", #SIZES, seen.buy, seen.unequip, seen.locked, tierCount))
