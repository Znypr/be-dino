--!strict
-- Combined Eggs screen (owner 2026-10-15): five nest slots on top, ONE large "Next egg" card below.
-- Drawing only; state rules live in Shared/EggsLogic (tools/verify_eggs_screen.py). Bootstrap passes a
-- context table of its UI helpers so this module stays focused and Bootstrap edits stay small.
-- Art: reuses the uploaded egg_nest icon and the real egg preview. No new art, no PLACEHOLDER needed.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local NestQueue = require(Shared.NestQueue)
local EggsLogic = require(Shared.EggsLogic)
local EggGenetics = require(Shared.EggGenetics)
local FusionSelection = require(Shared.FusionSelection)
local ProgressionConfig = require(Shared.ProgressionConfig)
local ProgressionRules = require(Shared.ProgressionRules)
local ModelPreview = require(Shared.ModelPreview)
local UIFormat = require(Shared.UIFormat)
local PreviewTraits = require(script.Parent.PreviewTraits)

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
    local nestH = math.clamp(touchH, 96, 124)

    local nestList = ctx.nestList
    local function projected() return NestQueue.project(nestList, math.floor(workspace:GetServerTimeNow()), duration) end
    local header = label(body, EggsLogic.nestHeader(nestList, capacity), 0, 0, 220, 28, 24, C.gold)
    header.TextXAlignment = Enum.TextXAlignment.Left
    local luck = label(body, "Nest eggs are lucky!", 224, 2, 600, 26, 18)
    luck.TextXAlignment = Enum.TextXAlignment.Right

    -- Five nest slots: egg-nest icon, status text, tap READY to open. Empty slots are dimmed.
    local slotW, gap = 156, 11
    local slotViews = {}
    for i = 1, capacity do
        local x = (i - 1) * (slotW + gap)
        local slot = button(body, "", x, 32, slotW, nestH, C.card, function()
            local info = slotViews[i].info
            if info and info.state == "ready" then ctx.openNest(info.id)
            elseif info and info.state == "empty" then ctx.notify("Finish a run to earn a nest!", C.gold)
            elseif info then ctx.notify("This nest is growing. Hang tight!", C.gold) end
        end)
        slot.Name = "NestSlot" .. i
        local icon = box(slot, (slotW - 52) // 2, 6, 52, 52, C.card, slot.ZIndex + 1)
        icon.BackgroundTransparency = 1
        art(icon, "egg_nest", 0, 0, 52)
        local text = label(slot, "", 0, 62, slotW, nestH - 64, 19)
        slotViews[i] = {slot = slot, icon = icon, text = text}
    end

    -- ONE large "Next egg" card.
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

    label(card, "Next egg", 14, 6, 200, 28, 22, C.gold).TextXAlignment = Enum.TextXAlignment.Left
    local look = FusionSelection.eggSlotLook(entry, entry ~= nil and EggGenetics.valid(entry.genes))
    local viewSize = math.clamp(cardH - 50, 96, 170)
    local view = ModelPreview.add(card, "egg", look == "empty")
    view.Position, view.Size = UDim2.fromOffset(16, 38), UDim2.fromOffset(viewSize, viewSize)
    if entry then PreviewTraits.add(view, if look == "genes" then entry else {shiny = entry.shiny, big = entry.big}) end

    local infoX = 16 + viewSize + 14
    local infoW = 824 - infoX - 14
    local rarity = if entry then entry.rarity or 1 else nil
    if entry and rarity then
        label(card, ctx.rarityNames[rarity], infoX, 40, 230, 30, 24, ctx.rarityColors[rarity]).TextXAlignment = Enum.TextXAlignment.Left
        local conditionName = if entry.genes then EggGenetics.condition(entry.genes.conditionId).name else nil
        local mutation = ProgressionRules.item(ProgressionConfig.EventMutations, entry.mutationId)
        local badge = conditionName
        local badgeColor = C.gold
        if mutation then
            badge = mutation.name
            badgeColor = Color3.fromRGB(mutation.color[1], mutation.color[2], mutation.color[3])
        elseif entry.eventId and entry.eventId ~= "clear" then
            local weather = ProgressionRules.item(ProgressionConfig.Weather, entry.eventId)
            badge = if weather then weather.name else entry.eventId
        end
        if badge then label(card, badge, infoX, 72, 230, 28, 20, badgeColor).TextXAlignment = Enum.TextXAlignment.Left end
    else
        local empty = label(card, statusText, infoX, 46, 250, 90, 22, C.text)
        empty.TextXAlignment = Enum.TextXAlignment.Left
    end
    local timer = label(card, if entry then statusText else "", infoX, 104, 230, 40, 26, C.gold)
    timer.TextXAlignment = Enum.TextXAlignment.Left
    label(card, "Eggs waiting: " .. waiting, infoX, 150, 230, 28, 20).TextXAlignment = Enum.TextXAlignment.Left

    -- OPEN (one clear action) + gear to the auto-open settings.
    local openW = math.min(300, infoW - 240)
    local openX = 824 - 14 - openW
    local openButton = button(card, buttonText, openX, 40, openW, math.min(touchH + 16, cardH - 100), if state.canOpen then C.accent else C.outline, function()
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        if state.canOpen then ctx.openEgg()
        elseif state.kind == "growing" then ctx.notify("This egg is still growing", C.gold)
        else ctx.notify("Finish a run to catch eggs!", C.gold) end
    end)
    openButton.Name = "OpenEggButton"
    openButton.TextSize = 30
    local gear = button(card, "AUTO", openX, cardH - 14 - math.max(touchH * .6, 52), openW, math.max(touchH * .6, 52), C.blue, function() ctx.openSettings() end)
    gear.Name = "AutoOpenSettingsButton"
    gear.TextSize = 20
    local autoLine = label(card, ctx.autoOpenText(), infoX, cardH - 62, openX - infoX - 10, 48, 17, C.text)
    autoLine.TextXAlignment = Enum.TextXAlignment.Left

    local function refresh()
        if not card.Parent then return end
        local now = math.floor(workspace:GetServerTimeNow())
        local slots = EggsLogic.nestSlots(projected(), capacity, now)
        for i, info in slots do
            local v = slotViews[i]
            v.info = info
            local opening, ready, empty = info.state == "opening", info.state == "ready", info.state == "empty"
            v.slot.BackgroundColor3 = if ready then C.accent elseif opening then C.gold elseif empty then C.outline else C.card
            v.text.Text = if opening then "Ready in " .. UIFormat.duration(info.remaining) else info.text
            v.text.TextTransparency = if empty then .45 else 0
            dim(v.icon, if empty then .8 else 0)
        end
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        statusText, buttonText = EggsLogic.cardCopy(state)
        openButton.Text = buttonText
        openButton.BackgroundColor3 = if state.canOpen then C.accent else C.outline
        if entry then
            local remaining = math.max(0, (if typeof(entry.readyAt) == "number" then entry.readyAt else ctx.num("NextChestReadyAt")) - workspace:GetServerTimeNow())
            timer.Text = if remaining <= 0 then "READY!" else "Growing " .. UIFormat.duration(remaining)
        end
    end
    refresh()
    return refresh
end

return EggsScreen
