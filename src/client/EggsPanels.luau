--!strict
-- BD-1195 (docs/232, finding P-ae0545): the Eggs screen on the Toybox layout rules. Required by EggsScreen ONLY while Config.ToyboxUIEnabled is on
-- (flag off = EggsScreen draws the old screen, this file is never loaded). Three cream panels fill the menu body: the nests (heading line, a
-- "Nests 0/5" chip, five equal cards), the egg stage (the egg picture in its own panel) and the info panel (status line as plain dark text, up to
-- two note lines, ONE green 48 px button, the small grey AUTO toggle with its state on it). Rects: Kit.eggsLayout (tools/verify_toybox_layout.py
-- checks them at four window sizes). Every function of the old screen is kept: nest tap (open ready nest / hints), timers, OPEN / Explore,
-- AUTO -> Settings, waiting count, Cracked hint, mutation / weather badge, condition and rarity chips.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local NestQueue = require(Shared.NestQueue)
local EggsLogic = require(Shared.EggsLogic)
local EggGenetics = require(Shared.EggGenetics)
local FusionSelection = require(Shared.FusionSelection)
local ProgressionConfig = require(Shared.ProgressionConfig)
local ProgressionRules = require(Shared.ProgressionRules)
local UIFormat = require(Shared.UIFormat)
local EggPicture = require(script.Parent.EggPicture)
local ConditionStage = require(script.Parent.ConditionStage)
local StageRules = require(Shared.ConditionStageRules)
local FxUi = require(Shared.FxUi)
local MutationLook = require(Shared.MutationLook)
local Theme = require(Shared.UITheme)
local Copy = require(Shared.FtueP1)
local Chip = require(Shared.ChipStyle)
local L = require(Shared.ToyboxLayout)
local Kit = L.Kit

local Panels = {}
local GREY = Color3.fromRGB(128, 142, 158) -- the grey gloss button; the only coloured (green) button of the screen is OPEN / Explore

local function pos(r: any): UDim2 return UDim2.fromOffset(r.x, r.y) end
local function size(r: any): UDim2 return UDim2.fromOffset(r.w, r.h) end

local function dim(root: Instance, transparency: number)
    for _, item in root:GetDescendants() do
        if item:IsA("ImageLabel") then item.ImageTransparency = transparency end
    end
end

-- "AUTO: ON / OFF / LOCKED": the state of auto-open on the toggle itself (the words come from Bootstrap's autoOpenText).
function Panels.autoState(line: string): string
    if string.find(line, "locked", 1, true) then return "AUTO: LOCKED" end
    if line == "Auto-open: off" then return "AUTO: OFF" end
    return "AUTO: ON"
end

-- ctx: the EggsScreen context (body, C, label, art, queue, str, num, nestList, rarityNames, rarityColors, notify, openNest, openEgg, openSettings,
-- autoOpenText, explore, collectionCopies, scale). Returns refresh(): the once-a-second timer update.
function Panels.build(ctx: any, bodyW: number, bodyH: number, bodyScale: number): () -> ()
    local C, label, art = ctx.C, ctx.label, ctx.art
    local capacity, duration = Config.NestStorageCapacity, Config.NestIncubationSeconds
    local nestList = ctx.nestList
    local function projected() return NestQueue.project(nestList, math.floor(workspace:GetServerTimeNow()), duration) end

    local queue = ctx.queue()
    local nextId = ctx.str("NextChestId")
    local entry = nil
    for _, item in queue do if item.id == nextId then entry = item break end end
    entry = entry or queue[1]
    local waiting = ctx.num("QueuedEggsWaiting")
    local state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
    local statusText, buttonText = EggsLogic.cardCopy(state)
    local waitingText = Copy.eggOfText(ctx.num("ActiveChestCount"), waiting) -- "Egg 1 of N": hidden at 0
    local isCracked = entry ~= nil and entry.genes ~= nil and entry.genes.conditionId == "cracked"
    local hintShown = isCracked or (entry ~= nil and Copy.crackedHintShown(ctx.collectionCopies(), true))
    local lay = Kit.eggsLayout(bodyScale, bodyW, bodyH, (if waitingText then 1 else 0) + (if hintShown then 1 else 0), capacity)

    local root = Instance.new("Frame")
    root.Name, root.BackgroundTransparency, root.BorderSizePixel = "EggsToybox", 1, 0
    root.Size, root.ZIndex = UDim2.fromOffset(bodyW, bodyH), ctx.body.ZIndex + 1 -- offsets, not scale: a short compact body never grows a scroll bar
    root.Parent = ctx.body

    -- ---- nests ----
    local nests = L.panel(root, "Nests", size(lay.nests), pos(lay.nests))
    L.text(nests, Copy.NestLine, size(lay.nestHead), pos(lay.nestHead), Kit.Type.body, "label").Name = "NestLine" -- BD-369: says why only one nest opens at a time
    local _, countLabel = L.chip(nests, EggsLogic.nestHeader(nestList, capacity), size(lay.nestChip), pos(lay.nestChip))
    countLabel.Name = "NestCount"
    local slotViews = {}
    for i = 1, capacity do
        local r = lay.nestCards[i]
        local card = L.card(nests, "NestSlot" .. i, size(r), pos(r))
        local textY = r.h - 8 - 24
        local iconSize = math.max(24, math.min(r.w - 16, textY - 12))
        local icon = Instance.new("Frame")
        icon.Name, icon.BackgroundTransparency, icon.BorderSizePixel = "NestIcon", 1, 0
        icon.Size, icon.Position, icon.ZIndex = UDim2.fromOffset(iconSize, iconSize), UDim2.fromOffset((r.w - iconSize) // 2, 8), card.ZIndex + 1
        icon.Parent = card
        art(icon, "egg_nest_single", 0, 0, iconSize)
        -- BD-1202 (finding P-dbfb7f): an EMPTY slot never shows the egg. The nest picture has its egg baked in, so an empty slot shows only the lower
        -- third of it (the woven nest, no egg) at 40%, cropped by a clipping box (same picture, same art helper, nothing new drawn).
        local emptyNest = Instance.new("Frame")
        emptyNest.Name, emptyNest.BackgroundTransparency, emptyNest.BorderSizePixel, emptyNest.ClipsDescendants, emptyNest.Visible = "EmptyNest", 1, 0, true, false
        emptyNest.Size = UDim2.fromOffset(iconSize, math.floor(iconSize * 0.34))
        emptyNest.Position, emptyNest.ZIndex = UDim2.fromOffset((r.w - iconSize) // 2, 8 + math.floor(iconSize * 0.33)), card.ZIndex + 1
        emptyNest.Parent = card
        local nestOnly = art(emptyNest, "egg_nest_single", 0, -math.floor(iconSize * 0.63), iconSize)
        if nestOnly then dim(emptyNest, 0.6) end
        local text = L.text(card, "", UDim2.fromOffset(r.w - 8, 24), UDim2.fromOffset(4, textY), Kit.Type.body, "value", Enum.TextXAlignment.Center)
        text.Name = "NestText"
        local tap = Instance.new("TextButton") -- the whole card is the button (it fills the card, no colour of its own)
        tap.Name, tap.Text, tap.BackgroundTransparency, tap.AutoButtonColor = "NestTap", "", 1, false
        tap.Size, tap.ZIndex = UDim2.fromOffset(r.w, r.h), card.ZIndex + 3
        tap.Parent = card
        tap.Activated:Connect(function()
            local info = slotViews[i].info
            if info and info.state == "ready" then ctx.openNest(info.id)
            elseif info and info.state == "empty" then ctx.notify("Finish a run to earn a nest!", C.gold)
            elseif info then ctx.notify("Still growing. Hang tight!", C.gold) end
        end)
        slotViews[i] = {card = card, icon = icon, text = text, emptyNest = emptyNest}
    end

    -- ---- the egg stage, in its own panel ----
    local stagePanel = L.panel(root, "EggStage", size(lay.stagePanel), pos(lay.stagePanel))
    local rarity = if entry then entry.rarity or 1 else nil
    local accent = if rarity then ctx.rarityColors[rarity] else C.blue
    local look = FusionSelection.eggSlotLook(entry, entry ~= nil and EggGenetics.valid(entry.genes))
    local conditionKey = StageRules.conditionKey(if entry and look == "genes" then entry.genes.conditionId else nil)
    local stageW, stageH = lay.stage.w, lay.stage.h
    local side = StageRules.heroSide(stageW, stageH)
    local official = ConditionStage.hero(stagePanel, side, conditionKey)
    local stage: GuiObject
    local egg: GuiObject
    if official then
        stageW, stageH = side, side
        stage = official.frame
        stage.Position = UDim2.fromOffset(lay.stage.x + (lay.stage.w - side) // 2, lay.stage.y + (lay.stage.h - side) // 2)
        if official.egg then
            egg = official.egg
            if not entry then (egg :: ImageLabel).ImageTransparency = .6 end
        else
            local eggSize = math.clamp(side - 64, 60, 190)
            egg = EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)
            egg.Position = UDim2.fromOffset((side - eggSize) // 2, math.max(4, math.floor(side * .76) - eggSize))
            if not entry then dim(egg, .6) end
        end
    else
        stage = EggPicture.stage(stagePanel, stageW, stageH, accent)
        stage.Position = pos(lay.stage)
        local eggSize = math.clamp(stageH - 64, 60, 190)
        egg = EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)
        egg.Position = UDim2.fromOffset((stageW - eggSize) // 2, 6)
        if not entry then dim(egg, .6) end
    end
    local function pill(parent: GuiObject, text: string, color: Color3, x: number, y: number, w: number, h: number, textSize: number): Frame
        local frame = Instance.new("Frame")
        frame.Position, frame.Size, frame.ZIndex = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), parent.ZIndex + 1
        Chip.apply(frame, color, C.outline)
        frame.Parent = parent
        local tag = label(frame, text, 0, 0, w, h, textSize)
        tag.TextScaled = true
        local limit = Instance.new("UITextSizeConstraint") limit.MaxTextSize, limit.MinTextSize, limit.Parent = textSize, 14, tag
        return frame
    end
    if entry and rarity then
        local conditionName = if entry.genes and EggGenetics.valid(entry.genes) then EggGenetics.condition(entry.genes.conditionId or "normal").name else nil
        local mutation = ProgressionRules.item(ProgressionConfig.EventMutations, entry.mutationId)
        local badge, badgeColor = nil, C.gold
        if mutation then
            badge = mutation.name
            badgeColor = Color3.fromRGB(mutation.color[1], mutation.color[2], mutation.color[3])
        elseif entry.eventId and entry.eventId ~= "clear" then
            local weather = ProgressionRules.item(ProgressionConfig.Weather, entry.eventId)
            badge = if weather then weather.name else entry.eventId
        end
        local chipY = stageH - 40
        local chipW = if conditionName then (stageW - 28) // 2 else stageW - 20
        pill(stage, ctx.rarityNames[rarity], ctx.rarityColors[rarity], 10, chipY, chipW, 32, 19).Name = "RarityChip"
        local typeCaption = label(stage, Copy.ChipTypeCaption, 10, chipY - 18, chipW, 18, 14, C.text)
        typeCaption.Name, typeCaption.TextStrokeTransparency = "RarityCaption", .4
        typeCaption:SetAttribute("TextKind", "note")
        if conditionName then
            pill(stage, conditionName, C.purple, 18 + chipW, chipY, chipW, 32, 19).Name = "ConditionChip"
            local shellCaption = label(stage, Copy.ChipShellCaption, 18 + chipW, chipY - 18, chipW, 18, 14, C.text)
            shellCaption.Name, shellCaption.TextStrokeTransparency = "ConditionCaption", .4
            shellCaption:SetAttribute("TextKind", "note")
        end
        if badge then pill(stage, badge, badgeColor, 10, 8, math.min(150, stageW - 20), 30, 17).Name = "BadgeChip" end
        local mutationLook = MutationLook.get(entry.mutationId)
        if mutationLook then
            local ok, handle = pcall(function() return FxUi.mount(stage, "mutation", mutationLook, {reduce = not Theme.MotionEnabled, detail = "lite"}) end)
            local fxFrame: any = if ok and handle then (handle :: any).frame else nil
            if fxFrame then fxFrame.ZIndex = math.max(1, egg.ZIndex - 1) fxFrame.Name = "FxUi_mutation_card" end
        end
    end

    -- ---- info panel ----
    local info = L.panel(root, "EggInfo", size(lay.infoPanel), pos(lay.infoPanel))
    local status = L.text(info, statusText, size(lay.status), pos(lay.status), Kit.Type.heading, "value")
    status.Name = "EggStatusPill"
    local noteY = lay.notes.y
    if waitingText then
        L.text(info, waitingText, UDim2.fromOffset(lay.notes.w, Kit.Eggs.noteH), UDim2.fromOffset(lay.notes.x, noteY), Kit.Type.body, "label").Name = "EggsWaiting"
        noteY += Kit.Eggs.noteH
    end
    if hintShown then
        L.text(info, if isCracked then Copy.CrackedShellLine else Copy.CrackedHint, UDim2.fromOffset(lay.notes.w, Kit.Eggs.noteH), UDim2.fromOffset(lay.notes.x, noteY), Kit.Type.body, "value").Name = "CrackedHint"
    end
    local function primary() return state.canOpen or state.kind == "empty" end
    local openButton = L.actionButton(info, buttonText, size(lay.action), pos(lay.action), if primary() then C.accent else GREY, false, function()
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        if state.canOpen then ctx.openEgg()
        elseif state.kind == "growing" then ctx.notify("This egg is still growing", C.gold)
        elseif state.kind == "empty" then ctx.explore() -- BD-369: no dead end, a button to the island
        else ctx.notify("Eggs are on the way!", C.gold) end
    end)
    openButton.Name = "OpenEggButton"
    local autoLineText = ctx.autoOpenText()
    local gear = L.actionButton(info, Panels.autoState(autoLineText), size(lay.auto), pos(lay.auto), GREY, true, function() ctx.openSettings("help") end)
    gear.Name = "AutoOpenSettingsButton"
    L.text(info, autoLineText, size(lay.autoLine), pos(lay.autoLine), Kit.Type.body, "label").Name = "AutoLine"

    local function refresh()
        if not root.Parent then return end
        local now = math.floor(workspace:GetServerTimeNow())
        local slots = EggsLogic.nestSlots(projected(), capacity, now)
        for i, slot in slots do
            local v = slotViews[i]
            v.info = slot
            local empty = slot.state == "empty"
            v.card.BackgroundColor3 = L.tone(if slot.state == "ready" then "ready" elseif slot.state == "opening" then "busy" else "card")
            v.text.Text = if slot.state == "opening" then UIFormat.duration(slot.remaining) else slot.text
            L.ink(v.text, if empty then "label" else "value")
            v.emptyNest.Visible, v.icon.Visible = empty, not empty -- BD-1202: an empty slot = the nest without the egg, never the egg art
        end
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        statusText, buttonText = EggsLogic.cardCopy(state)
        openButton.Text = buttonText
        openButton.BackgroundColor3 = if primary() then C.accent else GREY
        status.Text = statusText
        if entry then
            local remaining = math.max(0, (if typeof(entry.readyAt) == "number" then entry.readyAt else ctx.num("NextChestReadyAt")) - workspace:GetServerTimeNow())
            status.Text = if remaining <= 0 then Copy.ReadyStatus else "Ready in " .. UIFormat.duration(remaining)
        end
    end
    refresh()
    return refresh
end

return Panels
