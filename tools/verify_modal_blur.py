"""BD-296: the modal blur (Lighting.BeDinoModalBlur) is on only while a modal is actually visible.

Root cause being guarded: the old guard in Bootstrap only forced the blur to 0 when `active == ""` or `ModalScrim.Visible == false`. Disabling
(or destroying) the BeDinoUI ScreenGui while a menu was open leaves both true, so the blur stayed at Size 8 with nothing on screen.

Runs the REAL src/shared/ModalBlurGuard.luau, and the REAL guard wiring cut out of src/client/Bootstrap.client.luau (from
`local function modalState()` to the end of the poll loop) against mocked ScreenGui / scrim / blur objects (logic only, not Studio).

    python tools/verify_modal_blur.py --runner /path/to/luau
"""
from pathlib import Path
import argparse, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
START = 'local function modalState()'
END = '        clearStrayBlur()\n    end\nend)\n'

HARNESS = r'''
local Guard = (function() @@GUARD@@ end)()
local ModalBlurGuard = Guard

-- ---- pure rule
local function st(a, v, e, at) return {active = a, shadeVisible = v, guiEnabled = e, guiAttached = at} end
assert(Guard.modalShowing(st("shop", true, true, true)))
assert(not Guard.modalShowing(st("", true, true, true)), "no menu open")
assert(not Guard.modalShowing(st("shop", false, true, true)), "scrim hidden")
assert(not Guard.modalShowing(st("shop", true, false, true)), "BD-296: ScreenGui disabled with a menu open")
assert(not Guard.modalShowing(st("shop", true, true, false)), "BD-296: ScreenGui destroyed / unparented with a menu open")
assert(Guard.target(st("shop", true, true, true), true) == 8 and Guard.Size == 8)
assert(Guard.target(st("shop", true, true, true), false) == 0, "Calm / Reduce Motion: never blur")
assert(Guard.target(st("shop", true, false, true), true) == 0)
assert(Guard.mustClear(st("", true, true, true), 8) and not Guard.mustClear(st("", true, true, true), 0))
assert(Guard.mustClear(st("shop", true, false, true), 8) and not Guard.mustClear(st("shop", true, true, true), 8))
for _, a in {"", "shop"} do for _, v in {true, false} do for _, e in {true, false} do for _, at in {true, false} do
    local s = st(a, v, e, at)
    local on = a ~= "" and v and e and at
    assert(Guard.modalShowing(s) == on, "truth table")
    assert(Guard.target(s, true) == (if on then 8 else 0))
end end end end

-- ---- the real Bootstrap wiring against mocks
local function signal()
    local s = {handlers = {}}
    function s.Connect(self, f) table.insert(self.handlers, f) return {Disconnect = function() end} end
    function s.fire(self) for _, f in self.handlers do f() end end
    return s
end
local function guiObject(parentOf)
    local o = {attached = true, signals = {}, AncestryChanged = signal(), Destroying = signal()}
    function o.GetPropertyChangedSignal(self, name) self.signals[name] = self.signals[name] or signal() return self.signals[name] end
    function o.IsDescendantOf(self, other) return self.attached and (parentOf == nil or other == parentOf or other == "player") end
    return o
end
local player = "player"
local gui = guiObject(nil) gui.Enabled = true
local shade = guiObject(gui) shade.Visible = true
local blur = {Size = 8}
local Theme = {animate = function(target, _, goals) for k, v in goals do target[k] = v end end}
local active, motion = "shop", true
local pollers = {}
local task = {spawn = function(f) local co = coroutine.create(f) coroutine.resume(co) table.insert(pollers, co) end, wait = function() coroutine.yield() end}
@@WIRING@@
local function poll() for _, co in pollers do coroutine.resume(co) end end
local function reset() gui.Enabled, gui.attached, shade.Visible, shade.attached, active, motion, blur.Size = true, true, true, true, "shop", true, 8 end

-- menu open and visible: nothing clears it
poll() gui.signals.Enabled:fire() shade.signals.Visible:fire()
assert(blur.Size == 8, "an open, visible modal keeps its blur")
assert(blurTarget() == 8)

-- the lead's case: every ScreenGui disabled while a menu is open
gui.Enabled = false
assert(blurTarget() == 0, "target is 0 while the ScreenGui is disabled")
gui.signals.Enabled:fire()
assert(blur.Size == 0, "BD-296: disabling the ScreenGui clears the blur at once")
-- the old rule would have kept it: active ~= "" and shade.Visible are both still true
assert(not (active == "" or not shade.Visible), "this is the state the old guard missed")

-- same, but the change signal is missed: the poll catches it
reset() gui.Enabled = false poll()
assert(blur.Size == 0, "poll backstop clears a disabled-ScreenGui blur")

-- ScreenGui destroyed / unparented
reset() gui.attached = false gui.AncestryChanged:fire()
assert(blur.Size == 0, "unparented ScreenGui clears the blur")
reset() gui.Destroying:fire()
assert(blur.Size == 0, "destroyed ScreenGui clears the blur")
reset() shade.attached = false shade.AncestryChanged:fire()
assert(blur.Size == 0, "scrim removed clears the blur")

-- ordinary paths still work
reset() active = "" gui.signals.Enabled:fire()
assert(blur.Size == 0, "no menu open clears a stray blur")
reset() shade.Visible = false shade.signals.Visible:fire()
assert(blur.Size == 0, "hidden scrim clears the blur")
reset() blur.Size = 0 gui.signals.Enabled:fire() poll()
assert(blur.Size == 0)
-- opening: the target is 8 only when the modal can really be seen, and 0 under Calm
reset() assert(blurTarget() == 8)
motion = false assert(blurTarget() == 0, "Calm motion: no blur")
motion = true gui.Enabled = false assert(blurTarget() == 0, "open() on a disabled ScreenGui must not raise the blur")
print("modal blur guard ok")
'''


def source():
    guard = (ROOT / 'src/shared/ModalBlurGuard.luau').read_text(encoding='utf-8')
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    a = boot.index(START)
    b = boot.index(END, a) + len(END)
    return HARNESS.replace('@@GUARD@@', guard).replace('@@WIRING@@', boot[a:b])


def static_checks():
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert boot.count('Instance.new("BlurEffect")') == 1 and boot.count('"BeDinoModalBlur"') == 1, 'exactly one modal blur'
    assert 'require(Shared.ModalBlurGuard)' in boot, 'Bootstrap uses the shared guard'
    assert 'Theme.animate(blur,.16,{Size=blurTarget()})' in boot, 'open() aims at the guard target, not a fixed 8'
    assert 'Size=if motion then 8 else 0' not in boot, 'no inline blur size that ignores the ScreenGui state'
    assert 'if (active=="" or not shade.Visible) and blur.Size>0 then blur.Size=0 end' not in boot, 'the old guard (misses a disabled ScreenGui) is gone'
    for needle in ('gui:GetPropertyChangedSignal("Enabled")', 'gui.AncestryChanged', 'shade:GetPropertyChangedSignal("Visible")', 'gui.Destroying:Connect'):
        assert needle in boot, 'guard listens to ' + needle
    guard = (ROOT / 'src/shared/ModalBlurGuard.luau').read_text(encoding='utf-8')
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'require('):
        assert banned not in guard, 'ModalBlurGuard stays pure: ' + banned


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--runner', required=True)
    args = p.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'verify_modal_blur.luau'
        path.write_text(source(), encoding='utf-8')
        out = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(out.stdout.strip() + out.stderr.strip())
        raise SystemExit(out.returncode)
