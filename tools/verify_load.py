"""BD-019 offline multiplayer load harness for ProfileRepository.

Runs the *real* src/server/ProfileRepository.luau (read-only, loaded unmodified)
inside Luau with a virtual clock, cooperative coroutines and a mocked DataStore
that models latency spikes, transient failures, repeated UpdateAsync transforms
and the per-server request budget (60 + numPlayers x 10 UpdateAsync-class
requests per minute, FIFO throttle queue of 30). Simulated players join, run,
collect map crystals, settle runs, reveal eggs one at a time, equip, buy potions,
hop servers and leave.

    python tools/verify_load.py --runner /path/to/luau [--json out.json]

Gated scenarios (exit 1 on failure): 8 and 12 players playing Build 020 as
shipped -- zero failed operations, no throttle-queue drops, all eggs drained,
all leases released, peak 60 s request window within the budget.
Report-only scenarios: a BD-044-style 15-egg reveal burst and a client that
spams a cheap write remote, plus an analytic 150-egg projection.

Limits: Luau mocks prove transaction/budget behaviour of the repository, not
Roblox networking, physics, rendering, frame time or real DataStore latency.
OrderedDataStore leaderboard writes use separate budgets and are not modelled.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MAX_EMBED_BYTES = 120_000  # skip large generated art tables the repository never requires

HARNESS = r'''
local SOURCES = __SOURCES__
local SCENARIOS = __SCENARIOS__

-------------------------------------------------------------------- scheduler
local now = 0
local queue = {}
local seq = 0
local function schedule(at, co, ...)
    seq += 1
    table.insert(queue, {at = at, seq = seq, co = co, args = table.pack(...)})
end
local function sleep(seconds)
    schedule(now + math.max(0, seconds or 0), coroutine.running())
    return coroutine.yield()
end
local crashes = {}
local function runQueue(untilTime)
    while #queue > 0 do
        local best = 1
        for i = 2, #queue do
            local a, b = queue[i], queue[best]
            if a.at < b.at or (a.at == b.at and a.seq < b.seq) then best = i end
        end
        local item = table.remove(queue, best)
        if item.at > untilTime then table.insert(queue, item) break end
        now = math.max(now, item.at)
        if coroutine.status(item.co) == "suspended" then
            local ok, err = coroutine.resume(item.co, table.unpack(item.args, 1, item.args.n))
            if not ok then table.insert(crashes, tostring(err)) end
        end
    end
end
local task = {
    wait = function(s) sleep(s or 0) return s or 0 end,
    spawn = function(f, ...)
        local co = if type(f) == "thread" then f else coroutine.create(f)
        schedule(now, co, ...)
        return co
    end,
    delay = function(s, f, ...) local co = coroutine.create(f) schedule(now + s, co, ...) return co end,
    defer = function(f, ...) local co = coroutine.create(f) schedule(now, co, ...) return co end,
}
local vos = setmetatable({time = function() return math.floor(now) end, clock = function() return now end}, {__index = os})

-------------------------------------------------------------------- deterministic RNG
local function minstd(seed)
    local s = (seed % 2147483646) + 1
    return function()
        s = (s * 48271) % 2147483647
        return s / 2147483647
    end
end
local seedSource = minstd(20261013)
local Random = {new = function(seed)
    local nextValue = minstd(seed or math.floor(seedSource() * 2147483646))
    local r = {}
    function r:NextNumber(a, b) local x = nextValue() if a then return a + (b - a) * x end return x end
    function r:NextInteger(a, b) return a + math.floor(nextValue() * (b - a + 1)) end
    return r
end}

-------------------------------------------------------------------- helpers
local function deepcopy(v)
    if type(v) ~= "table" then return v end
    local out = {}
    for k, x in v do out[deepcopy(k)] = deepcopy(x) end
    return out
end
local function jsonSize(v)
    local t = type(v)
    if t == "string" then return #v + 2 end
    if t == "number" then return #tostring(v) end
    if t == "boolean" then return if v then 4 else 5 end
    if t ~= "table" then return 4 end
    local n, size = 0, 2
    for k, x in v do
        n += 1
        size += jsonSize(x) + (if type(k) == "string" then #k + 3 else 0)
    end
    return size + math.max(0, n - 1)
end

-------------------------------------------------------------------- module loader
local function exists(path)
    if SOURCES[path] then return true end
    for key in SOURCES do if string.sub(key, 1, #path + 1) == path .. "/" then return true end end
    return false
end
local nodes = {}
local function node(path)
    if nodes[path] then return nodes[path] end
    local n = {__path = path}
    setmetatable(n, {__index = function(_, k)
        if k == "Parent" then local parent = string.match(path, "^(.*)/[^/]+$") return parent and node(parent) end
        if k == "Name" then return string.match(path, "[^/]+$") end
        if k == "WaitForChild" then return function(_, c) return node(path .. "/" .. c) end end
        if k == "FindFirstChild" then return function(_, c) local p = path .. "/" .. c return if exists(p) then node(p) else nil end end
        return node(path .. "/" .. k)
    end})
    nodes[path] = n
    return n
end

-------------------------------------------------------------------- shared DataStore + per-server budget
local DATA = {}
local OPLABEL = setmetatable({}, {__mode = "k"})
local M -- metrics of the running scenario

local function newMetrics()
    return {requests = {}, ops = {}, failures = {}, denials = {}, transforms = 0, writes = 0,
        throttled = 0, queueDrops = 0, maxThrottleWait = 0, transientErrors = 0, warnings = 0,
        sameKeyWithin6s = 0, maxKeyWritesPerMinute = 0, maxKeyBytesPerMinute = 0, maxProfileBytes = 0,
        sessionBusy = 0, keyWrites = {}, byLabel = {}}
end

local LATENCY_RNG = minstd(77)
local function newServer(name, jobId)
    local server = {name = name, players = {}, cache = {}, bucket = nil, last = 0, waiting = 0}
    function server.rate() return 60 + 10 * #server.players end
    local function refill()
        if server.bucket == nil then server.bucket = server.rate() server.last = now return end
        server.bucket = math.min(server.rate(), server.bucket + (now - server.last) * server.rate() / 60)
        server.last = now
    end
    local store = {}
    function store:UpdateAsync(key, transform)
        local co = coroutine.running()
        local label = OPLABEL[co] or "renew"
        refill()
        server.bucket -= 1
        if server.bucket < 0 then
            if server.waiting >= 30 then
                server.bucket += 1
                M.queueDrops += 1
                error("DataStore throttle queue full")
            end
            server.waiting += 1
            M.throttled += 1
            local wait = -server.bucket / (server.rate() / 60)
            M.maxThrottleWait = math.max(M.maxThrottleWait, wait)
            sleep(wait)
            server.waiting -= 1
        end
        table.insert(M.requests, {t = now, server = name, players = #server.players})
        M.byLabel[label] = (M.byLabel[label] or 0) + 1
        local r = LATENCY_RNG()
        sleep(if r < 0.02 then 1.5 + LATENCY_RNG() * 1.5 else 0.06 + LATENCY_RNG() * 0.25)
        if LATENCY_RNG() < SCENARIO_FAIL_RATE then
            M.transientErrors += 1
            error("502: injected transient DataStore failure")
        end
        local passes = if LATENCY_RNG() < 0.1 then 2 else 1 -- UpdateAsync may rerun transforms
        local result
        for _ = 1, passes do
            M.transforms += 1
            result = transform(deepcopy(DATA[key]))
        end
        if result == nil then return nil end
        local bytes = jsonSize(result)
        M.maxProfileBytes = math.max(M.maxProfileBytes, bytes)
        M.writes += 1
        local list = M.keyWrites[key] or {}
        M.keyWrites[key] = list
        if #list > 0 and now - list[#list].t < 6 then M.sameKeyWithin6s += 1 end
        table.insert(list, {t = now, bytes = bytes})
        DATA[key] = deepcopy(result)
        return deepcopy(result)
    end
    local guid = 0
    local services = {
        DataStoreService = {GetDataStore = function() return store end,
            GetOrderedDataStore = function() error("OrderedDataStore is not modelled") end},
        HttpService = {GenerateGUID = function() guid += 1 return name .. "-" .. guid end,
            JSONEncode = function(_, v) return deepcopy(v) end, JSONDecode = function(_, v) return deepcopy(v) end},
        RunService = {IsStudio = function() return false end},
        Players = {GetPlayers = function() return table.clone(server.players) end},
    }
    services.ReplicatedStorage = setmetatable({}, {__index = function(_, k)
        if k == "Shared" then return node("src/shared") end
        if k == "WaitForChild" or k == "FindFirstChild" then return function(_, c) return if c == "Shared" then node("src/shared") else nil end end
        error("ReplicatedStorage." .. tostring(k) .. " is not modelled")
    end})
    server.game = {GameId = 4242, PlaceId = 4243, JobId = jobId,
        GetService = function(_, id) return services[id] or error("service " .. id .. " is not modelled") end}
    local function load(n)
        local path = n.__path
        if server.cache[path] ~= nil then return server.cache[path] end
        local source = SOURCES[path] or error("module not embedded in harness: " .. path)
        local chunk = assert(loadstring(source, "=" .. path))
        setfenv(chunk, setmetatable({script = n, game = server.game, require = load, task = task, os = vos,
            warn = function() M.warnings += 1 end, Random = Random, print = function() end},
            {__index = getfenv(0)}))
        local result = chunk()
        server.cache[path] = result
        return result
    end
    server.Repository = load(node("src/server/ProfileRepository"))
    server.Config = load(node("src/shared/Config"))
    return server
end

-------------------------------------------------------------------- simulated players
local function op(label, fn, ...)
    local co = coroutine.running()
    OPLABEL[co] = label
    local results = table.pack(pcall(fn, ...))
    OPLABEL[co] = nil
    M.ops[label] = (M.ops[label] or 0) + 1
    if not results[1] then
        M.failures[label .. ":error"] = (M.failures[label .. ":error"] or 0) + 1
        return false, nil, tostring(results[2])
    end
    return table.unpack(results, 2, results.n)
end
local FAIL = {save_failed = true, lease_lost = true, profile_not_loaded = true, missing = true, not_ready = true}
local function judge(label, ok, status)
    if ok then return true end
    local key = label .. ":" .. tostring(status)
    if FAIL[status] or status == nil then M.failures[key] = (M.failures[key] or 0) + 1
    else M.denials[key] = (M.denials[key] or 0) + 1 end
    return false
end

local function newPlayer(id)
    local p = {UserId = id, Name = "Load" .. id, Parent = true, attrs = {}}
    function p:SetAttribute(k, v) self.attrs[k] = v end
    function p:GetAttribute(k) return self.attrs[k] end
    return p
end
local function join(server, p) p.Parent = true table.insert(server.players, p) end
local function leave(server, p)
    local i = table.find(server.players, p)
    if i then table.remove(server.players, i) end
end
local function keyOf(p) return "u:" .. p.UserId end

local CRYSTALS = {}
local function takeCrystal()
    for i, readyAt in CRYSTALS do
        if readyAt <= now then CRYSTALS[i] = now + 90 return true end
    end
    return false
end

local function loadWithRetry(server, p)
    for attempt = 1, 6 do
        local ok = op("load", server.Repository.load, p)
        if ok then return true end
        if p.attrs.ProfileState == "SessionBusy" then M.sessionBusy += 1 sleep(10) else
            M.failures["load:" .. tostring(p.attrs.ProfileState)] = (M.failures["load:" .. tostring(p.attrs.ProfileState)] or 0) + 1
            return false
        end
    end
    M.failures["load:session_busy_timeout"] = (M.failures["load:session_busy_timeout"] or 0) + 1
    return false
end

local function revealAll(server, p, rng, sc)
    local claimed = 0
    for _ = 1, 400 do
        local profile = DATA[keyOf(p)]
        local egg = profile and profile.eggs[1]
        if not egg then break end
        -- BD-044-style batches beyond the 5 + 10 queue: top up the overflow counter so
        -- the real claim path refills the queue and every egg costs one UpdateAsync.
        if sc.seedEggs and (p.injected or 0) < sc.seedEggs - 15 and profile.pendingChestGrants < 10 then
            profile.pendingChestGrants += 1
            p.injected = (p.injected or 0) + 1
        end
        if egg.readyAt > now then sleep(egg.readyAt - now + 0.1) end
        local ok, _, status = op("claim", server.Repository.claimChest, p, egg.eggId)
        if not judge("claim", ok, status) then break end
        claimed += 1
        sleep(sc.revealSeconds)
    end
    return claimed
end

local ACTIVE = 0
local function playerLoop(sc, servers, p, index, rng)
    ACTIVE += 1
    local server = servers[1]
    sleep(sc.joinStagger * (index - 1))
    join(server, p)
    if not loadWithRetry(server, p) then leave(server, p) ACTIVE -= 1 return end
    local runs, token = 0, 0
    local hopped = false
    local function sanctuary()
        sleep(10 + rng() * 15)
        if rng() < 0.3 then
            local collection = DATA[keyOf(p)].collection
            for _, id in server.Config.SpeciesOrder do
                local e = collection[id]
                if id ~= DATA[keyOf(p)].equippedSpeciesId and e and e.base > 0 then
                    local ok, status = op("equip", server.Repository.equipSpecies, p, id)
                    judge("equip", ok, status)
                    break
                end
            end
        end
        if rng() < 0.2 then
            token += 1
            local ok, status = op("potion", server.Repository.progressionAction, p, "buyPotion", "speed_common", p.Name .. "-potion-" .. token, false)
            judge("potion", ok, status)
        end
    end
    if sc.seedEggs then revealAll(server, p, rng, sc) sanctuary() end
    while now < sc.duration - 60 do
        runs += 1
        local runEnd = math.min(sc.duration - 30, now + sc.runMin + rng() * (sc.runMax - sc.runMin))
        while now < runEnd do
            sleep(sc.pickupMin + rng() * (sc.pickupMax - sc.pickupMin))
            if takeCrystal() then
                token += 1
                local ok, status = op("pickup", server.Repository.progressionAction, p, "grant", "crystal", p.Name .. "-crystal-" .. token, false, 3)
                judge("pickup", ok, status)
            end
        end
        local runId = p.Name .. "-run-" .. runs
        local ok, _, status = op("settle", server.Repository.commitRunSettlement, p, runId, math.floor(20 + rng() * 580))
        judge("settle", ok, status)
        if ok and rng() < 0.15 then -- duplicate end-run request must be idempotent
            local again, _, againStatus = op("settle", server.Repository.commitRunSettlement, p, runId, 10)
            judge("settle", again, againStatus)
        end
        revealAll(server, p, rng, sc)
        sanctuary()
        if sc.hop and not hopped and index <= sc.hop and now > sc.duration / 3 then
            hopped = true
            local from = server
            p.Parent = nil
            leave(from, p)
            task.spawn(function() op("release", from.Repository.release, p) end)
            sleep(3)
            server = servers[2]
            join(server, p)
            if not loadWithRetry(server, p) then leave(server, p) ACTIVE -= 1 return end
        end
    end
    p.Parent = nil
    leave(server, p)
    op("release", server.Repository.release, p)
    ACTIVE -= 1
end

local function spammer(sc, server, p)
    sleep(30)
    local ids = {"compy", "raptor"}
    local i = 0
    while now < 30 + sc.spamSeconds do
        i += 1
        local ok, status = op("spam-equip", server.Repository.equipSpecies, p, ids[i % 2 + 1])
        judge("spam-equip", ok, status)
        sleep(server.Config.EquipRequestCooldownSeconds)
    end
end

-------------------------------------------------------------------- scenario runner
local function seedProfile(server, p, sc)
    join(server, p)
    assert(server.Repository.load(p))
    server.Repository.release(p)
    leave(server, p)
    local profile = DATA[keyOf(p)]
    if sc.seedEggs then
        for i = 1, server.Config.ChestQueueCapacity do
            table.insert(profile.eggs, {eggId = p.Name .. "-seed-" .. i, kind = "alpha_chest", readyAt = 0})
        end
        profile.pendingChestGrants = math.min(10, sc.seedEggs - server.Config.ChestQueueCapacity)
    end
    if sc.spammer then profile.collection.raptor.base = 1 end
end

local function windowPeak(requests, serverName)
    local list = {}
    for _, r in requests do if r.server == serverName then table.insert(list, r) end end
    -- Budget accrued over the window: players who left still funded the bucket.
    local peak, peakBudget, ratio, j = 0, 0, 0, 1
    for i, r in list do
        while list[j].t < r.t - 60 do j += 1 end
        local count = i - j + 1
        local most = 0
        for k = j, i do most = math.max(most, list[k].players) end
        local budget = 60 + 10 * most
        if count / budget > ratio then ratio, peak, peakBudget = count / budget, count, budget end
    end
    return peak, peakBudget, ratio, #list
end

local results = {}
for _, sc in SCENARIOS do
    now = 0
    queue = {}
    DATA = {}
    CRYSTALS = {}
    for i = 1, 64 do CRYSTALS[i] = 0 end
    SCENARIO_FAIL_RATE = sc.failRate
    M = newMetrics()
    local servers = {newServer("A", "job-A"), newServer("B", "job-B")}
    local players = {}
    for i = 1, sc.players do players[i] = newPlayer(1000 + i) end
    local spamUser = if sc.spammer then newPlayer(999) else nil
    -- Setup (seeding fixtures) runs outside the measured window.
    local setup = coroutine.create(function()
        for _, p in players do seedProfile(servers[1], p, sc) end
        if spamUser then seedProfile(servers[1], spamUser, sc) end
    end)
    schedule(0, setup)
    runQueue(math.huge)
    local setupEnd = now
    M = newMetrics()
    for _, server in servers do server.bucket = nil end
    local base = setupEnd
    now = 0
    -- Shift clock: measured run starts at t=0 with a fresh budget.
    for _, server in servers do server.Repository.start() end
    local rng = minstd(sc.seed)
    for i, p in players do
        local prng = minstd(sc.seed * 100 + i)
        task.spawn(playerLoop, sc, servers, p, i, prng)
    end
    if spamUser then
        task.spawn(function()
            ACTIVE += 1
            join(servers[1], spamUser)
            if loadWithRetry(servers[1], spamUser) then spammer(sc, servers[1], spamUser) end
            spamUser.Parent = nil
            leave(servers[1], spamUser)
            op("release", servers[1].Repository.release, spamUser)
            ACTIVE -= 1
        end)
    end
    ACTIVE = 0
    runQueue(sc.duration)
    while ACTIVE > 0 and now < sc.duration + 900 do runQueue(now + 30) end
    runQueue(now + 5) -- let in-flight background releases finish
    local endTime = now
    queue = {} -- stop background renew loops of this scenario
    -- Integrity: eggs drained, leases released.
    local undrained, leased = 0, 0
    for _, p in players do
        local profile = DATA[keyOf(p)]
        if profile then
            undrained += #profile.eggs + profile.pendingChestGrants
            if profile.session ~= nil then leased += 1 end
        end
    end
    local maxKeyWrites, maxKeyBytes = 0, 0
    for _, list in M.keyWrites do
        local j = 1
        local bytes = 0
        for i, w in list do
            bytes += w.bytes
            while list[j].t < w.t - 60 do bytes -= list[j].bytes j += 1 end
            maxKeyWrites = math.max(maxKeyWrites, i - j + 1)
            maxKeyBytes = math.max(maxKeyBytes, bytes)
        end
    end
    local peakA, budgetA, ratioA, totalA = windowPeak(M.requests, "A")
    local peakB, budgetB, ratioB, totalB = windowPeak(M.requests, "B")
    local function encode(t)
        local parts = {}
        for k, v in t do table.insert(parts, string.format("%q:%d", k, v)) end
        table.sort(parts)
        return "{" .. table.concat(parts, ",") .. "}"
    end
    print(string.format(
        "RESULT {\"name\":%q,\"players\":%d,\"duration\":%d,\"simulatedSeconds\":%.1f,\"requestsA\":%d,\"requestsB\":%d," ..
        "\"peakWindowA\":%d,\"budgetA\":%d,\"ratioA\":%.3f,\"peakWindowB\":%d,\"budgetB\":%d,\"ratioB\":%.3f," ..
        "\"transforms\":%d,\"writes\":%d,\"throttled\":%d,\"queueDrops\":%d,\"maxThrottleWait\":%.2f," ..
        "\"transientErrors\":%d,\"retryWarnings\":%d,\"sessionBusy\":%d,\"sameKeyWithin6s\":%d,\"maxKeyWritesPerMinute\":%d," ..
        "\"maxKeyBytesPerMinute\":%d,\"maxProfileBytes\":%d,\"undrainedEggs\":%d,\"leasedAtEnd\":%d,\"crashes\":%d," ..
        "\"ops\":%s,\"byLabel\":%s,\"failures\":%s,\"denials\":%s}",
        sc.name, sc.players, sc.duration, endTime, totalA, totalB, peakA, budgetA, ratioA, peakB, budgetB, ratioB,
        M.transforms, M.writes, M.throttled, M.queueDrops, M.maxThrottleWait, M.transientErrors, M.warnings,
        M.sessionBusy, M.sameKeyWithin6s, maxKeyWrites, maxKeyBytes, M.maxProfileBytes, undrained, leased, #crashes,
        encode(M.ops), encode(M.byLabel), encode(M.failures), encode(M.denials)))
    for _, c in crashes do print("CRASH " .. c) end
    crashes = {}
end
'''

BASE = {"duration": 900, "joinStagger": 2, "runMin": 90, "runMax": 240, "pickupMin": 8, "pickupMax": 20,
        "revealSeconds": 5, "failRate": 0.01, "hop": 2, "seedEggs": None, "spammer": False, "spamSeconds": 0}
SCENARIOS = [
    dict(BASE, name="build020-8-players", players=8, seed=8, gated=True),
    dict(BASE, name="build020-12-players", players=12, seed=12, gated=True),
    dict(BASE, name="egg-burst-15-x12", players=12, seed=15, seedEggs=15, duration=420, gated=False),
    dict(BASE, name="egg-burst-150-x12", players=12, seed=150, seedEggs=150, duration=1200, gated=False),
    dict(BASE, name="equip-spam-8+1", players=8, seed=81, spammer=True, spamSeconds=360, duration=480, gated=False),
]


def lua_value(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise TypeError(value)


def long_string(text: str) -> str:
    level = 0
    while "]" + "=" * level + "]" in text:
        level += 1
    eq = "=" * level
    return f"[{eq}[\n{text}]{eq}]"


def harness(root: Path = ROOT) -> str:
    entries = []
    for folder in ("src/server", "src/shared"):
        for path in sorted((root / folder).glob("*.luau")):
            if path.stat().st_size > MAX_EMBED_BYTES:
                continue
            key = f"{folder}/{path.stem}"
            entries.append(f"[{json.dumps(key)}] = {long_string(path.read_text(encoding='utf-8'))}")
    sources = "{\n" + ",\n".join(entries) + "\n}"
    scenarios = "{" + ",".join(
        "{" + ",".join(f"{k}={lua_value(v)}" for k, v in sc.items() if k != "gated") + "}" for sc in SCENARIOS) + "}"
    text = HARNESS.replace("__SCENARIOS__", scenarios).replace("__SOURCES__", sources)
    return "local SCENARIO_FAIL_RATE = 0\n" + text


def projection(players: int, eggs_per_run: int, reveal_seconds: float = 5.0, renew_seconds: float = 30.0,
               pickups_per_minute: float = 64 * 60 / 90) -> dict:
    """Requests/minute if every player reveals eggs at once with one UpdateAsync per egg."""
    budget = 60 + 10 * players
    claims = players * min(60 / reveal_seconds, eggs_per_run)
    renew = players * 60 / renew_seconds
    total = claims + renew + pickups_per_minute
    return {"players": players, "eggsPerRun": eggs_per_run, "budget": budget, "requestsPerMinute": round(total, 1),
            "ratio": round(total / budget, 2), "revealMinutes": round(eggs_per_run * reveal_seconds / 60, 1)}


def gate(result: dict) -> list[str]:
    problems = []
    if result["crashes"]:
        problems.append(f"{result['crashes']} coroutine crash(es)")
    if result["failures"]:
        problems.append(f"failed operations {result['failures']}")
    if result["queueDrops"]:
        problems.append(f"{result['queueDrops']} throttle-queue drops")
    if result["undrainedEggs"]:
        problems.append(f"{result['undrainedEggs']} eggs left unclaimed")
    if result["leasedAtEnd"]:
        problems.append(f"{result['leasedAtEnd']} profiles still leased after leaving")
    for side in ("A", "B"):
        if result[f"ratio{side}"] > 1.0:
            problems.append(f"server {side} peak window {result[f'peakWindow{side}']} > budget {result[f'budget{side}']}")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True, help="path to the pinned luau executable")
    parser.add_argument("--json", type=Path, help="write all results to this file")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "load.luau"
        script.write_text(harness(), encoding="utf-8")
        completed = subprocess.run([args.runner, str(script)], capture_output=True, text=True)
    results = [json.loads(line[7:]) for line in completed.stdout.splitlines() if line.startswith("RESULT ")]
    for line in completed.stdout.splitlines():
        if line.startswith("CRASH "):
            print(line)
    if completed.returncode != 0 or len(results) != len(SCENARIOS):
        print(completed.stdout[-4000:])
        print(completed.stderr[-4000:])
        print("Load harness did not complete.")
        return 1
    failed = False
    for sc, result in zip(SCENARIOS, results):
        problems = gate(result)
        tag = "PASS" if not problems else ("FAIL" if sc["gated"] else "WARN")
        failed |= bool(problems) and sc["gated"]
        print(f"[{tag}] {result['name']}: {result['players']} players, {result['duration']}s; "
              f"requests A/B {result['requestsA']}/{result['requestsB']}, peak 60s window "
              f"{result['peakWindowA']}/{result['budgetA']} ({result['ratioA']:.0%}) on A, "
              f"{result['peakWindowB']}/{result['budgetB']} ({result['ratioB']:.0%}) on B; "
              f"transforms {result['transforms']} for {result['writes']} writes; throttled {result['throttled']} "
              f"(max wait {result['maxThrottleWait']:.1f}s); transient errors {result['transientErrors']} retried; "
              f"session-busy rejoins {result['sessionBusy']}; same-key writes <6s {result['sameKeyWithin6s']}; "
              f"max key writes/min {result['maxKeyWritesPerMinute']}, max key bytes/min {result['maxKeyBytesPerMinute']}, "
              f"max profile {result['maxProfileBytes']} bytes")
        print(f"       ops {result['ops']} requests-by-op {result['byLabel']} denials {result['denials']}")
        for problem in problems:
            print(f"       - {problem}")
    projections = [projection(n, e) for n in (8, 12) for e in (15, 150)]
    print("BD-044 projection (all players revealing simultaneously, one UpdateAsync per egg at 5 s):")
    for p in projections:
        print(f"       {p['players']} players x {p['eggsPerRun']} eggs: {p['requestsPerMinute']}/min vs budget "
              f"{p['budget']}/min ({p['ratio']:.0%}) for {p['revealMinutes']} min")
    if args.json:
        args.json.write_text(json.dumps({"scenarios": results, "projection": projections}, indent=2) + "\n", encoding="utf-8")
    print("Load harness " + ("FAILED" if failed else "passed") + " (gated: Build 020 8 and 12 player scenarios).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
