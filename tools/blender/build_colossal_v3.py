# Be Dino! BD-474: three colossal ancient trees in the V3 style (docs/139 s11, docs/140 "Colossal ancient trees").
#   1. broadleaf: giant baobab-like tree, buttress-root trunk, five thick limbs, layered umbrella crown, hanging vines
#   2. conifer:   giant ancient spire pine, root flare, bare snapped-limb lower trunk, broken drooping tiers, moss and vines
#   3. palm:      giant cycad-palm, ringed stout trunk with leaf boots, arching drooping fronds, seed cluster, vines
# Run headless (Blender 5.1):
#   blender -b -P tools/blender/build_colossal_v3.py -- export                  -> FBX LOD0/LOD1 + WorldKitV3_Colossal.blend + tris/size report
#   blender -b -P tools/blender/build_colossal_v3.py -- render <abs out dir> [shots]  -> comparison renders (stand-in vs new)
#   blender -b -P tools/blender/build_colossal_v3.py -- preview <abs out dir>   -> quick silhouette sheet while authoring
# Same scoped exception as the V3 trees (docs/140): shapes are authored by hand (branch paths, pad centres, frond curves are
# written out as numbers below; no scatter, no generators), painted with flat per-face vertex colours in ONE opaque material
# ("Col" attribute, no texture, no alpha). 1 unit = 1 stud, Z up; the FBX export uses the V3 settings. Pivot = bbox bottom centre
# (lowest point z = 0). Meshes are authored at the INTENDED size (80-140 studs tall, trunk 18-32 studs wide); the game scales them.
import bpy, bmesh, math, random, sys, os, json
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_trees_v3 as T
from build_trees_v3 import Mesh, lin, mix, shade3, spline, cluster, V3, vc_material, flat_material, tri_count, centre_xy, camera, render

ROOT = T.ROOT
FBX_V3 = T.FBX_V3
BLEND = os.path.join(ROOT, "assets", "blender", "world", "WorldKitV3_Colossal.blend")
GROUND = lin("#84A644")  # handbook 5.8 Grass as of BD-460 (132,166,68)

# ------------------------------------------------------------------ palette (V3 greens + warmer, lighter ancient bark)
P = dict(
    bark_hi=lin("#BE8C5E"), bark_mid=lin("#8F6444"), bark_lo=lin("#5B3F2E"), moss_lo=lin("#4E7E3A"), moss_hi=lin("#88B050"),
    leaf_hi=lin("#82C072"), leaf_mid=lin("#55A45F"), leaf_lo=lin("#2F7448"), leaf_warm=lin("#A4CC6C"),
    pine_hi=lin("#55A47C"), pine_mid=lin("#36805F"), pine_lo=lin("#1F5642"),
    palm_hi=lin("#86C972"), palm_mid=lin("#4FA55F"), palm_lo=lin("#2F7C4C"), palm_dead=lin("#9A7446"), palm_dead_lo=lin("#6C4E32"),
    palm_bark_hi=lin("#C28F5C"), palm_bark_lo=lin("#7A5230"), nut=lin("#8A5A34"),
    vine=lin("#3F7F4C"), vine_hi=lin("#6DB062"),
)


def smooth(x, a, b):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def tint(fn, k):
    k = Vector(k)
    return lambda p, n: Vector((fn(p, n)[i] * k[i] for i in range(3)))


# ------------------------------------------------------------------ shape helpers
def tube2(path, radii, sides=8, ridge=0.0, squash=1.0, seed=0, wob=0.0, tip=False, tip_len=1.3, phase=0.0):
    """tapered tube along a hand-placed path. radii: key list spread evenly or one value per path point. ridge alternates the
    radius per side (real bark ridges in the silhouette). Returns verts, faces, ref (ring centres)."""
    n = len(path)
    if len(radii) != n:
        keys = radii; radii = []
        for i in range(n):
            t = i / (n - 1) * (len(keys) - 1); a = min(int(t), len(keys) - 2); radii.append(keys[a] + (keys[a + 1] - keys[a]) * (t - a))
    verts = []; faces = []; N = None
    for k, p in enumerate(path):
        Tg = (path[min(k + 1, n - 1)] - path[max(k - 1, 0)]).normalized()
        if N is None:
            N = Tg.cross(Vector((0, 0, 1)))
            if N.length < .1: N = Tg.cross(Vector((1, 0, 0)))
            N.normalize()
        else:
            N = (N - Tg * N.dot(Tg)).normalized()
        B = Tg.cross(N)
        for i in range(sides):
            a = 2 * math.pi * (i + phase) / sides
            r = radii[k] * (1 + wob * noise.noise(Vector((seed + i * 1.3, k * .9, seed))))
            if ridge: r *= 1 + ridge * (1 if i % 2 == 0 else -1)
            verts.append(p + (N * math.cos(a) * r + B * math.sin(a) * r * squash))
    for k in range(n - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i))
    if tip:
        Tg = (path[-1] - path[-2]).normalized(); verts.append(path[-1] + Tg * radii[-1] * tip_len); t = len(verts) - 1
        for i in range(sides): faces.append(((n - 1) * sides + i, (n - 1) * sides + (i + 1) % sides, t))
    else:
        faces.append(tuple((n - 1) * sides + i for i in range(sides)))
    return verts, faces, list(path)


def fin(ang, d0, d1, ztop, t0, K=6, sweep=1.7, seed=0, zbase=0.0):
    """buttress root: a hexagonal plate that starts INSIDE the trunk at height ztop and sweeps out and down, thinning, until it
    meets the ground at distance d1 (flat underside at zbase). Returns verts, faces, ref."""
    a = math.radians(ang); D = Vector((math.cos(a), math.sin(a), 0)); Tg = Vector((-math.sin(a), math.cos(a), 0))
    verts = []; faces = []; ref = []
    for k in range(K + 1):
        u = k / K
        d = d0 + (d1 - d0) * u
        top = zbase + max(ztop * (1 - u) ** sweep, 1.2 if k < K else .9)
        top *= 1 + .08 * noise.noise(Vector((seed, k * .8, 3.3)))
        h = (top - zbase) / 2; zc = zbase + h
        t = t0 * (1 - .62 * u) * (1 + .12 * noise.noise(Vector((seed, k * .7, 9.1))))
        if k == K: t *= .55
        for s, z in [(0, h), (t, h * .45), (t, -h * .45), (0, -h), (-t, -h * .45), (-t, h * .45)]:
            verts.append(D * d + Tg * s + Vector((0, 0, zc + z)))
        ref.append(D * d + Vector((0, 0, zc)))
    for k in range(K):
        for i in range(6):
            j = (i + 1) % 6
            faces.append((k * 6 + i, k * 6 + j, (k + 1) * 6 + j, (k + 1) * 6 + i))
    faces.append(tuple(K * 6 + i for i in range(6)))
    return verts, faces, ref


def pad(center, radii, seed, amp=.24, flat_bottom=.4, subdiv=2):
    return cluster(Vector(center), radii, seed, amp=amp, flat_bottom=flat_bottom, subdiv=subdiv)


def frond(M, top, yaw, L, lift, droop, W, S, colfn, thick=.5, seed=0, dead=False):
    """two-sided arched frond with a folded midrib and a zigzag (toothed) edge; lift = degrees above horizontal at the stem"""
    y = math.radians(yaw); dirh = Vector((math.cos(y), math.sin(y), 0))
    lf = math.radians(lift); d0 = dirh * math.cos(lf) + Vector((0, 0, math.sin(lf)))
    side = Vector((-math.sin(y), math.cos(y), 0))
    stations = []
    for s in range(S):
        t = s / (S - 1)
        c = top + d0 * L * t + Vector((0, 0, -1)) * droop * t * t
        wt = W * (math.sin(math.pi * min(1, t * .88 + .1) ** .9)) * (1.0 if s % 2 == 0 else .55)
        if s == S - 1: wt = .25
        stations.append((c, side * wt, .22 * wt))
    verts = []; faces = []
    for (c, sd, fold) in stations:
        verts += [c - sd + Vector((0, 0, -fold * .3)), c + Vector((0, 0, fold)), c + sd + Vector((0, 0, -fold * .3))]
    for (c, sd, fold) in stations:
        verts += [c - sd * .8 + Vector((0, 0, -thick - fold * .2)), c + Vector((0, 0, fold - thick * 1.5)), c + sd * .8 + Vector((0, 0, -thick - fold * .2))]
    nb = 3 * S
    for s in range(S - 1):
        a = 3 * s; b = 3 * (s + 1)
        faces += [(a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1)]
        faces += [(nb + a, nb + b, nb + b + 1, nb + a + 1), (nb + a + 1, nb + b + 1, nb + b + 2, nb + a + 2)]
    M.add(verts, faces, [s[0] for s in stations], colfn, jit=.04, seed=seed)


def vine(M, start, length, seed, sides=3, segs=5, r0=1.9, knots=True, lod=0):
    """hanging vine: a two-sided leaf ribbon (toothed edge, slight sway) hanging from `start`; opaque geometry, no alpha card"""
    R = random.Random(seed)
    yaw = R.uniform(0, 360)
    cf = lambda p, n: mix(P['vine'], P['vine_hi'], .35 + .45 * n.z + .15 * (p.z - start.z + length) / max(length, 1))
    frond(M, start, yaw, length, -80 + R.uniform(-6, 6), 0.0, r0 * 1.25, 4 if (lod or not knots) else 6, cf, thick=.35, seed=seed)


def bark_fn(zlo, zhi, moss=0.0, moss_to=40.0, streak=1.0):
    """warm ancient bark: vertical streaks (noise stretched along z), light on up faces, optional moss on upward-facing surfaces near the ground"""
    def f(p, n):
        h = (p.z - zlo) / max(zhi - zlo, 1e-6)
        c = mix(P['bark_lo'], P['bark_mid'], h * 1.3 + n.z * .35 + .15)
        c = mix(c, P['bark_hi'], max(0.0, n.z) * .3 + max(0.0, h - .5) * .2)
        s = noise.noise(Vector((p.x * .22, p.y * .22, p.z * .035)))
        c = c * (1 + streak * .22 * s)
        if moss:
            m = smooth(n.z, .5, .9) * (1 - smooth(p.z, moss_to * .5, moss_to)) * moss
            m *= .7 + .6 * (noise.noise(Vector((p.x * .13, p.y * .13, p.z * .11))) + .5)
            c = mix(c, mix(P['moss_lo'], P['moss_hi'], .5 + .5 * n.z), min(1.0, m))
        return c
    return f


# =============================================================== 1. BROADLEAF (giant baobab-like)
# (centre, radii, subdiv at LOD0, keep at LOD1, tint) -- every pad hand placed, all different; three layers (low ring, wide middle
# umbrella, top cap) overlap into one crown with sky gaps and flat undersides
BROAD_PADS = [
    # low ring, z 62-72
    ((-41, -5, 65), (14.5, 13, 9.5), 2, True, (.94, .98, .96)), ((39, 11, 67), (14, 12.5, 9.5), 2, True, (.98, 1.0, .92)),
    ((-9, -39, 66), (15, 13, 9.5), 2, True, (1.0, 1.0, 1.04)), ((11, 41, 69), (15.5, 13.5, 10), 2, False, (1.02, .98, .96)),
    ((-31, 29, 66), (13, 12, 9), 2, False, (.96, 1.0, .98)), ((31, -31, 65), (13.5, 12, 8.5), 2, True, (1.0, .97, 1.0)),
    # wide middle umbrella, z 78-90
    ((-27, 7, 81), (25, 22, 12.5), 3, True, (1.0, 1.0, 1.0)), ((25, -10, 83), (23, 21, 12), 3, True, (.97, 1.02, .96)),
    ((4, 27, 86), (20, 18, 11.5), 2, True, (1.0, .98, 1.02)), ((3, -27, 84), (20, 19, 11), 2, True, (1.03, 1.0, .95)),
    ((-15, -19, 88), (16, 15, 10.5), 2, True, (1.0, 1.0, 1.05)), ((17, 15, 90), (16, 14, 10.5), 2, True, (1.04, 1.02, .98)),
    ((-44, 14, 82), (9.5, 9, 7.5), 2, False, (.93, .97, .93)),
    # top cap and puffs, z 96-112
    ((-6, 2, 99), (22, 20, 13), 3, True, (1.02, 1.03, 1.0)), ((-26, 7, 98), (13.5, 12.5, 10), 2, False, (1.05, 1.04, 1.0)),
    ((21, -4, 97), (13.5, 12, 10), 2, False, (1.02, 1.04, .98)), ((3, -12, 105), (10.5, 9.5, 8.5), 2, False, (1.06, 1.05, 1.0)),
    ((-10, 15, 103), (10.5, 9.5, 8.5), 2, False, (1.04, 1.05, 1.0)),
]
BROAD_LIMBS = [  # (path key points, radius keys): thick forks of the trunk top, then secondary branches
    ([(-5, 1, 38), (-13, 4, 52), (-25, 9, 66), (-39, 9, 74)], (9.6, 7.0, 4.6, 2.8)),
    ([(-5, 1, 40), (6, -3, 55), (18, -7, 68), (33, -10, 78)], (9.4, 6.8, 4.6, 2.8)),
    ([(-5, 1, 41), (-3, 12, 56), (3, 22, 70), (6, 28, 82)], (8.6, 6.0, 4.2, 2.6)),
    ([(-5, 1, 39), (-3, -10, 54), (2, -20, 68), (4, -27, 80)], (8.6, 6.0, 4.2, 2.6)),
    ([(-5, 1, 42), (-8, 1, 60), (-9, 3, 80), (-7, 4, 97)], (9.0, 6.0, 4.0, 2.6)),
    ([(-25, 9, 66), (-33, 18, 78), (-30, 25, 90)], (3.8, 2.8, 2.0)),
    ([(18, -7, 68), (28, -15, 80), (30, -23, 88)], (3.8, 2.8, 2.0)),
    ([(3, 22, 70), (-3, 29, 80), (-8, 33, 90)], (3.4, 2.6, 1.8)),
]
BROAD_FINS = [  # (angle deg, reach d1, height on trunk ztop, half thickness at the trunk): different lengths, none evenly spaced
    (8, 41, 42, 7.2), (58, 32, 31, 6.0), (112, 38, 38, 6.8), (169, 30, 28, 5.8), (218, 42, 44, 7.6), (271, 33, 33, 6.2), (322, 37, 37, 6.6),
]
BROAD_VINES = [  # (start x, y, z just under a pad or limb, length)
    (-38, 3, 64, 34), (-20, 14, 70, 29), (-31, 19, 67, 24), (26, -2, 70, 33), (14, -12, 74, 24), (36, 6, 60, 26), (5, 25, 74, 30),
    (-4, -22, 72, 31), (1, -31, 71, 24), (-12, -17, 79, 20), (-47, -4, 58, 20),
]


def build_broadleaf(lod=0):
    M = Mesh(); L1 = lod == 1
    sides = 8 if L1 else 12; n = 2 if L1 else 4
    bk = bark_fn(0, 62, moss=.8, moss_to=36)
    trunk = spline([Vector(p) for p in [(0, 0, 0), (1, 1, 10), (-1, 2, 26), (-3, 2, 38), (-5, 1, 47)]], n)
    radii = [16.0, 13.8, 12.2, 10.8, 9.8]
    v, f, ref = tube2(trunk, radii, sides, ridge=0.0 if L1 else .045, seed=2, wob=.04); M.add(v, f, ref, bk, jit=.02, seed=1)
    for i, (ang, d1, zt, t0) in enumerate(BROAD_FINS):
        K = 4 if L1 else 6
        v, f, ref = fin(ang, 9, d1, zt, t0, K=K, seed=i); M.add(v, f, ref, bk, seed=ang)
    for i, (pts, rk) in enumerate(BROAD_LIMBS):
        if L1 and i > 4: continue
        v, f, ref = tube2(spline([Vector(p) for p in pts], 2 if L1 else 3), list(rk), 5 if L1 else 7, ridge=0 if L1 else .05, seed=i, wob=.05, tip=True)
        M.add(v, f, ref, bark_fn(40, 100, moss=.5, moss_to=70), seed=10 + i)
    seed = 1
    for c, r, sd, keep, tn in BROAD_PADS:
        if L1 and not keep: continue
        k = 1.12 if L1 else 1.0
        cf = tint(shade3(P['leaf_lo'], P['leaf_mid'], P['leaf_hi'], c[2] - r[2], c[2] + r[2], .66), tn)
        v, f, ref = pad(c, (r[0] * k, r[1] * k, r[2] * k), 40 + seed, amp=.27, flat_bottom=.38, subdiv=(1 if L1 else sd)); M.add(v, f, ref, cf, jit=.04, seed=seed)
        seed += 1
    if not L1:
        for i, (x, y, z, ln) in enumerate(BROAD_VINES): vine(M, Vector((x, y, z)), ln, 100 + i, lod=lod)
        # moss ledges where limbs leave the trunk and on two root tops
        for c, r in [((-9, 4, 45), (6, 5.5, 2.4)), ((3, -7, 44), (5.5, 5, 2.2)), ((10, 2, 20), (5, 4.5, 1.8)), ((-14, -9, 12), (4.5, 4, 1.6))]:
            v, f, ref = pad(c, r, 200 + int(c[0]), amp=.2, flat_bottom=.2, subdiv=1)
            M.add(v, f, ref, lambda p, nn: mix(P['moss_lo'], P['moss_hi'], .5 + .5 * nn.z), seed=3)
    else:
        for i, (x, y, z, ln) in enumerate(BROAD_VINES[:4]): vine(M, Vector((x, y, z)), ln, 100 + i, sides=3, segs=3, r0=2.2, knots=False)
    return M


# =============================================================== 2. CONIFER (giant ancient spire pine)
# (base z, rim radius, height, rotation deg, eccentricity, tilt x/y, centre shift x/y, rim points): 11 broken, drooping tiers,
# no two the same; radii go up and down on purpose (a few tiers stick out like old shelves)
CONI_TIERS = [
    (36, 31, 17, 12, 1.12, (.07, .0), (2.0, -1.0), 10), (45, 35, 16, 40, .92, (-.05, .06), (-2.5, 1.5), 11), (54, 25, 16, 77, 1.1, (.05, -.05), (1.5, 2.0), 9),
    (62, 30, 15.5, 20, .94, (-.06, .0), (-2.0, -1.5), 11), (70, 19.5, 15, 58, 1.08, (.0, .05), (1.0, -2.0), 9), (77, 23, 14, 95, .9, (.04, -.04), (-1.5, 1.0), 10),
    (84, 15.5, 13, 8, 1.05, (.0, .0), (1.0, 1.0), 9), (89.5, 15, 12, 51, .94, (-.04, .04), (-1.0, -.5), 9), (95, 9.5, 10.5, 33, 1.05, (.03, -.02), (.5, .5), 8),
    (99, 7.2, 9, 70, .96, (.0, .0), (0, 0), 7), (102, 4.4, 7.5, 18, 1.0, (.0, .0), (0, 0), 7),
]


def build_conifer(lod=0):
    M = Mesh(); L1 = lod == 1; R = random.Random(5)
    sides = 8 if L1 else 12
    axis = spline([Vector(p) for p in [(0, 0, 0), (1.5, .5, 30), (4, 1.5, 62), (6.5, 1.0, 92), (7.5, 0, 106)]], 3 if L1 else 6)
    def axis_at(z):
        for a, b in zip(axis, axis[1:]):
            if a.z <= z <= b.z: return a.lerp(b, (z - a.z) / max(b.z - a.z, 1e-6))
        return axis[-1]
    bk = bark_fn(0, 80, moss=.9, moss_to=38)
    v, f, ref = tube2(axis, [13.2, 10.8, 8.2, 5.2, 2.0], sides, ridge=0.0 if L1 else .05, seed=4, wob=.04); M.add(v, f, ref, bk, jit=.02, seed=3)
    fins = [(20, 27, 22, 4.8), (82, 22, 16, 3.8), (141, 29, 24, 5.0), (197, 22, 15, 3.8), (252, 28, 21, 4.8), (312, 24, 17, 4.0)]
    for i, (ang, d1, zt, t0) in enumerate(fins):
        v, f, ref = fin(ang, 8, d1, zt, t0, K=3 if L1 else 5, seed=20 + i); M.add(v, f, ref, bk, seed=ang)
    # the lower trunk is bare: snapped limb stubs (moss on top) and two big dead limbs that fork
    if not L1:
        stubs = [(16, 10, 2.1), (22, 105, 2.3), (27, 200, 1.9), (31, 285, 2.2), (19, 330, 1.8), (34, 150, 2.0)]
        for z, ang, r in stubs:
            a = math.radians(ang); d = Vector((math.cos(a), math.sin(a), .22)).normalized(); p0 = axis_at(z)
            ln = R.uniform(9, 15)
            v, f, ref = tube2([p0 - d * 3, p0 + d * ln * .45 + Vector((0, 0, .4)), p0 + d * ln + Vector((0, 0, -1.2))], (r * 1.5, r * 1.1, r * .8), 5, seed=z); M.add(v, f, ref, bk, seed=int(z))
            c = p0 + d * ln * .6 + Vector((0, 0, r * .9))
            v, f, ref = pad(c, (r * 1.7, r * 1.6, r * .7), int(z) + ang, amp=.18, flat_bottom=.1, subdiv=1)
            M.add(v, f, ref, lambda p, nn: mix(P['moss_lo'], P['moss_hi'], .5 + .5 * nn.z), seed=1)
        for ang, z in [(60, 26), (235, 30)]:
            a = math.radians(ang); d = Vector((math.cos(a), math.sin(a), 0)); p0 = axis_at(z)
            main = [p0 - d * 3, p0 + d * 8 + Vector((0, 0, 3)), p0 + d * 18 + Vector((0, 0, 8)), p0 + d * 25 + Vector((0, 0, 8.5))]
            v, f, ref = tube2(main, (3.0, 2.4, 1.7, 1.0), 5, seed=ang, tip=True); M.add(v, f, ref, bk, seed=ang)
            fk = [main[1] + Vector((0, 0, .5)), main[1] + d * 6 + Vector((-d.y * 5, d.x * 5, 6)), main[1] + d * 9 + Vector((-d.y * 9, d.x * 9, 10))]
            v, f, ref = tube2(fk, (1.7, 1.2, .7), 4, seed=ang + 3, tip=True); M.add(v, f, ref, bk, seed=ang + 3)
    for ti, (zb, rad, hgt, rot, ecc, tilt, shift, N) in enumerate(CONI_TIERS):
        rad *= .94  # crown width kept inside the kit extent fit (docs/140 "Colossal ancient trees"): height decides the fit, not the width
        if L1:
            rad *= 1.04; hgt *= 1.1; N = 8  # same tiers, fewer rim points
        c = axis_at(zb + hgt * .5) + Vector((shift[0], shift[1], 0))
        rim = []
        for i in range(2 * N):
            a = math.radians(rot) + math.pi * i / N
            tp = (i % 2 == 0)
            rr = rad * (R.uniform(.88, 1.16) if tp else R.uniform(.62, .84))
            zz = zb + hgt * ((R.uniform(-.28, .06)) if tp else R.uniform(.12, .32))
            rim.append(Vector((math.cos(a) * rr * ecc + tilt[0] * rr * .5 * math.cos(a), math.sin(a) * rr / ecc + tilt[1] * rr * .5 * math.sin(a), zz)))
        def ring(share, zshare, jit):
            return [Vector((math.cos(math.radians(rot) + 2 * math.pi * (i + .5) / N) * rad * share * ecc, math.sin(math.radians(rot) + 2 * math.pi * (i + .5) / N) * rad * share / ecc, zb + hgt * zshare + R.uniform(-jit, jit))) for i in range(N)]
        mid1 = ring(.34, .78, .4); mid2 = ring(.62, .5, .5)
        apex = Vector((0, 0, zb + hgt)); under = Vector((0, 0, zb + hgt * .22))
        verts = [apex] + mid1 + mid2 + rim + [under]
        ia, i1, i2, ir = 0, 1, 1 + N, 1 + 2 * N; iu = len(verts) - 1
        faces = []
        for i in range(N):
            j = (i + 1) % N
            faces.append((ia, i1 + i, i1 + j))
            r0, rm, r2 = ir + 2 * i, ir + 2 * i + 1, ir + (2 * i + 2) % (2 * N)
            if L1:
                faces += [(i1 + i, r0, rm), (i1 + i, rm, i1 + j), (i1 + j, rm, r2)]
            else:
                faces += [(i1 + i, i2 + i, i2 + j, i1 + j)]
                faces += [(i2 + i, r0, rm), (i2 + i, rm, i2 + j), (i2 + j, rm, r2)]
            faces += [(iu, rm, r0), (iu, r2, rm)]
        verts = [p + Vector((c.x, c.y, 0)) for p in verts]
        tn = (1 + .04 * ((ti * 37) % 5 - 2), 1 + .03 * ((ti * 17) % 4 - 1.5), 1 + .04 * ((ti * 23) % 5 - 2))
        cf = tint(shade3(P['pine_lo'], P['pine_mid'], P['pine_hi'], zb, zb + hgt, .72), tn)
        M.add(verts, faces, [Vector((c.x, c.y, zb + hgt * .65)), Vector((c.x, c.y, zb + hgt * .25))], cf, jit=.04, seed=ti + 20)
        # bough lumps hanging off some rim tips: breaks the perfect skirt outline (LOD0 only)
        if not L1:
            for j in range(0, 2 * N, 2):
                if (j // 2 + ti) % 3 == 0: continue
                q = rim[j]; dirv = Vector((q.x, q.y, 0)).normalized()
                cc = Vector((c.x, c.y, 0)) + q + dirv * rad * .06 + Vector((0, 0, -hgt * .06))
                v, f, ref = pad(cc, (rad * .16 + 1.0, rad * .16 + 1.0, hgt * .14 + .7), ti * 31 + j, amp=.22, flat_bottom=.5, subdiv=1)
                M.add(v, f, ref, tint(shade3(P['pine_lo'], P['pine_mid'], P['pine_hi'], zb, zb + hgt, .6), tn), seed=ti * 3 + j)
        # visible branches under the tier: trunk to just short of the rim tips (lower, bigger tiers only)
        if not L1 and ti < 8:
            for j in range(3):
                tipv = rim[(j * 7 + ti * 3) % (2 * N) // 2 * 2] + Vector((c.x, c.y, 0))
                p0 = axis_at(zb + hgt * .2)
                tipv = p0.lerp(tipv, .78)
                pts = [p0, p0.lerp(tipv, .5) + Vector((0, 0, hgt * .1)), tipv + Vector((0, 0, hgt * .05))]
                v, f, ref = tube2(pts, (2.2 - ti * .12, 1.5 - ti * .08, .8), 4, seed=ti * 5 + j, tip=True)
                M.add(v, f, ref, bk, seed=ti * 7 + j)
    # weathered leader: a main spire and a bent broken second spike
    top = axis_at(106)
    v, f, ref = tube2([top + Vector((0, 0, -3)), top + Vector((.1, 0, 3.5)), top + Vector((.3, 0, 10))], (1.7, .9, .35), 5 if L1 else 6, tip=True, tip_len=1.8)
    M.add(v, f, ref, shade3(P['pine_lo'], P['pine_mid'], P['pine_hi'], 104, 118, .3), seed=77)
    if not L1:
        v, f, ref = tube2([top + Vector((.4, 0, -5)), top + Vector((3.2, 1.2, -1.5)), top + Vector((6.5, 1.8, 1.0))], (1.2, .8, .3), 4, tip=True, tip_len=1.6)
        M.add(v, f, ref, bk, seed=78)
        for i, (x, y, z, ln) in enumerate([(23, 6, 40, 20), (-22, 14, 42, 17), (8, -25, 44, 22), (-14, -22, 51, 18)]):
            vine(M, Vector((x, y, z)), ln, 300 + i, lod=lod, r0=1.5)
    return M


# =============================================================== 3. PALM / CYCAD (giant cycad-palm)
PALM_FRONDS = [  # (yaw, length, lift, droop, half width): a ring of big arched fronds, an inner ring, young upright ones. The side away from
    # the lean (yaw about 180) is longer so the bbox centre, the game pivot, stays near the trunk base
    (5, 56, 19, 34, 10.8), (34, 53, 29, 30, 10.3), (66, 58, 15, 35, 10.8), (98, 54, 25, 32, 10.3), (130, 60, 13, 37, 11.2), (162, 67, 19, 35, 11.7),
    (194, 69, 11, 40, 11.7), (226, 64, 21, 34, 11.2), (258, 58, 13, 35, 10.8), (290, 56, 25, 32, 10.3), (322, 53, 17, 34, 10.3),
    (18, 45, 45, 20, 8.5), (82, 43, 51, 19, 8.1), (146, 48, 43, 22, 8.8), (210, 50, 49, 21, 8.8), (274, 44, 53, 19, 8.1), (338, 43, 47, 18, 8.1),
    (50, 32, 72, 10, 5.9), (186, 37, 68, 11, 6.3), (118, 30, 76, 9, 5.8), (252, 31, 74, 10, 5.9),
]


def build_palm(lod=0):
    M = Mesh(); L1 = lod == 1; R = random.Random(9)
    sides = 8 if L1 else 12
    path = spline([Vector(p) for p in [(0, 0, 0), (1.5, 0, 20), (4.5, 1.5, 46), (6.5, 2.2, 68), (7.0, 2.4, 80)]], 3 if L1 else 9)
    n = len(path)
    keys = [13.4, 10.2, 8.8, 7.8, 8.6]
    radii = []
    for i in range(n):
        t = i / (n - 1) * (len(keys) - 1); a = min(int(t), len(keys) - 2)
        r = keys[a] + (keys[a + 1] - keys[a]) * (t - a)
        radii.append(r * (1 + (.07 if i % 2 else -.04)))  # ring bands
    top = path[-1]
    def pbark(p, nn):
        h = max(0.0, min(1.0, p.z / 80.0))
        c = mix(P['palm_bark_lo'], P['palm_bark_hi'], h * .55 + (nn.z * .4 + .5) * .3)
        s = noise.noise(Vector((p.x * .25, p.y * .25, p.z * .08)))
        c = c * (1 + .16 * s)
        m = smooth(nn.z, .5, .9) * (1 - smooth(p.z, 8, 22))
        return mix(c, mix(P['moss_lo'], P['moss_hi'], .5 + .5 * nn.z), min(1.0, m * .9))
    start = len(M.f)
    v, f, ref = tube2(path, radii, sides, ridge=0.0 if L1 else .035, seed=3); M.add(v, f, ref, pbark, jit=.0)
    if not L1:
        for fi in range(start, start + (n - 1) * sides):  # alternate band colour = ring bands on the trunk
            if ((fi - start) // sides) % 2 == 1: M.c[fi] = [c * .74 for c in M.c[fi]]
    fins = [(15, 24, 18, 4.4), (75, 19, 12, 3.6), (135, 26, 17, 4.6), (200, 20, 13, 3.6), (255, 25, 17, 4.4), (318, 22, 14, 3.8)]
    for i, (ang, d1, zt, t0) in enumerate(fins):
        v, f, ref = fin(ang, 7, d1, zt, t0, K=3 if L1 else 5, seed=40 + i); M.add(v, f, ref, pbark, seed=ang)
    S = 6 if L1 else 12
    cfx = shade3(P['palm_lo'], P['palm_mid'], P['palm_hi'], top.z - 30, top.z + 45, .5)
    for fi, (yaw, Ln, lift, droop, W) in enumerate(PALM_FRONDS):
        if L1 and fi in (1, 5, 7, 9, 12, 14, 17, 19): continue
        frond(M, top + Vector((0, 0, .8)), yaw, Ln, lift, droop, W * (1.1 if L1 else 1.0), S, tint(cfx, (1 + .03 * ((fi * 7) % 5 - 2), 1 + .02 * ((fi * 3) % 4 - 1.5), 1)), thick=.7, seed=fi)
    if not L1:  # chunky leaf-base stubs (old fronds sawn off) ringing the upper trunk
        for i in range(16):
            za = top.z - 4 - (i % 4) * 5.5 - (i // 4) % 2 * 2.2
            ang = math.radians(i * 22.5 + (i % 4) * 9)
            pa = path[min(n - 1, max(0, int(round((za / top.z) * (n - 1)))))]
            d = Vector((math.cos(ang), math.sin(ang), -.28)).normalized()
            rr = 7.4
            v, f, ref = tube2([pa + d * (rr - 2), pa + d * (rr + 3.2) + Vector((0, 0, -1.0))], (2.4, 1.6), 4, seed=i); M.add(v, f, ref, pbark, seed=i)
    dead = [(10, 26, -30, 9, 5.2), (70, 24, -40, 8, 4.8), (130, 28, -34, 10, 5.2), (190, 25, -44, 8, 4.7), (250, 27, -34, 9, 5.0), (310, 23, -42, 8, 4.6), (40, 20, -52, 6, 4.2), (160, 21, -50, 6, 4.2)]
    if not L1:
        dfx = shade3(P['palm_dead_lo'], P['palm_dead'], P['palm_dead'] * 1.12, top.z - 24, top.z, .4)
        for fi, (yaw, Ln, lift, droop, W) in enumerate(dead):
            frond(M, top + Vector((0, 0, -4)), yaw, Ln, lift, droop, W, 7, dfx, thick=.6, seed=60 + fi, dead=True)
        for i, (dx, dy, dz, rr) in enumerate([(6, 3.5, -3.6, 3.8), (-4.5, 6, -4.2, 3.6), (1, -7, -3.8, 3.9), (-7, -3.5, -3.4, 3.4), (8.5, -4.5, -4.4, 3.4), (-1, 7, -6, 3.2)]):
            v, f, ref = cluster(top + Vector((dx, dy, dz)), (rr, rr, rr * 1.1), 70 + i, amp=.12, flat_bottom=.8, subdiv=1)
            M.add(v, f, ref, lambda p, nn: mix(P['nut'] * .7, P['nut'], nn.z * .5 + .5), seed=i)
        for i, (x, y, z, ln) in enumerate([(top.x + 11, top.y + 2, top.z - 6, 25), (top.x - 10, top.y + 6, top.z - 7, 21), (top.x + 1, top.y - 11, top.z - 6, 27), (top.x - 6, top.y - 10, top.z - 10, 18)]):
            vine(M, Vector((x, y, z)), ln, 400 + i, r0=1.6, lod=lod)
    else:
        for i, (dx, dy) in enumerate([(9, 2), (-8, 6), (1, -9)]):
            vine(M, top + Vector((dx, dy, -8)), 22, 400 + i, sides=3, segs=3, r0=2.0, knots=False)
    return M


FAMS = {
    'broadleaf': dict(build=build_broadleaf, name='world_tree_colossal_broad_v3', key='tree_colossal_broadleaf_v3', cur=T.build_current_broadleaf,
                      kit=(17.926, 19.43, 16.656), kit_id='world_tree_canopy_l', h=105.0, look=52),
    'conifer': dict(build=build_conifer, name='world_tree_colossal_pine_v3', key='tree_colossal_pine_v3', cur=T.build_current_conifer,
                    kit=(15.781, 26.222, 15.769), kit_id='world_tree_conifer_l', h=110.0, look=55),
    'palm': dict(build=build_palm, name='world_tree_colossal_palm_v3', key='tree_colossal_palm_v3', cur=T.build_current_palm,
                 kit=(14.144, 12.673, 14.322), kit_id='world_tree_cycad_l', h=88.0, look=44),
}
LODS = {0: '', 1: '_lod1'}


# =============================================================== scene helpers
def make(builder, name, lod):
    ob = (builder() if lod is None else builder(lod)).to_object(name, flat=True)
    ob.data.materials.append(vc_material())
    return ob


def game_fit(ob, kit, scale):
    """what Arena.generatedProp does: the mesh is fitted inside the kit extent box (trees: by height, crown limited to 1.15 x the
    wider kit side), then ScaleTo(placement scale). Applies the same uniform factor to the Blender object. Returns the final height."""
    d = ob.dimensions  # Blender X, Y = width, depth; Z = height
    fit = min(kit[1] / d.z, max(kit[0], kit[2]) * 1.15 / max(d.x, d.y))
    k = fit * scale
    ob.scale = (k, k, k)
    return d.z * k


def compy(loc, yaw=0.0, s=1.0, color="#E8893A"):
    """Compy scale reference (measured low-poly Compy: 6.6 tall x 7.7 long x 3.5 wide at s=1, docs/139 s3.1): a chunky upright
    biped silhouette (egg body, thick legs, neck, head with a snout, tapering tail). Faces +Y before yaw. Not a game asset."""
    M = Mesh(); col = lin(color)
    belly = lin(color) * 1.25
    f = lambda p, n: mix(col * .78, belly, max(0.0, min(1.0, .35 + .6 * (n.z * .5 + .5) - .25 * (p.y < 0)))) 
    parts = [((0, .1, 3.55), (1.75, 2.55, 1.9), .06, 2), ((0, 2.3, 5.1), (.95, 1.35, 1.2), .05, 1), ((0, 3.55, 5.95), (1.05, 1.55, .85), .05, 2),
             ((0, -2.9, 3.45), (.95, 2.2, .85), .05, 1), ((0, -5.1, 3.0), (.55, 1.5, .5), .04, 1)]
    for c, r, amp, sub in parts:
        v, fc, ref = cluster(Vector(c) * s, (r[0] * s, r[1] * s, r[2] * s), 3, amp=amp, flat_bottom=1.0, subdiv=sub); M.add(v, fc, ref, f, seed=1)
    for x in (-.95, .95):
        v, fc, ref = T.tube([Vector((x, .35, 2.4)) * s, Vector((x, .55, 1.0)) * s, Vector((x, 1.1, 0.0)) * s], (.78 * s, .5 * s, .42 * s), 6, tip=False); M.add(v, fc, ref, f)
    ob = M.to_object("Compy"); ob.data.materials.append(vc_material("CompyMat")); ob.location = loc; ob.rotation_euler = (0, 0, yaw)
    return ob


def world(sc, res, sun=(52, 28)):
    T.world_setup(sc, res, sun)
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('Plane'):
            o.data.materials.clear(); o.data.materials.append(flat_material("Ground", GROUND)); o.scale = (3, 3, 1)
    sc.cycles.samples = 48


def cam(sc, target, dist, elev, azim, fov=70.0, res=(1280, 720)):
    camera(sc, target, dist, elev, azim, fov=fov, res=res)
    sc.camera.data.clip_end = 3000


def place_ob(ob, loc, rot=0.0):
    ob.location = loc; ob.rotation_euler = (0, 0, rot)
    return ob


def tree_variant(fam, variant, lod=0, height=None):
    """variant 'old' = scaled stand-in (approximation of the current generated meshes, docs/140), 'new' = colossal mesh. Both end up with
    the same height (placement scale picks it), fitted into the same kit extent box like Arena does."""
    d = FAMS[fam]
    if variant == 'old': ob = make(d['cur'], fam + "_old", None)
    else: ob = make(d['build'], fam + "_new", lod)
    centre_xy(ob)
    bpy.context.view_layer.update()
    kit = d['kit']; H = height or d['h']
    scale = H / kit[1]
    game_fit(ob, kit, scale)
    return ob


def gameplay_cam(sc, s, res, azim=0.0, fov=70.0):
    """the stock Roblox camera at its minimum zoom (docs/139 s3.2): distance 12 x s behind the dino, aim 3 + 2 (s - 1) above the floor,
    rest elevation about 10 degrees, FOV 70 (vertical). The dino stands at the origin facing +Y."""
    aim = Vector((0, 0, 3 + 2 * (s - 1)))
    D = 12 * s
    cam(sc, aim, D, 10, azim, fov=fov, res=res)


SHOTS = {
    # name: (dino size, tree distance, tree x offset share, camera azimuth)
    'spawn': dict(s=1.0, dist=290, az=24),
    's15': dict(s=1.5, dist=130, az=24),
    's4': dict(s=4.0, dist=135, az=24),
}


def stage_render(out_dir, only=None, res=(1280, 720)):
    os.makedirs(out_dir, exist_ok=True)
    for fam, d in FAMS.items():
        if only and fam not in only: continue
        for variant in ('old', 'new'):
            for shot, sp in SHOTS.items():
                sc = bpy.context.scene; T.reset(); sc = bpy.context.scene; world(sc, res)
                ob = tree_variant(fam, variant)
                place_ob(ob, (math.sin(math.radians(sp['az'] - 20)) * sp['dist'], math.cos(math.radians(sp['az'] - 20)) * sp['dist'], 0), .9)
                compy((0, 0, 0), 0.0, sp['s'])
                gameplay_cam(sc, sp['s'], res, sp['az'])
                render(sc, os.path.join(out_dir, f"_{fam}_{variant}_{shot}.png")); print("RENDERED", fam, variant, shot)
            # side-on lineup: three Compy at the trunk (spawn, 1.5, max 4) beside the tree, true elevations
            sc = bpy.context.scene; T.reset(); sc = bpy.context.scene; world(sc, res)
            ob = tree_variant(fam, variant)
            place_ob(ob, (0, 0, 0), .9)
            half = d['kit'][0] * (ob.scale[0]) * .5
            x0 = -d['h'] * .52
            compy((x0 + 4, -3, 0), math.radians(-90), 1.0)
            compy((x0 + 14, -3, 0), math.radians(-90), 1.5, "#F2C14E")
            compy((x0 + 36, -3, 0), math.radians(-90), 4.0, "#B58AE8")
            cam(sc, (-8, 0, d['h'] * .47), 190, 2, 0, fov=36, res=res)
            render(sc, os.path.join(out_dir, f"_{fam}_{variant}_lineup.png")); print("RENDERED", fam, variant, "lineup")


def stage_grove(out_dir, res=(1600, 800)):
    """skyline from the spawn: the three families together, a Compy at spawn size in the foreground, camera at the gameplay minimum.
    Trees are placed relative to the camera view direction (lateral offset, forward distance), never closer than the 150-stud keep-out."""
    os.makedirs(out_dir, exist_ok=True)
    az = math.radians(24)
    fwd = Vector((-math.sin(az), math.cos(az), 0)); lat = Vector((math.cos(az), math.sin(az), 0))
    for variant in ('old', 'new'):
        T.reset(); sc = bpy.context.scene; world(sc, res)
        spots = [('broadleaf', -95, 215, 4.0, 1.0), ('conifer', 10, 250, 1.1, 1.0), ('palm', 105, 205, 2.2, 1.0), ('broadleaf', 20, 380, 5.2, .92), ('conifer', -185, 300, .5, .9), ('palm', 190, 330, 1.7, .9)]
        heights = {'broadleaf': 104, 'conifer': 110, 'palm': 88}
        for fam, x, f, rot, k in spots:
            ob = tree_variant(fam, variant, height=heights[fam] * k)
            q = fwd * f + lat * x
            place_ob(ob, (q.x, q.y, 0), rot)
        compy((0, 0, 0), 0.0, 1.0)
        gameplay_cam(sc, 1.0, res, 24)
        render(sc, os.path.join(out_dir, f"_grove_{variant}.png")); print("RENDERED grove", variant)


def stage_lod(out_dir, res=(1280, 720)):
    os.makedirs(out_dir, exist_ok=True)
    for fam, d in FAMS.items():
        for lod in (0, 1):
            sc = bpy.context.scene; T.reset(); sc = bpy.context.scene; world(sc, res)
            ob = tree_variant(fam, 'new', lod)
            place_ob(ob, (0, 0, 0), .9)
            cam(sc, (0, 0, d['h'] * .47), 210, 3, 0, fov=36, res=res)
            render(sc, os.path.join(out_dir, f"_lod_{fam}_{lod}.png")); print("RENDERED lod", fam, lod, tri_count(ob))
        # far view at 300 studs (LOD1 takes over beyond about 150 studs, docs/139 s9), gameplay camera, three-quarter view
        for lod in (0, 1):
            T.reset(); sc = bpy.context.scene; world(sc, res)
            ob = tree_variant(fam, 'new', lod)
            place_ob(ob, (math.sin(math.radians(4)) * 300, math.cos(math.radians(4)) * 300, 0), .9)
            compy((0, 0, 0), 0.0, 1.0)
            gameplay_cam(sc, 1.0, res, 24)
            render(sc, os.path.join(out_dir, f"_far_{fam}_{lod}.png")); print("RENDERED far", fam, lod)


def stage_preview(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    res = (1000, 640)
    for fam, d in FAMS.items():
        for lod in (0, 1):
            T.reset(); sc = bpy.context.scene; world(sc, res)
            ob = make(d['build'], fam, lod); centre_xy(ob)
            ob.rotation_euler = (0, 0, .9)
            compy((-d['h'] * .45, -3, 0), math.radians(-90), 4.0, "#B58AE8")
            cam(sc, (0, 0, d['h'] * .5), 230, 6, 0, fov=36, res=res)
            render(sc, os.path.join(out_dir, f"prev_{fam}_{lod}.png"))
            dm = ob.dimensions
            print("PREVIEW", fam, "lod", lod, "tris", tri_count(ob), "size", [round(x, 1) for x in dm])


def stage_export():
    os.makedirs(FBX_V3, exist_ok=True)
    T.reset()
    report = {}
    obs = {}
    x = 0
    for fam, d in FAMS.items():
        for lod in (0, 1):
            name = d['name'] + LODS[lod]
            ob = make(d['build'], name, lod); ob.data.name = name; ob.name = name
            ox, oy, oz = centre_xy(ob)
            ob['trunk_base_offset'] = (-ox, -oy)
            ob.location = (x, 0, 0); x += 130
            dm = ob.dimensions
            report[name] = dict(tris=tri_count(ob), verts=len(ob.data.vertices), size=[round(dm.x, 2), round(dm.y, 2), round(dm.z, 2)],
                                materials=len(ob.data.materials), trunk_offset=[round(-ox, 2), round(-oy, 2)])
            obs[name] = ob
            print("REPORT", name, json.dumps(report[name]))
    for name, ob in obs.items():
        for o in bpy.context.selected_objects: o.select_set(False)
        loc = ob.location.copy(); ob.location = (0, 0, 0); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(FBX_V3, name + ".fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, axis_forward="-Z", axis_up="Y", colors_type="SRGB", mesh_smooth_type="FACE",
                                 add_leaf_bones=False, bake_anim=False)
        ob.location = loc; ob.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[0] if argv else "export"
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs", "evidence", "2026-10-17-colossal")
    only = argv[2].split(",") if len(argv) > 2 else None
    if stage == "export": stage_export()
    elif stage == "render": stage_render(out, only)
    elif stage == "grove": stage_grove(out)
    elif stage == "lod": stage_lod(out)
    elif stage == "preview": stage_preview(out)
