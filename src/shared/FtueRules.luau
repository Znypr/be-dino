--!strict
-- First-time-player rules (docs/112, BD-365..368). Pure: no Instances, services or remotes. Tested by tools/verify_ftue_*.py.
-- Nothing here changes an economy number. It only (a) keeps the first eggs of a brand-new profile from being Cracked,
-- (b) decides when the calm first-run hint shows, and (c) when the left menu collapses on a first run.
local Rules = {}

-- BD-365 (lead decision 2026-10-16): the first SafeEggs eggs a new profile gets are never Cracked ("safe"). After that the
-- normal Cracked odds apply (owner target 50% at tier 0, docs/09). Derived from existing data: no new persistent field.
Rules.SafeEggs = 2 -- same number as ProgressionConfig.SafeEggs (verify_ftue_rules); the player-facing line is OddsCopy.safeEggsLine

local function copiesOf(entry: any): number
    if type(entry) ~= "table" then return 0 end
    local n = 0
    for _, key in { "base", "gold", "diamond" } do
        local v = entry[key]
        if type(v) == "number" and v == v and v > 0 then n += v end
    end
    for _, group in { entry.variants, entry.events } do
        if type(group) == "table" then
            for _, v in group do
                local c = if type(v) == "table" then v.count else v
                if type(c) == "number" and c == c and c > 0 then n += c end
            end
        end
    end
    return n
end

-- Dinosaur copies in a collection table (every species, every stack). A new profile holds exactly the starter Compy (1).
function Rules.collectionCopies(collection: any): number
    if type(collection) ~= "table" then return 0 end
    local total = 0
    for _, entry in collection do total += copiesOf(entry) end
    return total
end

local function count(list: any): number
    return if type(list) == "table" then #list else 0
end

-- Eggs this profile has already hatched (or failed to hatch). Counts "chest_claim" operations (every hatch records one, kept
-- while recent) and, for older profiles whose operations rolled off, any copies beyond the starter Compy mean "not new".
function Rules.hatchedEggs(profile: any): number
    if type(profile) ~= "table" then return 0 end
    local claims = 0
    if type(profile.recentOperations) == "table" then
        for _, op in profile.recentOperations do
            if type(op) == "table" and op.kind == "chest_claim" then claims += 1 end
        end
    end
    local beyondStarter = math.max(0, Rules.collectionCopies(profile.collection) - 1)
    return math.max(claims, if beyondStarter > 0 then Rules.SafeEggs else 0)
end

-- Eggs already rolled and waiting (queue, run bank, banked grants): they used up the safe slots when they were rolled.
function Rules.waitingEggs(profile: any): number
    if type(profile) ~= "table" then return 0 end
    local grants = if type(profile.pendingChestGrants) == "number" then math.max(0, profile.pendingChestGrants) else 0
    return count(profile.eggs) + count(profile.runEggBank) + grants
end

-- How many of the NEXT eggs rolled for this profile must be non-Cracked. 0 for any veteran profile.
function Rules.safeEggsLeft(profile: any): number
    return math.max(0, Rules.SafeEggs - Rules.hatchedEggs(profile) - Rules.waitingEggs(profile))
end

-- Client view of the same rule. The client does not hold recentOperations, so it uses what it can see: any copy beyond the
-- starter Compy means an egg was already hatched (nothing left); otherwise the eggs in the line and the banked ones
-- (ActiveChestCount, QueuedEggsWaiting) have already used the safe slots, exactly like waitingEggs above.
-- Only run eggs are covered (ProfileRepository run settlement); shop and nest eggs roll the normal odds.
function Rules.safeEggsLeftView(copies: number, activeEggs: number, waitingEggs: number): number
    if copies > 1 then return 0 end
    return math.max(0, Rules.SafeEggs - math.max(0, activeEggs) - math.max(0, waitingEggs))
end

-- Condition weights with Cracked removed (its weight set to 0); the other weights keep their proportions because the
-- roll normalises by the total. Returns a new table.
function Rules.withoutCracked(weights: { number }, crackedIndex: number): { number }
    local out = table.clone(weights)
    out[crackedIndex] = 0
    return out
end

-- BD-366 first-run hint. `state`: running, hasFoundEgg, nearSpecialFood (an egg or amber pickup is close).
Rules.HintGrow = "Eat food to grow. Bigger dinos find eggs!"
Rules.HintNear = "Look for a glowing egg!"
Rules.NearDistance = 40 -- studs
function Rules.hint(state: any): string?
    if type(state) ~= "table" or state.running ~= true or state.hasFoundEgg == true then return nil end
    return if state.nearSpecialFood == true then Rules.HintNear else Rules.HintGrow
end

-- Food named "egg" or "amber" is worth the most (15 and 50 points, FoodService TYPES); berries 1, fruit 4.
function Rules.isSpecialFood(name: any): boolean
    return name == "egg" or name == "amber"
end

-- "Found an egg" ever? sessionCatch = saw a catch this session; the rest read the replicated player attributes.
function Rules.hasFoundEgg(info: any): boolean
    if type(info) ~= "table" then return false end
    if info.sessionCatch == true then return true end
    for _, key in { "activeEggs", "waitingEggs", "lastRunEggs" } do
        local v = info[key]
        if type(v) == "number" and v > 0 then return true end
    end
    return type(info.copies) == "number" and info.copies > 1
end

-- BD-440 (docs/130): the goal line and the Goals panel stay hidden until the first egg is found (one less thing on minute zero).
function Rules.showGoals(info: any): boolean
    return Rules.hasFoundEgg(info)
end

-- BD-367: the egg moment. One at a time: a minimum gap, and only the first few eggs of a run get the toast and sparkle
-- (a long run must not stack spam; the HUD counter still pops for every egg).
Rules.FoundText = "You found an egg!"
Rules.MomentGap = 5 -- seconds between moments
Rules.MomentsPerRun = 4
Rules.SparkleCount = 10
Rules.SoundAlias = "egg_found"
function Rules.momentAllowed(previous: number?, now: number, running: boolean, sinceLast: number?, momentsThisRun: number): boolean
    if not running or previous == nil or now <= previous then return false end
    if momentsThisRun >= Rules.MomentsPerRun then return false end
    return sinceLast == nil or sinceLast >= Rules.MomentGap
end
-- Reduce Motion: toast and sound stay, the sparkle burst does not.
function Rules.sparkle(motionEnabled: boolean): number
    return if motionEnabled then Rules.SparkleCount else 0
end

-- BD-368: collapsed left menu. Sticky for a whole run: decided when the run starts.
Rules.KeepButtons = { potions = true, settings = true }
Rules.MenuChipText = "MENU"
Rules.MenuAutoCloseSeconds = 8
function Rules.collapseForRun(runStarting: boolean, hasFoundEgg: boolean): boolean
    return runStarting and not hasFoundEgg
end
function Rules.buttonVisible(destination: string, collapsed: boolean, expanded: boolean): boolean
    if not collapsed or expanded then return true end
    return Rules.KeepButtons[destination] == true
end
function Rules.chipVisible(collapsed: boolean, expanded: boolean): boolean
    return collapsed and not expanded
end

-- BD-442 (docs/132): ONE gentle "go" cue on the EXPLORE ISLAND button for a brand-new player, until the first run starts.
-- Shows only at the hub (Sanctuary), only before any run began this session and before any egg was ever found, and not
-- while a menu covers the screen (no competing pulses). Reduce Motion = a still highlight (see GoCue).
Rules.GoCueText = "Tap to go!"
function Rules.goCueShown(state: any): boolean
    if type(state) ~= "table" then return false end
    return state.runState == "Sanctuary" and state.runStarted ~= true and state.hasFoundEgg ~= true and state.menuOpen ~= true
end

-- BD-1163 (docs/225) STARTER RUN: only the first run of a brand-new profile is short and generous. Everything here is pure; the server
-- applies it only while Config.StarterRunEnabled is true and passes the PROVISIONAL numbers in (Config.StarterRunEggs / MinEggs / SafeEggs).
-- WHO: a profile with zero settled runs, read from data the profile already has (no new stored field): no settled run id, no run or hatch
-- operation, no egg hatched or waiting, no nest, no account XP. Anything unreadable means "not new" (the normal economy).
function Rules.starterQualifies(profile: any): boolean
    if type(profile) ~= "table" then return false end
    local checkpoint = profile.lastCheckpoint
    if type(checkpoint) ~= "table" or checkpoint.lastSettledRunId ~= nil then return false end
    if profile.settledRuns ~= nil and (type(profile.settledRuns) ~= "table" or #profile.settledRuns > 0) then return false end
    if type(profile.recentOperations) ~= "table" then return false end
    for _, op in profile.recentOperations do
        if type(op) ~= "table" or op.kind == "run" or op.kind == "chest_claim" then return false end
    end
    if Rules.hatchedEggs(profile) > 0 or Rules.waitingEggs(profile) > 0 or count(profile.eggNests) > 0 then return false end
    local progress = profile.progression
    if progress ~= nil and (type(progress) ~= "table" or (type(progress.accountXP) == "number" and progress.accountXP > 0)) then return false end
    return true
end
-- EGG FLOOR: a starter run that caught at least one egg settles at least `minEggs` eggs (the starter card shows at StarterRunEggs caught, so
-- "reached the card" is covered by "caught one"). A run with no egg stays empty; a bigger run is never lowered. Bad input changes nothing.
function Rules.starterEggFloor(eggs: any, minEggs: any): number
    if type(eggs) ~= "number" or eggs ~= eggs then return 0 end
    local whole = math.max(0, math.floor(eggs))
    if whole < 1 or type(minEggs) ~= "number" or minEggs ~= minEggs then return whole end
    return math.max(whole, math.floor(minEggs))
end
-- SAFE EGGS on the starter run: every guaranteed egg hatches, so the first `starterSafe` eggs are never Cracked (2 -> 3). Never fewer than
-- the normal rule gives.
function Rules.starterSafeEggs(safeLeft: number, starterSafe: any): number
    if type(starterSafe) ~= "number" or starterSafe ~= starterSafe then return safeLeft end
    return math.max(safeLeft, math.floor(starterSafe))
end
-- AUTO START (server): once per join, only for a starter whose dinosaur stands ready in the hub. `s`: enabled, starter, started, runState, attached.
function Rules.starterAutoStart(s: any): boolean
    if type(s) ~= "table" then return false end
    return s.enabled == true and s.starter == true and s.started ~= true and s.runState == "Sanctuary" and s.attached == true
end
-- STARTER CARD (client): once per run, when the starter has caught `cardEggs` eggs in a running run. `s`: starter, runState, eggs, shown, cardEggs.
function Rules.starterCardNow(s: any): boolean
    if type(s) ~= "table" or s.starter ~= true or s.shown == true or s.runState ~= "Active" then return false end
    return type(s.eggs) == "number" and type(s.cardEggs) == "number" and s.cardEggs >= 1 and s.eggs >= s.cardEggs
end
-- Run Complete of the starter run: OPEN EGGS is the only big button (when there are eggs to open; otherwise the usual Back home stays).
function Rules.starterOnlyOpenEggs(starter: any, hasEggs: any): boolean
    return starter == true and hasEggs == true
end
-- "Run again to find new dinos!" once, after the starter eggs were opened: nothing left to open and at least one new dinosaur beyond the starter Compy.
-- `s`: starter, settled (the starter run was settled this session), shown, eggsLeft, copies.
function Rules.starterRunAgainNow(s: any): boolean
    if type(s) ~= "table" or s.starter ~= true or s.settled ~= true or s.shown == true then return false end
    return type(s.eggsLeft) == "number" and s.eggsLeft <= 0 and type(s.copies) == "number" and s.copies > 1
end

return Rules
