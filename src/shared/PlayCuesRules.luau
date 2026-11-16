--!strict
-- BD-1226 + BD-1231 + BD-1234 (docs/242 benchmark gaps 11, 15 and 19): the pure rules and the kid words of three small play cues, used ONLY while
-- Config.PlayCuesEnabled is on (playtest profile). No Roblox services and no Instances here: tools/verify_play_cues.py runs this file offline.
--   * Point at the thing (BD-1226): in a new player's first minutes a bobbing chip sits on the nearest food, on the nest when an egg is ready and on
--     a stall at home. Each marker goes away for the session once it was used (a bite, the nest opened, a stall opened) or after its time.
--   * Growth number pop (BD-1231): a "+N" rises at the dino when it eats (N = food points, never "+0.1"), and one short word banner when the SIZE bar
--     passes a quarter. Calm: a soft rise and fade, no shake; Reduce Motion = no rise, a short fade only.
--   * Egg ready (BD-1234): when a nest egg finishes during play, one toast "Your egg is ready!" and a number badge on the EGGS button. In game only:
--     Roblox experience notifications need Creator Hub setup on the owner's account (docs/160 s2), so they are not used.
-- Words follow docs/72: short, obvious, no "5m 0s", no "1.25x".
local Rules = {}

-- ---------------------------------------------------------------- point at the thing (BD-1226)
Rules.NewPlayerLevel = 2 -- an account at this level or lower is "new": the markers may show (StarterRun = 1 is new as well)
Rules.FoodBites = 3 -- the food marker goes away after this many bites in the session
Rules.FoodSeconds = 180 -- ... or after this many seconds of play (the first minutes)
Rules.StallSeconds = 120 -- the stall marker goes away after this many seconds at home, or when any stall opened
Rules.BobStuds = 0.6 -- the chip bobs this far up and down
Rules.BobSeconds = 1.1 -- one slow bob (calm; Reduce Motion: no bob)
Rules.Lift = 3 -- studs above the top of the food it points at
Rules.StationLift = 15 -- studs above a stall or nest prompt: over the stall awning and the big nest model (Studio 2026-11-16)
Rules.Words = table.freeze({food = "Eat me!", nest = "Eggs ready!", stall = "Shop!", potions = "Potions!"})
Rules.StallStations = table.freeze({"style", "potions"}) -- the stalls the stall marker may point at (HubSignCopy station ids)

-- Is this player new enough for the markers? level = AccountLevel (public attribute), starter = the owner-only StarterRun value.
function Rules.isNew(level: any, starter: any): boolean
    if starter == 1 then return true end
    return typeof(level) == "number" and level <= Rules.NewPlayerLevel
end

-- s: {new, runState, bites, played (seconds of run play this session)}
function Rules.foodOn(s: {new: boolean, runState: any, bites: number, played: number}): boolean
    return s.new and s.runState == "Active" and s.bites < Rules.FoodBites and s.played < Rules.FoodSeconds
end

-- s: {readyNests, runState, opened (the eggs screen was opened since this egg got ready)}. Any player: a ready egg is news for everyone, but only at home.
function Rules.nestOn(s: {readyNests: number, runState: any, opened: boolean}): boolean
    return s.readyNests > 0 and s.runState == "Sanctuary" and not s.opened
end

-- s: {new, runState, usedStall, home (seconds at home this session)}
function Rules.stallOn(s: {new: boolean, runState: any, usedStall: boolean, home: number}): boolean
    return s.new and s.runState == "Sanctuary" and not s.usedStall and s.home < Rules.StallSeconds
end

-- The chip's height offset at time t (seconds): a slow sine bob, 0 with Reduce Motion.
function Rules.bob(t: number, motion: boolean): number
    if not motion then return 0 end
    return math.sin(t * 2 * math.pi / Rules.BobSeconds) * Rules.BobStuds
end

-- The nearest of a list of {distance, clear} entries (index), or nil: an entry that is not in clear view (clear = false: off screen or under the
-- HUD rail) is never picked, so a chip never hides under the rail; it shows once the player turns toward a stall. Ties keep the first.
Rules.ClearLeft = 0.12 -- the left 12 % of the screen holds the rail (DINOS, EGGS, ...): a chip there would sit under it
Rules.ClearRight = 0.04 -- a small margin on the right edge
function Rules.nearest(list: {{distance: number, clear: boolean?}}): number?
    local best, bestD = nil, math.huge
    for i, item in list do
        if item.clear ~= false and item.distance < bestD then best, bestD = i, item.distance end
    end
    return best
end
-- Is a viewport point (x, on screen) in clear view on a screen `width` wide?
function Rules.inClearView(x: number, onScreen: boolean, width: number): boolean
    return onScreen and width > 0 and x >= width * Rules.ClearLeft and x <= width * (1 - Rules.ClearRight)
end

-- ---------------------------------------------------------------- growth number pop (BD-1231)
Rules.PopRise = 2.5 -- studs the "+N" rises (Reduce Motion: 0)
Rules.PopSeconds = 0.9 -- rise and fade
Rules.PopStillSeconds = 0.5 -- Reduce Motion: a short fade in place
Rules.MergeSeconds = 0.25 -- bites closer than this add up into one "+N" (no number storm)
Rules.MaxPops = 3 -- at most this many numbers in the air
Rules.BannerSeconds = 1.6
-- SIZE bar quarters (HudRules.barFill) and their word. One banner per quarter per run.
Rules.Milestones = table.freeze({
    {fill = 0.25, word = "Bigger!"},
    {fill = 0.5, word = "Big dino!"},
    {fill = 0.75, word = "Huge!"},
    {fill = 1, word = "Giant!"},
})

-- "+N" for a growth step. perFood = Config.GrowthPerFood. N is food points, rounded, at least 1. Bad input: nil (no pop).
function Rules.popText(delta: any, perFood: any): string?
    if typeof(delta) ~= "number" or delta ~= delta or delta <= 0 or delta == math.huge then return nil end
    if typeof(perFood) ~= "number" or perFood <= 0 then return nil end
    local n = math.max(1, math.floor(delta / perFood + 0.5))
    if n > 9999 then return "+9999" end
    return "+" .. tostring(n)
end

-- The milestone word crossed going from fill `before` to `after` (0..1), or nil. More than one crossed at once: the biggest.
function Rules.milestone(before: any, after: any): string?
    if typeof(before) ~= "number" or typeof(after) ~= "number" or after <= before then return nil end
    local word = nil
    for _, m in Rules.Milestones do
        if before < m.fill and after >= m.fill then word = m.word end
    end
    return word
end

-- How far the pop rises and how long it lives.
function Rules.popMotion(motion: boolean): (number, number)
    if motion then return Rules.PopRise, Rules.PopSeconds end
    return 0, Rules.PopStillSeconds
end

-- ---------------------------------------------------------------- egg ready (BD-1234)
Rules.ToastText = "Your egg is ready!"
Rules.ToastTwo = "%d eggs are ready!"
Rules.ToastBody = "Tap to open it"
Rules.ToastSeconds = 6
Rules.BadgeMax = 9 -- "9+" past this

-- How many projected nests (NestQueue.project results) are ready.
function Rules.readyCount(nests: any): number
    if typeof(nests) ~= "table" then return 0 end
    local n = 0
    for _, nest in nests do
        if typeof(nest) == "table" and nest.state == "ready" then n += 1 end
    end
    return n
end

-- Toast now? previous = the ready count last seen (nil = first reading after the join: the welcome-back card owns that moment, so no toast).
function Rules.toastNow(previous: number?, current: number): boolean
    return previous ~= nil and current > previous
end

function Rules.toastText(count: number): string
    if count <= 1 then return Rules.ToastText end
    return string.format(Rules.ToastTwo, math.min(count, Rules.BadgeMax))
end

-- The badge words on the EGGS button: "" (hidden) for 0, "1".."9", then "9+".
function Rules.badgeText(count: any): string
    if typeof(count) ~= "number" or count < 1 then return "" end
    if count > Rules.BadgeMax then return tostring(Rules.BadgeMax) .. "+" end
    return tostring(math.floor(count))
end

return Rules
