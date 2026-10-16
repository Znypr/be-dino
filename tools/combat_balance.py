"""Prints the combat balance report (docs/101 section 17): scenarios, class matrix. Offline simulation only."""
from combat_harness import run
BODY = r'''
local function r(w,t,al,fd) return string.format("%s t=%.1f surv=%d firstDown=%.1f",w,t,al,fd or -1) end
print("1v1 s1 vs s4:",r(fight(team(1,"Ground",S1),team(1,"Ground",S4),true)))
print("hits for s4 to kill s1:",math.ceil(Stats.maxHp("Ground",1)/Stats.hit("Ground",S4,"Ground",S1,0,1)))
for _,n in {3,6} do
  for _,name in {{"s2",S2},{"s3",S3},{"s4",S4}} do
    print(n.." small vs "..name[1],r(fight(team(n,"Ground",S1),team(1,"Ground",name[2]),true)))
  end
end
local names={"Ground","Fly","Water","Armored"}
-- equal size 1v1: hits each side needs (ceil(HP / hit)); fewer wins, equal is a draw (first strike decides)
local function hitsToKill(x,y,sz) return math.ceil(Stats.maxHp(y,sz)/Stats.hit(x,sz,y,sz,0,1)) end
for _,s in {S1,S2,S4} do
  print("matrix s="..string.format("%.2f",s).." (row vs column: result, hits row needs / hits column needs)")
  for _,x in names do
    local row={}
    for _,y in names do
      local a,b=hitsToKill(x,y,s),hitsToKill(y,x,s)
      row[#row+1]=(if x==y then "      =      " else string.format("%s %2d/%2d",(if a<b then "W" elseif a>b then "L" else "D"),a,b))
    end
    print(string.format("%-8s",x),table.concat(row," "))
  end
end
print("team-up by class (smalls s=1 of class X vs one big of class X; then cross: smalls Ground vs big of class Y)")
for _,c in names do
  for _,n in {1,3,6} do print(c,n.."v s4",r(fight(team(n,c,S1),team(1,c,S4),true))) end
end
for _,c in names do print("Ground x6 vs big "..c.." s4",r(fight(team(6,"Ground",S1),team(1,c,S4),true))) end
for _,c in names do local s=1.0
  print(c,"hp",math.floor(Stats.maxHp(c,1)),"hit",string.format("%.1f",Stats.damage(c,1,0)),"speed",Cfg.Classes[c].speedX,"effHPvsGround",math.floor(Stats.maxHp(c,1)/Cfg.Classes[c].damageTakenX))
end
'''
run(BODY,'balance')
