# Be Dino! tree asset-quality test, v3 redesigns of the three main families (broadleaf, conifer, palm).
# Run headless:  blender -b -P tools/blender/build_trees_v3.py -- <stage> [out_dir]
#   stages: export  -> write assets/blender/world/fbx_v3/*.fbx + WorldKitV3_Trees.blend + tri report
#           render  -> render the comparison panels into <out_dir> (current approximation vs V2 vs V3)
# Geometry is authored shape by shape from hand-placed branch paths, cluster centres and frond curves (no scatter, no
# generators), then painted with flat per-face vertex colours in ONE material. 1 unit = 1 stud, Z up in Blender
# (the FBX export uses the same axis settings as tools/blender/build_world_kit.py).
# NOTE (owner 2026-10-15 3D model rule): scripted modelling is the thing the owner called "3D Microsoft Paint".
# These meshes are a TEST so the owner can judge them next to the Roblox-generated meshes; they are not approved art.
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FBX_V2 = os.path.join(ROOT, "assets", "blender", "world", "fbx_v2")
FBX_V3 = os.path.join(ROOT, "assets", "blender", "world", "fbx_v3")

# ---------------------------------------------------------------- palette (handbook 5.8 Grass #84AA54 / LeafyGrass #3E7C4E,
# pulled slightly towards mint and slightly less saturated for the v3 foliage)
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return Vector([x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c])

def mix(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))

GROUND = lin("#84AA54")
V3 = dict(
    leaf_hi=lin("#80BF72"), leaf_mid=lin("#58A862"), leaf_lo=lin("#37824F"),
    pine_hi=lin("#4F9E78"), pine_mid=lin("#33795A"), pine_lo=lin("#1F5440"),
    palm_hi=lin("#7FC672"), palm_mid=lin("#4FA55F"), palm_lo=lin("#33804E"),
    bark_hi=lin("#B07E55"), bark_mid=lin("#8A5E3E"), bark_lo=lin("#5E3F2C"),
    palm_bark_hi=lin("#B98557"), palm_bark_lo=lin("#7A5230"), nut=lin("#7A5232"),
)
# "current in-game" approximation: more saturated, flatter, as in the island screenshots
CUR = dict(
    leaf_hi=lin("#79B23E"), leaf_lo=lin("#4C8A2C"), pine_hi=lin("#3C7A46"), pine_lo=lin("#2A5733"),
    bark=lin("#7A5030"), palm_hi=lin("#5DB43E"), palm_lo=lin("#3E8C2C"),
)

# ---------------------------------------------------------------- tiny mesh builder (verts, faces, per-corner colours)
class Mesh:
    def __init__(self): self.v = []; self.f = []; self.c = []

    def add(self, verts, faces, ref, colfn, jit=.03, seed=0):
        """verts: list[Vector]; faces: list[tuple]; ref: list[Vector] reference points, faces are flipped to face away from the
        nearest one; colfn(pos, normal) -> linear rgb Vector."""
        base = len(self.v)
        for fc in faces:
            pts = [verts[i] for i in fc]
            cen = sum(pts, Vector()) / len(pts)
            n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
            if n.length < 1e-9: continue
            n.normalize()
            r = min(ref, key=lambda q: (q - cen).length_squared)
            if n.dot(cen - r) < 0: fc = tuple(reversed(fc)); n = -n
            self.f.append(tuple(base + i for i in fc))
            j = noise.noise(cen * 1.7 + Vector((seed, seed * .7, 0))) * jit
            self.c.append([colfn(verts[i], n) + Vector((j, j, j)) for i in fc])
        self.v.extend(verts)

    def tris(self): return sum(len(f) - 2 for f in self.f)

    def to_object(self, name, flat=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.v], [], self.f)
        me.update(calc_edges=True)
        ca = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
        k = 0
        for p, cols in zip(me.polygons, self.c):
            p.use_smooth = not flat
            for li, c in zip(p.loop_indices, cols):
                ca.data[li].color = (max(0, min(1, c.x)), max(0, min(1, c.y)), max(0, min(1, c.z)), 1.0)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

# ---------------------------------------------------------------- shape helpers
def tube(path, radii, sides=6, tip=True, seed=0, wob=0.0, squash=1.0, phase=0.0):
    """tapered tube along a hand-placed path; radii per path point (list or (r0, r1)); returns verts, faces, ring centres"""
    n = len(path)
    if isinstance(radii, tuple): radii = [radii[0] + (radii[1] - radii[0]) * i / (n - 1) for i in range(n)]
    elif len(radii) != n:  # key radii spread evenly along the path
        keys = radii; radii = []
        for i in range(n):
            t = i / (n - 1) * (len(keys) - 1); a = min(int(t), len(keys) - 2); radii.append(keys[a] + (keys[a + 1] - keys[a]) * (t - a))
    verts = []; faces = []; N = None
    for k, p in enumerate(path):
        T = (path[min(k + 1, n - 1)] - path[max(k - 1, 0)]).normalized()
        if N is None:
            N = T.cross(Vector((0, 0, 1)))
            if N.length < .1: N = T.cross(Vector((1, 0, 0)))
            N.normalize()
        else:
            N = (N - T * N.dot(T)).normalized()
        B = T.cross(N)
        for i in range(sides):
            a = 2 * math.pi * (i + phase) / sides
            r = radii[k] * (1 + wob * noise.noise(Vector((seed + i * 1.3, k * .9, seed))))
            verts.append(p + (N * math.cos(a) * r + B * math.sin(a) * r * squash))
    for k in range(n - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i))
    if tip:
        T = (path[-1] - path[-2]).normalized(); verts.append(path[-1] + T * radii[-1] * 1.4); t = len(verts) - 1
        for i in range(sides): faces.append(((n - 1) * sides + i, (n - 1) * sides + (i + 1) % sides, t))
    else:
        faces.append(tuple((n - 1) * sides + i for i in range(sides)))
    return verts, faces, list(path)

def cluster(center, radii, seed, amp=.22, flat_bottom=.42, subdiv=2):
    """lumpy foliage cluster: low-poly icosphere, stretched, per-vertex lumps and a flattened underside"""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    rnd = random.Random(seed); verts = []
    for v in bm.verts:
        d = v.co.copy(); d *= 1 + rnd.uniform(-amp, amp)
        if d.z < -flat_bottom: d.z = -flat_bottom + (d.z + flat_bottom) * .35
        verts.append(Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])) + center)
    idx = {v.index: i for i, v in enumerate(bm.verts)}
    faces = [tuple(idx[v.index] for v in f.verts) for f in bm.faces]; bm.free()
    return verts, faces, [center]

def bez(p0, p1, p2, n):
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in [i / (n - 1) for i in range(n)]]

def spline(pts, n):
    """Catmull-Rom through hand-placed points, n samples per segment (n=2 keeps only the key points smoothed)"""
    out = []
    P = [pts[0]] + list(pts) + [pts[-1]]
    segs = len(pts) - 1
    for s in range(segs):
        p0, p1, p2, p3 = P[s], P[s + 1], P[s + 2], P[s + 3]
        for i in range(n if s == segs - 1 else n - 1):
            t = i / (n - 1)
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return out

# ---------------------------------------------------------------- colour functions
def shade3(lo, mid, hi, zlo, zhi, nzw=.5):
    def f(p, n):
        h = (p.z - zlo) / max(zhi - zlo, 1e-6)
        k = max(0.0, min(1.0, h * (1 - nzw) + (n.z * .5 + .5) * nzw))
        return mix(lo, mid, k * 2) if k < .5 else mix(mid, hi, (k - .5) * 2)
    return f

def bark_fn(zlo, zhi, tint=1.0):
    def f(p, n):
        h = (p.z - zlo) / max(zhi - zlo, 1e-6)
        c = mix(V3['bark_lo'], V3['bark_mid'], h * 1.4 + n.z * .3)
        c = mix(c, V3['bark_hi'], max(0, n.z) * .35)
        return c * tint
    return f

# =============================================================== V3 REDESIGNS
def build_broadleaf():
    """Broadleaf: tapered flared trunk, three visible roots, a fork with three branches, five asymmetric foliage clumps
    (big one leaning left, smaller ones lower right, one low front) with sky gaps so wood shows."""
    M = Mesh(); R = random.Random(11)
    zhi = 12.6
    bk = bark_fn(0, 8.5)
    # trunk: leaning a little, flared base
    trunk = spline([Vector(p) for p in [(0, 0, -.2), (.15, .1, 1.4), (-.1, .25, 3.4), (-.35, .15, 5.4), (-.75, .1, 7.0)]], 2)
    v, f, ref = tube(trunk, [1.8, 1.2, .95, .8, .6], 7, tip=False, seed=2, wob=.06); M.add(v, f, ref, bk, seed=1)
    # roots: three bulges leaving the trunk and diving into the ground, uneven lengths
    for ang, ln, th in [(20, 2.2, .52), (150, 1.7, .42), (265, 2.5, .48)]:
        a = math.radians(ang); d = Vector((math.cos(a), math.sin(a), 0))
        path = [d * .5 + Vector((0, 0, 1.1)), d * 1.2 + Vector((0, 0, .45)), d * ln + Vector((0, 0, -.15))]
        v, f, ref = tube(path, [th, th * .7, th * .35], 4, tip=True, seed=ang, wob=.1); M.add(v, f, ref, bk, seed=ang)
    # branches (visible under and between the clumps)
    br = [
        [(-.75, .1, 6.0), (-1.4, .2, 7.4), (-2.0, .35, 8.4)],      # main fork up-left into the big clump
        [(-.6, .1, 5.4), (.5, -.2, 6.0), (1.8, -.4, 6.7)],         # right branch
        [(-.4, .2, 4.2), (-1.7, -.2, 4.7), (-3.0, -.6, 5.2)],      # low left branch
        [(-.7, .1, 6.6), (-.4, 1.0, 8.2), (.2, 1.5, 9.6)],         # back-up branch to the top clump
        [(-.4, .1, 4.6), (.9, .8, 4.8), (2.4, 1.0, 5.0)],          # small right-back branch
    ]
    for i, b in enumerate(br):
        pts = [Vector(p) for p in b]
        v, f, ref = tube(pts, (.5 if i < 2 else .4, .18), 5, tip=True, seed=i, wob=.1); M.add(v, f, ref, bk, seed=10 + i)
    # foliage clumps, hand placed, all different sizes and heights; flat undersides
    clumps = [
        ((-2.0, .3, 9.0), (4.0, 3.5, 2.7), 1), ((1.8, -.4, 7.6), (3.0, 2.8, 2.2), 2), ((-3.4, -.6, 6.2), (2.5, 2.2, 1.8), 3),
        ((.2, 1.4, 10.8), (2.6, 2.3, 2.0), 4), ((3.4, .9, 5.7), (1.9, 1.8, 1.4), 5), ((-.4, -2.2, 7.2), (2.2, 1.9, 1.5), 6),
    ]
    for c, r, s in clumps:
        cf = shade3(V3['leaf_lo'], V3['leaf_mid'], V3['leaf_hi'], c[2] - r[2], c[2] + r[2], .62)
        v, f, ref = cluster(Vector(c), r, 40 + s, amp=.2); M.add(v, f, ref, cf, jit=.035, seed=s)
    return M

def build_conifer():
    """Conifer: leaning trunk with visible flare/roots and bare lower stubs; seven drooping skirts of different size, tilt,
    rotation, scalloped rim, irregular spacing; offset along the curved axis; spiky leader."""
    M = Mesh(); R = random.Random(5)
    axis = spline([Vector(p) for p in [(0, 0, -.2), (.1, .05, 4), (.45, .2, 9), (.7, .15, 14.4)]], 4)
    def axis_at(z):
        for a, b in zip(axis, axis[1:]):
            if a.z <= z <= b.z: return a.lerp(b, (z - a.z) / max(b.z - a.z, 1e-6))
        return axis[-1]
    bk = bark_fn(0, 5)
    v, f, ref = tube(axis[:5], [1.0, .72, .6, .5, .42], 6, tip=False, seed=4, wob=.05); M.add(v, f, ref, bk, seed=3)
    for ang, ln, th in [(35, 1.8, .4), (170, 1.5, .34), (290, 2.1, .38)]:
        a = math.radians(ang); d = Vector((math.cos(a), math.sin(a), 0))
        path = [d * .35 + Vector((0, 0, .9)), d * .9 + Vector((0, 0, .35)), d * ln + Vector((0, 0, -.12))]
        v, f, ref = tube(path, [th, th * .65, th * .3], 4, tip=True, seed=ang, wob=.1); M.add(v, f, ref, bk, seed=ang)
    for z, ang in [(2.0, 80), (3.2, 230)]:  # snapped lower branch stubs
        a = math.radians(ang); d = Vector((math.cos(a), math.sin(a), .2)).normalized(); p0 = axis_at(z)
        v, f, ref = tube([p0, p0 + d * .9, p0 + d * 1.6 + Vector((0, 0, -.25))], (.2, .12), 4, tip=False, seed=z); M.add(v, f, ref, bk, seed=int(z * 3))
    # tiers: (base z of the skirt rim, radius, height, rotation, eccentricity, tilt x/y)
    tiers = [
        (2.2, 4.6, 3.4, 12, 1.1, (.05, .0)), (4.2, 3.9, 3.2, 40, .93, (-.03, .04)), (6.1, 3.4, 3.0, 77, 1.08, (.03, -.03)),
        (7.9, 2.7, 2.8, 20, .95, (-.04, .0)), (9.5, 2.1, 2.6, 58, 1.06, (.0, .03)), (11.0, 1.55, 2.4, 95, .92, (.02, -.02)),
        (12.4, 1.0, 2.2, 8, 1.0, (.0, .0)),
    ]
    N = 7
    for ti, (zb, rad, hgt, rot, ecc, tilt) in enumerate(tiers):
        c = axis_at(zb + hgt * .5) + Vector((R.uniform(-.22, .22), R.uniform(-.22, .22), 0))
        verts = []; faces = []
        rim = []
        for i in range(2 * N):
            a = math.radians(rot) + math.pi * i / N
            tip = (i % 2 == 0)
            rr = rad * (R.uniform(.95, 1.1) if tip else R.uniform(.72, .85))
            zz = zb + (R.uniform(-.25, .1) if tip else R.uniform(.3, .55))
            rim.append(Vector((math.cos(a) * rr * ecc + tilt[0] * rr * math.cos(a) * 0, math.sin(a) * rr / ecc, zz)) + Vector((tilt[0] * rr * .5 * math.cos(a), tilt[1] * rr * .5 * math.sin(a), 0)))
        mid = []
        for i in range(N):
            a = math.radians(rot) + 2 * math.pi * (i + .5) / N
            rr = rad * .5; mid.append(Vector((math.cos(a) * rr * ecc, math.sin(a) * rr / ecc, zb + hgt * .55)))
        apex = Vector((0, 0, zb + hgt)); under = Vector((0, 0, zb + hgt * .30))
        verts = [apex] + mid + rim + [under]
        ia = 0; im = 1; ir = 1 + N; iu = 1 + N + 2 * N
        for i in range(N):
            j = (i + 1) % N
            faces.append((ia, im + i, im + j))                                     # apex -> mid ring
            # mid ring segment (i..j) to rim tips 2i, 2i+2 and notch 2i+1
            r0, r1, r2 = ir + 2 * i, ir + 2 * i + 1, ir + (2 * i + 2) % (2 * N)
            faces.append((im + i, r0, r1)); faces.append((im + i, r1, im + j)); faces.append((im + j, r1, r2))
            faces.append((iu, r1, r0)); faces.append((iu, r2, r1))                 # underside
        off = Vector((c.x - 0, c.y - 0, 0))
        verts = [p + Vector((c.x, c.y, 0)) for p in verts]
        refpts = [Vector((c.x, c.y, zb + hgt * .6))]
        cf = shade3(V3['pine_lo'], V3['pine_mid'], V3['pine_hi'], zb, zb + hgt, .72)
        M.add(verts, faces, refpts + [Vector((c.x, c.y, zb + hgt * .2))], cf, jit=.04, seed=ti + 20)
    # leader spike
    top = axis_at(14.4)
    v, f, ref = tube([top + Vector((0, 0, -.8)), top + Vector((.05, 0, .4)), top + Vector((.1, 0, 1.5))], (.28, .08), 4, tip=True); M.add(v, f, ref, shade3(V3['pine_lo'], V3['pine_mid'], V3['pine_hi'], 13, 16, .3), seed=77)
    return M

def build_palm():
    """Palm: curved tapered trunk with ring bands, flared base and roots, crown of 11 arched, overlapping, drooping
    two-sided fronds of unequal length, a few young upright fronds and a coconut cluster."""
    M = Mesh(); R = random.Random(9)
    path = spline([Vector(p) for p in [(0, 0, -.2), (.3, .05, 2.8), (.8, .2, 5.4), (1.1, .3, 7.6), (1.1, .4, 9.4)]], 3)  # 9 pts
    n = len(path)
    radii = []
    for i in range(n):
        t = i / (n - 1); r = .8 - .46 * t + (.25 * (1 - t * 6) if t < 1 / 6 else 0)
        r *= 1 + (.07 if i % 2 else -.03)  # ring bands
        radii.append(r)
    top = path[-1]
    def pbark(p, nn):
        h = max(0.0, min(1.0, p.z / 9.0)); k = mix(0, 1, nn.z * .4 + .5)
        c = mix(V3['palm_bark_lo'], V3['palm_bark_hi'], h * .7 + k * .3)
        return c
    v, f, ref = tube(path, radii, 6, tip=False, seed=3, wob=.0)
    start = len(M.f); M.add(v, f, ref, pbark, jit=.0)
    for fi in range(start, start + (n - 1) * 6):  # alternate band colour = ring bands on the trunk
        if ((fi - start) // 6) % 2 == 1: M.c[fi] = [c * .8 for c in M.c[fi]]
    for ang, ln, th in [(70, 1.7, .36), (190, 1.4, .3), (305, 1.8, .34)]:
        a = math.radians(ang); d = Vector((math.cos(a), math.sin(a), 0))
        pth = [d * .4 + Vector((0, 0, .9)), d * 1.0 + Vector((0, 0, .35)), d * ln + Vector((0, 0, -.12))]
        v, f, ref = tube(pth, [th, th * .65, th * .3], 4, tip=True, seed=ang, wob=.1); M.add(v, f, ref, pbark, seed=ang)
    # fronds: (yaw deg, length, lift deg, droop, width, twist)
    # fronds on the side away from the lean are longer so the bbox centre (the game pivot) stays close to the trunk base
    fronds = [
        (10, 5.6, 20, 4.2, 1.5, .2), (45, 5.4, 30, 3.4, 1.35, -.15), (85, 6.2, 14, 4.8, 1.5, .1), (125, 6.0, 32, 3.4, 1.35, .25),
        (165, 7.6, 12, 5.4, 1.5, -.2), (205, 6.8, 26, 4.2, 1.35, .15), (245, 6.4, 16, 4.6, 1.5, -.1), (285, 5.4, 30, 3.2, 1.35, .2),
        (325, 5.6, 10, 4.6, 1.5, .1), (65, 3.6, 62, 1.3, 1.0, .0), (225, 3.4, 70, 1.0, .95, .0), (140, 3.8, 55, 1.5, 1.0, .0),
    ]
    for fi, (yaw, L, lift, droop, W, tw) in enumerate(fronds):
        y = math.radians(yaw); dirh = Vector((math.cos(y), math.sin(y), 0))
        lf = math.radians(lift); d0 = dirh * math.cos(lf) + Vector((0, 0, math.sin(lf)))
        side = Vector((-math.sin(y), math.cos(y), 0))
        S = 6; stations = []
        for s in range(S):
            t = s / (S - 1)
            c = top + Vector((0, 0, .15)) + d0 * L * t + Vector((0, 0, -1)) * droop * t * t
            wt = W * 1.25 * (math.sin(math.pi * min(1, t * .85 + .1) ** .9)) * (1.0 if s % 2 == 0 else .58)
            if s == S - 1: wt = 0.06
            fold = .26 * wt
            stations.append((c, side * wt, fold))
        verts = []; faces = []
        th = .09
        for (c, sd, fold) in stations:
            verts += [c - sd + Vector((0, 0, -fold * .2)), c + Vector((0, 0, fold)), c + sd + Vector((0, 0, -fold * .2))]
        for (c, sd, fold) in stations:
            verts += [c - sd * .8 + Vector((0, 0, -th - fold * .1)), c + Vector((0, 0, fold - th * 1.4)), c + sd * .8 + Vector((0, 0, -th - fold * .1))]
        nb = 3 * S
        for s in range(S - 1):
            a = 3 * s; b = 3 * (s + 1)
            faces += [(a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1)]
            faces += [(nb + a, nb + b, nb + b + 1, nb + a + 1), (nb + a + 1, nb + b + 1, nb + b + 2, nb + a + 2)]
        ref = [s[0] for s in stations]
        cf = shade3(V3['palm_lo'], V3['palm_mid'], V3['palm_hi'], top.z - droop * 1.1, top.z + L * math.sin(lf) + .5, .5)
        M.add(verts, faces, ref, cf, jit=.04, seed=fi)
    for i, (dx, dy, dz) in enumerate([(.55, .3, -.7), (-.4, .5, -.75), (.1, -.6, -.65)]):
        v, f, ref = cluster(top + Vector((dx, dy, dz)), (.5, .5, .55), 70 + i, amp=.12, flat_bottom=.9, subdiv=1)
        M.add(v, f, ref, lambda p, n: mix(V3['nut'] * .75, V3['nut'], n.z * .5 + .5), seed=i)
    return M

# =============================================================== CURRENT in-game approximation (owner screenshots, no repo file)
def build_current_broadleaf():
    M = Mesh()
    tr = [Vector((0, 0, -.2)), Vector((0, 0, 3.5)), Vector((0, 0, 7.0))]
    v, f, ref = tube(tr, [.95, .8, .7], 8, tip=False); M.add(v, f, ref, lambda p, n: CUR['bark'] * (.8 + .3 * (n.z * .5 + .5)), jit=.02)
    for c, r, s in [((0, 0, 9.4), (4.6, 4.6, 4.0), 1), ((2.7, .6, 8.3), (3.0, 3.0, 2.8), 2), ((-2.9, -.5, 8.6), (2.9, 2.9, 2.7), 3)]:
        cf = shade3(CUR['leaf_lo'], (CUR['leaf_lo'] + CUR['leaf_hi']) * .5, CUR['leaf_hi'], c[2] - r[2], c[2] + r[2], .6)
        v, f, ref = cluster(Vector(c), r, 90 + s, amp=.12, flat_bottom=1.0, subdiv=2); M.add(v, f, ref, cf, seed=s)
    return M

def build_current_conifer():
    M = Mesh()
    v, f, ref = tube([Vector((0, 0, -.2)), Vector((0, 0, 3)), Vector((0, 0, 6))], [.8, .7, .6], 8, tip=False); M.add(v, f, ref, lambda p, n: CUR['bark'] * .9, jit=.02)
    for zb, rad, hgt in [(2.2, 4.0, 3.6), (4.8, 3.3, 3.4), (7.4, 2.6, 3.2), (9.9, 1.9, 3.0), (12.2, 1.2, 2.6)]:
        verts = [Vector((0, 0, zb + hgt))]
        faces = []
        S = 12
        for i in range(S):
            a = 2 * math.pi * i / S; verts.append(Vector((math.cos(a) * rad, math.sin(a) * rad, zb)))
        verts.append(Vector((0, 0, zb)))
        for i in range(S):
            j = (i + 1) % S; faces.append((0, 1 + i, 1 + j)); faces.append((S + 1, 1 + j, 1 + i))
        cf = shade3(CUR['pine_lo'], (CUR['pine_lo'] + CUR['pine_hi']) * .5, CUR['pine_hi'], zb, zb + hgt, .6)
        M.add(verts, faces, [Vector((0, 0, zb + hgt * .5))], cf, jit=.02)
    return M

def build_current_palm():
    M = Mesh()
    v, f, ref = tube([Vector((0, 0, -.2)), Vector((.4, 0, 4)), Vector((.6, 0, 8.5))], [.6, .5, .4], 6, tip=False)
    M.add(v, f, ref, lambda p, n: CUR['bark'] * (.9 + .2 * (n.z * .5 + .5)), jit=.02)
    top = Vector((.6, 0, 8.6))
    for i in range(8):
        a = 2 * math.pi * i / 8; d = Vector((math.cos(a), math.sin(a), 0)); s = Vector((-math.sin(a), math.cos(a), 0))
        tip = top + d * 4.8 + Vector((0, 0, -.2)); m = top + d * 2.4 + Vector((0, 0, .25))
        verts = [top, m - s * .9, m + s * .9, tip]
        faces = [(0, 1, 2), (1, 3, 2), (0, 2, 1), (1, 2, 3)]  # flat leaf, both sides
        M.add(verts, faces, [m], lambda p, n: mix(CUR['palm_lo'], CUR['palm_hi'], .5 + .5 * n.z), jit=.02)
    return M

# =============================================================== scene helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    return sc

def vc_material(name="BD3_vc", rough=.95):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    a = nt.nodes.new('ShaderNodeVertexColor'); a.layer_name = 'Col'
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = rough
    try: b.inputs['Specular IOR Level'].default_value = .05
    except KeyError: pass
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(a.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], o.inputs[0])
    m.use_backface_culling = True  # what Roblox does: wrong-wound faces show as holes here
    return m

def flat_material(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (col.x, col.y, col.z, 1); b.inputs['Roughness'].default_value = 1
    return m

def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)

def make(builder, name):
    ob = builder().to_object(name, flat=True)
    ob.data.materials.append(vc_material())
    return ob

def import_v2(fname):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX_V2, fname))
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    ob = new[0]
    for o in bpy.data.objects:
        if o not in before and o.type != 'MESH': bpy.data.objects.remove(o)
    ob.data.materials.clear(); ob.data.materials.append(vc_material())
    ob.rotation_euler = (0, 0, 0); ob.parent = None
    return ob

# Real sizes (src/shared/DinosaurVisual.luau + resources/models/compy.obj): spawn scale 1 -> compy 4.4 studs tall, 8.5 long;
# max run scale min(4, sqrt(1 + growth/50)) = 4 (HudRules.MaxSize) -> 17.6 tall, 34 long (BIG x1.2 -> 21 tall).
DINO_H, DINO_L = 4.4, 8.5
def dino_stand_in(loc, yaw=0.0, s=1.0, color="#E8893A"):
    """scale reference silhouette: simple blob dino, 4.4 studs tall x ~8.5 long at s=1 (compy), faces +Y before yaw"""
    M = Mesh(); col = lin(color)
    f = lambda p, n: col * (.7 + .4 * (n.z * .5 + .5))
    for c, r in [((0, 0, 2.5), (1.35, 2.5, 1.3)), ((0, 2.7, 3.3), (.85, 1.35, .95)), ((0, -3.3, 2.0), (.6, 1.8, .55))]:
        v, fc, ref = cluster(Vector(c) * s, (r[0] * s, r[1] * s, r[2] * s), 3, amp=.05, flat_bottom=1.0); M.add(v, fc, ref, f, seed=1)
    for x, y in [(-.7, .6), (.7, .6), (-.7, -.9), (.7, -.9)]:
        v, fc, ref = tube([Vector((x, y, 1.5)) * s, Vector((x, y, 0.0))], (.4 * s, .34 * s), 5, tip=False); M.add(v, fc, ref, f)
    ob = M.to_object("Dino"); ob.data.materials.append(vc_material("DinoMat")); ob.location = loc; ob.rotation_euler = (0, 0, yaw)
    return ob

def world_setup(sc, res=(960, 540), sun_dir_deg=(52, 28)):
    sc.render.resolution_x, sc.render.resolution_y = res
    try: sc.render.engine = 'CYCLES'
    except TypeError: pass
    sc.cycles.samples = 40; sc.cycles.use_denoising = True; sc.cycles.device = 'CPU'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*lin("#BFE2FF"), 1); bg.inputs['Strength'].default_value = 1.15
    ld = bpy.data.lights.new("Sun", 'SUN'); ld.energy = 3.6; ld.angle = math.radians(5); ld.color = (1, .96, .88)
    so = bpy.data.objects.new("Sun", ld); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(sun_dir_deg[0]), 0, math.radians(sun_dir_deg[1]))
    gm = flat_material("Ground", GROUND)
    bpy.ops.mesh.primitive_plane_add(size=400); g = bpy.context.active_object; g.data.materials.append(gm)

def camera(sc, target, dist, elev, azim, fov=70.0, res=(960, 540)):
    cd = bpy.data.cameras.new("Cam"); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(fov); cd.clip_end = 600
    co = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(co); sc.camera = co
    e = math.radians(elev); a = math.radians(azim)
    pos = Vector(target) + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    co.location = pos
    d = Vector(target) - pos
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def place(ob, loc, rot=0.0, scale=(1, 1, 1), linked=False):
    o = ob.copy() if linked else ob
    if linked: bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, rot); o.scale = scale
    return o

def centre_xy(ob):
    """move the mesh so the bbox XY centre is the origin and the lowest point is z=0 (docs/56 pivot convention)"""
    me = ob.data; xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    ox = (min(xs) + max(xs)) / 2; oy = (min(ys) + max(ys)) / 2; oz = min(zs)
    for v in me.vertices: v.co.x -= ox; v.co.y -= oy; v.co.z -= oz
    me.update()
    return ox, oy, oz

# =============================================================== stages
FAMS = {
    'broadleaf': dict(cur=build_current_broadleaf, v2="world_tree_broad_a.fbx", v3=build_broadleaf, h=12.6, look=5.5),
    'conifer': dict(cur=build_current_conifer, v2="world_tree_pine_a.fbx", v3=build_conifer, h=14.5, look=6.5),
    'palm': dict(cur=build_current_palm, v2="world_tree_palm_a.fbx", v3=build_palm, h=10.0, look=4.5),
}

def get_variant(fam, variant):
    d = FAMS[fam]
    if variant == 'cur': ob = make(d['cur'], f"{fam}_cur")
    elif variant == 'v2': ob = import_v2(d['v2'])
    else: ob = make(d['v3'], f"{fam}_v3")
    if variant != 'v2': ox, oy, oz = centre_xy(ob); ob['trunk_base_offset'] = (-ox, -oy)
    return ob

def stage_export(out_dir):
    os.makedirs(FBX_V3, exist_ok=True)
    rep = []
    reset()
    names = {'broadleaf': 'world_tree_broad_v3', 'conifer': 'world_tree_pine_v3', 'palm': 'world_tree_palm_v3'}
    x = 0
    for fam in FAMS:
        ob = get_variant(fam, 'v3'); ob.name = names[fam]; ob.data.name = names[fam]
        ob.location = (x, 0, 0); x += 20
        dims = ob.dimensions
        rep.append((names[fam], tri_count(ob), len(ob.data.vertices), [round(dims.x, 2), round(dims.y, 2), round(dims.z, 2)], len(ob.data.materials)))
    for fam, (n, t, v, d, m) in zip(FAMS, rep): print("REPORT", n, "tris", t, "verts", v, "size", d, "materials", m)
    for fam in FAMS: print("TRUNKOFFSET", fam, [round(x, 2) for x in bpy.data.objects[names[fam]]["trunk_base_offset"]])
    for fam in FAMS:
        ob = bpy.data.objects[names[fam]]
        for o in bpy.context.selected_objects: o.select_set(False)
        loc = ob.location.copy(); ob.location = (0, 0, 0); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(FBX_V3, names[fam] + ".fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, axis_forward="-Z", axis_up="Y", colors_type="SRGB", mesh_smooth_type="FACE",
                                 add_leaf_bones=False, bake_anim=False)
        ob.location = loc; ob.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "assets", "blender", "world", "WorldKitV3_Trees.blend"))

def render(sc, path):
    sc.render.filepath = path; sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)

def stage_render(out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    res = (1600, 900)
    for fam, d in FAMS.items():
        if only and fam not in only: continue
        for variant in ('cur', 'v2', 'v3'):
            for shot in ('play', 'scale', 'grove', 'close'):
                sc = reset(); world_setup(sc, res)
                base = get_variant(fam, variant)
                if shot == 'play':
                    place(base, (0, 0, 0), .6)
                    dino_stand_in((-5.5, -7.0, 0), math.radians(25))
                    camera(sc, (3, 0, d['look']), 32, 17, 28, res=res)
                elif shot == 'scale':
                    place(base, (0, 0, 0), .6)
                    dino_stand_in((-12, 0, 0), math.radians(-90))
                    dino_stand_in((22, 0, 0), math.radians(-90), 4.0, "#B58AE8")
                    camera(sc, (5, 0, 9), 95, 3, 0, fov=38, res=res)
                elif shot == 'grove':
                    spots = [((0, 0), .4, 1.0), ((13, 5), 2.0, .8), ((-12, 7), 3.5, 1.1), ((6, 17), 5.0, .9), ((-5, -11), 1.1, .75)]
                    for i, (xy, rot, s) in enumerate(spots):
                        place(base, (xy[0], xy[1], 0), rot, (s, s, s), linked=(i > 0))
                    dino_stand_in((4, -7, 0), math.radians(-30))
                    camera(sc, (0, 3, d['look'] * .8), 34, 16, 22, res=res)
                else:
                    place(base, (0, 0, 0), .6)
                    camera(sc, (0, 0, d['look']), 17, 12, 28, res=res)
                if os.path.exists(os.path.join(out_dir, f"_{fam}_{variant}_{shot}.png")): pass
                render(sc, os.path.join(out_dir, f"_{fam}_{variant}_{shot}.png"))
                print("RENDERED", fam, variant, shot, tri_count(base))

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[0] if argv else "export"
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs", "evidence", "2026-10-16-trees")
    only = argv[2].split(",") if len(argv) > 2 else None
    if stage == "export": stage_export(out)
    elif stage == "render": stage_render(out, only)
