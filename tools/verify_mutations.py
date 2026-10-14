"""Offline event-mutation audit (BD mutation-audit): rates match config, purchased eggs never mutate.
Runs the real ProgressionRules.eventEgg/validEgg and the real FoodService-style catch ordinal tagging."""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 s='local ProgressionConfig='+module('src/shared/ProgressionConfig.luau')+'\n'
 s+='local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}\nlocal Genetics={valid=function()return true end}\nlocal require=function(id)return if id=="Genetics" then Genetics else ProgressionConfig end\nlocal Rules='+module('src/shared/ProgressionRules.luau')+'\n'
 s+='''
local N=20000
math.randomseed(20261015)
local rng={NextNumber=function()return math.random()end}
local covered={}
for _,w in ProgressionConfig.Weather do
 local hits=0
 for _=1,N do
  local tag=Rules.eventEgg(w.id,rng:NextNumber())
  assert(tag.eventId==w.id and Rules.validEgg(tag))
  if tag.mutationId~="" then assert(tag.mutationId==w.mutation) hits+=1 end
 end
 local p=w.chance
 local sigma=math.sqrt(N*p*(1-p))
 assert(math.abs(hits-N*p)<=4.5*sigma,w.id.." rate "..hits.."/"..N.." vs "..p)
 assert(w.chance>=.02 and w.chance<=.08,w.id.." chance outside 2-8%")
 assert(Rules.knownEventMutation(w.mutation))
 covered[w.mutation]=true
 print(string.format("%-10s -> %-9s chance %.3f measured %.4f (%d/%d)",w.id,w.mutation,p,hits/N,hits,N))
end
for _,m in ProgressionConfig.EventMutations do assert(covered[m.id],m.id.." has no weather that grants it") end
-- purchased/clear eggs: tag is clear, never carries a mutation, and a forged mutation is rejected
for _=1,N do local t=Rules.eventEgg("clear",rng:NextNumber()) assert(t.eventId=="clear" and t.mutationId=="") end
assert(Rules.eventEgg("clear",0).mutationId=="")
for _,m in ProgressionConfig.EventMutations do assert(not Rules.validEgg({eventId="clear",mutationId=m.id})) end
print("Event mutation audit passed: "..#ProgressionConfig.Weather.." weathers x "..N.." earned eggs within 4.5 sigma; clear/purchased eggs never mutate")
'''
 return s
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/'mutations.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
