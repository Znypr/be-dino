--!strict
-- BD-1199 (docs/239): pure rules of "Play again" and the gentle run streak, behind Config.PlayAgainEnabled. No services: the server
-- (RunStreakService) decides the streak and the bonus, the client (HatchSequence, RunComplete, PlayAgainCue) only shows them.
-- Calm feel (docs/87): no timer on screen, no countdown, no auto-start, nothing is ever "lost" - a streak that ends just starts at 1.
-- Every number lives in Config and is PROVISIONAL (RunStreakWindowSeconds, RunStreakCrystals, RunStreakMinRunSeconds).
local P = {}

P.MaxStreak = 5 -- the table in Config.RunStreakCrystals has five steps; a longer streak stays at 5
P.ButtonText = {play = "PLAY AGAIN", home = "HOME"} -- docs/72: two short words each, like DONE / TRY AGAIN
-- One big green primary button (48 px or more, the accent green of DONE) and one small grey one (still 48 px high: a thumb target).
P.Buttons = {
    play = {w = 300, h = 64, textSize = 34, fill = {93, 237, 31}},
    home = {w = 150, h = 48, textSize = 24, fill = {176, 181, 192}},
}
P.ButtonGap = 16
P.MinTouchHeight = 48

-- Which buttons the hatch end shows. `base` is what FtueP1.hatchButtons already says. Only the real end of a batch (nothing left, no splat)
-- changes, and only with the flag on; a splat keeps DONE / TRY AGAIN, an egg with more to come keeps NEXT EGG or the tap hint.
function P.endKinds(enabled: boolean, failed: boolean, remaining: number, base: {string}): {string}
    if enabled and not failed and remaining <= 0 then return {"play", "home"} end
    return base
end

-- Left edge of each button and the width of the whole row (kinds without a spec of their own keep the old 230 wide buttons, 16 apart).
function P.layout(kinds: {string}): ({number}, number)
    local xs: {number} = {}
    local x = 0
    for i, kind in kinds do
        local spec = (P.Buttons :: any)[kind]
        xs[i] = x
        x += (if spec then spec.w else 230) + P.ButtonGap
    end
    return xs, math.max(0, x - P.ButtonGap)
end

-- The streak of a run that is starting now. prev = the streak of the run before (0 = none), lastEndAt = when that run ended (server time),
-- startAt = now. A run inside the window continues the streak (capped), anything else starts again at 1. Bad numbers start at 1, never an error.
function P.nextStreak(prev: any, lastEndAt: any, startAt: any, window: any): number
    if typeof(prev) ~= "number" or typeof(lastEndAt) ~= "number" or typeof(startAt) ~= "number" or typeof(window) ~= "number" then return 1 end
    if prev ~= prev or lastEndAt ~= lastEndAt or startAt ~= startAt or window ~= window then return 1 end
    if prev < 1 then return 1 end
    local gap = startAt - lastEndAt
    if gap < 0 or gap > window then return 1 end
    return math.min(P.MaxStreak, math.floor(prev) + 1)
end

-- Crystals for a streak step, from the Config table. Anything unknown pays nothing.
function P.crystalsFor(streak: any, steps: any): number
    if typeof(streak) ~= "number" or streak ~= streak or typeof(steps) ~= "table" then return 0 end
    local step = math.clamp(math.floor(streak), 1, P.MaxStreak)
    local value = (steps :: any)[step]
    if typeof(value) ~= "number" or value ~= value or value < 0 then return 0 end
    return math.floor(value)
end

-- A run earns the streak bonus only when it was a real run (one or more eggs, at least minSeconds long): a run that ends at once pays nothing.
function P.qualifies(catchScore: any, runSeconds: any, minSeconds: any): boolean
    if typeof(catchScore) ~= "number" or typeof(runSeconds) ~= "number" or typeof(minSeconds) ~= "number" then return false end
    return catchScore >= 1 and runSeconds >= minSeconds
end

-- The soft line, from streak 2 on ("Run streak 1" would be no news). Calm words, never a warning.
function P.text(streak: any): string?
    if typeof(streak) ~= "number" or streak ~= streak or streak < 2 then return nil end
    return "Run streak " .. tostring(math.min(P.MaxStreak, math.floor(streak))) .. "!"
end

return P
