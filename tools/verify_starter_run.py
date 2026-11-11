#!/usr/bin/env python3
"""BD-1163 (docs/225): the starter run, the first run of a brand-new profile (Config.StarterRunEnabled).

Runs with the pinned Luau runtime:
  1. the pure rules in src/shared/FtueRules.luau (who is a starter, the egg floor, the safe eggs, auto-start, the card, the Run
     Complete button rule, the "run again" rule), the words in src/shared/FtueCopy.luau and the `starter` field of the run_end
     telemetry line (src/shared/RunTelemetry.luau);
  2. the real src/server/StarterRunService.luau on mocked services (flag off = nothing at all; flag on = the first run starts by
     itself once per join through RunLifecycle.requestStart, for a bounded time, never for a save that settled a run);
  3. the real ProfileRepository on the verify_rewards harness (mocked DataStore): the floor of 3 eggs is paid exactly once (retry,
     outage, lost acknowledgement, reconnect), never on a second run, never for an empty run, never when the STORED save already
     settled a run; the starter eggs are never Cracked; crystals, XP and nests are those of the real catches; flag off = the old
     settlement and nothing set; no new stored field.
Then checks the wiring statically (flag false in source, profiles, one server Bootstrap line, the client card) and puts each defect
back (mutants). NOT Studio, phone or child evidence.
Usage: python tools/verify_starter_run.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_rewards  # noqa: E402

RULES = 'src/shared/FtueRules.luau'
COPY = 'src/shared/FtueCopy.luau'
TELEMETRY = 'src/shared/RunTelemetry.luau'
SERVICE = 'src/server/StarterRunService.luau'
REPO = 'src/server/ProfileRepository.luau'
EGGS = 'src/server/ProfileEggs.luau'
CLIENT = 'src/client/StarterRunClient.luau'
SCREENS = 'src/client/SmallScreens.luau'
RUN_COMPLETE = 'src/client/RunComplete.luau'
CONFIG = 'src/shared/Config.luau'
PROFILES = 'tools/release_profiles.py'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path, replacements=None):
    source = read(path)
    for old, new in (replacements or {}).get(path, []):
        assert old in source, 'mutant target missing in %s: %s' % (path, old)
        source = source.replace(old, new)
    return '(function()\n' + source + '\nend)()'


UNIT = r'''
-- WHO: a brand-new save, exactly as ProfileRepository.defaultProfile writes it (plus what the first load adds)
local function fresh()
    return {schemaVersion = 1, revision = 1, equippedSpeciesId = "compy",
        collection = {compy = {base = 1, gold = 0, diamond = 0, variants = {}}, triceratops = {base = 0, gold = 0, diamond = 0, variants = {}}},
        pendingChestGrants = 0, eggs = {}, recentOperations = {}, lastCheckpoint = {committedAt = 0, lastSettledRunId = nil},
        progression = {crystals = 0, accountXP = 0, conditionLevel = 0}, metrics = {playSeconds = 40, rarest = 0, robux = 0}, eggNests = {}}
end
local function with(change) local p = fresh() change(p) return p end
assert(R.starterQualifies(fresh()) == true, "a brand-new save is a starter")
assert(R.starterQualifies(with(function(p) p.eggNests = nil p.progression = nil p.settledRuns = {} end)) == true, "fields a new save may not have yet")
assert(not R.starterQualifies(with(function(p) p.lastCheckpoint.lastSettledRunId = "r1" end)), "a settled run id")
assert(not R.starterQualifies(with(function(p) p.settledRuns = {"r1"} end)), "the settled-run ledger")
assert(not R.starterQualifies(with(function(p) p.recentOperations = {{id = "run:r1", kind = "run", outcome = {}}} end)), "a run operation")
assert(not R.starterQualifies(with(function(p) p.recentOperations = {{id = "c", kind = "chest_claim"}} end)), "a hatch")
assert(R.starterQualifies(with(function(p) p.recentOperations = {{id = "s", kind = "settings"}} end)), "an unrelated operation does not end the starter state")
assert(not R.starterQualifies(with(function(p) p.eggs = {{eggId = "e"}} end)), "an egg in the line")
assert(not R.starterQualifies(with(function(p) p.runEggBank = {{eggId = "e"}} end)), "a banked egg")
assert(not R.starterQualifies(with(function(p) p.pendingChestGrants = 1 end)), "a granted egg")
assert(not R.starterQualifies(with(function(p) p.collection.triceratops.base = 1 end)), "a dinosaur beyond the starter Compy")
assert(not R.starterQualifies(with(function(p) p.eggNests = {{nestId = "n"}} end)), "a nest")
assert(not R.starterQualifies(with(function(p) p.progression.accountXP = 3 end)), "account XP")
assert(not R.starterQualifies(nil) and not R.starterQualifies("x") and not R.starterQualifies({}), "unreadable = not new")
assert(not R.starterQualifies(with(function(p) p.lastCheckpoint = nil end)) and not R.starterQualifies(with(function(p) p.recentOperations = nil end)), "missing ledger fields = not new")
assert(not R.starterQualifies(with(function(p) p.settledRuns = "x" end)) and not R.starterQualifies(with(function(p) p.progression = 5 end)) and not R.starterQualifies(with(function(p) p.recentOperations = {"junk"} end)))
-- EGG FLOOR
assert(R.starterEggFloor(0, 3) == 0, "no egg caught: nothing given")
assert(R.starterEggFloor(1, 3) == 3 and R.starterEggFloor(2, 3) == 3 and R.starterEggFloor(3, 3) == 3, "one or more caught: at least three")
assert(R.starterEggFloor(4, 3) == 4 and R.starterEggFloor(150, 3) == 150, "a bigger run is never lowered")
assert(R.starterEggFloor(-2, 3) == 0 and R.starterEggFloor(0/0, 3) == 0 and R.starterEggFloor("1", 3) == 0 and R.starterEggFloor(nil, 3) == 0, "bad input gives nothing")
assert(R.starterEggFloor(2, nil) == 2 and R.starterEggFloor(2, 0/0) == 2 and R.starterEggFloor(2, "3") == 2 and R.starterEggFloor(2.9, 3.9) == 3, "a bad floor changes nothing")
-- SAFE EGGS: 2 -> 3 on the starter run, never fewer than the normal rule
assert(R.SafeEggs == 2 and R.safeEggsLeft(fresh()) == 2, "the normal rule is unchanged")
assert(R.starterSafeEggs(2, 3) == 3 and R.starterSafeEggs(0, 3) == 3 and R.starterSafeEggs(5, 3) == 5 and R.starterSafeEggs(2, nil) == 2 and R.starterSafeEggs(2, 0/0) == 2)
-- AUTO START
local base = {enabled = true, starter = true, started = false, runState = "Sanctuary", attached = true}
local function auto(change) local s = table.clone(base) for k, v in change do s[k] = v end return R.starterAutoStart(s) end
assert(R.starterAutoStart(base) == true)
assert(not auto({enabled = false}) and not auto({starter = false}) and not auto({started = true}) and not auto({attached = false}), "flag, starter, once, dinosaur ready")
assert(not auto({runState = "Active"}) and not auto({runState = "Ending"}) and not auto({runState = "Settled"}) and not R.starterAutoStart(nil), "only from the hub")
-- STARTER CARD
local card = {starter = true, runState = "Active", eggs = 3, shown = false, cardEggs = 3}
local function cardNow(change) local s = table.clone(card) for k, v in change do s[k] = v end return R.starterCardNow(s) end
assert(R.starterCardNow(card) == true and cardNow({eggs = 9}) == true)
assert(not cardNow({eggs = 2}) and not cardNow({starter = false}) and not cardNow({shown = true}), "at three eggs, starters only, once per run")
assert(not cardNow({runState = "Sanctuary"}) and not cardNow({runState = "Ending"}) and not cardNow({eggs = "3"}) and not cardNow({cardEggs = 0}) and not R.starterCardNow(nil))
-- RUN COMPLETE and RUN AGAIN
assert(R.starterOnlyOpenEggs(true, true) and not R.starterOnlyOpenEggs(false, true) and not R.starterOnlyOpenEggs(true, false) and not R.starterOnlyOpenEggs(nil, nil))
local again = {starter = true, settled = true, shown = false, eggsLeft = 0, copies = 4}
local function againNow(change) local s = table.clone(again) for k, v in change do s[k] = v end return R.starterRunAgainNow(s) end
assert(R.starterRunAgainNow(again) == true)
assert(not againNow({eggsLeft = 1}) and not againNow({copies = 1}) and not againNow({shown = true}) and not againNow({settled = false}) and not againNow({starter = false}) and not R.starterRunAgainNow(nil))
-- WORDS (docs/72: short, obvious, no unit numbers, no jargon)
assert(C.starterCardTitle(3) == "You found 3 eggs!" and C.starterCardTitle(1) == "You found 1 egg!" and C.starterCardTitle(7) == "You found 7 eggs!" and C.starterCardTitle(0) == "You found 1 egg!")
assert(C.starterCardButton == "Take them home!" and C.starterRunAgain == "Run again to find new dinos!" and C.starterTrailHint == "Follow the shiny food!")
for _, s in {C.starterCardTitle(3), C.starterCardButton, C.starterCardHeading, C.starterRunAgain, C.starterTrailHint} do
    assert(#s <= 30, "fits a toast title and a button: " .. s)
    assert(not s:find("%d%a") and not s:find("%.%d") and not s:lower():find("catch") and not s:lower():find("bank") and not s:lower():find("settle"), "kid words: " .. s)
end
-- TELEMETRY: starter=true only on the starter run, and it reaches the log line
local e = T.runEnd({runSeconds = 95, reason = "ManualExit", eggs = 3, nests = 0, crystals = 4, foodCatchRate = 12 / 500, starter = true})
assert(e.starter == true and T.line(e):find('"starter":true', 1, true), "the starter run is marked")
for _, v in {false, "true", 1} do
    local other = T.runEnd({runSeconds = 95, reason = "ManualExit", eggs = 3, nests = 0, crystals = 4, foodCatchRate = 12 / 500, starter = v})
    assert(other.starter == nil and not T.line(other):find("starter", 1, true), "every other run has no starter field")
end
assert(T.runEnd({runSeconds = 1, reason = "Death", eggs = 0, nests = 0, crystals = 0}).starter == nil)
print("starter run rules ok")
'''

SERVICE_TEST = r'''
local function world(flag)
    local clock = 0
    local connects, waits, starts = 0, 0, {}
    local onWait = nil
    local added = {fns = {}}
    function added:Connect(fn) table.insert(self.fns, fn) connects += 1 end
    local list = {}
    local Players = {PlayerAdded = added, GetPlayers = function() return list end}
    local RS = {Shared = {Config = "Config", FtueRules = "FtueRules"}}
    local game = {GetService = function(_, name) return if name == "Players" then Players else RS end}
    local private = {}
    local PrivateState = {get = function(p, name) return private[p] and private[p][name] end}
    local answer = true
    local RunLifecycle = {requestStart = function(p) table.insert(starts, p) if answer == "error" then error("boom") end return answer end}
    local script = {Parent = {PrivateState = "PS", RunLifecycle = "RL"}}
    local function require(k)
        if k == "Config" then return {StarterRunEnabled = flag} elseif k == "FtueRules" then return R elseif k == "PS" then return PrivateState else return RunLifecycle end
    end
    local os = {clock = function() return clock end}
    local task = {spawn = function(fn) fn() end, wait = function(s) waits += 1 clock += s if onWait then onWait(waits) end end}
    local setmetatable = setmetatable
    local Service = @@SERVICE@@
    local function character(state, attached)
        local c = {attrs = {RunState = state, DinoAttached = attached}}
        function c:GetAttribute(k) return self.attrs[k] end
        return c
    end
    local function player(starter)
        local p = {Parent = Players, Character = nil, CharacterAdded = {fns = {}}}
        function p.CharacterAdded:Connect(fn) table.insert(self.fns, fn) connects += 1 end
        function p:spawn(c) self.Character = c for _, fn in self.CharacterAdded.fns do fn(c) end end
        private[p] = {StarterRun = if starter then 1 else 0}
        return p
    end
    return {Service = Service, added = added, list = list, player = player, character = character, starts = starts, private = private,
        connects = function() return connects end, waits = function() return waits end, setAnswer = function(v) answer = v end,
        setOnWait = function(fn) onWait = fn end, clock = function() return clock end}
end
-- flag off: nothing at all
do
    local w = world(false)
    local p = w.player(true)
    p.Character = w.character("Sanctuary", true)
    table.insert(w.list, p)
    w.Service.start()
    assert(w.connects() == 0 and #w.starts == 0 and #w.added.fns == 0 and w.waits() == 0, "flag off: no connection, no run started")
end
-- flag on
do
    local w = world(true)
    local early = w.player(true) -- already in the server with a ready dinosaur when the service starts
    early.Character = w.character("Sanctuary", true)
    table.insert(w.list, early)
    w.Service.start()
    w.Service.start()
    assert(#w.added.fns == 1, "started once")
    assert(#w.starts == 1 and w.starts[1] == early, "the first run starts by itself")
    early:spawn(w.character("Sanctuary", true))
    assert(#w.starts == 1, "once per join: the next hub visit waits for EXPLORE")
    -- a veteran is never touched
    local veteran = w.player(false)
    w.added.fns[1](veteran)
    veteran:spawn(w.character("Sanctuary", true))
    assert(#w.starts == 1 and w.waits() == 0, "a save that settled a run: no start, no waiting thread")
    -- the dinosaur is not attached yet: it waits, then starts
    local late = w.player(true)
    w.added.fns[1](late)
    local c = w.character("Sanctuary", nil)
    w.setOnWait(function(n) if n == 3 then c.attrs.DinoAttached = true end end)
    late:spawn(c)
    assert(#w.starts == 2 and w.starts[2] == late and w.waits() == 3, "waits for the dinosaur, then starts")
    w.setOnWait(nil)
    -- the run-start path says no (world loading): it keeps asking, but only for a bounded time, and never throws
    local slow = w.player(true)
    w.added.fns[1](slow)
    w.setAnswer(false)
    local before, t0 = #w.starts, w.clock()
    slow:spawn(w.character("Sanctuary", true))
    local tries = #w.starts - before
    assert(tries >= 10 and tries <= w.Service.TrySeconds / w.Service.StepSeconds + 1, "bounded retries: " .. tries)
    assert(w.clock() - t0 <= w.Service.TrySeconds + w.Service.StepSeconds, "gives up after TrySeconds")
    w.setAnswer(true)
    slow:spawn(w.character("Sanctuary", true))
    assert(#w.starts == before + tries + 1, "a refusal did not use up the one start")
    local broken = w.player(true)
    w.added.fns[1](broken)
    w.setAnswer("error")
    broken:spawn(w.character("Sanctuary", true)) -- must not throw
    w.setAnswer(true)
    -- the starter state ended while waiting (the save changed): stop
    local changed = w.player(true)
    w.added.fns[1](changed)
    local c2 = w.character("Sanctuary", nil)
    w.setOnWait(function(n) w.private[changed].StarterRun = 0 c2.attrs.DinoAttached = true end)
    local n0 = #w.starts
    changed:spawn(c2)
    assert(#w.starts == n0, "no longer a starter: no start")
    w.setOnWait(nil)
    -- already in a run or the player left: nothing
    local running = w.player(true)
    w.added.fns[1](running)
    w.setAnswer(false)
    n0 = #w.starts
    running:spawn(w.character("Active", true))
    assert(#w.starts == n0, "never from inside a run")
    local gone = w.player(true)
    w.added.fns[1](gone)
    gone.Parent = nil
    gone:spawn(w.character("Sanctuary", true))
    assert(#w.starts == n0, "a player who left is not started")
end
print("starter run service ok")
'''

E2E = r'''
local MIN=GameConfig.StarterRunMinEggs
assert(MIN==3 and GameConfig.StarterRunEggs==3 and GameConfig.StarterRunSafeEggs==3, "the PROVISIONAL numbers of docs/225")
local function line(u) local p=data[key(u)] return #p.eggs+#(p.runEggBank or {}) end
local function allEggs(u) local p=data[key(u)] local out={} for _,e in p.eggs do table.insert(out,e) end for _,e in p.runEggBank or {} do table.insert(out,e) end return out end
local function run(u,id,catches,seconds,attempts) return Repository.commitRunSettlement(u,id,catches,nil,seconds or 90,nil,attempts) end
local function has(t,word)
 if type(t)~="table" then return false end
 for k,v in t do if (type(k)=="string" and k:lower():find(word)) or has(v,word) then return true end end
 return false
end
local function topKeys(u) local keys={} for k in data[key(u)] do table.insert(keys,k) end table.sort(keys) return table.concat(keys,",") end
-- FLAG OFF (the default build): the old settlement, nothing set. Set here so the section also runs for real in the switch-on rehearsal (all flags on).
GameConfig.StarterRunEnabled=false
local off=user(116301) assert(Repository.load(off))
assert(off.attrs.StarterRun==nil, "flag off: the owner-only value is never set")
local okOff,outOff,statusOff=run(off,"off-1",1)
assert(okOff and statusOff=="committed" and outOff.eggCount==1 and outOff.starter==nil and line(off)==1, "flag off: one catch is one egg")
assert(not has(data[key(off)],"starter") and off.attrs.LastRunCatchScore==nil, "flag off: nothing about the starter run is stored or set")
local offKeys=topKeys(off)
Repository.release(off)
GameConfig.StarterRunEnabled=true
-- a veteran (the save above) is not a starter with the flag on
assert(Repository.load(off))
assert(off.attrs.StarterRun==0, "a save with a settled run is not a starter")
local okVet,outVet=run(off,"off-2",1)
assert(okVet and outVet.eggCount==1 and outVet.starter==nil and line(off)==2, "a veteran run has no floor")
Repository.release(off)
-- THE STARTER RUN: one egg caught, three eggs given, exactly once
local u=user(116302) assert(Repository.load(u))
assert(u.attrs.StarterRun==1, "a brand-new save is told it is a starter")
local plain=Rewards.computeRunReward(1,90)
local ok,outcome,status=run(u,"s-1",1)
assert(ok and status=="committed" and outcome.eggCount==MIN and outcome.starter==true and line(u)==MIN, "the floor: three eggs for a starter run that caught one")
assert(outcome.crystals==plain.crystals and outcome.accountXP==plain.accountXP and outcome.nestCount==0 and outcome.catchScore==1, "crystals, XP and nests are those of the real catches")
assert(data[key(u)].progression.crystals==plain.crystals and data[key(u)].progression.accountXP==plain.accountXP)
assert(u.attrs.LastRunCatchScore==MIN and u.attrs.LastRunEggCount==MIN, "Run Complete shows the eggs really given")
assert(u.attrs.StarterRun==0, "after the settlement the save is no longer a starter")
local ids={} for _,egg in allEggs(u) do assert(egg.source.runId=="s-1" and not ids[egg.eggId]) ids[egg.eggId]=true end
-- retry of the same run (watchdog, duplicate probe): no second payment
local again,againOut,againStatus=run(u,"s-1",1)
assert(again and againStatus=="duplicate" and againOut.eggCount==MIN and againOut.starter==true and line(u)==MIN, "a retry pays nothing more")
assert(data[key(u)].progression.crystals==plain.crystals)
-- reconnect: the same run id is still a duplicate, the next run is a normal run
Repository.release(u) assert(Repository.load(u))
assert(u.attrs.StarterRun==0 and select(3,run(u,"s-1",1))=="duplicate" and line(u)==MIN, "reconnect: no second starter run, no second payment")
local ok2,out2,status2=run(u,"s-2",1)
assert(ok2 and status2=="committed" and out2.eggCount==1 and out2.starter==nil and line(u)==MIN+1, "run 2 is a normal run: one catch, one egg")
assert(topKeys(u)==offKeys and not has(data[key(u)].lastCheckpoint,"starter"), "no new stored field: the same top-level fields as a flag-off save")
Repository.release(u)
-- an EMPTY starter run gives nothing and the save stays a starter (also across a reconnect)
local v=user(116303) assert(Repository.load(v))
local before=copy(data[key(v)])
local ok0,out0=run(v,"v-0",0)
assert(ok0 and out0.eggCount==0 and line(v)==0 and same(before,data[key(v)]), "no egg caught: no floor, nothing written")
assert(v.attrs.StarterRun==1, "still a starter")
Repository.release(v) assert(Repository.load(v))
assert(v.attrs.StarterRun==1, "a second join with no settled run: the starter run applies again")
local okV,outV=run(v,"v-1",2)
assert(okV and outV.eggCount==MIN and outV.starter==true and line(v)==MIN and v.attrs.StarterRun==0)
Repository.release(v)
-- a BIG starter run is never lowered and Run Complete keeps the real count
local b=user(116304) assert(Repository.load(b))
local okB,outB=run(b,"b-1",7)
assert(okB and outB.eggCount==7 and outB.starter==true and line(b)==7 and b.attrs.LastRunCatchScore==nil, "seven caught: seven eggs")
Repository.release(b)
-- OUTAGE: nothing is written; the retry of the same run pays the floor once
local o=user(116305) assert(Repository.load(o))
local snapshot=copy(data[key(o)])
failMode="all"
local failed,_,failedStatus=run(o,"o-1",1,90,2)
failMode=nil
assert(not failed and failedStatus=="save_failed" and same(snapshot,data[key(o)]), "outage: nothing written")
local okO,outO,statusO=run(o,"o-1",1)
assert(okO and statusO=="committed" and outO.eggCount==MIN and outO.starter==true and line(o)==MIN, "the retry after the outage pays the floor")
assert(select(3,run(o,"o-1",1))=="duplicate" and line(o)==MIN, "and only once")
Repository.release(o)
-- TRANSIENT failure and LOST ACKNOWLEDGEMENT: still exactly once
local t=user(116306) assert(Repository.load(t))
failMode="once"
local okT,outT,statusT=run(t,"t-1",1)
assert(okT and statusT=="committed" and outT.eggCount==MIN and line(t)==MIN, "a transient failure is retried inside the repository")
Repository.release(t)
local a=user(116307) assert(Repository.load(a))
failMode="ack_lost"
local okA,outA,statusA=run(a,"a-1",1)
assert(okA and statusA=="duplicate" and outA.eggCount==MIN and outA.starter==true and line(a)==MIN, "a lost acknowledgement never pays the floor twice")
assert(data[key(a)].progression.crystals==plain.crystals and a.attrs.StarterRun==0)
Repository.release(a)
-- the STORED save already settled a run (the cached copy is stale): only the eggs really caught are banked
local st=user(116308) assert(Repository.load(st))
data[key(st)].lastCheckpoint.lastSettledRunId="settled-elsewhere"
local okS,outS=run(st,"st-1",1)
assert(okS and outS.eggCount==1 and outS.starter==nil and line(st)==1, "the floor is checked against the stored save")
assert(allEggs(st)[1].source.ordinal==1)
Repository.release(st)
-- SAFE EGGS: every guaranteed starter egg hatches (Cracked is 50% at tier 0, so 40 saves x 3 eggs cannot pass by luck)
local third=0
for i=1,40 do
 local s=user(116400+i) assert(Repository.load(s))
 assert(run(s,"safe-"..i,1) and line(s)==MIN)
 for _,egg in allEggs(s) do assert(egg.genes.conditionId~="cracked", "a starter egg is never Cracked") end
 -- run 2 rolls the normal odds again
 assert(run(s,"safe2-"..i,6))
 for _,egg in allEggs(s) do if egg.source.runId=="safe2-"..i and egg.genes.conditionId=="cracked" then third+=1 end end
 Repository.release(s)
end
assert(third>40, "run 2 has the normal Cracked odds: "..third.." of 240")
print("starter run repository ok")
'''


def unit_script(replacements=None):
    s = 'local R=' + module(RULES, replacements) + '\n'
    s += 'local C=' + module(COPY, replacements) + '\n'
    s += 'local T=' + module(TELEMETRY, replacements) + '\n'
    return s + UNIT


def service_script(replacements=None):
    s = 'local R=' + module(RULES, replacements) + '\n'
    return s + SERVICE_TEST.replace('@@SERVICE@@', module(SERVICE, replacements))


def e2e_script(replacements=None):
    s = verify_rewards.script()
    head = s[:s.index('------------------------------------------------------------------ RewardMath')]
    for path in (REPO, EGGS, RULES):
        for old, new in (replacements or {}).get(path, []):
            assert old in head, 'mutant target missing in the harness copy of %s: %s' % (path, old)
            head = head.replace(old, new)
    return head + E2E


PARTS = (('rules', unit_script, 'starter run rules ok'), ('service', service_script, 'starter run service ok'), ('repository', e2e_script, 'starter run repository ok'))

MUTANTS = {
    'a save with a settled run id is a starter': {RULES: [('if type(checkpoint) ~= "table" or checkpoint.lastSettledRunId ~= nil then return false end', 'if type(checkpoint) ~= "table" then return false end')]},
    'the settled-run ledger is ignored': {RULES: [('if profile.settledRuns ~= nil and (type(profile.settledRuns) ~= "table" or #profile.settledRuns > 0) then return false end', '')]},
    'a save that hatched an egg is a starter': {RULES: [('if type(op) ~= "table" or op.kind == "run" or op.kind == "chest_claim" then return false end', 'if type(op) ~= "table" then return false end'),
                                                         ('if Rules.hatchedEggs(profile) > 0 or Rules.waitingEggs(profile) > 0 or count(profile.eggNests) > 0 then return false end', 'if count(profile.eggNests) > 0 then return false end')]},
    'a save with waiting eggs is a starter': {RULES: [('if Rules.hatchedEggs(profile) > 0 or Rules.waitingEggs(profile) > 0 or count(profile.eggNests) > 0 then return false end', 'if Rules.hatchedEggs(profile) > 0 or count(profile.eggNests) > 0 then return false end')]},
    'a save with account XP is a starter': {RULES: [('(type(progress.accountXP) == "number" and progress.accountXP > 0)', 'false')]},
    'an unreadable save is a starter': {RULES: [('    if type(profile.recentOperations) ~= "table" then return false end\n', '    if type(profile.recentOperations) ~= "table" then return true end\n')]},
    'an empty run gets the floor': {RULES: [('if whole < 1 or type(minEggs) ~= "number" or minEggs ~= minEggs then return whole end', 'if type(minEggs) ~= "number" or minEggs ~= minEggs then return whole end')]},
    'the floor lowers a bigger run': {RULES: [('return math.max(whole, math.floor(minEggs))', 'return math.floor(minEggs)')]},
    'the floor is not applied': {RULES: [('return math.max(whole, math.floor(minEggs))', 'return whole')]},
    'the starter safe eggs stay at two': {RULES: [('return math.max(safeLeft, math.floor(starterSafe))', 'return safeLeft')]},
    'the auto start repeats in the same join': {RULES: [('s.started ~= true and s.runState == "Sanctuary"', 's.runState == "Sanctuary"')]},
    'the auto start ignores the flag': {RULES: [('return s.enabled == true and s.starter == true and', 'return s.starter == true and')]},
    'the auto start does not wait for the dinosaur': {RULES: [('s.runState == "Sanctuary" and s.attached == true', 's.runState == "Sanctuary"')]},
    'the card shows before three eggs': {RULES: [('s.cardEggs >= 1 and s.eggs >= s.cardEggs', 's.cardEggs >= 1 and s.eggs >= 1')]},
    'the card shows again in the same run': {RULES: [('if type(s) ~= "table" or s.starter ~= true or s.shown == true or s.runState ~= "Active" then return false end', 'if type(s) ~= "table" or s.starter ~= true or s.runState ~= "Active" then return false end')]},
    'the card shows for a veteran': {RULES: [('if type(s) ~= "table" or s.starter ~= true or s.shown == true or s.runState ~= "Active" then return false end', 'if type(s) ~= "table" or s.shown == true or s.runState ~= "Active" then return false end')]},
    'Back home hides for a veteran': {RULES: [('return starter == true and hasEggs == true', 'return hasEggs == true')]},
    'run again shows while eggs are left': {RULES: [('s.eggsLeft <= 0 and type(s.copies) == "number"', 'type(s.copies) == "number"')]},
    'run again shows twice': {RULES: [('s.settled ~= true or s.shown == true then return false end', 's.settled ~= true then return false end')]},
    'the card title has a hand-typed number': {COPY: [('return string.format("You found %s!", plural(math.max(1, math.floor(eggs)), "egg", "eggs"))', 'return "You found 3 eggs!"')]},
    'the run again words are rule text': {COPY: [('Copy.starterRunAgain = "Run again to find new dinos!"', 'Copy.starterRunAgain = "Start another run to catch more eggs and hatch new dinosaurs"')]},
    'every run_end says starter': {TELEMETRY: [('starter = if input.starter == true then true else nil,', 'starter = true,')]},
    'the starter field never reaches the log line': {TELEMETRY: [('"crystals", "starter", "total_s"', '"crystals", "total_s"')]},
    'the service runs with the flag off': {SERVICE: [('    if not enabled() then return end\n', '')]},
    'the service starts a veteran': {SERVICE: [('        return PrivateState.get(player, "StarterRun") == 1\n', '        return true\n')]},
    'the service starts a run on every hub visit': {SERVICE: [('                        autoStarted[player] = true -- once per join', '                        -- once per join')]},
    'the service asks forever': {SERVICE: [('StarterRunService.TrySeconds = 90', 'StarterRunService.TrySeconds = 1e9')]},
    'a throwing run start kills the thread loudly': {SERVICE: [('local ok, began = pcall(RunLifecycle.requestStart, player)', 'local ok, began = true, RunLifecycle.requestStart(player)')]},
    'a refused start counts as started': {SERVICE: [('if ok and began == true then', 'if ok then')]},
    'the settlement gives the floor with the flag off': {EGGS: [('local starter = Config.StarterRunEnabled == true and FtueRules.starterQualifies(cached)', 'local starter = FtueRules.starterQualifies(cached)')]},
    'the settlement gives the floor to every save': {EGGS: [('local starter = Config.StarterRunEnabled == true and FtueRules.starterQualifies(cached)', 'local starter = Config.StarterRunEnabled == true')]},
    'the settlement never gives the floor': {EGGS: [('        eggCount = math.min(Config.RunEggMaxPerRun, FtueRules.starterEggFloor(caughtEggs, Config.StarterRunMinEggs))\n', '')]},
    'the stored save is not checked again': {EGGS: [('local floorHolds = not starter or FtueRules.starterQualifies(profileValue)', 'local floorHolds = true')]},
    'the starter eggs can be Cracked': {EGGS: [('    if starter then safeLeft = FtueRules.starterSafeEggs(safeLeft, Config.StarterRunSafeEggs) end', '')]},
    'the run is not marked as the starter run': {EGGS: [('        outcome.eggCount, outcome.starter = eggCount, true\n', '        outcome.eggCount = eggCount\n'),
                                                         ('if starter then outcome.eggCount, outcome.starter = if floorHolds then eggCount else caughtEggs, if floorHolds then true else nil end', 'if starter then outcome.eggCount = if floorHolds then eggCount else caughtEggs end')]},
    'Run Complete shows one egg for three': {EGGS: [('        if committedOutcome.starter == true and (committedOutcome.eggCount or 0) > caughtEggs then player:SetAttribute("LastRunCatchScore", committedOutcome.eggCount) end\n', '')]},
    'the floor also raises crystals and XP': {EGGS: [('    local caughtEggs = eggCount\n', '    local caughtEggs = eggCount\n    if Config.StarterRunEnabled == true and FtueRules.starterQualifies(cached) and eggCount >= 1 then outcome = RewardMath.computeRunReward(math.max(catchScore, Config.StarterRunMinEggs), runSeconds) nestsEarned = outcome.nestCount outcome.crystalBox = 0 end\n')]},
    'the starter value is sent with the flag off': {REPO: [('if Config.StarterRunEnabled == true then PrivateState.set(player, "StarterRun",', 'if true then PrivateState.set(player, "StarterRun",')]},
    'the starter value never goes back to 0': {REPO: [('PrivateState.set(player, "StarterRun", if FtueRules.starterQualifies(profile) then 1 else 0)', 'PrivateState.set(player, "StarterRun", 1)')]},
    'a starter flag is stored in the save': {EGGS: [('            recordSettledRun(profileValue, runId)\n', '            recordSettledRun(profileValue, runId)\n            if starter then profileValue.starterRunDone = true end\n')]},
}

SOURCE_MUTANTS = {
    'the flag is on in the source': (CONFIG, 'StarterRunEnabled = false,', 'StarterRunEnabled = true,'),
    'the card needs five eggs': (CONFIG, 'StarterRunEggs = 3,', 'StarterRunEggs = 5,'),
    'the normal safe-egg number changed': ('src/shared/ProgressionConfig.luau', 'SafeEggs=2,', 'SafeEggs=3,'),
    'the server never starts the service': ('src/server/Bootstrap.server.luau', 'require(script.Parent.StarterRunService).start()', ''),
    'the starter value is a public Player attribute': ('src/shared/PrivateStateCore.luau', '"StarterRun", -- BD-1163', '-- BD-1163'),
    'the default profile does not pin the flag off': (PROFILES, '_flag_off("StarterRunEnabled",', '_flag_off("StarterRunEnabledX",'),
    'the playtest profile does not switch it on': (PROFILES, 'Rule("StarterRunEnabled", "set", True,', 'Rule("StarterRunEnabled", "set", False,'),
    'the flag is missing from the rehearsal list': (PROFILES, '("StarterRunEnabled", "BD-1163', '("StarterRunEnabledX", "BD-1163'),
    'the client ignores the flag': (CLIENT, 'if not enabled() or attached then return end', 'if attached then return end'),
    'Run Complete hides Back home with the flag off': (CLIENT, 'if not enabled() or not latched then return "normal" end', 'if not latched then return "normal" end'),
    'the client decides the card by itself': (CLIENT, 'if Rules.starterCardNow({starter = latched and PrivateState.num("StarterRun") == 1,', 'if (character:GetAttribute("CatchScore") or 0) >= 3 and ({starter = latched and PrivateState.num("StarterRun") == 1,'),
    'the card button asks for a confirm': (CLIENT, 'if current and current:GetAttribute("RunState") == "Active" then d.endRun:FireServer() d.notify("Going home...", C.gold) end', 'd.open("exit")'),
    'the card button sends an argument': (CLIENT, 'd.endRun:FireServer() ', 'd.endRun:FireServer(true) '),
    'the card writes its own words': (CLIENT, 'd.button(body, Copy.starterCardButton,', 'd.button(body, "Finish the starter run and bank eggs",'),
    'the welcome lecture still opens for a starter': (CLIENT, '    d.markTutorialSeen() -- no lecture before the first run', '    -- no lecture before the first run'),
    'run again has its own words': (CLIENT, 'd.notify(Copy.starterRunAgain, Theme.Colors.gold,', 'd.notify("Play again!", Theme.Colors.gold,'),
    'SmallScreens does not attach the card': (SCREENS, 'require(script.Parent.StarterRunClient).attach(d, Screens)', ''),
    'the starter screen is not a screen name': (SCREENS, 'tutorial = true, starter = true}', 'tutorial = true}'),
    'the starter screen is never drawn': (SCREENS, 'if name=="starter" then require(script.Parent.StarterRunClient).render()', 'if name=="starter" then'),
    'Run Complete always shows Back home': (RUN_COMPLETE, 'if mode == "normal" then d.button(body, "Back home",', 'if true then d.button(body, "Back home",'),
    'Run Complete does not ask the starter module': (RUN_COMPLETE, 'local mode = require(script.Parent.StarterRunClient).resultsMode(d.hasEggs)', 'local mode = "normal"'),
}


def check_sources(overrides=None):
    """overrides: {path: source} for a source mutant. Returns the first problem or None."""
    def src(path):
        if overrides and path in overrides:
            return overrides[path]
        return read(path)
    config = src(CONFIG)
    if config.count('    StarterRunEnabled = false,') != 1:
        return 'the flag must be false in source'
    for needle in ('    StarterRunEggs = 3, -- PROVISIONAL', '    StarterRunMinEggs = 3, -- PROVISIONAL', '    StarterRunSafeEggs = 3, -- PROVISIONAL'):
        if config.count(needle) != 1:
            return 'Config lost a PROVISIONAL starter number: ' + needle.strip()
    if src('src/shared/ProgressionConfig.luau').count('SafeEggs=2,') != 1 or 'Rules.SafeEggs = 2 ' not in src(RULES):
        return 'the normal safe-egg rule (2) must stay as it is: the default build is unchanged'
    prof = src(PROFILES)
    for needle in ('_flag_off("StarterRunEnabled",', 'Rule("StarterRunEnabled", "set", True,', '("StarterRunEnabled", "BD-1163'):
        if needle not in prof:
            return 'release_profiles lost: ' + needle
    if src('src/server/Bootstrap.server.luau').count('require(script.Parent.StarterRunService).start()') != 1:
        return 'Bootstrap (server) starts the service with one line'
    if 'StarterRun' in src('src/client/Bootstrap.client.luau'):
        return 'the client Bootstrap is not touched (the card hangs on SmallScreens)'
    if '"StarterRun", -- BD-1163' not in src('src/shared/PrivateStateCore.luau'):
        return 'StarterRun is an owner-only (PRIVATE) value'
    service = src(SERVICE)
    service_code = '\n'.join(line for line in service.splitlines() if not line.strip().startswith('--'))
    for word in ('RemoteEvent', 'RemoteFunction', 'UpdateAsync', 'SetAttribute', 'FireClient', 'print(', 'UserId', '.Name', 'while true'):
        if word in service_code:
            return 'StarterRunService has no remote, no write, no attribute, no print, no id, no endless loop: ' + word
    for needle in ('pcall(RunLifecycle.requestStart, player)', 'while os.clock() < deadline and player.Parent ~= nil and player.Character == character do', 'FtueRules.starterAutoStart('):
        if needle not in service:
            return 'StarterRunService lost: ' + needle
    eggs = src(EGGS)
    if eggs.count('Config.StarterRunEnabled == true') != 1 or eggs.count('FtueRules.safeEggsLeft(cached)') != 1:
        return 'ProfileEggs reads the flag once, next to the unchanged safe-egg rule'
    repo = src(REPO)
    if repo.count('Config.StarterRunEnabled == true') != 1:
        return 'ProfileRepository reads the flag once'
    if 'tarter' in repo.split('local function isValidProfile', 1)[1].split('\nend\n', 1)[0] or 'tarter' in repo.split('local function defaultProfile', 1)[1].split('\nend\n', 1)[0]:
        return 'no starter field in the stored profile'
    client = src(CLIENT)
    code = '\n'.join(line for line in client.splitlines() if line.strip() and not line.strip().startswith('--'))
    for needle in ('if not enabled() or attached then return end', 'if not enabled() or not latched then return "normal" end',
                   'if Rules.starterCardNow({starter = latched and PrivateState.num("StarterRun") == 1,', 'cardEggs = Config.StarterRunEggs})',
                   'if Rules.starterRunAgainNow({starter = latched, settled = starterRunId ~= nil, shown = againShown,',
                   'd.notify(Copy.starterRunAgain, Theme.Colors.gold,', 'd.markTutorialSeen() -- no lecture before the first run',
                   'd.label(body, Copy.starterCardTitle(', 'd.button(body, Copy.starterCardButton,',
                   'if current and current:GetAttribute("RunState") == "Active" then d.endRun:FireServer() d.notify("Going home...", C.gold) end',
                   'Rules.starterOnlyOpenEggs(true, hasEggs)'):
        if needle not in client:
            return 'StarterRunClient lost: ' + needle
    if code.count('FireServer') != 1 or 'd.open("exit")' in code:
        return 'the card button ends the run directly: one FireServer, no confirm screen'
    if any(word in code for word in ('Instance.new', 'InvokeServer', 'rbxassetid', 'while true')):
        return 'StarterRunClient builds no instances of its own, has no asset id and no endless loop'
    screens = src(SCREENS)
    for needle in ('tutorial = true, starter = true}', 'require(script.Parent.StarterRunClient).attach(d, Screens)',
                   'if name=="starter" then require(script.Parent.StarterRunClient).render()', 'Screens.shown = name',
                   'button(body,"How to play",0,70,400,76,C.gold,function() open("tutorial") end)'):
        if needle not in screens:
            return 'SmallScreens lost: ' + needle
    rc = src(RUN_COMPLETE)
    for needle in ('local mode = require(script.Parent.StarterRunClient).resultsMode(d.hasEggs)', 'if mode == "normal" then d.button(body, "Back home",',
                   'if d.hasEggs then d.button(body, "OPEN EGGS", if mode == "normal" then 424 else 212, 348, if mode == "normal" then 370 else 400, 48, C.gold, d.openEggs) end'):
        if needle not in rc:
            return 'RunComplete lost: ' + needle
    return None


def run(runner, replacements=None):
    """Runs the three parts. Returns (all passed, output)."""
    out = ''
    for name, build, marker in PARTS:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / ('starter_run_%s.luau' % name)
            path.write_text(build(replacements), encoding='utf-8')
            result = subprocess.run([runner, str(path)], capture_output=True, text=True)
        out += result.stdout + result.stderr
        if result.returncode != 0 or marker not in result.stdout:
            return False, out
    return True, out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    problem = check_sources()
    if problem:
        print('FAIL', problem)
        sys.exit(1)
    ok, out = run(args.runner)
    print(out, end='')
    if not ok:
        sys.exit(1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            passed, _ = run(args.runner, replacements)
            assert not passed, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
        for name, (path, old, new) in SOURCE_MUTANTS.items():
            source = read(path)
            assert old in source, 'mutant target missing in %s: %s' % (path, old)
            assert check_sources({path: source.replace(old, new)}) is not None, 'SOURCE MUTANT SURVIVED: ' + name
            print('  source mutant caught: ' + name)
    print('Starter run passed: who is a starter, egg floor exactly once (retry, outage, lost acknowledgement, reconnect, stale cache), safe eggs, '
          'auto-start once per join, card and Run Complete rules, words, telemetry field, flag off unchanged, wiring, %d mutants caught'
          % (0 if args.no_mutants else len(MUTANTS) + len(SOURCE_MUTANTS)))


if __name__ == '__main__':
    main()
