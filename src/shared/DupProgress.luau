--!strict
-- BD-1170 part A (docs/221 C1 #5 and C3 #2, docs/227): a duplicate shows progress toward the next fusion step. Pure: no Instances,
-- services, RNG or remotes. Behind Config.DupProgressEnabled (default false, on only in the playtest profile).
--
-- ONE count rule: a copy counts exactly when the Fusion Menu would let the player put it in a slot, i.e.
-- FusionSelection.ineligibility(d, {targetStage, speciesId, patternId}) == nil (right stage, has a pattern, not locked, not a
-- favourite, same species, and the same pattern except for Gold). Nothing here re-states that rule; Shiny, BIG, mutation and
-- cosmetic copies count because the menu lets the player pick them (it only does not auto-fill them).
-- The recipes (6 Base / 3 Gold / 2 Emerald) come from FusionSelection.Stages. Exercised by tools/verify_dup_progress.py.
local Sel = require(script.Parent.FusionSelection)

local Dup = {}

-- A hatch line needs at least this many countable copies after the hatch: with 1 it is not a duplicate yet.
Dup.MinForLine = 2
-- Seconds without a hatch event before the copy list may be re-read (the egg counts are published a moment after a result).
Dup.QuietSeconds = 1
-- An egg that was opened but never answered (menu closed mid-party) stops blocking a re-read after this many seconds.
Dup.OpenTimeout = 5

-- Copies the Fusion Menu would accept for this step. Gold: every eligible Base copy of the species. Emerald and Diamond need one
-- pattern, so the best-stocked pattern counts (the same group FusionSelection.bestGroup picks). Returns count, patternId?.
function Dup.count(dinos: any, speciesId: string, stageId: string): (number, string?)
    local recipe = Sel.stage(stageId)
    if type(dinos) ~= "table" or not recipe or not recipe.approved then return 0, nil end
    local total, groups = 0, {} :: {[string]: number}
    local best, bestPattern = 0, nil :: string?
    for _, d in dinos do
        if type(d) == "table" and Sel.ineligibility(d, {targetStage = stageId, speciesId = speciesId}) == nil then
            total += 1
            local pattern = d.genes.patternId :: string -- ineligibility already refused a copy without one
            local n = (groups[pattern] or 0) + 1
            groups[pattern] = n
            if n > best or (n == best and bestPattern ~= nil and pattern < bestPattern) then best, bestPattern = n, pattern end
        end
    end
    if recipe.anyPattern then return total, nil end
    return best, bestPattern
end

-- {stageId, name, have, need, ready, fraction} for one step of one species, or nil for an unknown / unapproved step.
function Dup.step(dinos: any, speciesId: string, stageId: string, extra: number?): any
    local recipe = Sel.stage(stageId)
    if not recipe or not recipe.approved then return nil end
    local have, pattern = Dup.count(dinos, speciesId, stageId)
    have += math.max(0, math.floor(extra or 0))
    local need = recipe.donorCount
    return {stageId = stageId, name = recipe.name, have = have, need = need, ready = have >= need,
        fraction = math.clamp(have / need, 0, 1), patternId = pattern}
end

-- The words (docs/72: short, no "x", no fractions). "3 of 6 for Gold!", "Ready for Gold!"; nil below one copy.
function Dup.text(step: any): string?
    if type(step) ~= "table" or step.have < 1 then return nil end
    if step.ready then return "Ready for " .. step.name .. "!" end
    return string.format("%d of %d for %s!", step.have, step.need, step.name)
end

-- What is still missing, for the Index line: "1 more to go", "3 more to go"; the ready state says what to do.
function Dup.hint(step: any): string
    if step.ready then return "Tap to fuse!" end
    local left = step.need - step.have
    return left .. " more to go"
end

-- The hatch line: only for a real duplicate (MinForLine), only toward Gold (an egg always gives Base dinos).
function Dup.hatchLine(have: number?): any
    local recipe = Sel.stage("gold")
    if not recipe or not recipe.approved or type(have) ~= "number" or have < Dup.MinForLine then return nil end
    local step = {stageId = "gold", name = recipe.name, have = have, need = recipe.donorCount, ready = have >= recipe.donorCount}
    return {text = Dup.text(step) :: string, ready = step.ready}
end

-- The Index species page: one entry per step the player has started (Gold always while a Base copy counts; Emerald with a Gold;
-- Diamond with an Emerald), in ladder order. Each: {stageId, name, have, need, ready, fraction, text, hint}.
function Dup.speciesSteps(dinos: any, speciesId: string): {any}
    local result = {}
    for _, recipe in Sel.Stages do
        local step = Dup.step(dinos, speciesId, recipe.id)
        if step and step.have >= 1 then
            step.text, step.hint = Dup.text(step), Dup.hint(step)
            table.insert(result, step)
        end
    end
    return result
end

-- Hatch counting ---------------------------------------------------------------------------------------------------------
-- "3 of 6" must be the count AFTER this hatch, but the server can be ahead of the screen (a page of eggs is settled at once and
-- revealed one by one). So the screen never asks the server during a hatch party: it keeps the last quiet copy list (base) and
-- adds the copies it has revealed since (extra). A new list is taken only while nothing is hatching, and it is thrown away when a
-- hatch started before it arrived. No list yet = no line (never a wrong number).
function Dup.tracker()
    return {base = nil :: any, extra = {} :: {[string]: number}, events = 0, openAt = nil :: number?, lastEvent = -math.huge,
        requested = nil :: number?}
end

-- An egg started opening (its result is not here yet).
function Dup.opened(t: any, now: number)
    t.events += 1
    t.openAt, t.lastEvent = now, now
end

-- The result of the opening egg arrived: copies = dinos it gave (0 for a failed egg). Returns the count after this hatch, or nil
-- while no copy list is known.
function Dup.hatched(t: any, speciesId: string, copies: number, now: number): number?
    t.events += 1
    t.openAt, t.lastEvent = nil, now
    copies = math.max(0, math.floor(copies))
    if copies > 0 then t.extra[speciesId] = (t.extra[speciesId] or 0) + copies end
    return Dup.have(t, speciesId)
end

function Dup.have(t: any, speciesId: string): number?
    if t.base == nil then return nil end
    return (Dup.count(t.base, speciesId, "gold")) + (t.extra[speciesId] or 0)
end

-- True while nothing is hatching: no egg waits for its answer, the last hatch event is QuietSeconds old, no revealed-later eggs
-- are buffered and no request is on its way.
function Dup.quiet(t: any, now: number, buffered: number): boolean
    if buffered > 0 or t.requested ~= nil then return false end
    if t.openAt ~= nil and now - t.openAt < Dup.OpenTimeout then return false end
    return now - t.lastEvent >= Dup.QuietSeconds
end

-- Call right before asking the server for the copy list; pass the returned token to Dup.arrived.
function Dup.request(t: any): number
    t.requested = t.events
    return t.events
end

-- The list arrived (dinos = nil when the request failed). Accepted only when no hatch event happened since the request and
-- nothing is buffered; then the revealed-since counters start again at zero. Returns true when accepted.
function Dup.arrived(t: any, token: number, dinos: any, buffered: number): boolean
    t.requested = nil
    if type(dinos) ~= "table" or token ~= t.events or buffered > 0 then return false end
    t.base, t.extra = dinos, {}
    return true
end

-- "2x Compy" on the reveal's name label = 2 copies; a plain name = 1.
function Dup.copiesFromName(text: any): number
    if type(text) ~= "string" then return 1 end
    return tonumber(string.match(text, "^(%d+)x ")) or 1
end

return Dup
