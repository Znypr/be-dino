"""Check MeshSanity (src/shared/MeshSanity.luau) against the REAL authored creature data: every species' source
vertices span a non-degenerate, non-cube box that passes the check, while a cube-shaped, empty or NaN part (what a
failed mesh load renders as) is rejected. Guards the 'authored species drawn as a plain cube' bug (docs/86).
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'src' / 'shared' / 'CreatureData'


def extents():
    result = {}
    for module in sorted(DATA.glob('*.luau')):
        names = re.findall(r'Chunks\.([\w]+)\)', module.read_text(encoding='utf-8'))
        text = ''
        for name in names:
            raw = (DATA / 'Chunks' / f'{name}.luau').read_text(encoding='utf-8')
            text += re.search(r'\[==\[(.*)\]==\]', raw, re.S).group(1)
        data = json.loads(text)
        low = [min(v[i] for v in data['vertices']) for i in range(3)]
        high = [max(v[i] for v in data['vertices']) for i in range(3)]
        result[module.stem] = ([h - l for l, h in zip(low, high)], data.get('triangles', len(data['faces'])))
    return result


BODY = r'''
local cases = __CASES__
for _, c in cases do
    local e = {X = c[2][1], Y = c[2][2], Z = c[2][3]}
    local ok, why = Sanity.check(e, e, c[3])
    assert(ok, c[1] .. " real mesh must pass: " .. tostring(why))
    assert(not Sanity.check(e, {X = 1, Y = 1, Z = 1}, c[3]), c[1] .. " cube must fail")
    assert(not Sanity.check(e, {X = 4, Y = 4, Z = 4}, c[3]), c[1] .. " bigger cube must fail")
    assert(not Sanity.check(e, {X = 0, Y = 0, Z = 0}, c[3]), c[1] .. " empty must fail")
    assert(not Sanity.check(e, {X = 0/0, Y = e.Y, Z = e.Z}, c[3]), c[1] .. " nan must fail")
    assert(Sanity.check(e, {X = e.X * 1.05, Y = e.Y * .97, Z = e.Z}, c[3]), c[1] .. " small rounding must pass")
    assert(not Sanity.check(e, e, 2), c[1] .. " too few triangles must fail")
end
print("Mesh sanity checks passed for " .. #cases .. " authored creatures (real extents pass; cube, empty, NaN and tiny meshes rejected)")
-- BD-219 content check: a MeshPart whose EditableMesh was destroyed keeps its Size but has 0 faces and draws as a box.
assert(Sanity.contentLoaded("Object", 1400, "") == true, "live editable mesh is loaded")
assert(Sanity.contentLoaded("Object", 0, "") == false, "destroyed editable mesh (0 faces) is NOT loaded")
assert(Sanity.contentLoaded("Object", nil, "") == false, "unreadable editable mesh is NOT loaded")
assert(Sanity.contentLoaded("Uri", nil, "rbxassetid://1") == true, "uploaded mesh is loaded")
assert(Sanity.contentLoaded("None", nil, "rbxassetid://1") == true, "legacy MeshId part is loaded")
assert(Sanity.contentLoaded("None", nil, "") == false, "no mesh at all is NOT loaded")
local _, why = Sanity.contentLoaded("Object", 0, "")
assert(string.find(why, "destroyed"), "reason names the destroyed mesh")
print("Mesh content checks passed: destroyed/empty editable meshes are rejected, live and uploaded meshes accepted")
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    cases = extents()
    assert len(cases) >= 17, f'expected authored creatures, found {len(cases)}'
    for name, (size, _) in cases.items():
        assert min(size) > .05, f'{name} degenerate extents {size}'
    lua = '{' + ','.join(f'{{"{n}",{{{s[0]},{s[1]},{s[2]}}},{t}}}' for n, (s, t) in cases.items()) + '}'
    source = '(function()\n' + (ROOT / 'src/shared/MeshSanity.luau').read_text(encoding='utf-8') + '\nend)()'
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'sanity.luau'
        path.write_text('local Sanity=' + source + '\n' + BODY.replace('__CASES__', lua), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'content checks passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
