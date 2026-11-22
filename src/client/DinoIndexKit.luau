--!strict
-- BD-1296 (docs/246 slice 2): with Config.MenusSaeFrameEnabled the DINO INDEX (Dinos page) is the shop menu kit window (client/KitWindow):
-- one cyan title "Dino Index" with the red X, four columns x two rows of kit rarity cards (a found dino in full colour on its rarity card
-- with "x3" under it; a dino not found yet a dark silhouette on the grey card with "?"), the selected-dino panel on the right (about 28 %
-- of the window width: name, rarity word, a big preview, "You have 3", the green Look button that opens the dino page), and under the grid
-- the progress bar ("Found 5/22" on the kit strip, the green kit piece as the fill) with the grey page buttons. Dinos / Patterns / Colours
-- / Fusion sit outside the window on the right. Patterns and Colours keep their own pages (IndexTabs): a rail tap picks the tab and opens the
-- collection again, which this module then leaves to IndexTabs. Numbers: Shared/SaeMenuRules (indexLayout); art: the kit 2 pieces; the
-- dino pictures are the game's own previews (Bootstrap hero / DinosaurPreview silhouettes). Client presentation only: no remote here.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Config = require(Shared.Config)
local Slots = require(Shared.AssetSlots)
local Kit2 = require(Shared.ShopKit2)
local ShopArt = require(Shared.ShopArt)
local Menu = require(Shared.SaeMenuRules)
local FrameRules = require(Shared.SaeFrameRules)
local Preview = require(Shared.DinosaurPreview)
local FusionSelection = require(Shared.FusionSelection)
local Secret = require(Shared.SecretSpeciesConfig)
local TimerWords = require(Shared.TimerWords)
local Art = require(script.Parent.KitArt)
local KitWindow = require(script.Parent.KitWindow)
local KitButton = require(script.Parent.KitButton)
local IndexTabs = require(script.Parent.IndexTabs)

local M = {}

local state = {page = 1}
local CHARCOAL = Color3.fromRGB(32, 33, 39) -- lead polish 2026-11-23: silhouettes charcoal #202127, not pure black
local TRACK = Color3.fromRGB(150, 152, 165) -- lead polish round 2: the bar track darker than the window body (multiplies the kit strip)
local SELECTED = Color3.fromRGB(92, 214, 245) -- the selected card edge: the Index cyan #5CD6F5

local function rarityWord(index: number): string
    return Config.SpeciesRarityNames[index] or "Common"
end

-- A kit card face in `parent` (the kit 2 rarity card, else the Toybox one).
local function face(parent: Instance, rarity: string, w: number, h: number, z: number, outline: number)
    local slot = Kit2.cardSlot(rarity)
    local studK = w / Kit2.Studded[slot].w
    if not Art.studded(parent, "Face", slot, 0, 0, w, h, z, studK * outline, studK) then
        Art.kit(parent, "Face", "toybox_card_" .. string.lower(rarity), 0, 0, w, h, z)
    end
end

-- The rail tabs: Patterns and Colours only while their pages exist (Config.PatternColourIndexEnabled).
local function railTabs(): {string}
    local out = {}
    for _, tab in Menu.IndexRail do
        if (tab ~= "patterns" and tab ~= "colours") or Config.PatternColourIndexEnabled == true then table.insert(out, tab) end
    end
    return out
end

local function railIcon(tab: string): string?
    if tab == "dinos" or tab == "fusion" then return ShopArt.validId((require(Shared.UIIconAssets) :: any)[tab]) end
    return Slots.image("index_tab_" .. tab)
end

-- body: the Bootstrap panel body. d = {hero(parent, id, x, y, w, h, stage), copies(id) -> base, gold, diamond, bestMutation(id),
-- eventMutation(id), ownedTraits(id), speciesIndex(id), selected() -> id, select(id), openDetail(), openFusion(), notify(text), open(name),
-- close()}. Returns false when the kit window does not draw this page (another Index tab is chosen, or the kit frame is not bound).
function M.build(body: GuiObject, d: any): boolean
    if (Config :: any).IndexZonesEnabled == true then return require(script.Parent.DinoIndexZones).build(body, d) end -- BD-1299: the zones look
    if Config.PatternColourIndexEnabled == true and IndexTabs.lastTab() ~= "dinos" then return false end
    local order = Secret.indexOrder(Config.SpeciesOrder, Config.SecretSpeciesEnabled)
    local perPage = Menu.Index.cols * Menu.Index.rows
    local pages = math.max(1, math.ceil(#order / perPage))
    state.page = math.clamp(state.page, 1, pages)
    local function info(id: string, secret: boolean)
        local base, gold, diamond = d.copies(id)
        local found = base + gold + diamond > 0 or d.eventMutation(id) ~= nil or d.ownedTraits(id) ~= nil
        local look = if secret then Secret.indexCard(id, found) else FusionSelection.indexCard(found)
        return found, math.max(if found then 1 else 0, base + gold + diamond), look
    end
    local unlocked = 0
    for i, id in order do
        if i <= #Config.SpeciesOrder and info(id, false) then unlocked += 1 end
    end
    local tabs = railTabs()
    local words = {}
    for _, tab in tabs do table.insert(words, Menu.IndexRailWords[tab]) end
    local spec: any
    spec = {
        title = Menu.IndexTitle, colour = Menu.IndexColour, cards = {},
        layout = function(w: number, h: number, _: number, inset: number?) return Menu.indexLayout(w, h, inset, words) end,
        onClose = function() if d.close then d.close() end end,
        rail = {
            tabs = tabs, words = Menu.IndexRailWords, selected = "dinos", icon = railIcon,
            onTab = function(tab: string)
                if tab == "fusion" then d.openFusion()
                elseif tab == "patterns" or tab == "colours" then IndexTabs.choose(tab) d.open("collection") end
            end,
        },
        content = function(window: Frame, lay: any, _: Frame)
            local selected = d.selected()
            local first = (state.page - 1) * perPage + 1
            for slot = 1, perPage do
                local i = first + slot - 1
                local id = order[i]
                local r = lay.cards[slot]
                if not id or not r then break end
                local secret = i > #Config.SpeciesOrder
                local found, count, look = info(id, secret)
                local on = id == selected
                local x, y, w, h = r.x, r.y, r.w, r.h
                if on then x, y, w, h = x - 3, y - 3, w + 6, h + 6 end -- the selected card pops a little, with a 4 px cyan edge (the header colour)
                local card = Art.box(window, "IndexCard_" .. id, x, y, w, h, if on then 36 else 34)
                face(card, if found then rarityWord(d.speciesIndex(id)) else "Common", w, h, card.ZIndex, 0.9)
                if on then
                    local edge = Instance.new("UIStroke")
                    edge.Color, edge.Thickness, edge.Parent = SELECTED, 4, card
                    local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, 8), card
                end
                local render = lay.cardRender
                local ry = math.max(4, math.floor((h - (render + lay.countText + 2)) / 2))
                local rx = math.floor((w - render) / 2)
                local countY = ry + render - 2
                -- the preview camera leaves a wide margin round the model: its box is bigger than the render rect (same centre), so the dino
                -- itself fills the card (lead polish 2026-11-23: renders 35-50 % bigger, silhouettes 25-35 % bigger)
                local zoom = math.floor(render * (if found then Menu.CardZoom else Menu.SilhouetteZoom))
                rx, ry, render = rx - zoom, ry - zoom, render + 2 * zoom
                if found then
                    local view = d.hero(card, id, rx, ry, render, render, d.bestMutation(id))
                    view.ZIndex = card.ZIndex + 2
                elseif secret and not look.silhouette then
                    Art.words(card, "Mark", "?", rx, ry, render, render, 40, card.ZIndex + 2)
                else
                    local view = Preview.add(card, id, "silhouette", CHARCOAL)
                    view.Position, view.Size, view.ZIndex = UDim2.fromOffset(rx, ry), UDim2.fromOffset(render, render), card.ZIndex + 2
                end
                Art.words(card, "Count", if found then Menu.count(count) else "?", 0, countY, w, lay.countText + 4, lay.countText, card.ZIndex + 3)
                Art.tap(card, "Tap", 0, 0, w, h, card.ZIndex + 5, function()
                    if id == d.selected() and found then d.openDetail() return end
                    d.select(id)
                    if spec.refresh then spec.refresh() end
                end)
            end
            -- the selected-dino panel
            local P, pp = lay.panel, lay.panelParts
            local sid = selected
            local sIndex = table.find(order, sid) or 1
            local sFound, sCount, sLook = info(sid, sIndex > #Config.SpeciesOrder)
            local panel = Art.box(window, "IndexPanel", P.x, P.y, P.w, P.h, 34)
            local tier = rarityWord(d.speciesIndex(sid))
            face(panel, "Common", P.w, P.h, 34, 0.7) -- the light panel (lead polish: lighter, the rarity as a badge under the name)
            local name = sLook.nameText or Config.SpeciesDisplayNames[sid] or Secret.name(sid)
            Art.words(panel, "Name", name, 4, pp.edge, P.w - 8, pp.nameText + 2, FrameRules.fitSize(name, P.w - 12, pp.nameText), 38)
            local word = sLook.rarityText or tier
            local badgeW = math.min(P.w - 2 * pp.inset, FrameRules.textWidth(word, pp.wordText) + 24)
            local badge = Art.box(panel, "RarityBadge", math.floor((P.w - badgeW) / 2), pp.edge + pp.nameText + 2, badgeW, pp.badge, 37)
            face(badge, if sFound then tier else "Common", badgeW, pp.badge, 37, 0.5)
            Art.words(badge, "Rarity", word, 0, -1, badgeW, pp.badge, pp.wordText, 38)
            local buttonY = P.h - pp.edge - pp.button
            local lineY = buttonY - pp.gap - pp.line
            local render = math.min(pp.render, lineY - pp.gap - pp.renderTop)
            local rx, ry = math.floor((P.w - render) / 2), pp.renderTop + math.floor((lineY - pp.gap - pp.renderTop - render) / 2)
            local zoom = math.floor(render * (if sFound then Menu.PanelZoom else Menu.SilhouetteZoom))
            rx, ry, render = rx - zoom, ry - zoom, render + 2 * zoom
            if sFound then
                d.hero(panel, sid, rx, ry, render, render, d.bestMutation(sid)).ZIndex = 36
            elseif sIndex > #Config.SpeciesOrder and not sLook.silhouette then
                Art.words(panel, "Mark", "?", rx, ry, render, render, 56, 36)
            else
                local view = Preview.add(panel, sid, "silhouette", CHARCOAL)
                view.Position, view.Size, view.ZIndex = UDim2.fromOffset(rx, ry), UDim2.fromOffset(render, render), 36
            end
            local line = if sFound then "You have " .. tostring(sCount) else Menu.NotFoundWord
            local stripK = pp.line / Kit2.Studded[Kit2.StripSlot].h
            local strip = Art.studded(panel, "Line", Kit2.StripSlot, pp.inset, lineY, P.w - 2 * pp.inset, pp.line, 37, stripK, stripK)
            Art.words(strip or panel, "LineWords", line, if strip then 0 else pp.inset, if strip then -math.floor(pp.line * 0.05) else lineY,
                P.w - 2 * pp.inset, pp.line, FrameRules.fitSize(line, P.w - 2 * pp.inset - 14, pp.wordText), 38)
            KitButton.draw(panel, "Look", pp.inset, buttonY, P.w - 2 * pp.inset, pp.button, 37, {
                word = if sFound then Menu.LookWord else Menu.HatchWord, grey = not sFound, textSize = pp.buttonText,
                onPress = function() if sFound then d.openDetail() else d.notify("Hatch eggs to find this dino") end end,
            })
            -- the progress bar (the kit strip, the green kit piece as the fill) and the page buttons
            local B = lay.bar
            local bk = B.h / Kit2.Studded[Kit2.StripSlot].h
            local bar = Art.studded(window, "IndexBar", Kit2.StripSlot, B.x, B.y, B.w, B.h, 34, bk, bk) or Art.box(window, "IndexBar", B.x, B.y, B.w, B.h, 34)
            for _, piece in bar:GetDescendants() do if piece:IsA("ImageLabel") then piece.ImageColor3 = TRACK end end -- a darker track (the kit strip tinted down)
            local total = #Config.SpeciesOrder
            local fill = if total > 0 then math.floor(B.w * unlocked / total + 0.5) else 0 -- exact (1/22 = 4.5 %)
            -- lead polish round 2: never thinner than B.minFill (11 px at 720 p) once one dino is found, so a child sees it
            if unlocked > 0 then fill = math.max(fill, B.minFill) end
            if fill >= 4 then
                local gk = B.h / Kit2.Studded[Kit2.buttonSlot(false)].h
                -- a thin outline (0.6 of the piece's own) so the narrow fill shows mostly bright lime
                Art.studded(bar, "Fill", Kit2.buttonSlot(false), 0, 0, math.min(B.w, fill), B.h, 35, gk * 0.6, gk)
            end
            Art.words(bar, "Found", TimerWords.found(unlocked, total), 0, -math.floor(B.h * 0.05), B.w, B.h, B.text, 37)
            if pages > 1 then
                local function pageButton(key: string, r: any, word: string, step: number)
                    KitButton.draw(window, key, r.x, r.y, r.w, r.h, 36, {word = word, grey = true, textSize = pp.buttonText, onPress = function()
                        state.page = (state.page - 1 + step) % pages + 1
                        if spec.refresh then spec.refresh() end
                    end})
                end
                pageButton("PagePrev", lay.prev, "<", -1)
                pageButton("PageNext", lay.next, ">", 1)
            end
        end,
    }
    return KitWindow.open(body, spec)
end

return M
