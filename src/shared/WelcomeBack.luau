--!strict
-- BD-1168 (docs/221 section 3 and 4): the welcome-back moment. When a player joins and one or more egg nests finished while they
-- were away, the session opens with ONE happy card: "Your nest is ready!" / "2 nests are ready!". Pure rules, no services: the
-- server decides the number (nest timers are server time, WelcomeBackService), the client only shows it (WelcomeBackCue).
-- Behind Config.WelcomeBackEnabled. Nothing is stored: the number comes from the nest states the save already holds.
local W = {}

W.MaxNests = 50 -- the structural ceiling of a stored nest list (ProfileRepository.isValidProfile)
W.Body = "Welcome back! Tap to open" -- docs/72: one short line, no rule text
W.Seconds = 8 -- the card stays a little longer than a normal big-moment card (4.5 s) so a child can read and tap it
W.Sound = "level_up" -- the registered soft reward cue a nest already uses when it opens (docs/71); no new sound
W.WorldWaitSeconds = 20 -- show it anyway when the world-ready signal never comes (Config.WorldReadyTimeoutSeconds)

-- How many nests in a list are ready to open. A broken list counts as none.
function W.readyCount(list: any): number
    if typeof(list) ~= "table" then return 0 end
    local count = 0
    for _, nest in list do
        if typeof(nest) == "table" and nest.state == "ready" then count += 1 end
    end
    return count
end

-- The server rule. readyBefore = ready nests in the save as it was stored (the state when the player was last here);
-- readyAfter = ready nests after the queue moved forward to the join time. The difference finished while the player was away.
-- A brand-new save never gets the card (its first session), and a nest that was ready and left unopened is not counted again.
function W.finishedAway(isNew: any, readyBefore: any, readyAfter: any): number
    if isNew ~= false then return 0 end
    if typeof(readyBefore) ~= "number" or typeof(readyAfter) ~= "number" then return 0 end
    if readyBefore ~= readyBefore or readyAfter ~= readyAfter then return 0 end -- NaN
    local count = math.floor(readyAfter) - math.floor(readyBefore)
    return math.clamp(count, 0, W.MaxNests)
end

-- The big line. Children: short, obvious, one number at most.
function W.title(count: number): string
    if count <= 1 then return "Your nest is ready!" end
    return string.format("%d nests are ready!", count)
end

-- The toast card for `count` finished nests, or nil when there is nothing to say (the client then shows nothing).
function W.card(count: any): any?
    if typeof(count) ~= "number" or count ~= count or count < 1 then return nil end
    local n = math.min(math.floor(count), W.MaxNests)
    return {text = W.title(n), body = W.Body, kind = "major", key = "welcome_back", icon = "egg_nest", seconds = W.Seconds}
end

-- The client rule: show the card now? s = {shown, count, worldReady, waited, runState}. Once per join; never in a run (the card's
-- tap opens the Nests screen, which is a home screen); waits for the world (the loading screen) or WorldWaitSeconds.
function W.showNow(s: any): boolean
    if s.shown == true or W.card(s.count) == nil then return false end
    if not W.canOpen(s.runState) then return false end
    return s.worldReady == true or (typeof(s.waited) == "number" and s.waited >= W.WorldWaitSeconds)
end

-- May the tap open the Nests screen? Not during a run (the home screens are closed there).
function W.canOpen(runState: any): boolean
    return runState ~= "Active" and runState ~= "Ending"
end

return W
