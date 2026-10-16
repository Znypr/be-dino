"""BD-361 / BD-362: server hot paths for 12 players. Pure modules PointGrid (FoodService pickup lookup) and LeaderboardWrites
(OrderedDataStore write gate) run in the pinned Luau runtime, plus static wiring checks of FoodService and Leaderboards.
Not a Studio MicroProfiler run and not the real OrderedDataStore budget: those stay owner steps (docs/111).

    python tools/verify_server_scaling.py --runner /path/to/luau
"""
from pathlib import Path
import argparse, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local PointGrid,W=PG,LW
-- PointGrid equals brute force on 2,400 foods x 12 players, and touches far fewer foods
local seed=11
local function rnd() seed=(seed*1103515245+12345)%2147483648 return seed/2147483648 end
local grid,foods=PointGrid.new(8),{}
for i=1,2400 do local f={x=(rnd()-.5)*1400,z=(rnd()-.5)*1400} foods[i]=f PointGrid.insert(grid,f,f.x,f.z) end
local visited,total=0,0
for tick=1,50 do
 for p=1,12 do
  local px,pz,r=(rnd()-.5)*1400,(rnd()-.5)*1400,2.25+rnd()*2.75
  local brute,fast,seen={}, {}, 0
  for _,f in foods do local dx,dz=f.x-px,f.z-pz if dx*dx+dz*dz<=r*r then brute[f]=true end end
  PointGrid.query(grid,px,pz,r,function(f) seen+=1 local dx,dz=f.x-px,f.z-pz if dx*dx+dz*dz<=r*r then fast[f]=true end end)
  for f in brute do assert(fast[f],"grid missed a food in range") end
  for f in fast do assert(brute[f]) end
  visited+=seen total+=2400
 end
 -- foods relocate: moves must be reflected
 local f=foods[(tick%2400)+1] f.x,f.z=(rnd()-.5)*1400,(rnd()-.5)*1400 PointGrid.move(grid,f,f.x,f.z)
end
assert(visited*50<total,"grid should visit under 2% of the pair checks, got "..visited.."/"..total)
-- remove / negative coords / reinsert
local g=PointGrid.new(8) local a={} PointGrid.insert(g,a,-3,-3) local n=0
PointGrid.query(g,-3,-3,1,function() n+=1 end) assert(n==1)
PointGrid.remove(g,a) n=0 PointGrid.query(g,-3,-3,1,function() n+=1 end) assert(n==0)
PointGrid.insert(g,a,100,100) PointGrid.insert(g,a,-100,-100) n=0 PointGrid.query(g,100,100,2,function() n+=1 end) assert(n==0,"insert moves")

-- LeaderboardWrites: write only on change, throttled play time, failures retried, leave forces play time
local st=W.new()
assert(W.shouldWrite(st,"rarest",1,3,0,false))
assert(not W.shouldWrite(st,"rarest",1,0,0,false) and not W.shouldWrite(st,"rarest",1,0/0,0,false) and not W.shouldWrite(st,"robux",1,-5,0,false))
W.begin(st,"rarest",1,0) -- begin without success (failed write): still due
assert(W.shouldWrite(st,"rarest",1,3,1,false),"a failed write is retried")
W.succeeded(st,"rarest",1,3)
assert(not W.shouldWrite(st,"rarest",1,3,2,false) and not W.shouldWrite(st,"rarest",1,2,2,false),"unchanged or lower value skipped")
assert(W.shouldWrite(st,"rarest",1,4,2,false),"higher value written")
assert(W.shouldWrite(st,"playSeconds",1,100,0,false)) W.begin(st,"playSeconds",1,0) W.succeeded(st,"playSeconds",1,100)
assert(not W.shouldWrite(st,"playSeconds",1,160,60,false),"play time throttled")
assert(W.shouldWrite(st,"playSeconds",1,700,W.PlayInterval+1,false),"play time written after the interval")
assert(W.shouldWrite(st,"playSeconds",1,160,60,true),"leave forces play time")
-- 12 players over a 2 h session: writes per player stay tiny vs 120 minute ticks x 3 boards
local writes,naive=0,0
local s2=W.new()
for minute=1,120 do
 for u=1,12 do
  for _,id in {"rarest","robux","playSeconds"} do
   local v=if id=="playSeconds" then minute*60 elseif id=="rarest" then (if minute==30 then 2 else 1) else 0
   naive+=1
   if W.shouldWrite(s2,id,u,v,minute*60,false) then writes+=1 W.begin(s2,id,u,minute*60) W.succeeded(s2,id,u,v) end
  end
 end
end
print("leaderboard writes in 2 h, 12 players:",writes,"vs",naive,"unthrottled")
assert(writes*10<naive,"at least 10x fewer writes")
W.forget(s2,1) assert(W.shouldWrite(s2,"rarest",1,1,0,false),"forget clears a user")
print("Server scaling passed: grid equals brute force and visits "..string.format("%.2f",visited/total*100).."% of pairs; leaderboard gate "..writes.."/"..naive)
'''

def mod(n): return '(function()\n' + (ROOT / 'src/shared' / f'{n}.luau').read_text(encoding='utf-8') + '\nend)()'

def static():
    food = (ROOT / 'src/server/FoodService.luau').read_text(encoding='utf-8')
    assert 'PointGrid.query' in food and 'hiddenFoods' in food, 'FoodService uses the grid and the hidden set'
    assert 'for _, food in foods do\n                if now < food.readyAt' not in food, 'FoodService no longer walks every food per tick'
    lead = (ROOT / 'src/server/Leaderboards.luau').read_text(encoding='utf-8')
    assert 'Writes.shouldWrite' in lead and 'Writes.forget' in lead, 'Leaderboards gates writes'
    assert 'task.spawn(function()' in lead, 'board writes run in parallel'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--runner', required=True); a = ap.parse_args()
    static()
    code = f'local PG={mod("PointGrid")}\nlocal LW={mod("LeaderboardWrites")}\n{BODY}'
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 's.luau'; p.write_text(code, encoding='utf-8')
        r = subprocess.run([a.runner, str(p)], capture_output=True, text=True)
        print(r.stdout, end=''); print(r.stderr, end='')
        raise SystemExit(r.returncode)
main()
