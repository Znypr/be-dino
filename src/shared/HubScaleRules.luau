--!strict
-- BD-480 (OWNER 2026-10-16, docs/104 s2.4, docs/115): every dinosaur is exactly 1x in the cave hub, whatever its BIG trait,
-- potions or growth. Pure numbers and tables only (no Instances, no Config require) so the server (Dinosaur.luau) and
-- tools/verify_hub_scale.py run this same file. The size curve moved here from Dinosaur.luau unchanged.
-- Potions never change the drawn size: Growth Sip .. Titan Tonic only raise the GrowthMultiplier (how fast GrowthScore
-- rises), so "no potion effect in the hub" is automatic; this file only decides the SCALE that is drawn.
-- Behind Config.CaveHub (state.caveHub): with the flag false nothing here changes any scale.
local HubScaleRules = {}
HubScaleRules.HubScale = 1 -- the cave hub size of every dinosaur
HubScaleRules.MaxGrowthScale = 4 -- same cap as DinosaurVisual / HudRules (BIG multiplies on top of it)

local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end

-- Growth-curve scale for a GrowthScore (CODE since BD-386: min(4, sqrt(1 + growth / 50))).
function HubScaleRules.growthScale(score: any): number
    local s = if finite(score) then math.max(0, score :: number) else 0
    return math.min(HubScaleRules.MaxGrowthScale, math.sqrt(1 + s / 50))
end

-- The size on the island: growth curve times the BIG trait multiplier (unchanged behaviour).
function HubScaleRules.islandScale(score: any, big: any, bigMultiplier: any): number
    local factor = if big == true and finite(bigMultiplier) then bigMultiplier :: number else 1
    return HubScaleRules.growthScale(score) * factor
end

-- state = {caveHub, inHub, score, big, bigMultiplier}. In the cave hub (flag on AND the root is inside the hub) the answer is
-- always 1; everywhere else it is the island size. The run's own score/BIG are untouched, so leaving the hub restores them.
function HubScaleRules.scale(state: any): number
    if typeof(state) ~= "table" then return 1 end
    if state.caveHub == true and state.inHub == true then return HubScaleRules.HubScale end
    return HubScaleRules.islandScale(state.score, state.big, state.bigMultiplier)
end

return HubScaleRules
