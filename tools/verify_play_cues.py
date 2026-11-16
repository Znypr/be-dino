#!/usr/bin/env python3
"""BD-1226 + BD-1231 + BD-1234 (docs/242 benchmark gaps 11, 15, 19): the play cues behind Config.PlayCuesEnabled.

Runs the REAL Shared/PlayCuesRules in the pinned Luau runtime and checks: the point-at markers show only for a new player, only in the right
place (food in a run, nest and stall at home), and go away once used or after their time; the bob is calm and still with Reduce Motion; the
growth pop says "+N" in food points (never "+0.1"), merges fast bites, rises only with motion on; one banner per SIZE quarter; the egg-ready
toast never fires on the first reading after the join, the badge says "1".."9", "9+".
Source guards: the flag ships false (once), is pinned off in the default profile, ON in the playtest profile, in the rehearsal list and the
playtest manifest; every client script returns on its first lines with the flag off; client presentation only (no remote, no DataStore, no
Roblox notification service); every tag is a Chip (ChipStyle); Bootstrap and the hatch files do not know the flag; the kid words are short.
The mutants put each defect back and a check must fail. NOT Studio evidence (pictures: docs/evidence/2026-11-16-ui-feedback).
Usage: python tools/verify_play_cues.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RULES = 'src/shared/PlayCuesRules.luau'
CLIENTS = ('src/client/PointAtCue.client.luau', 'src/client/GrowthPop.client.luau', 'src/client/EggReadyCue.client.luau')
FLAG_LINE = 'if (Config :: any).PlayCuesEnabled ~= true then return end'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
-- point at the thing
check(Rules.isNew(1, 0) and Rules.isNew(2, nil) and not Rules.isNew(3, 0), "new = level 2 or lower")
check(Rules.isNew(9, 1), "a starter is new at any level")
check(not Rules.isNew(nil, nil), "unknown level is not new")
check(Rules.foodOn({new = true, runState = "Active", bites = 0, played = 0}), "food marker in a new player's run")
check(not Rules.foodOn({new = true, runState = "Sanctuary", bites = 0, played = 0}), "no food marker at home")
check(not Rules.foodOn({new = false, runState = "Active", bites = 0, played = 0}), "no food marker for a veteran")
check(not Rules.foodOn({new = true, runState = "Active", bites = Rules.FoodBites, played = 0}), "food marker gone after the bites")
check(not Rules.foodOn({new = true, runState = "Active", bites = 0, played = Rules.FoodSeconds}), "food marker gone after the first minutes")
check(Rules.nestOn({readyNests = 1, runState = "Sanctuary", opened = false}), "nest marker at home with a ready egg")
check(not Rules.nestOn({readyNests = 0, runState = "Sanctuary", opened = false}), "no nest marker without a ready egg")
check(not Rules.nestOn({readyNests = 1, runState = "Active", opened = false}), "no nest marker in a run")
check(not Rules.nestOn({readyNests = 1, runState = "Sanctuary", opened = true}), "nest marker gone once opened")
check(Rules.stallOn({new = true, runState = "Sanctuary", usedStall = false, home = 0}), "stall marker at home")
check(not Rules.stallOn({new = true, runState = "Sanctuary", usedStall = true, home = 0}), "stall marker gone once used")
check(not Rules.stallOn({new = true, runState = "Sanctuary", usedStall = false, home = Rules.StallSeconds}), "stall marker gone after a while")
check(not Rules.stallOn({new = false, runState = "Sanctuary", usedStall = false, home = 0}), "no stall marker for a veteran")
check(Rules.bob(0.3, false) == 0, "no bob with Reduce Motion")
local most = 0
for i = 0, 100 do most = math.max(most, math.abs(Rules.bob(i / 37, true))) end
check(most > 0.1 and most <= 1, "a calm bob (at most 1 stud)")
check(Rules.BobSeconds >= 0.8, "a slow bob")
check(Rules.nearest({{distance = 9}, {distance = 3}, {distance = 5}}) == 2, "nearest")
check(Rules.nearest({}) == nil, "nearest of nothing")
check(Rules.nearest({{distance = 3, clear = false}, {distance = 40, clear = true}}) == 2, "a stall in clear view beats a nearer hidden one")
check(Rules.nearest({{distance = 3, clear = false}}) == nil, "a stall under the rail is never picked")
check(Rules.inClearView(500, true, 1000) and Rules.inClearView(900, true, 1000) and not Rules.inClearView(100, true, 1000) and not Rules.inClearView(990, true, 1000), "the rail edge is not clear view")
check(Rules.StationLift > Rules.Lift, "a stall chip sits above the sign")
check(not Rules.inClearView(500, false, 1000), "behind the camera is not clear view")
for key, w in Rules.Words do check(#w <= 14 and not string.find(w, "%d"), "short marker word " .. key) end
-- growth pop
check(Rules.popText(0.1, 0.1) == "+1", "+1 for one food")
check(Rules.popText(0.5, 0.1) == "+5", "+5 for a big food")
check(Rules.popText(0.04, 0.1) == "+1", "at least +1")
check(Rules.popText(0, 0.1) == nil and Rules.popText(-1, 0.1) == nil and Rules.popText(0 / 0, 0.1) == nil, "no pop for nothing")
check(Rules.popText(1, 0) == nil, "no pop without a food size")
check(not string.find(Rules.popText(0.3, 0.1) or ".", "%."), "never a decimal")
check(Rules.milestone(0.2, 0.3) == "Bigger!", "first quarter")
check(Rules.milestone(0.3, 0.4) == nil, "no word between quarters")
check(Rules.milestone(0.2, 0.8) == "Huge!", "the biggest crossed word")
check(Rules.milestone(0.9, 1) == "Giant!", "full bar")
check(Rules.milestone(0.5, 0.5) == nil and Rules.milestone(0.6, 0.4) == nil, "no word without growth")
for _, m in Rules.Milestones do check(#m.word <= 12, "short banner word") end
local riseOn, secondsOn = Rules.popMotion(true)
local riseOff, secondsOff = Rules.popMotion(false)
check(riseOn > 0 and riseOn <= 4 and secondsOn <= 1.2, "a soft rise")
check(riseOff == 0 and secondsOff < secondsOn, "Reduce Motion: no rise, a short fade")
check(Rules.MergeSeconds > 0 and Rules.MaxPops <= 4, "no number storm")
-- egg ready
check(Rules.readyCount({{state = "ready"}, {state = "incubating"}, {state = "ready"}}) == 2, "ready count")
check(Rules.readyCount(nil) == 0 and Rules.readyCount({}) == 0, "ready count of nothing")
check(not Rules.toastNow(nil, 2), "no toast on the first reading")
check(Rules.toastNow(0, 1) and Rules.toastNow(1, 2), "toast when an egg gets ready")
check(not Rules.toastNow(2, 2) and not Rules.toastNow(2, 1), "no toast when nothing new")
check(Rules.toastText(1) == "Your egg is ready!", "one egg words")
check(Rules.toastText(3) == "3 eggs are ready!", "more eggs words")
check(Rules.badgeText(0) == "" and Rules.badgeText(1) == "1" and Rules.badgeText(9) == "9" and Rules.badgeText(12) == "9+", "badge words")
check(#Rules.ToastText <= 24 and #Rules.ToastBody <= 24, "short toast words")
if #fails > 0 then print("FAIL " .. table.concat(fails, "; ")) else print("OK") end
'''


def run_rules(runner, rules_text):
    source = 'local Rules = (function()\n' + rules_text + '\nend)()\n' + LUAU
    with tempfile.NamedTemporaryFile('w', suffix='.luau', delete=False, encoding='utf-8') as handle:
        handle.write(source)
        path = handle.name
    result = subprocess.run([runner, path], capture_output=True, text=True, timeout=60)
    Path(path).unlink(missing_ok=True)
    out = (result.stdout + result.stderr).strip()
    return out.splitlines()[-1] if out else 'FAIL no output'


def guards(clients, config, profiles, playtest):
    problems = []
    if len(re.findall(r'^    PlayCuesEnabled = false,$', config, re.M)) != 1:
        problems.append('Config.PlayCuesEnabled must ship false exactly once')
    for needle in ('_flag_off("PlayCuesEnabled",', 'Rule("PlayCuesEnabled", "set", True,', '("PlayCuesEnabled", "BD-1226'):
        if needle not in profiles:
            problems.append('release_profiles.py misses ' + needle)
    if '"PlayCuesEnabled"' not in playtest:
        problems.append('the playtest manifest must show PlayCuesEnabled')
    for path, text in clients.items():
        head = text.split('local Rules = require', 1)[0]
        if FLAG_LINE not in head:
            problems.append(path + ': must return first with the flag off')
        code = '\n'.join(line.split('--', 1)[0] for line in text.splitlines())
        for banned in ('FireServer', 'InvokeServer', 'DataStore', 'ExperienceNotificationService', 'HatchStage', 'HatchSequence', 'shake'):
            if banned in code:
                problems.append(path + ': client presentation only, no ' + banned)
        if 'AlwaysOnTop = true' in code:
            problems.append(path + ': AlwaysOnTop only through the marker argument (stall and nest), never fixed on')
    point, egg = clients[CLIENTS[0]], clients[CLIENTS[2]]
    for path, text in ((CLIENTS[0], point), (CLIENTS[2], egg)):
        if 'Chip.new(' not in text:
            problems.append(path + ': every tag is a Chip (ChipStyle)')
    if 'local food = marker("Food", nil, false)' not in point:
        problems.append('the food chip is drawn in the world (Studio evidence can see it)')
    if 'Rules.bob(clock, motion())' not in point:
        problems.append('the markers must bob through the rules (Reduce Motion)')
    if 'Rules.popMotion(motion())' not in clients[CLIENTS[1]]:
        problems.append('the growth pop must follow Reduce Motion')
    if 'Rules.toastNow(previous, count)' not in egg:
        problems.append('the egg toast must ask the rules')
    for path in ('src/client/Bootstrap.client.luau', 'src/client/HatchSequence.luau', 'src/client/HatchStage.luau'):
        if 'PlayCues' in read(path):
            problems.append(path + ' must not know the flag')
    return problems


MUTANTS = {
    'a hidden stall wins': ('rules', 'if item.clear ~= false and item.distance < bestD then', 'if item.distance < bestD then'),
    'veterans get markers': ('rules', 'return typeof(level) == "number" and level <= Rules.NewPlayerLevel', 'return true'),
    'the food marker never goes': ('rules', 'and s.bites < Rules.FoodBites and s.played < Rules.FoodSeconds', ''),
    'the nest marker stays after opening': ('rules', 'and s.runState == "Sanctuary" and not s.opened', 'and s.runState == "Sanctuary"'),
    'the stall marker stays after use': ('rules', 'and not s.usedStall and s.home < Rules.StallSeconds', ''),
    'the chip bobs with Reduce Motion': ('rules', '    if not motion then return 0 end\n    return math.sin', '    return math.sin'),
    'a decimal pop': ('rules', 'local n = math.max(1, math.floor(delta / perFood + 0.5))\n    if n > 9999 then return "+9999" end\n    return "+" .. tostring(n)', 'return string.format("+%.1f", delta)'),
    'every bite a banner': ('rules', 'if before < m.fill and after >= m.fill then word = m.word end', 'word = m.word'),
    'the pop rises with Reduce Motion': ('rules', 'return 0, Rules.PopStillSeconds', 'return Rules.PopRise, Rules.PopStillSeconds'),
    'a toast at join': ('rules', 'return previous ~= nil and current > previous', 'return current > (previous or 0)'),
    'a badge for zero': ('rules', 'if typeof(count) ~= "number" or count < 1 then return "" end', ''),
    'the flag is ignored': ('client0', FLAG_LINE, ''),
    'the pop calls the server': ('client1', 'local player = Players.LocalPlayer', 'local player = Players.LocalPlayer\nReplicatedStorage.X:FireServer()'),
    'the badge is not a chip': ('client2', 'Chip.new(badgeLayer,', 'Instance.new("Frame", badgeLayer,'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    rules = read(RULES)
    clients = {path: read(path) for path in CLIENTS}
    config, profiles, playtest = read('src/shared/Config.luau'), read('tools/release_profiles.py'), read('tools/release_playtest.py')
    out = run_rules(args.runner, rules)
    problems = guards(clients, config, profiles, playtest)
    if out != 'OK' or problems:
        print('verify_play_cues FAILED:', out, problems)
        return 1
    if not args.no_mutants:
        survived = []
        for name, (where, old, new) in MUTANTS.items():
            if where == 'rules':
                assert old in rules, 'mutant target missing: ' + name
                killed = run_rules(args.runner, rules.replace(old, new, 1)) != 'OK'
            else:
                path = CLIENTS[int(where[-1])]
                assert old in clients[path], 'mutant target missing: ' + name
                mutated = dict(clients)
                mutated[path] = clients[path].replace(old, new, 1)
                killed = bool(guards(mutated, config, profiles, playtest))
            if not killed:
                survived.append(name)
        if survived:
            print('verify_play_cues FAILED: mutants survived:', survived)
            return 1
        print('verify_play_cues: %d mutants killed' % len(MUTANTS))
    print('verify_play_cues OK: rules, flag wiring and source guards')
    return 0


if __name__ == '__main__':
    sys.exit(main())
