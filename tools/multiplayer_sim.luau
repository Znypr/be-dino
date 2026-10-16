-- BD-354 / BD-319 prep: 12-player offline simulation body. Appended by tools/verify_multiplayer_sim.py after the
-- verify_load scheduler / DataStore mock (virtual clock, cooperative coroutines, UpdateAsync budget and latency).
-- It runs the REAL ProfileRepository, RunLifecycle, LeaveCoordinator, RewardMath, CombatRules, NestQueue unmodified.
-- It proves ordering/transaction/invariant behaviour. It does NOT prove Roblox networking, physics, replication or real
-- DataStore behaviour (see docs/111 section 6 for what only a real server can show).

math.randomseed(20261016) -- the retry back-off jitter uses math.random; a fixed seed keeps the sim reproducible
local CHECKS = {}
local currentScenario = "?"
local function check(name, cond, detail)
    table.insert(CHECKS, {scenario = currentScenario, name = name, ok = cond == true, detail = detail or ""})
end
local function metric(name, value) print(string.format("METRIC|%s|%s|%s", currentScenario, name, tostring(value))) end

-------------------------------------------------------------------- engine mocks (per server)
local function signal()
    local s = {fns = {}}
    function s:Connect(f) table.insert(self.fns, f) return {Disconnect = function() end} end
    return s
end

local function installMocks(server)
    server.PlayersService = {PlayerAdded = signal(), PlayerRemoving = signal(), GetPlayers = function() return table.clone(server.players) end}
    server.workspace = {GetServerTimeNow = function() return 1.7e9 + now end, GetAttribute = function() return nil end,
        SetAttribute = function() end}
    server.Instance = {new = function(className)
        local o = {ClassName = className, Name = className, OnServerEvent = signal(), children = {}}
        function o:FindFirstChild(n) return self.children[n] end
        function o:Destroy() end
        function o:IsA(c) return c == className end
        return setmetatable(o, {__newindex = function(t, k, v)
            rawset(t, k, v)
            if k == "Parent" and type(v) == "table" and rawget(v, "children") then v.children[t.Name] = t end
        end})
    end}
end

local function newChar(owner)
    local c = {attrs = {}, Parent = true, Name = owner.Name}
    function c:SetAttribute(k, v) self.attrs[k] = v end
    function c:GetAttribute(k) return self.attrs[k] end
    local humanoid = setmetatable({Died = signal(), Parent = c, _health = 100}, {
        __index = function(t, k) if k == "Health" then return rawget(t, "_health") end end,
        __newindex = function(t, k, v)
            if k == "Health" then
                rawset(t, "_health", v)
                if v <= 0 then for _, f in t.Died.fns do task.spawn(f) end end -- real Humanoid.Died fires on Health = 0
            else rawset(t, k, v) end
        end})
    c.humanoid = humanoid
    function c:FindFirstChildOfClass(cls) if cls == "Humanoid" then return humanoid end return nil end
    function c:WaitForChild() return humanoid end
    return c
end

local function mockPlayer(server, userId)
    local p = {UserId = userId, Name = "P" .. userId, Parent = true, attrs = {}, respawns = 0}
    function p:SetAttribute(k, v) self.attrs[k] = v end
    function p:GetAttribute(k) return self.attrs[k] end
    function p:LoadCharacterAsync() self.respawns += 1 self.Character = newChar(self) self.Character:SetAttribute("RunState", "Sanctuary") end
    return p
end

-------------------------------------------------------------------- server boot (mirrors Bootstrap.server.luau wiring)
local function boot(server)
    installMocks(server)
    local Repo = server.Repository
    local RL = server.require(node("src/server/RunLifecycle"))
    local LC = server.require(node("src/server/LeaveCoordinator"))
    local PS = server.require(node("src/server/PrivateState")) -- BD-360: owner-only values live here, not in p.attrs
    local env = {server = server, RL = RL, Repo = Repo, PS = PS, settleCalls = {}, runs = {}, committed = {}, released = {}}
    local leaving = LC.new({endForDisconnect = RL.endForDisconnect,
        release = function(p) env.released[p] = true return Repo.release(p) end, publish = nil})
    env.leaving = leaving
    RL.configureSettlement(function(player, runId, catchScore, reason, eggEvents, runSeconds)
        env.settleCalls[runId] = (env.settleCalls[runId] or 0) + 1
        local ok, outcome, status = Repo.commitRunSettlement(player, runId, catchScore, eggEvents, runSeconds, nil)
        if ok then env.committed[runId] = {userId = player.UserId, catch = catchScore, outcome = outcome, status = status} end
        leaving.settlementFinished(player)
        return ok
    end)
    -- BD-359 (mirrors Bootstrap): a settlement the renew tick commits after its retry window ended.
    Repo.setSettlementRecoveredHook(function(player, runId, outcome)
        local info = env.runs[runId]
        env.committed[runId] = {userId = player.UserId, catch = info and info.catch or 0, outcome = outcome, status = "recovered"}
        env.recovered = (env.recovered or 0) + 1
        env.RL.recoverAfterSettlement(player)
    end)
    RL.start()
    server.PlayersService.PlayerRemoving:Connect(leaving.leave)
    return env
end

-- Bootstrap's spawnLoadedPlayer: load (with the SessionBusy wait) then a character in the Sanctuary.
local function connect(env, userId)
    local server = env.server
    local p = mockPlayer(server, userId)
    table.insert(server.players, p)
    local loaded = env.Repo.load(p)
    local retries = math.ceil((server.Config.ProfileLeaseSeconds + 10) / 5)
    while not loaded and p.Parent and retries > 0 and (p.attrs.ProfileState == "SessionBusy" or p.attrs.ProfileState == "LoadFailed") do
        retries -= 1
        sleep(5)
        loaded = env.Repo.load(p)
    end
    if loaded and p.Parent then
        p.Character = newChar(p)
        env.RL.prepareSanctuary(p, p.Character)
    end
    p.loaded = loaded
    p.loadedAt = now
    return p
end

-- PlayerRemoving fires while Parent is still set; Parent becomes nil afterwards (the handler's first yield).
local function disconnect(env, p)
    local server = env.server
    local co = coroutine.create(env.leaving.leave)
    local ok, err = coroutine.resume(co, p)
    if not ok then table.insert(crashes, tostring(err)) end
    p.Parent = nil
    local i = table.find(server.players, p)
    if i then table.remove(server.players, i) end
end

local function startRun(env, p, catches)
    local c = p.Character
    env.RL.begin(p, c)
    local runId = c.attrs.RunId
    if runId == nil then return nil end
    c:SetAttribute("CatchScore", catches)
    c:SetAttribute("GrowthScore", catches * 12)
    env.runs[runId] = {userId = p.UserId, catch = catches}
    return runId
end

local function profileOf(userId) return DATA["u:" .. userId] end
local function eggIdsOf(profile)
    local ids, n = {}, 0
    for _, e in profile.eggs do ids[e.eggId] = (ids[e.eggId] or 0) + 1 n += 1 end
    for _, e in profile.runEggBank or {} do ids[e.eggId] = (ids[e.eggId] or 0) + 1 n += 1 end
    return ids, n + (profile.pendingChestGrants or 0)
end

-- Join, give the account an owned raptor in the store (a fixture), leave, join again so the cache holds it.
local function seededConnect(env, userId)
    local first = connect(env, userId)
    local fixture = profileOf(userId)
    fixture.collection.raptor.base = 1
    DATA["u:" .. userId] = fixture
    env.leaving.leave(first) first.Parent = nil
    local i = table.find(env.server.players, first)
    if i then table.remove(env.server.players, i) end
    sleep(3)
    return connect(env, userId)
end

local SCENARIO_OVERRIDES = nil -- Config overrides for the next runScenario (BD-358 contrast run)
local function runScenario(name, limit, fn)
    currentScenario = name
    now = 0
    queue = {}
    DATA = {}
    M = newMetrics()
    SCENARIO_FAIL_RATE = 0
    crashes = {}
    local server = newServer("A", "job-A", SCENARIO_OVERRIDES)
    SCENARIO_OVERRIDES = nil
    local env = boot(server)
    local finished = false
    task.spawn(function() fn(env, server) finished = true end)
    runQueue(limit)
    check("scenario completed within " .. limit .. " virtual s", finished, "now=" .. now)
    check("no coroutine crashed", #crashes == 0, table.concat(crashes, " | "))
    queue = {}
    return env, server
end

local function userIds(n) local t = {} for i = 1, n do t[i] = 3000 + i end return t end

-------------------------------------------------------------------- A: join storm
local function joinStorm(label, stagger, failRate)
    runScenario(label, 600, function(env, server)
        SCENARIO_FAIL_RATE = failRate
        local players = {}
        for i, id in userIds(12) do
            task.spawn(function()
                sleep(stagger * (i - 1))
                players[i] = connect(env, id)
            end)
        end
        sleep(90)
        local loaded, maxAt = 0, 0
        for _, p in players do
            if p.loaded and p.attrs.ProfileState == "Loaded" and p.Character then loaded += 1 maxAt = math.max(maxAt, p.loadedAt) end
        end
        if failRate == 0 then check("all 12 players Loaded after the join storm", loaded == 12, loaded .. "/12") end
        metric("players loaded", loaded .. "/12")
        metric("last player ready at virtual s", string.format("%.1f", maxAt))
        check("every loaded player ready within 60 virtual s", maxAt <= 60, "last ready " .. maxAt)
        check("no DataStore throttle-queue drop", M.queueDrops == 0, "drops " .. M.queueDrops)
        local leased = 0
        for _, id in userIds(12) do if profileOf(id) and profileOf(id).session then leased += 1 end end
        check("each loaded player has a distinct leased profile key", leased == loaded, leased .. " vs " .. loaded)
        metric("throttled requests", M.throttled)
        metric("max throttle wait s", string.format("%.2f", M.maxThrottleWait))
    end)
end
joinStorm("join-storm-12-instant", 0, 0)
joinStorm("join-storm-12-staggered-1s-flaky-5pct", 1, 0.05)

-------------------------------------------------------------------- B: settlement exactly-once with leaving players
local MODES = {"manual", "death", "leave-active", "leave-ending", "death+leave", "double-end+leave", "manual-rejoin"}
local function settlementRaces(label, failRate, seed, permute)
    local signatures = {}
    local env, server = runScenario(label, 1200, function(env, server)
        local ids = userIds(12)
        local order = {}
        for i = 1, 12 do order[i] = i end
        local rng = minstd(seed)
        if permute then for i = 12, 2, -1 do local j = 1 + math.floor(rng() * i) order[i], order[j] = order[j], order[i] end end
        local done = 0
        for slot, i in order do
            local id = ids[i]
            task.spawn(function()
                sleep(slot * 0.3)
                local p = connect(env, id)
                if not p.loaded then done += 1 return end
                SCENARIO_FAIL_RATE = failRate
                local mode = MODES[(i - 1) % #MODES + 1]
                local prng = minstd(id)
                local catches = 5 + math.floor(prng() * 36) -- 5..40 catches, a fixed function of the user only
                local hold = 100 + math.floor(prng() * 100) -- fixed per user, so run seconds do not depend on the order
                local runId = startRun(env, p, catches)
                if runId == nil then check("run started " .. id, false, tostring(env.PS.get(p, "RunStartBlocked"))) done += 1 return end
                sleep(hold)
                local c = p.Character
                if mode == "manual" then
                    env.RL.tryEnd(p, c, "ManualExit") env.RL.tryEnd(p, c, "ManualExit")
                    sleep(15) disconnect(env, p)
                elseif mode == "death" then
                    c.humanoid.Health = 0 sleep(15) disconnect(env, p)
                elseif mode == "leave-active" then
                    disconnect(env, p)
                elseif mode == "leave-ending" then
                    env.RL.tryEnd(p, c, "Eaten", 1) disconnect(env, p) -- busy path: settlement already running
                elseif mode == "death+leave" then
                    c.humanoid.Health = 0 disconnect(env, p)
                elseif mode == "double-end+leave" then
                    env.RL.tryEnd(p, c, "Death") env.RL.tryEnd(p, c, "ManualExit") disconnect(env, p)
                else -- manual-rejoin: end, leave, come back at once as a NEW Player object, run again, leave while Active
                    env.RL.tryEnd(p, c, "ManualExit") sleep(12) disconnect(env, p)
                    local q = connect(env, id)
                    if q.loaded then
                        local second = startRun(env, q, 7 + (id % 5))
                        if second == nil then check("rejoined player can start a run " .. id, false, tostring(env.PS.get(q, "RunStartBlocked"))) end
                        sleep(120) disconnect(env, q)
                    end
                end
                done += 1
            end)
        end
        sleep(500)
        check("all 12 player threads finished", done == 12, done .. "/12")
    end)
    -- Invariants -------------------------------------------------------------------
    local twice = 0
    for runId in env.runs do if (env.settleCalls[runId] or 0) > 1 then twice += 1 end end
    check("every run settled AT MOST once (settlement callback)", twice == 0, twice .. " runs settled twice")
    local rewards = server.require(node("src/server/RewardMath"))
    local settledEggs = {}
    for _, info in env.committed do
        settledEggs[info.userId] = (settledEggs[info.userId] or 0) + rewards.computeRunReward(info.catch, 0).eggCount
    end
    for _, id in userIds(12) do
        local profile = profileOf(id)
        local mine, n = eggIdsOf(profile)
        local dup = 0
        for _, count in mine do if count > 1 then dup += 1 end end
        check("no duplicated egg id, user " .. id, dup == 0, dup .. " duplicates")
        if failRate == 0 then
            check("eggs in profile == eggs of committed runs, user " .. id, n == (settledEggs[id] or 0), string.format("%d vs %d", n, settledEggs[id] or 0))
            check("lease released after leaving, user " .. id, profile.session == nil, "session left")
            -- every operation id must belong to a run of THIS user (no cross-player attribution)
            for _, op in profile.recentOperations do
                local info = env.runs[string.sub(op.id, 5)]
                check("operation " .. op.id .. " belongs to user " .. id, info ~= nil and info.userId == id, "cross-player operation")
            end
            local progress = server.Rules.upgrade(profile)
            signatures[id] = string.format("%d|%d|%d", n, progress.crystals, progress.accountXP)
        end
    end
    check("player list drained", #server.players == 0, #server.players .. " still listed")
    check("leave coordinator idle", env.leaving.pending == 0, tostring(env.leaving.pending))
    local resurrected = 0
    for p in env.released do if env.Repo.isLoaded(p) then resurrected += 1 end end
    check("no departed player is still loaded in the repository (no leaked profile)", resurrected == 0, tostring(resurrected))
    local committedRuns = 0 for _ in env.committed do committedRuns += 1 end
    metric("runs started/committed", #(function() local t = {} for k in env.runs do t[#t + 1] = k end return t end)() .. "/" .. committedRuns)
    return signatures
end

local baseline = settlementRaces("settlement-races-order-A", 0, 1, false)
local reordered1 = settlementRaces("settlement-races-order-B", 0, 2, true)
local reordered2 = settlementRaces("settlement-races-order-C", 0, 3, true)
currentScenario = "determinism-under-reordering"
local mismatches = 0
for id, signature in baseline do
    if reordered1[id] ~= signature or reordered2[id] ~= signature then mismatches += 1 end
end
check("per-user outcome (eggs, crystals, XP) identical across 3 join/leave orderings", mismatches == 0 and next(baseline) ~= nil, mismatches .. " users differ")
settlementRaces("settlement-races-flaky-25pct", 0.25, 4, true)

-------------------------------------------------------------------- C: same user leaves and rejoins during in-flight work
runScenario("rejoin-race", 400, function(env, server)
    local ids = userIds(12)
    local old = {}
    for i, id in ids do task.spawn(function() old[i] = seededConnect(env, id) end) end
    sleep(40)
    for i, id in ids do
        local p = old[i]
        task.spawn(function()
            -- an equip write is in flight while the player leaves, then the same user is back one tick later
            task.spawn(function() env.Repo.equipSpecies(p, "raptor") end)
            sleep(0.05)
            disconnect(env, p)
            sleep(0.1)
            p.nextSession = connect(env, id)
        end)
    end
    sleep(90)
    local good, lost = 0, 0
    for i, id in ids do
        local q = old[i].nextSession
        local profile = profileOf(id)
        if q and q.attrs.ProfileState == "Loaded" and profile.session and profile.session.leaseId ~= nil then good += 1 end
        -- renew must still own the lease: a late release of the OLD session must not have cleared the NEW one
        if q and (not env.Repo.renew(q) or q.attrs.ProfileState ~= "Loaded") then lost += 1 end
        check("old Player is not loaded any more, user " .. id, not env.Repo.isLoaded(old[i]), "profile resurrected for the departed Player")
    end
    check("12/12 rejoined sessions hold a lease after the old releases finished", good == 12, good .. "/12")
    check("12/12 rejoined sessions renew (lease not cleared by the old release)", lost == 0, lost .. " lost the lease")
end)

-- C2: the player leaves while the profile load is still in flight (UpdateAsync latency)
runScenario("leave-during-load", 300, function(env, server)
    local players = {}
    for i, id in userIds(12) do
        task.spawn(function()
            local p = mockPlayer(server, id)
            table.insert(server.players, p)
            players[i] = p
            task.spawn(function() p.loaded = env.Repo.load(p) end)
            sleep(0.02) -- load's UpdateAsync is mid-flight
            disconnect(env, p)
        end)
    end
    sleep(60)
    local leased, cached = 0, 0
    for i, id in userIds(12) do
        if profileOf(id) and profileOf(id).session then leased += 1 end
        if env.Repo.isLoaded(players[i]) then cached += 1 end
    end
    check("a player who left mid-load does not keep the lease", leased == 0, leased .. " profiles still leased")
    check("a player who left mid-load is not cached", cached == 0, cached .. " cached")
end)

-------------------------------------------------------------------- D: SaveFailed is recoverable
runScenario("save-failed-recovery", 300, function(env, server)
    local p = seededConnect(env, 3101)
    SCENARIO_FAIL_RATE = 1
    local ok, status = env.Repo.equipSpecies(p, "raptor")
    check("a failing write reports save_failed", not ok and status == "save_failed", tostring(status))
    check("state is SaveFailed after the failed write", p.attrs.ProfileState == "SaveFailed", tostring(p.attrs.ProfileState))
    SCENARIO_FAIL_RATE = 0
    check("lease renew recovers the player", env.Repo.renew(p) and p.attrs.ProfileState == "Loaded", tostring(p.attrs.ProfileState))
    local runId = startRun(env, p, 12)
    SCENARIO_FAIL_RATE = 1
    env.Repo.equipSpecies(p, "raptor")
    SCENARIO_FAIL_RATE = 0
    check("second failure leaves SaveFailed", p.attrs.ProfileState == "SaveFailed", tostring(p.attrs.ProfileState))
    disconnect(env, p)
    sleep(30)
    local _, n = eggIdsOf(profileOf(3101))
    check("settlement on disconnect is committed although an earlier write failed", env.committed[runId] ~= nil and n > 0, "eggs " .. n)
    check("lease released", profileOf(3101).session == nil, "lease kept")
end)

-------------------------------------------------------------------- E: egg claims exactly once, claim racing a leave
runScenario("egg-claims", 600, function(env, server)
    local p = connect(env, 3201)
    local runId = startRun(env, p, 40)
    env.RL.tryEnd(p, p.Character, "ManualExit")
    sleep(30)
    local eggId = env.PS.get(p, "NextChestId")
    check("a settled run exposes its first egg", type(eggId) == "string" and eggId ~= "", tostring(eggId))
    sleep(10)
    local statuses = {}
    for i = 1, 3 do task.spawn(function() local _, _, s = env.Repo.claimChest(p, eggId) statuses[i] = s end) end
    sleep(20)
    local claimed = 0
    for _, s in statuses do if s == "claimed" then claimed += 1 end end
    check("three concurrent claims of one egg: exactly one 'claimed'", claimed == 1, table.concat(statuses, ","))
    task.spawn(function() env.Repo.claimChest(p, env.PS.get(p, "NextChestId")) end) -- the player leaves mid-claim
    sleep(0.03)
    disconnect(env, p)
    sleep(40)
    check("no profile cached for a player who left mid-claim", not env.Repo.isLoaded(p), "resurrected")
    check("lease released after a mid-claim leave", profileOf(3201).session == nil, "lease kept")
    local ids, n = eggIdsOf(profileOf(3201))
    local dup = 0 for _, c in ids do if c > 1 then dup += 1 end end
    check("hatched eggs left the queue, none duplicated", dup == 0 and n < 40, string.format("%d eggs left, %d dup", n, dup))
    check("run settled exactly once", env.settleCalls[runId] == 1, tostring(env.settleCalls[runId]))
end)

-------------------------------------------------------------------- S: BindToClose with 12 active runs
local function shutdown(label, parallel)
    local seconds = 0
    runScenario(label, 600, function(env, server)
        local players = {}
        for i, id in userIds(12) do task.spawn(function() players[i] = connect(env, id) end) end
        sleep(20)
        for i, p in players do startRun(env, p, 10 + i) end
        sleep(130)
        SCENARIO_FAIL_RATE = 0.2
        local started = now
        if parallel then
            env.leaving.leaveAll(table.clone(server.players))
            env.leaving.waitIdle(25)
        else -- the old BindToClose: one player after another
            for _, p in table.clone(server.players) do
                local status = env.RL.endForDisconnect(p)
                if status ~= "busy" then env.Repo.release(p) end
            end
        end
        seconds = now - started
        SCENARIO_FAIL_RATE = 0
        metric("virtual seconds for 12 players to settle and release", string.format("%.1f", seconds))
        sleep(60)
        if parallel then
            local leased, settled = 0, 0
            for i, id in userIds(12) do
                if profileOf(id).session then leased += 1 end
                if #profileOf(id).recentOperations > 0 then settled += 1 end
            end
            metric("flaky 20% store: leases left / runs settled", leased .. " / " .. settled .. " of 12")
            check("BindToClose finishes inside the 30 s budget (25 s waited)", seconds <= 25, string.format("%.1f s", seconds))
            check("leave coordinator idle after shutdown", env.leaving.pending == 0, tostring(env.leaving.pending))
        end
    end)
    return seconds
end
local parallelSeconds = shutdown("shutdown-parallel-12", true)
local sequentialSeconds = shutdown("shutdown-sequential-12-old-behaviour", false)
metric("parallel vs sequential seconds", string.format("%.1f vs %.1f", parallelSeconds, sequentialSeconds))

-------------------------------------------------------------------- G: replication volume per player (attributes replicate to ALL clients)
runScenario("attribute-volume", 600, function(env, server)
    local Core = server.require(node("src/shared/PrivateStateCore"))
    local p = connect(env, 3301)
    local function bytes(map)
        local total, big = 0, {}
        for k, v in map do
            local s = jsonSize(v)
            total += s + #k
            if s > 150 then table.insert(big, string.format("%s=%d", k, s)) end
        end
        table.sort(big)
        return total, table.concat(big, " ")
    end
    local function publicBytes() return bytes(p.attrs) end
    local function privateBytes() return bytes(env.PS.snapshot(p)) end
    local freshPublic = publicBytes()
    local freshPrivate = privateBytes()
    metric("PUBLIC player attribute bytes, fresh profile", freshPublic)
    metric("PRIVATE owner-only bytes, fresh profile", freshPrivate)
    -- a mid-game profile: 10 runs of 40 eggs settled, 40 hatched
    for run = 1, 10 do
        local runId = startRun(env, p, 40)
        env.RL.tryEnd(p, p.Character, "ManualExit")
        sleep(30)
        for _ = 1, 3 do
            local id = env.PS.get(p, "NextChestId")
            if id and id ~= "" then env.Repo.claimChest(p, id) end
            sleep(6)
        end
        p.Character = newChar(p) env.RL.prepareSanctuary(p, p.Character)
    end
    local afterPublic, publicBig = publicBytes()
    local afterPrivate, privateBig = privateBytes()
    metric("PUBLIC player attribute bytes, after 10 runs of 40 eggs", afterPublic)
    metric("PRIVATE owner-only bytes, after 10 runs of 40 eggs (sent to the owner only)", afterPrivate)
    metric("largest public attributes", publicBig)
    metric("largest private values", privateBig)
    metric("replicated bytes per full resync with 12 players (x11 receivers each), public only", afterPublic * 11 * 12)
    metric("owner-only bytes per full resync with 12 players (x1 receiver each)", afterPrivate * 12)
    check("a mid-game player stays under 2 KB of public attributes (BD-360)", afterPublic < 2048, tostring(afterPublic))
    -- every name still set on the Player is classified public; nothing private leaked back onto it
    local leaked = {}
    for k in p.attrs do if Core.isPrivate(k) then table.insert(leaked, k) end end
    check("no private name is set as a Player attribute", #leaked == 0, table.concat(leaked, ","))
end)

-------------------------------------------------------------------- F: CombatRules world, 12 players
local function combatWorld(joinOrder)
    local srv = newServer("C", "job-C")
    local R = srv.require(node("src/shared/CombatRules"))
    local world = R.new(true)
    local defeatCount, settleCount = {}, {}
    world.onDefeat = function(victim)
        defeatCount[victim.key] = (defeatCount[victim.key] or 0) + 1
        if R.settle(world, victim.key) then settleCount[victim.key] = (settleCount[victim.key] or 0) + 1 end
    end
    local dinos = {}
    for _, i in joinOrder do
        local score = if i % 3 == 0 then 25500 else 100 * i -- a few huge hunters, the rest small
        dinos[i] = R.join(world, {userId = 4000 + i, runId = "run" .. i, class = "Ground", score = score, now = 0})
    end
    local rng = minstd(77)
    local t, attacks, hits = 0, 0, 0
    for step = 1, 900 do
        t += 0.5 + (step % 3) * 0.2
        R.tick(world, t, 0.1)
        local a = 1 + math.floor(rng() * 12)
        local v = 1 + math.floor(rng() * 12)
        if a ~= v and dinos[a] and dinos[v] and world.dinos[dinos[a].key] then
            attacks += 1
            local victimPos = {X = 0, Y = 0, Z = 0}
            local result = R.attack(world, dinos[a].key, t, {X = 0, Y = 0, Z = 3}, {X = 0, Y = 0, Z = -1},
                {{key = dinos[v].key, pos = victimPos, radius = 1}})
            if result.ok then hits += 1 end
        end
        for _, d in world.dinos do assert(d.state.hp >= 0 and d.state.hp <= d.state.maxHp + 1e-6, "hp out of range") end
    end
    local defeated = {}
    for key, count in defeatCount do defeated[#defeated + 1] = key end
    table.sort(defeated)
    return {defeated = defeated, defeatCount = defeatCount, settleCount = settleCount, hits = hits, attacks = attacks, R = R, world = world, dinos = dinos}
end
do
    currentScenario = "combat-12-players"
    local forward, backward = {}, {}
    for i = 1, 12 do forward[i] = i backward[i] = 13 - i end
    local a = combatWorld(forward)
    local b = combatWorld(backward)
    local doubled = 0
    for _, c in a.defeatCount do if c > 1 then doubled += 1 end end
    for _, c in a.settleCount do if c > 1 then doubled += 1 end end
    check("every defeat and settle fires exactly once per (userId, run)", doubled == 0, doubled .. " duplicates")
    check("the fuzz produced hits and at least one defeat", a.hits > 20 and #a.defeated >= 1, string.format("hits %d defeated %d", a.hits, #a.defeated))
    check("outcomes do not depend on the join order (same defeated set)", table.concat(a.defeated, ",") == table.concat(b.defeated, ","), "orders differ")
    -- A defeated dino cannot bite; leave then rejoin with a NEW run id does not inherit the defeat
    local key = a.defeated[1]
    if key then
        local result = a.R.attack(a.world, key, 5000, {X = 0, Y = 0, Z = 3}, {X = 0, Y = 0, Z = -1}, {})
        check("a defeated dino cannot attack", result.ok == false, tostring(result.reason))
        local userId = tonumber(string.match(key, "^(%d+)"))
        a.R.leave(a.world, key)
        local rejoined = a.R.join(a.world, {userId = userId, runId = "second-run", class = "Ground", score = 0, now = 6000})
        check("a rejoin with a new run id is a fresh alive dino", rejoined ~= nil and rejoined.state.phase == "Alive", rejoined and rejoined.state.phase or "nil")
        check("the old run key is gone from the world", a.world.dinos[key] == nil, "still there")
    end
    local count = 0 for _ in a.world.dinos do count += 1 end
    metric("tracked dinos after fuzz", count)
end

-------------------------------------------------------------------- H: nest queue per user, any advance order
do
    currentScenario = "nest-queue-12-users"
    local srv = newServer("N", "job-N")
    local Q = srv.require(node("src/shared/NestQueue"))
    local D = srv.Config.NestIncubationSeconds
    local function newList(id) local l = {} for j = 1, 5 do l[j] = {nestId = id .. "-" .. j, state = "waiting"} end return l end
    local lists = {}
    for i = 1, 12 do lists[i] = newList("u" .. i) end
    -- advance in a scrambled order at scrambled times; the end state must equal one direct advance
    local times = {D * 0.2, D * 1.1, D * 1.1, D * 2.5, D * 4.4, D * 9}
    local rng = minstd(5)
    local steps = {}
    for i = 1, 12 do for _, tm in times do steps[#steps + 1] = {i, tm} end end
    for i = #steps, 2, -1 do local j = 1 + math.floor(rng() * i) steps[i], steps[j] = steps[j], steps[i] end
    local lastTime = {}
    for _, s in steps do
        if not lastTime[s[1]] or s[2] >= lastTime[s[1]] then Q.advance(lists[s[1]], s[2], D) lastTime[s[1]] = s[2] end
    end
    local drift = 0
    for i = 1, 12 do
        local direct = newList("u" .. i)
        Q.advance(direct, 0, D) -- the first nest starts at t=0 in both runs
        local viaSteps = newList("u" .. i)
        Q.advance(viaSteps, 0, D)
        Q.advance(viaSteps, D * 9, D)
        Q.advance(direct, D * 9, D)
        for j = 1, 5 do if viaSteps[j].state ~= direct[j].state or viaSteps[j].readyAt ~= direct[j].readyAt then drift += 1 end end
        check("a nest list shares no state with another user, user " .. i, lists[i][1].nestId == "u" .. i .. "-1", lists[i][1].nestId)
    end
    check("advancing in several steps equals one direct advance (offline catch-up)", drift == 0, drift .. " nests differ")
end


-------------------------------------------------------------------- I: write budget and settlement retry (BD-358 / BD-359)
-- Largest number of store requests inside any 60 s window, against the 60 + 10 x players budget of that moment.
local function peakWindow()
    local reqs, lo, worst, worstBudget = M.requests, 1, 0, 60
    for hi = 1, #reqs do
        while reqs[hi].t - reqs[lo].t >= 60 do lo += 1 end
        local n = hi - lo + 1
        if n > worst then worst, worstBudget = n, 60 + 10 * math.max(1, reqs[hi].players) end
    end
    return worst, worstBudget
end

-- Every started run committed exactly once: eggs of the profile == eggs of the committed runs, no duplicate egg id,
-- one operation per run id, nothing lost. `released` also expects the leases to be gone (players left).
local function verifyRewards(env, server, runIds, released)
    local rewards = server.require(node("src/server/RewardMath"))
    local expected, lost, dupOps = {}, 0, 0
    for _, runId in runIds do
        local info = env.committed[runId]
        if not info then lost += 1 else
            expected[info.userId] = (expected[info.userId] or 0) + rewards.computeRunReward(info.catch, 0).eggCount
        end
    end
    check("no run lost: every started run was credited (" .. #runIds .. " runs)", lost == 0, lost .. " runs never committed")
    local wrong, dupEggs, leased = 0, 0, 0
    for _, id in userIds(12) do
        local profile = profileOf(id)
        if profile then
            local ids, n = eggIdsOf(profile)
            for _, c in ids do if c > 1 then dupEggs += 1 end end
            if n ~= (expected[id] or 0) then wrong += 1 end
            local seen = {}
            for _, op in profile.recentOperations do
                if seen[op.id] then dupOps += 1 end
                seen[op.id] = true
            end
            if released and profile.session then leased += 1 end
        end
    end
    check("no duplicate credit: no duplicated egg id and no repeated operation", dupEggs == 0 and dupOps == 0, dupEggs .. " egg ids, " .. dupOps .. " operations")
    check("eggs in every profile == eggs of its committed runs (nothing lost, nothing doubled)", wrong == 0, wrong .. " profiles differ")
    if released then check("every lease released", leased == 0, leased .. " leases left") end
    local twice = 0
    for _, runId in runIds do if (env.settleCalls[runId] or 0) > 1 then twice += 1 end end
    check("every run entered the settlement callback at most once", twice == 0, twice .. " runs")
end

local function boundedRate(label)
    local worst, budget = peakWindow()
    metric("peak requests in 60 s / budget", worst .. " / " .. budget)
    check("request rate stays under 60 + 10 x players (" .. label .. ")", worst <= budget, worst .. " > " .. budget)
    check("no DataStore throttle-queue drop (" .. label .. ")", M.queueDrops == 0, "drops " .. M.queueDrops)
end

local function allPlayers(env, n)
    local players = {}
    for i, id in userIds(n) do task.spawn(function() players[i] = connect(env, id) end) end
    sleep(25)
    return players
end

local function spammer(label, failRate, unbudgeted)
    local result = {}
    if unbudgeted then SCENARIO_OVERRIDES = {WriteBurst = 1e9, WriteRefillPerSecond = 1e9, WriteBudgetReserve = 0} end
    local env, server = runScenario(label, 600, function(env, server)
        local players = allPlayers(env, 12)
        env.Repo.start()
        SCENARIO_FAIL_RATE = failRate
        local runIds = {}
        for i = 2, 12 do runIds[#runIds + 1] = startRun(env, players[i], 10 + i) end
        local bad = players[1]
        local sent = 0
        local spamStart = now
        task.spawn(function() -- 10 Hz x 3 remotes for 60 s: settings, reveal skip, nest claim
            for k = 1, 600 do
                sent += 3
                local _, answer = env.Repo.setSettings(bad, {sound = {master = (k % 11) / 10}})
                result.lastAnswer = answer
                env.Repo.setRevealSkip(bad, {1 + (k % 3)})
                env.Repo.claimNest(bad, "nest-" .. k)
                sleep(0.1)
            end
            result.spamSeconds = now - spamStart
        end)
        sleep(20)
        for i = 2, 12 do env.RL.tryEnd(players[i], players[i].Character, "ManualExit") end
        sleep(100) -- spam is over after 60 s; coalesced values flush
        result.committedBy = 0
        for _, runId in runIds do if env.committed[runId] then result.committedBy += 1 end end
        SCENARIO_FAIL_RATE = 0
        sleep(40)
        result.sent = sent
        result.spamWrites = #(M.keyWrites["u:3001"] or {})
        result.final = profileOf(3001)
        result.runIds = runIds
        result.stats = env.Repo.budgetStats()
        result.maxThrottleWait = M.maxThrottleWait
        result.drops = M.queueDrops
    end)
    return env, server, result
end

local function spamChecks(label, env, server, r, unbudgeted, failRate)
    metric("spammer remotes sent / store writes on its key", r.sent .. " / " .. r.spamWrites)
    metric("routine writes admitted / rejected / coalesced / flushed",
        r.stats.admitted .. " / " .. r.stats.rejected .. " / " .. r.stats.coalesced .. " / " .. r.stats.flushed)
    metric("max throttle wait s / queue drops", string.format("%.2f", r.maxThrottleWait) .. " / " .. r.drops)
    if unbudgeted then return end
    check("11 other players' settlements all committed while one client spams (" .. label .. ")", r.committedBy == 11, r.committedBy .. "/11")
    check("the spammer's store writes are bounded by its bucket (<= burst + refill over the spam window)", r.spamWrites <= 6 + (r.spamSeconds or 0) + 12, r.spamWrites .. " vs " .. 6 + (r.spamSeconds or 0) + 12)
    local model = server.require(node("src/shared/SettingsModel"))
    local wanted = model.toStore(model.fromStore({sound = {master = (600 % 11) / 10}}))
    -- Never lost SILENTLY: the stored value is the latest one, or (only when the store itself failed and the player was in
    -- SaveFailed) the client was told so by a refused answer instead of "queued"/"saved".
    local saved = r.final.settings ~= nil and r.final.settings.sound.master == wanted.sound.master
    local told = r.lastAnswer ~= "queued" and r.lastAnswer ~= "saved"
    check("the spammer's LATEST settings were saved (coalesced) or the client was told it was refused",
        saved or (told and failRate > 0), tostring(r.final.settings and r.final.settings.sound.master) .. " vs " .. wanted.sound.master .. ", last answer " .. tostring(r.lastAnswer))
    if failRate == 0 then check("with a healthy store the latest settings are always saved", saved, "stale") end
    check("the spammer's remotes were answered rate_limited / queued, store not hit per call", r.stats.rejected > 0 and r.stats.coalesced > 0, "rejected " .. r.stats.rejected)
    check("no throttle queue drop while a client spams", r.drops == 0, tostring(r.drops))
    verifyRewards(env, server, r.runIds, false)
    boundedRate(label)
end

do
    local env, server, r = spammer("budget-spammer-12", 0, false)
    spamChecks("budget-spammer-12", env, server, r, false, 0)
    local env2, server2, r2 = spammer("budget-spammer-12-flaky-30pct", 0.3, false)
    spamChecks("budget-spammer-12-flaky-30pct", env2, server2, r2, false, 0.3)
    -- Contrast: the same spam with the budget switched off (the old behaviour). Metrics only, plus one comparison.
    local env3, server3, r3 = spammer("unbudgeted-contrast-spammer-12", 0, true)
    spamChecks("unbudgeted-contrast", env3, server3, r3, true)
    currentScenario = "unbudgeted-contrast-spammer-12"
    check("contrast: without the budget the spammer's key takes more writes than with it", r3.spamWrites > r.spamWrites, r3.spamWrites .. " vs " .. r.spamWrites)
end

-- Runs end at the same moment on 12 players while the store fails completely for `hiccup` virtual seconds.
local function hiccupScenario(label, hiccup, leave)
    local info = {}
    local env, server = runScenario(label, 900, function(env, server)
        local players = allPlayers(env, 12)
        env.Repo.start()
        local runIds = {}
        for i = 1, 12 do runIds[#runIds + 1] = startRun(env, players[i], 10 + i) end
        sleep(130)
        SCENARIO_FAIL_RATE = 1
        task.delay(hiccup, function() SCENARIO_FAIL_RATE = 0 end)
        local startedAt = now
        if leave then
            env.leaving.leaveAll(table.clone(server.players))
            env.leaving.waitIdle(27)
            info.seconds = now - startedAt
            sleep(30)
        else
            for i = 1, 12 do env.RL.tryEnd(players[i], players[i].Character, "ManualExit") end
            local firstAt
            while now - startedAt < hiccup + 40 do
                sleep(0.5)
                local n = 0
                for _, runId in runIds do if env.committed[runId] then n += 1 end end
                if n == 12 and not firstAt then firstAt = now - startedAt end
            end
            info.allCommittedAfter = firstAt
            info.failedWindows = env.Repo.budgetStats().settlementFailedWindows
            sleep(120) -- renew ticks recover anything that outlasted the window
            info.players = players
        end
        SCENARIO_FAIL_RATE = 0
        info.runIds = runIds
        info.stats = env.Repo.budgetStats()
    end)
    return env, server, info
end

do
    local env, server, i = hiccupScenario("hiccup-15s-present-12", 15, false)
    metric("all 12 settlements committed after virtual s", tostring(i.allCommittedAfter))
    metric("settlement attempts / windows that failed", i.stats.settlementAttempts .. " / " .. i.stats.settlementFailedWindows)
    check("a 15 s store hiccup loses nothing: every settlement committed", i.allCommittedAfter ~= nil and i.allCommittedAfter < 15 + 25, tostring(i.allCommittedAfter))
    check("a 15 s hiccup needs no recovery tick (the retry window was enough)", i.failedWindows == 0, tostring(i.failedWindows))
    verifyRewards(env, server, i.runIds, false)
    boundedRate("hiccup-15s")

    local env2, server2, j = hiccupScenario("hiccup-60s-present-12", 60, false)
    metric("windows that failed / recovered by the renew tick", j.stats.settlementFailedWindows .. " / " .. j.stats.settlementRecovered)
    check("a hiccup longer than the window records SaveFailed pendings", j.failedWindows > 0, tostring(j.failedWindows))
    check("pending settlements are recovered by the lease renew tick", j.stats.settlementRecovered > 0, tostring(j.stats.settlementRecovered))
    local stuck = 0
    for _, p in j.players do if env2.Repo.pendingSettlement(p) ~= nil or p.attrs.ProfileState ~= "Loaded" or p.respawns < 1 then stuck += 1 end end
    check("after recovery every player is Loaded again, nothing pending, character brought back", stuck == 0, stuck .. " players")
    verifyRewards(env2, server2, j.runIds, false)
    boundedRate("hiccup-60s")

    local env3, server3, k = hiccupScenario("hiccup-15s-leaving-12", 15, true)
    metric("virtual seconds for 12 players to settle and release over a 15 s hiccup", string.format("%.1f", k.seconds or -1))
    check("BindToClose-style leave of 12 players over a 15 s hiccup finishes within 27 s", (k.seconds or 99) <= 27, tostring(k.seconds))
    verifyRewards(env3, server3, k.runIds, true)
    boundedRate("hiccup-15s-leaving")
end

do
    local function flaky(label, rate)
        local saved = {}
        local env, server = runScenario(label, 900, function(env, server)
            local players = allPlayers(env, 12)
            env.Repo.start()
            local runIds = {}
            for i = 1, 12 do runIds[#runIds + 1] = startRun(env, players[i], 10 + i) end
            sleep(130)
            SCENARIO_FAIL_RATE = rate
            for i = 1, 12 do env.RL.tryEnd(players[i], players[i].Character, "ManualExit") end
            sleep(150)
            for i = 1, 12 do if i % 2 == 0 then disconnect(env, players[i]) end end -- half the players leave under the same failures
            sleep(60)
            SCENARIO_FAIL_RATE = 0
            sleep(100)
            saved.runIds = runIds
        end)
        local stats = env.Repo.budgetStats()
        metric("settlement attempts / failed windows / recovered", stats.settlementAttempts .. " / " .. stats.settlementFailedWindows .. " / " .. stats.settlementRecovered)
        verifyRewards(env, server, saved.runIds, false)
        boundedRate(label)
    end
    flaky("flaky-store-20pct-12", 0.2)
    flaky("flaky-store-40pct-12", 0.4)
end

-------------------------------------------------------------------- report
local failed = 0
for _, c in CHECKS do
    if not c.ok then failed += 1 end
    print(string.format("CHECK|%s|%s|%s|%s", if c.ok then "PASS" else "FAIL", c.scenario, c.name, c.detail))
end
print(string.format("DONE|%d|%d", #CHECKS, failed))
