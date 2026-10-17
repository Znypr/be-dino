"""BD-080 offline check of the gameplay HUD rules (Shared/HudRules) plus wiring (HudV2, Bootstrap, TouchLayout).

Runs the real HudRules in Luau: counter formatting (0, 15, 150, 999, >999, junk), bar fill clamp, pop trigger (grow only, in a
run, never with Reduce Motion, merged fast pickups, no pop on reset/first reading), FOOD debug visibility. Static checks cover
the wiring: no new top-level local in client Bootstrap (it sits near Luau's 200-local limit), Island/Sanctuary/catches/GROWTH
HUD text gone, the HUD module reuses the existing "egg" icon (no invented asset ids). Not Studio evidence: see docs/evidence.
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local R=HudRules
assert(R.formatCount(0)=="0" and R.formatCount(7)=="7" and R.formatCount(15)=="15" and R.formatCount(150)=="150")
assert(R.formatCount(999)=="999" and R.formatCount(1000)=="1,000" and R.formatCount(1234)=="1,234" and R.formatCount(9999)=="9,999")
assert(R.formatCount(10000)=="10K" and R.formatCount(12345)=="12.3K" and R.formatCount(99999)=="99.9K")
assert(R.formatCount(999499)=="999.4K" and R.formatCount(999500)=="999K+" and R.formatCount(5e9)=="999K+")
assert(R.formatCount(-5)=="0" and R.formatCount(nil)=="0" and R.formatCount("x")=="0" and R.formatCount(0/0)=="0" and R.formatCount(math.huge)=="0")
assert(R.formatCount(3.9)=="3","fractions floor")
assert(R.eggsText(12)=="EGGS 12" and R.eggsText(nil)=="EGGS 0")
for _,n in {0,1,15,150,999,1000,9999,12345,999499,1e7} do assert(#R.eggsText(n)<=11,"fits the plate: "..n) end
-- bar
assert(R.barFill(0)==0 and R.barFill(-9)==0 and R.barFill(nil)==0 and R.barFill("x")==0 and R.barFill(0/0)==0)
assert(R.barFill(60)==1 and R.barFill(1e9)==1,"full at a normal 5 minute run (BD-386)")
assert(R.barFill(50)>0.85 and R.barFill(5)>0.05 and R.barFill(5)<0.2,"500 food nearly fills, early food shows")
local last=-1
for g=0,800,10 do local f=R.barFill(g) assert(f>=0 and f<=1 and f>=last,"monotonic clamp "..g) last=f end
assert(math.abs(R.sizeFor(150)-2)<1e-9,"sqrt(1+150/50)=2 body curve unchanged")
assert(R.SizeWord=="SIZE" and R.EggsWord=="EGGS")
-- pop
assert(R.shouldPop(3,4,true,true,5),"grew in a run pops")
assert(not R.shouldPop(3,4,true,false,5),"Reduce Motion never pops")
assert(not R.shouldPop(3,3,true,true,5) and not R.shouldPop(4,3,true,true,5),"no pop when equal or reset")
assert(not R.shouldPop(nil,4,true,true,5),"first reading never pops")
assert(not R.shouldPop(0,5,false,true,5),"no pop outside a run")
assert(not R.shouldPop(3,4,true,true,0.05),"rapid pickups merge")
assert(R.shouldPop(3,40,true,true,nil),"big jump pops once")
assert(R.shouldPop(999,1000,true,true,1))
-- debug line
assert(R.showFoodDebug(true,false,false) and R.showFoodDebug(false,true,false))
assert(not R.showFoodDebug(false,false,false),"players never see FOOD")
assert(not R.showFoodDebug(true,true,true),"never on phones")
assert(R.MinTarget>=44)
print("hud rules: counter, bar clamp, pop, debug-line gate ok")
'''

def script():
    return 'local HudRules=' + wrapped('src/shared/HudRules.luau') + '\n' + LUAU

def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_hud.luau'; path.write_text(script())
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    rules = (ROOT / 'src/shared/HudRules.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'os.clock', 'task.', 'require('):
        assert banned not in rules, 'HudRules stays pure: ' + banned
    hud = (ROOT / 'src/client/HudV2.luau').read_text()
    assert 'rbxassetid' not in hud, 'no invented asset ids'
    assert 'Theme.icon(holder, "egg")' in hud, 'reuses the existing egg icon'
    assert 'Theme.MotionEnabled' in hud and 'Rules.shouldPop' in hud, 'pop goes through the rule and Reduce Motion'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text()
    locals_ = len(re.findall(r'^local ', boot, re.M))
    assert locals_ <= 195, 'Bootstrap top-level locals: %d (limit 200, was 195 before BD-080)' % locals_
    assert 'growthLabel' not in boot and 'catchLabel' not in boot, 'old growth/catch labels removed'
    assert 'Safe sanctuary' not in boot and '"Island")' not in boot and ' GROWTH"' not in boot, 'Island/Sanctuary/GROWTH HUD text removed'
    assert 'GrowthIcon' not in boot and 'GrowthBar' not in boot, 'three-bar growth tile removed'
    assert 'require(script.Parent.HudV2).attach(hud,gui,{notify=notify})' in boot and 'require(script.Parent.HudV2).layout(layout)' in boot
    assert 'showFoodDebug(' in boot, 'FOOD debug line gated by HudRules'
    assert not re.search(r'^local HudV2', boot, re.M), 'no new top-level local for HudV2'
    touch = (ROOT / 'src/shared/TouchLayout.luau').read_text()
    assert 'TouchLayout.HUD = {w = 210, h = 64}' in touch, 'HUD slot is the compact egg plate'
    # BD-507: the "Tell us!" button no longer sits on the egg plate. The rect comes from TouchLayout (rect overlap is asserted at 8 phone, 6 tablet
    # and 7 desktop canvases, incl. 1156 x 841, in tools/verify_movement_mobile.py); Bootstrap publishes it, FeedbackClient follows it.
    assert 'result.feedback = feedbackRect(result, width, height)' in touch and touch.count('result.feedback =') == 2, 'desktop and touch layouts both place the Tell us! button'
    assert 'gui:SetAttribute("FeedbackRect"' in boot, 'Bootstrap publishes the Tell us! rect'
    feedback = (ROOT / 'src/client/FeedbackClient.client.luau').read_text(encoding='utf-8')
    assert 'GetAttribute("FeedbackRect")' in feedback and 'UDim2.new(0, 12, 1, -68)' not in feedback, 'Tell us! follows the layout rect (no fixed bottom-left spot over the egg plate)'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--runner', required=True); args = parser.parse_args()
    static_checks(); print(run(args.runner)); print('hud: static wiring ok')
