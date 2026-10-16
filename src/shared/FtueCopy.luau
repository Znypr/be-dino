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

return Copy
