# Be Dino! BD-464 step 1: ground props for tree bases and clearings (V3 style, same look as the V3 trees).
# Run headless:  blender -b -P tools/blender/build_ground_props_v3.py -- <stage> [out_dir] [shots]
#   stages: export -> write assets/blender/world/fbx_v3/ground_*_v3.fbx + WorldKitV3_GroundProps.blend + tri report
#           render -> comparison renders (version 1 current props approximated, version 2 the new props) into <out_dir>
# Every prop is shaped by hand: rocks start as a low icosphere that is lumped, chiselled with hand-placed cut planes (flat
# facets) and tidied by dissolving coplanar faces; the log, stump and mushrooms are hand-placed rings, roots, cut ends and caps;
# the bushes are hand-placed lumpy clumps with flat undersides. One vertex-colour material each (Col attribute), warm matte colours.
# 1 unit = 1 stud, Z up, pivot at the bbox bottom centre, same FBX settings as fbx_v3 (tools/blender/build_trees_v3.py).
# Scoped owner decision 2026-10-16: Blender is allowed for world art; the props must look hand-crafted, not like primitives.
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_trees_v3 as T
from build_trees_v3 import Mesh, tube, cluster, spline, shade3, bark_fn, lin, mix, V3, vc_material, tri_count, centre_xy
from build_trees_v3 import reset, world_setup, camera, place, dino_stand_in, render, ROOT

FBX_V3 = T.FBX_V3
FBX_V1 = os.path.join(ROOT, "assets", "blender", "world", "fbx")

# ---------------------------------------------------------------- palette (docs/114: warm, matte; stones lean warm grey, not slate)
STONE_LO, STONE_MID, STONE_HI = lin("#6F6558"), lin("#928672"), lin("#B2A68E")
STONE_LIGHT_LO, STONE_LIGHT_MID, STONE_LIGHT_HI = lin("#7E7262"), lin("#A39679"), lin("#C2B592")
MOSS_LO, MOSS_MID, MOSS_HI = lin("#4E7E3A"), lin("#69973F"), lin("#88B050")
WOOD_HI, WOOD_MID, WOOD_LO = lin("#E6C894"), lin("#D0A66C"), lin("#A67A46")
CAP_LO, CAP_MID, CAP_HI = lin("#C24E34"), lin("#E26B42"), lin("#F2905A")
HONEY_LO, HONEY_MID, HONEY_HI = lin("#C98B2E"), lin("#E8B04A"), lin("#F6CF74")
SPOT, STEM_HI, STEM_LO = lin("#FFF1D6"), lin("#F5E8CC"), lin("#D8C39A")
BERRY = lin("#D9505E")
BUSH_B_LO, BUSH_B_MID, BUSH_B_HI = lin("#3F8F4E"), lin("#66AE56"), lin("#92CB6C")

def rot_z(v, a):
    c, s = math.cos(a), math.sin(a)
    return Vector((v.x * c - v.y * s, v.x * s + v.y * c, v.z))

# ---------------------------------------------------------------- shape helpers
def rock(center, radii, seed, subdiv, cuts, amp=.05, flat=.55, yaw=0.0, tol=math.radians(9)):
    """sculpted stone: lumpy low icosphere, stretched, chiselled by hand-placed cut planes (normal, distance as fraction of the
    radius along that normal), flat sunk bottom, then coplanar faces dissolved into clean facets."""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    rnd = random.Random(seed)
    for v in bm.verts:
        p = v.co.copy() * (1 + rnd.uniform(-amp, amp))
        p = Vector((p.x * radii[0], p.y * radii[1], p.z * radii[2]))
        for n, d in cuts:
            n = Vector(n).normalized(); lim = d * (abs(n.x) * radii[0] + abs(n.y) * radii[1] + abs(n.z) * radii[2])
            k = p.dot(n) - lim
            if k > 0: p = p - n * k
        if p.z < -flat * radii[2]: p.z = -flat * radii[2]
        v.co = p
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=radii[0] * .035)
    bmesh.ops.dissolve_limit(bm, angle_limit=tol, verts=bm.verts, edges=bm.edges)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    verts = [rot_z(v.co, yaw) + center for v in bm.verts]
    faces = [tuple(v.index for v in f.verts) for f in bm.faces if len(f.verts) >= 3]
    bm.free()
    return verts, faces, [center]

def stone_colfn(zlo, zhi, light=False, moss=False, mossy_amt=.5, seed=0):
    lo, mid, hi = (STONE_LIGHT_LO, STONE_LIGHT_MID, STONE_LIGHT_HI) if light else (STONE_LO, STONE_MID, STONE_HI)
    base = shade3(lo, mid, hi, zlo, zhi, .6)
    def f(p, n):
        c = base(p, n)
        if moss:
            m = n.z * .9 + .45 * noise.noise(Vector((p.x * .55 + seed, p.y * .55, p.z * .6))) + (p.z - zlo) / max(zhi - zlo, 1e-6) * .35
            if m > 1.12 - mossy_amt * .5:
                return mix(MOSS_LO, MOSS_HI, n.z * .5 + .35 + .3 * noise.noise(Vector((p.x * 1.3, p.y * 1.3, seed))))
        return c
    return f

def lump_moss(M, center, radii, seed, subdiv=1):
    v, f, ref = cluster(Vector(center), radii, seed, amp=.18, flat_bottom=.25, subdiv=subdiv)
    M.add(v, f, ref, shade3(MOSS_LO, MOSS_MID, MOSS_HI, center[2] - radii[2], center[2] + radii[2], .7), jit=.03, seed=seed)

def gem(center, r, squash=1.0):
    """tiny faceted nugget: 6 verts, 8 triangles (berries)"""
    c = Vector(center); a = r
    verts = [c + Vector(p) for p in [(a, 0, 0), (-a, 0, 0), (0, a, 0), (0, -a, 0), (0, 0, a * squash), (0, 0, -a * squash * .6)]]
    faces = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    return verts, faces, [c]

# =============================================================== V3 GROUND PROPS
def build_rock_small():
    """~2 studs, a pebble-stone with two flat chisel faces and a leaning top; slightly warmer / paler stone"""
    M = Mesh()
    cuts = [((.5, -.8, .55), .78), ((-.9, .35, .3), .8), ((.15, .9, .5), .86)]
    v, f, ref = rock(Vector((0, 0, .7)), (1.4, 1.12, .98), 3, 2, cuts, amp=.06, flat=.25, yaw=.5, tol=math.radians(9))
    M.add(v, f, ref, stone_colfn(-.2, 1.3), jit=.04, seed=3)
    return M

def build_rock_medium():
    """~4.4 studs, chunky boulder with a broad sloped top, three big chisel facets and a chipped corner"""
    M = Mesh()
    cuts = [((1, .15, .55), .8), ((-.7, .9, .4), .78), ((.25, -1, .5), .78), ((-1, -.55, .35), .82), ((.1, .2, 1), .68), ((.8, -.8, .2), .84), ((-.2, .55, .95), .8)]
    v, f, ref = rock(Vector((0, 0, 1.0)), (2.35, 1.85, 1.5), 8, 3, cuts, amp=.05, flat=.45, yaw=-.35)
    M.add(v, f, ref, stone_colfn(-.5, 2.6), jit=.04, seed=8)
    # a small second stone leaning on it
    v, f, ref = rock(Vector((1.9, -1.25, .35)), (.9, .75, .55), 15, 2, [((.6, .2, .8), .72), ((-.4, -.9, .3), .8)], amp=.05, flat=.3, yaw=.9, tol=math.radians(9))
    M.add(v, f, ref, stone_colfn(-.1, .9), jit=.04, seed=9)
    return M

def build_rock_mossy():
    """~5.2 studs, the big mossy boulder: tall back, flat-faced front, a moss cap and a green skirt on the low side"""
    M = Mesh()
    cuts = [((1, -.3, .45), .8), ((-1, .45, .35), .8), ((.1, -1, .4), .8), ((-.2, 1, .6), .78), ((.2, .1, 1), .74), ((.7, .9, .4), .84), ((-.8, -.7, .5), .82)]
    v, f, ref = rock(Vector((0, 0, 1.2)), (2.7, 2.15, 1.85), 21, 3, cuts, amp=.05, flat=.4, yaw=.3)
    M.add(v, f, ref, stone_colfn(-.6, 3.1, moss=True, mossy_amt=.55, seed=5), jit=.035, seed=21)
    lump_moss(M, (-.7, .35, 2.55), (1.7, 1.35, .75), 31)
    lump_moss(M, (1.75, -1.5, .3), (1.1, .9, .6), 32)
    return M

def build_log():
    """~7.3 studs fallen log: slightly bent, uneven radius, flat sit on the ground, a carved-in cut end with growth rings,
    a jagged broken end, a snapped branch stub and two moss patches"""
    M = Mesh(); R = random.Random(41)
    n = 8; xs = [-3.6, -2.2, -.7, .8, 2.3, 3.6]
    rad = [1.05, 1.17, 1.22, 1.12, 1.18, 1.0]
    yc = [.15, -.05, -.3, -.2, .1, .35]
    def zc(i): return rad[i] * .84
    rings = []
    for k, x in enumerate(xs):
        ring = []
        for i in range(n):
            a = 2 * math.pi * (i + .5) / n
            r = rad[k] * (1 + R.uniform(-.07, .07))
            ring.append(Vector((x, yc[k] + math.cos(a) * r, max(0.0, zc(k) + math.sin(a) * r * .88))))
        rings.append(ring)
    verts = [p for ring in rings for p in ring]
    faces = [(k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i) for k in range(len(xs) - 1) for i in range(n)]
    bk = bark_fn(0, 2.6)
    ref = [Vector((xs[k], yc[k], zc(k))) for k in range(len(xs))]
    def logcol(p, nn):
        c = bk(p, nn)
        return c * (.8 + .4 * (noise.noise(Vector((p.x * .8, p.y * 1.6, p.z * 1.6))) * .5 + .5))
    M.add(verts, faces, ref, logcol, jit=.03, seed=2)
    # cut end (x = -3.6): recessed dish with two rings
    cx, cy, cz = xs[0], yc[0], zc(0)
    outer = rings[0]
    inner = [Vector((cx + .22 + R.uniform(-.04, .04), cy + (p.y - cy) * .66, cz + (p.z - cz) * .66)) for p in outer]
    mid = [Vector((cx + .30, cy + (p.y - cy) * .30, cz + (p.z - cz) * .30)) for p in outer[::2]]
    centre = Vector((cx + .42, cy, cz))
    ev = outer + inner + mid + [centre]
    ef = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for q in range(4):
        a_, b_, c_ = n + 2 * q, n + 2 * q + 1, n + (2 * q + 2) % n
        m, m1 = 2 * n + q, 2 * n + (q + 1) % 4
        ef += [(a_, b_, m), (b_, c_, m), (c_, m1, m)]
    ef += [(2 * n + q, 2 * n + (q + 1) % 4, 2 * n + 4) for q in range(4)]
    def endcol(c0):
        def f(p, nn):
            r = math.hypot(p.y - c0[0], p.z - c0[1]) / 1.15
            if r > .9: return bk(p, nn) * .95
            if r > .62: return WOOD_HI
            if r > .38: return WOOD_MID * .96
            return WOOD_LO * 1.05
        return f
    M.add(ev, ef, [Vector((cx - 1.2, cy, cz))], endcol((cy, cz)), jit=.02, seed=4)
    # broken end (x = 3.6): jagged zig-zag rim, fan to a pushed-in centre
    cx2, cy2, cz2 = xs[-1], yc[-1], zc(-1)
    last = rings[-1]
    jag = [Vector((cx2 + (.62 if i % 2 == 0 else -.1) + R.uniform(-.1, .1), p.y, p.z)) for i, p in enumerate(last)]
    c2 = Vector((cx2 - .05, cy2, cz2 + .05))
    bv = last + jag + [c2]
    bf = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)] + [(n + i, n + (i + 1) % n, 2 * n) for i in range(n)]
    def brokencol(p, nn):
        return mix(WOOD_MID, WOOD_HI, max(0, min(1, (p.x - cx2 + .2) * 1.2))) if nn.x > .25 else bk(p, nn)
    M.add(bv, bf, [Vector((cx2 - 1.5, cy2, cz2))], brokencol, jit=.03, seed=5)
    # branch stub on the upper back, snapped off
    base = Vector((-.9, -.3 - .1, 1.85)); d = Vector((.25, -.55, .85)).normalized()
    pth = [base - d * .25, base + d * .45, base + d * 1.2 + Vector((.15, 0, 0))]
    v, f, rf = tube(pth, [.46, .36, .27], 5, tip=False, seed=3, wob=.1)
    M.add(v, f, rf, lambda p, nn: WOOD_MID if nn.dot(d) > .8 else bk(p, nn), seed=6)
    lump_moss(M, (1.0, -.25, 1.95), (1.5, .7, .45), 51, subdiv=1)
    lump_moss(M, (-2.2, .4, 1.85), (.8, .55, .4), 52, subdiv=1)
    return M

def build_stump():
    """~5.4 studs across with roots: flared bark trunk, an uneven chopped top showing growth rings, four roots of different
    length that dive into the ground, a moss tuft on one side"""
    M = Mesh(); R = random.Random(61)
    n = 9
    prof = [(-.25, 2.1), (.45, 1.7), (1.25, 1.5), (2.0, 1.42)]
    rings = []
    for k, (z, r) in enumerate(prof):
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n + k * .12
            rr = r * (1 + R.uniform(-.09, .09) + (.12 if (i in (1, 4, 7) and k < 2) else 0))
            zz = z + (R.uniform(-.1, .1) if k == len(prof) - 1 else 0) + (.18 * math.cos(a - .9) if k == len(prof) - 1 else 0)
            ring.append(Vector((math.cos(a) * rr, math.sin(a) * rr, zz)))
        rings.append(ring)
    verts = [p for ring in rings for p in ring]
    faces = [(k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i) for k in range(len(prof) - 1) for i in range(n)]
    bk = bark_fn(-.2, 2.1)
    M.add(verts, faces, [Vector((0, 0, 1.0))], bk, jit=.03, seed=7)
    top = rings[-1]; tz = sum(p.z for p in top) / n
    inner = [Vector((p.x * .72, p.y * .72, p.z - .1 + R.uniform(-.03, .03))) for p in top]
    core = [Vector((p.x * .36, p.y * .36, p.z - .2)) for p in top[::3]]
    ctr = Vector((.05, -.04, tz - .32))
    tv = top + inner + core + [ctr]
    tf = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for q in range(3):
        a_, b_, c_, d_ = n + q * 3, n + q * 3 + 1, n + q * 3 + 2, n + (q * 3 + 3) % n
        m0, m1 = 2 * n + q, 2 * n + (q + 1) % 3
        tf += [(a_, b_, m0), (b_, c_, m0), (c_, d_, m1, m0)]
    tf += [(2 * n + q, 2 * n + (q + 1) % 3, 2 * n + 3) for q in range(3)]
    def topcol(p, nn):
        r = math.hypot(p.x, p.y) / 1.42
        if r > .96: return bk(p, nn) * .95
        if r > .68: return WOOD_HI
        if r > .42: return WOOD_MID
        return WOOD_LO * 1.05
    M.add(tv, tf, [Vector((0, 0, tz - 1.5))], topcol, jit=.02, seed=8)
    # roots: uneven lengths and thickness, arching out of the flare and diving into the soil
    for ang, ln, th in [(25, 2.6, .82), (118, 2.0, .7), (205, 2.4, .76), (292, 1.7, .62)]:
        a = math.radians(ang); d = Vector((math.cos(a), math.sin(a), 0))
        pth = [d * 1.0 + Vector((0, 0, 1.15)), d * (1.0 + ln * .5) + Vector((0, 0, .45)), d * (1.25 + ln) + Vector((0, 0, -.55))]
        v, f, rf = tube(pth, [th * 1.25, th * .8, th * .5], 5, tip=False, seed=ang, wob=.12, squash=.62)
        M.add(v, f, rf, bk, seed=ang)
    lump_moss(M, (-.7, 1.25, .3), (.8, .7, .45), 62, subdiv=1)
    return M

def mushroom(M, base, h, rcap, seed, kind, tilt=(0, 0), sides=6, yaw=0.0):
    """one stalk (curved tapered tube) + a hand-lathed dome cap with a darker underside; spots are colour only"""
    R = random.Random(seed); base = Vector(base)
    lean = Vector((tilt[0], tilt[1], 0))
    pth = [base + Vector((0, 0, -.1)), base + lean * .35 + Vector((0, 0, h * .55)), base + lean + Vector((0, 0, h))]
    rs = rcap * .3
    v, f, rf = tube(pth, [rs * 1.12, rs * .82, rs * .72], 5, tip=False, seed=seed, wob=.05)
    M.add(v, f, rf, lambda p, n: mix(STEM_LO, STEM_HI, max(0, min(1, (p.z - base.z) / h * .8 + n.z * .2))), jit=.02, seed=seed)
    lo, mid, hi = (CAP_LO, CAP_MID, CAP_HI) if kind == 'red' else (HONEY_LO, HONEY_MID, HONEY_HI)
    top = pth[-1]; ch = rcap * .72
    profile = [(0, ch), (rcap * .5, ch * .86), (rcap, ch * .36), (rcap * .88, -ch * .02)]
    ringv = []
    for (rr, zz) in profile[1:]:
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + (.5 if rr == profile[2][0] else 0)) / sides + yaw
            r2 = rr * (1 + R.uniform(-.1, .1))
            ring.append(top + Vector((math.cos(a) * r2, math.sin(a) * r2, zz + R.uniform(-.04, .04))))
        ringv.append(ring)
    pole = top + Vector((R.uniform(-.1, .1) * rcap, R.uniform(-.1, .1) * rcap, ch))
    under = top + Vector((0, 0, ch * .02))
    verts = [pole] + [p for ring in ringv for p in ring] + [under]
    S = sides
    iu = 1 + 3 * S
    faces = []
    for i in range(S):
        j = (i + 1) % S
        faces.append((0, 1 + i, 1 + j))
        faces.append((1 + i, 1 + S + i, 1 + S + j, 1 + j))
        faces.append((1 + S + i, 1 + 2 * S + i, 1 + 2 * S + j, 1 + S + j))
        faces.append((iu, 1 + 2 * S + j, 1 + 2 * S + i))
    start = len(M.f)
    cf = shade3(lo, mid, hi, top.z, top.z + ch, .55)
    def capcol(p, nn):
        if nn.z < -.2: return STEM_LO * .8                      # gills side
        return cf(p, nn)
    M.add(verts, faces, [top + Vector((0, 0, -ch))], capcol, jit=.02, seed=seed)
    if kind == 'red':  # cream spots: some quads of the upper rings and one top triangle
        for k, fc in enumerate(range(start, len(M.f))):
            if k % 4 == 1 and k // 4 in (0, 3): M.c[fc] = [SPOT * .98 for _ in M.c[fc]]
            elif k % 4 == 0 and k // 4 in (5,): M.c[fc] = [SPOT * .98 for _ in M.c[fc]]

def build_mushrooms():
    """cluster of five: one tall red cap, two mid ones leaning apart, a honey-coloured pair; low moss mound at the base"""
    M = Mesh()
    mushroom(M, (0, 0, 0), 1.7, 1.35, 71, 'red', (.2, -.1), yaw=.3)
    mushroom(M, (1.6, .6, 0), 1.1, .95, 72, 'honey', (.25, .1), yaw=.7)
    mushroom(M, (-1.25, .85, 0), 1.25, 1.0, 73, 'red', (-.3, .15), yaw=.1)
    mushroom(M, (.6, -1.25, 0), .75, .68, 74, 'honey', (.1, -.2), sides=5, yaw=.4)
    mushroom(M, (-.6, -1.35, 0), .55, .48, 75, 'red', (-.12, -.1), sides=5, yaw=.9)
    lump_moss(M, (.1, .2, -.05), (2.0, 1.55, .3), 76, subdiv=1)
    return M

def build_bush_round():
    """~4.6 x 2.7 studs, tree-base bush: four unequal lumpy clumps (tall back, two side, low front), flat undersides, a twig"""
    M = Mesh()
    clumps = [((-.5, .35, 1.35), (1.8, 1.55, 1.25), 1), ((1.25, -.2, .9), (1.5, 1.3, .95), 2), ((-1.75, -.55, .72), (1.15, 1.05, .78), 3), ((.1, -1.2, .58), (1.15, 1.0, .65), 4)]
    for c, r, s in clumps:
        cf = shade3(V3['leaf_lo'], V3['leaf_mid'], V3['leaf_hi'], c[2] - r[2], c[2] + r[2], .62)
        v, f, ref = cluster(Vector(c), r, 140 + s, amp=.24, flat_bottom=.4, subdiv=2)
        M.add(v, f, ref, cf, jit=.04, seed=s)
    bk = bark_fn(0, 1.4)
    v, f, rf = tube([Vector((.7, -.8, .0)), Vector((.95, -1.05, .5)), Vector((1.3, -1.55, .95))], (.2, .1), 4, tip=True, seed=5)
    M.add(v, f, rf, bk, seed=9)
    return M

def build_bush_berry():
    """~4.8 x 2.2 studs, low spreading berry bush for clearings: three flatter wide clumps in a warmer green and eight berries"""
    M = Mesh()
    clumps = [((.1, .1, .85), (2.05, 1.65, .95), 1), ((-1.7, -.6, .55), (1.4, 1.2, .65), 2), ((1.6, -.85, .5), (1.35, 1.1, .6), 3)]
    for c, r, s in clumps:
        cf = shade3(BUSH_B_LO, BUSH_B_MID, BUSH_B_HI, c[2] - r[2], c[2] + r[2], .62)
        v, f, ref = cluster(Vector(c), r, 160 + s, amp=.22, flat_bottom=.35, subdiv=2)
        M.add(v, f, ref, cf, jit=.04, seed=s)
    for i, (x, y, z) in enumerate([(-.6, -1.3, .95), (.5, -1.55, .8), (1.9, -1.7, .75), (-2.3, -1.4, .62), (.9, .9, 1.75), (-.9, .55, 1.85), (2.4, -.3, .85), (-1.5, .6, 1.2)]):
        v, f, ref = gem((x, y, z), .36 + (i % 3) * .04, 1.0)
        M.add(v, f, ref, lambda p, n: BERRY * (.82 + .3 * (n.z * .5 + .5)), jit=.015, seed=i)
    return M

PROPS = {
    'rock_small': ('ground_rock_small_v3', build_rock_small),
    'rock_medium': ('ground_rock_medium_v3', build_rock_medium),
    'rock_mossy': ('ground_rock_mossy_v3', build_rock_mossy),
    'log': ('ground_log_fallen_v3', build_log),
    'stump': ('ground_stump_roots_v3', build_stump),
    'mushrooms': ('ground_mushrooms_v3', build_mushrooms),
    'bush_round': ('ground_bush_round_v3', build_bush_round),
    'bush_berry': ('ground_bush_berry_v3', build_bush_berry),
}

# =============================================================== CURRENT (version 1) approximation, from the island screenshots
CUR = dict(
    rock_lo=lin("#7D8A78"), rock_hi=lin("#A9B3A0"), moss=lin("#78A85A"),
    bush_lo=lin("#4FB88F"), bush_hi=lin("#8AE3B9"),
)
def cur_rock(scale=1.0, seed=1):
    """the generated round mossy boulder: a rounded lumpy blob, cool grey-green, green top"""
    M = Mesh()
    v, f, ref = cluster(Vector((0, 0, 1.0 * scale)), (2.3 * scale, 2.0 * scale, 1.35 * scale), seed, amp=.1, flat_bottom=.5, subdiv=1)
    def col(p, n):
        c = mix(CUR['rock_lo'], CUR['rock_hi'], n.z * .5 + .5)
        return mix(c, CUR['moss'], max(0, n.z - .35) * 1.2)
    M.add(v, f, ref, col, jit=.02, seed=seed)
    return M
def cur_bush():
    """the generated bush: two or three smooth mint puffs"""
    M = Mesh()
    for c, r, s in [((0, 0, 1.0), (1.7, 1.5, 1.05), 1), ((1.5, .3, .7), (1.1, 1.0, .75), 2), ((-1.4, -.4, .65), (1.0, .95, .7), 3)]:
        cf = shade3(CUR['bush_lo'], (CUR['bush_lo'] + CUR['bush_hi']) * .5, CUR['bush_hi'], c[2] - r[2], c[2] + r[2], .6)
        v, f, ref = cluster(Vector(c), r, 190 + s, amp=.06, flat_bottom=.5, subdiv=2); M.add(v, f, ref, cf, jit=.015, seed=s)
    return M
def cur_mush():
    """the kit mushroom clump (assets/blender/world/fbx/world_mushrooms_a.fbx, 60 tris), imported as is"""
    return None

def import_kit(fname):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX_V1, fname))
    ob = [o for o in bpy.data.objects if o not in before and o.type == 'MESH'][0]
    for o in list(bpy.data.objects):
        if o not in before and o.type != 'MESH': bpy.data.objects.remove(o)
    ob.data.materials.clear(); ob.data.materials.append(vc_material()); ob.rotation_euler = (0, 0, 0); ob.parent = None
    return ob

# =============================================================== stages
def make_prop(key):
    name, fn = PROPS[key]
    ob = fn().to_object(name, flat=True)
    ob.data.materials.append(vc_material())
    centre_xy(ob)
    return ob

def stage_export():
    os.makedirs(FBX_V3, exist_ok=True)
    reset()
    obs = []; x = 0
    for key in PROPS:
        ob = make_prop(key); ob.location = (x, 0, 0); x += 12; obs.append(ob)
        d = ob.dimensions
        print("REPORT", ob.name, "tris", tri_count(ob), "verts", len(ob.data.vertices), "size", [round(d.x, 2), round(d.y, 2), round(d.z, 2)], "materials", len(ob.data.materials))
    for ob in obs:
        for o in bpy.context.selected_objects: o.select_set(False)
        loc = ob.location.copy(); ob.location = (0, 0, 0); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(FBX_V3, ob.name + ".fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, axis_forward="-Z", axis_up="Y", colors_type="SRGB", mesh_smooth_type="FACE",
                                 add_leaf_bones=False, bake_anim=False)
        ob.location = loc; ob.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "assets", "blender", "world", "WorldKitV3_GroundProps.blend"))

# grouping around the tree base: (prop key, screen-x, screen-depth, yaw, scale). Hand-placed in SCREEN coordinates of the render camera
# (x to the right, depth towards the camera, tree trunk at 0,0) so nothing overlaps or hides the dino; converted to world X/Y below.
CAM_AZIM = 28.0
def screen_to_world(sx, sd):
    a = math.radians(CAM_AZIM)
    return (sx * math.cos(a) + sd * math.sin(a), sx * math.sin(a) - sd * math.cos(a))
V2_GROUP = [
    ('stump', 4.8, 1.6, .5, 1.0), ('log', -6.8, -.6, .35, 1.0), ('rock_medium', 8.6, 4.6, .6, 1.0), ('rock_small', 5.2, 6.4, 1.9, 1.0),
    ('rock_small', -1.4, 6.0, .2, .85), ('rock_mossy', -10.8, -3.6, 2.4, 1.0), ('mushrooms', -1.6, 3.8, .5, 1.0),
    ('bush_round', -3.6, -4.6, .4, 1.0), ('bush_berry', 4.4, -5.0, -.3, 1.0), ('mushrooms', 9.8, -.6, 2.2, .75),
]
# version 1: what the island has around a tree base today (round boulders, mint puff bushes, the kit mushroom clump); no logs, no stumps.
# Same slots as version 2 where the same kind of prop sits (rocks, bushes, one mushroom clump); the other slots stay empty.
V1_GROUP = [
    ('cur_rock', 8.6, 4.6, .6, 1.0), ('cur_rock', 5.2, 6.4, 1.9, .5), ('cur_rock', -10.8, -3.6, 2.4, 1.2),
    ('cur_bush', -3.6, -4.6, .4, 1.0), ('cur_bush', 4.4, -5.0, -.3, .9), ('cur_mush', -1.6, 3.8, .5, 1.0),
]

def build_group(version):
    ob = T.make(T.build_broadleaf, "tree"); centre_xy(ob); place(ob, (0, 0, 0), .6)
    cache = {}
    group = V2_GROUP if version == 'v2' else V1_GROUP
    tris = 0
    for key, x, y, yaw, s in group:
        if key not in cache:
            if key == 'cur_rock': cache[key] = T.make(lambda: cur_rock(1.0), "cur_rock")
            elif key == 'cur_bush': cache[key] = T.make(cur_bush, "cur_bush")
            elif key == 'cur_mush': cache[key] = import_kit("world_mushrooms_a.fbx")
            else: cache[key] = make_prop(key)
            if key.startswith('cur_') and key != 'cur_mush': centre_xy(cache[key])
            first = True
        else:
            first = False
        base = cache[key]
        if first: o = base
        else:
            o = base.copy(); bpy.context.scene.collection.objects.link(o)
        wx, wy = screen_to_world(x, y)
        o.location = (wx, wy, 0); o.rotation_euler = (0, 0, yaw + math.radians(CAM_AZIM)); o.scale = (s, s, s)
        tris += tri_count(base)
    return tris

SHOTS = {
    # name: (distance, dino scale)
    'play25-spawn': (25, 1.0), 'play25-big': (25, 1.5), 'play40-spawn': (40, 1.0), 'play40-big': (40, 1.5),
}
def stage_render(out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    res = (1600, 900)
    counts = {}
    for version in ('v1', 'v2'):
        for shot, (dist, ds) in SHOTS.items():
            if only and shot not in only: continue
            sc = reset(); world_setup(sc, res); sc.cycles.samples = 48
            n = build_group(version)
            dino_stand_in((-6.5, -9.5, 0), math.radians(35), ds)
            counts[version] = n
            camera(sc, (0.5, -1.0, 2.6), dist, 17, CAM_AZIM, res=res)
            render(sc, os.path.join(out_dir, f"_{version}_{shot}.png"))
            print("RENDERED", version, shot, n)
    if counts:
        open(os.path.join(out_dir, "tris.txt"), "w").write("".join(f"{k} {v}" + chr(10) for k, v in counts.items()))
    if not only or 'lineup' in only:
        widths = {'rock_small': 3.4, 'rock_medium': 6, 'rock_mossy': 6.8, 'log': 8.6, 'stump': 7.6, 'mushrooms': 5.2, 'bush_round': 6.4, 'bush_berry': 6.6,
                  'cur_rock': 6, 'cur_bush': 5, 'cur_mush': 3}
        rows = {'v2': [['rock_small', 'rock_medium', 'rock_mossy', 'log'], ['stump', 'mushrooms', 'bush_round', 'bush_berry']],
                'v1': [['cur_rock', 'cur_rock', 'cur_bush', 'cur_mush']]}
        for version in ('v1', 'v2'):
            sc = reset(); world_setup(sc, res); sc.cycles.samples = 48
            for ri, row in enumerate(rows[version]):
                total = sum(widths[k] + 1.6 for k in row); x = -total / 2
                for k in row:
                    if k == 'cur_rock': ob = T.make(lambda: cur_rock(1.0), "cur_rock"); centre_xy(ob)
                    elif k == 'cur_bush': ob = T.make(cur_bush, "cur_bush"); centre_xy(ob)
                    elif k == 'cur_mush': ob = import_kit("world_mushrooms_a.fbx")
                    else: ob = make_prop(k)
                    w = widths[k]; ob.location = (x + w / 2, -ri * 9.0 + (4.5 if len(rows[version]) > 1 else 0), 0); x += w + 1.6
            camera(sc, (0, 0, 1.2), 34, 24, 0, fov=45, res=res)
            render(sc, os.path.join(out_dir, f"_{version}_lineup.png"))
            print("RENDERED", version, "lineup")

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[0] if argv else "export"
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs", "evidence", "2026-10-16-props")
    only = argv[2].split(",") if len(argv) > 2 else None
    if stage == "export": stage_export()
    elif stage == "render": stage_render(out, only)
