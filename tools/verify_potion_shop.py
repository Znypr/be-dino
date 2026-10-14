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
-- Bounds: distinct potions, OfferCount offers, stock 1..3, only configured potions.
local stockCount={0,0,0}
local appear={}
local windows=30000
for w=1,windows do
 local offers=Rules.shopOffers(w*7919)
 assert(#offers==Shop.OfferCount)
 local seen={}
 for _,o in offers do
  assert(not seen[o.id] and Rules.item(ProgressionConfig.Potions,o.id)) seen[o.id]=true
  assert(o.stock>=1 and o.stock<=3 and o.stock%1==0)
  stockCount[o.stock]+=1
  appear[o.id]=(appear[o.id] or 0)+1
 end
end
assert(stockCount[1]>stockCount[2] and stockCount[2]>stockCount[3] and stockCount[3]>0)
assert(math.abs(stockCount[1]/(windows*Shop.OfferCount)-.6)<.03)
assert(appear.speed_common>appear.speed_rare and appear.speed_rare>appear.speed_legendary and appear.growth_common>appear.growth_rare and appear.growth_rare>appear.growth_legendary)
for _,item in ProgressionConfig.Potions do assert((appear[item.id] or 0)>0,"every potion can appear: "..item.id) end
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
assert(Rules.valid(withShop({window=3,bought={speed_common=2}})) and Rules.valid(base))
print("Potion shop passed: 120s windows, deterministic offers, distinct/bounded stock, rarity+stock weights, stale/sold-out/not-offered rules, stock reset and validation")
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
