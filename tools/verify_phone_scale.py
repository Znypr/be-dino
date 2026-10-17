"""BD-333/BD-334 offline check of the phone scale policy (Shared/PhoneScale) and the compact HUD (Shared/TouchLayout).

Runs the real modules in Luau for the viewports 1445x841, 1080x720, 844x390, 740x360, 667x375 (each also with a Roblox top bar
and safe insets taken off, which is what the ScreenGui AbsoluteSize really is):
  * desktop sizes keep the old one-canvas formula min(1,(w-40)/860,(h-40)/520) exactly (proof desktop is unchanged),
  * compact sizes use a scale >= 0.8, the panel fits the screen, and any design text/button is floored to 14 px / 44 px,
  * HUD pieces (Leap, weather timer, speed line) get a design text size that renders >= 14 px and 44 px touch buttons.
Not Studio evidence: see docs/evidence/2026-10-16-phone-ui-scale.
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local P=PhoneScale
local function oldRule(w,h) return math.max(.05,math.min(1,(w-40)/860,(h-40)/520)) end
local sizes={{1445,841},{1080,720},{844,390},{740,360},{667,375}}
local seen={}
for _,s in sizes do
    for _,inset in {0,36} do -- raw window and window minus the Roblox top bar
        local w,h=s[1],s[2]-inset
        local m=P.modal(w,h)
        seen[#seen+1]=string.format("%dx%d gui %dx%d -> %s scale %.3f panel %dx%d",s[1],s[2],w,h,m.mode,m.scale,m.panelW,m.panelH)
        assert(m.minText==14 and m.minButton==44)
        assert(m.panelW*m.scale<=w+1e-6 and m.panelH*m.scale<=h+1e-6,"panel fits the screen "..w.."x"..h)
        if h>=500 then
            assert(m.mode=="desktop" and m.scale==oldRule(w,h) and m.panelW==860 and m.panelH==520 and m.bodyW==824 and m.bodyH==402 and m.bodyTop==98 and m.headerH==78,"desktop unchanged "..w.."x"..h)
        else
            assert(m.mode=="compact","short viewport is compact "..w.."x"..h)
            assert(m.scale>=.8 and m.scale<=1,"compact scale band")
            assert(m.scale>oldRule(w,h),"compact beats the old shrink "..w.."x"..h)
            assert(m.bodyH*m.scale>=150,"body keeps room "..w.."x"..h)
            -- design text/buttons that were 18 px / 40 px render >= 14 / 44 after the floor
            for _,t in {10,16,18,22,40} do assert(P.floorText(t,m.scale)*m.scale>=14-1e-9 and P.floorText(t,m.scale)>=t) end
            for _,b in {22,40,48,54,68} do assert(P.floorButton(b,m.scale)*m.scale>=44-1e-9 and P.floorButton(b,m.scale)>=b) end
        end
    end
end
-- desktop sweep: every size of height >= 500 equals the old formula
for w=800,2200,53 do for h=500,1300,41 do local m=P.modal(w,h) assert(m.mode=="desktop" and m.scale==oldRule(w,h)) end end
-- the old shrink really was the problem: 844x330 gui gave ~0.56
assert(math.abs(oldRule(844,330)-0.5577)<.001)
assert(P.modal(844,330).scale>=.95 and P.modal(740,300).scale>=.8)
assert(P.floorText(20,1)==20 and P.floorText(10,1)==14 and P.floorButton(30,1)==44 and P.floorButton(60,.5)==88)
assert(P.toastAnchor(330)=="top" and P.toastAnchor(684)=="default")
-- BD-507: GoalsPanel (44 px header, 14 px text) is not in the ModalCompact pass; its UIScale follows the goal line (0.6 on a phone).
for _,line in {0.3,0.55,0.6,0.65,0.8,0.99} do
    local s=P.floorScale(line,44,14)
    assert(s==1 and 44*s>=44-1e-9 and 14*s>=14-1e-9,"GoalsPanel header >= 44 px and text >= 14 px at goal-line scale "..line)
end
assert(P.floorScale(1,44,14)==1 and P.floorScale(0.6,80,28)==0.6 and math.abs(P.floorScale(0.2,80,28)-44/80)<1e-9,"floorScale only raises, never above 1")
assert(P.floorScale(2,44,14)==1,"never above 1:1")
assert(P.hudScale(.41,22,1)>=14/22 and P.hudScale(.9,22,1)==.9 and P.hudScale(.2,10,.5)==.5)
-- BD-531: the Eggs screen and the Go home confirm fit the VISIBLE compact body at the real phone canvases (836 x 390 and 667 x 375 minus a 0 to 58 px
-- top bar), so their main buttons need no scroll: everything inside [0, bodyH], buttons >= 44 px on screen, no two pieces overlap.
local function inside(y,h,bodyH,what) assert(y>=0 and y+h<=bodyH+1e-6,what.." inside the visible body") end
for _,s in {{836,390},{667,375}} do
    for _,bar in {0,36,44,58} do
        local w,h=s[1],s[2]-bar
        local m=P.modal(w,h)
        assert(m.mode=="compact")
        local bodyH=math.floor(m.bodyH)
        for _,hint in {false,true} do
            local L=P.eggsLayout(bodyH,hint,m.scale)
            local tag=string.format("Eggs %dx%d (bar %d) hint %s body %d",s[1],s[2],bar,tostring(hint),bodyH)
            inside(L.slotY,L.nestH,bodyH,tag.." nests")
            inside(L.cardY,L.cardH,bodyH,tag.." card")
            -- inside the card: row 1 (waiting + status pill), optional hint, OPEN, AUTO, in this order and not touching
            assert(L.rowH+8<=L.hintY or L.hintY>=8+L.rowH,tag.." row 1 above the hint line")
            assert(L.openY>=8+L.rowH and L.openY>=L.hintY+L.hintH,tag.." OPEN under the status row and the hint")
            assert(L.openY+L.openH<=L.gearY,tag.." OPEN does not touch AUTO")
            assert(L.gearY+L.gearH<=L.cardH,tag.." AUTO inside the card")
            assert(L.openH*m.scale>=44-1e-9 and L.gearH*m.scale>=44-1e-9,tag.." OPEN and AUTO >= 44 px")
            assert(L.nestH*m.scale>=44,tag.." nest slots are tap targets")
            assert(L.slotY+L.nestH<=L.cardY,tag.." nests above the card")
        end
        local X=P.exitLayout(bodyH,m.scale)
        local tag=string.format("Go home %dx%d (bar %d) body %d",s[1],s[2],bar,bodyH)
        inside(X.artY,X.artSize,bodyH,tag.." picture")
        inside(X.lineY,X.lineH,bodyH,tag.." line")
        inside(X.totalsY,X.totalsH,bodyH,tag.." totals")
        inside(X.buttonsY,X.buttonH,bodyH,tag.." buttons")
        assert(X.lineY+X.lineH<=X.totalsY and X.totalsY+X.totalsH<=X.buttonsY,tag.." text above the buttons")
        assert(X.buttonH*m.scale>=44-1e-9,tag.." GO HOME and CANCEL >= 44 px")
        assert(X.artY+X.artSize<=bodyH,tag.." picture fits")
    end
end
for _,line in seen do print(line) end
print("phone scale: modal policy, desktop identity, floors ok")
'''

TOUCH = r'''
local T=TouchLayout
for _,s in {{844,390},{836,390},{740,360},{667,375},{844,330},{740,300}} do
    for _,touch in {true,false} do
        local l=T.compute({width=s[1],height=s[2]-(if s[2]>=360 then 36 else 0),touch=touch,navCount=6})
        assert(l.touch==true,"short viewports use the phone layout even without PreferredInput touch "..s[1].."x"..s[2])
        local t=l.timers
        assert(t.scale*T.LEAP_H>=44-1e-9,"Leap button >= 44 px")
        assert(t.leapText*t.scale>=14-1e-9,"Leap text >= 14 px")
        assert(t.weatherText*t.scale>=14-1e-9 and t.buffsText*t.scale>=14-1e-9,"weather timer and speed line >= 14 px")
        assert(l.rail.button.textSize>=14 and l.rail.button.h>=44 and l.rail.button.w>=44,"rail labels >= 14, buttons >= 44")
        assert(l.rail.button.iconOnly==true or l.rail.button.w>=60,"narrow rail buttons are icon-only, wider ones fit a 14 px label "..s[1].."x"..s[2])
        assert(l.crystal.scale*24>=14-1e-9,"wallet text >= 14 px")
        if t.buffsVisible then assert(t.buffsH>=t.buffsText*2,"speed line fits 2 rows") end
    end
end
-- tall desktop unchanged: scale and positions are the old numbers
local d=T.compute({width=1445,height=841,touch=false,navCount=6})
assert(d.touch==false and d.hud.scale==1 and d.timers.scale==1 and d.timers.leapY==0 and d.timers.weatherY==72 and d.timers.buffsY==145)
local d2=T.compute({width=1080,height=684,touch=false,navCount=6})
assert(d2.touch==false and math.abs(d2.hud.scale-.855)<.001,"1080x684 desktop HUD scale unchanged")
print("touch layout: compact HUD floors ok, desktop unchanged")
'''

def script():
    return ('local PhoneScale=' + wrapped('src/shared/PhoneScale.luau') + '\n' + LUAU + '\n'
            'local script={Parent={Config=' + wrapped('src/shared/Config.luau') + ',PhoneScale=PhoneScale}}\n'
            'local TouchLayout=' + wrapped('src/shared/TouchLayout.luau').replace('require(script.Parent.Config)', 'script.Parent.Config').replace('require(script.Parent.PhoneScale)', 'script.Parent.PhoneScale') + '\n' + TOUCH)

def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_phone_scale.luau'; path.write_text(script())
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    scale = (ROOT / 'src/shared/PhoneScale.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'os.clock', 'task.', 'require('):
        assert banned not in scale, 'PhoneScale stays pure: ' + banned
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text()
    locals_ = len(re.findall(r'^local ', boot, re.M))
    assert locals_ <= 193, 'Bootstrap top-level locals: %d (was 193, limit 200)' % locals_
    assert 'PhoneScale' in boot and 'ModalCompact' in boot, 'Bootstrap uses the scale policy'
    assert not re.search(r'^local (PhoneScale|ModalCompact)', boot, re.M), 'no new top-level locals for the compact modal'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--runner', required=True); args = parser.parse_args()
    static_checks(); print(run(args.runner)); print('phone scale: static wiring ok')
