"""BD-1025: how long does a fight take? Prints bites and seconds BEFORE and AFTER the 2026-10-18 speed-up (offline, no Studio).

  python tools/combat_fight_time.py --runner C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe

Uses the real CombatStats/CombatConfig formulas (docs/101). Bites = ceil(target HP / one bite). Seconds = (bites - 1) x cooldown,
because the first bite lands at once. Perfect hit rate, no regen, no dodge, so real fights are a bit longer.
BEFORE = cooldown 0.9 s and wild HP x1.0 (the old numbers, written here on purpose). AFTER = the numbers now in CombatConfig.
"""
from combat_harness import run
BODY = r'''
local OLD={cd=0.9, wild=1.0}
local NEW={cd=Cfg.BiteCooldownSeconds, wild=Cfg.WildHpX}
local names={"Ground","Water","Fly","Armored"}
local sMid, sBig = Stats.scale(155), Stats.scale(250) -- wild predators have score 60..250 (NpcPredatorRules.Config)
-- player of class cls (size ps) bites a wild predator (size ws). All wild species today are Ground (NpcPredatorRules.Config.Species).
local function wild(cls, ps, ws, v)
  local hp=Stats.maxHp("Ground", ws, v.wild)
  local bites=math.ceil(hp/Stats.hit(cls, ps, "Ground", ws, 0, 1))
  return hp, bites, (bites-1)*v.cd
end
local function pvp(cls, s, v)
  local bites=math.ceil(Stats.maxHp(cls, s)/Stats.hit(cls, s, cls, s, 0, 1))
  return bites, (bites-1)*v.cd
end
print("EVEN fight: player (each class) bites a wild Ground predator of the same size (s="..string.format("%.2f",sMid)..")")
print("player    wild HP before->after   bites before->after   seconds before->after")
for _,c in names do
  local h0,b0,t0=wild(c,sMid,sMid,OLD); local h1,b1,t1=wild(c,sMid,sMid,NEW)
  print(string.format("%-8s  %3d -> %3d          %2d -> %2d             %4.1f -> %4.1f",c,h0,h1,b0,b1,t0,t1))
end
print("SMALL vs BIG: new player (s=1) against the biggest wild predator (s="..string.format("%.2f",sBig)..")")
for _,c in names do
  local h0,b0,t0=wild(c,1,sBig,OLD); local h1,b1,t1=wild(c,1,sBig,NEW)
  print(string.format("%-8s  %3d -> %3d          %2d -> %2d             %4.1f -> %4.1f",c,h0,h1,b0,b1,t0,t1))
end
print("PLAYER vs PLAYER, even fight at s=1 (players keep full HP; only the bite cooldown changed)")
for _,c in names do
  local b0,t0=pvp(c,1,OLD); local b1,t1=pvp(c,1,NEW)
  print(string.format("%-8s  bites %2d -> %2d       seconds %4.1f -> %4.1f",c,b0,b1,t0,t1))
end
-- BD-1025 part 2 (owner 2026-10-18): the SIZE DIFFERENCE R = bigger z / smaller z (z = 1 + growth / 50, 1..16) sets the bites.
-- Base fight: Ground vs Ground, both at combat scale 1.26 (so only R changes). Wild = wild predator HP (x WildHpX), Player = full HP.
local base=Stats.hit("Ground",sMid,"Ground",sMid,0,1)
local function bigger(hp,R) return math.ceil(Stats.bigBites(hp/base,R)-1e-6) end
local function smaller(hp,R) return math.ceil(hp/math.max(base*Stats.smallHitX(R),Cfg.MinHit)-1e-6) end
local hpWild, hpPlayer = Stats.maxHp("Ground",sMid,Cfg.WildHpX), Stats.maxHp("Ground",sMid)
print("")
print("SIZE DIFFERENCE R (1 = same size; "..Cfg.OneShotRatio.." = fresh dino vs a capped one; 100 vs 800 growth = R "..string.format("%.1f",Stats.sizeRatio(800,100))..")")
print("BIGGER hits SMALLER: bites (seconds)            SMALLER hits BIGGER: bites (seconds)")
print("R      vs wild        vs player                 vs wild         vs player")
for _,R in {1,1.5,2,3,5,8,12,Cfg.OneShotRatio,20} do
  local rr=math.min(R,Cfg.OneShotRatio*1.0)
  local a,b,c,d=bigger(hpWild,rr),bigger(hpPlayer,rr),smaller(hpWild,R),smaller(hpPlayer,R)
  local cd=Cfg.BiteCooldownSeconds
  print(string.format("%-5.1f  %2d (%4.1f s)    %2d (%4.1f s)            %3d (%5.1f s)    %3d (%5.1f s)",R,a,(a-1)*cd,b,(b-1)*cd,c,(c-1)*cd,d,(d-1)*cd))
end
print("(a wild predator keeps its normal bite on players and ignores players more than "..Cfg.WildMaxSizeRatio.."x smaller or bigger)")
print("Damage the player takes from a wild bite: unchanged (wild cooldown 2.5 s, at most 2 bites per chase, HP of players unchanged)")
'''
run(BODY,'fight_time')
