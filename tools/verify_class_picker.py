"""BD-423: species picker shows class + feel hint (ClassInfo), and class movement has its own flag (ClassMovementEnabled)."""
import argparse, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['Config', 'ProgressionConfig', 'CombatConfig', 'ClassMovement', 'ClassInfo', 'AssetSlots', 'ClassBadge']
BODY = r'''
local CI,Combat,Cfg=M.ClassInfo,M.CombatConfig,M.Config
local want={Ground="Fast runner",Fly="Flies and glides",Water="Swims and dashes",Armored="Tough armor"}
for id,class in Combat.SpeciesClasses do
  local i=CI.forSpecies(id)
  assert(i.class==class and i.hint==want[class] and #i.label>0,id)
  assert(#CI.line(id)<=32,"short kid copy: "..id)
  assert(not CI.line(id):find("%d"),"no numbers in picker copy")
end
assert(CI.forSpecies(nil).class=="Ground" and CI.forSpecies("bogus").hint=="Fast runner")
assert(Cfg.ClassMovementEnabled==false and Cfg.CombatEnabled==false)
for _,c in M.ClassMovement.ClassNames do assert(CI.Labels[c] and CI.Hints[c],c) end
-- Class badge (owner 2026-10-16): 4 slots, one letter each, unbound = clearly a placeholder, bound = the owner icon.
local seen={}
for c,slot in CI.IconSlots do assert(M.AssetSlots.Images[slot]=="" and #CI.Letters[c]==1 and not seen[CI.Letters[c]],c) seen[CI.Letters[c]]=true end
for _,c in M.ClassMovement.ClassNames do assert(CI.IconSlots[c],c) end
for id,class in Combat.SpeciesClasses do
  local sp=M.ClassBadge.spec(id)
  assert(sp.class==class and sp.placeholder and sp.image==nil and sp.letter==CI.Letters[class] and sp.label==CI.Labels[class],id)
end
M.AssetSlots.Images.class_water="rbxassetid://123"
local w=M.ClassBadge.spec("mosasaurus") assert(w.image=="rbxassetid://123" and not w.placeholder and w.letter=="W")
M.AssetSlots.Images.class_water="not an id" assert(M.ClassBadge.spec("mosasaurus").placeholder,"malformed id falls back")
M.AssetSlots.Images.class_water=""
assert(M.ClassBadge.spec(nil).class=="Ground","unknown species is Ground")
print("class picker ok")
'''


def module(n):
    return '(function()\n' + (ROOT / 'src/shared' / f'{n}.luau').read_text(encoding='utf-8') + '\nend)()'


p = argparse.ArgumentParser()
p.add_argument('--runner', required=True)
a = p.parse_args()
src = '\n'.join(['local M={}', 'local Color3={fromRGB=function() return 0 end,new=function() return 0 end}','local script={Parent=M}', 'local require=function(x) return x end']
                + [f'M.{n}={module(n)}' for n in MODULES] + [BODY])
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / 'cp.luau'
    f.write_text(src, encoding='utf-8')
    r = subprocess.run([a.runner, str(f)], capture_output=True, text=True)
    print(r.stdout, end='')
    print(r.stderr, end='')
if r.returncode == 0:
    def read(q):
        return (ROOT / q).read_text(encoding='utf-8')
    for q in ('src/server/ClassMovementService.luau', 'src/server/ProgressionService.luau',
              'src/client/ClassDash.client.luau', 'src/client/ClassGlide.client.luau'):
        t = read(q)
        assert 'ClassMovementEnabled' in t, q
        assert 'Config.CombatEnabled' not in t.replace('GameConfig.CombatEnabled', ''), q + ' still gated on combat'
    assert 'ClassInfo' in read('src/client/Bootstrap.client.luau'), 'picker uses ClassInfo'
    rp = read('tools/release_profiles.py')
    assert '_flag_off("ClassMovementEnabled"' in rp and 'Rule("ClassMovementEnabled", "set", True' in rp
    cb = read('src/shared/ClassBadge.luau')
    assert 'PLACEHOLDER' in cb and 'UICorner' in cb and 'AssetSlots.image' in cb
    hs = read('src/client/HatchSequence.luau')
    assert 'ClassBadge.create' in hs and 'classBadge' in hs and 'speciesId' in hs, 'reveal card shows the class badge'
    assert 'speciesId=id' in read('src/client/Bootstrap.client.luau'), 'reveal passes the species id'
    import re
    assert not re.search(r'^local (?!function)\w+ *=.*ClassBadge', read('src/client/Bootstrap.client.luau'), re.M), 'no new Bootstrap top-level local'
    pc = read('src/shared/PreviewCamera.luau')
    assert 'PreviewCamera.facing' in pc and 'roleOf' in pc and 'PreviewCamera.direction(facing' in pc, 'reveal model faces the camera'
    assert 'Vector3.new(0, 0, -1)' in pc and 'MotionEnabled' in pc, 'default -Z facing, wobble only with motion'
    print('class picker wiring ok')
raise SystemExit(r.returncode)
