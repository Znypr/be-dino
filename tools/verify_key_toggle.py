#!/usr/bin/env python3
"""BD-1074: the key that opens a screen also closes it (owner rule 2026-10-18: "what would a player expect?").

Studio round 4 (docs/192 part B) found that C (Dino Index), B (Eggs) and the station key G (Crystal Shops, Eggs, Fusion, Potions)
left the screen open when pressed a second time. This offline check runs the REAL pure rules in the pinned Luau runtime:

1. ModalCloseRules.keyAction(openName, want): "close" only when the screen on show IS the one the key belongs to; every other case opens.
2. HubWalkUpRules.press(state, station, canOpen, openName, now): the station key closes its own open screen, never opens a screen the
   station does not own, keeps the old rules (not while busy, never inside the 0.5 s gap), and a held key never opens then closes at once.
3. SOURCE GUARDS: Bootstrap routes C / B through keyAction, passes `current` to the hub travel client, the Escape / gamepad B line that
   verify_close_paths.py guards is untouched, the Fusion menu closes from the key only through closeFromKey (never while saving).
4. MUTANTS: the checks must FAIL when the toggle is removed (keyAction always opens; press never closes; press closes any station).

Not Studio evidence: no key was pressed in a real window here. Usage: python tools/verify_key_toggle.py --runner luau.exe
"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def wrapped(path, replacements=()):
    text = (ROOT / path).read_text(encoding='utf-8')
    for old, new in replacements:
        assert old in text, 'mutant target missing in %s: %s' % (path, old)
        text = text.replace(old, new)
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local Rules = ModalCloseRules
-- keyAction: the key of the open screen closes it; anything else opens
assert(Rules.keyAction("collection", "collection") == "close", "C twice closes the Dino Index")
assert(Rules.keyAction("eggs", "eggs") == "close", "B twice closes the Eggs screen")
assert(Rules.keyAction("", "collection") == "open" and Rules.keyAction(nil, "eggs") == "open", "nothing open: the key opens")
assert(Rules.keyAction("eggs", "collection") == "open" and Rules.keyAction("collection", "eggs") == "open", "another screen open: the key switches to its own")
assert(Rules.keyAction("hatch", "eggs") == "open", "a hatch on screen is not the Eggs screen: B does not close it")
assert(Rules.keyAction(5, "eggs") == "open" and Rules.keyAction({}, "eggs") == "open", "junk is never 'open'")

-- press: the station key
local W = HubWalkUpRules
local function fresh() return W.newState() end
local stations = {}
for _, s in W.stations() do stations[#stations + 1] = s.id end
assert(#stations >= 4, "the hub has its station prompts")
for _, id in stations do
    local dest = W.destination(id)
    assert(dest ~= nil)
    local st = fresh()
    assert(W.press(st, id, true, "", 10) == "open", id .. ": closed screen, key opens")
    assert(W.press(st, id, false, dest, 10.2) == "none", id .. ": a second press inside the gap does nothing (held key)")
    assert(W.press(st, id, false, dest, 10.6) == "close", id .. ": own screen open, key closes it (even though the scrim says canOpen = false)")
    st = fresh()
    assert(W.press(st, id, true, dest, 3) == "close", id .. ": close does not need canOpen")
    st = fresh()
    assert(W.press(st, id, false, "", 3) == "none", id .. ": busy / in a run / scrim up and nothing of ours open: nothing")
    for _, other in stations do
        if other ~= id then
            local st2 = fresh()
            local otherDest = W.destination(other)
            -- the screen of ANOTHER station is open: this key must not close it, and (canOpen false while a screen is up) must not open anything
            assert(W.press(st2, id, false, otherDest, 3) == "none", id .. " does not close " .. other .. "'s screen")
        end
    end
end
assert(W.press(fresh(), "heart", true, "", 5) == "none" and W.press(fresh(), nil, true, "", 5) == "none" and W.press(fresh(), "gate", true, "", 5) == "none", "no menu station, no action")
assert(W.press(fresh(), stations[1], true, 5, 5) == "open", "junk openName counts as nothing open")
-- the old entry point is unchanged
do
    local st = fresh()
    assert(W.trigger(st, stations[1], true, 10) == true and W.trigger(st, stations[1], true, 10.1) == false and W.trigger(st, stations[1], false, 20) == false)
end
print("key toggle passed: keyAction and press close the screen of their own key, nothing else")
'''


def script(replacements=None):
    replacements = replacements or {}
    return ('local mods={}\n'
            + 'local script={Parent={CaveHubLayout="CaveHubLayout",HubTravelClientRules="HubTravelClientRules"}}\n'
            + 'local require=function(name) return mods[name] end\n'
            + 'local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau') + '\nmods.CaveHubLayout=CaveHubLayout\n'
            + 'local HubTravelClientRules=' + wrapped('src/shared/HubTravelClientRules.luau') + '\nmods.HubTravelClientRules=HubTravelClientRules\n'
            + 'local ModalCloseRules=' + wrapped('src/shared/ModalCloseRules.luau', replacements.get('ModalCloseRules', ())) + '\n'
            + 'local HubWalkUpRules=' + wrapped('src/shared/HubWalkUpRules.luau', replacements.get('HubWalkUpRules', ())) + '\n' + LUAU)


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify_key_toggle.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


MUTANTS = {
    'keyAction never closes (old behaviour: key twice stays open)': {
        'ModalCloseRules': [('and openName == want then return "close" end', 'and openName == want then return "open" end')],
    },
    'keyAction closes whatever is open': {
        'ModalCloseRules': [('and openName ~= "" and openName == want then', 'and openName ~= "" then')],
    },
    'press never closes (old behaviour)': {
        'HubWalkUpRules': [('if typeof(openName) == "string" and openName == destination then', 'if false then')],
    },
    'press closes any open screen, not only its own': {
        'HubWalkUpRules': [('if typeof(openName) == "string" and openName == destination then', 'if typeof(openName) == "string" and openName ~= "" then')],
    },
    'press ignores the gap (a held key opens then closes)': {
        'HubWalkUpRules': [('if destination == nil or now - state.lastOpen < HubWalkUpRules.TriggerGap then return "none" end', 'if destination == nil then return "none" end')],
    },
    'press opens even when busy': {
        'HubWalkUpRules': [('    if not canOpen then return "none" end\n    state.lastOpen = now\n    return "open"', '    state.lastOpen = now\n    return "open"')],
    },
}


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_sources():
    boot = read('src/client/Bootstrap.client.luau')
    assert 'keyAction(' in boot and 'Enum.KeyCode.C or input.KeyCode==Enum.KeyCode.B' in boot, 'Bootstrap: C and B go through ModalCloseRules.keyAction'
    assert 'current=function() return if shade.Visible then active else "" end' in boot, 'Bootstrap tells the hub travel client which screen is on show'
    assert 'KeyCode==Enum.KeyCode.Escape or input.KeyCode==Enum.KeyCode.ButtonB) and shade.Visible then close()' in boot, 'the Escape / B line is untouched'
    walk = read('src/client/HubWalkUpClient.luau')
    assert 'Rules.press(state, s.id, canOpen(), openName(), os.clock())' in walk, 'the station prompt asks Rules.press'
    assert 'closeFromKey()' in walk and 'ctx.close()' in walk, 'the station key closes the Fusion menu through closeFromKey and every other screen through ctx.close'
    assert walk.count('openStation(') == 2, 'a screen still opens only from the prompt (one definition, one call)'
    assert 'Heartbeat' not in walk and 'padAt' not in walk, 'no dwell: stations open only on their key or prompt (docs/114 6.2)'
    fusion = read('src/client/FusionMenu.luau')
    body = fusion[fusion.index('function FusionMenu.closeFromKey'):][:300]
    assert 'fusionOutsideCloses(state.mode)' in body, 'the key never closes the Fusion menu while it is saving or showing the wheel'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_sources()
    result = run(args.runner, script())
    print(result.stdout, end='')
    if result.returncode or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            assert run(args.runner, script(replacements)).returncode != 0, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
    print('Key toggle passed: source guards, rules, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
