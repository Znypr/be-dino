--!strict
-- BD-065 / BD-062 pure client-side fusion logic. No Instances, services, RNG or
-- remotes: filtering, sorting, eligibility reasons, plain-only auto-fill, odds
-- formatting, retry-token bookkeeping, reveal-wheel construction and Dino Details
-- view models. The server (FusionAction remote) stays authoritative for every rule;
-- this module only explains and previews. Exercised by tools/verify_fusion_ui.py.
local Sel = {}

-- OWNER DECISION 2026-10-15 (docs/90): Gold = 6 Base of the same species (ANY pattern; the
-- Gold keeps the most common pattern), Emerald = 3 Gold, Diamond = 2 Emerald (same species +
-- same pattern); all three tiers active. Mirrors IdentityFusion.Recipes (verify_fusion_ui.py
-- asserts they match).
Sel.Stages = {
    {id = "gold", name = "Gold", source = "base", donorCount = 6, anyPattern = true, approved = true},
    {id = "emerald", name = "Emerald", source = "gold", donorCount = 3, approved = true},
    {id = "diamond", name = "Diamond", source = "emerald", donorCount = 2, approved = true},
}
-- Largest recipe; kept for older callers. Use Sel.donorCount(stage) instead.
Sel.DonorCount = 6
function Sel.donorCount(stageId: string?): number?
    for _, s in Sel.Stages do if s.id == stageId and s.approved then return s.donorCount end end
    return nil
end
-- Above this many slots the menu shows a compact n/N counter grid instead of cards.
Sel.CompactSlotThreshold = 10 -- unused by the 6/3/2 ladder (max 6 slots)
Sel.LockedStageText = "Recipe not approved yet"

local function stageInfo(id: string?)
    for _, s in Sel.Stages do if s.id == id then return s end end
    return nil
end
Sel.stage = stageInfo
function Sel.stageTitle(id: string?): string
    if id == "base" then return "Base" end
    local s = stageInfo(id)
    return if s then s.name else tostring(id)
end

-- Display catalog ------------------------------------------------------------------
local function titleCase(text: string): string
    return (string.gsub(text, "(%a)([%w]*)", function(a, b) return string.upper(a) .. b end))
end
function Sel.patternName(id: string?): string
    if type(id) ~= "string" or id == "" then return "Unknown pattern" end
    local stripped = string.gsub(string.gsub(id, "^%d+_", ""), "_", " ")
    return titleCase(stripped)
end

-- Builds name lookups from the shared config tables (passed in to stay pure).
-- Player-facing drop chance text: 26 -> "26%", 12.5 -> "12.5%", 0.04 -> "0.04%" (docs/85). Percent in, string out.
function Sel.pct(p: number): string
    local s = string.format("%.2f", p)
    if string.find(s, ".", 1, true) then s = string.gsub(s, "0+$", "") s = string.gsub(s, "%.$", "") end
    return s .. "%"
end

function Sel.buildCatalog(config, progression, patterns)
    local catalog = {species = {}, speciesOrder = {}, patterns = {}, patternOrder = {}, colors = {},
        colorOrder = {}, mutations = {}, mutationOrder = {}, auras = {}, trails = {}}
    for id, name in (config and config.SpeciesDisplayNames) or {} do catalog.species[id] = name end
    -- Base odds of ONE purchased egg (no run boost): species by weight, patterns equally likely, colors per slot by weight.
    catalog.speciesPct, catalog.speciesRarity, catalog.patternPct, catalog.colorPct = {}, {}, {}, {}
    local speciesTotal = 0
    for _, row in (config and config.ChestSpeciesWeights) or {} do speciesTotal += row.weight end
    for _, row in (config and config.ChestSpeciesWeights) or {} do
        catalog.speciesPct[row.speciesId] = if speciesTotal > 0 then 100 * row.weight / speciesTotal else 0
        local tier = config.SpeciesRarities and config.SpeciesRarities[row.speciesId]
        catalog.speciesRarity[row.speciesId] = tier and config.SpeciesRarityNames and config.SpeciesRarityNames[tier] or nil
    end
    for _, id in patterns or {} do catalog.patternPct[id] = 100 / math.max(1, #(patterns :: any)) end
    local colorTotal = 0
    for _, row in (progression and progression.EggColors) or {} do colorTotal += row.weight end
    for _, row in (progression and progression.EggColors) or {} do catalog.colorPct[row.id] = if colorTotal > 0 then 100 * row.weight / colorTotal else 0 end
    for i, id in (config and config.SpeciesOrder) or {} do catalog.speciesOrder[id] = i end
    for i, id in patterns or {} do catalog.patterns[id] = Sel.patternName(id) catalog.patternOrder[id] = i end
    for i, row in (progression and progression.EggColors) or {} do catalog.colors[row.id] = row.name catalog.colorOrder[row.id] = i end
    for i, row in (progression and progression.EventMutations) or {} do catalog.mutations[row.id] = row.name catalog.mutationOrder[row.id] = i end
    for _, row in (progression and progression.Auras) or {} do catalog.auras[row.id] = row.name end
    for _, row in (progression and progression.Trails) or {} do catalog.trails[row.id] = row.name end
    return catalog
end

local function lookup(catalog, group: string, id: any, fallback: string?): string
    if type(id) ~= "string" or id == "" then return fallback or "None" end
    local names = catalog and catalog[group]
    local name = names and names[id]
    if name then return name end
    if group == "patterns" then return Sel.patternName(id) end
    return titleCase((string.gsub(id, "_", " ")))
end
Sel.name = lookup

local function genes(d) return if type(d) == "table" and type(d.genes) == "table" then d.genes else {} end
local function mutationOf(d): string
    return if type(d.mutationId) == "string" and d.mutationId ~= "" then d.mutationId else "none"
end

-- Donor classification -------------------------------------------------------------
-- Cosmetic-bearing means any instance-bound aura/trail ownership or equip (BD-059).
function Sel.hasCosmetics(d): boolean
    return (tonumber(d.auraCount) or 0) > 0 or (tonumber(d.trailCount) or 0) > 0
        or (type(d.equippedAuraId) == "string" and d.equippedAuraId ~= "")
        or (type(d.equippedTrailId) == "string" and d.equippedTrailId ~= "")
end

-- Reasons a donor is valuable: these are never auto-filled and are highlighted
-- when chosen manually. Order is stable for display.
function Sel.valuableReasons(d): {string}
    local reasons = {}
    if d.shiny == true then table.insert(reasons, "shiny") end
    if d.big == true then table.insert(reasons, "big") end
    if mutationOf(d) ~= "none" then table.insert(reasons, "mutation") end
    if Sel.hasCosmetics(d) then table.insert(reasons, "cosmetics") end
    return reasons
end
function Sel.isPlain(d): boolean
    return #Sel.valuableReasons(d) == 0 and d.locked ~= true and d.favorited ~= true
end

-- Card words for children (docs/96): short, plain, say what is wrong.
Sel.ReasonText = {
    wrong_stage = "Not the right stage",
    missing_pattern = "Hatch new dinos to fuse", -- BD-381: the card above says "Older dino" (no saved pattern); kids learn what to do, not a rule word
    species_mismatch = "Different dino",
    pattern_mismatch = "Different pattern",
    locked = "Locked",
    favorited = "Favourite",
    recipe_not_approved = "Not ready yet",
    full = "Slots are full",
}

-- Context: {targetStage, speciesId?, patternId?} where species/pattern come from the
-- current selection (anchor) or an explicit filter. Returns reason code or nil.
function Sel.ineligibility(d, ctx): string?
    local recipe = stageInfo(ctx and ctx.targetStage or "gold")
    if not recipe or not recipe.approved then return "recipe_not_approved" end
    if d.stage ~= recipe.source then return "wrong_stage" end
    local g = genes(d)
    if type(g.patternId) ~= "string" or g.patternId == "" then return "missing_pattern" end
    if d.locked == true then return "locked" end
    if d.favorited == true then return "favorited" end
    if ctx and ctx.speciesId and d.speciesId ~= ctx.speciesId then return "species_mismatch" end
    if ctx and ctx.patternId and not recipe.anyPattern and g.patternId ~= ctx.patternId then return "pattern_mismatch" end
    return nil
end

-- The recipe anchor is defined by the first selected donor, else by explicit filters.
function Sel.context(targetStage: string, selection, byId, filters)
    local ctx = {targetStage = targetStage}
    local first = selection and selection[1] and byId[selection[1]]
    if first then
        ctx.speciesId, ctx.patternId = first.speciesId, genes(first).patternId
    elseif filters then
        ctx.speciesId = if filters.speciesId ~= nil then filters.speciesId else nil
        ctx.patternId = if filters.patternId ~= nil then filters.patternId else nil
    end
    return ctx
end

function Sel.index(dinos)
    local byId = {}
    for _, d in dinos do if type(d) == "table" and type(d.instanceId) == "string" then byId[d.instanceId] = d end end
    return byId
end

-- Filters --------------------------------------------------------------------------
-- filters fields (all optional): speciesId, patternId, stage, colorId (either gene),
-- shiny (bool), big (bool), mutationId ("none" or id), originKind,
-- cosmetics ("has" | "none" | "equipped").
function Sel.matches(d, filters): boolean
    if not filters then return true end
    local g = genes(d)
    if filters.speciesId ~= nil and d.speciesId ~= filters.speciesId then return false end
    if filters.patternId ~= nil and g.patternId ~= filters.patternId then return false end
    if filters.stage ~= nil and d.stage ~= filters.stage then return false end
    if filters.colorId ~= nil and g.primaryColorId ~= filters.colorId and g.secondaryColorId ~= filters.colorId then return false end
    if filters.shiny ~= nil and (d.shiny == true) ~= filters.shiny then return false end
    if filters.big ~= nil and (d.big == true) ~= filters.big then return false end
    if filters.mutationId ~= nil and mutationOf(d) ~= filters.mutationId then return false end
    if filters.originKind ~= nil and d.originKind ~= filters.originKind then return false end
    if filters.cosmetics == "has" and not Sel.hasCosmetics(d) then return false end
    if filters.cosmetics == "none" and Sel.hasCosmetics(d) then return false end
    if filters.cosmetics == "equipped" and not ((d.equippedAuraId or "") ~= "" or (d.equippedTrailId or "") ~= "") then return false end
    return true
end

function Sel.filter(dinos, filters)
    local result = {}
    for _, d in dinos do if Sel.matches(d, filters) then table.insert(result, d) end end
    return result
end

-- Distinct values present in the list, for the cycling filter chips.
Sel.FilterFields = {"speciesId", "patternId", "stage", "colorId", "shiny", "big", "mutationId", "originKind", "cosmetics"}
function Sel.filterOptions(dinos, catalog)
    local seen = {}
    for _, field in Sel.FilterFields do seen[field] = {} end
    for _, d in dinos do
        local g = genes(d)
        seen.speciesId[d.speciesId or ""] = true
        if g.patternId then seen.patternId[g.patternId] = true end
        seen.stage[d.stage or ""] = true
        if g.primaryColorId then seen.colorId[g.primaryColorId] = true end
        if g.secondaryColorId then seen.colorId[g.secondaryColorId] = true end
        seen.mutationId[mutationOf(d)] = true
        if d.originKind then seen.originKind[d.originKind] = true end
    end
    local order = {speciesId = "speciesOrder", patternId = "patternOrder", colorId = "colorOrder", mutationId = "mutationOrder"}
    local options = {}
    for _, field in Sel.FilterFields do
        local list = {}
        for value in seen[field] do if value ~= "" then table.insert(list, value) end end
        local rank = catalog and order[field] and catalog[order[field]] or {}
        table.sort(list, function(a, b)
            local ra, rb = rank[a] or 999, rank[b] or 999
            if ra ~= rb then return ra < rb end
            return tostring(a) < tostring(b)
        end)
        options[field] = list
    end
    options.shiny, options.big = {true, false}, {true, false}
    options.cosmetics = {"has", "none", "equipped"}
    return options
end

-- Cycles nil -> option1 -> ... -> nil.
function Sel.cycle(options, current)
    if current == nil then return options[1] end
    local i = table.find(options, current)
    if not i or i >= #options then return nil end
    return options[i + 1]
end

-- Sorting --------------------------------------------------------------------------
local function serial(id: string): number
    return tonumber(string.match(id or "", "/d:(%d+)$")) or 0
end
-- Natural-trait rarity score. Cosmetics are deliberately EXCLUDED (BD-062).
function Sel.rarityScore(d): number
    local g = genes(d)
    return (if d.shiny == true then 40 else 0) + (if mutationOf(d) ~= "none" then 30 else 0)
        + (if d.big == true then 20 else 0)
end

Sel.SortKeys = {"eligible", "rarest", "species", "pattern", "color", "recent", "selected"}
Sel.SortNames = {eligible = "Eligible first", rarest = "Rarest", species = "Species", pattern = "Pattern",
    color = "Color", recent = "Newest", selected = "Selected first"}

function Sel.sort(dinos, key: string, ctx, selectedSet, catalog)
    local list = table.clone(dinos)
    selectedSet = selectedSet or {}
    local speciesRank = catalog and catalog.speciesOrder or {}
    local colorRank = catalog and catalog.colorOrder or {}
    local function eligibleRank(d)
        if Sel.ineligibility(d, ctx) then return 2 end
        return if Sel.isPlain(d) then 0 else 1
    end
    local function compare(a, b)
        local ga, gb = genes(a), genes(b)
        local x, y
        if key == "eligible" then x, y = eligibleRank(a), eligibleRank(b)
        elseif key == "rarest" then x, y = -Sel.rarityScore(a), -Sel.rarityScore(b)
        elseif key == "species" then x, y = speciesRank[a.speciesId] or 999, speciesRank[b.speciesId] or 999
        elseif key == "pattern" then x, y = tostring(ga.patternId or "~"), tostring(gb.patternId or "~")
        elseif key == "color" then x, y = colorRank[ga.primaryColorId] or 999, colorRank[gb.primaryColorId] or 999
        elseif key == "recent" then x, y = -serial(a.instanceId), -serial(b.instanceId)
        elseif key == "selected" then x, y = if selectedSet[a.instanceId] then 0 else 1, if selectedSet[b.instanceId] then 0 else 1 end
        if x ~= nil and x ~= y then return x < y end
        local sa, sb = speciesRank[a.speciesId] or 999, speciesRank[b.speciesId] or 999
        if sa ~= sb then return sa < sb end
        local na, nb = serial(a.instanceId), serial(b.instanceId)
        if na ~= nb then return na < nb end
        return tostring(a.instanceId) < tostring(b.instanceId)
    end
    table.sort(list, compare)
    return list
end

-- Selection ------------------------------------------------------------------------
function Sel.selectedSet(selection)
    local set = {}
    for _, id in selection do set[id] = true end
    return set
end

-- Returns (newSelection, ok, reasonCode). Deselecting is always allowed.
function Sel.toggle(selection, d, targetStage: string, byId)
    local result = table.clone(selection)
    local at = table.find(result, d.instanceId)
    if at then table.remove(result, at) return result, true, nil end
    local recipe = stageInfo(targetStage)
    if not recipe or not recipe.approved then return selection, false, "recipe_not_approved" end
    if #result >= recipe.donorCount then return selection, false, "full" end
    local reason = Sel.ineligibility(d, Sel.context(targetStage, result, byId, nil))
    if reason then return selection, false, reason end
    table.insert(result, d.instanceId)
    return result, true, nil
end

-- Auto-fill ONLY ordinary, unprotected, eligible copies. Never Shiny / BIG / mutated /
-- cosmetic-bearing / locked / favorited. Returns (selection, added, shortfall).
function Sel.autoFill(dinos, selection, targetStage: string, filters, catalog)
    local recipe = stageInfo(targetStage)
    if not recipe or not recipe.approved then return selection, 0, 0 end
    local need = recipe.donorCount - #selection
    local byId = Sel.index(dinos)
    local result = table.clone(selection)
    if need <= 0 then return result, 0, 0 end
    local taken = Sel.selectedSet(selection)
    local ctx = Sel.context(targetStage, selection, byId, filters)
    local groups, order = {}, {}
    for _, d in Sel.sort(dinos, "recent", ctx, nil, catalog) do
        -- Oldest first so newest hatches stay; "recent" is newest-first, so reverse below.
        if not taken[d.instanceId] and Sel.isPlain(d) and Sel.ineligibility(d, ctx) == nil then
            local key = tostring(d.speciesId) .. "|" .. (if recipe.anyPattern then "*" else tostring(genes(d).patternId))
            if not groups[key] then groups[key] = {} table.insert(order, key) end
            table.insert(groups[key], 1, d)
        end
    end
    if #order == 0 then return result, 0, need end
    local speciesRank = catalog and catalog.speciesOrder or {}
    table.sort(order, function(a, b)
        if #groups[a] ~= #groups[b] then return #groups[a] > #groups[b] end
        local sa, sb = speciesRank[groups[a][1].speciesId] or 999, speciesRank[groups[b][1].speciesId] or 999
        if sa ~= sb then return sa < sb end
        return a < b
    end)
    local added = 0
    for _, d in groups[order[1]] do
        if added >= need then break end
        table.insert(result, d.instanceId)
        added += 1
    end
    return result, added, need - added
end

-- BD-346: why "Fill for me" added what it did. Never silent: the child is told what to do next.
function Sel.autoFillMessage(dinos, selectionBefore, selectionAfter, targetStage: string, byId, catalog): string
    local recipe = stageInfo(targetStage)
    if not recipe or not recipe.approved then return Sel.LockedStageText end
    local need = recipe.donorCount
    local added = #selectionAfter - #selectionBefore
    local left = need - #selectionAfter
    if added > 0 and left <= 0 then return "Filled! Tap FUSE." end
    if added > 0 then return "Added " .. added .. ". You need " .. left .. " more." end
    if need - #selectionBefore <= 0 then return "All " .. need .. " places are full." end
    local first = selectionBefore[1] and byId[selectionBefore[1]]
    if first then
        local who = lookup(catalog, "species", first.speciesId, "dino")
        local pattern = if recipe.anyPattern then "" else (Sel.cardPattern(first, catalog) .. " ")
        return "No more plain " .. pattern .. who .. " to add. Tap Clear to pick another."
    end
    return "No plain dinos to add. Special dinos are never picked for you."
end
-- Consumed donors leave the list at once, so a click right after a fusion never fills with dinos that are gone.
function Sel.withoutIds(dinos, ids)
    local gone = {}
    for _, id in ids do gone[id] = true end
    local kept = {}
    for _, d in dinos do if not gone[d.instanceId] then table.insert(kept, d) end end
    return kept
end

-- Selected-donor histogram: "2 Shiny / 15" etc. Cosmetics are listed but not rarity.
function Sel.histogram(selection, byId)
    local h = {count = 0, shiny = 0, big = 0, mutations = {}, cosmetics = 0, valuable = 0}
    for _, id in selection do
        local d = byId[id]
        if d then
            h.count += 1
            if d.shiny == true then h.shiny += 1 end
            if d.big == true then h.big += 1 end
            local m = mutationOf(d)
            if m ~= "none" then h.mutations[m] = (h.mutations[m] or 0) + 1 end
            if Sel.hasCosmetics(d) then h.cosmetics += 1 end
            if #Sel.valuableReasons(d) > 0 then h.valuable += 1 end
        end
    end
    return h
end

-- Short accessible card badges (text, never color-only).
function Sel.badges(d, catalog): {string}
    local list = {}
    if d.shiny == true then table.insert(list, "SHINY") end
    if d.big == true then table.insert(list, "BIG") end
    local m = mutationOf(d)
    if m ~= "none" then table.insert(list, lookup(catalog, "mutations", m)) end
    local cosmetic = (tonumber(d.auraCount) or 0) + (tonumber(d.trailCount) or 0)
    if cosmetic > 0 then table.insert(list, cosmetic .. " FX") end
    if d.locked == true then table.insert(list, "LOCKED") end
    if d.favorited == true then table.insert(list, "FAV") end
    return list
end

-- Odds formatting ------------------------------------------------------------------
local function finiteProbability(p): boolean
    return type(p) == "number" and p == p and p >= 0 and p <= 1 + 1e-9
end

local function trimZeros(text: string): string
    if string.find(text, "%.") then text = string.gsub(string.gsub(text, "0+$", ""), "%.$", "") end
    return text
end

-- rows: {{id, label, p}}. Returns rows with `units`, `text` and `decimals` such that the
-- integer units sum to exactly 100% at the displayed precision (largest remainder).
-- Returns nil, reason when the server distribution is malformed (UI must not offer
-- confirmation on unreadable odds).
function Sel.percentRows(rows)
    local total = 0
    for _, row in rows do
        if not finiteProbability(row.p) then return nil, "invalid_probability" end
        total += row.p
    end
    if math.abs(total - 1) > 1e-6 then return nil, "odds_do_not_sum" end
    local decimals = 1
    for _, row in rows do
        if row.p > 0 and row.p < 0.001 then decimals = math.max(decimals, 2) end
        if row.p > 0 and row.p < 0.0001 then decimals = 3 end
    end
    local whole = 100 * 10 ^ decimals
    local result, sum = {}, 0
    for i, row in rows do
        local exact = row.p / total * whole
        local units = math.floor(exact + 1e-9)
        sum += units
        table.insert(result, {id = row.id, label = row.label, p = row.p, units = units, remainder = exact - units, order = i})
    end
    local ranked = table.clone(result)
    table.sort(ranked, function(a, b)
        if math.abs(a.remainder - b.remainder) > 1e-12 then return a.remainder > b.remainder end
        return a.order < b.order
    end)
    local i = 1
    while sum < whole and #ranked > 0 do
        ranked[i].units += 1
        sum += 1
        i = i % #ranked + 1
    end
    for _, row in result do
        row.remainder, row.order = nil, nil
        row.decimals = decimals
        if row.units == 0 and row.p > 0 then
            row.text = "<" .. trimZeros(string.format("%." .. decimals .. "f", 10 ^ -decimals)) .. "%"
        else
            row.text = trimZeros(string.format("%." .. decimals .. "f", row.units / 10 ^ decimals)) .. "%"
        end
    end
    return result, nil
end

local function mapRows(map, catalog, group, extra)
    local rows = {}
    if type(map) ~= "table" then return rows end
    for id, p in map do table.insert(rows, {id = id, label = lookup(catalog, group, id), p = p}) end
    if extra then table.insert(rows, extra) end
    table.sort(rows, function(a, b)
        if type(a.p) == "number" and type(b.p) == "number" and a.p ~= b.p then return a.p > b.p end
        return tostring(a.id) < tostring(b.id)
    end)
    return rows
end

-- Raw (unformatted) wheel rows for one trait; shared by odds display and reveal.
function Sel.traitRows(odds, trait: string, catalog)
    if type(odds) ~= "table" then return {} end
    if trait == "shiny" or trait == "big" then
        local p = odds[trait]
        local name = if trait == "shiny" then "Shiny" else "BIG"
        if type(p) ~= "number" then return {} end
        return {{id = "yes", label = name, p = p}, {id = "no", label = "Not " .. name, p = 1 - p}}
    elseif trait == "mutation" then
        return mapRows(odds.mutation, catalog, "mutations", if type(odds.noMutation) == "number"
            then {id = "none", label = "No mutation", p = odds.noMutation} else nil)
    elseif trait == "primaryColor" or trait == "secondaryColor" then return mapRows(odds[trait], catalog, "colors") end
    return {}
end

Sel.OddsSections = {
    {trait = "shiny", title = "Shiny"}, {trait = "mutation", title = "Event mutation"},
    {trait = "big", title = "BIG"},
    {trait = "primaryColor", title = "Color 1"}, {trait = "secondaryColor", title = "Color 2"},
}
-- Returns {ok, sections={{title, trait, rows}}, error?}. Any malformed section makes
-- the whole quote unusable for confirmation.
function Sel.formatOdds(odds, catalog)
    if type(odds) ~= "table" then return {ok = false, sections = {}, error = "missing_odds"} end
    local sections = {}
    for _, section in Sel.OddsSections do
        local rows, err = Sel.percentRows(Sel.traitRows(odds, section.trait, catalog))
        if not rows or #rows == 0 then return {ok = false, sections = sections, error = err or ("missing_" .. section.trait)} end
        table.insert(sections, {title = section.title, trait = section.trait, rows = rows})
    end
    return {ok = true, sections = sections}
end

-- Loss confirmation ----------------------------------------------------------------
local function plural(n: number, word: string): string
    return n .. " " .. word .. (if n == 1 then "" else "s")
end
function Sel.lossSummary(quote, catalog)
    local summary = {auraCount = 0, trailCount = 0, auraNames = {}, trailNames = {}, valuables = {},
        consentRequired = type(quote) == "table" and quote.consentRequired == true}
    local manifest = type(quote) == "table" and quote.lossManifest or {}
    for _, entry in manifest do
        for _, id in entry.auraIds or {} do
            summary.auraCount += 1
            table.insert(summary.auraNames, lookup(catalog, "auras", id))
        end
        for _, id in entry.trailIds or {} do
            summary.trailCount += 1
            table.insert(summary.trailNames, lookup(catalog, "trails", id))
        end
        local traits = {}
        if entry.shiny then table.insert(traits, "Shiny") end
        if entry.big then table.insert(traits, "BIG") end
        if type(entry.mutationId) == "string" and entry.mutationId ~= "" then table.insert(traits, lookup(catalog, "mutations", entry.mutationId)) end
        if #traits > 0 then table.insert(summary.valuables, {instanceId = entry.instanceId, text = table.concat(traits, " + ")}) end
    end
    local names = {}
    for _, n in summary.auraNames do table.insert(names, n) end
    for _, n in summary.trailNames do table.insert(names, n) end
    if summary.auraCount + summary.trailCount > 0 then
        summary.cosmeticText = plural(summary.auraCount, "aura") .. " and " .. plural(summary.trailCount, "trail")
            .. " will be lost: " .. table.concat(names, ", ")
    else
        summary.cosmeticText = "No bought auras or trails will be lost."
    end
    summary.needsConfirm = summary.consentRequired or #summary.valuables > 0 or #names > 0
    return summary
end

-- Fuse attempts and retry tokens ---------------------------------------------------
-- The same confirmed request reuses its token on retry so a delayed or duplicated
-- commit returns the SAME result ("duplicate"); a changed request gets a new token.
function Sel.requestKey(targetStage: string, donorIds, quoteDigest): string
    local ids = table.clone(donorIds or {})
    table.sort(ids)
    return tostring(targetStage) .. "#" .. table.concat(ids, ",") .. "#" .. tostring(quoteDigest)
end

function Sel.attempt(previous, targetStage: string, donorIds, quoteDigest, newToken: () -> string)
    local key = Sel.requestKey(targetStage, donorIds, quoteDigest)
    if previous and previous.key == key and previous.state == "pending" then
        previous.tries += 1
        return previous, true
    end
    return {key = key, token = newToken(), state = "pending", tries = 1, targetStage = targetStage,
        donorIds = table.clone(donorIds), quoteDigest = quoteDigest}, false
end

Sel.FailureText = {
    fusion_disabled = "Fusion is unavailable right now.",
    rate_limited = "Too fast! Trying again in a moment.",
    stale_quote = "Your dinos changed. Check the new chances, then confirm.",
    consent_required = "Please check what you will lose, then confirm again.",
    donor_missing = "A selected dino is gone. Selection refreshed.",
    donor_locked = "A selected dino is locked or favorited. Selection refreshed.",
    wrong_donor_count = "Pick exactly 6 Base, 3 Gold or 2 Emerald dinos.",
    species_mismatch = "All dinos must be the same species.",
    pattern_mismatch = "Emerald and Diamond need dinos with the same pattern.",
    recipe_not_approved = "This recipe is not approved yet.",
    odds_not_approved = "Fusion odds are not approved yet. Nothing was consumed.",
    save_failed = "Could not save, but nothing was lost. Trying again.",
    lease_lost = "Rejoin the game, then open Fusion to see the result.",
    storage_limit = "Your collection is full. Make room before fusing.",
    token_conflict = "Something did not match. Please confirm again.",
    duplicate_donor = "A dino was selected twice. Selection refreshed.",
    wrong_stage = "A selected dino is the wrong stage. Selection refreshed.",
    missing_pattern = "A selected dino has no recorded egg pattern.",
    invalid_donor_id = "That pick did not work. Selection refreshed.",
    profile_not_loaded = "Your dinos are still loading. Try again in a moment.",
    request_failed = "Connection problem. Trying again.",
    unavailable = "Fusion unavailable.",
    identity_unavailable = "Fusion is unavailable for this save right now.",
    random_items_unavailable = "Fusion is not available for this account.",
    bad_request = "That did not work. Please open Fusion again.",
    invalid_token = "That did not work. Please confirm again.",
    invalid_instance = "A selected dino cannot be used. Selection refreshed.",
    wrong_owner = "A selected dino is not yours. Selection refreshed.",
    unknown_stage = "Unknown fusion stage.",
    projection_unsupported = "This stage is not fusable yet.",
    identity_capacity = "Your collection is at its limit. Nothing was used up.",
}
-- profile_not_loaded: after save_failed/lease_lost the server refuses until reload; the same token stays safe.
local RetrySame = {rate_limited = true, save_failed = true, request_failed = true, lease_lost = true, profile_not_loaded = true}
local Requote = {stale_quote = true, consent_required = true, donor_missing = true, donor_locked = true,
    wrong_donor_count = true, species_mismatch = true, pattern_mismatch = true, token_conflict = true,
    duplicate_donor = true, wrong_stage = true, missing_pattern = true, invalid_donor_id = true,
    invalid_instance = true, wrong_owner = true, invalid_token = true}

function Sel.failureMessage(reason: any): string
    return Sel.FailureText[reason] or ("Fusion failed: " .. string.gsub(tostring(reason), "_", " "))
end

-- Classifies a fuse response. kind: success | retry (same token) | requote | fatal.
function Sel.settle(attempt, response)
    if type(response) ~= "table" then
        return {kind = "retry", reason = "request_failed", message = Sel.failureMessage("request_failed"), attempt = attempt}
    end
    if response.ok == true and (response.status == "fused" or response.status == "duplicate") and type(response.result) == "table" then
        if attempt then attempt.state = "settled" end
        return {kind = "success", status = response.status, result = response.result, attempt = attempt}
    end
    local reason = if response.ok == true then "request_failed" else (response.reason or "request_failed")
    if RetrySame[reason] then return {kind = "retry", reason = reason, message = Sel.failureMessage(reason), attempt = attempt} end
    if attempt then attempt.state = "abandoned" end
    return {kind = if Requote[reason] then "requote" else "fatal", reason = reason, message = Sel.failureMessage(reason), attempt = nil}
end

-- Reveal sequence ------------------------------------------------------------------
-- Every wheel lands on the COMMITTED server value. Segment sizes equal the quoted
-- odds; the landing angle is the middle of the committed segment (no fake near-miss).
local function wheel(kind: string, title: string, rows, committed: string, detail: string?)
    local segments, cursor, landing = {}, 0, nil
    for i, row in rows do
        local p = if type(row.p) == "number" and row.p > 0 then row.p else 0
        table.insert(segments, {id = row.id, label = row.label, p = p, from = cursor, to = cursor + p})
        if row.id == committed then landing = i end
        cursor += p
    end
    local stage = {kind = "wheel", trait = kind, title = title, segments = segments, committed = committed, detail = detail}
    if landing and segments[landing].p > 0 then
        local seg = segments[landing]
        stage.landingIndex = landing
        stage.landingFraction = (seg.from + seg.to) / 2 / math.max(cursor, 1e-9)
    else
        -- Server result outside the quoted table: show it plainly, never animate a guess.
        stage.kind, stage.mismatch = "card", true
    end
    return stage
end

-- Rotation (degrees) that puts the landing fraction under a top pointer after `turns`.
function Sel.wheelRotation(stage, turns: number): number
    return turns * 360 + (1 - (stage.landingFraction or 0)) * 360
end

-- Horizontal reel variant used by the client: distance (in whole-strip units) the strip
-- travels so the centre pointer stops at the middle of the committed segment.
function Sel.reelOffset(stage, turns: number): number
    return turns + (stage.landingFraction or 0)
end

-- BD-346: every reveal step stays up long enough to read (docs/87): never under 1.2 s, even on the Reduce Motion path.
Sel.MinStepSeconds = 1.2
function Sel.stepSeconds(kind: string, motionOn: boolean, reelSeconds: number): number
    local wanted = if kind == "pattern" then 2.2 elseif motionOn then reelSeconds + 1.4 else 1.6
    return math.max(Sel.MinStepSeconds, wanted)
end
-- BD-346: Shiny / BIG as a readable bar: YES share and NO share, the marker inside the committed share (never on the label).
function Sel.chanceBar(stage)
    local yes, no = 0, 0
    for _, seg in stage.segments or {} do
        if seg.id == "yes" then yes = seg.p elseif seg.id == "no" then no = seg.p end
    end
    local total = math.max(yes + no, 1e-9)
    local yesShare = yes / total
    local landedYes = stage.committed == "yes"
    local marker = if landedYes then yesShare / 2 else yesShare + (1 - yesShare) / 2
    return {yesShare = yesShare, landedYes = landedYes, marker = marker,
        outcome = if landedYes then "YES!" else "Not this time"}
end

function Sel.revealSequence(quote, result, catalog)
    local traits = type(result) == "table" and result.traits or {}
    local g = traits.genes or {}
    local stages = {}
    local patternId = (type(result) == "table" and result.patternId) or g.patternId
    table.insert(stages, {kind = "pattern", title = "Pattern locked", value = lookup(catalog, "patterns", patternId)})
    local odds = type(quote) == "table" and quote.odds or nil
    if odds then
        local function add(trait, title, committed, detail)
            local rows = Sel.traitRows(odds, trait, catalog)
            if #rows > 0 then table.insert(stages, wheel(trait, title, rows, committed, detail)) end
        end
        add("primaryColor", "COLOR 1", g.primaryColorId)
        add("secondaryColor", "COLOR 2", g.secondaryColorId, if type(g.blend) == "number" then ("Blend " .. g.blend .. "% / " .. (100 - g.blend) .. "%") else nil)
        add("shiny", "SHINY", if traits.shiny then "yes" else "no")
        add("mutation", "MUTATION", if type(traits.mutationId) == "string" and traits.mutationId ~= "" then traits.mutationId else "none")
        add("big", "BIG", if traits.big then "yes" else "no")
    end
    for _, stage in stages do
        if stage.kind ~= "pattern" and stage.committed then
            local rowLabel = nil
            for _, s in stage.segments or {} do if s.id == stage.committed then rowLabel = s.label end end
            stage.value = rowLabel or stage.committed
        end
    end
    table.insert(stages, {kind = "final", title = "NEW " .. string.upper(lookup(catalog, "patterns", patternId)) .. " "
        .. string.upper(lookup(catalog, "species", type(result) == "table" and result.speciesId or nil, "DINO")),
        stage = type(result) == "table" and result.targetStage or "gold", replay = odds == nil})
    return stages
end

-- Dino Details view model (BD-062) -------------------------------------------------
Sel.DetailsParentLimit = 12
Sel.EggSourceNames = {alpha_chest = "Run reward egg", run = "Run egg", crystal_shop = "Crystal Shop egg",
    chest_claim = "Reward egg", progression = "Progression egg"}

local function geneLine(g, catalog): string
    if type(g) ~= "table" or not g.primaryColorId then return "Unknown genes" end
    local blend = tonumber(g.blend) or 100
    -- One colour (same twice, or a 100% blend): say it once, not "Cream 100% / Cream 0%".
    if blend >= 100 or g.primaryColorId == g.secondaryColorId then return lookup(catalog, "colors", g.primaryColorId) end
    return lookup(catalog, "colors", g.primaryColorId) .. " " .. blend .. "% / "
        .. lookup(catalog, "colors", g.secondaryColorId) .. " " .. (100 - blend) .. "%"
end
Sel.geneLine = geneLine

-- "a Gold" / "an Emerald" (child-facing copy must not say "a Emerald").
function Sel.article(word: string): string
    return if string.find(string.lower(word), "^[aeiou]") then "an" else "a"
end

local function eggLine(egg, catalog): string
    if type(egg) ~= "table" then return "Original egg not recorded" end
    local g = egg.genes or {}
    local parts = {lookup(catalog, "patterns", g.patternId), geneLine(g, catalog)}
    if type(egg.eventId) == "string" and egg.eventId ~= "" and egg.eventId ~= "clear" then table.insert(parts, "Event: " .. titleCase((string.gsub(egg.eventId, "_", " ")))) end
    table.insert(parts, Sel.EggSourceNames[egg.kind] or (if type(egg.kind) == "string" then titleCase((string.gsub(egg.kind, "_", " "))) else "Unknown source"))
    return table.concat(parts, " • ")
end
Sel.eggLine = eggLine

-- " • Common • 26% of eggs" (rarity optional); empty when the percent is unknown.
local function oddsText(rarity: string?, p: number?): string
    if p == nil then return "" end
    return " • " .. (if rarity then rarity .. " • " else "") .. Sel.pct(p) .. " of eggs"
end
local function colorOdds(g, catalog): string
    if type(g) ~= "table" or not g.primaryColorId then return "Unknown" end
    local function one(id)
        local p = catalog.colorPct and catalog.colorPct[id]
        return lookup(catalog, "colors", id) .. (if p then " " .. Sel.pct(p) else "")
    end
    if g.secondaryColorId == g.primaryColorId then return one(g.primaryColorId) .. " (per egg slot)" end
    return one(g.primaryColorId) .. " • " .. one(g.secondaryColorId) .. " (per egg slot)"
end

function Sel.details(d, catalog)
    local g = genes(d)
    local stage = d.stage or "base"
    local stageName = if stage == "base" then "Base" else titleCase(stage)
    local view = {
        title = (if stage == "base" then "" else stageName .. " ") .. lookup(catalog, "patterns", g.patternId, "Unknown pattern") .. " "
            .. lookup(catalog, "species", d.speciesId, "Dino"),
        traits = {
            {label = "Stage", value = stageName},
            {label = "Species", value = lookup(catalog, "species", d.speciesId, "Dino") .. oddsText(catalog.speciesRarity and catalog.speciesRarity[d.speciesId], catalog.speciesPct and catalog.speciesPct[d.speciesId])},
            {label = "Pattern", value = lookup(catalog, "patterns", g.patternId, "Unknown") .. oddsText(nil, catalog.patternPct and catalog.patternPct[g.patternId])},
            {label = "Colors", value = geneLine(g, catalog)},
            {label = "Color odds", value = colorOdds(g, catalog)},
            {label = "Shiny", value = if d.shiny then "Yes" else "No"},
            {label = "BIG", value = if d.big then "Yes" else "No"},
            {label = "Mutation", value = lookup(catalog, "mutations", d.mutationId, "None")},
        },
        origin = {lines = {}, parents = {}},
    }
    -- BD-172: optional hook set by the client (catalog.colourBonus(genes) -> "Colour bonus +3% growth" | nil); server stays authoritative.
    local bonusText = if type(catalog.colourBonus) == "function" then catalog.colourBonus(g) else nil
    if bonusText then table.insert(view.traits, 5, {label = "Colour bonus", value = (string.gsub(bonusText, "^Colour bonus ", ""))}) end
    local origin = type(d.origin) == "table" and d.origin or {}
    local lineage = d.lineage
    if origin.kind == "fusion" or type(lineage) == "table" then
        lineage = type(lineage) == "table" and lineage or {}
        local parentIds = lineage.parentIds or {}
        local snapshots = origin.parents or {}
        view.origin.kind = "fused"
        view.prestige = "Crafted " .. stageName .. " (earned)"
        table.insert(view.origin.lines, "Fused from " .. math.max(#parentIds, #snapshots) .. " dinos")
        table.insert(view.origin.lines, "Recipe " .. tostring(lineage.recipeVersion or origin.recipeVersion or "unknown")
            .. " • Odds " .. tostring(lineage.oddsVersion or origin.oddsVersion or "unknown"))
        table.insert(view.origin.lines, "Traits were rolled fresh. The stage is always guaranteed.")
        local eggs = lineage.parentEggs or {}
        local byParent = {}
        for _, snap in snapshots do byParent[snap.instanceId] = snap end
        local ids = if #parentIds > 0 then parentIds else (function()
            local list = {} for _, snap in snapshots do table.insert(list, snap.instanceId) end return list end)()
        -- Bounded view: a Gold has 6 parents; list the first DetailsParentLimit.
        local shown = math.min(#ids, Sel.DetailsParentLimit)
        if #ids > shown then
            table.insert(view.origin.lines, "Showing " .. shown .. " of " .. #ids .. " parents")
        end
        for i = 1, shown do
            local id = ids[i]
            local snap = byParent[id]
            local eggId = snap and snap.origin and snap.origin.eggId
            local egg = eggId and eggs[eggId]
            if not egg and #eggs > 0 then for _, e in eggs do if e.eggId == eggId then egg = e end end end
            table.insert(view.origin.parents, {instanceId = id,
                text = if snap then (lookup(catalog, "patterns", (snap.genes and snap.genes.patternId) or g.patternId) .. " " .. lookup(catalog, "species", snap.speciesId or d.speciesId, "Dino")
                    .. (if snap.shiny then " • Shiny" else "") .. (if snap.big then " • BIG" else "")
                    .. (if type(snap.mutationId) == "string" and snap.mutationId ~= "" then " • " .. lookup(catalog, "mutations", snap.mutationId) else ""))
                    else id,
                egg = if egg then eggLine(egg, catalog) elseif snap and snap.origin and snap.origin.kind == "fusion" then "Fused parent (own lineage)" else "Original egg not recorded"})
        end
    elseif origin.kind == "hatch" or type(d.originalEgg) == "table" then
        view.origin.kind = "hatched"
        view.prestige = if stage == "base" then "Natural hatch" else "Natural hatch • " .. stageName .. " stage"
        table.insert(view.origin.lines, "Hatched from: " .. eggLine(d.originalEgg, catalog))
        table.insert(view.origin.lines, "Natural hatch odds: not calculated yet (needs versioned source tables)")
    else
        view.origin.kind = "unknown"
        view.prestige = if stage == "base" then "Older copy" else stageName .. " (earned, older fusion)"
        table.insert(view.origin.lines, "Original egg was not recorded for this older copy. Traits are not guessed.")
    end
    local c = type(d.cosmetics) == "table" and d.cosmetics or {}
    local auras, trails = {}, {}
    for _, id in c.ownedAuraIds or {} do table.insert(auras, lookup(catalog, "auras", id)) end
    for _, id in c.ownedTrailIds or {} do table.insert(trails, lookup(catalog, "trails", id)) end
    view.cosmetics = {
        "Auras: " .. (if #auras > 0 then table.concat(auras, ", ") else "None (buy for this dino)"),
        "Trails: " .. (if #trails > 0 then table.concat(trails, ", ") else "Free/default only"),
        "Equipped: " .. lookup(catalog, "auras", c.equippedAuraId, "No aura") .. " • " .. lookup(catalog, "trails", c.equippedTrailId, "No trail"),
        "Bought cosmetics never count toward rarity or prestige.",
    }
    return view
end


-- Fusion Menu v2 (docs/96) ---------------------------------------------------------
-- Big tier tab: {title = "GOLD", sub = "6 Base"}.
function Sel.tabText(stageId: string)
    local s = stageInfo(stageId)
    if not s then return {title = string.upper(tostring(stageId)), sub = ""} end
    return {title = string.upper(s.name), sub = if s.approved then s.donorCount .. " " .. Sel.stageTitle(s.source) else "Soon"}
end

-- The list is filtered automatically to dinos of the recipe's source stage (plus any
-- optional filters). Wrong-stage copies are hidden instead of explained.
function Sel.visibleFor(dinos, targetStage: string, filters)
    local recipe = stageInfo(targetStage)
    local result = {}
    for _, d in dinos do
        if recipe and d.stage == recipe.source and Sel.matches(d, filters) then table.insert(result, d) end
    end
    return result
end

-- Largest group of eligible copies for this recipe: {speciesId, patternId?, count}.
-- Species only for Gold (any pattern); species + pattern for Emerald / Diamond.
function Sel.bestGroup(dinos, targetStage: string)
    local recipe = stageInfo(targetStage)
    if not recipe or not recipe.approved then return nil end
    local groups, best = {}, nil
    for _, d in dinos do
        if Sel.ineligibility(d, {targetStage = targetStage}) == nil then
            local pattern = if recipe.anyPattern then nil else genes(d).patternId
            local key = tostring(d.speciesId) .. "|" .. tostring(pattern or "*")
            local g = groups[key]
            if not g then g = {speciesId = d.speciesId, patternId = pattern, count = 0} groups[key] = g end
            g.count += 1
            if not best or g.count > best.count then best = g end
        end
    end
    return best
end

-- One sentence under the tabs: what to do next, or why nothing can be made yet.
function Sel.goalText(dinos, targetStage: string, selection, byId, catalog): string
    local recipe = stageInfo(targetStage)
    if not recipe or not recipe.approved then return Sel.LockedStageText end
    local need = recipe.donorCount
    local first = selection[1] and byId[selection[1]]
    if first then
        local left = need - #selection
        local who = lookup(catalog, "species", first.speciesId, "dino")
        if left <= 0 then return "Ready! Tap FUSE." end
        return "Tap " .. left .. " more " .. who .. "."
    end
    local best = Sel.bestGroup(dinos, targetStage)
    if not best then
        return "You need " .. need .. " " .. Sel.stageTitle(recipe.source) .. " dinos of one kind. You have 0."
    end
    local who = lookup(catalog, "species", best.speciesId, "dino")
    if best.count >= need then return "Tap " .. need .. " " .. who .. ", or Fill for me." end
    return "You need " .. need .. " " .. who .. " to make " .. Sel.article(recipe.name) .. " " .. recipe.name .. " " .. who .. ". You have " .. best.count .. "."
end

-- Exact server odds as short chips: {{title = "Shiny", chips = {{label = "Shiny 8%", p = .08}}}}.
-- Same numbers as formatOdds (largest remainder, sums to 100%), only phrased simply.
-- BD-344: every section has a HEADING the screen draws (Colour 1 / Colour 2 / Pattern / Shiny / Event / BIG), in the
-- order a child reads a dino (colours, pattern, then the lucky bits). The locked pattern is a one-chip section.
Sel.ChipOrder = {primaryColor = 1, secondaryColor = 2, pattern = 3, shiny = 4, mutation = 5, big = 6}
Sel.ChipHeadings = {primaryColor = "Colour 1", secondaryColor = "Colour 2", pattern = "Pattern", shiny = "Shiny", mutation = "Event", big = "BIG"}
function Sel.oddsChips(odds, catalog, patternId: string?)
    local formatted = Sel.formatOdds(odds, catalog)
    if not formatted.ok then return {ok = false, sections = {}, error = formatted.error} end
    local sections = {}
    for _, section in formatted.sections do
        local chips = {}
        for _, row in section.rows do
            local label = row.label
            if section.trait == "shiny" or section.trait == "big" then
                label = if row.id == "yes" then "Yes" else "No"
            elseif section.trait == "mutation" and row.id == "none" then label = "None" end
            table.insert(chips, {id = row.id, label = label .. " " .. row.text, p = row.p})
        end
        table.insert(sections, {title = Sel.ChipHeadings[section.trait] or section.title, trait = section.trait, chips = chips})
    end
    if type(patternId) == "string" and patternId ~= "" then
        table.insert(sections, {title = "Pattern", trait = "pattern", chips = {{id = patternId, label = lookup(catalog, "patterns", patternId) .. " (locked)", p = 1}}})
    end
    table.sort(sections, function(a, b) return (Sel.ChipOrder[a.trait] or 9) < (Sel.ChipOrder[b.trait] or 9) end)
    return {ok = true, sections = sections}
end

-- BD-344: height of one odds section (heading + wrapped chip rows) so a section never overflows or hides under FUSE.
Sel.ChipHeadingHeight, Sel.ChipHeight, Sel.ChipGap = 24, 34, 4
function Sel.sectionHeight(chipCount: number, columns: number): number
    local rows = math.ceil(math.max(chipCount, 1) / math.max(columns, 1))
    return Sel.ChipHeadingHeight + rows * (Sel.ChipHeight + Sel.ChipGap)
end
-- Columns that keep every chip at least `minWidth` px wide (a long "Cream 66.7%" never squeezes into a third of 130 px).
function Sel.chipColumns(totalWidth: number, minWidth: number): number
    return math.clamp(math.floor((totalWidth + Sel.ChipGap) / (minWidth + Sel.ChipGap)), 1, 4)
end

-- BD-345: traits handed to DinosaurPreview. A fused Gold/Emerald/Diamond keeps ITS OWN rolled gene colours and pattern
-- (the preview puts the tier over them); mutation tints never apply to fused tiers (BD-155). Never reads a donor.
function Sel.previewTraits(d)
    if type(d) ~= "table" then return nil end
    local g = if type(d.genes) == "table" and next(d.genes) ~= nil then d.genes else nil
    local base = d.stage == nil or d.stage == "base"
    local mutation = if base and type(d.mutationId) == "string" and d.mutationId ~= "" then d.mutationId else nil
    return {genes = g, shiny = d.shiny == true, big = d.big == true, mutationId = mutation}
end

-- Card words: pattern line never says "Unknown pattern"; an older copy says so plainly.
function Sel.cardPattern(d, catalog): string
    local g = genes(d)
    if type(g.patternId) ~= "string" or g.patternId == "" then return "Older dino" end
    return lookup(catalog, "patterns", g.patternId)
end
-- Short trait words for a card: Shiny, BIG, mutation name, "Effects", Locked, Favourite.
function Sel.cardTraits(d, catalog): {string}
    local list = {}
    if d.shiny == true then table.insert(list, "Shiny") end
    if d.big == true then table.insert(list, "BIG") end
    local m = mutationOf(d)
    if m ~= "none" then table.insert(list, lookup(catalog, "mutations", m)) end
    if Sel.hasCosmetics(d) then table.insert(list, "Effects") end
    if d.locked == true then table.insert(list, "Locked") end
    if d.favorited == true then table.insert(list, "Favourite") end
    return list
end

-- Nav FUSION target. "menu" = new Pattern Fusion Menu; "legacy" = old Build 020 page
-- (development profile only); "unavailable" = notify, open nothing.
-- ctx: {menuLoaded, remote (FusionAction exists), probe ("ok"|"disabled"|nil), profile}
function Sel.navTarget(ctx): string
    if ctx.menuLoaded and ctx.remote and ctx.probe ~= "disabled" then return "menu" end
    if ctx.profile == nil or ctx.profile == "development" then return "legacy" end
    return "unavailable"
end

-- Caught Eggs slot look: empty -> neutral placeholder; valid genes -> real gene look;
-- otherwise a plain (untinted) egg. genesValid comes from EggGenetics.valid.
function Sel.eggSlotLook(entry, genesValid: boolean): string
    if not entry then return "empty" end
    if entry.genes and genesValid then return "genes" end
    return "plain"
end

-- Dino Index card display for a species. discovered = any copy, event mutation or traits.
function Sel.indexCard(discovered: boolean)
    if discovered then return {silhouette = false, locked = false, nameText = nil, rarityText = nil, showButton = true} end
    return {silhouette = true, locked = true, nameText = "???", rarityText = "???", status = "Not discovered", showButton = false}
end

return Sel
