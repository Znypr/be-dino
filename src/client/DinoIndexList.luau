--!strict
-- BD-1194 (docs/232, finding P-110029): the Dino Index list (the "collection" screen) on the Toybox layout rules. Required by DinoIndexScreens
-- ONLY while Config.ToyboxUIEnabled is on (flag off = the old list, this file is never loaded). The card grid fills the body width in equal
-- columns and scrolls; the bottom bar (progress meter, page arrows, FUSION) is always inside the body (Kit.indexLayout, checked at four window
-- sizes by tools/verify_toybox_layout.py). A card is one tap target (no VIEW DINO bar). An undiscovered dino is a soft tinted silhouette with ONE "?".
-- Kept from the old list: paging (24 per page), secret species (BD-604), the milestone ticks (BD-269), mutation badge, colour bonus line.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Preview = require(Shared.DinosaurPreview)
local ProgressionConfig = require(Shared.ProgressionConfig)
local FusionSelection = require(Shared.FusionSelection)
local IndexProgress = require(Shared.IndexProgress)
local Secret = require(Shared.SecretSpeciesConfig)
local ChipStyle = require(Shared.ChipStyle)
local L = require(Shared.ToyboxLayout)
local Kit = L.Kit

local List = {}
local GREY = Color3.fromRGB(128, 142, 158) -- the grey gloss button; the only coloured (green) button of the screen is FUSION

local function pos(r: any): UDim2 return UDim2.fromOffset(r.x, r.y) end
local function size(r: any): UDim2 return UDim2.fromOffset(r.w, r.h) end

-- d: {body, C, label, hero, copies, bestMutation, eventMutation, ownedTraits, speciesIndex, decoded, open, openFusion, select(id), rarityColors,
--     rarityNames, motion, bodyW, bodyH, bodyScale}
function List.build(d: any)
    local C = d.C
    local order = Secret.indexOrder(Config.SpeciesOrder, Config.SecretSpeciesEnabled)
    local pg = IndexProgress.page(#order, 24, IndexProgress.state.page)
    IndexProgress.state.page = pg.page
    local lay = Kit.indexLayout(d.bodyScale, d.bodyW, d.bodyH, pg.pages > 1)

    local root = Instance.new("Frame")
    root.Name, root.BackgroundTransparency, root.BorderSizePixel = "DinoIndexToybox", 1, 0
    root.Size, root.ZIndex = UDim2.fromOffset(d.bodyW, d.bodyH), d.body.ZIndex + 1 -- offsets, not scale: a short body never grows a scroll bar from it
    root.Parent = d.body

    local list = Instance.new("ScrollingFrame")
    list.Name, list.Size, list.Position = "DinoCards", size(lay.grid), pos(lay.grid)
    list.BackgroundTransparency, list.BorderSizePixel, list.ScrollBarThickness, list.ZIndex = 1, 0, 6, root.ZIndex + 1
    list.Parent = root
    local padding = Instance.new("UIPadding") -- room for the 3 px card outline at the top and left edge
    padding.PaddingTop, padding.PaddingLeft, padding.Parent = UDim.new(0, 3), UDim.new(0, 3), list
    local grid = Instance.new("UIGridLayout")
    grid.CellSize, grid.CellPadding, grid.SortOrder = UDim2.fromOffset(lay.cellW, lay.cellH), UDim2.fromOffset(Kit.Gutter, Kit.Gutter), Enum.SortOrder.LayoutOrder
    grid.Parent = list
    local onPage = pg.last - pg.first + 1
    local rows = math.ceil(onPage / lay.columns)
    list.CanvasSize = UDim2.fromOffset(0, rows * lay.cellH + math.max(rows - 1, 0) * Kit.Gutter + 6)

    local unlocked = 0
    for i, id in order do
        local base, gold, diamond = d.copies(id)
        local event = d.eventMutation(id)
        local rarity = d.speciesIndex(id)
        local found = base + gold + diamond > 0 or event ~= nil or d.ownedTraits(id) ~= nil
        local secret = i > #Config.SpeciesOrder
        if found and not secret then unlocked += 1 end
        if i < pg.first or i > pg.last then continue end
        local look = if secret then Secret.indexCard(id, found) else FusionSelection.indexCard(found)
        local card = L.card(list, "Card_" .. id, UDim2.fromOffset(lay.cellW, lay.cellH), UDim2.new(), if found then "card" else "slot")
        card.LayoutOrder = i
        local innerW = lay.cellW - 16
        local heroY, heroH = 58, lay.cellH - 58 - 30
        if found then
            L.text(card, look.nameText or Config.SpeciesDisplayNames[id], UDim2.fromOffset(innerW, 22), UDim2.fromOffset(8, 8), Kit.Type.body, "value", Enum.TextXAlignment.Center).Name = "Name"
            local chip = Instance.new("Frame")
            chip.Name, chip.Size, chip.Position, chip.ZIndex = "RarityChip", UDim2.fromOffset(innerW, 22), UDim2.fromOffset(8, 32), card.ZIndex + 1
            ChipStyle.apply(chip, d.rarityColors[rarity], C.outline, true)
            chip.Parent = card
            d.label(chip, look.rarityText or d.rarityNames[rarity], 0, 0, innerW, 22, 14)
            d.hero(card, id, 8, heroY, innerW, heroH, d.bestMutation(id))
            if event then
                require(script.Parent.MutationBadge).chip(card, event.id, UDim2.new(0.5, 0, 0, lay.cellH - 30), Vector2.new(0.5, 0))
            else
                local traits = d.ownedTraits(id)
                local line = if traits then (require(Shared.ColourBonus).text(ProgressionConfig.EggColors, (traits :: any).genes) or "Special variant")
                    else require(script.Parent.ClassRow).label(id) .. " • " .. require(Shared.FtueP1).indexCount(base, gold, diamond)
                L.text(card, line, UDim2.fromOffset(innerW, 22), UDim2.fromOffset(8, lay.cellH - 30), Kit.Type.small, "label", Enum.TextXAlignment.Center).Name = "Detail"
            end
        else
            -- undiscovered: a soft tinted silhouette and ONE "?" line (never "???" twice)
            if secret and not look.silhouette then
                L.text(card, "?", UDim2.fromOffset(innerW, heroH), UDim2.fromOffset(8, heroY), Kit.Type.title, "label", Enum.TextXAlignment.Center).Name = "Unknown"
            else
                local view = Preview.add(card, id, "silhouette")
                view.Position, view.Size = UDim2.fromOffset(8, 12), UDim2.fromOffset(innerW, lay.cellH - 12 - 38)
                view.ImageColor3 = L.tone("silhouette")
                L.text(card, "?", UDim2.fromOffset(innerW, 28), UDim2.fromOffset(8, lay.cellH - 36), Kit.Type.heading, "label", Enum.TextXAlignment.Center).Name = "Unknown"
            end
        end
        if found then -- the whole card opens the dino
            local tap = Instance.new("TextButton")
            tap.Name, tap.Text, tap.BackgroundTransparency, tap.AutoButtonColor = "ViewDino", "", 1, false
            tap.Size, tap.ZIndex = UDim2.fromOffset(lay.cellW, lay.cellH), card.ZIndex + 8
            tap.Parent = card
            tap.Activated:Connect(function() d.select(id) d.open("detail") end)
        end
    end

    -- ---- bottom bar: always inside the body ----
    local progress = IndexProgress.summary(unlocked, #Config.SpeciesOrder)
    local track = L.card(root, "IndexBar", size(lay.meter), pos(lay.meter), "slot")
    track.ClipsDescendants = true
    local fill = Instance.new("Frame")
    fill.Name, fill.BorderSizePixel, fill.BackgroundColor3, fill.ZIndex = "IndexFill", 0, C.accent, track.ZIndex + 1
    fill.Size = UDim2.new(progress.fraction, 0, 1, 0)
    fill.Parent = track
    for _, tick in progress.ticks do
        if tick.fraction < 1 then -- BD-269: milestone ticks, inside the bar
            local mark = Instance.new("Frame")
            mark.Name, mark.BorderSizePixel, mark.ZIndex, mark.Parent = "IndexMilestone", 0, track.ZIndex + 2, track
            mark.Size, mark.Position = UDim2.new(0, 2, 1, 0), UDim2.fromOffset(math.floor(lay.meter.w * tick.fraction) - 1, 0)
            mark.BackgroundColor3, mark.BackgroundTransparency = L.tone("value"), if tick.reached then .6 else .8
        end
    end
    local words = progress.short
    if Config.SecretSpeciesEnabled == true and lay.meter.w >= 300 then
        words ..= " • " .. Secret.summary(Secret.countFound(d.decoded("CollectionJson", "{}"))).text -- BD-604: secrets counted apart from the 22
    end
    L.text(track, words, UDim2.fromOffset(lay.meter.w - 16, lay.meter.h - 4), UDim2.fromOffset(8, 2), Kit.Type.heading, "value", Enum.TextXAlignment.Center).Name = "IndexText"
    if pg.pages > 1 then
        L.actionButton(root, "<", size(lay.prev), pos(lay.prev), GREY, true, function() IndexProgress.state.page = pg.page - 1 d.open("collection") end).Name = "PagePrev"
        L.text(root, pg.page .. " / " .. pg.pages, size(lay.page), pos(lay.page), Kit.Type.heading, "value", Enum.TextXAlignment.Center).Name = "PageNumber"
        L.actionButton(root, ">", size(lay.next), pos(lay.next), GREY, true, function() IndexProgress.state.page = pg.page + 1 d.open("collection") end).Name = "PageNext"
    end
    L.actionButton(root, "FUSION", size(lay.fusion), pos(lay.fusion), C.accent, false, function() d.openFusion() end).Name = "FusionButton"
end

return List
