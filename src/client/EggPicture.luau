--!strict
-- BD-169 / BD-175: a flat egg picture from the official Blender egg render (uploaded "egg" icon, premium-egg-normal.png),
-- tinted with the egg's colour mix, with the condition look (Cracked, Dirty, Rainbow, Astra) as a transparent overlay layer.
-- Both PNGs share one 512 px canvas (premium-egg-bindings.json), so the layers line up without trimming.
-- The shell image has large transparent margins; IconLayout.egg scales it up inside the box (no clipping).
-- No 3D viewport, no cube, no plain ellipse: if the egg image id is ever empty a soft ellipse is shown instead.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Overlays = require(Shared.ConditionOverlays)
local EggGenetics = require(Shared.EggGenetics)
local IconLayout = require(Shared.UIIconLayout)
local ModelPreview = require(Shared.ModelPreview)
local EggAppearance = require(Shared.EggAppearance)

local EggPicture = {}

-- genes: egg genes table or nil (plain cream egg). size in pixels (square box). Returns the box Frame.
function EggPicture.add(parent: GuiObject, genes: any, size: number): Frame
    local root = Instance.new("Frame")
    root.Name, root.BackgroundTransparency, root.Size, root.ZIndex, root.Parent = "EggPicture", 1, UDim2.fromOffset(size, size), parent.ZIndex + 1, parent
    local valid = genes ~= nil and EggGenetics.valid(genes)
    local shell = Theme.ImageIds.egg
    if shell == nil or shell == "" then
        local fallback = Instance.new("Frame")
        fallback.Name, fallback.BackgroundColor3, fallback.AnchorPoint = "EggFallback", Color3.fromRGB(255, 244, 214), Vector2.new(.5, .5)
        fallback.Position, fallback.Size, fallback.ZIndex, fallback.Parent = UDim2.fromScale(.5, .5), UDim2.fromScale(.6, .8), root.ZIndex, root
        local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(.5, 0) corner.Parent = fallback
        return root
    end
    local scale = IconLayout.egg or 1
    local function layer(name: string, image: string, z: number): ImageLabel
        local item = Instance.new("ImageLabel")
        item.Name, item.BackgroundTransparency, item.BorderSizePixel, item.Image = name, 1, 0, image
        item.AnchorPoint, item.Position, item.Size = Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromScale(scale, scale)
        item.ScaleType, item.ZIndex, item.Parent = Enum.ScaleType.Fit, z, root
        return item
    end
    local base = layer("EggShell", shell, root.ZIndex)
    if valid then base.ImageColor3 = EggGenetics.tint(genes) end
    if valid and genes.conditionId then
        local look = Overlays.describe(genes.conditionId)
        if look.assetId ~= "" then
            layer("EggCondition", "rbxassetid://" .. look.assetId, root.ZIndex + 1)
        end
    end
    return root
end

-- BD-392: the big "same as the hatch" egg: the authored 3D egg with this dino's colours, PATTERN and condition baked through
-- EggAppearance.apply (the very call the hatch uses; patterns go through PatternAtlasCache, so the shared image budget holds).
-- If the 3D egg is not available the 2D picture fallback (tint + condition layer) is used, and the flat EggPicture when even that
-- cannot be built. genes = egg genes or nil (plain egg). size in pixels. Returns the frame holding the egg.
function EggPicture.baked(parent: GuiObject, genes: any, size: number): Frame
    local root = Instance.new("Frame")
    root.Name, root.BackgroundTransparency, root.Size, root.ZIndex, root.Parent = "BakedEgg", 1, UDim2.fromOffset(size, size), parent.ZIndex + 1, parent
    local ok, view = pcall(ModelPreview.add, root, "egg", genes == nil)
    if ok and view then
        view.Name = "BakedEggView"
        if genes ~= nil and EggGenetics.valid(genes) then EggAppearance.apply(view, genes, true) end
        root:SetAttribute("EggKind", if view:GetAttribute("EggImageFallback") == true then "Image" else "Model3D")
        view:SetAttribute("InspectZoom", 1.45)
        return root
    end
    root:Destroy()
    local flat = EggPicture.add(parent, genes, size)
    flat:SetAttribute("EggKind", "Flat")
    return flat
end

-- Soft tile-floor look the egg stands on (PLACEHOLDER until the Blender tile-floor render is uploaded; docs/77 "egg_stage").
-- A calm warm floor with a light checker of rounded tiles; one frame per tile, capped so phones stay cheap.
function EggPicture.stage(parent: GuiObject, width: number, height: number, accent: Color3): Frame
    local root = Instance.new("Frame")
    root.Name, root.BackgroundColor3, root.BorderSizePixel, root.ClipsDescendants = "TileFloor", accent:Lerp(Color3.fromRGB(255, 244, 214), .72), 0, true
    root.Size, root.ZIndex, root.Parent = UDim2.fromOffset(width, height), parent.ZIndex + 1, parent
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 18) corner.Parent = root
    local step = math.max(44, math.ceil(math.sqrt(width * height / 60)))
    local count = 0
    for row = 0, math.ceil(height / step) do
        for column = 0, math.ceil(width / step) do
            if (row + column) % 2 == 0 and count < 70 then
                count += 1
                local tile = Instance.new("Frame")
                tile.Name, tile.BackgroundColor3, tile.BackgroundTransparency, tile.BorderSizePixel = "Tile", Color3.new(1, 1, 1), .72, 0
                tile.Position, tile.Size, tile.ZIndex, tile.Parent = UDim2.fromOffset(column * step + 3, row * step + 3), UDim2.fromOffset(step - 6, step - 6), root.ZIndex, root
                local tileCorner = Instance.new("UICorner") tileCorner.CornerRadius = UDim.new(0, 8) tileCorner.Parent = tile
            end
        end
    end
    return root
end

return EggPicture
