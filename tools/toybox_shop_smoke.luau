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
    local L = Rules.layout(194, 330, 48, 1)
    check(L.name.y < L.pill.y and L.pill.y + L.pill.h <= L.art.y and L.art.y + L.art.h <= L.band.y and L.band.y + L.band.h <= L.button.y and L.button.y + L.button.h <= 330,
        "layout: name, pill, art box, band and button stack in order inside the card")
    check(L.button.w == 194 - 2 * Rules.Page.insetX and L.art.w == L.button.w and L.band.w == L.button.w, "layout: art box, band and button are one width")
    check(Rules.cardMin(48, 1) >= 48 + Rules.Page.minArt and Rules.layout(194, Rules.cardMin(48, 1), 48, 1).art.h >= Rules.Page.minArt, "layout: the least card height keeps room for the art")
    check(Rules.columns(824, 1) == 4 and Rules.columns(836, 0.78) == 3 and Rules.columns(836, 0.6) == 3 and Rules.columns(1250, 1) == 4, "columns: 4 when a cell is 170 px on screen, else 3")
    for _, spec in {{824, 1, 12}, {836, 0.78, 12}, {1250, 1, 7}} do
        local g = Rules.grid(spec[1], 320, spec[2], spec[3], 48)
        local last = g.cells[math.min(g.columns, spec[3])]
        check(spec[1] - 8 - (last.x + last.w) <= 16 and g.cells[1].x <= Rules.Page.pad + 2, string.format("grid %d wide: the cards fill the width (right gap %d)", spec[1], spec[1] - 8 - (last.x + last.w)))
        check(g.cells[2] == nil or g.cells[2].x - (g.cells[1].x + g.cells[1].w) == 12 or g.cells[2].y > g.cells[1].y, "grid: 12 px gaps")
        check(g.cellW * g.columns + 12 * (g.columns - 1) <= spec[1] - 8, "grid: the row fits beside the scroll bar")
    end
    check(Rules.grid(824, 320, 1, 3, 48).scrolls == false and Rules.grid(824, 320, 1, 12, 48).scrolls == true, "grid: one row does not scroll, more rows do")
    check(Rules.tabTitle("auras") == "Auras" and Rules.tabTitle("crystals") == "Crystals" and Rules.styling("Compy") == "Styling: Compy" and Rules.styling(nil) == "Styling: your dino", "tab and styling words")
    check(Rules.walletText(12450) == "12,450" and Rules.walletText(0) == "0" and Rules.walletText(999) == "999" and Rules.walletText(1000000) == "1,000,000" and Rules.walletText(nil) == "0" and Rules.walletText(-5) == "0", "the wallet number has commas")
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
    local function scan(parent)
        for _, d in parent:GetChildren() do
            if d:IsA("GuiObject") and d.Visible and string.find(d.Name, prefix, 1, true) == 1 then table.insert(out, d) end
        end
    end
    scan(world.body)
    local grid = world.body:FindFirstChild("ShopGrid")
    if grid then scan(grid) end
    table.sort(out, function(a, b)
        if math.abs(a.Position.Y.Offset - b.Position.Y.Offset) > 1 then return a.Position.Y.Offset < b.Position.Y.Offset end
        return a.Position.X.Offset < b.Position.X.Offset
    end)
    return out
end
local function childNamed(parent, name) return parent:FindFirstChild(name) end
local function hasChip(card)
    for _, d in card:GetChildren() do if string.find(d.Name, "Chip_", 1, true) == 1 or d.Name == "TierBadge" then return true end end
    return false
end
local function itemOf(list, id) for _, it in list do if it.id == id then return it end end return nil end
local function openTrails(world) for _, d in world.body:GetChildren() do if d:IsA("TextButton") and string.upper(d.Text) == "TRAILS" and (d.Name == "ShopTab_trails" or d.Size.X.Offset == 155) then d.Activated:Fire() break end end end
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
local seen = {buy = 0, unequip = 0, locked = 0, tiers = {}, columns = {}}
local EXTRA_SIZES = {{1280, 720}, {1274, 481}, {1920, 1080}}
local ALL_SIZES = {}
for _, s in SIZES do table.insert(ALL_SIZES, s) end
for _, s in EXTRA_SIZES do table.insert(ALL_SIZES, s) end
local function sameColour(a, b) return math.abs(a.R - b.R) < 0.004 and math.abs(a.G - b.G) < 0.004 and math.abs(a.B - b.B) < 0.004 end
local function numberOf(text) return tonumber((string.gsub(text, ",", ""))) end
for _, touch in {false, true} do
    for _, size in ALL_SIZES do
        local w, h = size[1], size[2]
        for _, page in {"auras", "trails"} do
            local world = buildWorld(w, h, touch)
            toybox(true) bind(true)
            local shop = mountShop(world, {touch = touch, level = 1})
            showMenu(world) shop.open("auras")
            if page == "trails" then openTrails(world) end
            ModalCompact.enforce()
            local tag = string.format("Toybox %s %dx%d%s", page, w, h, if touch then " touch" else "")
            local isTrail = page == "trails"
            local bodyW, k = Rules.usableWidth(ModalCompact.bodyWidth(), ModalCompact.model().mode == "compact"), ModalCompact.bodyScale()
            local vis = visibleBox(world)
            -- header: the crystal wallet pill (icon + number), left of the X
            local pill = world.header:FindFirstChild("WalletPill")
            check(pill ~= nil, tag .. ": the crystal wallet pill is in the header")
            if pill then
                local number = childNamed(pill, "WalletNumber")
                check(number ~= nil and number.Text == Rules.walletText(1000000) and numberOf(number.Text) == 1000000, tag .. ": the wallet shows the crystals with commas (" .. tostring(number and number.Text) .. ")")
                check(world.heading.Text == "Crystal Shop", tag .. ": the title is Crystal Shop (" .. tostring(world.heading.Text) .. ")")
                local close = world.x
                if close then check(not overlaps(rectOf(pill), rectOf(close)), tag .. ": the wallet pill does not touch the X") end
            end
            -- tab chips: one per tab, the selected one amber, cream otherwise; the Styling chip on the right
            local chipsSeen = 0
            for _, d in world.body:GetChildren() do
                if d:IsA("TextButton") and string.find(d.Name, "ShopTab_", 1, true) == 1 then
                    chipsSeen += 1
                    local id = string.sub(d.Name, #"ShopTab_" + 1)
                    local selected = (id == page)
                    check(d.Text == Rules.tabTitle(id), tag .. ": tab text " .. d.Text)
                    check(sameColour(d.BackgroundColor3, Color3.fromRGB(255, 215, 106)) == selected, tag .. ": only the selected tab is amber (" .. id .. ")")
                    local word = childNamed(d, "ChipWord")
                    check(word ~= nil and word.Text == d.Text and sameColour(word.TextColor3, Color3.fromRGB(KitReal.Tone.value[1], KitReal.Tone.value[2], KitReal.Tone.value[3])) and word.TextStrokeTransparency == 1, tag .. ": tab " .. id .. " is dark ink without an outline")
                    check(word ~= nil and pxOf(word) >= 13.5, tag .. ": the tab word is at least 14 px")
                    check(pxOf(d) >= 13.5 and rectOf(d).h >= 43.5, string.format("%s: tab %s is %.1f px text, %d px high", tag, id, pxOf(d), rectOf(d).h + .5))
                end
            end
            check(chipsSeen == 4, tag .. ": four tab chips (" .. chipsSeen .. ")")
            local styling = childNamed(world.body, "StylingChip")
            check(styling ~= nil and string.find(styling.Text, "Styling: ", 1, true) == 1, tag .. ": the Styling chip")
            if styling then
                check(inside(rectOf(styling), rectOf(world.body), 1.5) or inside(rectOf(styling), vis, 1.5), tag .. ": the Styling chip is inside the body")
                shop.name = "auras"
                styling.Activated:Fire()
                check(shop.name == "collection", tag .. ": the Styling chip opens Dinos (" .. shop.name .. ")")
                world.body:ClearAllChildren() shop.open("auras") if page == "trails" then openTrails(world) end ModalCompact.enforce()
            end
            check(childNamed(world.body, "BuyEggComingSoon") == nil, tag .. ": the cards are on the page")
            -- the grid fills the body width
            local gridFrame = childNamed(world.body, "ShopGrid")
            check(gridFrame ~= nil, tag .. ": the card grid")
            if gridFrame == nil then world.gui:Destroy() continue end
            local gr = rectOf(gridFrame)
            local k2 = gr.w / bodyW
            check(math.abs(gr.w / k - bodyW) < 2 or math.abs(k2 * bodyW - gr.w) < 1, tag .. ": the grid is as wide as the body")
            check(inside(gr, vis, 2), tag .. ": the grid is inside the body (" .. describe(gr) .. " in " .. describe(vis) .. ")")
            local cards = cardsOf(world, if isTrail then "TrailCard_" else "AuraCard_")
            local count = #(if isTrail then ProgressionReal.Trails else ProgressionReal.Auras)
            check(#cards == count, tag .. ": every item has a card (" .. #cards .. " of " .. count .. ")")
            local want = math.min(Rules.columns(bodyW, k), count)
            seen.columns[want] = true
            if w == 1280 and h == 720 and isTrail then check(want == 4, tag .. ": 4 columns at 1280x720 (" .. want .. ")") end
            if w == 667 and h == 375 and isTrail then check(want == 3, tag .. ": 3 columns at 667x375 (" .. want .. ")") end
            local firstRowRight, firstRowLeft, firstY, cellW = 0, math.huge, nil, nil
            for index, card in cards do
                local cr = rectOf(card)
                if index <= want then
                    firstY = firstY or cr.y
                    check(math.abs(cr.y - firstY) < 1.5, tag .. ": the first row is one row")
                    cellW = cellW or cr.w
                    check(math.abs(cr.w - cellW) < 1.5, tag .. ": equal cells (" .. cr.w .. " vs " .. cellW .. ")")
                    firstRowRight = math.max(firstRowRight, cr.x + cr.w)
                    firstRowLeft = math.min(firstRowLeft, cr.x)
                    if index > 1 then
                        local gap = (cr.x - (rectOf(cards[index - 1]).x + rectOf(cards[index - 1]).w)) / k2
                        check(math.abs(gap - 12) < 1.5, string.format("%s: 12 px gaps (%.1f)", tag, gap))
                    end
                end
            end
            check((gr.x + gr.w - firstRowRight) / k2 <= 16.5, string.format("%s: the cards fill the body (right edge %.1f px short)", tag, (gr.x + gr.w - firstRowRight) / k2))
            check((firstRowLeft - gr.x) / k2 <= 16.5, tag .. ": the cards start at the left edge")
            check(inside({x = cards[1].AbsolutePosition.X, y = cards[1].AbsolutePosition.Y, w = cards[1].AbsoluteSize.X, h = 1}, gr, 2), tag .. ": the first row is inside the grid")
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
                -- name, rarity pill, no Info button
                local name, word = childNamed(card, "Name"), childNamed(card, "RarityWord")
                local secret = isTrail and item.level > 1 and Rules.mystery(item.rarity, "locked")
                check(name ~= nil and name.Text == (if secret then Rules.MysteryName else item.name), ctag .. ": the name")
                check(childNamed(card, "Info") == nil, ctag .. ": no Info button (a tap on the art opens the details)")
                local expectWord, tierColour = RarityWordReal.get(item.rarity)
                check(word ~= nil and word.Text == expectWord and word.TextColor3 == tierColour and word.BackgroundTransparency == 0, ctag .. ": the rarity word in its tier colour on a cream pill")
                if word then check(pxOf(word) >= 13.5, string.format("%s: the rarity word is %.1f px on screen", ctag, pxOf(word))) end
                if name then check(pxOf(name) >= 13.5, string.format("%s: the name is %.1f px on screen", ctag, pxOf(name))) end
                -- the cream art box between the pill and the band
                local art, act, band = childNamed(card, "ArtBox"), childNamed(card, "Action"), childNamed(card, "BenefitBand")
                check(art ~= nil and act ~= nil and band ~= nil, ctag .. ": an art box, a benefit band and one Action button")
                if art == nil or act == nil or band == nil then continue end
                local ar, br, bandR = rectOf(art), rectOf(act), rectOf(band)
                check(inside(ar, cr, 1.5) and inside(bandR, cr, 1.5) and inside(br, cr, 1.5), ctag .. ": art box, band and button are inside the card")
                check(ar.y + ar.h <= bandR.y + .5 and bandR.y + bandR.h <= br.y + .5, ctag .. ": art box, then band, then button, none over another")
                if word and name then check(rectOf(name).y + rectOf(name).h <= rectOf(word).y + 1.5 and rectOf(word).y + rectOf(word).h <= ar.y + 1.5, ctag .. ": name, pill, art box in order") end
                check(ar.h >= 48 * k - 1, ctag .. ": the art box keeps room for a picture")
                check(art.ClipsDescendants == true and childNamed(art, "InfoTap") ~= nil, ctag .. ": the art box is clipped and taps open the details")
                if not isTrail then
                    local ring = childNamed(art, "AuraRing")
                    check(ring ~= nil and ring.Image == SlotsReal.Images["aura_" .. id] and ring.Image ~= "", ctag .. ": the art box shows the bound aura picture (the ring)")
                    if ring then check(inside(rectOf(ring), ar, 1.5), ctag .. ": the ring is inside the art box") end
                end
                -- rays: three, from the uploaded shaft texture
                local fan = childNamed(art, "Rays")
                check(fan ~= nil and #fan:GetChildren() == 3, ctag .. ": three slow rays behind the art")
                if fan then
                    for _, ray in fan:GetChildren() do check(ray.Image == EffectsReal.resolveUi("shaftGradient"), ctag .. ": a ray is the shaftGradient texture") end
                end
                -- the benefit band: dark text on cream
                local benefit = childNamed(band, if secret then "Hint" else "Benefit")
                local words = if secret then Rules.hint(item) else if isTrail then ShopPreviewReal.speedWords(item.speed) else (UIFormatReal.boost("Growth", item.growth) or "Growth")
                check(benefit ~= nil and benefit.Text == words, ctag .. ": the benefit band says '" .. words .. "' (" .. tostring(benefit and benefit.Text) .. ")")
                if benefit then
                    check(pxOf(benefit) >= 13.5, string.format("%s: the benefit is %.1f px on screen", ctag, pxOf(benefit)))
                    check(sameColour(benefit.TextColor3, Color3.fromRGB(KitReal.Tone.value[1], KitReal.Tone.value[2], KitReal.Tone.value[3])), ctag .. ": the benefit is dark ink on the cream band")
                end
                -- ONE wide button
                local buttons = 0
                for _, d in card:GetChildren() do if d:IsA("TextButton") then buttons += 1 end end
                check(buttons == 1, ctag .. ": exactly one action button on the card (" .. buttons .. ")")
                check(inside(br, cr, 1.5) and br.w >= cr.w - 36 * k2 - 1, string.format("%s: the button is %d px wide inside a %d px card", ctag, br.w + .5, cr.w + .5))
                check(pxOf(act) >= 13.5, string.format("%s: the button text is %.1f px on screen", ctag, pxOf(act)))
                local equipped = not isTrail and id == "meadow"
                local locked = isTrail and item.level > 1
                if equipped then
                    seen.unequip += 1
                    check(act.Text == "UNEQUIP" and act.BackgroundColor3 == Colors.card, ctag .. ": the equipped card says UNEQUIP on grey (" .. act.Text .. ")")
                    check(card:FindFirstChild("EquippedRing") ~= nil, ctag .. ": the equipped card has its gold ring")
                    local glow = card:FindFirstChild("EquippedGlow")
                    check(glow ~= nil and glow.Image == EffectsReal.resolveUi("glowPlate"), ctag .. ": the equipped card has the soft glow (glowPlate)")
                else
                    check(card:FindFirstChild("EquippedRing") == nil and card:FindFirstChild("EquippedGlow") == nil, ctag .. ": only the equipped card glows")
                end
                if not equipped and locked then
                    seen.locked += 1
                    check(act.Text == (if secret then Rules.LockedWord else "LEVEL " .. item.level) and act.BackgroundColor3 == ShopCardReal.SoldOutColor, ctag .. ": a locked trail says LEVEL n on a grey button (" .. act.Text .. ")")
                elseif not equipped then
                    seen.buy += 1
                    check(act.Text == UIFormatReal.number(item.price) and act.BackgroundColor3 == Colors.accent, ctag .. ": the number is on the green button (" .. act.Text .. ")")
                    -- icon and number are one group: the icon never overlaps the number, the group fits the button
                    local pad = act:FindFirstChild("IconPad")
                    local icon = act:FindFirstChild("CrystalIcon")
                    check(pad ~= nil, ctag .. ": the price group has its padding")
                    if pad and icon then
                        local padLeft, iconX, iconW = pad.PaddingLeft.Offset, icon.Position.X.Offset, icon.Size.X.Offset
                        check(padLeft + iconX >= 7.5, string.format("%s: the crystal icon starts %.1f px from the button edge", ctag, padLeft + iconX))
                        check(padLeft - (padLeft + iconX + iconW) >= 6, string.format("%s: icon and number are %.1f px apart (needs 6)", ctag, padLeft - (padLeft + iconX + iconW)))
                        local groupW = act:GetAttribute("PriceGroupW")
                        check(type(groupW) == "number" and groupW <= act.Size.X.Offset - 15, ctag .. ": the group fits the button")
                    end
                end
                for _, d in card:GetDescendants() do
                    if d:IsA("TextLabel") and string.find(d.Text, "Crystals", 1, true) then check(false, ctag .. ": a price caption is on the card ('" .. d.Text .. "')") end
                end
                for _, d in card:GetDescendants() do
                    if (d:IsA("TextLabel") or d:IsA("TextButton")) and d.Text ~= "" and d.Name ~= "Mystery" then
                        check(pxOf(d) >= 13.5, string.format("%s: '%s' is %.1f px on screen (needs 14)", ctag, d.Text, pxOf(d)))
                    end
                end
                check(childNamed(art, "Mystery") == nil or Rules.mystery(item.rarity, if equipped then "unequip" elseif locked then "locked" else "buy"), ctag .. ": the question mark only on a locked Legendary")
            end
            -- one coloured (green) button per card at most, the rest are grey: no blue or red anywhere on the cards
            for _, card in cards do
                local act = childNamed(card, "Action")
                if act then check(act.BackgroundColor3 == Colors.accent or act.BackgroundColor3 == Colors.card or act.BackgroundColor3 == ShopCardReal.SoldOutColor, card.Name .. ": the button is green or grey, never blue or red") end
            end
            -- nothing of the page lies below the visible body
            for _, d in world.body:GetChildren() do
                if d:IsA("GuiObject") and d.Visible and d.Name ~= "ShopWalletMark" then
                    local r = rectOf(d)
                    check(r.y + r.h <= vis.y + vis.h + 2, string.format("%s: %s lies below the body (%s)", tag, d.Name, describe(r)))
                end
            end
            world.gui:Destroy()
        end
    end
end
check(seen.buy > 0 and seen.unequip > 0 and seen.locked > 0, string.format("the sweep saw every button kind (buy %d, unequip %d, locked %d)", seen.buy, seen.unequip, seen.locked))
check(seen.columns[4] and seen.columns[3], "the sweep saw 4 and 3 columns")
local tierCount = 0
for _ in seen.tiers do tierCount += 1 end
check(tierCount >= 3, "the sweep saw at least three different tier pictures (" .. tierCount .. ")")

-- ===== the other tabs sit on a cream panel, in the same window =====
for _, size in {{1280, 720}, {667, 375}} do
    for _, tab in {"Eggs", "Crystals"} do
        local world = buildWorld(size[1], size[2], false)
        toybox(true) bind(true)
        local shop = mountShop(world, {touch = false})
        showMenu(world) shop.open("auras")
        for _, d in world.body:GetChildren() do if d:IsA("TextButton") and d.Text == tab then d.Activated:Fire() end end
        ModalCompact.enforce()
        local tag = string.format("Toybox %s tab %dx%d", tab, size[1], size[2])
        local panel = childNamed(world.body, "ShopPanel")
        check(panel ~= nil, tag .. ": the page sits on a cream panel")
        check(world.header:FindFirstChild("WalletPill") ~= nil, tag .. ": the wallet is in the header on every tab")
        check(childNamed(world.body, "ShopGrid") == nil, tag .. ": no card grid here")
        if panel then
            local pr, vis = rectOf(panel), visibleBox(world)
            check(inside(pr, vis, 2), tag .. ": the panel is inside the body (" .. describe(pr) .. " in " .. describe(vis) .. ")")
            check(pr.w / (pr.w / ModalCompact.bodyWidth()) >= ModalCompact.bodyWidth() - 1, tag .. ": the panel is as wide as the body")
        end
        world.gui:Destroy()
    end
end
-- leaving the shop page takes the wallet away
do
    local world = buildWorld(1280, 720, false)
    toybox(true) bind(true)
    local shop = mountShop(world, {touch = false})
    showMenu(world) shop.open("auras")
    check(world.header:FindFirstChild("WalletPill") ~= nil, "the wallet shows on the shop")
    world.body:ClearAllChildren()
    check(world.header:FindFirstChild("WalletPill") == nil, "the wallet goes when the body is cleared for another screen")
    world.gui:Destroy()
end

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
    local bandOf = childNamed(card, "BenefitBand")
    local hint = bandOf and childNamed(bandOf, "Hint")
    check(hint ~= nil and hint.Text == "Reach level 30", "and a short hint (" .. tostring(hint and hint.Text) .. ")")
    check(art ~= nil and bandOf ~= nil and childNamed(bandOf, "Benefit") == nil and childNamed(art, "TrailIcon") == nil and childNamed(art, "DinoSilhouette") == nil, "no benefit words and no picture on the secret card")
    local image, slot = toyboxPicture(card)
    check(slot == "toybox_card_legendary" and image ~= nil, "the secret card still wears the Legendary card")
    check(childNamed(card, "Action").Text == "LOCKED" and childNamed(card, "Action").BackgroundColor3 == ShopCardReal.SoldOutColor, "and its button says LOCKED on grey")
    check(childNamed(card, "Name").Text == "???", "and its name is hidden")
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
        check(childNamed(world.body, "ShopPanel") ~= nil, tag .. ": the popup sits on a cream panel")
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
