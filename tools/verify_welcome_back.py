#!/usr/bin/env python3
"""BD-1168 (docs/221 section 3 and 4, docs/223): the welcome-back card "Your nest is ready!" at join (Config.WelcomeBackEnabled).

Runs with the pinned Luau runtime:
  1. the pure rules of src/shared/WelcomeBack.luau (which nests count, the brand-new-save rule, the singular and plural words, the
     show and tap rules) together with the real NestQueue and the two NotifyQueue additions (a tap action, a time on screen);
  2. the real src/server/WelcomeBackService.luau on mocked services (flag off = nothing at all; flag on = the owner-only number is
     set once per join, never for a brand-new save, never for a nest that was ready before);
  3. the real ProfileRepository on the verify_rewards harness (mocked DataStore, controllable server clock): the three join facts,
     nothing stored, flag off = no facts.
Then checks the wiring statically (flag false in source, profiles, one line each in the two Bootstraps, the client cue) and puts
each defect back (mutants). NOT Studio or phone evidence.
Usage: python tools/verify_welcome_back.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_rewards  # noqa: E402

RULES = 'src/shared/WelcomeBack.luau'
QUEUE = 'src/shared/NotifyQueue.luau'
NESTS = 'src/shared/NestQueue.luau'
SERVICE = 'src/server/WelcomeBackService.luau'
REPO = 'src/server/ProfileRepository.luau'
CUE = 'src/client/WelcomeBackCue.luau'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path, replacements=None):
    source = read(path)
    for old, new in (replacements or {}).get(path, []):
        assert old in source, 'mutant target missing in %s: %s' % (path, old)
        source = source.replace(old, new)
    return '(function()\n' + source + '\nend)()'


UNIT = r'''
local D = 3 * 3600
-- which nests count: ready in the save as stored vs ready after the queue moved to the join time
local function away(isNew, stored, now)
    local before = W.readyCount(stored)
    local after = W.readyCount(if stored then NestQueue.project(stored, now, D) else nil)
    return W.finishedAway(isNew, before, after)
end
local one = {{nestId = "a", state = "incubating", readyAt = 1000 + D}}
assert(away(false, one, 1000 + D - 1) == 0, "one second early: nothing finished")
assert(away(false, one, 1000 + D) == 1, "finished exactly at the join time")
assert(away(false, {{nestId = "a", state = "ready", readyAt = 500}}, 99999) == 0, "a nest that was ready and left unopened is not counted again")
local three = {{nestId = "a", state = "ready", readyAt = 500}, {nestId = "b", state = "incubating", readyAt = 1000 + D}, {nestId = "c", state = "waiting"}, {nestId = "d", state = "waiting"}}
assert(away(false, three, 1000 + D) == 1 and away(false, three, 1000 + 2 * D) == 2 and away(false, three, 1000 + 30 * D) == 3, "the queue chains: one nest every 3 h, offline time counts")
assert(away(false, {}, 5000) == 0 and away(false, nil, 5000) == 0, "no nests, nothing to say")
assert(three[2].state == "incubating" and three[3].state == "waiting", "the stored list is never changed by the count")
-- the very first session of a brand-new save never gets the card, whatever the numbers say
assert(W.finishedAway(true, 0, 3) == 0 and W.finishedAway(nil, 0, 3) == 0 and W.finishedAway("no", 0, 3) == 0, "brand-new or unknown save: no card")
assert(W.finishedAway(false, 0, 3) == 3 and W.finishedAway(false, 2, 2) == 0 and W.finishedAway(false, 3, 1) == 0, "the difference, never negative")
assert(W.finishedAway(false, 0, 9999) == W.MaxNests and W.finishedAway(false, "1", 2) == 0 and W.finishedAway(false, 0, 0/0) == 0, "bounded, bad input is zero")
assert(W.readyCount({{state = "ready"}, "junk", {state = "waiting"}, {state = "ready"}}) == 2 and W.readyCount("x") == 0)
-- the words (docs/72: short, obvious, one number at most, no rule text)
assert(W.title(1) == "Your nest is ready!" and W.title(2) == "2 nests are ready!" and W.title(5) == "5 nests are ready!", W.title(2))
assert(W.card(0) == nil and W.card(-1) == nil and W.card(nil) == nil and W.card(0/0) == nil and W.card("2") == nil, "nothing finished: no card")
for n = 1, W.MaxNests do
    local card = W.card(n)
    assert(card.text == W.title(n) and card.body == W.Body and card.kind == "major" and card.icon == "egg_nest" and card.key == "welcome_back")
    assert(#card.text <= Q.MaxText and #card.body <= Q.MaxBody, "fits the toast card without being cut")
    assert(Q.clip(card.text, Q.MaxText) == card.text and Q.clip(card.body, Q.MaxBody) == card.body)
    for _, s in {card.text, card.body} do
        assert(not s:find("%d%a") and not s:find("%dm %ds") and not s:find("[Hh]atch") and not s:find("%d+ ?h") and not s:find("%.%d"), "kid words: " .. s)
    end
end
assert(W.card(2.9).text == "2 nests are ready!" and W.card(9999).text == W.MaxNests .. " nests are ready!")
assert(W.card(1).seconds == W.Seconds and W.Seconds > Q.Duration.major and W.Seconds <= Q.MaxSeconds, "stays a little longer than a normal big-moment card")
-- the client rule: once per join, only with a number, after the world is ready (or the wait), never in a run
assert(W.showNow({shown = false, count = 1, worldReady = true, waited = 0, runState = "Sanctuary"}) == true)
assert(W.showNow({shown = true, count = 1, worldReady = true, waited = 0, runState = "Sanctuary"}) == false, "once per join")
assert(W.showNow({shown = false, count = 0, worldReady = true, waited = 99, runState = "Sanctuary"}) == false, "nothing finished: nothing shown")
assert(W.showNow({shown = false, count = 2, worldReady = false, waited = W.WorldWaitSeconds - 1, runState = nil}) == false, "waits for the world")
assert(W.showNow({shown = false, count = 2, worldReady = false, waited = W.WorldWaitSeconds, runState = nil}) == true, "but not forever")
assert(W.showNow({shown = false, count = 2, worldReady = true, waited = 0, runState = "Active"}) == false and W.showNow({shown = false, count = 2, worldReady = true, waited = 0, runState = "Ending"}) == false, "never in a run")
assert(W.canOpen("Sanctuary") and W.canOpen(nil) and W.canOpen("Settled") and not W.canOpen("Active") and not W.canOpen("Ending"))
-- the toast stack: the card keeps its tap action and its time; other cards are untouched
do
    local q = Q.new()
    local taps = 0
    local card = W.card(2)
    assert(Q.push(q, 0, {text = card.text, body = card.body, kind = card.kind, key = card.key, icon = card.icon, seconds = card.seconds, action = function() taps += 1 end}) == "queued")
    assert(Q.push(q, 0, {text = "Level 2!", kind = "major"}) == "queued")
    assert(not Q.update(q, 0, true) and #q.visible == 0, "a big-moment card waits while a menu or the hatch reveal is open")
    assert(Q.update(q, 1, false) and #q.visible == 2)
    local welcome, level = q.visible[1], q.visible[2]
    assert(welcome.text == "2 nests are ready!" and welcome.expiresAt == 1 + W.Seconds and level.expiresAt == 1 + Q.Duration.major and level.action == nil and level.seconds == nil)
    Q.update(q, 1 + Q.Duration.major, false)
    assert(#q.visible == 1 and q.visible[1] == welcome, "the plain card left at its usual time, the welcome card stays")
    assert(Q.dismiss(q, welcome) and #q.visible == 0 and not Q.dismiss(q, welcome), "a tap closes exactly that card")
    welcome.action()
    assert(taps == 1)
    local q3 = Q.new()
    Q.push(q3, 0, {text = "First", kind = "major", action = function() end})
    Q.push(q3, 0, {text = "Second", kind = "major"})
    Q.update(q3, 0, false)
    local first = q3.visible[1]
    assert(first.text == "First" and Q.dismiss(q3, first) and #q3.visible == 1 and q3.visible[1].text == "Second", "the tapped card closes, not the newest one")
    local q2 = Q.new()
    Q.push(q2, 0, {text = "A", kind = "good", seconds = 999, action = "not a function"})
    Q.push(q2, 0, {text = "B", kind = "warning", seconds = -5})
    Q.push(q2, 0, {text = "C", kind = "major", seconds = 0/0})
    Q.update(q2, 0, false)
    local by = {} for _, c in q2.visible do by[c.text] = c end
    assert(by.A.expiresAt == Q.MaxSeconds and by.A.action == nil and by.B.expiresAt == 1 and by.C.expiresAt == Q.Duration.major, "the time is capped, a bad action or time is ignored")
    Q.update(q2, Q.MaxSeconds, false)
    assert(#q2.visible == 0, "it fades by itself")
end
print("welcome back rules ok")
'''

SERVICE_TEST = r'''
local function world(flag, infos)
    local sets, connects = {}, 0
    local added = {fns = {}}
    function added:Connect(fn) table.insert(self.fns, fn) connects += 1 end
    local list = {}
    local Players = {PlayerAdded = added, GetPlayers = function() return list end}
    local RS = {Shared = {Config = "Config", WelcomeBack = "WelcomeBack"}}
    local game = {GetService = function(_, name) return if name == "Players" then Players else RS end}
    local repository = {welcomeInfo = function(p) return infos[p] end}
    local PrivateState = {set = function(p, name, value) table.insert(sets, {p = p, name = name, value = value}) end}
    local script = {Parent = {ProfileRepository = "Repo", PrivateState = "PS"}}
    local function require(k)
        if k == "Config" then return {WelcomeBackEnabled = flag} elseif k == "WelcomeBack" then return W elseif k == "PS" then return PrivateState else return repository end
    end
    local setmetatable = setmetatable
    local Service = @@SERVICE@@
    local function player(state)
        local p = {attrs = {ProfileState = state}, changed = {}}
        function p:GetAttribute(k) return self.attrs[k] end
        function p:GetAttributeChangedSignal(_) local s = self.changed return {Connect = function(_, fn) table.insert(s, fn) connects += 1 end} end
        function p:set(k, v) self.attrs[k] = v for _, fn in self.changed do fn() end end
        return p
    end
    return {Service = Service, sets = sets, added = added, list = list, player = player, connects = function() return connects end}
end
-- flag off: nothing at all
do
    local infos = {}
    local w = world(false, infos)
    local p = w.player("Loaded")
    infos[p] = {isNew = false, readyBefore = 0, readyAfter = 2}
    table.insert(w.list, p)
    w.Service.start()
    assert(w.connects() == 0 and #w.sets == 0 and #w.added.fns == 0, "flag off: no connection, nothing sent")
end
-- flag on
do
    local infos = {}
    local w = world(true, infos)
    local early = w.player("Loaded") -- already in the server and loaded when the service starts
    infos[early] = {isNew = false, readyBefore = 1, readyAfter = 3}
    table.insert(w.list, early)
    w.Service.start()
    w.Service.start()
    assert(#w.added.fns == 1, "started once")
    assert(#w.sets == 1 and w.sets[1].p == early and w.sets[1].name == "WelcomeBackNests" and w.sets[1].value == 2, "two nests finished while away")
    early:set("ProfileState", "Loaded") early:set("ProfileState", "Loaded")
    assert(#w.sets == 1, "once per join")
    local late = w.player("Loading")
    w.added.fns[1](late)
    assert(#w.sets == 1, "nothing before the save is loaded")
    infos[late] = {isNew = false, readyBefore = 0, readyAfter = 1}
    late:set("ProfileState", "Loaded")
    assert(#w.sets == 2 and w.sets[2].p == late and w.sets[2].value == 1)
    infos[late] = {isNew = false, readyBefore = 0, readyAfter = 4}
    late:set("ProfileState", "Loaded")
    assert(#w.sets == 2, "a later change of the save never brings the card back in the same join")
    local fresh = w.player("Loading")
    w.added.fns[1](fresh)
    infos[fresh] = {isNew = true, readyBefore = 0, readyAfter = 1}
    fresh:set("ProfileState", "Loaded")
    local same = w.player("Loaded")
    infos[same] = {isNew = false, readyBefore = 2, readyAfter = 2}
    w.added.fns[1](same)
    local none = w.player("Loaded") -- no facts at all (the repository had the flag off)
    w.added.fns[1](none)
    local broken = w.player("Loaded")
    infos[broken] = "junk"
    w.added.fns[1](broken)
    assert(#w.sets == 2, "brand-new save, nothing new, no facts, broken facts: nothing is sent")
end
print("welcome back service ok")
'''

E2E_PRELUDE = '''local fakeNow=1800000000
local realOs=os
local os=setmetatable({time=function() return fakeNow end},{__index=realOs})
'''

E2E = r'''
local D=GameConfig.NestIncubationSeconds
local function nests(u) return data[key(u)].eggNests or {} end
local function run(u,id,catches,seconds) return Repository.commitRunSettlement(u,id,catches,nil,seconds) end
local function away(u) local i=Repository.welcomeInfo(u) return W.finishedAway(i.isNew,i.readyBefore,i.readyAfter) end
-- flag off (the default build): no facts are kept
local off=user(91680) assert(Repository.load(off))
assert(Repository.welcomeInfo(off)==nil, "flag off: no join facts")
Repository.release(off)
GameConfig.WelcomeBackEnabled=true
-- a brand-new save: its first session never gets the card
local u=user(91681) assert(Repository.load(u))
local info=Repository.welcomeInfo(u)
assert(info.isNew==true and info.readyBefore==0 and info.readyAfter==0 and away(u)==0, "brand-new save")
assert(run(u,"wb-1",10,300) and #nests(u)==1 and nests(u)[1].state=="incubating", "one nest dropped, incubating")
Repository.release(u)
-- back too early: nothing finished
fakeNow+=D-60
assert(Repository.load(u))
info=Repository.welcomeInfo(u)
assert(info.isNew==false and info.readyBefore==0 and info.readyAfter==0 and away(u)==0, "back before the nest is ready: no card")
Repository.release(u)
-- back after it finished: one nest
fakeNow+=60
assert(Repository.load(u))
info=Repository.welcomeInfo(u)
assert(info.isNew==false and info.readyBefore==0 and info.readyAfter==1 and away(u)==1, "the nest finished while away")
assert(nests(u)[1].state=="ready")
Repository.release(u)
-- joins again without opening it: it was ready before, so no second card
fakeNow+=500
assert(Repository.load(u))
info=Repository.welcomeInfo(u)
assert(info.readyBefore==1 and info.readyAfter==1 and away(u)==0, "ready and unopened: not counted again")
-- three more nests, then a long break: all of them finished while away (one ready one was already there)
for i=1,3 do assert(run(u,"wb-more-"..i,10,300)) end
assert(#nests(u)==4)
Repository.release(u)
fakeNow+=2*D
assert(Repository.load(u))
assert(away(u)==2, "two of the three finished in six hours")
Repository.release(u)
fakeNow+=40*D
assert(Repository.load(u))
info=Repository.welcomeInfo(u)
assert(info.readyBefore==3 and info.readyAfter==4 and away(u)==1, "the last one")
-- nothing about the card is stored in the save
local function has(t,word)
 if type(t)~="table" then return false end
 for k,v in t do if (type(k)=="string" and k:lower():find(word)) or has(v,word) then return true end end
 return false
end
assert(not has(data[key(u)],"welcome"), "nothing stored")
Repository.release(u)
print("welcome back repository ok")
'''


def unit_script(replacements=None):
    s = 'local NestQueue=' + module(NESTS, replacements) + '\n'
    s += 'local Q=' + module(QUEUE, replacements) + '\n'
    s += 'local W=' + module(RULES, replacements) + '\n'
    return s + UNIT


def service_script(replacements=None):
    s = 'local W=' + module(RULES, replacements) + '\n'
    return s + SERVICE_TEST.replace('@@SERVICE@@', module(SERVICE, replacements))


def e2e_script(replacements=None):
    s = verify_rewards.script()
    head = s[:s.index('------------------------------------------------------------------ RewardMath')]
    for old, new in (replacements or {}).get(REPO, []):
        assert old in head, 'mutant target missing in the harness copy of %s: %s' % (REPO, old)
        head = head.replace(old, new)
    return E2E_PRELUDE + head + 'local W=' + module(RULES, replacements) + '\n' + E2E


PARTS = (('rules', unit_script, 'welcome back rules ok'), ('service', service_script, 'welcome back service ok'), ('repository', e2e_script, 'welcome back repository ok'))

MUTANTS = {
    'a brand-new save gets the card': {RULES: [('if isNew ~= false then return 0 end', 'if isNew == nil then return 0 end')]},
    'a nest that was ready before is counted again': {RULES: [('local count = math.floor(readyAfter) - math.floor(readyBefore)', 'local count = math.floor(readyAfter)')]},
    'the count is not bounded': {RULES: [('return math.clamp(count, 0, W.MaxNests)', 'return count')]},
    'two nests still say Your nest is ready': {RULES: [('if count <= 1 then return "Your nest is ready!" end', 'if count <= 9 then return "Your nest is ready!" end')]},
    'the plural line is long rule text': {RULES: [('return string.format("%d nests are ready!", count)', 'return string.format("%d of your egg nests finished hatching", count)')]},
    'a card is made when nothing finished': {RULES: [('if typeof(count) ~= "number" or count ~= count or count < 1 then return nil end', 'if typeof(count) ~= "number" or count ~= count then return nil end')]},
    'the card shows again in the same join': {RULES: [('if s.shown == true or W.card(s.count) == nil then return false end', 'if W.card(s.count) == nil then return false end')]},
    'the card shows during a run': {RULES: [('    if not W.canOpen(s.runState) then return false end\n', '')]},
    'the card never waits for the world': {RULES: [('return s.worldReady == true or (typeof(s.waited) == "number" and s.waited >= W.WorldWaitSeconds)', 'return true')]},
    'the tap opens the Nests screen in a run': {RULES: [('return runState ~= "Active" and runState ~= "Ending"', 'return runState ~= "Ending"')]},
    'the card asks for a time the stack refuses': {RULES: [('W.Seconds = 8', 'W.Seconds = 60')]},
    'the stack ignores the asked time': {QUEUE: [('card.shownAt, card.expiresAt = now, now + (card.seconds or Q.Duration[card.kind])', 'card.shownAt, card.expiresAt = now, now + Q.Duration[card.kind]')]},
    'the asked time is not capped': {QUEUE: [('math.clamp(input.seconds, 1, Q.MaxSeconds)', 'input.seconds')]},
    'the stack drops the tap action': {QUEUE: [('action = if typeof(input.action) == "function" then input.action else nil,', 'action = nil,')]},
    'a tap closes the newest card instead of the tapped one': {QUEUE: [('    local at = table.find(q.visible, card)\n', '    local at = if #q.visible > 0 then #q.visible else nil\n')]},
    'the service runs with the flag off': {SERVICE: [('    if not enabled() then return end\n', '')]},
    'the service tells the client on every save change': {SERVICE: [('        told[player] = true -- once per join, whatever the save says later\n', '')]},
    'the service tells before the save is loaded': {SERVICE: [('if told[player] or player:GetAttribute("ProfileState") ~= "Loaded" then return end', 'if told[player] then return end')]},
    'the service sends a zero': {SERVICE: [('if count > 0 then PrivateState.set(player, "WelcomeBackNests", count) end', 'PrivateState.set(player, "WelcomeBackNests", count)')]},
    'the repository keeps the facts with the flag off': {REPO: [('local trackWelcome = Config.WelcomeBackEnabled == true -- BD-1168', 'local trackWelcome = true')]},
    'the repository counts the ready nests after the queue moved, twice': {REPO: [('welcome.isNew, welcome.readyBefore = current == nil, readyNests(profileValue) end -- BD-1168', 'welcome.isNew = current == nil end advanceNests(profileValue, now) if trackWelcome then welcome.readyBefore = readyNests(profileValue) end -- BD-1168')]},
    'the repository calls every save an old one': {REPO: [('welcome.isNew, welcome.readyBefore = current == nil, readyNests(profileValue) end', 'welcome.isNew, welcome.readyBefore = false, readyNests(profileValue) end')]},
    'the repository stores the facts in the save': {REPO: [('if trackWelcome then welcome.readyAfter = readyNests(profileValue) end', 'if trackWelcome then welcome.readyAfter = readyNests(profileValue) profileValue.welcomeBack = welcome.readyAfter end')]},
}

SOURCE_MUTANTS = {
    'the flag is on in the source': ('src/shared/Config.luau', 'WelcomeBackEnabled = false,', 'WelcomeBackEnabled = true,'),
    'the client cue ignores the flag': (CUE, 'if Config.WelcomeBackEnabled ~= true or attached then return end', 'if attached then return end'),
    'the client cue waits forever': (CUE, 'while os.clock() - started < 120 do', 'while true do'),
    'the client cue writes its own words': (CUE, 'notify(card.text, Theme.Colors.gold,', 'notify("Welcome back to Be Dino, your nests have finished!", Theme.Colors.gold,'),
    'the client cue has no tap action': (CUE, 'seconds = card.seconds, action = openNests})', 'seconds = card.seconds})'),
    'the tap opens the screen in a run': (CUE, '        if not Rules.canOpen(runState()) then return end\n', ''),
    'the toast stack ignores the tap action': ('src/client/Toasts.luau', 'if entry and entry.action and NotifyQueue.dismiss(notifyQueue,entry) then drawToasts() task.spawn(entry.action) return end', ''),
    'the toast stack does not pass the action on': ('src/client/Toasts.luau', 'live=o.live,action=o.action,seconds=o.seconds})', 'live=o.live})'),
    'Bootstrap does not attach the cue': ('src/client/Bootstrap.client.luau', 'require(script.Parent.WelcomeBackCue).attach(notify,open)', ''),
    'the server never starts the service': ('src/server/Bootstrap.server.luau', 'require(script.Parent.WelcomeBackService).start()', ''),
    'the number is a public Player attribute': ('src/shared/PrivateStateCore.luau', '"WelcomeBackNests", -- BD-1168', '-- BD-1168'),
    'the default profile does not pin the flag off': ('tools/release_profiles.py', '_flag_off("WelcomeBackEnabled",', '_flag_off("WelcomeBackEnabledX",'),
    'the playtest profile does not switch it on': ('tools/release_profiles.py', 'Rule("WelcomeBackEnabled", "set", True,', 'Rule("WelcomeBackEnabled", "set", False,'),
    'the flag is missing from the rehearsal list': ('tools/release_profiles.py', '("WelcomeBackEnabled", "BD-1168', '("WelcomeBackEnabledX", "BD-1168'),
}


def check_sources(overrides=None):
    """overrides: {path: source} for a source mutant. Returns the first problem or None."""
    def src(path):
        if overrides and path in overrides:
            return overrides[path]
        return read(path)
    if src('src/shared/Config.luau').count('    WelcomeBackEnabled = false,') != 1:
        return 'the flag must be false in source'
    prof = src('tools/release_profiles.py')
    for needle in ('_flag_off("WelcomeBackEnabled",', 'Rule("WelcomeBackEnabled", "set", True,', '("WelcomeBackEnabled", "BD-1168'):
        if needle not in prof:
            return 'release_profiles lost: ' + needle
    if src('src/client/Bootstrap.client.luau').count('require(script.Parent.WelcomeBackCue).attach(notify,open)') != 1:
        return 'Bootstrap (client) attaches the cue with one line'
    if src('src/server/Bootstrap.server.luau').count('require(script.Parent.WelcomeBackService).start()') != 1:
        return 'Bootstrap (server) starts the service with one line'
    if '"WelcomeBackNests", -- BD-1168' not in src('src/shared/PrivateStateCore.luau'):
        return 'WelcomeBackNests is an owner-only (PRIVATE) value'
    cue = src(CUE)
    code = [line.strip() for line in cue.splitlines() if line.strip() and not line.strip().startswith('--')]
    for needle in ('if Config.WelcomeBackEnabled ~= true or attached then return end', 'while os.clock() - started < 120 do', 'PrivateState.num("WelcomeBackNests")',
                   'Rules.showNow({shown = false, count = count,', 'local card = Rules.card(count) :: any',
                   'notify(card.text, Theme.Colors.gold, {kind = card.kind, key = card.key, icon = card.icon, body = card.body, seconds = card.seconds, action = openNests})',
                   'Sfx.playCue(Rules.Sound)', 'if not Rules.canOpen(runState()) then return end', 'return -- once per join',
                   'if not require(script.Parent.HubTravelClient).press("eggs", true) then open("eggs") end'):
        if needle not in cue:
            return 'WelcomeBackCue lost: ' + needle
    if any(word in '\n'.join(code) for word in ('Instance.new', 'FireServer', 'InvokeServer', 'rbxassetid')):
        return 'WelcomeBackCue builds no UI of its own, sends nothing and has no asset id'
    toasts = src('src/client/Toasts.luau')
    for needle in ('slot.entry=entry', 'if entry and entry.action and NotifyQueue.dismiss(notifyQueue,entry) then drawToasts() task.spawn(entry.action) return end',
                   'if NotifyQueue.dismissTop(notifyQueue) then drawToasts() end', 'live=o.live,action=o.action,seconds=o.seconds})'):
        if needle not in toasts:
            return 'Toasts lost: ' + needle
    service = src(SERVICE)
    service_code = '\n'.join(line for line in service.splitlines() if not line.strip().startswith('--'))
    for word in ('RemoteEvent', 'RemoteFunction', 'UpdateAsync', 'SetAttribute', 'FireClient', 'print(', 'UserId', '.Name'):
        if word in service_code:
            return 'WelcomeBackService has no remote, no write, no attribute, no print, no id: ' + word
    repo = src(REPO)
    if repo.count('Config.WelcomeBackEnabled == true') != 1 or repo.count('welcomeInfos[player] = welcome') != 1:
        return 'ProfileRepository reads the flag once and keeps the facts in memory'
    load = repo.split('function ProfileRepository.load(player: Player): boolean', 1)[1].split('\nend\n', 1)[0]
    before = load.split('advanceNests(profileValue, now)', 1)[0]
    if 'migrateLegacyNests(profileValue, now)' not in before or 'welcome.readyBefore = current == nil, readyNests(profileValue)' not in before.replace('welcome.isNew, ', ''):
        return 'the ready nests of the stored save are counted after the legacy migration and before the queue moves'
    if 'profileValue.welcome' in repo or 'welcome' in repo.split('local function isValidProfile', 1)[1].split('\nend\n', 1)[0]:
        return 'nothing about the card is stored or validated'
    for name in ('ProfileEggs', 'ProfileCollection', 'ProfilePrefs', 'ProfileShop', 'ProfileFusion', 'ProfileGifts', 'ProfileObjectives', 'ProfileSkins'):
        if 'elcomeBack' in read(f'src/server/{name}.luau'):
            return name + ' must not know the card'
    return None


def run(runner, replacements=None):
    """Runs the three parts. Returns (all passed, output)."""
    out = ''
    for name, build, marker in PARTS:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / ('welcome_back_%s.luau' % name)
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
    print('Welcome back passed: which nests count, brand-new save, singular and plural words, show and tap rules, toast action and time, '
          'service once per join, repository facts with nothing stored, wiring, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS) + len(SOURCE_MUTANTS)))


if __name__ == '__main__':
    main()
