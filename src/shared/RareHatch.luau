--!strict
-- BD-428 (owner 2026-10-16): a rare hatch is a HUGE celebration for the hatcher and a short announcement for everyone.
-- Pure rules, no Roblox services, so tests drive them with a fake clock. The SERVER decides from the settled hatch outcome
-- (ProfileRepository.publishHatch -> RareHatchService); the client only draws what it is told.
-- Rare = a Legendary species (tier 5), a Shiny, an event mutation, or (BD-606, docs/115 SS9, only while Config.SecretSpeciesEnabled) a SECRET species.
-- A Cracked (failed) egg is never rare.
-- Announcements are rate limited: eggs of one hatcher are coalesced for Window seconds and only the BEST one is announced,
-- then that hatcher is quiet for Cooldown seconds (a 15-egg reveal takes about 75 s); the whole server has a small global cap.
local R = {}

R.LegendaryTier = 5
R.Window = 3 -- seconds: rare eggs inside one window collapse into the best one
R.Cooldown = 45 -- seconds a hatcher stays quiet after an announcement
R.GlobalMax = 4 -- announcements per GlobalWindow seconds across the whole server
R.GlobalWindow = 10
R.MaxName = 20 -- display names are cut to this many characters
R.SecretScore = 4 -- a secret ranks with a Legendary when one window holds several rare eggs (docs/115 SS9)
R.Celebrate = table.freeze({gap = 4}) -- the hatcher's own celebrations are at least this many seconds apart (client)

-- score: higher is better. Legendary + Shiny beats Shiny beats Legendary beats a mutation alone.
-- `secret` (BD-606) is true only when the caller (RareHatchService) saw a secret species AND the flag is on; the default (nil/false) is exactly the old rule.
function R.classify(outcome: any, speciesRarity: number?, secret: boolean?): {kind: string, score: number, shiny: boolean, legendary: boolean, mutation: boolean, secret: boolean}?
    if type(outcome) ~= "table" or outcome.failed == true then return nil end
    local shiny = outcome.shiny == true
    local legendary = (speciesRarity or 0) >= R.LegendaryTier
    local mutation = type(outcome.eventMutationId) == "string" and outcome.eventMutationId ~= ""
    local isSecret = secret == true
    if not (shiny or legendary or mutation or isSecret) then return nil end
    local score = (if legendary then 4 else 0) + (if shiny then 5 else 0) + (if mutation then 2 else 0) + (if isSecret then R.SecretScore else 0)
    local kind = if isSecret then "secret" elseif shiny then "shiny" elseif legendary then "legendary" else "mutation"
    return {kind = kind, score = score, shiny = shiny, legendary = legendary, mutation = mutation, secret = isSecret}
end

-- Display names come from Roblox (already filtered by Roblox); still drop control characters and cut the length.
function R.cleanName(name: any): string
    local s = if type(name) == "string" then name else ""
    s = string.gsub(s, "[%c]", "")
    s = string.gsub(s, "^%s+", "")
    s = string.gsub(s, "%s+$", "")
    if #s > R.MaxName then s = string.sub(s, 1, R.MaxName) end
    if s == "" then s = "A player" end
    return s
end

-- Short kid-friendly text. speciesName is the display name ("T-Rex"). Example: "Sam hatched a Shiny T-Rex!"
function R.text(playerName: string, info: {shiny: boolean, legendary: boolean, mutation: boolean, secret: boolean?}, speciesName: string): string
    -- BD-606 (SS9): a secret is announced calmly and WITHOUT its name: the other players only learn that someone found one
    if info.secret == true then return string.format("%s found a secret dino!", R.cleanName(playerName)) end
    local label = if info.shiny then "Shiny " elseif info.mutation then "Mutant " elseif info.legendary then "Legendary " else ""
    return string.format("%s hatched a %s%s!", R.cleanName(playerName), label, speciesName)
end

-- Own celebration line.
function R.ownText(info: {shiny: boolean, legendary: boolean, mutation: boolean, secret: boolean?}, speciesName: string): string
    local label = if info.shiny then "Shiny " elseif info.mutation then "Mutant " elseif info.legendary then "Legendary " else ""
    if info.secret == true then return string.format("Secret find! You hatched a %s%s!", label, speciesName) end
    return string.format("You hatched a %s%s!", label, speciesName)
end

-- Client plan: how big the celebration is for the Effects setting (full / lite / off) and Reduce Motion (calm).
-- Off and Calm keep a banner and the sound but no confetti; Lite draws fewer pieces. Counts are capped for phones.
-- BD-430 / BD-433: `pop` = how many star pops (the starPop Blender flipbook) flank the own banner: two at Full, one at Lite, none at Off or
-- Calm. The client draws them ONLY while the starPop slot holds a real upload, so an empty slot keeps exactly the banner and confetti.
R.Confetti = table.freeze({full = 36, lite = 14, off = 0})
R.Pop = table.freeze({full = 2, lite = 1, off = 0})
R.PopLife = 0.9 -- seconds one star pop plays (16 frames, played once)
R.PopSize = 64 -- px
-- BD-433 (docs/123 s2 T8): ONE soft light sweep across the OWN rare banner, Full only (Lite: banner only, Off none, Reduce Motion none: it moves).
-- The client draws it ONLY while the shaftGradient Blender slot holds a real upload (the gradient is turned on its side and slid across), so an
-- empty slot keeps exactly today's banner.
R.Sweep = table.freeze({full = 1, lite = 0, off = 0})
R.SweepLife = 0.9 -- seconds for one pass
R.SweepAlpha = 0.45 -- peak opacity of the band, soft
R.SweepWidth = 0.35 -- band length as a share of the banner width
function R.plan(effects: string, calm: boolean, kind: string): {confetti: number, banner: boolean, sound: string, pop: number, sweep: number}
    local n = R.Confetti[effects]
    if n == nil then n = R.Confetti.full end
    local pop = R.Pop[effects]
    if pop == nil then pop = R.Pop.full end
    local sweep = R.Sweep[effects]
    if sweep == nil then sweep = R.Sweep.full end
    if calm then n, pop, sweep = 0, 0, 0 end
    -- BD-606 (SS9): a secret find is a calm banner only: no confetti, star pops or light sweep at ANY Effects setting, and no extra sound (the reveal
    -- already plays the calm Legendary sting), so Reduce Motion and Effects Off look exactly the same as Full.
    if kind == "secret" then return {confetti = 0, banner = true, sound = "", pop = 0, sweep = 0} end
    return {confetti = n, banner = true, sound = "shiny_bang", pop = pop, sweep = sweep}
end
-- Pure: one sweep pass at `age` seconds -> (centre 0..1 across the banner, opacity 0..SweepAlpha). Eases in and out of both ends, soft at the
-- edges, and is gone (opacity 0) once age >= SweepLife.
function R.sweepAt(age: number): (number, number)
    local t = math.clamp(age / R.SweepLife, 0, 1)
    local eased = t * t * (3 - 2 * t)
    local alpha = R.SweepAlpha * math.sin(math.pi * t) ^ 0.8
    if t >= 1 then alpha = 0 end
    return eased, alpha
end

-- BD-1121 (docs/202 R6, flag Config.RareFindBannerEnabled): the announcement other players see, as TWO lines and no panel:
--   a huge outlined title "RARE FIND!" ("SECRET FIND!" for a secret) and one sentence "A Legendary Compy was found!" with the rarity word in its colour.
-- NO player name (the old strip said "Sam hatched ..."); a secret keeps its species name out of it, as before (BD-606 SS9). The rate limits above are untouched: this only
-- changes the words and the look. The server sends the tier number and the species display name next to the old text; the client validates them again.
R.FindTitle = "RARE FIND!"
R.SecretFindTitle = "SECRET FIND!"
R.MaxSpecies = 24 -- letters, digits, spaces, - ' . only (a species display name)
R.FindKinds = table.freeze({legendary = true, shiny = true, mutation = true, secret = true})
R.FindFade = table.freeze({fadeIn = 0.3, hold = 3.6, fadeOut = 0.6}) -- seconds; Reduce Motion: no fades, the same hold

function R.findTitle(kind: any): string
    return if kind == "secret" then R.SecretFindTitle else R.FindTitle
end

-- "A Legendary Compy was found!", "An Epic Shiny Mutant Raptor was found!", "A secret dino was found!". tierName and speciesName are plain words (RarityWord colours the tier).
function R.findLine(info: {kind: any?, shiny: boolean?, mutation: boolean?, secret: boolean?}, tierName: string?, speciesName: string?): string?
    if info.secret == true or info.kind == "secret" then return "A secret dino was found!" end
    if type(tierName) ~= "string" or type(speciesName) ~= "string" or tierName == "" or speciesName == "" then return nil end
    local article = if string.find(tierName, "^[AEIOUaeiou]") then "An" else "A"
    local mods = (if info.shiny == true then " Shiny" else "") .. (if info.mutation == true then " Mutant" else "")
    return string.format("%s %s%s %s was found!", article, tierName, mods, speciesName)
end

-- The fades for the Reduce Motion setting (calm = true): no fade, the same time on screen.
function R.findPlan(calm: boolean): {fadeIn: number, hold: number, fadeOut: number}
    if calm then return {fadeIn = 0, hold = R.FindFade.hold, fadeOut = 0} end
    return {fadeIn = R.FindFade.fadeIn, hold = R.FindFade.hold, fadeOut = R.FindFade.fadeOut}
end

-- The client checks what the server sent: a known kind, a tier number that exists, a clean species name. Anything else -> nil (the client then shows the old text banner).
-- tierNames = the tier words by rank (RarityWord.Names). Returns {title, line}.
function R.findFromPayload(data: any, tierNames: {string}): {title: string, line: string}?
    if type(data) ~= "table" or type(data.kind) ~= "string" or R.FindKinds[data.kind] ~= true then return nil end
    local info = {kind = data.kind, shiny = data.shiny == true, mutation = data.mutation == true, secret = data.kind == "secret"}
    local tierName: string? = nil
    local species: string? = nil
    if data.kind ~= "secret" then
        local tier = data.tier
        if type(tier) ~= "number" or tier ~= math.floor(tier) or tier < 1 or tier > #tierNames then return nil end
        tierName = tierNames[tier]
        local name = data.species
        if type(name) ~= "string" or #name < 1 or #name > R.MaxSpecies or not string.find(name, "^[%w][%w %-'%.]*$") then return nil end
        species = name
    end
    local line = R.findLine(info, tierName, species)
    if line == nil then return nil end
    return {title = R.findTitle(data.kind), line = line}
end

export type State = {
    pending: {[number]: {score: number, info: any, text: string, flushAt: number}},
    quietUntil: {[number]: number},
    seen: {[string]: boolean},
    seenCount: number,
    sent: {number},
    stats: {offered: number, announced: number, merged: number, dropped: number},
}

function R.newState(): State
    return {pending = {}, quietUntil = {}, seen = {}, seenCount = 0, sent = {}, stats = {offered = 0, announced = 0, merged = 0, dropped = 0}}
end

-- A hatcher offers a rare egg. Returns the flush time (seconds, clock) when a NEW window opened (the caller schedules flush at
-- that time), or nil when the egg merged into an open window or was dropped (duplicate egg id, hatcher is quiet).
function R.offer(state: State, userId: number, eggId: string, info: any, text: string, now: number): number?
    state.stats.offered += 1
    if state.seen[eggId] then state.stats.dropped += 1 return nil end
    if state.seenCount > 400 then state.seen = {} state.seenCount = 0 end
    state.seen[eggId] = true
    state.seenCount += 1
    local open = state.pending[userId]
    if open then
        state.stats.merged += 1
        if info.score > open.score then open.score = info.score open.info = info open.text = text end
        return nil
    end
    if (state.quietUntil[userId] or 0) > now then state.stats.dropped += 1 return nil end
    state.pending[userId] = {score = info.score, info = info, text = text, flushAt = now + R.Window}
    return now + R.Window
end

-- Close the hatcher's window. Returns {text, info} to announce, or nil (global cap, or nothing pending).
function R.flush(state: State, userId: number, now: number): {text: string, info: any}?
    local open = state.pending[userId]
    state.pending[userId] = nil
    if not open then return nil end
    local keep = {}
    for _, t in state.sent do if now - t < R.GlobalWindow then table.insert(keep, t) end end
    state.sent = keep
    if #keep >= R.GlobalMax then state.stats.dropped += 1 return nil end
    table.insert(state.sent, now)
    state.quietUntil[userId] = now + R.Cooldown
    state.stats.announced += 1
    return {text = open.text, info = open.info}
end

function R.forget(state: State, userId: number)
    state.pending[userId] = nil
    state.quietUntil[userId] = nil
end

return R
