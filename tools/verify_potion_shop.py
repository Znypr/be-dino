"""BD-051 rotating Potion Shop: window math, determinism, weights/stock bounds and purchase rules.
Runs the real ProgressionConfig/ProgressionRules in Luau. Transaction idempotency/reconnect against the
profile repository is covered in tools/verify_progression.py.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
BODY=r'''
local Shop=ProgressionConfig.PotionShop
-- Window math: 2 minute rotation, boundary-exact.
assert(Shop.PeriodSeconds==120)
assert(Rules.shopWindow(0)==0 and Rules.shopWindow(119.99)==0 and Rules.shopWindow(120)==1 and Rules.shopWindow(240.5)==2)
assert(Rules.shopEndsAt(0)==120 and Rules.shopEndsAt(5)==720)
-- Determinism: same window -> identical offers (any server, any reconnect); windows rotate.
local function key(window) local t={} for _,o in Rules.shopOffers(window) do table.insert(t,o.id..":"..o.stock) end return table.concat(t,",") end
local distinct={}
for w=14000000,14000400 do
 assert(key(w)==key(w))
 distinct[key(w)]=true
end
local count=0 for _ in distinct do count+=1 end
assert(count>20,"offers must rotate")
-- Catalog (docs/68): 12 potions, 5 rarities, valid fields, legacy ids kept, price rises with rarity.
assert(#ProgressionConfig.Potions==12,"12-potion catalog")
local rank={} for i,r in Shop.Rarities do rank[r]=i end
assert(#Shop.Rarities==5 and Shop.OfferCount==6)
local seenIds,perRarity,kinds={}, {}, {}
for _,item in ProgressionConfig.Potions do
 assert(not seenIds[item.id] and item.id==item.kind.."_"..string.lower(item.rarity),"id/kind/rarity naming "..item.id) seenIds[item.id]=true
 assert(rank[item.rarity] and Shop.RarityWeights[item.rarity]>0 and Shop.StockWeights[item.rarity],"rarity config "..item.id)
 assert(item.name~="" and item.duration>=300 and item.duration%30==0 and item.multiplier>1 and item.price>0 and item.price%1==0)
 assert(table.find({"speed","growth","loot"},item.kind),"effect family "..item.id)
 perRarity[item.rarity]=(perRarity[item.rarity] or 0)+1 kinds[item.kind]=true
end
for _,id in {"speed_common","speed_rare","speed_legendary","growth_common","growth_rare","growth_legendary"} do assert(seenIds[id],"legacy potion id kept: "..id) end
for _,r in Shop.Rarities do assert((perRarity[r] or 0)>=2,"every rarity has potions: "..r) end
assert(kinds.speed and kinds.growth and kinds.loot)
-- Price ordering: strictly higher for every higher rarity (globally, so no cheap rare undercuts a common), and per effect family.
local lo,hi={}, {}
for _,item in ProgressionConfig.Potions do
 lo[item.rarity]=math.min(lo[item.rarity] or math.huge,item.price) hi[item.rarity]=math.max(hi[item.rarity] or 0,item.price)
end
for i=2,#Shop.Rarities do assert(hi[Shop.Rarities[i-1]]<lo[Shop.Rarities[i]],"price bands overlap at "..Shop.Rarities[i]) end
for _,a in ProgressionConfig.Potions do for _,b in ProgressionConfig.Potions do
 if a.kind==b.kind and rank[a.rarity]<rank[b.rarity] then assert(a.price<b.price and a.duration<=b.duration and a.multiplier<b.multiplier,"scaling "..a.id.." < "..b.id) end
end end
-- Bounds: 6 distinct potions per window, only configured potions, stock 1..3 (Epic/Legendary exactly 1), not all offered at once.
local stockCount={0,0,0}
local appear={}
local rarityCount={}
local legendaryWindows,windowsWithEpicOrBetter=0,0
local windows=30000
local rotates={}
for w=1,windows do
 local offers=Rules.shopOffers(w*7919)
 assert(#offers==Shop.OfferCount and #offers<#ProgressionConfig.Potions)
 local seen={}
 local top=false
 for _,o in offers do
  local item=Rules.item(ProgressionConfig.Potions,o.id)
  assert(not seen[o.id] and item) seen[o.id]=true
  assert(o.stock>=1 and o.stock<=Shop.MaxStock and o.stock%1==0)
  if item.rarity=="Epic" or item.rarity=="Legendary" then assert(o.stock==1,"epic/legendary stock is 1") end
  if item.rarity=="Legendary" then top=true end
  stockCount[o.stock]+=1
  appear[o.id]=(appear[o.id] or 0)+1
  rarityCount[item.rarity]=(rarityCount[item.rarity] or 0)+1
 end
 if top then legendaryWindows+=1 end
end
-- Rarity frequency: common most frequent, legendary rarest, strictly monotonic per offer slot.
local order=Shop.Rarities
for i=2,#order do assert(rarityCount[order[i-1]]>rarityCount[order[i]],"rarity frequency "..order[i]) end
assert(rarityCount.Legendary>0)
assert(legendaryWindows/windows<.2 and legendaryWindows/windows>.02,"legendary is rare but reachable: "..legendaryWindows/windows)
assert(stockCount[1]>stockCount[2] and stockCount[2]>stockCount[3] and stockCount[3]>0)
for _,item in ProgressionConfig.Potions do assert((appear[item.id] or 0)>0,"every potion can appear: "..item.id) end
for _,kind in {"speed","growth"} do
 assert(appear[kind.."_common"]>appear[kind.."_uncommon"] and appear[kind.."_uncommon"]>appear[kind.."_rare"] and appear[kind.."_rare"]>appear[kind.."_legendary"],"per-potion frequency "..kind)
end
assert(appear.growth_rare>appear.growth_epic and appear.growth_epic>appear.growth_legendary)
-- Purchases against a profile.
local function fresh() local p={} local progress=Rules.upgrade(p) progress.crystals=5000 return p,progress end
local now=1200
local window=Rules.shopWindow(now)
local offer=Rules.shopOffers(window)[1]
local other for _,item in ProgressionConfig.Potions do local listed=false for _,o in Rules.shopOffers(window) do if o.id==item.id then listed=true end end if not listed then other=item end end
local price=Rules.item(ProgressionConfig.Potions,offer.id).price
local p,progress=fresh()
local id=offer.id.."@"..window
assert(Rules.valid(progress))
for i=1,offer.stock do assert(Rules.apply(p,"buyPotion",id,now,false)) assert(Rules.valid(progress)) end
assert(progress.potions[offer.id]==offer.stock and progress.crystals==5000-price*offer.stock)
local ok,status=Rules.apply(p,"buyPotion",id,now,false)
assert(not ok and status=="sold_out" and progress.crystals==5000-price*offer.stock and Rules.shopRemaining(progress,window,offer.id)==0)
ok,status=Rules.apply(p,"buyPotion",other.id.."@"..window,now,false) assert(not ok and status=="not_offered")
ok,status=Rules.apply(p,"buyPotion",offer.id,now,false) assert(not ok and status=="window_required")
ok,status=Rules.apply(p,"buyPotion","fake@"..window,now,false) assert(not ok and status=="unknown_item")
ok,status=Rules.apply(p,"buyPotion",offer.id.."@"..(window-1),now,false) assert(not ok and status=="stale_window")
ok,status=Rules.apply(p,"buyPotion",offer.id.."@"..(window+1),now,false) assert(not ok and status=="stale_window")
local nextNow=Rules.shopEndsAt(window)
ok,status=Rules.apply(p,"buyPotion",id,nextNow,false) assert(not ok and status=="stale_window")
-- Stock resets in a new window; old counters are replaced.
local nextOffer=Rules.shopOffers(window+1)[1]
assert(Rules.apply(p,"buyPotion",nextOffer.id.."@"..(window+1),nextNow,false))
assert(progress.shop.window==window+1 and progress.shop.bought[nextOffer.id]==1)
assert(Rules.shopRemaining(progress,window+1,nextOffer.id)==nextOffer.stock-1)
-- Insufficient crystals / full inventory do not consume stock.
local poor,poorProgress=fresh() poorProgress.crystals=price-1
ok,status=Rules.apply(poor,"buyPotion",id,now,false) assert(not ok and status=="insufficient_crystals" and poorProgress.shop==nil)
local full,fullProgress=fresh() fullProgress.potions[offer.id]=999
ok,status=Rules.apply(full,"buyPotion",id,now,false) assert(not ok and status=="inventory_full" and fullProgress.shop==nil)
-- Rotation never removes owned potions; use is independent of the offer list.
local owner,ownerProgress=fresh() ownerProgress.potions[other.id]=1
assert(Rules.apply(owner,"usePotion",other.id,now,false) and ownerProgress.potions[other.id]==0)
-- Persistence validation.
local base={crystals=0,auras={},potions={},buffs={},equippedAura=""}
local function withShop(shop) local c=table.clone(base) c.shop=shop return c end
assert(not Rules.valid(withShop({window=-1,bought={}})))
assert(not Rules.valid(withShop({window=3,bought={fake=1}})))
assert(not Rules.valid(withShop({window=3,bought={speed_common=9}})))
assert(not Rules.valid(withShop({window=3,bought={speed_common=4}})))
assert(Rules.valid(withShop({window=3,bought={speed_common=2,loot_epic=1}})) and Rules.valid(base))
-- Migration: a profile saved before the 12-potion catalog (old ids, old shop record, active buff) stays valid and usable.
local old={crystals=40,auras={},equippedAura="",potions={speed_common=2,growth_rare=1,growth_legendary=1},buffs={speed={id="speed_rare",expiresAt=900}},shop={window=5,bought={speed_common=3,growth_rare=1}}}
assert(Rules.valid(old))
local legacyProfile={progression=table.clone(old)}
local migrated=Rules.upgrade(legacyProfile)
assert(migrated.potions.speed_common==2 and migrated.potions.growth_legendary==1 and migrated.buffs.speed.id=="speed_rare" and migrated.shop.bought.speed_common==3)
assert(Rules.apply(legacyProfile,"usePotion","growth_legendary",100,false) and migrated.buffs.growth.expiresAt==1000)
assert(Rules.valid(migrated))
local loot=select(3,Rules.multipliers({buffs={loot={id="loot_epic",expiresAt=500}},auras={},potions={},equippedAura=""},"compy",nil,100))
assert(math.abs(loot-1.4)<1e-9)
print("Potion shop passed: 12-potion/5-rarity catalog, price ordering, 120s windows, 6 deterministic offers, rarity frequency, stock bounds, stale/sold-out/not-offered rules, stock reset, migration and validation")
'''
def script():
 s='local ProgressionConfig='+module('src/shared/ProgressionConfig.luau')+'\n'
 s+='local script={Parent={ProgressionConfig="ProgressionConfig"}}\nlocal require=function(_)return ProgressionConfig end\nlocal Genetics='+module('src/shared/EggGenetics.luau')+'\n'
 s+='local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}\nlocal require=function(id)return if id=="Genetics" then Genetics else ProgressionConfig end\nlocal Rules='+module('src/shared/ProgressionRules.luau')+'\n'
 return s+BODY
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/'potion_shop.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
