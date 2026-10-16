"""BD-053/BD-054 offline evidence: run the real shared Luau modules with value stubs.

Slope/traversal: authored heightfield vs Humanoid MaxSlopeAngle, torso-collider slope
clearance at every growth scale (and proof that the legacy box snagged), and the
MovementGuard/service envelope for legitimate climbs, slides, jumps and teleports.
Touch layout: TouchLayout.compute for phone, tablet and desktop canvases, checking
containment, non-overlap, Roblox thumbstick/jump reserved zones and target sizes.
Engine physics, real TouchGui geometry and physical-device DPI still need Studio and
an Android phone; see docs/51-bd053-054-movement-mobile.md.
"""
from pathlib import Path
import argparse, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]


def wrapped(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


def script():
    return 'local Config = ' + wrapped('src/shared/Config.luau') + '\n' + '''
local script = {Parent = {Config = true}}
local require = function(_) return Config end
local workspace = {Gravity = 196.2}
local Vector2 = {new = function(x, y) return {Magnitude = math.sqrt(x * x + y * y)} end}
''' + 'local Layout = ' + wrapped('src/shared/IslandLayout.luau') + '\n' \
        + 'local Envelope = ' + wrapped('src/shared/MovementEnvelope.luau') + '\n' \
        + 'local TouchLayout = ' + wrapped('src/shared/TouchLayout.luau') + '\n' + r'''
local tanMax = math.tan(math.rad(Config.MaxSlopeAngle))

---------------------------------------------------------------- BD-053 slopes
-- 1. The authored heightfield never asks the Humanoid to exceed MaxSlopeAngle.
local steepest = 0
for x = -258, 258, 2 do
 for z = -258, 258, 2 do
  local gx = (Layout.height(x + 1, z) - Layout.height(x - 1, z)) / 2
  local gz = (Layout.height(x, z + 1) - Layout.height(x, z - 1)) / 2
  steepest = math.max(steepest, math.deg(math.atan(math.sqrt(gx * gx + gz * gz))))
 end
end
assert(steepest < Config.MaxSlopeAngle - 2, "terrain steeper than the Humanoid climb limit: " .. steepest)

-- 2. Collider geometry: footprint still grows (BIG colliders), underside clears slopes.
local GROUND = 3 -- R15: root half-height 1 + HipHeight 2; R6: 1 + 0 + leg 2
local function box(scale)
 local w, h, l, offset = Envelope.collider(scale, GROUND)
 return {w = w, h = h, l = l, bottom = offset + GROUND - h / 2, top = offset + GROUND + h / 2}
end
local scales = {1, 1.5, 2, 3, 4, 4 * Config.BigScaleMultiplier}
local previousTop = 0
for _, scale in scales do
 local b = box(scale)
 assert(math.abs(b.w - Config.DinoColliderWidth * scale) < 1e-9 and math.abs(b.l - Config.DinoColliderLength * scale) < 1e-9, "footprint must follow growth")
 assert(b.h >= Config.DinoColliderMinHeight - 1e-9 and b.top > previousTop, "collider must keep a body and grow upward")
 previousTop = b.top
 -- planar slope at exactly MaxSlopeAngle, every direction, every footprint corner
 for yaw = 0, 345, 15 do
  local dx, dz = math.cos(math.rad(yaw)), math.sin(math.rad(yaw))
  for _, corner in {{1, 1}, {1, -1}, {-1, 1}, {-1, -1}} do
   local rise = (corner[1] * b.w / 2 * dx + corner[2] * b.l / 2 * dz) * tanMax
   assert(rise < b.bottom, "collider corner wedges into a walkable slope")
  end
 end
end

-- 3. Real terrain poses: perimeter of the footprint under every pose stays below the box.
local function clipRate(bottomFor)
 local clipped, poses = 0, 0
 for _, scale in {1, 4 * Config.BigScaleMultiplier} do
  local w, l = Config.DinoColliderWidth * scale, Config.DinoColliderLength * scale
  local bottom = bottomFor(scale)
  for x = -250, 250, 10 do
   for z = -250, 250, 10 do
    local h0 = Layout.height(x, z)
    for yaw = 0, 315, 45 do
     local c, s = math.cos(math.rad(yaw)), math.sin(math.rad(yaw))
     local rise = -math.huge
     for i = -4, 4 do
      for j = -4, 4 do
       if math.abs(i) == 4 or math.abs(j) == 4 then
        local lx, lz = w / 2 * i / 4, l / 2 * j / 4
        rise = math.max(rise, Layout.height(x + lx * c - lz * s, z + lx * s + lz * c) - h0)
       end
      end
     end
     poses += 1
     if rise >= bottom then clipped += 1 end
    end
   end
  end
 end
 return clipped / poses
end
local fixed = clipRate(function(scale) return box(scale).bottom end)
local legacy = clipRate(function() return 0.2 end) -- Build 020: 2.4-stud box, 0.2 studs above the floor
assert(fixed == 0, "new collider still touches terrain in " .. fixed * 100 .. "% of poses")
assert(legacy > 0.5, "legacy collider regression probe lost sensitivity")
print(string.format("Slopes passed: steepest authored slope %.1f deg < MaxSlopeAngle %d; collider clears all terrain poses (legacy box snagged in %.0f%%)", steepest, Config.MaxSlopeAngle, legacy * 100))

-- 4. Guard and service envelopes accept legitimate traversal and reject cheats.
local walkFast = Config.WalkSpeed * 2.2 -- ProgressionConfig.SpeedCap
local tolerances = {{Config.MovementGuardSpeedTolerance, Config.MovementGuardBurstStuds}, {2, 2}}
for _, tol in tolerances do
 for _, speed in {Config.WalkSpeed, walkFast} do
  for _, dt in {0.05, 0.1, 0.25, 0.5, 1} do
   local run, climb = speed * dt, Envelope.maxClimbRate(speed) * dt
   for _, vy in {0, Envelope.maxClimbRate(speed)} do
    assert(Envelope.plausible({X = run, Y = climb, Z = 0}, dt, tol[1], tol[2], vy, speed), "uphill climb at max slope rejected")
    assert(Envelope.plausible({X = 0, Y = -climb, Z = run}, dt, tol[1], tol[2], -vy, speed), "downhill traverse rejected")
   end
   local fall = math.min(Config.MovementGuardMaxVerticalSpeed, workspace.Gravity * dt) * dt
   assert(Envelope.plausible({X = run, Y = -fall, Z = 0}, dt, tol[1], tol[2], -workspace.Gravity * dt, speed), "fall rejected")
  end
  assert(Envelope.plausible({X = 2, Y = 5, Z = 0}, 0.1, tol[1], tol[2], Config.JumpPower, speed), "jump rejected")
  -- cheats: horizontal teleport, flying, wall climbing at 75 degrees
  assert(not Envelope.plausible({X = speed * 0.1 * tol[1] + tol[2] + 1, Y = 0, Z = 0}, 0.1, tol[1], tol[2], 0, speed), "teleport accepted")
  assert(not Envelope.plausible({X = 0, Y = 30, Z = 0}, 0.1, tol[1], tol[2], 0, speed), "flight accepted")
 end
 -- A near-vertical (75 degree) climb at SpeedCap pace is outside the envelope. At base speed
 -- the pre-existing per-tick burst allowance can absorb it; the Humanoid's MaxSlopeAngle
 -- is what physically stops wall walking there (documented in docs/51).
 local wall = walkFast * math.tan(math.rad(75)) * 0.1
 assert(not Envelope.plausible({X = walkFast * 0.1, Y = wall, Z = 0}, 0.1, tol[1], tol[2], 0, walkFast), "wall climb accepted")
end
assert(not Envelope.plausible({X = 0, Y = 50, Z = 0}, 0.1, 2, 2, 10000), "vertical teleport accepted")
print("Guard envelope passed: climbs/traverses at MaxSlopeAngle up to SpeedCap, falls and jumps accepted; teleport/flight and SpeedCap 75-degree wall rejected")

---------------------------------------------------------------- BD-054 layout
local function rect(element) return TouchLayout.rendered(element) end
local function inside(r, w, h) return r.x >= -1e-6 and r.y >= -1e-6 and r.x + r.w <= w + 1e-6 and r.y + r.h <= h + 1e-6 end
local function elements(layout)
 local list = {}
 local t = layout.timers
 local function child(name, y, height, interactive)
  table.insert(list, {name = name, interactive = interactive, r = {x = t.x, y = t.y + y * t.scale, w = t.w * t.scale, h = height * t.scale}})
 end
 child("leap", t.leapY, TouchLayout.LEAP_H, true)
 if t.weatherVisible then child("weather", t.weatherY, TouchLayout.WEATHER_H, false) end
 if t.buffsVisible then child("buffs", t.buffsY, t.buffsH, false) end
 table.insert(list, {name = "hud", r = rect(layout.hud)})
 table.insert(list, {name = "crystal", r = rect(layout.crystal)})
 table.insert(list, {name = "action", interactive = true, r = rect(layout.action)})
 table.insert(list, {name = "badge", r = rect(layout.badge)})
 table.insert(list, {name = "notice", r = rect(layout.notice)})
 local rail = layout.rail
 for i, p in rail.positions do
  table.insert(list, {name = "nav" .. i, interactive = true, button = true,
   r = {x = rail.x + p.x * rail.scale, y = rail.y + p.y * rail.scale, w = rail.button.w * rail.scale, h = rail.button.h * rail.scale}})
 end
 return list
end
local NAV = 7
local function check(width, height, touch, measured)
 local layout = TouchLayout.compute({width = width, height = height, touch = touch, navCount = NAV,
  thumb = measured and measured.thumb, jump = measured and measured.jump})
 local list = elements(layout)
 local label = string.format("%dx%d %s", width, height, if touch then "touch" else "desktop")
 for i, a in list do
  assert(inside(a.r, width, height), label .. ": " .. a.name .. " leaves the safe canvas")
  for j = i + 1, #list do
   assert(not TouchLayout.overlaps(a.r, list[j].r), label .. ": " .. a.name .. " overlaps " .. list[j].name)
  end
  if touch then
   for zone, r in layout.reserved do
    assert(not TouchLayout.overlaps(a.r, r), label .. ": " .. a.name .. " intrudes on Roblox " .. zone .. " zone")
   end
   if a.interactive then
    assert(a.r.h >= Config.TouchMinTargetPx - 1e-6 and a.r.w >= Config.TouchMinTargetPx - 1e-6, label .. ": " .. a.name .. " below touch target")
   end
  end
 end
 if touch then
  assert(layout.rail.button.textSize >= 10, label .. ": nav label too small")
  assert(30 * layout.hud.scale >= 11, label .. ": HUD eggs text below 11 px")
  assert(layout.action.w * layout.action.scale >= 2 * Config.TouchMinTargetPx, label .. ": Home too narrow")
  assert(layout.timers.weatherVisible, label .. ": weather hidden")
  local centre = layout.action.x + layout.action.w * layout.action.scale / 2
  assert(math.abs(centre - width / 2) < 1, label .. ": Home is not bottom-centre")
 else
  -- Desktop keeps the Build 020 rail/HUD/wallet geometry.
  local small = math.max(0.3, math.min(1, width / 1000, height / 800))
  assert(layout.rail.x == 14 and math.abs(layout.rail.y + layout.rail.h * small / 2 - height / 2) < 1e-6 and layout.rail.button.w == 172)
  assert(layout.hud.x == 18 and math.abs(layout.hud.y + TouchLayout.HUD.h * small - (height - 18)) < 1e-6)
  assert(math.abs(layout.crystal.x + 260 * layout.crystal.scale - (width - 20)) < 1e-6)
 end
 return layout
end
local phones = {{800, 360}, {640, 360}, {667, 375}, {732, 412}, {844, 390}, {915, 412}, {800, 302}, {760, 360}}
local tablets = {{1024, 768}, {1280, 720}, {1280, 800}, {1366, 1024}, {1920, 1080}, {2400, 1080}}
for _, v in phones do check(v[1], v[2], true) end
for _, v in tablets do check(v[1], v[2], true) end
for _, v in {{1280, 720}, {1366, 768}, {1920, 1080}, {2400, 1080}, {1024, 768}} do check(v[1], v[2], false) end
-- A live TouchGui measured larger than the defaults is still avoided.
check(800, 360, true, {jump = {x = 690, y = 250, w = 90, h = 90}, thumb = {x = 0, y = 110, w = 340, h = 250}})
local phone = TouchLayout.compute({width = 800, height = 360, touch = true, navCount = NAV})
print(string.format("Touch layout passed: %d phone + %d tablet + 5 desktop canvases; 800x360 Home %dx%d px, nav %dx%d px, leap %d px tall, no overlap with thumbstick/jump zones",
 #phones, #tablets, phone.action.w * phone.action.scale, phone.action.h * phone.action.scale,
 phone.rail.button.w, phone.rail.button.h, TouchLayout.LEAP_H * phone.timers.scale))
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify.luau'
        path.write_text(script(), encoding='utf-8')
        subprocess.run([args.runner, str(path)], check=True)
