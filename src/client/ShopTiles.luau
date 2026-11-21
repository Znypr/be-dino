--!strict
-- BD-047: Crystal Shop art, drawing only. Rules and ids come from Shared.ShopArt (tested by tools/verify_shop_tiles.py); the images are
-- Blender renders (tools/blender/build_shop_tiles.py). Every function does nothing, and today's look stays, while its image slot is empty.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Slots = require(Shared.AssetSlots)
local Art = require(Shared.ShopArt)
local C = Theme.Colors
-- BD-1237: the style rules for the landing tiles while Config.MenusCohesionEnabled is on (nil = the old slate tiles).
local Cohesion = if (require(Shared.Config) :: any).MenusCohesionEnabled == true then require(Shared.MenusCohesionRules) else nil
local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
-- BD-1254 (docs/243, owner 2026-11-17): with Config.MenusTopLookEnabled each landing tile is filled with its own colour (proposal sheet panel 4).
local TopLook = (require(game:GetService("ReplicatedStorage"):WaitForChild("Shared"):WaitForChild("Config")) :: any).MenusTopLookEnabled == true
-- BD-1287 (docs/246 slice 1): with Config.MenusSaeFrameEnabled the landing page is the compact Steal-an-Egg window with the outside rail (ShopSaeLanding).
local SaeFrame = (require(Shared.Config) :: any).MenusSaeFrameEnabled == true

local Tiles = {}
-- true when the shop was opened from SHOP / the crystal counter and the landing page should show instead of a category.
Tiles.landing = false

local function image(parent: GuiObject, name: string, id: string, anchor: Vector2, position: UDim2, size: UDim2, z: number): ImageLabel
    local img = Instance.new("ImageLabel")
    img.Name, img.BackgroundTransparency, img.BorderSizePixel, img.Image, img.ScaleType = name, 1, 0, id, Enum.ScaleType.Fit
    img.AnchorPoint, img.Position, img.Size, img.ZIndex, img.Parent = anchor, position, size, z, parent
    return img
end

-- The live numbers the tile subtitles read: p = the decoded progression profile.
function Tiles.info(p: any, eggPrice: number, crystals: number, randomBlocked: boolean?): {[string]: number}
    return {auras = Art.countOwned(p.auras), trails = Art.countOwned(p.trails), eggPrice = eggPrice, crystals = crystals, randomBlocked = if randomBlocked then 1 else 0}
end

-- Decide whether the next shop open starts on the landing page (call before open("auras")).
function Tiles.enter(tabs: {string})
    Tiles.landing = Art.landingReady(Slots.Images, tabs)
end

-- A leading icon on a shop tab button (the button keeps its text). No icon id: nothing changes.
function Tiles.decorateTab(button: TextButton, tab: string, height: number)
    local id = Art.tabIconId(Slots.Images, tab)
    if not id then return end
    local layout = Art.tabLayout(true, height)
    local pad = Instance.new("UIPadding")
    pad.PaddingLeft = UDim.new(0, layout.pad)
    pad.Parent = button
    -- children sit inside the padded area, so the icon steps back out by the pad
    image(button, "TabIcon", id, Vector2.new(0, .5), UDim2.new(0, 4 - layout.pad, .5, 0), UDim2.fromOffset(layout.icon, layout.icon), button.ZIndex + 1)
    button.TextSize = layout.textSize
end

-- The Eggs product picture: the green-spotted egg when its id exists. Returns true when it drew (the caller then skips the old egg).
function Tiles.eggProduct(parent: GuiObject, x: number, y: number, size: number): boolean
    local id = Art.eggProductId(Slots.Images)
    if not id then return false end
    image(parent, "GreenSpottedEgg", id, Vector2.zero, UDim2.fromOffset(x, y), UDim2.fromOffset(size, size), parent.ZIndex + 1)
    return true
end

-- The landing page: one tall illustrated tile per visible tab. ui = Bootstrap's {label, box}; spec = {tabs, info, onPick(tab)}.
-- Each tile is ONE button (the whole card), far larger than the 44 px tap target. Words are live text, never baked into the picture.
Tiles.TopLookFill = {eggs = {255, 200, 64}, auras = {255, 122, 107}, trails = {96, 196, 255}, conditions = {186, 128, 255}, crystals = {255, 176, 72}}
function Tiles.build(ui, body: GuiObject, spec)
    if SaeFrame and require(script.Parent.ShopSaeLanding).build(body, spec) then return end
    local layout = Art.tileLayout(#spec.tabs)
    local total = #spec.tabs * layout.width + (#spec.tabs - 1) * Art.TileGap
    local x0 = math.floor((824 - total) / 2)
    for i, tab in spec.tabs do
        local x = x0 + (i - 1) * (layout.width + Art.TileGap)
        local card = Instance.new("TextButton")
        card.Name, card.Text, card.AutoButtonColor = "ShopTile_" .. tab, "", true
        card.Position, card.Size, card.BackgroundColor3 = UDim2.fromOffset(x, 0), UDim2.fromOffset(layout.width, layout.height), Color3.fromRGB(61, 58, 73)
        card.ZIndex, card.Parent = body.ZIndex + 1, body
        Theme.decorate(card, 8)
        local picture = Art.tileId(Slots.Images, tab)
        if picture then
            image(card, "TileArt", picture, Vector2.zero, UDim2.fromOffset(6, 4), UDim2.fromOffset(layout.image, layout.image), card.ZIndex + 1)
        end
        local title = ui.label(card, Art.Titles[tab], 0, layout.image + 6, layout.width, 34, 24)
        title.Name = "TileTitle"
        local sub = ui.label(card, Art.subtitle(tab, spec.info), 4, layout.image + 40, layout.width - 8, 48, 18, C.gold)
        sub.Name = "TileSubtitle"
        local open = ui.box(card, 8, layout.height - 50, layout.width - 16, 44, C.accent, card.ZIndex + 1)
        open.Name = "TileOpen"
        local words = ui.label(open, "OPEN", 0, 0, layout.width - 16, 44, 22)
        words.Name = "TileOpenText"
        if Cohesion then -- BD-1237 (docs/240 step 4): a cream card with ink words (no gold words on a slate card, R1 R2 R4), OPEN grey (R3: four green buttons were four main buttons)
            card.BackgroundColor3 = rgb(Cohesion.Cream)
            local g = card:FindFirstChildOfClass("UIGradient") if g then g:Destroy() end
            for _, label in {title, sub} do
                label.TextColor3, label.TextStrokeTransparency = rgb(if label == title then Cohesion.Ink else Cohesion.Muted), 1
                for _, child in label:GetChildren() do if child:IsA("UIStroke") then child.Enabled = false end end
            end
            sub.Text = string.gsub(sub.Text, "%d%d%d%d+", function(n: string): string return Cohesion.grouped(tonumber(n) or 0) end)
            open.BackgroundColor3 = Color3.fromRGB(128, 142, 158)
            -- the Toybox skin turns every TextButton into a gloss button picture (grey face, transparent body): a cream card frame sits under the
            -- words and the picture instead, and the grey face is hidden whenever the skin adds it
            local back = Instance.new("Frame")
            back.Name, back.Size, back.BackgroundColor3, back.BorderSizePixel, back.ZIndex = "CreamCard", UDim2.fromScale(1, 1), rgb(Cohesion.Cream), 0, card.ZIndex
            local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, 12), back
            local line = Instance.new("UIStroke") line.Color, line.Thickness, line.Parent = rgb(Cohesion.Outline), Cohesion.Toast.stroke, back
            back.Parent = card
            local function hideFace()
                local face = card:FindFirstChild("ToyboxFace")
                if face and face:IsA("GuiObject") then face.Visible = false end
            end
            card.ChildAdded:Connect(function() task.defer(hideFace) end)
            task.defer(hideFace)
            local fill = Tiles.TopLookFill[tab]
            if TopLook and fill then -- BD-1254 (docs/243 G4/G5): the tile in its own colour, white outlined words, a green OPEN on every tile
                back.BackgroundColor3 = rgb(fill)
                for _, label in {title, sub} do
                    label.TextColor3, label.TextStrokeTransparency, label.TextStrokeColor3 = Color3.new(1, 1, 1), 0, rgb(Cohesion.Outline)
                end
                open.BackgroundColor3 = C.accent
            end
        end
        card.Activated:Connect(function() spec.onPick(tab) end)
    end
end

return Tiles
