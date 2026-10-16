--!strict
-- BD-394: draws the owner's Blender "egg stage" (jungle backdrop + per-condition egg picture) in the Conditions shop when the
-- ids in ProgressionConfig.ConditionStageAssetIds exist. Returns false/nil when nothing is bound so the caller keeps the
-- current live egg tiles (never an empty hole). Pure choice lives in ConditionStageRules.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Progression = require(Shared:WaitForChild("ProgressionConfig"))
local Rules = require(Shared:WaitForChild("ConditionStageRules"))

local Stage = {}

local function image(parent: GuiObject, name: string, id: string, z: number): ImageLabel
    local item = Instance.new("ImageLabel")
    item.Name, item.BackgroundTransparency, item.BorderSizePixel, item.Image = name, 1, 0, id
    item.Size, item.ZIndex, item.ScaleType, item.Parent = UDim2.fromScale(1, 1), z, Enum.ScaleType.Crop, parent
    return item
end

-- One jungle backdrop under a row of condition tiles. True when drawn.
function Stage.background(parent: GuiObject, x: number, y: number, width: number, height: number): boolean
    local id = Rules.assetId((Progression :: any).ConditionStageAssetIds, "stage")
    if not id then return false end
    local frame = Instance.new("Frame")
    frame.Name, frame.BackgroundTransparency, frame.ClipsDescendants = "ConditionStage", 1, true
    frame.Position, frame.Size, frame.ZIndex, frame.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(width, height), parent.ZIndex + 1, parent
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 24) corner.Parent = frame
    image(frame, "StageImage", id, frame.ZIndex)
    return true
end

-- The condition's egg picture inside its tile. True when drawn (needs the stage too, see Rules.resolve).
function Stage.egg(tile: GuiObject, conditionId: string): boolean
    local pick = Rules.resolve((Progression :: any).ConditionStageAssetIds, conditionId)
    if not pick.egg then return false end
    local item = image(tile, "ConditionEgg", pick.egg, tile.ZIndex + 1)
    item.ScaleType = Enum.ScaleType.Fit
    return true
end

return Stage
