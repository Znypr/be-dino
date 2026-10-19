"""BD-428: rare-hatch celebration + server-wide announcement (src/shared/RareHatch.luau, src/server/RareHatchService.luau,
src/client/RareHatchClient.client.luau). Offline: classification from the settled outcome (Legendary, Shiny, event mutation,
never a Cracked egg), kid-friendly text, name cleaning, the announcer (best egg per window, per-hatcher cooldown, global cap,
duplicate eggs), the Effects / Reduce Motion plan, and a source scan (server decides, the remote is server -> client only,
no invented asset ids, HatchSequence untouched).

    python tools/verify_rare_hatch.py --runner /path/to/luau
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (docs/150: ProfileRepository plus its parts)

BODY = r'''
local LEG = 5
-- 1. classification
assert(R.classify({}, 1) == nil and R.classify({shiny = false, eventMutationId = ""}, 4) == nil, "ordinary eggs are not rare")
assert(R.classify({failed = true, shiny = true}, 5) == nil, "a Cracked egg is never rare")
assert(R.classify(nil, 5) == nil and R.classify("x", 5) == nil)
local leg = R.classify({}, LEG) assert(leg and leg.kind == "legendary" and leg.legendary)
local sh = R.classify({shiny = true}, 1) assert(sh and sh.kind == "shiny" and sh.shiny)
local mu = R.classify({eventMutationId = "lava"}, 1) assert(mu and mu.kind == "mutation" and mu.mutation)
local both = R.classify({shiny = true}, LEG) assert(both and both.score > sh.score and sh.score > leg.score and leg.score > mu.score)
assert(R.classify({}, nil) == nil)
-- 2. text
assert(R.text("Sam", sh, "T-Rex") == "Sam hatched a Shiny T-Rex!")
assert(R.text("Sam", leg, "T-Rex") == "Sam hatched a Legendary T-Rex!")
assert(R.text("Sam", mu, "Compy") == "Sam hatched a Mutant Compy!")
assert(R.ownText(sh, "T-Rex") == "You hatched a Shiny T-Rex!")
assert(R.cleanName("  Bob\n\0 ") == "Bob" and R.cleanName("") == "A player" and R.cleanName(5) == "A player")
assert(#R.cleanName(string.rep("x", 60)) == R.MaxName)
for _, t in {R.text("Sam", both, "T-Rex"), R.ownText(leg, "Spinosaurus")} do assert(#t <= 48, "short text: " .. t) end
-- 3. announcer: a 15-egg reveal with several rares announces ONE (the best) and stays quiet after
local st = R.newState()
local t0 = 100
local f1 = R.offer(st, 1, "e1", leg, "legend", t0) assert(f1 == t0 + R.Window, "first rare opens a window")
assert(R.offer(st, 1, "e2", sh, "shiny", t0 + 0.5) == nil, "second rare merges")
assert(R.offer(st, 1, "e3", mu, "mut", t0 + 1) == nil)
assert(R.offer(st, 1, "e2", both, "dup", t0 + 1) == nil, "a repeated egg id is dropped")
local out = R.flush(st, 1, t0 + R.Window)
assert(out and out.text == "shiny", "best egg wins: " .. tostring(out and out.text))
assert(R.flush(st, 1, t0 + R.Window) == nil, "nothing pending after a flush")
assert(R.offer(st, 1, "e4", both, "late", t0 + 20) == nil, "hatcher is quiet during the cooldown")
assert(R.offer(st, 1, "e5", both, "later", t0 + R.Window + R.Cooldown + 1) ~= nil, "after the cooldown a new window opens")
assert(st.stats.announced == 1 and st.stats.merged >= 2 and st.stats.dropped >= 2)
-- 4. global cap
local g = R.newState()
local sent = 0
for u = 1, 10 do
    R.offer(g, u, "g" .. u, sh, "x", 500) if R.flush(g, u, 503) then sent += 1 end
end
assert(sent == R.GlobalMax, "global cap per window: " .. sent)
R.offer(g, 99, "g99", sh, "x", 520) assert(R.flush(g, 99, 523) ~= nil, "cap frees after the window")
-- 5. forget
local f = R.newState() R.offer(f, 7, "z1", sh, "x", 1) R.forget(f, 7) assert(R.flush(f, 7, 5) == nil)
-- 6. Effects / Reduce Motion plan
assert(R.plan("full", false, "shiny").confetti > R.plan("lite", false, "shiny").confetti and R.plan("lite", false, "shiny").confetti > 0)
assert(R.plan("off", false, "shiny").confetti == 0 and R.plan("full", true, "shiny").confetti == 0, "Off and Calm: no confetti")
assert(R.plan("full", true, "shiny").banner and R.plan("off", true, "legendary").sound == "shiny_bang", "banner + sound stay")
assert(R.plan("bogus", false, "shiny").confetti == R.Confetti.full)
-- 7. BD-439 runtime: the REAL CooldownMemory + Rare.offer/flush wired as RareHatchService.record does (UserId-keyed cooldown,
-- Rare.forget on leave). Hatch rare, leave, rejoin inside 45 s, hatch another rare: personal celebration yes, 2nd server announcement no.
local announced = CM.new(math.max(120, R.Cooldown * 2))
local sim = R.newState()
local clock, me, all = 1000, 0, 0
local function record(userId, eggId)
    me += 1 -- the hatcher's own celebration fires before any cooldown check
    local flushAt = nil
    if clock - announced.last(userId, "announce") >= R.Cooldown then flushAt = R.offer(sim, userId, eggId, sh, "txt", clock)
    else sim.seen[eggId] = true end
    if flushAt then
        clock = flushAt
        if R.flush(sim, userId, clock) then announced.mark(userId, "announce", clock) all += 1 end
    end
end
record(42, "r1") assert(me == 1 and all == 1, "first rare: celebration and one announcement")
clock += 10 R.forget(sim, 42) -- leaves
clock += 10 -- rejoins about 22 s after the announcement, same UserId
record(42, "r2")
assert(me == 2 and all == 1, "rejoin inside 45 s: own celebration, no second announcement: me=" .. me .. " all=" .. all)
clock += R.Cooldown + 1 record(42, "r3")
assert(me == 3 and all == 2, "after the cooldown a new announcement is allowed: all=" .. all)
record(43, "o1") assert(all == 3, "another player is not limited by 42's cooldown")
-- 8. BD-1121 the two-line announcement: words, the checks of the server payload, the fades
local NAMES = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}
assert(R.FindTitle == "RARE FIND!" and R.SecretFindTitle == "SECRET FIND!" and R.findTitle("legendary") == "RARE FIND!" and R.findTitle("secret") == "SECRET FIND!")
assert(R.findLine({kind = "legendary"}, "Legendary", "Compy") == "A Legendary Compy was found!")
assert(R.findLine({kind = "shiny", shiny = true}, "Epic", "Raptor") == "An Epic Shiny Raptor was found!", "An before a vowel")
assert(R.findLine({kind = "mutation", mutation = true}, "Uncommon", "T-Rex") == "An Uncommon Mutant T-Rex was found!")
assert(R.findLine({kind = "shiny", shiny = true, mutation = true}, "Rare", "Compy") == "A Rare Shiny Mutant Compy was found!")
assert(R.findLine({kind = "secret", secret = true}, nil, nil) == "A secret dino was found!" and R.findLine({kind = "secret"}, "Rare", "Hidden Name") == "A secret dino was found!", "a secret keeps its name out of it")
assert(R.findLine({kind = "legendary"}, nil, "Compy") == nil and R.findLine({kind = "legendary"}, "Rare", "") == nil, "missing words -> nil")
for _, line in {R.findLine({kind = "shiny", shiny = true, mutation = true}, "Uncommon", "Quetzalcoatlus"), R.findLine({kind = "legendary"}, "Legendary", "Therizinosaurus")} do assert(#line <= 60, "short: " .. line) end
local ok = R.findFromPayload({k = "all", kind = "legendary", tier = 5, species = "Compy", text = "Sam hatched a Legendary Compy!"}, NAMES)
assert(ok and ok.title == "RARE FIND!" and ok.line == "A Legendary Compy was found!", "good payload")
assert(not string.find(ok.line, "Sam") and not string.find(ok.title, "Sam"), "no player name in the new look")
local sec = R.findFromPayload({kind = "secret", species = "Silly Name"}, NAMES)
assert(sec and sec.title == "SECRET FIND!" and sec.line == "A secret dino was found!" and not string.find(sec.line, "Silly"), "secret payload")
for _, bad in {
    {kind = "legendary", tier = 9, species = "Compy"}, {kind = "legendary", tier = 0, species = "Compy"}, {kind = "legendary", tier = 2.5, species = "Compy"},
    {kind = "legendary", tier = "5", species = "Compy"}, {kind = "legendary", tier = 5}, {kind = "legendary", tier = 5, species = ""},
    {kind = "legendary", tier = 5, species = "<b>Compy</b>"}, {kind = "legendary", tier = 5, species = string.rep("x", 25)}, {kind = "legendary", tier = 5, species = "A\nB"},
    {kind = "legendary", tier = 5, species = "Co\"mpy"}, {kind = "weird", tier = 5, species = "Compy"}, {tier = 5, species = "Compy"}, {kind = 5, tier = 5, species = "Compy"},
} do assert(R.findFromPayload(bad, NAMES) == nil, "a bad payload is refused: " .. tostring(bad.species)) end
assert(R.findFromPayload("x", NAMES) == nil and R.findFromPayload(nil, NAMES) == nil, "not a table")
assert(R.findFromPayload({kind = "shiny", tier = 4, species = "T-Rex", shiny = true}, NAMES).line == "An Epic Shiny T-Rex was found!")
local motion, calm = R.findPlan(false), R.findPlan(true)
assert(motion.fadeIn > 0 and motion.fadeOut > 0 and motion.hold >= 3 and calm.fadeIn == 0 and calm.fadeOut == 0 and calm.hold == motion.hold, "Reduce Motion: no fades, the same time on screen")
print("rare hatch rules passed")
'''


def script():
    text = (ROOT / 'src/shared/RareHatch.luau').read_text(encoding='utf-8')
    cm = (ROOT / 'src/server/CooldownMemory.luau').read_text(encoding='utf-8')
    return 'local R = (function()\n' + text + '\nend)()\nlocal CM = (function()\n' + cm + '\nend)()\n' + BODY


def scan():
    svc = (ROOT / 'src/server/RareHatchService.luau').read_text(encoding='utf-8')
    cli = (ROOT / 'src/client/RareHatchClient.client.luau').read_text(encoding='utf-8')
    repo = profile_sources.repository_text()
    assert 'RareHatchService.record(player, committedOutcome)' in repo, 'publishHatch must hand the settled outcome to the service'
    assert 'OnServerEvent' not in svc, 'the RareHatch remote is server -> client only: never trust a client message'
    assert 'FireServer' not in cli, 'the client sends nothing'
    assert 'DisplayName' in svc, 'announcements carry display names only'
    assert 'FireAllClients' not in svc, 'announcements go through the rate limiter, one per window'
    assert 'Rare.offer' in svc and 'Rare.flush' in svc
    assert 'CooldownMemory' in svc and 'announced.mark(' in svc and 'announced.last(' in svc, 'BD-439: UserId-keyed announcement cooldown'
    assert 'quietUntil' not in svc, 'the cooldown must not live in the per-leave state'
    for needle in ['s.calm', 's.effects', 'Rare.plan', 'shiny_bang']:
        assert needle in cli, 'client must honour Effects / Reduce Motion and play the special sound: ' + needle
    for p in ['src/shared/RareHatch.luau', 'src/server/RareHatchService.luau', 'src/client/RareHatchClient.client.luau']:
        assert not re.search(r'rbxassetid://\d+', (ROOT / p).read_text(encoding='utf-8')), p + ' must not contain asset ids'
    assert 'RareHatch' not in (ROOT / 'src/client/HatchSequence.luau').read_text(encoding='utf-8'), 'HatchSequence stays untouched (PR #240)'
    assert 'RareHatch' not in (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8'), 'Bootstrap is at the local-register limit'
    # BD-1121: the two-line look is behind the flag on both sides; the old payload is byte for byte the same with the flag off; a secret's name never goes out
    assert 'if Config.RareFindBannerEnabled == true then' in svc and 'event:FireClient(other, {k = "all", kind = out.info.kind, text = out.text})' in svc, 'flag off: the old payload'
    assert 'if info.secret then nil else speciesName' in svc, 'a secret species name is never sent'
    assert 'Config.RareFindBannerEnabled == true and FindBanner.show(' in cli, 'the client draws the new look only with the flag on'
    banner = (ROOT / 'src/client/RareFindBanner.luau').read_text(encoding='utf-8')
    assert 'DisplayName' not in banner and 'data.text' not in banner, 'the new look has no player name and shows no free text'
    print('Source scan passed: server decides, server -> client only, no asset ids, HatchSequence untouched')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'rare.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
