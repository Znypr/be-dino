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
print("Damage the player takes from a wild bite: unchanged (wild cooldown 2.5 s, at most 2 bites per chase, HP of players unchanged)")
'''
run(BODY,'fight_time')
