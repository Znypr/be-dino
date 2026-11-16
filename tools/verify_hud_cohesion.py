#!/usr/bin/env python3
"""BD-1213 (docs/240 step 2, style tile v2 board 1): the in-run HUD and the world labels on the style rules R1-R8 behind Config.HudCohesionEnabled.

Runs the REAL Shared/HudCohesionRules in the pinned Luau runtime and checks: the crystal count is grouped ("12,450"; Bootstrap's "N Crystals" is
read back, a grouped number is left alone so the rewrite stops), the test chip only in an unsaved Studio preview and never wider / taller than the
old preview slot, the HUD text sizes on the 28 / 20 / 16 / 14 scale, the key badge clear of a centred word (Kit.Hud numbers), "+3 Crystals" above
its model, LEAP blue becomes grey and every other colour stays.
Source guards: the flag ships false (once) and is pinned off in the default profile, ON in the playtest profile, in the rehearsal list and the
playtest manifest; the client script returns on its first lines with the flag off; Bootstrap and the hatch files do not mention it; client
presentation only (no remote, no DataStore, no Instance.new of anything but plates and labels).
The mutants put each defect back and a check must fail. NOT Studio evidence: nobody saw a pixel here (pictures: docs/evidence/2026-11-16-hud-cohesion).
Usage: python tools/verify_hud_cohesion.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RULES = 'src/shared/HudCohesionRules.luau'
CLIENT = 'src/client/HudCohesion.client.luau'
KIT = 'src/shared/ToyboxKit.luau'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local Kit = KIT
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
check(Rules.grouped(0) == "0", "0")
check(Rules.grouped(999) == "999", "999")
check(Rules.grouped(1000) == "1,000", "1,000")
check(Rules.grouped(12450) == "12,450", "12,450")
check(Rules.grouped(1000000) == "1,000,000", "1,000,000")
check(Rules.grouped(12449.6) == "12,450", "rounds")
check(Rules.crystalsFrom("1000000 Crystals") == 1000000, "reads N Crystals")
check(Rules.crystalsFrom("1,000,000") == nil, "a grouped number is left alone")
check(Rules.crystalsFrom("500") == nil, "a short number is left alone")
check(Rules.testChipVisible("Studio preview (not saved)") == true, "chip in a Studio preview")
check(Rules.testChipVisible("Live") == false and Rules.testChipVisible(nil) == false, "no chip in a live game")
check(#Rules.TestChip <= 24 and not string.find(Rules.TestChip, "STUDIO") and not string.find(Rules.TestChip, "•"), "kid words on the chip")
for _, slot in {{500, 25}, {250, 24}, {120, 20}, {184, 26}} do
    local w, h = Rules.chipSize(slot[1], slot[2])
    check(w <= slot[1] and h <= slot[2] and h >= 14 + 4, "chip fits slot " .. slot[1] .. "x" .. slot[2])
end
for name, size in Rules.Text do check(Rules.onScale(size) and size >= Kit.MinText, "text size on the scale: " .. name) end
local H = Kit.Hud
local anchor, x, y = Rules.badgeSpot(H.badgeInset)
check(anchor.Y == 0.5 and y == 0 and x < 0, "badge hangs on the top edge")
check(Rules.badgeClear(H.height, H.badge, H.word), "badge clear of the word")
check(Rules.labelLift(12, 10) >= 2 + 1, "label above the model top")
check(Rules.labelLift(5, 10) >= 1, "label never inside the part")
local blue, grey, green = Color3.fromRGB(46, 206, 255), Color3.fromRGB(128, 142, 158), Color3.fromRGB(93, 237, 31)
check(Rules.leapColour(blue, blue, grey) == grey, "LEAP blue becomes grey")
check(Rules.leapColour(green, blue, grey) == green, "other colours stay")
if #fails > 0 then print("FAIL " .. table.concat(fails, "; ")) else print("OK") end
'''

COLOR = r'''
local Color3 = {}
Color3.__index = Color3
Color3.__eq = function(a, b) return a.r == b.r and a.g == b.g and a.b == b.b end
function Color3.fromRGB(r, g, b) return setmetatable({r = r, g = g, b = b}, Color3) end
local Vector2 = {new = function(x, y) return {X = x, Y = y} end}
'''


def run_rules(runner, rules_text):
    source = COLOR + 'local Rules = ' + module(rules_text) + '\nlocal KIT = ' + module(read(KIT)) + '\n' + LUAU
    with tempfile.NamedTemporaryFile('w', suffix='.luau', delete=False, encoding='utf-8') as handle:
        handle.write(source)
        path = handle.name
    result = subprocess.run([runner, path], capture_output=True, text=True, timeout=60)
    Path(path).unlink(missing_ok=True)
    out = (result.stdout + result.stderr).strip()
    return out.splitlines()[-1] if out else 'FAIL no output'


def guards(client, config, profiles):
    problems = []
    if len(re.findall(r'^    HudCohesionEnabled = false,$', config, re.M)) != 1:
        problems.append('the flag ships false in Config (once)')
    if '_flag_off("HudCohesionEnabled",' not in profiles:
        problems.append('the default profile pins the flag off')
    if 'Rule("HudCohesionEnabled", "set", True,' not in profiles:
        problems.append('the playtest profile sets it on')
    if '("HudCohesionEnabled", "BD-1213' not in profiles:
        problems.append('the rehearsal list has it')
    if '"HudCohesionEnabled"' not in read('tools/release_playtest.py'):
        problems.append('the playtest manifest records it')
    head = client.split('local Rules = require', 1)[0]
    if 'if (Config :: any).HudCohesionEnabled ~= true then return end' not in head:
        problems.append('the client script returns first with the flag off')
    code = '\n'.join(line.split('--', 1)[0] for line in client.splitlines())
    for banned in ('FireServer', 'InvokeServer', 'DataStore', 'RemoteEvent', 'RemoteFunction', 'ImageLabel', 'HatchStage', 'HatchSequence'):
        if banned in code:
            problems.append('client presentation only, no ' + banned)
    made = set(re.findall(r'Instance\.new\("(\w+)"\)', code))
    if not made <= {'Frame', 'TextLabel', 'UICorner', 'UIStroke'}:
        problems.append('only plates and labels are made: ' + ', '.join(sorted(made)))
    for path in ('src/client/Bootstrap.client.luau', 'src/client/HatchSequence.luau'):
        if 'HudCohesion' in read(path):
            problems.append(path + ' must not know the flag')
    return problems


MUTANTS = {
    'no thousands comma': ('rules', 'if count % 3 == 0 and i > 1 then out = "," .. out end', ''),
    'the grouped number is rewritten again': ('rules', 'string.match(text, "^(%d+) Crystals$")', 'string.match(text, "^([%d,]+)")'),
    'the chip shows in a live game': ('rules', 'return profileMode == Rules.PreviewMode', 'return true'),
    'the chip is wider than its slot': ('rules', 'return math.min(Rules.TestChipW, slotW), math.min(Rules.TestChipH, slotH)', 'return Rules.TestChipW, Rules.TestChipH'),
    'the badge sits on the word again': ('rules', 'return Vector2.new(1, 0.5), -inset, 0', 'return Vector2.new(1, 0), -inset, inset'),
    'the world label is off the scale': ('rules', 'worldLabel = 20}', 'worldLabel = 18}'),
    'the label sits inside its amber': ('rules', 'return math.max(modelTop - anchorY, 0) + Rules.LabelGap', 'return 0'),
    'LEAP stays blue': ('rules', 'return if current == blue then grey else current', 'return current'),
    'the flag is ignored': ('client', 'if (Config :: any).HudCohesionEnabled ~= true then return end', ''),
    'the script calls the server': ('client', 'local player = Players.LocalPlayer', 'local player = Players.LocalPlayer\nReplicatedStorage.X:FireServer()'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    rules, client = read(RULES), read(CLIENT)
    config, profiles = read('src/shared/Config.luau'), read('tools/release_profiles.py')
    out = run_rules(args.runner, rules)
    problems = guards(client, config, profiles)
    if out != 'OK' or problems:
        print('verify_hud_cohesion FAILED:', out, problems)
        return 1
    if not args.no_mutants:
        survived = []
        for name, (where, old, new) in MUTANTS.items():
            text = rules if where == 'rules' else client
            assert old in text, 'mutant target missing: ' + name
            mutated = text.replace(old, new, 1)
            if where == 'rules':
                killed = run_rules(args.runner, mutated) != 'OK'
            else:
                killed = bool(guards(mutated, config, profiles))
            if not killed:
                survived.append(name)
        if survived:
            print('verify_hud_cohesion FAILED: mutants survived:', survived)
            return 1
        print('verify_hud_cohesion: %d mutants killed' % len(MUTANTS))
    print('verify_hud_cohesion OK: rules, flag wiring and source guards')
    return 0


if __name__ == '__main__':
    sys.exit(main())
