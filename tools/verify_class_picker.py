"""BD-423: species picker shows class + feel hint (ClassInfo), and class movement has its own flag (ClassMovementEnabled)."""
import argparse, subprocess, tempfile
from pathlib import Path
import rehearsal_env
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
assert(Cfg.ClassMovementEnabled==false and Cfg.CombatEnabled==false,"the committed Config has the class movement and combat flags off")
for _,c in M.ClassMovement.ClassNames do assert(CI.Labels[c] and CI.Hints[c],c) end
-- Class badge (owner 2026-10-18): the owner's 4 icons are bound and the class word is the label; NO one-letter label exists any more.
assert(CI.Letters==nil,"the letter badge (G / W / F / A) is gone")
assert(CI.Labels.Ground=="Ground" and CI.Labels.Water=="Water" and CI.Labels.Fly=="Fly" and CI.Labels.Armored=="Armored","owner words")
local slotOf={Ground="class_ground",Water="class_water",Fly="class_flyer",Armored="class_armored"}
local ids,seen={},{}
for c,slot in CI.IconSlots do
  assert(slotOf[c]==slot,"slot for "..c)
  local id=M.AssetSlots.Images[slot]
  assert(id:match("^rbxassetid://%d+$") and not seen[id],"bound and distinct: "..slot) seen[id]=true ids[slot]=id
  for _,word in CI.Labels do assert(#word>1,"never one letter") end
end
for _,c in M.ClassMovement.ClassNames do assert(CI.IconSlots[c],c) end
for id,class in Combat.SpeciesClasses do
  local sp=M.ClassBadge.spec(id)
  assert(sp.class==class and not sp.placeholder and sp.image==ids[CI.IconSlots[class]] and sp.label==CI.Labels[class],id)
end
-- missing or malformed id: clean fallback (the class word on a colour pill), never a crash and never a letter
for _,bad in {"","not an id","rbxassetid://"} do
  M.AssetSlots.Images.class_water=bad
  local w=M.ClassBadge.spec("mosasaurus") assert(w.placeholder and w.image==nil and w.label=="Water","fallback for '"..bad.."'")
end
M.AssetSlots.Images.class_water=ids.class_water
assert(M.ClassBadge.spec(nil).class=="Ground","unknown species is Ground")
local hex={Ground={47,158,68},Fly={30,136,229},Water={15,143,128},Armored={168,100,58}}
for c,h in hex do local k=CI.Colors[c] assert(k and k[1]==h[1] and k[2]==h[2] and k[3]==h[3],"colour "..c) end
for id,class in Combat.SpeciesClasses do assert(M.ClassBadge.spec(id).color==CI.Colors[class],"badge colour "..id) end
print("class picker ok")
'''


def module(n):
    return '(function()\n' + (ROOT / 'src/shared' / f'{n}.luau').read_text(encoding='utf-8') + '\nend)()'


p = argparse.ArgumentParser()
p.add_argument('--runner', required=True)
a = p.parse_args()
src = '\n'.join(['local M={}', 'local Color3={fromRGB=function(r,g,b) return {r,g,b} end,new=function() return 0 end}','local script={Parent=M}', 'local require=function(x) return x end']
                + [f'M.{n}={module(n)}' for n in MODULES] + [BODY])
# docs/152 BD-626: the pin is only a statement about the committed Config; nothing after it depends on the flags being off, so under the
# all-on rehearsal Config the file just continues (the picker, the badge and the class-movement wiring checks all run).
src = rehearsal_env.pin(src, 'assert(Cfg.ClassMovementEnabled==false and Cfg.CombatEnabled==false,"the committed Config has the class movement and combat flags off")',
                        '-- rehearsal: the class movement and combat flags are on in this build', label='class picker flag-off pin')
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
    assert 'ClassInfo.Colors[info.class]' in read('src/shared/ClassBadge.luau'), 'badge uses class colour'
    assert 'PlaceholderFill' not in read('src/shared/ClassBadge.luau'), 'neutral fill gone'
    assert '.Colors[' in read('src/client/Bootstrap.client.luau'), 'picker line uses class colour'
    rp = read('tools/release_profiles.py')
    assert '_flag_off("ClassMovementEnabled"' in rp and 'Rule("ClassMovementEnabled", "set", True' in rp
    cb = read('src/shared/ClassBadge.luau')
    assert 'AssetSlots.image' in cb and 'withLabel' in cb and 'PlaceholderLetter' not in cb and 'Letters' not in cb, 'icon + word, no letter'
    assert 'ClassBadge.create(a.body, r.speciesId, badgeSize, true)' in read('src/client/HatchSequence.luau'), 'reveal shows icon plus word'
    for n in ('ground', 'water', 'fly', 'armored'):
        assert (ROOT / f'resources/ui/v2/icons/class-{n}-v1.png').exists(), n
    reg = read('docs/77-asset-registry.md')
    for slot in ('class_ground', 'class_water', 'class_flyer', 'class_armored'):
        assert f'| {slot} |' in reg, 'docs/77 line for ' + slot
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
