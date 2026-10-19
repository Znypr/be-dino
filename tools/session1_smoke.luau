-- Session 1 smoke body (docs/125). Appended by tools/verify_session1_smoke.py after the verify_load scheduler / DataStore mock.
-- Runs the real server modules unmodified with the PLAYTEST Config values (__PLAYTEST__ is replaced by the wrapper).
-- Output protocol: REPORT|text, CHECK|PASS/FAIL|name|detail, DONE|total|failed.

math.randomseed(20261016)
local CHECKS = {}
local function check(name, cond, detail)
    table.insert(CHECKS, {name = name, ok = cond == true, detail = tostring(detail or "")})
end
local REPORT = {}
local function report(text) table.insert(REPORT, text) end

local captured, warnings = {}, {}
SMOKE_PRINT = function(...) table.insert(captured, table.concat(table.pack(...), " ")) end
SMOKE_WARN = function(...) table.insert(warnings, table.concat(table.pack(...), " ")) end

-- Engine globals the real modules touch only on the paths this smoke drives.
CFrame = {new = function(x, y, z) return setmetatable({x = x, y = y, z = z}, {__mul = function(a) return a end}) end, Angles = function() return {} end}

local function v3(x, y, z)
    return setmetatable({X = x, Y = y, Z = z}, {__sub = function(a, b)
        local d = {X = a.X - b.X, Y = a.Y - b.Y, Z = a.Z - b.Z}
        d.Magnitude = math.sqrt(d.X ^ 2 + d.Y ^ 2 + d.Z ^ 2)
        return d
    end})
end

local function signal()
    local s = {fns = {}}
    function s:Connect(f) table.insert(self.fns, f) return {Disconnect = function() end} end
    return s
end

local function installMocks(server)
    server.PlayersService = {PlayerAdded = signal(), PlayerRemoving = signal(), GetPlayers = function() return table.clone(server.players) end}
    server.workspace = {GetServerTimeNow = function() return 1.7e9 + now end, GetAttribute = function() return nil end, SetAttribute = function() end, GetAttributeChangedSignal = function() return signal() end}
    server.created, server.fired = {}, {}
    server.Instance = {new = function(className)
        local o = {ClassName = className, Name = className, OnServerEvent = signal(), children = {}}
        function o:FindFirstChild(n) return self.children[n] end
        function o:Destroy() end
        function o:IsA(c) return c == className end
        function o:FireClient(to, msg) table.insert(server.fired, {remote = self.Name, to = to, msg = msg}) end
        table.insert(server.created, o)
        return setmetatable(o, {__newindex = function(t, k, v)
            rawset(t, k, v)
            if k == "Parent" and type(v) == "table" and rawget(v, "children") then v.children[t.Name] = t end
        end})
    end}
end

local function remote(env, name)
    for i = #env.server.created, 1, -1 do
        local o = env.server.created[i]
        if o.Name == name then return o end
    end
    error("remote not created: " .. name)
end
local function fire(env, name, player, ...) -- the real OnServerEvent handler, as the engine would call it
    for _, f in remote(env, name).OnServerEvent.fns do f(player, ...) end
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
                if v <= 0 then for _, f in t.Died.fns do task.spawn(f) end end
            else rawset(t, k, v) end
        end})
    c.humanoid = humanoid
    c.root = {Position = v3(0, 6, 580), IsA = function(_, cls) return cls == "BasePart" end}
    function c:FindFirstChildOfClass(cls) if cls == "Humanoid" then return humanoid end return nil end
    function c:FindFirstChild(n) if n == "HumanoidRootPart" then return self.root end return nil end
    function c:WaitForChild() return humanoid end
    c:SetAttribute("DinoAttached", true)
    return c
end

local ENV
local function mockPlayer(server, userId)
    local p = {UserId = userId, Name = "P" .. userId, DisplayName = "Friend" .. string.char(65 + (userId - 3001) % 26), Parent = true, attrs = {}, sig = {}, respawns = 0}
    function p:SetAttribute(k, v)
        local old = self.attrs[k]
        self.attrs[k] = v
        if old ~= v and self.sig[k] then for _, f in self.sig[k].fns do task.spawn(f) end end
    end
    function p:GetAttribute(k) return self.attrs[k] end
    function p:GetAttributeChangedSignal(k) self.sig[k] = self.sig[k] or signal() return self.sig[k] end
    function p:Kick(message) self.kicked = message or true self.Parent = nil end
    function p:LoadCharacterAsync()
        self.respawns += 1
        self.Character = newChar(self)
        ENV.RL.prepareSanctuary(self, self.Character) -- Bootstrap's CharacterAdded: back in the Sanctuary
    end
    return p
end

local function boot(server)
    installMocks(server)
    local Repo = server.Repository
    local RL = server.require(node("src/server/RunLifecycle"))
    local LC = server.require(node("src/server/LeaveCoordinator"))
    local PS = server.require(node("src/server/PrivateState"))
    local Telemetry = server.require(node("src/server/TelemetryService"))
    local Rare = server.require(node("src/server/RareHatchService"))
    local Chest = server.require(node("src/server/ChestService"))
    local Hub = server.require(node("src/server/HubTravelService"))
    local env = {server = server, RL = RL, Repo = Repo, PS = PS, Rare = Rare, Hub = Hub, settleCalls = {}, runs = {}, committed = {}, released = {}}
    ENV = env
    PS.start()
    local leaving = LC.new({endForDisconnect = RL.endForDisconnect, release = function(p) env.released[p] = true return Repo.release(p) end, publish = nil})
    env.leaving = leaving
    -- mirrors Bootstrap.server.luau's settlement callback (commit, then the read-only telemetry hook)
    RL.configureSettlement(function(player, runId, catchScore, reason, eggEvents, runSeconds)
        env.settleCalls[runId] = (env.settleCalls[runId] or 0) + 1
        local ok, outcome, status = Repo.commitRunSettlement(player, runId, catchScore, eggEvents, runSeconds, nil)
        if ok then
            env.committed[runId] = {userId = player.UserId, catch = catchScore, outcome = outcome, status = status, reason = reason}
            Telemetry.runSettled(player, reason, runSeconds, outcome)
        end
        leaving.settlementFinished(player)
        return ok
    end)
    Repo.setSettlementRecoveredHook(function(player) RL.recoverAfterSettlement(player) end)
    Telemetry.start()
    RL.start()
    Chest.start(Repo)
    Rare.start()
    Hub.start()
    Repo.start()
    server.PlayersService.PlayerRemoving:Connect(leaving.leave)
    return env
end

local function connect(env, userId)
    local server = env.server
    local p = mockPlayer(server, userId)
    table.insert(server.players, p)
    for _, f in server.PlayersService.PlayerAdded.fns do task.spawn(f, p) end
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
        env.PS.sendSnapshot(p) -- the client's hello
    end
    p.loaded = loaded
    return p
end

local function disconnect(env, p)
    for _, f in env.server.PlayersService.PlayerRemoving.fns do -- every PlayerRemoving handler, while Parent is still set
        local co = coroutine.create(f)
        local ok, err = coroutine.resume(co, p)
        if not ok then table.insert(crashes, tostring(err)) end
    end
    p.Parent = nil
    local i = table.find(env.server.players, p)
    if i then table.remove(env.server.players, i) end
end

local function profileOf(userId) return DATA["u:" .. userId] end

-------------------------------------------------------------------- scenario
local PLAYTEST = __PLAYTEST__
local FOOD = __FOOD_KINDS__
local totalWeight = 0
for _, k in FOOD do totalWeight += k.weight end
local meanPoints = 0
for _, k in FOOD do meanPoints += k.weight / totalWeight * k.points end

local function runScenario(fn)
    now = 0
    queue = {}
    DATA = {}
    M = newMetrics()
    SCENARIO_FAIL_RATE = 0
    crashes = {}
    local server = newServer("A", "job-A", PLAYTEST)
    local env = boot(server)
    local finished = false
    task.spawn(function() fn(env, server) finished = true end)
    runQueue(60000)
    check("session completed within 60000 virtual s", finished, "now=" .. now)
    check("no coroutine crashed", #crashes == 0, table.concat(crashes, " | "))
    return env, server
end

local function containsString(value, needle, depth)
    depth = depth or 0
    if depth > 8 then return false end
    if type(value) == "string" then return string.find(value, needle, 1, true) ~= nil end
    if type(value) == "table" then
        for k, v in value do
            if containsString(k, needle, depth + 1) or containsString(v, needle, depth + 1) then return true end
        end
    end
    return false
end

runScenario(function(env, server)
    local Config = server.Config
    local RewardMath = server.require(node("src/server/RewardMath"))
    local FoodCatchRules = server.require(node("src/shared/FoodCatchRules"))
    local RunEggTags = server.require(node("src/shared/RunEggTags"))
    local PS, Repo, RL = env.PS, env.Repo, env.RL
    local ids = {3001, 3002, 3003, 3004}
    local species = {[3001] = "raptor", [3002] = "compy", [3003] = "triceratops", [3004] = "tyrannosaurus"}
    local plan = { -- efficiency = share of the 40 pickups/min of docs/119 that the player really collects
        [3001] = {eff = 0.80, end_ = "home", seconds = 300},
        [3002] = {eff = 0.75, end_ = "home", seconds = 300},
        [3003] = {eff = 0.85, end_ = "eaten", seconds = 210},
        [3004] = {eff = 0.90, end_ = "home", seconds = 170},
    }

    -- phase 0: seed owned species (a previous visit), then forget its telemetry
    for _, id in ids do
        local first = connect(env, id)
        local fixture = profileOf(id)
        fixture.collection[species[id]] = fixture.collection[species[id]] or {base = 0, gold = 0, diamond = 0, events = {}, variants = {}}
        fixture.collection[species[id]].base = math.max(1, fixture.collection[species[id]].base)
        DATA["u:" .. id] = fixture
        env.leaving.leave(first) first.Parent = nil
        table.remove(server.players, table.find(server.players, first))
    end
    sleep(10)
    captured = {}
    server.fired = {}

    -- phase 1: 4 players join, each picks a species
    local players = {}
    for i, id in ids do task.spawn(function() sleep(i * 0.7) players[id] = connect(env, id) end) end
    sleep(15)
    for _, id in ids do
        local p = players[id]
        check("player joined and loaded " .. id, p and p.loaded and p.attrs.ProfileState == "Loaded", p and p.attrs.ProfileState)
        local ok, status = Repo.equipSpecies(p, species[id])
        check("species picked " .. id .. " = " .. species[id], ok == true, status)
        check("equipped species is replicated " .. id, p.attrs.EquippedSpeciesId == species[id], p.attrs.EquippedSpeciesId)
    end

    -- run + hatch helpers
    local stats = {}
    local rng = minstd(2026)
    local function pickPoints()
        local roll = rng() * totalWeight
        for _, k in FOOD do roll -= k.weight if roll <= 0 then return k.points end end
        return FOOD[1].points
    end
    local function waitForRespawn(p, before)
        local waited = 0
        while p.respawns == before and waited < 120 do sleep(1) waited += 1 end
        sleep(1)
    end
    local function playRun(p, cfg, runNo)
        local c = p.Character
        RL.begin(p, c)
        c.root.Position = v3((p.UserId - 3000) * 300, 20, 0) -- players are far apart on the island
        local runId = c.attrs.RunId
        check("run " .. runNo .. " started " .. p.UserId, runId ~= nil and c.attrs.RunState == "Active" and p.attrs.Location == "Island", tostring(p.attrs.RunBlocked))
        local s = {runId = runId, food = 0, start = now, pickups = 0}
        env.runs[runId] = {userId = p.UserId}
        local carry, catches, growth = 0, 0, 0
        local interval = 60 / (40 * cfg.eff)
        local before = p.respawns
        while now - s.start < cfg.seconds do
            sleep(interval * (0.6 + 0.8 * rng()))
            local points = pickPoints()
            s.food += points s.pickups += 1
            -- FoodService: FoodCatchRules.award + RunEggTags.nextScore, GrowthPerFood
            local whole
            whole, carry = FoodCatchRules.award(points, carry, 1)
            catches = RunEggTags.nextScore(catches, whole, Config.MaxCatchScore, Config.RunEggMaxPerRun)
            growth += points * Config.GrowthPerFood
            c:SetAttribute("FoodCatchCarry", carry)
            c:SetAttribute("CatchScore", catches)
            c:SetAttribute("GrowthScore", growth)
        end
        s.catches, s.seconds = catches, now - s.start
        env.runs[runId].catch = catches
        if cfg.end_ == "eaten" then
            RL.tryEnd(p, c, "Predation", 9999) -- the same call PredationService makes
            check("eaten player cannot end the run twice", RL.tryEnd(p, c, "Predation", 9999) == false)
        else
            fire(env, "RequestEndRun", p) -- the real Exit Home handler
            fire(env, "RequestEndRun", p) -- a double tap inside the cooldown is ignored
        end
        waitForRespawn(p, before)
        s.reason = (env.committed[runId] or {}).reason
        return s
    end
    local function revealAll(p, s)
        local revealed, failed, species_ = 0, 0, {}
        local guard = 0
        while guard < 600 do
            guard += 1
            local eggId = PS.get(p, "NextChestId")
            if type(eggId) ~= "string" or eggId == "" then break end
            fire(env, "ClaimChest", p, eggId, "tok" .. guard)
            if p.attrs.LastChestClaimStatus == "claimed" then
                revealed += 1
                if PS.get(p, "LastChestFailed") == true then failed += 1 end
                if guard == 1 then -- BD-1019: closing the hatch screen (X, tap outside, Escape) and tapping the same egg again must never hatch it twice
                    sleep(Config.ChestClaimRequestCooldownSeconds + .1)
                    fire(env, "ClaimChest", p, eggId, "replay" .. guard)
                    check("a replayed claim of an opened egg hatches nothing " .. tostring(p.UserId), p.attrs.LastChestClaimStatus ~= "claimed", p.attrs.LastChestClaimStatus)
                end
            end
            sleep(Config.HatchRevealSeconds)
        end
        s.revealed, s.failed = revealed, failed
        return revealed
    end

    -- phase 2: first runs, in parallel
    local first = {}
    local done = 0
    for _, id in ids do
        task.spawn(function()
            first[id] = playRun(players[id], plan[id], 1)
            done += 1
        end)
    end
    sleep(380)
    check("all first runs finished", done == 4, done)
    local expectedEggs, runs1 = 0, {}
    for _, id in ids do
        local s = first[id]
        local c = env.committed[s.runId]
        check("run settled exactly once " .. id, env.settleCalls[s.runId] == 1 and c ~= nil, tostring(env.settleCalls[s.runId]))
        local reward = RewardMath.computeRunReward(s.catches, s.seconds)
        check("committed eggs == eggs caught " .. id, c and c.outcome.eggCount == s.catches and reward.eggCount == s.catches, string.format("%s vs %d", c and c.outcome.eggCount, s.catches))
        check("end reason recorded " .. id, c and c.reason == (if plan[id].end_ == "eaten" then "Predation" else "ManualExit"), c and c.reason)
        runs1[id] = s
        report(string.format("run 1 user %d (%s, %s): %ds, %d pickups, %d food (%.0f/min), %d eggs, %d crystals, %d nests", id, species[id], plan[id].end_, s.seconds, s.pickups, s.food,
            s.food / (s.seconds / 60), s.catches, c.outcome.crystals, c.outcome.nestCount))
    end
    -- egg band for the food-only players who ran the full 5 minutes (docs/119: about 15, 12..20 healthy)
    local sum, n = 0, 0
    for _, id in {3001, 3002} do
        local e = runs1[id].catches
        check(string.format("food-only 5 min run %d gives a healthy egg band (10..22)", id), e >= 10 and e <= 22, e)
        check("food-only run growth > 0 without any predation " .. id, players[id].attrs.LastPredatorUserId == nil and runs1[id].reason == "ManualExit")
        sum += e n += 1
    end
    check("mean eggs of two 5-minute runs about 15 (12..18)", sum / n >= 12 and sum / n <= 18, sum / n)
    check("eaten player kept the eggs caught before being eaten", runs1[3003].catches >= 5 and env.committed[runs1[3003].runId].outcome.eggCount == runs1[3003].catches, runs1[3003].catches)
    check("eaten run records the predator for telemetry only", players[3003].attrs.LastRunEndReason == "Predation")
    check("exit-home run is at least the nest minimum and drops a nest", env.committed[runs1[3004].runId].outcome.nestCount >= 1, env.committed[runs1[3004].runId].outcome.nestCount)

    -- phase 3: reveal every egg, one by one (15 eggs about 15 s here: HatchRevealSeconds)
    local revealDone = 0
    for _, id in ids do task.spawn(function() revealAll(players[id], runs1[id]) revealDone += 1 end) end
    sleep(60)
    check("all reveal loops finished", revealDone == 4, revealDone)
    local heldSpecies = {}
    for _, id in ids do
        local s = runs1[id]
        check("every run egg revealed exactly once " .. id, s.revealed == s.catches, string.format("%d of %d", s.revealed, s.catches))
        local profile = profileOf(id)
        local left = #profile.eggs + #(profile.runEggBank or {}) + (profile.pendingChestGrants or 0)
        check("no egg left in the queue after revealing " .. id, left == 0, left)
        report(string.format("hatch user %d: %d revealed, %d Cracked (failed)", id, s.revealed, s.failed))
    end

    -- phase 4: rare hatch through RareHatchService (real settled-outcome shape) and its rate limits
    local legendary
    for id, tier in server.Config.SpeciesRarities do if tier == 5 and legendary == nil then legendary = id end end
    check("a Legendary species exists in the playtest config", legendary ~= nil)
    local rareBefore = #server.fired
    local function rareFired(kind, to)
        local n = 0
        for i = rareBefore + 1, #server.fired do
            local f = server.fired[i]
            if f.remote == "RareHatch" and f.msg.k == kind and (to == nil or f.to == to) then n += 1 end
        end
        return n
    end
    local p1, p2, p3, p4 = players[3001], players[3002], players[3003], players[3004]
    -- (a) the hatcher gets a celebration per rare egg, the room gets ONE announcement (the best) per window
    env.Rare.record(p1, {speciesId = legendary, shiny = false, eventMutationId = "", failed = false, eggId = "smoke-e1"})
    env.Rare.record(p1, {speciesId = "compy", shiny = true, eventMutationId = "", failed = false, eggId = "smoke-e2"})
    env.Rare.record(p1, {speciesId = "compy", shiny = false, eventMutationId = "", failed = true, eggId = "smoke-e3"}) -- a Cracked egg is never rare
    env.Rare.record(p1, {speciesId = "compy", shiny = true, eventMutationId = "", failed = false, eggId = "smoke-e2"}) -- the same egg twice
    sleep(5)
    check("hatcher got 2 personal celebrations (Cracked and repeated egg ignored)", rareFired("me", p1) == 2, rareFired("me", p1))
    check("the other three players got exactly one announcement each", rareFired("all", p2) == 1 and rareFired("all", p3) == 1 and rareFired("all", p4) == 1, rareFired("all", p2) .. "," .. rareFired("all", p3) .. "," .. rareFired("all", p4))
    check("the hatcher is not told about their own announcement", rareFired("all", p1) == 0)
    -- (b) per-hatcher cooldown, then (c) global cap with 4 hatchers inside one window
    local announcedBefore = rareFired("all")
    env.Rare.record(p1, {speciesId = "compy", shiny = true, eventMutationId = "", failed = false, eggId = "smoke-e4"})
    sleep(5)
    check("a hatcher inside the cooldown is not announced again", rareFired("all") == announcedBefore, rareFired("all") - announcedBefore)
    sleep(60) -- past R.Cooldown
    for i, p in {p1, p2, p3, p4} do env.Rare.record(p, {speciesId = "compy", shiny = true, eventMutationId = "", failed = false, eggId = "smoke-g" .. i}) end
    sleep(5)
    local inWindow = rareFired("all") - announcedBefore
    local capped = (3 * 4) -- 4 hatchers x 3 other players: at most GlobalMax (4) announcements, each sent to 3 others
    check("server-wide announcement cap holds with 4 simultaneous hatchers", inWindow <= 4 * 3 and inWindow >= 3, inWindow .. " messages (cap " .. capped .. ")")
    -- nothing private in the announcement: only kind and text, no egg id, no user id
    local leakedAll = false
    for _, f in server.fired do
        if f.remote == "RareHatch" and f.msg.k == "all" then
            -- BD-1121: with Config.RareFindBannerEnabled the announcement also carries the tier number, the species display name and two booleans (no egg id, no user id, no player name)
            local allowedKeys = {k = true, kind = true, text = true, tier = true, species = true, shiny = true, mutation = true}
            for key, value in f.msg do
                if not allowedKeys[key] then leakedAll = true end
                if key == "species" and (type(value) ~= "string" or string.find(value, "smoke%-") or string.find(value, "300%d")) then leakedAll = true end
                if (key == "tier" and type(value) ~= "number") or ((key == "shiny" or key == "mutation") and type(value) ~= "boolean") then leakedAll = true end
            end
            if string.find(f.msg.text, "smoke%-") or string.find(f.msg.text, "300%d") then leakedAll = true end
        end
    end
    check("announcements carry only kind and kid-friendly text (no egg id, no user id)", not leakedAll)

    -- phase 5: second runs. P4 plays a long marathon (nests overflow to crystals), others a normal 5 minutes
    local second, done2 = {}, 0
    local plan2 = {
        [3001] = {eff = 0.80, end_ = "home", seconds = 300},
        [3002] = {eff = 0.75, end_ = "home", seconds = 300},
        [3003] = {eff = 0.85, end_ = "home", seconds = 300},
        [3004] = {eff = 4.0, end_ = "home", seconds = 1560}, -- ~26 min at 160 pickups/min: a long, fast run near the 150-egg cap
    }
    local third
    for _, id in ids do
        task.spawn(function()
            second[id] = playRun(players[id], plan2[id], 2)
            if id == 3004 then third = playRun(players[id], plan2[id], 3) end -- a second long run pays for the perk
            done2 += 1
        end)
    end
    local waited2 = 0
    while done2 < 4 and waited2 < 6000 do sleep(10) waited2 += 10 end
    check("all second runs finished", done2 == 4, done2)
    check("the third (long) run settled once", third ~= nil and env.settleCalls[third.runId] == 1 and env.committed[third.runId] ~= nil, third and env.settleCalls[third.runId])
    report(string.format("run 3 user 3004: %d eggs, %d crystals, +%d nest crystals", third.catches, env.committed[third.runId].outcome.crystals, env.committed[third.runId].outcome.nestCrystals or 0))
    for _, id in ids do
        local s = second[id]
        local c = env.committed[s.runId]
        check("second run settled exactly once " .. id, env.settleCalls[s.runId] == 1 and c ~= nil, tostring(env.settleCalls[s.runId]))
        report(string.format("run 2 user %d: %ds, %d food, %d eggs, %d crystals, %d nests kept%s, +%d nest crystals", id, s.seconds, s.food, s.catches,
            c.outcome.crystals, c.outcome.nestCount, if c.outcome.nestFull then " (full)" else "", c.outcome.nestCrystals or 0))
    end
    local big = env.committed[second[3004].runId].outcome
    check("the long run is capped at RunEggMaxPerRun", second[3004].catches <= Config.RunEggMaxPerRun and second[3004].catches >= 100, second[3004].catches)
    check("nest overflow: nests beyond the five spots became crystals", (big.nestCrystals or 0) > 0 and big.nestFull == true, tostring(big.nestCrystals))
    check("nest overflow pays NestOverflowCrystals each", (big.nestCrystals or 0) % Config.NestOverflowCrystals == 0)
    local nestCount = #profileOf(3004).eggNests
    check("never more nests than the storage capacity", nestCount <= Config.NestStorageCapacity, nestCount)
    -- hatch the second batches
    local rev2 = 0
    for _, id in ids do task.spawn(function() revealAll(players[id], second[id]) rev2 += 1 end) end
    local waited3 = 0
    while rev2 < 4 and waited3 < 2000 do sleep(10) waited3 += 10 end
    check("second hatch loops finished", rev2 == 4, rev2)
    for _, id in ids do
        local expected = second[id].catches + (if id == 3004 then third.catches else 0)
        check("every second-run egg revealed " .. id, second[id].revealed == expected, string.format("%d of %d", second[id].revealed, expected))
    end

    -- phase 6: shops. crystals buy an aura; Fast travel needs 500
    local progress = server.Rules.upgrade(profileOf(3004))
    report(string.format("user 3004 crystals before shopping: %d (perk costs %d)", progress.crystals, server.require(node("src/shared/ProgressionConfig")).Perks[1].price))
    local hubStation = "nests"
    check("hub station exists", server.require(node("src/shared/CaveHubLayout")).get().byId[hubStation] ~= nil)
    p4.Character.root.Position = v3(0, 6, 580)
    sleep(2)
    -- The playtest ships FastTravelPerk = false (read from the real profile): the perk cannot be bought and rail travel is free.
    -- With the flag true (a future profile) the original perk checks run instead.
    local PERK = PLAYTEST.FastTravelPerk == true
    local okPoor, statusPoor = Repo.progressionAction(p3, "buyPerk", "fastTravel", "smoke-poor")
    local p3Crystals = server.Rules.upgrade(profileOf(3003)).crystals
    local okAura, statusAura = Repo.progressionAction(p1, "buyAura", "meadow", "smoke-aura", false)
    local crystals1 = server.Rules.upgrade(profileOf(3001)).crystals
    check("two normal runs buy a first aura (crystal shop)", okAura == true, statusAura)
    local okEgg, statusEgg = Repo.progressionAction(p2, "buyEgg", "random", "smoke-egg")
    check("random shop eggs stay blocked in the playtest (paid-random policy gate)", okEgg == false and statusEgg == "random_items_unavailable", statusEgg)
    local before4 = server.Rules.upgrade(profileOf(3004)).crystals
    if not PERK then
        report("FastTravelPerk is false in the playtest profile: perk purchase refused, rail travel free for everyone")
        check("fast travel perk cannot be bought while the flag is off", okPoor == false and statusPoor == "perk_unavailable", tostring(statusPoor))
        local okPerk, statusPerk = Repo.progressionAction(p4, "buyPerk", "fastTravel", "smoke-perk")
        check("the long-run player cannot buy the perk either", okPerk == false and statusPerk == "perk_unavailable", tostring(statusPerk))
        check("a refused perk charges nothing", server.Rules.upgrade(profileOf(3004)).crystals == before4, server.Rules.upgrade(profileOf(3004)).crystals .. " vs " .. before4)
        sleep(2)
        local travel = env.Hub.handle(p4, {station = hubStation})
        check("rail travel works inside the hub without the perk", travel.ok == true and travel.station == hubStation, tostring(travel.reason))
        check("travel marks only a public station name", p4.attrs.HubStation == hubStation)
        local again = env.Hub.handle(p4, {station = hubStation})
        check("rail travel is rate limited", again.ok == false and again.reason == "rate_limited", tostring(again.reason))
        p3.Character.root.Position = v3(0, 6, 580)
        sleep(2)
        local other = env.Hub.handle(p3, {station = hubStation})
        check("a player without the perk can travel too (perk flag off)", other.ok == true, tostring(other.reason))
    else
        local denied = env.Hub.handle(p4, {station = hubStation})
        check("fast travel is refused before the perk is bought", denied.ok == false and denied.reason == "not_owned", denied.reason)
        check("a player without 500 crystals cannot buy the perk", okPoor == false and statusPoor == "insufficient_crystals", tostring(statusPoor) .. " crystals " .. p3Crystals)
        local okPerk, statusPerk = Repo.progressionAction(p4, "buyPerk", "fastTravel", "smoke-perk")
        check("the long-run player buys the Fast travel perk", okPerk == true and statusPerk == "purchased", tostring(statusPerk) .. " had " .. before4)
        local after4 = server.Rules.upgrade(profileOf(3004)).crystals
        check("the perk cost exactly its price", before4 - after4 == 500, before4 - after4)
        local okTwice, statusTwice = Repo.progressionAction(p4, "buyPerk", "fastTravel", "smoke-perk2")
        check("the perk cannot be bought twice", okTwice == false and statusTwice == "already_owned", statusTwice)
        local replay, statusReplay = Repo.progressionAction(p4, "buyPerk", "fastTravel", "smoke-perk")
        check("replaying the same purchase token does not charge twice", replay == true and server.Rules.upgrade(profileOf(3004)).crystals == after4, tostring(statusReplay))
        sleep(2)
        local travel = env.Hub.handle(p4, {station = hubStation})
        check("fast travel works for the owner inside the hub", travel.ok == true and travel.station == hubStation, tostring(travel.reason))
        check("travel marks only a public station name", p4.attrs.HubStation == hubStation)
        local again = env.Hub.handle(p4, {station = hubStation})
        check("fast travel is rate limited", again.ok == false and again.reason == "rate_limited", tostring(again.reason))
        p3.Character.root.Position = v3(0, 6, 580)
        sleep(2)
        local other = env.Hub.handle(p3, {station = hubStation})
        check("a player who did not buy the perk still cannot travel", other.ok == false and other.reason == "not_owned", tostring(other.reason))
    end

    -- phase 7: nests are ready after incubation; claim them (overflow already paid)
    sleep(Config.NestIncubationSeconds + 600)
    local nestEggsBefore = {}
    for _, id in ids do
        local list = profileOf(id).eggNests or {}
        local ready = nil
        for _, nest in list do
            if nest.state == "ready" or (nest.readyAt ~= nil and nest.readyAt <= math.floor(now)) then ready = nest break end
        end
        if ready then
            local bank = #(profileOf(id).runEggBank or {}) + #profileOf(id).eggs
            fire(env, "ClaimNest", players[id], ready.nestId)
            sleep(3)
            local after = #(profileOf(id).runEggBank or {}) + #profileOf(id).eggs
            check("claiming a ready nest adds its eggs once " .. id, players[id].attrs.LastNestClaimStatus == "opened" and after - bank == ready.size, string.format("%s +%d of %d", tostring(players[id].attrs.LastNestClaimStatus), after - bank, ready.size))
            fire(env, "ClaimNest", players[id], ready.nestId)
            sleep(3)
            check("claiming the same nest twice adds nothing " .. id, #(profileOf(id).runEggBank or {}) + #profileOf(id).eggs == after, players[id].attrs.LastNestClaimStatus)
            revealAll(players[id], {})
        else
            check("a ready nest exists after incubation " .. id, false, #list .. " nests")
        end
    end

    -- phase 8: goals panel counts
    local Goals = server.require(node("src/shared/GoalsRules"))
    local ProgressionConfig = server.require(node("src/shared/ProgressionConfig"))
    local EggGenetics = server.require(node("src/shared/EggGenetics"))
    local Http = server.game:GetService("HttpService")
    for _, id in ids do
        local p = players[id]
        local collection = Http:JSONDecode(PS.get(p, "CollectionJson"))
        local list = Repo.listDinosaurs(p, 0, 200)
        local counts = Goals.indexCounts(collection, Config.SpeciesOrder, function() return false end, list and list.dinosaurs, {colours = #ProgressionConfig.EggColors, patterns = #EggGenetics.Patterns, mutations = #ProgressionConfig.EventMutations})
        local ownedNow = 0
        for sid, e in profileOf(id).collection do if e.base + e.gold + (e.emerald or 0) + e.diamond > 0 then ownedNow += 1 end end
        check("goals: owned species match the profile " .. id, counts.owned == ownedNow and counts.found >= counts.owned and counts.total == #Config.SpeciesOrder, string.format("%d/%d vs %d", counts.owned, counts.found, ownedNow))
        check("goals: colours and patterns discovered from hatched dinos " .. id, counts.parts.colours.found >= 1 and counts.parts.patterns.found >= 1, counts.parts.colours.found .. "," .. counts.parts.patterns.found)
        local lines = Goals.lines({species = counts, dinos = list and list.dinosaurs, stages = {"base", "gold", "emerald", "diamond"}, speciesName = function(s) return s end, patternName = function(s) return s end})
        local fits = #lines == 3
        for _, l in lines do if #l.progress > Goals.MaxLine or #l.step > Goals.MaxLine then fits = false end end
        check("goals: three lines that fit the panel " .. id, fits)
        if id == 3001 then report(string.format("goals user 3001: %s | %s | %s", lines[1].progress, lines[2].progress, lines[3].progress)) end
    end

    -- phase 9: rejoin keeps the perk, crystals, nests and the UserId-keyed cooldowns
    local crystalsBefore = server.Rules.upgrade(profileOf(3004)).crystals
    local nestsBefore = #profileOf(3004).eggNests
    fire(env, "SetRevealSkip", p4, {1})
    local leftAt = now
    disconnect(env, p4)
    local p4b = connect(env, 3004)
    check("rejoined player loaded with a lease", p4b.loaded and profileOf(3004).session ~= nil)
    local waited = now - leftAt
    local skipBefore = profileOf(3004).revision
    fire(env, "SetRevealSkip", p4b, {2})
    sleep(1)
    check("rejoin inside the 1 s reveal-skip cooldown is still throttled (UserId keyed, BD-363)", waited >= 1 or profileOf(3004).revision == skipBefore, string.format("rejoin took %.2f s", waited))
    report(string.format("rejoin took %.2f virtual s (the 1 s reveal-skip cooldown %s)", waited, if waited < 1 then "was still running" else "had already passed"))
    check("rejoin keeps crystals", server.Rules.upgrade(profileOf(3004)).crystals == crystalsBefore, server.Rules.upgrade(profileOf(3004)).crystals .. " vs " .. crystalsBefore)
    check("rejoin keeps the nests", #profileOf(3004).eggNests == nestsBefore, #profileOf(3004).eggNests .. " vs " .. nestsBefore)
    if PLAYTEST.FastTravelPerk == true then
        check("rejoin keeps the Fast travel perk", server.require(node("src/shared/ProgressionRules")).hasPerk(server.Rules.upgrade(profileOf(3004)), "fastTravel"))
    else
        check("rejoin does not invent a Fast travel perk (flag off)", not server.require(node("src/shared/ProgressionRules")).hasPerk(server.Rules.upgrade(profileOf(3004)), "fastTravel"))
    end
    p4b.Character.root.Position = v3(0, 6, 580)
    sleep(2)
    local travel2 = env.Hub.handle(p4b, {station = hubStation})
    check("rail travel still works after the rejoin", travel2.ok == true, tostring(travel2.reason))
    -- the rare-hatch hatcher cooldown lives in server memory keyed by UserId and is forgotten on leave: a rejoin starts fresh.
    sleep(1)
    players[3004] = p4b

    -- phase 10: everyone leaves; nothing leaks
    for _, id in ids do disconnect(env, players[id]) end
    sleep(60)
    local runIds = {}
    for runId in env.runs do table.insert(runIds, runId) end
    local twice, uncommitted = 0, 0
    for _, runId in runIds do
        if (env.settleCalls[runId] or 0) > 1 then twice += 1 end
        if not env.committed[runId] then uncommitted += 1 end
    end
    check("no run settled twice (" .. #runIds .. " runs)", twice == 0, twice)
    check("every run settled (none lost)", uncommitted == 0, uncommitted)
    local dupEggs, leased = 0, 0
    for _, id in ids do
        local profile = profileOf(id)
        local seen = {}
        for _, e in profile.eggs do if seen[e.eggId] then dupEggs += 1 end seen[e.eggId] = true end
        for _, e in profile.runEggBank or {} do if seen[e.eggId] then dupEggs += 1 end seen[e.eggId] = true end
        local ops = {}
        for _, op in profile.recentOperations do
            if ops[op.id] then dupEggs += 1 end
            ops[op.id] = true
            if string.sub(op.id, 1, 4) == "run:" then
                local info = env.runs[string.sub(op.id, 5)]
                check("operation belongs to user " .. id, info ~= nil and info.userId == id, op.id)
            end
        end
        if profile.session then leased += 1 end
    end
    check("no duplicated egg id or operation id", dupEggs == 0, dupEggs)
    check("every lease released after everyone left", leased == 0, leased)
    check("leave coordinator idle", env.leaving.pending == 0, env.leaving.pending)
    check("no DataStore throttle-queue drop", M.queueDrops == 0, M.queueDrops)

    -- privacy: private values only ever go to their owner, and never become public attributes
    local Core = server.require(node("src/shared/PrivateStateCore"))
    local allRunIds = {}
    for _, runId in runIds do table.insert(allRunIds, {runId = runId, userId = env.runs[runId].userId}) end
    local snapshots, leakedPrivate, foreignRun = 0, 0, 0
    for _, f in server.fired do
        if f.remote == "PrivateState" then
            snapshots += 1
            for _, r in allRunIds do
                if r.userId ~= f.to.UserId and containsString(f.msg, r.runId) then foreignRun += 1 end
            end
        end
    end
    check("owner-only messages were sent (" .. snapshots .. ")", snapshots >= 8, snapshots)
    check("no owner-only message contains another player's run or egg id", foreignRun == 0, foreignRun)
    for _, id in ids do
        local p = players[id]
        for k, v in p.attrs do
            if Core.isPrivate(k) then leakedPrivate += 1 end
            if type(v) == "string" and (string.sub(v, 1, 4) == "run:" or string.sub(v, 1, 5) == "nest:") then leakedPrivate += 1 end
        end
    end
    check("no private name or egg id is a public Player attribute", leakedPrivate == 0, leakedPrivate)

    -- telemetry (BD-426): one run_end per settled run, session_end per leaver, anonymous, whitelisted
    local runEnds, sessionEnds, badLine, visits = 0, 0, 0, 0
    local eventLines, serverIds = {}, {}
    for _, line in captured do
        if string.sub(line, 1, 15) == "[BD-TELEMETRY] " then
            table.insert(eventLines, line)
            if string.find(line, '"event":"run_end"', 1, true) then runEnds += 1 end
            if string.find(line, '"event":"session_end"', 1, true) then sessionEnds += 1 end
            -- BD-653: the unix time and the random 8-hex server id are numbers that can contain "300" by chance, so they are masked first
            local scan = string.gsub(string.gsub(line, '"at":%d+', '"at":0'), '"server":"%w+"', '"server":"x"')
            if string.find(scan, "300%d") or string.find(scan, "P300") or string.find(scan, "Friend") or string.find(scan, "run:") then badLine += 1 end
            if string.find(line, '"event":"visit"', 1, true) then visits += 1 end
            local id = string.match(line, '"server":"(%w+)"')
            if id then serverIds[id] = true end
        end
    end
    local serverCount = 0
    for _ in serverIds do serverCount += 1 end
    check("telemetry (BD-653): a visit line at every join (4 + the rejoin), one random server id on all of them", visits == 5 and serverCount == 1, visits .. " visits, " .. serverCount .. " server ids")
    check("telemetry: one run_end per settled run", runEnds == #runIds, runEnds .. " vs " .. #runIds)
    check("telemetry: a session_end for every leaver (4 + the rejoin)", sessionEnds == 5, sessionEnds)
    check("telemetry: no user id, name or egg id in any line", badLine == 0, badLine)
    local reasons = {}
    for _, line in eventLines do local r = string.match(line, '"reason":"(%w+)"') if r then reasons[r] = (reasons[r] or 0) + 1 end end
    check("telemetry: both exit-home and eaten reasons appear", (reasons.ManualExit or 0) >= 6 and (reasons.Predation or 0) == 1, (reasons.ManualExit or 0) .. "/" .. (reasons.Predation or 0))
    report(string.format("telemetry: %d lines, %d run_end, %d session_end, reasons ManualExit %d, Predation %d", #eventLines, runEnds, sessionEnds, reasons.ManualExit or 0, reasons.Predation or 0))

    -- no errors: every warning is accounted for
    local unexpected = {}
    for _, w in warnings do table.insert(unexpected, w) end
    check("no warnings or errors from the real modules", #unexpected == 0, table.concat(unexpected, " | "):sub(1, 400))
    report(string.format("DataStore: %d writes, %d throttled, peak window ok; warnings %d", M.writes, M.throttled, #warnings))
end)

local failed = 0
for _, c in CHECKS do
    if not c.ok then failed += 1 end
    print(string.format("CHECK|%s|%s|%s", if c.ok then "PASS" else "FAIL", c.name, c.detail))
end
for _, line in REPORT do print("REPORT|" .. line) end
print(string.format("DONE|%d|%d", #CHECKS, failed))
