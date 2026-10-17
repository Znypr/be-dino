-- BD-319 round 2: cross-player cases for 2, 4 and 8 simulated players. Spliced by tools/verify_multiplayer_sim.py into
-- multiplayer_sim.luau just before its report section, so it shares the scheduler, the DataStore mock and the helpers
-- (runScenario, connect, startRun, disconnect, profileOf, eggIdsOf, check, metric, sleep, now). Every block is wrapped in
-- do ... end / a function so it adds no top-level locals (Luau allows 200 per function).
--
-- OFFLINE: real ProfileRepository, RunLifecycle, PrivateState, PrivateStateCore, Dinosaur, AdminService and the pure shared
-- rules run against mocks. Nothing here proves replication, networking, physics, rendering or a frame time; docs/111 s5.6
-- lists what only a live Local Server with 4 players can show.
--
--   P  owner-only state never reaches another client (PrivateState channel, Player and Character attributes)
--   S  settlement exactly once per player when several settle in the SAME tick, and equal to the same player alone
--   W  the nest weather ledger is kept per run / per player (BD-479)
--   H  the cave hub is exactly 1x for the player inside it and nobody else (BD-480)
--   A  admin Mutation chance x10 is set only by the admin, applies to the admin's own catches only (everyone else rolls x1),
--      is cleared when the admin leaves, stays in server memory and never reaches a profile (BD-237, docs/115)
--   C  per-client caps (contact shadows, effects LOD, FX pool, moment rim) are counted per client, never across players

local CROSS_COUNTS = {2, 4, 8}
local function crossIds(n, base)
    local t = {}
    for i = 1, n do t[i] = base + i end
    return t
end
local function crossContains(value, needle, seen)
    if type(value) == "string" then return value == needle end
    if type(value) == "table" then
        seen = seen or {}
        if seen[value] then return false end -- the mock Player and Character tables point at each other
        seen[value] = true
        for k, v in value do
            if crossContains(k, needle, seen) or crossContains(v, needle, seen) then return true end
        end
    end
    return false
end

-------------------------------------------------------------------- S: several players settle in the same tick
do
    -- What one player alone gets for `catches` catches over `seconds` (reference for the concurrent run).
    local function aloneSignature(id, catches, seconds)
        local out
        runScenario("alone-reference-" .. id, 700, function(env, server)
            local p = connect(env, id)
            local runId = startRun(env, p, catches)
            sleep(seconds)
            env.RL.tryEnd(p, p.Character, "ManualExit")
            sleep(30)
            local profile = profileOf(id)
            local _, eggs = eggIdsOf(profile)
            local progress = server.Rules.upgrade(profile)
            out = string.format("%d|%d|%d|%d", eggs, progress.crystals, progress.accountXP, #(profile.eggNests or {}))
            out = out .. "|" .. tostring(env.settleCalls[runId])
        end)
        return out
    end

    for _, n in CROSS_COUNTS do
        local ids = crossIds(n, 5100 + n * 10)
        local players, runIds, catches, modes, firedAt = {}, {}, {}, {}, {}
        local alone = {} -- the same runs, one player at a time (runScenario resets the store, so do this first)
        for i, id in ids do alone[i] = aloneSignature(id, 8 + i * 6, 145) end
        local env, server = runScenario("same-tick-settle-" .. n, 900, function(env, server)
            for i, id in ids do task.spawn(function() players[i] = connect(env, id) end) end
            sleep(30)
            for i, p in players do
                catches[i] = 8 + i * 6
                runIds[i] = startRun(env, p, catches[i])
            end
            sleep(server.Config.NestMinRunSeconds + 20) -- long enough for a nest
            local barrier = now + 5
            for i, p in players do
                modes[i] = (i - 1) % 4
                task.spawn(function()
                    sleep(barrier - now) -- every player wakes up in the SAME virtual tick
                    firedAt[i] = now
                    local c = p.Character
                    if modes[i] == 0 then
                        env.RL.tryEnd(p, c, "ManualExit") env.RL.tryEnd(p, c, "ManualExit")
                    elseif modes[i] == 1 then
                        c.humanoid.Health = 0 env.RL.tryEnd(p, c, "Death")
                    elseif modes[i] == 2 then
                        env.RL.tryEnd(p, c, "Eaten", 1) env.RL.tryEnd(p, c, "ManualExit")
                    else
                        disconnect(env, p) -- leave in the same tick
                    end
                end)
            end
            sleep(80)
        end)
        local seenEgg = {}
        local cross = 0
        local sameTick = true
        for i = 1, n do if firedAt[i] ~= firedAt[1] then sameTick = false end end
        check(n .. " players: all " .. n .. " end/leave actions ran in the same virtual tick", sameTick and firedAt[1] ~= nil, tostring(firedAt[1]) .. ".." .. tostring(firedAt[n]))
        for i, id in ids do
            local runId = runIds[i]
            check(n .. " players: player " .. i .. " settled exactly once", runId ~= nil and env.settleCalls[runId] == 1, tostring(runId and env.settleCalls[runId]))
            local committed = env.committed[runId]
            check(n .. " players: player " .. i .. " run committed under its own user id", committed ~= nil and committed.userId == id, "")
            local profile = profileOf(id)
            local mine, count = eggIdsOf(profile)
            local expected = server.require(node("src/server/RewardMath")).computeRunReward(catches[i], 0).eggCount
            check(n .. " players: player " .. i .. " got exactly its own eggs", count == expected, count .. " vs " .. expected)
            for eggId in mine do
                if seenEgg[eggId] and seenEgg[eggId] ~= id then cross += 1 end
                seenEgg[eggId] = id
            end
            for _, nest in profile.eggNests or {} do
                if nest.droppedFromRun ~= runId then cross += 1 end
            end
            local wantNests = math.min(server.Config.NestStorageCapacity, server.require(node("src/server/RewardMath")).nestCount(catches[i], 145))
            check(n .. " players: player " .. i .. " got exactly its own " .. wantNests .. " nest(s)", wantNests > 0 and #(profile.eggNests or {}) == wantNests, tostring(#(profile.eggNests or {})))
            for _, op in profile.recentOperations do
                local info = env.runs[string.sub(op.id, 5)]
                if info == nil or info.userId ~= id then cross += 1 end
            end
            -- the same player alone gets the same result (concurrency changed nothing)
            local progress = server.Rules.upgrade(profile)
            local signature = string.format("%d|%d|%d|%d|1", count, progress.crystals, progress.accountXP, #(profile.eggNests or {}))
            check(n .. " players: player " .. i .. " result equals the same run alone", signature == alone[i], signature .. " vs " .. tostring(alone[i]))
        end
        currentScenario = "same-tick-settle-" .. n
        check(n .. " players: no egg, nest or operation belongs to two players", cross == 0, tostring(cross) .. " crossings")
        check(n .. " players: leave coordinator idle", env.leaving.pending == 0, tostring(env.leaving.pending))
        local left = 0
        for i, id in ids do if modes[i] == 3 and profileOf(id).session ~= nil then left += 1 end end
        check(n .. " players: players that left in that tick released their lease", left == 0, tostring(left))
    end
end

-------------------------------------------------------------------- W: nest weather ledger per player (BD-479)
do
    -- Global weather by absolute virtual second; players start at different times so their nests are found in different weather.
    local function weatherAt(t)
        if t < 150 then return "rain" elseif t < 260 then return nil elseif t < 360 then return "thunder" elseif t < 460 then return "blizzard" end
        return "aurora"
    end
    for _, n in CROSS_COUNTS do
        local ids = crossIds(n, 5300 + n * 10)
        local players, runIds, expected = {}, {}, {}
        local env, server = runScenario("nest-weather-" .. n, 1500, function(env, server)
            server.workspace.GetAttribute = function(_, key) if key == "WeatherId" then return weatherAt(now) end return nil end
            for i, id in ids do task.spawn(function() players[i] = connect(env, id) end) end
            sleep(20)
            local minSeconds = server.Config.NestMinRunSeconds
            for i, p in players do
                task.spawn(function()
                    sleep((i - 1) * 37) -- different start moments, different weather in the run
                    local c = p.Character
                    runIds[i] = startRun(env, p, 0)
                    local t0 = now
                    sleep(15)
                    c:SetAttribute("CatchScore", 5) env.RL.noteNestWeather(c) -- before the minimum time: no nest yet
                    sleep(minSeconds + 0.5 - 15) -- the begin() timer notes nest 1 at minSeconds + 0.25
                    local ledger = {weatherAt(t0 + minSeconds + 0.25)}
                    sleep(60)
                    c:SetAttribute("CatchScore", 36) env.RL.noteNestWeather(c) ledger[2] = weatherAt(now)
                    sleep(90)
                    c:SetAttribute("CatchScore", 70) env.RL.noteNestWeather(c) ledger[3] = weatherAt(now)
                    sleep(60)
                    expected[i] = {ledger = ledger, settledIn = weatherAt(now)}
                    env.RL.tryEnd(p, c, "ManualExit")
                end)
            end
            sleep(1400)
        end)
        local different, legacyMismatch = 0, 0
        local firstKey
        for i, id in ids do
            local info = expected[i]
            local profile = profileOf(id)
            local byId = {}
            for _, nest in profile.eggNests or {} do byId[nest.nestId] = nest end
            local ok, detail = info ~= nil, ""
            if ok then
                local Rewards = server.require(node("src/server/RewardMath"))
                for j = 1, 3 do
                    local nest = byId[Rewards.nestId(runIds[i], j)]
                    local want = info.ledger[j]
                    if nest == nil or nest.weatherId ~= want then
                        ok = false
                        detail = detail .. string.format(" nest%d got %s want %s;", j, tostring(nest and nest.weatherId), tostring(want))
                    end
                    if want ~= info.settledIn then legacyMismatch += 1 end
                end
                local key = tostring(info.ledger[1]) .. "/" .. tostring(info.ledger[2]) .. "/" .. tostring(info.ledger[3])
                if firstKey == nil then firstKey = key elseif key ~= firstKey then different += 1 end
            end
            check(n .. " players: player " .. i .. " nests carry the weather they were FOUND in, from their own run", ok and #(profile.eggNests or {}) == 3, detail)
            check(n .. " players: player " .. i .. " settled once", env.settleCalls[runIds[i]] == 1, tostring(env.settleCalls[runIds[i]]))
        end
        currentScenario = "nest-weather-" .. n
        check(n .. " players: the players' ledgers really differ from each other (test is not vacuous)", different > 0, tostring(different))
        check(n .. " players: some nest differs from the settlement weather (the old behaviour would fail)", legacyMismatch > 0, tostring(legacyMismatch))
    end
end


-------------------------------------------------------------------- P: owner-only state, through the real PrivateState channel
do
    for _, n in CROSS_COUNTS do
        local ids = crossIds(n, 5500 + n * 10)
        local sent, caches, players, markers, counts = {}, {}, {}, {}, {}
        local rejoined
        local env, server = runScenario("private-state-" .. n, 1500, function(env, server)
            local Core = server.require(node("src/shared/PrivateStateCore"))
            server.workspace.GetAttribute = function(_, key) if key == "WeatherId" then return "rain" end return nil end -- every nest carries a weather
            local channel
            local makeInstance = server.Instance.new
            server.Instance.new = function(className)
                local o = makeInstance(className)
                if className == "RemoteEvent" then
                    channel = o
                    function o:FireClient(target, message) -- what the engine would deliver to ONE client
                        sent[target] = sent[target] or {}
                        table.insert(sent[target], message)
                    end
                end
                return o
            end
            env.PS.start()
            local function hello(p) caches[p] = caches[p] or {cache = Core.newCache(), cursor = 0} channel.OnServerEvent.fns[1](p) end
            local function pump() -- each client applies only what was delivered to it
                for p, list in sent do
                    local c = caches[p]
                    while c and c.cursor < #list do
                        c.cursor += 1
                        local _, err = Core.apply(c.cache, list[c.cursor])
                        if err == "gap" then hello(p) end
                    end
                end
            end
            for i, id in ids do task.spawn(function() players[i] = connect(env, id) hello(players[i]) end) end
            sleep(30)
            for i, p in players do
                task.spawn(function()
                    local c = i + 1 -- 2..9 eggs: all in the first hatch page, so the buffer holds i eggs after the first claim
                    startRun(env, p, c)
                    sleep(130) -- long enough for a nest, found in rain
                    env.RL.noteNestWeather(p.Character)
                    env.RL.tryEnd(p, p.Character, "ManualExit")
                    sleep(30)
                    env.Repo.claimChest(p, env.PS.get(p, "NextChestId"))
                    sleep(5)
                end)
            end
            sleep(250)
            pump()
            for i, p in players do
                local set = {}
                for key in eggIdsOf(profileOf(ids[i])) do set[key] = true end
                for _, nest in profileOf(ids[i]).eggNests or {} do set[nest.nestId] = true end
                for _, name in {"NextChestId", "LastClaimedChestId"} do
                    local v = env.PS.get(p, name)
                    if type(v) == "string" and v ~= "" then set[v] = true end
                end
                markers[i] = set
            end
            for i, p in players do counts[i] = #(sent[p] or {}) end
            -- a client says hello again: only ITS queue grows
            sleep(1)
            hello(players[1])
            pump()
            counts.afterHello = {}
            for i, p in players do counts.afterHello[i] = #(sent[p] or {}) end
            -- the same user rejoins as a NEW Player object: a fresh snapshot of its own state only
            disconnect(env, players[1])
            sleep(30)
            rejoined = connect(env, ids[1])
            hello(rejoined)
            sleep(2)
            pump()
            counts.afterRejoin = {}
            for i, p in players do counts.afterRejoin[i] = #(sent[p] or {}) end
        end)
        local Core = server.require(node("src/shared/PrivateStateCore"))
        local buffered, distinct, ownOk = {}, 0, 0
        for i, p in players do
            local cacheValue = caches[p] and caches[p].cache.values.BufferedRevealCount
            if cacheValue == i then ownOk += 1 end
            if cacheValue ~= nil then buffered[cacheValue] = true end
        end
        for _ in buffered do distinct += 1 end
        currentScenario = "private-state-" .. n
        check(n .. " players: every client holds its OWN BufferedRevealCount (2.." .. (n + 1) .. " eggs, first claim done)", ownOk == n, ownOk .. "/" .. n)
        check(n .. " players: the buffered counts differ per player, so a mix-up would show", distinct == n, tostring(distinct))
        local nonEmpty, leaks, wrongNames, sawOwn = 0, 0, 0, 0
        for j, pj in players do
            local list = sent[pj] or {}
            if #list > 0 then nonEmpty += 1 end
            for _, message in list do
                for name in (message.d or {}) do if not Core.isPrivate(name) then wrongNames += 1 end end
                for _, name in message.o or {} do if not Core.isPrivate(name) then wrongNames += 1 end end
            end
            for i = 1, n do
                for marker in markers[i] or {} do
                    local has = crossContains(list, marker)
                    if i == j and has then sawOwn += 1 end
                    if i ~= j and has then leaks += 1 end
                end
            end
        end
        check(n .. " players: every client received its own private snapshot (test is not vacuous)", nonEmpty == n and sawOwn > 0, nonEmpty .. " clients, " .. sawOwn .. " own markers")
        check(n .. " players: no private value of one player was delivered to another client", leaks == 0, leaks .. " leaked values")
        check(n .. " players: the channel carries only names classified private", wrongNames == 0, tostring(wrongNames))
        local publicBad, ledgerNames = 0, 0
        local function scan(attrs)
            for name, value in attrs do
                if Core.isPrivate(name) then publicBad += 1 end
                if string.find(name, "Weather") and (string.find(name, "Nest") or string.find(name, "Ledger")) then ledgerNames += 1 end
                for i = 1, n do for marker in markers[i] or {} do if crossContains(value, marker) then publicBad += 1 end end end
            end
        end
        for _, p in players do
            scan(p.attrs)
            if p.Character then scan(p.Character.attrs) end
        end
        check(n .. " players: no private name or private value on any Player or Character attribute (these replicate to everybody)", publicBad == 0, tostring(publicBad))
        check(n .. " players: the nest weather ledger is not published under any attribute name", ledgerNames == 0, tostring(ledgerNames))
        local allMessages = {}
        for _, list in sent do for _, message in list do table.insert(allMessages, message) end end
        check(n .. " players: no message carries a nest weather id (summary holds id, size, luck, state, readyAt only)", not crossContains(allMessages, "weatherId"), "")
        local others = true
        for i = 2, n do if (counts.afterHello or {})[i] ~= counts[i] then others = false end end
        check(n .. " players: one client's hello sends a snapshot to that client only", (counts.afterHello or {})[1] == counts[1] + 1 and others, tostring((counts.afterHello or {})[1]) .. " vs " .. tostring(counts[1]))
        local rejoinOthers = true
        for i = 2, n do if (counts.afterRejoin or {})[i] ~= (counts.afterHello or {})[i] then rejoinOthers = false end end
        local fresh = rejoined and caches[rejoined] and caches[rejoined].cache.values
        local foreign = 0
        for i = 2, n do for marker in markers[i] or {} do if crossContains(fresh or {}, marker) then foreign += 1 end end end
        check(n .. " players: a rejoin (new Player object) gets a snapshot of its own state, nothing from the others and nothing sent to them", rejoinOthers and fresh ~= nil and foreign == 0 and fresh.BufferedRevealCount == 0, tostring(fresh and fresh.BufferedRevealCount) .. ", foreign " .. foreign)
        local setPublic = pcall(function() env.PS.set(players[1], "Location", "x") end)
        check(n .. " players: a public name cannot be pushed through the private channel", setPublic == false, "")
    end
end

-------------------------------------------------------------------- H: cave hub is exactly 1x for the player inside it and for nobody else (BD-480)
do
    local function hubScenario(n, caveHub)
        local label = "hub-scale-" .. (if caveHub then "on-" else "off-") .. n
        SCENARIO_OVERRIDES = if caveHub then {CaveHub = true} else nil
        local result = {}
        runScenario(label, 60, function(env, server)
            local renders = {}
            server.cache["src/shared/DinosaurVisual"] = {render = function(character, scale)
                character:SetAttribute("VisualScale", scale)
                renders[character] = (renders[character] or 0) + 1
            end}
            local original = server.game.GetService
            server.game.GetService = function(self, id)
                if id == "PhysicsService" then
                    return {IsCollisionGroupRegistered = function() return true end, RegisterCollisionGroup = function() end, CollisionGroupSetCollidable = function() end}
                end
                return original(self, id)
            end
            local Dino = server.require(node("src/server/Dinosaur"))
            local Hub = server.require(node("src/shared/HubScaleRules"))
            local Layout = server.require(node("src/shared/CaveHubLayout"))
            local hub = Layout.hub(server.Config)
            local function newDino(x, z, growth, big)
                local c = {attrs = {RunState = "Active", DinoAttached = true, GrowthScore = growth, BigDinosaur = big}}
                local root = {Position = {X = x, Y = 0, Z = z}}
                function root:IsA(className) return className == "BasePart" end
                function c:GetAttribute(k) return self.attrs[k] end
                function c:SetAttribute(k, v) self.attrs[k] = v end
                function c:FindFirstChild(name) if name == "HumanoidRootPart" then return root end return nil end
                function c:FindFirstChildOfClass() return nil end -- no Humanoid or collider: placeCollider returns at once
                return c, root
            end
            local chars, roots, inHubNow = {}, {}, {}
            for i = 1, n do
                inHubNow[i] = i % 2 == 1
                local x, z = if inHubNow[i] then hub.centerX + (i - 1) else 240, if inHubNow[i] then hub.centerZ else 40 * i
                chars[i], roots[i] = newDino(x, z, 300 + 90 * i, i % 3 ~= 0) -- some BIG, all different growth
                Dino.syncScale(chars[i])
            end
            local function expected(i, hubNow)
                local c = chars[i]
                local island = Hub.islandScale(c.attrs.GrowthScore, c.attrs.BigDinosaur, server.Config.BigScaleMultiplier)
                return if caveHub and hubNow then 1 else island
            end
            result.firstOk, result.growOk, result.moveOk, result.untouched = 0, 0, 0, true
            for i = 1, n do if math.abs(chars[i].attrs.VisualScale - expected(i, inHubNow[i])) < 1e-6 then result.firstOk += 1 end end
            -- everybody grows: the hub player stays at 1, nobody else is affected by it
            for i = 1, n do Dino.addGrowth(chars[i], 400) end
            for i = 1, n do if math.abs(chars[i].attrs.VisualScale - expected(i, inHubNow[i])) < 1e-6 then result.growOk += 1 end end
            -- player 1 (in the hub) walks out, player 2 (island) walks in; the others are not re-rendered
            local before = {}
            for i = 3, n do before[i] = renders[chars[i]] end
            roots[1].Position.X, roots[1].Position.Z = 240, 40
            roots[2].Position.X, roots[2].Position.Z = hub.centerX, hub.centerZ
            inHubNow[1], inHubNow[2] = false, true
            Dino.syncScale(chars[1]) Dino.syncScale(chars[2])
            for i = 1, 2 do if math.abs(chars[i].attrs.VisualScale - expected(i, inHubNow[i])) < 1e-6 then result.moveOk += 1 end end
            for i = 3, n do if renders[chars[i]] ~= before[i] then result.untouched = false end end
            result.growthKept = chars[1].attrs.GrowthScore > 300 + 90 -- leaving the hub gives the run's own size back
            result.hubSizes = {}
            for i = 1, n do if caveHub and inHubNow[i] then table.insert(result.hubSizes, chars[i].attrs.VisualScale) end end
        end)
        currentScenario = label
        local tag = n .. " players, hub " .. (if caveHub then "ON" else "OFF")
        check(tag .. ": first sizes are right (hub player 1x, island players growth x BIG)", result.firstOk == n, result.firstOk .. "/" .. n)
        check(tag .. ": everybody grows, the hub player stays 1x", result.growOk == n, result.growOk .. "/" .. n)
        check(tag .. ": one player leaving and one entering the hub change only themselves", result.moveOk == 2 and result.untouched == true and result.growthKept == true, tostring(result.moveOk) .. " " .. tostring(result.untouched))
        if caveHub then
            local allOne = #result.hubSizes > 0
            for _, size in result.hubSizes do if size ~= 1 then allOne = false end end
            check(tag .. ": every dinosaur inside the hub is exactly 1", allOne, table.concat(result.hubSizes, ","))
        end
    end
    for _, n in CROSS_COUNTS do
        hubScenario(n, true)
        hubScenario(n, false)
    end
end

-------------------------------------------------------------------- A: admin "Mutation chance x10" (BD-237) with several players
do
    Enum = Enum or {CreatorType = {User = {Name = "User"}, Group = {Name = "Group"}}}
    for _, n in CROSS_COUNTS do
        local ids = crossIds(n, 5900 + n * 10)
        local R = {calls = {food = {}, mutation = {}, weatherStart = {}, weatherStop = 0}, published = {}, answers = {}}
        SCENARIO_OVERRIDES = {AdminPanelEnabled = true}
        local env, server = runScenario("admin-x10-" .. n, 900, function(env, server)
            local players = {}
            server.game.CreatorType = Enum.CreatorType.User
            server.game.CreatorId = ids[1] -- the first player owns the experience, so only they are an admin
            -- FoodService itself needs Color3 and the art models, so this stub mirrors its four one-line Mutation chance wrappers over the
            -- real shared AdminMutationScale book (verify_multiplayer_sim / verify_admin pin the wrappers and the catch-roll call by source).
            local Scale = server.require(node("src/shared/AdminMutationScale"))
            local book = Scale.new()
            local Food = {
                setAdminFoodMultiplier = function(v) table.insert(R.calls.food, v) end,
                setAdminMutationMultiplier = function(player, v) Scale.set(book, player, v) end,
                clearAdminMutationMultiplier = function(player) Scale.clear(book, player) end,
                clearAllAdminMutationMultipliers = function() Scale.clearAll(book) end,
                adminMutationScale = function(player) return Scale.get(book, player) end,
            }
            server.cache["src/server/FoodService"] = Food
            server.cache["src/server/ProgressionService"] = {
                setAdminMultipliers = function() end,
                adminStartWeather = function(id, seconds) table.insert(R.calls.weatherStart, {id, seconds}) return id == "rain" end,
                adminStopWeather = function() R.calls.weatherStop += 1 end,
            }
            local makeInstance = server.Instance.new
            local remote
            server.Instance.new = function(className)
                local o = makeInstance(className)
                if className == "RemoteFunction" then remote = o end
                return o
            end
            server.workspace.SetAttribute = function(_, k, v) R.published[k] = v end
            for i, id in ids do task.spawn(function() players[i] = connect(env, id) end) end
            sleep(30)
            local Odds = server.require(node("src/shared/EggOutcomeOdds"))
            local Rules = server.require(node("src/shared/ProgressionRules"))
            local function oddsSample() return deepCopy({Odds.catalog(0, nil).count, Odds.catalog(0, nil).at(1), Rules.eventEgg("rain", 0.1, nil)}) end
            local oddsBefore = oddsSample()
            server.require(node("src/server/AdminService")).start()
            sleep(2)
            R.startScales = {}
            for i, p in players do R.startScales[i] = Food.adminMutationScale(p) end
            R.isAdmin = {}
            for i, p in players do R.isAdmin[i] = p.attrs.IsAdmin end
            local function invoke(p, ...) return remote.OnServerInvoke(p, ...) end
            -- every player sets Mutation chance to x10 in the same tick
            local answers = {}
            for i, p in players do task.spawn(function() answers[i] = {invoke(p, "set", "mutationChanceMultiplier", 10)} end) end
            sleep(1)
            R.answers.set = answers
            R.afterSet = {}
            for i, p in players do R.afterSet[i] = Food.adminMutationScale(p) end
            -- one earned weather egg per player at a roll that only the boosted chance hits (rain is 2%; x10 is 20%)
            local Tags = server.require(node("src/shared/RunEggTags"))
            local rainChance = Rules.item(server.require(node("src/shared/ProgressionConfig")).Weather, "rain").chance
            R.eggRolls = {}
            for i, p in players do
                local _, hits = Tags.apply({}, "rain", 0, 1, function() return rainChance * 5 end, Food.adminMutationScale(p))
                R.eggRolls[i] = hits
            end
            -- non-admins try everything else
            sleep(1)
            R.others = {}
            for i = 2, n do
                R.others[i] = {
                    reset = {invoke(players[i], "reset")}, weather = {invoke(players[i], "startWeather", "rain", 60)},
                    stop = {invoke(players[i], "stopWeather")}, gravity = {invoke(players[i], "set", "gravity", 150)},
                }
                sleep(0.2)
            end
            R.state = {mutation = (function() local m = 0 for i = 2, n do m += Food.adminMutationScale(players[i]) - 1 end return m end)(), weather = #R.calls.weatherStart, stop = R.calls.weatherStop, gravity = R.published.Admin_gravity}
            -- the admin: out-of-range and bad values are clamped or refused; a too-fast second request is busy
            sleep(1) R.clamp = {invoke(players[1], "set", "mutationChanceMultiplier", 99)}
            sleep(1) R.low = {invoke(players[1], "set", "mutationChanceMultiplier", 0)}
            sleep(1) R.nan = {invoke(players[1], "set", "mutationChanceMultiplier", 0 / 0)}
            sleep(1) R.unknown = {invoke(players[1], "set", "bogus", 3)}
            R.scaleAfterLow = Food.adminMutationScale(players[1]) -- the "0" request above clamped to x1 (cleared)
            sleep(1) invoke(players[1], "set", "mutationChanceMultiplier", 10)
            R.busy = {invoke(players[1], "set", "mutationChanceMultiplier", 5)}
            sleep(1)
            -- eggs are earned and settled with x10 up; nothing about it may be stored on any profile
            for _, p in players do startRun(env, p, 12) end
            sleep(30)
            for _, p in players do env.RL.tryEnd(p, p.Character, "ManualExit") end
            sleep(40)
            R.oddsSame = deepEqual(oddsBefore, oddsSample())
            R.scalesAtSettle = {}
            for i, p in players do R.scalesAtSettle[i] = Food.adminMutationScale(p) end
            -- the creator leaves: the old Player can no longer use the panel; a new join of a non-admin stays a non-admin
            local old = players[1]
            for _, f in server.PlayersService.PlayerRemoving.fns do task.spawn(f, old) end
            old.Parent = nil
            local at = table.find(server.players, old)
            if at then table.remove(server.players, at) end
            sleep(30)
            R.scaleAfterLeave = Food.adminMutationScale(old)
            R.displayAfterLeave = R.published.Admin_mutationChanceMultiplier
            R.afterLeave = {invoke(old, "set", "foodMultiplier", 10)}
            local late = connect(env, ids[n] + 500)
            for _, f in server.PlayersService.PlayerAdded.fns do task.spawn(f, late) end
            sleep(2)
            R.lateAdmin = late.attrs.IsAdmin
            local back = connect(env, ids[1])
            for _, f in server.PlayersService.PlayerAdded.fns do task.spawn(f, back) end
            sleep(2)
            R.rejoinAdmin = back.attrs.IsAdmin
            R.rejoinScaleBefore = Food.adminMutationScale(back)
            R.lateScale = Food.adminMutationScale(late)
            R.rejoinAnswer = {invoke(back, "set", "mutationChanceMultiplier", 3)}
            R.rejoinScale = Food.adminMutationScale(back)
            R.othersAfterRejoin = {}
            for i = 2, n do R.othersAfterRejoin[i] = Food.adminMutationScale(players[i]) end
        end)
        local tag = n .. " players: "
        check(tag .. "only the experience owner is an admin (IsAdmin hint)", R.isAdmin ~= nil and R.isAdmin[1] == true and (function() for i = 2, n do if R.isAdmin[i] ~= false then return false end end return true end)(), "")
        local nonAdminRefused = true
        for i = 2, n do local a = R.answers.set and R.answers.set[i] if not a or a[1] ~= false or a[2] ~= "not_admin" then nonAdminRefused = false end end
        check(tag .. "every non-admin who sets Mutation chance x10 is refused (not_admin)", nonAdminRefused and R.answers.set and R.answers.set[1][1] == true, "")
        local othersX1 = true
        for i = 2, n do if R.afterSet[i] ~= 1 or R.startScales[i] ~= 1 or R.scalesAtSettle[i] ~= 1 or R.othersAfterRejoin[i] ~= 1 then othersX1 = false end end
        check(tag .. "x10 belongs to the admin's own catches only (scale 10 for the admin, 1 for every other player) and is published for display", R.startScales[1] == 1 and R.afterSet[1] == 10 and othersX1 and R.published.Admin_mutationChanceMultiplier ~= nil, tostring(R.afterSet[1]) .. "/" .. tostring(R.afterSet[2]))
        local othersMiss = true
        for i = 2, n do if R.eggRolls[i] ~= 0 then othersMiss = false end end
        check(tag .. "with x10 up the admin's weather egg mutates at the roll that every non-admin's egg (x1) misses", R.eggRolls[1] == 1 and othersMiss, tostring(R.eggRolls[1]) .. "/" .. tostring(R.eggRolls[2]))
        check(tag .. "the admin's own request for x1 clears their scale (back to the shipped chance)", R.scaleAfterLow == 1, tostring(R.scaleAfterLow))
        local refusedAll = true
        for i = 2, n do for _, k in {"reset", "weather", "stop", "gravity"} do local a = R.others[i][k] if a[1] ~= false or a[2] ~= "not_admin" then refusedAll = false end end end
        check(tag .. "non-admins cannot reset, start or stop weather or change gravity, and nothing moved", refusedAll and R.state.mutation == 0 and R.state.weather == 0 and R.state.stop == 0 and R.state.gravity == 250, "")
        check(tag .. "admin value 99 is clamped to 10, 0 to 1; NaN and an unknown key are refused", R.clamp[1] == true and R.clamp[2] == "x10" and R.low[2] == "x1" and R.nan[1] == false and R.unknown[1] == false, tostring(R.clamp[2]) .. "/" .. tostring(R.low[2]) .. "/" .. tostring(R.nan[2]) .. "/" .. tostring(R.unknown[2]))
        check(tag .. "a second request inside 0.15 s is busy", R.busy[1] == false and R.busy[2] == "busy", tostring(R.busy[2]))
        local stored = 0
        local function scanKeys(value)
            if type(value) ~= "table" then return end
            for k, v in value do
                if type(k) == "string" then
                    local low = string.lower(k)
                    if string.find(low, "admin", 1, true) or string.find(low, "mutationchance", 1, true) then stored += 1 end
                end
                scanKeys(v)
            end
        end
        for _, id in ids do scanKeys(profileOf(id)) end
        check(tag .. "no profile stores any admin value, also after settling runs with x10 up", stored == 0, tostring(stored))
        check(tag .. "x10 changes nothing a player is shown (odds catalog, event egg chance at the shipped scale)", R.oddsSame == true, "")
        check(tag .. "when the admin leaves their scale is cleared and the display falls back to x1; a new join (non-admin or the rejoined owner) starts at x1, and no other player changed", R.scaleAfterLeave == 1 and R.displayAfterLeave == 1 and R.lateScale == 1 and R.rejoinScaleBefore == 1 and R.rejoinScale == 3, tostring(R.scaleAfterLeave) .. "/" .. tostring(R.displayAfterLeave) .. "/" .. tostring(R.lateScale) .. "/" .. tostring(R.rejoinScaleBefore) .. "/" .. tostring(R.rejoinScale))
        check(tag .. "after the owner left their old Player is refused, a new non-admin join is not an admin, the owner is admin again on rejoin", R.afterLeave and R.afterLeave[2] == "not_admin" and R.lateAdmin == false and R.rejoinAdmin == true and R.rejoinAnswer[1] == true, tostring(R.afterLeave and R.afterLeave[2]) .. "/" .. tostring(R.lateAdmin) .. "/" .. tostring(R.rejoinAdmin))
    end
end

-------------------------------------------------------------------- C: caps are counted per client (contact shadows, effects LOD, FX pool, moment rim)
do
    currentScenario = "per-client-caps"
    local pure = newServer("E", "job-E")
    local Shadow = pure.require(node("src/shared/ContactShadowRules"))
    local Lod = pure.require(node("src/shared/EffectsLod"))
    local devices, modes = {"Phone", "Tablet", "Desktop"}, {"full", "lite", "off"}
    local function keysOf(t) local n = 0 for _ in t do n += 1 end return n end
    local shadowKeys, lodKeys = keysOf(Shadow), keysOf(Lod)
    for _, n in CROSS_COUNTS do
        -- client k: its own device and Effects setting; around it n - 1 other players plus 10 more dinos
        local clients = {}
        for k = 1, n do
            local candidates = {}
            for j = 1, n - 1 + 10 do table.insert(candidates, {id = "other" .. j, distance = 6 + j * 2.5}) end
            clients[k] = {device = devices[k % 3 + 1], effects = modes[(k // 3) % 3 + 1], candidates = candidates, used = {}, rigs = 0}
        end
        local alone = {}
        for k, c in clients do alone[k] = Shadow.pick(c.candidates, c.device, c.effects) end
        local forward, backward, drawn, perClientOk = {}, {}, 0, true
        for k = 1, n do forward[k] = Shadow.pick(clients[k].candidates, clients[k].device, clients[k].effects) end
        for k = n, 1, -1 do backward[k] = Shadow.pick(clients[k].candidates, clients[k].device, clients[k].effects) end
        local same = true
        for k = 1, n do
            if not deepEqual(forward[k], backward[k]) or not deepEqual(forward[k], alone[k]) then same = false end
            local want = math.min(Shadow.maxOthers(clients[k].device, clients[k].effects), #clients[k].candidates)
            if #forward[k] ~= want then perClientOk = false end
            drawn += #forward[k]
        end
        check(n .. " clients: each client's contact shadows follow ITS device and Effects setting, not the other clients'", perClientOk, "")
        check(n .. " clients: the contact shadow picks do not depend on which client was asked first (no shared state)", same, "")
        local cap = Shadow.maxOthers("Desktop", "full")
        check(n .. " clients: shadows add up across clients (cap is per client, not one pool of " .. cap .. ")", n < 2 or drawn > cap, tostring(drawn))

        -- effects LOD: 12 other dinos around each client
        local lodOk = true
        for k, c in clients do
            local mode = c.effects
            local shown = 0
            for rank = 1, 12 do if Lod.detail(mode, "mutation", 10, false, rank, 3) ~= "none" then shown += 1 end end
            if shown ~= Lod.MaxDinos[mode] or Lod.detail(mode, "aura", 9000, true, 99, 3) == "none" and mode ~= "off" then lodOk = false end
        end
        check(n .. " clients: effects LOD allows MaxDinos for each client's own mode and never culls its own dino", lodOk, "")

        -- FX pool: round-robin, so a global counter would run out after the first clients
        local cost = {beams = 2, trails = 1, lights = 1, shells = 0}
        local progress = true
        while progress do
            progress = false
            for _, c in clients do
                if Lod.fits(c.device:lower(), c.used, cost) then
                    for _, key in Lod.CostKeys do c.used[key] = (c.used[key] or 0) + (cost[key] or 0) end
                    c.rigs += 1
                    progress = true
                end
            end
        end
        local poolOk = true
        for k, c in clients do
            local solo = {}
            local count = 0
            while Lod.fits(c.device:lower(), solo, cost) do
                for _, key in Lod.CostKeys do solo[key] = (solo[key] or 0) + (cost[key] or 0) end
                count += 1
            end
            if count ~= c.rigs or count == 0 then poolOk = false end
        end
        check(n .. " clients: each client's FX pool (beams, trails, lights) fills to the same size alone or next to the others", poolOk, "")

        -- MomentRim (BD-433): only checked once it is on main (PR #338). One rim per client; its budget is that client's own Highlight
        -- count and its own Effects setting, so a crowded client never blocks a quiet one.
        if exists("src/shared/MomentRimPlan") and Lod.rimFits ~= nil then
            local Plan = pure.require(node("src/shared/MomentRimPlan"))
            local rimOk, detail = true, ""
            for round = 1, 2 do
                for k = (if round == 1 then 1 else n), (if round == 1 then n else 1), (if round == 1 then 1 else -1) do
                    local c = clients[k]
                    local alive = if k % 2 == 0 then 0 else 40 -- Highlights alive in THIS client's world
                    local calm = k % 3 == 0
                    local wantFits = c.effects ~= "off" and alive < Lod.RimHighlightHardCap - 1
                    local wantMode = if c.effects == "off" then "none" else "new"
                    if Lod.rimFits(c.effects, alive) ~= wantFits or Plan.mode(c.effects, calm, false) ~= wantMode then
                        rimOk, detail = false, detail .. " client" .. k
                    end
                end
            end
            check(n .. " clients: the moment rim budget and mode depend only on the client's own Effects setting and Highlight count", rimOk, detail)
        end
    end
    check("the shared rule modules gained no state while 8 clients used them", keysOf(Shadow) == shadowKeys and keysOf(Lod) == lodKeys and table.isfrozen(Lod.Live) and table.isfrozen(Shadow.Layers), "")
end
