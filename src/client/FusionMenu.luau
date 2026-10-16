--!strict
-- BD-065 / BD-217 Fusion Menu v2 (client, docs/96). Three columns a child reads in one
-- glance: LEFT your dinos as big cards (already filtered to the chosen tier), CENTRE the
-- 6 / 3 / 2 slots that fill on tap plus "Fill for me", RIGHT a big preview of the new dino
-- with simple odds chips and ONE big FUSE button. The server
-- (ReplicatedStorage.BeDinoRemotes.FusionAction) owns every rule, odds table, consumption
-- and roll; this module only lists, previews the exact quoted odds in plain words,
-- collects explicit consent and REVEALS the committed result. Pure decisions live in
-- Shared.FusionSelection (tested by tools/verify_fusion_ui.py). If the remote is missing
-- the menu shows "Fusion unavailable" and never errors.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Input = game:GetService("UserInputService")
local Http = game:GetService("HttpService")
local TweenService = game:GetService("TweenService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local ProgressionConfig = require(Shared.ProgressionConfig)
local EggGenetics = require(Shared.EggGenetics)
local Theme = require(Shared.UITheme)
local Preview = require(Shared.DinosaurPreview)
local Sel = require(Shared.FusionSelection)
local Sfx = require(Shared.Sfx)
local OddsCopy = require(Shared.OddsCopy)
local PreviewTraits = require(script.Parent.PreviewTraits)
local W = require(script.Parent.FusionWidgets)
local DinoDetails = require(script.Parent.DinoDetails)
local C = W.Colors
local T = W.Touch

local FusionMenu = {}
local leftInset = 0 -- px kept clear for the left nav rail
-- Client display constants (module-local by design; no Config edits).
FusionMenu.QuoteDebounce = .35
FusionMenu.RequestTimeout = 12
FusionMenu.MaxListPages = 10
FusionMenu.PageSize = 200
FusionMenu.CardBatch = 120
FusionMenu.AutoRetries = 3
FusionMenu.ReelTurns = 3
FusionMenu.ReelSeconds = 1.7

local ColourBonus = require(ReplicatedStorage.Shared.ColourBonus)
local catalog = Sel.buildCatalog(Config, ProgressionConfig, EggGenetics.Patterns)
catalog.colourBonus = function(genes) return ColourBonus.text(ProgressionConfig.EggColors, genes) end -- BD-172
local player = Players.LocalPlayer
local SlotGrid = {gold = {3, 2}, emerald = {3, 1}, diamond = {2, 1}} -- columns, rows per tier
local Dim = Color3.fromRGB(150, 150, 170)

local function remote(): RemoteFunction?
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local found = folder and folder:FindFirstChild("FusionAction")
    return if found and found:IsA("RemoteFunction") then found else nil
end
function FusionMenu.available(): boolean return remote() ~= nil end

-- InvokeServer wrapped with pcall + timeout. nil means "no answer" (retry-safe).
local function call(payload, timeout: number?)
    local fn = remote()
    if not fn then return {ok = false, reason = "unavailable"} end
    local done, response = false, nil
    task.spawn(function()
        local ok, result = pcall(function() return (fn :: RemoteFunction):InvokeServer(payload) end)
        if ok then response = result end
        done = true
    end)
    local started = os.clock()
    while not done and os.clock() - started < (timeout or FusionMenu.RequestTimeout) do task.wait(.05) end
    return response
end

-- Module-level so a confirmed-but-unanswered attempt survives closing the menu.
local pendingAttempt = nil
local fuseInFlight = false
local unseenResult = nil -- committed while the menu was closed; shown on re-open

local state = {
    open = false, mode = "browse", targetStage = "gold", dinos = {}, byId = {}, nextCursor = nil,
    listError = nil, loading = false, selection = {}, filters = {}, sortKey = "eligible", filtersOpen = false,
    visible = FusionMenu.CardBatch, quote = nil, quoteKey = nil, quoteStatus = "idle", quoteMessage = "",
    quoteSerial = 0, viewSerial = 0, acknowledged = false,
}

local gui: ScreenGui? = nil
local panel: Frame? = nil
local body: Frame? = nil
local titleLabel: TextLabel? = nil
function FusionMenu.setLeftInset(px: number)
    leftInset = math.clamp(math.floor(px), 0, 320)
    if panel then
        (panel :: Frame).Size = UDim2.new(.97, -leftInset, .95, 0)
        ;(panel :: Frame).Position = UDim2.new(0, leftInset + 6, .5, 0)
    end
end
local cards = {}
local column = {}

local function motion(): boolean return Theme.MotionEnabled ~= false end

local toastSerial = 0
local toastLabel: TextLabel? = nil
local function toast(text: string, color: Color3?)
    if not toastLabel then return end
    local label = toastLabel :: TextLabel
    toastSerial += 1
    local serial = toastSerial
    label.Text, label.TextColor3, label.Visible = text, color or C.text, true
    -- BD-334 / BD-344: the toast rides the TOP on every screen size, so it never covers Fill / Clear / FUSE at the bottom.
    label.Position = UDim2.new(.2, 0, 0, 6)
    task.delay(3.2, function() if serial == toastSerial then label.Visible = false end end)
end

local function ensureGui()
    if gui then return end
    local screen = Instance.new("ScreenGui")
    screen.Name, screen.ResetOnSpawn, screen.DisplayOrder, screen.Enabled = "BeDinoFusionUI", false, 20, false
    screen.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    pcall(function() (screen :: any).ScreenInsets = Enum.ScreenInsets.DeviceSafeInsets end)
    screen.Parent = player:WaitForChild("PlayerGui")
    local scrim = Instance.new("TextButton")
    scrim.Name, scrim.Text, scrim.AutoButtonColor, scrim.Size = "FusionScrim", "", false, UDim2.fromScale(1, 1)
    scrim.BackgroundColor3, scrim.BackgroundTransparency = Color3.new(0, 0, 0), .42
    scrim.Parent = screen
    local frame = W.box(scrim, UDim2.new(.97, -leftInset, .95, 0), UDim2.new(0, leftInset + 6, .5, 0), C.panel, 10)
    frame.Name, frame.AnchorPoint, frame.Active = "FusionPanel", Vector2.new(0, .5), true
    local limit = Instance.new("UISizeConstraint")
    limit.MaxSize, limit.Parent = Vector2.new(1180, 680), frame
    local header = W.box(frame, UDim2.new(1, -8, 0, T + 8), UDim2.fromOffset(4, 4), C.purple)
    titleLabel = W.label(header, "Fusion", UDim2.new(1, -(T * 2 + 28), 1, -8), UDim2.fromOffset(12, 4), 30, nil, true)
    W.button(header, "X", UDim2.new(0, T + 16, 0, T), UDim2.new(1, -(T + 20), 0, 4), C.red, function() FusionMenu.close() end)
    local content = Instance.new("Frame")
    content.Name, content.BackgroundTransparency, content.ClipsDescendants = "FusionBody", 1, true
    content.Size, content.Position = UDim2.new(1, -16, 1, -(T + 22)), UDim2.fromOffset(8, T + 16)
    content.Parent = frame
    local note = W.label(frame, "", UDim2.new(.6, 0, 0, 32), UDim2.new(.2, 0, 0, 6), 20)
    note.Name, note.Visible, note.BackgroundTransparency, note.BackgroundColor3 = "FusionToast", false, .15, C.outline
    note.ZIndex = 10
    toastLabel = note
    gui, panel, body = screen, frame, content
    Input.InputBegan:Connect(function(input, processed)
        if not processed and input.KeyCode == Enum.KeyCode.Escape and state.open then FusionMenu.close() end
    end)
end

local function setTitle(text: string, color: Color3?)
    if titleLabel then
        titleLabel.Text = text
        local header = titleLabel.Parent :: Frame
        header.BackgroundColor3 = color or C.purple
    end
end

local function clearBody()
    state.viewSerial += 1
    cards, column = {}, {}
    if body then (body :: Frame):ClearAllChildren() end
end

local render: () -> () = function() end

-- Data ------------------------------------------------------------------------------
local function pruneSelection()
    local kept = {}
    for _, id in state.selection do
        local d = state.byId[id]
        if d then
            local ctx = Sel.context(state.targetStage, kept, state.byId, nil)
            if Sel.ineligibility(d, ctx) == nil then table.insert(kept, id) end
        end
    end
    state.selection = kept
end

local scheduleQuote: () -> () = function() end

local function loadList(after: (() -> ())?)
    state.loading, state.listError = true, nil
    task.spawn(function()
        local all, cursor, pages = {}, nil, 0
        repeat
            local response = call({action = "list", cursor = cursor, limit = FusionMenu.PageSize})
            if type(response) ~= "table" or response.ok ~= true or type(response.dinosaurs) ~= "table" then
                state.loading = false
                state.listError = if type(response) == "table" then tostring(response.reason or "unknown") else "request_failed"
                if state.listError == "fusion_disabled" or state.listError == "unavailable" or state.listError == "identity_unavailable" or state.listError == "random_items_unavailable" then state.mode = "unavailable" end
                if state.open then render() end
                return
            end
            for _, d in response.dinosaurs do if type(d) == "table" and type(d.instanceId) == "string" then table.insert(all, d) end end
            cursor = response.nextCursor
            pages += 1
        until cursor == nil or pages >= FusionMenu.MaxListPages
        state.dinos, state.byId, state.nextCursor, state.loading = all, Sel.index(all), cursor, false
        pruneSelection()
        if after then after() end
        if state.open then render() scheduleQuote() end
    end)
end

local function currentKey(): string
    return Sel.requestKey(state.targetStage, state.selection, "")
end

local updateColumn: () -> () = function() end

scheduleQuote = function()
    state.quoteSerial += 1
    local serial = state.quoteSerial
    state.quote, state.quoteKey, state.acknowledged = nil, nil, false
    local recipe = Sel.stage(state.targetStage)
    if not recipe or not recipe.approved then
        state.quoteStatus, state.quoteMessage = "locked", Sel.LockedStageText
    elseif #state.selection ~= recipe.donorCount then
        -- Quotes are requested at EXACTLY the recipe count (6 / 3 / 2).
        state.quoteStatus = "need"
        state.quoteMessage = if #state.selection < recipe.donorCount
            then "Pick " .. (recipe.donorCount - #state.selection) .. " more to see your chances."
            else "Too many: take " .. (#state.selection - recipe.donorCount) .. " out."
    else
        state.quoteStatus, state.quoteMessage = "loading", "Working out your chances..."
        local key, donors, stage = currentKey(), table.clone(state.selection), state.targetStage
        task.delay(FusionMenu.QuoteDebounce, function()
            if serial ~= state.quoteSerial then return end
            local response = call({action = "quote", targetStage = stage, donorIds = donors})
            if serial ~= state.quoteSerial or key ~= currentKey() then return end
            if type(response) == "table" and response.ok == true and type(response.quote) == "table"
                and Sel.requestKey(stage, response.quote.donorIds or {}, "") ~= key then
                state.quoteStatus, state.quoteMessage = "error", "Something changed. Please pick again."
            elseif type(response) == "table" and response.ok == true and type(response.quote) == "table" then
                local formatted = Sel.formatOdds(response.quote.odds, catalog)
                if formatted.ok then
                    state.quote, state.quoteKey, state.quoteStatus = response.quote, key, "ready"
                    state.quoteMessage = ""
                else
                    state.quoteStatus, state.quoteMessage = "error", "Chances could not be read (" .. tostring(formatted.error) .. "). Fusion is paused until they can."
                end
            else
                local reason = if type(response) == "table" then response.reason else "request_failed"
                state.quoteStatus, state.quoteMessage = "error", Sel.failureMessage(reason)
                if reason == "fusion_disabled" or reason == "unavailable" then state.mode = "unavailable" render() return end
                if reason == "donor_missing" or reason == "donor_locked" or reason == "stale_quote" then
                    loadList()
                end
            end
            if state.open and state.mode == "browse" then updateColumn() end
        end)
    end
    if state.open and state.mode == "browse" then updateColumn() end
end

-- Browse screen ----------------------------------------------------------------------
local function filterValueName(field: string, value): string
    if value == nil then return "All" end
    if field == "speciesId" then return Sel.name(catalog, "species", value) end
    if field == "patternId" then return Sel.name(catalog, "patterns", value) end
    if field == "colorId" then return Sel.name(catalog, "colors", value) end
    if field == "mutationId" then return if value == "none" then "None" else Sel.name(catalog, "mutations", value) end
    if field == "shiny" or field == "big" then return if value then "Yes" else "No" end
    if field == "originKind" then return ({hatch = "Hatched", fusion = "Fused", legacy_unknown = "Older"})[value] or tostring(value) end
    if field == "cosmetics" then return ({has = "Has effects", none = "No effects", equipped = "Wearing"})[value] or tostring(value) end
    return tostring(value)
end
local FilterLabels = {speciesId = "Dino", patternId = "Pattern", colorId = "Colour",
    shiny = "Shiny", big = "BIG", mutationId = "Mutation", originKind = "From", cosmetics = "Effects"}
-- Stage is chosen by the tier tabs, so it is not a chip.
local FilterChips = {"speciesId", "patternId", "colorId", "shiny", "big", "mutationId", "originKind", "cosmetics"}

local function speciesName(d): string return Sel.name(catalog, "species", d.speciesId, "Dino") end

local function cardLook(d)
    local entry = cards[d.instanceId]
    if not entry then return end
    local at = table.find(state.selection, d.instanceId)
    local ctx = Sel.context(state.targetStage, state.selection, state.byId, state.filters)
    local reason = if at then nil else Sel.ineligibility(d, ctx)
    local valuable = #Sel.valuableReasons(d) > 0
    entry.stroke.Color = if at then (if valuable then C.purple else C.accent) else C.outline
    entry.stroke.Thickness = if at then 5 else 3
    entry.button.BackgroundColor3 = if reason then C.outline else C.card
    entry.status.Text = if at then "In slot " .. at .. (if valuable then " (Special)" else "")
        elseif reason then (Sel.ReasonText[reason] or reason)
        elseif valuable then "Special! Tap" else "Tap to add"
    entry.status.TextColor3 = if at then C.accent elseif reason then C.red elseif valuable then C.purple else C.text
    entry.tick.Visible = at ~= nil
    entry.tick.Text = if at then tostring(at) else ""
    entry.dim.Visible = reason ~= nil
end

local function refreshCards()
    for _, d in state.dinos do cardLook(d) end
end

local openDetails: (string) -> () = function() end

local function toggle(d)
    local nextSelection, ok, reason = Sel.toggle(state.selection, d, state.targetStage, state.byId)
    if not ok then toast(Sel.ReasonText[reason] or tostring(reason), C.red) return end
    state.selection = nextSelection
    Sfx.play("ui_click")
    refreshCards()
    scheduleQuote()
end

local function buildGrid(grid: ScrollingFrame)
    for _, child in grid:GetChildren() do if not child:IsA("UIGridLayout") then child:Destroy() end end
    cards = {}
    local ctx = Sel.context(state.targetStage, state.selection, state.byId, state.filters)
    local list = Sel.sort(Sel.visibleFor(state.dinos, state.targetStage, state.filters), state.sortKey, ctx, Sel.selectedSet(state.selection), catalog)
    for i, d in list do
        if i > state.visible then
            local more = W.button(grid, "Show more (" .. (#list - state.visible) .. ")", UDim2.new(), UDim2.new(), C.blue, function()
                state.visible += FusionMenu.CardBatch
                buildGrid(grid)
            end)
            more.LayoutOrder = i
            break
        end
        local g = d.genes or {}
        local card = Instance.new("TextButton")
        card.Name, card.Text, card.AutoButtonColor, card.LayoutOrder = "Dino_" .. i, "", false, i
        card.BackgroundColor3 = C.card
        Theme.decorate(card, 10)
        card.Parent = grid
        card.Activated:Connect(function() toggle(d) end)
        -- Big picture first: the real dino (lazy, culled by DinosaurPreview) with its colours.
        local view = Preview.add(card, d.speciesId or "compy", if d.stage == "base" or d.stage == nil then "base" else d.stage)
        view.Size, view.Position = UDim2.new(1, -8, .44, 0), UDim2.new(0, 4, 0, 28)
        PreviewTraits.add(view, {genes = (Sel.previewTraits(d) or {}).genes})
        W.label(card, speciesName(d), UDim2.new(1, -44, 0, 26), UDim2.fromOffset(38, 2), 22)
        W.label(card, Sel.cardPattern(d, catalog), UDim2.new(1, -8, 0, 20), UDim2.new(0, 4, .44, 30), 17, C.gold)
        W.swatch(card, g, UDim2.new(1, -16, 0, 8), UDim2.new(0, 8, .44, 52))
        local traits = Sel.cardTraits(d, catalog)
        W.label(card, table.concat(traits, " • "), UDim2.new(1, -8, 0, 20), UDim2.new(0, 4, .44, 62), 16, C.purple)
        local status = W.label(card, "", UDim2.new(1, -(T + 10), 0, 46), UDim2.new(0, 4, 1, -50), 18)
        local info = W.button(card, "i", UDim2.fromOffset(T, T), UDim2.new(1, -(T + 2), 1, -(T + 2)), C.blue, function() openDetails(d.instanceId) end)
        info.Name = "Details"
        local dim = Instance.new("Frame")
        dim.Name, dim.Size, dim.BackgroundColor3, dim.BackgroundTransparency, dim.BorderSizePixel = "Dim", UDim2.fromScale(1, 1), C.outline, .55, 0
        dim.ZIndex, dim.Visible, dim.Parent = card.ZIndex + 3, false, card
        local tick = W.label(card, "", UDim2.fromOffset(30, 30), UDim2.fromOffset(4, 4), 18, C.outline)
        tick.Name, tick.BackgroundTransparency, tick.BackgroundColor3, tick.ZIndex, tick.Visible = "Tick", 0, C.accent, card.ZIndex + 4, false
        Theme.decorate(tick, 15)
        local stroke = card:FindFirstChildOfClass("UIStroke") :: UIStroke
        cards[d.instanceId] = {button = card, stroke = stroke, status = status, tick = tick, dim = dim}
        cardLook(d)
    end
    if #list == 0 then
        local recipe = Sel.stage(state.targetStage)
        local text = if state.loading then "Loading your dinos..."
            elseif next(state.filters) ~= nil then "No dinos match. Tap Filter to clear."
            else "No " .. (if recipe then Sel.stageTitle(recipe.source) else "") .. " dinos yet. Hatch more eggs!"
        local empty = W.label(grid, text, UDim2.new(), UDim2.new(), 20, C.gold)
        empty.LayoutOrder = 0
    end
end

-- QA 2026-10-16: on phone landscape the picture shares the column with the odds chips; give the chips more room.
local function resultRatio(): number
    local camera = if workspace then workspace.CurrentCamera else nil
    return if camera and camera.ViewportSize.Y < 520 then .27 else .4
end

-- Result preview (right column): big picture of the new dino + name + guarantee line.
local function resultBox(parent: Frame, speciesId: string?, stageId: string, traits, big: boolean)
    local recipe = Sel.stage(stageId)
    local box = W.box(parent, UDim2.new(1, 0, if big then .62 else resultRatio(), 0), UDim2.new(), W.StageColors[stageId] or C.gold, 10)
    box.Name = "Result"
    local badge = W.label(box, "NEW " .. string.upper(if recipe then recipe.name else stageId), UDim2.new(.6, 0, 0, 26), UDim2.fromOffset(6, 4), 20, C.outline)
    badge.Name, badge.BackgroundTransparency, badge.BackgroundColor3, badge.ZIndex = "Badge", 0, C.text, box.ZIndex + 2
    Theme.decorate(badge, 13)
    if speciesId then
        local view = Preview.add(box, speciesId, stageId)
        view.Size, view.Position = UDim2.new(1, -8, 1, -62), UDim2.fromOffset(4, 30)
        PreviewTraits.add(view, traits)
        local who = Sel.name(catalog, "species", speciesId, "Dino")
        W.label(box, (if recipe then recipe.name else "") .. " " .. who, UDim2.new(1, -8, 0, 26), UDim2.new(0, 4, 1, -30), 22, C.text)
    else
        W.label(box, "?", UDim2.new(1, 0, 1, -60), UDim2.fromOffset(0, 30), 80, C.outline)
        W.label(box, "Your new dino", UDim2.new(1, -8, 0, 26), UDim2.new(0, 4, 1, -30), 22, C.text)
    end
    return box
end

-- Odds as headed sections (BD-344): "Colour 1" / "Colour 2" / "Pattern" / "Shiny" / "Event" / "BIG", each a heading
-- over its own wrapping chips, exact server numbers. Section heights come from Sel.sectionHeight so nothing overflows.
local function viewportSize(): Vector2
    local camera = if workspace then workspace.CurrentCamera else nil -- the offline smoke mock has no workspace
    return if camera then camera.ViewportSize else Vector2.new(1280, 720)
end
local function panelWidth(): number
    return math.min(1180, viewportSize().X * .97 - leftInset) - 16
end
FusionMenu.ChipMinWidth = 84
local function oddsSections(parent: Instance, odds, patternId: string?, width: number): number
    local formatted = Sel.oddsChips(odds, catalog, patternId)
    local columns = Sel.chipColumns(width, FusionMenu.ChipMinWidth)
    local total = 0
    local list = W.list(parent, 4)
    for index, section in formatted.sections do
        local height = Sel.sectionHeight(#section.chips, columns)
        total += height + 4
        local holder = Instance.new("Frame")
        holder.Name, holder.BackgroundTransparency, holder.LayoutOrder = "Section_" .. section.trait, 1, index
        holder.Size = UDim2.new(1, -6, 0, height)
        holder.Parent = parent
        local heading = W.label(holder, section.title, UDim2.new(1, 0, 0, Sel.ChipHeadingHeight - 2), UDim2.new(), 18, C.gold, true)
        heading.Name = "Heading"
        local grid = Instance.new("Frame")
        grid.Name, grid.BackgroundTransparency = "Chips", 1
        grid.Size, grid.Position = UDim2.new(1, 0, 1, -Sel.ChipHeadingHeight), UDim2.fromOffset(0, Sel.ChipHeadingHeight)
        grid.Parent = holder
        local layout = Instance.new("UIGridLayout")
        layout.CellSize, layout.CellPadding, layout.SortOrder = UDim2.new(1 / columns, -Sel.ChipGap, 0, Sel.ChipHeight), UDim2.fromOffset(Sel.ChipGap, Sel.ChipGap), Enum.SortOrder.LayoutOrder
        layout.Parent = grid
        for order, chip in section.chips do
            local c = W.label(grid, chip.label, UDim2.new(), UDim2.new(), 17, C.text)
            c.Name, c.BackgroundTransparency, c.LayoutOrder = "Chip", 0, order
            c.BackgroundColor3 = if section.trait == "primaryColor" or section.trait == "secondaryColor" then W.colorOf(chip.id) else C.card
            if (section.trait == "shiny" or section.trait == "big") and chip.id == "yes" then c.BackgroundColor3 = C.purple end
            if section.trait == "mutation" and chip.id ~= "none" then c.BackgroundColor3 = C.purple end
            if section.trait == "pattern" then c.BackgroundColor3 = C.blue end
            Theme.decorate(c, 12)
        end
    end
    return total
end

updateColumn = function()
    local col = column
    if not col.slots then return end
    for _, child in col.slots:GetChildren() do if not child:IsA("UIGridLayout") then child:Destroy() end end
    local recipe = Sel.stage(state.targetStage)
    local need = (recipe and recipe.donorCount) or 0
    local first = state.selection[1] and state.byId[state.selection[1]]
    for i = 1, need do
        local id = state.selection[i]
        local d = id and state.byId[id]
        if d then
            local slot = W.button(col.slots, "", UDim2.new(), UDim2.new(), if #Sel.valuableReasons(d) > 0 then C.purple else C.card, function() toggle(d) end)
            slot.Name, slot.LayoutOrder = "Slot_" .. i, i
            local view = Preview.add(slot, d.speciesId or "compy", if d.stage == "base" or d.stage == nil then "base" else d.stage)
            view.Size, view.Position = UDim2.new(1, -4, 1, -22), UDim2.fromOffset(2, 2)
            PreviewTraits.add(view, {genes = (Sel.previewTraits(d) or {}).genes})
            W.swatch(slot, d.genes, UDim2.new(1, -8, 0, 6), UDim2.new(0, 4, 1, -12))
            W.label(slot, "x", UDim2.fromOffset(28, 28), UDim2.new(1, -30, 0, 2), 22, C.red)
        else
            local empty = W.box(col.slots, UDim2.new(), UDim2.new(), C.outline, 8)
            empty.Name, empty.LayoutOrder = "Empty_" .. i, i
            W.label(empty, tostring(i), UDim2.fromScale(1, 1), UDim2.new(), 40, Dim)
        end
    end
    col.count.Text = string.format("%d of %d", #state.selection, need)
    col.goal.Text = Sel.goalText(state.dinos, state.targetStage, state.selection, state.byId, catalog)
    -- Right column: result preview + chips + FUSE.
    local right = col.right :: Frame
    for _, child in right:GetChildren() do if child.Name ~= "Fuse" then child:Destroy() end end
    local ready = state.quoteStatus == "ready" and state.quote ~= nil and state.quoteKey == currentKey()
    local speciesId = if state.quote then state.quote.speciesId else (if first then first.speciesId else nil)
    resultBox(right, speciesId, state.targetStage, nil, false)
    local guarantee = W.label(right, if recipe and recipe.approved then "Guaranteed: " .. recipe.name .. "!" else Sel.LockedStageText, UDim2.new(1, 0, 0, 28), UDim2.new(0, 0, resultRatio(), 4), 22, C.accent)
    guarantee.Name = "Guarantee"
    local chips = Instance.new("ScrollingFrame")
    chips.Name, chips.BackgroundTransparency, chips.BorderSizePixel = "Odds", 1, 0
    chips.Size, chips.Position = UDim2.new(1, 0, 1 - resultRatio(), -(T + 70)), UDim2.new(0, 0, resultRatio(), 34)
    chips.ScrollBarThickness, chips.AutomaticCanvasSize, chips.CanvasSize = 4, Enum.AutomaticSize.Y, UDim2.new()
    chips.Parent = right
    if ready then
        oddsSections(chips, (state.quote :: any).odds, (state.quote :: any).patternId, panelWidth() * .34 - 18)
    else
        local msg = W.label(chips, state.quoteMessage, UDim2.new(1, -6, 0, 56), UDim2.new(), 18, if state.quoteStatus == "error" then C.red else C.gold)
        msg.Name = "Message"
    end
    -- BD-347: a calm line next to FUSE; the details line lives in the odds panel (OddsCopy.fusionDetails, shown on confirm).
    local calm = W.label(right, OddsCopy.fusionCalm, UDim2.new(1, 0, 0, 22), UDim2.new(0, 0, 1, -(T + 34)), 17, Dim)
    calm.Name = "OddsNote"
    col.fuse.BackgroundColor3 = if ready then C.accent else C.card
    col.fuse.Text = if ready then "FUSE!" elseif #state.selection < need then "Pick " .. (need - #state.selection) .. " more" else "FUSE"
end

local function renderBrowse()
    local active = Sel.stage(state.targetStage)
    setTitle(if active then "Make " .. Sel.article(active.name) .. " " .. active.name .. " dino" else "Fusion", W.StageColors[state.targetStage] or C.purple)
    local root = body :: Frame
    local left = Instance.new("Frame")
    left.Name, left.BackgroundTransparency, left.Size, left.Parent = "Browse", 1, UDim2.new(.38, -6, 1, 0), root
    local centre = W.box(root, UDim2.new(.28, -6, 1, 0), UDim2.new(.38, 3, 0, 0), C.card, 10)
    centre.Name = "Ingredients"
    local right = Instance.new("Frame")
    right.Name, right.BackgroundTransparency, right.Size, right.Position, right.Parent = "ResultColumn", 1, UDim2.new(.34, -6, 1, 0), UDim2.new(.66, 6, 0, 0), root
    -- Row 1: three big tier tabs.
    local tabHeight = T + 12
    for i, s in Sel.Stages do
        local words = Sel.tabText(s.id)
        local on = state.targetStage == s.id
        local b = W.button(left, "", UDim2.new(1 / 3, -4, 0, tabHeight), UDim2.new((i - 1) / 3, 0, 0, 0),
            if on then (W.StageColors[s.id] or C.gold) else C.card, function()
                if state.targetStage == s.id then return end
                state.targetStage = s.id
                if not s.approved then toast(words.title .. ": " .. Sel.LockedStageText, C.gold) end
                state.selection, state.visible = {}, FusionMenu.CardBatch
                render()
                scheduleQuote()
            end)
        b.Name = "Stage_" .. s.id
        W.label(b, words.title, UDim2.new(1, -4, 0, 26), UDim2.fromOffset(2, 2), 22, if on then C.outline else C.text)
        W.label(b, words.sub, UDim2.new(1, -4, 0, 20), UDim2.fromOffset(2, 28), 16, if on then C.outline else Dim)
    end
    -- Row 2: goal sentence + one Filter button.
    local y = tabHeight + 6
    column.goal = W.label(left, "", UDim2.new(1, -(T + 48), 0, T), UDim2.fromOffset(0, y), 20, C.gold, true)
    column.goal.Name = "Goal"
    local filterOn = state.filtersOpen or next(state.filters) ~= nil
    W.button(left, "Filter", UDim2.fromOffset(T + 40, T), UDim2.new(1, -(T + 40), 0, y), if filterOn then C.blue else C.card, function()
        state.filtersOpen = not state.filtersOpen
        render()
    end).Name = "Filter"
    y += T + 6
    if state.filtersOpen then
        -- Chips (tap to cycle, scroll sideways) live behind the Filter button.
        local chips = Instance.new("ScrollingFrame")
        chips.Name, chips.BackgroundTransparency, chips.BorderSizePixel = "Filters", 1, 0
        chips.Size, chips.Position, chips.ScrollingDirection = UDim2.new(1, 0, 0, T + 8), UDim2.fromOffset(0, y), Enum.ScrollingDirection.X
        chips.ScrollBarThickness, chips.AutomaticCanvasSize, chips.CanvasSize = 4, Enum.AutomaticSize.X, UDim2.new()
        chips.Parent = left
        W.list(chips, 6, true)
        local options = Sel.filterOptions(state.dinos, catalog)
        W.button(chips, "Sort: " .. Sel.SortNames[state.sortKey], UDim2.fromOffset(150, T), UDim2.new(), C.purple, function()
            local i = table.find(Sel.SortKeys, state.sortKey) or 1
            state.sortKey = Sel.SortKeys[i % #Sel.SortKeys + 1]
            render()
        end).LayoutOrder = 0
        for i, field in FilterChips do
            local value = state.filters[field]
            local chip = W.button(chips, FilterLabels[field] .. ": " .. filterValueName(field, value), UDim2.fromOffset(150, T), UDim2.new(),
                if value ~= nil then C.blue else C.card, function()
                    state.filters[field] = Sel.cycle(options[field] or {}, state.filters[field])
                    state.visible = FusionMenu.CardBatch
                    render()
                end)
            chip.LayoutOrder = i
        end
        local reset = W.button(chips, "Clear", UDim2.fromOffset(84, T), UDim2.new(), C.red, function()
            state.filters, state.visible, state.filtersOpen = {}, FusionMenu.CardBatch, false
            render()
        end)
        reset.LayoutOrder = #FilterChips + 1
        y += T + 12
    end
    -- Grid of big dino cards.
    local grid = W.scroll(left, UDim2.new(1, 0, 1, -y), UDim2.fromOffset(0, y))
    grid.Name = "DinoGrid"
    local layout = Instance.new("UIGridLayout")
    -- QA 2026-10-16: the ScreenGui is not laid out yet when this runs, so read the camera viewport. 1080x720 gets two
    -- columns that fill the lane (was one 176 px card and a wasted gap); phone landscape gets one wide, shorter card.
    local camera = if workspace then workspace.CurrentCamera else nil -- the offline smoke mock has no workspace
    local view = if camera then camera.ViewportSize else Vector2.new(1280, 720)
    if view.Y < 520 then layout.CellSize = UDim2.new(1, -10, 0, 200)
    elseif view.X < 1300 then layout.CellSize = UDim2.new(.5, -8, 0, 224)
    else layout.CellSize = UDim2.fromOffset(176, 232) end
    layout.CellPadding, layout.SortOrder = UDim2.fromOffset(6, 6), Enum.SortOrder.LayoutOrder
    layout.Parent = grid
    if state.listError and state.mode == "browse" then
        W.label(grid, "Could not load dinos: " .. Sel.failureMessage(state.listError), UDim2.new(), UDim2.new(), 20, C.red)
        W.button(grid, "Try again", UDim2.new(), UDim2.new(), C.blue, function() loadList() render() end)
    else
        buildGrid(grid)
    end
    -- Centre column: slots, Fill for me, Clear.
    local need = (active and active.donorCount) or 0
    local cols, rows = table.unpack(SlotGrid[state.targetStage] or {3, 2})
    W.label(centre, if active then "Put in " .. need .. " " .. Sel.stageTitle(active.source) else "", UDim2.new(1, -110, 0, 30), UDim2.fromOffset(8, 2), 22, C.text, true)
    column.count = W.label(centre, "", UDim2.fromOffset(100, 30), UDim2.new(1, -106, 0, 2), 22, C.gold)
    column.count.Name = "SlotCount"
    local slots = Instance.new("Frame")
    slots.Name, slots.BackgroundTransparency, slots.Size, slots.Position = "Slots", 1, UDim2.new(1, -12, 1, -(T + 50)), UDim2.fromOffset(6, 36)
    slots.Parent = centre
    local slotLayout = Instance.new("UIGridLayout")
    slotLayout.CellSize = UDim2.new(1 / cols, -6, 1 / rows, -6)
    slotLayout.CellPadding, slotLayout.SortOrder = UDim2.fromOffset(6, 6), Enum.SortOrder.LayoutOrder
    slotLayout.HorizontalAlignment, slotLayout.VerticalAlignment = Enum.HorizontalAlignment.Center, Enum.VerticalAlignment.Center
    slotLayout.Parent = slots
    column.slots = slots
    W.button(centre, "Fill for me", UDim2.new(.62, -8, 0, T), UDim2.new(0, 6, 1, -(T + 6)), C.accent, function()
        -- BD-346: never swallowed. While the list is refreshing say so; otherwise always answer with what was added or why not.
        if state.loading then toast("One moment...", C.gold) return end
        local before = state.selection
        local filled = Sel.autoFill(state.dinos, before, state.targetStage, state.filters, catalog)
        state.selection = filled
        local message = Sel.autoFillMessage(state.dinos, before, filled, state.targetStage, state.byId, catalog)
        toast(message, if #filled > #before then C.accent else C.gold)
        refreshCards()
        scheduleQuote()
    end).Name = "AutoFill"
    W.button(centre, "Clear", UDim2.new(.38, -8, 0, T), UDim2.new(.62, 2, 1, -(T + 6)), C.red, function()
        state.selection = {}
        refreshCards()
        scheduleQuote()
    end).Name = "Clear"
    -- Right column: result, chips, FUSE.
    column.right = right
    column.fuse = W.button(right, "FUSE", UDim2.new(1, 0, 0, T + 8), UDim2.new(0, 0, 1, -(T + 8)), C.card, function()
        local ready = state.quoteStatus == "ready" and state.quote ~= nil and state.quoteKey == currentKey()
        if not ready then
            toast(if state.quoteStatus == "loading" then "One moment..." else state.quoteMessage, C.gold)
            return
        end
        state.mode, state.acknowledged = "confirm", false
        render()
    end)
    column.fuse.Name = "Fuse"
    updateColumn()
end

-- Confirmation -------------------------------------------------------------------
local runFuse: (any) -> () = function() end

local function donorLine(d): string
    local traits = Sel.cardTraits(d, catalog)
    return Sel.cardPattern(d, catalog) .. " " .. speciesName(d) .. (if #traits > 0 then " • " .. table.concat(traits, ", ") else "")
end

local function renderConfirm()
    local quote = state.quote
    if not quote or state.quoteKey ~= currentKey() then state.mode = "browse" render() return end
    local recipe = Sel.stage(quote.targetStage or state.targetStage)
    local stageName = if recipe then recipe.name else "?"
    local donorTotal = #(quote.donorIds or state.selection)
    local who = Sel.name(catalog, "species", quote.speciesId, "Dino")
    setTitle("Fuse " .. donorTotal .. " " .. who .. "?", C.gold)
    local root = body :: Frame
    local loss = Sel.lossSummary(quote, catalog)
    -- Left: the new dino. Right: what goes away + chances.
    local left = Instance.new("Frame")
    left.Name, left.BackgroundTransparency, left.Size, left.Parent = "ConfirmResult", 1, UDim2.new(.34, -6, 1, -(T + 38)), root
    resultBox(left, quote.speciesId, quote.targetStage or state.targetStage, nil, true)
    W.label(left, "Guaranteed: " .. stageName .. " " .. who .. "!", UDim2.new(1, 0, 0, 26), UDim2.new(0, 0, .62, 4), 20, C.accent)
    W.label(left, "Pattern: " .. Sel.name(catalog, "patterns", quote.patternId), UDim2.new(1, 0, 0, 24), UDim2.new(0, 0, .62, 32), 18, C.gold)
    W.label(left, "Colours, Shiny, BIG and mutation are rolled new.", UDim2.new(1, 0, 0, 44), UDim2.new(0, 0, .62, 56), 17, C.text)
    local list = W.scroll(root, UDim2.new(.66, -6, 1, -(T + 38)), UDim2.new(.34, 6, 0, 0))
    W.list(list, 3)
    local order = 0
    local function line(text: string, color: Color3?, height: number?)
        order += 1
        local l = W.label(list, text, UDim2.new(1, -14, 0, height or (if #text > 70 then 48 else 26)), UDim2.new(), 20, color, true)
        l.LayoutOrder = order
    end
    line("All " .. donorTotal .. " dinos go away. You get 1 new " .. stageName .. " " .. who .. ".", C.red, 30)
    for i, id in quote.donorIds or state.selection do
        local d = state.byId[id]
        line(i .. ". " .. (if d then donorLine(d) else id), if d and #Sel.valuableReasons(d) > 0 then C.purple else nil)
    end
    line(loss.cosmeticText, if loss.auraCount + loss.trailCount > 0 then C.red else C.text, 48)
    if #loss.valuables > 0 then
        local parts = {}
        for _, v in loss.valuables do
            local d = state.byId[v.instanceId]
            table.insert(parts, (if d then speciesName(d) else "Dino") .. " (" .. v.text .. ")")
        end
        line("Special dinos going away: " .. table.concat(parts, ", "), C.purple, 48)
    end
    line("Your chances:", C.blue)
    local chips = Instance.new("Frame")
    chips.Name, chips.BackgroundTransparency, chips.LayoutOrder = "Odds", 1, order + 1
    local oddsWidth = panelWidth() * .66 - 40
    local sectionTotal = 0
    for _, section in Sel.oddsChips(quote.odds, catalog, quote.patternId).sections do
        sectionTotal += Sel.sectionHeight(#section.chips, Sel.chipColumns(oddsWidth, FusionMenu.ChipMinWidth)) + 4
    end
    chips.Size = UDim2.new(1, -14, 0, sectionTotal)
    chips.Parent = list
    oddsSections(chips, quote.odds, quote.patternId, oddsWidth)
    order += 1
    -- BD-347: the odds panel says plainly that this version of fusion costs no real money.
    line(OddsCopy.fusionDetails, Dim, 44)
    -- docs/72: no version strings for children (the quote still carries them for the server ledger).
    line("The wheels only show the result that is already saved.", Dim, 24)
    local needs = loss.needsConfirm
    local y = UDim2.new(0, 0, 1, -(T + 6))
    local calm = W.label(root, OddsCopy.fusionCalm, UDim2.new(.7, 0, 0, 20), UDim2.new(.3, 0, 1, -(T + 30)), 16, Dim)
    calm.Name = "OddsNote"
    W.button(root, "Not now", UDim2.new(.3, -6, 0, T + 4), y, C.red, function() state.mode = "browse" render() end)
    if needs and not state.acknowledged then
        W.button(root, "I understand: " .. (loss.auraCount + loss.trailCount) .. " effects + " .. #loss.valuables .. " special dinos go away", UDim2.new(.7, 0, 0, T + 4), UDim2.new(.3, 0, 1, -(T + 6)), C.gold, function()
            state.acknowledged = true
            render()
        end).Name = "Acknowledge"
    else
        W.button(root, "FUSE! (" .. donorTotal .. " go away)", UDim2.new(.7, 0, 0, T + 4), UDim2.new(.3, 0, 1, -(T + 6)), C.accent, function()
            if state.quoteKey ~= currentKey() then state.mode = "browse" render() return end
            local attempt = Sel.attempt(pendingAttempt, state.targetStage, quote.donorIds or state.selection, quote.quoteDigest, function()
                return Http:GenerateGUID(false)
            end)
            attempt.consentDigest = if quote.consentRequired then quote.consentDigest else nil
            attempt.quote = quote
            pendingAttempt = attempt
            runFuse(attempt)
        end).Name = "FuseNow"
    end
end

-- Fuse + retries -----------------------------------------------------------------
local startReveal: (any, any, string) -> () = function() end

local function renderStatus(text: string, color: Color3?, buttons)
    clearBody()
    local root = body :: Frame
    W.label(root, text, UDim2.new(1, -40, .5, 0), UDim2.fromScale(0, .1) + UDim2.fromOffset(20, 0), 28, color or C.gold)
    for i, b in buttons or {} do
        W.button(root, b[1], UDim2.new(.3, 0, 0, T + 8), UDim2.new(.02 + (i - 1) * .34, 0, .7, 0), b[2], b[3]).Name = b[4] or b[1]
    end
end

runFuse = function(attempt)
    if fuseInFlight then return end
    fuseInFlight = true
    state.mode = "fusing"
    setTitle("Fusing...", C.gold)
    renderStatus("Fusing your " .. #attempt.donorIds .. " dinos...\nThis is saved: trying again can never fuse twice.", C.gold)
    task.spawn(function()
        local tries = 0
        while true do
            tries += 1
            local response = call({action = "fuse", token = attempt.token, targetStage = attempt.targetStage,
                donorIds = attempt.donorIds, quoteDigest = attempt.quoteDigest, consentDigest = attempt.consentDigest})
            local outcome = Sel.settle(attempt, response)
            if outcome.kind == "success" then
                fuseInFlight = false
                pendingAttempt = nil
                state.dinos = Sel.withoutIds(state.dinos, attempt.donorIds)
                state.byId = Sel.index(state.dinos)
                state.selection = {}
                if state.open then startReveal(attempt.quote, outcome.result, outcome.status)
                else unseenResult = outcome.result end
                loadList()
                return
            elseif outcome.kind == "retry" and tries < FusionMenu.AutoRetries and outcome.reason ~= "lease_lost" then
                if state.open then renderStatus(outcome.message .. "\n(try " .. (tries + 1) .. ")", C.gold) end
                task.wait(2 ^ tries)
            elseif outcome.kind == "retry" then
                fuseInFlight = false
                if not state.open then state.mode = "browse" return end
                renderStatus(outcome.message, C.red, {
                    {"Try again", C.accent, function() runFuse(attempt) end, "Retry"},
                    {"Back", C.blue, function() state.mode = "browse" loadList() render() end, "Back"},
                })
                return
            else
                fuseInFlight = false
                pendingAttempt = nil
                state.mode = if outcome.reason == "fusion_disabled" then "unavailable" else "browse"
                if state.open then render() toast(outcome.message, C.red) end
                if outcome.kind == "requote" then loadList() end
                return
            end
        end
    end)
end

-- Reveal ---------------------------------------------------------------------------
local reelPalette = {C.blue, C.purple, C.accent, C.gold, Color3.fromRGB(255, 120, 80), Color3.fromRGB(110, 120, 150)}
local RevealTitles = {primaryColor = "Colour 1", secondaryColor = "Colour 2", shiny = "Shiny?", mutation = "Mutation?", big = "BIG?"}

-- BD-346: Shiny / BIG as a readable bar. YES share on the left, NO share on the right, the words UNDER the bar and the
-- marker only over the bar, so nothing crosses a label. The result is the server's committed one (Sel.chanceBar reads it);
-- under Reduce Motion the marker simply sits on its answer.
local function chanceBar(parent: Instance, stage, animate: boolean, name: string)
    local bar = Sel.chanceBar(stage)
    local frame = W.box(parent, UDim2.new(1, -40, 0, 46), UDim2.new(0, 20, .34, 0), C.card, 8)
    frame.Name = "ChanceBar"
    local yes = W.box(frame, UDim2.fromScale(math.max(bar.yesShare, .02), 1), UDim2.new(), C.purple, 8)
    yes.Name = "YesPart"
    local no = W.box(frame, UDim2.fromScale(math.max(1 - bar.yesShare, .02), 1), UDim2.fromScale(math.max(bar.yesShare, .02), 0), C.outline, 8)
    no.Name = "NoPart"
    local yesWords = W.label(parent, "Yes " .. Sel.pct(bar.yesShare), UDim2.new(.5, -24, 0, 24), UDim2.new(0, 20, .34, 70), 20, C.purple, true)
    yesWords.Name = "YesWords"
    local noWords = W.label(parent, "No " .. Sel.pct(1 - bar.yesShare), UDim2.new(.5, -24, 0, 24), UDim2.new(.5, 4, .34, 70), 20, Dim)
    noWords.TextXAlignment, noWords.Name = Enum.TextXAlignment.Right, "NoWords"
    local marker = Instance.new("Frame")
    marker.Name, marker.BorderSizePixel, marker.BackgroundColor3 = "Marker", 0, C.gold
    marker.AnchorPoint, marker.Size = Vector2.new(.5, .5), UDim2.new(0, 8, 1, 14)
    marker.Position = UDim2.fromScale(if animate then 0 else bar.marker, .5)
    marker.ZIndex, marker.Parent = frame.ZIndex + 5, frame
    if animate then
        TweenService:Create(marker, TweenInfo.new(FusionMenu.ReelSeconds, Enum.EasingStyle.Quint, Enum.EasingDirection.Out), {Position = UDim2.fromScale(bar.marker, .5)}):Play()
    end
    local outcome = W.label(parent, "", UDim2.new(1, -40, 0, 52), UDim2.new(0, 20, .34, 104), 36, if bar.landedYes then C.accent else Dim)
    outcome.Name = "Outcome"
    local function show()
        if outcome.Parent then outcome.Text = bar.outcome .. (if bar.landedYes then "  " .. name else "") end
    end
    if animate then task.delay(FusionMenu.ReelSeconds, show) else show() end
end

local function reel(parent: Instance, stage, animate: boolean)
    local frame = W.box(parent, UDim2.new(1, -24, 0, 70), UDim2.new(0, 12, .34, 0), C.outline, 6)
    frame.ClipsDescendants, frame.Name = true, "Reel"
    local strip = Instance.new("Frame")
    strip.BackgroundTransparency, strip.Size, strip.Position, strip.Parent = 1, UDim2.fromScale(1, 1), UDim2.fromScale(.5, 0), frame
    local unit = 1.5
    local total = 0
    for _, seg in stage.segments do total = math.max(total, seg.to) end
    for k = 0, FusionMenu.ReelTurns + 1 do
        for i, seg in stage.segments do
            if seg.p > 0 then
                local block = Instance.new("Frame")
                block.BorderSizePixel = 0
                block.Position = UDim2.fromScale((k + seg.from / total) * unit, 0)
                block.Size = UDim2.fromScale(seg.p / total * unit, 1)
                block.BackgroundColor3 = if stage.trait == "primaryColor" or stage.trait == "secondaryColor" then W.colorOf(seg.id) else reelPalette[(i - 1) % #reelPalette + 1]
                local edge = Instance.new("UIStroke")
                edge.Color, edge.Thickness, edge.Parent = C.outline, 2, block
                block.Parent = strip
                if seg.p / total * unit > .1 then
                    W.label(block, seg.label .. "\n" .. (math.floor(seg.p * 1000 + .5) / 10) .. "%", UDim2.fromScale(1, 1), UDim2.new(), 18)
                end
            end
        end
    end
    local pointer = Instance.new("Frame")
    pointer.Size, pointer.AnchorPoint, pointer.Position = UDim2.new(0, 6, 1, 8), Vector2.new(.5, .5), UDim2.fromScale(.5, .5)
    pointer.BackgroundColor3, pointer.BorderSizePixel, pointer.Parent = C.gold, 0, frame
    local goal = UDim2.fromScale(.5 - Sel.reelOffset(stage, FusionMenu.ReelTurns) * unit, 0)
    if animate then
        local tween = TweenService:Create(strip, TweenInfo.new(FusionMenu.ReelSeconds, Enum.EasingStyle.Quint, Enum.EasingDirection.Out), {Position = goal})
        tween:Play()
    else
        strip.Position = goal
    end
end

-- Celebration: the new dino pops in big (soft overshoot), facts in short lines.
local function finalCard(root: Frame, result, stage)
    local traits = result.traits or {}
    local g = traits.genes or {}
    local stageId = result.targetStage or "gold"
    local holder = Instance.new("Frame")
    holder.BackgroundTransparency, holder.Size, holder.Position, holder.Parent = 1, UDim2.new(.46, 0, .9, 0), UDim2.new(.02, 0, .02, 0), root
    -- BD-345: the NEW dino wears its own rolled colours and pattern under the tier (never a donor's).
    resultBox(holder, result.speciesId or "compy", stageId, Sel.previewTraits({stage = stageId, genes = g, shiny = traits.shiny, big = traits.big, mutationId = traits.mutationId}), true)
    local pop = Instance.new("UIScale")
    pop.Scale, pop.Parent = if motion() then .6 else 1, holder
    if motion() then
        TweenService:Create(pop, TweenInfo.new(.5, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play()
    end
    local chips = Instance.new("Frame")
    chips.Name, chips.BackgroundTransparency, chips.Size, chips.Position, chips.Parent = "ResultChips", 1, UDim2.new(1, 0, .36, 0), UDim2.new(0, 0, .64, 0), holder
    local layout = Instance.new("UIGridLayout")
    layout.CellSize, layout.CellPadding, layout.SortOrder = UDim2.new(.5, -4, 0, 36), UDim2.fromOffset(4, 4), Enum.SortOrder.LayoutOrder
    layout.Parent = chips
    local n = 0
    local function chip(text: string, color: Color3)
        n += 1
        local c = W.label(chips, text, UDim2.new(), UDim2.new(), 18, C.text)
        c.BackgroundTransparency, c.BackgroundColor3, c.LayoutOrder = 0, color, n
        Theme.decorate(c, 12)
    end
    chip(if traits.shiny then "Shiny!" else "Not shiny", if traits.shiny then C.purple else C.card)
    chip(if traits.big then "BIG!" else "Not BIG", if traits.big then C.purple else C.card)
    local mutation = Sel.name(catalog, "mutations", traits.mutationId, "")
    chip(if mutation ~= "" then mutation .. "!" else "No mutation", if mutation ~= "" then C.purple else C.card)
    chip("Colour 1: " .. Sel.name(catalog, "colors", g.primaryColorId), W.colorOf(g.primaryColorId))
    chip("Colour 2: " .. Sel.name(catalog, "colors", g.secondaryColorId), W.colorOf(g.secondaryColorId))
    local info = W.scroll(root, UDim2.new(.5, 0, .9, 0), UDim2.new(.49, 0, .02, 0))
    W.list(info, 4)
    local order = 0
    local function line(text: string, color: Color3?, size: number?)
        order += 1
        W.label(info, text, UDim2.new(1, -12, 0, if #text > 40 then 48 else 32), UDim2.new(), size or 22, color, true).LayoutOrder = order
    end
    line(stage.title .. "!", C.gold, 30)
    line(Sel.stageTitle(stageId) .. " stage: guaranteed. Made by you.", C.accent)
    line("Pattern: " .. Sel.name(catalog, "patterns", result.patternId or g.patternId))
    line("Colours: " .. Sel.geneLine(g, catalog))
    line("No effects yet. Buy some for this new dino in the Shop.", Dim, 17)
    if stage.replay then line("Already fused: this is your saved result.", C.blue) end
end

startReveal = function(quote, result, status)
    state.mode = "reveal"
    clearBody()
    local serial = state.viewSerial
    local root = body :: Frame
    -- Duplicate (re-open/retry) shows the committed result without replaying odds.
    local stages = Sel.revealSequence(if status == "duplicate" then nil else quote, result, catalog)
    local index = 0
    local content = Instance.new("Frame")
    content.BackgroundTransparency, content.Size, content.Parent = 1, UDim2.new(1, 0, 1, -(T + 12)), root
    local advance: () -> ()
    local auto = true
    local stepButtons = {}
    local function show(i: number)
        if serial ~= state.viewSerial then return end
        index = i
        content:ClearAllChildren()
        local stage = stages[i]
        setTitle(if stage.kind == "final" then "Ta-da!" else "Rolling " .. i .. " of " .. (#stages - 1), C.gold)
        if stage.kind == "final" then
            Sfx.play("fusion_reveal")
            finalCard(content, result, stage)
            for _, b in stepButtons do b.Visible = false end -- only "See my dino" and X remain
            return
        end
        W.label(content, if stage.kind == "pattern" then "Pattern locked" else (RevealTitles[stage.trait] or stage.title), UDim2.new(1, 0, 0, 44), UDim2.fromScale(0, .06), 34, C.gold)
        if stage.kind == "pattern" then
            -- BD-346: "Pattern locked" is a visible step: the real species in the locked pattern (neutral colours, so the
            -- colour rolls stay a surprise), a short pop, and the pattern name. Reduce Motion: no pop, same picture.
            local holder = W.box(content, UDim2.new(.5, 0, .52, 0), UDim2.new(.25, 0, .16, 0), C.card, 10)
            holder.Name = "PatternStep"
            local view = Preview.add(holder, result.speciesId or "compy", "base")
            view.Size, view.Position = UDim2.new(1, -8, 1, -8), UDim2.fromOffset(4, 4)
            PreviewTraits.add(view, {genes = {hatchSuccess = true, primaryColorId = "white", secondaryColorId = "blue", blend = 60, patternId = result.patternId or (result.traits and result.traits.genes and result.traits.genes.patternId)}})
            local pop = Instance.new("UIScale")
            pop.Scale, pop.Parent = if motion() then .7 else 1, holder
            if motion() then TweenService:Create(pop, TweenInfo.new(.45, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play() end
            W.label(content, "Pattern: " .. stage.value, UDim2.new(1, -40, 0, 48), UDim2.new(0, 20, .7, 0), 32, C.accent)
            W.label(content, "The pattern stays the same.", UDim2.new(1, -40, 0, 30), UDim2.new(0, 20, .84, 0), 20)
        elseif stage.kind == "wheel" and (stage.trait == "shiny" or stage.trait == "big") then
            chanceBar(content, stage, motion(), if stage.trait == "shiny" then "Shiny!" else "BIG!")
        elseif stage.kind == "wheel" then
            local animate = motion()
            reel(content, stage, animate)
            local valueLabel = W.label(content, "", UDim2.new(1, -40, 0, 48), UDim2.new(0, 20, .66, 0), 32, C.accent)
            local reveal = function()
                if valueLabel.Parent then valueLabel.Text = tostring(stage.value) .. "!" .. (if stage.detail then "  (" .. stage.detail .. ")" else "") end
            end
            if animate then task.delay(FusionMenu.ReelSeconds, reveal) else reveal() end
        else
            -- Committed value outside the quoted table: state it plainly.
            W.label(content, tostring(stage.value), UDim2.new(1, -40, 0, 60), UDim2.new(0, 20, .36, 0), 34, C.accent)
        end
        if auto then
            local wait = Sel.stepSeconds(stage.kind, motion(), FusionMenu.ReelSeconds) -- BD-346: never under 1.2 s
            task.delay(wait, function() if serial == state.viewSerial and index == i and auto then advance() end end)
        end
    end
    advance = function() if index < #stages then show(index + 1) end end
    local y = UDim2.new(0, 0, 1, -(T + 6))
    local skip = W.button(root, "Skip", UDim2.new(.32, -6, 0, T + 4), y, C.blue, function() auto = false show(#stages) end)
    skip.Name = "Skip"
    local nextButton = W.button(root, "Next", UDim2.new(.32, -6, 0, T + 4), UDim2.new(.33, 0, 1, -(T + 6)), C.accent, function() auto = false advance() end)
    nextButton.Name = "Next"
    stepButtons = {skip, nextButton}
    W.button(root, "See my dino", UDim2.new(.34, 0, 0, T + 4), UDim2.new(.66, 0, 1, -(T + 6)), C.purple, function()
        auto = false
        if type(result.resultId) == "string" then openDetails(result.resultId) end
    end).Name = "ResultDetails"
    show(1)
end

-- Other screens -----------------------------------------------------------------
openDetails = function(instanceId: string)
    local previous = state.mode
    state.mode = "details"
    setTitle("Dino Details", C.blue)
    DinoDetails.show(body :: Frame, instanceId, catalog, call, function()
        state.mode = if previous == "reveal" then "browse" else previous
        render()
    end)
end

local function renderUnavailable()
    setTitle("Fusion unavailable", C.card)
    renderStatus("Fusion unavailable\nFusion is not switched on here yet. Nothing was changed.", C.gold,
        {{"Close", C.red, function() FusionMenu.close() end, "Close"}})
end

local function renderResume()
    local attempt = pendingAttempt
    setTitle("Checking your last fusion", C.gold)
    renderStatus("Your last fusion did not get an answer.\nCHECK RESULT asks again for the SAME fusion: it shows the saved result or finishes that one. It never fuses twice.", C.gold, {
        {"Check result", C.accent, function() if attempt then runFuse(attempt) end end, "CheckResult"},
        {"Forget it", C.red, function() pendingAttempt = nil state.mode = "browse" render() end, "Discard"},
    })
end

render = function()
    if not state.open or not body then return end
    if state.mode == "reveal" or state.mode == "fusing" or state.mode == "details" then return end
    clearBody()
    if state.mode == "unavailable" or not FusionMenu.available() then renderUnavailable()
    elseif state.mode == "confirm" then renderConfirm()
    elseif state.mode == "resume" then renderResume()
    else state.mode = "browse" renderBrowse() end
end

function FusionMenu.open()
    ensureGui()
    state.open = true
    local screen = gui :: ScreenGui
    screen.Enabled = true
    -- BD-334: on a short phone canvas stay below the Roblox top bar (menu/chat buttons), which covered the title.
    local camera = if workspace then workspace.CurrentCamera else nil
    pcall(function()
        (screen :: any).ScreenInsets = if camera and camera.ViewportSize.Y < 500 then Enum.ScreenInsets.CoreUISafeInsets else Enum.ScreenInsets.DeviceSafeInsets
    end)
    if panel and motion() then
        local frame = panel :: Frame
        frame.Position = UDim2.new(0, leftInset + 6, .53, 0)
        Theme.animate(frame, .16, {Position = UDim2.new(0, leftInset + 6, .5, 0)})
    end
    if not FusionMenu.available() then state.mode = "unavailable" render() return end
    if fuseInFlight then
        state.mode = "fusing"
        renderStatus("Your fusion is still being saved...\nTrying again can never fuse twice.", C.gold)
        return
    elseif unseenResult then
        -- Committed while closed: show the saved result without replaying odds.
        local result = unseenResult
        unseenResult = nil
        startReveal(nil, result, "duplicate")
        loadList()
        return
    end
    state.mode = if pendingAttempt and pendingAttempt.state == "pending" then "resume" else "browse"
    render()
    loadList()
end

function FusionMenu.close()
    state.open = false
    state.quoteSerial += 1
    if state.mode ~= "fusing" then state.mode = "browse" end
    clearBody()
    if gui then (gui :: ScreenGui).Enabled = false end
end

function FusionMenu.isOpen(): boolean return state.open end

return FusionMenu
