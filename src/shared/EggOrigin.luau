--!strict
-- BD-175: "Where did this dino come from?" view model for the Dino Index egg button and its popup.
-- Pure data (no Instances). Input is the server's read-only dinosaur details copy (`originalEgg` for hatched copies,
-- `origin.kind == "fusion"` for fused ones). Older copies without data show "Unknown egg"; nothing is guessed or rewritten.
-- Conditions belong to the EGG only (BD-181): the popup shows the egg's condition, never a dino condition.
local Origin = {}

local MONTHS = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}

-- "Oct 14, 2026" from a unix time; nil when the time is not a usable number.
function Origin.dateText(t: any): string?
    if type(t) ~= "number" or t ~= t or t < 86400 or t > 4102444800 then return nil end
    local parts = os.date("!*t", math.floor(t))
    return string.format("%s %d, %d", MONTHS[parts.month], parts.day, parts.year)
end

-- Egg source, in words a child understands.
function Origin.sourceText(egg: any): string
    local source = if type(egg.source) == "table" then egg.source.kind else nil
    local kind = egg.kind
    if source == "nest" or kind == "nest_egg" then return "Nest egg" end
    if source == "crystal_shop" or kind == "crystal_shop" then return "Shop egg" end
    if source == "run" or kind == "run_egg" or kind == "alpha_chest" or kind == "run" then return "Run egg" end
    return "Special egg"
end

-- details = server dinosaur details; catalog = FusionSelection.buildCatalog; sel = FusionSelection;
-- conditionName(id) -> display name or nil (EggGenetics.condition).
-- Result: {kind = "egg"|"fusion"|"unknown", title, lines = {...}, conditionId, genes, source, when, eventId, tint = genes}
function Origin.view(details: any, catalog: any, sel: any, conditionName: ((string) -> string?)?)
    local d = if type(details) == "table" then details else {}
    local origin = if type(d.origin) == "table" then d.origin else {}
    -- BD-352: the dino's own event mutation (not an egg trait); the popup shows it as a badge next to the egg.
    local mutationId = if type(d.mutationId) == "string" and d.mutationId ~= "" then d.mutationId else nil
    if origin.kind == "fusion" then
        return {kind = "fusion", title = "Made by fusion",
            lines = {"This dino was made from other dinos.", "A fused dino has no single egg."}, mutationId = mutationId}
    end
    local egg = d.originalEgg
    if origin.kind ~= "hatch" or type(egg) ~= "table" then
        return {kind = "unknown", title = "Unknown egg",
            lines = {"This older dino has no egg memory."}, mutationId = mutationId}
    end
    local genes = if type(egg.genes) == "table" then egg.genes else nil
    local conditionId = if genes and type(genes.conditionId) == "string" then genes.conditionId else "normal"
    local conditionLabel = (if conditionName then conditionName(conditionId) else nil) or sel.name(catalog, "conditions", conditionId, "Normal")
    local lines = {}
    table.insert(lines, "Egg look: " .. conditionLabel)
    table.insert(lines, "From: " .. Origin.sourceText(egg))
    table.insert(lines, "Found: " .. (Origin.dateText(egg.readyAt) or "a while ago"))
    if genes and genes.primaryColorId then
        table.insert(lines, "Colors: " .. sel.geneLine(genes, catalog))
        table.insert(lines, "Pattern: " .. sel.name(catalog, "patterns", genes.patternId, "Plain"))
    end
    if type(egg.eventId) == "string" and egg.eventId ~= "" and egg.eventId ~= "clear" then
        table.insert(lines, "Weather: " .. sel.name(catalog, "weather", egg.eventId, egg.eventId))
    end
    return {kind = "egg", title = "Original egg", lines = lines, conditionId = conditionId, conditionName = conditionLabel,
        genes = genes, mutationId = mutationId, source = Origin.sourceText(egg), when = Origin.dateText(egg.readyAt), eventId = egg.eventId}
end

return Origin
