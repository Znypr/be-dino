"""Offline event-mutation audit (BD mutation-audit): rates match config, purchased eggs never mutate.
Runs the real ProgressionRules.eventEgg/validEgg and the real FoodService-style catch ordinal tagging."""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 s='local ProgressionConfig='+module('src/shared/ProgressionConfig.luau')+'\n'
 s+='local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}\nlocal Genetics={valid=function()return true end}\nlocal Rules\nlocal require=function(id)return if id=="Genetics" then Genetics elseif id=="Rules" then Rules else ProgressionConfig end\nRules='+module('src/shared/ProgressionRules.luau')+'\n'
 s+='''
local Tags=(function() local script={Parent={ProgressionRules="Rules"}}
'''+(ROOT/'src/shared/RunEggTags.luau').read_text()+'''
end)()
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
-- BD-236: FoodService catch glue (RunEggTags): one roll per earned egg, never for non-egg catches, clear weather, or past the cap
local calls=0
local function roll() calls+=1 return rng:NextNumber() end
do
 local ev,added=Tags.apply({},"clear",0,40,roll) assert(#ev==0 and added==0 and calls==0,"clear weather must not roll or tag")
 for _,w in ProgressionConfig.Weather do
  local ev2,a2=Tags.apply({},w.id,7,7,roll) assert(#ev2==0 and a2==0 and calls==0,"a catch adding no egg must not roll")
  local ev3,a3=Tags.apply({},w.id,9,5,roll) assert(a3==0 and calls==0)
 end
 assert(Tags.nextScore(3,2,5000,40)==5 and Tags.nextScore(38,9,5000,40)==40 and Tags.nextScore(40,3,5000,40)==40 and Tags.nextScore(0,99999,30,40)==30)
 local M=60000
 for _,w in ProgressionConfig.Weather do
  local hits,total=0,0
  for _=1,M/20 do
   -- a run: 20 sequential catch ticks of 1..3 eggs each, tagged incrementally like FoodService, under the per-run cap
   local events,score,before=({}:: any),0,0
   local seen={}
   calls=0
   for _=1,20 do
    local whole=math.random(0,3)
    local after=Tags.nextScore(score,whole,5000,40)
    local tagsBefore=#events
    Tags.apply(events,w.id,score,after,roll)
    assert(#events-tagsBefore==after-score,"one weather tag per earned egg")
    score=after
   end
   assert(calls==score,"exactly one roll per earned egg: "..calls.." vs "..score)
   for _,t in events do
    assert(Rules.validEgg(t) and t.eventId==w.id and (t.mutationId=="" or t.mutationId==w.mutation),"tag has its own weather")
    assert(t.n>=1 and t.n<=score and t.n<=40 and not seen[t.n],"tag once per catch ordinal within the cap")
    seen[t.n]=true
   end
   for _,t in events do if t.mutationId~="" then hits+=1 end end
   total+=score
  end
  local p=w.chance
  local sigma=math.sqrt(total*p*(1-p))
  assert(math.abs(hits-total*p)<=4.5*sigma,w.id.." glue rate "..hits.."/"..total.." vs "..p)
 end
end
print("Event mutation audit passed: "..#ProgressionConfig.Weather.." weathers x "..N.." earned eggs within 4.5 sigma; clear/purchased eggs never mutate")
'''
 return s
def scans():
  tags=chr(10).join(l.split('--')[0] for l in (ROOT/'src/shared/RunEggTags.luau').read_text().splitlines());food=(ROOT/'src/server/FoodService.luau').read_text();repo=(ROOT/'src/server/ProfileRepository.luau').read_text()
  assert 'RunEggTags.apply(' in food and 'RunEggTags.nextScore(' in food and 'eventEgg(' not in food,'FoodService must use the tested RunEggTags glue only'
  for word in ('condition','Cracked','genes','hatchSuccess'):
   assert word not in tags,'RunEggTags must not know the egg condition: '+word
  h=repo.index('local function applyHatch');body=repo[h:h+2500]
  assert body.index('outcome.failed=')<body.index('outcome.count=0')<body.index('species.events'),'Cracked failure (count 0) must come before any credit'
  print('Source scans passed: FoodService uses RunEggTags; tag is condition-blind; a failed Cracked egg credits nothing (docs/99 G2)')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 with tempfile.TemporaryDirectory() as d:
  scans()
  path=Path(d)/'mutations.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
