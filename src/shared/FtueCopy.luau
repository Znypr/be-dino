--!strict
-- First-time-player copy (docs/112 audit, BD-370). Plain words for 7 to 10 year olds (docs/72): no "catches",
-- "banked" or "bank". Pure strings, no Instances. Checked by tools/verify_ftue_copy.py.
local Copy = {}

Copy.tutorialSteps = {
    { "1", "EAT & GROW", "Walk into food to eat it. Eat lots to find eggs!" },
    { "2", "JUMP & EXPLORE", "Space to jump, E to leap. Buttons on phone." },
    { "3", "SAVE & HATCH", "Tap HOME to save your eggs. Then open them!" },
}

Copy.homeConfirmLine = "Your run ends and your eggs are saved."

local function plural(n: number, one: string, many: string): string
    return if n == 1 then "1 " .. one else string.format("%d %s", n, many)
end

-- "You found 1 egg  •  Growth 65" (was "Banking 1 catches  •  65 growth")
function Copy.homeConfirmTotals(eggs: number, growth: number): string
    return string.format("You found %s  •  Growth %d", plural(eggs, "egg", "eggs"), math.floor(growth))
end

Copy.runCompleteEggsLabel = "Eggs found"

-- BD-448: Run Complete rows from LastRun* state, one fact per row, no duplicates. Pure: {{kind, text}}.
-- kinds: eggs, hunting (only when > 0), crystals, nests, nestCrystals, growth (growth is hidden at 0).
function Copy.runCompleteRows(s: {eggs: number?, crystals: number?, nests: number?, nestCrystals: number?, growth: number?, killEggs: number?}): {{string}}
    local rows = {{"eggs", string.format("%s  %d", Copy.runCompleteEggsLabel, s.eggs or 0)}}
    table.insert(rows, {"crystals", string.format("+%d Crystals", s.crystals or 0)})
    local kills = s.killEggs or 0
    if kills > 0 then table.insert(rows, {"hunting", string.format("Hunting bonus: +%s", plural(kills, "egg", "eggs"))}) end
    local nests = s.nests or 0
    if nests > 0 then table.insert(rows, {"nests", string.format("+%s", plural(nests, "nest", "nests"))}) end
    if (s.nestCrystals or 0) > 0 then table.insert(rows, {"nestCrystals", string.format("Extra nests: +%d Crystals", s.nestCrystals)}) end
    if math.floor(s.growth or 0) > 0 then table.insert(rows, {"growth", string.format("Growth  %d", math.floor(s.growth))}) end
    return rows
end

-- Sanctuary card (smoke test 2026-10-16: it still said "clusters" and "Bank catches")
Copy.sanctuaryTip1 = "Eat food to grow. Jump over hills. Stay away from bigger dinos!"
Copy.sanctuaryTip2 = "Tap HOME to save your eggs, then open them."

return Copy
