"""BD-172 colour growth bonus: tier ladder, double-colour sums, cap, junk input (src/shared/ColourBonus.luau)."""
import argparse, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def module(path): return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'
BODY = r'''
local function g(a,b) return {primaryColorId=a,secondaryColorId=b} end
local P=function(a,b) return Bonus.percent(Progression.EggColors,g(a,b)) end
assert(P("white","white")==0 and P("blue","blue")==0,"Common colours give 0")
assert(P("green","green")==2,"Uncommon x2")
assert(Bonus.percent(Progression.EggColors,{primaryColorId="green"})==2,"missing secondary counts as a double")
assert(P("black","white")==5,"single black = owner 5%")
assert(P("black","black")==10,"double black = owner 10%")
assert(P("red","black")==10,"capped at 10")
assert(P("violet","gold")==7 and P("teal","pink")==4,"mixed sums")
assert(P("nope","black")==5 and P("nope","nope")==0,"unknown colours are 0")
assert(Bonus.percent(Progression.EggColors,nil)==0 and Bonus.percent(nil,g("black","black"))==0 and Bonus.percent({}, "x")==0,"junk input is 0")
local max=0
for _,a in Progression.EggColors do for _,b in Progression.EggColors do
  local p=P(a.id,b.id); assert(p>=0 and p<=Bonus.MaxPercent); max=math.max(max,p)
  assert(math.abs(Bonus.multiplier(Progression.EggColors,g(a.id,b.id))-(1+p/100))<1e-9)
end end
assert(max==10)
assert(Bonus.text(Progression.EggColors,g("red","white"))=="Colour bonus +5% growth")
assert(Bonus.text(Progression.EggColors,g("white","white"))==nil)
local gained=500*Config.GrowthPerFood
assert(gained*Bonus.multiplier(Progression.EggColors,g("black","black"))<=gained*1.1+1e-9)
print("Colour bonus passed: Common 0 .. Mythic 5 per colour, sum of two, cap 10, max multiplier 1.10")
'''
def script():
    return ('local Curve=' + module('src/shared/RarityCurve.luau') + '\nlocal Config=' + module('src/shared/Config.luau')
        + '\nlocal Progression=' + module('src/shared/ProgressionConfig.luau')
        + '\nlocal script={Parent={RarityCurve=Curve}}\nlocal require=function(_) return Curve end\nlocal Bonus=' + module('src/shared/ColourBonus.luau') + '\n' + BODY)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--runner', required=True); args = parser.parse_args()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'colour.luau'; path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end=''); print(result.stderr, end=''); raise SystemExit(result.returncode)
