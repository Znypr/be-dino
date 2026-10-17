--!strict
-- BD-394 (docs/87, docs/72): pure rules for the Conditions shop "stage" art slot. The owner's Blender render stage is
-- resources/ui/v2/stage/egg-stage-jungle-v1.jpg (jungle floor) plus resources/ui/v2/stage/eggs/egg-0N_<condition>.png (five
-- condition eggs). Until the owner uploads them, ProgressionConfig.ConditionStageAssetIds has no entries and the shop keeps its
-- current live egg tiles. Ids are never invented: only "rbxassetid://<digits>" strings are accepted, anything else is nil.
local Rules = {}
Rules.Keys = {"stage", "normal", "cracked", "dirty", "rainbow", "astra"}
Rules.Files = {
    stage = "resources/ui/v2/stage/egg-stage-jungle-v1.jpg",
    cracked = "resources/ui/v2/stage/eggs/egg-01_cracked.png", dirty = "resources/ui/v2/stage/eggs/egg-02_dirty.png",
    normal = "resources/ui/v2/stage/eggs/egg-03_normal.png", rainbow = "resources/ui/v2/stage/eggs/egg-04_rainbow.png",
    astra = "resources/ui/v2/stage/eggs/egg-05_astra.png",
}
-- ids = ProgressionConfig.ConditionStageAssetIds (or nil); key = "stage" or a condition id. Returns the asset string or nil.
function Rules.assetId(ids: any, key: string): string?
    if type(ids) ~= "table" then return nil end
    local id = ids[key]
    if type(id) == "string" and string.match(id, "^rbxassetid://%d+$") then return id end
    return nil
end
-- What the shop draws for one condition: {stage = id|nil (shared backdrop), egg = id|nil (this condition's picture)}.
-- A condition egg picture only counts when the stage is also bound, so a half-uploaded set never shows a floating cut-out.
function Rules.resolve(ids: any, conditionId: string): {stage: string?, egg: string?}
    local stage = Rules.assetId(ids, "stage")
    local egg = if stage then Rules.assetId(ids, conditionId) else nil
    return {stage = stage, egg = egg}
end

-- BD-208 / BD-094: the Eggs page "hero" stage. The jungle image is square (1024 x 1024) and so are the five condition eggs, drawn on the
-- SAME square canvas with the egg centred (about 30% to 70% across, 21% to 74% down). The stage frame is therefore a SQUARE and both images
-- use ScaleType Fit, so nothing is ever stretched or cropped on a phone. The egg is enlarged around the pedestal (top centre at about
-- 50% across, 72% down), keeping its base on the stone: EggScale 1.25 stays inside the frame (top edge at about 6%).
Rules.Hero = {MaxSide = 300, MinSide = 120, EggScale = 1.25, PedestalX = .5, PedestalY = .74}
-- The square side for the stage: as large as the free box allows, never wider than MaxSide. Always an integer.
function Rules.heroSide(width: number, height: number): number
    return math.floor(math.clamp(math.min(width, height), Rules.Hero.MinSide, Rules.Hero.MaxSide))
end
-- Which condition egg picture an Eggs page egg uses: a real condition id, else "normal" (unknown or missing data is never an error).
function Rules.conditionKey(conditionId: any): string
    if type(conditionId) == "string" then
        for _, key in Rules.Keys do
            if key ~= "stage" and key == conditionId then return key end
        end
    end
    return "normal"
end
return Rules
