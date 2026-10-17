# Be Dino! BD-296 art: cave wall rock forms and the gate arch frame (V3 style, same pipeline as the ground props and colossal trees).
# Run headless:  blender -b -P tools/blender/build_cave_rockforms_v3.py -- <stage> [out_dir] [shots]
#   stages: export -> write assets/blender/world/fbx_v3/cave_*_v3.fbx + WorldKitV3_CaveRockforms.blend + tri / size / colour report
#           render -> comparison renders in a dim warm-lit Blender scene that mimics the cave (docs/114 s6.1) into <out_dir>:
#                     _wall_v1 / _wall_v2 (today's flat wall approximated vs with the rock forms), _arch_v1 / _arch_v2 (today's faint
#                     niche vs the arch frame with two lantern hooks and a warm light), _lineup (the seven meshes close up)
# Every mesh is shaped by hand: rock chunks are low icosphere lumps chiselled by hand-placed cut planes (flat facets), tilted and stacked
# by hand-set numbers; the arch is hand-cut voussoir blocks round an ellipse. No scatter, no generators. One vertex-colour material each
# (Col attribute), warm matte stone around the cave wall colour (124,104,86) with lighter edges, a few moss-green tops.
# 1 unit = 1 stud, Z up, pivot at the bbox bottom centre, same FBX settings as fbx_v3 (tools/blender/build_trees_v3.py).
# ORIENTATION: the face that stands against the cave wall is Blender -Y and is left OPEN (no back faces); the face that looks into the
# cave is Blender +Y. With the fbx_v3 export axes that is Roblox -Z (the part front, CFrame yaw 0), so a placed form uses
# yaw = CaveHubLayout.yawTo(inward normal) and its back lands on the wall. The arch walks along Y: yaw 0 faces the Heart side.
# Scoped owner decision 2026-10-16: Blender is allowed for world art; the meshes must look hand-crafted, not like primitives.
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Euler, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_trees_v3 as T
from build_trees_v3 import Mesh, tube, spline, lin, mix, vc_material, flat_material, tri_count, centre_xy, reset, render, camera, dino_stand_in, ROOT

FBX_V3 = T.FBX_V3
BLEND = os.path.join(ROOT, "assets", "blender", "world", "WorldKitV3_CaveRockforms.blend")

# ---------------------------------------------------------------- palette: the cave wall is Concrete (124,104,86) = #7C6856 (docs/104 s17)
STONE_DK, STONE_LO, STONE_MID = lin("#54473A"), lin("#6C5B4A"), lin("#7C6856")
STONE_HI, STONE_EDGE = lin("#9C876C"), lin("#B39B78")
MOSS_LO, MOSS_MID, MOSS_HI = lin("#4E7E3A"), lin("#5F8E3C"), lin("#7DA64A")
IRON_LO, IRON_HI = lin("#2E2822"), lin("#4C4137")
WALL_RGB = (124, 104, 86)

def form_col(zlo, zhi, seed=0, moss=0.0, bands=True, front=.12):
    """warm stone: darker at the foot, lighter on up-facing and sun-side facets (the chiselled edges), faint strata banding,
    optional moss on high up-facing facets (moss = how much of the top is green, 0..1)"""
    def f(p, n):
        t = (p.z - zlo) / max(zhi - zlo, 1e-6)
        c = mix(STONE_LO, STONE_MID, .25 + t * 1.1)
        if bands:
            c = c * (.93 + .1 * math.sin(p.z * 1.9 + noise.noise(Vector((p.x * .3, p.y * .3, seed))) * 2.2))
        up = max(0.0, n.z)
        c = mix(c, STONE_HI, up * .55 + max(0.0, n.y) * front)
        edge = max(0.0, 1 - abs(n.z) * 1.6) * max(0.0, n.x * .5 + n.y * .5)
        c = mix(c, STONE_EDGE, edge * .35)
        if n.y < -.4: c = c * .7
        if moss > 0 and n.z > .5:
            m = .5 + .5 * noise.noise(Vector((p.x * .45 + seed, p.y * .45, p.z * .3))) + t * .3
            if m > 1.12 - moss * .6:
                return mix(MOSS_LO, MOSS_HI, n.z * .5 + .3 + .25 * noise.noise(Vector((p.x * 1.1, p.y * 1.1, seed))))
        return c
    return f

# ---------------------------------------------------------------- shape helpers
def slab(M, center, half, seed, taper=(1.0, 1.0), jitter=.10, tilt=(0.0, 0.0), yaw=0.0, cuts=1, col=None, jit=.035, tol=math.radians(7), top_skew=(0.0, 0.0)):
    """one chiselled stone block: a cube cut into a 3x3 grid per face (cuts=1) or finer, every vertex pushed by a hand-set seed (`jitter` of the
    half size), the top pulled in by `taper` (x, y) and shifted by `top_skew`, then tilted, turned and placed; near-coplanar faces are dissolved so
    the result keeps big flat chiselled facets and sharp edges instead of reading as a pebble"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    R = random.Random(seed)
    for v in bm.verts:
        p = v.co.copy()
        t = (p.z + 1) / 2
        p.x *= 1 + (taper[0] - 1) * t; p.y *= 1 + (taper[1] - 1) * t
        p.x += top_skew[0] * t; p.y += top_skew[1] * t
        p = Vector((p.x * half[0], p.y * half[1], p.z * half[2]))
        p += Vector((R.uniform(-1, 1) * half[0], R.uniform(-1, 1) * half[1], R.uniform(-1, 1) * half[2])) * jitter
        v.co = p
    bmesh.ops.dissolve_limit(bm, angle_limit=tol, verts=bm.verts, edges=bm.edges)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    e = Euler((tilt[0], tilt[1], yaw), 'XYZ'); c = Vector(center)
    pts = []
    for v in bm.verts:
        q = v.co.copy(); q.rotate(e); pts.append(q + c)
    faces = [tuple(v.index for v in f.verts) for f in bm.faces if len(f.verts) >= 3]
    bm.free()
    M.add(pts, faces, [c], col, jit=jit, seed=seed)

def moss(M, center, radii, seed):
    """a dim, flat moss cushion (darker than the island greens so it sits in the lamp-lit cave)"""
    v, f, ref = T.cluster(Vector(center), radii, seed, amp=.2, flat_bottom=.25, subdiv=1)
    M.add(v, f, ref, T.shade3(MOSS_LO, MOSS_MID, MOSS_HI, center[2] - radii[2], center[2] + radii[2], .7), jit=.03, seed=seed)

def flatten_back(M, y0=0.0, eps=.02):
    """the wall side: clamp every vertex to y >= y0 and drop the faces that now lie flat on the wall (they are never seen)"""
    for p in M.v:
        if p.y < y0: p.y = y0
    keep = [i for i, fc in enumerate(M.f) if not all(M.v[k].y < y0 + eps for k in fc)]
    M.f = [M.f[i] for i in keep]; M.c = [M.c[i] for i in keep]

def finish(M):
    flatten_back(M)
    return M

# =============================================================== the six rock forms (studs; wall plane y = 0, the cave is +Y)
def build_slab_stack():
    """layered slabs, about 14 x 7 x 13: five stepped, slightly turned strata slabs on a fat foot slab, a leaning cap stone, moss on two tops"""
    M = Mesh(); col = form_col(0, 13, 1, moss=.45)
    slab(M, (0, 2.9, 1.3), (7.0, 3.1, 1.4), 11, taper=(.92, .9), tilt=(0, .02), yaw=.04, col=col, cuts=2)
    slab(M, (-.8, 2.8, 3.55), (6.2, 2.8, 1.0), 12, taper=(.93, .92), tilt=(0, -.03), yaw=.09, col=col, cuts=2)
    slab(M, (.9, 3.0, 5.4), (5.4, 2.9, .95), 13, taper=(.92, .9), tilt=(.02, .04), yaw=-.1, col=col, cuts=2)
    slab(M, (-.6, 2.6, 7.2), (4.5, 2.5, .9), 14, taper=(.9, .9), tilt=(0, -.05), yaw=.14, col=col)
    slab(M, (.5, 2.5, 9.0), (3.4, 2.1, .9), 16, taper=(.88, .9), tilt=(-.03, .05), yaw=-.12, col=col)
    slab(M, (.2, 2.3, 11.0), (2.1, 1.8, 1.15), 15, taper=(.55, .6), tilt=(.04, -.1), yaw=.5, col=col, jitter=.16)
    moss(M, (.5, 2.6, 10.0), (3.0, 1.9, .4), 21)
    moss(M, (-.7, 3.0, 4.6), (4.2, 1.9, .4), 22)
    return finish(M)

def build_buttress():
    """a tall tapering buttress, about 10 x 7 x 18: broad foot blocks, three narrowing tiers with vertical facets, a leaning side rib, a pointed top"""
    M = Mesh(); col = form_col(0, 18, 2, moss=.3)
    slab(M, (0, 3.2, 2.2), (5.0, 3.3, 2.4), 21, taper=(.85, .85), yaw=.18, col=col, cuts=2, jitter=.12)
    slab(M, (.3, 2.8, 6.6), (3.7, 2.6, 2.4), 22, cuts=2, taper=(.82, .85), tilt=(0, .04), yaw=-.1, col=col, jitter=.12)
    slab(M, (-.3, 2.4, 11.0), (2.9, 2.1, 2.5), 23, cuts=2, taper=(.78, .82), tilt=(0, -.05), yaw=.2, col=col, jitter=.12)
    slab(M, (-.1, 2.0, 15.4), (2.0, 1.6, 2.6), 24, taper=(.2, .3), tilt=(0, .03), yaw=.35, col=col, jitter=.12, top_skew=(-.3, 0))
    slab(M, (3.9, 3.2, 4.2), (1.8, 2.4, 4.0), 25, taper=(.6, .8), tilt=(0, .12), yaw=.25, col=col, jitter=.12)
    slab(M, (-4.0, 3.4, 1.6), (1.9, 2.1, 1.6), 26, taper=(.8, .8), yaw=-.5, col=col, jitter=.14)
    slab(M, (-1.8, 6.0, .9), (1.3, 1.2, .9), 27, taper=(.8, .8), yaw=.6, col=col, jitter=.14)
    moss(M, (3.9, 3.2, 8.0), (1.4, 1.5, .4), 28)
    return finish(M)

def build_overhang():
    """an overhang ledge, about 16 x 8 x 12: a heavy top slab jutting out over a stacked pillar on the left and a block on the right, rubble
    at the foot, moss on the ledge"""
    M = Mesh(); col = form_col(0, 12, 3, moss=.5)
    slab(M, (-5.0, 2.6, 2.1), (3.0, 2.6, 2.2), 31, taper=(.9, .9), yaw=.1, col=col, jitter=.12)
    slab(M, (-4.8, 2.6, 6.0), (2.5, 2.3, 2.0), 32, taper=(.85, .9), tilt=(0, -.04), yaw=-.12, col=col, jitter=.12)
    slab(M, (5.6, 3.0, 1.9), (2.8, 2.9, 2.0), 33, taper=(.85, .85), yaw=-.3, col=col, jitter=.12)
    slab(M, (.3, 3.9, 9.3), (7.8, 4.0, 1.35), 34, taper=(.95, .88), tilt=(-.05, .02), yaw=-.04, col=col, cuts=2, jitter=.1)
    slab(M, (3.0, 4.0, 5.2), (2.0, 2.1, 1.7), 35, taper=(.8, .85), yaw=.4, col=col, jitter=.14)
    slab(M, (1.0, 6.5, .9), (1.7, 1.5, .9), 36, taper=(.8, .8), yaw=.6, col=col, jitter=.14)
    slab(M, (-2.4, 6.4, .7), (1.3, 1.1, .7), 37, taper=(.8, .8), yaw=-.5, col=col, jitter=.14)
    moss(M, (-.4, 4.3, 10.4), (5.0, 2.4, .4), 38)
    moss(M, (5.6, 3.2, 3.9), (2.0, 1.8, .4), 39)
    return finish(M)

def build_tumble():
    """a tumble of blocks, about 15 x 8 x 9: two big blocks with a third resting across them, four smaller fallen stones in front"""
    M = Mesh(); col = form_col(0, 9, 4, moss=.4)
    slab(M, (-3.9, 3.1, 2.4), (3.4, 3.0, 2.5), 41, cuts=2, taper=(.85, .9), tilt=(0, .06), yaw=.3, col=col, jitter=.13)
    slab(M, (3.2, 3.3, 2.9), (3.7, 3.1, 3.0), 42, cuts=2, taper=(.8, .85), tilt=(.03, -.07), yaw=-.25, col=col, jitter=.13)
    slab(M, (-.3, 2.4, 6.6), (3.6, 2.3, 1.7), 43, taper=(.85, .85), tilt=(.04, .16), yaw=.45, col=col, jitter=.12)
    slab(M, (6.6, 5.6, 1.3), (1.9, 1.8, 1.4), 44, taper=(.8, .8), tilt=(.1, .08), yaw=.8, col=col, jitter=.14)
    slab(M, (-6.7, 5.4, 1.2), (1.8, 1.7, 1.3), 45, taper=(.8, .8), tilt=(-.08, .1), yaw=-.7, col=col, jitter=.14)
    slab(M, (1.0, 6.4, 1.0), (1.6, 1.4, 1.0), 46, taper=(.8, .8), tilt=(.05, -.1), yaw=.2, col=col, jitter=.14)
    slab(M, (-2.2, 7.2, .7), (1.1, 1.0, .7), 47, taper=(.8, .8), yaw=1.0, col=col, jitter=.14)
    moss(M, (-.4, 2.6, 8.2), (2.6, 1.6, .4), 48)
    moss(M, (3.3, 3.6, 5.8), (2.2, 1.8, .4), 49)
    return finish(M)

def build_fins():
    """three tall stone fins, about 10 x 6 x 18, leaning a little apart like a split strata ridge, on a low rubble mound"""
    M = Mesh(); col = form_col(0, 18, 5, moss=.2)
    slab(M, (0, 2.8, 1.4), (5.0, 3.0, 1.5), 51, taper=(.85, .85), yaw=.1, col=col, cuts=2, jitter=.12)
    slab(M, (-2.9, 2.3, 8.0), (1.7, 1.7, 7.6), 52, cuts=2, taper=(.35, .55), tilt=(0, -.08), yaw=.2, col=col, jitter=.1, top_skew=(.3, 0))
    slab(M, (.5, 2.1, 9.4), (2.0, 1.8, 8.6), 53, cuts=2, taper=(.4, .55), tilt=(0, .02), yaw=-.1, col=col, jitter=.1, top_skew=(-.3, 0))
    slab(M, (3.4, 2.6, 6.6), (1.7, 1.7, 5.8), 54, cuts=2, taper=(.3, .5), tilt=(0, .09), yaw=.3, col=col, jitter=.1)
    slab(M, (-.4, 5.6, .9), (1.8, 1.4, .9), 55, taper=(.8, .8), yaw=.5, col=col, jitter=.14)
    moss(M, (3.4, 2.8, 10.9), (1.0, 1.0, .3), 56)
    moss(M, (-2.9, 2.6, 2.9), (2.0, 1.7, .4), 57)
    return finish(M)

def build_terrace():
    """a stepped terrace, about 20 x 7 x 8: three long slabs stepping back and up, an end block, moss on the steps"""
    M = Mesh(); col = form_col(0, 8, 6, moss=.45)
    slab(M, (0, 2.9, 1.7), (9.1, 3.2, 1.8), 61, taper=(.96, .9), yaw=.02, col=col, cuts=3, jitter=.09)
    slab(M, (-1.6, 2.2, 4.0), (6.9, 2.5, 1.0), 62, taper=(.95, .9), yaw=.03, col=col, cuts=2, jitter=.1)
    slab(M, (-3.3, 1.7, 5.9), (4.6, 1.9, .95), 63, taper=(.92, .9), yaw=-.05, col=col, cuts=2, jitter=.1)
    slab(M, (7.6, 3.9, 2.0), (2.4, 2.6, 2.2), 64, taper=(.8, .85), yaw=.5, tilt=(0, -.06), col=col, jitter=.13)
    slab(M, (5.0, 5.7, .8), (1.5, 1.3, .9), 65, taper=(.8, .8), yaw=1.0, col=col, jitter=.14)
    moss(M, (1.4, 2.9, 3.4), (4.4, 1.7, .4), 66)
    moss(M, (-5.0, 1.9, 6.9), (2.8, 1.2, .35), 67)
    return finish(M)

# =============================================================== the gate arch frame (studs)
ARCH_A, ARCH_B = 14.6, 19.6          # inner half-ellipse of the opening (the terrain mouth is 15 x 20: CaveTerrainRules / CaveHubLayout.gate)
ARCH_D = 6.0                          # depth along Y (the terrain niche is 6 studs deep)
ARCH_INFO = {}                        # filled by build_gate_arch: where the block fronts and the back plane are before the bbox is centred

def ring_point(theta, off, a=ARCH_A, b=ARCH_B):
    """point on the ellipse (a, b) at angle theta (0 = right foot, pi = left foot) pushed `off` studs outwards along the normal"""
    x, z = a * math.cos(theta), b * math.sin(theta)
    nx, nz = math.cos(theta) / a, math.sin(theta) / b
    l = math.hypot(nx, nz); nx, nz = nx / l, nz / l
    return Vector((x + nx * off, 0.0, z + nz * off))

def arc_params(n):
    """n+1 angles from 0 to pi at equal arc length of the half-ellipse"""
    S = 400; pts = [ring_point(math.pi * i / S, 0) for i in range(S + 1)]
    cum = [0.0]
    for i in range(1, S + 1): cum.append(cum[-1] + (pts[i] - pts[i - 1]).length)
    out = []
    for k in range(n + 1):
        target = cum[-1] * k / n
        i = next(j for j in range(1, S + 1) if cum[j] >= target)
        t = (target - cum[i - 1]) / max(cum[i] - cum[i - 1], 1e-9)
        out.append(math.pi * (i - 1 + t) / S)
    return out

def block(M, p_in0, p_in1, p_out0, p_out1, y_back, y_front, col, seed, shrink=.07, cham=.55, front_in=.1):
    """one hand-cut stone block between two ring positions: a chamfered front (inset, sloped edge ring, flat face), open back"""
    R = random.Random(seed)
    def jv(v, a=.1): return v + Vector((R.uniform(-a, a), R.uniform(-a, a) * .6, R.uniform(-a, a)))
    cen = (p_in0 + p_in1 + p_out0 + p_out1) / 4
    def shr(p): return p + (cen - p) * shrink
    quad = [shr(p_in0), shr(p_in1), shr(p_out1), shr(p_out0)]          # a ring-plane quad (y = 0) in order
    yb, yf = y_back, y_front
    back = [Vector((q.x, yb, q.z)) for q in quad]
    mid = [jv(Vector((q.x, yf - cham, q.z))) for q in quad]
    face = [jv(Vector((q.x + (cen.x - q.x) * front_in, yf + R.uniform(-.12, .12), q.z + (cen.z - q.z) * front_in)), .05) for q in quad]
    verts = back + mid + face
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.append((i, j, 4 + j, 4 + i))           # sides back -> mid
        faces.append((4 + i, 4 + j, 8 + j, 8 + i))   # chamfer mid -> front
    faces.append((8, 9, 10, 11))                     # front face
    M.add(verts, faces, [Vector((cen.x, (yb + yf) / 2, cen.z))], col, jit=.04, seed=seed)

def build_gate_arch():
    """a chunky stone arch frame, about 38 x 9 x 27: 13 hand-cut blocks round the half-ellipse opening with a keystone that stands proud,
    a foot plinth each side, two iron lantern hooks on the jambs (the warm PointLight sits between them), moss on the plinths and the ring"""
    M = Mesh(); R = random.Random(7)
    N = 13; ths = arc_params(N)
    zmax = ARCH_B + 6.0
    col = form_col(0, zmax, 8, moss=.0, bands=False, front=.38)
    mosscol = form_col(0, zmax, 9, moss=.55, bands=False, front=.38)
    yb = -ARCH_D / 2
    for i in range(N):
        t0, t1 = ths[i], ths[i + 1]
        key = (i == N // 2)
        th = [4.4, 4.8, 4.2, 5.0, 4.5, 4.7, 5.4, 4.6, 4.3, 4.9, 4.2, 4.8, 4.5][i]
        th1 = th if not key else th + .5
        d = ARCH_D * (1.0 if not key else 1.0) + (R.uniform(-.25, .25) if not key else 0)
        yf = -ARCH_D / 2 + d + (1.0 if key else R.uniform(-.1, .5))
        c = mosscol if i in (2, 7, 8, 10) else col
        pi0, pi1 = ring_point(t0, 0), ring_point(t1, 0)
        po0, po1 = ring_point(t0, th), ring_point(t1, th1)
        if key:  # wedge: the keystone is wider at the outside
            po0, po1 = ring_point(t0 - .02, th + 1.4), ring_point(t1 + .02, th + 1.4)
        block(M, pi0, pi1, po0, po1, yb, yf, c, 70 + i)
    # foot plinths: wide low blocks beside the jamb feet
    for s in (-1, 1):
        x0, x1 = ARCH_A - .2, ARCH_A + 4.9
        pts = [Vector((s * x0, 0, 0)), Vector((s * x1, 0, 0)), Vector((s * x1, 0, 2.4)), Vector((s * x0, 0, 2.7))]
        block(M, pts[0], pts[1], pts[3], pts[2], yb, yb + ARCH_D + .9, col, 90 + s, shrink=.03, cham=.5)
    # moss on the plinths and over the shoulders of the ring
    moss(M, (-ARCH_A - 3.0, 1.0, 2.9), (2.6, 2.0, .45), 101)
    moss(M, (ARCH_A + 2.7, 1.6, 2.9), (2.2, 1.8, .45), 102)
    sh = ring_point(math.radians(58), 3.9); moss(M, (sh.x, 0.3, sh.z + .5), (2.4, 2.1, .5), 103)
    ARCH_INFO['block_front'] = max(p.y for p in M.v); ARCH_INFO['back'] = yb   # before the hooks: the hooks stand out beyond the block fronts
    # lantern hooks: an iron plate on each jamb face and a J-shaped arm out and down, ring tip up
    for s in (-1, 1):
        hx = s * (ARCH_A + 1.9); hz = 10.4; yf = -ARCH_D / 2 + ARCH_D + .1
        v, f, rf = tube([Vector((hx, yf - .15, hz)), Vector((hx, yf + 1.3, hz + .12)), Vector((hx, yf + 2.6, hz + .05)), Vector((hx, yf + 3.3, hz - .5)), Vector((hx, yf + 3.15, hz - 1.35)), Vector((hx, yf + 2.75, hz - 1.7))],
                        [.5, .45, .45, .42, .34, .22], 5, tip=False, seed=s + 3, wob=.04)
        M.add(v, f, rf, lambda p, n: mix(IRON_LO, IRON_HI, n.z * .5 + .5), jit=.02, seed=4)
        plate = [Vector((hx + dx, yf + .02 + (.2 if (dx, dz) == (0, 0) else 0), hz + dz)) for dx, dz in [(-.7, -1.0), (.7, -1.0), (.7, 1.0), (-.7, 1.0)]]
        pv = plate + [p + Vector((0, .35, 0)) for p in plate]
        pf = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        M.add(pv, pf, [Vector((hx, yf - 1, hz))], lambda p, n: IRON_LO * 1.1, jit=.01, seed=6)
    return M          # no flatten_back: the blocks have no back faces and their back plane is at y = -ARCH_D / 2 on purpose

FORMS = {
    'slab_stack': ('cave_rockform_slabs_v3', build_slab_stack),
    'buttress': ('cave_rockform_buttress_v3', build_buttress),
    'overhang': ('cave_rockform_ledge_v3', build_overhang),
    'tumble': ('cave_rockform_tumble_v3', build_tumble),
    'fins': ('cave_rockform_fins_v3', build_fins),
    'terrace': ('cave_rockform_terrace_v3', build_terrace),
}
ARCH = ('cave_gate_arch_v3', build_gate_arch)
ALL = dict(FORMS); ALL['gate_arch'] = ARCH

def make_mesh(key):
    name, fn = ALL[key]
    M = fn()
    ob = M.to_object(name, flat=True)
    ob.data.materials.append(vc_material())
    ox, oy, oz = centre_xy(ob)
    ob['pivot_oy'] = oy      # the bbox centre in Y before centring: ARCH_INFO y values minus this = studs from the pivot
    return ob

def mean_srgb(ob):
    """area-weighted mean sRGB of the Col attribute (the Roblox side shows it as is, ColorSequence of SRGB)"""
    me = ob.data; ca = me.color_attributes['Col']; tot = Vector((0, 0, 0)); area = 0.0
    def to_s(x): return 12.92 * x if x <= .0031308 else 1.055 * x ** (1 / 2.4) - .055
    for p in me.polygons:
        c = Vector((0, 0, 0))
        for li in p.loop_indices: c += Vector(ca.data[li].color[:3])
        c /= len(p.loop_indices); tot += c * p.area; area += p.area
    m = tot / max(area, 1e-9)
    return tuple(round(255 * to_s(x)) for x in m)

# =============================================================== stages: export
def stage_export():
    os.makedirs(FBX_V3, exist_ok=True)
    reset()
    obs = []; x = 0
    for key in ALL:
        ob = make_mesh(key); ob.location = (x, 0, 0); x += 26; obs.append(ob)
        d = ob.dimensions
        print("REPORT", ob.name, "tris", tri_count(ob), "verts", len(ob.data.vertices), "size", [round(d.x, 2), round(d.y, 2), round(d.z, 2)],
              "materials", len(ob.data.materials), "mean_rgb", mean_srgb(ob))
        if key == 'gate_arch':
            print("REPORT arch block_front_from_pivot", round(ARCH_INFO['block_front'] - ob['pivot_oy'], 2), "back_from_pivot", round(ARCH_INFO['back'] - ob['pivot_oy'], 2),
                  "(Blender +Y = Roblox -Z, the cave side)")
    for ob in obs:
        for o in bpy.context.selected_objects: o.select_set(False)
        loc = ob.location.copy(); ob.location = (0, 0, 0); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(FBX_V3, ob.name + ".fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, axis_forward="-Z", axis_up="Y", colors_type="SRGB", mesh_smooth_type="FACE",
                                 add_leaf_bones=False, bake_anim=False)
        ob.location = loc; ob.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)

# =============================================================== stages: render (a dim, warm, lamp-lit cave look, docs/114 s6.1)
# The scene mimics the hub: one matte warm Concrete wall (124,104,86) with a thin moss skirt, an orange cracked floor, a low dark ceiling,
# a very dark warm ambient and a few warm point lights at head height like the wall lantern niches. The wall is a curved, low-poly, noise-displaced
# face with ~3 stud facets: an APPROXIMATION of today's terrain wall from the Studio screenshots (docs/evidence/2026-10-16-cave-organic/ 9, 10, 11),
# not a capture. Camera = the gameplay camera (70 degree FOV at about 46 studs, a little above the dino).
WALL_COL = lin("#7C6856")      # Concrete 124,104,86
FLOOR_A, FLOOR_B = lin("#8E5A34"), lin("#B0733F")   # the orange cracked floor of today's hub (approximation from the Studio screenshots)
LAMP = (1.0, .84, .62)
AMBIENT = 1.0
CURVE = 46.0

def wall_y(x, z, seed, curve=CURVE, notch=None):
    """depth of the wall surface (+Y = into the rock) at (x, z): the room curves round the camera (edges come towards it), swells and facets add
    +-2 studs; `notch` = (a, b, depth) pushes the faint half-ellipse gate niche back"""
    y = -(curve - math.sqrt(max(curve * curve - x * x, 0.0)))
    y += 2.6 * noise.noise(Vector((x / 9.0, z / 9.0, seed))) + 1.0 * noise.noise(Vector((x / 3.6, z / 3.6, seed + 4)))
    if notch:
        a, b, dep = notch
        r = math.hypot(abs(x) / a, z / b)
        if r < 1.0: y += dep
        elif r < 1.18: y += dep * (1.18 - r) / .18 * .8
    return y

def faceted_wall(x_half, z_top, seed, notch=None, step=3.0, curve=CURVE, moss_h=3.2):
    """today's wall, approximated (see above)"""
    nx = int(2 * x_half / step) + 1; nz = int(z_top / step) + 1
    R = random.Random(seed); verts = []; idx = {}
    for i in range(nx + 1):
        for k in range(nz + 1):
            x = -x_half + i * 2 * x_half / nx; z = k * z_top / nz
            x += R.uniform(-.5, .5) * step * .35
            if 0 < k < nz: z += R.uniform(-.5, .5) * step * .3
            verts.append(Vector((x, wall_y(x, z, seed, curve, notch), z))); idx[(i, k)] = len(verts) - 1
    faces = [(idx[(i, k)], idx[(i + 1, k)], idx[(i + 1, k + 1)], idx[(i, k + 1)]) for i in range(nx) for k in range(nz)]
    M = Mesh()
    def cf(p, n):
        t = max(0.0, min(1.0, p.z / 20.0))
        c = WALL_COL * (.9 + .2 * noise.noise(Vector((p.x * .5, p.y * .5, p.z * .5))) + .08 * n.z)
        c = mix(c, WALL_COL * 1.1, t * .12)
        if p.z < moss_h:  # moss skirt like the bd-490 dressing
            m = max(0.0, 1.0 - p.z / moss_h) * (.6 + .4 * noise.noise(Vector((p.x * .4, 0, 3))))
            c = mix(c, lin("#55803C") * .8, min(1.0, m * 1.1))
        return c
    M.add(verts, faces, [Vector((0, -200, 10))], cf, jit=.0, seed=seed)     # faces point at the camera (-Y)
    ob = M.to_object("wall", flat=True); ob.data.materials.append(vc_material("WallMat", rough=1.0))
    return ob

def cave_scene(res, samples, lamps, ceiling=True):
    sc = reset()
    sc.render.resolution_x, sc.render.resolution_y = res
    try: sc.render.engine = 'CYCLES'
    except TypeError: pass
    sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.device = 'CPU'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    w = bpy.data.worlds.new("CaveDark"); sc.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*lin("#3E3428"), 1); bg.inputs['Strength'].default_value = AMBIENT     # dark warm ambient (CaveLightingRules.Look.ambient 62,52,44 is dim)
    M = Mesh(); R = random.Random(3); n = 40; verts = []; idx = {}
    for i in range(n + 1):
        for k in range(n + 1):
            x = -100 + i * 200 / n + R.uniform(-1.2, 1.2); y = -90 + k * 150 / n + R.uniform(-1.2, 1.2)
            verts.append(Vector((x, y, R.uniform(-.25, .25)))); idx[(i, k)] = len(verts) - 1
    faces = [(idx[(i, k)], idx[(i + 1, k)], idx[(i + 1, k + 1)], idx[(i, k + 1)]) for i in range(n) for k in range(n)]
    M.add(verts, faces, [Vector((0, 0, -50))], lambda p, nn: mix(FLOOR_A, FLOOR_B, .5 + .5 * noise.noise(Vector((p.x * .3, p.y * .3, 1)))), jit=.03, seed=2)
    fo = M.to_object("floor", flat=True); fo.data.materials.append(vc_material("FloorMat", rough=1.0))
    if ceiling:
        cm = flat_material("Ceil", lin("#4A3A2E")); bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 38)); bpy.context.active_object.data.materials.append(cm)
    for (x, y, z, watt) in lamps:
        ld = bpy.data.lights.new("Lamp", 'POINT'); ld.energy = watt; ld.color = LAMP; ld.shadow_soft_size = .8
        lo = bpy.data.objects.new("Lamp", ld); sc.collection.objects.link(lo); lo.location = (x, y, z)
    return sc

def luminance(path):
    """mean Rec.709 luminance (0..1, display values) of a rendered PNG, read with Blender's own image loader"""
    import numpy as np
    im = bpy.data.images.load(path, check_existing=False)
    a = np.empty(len(im.pixels), dtype=np.float32); im.pixels.foreach_get(a)
    a = a.reshape(-1, 4)[:, :3]
    bpy.data.images.remove(im)
    return float((a[:, 0] * .2126 + a[:, 1] * .7152 + a[:, 2] * .0722).mean())

def stand_on_wall(ob, x, seed, curve=CURVE, notch=None, proud=-0.8, extra_yaw=0.0):
    """put a mesh (back plane at local y = -depth/2, front = local +Y) against the wall at x, facing into the room, the back buried by -proud"""
    y = wall_y(x, 0.0, seed, curve, notch)
    cy = -curve; ny = cy - y; nx = -x                       # inward = towards the centre of curvature (0, -curve)
    l = math.hypot(nx, ny); nx, ny = nx / l, ny / l
    yaw = math.atan2(-nx, ny) + extra_yaw
    d = ob.dimensions.y
    ob.location = (x + nx * (d / 2 + proud), y + ny * (d / 2 + proud), 0)
    ob.rotation_euler = (0, 0, yaw)

WALL_FORMS = [  # (form key, x along the wall, scale): hand-set along the wall and clear of the middle (the dino and the lane)
    ('buttress', -33, 1.0), ('slab_stack', -19, 1.0), ('terrace', -3, .8), ('fins', 8.5, 1.0), ('tumble', 21, 1.0), ('overhang', 36, 1.0),
]

def stage_render(out_dir, only=None):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    res = (1600, 900); lum = {}
    S = 56
    if os.environ.get('BD_FAST'): res, S = (800, 450), 14
    for version in ('v1', 'v2'):
        if only and 'wall' not in only: break
        wall_lamps = [(-40, -14, 8.0, 2600), (-14, -14, 7.5, 2600), (12, -14, 7.5, 2600), (40, -14, 8.0, 2600)]
        sc = cave_scene(res, S, wall_lamps)
        faceted_wall(60, 30, 5)
        tris = 0
        if version == 'v2':
            for key, x, s in WALL_FORMS:
                ob = make_mesh(key); ob.scale = (s, s, s); bpy.context.view_layer.update()
                stand_on_wall(ob, x, 5)
                tris += tri_count(ob)
        dino_stand_in((-4, -16, 0), math.radians(205), 1.0)
        camera(sc, (0, 0, 8.0), 46, 7, 0, fov=62, res=res)
        render(sc, os.path.join(out_dir, f"_wall_{version}.png"))
        lum[f"wall_{version}"] = (luminance(os.path.join(out_dir, f"_wall_{version}.png")), tris)
        print("RENDERED wall", version, lum[f"wall_{version}"])
    notch = (15.0, 20.0, 6.0)
    for version in ('v1', 'v2'):
        if only and 'arch' not in only: break
        lamps = [(-30, -14, 7.5, 2200), (30, -14, 7.5, 2200), (0, -26, 6.0, 1200)]
        if version == 'v2': lamps += [(0, -6.5, 13.0, 1500)]       # the arch light: one warm PointLight in front of the arch, between the two hooks
        sc = cave_scene(res, S, lamps)
        faceted_wall(60, 34, 11, notch=notch, curve=60.0)
        # the island glow: GateMist is a warm particle haze inside the niche; approximated by one soft warm light inside it (both versions)
        wy = wall_y(0, 10, 11, 60.0, notch)
        ld = bpy.data.lights.new("GateGlow", 'POINT'); ld.energy = 900; ld.color = (1, .78, .5); ld.shadow_soft_size = 3.0
        lo = bpy.data.objects.new("GateGlow", ld); sc.collection.objects.link(lo); lo.location = (0, wy - 3.0, 9.0)
        tris = 0
        if version == 'v2':
            ob = make_mesh('gate_arch'); tris = tri_count(ob)
            # the frame stands proud of the wall patch it frames (in the game the terrain wall curves in front of the outer blocks and buries
            # their edges a few studs; here the whole ring stays visible): front face 0.3 studs in front of the nearest wall point
            wmin = min(wall_y(x * 1.0, z * 1.0, 11, 60.0, None) for x in range(-20, 21, 2) for z in range(0, 27, 2))
            front = ARCH_INFO['block_front'] - ob['pivot_oy']      # block fronts stand this far in front of the pivot
            ob.location = (0, wmin - .3 + front, 0); ob.rotation_euler = (0, 0, math.pi)
        dino_stand_in((-6, -22, 0), math.radians(190), 1.0)
        camera(sc, (0, 0, 11), 44, 6, 0, fov=62, res=res)
        render(sc, os.path.join(out_dir, f"_arch_{version}.png"))
        lum[f"arch_{version}"] = (luminance(os.path.join(out_dir, f"_arch_{version}.png")), tris)
        print("RENDERED arch", version, lum[f"arch_{version}"])
    if lum:
        open(os.path.join(out_dir, "tris.txt"), "w").write("".join(f"{k} tris={v[1]} luminance={v[0]:.3f}" + chr(10) for k, v in lum.items()))
    if not only or 'lineup' in only:
        sc = reset(); res2 = (1600, 700)
        sc.render.resolution_x, sc.render.resolution_y = res2
        try: sc.render.engine = 'CYCLES'
        except TypeError: pass
        sc.cycles.samples = 40; sc.cycles.use_denoising = True; sc.cycles.device = 'CPU'
        sc.view_settings.view_transform = 'Standard'
        w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
        bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs['Color'].default_value = (*lin("#C9B9A4"), 1); bg.inputs['Strength'].default_value = 1.0
        ld = bpy.data.lights.new("Sun", 'SUN'); ld.energy = 3.2; ld.color = (1, .95, .85)
        so = bpy.data.objects.new("Sun", ld); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(-25))
        bpy.ops.mesh.primitive_plane_add(size=300); g = bpy.context.active_object; g.data.materials.append(flat_material("G", lin("#6A5A4A")))
        obs = {k: make_mesh(k) for k in FORMS}
        total = sum(o.dimensions.x for o in obs.values()) + 3.0 * (len(FORMS) - 1); x = -total / 2
        for key, ob in obs.items():
            ob.location = (-(x + ob.dimensions.x / 2), -8, 0); x += ob.dimensions.x + 3.0   # camera looks from +Y: screen left = +X
        camera(sc, (0, -8, 7), 80, 12, 180, fov=40, res=res2)
        render(sc, os.path.join(out_dir, "_lineup.png"))
        print("RENDERED lineup")
        for o in list(bpy.data.objects):
            if o.type == 'MESH' and o.name.startswith("cave_rockform"): bpy.data.objects.remove(o)
        ob = make_mesh('gate_arch'); ob.location = (0, 0, 0)
        camera(sc, (0, 0, 11), 62, 12, 155, fov=40, res=res2)
        render(sc, os.path.join(out_dir, "_archclose.png"))
        print("RENDERED archclose")

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[0] if argv else "export"
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs", "evidence", "2026-10-17-cave")
    only = argv[2].split(",") if len(argv) > 2 else None
    if stage == "export": stage_export()
    elif stage == "render": stage_render(out, only)
