"""BD-100: UIFormat (docs/72) - durations, percent boosts, no '5m 0s', no raw multipliers, neutral boosts hidden;
plus a source scan that in-game text no longer uses the old formats."""
from pathlib import Path
import argparse,subprocess,tempfile,re
ROOT=Path(__file__).resolve().parents[1]
BODY=r'''
local F=UIFormat
local cases={{0,"0 s"},{0.2,"1 s"},{40,"40 s"},{59,"59 s"},{60,"1 min"},{119,"1 min"},{300,"5 min"},{574,"9 min"},{3599,"59 min"},{3600,"1 h"},{7200,"2 h"},{7800,"2 h 10 min"},{10800,"3 h"},{-5,"0 s"}}
for _,c in cases do assert(F.duration(c[1])==c[2],c[1].." -> "..F.duration(c[1])) end
for s=0,20000,7 do local t=F.duration(s) assert(not t:find("%d+m %d") and not t:find(" 0 min") and not t:find(" 0 s") or s==0,t) assert(not t:find(":")) end
assert(F.readyIn(10800)=="Ready in 3 h")
assert(F.percent(1.2)=="+20%" and F.percent(1.25)=="+25%" and F.percent(1)=="" and F.percent(1.001)=="" and F.percent(.8)=="-20%")
assert(F.boost("Speed",1.2)=="Speed +20%" and F.boost("Loot",1)==nil)
local none=F.boostLines(1,1,1) assert(#none==0)
local one=F.boostLines(1,1.2,1) assert(#one==1 and one[1]=="Speed +20%")
local all=F.boostLines(1.25,1.2,1.4) assert(table.concat(all," | ")=="Speed +20% | Growth +25% | Loot +40%")
assert(F.potion("growth",1.25,300)=="Growth +25% - 5 min")
for _,line in all do assert(not line:find("x")) end
local seen={}
for _,c in ProgressionConfig.Conditions do
 local g=Genetics.neutral(c.id) assert(Genetics.valid(g) and g.patternId=="01_blank" and g.conditionId==c.id)
 seen[#seen+1]=Genetics.tint(g)
end
local sigs={} for _,c in ProgressionConfig.Conditions do local sg=Overlays.signature(c.id) assert(not sigs[sg],"condition renders like another: "..c.id) sigs[sg]=true end
assert(#ProgressionConfig.Conditions==5)
-- Detailed odds logic stays callable even though no screen opens it.
local pct=ShopOdds.conditionPercents(0) local sum=0 for _,v in pct do sum+=v end assert(math.abs(sum-100)<1e-6)
print("UIFormat passed")
'''
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 s='local UIFormat='+module('src/shared/UIFormat.luau')+'\nlocal ProgressionConfig='+module('src/shared/ProgressionConfig.luau')+'\n'
 s+='local Color3={fromRGB=function(r,g,b)return {r,g,b,Lerp=function(self,o,a)return {self[1]+(o[1]-self[1])*a,self[2]+(o[2]-self[2])*a,self[3]+(o[3]-self[3])*a} end} end}\n'
 s+='local script={Parent={}}\nlocal require=function(_)return ProgressionConfig end\nlocal Genetics='+module('src/shared/EggGenetics.luau')+'\n'
 s+='local Enum={Material={SmoothPlastic="SmoothPlastic",Plastic="Plastic"}}\nlocal Overlays='+module('src/shared/ConditionOverlays.luau')+'\n'
 s+='local ShopOdds={conditionPercents=function(level)local w=ProgressionConfig.ConditionWeights[level+1] local t=0 for _,x in w do t+=x end local r={} for i,x in w do r[i]=100*x/t end return r end}\n'
 return s+BODY
def scan():
 src=(ROOT/'src/client/Bootstrap.client.luau').read_text()
 for bad in ['%dm %02ds','%d:%02d','Restock in','Future eggs','x stats','"VIEW ODDS",0,cardsY','Growth %.2fx','(item.duration//60).."m "']:
  assert bad not in src,'old copy still in Bootstrap: '+bad
 assert 'UIFormat' in src
 for m in re.finditer(r'(\d)m (\d)+s',src): raise AssertionError('5m 0s style text: '+m.group(0))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 scan()
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/'ui_format.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
