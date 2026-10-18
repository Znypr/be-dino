
---------------------------------------------------------------- 8. fusion and other players' data (the playtest has the identity sidecar and FusionAction on)
local function hatchEverything(server, p, catches)
    settle(server, p, catches, 600)
    sleep(10)
    for _ = 1, 800 do
        local id = server.PS.get(p, "NextChestId")
        if type(id) ~= "string" or id == "" then break end
        local ok, _, status = server.Repo.claimChest(p, id)
        if status == "rate_limited" then sleep(1.5) end
        if not ok and status ~= "rate_limited" then break end
    end
    sleep(2)
end
local function donorsFor(userId, count)
    local state = profileOf(userId).dinosaurIdentity
    local bySpecies = {}
    for id, inst in state and state.instances or {} do
        if inst.stage == "base" and inst.traitsKnown == true and type(inst.genes) == "table" and inst.genes.patternId and inst.locked ~= true then
            bySpecies[inst.speciesId] = bySpecies[inst.speciesId] or {}
            table.insert(bySpecies[inst.speciesId], id)
        end
    end
    local best, bestSpecies = nil, nil
    for species, list in bySpecies do
        table.sort(list)
        if #list >= count and (best == nil or #list > #best) then best, bestSpecies = list, species end
    end
    if not best then return nil, nil end
    local picked = {}
    for i = 1, count do picked[i] = best[i] end
    return picked, bestSpecies
end

runScenario("fusion-and-isolation", nil, function(server)
    startServices(server)
    check("fusion-and-isolation: the playtest config turns the identity sidecar and fusion on", server.Config.IdentityPersistentEnabled == true and server.Config.IdentityFusionPreviewEnabled == true, "")
    local a = connect(server, 1001)
    local b = connect(server, 1002)
    hatchEverything(server, a, 150)
    hatchEverything(server, b, 150)
    local donorsA, speciesA = donorsFor(1001, 6)
    local donorsB, speciesB = donorsFor(1002, 6)
    check("fusion-and-isolation: both players hatched six same-species dinosaurs to fuse", donorsA ~= nil and donorsB ~= nil, tostring(donorsA) .. tostring(donorsB))
    if not donorsA or not donorsB then return end
    local invoke = function(p, request) sleep(1.2) return fireNow(server, "FusionAction", p, request) end

    -- 1. reading: a player sees only their own dinosaurs
    local list = invoke(a, {action = "list", limit = 200})
    local ownIds = {}
    local leakedFromB = 0
    for _, d in list.dinosaurs or {} do
        ownIds[d.instanceId] = true
        if string.find(d.instanceId, "u:1002/", 1, true) then leakedFromB += 1 end
    end
    check("fusion-and-isolation: list returns the caller's own dinosaurs only", list.ok == true and leakedFromB == 0 and next(ownIds) ~= nil, tostring(list.reason) .. " leaked " .. leakedFromB)
    local d1 = invoke(a, {action = "details", instanceId = donorsB[1]})
    check("fusion-and-isolation: details of ANOTHER player's dinosaur id is refused", d1.ok == false, tostring(d1.ok) .. tostring(d1.reason))
    local q1 = invoke(a, {action = "quote", targetStage = "gold", donorIds = donorsB})
    check("fusion-and-isolation: quote with another player's donors is refused", q1.ok == false, tostring(q1.reason))
    local mixed = table.clone(donorsA) mixed[6] = donorsB[1]
    local q2 = invoke(a, {action = "quote", targetStage = "gold", donorIds = mixed})
    check("fusion-and-isolation: quote mixing one foreign donor in is refused", q2.ok == false, tostring(q2.reason))
    local f1 = invoke(a, {action = "fuse", token = tok("fu"), targetStage = "gold", donorIds = donorsB, quoteDigest = "00000000000000000", consentDigest = nil})
    check("fusion-and-isolation: fuse with another player's donors is refused and consumes nothing", f1.ok == false, tostring(f1.reason))
    local bBefore = wealth(1002)

    -- 2. one fusion, many tries
    local quote = invoke(a, {action = "quote", targetStage = "gold", donorIds = donorsA})
    check("fusion-and-isolation: a valid quote for six owned donors is priced", quote.ok == true and quote.quote ~= nil, tostring(quote.reason))
    local entry0 = profileOf(1001).collection[speciesA]
    local gold0, dinos0 = entry0.gold, 0
    for _, e in profileOf(1001).collection do dinos0 += e.base + e.gold + (e.emerald or 0) + e.diamond for _, v in e.variants do dinos0 += v.count end end
    local request = function(token) return {action = "fuse", token = token, targetStage = "gold", donorIds = donorsA, quoteDigest = quote.quote.quoteDigest, consentDigest = quote.quote.consentDigest} end
    sleep(8) -- write budget
    -- 10 different tokens at once with the same six donors (bypassing the per-player request window): exactly one fusion can commit
    local results = {}
    parallel(10, function(i) results[i] = server.Repo.fuseDinosaurs(a, {token = tok("par"), targetStage = "gold", donorIds = donorsA, quoteDigest = quote.quote.quoteDigest, consentDigest = quote.quote.consentDigest}) end)
    local committed = 0
    local dinos1 = 0
    for _, e in profileOf(1001).collection do dinos1 += e.base + e.gold + (e.emerald or 0) + e.diamond for _, v in e.variants do dinos1 += v.count end end
    local instances = 0
    for _ in profileOf(1001).dinosaurIdentity.instances do instances += 1 end
    local goldNow = profileOf(1001).collection[speciesA].gold
    check("fusion-and-isolation: ten parallel fuse tokens on the same six donors commit one fusion (six dinosaurs become one Gold)", goldNow == gold0 + 1 and dinos1 == dinos0 - 5, "gold " .. gold0 .. "->" .. goldNow .. " dinos " .. dinos0 .. "->" .. dinos1)
    local ledgerSize = 0
    for _ in profileOf(1001).dinosaurIdentity.fusions or {} do ledgerSize += 1 end
    check("fusion-and-isolation: the ledger holds exactly one fusion", ledgerSize == 1, tostring(ledgerSize))
    -- replay of a committed token is free and identical
    local tokenA = tok("replay")
    sleep(8)
    local donorsA2 = donorsFor(1001, 6)
    if donorsA2 then
        local q = invoke(a, {action = "quote", targetStage = "gold", donorIds = donorsA2})
        if q.ok then
            local r1 = invoke(a, {action = "fuse", token = tokenA, targetStage = "gold", donorIds = donorsA2, quoteDigest = q.quote.quoteDigest, consentDigest = q.quote.consentDigest})
            local goldMid = profileOf(1001).collection[(donorsA2[1] and profileOf(1001).dinosaurIdentity.fusions[("fusion:" .. tokenA)] and profileOf(1001).dinosaurIdentity.fusions[("fusion:" .. tokenA)].speciesId) or speciesA].gold
            local r2 = invoke(a, {action = "fuse", token = tokenA, targetStage = "gold", donorIds = donorsA2, quoteDigest = q.quote.quoteDigest, consentDigest = q.quote.consentDigest})
            local goldEnd = profileOf(1001).collection[profileOf(1001).dinosaurIdentity.fusions[("fusion:" .. tokenA)].speciesId].gold
            check("fusion-and-isolation: replaying a fuse token returns the first result and spends nothing", r1.ok == true and r2.ok == true and r2.status == "duplicate" and goldEnd == goldMid, tostring(r1.status) .. "/" .. tostring(r2.status))
            local r3 = invoke(a, {action = "fuse", token = tokenA, targetStage = "diamond", donorIds = donorsA2, quoteDigest = q.quote.quoteDigest, consentDigest = q.quote.consentDigest})
            check("fusion-and-isolation: the same token with a different request is a conflict", r3.ok == false, tostring(r3.reason))
        end
    end
    check("fusion-and-isolation: the other player's profile never changed", wealth(1002) == bBefore, "")

    -- 3. the request window: more than the limit inside one window is refused, per player
    local limit = server.Config.FusionRequestsPerWindow
    local refused = 0
    for i = 1, limit + 15 do
        local r = fireNow(server, "FusionAction", a, {action = "list", limit = 1})
        if type(r) == "table" and r.reason == "rate_limited" then refused += 1 end
    end
    check("fusion-and-isolation: FusionAction refuses requests over the window limit (" .. limit .. ")", refused >= 15, tostring(refused))
    local other = fireNow(server, "FusionAction", b, {action = "list", limit = 1})
    check("fusion-and-isolation: one player's flood does not limit another player", type(other) == "table" and other.reason ~= "rate_limited", tostring(other and other.reason))

    -- 4. malformed requests: every one is refused with a table, nothing escapes
    sleep(server.Config.FusionRateWindowSeconds + 1)
    local items = corpus({victim = b})
    local bad = 0
    for _, item in items do
        for _, request in {item[2], {action = item[2]}, {action = "list", cursor = item[2]}, {action = "list", limit = item[2]}, {action = "details", instanceId = item[2]},
            {action = "quote", targetStage = item[2], donorIds = donorsA}, {action = "quote", targetStage = "gold", donorIds = item[2]},
            {action = "fuse", token = item[2], targetStage = "gold", donorIds = donorsA, quoteDigest = "x"}, {action = "fuse", token = "t", targetStage = "gold", donorIds = donorsA, quoteDigest = item[2]},
            {action = "list", extra = item[2]}} do
            if (bad + 1) % 25 == 0 then sleep(server.Config.FusionRateWindowSeconds + 1) end
            bad += 1
            local r = fireNow(server, "FusionAction", a, request)
            if type(r) ~= "table" then check("fusion-and-isolation: FusionAction answers a table to " .. item[1], false, type(r)) end
        end
    end
    reportErrors("fusion-and-isolation", takeErrors())
    reloads(server, "fusion-and-isolation", a)
end)

---------------------------------------------------------------- 9. other players' ids in every handler that takes an id
runScenario("cross-player", nil, function(server)
    startServices(server)
    local a = connect(server, 1001)
    local b = connect(server, 1002)
    hatchEverything(server, b, 90)
    settle(server, b, 90, 600)
    sleep(10)
    local nestsB = profileOf(1002).eggNests or {}
    local eggB = profileOf(1002).eggs[1] and profileOf(1002).eggs[1].eggId
    local variantB, speciesB = nil, nil
    for id, e in profileOf(1002).collection do
        for key, v in e.variants do if v.count > 0 then variantB, speciesB = key, id break end end
        if variantB then break end
    end
    local before = wealth(1002)
    local aBefore = wealthPoints(server, 1001)
    -- A uses B's egg, nest and variant ids
    if eggB then fireNow(server, "ClaimChest", a, eggB, tok("x")) end
    sleep(1)
    for _, nest in nestsB do fireNow(server, "ClaimNest", a, nest.nestId) sleep(1) end
    if variantB then fireNow(server, "EquipSpecies", a, speciesB, tok("x"), variantB) end
    sleep(1)
    check("cross-player: B's egg and nest ids claimed by A change nothing for either player", wealth(1002) == before and wealthPoints(server, 1001) <= aBefore, "")
    check("cross-player: A cannot equip a variant that only B owns", a.attrs.LastEquipStatus == "not_owned" or a.attrs.LastEquipStatus == "locked", tostring(a.attrs.LastEquipStatus))
    -- BD-1000: the "plain" key is a claim like any other: a species A does not hold cannot be equipped plain
    fireNow(server, "EquipSpecies", a, "mosasaurus", tok("plain"), "plain")
    sleep(1)
    check("cross-player: A cannot equip a species A does not hold as 'plain'", a.attrs.LastEquipStatus == "locked" or a.attrs.LastEquipStatus == "not_owned", tostring(a.attrs.LastEquipStatus))
    -- every message the server sent in answer to A's requests went to A, never to B
    local leaked = 0
    for name, remote in server.remotes do
        for _, f in remote.fired do if f.to == b and name ~= "PrivateState" and name ~= "RareHatch" then leaked += 1 end end
    end
    check("cross-player: no remote answer to player A was delivered to player B (outside the documented broadcasts)", leaked == 0, tostring(leaked))
    -- public Player attributes of both players contain only classified, small values
    local Core = loadMod(server, "src/shared/PrivateStateCore")
    local badNames, biggest = {}, 0
    for _, who in {a, b} do
        for name, value in who.attrs do
            if Core.classify(name) ~= "public" then table.insert(badNames, name) end
            if type(value) == "string" then biggest = math.max(biggest, #value) end
        end
    end
    check("cross-player: every Player attribute is on the public list (nothing private rides an attribute)", #badNames == 0, table.concat(badNames, ","))
    check("cross-player: no public attribute value is large (< 2 KB)", biggest < 2048, tostring(biggest))
    reportErrors("cross-player", takeErrors())
end)
