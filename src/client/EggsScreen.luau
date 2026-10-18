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
local PhoneScale = require(Shared.PhoneScale)
local Chip = require(Shared.ChipStyle)

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
-- BD-1067: bodyH / bodyScale are the visible body height and the scale it renders at (ModalCompact), read NOW by render() below.
local function build(ctx: any, bodyH: number, bodyScale: number)
    local body, C, label, box, button, art = ctx.body, ctx.C, ctx.label, ctx.box, ctx.button, ctx.art
    local capacity = Config.NestStorageCapacity
    local duration = Config.NestIncubationSeconds
    local touchH = math.clamp(45 / ctx.scale(), 64, 120)
    -- BD-531: on a phone-landscape canvas (ModalCompact.bodyHeight < 402) the whole screen is laid out inside the visible body height, so the
    -- OPEN button and AUTO never need a scroll. Desktop (402) keeps every number below exactly as before.
    local compact = bodyH < 402
    local L = PhoneScale.eggsLayout(bodyH, false, bodyScale) -- only read when compact (numbers asserted in tools/verify_phone_scale.py)
    local fullH = math.max(402, bodyH) -- BD-1067: a tall small-width window (500 x 465) has more room than the 402 desktop body: use it, so the floored buttons never touch
    local minButton = PhoneScale.floorButton(0, bodyScale) -- a button renders >= 44 px; 52 or less on every desktop-sized canvas, so desktop numbers do not change
    local slotY = if compact then L.slotY else 32
    local nestH = if compact then L.nestH else math.clamp(touchH + 8, 96, 118)

    local nestList = ctx.nestList
    local function projected() return NestQueue.project(nestList, math.floor(workspace:GetServerTimeNow()), duration) end
    local header = label(body, EggsLogic.nestHeader(nestList, capacity), 0, 0, 220, 28, 24, C.gold)
    header.TextXAlignment = Enum.TextXAlignment.Left
    local luck = label(body, Copy.NestLine, 224, 2, 600, 26, 18) -- BD-369: says why only one nest opens at a time
    luck.TextXAlignment = Enum.TextXAlignment.Right

    -- A chunky colour tag (ChipStyle) with one short line of text (friendly timers and chips).
    local function pill(parent: GuiObject, text: string, color: Color3, x: number, y: number, w: number, h: number, size: number): (Frame, TextLabel)
        local frame = Instance.new("Frame")
        frame.Position, frame.Size, frame.ZIndex = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), parent.ZIndex + 1
        Chip.apply(frame, color, C.outline) -- BD-1077: the chunky tag (rounded rectangle, 3 px outline), never a round pill
        frame.Parent = parent
        local text = label(frame, text, 0, 0, w, h, size)
        text.TextScaled = true
        -- docs/114 s4.4 / BD-1067: shrink-to-fit text is not raised by ModalCompact's floor pass, so its largest size already renders >= 14 px
        local limit = Instance.new("UITextSizeConstraint") limit.MaxTextSize, limit.MinTextSize, limit.Parent = PhoneScale.floorText(size, bodyScale), 14, text
        return frame, text
    end

    -- Five nest slots: the occupied one shows the single-egg nest, empty ones stay dimmed. Tap READY to open.
    local slotW, gap = 156, 11
    local slotViews = {}
    for i = 1, capacity do
        local x = (i - 1) * (slotW + gap)
        local slot = button(body, "", x, slotY, slotW, nestH, C.card, function()
            local info = slotViews[i].info
            if info and info.state == "ready" then ctx.openNest(info.id)
            elseif info and info.state == "empty" then ctx.notify("Finish a run to earn a nest!", C.gold)
            elseif info then ctx.notify("Still growing. Hang tight!", C.gold) end
        end)
        slot.Name = "NestSlot" .. i
        local iconSize = if compact then nestH - 40 else nestH - 52
        local icon = box(slot, (slotW - iconSize) // 2, if compact then 2 else 4, iconSize, iconSize, C.card, slot.ZIndex + 1)
        icon.BackgroundTransparency = 1
        art(icon, "egg_nest_single", 0, 0, iconSize)
        local chip, text = pill(slot, "", C.outline, 14, if compact then nestH - 34 else nestH - 40, slotW - 28, if compact then 30 else 32, 18)
        slotViews[i] = {slot = slot, icon = icon, text = text, chip = chip}
    end

    -- Hero card: big egg on the tile floor, chips on the egg, waiting count, OPEN and AUTO.
    local cardY = if compact then L.cardY else slotY + nestH + 8
    local cardH = if compact then L.cardH else fullH - cardY
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
            local eggSize = if compact then math.clamp(side - 64, 60, 190) else math.clamp(side - 70, 110, 190) -- stage only: today's tinted egg standing on the pedestal
            egg = EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)
            egg.Position = UDim2.fromOffset((side - eggSize) // 2, math.max(4, math.floor(side * .76) - eggSize))
            if not entry then dim(egg, .6) end
        end
    else
        stage = EggPicture.stage(card, stageW, stageH, accent)
        stage.Position = UDim2.fromOffset(10, 10)
        local eggSize = if compact then math.clamp(stageH - 64, 60, 190) else math.clamp(stageH - 70, 110, 190)
        egg = EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)
        egg.Position = UDim2.fromOffset((stageW - eggSize) // 2, if compact then 6 else 14)
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
        -- Owner 2026-10-18: say what each chip is. "Egg type" = rarity, "Shell" = condition (small captions, 14 px, above the chips).
        local typeCaption = label(stage, Copy.ChipTypeCaption, 10, chipY - 18, chipW, 18, 14, C.text)
        typeCaption.Name, typeCaption.TextStrokeTransparency = "RarityCaption", .4
        typeCaption:SetAttribute("TextKind", "note") -- BD-1119: fine print (the 14 px note floor), not card text
        if conditionName then
            local conditionChip = pill(stage, conditionName, C.purple, 18 + chipW, chipY, chipW, 32, 19)
            conditionChip.Name = "ConditionChip"
            local shellCaption = label(stage, Copy.ChipShellCaption, 18 + chipW, chipY - 18, chipW, 18, 14, C.text)
            shellCaption.Name, shellCaption.TextStrokeTransparency = "ConditionCaption", .4
            shellCaption:SetAttribute("TextKind", "note")
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
    local waitingText = Copy.eggOfText(ctx.num("ActiveChestCount"), waiting) -- "Egg 1 of N": N counts the card egg (BD-369); hidden at 0
    -- BD-531 compact: row 1 holds the waiting count and the status pill side by side; the OPEN button takes the height left above AUTO.
    local rowH = if compact then L.rowH else 38
    local pillX, pillW = infoX, if entry then math.min(280, infoW) else infoW
    local pillY = if compact then 8 else 54
    if waitingText then
        local waitingLabel = label(card, waitingText, infoX, if compact then 8 else 10, if compact then 248 else infoW, rowH, if compact then 26 else 30, C.gold)
        waitingLabel.Name = "EggsWaiting"
        waitingLabel.TextXAlignment = Enum.TextXAlignment.Left
        if compact then pillX, pillW = infoX + 256, infoW - 256 end
    end
    local timerChip, timer = pill(card, statusText, if state.canOpen then C.accent else C.blue, pillX, pillY, pillW, rowH, if compact then 20 else 22)
    timerChip.Name = "EggStatusPill"
    -- BD-369: after the safe first eggs, say once in one short line that an egg can crack.
    -- Owner 2026-10-18: a Cracked shell on the card ALWAYS says it may not hatch (the one shell rule that exists); other shells say nothing.
    local isCracked = entry ~= nil and entry.genes ~= nil and entry.genes.conditionId == "cracked"
    local hintShown = isCracked or (entry ~= nil and Copy.crackedHintShown(ctx.collectionCopies(), true))
    L = PhoneScale.eggsLayout(bodyH, hintShown, bodyScale)
    local hintH = if compact then L.hintH elseif hintShown then 24 else 0
    local hintY = if compact then L.hintY else 94
    if hintShown then
        local crackedHint = label(card, if isCracked then Copy.CrackedShellLine else Copy.CrackedHint, infoX, hintY, infoW, 22, 19, C.gold)
        crackedHint.Name = "CrackedHint"
        crackedHint.TextXAlignment = Enum.TextXAlignment.Left
    end

    local gearH = if compact then L.gearH else math.max(touchH * .6, 52, minButton)
    local openY = if compact then L.openY else 106 + hintH
    local gearY = if compact then L.gearY else cardH - 14 - gearH
    local openH = if compact then L.openH else math.clamp(cardH - 106 - hintH - 14 - gearH - 14, math.max(64, minButton), math.max(96, minButton))
    local openButton = button(card, buttonText, infoX, openY, infoW, openH, if state.canOpen or state.kind == "empty" then C.accent else C.outline, function()
        state = EggsLogic.card(entry, nextId, ctx.num("NextChestReadyAt"), workspace:GetServerTimeNow(), waiting)
        if state.canOpen then ctx.openEgg()
        elseif state.kind == "growing" then ctx.notify("This egg is still growing", C.gold)
        elseif state.kind == "empty" then ctx.explore() -- BD-369: no dead end, a button to the island
        else ctx.notify("Eggs are on the way!", C.gold) end
    end)
    openButton.Name = "OpenEggButton"
    openButton.TextSize = if compact then 30 else 36
    local gear = button(card, "AUTO", infoX, gearY, 130, gearH, C.blue, function() ctx.openSettings() end)
    gear.Name = "AutoOpenSettingsButton"
    gear.TextSize = 22
    local autoLine = label(card, ctx.autoOpenText(), infoX + 142, gearY, infoW - 142, gearH, 17, C.text)
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
            timer.Text = if remaining <= 0 then Copy.ReadyStatus else "Ready in " .. UIFormat.duration(remaining)
        end
    end
    refresh()
    return refresh
end

-- BD-1067: the screen draws itself again when the window changes size (a phone turned, a Studio window dragged): the layout above is computed from
-- the visible body height and scale at draw time, so a drawing made at the old size would stay cut or overlapped. Bootstrap's resize handler only
-- re-lays the panel. The returned refresh stays valid across redraws (Bootstrap keeps it for the once-a-second timers).
function EggsScreen.render(ctx: any)
    local ModalCompact = require(script.Parent.ModalCompact)
    local gui = ctx.body:FindFirstAncestorOfClass("ScreenGui")
    local drawnH, drawnScale = ctx.bodyH or 402, ctx.bodyScale or 1
    local before: {[Instance]: boolean} = {}
    for _, child in ctx.body:GetChildren() do before[child] = true end
    local current = build(ctx, drawnH, drawnScale)
    if not gui then return function() current() end end
    local marker = Instance.new("Folder")
    marker.Name, marker.Parent = "EggsResizeWatch", ctx.body
    local pending = false
    local connection: RBXScriptConnection? = nil
    connection = gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(function()
        if not marker.Parent then
            if connection then connection:Disconnect() end
            return
        end
        if pending then return end
        pending = true
        task.defer(function() -- after Bootstrap's own resize handler has re-laid the panel
            pending = false
            if not marker.Parent then return end
            local h, s = ModalCompact.bodyHeight(), ModalCompact.bodyScale()
            if h == drawnH and s == drawnScale then return end
            drawnH, drawnScale = h, s
            for _, child in ctx.body:GetChildren() do
                if not before[child] and child ~= marker then child:Destroy() end -- only what this screen drew
            end
            current = build(ctx, h, s)
        end)
    end)
    return function() current() end
end

return EggsScreen
