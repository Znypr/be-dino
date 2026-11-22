--!strict
-- BD-1299 (owner 2026-11-23 "Rebuild both now", target docs/evidence/2026-11-23-index-proposal/proposal.jpg): with Config.IndexZonesEnabled
-- (and MenusSaeFrameEnabled) the kit DINO INDEX shows one ZONE at a time, as on the owner's proposed picture: the cyan "Dino Index" header
-- (title about 18 % bigger), the zone's illustrated panel on the left with its name on top, the zone's species as 4 x 2 near-square kit
-- cards COLOURED BY RARITY (a found dino in colour with its name under it, a dino not found yet a charcoal #202127 silhouette with "???"),
-- the zone bar "4/8" under the grid, the blue footer with the Index icon and "Found: n/22", and on the right the selected dino on a charcoal
-- #55555B panel (big, name + rarity under it, "You have N", the View button) with the dark rewards box under it ("Rewards:", the crystal
-- and +N, the yellow CLAIM! button when a zone reward is ready, else the next goal or "Got it!"). The zone buttons (Meadow / Forest / Beach /
-- Volcano in their colours) are stacked OUTSIDE the window on the right; Patterns / Colours / Fusion stay reachable as small icons in a
-- column right of them (LEAD decision 2026-11-23, like the picture's icon column). Kept from BD-1296: the 4 px cyan selected-card outline,
-- "You have N", View, the page arrows (only when a zone has more than 8 cards: found secret dinos join their zone after its species).
-- Numbers: Shared/SaeMenuRules.indexZonesLayout; zones and rewards: Shared/IndexZones; the claim goes to the server (IndexZoneAction), which
-- decides and pays exactly once. Code only places, slices, tints and tiles uploaded pictures (docs/72).
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Slots = require(Shared.AssetSlots)
local Kit2 = require(Shared.ShopKit2)
local ShopArt = require(Shared.ShopArt)
local Menu = require(Shared.SaeMenuRules)
local FrameRules = require(Shared.SaeFrameRules)
local Preview = require(Shared.DinosaurPreview)
local Secret = require(Shared.SecretSpeciesConfig)
local Zones = require(Shared.IndexZones)
local Art = require(script.Parent.KitArt)
local KitWindow = require(script.Parent.KitWindow)
local KitButton = require(script.Parent.KitButton)
local IndexTabs = require(script.Parent.IndexTabs)
local PrivateState = require(script.Parent.PrivateState)

local M = {}

local CHARCOAL = Color3.fromRGB(32, 33, 39) -- silhouettes #202127
local PANEL = Color3.fromRGB(110, 110, 118) -- the charcoal panel #55555B: the light kit card (about 0.66 grey) tinted down
local TRACK = Color3.fromRGB(150, 152, 165)
local SELECTED = Color3.fromRGB(92, 214, 245) -- the selected card edge (BD-1296)
local FOOTER = Color3.fromRGB(150, 200, 255) -- the cyan kit card tinted to the picture's sky blue footer
local state = {spec = nil :: any, body = nil :: GuiObject?, zone = nil :: string?, page = 1, busy = false, paid = {} :: {[string]: boolean}, hooked = false}

-- The zone buttons and the placeholder panel: the kit card piece of the zone tinted to the zone colour (Meadow is the lime card itself).
local ZoneLook: {[string]: {slot: string, tint: Color3}} = {
    meadow = {slot = "shopkit2_card_uncommon", tint = Color3.new(1, 1, 1)},
    forest = {slot = "shopkit2_card_uncommon", tint = Color3.fromRGB(97, 150, 255)},
    beach = {slot = "shopkit2_card_common", tint = Color3.fromRGB(255, 232, 170)},
    volcano = {slot = "shopkit2_card_mythic", tint = Color3.fromRGB(242, 230, 77)},
}

local function rarityWord(index: number): string return Config.SpeciesRarityNames[index] or "Common" end

local function studded(parent: Instance, name: string, slot: string, x: number, y: number, w: number, h: number, z: number, outline: number, tint: Color3?): Frame?
    local d = Kit2.Studded[slot]
    if not d then return nil end
    local k = math.min(w / d.w, h / d.h) * 1.6
    local piece = Art.studded(parent, name, slot, x, y, w, h, z, k * outline, k)
    if piece and tint then
        for _, img in piece:GetDescendants() do if img:IsA("ImageLabel") then img.ImageColor3 = tint end end
    end
    return piece
end

local function card(parent: Instance, name: string, rarity: string, x: number, y: number, w: number, h: number, z: number, tint: Color3?): Frame
    local slot = Kit2.cardSlot(rarity)
    local holder = Art.box(parent, name, x, y, w, h, z)
    local d = Kit2.Studded[slot]
    local studK = w / d.w
    local face = Art.studded(holder, "Face", slot, 0, 0, w, h, z, studK * 0.9, studK)
    if face and tint then for _, img in face:GetDescendants() do if img:IsA("ImageLabel") then img.ImageColor3 = tint end end end
    if not face then Art.kit(holder, "Face", "toybox_card_" .. string.lower(rarity), 0, 0, w, h, z) end
    return holder
end

local function stored(): any
    local ok, list = pcall(function() return HttpService:JSONDecode(PrivateState.str("IndexZonesJson", "[]")) end)
    local out = if ok and typeof(list) == "table" then table.clone(list) else {}
    for key in state.paid do table.insert(out, key) end -- answered "applied" by the server; the private value follows a moment later
    return out
end

-- The cards of a zone: its species, then the secret dinos of that zone the player has found (never counted for the rewards).
local function zoneCards(zone: any, found: (string) -> boolean): {string}
    local out = table.clone(zone.species)
    if Config.SecretSpeciesEnabled == true then
        for _, id in Secret.Order do
            local row = Secret.Species[id]
            if row and Zones.secretZone(row.class) == zone.id and found(id) then table.insert(out, id) end
        end
    end
    return out
end

-- body: the Bootstrap panel body; d: the DinoIndexKit table (hero, copies, bestMutation, eventMutation, ownedTraits, speciesIndex, selected,
-- select, openDetail, openFusion, notify, open, close). Returns false when the kit window does not draw this page.
function M.build(body: GuiObject, d: any): boolean
    if Config.PatternColourIndexEnabled == true and IndexTabs.lastTab() ~= "dinos" then return false end
    local function isFound(id: string): boolean
        local base, gold, diamond = d.copies(id)
        return base + gold + diamond > 0 or d.eventMutation(id) ~= nil or d.ownedTraits(id) ~= nil
    end
    local function count(id: string): number
        local base, gold, diamond = d.copies(id)
        return math.max(if isFound(id) then 1 else 0, base + gold + diamond)
    end
    if state.zone == nil then
        local z = Zones.zoneOf(d.selected())
        state.zone = if z then z.id else Zones.Zones[1].id
    end
    local spec: any
    -- redraw only while this window is still open (the marker KitWindow leaves in the body); a closed window is never drawn again
    local function refresh()
        local s, b = state.spec, state.body
        if s and s.refresh and b and b:FindFirstChild("KitWindowMark") then s.refresh() end
    end
    if not state.hooked then
        state.hooked = true
        PrivateState.onChanged("IndexZonesJson", refresh)
    end
    local function claim(zoneId: string, step: string)
        if state.busy then return end
        local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
        local remote = folder and folder:FindFirstChild("IndexZoneAction")
        if not remote or not remote:IsA("RemoteFunction") then d.notify("Try again soon!") return end
        state.busy = true
        task.spawn(function()
            local ok, answer = pcall(function() return (remote :: RemoteFunction):InvokeServer({action = "claim", zone = zoneId, step = step}) end)
            state.busy = false
            if ok and typeof(answer) == "table" and answer.ok == true then
                state.paid[Zones.key(zoneId, step)] = true
                if answer.status == "applied" then d.notify(Zones.toast(answer.crystals)) end
            else
                d.notify(if ok and typeof(answer) == "table" and answer.status == "full" then "Your crystal bag is full!" else "Try again soon!")
            end
            refresh()
        end)
    end
    local icons = {"patterns", "colours", "fusion"}
    if Config.PatternColourIndexEnabled ~= true then icons = {"fusion"} end
    spec = {
        title = Menu.IndexTitle, colour = Menu.IndexColour, cards = {},
        layout = function(w: number, h: number, _: number, inset: number?) return Menu.indexZonesLayout(w, h, inset, #icons) end,
        onClose = function() if d.close then d.close() end end,
        content = function(window: Frame, lay: any, holder: Frame)
            local zone = Zones.zone(state.zone) or Zones.Zones[1]
            local list = zoneCards(zone, isFound)
            local pages = math.max(1, math.ceil(#list / Zones.PerPage))
            state.page = math.clamp(state.page, 1, pages)
            local selected = d.selected()
            if not table.find(list, selected) then selected = list[1] d.select(selected) end
            -- the zone panel (the illustrated picture, the zone name on top)
            local Zp = lay.zonePanel
            local look = ZoneLook[zone.id]
            local zp = Art.box(window, "ZonePanel", Zp.x, Zp.y, Zp.w, Zp.h, 34)
            studded(zp, "Frame", look.slot, 0, 0, Zp.w, Zp.h, 34, 0.9, look.tint)
            local edge = math.max(4, math.floor(Zp.w * 0.05))
            if zone.art ~= "" then
                local pic = Art.picture(zp, "ZoneArt", zone.art, edge, edge, Zp.w - 2 * edge, Zp.h - 2 * edge, 35)
                pic.ScaleType = Enum.ScaleType.Crop
                local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, 8), pic
            end -- else the PLACEHOLDER: the tinted kit card alone
            Art.words(zp, "ZoneName", zone.name, 0, edge + 2, Zp.w, Zp.text + 6, FrameRules.fitSize(zone.name, Zp.w - 8, Zp.text), 37)
            -- the cards
            local first = (state.page - 1) * Zones.PerPage + 1
            for slot = 1, Zones.PerPage do
                local id = list[first + slot - 1]
                local r = lay.cards[slot]
                if not id or not r then break end
                local secret = Secret.Species[id] ~= nil
                local found = isFound(id)
                local on = id == selected
                local x, y, w, h = r.x, r.y, r.w, r.h
                if on then x, y, w, h = x - 3, y - 3, w + 6, h + 6 end
                local rarity = if secret then "mythic" else rarityWord(d.speciesIndex(id))
                local c = card(window, "IndexCard_" .. id, rarity, x, y, w, h, if on then 36 else 34)
                if on then
                    local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = SELECTED, 4, c
                    local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, 8), c
                end
                local nameH = lay.cardName + 4
                local render = math.max(30, math.min(w - 8, h - nameH - 6))
                local rx, ry = math.floor((w - render) / 2), math.max(3, math.floor((h - nameH - render) / 2) + 2)
                local zoom = math.floor(render * (if found then Menu.CardZoom else Menu.SilhouetteZoom))
                rx, ry, render = rx - zoom, ry - zoom, render + 2 * zoom
                if found then
                    d.hero(c, id, rx, ry, render, render, d.bestMutation(id)).ZIndex = c.ZIndex + 2
                else
                    local view = Preview.add(c, id, "silhouette", CHARCOAL)
                    view.Position, view.Size, view.ZIndex = UDim2.fromOffset(rx, ry), UDim2.fromOffset(render, render), c.ZIndex + 2
                end
                local name = if found then (Config.SpeciesDisplayNames[id] or Secret.name(id)) else Menu.SecretMark
                if found and FrameRules.textWidth(name, Menu.MinText) > w - 10 and Zones.CardNames[id] then name = Zones.CardNames[id] end
                Art.words(c, "Name", name, 2, h - nameH - 3, w - 4, nameH, FrameRules.fitSize(name, w - 10, lay.cardName), c.ZIndex + 3)
                Art.tap(c, "Tap", 0, 0, w, h, c.ZIndex + 5, function()
                    if id == d.selected() and found then d.openDetail() return end
                    d.select(id)
                    if spec.refresh then spec.refresh() end
                end)
            end
            -- the zone bar "4/8" (the kit strip, the lime kit piece as the fill)
            local zoneFound = 0
            for _, id in zone.species do if isFound(id) then zoneFound += 1 end end
            local B = lay.bar
            local pagesOn = pages > 1
            local bx, bw = B.x, B.w
            if pagesOn then bx, bw = B.x + lay.prev.w + 6, B.w - 2 * (lay.prev.w + 6) end
            local bk = B.h / Kit2.Studded[Kit2.StripSlot].h
            local bar = Art.studded(window, "ZoneBar", Kit2.StripSlot, bx, B.y, bw, B.h, 34, bk, bk) or Art.box(window, "ZoneBar", bx, B.y, bw, B.h, 34)
            for _, piece in bar:GetDescendants() do if piece:IsA("ImageLabel") then piece.ImageColor3 = TRACK end end
            local fill = math.floor(bw * zoneFound / #zone.species + 0.5)
            if zoneFound > 0 then fill = math.max(fill, B.minFill) end
            if fill >= 4 then
                local gk = B.h / Kit2.Studded[Kit2.buttonSlot(false)].h
                Art.studded(bar, "Fill", Kit2.buttonSlot(false), 0, 0, math.min(bw, fill), B.h, 35, gk * 0.6, gk)
            end
            Art.words(bar, "Progress", Zones.progress(zoneFound, zone), 0, -math.floor(B.h * 0.05), bw, B.h, B.text, 37)
            if pagesOn then
                local function pageButton(key: string, r: any, word: string, step: number)
                    KitButton.draw(window, key, r.x, r.y, r.w, r.h, 36, {word = word, grey = true, textSize = B.text, onPress = function()
                        state.page = (state.page - 1 + step) % pages + 1
                        if spec.refresh then spec.refresh() end
                    end})
                end
                pageButton("PagePrev", lay.prev, "<", -1)
                pageButton("PageNext", lay.next, ">", 1)
            end
            -- the footer: the Index icon and "Found: n/22" (all zones, the regular species)
            local all = 0
            for _, id in Config.SpeciesOrder do if isFound(id) then all += 1 end end
            local F = lay.footer
            local foot = card(window, "IndexFooter", "rare", F.x, F.y, F.w, F.h, 34, FOOTER)
            local bookId = ShopArt.validId((require(Shared.UIIconAssets) :: any).dinos)
            if bookId then Art.picture(window, "FooterIcon", bookId, F.x - math.floor(F.icon * 0.12), F.y + math.floor((F.h - F.icon) / 2), F.icon, F.icon, 37) end
            local foundWord = "Found: " .. tostring(all) .. "/" .. tostring(#Config.SpeciesOrder)
            Art.words(foot, "Found", foundWord, F.icon, -math.floor(F.h * 0.05), F.w - F.icon, F.h, F.text, 37)
            -- the selected dino (charcoal panel: big picture, name and rarity under it, "You have N", View)
            local P = lay.panel
            local sFound = isFound(selected)
            local sSecret = Secret.Species[selected] ~= nil
            local panel = Art.box(window, "IndexPanel", P.x, P.y, P.w, P.h, 34)
            studded(panel, "Face", "shopkit2_card_common", 0, 0, P.w, P.h, 34, 0.8, PANEL)
            local render = math.min(P.w - 2 * P.inset, P.render)
            local rx, ry = math.floor((P.w - render) / 2), P.edge + math.floor((P.render - render) / 2)
            local zoom = math.floor(render * (if sFound then Menu.PanelZoom else Menu.SilhouetteZoom))
            rx, ry, render = rx - zoom, ry - zoom, render + 2 * zoom
            if sFound then
                d.hero(panel, selected, rx, ry, render, render, d.bestMutation(selected)).ZIndex = 36
            else
                local view = Preview.add(panel, selected, "silhouette", CHARCOAL)
                view.Position, view.Size, view.ZIndex = UDim2.fromOffset(rx, ry), UDim2.fromOffset(render, render), 36
            end
            local nameY = P.edge + P.render + 2
            local name = if sFound then (Config.SpeciesDisplayNames[selected] or Secret.name(selected)) else Menu.SecretMark
            Art.words(panel, "Name", name, 4, nameY, P.w - 8, P.nameText + 2, FrameRules.fitSize(name, P.w - 12, P.nameText), 38)
            local word = if sSecret then Secret.RarityLabel else rarityWord(d.speciesIndex(selected))
            Art.words(panel, "Rarity", word, 4, nameY + P.nameText + 1, P.w - 8, P.wordText + 2, P.wordText, 38, Color3.fromRGB(215, 218, 230))
            local line = if sFound then "You have " .. tostring(count(selected)) else Menu.NotFoundWord
            Art.words(panel, "Have", line, 4, nameY + P.nameText + P.wordText + 4, P.w - 8, P.wordText + 2, FrameRules.fitSize(line, P.w - 12, P.wordText), 38)
            KitButton.draw(panel, "Look", P.edge + 2, P.edge + 2, P.buttonW, P.button, 39, { -- top left: the dinos face right
                word = if sFound then Menu.LookWord else Menu.HatchWord, grey = not sFound, textSize = P.buttonText - 2,
                onPress = function() if sFound then d.openDetail() else d.notify("Hatch eggs to find this dino") end end,
            })
            -- the rewards box
            local R = lay.rewards
            local box = Art.box(window, "Rewards", R.x, R.y, R.w, R.h, 34)
            local rk = R.h / Kit2.Studded[Kit2.StripSlot].h
            Art.studded(box, "Face", Kit2.StripSlot, 0, 0, R.w, R.h, 34, math.min(rk, 0.6), math.min(rk, 0.6))
            local outline = Instance.new("UIStroke") outline.Color, outline.Thickness, outline.Parent = Color3.fromRGB(114, 242, 57), 2, box
            local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, 8), box
            local rewardsWord = Art.words(box, "Title", Zones.RewardsWord, R.inset, if R.oneLine then R.pad + math.floor((R.row - R.text) / 2) else R.pad, R.w - 2 * R.inset, R.text + 2, R.text, 36)
            rewardsWord.TextXAlignment = Enum.TextXAlignment.Left
            local step, status = Zones.current(zone, zoneFound, stored())
            local rowY = if R.oneLine then R.pad else R.pad + R.text + 2
            local gem = ShopArt.validId((require(Shared.UIIconAssets) :: any).amber)
            local amount = "+" .. tostring(Zones.Crystals[step])
            -- one line (a short screen): "Rewards:" at the left, a smaller crystal and number at the right
            local gemSize = if R.oneLine then R.text + 6 else R.row
            local amountSize = if R.oneLine then R.text + 2 else R.row - 8
            local amountW = FrameRules.textWidth(amount, amountSize)
            local gemY = rowY + math.floor((R.row - gemSize) / 2)
            local left = if R.oneLine then R.w - R.inset + 2 - (gemSize + 2 + amountW) else math.max(R.inset, math.floor((R.w - (R.row + 4 + amountW)) / 2))
            if gem then Art.picture(box, "Gem", gem, left, gemY, gemSize, gemSize, 36) end
            local amountLabel = Art.words(box, "Amount", amount, left + gemSize + 2, rowY, amountW + 10, R.row, amountSize, 36)
            amountLabel.TextXAlignment = Enum.TextXAlignment.Left
            local by = R.h - R.pad - R.button
            if status == "ready" then
                -- the yellow CLAIM! button (#FFE825): the yellow kit card piece (Legendary) at button size
                local btn = Art.box(box, "Claim", R.inset, by, R.w - 2 * R.inset, R.button, 36)
                studded(btn, "Face", "shopkit2_card_legendary", 0, 0, R.w - 2 * R.inset, R.button, 36, 0.9)
                Art.words(btn, "Word", if state.busy then "..." else Zones.ClaimWord, 0, -math.floor(R.button * 0.06), R.w - 2 * R.inset, R.button,
                    FrameRules.fitSize(Zones.ClaimWord, R.w - 2 * R.inset - 12, R.buttonText), 38)
                Art.tap(btn, "Tap", 0, 0, R.w - 2 * R.inset, R.button, 40, function() claim(zone.id, step) end)
            else
                local word = if status == "claimed" then Zones.GotWord else Zones.goal(zone, step, zoneFound)
                KitButton.draw(box, "Goal", R.inset, by, R.w - 2 * R.inset, R.button, 36, {word = word, grey = true, textSize = R.buttonText - 4})
            end
            -- the zone buttons outside the window, the Patterns / Colours / Fusion icons beside them
            for i, z in Zones.Zones do
                local r = lay.zones[i]
                if not r then break end
                local on = z.id == zone.id
                local zl = ZoneLook[z.id]
                local x, y, w, h = r.x, r.y, r.w, r.h
                if on then x, y, w, h = x - 4, y - 3, w + 8, h + 6 end
                local btn = Art.box(holder, "ZoneButton_" .. z.id, x, y, w, h, if on then 33 else 32)
                studded(btn, "Face", zl.slot, 0, 0, w, h, btn.ZIndex, 0.9, zl.tint)
                if on then
                    local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = Color3.new(1, 1, 1), 3, btn
                    local corner = Instance.new("UICorner") corner.CornerRadius, corner.Parent = UDim.new(0, 8), btn
                end
                Art.words(btn, "Word", z.name, 0, -math.floor(h * 0.05), w, h, FrameRules.fitSize(z.name, w - 12, lay.zoneText), btn.ZIndex + 2)
                Art.tap(btn, "Tap", 0, 0, w, h, btn.ZIndex + 4, function()
                    if state.zone == z.id then return end
                    state.zone, state.page = z.id, 1
                    d.select(z.species[1])
                    if spec.refresh then spec.refresh() end
                end)
            end
            for i, tab in icons do
                local s = lay.icons[i]
                if not s then break end
                local id = if tab == "fusion" then ShopArt.validId((require(Shared.UIIconAssets) :: any).fusion) else Slots.image("index_tab_" .. tab)
                if id then Art.picture(holder, "ZoneIcon_" .. tab, id, s.x + math.floor((s.w - lay.icon) / 2), s.y, lay.icon, lay.icon, 32) end
                if lay.iconText > 0 then Art.words(holder, "ZoneIconWord_" .. tab, Menu.ZoneRailWords[tab], s.x - 6, s.y + lay.icon, s.w + 12, lay.iconText + 2, lay.iconText, 32) end
                Art.tap(holder, "ZoneIconTap_" .. tab, s.x, s.y, s.w, s.h, 34, function()
                    if tab == "fusion" then d.openFusion() else IndexTabs.choose(tab) d.open("collection") end
                end)
            end
        end,
    }
    state.spec, state.body = spec, body
    return KitWindow.open(body, spec)
end

return M
