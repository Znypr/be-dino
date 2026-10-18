--!strict
-- BD-150 / BD-151 pure logic for the Dino Index species page "My dinos": which copies belong to the species, which
-- copy is selected by default, how a copy maps to an equip request, which card carries the "Equipped" tag, and the
-- filter/sort view. Filtering and sorting are NOT re-implemented: they call FusionSelection (FilterFields, SortKeys,
-- Sel.filter/Sel.sort/Sel.filterOptions) so the Fusion menu and the Dino Index can never disagree.
-- No Instances or services; exercised by tools/verify_inspect.py.
local Sel = require(script.Parent.FusionSelection)
local EggTraits = require(script.Parent.EggTraits)
local Genetics = require(script.Parent.EggGenetics)

local M = {}

M.PageSize = 24 -- cards drawn before SHOW MORE (each card owns one ViewportFrame)
M.StageRank = {base = 0, gold = 1, emerald = 2, diamond = 3}
-- Sheet order. Every key must exist in Sel.SortKeys (verified offline).
M.SortKeys = {"rarest", "recent", "color", "pattern", "species"}
M.SortLabels = {rarest = "Rarest", recent = "Newest", color = "Color", pattern = "Pattern", species = "Species"}
-- Filter groups in sheet order. Every field must exist in Sel.FilterFields. shiny/big are single "yes" chips.
M.FilterGroups = {"colorId", "patternId", "mutationId", "shiny", "big", "stageId"}
local FIELD = {stageId = "stage"}
M.GroupLabels = {colorId = "Color", patternId = "Pattern", mutationId = "Mutation", shiny = "Shiny", big = "BIG",
    stageId = "Stage"}

function M.field(group: string): string return FIELD[group] or group end

-- Every owned copy of one species, newest-to-oldest order is left to the sort.
function M.forSpecies(all, speciesId: string)
    local list = {}
    for _, d in all do
        if type(d) == "table" and d.speciesId == speciesId and type(d.instanceId) == "string" then table.insert(list, d) end
    end
    return list
end

-- Variant key of ONE base-stage copy in the player's collection (what the server checks on equip), or nil when the
-- copy has no per-copy identity (plain Base, event-only, Gold/Emerald/Diamond) and equips as "the species".
function M.variantKey(d): string?
    if type(d) ~= "table" or d.stage ~= "base" then return nil end
    local genes = if type(d.genes) == "table" then d.genes else nil
    if not (d.shiny == true or d.big == true or genes) then return nil end
    return EggTraits.key(if type(d.mutationId) == "string" then d.mutationId else "", d.shiny == true, d.big == true, genes :: any)
end

-- BD-1000: the key a base-stage copy WITHOUT traits (the plain starter, an event-only copy) sends to equip exactly itself. Real variant keys
-- always contain ":" (EggTraits.key), so this can never collide with one; the server stores it as a flag (ProfileCollection.equipSpecies).
M.PlainKey = "plain"

-- What the client sends for EQUIP of copy d: always the species, plus the exact variant key when it has one, or PlainKey for a
-- trait-free base copy (so it is no longer mistaken for "any copy": the server used to play the best variant instead).
function M.equipRequest(d)
    if type(d) ~= "table" or type(d.speciesId) ~= "string" then return nil end
    local key = M.variantKey(d)
    if key == nil and d.stage == "base" then key = M.PlainKey end
    return {speciesId = d.speciesId, variantKey = key}
end

-- Server-side mirror used by the offline check: a key is only equippable when the collection entry owns it.
function M.ownsVariant(entry, key: any): boolean
    if type(key) ~= "string" or #key < 1 or #key > 160 then return false end
    if type(entry) ~= "table" or type(entry.variants) ~= "table" then return false end
    local v = entry.variants[key]
    return type(v) == "table" and type(v.count) == "number" and v.count > 0
end

-- attrs: {speciesId, genes (table|nil), shiny, big, mutationId} read from the EquippedXxx player attributes.
local function matchesKeyed(d, attrs): boolean
    if d.speciesId ~= attrs.speciesId or d.stage ~= "base" or not M.variantKey(d) then return false end
    local dg, ag = d.genes, attrs.genes
    if (dg == nil) ~= (ag == nil) then return false end
    if dg and ag and Genetics.key(dg) ~= Genetics.key(ag) then return false end
    return (d.shiny == true) == (attrs.shiny == true) and (d.big == true) == (attrs.big == true)
        and (d.mutationId or "") == (attrs.mutationId or "")
end

-- Exactly one instanceId carries the "Equipped" tag (or nil). `list` should be in best-first order so a keyless
-- equip (plain / Gold / Diamond) tags the best copy of the species.
function M.equippedId(list, attrs): string?
    if type(attrs) ~= "table" then return nil end
    for _, d in list do if matchesKeyed(d, attrs) then return d.instanceId end end
    if attrs.genes == nil and attrs.shiny ~= true and attrs.big ~= true then
        for _, d in list do
            if d.speciesId == attrs.speciesId and not M.variantKey(d) then return d.instanceId end
        end
    end
    return nil
end

-- Filters: group -> value. Maps sheet groups onto FusionSelection filter fields.
function M.toFilters(chosen)
    local filters: {[string]: any} = {}
    for group, value in chosen do filters[M.field(group)] = value end
    return filters
end

-- The grid view: Sel.filter then Sel.sort, never a second implementation.
function M.view(list, chosen, sortKey: string, catalog)
    local key = if table.find(M.SortKeys, sortKey) then sortKey else "rarest"
    return Sel.sort(Sel.filter(list, M.toFilters(chosen or {})), key, {}, {}, catalog)
end

function M.defaultSelection(list, catalog): string?
    local first = M.view(list, {}, "rarest", catalog)[1]
    return if first then first.instanceId else nil
end

-- Choice lists for the sheet, from the owned copies only (so a chip never leads to an empty grid by itself).
function M.options(list, catalog)
    local o = Sel.filterOptions(list, catalog)
    local result: {[string]: {any}} = {
        colorId = o.colorId, patternId = o.patternId, stageId = o.stage,
        shiny = {true}, big = {true}, mutationId = {},
    }
    -- Mutation chips: real mutations only ("none" is every other dino and adds nothing).
    for _, id in o.mutationId do if id ~= "none" then table.insert(result.mutationId, id) end end
    -- Stage order, not alphabet.
    table.sort(result.stageId, function(a, b) return (M.StageRank[a] or 9) < (M.StageRank[b] or 9) end)
    return result
end

function M.valueName(group: string, value, catalog): string
    if group == "shiny" then return "Shiny" end
    if group == "big" then return "BIG" end
    if group == "stageId" then return Sel.stageTitle(value) end
    if group == "colorId" then return Sel.name(catalog, "colors", value) end
    if group == "patternId" then return Sel.name(catalog, "patterns", value) end
    if group == "mutationId" then return Sel.name(catalog, "mutations", value) end
    return tostring(value)
end

-- Removable chips for the active filters, in sheet order.
function M.activeChips(chosen, catalog)
    local chips = {}
    for _, group in M.FilterGroups do
        local value = chosen[group]
        if value ~= nil then table.insert(chips, {group = group, value = value, text = M.valueName(group, value, catalog)}) end
    end
    return chips
end

function M.header(speciesName: string, count: number): string
    return speciesName .. " x " .. count
end

-- BD-507: card layout of one "My dinos" card (design px). The SHINY / BIG pills and the mutation badge sit in a band UNDER the dino thumbnail,
-- never over it (they used to cover the dino at the left). Everything is stacked up from the bottom: EQUIPPED tag, colour swatch, pattern name,
-- then the badge row, then the pill row, and the thumbnail takes the height that is left (a plain dino gets the whole band, so the thumbnail
-- only shrinks when the card really carries a ribbon). Pills are 14 px text (docs/114 s4.4), so the pill row is 17 high, the mutation badge 22.
M.Card = {w = 120, h = 160, top = 4, tagH = 18, swatchH = 9, labelH = 17, pillH = 17, chipH = 22, gap = 2, minThumbH = 56}
function M.cardRows(pills: number, chip: boolean)
    local C = M.Card
    local tagY = C.h - 2 - C.tagH
    local swatchY = tagY - C.gap - C.swatchH
    local labelY = swatchY - C.gap - C.labelH
    local y = labelY - C.gap
    local rows: {[string]: number} = {tagY = tagY, swatchY = swatchY, labelY = labelY}
    if chip then
        y -= C.chipH
        rows.chipY = y
        y -= C.gap + 1
    end
    if pills > 0 then
        y -= C.pillH
        rows.pillY = y
        y -= C.gap
    end
    rows.thumbH = y - C.top -- the thumbnail runs from `top` down to just above the first ribbon row
    return rows
end

-- Card ribbons: short words, never colour-only.
function M.ribbons(d, catalog): {string}
    local list = {}
    if d.shiny == true then table.insert(list, "SHINY") end
    if d.big == true then table.insert(list, "BIG") end
    if type(d.mutationId) == "string" and d.mutationId ~= "" then table.insert(list, string.upper(Sel.name(catalog, "mutations", d.mutationId))) end
    return list
end

-- Cards drawn for a view: first `shown` entries plus how many remain behind SHOW MORE.
function M.page(view, shown: number)
    local count = math.min(#view, math.max(shown, M.PageSize))
    return count, #view - count
end

-- Roblox allows ~32 live EditableImages (pattern textures), so only cards inside the scroll window (plus one row
-- of buffer) own a live preview, never more than MaxLivePreviews; the big InspectView is one more. Returns the
-- first and last card index (1-based, inclusive) that should be mounted.
M.MaxLivePreviews = 20
function M.window(canvasY: number, viewH: number, cellH: number, pad: number, cols: number, total: number)
    if total <= 0 or cols < 1 then return 1, 0 end
    local row = math.max(cellH + pad, 1)
    local firstRow = math.max(0, math.floor(canvasY / row) - 1)
    local lastRow = math.ceil((canvasY + viewH) / row)
    local first = firstRow * cols + 1
    local last = math.min(total, (lastRow + 1) * cols)
    if last - first + 1 > M.MaxLivePreviews then last = first + M.MaxLivePreviews - 1 end
    return math.min(first, total), last
end

-- Keep the selection if it is still in the view, else the first card, else nil.
function M.settleSelection(view, selectedId: string?): string?
    if selectedId then for _, d in view do if d.instanceId == selectedId then return selectedId end end end
    return if view[1] then view[1].instanceId else nil
end

return M
