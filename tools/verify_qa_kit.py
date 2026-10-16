"""BD-085 / BD-322 phone QA kit checks (docs/124).

Runs src/shared/QaOverlayRules.luau in the pinned Luau runtime (authorization, snapshot validation, rate limit, overlay lines),
checks the report script selftest, and statically checks the wiring: flag off in Config, no authorization in the client, the server
prints the [BD-QA] tag, touch targets in the overlay are at least 44 px, and the kit imports no gameplay modules.
Not Studio or phone evidence.
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local function id(o) local t = {userId = 100, allowedIds = {100}, unpublishedStudio = false, enabled = true} for k, v in o do t[k] = v end return t end
assert(Q.allowed(id({})), "listed id")
assert(not Q.allowed(id({userId = 101})), "unlisted id")
assert(not Q.allowed(id({enabled = false})), "flag off admits nobody")
assert(not Q.allowed(id({enabled = false, unpublishedStudio = true})), "flag off beats Studio")
assert(Q.allowed(id({userId = -1, allowedIds = {}, unpublishedStudio = true})), "unpublished Studio")
assert(not Q.allowed(id({userId = -5, allowedIds = {-5}})), "negative ids only in Studio")
assert(not Q.allowed(id({allowedIds = {}})), "empty list admits nobody (not even the owner)")
assert(not Q.allowed({userId = 100, unpublishedStudio = false, enabled = true}), "nil list")
assert(not Q.allowed(id({userId = "100"})), "non-number id")

assert(Q.sanitize(nil) == nil and Q.sanitize("x") == nil and Q.sanitize(5) == nil, "junk")
local s = Q.sanitize({label = "run_start", fps = 59.123, memMb = 1e12, pingMs = 0/0, instances = math.huge, parts = -4, touch = true, evil = "x"})
assert(s.label == "run_start" and s.fps == 59.12 and s.memMb == 100000 and s.pingMs == nil and s.instances == nil and s.parts == 0 and s.touch == true)
assert(s.evil == nil, "unknown fields dropped")
assert(Q.sanitize({label = 'a"}\n[BD-QA] {"x":1'}).label == "aBD-QA x1", "label cannot break the log line")
assert(Q.sanitize({label = string.rep("a", 99)}).label == string.rep("a", Q.MaxLabel), "label cut")
assert(Q.sanitize({label = 5}).label == "mark" and Q.sanitize({label = "!!!"}).label == "mark", "label fallback")
assert(Q.sanitize({fps = "60"}).fps == nil, "strings are not numbers")
assert(Q.mayMark(nil, 0) and not Q.mayMark(1, 1.2) and Q.mayMark(1, 1.6), "rate limit")
assert(#Q.Steps == 12 and Q.Steps[1] == "start_hub" and Q.Steps[12] == "end", "twelve tour steps")
local seen = {} for _, step in Q.Steps do assert(not seen[step] and #step <= Q.MaxLabel); seen[step] = true end
local lines = Q.lines({fps = 31, pingMs = 90})
assert(#lines == 4 and lines[1] == "fps 31  ping 90 ms" and lines[2]:find("mem %?"), lines[1])
assert(#Q.lines({}) == 4, "empty snapshot still renders")
print("qa kit rules passed")
'''


def static_checks():
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert re.search(r'^    QaOverlayEnabled = false,', config, re.M), 'Config.QaOverlayEnabled must be false'
    assert re.search(r'^    QaOverlayUserIds = \{\}', config, re.M), 'Config.QaOverlayUserIds must be empty'
    profiles = (ROOT / 'tools/release_profiles.py').read_text(encoding='utf-8')
    assert '_flag_off("QaOverlayEnabled"' in profiles, 'release_profiles must pin QaOverlayEnabled off in every profile'
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    assert 'QaService).start()' in boot, 'QaService wired in Bootstrap'
    server = (ROOT / 'src/server/QaService.luau').read_text(encoding='utf-8')
    assert 'if not Config.QaOverlayEnabled then return end' in server, 'server inert while the flag is off'
    assert 'Rules.allowed' in server and 'allowed[player] ~= true' in server, 'server re-authorizes every mark'
    assert 'Rules.LogTag' in server and 'JSONEncode' in server and 'Rules.sanitize' in server and 'Rules.mayMark' in server
    for banned in ('ProfileRepository', 'DataStore', 'FoodService', 'NestQueue', 'CosmeticOwnership', 'CombatService', 'HatchSequence',
                   'Telemetry', 'GoalsRules', 'ProgressionService', 'Cave'):
        assert banned not in server, 'QaService must stay out of gameplay: ' + banned
    client = (ROOT / 'src/client/QaOverlay.client.luau').read_text(encoding='utf-8')
    assert 'GetAttribute("QaOverlay")' in client and 'QaMark' in client
    assert 'rbxassetid' not in client and 'ImageLabel' not in client, 'no art in the developer overlay'
    for banned in ('InvokeServer', 'ProfileRepository', 'FoodService', 'HatchSequence', 'GoalsPanel', 'CombatHud'):
        assert banned not in client, 'overlay is display + mark only: ' + banned
    # touch targets: every button() call has a literal pixel height of at least 44
    heights = re.findall(r'button\("(\w+)",[^\n]*UDim2\.new\([^,]+,\s*-?\d+,\s*0,\s*(\d+)\)\)\s*$', client, re.M)
    assert {h[0] for h in heights} == {'MarkButton', 'StepButton', 'HideButton'}, heights
    for name, h in heights:
        assert int(h) >= 44, '%s is %s px, minimum 44' % (name, h)
    assert re.search(r'readout\.Font, readout\.TextSize, readout\.TextColor3 = Enum\.Font\.Code, 14,', client), 'readout text 14 px'
    rules = (ROOT / 'src/shared/QaOverlayRules.luau').read_text(encoding='utf-8')
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'task.', 'os.clock'):
        assert banned not in rules, 'QaOverlayRules stays pure: ' + banned
    # the report budgets cite the docs they came from
    report = (ROOT / 'tools/qa/phone_report.py').read_text(encoding='utf-8')
    assert 'docs/107' in report and 'docs/123' in report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    sys.path.insert(0, str(ROOT / 'tools/qa'))
    import phone_report
    phone_report.selftest()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'qa.luau'
        path.write_text('local Q = ' + module('src/shared/QaOverlayRules.luau') + '\n' + BODY, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            raise SystemExit(result.stderr or 'failed')
    print('qa kit checks passed')
