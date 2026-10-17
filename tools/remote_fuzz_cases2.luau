
---------------------------------------------------------------- 6. what a PUBLISHED playtest server exposes: the reviewed inventory, and every debug path inert
local function remoteNames(server)
    local names = {}
    for name in server.remotes do table.insert(names, name) end
    table.sort(names)
    return names
end
local function setOf(list) local t = {} for _, v in list do t[v] = true end return t end

runScenario("published-pins", {DemoDirectorEnabled = true}, function(server)
    -- DemoDirectorEnabled is forced ON here to prove the guard itself (IsStudio + GameId 0) keeps the trigger out of a published server.
    startServices(server)
    local names = remoteNames(server)
    local expected = setOf(EXPECTED)
    local seen = setOf(names)
    local extra, missing = {}, {}
    for _, n in names do if not expected[n] then table.insert(extra, n) end end
    for _, n in EXPECTED do if not seen[n] then table.insert(missing, n) end end
    check("published-pins: the remotes of a playtest server are exactly the reviewed inventory", #extra == 0 and #missing == 0, "unreviewed: " .. table.concat(extra, ",") .. " missing: " .. table.concat(missing, ","))
    for _, n in {"DemoTrigger", "QaMark", "PreviewDinosaurArt", "CombatBite", "ObjectiveAction", "GiftAction", "AdminGiftAction", "SkinAction", "TestGrantChests", "TestGrantSpecies", "TestSetMutationCopies"} do
        check("published-pins: " .. n .. " does not exist on a published server", server.remotes[n] == nil, "")
    end
    local p = connect(server, 1001)
    check("published-pins: the test-grant, mutation-setup and security-harness flags are false in the playtest Config",
        server.Config.ChestTestGrantEnabled == false and server.Config.CollectionTestGrantEnabled == false and server.Config.MutationTestSetupEnabled == false
        and server.Config.SecurityTestHarnessEnabled == false and server.Config.ArtTestHarnessEnabled == false and server.Config.QaOverlayEnabled == false and server.Config.CombatEnabled == false,
        "")
    -- AdminAction exists for everybody; only the experience creator (userId 1 here) is an admin
    local stranger = connect(server, 1002)
    sleep(1)
    local gravity0 = server.workspace.Gravity
    local ok1, why1 = fireNow(server, "AdminAction", stranger, "set", "gravity", 150)
    local ok2, why2 = fireNow(server, "AdminAction", stranger, "startWeather", "rain", 600)
    local ok3, why3 = fireNow(server, "AdminAction", stranger, "reset")
    check("published-pins: a non-admin gets not_admin from AdminAction for set, startWeather and reset and nothing changes",
        ok1 == false and why1 == "not_admin" and why2 == "not_admin" and why3 == "not_admin" and server.workspace.Gravity == gravity0, tostring(why1) .. "/" .. tostring(why2) .. "/" .. tostring(why3))
    reportErrors("published-pins", takeErrors())
end)

-- The three test-grant remotes exist ONLY while their flag is on (Studio test aid, evidence in docs/evidence/2026-10-17-hover). With the flag on
-- they work; with one flag off, that remote alone is missing.
runScenario("test-grants-flag-on", {ChestTestGrantEnabled = true, CollectionTestGrantEnabled = true, MutationTestSetupEnabled = true}, function(server)
    startServices(server)
    for _, n in {"TestGrantChests", "TestGrantSpecies", "TestSetMutationCopies"} do check("test-grants-flag-on: " .. n .. " exists with its flag on", server.remotes[n] ~= nil, "") end
    local p = connect(server, 1001)
    sleep(1)
    local eggs0 = eggTotals(1001)
    fireNow(server, "TestGrantChests", p)
    sleep(2)
    check("test-grants-flag-on: TestGrantChests grants the test eggs", eggTotals(1001) == eggs0 + server.Config.ChestTestGrantCount or p.attrs.LastChestTestGrantStatus == "granted", tostring(p.attrs.LastChestTestGrantStatus))
    reportErrors("test-grants-flag-on", takeErrors())
end)
runScenario("test-grants-one-flag", {MutationTestSetupEnabled = true}, function(server)
    startServices(server)
    check("test-grants-one-flag: only the remote whose flag is on exists", server.remotes.TestSetMutationCopies ~= nil and server.remotes.TestGrantChests == nil and server.remotes.TestGrantSpecies == nil, "")
end)

-- Studio only: the demo trigger exists in an UNPUBLISHED Studio session with the flag on, belongs to the first player only.
runScenario("demo-trigger-studio", {DemoDirectorEnabled = true}, function(server)
    startServices(server)
    check("demo-trigger-studio: the DemoTrigger remote exists in an unpublished Studio session with the flag on", server.remotes.DemoTrigger ~= nil, "")
    local owner = connect(server, 1001)
    local guest = connect(server, 1002)
    sleep(1)
    local ok1, r1 = fireNow(server, "DemoTrigger", owner, {kind = "giveCrystals", amount = 10})
    sleep(1)
    local ok2, r2 = fireNow(server, "DemoTrigger", guest, {kind = "giveCrystals", amount = 10})
    check("demo-trigger-studio: only the first player may use it", ok1 == true and ok2 == false and r2 == "not_owner", tostring(ok1) .. tostring(r1) .. "/" .. tostring(ok2) .. tostring(r2))
    -- garbage from the owner: bad requests are refused, no error
    local items = corpus({victim = guest})
    for _, item in items do
        sleep(0.3)
        fireNow(server, "DemoTrigger", owner, item[2])
        fireNow(server, "DemoTrigger", owner, {kind = item[2]})
        fireNow(server, "DemoTrigger", owner, {kind = "hatchParty", eggs = item[2]})
        fireNow(server, "DemoTrigger", owner, {kind = "giveCrystals", amount = item[2]})
        fireNow(server, "DemoTrigger", owner, {kind = "equipSpecies", speciesId = item[2]})
        fireNow(server, "DemoTrigger", owner, {kind = "setWeather", id = item[2]})
    end
    reportErrors("demo-trigger-studio", takeErrors())
end, {studio = true})

---------------------------------------------------------------- 7. the dormant handlers (every flag that ships off, switched on): same attacks
local DORMANT = {ObjectivesEnabled = true, GiftClaimEnabled = true, AdminGiftsEnabled = true, CombatEnabled = true, QaOverlayEnabled = true, ArtTestHarnessEnabled = true, PaidRandomItemsEnabled = true, DinoSkinsEnabled = true}
runScenario("dormant-handlers", DORMANT, function(server)
    startServices(server)
    local expected = {"ObjectiveAction", "GiftAction", "AdminGiftAction", "SkinAction", "CombatBite", "QaMark", "PreviewDinosaurArt"}
    for _, n in expected do check("dormant-handlers: " .. n .. " exists once its flag is on", server.remotes[n] ~= nil, "") end
    check("dormant-handlers: every service started", server.startErrors == nil, table.concat(server.startErrors or {}, " | "))
    local hostile = seeded(server, 1002, function(profile)
        profile.progression = {crystals = 9000, auras = {}, equippedAura = "", potions = {}, buffs = {}, accountXP = 360000, conditionLevel = 0}
    end)
    local admin = connect(server, 1) -- the experience creator: an admin
    local bystander = connect(server, 3003)
    settle(server, hostile, 40, 600)
    sleep(3)
    local tmpl = templates(server, hostile)
    local before = wealthPoints(server, 1002)
    local bystanderBefore = wealth(3003)
    local peak = before
    local calls = 0
    local items = corpus({victim = bystander})
    for _, name in expected do
        for _, who in {hostile, admin} do
            local base = tmpl[name]()
            for slot = 1, #base + 1 do
                for _, item in items do
                    local list = table.clone(base)
                    list[slot] = item[2]
                    fireNow(server, name, who, table.unpack(list, 1, math.max(#base, slot)))
                    calls += 1
                    sleep(0.3)
                    peak = math.max(peak, wealthPoints(server, 1002))
                end
            end
            fireNow(server, name, who)
            fireNow(server, name, who, nil, nil, nil, nil, nil)
        end
    end
    reportErrors("dormant-handlers", takeErrors())
    report("dormant-handlers: " .. calls .. " malformed calls over " .. #expected .. " handlers, from a player and from an admin")
    check("dormant-handlers: no free value", peak <= before, peak .. " vs " .. before)
    check("dormant-handlers: the bystander is untouched", wealth(3003) == bystanderBefore, "")
    -- a non-admin cannot reach the admin gift page or change the admin values
    local r = fireNow(server, "AdminGiftAction", hostile, {action = "audit", userId = 5})
    check("dormant-handlers: AdminGiftAction refuses a non-admin", type(r) == "table" and r.ok == false and r.reason == "not_admin", type(r) == "table" and tostring(r.reason) or tostring(r))
    local g = server.workspace.Gravity
    check("dormant-handlers: after the admin's garbage the shared values are inside their ranges", g >= 150 and g <= 400, tostring(g))
    for _, key in {"foodMultiplier", "growthMultiplier", "speedMultiplier", "mutationChanceMultiplier", "jumpPower", "leapSpeed"} do
        local v = server.workspace.attrs["Admin_" .. key]
        check("dormant-handlers: Admin_" .. key .. " is a finite number in range", type(v) == "number" and v == v and v > 0 and v < 100, tostring(v))
    end
    reloads(server, "dormant-handlers", hostile)
end)
