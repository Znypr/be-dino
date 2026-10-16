"""BD-423: species picker shows class + feel hint (ClassInfo), and class movement has its own flag (ClassMovementEnabled)."""
import argparse, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['Config', 'ProgressionConfig', 'CombatConfig', 'ClassMovement', 'ClassInfo']
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
print("class picker ok")
'''


def module(n):
    return '(function()\n' + (ROOT / 'src/shared' / f'{n}.luau').read_text(encoding='utf-8') + '\nend)()'


p = argparse.ArgumentParser()
p.add_argument('--runner', required=True)
a = p.parse_args()
src = '\n'.join(['local M={}', 'local script={Parent=M}', 'local require=function(x) return x end']
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
    print('class picker wiring ok')
raise SystemExit(r.returncode)
