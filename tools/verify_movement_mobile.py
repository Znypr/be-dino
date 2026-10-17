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
import argparse, re, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]


def wrapped(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


def static_feedback_paths():
    """BD-524: every code path that can move the "Tell us!" button (first screen, mid-run, Run Complete, respawn, a toast, the Admin button)
    must use the published TouchLayout.feedback rect. The Luau layout math below proves the rect is clear; this proves nothing else
    repositions the button after it. Static, so it also covers the post-run and respawn paths that the layout runner cannot reach."""
    fb = (ROOT / 'src/client/FeedbackClient.client.luau').read_text(encoding='utf-8')
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    # 1. Nothing outside FeedbackClient touches the button.
    for path in (ROOT / 'src').rglob('*.luau'):
        text = path.read_text(encoding='utf-8')
        if path.name != 'FeedbackClient.client.luau':
            assert 'TellUsButton' not in text, f'{path.name}: only FeedbackClient may touch the Tell us! button'
            assert not re.search(r'PlayerGui[^\n]{0,80}"PlaytestFeedback"', text), f'{path.name}: only FeedbackClient may reach the PlaytestFeedback gui'
    # 2. Exactly one function, pin(), assigns Position/Size; it reads the published rect.
    match = re.search(r'^local function pin\(\)\n(.*?)^end\n', fb, re.M | re.S)
    assert match, 'FeedbackClient: pin() missing'
    pin_body, outside = match.group(1), fb[:match.start()] + fb[match.end():]
    assert 'GetAttribute("FeedbackRect")' in pin_body, 'pin() must read the published FeedbackRect'
    assert len(re.findall(r'open\.Position, open\.Size = pos, size', pin_body)) == 1, 'pin() assigns open.Position once, from the rect'
    assert not re.search(r'open\.(Position|Size)\b[^\n]*[^=<>~]=[^=]', outside), 'a path outside pin() assigns the Tell us! Position/Size'
    assert 'open.Position' not in outside.replace('open:GetPropertyChangedSignal("Position")', ''), 'open.Position is used outside pin()'
    # 3. The initial spot is the one fallback constant (above the plate), used only until the first publish.
    assert fb.count('FALLBACK_POS') == 3 and 'UDim2.new(0, 18, 1, -138)' in fb and 'UDim2.new(0, 12, 1, -68)' not in fb, 'only the above-the-plate fallback may position the button'
    # 4. pin() re-runs on every event that could leave the button stale: a new rect, any other change of Position, Visible (run end, respawn), the plate moving.
    for hook in ('ui:GetAttributeChangedSignal("FeedbackRect"):Connect(pin)', 'open:GetPropertyChangedSignal("Position"):Connect(pin)',
                 'open:GetPropertyChangedSignal("Visible"):Connect(pin)', 'plate:GetPropertyChangedSignal("AbsolutePosition"):Connect(pin)'):
        assert hook in fb, 'pin() hook missing: ' + hook
    # 5. The run-end / respawn watcher (BD-441) only changes Visible, never the spot.
    watcher = fb[fb.index('-- BD-441: watch the character'):fb.index('open.Activated:Connect')]
    assert 'CharacterAdded' in watcher and 'Rules.showButton' in watcher and 'open.Visible' in watcher
    assert 'Position' not in watcher and 'open.Size' not in watcher, 'the run-end / respawn watcher must not move the button'
    # 6. Neither gui is rebuilt on respawn, and both share one pixel space, so the published rect stays valid after a respawn.
    assert 'gui.Name, gui.ResetOnSpawn, gui.DisplayOrder = "PlaytestFeedback", false, 40' in fb
    assert 'gui.Name,gui.ResetOnSpawn,gui.ZIndexBehavior = "BeDinoUI",false' in boot
    assert 'ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets' in fb and 'gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets' in boot
    # 7. The rect is published once per layout pass, from scales(), after HudV2.layout, and scales() re-runs on resize, viewport, touch controls, input change.
    assert boot.count('SetAttribute("FeedbackRect"') == 1 and 'RemoveAttribute("FeedbackRect")' not in boot, 'one publisher, never cleared'
    scales = boot[boot.index('local function scales()'):boot.index('local function characterAdded')]
    assert scales.index('HudV2).layout(layout)') < scales.index('SetAttribute("FeedbackRect"'), 'FeedbackRect is published after the HUD layout'
    for trigger in ('gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(scales)', 'ViewportSize"):Connect(scales)', 'task.defer(function() layoutQueued=false scales() end)'):
        assert trigger in boot, 'layout re-run trigger missing: ' + trigger
    assert '\nscales()\ngui:SetAttribute("Ready",true)' in boot, 'first layout pass runs before Ready'
    print('Tell us! static paths ok: one writer (pin), run-end/respawn only flip Visible, rect republished by every layout pass')


def script():
    return 'local Config = ' + wrapped('src/shared/Config.luau') + '\nlocal PhoneScale = ' + wrapped('src/shared/PhoneScale.luau') + '\n' + '''
local script = {Parent = {Config = "Config", PhoneScale = "PhoneScale"}}
local require = function(name) if name == "PhoneScale" then return PhoneScale end return Config end
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
 -- BD-507: the Tell us! button (FeedbackClient) must never touch the egg plate ("hud") or any other HUD piece. On touch it sits in the bottom-left
 -- corner, which is inside Roblox's thumbstick zone (a 120 x 48 button there only swallows taps on itself), so only that zone check is skipped.
 table.insert(list, {name = "feedback", interactive = true, thumbOk = true, r = {x = layout.feedback.x, y = layout.feedback.y, w = layout.feedback.w, h = layout.feedback.h}})
 -- BD-531: the Admin button (Studio/admin only) and the hub Goals header must not sit on any HUD piece either (it covered the egg plate at 836 x 390).
 table.insert(list, {name = "admin", interactive = true, thumbOk = true, r = {x = layout.admin.x, y = layout.admin.y, w = layout.admin.w, h = layout.admin.h}})
 if layout.goals then table.insert(list, {name = "goals", interactive = true, thumbOk = true, r = {x = layout.goals.x, y = layout.goals.y, w = layout.goals.w, h = layout.goals.h}}) end
 table.insert(list, {name = "goalline", r = {x = layout.crystal.x, y = layout.crystal.y + layout.crystal.h * layout.crystal.scale + TouchLayout.GOAL_GAP, w = layout.crystal.w * layout.crystal.scale, h = TouchLayout.GOAL_H * layout.crystal.scale}})
 table.insert(list, {name = "notice", r = rect(layout.notice)})
 local rail = layout.rail
 for i, p in rail.positions do
  table.insert(list, {name = "nav" .. i, interactive = true, button = true,
   r = {x = rail.x + p.x * rail.scale, y = rail.y + p.y * rail.scale, w = rail.button.w * rail.scale, h = rail.button.h * rail.scale}})
 end
 return list
end
local NAV = 7
local function check(width, height, touch, measured, goals)
 local layout = TouchLayout.compute({width = width, height = height, touch = touch, navCount = NAV,
  thumb = measured and measured.thumb, jump = measured and measured.jump, goals = goals})
 local list = elements(layout)
 local label = string.format("%dx%d %s%s", width, height, if touch then "touch" else "desktop", if goals then " hub" else "")
 for i, a in list do
  assert(inside(a.r, width, height), label .. ": " .. a.name .. " leaves the safe canvas")
  for j = i + 1, #list do
   assert(not TouchLayout.overlaps(a.r, list[j].r), label .. ": " .. a.name .. " overlaps " .. list[j].name)
  end
  if touch then
   for zone, r in layout.reserved do
    assert(a.thumbOk or not TouchLayout.overlaps(a.r, r), label .. ": " .. a.name .. " intrudes on Roblox " .. zone .. " zone")
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
  assert(goals or layout.timers.weatherVisible, label .. ": weather hidden") -- BD-531: with the hub Goals header a very small canvas may drop the weather chip (never overlap it); the target phones below must keep it
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
for _, v in phones do check(v[1], v[2], true) check(v[1], v[2], true, nil, true) end
for _, v in tablets do check(v[1], v[2], true) check(v[1], v[2], true, nil, true) end
-- BD-531: the real phone-landscape canvases. A 836 x 390 / 667 x 375 screen minus the Roblox top bar (36 to 58 px; the ScreenGui uses
-- CoreUISafeInsets, which is what AbsoluteSize reports) is what TouchLayout sees; in a run and in the hub (Goals header on screen), mouse or touch.
-- Every HUD element must be on the canvas and clear of every other one: egg plate ("hud"), wallet, goal line, Goals header, weather/leap/buffs
-- column, rail, Home/Explore, Tell us!, Admin button.
for _, v in {{836, 390}, {667, 375}} do
 for _, bar in {0, 36, 44, 58} do
  for _, goals in {false, true} do
   for _, touch in {true, false} do -- Studio / a PC window this short reports a mouse: it still gets the phone layout (PhoneScale.isCompact)
    local layout = TouchLayout.compute({width = v[1], height = v[2] - bar, touch = touch, navCount = NAV, goals = goals})
    assert(layout.touch, "short canvas uses the phone layout")
    if touch then check(v[1], v[2] - bar, true, nil, goals) end
    local e = TouchLayout.rendered(layout.hud)
    assert(e.w > 0 and e.h > 0 and e.x >= 0 and e.y >= 0, "egg plate visible")
    assert(layout.timers.weatherVisible, "weather chip stays visible")
    local g = layout.goals
    if goals then assert(g and g.y + g.h <= layout.timers.y + 1e-6 or g.x + g.w <= layout.timers.x, "Goals header clear of the weather column") end
   end
  end
 end
end
-- BD-507: 1156 x 841 is the Studio game view of the owner review pictures (Tell us! sat on "EGGS 0" there); 800 x 600 is a small desktop window (a canvas under 500 px tall is the phone layout).
for _, v in {{1280, 720}, {1366, 768}, {1920, 1080}, {2400, 1080}, {1024, 768}, {1156, 841}, {800, 600}} do check(v[1], v[2], false) end
for _, v in {{1156, 841}, {1280, 720}, {1920, 1080}, {1024, 768}, {800, 600}} do
 local layout = TouchLayout.compute({width = v[1], height = v[2], touch = false, navCount = NAV})
 assert(not TouchLayout.overlaps(layout.feedback, TouchLayout.rendered(layout.hud)), string.format("%dx%d desktop: Tell us! covers the egg plate", v[1], v[2]))
 assert(layout.feedback.h >= Config.TouchMinTargetPx and layout.feedback.w >= Config.TouchMinTargetPx, "Tell us! below the 44 px target")
end
-- A live TouchGui measured larger than the defaults is still avoided.
check(800, 360, true, {jump = {x = 690, y = 250, w = 90, h = 90}, thumb = {x = 0, y = 110, w = 340, h = 250}})
local phone = TouchLayout.compute({width = 800, height = 360, touch = true, navCount = NAV})
print(string.format("Touch layout passed: %d phone + %d tablet + 7 desktop canvases (Tell us! clear of the egg plate and every HUD piece); 800x360 Home %dx%d px, nav %dx%d px, leap %d px tall, no overlap with thumbstick/jump zones",
 #phones, #tablets, phone.action.w * phone.action.scale, phone.action.h * phone.action.scale,
 phone.rail.button.w, phone.rail.button.h, TouchLayout.LEAP_H * phone.timers.scale))
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_feedback_paths()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify.luau'
        path.write_text(script(), encoding='utf-8')
        subprocess.run([args.runner, str(path)], check=True)
