--!strict
-- BD-236: the catch-time glue of FoodService as a pure module (no Roblox services, no attributes), so it is unit tested
-- (tools/verify_mutations.py). One catch = one run egg. Only an egg that is really added (after > before) during
-- weather rolls the weather mutation, ONCE per catch ordinal, with that weather's own chance; clear weather and catches
-- that add no egg (carry, per-run cap) roll nothing and tag nothing. The tag never looks at the egg condition: a Cracked
-- egg that later fails to hatch loses its mutation at hatch time (docs/99 G2, owner decision BD-235), not here.
local Rules = require(script.Parent.ProgressionRules)
local Tags = {}

-- New CatchScore after `whole` eggs are earned, never above the score cap or the per-run egg cap.
function Tags.nextScore(before: number, whole: number, maxScore: number, runCap: number): number
    return math.min(maxScore, runCap, before + whole)
end

-- Appends one compact tag {eventId, mutationId, n = catch ordinal} per egg earned in (before, after] during weather
-- (mutationId is "" unless that egg's roll hit the weather chance; this keeps the legacy FoodService format). `events` is the
-- already decoded RunEggEvents list (mutated in place and returned). roll() returns a number in [0,1).
-- Returns the list and how many MUTATED tags were added.
function Tags.apply(events: {any}, weatherId: string, before: number, after: number, roll: () -> number): ({any}, number)
    local added = 0
    if after <= before or weatherId == "clear" then return events, 0 end
    for n = before + 1, after do
        local tag = Rules.eventEgg(weatherId, roll())
        if tag.eventId ~= "clear" then
            tag.n = n
            table.insert(events, tag)
            if tag.mutationId ~= "" then added += 1 end
        end
    end
    return events, added
end

return Tags
