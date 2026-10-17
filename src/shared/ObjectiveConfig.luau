--!strict
-- BD-072 (docs/66 section 5): the mini-objective catalogue. DATA ONLY, no behaviour (ObjectiveRules reads it).
-- PROVISIONAL: every reward amount and cap below is a starting number from docs/66, NOT owner-approved balance
-- (docs/09: never invent reward amounts as final). Rewards are Crystals (and optionally account XP) ONLY: never Robux,
-- never random items, never eggs, nests or species. The whole feature is behind Config.ObjectivesEnabled (false in every
-- committed build, pinned by tools/release_profiles.py). Verified by tools/verify_objectives.py.
local Catalogue = {
    -- Tutorial: ordered, one-time, one shown at a time (UI shows the first unclaimed). Total 160 Crystals (docs/66).
    {id = "T1", group = "tutorial", name = "Eat 10 food", event = "food_eaten", goal = 10, reward = {crystals = 10}},
    {id = "T2", group = "tutorial", name = "Finish your first run", event = "run_end", goal = 1, reward = {crystals = 20}},
    {id = "T3", group = "tutorial", name = "Hatch 3 eggs", event = "egg_hatched", goal = 3, reward = {crystals = 15}},
    {id = "T4", group = "tutorial", name = "Equip a dino in the Index", event = "dino_equipped", goal = 1, reward = {crystals = 10}},
    {id = "T5", group = "tutorial", name = "Use leap once", event = "leap_used", goal = 1, reward = {crystals = 10}},
    {id = "T6", group = "tutorial", name = "Buy a potion", event = "potion_bought", goal = 1, reward = {crystals = 25}},
    {id = "T7", group = "tutorial", name = "Reach level 3", event = "level_reached", minValue = 3, goal = 1, reward = {crystals = 20}},
    {id = "T8", group = "tutorial", name = "Collect a second species", event = "species_new", goal = 1, reward = {crystals = 30}},
    {id = "T9", group = "tutorial", name = "Open the Fusion menu", event = "fusion_menu_opened", goal = 1, reward = {crystals = 20}},
    -- Short: 3 active at a time, rolled from the pool by the window number, reset every 30 minutes (docs/66 section 6).
    {id = "S1", group = "short", name = "Hatch 10 eggs", event = "egg_hatched", goal = 10, reward = {crystals = 15}},
    {id = "S2", group = "short", name = "Eat 40 food", event = "food_eaten", goal = 40, reward = {crystals = 10}},
    {id = "S3", group = "short", name = "Finish a run", event = "run_end", goal = 1, reward = {crystals = 15}},
    {id = "S4", group = "short", name = "Use leap 3 times", event = "leap_used", goal = 3, reward = {crystals = 10}},
    {id = "S5", group = "short", name = "Catch an event egg", event = "event_egg_caught", goal = 1, reward = {crystals = 25}},
    -- Daily: 3 active at a time, reset at UTC midnight (docs/66 owner question 1, recommended yes; not yet answered).
    {id = "D1", group = "daily", name = "Hatch 60 eggs", event = "egg_hatched", goal = 60, reward = {crystals = 50}},
    {id = "D2", group = "daily", name = "Finish 3 runs", event = "run_end", goal = 3, reward = {crystals = 40}},
    {id = "D3", group = "daily", name = "Buy any potion", event = "potion_bought", goal = 1, reward = {crystals = 30}},
    {id = "D4", group = "daily", name = "Collect a new species", event = "species_new", goal = 1, reward = {crystals = 60}},
    {id = "D5", group = "daily", name = "Add a dino toward a fusion step", event = "fusion_step_added", goal = 1, reward = {crystals = 40}},
    {id = "D6", group = "daily", name = "Hatch a Rare or better", event = "rare_hatched", goal = 1, reward = {crystals = 50}},
}

local byId = {}
for _, entry in Catalogue do byId[entry.id] = entry end

return table.freeze({
    SchemaVersion = 1, -- profile.objectives.v. A stored value NEWER than this is never touched (rollback safety, docs/111).
    Catalogue = table.freeze(Catalogue),
    ById = table.freeze(byId),
    -- Event kinds the server may record (BD-074 wires the real gameplay hooks; BD-073 only accepts them).
    EventKinds = table.freeze({
        food_eaten = true, run_end = true, egg_hatched = true, dino_equipped = true, leap_used = true, potion_bought = true,
        level_reached = true, species_new = true, fusion_menu_opened = true, event_egg_caught = true, fusion_step_added = true,
        rare_hatched = true,
    }),
    -- Windows come from the SERVER clock (os.time(), unix seconds, UTC): window = floor(now / seconds).
    Windows = table.freeze({
        short = table.freeze({seconds = 1800, active = 3, salt = 1013904223}),
        daily = table.freeze({seconds = 86400, active = 3, salt = 2654435761}),
    }),
    ProgressCapMultiplier = 2, -- a counter never exceeds 2 x goal inside one window (docs/66 section 7)
    -- PROVISIONAL reward caps (none of these is owner-approved balance).
    MaxClaimCrystals = 100, -- one claim never grants more than this, whatever the catalogue says
    MaxClaimXP = 50,
    WindowCrystalCapPerDay = 600, -- Short + Daily crystals claimed per UTC day; a claim past it is clamped to what is left
    -- Bounded state.
    SeenMax = 48, -- remembered event ids (egg:<outcomeId>, run:<runId>) so a replayed event never counts twice
    PendingMax = 64, -- server-side unflushed events per player
    FlushSeconds = 30, -- service flush cadence; claim and lease release flush too
    ClaimTokenMax = 80,
    -- ObjectiveAction remote limiter (fixed window per player), PROVISIONAL.
    RequestsPerWindow = 10,
    RateWindowSeconds = 10,
})
