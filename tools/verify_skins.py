"""BD-456 dino skins data model and equip (docs/137 s7, s10, s15): offline verifier in pinned Luau.

Runs the REAL src/shared/SkinCatalog.luau, src/shared/SkinPickerModel.luau, src/shared/GiftRules.luau (whose skin items are built from the
catalogue), src/server/SkinService.luau and src/server/ProfileRepository.luau (skinView, applySkin, applyGifts, fuseDinosaurs) on the mocked
DataStore of tools/verify_rewards.py, plus the frozen Build 020 reader of tools/verify_rollback.py.

Covers: catalogue shape (kid-friendly names, Base fallback, every model set EMPTY so no skin but Base can be worn); one source of truth with
gifting; flag-off identity (no remote, no profile read or write, existing skin fields left alone); equip only an OWNED skin and only on a species
that has a model; Base fallback for unowned, revoked, unknown and model-less looks (no write); gifted skins land in the same `ownedSkins`;
the account default; the stale-entitlement race (a revoke on another server); a skin never touches genes, Shiny/BIG, mutations, stage, the
entitlement record or fusion inputs (same quote digest, odds and eligibility); a fused output starts without a skin while the account-wide
entitlement survives; additive and lazy fields (a profile that never touches skins stays byte-identical); rollback rule RB1 (Build 020 loads
and keeps the new fields); strict request shapes and the rate limit; the pure picker model's requests pass the real server.
Static: DinoSkinsEnabled is false in source and pinned off in the default AND playtest release profiles; pure modules stay pure; no Robux API; the
profile writer touches only skin fields and never `ownedSkins`; only SkinService calls it; fusion code never reads or copies a skin.

  python tools/verify_skins.py --runner C:/path/to/luau.exe
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release_profiles  # noqa: E402
import verify_gifts  # noqa: E402  (the shared token filler, GiftRules binding and Build 020 fixture paths)
import verify_rewards  # noqa: E402  (the mocked DataStore prefix)

FLAG = 'DinoSkinsEnabled'
module = verify_gifts.module
strip_comments = verify_gifts.strip_comments
IMPURE = ('Instance.new', 'game:GetService', 'GetService(', 'os.time', 'os.clock', 'os.date', 'DataStore', 'RemoteEvent', 'RemoteFunction', 'task.')
ROBUX_WORDS = ('MarketplaceService', 'PromptProductPurchase', 'PromptGamePassPurchase', 'DeveloperProducts', 'ProcessReceipt', 'TextService', 'FilterStringAsync')


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def function_body(text: str, header: str) -> str:
    """The body of a top-level `function X.y(...)` up to its closing `end` at column 0."""
    match = re.search(r'^' + re.escape(header) + r'.*?\n(.*?)^end$', text, flags=re.S | re.M)
    return match.group(1) if match else ''


def first_lines(body: str, count: int = 3) -> list[str]:
    return [line for line in body.splitlines() if line.strip()][:count]


def static_errors() -> list[str]:
    errors: list[str] = []
    config = read('src/shared/Config.luau')
    entries = release_profiles.config_entries(config)
    found = entries.get(FLAG)
    if not found or len(found) != 1 or found[-1][1] is not False:
        errors.append(f'Config.{FLAG} must exist exactly once and be false in source')
    for profile in ('default', 'playtest'):
        mine = [r for r in release_profiles.rules_for(profile) if r.key == FLAG]
        if not mine or any(r.mode != 'require' or r.value is not False or r.missing != 'error' for r in mine):
            errors.append(f'release profile {profile!r} must pin {FLAG} to false (mode require, missing = error)')
        report = release_profiles.verify_source(config, profile)
        errors.extend(f'[{profile}] {e}' for e in report.errors if FLAG in e)
        flipped = re.sub(rf'^(    {FLAG} = )false', r'\1true', config, flags=re.M)
        if not any(FLAG in e for e in release_profiles.verify_source(flipped, profile).errors):
            errors.append(f'{FLAG}=true in Config is NOT rejected by profile {profile!r}')

    catalog = strip_comments(read('src/shared/SkinCatalog.luau'))
    picker = strip_comments(read('src/shared/SkinPickerModel.luau'))
    service = strip_comments(read('src/server/SkinService.luau'))
    repo = strip_comments(read('src/server/ProfileRepository.luau'))
    for name, text in (('SkinCatalog', catalog), ('SkinPickerModel', picker)):
        for word in IMPURE:
            if word in text:
                errors.append(f'src/shared/{name}.luau must stay pure, found {word}')
    for name, text in (('src/shared/SkinCatalog.luau', catalog), ('src/shared/SkinPickerModel.luau', picker), ('src/server/SkinService.luau', service)):
        for word in ROBUX_WORDS:
            if word in text:
                errors.append(f'{name} mentions {word}: BD-456 has no Robux (purchases are BD-459)')
        if re.search(r'rbxassetid|ImageId|Instance\.new\("(?:Frame|TextLabel|ImageLabel|ScreenGui)"', text):
            errors.append(f'{name} draws or loads art: the picker UI and its art are BD-457')

    # Flag-first entry points: with the flag off every public function answers before it touches anything.
    for label, body, needle in (
        ('SkinService.handle', function_body(service, 'function SkinService.handle('), 'Config.DinoSkinsEnabled ~= true then return fail("disabled")'),
        ('SkinService.resolve', function_body(service, 'function SkinService.resolve('), 'Config.DinoSkinsEnabled ~= true'),
        ('SkinService.start', function_body(service, 'function SkinService.start('), 'if Config.DinoSkinsEnabled ~= true then return nil end'),
        ('ProfileRepository.skinView', function_body(repo, 'function ProfileRepository.skinView('), 'if Config.DinoSkinsEnabled ~= true then return nil, "disabled" end'),
        ('ProfileRepository.applySkin', function_body(repo, 'function ProfileRepository.applySkin('), 'if Config.DinoSkinsEnabled ~= true then return false, "disabled" end'),
    ):
        first = first_lines(body, 1)
        if not first or needle not in first[0]:
            errors.append(f'{label} must test the flag on its FIRST line (flag-off identity)')

    # The profile writer: only skin fields, never the entitlement record, nothing about genes or fusion.
    writer = function_body(repo, 'function ProfileRepository.applySkin(') + function_body(repo, 'function ProfileRepository.skinView(')
    fields = set(re.findall(r'\b(?:instance|profile)\.(\w+)\s*=(?!=)', writer))
    if fields - {'skin', 'defaultSkin', 'revision'}:
        errors.append(f'applySkin may only write skin, defaultSkin and revision, found {sorted(fields - {"skin", "defaultSkin", "revision"})}')
    if re.search(r'ownedSkins\s*(?:\[[^\]]*\])?\s*=(?!=)', writer):
        errors.append('applySkin/skinView must never write ownedSkins: only gifts, receipts and admin grants add or remove entitlements (docs/137 s7)')
    for word in ('genes', 'shiny', 'big', 'mutation', 'stage', 'rarity', 'cosmetics', 'collection', 'progression', 'crystals', 'recentOperations', 'purchaseReceipts'):
        if re.search(rf'\b{word}\b', writer + service):
            errors.append(f'the skin writer/service must not read or write {word}: a skin is a look only')
    if re.search(r'\bownedSkins\b', service):
        errors.append('SkinService must read the entitlement only through the repository view, never the record itself')

    # Only SkinService may call the new repository functions.
    for path in sorted((ROOT / 'src').rglob('*.luau')):
        text = strip_comments(path.read_text(encoding='utf-8'))
        rel = path.relative_to(ROOT).as_posix()
        if rel not in ('src/server/SkinService.luau', 'src/server/ProfileRepository.luau') and re.search(r'\.(applySkin|skinView)\(', text):
            errors.append(f'{rel} calls ProfileRepository.applySkin/skinView: only SkinService may')
    boot = read('src/server/Bootstrap.server.luau')
    if boot.count('SkinService') != 1 or 'SkinService).start(ProfileRepository)' not in boot:
        errors.append('Bootstrap must start SkinService exactly once, with the repository')
    if 'remote.Name = "SkinAction"' not in service or 'RemoteName = "SkinAction"' not in picker:
        errors.append('the remote must be named SkinAction in both SkinService and SkinPickerModel')

    # Fusion neither reads nor copies a skin (the output has no skin field; the entitlement is untouched).
    for path in ('src/server/IdentityFusion.luau', 'src/server/DinosaurIdentity.luau', 'src/server/FusionService.luau', 'src/server/CosmeticOwnership.luau', 'src/server/FusionOdds.luau'):
        if re.search(r'skin', strip_comments(read(path)), flags=re.I):
            errors.append(f'{path} mentions a skin: fusion must not read, copy or price a skin (docs/137 s4, docs/46)')

    # One source of truth: GiftRules builds its skin items from the catalogue.
    gifts = strip_comments(read('src/shared/GiftRules.luau'))
    if 'require(script.Parent.SkinCatalog)' not in gifts or re.search(r'skin\s*=\s*"', gifts):
        errors.append('GiftRules must build its skin items from SkinCatalog.Ownable and list no skin id itself')
    return errors


# ----------------------------------------------------------------------------------------------------------------------------------
HEAD = r'''
local checks=0
local function check(cond,msg) checks+=1 if not cond then error("FAIL: "..tostring(msg),2) end end
local function key(id) return "u:"..tostring(id) end
local function newUser(id)
 local u={Parent=true,UserId=id,Name="P"..id,attrs={}}
 function u:SetAttribute(k,v) self.attrs[k]=v end
 function u:GetAttribute(k) return self.attrs[k] end
 return u
end

------------------------------------------------------------------ modules under test
local SkinCatalog=@@SKIN_CATALOG@@
-- Test-only catalogue: a copy of the REAL source with two model sets made reachable, so the "has a model" paths can run. The committed catalogue
-- has every set empty (asserted below), which is what ships.
local PatchedPlush,PatchedClay={},{}
local PatchedCatalog=@@SKIN_CATALOG_PATCHED@@
local GiftRules=@@GIFT_RULES@@
local function makePicker(CAT)
 local script={Parent={SkinCatalog="SkinCatalog"}}
 local require=function(id) assert(id=="SkinCatalog") return CAT end
 return @@PICKER@@
end
local function makeService(cfg,CAT)
 local world={instances=0,connects=0,warned=0}
 local rs={children={},Shared={Config="Config",SkinCatalog="SkinCatalog"}}
 function rs:FindFirstChild(n) return self.children[n] end
 local Instance={new=function(class)
  world.instances+=1
  local o={ClassName=class,Name=class,children={}}
  return setmetatable(o,{__newindex=function(t,k,v) rawset(t,k,v) if k=="Parent" and v then v.children[rawget(t,"Name")]=t end end})
 end}
 local services={Players={PlayerRemoving={Connect=function() world.connects+=1 end}},ReplicatedStorage=rs}
 local game={GetService=function(_,n) return services[n] or error("service "..n.." is not modelled") end}
 local script={Parent={}}
 local require=function(id)
  if id=="Config" then return cfg elseif id=="SkinCatalog" then return CAT end
  error("unexpected module "..tostring(id))
 end
 local warn=function() world.warned+=1 end
 local S=@@SKIN_SERVICE@@
 return S,world,rs
end

------------------------------------------------------------------ the current repository with the playtest-profile identity flags
local baseConfig=GameConfig
local Cfg=table.clone(baseConfig)
Cfg.IdentityPersistentEnabled=true
Cfg.IdentityFusionPreviewEnabled=true
GameConfig=Cfg
local Repo=@@REPO_MODULE@@
GameConfig=baseConfig
local VOLATILE={session=true,revision=true,metrics=true} -- lease, revision counter, play-time metric legitimately move
local function sameData(a,b,ignore)
 for k,v in a do if not VOLATILE[k] and not (ignore and ignore[k]) and not same(v,b[k]) then return false,k end end
 for k in b do if not VOLATILE[k] and not (ignore and ignore[k]) and a[k]==nil then return false,k end end
 return true
end
local function claimAll(u)
 local ids={}
 for _,chest in u.attrs.ChestQueueJson or {} do
  local ok,h=Repo.claimChest(u,chest.id)
  if ok and h.instanceIds then for _,id in h.instanceIds do table.insert(ids,id) end end
 end
 return ids
end
local function hatchPlayer(id,rounds)
 local u=newUser(id) assert(Repo.load(u))
 local ids={}
 for round=1,rounds do
  assert(Repo.commitRunSettlement(u,"sk"..id.."-"..round,10,nil,300))
  for _,i in claimAll(u) do table.insert(ids,i) end
 end
 return u,ids
end
local function giftSkin(u,itemId,giftId) -- the REAL gift claim transaction (docs/134), driven with the REAL GiftRules operation
 Cfg.GiftClaimEnabled=true
 local gift=assert(GiftRules.newGift("admin",1,itemId,nil,nil,1000,giftId))
 local ok,r=Repo.applyGifts(u,{apply={GiftRules.operationFor(gift)},revoke={}})
 Cfg.GiftClaimEnabled=false
 return ok and r[giftId]
end
local function revokeGift(u,itemId,giftId)
 Cfg.GiftClaimEnabled=true
 local ok,r=Repo.applyGifts(u,{apply={},revoke={{id=giftId,skin=GiftRules.skinOf(itemId)}}})
 Cfg.GiftClaimEnabled=false
 return ok and r[giftId]
end
local function skinFree(profile) -- a profile with every skin field removed (to prove nothing ELSE changed)
 local p=copy(profile) p.defaultSkin=nil
 if p.dinosaurIdentity then for _,inst in p.dinosaurIdentity.instances do inst.skin=nil end end
 return p
end
'''

CATALOG = r'''
------------------------------------------------------------------ (A) SkinCatalog: shape, kid-friendly names, Base fallback, empty model sets, one source of truth
do
 local POWER={"luck","power","boost","random","mystery","chance","rarity","rare","egg","dino","species","stronger","faster","bigger","fusion","odds","win","speed","nest","potion","limited","only"}
 check(SkinCatalog.Base=="Base" and SkinCatalog.List[1].id=="Base" and SkinCatalog.List[1].kind=="free" and SkinCatalog.isFree("Base"),"Base is first and free")
 local seen,labels={},{}
 for i,s in SkinCatalog.List do
  check(not seen[s.id] and string.match(s.id,"^%u%l+$"),"unique plain id "..s.id) seen[s.id]=true
  check(s.kind=="free" or s.kind=="robux","valid kind "..s.id)
  check(#s.label>=3 and #s.label<=10 and string.match(s.label,"^%u%l+$"),"short one-word kid label "..s.id)
  local lower=string.lower(s.label)
  for _,w in POWER do check(not string.find(lower,w,1,true),"no power, random or pressure word in "..s.id..": "..w) end
  check(SkinCatalog.ById[s.id]==s and SkinCatalog.isKnown(s.id) and SkinCatalog.get(s.id)==s and SkinCatalog.label(s.id)==s.label,"lookups "..s.id)
  check(type(s.defeat)=="string" and #s.defeat>=3,"defeat id "..s.id)
  check(i==1 or s.kind=="robux","only Base is free")
  labels[s.id]=s.label
 end
 check(labels.Plush=="Plushy" and labels.Clay=="Clay" and labels.Bricks=="Bricks" and labels.Balloon=="Balloon","docs/137 s15 names: Plushy, Clay, Bricks, Balloon")
 check(#SkinCatalog.List==5 and #SkinCatalog.Ownable==4 and SkinCatalog.Ownable[1].id=="Plush","four ownable styles in the docs/137 order")
 for _,bad in {"plush","PLUSH","Anime","Movie","","Base ",5,true,{},false} do
  check(not SkinCatalog.isKnown(bad) and SkinCatalog.normalize(bad)=="Base" and SkinCatalog.get(bad)==nil and not SkinCatalog.isFree(bad),"unknown reads as Base: "..tostring(bad))
 end
 check(SkinCatalog.normalize(nil)=="Base" and SkinCatalog.label("nope")==SkinCatalog.label("Base"),"nil and unknown labels fall back to Base")
 check(not pcall(function() SkinCatalog.List[1]=nil end) and not pcall(function() SkinCatalog.Models.Plush=nil end),"the catalogue is frozen")
 -- every model set is EMPTY in the committed catalogue: no skin but Base can be worn by any species
 for _,id in {"Plush","Clay","Bricks","Balloon"} do
  check(next(SkinCatalog.Models[id])==nil and #SkinCatalog.supportedSpecies(id)==0 and SkinCatalog.modelSet(id)==SkinCatalog.Models[id],"no species has a "..id.." model yet")
 end
 check(SkinCatalog.modelSet("Base")==nil and SkinCatalog.modelSet("nope")==nil and #SkinCatalog.supportedSpecies("Base")==0,"Base has no model set: it fits everything")
 for _,species in GameConfig.SpeciesOrder do
  check(SkinCatalog.hasModel("Base",species),"Base fits "..species)
  for _,id in {"Plush","Clay","Bricks","Balloon"} do check(not SkinCatalog.hasModel(id,species),id.." has no model for "..species) end
 end
 for _,bad in {"",5,nil,true,{}} do check(not SkinCatalog.hasModel("Base",bad),"a missing species fits nothing: "..tostring(bad)) end
 -- owns / canEquip / effective
 check(SkinCatalog.owns(nil,"Base") and SkinCatalog.owns("junk","Base") and not SkinCatalog.owns(nil,"Plush") and not SkinCatalog.owns("junk","Plush")
  and not SkinCatalog.owns({Plush="yes"},"Plush") and not SkinCatalog.owns({Plush=1},"Plush") and SkinCatalog.owns({Plush=true},"Plush") and not SkinCatalog.owns({Plush=true},"Clay")
  and not SkinCatalog.owns({Hologram=true},"Hologram") and not SkinCatalog.owns({},"nope"),"owns: Base always; others only with an explicit true; unknown never")
 local c,why=SkinCatalog.canEquip({Plush=true},"Plush","compy") check(not c and why=="no_model","owned but no model yet")
 c,why=SkinCatalog.canEquip({},"Plush","compy") check(not c and why=="not_owned","not owned")
 c,why=SkinCatalog.canEquip({Plush=true},"Hologram","compy") check(not c and why=="unknown_skin","unknown")
 c,why=SkinCatalog.canEquip(nil,"Base","raptor") check(c and why=="ok","Base always")
 check(SkinCatalog.effective(nil,nil,nil,"compy")=="Base" and SkinCatalog.effective({Plush=true},"Plush","Plush","compy")=="Base","no model anywhere: everything is Base")
end
do -- with a model: the patched copy (test only)
 local P=PatchedCatalog
 PatchedPlush.compy=true PatchedClay.compy=true
 check(P.hasModel("Plush","compy") and not P.hasModel("Plush","raptor") and P.supportedSpecies("Plush")[1]=="compy" and #P.supportedSpecies("Plush")==1,"patched: Plush on compy only")
 local owned={Plush=true}
 local ok,why=P.canEquip(owned,"Plush","compy") check(ok and why=="ok","owned + model")
 ok,why=P.canEquip(owned,"Plush","raptor") check(not ok and why=="no_model","owned, other species")
 ok,why=P.canEquip(owned,"Clay","compy") check(not ok and why=="not_owned","model but not owned")
 check(P.effective(owned,nil,"Plush","compy")=="Plush","its own choice")
 check(P.effective(owned,"Plush",nil,"compy")=="Plush","no choice: the account default")
 check(P.effective(owned,"Plush","Base","compy")=="Base","an explicit Base beats the default")
 check(P.effective(owned,"Plush",nil,"raptor")=="Base","default on a species with no model: Base")
 check(P.effective({},"Plush","Plush","compy")=="Base" and P.effective({},"Plush",nil,"compy")=="Base","revoked or never owned: Base, not the default")
 check(P.effective(owned,"Clay","Plush","compy")=="Plush" and P.effective(owned,"Plush","Hologram","compy")=="Base" and P.effective(owned,"Plush",5,"compy")=="Base","an unknown or junk choice is Base, not the default")
 PatchedPlush.compy=nil PatchedClay.compy=nil
end
-- one source of truth with gifting: the gift items for skins are exactly SkinCatalog.Ownable
do
 local skinsInGifts={}
 for _,e in GiftRules.Catalogue do if e.kind=="skin" then table.insert(skinsInGifts,e) end end
 check(#skinsInGifts==#SkinCatalog.Ownable,"as many gift skins as ownable skins")
 for i,e in skinsInGifts do
  local s=SkinCatalog.Ownable[i]
  check(e.skin==s.id and e.id=="skin_"..string.lower(s.id) and e.label==s.label.." skin" and e.launch==true and GiftRules.skinOf(e.id)==s.id,"gift item "..e.id.." is the catalogue skin "..s.id)
  check(SkinCatalog.isKnown(e.skin) and not SkinCatalog.isFree(e.skin),"a gifted skin is an ownable catalogue skin")
 end
 check(GiftRules.skinOf("skin_base")==nil,"Base is never a gift (everyone has it)")
end
print("SkinCatalog passed: names, Base fallback, empty model sets, owns/canEquip/effective, one source of truth with GiftRules")
'''

SERVICE = r'''
------------------------------------------------------------------ (B) flag-off identity
local A,aIds=hatchPlayer(5001,30)
local B,bIds=hatchPlayer(5002,6)
local function speciesOf(owner,id) return data[key(owner)].dinosaurIdentity.instances[id].speciesId end
local bySpecies={}
for _,id in aIds do local s=speciesOf(5001,id) bySpecies[s]=bySpecies[s] or {} table.insert(bySpecies[s],id) end
local sp1,list1
for s,l in bySpecies do if #l>=6 and (sp1==nil or s<sp1) then sp1,list1=s,l end end
assert(sp1,"a species with at least six hatched copies") table.sort(list1)
local otherId,otherSpecies for s,l in bySpecies do if s~=sp1 then otherSpecies,otherId=s,l[1] break end end
assert(otherId,"a second species")
print("hatched "..#aIds.." dinos for A; donors "..sp1.." x"..#list1.."; other species "..otherSpecies)
local dino=list1[1]

do
 check(GameConfig.DinoSkinsEnabled==false and Cfg.DinoSkinsEnabled==false,"the committed Config has DinoSkinsEnabled off")
 local touched=0
 local spy=setmetatable({},{__index=function(_,k) return function() touched+=1 error("repository touched: "..tostring(k)) end end})
 local S,world,rs=makeService(Cfg,SkinCatalog)
 check(S.start(spy)==nil and world.instances==0 and world.connects==0 and next(rs.children)==nil,"flag off: start creates no remote, no folder, no connection")
 for _,req in {{action="get"},{action="equip",instanceId=dino,skin="Base"},{action="setDefault",skin="Plush"},"junk",5,{}} do
  local r=S.handle(A,req) check(r.ok==false and r.reason=="disabled","flag off: handle answers disabled: "..tostring(req))
 end
 check(S.handle(A,{action="get"},"extra").reason=="disabled" and touched==0,"flag off: nothing reached the repository")
 check(S.resolve(A,dino)=="Base" and touched==0,"flag off: resolve is Base")
 local snap,t0=copy(data[key(5001)]),transforms
 local v,why=Repo.skinView(A,dino) check(v==nil and why=="disabled","flag off: skinView")
 for _,plan in {{kind="equip",instanceId=dino,skin="Base",free=true},{kind="setDefault",skin="Plush"},{kind="unequip",instanceId=dino},"junk"} do
  local ok,st=Repo.applySkin(A,plan) check(ok==false and st=="disabled","flag off: applySkin answers disabled")
 end
 check(transforms==t0 and same(snap,data[key(5001)]),"flag off: not one profile transform, byte-identical profile")
 -- a profile that ALREADY carries skin fields (a flag-on session, a newer build) is left alone while off
 local D=hatchPlayer(5004,3) Repo.release(D)
 local stored=data[key(5004)]
 local firstId for id in stored.dinosaurIdentity.instances do firstId=id break end
 stored.ownedSkins={Plush=true,Hologram=true} stored.defaultSkin="Plush" stored.dinosaurIdentity.instances[firstId].skin="Plush"
 local keep=copy(stored)
 local D2=newUser(5004) assert(Repo.load(D2)) Repo.renew(D2) Repo.release(D2)
 check(sameData(keep,data[key(5004)]) and data[key(5004)].dinosaurIdentity.instances[firstId].skin=="Plush","flag off: existing skin fields are not normalised, migrated or rewritten by load, renew or release")
end
print("Flag-off identity passed: no remote, no repository access, no profile read or write, existing fields left alone")

------------------------------------------------------------------ (C) flag on: service + repository
Cfg.DinoSkinsEnabled=true
local S1,w1,rs1=makeService(Cfg,SkinCatalog) -- the committed (empty) catalogue
local S2,w2=makeService(Cfg,PatchedCatalog) -- test catalogue: Plush on sp1 only, Clay on nobody yet
local R1=S1.start(Repo) local R2=S2.start(Repo)
check(R1 and R1.Name=="SkinAction" and R1.ClassName=="RemoteFunction" and rs1.children.BeDinoRemotes.children.SkinAction==R1 and w1.instances==2 and R2.Name=="SkinAction","flag on: the SkinAction RemoteFunction exists")
PatchedPlush[sp1]=true
local clock1,clock2=0,0
S1.setClock(function() return clock1 end) S2.setClock(function() return clock2 end)
local function call1(u,req) clock1+=1 return S1.handle(u,req) end
local function call2(u,req) clock2+=1 return S2.handle(u,req) end
local function stored(owner) return data[key(owner)] end
local function revisionOf(owner) return stored(owner).revision end
local baseline=copy(stored(5001)) -- for "nothing else changed" at the end
local lowDino for _,id in aIds do if speciesOf(5001,id)==sp1 and id~=list1[1] then lowDino=id break end end

do -- get: read only, lazy
 local snap,t0=copy(stored(5001)),transforms
 local r=call1(A,{action="get"}) check(r.ok and #r.owned==0 and r.defaultSkin=="Base" and r.speciesId==nil,"get (no dino): nothing owned, default Base")
 r=call1(A,{action="get",instanceId=dino}) check(r.ok and r.speciesId==sp1 and r.wearing=="Base" and r.skin==nil,"get (one dino): Base, no choice")
 r=call1(B,{action="get",instanceId=dino}) check(r.ok==false and r.reason=="instance_missing","another player's dino is not yours")
 r=call1(A,{action="get",instanceId="u:5001/d:999999"}) check(r.ok==false and r.reason=="instance_missing","an unknown dino")
 check(transforms==t0 and same(snap,stored(5001)),"get makes no store request and writes nothing")
end

do -- the free Base look, equip / unequip, lazy fields
 local rev=revisionOf(5001)
 local before=copy(stored(5001))
 local r=call1(A,{action="equip",instanceId=dino,skin="Base"})
 check(r.ok and r.status=="equipped" and r.skin=="Base","equip Base")
 check(stored(5001).dinosaurIdentity.instances[dino].skin=="Base" and revisionOf(5001)==rev+1,"one revision for one change")
 check(sameData(skinFree(before),skinFree(stored(5001))),"nothing but the skin field changed (genes, traits, collection, wallet, eggs...)")
 check(stored(5001).ownedSkins==nil and stored(5001).defaultSkin==nil,"equipping Base creates no entitlement record and no default")
 local snap,t0=copy(stored(5001)),transforms
 r=call1(A,{action="equip",instanceId=dino,skin="Base"}) check(r.ok and r.status=="unchanged","equip the same look again: unchanged")
 check(same(snap,stored(5001)),"a repeat writes nothing (byte-identical)")
 r=call1(A,{action="unequip",instanceId=dino}) check(r.ok and r.status=="unequipped" and r.skin=="Base","unequip")
 check(stored(5001).dinosaurIdentity.instances[dino].skin==nil and revisionOf(5001)==rev+2,"the field is removed, not set to nil text")
 snap=copy(stored(5001))
 r=call1(A,{action="unequip",instanceId=dino}) check(r.ok and r.status=="unchanged" and same(snap,stored(5001)),"unequip with no choice: unchanged, nothing written")
 r=call1(A,{action="setDefault",skin="Base"}) check(r.ok and r.status=="unchanged" and same(snap,stored(5001)),"clearing a default that is not set: nothing written")
end

do -- ownership + model, with the committed (empty) catalogue and the patched one
 local snap=copy(stored(5001))
 local r=call1(A,{action="equip",instanceId=dino,skin="Plush"}) check(r.ok==false and r.reason=="not_owned","committed catalogue: not owned")
 r=call2(A,{action="equip",instanceId=dino,skin="Plush"}) check(r.ok==false and r.reason=="not_owned","patched catalogue: a model exists but the skin is not owned")
 for _,bad in {"Hologram","plush","Anime","Base2"} do
  r=call2(A,{action="equip",instanceId=dino,skin=bad}) check(r.ok==false and r.reason=="unknown_skin","unknown skin refused: "..bad)
  r=call2(A,{action="setDefault",skin=bad}) check(r.ok==false and r.reason=="unknown_skin","unknown default refused: "..bad)
 end
 r=call2(A,{action="setDefault",skin="Plush"}) check(r.ok==false and r.reason=="not_owned","an unowned default is refused")
 check(same(snap,stored(5001)),"refusals write nothing")
 -- a gift lands in the SAME ownedSkins the skins read (docs/134 + docs/137)
 check(giftSkin(A,"skin_plush","Agift-p1")=="applied","gift the Plush skin")
 check(stored(5001).ownedSkins.Plush==true,"the gifted skin is in profile.ownedSkins")
 r=call1(A,{action="get"}) check(r.ok and #r.owned==1 and r.owned[1]=="Plush","get lists the gifted skin")
 r=call1(A,{action="equip",instanceId=dino,skin="Plush"}) check(r.ok==false and r.reason=="no_model","owned, but no species has a Plush model yet (committed catalogue)")
 r=call2(A,{action="equip",instanceId=otherId,skin="Plush"}) check(r.ok==false and r.reason=="no_model","owned, but THIS species has no Plush model")
 local rev=revisionOf(5001)
 r=call2(A,{action="equip",instanceId=dino,skin="Plush"}) check(r.ok and r.status=="equipped" and r.skin=="Plush","owned + model: equipped")
 check(stored(5001).dinosaurIdentity.instances[dino].skin=="Plush" and revisionOf(5001)==rev+1,"stored on the instance")
 r=call2(A,{action="get",instanceId=dino}) check(r.ok and r.skin=="Plush" and r.wearing=="Plush","get shows what it wears")
 check(S2.resolve(A,dino)=="Plush" and S1.resolve(A,dino)=="Base" and S2.resolve(A,otherId)=="Base" and S2.resolve(A,"nope")=="Base" and S2.resolve(B,dino)=="Base","resolve: model + choice wears it; everything else Base")
 -- the account default
 r=call2(A,{action="setDefault",skin="Plush"}) check(r.ok and r.status=="default_set" and stored(5001).defaultSkin=="Plush","setDefault Plush")
 check(call2(A,{action="get"}).defaultSkin=="Plush","get shows the default")
 check(S2.resolve(A,lowDino)=="Plush","a dino with no choice wears the default where its species has the model")
 check(S2.resolve(A,otherId)=="Base" and S1.resolve(A,lowDino)=="Base","default where there is no model: Base")
 r=call2(A,{action="equip",instanceId=lowDino,skin="Base"}) check(r.ok and r.skin=="Base" and S2.resolve(A,lowDino)=="Base","an explicit Base beats the default")
 r=call2(A,{action="unequip",instanceId=lowDino}) check(r.ok and r.skin=="Plush","unequip returns to the default")
 local snap2=copy(stored(5001))
 r=call2(A,{action="setDefault",skin="Plush"}) check(r.ok and r.status=="unchanged" and same(snap2,stored(5001)),"same default again: nothing written")
 r=call2(A,{action="setDefault",skin="Base"}) check(r.ok and r.status=="default_cleared" and stored(5001).defaultSkin==nil,"setDefault Base clears the field")
 check(S2.resolve(A,lowDino)=="Base" and S2.resolve(A,dino)=="Plush","cleared: dinos with no choice are Base; the dino with its own choice keeps it")
 check(stored(5001).ownedSkins.Plush==true and next(stored(5001).ownedSkins,"Plush")==nil,"skin actions never touched the entitlement record")
end

do -- the stale-entitlement race: a revoke on ANOTHER server after this server cached the profile
 local savedOwned=copy(stored(5001).ownedSkins)
 stored(5001).ownedSkins.Plush=nil -- the other server's committed revoke
 local snap=copy(stored(5001))
 local r=call2(A,{action="equip",instanceId=lowDino,skin="Plush"})
 check(r.ok==false and r.reason=="not_owned" and same(snap,stored(5001)),"the transaction re-checks ownership against the CURRENT profile (a stale cache cannot equip)")
 stored(5001).ownedSkins=savedOwned
end

do -- revoke: the skin falls back to Base on the next read, with no write; a regift restores the choice
 local snap=copy(stored(5001))
 check(revokeGift(A,"skin_plush","Agift-p1")=="revoked" and stored(5001).ownedSkins.Plush==nil,"admin revoke removes the entitlement")
 check(stored(5001).dinosaurIdentity.instances[dino].skin=="Plush","the revoke did not rewrite the instance")
 check(S2.resolve(A,dino)=="Base" and call2(A,{action="get",instanceId=dino}).wearing=="Base","revoked: the dino renders Base (no write)")
 local r=call2(A,{action="setDefault",skin="Plush"}) check(r.ok==false and r.reason=="not_owned","a revoked skin cannot be the default")
 check(giftSkin(A,"skin_plush","Agift-p2")=="applied" and S2.resolve(A,dino)=="Plush","a new gift brings the old choice back")
 check(sameData(skinFree(snap),skinFree(stored(5001)),{ownedSkins=true,claimedGifts=true}),"gift and revoke changed only the gift records")
end

do -- forward compatibility and junk values never lock anything
 local D=newUser(5004) assert(Repo.load(D)) -- seeded above: Plush + Hologram owned, default Plush, one instance on Plush
 local r=call2(D,{action="get"}) check(r.ok and #r.owned==1 and r.owned[1]=="Plush" and r.defaultSkin=="Plush","an id from a newer build is kept in the profile but not offered")
 local firstId for id,inst in stored(5004).dinosaurIdentity.instances do if inst.skin then firstId=id end end
 stored(5004).dinosaurIdentity.instances[firstId].skin="Hologram"
 Repo.release(D) assert(Repo.load(D))
 r=call2(D,{action="get",instanceId=firstId}) check(r.ok and r.skin==nil and r.wearing=="Base","an unknown stored choice reads as no choice and wears Base")
 check(S2.resolve(D,firstId)=="Base","resolve: unknown stored choice is Base")
 local snap=copy(stored(5004))
 call2(D,{action="get",instanceId=firstId}) S2.resolve(D,firstId) Repo.renew(D)
 check(sameData(snap,stored(5004)) and stored(5004).ownedSkins.Hologram==true and stored(5004).dinosaurIdentity.instances[firstId].skin=="Hologram","unknown values are kept byte-for-byte")
 Repo.release(D)
 -- junk values
 local E=hatchPlayer(5005,3) Repo.release(E)
 stored(5005).ownedSkins="junk" stored(5005).defaultSkin=5
 local firstE for id in stored(5005).dinosaurIdentity.instances do firstE=id break end
 assert(Repo.load(E))
 r=call2(E,{action="get"}) check(r.ok and #r.owned==0 and r.defaultSkin=="Base","junk records read as nothing owned, default Base")
 r=call2(E,{action="equip",instanceId=firstE,skin="Plush"}) check(r.ok==false and r.reason=="not_owned","junk ownedSkins: nothing is owned")
 local ok,st=Repo.applySkin(E,{kind="setDefault",skin="Plush"}) check(ok==false and st=="invalid_skin_state" and stored(5005).ownedSkins=="junk","the writer refuses to touch junk entitlements and leaves them")
 r=call2(E,{action="equip",instanceId=firstE,skin="Base"}) check(r.ok and r.status=="equipped","the free Base look still works")
 check(stored(5005).ownedSkins=="junk","junk ownedSkins is not repaired or removed")
 r=call2(E,{action="setDefault",skin="Base"}) check(r.ok and r.status=="default_cleared" and stored(5005).defaultSkin==nil,"a junk default is cleared by Base")
 Repo.release(E)
end

do -- strict shapes and the rate limit
 local t0,snap=transforms,copy(stored(5001))
 local bads={nil,"x",5,true,{},{action="nope"},{action=5},{"get"},{action="get",skin="Base"},{action="get",instanceId={}},{action="get",instanceId=""},{action="get",extra=1},
  {action="equip"},{action="equip",instanceId=dino},{action="equip",skin="Base"},{action="equip",instanceId=dino,skin=5},{action="equip",instanceId=5,skin="Base"},
  {action="equip",instanceId=dino,skin="Base",extra=1},{action="equip",instanceId=dino,skin=string.rep("x",25)},{action="equip",instanceId=string.rep("x",121),skin="Base"},
  {action="unequip"},{action="unequip",instanceId=""},{action="unequip",instanceId=dino,skin="Base"},{action="setDefault"},{action="setDefault",skin=""},
  {action="setDefault",skin=string.rep("x",25)},{action="setDefault",skin="Base",instanceId=dino},{action="get",[1]=true}}
 for i=1,28 do
  local req=bads[i]
  local r=call2(A,req) check(r.ok==false and r.reason=="bad_request","bad shape "..i.." refused as bad_request")
 end
 local r=S2.handle(A,{action="get"},"extra") check(r.ok==false and r.reason=="bad_request","extra arguments refused")
 check(transforms==t0 and same(snap,stored(5001)),"bad requests never reach the store")
 local S3=makeService(Cfg,PatchedCatalog) S3.start(Repo)
 local now=100 S3.setClock(function() return now end)
 for i=1,S3.ActionsPerWindow do check(S3.handle(A,{action="get"}).ok,"request "..i.." inside the window") end
 local r2=S3.handle(A,{action="get"}) check(r2.ok==false and r2.reason=="rate_limited","one more in the same window is rate limited")
 check(S3.handle(B,{action="get"}).ok,"the limit is per player")
 check(S3.handle(A,"junk").reason=="rate_limited","bad shapes are rate limited too")
 now=100+S3.ActionWindowSeconds+1
 check(S3.handle(A,{action="get"}).ok,"a new window opens")
 local n=0 for i=1,S3.ActionsPerWindow+3 do if S3.handle(B,{action="bogus"}).reason=="rate_limited" then n+=1 end end
 check(n>=1,"a stream of bad requests gets limited")
end

do -- a skin never changes genes, traits or fusion inputs
 local start=baseline
 local now=copy(stored(5001))
 check(same(start.collection,now.collection) and same(start.progression,now.progression) and same(start.eggs,now.eggs) and same(start.rarityScale,now.rarityScale),"collection, wallet/progression and eggs are untouched by every skin action so far")
 check(sameData(skinFree({dinosaurIdentity=start.dinosaurIdentity}),skinFree({dinosaurIdentity=now.dinosaurIdentity})),"every instance (genes, shiny, big, mutation, stage, origin, cosmetics) is exactly as before, minus the skin field")
end
print("Service passed: lazy get, equip/unequip, ownership + model checks (also re-checked in the transaction), default, Base fallback, revoke, forward compat, junk, shapes, rate limit")
'''

FUSION = r'''
------------------------------------------------------------------ (D) fusion: eligibility and odds unchanged by skins; the output starts without a skin
do
 Cfg.DinoSkinsEnabled=true
 local donors={table.unpack(list1,1,6)}
 local q1=assert(Repo.quoteFusion(A,"gold",donors))
 -- six donors each wear Plush (owned via the gift above, model on sp1); the account default is Plush too
 for _,id in donors do
  local r=call2(A,{action="equip",instanceId=id,skin="Plush"}) check(r.ok,"donor wears Plush")
 end
 check(call2(A,{action="setDefault",skin="Plush"}).ok,"default Plush")
 local q2=assert(Repo.quoteFusion(A,"gold",donors))
 check(q1.quoteDigest==q2.quoteDigest and q1.consentDigest==q2.consentDigest and q1.consentRequired==q2.consentRequired and q1.requestDigest==q2.requestDigest,"the quote (digests, consent) is identical with and without skins")
 check(same(q1.odds,q2.odds) and same(q1.summary,q2.summary) and same(q1.lossManifest,q2.lossManifest) and q1.oddsVersion==q2.oddsVersion,"odds, ingredient summary and loss list do not see skins")
 -- a skinned donor is still eligible; lock/favourite protection is the only thing that stops a donor
 local owned=copy(stored(5001).ownedSkins)
 local ok,res,status=Repo.fuseDinosaurs(A,{token="skins-fuse-1",targetStage="gold",donorIds=donors,quoteDigest=q2.quoteDigest,consentDigest=q2.consentDigest})
 check(ok and status=="fused","a fusion of skinned donors works")
 local sc=stored(5001)
 local out=sc.dinosaurIdentity.instances[res.resultId]
 check(out and out.skin==nil and out.stage=="gold","the fused output is a NEW instance with no skin field")
 for _,id in donors do check(sc.dinosaurIdentity.instances[id]==nil,"donor consumed: "..id) end
 check(same(owned,sc.ownedSkins) and sc.ownedSkins.Plush==true,"the account-wide entitlement survives fusion")
 check(sc.defaultSkin=="Plush","the account default is untouched by fusion")
 local origin=out.origin
 check(origin.kind=="fusion" and out.cosmetics.equippedAuraId=="" and next(out.cosmetics.ownedAuraIds)==nil,"lineage and cosmetics are the fusion's own; no skin appears in the lineage")
 for _,parent in origin.parents do check(parent.skin==nil,"no parent snapshot carries a skin") end
 local keys={} for k in out do table.insert(keys,k) end table.sort(keys)
 local s=table.concat(keys,",") check(not string.find(s,"skin",1,true),"the output has no skin-like field: "..s)
 -- it starts on the account default: Plush here (default set, species has the model), Base once the default is cleared
 check(S2.resolve(A,res.resultId)=="Plush","a fused output with no choice wears the account default")
 check(call2(A,{action="setDefault",skin="Base"}).ok and S2.resolve(A,res.resultId)=="Base","with no default it is Base")
 -- the other copies of the species (not donors) keep their own choices
 local r=call2(A,{action="get",instanceId=res.resultId}) check(r.ok and r.skin==nil and r.wearing=="Base","get on the fused output: no choice")
end
print("Fusion passed: skins do not change the quote, odds or eligibility; the output has no skin and starts on the account default; entitlement survives")
'''

PICKER = r'''
------------------------------------------------------------------ (E) the pure picker model against the REAL server
do
 local P=makePicker(PatchedCatalog)
 Cfg.DinoSkinsEnabled=true
 local lows=nil for _,id in aIds do if speciesOf(5001,id)==sp1 and stored(5001).dinosaurIdentity.instances[id] and id~=dino then lows=id break end end
 -- shapes: every request the model builds is accepted by the real strict validator
 for _,req in {P.getRequest(),P.getRequest(lows),P.equipRequest(lows,"Base"),P.unequipRequest(lows),P.defaultRequest("Base")} do
  local r=call2(A,req) check(r.ok==true,"the model's "..req.action.." request is accepted by SkinService")
 end
 check(P.RemoteName=="SkinAction" and P.equipRequest("a","Plush").skin=="Plush","remote name and equip request")
 local function cardsFor(id)
  local answer=call2(A,P.getRequest(id))
  local view=P.view(answer)
  local byCard={} for _,c in P.cards(view,id) do byCard[c.id]=c end
  return view,byCard
 end
 -- Plush: owned + model for sp1; Clay: model for sp1, NOT owned; Bricks / Balloon: no model
 PatchedClay[sp1]=true
 local view,cards=cardsFor(lows)
 check(cards.Base.state=="worn" or cards.Base.state=="wear","Base is always there")
 check(cards.Plush.state=="wear" and cards.Plush.text=="Wear" and cards.Plush.request.action=="equip" and cards.Plush.request.skin=="Plush","an owned skin with a model: tap to wear")
 check(cards.Clay.state=="locked" and cards.Clay.text=="Locked" and cards.Clay.request==nil,"a model but not owned: locked, no request")
 check(cards.Bricks.state=="soon" and cards.Bricks.text=="Coming soon" and cards.Balloon.state=="soon" and cards.Bricks.request==nil,"no model for this species: Coming soon, no request")
 local r=call2(A,cards.Plush.request) check(r.ok and r.skin=="Plush","tapping the card works on the real server")
 local after=P.applyResult(view,cards.Plush.request,r)
 local after_cards={} for _,c in P.cards(after,lows) do after_cards[c.id]=c end
 check(after.wearing=="Plush" and after_cards.Plush.state=="worn" and after_cards.Plush.text=="Wearing" and after_cards.Base.state=="wear","after a good reply the picker shows Wearing without another request")
 check(P.applyResult(view,cards.Plush.request,{ok=false,reason="no_model"})==view and P.applyResult(view,{action="nope"},{ok=true})==view,"a failed or unknown reply changes nothing")
 local un=P.applyResult(after,P.unequipRequest(lows),{ok=true}) check(un.skin==nil,"unequip clears the choice in the view")
 local d=P.applyResult(view,P.defaultRequest("Plush"),{ok=true}) check(d.defaultSkin=="Plush","a good default reply updates the view")
 -- a species with no model at all: everything but Base is Coming soon (owned or not)
 local _,oc=cardsFor(otherId)
 check(oc.Plush.state=="soon" and oc.Clay.state=="soon" and oc.Plush.request==nil,"a species with no model shows Coming soon for every style")
 check(oc.Base.state=="worn" and oc.Base.isDefault==true,"Base is worn and the default there")
 -- unreadable answers never break the picker
 for _,junk in {nil,"x",5,{},{ok=false},{owned="x"},{owned={5,{},"Hologram"},defaultSkin=7,skin=9}} do
  local v=P.view(junk) check(next(v.owned)==nil and v.defaultSkin=="Base" and v.wearing=="Base","a junk answer reads as Base: "..tostring(junk))
  check(#P.cards(v,nil)==5,"five cards even then")
 end
 -- kid copy (docs/72): short, plain, no jargon
 local JARGON={"transform","ledger","window","idle","profile","instance","server","request","error","remote","entitlement","catalogue","model","flag"}
 for name,text in P.Copy do
  check(#text<=20 and not string.find(text,"%d"),"short copy "..name)
  for _,w in JARGON do check(not string.find(string.lower(text),w,1,true),"no jargon in "..name..": "..w) end
 end
 for code,text in P.Messages do
  check(#text<=36 and not string.find(text,"%d"),"short message "..code)
  for _,w in JARGON do check(not string.find(string.lower(text),w,1,true),"no jargon in "..code..": "..w) end
 end
 for _,code in {"not_owned","no_model","unknown_skin","rate_limited","disabled","profile_not_loaded","instance_missing","identity_unavailable"} do
  check(P.Messages[code]~=nil and P.message(code)==P.Messages[code],"copy for "..code)
 end
 check(P.message("save_failed")==P.FallbackMessage and P.message(nil)==P.FallbackMessage and P.message({})==P.FallbackMessage,"unknown codes read 'Try again.'")
 PatchedClay[sp1]=nil
end
print("Picker model passed: states, requests accepted by the real server, optimistic result, junk answers, kid copy")
'''

OLD = r'''
------------------------------------------------------------------ (F) migration and rollback rule RB1 against the frozen Build 020 reader
do
 local mods={}
 local names=setmetatable({},{__index=function(_,k) return k end})
 local script={Parent=names}
 local require=function(id) return assert(mods[id],"old module "..tostring(id)) end
 mods.Config=@@OLD_CONFIG@@
 mods.ProgressionConfig=@@OLD_PROGRESSION_CONFIG@@
 mods.EggGenetics=@@OLD_GENETICS@@
 mods.ProgressionRules=@@OLD_RULES@@
 mods.EggTraits=@@OLD_TRAITS@@
 local storage={Shared=names}
 local services={DataStoreService={GetDataStore=function() return store end},HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function() return false end}}
 local game={GameId=1,JobId="old-build-020",GetService=function(_,id) return services[id] end}
 local task={wait=function() end,spawn=function() end}
 local warn=function() end
 mods.RewardMath=@@OLD_REWARD_MATH@@
 local OldRepo=@@OLD_REPO@@

 -- MIGRATION: a profile that never touches skins stays byte-identical, flag on or off, and Build 020 loads it
 Cfg.DinoSkinsEnabled=true
 local C=hatchPlayer(5003,4) Repo.release(C)
 local before=copy(stored(5003))
 check(before.ownedSkins==nil and before.defaultSkin==nil,"a clean profile has none of the skin fields")
 for _,inst in before.dinosaurIdentity.instances do check(inst.skin==nil,"no instance has a skin") end
 local firstC for id in before.dinosaurIdentity.instances do firstC=id break end
 local C2=newUser(5003) assert(Repo.load(C2))
 local t0=transforms
 local cs=makeService(Cfg,PatchedCatalog) cs.start(Repo)
 check(cs.handle(C2,{action="get"}).ok and cs.handle(C2,{action="get",instanceId=firstC}).ok and cs.resolve(C2,firstC)=="Base","reads work")
 check(transforms==t0,"reading skins makes no store request")
 local r=cs.handle(C2,{action="unequip",instanceId=firstC}) check(r.ok and r.status=="unchanged","unequip with nothing set")
 r=cs.handle(C2,{action="setDefault",skin="Base"}) check(r.ok and r.status=="unchanged","clear a default that is not set")
 Repo.renew(C2) Repo.release(C2)
 check(sameData(before,stored(5003)),"flag on but never used: the stored profile is byte-identical apart from lease/revision/metrics")
 check(stored(5003).ownedSkins==nil and stored(5003).defaultSkin==nil,"no field was created by load, read, no-op, renew or release")
 -- RB1a: Build 020 loads it and leaves it alone
 local oc=newUser(5003)
 check(OldRepo.load(oc) and oc.attrs.ProfileState=="Loaded","RB1: Build 020 loads a profile that never touched skins")
 OldRepo.renew(oc) OldRepo.release(oc)
 check(sameData(before,stored(5003)),"Build 020 session leaves it equal")
 local back=newUser(5003) check(Repo.load(back),"roll-forward after a Build 020 session") Repo.release(back)

 -- RB1b: a profile that DID use skins: Build 020 loads it and keeps every new field byte-for-byte
 local F,fIds=hatchPlayer(5006,6) assert(#fIds>=2,"F hatched two dinos")
 check(giftSkin(F,"skin_plush","Agift-f1")=="applied" and giftSkin(F,"skin_bricks","Agift-f2")=="applied","two gifted skins")
 local fs=makeService(Cfg,PatchedCatalog) fs.start(Repo)
 local fSpecies=speciesOf(5006,fIds[1]) PatchedPlush[fSpecies]=true
 r=fs.handle(F,{action="equip",instanceId=fIds[1],skin="Plush"}) check(r.ok and r.status=="equipped","F wears Plush")
 r=fs.handle(F,{action="equip",instanceId=fIds[2],skin="Base"}) check(r.ok,"F's second dino wears explicit Base")
 r=fs.handle(F,{action="setDefault",skin="Bricks"}) check(r.ok and r.status=="default_set","F default Bricks")
 Repo.release(F)
 local used=copy(stored(5006))
 check(used.ownedSkins.Plush and used.ownedSkins.Bricks and used.defaultSkin=="Bricks" and used.dinosaurIdentity.instances[fIds[1]].skin=="Plush","the used profile carries ownedSkins, defaultSkin and instance skins")
 local of=newUser(5006)
 check(OldRepo.load(of) and of.attrs.ProfileState=="Loaded","RB1: Build 020 loads a profile that uses skins (unknown fields ignored)")
 OldRepo.renew(of) OldRepo.release(of)
 local g=stored(5006)
 check(same(used.ownedSkins,g.ownedSkins) and same(used.defaultSkin,g.defaultSkin) and same(used.dinosaurIdentity,g.dinosaurIdentity) and same(used.claimedGifts,g.claimedGifts),"Build 020 preserves ownedSkins, defaultSkin and every instance skin byte-for-byte")
 check(g.progression.crystals==used.progression.crystals,"the wallet is kept")
 local fwd=newUser(5006) check(Repo.load(fwd),"current code loads it again")
 local fr=makeService(Cfg,PatchedCatalog) fr.start(Repo)
 check(fr.resolve(fwd,fIds[1])=="Plush" and fr.handle(fwd,{action="get"}).defaultSkin=="Bricks","roll-forward: the choices are still there")
 Repo.release(fwd)
 -- flag turned OFF again: the fields stay exactly as they are
 Cfg.DinoSkinsEnabled=false
 local off=newUser(5006) assert(Repo.load(off)) Repo.renew(off) Repo.release(off)
 check(same(used.ownedSkins,stored(5006).ownedSkins) and same(used.defaultSkin,stored(5006).defaultSkin) and same(used.dinosaurIdentity,stored(5006).dinosaurIdentity),"flag off again: skin fields untouched")
 Cfg.DinoSkinsEnabled=true
 PatchedPlush[fSpecies]=nil
end
print("Migration + RB1 passed: a clean profile stays byte-identical, Build 020 loads and keeps skin fields, roll-forward and flag-off leave them")
print("Skins verified: "..checks.." checks")
'''


def fill(text: str) -> str:
    patched = read('src/shared/SkinCatalog.luau')
    for needle, replacement in (('    Plush = {},', '    Plush = PatchedPlush,'), ('    Clay = {},', '    Clay = PatchedClay,')):
        if needle not in patched:
            raise SystemExit(f'SkinCatalog.luau no longer contains {needle!r}: update the test-only patch in verify_skins.py')
        patched = patched.replace(needle, replacement)
    patched_module = '(function()\n' + patched + '\nend)()'
    # SkinService / SkinPickerModel / GiftRules require the catalogue through `script.Parent` / `ReplicatedStorage.Shared`: the harness gives each
    # its own `require`, so only the module text is inlined here.
    for token, value in (
        ('@@SKIN_CATALOG_PATCHED@@', patched_module),
        ('@@SKIN_CATALOG@@', module('src/shared/SkinCatalog.luau')),
        ('@@SKIN_SERVICE@@', module('src/server/SkinService.luau')),
        ('@@PICKER@@', module('src/shared/SkinPickerModel.luau')),
    ):
        text = text.replace(token, value)
    return verify_gifts.fill(text)


def script() -> str:
    prefix = verify_rewards.HARNESS.split('local function user(id)')[0]
    return fill(prefix + '\n' + HEAD + CATALOG + SERVICE + PICKER + FUSION + OLD)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--dump', type=Path, help='write the generated Luau script here (debugging)')
    args = parser.parse_args(argv)
    errors = static_errors()
    for error in errors:
        print('FAIL:', error)
    if errors:
        return 1
    print('Static checks passed: flag false in source and pinned off in default + playtest, pure modules, no Robux or art, skin-only writer, only SkinService calls it, fusion never sees skins')
    with tempfile.TemporaryDirectory() as directory:
        path = args.dump or Path(directory) / 'skins.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        print(result.stderr, end='')
        if result.returncode == 0 and 'Skins verified' in result.stdout:
            print('Skins verification passed (BD-456).')
            return 0
        return result.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())
