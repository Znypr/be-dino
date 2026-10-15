--!strict
-- Combined Eggs screen (owner 2026-10-15): five nest slots on top, ONE large "Next egg" card below.
-- Drawing only; state rules live in Shared/EggsLogic (tools/verify_eggs_screen.py). Bootstrap passes a
-- context table of its UI helpers so this module stays focused and Bootstrap edits stay small.
-- BD-169 redesign (docs/87 calm, bubbly, colourful): the hero egg is the official Blender egg PNG (EggPicture, with its condition look)
-- on a soft tile floor (PLACEHOLDER until the Blender tile-floor render is uploaded, docs/77 egg_stage); nest slots use the single-egg
-- nest icon (egg_nest_single). No motion is added, so Reduce Motion needs nothing.
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
    local luck = label(body, "Nest eggs are lucky!", 224, 2, 600, 26, 18)
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
    local stageW, stageH = 300, cardH - 20
    local stage = EggPicture.stage(card, stageW, stageH, accent)
    stage.Position = UDim2.fromOffset(10, 10)
    local look = FusionSelection.eggSlotLook(entry, entry ~= nil and EggGenetics.valid(entry.genes))
    local eggSize = math.clamp(stageH - 70, 110, 190)
    local egg = EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)
    egg.Position = UDim2.fromOffset((stageW - eggSize) // 2, 14)
    if not entry then dim(egg, .6) end

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
    end

    local infoX = stageW + 30
    local infoW = 824 - infoX - 14
    local waitingLabel = label(card, "Eggs waiting: " .. waiting, infoX, 10, infoW, 38, 30, C.gold)
    waitingLabel.Name = "EggsWaiting"
    waitingLabel.TextXAlignment = Enum.TextXAlignment.Left
    local timerChip, timer = pill(card, if entry then statusText else "No eggs yet", if state.canOpen then C.accent else C.blue, infoX, 54, math.min(280, infoW), 38, 22)
    timerChip.Name = "EggStatusPill"

    local gearH = math.max(touchH * .6, 52)
    local openH = math.clamp(cardH - 106 - 14 - gearH - 14, 64, 96)
    local openButton = button(card, buttonText, infoX, 106, infoW, openH, if state.canOpen then C.accent else C.outline, function()
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        if state.canOpen then ctx.openEgg()
        elseif state.kind == "growing" then ctx.notify("This egg is still growing", C.gold)
        else ctx.notify("Finish a run to catch eggs!", C.gold) end
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
        openButton.BackgroundColor3 = if state.canOpen then C.accent else C.outline
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
