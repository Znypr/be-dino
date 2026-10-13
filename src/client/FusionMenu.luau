--!strict
-- BD-065 Fusion Menu (client). Ten same-species + same-pattern Base dinos -> ONE NEW
-- Gold. The server (ReplicatedStorage.BeDinoRemotes.FusionAction) owns every rule,
-- odds table, consumption and roll; this module only lists, explains, previews the
-- exact quoted odds, collects explicit consent and REVEALS the committed result.
-- Pure decisions live in Shared.FusionSelection (tested by tools/verify_fusion_ui.py).
-- If the remote is missing the menu shows "Fusion unavailable" and never errors.
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
local PreviewTraits = require(script.Parent.PreviewTraits)
local W = require(script.Parent.FusionWidgets)
local DinoDetails = require(script.Parent.DinoDetails)
local C = W.Colors
local T = W.Touch

local FusionMenu = {}
-- Client display constants (module-local by design; no Config edits).
FusionMenu.QuoteDebounce = .35
FusionMenu.RequestTimeout = 12
FusionMenu.MaxListPages = 10
FusionMenu.PageSize = 200
FusionMenu.CardBatch = 120
FusionMenu.AutoRetries = 3
FusionMenu.ReelTurns = 3
FusionMenu.ReelSeconds = 1.7

local catalog = Sel.buildCatalog(Config, ProgressionConfig, EggGenetics.Patterns)
local player = Players.LocalPlayer

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
    listError = nil, loading = false, selection = {}, filters = {}, sortKey = "eligible",
    visible = FusionMenu.CardBatch, quote = nil, quoteKey = nil, quoteStatus = "idle", quoteMessage = "",
    quoteSerial = 0, viewSerial = 0, acknowledged = false,
}

local gui: ScreenGui? = nil
local panel: Frame? = nil
local body: Frame? = nil
local titleLabel: TextLabel? = nil
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
    local frame = W.box(scrim, UDim2.fromScale(.97, .95), UDim2.fromScale(.5, .5), C.panel, 8)
    frame.Name, frame.AnchorPoint, frame.Active = "FusionPanel", Vector2.new(.5, .5), true
    local limit = Instance.new("UISizeConstraint")
    limit.MaxSize, limit.Parent = Vector2.new(1180, 680), frame
    local header = W.box(frame, UDim2.new(1, -8, 0, T + 8), UDim2.fromOffset(4, 4), C.purple)
    titleLabel = W.label(header, "Pattern Fusion", UDim2.new(1, -(T * 2 + 28), 1, -8), UDim2.fromOffset(12, 4), 30, nil, true)
    W.button(header, "X", UDim2.new(0, T + 16, 0, T), UDim2.new(1, -(T + 20), 0, 4), C.red, function() FusionMenu.close() end)
    local content = Instance.new("Frame")
    content.Name, content.BackgroundTransparency, content.ClipsDescendants = "FusionBody", 1, true
    content.Size, content.Position = UDim2.new(1, -16, 1, -(T + 22)), UDim2.fromOffset(8, T + 16)
    content.Parent = frame
    local note = W.label(frame, "", UDim2.new(.7, 0, 0, 32), UDim2.new(.15, 0, 1, -40), 20)
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
                if state.listError == "fusion_disabled" or state.listError == "unavailable" then state.mode = "unavailable" end
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
    elseif #state.selection < (recipe.donorCount or Sel.DonorCount) then
        state.quoteStatus = "need"
        state.quoteMessage = "Select " .. ((recipe.donorCount or Sel.DonorCount) - #state.selection) .. " more matching dinos to see exact odds."
    else
        state.quoteStatus, state.quoteMessage = "loading", "Calculating exact odds for these 10 dinos..."
        local key, donors, stage = currentKey(), table.clone(state.selection), state.targetStage
        task.delay(FusionMenu.QuoteDebounce, function()
            if serial ~= state.quoteSerial then return end
            local response = call({action = "quote", targetStage = stage, donorIds = donors})
            if serial ~= state.quoteSerial or key ~= currentKey() then return end
            if type(response) == "table" and response.ok == true and type(response.quote) == "table"
                and Sel.requestKey(stage, response.quote.donorIds or {}, "") ~= key then
                state.quoteStatus, state.quoteMessage = "error", "The server quoted different dinos. Please reselect."
            elseif type(response) == "table" and response.ok == true and type(response.quote) == "table" then
                local formatted = Sel.formatOdds(response.quote.odds, catalog)
                if formatted.ok then
                    state.quote, state.quoteKey, state.quoteStatus = response.quote, key, "ready"
                    state.quoteMessage = ""
                else
                    state.quoteStatus, state.quoteMessage = "error", "Odds could not be read (" .. tostring(formatted.error) .. "). Fusion is disabled until they are."
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
    if field == "conditionId" then return Sel.name(catalog, "conditions", value) end
    if field == "mutationId" then return if value == "none" then "None" else Sel.name(catalog, "mutations", value) end
    if field == "shiny" or field == "big" then return if value then "Yes" else "No" end
    if field == "originKind" then return ({hatch = "Hatched", fusion = "Fused", legacy_unknown = "Older"})[value] or tostring(value) end
    if field == "cosmetics" then return ({has = "Owns FX", none = "No FX", equipped = "Equipped"})[value] or tostring(value) end
    if field == "stage" then return Sel.name(nil, "x", value) end
    return tostring(value)
end
local FilterLabels = {speciesId = "Species", patternId = "Pattern", stage = "Stage", colorId = "Color", conditionId = "Condition",
    shiny = "Shiny", big = "BIG", mutationId = "Mutation", originKind = "Origin", cosmetics = "Cosmetics"}

local function cardLook(d)
    local entry = cards[d.instanceId]
    if not entry then return end
    local selected = table.find(state.selection, d.instanceId) ~= nil
    local ctx = Sel.context(state.targetStage, state.selection, state.byId, state.filters)
    local reason = if selected then nil else Sel.ineligibility(d, ctx)
    local valuable = #Sel.valuableReasons(d) > 0
    entry.stroke.Color = if selected then (if valuable then C.purple else C.gold) else C.outline
    entry.stroke.Thickness = if selected then 5 else 3
    entry.button.BackgroundColor3 = if reason then C.outline else (W.StageColors[d.stage] or C.card)
    entry.status.Text = if selected then (if valuable then "SELECTED (VALUABLE)" else "SELECTED")
        elseif reason then (Sel.ReasonText[reason] or reason)
        elseif valuable then "Valuable: tap to add" else "Tap to add"
    entry.status.TextColor3 = if selected then C.gold elseif reason then C.red elseif valuable then C.purple else C.accent
end

local function refreshCards()
    for _, d in state.dinos do cardLook(d) end
end

local openDetails: (string) -> () = function() end

local function toggle(d)
    local nextSelection, ok, reason = Sel.toggle(state.selection, d, state.targetStage, state.byId)
    if not ok then toast(Sel.ReasonText[reason] or tostring(reason), C.red) return end
    state.selection = nextSelection
    refreshCards()
    scheduleQuote()
end

local function buildGrid(grid: ScrollingFrame)
    for _, child in grid:GetChildren() do if not child:IsA("UIGridLayout") then child:Destroy() end end
    cards = {}
    local ctx = Sel.context(state.targetStage, state.selection, state.byId, state.filters)
    local list = Sel.sort(Sel.filter(state.dinos, state.filters), state.sortKey, ctx, Sel.selectedSet(state.selection), catalog)
    for i, d in list do
        if i > state.visible then
            local more = W.button(grid, "SHOW MORE (" .. (#list - state.visible) .. ")", UDim2.new(), UDim2.new(), C.blue, function()
                state.visible += FusionMenu.CardBatch
                buildGrid(grid)
            end)
            more.LayoutOrder = i
            break
        end
        local g = d.genes or {}
        local card = Instance.new("TextButton")
        card.Name, card.Text, card.AutoButtonColor, card.LayoutOrder = "Dino_" .. i, "", false, i
        card.BackgroundColor3 = W.StageColors[d.stage] or C.card
        Theme.decorate(card, 6)
        card.Parent = grid
        card.Activated:Connect(function() toggle(d) end)
        W.label(card, Sel.name(catalog, "species", d.speciesId), UDim2.new(1, -8, 0, 20), UDim2.fromOffset(4, 3), 18)
        W.label(card, Sel.name(catalog, "patterns", g.patternId, "Unknown pattern") .. " • " .. Sel.name(nil, "x", d.stage), UDim2.new(1, -8, 0, 16), UDim2.fromOffset(4, 24), 14, C.gold)
        W.swatch(card, g, UDim2.new(1, -16, 0, 9), UDim2.fromOffset(8, 43))
        local badges = Sel.badges(d, catalog)
        W.label(card, (if #badges > 0 then table.concat(badges, " • ") else Sel.name(catalog, "conditions", g.conditionId, "")), UDim2.new(1, -8, 0, 18), UDim2.fromOffset(4, 55), 15,
            if #badges > 0 then C.purple else C.text)
        local status = W.label(card, "", UDim2.new(1, -(T + 8), 0, T - 4), UDim2.new(0, 4, 1, -(T + 2)), 15)
        local info = W.button(card, "i", UDim2.fromOffset(T, T), UDim2.new(1, -(T + 2), 1, -(T + 2)), C.blue, function() openDetails(d.instanceId) end)
        info.Name = "Details"
        local stroke = card:FindFirstChildOfClass("UIStroke") :: UIStroke
        cards[d.instanceId] = {button = card, stroke = stroke, status = status}
        cardLook(d)
    end
    if #list == 0 then
        local empty = W.label(grid, if state.loading then "Loading your dinos..." else "No dinos match these filters.", UDim2.new(), UDim2.new(), 20, C.gold)
        empty.LayoutOrder = 0
    end
end

updateColumn = function()
    local col = column
    if not col.slots then return end
    for _, child in col.slots:GetChildren() do if not child:IsA("UIGridLayout") then child:Destroy() end end
    local recipe = Sel.stage(state.targetStage)
    local need = (recipe and recipe.donorCount) or Sel.DonorCount
    for i = 1, need do
        local id = state.selection[i]
        local d = id and state.byId[id]
        if d and col.compact then
            -- Phone landscape: slots are a compact read-only strip; tap the dino card to remove.
            local chip = W.box(col.slots, UDim2.new(), UDim2.new(), if #Sel.valuableReasons(d) > 0 then C.purple else C.card, 3)
            chip.LayoutOrder = i
            W.swatch(chip, d.genes, UDim2.new(1, -4, 0, 6), UDim2.new(0, 2, 1, -8))
        elseif d then
            local slot = W.button(col.slots, string.sub(Sel.name(catalog, "species", d.speciesId), 1, 4), UDim2.new(), UDim2.new(), if #Sel.valuableReasons(d) > 0 then C.purple else C.card, function() toggle(d) end)
            slot.LayoutOrder = i
            W.swatch(slot, d.genes, UDim2.new(1, -8, 0, 5), UDim2.new(0, 4, 1, -9))
        else
            local empty = W.box(col.slots, UDim2.new(), UDim2.new(), C.outline, 4)
            empty.LayoutOrder = i
            W.label(empty, tostring(i), UDim2.fromScale(1, 1), UDim2.new(), 16, Color3.fromRGB(120, 120, 140))
        end
    end
    local h = Sel.histogram(state.selection, state.byId)
    col.count.Text = string.format("INGREDIENTS %d/%d", #state.selection, need)
    local parts = {string.format("%d Shiny / %d", h.shiny, need), string.format("%d BIG", h.big)}
    for id, n in h.mutations do table.insert(parts, Sel.name(catalog, "mutations", id) .. " x" .. n) end
    if h.cosmetics > 0 then table.insert(parts, h.cosmetics .. " with bought FX (lost)") end
    col.histogram.Text = table.concat(parts, " • ")
    local odds = col.odds :: ScrollingFrame
    for _, child in odds:GetChildren() do if not child:IsA("UIListLayout") then child:Destroy() end end
    local order = 0
    local function line(text: string, color: Color3?, height: number?)
        order += 1
        local l = W.label(odds, text, UDim2.new(1, -12, 0, height or 24), UDim2.new(), 18, color, true)
        l.LayoutOrder = order
    end
    if state.targetStage ~= "gold" then
        line(string.upper(state.targetStage) .. " LOCKED", C.gold, 30)
        line(Sel.LockedStageText .. ". Gold is the only approved recipe.", nil, 44)
    else
        line("UPGRADED (guaranteed): 1 NEW Gold, stage + stats", C.accent, 40)
        if state.selection[1] and state.byId[state.selection[1]] then
            local g = state.byId[state.selection[1]].genes or {}
            line("PATTERN LOCKED: " .. Sel.name(catalog, "patterns", g.patternId), C.gold)
        end
        line("ROLLED (exact odds from the server):", C.blue)
        if state.quoteStatus == "ready" and state.quote then
            local formatted = Sel.formatOdds(state.quote.odds, catalog)
            for _, section in formatted.sections do
                local texts = {}
                for _, row in section.rows do table.insert(texts, row.label .. " " .. row.text) end
                local text = section.title .. ": " .. table.concat(texts, " • ")
                line(text, nil, if #text > 70 then 64 elseif #text > 36 then 44 else 24)
            end
            line("Odds version " .. tostring(state.quote.oddsVersion) .. " • recipe " .. tostring(state.quote.recipeVersion), Color3.fromRGB(170, 170, 190))
        else
            line(state.quoteMessage, if state.quoteStatus == "error" then C.red else C.gold, 44)
        end
    end
    local ready = state.quoteStatus == "ready" and state.quote ~= nil and state.quoteKey == currentKey()
    col.fuse.BackgroundColor3 = if ready then C.accent else C.card
    col.fuse.Text = if ready then "REVIEW & FUSE" else "FUSE (" .. #state.selection .. "/" .. need .. ")"
end

local function renderBrowse()
    setTitle("Pattern Fusion: 10 Base -> 1 NEW Gold", C.purple)
    local root = body :: Frame
    local left = Instance.new("Frame")
    left.Name, left.BackgroundTransparency, left.Size, left.Parent = "Browse", 1, UDim2.new(.6, -6, 1, 0), root
    local right = W.box(root, UDim2.new(.4, -6, 1, 0), UDim2.new(.6, 6, 0, 0), C.card, 6)
    right.Name = "Ingredients"
    -- Row 1: target stage tabs + sort + auto-fill.
    local tabs = {{"gold", "GOLD"}, {"emerald", "EMERALD (LOCKED)"}, {"diamond", "DIAMOND (LOCKED)"}}
    for i, tab in tabs do
        local stage = Sel.stage(tab[1])
        local b = W.button(left, tab[2], UDim2.new(.17, -4, 0, T), UDim2.new((i - 1) * .17, 0, 0, 0),
            if state.targetStage == tab[1] then (W.StageColors[tab[1]] or C.gold) elseif stage and stage.approved then C.card else C.outline, function()
                if state.targetStage == tab[1] then return end
                state.targetStage = tab[1]
                if not (stage and stage.approved) then toast(string.upper(tab[2]) .. ": " .. Sel.LockedStageText, C.gold) end
                state.selection = {}
                render()
                scheduleQuote()
            end)
        b.Name = "Stage_" .. tab[1]
    end
    W.button(left, "SORT: " .. string.upper(Sel.SortNames[state.sortKey]), UDim2.new(.25, -4, 0, T), UDim2.new(.51, 0, 0, 0), C.blue, function()
        local i = table.find(Sel.SortKeys, state.sortKey) or 1
        state.sortKey = Sel.SortKeys[i % #Sel.SortKeys + 1]
        render()
    end)
    W.button(left, "AUTO-FILL PLAIN", UDim2.new(.24, 0, 0, T), UDim2.new(.76, 0, 0, 0), C.accent, function()
        local filled, added, short = Sel.autoFill(state.dinos, state.selection, state.targetStage, state.filters, catalog)
        state.selection = filled
        if added == 0 then toast("No plain matching dinos to add. Valuable dinos are never auto-filled.", C.gold)
        elseif short > 0 then toast("Added " .. added .. " plain dinos; " .. short .. " more needed.", C.gold)
        else toast("Added " .. added .. " plain dinos. Valuables were skipped.", C.accent) end
        refreshCards()
        scheduleQuote()
    end)
    -- Row 2: cycling filter chips (horizontal scroll for small screens).
    local chips = Instance.new("ScrollingFrame")
    chips.Name, chips.BackgroundTransparency, chips.BorderSizePixel = "Filters", 1, 0
    chips.Size, chips.Position, chips.ScrollingDirection = UDim2.new(1, 0, 0, T + 8), UDim2.fromOffset(0, T + 6), Enum.ScrollingDirection.X
    chips.ScrollBarThickness, chips.AutomaticCanvasSize, chips.CanvasSize = 4, Enum.AutomaticSize.X, UDim2.new()
    chips.Parent = left
    W.list(chips, 6, true)
    local options = Sel.filterOptions(state.dinos, catalog)
    local reset = W.button(chips, "RESET", UDim2.fromOffset(84, T), UDim2.new(), C.red, function()
        state.filters, state.visible = {}, FusionMenu.CardBatch
        render()
    end)
    reset.LayoutOrder = 0
    for i, field in Sel.FilterFields do
        local value = state.filters[field]
        local chip = W.button(chips, FilterLabels[field] .. ": " .. filterValueName(field, value), UDim2.fromOffset(150, T), UDim2.new(),
            if value ~= nil then C.blue else C.card, function()
                state.filters[field] = Sel.cycle(options[field] or {}, state.filters[field])
                state.visible = FusionMenu.CardBatch
                render()
            end)
        chip.LayoutOrder = i
    end
    -- Grid of individual dinos.
    local grid = W.scroll(left, UDim2.new(1, 0, 1, -(T * 2 + 20)), UDim2.fromOffset(0, T * 2 + 20))
    grid.Name = "DinoGrid"
    local layout = Instance.new("UIGridLayout")
    local small = gui ~= nil and (gui :: ScreenGui).AbsoluteSize.Y < 520
    layout.CellSize = if small then UDim2.fromOffset(118, 124) else UDim2.fromOffset(146, 132)
    layout.CellPadding, layout.SortOrder = UDim2.fromOffset(6, 6), Enum.SortOrder.LayoutOrder
    layout.Parent = grid
    if state.listError and state.mode == "browse" then
        W.label(grid, "Could not load dinos: " .. Sel.failureMessage(state.listError), UDim2.new(), UDim2.new(), 20, C.red)
        W.button(grid, "RETRY", UDim2.new(), UDim2.new(), C.blue, function() loadList() render() end)
    else
        buildGrid(grid)
    end
    -- Right column: slots, histogram, odds, fuse.
    -- Compact layout for short (phone landscape) safe areas: one read-only slot strip.
    local compact = gui ~= nil and (gui :: ScreenGui).AbsoluteSize.Y < 450
    column.compact = compact
    local slotsHeight = if compact then 26 else T * 2 + 6
    local slotsBottom = T + 6 + slotsHeight
    column.count = W.label(right, "", UDim2.new(1, -100, 0, T), UDim2.fromOffset(6, 2), 24, C.gold, true)
    W.button(right, "CLEAR", UDim2.fromOffset(84, T), UDim2.new(1, -88, 0, 2), C.red, function()
        state.selection = {}
        refreshCards()
        scheduleQuote()
    end).Name = "Clear"
    local slots = Instance.new("Frame")
    slots.Name, slots.BackgroundTransparency, slots.Size, slots.Position = "Slots", 1, UDim2.new(1, -12, 0, slotsHeight), UDim2.fromOffset(6, T + 6)
    slots.Parent = right
    local slotLayout = Instance.new("UIGridLayout")
    slotLayout.CellSize = if compact then UDim2.new(.1, -3, 0, slotsHeight) else UDim2.new(.2, -5, 0, T)
    slotLayout.CellPadding, slotLayout.SortOrder = if compact then UDim2.fromOffset(3, 0) else UDim2.fromOffset(5, 6), Enum.SortOrder.LayoutOrder
    slotLayout.Parent = slots
    column.slots = slots
    column.histogram = W.label(right, "", UDim2.new(1, -12, 0, 20), UDim2.fromOffset(6, slotsBottom + 2), 16, C.text, true)
    local odds = W.scroll(right, UDim2.new(1, -12, 1, -(slotsBottom + 26 + T + 14)), UDim2.fromOffset(6, slotsBottom + 24))
    odds.Name = "Odds"
    W.list(odds, 2)
    column.odds = odds
    column.fuse = W.button(right, "FUSE", UDim2.new(1, -12, 0, T + 4), UDim2.new(0, 6, 1, -(T + 10)), C.card, function()
        local ready = state.quoteStatus == "ready" and state.quote ~= nil and state.quoteKey == currentKey()
        if not ready then
            toast(if state.quoteStatus == "loading" then "Odds are still loading." else state.quoteMessage, C.gold)
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
    local g = d.genes or {}
    local badges = Sel.badges(d, catalog)
    return Sel.name(catalog, "patterns", g.patternId) .. " " .. Sel.name(catalog, "species", d.speciesId) .. " • "
        .. Sel.geneLine(g, catalog) .. " • " .. Sel.name(catalog, "conditions", g.conditionId, "?")
        .. (if #badges > 0 then " • " .. table.concat(badges, ", ") else "")
end

local function renderConfirm()
    local quote = state.quote
    if not quote or state.quoteKey ~= currentKey() then state.mode = "browse" render() return end
    setTitle("Confirm Gold Fusion (no undo)", C.gold)
    local root = body :: Frame
    local loss = Sel.lossSummary(quote, catalog)
    local list = W.scroll(root, UDim2.new(1, 0, 1, -(T + 14)), UDim2.new())
    W.list(list, 3)
    local order = 0
    local function line(text: string, color: Color3?, height: number?)
        order += 1
        local l = W.label(list, text, UDim2.new(1, -14, 0, height or (if #text > 80 then 48 else 26)), UDim2.new(), 20, color, true)
        l.LayoutOrder = order
    end
    line("GUARANTEED: 1 NEW Gold " .. Sel.name(catalog, "patterns", quote.patternId) .. " " .. Sel.name(catalog, "species", quote.speciesId)
        .. " with the Gold stage upgrade. Its colors, condition, Shiny, BIG and mutation are freshly rolled.", C.accent, 48)
    line("PATTERN LOCKED: " .. Sel.name(catalog, "patterns", quote.patternId), C.gold)
    line("ALL 10 DINOS BELOW ARE CONSUMED:", C.red)
    for i, id in quote.donorIds or state.selection do
        local d = state.byId[id]
        line(i .. ". " .. (if d then donorLine(d) else id), if d and #Sel.valuableReasons(d) > 0 then C.purple else nil)
    end
    line(loss.cosmeticText, if loss.auraCount + loss.trailCount > 0 then C.red else C.text, 48)
    if #loss.valuables > 0 then
        local parts = {}
        for _, v in loss.valuables do
            local d = state.byId[v.instanceId]
            table.insert(parts, (if d then Sel.name(catalog, "species", d.speciesId) else "Dino") .. " (" .. v.text .. ")")
        end
        line("Valuable donors consumed: " .. table.concat(parts, ", "), C.purple, 48)
    end
    line("EXACT ROLL ODDS FOR THIS SELECTION:", C.blue)
    for _, section in Sel.formatOdds(quote.odds, catalog).sections do
        local texts = {}
        for _, row in section.rows do table.insert(texts, row.label .. " " .. row.text) end
        line(section.title .. ": " .. table.concat(texts, " • "), nil, 48)
    end
    line("Odds version " .. tostring(quote.oddsVersion) .. " • recipe " .. tostring(quote.recipeVersion) .. ". Wheels after fusion only reveal the saved result.", Color3.fromRGB(170, 170, 190), 48)
    local needs = loss.needsConfirm
    local y = UDim2.new(0, 0, 1, -(T + 6))
    W.button(root, "CANCEL", UDim2.new(.3, -6, 0, T + 4), y, C.red, function() state.mode = "browse" render() end)
    if needs and not state.acknowledged then
        W.button(root, "I UNDERSTAND: " .. (loss.auraCount + loss.trailCount) .. " FX + " .. #loss.valuables .. " VALUABLE LOST", UDim2.new(.7, 0, 0, T + 4), UDim2.new(.3, 0, 1, -(T + 6)), C.gold, function()
            state.acknowledged = true
            render()
        end).Name = "Acknowledge"
    else
        W.button(root, "FUSE NOW (CONSUMES 10)", UDim2.new(.7, 0, 0, T + 4), UDim2.new(.3, 0, 1, -(T + 6)), C.accent, function()
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
    renderStatus("Fusing your 10 dinos...\nThis request is saved: retries reuse the same token, so it can never fuse twice.", C.gold)
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
                state.selection = {}
                if state.open then startReveal(attempt.quote, outcome.result, outcome.status)
                else unseenResult = outcome.result end
                loadList()
                return
            elseif outcome.kind == "retry" and tries < FusionMenu.AutoRetries and outcome.reason ~= "lease_lost" then
                if state.open then renderStatus(outcome.message .. "\n(attempt " .. (tries + 1) .. ")", C.gold) end
                task.wait(2 ^ tries)
            elseif outcome.kind == "retry" then
                fuseInFlight = false
                if not state.open then state.mode = "browse" return end
                renderStatus(outcome.message, C.red, {
                    {"RETRY (SAME REQUEST)", C.accent, function() runFuse(attempt) end, "Retry"},
                    {"BACK", C.blue, function() state.mode = "browse" loadList() render() end, "Back"},
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
                    W.label(block, seg.label .. "\n" .. (math.floor(seg.p * 1000 + .5) / 10) .. "%", UDim2.fromScale(1, 1), UDim2.new(), 16)
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

local function finalCard(root: Frame, result, stage)
    local traits = result.traits or {}
    local g = traits.genes or {}
    local card = W.box(root, UDim2.new(.42, 0, .8, 0), UDim2.new(.03, 0, .04, 0), W.StageColors[result.targetStage or "gold"] or C.gold, 8)
    local view = Preview.add(card, result.speciesId or "compy", result.targetStage or "gold")
    view.Size, view.Position = UDim2.fromScale(1, .9), UDim2.fromScale(0, .05)
    PreviewTraits.add(view, {shiny = traits.shiny, big = traits.big})
    local info = W.scroll(root, UDim2.new(.52, 0, .8, 0), UDim2.new(.47, 0, .04, 0))
    W.list(info, 3)
    local order = 0
    local function line(text: string, color: Color3?)
        order += 1
        W.label(info, text, UDim2.new(1, -12, 0, if #text > 44 then 46 else 28), UDim2.new(), 22, color, true).LayoutOrder = order
    end
    line(stage.title, C.gold)
    line("Crafted Gold (earned) • guaranteed stage", C.accent)
    line("Pattern (locked): " .. Sel.name(catalog, "patterns", result.patternId or g.patternId))
    line("Colors: " .. Sel.geneLine(g, catalog))
    line("Condition: " .. Sel.name(catalog, "conditions", g.conditionId, "?"))
    line("Shiny: " .. (if traits.shiny then "YES" else "No") .. " • BIG: " .. (if traits.big then "YES" else "No"))
    line("Mutation: " .. Sel.name(catalog, "mutations", traits.mutationId, "None"))
    line("Bought cosmetics: none (buy separately for this new dino)")
    line("Odds version " .. tostring(result.oddsVersion or "?"), Color3.fromRGB(170, 170, 190))
    if stage.replay then line("Already fused: showing your saved result.", C.blue) end
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
    local function show(i: number)
        if serial ~= state.viewSerial then return end
        index = i
        content:ClearAllChildren()
        local stage = stages[i]
        setTitle(if stage.kind == "final" then "Fusion complete!" else "Revealing " .. i .. " / " .. (#stages - 1), C.gold)
        if stage.kind == "final" then
            finalCard(content, result, stage)
            return
        end
        W.label(content, stage.title, UDim2.new(1, 0, 0, 44), UDim2.fromScale(0, .06), 34, C.gold)
        if stage.kind == "pattern" then
            W.label(content, "PATTERN LOCKED: " .. string.upper(stage.value), UDim2.new(1, -40, 0, 60), UDim2.new(0, 20, .34, 0), 34, C.accent)
            W.label(content, "Same-pattern recipe: the pattern is never rolled.", UDim2.new(1, -40, 0, 34), UDim2.new(0, 20, .6, 0), 20)
        elseif stage.kind == "wheel" then
            local animate = motion() and auto
            reel(content, stage, animate)
            local valueLabel = W.label(content, "", UDim2.new(1, -40, 0, 48), UDim2.new(0, 20, .66, 0), 32, C.accent)
            local reveal = function()
                if valueLabel.Parent then valueLabel.Text = string.upper(tostring(stage.value)) .. (if stage.detail then "  (" .. stage.detail .. ")" else "") end
            end
            if animate then task.delay(FusionMenu.ReelSeconds, reveal) else reveal() end
        else
            -- Committed value outside the quoted table: state it plainly.
            W.label(content, string.upper(tostring(stage.value)), UDim2.new(1, -40, 0, 60), UDim2.new(0, 20, .36, 0), 34, C.accent)
        end
        if auto then
            local wait = if motion() then FusionMenu.ReelSeconds + .9 else .6
            task.delay(wait, function() if serial == state.viewSerial and index == i and auto then advance() end end)
        end
    end
    advance = function() if index < #stages then show(index + 1) end end
    local y = UDim2.new(0, 0, 1, -(T + 6))
    W.button(root, "SKIP TO RESULT", UDim2.new(.32, -6, 0, T + 4), y, C.blue, function() auto = false show(#stages) end).Name = "Skip"
    W.button(root, "NEXT", UDim2.new(.32, -6, 0, T + 4), UDim2.new(.33, 0, 1, -(T + 6)), C.accent, function() auto = false advance() end).Name = "Next"
    W.button(root, "VIEW DETAILS", UDim2.new(.34, 0, 0, T + 4), UDim2.new(.66, 0, 1, -(T + 6)), C.purple, function()
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
    renderStatus("Fusion unavailable\nThe 10-dino Gold fusion is not enabled on this server yet. Nothing was changed.", C.gold,
        {{"CLOSE", C.red, function() FusionMenu.close() end, "Close"}})
end

local function renderResume()
    local attempt = pendingAttempt
    setTitle("Checking your last fusion", C.gold)
    renderStatus("Your last confirmed fusion did not get an answer.\nCHECK RESULT resends the SAME request: it either shows the saved result or finishes that one fusion. It never fuses twice.", C.gold, {
        {"CHECK RESULT", C.accent, function() if attempt then runFuse(attempt) end end, "CheckResult"},
        {"DISCARD", C.red, function() pendingAttempt = nil state.mode = "browse" render() end, "Discard"},
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
    if panel and motion() then
        local frame = panel :: Frame
        frame.Position = UDim2.fromScale(.5, .53)
        Theme.animate(frame, .16, {Position = UDim2.fromScale(.5, .5)})
    end
    if not FusionMenu.available() then state.mode = "unavailable" render() return end
    if fuseInFlight then
        state.mode = "fusing"
        renderStatus("Your fusion is still being saved...\nRetries reuse the same token, so it can never fuse twice.", C.gold)
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
