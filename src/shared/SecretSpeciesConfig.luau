--!strict
-- BD-604 / BD-228 (docs/115 SS1 to SS6, docs/149): secret silly creatures, the DATA and the RULES. Pure (no Roblox APIs), so
-- tools/verify_secret_species.py runs the real module. Everything here is behind Config.SecretSpeciesEnabled (false, pinned OFF in the
-- default and playtest profiles by tools/release_profiles.py): the server hook in RewardMath and ProfileRepository and the client Index
-- read it, this module never does. Every number is PROVISIONAL.
--
-- SS1: SECRET species, NOT a sixth rarity tier: each row below is `secret = true` plus a provisional drop weight. They are not in
-- Config.SpeciesOrder / SpeciesRarities / ChestSpeciesWeights (the normal 22-species Index, odds copy and completion number stay as they
-- are) and never raise metrics.rarest.
-- SS2: a flat chance per egg, only for eggs earned in a RUN or opened from a free NEST; never a shop egg, never a paid or Robux-linked egg.
-- SS3/SS4: shown as "Secret" in the Index and on the hatch ribbon; hidden "???" card until first found; counted separately.
-- SS5: classes. SS6: with the flag off nothing here is ever called.
local Secret = {}

-- Version written into the egg metadata of every egg that went through the roll (versioned like Config traitRollVersion).
Secret.Version = "bd228-secret-v1"

-- PROVISIONAL (SS2): probability that one eligible egg carries a secret species. FLAT: no luck tier, run size, BIG, potion or weather
-- changes it (the roll takes only an origin and a random source).
Secret.Chance = 0.005

Secret.RarityLabel = "Secret" -- shown instead of a tier name (SS3)
-- Colour/sound treatment only (SS3: "the same calm treatment as Legendary", no extra loud effects). NOT a tier: it is never stored in
-- metrics.rarest or used by the size ladder.
Secret.DisplayTier = 5

-- Only these egg origins can roll a secret (SS2). "run" = earned in a run, "nest" = a free bonus nest. Anything else (the crystal shop,
-- gifts, legacy chests, paid or unknown origins) never does.
Secret.EligibleOrigins = table.freeze({ run = true, nest = true })

-- The roster, in Index order (SS1). class = SS5 (and CombatConfig.SpeciesClasses must agree, checked by verify_secret_species).
-- weight = PROVISIONAL relative share among the secrets that can drop. assetId = the MODEL SLOT: 0 / empty = no generated model yet
-- (a plain fallback look); a secret species can NOT hatch while its slot is empty (modelReady), so a flag flip alone never shows a
-- broken dino. Filling a slot is a separate model task (docs/77 lines secret_dino_*), and must come with the LowPolyDinoAssets and
-- ScaleLadder entries (verify_secret_species checks the two agree).
Secret.Order = table.freeze({ "chickosaurus", "pigeon", "dodo", "duck", "penguin", "budgiesaurus", "foxosaurus", "cockatoosaurus", "eaglesaurus" })
Secret.Species = {
    chickosaurus = { id = "chickosaurus", name = "Chickosaurus", secret = true, class = "Ground", weight = 20, assetId = 108391746824463 },
    pigeon = { id = "pigeon", name = "Pigeon", secret = true, class = "Ground", weight = 20, assetId = 83982208995212 },
    dodo = { id = "dodo", name = "Dodo", secret = true, class = "Ground", weight = 14, assetId = 128146035116312 },
    duck = { id = "duck", name = "Duck", secret = true, class = "Ground", weight = 18, assetId = 129901658996389 },
    penguin = { id = "penguin", name = "Penguin", secret = true, class = "Water", weight = 12, assetId = 120950430829492 },
    budgiesaurus = { id = "budgiesaurus", name = "Budgiesaurus", secret = true, class = "Fly", weight = 10, assetId = 107910518074360 },
    foxosaurus = { id = "foxosaurus", name = "Foxosaurus", secret = true, class = "Ground", weight = 6, assetId = 112996440434481 },
    -- BD-621 / BD-622 (docs/115 SS14): the two special birds, both Fly like the Budgiesaurus; PROVISIONAL weights, rarer than the fox.
    cockatoosaurus = { id = "cockatoosaurus", name = "Cockatoosaurus", secret = true, class = "Fly", weight = 5, assetId = 77920946493998 },
    eaglesaurus = { id = "eaglesaurus", name = "Eaglesaurus", secret = true, class = "Fly", weight = 3, assetId = 116840996663024 },
}

function Secret.isSecret(speciesId: any): boolean
    return typeof(speciesId) == "string" and Secret.Species[speciesId] ~= nil
end

function Secret.name(speciesId: any): string
    local row = if typeof(speciesId) == "string" then Secret.Species[speciesId] else nil
    return if row then row.name else tostring(speciesId)
end

function Secret.classOf(speciesId: any): string?
    local row = if typeof(speciesId) == "string" then Secret.Species[speciesId] else nil
    return if row then row.class else nil
end

-- DisplayTier for a secret id, nil for any other id (so `Config.SpeciesRarities[id] or Secret.displayTier(id) or 1` is safe).
function Secret.displayTier(speciesId: any): number?
    return if Secret.isSecret(speciesId) then Secret.DisplayTier else nil
end

-- True only when the model slot holds a real positive whole asset id.
function Secret.modelReady(speciesId: any): boolean
    local row = if typeof(speciesId) == "string" then Secret.Species[speciesId] else nil
    if row == nil then return false end
    local id = row.assetId
    return typeof(id) == "number" and id == id and id > 0 and id % 1 == 0 and id < 2 ^ 53
end

-- Secret ids that may drop right now (model slot filled), in roster order.
function Secret.readyIds(): { string }
    local ids = {}
    for _, id in Secret.Order do
        if Secret.modelReady(id) then table.insert(ids, id) end
    end
    return ids
end

function Secret.eligibleOrigin(origin: any): boolean
    return typeof(origin) == "string" and Secret.EligibleOrigins[origin] == true
end

-- The roll (SS2). `rng` is a Random-like object (NextNumber). Returns a secret species id or nil.
-- No eligible origin or no secret with a filled model slot: returns nil WITHOUT touching the random source.
-- Otherwise exactly one draw decides the hit (flat Secret.Chance) and a hit takes one more draw to pick the species by weight among the
-- ready secrets only.
function Secret.roll(rng: any, origin: any): string?
    if not Secret.eligibleOrigin(origin) then return nil end
    local ready = Secret.readyIds()
    if #ready == 0 then return nil end
    if rng:NextNumber() >= Secret.Chance then return nil end
    local total = 0
    for _, id in ready do total += Secret.Species[id].weight end
    local pick = rng:NextNumber() * total
    local cumulative = 0
    for _, id in ready do
        cumulative += Secret.Species[id].weight
        if pick < cumulative then return id end
    end
    return ready[#ready]
end

-- Writes the roll into an egg reward table (the egg metadata). The normally rolled species stays in reward.speciesId (so every older
-- reader keeps a valid egg); the secret is the additive reward.secretSpeciesId. reward.secretRollVersion marks that the egg went through
-- the roll. Does nothing (reward untouched) when the origin is not eligible or no model is ready.
function Secret.attach(reward: any, rng: any, origin: any): any
    if not Secret.eligibleOrigin(origin) or #Secret.readyIds() == 0 then return reward end
    local hit = Secret.roll(rng, origin)
    reward.secretRollVersion = Secret.Version
    if hit then reward.secretSpeciesId = hit end
    return reward
end

-- The species the hatch should credit for this egg reward: the secret id when the egg carries a valid one AND its model slot is still
-- filled, otherwise nil (hatch the normally rolled species). Flag-independent on purpose; callers check Config.SecretSpeciesEnabled.
function Secret.resolve(reward: any): string?
    if typeof(reward) ~= "table" then return nil end
    local id = reward.secretSpeciesId
    if reward.secretRollVersion ~= Secret.Version or not Secret.isSecret(id) or not Secret.modelReady(id) then return nil end
    return id :: string
end

-------------------------------------------------------------------- Equip (BD-606, docs/115 SS7)
-- A found secret can be EQUIPPED and played, but it is never written into `equippedSpeciesId`: Build 020 refuses a profile whose equipped
-- species it does not know (SchemaError, RB1), so the stored pair stays a species Build 020 knows (the fallback below, with no variant key)
-- and the secret lives in the ADDITIVE record `profile.equippedSecret = {speciesId, variantKey?}`. Build 020 ignores the record (and plays
-- the fallback dino); the current build honours it only while the flag is on, the model slot is filled, the profile still owns the secret and
-- the stored species is still the fallback (a re-equip made by an older build wins).
Secret.EquipFallback = "compy"

-- May a request equip this species id right now? (the flag is the caller's: it passes Config.SecretSpeciesEnabled)
function Secret.canEquip(speciesId: any, enabled: any): boolean
    return enabled == true and Secret.isSecret(speciesId) and Secret.modelReady(speciesId)
end

-- The record stored beside the fallback pair.
function Secret.equipRecord(speciesId: string, variantKey: string?): { speciesId: string, variantKey: string? }
    return { speciesId = speciesId, variantKey = variantKey }
end

-- The equip a stored profile asks for: (secret id, variant key or nil), or nil when there is none or it cannot be honoured (not a secret,
-- model slot empty, junk variant key, or the stored species is no longer the fallback). Ownership is the caller's check.
function Secret.readEquip(record: any, storedSpeciesId: any): (string?, string?)
    if typeof(record) ~= "table" or storedSpeciesId ~= Secret.EquipFallback then return nil, nil end
    local id, key = record.speciesId, record.variantKey
    if not Secret.isSecret(id) or not Secret.modelReady(id) then return nil, nil end
    if key ~= nil and (typeof(key) ~= "string" or #key < 1 or #key > 160) then return nil, nil end
    return id :: string, key :: string?
end

-- A fresh collection entry for a secret species, created lazily on its first hatch (never in a new profile).
function Secret.newEntry(): { base: number, gold: number, diamond: number, events: { [string]: number }, variants: { [string]: any } }
    return { base = 0, gold = 0, diamond = 0, events = {}, variants = {} }
end

-------------------------------------------------------------------- Index (SS3, SS4)
local function ownsAny(entry: any): boolean
    if typeof(entry) ~= "table" then return false end
    for _, key in { "base", "gold", "diamond" } do
        if typeof(entry[key]) == "number" and entry[key] > 0 then return true end
    end
    return (typeof(entry.variants) == "table" and next(entry.variants) ~= nil)
        or (typeof(entry.events) == "table" and next(entry.events) ~= nil)
end

-- The Index order: with the flag off it is `baseOrder` itself (the same table, nothing appended). With it on, the secret cards follow the
-- normal species.
function Secret.indexOrder(baseOrder: { string }, enabled: any): { string }
    if enabled ~= true then return baseOrder end
    local order = table.clone(baseOrder)
    for _, id in Secret.Order do table.insert(order, id) end
    return order
end

-- Decoded CollectionJson ({speciesId = entry}) -> how many secrets are found (a hidden card turns into a normal card).
function Secret.countFound(collection: any): number
    if typeof(collection) ~= "table" then return 0 end
    local found = 0
    for _, id in Secret.Order do
        if ownsAny(collection[id]) then found += 1 end
    end
    return found
end

-- "2 / 7 secrets found" (SS4); kept apart from the 22-species completion number.
function Secret.summary(found: number)
    local total = #Secret.Order
    found = math.clamp(math.floor(found), 0, total)
    return { found = found, total = total, text = string.format("%d / %d secrets found", found, total) }
end

-- The card for one secret id: hidden until first found (the "???" silhouette card), then a normal card whose rarity line reads "Secret".
-- A hidden card never shows the name, the class or a model; `silhouette` is only true when a model is ready to draw (an empty slot gets a
-- plain "?" mark, never a broken dino).
function Secret.indexCard(speciesId: string, found: boolean)
    if found then
        return { found = true, silhouette = false, locked = false, nameText = Secret.name(speciesId), rarityText = Secret.RarityLabel, status = nil, showButton = true }
    end
    return { found = false, silhouette = Secret.modelReady(speciesId), locked = true, nameText = "???", rarityText = Secret.RarityLabel, status = "Secret dino", showButton = false }
end

return Secret
