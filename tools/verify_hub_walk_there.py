"""BD-289 / BD-292 offline check of the Cave hub "walk there" moss trail and the station sign copy (docs/104 s7.6, s6).

Runs the real HubGuideRules, HubSignCopy, CaveHubLayout and HubTravelClientRules in Luau: for a grid of start points and every
station the route starts at the player, ends on the station pad, follows layout path edges, never crosses the lava keep-out;
dots stay <= 24 and evenly spaced; the 25 s life, fade and arrival timing, Reduce Motion (static) behaviour, the guide
decision with the toggle OFF and flag-off identity; every station has a sign <= 14 characters equal to the layout, with no
numbers or jargon. Static checks cover the wiring (no new Bootstrap locals; pooled parts cap; flag off = no-op).
NOT Studio evidence: the live look is checked separately.
"""
from pathlib import Path
import argparse, re, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local G, C, L, R = HubGuideRules, HubSignCopy, CaveHubLayout, HubTravelClientRules
local cz = L.CenterZ
local lay = L.get()
local pool = L.Pool
local function d(ax, az, bx, bz) return math.sqrt((ax-bx)^2+(az-bz)^2) end

-- ---- every layout path is an edge; none crosses the lava keep-out
local nodes, edges = G.graph(L)
assert(#edges == #lay.paths - 1 and #edges >= 20, "every layout path piece except the gate mouth stub is an edge: "..#edges.." vs "..#lay.paths)
for _, e in edges do
 local A, B = nodes[e.a], nodes[e.b]
 assert(not G.hitsCircle(A.x, A.z, B.x, B.z, pool.x, pool.z, pool.r + G.LavaMargin), "edge avoids lava: "..e.a.."-"..e.b)
end

local function onSomeEdge(x, z, tol)
 for _, e in edges do
  local A, B = nodes[e.a], nodes[e.b]
  local dx, dz = B.x-A.x, B.z-A.z
  local t = math.clamp(((x-A.x)*dx+(z-A.z)*dz)/(dx*dx+dz*dz), 0, 1)
  if d(x, z, A.x+dx*t, A.z+dz*t) <= tol then return true end
 end
 return false
end

-- ---- routes from a grid of starts to every station
local routes, here = 0, 0
for gx = -120, 120, 6 do for gz = -100, 110, 6 do
 if L.insideFloor(gx, gz + cz, 4) and d(gx, gz, pool.x, pool.z) > pool.r + G.LavaMargin then
  for _, id in {"nests","potions","fusion","style","index","settings","fame","gate"} do
   local route, why = G.route(L, gx, gz + cz, id)
   if route == nil then
    assert(why == "here" or why == "outside", "reason "..tostring(why))
    if why == "here" then here += 1 assert(d(gx, gz, nodes[id].x, nodes[id].z) <= nodes[id].r) end
   else
    routes += 1
    local pts = route.points
    assert(#pts >= 2, "route has a start and an end")
    assert(math.abs(pts[1].x - gx) < 1e-6 and math.abs(pts[1].z - (gz + cz)) < 1e-6, "route starts at the player")
    local last = pts[#pts]
    assert(d(last.x, last.z - cz, nodes[id].x, nodes[id].z) <= nodes[id].r, "route ends on the pad of "..id)
    local sum = 0
    for i = 2, #pts do
     local a, b = pts[i-1], pts[i]
     sum += d(a.x, a.z, b.x, b.z)
     assert(not G.hitsCircle(a.x, a.z-cz, b.x, b.z-cz, pool.x, pool.z, pool.r + G.LavaMargin - 0.01), "no leg crosses lava ("..id..")")
     assert(onSomeEdge(b.x, b.z-cz, 0.05), "waypoints sit on paths")
     if i > 2 then assert(onSomeEdge((a.x+b.x)/2, (a.z+b.z)/2-cz, 0.05), "leg follows a path") end
    end
    assert(math.abs(sum - route.length) < 1e-6, "length matches")
    assert(onSomeEdge(gx, gz, 0.05) or d(pts[1].x, pts[1].z, pts[2].x, pts[2].z) <= G.NearPathLimit + 0.01, "first leg (the only non-path leg) is short")
    assert(route.length < 600, "sane length")
    local dots = G.dots(pts, G.MaxDots)
    assert(#dots >= 1 and #dots <= 24, "cap 24: "..#dots)
    assert(math.abs(dots[1].x - pts[1].x) < 1e-6 and math.abs(dots[#dots].x - last.x) < 1e-6 and math.abs(dots[#dots].z - last.z) < 1e-6, "dots span the route")
    if #dots >= 3 then
     local step = route.length / (#dots - 1) -- arc spacing; straight distance can only be shorter at a corner
     for i = 3, #dots do
      local s = d(dots[i-1].x, dots[i-1].z, dots[i].x, dots[i].z)
      assert(s <= step * 1.02 + 1e-6, "no gap bigger than the step")
     end
    end
   end
  end
 end
end end
assert(routes > 500 and here > 0, "enough grid routes: "..routes.." here "..here)

-- ---- hand-checked routes
local r1 = G.route(L, 66, -38 + cz, "potions") -- standing on the Nests pad, going to Potions
assert(r1 and #r1.points >= 3, "nests -> potions bends")
local viaHeart = false
for _, p in r1.points do if math.abs(p.x) < 0.01 and math.abs(p.z - cz) < 0.01 then viaHeart = true end end
assert(viaHeart, "nests -> potions goes through the heart plaza")
local r2 = G.route(L, -48, 76 + cz, "fusion") -- from the Settings pad (next to the lava) to Fusion
assert(r2 and r2.length < 120, "settings -> fusion is short and dry")
local r3 = G.route(L, 0, cz, "fusion") assert(r3 and #r3.points == 3 and r3.length >= 48 and r3.length < 56, "heart -> fusion bends once through the short south tunnel: "..tostring(r3 and r3.length))
local nr, why = G.route(L, 66, -38 + cz, "nests") assert(nr == nil and why == "here")
for _, bad in {{nil, 0, "nests"}, {0, nil, "nests"}, {0/0, 0, "nests"}, {math.huge, 0, "nests"}, {0, 0, 5}} do
 local x, why2 = G.route(L, bad[1], bad[2], bad[3]) assert(x == nil and why2 == "bad_input", "junk refused")
end
local u, why3 = G.route(L, 0, cz, "nowhere") assert(u == nil and why3 == "no_station")
local far, why4 = G.route(L, 900, cz + 900, "nests") assert(far == nil and why4 == "outside", "far outside the cave")
local behind = G.route(L, pool.x, pool.z + 20 + cz, "fusion") -- a start behind the lava pool must not walk through it
if behind then for i = 2, #behind.points do
 local a, b = behind.points[i-1], behind.points[i]
 assert(not G.hitsCircle(a.x, a.z-cz, b.x, b.z-cz, pool.x, pool.z, pool.r + G.LavaMargin - 0.01), "lava respected behind the pool")
end end

-- ---- dots: cap, tiny and degenerate routes
assert(#G.dots({{x=0,z=0},{x=3,z=0}}, 24) == 2 and #G.dots({{x=0,z=0},{x=1000,z=0}}, 24) == 24 and #G.dots({{x=0,z=0},{x=1000,z=0}}, 999) == 24 and #G.dots({{x=0,z=0},{x=1000,z=0}}, 5) == 5)
assert(#G.dots({{x=2,z=2},{x=2,z=2}}, 24) == 1 and #G.dots({}, 24) == 0 and #G.dots(nil, 24) == 0 and #G.dots({{x=0,z=0},{x=50,z=0}}, nil) <= 24)
local line = G.dots({{x=0,z=0},{x=40,z=0},{x=40,z=30}}, 24)
assert(line[1].x == 0 and math.abs(line[#line].z - 30) < 1e-6 and #line == 18, "corner polyline: "..#line)

-- ---- timing: 25 s life, fade in, arrival fade, Reduce Motion
local st = G.begin("nests", 100)
local a0, f0 = G.update(st, 100, nil, false) assert(a0 == 0 and not f0, "fades in from 0")
local a1 = G.update(st, 100.4, nil, false) assert(a1 == 1, "full after 0.4 s")
local a2 = G.update(st, 110, nil, false) assert(a2 == 1)
local a3, f3 = G.update(st, 124.25, nil, false) assert(a3 > 0.4 and a3 < 0.6 and not f3, "fading at the end of life")
local a4, f4 = G.update(st, 125, nil, false) assert(a4 == 0 and f4, "gone at exactly 25 s")
local st2 = G.begin("nests", 0)
G.update(st2, 5, "potions", false) assert(st2.ended == nil, "another pad does not end it")
local b1, g1 = G.update(st2, 6, "nests", false) assert(st2.ended == 6 and b1 == 1 and not g1, "arrival starts the fade")
local b2 = G.update(st2, 6.3, nil, false) assert(b2 > 0.4 and b2 < 0.6, "keeps fading if the player steps off")
local b3, g3 = G.update(st2, 6.61, nil, false) assert(b3 == 0 and g3, "gone 0.6 s after arrival")
local sc = G.begin("nests", 0)
assert(G.update(sc, 0, nil, true) == 1 and G.update(sc, 24.9, nil, true) == 1, "calm: static, full strength")
local _, fc = G.update(sc, 25, nil, true) assert(fc)
local sc2 = G.begin("fusion", 0)
local ca, cf = G.update(sc2, 3, "fusion", true) assert(ca == 0 and cf, "calm: arrival removes the dots at once")
for i = 1, 24 do assert(G.pulse(i, 24, 12.34, true) == 1, "calm: no ripple") end
local lo, hi = 9, 0
for k = 0, 200 do local p = G.pulse(5, 24, k * 0.05, false) lo = math.min(lo, p) hi = math.max(hi, p) end
assert(lo >= 0.79 and hi <= 1.21 and hi - lo > 0.3, "gentle ripple otherwise")
assert(G.LifeSeconds == 25 and G.MaxDots == 24)

-- ---- BD-396 "Follow the glow": bigger, brighter, softer; travelling pulse (1.2 s loop); edge arrow; calm = static
local K = G.Look
assert(K.dotSize >= 1.4 and K.dotSize <= 2, "dots 1.4-2 studs")
assert(G.MinSpacing == 4 and G.MaxDots == 24, "spacing 4 studs, cap 24 parts")
assert(K.haloScale > 2 and K.haloTransparency > 0.5 and K.haloTransparency < 0.85, "soft halo, not a hard disc")
assert(K.coreScale > 0.2 and K.coreScale < 0.6 and K.lightEmission == 0.6 and K.brightness > 1, "white core, daylight brightness")
assert(G.PulseSeconds == 1.2, "pulse loops every 1.2 s")
for i = 1, 24 do
 local a, b = G.glow(i, 24, 3.3, false), G.glow(i, 24, 3.3 + G.PulseSeconds, false)
 assert(math.abs(a - b) < 1e-9, "glow loops every 1.2 s")
 assert(a >= 0.55 - 1e-9 and a <= 1 + 1e-9, "glow never fades out in daylight")
 assert(G.glow(i, 24, 7.7, true) == 0.8 and G.pulse(i, 24, 7.7, true) == 1, "calm: static")
end
local c0, c1 = G.glow(1, 24, 0, false), G.glow(2, 24, 0, false)
assert(math.abs(c0 - c1) > 1e-3, "neighbouring dots are out of phase (the pulse travels)")
-- the crest moves toward the station: the dot at the crest now is not the crest later
local function crest(t) local best, bi = -1, 0 for i = 1, 24 do local g = G.glow(i, 24, t, false) if g > best then best, bi = g, i end end return bi end
assert(crest(0) ~= crest(0.3), "crest travels along the path")
local on = G.edgeArrow(400, 300, 5, 800, 600, 40) assert(not on.visible, "station on screen: no arrow")
local right = G.edgeArrow(1500, 300, 5, 800, 600, 40) assert(right.visible and math.abs(right.x - 760) < 1e-6 and math.abs(right.y - 300) < 1e-6 and math.abs(right.angle - 90) < 1e-6, "off to the right")
local left = G.edgeArrow(-900, 300, 5, 800, 600, 40) assert(left.visible and math.abs(left.x - 40) < 1e-6 and math.abs(left.angle + 90) < 1e-6, "off to the left")
local up = G.edgeArrow(400, -900, 5, 800, 600, 40) assert(up.visible and math.abs(up.y - 40) < 1e-6 and math.abs(up.angle) < 1e-6, "above")
local down = G.edgeArrow(400, 1500, 5, 800, 600, 40) assert(down.visible and math.abs(down.y - 560) < 1e-6 and math.abs(math.abs(down.angle) - 180) < 1e-6, "below")
local behind = G.edgeArrow(400, 300, -3, 800, 600, 40) assert(behind.visible, "behind the camera still gets an arrow")
for _, bad in {{0/0, 1, 1}, {1, math.huge, 1}, {1, 1, nil}} do assert(not G.edgeArrow(bad[1], bad[2], bad[3], 800, 600, 40).visible, "junk: no arrow") end
for _, pt in {{1500, 1200}, {-300, -200}, {2000, 10}, {10, 2000}} do
 local r = G.edgeArrow(pt[1], pt[2], 5, 800, 600, 40)
 assert(r.visible and r.x >= 40 - 1e-6 and r.x <= 760 + 1e-6 and r.y >= 40 - 1e-6 and r.y <= 560 + 1e-6, "arrow stays inside the margin")
end

-- ---- decision: toggle OFF at home -> guide; ON -> travel; flag off or in a run -> as before
local function decide(over)
 local i = {caveHub=true, destination="eggs", runState="Sanctuary", teleportShops=false, remote=true, busy=false}
 for k, v in over or {} do i[k] = v end
 return R.decide(i)
end
for dest, station in R.Stations do
 local g = decide({destination=dest}) assert(g.kind == "guide" and g.station == station, "guide "..dest)
 assert(decide({destination=dest, teleportShops=true}).kind == "travel")
 assert(decide({destination=dest, caveHub=false}).kind == "open" and decide({destination=dest, caveHub=false, runState="Active"}).kind == "open", "flag off identity")
 assert(decide({destination=dest, runState="Active"}).kind ~= "guide", "in a run nothing is guided")
 assert(decide({destination=dest, remote=false}).kind == "guide", "walking needs no remote")
end
assert(decide({destination="settings"}).kind == "open" and decide({destination="potions", runState="Active"}).kind == "open")

-- ---- copy: one table, every station has a sign
local layoutIds = 0
for _, s in lay.stations do
 layoutIds += 1
 local sign = C.Signs[s.id]
 assert(sign ~= nil, "copy table has "..s.id)
 assert(sign == s.sign, "layout sign equals the copy table for "..s.id)
 assert(#sign <= C.MaxLength and #sign <= 14, "sign <= 14 characters: "..s.id)
 if s.id ~= "heart" then assert(#sign > 0, "sign not empty: "..s.id) end
 assert(C.acceptable(sign), "no numbers or jargon: "..sign)
 local words = 0 for _ in sign:gmatch("%S+") do words += 1 end
 assert(words <= 2, "one or two words: "..sign)
 assert(sign == sign:upper(), "signs are upper case like the rail")
end
local copyCount = 0 for _ in C.Signs do copyCount += 1 end
assert(copyCount == layoutIds, "copy table has no extra stations")
assert(C.acceptable(C.GuideToast) and #C.GuideToast <= 24, "toast is calm")
assert(not C.acceptable("Teleport now") and not C.acceptable("5 eggs") and not C.acceptable("Open menu") and not C.acceptable("SERVER") and not C.acceptable(5) and C.acceptable("Quiet spot"))
assert(C.sign("nests") == "NESTS" and C.sign("nope") == nil and C.sign(5) == nil)
assert(R.MinTarget == 44)
print("hub walk there: routes, lava, cap, timing, calm, decision, sign copy ok ("..routes.." routes)")
'''

def script():
    return ('local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau') + '\n'
            + 'local HubTravelClientRules=' + wrapped('src/shared/HubTravelClientRules.luau') + '\n'
            + 'local HubGuideRules=' + wrapped('src/shared/HubGuideRules.luau') + '\n'
            + 'local HubSignCopy=' + wrapped('src/shared/HubSignCopy.luau') + '\n' + LUAU)

def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_hub_walk_there.luau'; path.write_text(script())
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    for name in ('HubGuideRules', 'HubSignCopy'):
        text = (ROOT / f'src/shared/{name}.luau').read_text()
        for banned in ('Instance.new', 'game:GetService', 'Vector3', 'CFrame', 'workspace', 'os.clock', 'task.', 'require('):
            assert banned not in text, f'{name} stays pure: {banned}'
    client = (ROOT / 'src/client/HubGuideClient.luau').read_text()
    attach = client[client.index('function Client.attach'):]
    assert 'Config.CaveHub ~= true then return nil end' in attach.splitlines()[1], 'attach is a no-op with the flag off'
    assert 'for i = 1, Rules.MaxDots do' in client and client.count('Instance.new("Part")') == 1, 'one pooled loop of at most MaxDots parts'
    assert 'ensurePool()' in client and 'Rules.update(' in client and 'Settings.calm()' in client, 'rules drive the fade, Reduce Motion honoured'
    assert 'Rules.glow(' in client and 'Rules.edgeArrow(' in client and 'Rules.Look' in client, 'BD-396: halo glow, edge arrow and look come from the rules'
    assert 'Name, label.Text' in client or 'label.Text' in client, 'edge arrow label exists'
    assert 'board.Brightness' in client, 'daylight brightness set on the billboard'
    assert 'FireServer' not in client and 'InvokeServer' not in client, 'the trail is client-only feedback'
    assert 'starFour' in client and 'Assets.setCell' in client, 'uses the existing alpha FX sheet'
    travel = (ROOT / 'src/client/HubTravelClient.luau').read_text()
    assert 'Guide.attach()' in travel and 'guide.cancel()' in travel and 'guide.show(decision.station)' in travel, 'hooked through HubTravelClient'
    press = travel[travel.index('function Client.press'):]
    assert 'Config.CaveHub ~= true then return false end' in press.splitlines()[1], 'press answers false with the flag off'
    assert press.index('guide.cancel()') < press.index('Rules.decide('), 'any rail press cancels a showing trail first'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text()
    assert 'HubGuide' not in boot and 'HubSign' not in boot, 'client Bootstrap untouched (no new locals)'
    top = [l for l in boot.splitlines() if re.match(r'^local\s', l)]
    assert len(top) <= 195, 'client Bootstrap top-level locals stay at or below 195: %d' % len(top)
    # BD-292: rail buttons are 54 px high (rule floor 44) and dimmed ones keep that size
    assert 'button(rail,entry[1],7,7+(i-1)*62,172,54,' in boot, 'rail buttons are 54 px high'
    assert 'MinTarget = 44' in (ROOT / 'src/shared/HubTravelClientRules.luau').read_text()

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    print(run(args.runner))
