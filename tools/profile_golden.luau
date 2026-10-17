-- docs/150 golden session. Appended to the verify_load.py harness head (virtual clock, deterministic Random, mocked DataStore with
-- latency and repeated transforms) by tools/verify_profile_golden.py. It plays one long scripted session against the REAL
-- ProfileRepository and prints, after EVERY step, the stored profile as canonical JSON (sorted keys) plus the step's own return values and
-- the player's owner-only state, as `STEP <n> <label> len=<bytes> h=<hash>` (and the full text as `JSON <n> ...` when DUMP is true).
-- The same script runs on the code before and after the split of ProfileRepository; the lines must be identical.
local DUMP = __DUMP__

-------------------------------------------------------------------- canonical JSON + hash
local function canon(v, out)
    local t = type(v)
    if t == "nil" then out[#out + 1] = "null"
    elseif t == "boolean" then out[#out + 1] = if v then "true" else "false"
    elseif t == "number" then out[#out + 1] = if v == math.floor(v) and math.abs(v) < 2 ^ 53 then string.format("%d", v) else string.format("%.17g", v)
    elseif t == "string" then out[#out + 1] = string.format("%q", v)
    elseif t == "table" then
        local keys, isArray, n = {}, true, 0
        for k in v do
            n += 1
            keys[n] = k
            if type(k) ~= "number" or k < 1 or k % 1 ~= 0 then isArray = false end
        end
        if isArray and n > 0 and n ~= #v then isArray = false end
        if n == 0 then out[#out + 1] = "[]" return end
        if isArray then
            out[#out + 1] = "["
            for i = 1, n do
                if i > 1 then out[#out + 1] = "," end
                canon(v[i], out)
            end
            out[#out + 1] = "]"
        else
            table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
            out[#out + 1] = "{"
            for i, k in keys do
                if i > 1 then out[#out + 1] = "," end
                out[#out + 1] = string.format("%q:", tostring(k))
                canon(v[k], out)
            end
            out[#out + 1] = "}"
        end
    else out[#out + 1] = "<" .. t .. ">" end
end
local function canonical(v)
    local out = {}
    canon(v, out)
    return table.concat(out)
end
-- two 32-bit FNV-1a style passes (different bases and directions) -> a 64-bit fingerprint; multiplication is split to stay exact in doubles
local function mul(h, p) return ((h % 256) * 16777216 + h * (p - 16777216)) % 4294967296 end
local function fingerprint(s)
    local a, b = 2166136261, 3735928559
    for i = 1, #s do
        local c = string.byte(s, i)
        a = mul(bit32.bxor(a, c), 16777619)
        b = mul(bit32.bxor(b, string.byte(s, #s - i + 1)), 16777619)
    end
    return string.format("%08x%08x", a, b)
end

-------------------------------------------------------------------- scenario plumbing
local STEP = 0
local log = {}
local function step(label, profileValue, extra, player, server)
    STEP += 1
    local parts = {canonical(profileValue), canonical(extra)}
    if player then
        local attrs = {}
        for k, v in player.attrs do attrs[k] = v end
        parts[#parts + 1] = canonical(attrs)
        local PrivateState = server.require(node("src/server/PrivateState"))
        parts[#parts + 1] = canonical(PrivateState.snapshot(player))
    end
    local text = table.concat(parts, "\n")
    print(string.format("STEP %d %s len=%d h=%s", STEP, label, #text, fingerprint(text)))
    if DUMP then print("JSON " .. STEP .. " " .. string.gsub(text, "\n", " ## ")) end
end

local function newPlayer(id)
    local p = {UserId = id, Name = "Golden" .. id, Parent = true, attrs = {}}
    function p:SetAttribute(k, v) self.attrs[k] = v end
    function p:GetAttribute(k) return self.attrs[k] end
    function p:Kick(message) self.kicked = message end
    return p
end
local function join(server, p) table.insert(server.players, p) end

local function stored(server, p)
    return DATA["u:" .. p.UserId]
end

-- run `fn(...)`, record its return values with the stored profile after it
local function act(label, server, p, view, fn, ...)
    local results = table.pack(pcall(fn, ...))
    local extra = {}
    if results[1] then
        extra.count = results.n - 1
        for i = 2, results.n do extra["r" .. (i - 1)] = results[i] end -- a nil in the middle stays visible through `count`
    else
        extra.error = string.gsub(tostring(results[2]), "[%w/%._]+:%d+: ", "") -- line numbers move with the code, the message must not
    end
    step(label, view(), extra, p, server)
    if results[1] then return table.unpack(results, 2, results.n) end
    return nil
end

local function PrivateState_get(server, p, name)
    return server.require(node("src/server/PrivateState")).get(p, name)
end

local function scenarioPersistent()
    local overrides = {
        ObjectivesEnabled = true, GiftClaimEnabled = true, IdentityPersistentEnabled = true, IdentityFusionPreviewEnabled = true,
        PerDinoCosmeticsEnabled = true, CollectionTestGrantEnabled = true, ChestTestGrantEnabled = true,
        MutationTestSetupEnabled = true, PaidRandomItemsEnabled = true, FastTravelPerk = true, CaveHub = true,
        DinoSkinsEnabled = true, SecretSpeciesEnabled = true,
    }
    local server = newServer("golden", "job-golden", overrides)
    local R, Config, Rules = server.Repository, server.Config, server.Rules
    local PrivateState = server.require(node("src/server/PrivateState"))
    local p = newPlayer(9001)
    join(server, p)
    local function view() return stored(server, p) end
    local function A(label, fn, ...)
        local r = table.pack(act(label, server, p, view, fn, ...))
        sleep(4) -- the write budget refills between steps; the bursts below call `act` directly
        return table.unpack(r, 1, r.n)
    end

    A("load", R.load, p)
    PrivateState.set(p, "PaidRandomEligible", true)
    A("fusion status before any dino", R.fusionStatus, p)
    -- a first run: 500 food -> eggs, nests, crystals
    A("settle run r1", R.commitRunSettlement, p, "run-r1", 500, nil, 420)
    A("settle run r1 replay", R.commitRunSettlement, p, "run-r1", 500, nil, 420)
    local rainTag = Rules.eventEgg("rain", 0)
    A("settle run r2 (tags, nests)", R.commitRunSettlement, p, "run-r2", 5000, {rainTag, rainTag, {eventId = "clear", mutationId = ""}}, 900, {"rain", "clear", "rain"})
    A("settle bad run id", R.commitRunSettlement, p, "", 10)
    A("settle bad events", R.commitRunSettlement, p, "run-bad", 10, {{eventId = 5}})
    A("pending reveals", R.pendingReveals, p)
    -- hatch: reveal whatever the client would reveal next
    for i = 1, 14 do
        local id = PrivateState.get(p, "NextChestId")
        if id == nil or id == "" then break end
        A("claim egg " .. i, R.claimChest, p, id)
        sleep(1)
    end
    A("claim missing egg", R.claimChest, p, "no-such-egg")
    A("claim invalid id", R.claimChest, p, "")
    local queue = PrivateState.get(p, "ChestQueueJson")
    A("pending reveals after page", R.pendingReveals, p)
    -- preferences, with a burst that has to coalesce
    A("reveal skip", R.setRevealSkip, p, {1, 2})
    A("reveal skip bad", R.setRevealSkip, p, {1, 1})
    for i = 1, 8 do act("settings burst " .. i, server, p, view, R.setSettings, p, {musicVolume = i / 10}) end
    A("settings bad", R.setSettings, p, "x")
    sleep(5)
    step("after coalesce flush", view(), {R.budgetStats()}, p, server)
    -- nests incubate one at a time (server time): claim each as it becomes ready
    for round = 1, 3 do
        sleep(Config.NestIncubationSeconds + 60)
        local nests = PrivateState.get(p, "NestsJson")
        step("nests round " .. round, view(), {nests}, p, server)
        if type(nests) == "table" and nests[1] then
            A("claim not-ready nest " .. round, R.claimNest, p, nests[#nests].id)
            A("claim nest " .. round, R.claimNest, p, nests[1].id)
            A("claim nest replay " .. round, R.claimNest, p, nests[1].id)
        end
    end
    A("claim nest missing", R.claimNest, p, "nest-none")
    -- hatch more (nest eggs go to the front of the bank)
    for i = 1, 90 do
        local id = PrivateState.get(p, "NextChestId")
        if id == nil or id == "" then break end
        if i <= 4 or i % 10 == 0 then
            A("claim more " .. i, R.claimChest, p, id)
        else
            pcall(R.claimChest, p, id) -- the in-between claims are covered by the next snapshot
            sleep(1)
        end
    end
    -- equip
    A("equip compy", R.equipSpecies, p, "compy")
    A("equip compy again", R.equipSpecies, p, "compy")
    A("equip unknown", R.equipSpecies, p, "not_a_species")
    local profile = stored(server, p)
    for speciesId, entry in profile.collection do
        if speciesId ~= "compy" and type(entry.variants) == "table" and next(entry.variants) ~= nil then
            local key = next(entry.variants)
            A("equip variant " .. speciesId, R.equipSpecies, p, speciesId, key)
            break
        end
    end
    A("equip locked", R.equipSpecies, p, "spinosaurus")
    -- test grants
    A("collection test grant", R.grantCollectionTestSpecies, p)
    A("collection test grant replay", R.grantCollectionTestSpecies, p)
    A("chest test grant", R.grantChestTest, p)
    -- crystals, shop, potions, cosmetics
    for i = 1, 4 do A("grant crystals " .. i, R.progressionAction, p, "grant", "crystal", "grant-" .. i, nil, 100) end
    A("grant replay", R.progressionAction, p, "grant", "crystal", "grant-1", nil, 100)
    local window = Rules.shopWindow(vos.time())
    local offers = Rules.shopOffers(window)
    A("buy potion", R.progressionAction, p, "buyPotion", offers[1].id .. "@" .. window, "potion-1")
    A("buy potion again", R.progressionAction, p, "buyPotion", offers[1].id .. "@" .. window, "potion-2")
    A("buy potion stale", R.progressionAction, p, "buyPotion", offers[1].id .. "@" .. (window - 1), "potion-3")
    A("use potion", R.progressionAction, p, "usePotion", offers[1].id, "use-1", false)
    A("use potion twice", R.progressionAction, p, "usePotion", offers[1].id, "use-2", false)
    A("buy aura", R.progressionAction, p, "buyAura", "meadow", "aura-1")
    A("equip aura", R.progressionAction, p, "equipAura", "meadow", "aura-2")
    A("buy trail locked", R.progressionAction, p, "buyTrail", "tidal", "trail-1")
    A("buy perk", R.progressionAction, p, "buyPerk", "fast_travel", "perk-1")
    A("buy egg", R.progressionAction, p, "buyEgg", "random", "egg-1")
    A("upgrade condition", R.progressionAction, p, "upgradeCondition", "1", "up-1")
    A("progression read", R.progression, p)
    -- objectives
    A("objective record food", R.objectiveRecord, p, {kind = "food_eaten", amount = 10})
    A("objective record hatch", R.objectiveRecord, p, {kind = "egg_hatched", amount = 3})
    A("objective record bad", R.objectiveRecord, p, {kind = "nonsense", amount = 1})
    A("objective view", R.objectiveView, p)
    A("objective flush", R.objectiveFlush, p)
    A("objective seen", R.objectiveSeen, p, "fusion_menu")
    A("objective seen again", R.objectiveSeen, p, "fusion_menu")
    A("objective flush 2", R.objectiveFlush, p)
    A("objective claim T1", R.objectiveClaim, p, "T1", "claim-1")
    A("objective claim T1 replay", R.objectiveClaim, p, "T1", "claim-1")
    A("objective claim T1 again", R.objectiveClaim, p, "T1", "claim-2")
    A("objective claim unknown", R.objectiveClaim, p, "ZZ", "claim-3")
    A("objective claim unmet", R.objectiveClaim, p, "T2", "claim-4")
    -- gifts
    A("gifts apply", R.applyGifts, p, {apply = {{id = "g1", kind = "skin", skin = "Plush", thankYou = 7}, {id = "g2", kind = "crystals", amount = 25},
        {id = "g3", kind = "skin", skin = "Plush", thankYou = 7}, {id = "g4", kind = "skin", skin = "Clay", thankYou = 7}}, revoke = {}, claimedCap = 100})
    A("gifts replay", R.applyGifts, p, {apply = {{id = "g1", kind = "skin", skin = "Plush", thankYou = 7}}, revoke = {}, claimedCap = 100})
    A("gifts revoke", R.applyGifts, p, {apply = {}, revoke = {{id = "g1", skin = "Plush"}, {id = "g9", skin = "Clay"}}, claimedCap = 100})
    A("gifts bad plan", R.applyGifts, p, {})
    -- mutation (needs 50 base copies of the test species)
    A("mutation setup 49", R.setMutationTestCopies, p, "compy", 49)
    A("mutate short", R.mutateSpecies, p, "compy", "gold", "mut-0")
    A("mutation setup 50", R.setMutationTestCopies, p, "compy", 50)
    A("mutate gold", R.mutateSpecies, p, "compy", "gold", "mut-1")
    A("mutate gold replay", R.mutateSpecies, p, "compy", "gold", "mut-1")
    A("mutate conflict", R.mutateSpecies, p, "compy", "diamond", "mut-1")
    A("mutate unknown", R.mutateSpecies, p, "compy", "silver", "mut-2")
    -- fusion over the identities the grouped collection projects
    A("mutation setup 51", R.setMutationTestCopies, p, "compy", 51)
    A("fusion status", R.fusionStatus, p)
    local listing = A("list dinosaurs", R.listDinosaurs, p, 0, 200)
    local bySpecies, ids = {}, {}
    if type(listing) == "table" then
        for _, d in listing.dinosaurs do
            if d.stage == "base" and d.originKind == "hatch" then
                bySpecies[d.speciesId] = bySpecies[d.speciesId] or {}
                table.insert(bySpecies[d.speciesId], d.instanceId)
            end
        end
        local species = {}
        for speciesId in bySpecies do table.insert(species, speciesId) end
        table.sort(species)
        for _, speciesId in species do
            if #bySpecies[speciesId] >= 6 then
                for i = 1, 6 do ids[i] = bySpecies[speciesId][i] end
                break
            end
        end
    end
    step("fusion donors", view(), {ids}, p, server)
    if ids[1] then
        A("dinosaur details", R.dinosaurDetails, p, ids[1])
        A("fusion details", R.fusionDetails, p, ids[1])
        local quote = A("quote fusion", R.quoteFusion, p, "gold", ids)
        A("quote fusion bad", R.quoteFusion, p, "gold", {ids[1]})
        if type(quote) == "table" then
            A("fuse bad digest", R.fuseDinosaurs, p, {token = "fuse-0", targetStage = "gold", donorIds = ids, quoteDigest = "nope"})
            A("fuse", R.fuseDinosaurs, p, {token = "fuse-1", targetStage = "gold", donorIds = ids, quoteDigest = quote.quoteDigest, consentDigest = quote.consentDigest})
            A("fuse replay", R.fuseDinosaurs, p, {token = "fuse-1", targetStage = "gold", donorIds = ids, quoteDigest = quote.quoteDigest, consentDigest = quote.consentDigest})
        end
    end
    local after = A("list dinosaurs after", R.listDinosaurs, p, 0, 10)
    -- dino skins (a look only): free Base, an owned skin with and without a model, the default, bad plans
    local first = if type(after) == "table" and after.dinosaurs[1] then after.dinosaurs[1] else nil
    if first then
        A("skin view", R.skinView, p)
        A("skin view instance", R.skinView, p, first.instanceId)
        A("skin view missing", R.skinView, p, "u:9001/d:none")
        A("skin equip base", R.applySkin, p, {kind = "equip", instanceId = first.instanceId, skin = "Base", free = true})
        A("skin equip clay no model", R.applySkin, p, {kind = "equip", instanceId = first.instanceId, skin = "Clay", free = false, modelSpecies = {}})
        A("skin equip clay", R.applySkin, p, {kind = "equip", instanceId = first.instanceId, skin = "Clay", free = false, modelSpecies = {[first.speciesId] = true}})
        A("skin equip not owned", R.applySkin, p, {kind = "equip", instanceId = first.instanceId, skin = "Balloon", free = false, modelSpecies = {[first.speciesId] = true}})
        A("skin set default", R.applySkin, p, {kind = "setDefault", skin = "Clay", free = false})
        A("skin view default", R.skinView, p, first.instanceId)
        A("skin unequip", R.applySkin, p, {kind = "unequip", instanceId = first.instanceId})
        A("skin clear default", R.applySkin, p, {kind = "clearDefault"})
        A("skin bad plan", R.applySkin, p, {kind = "nonsense"})
    end
    -- a Robux receipt, then the paid-random gate for fusion/eggs
    local product = next(Config.DeveloperProducts)
    A("purchase", R.purchase, p, {ProductId = product, PlayerId = p.UserId, PurchaseId = "receipt-1", CurrencySpent = 49})
    A("purchase replay", R.purchase, p, {ProductId = product, PlayerId = p.UserId, PurchaseId = "receipt-1", CurrencySpent = 49})
    A("purchase bad", R.purchase, p, {ProductId = product, PlayerId = 1, PurchaseId = "receipt-2", CurrencySpent = 49})
    PrivateState.set(p, "PaidRandomEligible", false)
    A("buy egg gated", R.progressionAction, p, "buyEgg", "random", "egg-2")
    A("fusion gated", R.fusionStatus, p)
    -- lease renew, a settlement that has to be retried after an outage, then the lease release
    A("renew", R.renew, p)
    A("settle run r3", R.commitRunSettlement, p, "run-r3", 300, nil, 300)
    A("renew 2", R.renew, p)
    A("release", R.release, p)
    step("after release", stored(server, p), {}, nil, server)
    -- a second session of the same player: the stored profile must load, migrate and play on
    local p2 = newPlayer(9001)
    join(server, p2)
    local function view2() return stored(server, p2) end
    act("reload", server, p2, view2, R.load, p2)
    act("reload progression", server, p2, view2, R.progression, p2)
    act("reload claim", server, p2, view2, R.claimChest, p2, PrivateState.get(p2, "NextChestId") or "none")
    act("reload release", server, p2, view2, R.release, p2)
end

local function scenarioPreview()
    STUDIO = true
    local server = newServer("preview", "job-preview", {DemoDirectorEnabled = true, IdentityFusionPreviewEnabled = true})
    STUDIO = false
    local R, Config, Rules = server.Repository, server.Config, server.Rules
    local PrivateState = server.require(node("src/server/PrivateState"))
    local p = newPlayer(9002)
    join(server, p)
    local function view() return LASTPROFILE end
    local function A(label, fn, ...) return act(label, server, p, view, fn, ...) end
    A("preview load", R.load, p)
    A("preview fusion status", R.fusionStatus, p)
    A("preview settle", R.commitRunSettlement, p, "prev-1", 100, nil, 200)
    local eggs = {}
    for i = 1, 3 do
        local egg = R.prepareEgg(p, {eventId = "clear", mutationId = ""})
        egg.eggId = "demo-egg-" .. i
        egg.kind = "run_egg"
        egg.reward = {speciesId = if i == 1 then "compy" else "triceratops", count = 1}
        egg.source = {kind = "run", runId = "demo", ordinal = i, originalEggId = egg.eggId}
        table.insert(eggs, egg)
    end
    A("demo grant eggs", R.demoGrantEggs, p, eggs, false)
    A("demo grant eggs new find", R.demoGrantEggs, p, {eggs[1]}, true)
    A("demo grant bad", R.demoGrantEggs, p, {}, false)
    A("demo equip", R.demoEquip, p, "triceratops")
    A("demo crystals", R.demoAddCrystals, p, 500)
    A("demo crystals bad", R.demoAddCrystals, p, 0)
    for i = 1, 6 do
        local id = PrivateState.get(p, "NextChestId")
        if id == nil or id == "" then break end
        A("preview claim " .. i, R.claimChest, p, id)
    end
    A("preview grant crystals", R.progressionAction, p, "grant", "crystal", "pg-1", nil, 50)
    A("preview release", R.release, p)
end

local function scenarioOutage()
    local server = newServer("outage", "job-outage", {})
    local R = server.Repository
    local p = newPlayer(9003)
    join(server, p)
    local function view() return stored(server, p) end
    local function A(label, fn, ...)
        local r = table.pack(act(label, server, p, view, fn, ...))
        sleep(4)
        return table.unpack(r, 1, r.n)
    end
    A("outage load", R.load, p)
    A("outage settle ok", R.commitRunSettlement, p, "out-1", 40, nil, 100)
    SCENARIO_FAIL_RATE = 1 -- every store request fails
    A("outage settings", R.setSettings, p, {musicVolume = 0.5})
    A("outage settle", R.commitRunSettlement, p, "out-2", 60, nil, 100, nil, 2)
    step("outage pending", view(), {R.pendingSettlement(p), R.budgetStats()}, p, server)
    A("outage renew", R.renew, p)
    SCENARIO_FAIL_RATE = 0
    A("outage renew recovers", R.renew, p)
    step("outage recovered", view(), {R.pendingSettlement(p), R.budgetStats(), R.isLoaded(p), R.runStartBlockReason(view())}, p, server)
    A("outage claim", R.claimChest, p, PrivateState_get(server, p, "NextChestId") or "none")
    -- another server takes the lease over: every write is refused, the player is sent back to rejoin
    DATA["u:9003"].session = {leaseId = "another-server", jobId = "other", expiresAt = vos.time() + 100000, metricsAt = vos.time()}
    A("lease lost settle", R.commitRunSettlement, p, "out-3", 50, nil, 100)
    A("lease lost equip", R.equipSpecies, p, "triceratops")
    A("lease lost renew", R.renew, p)
    sleep(10)
    step("lease lost kicked", view(), {p.kicked, R.leaseLostStats()}, p, server)
    A("lease lost release", R.release, p)
end

task.spawn(function()
    math.randomseed(20261017) -- settlement retry jitter uses math.random
    M = newMetrics()
    local ok, err = pcall(scenarioPersistent)
    if not ok then print("SCENARIO_ERROR persistent " .. tostring(err)) end
    ok, err = pcall(scenarioPreview)
    if not ok then print("SCENARIO_ERROR preview " .. tostring(err)) end
    ok, err = pcall(scenarioOutage)
    if not ok then print("SCENARIO_ERROR outage " .. tostring(err)) end
    print("DONE steps=" .. STEP)
end)
runQueue(math.huge)
for _, crash in crashes do print("CRASH " .. crash) end
