--!strict
-- BD-1039 / docs/186 s7: the three tabs at the TOP of the Index screen, Dinos | Patterns | Colours, and the small dot on the Dinos button.
-- Behind Config.PatternColourIndexEnabled (false in the default build: mount() and attachDot() return at once and touch nothing).
--   * The tab bar lives in the blue header strip, where the title "Dino Index" was (the title is hidden while the tabs show), left of the X.
--     It is as tall as the X button, so on a phone it keeps the 44 px floor too. No new HUD button.
--   * Bootstrap's "collection" screen calls mount(open) first. On the Dinos tab mount returns false and Bootstrap draws the Dino Index as
--     always; on Patterns or Colours mount draws the cards into the body and returns true. The last tab is remembered for the session.
--   * Tapping Dinos asks Bootstrap to open the collection again (open("collection")); tapping Patterns or Colours redraws the body here.
--   * A marker frame sits in the body. Bootstrap clears the body when ANY screen opens, which destroys the marker; that removes the tab bar
--     and shows the title again, so no other screen has to know the tabs exist.
--   * The dot: shown on the Dinos button while more patterns and colours are found than the last time the Patterns or Colours tab was
--     looked at. The first reading in a session is the baseline (what you already had is not "new"); it is kept in memory only.
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Theme = require(Shared:WaitForChild("UITheme"))
local AssetSlots = require(Shared:WaitForChild("AssetSlots"))
local ProgressionConfig = require(Shared:WaitForChild("ProgressionConfig"))
local Index = require(Shared:WaitForChild("PatternColourIndex"))
local Secret = require(Shared:WaitForChild("SecretSpeciesConfig"))
local PrivateState = require(script.Parent.PrivateState)
local Compact = require(script.Parent.ModalCompact)
local Cards = require(script.Parent.PatternColourCards)

local Tabs = {}
local C = Theme.Colors

local lastTab = "dinos"
local seenTotal: number? = nil
local dot: Frame? = nil

local function decode(name: string): any
    local raw = PrivateState.str(name, "")
    if raw == "" then return {} end
    local ok, data = pcall(function() return HttpService:JSONDecode(raw) end)
    return if ok and typeof(data) == "table" then data else {}
end

local function speciesOrder(): {string}
    return Secret.indexOrder(Config.SpeciesOrder, Config.SecretSpeciesEnabled)
end

local function speciesName(id: any): string
    return (Config.SpeciesDisplayNames :: any)[id] or Secret.name(id)
end

-- What this player has found right now (the discovery log merged with the dinos they own).
function Tabs.found()
    return Index.foundSets(decode("CollectionJson"), decode("DiscoveryJson"), speciesOrder())
end

function Tabs.lastTab(): string return lastTab end

-- ---------------------------------------------------------------- the dot on the Dinos button
local function refreshDot()
    if dot == nil or not PrivateState.isReady() then return end
    local total = Index.foundTotal(Tabs.found(), ProgressionConfig.EggPatterns, ProgressionConfig.EggColors)
    if seenTotal == nil then seenTotal = total end -- the first reading is the baseline
    dot.Visible = Index.dotVisible(total, seenTotal)
end

local function markSeen()
    seenTotal = Index.foundTotal(Tabs.found(), ProgressionConfig.EggPatterns, ProgressionConfig.EggColors)
    refreshDot()
end

-- buttons = the nav buttons (each has a "Destination" attribute); the dot goes on the one that opens the collection.
function Tabs.attachDot(buttons: {any})
    if Config.PatternColourIndexEnabled ~= true or dot ~= nil then return end
    for _, b in buttons do
        if b:GetAttribute("Destination") == "collection" then
            local d = Instance.new("Frame")
            d.Name, d.AnchorPoint, d.Position, d.Size = "IndexDot", Vector2.new(1, 0), UDim2.new(1, -4, 0, 4), UDim2.fromOffset(18, 18)
            d.BackgroundColor3, d.Visible, d.ZIndex, d.Parent = C.red, false, b.ZIndex + 6, b
            local corner = Instance.new("UICorner")
            corner.CornerRadius = UDim.new(0.5, 0)
            corner.Parent = d
            local edge = Instance.new("UIStroke")
            edge.Color, edge.Thickness, edge.Parent = C.text, 2, d
            dot = d
            break
        end
    end
    if dot == nil then return end
    for _, name in {"CollectionJson", "DiscoveryJson"} do PrivateState.onChanged(name, refreshDot) end
    refreshDot()
end

-- ---------------------------------------------------------------- the tab bar
local TAB_NAMES = Index.TabNames
local barParts: {bar: Frame?} = {bar = nil}

-- PLACEHOLDER (docs/72): a tiny glyph in code until the tab icons exist (AssetSlots.Images.index_tab_patterns / index_tab_colours).
local function glyph(parent: GuiObject, tab: string, color: Color3)
    local holder = Instance.new("Frame")
    holder.Name, holder.BackgroundTransparency, holder.Position, holder.Size, holder.ZIndex, holder.Parent = "TabIcon", 1, UDim2.new(0, 10, 0.5, -19), UDim2.fromOffset(38, 38), parent.ZIndex + 1, parent
    local slot = AssetSlots.image("index_tab_" .. tab)
    if slot then
        local img = Instance.new("ImageLabel")
        img.BackgroundTransparency, img.Image, img.Size, img.ScaleType, img.ZIndex, img.Parent = 1, slot, UDim2.fromScale(1, 1), Enum.ScaleType.Fit, holder.ZIndex + 1, holder
        return
    end
    holder.Name = "PlaceholderGlyph"
    if tab == "dinos" then
        local art = Theme.icon(holder, (require(Shared:WaitForChild("NavigationArtwork")) :: any).collection or "dinos")
        if art then art.Position, art.Size = UDim2.fromOffset(0, 0), UDim2.fromOffset(38, 38) end
    elseif tab == "patterns" then
        for i = 0, 3 do
            local sq = Instance.new("Frame")
            sq.Position, sq.Size, sq.ZIndex, sq.Parent = UDim2.fromOffset((i % 2) * 20, math.floor(i / 2) * 20), UDim2.fromOffset(17, 17), holder.ZIndex + 1, holder
            sq.BackgroundColor3 = if (i == 0 or i == 3) then color else Color3.fromRGB(255, 210, 43)
            local corner = Instance.new("UICorner")
            corner.CornerRadius = UDim.new(0, 4)
            corner.Parent = sq
        end
    else
        for i, c in {Color3.fromRGB(247, 57, 48), Color3.fromRGB(255, 210, 43), Color3.fromRGB(46, 206, 255)} do
            local dotShape = Instance.new("Frame")
            dotShape.Position, dotShape.Size, dotShape.ZIndex, dotShape.Parent = UDim2.fromOffset((i - 1) * 11, if i == 2 then 14 else 2), UDim2.fromOffset(18, 18), holder.ZIndex + 1, holder
            dotShape.BackgroundColor3 = c
            local corner = Instance.new("UICorner")
            corner.CornerRadius = UDim.new(0.5, 0)
            corner.Parent = dotShape
        end
    end
end

local function removeBar()
    local bar = barParts.bar
    barParts.bar = nil
    if bar ~= nil and bar.Parent ~= nil then bar:Destroy() end
end

local function renderTab(parts: any, tab: string, mark: Frame?)
    local body = parts.body :: GuiObject
    for _, child in body:GetChildren() do
        if child ~= mark then child:Destroy() end
    end
    local rows = if tab == "colours" then ProgressionConfig.EggColors else ProgressionConfig.EggPatterns
    local cards = Index.cards(tab, rows, Tabs.found(), speciesName)
    local header = Index.header(tab, cards)
    local height = math.max(180, math.min(402, Compact.bodyHeight()) - 46)
    Cards.build(body, tab, cards, header.text, "Hatch eggs to find more!", height)
    markSeen()
end

local function build(parts: any, mark: Frame, open: (string) -> ())
    local header, heading, close = parts.header :: GuiObject, parts.heading :: TextLabel, parts.closeButton :: GuiObject
    removeBar()
    local bar = Instance.new("Frame")
    bar.Name, bar.BackgroundTransparency, bar.ZIndex, bar.Parent = "IndexTabs", 1, header.ZIndex + 1, header
    bar.Position = UDim2.fromOffset(8, close.Position.Y.Offset)
    bar.Size = UDim2.new(1, -(close.Size.X.Offset + 22), 0, close.Size.Y.Offset) -- as tall as X: keeps the 44 px floor on a phone
    barParts.bar = bar
    heading.Visible = false
    local buttons: {[string]: TextButton} = {}
    local function paint()
        for tab, b in buttons do
            local on = tab == lastTab
            b.BackgroundColor3 = if on then C.text else C.blue:Lerp(C.outline, 0.55)
            local text = b:FindFirstChild("TabText") :: TextLabel?
            if text then text.TextColor3 = if on then C.outline else C.text Theme.TextStyle.apply(text) end
            b:SetAttribute("Active", on)
        end
    end
    for i, tab in Index.Tabs do
        local b = Instance.new("TextButton")
        b.Name, b.Text, b.AutoButtonColor, b.ZIndex = "Tab_" .. tab, "", false, bar.ZIndex + 1
        b.Position, b.Size, b.Parent = UDim2.new((i - 1) / 3, 3, 0, 0), UDim2.new(1 / 3, -6, 1, 0), bar
        b.BackgroundColor3 = C.blue
        Theme.decorate(b, 10)
        glyph(b, tab, C.blue)
        local text = Instance.new("TextLabel")
        text.Name, text.BackgroundTransparency, text.Position, text.Size = "TabText", 1, UDim2.new(0, 54, 0, 0), UDim2.new(1, -58, 1, 0)
        text.Font, text.TextSize, text.Text, text.TextXAlignment, text.ZIndex, text.Parent = Enum.Font.FredokaOne, 24, TAB_NAMES[tab], Enum.TextXAlignment.Left, b.ZIndex + 1, b
        buttons[tab] = b
        b.Activated:Connect(function()
            if tab == lastTab or mark.Parent == nil then return end
            lastTab = tab
            paint()
            if tab == "dinos" then open("collection") else renderTab(parts, tab, mark) end
        end)
    end
    paint()
    mark.Destroying:Connect(function() -- Bootstrap cleared the body for another screen: the tabs go, the title returns
        if barParts.bar == bar then removeBar() end
        heading.Visible = true
    end)
end

-- Called first thing by Bootstrap's "collection" screen. open = Bootstrap's open(name). Returns true when this module drew the screen.
function Tabs.mount(open: (string) -> ()): boolean
    if Config.PatternColourIndexEnabled ~= true then return false end
    local parts = Compact.parts()
    if parts == nil then return false end
    local body = (parts :: any).body :: GuiObject
    local mark = Instance.new("Frame")
    mark.Name, mark.BackgroundTransparency, mark.Size, mark.Parent = "IndexTabsMark", 1, UDim2.fromOffset(0, 0), body
    lastTab = Index.validTab(lastTab)
    build(parts, mark, open)
    if lastTab == "dinos" then return false end
    renderTab(parts, lastTab, mark)
    return true
end

return Tabs
