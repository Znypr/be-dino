#!/usr/bin/env python3
"""BD-1199 (docs/239, docs/235): PLAY AGAIN after the last egg and the gentle run streak (Config.PlayAgainEnabled).

Runs with the pinned Luau runtime:
  1. the pure rules of src/shared/PlayAgain.luau (which buttons the hatch end shows, their size and colour contrast, the streak by the
     window, the crystal table, who qualifies for the bonus, the soft words) - flag off = the old buttons for every case;
  2. the real src/server/RunStreakService.luau on a mocked PrivateState: the streak counts 1..5 and stops at 5, a run later than the window
     starts again at 1 (quietly), a new Player object (leave and rejoin) starts at 1, the bonus is paid once per run id;
  3. the real ProfileRepository on the verify_rewards harness (mocked DataStore): flag off = the settlement is byte for byte what it was
     (same outcome, same crystals, RunStreakService never loaded, no owner-only streak value); flag on = the bonus joins the run crystals in the
     ONE settlement, a replay of the same run id pays nothing more, a failing service never blocks a settlement, a run that ends at once earns none;
  4. static wiring: the flag is false in source and pinned off / on / rehearsed in the profiles, PLAY AGAIN goes through the existing onAgain
     path (Bootstrap fires only the normal RequestStartRun while the dino is in the Sanctuary), HOME starts nothing, nobody sends a streak or a
     bonus from the client, no timer and no auto-start, Reduce Motion (no tween, no wait in the new files), the new owner-only names.
Then each defect is put back (mutants). NOT Studio or phone evidence.
Usage: python tools/verify_play_again.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_rewards  # noqa: E402

RULES = 'src/shared/PlayAgain.luau'
SERVICE = 'src/server/RunStreakService.luau'
REPO = 'src/server/ProfileRepository.luau'
EGGS = 'src/server/ProfileEggs.luau'
LIFE = 'src/server/RunLifecycle.luau'
CUE = 'src/client/PlayAgainCue.luau'
HATCH = 'src/client/HatchSequence.luau'
BOOT = 'src/client/Bootstrap.client.luau'
COMPLETE = 'src/client/RunComplete.luau'
CORE = 'src/shared/PrivateStateCore.luau'
COPY = 'src/shared/FtueP1.luau'
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
local W, Copy = PlayAgainRules, FtueP1
-- flag off (or anything but the end of a batch): the buttons are exactly what FtueP1 said
for _, failed in {false, true} do
    for _, remaining in {0, 1, 5} do
        local base = Copy.hatchButtons(failed, remaining)
        local off = W.endKinds(false, failed, remaining, base)
        assert(table.concat(off, ",") == table.concat(base, ","), "flag off: the old buttons")
        local on = W.endKinds(true, failed, remaining, base)
        if not failed and remaining == 0 then
            assert(table.concat(on, ",") == "play,home", "the end of a batch: PLAY AGAIN + HOME")
        else
            assert(table.concat(on, ",") == table.concat(base, ","), "a splat or an egg with more to come keeps its buttons")
        end
    end
end
-- sizes and colours: a big green primary, a small grey one, both a thumb target; dark ink readable on both (docs/72 contrast 4.5)
local play, home = W.Buttons.play, W.Buttons.home
assert(play.h >= 48 and home.h >= W.MinTouchHeight and play.w > home.w and play.h > home.h and play.textSize > home.textSize, "big primary, small secondary")
assert(W.MinTouchHeight == 48 and play.h >= 48, "48 px or more")
assert(play.fill[2] > play.fill[1] + 80 and play.fill[2] > play.fill[3] + 80, "green")
assert(math.abs(home.fill[1] - home.fill[2]) < 20 and math.abs(home.fill[2] - home.fill[3]) < 20, "grey")
assert(Copy.contrast(play.fill, Copy.ButtonTextColor) >= 4.5 and Copy.contrast(home.fill, Copy.ButtonTextColor) >= 4.5, "readable")
assert(#W.ButtonText.play <= 10 and #W.ButtonText.home <= 10 and W.ButtonText.play == "PLAY AGAIN" and W.ButtonText.home == "HOME", "kid words")
local xs, total = W.layout({"play", "home"})
assert(xs[1] == 0 and xs[2] == play.w + W.ButtonGap and total == play.w + W.ButtonGap + home.w and total <= 824 - 40, "the row fits the 824 px card")
local xs2, total2 = W.layout({"done", "again"})
assert(xs2[1] == 0 and xs2[2] == 246 and total2 == 230 * 2 + 16, "the other rows keep their 230 px buttons")
-- the streak by the window (server clock)
local WIN = 120
assert(W.nextStreak(0, nil, 1000, WIN) == 1 and W.nextStreak(nil, nil, 1000, WIN) == 1 and W.nextStreak(0, 1000, 1010, WIN) == 1, "the first run")
assert(W.nextStreak(1, 1000, 1000 + WIN, WIN) == 2, "exactly at the window edge still counts")
assert(W.nextStreak(1, 1000, 1000 + WIN + 0.01, WIN) == 1, "one moment later starts again, quietly")
assert(W.nextStreak(2, 1000, 1010, WIN) == 3 and W.nextStreak(4, 1000, 1010, WIN) == 5 and W.nextStreak(5, 1000, 1010, WIN) == 5 and W.nextStreak(99, 1000, 1010, WIN) == 5, "capped at 5")
assert(W.nextStreak(3, 1000, 900, WIN) == 1, "a clock that went back starts again")
assert(W.nextStreak("3", 1000, 1010, WIN) == 1 and W.nextStreak(3, "1000", 1010, WIN) == 1 and W.nextStreak(3, 1000, 1010, "120") == 1 and W.nextStreak(3, 0/0, 1010, WIN) == 1, "bad input starts at 1")
-- the crystal table (PROVISIONAL numbers live in Config)
local T = Config.RunStreakCrystals
assert(#T == 5 and T[1] == 0 and T[2] == 5 and T[3] == 10 and T[4] == 15 and T[5] == 20 and Config.RunStreakWindowSeconds == 120, "provisional table")
for i = 1, 5 do assert(W.crystalsFor(i, T) == T[i]) end
assert(W.crystalsFor(9, T) == 20 and W.crystalsFor(0, T) == 0 and W.crystalsFor(-3, T) == 0, "bounded")
assert(W.crystalsFor(2, nil) == 0 and W.crystalsFor("2", T) == 0 and W.crystalsFor(2, {-5, -5}) == 0 and W.crystalsFor(0/0, T) == 0, "bad input pays nothing")
local total_ = 0 for i = 1, 5 do total_ += W.crystalsFor(i, T) end
assert(total_ == 50, "a full streak of five runs adds 50 crystals, about one 12-egg run (30) and a half")
-- who earns the bonus
assert(W.qualifies(1, 60, 60) and W.qualifies(12, 300, 60) and not W.qualifies(0, 300, 60) and not W.qualifies(5, 59.9, 60) and not W.qualifies("5", 300, 60) and not W.qualifies(5, nil, 60), "a real run")
-- the soft words
assert(W.text(1) == nil and W.text(0) == nil and W.text(nil) == nil and W.text(0/0) == nil and W.text("3") == nil, "no line for a streak of 1")
assert(W.text(2) == "Run streak 2!" and W.text(3) == "Run streak 3!" and W.text(5) == "Run streak 5!" and W.text(9) == "Run streak 5!")
for i = 2, 5 do
    local t = W.text(i)
    assert(#t <= 14 and not t:find("[Ll]ost") and not t:find("[Bb]reak") and not t:find("[Hh]urry") and not t:find("%d+ ?s") and not t:find("!!"), "calm words: " .. t)
end
print("play again rules ok")
'''

SERVICE_TEST = r'''
local function world(sets)
    local game = {GetService = function() return {Shared = {Config = "Config", PlayAgain = "PlayAgain"}} end}
    local PrivateState = {set = function(p, name, value) table.insert(sets, {p = p, name = name, value = value}) end}
    local script = {Parent = {PrivateState = "PS"}}
    local require = function(k) if k == "Config" then return Config elseif k == "PlayAgain" then return W elseif k == "PS" then return PrivateState end error(k) end
    local setmetatable = setmetatable
    return @@SERVICE@@
end
local sets = {}
local S = world(sets)
local p = {}
local function last(name) for i = #sets, 1, -1 do if sets[i].p == p and sets[i].name == name then return sets[i].value end end return nil end
-- run 1, then 2, 3, 4, 5, 6 in the window: 1..5 and it stays at 5
local t = 1000
for i = 1, 6 do
    local want = math.min(i, 5)
    assert(S.onBegin(p, "run" .. i, t) == want and last("RunStreak") == want, "streak " .. i)
    assert(S.bonusFor(p, "run" .. i, 12, 300) == Config.RunStreakCrystals[want], "bonus of step " .. want)
    t += 300
    S.onEnd(p, "run" .. i, t)
    assert(last("LastRunStreak") == want and last("LastRunStreakCrystals") == 0, "Run Complete sees the streak, the bonus follows the settlement")
    S.committed(p, "run" .. i, S.bonusFor(p, "run" .. i, 12, 300))
    assert(S.bonusFor(p, "run" .. i, 12, 300) == 0, "paid once: asking again pays nothing")
    t += Config.RunStreakWindowSeconds - 1 -- play again inside the window
end
-- a run that ends at once (no eggs, or too short) earns nothing but does not break the streak count
assert(S.onBegin(p, "short", t) == 5 and S.bonusFor(p, "short", 0, 300) == 0 and S.bonusFor(p, "short", 3, 5) == 0 and S.bonusFor(p, "short", 3, 300) == 20)
t += 5
S.onEnd(p, "short", t)
-- waiting longer than the window starts again at 1, quietly (the line is simply not shown)
t += Config.RunStreakWindowSeconds + 1
assert(S.onBegin(p, "late", t) == 1 and last("RunStreak") == 1 and S.bonusFor(p, "late", 12, 300) == 0, "late: step 1 pays 0")
-- the number the client reads never tells it a loss
for _, e in sets do assert(e.name == "RunStreak" or e.name == "LastRunStreak" or e.name == "LastRunStreakCrystals", "only the three owner-only names: " .. e.name) end
-- leaving the game (a new Player object) starts again at 1
local q = {}
assert(S.onBegin(q, "q1", t) == 1 and S.streakOf(q) == 1 and S.streakOf({}) == 0, "new player object: 1")
-- a run id the service never saw, a bad commit, other players cannot be paid
assert(S.bonusFor(p, "never-seen", 12, 300) == 0 and S.bonusFor({}, "run1", 12, 300) == 0)
S.committed({}, "x", 5)
-- the memory per player is bounded
for i = 1, 40 do S.onBegin(q, "many" .. i, t) end
print("play again service ok")
'''

E2E_PRELUDE = '''local fakeNow=1800000000
local realOs=os
local os=setmetatable({time=function() return fakeNow end},{__index=realOs})
'''

E2E = r'''
local function runBonus(u, id, catches, seconds) return Repository.commitRunSettlement(u, id, catches, nil, seconds) end
local function crystals(u) return data[key(u)].progression.crystals end
-- flag off (the default build): the settlement is the old one, the service is never even required, nothing owner-only is set.
GameConfig.PlayAgainEnabled = false
local a = user(92001) assert(Repository.load(a))
local ok, base, status = runBonus(a, "pa-off-1", 12, 300)
assert(ok and status == "committed" and base.crystals == 30 and crystals(a) == 30, "flag off: 12 eggs = 30 crystals, nothing extra")
assert(StreakLoads.n == 0, "flag off: RunStreakService never loaded")
assert(a.attrs.RunStreak == nil and a.attrs.LastRunStreak == nil and a.attrs.LastRunStreakCrystals == nil, "flag off: no streak values")
assert(base.streakCrystals == nil, "the stored outcome has no new field")
-- even with a service that would pay, the flag off pays nothing
StreakReal.onBegin(a, "pa-off-2", 100) StreakReal.onBegin(a, "pa-off-2b", 200)
local ok2, base2 = runBonus(a, "pa-off-2", 12, 300)
assert(ok2 and base2.crystals == 30 and crystals(a) == 60, "flag off: no bonus even when a streak exists in memory")
-- flag on
GameConfig.PlayAgainEnabled = true
local u = user(92002) assert(Repository.load(u))
local t = 5000
local expect = 0
for i = 1, 6 do
    local id = "pa-" .. i
    local streak = StreakReal.onBegin(u, id, t)
    assert(streak == math.min(i, 5))
    t += 300
    StreakReal.onEnd(u, id, t)
    local okc, outcome, st = runBonus(u, id, 12, 100)
    local bonus = GameConfig.RunStreakCrystals[streak]
    assert(okc and st == "committed" and outcome.crystals == 30 + bonus, "run " .. i .. ": 30 + bonus " .. bonus .. " got " .. tostring(outcome.crystals))
    expect += 30 + bonus
    assert(crystals(u) == expect, "stored crystals follow")
    assert(u.attrs.LastRunStreakCrystals == bonus and u.attrs.LastRunStreak == streak, "Run Complete numbers")
    -- the same run settles again (lost acknowledgement, retry, a client asking twice): exactly once
    local okd, dup, std = runBonus(u, id, 12, 100)
    assert(okd and std == "duplicate" and crystals(u) == expect, "a replay of the same run id pays nothing more")
    assert(u.attrs.LastRunStreakCrystals == bonus, "a replay does not change what Run Complete shows")
    t += 60
end
-- waiting longer than the window: back to 1, no bonus
t += GameConfig.RunStreakWindowSeconds + 1
assert(StreakReal.onBegin(u, "pa-late", t) == 1)
local okl, late = runBonus(u, "pa-late", 12, 100)
assert(okl and late.crystals == 30 and crystals(u) == expect + 30, "a late run is a plain run")
-- a run that ends at once earns no streak bonus, however high the streak
local v = user(92003) assert(Repository.load(v))
local tv = 9000
for i = 1, 4 do StreakReal.onBegin(v, "pv-" .. i, tv) tv += 10 StreakReal.onEnd(v, "pv-" .. i, tv) end
local okz, zero = runBonus(v, "pv-4", 0, 3)
assert(okz and zero.crystals == 0 and crystals(v) == 0, "no eggs, no bonus")
local oks, short = runBonus(v, "pv-3", 3, 10)
assert(oks and short.crystals == Rewards.runCrystals(3), "a 10 second run with eggs: only its own crystals")
-- the client cannot claim: the settlement takes no streak argument and the only source is the service memory of this run id
local w = user(92004) assert(Repository.load(w))
local okw, forged = Repository.commitRunSettlement(w, "pa-forged", 12, nil, 300, nil, nil)
assert(okw and forged.crystals == 30, "a run id the server never started pays nothing extra")
w.attrs.RunStreak = 5 w.attrs.LastRunStreak = 5 w.attrs.LastRunStreakCrystals = 20
local okf, forged2 = runBonus(w, "pa-forged-2", 12, 300)
assert(okf and forged2.crystals == 30, "values on the player never change what is paid")
-- a failing or missing service never blocks the settlement
local brokenFlag = StreakLoads.broken
StreakLoads.broken = true
local x = user(92005) assert(Repository.load(x))
local okx, plain, stx = runBonus(x, "pa-broken", 12, 300)
assert(okx and stx == "committed" and plain.crystals == 30 and crystals(x) == 30, "a broken streak service: the run still settles, no bonus")
StreakLoads.broken = brokenFlag
-- nothing about the streak is stored in the save
local function has(tbl, word)
    if type(tbl) ~= "table" then return false end
    for k, v in tbl do if (type(k) == "string" and k:lower():find(word)) or has(v, word) then return true end end
    return false
end
assert(not has(data[key(u)], "streak") and not has(data[key(a)], "streak"), "nothing stored: session-only")
GameConfig.PlayAgainEnabled = false
print("play again repository ok")
'''


def unit_script(replacements=None):
    cfg = module('src/shared/Config.luau', replacements)
    return ('local Config=' + cfg + '\nlocal PlayAgainRules=' + module(RULES, replacements) + '\nlocal FtueP1=' + module(COPY, replacements) + '\n' + UNIT)


def service_script(replacements=None):
    s = 'local Config=' + module('src/shared/Config.luau', replacements) + '\nlocal W=' + module(RULES, replacements) + '\n'
    return s + SERVICE_TEST.replace('@@SERVICE@@', module(SERVICE, replacements))


def e2e_script(replacements=None):
    s = verify_rewards.script()
    head = s[:s.index('------------------------------------------------------------------ RewardMath')]
    for old, new in (replacements or {}).get(REPO, []) + (replacements or {}).get(EGGS, []):
        # the harness inlines the repository module; the ProfileEggs part is a separate module required by it in the real game, so a
        # mutant of ProfileEggs is applied through the harness copy when it carries the text, else the mutant is rejected
        assert old in head, 'mutant target missing in the harness copy: %s' % old
        head = head.replace(old, new)
    marker = 'local script={Parent={RewardMath="Rewards"'
    assert head.count(marker) == 1
    real = ('local StreakLoads={n=0,broken=false}\n'
            'local PlayAgainRules=' + module(RULES, replacements) + '\n'
            'local StreakReal=(function()\n'
            'local game={GetService=function() return {Shared={Config="Config",PlayAgain="PlayAgain"}} end}\n'
            'local script={Parent={PrivateState="PS"}}\n'
            'local require=function(k) if k=="Config" then return GameConfig elseif k=="PlayAgain" then return PlayAgainRules elseif k=="PS" then return PrivateStateStub end error(k) end\n'
            'local setmetatable=setmetatable\n' + read(SERVICE).replace('return Service', 'return Service') + '\nend)()\n')
    for old, new in (replacements or {}).get(SERVICE, []):
        assert old in real, 'mutant target missing in the service: %s' % old
        real = real.replace(old, new)
    head = head.replace(marker, real + marker)
    head = head.replace('PrivateState="PrivateState",', 'PrivateState="PrivateState",RunStreakService="RunStreakService",', 1)
    key = ' if id=="PrivateState" then return PrivateStateStub end\n'
    assert head.count(key) == 1
    head = head.replace(key, ' if id=="RunStreakService" then StreakLoads.n+=1 if StreakLoads.broken then error("broken streak service") end return StreakReal end\n' + key)
    return E2E_PRELUDE + head + E2E


PARTS = (('rules', unit_script, 'play again rules ok'), ('service', service_script, 'play again service ok'), ('repository', e2e_script, 'play again repository ok'))

MUTANTS = {
    'the end buttons change with the flag off': {RULES: [('if enabled and not failed and remaining <= 0 then return {"play", "home"} end', 'if not failed and remaining <= 0 then return {"play", "home"} end')]},
    'a splat gets PLAY AGAIN': {RULES: [('if enabled and not failed and remaining <= 0', 'if enabled and remaining <= 0')]},
    'an egg with more to come gets PLAY AGAIN': {RULES: [('if enabled and not failed and remaining <= 0', 'if enabled and not failed')]},
    'the primary button is small': {RULES: [('play = {w = 300, h = 64, textSize = 34', 'play = {w = 120, h = 40, textSize = 20')]},
    'the home button is below a thumb target': {RULES: [('home = {w = 150, h = 48', 'home = {w = 150, h = 30')]},
    'the home button is as big as play': {RULES: [('home = {w = 150, h = 48, textSize = 24', 'home = {w = 300, h = 64, textSize = 34')]},
    'the primary is not green': {RULES: [('fill = {93, 237, 31}}', 'fill = {237, 93, 31}}')]},
    'the grey button is too dark for its ink': {RULES: [('fill = {176, 181, 192}', 'fill = {40, 40, 50}')]},
    'the streak ignores the window': {RULES: [('if gap < 0 or gap > window then return 1 end', 'if gap < 0 then return 1 end')]},
    'the window edge is not included': {RULES: [('gap > window', 'gap >= window')]},
    'the streak is not capped': {RULES: [('return math.min(P.MaxStreak, math.floor(prev) + 1)', 'return math.floor(prev) + 1')]},
    'a streak starts at 0': {RULES: [('if prev < 1 then return 1 end', 'if prev < 1 then return 0 end')]},
    'a streak never resets on a bad clock': {RULES: [('if gap < 0 or gap > window then return 1 end', 'if gap > window then return 1 end')]},
    'the crystals table is unbounded': {RULES: [('local step = math.clamp(math.floor(streak), 1, P.MaxStreak)', 'local step = math.floor(streak)')]},
    'a run that ends at once earns the bonus': {RULES: [('return catchScore >= 1 and runSeconds >= minSeconds', 'return true')]},
    'the words are a warning': {RULES: [('"Run streak " .. tostring', '"You may lose your Run streak " .. tostring')]},
    'a streak of 1 gets a line': {RULES: [('streak < 2 then return nil end', 'streak < 1 then return nil end')]},
    'the table changes (not the owner numbers)': {'src/shared/Config.luau': [('RunStreakCrystals = {0, 5, 10, 15, 20}', 'RunStreakCrystals = {0, 50, 100, 150, 200}')]},
    'the service forgets the end of a run': {SERVICE: [('    m.lastEndAt = now\n', '')]},
    'the service pays a run twice': {SERVICE: [('    m.paid[runId] = true\n', '')]},
    'the service pays an unknown run': {SERVICE: [('    local streak = m.runs[runId]\n    if not streak then return 0 end\n', '    local streak = m.runs[runId] or 5\n')]},
    'the service pays a run that ends at once': {SERVICE: [('    if not Rules.qualifies(catchScore, runSeconds, Config.RunStreakMinRunSeconds) then return 0 end\n', '')]},
    'the service keeps the streak across a leave': {SERVICE: [('local memory: {[Player]: Memory} = setmetatable({}, {__mode = "k"}) :: any', 'local memory: {[Player]: Memory} = setmetatable({}, {__mode = "k"}) :: any\nlocal shared: Memory = {streak = 0, lastEndAt = nil, runs = {}, paid = {}}'), ('    local m = memory[player]\n    if not m then\n        m = {streak = 0, lastEndAt = nil, runs = {}, paid = {}}\n        memory[player] = m\n    end\n    return m', '    return shared')]},
    'the service tells the client a loss': {SERVICE: [('PrivateState.set(player, "LastRunStreakCrystals", 0)', 'PrivateState.set(player, "LastRunStreakCrystals", -1)')]},
}

SOURCE_MUTANTS = {
    'the flag is on in the source': (CONFIG, '    PlayAgainEnabled = false,', '    PlayAgainEnabled = true,'),
    'the default profile does not pin the flag off': (PROFILES, '_flag_off("PlayAgainEnabled",', '_flag_off("PlayAgainEnabledX",'),
    'the playtest profile does not switch it on': (PROFILES, 'Rule("PlayAgainEnabled", "set", True,', 'Rule("PlayAgainEnabled", "set", False,'),
    'the flag is missing from the rehearsal list': (PROFILES, '("PlayAgainEnabled", "BD-1199', '("PlayAgainEnabledX", "BD-1199'),
    'the playtest manifest forgets the flag': ('tools/release_playtest.py', '"PlayAgainEnabled",', ''),
    'the numbers lose their PROVISIONAL label': (CONFIG, 'RunStreakWindowSeconds = 120, -- PROVISIONAL', 'RunStreakWindowSeconds = 120, --'),
    'the table loses its PROVISIONAL label': (CONFIG, 'RunStreakCrystals = {0, 5, 10, 15, 20}, -- PROVISIONAL', 'RunStreakCrystals = {0, 5, 10, 15, 20}, --'),
    'PLAY AGAIN has its own remote': (HATCH, 'if a.onAgain then (a.onAgain :: (boolean?) -> ())() end', 'if a.onAgain then (a.onAgain :: (boolean?) -> ())() end startRemote:FireServer()'),
    'HOME starts a run': (HATCH, '(a.onAgain :: (boolean?) -> ())(false)', '(a.onAgain :: (boolean?) -> ())()'),
    'the hatch ignores the flag': (HATCH, 'if Config.PlayAgainEnabled == true and not autoNext then kinds', 'if not autoNext then kinds'),
    'PLAY AGAIN is not the same path as TRY AGAIN': (HATCH, 'if kind == "again" or kind == "play" then', 'if kind == "again" then'),
    'PLAY AGAIN starts by itself after a delay': (HATCH, 'if kind == "play" then playAction = act end', 'if kind == "play" then playAction = act task.delay(3, act) end'),
    'Bootstrap starts a run outside the Sanctuary': (BOOT, 'if go~=false and character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() end', 'if go~=false then startRun:FireServer() end'),
    'Bootstrap lets HOME start a run': (BOOT, 'if go~=false and character and', 'if character and'),
    'Bootstrap does not attach the cue': (BOOT, 'require(script.Parent.PlayAgainCue).attach(notify) -- BD-1199', ''),
    'the cue ignores the flag': (CUE, 'if Config.PlayAgainEnabled ~= true or attached then return end', 'if attached then return end'),
    'the cue sends the streak to the server': (CUE, 'if text then notify(text, Theme.Colors.gold) end', 'if text then notify(text, Theme.Colors.gold) game:GetService("ReplicatedStorage").BeDinoRemotes.RequestStartRun:FireServer(value) end'),
    'the cue animates': (CUE, 'local Cue = {}', 'local TweenService = game:GetService("TweenService")\nlocal Cue = {}'),
    'the settlement pays without the flag': (EGGS, 'if Config.PlayAgainEnabled == true then\n        local askedOk', 'if true then\n        local askedOk'),
    'the settlement takes the bonus from the client': (EGGS, 'runStreak().bonusFor(player, runId, catchScore, runSeconds)', 'runStreak().bonusFor(player, runId, catchScore, runSeconds) + (player:GetAttribute("LastRunStreakCrystals") or 0)'),
    'the settlement is not protected': (EGGS, 'local askedOk, asked = pcall(function() return runStreak().bonusFor(player, runId, catchScore, runSeconds) end)', 'local askedOk, asked = true, runStreak().bonusFor(player, runId, catchScore, runSeconds)'),
    'the bonus is added after the transaction': (EGGS, '        outcome.crystals += streakBonus\n', ''),
    'the run start does not check the flag': (LIFE, 'if Config.PlayAgainEnabled == true then pcall(function() require(script.Parent.RunStreakService).onBegin', 'if true then pcall(function() require(script.Parent.RunStreakService).onBegin'),
    'the run end does not tell the service': (LIFE, 'pcall(function() require(script.Parent.RunStreakService).onEnd(player, snapshot.runId, workspace:GetServerTimeNow()) end)', 'nil'),
    'the streak numbers are public': (CORE, '"RunStreak", "LastRunStreak", "LastRunStreakCrystals", --', '--'),
    'Run Complete ignores the flag': (COMPLETE, 'if Config.PlayAgainEnabled == true then Rules.text(d.num("LastRunStreak")) else nil', 'Rules.text(d.num("LastRunStreak"))'),
}


def check_sources(overrides=None):
    """overrides: {path: source} for a source mutant. Returns the first problem or None."""
    def src(path):
        if overrides and path in overrides:
            return overrides[path]
        return read(path)
    config = src(CONFIG)
    if config.count('    PlayAgainEnabled = false,') != 1:
        return 'the flag must be false in source'
    for name in ('RunStreakWindowSeconds', 'RunStreakCrystals', 'RunStreakMinRunSeconds'):
        line = [l for l in config.splitlines() if l.strip().startswith(name + ' =')]
        if len(line) != 1 or 'PROVISIONAL' not in line[0]:
            return name + ' must be one line labelled PROVISIONAL'
    if not re.search(r'RunStreakCrystals = \{0, 5, 10, 15, 20\}', config) or 'RunStreakWindowSeconds = 120,' not in config:
        return 'the owner-visible numbers: window 120 s, crystals 0/5/10/15/20'
    prof = src(PROFILES)
    for needle in ('_flag_off("PlayAgainEnabled",', 'Rule("PlayAgainEnabled", "set", True,', '("PlayAgainEnabled", "BD-1199'):
        if needle not in prof:
            return 'release_profiles lost: ' + needle
    if '"PlayAgainEnabled"' not in src('tools/release_playtest.py'):
        return 'the playtest manifest records PlayAgainEnabled'
    if 'PROVISIONAL' not in read_doc():
        return 'the doc labels the numbers PROVISIONAL'
    rules = src(RULES)
    cue = src(CUE)
    hatch = src(HATCH)
    boot = src(BOOT)
    eggs = src(EGGS)
    life = src(LIFE)
    complete = src(COMPLETE)
    # the new files have no motion, no wait, no remote of their own: Reduce Motion and the calm feel (docs/87)
    for name, text in (('PlayAgain', rules), ('PlayAgainCue', cue), ('RunStreakService', src(SERVICE))):
        code = '\n'.join(l for l in text.splitlines() if not l.strip().startswith('--'))
        for word in ('Tween', 'task.wait', 'task.delay', 'task.spawn', 'wait(', 'RunService', 'Heartbeat', 'os.clock', 'tick()', 'FireServer', 'InvokeServer', 'RemoteEvent', 'RemoteFunction', 'UpdateAsync', 'DataStore', 'GetServerTimeNow', 'Instance.new'):
            if word in code:
                return '%s has no motion, wait, remote, store or clock of its own: %s' % (name, word)
    if cue.count('if Config.PlayAgainEnabled ~= true or attached then return end') != 1 or 'PrivateState.onChanged("RunStreak"' not in cue or 'notify(text, Theme.Colors.gold)' not in cue:
        return 'the cue returns at once with the flag off and only shows the server number'
    if boot.count('require(script.Parent.PlayAgainCue).attach(notify)') != 1:
        return 'Bootstrap attaches the cue with one line'
    # PLAY AGAIN is the same path as TRY AGAIN: onAgain closes the party and fires the ONE normal start remote, only while the dino is in the Sanctuary
    for needle in ('if kind == "again" or kind == "play" then', '(a.onAgain :: (boolean?) -> ())()', 'elseif kind == "home" then', '(a.onAgain :: (boolean?) -> ())(false)',
                   'if Config.PlayAgainEnabled == true and not autoNext then kinds = PlayAgain.endKinds(true, failed, r.remaining, kinds) end', 'if kind == "play" then playAction = act end'):
        if needle not in hatch:
            return 'HatchSequence lost: ' + needle
    if any(w in hatch for w in ('FireServer', 'startRun', 'startRemote', 'RequestStartRun', 'InvokeServer')):
        return 'HatchSequence sends nothing itself: the start goes through Bootstrap onAgain'
    for word in ('task.delay(3', 'autoStart', 'countdown'):
        if word in hatch:
            return 'no timer or auto-start in HatchSequence: ' + word
    if 'onAgain=function(go) -- BD-371' not in boot or 'if go~=false and character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() end' not in boot:
        return 'Bootstrap onAgain starts the normal run only for PLAY AGAIN and only in the Sanctuary'
    if boot.count('startRun:FireServer()') != 4:
        return 'Bootstrap still has exactly the four existing start calls'
    # the server decides: the bonus is asked from the service memory, never from an argument or a client value
    for needle in ('    if Config.PlayAgainEnabled == true then\n        local askedOk', 'local askedOk, asked = pcall(function() return runStreak().bonusFor(player, runId, catchScore, runSeconds) end)', 'outcome.crystals += streakBonus',
                   'if Config.PlayAgainEnabled == true and not duplicate then pcall(function() runStreak().committed(player, runId, streakBonus) end) end'):
        if needle not in eggs:
            return 'ProfileEggs lost: ' + needle
    if 'GetAttribute' in eggs.split('local streakBonus = 0', 1)[1].split('local eggCount', 1)[0]:
        return 'the settlement never reads a client value for the bonus'
    if 'function ProfileRepository.commitRunSettlement(player: Player, runId: string, catchScore: number, eggEvents, runSeconds: number?, nestWeather: any?, maxAttempts: number?)' not in eggs:
        return 'commitRunSettlement keeps its signature: no streak argument'
    if life.count('Config.PlayAgainEnabled == true then pcall(function() require(script.Parent.RunStreakService).') != 2:
        return 'RunLifecycle: two flag-gated, protected lazy calls (begin, end)'
    if 'RunStreakService' in read('src/server/Bootstrap.server.luau') or 'RunStreak' in read('src/server/Remotes.luau') if (ROOT / 'src/server/Remotes.luau').exists() else False:
        return 'the streak has no remote'
    core = src(CORE)
    if '"RunStreak", "LastRunStreak", "LastRunStreakCrystals", --' not in core:
        return 'the streak numbers are owner-only (PRIVATE) values'
    if 'Config.PlayAgainEnabled == true then Rules.text(d.num("LastRunStreak")) else nil' not in complete:
        return 'Run Complete shows the soft streak line only with the flag on'
    return None


def read_doc():
    for p in sorted((ROOT / 'docs').glob('239-*.md')):
        return p.read_text(encoding='utf-8')
    return ''


def run(runner, replacements=None):
    """Runs the three parts. Returns (all passed, output)."""
    out = ''
    for name, build, marker in PARTS:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / ('play_again_%s.luau' % name)
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
            assert check_sources({path: source.replace(old, new, 1)}) is not None, 'SOURCE MUTANT SURVIVED: ' + name
            print('  source mutant caught: ' + name)
    print('Play again passed: flag off = old buttons / no bonus / no load, PLAY AGAIN + HOME at the end of a batch only, sizes and contrast, streak by the window (1..5, capped, '
          'resets quietly), bonus exactly once per run id in the settlement, server decides, broken service never blocks, session-only, Reduce Motion (no motion code), wiring, %d mutants caught'
          % (0 if args.no_mutants else len(MUTANTS) + len(SOURCE_MUTANTS)))


if __name__ == '__main__':
    main()
