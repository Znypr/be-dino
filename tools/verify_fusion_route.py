#!/usr/bin/env python3
"""BD-1196 (docs/234, polish finding P-43bc51): opening "fusion" never shows an empty window under the title of the screen before.

Cause: Bootstrap's open(name) is the shared menu window; it has no "fusion" screen (the Fusion menu is FusionMenu, its own gui), so open("fusion") cleared the body,
drew nothing and left the heading of the last screen ("Potion Shop", purple header). The rail button and the hub paths already call openFusion; any other caller of
open("fusion") hit the hole.
This check runs the REAL ModalGuard (src/client/ModalGuard.luau) in the pinned Luau runtime with a small Instance mock:
 * routed("fusion", openFusion) calls openFusion once and answers true (the shared window is left alone); other names answer false and call nothing; without an
   opener nothing is routed (never a crash);
 * fill(name, ui) on an empty body sets the heading to the name (capitalised), the header colour and one "Nothing here yet" line, and answers true; on a body with
   content it changes nothing; the hatch body (it fills itself later) is left alone;
 * the source: Bootstrap's open() asks ModalGuard.routed BEFORE it clears the body, and asks ModalGuard.fill right after render(name); the rail, the hub travel, the
   walk-up and the Dino Index all open Fusion through openFusion, none through open("fusion").
The mutants put each defect back and the check must fail. NOT Studio evidence: nobody saw a pixel (a Studio look at the Fusion button is the follow-up).
Usage: python tools/verify_fusion_route.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


LUAU = r'''
local failures = {}
local function check(ok, msg) if not ok then table.insert(failures, msg) end end

local calls = 0
check(Guard.routed("fusion", function() calls += 1 end) == true and calls == 1, "fusion is routed to its own menu exactly once")
calls = 0
for _, name in {"home", "eggs", "collection", "auras", "potions", "settings", "detail", "hatch", "results", "potionConfirm"} do
    check(Guard.routed(name, function() calls += 1 end) == false, name .. " must stay in the shared window")
end
check(calls == 0, "no other name calls the Fusion opener")
check(Guard.routed("fusion", nil) == false, "no opener: nothing is routed and nothing crashes")

local function frame(children)
    local f = {BackgroundColor3 = "old"}
    f.kids = children
    function f:GetChildren() return self.kids end
    return f
end
local function ui(children)
    local made = {}
    return {body = frame(children), heading = {Text = "Potion Shop"}, header = {BackgroundColor3 = "purple"}, color = "card", gold = "gold",
        label = function(parent, text, x, y, w, h, size, color) table.insert(made, text) table.insert(parent.kids, text) return text end, made = made}
end
do
    local u = ui({})
    check(Guard.fill("fusion", u) == true, "an empty body is filled")
    check(u.heading.Text == "Fusion", "the title comes from the name, not the last screen: " .. tostring(u.heading.Text))
    check(u.header.BackgroundColor3 == "card", "the header colour is reset")
    check(#u.made == 1 and u.made[1] == Guard.EmptyText, "one calm line")
end
do
    local u = ui({"something"})
    check(Guard.fill("eggs", u) == false and u.heading.Text == "Potion Shop" and #u.made == 0, "a body with content is left alone")
end
do
    local u = ui({})
    check(Guard.fill("hatch", u) == false and u.heading.Text == "Potion Shop" and #u.made == 0, "the hatch body is left alone")
end

if #failures > 0 then print(table.concat(failures, "\n")) error("fusion route check failed") end
print("fusion route passed: ModalGuard routes fusion, fills an empty window with its own title and one line, leaves content and the hatch alone")
'''


def guard_source(replacements=()):
    text = read('src/client/ModalGuard.luau')
    for old, new in replacements:
        assert old in text, 'mutant target missing in ModalGuard: ' + old
        text = text.replace(old, new)
    return '(function()\n' + text + '\nend)()'


def script(replacements=None):
    return 'local Guard = ' + guard_source((replacements or {}).get('ModalGuard', ())) + '\n' + LUAU


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify_fusion_route.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


def check_sources(boot=None):
    boot = boot if boot is not None else read('src/client/Bootstrap.client.luau')
    start = boot.index('local function open(name: string)')
    end = boot.index('\nlocal fusionProbe', start)
    body = boot[start:end]
    assert 'ModalGuard).routed(name,openFusion)' in body, 'open() asks ModalGuard.routed'
    assert body.index('ModalGuard).routed') < body.index('body:ClearAllChildren()'), 'the routing happens BEFORE the body is cleared'
    assert 'ModalGuard).fill(name' in body, 'open() fills an empty window'
    assert body.index('render(name)') < body.index('ModalGuard).fill(name'), 'fill runs after the screen drew'
    for path in ('src/client/Bootstrap.client.luau', 'src/client/HubTravelClient.luau', 'src/client/HubWalkUpClient.luau', 'src/client/DinoIndexScreens.luau', 'src/client/DinoIndexPanels.luau'):
        text = read(path)
        assert not re.search(r'\bopen\(\s*"fusion"\s*\)', text), path + ' opens "fusion" through the shared window'
    assert 'entry[3]=="fusion" then openFusion()' in boot, 'the rail FUSION button opens the Fusion menu'
    assert 'if destination == "fusion" then ctx.openFusion()' in read('src/client/HubTravelClient.luau')


BOOT_MUTANTS = {
    'open() no longer routes fusion': lambda b: b.replace('if require(script.Parent.ModalGuard).routed(name,openFusion) then return end', ''),
    'the routing happens after the body is cleared': lambda b: b.replace('    if require(script.Parent.ModalGuard).routed(name,openFusion) then return end -- BD-1196\n', '', 1).replace('    body:ClearAllChildren()\n', '    body:ClearAllChildren()\n    if require(script.Parent.ModalGuard).routed(name,openFusion) then return end\n', 1),
    'the empty window is not filled': lambda b: b.replace('require(script.Parent.ModalGuard).fill(name', 'noop(name'),
    'the rail FUSION button opens the shared window': lambda b: b.replace('entry[3]=="fusion" then openFusion()', 'entry[3]=="fusion" then open("fusion")'),
}
GUARD_MUTANTS = {
    'fusion is not an own menu': [('Guard.OwnMenus = {fusion = true}', 'Guard.OwnMenus = {}')],
    'the title stays the last screen\'s': [('ui.heading.Text, ui.header.BackgroundColor3 = Guard.title(name), ui.color', 'ui.header.BackgroundColor3 = ui.color')],
    'an empty window gets no line': [('    ui.label(ui.body, Guard.EmptyText, 0, 120, 824, 60, 32, ui.gold)\n', '')],
    'a window with content is overwritten': [('or #ui.body:GetChildren() > 0 then return false end', 'then return false end')],
    'the hatch body is filled': [('if name == "hatch" or', 'if')],
}


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
    count = 0
    if not args.no_mutants:
        boot = read('src/client/Bootstrap.client.luau')
        for name, mutate in BOOT_MUTANTS.items():
            mutated = mutate(boot)
            assert mutated != boot, 'mutant target missing: ' + name
            try:
                check_sources(mutated)
            except (AssertionError, ValueError):
                print('  mutant caught: ' + name)
                count += 1
                continue
            raise AssertionError('MUTANT SURVIVED: ' + name)
        for name, replacements in GUARD_MUTANTS.items():
            assert run(args.runner, script({'ModalGuard': replacements})).returncode != 0, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
            count += 1
    print('Fusion route passed: ModalGuard rules, source wiring, %d mutants caught' % count)


if __name__ == '__main__':
    main()
