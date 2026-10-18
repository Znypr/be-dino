"""BD-245 (docs/115 HZ1, PROPOSAL): offline verifier for the hit ZONE shape, src/shared/HitSize.luau (zone / capsule / gap / reach).

It runs the REAL pure modules (CombatConfig, ScaleLadder, HitSize) in Luau and fails when:
  1. DEFAULT: CombatConfig.HitZoneRule is not "circle", or under the default rule HitSize.zone differs from today's (HitSize.radius, 0)
     for any of the 22 species at growth 1, 2, 3, 4 and 4.8 (flag-off identity: the proposal changes nothing until the owner flips it);
     an unknown rule name must read as "circle";
  2. CAPSULE FORMULA: radius = clamp(width / 2 x scale, 1, 20), halfSpan = clamp((length - width) / 2 x scale, 0, 32) from the
     ScaleLadder boxes (also compared to this file's own Python copy of the MEASURED boxes of verify_scale_ladder);
  3. NOT WIDER THAN THE BODY: the zone's full width 2 x radius is at most the body's real width x scale + 1 stud, and its full length
     is at most the body's real longest side x scale + 1 stud, for every species at every scale 1 to 4.8 in steps of 0.1;
  4. ORDER BY SIZE: inside a species the radius and the reach (radius + halfSpan) strictly grow with the growth scale and grow in
     proportion to it (no cap flattens growth 2 to 4.8: the failure of today's rule); across species at one growth scale, a body that is
     at least as wide AND as long has at least the radius, the reach and the area;
  5. COMPY PARITY: at growth 1 the Compy capsule reaches exactly as far along the body as today's circle (3.845) and the default rule
     returns today's radius;
  6. GAP: the planar gap to the zone surface is 0 inside, radius-aware beside the body (a point 14 studs beside an Ankylosaurus at
     growth 2, inside today's capped circle, is OUTSIDE the capsule), rotation invariant, never negative, finite for junk input;
  7. SAFETY: junk scales and unknown species cannot open a zone beyond the caps; combat stays OFF.
Not Studio evidence: combat is OFF; no bite was seen, nothing here says the proposed rule FEELS right. The owner decides.
Usage: python tools/verify_hit_zone.py --runner luau.exe [--print]   (--print writes the 6-species table of docs/115 HZ1)
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_scale_ladder import MEASURED  # noqa: E402  (width, height, length at spawn of all 22 species, Studio-measured)

TABLE_SCALES = (1, 2, 3, 4, 4.8)
MARGIN = 1.0  # studs a zone may exceed the real body (the bite range already adds BiteRangeSlack 1.5 on top)
RADIUS_MAX, SPAN_MAX, CIRCLE_MAX = 20.0, 32.0, 14.0
problems: list = []


def check(ok: bool, message: str):
    if not ok:
        problems.append(message)


def read(rel: str) -> str:
    return (SRC / rel).read_text(encoding="utf-8")


def code(rel: str) -> str:
    return "\n".join(re.sub(r"--.*$", "", line) for line in read(rel).splitlines())


def module(rel: str) -> str:
    return "(function()\n" + read(rel) + "\nend)()"


BODY = r'''
local EPS=1e-9
local IDS={%IDS%}
local TABLE_SCALES={1,2,3,4,4.8}
local MARGIN=%MARGIN%
local function boxOf(id) local r=Ladder.Dino.species[id]; return r.width,r.length end

-- 1. DEFAULT = today's rule
assert(Cfg.HitZoneRule=="circle" and HitSize.rule()=="circle","the default hit zone rule is circle")
assert(Cfg.Enabled==false,"combat stays off")
for _,id in IDS do
  for _,s in TABLE_SCALES do
    local r,span=HitSize.zone(id,s)
    assert(r==HitSize.radius(id,s) and span==0,id.." default zone is today's circle at "..s)
    local r2,span2=HitSize.zone(id,s,"no such rule")
    assert(r2==HitSize.radius(id,s) and span2==0,"an unknown rule name reads as circle")
    local r3,span3=HitSize.zoneOrFallback(id,s)
    assert(r3==r and span3==0)
  end
end
do
  local r,span=HitSize.zone("nope",2); assert(r==nil and span==nil)
  local fr,fspan=HitSize.zoneOrFallback("nope",2); assert(fr==Cfg.BodyRadiusPerScale*2 and fspan==0,"unknown species: the CombatRules fallback circle")
  local cr,cspan=HitSize.zoneOrFallback("nope",2,"capsule"); assert(cr==fr and cspan==0,"unknown species: fallback circle under the capsule rule too")
  assert(HitSize.capsule(nil,1)==nil and HitSize.capsule(42,1)==nil and HitSize.capsule({},1)==nil)
end

-- 2 + 3. CAPSULE FORMULA and NOT WIDER THAN THE BODY, every species, growth 1 to 4.8 in steps of 0.1 (plus the table scales)
local scales={}
for i=0,38 do table.insert(scales,1+i*0.1) end
for _,s in TABLE_SCALES do table.insert(scales,s) end
local lines={}
local flattened=0
for _,id in IDS do
  local w,l=boxOf(id)
  for _,s in scales do
    local r,span=HitSize.zone(id,s,"capsule")
    local r0,span0=HitSize.capsule(id,s)
    assert(r==r0 and span==span0,"zone(capsule) is capsule()")
    assert(math.abs(r-math.clamp(w/2*s,1,%RMAX%))<EPS and math.abs(span-math.clamp((l-w)/2*s,0,%SMAX%))<EPS,id.." capsule formula at "..s)
    assert(2*r<=w*s+MARGIN,id.." zone wider than the body at "..s)
    assert(2*(r+span)<=math.max(w,l)*s+MARGIN,id.." zone longer than the body at "..s)
    assert(r<%RMAX%-0.2 and span<%SMAX%-0.2,id.." a real body hits a safety cap at "..s)
    assert(r==r and span==span and r>0 and span>=0)
    -- the full body is covered lengthwise (reach equals the uncapped raw radius)
    assert(math.abs(HitSize.reach(r,span)-math.max(w,l)/2*s)<EPS,id.." reach is half the longest side at "..s)
    if HitSize.rawRadius(id,s)>HitSize.MaxRadius+EPS then flattened+=1 end
  end
  for _,s in TABLE_SCALES do
    local r,span=HitSize.capsule(id,s)
    table.insert(lines,string.format("Z %s %g %.9f %.9f %.9f %.9f",id,s,HitSize.rawRadius(id,s),HitSize.radius(id,s),r,span))
  end
end
for _,l in lines do print(l) end
print("FLATTENED "..flattened)

-- 4. ORDER BY SIZE
for _,id in IDS do
  local pr,preach=0,0
  for i=0,38 do
    local s=1+i*0.1
    local r,span=HitSize.capsule(id,s)
    local reach=HitSize.reach(r,span)
    if i>0 then assert(r>pr and reach>preach,id.." the zone must strictly grow with the scale at "..s) end
    pr,preach=r,reach
  end
  -- proportional: the zone at 4.8 is 4.8x the zone at 1 (nothing flattens it), unlike the capped circle
  local r1,sp1=HitSize.capsule(id,1)
  local r48,sp48=HitSize.capsule(id,4.8)
  assert(math.abs(r48/r1-4.8)<1e-6 and (sp1==0 or math.abs(sp48/sp1-4.8)<1e-6),id.." the zone is proportional to growth, 1 to 4.8")
  -- reliably bigger: each of the growth steps 1, 2, 3, 4, 4.8 is at least 15% wider than the one before
  local prev
  for _,s in {1,2,3,4,4.8} do
    local r=HitSize.capsule(id,s)
    if prev then assert(r>=prev*1.15,id.." each growth step is at least 15% wider in the zone") end
    prev=r
  end
end
for _,s in {1,2,3,4,4.8} do
  for _,a in IDS do
    for _,b in IDS do
      local wa,la=boxOf(a); local wb,lb=boxOf(b)
      if wa>=wb and la>=lb then
        local ra,sa=HitSize.capsule(a,s); local rb,sb=HitSize.capsule(b,s)
        assert(ra>=rb-EPS,a.." wider than "..b.." must not have the smaller radius at "..s)
        assert(HitSize.reach(ra,sa)>=HitSize.reach(rb,sb)-EPS,a.." longer than "..b.." must not reach less at "..s)
        local areaA=math.pi*ra*ra+4*ra*sa
        local areaB=math.pi*rb*rb+4*rb*sb
        assert(areaA>=areaB-1e-6,a.." bigger than "..b.." must not have the smaller zone area at "..s)
      end
    end
  end
end

-- 5. COMPY PARITY at growth 1
do
  local r,span=HitSize.capsule("compy",1)
  assert(math.abs(HitSize.reach(r,span)-HitSize.radius("compy",1))<EPS,"Compy at growth 1 reaches along the body exactly as far as today's circle")
  assert(math.abs(HitSize.radius("compy",1)-3.845)<1e-9)
  local dr,dspan=HitSize.zone("compy",1)
  assert(dr==HitSize.radius("compy",1) and dspan==0,"default rule: Compy radius is today's")
end

-- 6. GAP
do
  -- circle (no spine): distance minus radius, floored at 0
  assert(HitSize.gap(5,0,3,4,1,0)==0 and math.abs(HitSize.gap(3,0,6,8,1,0)-7)<EPS and math.abs(HitSize.gap(3,0,6,8,0,0)-7)<EPS)
  -- Ankylosaurus at growth 3 (BD-992 box: body 17.31 wide, 32.04 long, facing +X): today's capped circle is radius 14
  local r,span=HitSize.capsule("ankylosaurus",3)
  assert(math.abs(r-8.655)<1e-6 and math.abs(span-7.365)<1e-6)
  assert(HitSize.radius("ankylosaurus",3)==14)
  local oldCircleGap=HitSize.gap(14,0,0,14,1,0)
  assert(oldCircleGap==0,"today's circle hits a point 14 studs beside the middle of the body")
  local sideGap=HitSize.gap(r,span,0,14,1,0)
  assert(math.abs(sideGap-(14-r))<1e-9 and sideGap>5,"the capsule does NOT hit beside the body (gap "..sideGap..")")
  assert(HitSize.gap(r,span,0,r,1,0)<1e-9,"the flank is on the surface")
  -- the nose: past the end of the body by 2 studs
  assert(math.abs(HitSize.gap(r,span,r+span+2,0,1,0)-2)<1e-9,"2 studs past the nose is a gap of 2")
  assert(HitSize.gap(r,span,r+span-0.01,0,1,0)==0 and HitSize.gap(r,span,-(r+span-0.01),0,1,0)==0)
  assert(math.abs(HitSize.gap(r,span,-(r+span+2),0,1,0)-2)<1e-9,"the tail end is the same as the nose")
  -- a corner point: diagonal from the nose cap's centre
  local dx,dz=span+r*0.6,r*1.6
  assert(math.abs(HitSize.gap(r,span,dx,dz,1,0)-(math.sqrt((r*0.6)^2+(r*1.6)^2)-r))<1e-9)
  -- rotation invariance + never negative + monotone with distance
  local seed=7
  local function rnd() seed=(seed*1103515245+12345)%2147483648; return seed/2147483648 end
  for _=1,2000 do
    local rr,ss=0.5+rnd()*19,rnd()*24
    local px,pz=(rnd()-0.5)*120,(rnd()-0.5)*120
    local ang=rnd()*2*math.pi
    local hx,hz=math.cos(ang),math.sin(ang)
    local g=HitSize.gap(rr,ss,px,pz,hx,hz)
    assert(g>=0 and g==g)
    local th=rnd()*2*math.pi
    local c,s2=math.cos(th),math.sin(th)
    local g2=HitSize.gap(rr,ss,px*c-pz*s2,px*s2+pz*c,hx*c-hz*s2,hx*s2+hz*c)
    assert(math.abs(g-g2)<1e-6,"rotation invariant")
    assert(math.abs(g-HitSize.gap(rr,ss,px,pz,hx*7,hz*7))<1e-9,"the heading length does not matter")
    assert(math.abs(g-HitSize.gap(rr,ss,px,pz,-hx,-hz))<1e-9,"a spine has no front")
    assert(g<=math.sqrt(px*px+pz*pz)+1e-9,"the gap never exceeds the distance to the root")
    local g3=HitSize.gap(rr,ss,px*1.5,pz*1.5,hx,hz)
    assert(g3>=g-1e-9,"farther is not nearer")
  end
  for _,junk in {0/0,math.huge,-math.huge,1e300,"x"} do
    local g=HitSize.gap(5,5,junk,junk,junk,junk)
    assert(g==g and g>=0 and g<1e12,"junk input gives a finite gap")
  end
end

-- 7. SAFETY
for _,id in IDS do
  for _,junk in {0/0,-5,0,1e12,math.huge,-math.huge,"x",6,99} do
    local r,span=HitSize.capsule(id,junk)
    assert(r and r>=1 and r<=%RMAX% and span>=0 and span<=%SMAX% and r==r and span==span,"junk scale clamped")
  end
  local rLow,sLow=HitSize.capsule(id,0.1); local rOne,sOne=HitSize.capsule(id,1)
  assert(rLow==rOne and sLow==sOne,"a scale below 1 is read as 1")
end
print("hit zone passed")
'''


def luau_script() -> str:
    ids = ",".join(f'"{i}"' for i in sorted(MEASURED))
    body = (BODY.replace("%IDS%", ids).replace("%MARGIN%", str(MARGIN)).replace("%RMAX%", str(RADIUS_MAX)).replace("%SMAX%", str(SPAN_MAX)))
    parts = [
        "local M={}", "local script={Parent=M}", "local require=function(x) return x end",
        "M.CombatConfig=" + module("shared/CombatConfig.luau"),
        "M.ScaleLadder=" + module("shared/ScaleLadder.luau"),
        "M.HitSize=" + module("shared/HitSize.luau"),
        "local HitSize,Ladder,Cfg=M.HitSize,M.ScaleLadder,M.CombatConfig",
        body,
    ]
    return "\n".join(parts)


def run_luau(runner: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "hit_zone.luau"
        path.write_text(luau_script(), encoding="utf-8")
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding="utf-8")
    if result.returncode or "hit zone passed" not in result.stdout:
        print(result.stdout)
        print(result.stderr)
        problems.append("Luau behavior checks failed")
        return {}, 0
    got, flattened = {}, 0
    for line in result.stdout.splitlines():
        m = re.match(r"Z (\w+) (\S+) (\S+) (\S+) (\S+) (\S+)$", line)
        if m:
            got[(m.group(1), float(m.group(2)))] = tuple(float(m.group(i)) for i in range(3, 7))
        m = re.match(r"FLATTENED (\d+)$", line)
        if m:
            flattened = int(m.group(1))
    print("hit zone passed: 22 species x growth 1 to 4.8: capsule is the body footprint, ordered by size, default rule is today's circle")
    return got, flattened


def expected(species: str, scale: float):
    w, _h, l = MEASURED[species]
    raw = max(w, l) / 2 * scale
    return raw, min(CIRCLE_MAX, max(1.0, raw)), min(RADIUS_MAX, max(1.0, w / 2 * scale)), min(SPAN_MAX, max(0.0, (l - w) / 2 * scale))


def python_cross_check(got):
    check(len(got) == len(MEASURED) * len(TABLE_SCALES), f"expected {len(MEASURED) * len(TABLE_SCALES)} zone rows, got {len(got)}")
    for species in MEASURED:
        for scale in TABLE_SCALES:
            have = got.get((species, float(scale)))
            want = expected(species, scale)
            check(have is not None and all(abs(a - b) < 1e-6 for a, b in zip(have, want)),
                  f"{species} scale {scale}: Luau {have} differs from the ScaleLadder value {want}")


def static_checks():
    cfg = read("shared/CombatConfig.luau")
    check(re.search(r'^\s*HitZoneRule = "circle",', cfg, re.M) is not None, 'CombatConfig.HitZoneRule must default to "circle" (today\'s rule, HS1)')
    check(re.search(r"^\s*Enabled = false,", cfg, re.M) is not None, "CombatConfig.Enabled must stay false")
    check(re.search(r"^\s*CombatEnabled = false,", read("shared/Config.luau"), re.M) is not None, "Config.CombatEnabled must stay false (BD-252 gate)")
    check(f"HitCapsuleRadiusMax = {int(RADIUS_MAX)}," in cfg and f"HitCapsuleSpanMax = {int(SPAN_MAX)}," in cfg,
          "the capsule caps in CombatConfig differ from this verifier (20 / 32)")
    hs = code("shared/HitSize.luau")
    check(re.search(r"\b(game|workspace|Instance|Config|GetService|GetAttribute)\b", hs) is None, "HitSize must be pure numbers (no Instances, no Config)")
    check(set(re.findall(r"require\(script\.Parent\.(\w+)\)", hs)) == {"ScaleLadder", "CombatConfig"}, "HitSize requires only ScaleLadder and CombatConfig")


def table_rows(names):
    out = ["species | growth | today raw | today capped | capsule radius | capsule half-spine | zone W x L | body W x L"]
    for sp in names:
        for s in TABLE_SCALES:
            raw, cap, r, hs = expected(sp, s)
            w, _h, l = MEASURED[sp]
            out.append(f"{sp} | {s:g} | {raw:.2f} | {cap:.2f} | {r:.2f} | {hs:.2f} | {2 * r:.1f} x {2 * (r + hs):.1f} | {w * s:.1f} x {l * s:.1f}")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()
    static_checks()
    got, flattened = run_luau(args.runner)
    python_cross_check(got)
    if args.print:
        print("\n".join(table_rows(["compy", "stegosaurus", "ankylosaurus", "spinosaurus", "mosasaurus", "quetzalcoatlus"])))
        capped = sum(1 for v in got.values() if v[0] > CIRCLE_MAX)
        print(f"today's rule: {capped} of {len(got)} species x scale rows are above the 14 stud cap")
    if problems:
        print("verify_hit_zone FAIL")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("verify_hit_zone ok")
