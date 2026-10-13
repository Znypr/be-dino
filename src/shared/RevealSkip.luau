--!strict
-- BD-044 reveal skipping (PROVISIONAL). Pure client/server-neutral selection logic.
-- A skipped egg is still hatched and credited by the server; skipping only drops the
-- animation. Notable finds (Shiny, BIG, event mutation, Rainbow/Astra) are never skipped.
-- The stored selection is a UI preference: the server never uses it for rewards.
local Skip = {}
Skip.Rarities = {1, 2, 3} -- Config.SpeciesRarities values: Common / Rare / Legendary
Skip.Names = {"Common", "Rare", "Legendary"}

-- Accepts any list of rarity numbers; returns a sorted, de-duplicated, valid list.
function Skip.normalize(list: any): {number}
    local seen, result = {}, {}
    if typeof(list) ~= "table" then return result end
    for _, value in list do
        if typeof(value) == "number" and value % 1 == 0 and value >= 1 and value <= #Skip.Names and not seen[value] then
            seen[value] = true
            table.insert(result, value)
        end
    end
    table.sort(result)
    return result
end

function Skip.set(list: any): {[number]: boolean}
    local set = {}
    for _, rarity in Skip.normalize(list) do set[rarity] = true end
    return set
end

function Skip.toggle(list: any, rarity: number): {number}
    local set = Skip.set(list)
    if rarity >= 1 and rarity <= #Skip.Names and rarity % 1 == 0 then set[rarity] = if set[rarity] then nil else true end
    local result = {}
    for value in set do table.insert(result, value) end
    table.sort(result)
    return result
end

-- outcome: {big, shiny, eventMutationId, genes={conditionId}, failed}
function Skip.isNotable(outcome: any): boolean
    if typeof(outcome) ~= "table" then return true end -- unknown data is never hidden
    if outcome.shiny == true or outcome.big == true then return true end
    if typeof(outcome.eventMutationId) == "string" and outcome.eventMutationId ~= "" then return true end
    local genes = outcome.genes
    if typeof(genes) == "table" and (genes.conditionId == "rainbow" or genes.conditionId == "astra") then return true end
    return false
end

function Skip.shouldSkip(selection: any, rarity: number, outcome: any): boolean
    if not Skip.set(selection)[rarity] then return false end
    return not Skip.isNotable(outcome)
end

-- entries: {{rarity=number, outcome=table, speciesId=string?}}
function Skip.summarize(entries: {any})
    local summary = {total = #entries, byRarity = {0, 0, 0}, failed = 0, hatched = 0, notable = {}}
    for _, entry in entries do
        local rarity = math.clamp(entry.rarity or 1, 1, #Skip.Names)
        summary.byRarity[rarity] += 1
        if entry.outcome and entry.outcome.failed == true then summary.failed += 1 else summary.hatched += 1 end
        if Skip.isNotable(entry.outcome) then table.insert(summary.notable, entry) end
    end
    return summary
end

function Skip.lines(summary: any): {string}
    local lines = {string.format("%d eggs skipped (%d hatched, %d cracked)", summary.total, summary.hatched, summary.failed)}
    local parts = {}
    for rarity, count in summary.byRarity do
        if count > 0 then table.insert(parts, string.format("%d %s", count, Skip.Names[rarity])) end
    end
    if #parts > 0 then table.insert(lines, table.concat(parts, "  |  ")) end
    return lines
end

return Skip
