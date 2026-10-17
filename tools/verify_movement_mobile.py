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


def static_modal_rail():
    """BD-546: the numbers above are only worth something when the game applies them. Bootstrap hands every layout pass's rail clearance to ModalCompact,
    the panel scale and every slide position come from ModalCompact (never a loose fromScale(.5,y) or a PhoneScale.modal call without the clearance),
    and the layout pass re-places the panel x when the clearance changes."""
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    mc = (ROOT / 'src/client/ModalCompact.luau').read_text(encoding='utf-8')
    scales = boot[boot.index('local function scales()'):boot.index('local function characterAdded')]
    assert 'ModalCompact).setClearLeft(TouchLayout.modalClearLeft(layout))' in scales, 'every HUD layout pass publishes the rail clearance to the modal'
    assert scales.index('TouchLayout.compute(') < scales.index('setClearLeft('), 'the clearance comes from the layout just computed'
    assert boot.count('ModalCompact).home(') == 3, 'open/close slide to ModalCompact.home'
    assert 'panel.Position=UDim2.fromScale(' not in boot and 'Position=UDim2.fromScale(.5,.5)})' not in boot.replace('pic.Position', ''), 'no loose centred panel position'
    assert 'PhoneScale).modal(' not in boot, 'Bootstrap takes the modal scale from ModalCompact.model(), which carries the clearance'
    assert 'PhoneScale.modal(size.X, size.Y, clearLeft)' in mc, 'ModalCompact.model passes the clearance'
    assert 'c.panel.Position = UDim2.new(0.5, m.centerDx,' in mc, 'ModalCompact.layout places the panel x from centerDx'
    assert re.search(r'function M\.setClearLeft\(px: number\)[\s\S]*?M\.layout\(\)', mc), 'a changed clearance re-lays the open panel at once'
    print('menu card static wiring ok: clearance published after every layout pass, panel x and scale from ModalCompact')


def static_538_paths():
    """BD-538: the SIZE bar, its hint and the hub chip take their spots from TouchLayout (no centred constants in the views), the chip rect is
    published, and Tell us! is hidden while a menu is open on a phone canvas."""
    hud = (ROOT / 'src/client/HudV2.luau').read_text(encoding='utf-8')
    layout_fn = hud[hud.index('function Hud.layout'):hud.index('return Hud')]
    assert 'layout.sizeBar' in layout_fn and 'layout.sizeHint' in layout_fn and 'UDim2.new(0.5, 0, 0' not in layout_fn, 'HudV2.layout uses the TouchLayout rects'
    assert re.search(r'BAR_W, BAR_H = 250, 34', hud) and 'SIZEBAR = {w = 250, h = 34, hintW = 360, hintH = 28' in (ROOT / 'src/shared/TouchLayout.luau').read_text(encoding='utf-8')
    assert 'UDim2.fromOffset(360, 28)' in hud, 'hint is 360 x 28 design px'
    chip_client = (ROOT / 'src/client/HubTravelClient.luau').read_text(encoding='utf-8')
    assert 'gui:GetAttribute("ChipRect")' in chip_client and 'GetAttributeChangedSignal("ChipRect")' in chip_client, 'chip follows the published rect'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert boot.count('SetAttribute("ChipRect"') == 1, 'Bootstrap publishes ChipRect once per layout pass'
    rules = (ROOT / 'src/shared/HubTravelClientRules.luau').read_text(encoding='utf-8')
    bottom = re.search(r'Rules\.ChipBottom = (\d+)', rules).group(1)
    assert f'CHIP = {{w = 240, h = 48, bottom = {bottom},' in (ROOT / 'src/shared/TouchLayout.luau').read_text(encoding='utf-8'), 'TouchLayout.CHIP matches HubTravelClientRules.ChipBottom and the 240 x 48 button'
    assert 'UDim2.fromOffset(240, 48)' in chip_client
    fb = (ROOT / 'src/client/FeedbackClient.client.luau').read_text(encoding='utf-8')
    assert 'menuOpen = menuOpen(), compact = compactCanvas()' in fb and 'ModalScrim' in fb, 'Tell us! hides behind an open menu on a phone canvas'
    print('BD-538 static paths ok: SIZE bar/hint/chip follow the layout, chip rect published, Tell us! hidden behind a phone menu')


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
 -- BD-538: the in-run SIZE bar and its goal hint (HudV2) and the hub "Back to the middle" chip (HubTravelClient) come from the layout now. They used to be
 -- centred and put 9 x 30 px (bar) and 4 x 44 px (chip) under the weather/LEAP column at 667 x 317. Included for every canvas (more than the game ever shows
 -- at once), so a piece that comes back onto the column, the rail, the egg plate, Tell us!, Admin or Home fails here. The chip is a 48 px tap target.
 if not layout.goals then -- the SIZE bar and hint are in-run only; the Goals header is hub-only (never on screen together)
  table.insert(list, {name = "sizebar", thumbOk = true, r = rect(layout.sizeBar)})
  table.insert(list, {name = "sizehint", thumbOk = true, r = rect(layout.sizeHint)})
 end
 table.insert(list, {name = "chip", interactive = true, thumbOk = true, r = {x = layout.chip.x, y = layout.chip.y, w = layout.chip.w, h = layout.chip.h}})
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
   -- The Studio-only "STUDIO PREVIEW" notice can touch the SIZE bar on 1000+ px tablet canvases (it did before BD-538 too, and the notice is not in the shipped
   -- game); phone canvases (under 1000 px wide) must be clean.
   local studioNotice = width >= 1000 and ((a.name == "notice" and string.sub(list[j].name, 1, 4) == "size") or (list[j].name == "notice" and string.sub(a.name, 1, 4) == "size"))
   assert(studioNotice or not TouchLayout.overlaps(a.r, list[j].r), label .. ": " .. a.name .. " overlaps " .. list[j].name)
  end
  if layout.touch then
   for zone, r in layout.reserved do
    assert(a.thumbOk or not TouchLayout.overlaps(a.r, r), label .. ": " .. a.name .. " intrudes on Roblox " .. zone .. " zone")
   end
   if a.interactive then
    assert(a.r.h >= Config.TouchMinTargetPx - 1e-6 and a.r.w >= Config.TouchMinTargetPx - 1e-6, label .. ": " .. a.name .. " below touch target")
   end
  end
 end
 if layout.touch then
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
    check(v[1], v[2] - bar, touch, nil, goals) -- BD-538: the mouse case too (a PC window this short gets the phone layout)
    local e = TouchLayout.rendered(layout.hud)
    assert(e.w > 0 and e.h > 0 and e.x >= 0 and e.y >= 0, "egg plate visible")
    assert(layout.timers.weatherVisible, "weather chip stays visible")
    local g = layout.goals
    if goals then assert(g and g.y + g.h <= layout.timers.y + 1e-6 or g.x + g.w <= layout.timers.x, "Goals header clear of the weather column") end
   end
  end
 end
end
-- BD-538: at 667 x 317 (the Studio small-phone size) the centred SIZE bar / hint / chip WOULD touch the weather column: the probe keeps this test honest,
-- and the real rects must differ from the centred ones exactly there (and equal them wherever nothing is in the way, e.g. 836 x 332 and desktop).
do
 local S, C = TouchLayout.SIZEBAR, TouchLayout.CHIP
 local run = TouchLayout.compute({width = 667, height = 317, touch = true, navCount = NAV}) -- in a run: SIZE bar + hint, no Goals header
 local hub = TouchLayout.compute({width = 667, height = 317, touch = true, navCount = NAV, goals = true}) -- in the hub: the chip
 local runCol, hubCol = rect(run.timers), rect(hub.timers)
 local centredBar = {x = 667 / 2 - S.w / 2, y = run.sizeBar.y, w = S.w, h = S.h}
 local centredChip = {x = 667 / 2 - C.w / 2, y = 317 - C.bottom - C.h, w = C.w, h = C.h}
 assert(TouchLayout.overlaps(centredBar, runCol) and TouchLayout.overlaps(centredChip, hubCol), "probe lost sensitivity: centred bar/chip no longer touch the column")
 assert(not TouchLayout.overlaps(rect(run.sizeBar), runCol) and not TouchLayout.overlaps(rect(run.sizeHint), runCol), "667 x 317: bar and hint clear of the column")
 assert(not TouchLayout.overlaps(hub.chip, hubCol) and not TouchLayout.overlaps(hub.chip, hub.goals), "667 x 317: chip clear of the column and the Goals header")
 assert(run.chip.w * 1 >= Config.TouchMinTargetPx and run.chip.h >= Config.TouchMinTargetPx and hub.chip.x >= 0, "chip is a 44 px target, on the canvas")
 local wide = TouchLayout.compute({width = 836, height = 332, touch = true, navCount = NAV, goals = true})
 assert(math.abs(wide.chip.x - (836 / 2 - C.w / 2)) < 1e-6 and math.abs(wide.sizeBar.x - (836 / 2 - S.w * wide.sizeBar.scale / 2)) < 1e-6, "836 x 332 keeps the centred spots")
 for _, v in {{1280, 720}, {1366, 768}, {1920, 1080}, {1156, 841}, {800, 600}, {1024, 768}} do
  local d = TouchLayout.compute({width = v[1], height = v[2], touch = false, navCount = NAV})
  assert(math.abs(d.chip.x - (v[1] / 2 - C.w / 2)) < 1e-6 and math.abs(d.chip.y - (v[2] - C.bottom - C.h)) < 1e-6, "desktop chip unchanged " .. v[1])
  assert(math.abs(d.sizeBar.x - (v[1] / 2 - S.w * d.sizeBar.scale / 2)) < 1e-6 and d.sizeBar.y == 64, "desktop SIZE bar unchanged " .. v[1])
 end
end
-- BD-507: 1156 x 841 is the Studio game view of the owner review pictures (Tell us! sat on "EGGS 0" there); 800 x 600 is a small desktop window (a canvas under 500 px tall is the phone layout).
for _, v in {{1280, 720}, {1366, 768}, {1920, 1080}, {2400, 1080}, {1024, 768}, {1156, 841}, {800, 600}} do check(v[1], v[2], false) end
for _, v in {{1156, 841}, {1280, 720}, {1920, 1080}, {1024, 768}, {800, 600}} do
 local layout = TouchLayout.compute({width = v[1], height = v[2], touch = false, navCount = NAV})
 assert(not TouchLayout.overlaps(layout.feedback, TouchLayout.rendered(layout.hud)), string.format("%dx%d desktop: Tell us! covers the egg plate", v[1], v[2]))
 assert(layout.feedback.h >= Config.TouchMinTargetPx and layout.feedback.w >= Config.TouchMinTargetPx, "Tell us! below the 44 px target")
end
-- BD-546: no menu card (the Bootstrap modal panel) may cover the left rail on a desktop canvas, 1024 to 1920 wide, any height from the
-- 500 px phone limit up. The panel is PhoneScale.modal(w, h, TouchLayout.modalClearLeft(layout)): UIScale scale, centre shifted right by centerDx.
local function modalRect(w, h, clear)
 local m = PhoneScale.modal(w, h, clear)
 local pw, ph = m.panelW * m.scale, m.panelH * m.scale
 return m, {x = w / 2 + m.centerDx - pw / 2, y = h / 2 - ph / 2, w = pw, h = ph}
end
local modalChecked, legacyOverlaps = 0, 0
for w = 1024, 1920, 8 do
 for _, h in {500, 560, 600, 640, 700, 727, 768, 785, 800, 841, 900, 1000, 1080} do
  local layout = TouchLayout.compute({width = w, height = h, touch = false, navCount = NAV})
  local m, panel = modalRect(w, h, TouchLayout.modalClearLeft(layout))
  local label = string.format("%dx%d desktop modal", w, h)
  assert(m.mode == "desktop", label .. ": desktop canvas keeps the desktop panel")
  assert(panel.x >= 0 and panel.x + panel.w <= w + 1e-6 and panel.y >= -1e-6 and panel.y + panel.h <= h + 1e-6, label .. ": the menu card leaves the screen")
  assert(m.scale >= 0.5, label .. ": the menu card shrank under 0.5")
  local railBox = rect(layout.rail)
  assert(not TouchLayout.overlaps(panel, railBox), label .. ": the menu card covers the left rail")
  for i, p in layout.rail.positions do
   local button = {x = layout.rail.x + p.x * layout.rail.scale, y = layout.rail.y + p.y * layout.rail.scale, w = layout.rail.button.w * layout.rail.scale, h = layout.rail.button.h * layout.rail.scale}
   assert(not TouchLayout.overlaps(panel, button), label .. ": the menu card covers rail button " .. i)
   assert(panel.x >= button.x + button.w + PhoneScale.ModalRailGap - 1e-6, label .. ": rail button " .. i .. " has no gap before the menu card")
  end
  -- where the old centred panel already cleared the rail, nothing moves (no shift, the old scale)
  local old = PhoneScale.modal(w, h)
  local _, oldPanel = modalRect(w, h, nil)
  if not TouchLayout.overlaps(oldPanel, railBox) and oldPanel.x >= railBox.x + railBox.w + PhoneScale.ModalRailGap then
   assert(m.centerDx == 0 and math.abs(m.scale - old.scale) < 1e-9, label .. ": a panel that already clears the rail must not move")
  else
   legacyOverlaps += 1
  end
  modalChecked += 1
 end
end
assert(legacyOverlaps > 0, "BD-546 probe lost sensitivity: the old centred panel no longer overlaps the rail anywhere")
do -- the owner's 1140 x 785 game view (top bar excluded: 727 tall): the old panel started at x=140 over a rail that ends at 183
 local layout = TouchLayout.compute({width = 1140, height = 727, touch = false, navCount = NAV})
 local _, oldPanel = modalRect(1140, 727, nil)
 assert(TouchLayout.overlaps(oldPanel, rect(layout.rail)), "1140 x 727: the old centred card should cover the rail (the bug)")
 local _, panel = modalRect(1140, 727, TouchLayout.modalClearLeft(layout))
 assert(panel.x >= layout.rail.x + layout.rail.w * layout.rail.scale + 12 - 1e-6 and panel.w >= 860 * 0.99, "1140 x 727: the card clears the rail at full size")
end
-- Phones and tablets: unchanged. Touch layouts give clearLeft 0 and compact canvases ignore it, so the panel is the old one exactly.
for _, v in {{800, 360}, {667, 375}, {836, 390}, {844, 390}, {915, 412}, {800, 302}, {1024, 768}, {1280, 800}, {2400, 1080}} do
 local layout = TouchLayout.compute({width = v[1], height = v[2], touch = true, navCount = NAV})
 assert(TouchLayout.modalClearLeft(layout) == 0, string.format("%dx%d touch: no left-rail clearance (the touch rail is a top row)", v[1], v[2]))
 local a, b = PhoneScale.modal(v[1], v[2], TouchLayout.modalClearLeft(layout)), PhoneScale.modal(v[1], v[2])
 assert(a.scale == b.scale and a.panelW == b.panelW and a.panelH == b.panelH and a.centerDx == 0 and b.centerDx == 0 and a.mode == b.mode, string.format("%dx%d touch modal changed", v[1], v[2]))
end
for _, v in {{800, 360}, {667, 375}, {836, 390}, {844, 390}, {915, 412}, {800, 302}, {700, 480}} do -- a mouse in a short window is the phone layout too
 local layout = TouchLayout.compute({width = v[1], height = v[2], touch = false, navCount = NAV})
 local m = PhoneScale.modal(v[1], v[2], TouchLayout.modalClearLeft(layout))
 assert(m.mode == "compact" and m.centerDx == 0, string.format("%dx%d phone-height modal must stay compact and centred", v[1], v[2]))
end
print(string.format("Menu cards clear the left rail: %d desktop canvases 1024-1920 wide (13 heights each); 1140 x 727 fixed; phones, tablets and compact windows unchanged", modalChecked))
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
    static_538_paths()
    static_modal_rail()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'verify.luau'
        path.write_text(script(), encoding='utf-8')
        subprocess.run([args.runner, str(path)], check=True)
