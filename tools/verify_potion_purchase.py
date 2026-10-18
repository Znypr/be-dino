"""Potion purchase, end to end (lead Studio check 2026-10-17: "Buy Potion?" -> BUY POTION seemed to do nothing).

Runtime part (pinned Luau, stubs only for Roblox services): the REAL ProgressionService remote handler, the REAL ProfileRepository
in the unpublished-Studio "memory profile" (local preview + test wallet) and the REAL ProgressionRules/Config. Requests are exactly
what the client's confirm button sends (action "buyPotion", id "<potion>@<window>", GUID token, replace=false). Checks:
  * the server answers (token, true, "purchased") and the owner-only state the client reads (ProgressionJson.potions, .shop) changes,
  * the test wallet keeps Crystals at StudioTestCrystals AFTER a purchase (by design: the counter does not move in Studio),
  * busy / duplicate-token retry / stale window / sold out / use-after-buy answers, every catalog potion is buyable and its request id
    fits the remote's 40 character limit.
Static part (the client needs Roblox instances, so it is checked as source): the BUY POTION handler always calls transact() with the
window-stamped id BEFORE it leaves the modal, transact fires the server remote, the result handler and the ProgressionJson listener
both re-render the Potion Shop, the remote names and the allowed-action list agree on both sides.

    python tools/verify_potion_purchase.py --runner /path/to/luau
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[1]


sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402


def module(path):
    return profile_sources.module(path)  # docs/150: ProfileRepository plus the parts it installs


BODY = r'''
local nowTime=1700000030
local clockNow=1000 -- os.clock() seen by ProgressionService (rate limit bucket)
local function copy(t)
 if type(t)~="table" then return t end
 local result={} for k,v in t do result[k]=copy(v) end return result
end
local data={}
local store={UpdateAsync=function(_,key,fn)
 local updated=fn(copy(data[key]))
 if updated==nil then return nil end
 data[key]=copy(updated)
 return copy(updated)
end}
local guid=0
local http={GenerateGUID=function()guid+=1 return "test-"..guid end,JSONEncode=function(_,v)return copy(v) end,JSONDecode=function(_,v)return copy(v) end}
local mutableConfig=table.clone(GameConfig)
mutableConfig.WriteBudgetEnabled=false
GameConfig=mutableConfig
assert(GameConfig.StudioLocalProfilesEnabled==true and GameConfig.StudioTestWalletEnabled==true,"this case models the unpublished Studio memory profile")
local storage={Shared={Config="Config",ProgressionRules="Rules",EggTraits="EggTraits",EggGenetics="Genetics",NestQueue="NestQueue",FtueRules="FtueRules",ProgressionConfig="ProgressionConfig",SettingsModel="SettingsModel",PaidRandomGate="PaidRandomGate"}}
local services={DataStoreService={GetDataStore=function()return store end},HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function()return true end}}
local game={GameId=0,JobId="test",GetService=function(_,id)return services[id] end} -- unpublished place: GameId 0 + Studio = local preview
local task={wait=function()end,spawn=function()end,delay=function()end}
local warns={}
local warn=function(...)table.insert(warns,table.concat({...}," "))end
local os={time=function()return nowTime end,clock=function()return clockNow end,date=os.date}
local Identity=IDENTITY_MODULE
local script={Parent={DinosaurIdentity="Identity"}}
local require=function(id) assert(id=="Identity") return Identity end
local IdentityFusion=IDENTITY_FUSION_MODULE
local FusionOdds=FUSION_ODDS_MODULE
-- Server PrivateState stand-in that also plays the client cache (the real channel is proven by verify_private_state).
local client={cache={},log={}}
local PrivateStateStub={
 set=function(p,k,v) p.attrs[k]=v client.cache[k]=v table.insert(client.log,k) end,
 get=function(p,k) return p.attrs[k] end,forget=function() end}
local script={Parent={RewardMath="Rewards",DinosaurIdentity="Identity",IdentityFusion="IdentityFusion",FusionOdds="FusionOdds",PrivateState="PrivateState",RareHatchService="RareHatchService",CosmeticOwnership="Cosmetic",ObjectiveService="ObjectiveService"}}
local ObjectiveSpy=setmetatable({loads=0},{__index=function() return function() return true end end}) -- docs/152: stands in for the lazily required ObjectiveService when Config.ObjectivesEnabled is on
local rewardSpecies=nil
local NestQueue=NEST_QUEUE_MODULE
local FtueRules=FTUE_RULES_MODULE
local SettingsModel=SETTINGS_MODEL_MODULE
local Rewards=nil
local require=function(id)
 if id=="ObjectiveService" then ObjectiveSpy.loads+=1 return ObjectiveSpy end
 if id=="PrivateState" then return PrivateStateStub end
 if id=="Cosmetic" then return COSMETIC_OWNERSHIP_MODULE end
 if id=="RareHatchService" then return {record=function() end} end
 if id=="FusionOdds" then return FusionOdds end
 if id=="IdentityFusion" then return IdentityFusion elseif id=="Identity" then return Identity elseif id=="Genetics" then return Genetics elseif id=="EggTraits" then return EggTraits elseif id=="ProgressionConfig" then return ProgressionConfig elseif id=="Config" then return GameConfig elseif id=="Rules" then return Rules elseif id=="Rewards" then return Rewards elseif id=="NestQueue" then return NestQueue elseif id=="FtueRules" then return FtueRules elseif id=="SettingsModel" then return SettingsModel end
 if id=="PaidRandomGate" then return PAID_RANDOM_GATE_MODULE end -- BD-532
 error("unexpected module "..tostring(id))
end
local Random={new=function()return {NextNumber=function()return .5 end}end}
local RealRewards=REWARDS_MODULE
Rewards=setmetatable({computeChestReward=function()return {speciesId="raptor",count=1,mutationId="base"}end},{__index=RealRewards})
local Repository=REPO_MODULE

-- The REAL ProgressionService, with the remote events captured instead of replicated.
local remotes,responses={}, {}
local Service
do
 local signal=function()return {Connect=function(self,fn)self.fn=fn end}end
 local Instance={new=function(kind)
  local o
  o={kind=kind,OnServerEvent={Connect=function(_,fn) o.handler=fn end}}
  function o:FireClient(_,...) table.insert(responses,{...}) end
  return setmetatable(o,{__newindex=function(t,k,v) rawset(t,k,v) if k=="Name" then remotes[v]=o end end})
 end}
 local workspace={GetServerTimeNow=function()return nowTime end,SetAttribute=function()end,GetAttribute=function()return nil end}
 local svcShared={ProgressionConfig="ProgressionConfig",ProgressionRules="Rules",ResourceModels="Resources",MovementEnvelope="MovementEnvelope",Config="Config",ClassMovement="ClassMovement",ColourBonus="ColourBonus",WeatherClock="WeatherClock"}
 local svcServices={Players={PlayerAdded=signal(),PlayerRemoving=signal(),GetPlayers=function()return {}end},ReplicatedStorage={Shared=svcShared,BeDinoRemotes={}},Lighting={},HttpService=http}
 local game={GetService=function(_,id)return svcServices[id] end}
 local WeatherClock do
  local script={Parent={ProgressionConfig="ProgressionConfig"}}
  local require=function()return ProgressionConfig end
  WeatherClock=CLOCK_MODULE
 end
 local script={Parent={PrivateState="PrivateState"}}
 local require=function(id)
  if id=="PrivateState" then return PrivateStateStub end
  if id=="ProgressionConfig" then return ProgressionConfig elseif id=="Rules" then return Rules elseif id=="Config" then return GameConfig elseif id=="WeatherClock" then return WeatherClock end
  return {} -- Resources / MovementEnvelope / ClassMovement / ColourBonus are only used by loops that task.spawn (a no-op here) runs
 end
 Service=SERVICE_MODULE
end
Service.start(Repository)
local serverHandler=remotes.ProgressionAction.handler
assert(serverHandler and remotes.ProgressionResult,"the server must create ProgressionAction and ProgressionResult")

local player={Parent=true,UserId=555,Name="LeadTester",attrs={}}
function player:SetAttribute(k,v)self.attrs[k]=v end
function player:GetAttribute(k)return self.attrs[k]end
assert(Repository.load(player))
-- (a) the memory profile starts on the test wallet.
assert(player.attrs.StudioTestWallet==true and client.cache.Crystals==1000000 and client.cache.ProgressionJson.crystals==1000000)

-- What the client does on a confirm click: transact("buyPotion", id.."@"..window, false) -> FireServer(action,id,token,replace).
local pendingToken=nil
local function clientBuy(potionId,windowOverride)
 local window=windowOverride or Rules.shopWindow(nowTime) -- client: ProgressionRules.shopWindow(workspace:GetServerTimeNow())
 local token="client-"..guid guid+=1
 pendingToken=token
 clockNow+=1 -- the real client cannot send two actions inside the server's 0.4 s guard
 local before=#responses
 serverHandler(player,"buyPotion",potionId.."@"..window,token,false)
 assert(#responses==before+1,"the server must always answer a well-formed request (otherwise pendingShop sticks and later buys say 'still processing')")
 local r=responses[#responses]
 assert(r[1]==token,"the result echoes the client's token so pendingShop clears")
 pendingToken=nil
 return r[2],r[3]
end
local function owned(id) return client.cache.ProgressionJson.potions[id] or 0 end

-- First: a common potion with stock >= 2 (so the replace dialog path can own two copies); the window is found by walking forward.
local first,window=nil,nil
for w=Rules.shopWindow(nowTime),Rules.shopWindow(nowTime)+4000 do
 for _,offer in Rules.shopOffers(w) do if not first and offer.stock>=2 then first=offer window=w end end
 if first then break end
end
assert(first,"some window offers a potion with stock >= 2")
nowTime=Rules.shopEndsAt(window-1)
local firstItem=Rules.item(ProgressionConfig.Potions,first.id)
assert(owned(first.id)==0)
local ok,status=clientBuy(first.id)
assert(ok and status=="purchased",tostring(status))
-- (c) the state the "Your potions" list is drawn from has the potion once the delta reaches the client...
assert(owned(first.id)==1 and client.cache.ProgressionJson.shop.window==window and client.cache.ProgressionJson.shop.bought[first.id]==1)
-- ...and ProgressionJson is exactly the attribute the client refreshes on (PrivateState.onChanged("ProgressionJson")).
local sawProgression=false for _,k in client.log do if k=="ProgressionJson" then sawProgression=true end end
assert(sawProgression)
-- (a) test wallet: Crystals is re-pinned after the spend, so the counter staying at 1,000,000 does NOT mean the buy failed.
assert(client.cache.Crystals==1000000 and client.cache.ProgressionJson.crystals==1000000 and Repository.progression(player).crystals==1000000)
-- Re-render source for the Potion Shop header: "Balance after purchase" is computed client-side and never lowers a pinned wallet.
-- Same click twice within the server guard: refused with "busy", nothing bought, token echoed.
serverHandler(player,"buyPotion",first.id.."@"..window,"rapid",false)
assert(responses[#responses][1]=="rapid" and responses[#responses][2]==false and responses[#responses][3]=="busy" and owned(first.id)==1)
-- Client retry (pendingShop > 8 s) re-sends the SAME token: acknowledged, never charged twice.
clockNow+=1
serverHandler(player,"buyPotion",first.id.."@"..window,"client-"..(guid-1),false)
local lastR=responses[#responses]
assert(lastR[2]==true and lastR[3]=="duplicate" and owned(first.id)==1,tostring(lastR[3]))
-- Use it: USE button -> usePotion (replace=false), buff recorded with a future expiry.
clockNow+=1
serverHandler(player,"usePotion",first.id,"use-1",false)
lastR=responses[#responses]
assert(lastR[1]=="use-1" and lastR[2]==true and lastR[3]=="activated" and owned(first.id)==0)
assert(client.cache.ProgressionJson.buffs[firstItem.kind].expiresAt==nowTime+firstItem.duration)
-- Second use while active needs the replace dialog.
assert(select(2,clientBuy(first.id))=="purchased")
clockNow+=1
serverHandler(player,"usePotion",first.id,"use-2",false)
assert(responses[#responses][2]==false and responses[#responses][3]=="replace_confirmation_required")
clockNow+=1
serverHandler(player,"usePotion",first.id,"use-3",true)
assert(responses[#responses][2]==true and owned(first.id)==0)

-- Every potion offered in some window can be bought through the handler, to its stock, then 'sold_out'; request ids fit the 40 char limit.
local bought={}
local w0=Rules.shopWindow(nowTime)
for w=w0+1,w0+4000 do
 nowTime=Rules.shopEndsAt(w-1) -- start of window w
 local all=Rules.shopOffers(w)
 for _,offer in all do
  if not bought[offer.id] then
   bought[offer.id]=true
   local before=owned(offer.id)
   for i=1,offer.stock do
    local good,why=clientBuy(offer.id)
    assert(good and why=="purchased",offer.id.." "..tostring(why))
   end
   assert(owned(offer.id)==before+offer.stock)
   local good,why=clientBuy(offer.id)
   assert(not good and why=="sold_out",offer.id.." "..tostring(why))
   assert(#(offer.id.."@"..w)<=40)
  end
 end
 local n=0 for _ in bought do n+=1 end
 if n==#ProgressionConfig.Potions then break end
end
local n=0 for _ in bought do n+=1 end
assert(n==#ProgressionConfig.Potions,"every catalog potion was bought through the real handler")
for _,item in ProgressionConfig.Potions do assert(#(item.id.."@99999999999")<=40,"id fits the 40 char remote limit even with an 11 digit window: "..item.id) end
assert(client.cache.Crystals==1000000)

-- Stale window: a confirm dialog left open across a restock is refused with stale_window (shown as "The shop just changed"), nothing changes.
nowTime=Rules.shopEndsAt(Rules.shopWindow(nowTime))+1
local staleBefore=owned("speed_common")
local oldWindow=Rules.shopWindow(nowTime)-1
local staleGood,staleWhy=clientBuy("speed_common",oldWindow)
assert(not staleGood and staleWhy=="stale_window" and owned("speed_common")==staleBefore)
-- Malformed requests (never sent by the real client) are dropped silently and cannot wedge the handler.
clockNow+=1
local count=#responses
serverHandler(player,"buyPotion",string.rep("x",41),"bad",false)
serverHandler(player,"buyPotion","speed_common@1",nil,false)
serverHandler(player,"buyPotion","speed_common@1","bad2","yes")
serverHandler(player,"dropTable","x","bad3",false)
assert(#responses==count)
local afterGood=clientBuy("speed_common",Rules.shopWindow(nowTime))
assert(#warns==0,"no handler errors: "..table.concat(warns,"; "))
print("Potion purchase passed: real ProgressionAction handler + memory-profile repository answer purchased/busy/duplicate/stale/sold_out, update ProgressionJson potions and shop stock, keep the 1,000,000 test wallet pinned, and every catalog potion is buyable")
'''


def script():
    s = 'local ProgressionConfig=' + module('src/shared/ProgressionConfig.luau') + '\nlocal GameConfig=' + module('src/shared/Config.luau') + '\n'
    s += 'local script={Parent={ProgressionConfig="ProgressionConfig"}}\nlocal require=function(_)return ProgressionConfig end\nlocal Genetics=' + module('src/shared/EggGenetics.luau') + '\n'
    s += 'local script={Parent={Config="Config",EggGenetics="Genetics"}}\nlocal require=function(id)return if id=="Genetics" then Genetics else GameConfig end\nlocal EggTraits=' + module('src/shared/EggTraits.luau') + '\n'
    s += 'local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}\nlocal require=function(id)return if id=="Genetics" then Genetics else ProgressionConfig end\nlocal Rules=' + module('src/shared/ProgressionRules.luau') + '\n'
    s += BODY
    for key, path in (
        ('FTUE_RULES_MODULE', 'src/shared/FtueRules.luau'), ('FUSION_ODDS_MODULE', 'src/server/FusionOdds.luau'),
        ('IDENTITY_FUSION_MODULE', 'src/server/IdentityFusion.luau'), ('COSMETIC_OWNERSHIP_MODULE', 'src/server/CosmeticOwnership.luau'),
        ('IDENTITY_MODULE', 'src/server/DinosaurIdentity.luau'), ('NEST_QUEUE_MODULE', 'src/shared/NestQueue.luau'),
        ('SETTINGS_MODEL_MODULE', 'src/shared/SettingsModel.luau'), ('PAID_RANDOM_GATE_MODULE', 'src/shared/PaidRandomGate.luau'), ('REWARDS_MODULE', 'src/server/RewardMath.luau'),
        ('REPO_MODULE', 'src/server/ProfileRepository.luau'), ('CLOCK_MODULE', 'src/shared/WeatherClock.luau'),
        ('SERVICE_MODULE', 'src/server/ProgressionService.luau')):
        s = s.replace(key, module(path))
    return s


def static_checks():
    client = (ROOT / 'src/client/Bootstrap.client.luau').read_text() + (ROOT / 'src/client/ShopScreens.luau').read_text()  # BD-1020: transact and the shop screens moved
    server = (ROOT / 'src/server/ProgressionService.luau').read_text()
    status = (ROOT / 'src/shared/NotifyQueue.luau').read_text()
    # transact fires the remote (unless a request is already in flight) and records the pending token.
    m = re.search(r'local function transact\(action,id,replace\)(.*?)\nend\n', client, re.S)
    assert m, 'transact() not found'
    t = m.group(1)
    assert 'shopAction:FireServer(action,id,token,replace==true)' in t and 'pendingShop={token=token' in t, 'transact must fire ProgressionAction'
    assert t.index('shopAction:FireServer') > t.index('pendingShop={'), 'pending recorded before the request'
    # The only early return in transact is the visible "still processing" notice.
    assert t.count('return') == 1 and 'notify("Purchase is still processing"' in t, 'transact may only bail out with the processing notice'
    # BUY POTION: transact first, leave the modal after; no early exit in the handler.
    b = re.search(r'button\(body,if replacing then "Replace" else "BUY POTION",290,263,510,58,C\.accent,function\(\)(.*?)\n        end\)', client, re.S)
    assert b, 'BUY POTION button not found'
    h = b.group(1)
    assert 'return' not in h, 'confirm handler must not return before transact'
    assert 'transact("buyPotion",item.id.."@"..potionChoice.window,false)' in h, 'buy must send the window-stamped id'
    assert h.index('transact(') < h.index('open("potions")'), 'transact before leaving the modal'
    # CANCEL is the only other control on the confirm card and never transacts.
    c = re.search(r'button\(body,"CANCEL",290,339,510,44,C\.red,function\(\) open\("potions"\) end\)', client)
    assert c, 'CANCEL button on the confirm card'
    # The scrim closes the modal (a click outside the panel): documented, never buys.
    assert 'shade.Activated:Connect(function() if require(script.Parent.ModalClose).outsideTap() then close() end end)' in client  # BD-1019: still a close, now through the hatch's backdrop rule
    # Result handler: clears the pending token and re-renders the shop list.
    r = re.search(r'shopResult\.OnClientEvent:Connect\(function\(token,ok,status\)(.*?)\n    end\)', client, re.S)
    assert r, 'ProgressionResult handler'
    assert 'pendingShop.token==token then pendingShop=nil' in r.group(1)
    assert 'local current=isActive() if current=="auras" or current=="potions" then body:ClearAllChildren() render(current) end' in r.group(1)  # same test, the active screen comes from Bootstrap through a getter
    # ProgressionJson delta re-renders the open Potion Shop (so "Your potions" fills in without reopening).
    assert re.search(r'for _,attribute in \{[^}]*"ProgressionJson"[^}]*\} do\s+PrivateState\.onChanged\(attribute,\s*function\(\)\s+scheduleModalRefresh\(\)', client, re.S)
    sm = re.search(r'local function scheduleModalRefresh\(\)(.*?)\nend\n', client, re.S)
    assert sm and '"potions"' in sm.group(1), 'scheduleModalRefresh must include the potions screen'
    # Both sides agree on the remote names and on buyPotion being an allowed action.
    assert 'remotes:WaitForChild("ProgressionAction")' in client and 'remotes:WaitForChild("ProgressionResult")' in client
    assert 'remote.Name="ProgressionAction"' in server and 'response.Name="ProgressionResult"' in server
    assert '"buyPotion","usePotion"' in server
    # Server statuses a purchase can return all have child-friendly copy (busy has the generic fallback).
    for code in ('insufficient_crystals', 'sold_out', 'not_offered', 'stale_window', 'window_required', 'inventory_full', 'save_failed'):
        assert code in status, code
    # The test wallet re-pins crystals AFTER a purchase is applied (so the counter never moves in Studio memory profiles).
    repo = profile_sources.repository_text()
    pin = 'if localPreview and Config.StudioTestWalletEnabled then progress.crystals = Config.StudioTestCrystals end'
    assert repo.count(pin) >= 3
    print('Potion purchase source checks passed: confirm handler transacts before leaving the modal, transact fires ProgressionAction, result and ProgressionJson refresh the shop, remote contract agrees on both sides')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'potion_purchase.luau'
        path.write_text(script())
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
