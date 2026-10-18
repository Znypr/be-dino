"""Execute the BD-065/BD-062 pure Fusion Menu logic (src/shared/FusionSelection.luau)
with the pinned Luau runtime. Covers filters, sorting, eligibility reasons, plain-only
auto-fill, odds formatting (exact 100% sums), retry-token reuse, reveal wheels landing
on committed values and Dino Details truthfulness. UI Instances are not executed here.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


def script():
    return ('local Config=' + module('src/shared/Config.luau') + '\n'
            + 'local Progression=' + module('src/shared/ProgressionConfig.luau') + '\n'
            + 'local script={Parent={ProgressionConfig=Progression}}\nlocal function require(x) return x end\n'  # BD-1033: kid pattern names come from the config
            + 'local S=' + module('src/shared/FusionSelection.luau') + '\n' + r'''
local Patterns={"01_blank","02_emerald_islands","03_round_spots","04_bold_patches","05_horizontal_bands","06_wavy_stripes","07_diamond_scales","08_freckles"}
local cat=S.buildCatalog(Config,Progression,Patterns)
local n=0
local function dino(over)
 n+=1
 local d={instanceId="u:1/d:"..n,speciesId="compy",stage="base",
  genes={patternId="06_wavy_stripes",primaryColorId="green",secondaryColorId="blue",blend=20},
  big=false,shiny=false,mutationId="",originKind="hatch",locked=false,favorited=false,auraCount=0,trailCount=0,equippedAuraId="",equippedTrailId=""}
 for k,v in over or {} do if k=="genes" then for gk,gv in v do d.genes[gk]=gv end else d[k]=v end end
 return d
end
local function ids(list) local r={} for _,d in list do table.insert(r,d.instanceId) end return r end
local function has(t,v) return table.find(t,v)~=nil end

-- Fixture: 17 plain wavy compies (Gold = 6 Base) + valuables + mismatches.
local all={}
local plain={}
for i=1,17 do local d=dino() table.insert(all,d) table.insert(plain,d.instanceId) end
local shiny=dino({shiny=true}) local big=dino({big=true}) local ember=dino({mutationId="ember"})
local aura=dino({auraCount=2}) local trail=dino({trailCount=1,equippedTrailId="fern"})
local locked=dino({locked=true}) local fav=dino({favorited=true})
local spots=dino({genes={patternId="03_round_spots"}}) local raptor=dino({speciesId="raptor"})
local gold=dino({stage="gold"}) local legacy=dino({originKind="legacy_unknown"}) legacy.genes={}
local rainbow=dino({genes={primaryColorId="red"}})
for _,d in {shiny,big,ember,aura,trail,locked,fav,spots,raptor,gold,legacy,rainbow} do table.insert(all,d) end
local byId=S.index(all)

-- ===== Nav gating, egg slot look, Dino Index silhouette =====
assert(S.navTarget({menuLoaded=true,remote=true,probe="ok",profile="playtest"})=="menu")
assert(S.navTarget({menuLoaded=true,remote=true,probe=nil,profile="release"})=="menu")
assert(S.navTarget({menuLoaded=true,remote=true,probe="disabled",profile="development"})=="unavailable") -- BD-617: no old page any more
assert(S.navTarget({menuLoaded=true,remote=false,profile="development"})=="unavailable")
assert(S.navTarget({menuLoaded=false,remote=true,profile="development"})=="unavailable")
assert(S.navTarget({menuLoaded=true,remote=true,probe="disabled",profile="playtest"})=="unavailable")
assert(S.navTarget({menuLoaded=true,remote=false,profile="release"})=="unavailable")
assert(S.eggSlotLook(nil,false)=="empty")
assert(S.eggSlotLook({genes={}},true)=="genes")
assert(S.eggSlotLook({genes={}},false)=="plain")
assert(S.eggSlotLook({rarity=1},false)=="plain")
local hidden=S.indexCard(false)
assert(hidden.silhouette and hidden.locked and hidden.nameText=="???" and hidden.rarityText=="???" and hidden.status=="Not discovered" and hidden.showButton==false)
local shown=S.indexCard(true)
assert(not shown.silhouette and not shown.locked and shown.nameText==nil and shown.rarityText==nil and shown.showButton==true)

-- ===== Eligibility reasons =====
local ctx={targetStage="gold",speciesId="compy",patternId="06_wavy_stripes"}
assert(S.ineligibility(all[1],ctx)==nil)
assert(S.ineligibility(gold,ctx)=="wrong_stage")
assert(S.ineligibility(legacy,ctx)=="missing_pattern")
assert(S.ineligibility(locked,ctx)=="locked")
assert(S.ineligibility(fav,ctx)=="favorited")
assert(S.ineligibility(spots,ctx)==nil,"Gold takes any pattern of the species")
local goldSpots=dino({stage="gold",genes={patternId="03_round_spots"}})
assert(S.ineligibility(goldSpots,{targetStage="emerald",speciesId="compy",patternId="06_wavy_stripes"})=="pattern_mismatch")
assert(S.ineligibility(goldSpots,{targetStage="emerald",speciesId="compy"})==nil)
assert(S.ineligibility(raptor,ctx)=="species_mismatch")
assert(S.ineligibility(all[1],{targetStage="emerald"})=="wrong_stage")
assert(S.ineligibility(all[1],{targetStage="diamond"})=="wrong_stage")
assert(S.ineligibility(gold,{targetStage="emerald"})==nil)
assert(S.ineligibility(all[1],{targetStage="platinum"})=="recipe_not_approved")
for _,code in {"wrong_stage","missing_pattern","locked","favorited","pattern_mismatch","species_mismatch","recipe_not_approved","full"} do assert(S.ReasonText[code],code) end
-- Valuables are ELIGIBLE (manual selection allowed) but not plain.
for _,d in {shiny,big,ember,aura,trail} do assert(S.ineligibility(d,ctx)==nil and not S.isPlain(d)) end
assert(#S.valuableReasons(trail)==1 and S.valuableReasons(trail)[1]=="cosmetics")
-- Owner decision 2026-10-15: ladder 6/3/2 (Gold any pattern), all tiers active.
assert(S.stage("gold").approved and S.stage("emerald").approved and S.stage("diamond").approved)
assert(S.donorCount("gold")==6 and S.donorCount("emerald")==3 and S.donorCount("diamond")==2 and S.donorCount("platinum")==nil)
assert(S.stage("gold").anyPattern==true and S.stage("emerald").anyPattern==nil and S.stage("diamond").anyPattern==nil)
assert(S.stage("emerald").source=="gold" and S.stage("diamond").source=="emerald" and S.stageTitle("base")=="Base")

-- ===== Filters =====
assert(#S.filter(all,{shiny=true})==1)
assert(#S.filter(all,{big=false})==#all-1)
assert(#S.filter(all,{mutationId="ember"})==1 and #S.filter(all,{mutationId="none"})==#all-1)
assert(#S.filter(all,{speciesId="raptor"})==1)
assert(#S.filter(all,{patternId="03_round_spots"})==1)
assert(#S.filter(all,{stage="gold"})==1)
assert(#S.filter(all,{colorId="red"})==1 and #S.filter(all,{colorId="blue"})==#all-1)
assert(#S.filter(all,{conditionId="rainbow"})==#all,"dinosaurs have no condition: a stale condition filter is ignored")
assert(#S.filter(all,{originKind="legacy_unknown"})==1)
assert(#S.filter(all,{cosmetics="has"})==2 and #S.filter(all,{cosmetics="equipped"})==1 and #S.filter(all,{cosmetics="none"})==#all-2)
assert(#S.filter(all,{speciesId="compy",patternId="06_wavy_stripes",shiny=false,stage="base"})==#all-5)
local opts=S.filterOptions(all,cat)
assert(opts.speciesId[1]=="compy" and opts.speciesId[2]=="raptor")
assert(has(opts.mutationId,"ember") and has(opts.mutationId,"none"))
assert(opts.conditionId==nil,"no condition filter options for dinosaurs")
assert(S.cycle(opts.speciesId,nil)=="compy" and S.cycle(opts.speciesId,"compy")=="raptor" and S.cycle(opts.speciesId,"raptor")==nil)

-- ===== Sorting =====
local sorted=S.sort(all,"eligible",ctx,nil,cat)
for i=1,19 do assert(S.isPlain(sorted[i]) and S.ineligibility(sorted[i],ctx)==nil,"plain eligible first "..i) end
for i=20,24 do assert(not S.isPlain(sorted[i]) and S.ineligibility(sorted[i],ctx)==nil,"valuable eligible next "..i) end
for i=25,#sorted do assert(S.ineligibility(sorted[i],ctx)~=nil,"ineligible last "..i) end
local rarest=S.sort(all,"rarest",ctx,nil,cat)
assert(rarest[1]==shiny and rarest[2]==ember and rarest[3]==big,"rarity order")
-- Cosmetics never raise rarity.
assert(S.rarityScore(aura)==S.rarityScore(all[1]) and S.rarityScore(trail)==S.rarityScore(all[1]))
local recent=S.sort(all,"recent",ctx,nil,cat)
assert(recent[1]==rainbow and recent[#recent]==all[1])
local species=S.sort(all,"species",ctx,nil,cat)
assert(species[#species]==raptor)
for _,key in S.SortKeys do assert(key~="condition") end
local sel=S.sort(all,"selected",ctx,{[raptor.instanceId]=true},cat)
assert(sel[1]==raptor)
-- Deterministic: same input gives same order twice.
assert(table.concat(ids(S.sort(all,"color",ctx,nil,cat)),",")==table.concat(ids(S.sort(all,"color",ctx,nil,cat)),","))

-- ===== Toggle =====
local s,ok,why={},nil,nil
s,ok,why=S.toggle(s,shiny,"gold",byId) assert(ok and #s==1,"manual valuable select allowed")
s,ok,why=S.toggle(s,spots,"gold",byId) assert(ok and #s==2,"any pattern for Gold") s=S.toggle(s,spots,"gold",byId) assert(#s==1)
s,ok,why=S.toggle(s,raptor,"gold",byId) assert(not ok and why=="species_mismatch")
s,ok,why=S.toggle(s,locked,"gold",byId) assert(not ok and why=="locked")
s,ok,why=S.toggle(s,all[1],"emerald",byId) assert(not ok and why=="wrong_stage")
s,ok,why=S.toggle(s,all[1],"platinum",byId) assert(not ok and why=="recipe_not_approved")
s,ok,why=S.toggle(s,shiny,"gold",byId) assert(ok and #s==0,"deselect")
local full={} for i=1,6 do full=S.toggle(full,all[i],"gold",byId) end
assert(#full==6)
local _,okFull,whyFull=S.toggle(full,all[7],"gold",byId) assert(not okFull and whyFull=="full")

-- ===== Auto-fill never picks valuables =====
local filled,added,short=S.autoFill(all,{},"gold",nil,cat)
assert(#filled==6 and added==6 and short==0)
for _,id in filled do assert(has(plain,id),"auto-fill picked non-plain "..id) end
-- Keeps a manual Shiny and fills only plain copies around it.
local manual=S.toggle({},shiny,"gold",byId)
filled,added,short=S.autoFill(all,manual,"gold",nil,cat)
assert(#filled==6 and added==5 and filled[1]==shiny.instanceId)
for i=2,6 do assert(has(plain,filled[i])) end
-- Shortfall when not enough plain copies: never tops up with valuables.
local few={shiny,big,ember,aura,trail,locked,fav,all[1],all[2],all[3]}
filled,added,short=S.autoFill(few,{},"gold",nil,cat)
assert(added==3 and short==3 and #filled==3)
for _,id in filled do assert(byId[id].shiny==false and byId[id].big==false and byId[id].mutationId=="" and not S.hasCosmetics(byId[id])) end
-- Anchored to selected species/pattern.
local anchored=S.autoFill({spots,dino({genes={patternId="03_round_spots"}}),all[1],all[2]},{spots.instanceId},"gold",nil,cat)
assert(#anchored==4 and byId[anchored[1]]==spots,"Gold auto-fill ignores pattern")
local plain_base={} for _,d in all do if d.stage=="base" then table.insert(plain_base,d) end end
-- Base dinos never fill a higher tier; unknown stages fill nothing.
local none,a2=S.autoFill(plain_base,{},"emerald",nil,cat) assert(#none==0 and a2==0)
local none2,a3,short3=S.autoFill(all,{},"platinum",nil,cat) assert(#none2==0 and a3==0 and short3==0)
-- Emerald auto-fills exactly 3 plain Golds; Diamond exactly 2 plain Emeralds (genes from fused records).
local tier={}
for i=1,12 do table.insert(tier,dino({stage="gold"})) end
for i=1,4 do table.insert(tier,dino({stage="emerald"})) end
table.insert(tier,dino({stage="gold",genes={patternId="03_round_spots"}}))
table.insert(tier,dino({stage="gold",shiny=true}))
local te=S.autoFill(tier,{},"emerald",nil,cat) assert(#te==3)
local tIdx=S.index(tier)
for _,id in te do assert(tIdx[id].stage=="gold" and tIdx[id].genes.patternId=="06_wavy_stripes" and not tIdx[id].shiny) end
local td,addD,shortD=S.autoFill(tier,{},"diamond",nil,cat) assert(#td==2 and addD==2 and shortD==0)
for _,id in td do assert(tIdx[id].stage=="emerald") end
local tdFull=td local _,okD,whyD=S.toggle(tdFull,tier[16],"diamond",tIdx) assert(not okD and whyD=="full")
-- Larger fuzz: random populations never auto-fill valuables or mismatches.
local seed=7
local function rnd() seed=(seed*1103515245+12345)%2147483648 return seed/2147483648 end
for trial=1,200 do
 local pop={}
 for i=1,math.floor(rnd()*30)+1 do
  table.insert(pop,dino({shiny=rnd()<.2,big=rnd()<.2,mutationId=if rnd()<.2 then "frost" else "",auraCount=if rnd()<.1 then 1 else 0,
   locked=rnd()<.1,favorited=rnd()<.1,speciesId=if rnd()<.5 then "compy" else "raptor",stage=if rnd()<.9 then "base" else "gold",
   genes={patternId=if rnd()<.5 then "06_wavy_stripes" else "02_emerald_islands"}}))
 end
 local idx=S.index(pop)
 local out=S.autoFill(pop,{},"gold",nil,cat)
 assert(#out<=6)
 local first=out[1] and idx[out[1]]
 for _,id in out do
  local d=idx[id]
  assert(S.isPlain(d) and d.stage=="base" and d.speciesId==first.speciesId,"fuzz "..trial)
 end
end

-- ===== Histogram & badges =====
local h=S.histogram({shiny.instanceId,ember.instanceId,aura.instanceId,all[1].instanceId},byId)
assert(h.count==4 and h.shiny==1 and h.mutations.ember==1 and h.cosmetics==1 and h.valuable==3)
local b=S.badges(trail,cat) assert(b[1]=="1 FX")
assert(table.concat(S.badges(ember,cat),",")=="Ember")

-- ===== Odds formatting: always sums to exactly 100% =====
local function units(section) local t=0 for _,r in section.rows do t+=r.units end return t,section.rows[1].decimals end
local odds={shiny=.1,big=.05,mutation={ember=.1,frost=.05},noMutation=.85,
 primaryColor={green=1/3,blue=1/3,white=1/3},secondaryColor={blue=.7,teal=.2999,black=.0001}}
local f=S.formatOdds(odds,cat)
assert(f.ok,tostring(f.error))
for _,section in f.sections do
 local t,dec=units(section)
 assert(t==100*10^dec,section.title.." sums "..t)
end
local function row(section,id) for _,r in section.rows do if r.id==id then return r end end end
assert(row(f.sections[1],"yes").text=="10%" and row(f.sections[1],"no").text=="90%")
assert(f.sections[1].rows[1].id=="yes","yes/no fixed order")
assert(f.sections[5].rows[1].id=="blue","maps sorted by probability")
assert(#f.sections==5)
for _,section in f.sections do assert(section.trait~="condition") end
assert(row(f.sections[2],"none").text=="85%" and row(f.sections[2],"ember").label=="Ember")
local thirds=f.sections[4]
local tt=units(thirds) assert(tt==1000)
local labels={} for _,r in thirds.rows do table.insert(labels,r.text) end
assert(table.concat(labels,",")=="33.4%,33.3%,33.3%","largest remainder "..table.concat(labels,","))
local c2=f.sections[5] assert(c2.rows[1].decimals==2 and row(c2,"black").text=="0.01%")
-- 2/10 Shiny proposed example renders as 10%.
local r=S.percentRows({{id="yes",label="Shiny",p=.1},{id="no",label="Not",p=.9}})
assert(r[1].text=="10%")
-- Tiny nonzero never displays as a flat 0%.
r=S.percentRows({{id="a",p=.0000001},{id="b",p=.9999999}})
assert(r[1].text=="<0.001%" and r[1].units+r[2].units==100000)
-- Malformed odds are rejected (UI must not offer confirmation).
assert(S.percentRows({{id="a",p=.5},{id="b",p=.4}})==nil)
assert(S.percentRows({{id="a",p=0/0},{id="b",p=1}})==nil)
assert(not S.formatOdds({shiny=.1},cat).ok)
assert(not S.formatOdds(nil,cat).ok)
-- Fuzz exact sums.
for trial=1,300 do
 local rows,total={},0
 for i=1,math.floor(rnd()*9)+1 do local w=rnd()^3 table.insert(rows,{id="c"..i,p=w}) total+=w end
 if total>0 then
  for _,x in rows do x.p=x.p/total end
  local out=assert(S.percentRows(rows))
  local sum=0 for _,x in out do sum+=x.units end
  assert(sum==100*10^out[1].decimals,"fuzz sum "..trial)
 end
end

-- ===== Loss summary =====
local quote={speciesId="compy",patternId="06_wavy_stripes",targetStage="gold",consentRequired=true,quoteDigest="q1",consentDigest="c1",
 odds=odds,lossManifest={
  {instanceId=aura.instanceId,auraIds={"meadow","tidal"},trailIds={},equippedAuraId="meadow",equippedTrailId=""},
  {instanceId=trail.instanceId,auraIds={},trailIds={"fern"},equippedAuraId="",equippedTrailId="fern"},
  {instanceId=shiny.instanceId,auraIds={},trailIds={},shiny=true},
  {instanceId=ember.instanceId,auraIds={},trailIds={},mutationId="ember",big=true}}}
local loss=S.lossSummary(quote,cat)
assert(loss.auraCount==2 and loss.trailCount==1 and loss.needsConfirm and loss.consentRequired)
assert(loss.cosmeticText=="2 auras and 1 trail will be lost: Meadow Glow, Tidal Halo, Fern Drift",loss.cosmeticText)
assert(#loss.valuables==2 and loss.valuables[1].text=="Shiny" and loss.valuables[2].text=="BIG + Ember")
local noLoss=S.lossSummary({consentRequired=false,lossManifest={}},cat)
assert(not noLoss.needsConfirm and noLoss.auraCount==0)

-- ===== Token reuse =====
local tokens=0
local function newToken() tokens+=1 return "tok-"..tokens end
local donors=table.clone(plain) table.remove(donors) table.remove(donors)
local at,reused=S.attempt(nil,"gold",donors,"q1",newToken)
assert(not reused and at.token=="tok-1")
-- Network failure: retry keeps the same token.
local o=S.settle(at,nil) assert(o.kind=="retry" and o.attempt==at)
local reversed={} for i=#donors,1,-1 do table.insert(reversed,donors[i]) end
local again,re2=S.attempt(at,"gold",reversed,"q1",newToken)
assert(re2 and again.token=="tok-1" and again.tries==2,"same request any order reuses token")
o=S.settle(again,{ok=false,reason="save_failed"}) assert(o.kind=="retry")
o=S.settle(again,{ok=false,reason="rate_limited"}) assert(o.kind=="retry")
-- Server duplicate returns committed result; attempt settles.
local committed={resultId="u:1/d:99",targetStage="gold",speciesId="compy",patternId="06_wavy_stripes",oddsVersion="v1",
 traits={big=false,shiny=true,mutationId="ember",genes={patternId="06_wavy_stripes",primaryColorId="blue",secondaryColorId="teal",blend=55}}}
o=S.settle(again,{ok=true,status="duplicate",result=committed}) assert(o.kind=="success" and o.status=="duplicate" and again.state=="settled")
-- A settled attempt is never reused for a new confirmation.
local fresh,re3=S.attempt(again,"gold",donors,"q1",newToken) assert(not re3 and fresh.token=="tok-2")
-- Changed request (new quote digest) => new token.
local changed,re4=S.attempt(fresh,"gold",donors,"q2",newToken) assert(not re4 and changed.token=="tok-3")
-- Requote/fatal failures abandon the token.
for _,reason in {"stale_quote","consent_required","donor_missing","donor_locked","wrong_donor_count","species_mismatch","pattern_mismatch"} do
 local a=S.attempt(nil,"gold",donors,reason,newToken)
 local out=S.settle(a,{ok=false,reason=reason})
 assert(out.kind=="requote" and out.attempt==nil and a.state=="abandoned" and out.message~="",reason)
end
for _,reason in {"fusion_disabled","recipe_not_approved","odds_not_approved","storage_limit"} do
 local out=S.settle(S.attempt(nil,"gold",donors,reason,newToken),{ok=false,reason=reason})
 assert(out.kind=="fatal" and S.FailureText[reason],reason)
end
assert(S.settle(nil,{ok=false,reason="lease_lost"}).kind=="retry")
assert(string.find(S.failureMessage("weird_new_reason"),"weird new reason"))

-- ===== Reveal sequence lands on committed values =====
local seq=S.revealSequence(quote,committed,cat)
assert(seq[1].kind=="pattern" and seq[1].value=="Waves")
local order={} for _,st in seq do table.insert(order,st.trait or st.kind) end
assert(table.concat(order,",")=="pattern,primaryColor,secondaryColor,shiny,mutation,big,final",table.concat(order,","))
local expect={primaryColor="blue",secondaryColor="teal",shiny="yes",mutation="ember",big="no"}
for _,st in seq do
 if st.kind=="wheel" then
  local seg=st.segments[st.landingIndex]
  assert(seg.id==expect[st.trait] and st.committed==expect[st.trait],st.trait)
  local total=st.segments[#st.segments].to
  assert(st.landingFraction>=seg.from/total and st.landingFraction<=seg.to/total,st.trait.." inside segment")
  local rot=S.wheelRotation(st,4)
  local pointer=(1-((rot%360)/360))%1
  assert(math.abs(pointer-st.landingFraction)<1e-9,"rotation lands "..st.trait)
  local reel=S.reelOffset(st,3)
  assert(math.abs((reel%1)-st.landingFraction)<1e-9 and reel>=3,"reel lands "..st.trait)
  for _,sgm in st.segments do assert(sgm.p>=0) end
 end
end
-- BD-1003: the reel pointer is two edge notches; the label band in the middle is free, text stays 14 px or more.
do
 local top,bottom=S.reelLabelBand()
 assert(S.reelPointerClear() and S.Reel.notchHeight<=top and S.Reel.height-S.Reel.notchHeight>=bottom and S.Reel.labelTextSize>=14,"the pointer never crosses a label")
 assert(S.Reel.notchHeight*2<S.Reel.height/2,"the notches are small")
end
assert(seq[3].detail=="Blend 55% / 45%")
assert(seq[4].value=="Shiny" and seq[5].value=="Ember" and seq[6].value=="Not BIG")
assert(seq[#seq].kind=="final" and seq[#seq].title=="NEW WAVES COMPY" and seq[#seq].replay==false)
-- Committed value outside the quoted odds: shown plainly, never animated as a guess.
local odd=table.clone(committed) odd.traits=table.clone(committed.traits) odd.traits.genes=table.clone(committed.traits.genes)
odd.traits.genes.primaryColorId="black"
local seq2=S.revealSequence(quote,odd,cat)
assert(seq2[2].kind=="card" and seq2[2].mismatch and seq2[2].value=="black")
-- Re-open / duplicate without the quote: no wheels, only pattern + final.
local replay=S.revealSequence(nil,committed,cat)
assert(#replay==2 and replay[1].kind=="pattern" and replay[2].kind=="final" and replay[2].replay==true)
-- Fuzz: random odds + random committed outcomes always land.
for trial=1,200 do
 local m={} local colors={"white","blue","green","teal","pink"} local tot=0
 for _,cid in colors do local w=rnd()+.01 m[cid]=w tot+=w end
 for k,v in m do m[k]=v/tot end
 local pick=colors[math.floor(rnd()*5)+1]
 local q={odds={shiny=rnd(),big=rnd(),mutation={frost=.2},noMutation=.8,primaryColor=m,secondaryColor=m}}
 local res={patternId="02_emerald_islands",speciesId="raptor",targetStage="gold",traits={shiny=rnd()<.5,big=rnd()<.5,mutationId=if rnd()<.5 then "frost" else "",
  genes={patternId="02_emerald_islands",primaryColorId=pick,secondaryColorId=pick,blend=100}}}
 for _,st in S.revealSequence(q,res,cat) do
  if st.kind=="wheel" then assert(st.segments[st.landingIndex].id==st.committed) end
  if st.kind=="card" then error("unexpected mismatch "..trial) end
 end
end

-- ===== Dino Details =====
local hatched={instanceId="u:1/d:5",speciesId="compy",stage="base",genes={patternId="06_wavy_stripes",primaryColorId="green",secondaryColorId="blue",blend=20},
 shiny=false,big=false,mutationId="",origin={kind="hatch",eggId="egg-1"},
 originalEgg={eggId="egg-1",kind="alpha_chest",eventId="rain",genes={patternId="06_wavy_stripes",primaryColorId="green",secondaryColorId="blue",blend=20,conditionId="normal"}},
 cosmetics={ownedAuraIds={"meadow"},ownedTrailIds={},equippedAuraId="meadow",equippedTrailId=""}}
local hv=S.details(hatched,cat)
assert(hv.origin.kind=="hatched" and hv.title=="Waves Compy")
assert(string.find(hv.origin.lines[1],"Event: Rain",1,true) and string.find(hv.origin.lines[1],"Run reward egg",1,true) and string.find(hv.origin.lines[1],"Green 20% / Blue 80%",1,true))
assert(hv.prestige=="Natural hatch")
assert(hv.cosmetics[1]=="Auras: Meadow Glow" and string.find(hv.cosmetics[4],"never count",1,true))
local fused={instanceId="u:1/d:99",speciesId="compy",stage="gold",genes=committed.traits.genes,shiny=true,big=false,mutationId="ember",
 origin={kind="fusion",operationId="fusion:tok-1",recipeVersion="r1",oddsVersion="o1",parents={
  {instanceId="u:1/d:1",speciesId="compy",stage="base",genes={patternId="06_wavy_stripes"},shiny=true,origin={kind="hatch",eggId="egg-1"}},
  {instanceId="u:1/d:2",speciesId="compy",stage="base",genes={patternId="06_wavy_stripes"},origin={kind="legacy_unknown"}}}},
 lineage={parentIds={"u:1/d:1","u:1/d:2"},recipeVersion="r1",oddsVersion="o1",parentEggs={["egg-1"]=hatched.originalEgg}},
 cosmetics={ownedAuraIds={},ownedTrailIds={},equippedAuraId="",equippedTrailId=""}}
local fv=S.details(fused,cat)
assert(fv.origin.kind=="fused" and fv.prestige=="Crafted Gold (earned)")
assert(fv.title=="Gold Waves Compy")
assert(fv.origin.lines[1]=="Fused from 2 dinos" and fv.origin.lines[2]=="Recipe r1 • Odds o1")
assert(#fv.origin.parents==2 and string.find(fv.origin.parents[1].egg,"Run reward egg",1,true) and fv.origin.parents[1].text=="Waves Compy • Shiny")
assert(fv.origin.parents[2].egg=="Original egg not recorded")
-- Never a fake Gold drop percentage; no "%" anywhere in prestige/origin text for stage.
assert(not string.find(fv.prestige,"%",1,true))
for _,line in fv.origin.lines do assert(not string.find(line,"drop",1,true) or string.find(line,"not a drop",1,true)) end
assert(fv.cosmetics[1]=="Auras: None (buy for this dino)" and fv.cosmetics[2]=="Trails: Free/default only")
local old=S.details({instanceId="u:1/d:3",speciesId="raptor",stage="gold",origin={kind="legacy_unknown"}},cat)
assert(old.origin.kind=="unknown" and string.find(old.origin.lines[1],"not guessed",1,true) and old.title=="Gold Unknown pattern Raptor")
-- 15-parent compact lineage (no per-parent speciesId/patternId): bounded view.
local bigParents,bigIds={},{}
for i=1,15 do table.insert(bigParents,{instanceId="u:1/d:"..(1000+i),genes={primaryColorId="green"},shiny=i==1,origin={kind="hatch",eggId="egg-"..i}}) table.insert(bigIds,"u:1/d:"..(1000+i)) end
local gv=S.details({instanceId="u:1/d:2000",speciesId="compy",stage="gold",genes={patternId="06_wavy_stripes"},origin={kind="fusion",recipeVersion="gold-same-species-6-v2",oddsVersion="o",parentStage="base",parents=bigParents},
 lineage={parentIds=bigIds,parentEggs={}},cosmetics={}},cat)
assert(gv.origin.lines[1]=="Fused from 15 dinos" and #gv.origin.parents==S.DetailsParentLimit)
assert(gv.origin.parents[1].text=="Waves Compy • Shiny","compact snapshot falls back to result species/pattern")
local showing=false for _,l in gv.origin.lines do if l=="Showing 12 of 15 parents" then showing=true end end assert(showing)
-- Cosmetics do not change rarity/prestige output.
local plainFused=table.clone(fused) plainFused.cosmetics={ownedAuraIds={"royal"},ownedTrailIds={"astra"},equippedAuraId="royal",equippedTrailId="astra"}
assert(S.details(plainFused,cat).prestige==fv.prestige)

-- ===== Fusion Menu v2 helpers (docs/96): plain words, auto-filter, goal sentence, odds chips =====
assert(S.tabText("gold").title=="GOLD" and S.tabText("gold").sub=="6 Base" and S.tabText("emerald").sub=="3 Gold" and S.tabText("diamond").sub=="2 Emerald")
local vis=S.visibleFor(all,"gold",nil)
assert(#vis==#all-1,"Gold lists Base copies only (the gold copy is hidden): "..#vis)
assert(#S.visibleFor(all,"emerald",nil)==1 and #S.visibleFor(all,"diamond",nil)==0 and #S.visibleFor(all,"platinum",nil)==0)
assert(#S.visibleFor(all,"gold",{speciesId="raptor"})==1,"optional filters still apply")
local bg=S.bestGroup(all,"gold") assert(bg.speciesId=="compy" and bg.count==24 and bg.patternId==nil,"best group "..bg.count)
assert(S.bestGroup(tier,"emerald").count==13 and S.bestGroup(tier,"emerald").patternId=="06_wavy_stripes","Emerald groups by pattern too")
assert(S.bestGroup(all,"platinum")==nil)
assert(S.goalText(all,"gold",{},byId,cat)=="Tap 6 Compy, or Fill for me.",S.goalText(all,"gold",{},byId,cat))
assert(S.goalText({all[1],all[2]},"gold",{},byId,cat)=="You need 6 Compy to make a Gold Compy. You have 2.")
assert(S.article("Gold")=="a" and S.article("Emerald")=="an" and S.article("Diamond")=="a")
assert(S.geneLine({primaryColorId="white",secondaryColorId="white",blend=100},cat)==S.geneLine({primaryColorId="white",secondaryColorId="blue",blend=100},cat))
assert(not string.find(S.geneLine({primaryColorId="white",secondaryColorId="white",blend=100},cat),"%",1,true))
assert(S.goalText({},"gold",{},byId,cat)=="You need 6 Base dinos of one kind. You have 0.")
assert(S.goalText(all,"gold",{all[1].instanceId,all[2].instanceId},byId,cat)=="Tap 4 more Compy.")
assert(S.goalText(all,"gold",full,byId,cat)=="Ready! Tap FUSE.")
assert(S.goalText(all,"platinum",{},byId,cat)==S.LockedStageText)
local chips=S.oddsChips(odds,cat)
assert(chips.ok and #chips.sections==5)
-- BD-344: headings in reading order Colour 1, Colour 2, (Pattern), Shiny, Event, BIG; "Yes/No" chips, no duplicate unlabeled names
assert(chips.sections[1].title=="Colour 1" and chips.sections[2].title=="Colour 2" and chips.sections[2].chips[1].label=="Blue 70%")
assert(chips.sections[3].title=="Shiny" and chips.sections[3].chips[1].label=="Yes 10%" and chips.sections[3].chips[2].label=="No 90%")
assert(chips.sections[4].title=="Event" and chips.sections[4].chips[1].label=="None 85%" and chips.sections[4].chips[2].label=="Ember 10%")
assert(chips.sections[5].title=="BIG" and chips.sections[5].chips[1].label=="Yes 5%" and chips.sections[5].chips[2].label=="No 95%")
local withPattern=S.oddsChips(odds,cat,"06_wavy_stripes")
assert(#withPattern.sections==6 and withPattern.sections[3].title=="Pattern" and withPattern.sections[3].chips[1].label:find("%(locked%)"))
for _,sec in withPattern.sections do assert(type(sec.title)=="string" and sec.title~="" and #sec.chips>0) end
assert(S.sectionHeight(1,3)==S.ChipHeadingHeight+(S.ChipHeight+S.ChipGap) and S.sectionHeight(7,3)==S.ChipHeadingHeight+3*(S.ChipHeight+S.ChipGap))
assert(S.chipColumns(360,110)==3 and S.chipColumns(200,110)==1 and S.chipColumns(90,110)==1 and S.chipColumns(1000,110)==4)
-- BD-345: preview traits keep the fused output's OWN genes (never a donor's, never a mutation tint on a fused tier)
local pt=S.previewTraits({stage="gold",genes={patternId="06_wavy_stripes",primaryColorId="cream",secondaryColorId="blue",blend=60},shiny=true,mutationId="ember"})
assert(pt.genes.primaryColorId=="cream" and pt.genes.patternId=="06_wavy_stripes" and pt.shiny==true and pt.big==false and pt.mutationId==nil)
assert(S.previewTraits({stage="base",genes={primaryColorId="green"},mutationId="ember"}).mutationId=="ember")
assert(S.previewTraits({stage="emerald",genes={}}).genes==nil and S.previewTraits(nil)==nil)
-- BD-346: step pacing, chance bar, Fill for me explanations, consumed donors leave the list
for _,k in {"pattern","wheel","card"} do for _,m in {true,false} do assert(S.stepSeconds(k,m,.1)>=1.2) end end
assert(S.stepSeconds("wheel",true,1.7)>S.stepSeconds("wheel",false,1.7))
local bar=S.chanceBar({segments={{id="yes",p=.1},{id="no",p=.9}},committed="yes"})
assert(bar.landedYes and bar.outcome=="YES!" and math.abs(bar.marker-.05)<1e-9 and math.abs(bar.yesShare-.1)<1e-9)
local bar2=S.chanceBar({segments={{id="yes",p=.1},{id="no",p=.9}},committed="no"})
assert(not bar2.landedYes and bar2.outcome=="Not this time" and bar2.marker>bar2.yesShare and bar2.marker<1)
local fillA={dino(),dino(),dino()}
local idx=S.index(fillA)
assert(S.autoFillMessage(fillA,{},{fillA[1].instanceId},"gold",idx,cat):find("need 5 more"))
local six={} for i=1,6 do table.insert(six,fillA[1].instanceId) end
assert(S.autoFillMessage(fillA,{fillA[1].instanceId},six,"gold",idx,cat)=="Filled! Tap FUSE.")
local msgEmerald=S.autoFillMessage(fillA,{fillA[1].instanceId},{fillA[1].instanceId},"emerald",idx,cat)
assert(msgEmerald:find("Tap Clear") and msgEmerald:find("Waves"),msgEmerald)
assert(S.autoFillMessage(fillA,{},{},"gold",idx,cat):find("No plain dinos"))
assert(#S.withoutIds(fillA,{fillA[1].instanceId})==2 and S.withoutIds(fillA,{})[1]==fillA[1])
local chipTotal=0 for _,c in chips.sections[1].chips do chipTotal+=tonumber(string.match(c.label,"([%d%.]+)%%$")) end
assert(math.abs(chipTotal-100)<1e-9,"chip percentages sum to 100")
assert(not S.oddsChips({shiny=.1},cat).ok and not S.oddsChips(nil,cat).ok,"malformed odds give no chips")
assert(S.cardPattern(legacy,cat)=="Older dino" and S.cardPattern(all[1],cat)=="Waves")
assert(table.concat(S.cardTraits(trail,cat),",")=="Effects" and table.concat(S.cardTraits(ember,cat),",")=="Ember" and S.cardTraits(locked,cat)[1]=="Locked" and S.cardTraits(fav,cat)[1]=="Favourite")
for code,text in S.ReasonText do assert(#text<=24 and not string.find(text,"recipe") and not string.find(text,"species"),"plain short reason "..code) end

print("Fusion UI logic passed: ladder 6/3/2 stages (Gold any pattern), filters, sorts, eligibility reasons, plain-only auto-fill (fuzzed), exact 100% odds (fuzzed), loss summary, token reuse, committed reveal wheels (fuzzed), truthful Dino Details and the v2 menu words (tabs, auto-filter, goal sentence, odds chips)")
''')


UI_MODULES = {
    'Config': 'src/shared/Config.luau',
    'ProgressionConfig': 'src/shared/ProgressionConfig.luau',
    'RarityCurve': 'src/shared/RarityCurve.luau',
    'ColourBonus': 'src/shared/ColourBonus.luau',
    'EggGenetics': 'src/shared/EggGenetics.luau',
    'ModalCloseRules': 'src/shared/ModalCloseRules.luau',
    'ChipStyle': 'src/shared/ChipStyle.luau',  # BD-1077: fusion tags use the shared chunky tag
    'FusionSelection': 'src/shared/FusionSelection.luau',
    'FusionWidgets': 'src/client/FusionWidgets.luau',
    'DinoDetails': 'src/client/DinoDetails.luau',
    'FusionMenu': 'src/client/FusionMenu.luau',
}


def ui_script():
    """Real client modules + mock Roblox runtime + fake FusionAction server."""
    parts = []
    for name, path in UI_MODULES.items():
        source = (ROOT / path).read_text(encoding='utf-8')
        parts.append(name + '=function(script, require)\n' + source + '\nend,\n')
    table = '{\n' + ''.join(parts) + '}'
    harness = (ROOT / 'tools/fusion_ui_smoke.luau').read_text(encoding='utf-8')
    assert harness.count('MODULE_SOURCES') == 2
    return harness.replace('local sources = MODULE_SOURCES', 'local sources = ' + table)


def run(runner, source, name):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)


def check_recipes():
    server = (ROOT / 'src/server/IdentityFusion.luau').read_text(encoding='utf-8')
    client = (ROOT / 'src/shared/FusionSelection.luau').read_text(encoding='utf-8')
    for stage, count in (('gold', 6), ('emerald', 3), ('diamond', 2)):
        assert re.search(r'%s = \{targetStage = "%s", sourceStage = "\w+", donorCount = %d,' % (stage, stage, count), server), stage
        assert re.search(r'\{id = "%s", name = "\w+", source = "\w+", donorCount = %d(?:, anyPattern = true)?, approved = true\}' % (stage, count), client), stage
    service = (ROOT / 'src/server/FusionService.luau').read_text(encoding='utf-8')
    assert 'FusionService.MaxDonorIds = 6' in service
    copy = (ROOT / 'src/shared/OddsCopy.luau').read_text(encoding='utf-8')
    smoke = (ROOT / 'tools/fusion_ui_smoke.luau').read_text(encoding='utf-8')
    for name in ('fusionCalm', 'fusionDetails'):  # BD-347: the smoke stub must carry the exact shipped wording
        text = re.search(r'Copy\.%s = "([^"]+)"' % name, copy).group(1)
        assert '%s = "%s"' % (name, text) in smoke, name
    menu = (ROOT / 'src/client/FusionMenu.luau').read_text(encoding='utf-8')
    reel = menu[menu.index('local function reel('):menu.index('local function reel(') + 3500]
    assert '"PointerTop"' in reel and '"PointerBottom"' in reel and 'Sel.Reel.notchHeight' in reel, 'BD-1003: reel pointer is two edge notches'
    assert 'UDim2.new(0, 6, 1, 8)' not in menu, 'BD-1003: no full-height pointer line through the reel labels'
    print('Recipe parity passed: IdentityFusion, FusionSelection and FusionService agree on 6/3/2')


if __name__ == '__main__':
    check_recipes()
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    run(args.runner, script(), 'fusion_ui.luau')
    run(args.runner, ui_script(), 'fusion_ui_smoke.luau')
