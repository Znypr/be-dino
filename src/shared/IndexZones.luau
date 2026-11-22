--!strict
-- BD-1299 (owner 2026-11-23 "Rebuild both now", target docs/evidence/2026-11-23-index-proposal/proposal.jpg): the Dino Index ZONES and their
-- free rewards, used ONLY while Config.IndexZonesEnabled is on (playtest profile). Pure: no requires, no Roblox services, no Instances; the
-- server (ProfileIndexZones, inside the claim UpdateAsync) and the client (client/DinoIndexKit) run the SAME tables, so the CLAIM button and
-- the grant never disagree. tools/verify_index_zones.py runs it offline.
--   * four zones in the picture's order and colours: Meadow, Forest, Beach, Volcano.
--   * each zone pays FREE crystals ONCE when the save has found half of its species (rounded up) and once when it has found all of them.
--     Claimed with the CLAIM button (remote IndexZoneAction, server-validated, idempotent). Never Robux, never a paid line, never random.
--   * stored: profile.indexZoneRewards = {"meadow_half", "beach_all", ...} (ADDITIVE, created lazily by the first claim; an older build
--     ignores and keeps it, docs/111). A word in the list is never paid again, even if a later fusion makes the count drop.
local M = {}

export type Zone = {id: string, name: string, colour: string, rgb: {number}, species: {string}, art: string}

-- PROVISIONAL species split (LEAD decision 2026-11-23, owner delegated 2026-10-16; the owner decides later, docs/115). Built from the
-- world's own data: IslandLife.Babies (meadow: triceratops, parasaurolophus; forest: stegosaurus, brachiosaurus; pine: pachycephalosaurus;
-- beach: gallimimus), LowPolyDinoAssets class Water (ichthyosaurus, mosasaurus, plesiosaurus) and the marine elasmosaurus, the small flyers by
-- the sea (pteranodon, dimorphodon), the small feathered flyers on the meadow (microraptor, archaeopteryx), the armoured and the big top-tier
-- dinos on the volcano (ankylosaurus, quetzalcoatlus, spinosaurus, tyrannosaurus). Every one of the 22 Config.SpeciesOrder species is in
-- exactly one zone (the verifier checks it); inside a zone the order is the Config.SpeciesOrder order. Up to 8 per zone fit one 4 x 2 page.
-- art: the zone's illustrated panel (a Roblox IMAGE id; ChatGPT-made (v3) in the game's own 3D toy look per zone, no text, 256x512, resources/ui/v2/index-zones,
-- docs/77). One entry per zone so it can be swapped; "" = the placeholder (a solid zone-colour panel with the name).
M.Zones = table.freeze({
    {id = "meadow", name = "Meadow", colour = "#72F239", rgb = {114, 242, 57}, art = "rbxassetid://105611360763460",
        species = {"compy", "triceratops", "raptor", "archaeopteryx", "microraptor", "parasaurolophus"}},
    {id = "forest", name = "Forest", colour = "#248A44", rgb = {36, 138, 68}, art = "rbxassetid://124704617850449",
        species = {"stegosaurus", "baryonyx", "brachiosaurus", "pachycephalosaurus", "therizinosaurus"}},
    {id = "beach", name = "Beach", colour = "#E9D197", rgb = {233, 209, 151}, art = "rbxassetid://80194922483150",
        species = {"dimorphodon", "elasmosaurus", "gallimimus", "ichthyosaurus", "mosasaurus", "plesiosaurus", "pteranodon"}},
    {id = "volcano", name = "Volcano", colour = "#F04440", rgb = {240, 68, 64}, art = "rbxassetid://78493119997205",
        species = {"tyrannosaurus", "ankylosaurus", "quetzalcoatlus", "spinosaurus"}},
} :: {Zone})
M.Steps = table.freeze({"half", "all"})
-- PROVISIONAL (LEAD decision 2026-11-23): about two and five normal runs' worth of crystals.
M.Crystals = table.freeze({half = 100, all = 250})
M.MaxStored = 16 -- structural ceiling for the stored list (4 zones x 2 steps = 8 today)
M.PerPage = 8 -- the 4 x 2 grid
-- A found SECRET dino is shown in its zone after the zone's species (by its class), never counted for the rewards or "Found: n/22".
M.SecretZones = table.freeze({Ground = "forest", Water = "beach", Fly = "meadow"})
function M.secretZone(class: any): string return M.SecretZones[class] or "forest" end

function M.zone(id: any): Zone?
    for _, zone in M.Zones do
        if zone.id == id then return zone end
    end
    return nil
end

-- The zone a species is in (nil for a secret or an unknown id).
function M.zoneOf(species: string): Zone?
    for _, zone in M.Zones do
        if table.find(zone.species, species) then return zone end
    end
    return nil
end

-- How many species a step needs: half = half the zone rounded up, all = every one.
function M.need(zone: Zone, step: string): number
    local n = #zone.species
    return if step == "half" then math.ceil(n / 2) else n
end

-- The server's ownsAny test (ProgressionRules.indexFound): any Base / Gold / Diamond copy, a variant or an event copy.
local function ownsAny(entry: any): boolean
    if typeof(entry) ~= "table" then return false end
    for _, key in {"base", "gold", "diamond"} do
        if typeof(entry[key]) == "number" and entry[key] > 0 then return true end
    end
    return (typeof(entry.variants) == "table" and next(entry.variants) ~= nil)
        or (typeof(entry.events) == "table" and next(entry.events) ~= nil)
end

-- How many of the zone's species the collection owns.
function M.found(collection: any, zone: Zone): number
    if typeof(collection) ~= "table" then return 0 end
    local n = 0
    for _, id in zone.species do
        if ownsAny(collection[id]) then n += 1 end
    end
    return n
end

function M.key(zoneId: string, step: string): string return zoneId .. "_" .. step end

-- The stored words as a set. Bad or missing input reads as none.
function M.claimed(stored: any): {[string]: boolean}
    local set = {}
    if typeof(stored) ~= "table" then return set end
    for _, value in stored do
        if typeof(value) == "string" then set[value] = true end
    end
    return set
end

-- The state of one zone step for the button: "claimed" | "ready" (reached, not paid: CLAIM) | "locked" (not reached yet).
function M.state(zone: Zone, step: string, found: number, stored: any): string
    if M.claimed(stored)[M.key(zone.id, step)] then return "claimed" end
    return if found >= M.need(zone, step) then "ready" else "locked"
end

-- The step the rewards box shows: the first one ready, else the first one locked, else "all" (both claimed).
function M.current(zone: Zone, found: number, stored: any): (string, string)
    for _, step in M.Steps do
        local s = M.state(zone, step, found, stored)
        if s == "ready" then return step, s end
    end
    for _, step in M.Steps do
        local s = M.state(zone, step, found, stored)
        if s == "locked" then return step, s end
    end
    return "all", "claimed"
end

-- Server, INSIDE the claim UpdateAsync transform: pays one zone step exactly once. Returns status, crystals:
--   "applied" (paid now), "already" (in the list: nothing changes), "not_reached", "bad_zone", "bad_step", "full" (the wallet cap: nothing
--   changes), "no_wallet", "invalid_state" (a newer build's field: never touched). Only "applied" changes the profile (crystals + the word).
function M.apply(profile: any, zoneId: any, step: any, maxCrystals: number): (string, number)
    if typeof(profile) ~= "table" then return "no_wallet", 0 end
    local zone = M.zone(zoneId)
    if not zone then return "bad_zone", 0 end
    if typeof(step) ~= "string" or not M.Crystals[step] then return "bad_step", 0 end
    local stored = profile.indexZoneRewards
    if stored ~= nil and (typeof(stored) ~= "table" or #stored > M.MaxStored) then return "invalid_state", 0 end
    local key = M.key(zone.id, step)
    if M.claimed(stored)[key] then return "already", 0 end
    if M.found(profile.collection, zone) < M.need(zone, step) then return "not_reached", 0 end
    local wallet = profile.progression
    if typeof(wallet) ~= "table" or typeof(wallet.crystals) ~= "number" then return "no_wallet", 0 end
    local crystals = M.Crystals[step]
    if wallet.crystals + crystals > maxCrystals then return "full", 0 end
    wallet.crystals += crystals
    local list = if stored ~= nil then table.clone(stored) else {}
    table.insert(list, key)
    profile.indexZoneRewards = list
    return "applied", crystals
end

-- ---------------------------------------------------------------- kid words (docs/72)
-- Short card names, like the picture's "Trike" and "Stego": used on a card only when the full name does not fit at 19 px (the selected
-- panel always shows the full name). LEAD decision 2026-11-23.
M.CardNames = table.freeze({
    triceratops = "Trike", stegosaurus = "Stego", tyrannosaurus = "T-Rex", ankylosaurus = "Ankylo", archaeopteryx = "Archaeo",
    brachiosaurus = "Brachio", dimorphodon = "Dimorpho", elasmosaurus = "Elasmo", gallimimus = "Galli", ichthyosaurus = "Ichthyo",
    microraptor = "Micro", mosasaurus = "Mosa", pachycephalosaurus = "Pachy", parasaurolophus = "Parasaur", plesiosaurus = "Plesio",
    pteranodon = "Ptera", quetzalcoatlus = "Quetzal", spinosaurus = "Spino", therizinosaurus = "Therizino",
})
M.RewardsWord, M.ClaimWord, M.GotWord = "Rewards:", "CLAIM!", "Got it!"
-- The line under the crystal when the step is not reached: "Find 3!" (half) / "Find all 6!" (all).
function M.goal(zone: Zone, step: string, found: number): string
    if step == "half" then return "Find " .. tostring(math.max(0, M.need(zone, step) - found)) .. " more!" end
    return "Find all " .. tostring(#zone.species) .. "!"
end
function M.progress(found: number, zone: Zone): string return tostring(found) .. "/" .. tostring(#zone.species) end
function M.toast(crystals: number): string return "+" .. tostring(crystals) .. " Crystals!" end

return M
