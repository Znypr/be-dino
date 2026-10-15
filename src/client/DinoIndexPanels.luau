--!strict
-- BD-149 / BD-150 / BD-151 Dino Index species page: big drag-to-turn hero, "My dinos" grid (every owned copy as a
-- card with its real pattern and colors), per-copy details/percent lines, per-copy EQUIP and one Sort and filter
-- sheet. Data comes from the existing FusionAction remote ("list" pages + "details", read-only, server-validated);
-- all rules live in Shared.MyDinos / Shared.FusionSelection (tools/verify_inspect.py). Opened from Bootstrap's
-- name == "detail" branch through Panels.species(ctx); if FusionAction is missing Bootstrap keeps the old page.
-- Previews: one hero ViewportFrame + at most MyDinos.PageSize card viewports (SHOW MORE adds a page); Preview.add
-- loads a model only while its viewport is visible, through the same patient LoadGate loader as everywhere else,
-- so there is never a box fallback and off-screen cards cost nothing.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local ProgressionConfig = require(Shared.ProgressionConfig)
local EggGenetics = require(Shared.EggGenetics)
local Theme = require(Shared.UITheme)
local Preview = require(Shared.DinosaurPreview)
local Sel = require(Shared.FusionSelection)
local MyDinos = require(Shared.MyDinos)
local PreviewTraits = require(script.Parent.PreviewTraits)
local InspectView = require(script.Parent.InspectView)
local W = require(script.Parent.FusionWidgets)
local C = W.Colors

local Panels = {}
Panels.RequestTimeout = 12
Panels.PageLimit = 200
Panels.MaxPages = 10

local player = Players.LocalPlayer
local catalog = Sel.buildCatalog(Config, ProgressionConfig, EggGenetics.Patterns)

local function remote(): RemoteFunction?
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local found = folder and folder:FindFirstChild("FusionAction")
    return if found and found:IsA("RemoteFunction") then found else nil
end
function Panels.supported(): boolean return remote() ~= nil end

local function call(payload)
    local fn = remote()
    if not fn then return {ok = false, reason = "unavailable"} end
    local done, response = false, nil
    task.spawn(function()
        local ok, result = pcall(function() return (fn :: RemoteFunction):InvokeServer(payload) end)
        if ok then response = result end
        done = true
    end)
    local started = os.clock()
    while not done and os.clock() - started < Panels.RequestTimeout do task.wait(.05) end
    return response
end

-- One shared copy of the player's dinos, reloaded only when the profile revision changes.
local cache = {revision = -1, dinos = {} :: {any}, loading = false, waiters = {} :: {(boolean) -> ()}}
local function loadAll(revision: number, done: (boolean) -> ())
    if cache.revision == revision then done(true) return end
    table.insert(cache.waiters, done)
    if cache.loading then return end
    cache.loading = true
    task.spawn(function()
        local all, cursor, pages, ok = {}, nil, 0, true
        repeat
            local response = call({action = "list", cursor = cursor, limit = Panels.PageLimit})
            if type(response) ~= "table" or response.ok ~= true or type(response.dinosaurs) ~= "table" then ok = false break end
            for _, d in response.dinosaurs do if type(d) == "table" and type(d.instanceId) == "string" then table.insert(all, d) end end
            cursor = response.nextCursor
            pages += 1
        until cursor == nil or pages >= Panels.MaxPages
        if ok then cache.dinos, cache.revision = all, revision end
        cache.loading = false
        local waiters = cache.waiters
        cache.waiters = {}
        for _, w in waiters do w(ok) end
    end)
end

local StageColors = {base = Color3.fromRGB(86, 82, 104), gold = C.gold, emerald = Color3.fromRGB(46, 196, 120), diamond = C.blue}

local function pill(parent: GuiObject, text: string, color: Color3, size: UDim2, position: UDim2, textColor: Color3?): TextLabel
    local p = Instance.new("TextLabel")
    p.BackgroundColor3, p.BackgroundTransparency, p.BorderSizePixel = color, 0, 0
    p.Size, p.Position, p.Font, p.Text = size, position, Enum.Font.FredokaOne, text
    p.TextColor3, p.TextScaled, p.ZIndex = textColor or C.text, true, parent.ZIndex + 3
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 6) corner.Parent = p
    local limit = Instance.new("UITextSizeConstraint") limit.MaxTextSize, limit.MinTextSize, limit.Parent = 14, 8, p
    p.Parent = parent
    return p
end

local function chipButton(parent: GuiObject, text: string, height: number, on: boolean, swatch: Color3?, callback: () -> ()): TextButton
    local b = Instance.new("TextButton")
    b.AutomaticSize, b.Size = Enum.AutomaticSize.X, UDim2.fromOffset(0, height)
    b.BackgroundColor3 = if on then C.gold:Lerp(C.panel, .35) else C.card
    b.Font, b.Text, b.TextSize, b.TextColor3 = Enum.Font.FredokaOne, text, 18, if on then C.outline else C.text
    b.AutoButtonColor = true
    local pad = Instance.new("UIPadding")
    pad.PaddingLeft, pad.PaddingRight = UDim.new(0, if swatch then 36 else 14), UDim.new(0, 14)
    pad.Parent = b
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 10) corner.Parent = b
    local stroke = Instance.new("UIStroke")
    stroke.Color, stroke.Thickness = if on then C.gold else C.outline, if on then 3 else 2
    stroke.Parent = b
    if swatch then
        local s = Instance.new("Frame")
        s.Name, s.BackgroundColor3, s.Size = "Swatch", swatch, UDim2.fromOffset(20, 20)
        s.AnchorPoint, s.Position = Vector2.new(0, .5), UDim2.new(0, -26, .5, 0)
        local c = Instance.new("UICorner") c.CornerRadius = UDim.new(0, 5) c.Parent = s
        local st = Instance.new("UIStroke") st.Color, st.Thickness, st.Parent = C.outline, 1.5, s
        s.Parent = b
    end
    b.Activated:Connect(callback)
    b.Parent = parent
    return b
end

-- ctx: body, speciesId, owned, color, fallbackStage, fallbackLine, scale(), equipped() -> attrs, equip(id, key),
-- notify(text, color?), onBack(), revision() -> number
function Panels.species(ctx)
    local speciesId: string = ctx.speciesId
    local speciesName = Config.SpeciesDisplayNames[speciesId] or speciesId
    local T = math.max(W.Touch, math.ceil(W.Touch / math.max(.3, ctx.scale())))
    local root = Instance.new("Frame")
    root.Name, root.Size, root.BackgroundTransparency = "DinoIndexSpecies", UDim2.fromScale(1, 1), 1
    root.Parent = ctx.body
    local connections: {RBXScriptConnection} = {}
    root.Destroying:Once(function() for _, c in connections do c:Disconnect() end end)

    local left = Instance.new("Frame")
    left.Name, left.Size, left.BackgroundTransparency, left.Parent = "Hero", UDim2.fromOffset(296, 402), 1, root
    local right = Instance.new("Frame")
    right.Name, right.Size, right.Position, right.BackgroundTransparency, right.Parent = "MyDinos", UDim2.fromOffset(516, 402), UDim2.fromOffset(308, 0), 1, root

    local function backButton(position: UDim2, size: UDim2)
        W.button(left, "BACK", size, position, C.blue, function() ctx.onBack() end)
    end

    -- Undiscovered species: black silhouette and one plain line, nothing else.
    if not ctx.owned then
        local stage = W.box(left, UDim2.fromOffset(296, 250), UDim2.new(), Color3.fromRGB(62, 64, 74), 24)
        local view = Preview.add(stage, speciesId, "silhouette")
        view.Size, view.Position = UDim2.fromScale(1, .9), UDim2.fromScale(0, .05)
        W.label(left, "Not discovered yet", UDim2.fromOffset(296, 44), UDim2.fromOffset(0, 262), 30, C.gold)
        W.label(left, "Hatch eggs to find " .. speciesName .. ".", UDim2.fromOffset(296, 36), UDim2.fromOffset(0, 308), 20)
        backButton(UDim2.fromOffset(0, 350), UDim2.fromOffset(296, math.max(48, T)))
        return root
    end

    local st = {list = {} :: {any}, byId = {} :: {[string]: any}, chosen = {} :: {[string]: any}, sortKey = "rarest",
        visible = MyDinos.PageSize, selected = nil :: string?, details = {} :: {[string]: any}, loaded = false, equippedId = nil :: string?}
    local hero: InspectView.Handle? = nil
    local cards: {[string]: {stroke: UIStroke, tag: GuiObject?, button: TextButton, index: number, mount: () -> (), unmount: () -> (), mounted: boolean}} = {}
    local grid: ScrollingFrame? = nil
    local filterButton: TextButton? = nil
    local equipButton: TextButton? = nil
    local traitsList: ScrollingFrame? = nil
    local titleLabel: TextLabel? = nil
    local buildLeft: () -> ()
    local buildRight: () -> ()

    local function viewList(): {any} return MyDinos.view(st.list, st.chosen, st.sortKey, catalog) end
    local function refreshEquipped()
        local best = MyDinos.view(st.list, {}, "rarest", catalog)
        st.equippedId = MyDinos.equippedId(best, ctx.equipped())
        for id, entry in cards do
            if entry.tag then entry.tag.Visible = id == st.equippedId end
        end
        if equipButton then
            local on = st.selected ~= nil and st.selected == st.equippedId
            equipButton.Text = if on then "EQUIPPED" else "EQUIP"
            equipButton.BackgroundColor3 = if on then C.card else C.accent
        end
    end
    for _, attribute in {"EquippedSpeciesId", "EquippedGenesJson", "EquippedShiny", "EquippedBig", "EquippedEventMutation"} do
        table.insert(connections, player:GetAttributeChangedSignal(attribute):Connect(function() if st.loaded then refreshEquipped() end end))
    end

    local function selectCopy(id: string)
        if st.selected == id then return end
        st.selected = id
        for key, entry in cards do
            entry.stroke.Color = if key == id then C.gold else C.outline
            entry.stroke.Thickness = if key == id then 5 else 3
        end
        buildLeft()
    end

    local function fillDetails(d: any)
        local list, label = traitsList, titleLabel
        if not list or not label then return end
        for _, child in list:GetChildren() do if child:IsA("TextLabel") then child:Destroy() end end
        local response = st.details[d.instanceId]
        if response == "loading" then
            W.label(list, "Loading details...", UDim2.new(1, -10, 0, 26), UDim2.new(), 18, C.gold, true)
            return
        end
        if type(response) ~= "table" then
            W.label(list, "Details unavailable. Tap the dino again.", UDim2.new(1, -10, 0, 40), UDim2.new(), 18, C.red, true)
            return
        end
        local view = Sel.details(response, catalog)
        label.Text = view.title
        local order = 0
        local function line(text: string, color: Color3?)
            order += 1
            local l = W.label(list, text, UDim2.new(1, -10, 0, if #text > 30 then 40 else 22), UDim2.new(), 17, color, true)
            l.LayoutOrder = order
        end
        for _, row in view.traits do line(row.label .. ": " .. row.value, if row.label == "Stage" then C.gold else nil) end
        line(view.prestige or "", C.gold)
    end

    local function loadDetails(d: any)
        local id = d.instanceId
        if st.details[id] ~= nil and st.details[id] ~= "loading" then fillDetails(d) return end
        st.details[id] = "loading"
        fillDetails(d)
        task.spawn(function()
            local response = call({action = "details", instanceId = id})
            st.details[id] = if type(response) == "table" and response.ok == true and type(response.dinosaur) == "table" then response.dinosaur else nil
            if root.Parent and st.selected == id then fillDetails(d) end
        end)
    end

    buildLeft = function()
        if hero then hero.destroy() hero = nil end
        left:ClearAllChildren()
        local d = if st.selected then st.byId[st.selected] else nil
        local stageName = if d then d.stage else ctx.fallbackStage
        local backdrop = if stageName == "base" or stageName == nil then ctx.color else (StageColors[stageName] or ctx.color)
        local stage = W.box(left, UDim2.fromOffset(296, 196), UDim2.new(), backdrop, 24)
        stage.ClipsDescendants = true
        local view = Preview.add(stage, speciesId, if stageName == nil then "base" else stageName)
        view.Size, view.Position = UDim2.fromScale(1, 1), UDim2.new()
        PreviewTraits.add(view, if d then {shiny = d.shiny, big = d.big, mutationId = if d.stage == "base" then d.mutationId else nil, genes = if d.stage == "base" then d.genes else nil} else nil)
        hero = InspectView.attach(view, {hintPosition = UDim2.new(.5, 0, 0, 34), resetPosition = UDim2.new(1, -6, 0, 6)})
        titleLabel = W.label(left, speciesName, UDim2.fromOffset(296, 26), UDim2.fromOffset(0, 200), 22, C.text)
        if not d then
            W.label(left, ctx.fallbackLine, UDim2.fromOffset(296, 100), UDim2.fromOffset(0, 232), 20)
        else
            local list = W.scroll(left, UDim2.fromOffset(296, 108), UDim2.fromOffset(0, 228))
            W.list(list, 2)
            traitsList = list
            loadDetails(d)
        end
        local equip = W.button(left, "EQUIP", UDim2.fromOffset(196, math.max(52, T)), UDim2.fromOffset(0, 402 - math.max(52, T)), C.accent, function()
            if d then
                if st.equippedId == d.instanceId then ctx.notify("Already equipped", C.gold) return end
                local request = MyDinos.equipRequest(d)
                if request then ctx.equip(request.speciesId, request.variantKey) end
            else
                ctx.equip(speciesId, nil)
            end
        end)
        equip.Name, equipButton = "Equip", equip
        backButton(UDim2.fromOffset(204, 402 - math.max(52, T)), UDim2.fromOffset(92, math.max(52, T)))
        if st.loaded then refreshEquipped() end
    end

    local openSheet: () -> ()

    local function buildCard(d: any, order: number, parent: GuiObject)
        local button = Instance.new("TextButton")
        button.Name, button.Text, button.AutoButtonColor, button.LayoutOrder = "Dino_" .. order, "", false, order
        button.BackgroundColor3 = StageColors[d.stage] or StageColors.base
        Theme.decorate(button, 8)
        local stroke = button:FindFirstChildOfClass("UIStroke") :: UIStroke
        stroke.Color, stroke.Thickness = if d.instanceId == st.selected then C.gold else C.outline, if d.instanceId == st.selected then 5 else 3
        button.Parent = parent
        button.Activated:Connect(function() selectCopy(d.instanceId) end)
        local g = d.genes or {}
        local previewView: ViewportFrame? = nil
        local entryRef: any = nil
        local function mount()
            if previewView then return end
            local view = Preview.add(button, speciesId, if d.stage == "base" then "base" else d.stage)
            view.Position, view.Size = UDim2.fromOffset(4, 4), UDim2.new(1, -8, 0, 74)
            if d.stage == "base" and (d.genes or (d.mutationId or "") ~= "") then PreviewTraits.add(view, {genes = d.genes, mutationId = d.mutationId}) end
            previewView = view
            entryRef.mounted = true
        end
        local function unmount()
            if previewView then previewView:Destroy() previewView = nil end
            entryRef.mounted = false
        end
        pill(button, string.upper(Sel.stageTitle(d.stage)), StageColors[d.stage] or StageColors.base, UDim2.fromOffset(62, 16), UDim2.new(1, -68, 0, 7), if d.stage == "base" then C.text else C.outline)
        local y = 7
        for _, text in MyDinos.ribbons(d, catalog) do
            if y > 45 then break end
            pill(button, text, if text == "SHINY" then C.gold else C.purple, UDim2.fromOffset(54, 16), UDim2.fromOffset(7, y), if text == "SHINY" then C.outline else C.text)
            y += 19
        end
        W.label(button, Sel.name(catalog, "patterns", g.patternId, "Plain"), UDim2.new(1, -8, 0, 17), UDim2.fromOffset(4, 82), 14)
        W.swatch(button, g, UDim2.new(1, -16, 0, 9), UDim2.fromOffset(8, 101))
        local tag = pill(button, "EQUIPPED", C.accent, UDim2.new(1, -8, 0, 17), UDim2.fromOffset(4, 115), C.outline)
        tag.Visible = d.instanceId == st.equippedId
        cards[d.instanceId] = {stroke = stroke, tag = tag, button = button, index = order, mount = mount, unmount = unmount, mounted = false}
        entryRef = cards[d.instanceId]
    end

    local function updateWindow()
        local g = grid
        if not g then return end
        local total = 0
        for _ in cards do total += 1 end
        local first, last = MyDinos.window(g.CanvasPosition.Y, g.AbsoluteWindowSize.Y / math.max(.3, ctx.scale()), 138, 8, 4, total)
        for _, entry in cards do
            if entry.index >= first and entry.index <= last then entry.mount() else entry.unmount() end
        end
    end

    local function buildGrid()
        local target = grid
        if not target then return end
        for _, child in target:GetChildren() do if not child:IsA("UIGridLayout") then child:Destroy() end end
        table.clear(cards)
        local view = viewList()
        if #view == 0 then
            local empty = W.label(right, "No dinos match, clear filters", UDim2.fromOffset(516, 44), UDim2.fromOffset(0, 150), 24, C.gold)
            empty.Name = "EmptyState"
            W.button(right, "CLEAR FILTERS", UDim2.fromOffset(220, T), UDim2.fromOffset(148, 204), C.blue, function()
                st.chosen, st.sortKey = {}, "rarest"
                empty:Destroy()
                buildRight()
            end).Name = "ClearFilters"
            return
        end
        local count, more = MyDinos.page(view, st.visible)
        for i = 1, count do buildCard(view[i], i, target) end
        updateWindow()
        if more > 0 then
            local b = W.button(target, "SHOW MORE (" .. more .. ")", UDim2.new(), UDim2.new(), C.blue, function()
                st.visible += MyDinos.PageSize
                buildGrid()
            end)
            b.LayoutOrder = count + 1
        end
    end

    buildRight = function()
        right:ClearAllChildren()
        grid, filterButton = nil, nil
        if not st.loaded then
            W.label(right, "Loading your dinos...", UDim2.fromOffset(516, 44), UDim2.fromOffset(0, 150), 26, C.gold)
            return
        end
        W.label(right, MyDinos.header(speciesName, #st.list), UDim2.fromOffset(300, 44), UDim2.new(), 32, ctx.color:Lerp(C.text, .35), true).Name = "Header"
        local active = MyDinos.activeChips(st.chosen, catalog)
        local sortChanged = st.sortKey ~= "rarest"
        local count = #active + (if sortChanged then 1 else 0)
        local fb = W.button(right, if count > 0 then "SORT / FILTER (" .. count .. ")" else "SORT / FILTER", UDim2.fromOffset(204, T), UDim2.fromOffset(312, 0), C.purple, function() openSheet() end)
        fb.Name, filterButton = "FilterButton", fb
        local top = 50
        if #active > 0 then
            local row = Instance.new("ScrollingFrame")
            row.Name, row.Size, row.Position = "ActiveFilters", UDim2.fromOffset(516, T + 4), UDim2.fromOffset(0, 48)
            row.BackgroundTransparency, row.BorderSizePixel, row.ScrollBarThickness = 1, 0, 0
            row.ScrollingDirection, row.AutomaticCanvasSize, row.CanvasSize = Enum.ScrollingDirection.X, Enum.AutomaticSize.X, UDim2.new()
            row.Parent = right
            W.list(row, 6, true)
            for _, chip in active do
                chipButton(row, chip.text .. "  X", T, true, if chip.group == "colorId" then W.colorOf(chip.value) else nil, function()
                    st.chosen[chip.group] = nil
                    st.visible = MyDinos.PageSize
                    st.selected = MyDinos.settleSelection(viewList(), st.selected)
                    buildRight()
                    buildLeft()
                end)
            end
            top = 48 + T + 8
        end
        local g = W.scroll(right, UDim2.fromOffset(516, 402 - top), UDim2.fromOffset(0, top))
        g.Name = "DinoCards"
        local layout = Instance.new("UIGridLayout")
        layout.CellSize, layout.CellPadding, layout.SortOrder = UDim2.fromOffset(120, 138), UDim2.fromOffset(8, 8), Enum.SortOrder.LayoutOrder
        layout.Parent = g
        grid = g
        table.insert(connections, g:GetPropertyChangedSignal("CanvasPosition"):Connect(updateWindow))
        buildGrid()
        local settled = MyDinos.settleSelection(viewList(), st.selected)
        if settled ~= st.selected then st.selected = settled buildLeft() end
    end

    -- Sort and filter sheet ---------------------------------------------------------------------------
    openSheet = function()
        if right:FindFirstChild("FilterSheet") then return end
        local sheet = Instance.new("Frame")
        sheet.Name, sheet.Size, sheet.BackgroundColor3, sheet.ZIndex = "FilterSheet", UDim2.fromOffset(516, 402), C.panel, 10
        Theme.decorate(sheet, 12)
        sheet.Active = true
        sheet.Parent = right
        W.label(sheet, "Sort and filter", UDim2.fromOffset(250, 40), UDim2.fromOffset(12, 4), 28, C.gold, true).ZIndex = 11
        local function close()
            sheet:Destroy()
            st.visible = MyDinos.PageSize
            st.selected = MyDinos.settleSelection(viewList(), st.selected)
            buildRight()
            buildLeft()
        end
        local done = W.button(sheet, "DONE", UDim2.fromOffset(110, T), UDim2.new(1, -118, 0, 4), C.accent, close)
        done.ZIndex = 11
        local clear = W.button(sheet, "CLEAR", UDim2.fromOffset(110, T), UDim2.new(1, -236, 0, 4), C.red, function()
            st.chosen, st.sortKey = {}, "rarest"
            sheet:Destroy()
            openSheet()
        end)
        clear.ZIndex = 11
        local list = W.scroll(sheet, UDim2.new(1, -16, 1, -(T + 14)), UDim2.fromOffset(8, T + 10))
        list.ZIndex = 11
        W.list(list, 6)
        local options = MyDinos.options(st.list, catalog)
        local order = 0
        local function addRow(title: string, items: {any}, groupId: string?)
            if #items == 0 then return end
            order += 1
            local row = Instance.new("Frame")
            row.Name, row.Size, row.BackgroundTransparency, row.LayoutOrder, row.ZIndex = "Row_" .. title, UDim2.new(1, -10, 0, T + 24), 1, order, 11
            row.Parent = list
            local caption = W.label(row, title, UDim2.new(1, 0, 0, 20), UDim2.new(), 16, C.blue, true)
            caption.ZIndex = 11
            local chips = Instance.new("ScrollingFrame")
            chips.Name, chips.Size, chips.Position, chips.BackgroundTransparency = "Chips", UDim2.new(1, 0, 0, T + 4), UDim2.fromOffset(0, 22), 1
            chips.BorderSizePixel, chips.ScrollBarThickness, chips.ZIndex = 0, 0, 11
            chips.ScrollingDirection, chips.AutomaticCanvasSize, chips.CanvasSize = Enum.ScrollingDirection.X, Enum.AutomaticSize.X, UDim2.new()
            chips.Parent = row
            W.list(chips, 6, true)
            for _, item in items do
                local on, text, swatch
                if groupId then
                    on = st.chosen[groupId] == item
                    text = MyDinos.valueName(groupId, item, catalog)
                    swatch = if groupId == "colorId" then W.colorOf(item) else nil
                else
                    on = st.sortKey == item
                    text = MyDinos.SortLabels[item]
                end
                chipButton(chips, text, T, on, swatch, function()
                    if groupId then st.chosen[groupId] = if st.chosen[groupId] == item then nil else item else st.sortKey = item end
                    local scroll = list.CanvasPosition
                    sheet:Destroy()
                    openSheet()
                    local again = right:FindFirstChild("FilterSheet")
                    if again then
                        local l = again:FindFirstChildOfClass("ScrollingFrame")
                        if l then l.CanvasPosition = scroll end
                    end
                end).ZIndex = 12
            end
        end
        addRow("Sort by", MyDinos.SortKeys, nil)
        for _, group in MyDinos.FilterGroups do addRow(MyDinos.GroupLabels[group], options[group] or {}, group) end
    end

    -- Load every copy of this species, then build the grid; fall back to the species-only page on failure.
    local answered = false
    loadAll(ctx.revision(), function(ok: boolean)
        answered = true
        if not root.Parent then return end
        if not ok then
            right:ClearAllChildren()
            W.label(right, "Could not load your dinos", UDim2.fromOffset(516, 44), UDim2.fromOffset(0, 140), 26, C.red)
            W.button(right, "TRY AGAIN", UDim2.fromOffset(220, T), UDim2.fromOffset(148, 196), C.blue, function()
                cache.revision = -1
                root:Destroy()
                Panels.species(ctx)
            end)
            return
        end
        st.list = MyDinos.forSpecies(cache.dinos, speciesId)
        st.byId = {}
        for _, d in st.list do st.byId[d.instanceId] = d end
        st.loaded = true
        st.selected = MyDinos.defaultSelection(st.list, catalog)
        -- Hero first: it takes the scarce EditableImages (pattern textures) before the card previews do.
        if st.selected then buildLeft() end
        buildRight()
        refreshEquipped()
    end)
    if not answered then
        buildLeft()
        buildRight()
    end
    return root
end

return Panels
