--!strict
-- First-time-player rules (docs/112, BD-365..368). Pure: no Instances, services or remotes. Tested by tools/verify_ftue_*.py.
-- Nothing here changes an economy number. It only (a) keeps the first eggs of a brand-new profile from being Cracked,
-- (b) decides when the calm first-run hint shows, and (c) when the left menu collapses on a first run.
local Rules = {}

-- BD-365 (lead decision 2026-10-16): the first SafeEggs eggs a new profile gets are never Cracked ("safe"). After that the
-- normal Cracked odds apply (owner target 50% at tier 0, docs/09). Derived from existing data: no new persistent field.
Rules.SafeEggs = 2
Rules.SafeEggsLine = "Your first 2 eggs are safe: they are never Cracked."

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
Rules.GoCueText = "TAP TO GO!"
function Rules.goCueShown(state: any): boolean
    if type(state) ~= "table" then return false end
    return state.runState == "Sanctuary" and state.runStarted ~= true and state.hasFoundEgg ~= true and state.menuOpen ~= true
end

return Rules
