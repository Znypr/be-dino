--!strict
-- BD-073 (docs/66 sections 6-7): PURE objective rules. No Instances, services, remotes, clocks or profile access: every
-- function takes `now` (server unix seconds) and plain tables, so tools/verify_objectives.py runs this exact file.
-- ProfileRepository owns persistence (one UpdateAsync transaction per call); ObjectiveService owns the remote.
--
-- State = profile.objectives (ADDITIVE; absent until the first mutation while Config.ObjectivesEnabled is true; never written
-- when the flag is off):
--   {v = 1,
--    tutorial = {progress = {[id] = n}, claimed = {[id] = true}},
--    short / daily = {window = N, ids = {id,id,id}, progress = {n,n,n}, claimed = {bool,bool,bool},
--                     carry = {window = N-1, ids = {...}, claimed = {...}} or nil},   -- finished-unclaimed from the window before
--    earned = {day = D, crystals = n},   -- Short + Daily crystals claimed this UTC day (reward cap)
--    seen = {"egg:<outcomeId>", ...},    -- bounded ring of event ids already counted
--    flush = "<guid>"}                   -- id of the last applied event batch (idempotent retries)
-- PROVISIONAL numbers live in ObjectiveConfig. Rewards are Crystals/XP only, clamped here AND by the repository wallet.
local DefaultConfig = require(script.Parent.ObjectiveConfig)

local function whole(value: any, low: number, high: number): number?
    if type(value) ~= "number" or value ~= value or value % 1 ~= 0 or value < low or value > high then return nil end
    return value
end

local function clamped(value: any, low: number, high: number): number
    if type(value) ~= "number" or value ~= value then return low end
    return math.clamp(math.floor(value), low, high)
end

local function build(cfg: any)
    local Rules: any = {Config = cfg}
    local Groups = {"short", "daily"}

    local tutorialOrder: {string} = {}
    local pools: {[string]: {string}} = {short = {}, daily = {}}
    for _, entry in cfg.Catalogue do
        if entry.group == "tutorial" then table.insert(tutorialOrder, entry.id)
        elseif pools[entry.group] then table.insert(pools[entry.group], entry.id) end
    end
    Rules.TutorialOrder = tutorialOrder

    local function cap(entry: any): number
        return entry.goal * cfg.ProgressCapMultiplier
    end

    function Rules.windowNumber(group: string, now: number): number
        return math.floor(math.max(0, now) / cfg.Windows[group].seconds)
    end

    function Rules.windowEndsAt(group: string, window: number): number
        return (window + 1) * cfg.Windows[group].seconds
    end

    -- Deterministic roll of `active` distinct pool entries from the window number (same on every server, rejoin never rerolls).
    -- Park-Miller as in ProgressionRules.shopOffers; products stay below 2^53.
    function Rules.pick(group: string, window: number): {string}
        local setup = cfg.Windows[group]
        local pool = table.clone(pools[group])
        local state = (window * 16807 + setup.salt) % 2147483646 + 1
        local function nextUnit(): number
            state = (state * 48271) % 2147483647
            return state / 2147483647
        end
        for _ = 1, 6 do nextUnit() end
        local picked = {}
        for _ = 1, math.min(setup.active, #pool) do
            table.insert(picked, table.remove(pool, math.min(#pool, 1 + math.floor(nextUnit() * #pool))) :: string)
        end
        return picked
    end

    local function newGroup(group: string, window: number, carry: any)
        local ids = Rules.pick(group, window)
        local progress, claimed = {}, {}
        for i = 1, #ids do progress[i] = 0 claimed[i] = false end
        return {window = window, ids = ids, progress = progress, claimed = claimed, carry = carry}
    end

    function Rules.fresh()
        return {v = cfg.SchemaVersion, tutorial = {progress = {}, claimed = {}}, earned = {day = 0, crystals = 0}, seen = {}}
    end

    ---------------------------------------------------------------- migration / normalisation
    local function cleanGroup(group: string, raw: any): any
        if type(raw) ~= "table" or not whole(raw.window, 0, 2 ^ 31) or type(raw.ids) ~= "table" then return nil end
        local active = cfg.Windows[group].active
        local ids, progress, claimed = {}, {}, {}
        for i = 1, math.min(#raw.ids, active) do
            local id = raw.ids[i]
            local entry: any = if type(id) == "string" then cfg.ById[id] else nil
            if entry == nil or entry.group ~= group then return nil end -- a catalogue edit: roll the window afresh (progress is small)
            ids[i] = id
            progress[i] = clamped(if type(raw.progress) == "table" then raw.progress[i] else 0, 0, cap(entry))
            claimed[i] = type(raw.claimed) == "table" and raw.claimed[i] == true
        end
        if #ids == 0 then return nil end
        local out: any = {window = raw.window, ids = ids, progress = progress, claimed = claimed}
        local carry = raw.carry
        if type(carry) == "table" and whole(carry.window, 0, 2 ^ 31) and type(carry.ids) == "table" then
            local cids, cclaimed = {}, {}
            for i = 1, math.min(#carry.ids, active) do
                local id = carry.ids[i]
                local entry: any = if type(id) == "string" then cfg.ById[id] else nil
                if entry and entry.group == group then
                    table.insert(cids, id)
                    table.insert(cclaimed, type(carry.claimed) == "table" and carry.claimed[i] == true)
                end
            end
            if #cids > 0 then out.carry = {window = carry.window, ids = cids, claimed = cclaimed} end
        end
        return out
    end

    -- raw profile.objectives -> (normalised COPY, status). raw is never mutated.
    --   nil / corrupt     -> fresh state ("created"): a bad value in OUR OWN field must not lock a player out
    --   v > SchemaVersion -> nil, "newer_version": written by a newer build, we neither read nor touch it
    --   otherwise         -> field-by-field sanitised copy ("ok"); a well-formed state comes back equal to the input
    function Rules.load(raw: any): (any, string)
        if raw == nil then return Rules.fresh(), "created" end
        if type(raw) ~= "table" or type(raw.v) ~= "number" or raw.v ~= raw.v or raw.v % 1 ~= 0 or raw.v < 1 then
            return Rules.fresh(), "created"
        end
        if raw.v > cfg.SchemaVersion then return nil, "newer_version" end
        local state = Rules.fresh()
        local tutorial = raw.tutorial
        if type(tutorial) == "table" then
            for _, id in tutorialOrder do
                local entry = cfg.ById[id]
                if type(tutorial.claimed) == "table" and tutorial.claimed[id] == true then state.tutorial.claimed[id] = true end
                local count = if type(tutorial.progress) == "table" then tutorial.progress[id] else nil
                if type(count) == "number" and count == count and count > 0 then state.tutorial.progress[id] = clamped(count, 0, cap(entry)) end
            end
        end
        for _, group in Groups do state[group] = cleanGroup(group, raw[group]) end
        if type(raw.flush) == "string" and #raw.flush >= 1 and #raw.flush <= 80 then state.flush = raw.flush end
        local earned = raw.earned
        if type(earned) == "table" then
            state.earned = {day = clamped(earned.day, 0, 2 ^ 31), crystals = clamped(earned.crystals, 0, 2000000000)}
        end
        if type(raw.seen) == "table" then
            for i = math.max(1, #raw.seen - cfg.SeenMax + 1), #raw.seen do
                local id = raw.seen[i]
                if type(id) == "string" and #id >= 1 and #id <= 80 then table.insert(state.seen, id) end
            end
        end
        return state, "ok"
    end

    ---------------------------------------------------------------- windows
    local function pendingCarry(g: any): any
        local ids, claimed = {}, {}
        for i, id in g.ids do
            local entry = cfg.ById[id]
            if not g.claimed[i] and g.progress[i] >= entry.goal then
                table.insert(ids, id)
                table.insert(claimed, false)
            end
        end
        if #ids == 0 then return nil end
        return {window = g.window, ids = ids, claimed = claimed}
    end

    -- Server-clock rollover (mutates `state`). A group whose stored window is AHEAD of the clock is left alone (clock moved
    -- backwards: never wipe progress). Exactly one window old: finished-but-unclaimed rows carry over for one window; any
    -- older window is dropped (docs/66: "no backlog guilt").
    function Rules.advance(state: any, now: number)
        for _, group in Groups do
            local window = Rules.windowNumber(group, now)
            local g = state[group]
            if g == nil then
                state[group] = newGroup(group, window, nil)
            elseif g.window < window then
                state[group] = newGroup(group, window, if window - g.window == 1 then pendingCarry(g) else nil)
            end
        end
        local day = Rules.windowNumber("daily", now)
        if state.earned.day < day then state.earned = {day = day, crystals = 0} end
    end

    ---------------------------------------------------------------- events
    -- Sanitise one gameplay event. kind must be a known EventKinds entry; amount a whole number 1..100000 (default 1);
    -- id (optional) a bounded string used for replay protection; value (optional) a finite number for minValue objectives.
    function Rules.cleanEvent(event: any): any
        if type(event) ~= "table" or type(event.kind) ~= "string" or cfg.EventKinds[event.kind] ~= true then return nil end
        local amount = if event.amount == nil then 1 else whole(event.amount, 1, 100000)
        if amount == nil then return nil end
        local id = event.id
        if id ~= nil and (type(id) ~= "string" or #id < 1 or #id > 80) then return nil end
        local value = event.value
        if value ~= nil and (type(value) ~= "number" or value ~= value or math.abs(value) > 1e9) then return nil end
        return {kind = event.kind, amount = amount, id = id, value = value}
    end

    -- Memory-only server queue: id-less events of one kind merge (amounts add, value keeps the max). Bounded by PendingMax.
    function Rules.queue(pending: {any}, event: any): boolean
        local clean = Rules.cleanEvent(event)
        if clean == nil then return false end
        if clean.id == nil then
            for _, queued in pending do
                if queued.id == nil and queued.kind == clean.kind then
                    queued.amount = math.min(100000, queued.amount + clean.amount)
                    if clean.value ~= nil then queued.value = math.max(queued.value or clean.value, clean.value) end
                    return true
                end
            end
        end
        if #pending >= cfg.PendingMax then return false end
        table.insert(pending, clean)
        return true
    end

    -- OB1 (docs/115): does a settled run count for the run objectives (T2, S3, D2)? It must have lasted at least RunMinSeconds and
    -- eaten at least RunMinFood. Both numbers come from the server (run clock, food ticks), never from the client.
    function Rules.runCounts(runSeconds: any, foodEaten: any): boolean
        if type(runSeconds) ~= "number" or runSeconds ~= runSeconds or runSeconds < cfg.RunMinSeconds then return false end
        if type(foodEaten) ~= "number" or foodEaten ~= foodEaten or foodEaten < cfg.RunMinFood then return false end
        return true
    end

    -- OB2 (docs/115): a "seen" report ("the player opened the menu") is accepted only for a catalogue row that declares it
    -- (`seen = "<id>"`, today T9 "fusion_menu"). Returns the catalogue entry or nil (a forged id is refused).
    local seenEntries: {[string]: any} = {}
    for _, entry in cfg.Catalogue do
        if entry.seen ~= nil and entry.group == "tutorial" then seenEntries[entry.seen] = entry end
    end
    function Rules.seenEntry(seenId: any): any
        if type(seenId) ~= "string" then return nil end
        return seenEntries[seenId]
    end
    -- Event id used for the report: it makes a repeat count once while it is in the bounded `seen` ring.
    function Rules.seenEventId(seenId: string): string
        return "seen:" .. seenId
    end

    local function bump(entry: any, current: number, amount: number, value: any): number
        -- BD-1041: a `total` row takes the event's value as the running total (the highest wins). Nothing adds up, so a replay is harmless.
        if entry.total == true then
            if type(value) ~= "number" or value ~= value or value < 0 then return current end
            return math.max(current, math.min(cap(entry), math.floor(value)))
        end
        if entry.minValue ~= nil and (type(value) ~= "number" or value < entry.minValue) then return current end
        return math.min(cap(entry), current + amount)
    end

    -- Applies events to `state` (mutates). Replayed ids count once; counters cap at ProgressCapMultiplier x goal.
    -- Returns how many events were counted (replays and junk are not).
    function Rules.applyEvents(state: any, events: {any}, now: number): number
        Rules.advance(state, now)
        local counted = 0
        for _, raw in events do
            local event = Rules.cleanEvent(raw)
            if event == nil then continue end
            if event.id ~= nil then
                if table.find(state.seen, event.id) ~= nil then continue end
                table.insert(state.seen, event.id)
                while #state.seen > cfg.SeenMax do table.remove(state.seen, 1) end
            end
            counted += 1
            for _, id in tutorialOrder do
                local entry = cfg.ById[id]
                if entry.event == event.kind and not state.tutorial.claimed[id] then
                    state.tutorial.progress[id] = bump(entry, state.tutorial.progress[id] or 0, event.amount, event.value)
                end
            end
            for _, group in Groups do
                local g = state[group]
                for i, id in g.ids do
                    local entry = cfg.ById[id]
                    if entry.event == event.kind and not g.claimed[i] then
                        g.progress[i] = bump(entry, g.progress[i], event.amount, event.value)
                    end
                end
            end
        end
        return counted
    end

    ---------------------------------------------------------------- claim
    local function rewardOf(entry: any): (number, number)
        local reward = entry.reward or {}
        return clamped(reward.crystals, 0, cfg.MaxClaimCrystals), clamped(reward.xp, 0, cfg.MaxClaimXP)
    end

    -- Claim objective `id` (mutates state and, when given, wallet = {crystals, accountXP}). Server-authoritative: the id is the
    -- only client input. Statuses: claimed | claimed_capped | already_claimed | not_done | not_active | unknown_objective.
    -- Returns ok, status, grant ({crystals, xp} actually granted).
    function Rules.claim(state: any, id: any, now: number, wallet: any, maxCrystals: number?): (boolean, string, any)
        local entry: any = if type(id) == "string" then cfg.ById[id] else nil
        if entry == nil then return false, "unknown_objective", nil end
        Rules.advance(state, now)
        local markSlot: any, markIndex = nil, 0 -- where to flip `claimed` once the reward is settled
        local claimable = false
        local found, claimedBefore = false, false
        local windowed = entry.group ~= "tutorial"
        if not windowed then
            found = true
            if state.tutorial.claimed[id] then claimedBefore = true
            elseif (state.tutorial.progress[id] or 0) >= entry.goal then
                claimable = true
            end
        else
            local g = state[entry.group]
            for _, slot in {g, g.carry} do
                if slot == nil then continue end
                for i, slotId in slot.ids do
                    if slotId ~= id then continue end
                    found = true
                    local progress = if slot == g then g.progress[i] else entry.goal -- a carry row is finished by construction
                    if slot.claimed[i] then claimedBefore = true
                    elseif progress >= entry.goal and not claimable then
                        claimable, markSlot, markIndex = true, slot, i
                    end
                end
            end
        end
        if not found then return false, "not_active", nil end
        if not claimable then return false, if claimedBefore then "already_claimed" else "not_done", nil end
        local crystals, xp = rewardOf(entry)
        local status = "claimed"
        if windowed then
            local left = math.max(0, cfg.WindowCrystalCapPerDay - state.earned.crystals)
            if crystals > left then crystals = left status = "claimed_capped" end
            state.earned.crystals += crystals
        end
        if markSlot ~= nil then markSlot.claimed[markIndex] = true else state.tutorial.claimed[id] = true end
        if wallet ~= nil then
            wallet.crystals = math.min(maxCrystals or 2000000000, (wallet.crystals or 0) + crystals)
            if xp > 0 then wallet.accountXP = math.min(2000000000, (wallet.accountXP or 0) + xp) end
        end
        return true, status, {crystals = crystals, xp = xp}
    end

    ---------------------------------------------------------------- profile helpers (transaction bodies)
    -- Normalise profile.objectives, apply events, store the result back. Returns ok, status. Never throws on bad data; a newer
    -- stored version is left byte-identical. On any failure the profile is unchanged.
    -- batchId (optional) makes a batch idempotent: the id of the LAST applied batch is stored (state.flush), so a transaction that
    -- Roblox retries after a lost acknowledgement cannot count the same id-less events twice. Returns ok, status
    -- (created | ok | duplicate | newer_version).
    function Rules.applyToProfile(profile: any, events: {any}, now: number, batchId: string?): (boolean, string)
        local state, status = Rules.load(profile.objectives)
        if state == nil then return false, status end
        if batchId ~= nil and state.flush == batchId then return true, "duplicate" end
        Rules.applyEvents(state, events, now)
        if batchId ~= nil and #batchId >= 1 and #batchId <= 80 then state.flush = batchId end
        profile.objectives = state
        return true, status
    end

    -- Events first, then the claim, in ONE state copy: the profile is only written when the claim succeeds.
    function Rules.claimOnProfile(profile: any, wallet: any, id: any, events: {any}, now: number, maxCrystals: number?): (boolean, string, any)
        local state, status = Rules.load(profile.objectives)
        if state == nil then return false, status, nil end
        Rules.applyEvents(state, events, now)
        local ok, claimStatus, grant = Rules.claim(state, id, now, wallet, maxCrystals)
        if not ok then return false, claimStatus, nil end
        profile.objectives = state
        return true, claimStatus, grant
    end

    ---------------------------------------------------------------- read-only view for the UI (BD-075)
    local function row(entry: any, progress: number, claimed: boolean, carried: boolean)
        local crystals, xp = rewardOf(entry)
        return {id = entry.id, name = entry.name, note = entry.note, progress = math.min(progress, entry.goal), goal = entry.goal,
            reward = {crystals = crystals, xp = xp}, done = progress >= entry.goal, claimed = claimed, carried = carried}
    end

    -- Never mutates `raw`. Returns nil, status when the stored value is from a newer build.
    function Rules.view(raw: any, now: number, pending: {any}?): (any, string)
        local state, status = Rules.load(raw)
        if state == nil then return nil, status end
        Rules.applyEvents(state, pending or {}, now)
        local view: any = {tutorial = nil, tutorialDone = true, short = {}, daily = {}, carry = {}}
        for _, id in tutorialOrder do
            if not state.tutorial.claimed[id] then
                view.tutorialDone = false
                view.tutorial = row(cfg.ById[id], state.tutorial.progress[id] or 0, false, false)
                break
            end
        end
        for _, group in Groups do
            local g = state[group]
            for i, id in g.ids do table.insert(view[group], row(cfg.ById[id], g.progress[i], g.claimed[i], false)) end
            if g.carry then
                for i, id in g.carry.ids do
                    if not g.carry.claimed[i] then table.insert(view.carry, row(cfg.ById[id], cfg.ById[id].goal, false, true)) end
                end
            end
            view[group .. "ResetsIn"] = math.max(0, Rules.windowEndsAt(group, g.window) - now)
        end
        view.crystalsLeftToday = math.max(0, cfg.WindowCrystalCapPerDay - state.earned.crystals)
        return view, "ok"
    end

    -- OB2: has this seen-objective already been reported (or claimed)? Read-only; pending = the unflushed queue. A repeat report is
    -- "already_seen" and queues nothing, so the report counts at most once per profile. Returns done, status.
    function Rules.seenDone(raw: any, seenId: any, now: number, pending: {any}?): (boolean, string)
        local entry = Rules.seenEntry(seenId)
        if entry == nil then return false, "unknown_objective" end
        local state, status = Rules.load(raw)
        if state == nil then return false, status end
        Rules.applyEvents(state, pending or {}, now)
        return state.tutorial.claimed[entry.id] == true or (state.tutorial.progress[entry.id] or 0) >= entry.goal, "ok"
    end

    return Rules
end

local Default = build(DefaultConfig)
Default.with = build -- tests inject a synthetic catalogue
return Default
