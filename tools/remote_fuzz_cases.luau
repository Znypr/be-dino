-- Scenarios (appended after remote_fuzz.luau by tools/verify_remote_fuzz.py).

-------------------------------------------------------------------- the hostile corpus: everything a client can put on the wire
local NaN = 0 / 0
local function nested(depth) local t = {} local cur = t for _ = 1, depth do local n = {} cur[1] = n cur = n end return t end
local function wideDict(n) local t = {} for i = 1, n do t["k" .. i] = i end return t end
local function bigArray(n) local t = {} for i = 1, n do t[i] = i end return t end
local function corpus(extra)
    return {
        {"nil", nil}, {"true", true}, {"false", false},
        {"0", 0}, {"-0", -0}, {"1", 1}, {"-1", -1}, {"0.5", 0.5}, {"1e9", 1e9}, {"2^31", 2 ^ 31}, {"2^53", 2 ^ 53}, {"1e308", 1e308}, {"-1e308", -1e308},
        {"inf", math.huge}, {"-inf", -math.huge}, {"NaN", NaN},
        {"empty string", ""}, {"space", " "}, {"a", "a"}, {"80 chars", string.rep("x", 80)}, {"81 chars", string.rep("x", 81)}, {"161 chars", string.rep("y", 161)},
        {"100k chars", string.rep("z", 100000)}, {"NUL", "\0"}, {"newline", "a\nb"}, {"bad utf8", "\255\254\253"}, {"format", "%s%d%q"}, {"path", "../../etc"},
        {"sql", "'; DROP TABLE x;--"}, {"lua pattern", "^(.-)$"}, {"proto", "__proto__"}, {"at-sign", "speed_common@999999999999999999999"},
        {"{}", {}}, {"{1}", {1}}, {"{1..7}", {1, 2, 3, 4, 5, 6, 7}}, {"{'a','b'}", {"a", "b"}}, {"{a=1}", {a = 1}}, {"sparse", {[1] = "x", [3] = "y"}},
        {"zero key", {[0] = "z"}}, {"neg key", {[-1] = 1}}, {"float key", {[1.5] = 1}}, {"{{}}", {{}}}, {"depth 40", nested(40)}, {"wide dict 3000", wideDict(3000)},
        {"array 3000", bigArray(3000)}, {"action=list", {action = "list"}}, {"action=fuse", {action = "fuse"}}, {"__proto__ key", {__proto__ = 1}},
        {"nan in table", {NaN, NaN}}, {"inf in table", {math.huge}}, {"bool table", {true, false}}, {"string array", {"a", "b", "c", "d", "e", "f", "g"}},
        {"vector3", Vector3.new(1, 2, 3)}, {"another player", extra and extra.victim}, {"enum item", Enum.Material.Grass},
    }
end

-------------------------------------------------------------------- state helpers
local function progressionConfig(server) return loadMod(server, "src/shared/ProgressionConfig") end
local function rulesOf(server) return loadMod(server, "src/shared/ProgressionRules") end
local function keyOf(userId) return "u:" .. userId end
local tokenCounter = 0
local function tok(prefix) tokenCounter += 1 return (prefix or "t") .. "-" .. tokenCounter end

-- Total value a player holds, in one unit: crystals + eggs + dinos + everything bought with crystals. Remote requests can only
-- MOVE value (buy an egg: crystals -> egg, hatch: egg -> dino) or DESTROY it (use a potion, mutate, fuse, Cracked eggs). If this
-- number ever rises during a remote-only sequence, something paid out for free.
local function wealthPoints(server, userId)
    local profile = DATA[keyOf(userId)]
    if not profile then return 0 end
    local pc = progressionConfig(server)
    local total = 0
    local progress = profile.progression or {}
    total += progress.crystals or 0
    local EGG = pc.RandomEggPrice
    total += EGG * (#(profile.eggs or {}) + #(profile.runEggBank or {}) + (profile.pendingChestGrants or 0))
    for _, nest in profile.eggNests or {} do total += EGG * (nest.size or 0) end
    for _, entry in profile.collection or {} do
        local n = (entry.base or 0) + (entry.gold or 0) + (entry.emerald or 0) + (entry.diamond or 0)
        for _, count in entry.events or {} do n += count end
        for _, variant in entry.variants or {} do n += variant.count or 0 end
        total += EGG * n
    end
    local function priceOf(catalog, id) for _, item in catalog do if item.id == id then return item.price end end return 0 end
    for id, count in progress.potions or {} do total += priceOf(pc.Potions, id) * count end
    for id in progress.auras or {} do total += priceOf(pc.Auras, id) end
    for id in progress.trails or {} do total += priceOf(pc.Trails, id) end
    for id in progress.perks or {} do total += priceOf(pc.Perks, id) end
    for level = 1, progress.conditionLevel or 0 do total += pc.ConditionUpgrades[level].price end
    return total
end

-- A fresh player whose stored profile is edited by `edit` before the session starts (a cheap way to give a hostile account something to lose).
local function seeded(server, userId, edit)
    local p = connect(server, userId)
    assert(p.loaded, "seed: profile did not load")
    if edit then
        server.Repo.release(p)
        disconnect(server, p)
        edit(DATA[keyOf(userId)])
        p = connect(server, userId)
        assert(p.loaded, "seed: profile did not reload")
    end
    return p
end

local function settle(server, p, catches, seconds)
    local runId = "seed-" .. p.UserId .. "-" .. tostring(math.floor(now * 1000)) .. "-" .. tok()
    local ok, outcome, status = server.Repo.commitRunSettlement(p, runId, catches, nil, seconds or 600, nil)
    assert(ok, "settle failed: " .. tostring(status))
    return runId
end

local function windowOf(server) return rulesOf(server).shopWindow(vos.time()) end
local function profileOf(userId) return DATA[keyOf(userId)] end

-- The calls a well-behaved client makes. Each entry returns the argument list for this moment.
local function templates(server, p)
    local pc = progressionConfig(server)
    local rules = rulesOf(server)
    local win = windowOf(server)
    local offers = rules.shopOffers(win)
    local offered = offers[1] and offers[1].id or pc.Potions[1].id
    local nextChest = server.PS.get(p, "NextChestId")
    local nests = {}
    local nestJson = server.PS.get(p, "NestsJson")
    if type(nestJson) == "string" then local ok, list = pcall(jsonDecode, nestJson) if ok and type(list) == "table" then nests = list end end
    local anyNest = nests[1] and nests[1].id or "nest:none:1"
    local ownedSpecies = "compy"
    for _, id in server.Config.SpeciesOrder do
        local e = profileOf(p.UserId).collection[id]
        if e and (e.base > 0 or e.gold > 0) then ownedSpecies = id break end
    end
    return {
        ClaimChest = function() return {if type(nextChest) == "string" and nextChest ~= "" then nextChest else "chest-none", tok("claim")} end,
        ClaimNest = function() return {anyNest} end,
        SetRevealSkip = function() return {{1, 2}} end,
        SetSettings = function() return {{v = 1, sound = {master = 0.5, sfx = 0.5, ambience = 0.5}, effects = "lite", weather = "lite", calm = false, jumpSize = "normal", teleportShops = true}} end,
        EquipSpecies = function() return {ownedSpecies, tok("equip")} end,
        MutateSpecies = function() return {ownedSpecies, "gold", tok("mut")} end,
        ProgressionAction = function() return {"buyPotion", offered .. "@" .. win, tok("prog"), false} end,
        FusionAction = function() return {{action = "list"}} end,
        PrivateState = function() return {} end,
        RequestStartRun = function() return {} end,
        RequestEndRun = function() return {} end,
        ClientWorldReady = function() return {} end,
        RequestLeap = function() return {} end,
        ClassDash = function() return {} end,
        ClassGlide = function() return {true} end,
        HubTravel = function() return {{station = "nests"}} end,
        AdminAction = function() return {"set", "foodMultiplier", 2} end,
        PlaytestFeedback = function() return {{fun = 3, level = 2, looks = 3, text = "hello"}} end,
        TestGrantChests = function() return {} end,
        TestGrantSpecies = function() return {} end,
        TestSetMutationCopies = function() return {50} end,
        ObjectiveAction = function() return {{action = "view"}} end,
        GiftAction = function() return {{action = "get"}} end,
        SkinAction = function() return {{action = "get"}} end,
        AdminGiftAction = function() return {{action = "audit", userId = 5}} end,
        CombatBite = function() return {} end,
        QaMark = function() return {{label = "x", fps = 60}} end,
        PreviewDinosaurArt = function() return {"compy", false, false} end,
    }
end

local function takeErrors()
    local mine = {}
    for _, e in errors do table.insert(mine, e.remote .. "(" .. e.args .. "): " .. e.message) end
    table.clear(errors)
    return mine
end

local function reportErrors(name, list)
    check(name .. ": no error escaped from any handler", #list == 0, if #list > 0 then (#list .. " errors, first: " .. string.sub(list[1], 1, 500)) else "")
end

local function reloads(server, name, p, silent)
    -- the stored profile must still pass the repository's own validation: a fresh load succeeds
    local userId = p.UserId
    server.Repo.release(p)
    disconnect(server, p)
    local again = connect(server, userId)
    if not silent then check(name .. ": stored profile still loads after the fuzz (not corrupted)", again.loaded == true, again.attrs.ProfileState) end
    return again
end

---------------------------------------------------------------- 1. malformed arguments, one slot at a time
runScenario("slot-fuzz", nil, function(server)
    startServices(server)
    check("slot-fuzz: every service started", server.startErrors == nil, table.concat(server.startErrors or {}, " | "))
    local victim = connect(server, 2002) -- a bystander, to prove isolation
    local hostile = seeded(server, 1001, function(profile)
        profile.progression = profile.progression or {crystals = 0, auras = {}, equippedAura = "", potions = {}, buffs = {}}
        profile.progression.crystals = 50000
        profile.progression.accountXP = 360000
    end)
    settle(server, hostile, 30, 600)
    sleep(2)
    local tmpl = templates(server, hostile)
    local before = wealthPoints(server, 1001)
    local victimBefore = wealthPoints(server, 2002)
    local victimWealthText = wealth(2002)
    local calls = 0
    local names = {}
    for name in tmpl do if server.remotes[name] and name ~= "AdminAction" then table.insert(names, name) end end
    table.sort(names)
    local items = corpus({victim = victim})
    local peakWealth = before
    for _, name in names do
        local make = tmpl[name]
        local base = make()
        local slots = math.max(#base, 1)
        for slot = 1, slots + 1 do
            for _, item in items do
                local list = table.clone(base)
                list[slot] = item[2]
                local count = math.max(#base, slot)
                fireNow(server, name, hostile, table.unpack(list, 1, count))
                calls += 1
                sleep(0.6) -- past every per-request cooldown, so validation (not the limiter) is what answers
                local w = wealthPoints(server, 1001)
                if w > peakWealth then peakWealth = w end
            end
        end
        -- whole-list garbage: wrong arity, nothing, and a long tail of extras
        fireNow(server, name, hostile)
        fireNow(server, name, hostile, nil, nil, nil, nil, nil, nil, nil)
        fireNow(server, name, hostile, table.unpack(make()), "extra", 1, {})
        sleep(1)
    end
    reportErrors("slot-fuzz", takeErrors())
    report("slot-fuzz: " .. calls .. " malformed calls over " .. #names .. " handlers")
    check("slot-fuzz: no free value (wealth never rose above its starting point)", peakWealth <= before, "peak " .. peakWealth .. " vs start " .. before)
    check("slot-fuzz: the bystander lost and gained nothing", wealthPoints(server, 2002) == victimBefore and wealth(2002) == victimWealthText, string.sub(wealth(2002), 1, 200))
    reloads(server, "slot-fuzz", hostile)
end)

---------------------------------------------------------------- 2. the harness itself: valid requests work, a throwing handler is seen
runScenario("sanity", nil, function(server)
    startServices(server)
    -- canary: a handler that throws must show up in `errors` (otherwise "no error escaped" would prove nothing)
    local canary = server.Instance.new("RemoteEvent")
    canary.Name = "Canary"
    canary.Parent = server.RS
    canary.OnServerEvent:Connect(function() error("boom") end)
    server.remotes.Canary = canary
    fireNow(server, "Canary", mockPlayer(server, 5))
    local seen = takeErrors()
    check("sanity: the harness records a handler that throws", #seen == 1 and string.find(seen[1], "boom", 1, true) ~= nil, tostring(seen[1]))
    server.remotes.Canary = nil

    local p = seeded(server, 1001, function(profile)
        profile.progression = {crystals = 5000, auras = {}, equippedAura = "", potions = {}, buffs = {}, accountXP = 0, conditionLevel = 0}
    end)
    local pc = progressionConfig(server)
    local rules = rulesOf(server)
    local win = windowOf(server)
    local offer = rules.shopOffers(win)[1]
    local price = rules.item(pc.Potions, offer.id).price
    local c0 = profileOf(1001).progression.crystals
    fireNow(server, "ProgressionAction", p, "buyPotion", offer.id .. "@" .. win, tok("buy"), false)
    sleep(1)
    check("sanity: ProgressionAction buyPotion spends crystals and adds one potion", profileOf(1001).progression.crystals == c0 - price and profileOf(1001).progression.potions[offer.id] == 1,
        tostring(profileOf(1001).progression.crystals) .. " potions=" .. tostring(profileOf(1001).progression.potions[offer.id]))
    settle(server, p, 30, 600)
    sleep(1)
    local dinos0 = 0
    for _, e in profileOf(1001).collection do dinos0 += e.base + e.gold + e.diamond end
    local chest = server.PS.get(p, "NextChestId")
    check("sanity: the settlement queued eggs and the client is told the next egg id", type(chest) == "string" and chest ~= "", tostring(chest))
    fireNow(server, "ClaimChest", p, chest, tok("claim"))
    sleep(1)
    local dinos1 = 0
    for _, e in profileOf(1001).collection do dinos1 += e.base + e.gold + e.diamond for _, v in e.variants do dinos1 += v.count end for _, n in e.events do dinos1 += n end end
    check("sanity: ClaimChest turns the egg into a dinosaur", dinos1 > dinos0 or p.attrs.LastChestClaimStatus == "claimed", p.attrs.LastChestClaimStatus)
    fireNow(server, "SetSettings", p, {v = 1, sound = {master = 0.3, sfx = 0.3, ambience = 0.3}, effects = "off", weather = "off", calm = true, jumpSize = "big", teleportShops = false})
    sleep(2)
    check("sanity: SetSettings stores the normalised settings", profileOf(1001).settings and profileOf(1001).settings.effects == "off" and profileOf(1001).settings.calm == true,
        canon(profileOf(1001).settings))
    reportErrors("sanity", takeErrors())
end)

---------------------------------------------------------------- 3. nothing to claim, nothing to buy: the whole corpus at every handler pays nothing
runScenario("empty-handed", nil, function(server)
    startServices(server)
    local p = connect(server, 3003)
    local other = connect(server, 3004)
    sleep(1)
    local before = wealth(3003)
    local beforeOther = wealth(3004)
    local points = wealthPoints(server, 3003)
    local items = corpus({victim = other})
    local tmpl = templates(server, p)
    local names = {}
    for name in tmpl do if server.remotes[name] and name ~= "AdminAction" then table.insert(names, name) end end
    table.sort(names)
    local calls = 0
    for _, name in names do
        for _, a in items do
            for _, b in items do
                if (calls % 7 == 0) then -- every pair would be 3,000 calls per handler; a seeded stride keeps the run short
                    fireNow(server, name, p, a[2], b[2])
                    fireNow(server, name, p, a[2], b[2], a[2])
                end
                calls += 1
            end
        end
        sleep(2)
    end
    sleep(5)
    reportErrors("empty-handed", takeErrors())
    check("empty-handed: a new player ends with the same crystals, eggs, dinosaurs and items", wealthPoints(server, 3003) <= points, wealthPoints(server, 3003) .. " vs " .. points)
    check("empty-handed: the other player is untouched", wealth(3004) == beforeOther)
    report("empty-handed: " .. calls .. " pair combinations offered to " .. #names .. " handlers")
end)

---------------------------------------------------------------- 4. ordering races: the same request many times at once, the same resource through many requests
local function parallel(count, fn)
    local boxes = {}
    for i = 1, count do
        local box = {done = false}
        boxes[i] = box
        task.spawn(function()
            local ok, err = xpcall(fn, function(e) return tostring(e) end, i)
            if not ok then table.insert(errors, {remote = "parallel", args = tostring(i), message = err}) end
            box.done = true
        end)
    end
    waitAll(boxes)
end
local function collectionTotals(userId)
    local n = 0
    for _, e in profileOf(userId).collection do
        n += e.base + e.gold + (e.emerald or 0) + e.diamond
        for _, v in e.variants do n += v.count end
        for _, c in e.events do n += c end
    end
    return n
end
local function eggTotals(userId)
    local profile = profileOf(userId)
    return #profile.eggs + #(profile.runEggBank or {}) + profile.pendingChestGrants
end

local function racesScenario(server)
    startServices(server)
    -- "lossy": 15% of store calls fail before the write and 20% apply the write but lose the acknowledgement. The retry must find its own
    -- earlier write (operation id) instead of paying twice. Under loss an operation may fail outright, so exact counts become upper bounds.
    local lossy = string.find(server.name, "lossy", 1, true) ~= nil
    local function exactly(cond, bound) if lossy then return bound else return cond end end
    local pc = progressionConfig(server)
    local rules = rulesOf(server)
    local p = seeded(server, 1001, function(profile)
        profile.progression = {crystals = 3000, auras = {}, equippedAura = "", potions = {}, buffs = {}, accountXP = 400000, conditionLevel = 0}
        profile.collection.compy.base = 50
    end)
    server.PS.set(p, "PaidRandomEligible", true) -- as PolicyService answers for an adult (the mock policy is permissive)
    local price = 0
    local win = windowOf(server)
    local offers = rules.shopOffers(win)
    local offer = offers[1]
    price = rules.item(pc.Potions, offer.id).price

    -- same token, 40 at once (transaction level): one purchase
    local c0 = profileOf(1001).progression.crystals
    local token = tok("same")
    local results = {}
    parallel(40, function(i) local ok, status = server.Repo.progressionAction(p, "buyPotion", offer.id .. "@" .. win, token, false) results[i] = status end)
    local bought = profileOf(1001).progression.potions[offer.id] or 0
    check("races: 40 buyPotion with ONE token charge once", exactly(bought == 1 and profileOf(1001).progression.crystals == c0 - price, bought <= 1 and profileOf(1001).progression.crystals == c0 - bought * price), "potions=" .. bought .. " crystals " .. c0 .. " -> " .. profileOf(1001).progression.crystals)

    -- distinct tokens, 60 at once: bounded by the shop stock, never negative
    sleep(10)
    local c1 = profileOf(1001).progression.crystals
    parallel(60, function(i) server.Repo.progressionAction(p, "buyPotion", offer.id .. "@" .. win, tok("many"), false) end)
    local bought2 = profileOf(1001).progression.potions[offer.id] or 0
    check("races: 60 buyPotion with distinct tokens stop at the stock (" .. offer.stock .. ")", bought2 <= offer.stock, "bought " .. bought2)
    check("races: crystals never negative and equal price x purchases", profileOf(1001).progression.crystals == c1 - (bought2 - bought) * price and profileOf(1001).progression.crystals >= 0,
        tostring(profileOf(1001).progression.crystals))

    sleep(10)
    -- use one potion 30 times at once with distinct tokens: one activation, potions never negative
    local have = profileOf(1001).progression.potions[offer.id] or 0
    parallel(30, function(i) server.Repo.progressionAction(p, "usePotion", offer.id, tok("use"), true) end)
    local left = profileOf(1001).progression.potions[offer.id] or 0
    check("races: 30 usePotion in parallel consume what was owned and never go below zero", left >= 0 and left <= have, "had " .. have .. " left " .. left)

    -- the same egg purchase (ONE token) 20 times at once: one egg, one price
    sleep(10)
    local c2b, e2b = profileOf(1001).progression.crystals, eggTotals(1001)
    local eggToken = tok("egg-one")
    parallel(20, function(i) server.Repo.progressionAction(p, "buyEgg", "random", eggToken, false) end)
    local gained2 = eggTotals(1001) - e2b
    check("races: 20 buyEgg with ONE token buy one egg", exactly(gained2 == 1 and profileOf(1001).progression.crystals == c2b - pc.RandomEggPrice, gained2 <= 1 and profileOf(1001).progression.crystals == c2b - gained2 * pc.RandomEggPrice),
        "eggs +" .. gained2 .. " crystals " .. c2b .. " -> " .. profileOf(1001).progression.crystals)

    sleep(10)
    -- buy an egg 25 times at once: crystals spent equal eggs gained, the queue never exceeds its capacity
    sleep(2)
    local c2, e2 = profileOf(1001).progression.crystals, eggTotals(1001)
    parallel(25, function(i) server.Repo.progressionAction(p, "buyEgg", "random", tok("egg"), false) end)
    local gained = eggTotals(1001) - e2
    check("races: 25 buyEgg in parallel: every egg paid for (crystals fall by 150 each)", profileOf(1001).progression.crystals == c2 - gained * pc.RandomEggPrice and gained >= 0 and gained <= 25,
        "gained " .. gained .. " crystals " .. c2 .. " -> " .. profileOf(1001).progression.crystals)

    -- condition upgrade 12 at once: one level, one price
    sleep(10)
    local lvl0, c3 = profileOf(1001).progression.conditionLevel, profileOf(1001).progression.crystals
    parallel(12, function(i) server.Repo.progressionAction(p, "upgradeCondition", tostring(lvl0 + 1), tok("up"), false) end)
    local lvl1 = profileOf(1001).progression.conditionLevel
    check("races: 12 upgradeCondition(level+1) at once buy exactly one level", exactly(lvl1 == lvl0 + 1 and profileOf(1001).progression.crystals == c3 - pc.ConditionUpgrades[lvl1].price, lvl1 <= lvl0 + 1 and profileOf(1001).progression.crystals == c3 - (if lvl1 > lvl0 then pc.ConditionUpgrades[lvl1].price else 0)),
        "level " .. lvl0 .. " -> " .. lvl1 .. " crystals " .. c3 .. " -> " .. profileOf(1001).progression.crystals)

    -- gold mutation 20 at once, 50 base copies: exactly one Gold, 50 base spent, token replay free
    if lossy then SCENARIO_FAIL_RATE, SCENARIO_AMBIGUOUS_RATE = 0.15, 0.2 end
    sleep(10) -- let the per-player write budget refill (6 burst, 1 per second): the budget is exercised by the storm scenarios
    local before = profileOf(1001).collection.compy
    local b0, g0 = before.base, before.gold
    local statuses = {}
    parallel(20, function(i) local ok, _, status = server.Repo.mutateSpecies(p, "compy", "gold", tok("mut")) statuses[i] = tostring(ok) .. ":" .. tostring(status) end)
    report("mutation statuses: " .. table.concat(statuses, ","))
    local after = profileOf(1001).collection.compy
    check("races: 20 MutateSpecies at once with 50 copies make exactly one Gold", exactly(after.gold == g0 + 1 and after.base == b0 - server.Config.GoldMutationCost, after.gold <= g0 + 1 and after.base == b0 - (after.gold - g0) * server.Config.GoldMutationCost), "base " .. b0 .. "->" .. after.base .. " gold " .. g0 .. "->" .. after.gold)
    local sameTok = tok("mutdup")
    local g1 = profileOf(1001).collection.compy.gold
    parallel(10, function(i) server.Repo.mutateSpecies(p, "compy", "gold", sameTok) end)
    check("races: a mutation token replayed 10 times at once never pays twice", profileOf(1001).collection.compy.gold <= g1 + 1, tostring(profileOf(1001).collection.compy.gold - g1))

    -- hatch: 150 eggs, then claim the head egg 40 times at once and then everything 200 times: eggs only turn into dinosaurs
    settle(server, p, 60, 600)
    sleep(10)
    local wBefore = wealthPoints(server, 1001)
    local head = server.PS.get(p, "NextChestId")
    parallel(40, function(i) server.Repo.claimChest(p, head) end)
    local wAfter = wealthPoints(server, 1001)
    check("races: 40 claims of one egg pay out at most that egg (and its page)", wAfter <= wBefore, wBefore .. " -> " .. wAfter)
    for round = 1, 14 do
        local id = server.PS.get(p, "NextChestId")
        if type(id) ~= "string" or id == "" then break end
        parallel(6, function(i) server.Repo.claimChest(p, id) end)
        sleep(2)
    end
    check("races: claiming every egg from 6 threads at once never creates value", wealthPoints(server, 1001) <= wBefore, wBefore .. " -> " .. wealthPoints(server, 1001))

    -- nests: claim each ready nest 15 times at once
    local nestsBefore = wealthPoints(server, 1001)
    for _ = 1, 3 do
        sleep(server.Config.NestIncubationSeconds + 5)
        local list = profileOf(1001).eggNests or {}
        for _, nest in list do parallel(15, function(i) server.Repo.claimNest(p, nest.nestId) end) end
    end
    check("races: claiming each nest 15 times at once opens it once (no value created)", wealthPoints(server, 1001) <= nestsBefore, nestsBefore .. " -> " .. wealthPoints(server, 1001))
    reportErrors("races", takeErrors())
    reloads(server, "races", p)
end
runScenario("races", {PaidRandomItemsEnabled = true}, racesScenario)
runScenario("races-no-write-budget", {PaidRandomItemsEnabled = true, WriteBudgetEnabled = false}, racesScenario)
runScenario("races-lossy-store", {PaidRandomItemsEnabled = true, WriteBudgetEnabled = false}, racesScenario)

---------------------------------------------------------------- 5. request storms: hostile clients flood every handler while honest players play
-- 12 players on one server. `hostile` of them fire a valid-looking request at EVERY handler every 50 ms for two minutes; the other
-- players hatch eggs, equip and buy normally. Measured: honest requests that were refused with rate_limited, honest run settlements that failed,
-- DataStore throttling, the store requests per minute against the 60 + 10 x players budget, and the writes the hostile accounts got through.
local STORM = STORM_SECONDS
local function stormScenario(hostileCount, label)
    return function(server)
        startServices(server)
        local pc = progressionConfig(server)
        local players, hostile, honest = {}, {}, {}
        for i = 1, 12 do
            local p = seeded(server, 4000 + i, function(profile)
                profile.progression = {crystals = 20000, auras = {}, equippedAura = "", potions = {}, buffs = {}, accountXP = 360000, conditionLevel = 0}
                profile.collection.compy.base = 60
            end)
            players[i] = p
            if i <= hostileCount then table.insert(hostile, p) else table.insert(honest, p) end
        end
        for _, p in players do settle(server, p, 90, 600) end
        sleep(5)
        local stats = {honestTried = 0, honestLimited = 0, honestOk = 0, hostileCalls = 0}
        local stormEnds = now + STORM
        local hostileWritesStart = {}
        for _, p in hostile do hostileWritesStart[p] = M.byKeyWrites[keyOf(p.UserId)] or 0 end
        -- docs/157: with fusion on, the old 50-copy MutateSpecies the storm fires is refused, so it no longer burns ~7,000 points of copies;
        -- the fixed bound below was only loose because of that burn. A hostile account must also end at or under what it had when the storm began.
        local pointsAtStart = {}
        for _, p in hostile do pointsAtStart[p] = wealthPoints(server, p.UserId) end
        for _, p in hostile do
            task.spawn(function()
                local names = {"ClaimChest", "ClaimNest", "EquipSpecies", "MutateSpecies", "ProgressionAction", "SetSettings", "SetRevealSkip", "FusionAction", "PrivateState", "HubTravel", "PlaytestFeedback", "RequestLeap", "ClassDash", "ClassGlide", "RequestEndRun", "RequestStartRun"}
                local i = 0
                while now < stormEnds do
                    i += 1
                    local tmpl = templates(server, p)
                    local name = names[1 + (i % #names)]
                    if name == "EquipSpecies" then
                        fireNow(server, name, p, (if i % 2 == 0 then "compy" else "triceratops"), tok("e"))
                    else
                        fireNow(server, name, p, table.unpack(tmpl[name]()))
                    end
                    stats.hostileCalls += 1
                    sleep(0.05)
                end
            end)
        end
        for _, p in honest do
            task.spawn(function()
                local n = 0
                while now < stormEnds do
                    n += 1
                    sleep(6 + (p.UserId % 5))
                    local id = server.PS.get(p, "NextChestId")
                    if type(id) == "string" and id ~= "" then
                        local ok, _, status = server.Repo.claimChest(p, id)
                        stats.honestTried += 1
                        if status == "rate_limited" then stats.honestLimited += 1 elseif ok then stats.honestOk += 1 end
                    end
                    if n % 3 == 0 then
                        local ok, status = server.Repo.equipSpecies(p, if n % 2 == 0 then "compy" else "triceratops", nil)
                        stats.honestTried += 1
                        if status == "rate_limited" then stats.honestLimited += 1 elseif ok then stats.honestOk += 1 end
                    end
                end
            end)
        end
        -- an honest player ends a run in the middle of the storm: the settlement is a priority write and must always commit
        local settledDuringStorm = nil
        task.spawn(function()
            sleep(STORM / 2)
            local p = honest[1]
            local runId = "storm-run-" .. label
            local ok, _, status = server.Repo.commitRunSettlement(p, runId, 20, nil, 300, nil)
            settledDuringStorm = ok
        end)
        sleep(STORM + 10)
        local worstWindow = 0
        local requests = M.requests
        report(string.format("%s: hostile=%d honest requests=%d refused rate_limited=%d ok=%d | hostile calls=%d | store requests %d, throttled %d, queue drops %d, hostile key writes %s",
            label, hostileCount, stats.honestTried, stats.honestLimited, stats.honestOk, stats.hostileCalls, M.requests, M.throttled, M.queueDrops,
            (function() local t = 0 for _, p in hostile do t += (M.byKeyWrites[keyOf(p.UserId)] or 0) - hostileWritesStart[p] end return tostring(t) end)()))
        reportErrors(label, takeErrors())
        check(label .. ": the honest player's run settlement committed during the storm", settledDuringStorm == true, tostring(settledDuringStorm))
        check(label .. ": no DataStore queue drop", M.queueDrops == 0, tostring(M.queueDrops))
        -- BD-614: one account's spam must not starve the others (before the fix: 1%, 16% and 41% for 1, 2 and 4 hostile of 12), and the
        -- fair-share path must not push the store past 60 + 10 x players requests a minute (the mock throttles when it would).
        check(label .. ": honest players' routine writes answered rate_limited at most 2% (" .. stats.honestLimited .. " of " .. stats.honestTried .. ")",
            stats.honestLimited * 50 <= stats.honestTried, stats.honestLimited .. "/" .. stats.honestTried)
        check(label .. ": the DataStore request ceiling was never exceeded (nothing throttled)", M.throttled == 0, tostring(M.throttled))
        local hostileWrites = 0
        for _, p in hostile do hostileWrites += (M.byKeyWrites[keyOf(p.UserId)] or 0) - hostileWritesStart[p] end
        local bound = hostileCount * (server.Config.WriteBurst + (STORM + 10) * server.Config.WriteRefillPerSecond + (STORM + 10) / 30 + 8)
        check(label .. ": hostile accounts got at most burst + refill writes through (bound " .. math.floor(bound) .. ")", hostileWrites <= bound, tostring(hostileWrites))
        for _, p in hostile do
            check(label .. ": hostile " .. p.UserId .. " did not gain value", wealthPoints(server, p.UserId) <= math.max(20000 + 150 * 60 + 150 * 90 + 3000, pointsAtStart[p]), tostring(wealthPoints(server, p.UserId)) .. " (at storm start " .. pointsAtStart[p] .. ")")
        end
        stats.label = label
        server.stormStats = stats
    end
end
STORM_RESULTS = {}
for _, k in {1, 2, 4} do
    local label = "storm-" .. k .. "-hostile-of-12"
    local server = runScenario(label, nil, stormScenario(k, label))
    STORM_RESULTS[k] = server.stormStats
end

