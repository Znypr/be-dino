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
-- BD-1036: the colour rarity a dino shows is the rarer of its two colours.
local R=function(a,b) return Bonus.rarity(Progression.EggColors,g(a,b)) end
assert(R("white","white")=="Common" and R("blue","white")=="Common" and R("green","white")=="Uncommon" and R("white","green")=="Uncommon")
assert(R("pink","green")=="Rare" and R("teal","teal")=="Rare" and R("gold","pink")=="Epic" and R("violet","violet")=="Legendary")
assert(R("red","white")=="Mythic" and R("white","black")=="Mythic" and R("black","red")=="Mythic","a Mythic accent OR main colour makes the dino Mythic")
assert(Bonus.rarity(Progression.EggColors,{primaryColorId="violet"})=="Legendary","missing secondary counts as the primary")
assert(R("nope","nope")=="Common" and R("nope","gold")=="Epic" and R("gold","nope")=="Epic","unknown ids count as Common")
assert(Bonus.rarity(nil,g("red","red"))=="Common" and Bonus.rarity(Progression.EggColors,nil)=="Common" and Bonus.rarity({},"x")=="Common")
assert(Curve.rarer("Rare","Epic")=="Epic" and Curve.rarer("Epic","Rare")=="Epic" and Curve.rarer("Mythic","Common")=="Mythic" and Curve.rarer(nil,nil)=="Common" and Curve.rarer("Rare","nope")=="Rare")
for _,a in Progression.EggColors do for _,b in Progression.EggColors do -- never below either colour, symmetric, one of the two
  local r,r2=R(a.id,b.id),R(b.id,a.id) assert(r==r2,"symmetric")
  assert(Curve.index(r)>=Curve.index(a.rarity) and Curve.index(r)>=Curve.index(b.rarity) and (r==a.rarity or r==b.rarity))
end end
print("Colour bonus passed: Common 0 .. Mythic 5 per colour, sum of two, cap 10, max multiplier 1.10; displayed colour rarity = the rarer of two")
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
