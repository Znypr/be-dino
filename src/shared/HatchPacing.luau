--!strict
-- BD-1164 (docs/226): hatch pacing for big batches, behind Config.HatchFastCommonsEnabled (default false).
-- OWNER 2026-11-10 (docs/115): eggs stay one at a time in rising rarity; Common and Uncommon flash by in about 1 s each, Rare and up keep
-- the full slow build-up and reveal. LEAD decision: the first 3 eggs a brand-new save is shown always get the full show.
-- Pure rules only (no Instances, no clock, no remote): WHICH egg takes the fast path, which one moves on by itself, and which Rare+ egg
-- gets the short "something special is coming" lead-in. The timings live in HatchTimeline (durations with fast = true), the drawing in
-- client/HatchSequence. Presentation only: nothing here reads or changes what the server committed, the odds or the economy.
-- Tested by tools/verify_hatch_pacing.py (with mutants).
local RevealSkip = require(script.Parent.RevealSkip)
local P = {}

P.FullShowFirstEggs = 3 -- LEAD decision: a brand-new save sees its first 3 eggs with the full show (first impression, docs/225)
P.FastMaxRarity = 2 -- Common (1) and Uncommon (2) are fast; Rare (3) and up keep the full show
P.SpecialAfterFast = 2 -- the lead-in needs at least this many fast eggs right before the Rare+ egg (otherwise there is no contrast)
P.SpecialLead = .7 -- seconds the Rare+ egg holds still and glows before its normal build-up starts (PROVISIONAL)
P.SpecialCue = "level_up" -- an existing soft registered sound (Sfx.Sounds), no new id
P.SpecialText = "Ooh! Something special!" -- docs/72: short and obvious

-- A save that holds only the starter Compy has never hatched a dinosaur (FtueRules.collectionCopies; the client has no hatch counter).
function P.isFresh(copies: any): boolean
    return type(copies) == "number" and copies == copies and copies <= 1
end

-- The pacing facts of one hatch party live on the party table of HatchTimeline (T.session; T.batchReset clears them):
-- shown = eggs drawn so far, fastRun = fast eggs in a row right before this one, fresh = the save was brand-new when the party started.
-- Called when an egg is put on screen, BEFORE its server answer is drawn: only the first egg of a party decides `fresh`.
function P.begin(batch: any, copies: any)
    if type(batch) ~= "table" then return end
    if (batch.shown or 0) == 0 then
        batch.fresh = P.isFresh(copies)
        batch.fastRun = 0
    end
end

-- egg = {rarity = 1..5, failed = boolean, remaining = eggs still to open after this one, outcome = RevealSkip outcome table}.
-- Returns {fast, auto, special, why}. fast = short timings; auto = moves on by itself (never on the last egg: DONE needs the player);
-- special = full show with the lead-in. Flag off: always the full show and the party table is not touched (exactly as before).
function P.plan(enabled: boolean, batch: any, egg: any)
    if enabled ~= true or type(batch) ~= "table" or type(egg) ~= "table" then
        return {fast = false, auto = false, special = false, why = "off"}
    end
    local shown = (batch.shown or 0) + 1
    batch.shown = shown
    local run = batch.fastRun or 0
    local rarity = egg.rarity
    local failed = egg.failed == true
    local why = "fast"
    if batch.fresh == true and shown <= P.FullShowFirstEggs then
        why = "first"
    elseif failed then
        why = "fast" -- a cracked egg shows only its splat: short too
    elseif RevealSkip.isNotable(egg.outcome) then
        why = "notable" -- Shiny, BIG, event mutation, Rainbow, Astra, secret: always the full show
    elseif type(rarity) ~= "number" or rarity ~= rarity or rarity > P.FastMaxRarity then
        why = "rare" -- Rare and up (and anything unreadable) keep the full show
    end
    local fast = why == "fast"
    batch.fastRun = if fast then run + 1 else 0
    local remaining = if type(egg.remaining) == "number" then egg.remaining else 0
    local special = why == "rare" and not failed and type(rarity) == "number" and run >= P.SpecialAfterFast
    return {fast = fast, auto = fast and remaining > 0, special = special, why = why}
end

-- Seconds of one egg from "on screen" to "the next egg is on screen", for the measurement in docs/226 (tools/verify_hatch_pacing.py --report).
-- durs = HatchTimeline.durations(...); plan as above (nil = full show); tapSeconds = how long the player takes to tap after the hint
-- (an ASSUMPTION of the measurement, not a rule); fastForward = the player taps the build-up away as soon as the tap gate allows.
function P.eggSeconds(durs: any, plan: any, tapSeconds: number, fastForward: boolean?): number
    local build = durs.build
    if fastForward and not durs.fast and build > durs.tapGate then build = durs.tapGate end
    local seconds = build + durs.burst + durs.settle + (durs.revealLag or 0)
    if plan and plan.special then seconds += P.SpecialLead end
    if not (plan and plan.auto) then seconds += tapSeconds end
    return seconds
end

return P
