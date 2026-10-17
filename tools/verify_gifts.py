"""BD-451 gifting core (docs/134, docs/115 GF1b..GF17): offline verifier in pinned Luau.

Runs the REAL src/shared/GiftRules.luau, src/server/GiftService.luau and src/server/ProfileRepository.luau (applyGifts) against two mocked
DataStores (the profile store of tools/verify_rewards.py and a Gifts store), plus the frozen Build 020 reader of tools/verify_rollback.py.
Covers: catalogue (skins and crystals only) and preset messages; recipient setting Everyone/Friends/Nobody (missing record = Everyone), mute
and Roblox block at purchase AND claim, one identical refusal; inbox cap 25 and 3 per sender, rate limits and durable daily counters;
exactly-once claim across reconnect, duplicate delivery and a second server; revoke before and after claim; corrupt inbox entries;
the race-duplicate skin; crystal cap; audit by UserId only (no names or text anywhere); flag-off identity (no DataStore request, no profile
transaction, no remote, no popup); migration (an older profile without the fields is untouched until a gift is claimed); rollback rule RB1
(Build 020 keeps loading profiles that never received a gift, and keeps the fields of ones that did).
Static: the three flags exist and are false in source and pinned off in the default AND playtest release profiles; no Robux API in the gift
modules; the pure module stays pure.

  python tools/verify_gifts.py --runner C:/path/to/luau.exe
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
import verify_rewards  # noqa: E402  (reuses the mocked DataStore prefix)

FLAGS = ('GiftingEnabled', 'AdminGiftsEnabled', 'GiftClaimEnabled')
FIXTURE = 'tools/fixtures/build020/'


sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402


def module(path: str) -> str:
    return profile_sources.module(path)  # docs/150: ProfileRepository plus the parts it installs


def gift_rules_module() -> str:
    """GiftRules requires the one skin catalogue (BD-456): bind the real SkinCatalog for that require inside the inlined module."""
    catalog = module('src/shared/SkinCatalog.luau')
    rules = (ROOT / 'src/shared/GiftRules.luau').read_text(encoding='utf-8')
    parts = ['(function()', 'local SkinCatalogModule=' + catalog, 'local script={Parent={SkinCatalog="SkinCatalog"}}',
            'local require=function(id) assert(id=="SkinCatalog") return SkinCatalogModule end', rules, 'end)()']
    return chr(10).join(parts)


def strip_comments(text: str) -> str:
    return re.sub(r'--.*$', '', text, flags=re.M)


def static_errors() -> list[str]:
    errors: list[str] = []
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    entries = release_profiles.config_entries(config)
    for flag in FLAGS:
        found = entries.get(flag)
        if not found or len(found) != 1 or found[-1][1] is not False:
            errors.append(f'Config.{flag} must exist exactly once and be false in source')
    for profile in ('default', 'playtest'):
        rules = release_profiles.rules_for(profile)
        for flag in FLAGS:
            mine = [r for r in rules if r.key == flag]
            if not mine or any(r.mode != 'require' or r.value is not False or r.missing != 'error' for r in mine):
                errors.append(f'release profile {profile!r} must pin {flag} to false (mode require, missing = error)')
        # The generated place must carry the pinned values: verify_source on the committed Config is the same check verify_release runs.
        report = release_profiles.verify_source(config, profile)
        errors.extend(f'[{profile}] {e}' for e in report.errors if any(flag in e for flag in FLAGS))
    # A flag flipped on in a copy of the source must be caught by both profiles (the enforcement itself works).
    for flag in FLAGS:
        flipped = re.sub(rf'^(    {flag} = )false', r'\1true', config, flags=re.M)
        for profile in ('default', 'playtest'):
            if not any(flag in e for e in release_profiles.verify_source(flipped, profile).errors):
                errors.append(f'{flag}=true in Config is NOT rejected by profile {profile!r}')
    for path in ('src/shared/GiftRules.luau', 'src/server/GiftService.luau', 'src/client/GiftPopup.client.luau'):
        text = strip_comments((ROOT / path).read_text(encoding='utf-8'))
        for word in ('MarketplaceService', 'PromptProductPurchase', 'PromptGamePassPurchase', 'DeveloperProducts', 'ProcessReceipt', 'TextService', 'FilterStringAsync'):
            if word in text:
                errors.append(f'{path} mentions {word}: BD-451 has no Robux and no free text (BD-453 adds the receipt branch)')
    text = strip_comments((ROOT / 'src/shared/GiftRules.luau').read_text(encoding='utf-8'))
    for word in ('Instance.new', 'game:GetService', 'GetService(', 'os.time', 'os.clock', 'os.date', 'DataStore', 'RemoteEvent', 'RemoteFunction', 'task.'):
        if word in text:
            errors.append(f'src/shared/GiftRules.luau must stay pure, found {word}')
    service = strip_comments((ROOT / 'src/server/GiftService.luau').read_text(encoding='utf-8'))
    # Every public entry point answers "disabled" before it touches a store, a profile or PrivateState.
    for name in ('setFrom', 'mute', 'reportBlocked', 'getPref', 'preflight', 'send', 'allowLookup', 'revoke', 'auditFor', 'claim', 'handle'):
        match = re.search(rf'function GiftService\.{name}\(.*?\n(.*?)\nend\n', service, flags=re.S)
        body = match.group(1) if match else ''
        first = [line for line in body.splitlines() if line.strip()][:3]
        if not match or not any(('claimOn()' in line or 'sendOn(' in line) for line in first):
            errors.append(f'GiftService.{name} must test the flag in its first lines (flag-off identity)')
    start = re.search(r'function GiftService\.start\(.*?\n(.*?)\nend\n', service, flags=re.S)
    if not start or 'if not claimOn() then return nil end' not in start.group(1).split('\n')[0] + '\n' + start.group(1).split('\n')[1]:
        errors.append('GiftService.start must return nil on its first line while the flag is off')
    repo = profile_sources.repository_text()
    match = re.search(r'function ProfileRepository\.applyGifts\(.*?\n(.*?)\n', repo)
    if not match or 'Config.GiftClaimEnabled ~= true' not in match.group(1):
        errors.append('ProfileRepository.applyGifts must test Config.GiftClaimEnabled on its first line')
    admin = strip_comments((ROOT / 'src/server/AdminService.luau').read_text(encoding='utf-8'))
    if 'GiftService' in admin:
        errors.append('AdminService stays runtime-only; the gift path lives in GiftService (docs/134 s5)')
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    if boot.count('GiftService') != 1 or 'GiftService).start(ProfileRepository)' not in boot:
        errors.append('Bootstrap must start GiftService exactly once, with the repository')
    private = (ROOT / 'src/shared/PrivateStateCore.luau').read_text(encoding='utf-8')
    if '"GiftNoticeJson"' not in private:
        errors.append('GiftNoticeJson must be a PRIVATE state name (the popup payload is owner-only)')
    for path in ('src/server/GiftService.luau', 'src/client/GiftPopup.client.luau'):
        if re.search(r'SetAttribute\(\s*"GiftNotice', (ROOT / path).read_text(encoding='utf-8')):
            errors.append(f'{path} must not publish the gift notice as a Player attribute')
    errors.extend(admin_page_errors())
    return errors


def admin_page_errors() -> list[str]:
    """BD-452: the admin Gift page. Static rules that keep the first-line admin check, the flag-off identity and the UI rules honest."""
    errors: list[str] = []
    server = strip_comments((ROOT / 'src/server/AdminGifts.luau').read_text(encoding='utf-8'))
    handle = re.search(r'function AdminGifts\.handle\(.*?\n(.*?)\nend\n', server, flags=re.S)
    lines = [line for line in (handle.group(1).splitlines() if handle else []) if line.strip()]
    if not lines or 'isAdmin' not in lines[0] or 'not_admin' not in lines[0]:
        errors.append('AdminGifts.handle must refuse non-admins on its FIRST line (the AdminRules.isAdmin result), before the flag, the shape or any store access')
    elif not any('giftsOn()' in line for line in lines[1:3]):
        errors.append('AdminGifts.handle must test the flags right after the admin check')
    start = re.search(r'function AdminGifts\.start\(.*?\n(.*?)\nend\n', server, flags=re.S)
    start_lines = [line for line in (start.group(1).splitlines() if start else []) if line.strip()]
    if not start_lines or 'if not giftsOn() then return nil end' not in start_lines[0]:
        errors.append('AdminGifts.start must return nil on its first line while a flag is off (no remote, no page)')
    for word in ('DataStore', 'ProfileRepository', 'PrivateState', 'UpdateAsync', 'GetAsync', 'SetAsync', 'MarketplaceService', 'PromptProductPurchase',
                 'TextService', 'FilterStringAsync', 'HttpService', 'ProcessReceipt'):
        if word in server:
            errors.append(f'AdminGifts must go through GiftService only, found {word}')
    for needle in ('GiftService.send(', 'GiftService.revoke(', 'GiftService.auditFor(', 'GiftService.allowLookup('):
        if needle not in server:
            errors.append(f'AdminGifts must call {needle[:-1]}')
    if 'source = "admin"' not in server or 'from = admin.UserId' not in server:
        errors.append("AdminGifts must send with source 'admin' and the caller's own UserId")
    if re.search(r'label', server.replace('label = GiftRules.TeamLine', '')):
        errors.append('AdminGifts must not take or build a label: the fixed GiftRules.TeamLine is the only one')
    service = strip_comments((ROOT / 'src/server/AdminService.luau').read_text(encoding='utf-8'))
    call = service.find('AdminGifts.start(')
    if service.count('AdminGifts.start(') != 1 or 'admins[player] == true' not in service[call:call + 200]:
        errors.append('AdminService must start AdminGifts exactly once with the server admin list (admins[player] == true)')
    elif not (service.index('if not Config.AdminPanelEnabled then return end') < call < service.index('remote.Name = "AdminAction"')):
        errors.append('AdminService must start AdminGifts after the AdminPanelEnabled check and before it creates AdminAction')
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    if 'AdminGifts' in boot:
        errors.append('Bootstrap does not start AdminGifts: AdminService does (flag-off identity of the admin panel)')
    rules = strip_comments((ROOT / 'src/shared/AdminGiftRules.luau').read_text(encoding='utf-8'))
    for word in ('Instance.new', 'game:GetService', 'GetService(', 'os.time', 'os.clock', 'os.date', 'DataStore', 'RemoteFunction', 'task.'):
        if word in rules:
            errors.append(f'src/shared/AdminGiftRules.luau must stay pure, found {word}')
    remote_name = re.search(r'RemoteName = "(\w+)"', rules)
    block = re.search(r'local messages: [^\n]*= \{(.*?)\n\}', rules, flags=re.S)
    known = set(re.findall(r'^\s+(\w+) = "', block.group(1), flags=re.M)) if block else set()
    for code in sorted(set(re.findall(r'fail\("(\w+)"\)', server))):
        if code not in known:
            errors.append(f'AdminGiftRules.Messages has no copy for the code {code!r} that AdminGifts returns')
    for code in ('rate_limited', 'cant_receive', 'try_again', 'lookup_minute', 'lookup_day', 'lookup_server', 'store_corrupt', 'bad_sender', 'profile_not_loaded', 'unknown_gift'):
        if code not in known:
            errors.append(f'AdminGiftRules.Messages has no copy for the GiftService code {code!r}')
    panel = (ROOT / 'src/client/AdminPanel.client.luau').read_text(encoding='utf-8')
    page = strip_comments((ROOT / 'src/client/AdminGiftPage.luau').read_text(encoding='utf-8'))
    branch = 'if giftRemote and giftRemote:IsA("RemoteFunction") then'
    if not remote_name or f'FindFirstChild("{remote_name.group(1)}")' not in panel or branch not in panel:
        errors.append('AdminPanel must look for the Gift remote by the name AdminGiftRules.RemoteName')
    else:
        if panel.count('AdminGiftPage') != 1 or panel.index('AdminGiftPage') < panel.index(branch):
            errors.append('AdminPanel may load AdminGiftPage only inside the "remote exists" branch (flag-off: no page)')
        if panel.count('AdminTabs') != 1 or panel.index('AdminTabs') < panel.index(branch):
            errors.append('the Tools/Gift tab row may only exist inside the "remote exists" branch (flag-off: layout unchanged)')
    if 'GiftRules.TeamLine' not in page:
        errors.append('the Gift page must show the fixed GiftRules.TeamLine label')
    for word in ('MarketplaceService', 'rbxassetid', 'ImageId', 'ImageIds', 'PromptProductPurchase', 'HttpService', 'ProfileRepository'):
        if word in page:
            errors.append(f'AdminGiftPage is plain UITheme UI with no new art or Robux, found {word}')
    sizes = [int(n) for n in re.findall(r'TextSize\s*=\s*(\d+)', page)] + [int(n) for n in re.findall(r'\blabel\(\w+, [^,\n]+, (\d+), \d+\)', page)]
    if not sizes or min(sizes) < 14:
        errors.append(f'AdminGiftPage text must be at least 14 px, found {min(sizes) if sizes else "none"}')
    heights = [int(n) for n in re.findall(r'\b(?:grid|row)\((\d+)\)', page)]
    heights += [int(n) for n in re.findall(r'(?:button|box)\([^\n]*UDim2\.new\([^)\n]*, 0, (\d+)\)\)', page)]
    if not heights or min(heights) < 44:
        errors.append(f'AdminGiftPage buttons and fields must be at least 44 px high, found {min(heights) if heights else "none"}')
    if len(re.findall(r'\bbox\(', page)) != 6:  # the helper + username, amount, gift id, player id, history player id
        errors.append('AdminGiftPage may have only the username, amount, gift id and player id fields: no free-text message box (presets only)')
    if 'msg = selectedMsg' not in page or 'selectedMsg = preset.id' not in page:
        errors.append('AdminGiftPage must send a preset id, never typed text, as the message')
    return errors


PURE = r'''
------------------------------------------------------------------ (A) GiftRules: catalogue, presets, settings, caps, rates, audit
local GiftRules=@@GIFT_RULES@@
local L=GiftRules.Limits
local checks=0
local function check(cond,msg) checks+=1 if not cond then error("FAIL: "..tostring(msg),2) end end
do
 -- catalogue: skins and crystals only
 local seen={}
 local POWER={"luck","power","boost","random","mystery","chance","rarity","rare","egg","dino","species","stronger","faster","bigger","fusion","odds","win","speed","nest","potion"}
 check(#GiftRules.Catalogue>=5,"catalogue exists")
 for _,e in GiftRules.Catalogue do
  check(not seen[e.id] and string.match(e.id,"^[%l%d_]+$"),"unique plain id "..e.id) seen[e.id]=true
  check(GiftRules.AllowedKinds[e.kind]==true and GiftRules.ForbiddenKinds[e.kind]==nil,"kind is skin or crystals: "..e.id)
  check(#e.label>=3 and #e.label<=24,"short label "..e.id)
  local lower=string.lower(e.label)
  for _,word in POWER do check(not string.find(lower,word,1,true),"no power or random word in "..e.id..": "..word) end
  if e.kind=="skin" then check(({Plush=1,Clay=1,Bricks=1,Balloon=1})[e.skin]==1 and e.crystals==nil,"skin ids are the docs/137 styles: "..e.id)
  else check(e.skin==nil and (e.id==GiftRules.CustomCrystalsId or (e.crystals and e.crystals>=1 and e.crystals<=5000)),"crystal entry "..e.id) end
  check(GiftRules.ById[e.id]==e,"ById "..e.id)
  local adminOk=GiftRules.itemAllowed(e.id,"admin") check(adminOk,"admin may send "..e.id)
  local robuxOk=GiftRules.itemAllowed(e.id,"robux")
  check(robuxOk==(e.launch==true and e.adminOnly~=true),"robux launch rule for "..e.id)
 end
 check(select(2,GiftRules.itemAllowed("crystals_100","robux"))=="not_giftable","crystal packs wait for the packs playtest (GF2)")
 check(select(2,GiftRules.itemAllowed("crystals_custom","robux"))=="not_giftable","the custom admin grant is never a Robux gift")
 for _,bad in {"egg","egg_common","dino","compy","raptor","species_raptor","rarity_boost","luck_potion","nest","fusion_token","Plush","skin_unknown","skin_plush ","",5,true,{},false} do
  check(not (GiftRules.itemAllowed(bad,"robux")) and not (GiftRules.itemAllowed(bad,"admin")),"never giftable: "..tostring(bad))
 end
 check(not (GiftRules.itemAllowed("skin_plush","nobody")) and not (GiftRules.itemAllowed("skin_plush",nil)),"unknown source")
 check(GiftRules.crystalAmount(GiftRules.ById.crystals_500,nil)==500 and GiftRules.crystalAmount(GiftRules.ById.crystals_custom,40)==40
  and GiftRules.crystalAmount(GiftRules.ById.crystals_custom,0)==nil and GiftRules.crystalAmount(GiftRules.ById.crystals_custom,L.AdminMaxCrystals+1)==nil
  and GiftRules.crystalAmount(GiftRules.ById.crystals_custom,1.5)==nil and GiftRules.crystalAmount(GiftRules.ById.skin_plush,5)==nil,"crystal amounts")
 check(GiftRules.clampAdminCrystals(1e9)==L.AdminMaxCrystals and GiftRules.clampAdminCrystals(-5)==1 and GiftRules.clampAdminCrystals(0/0)==nil and GiftRules.clampAdminCrystals("9")==nil,"admin amount clamp")
 -- presets: ids only, never free text
 check(#GiftRules.Presets>=4 and #GiftRules.Presets<=8,"about six presets")
 for _,p in GiftRules.Presets do
  check(string.match(p.id,"^[%l_]+$") and #p.text>=3 and #p.text<=24 and GiftRules.validMessage(p.id) and GiftRules.presetText(p.id)==p.text,"preset "..p.id)
 end
 check(GiftRules.validMessage(nil),"no message is fine")
 for _,bad in {"Have fun!","hello there","","have_fun ","HAVE_FUN",5,true,{},{id="have_fun"},"<script>"} do check(not GiftRules.validMessage(bad),"free text or non-preset rejected: "..tostring(bad)) end
 check(GiftRules.presetText("hello there")==nil and GiftRules.presetText(5)==nil,"presetText only knows ids")
 -- ids
 check(GiftRules.idMatchesSource("R12345-abc","robux") and not GiftRules.idMatchesSource("A12345","robux") and GiftRules.idMatchesSource("Aabc-1","admin")
  and not GiftRules.idMatchesSource("Rabc","admin") and not GiftRules.idMatchesSource("R bad","robux") and not GiftRules.idMatchesSource("R"..string.rep("x",L.MaxIdLength),"robux")
  and not GiftRules.idMatchesSource(5,"robux") and not GiftRules.idMatchesSource("","robux"),"gift ids come from the source")
 for _,id in {1,2^53,12345} do check(GiftRules.validUserId(id),"valid user id") end
 for _,id in {0,-1,1.5,2^53+2,0/0,math.huge,"1",true,{}} do check(not GiftRules.validUserId(id),"invalid user id "..tostring(id)) end
 -- newGift: stored fields are ids only
 local gift=GiftRules.newGift("robux",77,"skin_plush","have_fun",nil,1000,"Rpurchase-1")
 check(gift~=nil,"newGift") local keys={} for k in gift do table.insert(keys,k) end table.sort(keys)
 check(table.concat(keys,",")=="at,from,id,item,msg,source","a gift stores only {id, source, from, item, msg, at}: "..table.concat(keys,","))
 check(GiftRules.validGift(gift,gift.id) and GiftRules.validGift(gift),"valid gift")
 for _,case in {
  {"robux",0,"skin_plush",nil,nil,1,"Rx","bad_sender"},{"robux",5,"egg",nil,nil,1,"Rx","unknown_item"},{"robux",5,"crystals_100",nil,nil,1,"Rx","not_giftable"},
  {"robux",5,"skin_plush","free text here",nil,1,"Rx","bad_message"},{"robux",5,"skin_plush",nil,nil,1,"Ax","bad_id"},{"admin",5,"skin_plush",nil,nil,1,"Rx","bad_id"},
  {"robux",5,"skin_plush",nil,99,1,"Rx","bad_amount"},{"admin",5,"crystals_custom",nil,nil,1,"Ax","bad_amount"},{"admin",5,"crystals_custom",nil,0/0,1,"Ax","bad_amount"},{"admin",5,"crystals_custom",nil,"x",1,"Ax","bad_amount"},
  {"bank",5,"skin_plush",nil,nil,1,"Rx","bad_source"},{"robux",5,"skin_plush",nil,nil,-1,"Rx","bad_time"},
 } do
  local g,code=GiftRules.newGift(table.unpack(case,1,7))
  check(g==nil and code==case[8],"newGift refuses "..tostring(case[8])..": got "..tostring(code))
 end
 local custom=GiftRules.newGift("admin",5,"crystals_custom",nil,10^9,2,"Aabc") check(custom and custom.crystals==L.AdminMaxCrystals,"admin amount clamped when built")
 check(GiftRules.newGift("admin",5,"crystals_custom",nil,0,2,"Aabc").crystals==1 and GiftRules.newGift("admin",5,"crystals_custom",nil,-9,2,"Aabc").crystals==1,"an admin amount below 1 is clamped up to 1")
 -- validGift: every corrupt shape is rejected
 local function mutated(fn) local g=table.clone(gift) fn(g) return g end
 for label,bad in {
  string="text",number=7,empty={},noid=mutated(function(g) g.id=nil end),wrongid=mutated(function(g) g.id="Rother" end),badsource=mutated(function(g) g.source="bank" end),
  mixedsource=mutated(function(g) g.source="admin" end),nofrom=mutated(function(g) g.from=nil end),negfrom=mutated(function(g) g.from=-3 end),strfrom=mutated(function(g) g.from="5" end),
  unknownitem=mutated(function(g) g.item="skin_from_the_future" end),noitem=mutated(function(g) g.item=nil end),freetext=mutated(function(g) g.msg="hello there" end),
  skincrystals=mutated(function(g) g.crystals=500 end),noat=mutated(function(g) g.at=nil end),nanat=mutated(function(g) g.at=0/0 end),
  robuxcustom=mutated(function(g) g.item="crystals_custom" g.crystals=5 end),
 } do check(not GiftRules.validGift(bad,gift.id),"corrupt gift rejected: "..label) end
 check(not GiftRules.validGift(gift,"Rmismatch"),"inbox key must equal the gift id")
 local op=GiftRules.operationFor(gift) check(op.kind=="skin" and op.skin=="Plush" and op.id==gift.id and op.thankYou==L.ThankYouCrystals,"skin operation")
 local cop=GiftRules.operationFor(custom) check(cop.kind=="crystals" and cop.amount==L.AdminMaxCrystals,"crystal operation")
 check(GiftRules.skinOf("skin_clay")=="Clay" and GiftRules.skinOf("crystals_100")==nil and GiftRules.skinOf("nope")==nil and GiftRules.skinOf(5)==nil,"skinOf")
end
do
 -- recipient setting, mute, block: missing record = Everyone
 do local pref=GiftRules.normalizePref(nil) check(pref.from=="everyone" and next(pref.blocked)==nil,"a missing record (nil) is Everyone") end
 for _,raw in {"junk",5,true,{},{from="stranger"},{from=5},{from="everyone",blocked="x",muted=3},{blocked={"a",-1,1.5}}} do
  local pref=GiftRules.normalizePref(raw)
  check(pref.from=="everyone" and next(pref.blocked)==nil and next(pref.muted)==nil,"missing or unreadable pref = Everyone, no blocks: "..tostring(raw))
  check((GiftRules.recipientAllows(pref,9,false,"robux")),"a stranger may gift when there is no record")
 end
 local function pref(from,blocked,muted) return GiftRules.normalizePref({from=from,blocked=blocked or {},muted=muted or {}}) end
 local matrix={
  {pref("everyone"),9,false,"robux",true,"ok"},{pref("everyone"),9,true,"robux",true,"ok"},
  {pref("friends"),9,false,"robux",false,"friends_only"},{pref("friends"),9,true,"robux",true,"ok"},
  {pref("nobody"),9,true,"robux",false,"setting_off"},{pref("nobody"),9,false,"robux",false,"setting_off"},
  {pref("everyone",{9}),9,true,"robux",false,"blocked"},{pref("everyone",nil,{9}),9,true,"robux",false,"muted"},{pref("friends",nil,{9}),9,true,"robux",false,"muted"},
  {pref("nobody"),9,false,"admin",true,"ok"},{pref("friends"),9,false,"admin",true,"ok"},{pref("everyone",nil,{9}),9,false,"admin",true,"ok"},
  {pref("everyone",{9}),9,false,"admin",false,"blocked"},{pref("nobody",{9}),9,false,"admin",false,"blocked"},
  {pref("everyone",{8}),9,false,"robux",true,"ok"},
 }
 for i,row in matrix do
  local ok,code=GiftRules.recipientAllows(row[1],row[2],row[3],row[4])
  check(ok==row[5] and code==row[6],"recipientAllows row "..i..": "..tostring(ok).." "..code)
 end
 -- one refusal, byte-identical
 local publicCodes={}
 for _,code in {"blocked","setting_off","friends_only","muted","inbox_full","sender_cap"} do publicCodes[GiftRules.toPublic(code)]=true end
 check(publicCodes.cant_receive and next(publicCodes,"cant_receive")==nil and GiftRules.PublicRefusal=="cant_receive","every recipient-side refusal is ONE public code")
 check(GiftRules.toPublic("rate_limited")=="rate_limited" and GiftRules.toPublic("daily_limit")=="daily_limit" and GiftRules.toPublic("self")=="self","buyer-side codes pass through")
 check(GiftRules.refusalText("Sam")=="Sam can't get gifts right now.","the refusal sentence")
 -- pref encode / edit
 local p=pref("friends",{3,1,2},{5})
 check(GiftRules.setFrom(p,"nobody") and p.from=="nobody" and not GiftRules.setFrom(p,"anyone") and not GiftRules.setFrom(p,5) and p.from=="nobody","setFrom accepts only Everyone/Friends/Nobody")
 local enc=GiftRules.encodePref(p) check(enc.from=="nobody" and table.concat(enc.blocked,",")=="1,2,3" and table.concat(enc.muted,",")=="5","encoded as sorted arrays")
 for i=1,L.MutedCap do GiftRules.addMuted(p,1000+i) end
 check(not (GiftRules.addMuted(p,5000)) and select(2,GiftRules.addMuted(p,1001))=="already" and not (GiftRules.addMuted(p,-1)),"mute list is capped (50)")
 local many={} for i=1,L.BlockedCap+1 do many[i]=i end
 check(not (GiftRules.setBlocked(p,many)) and not (GiftRules.setBlocked(p,{1,"x"})) and not (GiftRules.setBlocked(p,"x")) and GiftRules.setBlocked(p,{4,5,5}) and GiftRules.count(p.blocked)==2,"blocked report is capped (200) and validated")
end
do
 -- inbox and caps
 local function g(id,from,source) return {id=id,source=source or "robux",from=from,item="skin_plush",at=1} end
 local inbox=GiftRules.normalizeInbox(nil) check(next(inbox.gifts)==nil and next(inbox.revoked)==nil,"missing inbox = empty")
 for _,bad in {"x",5,true,{gifts="x"},{gifts={},revoked=5}} do check(GiftRules.normalizeInbox(bad)==nil,"corrupt inbox record is nil: "..tostring(bad)) end
 local keep=GiftRules.normalizeInbox({gifts={},future={a=1}}) check(keep.future.a==1,"unknown top-level fields ride along")
 for i=1,L.InboxCap-1 do inbox.gifts["R"..i]=g("R"..i,100+i) end
 check((GiftRules.inboxAdmits(inbox,g("Rnew",500))),"24 pending: one more fits")
 inbox.gifts.Rlast=g("Rlast",900)
 local ok,code=GiftRules.inboxAdmits(inbox,g("Rnew",500)) check(not ok and code=="inbox_full","25 pending: full")
 ok,code=GiftRules.inboxAdmits(inbox,g("Aadmin",500,"admin")) check(not ok and code=="inbox_full","admin gifts obey the inbox cap too")
 ok,code=GiftRules.inboxAdmits(inbox,g("R1",101)) check(ok and code=="duplicate","the same gift id is a duplicate, not a refusal, even in a full inbox")
 inbox.revoked.Rgone=true ok,code=GiftRules.inboxAdmits(inbox,g("Rgone",5)) check(not ok and code=="revoked","a revoked id is never admitted again")
 local small=GiftRules.normalizeInbox(nil)
 for i=1,L.PerSenderCap do small.gifts["R"..i]=g("R"..i,42) end
 ok,code=GiftRules.inboxAdmits(small,g("R99",42)) check(not ok and code=="sender_cap","3 pending from one sender")
 check((GiftRules.inboxAdmits(small,g("R98",43))),"another sender still fits")
 check((GiftRules.inboxAdmits(small,g("Aadmin",42,"admin"))),"admin gifts are exempt from the per-sender cap")
 small.gifts.Rjunk="garbage" for i=1,L.InboxCap do small.gifts["Rx"..i]="garbage" end
 ok,code=GiftRules.inboxAdmits(small,g("R50",44)) check(not ok and code=="inbox_full","corrupt entries still count toward the cap")
end
do
 -- rate limits and durable daily counters
 local w={start=0,count=0}
 local t=100
 for i=1,L.PromptsPerMinute do check(GiftRules.windowAllow(w,t+i,L.PromptsPerMinute,60),"prompt "..i) end
 check(not GiftRules.windowAllow(w,t+10,L.PromptsPerMinute,60),"4th prompt in a minute refused")
 check(GiftRules.windowAllow(w,t+61+L.PromptsPerMinute,L.PromptsPerMinute,60),"a new minute opens")
 local now=20000*86400+3600
 local intent=GiftRules.normalizeIntent(nil,now) check(intent.dayCount==0 and intent.day==20000,"fresh intent")
 for i=1,L.PerRecipientPerDay do check((GiftRules.dailyAllows(intent,5)),"recipient "..i) GiftRules.bumpDaily(intent,5) end
 local ok,code=GiftRules.dailyAllows(intent,5) check(not ok and code=="recipient_limit","3 per recipient per day")
 for i=1,L.GiftsPerDay-L.PerRecipientPerDay do check((GiftRules.dailyAllows(intent,100+i)),"gift "..i) GiftRules.bumpDaily(intent,100+i) end
 ok,code=GiftRules.dailyAllows(intent,999) check(not ok and code=="daily_limit","10 gifts per day")
 local again=GiftRules.normalizeIntent(intent,now+10) check(again.dayCount==L.GiftsPerDay and again.perRecipient["5"]==3,"same day: counters survive")
 local nextDay=GiftRules.normalizeIntent(intent,now+86400) check(nextDay.dayCount==0 and next(nextDay.perRecipient)==nil,"next day: counters reset")
 for _,junk in {"x",{day=20000,dayCount="a",perRecipient={}},{day=20000,dayCount=1},{day=20000,dayCount=-1,perRecipient={}}} do
  check(GiftRules.normalizeIntent(junk,now).dayCount==0,"a corrupt intent reads as empty")
 end
 -- lookups: per player per minute and day, plus a server bucket; a refusal costs nothing
 local server={start=0,count=0}
 local player=GiftRules.newLookupState()
 for i=1,L.LookupsPerMinute do check((GiftRules.lookupAllows(player,server,1000+i)),"lookup "..i) end
 ok,code=GiftRules.lookupAllows(player,server,1020) check(not ok and code=="lookup_minute","10 lookups a minute")
 check(server.count==L.LookupsPerMinute,"a refused lookup does not touch the server bucket")
 for i=1,L.LookupsPerDay//L.LookupsPerMinute-1 do
  local base=2000+i*100
  for j=1,L.LookupsPerMinute do check((GiftRules.lookupAllows(player,server,base+j)),"daily lookup "..i.."/"..j) end
 end
 ok,code=GiftRules.lookupAllows(player,server,9000) check(not ok and code=="lookup_day","60 lookups a day")
 local busy={start=0,count=0}
 for i=1,L.ServerLookupsPerMinute do check((GiftRules.lookupAllows(GiftRules.newLookupState(),busy,5000+i)),"server lookup "..i) end
 ok,code=GiftRules.lookupAllows(GiftRules.newLookupState(),busy,5040) check(not ok and code=="lookup_server","30 lookups a minute server-wide")
 -- dates
 check(GiftRules.dateKey(0)==19700101 and GiftRules.dateKey(86400*365)==19710101 and GiftRules.dateKey(951782400)==20000229 and GiftRules.dateKey(1735689599)==20241231 and GiftRules.dateKey(1735689600)==20250101,"yyyymmdd")
 -- audit: UserIds and codes only
 local ev=GiftRules.auditEvent("claimed",1790000000,5,6,"skin_plush","Rabc-1","purchase-1","converted")
 check(ev and ev.ev=="claimed" and ev.from==5 and ev.to==6 and ev.item=="skin_plush" and ev.giftId=="Rabc-1" and ev.purchaseId=="purchase-1" and ev.code=="converted","audit event")
 for _,bad in {{"bought!",1,5,6},{"claimed","x",5,6},{"claimed",1,"Sam",6},{"claimed",1,5,6,"Sam's plush"},{"claimed",1,5,6,"skin_plush","has space"},{"claimed",1,5,6,"skin_plush","Rabc",nil,"Some Text"},{"claimed",1,5,6,"skin_plush","Rabc",nil,"UPPER"},{"claimed",-1,5,6},{"claimed",1,5,0}} do
  check(GiftRules.auditEvent(table.unpack(bad,1,8))==nil,"audit refuses names, text and bad fields")
 end
 local list={} for i=1,L.AuditUserCap+5 do list=GiftRules.appendCapped(list,{at=i},L.AuditUserCap) end
 check(#list==L.AuditUserCap and list[1].at==6 and list[#list].at==L.AuditUserCap+5,"audit lists keep the newest 50")
 check(GiftRules.noticeLine("robux","Sam")=="You got a gift from Sam!" and GiftRules.noticeLine("robux",nil)=="You got a gift from A Be Dino player!"
  and GiftRules.noticeLine("admin","Sam")=="A gift from the Be Dino team!" and #GiftRules.noticeLine("robux",string.rep("x",200))<=L.MaxNameLength+30,"notice text; admin never shows a name")
end
print("GiftRules passed: catalogue (skins and crystals only), presets, setting/mute/block matrix, one refusal, caps, rates, daily counters, audit")
'''

REPO = r'''
------------------------------------------------------------------ (B) ProfileRepository.applyGifts (real transactions, mocked profile store)
local function user(id,friends)
 local u={Parent=true,UserId=id,Name="P"..id,attrs={},friends=friends or {}}
 function u:SetAttribute(k,v) self.attrs[k]=v end
 function u:GetAttribute(k) return self.attrs[k] end
 function u:IsFriendsWith(other) return self.friends[other]==true end
 return u
end
local function key(u) return "u:"..tostring(u.UserId) end
local function wallet(u) local p=data[key(u)].progression return p and p.crystals or 0 end
local function skinOp(id,skin) return {id=id,kind="skin",skin=skin,thankYou=L.ThankYouCrystals} end
local function crystalOp(id,n) return {id=id,kind="crystals",amount=n} end
local MAXC=ProgressionConfig.MaxCrystals
do
 -- flag OFF: identity
 check(GameConfig.GiftClaimEnabled==false and GameConfig.GiftingEnabled==false and GameConfig.AdminGiftsEnabled==false,"the committed Config has all three flags off")
 local a=user(7001) assert(Repository.load(a))
 local snap,t0=copy(data[key(a)]),transforms
 for _,plan in {{apply={skinOp("Rx1","Plush")},revoke={}},{apply={},revoke={{id="Rx1"}}},"junk"} do
  local ok,status=Repository.applyGifts(a,plan)
  check(ok==false and status=="disabled","flag off: applyGifts answers disabled")
 end
 check(transforms==t0 and same(snap,data[key(a)]),"flag off: not one profile transform, byte-identical profile")
 Repository.release(a)
 check(data[key(a)].claimedGifts==nil and data[key(a)].ownedSkins==nil,"flag off: a load and a release add no gift fields")
 -- a profile that ALREADY has the fields (a flag-on session, a newer build) is left alone while off
 data[key(a)].claimedGifts={Rold=123} data[key(a)].ownedSkins={Plush=true}
 local keep=copy({data[key(a)].claimedGifts,data[key(a)].ownedSkins})
 assert(Repository.load(a)) Repository.applyGifts(a,{apply={skinOp("Rnew","Clay")},revoke={}}) Repository.renew(a) Repository.release(a)
 check(same(keep,{data[key(a)].claimedGifts,data[key(a)].ownedSkins}),"flag off: existing gift fields are not normalised, migrated or rewritten")
end
GameConfig.GiftClaimEnabled=true
do
 local b=user(7002) assert(Repository.load(b))
 check(data[key(b)].claimedGifts==nil and data[key(b)].ownedSkins==nil,"flag on: load alone never creates the fields (lazy, additive)")
 local rev0,c0=data[key(b)].revision,wallet(b)
 local ok,r=Repository.applyGifts(b,{apply={skinOp("RA1","Plush")},revoke={}})
 check(ok and r.RA1=="applied","skin applied")
 local s=data[key(b)]
 check(type(s.claimedGifts.RA1)=="number" and s.ownedSkins.Plush==true and s.revision==rev0+1 and wallet(b)==c0,"claimedGifts token + ownedSkins written, one revision")
 local snap=copy(data[key(b)])
 ok,r=Repository.applyGifts(b,{apply={skinOp("RA1","Plush")},revoke={}})
 check(ok and r.RA1=="already" and same(snap,data[key(b)]),"the same gift again is 'already' and writes nothing")
 ok,r=Repository.applyGifts(b,{apply={crystalOp("RA2",100)},revoke={}})
 check(ok and r.RA2=="applied" and wallet(b)==c0+100 and data[key(b)].metrics.robux==0,"crystals applied; a gift never touches metrics.robux")
 ok,r=Repository.applyGifts(b,{apply={skinOp("RA3","Plush")},revoke={}})
 check(ok and r.RA3=="converted" and wallet(b)==c0+100+L.ThankYouCrystals and data[key(b)].claimedGifts.RA3~=nil,"race duplicate: owned skin becomes thank-you crystals, once")
 ok,r=Repository.applyGifts(b,{apply={skinOp("RA3","Plush")},revoke={}})
 check(r.RA3=="already" and wallet(b)==c0+100+L.ThankYouCrystals,"conversion is not repeated")
 -- revoke: claimed skin, idempotent, pending, crystals
 ok,r=Repository.applyGifts(b,{apply={},revoke={{id="RA1",skin="Plush"}}})
 check(ok and r.RA1=="revoked" and data[key(b)].claimedGifts.RA1=="revoked" and data[key(b)].ownedSkins.Plush==nil,"revoke after claim removes the skin and tombstones the id")
 ok,r=Repository.applyGifts(b,{apply={},revoke={{id="RA1",skin="Plush"}}})
 check(r.RA1=="already_revoked","revoke is idempotent")
 ok,r=Repository.applyGifts(b,{apply={skinOp("RA1","Plush")},revoke={}})
 check(r.RA1=="already" and data[key(b)].ownedSkins.Plush==nil,"a revoked id is never granted again")
 ok,r=Repository.applyGifts(b,{apply={},revoke={{id="RB9",skin="Clay"}}})
 check(r.RB9=="revoked_pending" and data[key(b)].claimedGifts.RB9=="revoked","revoke before claim tombstones the id")
 ok,r=Repository.applyGifts(b,{apply={skinOp("RB9","Clay")},revoke={}})
 check(r.RB9=="already" and data[key(b)].ownedSkins.Clay==nil,"a revoked pending gift never lands")
 local spent=wallet(b)
 ok,r=Repository.applyGifts(b,{apply={},revoke={{id="RA2"}}})
 check(r.RA2=="revoked" and wallet(b)==spent,"crystals already granted are not clawed back")
 -- plan hygiene
 for _,bad in {"x",{},{apply={}},{apply={},revoke="x"},5} do local bok,bs=Repository.applyGifts(b,bad) check(bok==false and bs=="bad_plan","bad plan "..tostring(bad)) end
 snap=copy(data[key(b)])
 ok,r=Repository.applyGifts(b,{apply={{id=5,kind="skin",skin="Plush"},{id="Rz",kind="skin"},{id="Rz2",kind="mystery"}},revoke={}})
 check(ok and next(r)==nil and same(snap,data[key(b)]),"malformed operations are skipped, nothing is written")
 -- claimedGifts cap fails closed
 local c=user(7003) assert(Repository.load(c))
 ok,r=Repository.applyGifts(c,{claimedCap=2,apply={skinOp("RC1","Plush"),skinOp("RC2","Clay"),skinOp("RC3","Bricks")},revoke={}})
 check(r.RC1=="applied" and r.RC2=="applied" and r.RC3=="held_cap" and data[key(c)].ownedSkins.Bricks==nil and data[key(c)].claimedGifts.RC3==nil,"claimedGifts cap fails closed: never grant what cannot be recorded")
 -- crystal wallet cap: held, not lost
 local d=user(7004) assert(Repository.load(d)) Repository.release(d)
 data[key(d)].progression.crystals=MAXC-10
 assert(Repository.load(d))
 ok,r=Repository.applyGifts(d,{apply={crystalOp("RD1",100),skinOp("RD2","Plush")},revoke={}})
 check(r.RD1=="held_crystals" and r.RD2=="applied" and wallet(d)==MAXC-10 and data[key(d)].claimedGifts.RD1==nil,"crystals over the wallet cap are held, nothing is lost")
 ok,r=Repository.applyGifts(d,{apply={skinOp("RD3","Plush")},revoke={}})
 check(r.RD3=="held_crystals","a race-duplicate conversion over the cap is held too")
 -- lease lost, outage, lost acknowledgement, junk fields
 local e=user(7005) assert(Repository.load(e))
 data[key(e)].session.leaseId="another-server"
 local before=copy(data[key(e)])
 ok,r=Repository.applyGifts(e,{apply={skinOp("RE1","Plush")},revoke={}})
 check(ok==false and r=="lease_lost" and same(before,data[key(e)]),"another server holds the lease: nothing applied, nothing written")
 local f=user(7006) assert(Repository.load(f))
 failMode="all"
 ok,r=Repository.applyGifts(f,{apply={skinOp("RF1","Plush")},revoke={}})
 failMode=nil
 check(ok==false and r=="save_failed" and f.attrs.ProfileState=="SaveFailed" and data[key(f)].claimedGifts==nil,"outage: save_failed, profile untouched")
 f.attrs.ProfileState="Loaded"
 failMode="ack_lost"
 ok,r=Repository.applyGifts(f,{apply={skinOp("RF1","Plush")},revoke={}})
 check(ok and (r.RF1=="applied" or r.RF1=="already") and data[key(f)].ownedSkins.Plush==true,"lost acknowledgement: committed once, the retry sees it")
 local cnt=0 for _ in data[key(f)].claimedGifts do cnt+=1 end check(cnt==1,"lost acknowledgement grants one token")
 local g=user(7007) assert(Repository.load(g)) data[key(g)].claimedGifts="junk"
 before=copy(data[key(g)])
 ok,r=Repository.applyGifts(g,{apply={skinOp("RG1","Plush")},revoke={}})
 check(ok==false and r=="invalid_gift_state" and same(before,data[key(g)]),"junk in claimedGifts: refused, never overwritten")
 Repository.release(g)
 local g2=user(7007) check(Repository.load(g2) and g2.attrs.ProfileState=="Loaded","a junk gift field is not a validity condition: the player still loads")
 data[key(g2)].ownedSkins=5
 ok,r=Repository.applyGifts(g2,{apply={skinOp("RG1","Plush")},revoke={}}) check(ok==false and r=="invalid_gift_state","junk ownedSkins refused too")
 for _,u in {b,c,d,e,f,g2} do Repository.release(u) end
end
print("Repository passed: flag-off identity, lazy additive fields, exactly-once token, race duplicate, revoke, caps, lease, outage, lost ack, junk fields")
'''

SERVICE = r'''
------------------------------------------------------------------ (C) GiftService on a mocked Gifts store + the real repository
local NOW=20000*86400+3600
local giftsData={}
local g={requests=0,block={},outage=false}
local giftsStore={}
function giftsStore:GetAsync(k)
 g.requests+=1
 if g.outage then error("injected outage") end
 return copy(giftsData[k])
end
function giftsStore:UpdateAsync(k,fn)
 g.requests+=1
 if g.outage or g.block[k] then error("injected failure") end
 local probe=copy(giftsData[k]) fn(probe) -- Roblox may run a transform twice; only the final result commits
 local updated=fn(copy(giftsData[k]))
 if updated==nil then return nil end
 giftsData[k]=copy(updated)
 return copy(updated)
end
local guidCounter=0
local function makeService(cfg)
 local world={dsNames={},instances=0,sets=0,printed={},players={}}
 local rs={children={},Shared={Config="Config",GiftRules="GiftRules"}}
 function rs:FindFirstChild(n) return self.children[n] end
 local Instance={new=function(class)
  world.instances+=1
  local o={ClassName=class,Name=class,children={}}
  return setmetatable(o,{__newindex=function(t,k,v) rawset(t,k,v) if k=="Parent" and v then v.children[rawget(t,"Name")]=t end end})
 end}
 local PS={set=function(p,k,v) world.sets+=1 p.attrs[k]=v end,forget=function() end}
 local services={
  Players={GetPlayers=function() return world.players end,PlayerAdded={Connect=function() end},PlayerRemoving={Connect=function() end}},
  DataStoreService={GetDataStore=function(_,name) table.insert(world.dsNames,name) return giftsStore end},
  HttpService={GenerateGUID=function() guidCounter+=1 return "guid"..guidCounter end,JSONEncode=function(_,v) return copy(v) end,JSONDecode=function(_,v) return copy(v) end},
  RunService={IsStudio=function() return false end},ReplicatedStorage=rs,
 }
 local game={GameId=1,GetService=function(_,n) return services[n] or error("service "..n.." is not modelled") end}
 local script={Parent={PrivateState="PrivateState"}}
 local require=function(id)
  if id=="Config" then return cfg elseif id=="GiftRules" then return GiftRules elseif id=="PrivateState" then return PS end
  error("unexpected module "..tostring(id))
 end
 local task={wait=function() end,spawn=function() end}
 local warn=function() end
 local print=function(s) table.insert(world.printed,s) end
 local Service=@@GIFT_SERVICE@@
 Service.setClock(function() return NOW end)
 Service.setNameResolver(function() return "Samantha Display" end)
 return Service,world,rs
end
local function server(cfg,repo)
 local S,W,rs=makeService(cfg or GameConfig)
 S.start(repo or Repository)
 return S,W,rs
end
local function inbox(id) return giftsData["inbox_"..id] end
local function pending(id) local n=0 for _ in (inbox(id) and inbox(id).gifts or {}) do n+=1 end return n end
local function noticeOf(u) return u.attrs.GiftNoticeJson end

------------------------------------------------------------------ flag-off identity (even with the sender flags on)
do
 local off=table.clone(GameConfig) off.GiftClaimEnabled=false off.GiftingEnabled=true off.AdminGiftsEnabled=true
 GameConfig.GiftClaimEnabled=false
 local S,W,rs=makeService(off)
 local u=user(7100) assert(Repository.load(u))
 local t0,r0,snap=transforms,g.requests,copy(data[key(u)])
 check(S.start(Repository)==nil and W.instances==0 and next(rs.children)==nil,"flag off: start() returns at once and creates no remote")
 local calls={
  function() return S.send({source="admin",from=1,to=2,item="skin_plush"}) end,
  function() return S.send({source="robux",giftId="Rx",from=1,to=2,item="skin_plush"}) end,
  function() return S.preflight({source="robux",from=1,to=2,item="skin_plush"}) end,
  function() return S.revoke(1,2,"Rx") end, function() return S.auditFor(2) end, function() return S.claim(u) end,
  function() return S.handle(u,{action="ack"}) end, function() return S.setFrom(2,"nobody") end, function() return S.mute(2,3) end,
  function() return S.reportBlocked(2,{3}) end, function() return S.getPref(2) end, function() return S.allowLookup(2) end,
 }
 for i,call in calls do
  local ok,why=call()
  if type(ok)=="table" then ok,why=ok.ok,ok.reason end -- handle() answers a table
  check((ok==false or ok==nil) and (why=="disabled" or why==nil),"flag off: call "..i.." answers disabled, got "..tostring(ok).."/"..tostring(why))
 end
 check(#W.dsNames==0 and g.requests==r0,"flag off: no GetDataStore, no Gifts request")
 check(transforms==t0 and same(snap,data[key(u)]) and W.sets==0 and u.attrs.GiftNoticeJson==nil and W.instances==0,"flag off: no profile transform, no popup state, no instance")
 Repository.release(u)
 -- GiftClaimEnabled on but a sender flag off: that sender is refused, nothing else changes
 GameConfig.GiftClaimEnabled=true
 local only=table.clone(GameConfig) only.GiftingEnabled=false only.AdminGiftsEnabled=false
 local S2,W2=server(only)
 check(S2.send({source="admin",from=1,to=2,item="skin_plush"})==false and select(2,S2.send({source="admin",from=1,to=2,item="skin_plush"}))=="disabled","AdminGiftsEnabled off: admin send disabled")
 check(select(2,S2.send({source="robux",giftId="Rx",from=1,to=2,item="skin_plush"}))=="disabled" and select(2,S2.preflight({source="robux",from=1,to=2,item="skin_plush"}))=="disabled","GiftingEnabled off: robux send disabled")
 local panelOff=table.clone(GameConfig) panelOff.AdminGiftsEnabled=true panelOff.AdminPanelEnabled=false
 local S3=server(panelOff)
 check(select(2,S3.send({source="admin",from=1,to=2,item="skin_plush"}))=="disabled","admin gifts also need AdminPanelEnabled")
 check(W2.dsNames[1]==nil and g.requests==r0,"a refused send makes no store request")
end
print("GiftService flag-off identity passed: no DataStore request, no profile transform, no remote, no popup state")

GameConfig.GiftClaimEnabled=true GameConfig.AdminGiftsEnabled=true GameConfig.GiftingEnabled=false
------------------------------------------------------------------ admin gift to a user who never played: inbox, no expiry, exactly one grant at first join
local ADMIN=100
do
 local S,W=server()
 local R1=7200
 local ok,code,id=S.send({source="admin",from=ADMIN,to=R1,item="skin_plush",msg="have_fun"})
 check(ok and code=="queued" and id and string.sub(id,1,1)=="A","admin gift queued: "..tostring(code))
 check(data["u:"..R1]==nil,"a never-played recipient has NO profile; nothing is written to it from this server")
 check(W.dsNames[1]=="BeDino_PrivateTest_v1_Gifts" and #W.dsNames==1,"the Gifts store name derives from the profile store name")
 local entry=inbox(R1).gifts[id]
 local keys={} for k in entry do table.insert(keys,k) end table.sort(keys)
 check(table.concat(keys,",")=="at,from,id,item,msg,source" and entry.at==NOW and entry.from==ADMIN and entry.msg=="have_fun","stored gift is ids only")
 -- a gift dated long ago still delivers: NO expiry (GF10)
 local old=GiftRules.newGift("admin",ADMIN,"crystals_custom",nil,40,1,"Aold1")
 giftsData["inbox_"..R1].gifts.Aold1=old
 local u=user(R1) assert(Repository.load(u))
 local c0=wallet(u)
 local okc,status,summary=S.claim(u)
 check(okc and status=="claimed" and summary.applied==2 and summary.held==0,"first join: both gifts granted: "..tostring(status))
 check(data[key(u)].ownedSkins.Plush==true and wallet(u)==c0+40 and data[key(u)].claimedGifts.Aold1~=nil and data[key(u)].claimedGifts[id]~=nil,"skin + crystals, tokens recorded")
 check(pending(R1)==0,"applied gifts are removed from the inbox")
 check(select(2,S.claim(u))=="empty" and wallet(u)==c0+40,"a second claim finds nothing and grants nothing")
 local n=noticeOf(u)
 check(n and n.id=="Aold1" and n.line=="A gift from the Be Dino team!" and n.more==1 and n.canMute==false and n.name=="" and n.kind=="crystals","admin popup: team label, no name, cannot be muted, crystals icon kind")
 local r=S.handle(u,{action="ack"}) check(r.ok and noticeOf(u).id==id and noticeOf(u).message=="Have fun!" and noticeOf(u).item=="Plushy skin","ack shows the next notice")
 S.handle(u,{action="ack"}) check(noticeOf(u)=="","nothing left to show")
 Repository.release(u)
end
print("GiftService admin->never-played passed: no profile written by the sender, no expiry, one grant, ids-only gift")

GameConfig.GiftingEnabled=true
------------------------------------------------------------------ duplicate delivery, redelivery after claim, reconnect, a second server
do
 local S=server()
 local R2,SENDER=7210,200
 local req={source="robux",giftId="Rpurchase-1",from=SENDER,to=R2,item="skin_clay",isFriend=false}
 local ok,code=S.send(req) check(ok and code=="queued","robux gift queued")
 ok,code=S.send(req) check(ok and code=="duplicate" and pending(R2)==1,"the same receipt twice is ONE inbox entry")
 local u=user(R2) assert(Repository.load(u))
 local okc,status,summary=S.claim(u) check(okc and summary.applied==1 and data[key(u)].ownedSkins.Clay==true,"claimed")
 check(noticeOf(u).line=="You got a gift from Samantha Display!" and noticeOf(u).canMute==true and noticeOf(u).name=="Samantha Display" and noticeOf(u).kind=="skin","robux popup shows the sender's display name (also as name, for Mute <name>), resolved fresh")
 local c1=wallet(u)
 ok,code=S.send(req) check(ok and code=="queued" and pending(R2)==1,"a receipt re-delivered AFTER the claim re-adds the gift")
 okc,status,summary=S.claim(u) check(okc and summary.already==1 and summary.applied==0 and wallet(u)==c1,"...and claimedGifts blocks the second grant")
 check(pending(R2)==0,"the re-added gift is cleaned up")
 -- crash between the profile commit and the inbox cleanup: re-claim after a reconnect is a harmless no-op
 local R3=7211
 S.send({source="admin",from=ADMIN,to=R3,item="crystals_custom",crystals=100})
 local u3=user(R3) assert(Repository.load(u3))
 local w0=wallet(u3)
 g.block["inbox_"..R3]=true
 okc,status,summary=S.claim(u3)
 check(okc and summary.applied==1 and wallet(u3)==w0+100 and pending(R3)==1,"cleanup failed: the gift is still in the inbox but already granted")
 g.block["inbox_"..R3]=nil
 Repository.release(u3)
 local S2=server() -- a new server instance: no memory of the first claim
 local u3b=user(R3) assert(Repository.load(u3b))
 okc,status,summary=S2.claim(u3b)
 check(okc and summary.already==1 and summary.applied==0 and wallet(u3b)==w0+100 and pending(R3)==0,"after a reconnect the same gift is NOT granted twice and the inbox is cleaned")
 -- a second server cannot claim for a player it does not hold the lease for
 local Repository2=@@REPO_MODULE@@
 local S4=server(GameConfig,Repository2)
 local u3c=user(R3)
 check(not Repository2.load(u3c) and u3c.attrs.ProfileState=="SessionBusy","server B cannot load a profile server A leases")
 S.send({source="admin",from=ADMIN,to=R3,item="crystals_custom",crystals=7})
 local okB,statusB=S4.claim(u3c) check(okB==false and statusB=="profile_not_loaded","server B claims nothing")
 local okB2,resB2=Repository2.applyGifts(u3c,{apply={crystalOp("Ab",5)},revoke={}}) check(okB2==false and resB2=="profile_not_loaded","...and cannot apply a plan")
 check(wallet(u3b)==w0+100 and pending(R3)==1,"the gift waits for the lease owner")
 okc,status,summary=S2.claim(u3b) check(summary.applied==1 and wallet(u3b)==w0+107,"the lease owner claims it once")
 Repository.release(u3b) Repository.release(u)
end
print("GiftService exactly-once passed: duplicate receipts, redelivery after claim, cleanup crash + reconnect, second server")

------------------------------------------------------------------ recipient setting (Everyone/Friends/Nobody), mute, block: at purchase AND at claim
do
 local S=server()
 local sender=0
 local function nextSender() sender+=1 return 300+sender end
 local function pre(to,isFriend,from) return S.preflight({source="robux",from=from or nextSender(),to=to,item="skin_plush",isFriend=isFriend==true}) end
 -- missing record = Everyone
 check(pre(7300),"no pref record: Everyone")
 check(S.setFrom(7301,"nobody") and giftsData.pref_7301.from=="nobody","Nobody is stored")
 local ok,code=pre(7301,true) check(not ok and code=="cant_receive","Nobody refuses at purchase")
 check(S.setFrom(7301,"friends"))
 ok,code=pre(7301,false) check(not ok and code=="cant_receive","Friends refuses a stranger")
 check((pre(7301,true)),"Friends accepts a friend")
 check(S.setFrom(7301,"everyone") and (pre(7301,false)),"Everyone accepts a stranger again")
 check(select(2,S.setFrom(7301,"anyone"))=="bad_request" and giftsData.pref_7301.from=="everyone","an unknown setting is refused and nothing changes")
 -- one identical refusal for every recipient-side reason
 local reasons={}
 S.setFrom(7302,"nobody") local _,c1=pre(7302,true) reasons[c1]=true
 S.setFrom(7303,"friends") local _,c2=pre(7303,false) reasons[c2]=true
 S.reportBlocked(7304,{450}) local _,c3=pre(7304,true,450) reasons[c3]=true
 S.mute(7305,451) local _,c4=pre(7305,true,451) reasons[c4]=true
 check(reasons.cant_receive and next(reasons,"cant_receive")==nil,"setting, friends-only, block and mute all give the SAME code")
 -- block: refused before the prompt, held at claim, also for someone who never played
 check(giftsData.pref_7304.blocked[1]==450,"blocked ids are stored as an array")
 -- at claim: hold, audit once, deliver after the user changes their mind
 local R=7310
 local gid=select(3,S.send({source="robux",giftId="Rhold-1",from=460,to=R,item="skin_balloon"}))
 local u=user(R) assert(Repository.load(u))
 S.setFrom(R,"nobody")
 local okc,status,summary=S.claim(u)
 check(okc and status=="held" and summary.held==1 and data[key(u)].ownedSkins==nil and pending(R)==1 and noticeOf(u)==nil,"Nobody at claim: held, not applied, not announced")
 S.claim(u) S.claim(u)
 local held=0 for _,event in (giftsData["audituser_"..R] or {}) do if event.ev=="held" then held+=1 end end
 check(held==1,"a held gift is audited once, not every minute")
 S.setFrom(R,"everyone")
 okc,status,summary=S.claim(u) check(summary.applied==1 and data[key(u)].ownedSkins.Balloon==true and pending(R)==0,"switched back: delivered, never lost")
 -- friends at claim
 local F=user(7311,{[470]=true}) assert(Repository.load(F))
 S.send({source="robux",giftId="Rf1",from=470,to=7311,item="skin_plush"}) S.send({source="robux",giftId="Rf2",from=471,to=7311,item="skin_clay"})
 S.setFrom(7311,"friends")
 okc,status,summary=S.claim(F) check(summary.applied==1 and summary.held==1 and data[key(F)].ownedSkins~=nil and data[key(F)].ownedSkins.Plush==true and data[key(F)].ownedSkins.Clay==nil,"Friends at claim: the friend's gift lands, the stranger's is held: "..tostring(status).." applied="..tostring(summary and summary.applied).." held="..tostring(summary and summary.held))
 -- mute at claim; admin bypasses the setting and mute but not a block
 local M=user(7312) assert(Repository.load(M))
 S.send({source="robux",giftId="Rm1",from=480,to=7312,item="skin_plush"})
 S.mute(7312,480)
 okc,status,summary=S.claim(M) check(summary.held==1 and data[key(M)].ownedSkins==nil,"a muted sender's gift is held at claim")
 S.setFrom(7312,"nobody")
 local aok,acode,aid=S.send({source="admin",from=ADMIN,to=7312,item="crystals_custom",crystals=25})
 check(aok and aid,"admin bypasses Nobody at send")
 local w=wallet(M)
 okc,status,summary=S.claim(M) check(summary.applied==1 and wallet(M)==w+25 and pending(7312)==1,"admin gift delivered despite Nobody + mute; the player's gift is still held")
 S.reportBlocked(7313,{ADMIN})
 aok,acode=S.send({source="admin",from=ADMIN,to=7313,item="skin_plush"}) check(not aok and acode=="cant_receive" and pending(7313)==0,"admin gifts do NOT bypass a Roblox block")
 -- never-played recipient who reported blocks before their first join: held at first join
 S.reportBlocked(7314,{490})
 S.send({source="robux",giftId="Rb1",from=490,to=7314,item="skin_plush"})
 local P=user(7314) assert(Repository.load(P))
 okc,status,summary=S.claim(P) check(summary.held==1 and data[key(P)].ownedSkins==nil and pending(7314)==1,"first join: a gift from a blocked sender is held, never shown")
 -- reportBlocked / mute are limited to the player's own record by construction
 check(select(2,S.reportBlocked(7315,{1,2,"x"}))=="bad_request" and giftsData.pref_7315==nil,"a bad block report writes nothing")
 for _,u2 in {u,F,M,P} do Repository.release(u2) end
end
print("GiftService recipient controls passed: Everyone/Friends/Nobody (missing = Everyone), mute, block, one refusal, hold + deliver, admin bypass rules")

------------------------------------------------------------------ caps, rate limits, durable daily counters
do
 local S=server()
 -- inbox cap 25 (admin gifts from 25 different admins), the 26th is refused with the one public code
 local R=7400
 for i=1,L.InboxCap do local ok=S.send({source="admin",from=600+i,to=R,item="skin_plush"}) check(ok,"gift "..i.." fits") end
 local ok,code=S.send({source="admin",from=700,to=R,item="skin_plush"})
 check(not ok and code=="cant_receive" and pending(R)==L.InboxCap,"inbox full at 25: refused with the public code, nothing overwritten")
 ok,code=S.preflight({source="robux",from=701,to=R,item="skin_plush"}) check(not ok and code=="cant_receive","a full inbox also refuses before the prompt")
 -- 3 pending per sender
 local R2=7401
 for i=1,L.PerSenderCap do check((S.send({source="robux",giftId="Rcap"..i,from=702,to=R2,item="skin_plush"})),"pending "..i) end
 ok,code=S.preflight({source="robux",from=702,to=R2,item="skin_clay"}) check(not ok and code=="cant_receive","3 pending from one sender: refused before the prompt")
 check((S.preflight({source="robux",from=703,to=R2,item="skin_clay"})),"another sender is fine")
 -- admin: 10 grants a minute
 local A=800
 for i=1,L.AdminGrantsPerMinute do check((S.send({source="admin",from=A,to=7500+i,item="skin_plush"})),"admin grant "..i) end
 ok,code=S.send({source="admin",from=A,to=7599,item="skin_plush"}) check(not ok and code=="rate_limited","11th admin grant in a minute")
 NOW+=61 check((S.send({source="admin",from=A,to=7599,item="skin_plush"})),"a new minute opens")
 -- 3 prompts a minute
 local B=900
 for i=1,L.PromptsPerMinute do check((S.preflight({source="robux",from=B,to=7600+i,item="skin_plush"})),"prompt "..i) end
 ok,code=S.preflight({source="robux",from=B,to=7699,item="skin_plush"}) check(not ok and code=="rate_limited","4th prompt in a minute")
 -- durable daily counters: 10 a day, 3 per recipient, surviving a server hop (a new service instance, same store)
 local C=910
 local hop=S
 for i=1,L.GiftsPerDay do
  NOW+=61
  if i==5 then hop=server() end -- a server hop: new instance, same store
  local ok2,code2=hop.preflight({source="robux",from=C,to=7700+(i%7),item="skin_plush"})
  check(ok2,"gift "..i.." of the day: "..tostring(code2))
 end
 NOW+=61
 ok,code=hop.preflight({source="robux",from=C,to=7799,item="skin_plush"}) check(not ok and code=="daily_limit","the 11th gift of the day is refused, also after a server hop")
 local D=920
 for i=1,L.PerRecipientPerDay do NOW+=61 check((S.preflight({source="robux",from=D,to=7800,item="skin_plush"})),"same recipient "..i) end
 NOW+=61
 ok,code=S.preflight({source="robux",from=D,to=7800,item="skin_plush"}) check(not ok and code=="recipient_limit","3 per recipient per day")
 local hopped=server()
 NOW+=61
 ok,code=hopped.preflight({source="robux",from=D,to=7800,item="skin_plush"}) check(not ok and code=="recipient_limit","...also after a server hop (counters are durable)")
 for i=1,L.GiftsPerDay-L.PerRecipientPerDay do NOW+=61 check((hopped.preflight({source="robux",from=D,to=7801+i,item="skin_plush"})),"daily "..i) end
 NOW+=61
 ok,code=hopped.preflight({source="robux",from=D,to=7899,item="skin_plush"}) check(not ok and code=="daily_limit","10 gifts per buyer per day")
 NOW+=86400
 check((hopped.preflight({source="robux",from=D,to=7800,item="skin_plush"})),"next day: allowed again")
 -- self and bad input
 ok,code=S.preflight({source="robux",from=930,to=930,item="skin_plush"}) check(not ok and code=="self","no gifts to yourself")
 for _,bad in {{source="robux",from=0,to=5,item="skin_plush"},{source="robux",from=5,to=-1,item="skin_plush"},{source="robux",from=5,to=6,item="egg"},{source="robux",from=5,to=6,item="crystals_100"},{source="robux",from=5,to=6,item="skin_plush",msg="hi there"},{source="admin",from=5,to=6,item="skin_plush"},"x",5} do
  ok,code=S.preflight(bad) check(not ok,"preflight refuses bad input")
 end
 for _,bad in {{source="robux",giftId="bad id",from=5,to=6,item="skin_plush"},{source="robux",giftId="Rok",from=5,to=6,item="egg"},{source="robux",giftId="Aok",from=5,to=6,item="skin_plush"},{source="admin",from=5,to=6,item="skin_plush",msg="free text"},{source="admin",from=5,to=6,item="crystals_custom"},{source="admin",from=5,to=0,item="skin_plush"},{source="bank",from=5,to=6,item="skin_plush"},"x"} do
  ok,code=S.send(bad) check(not ok,"send refuses bad input: "..tostring(code))
 end
 -- lookups share one budget
 local look=server()
 for i=1,L.LookupsPerMinute do check((look.allowLookup(950)),"lookup "..i) end
 ok,code=look.allowLookup(950) check(not ok and code=="lookup_minute","lookups: 10 a minute per player")
 check((look.allowLookup(951)),"another player still has a budget")
 NOW+=61 check((look.allowLookup(950)),"a new minute opens")
end
print("GiftService caps and rates passed: inbox 25, 3 per sender, prompts, admin grants, durable daily counters across a server hop, lookups")

------------------------------------------------------------------ revoke before and after claim, idempotent, redelivered receipt
do
 local S=server()
 local R=7900
 -- before claim
 S.send({source="robux",giftId="Rrev-1",from=1000,to=R,item="skin_plush"})
 local ok,status=S.revoke(ADMIN,R,"Rrev-1") check(ok and status=="revoked_pending" and pending(R)==0 and giftsData["inbox_"..R].revoked["Rrev-1"]=="skin_plush","revoke before claim removes it and tombstones it")
 ok,status=S.revoke(ADMIN,R,"Rrev-1") check(ok and status=="already_revoked","revoke is idempotent")
 ok,status=S.send({source="robux",giftId="Rrev-1",from=1000,to=R,item="skin_plush"}) check(not ok and status=="revoked","a re-delivered receipt does not re-add a revoked gift")
 local u=user(R) assert(Repository.load(u))
 local okc,st,summary=S.claim(u)
 check(okc and summary.revoked==1 and data[key(u)].claimedGifts["Rrev-1"]=="revoked" and data[key(u)].ownedSkins==nil and giftsData["inbox_"..R].revoked["Rrev-1"]==nil,"first join: the tombstone moves to the profile")
 okc,st,summary=S.claim(u) check(st=="empty","nothing left to do")
 S.send({source="robux",giftId="Rrev-1",from=1000,to=R,item="skin_plush"})
 okc,st,summary=S.claim(u) check(summary.already==1 and data[key(u)].ownedSkins==nil,"even a re-added revoked id is never granted (profile tombstone)")
 -- after claim
 S.send({source="robux",giftId="Rrev-2",from=1001,to=R,item="skin_bricks"})
 S.send({source="admin",from=ADMIN,to=R,item="crystals_custom",crystals=60})
 S.claim(u)
 check(data[key(u)].ownedSkins.Bricks==true,"claimed")
 local w=wallet(u)
 ok,status=S.revoke(ADMIN,R,"Rrev-2","skin_bricks") check(ok and status=="revoked","revoke after claim: tombstone with the item")
 okc,st,summary=S.claim(u) -- the recipient's server applies it on the next tick (or next load)
 check(summary.revoked==1 and data[key(u)].ownedSkins.Bricks==nil and data[key(u)].claimedGifts["Rrev-2"]=="revoked","claimed skin removed, id tombstoned")
 check(wallet(u)==w,"crystals are not clawed back")
 ok,status=S.revoke(ADMIN,R,"Rrev-2","skin_bricks") check(ok,"revoke again is fine (idempotent)")
 S.claim(u) check(data[key(u)].ownedSkins.Bricks==nil and data[key(u)].claimedGifts["Rrev-2"]=="revoked","...and changes nothing")
 -- item found from the audit trail when no hint is given
 S.send({source="robux",giftId="Rrev-3",from=1002,to=R,item="skin_clay"}) S.claim(u)
 check(data[key(u)].ownedSkins.Clay==true,"claimed")
 ok,status=S.revoke(ADMIN,R,"Rrev-3") check(ok and giftsData["inbox_"..R].revoked["Rrev-3"]=="skin_clay","the audit trail supplies the item")
 S.claim(u) check(data[key(u)].ownedSkins.Clay==nil,"removed")
 -- guards
 for _,bad in {{ADMIN,R,"bad id"},{0,R,"Rx"},{ADMIN,0,"Rx"},{ADMIN,R,5},{ADMIN,R,"Rx","egg"}} do
  ok,status=S.revoke(table.unpack(bad,1,4)) check(not ok and status=="bad_request","revoke refuses bad input")
 end
 local ro=table.clone(GameConfig) ro.AdminGiftsEnabled=false
 local SR=server(ro) check(select(2,SR.revoke(ADMIN,R,"Rx"))=="disabled" and select(2,SR.auditFor(R))=="disabled","revoke and audit need AdminGiftsEnabled")
 local okA,trail=S.auditFor(R) check(okA and #trail>=3,"auditFor returns the user's events")
 Repository.release(u)
end
print("GiftService revoke passed: before claim, after claim, idempotent, tombstone beats a re-delivered receipt, no crystal clawback")

 ---------------------------------------------------------------- BD-590: Take back needs a gift that exists
do
 local S,W=server()
 local R2,R3=7910,7911
 local u=user(R2) assert(Repository.load(u))
 local function claimedCount() local n=0 for _ in (data[key(u)].claimedGifts or {}) do n+=1 end return n end
 local function revokeLogs() local n=0 for _,line in W.printed do if string.find(line,"[BD-GIFT] revoke",1,true) then n+=1 end end return n end
 local function auditHas(userId,ev) for _,e in (giftsData["audituser_"..userId] or {}) do if e.ev==ev then return true end end return false end
 -- an id nobody ever sent: nothing is written anywhere
 local before,beforeProfile,beforeClaimed=copy(giftsData),copy(data[key(u)]),claimedCount()
 local logs0=revokeLogs()
 local ok,status=S.revoke(ADMIN,R2,"Anope")
 check(not ok and status=="unknown_gift","a never-sent id answers unknown_gift")
 check(same(before,giftsData),"unknown id: the Gifts store is byte-for-byte unchanged (no inbox key, no tombstone, no audit line)")
 check(giftsData["inbox_"..R2]==nil and not auditHas(R2,"revoked"),"unknown id: no inbox, no revoked audit event")
 check(claimedCount()==beforeClaimed and same(beforeProfile,data[key(u)]),"unknown id: no claimedGifts entry, profile unchanged")
 S.claim(u) check(claimedCount()==beforeClaimed,"unknown id: the next claim has nothing to apply")
 check(revokeLogs()==logs0+1,"unknown id: exactly one [BD-GIFT] log line")
 -- again and again: still nothing, still the same answer
 for _=1,3 do ok,status=S.revoke(ADMIN,R2,"Anope") check(not ok and status=="unknown_gift","repeat of an unknown id stays unknown_gift") end
 check(same(before,giftsData),"unknown id repeated: still nothing written")
 -- a real gift, wrong recipient: also unknown (nothing proves it was sent to them)
 local sent,_,pendingId=S.send({source="admin",from=ADMIN,to=R3,item="skin_plush"}) check(sent and pendingId~=nil,"real pending gift to someone else")
 local snap=copy(giftsData)
 ok,status=S.revoke(ADMIN,R2,pendingId) check(not ok and status=="unknown_gift" and same(snap,giftsData),"a real id for another recipient is unknown and writes nothing")
 -- forged id formats are refused as bad input before any store request
 local requests=g.requests
 for _,bad in {"nope","Xabc","a123","","bad id","A b","../x",string.rep("A",200),5,true,{}} do
  ok,status=S.revoke(ADMIN,R2,bad) check(not ok and status=="bad_request","forged id format is refused: "..tostring(bad))
 end
 check(g.requests==requests and same(snap,giftsData),"forged ids: no store request at all")
 -- a real pending gift revokes
 ok,status=S.revoke(ADMIN,R3,pendingId) check(ok and status=="revoked_pending" and pending(R3)==0 and giftsData["inbox_"..R3].revoked[pendingId]=="skin_plush","a real pending gift is taken back")
 check(auditHas(R3,"revoked"),"...and audited once")
 ok,status=S.revoke(ADMIN,R3,pendingId) check(ok and status=="already_revoked","repeat of a pending take back is already_revoked")
 -- a real claimed gift revokes, and a repeat is idempotent before and after the recipient's server applies the tombstone
 local _,_,claimedId=S.send({source="admin",from=ADMIN,to=R2,item="skin_bricks"})
 S.claim(u) check(data[key(u)].ownedSkins.Bricks==true and data[key(u)].claimedGifts[claimedId]~=nil,"claimed")
 ok,status=S.revoke(ADMIN,R2,claimedId) check(ok and status=="revoked" and giftsData["inbox_"..R2].revoked[claimedId]=="skin_bricks","a claimed gift is taken back (item read from the audit trail)")
 ok,status=S.revoke(ADMIN,R2,claimedId) check(ok and status=="already_revoked","repeat before the next claim: already_revoked")
 S.claim(u) check(data[key(u)].ownedSkins.Bricks==nil and data[key(u)].claimedGifts[claimedId]=="revoked","the next claim removes the skin (GF16 receipt tombstone on the profile)")
 local settled=copy(giftsData) local settledClaimed=claimedCount()
 ok,status=S.revoke(ADMIN,R2,claimedId) check(ok and status=="already_revoked","repeat after the tombstone moved to the profile: still already_revoked")
 check(same(settled,giftsData) and claimedCount()==settledClaimed,"...and writes nothing (no new tombstone, no new slot)")
 -- a re-delivered receipt still cannot re-add a taken-back Robux gift (GF16)
 S.send({source="robux",giftId="Rrev-590",from=1000,to=R3,item="skin_clay"})
 ok,status=S.revoke(ADMIN,R3,"Rrev-590") check(ok and status=="revoked_pending","a real Robux gift revokes")
 ok,status=S.send({source="robux",giftId="Rrev-590",from=1000,to=R3,item="skin_clay"}) check(not ok and status=="revoked","...and its re-delivered receipt is still refused")
 -- a store outage is try_again, never unknown_gift, and writes nothing
 g.outage=true
 ok,status=S.revoke(ADMIN,R2,"Aabc123") g.outage=false
 check(not ok and status=="try_again","an unreadable audit trail is try_again, not unknown_gift")
 Repository.release(u)
end
print("GiftService revoke needs a real gift passed: unknown id writes nothing, forged ids refused, pending + claimed revoke, repeat idempotent")


------------------------------------------------------------------ corrupt inbox entries, crystal cap, race duplicate
do
 local S=server()
 local R=7950
 local good=GiftRules.newGift("admin",ADMIN,"skin_plush",nil,nil,50,"Agood1")
 local copyOfGood=table.clone(good)
 giftsData["inbox_"..R]={future={keep="me"},gifts={
  Agood1=good,Rtext="not a table",Rwrongid={id="Rother",source="robux",from=5,item="skin_plush",at=1},Rnewer={id="Rnewer",source="robux",from=5,item="skin_from_the_future",at=1},
  Rskincrystals={id="Rskincrystals",source="robux",from=5,item="skin_plush",crystals=900,at=1},Rnofrom={id="Rnofrom",source="robux",item="skin_plush",at=1},
  Rfreetext={id="Rfreetext",source="robux",from=5,item="skin_plush",msg="hello stranger",at=1},
 },revoked={}}
 local u=user(R) assert(Repository.load(u))
 local okc,status,summary=S.claim(u)
 check(okc and status=="claimed" and summary.applied==1 and summary.corrupt==6,"the valid gift is claimed, six corrupt entries are skipped: "..tostring(summary and summary.corrupt))
 check(data[key(u)].ownedSkins.Plush==true and data[key(u)].ownedSkins.Clay==nil,"corrupt entries grant nothing")
 local left=giftsData["inbox_"..R]
 check(left.gifts.Agood1==nil and left.gifts.Rtext=="not a table" and left.gifts.Rnewer~=nil and left.future.keep=="me","corrupt entries stay in place, untouched; unknown inbox fields survive")
 okc,status=S.claim(u) check(okc and status=="held" or status=="empty","a corrupt-only inbox does not loop")
 -- a whole-record corruption is never written over
 giftsData["inbox_"..7951]="garbage"
 local u2=user(7951) assert(Repository.load(u2))
 okc,status=S.claim(u2) check(okc==false and status=="corrupt_inbox" and giftsData["inbox_"..7951]=="garbage","a corrupt inbox record is left exactly as it is")
 local ok,code=S.send({source="admin",from=ADMIN,to=7951,item="skin_plush"}) check(not ok and giftsData["inbox_"..7951]=="garbage","sending into a corrupt record is refused, never overwrites")
 giftsData["inbox_"..7952]={gifts={}, revoked="x"}
 check(select(2,S.send({source="admin",from=ADMIN,to=7952,item="skin_plush"}))~="queued","a corrupt revoked list is not overwritten either")
 -- store outage on claim: nothing applied, nothing lost
 local R3=7953
 S.send({source="admin",from=ADMIN,to=R3,item="skin_plush"})
 local u3=user(R3) assert(Repository.load(u3))
 g.outage=true okc,status=S.claim(u3) g.outage=false
 check(okc==false and status=="try_again" and data[key(u3)].ownedSkins==nil and pending(R3)==1,"Gifts store outage: no partial apply, the gift stays queued")
 okc,status,summary=S.claim(u3) check(summary.applied==1,"recovers when the store returns")
 -- crystals at the wallet cap stay pending
 local R4=7954
 local u4=user(R4) assert(Repository.load(u4)) Repository.release(u4)
 data[key(u4)].progression.crystals=MAXC-5
 assert(Repository.load(u4))
 S.send({source="admin",from=ADMIN,to=R4,item="crystals_custom",crystals=500})
 okc,status,summary=S.claim(u4) check(summary.held==1 and summary.applied==0 and pending(R4)==1 and wallet(u4)==MAXC-5 and noticeOf(u4)==nil,"over the crystal cap: stays pending, not announced")
 -- race duplicate: the player already owns the skin
 local R5=7955
 local u5=user(R5) assert(Repository.load(u5)) Repository.release(u5)
 data[key(u5)].ownedSkins={Plush=true}
 assert(Repository.load(u5))
 local w=wallet(u5)
 S.send({source="admin",from=ADMIN,to=R5,item="skin_plush"})
 okc,status,summary=S.claim(u5)
 check(summary.converted==1 and wallet(u5)==w+L.ThankYouCrystals and noticeOf(u5).converted==true,"race duplicate -> thank-you crystals, announced as such")
 for _,u9 in {u,u2,u3,u4,u5} do Repository.release(u9) end
end
print("GiftService corrupt entries, store outage, crystal cap, race duplicate passed")

------------------------------------------------------------------ GiftAction remote: strict shapes, rate limit, recipient controls only
do
 local S,W,rs=server()
 local remote=rs.children.BeDinoRemotes and rs.children.BeDinoRemotes.children.GiftAction
 check(remote and remote.ClassName=="RemoteFunction" and type(remote.OnServerInvoke)=="function","flag on: the GiftAction remote exists")
 local R=8000
 local u=user(R) assert(Repository.load(u))
 S.send({source="robux",giftId="Rrem-1",from=1100,to=R,item="skin_plush",msg="enjoy"})
 S.send({source="robux",giftId="Rrem-2",from=1101,to=R,item="skin_clay"})
 S.claim(u)
 check(noticeOf(u).canMute==true and noticeOf(u).more==1,"two notices queued")
 local function call(request,...) return remote.OnServerInvoke(u,request,...) end
 for _,bad in {5,"x",{},{action="nope"},{action="mute",userId=1100},{action="ack",extra=true},{action="get",extra=true},{action="get",from="friends"},{action="setFrom"},{action="setFrom",from="anyone"},{action="setFrom",from=5},{action="blocked"},{action="blocked",ids="x"},{action="blocked",ids={1,-2}},{action="turnOff",from="nobody"}} do
  local r=call(bad) check(r.ok==false and (r.reason=="bad_request"),"strict shape: "..tostring(bad)..": "..tostring(r.reason))
  check(noticeOf(u).canMute==true and noticeOf(u).more==1,"bad requests change nothing")
 end
 NOW+=S.ActionWindowSeconds+1
 check(call({action="ack"},"extra").reason=="bad_request","extra arguments are rejected")
 local r=call({action="mute"}) check(r.ok and giftsData.pref_8000.muted[1]==1100 and noticeOf(u).more==0,"Mute: the server mutes the sender of the notice on screen, then shows the next")
 r=call({action="turnOff"}) check(r.ok and giftsData.pref_8000.from=="nobody" and noticeOf(u)=="","Turn gifts off: setting = Nobody, popup closes")
 r=call({action="mute"}) check(r.ok==false and r.reason=="nothing_to_mute","nothing on screen: nothing to mute")
 r=call({action="setFrom",from="friends"}) check(r.ok and giftsData.pref_8000.from=="friends","the Settings row writes the setting")
 -- BD-570: the Settings row reads the saved value through the same remote (a missing record = Everyone, and a read never writes one)
 r=call({action="get"}) check(r.ok and r.from=="friends" and r.reason==nil,"get answers the saved setting")
 do
  local fresh=user(8002) assert(Repository.load(fresh))
  local g0=g.requests
  local rf=remote.OnServerInvoke(fresh,{action="get"})
  check(rf.ok and rf.from=="everyone" and giftsData.pref_8002==nil,"a player with no saved setting reads Everyone and nothing is written")
  check(remote.OnServerInvoke(user(8003),{action="get"}).reason=="profile_not_loaded","get needs a loaded profile")
  local unread=user(8004) assert(Repository.load(unread))
  g.outage=true rf=remote.OnServerInvoke(unread,{action="get"}) g.outage=false
  check(rf.ok==false and rf.reason=="try_again","a store outage answers try_again, not a made-up Everyone")
  Repository.release(fresh) Repository.release(unread)
 end
 r=call({action="blocked",ids={11,12}}) check(r.ok and giftsData.pref_8000.blocked[2]==12 and giftsData.pref_8000.muted[1]==1100 and giftsData.pref_8000.from=="friends","the client reports its blocked ids; other pref fields kept")
 local many={} for i=1,L.BlockedCap+1 do many[i]=i end
 check(call({action="blocked",ids=many}).reason=="bad_request","blocked report over 200 is refused")
 -- the rate limit
 local limited=0
 for i=1,S.ActionsPerWindow+5 do if call({action="ack"}).reason=="rate_limited" then limited+=1 end end
 check(limited>=5,"the action limiter works: "..limited)
 NOW+=S.ActionWindowSeconds+1 check(call({action="ack"}).ok,"window passed: allowed again")
 -- an unloaded player gets nothing
 local ghost=user(8001)
 check(remote.OnServerInvoke(ghost,{action="turnOff"}).reason=="profile_not_loaded" and giftsData.pref_8001==nil,"no profile, no pref write")
 -- the mocked errors never reach the client as a throw
 local brokenStore=giftsStore.UpdateAsync
 giftsStore.UpdateAsync=function() error("boom") end
 check(call({action="setFrom",from="everyone"}).ok==false,"a failing store answers a table, not a throw")
 giftsStore.UpdateAsync=brokenStore
 Repository.release(u)
end
print("GiftAction remote passed: strict shapes, mute/turn-off/setting/blocked, rate limit, no throw")

------------------------------------------------------------------ audit and privacy: UserIds and codes only, no name, no message text, anywhere
do
 local seenAudit=0
 local FIELDS={at=true,ev=true,from=true,to=true,item=true,giftId=true,purchaseId=true,code=true}
 for k,list in giftsData do
  if string.sub(k,1,6)=="audit_" or string.sub(k,1,10)=="audituser_" then
   check(type(list)=="table" and #list>=1 and #list<=(if string.sub(k,1,6)=="audit_" then L.AuditDayCap else L.AuditUserCap),"audit list is capped: "..k)
   for _,event in list do
    seenAudit+=1
    for field,value in event do check(FIELDS[field]==true,"audit field is whitelisted: "..field) end
    local rebuilt=GiftRules.auditEvent(event.ev,event.at,event.from,event.to,event.item,event.giftId,event.purchaseId,event.code)
    check(rebuilt~=nil and same(rebuilt,event),"every stored audit event re-validates: "..k)
   end
  end
 end
 check(seenAudit>20,"events were recorded: "..seenAudit)
 local days=0 for k in giftsData do if string.match(k,"^audit_%d%d%d%d%d%d%d%d$") then days+=1 end end
 check(days>=1,"day lists are keyed yyyymmdd")
 local FORBIDDEN={"Samantha","Have fun","Enjoy!","can't get gifts","You got a gift","Be Dino team"}
 local function scan(label,value,path)
  if type(value)=="string" then
   for _,word in FORBIDDEN do check(not string.find(value,word,1,true),label.." stores no names or text: "..path.." = "..value) end
  elseif type(value)=="table" then
   for k,v in value do scan(label,k,path.."/key") scan(label,v,path.."/"..tostring(k)) end
  end
 end
 for k,v in giftsData do scan("Gifts store",v,k) end
 for k,v in data do scan("profile store",v,k) end
end
print("Audit and privacy passed: UserIds and codes only; no display name, message text or UI copy in any store")
'''

ADMIN = r'''
------------------------------------------------------------------ (E) BD-452 AdminGifts: the admin Gift page, server side, on the REAL GiftService
do
 GameConfig.GiftClaimEnabled=true GameConfig.AdminGiftsEnabled=true GameConfig.AdminPanelEnabled=true GameConfig.GiftingEnabled=false
 local AdminRulesMod=@@ADMIN_RULES@@
 local function mockPlayer(id,display,name) return {UserId=id,DisplayName=display or ("Display"..id),Name=name or ("user"..id)} end
 local roster=setmetatable({},{__index=function(t,id)
  if type(id)=="number" and id>=9000 and id<9400 then local p=mockPlayer(id) rawset(t,id,p) return p end
  return nil
 end})
 local ADMIN2=101
 local admin,admin2,rando,negative,zero=mockPlayer(ADMIN,"Boss","boss"),mockPlayer(ADMIN2,"Boss Two","boss2"),mockPlayer(555),mockPlayer(-1),mockPlayer(0)
 -- The server's admin test: AdminRules.isAdmin over the UserId allow-list (no creator match, not Studio).
 local function isAdminFor(cfg) return function(p)
  return AdminRulesMod.isAdmin({userId=p.UserId,creatorType="User",creatorId=0,groupRank=nil,adminIds={ADMIN,ADMIN2},unpublishedStudio=false,enabled=cfg.AdminPanelEnabled})
 end end
 -- Public profiles the default resolver finds (Players:GetUserIdFromNameAsync + UserService).
 local directory={never_played={id=9100,display="Pat",user="never_played",info=true},offline_olly={id=9101,display="Olly",user="offline_olly",info=true},
  broken_info={id=9102,display="x",user="broken_info",info=false},blocker_bob={id=9301,display="Bob",user="blocker_bob",info=true}}
 local ACLOCK=1000
 local function makeAdmin(cfg,S)
  local world={instances=0,printed={},lookups=0}
  local rs={children={},Shared={Config="Config",GiftRules="GiftRules",AdminGiftRules="AdminGiftRules"}}
  function rs:FindFirstChild(n) return self.children[n] end
  local Instance={new=function(class)
   world.instances+=1
   local o={ClassName=class,Name=class,children={}}
   return setmetatable(o,{__newindex=function(t,k,v) rawset(t,k,v) if k=="Parent" and v then v.children[rawget(t,"Name")]=t end end})
  end}
  local services={
   Players={GetPlayerByUserId=function(_,id) return roster[id] end,
    GetUserIdFromNameAsync=function(_,name) world.lookups+=1 local entry=directory[name] if not entry then error("HTTP 400 (not found)") end return entry.id end},
   UserService={GetUserInfosByUserIdsAsync=function(_,ids)
    for _,entry in directory do
     if entry.id==ids[1] then return if entry.info then {{DisplayName=entry.display,Username=entry.user}} else {} end
    end
    return {}
   end},
   ReplicatedStorage=rs,
  }
  local game={GetService=function(_,n) return services[n] or error("service "..n.." is not modelled") end}
  local script={Parent={GiftService="GiftService",GiftRules="GiftRules"}}
  local PageRules
  local require=function(id)
   if id=="Config" then return cfg elseif id=="GiftRules" then return GiftRules elseif id=="AdminGiftRules" then return PageRules elseif id=="GiftService" then return S end
   error("unexpected module "..tostring(id))
  end
  local print=function(s) table.insert(world.printed,s) end
  PageRules=@@ADMIN_GIFT_RULES@@
  local Module=@@ADMIN_GIFTS@@
  Module.setClock(function() return ACLOCK end)
  return Module,world,PageRules
 end
 local function asText(value,words)
  local found
  local function walk(v) if type(v)=="string" then for _,w in words do if string.find(v,w,1,true) then found=w end end elseif type(v)=="table" then for k,x in v do walk(k) walk(x) end end end
  walk(value) return found
 end

 ---------------------------------------------------------------- flag-off identity: no page (no remote), no work
 for label,mutate in {claim=function(c) c.GiftClaimEnabled=false end,adminGifts=function(c) c.AdminGiftsEnabled=false end,panel=function(c) c.AdminPanelEnabled=false end} do
  local cfg=table.clone(GameConfig) mutate(cfg)
  local S0=server(cfg)
  local M0,W0=makeAdmin(cfg,S0)
  local folder0={children={}}
  local r0=g.requests
  check(M0.start(folder0,isAdminFor(cfg))==nil and W0.instances==0 and next(folder0.children)==nil,"flag off ("..label.."): start() creates no remote, no page for the client to find")
  local r=M0.handle(admin,{action="pick",userId=9201}) check(r.ok==false,"flag off ("..label.."): the handler refuses")
  local r2=M0.handle(admin,{action="audit",userId=9201}) check(r2.ok==false and (r2.reason=="disabled" or r2.reason=="not_admin"),"flag off ("..label.."): answers disabled")
  check(g.requests==r0 and W0.lookups==0 and #W0.printed==0 and W0.instances==0,"flag off ("..label.."): no store request, no lookup, no log, no instance")
 end

 ---------------------------------------------------------------- non-admins are refused BEFORE any store access
 local S,SW=server()
 local M,W,PageRules=makeAdmin(GameConfig,S)
 local folder={children={}}
 local remote=M.start(folder,isAdminFor(GameConfig))
 check(remote and remote.ClassName=="RemoteFunction" and remote.Name=="AdminGiftAction" and folder.children.AdminGiftAction==remote and type(remote.OnServerInvoke)=="function","flags on: the AdminGiftAction remote exists")
 local function call(p,req) ACLOCK+=1 return remote.OnServerInvoke(p,req) end
 local function sendTo(p,id,item,extra)
  local r=call(p,{action="pick",userId=id}) if not r.ok then return r end
  r=call(p,{action="confirm",userId=id}) if not r.ok then return r end
  local req={action="send",to=id,item=item or "skin_plush"} for k,v in extra or {} do req[k]=v end
  return call(p,req)
 end
 do
  local r0,l0,p0,s0=g.requests,W.lookups,#W.printed,#SW.printed
  local requests={{action="pick",userId=9201},{action="lookup",name="never_played"},{action="confirm",userId=9201},{action="send",to=9201,item="skin_plush"},
   {action="revoke",to=9201,giftId="Aabc"},{action="audit",userId=9201},"junk",5,{action="nope"},{}}
  for _,who in {rando,negative,zero,mockPlayer(ADMIN+7)} do
   for _,req in requests do
    local r=call(who,req) check(r.ok==false and r.reason=="not_admin","non-admin "..who.UserId.." refused first: "..tostring(type(req)=="table" and req.action or req))
   end
  end
  check(remote.OnServerInvoke(rando,{action="audit",userId=1},"extra").reason=="not_admin","a non-admin is refused before the argument check")
  check(g.requests==r0 and W.lookups==l0 and #W.printed==p0 and #SW.printed==s0,"non-admin: ZERO store requests, no lookup, no log line")
  check(not isAdminFor(GameConfig)(rando) and isAdminFor(GameConfig)(admin) and isAdminFor(GameConfig)(admin2),"the allow-list is AdminRules.isAdmin over Config.AdminUserIds")
  local r=call(admin,{action="send",to=9201,item="skin_plush"}) check(r.ok==false and r.reason=="not_confirmed","no target without pick and Yes")
  check(remote.OnServerInvoke(admin,{action="audit",userId=7771},"extra").reason=="bad_request","extra arguments are rejected for an admin")
  check(g.requests==r0,"...and still no store request")
 end

 ---------------------------------------------------------------- send to an online player: pick, Yes, send; label fixed; stored gift is ids only
 local firstGift
 do
  local r=call(admin,{action="pick",userId=9201}) check(r.ok and r.userId==9201 and r.displayName=="Display9201" and r.username=="user9201","pick an online player")
  r=call(admin,{action="send",to=9201,item="skin_plush"}) check(not r.ok and r.reason=="not_confirmed" and pending(9201)==0,"picked but not confirmed: nothing sent")
  r=call(admin,{action="confirm",userId=9999}) check(not r.ok and r.reason=="not_confirmed","Yes for somebody else is refused")
  r=call(admin,{action="confirm",userId=9201}) check(r.ok and r.displayName=="Display9201","Yes confirms the picked player")
  r=call(admin,{action="send",to=9202,item="skin_plush"}) check(not r.ok and r.reason=="not_confirmed","only the confirmed player can be sent a gift")
  r=call(admin2,{action="send",to=9201,item="skin_plush"}) check(not r.ok and r.reason=="not_confirmed","another admin's confirmation is not mine")
  r=call(admin,{action="send",to=9201,item="skin_plush",msg="have_fun"})
  check(r.ok and r.status=="queued" and string.sub(r.giftId,1,1)=="A" and r.label==GiftRules.TeamLine and r.label=="A gift from the Be Dino team!","sent through GiftService.send, label fixed")
  firstGift=r.giftId
  local entry=inbox(9201).gifts[firstGift]
  local keys={} for k in entry do table.insert(keys,k) end table.sort(keys)
  check(table.concat(keys,",")=="at,from,id,item,msg,source" and entry.source=="admin" and entry.from==ADMIN and entry.item=="skin_plush" and entry.msg=="have_fun","stored: ids only, source admin, the caller's own UserId, no label field")
  r=call(admin,{action="send",to=9201,item="skin_clay"}) check(r.ok,"the confirmed player can get a second gift")
  r=call(admin,{action="pick",userId=9202}) r=call(admin,{action="send",to=9201,item="skin_clay"}) check(not r.ok and r.reason=="not_confirmed","picking somebody else clears the confirmation")
  r=call(admin,{action="pick",userId=7}) check(not r.ok and r.reason=="not_here","a player who is not here")
  for _,bad in {-1,0,1.5,"x",0/0,true} do r=call(admin,{action="pick",userId=bad}) check(not r.ok and r.reason=="bad_request","bad pick id "..tostring(bad)) end
 end

 ---------------------------------------------------------------- offline and never-played users by username (display name confirm), one claim at first join
 do
  local r=call(admin,{action="lookup",name="never_played"})
  check(r.ok and r.userId==9100 and r.displayName=="Pat" and r.username=="never_played","username lookup returns display name and @username for the confirm card")
  r=call(admin,{action="send",to=9100,item="crystals_custom",crystals=250}) check(not r.ok and r.reason=="not_confirmed","a looked-up user must be confirmed first")
  r=call(admin,{action="confirm",userId=9100}) check(r.ok,"Yes")
  r=call(admin,{action="send",to=9100,item="crystals_custom",crystals=250,msg="thank_you"}) check(r.ok and r.status=="queued","sent to a user who never played")
  check(data["u:9100"]==nil and inbox(9100).gifts[r.giftId].crystals==250,"never-played recipient: the gift waits in the inbox, no profile is written")
  local u=user(9100) assert(Repository.load(u))
  local w0=wallet(u)
  local okc,status,summary=S.claim(u)
  check(okc and summary.applied==1 and wallet(u)==w0+250,"first join: granted once")
  check(noticeOf(u).line=="A gift from the Be Dino team!" and noticeOf(u).message=="Thank you!" and noticeOf(u).canMute==false,"popup: the fixed team label, no admin name")
  check(noticeOf(u).item=="250 crystals","popup: the custom admin amount is named (BD-579), not just 'Crystals'")
  Repository.release(u)
  local l0=W.lookups
  for _,name in {"ab","a b c",string.rep("x",21),"","bad-name!",5,"semi;colon"} do
   r=call(admin,{action="lookup",name=name}) check(not r.ok and r.reason=="bad_name","bad username refused: "..tostring(name))
  end
  check(W.lookups==l0,"a bad username never reaches Roblox")
  r=call(admin,{action="lookup",name="no_such_user"}) check(not r.ok and r.reason=="not_found","unknown username: not found")
  r=call(admin,{action="lookup",name="broken_info"}) check(not r.ok and r.reason=="try_again","public profile unavailable: try again")
  r=call(admin,{action="lookup",name="offline_olly"}) check(r.ok and r.userId==9101,"another offline user")
 end

 ---------------------------------------------------------------- items, amounts, messages are validated by the server (no silent clamping)
 do
  call(admin,{action="pick",userId=9205}) call(admin,{action="confirm",userId=9205})
  local r0=g.requests
  for _,bad in {0,50001,1.5,"5",0/0,math.huge,-3,1e9,true} do
   local r=call(admin,{action="send",to=9205,item="crystals_custom",crystals=bad}) check(not r.ok and r.reason=="bad_amount","crystal amount refused: "..tostring(bad))
  end
  check(call(admin,{action="send",to=9205,item="crystals_custom"}).reason=="bad_amount","the custom crystals item needs an amount")
  check(call(admin,{action="send",to=9205,item="skin_plush",crystals=5}).reason=="bad_amount","a skin takes no amount")
  check(call(admin,{action="send",to=9205,item="crystals_100",crystals=100}).reason=="bad_amount","a fixed pack takes no amount either")
  for _,bad in {"egg","",5,"skin_unknown","dino","crystals_custom "} do check(call(admin,{action="send",to=9205,item=bad}).reason=="unknown_item","unknown item refused: "..tostring(bad)) end
  for _,bad in {"hello there","Have fun!","",5,true} do check(call(admin,{action="send",to=9205,item="skin_plush",msg=bad}).reason=="bad_message","free text refused: "..tostring(bad)) end
  check(g.requests==r0,"refused requests made no store request")
  local r=call(admin,{action="send",to=9205,item="crystals_custom",crystals=50000}) check(r.ok and inbox(9205).gifts[r.giftId].crystals==50000,"the cap itself is allowed")
  check(PageRules.amountOk(1) and PageRules.amountOk(50000) and not PageRules.amountOk(50001) and not PageRules.amountOk(0),"amountOk")
 end

 ---------------------------------------------------------------- the label (and the sender) can never come from the request
 do
  call(admin,{action="pick",userId=9206}) call(admin,{action="confirm",userId=9206})
  local base={action="send",to=9206,item="skin_plush"}
  for _,extra in {{label="From Boss!"},{from=1},{source="robux"},{giftId="Rfake"},{name="Boss"},{text="hi"},{isFriend=true},{at=1}} do
   local req=table.clone(base) for k,v in extra do req[k]=v end
   local r=call(admin,req) check(not r.ok and r.reason=="bad_request","extra key refused: "..next(extra))
  end
  check(pending(9206)==0,"nothing was sent by the rejected requests")
  local r=call(admin,base) check(r.ok and r.label==GiftRules.TeamLine,"the plain request works and carries the fixed label")
  check(GiftRules.noticeLine("admin","Boss")==GiftRules.TeamLine and GiftRules.noticeLine("admin",nil)==GiftRules.TeamLine and GiftRules.TeamLine=="A gift from the Be Dino team!","popup text for an admin gift is the team line")
  for id,held in giftsData do
   local owner=tonumber(string.match(id,"^inbox_(%d+)$"))
   if owner and owner>=9000 and owner<9400 then -- the recipients this section used
    for _,gift in held.gifts do
     check(gift.label==nil and gift.name==nil and (gift.from==ADMIN or gift.from==ADMIN2),"admin gift has no label or name field and the caller's own id: "..id)
    end
   end
  end
 end

 ---------------------------------------------------------------- revoke by gift id: pending, claimed, idempotent, bad input
 local revokedPending,revokedClaimed
 do
  NOW+=61
  local r=sendTo(admin,9203,"skin_clay") check(r.ok,"gift to revoke") revokedPending=r.giftId
  r=call(admin,{action="revoke",to=9203,giftId=revokedPending}) check(r.ok and r.status=="revoked_pending" and pending(9203)==0 and giftsData["inbox_9203"].revoked[revokedPending]=="skin_clay","revoke before they open it")
  r=call(admin,{action="revoke",to=9203,giftId=revokedPending}) check(r.ok and r.status=="already_revoked","revoke is idempotent")
  r=sendTo(admin,9204,"skin_bricks") check(r.ok,"gift to revoke after claim") revokedClaimed=r.giftId
  local u=user(9204) assert(Repository.load(u)) S.claim(u)
  check(data[key(u)].ownedSkins.Bricks==true,"claimed")
  r=call(admin,{action="revoke",to=9204,giftId=revokedClaimed,item="skin_bricks"}) check(r.ok and r.status=="revoked","revoke after claim writes the tombstone")
  S.claim(u)
  check(data[key(u)].ownedSkins.Bricks==nil and data[key(u)].claimedGifts[revokedClaimed]=="revoked","the next claim takes the skin back and tombstones the id")
  Repository.release(u)
  local snapAdmin=copy(giftsData)
  r=call(admin,{action="revoke",to=9203,giftId="Anever-sent-590"}) check(not r.ok and r.reason=="unknown_gift" and same(snapAdmin,giftsData),"admin page: an id that was never sent answers unknown_gift and writes nothing (BD-590)")
  check(PageRules.explain(r.reason)=="No gift with that number.","...and the page says so in plain words")
  r=call(admin,{action="revoke",to=9203,giftId="nope"}) check(not r.ok and r.reason=="bad_request" and same(snapAdmin,giftsData),"admin page: a forged id format is refused")
  for _,bad in {{to=9203,giftId="bad id"},{to=0,giftId="Aabc"},{to=9203,giftId="Aabc",item="egg"},{to=9203},{giftId="Aabc"},{to=1.5,giftId="Aabc"},{to=9203,giftId=5}} do
   local req={action="revoke"} for k,v in bad do req[k]=v end
   local rr=call(admin,req) check(not rr.ok and rr.reason=="bad_request","revoke refuses bad input")
  end
 end

 ---------------------------------------------------------------- audit view by UserId: whitelisted ids and codes only
 do
  local r=call(admin,{action="audit",userId=9203})
  check(r.ok and #r.events>=2,"audit returns the user's events")
  local seenAdmin,seenRevoked,last=false,false,math.huge
  local FIELDS={at=true,ev=true,from=true,to=true,item=true,giftId=true,purchaseId=true,code=true}
  for _,event in r.events do
   check(event.at<=last,"newest first") last=event.at
   for field in event do check(FIELDS[field]==true,"audit field is whitelisted: "..field) end
   if event.ev=="admin" then seenAdmin=true end if event.ev=="revoked" then seenRevoked=true end
  end
  check(seenAdmin and seenRevoked,"the send and the revoke are both in the trail")
  check(asText(r,{"Display9203","user9203","Boss","Have fun"})==nil,"the audit answer holds no name and no text")
  check(call(admin,{action="audit",userId=0}).reason=="bad_request" and call(admin,{action="audit",userId=-4}).reason=="bad_request" and call(admin,{action="audit"}).reason=="bad_request","audit needs a valid UserId")
  local empty=call(admin,{action="audit",userId=9390}) check(empty.ok and #empty.events==0,"nothing recorded: an empty list")
  local line=PageRules.historyLine(r.events[1]) check(type(line)=="string" and #line>3 and not string.find(line,"Display",1,true),"history lines are ids and codes")
 end

 ---------------------------------------------------------------- Roblox blocks beat admin gifts; the recipient setting and mute do not
 do
  NOW+=61
  S.reportBlocked(9300,{ADMIN})
  local r=sendTo(admin,9300,"skin_plush") check(not r.ok and r.reason=="cant_receive" and pending(9300)==0,"a user who blocked the admin account is refused with the one public code")
  r=call(admin,{action="lookup",name="blocker_bob"}) check(r.ok,"offline lookup of a blocker")
  S.reportBlocked(9301,{ADMIN})
  call(admin,{action="confirm",userId=9301})
  r=call(admin,{action="send",to=9301,item="skin_clay"}) check(not r.ok and r.reason=="cant_receive" and pending(9301)==0,"...also by username")
  r=sendTo(admin2,9300,"skin_plush") check(r.ok and pending(9300)==1,"a block is per account: another admin can still send")
  S.setFrom(9302,"nobody") S.mute(9302,ADMIN)
  r=sendTo(admin,9302,"skin_plush") check(r.ok,"admin gifts bypass Nobody and mute")
  S.setFrom(9303,"friends")
  r=sendTo(admin,9303,"skin_plush") check(r.ok,"admin gifts bypass Friends")
  local trail=call(admin,{action="audit",userId=9300})
  local refused=false for _,event in trail.events do if event.ev=="refused" and event.code=="blocked" then refused=true end end
  check(refused,"the refusal is in the audit trail (the team can see why; the player never sees a reason)")
 end

 ---------------------------------------------------------------- admin rate limit: 10 a minute, per admin
 do
  local S2=server() local M2=makeAdmin(GameConfig,S2)
  local f2={children={}} local remote2=M2.start(f2,isAdminFor(GameConfig))
  NOW+=61
  local function call2(p,req) ACLOCK+=1 return remote2.OnServerInvoke(p,req) end
  local function send2(p,id) call2(p,{action="pick",userId=id}) call2(p,{action="confirm",userId=id}) return call2(p,{action="send",to=id,item="skin_plush"}) end
  for i=1,L.AdminGrantsPerMinute do check(send2(admin,9210+i).ok,"admin gift "..i) end
  local r=send2(admin,9230) check(not r.ok and r.reason=="rate_limited" and pending(9230)==0,"the 11th gift in a minute is refused")
  check(send2(admin2,9231).ok,"another admin has their own budget")
  NOW+=61 check(send2(admin,9230).ok,"a new minute opens")
  -- username lookups share GiftService's budget (10 a minute per player)
  NOW+=61
  local look=server() local M3=makeAdmin(GameConfig,look) local f3={children={}} local remote3=M3.start(f3,isAdminFor(GameConfig))
  local ok,why=0,nil
  for i=1,L.LookupsPerMinute+2 do ACLOCK+=1 local rr=remote3.OnServerInvoke(admin,{action="lookup",name="offline_olly"}) if rr.ok then ok+=1 else why=rr.reason end end
  check(ok==L.LookupsPerMinute and why=="lookup_minute","10 lookups a minute, then 'slow down': "..ok.." "..tostring(why))
 end

 ---------------------------------------------------------------- logs, throttle, thrown errors
 do
  local sawServer,sawPage,sawRevoke=false,false,false
  for _,line in SW.printed do if string.find(line,"[BD-GIFT] admin from=100 to=9201 item=skin_plush id=A",1,true) then sawServer=true end end
  for _,line in W.printed do
   if string.find(line,"[BD-GIFT] admin-page send admin=100 to=9201 item=skin_plush result=queued",1,true) then sawPage=true end
   if string.find(line,"[BD-GIFT] admin-page revoke admin=100 to=9203",1,true) then sawRevoke=true end
  end
  check(sawServer and sawPage and sawRevoke,"[BD-GIFT] log lines for the send (service + page) and the revoke")
  check(asText(SW.printed,{"Display","Boss","user9","Pat"})==nil and asText(W.printed,{"Display","Boss","user9","Pat","Have fun"})==nil,"log lines hold UserIds, item ids and codes, never names or text")
  check(giftsData["audituser_9201"][1].ev=="admin" and giftsData["audituser_9201"][1].from==ADMIN,"an audit record exists for the send")
  ACLOCK+=1
  local t1=remote.OnServerInvoke(admin,{action="audit",userId=9201}) local t2=remote.OnServerInvoke(admin,{action="audit",userId=9201})
  check(t1.ok==true and t2.ok==false and t2.reason=="busy","two requests inside 0.15 s: the second is 'busy'")
  ACLOCK+=1
  M.setLookup(function() error("boom") end)
  local r=remote.OnServerInvoke(admin,{action="lookup",name="never_played"}) check(r.ok==false and r.reason=="error","a thrown error answers a table, not a throw")
  M.setLookup(nil)
  ACLOCK+=1
 end

 ---------------------------------------------------------------- pure page rules
 do
  check(PageRules.shapeOk({action="pick",userId=1})=="pick" and PageRules.shapeOk({action="send",to=1,item="x",crystals=2,msg="y"})=="send" and PageRules.shapeOk({action="audit",userId=1})=="audit","shapes")
  for _,bad in {5,"x",{},{action=5},{action="nope"},{action="pick",userId=1,extra=true},{action="send",label="x"},{action="lookup",userId=1},{[1]=1,action="pick"}} do check(PageRules.shapeOk(bad)==nil,"bad shape") end
  check(PageRules.validName("abc") and PageRules.validName("a_b_c_1") and not PageRules.validName("ab") and not PageRules.validName("a b") and not PageRules.validName(string.rep("a",21)) and not PageRules.validName(nil),"usernames")
  check(PageRules.parseAmount("1,000")==1000 and PageRules.parseAmount(" 50 000 ")==50000 and PageRules.parseAmount("50,001")==nil and PageRules.parseAmount("0")==nil and PageRules.parseAmount("12a")==nil
   and PageRules.parseAmount("")==nil and PageRules.parseAmount("99999999")==nil and PageRules.parseAmount("1.5")==nil and PageRules.parseAmount(5)==nil and PageRules.parseAmount("-5")==nil,"typed amounts")
  local choices=PageRules.choices()
  check(#choices==5 and choices[5].id==GiftRules.CustomCrystalsId and choices[5].kind=="crystals","the page offers the four skins and a crystal amount")
  for _,c in choices do check((GiftRules.itemAllowed(c.id,"admin")) and #c.label>=3 and (c.kind=="skin")==(GiftRules.ById[c.id].kind=="skin"),"choice is a catalogue item: "..c.id) end
  for _,chip in PageRules.CrystalChips do check(PageRules.amountOk(chip),"chip within the cap: "..chip) end
  check(PageRules.explain("cant_receive")=="They can't get gifts right now." and PageRules.explain("zzz_unknown")=="Failed: zzz unknown" and PageRules.explain(nil)~=nil,"explain")
  check(PageRules.stamp(0)=="01-01 00:00" and PageRules.stamp(951782400+3600*13+120)=="02-29 13:02","stamps")
  local events={} for i=1,60 do events[i]={at=i,ev="admin",from=5,to=6,item="skin_plush",giftId="A"..i} end
  table.insert(events,{at=99,ev="admin",from="Sam",to=6}) table.insert(events,"junk") table.insert(events,{at=98,ev="claimed",from=5,to=6,item="skin_plush",giftId="Rhas space"})
  local clean=PageRules.cleanHistory(events)
  check(#clean==PageRules.HistoryMax and clean[1].at==60 and clean[#clean].at==60-PageRules.HistoryMax+1,"history: junk dropped, newest 50, newest first")
  check(PageRules.historyLine(clean[1])==PageRules.stamp(60).."  Sent by the team  Plushy skin  5 to 6\nid A60","history line")
 end
end
print("Admin gifts (BD-452) passed: flag-off identity, non-admin refused before any store access, pick/lookup + Yes, send/revoke/audit on the real GiftService, rate limits, block refusal, fixed label")
print("Admin gifts verified")
'''

OLD = r'''
------------------------------------------------------------------ (D) migration and rollback rule RB1 against the frozen Build 020 reader
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
 local VOLATILE={session=true,revision=true,metrics=true} -- the play-time metric moves with the clock
 local function sameData(a,b)
  for k,v in a do if not VOLATILE[k] and not same(v,b[k]) then return false,k end end
  for k in b do if not VOLATILE[k] and a[k]==nil then return false,k end end
  return true
 end
 local S=server()

 -- MIGRATION: an older profile without the fields is untouched until a gift is claimed.
 local M=8100
 local older=user(M) assert(Repository.load(older)) Repository.release(older)
 local stored=data[key(older)]
 check(stored.claimedGifts==nil and stored.ownedSkins==nil,"an older profile has neither field")
 local before=copy(stored)
 local u=user(M) assert(Repository.load(u))
 check(select(2,S.claim(u))=="empty","flags on, empty inbox: claim reads the inbox only")
 local t0=transforms
 S.claim(u) S.claim(u)
 check(transforms==t0,"claiming an empty inbox makes no profile transform")
 Repository.renew(u) Repository.release(u)
 local okSame,diff=sameData(before,data[key(u)])
 check(okSame,"flags on but no gift: the stored profile is byte-identical apart from lease/revision ("..tostring(diff)..")")
 check(data[key(u)].claimedGifts==nil and data[key(u)].ownedSkins==nil,"no gift received: the fields are still absent after load, claim, renew and release")

 -- RB1a: Build 020 loads a profile that never received a gift, and leaves it alone
 local ou=user(M)
 check(OldRepo.load(ou) and ou.attrs.ProfileState=="Loaded","RB1: Build 020 loads a profile that never received a gift")
 local afterLoad=copy(data[key(ou)])
 check(OldRepo.renew(ou),"Build 020 renews it")
 OldRepo.release(ou)
 okSame,diff=sameData(before,data[key(ou)])
 check(okSame,"Build 020 session leaves the profile equal ("..tostring(diff)..")")
 -- ...and the current code loads what Build 020 wrote
 local back=user(M) check(Repository.load(back),"roll-forward after a Build 020 session") Repository.release(back)

 -- RB1b: a profile that DID receive gifts: Build 020 loads it and preserves both fields byte-for-byte
 local G=8101
 S.send({source="admin",from=ADMIN,to=G,item="skin_bricks"}) S.send({source="admin",from=ADMIN,to=G,item="crystals_custom",crystals=75})
 local gu=user(G) assert(Repository.load(gu))
 local okc,st,summary=S.claim(gu) check(summary.applied==2,"gifts claimed")
 Repository.release(gu)
 local gifted=copy(data[key(gu)])
 check(gifted.ownedSkins.Bricks==true and next(gifted.claimedGifts)~=nil,"gifted profile carries claimedGifts + ownedSkins")
 local og=user(G)
 check(OldRepo.load(og) and og.attrs.ProfileState=="Loaded","RB1: Build 020 loads a profile that received gifts (unknown fields are ignored)")
 OldRepo.renew(og) OldRepo.release(og)
 check(same(gifted.claimedGifts,data[key(og)].claimedGifts) and same(gifted.ownedSkins,data[key(og)].ownedSkins),"Build 020 preserves claimedGifts and ownedSkins byte-for-byte")
 check(data[key(og)].progression.crystals==gifted.progression.crystals,"the gifted crystals are kept")
 local fwd=user(G) check(Repository.load(fwd),"current code loads it again")
 okc,st,summary=S.claim(fwd) check(st=="empty" and data[key(fwd)].ownedSkins.Bricks==true,"roll-forward: nothing granted twice")
 Repository.release(fwd)

 -- flags turned OFF again: the fields stay exactly as they are
 GameConfig.GiftClaimEnabled=false
 local off=user(G) assert(Repository.load(off)) Repository.renew(off) Repository.release(off)
 check(same(gifted.claimedGifts,data[key(off)].claimedGifts) and same(gifted.ownedSkins,data[key(off)].ownedSkins),"flag off again: existing gift fields untouched")
 GameConfig.GiftClaimEnabled=true
end
print("Migration + RB1 passed: older profile untouched, Build 020 loads gift-free profiles, preserves gifted ones, roll-forward grants nothing twice")
print("Gifting core verified: "..checks.." checks")
'''


def fill(text: str) -> str:
    for token, path in [
        ('@@PROGRESSION_CONFIG@@', 'src/shared/ProgressionConfig.luau'),
        ('@@GAME_CONFIG@@', 'src/shared/Config.luau'),
        ('@@FOOD_RULES@@', 'src/shared/FoodCatchRules.luau'),
        ('@@GENETICS@@', 'src/shared/EggGenetics.luau'),
        ('@@EGG_TRAITS@@', 'src/shared/EggTraits.luau'),
        ('@@RULES@@', 'src/shared/ProgressionRules.luau'),
        ('@@FUSION_ODDS@@', 'src/server/FusionOdds.luau'),
        ('@@REVEAL_SKIP@@', 'src/shared/RevealSkip.luau'),
        ('@@NEST_QUEUE@@', 'src/shared/NestQueue.luau'),
        ('@@FTUE_RULES@@', 'src/shared/FtueRules.luau'),
        ('@@SETTINGS_MODEL@@', 'src/shared/SettingsModel.luau'),
        ('@@PAID_RANDOM_GATE@@', 'src/shared/PaidRandomGate.luau'),
        ('@@REWARD_MATH@@', 'src/server/RewardMath.luau'),
        ('@@IDENTITY_FUSION_MODULE@@', 'src/server/IdentityFusion.luau'),
        ('@@IDENTITY_MODULE@@', 'src/server/DinosaurIdentity.luau'),
        ('@@COSMETIC_OWNERSHIP@@', 'src/server/CosmeticOwnership.luau'),
        ('@@GIFT_RULES@@', 'src/shared/GiftRules.luau'),
        ('@@GIFT_SERVICE@@', 'src/server/GiftService.luau'),
        ('@@ADMIN_RULES@@', 'src/shared/AdminRules.luau'),
        ('@@ADMIN_GIFT_RULES@@', 'src/shared/AdminGiftRules.luau'),
        ('@@ADMIN_GIFTS@@', 'src/server/AdminGifts.luau'),
        ('@@OLD_CONFIG@@', FIXTURE + 'Config.luau'),
        ('@@OLD_PROGRESSION_CONFIG@@', FIXTURE + 'ProgressionConfig.luau'),
        ('@@OLD_GENETICS@@', FIXTURE + 'EggGenetics.luau'),
        ('@@OLD_RULES@@', FIXTURE + 'ProgressionRules.luau'),
        ('@@OLD_TRAITS@@', FIXTURE + 'EggTraits.luau'),
        ('@@OLD_REWARD_MATH@@', FIXTURE + 'RewardMath.luau'),
        ('@@OLD_REPO@@', FIXTURE + 'ProfileRepository.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        text = text.replace(token, gift_rules_module() if token == '@@GIFT_RULES@@' else module(path))
    return text


def script() -> str:
    prefix = verify_rewards.HARNESS.split('local function user(id)')[0]
    return fill(prefix + '\n' + PURE + '\n' + REPO + '\n' + SERVICE + '\n' + ADMIN + '\n' + OLD)


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
    print('Static checks passed: flags false in source and pinned off in default + playtest, no Robux API, pure rules, flag-first entry points')
    with tempfile.TemporaryDirectory() as directory:
        path = args.dump or Path(directory) / 'gifts.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        print(result.stderr, end='')
        if result.returncode == 0 and 'Gifting core verified' in result.stdout and 'Admin gifts verified' in result.stdout:
            print('Gifting verification passed (BD-451, BD-452).')
            return 0
        return result.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())
