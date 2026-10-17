"""BD-604 / BD-228 (docs/149, docs/115 SS1 to SS6): secret silly creatures, verified by running the REAL modules in pinned Luau.

Part A (pure rules): SecretSpeciesConfig + the real RewardMath, Config, ProgressionConfig, CombatConfig, LowPolyDinoAssets.
  * flag-off identity: RewardMath.computeChestReward is byte-identical to the pre-BD-604 code (a golden hash taken from the unmodified
    module over 16,000 rolls), with and without an origin argument, and also with the flag ON while no model slot is filled;
  * the roll NEVER fires for a shop egg, a paid / Robux-linked egg, a gift, a legacy chest or any unknown origin, and never touches the
    random source for them;
  * the chance is flat 0.5% within statistical tolerance over 200,000 run rolls and 200,000 nest rolls, and does not rise with run size
    (1 egg vs 400 eggs) or nest luck;
  * the species split follows the provisional weights, and only secrets with a filled model slot can drop;
  * secrets are counted apart ("2 / 7 secrets found"), the hidden card never leaks the name, the 22-species number is untouched;
  * no secret hatches while its model slot is empty; shipped slots are empty and agree with the class table.
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
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_rewards  # noqa: E402  (reuses the mocked-DataStore prefix)
import verify_rollback  # noqa: E402  (the frozen Build 020 reader)
import release_profiles  # noqa: E402
import profile_sources  # noqa: E402

# Hash of RewardMath.computeChestReward over seeds 1..400 x run sizes {1, 40, 120, 400} x 10 rolls, taken from the UNMODIFIED module
# (origin/main 18a9d665) with the same harness. If this changes, the flag-off egg rolls are no longer identical to Build 020 as shipped.
GOLDEN_FLAG_OFF_HASH = 2926628964


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path):
    return profile_sources.module(path)  # docs/150: ProfileRepository plus the parts it installs


# ---------------------------------------------------------------------------------------------------------------- part A
PURE = r'''
local Config = @@CONFIG@@
local ProgressionConfig = @@PROGRESSION_CONFIG@@
local CombatConfig = @@COMBAT_CONFIG@@
local LowPoly = @@LOWPOLY@@
local GOLDEN = @@GOLDEN@@

local function mkSecret() return @@SECRET@@ end
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
check(#S0.Order == 7, "seven secrets")
local want = {"chickosaurus", "pigeon", "dodo", "duck", "penguin", "budgiesaurus", "foxosaurus"}
for i, id in want do check(S0.Order[i] == id, "roster order " .. id) end
local weightSum = 0
for _, id in S0.Order do
  local row = S0.Species[id]
  check(row ~= nil and row.id == id and row.secret == true, id .. " is a secret species row")
  check(typeof(row.name) == "string" and #row.name >= 3 and #row.name <= 14, id .. " has a short kid-friendly name")
  check(typeof(row.weight) == "number" and row.weight > 0, id .. " has a drop weight")
  weightSum += row.weight
  check(row.assetId == 0 and S0.modelReady(id) == false, id .. " model slot is EMPTY in the shipped config")
  check(CombatConfig.Classes[row.class] ~= nil and CombatConfig.SpeciesClasses[id] == row.class, id .. " class agrees with CombatConfig.SpeciesClasses")
  check(not table.find(Config.SpeciesOrder, id) and Config.SpeciesRarities[id] == nil and Config.SpeciesDisplayNames[id] == nil
    and Config.LegacySpeciesRarities[id] == nil, id .. " is not in the normal 22-species tables")
  for _, w in Config.ChestSpeciesWeights do check(w.speciesId ~= id, id .. " is not in the shop/odds table") end
  check(table.find(CombatConfig.SecretSpecies, id) ~= nil, id .. " is in CombatConfig.SecretSpecies")
  check(S0.isSecret(id) and not S0.isSecret(nil) and not S0.isSecret("compy") and not S0.isSecret(5), "isSecret")
  check(S0.displayTier(id) == 5 and S0.displayTier("compy") == nil, "calm Legendary look only")
  check(LowPoly[id] == nil, id .. " has no LowPolyDinoAssets entry while its slot is empty")
end
check(#CombatConfig.SecretSpecies == 7, "CombatConfig.SecretSpecies lists the same seven")
check(weightSum == 100, "provisional drop weights sum to 100")
-- SS5
check(S0.Species.budgiesaurus.class == "Fly" and S0.Species.foxosaurus.class == "Ground" and S0.Species.penguin.class == "Water", "SS5 classes")
for _, id in {"chickosaurus", "pigeon", "dodo", "duck"} do check(S0.Species[id].class == "Ground", id .. " Ground") end
-- SS1: not a sixth tier
check(#Config.SpeciesRarityNames == 5 and Config.SpeciesRarityScale == 5 and #Config.SpeciesOrder == 22, "still five tiers and 22 normal species")
check(S0.Chance == 0.005 and S0.RarityLabel == "Secret" and S0.Version == "bd228-secret-v1", "SS2/SS3 constants")
-- LowPolyDinoAssets consistency guard: a filled slot must come with a registry entry of the same id and class.
for _, id in S0.Order do
  local row = S0.Species[id]
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
  check(#on == 29 and #Config.SpeciesOrder == 22 and on[22] == Config.SpeciesOrder[22] and on[23] == "chickosaurus" and on[29] == "foxosaurus", "flag on: 22 normal cards, then 7 secret cards")
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
  check(sum.text == "3 / 7 secrets found" and sum.found == 3 and sum.total == 7, "summary text")
  check(S.summary(2).text == "2 / 7 secrets found" and S.summary(-4).found == 0 and S.summary(99).found == 7, "summary clamps")
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
        ('@@SECRET@@', 'src/shared/SecretSpeciesConfig.luau'),
        ('@@REWARD_MATH@@', 'src/server/RewardMath.luau'),
    ]:
        s = s.replace(token, module(path))
    return s.replace('@@GOLDEN@@', str(GOLDEN_FLAG_OFF_HASH))


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
local function mkSecret() return @@SECRET@@ end
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
  for _,id in {"chickosaurus","pigeon","dodo","duck","penguin","budgiesaurus","foxosaurus","secret"} do if string.find(text,id,1,true) then return path.."="..v end end
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

print(string.format("secret species part B passed (%d checks)",checks))
'''


def part_b():
    prefix = verify_rewards.HARNESS.split('local function user(id)')[0]
    # 1. a global the repository tests use to swap the secret module and to restart the deterministic PRNG
    prefix = 'local CURRENT_SECRET=nil\n' + prefix
    patches = [
        ('local seedCounter=1\n', 'local seedCounter=1\nlocal function resetSeed(n) seedCounter=n end\n'),
        ('SettingsModel="SettingsModel",PaidRandomGate="PaidRandomGate"}}', 'SettingsModel="SettingsModel",PaidRandomGate="PaidRandomGate",SecretSpeciesConfig="Secret"}}'),
        (' if id=="Config" then return GameConfig elseif id=="ProgressionConfig" then return ProgressionConfig end\n error("unexpected module "..tostring(id))',
         ' if id=="Config" then return GameConfig elseif id=="ProgressionConfig" then return ProgressionConfig elseif id=="Secret" then return CURRENT_SECRET end\n error("unexpected module "..tostring(id))'),
        ('elseif id=="PaidRandomGate" then return @@PAID_RANDOM_GATE@@ end', 'elseif id=="PaidRandomGate" then return @@PAID_RANDOM_GATE@@ elseif id=="Secret" then return CURRENT_SECRET end'),
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
        ('@@SECRET@@', 'src/shared/SecretSpeciesConfig.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        body = body.replace(token, module(path))
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
def static():
    errors = []

    def need(cond, msg):
        if not cond:
            errors.append(msg)

    config = read('src/shared/Config.luau')
    need(re.search(r'^\s*SecretSpeciesEnabled = false,', config, re.M) is not None, 'Config.SecretSpeciesEnabled must be false in source')

    # The flag is pinned OFF in the default AND the playtest profile (verify_release enforces it on the built places).
    for name in ('default', 'playtest'):
        rules = [r for r in release_profiles.PROFILES[name] if r.key == 'SecretSpeciesEnabled']
        need(len(rules) == 1 and rules[0].mode == 'require' and rules[0].value is False and rules[0].missing == 'error',
             f'release profile {name!r} must require SecretSpeciesEnabled == false (missing = error)')
    need(any(r.key == 'SecretSpeciesEnabled' for r in release_profiles.COMMON_RULES), 'the pin lives in COMMON_RULES, so every committed build has it')

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
    # a secret is not equippable or mutable by request in this PR (so Build 020 loads every profile)
    known = repo[repo.index('local function knownSpecies'):]
    known = known[:known.index('\nend')]
    need('Secret' not in known, 'knownSpecies stays the normal 22 (no equip / mutate of a secret yet)')

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
    for name, asset in (('secret_dino_budgiesaurus', '111728956844490'), ('secret_dino_foxosaurus', '119604460832523')):
        need(re.search(rf'^\| {name} \|.*{asset}.*placeholder', registry, re.M | re.I) is not None, f'docs/77 pending line for {name} ({asset})')
    decisions = read('docs/115-decisions-log.md')
    for n in range(1, 7):
        need(re.search(rf'^\| SS{n} \| \*\*LEAD \(owner delegated 2026-10-16\)', decisions, re.M) is not None, f'docs/115 row SS{n}')
    need((ROOT / 'docs/149-secret-species.md').exists(), 'docs/149-secret-species.md exists')
    return errors


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
        return
    status = 0
    with tempfile.TemporaryDirectory() as directory:
        for name, build in (('part_a', part_a), ('part_b', part_b)):
            path = Path(directory) / (name + '.luau')
            path.write_text(build(), encoding='utf-8')
            result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
            print(result.stdout, end='')
            print(result.stderr, end='')
            status = status or result.returncode
    if status == 0:
        print('Secret species verified (offline Luau; Studio check of the Index cards pending, no model slot is filled yet)')
    raise SystemExit(status)


if __name__ == '__main__':
    main()
