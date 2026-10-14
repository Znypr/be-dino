"""Execute the pure BD-079 dino action curves (src/shared/DinoMotion.luau) with the pinned Luau runtime.
Covers scale bounds, NaN safety, determinism, exact return to rest, lean smoothing and BIG safety.
Roblox Instances are not executed here; Studio checks are listed in docs/74-dino-motion.md.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local out = M.newPose()
local function rest(p) return p.sx == 1 and p.sy == 1 and p.sz == 1 and p.pitch == 0 and p.roll == 0 and p.fx == 0 and p.dy == 0 and p.fade == 0 end
local function bounded(p)
 for _, k in {"sx", "sy", "sz"} do assert(p[k] >= 0.6 and p[k] <= 1.4, k .. "=" .. p[k]) end
 for _, k in {"sx", "sy", "sz", "pitch", "roll", "fx", "dy", "fade"} do assert(p[k] == p[k] and math.abs(p[k]) < 10, "NaN/huge " .. k) end
 assert(math.abs(p.fx) <= 0.35 and math.abs(p.dy) <= 0.35 and p.fade >= 0 and p.fade <= 1)
end
-- Fresh state is exactly rest and inactive.
local s = M.new()
assert(M.sample(s, 5, out) == false and rest(out))
-- Every transient kind: bounded all along, changes the pose, and returns EXACTLY to rest.
for _, kind in M.Kinds do
 if kind ~= "death" then
  local st = M.new()
  M.trigger(st, kind, 10)
  local moved = false
  for i = 0, 400 do
   local active = M.sample(st, 10 + i * 0.002, out)
   bounded(out)
   if active and not rest(out) then moved = true end
  end
  assert(moved, kind .. " never moved")
  assert(M.sample(st, 10 + M.Duration[kind] + 0.001, out) == false and rest(out), kind .. " did not return to rest")
  assert(next(st.start) == nil, kind .. " leaked state")
 end
end
-- Determinism: same events + time give identical poses, regardless of sampling history.
local a, b = M.new(), M.new()
M.trigger(a, "eat", 1) M.trigger(a, "land", 1.05) M.trigger(a, "bite", 1.1)
M.trigger(b, "eat", 1) M.trigger(b, "land", 1.05) M.trigger(b, "bite", 1.1)
local pa, pb = M.newPose(), M.newPose()
M.sample(b, 1.02, pb) M.sample(b, 1.07, pb)
M.sample(a, 1.12, pa) M.sample(b, 1.12, pb)
for k, v in pa do assert(v == pb[k], "nondeterministic " .. k) end
-- Retriggering the same kind restarts it and never stacks state; spam stays bounded.
local spam = M.new()
for i = 1, 500 do M.trigger(spam, "eat", i * 0.01) M.sample(spam, i * 0.01 + 0.05, out) bounded(out) end
local n = 0 for _ in spam.start do n += 1 end
assert(n == 1, "spam grew state")
-- All kinds at once (worst-case stacking) still respects the 0.6..1.4 envelope.
local all = M.new()
for _, kind in M.Kinds do M.trigger(all, kind, 3, 1) end
all.lean = 0.25
for i = 0, 300 do M.sample(all, 3 + i * 0.002, out) bounded(out) end
-- Death: tips over, shrinks to exactly 0.6 and fades fully; terminal (cannot be restarted or overridden).
local d = M.new()
M.trigger(d, "death", 0)
M.sample(d, 0.2, out) bounded(out) assert(out.roll > 0 and out.fade > 0 and out.fade < 1)
M.sample(d, 5, out) bounded(out)
assert(math.abs(out.sx - 0.6) < 1e-9 and out.fade == 1 and out.roll > 1)
M.trigger(d, "eat", 5) M.sample(d, 5.05, out) assert(out.fade == 1 and d.start.eat == nil)
-- Lean: clamped, smoothed, zero at rest, NaN safe.
local lean = 0
for i = 1, 600 do lean = M.lean(lean, 50, 20, 1 / 60) assert(math.abs(lean) <= M.MaxLean + 1e-12) end
assert(lean < -0.2, "lean should approach the clamp opposite the yaw rate")
local first = M.lean(0, 50, 20, 1 / 60) assert(math.abs(first) < math.abs(lean), "lean must ease in")
for i = 1, 600 do lean = M.lean(lean, 0, 20, 1 / 60) end
assert(lean == 0, "lean must return exactly to 0")
assert(M.lean(0.1, 0 / 0, 5, 0.016) == 0 and M.lean(0.1, 1, 0 / 0, 0.016) == 0)
assert(M.lean(0, 50, 0, 0.1) == 0, "no lean while standing still")
local ls = M.new() ls.lean = 0.2 assert(M.sample(ls, 0, out) == true and out.roll == 0.2)
ls.lean = 0 assert(M.sample(ls, 0, out) == false and rest(out))
-- Growth tween: starts at old/new, eases out monotonically to exactly 1, and a mid-tween retrigger continues without a step.
local g = M.new()
M.trigger(g, "grow", 0, 0.2)
M.sample(g, 0, out) assert(math.abs(out.sx - 0.8) < 1e-9, "grow must start at old/new")
local last = out.sx
for i = 1, 35 do M.sample(g, i * 0.01, out) assert(out.sx >= last - 1e-12 and out.sx <= 1, "grow must ease monotonically") last = out.sx end
M.sample(g, 0.2, out) local mid = M.growFactor(g, 0.2) assert(math.abs(mid - out.sx) < 1e-9)
M.trigger(g, "grow", 0.2, 1 - mid * 0.98) M.sample(g, 0.2, out) assert(math.abs(out.sx - mid * 0.98) < 1e-9, "retrigger must not step")
M.sample(g, 0.6, out) assert(rest(out) and M.growFactor(g, 0.6) == 1, "grow must end at exactly rest")
local w = M.new() M.trigger(w, "windup", 0) M.sample(w, 0.04, out) assert(out.sy < 1) M.cancel(w, "windup") assert(M.sample(w, 0.05, out) == false)
-- Power scales amplitude; bad inputs are clamped; BIG (dimensionless offsets) identical for any scale.
local weak, strong = M.new(), M.new()
M.trigger(weak, "bite", 0, 0.25) M.trigger(strong, "bite", 0, 5)
local pw, ps = M.newPose(), M.newPose()
M.sample(weak, 0.11, pw) M.sample(strong, 0.11, ps)
assert(pw.fx < ps.fx and ps.fx <= 0.35)
M.trigger(weak, "nonsense", 0) M.trigger(weak, "eat", 0 / 0) M.sample(weak, 0.05, out) bounded(out)
print("dino motion tests passed")
'''


def script():
    return 'local M=(function()\n' + (ROOT / 'src/shared/DinoMotion.luau').read_text(encoding='utf-8') + '\nend)()\n' + BODY


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'dino_motion.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
