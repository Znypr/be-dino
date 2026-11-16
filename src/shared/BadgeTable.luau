--!strict
-- BD-1229 (docs/242 gap 18, flag Config.BadgesEnabled): the badge-id table and the pure rules that say which badges a moment earns.
-- Creating a badge on Roblox is an OWNER account action (Creator Hub, the game, Associated Items, Badges): agents never create them.
-- Every id below stays 0 until the owner pastes the id Roblox gives; a 0 id is skipped, so with the flag on and no ids nothing is awarded.
-- The names, descriptions and icon ideas the owner should use are in docs/evidence/2026-11-16-social/README.md (the "Badges to create" table).
-- Pure: no Roblox services (tools/verify_social.py drives it). The server (BadgeAwardService) decides from settled outcomes only.
local B = {}

B.Order = table.freeze({"welcome", "first_hatch", "first_rare", "first_epic", "first_legendary", "first_shiny", "first_mutant", "index_5", "index_10", "index_all"})

-- key -> Roblox badge id (0 = not created yet). The owner fills these in.
B.Ids = table.freeze({
    welcome = 0, -- "Welcome to Be Dino!": joined the game
    first_hatch = 0, -- "First Hatch": hatched a dino
    first_rare = 0, -- "Rare Find": hatched a Rare (or better) dino
    first_epic = 0, -- "Epic Find": hatched an Epic (or better) dino
    first_legendary = 0, -- "Legendary!": hatched a Legendary dino
    first_shiny = 0, -- "Shiny!": hatched a Shiny dino
    first_mutant = 0, -- "Mutant!": hatched a dino with a weather mutation
    index_5 = 0, -- "Dino Spotter": 5 kinds of dino in the Index
    index_10 = 0, -- "Dino Expert": 10 kinds of dino in the Index
    index_all = 0, -- "Dino Master": every kind of dino in the Index
})

B.RareTier, B.EpicTier, B.LegendaryTier = 3, 4, 5
B.IndexSteps = table.freeze({{key = "index_5", count = 5}, {key = "index_10", count = 10}})

-- A valid badge id is a whole number above 0; anything else (0, junk) means "not created yet": skip.
function B.idOf(key: string, ids: {[string]: any}?): number?
    local id = (ids or B.Ids :: any)[key]
    if type(id) ~= "number" or id ~= id or id < 1 or id % 1 ~= 0 then return nil end
    return id
end

-- Badge keys a settled hatch earns. outcome = the committed hatch outcome (failed, shiny, eventMutationId); tier = the species rarity 1..5;
-- found = how many species this save owns after the hatch; total = how many species exist.
function B.forHatch(outcome: any, tier: number?, found: number?, total: number?): {string}
    local keys = {}
    if type(outcome) ~= "table" or outcome.failed == true then return keys end
    local t = if type(tier) == "number" then tier else 0
    table.insert(keys, "first_hatch")
    if t >= B.RareTier then table.insert(keys, "first_rare") end
    if t >= B.EpicTier then table.insert(keys, "first_epic") end
    if t >= B.LegendaryTier then table.insert(keys, "first_legendary") end
    if outcome.shiny == true then table.insert(keys, "first_shiny") end
    if type(outcome.eventMutationId) == "string" and outcome.eventMutationId ~= "" then table.insert(keys, "first_mutant") end
    local n = if type(found) == "number" then found else 0
    for _, step in B.IndexSteps do
        if n >= step.count then table.insert(keys, step.key) end
    end
    if type(total) == "number" and total > 0 and n >= total then table.insert(keys, "index_all") end
    return keys
end

return B
