---------------------------------------------------------------- 17. BD-631: nobody else can change a player's `objectives` field
-- The cross-player checks above compare a victim's wealth before and after an attacker's calls; with ObjectivesEnabled on the victim's OWN
-- queued events are written by his own lease renew (BD-625), so the field moves while the attacker sleeps and cannot sit in that list.
-- This scenario proves it apart: B is the victim, A the attacker. B's objectives are recorded (progress, claimed, seen) after B's own
-- pending events are flushed; then A sends every remote call he can think of (forged keys naming B, B's ids and token in every slot,
-- the whole hostile corpus at the objective handlers) while B keeps recording events of his own and his renew keeps writing. The stored
-- field must end as a pure function of "B's baseline + exactly the events B recorded": the model is ObjectiveRules.applyToProfile on a
-- copy of the baseline. The short and daily window ids roll with the server clock (that is B's own write and not A's doing), so the
-- comparison covers the tutorial progress and claims, the remembered `seen` ids, the crystals earned and the claimed flags.
do
local function projection(objectives)
    if type(objectives) ~= "table" then return "<none>" end
    local flagged = 0
    for _, group in {"short", "daily"} do
        local g = objectives[group]
        for _, claimed in (type(g) == "table" and g.claimed) or {} do if claimed == true then flagged += 1 end end
    end
    return canon({v = objectives.v, tutorial = objectives.tutorial, seen = objectives.seen, earned = objectives.earned}) .. "|claimedShortDaily=" .. flagged
end
local function storedObjectives(userId)
    local profile = DATA[keyOf(userId)]
    return profile and profile.objectives
end
local function crystalsInProfile(userId)
    local profile = DATA[keyOf(userId)]
    return profile and profile.progression and profile.progression.crystals or -1
end
local function flushAll(server, p)
    for _ = 1, 40 do
        local ok, status = server.Repo.objectiveFlush(p)
        if ok then return status end
        sleep(2)
    end
    return "never"
end

runScenario("objectives-isolation", DORMANT, function(server)
    startServices(server)
    check("objectives-isolation: ObjectiveAction exists with its flag on and every service started", server.remotes.ObjectiveAction ~= nil and server.startErrors == nil, table.concat(server.startErrors or {}, " | "))
    local Rules = loadMod(server, "src/shared/ObjectiveRules")
    local a = connect(server, 1001) -- the attacker
    local b = connect(server, 1002) -- the victim
    hatchEverything(server, a, 60)
    hatchEverything(server, b, 90)
    settle(server, b, 90, 600)
    sleep(10)
    -- B's own state: T1 done and claimed, T2 done and NOT claimed (a forged claim for B would be accepted if it ever reached him), T3 partly done
    server.Repo.objectiveRecord(b, {kind = "food_eaten", amount = 12})
    server.Repo.objectiveRecord(b, {kind = "run_end", amount = 1, id = "run:own-1", value = 600})
    sleep(2)
    local bToken = tok("own-claim")
    local own = fireNow(server, "ObjectiveAction", b, {action = "claim", id = "T1", token = bToken})
    check("objectives-isolation: the victim's own claim works (the handler is live)", type(own) == "table" and own.ok == true, type(own) == "table" and tostring(own.reason) or tostring(own))
    sleep(11)
    check("objectives-isolation: the victim's flush finishes (nothing of his own is still queued)", flushAll(server, b) ~= "never", "")
    -- A earns a state of his own, so his forged calls run against live code and a profile that can change
    server.Repo.objectiveRecord(a, {kind = "food_eaten", amount = 12})
    sleep(2)
    local aClaim = fireNow(server, "ObjectiveAction", a, {action = "claim", id = "T1", token = tok("a-claim")})
    check("objectives-isolation: the attacker's own claim works", type(aClaim) == "table" and aClaim.ok == true, type(aClaim) == "table" and tostring(aClaim.reason) or tostring(aClaim))
    sleep(11)

    local baseObjectives = deepcopy(storedObjectives(1002))
    local baseCrystals = crystalsInProfile(1002)
    local baseRevision = DATA[keyOf(1002)].revision
    check("objectives-isolation: the baseline has a tutorial state worth protecting (T1 claimed, T2 done, T3 started)",
        type(baseObjectives) == "table" and baseObjectives.tutorial.claimed.T1 == true and baseObjectives.tutorial.claimed.T2 ~= true and (baseObjectives.tutorial.progress.T2 or 0) >= 1 and (baseObjectives.tutorial.progress.T3 or 0) >= 1, canon(baseObjectives and baseObjectives.tutorial))
    local startedAt = now

    -- everything of B's an attacker could name
    local nestsB = profileOf(1002).eggNests or {}
    local nestB = nestsB[1] and nestsB[1].nestId or "nest:none:1"
    local eggB = profileOf(1002).eggs[1] and profileOf(1002).eggs[1].eggId or "egg-none"
    local instB, speciesB, variantB = nil, nil, nil
    for id in profileOf(1002).dinosaurIdentity.instances do instB = id break end
    for id, e in profileOf(1002).collection do
        for key, v in e.variants do if v.count > 0 then variantB, speciesB = key, id break end end
        if variantB then break end
    end
    local donorsB = donorsFor(1002, 6)
    local named = {
        {"B player", b}, {"B user id", 1002}, {"B key", "u:1002"}, {"B egg", eggB}, {"B nest", nestB}, {"B dinosaur", instB or "u:1002/none"},
        {"B species", speciesB or "compy"}, {"B variant", variantB or "x"}, {"B claim token", bToken}, {"B operation id", "objective:" .. bToken},
        {"B donors", donorsB or {"u:1002/1"}}, {"T2", "T2"}, {"T3", "T3"}, {"fusion_menu", "fusion_menu"},
    }

    -- B plays on: his own events (in memory, committed by his renew or the final flush)
    local recorded = 0
    local function victimPlays()
        if server.Repo.objectiveRecord(b, {kind = "food_eaten", amount = 1}) then recorded += 1 end
    end

    -- 1. forged requests that name B in a key or a value, through the objective handler
    local forgedKeys = {"as", "player", "target", "victim", "userId", "to", "for", "owner", "profile", "key"}
    local forged = 0
    for _, id in {"T2", "T3", "S1", "D1", "fusion_menu"} do
        for _, key in forgedKeys do
            for _, value in {b, 1002, "u:1002"} do
                fireNow(server, "ObjectiveAction", a, {action = "claim", id = id, token = tok("forge"), [key] = value})
                fireNow(server, "ObjectiveAction", a, {action = "seen", id = id, [key] = value})
                fireNow(server, "ObjectiveAction", a, {action = "view", [key] = value})
                forged += 3
                sleep(1.1)
            end
        end
        victimPlays()
    end
    -- B's real claim token and ids used by A, shaped like a genuine request
    for _, id in {"T1", "T2", "T3"} do
        fireNow(server, "ObjectiveAction", a, {action = "claim", id = id, token = bToken})
        fireNow(server, "ObjectiveAction", a, {action = "claim", id = id, token = "objective:" .. bToken})
        sleep(1.5)
    end
    fireNow(server, "ObjectiveAction", b, {action = "view"}) -- the victim opens his own view meanwhile
    -- A opens the fusion menu and reports it for himself, then reports it again naming B: only A's own profile may take it
    fireNow(server, "FusionAction", a, {action = "list", limit = 5})
    sleep(1.5)
    fireNow(server, "ObjectiveAction", a, {action = "seen", id = "fusion_menu"})
    sleep(1.5)
    -- fusion hooks with B's donors, B's ids in every other handler
    fireNow(server, "FusionAction", a, {action = "quote", targetStage = "gold", donorIds = donorsB or {}})
    sleep(1.5)
    fireNow(server, "FusionAction", a, {action = "fuse", token = tok("fu"), targetStage = "gold", donorIds = donorsB or {}, quoteDigest = "00000000000000000"})
    sleep(1.5)
    fireNow(server, "ClaimChest", a, eggB, tok("x"))
    sleep(1.5)
    fireNow(server, "ClaimNest", a, nestB)
    sleep(1.5)
    fireNow(server, "EquipSpecies", a, speciesB or "compy", tok("x"), variantB)
    sleep(1.5)
    victimPlays()

    -- 2. every remote, one slot at a time, B's ids and the hostile corpus (objective handlers get the whole corpus, the rest B's names plus a few)
    local tmpl = templates(server, a)
    local names = {}
    for name in tmpl do if server.remotes[name] and name ~= "AdminAction" then table.insert(names, name) end end
    table.sort(names)
    local wide = {ObjectiveAction = true, FusionAction = true, GiftAction = true, SkinAction = true}
    local everything = corpus({victim = b})
    local calls = 0
    for _, name in names do
        local base = tmpl[name]()
        local items = {}
        for _, item in named do table.insert(items, item) end
        if wide[name] then
            for _, item in everything do table.insert(items, item) end
        else
            for i = 1, 8 do table.insert(items, everything[i * 7]) end
        end
        for slot = 1, math.max(#base, 1) + 1 do
            for _, item in items do
                local list = table.clone(base)
                list[slot] = item[2]
                fireNow(server, name, a, table.unpack(list, 1, math.max(#base, slot)))
                calls += 1
                sleep(0.6)
                if calls % 40 == 0 then victimPlays() end
            end
        end
        fireNow(server, name, a)
        sleep(1)
    end
    -- a last round: B's name in every slot of the objective handler, whole-table forms
    for _, item in named do
        fireNow(server, "ObjectiveAction", a, item[2])
        fireNow(server, "ObjectiveAction", a, {action = item[2]})
        fireNow(server, "ObjectiveAction", a, {action = "claim", id = item[2], token = item[2]})
        fireNow(server, "ObjectiveAction", a, {action = "seen", id = item[2]})
        sleep(1.2)
    end
    victimPlays()
    sleep(server.Config.ProfileRenewSeconds * 2 + 5) -- B's own renew carries his queued events
    local flushed = flushAll(server, b)
    sleep(2)

    local took = now - startedAt
    local after = storedObjectives(1002)
    local model = {objectives = deepcopy(baseObjectives)}
    if recorded > 0 then Rules.applyToProfile(model, {{kind = "food_eaten", amount = recorded}}, vos.time()) end
    report("objectives-isolation: " .. forged .. " forged requests and " .. calls .. " malformed calls by the attacker in " .. math.floor(took) .. " s; the victim recorded " .. recorded .. " events of his own, his profile revision " .. baseRevision .. " -> " .. DATA[keyOf(1002)].revision)
    check("objectives-isolation: the victim's own flush ends cleanly", flushed == "flushed" or flushed == "nothing", tostring(flushed))
    check("objectives-isolation: the victim recorded events of his own meanwhile (the test tolerates his own writes)", recorded >= 10, tostring(recorded))
    check("objectives-isolation: the victim's own lease renew wrote during the attack", DATA[keyOf(1002)].revision > baseRevision, baseRevision .. " -> " .. DATA[keyOf(1002)].revision)
    check("objectives-isolation: the run stayed inside one UTC day (the earned-today counter did not roll)", vos.time() < 1700006400, tostring(vos.time()))
    check("objectives-isolation: the victim's tutorial progress, claims, seen ids and earned crystals are exactly baseline + his own events",
        projection(after) == projection(model.objectives), projection(after):sub(1, 300) .. " vs " .. projection(model.objectives):sub(1, 300))
    check("objectives-isolation: no short or daily objective of the victim became claimed", projection(after):match("claimedShortDaily=(%d+)") == projection(baseObjectives):match("claimedShortDaily=(%d+)"), "")
    check("objectives-isolation: the victim's unclaimed T2 is still unclaimed and T1 still claimed", after.tutorial.claimed.T2 ~= true and after.tutorial.claimed.T1 == true, canon(after.tutorial.claimed))
    check("objectives-isolation: the victim's crystals did not move (no foreign reward)", crystalsInProfile(1002) == baseCrystals, baseCrystals .. " -> " .. crystalsInProfile(1002))
    check("objectives-isolation: the victim did not grow a `seen` entry he never reported", canon(after.seen) == canon(model.objectives.seen), canon(after.seen))
    -- what the victim's client reads back agrees
    sleep(11)
    local view = fireNow(server, "ObjectiveAction", b, {action = "view"})
    check("objectives-isolation: the victim's own view still answers ok", type(view) == "table" and view.ok == true, type(view) == "table" and tostring(view.reason) or tostring(view))
    -- the attacker's own claims are only for objectives his own play completed (his sweep above legitimately claims some of them)
    local aObjectives = storedObjectives(1001)
    local ObjectiveConfig = loadMod(server, "src/shared/ObjectiveConfig")
    local unearned = {}
    for id, claimed in (type(aObjectives) == "table" and aObjectives.tutorial.claimed) or {} do
        local goal = ObjectiveConfig.ById[id] and ObjectiveConfig.ById[id].goal or math.huge
        if claimed == true and (aObjectives.tutorial.progress[id] or 0) < goal then table.insert(unearned, id) end
    end
    check("objectives-isolation: the attacker holds no claim for an objective his own play did not complete", type(aObjectives) == "table" and aObjectives.tutorial.claimed.T1 == true and #unearned == 0, table.concat(unearned, ","))
    reportErrors("objectives-isolation", takeErrors())
    reloads(server, "objectives-isolation", b)
end)
end
