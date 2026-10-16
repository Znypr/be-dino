--!strict
-- BD-427 (docs/114 s1.1): the three long-term goals as three short lines for the hub Goals panel. OWNER vision 2026-10-16:
-- an equal mix of (1) filling the collection, (2) perfecting one favourite dino up to Diamond, (3) playing new dinos.
-- Pure: no Instances, services or remotes; it only reads data the client already has (collection, fusion list). No new
-- progression system and no reward is promised here. Copy follows docs/72 (short, plain, no "1.25x" or "5m 0s").
-- Exercised by tools/verify_goals.py.
local NextGoal = require(script.Parent.NextGoal)

local Goals = {}
Goals.Title = "GOALS"
Goals.Order = {"collect", "perfect", "play"}
Goals.MaxLine = 40 -- characters per line on the 260 px panel at the smallest text size

local function whole(n: any): number
    return math.max(0, math.floor(tonumber(n) or 0))
end

-- Whole collection (owner vision): species + colours + patterns + mutations. opts.found / opts.total = species found in the
-- Dino Index; opts.parts (optional, from indexCounts) = {colours, patterns, mutations}, each {found, total}.
local HINTS = {colours = "Find new colours", patterns = "Find new patterns", mutations = "Find a weather mutation"}
function Goals.collect(opts: any)
    local total, found = whole(opts.total), whole(opts.found)
    found = math.min(found, total)
    local worst, worstFraction = if total > 0 and found < total then "species" else nil, if total > 0 then found / total else 1
    local parts = if type(opts.parts) == "table" then opts.parts else {}
    for _, key in {"colours", "patterns", "mutations"} do
        local p = parts[key]
        local pt = if type(p) == "table" then whole(p.total) else 0
        if pt > 0 then
            local pf = math.min(whole(p.found), pt)
            total += pt
            found += pf
            if pf < pt and (worst == nil or pf / pt < worstFraction) then worst, worstFraction = key, pf / pt end
        end
    end
    local fraction = if total > 0 then found / total else 0
    if total > 0 and found >= total then
        return {id = "collect", title = "COLLECT", progress = "Everything found!", step = "You did it!", fraction = 1, done = true}
    end
    local step = if total - found == 1 then "1 more to find" elseif worst == nil or worst == "species" then "Hatch eggs to find more" else HINTS[worst]
    return {id = "collect", title = "COLLECT", progress = string.format("%d of %d found", found, total), step = step, fraction = fraction, done = false}
end

-- opts.dinos: FusionAction list rows (or nil), opts.stages, speciesName, patternName (same shape as NextGoal.fusion).
function Goals.perfect(opts: any)
    local dinos = opts.dinos
    local diamonds = 0
    if type(dinos) == "table" then
        for _, d in dinos do
            if type(d) == "table" and d.stage == "diamond" then diamonds += 1 end
        end
    end
    local fusion = NextGoal.fusion(dinos, opts)
    if fusion then
        return {id = "perfect", title = "FAVOURITE", progress = fusion.text, step = if fusion.ready then "Tap FUSION now!" else "Hatch more of the same",
            fraction = fusion.fraction, done = false}
    end
    if diamonds > 0 then
        return {id = "perfect", title = "FAVOURITE", progress = "Diamond dino!", step = "Make another one", fraction = 1, done = true}
    end
    return {id = "perfect", title = "FAVOURITE", progress = "Pick a favourite", step = "Collect copies, then FUSION", fraction = 0, done = false}
end

-- opts.owned: species the player owns (every owned species is playable, BD-423), opts.total: species in the game.
function Goals.play(opts: any)
    local total, owned = whole(opts.total), whole(opts.owned)
    owned = math.min(owned, total)
    if total > 0 and owned >= total then
        return {id = "play", title = "PLAY", progress = "All dinos playable!", step = "Try each one", fraction = 1, done = true}
    end
    return {id = "play", title = "PLAY", progress = if owned == 1 then "1 dino to play" else string.format("%d dinos to play", owned),
        step = "Hatch a new kind to try", fraction = if total > 0 then owned / total else 0, done = false}
end

-- Returns the three lines in Goals.Order.
function Goals.lines(opts: any)
    local o = if type(opts) == "table" then opts else {}
    local species = if type(o.species) == "table" then o.species else {}
    return {Goals.collect(species), Goals.perfect(o), Goals.play(species)}
end

-- collection: decoded CollectionJson {speciesId = {base, gold, diamond}}, order: species ids in Index order,
-- extraFound(id): true when the Index also counts the species as found (event mutation / saved traits).
-- found = Index "found" count; owned = species with at least one dino copy.
function Goals.speciesCounts(collection: any, order: any, extraFound: any)
    local found, owned = 0, 0
    local c = if type(collection) == "table" then collection else {}
    local extra = if type(extraFound) == "function" then extraFound else function(_: string) return false end
    local ids = if type(order) == "table" then order else {}
    for _, id in ids do
        local e = c[id]
        local copies = if type(e) == "table" then whole(e.base) + whole(e.gold) + whole(e.diamond) else 0
        if copies > 0 then owned += 1 end
        if copies > 0 or extra(id) then found += 1 end
    end
    return {found = found, owned = owned, total = #ids}
end

-- speciesCounts plus parts: colours / patterns seen on dinos the player owns now (list rows: genes.primaryColorId,
-- genes.patternId, mutationId) and mutations from the collection events/variants. Derived only; nothing is saved or
-- rewritten. BD-436: `discovered` (optional, owner-only DiscoveryJson counts {colours, patterns, mutations}) is the permanent log; when it
-- is present each part uses max(log, derived) so a dino fused away never un-discovers its colour; absent = derived only (older saves).
-- totals = {colours, patterns, mutations}.
function Goals.indexCounts(collection: any, order: any, extraFound: any, dinos: any, totals: any, discovered: any)
    local out = Goals.speciesCounts(collection, order, extraFound)
    local t = if type(totals) == "table" then totals else {}
    local colours, patterns, mutations = {}, {}, {}
    if type(dinos) == "table" then
        for _, d in dinos do
            if type(d) == "table" then
                local g = if type(d.genes) == "table" then d.genes else {}
                if type(g.primaryColorId) == "string" then colours[g.primaryColorId] = true end
                if type(g.patternId) == "string" and g.patternId ~= "" then patterns[g.patternId] = true end
                if type(d.mutationId) == "string" and d.mutationId ~= "" and d.mutationId ~= "none" then mutations[d.mutationId] = true end
            end
        end
    end
    if type(collection) == "table" then
        for _, e in collection do
            if type(e) == "table" then
                if type(e.events) == "table" then for id, n in e.events do if whole(n) > 0 then mutations[id] = true end end end
                if type(e.variants) == "table" then
                    for _, v in e.variants do
                        if type(v) == "table" and whole(v.count) > 0 and type(v.mutationId) == "string" then mutations[v.mutationId] = true end
                    end
                end
            end
        end
    end
    local log = if type(discovered) == "table" then discovered else nil
    local function count(set: any, total: any, logged: any)
        local n = 0
        for _ in set do n += 1 end
        if log ~= nil then n = math.max(n, whole(logged)) end
        return {found = math.min(n, whole(total)), total = whole(total)}
    end
    local l = log or {}
    out.parts = {colours = count(colours, t.colours, l.colours), patterns = count(patterns, t.patterns, l.patterns), mutations = count(mutations, t.mutations, l.mutations)}
    return out
end

return Goals
