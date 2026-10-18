"""BD-570 gifting player UI (docs/134 s13, docs/72): offline verifier in pinned Luau.

Runs the REAL src/shared/GiftUiModel.luau, src/shared/TouchLayout.luau (giftRect), src/client/SettingsMenu.luau and the source of
src/client/GiftPopup.client.luau, end to end against the REAL src/server/GiftService.luau on the mocked stores of tools/verify_gifts.py.
Covers:
  * flag-off identity: Config.GiftClaimEnabled is false; the popup script returns on its first lines (no Instance, no remote, no module); the Settings
    Controls tab draws exactly the same rows with the flag off, unset, or on without a GiftAction remote, and never loads the gift modules; Bootstrap
    computes and publishes GiftRect only inside the flag; TouchLayout.compute never mentions gifts;
  * the Settings row: three states (Everyone / Friends / Nobody) round-trip through GiftAction (get, setFrom), a failed save is put back, a bad value
    sends nothing, the default is Everyone, a read never writes;
  * the popup: exact copy ("You got a gift from <name>!", "Nice!", "Mute <name>", "Turn gifts off"), no refuse / decline button or request anywhere,
    Mute and Turn gifts off send {action = "mute"} / {action = "turnOff"} and the server does the right thing, one notice at a time and queued,
    team gifts have no Mute, long and multi-byte names are clipped to the room, text >= 14 px, buttons >= 44 px, nothing outside the panel or
    overlapping, Reduce Motion (no bounce), registered icons only (no new art);
  * placement: the popup rectangle (TouchLayout.giftRect) touches no HUD piece on desktop, tablet and the listed phone canvases; on the most crowded
    phone canvases it may cover only the soft pieces (the Back to the middle chip, weather / buffs tiles), never a hard one.

  python tools/verify_gift_ui.py --runner C:/path/to/luau.exe
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
import verify_gifts  # noqa: E402
import verify_rewards  # noqa: E402

MODEL = 'src/shared/GiftUiModel.luau'
POPUP = 'src/client/GiftPopup.client.luau'
SETTINGS = 'src/client/SettingsMenu.luau'
SETTINGS_CLIENT = 'src/client/GiftSettings.luau'
BOOTSTRAP = 'src/client/Bootstrap.client.luau'
LAYOUT = 'src/shared/TouchLayout.luau'
SERVICE = 'src/server/GiftService.luau'
ICONS = 'src/shared/UIIconAssets.luau'


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def strip_comments(text: str) -> str:
    return re.sub(r'--.*$', '', text, flags=re.M)


def static_errors() -> list[str]:
    errors: list[str] = list(verify_gifts.static_errors())  # the three flags are false in source and pinned off in the release profiles
    for path in (MODEL, POPUP, SETTINGS, SETTINGS_CLIENT, BOOTSTRAP, LAYOUT, SERVICE, ICONS):
        if not (ROOT / path).exists():
            errors.append(f'{path} is missing')
    if errors:
        return errors
    popup, model, settings, client = (strip_comments(read(p)) for p in (POPUP, MODEL, SETTINGS, SETTINGS_CLIENT))
    boot, layout, service = read(BOOTSTRAP), read(LAYOUT), strip_comments(read(SERVICE))

    # --- flag-off identity (static half; the dynamic half runs the real popup and Settings sources below)
    gate = 'if (Config :: any).GiftClaimEnabled ~= true then return end'
    if popup.count(gate) != 1:
        errors.append('GiftPopup must return on its flag check exactly once, before anything else')
    else:
        before = popup[:popup.index(gate)]
        for word in ('Instance.new', 'WaitForChild("BeDinoRemotes"', 'GiftUiModel', 'GiftSettings', 'PrivateState', 'UITheme'):
            if word in before:
                errors.append(f'GiftPopup touches {word} before the GiftClaimEnabled check')
    # SettingsMenu: the gift modules are required only inside drawGifts, which is called only behind the flag.
    top = settings[:settings.index('local function drawGifts')]
    for word in ('GiftSettings', 'GiftUiModel'):
        if word in top:
            errors.append(f'SettingsMenu requires {word} at the top of the file (flag off must not load it)')
    if 'Config.GiftClaimEnabled == true and drawGifts(' not in settings:
        errors.append('SettingsMenu must call drawGifts only behind Config.GiftClaimEnabled == true')
    if len(re.findall(r'drawGifts\(', settings)) != 2:
        errors.append('SettingsMenu: drawGifts must be defined once and called once')
    for path, text in ((POPUP, popup), (SETTINGS, settings), (BOOTSTRAP, strip_comments(boot))):
        if path != SETTINGS and path != POPUP and 'GiftSettings' in text:
            errors.append(f'{path} must not use GiftSettings')
    if 'Config.GiftClaimEnabled==true then' not in boot or boot.count('giftRect(') != 1:
        errors.append('Bootstrap must compute the gift rect exactly once, inside Config.GiftClaimEnabled==true')
    else:
        start = boot.index('Config.GiftClaimEnabled==true then')
        block = boot[start:boot.index('end\n', boot.index('GiftVariant', start))]
        if boot.index('giftRect(') < start or 'GiftRect' not in block or 'GiftVariant' not in block:
            errors.append('Bootstrap: giftRect and the GiftRect / GiftVariant attributes must sit inside the flag block')
        if boot.count('"GiftRect"') != 1 or boot.count('"GiftVariant"') != 1:
            errors.append('Bootstrap must publish GiftRect and GiftVariant once each')
    compute = layout[layout.index('function TouchLayout.compute'):layout.index('-- BD-570')]
    if re.search(r'gift', compute, flags=re.I):
        errors.append('TouchLayout.compute must not mention gifts (flag-off layout identity)')
    # GiftSettings: no remote call at load time, only inside invoke().
    if 'WaitForChild("BeDinoRemotes"' in client or re.sub(r'local function invoke.*?\nend\n', '', client, flags=re.S).count('InvokeServer') != 0:
        errors.append('GiftSettings must call the remote only inside invoke() and never block on it')

    # --- no refuse / decline (owner 2026-10-17): the server's actions, the model's buttons and the popup's wording
    shapes = re.search(r'local Shapes[^=]*=\s*\{(.*?)\n\}', service, flags=re.S)
    actions = sorted(re.findall(r'^\s*(\w+)\s*=\s*\{action = true', shapes.group(1), flags=re.M)) if shapes else []
    if actions != ['ack', 'blocked', 'get', 'mute', 'setFrom', 'turnOff']:
        errors.append(f'GiftAction actions must be exactly get, ack, mute, turnOff, setFrom, blocked, found {actions}')
    ids = re.search(r'Model\.ButtonIds = table\.freeze\(\{(.*?)\}\)', model)
    if not ids or re.findall(r'"(\w+)"', ids.group(1)) != ['ack', 'mute', 'turnOff']:
        errors.append('GiftUiModel.ButtonIds must be exactly ack, mute, turnOff')
    for path, text in ((POPUP, popup), (MODEL, model), (SETTINGS, settings), (SETTINGS_CLIENT, client)):
        for word in ('refuse', 'decline', 'reject', 'deny', 'no thanks', 'return gift', 'send back'):
            if word in text.lower():
                errors.append(f'{path} mentions "{word}": there is no per-gift refuse (owner 2026-10-17)')

    # --- no new art, no code-drawn art: a registered icon via Theme.icon, UITheme plates (Theme.decorate)
    if re.search(r'rbxassetid|ImageLabel|ImageButton|\.Image\b', popup + model):
        errors.append('the gift popup must not bring its own images or asset ids (existing registered icons only, docs/77)')
    if 'Theme.icon(panel, Model.iconFor(current))' not in popup or 'Theme.decorate(panel,' not in popup or 'Theme.decorate(b,' not in popup:
        errors.append('the popup must use Theme.icon for its icon and Theme.decorate for its plates')
    registered = set(re.findall(r'^\s+(\w+) = "rbxassetid://\d+"', read(ICONS), flags=re.M))
    icon_fn = re.search(r'function Model\.iconFor.*?\nend', model, flags=re.S)
    icons = re.findall(r'"(\w+)"', icon_fn.group(0)) if icon_fn else []
    if sorted(set(icons) - {'crystals'}) != ['amber', 'dinos']:
        errors.append(f'GiftUiModel.iconFor must return exactly the registered icons amber and dinos, found {icons}')
    for icon in ('amber', 'dinos'):
        if icon not in registered:
            errors.append(f'icon {icon!r} is not a registered UI icon in {ICONS}')
    # --- Reduce Motion: the Back (bounce) easing is only ever reached when Theme.MotionEnabled, and the else branch is flat
    bounces = [m.start() for m in re.finditer(r'EasingStyle\.Back', popup)]
    guard = popup.find('if Theme.MotionEnabled then')
    if len(bounces) != 1 or guard < 0 or not (guard < bounces[0] < popup.index('else', guard)) or 'pop.Scale = 1' not in popup:
        errors.append('the popup bounce must sit inside `if Theme.MotionEnabled then` with a flat else branch')
    if 'TweenService' in popup or 'Spring' in popup:
        errors.append('the popup must animate only through Theme.animate (which honours Reduce Motion)')
    # --- one popup at a time, shown only in the hub and never over a menu
    if 'player:GetAttribute("Location") ~= "Island"' not in popup or 'not menuOpen' not in popup:
        errors.append('the popup must stay hidden during a run and behind an open menu')
    if popup.count('Instance.new("ScreenGui")') != 1 or popup.count('Instance.new("Frame")') != 1:
        errors.append('the popup must have exactly one ScreenGui and one panel (one popup at a time)')
    # --- CI runs this verifier
    workflow = (ROOT / '.github/workflows/build-generated-place.yml').read_text(encoding='utf-8')
    if 'verify_gift_ui.py' not in workflow:
        errors.append('.github/workflows/build-generated-place.yml must run tools/verify_gift_ui.py')
    return errors


def module(path: str) -> str:
    return '(function()\n' + read(path) + '\nend)()'


UI = r'''
------------------------------------------------------------------ (D) gifting player UI (BD-570)
local Model=@@GIFT_UI_MODEL@@
local PhoneScale=@@PHONE_SCALE@@
local TouchLayout
do
 local script={Parent={Config="Config",PhoneScale="PhoneScale"}}
 local require=function(name) if name=="PhoneScale" then return PhoneScale end return GameConfig end
 TouchLayout=@@TOUCH_LAYOUT@@
end
local ui=0
local function ok(cond,msg) ui+=1 if not cond then error("FAIL: "..tostring(msg),2) end end
local function reqText(r) local keys={} for k,v in r do table.insert(keys,k.."="..tostring(v)) end table.sort(keys) return table.concat(keys,",") end
GameConfig.GiftClaimEnabled=true GameConfig.GiftingEnabled=true GameConfig.AdminGiftsEnabled=true

------------------------------------------------------------------ constants and copy (docs/72: short, plain, children)
do
 ok(Model.RowLabel=="Gifts from" and table.concat(Model.Options,",")=="everyone,friends,nobody" and Model.Default=="everyone" and GiftRules.DefaultSetting==Model.Default,"row label, three options, default Everyone")
 for _,id in Model.Options do ok(GiftRules.Settings[id]==true and Model.OptionLabels[id]==string.upper(id),"option "..id.." is a real setting with an upper-case label") end
 ok(Model.normalizeSetting("friends")=="friends" and Model.normalizeSetting("anyone")=="everyone" and Model.normalizeSetting(nil)=="everyone" and Model.normalizeSetting(5)=="everyone","an unknown saved value reads as Everyone")
 ok(Model.Copy.ack=="Nice!" and Model.Copy.turnOff=="Turn gifts off","button copy")
 local FORBIDDEN={"refuse","decline","reject","deny","no thanks","block","report","error","fail","invalid","%d","%%","x%d"}
 for key,text in Model.Copy do
  ok((#text>=3 or key=="titleSuffix") and #text<=40,"short copy: "..key)
  for _,bad in FORBIDDEN do ok(string.find(string.lower(text),bad)==nil,"copy "..key.." has no jargon / numbers / refusal: "..bad) end
 end
 ok(Model.MinText==14 and Model.MinButton==44 and Model.MinText==PhoneScale.MinText and Model.MinButton==PhoneScale.MinButton,"floors equal PhoneScale (docs/72)")
 ok(Model.clip("Sam",8)=="Sam" and Model.clip("Samantha Display",8)=="Samanth…" and utf8.len(Model.clip("Samantha Display",8))==8,"clip keeps the room")
 ok(Model.clip("Ünï😀cødé-fan",6)=="Ünï😀c…" and utf8.len(Model.clip("Ünï😀cødé-fan",6))==6,"clip never cuts a multi-byte character")
 ok(Model.clip("\xff\xfe",5)==Model.Copy.fallbackName,"invalid UTF-8 shows the fallback name")
 ok(Model.parseNotice(nil)==nil and Model.parseNotice({})==nil and Model.parseNotice({line=5,id="x"})==nil and Model.parseNotice({line="",id="x"})==nil and Model.parseNotice({line=string.rep("x",300),id="x"})==nil,"a malformed payload shows nothing")
end

------------------------------------------------------------------ requests: exact shapes, accepted by the real GiftAction
do
 local S,W,rs=server()
 local R=9100
 local u=user(R) assert(Repository.load(u))
 local sent={}
 local function invoke(req) table.insert(sent,reqText(req)) return S.handle(u,req) end
 local c=Model.controller(invoke)
 ok(c.current()=="everyone" and not c.loaded(),"before the first read the row shows Everyone")
 ok(c.refresh()==false and c.loaded() and c.current()=="everyone" and giftsData.pref_9100==nil,"first read: Everyone (nothing saved), unchanged, and a read writes nothing")
 -- the three states round-trip through the server and back through a fresh controller
 for _,state in {"friends","nobody","everyone","nobody","friends"} do
  NOW+=S.ActionWindowSeconds+1
  local before=#sent
  ok(c.choose(state) and c.current()==state and giftsData.pref_9100.from==state,"choose "..state.." is saved on the server")
  ok(#sent==before+1 and sent[#sent]=="action=setFrom,from="..state,"choose "..state.." sends exactly one setFrom: "..tostring(sent[#sent]))
  local again=Model.controller(invoke)
  ok(again.refresh()==(state~="everyone") and again.current()==state,"a fresh controller reads "..state.." back")
 end
 -- bad values send nothing; a failed save is put back
 NOW+=S.ActionWindowSeconds+1
 local n=#sent
 for _,bad in {"anyone","",5,{},false} do ok(c.choose(bad)==false and c.current()=="friends","a bad value changes nothing: "..tostring(bad)) end
 ok(#sent==n,"a bad value sends no request")
 g.outage=true
 ok(c.choose("nobody")==false and c.current()=="friends" and giftsData.pref_9100.from=="friends","a failed save puts the row back")
 g.outage=false
 ok(Model.setFromRequest("nobody").from=="nobody" and Model.setFromRequest("x")==nil and Model.setFromRequest(nil)==nil,"setFromRequest only builds the three settings")
 -- request tables are fresh copies
 local r1=Model.request("mute") r1.action="hacked"
 ok(Model.request("mute").action=="mute","requests are copies")
 Repository.release(u)
end

------------------------------------------------------------------ the popup end to end: queue, Mute, Turn gifts off, no refuse
do
 local S=server()
 local R,SENDER1,SENDER2=9110,1100,1101
 local R3=9112
 local u=user(R) assert(Repository.load(u))
 S.send({source="robux",giftId="Rui-1",from=SENDER1,to=R,item="skin_plush",msg="have_fun"})
 S.send({source="robux",giftId="Rui-3",from=SENDER2,to=R,item="skin_clay",msg="enjoy"})
 S.send({source="robux",giftId="Rui-5",from=1102,to=R,item="skin_bricks"})
 S.claim(u)
 local sent={}
 local function invoke(req) table.insert(sent,reqText(req)) return S.handle(u,req) end
 local c=Model.controller(invoke)
 local function current() return Model.parseNotice(noticeOf(u)) end
 -- the three notices are queued; exactly one is announced at a time
 local seen={}
 local first=current()
 ok(first~=nil,"a notice is on screen")
 ok(first.name=="Samantha Display" and first.canMute and first.kind=="skin" and first.item=="Plushy skin" and first.message=="Have fun!" and not first.converted,"payload fields (name, item, message, kind)")
 ok(table.concat(Model.buttonsFor(first),",")=="ack,mute,turnOff","a gift from a player has Nice!, Mute and Turn gifts off")
 for _,variant in Model.Variants do
  local layout=Model.layout(variant.name,true)
  ok(Model.buttonText("ack",first,layout)=="Nice!" and Model.buttonText("turnOff",first,layout)=="Turn gifts off","button copy in "..variant.name)
  local mute=Model.buttonText("mute",first,layout)
  ok(string.sub(mute,1,5)=="Mute " and #mute>5,"Mute <name> in "..variant.name..": "..mute)
  local title=Model.title(first,layout)
  ok(string.sub(title,1,20)=="You got a gift from " and string.sub(title,-1)=="!","title in "..variant.name..": "..title)
 end
 local roomy=Model.layout("roomy",true)
 ok(Model.title({name="Sam",line="x",id="i",item="",message="",kind="skin",canMute=true,converted=false},roomy)=="You got a gift from Sam!","title copy for a short name")
 ok(Model.buttonText("mute",{name="Sam",line="x",id="i",item="",message="",kind="skin",canMute=true,converted=false},roomy)=="Mute Sam","Mute <name> copy for a short name")
 ok(Model.detail(first)=="Plushy skin - Have fun!","detail = item - preset message")
 ok(Model.iconFor(first)=="dinos" and Model.iconFor({kind="crystals"})=="amber","icons: dinos for a skin, amber for crystals")
 -- Mute: the server mutes the sender of the notice on screen and brings the next one
 local before=#sent
 ok(c.press("mute") and sent[#sent]=="action=mute" and #sent==before+1,"Mute sends exactly {action = mute}")
 ok(giftsData.pref_9110 and giftsData.pref_9110.muted[1]==SENDER1 and giftsData.pref_9110.from~="nobody","the sender is muted, the setting is untouched")
 local second=current()
 ok(second~=nil and second.id~=first.id,"the next queued notice comes up after Mute (one at a time)")
 -- Nice!: closes this notice, shows the next
 ok(c.press("ack") and sent[#sent]=="action=ack","Nice! sends exactly {action = ack}")
 local third=current()
 ok(third~=nil and third.id~=second.id and third.name=="Samantha Display" and third.item=="Bricks skin","the third notice comes up after Nice!")
 -- a team gift: no Mute
 local u3=user(R3) assert(Repository.load(u3))
 S.send({source="admin",from=100,to=R3,item="crystals_custom",crystals=40,msg="great_job"})
 S.claim(u3)
 local team=Model.parseNotice(noticeOf(u3))
 ok(team~=nil and team.name=="" and team.canMute==false and team.kind=="crystals" and team.line=="A gift from the Be Dino team!","a team gift has no name")
 ok(table.concat(Model.buttonsFor(team),",")=="ack,turnOff","a team gift has no Mute button")
 for _,variant in Model.Variants do
  local layout=Model.layout(variant.name,false)
  ok(layout.buttons.mute==nil and #layout.order==2 and Model.title(team,layout)==team.line,"no Mute in "..variant.name.." for a team gift")
 end
 Repository.release(u3)
 -- Turn gifts off: setting becomes Nobody and the popup closes; the Settings row reads it back
 ok(c.press("turnOff") and sent[#sent]=="action=turnOff" and giftsData.pref_9110.from=="nobody" and noticeOf(u)=="","Turn gifts off sends exactly {action = turnOff}: Nobody, popup closed")
 ok(c.current()=="nobody","the shared controller (and so the Settings row) shows Nobody at once")
 NOW+=S.ActionWindowSeconds+1
 ok(Model.controller(invoke).refresh() and giftsData.pref_9110.from=="nobody","a fresh read of the row says Nobody")
 -- there is no refuse: nothing but the three popup ids is ever sent
 local count=#sent
 for _,bad in {"refuse","decline","reject","no","get","setFrom","blocked","","ACK",5,{},false} do
  ok(c.press(bad)==false,"press("..tostring(bad)..") is refused by the controller")
 end
 ok(c.press(nil)==false and #sent==count,"no refuse / decline / unknown request is ever sent")
 ok(Model.request("refuse")==nil and Model.request("decline")==nil and Model.request("get").action=="get","only known requests exist")
 for _,id in Model.ButtonIds do ok(Model.request(id)~=nil and Model.request(id).action==id,"button id "..id.." maps to its own action") end
 -- the real server accepts exactly these shapes and nothing else for the popup
 NOW+=S.ActionWindowSeconds+1
 for _,probe in {{action="refuse"},{action="decline"},{action="reject"}} do ok(S.handle(u,probe).ok==false,"the server has no "..probe.action.." action") end
 -- converted gift (the player already owned the skin)
 local R2=9111
 local u2=user(R2) assert(Repository.load(u2)) Repository.release(u2)
 data[key(u2)].ownedSkins={Plush=true}
 assert(Repository.load(u2))
 S.send({source="robux",giftId="Rui-4",from=SENDER1,to=R2,item="skin_plush",msg="thank_you"})
 S.claim(u2)
 local conv=Model.parseNotice(noticeOf(u2))
 ok(conv and conv.converted and Model.detail(conv)=="You had it: crystals!","converted gift copy: "..tostring(conv and Model.detail(conv)))
 Repository.release(u) Repository.release(u2)
end

------------------------------------------------------------------ sizes: text >= 14, buttons >= 44, nothing outside, nothing overlapping, names fit
do
 local NAMES={"Sam","Samantha Display","Maximilian the Dinosaur Fan 2012","Ünï😀cødé-fan","WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW","Mia"}
 local function inside(b,w,h) return b.x>=0 and b.y>=0 and b.x+b.w<=w and b.y+b.h<=h end
 local function hits(a,b) return a.x<b.x+b.w and b.x<a.x+a.w and a.y<b.y+b.h and b.y<a.y+a.h end
 local function width(text,size) return utf8.len(text)*size*Model.GlyphWidth end
 ok(#Model.Variants==#TouchLayout.GIFT,"TouchLayout.GIFT lists every variant")
 for i,variant in Model.Variants do
  local t=TouchLayout.GIFT[i]
  ok(t.name==variant.name and t.w==variant.w and t.h==variant.h,"TouchLayout.GIFT and GiftUiModel agree on "..variant.name)
  if i>1 then ok(variant.w<=Model.Variants[i-1].w and variant.h<=Model.Variants[i-1].h+60,"variants shrink: "..variant.name) end
  for _,canMute in {true,false} do
   local L=Model.layout(variant.name,canMute)
   ok(L.w==variant.w and L.h==variant.h and L.variant==variant.name,"layout size "..variant.name)
   local boxes={}
   local label=variant.name.." mute="..tostring(canMute)
   ok(inside(L.icon,L.w,L.h) and inside(L.title,L.w,L.h) and inside(L.detail,L.w,L.h),label..": icon and text inside the panel")
   ok(L.title.size>=Model.MinText and L.detail.size>=Model.MinText and L.title.h>=L.title.size and L.detail.h>=L.detail.size,label..": text >= 14 px and its box holds a line")
   ok(L.icon.h>=Model.IconSize and not hits(L.icon,L.title) and not hits(L.icon,L.detail),label..": the icon does not cover the text")
   ok(not hits(L.title,L.detail),label..": title and detail do not overlap")
   for _,id in L.order do
    local b=L.buttons[id]
    ok(b.h>=Model.MinButton and b.w>=Model.MinButton and b.size>=Model.MinText,label..": button "..id.." >= 44 px and text >= 14 px")
    ok(inside(b,L.w,L.h),label..": button "..id.." inside the panel")
    ok(not hits(b,L.title) and not hits(b,L.detail) and not hits(b,L.icon),label..": button "..id.." clear of the text and icon")
    for _,other in boxes do ok(not hits(b,other.b),label..": buttons "..id.." and "..other.id.." do not overlap") end
    table.insert(boxes,{id=id,b=b})
   end
   for _,name in NAMES do
    local notice={id="i",line="You got a gift from "..name.."!",name=name,item="Plushy skin",message="Have fun!",kind="skin",canMute=canMute,converted=false}
    local title=Model.title(notice,L)
    ok(width(title,L.title.size)<=L.title.w,label..": the title fits for "..name..": "..title)
    for _,id in L.order do
     local text=Model.buttonText(id,notice,L)
     ok(width(text,L.buttons[id].size)+Model.ButtonPad<=L.buttons[id].w,label..": button text fits for "..name..": "..text)
    end
   end
   local detail={id="i",line="x",name="Sam",item="Clay skin",message="You're welcome!",kind="skin",canMute=canMute,converted=false}
   ok(width(Model.detail(detail),L.detail.size)<=L.detail.w,label..": the longest detail fits: "..Model.detail(detail))
   detail.converted=true
   ok(width(Model.detail(detail),L.detail.size)<=L.detail.w,label..": the converted detail fits: "..Model.detail(detail))
  end
 end
 -- every preset message fits the narrowest row variant with the longest skin name
 for _,preset in GiftRules.Presets do
  local L=Model.layout("tight",true)
  local text="Balloon skin - "..preset.text
  ok(width(text,L.detail.size)<=L.detail.w,"preset fits the narrow detail line: "..text)
 end
end

------------------------------------------------------------------ flag-off identity: the real GiftPopup source returns on its first lines
local function popupRun(flag)
 local log={instances=0,requires={},waits={},services={},spawned=0,remote=0}
 local shared={WaitForChild=function(_,name) table.insert(log.waits,name) return name end}
 local rs={WaitForChild=function(_,name) table.insert(log.waits,name) if name=="Shared" then return shared end log.remote+=1 return nil end}
 local game={GetService=function(_,name) table.insert(log.services,name) if name=="ReplicatedStorage" then return rs end return {} end}
 local Instance={new=function() log.instances+=1 return {} end}
 local script={Parent={WaitForChild=function(_,name) table.insert(log.waits,name) return name end}}
 local require=function(id) table.insert(log.requires,tostring(id)) if id=="Config" then return {GiftClaimEnabled=flag} end return {} end
 local task={spawn=function() log.spawned+=1 end,wait=function() end}
 local result=@@POPUP@@
 return log
end
do
 for i,log in {popupRun(false),popupRun(nil)} do
  ok(log.instances==0 and log.remote==0 and log.spawned==0 and #log.requires==1 and log.requires[1]=="Config","flag off/unset ("..i.."): the popup builds no UI, waits for no remote, requires only Config")
  ok(table.concat(log.waits,",")=="Shared,Config","flag off/unset ("..i.."): the popup waits for nothing but Shared and Config: "..table.concat(log.waits,","))
 end
 local on=popupRun(true)
 ok(on.instances>0 or #on.requires>1 or #on.waits>2,"probe: with the flag ON the same harness sees the popup start up (so the flag-off result means something)")
end
print("Gift UI flag-off identity (popup source) passed: no Instance, no remote, no module beyond Config")

------------------------------------------------------------------ the Settings row, drawn by the real SettingsMenu source
local function settingsRun(cfg,gifts)
 local log={requires={},giftCalls=0}
 local shared={WaitForChild=function(_,name) return name end}
 local rs={WaitForChild=function(_,name) return shared end}
 local game={GetService=function(_,name) if name=="ReplicatedStorage" then return rs elseif name=="UserInputService" then return {TouchEnabled=false} end error("service "..name) end}
 local script={Parent={WaitForChild=function(_,name) return name end}}
 local colors={accent="accent",card="card",blue="blue",purple="purple",gold="gold",text="text"}
 local SettingsModel=@@SETTINGS_MODEL@@
 local require=function(id)
  table.insert(log.requires,tostring(id))
  if id=="UITheme" then return {Colors=colors,HatchSoundEnabled=true}
  elseif id=="SettingsModel" then return SettingsModel
  elseif id=="AudioMixer" then return {Order={},get=function() return 0 end,reset=function() end}
  elseif id=="Config" then return cfg
  elseif id=="FtueP1" then return {controlsLines=function() return {"line one","line two"} end}
  elseif id=="GiftSettings" then return gifts
  elseif id=="GiftUiModel" then return Model end
  error("unexpected module "..tostring(id))
 end
 local task={spawn=function(f,...) f(...) end}
 local Enum=setmetatable({},{__index=function(_,group) return setmetatable({},{__index=function(_,item) return group.."."..item end}) end})
 local Menu=@@SETTINGS_MENU@@
 local rec={labels={},buttons={},opens={}}
 local ctx={}
 function ctx.label(_,text,x,y,w,h,size) local o={Text=text,x=x,y=y,w=w,h=h,size=size} table.insert(rec.labels,o) return o end
 function ctx.button(_,text,x,y,w,h,color,cb) local o={Text=text,x=x,y=y,w=w,h=h,color=color,cb=cb} table.insert(rec.buttons,o) return o end
 function ctx.open(id) table.insert(rec.opens,id) end
 function ctx.notify() end
 function ctx.cameraReset() end
 Menu.setTab("controls")
 local function draw()
  rec.labels,rec.buttons={}, {}
  Menu.build({},ctx)
 end
 draw()
 return log,rec,draw
end
local function rowsOf(rec)
 local out={}
 for _,b in rec.buttons do table.insert(out,string.format("%s@%d,%d,%d,%d",b.Text,b.x,b.y,b.w,b.h)) end
 for _,l in rec.labels do table.insert(out,string.format("%s@%d,%d",l.Text,l.x,l.y)) end
 return table.concat(out,"|")
end
do
 local calls=0
 local function counting(available)
  return {available=function() calls+=1 return available end,controller=function() calls+=1 error("no controller when the row is hidden") end,
   refresh=function() calls+=1 end,rowShowing=function() calls+=1 return true end}
 end
 for _,hub in {true,false} do
  local base={CaveHub=hub,FastTravelPerk=false,CombatEnabled=false}
  local offCfg=table.clone(base) offCfg.GiftClaimEnabled=false
  local unsetCfg=table.clone(base)
  local onCfg=table.clone(base) onCfg.GiftClaimEnabled=true
  calls=0
  local logOff,recOff=settingsRun(offCfg,counting(true))
  local logUnset,recUnset=settingsRun(unsetCfg,counting(true))
  ok(calls==0,"flag off or unset: the Settings tab never touches the gift modules ("..calls.." calls)")
  ok(rowsOf(recOff)==rowsOf(recUnset),"flag off and unset draw the same Controls tab")
  for _,id in logOff.requires do ok(id~="GiftSettings" and id~="GiftUiModel","flag off: "..id.." is not loaded") end
  for _,b in recOff.buttons do ok(not string.find(b.Text,"EVERYONE") and not string.find(b.Text,"FRIENDS") and not string.find(b.Text,"NOBODY"),"flag off: no gift row button") end
  for _,l in recOff.labels do ok(l.Text~="Gifts from","flag off: no gift row label") end
  -- flag on but this server has no GiftAction remote: the row stays hidden and the tab is unchanged
  calls=0
  local logNoRemote,recNoRemote=settingsRun(onCfg,counting(false))
  ok(calls==1 and rowsOf(recNoRemote)==rowsOf(recOff),"flag on, no remote: only available() is asked once, the tab is unchanged")
 end
end
do
 local S=server()
 local R=9120
 local u=user(R) assert(Repository.load(u))
 local sent={}
 local function invoke(req) table.insert(sent,reqText(req)) return S.handle(u,req) end
 local controller=Model.controller(invoke)
 local opens=0
 local gifts={available=function() return true end,controller=function() return controller end,
  refresh=function(changed) if not controller.loaded() then if controller.refresh() then changed() end end end,rowShowing=function() return true end}
 local cfgOn={CaveHub=true,FastTravelPerk=false,CombatEnabled=false,GiftClaimEnabled=true}
 local cfgOff={CaveHub=true,FastTravelPerk=false,CombatEnabled=false,GiftClaimEnabled=false}
 local _,recOff=settingsRun(cfgOff,gifts)
 S.setFrom(R,"friends") -- saved earlier (another session): the row must show it after the first read
 NOW+=S.ActionWindowSeconds+1
 local log,rec,draw=settingsRun(cfgOn,gifts)
 local names={}
 for _,b in rec.buttons do if string.find(b.Text,"^[A-Z]+$") and (b.Text=="EVERYONE" or b.Text=="FRIENDS" or b.Text=="NOBODY") then table.insert(names,b) end end
 ok(#names==3 and names[1].Text=="EVERYONE" and names[2].Text=="FRIENDS" and names[3].Text=="NOBODY","the row has Everyone, Friends and Nobody in that order")
 ok(names[1].y==names[2].y and names[2].y==names[3].y and names[1].x<names[2].x and names[2].x<names[3].x and names[3].x+names[3].w<=824,"the three choices sit in one row inside the 824 px body")
 for _,b in names do ok(b.h>=48 and b.w>=100,"row buttons are big enough (>= 48 px high)") end
 local gl=nil for _,l in rec.labels do if l.Text=="Gifts from" then gl=l end end
 ok(gl~=nil and gl.y==names[1].y and gl.size>=14,"the row label is 'Gifts from' on the same line")
 ok(names[1].y==64+3*56,"the row is the next row after Fast travel (row 3)")
 -- the lines under the rows moved down one row; nothing else changed
 local function line(r,n) for _,l in r.labels do if l.Text==n then return l end end end
 ok(line(rec,"line one").y==line(recOff,"line one").y+56 and line(rec,"line two").y==line(recOff,"line two").y+56,"the control lines under the rows move down one row")
 ok(#rec.buttons==#recOff.buttons+3,"exactly the three row buttons are added")
 -- the first read found Friends: the menu asked for one redraw and now shows it
 ok(#rec.opens==1 and rec.opens[1]=="settings" and controller.current()=="friends" and sent[1]=="action=get","the saved value (Friends) is read through get and the menu redraws once")
 draw()
 local sel
 for _,b in rec.buttons do if b.color=="accent" and (b.Text=="EVERYONE" or b.Text=="FRIENDS" or b.Text=="NOBODY") then sel=b.Text end end
 ok(sel=="FRIENDS" and #rec.opens==1 and #sent==1,"the saved choice is highlighted, no second read")
 -- tapping Nobody saves it through setFrom and redraws
 NOW+=S.ActionWindowSeconds+1
 local nobody for _,b in rec.buttons do if b.Text=="NOBODY" then nobody=b end end
 nobody.cb()
 ok(giftsData.pref_9120.from=="nobody" and sent[#sent]=="action=setFrom,from=nobody" and rec.opens[#rec.opens]=="settings","tapping Nobody saves it with {action = setFrom, from = nobody}")
 draw()
 sel=nil for _,b in rec.buttons do if b.color=="accent" and (b.Text=="EVERYONE" or b.Text=="FRIENDS" or b.Text=="NOBODY") then sel=b.Text end end
 ok(sel=="NOBODY","the row now shows Nobody")
 local everyone for _,b in rec.buttons do if b.Text=="EVERYONE" then everyone=b end end
 everyone.cb()
 ok(giftsData.pref_9120.from=="everyone","tapping Everyone saves it")
 -- a failed save is put back and the menu redraws
 local opensBefore=#rec.opens
 local friends for _,b in rec.buttons do if b.Text=="FRIENDS" then friends=b end end
 g.outage=true NOW+=S.ActionWindowSeconds+1 friends.cb() g.outage=false
 ok(controller.current()=="everyone" and giftsData.pref_9120.from=="everyone" and #rec.opens>=opensBefore+2,"a failed save puts the row back and redraws it")
 Repository.release(u)
end
print("Gift UI Settings row passed: hidden with the flag off or without the remote; Everyone/Friends/Nobody round-trip through GiftAction; failed saves revert")

------------------------------------------------------------------ placement: the popup rectangle never covers a HUD piece
local function pieces(layout)
 local list={}
 local function add(name,r,soft) if r and r.w>0 and r.h>0 then table.insert(list,{name=name,r=r,soft=soft==true}) end end
 local t=layout.timers
 add("leap",{x=t.x,y=t.y+t.leapY*t.scale,w=t.w*t.scale,h=TouchLayout.LEAP_H*t.scale})
 if t.weatherVisible then add("weather",{x=t.x,y=t.y+t.weatherY*t.scale,w=t.w*t.scale,h=TouchLayout.WEATHER_H*t.scale},true) end
 if t.buffsVisible then add("buffs",{x=t.x,y=t.y+t.buffsY*t.scale,w=t.w*t.scale,h=t.buffsH*t.scale},true) end
 add("hud",TouchLayout.rendered(layout.hud))
 add("crystal",TouchLayout.rendered(layout.crystal))
 add("goalline",{x=layout.crystal.x,y=layout.crystal.y+layout.crystal.h*layout.crystal.scale+TouchLayout.GOAL_GAP,w=layout.crystal.w*layout.crystal.scale,h=TouchLayout.GOAL_H*layout.crystal.scale})
 add("action",TouchLayout.rendered(layout.action))
 add("badge",TouchLayout.rendered(layout.badge))
 add("notice",TouchLayout.rendered(layout.notice))
 add("feedback",layout.feedback)
 add("admin",layout.admin)
 add("chip",layout.chip,true)
 add("rail",TouchLayout.rendered(layout.rail))
 for i,p in layout.rail.positions do
  add("nav"..i,{x=layout.rail.x+p.x*layout.rail.scale,y=layout.rail.y+p.y*layout.rail.scale,w=layout.rail.button.w*layout.rail.scale,h=layout.rail.button.h*layout.rail.scale})
 end
 add("goals",layout.goals)
 if not layout.touch then local _,open=TouchLayout.goalsDesktop(layout.crystal) add("goalspanel",open) end
 add("objectives",layout.objectives)
 return list
end
local summary={strict=0,soft=0,desktop=0,zones=0}
local function placement(width,height,touch,objectives,expect)
 local layout=TouchLayout.compute({width=width,height=height,touch=touch,navCount=7,goals=true,objectives=objectives})
 ok(layout.gift==nil,"TouchLayout.compute adds no gift key")
 local g=TouchLayout.giftRect(layout,width,height)
 local label=string.format("%dx%d %s%s",width,height,if touch then "touch" else "mouse",if objectives then " +objectives" else "")
 ok(g.clear,label..": a free rectangle exists ("..g.variant..")")
 ok(g.x>=0 and g.y>=0 and g.x+g.w<=width and g.y+g.h<=height,label..": the popup is on the canvas")
 local v for _,variant in Model.Variants do if variant.name==g.variant then v=variant end end
 ok(v and g.w==v.w and g.h==v.h,label..": the rectangle is exactly the variant size (real pixels, never scaled)")
 local soft={}
 for _,p in pieces(layout) do
  if TouchLayout.overlaps(g,p.r) then
   if p.soft and g.covers==1 then soft[p.name]=true else error("FAIL: "..label..": the popup ("..g.variant..") overlaps "..p.name.." (covers="..g.covers..")") end
  end
 end
 if expect=="strict" then ok(g.covers==0 and next(soft)==nil,label..": no HUD piece at all is covered (variant "..g.variant..")") end
 if g.covers==1 then summary.soft+=1 else summary.strict+=1 end
 if not layout.touch or not g.overZones then summary.desktop+=1 end
 if g.overZones then summary.zones+=1 end
 if not touch and height>=500 then ok(not g.overZones,label..": a desktop canvas has no Roblox control zones") end
 local gap=TouchLayout.GIFT_GAP
 if g.covers==0 then
  for _,p in pieces(layout) do
   ok(g.x>=p.r.x+p.r.w+gap-1e-6 or p.r.x>=g.x+g.w+gap-1e-6 or g.y>=p.r.y+p.r.h+gap-1e-6 or p.r.y>=g.y+g.h+gap-1e-6,label..": "..p.name.." keeps a gap of "..gap.." px")
  end
 end
 return g,layout
end
do
 for _,v in {{1280,720},{1366,768},{1920,1080},{1024,768},{1156,841},{800,600},{2400,1080},{1280,800},{1366,1024}} do
  for _,touch in {false,true} do
   for _,obj in {false,true} do placement(v[1],v[2],touch,obj,"strict") end
  end
 end
 -- phone canvases: the listed landscape phones (and the BD-531 ones minus the Roblox top bar) with the hub Goals header on screen
 for _,v in {{800,360},{667,375},{836,332},{732,412},{844,390},{760,360},{915,412}} do
  for _,touch in {true,false} do placement(v[1],v[2],touch,false,"strict") end
  placement(v[1],v[2],true,true,"any")
 end
 -- the most crowded phone canvases: only soft pieces (chip, weather, buffs) may be covered, never a hard one
 for _,v in {{640,360},{667,317},{667,332},{800,302}} do
  for _,obj in {false,true} do placement(v[1],v[2],true,obj,"any") end
 end
 ok(summary.strict>=50 and summary.soft>=1,"placement summary: "..summary.strict.." strict, "..summary.soft.." soft-cover")
 -- sensitivity: a naive centred popup DOES cover HUD pieces on a phone, so the checks above can fail
 local layout=TouchLayout.compute({width=667,height=375,touch=true,navCount=7,goals=true})
 local naive={x=(667-420)/2,y=(375-104)/2,w=420,h=104}
 local covered=false
 for _,p in pieces(layout) do if TouchLayout.overlaps(naive,p.r) then covered=true end end
 ok(covered,"probe: a centred 420 x 104 popup covers a HUD piece at 667 x 375")
 -- giftRect does not move when the layout is the same (deterministic)
 local a=TouchLayout.giftRect(layout,667,375) local b=TouchLayout.giftRect(layout,667,375)
 ok(a.x==b.x and a.y==b.y and a.variant==b.variant,"giftRect is deterministic")
end
print(string.format("Gift UI placement passed: %d canvases clear of every HUD piece, %d crowded phone canvases cover only soft pieces; %d spots overlap Roblox thumbstick/jump zones",summary.strict,summary.soft,summary.zones))
print("Gift UI verified: "..ui.." checks")
'''


def script() -> str:
    prefix = verify_rewards.HARNESS.split('local function user(id)')[0]
    base = verify_gifts.rehearsal_pins(verify_gifts.fill(prefix + '\n' + verify_gifts.PURE + '\n' + verify_gifts.REPO + '\n' + verify_gifts.SERVICE))
    ui = (UI.replace('@@GIFT_UI_MODEL@@', module(MODEL))
          .replace('@@PHONE_SCALE@@', module('src/shared/PhoneScale.luau'))
          .replace('@@TOUCH_LAYOUT@@', module(LAYOUT))
          .replace('@@POPUP@@', module(POPUP))
          .replace('@@SETTINGS_MODEL@@', module('src/shared/SettingsModel.luau'))
          .replace('@@SETTINGS_MENU@@', module(SETTINGS)))
    return base + '\n' + ui


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
    print('Static checks passed: flag-first popup and Settings row, gift rect only behind the flag, no refuse action or word, no new art, Reduce Motion guard, CI hook')
    with tempfile.TemporaryDirectory() as directory:
        path = args.dump or Path(directory) / 'gift_ui.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        out = result.stdout
        # The shared sections print their own lines; show only the new UI ones plus failures.
        for line in out.splitlines():
            if line.startswith('Gift UI') or line.startswith('FAIL'):
                print(line)
        print(result.stderr, end='')
        if result.returncode == 0 and 'Gift UI verified' in out:
            print('Gift UI verification passed (BD-570).')
            return 0
        return result.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())
