"""BD-246: every species has a class (config), registry agrees, owner class decisions, multipliers, FLY hover cap, flag-off default."""
import argparse, re, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['Config', 'ProgressionConfig', 'CombatConfig', 'ClassMovement']

BODY = r'''
local C,CM=M.CombatConfig,M.ClassMovement
assert(C.Enabled==false and CM.Enabled==false,"flags default OFF")
for sp,cl in C.SpeciesClasses do assert(C.Classes[cl],sp.." has a known class") end
for _,sp in M.Config.SpeciesOrder do assert(C.SpeciesClasses[sp],sp.." is classed") end
for _,sp in {"ankylosaurus","sauropelta","styracosaurus"} do assert(C.SpeciesClasses[sp]=="Armored",sp) end
assert(C.SpeciesClasses.kentrosaurus=="Ground" and C.SpeciesClasses.elasmosaurus=="Ground","owner: Kentrosaurus and Elasmosaurus are Ground")
assert(#C.SecretSpecies==7,"BD-604: five silly birds, Budgiesaurus and Foxosaurus")
assert(C.SpeciesClasses.penguin=="Water" and C.SpeciesClasses.budgiesaurus=="Fly" and C.SpeciesClasses.foxosaurus=="Ground","SS5 classes")
for _,sp in C.SecretSpecies do assert(C.SpeciesClasses[sp],sp.." secret bird classed") end
local cap=CM.rules("Fly").jump.heightCap
assert(cap>=6 and cap<=7,"fly hover cap about 6 studs")
for _,c in CM.ClassNames do assert(CM.walkSpeed(c)==M.Config.WalkSpeed*C.Classes[c].speedX and CM.walkSpeed(c)>0,c) end
assert(CM.rules("Water").jump.powerX==0 and CM.rules("Armored").jump.powerX<1 and CM.rules("Fly").jump.powerX>1)
print("classes ok")
'''


def module(name):
    return '(function()\n' + (ROOT / 'src/shared' / f'{name}.luau').read_text(encoding='utf-8') + '\nend)()'


parser = argparse.ArgumentParser()
parser.add_argument('--runner', required=True)
args = parser.parse_args()
parts = ['local M={}', 'local script={Parent=M}', 'local require=function(x) return x end']
parts += [f'M.{n}={module(n)}' for n in MODULES] + [BODY]
reg = (ROOT / 'src/shared/LowPolyDinoAssets.luau').read_text(encoding='utf-8')
cfg = (ROOT / 'src/shared/CombatConfig.luau').read_text(encoding='utf-8')
for name, cls in re.findall(r'(\w+) = \{assetId = \d+, version = "v\d+", scale = [\d.]+, tier = \d, class = "(\w+)"\}', reg):
    m = re.search(rf'\b{name} = "(\w+)"', cfg)
    assert m and m.group(1) == cls, f'{name}: registry {cls} != CombatConfig.SpeciesClasses'
with tempfile.TemporaryDirectory() as d:
    path = Path(d) / 'classes.luau'
    path.write_text('\n'.join(parts), encoding='utf-8')
    r = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
    print(r.stdout, end=''); print(r.stderr, end='')
    raise SystemExit(r.returncode)
