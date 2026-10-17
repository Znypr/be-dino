--!strict
-- Combined Eggs screen (owner 2026-10-15): five nest slots on top, ONE large "Next egg" card below.
-- Drawing only; state rules live in Shared/EggsLogic (tools/verify_eggs_screen.py). Bootstrap passes a
-- context table of its UI helpers so this module stays focused and Bootstrap edits stay small.
-- BD-169 redesign (docs/87 calm, bubbly, colourful): the hero egg is the official Blender egg PNG (EggPicture, with its condition look)
-- on a soft tile floor (PLACEHOLDER; BD-208: once ConditionStageAssetIds holds the owner's jungle stage, docs/77 egg_stage_jungle, the card draws
-- it with the condition egg PNG instead, ConditionStage.hero); nest slots use the single-egg nest icon (egg_nest_single, bound; code-drawn
-- fallback in UITheme if its id is ever empty). No motion is added, so Reduce Motion needs nothing.
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

local EggsScreen = {}

local function dim(root: Instance, transparency: number)
    for _, item in root:GetDescendants() do
        if item:IsA("ImageLabel") then item.ImageTransparency = transparency
        elseif item:IsA("Frame") and item.BackgroundTransparency < 1 then item.BackgroundTransparency = math.max(item.BackgroundTransparency, transparency) end
    end
end

-- ctx: body, C, label, box, button, art, queue, str, num, nestList, rarityNames, rarityColors, scale (viewportScale),
-- isActive(), openEgg(), openNest(id), openSettings(), autoOpenText(), notify(text, color?)
-- Returns refresh(): cheap once-a-second text updates (timers).
function EggsScreen.render(ctx: any)
    local body, C, label, box, button, art = ctx.body, ctx.C, ctx.label, ctx.box, ctx.button, ctx.art
    local capacity = Config.NestStorageCapacity
    local duration = Config.NestIncubationSeconds
    local touchH = math.clamp(45 / ctx.scale(), 64, 120)
    local nestH = math.clamp(touchH + 8, 96, 118)

    local nestList = ctx.nestList
    local function projected() return NestQueue.project(nestList, math.floor(workspace:GetServerTimeNow()), duration) end
    local header = label(body, EggsLogic.nestHeader(nestList, capacity), 0, 0, 220, 28, 24, C.gold)
    header.TextXAlignment = Enum.TextXAlignment.Left
    local luck = label(body, Copy.NestLine, 224, 2, 600, 26, 18) -- BD-369: says why only one nest opens at a time
    luck.TextXAlignment = Enum.TextXAlignment.Right

    -- A rounded colour pill with one short line of text (friendly timers and chips).
    local function pill(parent: GuiObject, text: string, color: Color3, x: number, y: number, w: number, h: number, size: number): (Frame, TextLabel)
        local frame = Instance.new("Frame")
        frame.BackgroundColor3, frame.BorderSizePixel = color, 0
        frame.Position, frame.Size, frame.ZIndex, frame.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), parent.ZIndex + 1, parent
        local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(.5, 0) corner.Parent = frame
        local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = C.outline, 2, frame
        local text = label(frame, text, 0, 0, w, h, size)
        text.TextScaled = true
        local limit = Instance.new("UITextSizeConstraint") limit.MaxTextSize, limit.MinTextSize, limit.Parent = size, 10, text
        return frame, text
    end

    -- Five nest slots: the occupied one shows the single-egg nest, empty ones stay dimmed. Tap READY to open.
    local slotW, gap = 156, 11
    local slotViews = {}
    for i = 1, capacity do
        local x = (i - 1) * (slotW + gap)
        local slot = button(body, "", x, 32, slotW, nestH, C.card, function()
            local info = slotViews[i].info
            if info and info.state == "ready" then ctx.openNest(info.id)
            elseif info and info.state == "empty" then ctx.notify("Finish a run to earn a nest!", C.gold)
            elseif info then ctx.notify("Still growing. Hang tight!", C.gold) end
        end)
        slot.Name = "NestSlot" .. i
        local iconSize = nestH - 52
        local icon = box(slot, (slotW - iconSize) // 2, 4, iconSize, iconSize, C.card, slot.ZIndex + 1)
        icon.BackgroundTransparency = 1
        art(icon, "egg_nest_single", 0, 0, iconSize)
        local chip, text = pill(slot, "", C.outline, 14, nestH - 40, slotW - 28, 32, 18)
        slotViews[i] = {slot = slot, icon = icon, text = text, chip = chip}
    end

    -- Hero card: big egg on the tile floor, chips on the egg, waiting count, OPEN and AUTO.
    local cardY = 32 + nestH + 8
    local cardH = 402 - cardY
    local card = box(body, 0, cardY, 824, cardH, C.card, 24)
    local queue = ctx.queue()
    local nextId = ctx.str("NextChestId")
    local entry = nil
    for _, item in queue do if item.id == nextId then entry = item break end end
    entry = entry or queue[1]
    local waiting = ctx.num("QueuedEggsWaiting")
    local state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
    local statusText, buttonText = EggsLogic.cardCopy(state)

    local rarity = if entry then entry.rarity or 1 else nil
    local accent = if rarity then ctx.rarityColors[rarity] else C.blue
    -- BD-208: the official Blender stage + condition egg when uploaded (ConditionStageAssetIds, a SQUARE with ScaleType Fit, nothing
    -- stretched); with no id the tile floor and tinted egg below stay exactly as they were.
    local look = FusionSelection.eggSlotLook(entry, entry ~= nil and EggGenetics.valid(entry.genes))
    local conditionKey = StageRules.conditionKey(if entry and look == "genes" then entry.genes.conditionId else nil)
    local stageW, stageH = 300, cardH - 20
    local side = StageRules.heroSide(stageW, stageH)
    local official = ConditionStage.hero(card, side, conditionKey)
    local stage: GuiObject
    local egg: GuiObject
    if official then
        stageW, stageH = side, side
        stage = official.frame
        stage.Position = UDim2.fromOffset(10, 10 + (cardH - 20 - side) // 2)
        if official.egg then
            egg = official.egg
            if not entry then (egg :: ImageLabel).ImageTransparency = .6 end
        else
            local eggSize = math.clamp(side - 70, 110, 190) -- stage only: today's tinted egg standing on the pedestal
            egg = EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)
            egg.Position = UDim2.fromOffset((side - eggSize) // 2, math.max(4, math.floor(side * .76) - eggSize))
            if not entry then dim(egg, .6) end
        end
    else
        stage = EggPicture.stage(card, stageW, stageH, accent)
        stage.Position = UDim2.fromOffset(10, 10)
        local eggSize = math.clamp(stageH - 70, 110, 190)
        egg = EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)
        egg.Position = UDim2.fromOffset((stageW - eggSize) // 2, 14)
        if not entry then dim(egg, .6) end
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
        local rarityChip = pill(stage, ctx.rarityNames[rarity], ctx.rarityColors[rarity], 10, chipY, chipW, 32, 19)
        rarityChip.Name = "RarityChip"
        if conditionName then
            local conditionChip = pill(stage, conditionName, C.purple, 18 + chipW, chipY, chipW, 32, 19)
            conditionChip.Name = "ConditionChip"
        end
        if badge then
            local badgeChip = pill(stage, badge, badgeColor, 10, 8, 150, 30, 17)
            badgeChip.Name = "BadgeChip"
        end
        -- BD-162: a small live mutation preview (soft glow + motes) behind the egg; Reduce Motion shows one still glow.
        local mutationLook = MutationLook.get(entry.mutationId)
        if mutationLook then
            local ok, handle = pcall(function() return FxUi.mount(stage, "mutation", mutationLook, {reduce = not Theme.MotionEnabled, detail = "lite"}) end)
            local fxFrame: any = if ok and handle then (handle :: any).frame else nil
            if fxFrame then fxFrame.ZIndex = math.max(1, egg.ZIndex - 1) fxFrame.Name = "FxUi_mutation_card" end
        end
    end

    local infoX = stageW + 30
    local infoW = 824 - infoX - 14
    local waitingText = Copy.waitingText(ctx.num("ActiveChestCount"), waiting) -- BD-369: counts the card egg; hidden at 0
    if waitingText then
        local waitingLabel = label(card, waitingText, infoX, 10, infoW, 38, 30, C.gold)
        waitingLabel.Name = "EggsWaiting"
        waitingLabel.TextXAlignment = Enum.TextXAlignment.Left
    end
    local timerChip, timer = pill(card, statusText, if state.canOpen then C.accent else C.blue, infoX, 54, if entry then math.min(280, infoW) else infoW, 38, 22)
    timerChip.Name = "EggStatusPill"
    -- BD-369: after the safe first eggs, say once in one short line that an egg can crack.
    local hintShown = entry ~= nil and Copy.crackedHintShown(ctx.collectionCopies(), true)
    local hintH = if hintShown then 24 else 0
    if hintShown then
        local crackedHint = label(card, Copy.CrackedHint, infoX, 94, infoW, 22, 19, C.gold)
        crackedHint.Name = "CrackedHint"
        crackedHint.TextXAlignment = Enum.TextXAlignment.Left
    end

    local gearH = math.max(touchH * .6, 52)
    local openH = math.clamp(cardH - 106 - hintH - 14 - gearH - 14, 64, 96)
    local openButton = button(card, buttonText, infoX, 106 + hintH, infoW, openH, if state.canOpen or state.kind == "empty" then C.accent else C.outline, function()
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        if state.canOpen then ctx.openEgg()
        elseif state.kind == "growing" then ctx.notify("This egg is still growing", C.gold)
        elseif state.kind == "empty" then ctx.explore() -- BD-369: no dead end, a button to the island
        else ctx.notify("Eggs are on the way!", C.gold) end
    end)
    openButton.Name = "OpenEggButton"
    openButton.TextSize = 36
    local gear = button(card, "AUTO", infoX, cardH - 14 - gearH, 130, gearH, C.blue, function() ctx.openSettings() end)
    gear.Name = "AutoOpenSettingsButton"
    gear.TextSize = 22
    local autoLine = label(card, ctx.autoOpenText(), infoX + 142, cardH - 14 - gearH, infoW - 142, gearH, 17, C.text)
    autoLine.TextXAlignment = Enum.TextXAlignment.Left

    local function refresh()
        if not card.Parent then return end
        local now = math.floor(workspace:GetServerTimeNow())
        local slots = EggsLogic.nestSlots(projected(), capacity, now)
        for i, info in slots do
            local v = slotViews[i]
            v.info = info
            local opening, ready, empty = info.state == "opening", info.state == "ready", info.state == "empty"
            v.slot.BackgroundColor3 = if empty then C.outline else C.card
            v.chip.BackgroundColor3 = if ready then C.accent elseif opening then C.gold elseif empty then C.card else C.blue
            v.text.Text = if opening then UIFormat.duration(info.remaining) else info.text
            v.text.TextTransparency = if empty then .45 else 0
            dim(v.icon, if empty then .75 else 0)
        end
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        statusText, buttonText = EggsLogic.cardCopy(state)
        openButton.Text = buttonText
        openButton.BackgroundColor3 = if state.canOpen or state.kind == "empty" then C.accent else C.outline
        timerChip.BackgroundColor3 = if state.canOpen then C.accent else C.blue
        if entry then
            local remaining = math.max(0, (if typeof(entry.readyAt) == "number" then entry.readyAt else ctx.num("NextChestReadyAt")) - workspace:GetServerTimeNow())
            timer.Text = if remaining <= 0 then "READY!" else "Ready in " .. UIFormat.duration(remaining)
        end
    end
    refresh()
    return refresh
end

return EggsScreen
