"""BD-1096: nothing but the settlement itself may keep a run in "Ending".

Studio round 5 saw one run stay in RunState "Ending" for good after a server "Script timeout" surfaced in
TelemetryService.runSettled (called on the settle thread, inline). The error killed the thread that was about to mark the run
Settled. This check runs the REAL src/server/RunLifecycle.luau and the REAL src/server/TelemetryService.luau (and the real
src/shared/RunTelemetry.luau) in pinned Luau with mocked Roblox services and proves:

  1. A telemetry report that errors, yields forever or loops long never blocks, delays or breaks the settlement: the callback
     pays once, the run ends Settled, the settle thread finishes (is not suspended), and the report had NOT started when the
     settlement returned (it runs in task.defer).
  2. The Ending watchdog: a settlement callback that threw (after paying) or never finished is force-settled ONCE (same run id,
     the ledger answers "duplicate": no double pay), a callback that keeps failing is tried exactly once more and then left
     alone, a settle call that is still running is waited for until the hard limit, and a normal settlement (or a clean "save failed" answer, which the lease renew tick retries) is never re-run.
  3. Mutants fail: telemetry put back inline, the pcall around the callback removed, the watchdog removed.

    python tools/verify_settle_guard.py --runner /path/to/luau
"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
local CFG = {RespawnDelaySeconds = 0, RunEggMaxPerRun = 400, WorldReadyTimeoutSeconds = 20, SpawnProtectionSeconds = 5, NestMinRunSeconds = 120,
    EndingWatchdogSeconds = 20, EndingWatchdogMaxSeconds = 60, RunTelemetryEnabled = true, FoodCatchRate = 40 / 500}
local clock = 100
local os = {clock = function() return clock end, time = os.time}
local printed, warned = {}, {}
local print = function(s) table.insert(printed, s) end
local warn = function(s) table.insert(warned, s) end
local typeof = function(v) return type(v) end
local Http = {GenerateGUID = function() return "run-1" end, JSONDecode = function(_, s) return {} end}
local services = {Players = {GetPlayers = function() return {} end}, HttpService = Http}
local game = {GetService = function(_, n) return services[n] end}
local workspace = {GetServerTimeNow = function() return clock end, GetAttribute = function() return nil end}

-- task: spawn runs at once (like the engine until the first yield), defer is QUEUED and run later in its own coroutine, delay is queued
local deferred, timers = {}, {}
local task = {
    spawn = function(f, ...) f(...) end,
    wait = function() end,
    defer = function(f) table.insert(deferred, f) end,
    delay = function(seconds, f) table.insert(timers, {at = clock + seconds, fn = f}) end,
}
local deferredThreads = {}
local function runDeferred()
    local queue = deferred
    deferred = {}
    for _, f in queue do
        local co = coroutine.create(f)
        table.insert(deferredThreads, co)
        local ok, err = coroutine.resume(co)
        if not ok then table.insert(warned, "deferred thread died: " .. tostring(err)) end
    end
end
-- fires every timer due at the current clock (a timer may arm another one; bounded)
local function fireTimers()
    for _ = 1, 50 do
        local due
        for i, t in timers do if t.at <= clock then due = i break end end
        if not due then return end
        local t = table.remove(timers, due)
        local co = coroutine.create(t.fn)
        local ok, err = coroutine.resume(co)
        if not ok then table.insert(warned, "timer thread died: " .. tostring(err)) end
    end
end

local RewardMath = {recordNestWeather = function(ledger) return ledger end}
local CooldownMemory = {new = function() return {allow = function() return true end} end}
local ReplicatedStorage = {Shared = {Config = CFG, IslandLayout = {}, SpawnGeometry = {}}}
services.ReplicatedStorage = ReplicatedStorage
local script = {Parent = {PrivateState = {get = function() return nil end}, RewardMath = RewardMath, CooldownMemory = CooldownMemory}}
local require = function(x) return x end

local function moduleRT() @@RT@@ end
local RT = moduleRT()
ReplicatedStorage.Shared.RunTelemetry = RT
local realRunEnd = RT.runEnd
local telemetryMode = "ok"
local telemetryStarted = false
RT.runEnd = function(input)
    telemetryStarted = true
    if telemetryMode == "error" then error("telemetry boom") end
    if telemetryMode == "yield" then coroutine.yield() end
    if telemetryMode == "loop" then local n = 0 for i = 1, 3000000 do n += i end end
    return realRunEnd(input)
end

local function moduleTS() @@TS@@ end
local TS = moduleTS()
local function moduleRL() @@RL@@ end
local RL = moduleRL()

local function mock()
    local attrs = {RunState = "Active", RunId = "r1", CatchScore = 37, RunEggEvents = "[]", GrowthScore = 50}
    local humanoid = {Health = 100}
    local character = {}
    function character:GetAttribute(n) return attrs[n] end
    function character:SetAttribute(n, v) attrs[n] = v end
    function character:FindFirstChildOfClass() return humanoid end
    function character:FindFirstChild() return nil end
    function character:WaitForChild() return nil end
    local pattrs = {ProfileState = "Loaded"}
    local player = {Character = character, Parent = true, loads = 0}
    function player:GetAttribute(n) return pattrs[n] end
    function player:SetAttribute(n, v) pattrs[n] = v end
    function player:LoadCharacterAsync() player.loads += 1 end
    return player, character, attrs, pattrs
end

-- the Bootstrap settlement callback in miniature: commit once per run id (the ledger), then the telemetry hook, then done
local ledger, pays, calls = {}, 0, 0
local behaviour = "normal" -- normal | throw_after_pay | always_throw | yield_first | save_failed
local function callback(player, runId, catchScore, reason, eggEvents, runSeconds, nestWeather)
    calls += 1
    if behaviour == "always_throw" then error("settle boom (script timeout)") end
    if behaviour == "save_failed" then return false end
    if behaviour == "yield_first" and calls == 1 then
        if not ledger[runId] then ledger[runId] = true pays += 1 end
        coroutine.yield() -- a commit that is still waiting on the DataStore
        return true
    end
    if not ledger[runId] then ledger[runId] = true pays += 1 end -- duplicate calls find the ledger entry and pay nothing
    TS.runSettled(player, reason, runSeconds, {eggCount = catchScore, nestCount = 1, crystals = 20}, runId)
    if behaviour == "throw_after_pay" and calls == 1 then error("script timeout after the commit") end
    return true
end
RL.configureSettlement(callback)

local function scenario(mode, beh)
    telemetryMode, behaviour = mode, beh
    ledger, pays, calls, printed, warned, deferred, timers, deferredThreads = {}, 0, 0, {}, {}, {}, {}, {}
    telemetryStarted = false
    clock = 100
    local player, character, attrs, pattrs = mock()
    local co = coroutine.create(function() return RL.tryEnd(player, character, "ManualExit", 9) end)
    assert(coroutine.resume(co))
    return {player = player, character = character, attrs = attrs, pattrs = pattrs, co = co}
end

-- 1. telemetry can never block, delay or break the settlement
for _, mode in {"ok", "error", "yield", "loop"} do
    local s = scenario(mode, "normal")
    assert(coroutine.status(s.co) == "dead", mode .. ": the settle thread finished (telemetry did not suspend it)")
    assert(s.attrs.RunState == "Settled", mode .. ": the run is Settled, got " .. tostring(s.attrs.RunState))
    assert(pays == 1 and calls == 1, mode .. ": paid once")
    assert(s.player.loads == 1, mode .. ": the dinosaur came back once")
    assert(telemetryStarted == false, mode .. ": the telemetry report had not started when the settlement returned")
    runDeferred()
    assert(telemetryStarted == true, mode .. ": the report runs later, in its own thread")
    if mode == "ok" then
        assert(#printed == 1 and printed[1]:find("run_end", 1, true), "the run_end line is still written")
    end
    if mode == "error" then
        local sawWarn = false
        for _, w in warned do if w:find("telemetry run_end failed", 1, true) then sawWarn = true end end
        assert(sawWarn, "a failing report is logged, not thrown")
    end
    fireTimers() clock += 100 fireTimers()
    assert(calls == 1 and pays == 1, mode .. ": the watchdog leaves a settled run alone")
end

-- telemetry switched off: the hook is a no-op and the settlement is the same
do
    CFG.RunTelemetryEnabled = false
    local s = scenario("ok", "normal")
    assert(coroutine.status(s.co) == "dead" and s.attrs.RunState == "Settled" and pays == 1, "flag off: settled")
    assert(#deferred == 0, "flag off: nothing is deferred")
    CFG.RunTelemetryEnabled = true
end

-- 2. the Ending watchdog
do -- the callback threw AFTER paying: the run stays Ending, the watchdog finishes it, nobody is paid twice
    local s = scenario("ok", "throw_after_pay")
    assert(coroutine.status(s.co) == "dead" and s.attrs.RunState == "Ending" and pays == 1 and calls == 1, "a thrown callback leaves Ending")
    clock = 100 + 19 fireTimers()
    assert(calls == 1 and s.attrs.RunState == "Ending", "not before the limit")
    clock = 100 + 20 fireTimers()
    assert(calls == 2 and pays == 1, "forced once, the ledger pays nothing more: calls " .. calls .. " pays " .. pays)
    assert(s.attrs.RunState == "Settled" and s.player.loads == 1, "the watchdog settled the run and brought the dinosaur back once")
    clock += 500 fireTimers()
    assert(calls == 2, "never forced a second time")
end
do -- a callback that keeps failing: one forced try, then left alone (no loop)
    local s = scenario("ok", "always_throw")
    clock = 100 + 20 fireTimers()
    assert(calls == 2, "original + exactly one forced call: " .. calls)
    clock += 1000 fireTimers()
    assert(calls == 2 and s.attrs.RunState == "Ending", "still failing: not retried forever")
end
do -- a settle call that is still running (a DataStore retry) is waited for until the hard limit
    local s = scenario("ok", "yield_first")
    assert(coroutine.status(s.co) == "suspended" and s.attrs.RunState == "Ending" and pays == 1, "settle thread waiting")
    clock = 100 + 20 fireTimers()
    clock = 100 + 40 fireTimers()
    clock = 100 + 59 fireTimers()
    assert(calls == 1, "no second call while the first is still running: " .. calls)
    clock = 100 + 66 fireTimers()
    assert(calls == 2 and pays == 1 and s.attrs.RunState == "Settled", "forced at the hard limit, paid once")
    local loadsBefore = s.player.loads
    coroutine.resume(s.co) -- the late original finishes: it must not respawn a second time
    assert(s.player.loads == loadsBefore and loadsBefore == 1, "one respawn only")
end
do -- a clean "false" (save failed) is the designed path (the lease renew tick retries it): the watchdog must not call the callback again
    local s = scenario("ok", "save_failed")
    assert(s.pattrs.ProfileState == "SaveFailed" and s.attrs.RunState == "Ending", "save failed is recorded")
    clock = 100 + 20 fireTimers()
    clock += 1000 fireTimers()
    assert(calls == 1, "no forced second settlement after a clean false: " .. calls)
end
do -- the player left: the watchdog does nothing (the leave path owns the settlement)
    local s = scenario("ok", "always_throw")
    s.player.Parent = nil
    clock = 100 + 20 fireTimers()
    assert(calls == 1, "a departed player is not force-settled here")
end

print("BD-1096 settle guard checks passed")
'''

MUTANTS = [
    # name, file, old, new
    ('telemetry back inline', 'src/server/TelemetryService.luau', 'task.defer(function()', ';(function(f) f() end)(function()'),
    ('no pcall around the settle callback', 'src/server/RunLifecycle.luau', 'pcall(settleRun, ', '(function(...) return true, settleRun(...) end)('),
    ('no watchdog', 'src/server/RunLifecycle.luau', '    armEndingWatchdog(player, character, snapshot, reason)\n', ''),
    ('watchdog may run twice', 'src/server/RunLifecycle.luau', '    task.delay(Config.EndingWatchdogSeconds or 20, check)\n',
     '    task.delay(Config.EndingWatchdogSeconds or 20, check)\n    task.delay((Config.EndingWatchdogSeconds or 20) + 1, check)\n'),
]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('--!strict', '')


def build(overrides=None):
    sources = {
        'RT': read('src/shared/RunTelemetry.luau'),
        'TS': read('src/server/TelemetryService.luau'),
        'RL': read('src/server/RunLifecycle.luau'),
    }
    key_of = {'src/shared/RunTelemetry.luau': 'RT', 'src/server/TelemetryService.luau': 'TS', 'src/server/RunLifecycle.luau': 'RL'}
    if overrides:
        path, old, new = overrides
        key = key_of[path]
        assert old in sources[key], 'mutant target not found: ' + old
        sources[key] = sources[key].replace(old, new, 1)
    code = HARNESS
    for key, body in sources.items():
        code = code.replace('@@' + key + '@@', body)
    return code


def run(runner, code):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'settle_guard.luau'
        path.write_text(code, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True)


def static():
    boot = read('src/server/Bootstrap.server.luau')
    assert 'Telemetry.runSettled(player, reason, runSeconds, settledOutcome, runId)' in boot, 'Bootstrap still reports settled runs to telemetry'
    ts = read('src/server/TelemetryService.luau')
    body = ts[ts.index('function TelemetryService.runSettled'):ts.index('-- BD-651')]
    assert 'task.defer(' in body and 'pcall(' in body, 'runSettled defers the report inside a pcall'
    assert 'RunTelemetry.runEnd' not in body, 'the report itself lives outside runSettled'
    cfg = read('src/shared/Config.luau')
    assert 'EndingWatchdogSeconds = 20' in cfg and 'EndingWatchdogMaxSeconds = 60' in cfg, 'watchdog config'
    food = read('src/server/FoodService.luau')
    assert 'pcall(function() telemetry().noteFood(' in food, 'the food hook cannot throw into the food tick'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static()
    result = run(args.runner, build())
    print(result.stdout, end='')
    print(result.stderr, end='')
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print('BD-1096 settle guard checks passed')
    for name, path, old, new in MUTANTS:
        mutant = run(args.runner, build((path, old, new)))
        if mutant.returncode == 0:
            print('MUTANT SURVIVED: ' + name)
            raise SystemExit(1)
        reason = (mutant.stderr.strip().splitlines() or ['?'])[0]
        print('mutant caught: ' + name + ' (' + reason[-110:] + ')')
    print('BD-1096 settle guard mutants all caught')
