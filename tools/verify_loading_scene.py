#!/usr/bin/env python3
"""BD-1232 (docs/242 benchmark gap 17): the loading scene, the rotating kid tip and the late Skip behind Config.LoadingSceneEnabled.

Runs the REAL Shared/LoadingScene in the pinned Luau runtime and checks: the scene id is a real uploaded image listed in docs/77 (no code-drawn
art: no Frame painting, the picture is an ImageLabel with that id), the tips are short kid words (no "5m 0s", no "1.25x", one line), every tip
shows in turn, Skip shows only after the save has loaded and a few seconds have passed.
Source guards: the flag ships false (once), is pinned off in the default profile, ON in the playtest profile, the rehearsal list and the
manifest; the loading script reads it only with the warm look; the picture, tip and Skip are built only inside `if scene then`; a problem
message hides the tip; Skip only ends the cover (no remote, no DataStore).
The mutants put each defect back and a check must fail. NOT Studio evidence (pictures: docs/evidence/2026-11-16-ui-feedback).
Usage: python tools/verify_loading_scene.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RULES = 'src/shared/LoadingScene.luau'
LOADING = 'src/loading/Loading.client.luau'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
check(S.validImage(S.SceneImage), "the scene is an uploaded image id")
check(not S.validImage("") and not S.validImage("rbxasset://textures/x.png") and not S.validImage(nil), "bad ids are refused")
check(#S.Tips >= 5, "enough tips")
local seen = {}
for i = 0, #S.Tips - 1 do seen[S.tipAt(i * S.TipSeconds + 0.1, 0)] = true end
local n = 0
for _ in seen do n += 1 end
check(n == #S.Tips, "every tip shows in turn")
check(S.tipAt(0, 2) == S.Tips[3], "the seed picks the first tip")
check(S.tipAt(S.TipSeconds - 0.01, 0) == S.tipAt(0, 0), "a tip stays for TipSeconds")
for _, tip in S.Tips do
    check(#tip <= S.TipMax, "one line: " .. tip)
    check(not string.find(tip, "%d+m %d+s") and not string.find(tip, "%d%.%d+x") and not string.find(tip, "%%"), "kid words: " .. tip)
end
check(S.TipSeconds >= 3, "a tip stays long enough to read")
check(not S.skipVisible(S.SkipSeconds + 5, false), "no Skip before the save loaded")
check(not S.skipVisible(S.SkipSeconds - 1, true), "no Skip at once")
check(S.skipVisible(S.SkipSeconds, true), "Skip after a few seconds")
check(S.SceneShade > 0 and S.SceneShade < 0.6, "a light veil, the picture stays visible")
if #fails > 0 then print("FAIL " .. table.concat(fails, "; ")) else print("OK") end
'''


def run_rules(runner, rules_text):
    source = 'local S = (function()\n' + rules_text + '\nend)()\n' + LUAU
    with tempfile.NamedTemporaryFile('w', suffix='.luau', delete=False, encoding='utf-8') as handle:
        handle.write(source)
        path = handle.name
    result = subprocess.run([runner, path], capture_output=True, text=True, timeout=60)
    Path(path).unlink(missing_ok=True)
    out = (result.stdout + result.stderr).strip()
    return out.splitlines()[-1] if out else 'FAIL no output'


def guards(texts):
    problems = []
    if len(re.findall(r'^    LoadingSceneEnabled = false,$', texts['config'], re.M)) != 1:
        problems.append('Config.LoadingSceneEnabled must ship false exactly once')
    for needle in ('_flag_off("LoadingSceneEnabled",', 'Rule("LoadingSceneEnabled", "set", True,', '("LoadingSceneEnabled", "BD-1232'):
        if needle not in texts['profiles']:
            problems.append('release_profiles.py misses ' + needle)
    if '"LoadingSceneEnabled"' not in texts['playtest']:
        problems.append('the playtest manifest must show LoadingSceneEnabled')
    image = re.search(r'S\.SceneImage = "rbxassetid://(\d+)"', texts['rules'])
    if not image or image.group(1) not in texts['registry']:
        problems.append('the scene id must be a registered asset (docs/77)')
    loading = texts['loading']
    if 'scene=warm and (config :: any).LoadingSceneEnabled==true' not in loading:
        problems.append('the scene follows the flag and the warm look only')
    block = loading.split('    if scene then\n', 1)[1].split('\nend\nReplicatedFirst', 1)[0] if '    if scene then\n' in loading else ''
    for needle in ('Scene.validImage(Scene.SceneImage)', 'art.Image', 'Scene.SceneImage', 'tipWord,tipChip=tip,chip', 'skip.Activated:Connect(function() skipped=true end)'):
        if needle not in block:
            problems.append('built only inside `if scene then`: ' + needle)
    if 'if tipChip then tipChip.Visible = false end' not in loading:
        problems.append('a problem message hides the tip')
    if 'Scene.skipVisible(os.clock() - started, state == "Loaded" and character ~= nil)' not in loading:
        problems.append('Skip follows the rules (only after the save loaded)')
    code = '\n'.join(line.split('--', 1)[0] for line in (loading + texts['rules']).splitlines())
    for banned in ('FireServer', 'InvokeServer', 'DataStore', 'EditableImage', 'rbxasset://'):
        if banned in code:
            problems.append('no remote, no store, no code-drawn picture: ' + banned)
    return problems


MUTANTS = {
    'Skip before the save loaded': ('rules', 'return loaded and elapsed >= S.SkipSeconds', 'return elapsed >= S.SkipSeconds'),
    'the same tip forever': ('rules', 'local step = math.max(0, math.floor(elapsed / S.TipSeconds))', 'local step = 0'),
    'a grown-up tip': ('rules', '"Eat food to grow big!",', '"Growth x1.25 for 5m 0s with potions!",'),
    'a code-drawn scene': ('rules', 'S.SceneImage = "rbxassetid://116338780514546"', 'S.SceneImage = "rbxasset://textures/scene.png"'),
    'the flag is ignored': ('loading', 'scene=warm and (config :: any).LoadingSceneEnabled==true', 'scene=warm'),
    'the tip stays over a problem': ('loading', 'if tipChip then tipChip.Visible = false end', ''),
    'Skip always shown': ('loading', 'Scene.skipVisible(os.clock() - started, state == "Loaded" and character ~= nil)', 'true'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    texts = {'rules': read(RULES), 'loading': read(LOADING), 'config': read('src/shared/Config.luau'), 'profiles': read('tools/release_profiles.py'),
             'playtest': read('tools/release_playtest.py'), 'registry': read('docs/77-asset-registry.md')}
    out = run_rules(args.runner, texts['rules'])
    problems = guards(texts)
    if out != 'OK' or problems:
        print('verify_loading_scene FAILED:', out, problems)
        return 1
    if not args.no_mutants:
        survived = []
        for name, (where, old, new) in MUTANTS.items():
            assert old in texts[where], 'mutant target missing: ' + name
            mutated = dict(texts)
            mutated[where] = texts[where].replace(old, new, 1)
            killed = (run_rules(args.runner, mutated['rules']) != 'OK' or bool(guards(mutated))) if where == 'rules' else bool(guards(mutated))
            if not killed:
                survived.append(name)
        if survived:
            print('verify_loading_scene FAILED: mutants survived:', survived)
            return 1
        print('verify_loading_scene: %d mutants killed' % len(MUTANTS))
    print('verify_loading_scene OK: rules, real art id, flag wiring and source guards')
    return 0


if __name__ == '__main__':
    sys.exit(main())
