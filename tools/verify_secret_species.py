"""BD-604 / BD-228 (docs/149, docs/115 SS1 to SS6): secret silly creatures, verified by running the REAL modules in pinned Luau.

Part A (pure rules): SecretSpeciesConfig + the real RewardMath, Config, ProgressionConfig, CombatConfig, LowPolyDinoAssets.
  * flag-off identity: RewardMath.computeChestReward is byte-identical to the pre-BD-604 code (a golden hash taken from the unmodified
    module over 16,000 rolls), with and without an origin argument, and also with the flag ON while no model slot is filled;
  * the roll NEVER fires for a shop egg, a paid / Robux-linked egg, a gift, a legacy chest or any unknown origin, and never touches the
    random source for them;
  * the chance is flat 0.5% within statistical tolerance over 200,000 run rolls and 200,000 nest rolls, and does not rise with run size
    (1 egg vs 400 eggs) or nest luck;
  * the species split follows the provisional weights, and only secrets with a filled model slot can drop;
  * secrets are counted apart ("2 / 9 secrets found"), the hidden card never leaks the name, the 22-species number is untouched;
  * no secret hatches while its model slot is empty; the shipped slots are EXACTLY the pinned BOUND_IDS (docs/173: only real, plain,
    positive asset ids, each with its LowPolyDinoAssets entry and a measured ladder row) and agree with the class table; every unit test
    runs on an all-empty copy of the module so the rules are proved without the shipped ids.
Part B (repository): the real ProfileRepository on the mocked DataStore of verify_rewards:
  * flag off: no egg, outcome, collection or profile key mentions a secret; flag on with empty slots: byte-identical egg digests;
  * flag on with filled slots: the roll is recorded in the egg metadata (secretRollVersion), a secret hatches into a lazily created
    collection entry, never raises metrics.rarest, reveals last in a batch, comes from nests too, never from the crystal shop;
  * the secret hatches only while the flag is on AND the slot is filled; fusion treats the new species like any other (6 -> Gold);
  * RB1: the frozen Build 020 reader (tools/fixtures/build020) loads and keeps a profile that holds secret eggs and a secret entry.
Static: release profiles pin the flag OFF in default and playtest, call sites, lazy requires, Index wiring, docs lines.

Run: python tools/verify_secret_species.py --runner C:/path/to/luau.exe
"""
from pathlib import Path
import argparse
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_odds_copy  # noqa: E402  (the real odds modules for part C)
import verify_rewards  # noqa: E402  (reuses the mocked-DataStore prefix)
import verify_rollback  # noqa: E402  (the frozen Build 020 reader)
import release_profiles  # noqa: E402
import rehearsal_env  # noqa: E402
import profile_sources  # noqa: E402

# Hash of RewardMath.computeChestReward over seeds 1..400 x run sizes {1, 40, 120, 400} x 10 rolls, taken from the UNMODIFIED module
# (origin/main 18a9d665) with the same harness. If this changes, the flag-off egg rolls are no longer identical to Build 020 as shipped.
# BD-1032 (2026-10-18) re-took it: the species weights, the run boost and RunRewardConfigVersion changed on purpose (docs/186 s3), so the golden
# draws changed. The new value was checked against an independent flag-off reimplementation (weights -> one weighted pick -> quantity pick,
# no secret code path) and both gave 3792976408. Old value: 2926628964.
GOLDEN_FLAG_OFF_HASH = 3792976408


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path):
    return profile_sources.module(path)  # docs/150: ProfileRepository plus the parts it installs


# BD-606 / docs/173: the REAL model asset ids bound in src/shared/SecretSpeciesConfig.luau. Pinned here on purpose: binding another slot (or
# changing an id) fails this verifier until this table, docs/173 and the evidence line change in the same commit. Every id is a published
# `generate_mesh` Model of the owner's account (Roblox economy details: AssetTypeId 10, creator znyprs, the same as the 22 shipped species).
# Never invent an id: a slot that is not here stays 0.
BOUND_IDS = {'budgiesaurus': 107910518074360, 'chickosaurus': 108391746824463, 'cockatoosaurus': 77920946493998, 'dodo': 128146035116312, 'duck': 129901658996389, 'eaglesaurus': 116840996663024, 'foxosaurus': 112996440434481, 'penguin': 120950430829492, 'pigeon': 83982208995212}
SLOT_RE = re.compile(r'(\{ id = "(\w+)", name = "[^"]+", secret = true, class = "\w+", weight = \d+, assetId = )(\d+)( \})')


def shipped_slots():
    """{secret id: assetId} exactly as written in the shipped SecretSpeciesConfig."""
    return {m.group(2): int(m.group(3)) for m in SLOT_RE.finditer(read('src/shared/SecretSpeciesConfig.luau'))}


def empty_secret_module():
    """The real SecretSpeciesConfig with EVERY model slot set to 0: the neutral universe the unit tests run in (the shipped ids are tested apart)."""
    return profile_sources.neutral_secret_module()


# ---------------------------------------------------------------------------------------------------------------- part A
PURE = r'''
local Config = @@CONFIG@@
local ProgressionConfig = @@PROGRESSION_CONFIG@@
local CombatConfig = @@COMBAT_CONFIG@@
local LowPoly = @@LOWPOLY@@
local GOLDEN = @@GOLDEN@@

local function mkSecret() return @@SECRET@@ end -- an all-empty copy (neutral universe)
local function mkShipped() return @@SECRET_SHIPPED@@ end -- the module exactly as shipped
local BOUND = {@@BOUND@@}
local function mkRM(cfg, secret)
  local MODS = {Config = cfg, ProgressionConfig = ProgressionConfig, Secret = secret}
  local SERVICES = {ReplicatedStorage = {Shared = {Config = "Config", ProgressionConfig = "ProgressionConfig", SecretSpeciesConfig = "Secret"}}}
  local game = {GetService = function(_, n) return SERVICES[n] end}
  local script = {Parent = {}}
  local require = function(id) return MODS[id] end
  return @@REWARD_MATH@@
end

local checks = 0
local function check(cond, msg) checks += 1 if not cond then error("FAILED: " .. msg, 2) end end

-- Park-Miller (the same generator as the other harnesses); `calls` counts draws so "never touched" is provable.
local function Rng(seed)
  local state = seed % 2147483646 + 1
  local self = {calls = 0}
  function self:NextNumber(lo, hi)
    self.calls += 1
    state = (state * 48271) % 2147483647
    local v = (state - 1) / 2147483646
    if lo then return lo + v * (hi - lo) end
    return v
  end
  return self
end

local function readyAll(S)
  local i = 0
  for _, id in S.Order do i += 1 S.Species[id].assetId = 7770000 + i end
  return S
end
local function keyCount(t) local n = 0 for _ in t do n += 1 end return n end

local function goldenHash(RM, origin)
  local hash = 5381
  local function mix(s) for i = 1, #s do hash = (hash * 33 + string.byte(s, i)) % 4294967296 end end
  for seed = 1, 400 do
    local rng = Rng(seed * 7919)
    for _, n in {1, 40, 120, 400} do
      for _ = 1, 10 do
        local r = RM.computeChestReward(rng, n, origin)
        check(keyCount(r) == 4, "a flag-off reward has exactly the four original fields")
        mix(r.speciesId .. ":" .. r.mutationId .. ":" .. tostring(r.count) .. ":" .. tostring(r.rewardConfigVersion) .. ";")
      end
    end
  end
  return hash
end

---------------------------------------------------------------- SS1 data and rules
local S0 = mkSecret()
check(Config.SecretSpeciesEnabled == false, "the committed flag is OFF")
check(#S0.Order == 9, "nine secrets")
local want = {"chickosaurus", "pigeon", "dodo", "duck", "penguin", "budgiesaurus", "foxosaurus", "cockatoosaurus", "eaglesaurus"}
for i, id in want do check(S0.Order[i] == id, "roster order " .. id) end
local weightSum = 0
for _, id in S0.Order do
  local row = S0.Species[id]
  check(row ~= nil and row.id == id and row.secret == true, id .. " is a secret species row")
  check(typeof(row.name) == "string" and #row.name >= 3 and #row.name <= 14, id .. " has a short kid-friendly name")
  check(typeof(row.weight) == "number" and row.weight > 0, id .. " has a drop weight")
  weightSum += row.weight
  check(row.assetId == 0 and S0.modelReady(id) == false, id .. " model slot is EMPTY in the neutral copy")
  check(CombatConfig.Classes[row.class] ~= nil and CombatConfig.SpeciesClasses[id] == row.class, id .. " class agrees with CombatConfig.SpeciesClasses")
  check(not table.find(Config.SpeciesOrder, id) and Config.SpeciesRarities[id] == nil and Config.SpeciesDisplayNames[id] == nil
    and Config.LegacySpeciesRarities[id] == nil, id .. " is not in the normal 22-species tables")
  for _, w in Config.ChestSpeciesWeights do check(w.speciesId ~= id, id .. " is not in the shop/odds table") end
  check(table.find(CombatConfig.SecretSpecies, id) ~= nil, id .. " is in CombatConfig.SecretSpecies")
  check(S0.isSecret(id) and not S0.isSecret(nil) and not S0.isSecret("compy") and not S0.isSecret(5), "isSecret")
  check(S0.displayTier(id) == 5 and S0.displayTier("compy") == nil, "calm Legendary look only")
end
-- the SHIPPED slots: exactly the pinned real ids, plain positive whole numbers, nothing else (docs/173)
do
  local SH = mkShipped()
  for _, id in SH.Order do
    local row = SH.Species[id]
    if BOUND[id] ~= nil then
      check(row.assetId == BOUND[id] and typeof(row.assetId) == "number" and row.assetId > 0 and row.assetId % 1 == 0 and SH.modelReady(id), id .. " is bound to its pinned real id")
      local entry = LowPoly[id]
      check(entry ~= nil and entry.assetId == row.assetId and entry.class == row.class and entry.tier == 1, id .. " has its LowPolyDinoAssets entry (same id and class, size tier 1)")
    else
      check(row.assetId == 0 and not SH.modelReady(id), id .. " model slot is EMPTY in the shipped config (no pinned real id)")
      check(LowPoly[id] == nil, id .. " has no LowPolyDinoAssets entry while its slot is empty")
    end
  end
  local readyShipped = SH.readyIds()
  local nBound = 0 for _ in BOUND do nBound += 1 end
  check(#readyShipped == nBound, "exactly the pinned ids are ready in the shipped config")
  -- flag off with the SHIPPED module: still byte-identical egg rolls (the flag decides, a bound slot alone changes nothing)
  check(goldenHash(mkRM(Config, SH), "run") == GOLDEN and goldenHash(mkRM(Config, SH), "nest") == GOLDEN, "flag off with the shipped bound slots: identical to the pre-BD-604 module")
end
check(#CombatConfig.SecretSpecies == 9, "CombatConfig.SecretSpecies lists the same nine")
check(weightSum == 108, "provisional drop weights sum to 108 (100 for the first seven, plus the cockatoo 5 and the eagle 3, docs/115 SS14)")
-- SS5
check(S0.Species.budgiesaurus.class == "Fly" and S0.Species.foxosaurus.class == "Ground" and S0.Species.penguin.class == "Water" and S0.Species.cockatoosaurus.class == "Fly" and S0.Species.eaglesaurus.class == "Fly", "SS5 / SS14 classes")
for _, id in {"chickosaurus", "pigeon", "dodo", "duck"} do check(S0.Species[id].class == "Ground", id .. " Ground") end
-- SS1: not a sixth tier
check(#Config.SpeciesRarityNames == 5 and Config.SpeciesRarityScale == 5 and #Config.SpeciesOrder == 22, "still five tiers and 22 normal species")
check(S0.Chance == 0.005 and S0.RarityLabel == "Secret" and S0.Version == "bd228-secret-v1", "SS2/SS3 constants")
-- LowPolyDinoAssets consistency guard: a filled slot must come with a registry entry of the same id and class.
for _, id in mkShipped().Order do
  local row = mkShipped().Species[id]
  if row.assetId > 0 then
    check(LowPoly[id] ~= nil and LowPoly[id].assetId == row.assetId and LowPoly[id].class == row.class, id .. " slot and LowPolyDinoAssets agree")
  end
end

---------------------------------------------------------------- flag-off identity (byte-identical egg rolls)
local RMoff = mkRM(Config, S0)
check(goldenHash(RMoff, nil) == GOLDEN, "flag off, no origin: identical to the pre-BD-604 module")
check(goldenHash(RMoff, "run") == GOLDEN, "flag off, origin run: identical")
check(goldenHash(RMoff, "nest") == GOLDEN, "flag off, origin nest: identical")
local onCfg = table.clone(Config) onCfg.SecretSpeciesEnabled = true
local RMonEmpty = mkRM(onCfg, mkSecret())
check(goldenHash(RMonEmpty, "run") == GOLDEN, "flag ON but every model slot empty: still identical (no draw, no field)")
check(goldenHash(RMonEmpty, "nest") == GOLDEN, "flag ON, nest, slots empty: identical")
-- the module is never even required with the flag off
local requested = 0
do
  local MODS = {Config = Config, ProgressionConfig = ProgressionConfig}
  local SERVICES = {ReplicatedStorage = {Shared = {Config = "Config", ProgressionConfig = "ProgressionConfig", SecretSpeciesConfig = "Secret"}}}
  local game = {GetService = function(_, n) return SERVICES[n] end}
  local script = {Parent = {}}
  local require = function(id) if id == "Secret" then requested += 1 end return MODS[id] end
  local RM = @@REWARD_MATH@@
  for i = 1, 200 do RM.computeChestReward(Rng(i), 40, "run") end
end
check(requested == 0, "flag off: SecretSpeciesConfig is never required by RewardMath")

---------------------------------------------------------------- SS2 eligibility: shop / paid / unknown origins never roll
local Sr = readyAll(mkSecret())
for _, origin in {"shop", "crystal_shop", "gift", "paid", "robux", "robux_nest", "legacy", "chest", "alpha_chest", "RUN", "Run", " run", "run ", "nests", "", 5, true, {}} do
  local rng = Rng(5)
  for _ = 1, 2000 do check(Sr.roll(rng, origin) == nil, "origin never rolls: " .. tostring(origin)) end
  check(rng.calls == 0, "an ineligible origin never touches the random source: " .. tostring(origin))
  local reward = {speciesId = "compy"}
  Sr.attach(reward, rng, origin)
  check(keyCount(reward) == 1, "an ineligible origin leaves the reward untouched")
end
do
  local rng = Rng(5)
  check(Sr.roll(rng, nil) == nil and rng.calls == 0, "nil origin never rolls")
  local always = Sr.Chance
  Sr.Chance = 1
  check(Sr.roll(Rng(1), "crystal_shop") == nil and Sr.roll(Rng(1), "gift") == nil, "even a 100% chance never rolls for a shop or gift origin")
  check(Sr.roll(Rng(1), "run") ~= nil and Sr.roll(Rng(1), "nest") ~= nil, "run and nest are the eligible origins")
  Sr.Chance = always
end
check(Sr.eligibleOrigin("run") and Sr.eligibleOrigin("nest") and keyCount(Sr.EligibleOrigins) == 2, "exactly two eligible origins")

-- RewardMath with the flag ON and every slot filled: no origin = no secret, ever
do
  local onSecret = readyAll(mkSecret())
  onSecret.Chance = 1 -- a certain hit for any eligible egg, so a leak would show at once
  local RM = mkRM(onCfg, onSecret)
  local rng = Rng(99)
  for i = 1, 200000 do
    local r = RM.computeChestReward(rng, (i % 400) + 1)
    if r.secretSpeciesId ~= nil or r.secretRollVersion ~= nil or keyCount(r) ~= 4 then error("a shop-style roll (no origin) carried a secret at " .. i) end
  end
  local r = RM.computeChestReward(Rng(3), 40, "run")
  check(r.secretSpeciesId ~= nil and r.secretRollVersion == "bd228-secret-v1" and r.speciesId ~= nil and Config.SpeciesRarities[r.speciesId] ~= nil,
    "an eligible run egg records the roll and keeps the normally rolled species")
end
print("shop / paid / unknown origins: 200,000 origin-less rolls and 18 ineligible origins never carried a secret")

---------------------------------------------------------------- SS2 flat 0.5% (statistics)
local function bounds(n) local mean = n * 0.005 local sigma = math.sqrt(n * 0.005 * 0.995) return mean - 4.5 * sigma, mean + 4.5 * sigma, sigma end
do
  local secret = readyAll(mkSecret())
  local RM = mkRM(onCfg, secret)
  local sizes = {1, 40, 120, 400}
  local function run(count, originOf, sizeOf, seed)
    local rng = Rng(seed)
    local hits, normalMismatch = 0, 0
    local bySpecies = {}
    for i = 1, count do
      local r = RM.computeChestReward(rng, sizeOf(i), originOf(i))
      check(r.secretRollVersion == "bd228-secret-v1", "every rolled egg records the roll version")
      if r.secretSpeciesId then
        hits += 1
        bySpecies[r.secretSpeciesId] = (bySpecies[r.secretSpeciesId] or 0) + 1
        check(secret.Species[r.secretSpeciesId] ~= nil and Config.SpeciesRarities[r.speciesId] ~= nil, "a hit adds the secret next to a valid normal species")
      end
    end
    return hits, bySpecies
  end
  local lo, hi = bounds(200000)
  local hitsRun, bySpecies = run(200000, function() return "run" end, function(i) return sizes[(i % 4) + 1] end, 424242)
  check(hitsRun >= lo and hitsRun <= hi, string.format("run chance flat 0.5%%: %d hits in 200,000 (allowed %.0f..%.0f)", hitsRun, lo, hi))
  local hitsNest = run(200000, function() return "nest" end, function() return 120 end, 515151)
  check(hitsNest >= lo and hitsNest <= hi, string.format("nest chance flat 0.5%%: %d hits in 200,000 (allowed %.0f..%.0f)", hitsNest, lo, hi))
  -- Flat: a 400-egg (long, BIG-heavy) run is not luckier than a 1-egg run.
  local loS, hiS, sigma = bounds(100000)
  local hits1 = run(100000, function() return "run" end, function() return 1 end, 31337)
  local hits400 = run(100000, function() return "run" end, function() return 400 end, 73313)
  check(hits1 >= loS and hits1 <= hiS and hits400 >= loS and hits400 <= hiS, string.format("1 egg %d and 400 eggs %d both within 4.5 sigma of 500", hits1, hits400))
  check(math.abs(hits1 - hits400) <= 5 * math.sqrt(2) * sigma, "no run-size effect: |hits(1) - hits(400)| = " .. math.abs(hits1 - hits400))
  -- species split follows the weights (4.5 sigma each)
  local total = 0
  for _, n in bySpecies do total += n end
  for _, id in secret.Order do
    local p = secret.Species[id].weight / 100
    local mean = total * p
    local sd = math.sqrt(total * p * (1 - p))
    local got = bySpecies[id] or 0
    check(math.abs(got - mean) <= 4.5 * sd, string.format("%s drew %d of %d secret hits (expected %.0f)", id, got, total, mean))
  end
  print(string.format("flat 0.5%%: run %d / 200,000, nest %d / 200,000, 1 egg %d / 100,000, 400 eggs %d / 100,000", hitsRun, hitsNest, hits1, hits400))
end
-- Direct roll: only ready secrets can drop, and the hit rate stays 0.5% when only some are ready
do
  local S = mkSecret()
  S.Species.penguin.assetId, S.Species.duck.assetId = 111, 222
  check(#S.readyIds() == 2 and S.readyIds()[1] == "duck" and S.readyIds()[2] == "penguin", "readyIds follow roster order")
  local rng = Rng(8080)
  local hits, split = 0, {duck = 0, penguin = 0}
  for _ = 1, 400000 do
    local id = S.roll(rng, "run")
    if id then
      hits += 1
      check(id == "duck" or id == "penguin", "only a ready secret can drop: " .. tostring(id))
      split[id] += 1
    end
  end
  local lo, hi = bounds(400000)
  check(hits >= lo and hits <= hi, string.format("partial roster keeps the flat 0.5%% (%d / 400,000)", hits))
  local pDuck = 18 / 30
  check(math.abs(split.duck - hits * pDuck) <= 4.5 * math.sqrt(hits * pDuck * (1 - pDuck)), "duck : penguin follows 18 : 12")
  local none = mkSecret()
  local rng2 = Rng(1)
  for _ = 1, 1000 do check(none.roll(rng2, "run") == nil, "no ready secret: no roll") end
  check(rng2.calls == 0, "no ready secret: the random source is untouched")
end

---------------------------------------------------------------- model gate
do
  local S = mkSecret()
  local egg = {speciesId = "compy", secretSpeciesId = "chickosaurus", secretRollVersion = S.Version}
  check(S.resolve(egg) == nil, "an empty model slot: nothing hatches as the secret (a flag flip alone is safe)")
  S.Species.chickosaurus.assetId = 4242
  check(S.resolve(egg) == "chickosaurus", "a filled slot resolves")
  check(S.resolve({secretSpeciesId = "chickosaurus"}) == nil, "no roll version: not trusted")
  check(S.resolve({secretSpeciesId = "chickosaurus", secretRollVersion = "other"}) == nil, "a different roll version is not trusted")
  check(S.resolve({secretSpeciesId = "compy", secretRollVersion = S.Version}) == nil, "a normal species id is never a secret")
  check(S.resolve({secretSpeciesId = "nope", secretRollVersion = S.Version}) == nil and S.resolve(nil) == nil and S.resolve(5) == nil, "garbage resolves to nothing")
  for _, bad in {0, -1, 1.5, 0 / 0, math.huge, "123", true, false} do
    S.Species.chickosaurus.assetId = bad
    check(S.modelReady("chickosaurus") == false, "a bad slot value is not ready: " .. tostring(bad))
  end
  check(S.newEntry().base == 0 and S.newEntry().gold == 0 and S.newEntry().diamond == 0 and next(S.newEntry().variants) == nil, "lazy entry shape")
end

---------------------------------------------------------------- SS3 / SS4 Index
do
  local S = mkSecret()
  local normal = {"compy", "raptor"}
  local off = S.indexOrder(Config.SpeciesOrder, false)
  check(rawequal(off, Config.SpeciesOrder) and rawequal(S.indexOrder(Config.SpeciesOrder, nil), Config.SpeciesOrder) and rawequal(S.indexOrder(Config.SpeciesOrder, "yes"), Config.SpeciesOrder),
    "flag off: the Index order is the very same table (identical Index)")
  local on = S.indexOrder(Config.SpeciesOrder, true)
  check(#on == 31 and #Config.SpeciesOrder == 22 and on[22] == Config.SpeciesOrder[22] and on[23] == "chickosaurus" and on[29] == "foxosaurus" and on[30] == "cockatoosaurus" and on[31] == "eaglesaurus", "flag on: 22 normal cards, then 9 secret cards")
  for i = 1, 22 do check(on[i] == Config.SpeciesOrder[i], "normal order unchanged") end
  -- hidden card
  local hidden = S.indexCard("budgiesaurus", false)
  check(hidden.nameText == "???" and hidden.rarityText == "Secret" and hidden.locked == true and hidden.showButton == false and hidden.status == "Secret dino", "hidden card")
  for _, v in hidden do check(not (typeof(v) == "string" and (string.find(string.lower(v), "budgie") or string.find(string.lower(v), "fly"))), "a hidden card leaks neither name nor class") end
  check(hidden.silhouette == false, "no model yet: no silhouette (a plain ? mark), never a broken dino")
  S.Species.budgiesaurus.assetId = 99
  check(S.indexCard("budgiesaurus", false).silhouette == true and S.indexCard("budgiesaurus", false).nameText == "???", "model ready: a silhouette, still no name")
  local found = S.indexCard("budgiesaurus", true)
  check(found.nameText == "Budgiesaurus" and found.rarityText == "Secret" and found.locked == false and found.showButton == true, "found card: real name and the Secret chip")
  -- counting
  check(S.countFound(nil) == 0 and S.countFound({}) == 0 and S.countFound("x") == 0, "nothing found")
  local collection = {
    compy = {base = 9, gold = 0, diamond = 0}, tyrannosaurus = {base = 1, gold = 1, diamond = 1},
    chickosaurus = {base = 1, gold = 0, diamond = 0, events = {}, variants = {}},
    pigeon = {base = 0, gold = 0, diamond = 0, events = {}, variants = {}},
    dodo = {base = 0, gold = 0, diamond = 0, events = {}, variants = {ab = {count = 1}}},
    duck = {base = 0, gold = 0, diamond = 0, events = {rain = 1}, variants = {}},
  }
  check(S.countFound(collection) == 3, "base, variant and event copies count; a zero entry and normal species do not")
  local sum = S.summary(S.countFound(collection))
  check(sum.text == "3 / 9 secrets found" and sum.found == 3 and sum.total == 9, "summary text")
  check(S.summary(2).text == "2 / 9 secrets found" and S.summary(-4).found == 0 and S.summary(99).found == 9, "summary clamps")
  -- the normal 22-species completion number is independent of secrets
  local function normalFound(collection)
    local n = 0
    for _, id in Config.SpeciesOrder do
      local e = collection[id]
      if e and (e.base > 0 or e.gold > 0 or e.diamond > 0) then n += 1 end
    end
    return n
  end
  local withSecrets = table.clone(collection)
  local without = table.clone(collection)
  for _, id in S.Order do without[id] = nil end
  check(normalFound(withSecrets) == normalFound(without) and normalFound(withSecrets) == 2, "secrets never change the Collected X of 22 number")
end

print(string.format("secret species part A passed (%d checks)", checks))
'''


def part_a():
    s = PURE
    for token, path in [
        ('@@CONFIG@@', 'src/shared/Config.luau'),
        ('@@PROGRESSION_CONFIG@@', 'src/shared/ProgressionConfig.luau'),
        ('@@COMBAT_CONFIG@@', 'src/shared/CombatConfig.luau'),
        ('@@LOWPOLY@@', 'src/shared/LowPolyDinoAssets.luau'),
        ('@@SECRET_SHIPPED@@', 'src/shared/SecretSpeciesConfig.luau'),
        ('@@REWARD_MATH@@', 'src/server/RewardMath.luau'),
    ]:
        s = s.replace(token, module(path))
    s = s.replace('@@SECRET@@', empty_secret_module())
    s = s.replace('@@BOUND@@', ', '.join(f'{k} = {v}' for k, v in BOUND_IDS.items()))
    s = s.replace('@@GOLDEN@@', str(GOLDEN_FLAG_OFF_HASH))
    # docs/152 BD-626: under the all-on rehearsal Config part A's flag-off section (the golden hash of the flag-off reward draws) runs on a
    # private copy of the Config with SecretSpeciesEnabled forced off; part B has its own flag-on runs.
    return rehearsal_env.pin(s, 'check(Config.SecretSpeciesEnabled == false, "the committed flag is OFF")',
                             'Config = table.clone(Config) Config.SecretSpeciesEnabled = false', label='secret species flag-off pin')


# ---------------------------------------------------------------------------------------------------------------- part B
REPO = r'''
local function newUser(id)
 local u={Parent=true,UserId=id,Name="P"..id,attrs={}}
 function u:SetAttribute(k,v) self.attrs[k]=v end
 function u:GetAttribute(k) return self.attrs[k] end
 return u
end
local function key(id) return "u:"..tostring(id) end
local checks=0
local function check(cond,msg) checks+=1 if not cond then error("FAILED: "..msg,2) end end
local function keyCount(t) local n=0 for _ in t do n+=1 end return n end

-- the secret module the harness serves to RewardMath and to each repository instance
local function mkSecret() return @@SECRET@@ end -- an all-empty copy (neutral universe)
local function mkShipped() return @@SECRET_SHIPPED@@ end -- the module exactly as shipped (docs/173)
local BOUND = {@@BOUND@@}
local function ready(S, only)
 local i=0
 for _,id in S.Order do i+=1 S.Species[id].assetId=(if only==nil or only==id then 7770000+i else 0) end
 return S
end
local function makeRepo() return @@REPO_MODULE@@ end
local cfg=GameConfig -- the mutable table every module of the prefix captured
cfg.RunEggMaxPerRun=500
cfg.DeveloperProducts={}

-- canonical, order-independent text of a value (sorted keys)
local function ser(v)
 if type(v)~="table" then return tostring(v) end
 local keys={} for k in v do table.insert(keys,k) end
 table.sort(keys,function(a,b) return tostring(a)<tostring(b) end)
 local out={} for _,k in keys do table.insert(out,tostring(k).."="..ser(v[k])) end
 return "{"..table.concat(out,",").."}"
end
-- everything about the eggs a run produced EXCEPT queue guids and clock times: the rolls themselves
local function digest(profile)
 local parts={}
 local function add(tag,egg) table.insert(parts,tag..":"..ser({reward=egg.reward,genes=egg.genes,shiny=egg.shiny,big=egg.big,eventId=egg.eventId,mutationId=egg.mutationId,source=egg.source,traitRollVersion=egg.traitRollVersion})) end
 for _,egg in profile.eggs do add("q",egg) end
 for _,egg in profile.runEggBank or {} do add("b",egg) end
 return table.concat(parts,"|")
end
local function scanForSecret(v,path)
 if type(v)=="table" then
  for k,x in v do
   local name=tostring(k):lower()
   if string.find(name,"secret",1,true) then return path.."/"..name end
   local found=scanForSecret(x,path.."/"..tostring(k)) if found then return found end
  end
 elseif type(v)=="string" then
  local text=v:lower()
  for _,id in {"chickosaurus","pigeon","dodo","duck","penguin","budgiesaurus","foxosaurus","cockatoosaurus","eaglesaurus","secret"} do if string.find(text,id,1,true) then return path.."="..v end end
 end
 return nil
end
local function claimAll(repo,u)
 local outcomes={}
 local guard=0
 while #(u.attrs.ChestQueueJson or {})>0 and guard<400 do
  guard+=1
  local chest=u.attrs.ChestQueueJson[1]
  local ok,h=repo.claimChest(u,chest.id)
  if not ok then break end
  table.insert(outcomes,h)
 end
 return outcomes
end

---------------------------------------------------------------- B1 flag OFF: nothing secret anywhere
cfg.SecretSpeciesEnabled=false
CURRENT_SECRET=mkSecret()
local R0=makeRepo()
resetSeed(500)
local u0=newUser(7001)
check(R0.load(u0),"load")
check(keyCount(data[key(7001)].collection)==22,"a new profile has exactly the 22 normal species")
for i=1,3 do check(R0.commitRunSettlement(u0,"digest-run-"..i,120,nil,300),"settle") end
local digestOff=digest(data[key(7001)])
for _,egg in data[key(7001)].eggs do check(keyCount(egg.reward)==4,"flag off: a queue egg reward has the four original fields") end
for _,egg in data[key(7001)].runEggBank do check(keyCount(egg.reward)==4,"flag off: a banked egg reward has the four original fields") end
local outcomes0=claimAll(R0,u0)
check(#outcomes0>=300,"claimed the eggs of three 120-egg runs, got "..#outcomes0)
for _,h in outcomes0 do check(h.secret==nil and h.secretSpeciesId==nil and h.secretRollVersion==nil,"flag off: no secret field on an outcome") end
R0.release(u0)
check(scanForSecret(data[key(7001)],"profile")==nil,"flag off: the saved profile never mentions a secret ("..tostring(scanForSecret(data[key(7001)],"profile"))..")")
check(keyCount(data[key(7001)].collection)==22,"flag off: still 22 collection entries after hatching")

---------------------------------------------------------------- B2 flag ON, slots EMPTY: byte-identical egg digests
cfg.SecretSpeciesEnabled=true
CURRENT_SECRET=mkSecret()
local R1=makeRepo()
resetSeed(500)
local u1=newUser(7002)
check(R1.load(u1),"load")
for i=1,3 do check(R1.commitRunSettlement(u1,"digest-run-"..i,120,nil,300),"settle (flag on, slots empty)") end
check(digest(data[key(7002)])==digestOff,"flag ON with every model slot empty: the egg digests are byte-identical to flag OFF")
local outcomes1=claimAll(R1,u1)
for _,h in outcomes1 do check(h.secret==nil,"slots empty: no secret outcome") end
R1.release(u1)
check(scanForSecret(data[key(7002)],"profile")==nil and keyCount(data[key(7002)].collection)==22,"slots empty: the profile is untouched")

---------------------------------------------------------------- B3 flag ON, slots filled, real 0.5%: metadata recorded on every egg
cfg.SecretSpeciesEnabled=true
CURRENT_SECRET=ready(mkSecret())
local R2=makeRepo()
local u2=newUser(7003)
check(R2.load(u2),"load")
check(R2.commitRunSettlement(u2,"meta-run",400,nil,300),"settle 400 eggs")
local rolled=0
for _,list in {data[key(7003)].eggs,data[key(7003)].runEggBank} do
 for _,egg in list do
  rolled+=1
  check(egg.reward.secretRollVersion=="bd228-secret-v1","every earned run egg records the roll version in its metadata")
  check(GameConfig.SpeciesRarities[egg.reward.speciesId]~=nil and egg.reward.count==1,"the normally rolled species stays valid in reward.speciesId")
  if egg.reward.secretSpeciesId then check(CURRENT_SECRET.Species[egg.reward.secretSpeciesId]~=nil,"a recorded secret is a real secret id") end
 end
end
check(rolled==400,"all 400 run eggs went through the roll")
R2.release(u2)
check(R2.load(u2),"a profile whose eggs carry the roll metadata reloads (validation never rejects it)")
R2.release(u2)

---------------------------------------------------------------- B4 forced hits (Chance = 1, only Chickosaurus ready): hatch, lazy entry, rarest, order
cfg.SecretSpeciesEnabled=true
local forced=ready(mkSecret(),"chickosaurus")
forced.Chance=1
CURRENT_SECRET=forced
local R3=makeRepo()
local u3=newUser(7004)
check(R3.load(u3),"load")
check(data[key(7004)].collection.chickosaurus==nil,"no secret key before the first secret hatch (lazy)")
local rarestBefore=data[key(7004)].metrics.rarest
check(R3.commitRunSettlement(u3,"forced-run",12,nil,300),"settle 12 forced eggs")
local line={}
for _,egg in data[key(7004)].eggs do table.insert(line,egg) end
for _,egg in data[key(7004)].runEggBank do table.insert(line,egg) end
for _,egg in line do check(egg.reward.secretSpeciesId=="chickosaurus" and egg.reward.secretRollVersion=="bd228-secret-v1","forced: every egg carries the secret") end
local hatched,failedCount=0,0
for _,h in claimAll(R3,u3) do
 if h.failed then failedCount+=1 check(h.count==0 and h.secret==nil,"a failed Cracked egg hatches nothing and reveals no secret")
 else hatched+=1 check(h.speciesId=="chickosaurus" and h.secret==true and h.count==1,"the secret species is what hatches") end
end
check(hatched>=1,"at least one forced egg hatched")
-- bank eggs refill the queue as it drains
local guard=0
while #(u3.attrs.ChestQueueJson or {})>0 and guard<50 do
 guard+=1 local ok,h=R3.claimChest(u3,u3.attrs.ChestQueueJson[1].id) check(ok,"claim") if h.failed then failedCount+=1 else hatched+=1 check(h.speciesId=="chickosaurus","drained bank egg hatches the secret") end
end
local entry=data[key(7004)].collection.chickosaurus
check(entry~=nil and entry.diamond==0 and type(entry.variants)=="table","the collection entry was created lazily on the first secret hatch")
local copies=entry.base+entry.gold for _,v in entry.variants do copies+=v.count end for _,n in entry.events do copies+=n end
check(copies==hatched,"every successful secret hatch is exactly one copy ("..copies.." vs "..hatched..")")
check(data[key(7004)].metrics.rarest==rarestBefore,"a secret species never raises metrics.rarest (it is not a tier)")
check(u3.attrs.CollectionJson.chickosaurus~=nil,"the Index sees the secret through CollectionJson")
check(keyCount(data[key(7004)].collection)==23,"22 normal entries plus the one secret entry")
R3.release(u3)
check(R3.load(u3),"the profile with a secret entry reloads")
R3.release(u3)

-- reveal order: eggs that carry a secret come last in the batch
local mixed=ready(mkSecret()) mixed.Chance=0.3
CURRENT_SECRET=mixed
local R4=makeRepo()
local u4=newUser(7005)
check(R4.load(u4),"load")
check(R4.commitRunSettlement(u4,"mixed-run",200,nil,300),"settle")
local seenSecret,secretCount=false,0
local order={}
for _,egg in data[key(7005)].eggs do table.insert(order,egg) end
for _,egg in data[key(7005)].runEggBank do table.insert(order,egg) end
for _,egg in order do
 if egg.reward.secretSpeciesId then seenSecret=true secretCount+=1 else check(not seenSecret,"a normal egg appeared after a secret egg") end
end
check(secretCount>20 and secretCount<180,"mixed batch has both kinds ("..secretCount..")")
R4.release(u4)

---------------------------------------------------------------- B5 nests are eligible too (free), the crystal shop never
local nestSecret=ready(mkSecret()) nestSecret.Chance=1
CURRENT_SECRET=nestSecret
local R5=makeRepo()
local u5=newUser(7006)
check(R5.load(u5),"load")
check(R5.commitRunSettlement(u5,"nest-run",12,nil,300),"settle with a nest")
local nest=data[key(7006)].eggNests[1]
check(nest~=nil and nest.eggs==nil,"a nest dropped")
R5.release(u5)
data[key(7006)].eggNests[1].state="incubating" data[key(7006)].eggNests[1].readyAt=1
data[key(7006)].runEggBank={} data[key(7006)].eggs={}
check(R5.load(u5),"reload with a ready nest")
local okN,nestOutcome=R5.claimNest(u5,nest.nestId)
check(okN,"claim the ready nest")
local nestEggs=0
for _,list in {data[key(7006)].eggs,data[key(7006)].runEggBank} do
 for _,egg in list do
  nestEggs+=1
  check(egg.source.kind=="nest" and egg.reward.secretSpeciesId~=nil and egg.reward.secretRollVersion=="bd228-secret-v1","a free nest egg went through the roll (kind "..tostring(egg.kind)..")")
 end
end
check(nestEggs>=GameConfig.NestMinSize,"the nest produced its eggs ("..nestEggs..")")
R5.release(u5)

-- the crystal shop egg: even at a 100% chance it never carries a secret
local shop=ready(mkSecret()) shop.Chance=1
CURRENT_SECRET=shop
local R6=makeRepo()
local u6=newUser(7007)
check(R6.load(u6),"load")
R6.release(u6)
data[key(7007)].progression.crystals=1000
data[key(7007)].eggs={}
check(R6.load(u6),"reload with crystals")
check(R6.progressionAction(u6,"buyEgg","random","secret-shop-1",false),"the crystal shop sold an egg")
local bought=data[key(7007)].eggs[#data[key(7007)].eggs]
check(bought~=nil and bought.source.kind=="crystal_shop" and bought.reward.secretSpeciesId==nil and bought.reward.secretRollVersion==nil and keyCount(bought.reward)==4,
 "a shop egg carries no secret and no roll metadata, even with a 100% chance and every slot filled")
local okH,hShop=R6.claimChest(u6,bought.eggId)
check(okH and hShop.secret==nil and GameConfig.SpeciesRarities[hShop.speciesId]~=nil,"a shop egg hatches a normal species")
R6.release(u6)

---------------------------------------------------------------- B6 the gate at hatch time
-- (a) flag ON but the slot is EMPTY now: an egg that carries a secret hatches its normal species.
local gate=mkSecret()
gate.Chance=1
CURRENT_SECRET=ready(mkSecret(),"pigeon") CURRENT_SECRET.Chance=1
local Rg=makeRepo()
local ug=newUser(7008)
check(Rg.load(ug),"load")
check(Rg.commitRunSettlement(ug,"gate-run",5,nil,300),"settle")
Rg.release(ug)
for _,egg in data[key(7008)].eggs do check(egg.reward.secretSpeciesId=="pigeon","eggs rolled while the pigeon slot was filled") end
CURRENT_SECRET.Species.pigeon.assetId=0 -- the slot empties (a model withdrawn)
local Rg2=makeRepo()
local ug2=newUser(7008)
check(Rg2.load(ug2),"reload")
for _,h in claimAll(Rg2,ug2) do check(h.secret==nil and GameConfig.SpeciesRarities[h.speciesId]~=nil,"an empty slot: the normal species hatches, never a broken secret") end
check(data[key(7008)].collection.pigeon==nil,"an empty slot: no collection entry for the secret")
Rg2.release(ug2)
-- (b) the flag is OFF now: the same kind of egg hatches the normal species too.
cfg.SecretSpeciesEnabled=true
CURRENT_SECRET=ready(mkSecret(),"duck") CURRENT_SECRET.Chance=1
local Rh=makeRepo()
local uh=newUser(7009)
check(Rh.load(uh),"load")
check(Rh.commitRunSettlement(uh,"flagoff-run",5,nil,300),"settle")
Rh.release(uh)
cfg.SecretSpeciesEnabled=false
local Rh2=makeRepo()
local uh2=newUser(7009)
check(Rh2.load(uh2),"reload with the flag off")
for _,h in claimAll(Rh2,uh2) do check(h.secret==nil and GameConfig.SpeciesRarities[h.speciesId]~=nil,"flag turned OFF: eggs that carry a secret hatch their normal species") end
check(data[key(7009)].collection.duck==nil,"flag off: no secret collection entry")
Rh2.release(uh2)
cfg.SecretSpeciesEnabled=true

---------------------------------------------------------------- B7 fusion treats a secret like any other species (6 -> Gold)
cfg.IdentityPersistentEnabled=true
cfg.IdentityFusionPreviewEnabled=true
local fuse=ready(mkSecret(),"chickosaurus") fuse.Chance=1
CURRENT_SECRET=fuse
local Rf=makeRepo()
local uf=newUser(7010)
check(Rf.load(uf),"load with identity on")
local donors={}
for round=1,30 do
 check(Rf.commitRunSettlement(uf,"fuse-run-"..round,10,nil,300),"settle")
 for _,h in claimAll(Rf,uf) do
  if h.instanceIds then for _,id in h.instanceIds do check(h.speciesId=="chickosaurus","identity species") table.insert(donors,id) end end
 end
 if #donors>=6 then break end
end
check(#donors>=6,"collected six secret instances ("..#donors..")")
local six={table.unpack(donors,1,6)}
local sidecar=data[key(7010)].dinosaurIdentity
check(sidecar~=nil and sidecar.instances[six[1]].speciesId=="chickosaurus","the identity sidecar tracks the secret species")
local quote,why=Rf.quoteFusion(uf,"gold",six)
check(quote~=nil,"quoteFusion accepts six secret donors: "..tostring(why))
local okF,committed,status=Rf.fuseDinosaurs(uf,{token="secret-fuse",targetStage="gold",donorIds=six,quoteDigest=quote.quoteDigest,consentDigest=quote.consentDigest})
check(okF and status=="fused","fusion of six Chickosaurus -> Gold: "..tostring(status))
check(data[key(7010)].collection.chickosaurus.gold>=1,"a Gold Chickosaurus exists after the fusion")
Rf.release(uf)
cfg.IdentityPersistentEnabled=false
cfg.IdentityFusionPreviewEnabled=false

---------------------------------------------------------------- B8 RB1: the frozen Build 020 reader loads and keeps secret data
@@OLD_WORLD@@
local VOLATILE={session=true,revision=true}
local function sameData(a,b,ignore)
 for k,v in a do if not (ignore and ignore[k]) and ser(v)~=ser(b[k]) then return false,k end end
 for k in b do if not (ignore and ignore[k]) and a[k]==nil then return false,k end end
 return true
end
local rb=ready(mkSecret(),"chickosaurus") rb.Chance=1
CURRENT_SECRET=rb
local Rn=makeRepo()
local un=newUser(7011)
check(Rn.load(un),"load")
check(Rn.commitRunSettlement(un,"rb1-run",40,nil,300),"settle 40 forced secret eggs")
check(Rn.claimChest(un,un.attrs.ChestQueueJson[1].id),"hatch one page of ten (HatchPageSize)")
local hasSecretEntry=data[key(7011)].collection.chickosaurus~=nil
check(hasSecretEntry,"the first eggs are safe (never Cracked), so a secret entry exists")
Rn.release(un)
local secretProfile=copy(data[key(7011)])
local secretEggs=0
for _,list in {secretProfile.eggs,secretProfile.runEggBank or {}} do for _,egg in list do if egg.reward.secretSpeciesId then secretEggs+=1 end end end
check(secretEggs>=25,"the profile still holds unhatched eggs that carry a secret ("..secretEggs.." of "..#secretProfile.eggs.." queued + "..#(secretProfile.runEggBank or {}).." banked)")
-- Build 020 reads it
local uo=newUser(7011)
check(OldRepo.load(uo) and uo.attrs.ProfileState=="Loaded","Build 020 LOADS a profile with secret egg metadata and a secret collection entry")
local afterLoad=data[key(7011)]
local same,diff=sameData(secretProfile,afterLoad,VOLATILE)
check(same,"Build 020 load keeps every field byte for byte; differing: "..tostring(diff))
check(ser(afterLoad.collection.chickosaurus)==ser(secretProfile.collection.chickosaurus),"the secret collection entry is kept untouched")
check(OldRepo.renew(uo),"Build 020 renew")
-- Build 020 hatches one of the secret-tagged eggs: it knows only the normal species, so a normal dino hatches and nothing breaks
local queue=uo.attrs.ChestQueueJson
local headReward=nil
for _,egg in data[key(7011)].eggs do if egg.eggId==queue[1].id then headReward=egg.reward end end
local okOld,hOld=OldRepo.claimChest(uo,queue[1].id)
check(okOld and GameConfig.SpeciesRarities[hOld.speciesId]~=nil and hOld.speciesId==headReward.speciesId,"Build 020 hatches the normally rolled species of a secret-tagged egg")
OldRepo.release(uo)
-- the current build loads it again and the secret entry survives
local Rn2=makeRepo()
local un2=newUser(7011)
check(Rn2.load(un2),"the current build reloads the profile Build 020 touched")
check(data[key(7011)].collection.chickosaurus~=nil,"the secret entry survived Build 020")
Rn2.release(un2)
-- a profile that never saw a secret is identical for both readers (RB1 baseline)
cfg.SecretSpeciesEnabled=false
CURRENT_SECRET=mkSecret()
local Rz=makeRepo()
local uz=newUser(7012)
check(Rz.load(uz) and Rz.commitRunSettlement(uz,"rb1-flag-off",10,nil,300),"a flag-off run")
Rz.release(uz)
check(scanForSecret(data[key(7012)],"profile")==nil,"the flag-off profile has no secret data")
local uzo=newUser(7012)
check(OldRepo.load(uzo) and uzo.attrs.ProfileState=="Loaded","Build 020 loads a flag-off profile")
OldRepo.release(uzo)
check(OldConfig.SecretSpeciesEnabled==nil,"Build 020 has no secret flag at all")

---------------------------------------------------------------- B9 equip and play a found secret (BD-606, SS7) and the RB1 fallback
cfg.SecretSpeciesEnabled=true
local eq=ready(mkSecret(),"chickosaurus") eq.Chance=1
CURRENT_SECRET=eq
local Re=makeRepo()
local ue=newUser(7013)
check(Re.load(ue),"load")
check(ue.attrs.EquippedSpeciesId=="compy","a new profile plays the Compy")
local okLocked,lockedWhy=Re.equipSpecies(ue,"chickosaurus")
check(not okLocked and lockedWhy=="locked","a secret that was never found cannot be equipped (locked), got "..tostring(lockedWhy))
check(Re.commitRunSettlement(ue,"equip-run",12,nil,300),"settle forced secret eggs")
local hatchedSecret=0
for _,h in claimAll(Re,ue) do if h.speciesId=="chickosaurus" and not h.failed then hatchedSecret+=1 end end
local guardE=0
while #(ue.attrs.ChestQueueJson or {})>0 and guardE<50 do
 guardE+=1 local okc,hc=Re.claimChest(ue,ue.attrs.ChestQueueJson[1].id) if not okc then break end if hc.speciesId=="chickosaurus" and not hc.failed then hatchedSecret+=1 end
end
check(hatchedSecret>=1,"found at least one secret Chickosaurus ("..hatchedSecret..")")
local okEq,whyEq=Re.equipSpecies(ue,"chickosaurus")
check(okEq and whyEq=="equipped","a found secret species can be equipped (flag on, model ready): "..tostring(whyEq))
check(ue.attrs.EquippedSpeciesId=="chickosaurus","the player now plays the secret species (attribute)")
local stored=data[key(7013)]
check(stored.equippedSpeciesId=="compy" and stored.equippedVariantKey==nil,"RB1: the stored equipped species is still a species Build 020 knows (the fallback), never the secret id")
check(type(stored.equippedSecret)=="table" and stored.equippedSecret.speciesId=="chickosaurus","the secret is the additive record beside it")
for k in stored do check(k~="equippedSpeciesId" or stored[k]=="compy","no field stores the secret id as the equipped species") end
local okAgain,whyAgain=Re.equipSpecies(ue,"chickosaurus")
check(okAgain and whyAgain=="already_equipped","equipping the same secret again changes nothing")
-- an exact copy (variant key) of the secret
local firstVariant=nil
for vk,v in data[key(7013)].collection.chickosaurus.variants do if v.count>0 then firstVariant=vk break end end
if firstVariant then
 local okV,whyV=Re.equipSpecies(ue,"chickosaurus",firstVariant)
 check(okV and whyV=="equipped" and data[key(7013)].equippedSecret.variantKey==firstVariant and data[key(7013)].equippedVariantKey==nil,"an exact secret copy is recorded in the secret record, the stored variant key stays empty")
 check(ue.attrs.EquippedSpeciesId=="chickosaurus","still the secret species with its variant")
 local okBad=Re.equipSpecies(ue,"chickosaurus","no-such-variant")
 check(not okBad,"a variant the player does not own is refused")
end
Re.release(ue)
local secretStored=copy(data[key(7013)])

-- RB1: Build 020 loads the profile, keeps every field, and plays the fallback dino (no SchemaError)
local uoe=newUser(7013)
check(OldRepo.load(uoe) and uoe.attrs.ProfileState=="Loaded","RB1: Build 020 LOADS a profile that equipped a secret species")
check(uoe.attrs.EquippedSpeciesId=="compy","RB1: Build 020 plays the fallback Compy (the equipped-species field falls back, it does not refuse)")
local sameE,diffE=sameData(secretStored,data[key(7013)],VOLATILE)
check(sameE,"RB1: Build 020 load keeps every field byte for byte (incl. equippedSecret); differing: "..tostring(diffE))
check(OldRepo.renew(uoe),"Build 020 renew keeps the profile")
OldRepo.release(uoe)
check(data[key(7013)].equippedSecret~=nil and data[key(7013)].equippedSecret.speciesId=="chickosaurus","the secret record survived Build 020")

-- the current build reads the record again (flag on, model ready, secret still owned)
local Re2=makeRepo()
local ue2=newUser(7013)
check(Re2.load(ue2) and ue2.attrs.EquippedSpeciesId=="chickosaurus","the current build plays the secret again after Build 020 touched the profile")
Re2.release(ue2)

-- flag OFF: the record is ignored, the fallback dino is played, and a request for the secret is as unknown as before the feature
cfg.SecretSpeciesEnabled=false
local Re3=makeRepo()
local ue3=newUser(7013)
check(Re3.load(ue3) and ue3.attrs.EquippedSpeciesId=="compy","flag off: the Compy is played, nothing breaks")
local okOff,whyOff=Re3.equipSpecies(ue3,"chickosaurus")
check(not okOff and whyOff=="unknown_species","flag off: equipping a secret is refused exactly like an unknown species ("..tostring(whyOff)..")")
Re3.release(ue3)
check(ser(data[key(7013)].equippedSecret)==ser(secretStored.equippedSecret),"flag off: the profile is not rewritten by merely loading")

-- flag on but the model slot withdrawn: the fallback is played, a request is refused
cfg.SecretSpeciesEnabled=true
local gone=ready(mkSecret(),"chickosaurus") gone.Species.chickosaurus.assetId=0
CURRENT_SECRET=gone
local Re4=makeRepo()
local ue4=newUser(7013)
check(Re4.load(ue4) and ue4.attrs.EquippedSpeciesId=="compy","an emptied model slot: the Compy is played")
local okGone,whyGone=Re4.equipSpecies(ue4,"chickosaurus")
check(not okGone and whyGone=="unknown_species","an emptied model slot: the equip is refused")
Re4.release(ue4)

-- a re-equip by an older build wins (the stored species is no longer the fallback)
CURRENT_SECRET=ready(mkSecret(),"chickosaurus") CURRENT_SECRET.Chance=1
data[key(7013)].equippedSpeciesId="triceratops"
local Re5=makeRepo()
local ue5=newUser(7013)
check(Re5.load(ue5) and ue5.attrs.EquippedSpeciesId=="triceratops","a stale secret record never overrides a newer equip of another species")
Re5.release(ue5)
data[key(7013)].equippedSpeciesId="compy"

-- equipping a normal species clears the record; the secret can be picked again
local Re6=makeRepo()
local ue6=newUser(7013)
check(Re6.load(ue6) and ue6.attrs.EquippedSpeciesId=="chickosaurus","secret equipped again")
local okN1,whyN1=Re6.equipSpecies(ue6,"compy")
check(okN1 and whyN1=="equipped" and ue6.attrs.EquippedSpeciesId=="compy" and data[key(7013)].equippedSecret==nil,"equipping a normal species clears the secret record")
local okN2=Re6.equipSpecies(ue6,"chickosaurus")
check(okN2 and ue6.attrs.EquippedSpeciesId=="chickosaurus","and the secret can be equipped again")
-- losing the last copy falls back to the Compy by itself
Re6.release(ue6)
data[key(7013)].collection.chickosaurus={base=0,gold=0,diamond=0,events={},variants={}}
local Re7=makeRepo()
local ue7=newUser(7013)
check(Re7.load(ue7) and ue7.attrs.EquippedSpeciesId=="compy","a secret the player no longer owns (all copies fused away) falls back to the Compy")
Re7.release(ue7)
-- junk records are ignored, never an error
for _,junk in {5,"chickosaurus",{speciesId=5},{speciesId="nope"},{speciesId="pigeon"},{speciesId="chickosaurus",variantKey=7}} do
 data[key(7013)].equippedSecret=junk
 local Rj=makeRepo()
 local uj=newUser(7013)
 check(Rj.load(uj) and uj.attrs.EquippedSpeciesId=="compy","a junk equippedSecret record is ignored")
 Rj.release(uj)
end
cfg.SecretSpeciesEnabled=true

---------------------------------------------------------------- B9 the SHIPPED roster (docs/173): flag on, the real bound ids, Chance forced to 1
-- Only the pinned bound species can drop, from run and free nest eggs, never from a shop egg; the real chance is untouched by the forcing below.
do
 local shipped=mkShipped()
 check(shipped.Chance==0.005,"the shipped chance is the flat 0.5%")
 shipped.Chance=1
 CURRENT_SECRET=shipped
 local Rs=makeRepo()
 local us=newUser(7020)
 check(Rs.load(us),"load")
 check(Rs.commitRunSettlement(us,"shipped-run",30,nil,300),"settle 30 eggs with the shipped roster")
 local n=0
 for _,list in {data[key(7020)].eggs,data[key(7020)].runEggBank} do
  for _,egg in list do
   n+=1
   check(egg.reward.secretRollVersion=="bd228-secret-v1" and BOUND[egg.reward.secretSpeciesId]~=nil,"every egg carries a secret, and only a pinned real model can drop")
  end
 end
 check(n==30,"all 30 run eggs rolled")
 local hatched=0
 local seen={}
 for _,h in claimAll(Rs,us) do
  if not h.failed then hatched+=1 seen[h.speciesId]=true check(h.secret==true and BOUND[h.speciesId]~=nil and h.count==1,"a hatched secret is a pinned bound species") end
 end
 check(hatched>=1,"at least one shipped secret hatched")
 -- with several bound species a 30-egg run need not hit every one: each species that hatched has its lazy entry, a bound species that did not hatch has none
 for id in BOUND do
  local entry=data[key(7020)].collection[id]
  if seen[id] then check(entry~=nil and type(entry.variants)=="table","the lazy collection entry exists for "..id)
  else check(entry==nil,"a bound secret that did not hatch has no collection entry: "..id) end
 end
 for _,id in shipped.Order do
  if BOUND[id]==nil then check(data[key(7020)].collection[id]==nil,"an empty-slot secret never gets a collection entry: "..id) end
 end
 Rs.release(us)
 -- the crystal shop still never rolls, even with the shipped roster and a 100% chance
 local Rs2=makeRepo()
 local us2=newUser(7021)
 check(Rs2.load(us2),"load")
 Rs2.release(us2)
 data[key(7021)].progression.crystals=1000
 data[key(7021)].eggs={}
 check(Rs2.load(us2),"reload with crystals")
 check(Rs2.progressionAction(us2,"buyEgg","random","shipped-shop-1",false),"the crystal shop sold an egg")
 local bought=data[key(7021)].eggs[#data[key(7021)].eggs]
 check(bought~=nil and bought.reward.secretSpeciesId==nil and bought.reward.secretRollVersion==nil and keyCount(bought.reward)==4,"a shop egg carries no secret with the shipped roster")
 Rs2.release(us2)
end
cfg.SecretSpeciesEnabled=true

print(string.format("secret species part B passed (%d checks)",checks))
'''


def part_b():
    prefix = verify_rewards.HARNESS.split('local function user(id)')[0]
    # 1. a global the repository tests use to swap the secret module and to restart the deterministic PRNG
    prefix = 'local CURRENT_SECRET=nil\n' + prefix
    patches = [
        ('local seedCounter=1\n', 'local seedCounter=1\nlocal function resetSeed(n) seedCounter=n end\n'),
        # docs/152: verify_rewards' harness now carries the real SecretSpeciesConfig for every rewards-family verifier (the rehearsal turns the flag on).
        # Here the module under test is swapped between sub-tests, so the base module becomes a proxy onto CURRENT_SECRET.
        ('SecretSpecies=' + profile_sources.neutral_secret_module(), 'SecretSpecies=setmetatable({}, {__index = function(_, key) return CURRENT_SECRET[key] end})'),
    ]
    for old, new in patches:
        assert prefix.count(old) == 1, 'harness patch target changed in verify_rewards: ' + old[:60]
        prefix = prefix.replace(old, new)
    # the frozen Build 020 reader: the OLD-world block of the rollback body, up to its NEW-world section
    old_world = verify_rollback.BODY.split('-- ===== OLD world')[1].split('-- ===== NEW world')[0]
    old_world = old_world.split(chr(10), 1)[1]  # drop the rest of the marker line
    body = REPO.replace('@@OLD_WORLD@@', old_world)
    for token, path in [
        ('@@OLD_CONFIG@@', verify_rollback.FIXTURE + 'Config.luau'),
        ('@@OLD_PROGRESSION_CONFIG@@', verify_rollback.FIXTURE + 'ProgressionConfig.luau'),
        ('@@OLD_GENETICS@@', verify_rollback.FIXTURE + 'EggGenetics.luau'),
        ('@@OLD_RULES@@', verify_rollback.FIXTURE + 'ProgressionRules.luau'),
        ('@@OLD_TRAITS@@', verify_rollback.FIXTURE + 'EggTraits.luau'),
        ('@@OLD_REWARD_MATH@@', verify_rollback.FIXTURE + 'RewardMath.luau'),
        ('@@OLD_REPO@@', verify_rollback.FIXTURE + 'ProfileRepository.luau'),
        ('@@SECRET_SHIPPED@@', 'src/shared/SecretSpeciesConfig.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        body = body.replace(token, module(path))
    body = body.replace('@@SECRET@@', empty_secret_module())
    body = body.replace('@@BOUND@@', ', '.join(f'{k} = {v}' for k, v in BOUND_IDS.items()))
    s = prefix + '\n' + body
    for token, path in [
        ('@@PROGRESSION_CONFIG@@', 'src/shared/ProgressionConfig.luau'),
        ('@@GAME_CONFIG@@', 'src/shared/Config.luau'),
        ('@@FOOD_RULES@@', 'src/shared/FoodCatchRules.luau'),
        ('@@GENETICS@@', 'src/shared/EggGenetics.luau'),
        ('@@EGG_TRAITS@@', 'src/shared/EggTraits.luau'),
        ('@@RULES@@', 'src/shared/ProgressionRules.luau'),
        ('@@FUSION_ODDS@@', 'src/server/FusionOdds.luau'),
        ('@@REVEAL_SKIP@@', 'src/shared/RevealSkip.luau'),
        ('@@NEST_QUEUE@@', 'src/shared/NestQueue.luau'),
        ('@@FTUE_RULES@@', 'src/shared/FtueRules.luau'),
        ('@@SETTINGS_MODEL@@', 'src/shared/SettingsModel.luau'),
        ('@@PAID_RANDOM_GATE@@', 'src/shared/PaidRandomGate.luau'),
        ('@@REWARD_MATH@@', 'src/server/RewardMath.luau'),
        ('@@IDENTITY_FUSION_MODULE@@', 'src/server/IdentityFusion.luau'),
        ('@@IDENTITY_MODULE@@', 'src/server/DinosaurIdentity.luau'),
        ('@@COSMETIC_OWNERSHIP@@', 'src/server/CosmeticOwnership.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        s = s.replace(token, module(path))
    return s


# ---------------------------------------------------------------------------------------------------------------- static checks
def boot_text():
    return read('src/client/Bootstrap.client.luau') + read('src/client/ShopScreens.luau')  # BD-1020: the Egg Odds panel moved to ShopScreens


def static():
    errors = []

    def need(cond, msg):
        if not cond:
            errors.append(msg)

    config = read('src/shared/Config.luau')
    need(re.search(r'^\s*SecretSpeciesEnabled = false,', config, re.M) is not None, 'Config.SecretSpeciesEnabled must be false in source')

    # The flag is pinned OFF in the DEFAULT profile (Build 020 parity) and SET ON in the PLAYTEST profile only (docs/173, owner directive
    # 2026-10-18); verify_release enforces both on the built places. The committed source stays false.
    rules = [r for r in release_profiles.PROFILES['default'] if r.key == 'SecretSpeciesEnabled']
    need(len(rules) == 1 and rules[0].mode == 'require' and rules[0].value is False and rules[0].missing == 'error',
         "release profile 'default' must require SecretSpeciesEnabled == false (missing = error)")
    rules = [r for r in release_profiles.PROFILES['playtest'] if r.key == 'SecretSpeciesEnabled']
    need(len(rules) == 1 and rules[0].mode == 'set' and rules[0].value is True and rules[0].missing == 'error',
         "release profile 'playtest' must SET SecretSpeciesEnabled == true (docs/173)")
    need(not any(r.key == 'SecretSpeciesEnabled' for r in release_profiles.COMMON_RULES), 'the flag is not in COMMON_RULES any more (it is set by the playtest)')
    # The playtest turns it on ONLY because every slot that can drop holds a real id (docs/173): the shipped slots are exactly the pinned ids.
    slots = shipped_slots()
    need(sorted(slots) == sorted(['chickosaurus', 'pigeon', 'dodo', 'duck', 'penguin', 'budgiesaurus', 'foxosaurus', 'cockatoosaurus', 'eaglesaurus']), 'nine secret rows in SecretSpeciesConfig: ' + repr(sorted(slots)))
    need({k: v for k, v in slots.items() if v} == BOUND_IDS, f'the bound model slots {({k: v for k, v in slots.items() if v})} differ from the pinned real ids {BOUND_IDS} (docs/173): bind through tools/bind_secret_species.py and update BOUND_IDS, docs/173 and the evidence line together')
    need(len(BOUND_IDS) >= 1 and all(isinstance(v, int) and not isinstance(v, bool) and 10 ** 9 < v < 10 ** 16 for v in BOUND_IDS.values()), 'every bound id is a plain positive whole number of a real published asset (10 to 16 digits)')
    need(len(set(BOUND_IDS.values())) == len(BOUND_IDS), 'no two secrets share a model id')
    doc173 = read('docs/173-secret-roster-bind.md') if (ROOT / 'docs/173-secret-roster-bind.md').exists() else ''
    for sid, asset in BOUND_IDS.items():
        need(str(asset) in doc173, f'docs/173 lists the bound id of {sid} ({asset})')
    lowpoly = read('src/shared/LowPolyDinoAssets.luau')
    for sid, asset in BOUND_IDS.items():
        need(re.search(rf'^\s+{sid} = \{{assetId = {asset}, ', lowpoly, re.M) is not None, f'LowPolyDinoAssets has the entry of {sid} with the pinned id')
    others = [sid for sid in slots if sid not in BOUND_IDS]
    for sid in others:
        need(re.search(rf'^\s+{sid} = \{{assetId', lowpoly, re.M) is None, f'LowPolyDinoAssets has no entry for the empty slot {sid} (never invent ids)')

    # Only the two earned-egg origins pass an origin to the egg roll; every other caller passes none.
    callers = []
    for path in sorted((ROOT / 'src').rglob('*.luau')):
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if 'computeChestReward(' in line and 'function RewardMath.computeChestReward' not in line:
                callers.append((path.relative_to(ROOT).as_posix(), number, line.strip()))
    with_origin = [c for c in callers if re.search(r'computeChestReward\([^)]*,[^)]*,\s*"(run|nest)"\)', c[2])]
    without = [c for c in callers if c not in with_origin]
    need(len(with_origin) == 2 and {re.search(r'"(run|nest)"', c[2]).group(1) for c in with_origin} == {'run', 'nest'},
         'exactly two call sites pass an origin ("run" and "nest"): ' + repr(with_origin))
    need(len(without) >= 2 and all('crystal' in c[2] or 'Random.new()' in c[2] for c in without), 'every other call site passes no origin (the crystal shop and the legacy claim fallback): ' + repr(without))
    need(any('Random.new(),1)' in c[2] for c in without), 'the crystal shop roll passes no origin')

    # SecretSpeciesConfig is required lazily on the server (never at the top of a module) and only behind the flag.
    for path in ['src/server/RewardMath.luau'] + profile_sources.files():
        text = read(path)
        need(not re.search(r'^local \w+ = require\(.*SecretSpeciesConfig\)', text, re.M), path + ' must not require SecretSpeciesConfig at module level')
    rm = read('src/server/RewardMath.luau')
    need('if origin ~= nil and Config.SecretSpeciesEnabled == true then' in rm, 'RewardMath hook is behind the flag')
    repo = profile_sources.repository_text()
    need('if Config.SecretSpeciesEnabled == true and outcome.secretSpeciesId ~= nil and not (chest.genes ~= nil and not chest.genes.hatchSuccess) then' in repo, 'the hatch hook is behind the flag and skips failed Cracked eggs')
    need('secretSpecies().resolve(outcome)' in repo, 'the hatch asks resolve (the model gate)')
    need('Config.SpeciesRarities[outcome.speciesId] or 0' in repo, 'a secret species never raises metrics.rarest')
    # a secret is never mutable by request and is never written into a field Build 020 validates (BD-606, SS7: the additive equippedSecret record)
    known = repo[repo.index('local function knownSpecies'):]
    known = known[:known.index('\nend')]
    need('Secret' not in known, 'knownSpecies stays the normal 22 (the equip goes through equippedSecret, the mutate stays refused)')
    need('if Config.SecretSpeciesEnabled == true and secretSpecies().canEquip(speciesId, true) then secretEquip = true' in repo, 'the equip of a secret is behind the flag and the model-slot gate')
    need('profileValue.equippedSpeciesId = secretSpecies().EquipFallback' in repo and 'profileValue.equippedSecret = secretSpecies().equipRecord(speciesId, variantKey)' in repo,
         'a secret equip stores the fallback species and the additive record')
    need(len(re.findall(r'equippedSpeciesId\s*=\s*speciesId', repo)) == 2, 'only the normal-species equip and the Studio demo equip assign equippedSpeciesId = speciesId')
    need('local equippedId, equippedKey = equippedOf(profile)' in repo and 'equipped=(function() local id,key=equippedOf(profile)' in repo, 'the attribute, the traits and the per-dino cosmetics read the dino actually played')
    need('equippedOf' in read('src/server/ProfileRepository.luau') and 'ctx.equipped' in read('src/server/CosmeticOwnership.luau'), 'CosmeticOwnership.apply reads ctx.equipped')
    need('profile.equippedSecret ~= nil and Config.SecretSpeciesEnabled == true' in repo, 'equippedOf reads the record only with the flag on (the secret module is not required otherwise)')
    mutate = repo[repo.index('function ProfileRepository.mutateSpecies'):]
    need('if not knownSpecies(speciesId) then return false, nil, "unknown_species" end' in mutate[:600], 'mutateSpecies still refuses a secret id')
    # BD-606 SS9: the announcement and the odds line stay behind the flag
    svc = read('src/server/RareHatchService.luau')
    need('Config.SecretSpeciesEnabled == true and outcome.secret == true' in svc and 'Rare.classify(outcome, Config.SpeciesRarities[species], secretId ~= nil)' in svc, 'RareHatchService announces a secret only behind the flag and the settled outcome')
    need('require(ReplicatedStorage.Shared.SecretSpeciesConfig)' in svc and not re.search(r'^local \w+ = require\(.*SecretSpeciesConfig\)', svc, re.M), 'RareHatchService requires the secret module lazily, only behind the flag')
    need('if plan.sound ~= "" then pcall(Sfx.play, plan.sound) end' in read('src/client/RareHatchClient.client.luau'), 'the client plays no sound for a secret find')
    for path in ('src/shared/OddsCopy.luau', 'src/shared/ShopOdds.luau', 'src/shared/EggOutcomeOdds.luau', 'src/shared/EggOutcomeView.luau'):
        need('SecretSpeciesConfig' not in read(path), path + ' never reads the secret module (the shop egg odds cannot mention a secret)')
    need('if not upgradeOdds then for _,note in OddsCopy.freeEggNotes(Config.SecretSpeciesEnabled==true and #require(Shared.SecretSpeciesConfig).readyIds()>0) do' in boot_text(), 'the Egg Odds panel shows the free-egg line only behind the flag and a ready model, never in the upgrade odds')
    need(boot_text().count('freeEggNotes') == 1, 'the free-egg line has exactly one UI call site')

    # The pure module: no Roblox APIs and no Config reads (the flag is read by the callers).
    module_text = chr(10).join(line.split('--')[0] for line in read('src/shared/SecretSpeciesConfig.luau').splitlines())  # code only, no comments
    for banned in ('game:GetService', 'Instance.new', 'workspace', 'require(', 'Config.', 'Random.new', 'os.time', 'os.clock', 'task.'):
        need(banned not in module_text, 'SecretSpeciesConfig stays pure: ' + banned)

    # Client Index wiring: the 22-species number and meter are untouched; secrets are counted apart and only behind the flag.
    boot = read('src/client/Bootstrap.client.luau')
    for needle in (
        'local order=Secret.indexOrder(Config.SpeciesOrder,Config.SecretSpeciesEnabled)',
        'IndexProgress.page(#order,24,IndexProgress.state.page)',
        'local secret=i>#Config.SpeciesOrder',
        'if found and not secret then unlocked+=1 end',
        'IndexProgress.summary(unlocked,#Config.SpeciesOrder)',
        'meter(body,0,356,meterWidth,unlocked,#Config.SpeciesOrder,C.accent,progress.text)',
        'if Config.SecretSpeciesEnabled==true then label(body,Secret.summary(Secret.countFound(decoded("CollectionJson","{}"))).text',
        'require(Shared.SecretSpeciesConfig).RarityLabel',
    ):
        need(needle in boot, 'Bootstrap Index wiring missing: ' + needle)
    need(boot.count('Secret.indexCard(id,found)') == 1, 'secret cards use their own card state')

    # docs
    registry = read('docs/77-asset-registry.md')
    for name, asset in (('secret_dino_budgiesaurus', '107910518074360'), ('secret_dino_foxosaurus', '112996440434481'), ('secret_dino_chickosaurus', '108391746824463'),
                        ('secret_dino_cockatoosaurus', '77920946493998'), ('secret_dino_eaglesaurus', '116840996663024')):
        need(re.search(rf'^\| {name} \|.*{asset}', registry, re.M) is not None, f'docs/77 line for {name} ({asset})')
    need(re.search(r'^\| secret_dino_foxosaurus \|.*BOUND', registry, re.M) is not None, 'docs/77 says the Foxosaurus line is BOUND')
    decisions = read('docs/115-decisions-log.md')
    for n in range(1, 15):
        need(re.search(rf'^\| SS{n} \| \*\*LEAD \(owner delegated 2026-10-16', decisions, re.M) is not None, f'docs/115 row SS{n}')
    need('equippedSecret' in read('docs/111-rollback-drill.md'), 'docs/111 lists the additive equippedSecret field')
    need((ROOT / 'docs/149-secret-species.md').exists(), 'docs/149-secret-species.md exists')
    return errors


# ---------------------------------------------------------------------------------------------------------------- part C (BD-606)
# C1: the rare-find announcement and the odds line (pure rules, real modules).
PART_C = r'''
local R = @@RARE@@
local function mk() return @@SECRET@@ end
local Secret = mk()
local Config = ConfigForC

-- ===== SS9 announcement: calm, short, friendly, Reduce Motion safe, only when the caller says "secret" =====
local plain = R.classify({}, 2, false)
assert(plain == nil and R.classify({}, 2) == nil and R.classify({}, nil, nil) == nil, "an ordinary egg is never rare, with or without the new argument")
local sec = R.classify({}, nil, true)
assert(sec and sec.kind == "secret" and sec.secret == true and sec.score == R.SecretScore and not sec.legendary and not sec.shiny, "a secret hatch is a rare find of kind secret")
assert(R.classify({failed = true}, nil, true) == nil, "a Cracked egg is never a rare find, secret or not")
local shinySecret = R.classify({shiny = true}, nil, true)
assert(shinySecret and shinySecret.kind == "secret" and shinySecret.score > sec.score and shinySecret.score > R.classify({shiny = true}, 1).score, "a Shiny secret ranks above both")
-- the old kinds are untouched (new argument absent)
assert(R.classify({}, 5).kind == "legendary" and R.classify({shiny = true}, 1).kind == "shiny" and R.classify({eventMutationId = "x"}, 1).kind == "mutation")
-- copy: short, friendly, no loud words; others do not learn the name
local own = R.ownText(sec, "Chickosaurus")
local others = R.text("Sam", sec, "Chickosaurus")
assert(own == "Secret find! You hatched a Chickosaurus!", own)
assert(others == "Sam found a secret dino!" and not others:find("Chickosaurus"), others)
for _, name in {"Chickosaurus", "Pigeon", "Dodo", "Duck", "Penguin", "Budgiesaurus", "Foxosaurus", "Cockatoosaurus", "Eaglesaurus"} do
    for _, info in {sec, shinySecret} do
        local text = R.ownText(info, name)
        assert(#text <= 48, "short: " .. text)
        assert(#R.text(string.rep("x", 60), info, name) <= 48, "short for a long display name")
        for _, text2 in {text, R.text("Sam", info, name)} do
            assert(not text2:find("[A-Z][A-Z][A-Z]") and not text2:find("!!") and not text2:lower():find("legendary") and not text2:lower():find("guarantee"), "calm words: " .. text2)
        end
    end
end
assert(R.text("Sam", R.classify({}, 5), "T-Rex") == "Sam hatched a Legendary T-Rex!", "old announcements are unchanged")
-- Effects settings x Reduce Motion: a secret is the same calm banner everywhere: no confetti, no star pops, no light sweep, no extra sound
for _, effects in {"full", "lite", "off", "bogus"} do
    for _, calm in {true, false} do
        local plan = R.plan(effects, calm, "secret")
        assert(plan.banner == true and plan.confetti == 0 and plan.pop == 0 and plan.sweep == 0 and plan.sound == "", "secret plan " .. effects .. " calm=" .. tostring(calm))
    end
end
assert(R.plan("full", false, "shiny").sound == "shiny_bang" and R.plan("full", false, "shiny").confetti > 0, "the other kinds keep their celebration")
-- the announcer treats a secret like any rare egg: one per window, the best wins, the hatcher is then quiet
local st = R.newState()
assert(R.offer(st, 1, "s1", sec, "secret text", 10) == 10 + R.Window)
assert(R.offer(st, 1, "s2", R.classify({}, 1, false) or R.classify({}, 5), "legendary text", 10.5) == nil)
local out = R.flush(st, 1, 10 + R.Window)
assert(out and out.text == "secret text", "a secret ranks with a Legendary (ties keep the first)")

-- ===== SS9 odds line: one honest sentence, free eggs only, only while secrets can really drop =====
local Copy = OddsCopyForC
local ShopOdds = ShopOddsForC
local line = "A tiny chance of a secret dino in free eggs"
assert(Copy.secretLine == line, "the line is exactly the owner-reviewed sentence")
assert(#Copy.freeEggNotes(false) == 0 and #Copy.freeEggNotes(nil) == 0 and #Copy.freeEggNotes(0 :: any) == 0, "off: no line")
local live = Copy.freeEggNotes(true)
assert(#live == 1 and live[1] == line, "on: exactly the one line")
local lower = line:lower()
assert(lower:find("free eggs", 1, true) and lower:find("tiny chance", 1, true), "it says free eggs and a tiny chance")
for _, banned in {"guarantee", "sure", "always", "buy", "price", "sold", "robux", "crystal", "shop", "pack", "%d", "%%", "x%d"} do
    assert(not lower:find(banned), "the line must not say: " .. banned)
end
assert(#line <= 48, "short enough for a child")
-- what a SHOP egg can be never mentions a secret, whatever the flag: groups, notes, the long list, the buy sentence, the upgrade odds
local function noSecret(text) assert(not tostring(text):lower():find("secret"), "mentions a secret: " .. tostring(text)) end
for level = 0, #Progression.ConditionWeights - 1 do
    for _, group in Copy.eggGroups(level, 2) do
        noSecret(group.title) noSecret(group.note or "")
        for _, row in group.rows do noSecret(row.name) noSecret(row.text) end
    end
    for _, group in Copy.upgradeGroups(level) do
        noSecret(group.title) noSecret(group.note or "")
        for _, row in group.rows do noSecret(row.name) end
    end
    for _, isEgg in {true, false} do for _, note in Copy.notes(isEgg) do noSecret(note) end end
    for _, text in ShopOdds.lines(level) do noSecret(text) end
    noSecret(Copy.hatchSentence(level))
end
noSecret(Copy.fusionCalm) noSecret(Copy.fusionDetails)
for _, row in Config.ChestSpeciesWeights do
    assert(not Secret.isSecret(row.speciesId), "the shop species table has no secret")
end
-- "secretLive" exactly as Bootstrap computes it: the flag AND at least one model slot filled (an honest line: with every slot empty nothing can drop)
local function secretLive(flag, S) return flag == true and #S.readyIds() > 0 end
local empty = mk()
local filled = mk() filled.Species.penguin.assetId = 7770001
assert(secretLive(false, filled) == false and secretLive(true, empty) == false and secretLive(nil, filled) == false, "no line while off or while no model is ready")
assert(secretLive(true, filled) == true and #Copy.freeEggNotes(secretLive(true, filled)) == 1, "the line shows only with the flag on and a ready model")
assert(#Copy.freeEggNotes(secretLive(true, empty)) == 0, "flag on with every slot empty: still no line (nothing can drop)")
print("secret species part C passed")
'''


def part_c():
    base = verify_odds_copy.script()
    prefix = base[:-len(verify_odds_copy.BODY)]
    body = PART_C
    body = body.replace('@@RARE@@', module('src/shared/RareHatch.luau'))
    body = body.replace('@@SECRET@@', empty_secret_module())
    # the odds modules the prefix built: expose them under the names PART_C uses
    glue = 'local ConfigForC, OddsCopyForC, ShopOddsForC = Config, Copy, ShopOdds\nlocal Progression = Progression\n'
    return prefix + glue + body


# C2: a secret species WITH a model, tested with FAKE ids for every slot that is still empty (no real mesh id; the bound real ones stay as shipped;
# the flag and the shipped files stay untouched).
# The tree copy is a scratch directory; the shipped sources are only read.
WIRING_TOOLS = ['verify_scale_ladder.py', 'verify_camera_framing.py', 'verify_hit_sizes.py', 'verify_mouth_reach.py', 'verify_lowpoly_dinos.py']
SUPPORT_TOOLS = ['rehearsal_env.py']  # imported by the wiring tools above (BD-626); copied, never run
FAKE_BASE = 9990000000000  # 13 digits, all fake: never a published asset
SECRET_ROWS = re.compile(r'^(\s{12})(\w+) = \{scale = ([\d.]+), tier = (\d), basis = "(\w+)"', re.M)


def edit(path, old, new, count=1):
    text = path.read_text(encoding='utf-8')
    assert text.count(old) == count, f'{path.name}: expected {count} of {old[:70]!r}, found {text.count(old)}'
    path.write_text(text.replace(old, new), encoding='utf-8', newline='')


def edit_re(path, pattern, repl):
    """Regex edit (exactly one match): the shipped rows now hold the real measured numbers, so the mutations below match them by shape."""
    text = path.read_text(encoding='utf-8')
    new, n = re.subn(pattern, repl, text, count=1)
    assert n == 1, f'{path.name}: pattern {pattern[:70]!r} matched {n} times'
    path.write_text(new, encoding='utf-8', newline='')


def build_tree(dst, fill=True, measured=True, lowpoly=True):
    """Copy src, the five sizing verifiers and docs/114 into dst; optionally fill every still EMPTY model slot with a FAKE id (the slots bound to a
    real id keep it), add the missing LowPolyDinoAssets entries and mark the remaining ladder rows measured."""
    shutil.copytree(ROOT / 'src', dst / 'src')
    (dst / 'tools').mkdir()
    for name in WIRING_TOOLS + SUPPORT_TOOLS:
        shutil.copy(ROOT / 'tools' / name, dst / 'tools' / name)
    (dst / 'docs').mkdir()
    shutil.copy(ROOT / 'docs/114-handbook.md', dst / 'docs/114-handbook.md')
    ladder = (dst / 'src/shared/ScaleLadder.luau').read_text(encoding='utf-8')
    rows = {m.group(2): (m.group(3), m.group(4)) for m in SECRET_ROWS.finditer(ladder)}
    cfg_path = dst / 'src/shared/SecretSpeciesConfig.luau'
    classes = dict(re.findall(r'\{ id = "(\w+)", name = "[^"]+", secret = true, class = "(\w+)"', cfg_path.read_text(encoding='utf-8')))
    assert sorted(rows) == sorted(classes) and len(rows) == 9, (sorted(rows), sorted(classes))
    fakes = {}
    bound = dict(BOUND_IDS)
    for index, sid in enumerate(classes, 1):
        if sid in bound:
            fakes[sid] = bound[sid]  # a real bound id stays as shipped (its entry and measured row are already in the copied tree)
            continue
        fakes[sid] = FAKE_BASE + index
        if fill:
            text = cfg_path.read_text(encoding='utf-8')
            pattern = re.compile(r'(\{ id = "%s", name = "[^"]+", secret = true, class = "\w+", weight = \d+, assetId = )0( \})' % sid)
            assert pattern.search(text), sid
            cfg_path.write_text(pattern.sub(lambda m: m.group(1) + str(fakes[sid]) + m.group(2), text), encoding='utf-8', newline='')
    empties = [sid for sid in classes if sid not in bound]
    if fill and lowpoly:
        lp = dst / 'src/shared/LowPolyDinoAssets.luau'
        text = lp.read_text(encoding='utf-8').rstrip()
        assert text.endswith('}')
        lines = ''.join(f'    {sid} = {{assetId = {fakes[sid]}, version = "v1", scale = {rows[sid][0]}, tier = {rows[sid][1]}, class = "{classes[sid]}"}},\n' for sid in empties)
        lp.write_text(text[:-1] + lines + '}\n', encoding='utf-8', newline='')
    if fill and measured:
        text = (dst / 'src/shared/ScaleLadder.luau').read_text(encoding='utf-8')
        # BD-992: the T-Rex and Ankylosaurus rows are also `measured = false` (scaled from the Studio box), so only the secret block is flipped
        head, sep, tail = text.partition('    secret = {')
        assert sep and tail.count(', measured = false}') == len(empties), (tail.count(', measured = false}'), len(empties))
        (dst / 'src/shared/ScaleLadder.luau').write_text(head + sep + tail.replace(', measured = false}', ', measured = true}'), encoding='utf-8', newline='')
    return fakes, classes, rows


def run_tool(dst, name, runner, *extra):
    result = subprocess.run([sys.executable, str(dst / 'tools' / name), '--runner', runner, *extra], capture_output=True, text=True, cwd=str(dst))
    return result.returncode, (result.stdout + result.stderr)


def wiring(runner):
    errors = []
    summary = []

    def need(cond, msg):
        if not cond:
            errors.append(msg)

    def fresh(**kw):
        scratch = Path(tempfile.mkdtemp(prefix='ss_wiring_'))
        fakes, classes, rows = build_tree(scratch, **kw)
        return scratch, fakes, classes, rows

    # 1. the shipped tree (the pinned real ids bound, the other slots empty) passes every sizing verifier with the secret rows present
    for name in WIRING_TOOLS:
        code, out = run_tool(ROOT, name, runner)
        need(code == 0, f'{name} fails on the shipped tree: {out[-400:]}')
    # 2. all nine filled (the bound real ids plus FAKE ids for the rest, with entries and measured rows): every verifier still passes
    scratch, fakes, classes, rows = fresh()
    try:
        need(all(str(v).startswith('99900000000') for k, v in fakes.items() if k not in BOUND_IDS) and len(set(fakes.values())) == 9, 'the unbound ids are fake and distinct from each other and from the real ones')
        code, out = run_tool(scratch, 'verify_scale_ladder.py', runner, '--write-doc')
        need(code == 0, 'scale ladder (fake ids, regenerated doc) fails: ' + out[-600:])
        for name in WIRING_TOOLS:
            code, out = run_tool(scratch, name, runner)
            need(code == 0, f'{name} fails with all nine secret species filled (real + FAKE ids): {out[-600:]}')
            if name == 'verify_lowpoly_dinos.py':
                need('(9 secret slots, 9 filled)' in out, 'verify_lowpoly_dinos must see the nine filled secret entries: ' + out[-300:])
            if name == 'verify_hit_sizes.py':
                need('9 secret species' in out, 'hit sizes must cover the secret species')
        summary.append(f'9 filled secrets ({len(BOUND_IDS)} real, {9 - len(BOUND_IDS)} fake ids): scale ladder, camera framing, hit sizes, mouth reach, low-poly registry all pass')
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    # 3. mutations: each broken wiring must be caught by the named verifier
    def mutate(label, tool, expect, fn, **kw):
        scratch, fakes, classes, rows = fresh(**kw)
        try:
            fn(scratch, fakes, classes, rows)
            if tool == 'verify_scale_ladder.py':
                run_tool(scratch, tool, runner, '--write-doc')  # regenerate the doc so only the mutation can fail
            code, out = run_tool(scratch, tool, runner)
            need(code != 0 and expect in out, f'MUTATION {label}: {tool} must fail with {expect!r} (exit {code}): {out[-400:]}')
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    # since the second binding round every slot is bound to a real id with a measured row and a registry entry, so each mutation breaks one of those
    # shipped rows (matched by shape, not by number)
    def drop_penguin_entry(d, f, c, r):
        edit_re(d / 'src/shared/LowPolyDinoAssets.luau', r'    penguin = \{assetId = \d+[^\n]*\n', '')

    mutate('estimate in game', 'verify_scale_ladder.py', 'still an ESTIMATE',
           lambda d, f, c, r: edit_re(d / 'src/shared/ScaleLadder.luau', r'(chickosaurus = \{[^}]*measured = )true', r'\g<1>false'))
    mutate('filled slot without a LowPolyDinoAssets entry', 'verify_scale_ladder.py', 'has no entry', drop_penguin_entry)
    mutate('filled slot without a LowPolyDinoAssets entry (registry)', 'verify_lowpoly_dinos.py', 'no entry', drop_penguin_entry)
    mutate('model scale off the ladder', 'verify_scale_ladder.py', 'differs from the ladder',
           lambda d, f, c, r: edit_re(d / 'src/shared/LowPolyDinoAssets.luau', r'(penguin = \{assetId = \d+, version = "v\d", scale = )2\.38', r'\g<1>2.5'))
    mutate('model class wrong', 'verify_lowpoly_dinos.py', 'class',
           lambda d, f, c, r: edit(d / 'src/shared/LowPolyDinoAssets.luau', f'tier = 1, class = "Water"}}', 'tier = 1, class = "Ground"}}'))
    mutate('asset id differs from the slot', 'verify_scale_ladder.py', 'differs from the SecretSpeciesConfig slot',
           lambda d, f, c, r: edit(d / 'src/shared/LowPolyDinoAssets.luau', f'assetId = {f["duck"]}', f'assetId = {f["duck"] + 5000}'))
    mutate('invented LowPolyDinoAssets entry with an empty slot', 'verify_lowpoly_dinos.py', 'never invent ids',
           lambda d, f, c, r: edit_re(d / 'src/shared/SecretSpeciesConfig.luau', r'(\{ id = "dodo", name = "[^"]+", secret = true, class = "\w+", weight = \d+, assetId = )\d+', r'\g<1>0'))
    mutate('target off the size rule', 'verify_scale_ladder.py', 'SECRET penguin',
           lambda d, f, c, r: edit_re(d / 'src/shared/ScaleLadder.luau', r'(penguin = \{scale = [\d.]+, tier = 1, basis = "bulk", target = )5\.55', r'\g<1>6.60'))
    mutate('basis wrong for the class (Water by height)', 'verify_scale_ladder.py', 'does not fit class',
           lambda d, f, c, r: edit_re(d / 'src/shared/ScaleLadder.luau', r'(penguin = \{scale = [\d.]+, tier = 1, basis = )"bulk"', r'\g<1>"height"'))
    mutate('tier not Compy-sized', 'verify_scale_ladder.py', 'SS8 says 1',
           lambda d, f, c, r: edit_re(d / 'src/shared/ScaleLadder.luau', r'(chickosaurus = \{scale = [\d.]+, tier = )1', r'\g<1>3'))
    mutate('box drifts from the verifier list', 'verify_scale_ladder.py', 'SECRET_BOXES',
           lambda d, f, c, r: edit_re(d / 'src/shared/ScaleLadder.luau', r'(chickosaurus = \{[^}]*)width = [\d.]+', r'\g<1>width = 9.00'))
    mutate('box off the size rule', 'verify_scale_ladder.py', 'more than 2%',
           lambda d, f, c, r: edit_re(d / 'tools/verify_scale_ladder.py', r"('dodo': \([\d.]+, )[\d.]+", r'\g<1>9.00') or edit_re(d / 'src/shared/ScaleLadder.luau', r'(dodo = \{[^}]*)height = [\d.]+', r'\g<1>height = 9.00'))
    mutate('HitSize ignores the secret rows', 'verify_hit_sizes.py', 'Luau behavior checks failed',
           lambda d, f, c, r: edit(d / 'src/shared/HitSize.luau', 'ScaleLadder.dinoRow(speciesId)', '(ScaleLadder.Dino.species :: any)[speciesId]'))
    mutate('MouthReach ignores the secret rows', 'verify_mouth_reach.py', 'exceeds the cap',
           lambda d, f, c, r: edit(d / 'src/shared/MouthReach.luau', 'ScaleLadder.dinoRow(speciesId)', '(ScaleLadder.Dino.species :: any)[speciesId]'))
    summary.append('mutations caught: estimate in game, missing/invented/drifting LowPolyDinoAssets entry, wrong class, off-rule target/basis/tier/box, blind HitSize, blind MouthReach')
    return errors, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--dump', help='write the generated Luau scripts to this directory and exit (debugging)')
    args = parser.parse_args()
    errors = [] if args.dump else static()
    if errors:
        for error in errors:
            print('FAIL:', error)
        raise SystemExit(1)
    print('secret species static checks passed')
    if args.dump:
        Path(args.dump, 'part_a.luau').write_text(part_a(), encoding='utf-8')
        Path(args.dump, 'part_b.luau').write_text(part_b(), encoding='utf-8')
        Path(args.dump, 'part_c.luau').write_text(part_c(), encoding='utf-8')
        return
    status = 0
    with tempfile.TemporaryDirectory() as directory:
        for name, build in (('part_a', part_a), ('part_b', part_b), ('part_c', part_c)):
            path = Path(directory) / (name + '.luau')
            path.write_text(build(), encoding='utf-8')
            result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
            print(result.stdout, end='')
            print(result.stderr, end='')
            status = status or result.returncode
    if status == 0:
        wiring_errors, wiring_summary = wiring(args.runner)
        for line in wiring_summary:
            print(line)
        for error in wiring_errors:
            print('FAIL:', error)
        status = 1 if wiring_errors else 0
    if status == 0:
        print(f'Secret species verified (offline Luau; {len(BOUND_IDS)} of 9 model slots bound to real ids: {sorted(BOUND_IDS)}; Studio check of the Index cards and the models in game pending)')
    raise SystemExit(status)


if __name__ == '__main__':
    main()
