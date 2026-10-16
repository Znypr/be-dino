--!strict
-- BD-440: Run Complete body (was inline in Bootstrap). Reserved trophy slot so nothing jumps while the image loads;
-- one row per fact with an icon (eggs, crystals, nests); no duplicate egg line; Growth hidden at 0 (docs/72, docs/114).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Copy = require(Shared.FtueCopy)

local RunComplete = {}

local ICON = {eggs = "egg", crystals = "amber", nests = "egg_nest", nestCrystals = "amber", growth = "leaf"}

-- d: {body, C, label, box, art, button, num, oops, hasEggs, back, openEggs}
function RunComplete.build(d: any)
    local body, C, oops = d.body, d.C, d.oops
    local slot = d.box(body, 30, 46 + oops, 220, 220, C.panel, body.ZIndex + 1) -- reserved: sized before the trophy image loads
    d.art(slot, "trophy", 10, 10, 200)
    local rows = Copy.runCompleteRows({
        eggs = d.num("LastRunCatchScore"), crystals = d.num("LastRunCrystals"), nests = d.num("LastRunNestCount"),
        nestCrystals = d.num("LastRunNestCrystals"), growth = d.num("LastRunGrowthScore"),
    })
    local color = {eggs = C.blue, crystals = C.gold, nests = C.accent, nestCrystals = C.gold, growth = C.accent}
    local y = 20 + oops
    for _, row in rows do
        local kind = row[1]
        local primary = kind == "eggs" or kind == "crystals"
        local h = if primary then 64 else 44
        d.art(body, ICON[kind] or "leaf", 280, y + 4, h - 8)
        local text = d.label(body, row[2], 280 + h, y, 800 - 280 - h, h, if primary then 38 else 26, color[kind])
        text.TextXAlignment = Enum.TextXAlignment.Left
        y += h + 6
    end
    local level = d.label(body, "Level " .. d.num("AccountLevel"), 30, 282, 220, 36, 24, C.gold)
    level.TextXAlignment = Enum.TextXAlignment.Center
    d.button(body, "BACK TO SANCTUARY", if d.hasEggs then 30 else 212, 348, if d.hasEggs then 370 else 400, 48, C.accent, d.back)
    if d.hasEggs then d.button(body, "OPEN EGGS", 424, 348, 370, 48, C.gold, d.openEggs) end
end

return RunComplete
