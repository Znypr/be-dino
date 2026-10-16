"""BD-378 / BD-380: the egg-found toast and the hatch "N left" counter (root causes found from code; docs/113 smoke).

BD-380 (counter). A hatch page commits up to Config.HatchPageSize ready run eggs in one transaction. The eggs after the
first one are removed from profile.eggs and parked in the server's reveal buffer (still to be revealed, already credited).
ActiveChestCount (= #profile.eggs) and QueuedEggsWaiting (= bank + grants) do not include them, so after the first claim of
a 4-egg run the client saw active 0 + waiting 0 and HatchTimeline.remaining's floor of 1 printed "Tap for next egg (1 left)"
with 3 eggs still to open ("Egg 1 of 2"). The fix publishes BufferedRevealCount (owner-only PrivateState) and the client adds it.
This test drives the REAL ProfileRepository claim flow (the verify_rewards mocked DataStore harness) and then computes the
hint exactly as Bootstrap does, for a 4, 12 and 25 egg run, claim by claim.

BD-378 (toast). Two causes. (1) The second card ("Frost egg caught!") came from an old Bootstrap path with its own key; #210
merged it into the one HudV2 toast: a static scan keeps it single (one toast site, one Heartbeat connection, one attach).
(2) The stack sat over the Crystals plate and the goal line under it ("Level 1: 0/100 XP"): with a menu open it was forced
to y=4 and centred, so on every canvas narrower than about 1000 px it covered both. TouchLayout.toastPlacement now keeps it
clear of that wallet rect on a grid of desktop and phone canvases, menu open and closed.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_rewards  # noqa: E402  (the mocked DataStore + real ProfileRepository harness)


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


COUNTER = r'''
------------------------------------------------------------------ BD-380: the hatch "N left" counter
local T=(function()
 local RS=@@REVEAL_SKIP@@
 local V2=@@HATCH_V2@@
 local script={Parent={RevealSkip=RS,HatchV2Plan=V2}}
 local function require(x) return x end
 return @@HATCH_TIMELINE@@
end)()
-- Exactly what Bootstrap computes for the hint after a claim (PrivateState values; the stub keeps them in attrs).
local function clientRemaining(u)
 local more=u.attrs.NextChestId~="" and (u.attrs.NextChestReadyAt or 0)<=os.time()+5
 return T.remaining(more,u.attrs.ActiveChestCount or 0,u.attrs.QueuedEggsWaiting or 0,u.attrs.BufferedRevealCount or 0)
end
for _,runEggs in {4,12,25} do
 local u=user(300+runEggs)
 assert(Repository.load(u))
 assert(Repository.commitRunSettlement(u,"count-"..runEggs,runEggs))
 local batch=T.newBatch()
 for k=1,runEggs do
  local ok,_,status=Repository.claimChest(u,u.attrs.NextChestId)
  assert(ok and status=="claimed",tostring(status))
  local left=runEggs-k
  local shown=clientRemaining(u)
  assert(shown==left,string.format("%d-egg run, egg %d opened: the hint says %d left but %d are still to open (active %s, waiting %s, buffered %s, really buffered %d)",
   runEggs,k,shown,left,tostring(u.attrs.ActiveChestCount),tostring(u.attrs.QueuedEggsWaiting),tostring(u.attrs.BufferedRevealCount),Repository.pendingReveals(u)))
  assert(u.attrs.BufferedRevealCount==Repository.pendingReveals(u),"the published buffered count is the server's own reveal buffer")
  local i,n=T.batchStep(batch,shown,os.clock())
  assert(i==k and n==runEggs,string.format("counter reads Egg %d of %d, expected Egg %d of %d",i,n,k,runEggs))
  assert(T.hint(shown)==(if left>0 then "Tap for next egg ("..left.." left)" else "Done"))
 end
 assert(u.attrs.BufferedRevealCount==0 and u.attrs.NextChestId=="")
end
-- Leaving mid-page: the buffer is gone with the session; a rejoin must not show a stale buffered count.
do
 local u=user(399)
 assert(Repository.load(u))
 assert(Repository.commitRunSettlement(u,"count-leave",12))
 assert(Repository.claimChest(u,u.attrs.NextChestId))
 assert(u.attrs.BufferedRevealCount>0)
 Repository.release(u)
 assert(Repository.load(u))
 assert((u.attrs.BufferedRevealCount or 0)==0,"a rejoin starts with an empty reveal buffer")
end
print("BD-380 counter passed: hint and Egg N of M equal the eggs really left after every claim (4, 12 and 25 egg runs, buffered page eggs counted)")
'''

PLACEMENT = r'''
-- BD-378: the toast stack never covers the Crystals plate or the goal line under it.
local PhoneScale=(function() @@PHONE_SCALE@@ end)()
local TL
do
 local script={Parent={Config=@@CONFIG@@,PhoneScale=PhoneScale}}
 local function require(x) return x end
 TL=@@TOUCH_LAYOUT@@
end
local function overlaps(a,b) return a.x<b.x+b.w-1e-6 and b.x<a.x+a.w-1e-6 and a.y<b.y+b.h-1e-6 and b.y<a.y+a.h-1e-6 end
local grid,checked,moved=0,0,0
for _,w in {640,667,740,770,812,844,900,960,1000,1100,1280,1445,1920} do
 for _,h in {360,375,390,420,500,600,720,841,1080} do
  for _,touch in {true,false} do
   local layout=TL.compute({width=w,height=h,touch=touch,navCount=7})
   local plates=TL.walletPlates(layout)
   local ts=layout.toastScale
   for _,menuOpen in {false,true} do
    local shift,top=TL.toastPlacement(w,ts,plates,menuOpen,0)
    local rect={x=w/2+shift-220*ts,y=top,w=440*ts,h=186*ts}
    checked+=1
    assert(not overlaps(rect,plates),string.format("%dx%d touch=%s menu=%s: the toast stack (x %.0f..%.0f, y %.0f..%.0f) covers the Crystals / XP plates (x %.0f..%.0f, y %.0f..%.0f)",
     w,h,tostring(touch),tostring(menuOpen),rect.x,rect.x+rect.w,rect.y,rect.y+rect.h,plates.x,plates.x+plates.w,plates.y,plates.y+plates.h))
    assert(rect.x>=-1e-6 and rect.x+rect.w<=w+1e-6,string.format("%dx%d: the toast stays on screen horizontally",w,h))
    assert(top>=(if menuOpen then 4 else 80),"never higher than the old slot")
    if shift~=0 or top~=(if menuOpen then 4 else 80) then moved+=1 end
   end
  end
 end
 grid+=1
end
-- Roomy canvases keep the old placement exactly (desktop unchanged): run slot y=80 and menu slot y=4, centred, when clear.
do
 local layout=TL.compute({width=1920,height=1080,touch=false,navCount=7})
 local plates=TL.walletPlates(layout)
 local shift,top=TL.toastPlacement(1920,layout.toastScale,plates,false,0) assert(shift==0 and top==80,"1920x1080 run slot unchanged")
 shift,top=TL.toastPlacement(1920,layout.toastScale,plates,true,0) assert(shift==0 and top==4,"1920x1080 menu slot unchanged")
end
-- The reported case: a ~770 px wide window with the "Return to Sanctuary" confirm open (docs/evidence/2026-10-16-integration-smoke/04b).
do
 local layout=TL.compute({width=770,height=600,touch=false,navCount=7})
 local plates=TL.walletPlates(layout)
 local legacy={x=770/2-220*layout.toastScale,y=4,w=440*layout.toastScale,h=186*layout.toastScale}
 assert(overlaps(legacy,plates),"fixture: the old centred y=4 stack really covers the plates here")
end
-- An admin panel sliding the stack right is respected, and the plates are still cleared (dropped below instead of slid left).
do
 local layout=TL.compute({width=1280,height=720,touch=false,navCount=7})
 local plates=TL.walletPlates(layout)
 local shift,top=TL.toastPlacement(1280,layout.toastScale,plates,false,300)
 local rect={x=1280/2+shift-220*layout.toastScale,y=top,w=440*layout.toastScale,h=186*layout.toastScale}
 assert(shift==300 and not overlaps(rect,plates),"admin shift kept, plates cleared")
 assert(TL.toastPlacement(1280,layout.toastScale,nil,true,0)==0,"no plate known yet: centred")
end
print(string.format("BD-378 placement passed: %d canvas sizes x touch/mouse x menu open/closed = %d placements keep the toast off the Crystals / XP plates (%d were moved)",grid*9,checked,moved))
'''


def counter_script():
    s = verify_rewards.script()
    marker = '------------------------------------------------------------------ RewardMath'
    s = s[:s.index(marker)]
    body = COUNTER
    for token, path in (('@@REVEAL_SKIP@@', 'src/shared/RevealSkip.luau'), ('@@HATCH_V2@@', 'src/shared/HatchV2Plan.luau'),
                        ('@@HATCH_TIMELINE@@', 'src/shared/HatchTimeline.luau')):
        body = body.replace(token, module(path))
    return s + body


def placement_script():
    body = PLACEMENT
    phone = (ROOT / 'src/shared/PhoneScale.luau').read_text(encoding='utf-8')
    touch = module('src/shared/TouchLayout.luau').replace('require(script.Parent.Config)', 'script.Parent.Config').replace(
        'require(script.Parent.PhoneScale)', 'script.Parent.PhoneScale')
    body = body.replace('@@PHONE_SCALE@@', phone).replace('@@CONFIG@@', module('src/shared/Config.luau')).replace('@@TOUCH_LAYOUT@@', touch)
    return body


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_wiring():
    boot = read('src/client/Bootstrap.client.luau')
    hud = read('src/client/HudV2.luau')
    core = read('src/shared/PrivateStateCore.luau')
    repo = read('src/server/ProfileRepository.luau')
    # BD-380: server publishes the buffered count, the client adds it at every call site.
    assert '"BufferedRevealCount"' in core, 'BufferedRevealCount must be a classified PrivateState name'
    assert 'PrivateState.set(player, "BufferedRevealCount"' in repo, 'the server publishes its reveal buffer size'
    calls = re.findall(r'HatchTimeline\.remaining\(', boot)
    assert len(calls) == 3 and boot.count('num("BufferedRevealCount")') == 3, 'every remaining() call site passes the buffered count'
    # BD-378: one found-egg toast site and one HudV2 loop; no other client file raises an egg-found / egg-caught card.
    assert len(re.findall(r'key\s*=\s*"egg_found"', hud)) == 1, 'one egg_found toast site'
    assert len(re.findall(r'RunService\.Heartbeat:Connect', hud)) == 1, 'HudV2 keeps ONE Heartbeat loop (a second one would toast twice)'
    assert boot.count('require(script.Parent.HudV2).attach(') == 1, 'HudV2.attach runs once'
    for path in sorted((ROOT / 'src/client').glob('*.luau')):
        if path.name == 'HudV2.luau':
            continue
        text = path.read_text(encoding='utf-8')
        for needle in ('egg caught', 'mutation_egg', '"egg_found"'):
            assert needle not in text, path.name + ' raises its own egg-found toast: ' + needle
    # BD-378: the toast placement comes from the pure layout rule, not a fixed y.
    assert 'toastPlacement(' in boot and 'WalletRect' in boot, 'Bootstrap places the toast with TouchLayout.toastPlacement'
    assert 'topY=if shade.Visible then 4 else 80' not in boot, 'the fixed y=4 / y=80 slot is gone'


def run(runner, name, source):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / name
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        return result.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    code = run(args.runner, 'egg_count.luau', counter_script())
    code = run(args.runner, 'egg_toast_placement.luau', placement_script()) or code
    try:
        check_wiring()
        print('BD-378/BD-380 wiring passed: one egg-found toast site, one HUD loop, buffered count published and used, toast placed by the pure rule')
    except AssertionError as problem:
        print('WIRING FAILED:', problem)
        code = code or 1
    raise SystemExit(code)
