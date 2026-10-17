---------------------------------------------------------------- 15. BD-618 hygiene bundle (docs/151 F8): one check per item that can be exercised offline
runScenario("hygiene-618", {ExitRequestCooldownSeconds = 60, PlaytestFeedbackEnabled = true, DinoSkinsEnabled = true}, function(server)
    startServices(server)
    local rules = rulesOf(server)
    local pc = progressionConfig(server)
    local p = seeded(server, 1001, function(profile)
        profile.progression = {crystals = 5000, auras = {}, equippedAura = "", potions = {}, buffs = {}, accountXP = 0, conditionLevel = 0}
        profile.collection.compy.base = 3
        profile.collection.triceratops.base = 2
    end)

    -- (a) ClassGlide: the remote may exist (the client waits for it) but nothing on the server listens to it
    if server.remotes.ClassGlide ~= nil then
        check("hygiene-618 (a): ClassGlide has no server handler", #handlersOf(server.remotes.ClassGlide) == 0, tostring(#handlersOf(server.remotes.ClassGlide)))
    else
        check("hygiene-618 (a): ClassGlide is not created while ClassMovementEnabled is off", true, "")
    end

    -- (b) ClientWorldReady: ignored until the SERVER terrain exists, believed once
    server.workspace.attrs.IslandTerrainReady = false
    fireNow(server, "ClientWorldReady", p)
    check("hygiene-618 (b): a ClientWorldReady before the server terrain is ready is ignored", p.attrs.WorldReady ~= true, tostring(p.attrs.WorldReady))
    server.workspace.attrs.IslandTerrainReady = true
    fireNow(server, "ClientWorldReady", p, "junk")
    check("hygiene-618 (b): a malformed ClientWorldReady is ignored", p.attrs.WorldReady ~= true, tostring(p.attrs.WorldReady))
    fireNow(server, "ClientWorldReady", p)
    check("hygiene-618 (b): the honest ClientWorldReady after the server terrain is believed", p.attrs.WorldReady == true, tostring(p.attrs.WorldReady))

    -- (c) PrivateState hello: 20 hellos in one second cost one snapshot now and one when the 2 s floor ends, never 20
    sleep(3)
    local snapshots0 = server.PS.stats.snapshots
    for _ = 1, 20 do fireNow(server, "PrivateState", p, "hello") sleep(0.05) end
    local nowSnapshots = server.PS.stats.snapshots - snapshots0
    check("hygiene-618 (c): 20 hellos in a second send one snapshot at once", nowSnapshots == 1, tostring(nowSnapshots))
    sleep(3)
    local laterSnapshots = server.PS.stats.snapshots - snapshots0
    check("hygiene-618 (c): the requests inside the floor are answered by exactly one trailing snapshot (a resync is never lost)", laterSnapshots == 2, tostring(laterSnapshots))

    -- (d) EquipSpecies answering already_equipped does not render the dinosaur again
    sleep(1)
    fireNow(server, "EquipSpecies", p, "triceratops", tok("eq"))
    sleep(1)
    local refresh0 = server.dinoCalls.refresh
    fireNow(server, "EquipSpecies", p, "triceratops", tok("eq"))
    sleep(1)
    check("hygiene-618 (d): equipping the species already worn answers already_equipped", p.attrs.LastEquipStatus == "already_equipped", tostring(p.attrs.LastEquipStatus))
    check("hygiene-618 (d): and does not re-render the dinosaur", server.dinoCalls.refresh == refresh0, tostring(server.dinoCalls.refresh - refresh0))
    fireNow(server, "EquipSpecies", p, "compy", tok("eq"))
    sleep(1)
    check("hygiene-618 (d): a real change still re-renders it once", server.dinoCalls.refresh == refresh0 + 1 and p.attrs.LastEquipStatus == "equipped", tostring(server.dinoCalls.refresh - refresh0) .. " " .. tostring(p.attrs.LastEquipStatus))

    -- (e) the public attributes no longer carry the server clock or the predator's id
    check("hygiene-618 (e): no LastPredatorUserId Player attribute exists", p.attrs.LastPredatorUserId == nil, tostring(p.attrs.LastPredatorUserId))
    check("hygiene-618 (e): RunLifecycle keeps it in server memory (0 = nobody)", server.RL.lastPredatorUserId(p) == 0, tostring(server.RL.lastPredatorUserId(p)))
    fireNow(server, "ClaimNest", p, "no-such-nest")
    local first = p.attrs.LastNestClaimAt
    sleep(1)
    fireNow(server, "ClaimNest", p, "no-such-nest")
    local second = p.attrs.LastNestClaimAt
    check("hygiene-618 (e): LastNestClaimAt is a small per-player counter that still changes on every request", type(first) == "number" and first < 1000 and second == first + 1, tostring(first) .. " -> " .. tostring(second))

    -- (f) limiters keyed by UserId: leaving and rejoining does not reset them
    local reasons = {}
    for i = 1, 40 do local r = fireNow(server, "FusionAction", p, {action = "list"}) reasons[i] = type(r) == "table" and r.reason or "ok" end
    local limited = 0
    for _, r in reasons do if r == "rate_limited" then limited += 1 end end
    check("hygiene-618 (f): 40 FusionAction requests in one window are limited to the window", limited >= 15, tostring(limited))
    server.Repo.release(p) disconnect(server, p)
    p = connect(server, 1001)
    local again = fireNow(server, "FusionAction", p, {action = "list"})
    check("hygiene-618 (f): a rejoin does not give a fresh FusionAction window", type(again) == "table" and again.reason == "rate_limited", type(again) == "table" and tostring(again.reason) or tostring(again))
    local feedback = {fun = 3, level = 2, looks = 3, text = "hello"}
    local lines0 = 0
    for _, line in server.prints do if string.find(line, "BD-FEEDBACK", 1, true) then lines0 += 1 end end
    fireNow(server, "PlaytestFeedback", p, feedback)
    server.Repo.release(p) disconnect(server, p)
    p = connect(server, 1001)
    fireNow(server, "PlaytestFeedback", p, feedback)
    local lines1 = 0
    for _, line in server.prints do if string.find(line, "BD-FEEDBACK", 1, true) then lines1 += 1 end end
    check("hygiene-618 (f): a rejoin does not reset the 1-per-2-minutes feedback limit (1 line logged, not 2)", lines1 - lines0 == 1, tostring(lines1 - lines0))
    -- the Home cooldown (60 s in this scenario) survives a rejoin: end a run, rejoin, start, a Home inside the cooldown does nothing
    server.workspace.attrs.IslandTerrainReady = true
    startRunNow(server, p)
    sleep(2)
    fireNow(server, "RequestEndRun", p)
    sleep(8)
    server.Repo.release(p) disconnect(server, p)
    p = connect(server, 1001)
    startRunNow(server, p)
    sleep(2)
    local runId = charOf(p):GetAttribute("RunId")
    fireNow(server, "RequestEndRun", p)
    sleep(3)
    check("hygiene-618 (f): Home inside the cooldown after a rejoin is ignored (the run is still active)", charOf(p) ~= nil and charOf(p):GetAttribute("RunState") == "Active" and charOf(p):GetAttribute("RunId") == runId, tostring(charOf(p) and charOf(p):GetAttribute("RunState")))

    -- (h) a purchase token that left the profile's operation ring is still answered as a duplicate (memory, no schema change)
    sleep(70)
    local q = seeded(server, 1002, function(profile)
        profile.progression = {crystals = 5000, auras = {}, equippedAura = "", potions = {}, buffs = {}, accountXP = 0, conditionLevel = 0}
    end)
    local win = windowOf(server)
    local offer = rules.shopOffers(win)[1]
    local price = rules.item(pc.Potions, offer.id).price
    local token = tok("ring")
    local okBuy, statusBuy = server.Repo.progressionAction(q, "buyPotion", offer.id .. "@" .. win, token, false)
    check("hygiene-618 (h): the first purchase commits", okBuy == true and profileOf(1002).progression.potions[offer.id] == 1, tostring(statusBuy))
    local after = profileOf(1002).progression.crystals
    server.Repo.release(q) disconnect(server, q)
    local ring = profileOf(1002).recentOperations
    local kept = {}
    for _, op in ring do if op.id ~= "progression:" .. token then table.insert(kept, op) end end
    profileOf(1002).recentOperations = kept -- what 50 newer operations would have done to the stored ring
    q = connect(server, 1002)
    sleep(1)
    local okReplay, statusReplay = server.Repo.progressionAction(q, "buyPotion", offer.id .. "@" .. win, token, false)
    check("hygiene-618 (h): the replay after the ring dropped the token is a duplicate and charges nothing", okReplay == true and statusReplay == "duplicate" and profileOf(1002).progression.crystals == after and profileOf(1002).progression.potions[offer.id] == 1,
        tostring(statusReplay) .. " crystals " .. tostring(profileOf(1002).progression.crystals) .. " vs " .. after)
    local okOther, statusOther = server.Repo.progressionAction(q, "buyPotion", "someone-else@" .. win, token, false)
    check("hygiene-618 (h): the same token for another item is a token_conflict", okOther == false and statusOther == "token_conflict", tostring(statusOther))

    -- (i) applySkin is charged to the same write budget as every other routine write
    hatchEverything(server, q, 40)
    local instanceId = nil
    for id in profileOf(1002).dinosaurIdentity.instances do instanceId = id break end
    local limitedSkins, allowedSkins = 0, 0
    for _ = 1, 14 do
        local ok, status = server.Repo.applySkin(q, {kind = "unequip", instanceId = instanceId})
        if status == "rate_limited" then limitedSkins += 1 else allowedSkins += 1 end
    end
    check("hygiene-618 (i): 14 skin writes in one instant are cut by the write budget (some rate_limited, some allowed)", limitedSkins >= 1 and allowedSkins >= 1, "limited " .. limitedSkins .. " allowed " .. allowedSkins)
    reportErrors("hygiene-618", takeErrors())
end)
