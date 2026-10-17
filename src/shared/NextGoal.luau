--!strict
-- Polish pass: pure "next goal" HUD line. No Instances, services or remotes.
-- Best fusion progress across species + pattern (from the FusionAction list data) wins; when that data
-- is unavailable or nothing is in progress the line falls back to account-level XP progress.
-- Exercised by tools/verify_next_goal.py.
local NextGoal = {}
-- Mirrors FusionSelection.Stages (docs/58). Callers may pass opts.stages to stay in sync.
NextGoal.Stages = {
    {id = "gold", name = "Gold", source = "base", donorCount = 6, anyPattern = true},
    {id = "emerald", name = "Emerald", source = "gold", donorCount = 3},
    {id = "diamond", name = "Diamond", source = "emerald", donorCount = 2},
}

-- Returns the best in-progress (or ready) fusion goal, or nil.
function NextGoal.fusion(dinos: any, opts: any)
    if type(dinos) ~= "table" then return nil end
    local stages = opts.stages or NextGoal.Stages
    local counts: {[string]: number} = {}
    for _, d in dinos do
        if type(d) == "table" and not d.locked then
            local pattern = if type(d.genes) == "table" then d.genes.patternId else nil
            if type(d.speciesId) == "string" and type(pattern) == "string" and type(d.stage) == "string" then
                local key = d.stage .. "|" .. d.speciesId .. "|" .. pattern
                counts[key] = (counts[key] or 0) + 1
                -- Any-pattern recipes (Gold) count the whole species.
                local anyKey = d.stage .. "|" .. d.speciesId .. "|*"
                counts[anyKey] = (counts[anyKey] or 0) + 1
            end
        end
    end
    local best = nil
    for key, count in counts do
        local stageId, species, pattern = string.match(key, "^([^|]*)|([^|]*)|(.*)$")
        for _, stage in stages do
            if stage.source == stageId and ((pattern == "*") == (stage.anyPattern == true)) then
                local have = math.min(count, stage.donorCount)
                local fraction = have / stage.donorCount
                local ready = count >= stage.donorCount
                -- Prefer ready, then fraction, then smaller recipe, then name (deterministic).
                local score = (if ready then 2 else 0) + fraction
                local tier = stage.donorCount
                local name = stage.name .. "|" .. species .. "|" .. pattern
                if not best or score > best.score or (score == best.score and (tier < best.tier or (tier == best.tier and name < best.name))) then
                    best = {score = score, tier = tier, name = name, stage = stage, species = species, pattern = pattern, have = have, fraction = fraction, ready = ready}
                end
            end
        end
    end
    if not best then return nil end
    local label = if opts.speciesName then opts.speciesName(best.species) else best.species
    local patternLabel = if best.pattern == "*" then "" elseif opts.patternName then opts.patternName(best.pattern) else best.pattern
    patternLabel = if patternLabel == "" then "" else " " .. patternLabel
    local text = if best.ready then string.format("%s ready: fuse %s%s", best.stage.name, label, patternLabel)
        else string.format("%s: %d/%d %s%s", best.stage.name, best.have, best.stage.donorCount, label, patternLabel)
    return {kind = "fusion", text = text, fraction = best.fraction, ready = best.ready}
end

-- Level XP progress. Level L starts at (L-1)^2 * perLevel xp (ProgressionRules.level).
function NextGoal.level(opts: any)
    local perLevel, maxLevel = opts.perLevel or 100, opts.maxLevel or 60
    local xp = math.max(0, tonumber(opts.xp) or 0)
    local level = tonumber(opts.level)
    if not level then level = math.min(maxLevel, 1 + math.floor(math.sqrt(xp / perLevel))) end
    level = math.clamp(level, 1, maxLevel)
    if level >= maxLevel then return {kind = "level", text = "Level " .. level .. " (max)", fraction = 1} end
    local floorXp, nextXp = (level - 1) ^ 2 * perLevel, level ^ 2 * perLevel
    local into = math.clamp(xp - floorXp, 0, nextXp - floorXp)
    return {kind = "level", text = string.format("Level %d: %d/%d XP", level, into, nextXp - floorXp), fraction = into / (nextXp - floorXp)}
end

-- BD-076 (docs/66 s19): opts.objective is the top objective already worded and fitted for the line ({text, claimable, fraction}) or nil.
-- Only while Config.ObjectivesEnabled is true does a caller pass one; nil (flag off, no answer yet, nothing to show) = the line is exactly the old one.
local function asObjective(o: any)
    return {kind = "objective", text = o.text, fraction = tonumber(o.fraction) or 0, ready = o.claimable == true, claimable = o.claimable == true}
end

-- Priority, highest first (one rule, docs/66 s19):
--   1. a CLAIMABLE objective            ("Done! Claim ..."), it is free crystals waiting
--   2. the fusion goal                  (best in-progress or ready recipe), beats an unfinished objective
--   3. an unfinished objective          ("Hatch 3 eggs: 1/3"), beats the level fallback
--   4. level XP progress                (the fallback)
-- opts: dinos (list or nil), level, xp, perLevel, maxLevel, stages, speciesName(id), patternName(id), objective (optional, see above)
function NextGoal.pick(opts: any)
    local objective = opts.objective
    local usable = type(objective) == "table" and type(objective.text) == "string" and objective.text ~= ""
    if usable and objective.claimable == true then return asObjective(objective) end
    local fusion = NextGoal.fusion(opts.dinos, opts)
    if fusion then return fusion end
    if usable then return asObjective(objective) end
    return NextGoal.level(opts)
end
return NextGoal
