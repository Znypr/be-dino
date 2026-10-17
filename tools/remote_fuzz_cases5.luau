
---------------------------------------------------------------- 11. the other kind of entry point: a ProximityPrompt (the Heart "show off" spot) and the dormant handlers' valid requests
runScenario("show-off-prompt", {CaveHub = true}, function(server)
    startServices(server)
    local ShowOff = loadMod(server, "src/server/CaveShowOff")
    local parent = newInstance("Folder")
    local anchor = ShowOff.build(parent)
    check("show-off-prompt: the prompt anchor was built", anchor ~= nil, "")
    if not anchor then return end
    local prompt = anchor.children.ProximityPrompt
    check("show-off-prompt: it carries a ProximityPrompt with a Triggered handler", prompt ~= nil and #prompt.Triggered.fns == 1, "")
    local p = connect(server, 1001)
    local fn = prompt.Triggered.fns[1]
    local function trigger(who, ...)
        local ok, err = xpcall(fn, function(e) return tostring(e) end, who, ...)
        if not ok then table.insert(errors, {remote = "ShowOffPrompt", args = describe(who), message = err}) end
    end
    local root = p.Character.root
    local startPos = root.Position
    -- far away from the pedestal (the player stands at the spawn): a forged Triggered moves nobody
    trigger(p)
    sleep(2)
    check("show-off-prompt: a Triggered from far away does not move the dinosaur", root.Position == startPos, "")
    -- (the engine only ever passes the triggering Player, so the argument itself is not hostile input; the player's STATE is)
    trigger(p, "extra", 1, {})
    -- a player with no character, a dead one
    local ghost = mockPlayer(server, 7)
    trigger(ghost)
    p.Character.humanoid.Health = 0
    trigger(p)
    reportErrors("show-off-prompt", takeErrors())
end)

-- The dormant handlers answer valid requests too (so the fuzz above ran against live code, not against an early return)
runScenario("dormant-valid", DORMANT, function(server)
    startServices(server)
    local p = connect(server, 1002)
    sleep(1)
    local view = fireNow(server, "ObjectiveAction", p, {action = "view"})
    check("dormant-valid: ObjectiveAction view answers ok with a view", type(view) == "table" and view.ok == true and view.view ~= nil, type(view) == "table" and tostring(view.reason) or tostring(view))
    sleep(1)
    local get = fireNow(server, "GiftAction", p, {action = "get"})
    check("dormant-valid: GiftAction get answers ok with the recipient setting", type(get) == "table" and get.ok == true, type(get) == "table" and tostring(get.reason) or tostring(get))
    local admin = connect(server, 1)
    sleep(1)
    local audit = fireNow(server, "AdminGiftAction", admin, {action = "audit", userId = 55})
    check("dormant-valid: AdminGiftAction audit answers an admin", type(audit) == "table" and audit.ok == true, type(audit) == "table" and tostring(audit.reason) or tostring(audit))
    -- an admin gift needs pick/lookup then confirm then send; sending without confirming is refused
    sleep(1)
    local send = fireNow(server, "AdminGiftAction", admin, {action = "send", to = p.UserId, item = "crystals_custom", crystals = 100})
    check("dormant-valid: an admin gift to someone who was not picked and confirmed is refused", type(send) == "table" and send.ok == false, type(send) == "table" and tostring(send.reason) or tostring(send))
    sleep(1)
    local c = admin.Character
    local skins = fireNow(server, "SkinAction", p, {action = "get"})
    check("dormant-valid: SkinAction get answers ok with the owned list", type(skins) == "table" and skins.ok == true and type(skins.owned) == "table", type(skins) == "table" and tostring(skins.reason) or tostring(skins))
    local bite = fireNow(server, "CombatBite", p)
    check("dormant-valid: CombatBite is a no-op answer for a player who is not in a run", bite == nil, tostring(bite))
    reportErrors("dormant-valid", takeErrors())
end)

---------------------------------------------------------------- 12. client-owned movement handlers under a request storm (the envelope itself needs Studio; the cooldowns and counts do not)
runScenario("movement-handlers", nil, function(server)
    startServices(server, {heartbeat = true})
    local made = {}
    local realNew = server.Instance.new
    server.Instance.new = function(className) made[className] = (made[className] or 0) + 1 return realNew(className) end
    local p = connect(server, 1001)
    startRunNow(server, p)
    sleep(2)
    check("movement-handlers: the run is active", charOf(p):GetAttribute("RunState") == "Active", "")
    local cooldown = loadMod(server, "src/shared/ProgressionConfig").LeapCooldown
    -- RequestLeap: 3 requests a second for 130 s. The server accepts a leap only when the 60 s cooldown is over.
    local trails0 = made.Trail or 0
    local sent = 0
    local t0 = now
    while now - t0 < 130 do
        fireNow(server, "RequestLeap", p)
        sent += 1
        sleep(0.34)
    end
    local leaps = (made.Trail or 0) - trails0
    check("movement-handlers: " .. sent .. " RequestLeap in 130 s start at most 3 leaps (cooldown " .. cooldown .. " s)", leaps >= 1 and leaps <= 3, tostring(leaps))
    -- ClassDash as a Water dinosaur: cooldown 3 s, grounded only
    p:SetAttribute("EquippedSpeciesId", "mosasaurus")
    local dash = server.remotes.ClassDash
    local fired0 = #dash.fired
    t0 = now
    sent = 0
    while now - t0 < 30 do
        fireNow(server, "ClassDash", p)
        sent += 1
        sleep(0.34)
    end
    local dashes = #dash.fired - fired0
    check("movement-handlers: " .. sent .. " ClassDash in 30 s are answered at most once per 3 s (" .. dashes .. " answered)", dashes >= 1 and dashes <= 11, tostring(dashes))
    -- a Ground dinosaur gets nothing from ClassDash, and a request in the air gets nothing
    p:SetAttribute("EquippedSpeciesId", "compy")
    local fired1 = #dash.fired
    for _ = 1, 20 do fireNow(server, "ClassDash", p) sleep(0.4) end
    check("movement-handlers: ClassDash from a non-Water class is never answered", #dash.fired == fired1, tostring(#dash.fired - fired1))
    p:SetAttribute("EquippedSpeciesId", "mosasaurus")
    charOf(p).humanoid.FloorMaterial = Enum.Material.Air
    local fired2 = #dash.fired
    for _ = 1, 20 do fireNow(server, "ClassDash", p) sleep(0.4) end
    check("movement-handlers: ClassDash while airborne is never answered", #dash.fired == fired2, tostring(#dash.fired - fired2))
    charOf(p).humanoid.FloorMaterial = Enum.Material.Grass
    -- ClassGlide: any number of boolean flips; anything else is dropped
    for i = 1, 200 do fireNow(server, "ClassGlide", p, i % 2 == 0) sleep(0.05) end
    for _, junk in {1, "true", {}, nil} do fireNow(server, "ClassGlide", p, junk) end
    fireNow(server, "ClassGlide", p, true, true)
    -- HubTravel needs a player at home inside the hub: the spawn point of this mock is the hub
    local q = connect(server, 1002)
    sleep(1)
    local accepted, refused = 0, 0
    for i = 1, 100 do
        local r = fireNow(server, "HubTravel", q, {station = "nests"})
        if type(r) == "table" and r.ok == true then accepted += 1 else refused += 1 end
        sleep(0.1)
    end
    report("movement-handlers: HubTravel 100 requests in 10 s: accepted " .. accepted .. ", refused " .. refused)
    check("movement-handlers: HubTravel is limited to one request per 0.8 s", accepted <= 14, tostring(accepted))
    reportErrors("movement-handlers", takeErrors())
end)

---------------------------------------------------------------- 13. a lost acknowledgement in the middle of a hatch page
-- The first ClaimChest commits the head egg AND the next nine eggs of its page in one write. If the write lands but the answer is lost,
-- the retry finds the operation and answers "duplicate". The nine eggs ARE credited; their reveal must still be shown, not skipped.
runScenario("claim-lost-ack", nil, function(server)
    startServices(server)
    local p = connect(server, 1001)
    settle(server, p, 40, 600)
    sleep(10)
    local before = eggTotals(1001)
    local head = server.PS.get(p, "NextChestId")
    AMBIGUOUS_NEXT = 1
    local ok, outcome, status = server.Repo.claimChest(p, head)
    sleep(5)
    local credited = before - eggTotals(1001)
    local pending = server.Repo.pendingReveals(p)
    check("claim-lost-ack: the claim answered after the retry", ok == true, tostring(status))
    check("claim-lost-ack: the page was credited (" .. credited .. " eggs left the queue)", credited >= 2, tostring(credited))
    check("claim-lost-ack: every credited egg after the head is still waiting to be revealed (" .. pending .. " of " .. (credited - 1) .. ")", pending == credited - 1, "pending " .. pending .. " credited " .. credited)
    -- and an honest duplicate claim of the same head egg from a second thread never buffers the page twice
    local before2 = server.Repo.pendingReveals(p)
    local q = connect(server, 1002)
    settle(server, q, 40, 600)
    sleep(10)
    local headQ = server.PS.get(q, "NextChestId")
    sleep(8)
    parallel(8, function() server.Repo.claimChest(q, headQ) end)
    local pq = server.Repo.pendingReveals(q)
    check("claim-lost-ack: eight parallel claims of one head egg buffer its page once", pq <= 9, tostring(pq))
    reportErrors("claim-lost-ack", takeErrors())
end)

---------------------------------------------------------------- 14. random sequences on a lossy store: valid and hostile requests in any order, with leaves and rejoins in between
local function sequenceScenario(seed)
    return function(server)
        startServices(server)
        local rng = minstd(seed)
        local function roll(n) return 1 + math.floor(rng() * n) % n end
        local pc = progressionConfig(server)
        local rules = rulesOf(server)
        local a = seeded(server, 1001, function(profile)
            profile.progression = {crystals = 6000, auras = {}, equippedAura = "", potions = {}, buffs = {}, accountXP = 360000, conditionLevel = 0}
            profile.collection.compy.base = 70
        end)
        local c = connect(server, 3003) -- passive bystander
        settle(server, a, 70, 600)
        sleep(10)
        local start = wealthPoints(server, 1001)
        local bystanderBefore = wealth(3003)
        SCENARIO_FAIL_RATE, SCENARIO_AMBIGUOUS_RATE = 0.12, 0.18
        local species = server.Config.SpeciesOrder
        local actions = {"buyAura", "equipAura", "buyTrail", "equipTrail", "buyPotion", "usePotion", "buyEgg", "upgradeCondition", "buyPerk"}
        local reused = {}
        local function token(reuse)
            if reuse and #reused > 0 and rng() < 0.5 then return reused[roll(#reused)] end
            local t = tok("seq")
            table.insert(reused, t)
            return t
        end
        local peak = start
        for step = 1, 260 do
            local kind = roll(11)
            local win = windowOf(server)
            local offers = rules.shopOffers(win)
            if kind == 1 then
                local id = server.PS.get(a, "NextChestId")
                fireNow(server, "ClaimChest", a, if type(id) == "string" and id ~= "" and rng() < 0.8 then id else "run:garbage:1", token(true))
            elseif kind == 2 then
                local list = profileOf(1001).eggNests or {}
                fireNow(server, "ClaimNest", a, if #list > 0 and rng() < 0.7 then list[roll(#list)].nestId else "nest:garbage:1")
            elseif kind == 3 then
                fireNow(server, "EquipSpecies", a, species[roll(#species)], token(true))
            elseif kind == 4 then
                fireNow(server, "MutateSpecies", a, if rng() < 0.6 then "compy" else species[roll(#species)], if rng() < 0.7 then "gold" else "diamond", token(true))
            elseif kind <= 7 then
                local action = actions[roll(#actions)]
                local id = ""
                if action == "buyPotion" then local o = offers[roll(#offers)] id = o.id .. "@" .. win
                elseif action == "usePotion" then id = pc.Potions[roll(#pc.Potions)].id
                elseif action == "buyEgg" then id = "random"
                elseif action == "upgradeCondition" then id = tostring((profileOf(1001).progression.conditionLevel or 0) + 1)
                elseif action == "buyAura" or action == "equipAura" then id = pc.Auras[roll(#pc.Auras)].id
                elseif action == "buyTrail" or action == "equipTrail" then id = pc.Trails[roll(#pc.Trails)].id
                else id = "fastTravel" end
                fireNow(server, "ProgressionAction", a, action, id, token(true), rng() < 0.5)
            elseif kind == 8 then
                local donors = donorsFor and donorsFor(1001, 6)
                if donors then
                    local q = fireNow(server, "FusionAction", a, {action = "quote", targetStage = "gold", donorIds = donors})
                    if type(q) == "table" and q.ok then
                        fireNow(server, "FusionAction", a, {action = "fuse", token = token(true), targetStage = "gold", donorIds = donors, quoteDigest = q.quote.quoteDigest, consentDigest = q.quote.consentDigest})
                    end
                else
                    fireNow(server, "FusionAction", a, {action = "list"})
                end
            elseif kind == 9 then
                fireNow(server, "SetSettings", a, {effects = "lite", calm = rng() < 0.5})
                fireNow(server, "SetRevealSkip", a, {roll(5), roll(5)})
            elseif kind == 10 then
                if step % 5 == 0 then
                    a = reloads(server, "sequence-" .. seed, a, true)
                    if not a.loaded then return end
                end
            else
                fireNow(server, "PrivateState", a)
                fireNow(server, "HubTravel", a, {station = "nests"})
            end
            sleep(0.4 + rng() * 2.5)
            peak = math.max(peak, wealthPoints(server, 1001))
        end
        SCENARIO_FAIL_RATE, SCENARIO_AMBIGUOUS_RATE = 0, 0
        sleep(40)
        reportErrors("sequence-" .. seed, takeErrors())
        check("sequence-" .. seed .. ": 260 mixed requests on a lossy store never created value", peak <= start, "peak " .. peak .. " vs " .. start)
        check("sequence-" .. seed .. ": the bystander was untouched", wealth(3003) == bystanderBefore, "")
        report("sequence-" .. seed .. ": store calls failed before the write " .. M.transientErrors .. ", lost their acknowledgement " .. M.ambiguous .. ", wealth " .. start .. " -> " .. wealthPoints(server, 1001))
        reloads(server, "sequence-" .. seed, a)
    end
end
for _, seed in {11, 4242, 90210} do runScenario("sequence-" .. seed, {PaidRandomItemsEnabled = true}, sequenceScenario(seed)) end

---------------------------------------------------------------- 15. SkinAction (BD-456, behind DinoSkinsEnabled): ownership, instances of other players, no free skin
runScenario("skin-action", {DinoSkinsEnabled = true}, function(server)
    startServices(server)
    check("skin-action: the SkinAction remote exists with its flag on", server.remotes.SkinAction ~= nil, "")
    local a = connect(server, 1001)
    local b = connect(server, 1002)
    hatchEverything(server, a, 40)
    hatchEverything(server, b, 40)
    local ownA, ownB = nil, nil
    for id, inst in profileOf(1001).dinosaurIdentity.instances do ownA = id break end
    for id, inst in profileOf(1002).dinosaurIdentity.instances do ownB = id break end
    local before = wealth(1001) .. "|" .. wealth(1002)
    local function call(p, request) sleep(1.2) return fireNow(server, "SkinAction", p, request) end
    -- skins are an entitlement the account owns: a request cannot grant one
    local r1 = call(a, {action = "equip", instanceId = ownA, skin = "Plush"})
    local r2 = call(a, {action = "setDefault", skin = "Clay"})
    local r3 = call(a, {action = "equip", instanceId = ownB, skin = "Base"})
    local r4 = call(a, {action = "get", instanceId = ownB})
    check("skin-action: a skin the account does not own cannot be worn or made the default", r1.ok == false and r2.ok == false, tostring(r1.reason) .. "/" .. tostring(r2.reason))
    check("skin-action: another player's dinosaur id is refused for equip and get", r3.ok == false and r4.ok == false, tostring(r3.reason) .. "/" .. tostring(r4.reason))
    local ownedAfter = profileOf(1001).ownedSkins
    check("skin-action: no request ever writes ownedSkins", ownedAfter == nil or next(ownedAfter) == nil, canon(ownedAfter))
    -- the free Base look works on an own dinosaur
    local r5 = call(a, {action = "equip", instanceId = ownA, skin = "Base"})
    check("skin-action: the free Base look can be worn on an own dinosaur", r5.ok == true, tostring(r5.reason))
    -- an entitlement granted by the server (a gift or receipt) still needs a MODEL: no species has one yet
    server.Repo.release(a) disconnect(server, a)
    DATA[keyOf(1001)].ownedSkins = {Plush = true}
    a = connect(server, 1001)
    local ownA2 = nil
    for id in profileOf(1001).dinosaurIdentity.instances do ownA2 = id break end
    local r6 = call(a, {action = "equip", instanceId = ownA2, skin = "Plush"})
    check("skin-action: an owned skin without a species model is refused (no_model)", r6.ok == false and r6.reason == "no_model", tostring(r6.reason))
    -- a hostile storm of equips changes nothing but the dinosaur's own skin field
    for i = 1, 40 do
        sleep(1.2)
        fireNow(server, "SkinAction", a, {action = "equip", instanceId = (if i % 2 == 0 then ownB else ownA2), skin = ({"Plush", "Clay", "Bricks", "Balloon", "Base", "x"})[1 + i % 6]})
    end
    check("skin-action: the other player's profile never changed", wealth(1002) == string.match(before, "|(.*)$"), "")
    reportErrors("skin-action", takeErrors())
end)
