
---------------------------------------------------------------- 10. the run itself: start, end, die and leave all at once; equip during a run; empty runs
local function charOf(p) return p.Character end
local function startRunNow(server, p)
    fireNow(server, "ClientWorldReady", p)
    fireNow(server, "RequestStartRun", p)
end

runScenario("run-lifecycle", nil, function(server)
    startServices(server)
    local settleCount = function() local n = 0 for _, c in server.settleCalls do n += c end return n end
    local p = connect(server, 1001)
    local before = settleCount()
    -- 1. thirty start requests at once: one run
    fireNow(server, "ClientWorldReady", p)
    parallel(30, function() fireNow(server, "RequestStartRun", p) end)
    local c = charOf(p)
    local runId = c:GetAttribute("RunId")
    check("run-lifecycle: 30 RequestStartRun at once begin exactly one run", c:GetAttribute("RunState") == "Active" and type(runId) == "string", tostring(c:GetAttribute("RunState")))
    -- 2. the client cannot grant itself catches; the server's food loop does. Simulate the server writing 40 catches, then end 30 times at once
    c:SetAttribute("CatchScore", 40)
    sleep(1)
    parallel(30, function() fireNow(server, "RequestEndRun", p) end)
    sleep(6)
    check("run-lifecycle: 30 RequestEndRun at once settle the run exactly once", settleCount() - before == 1 and server.settleCalls[runId] == 1, tostring(settleCount() - before))
    check("run-lifecycle: the 40 catches became 40 eggs, not more", eggTotals(1001) == 40, tostring(eggTotals(1001)))
    check("run-lifecycle: the player is back in the sanctuary with a fresh dinosaur", p.respawns >= 1 and charOf(p):GetAttribute("RunState") == "Sanctuary", tostring(p.respawns))
    -- 3. end, die, disconnect in the same tick: one settlement
    sleep(10)
    startRunNow(server, p)
    local c2 = charOf(p)
    local run2 = c2:GetAttribute("RunId")
    c2:SetAttribute("CatchScore", 25)
    local settleBefore = settleCount()
    local eggsBefore = eggTotals(1001)
    task.spawn(function() fireNow(server, "RequestEndRun", p) end)
    task.spawn(function() c2.humanoid.Health = 0 end)
    task.spawn(function() disconnect(server, p) end)
    sleep(30)
    check("run-lifecycle: Home, death and leaving in the same tick settle once", server.settleCalls[run2] == 1, tostring(server.settleCalls[run2]))
    check("run-lifecycle: exactly 25 more eggs were credited", (profileOf(1001).runEggBank and #profileOf(1001).runEggBank or 0) + #profileOf(1001).eggs + profileOf(1001).pendingChestGrants == eggsBefore + 25,
        tostring((#(profileOf(1001).runEggBank or {})) + #profileOf(1001).eggs))
    reportErrors("run-lifecycle", takeErrors())
end)

-- BD-613 (LEAD decision, docs/115): a dinosaur picked while a run is Active or Ending is accepted ("next_run") but only applies at the next spawn.
-- Before the fix this scenario's first check failed: EquipSpecies answered "equipped" with RunState = Active and re-rendered the dinosaur.
runScenario("equip-next-run", nil, function(server)
    startServices(server)
    local CS = loadMod(server, "src/server/CollectionService")
    local p = seeded(server, 1001, function(profile)
        profile.collection.compy.base = 3
        profile.collection.triceratops.base = 2
    end)
    local before = p.attrs.EquippedSpeciesId
    local locked = nil
    for id, e in profileOf(1001).collection do
        if type(e) == "table" and id ~= "compy" and id ~= "triceratops" and (e.base or 0) + (e.gold or 0) + (e.emerald or 0) + (e.diamond or 0) == 0 then locked = id break end
    end
    startRunNow(server, p)
    local c = charOf(p)
    check("equip-next-run: the run is active", c:GetAttribute("RunState") == "Active", tostring(c:GetAttribute("RunState")))
    sleep(2)
    local refreshBefore, writesBefore = server.dinoCalls.refresh, M.writes
    fireNow(server, "EquipSpecies", p, "triceratops", tok("midrun"))
    sleep(2)
    check("equip-next-run: a pick during a run answers next_run", p.attrs.LastEquipStatus == "next_run", tostring(p.attrs.LastEquipStatus))
    check("equip-next-run: the dinosaur in play does not change during the run", p.attrs.EquippedSpeciesId == before and p.attrs.EquippedSpeciesId ~= "triceratops" and server.dinoCalls.refresh == refreshBefore,
        tostring(p.attrs.EquippedSpeciesId) .. " refresh+" .. (server.dinoCalls.refresh - refreshBefore))
    check("equip-next-run: nothing was written to the profile for the pending pick", profileOf(1001).equippedSpeciesId == before and M.writes == writesBefore, tostring(profileOf(1001).equippedSpeciesId) .. " writes+" .. (M.writes - writesBefore))
    -- a species the player does not own is refused as before, even during a run, and does not replace the pending pick
    if locked then
        fireNow(server, "EquipSpecies", p, locked, tok("locked")) sleep(2)
        check("equip-next-run: an unowned species is still refused during a run", p.attrs.LastEquipStatus == "locked", tostring(p.attrs.LastEquipStatus))
    end
    -- picking the dinosaur already in use cancels the pending pick
    fireNow(server, "EquipSpecies", p, before, tok("back")) sleep(2)
    check("equip-next-run: picking the dinosaur in use cancels the pending pick", p.attrs.LastEquipStatus == "already_equipped", tostring(p.attrs.LastEquipStatus))
    CS.applyPending(p) sleep(1)
    check("equip-next-run: a cancelled pick applies nothing at the spawn", p.attrs.EquippedSpeciesId == before and M.writes == writesBefore, tostring(p.attrs.EquippedSpeciesId))
    -- the last pick wins, and it applies at the next spawn
    fireNow(server, "EquipSpecies", p, "triceratops", tok("again")) sleep(2)
    check("equip-next-run: the pick is pending again", p.attrs.LastEquipStatus == "next_run" and p.attrs.EquippedSpeciesId == before, tostring(p.attrs.LastEquipStatus))
    c:SetAttribute("CatchScore", 0)
    fireNow(server, "RequestEndRun", p)
    sleep(12)
    check("equip-next-run: after the run the player is back home on the old dinosaur until the spawn applies the pick", charOf(p):GetAttribute("RunState") == "Sanctuary" and p.attrs.EquippedSpeciesId == before, tostring(p.attrs.EquippedSpeciesId))
    CS.applyPending(p) sleep(2)  -- Bootstrap.server calls this on every spawn, before Dinosaur.attach
    check("equip-next-run: the next spawn equips the pick", p.attrs.EquippedSpeciesId == "triceratops" and profileOf(1001).equippedSpeciesId == "triceratops", tostring(p.attrs.EquippedSpeciesId))
    local writesAfter = M.writes
    CS.applyPending(p) sleep(1)
    check("equip-next-run: the pick applies once", M.writes == writesAfter, "writes+" .. (M.writes - writesAfter))
    -- at home an equip is immediate, as before
    sleep(2)
    fireNow(server, "EquipSpecies", p, "compy", tok("home")) sleep(2)
    check("equip-next-run: at home an equip is immediate", p.attrs.LastEquipStatus == "equipped" and p.attrs.EquippedSpeciesId == "compy", tostring(p.attrs.LastEquipStatus))
    -- Ending counts as in a run; a pick is dropped when the player leaves
    startRunNow(server, p)
    charOf(p):SetAttribute("RunState", "Ending")
    sleep(2)
    fireNow(server, "EquipSpecies", p, "triceratops", tok("ending")) sleep(2)
    check("equip-next-run: a pick while the run is Ending is also next_run", p.attrs.LastEquipStatus == "next_run" and p.attrs.EquippedSpeciesId == "compy", tostring(p.attrs.LastEquipStatus))
    disconnect(server, p)
    sleep(30)
    CS.applyPending(p)
    check("equip-next-run: a pick does not survive the player leaving", profileOf(1001).equippedSpeciesId == "compy", tostring(profileOf(1001).equippedSpeciesId))
    reportErrors("equip-next-run", takeErrors())
end)

-- Findings reproduced, not asserted as fixed: each line prints "FINDING" so the audit document can quote the exact numbers.
runScenario("findings", nil, function(server)
    startServices(server)
    local p = seeded(server, 1001, function(profile)
        profile.collection.compy.base = 3
        profile.collection.triceratops.base = 2
    end)
    -- F-EQUIP (BD-613) is fixed: see the "equip-next-run" scenario above.
    -- F-ZERO-RUN: a run that ate nothing still costs a settlement write; one player can cycle it every ~3 s
    local writesBefore = M.writes
    local cycles = 0
    local t0 = now
    for i = 1, 6 do
        sleep(4)
        local ch = charOf(p)
        if ch and ch:GetAttribute("RunState") == "Sanctuary" then
            startRunNow(server, p)
            sleep(1)
            fireNow(server, "RequestEndRun", p)
            cycles += 1
        elseif ch and ch:GetAttribute("RunState") == "Active" then
            fireNow(server, "RequestEndRun", p)
            cycles += 1
        end
    end
    sleep(5)
    report(string.format("FINDING zero-catch-runs: %d start/end cycles in %.0f virtual s cost %d profile writes with 0 eggs and 0 crystals earned (about %.2f writes per second per account)", cycles, now - t0, M.writes - writesBefore, (M.writes - writesBefore) / math.max(1, now - t0)))
    server.findingZeroRunWrites = M.writes - writesBefore

    -- F-RECEIPT: a developer product purchase is honoured whatever CrystalPacksEnabled says (the client can prompt any product id)
    local product, crystals = nil, nil
    for id, amount in server.Config.DeveloperProducts do product, crystals = id, amount break end
    local c0 = profileOf(1001).progression and profileOf(1001).progression.crystals or 0
    local granted = server.Repo.purchase(p, {PlayerId = p.UserId, ProductId = product, PurchaseId = "receipt-1", CurrencySpent = 49})
    local c1 = profileOf(1001).progression.crystals
    report("FINDING receipt-ignores-flag: ProcessReceipt path granted " .. tostring(crystals) .. " crystals for product " .. tostring(product) .. " with CrystalPacksEnabled=" .. tostring(server.Config.CrystalPacksEnabled) .. " (crystals " .. c0 .. " -> " .. c1 .. ")")
    server.findingReceipt = granted == true and c1 == c0 + crystals
    -- malformed receipts never grant and never throw
    local before = wealthPoints(server, 1001)
    local bad = {
        {PlayerId = p.UserId, ProductId = product, PurchaseId = "", CurrencySpent = 1}, {PlayerId = p.UserId, ProductId = product, PurchaseId = string.rep("x", 121), CurrencySpent = 1},
        {PlayerId = p.UserId + 1, ProductId = product, PurchaseId = "other", CurrencySpent = 1}, {PlayerId = p.UserId, ProductId = 12345, PurchaseId = "unknown", CurrencySpent = 1},
        {PlayerId = p.UserId, ProductId = product, PurchaseId = "neg", CurrencySpent = -1}, {PlayerId = p.UserId, ProductId = product, PurchaseId = "nan", CurrencySpent = NaN},
        {PlayerId = p.UserId, ProductId = product, PurchaseId = "huge", CurrencySpent = 3e9}, {PlayerId = p.UserId, ProductId = product, PurchaseId = "frac", CurrencySpent = 1.5},
        {PlayerId = p.UserId, ProductId = product, PurchaseId = 5, CurrencySpent = 1}, {PlayerId = p.UserId, ProductId = "x", PurchaseId = "str", CurrencySpent = 1},
        {}, {PlayerId = p.UserId},
    }
    for _, receipt in bad do
        local ok, result = pcall(server.Repo.purchase, p, receipt)
        if not ok then table.insert(errors, {remote = "ProcessReceipt", args = describe(receipt), message = tostring(result)}) end
    end
    local replay = server.Repo.purchase(p, {PlayerId = p.UserId, ProductId = product, PurchaseId = "receipt-1", CurrencySpent = 49})
    check("findings: malformed receipts grant nothing and a replayed PurchaseId is granted once", wealthPoints(server, 1001) == before and replay == true, tostring(wealthPoints(server, 1001)) .. " vs " .. before)
    reportErrors("findings", takeErrors())

    -- F-ENVELOPE: what the movement checks accept, sustained, for a client that moves as fast as every tick allows
    local Env = loadMod(server, "src/shared/MovementEnvelope")
    local cfg = server.Config
    local function sustained(walk, dt, tolerance, burst)
        -- largest horizontal step per tick the check accepts, as studs per second
        local step = walk * dt * tolerance + burst
        return step / dt
    end
    local walk = cfg.WalkSpeed
    local guard = sustained(walk, cfg.MovementGuardTickSeconds, cfg.MovementGuardSpeedTolerance, cfg.MovementGuardBurstStuds)
    local food = sustained(walk, cfg.FoodTickSeconds, 2, 2)
    local crystal = sustained(walk, 0.25, 2, 2)
    -- cross-check against the real function: a step just inside the bound passes, just outside fails
    local function passes(stepStuds, dt, tolerance, burst) return Env.plausible(Vector3.new(stepStuds, 0, 0), dt, tolerance, burst, 0, walk) end
    local insideGuard = passes(guard * cfg.MovementGuardTickSeconds - 0.01, cfg.MovementGuardTickSeconds, cfg.MovementGuardSpeedTolerance, cfg.MovementGuardBurstStuds)
    local outsideGuard = passes(guard * cfg.MovementGuardTickSeconds + 0.01, cfg.MovementGuardTickSeconds, cfg.MovementGuardSpeedTolerance, cfg.MovementGuardBurstStuds)
    report(string.format("FINDING movement-envelope: WalkSpeed %d; MovementGuard accepts a sustained %.0f studs/s (x%.1f), food pickup %.0f studs/s (x%.1f), crystal pickup %.0f studs/s (x%.1f); with a x2.2 speed potion the guard accepts %.0f studs/s",
        walk, guard, guard / walk, food, food / walk, crystal, crystal / walk, sustained(walk * 2.2, cfg.MovementGuardTickSeconds, cfg.MovementGuardSpeedTolerance, cfg.MovementGuardBurstStuds)))
    check("findings: the envelope numbers above are what MovementEnvelope.plausible really accepts", insideGuard == true and outsideGuard == false, tostring(insideGuard) .. "/" .. tostring(outsideGuard))
    -- BD-611: the sliding window (shared/MovementWindow.luau) closes most of that. The per-tick numbers above are what each tick alone accepts; the window bounds the SUSTAINED speed.
    local Win = loadMod(server, "src/shared/MovementWindow")
    local windowed = Win.sustained(walk)
    local function cheatRejectedAfter(studsPerSecond, tick)
        local w, t, x = Win.new(), 0, 0
        while t <= 10 do
            x += studsPerSecond * tick
            if not Win.push(w, t, Vector3.new(x, 0, 0), walk, x) then return t end
            t += tick
        end
        return nil
    end
    local g, f, c = cheatRejectedAfter(guard, cfg.MovementGuardTickSeconds), cheatRejectedAfter(food, cfg.FoodTickSeconds), cheatRejectedAfter(crystal, 0.25)
    report(string.format("FINDING movement-envelope-window (BD-611): sliding window accepts a sustained %.0f studs/s (x%.2f); the old guard/food/crystal cheats (%.0f/%.0f/%.0f studs/s) are rejected after %.1f/%.1f/%.1f s; Studio must still measure real replication jitter",
        windowed, windowed / walk, guard, food, crystal, g or -1, f or -1, c or -1))
    check("findings: the old 106 / 69 / 52 studs/s cheats are rejected by the sliding window within 2 s", g ~= nil and g <= 2 and f ~= nil and f <= 2 and c ~= nil and c <= 2, tostring(g) .. "/" .. tostring(f) .. "/" .. tostring(c))
    check("findings: the sliding window accepts at most 2x WalkSpeed sustained", windowed <= walk * 2, tostring(windowed))
    server.findingSpeed = guard / walk
end)
