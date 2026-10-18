--!strict
-- BD-1039 / docs/186 s7: the Pattern Index and the Colour Index (the Patterns and Colours tabs of the Index screen). Pure rules, no Roblox
-- services: pass the decoded owner-only values and the config tables; the client module PatternColourCards draws what this returns.
--
--   FOUND  A pattern or colour is found when the player owns (or ever hatched) a dino that carries it. A dino's MAIN and ACCENT colour both
--          count. Two sources, merged: (1) the permanent discovery log the server keeps (progression.discovered, BD-436; with
--          Config.PatternColourIndexEnabled it also holds accent colours and reaches the client as DiscoveryJson.ids), so a dino fused away never
--          un-finds a pattern; (2) the dinos the player owns right now (CollectionJson variants), computed on the fly, which backfills old
--          saves with NO profile rewrite. Nothing here saves anything.
--   CARDS  One card per row of ProgressionConfig.EggPatterns / EggColors (never hard-coded), in tier order (Common first), the table order
--          inside a tier. A found card shows name, tier word, boost pips and "Found on: Compy, Raptor +1"; a card not found yet shows a grey
--          silhouette, the DIMMED tier colour (so how rare it is stays visible) and "Not found yet".
--   BOOST  Pips (0 to 5) come from GeneBoost.itemPips (the tier points), never a percent.
local Curve = require(script.Parent.RarityCurve)
local Boost = require(script.Parent.GeneBoost)

local Index = {}

Index.Version = "bd1039-index-v1"
Index.Tabs = table.freeze({"dinos", "patterns", "colours"})
Index.TabNames = table.freeze({dinos = "Dinos", patterns = "Patterns", colours = "Colours"})
Index.MaxFoundOn = 2 -- species named on a card before "+N"
Index.NotFoundLine = "Not found yet"
Index.FoundBeforeLine = "Found before" -- found, but no dino of it is owned any more (fused away)
Index.NoBoostLine = "No boost"
Index.DimBlend = 0.55 -- how far a not-found card's tier colour is pulled toward the dark card (0 = same colour, 1 = card colour)

-- A tab id the screen knows, else the Dinos tab (a bad remembered value must never open a blank screen).
function Index.validTab(id: any): string
    for _, tab in Index.Tabs do if tab == id then return tab end end
    return "dinos"
end

local function whole(n: any): number
    return if type(n) == "number" and n == n and n > 0 then n else 0
end

-- Adds `speciesId` once to the ordered list under `key`.
local function addSpecies(map: {[string]: {string}}, key: any, speciesId: string)
    if type(key) ~= "string" or key == "" then return end
    local list = map[key]
    if list == nil then list = {} map[key] = list end
    if not table.find(list, speciesId) then table.insert(list, speciesId) end
end

-- collection = decoded CollectionJson ({speciesId = {variants = {key = {count, genes}}}}), discovered = decoded DiscoveryJson (nil or junk is fine;
-- ids = {patterns = {...}, colours = {...}} only arrives with the flag), order = species ids in Index order (the order "Found on" names them).
-- Returns {patterns = {[id] = true}, colours = {[id] = true}, patternSpecies = {[id] = {species...}}, colourSpecies = {[id] = {species...}}}.
function Index.foundSets(collection: any, discovered: any, order: any)
    local out = {patterns = {} :: {[string]: boolean}, colours = {} :: {[string]: boolean},
        patternSpecies = {} :: {[string]: {string}}, colourSpecies = {} :: {[string]: {string}}}
    if type(collection) == "table" and type(order) == "table" then
        for _, speciesId in order do
            local entry = if type(speciesId) == "string" then collection[speciesId] else nil
            if type(entry) == "table" and type(entry.variants) == "table" then
                -- variants in key order so the result never depends on hash order
                local keys = {}
                for key in entry.variants do table.insert(keys, key) end
                table.sort(keys)
                for _, key in keys do
                    local variant = entry.variants[key]
                    if type(variant) == "table" and whole(variant.count) > 0 and type(variant.genes) == "table" then
                        local g = variant.genes
                        if type(g.patternId) == "string" and g.patternId ~= "" then
                            out.patterns[g.patternId] = true
                            addSpecies(out.patternSpecies, g.patternId, speciesId)
                        end
                        for _, colourId in {g.primaryColorId, g.secondaryColorId} do -- main AND accent
                            if type(colourId) == "string" and colourId ~= "" then
                                out.colours[colourId] = true
                                addSpecies(out.colourSpecies, colourId, speciesId)
                            end
                        end
                    end
                end
            end
        end
    end
    local ids = if type(discovered) == "table" and type(discovered.ids) == "table" then discovered.ids else nil
    if ids ~= nil then
        if type(ids.patterns) == "table" then
            for _, id in ids.patterns do if type(id) == "string" and id ~= "" then out.patterns[id] = true end end
        end
        if type(ids.colours) == "table" then
            for _, id in ids.colours do if type(id) == "string" and id ~= "" then out.colours[id] = true end end
        end
    end
    return out
end

-- The kid name of a row (docs/72: ids are never shown). A row without a name gets a calm generic one.
function Index.displayName(kind: string, row: any): string
    if type(row) == "table" and type(row.name) == "string" and row.name ~= "" then return row.name end
    return if kind == "colours" then "Colour" else "Pattern"
end

-- "Compy, Raptor" for up to MaxFoundOn species and "Compy, Raptor +3" beyond; nil when the list is empty.
function Index.foundOnText(speciesIds: any, nameOf: any): string?
    if type(speciesIds) ~= "table" or #speciesIds == 0 then return nil end
    local names = {}
    for i = 1, math.min(#speciesIds, Index.MaxFoundOn) do
        local id = speciesIds[i]
        local name = if type(nameOf) == "function" then nameOf(id) else nil
        table.insert(names, if type(name) == "string" and name ~= "" then name else tostring(id))
    end
    local text = table.concat(names, ", ")
    if #speciesIds > Index.MaxFoundOn then text ..= " +" .. (#speciesIds - Index.MaxFoundOn) end
    return text
end

-- The boost line under the pips: "Boost 3 of 5", or "No boost" for a Common one.
function Index.boostText(pips: number): string
    if pips <= 0 then return Index.NoBoostLine end
    return string.format("Boost %d of %d", pips, Boost.MaxPips)
end

-- One card per row. kind = "patterns" | "colours", rows = ProgressionConfig.EggPatterns / EggColors, found = Index.foundSets(...),
-- nameOf(speciesId) -> kid name. Sorted by tier (Common first), then the table order, so the grid never reshuffles when something is found.
-- A card: {id, name, rarity, tier (0..5), found, pips (0..5), boostText, line (the third line), rgb (colours only, else nil)}.
function Index.cards(kind: string, rows: any, found: any, nameOf: any)
    local cards = {}
    if type(rows) ~= "table" then return cards end
    local set = if type(found) == "table" then (if kind == "colours" then found.colours else found.patterns) else nil
    local speciesMap = if type(found) == "table" then (if kind == "colours" then found.colourSpecies else found.patternSpecies) else nil
    for position, row in rows do
        if type(row) == "table" and type(row.id) == "string" then
            local tier = Curve.index(row.rarity) or 0
            local points = if kind == "colours" then Boost.colourPoints(rows, row.id) else Boost.patternPoints(rows, row.id)
            local pips = Boost.itemPips(points)
            local isFound = type(set) == "table" and set[row.id] == true
            local line = Index.NotFoundLine
            if isFound then
                local on = Index.foundOnText(if type(speciesMap) == "table" then speciesMap[row.id] else nil, nameOf)
                line = if on then "Found on: " .. on else Index.FoundBeforeLine
            end
            table.insert(cards, {id = row.id, name = Index.displayName(kind, row), rarity = Curve.Names[tier + 1], tier = tier, found = isFound,
                pips = pips, boostText = Index.boostText(pips), line = line, rgb = if kind == "colours" then row.rgb else nil, position = position})
        end
    end
    table.sort(cards, function(a, b)
        if a.tier ~= b.tier then return a.tier < b.tier end
        return a.position < b.position
    end)
    return cards
end

-- {found, total, text} for the top line of a tab: "Patterns 5 / 8", "Colours 4 / 9".
function Index.header(kind: string, cards: any)
    local found, total = 0, 0
    if type(cards) == "table" then
        for _, card in cards do
            total += 1
            if card.found then found += 1 end
        end
    end
    local word = if kind == "colours" then "Colours" else "Patterns"
    return {found = found, total = total, text = string.format("%s %d / %d", word, found, total)}
end

-- How many patterns and colours are found altogether (the dot on the Dinos button compares this with the count when the tabs were last opened).
function Index.foundTotal(found: any, patternRows: any, colourRows: any): number
    local n = 0
    if type(found) ~= "table" then return 0 end
    for _, row in (if type(patternRows) == "table" then patternRows else {}) do
        if type(row) == "table" and found.patterns[row.id] == true then n += 1 end
    end
    for _, row in (if type(colourRows) == "table" then colourRows else {}) do
        if type(row) == "table" and found.colours[row.id] == true then n += 1 end
    end
    return n
end

-- The dot: shown while more has been found than the player has looked at. `seen` nil = no baseline yet (the first reading becomes it).
function Index.dotVisible(total: number, seen: number?): boolean
    return seen ~= nil and total > seen
end

-- Ribbons on the hatch reveal. fresh = the decoded LastChestNewJson ({colour = true, pattern = true, mutation = true}, first-time finds only).
-- enabled false = the old single "NEW!" ribbon. enabled true = "New pattern!" and "New colour!" (one each); a mutation-only find keeps "NEW!".
function Index.ribbons(fresh: any, enabled: any): {string}
    if type(fresh) ~= "table" then return {} end
    local out = {}
    if enabled == true then
        if fresh.pattern == true then table.insert(out, "New pattern!") end
        if fresh.colour == true then table.insert(out, "New colour!") end
        if #out == 0 and fresh.mutation == true then table.insert(out, "NEW!") end
    elseif next(fresh) ~= nil then
        table.insert(out, "NEW!")
    end
    return out
end

-- The border colour of a card: the tier colour when found, the same colour pulled toward `dark` when not (rarity stays visible).
-- Pure maths on 0..1 triples so the test can check it: dim(c, dark) = c + (dark - c) * DimBlend.
function Index.dim(rgb: {number}, dark: {number}): {number}
    return {rgb[1] + (dark[1] - rgb[1]) * Index.DimBlend, rgb[2] + (dark[2] - rgb[2]) * Index.DimBlend, rgb[3] + (dark[3] - rgb[3]) * Index.DimBlend}
end

return table.freeze(Index)
