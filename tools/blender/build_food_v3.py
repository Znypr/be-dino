# Be Dino! BD-1208 step 3: V3 food pickups, the approved food icons come to life (docs/241 W6, W7; sheet
# docs/evidence/2026-11-15-board/sheet-food-chatgpt.jpg). Same look as the V3 trees, plants and ground props.
# Run headless:  blender -b -P tools/blender/build_food_v3.py -- <stage> [out_dir] [shots]
#   stages: export -> write assets/blender/world/fbx_v3/food_*_v3_[ab].fbx + WorldKitV3_Food.blend + tri report
#           render -> lineup (version 1 = the current kit food from assets/blender/world/fbx, version 2 = the new food) and a
#                     play-height shot with a spawn-size dino, into <out_dir>
# Every pickup is ONE mesh (FoodService uses the kit MeshPart as the pickup part), shaped by hand from placed berries, drupelets,
# leaves, stems, straw strands and cut stones (no scatter, no generators). ONE vertex-colour material (Col attribute), flat per-face
# colours, 1 unit = 1 stud, Z up, pivot at the bbox bottom centre (lowest point z=0). The game scales each pickup so its largest side
# is the kind size (src/shared/ScaleLadder.luau Food), so only proportions matter here.
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_trees_v3 as T
from build_trees_v3 import Mesh, tube, cluster, shade3, lin, mix, vc_material, tri_count, centre_xy
from build_trees_v3 import reset, world_setup, camera, dino_stand_in, render, ROOT
import build_plants_v3 as P
import build_ground_props_v3 as G

FBX_V3 = T.FBX_V3
FBX_V1 = os.path.join(ROOT, "assets", "blender", "world", "fbx")

# ---------------------------------------------------------------- palette (icon colours, a touch deeper so they hold in daylight)
BLUE_LO, BLUE_MID, BLUE_HI = lin("#23307E"), lin("#3B52C4"), lin("#8EA6F4")
RASP_LO, RASP_MID, RASP_HI = lin("#7A1530"), lin("#C8284A"), lin("#FF6F86")
APPLE_LO, APPLE_MID, APPLE_HI = lin("#8E1A1E"), lin("#D9302C"), lin("#FF8A6E")
ORANGE_LO, ORANGE_MID, ORANGE_HI = lin("#C4561A"), lin("#F28A24"), lin("#FFC46A")
LEAF_LO, LEAF_MID, LEAF_HI = lin("#2F7A34"), lin("#4FA83E"), lin("#9AD660")
STEM_LO, STEM_HI = lin("#5A3A22"), lin("#8E6238")
SHELL_LO, SHELL_MID, SHELL_HI = lin("#CDB892"), lin("#EBDDBB"), lin("#FFF6E0")
SPOT_PURPLE, SPOT_PURPLE_HI = lin("#8E4FB8"), lin("#B57AD8")
SPOT_GREEN, SPOT_GREEN_HI = lin("#5E9E3A"), lin("#8CC45A")
SPOT_BLUE, SPOT_BLUE_HI = lin("#3F78C8"), lin("#76A8E8")
STRAW_LO, STRAW_MID, STRAW_HI = lin("#9A6A26"), lin("#D4A044"), lin("#F2CF78")
AMBER_LO, AMBER_MID, AMBER_HI = lin("#A8420A"), lin("#F08A14"), lin("#FFD866")
FOSSIL = lin("#8A3E0C")

# ---------------------------------------------------------------- smooth mesh (owner 2026-11-15: "too low poly")
class SMesh(Mesh):
    """Mesh with per-part smooth shading: parts added with smooth=True get smooth normals and per-vertex colours from the
    vertex normal (no per-face jitter), so round fruit, berries and eggs read soft and glossy like the icons."""
    def __init__(self): super().__init__(); self.parts = []
    def add(self, verts, faces, ref, colfn, jit=.03, seed=0, smooth=False):
        f0 = len(self.f)
        super().add(verts, faces, ref, colfn, jit=0 if smooth else jit, seed=seed)
        self.parts.append((f0, len(self.f), colfn, smooth))
    def to_object(self, name, flat=True):
        ob = super().to_object(name, flat=True)
        me = ob.data; ca = me.color_attributes['Col']
        for f0, f1, colfn, smooth in self.parts:
            if not smooth: continue
            for pi in range(f0, f1):
                p = me.polygons[pi]; p.use_smooth = True
        me.update()
        for f0, f1, colfn, smooth in self.parts:
            if not smooth: continue
            for pi in range(f0, f1):
                p = me.polygons[pi]
                for li in p.loop_indices:
                    vi = me.loops[li].vertex_index; v = me.vertices[vi]
                    c = colfn(Vector(v.co), Vector(v.normal))
                    ca.data[li].color = (max(0, min(1, c.x)), max(0, min(1, c.y)), max(0, min(1, c.z)), 1.0)
        return ob

def weld(M, f0):
    pass

# ---------------------------------------------------------------- shape helpers
def ball(center, r, subdiv, shape=None, seed=0, amp=0.0):
    """icosphere; shape(unit_dir) -> scale vector applied before r (dents, egg taper); returns verts, faces, ref"""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    rnd = random.Random(seed); c = Vector(center); verts = []
    for v in bm.verts:
        d = v.co.normalized()
        p = shape(d) if shape else d.copy()
        if amp: p *= 1 + rnd.uniform(-amp, amp)
        verts.append(c + p * r)
    idx = {v.index: i for i, v in enumerate(bm.verts)}
    faces = [tuple(idx[v.index] for v in f.verts) for f in bm.faces]; bm.free()
    return verts, faces, [c]

def lit(lo, mid, hi, center, nzw=.75, key=Vector((-.35, -.45, .82))):
    """round-fruit shading: dark underside, mid body, a bright cap towards the sun side (reads as the icon gloss)"""
    k_dir = key.normalized(); c = Vector(center)
    def f(p, n):
        k = max(0.0, min(1.0, (n.z * .5 + .5) * nzw + (n.dot(k_dir) * .5 + .5) * (1 - nzw)))
        col = mix(lo, mid, k * 2) if k < .5 else mix(mid, hi, (k - .5) * 1.6)
        if n.dot(k_dir) > .86: col = mix(col, hi, .7)  # small specular facet
        return col
    return f

def leaf(M, base, yaw, lean, reach, height, width, seed=0):
    P.blade(M, base, yaw, lean, reach, height, width, (.3, .7, .98, .9, .55, 0), P.leafcol(LEAF_LO, LEAF_MID, LEAF_HI, base[2] - .1, base[2] + height + .1, .6),
            thick=.22, bow=.55, flank=.3, seed=seed)

def stem(M, a, b, r=.06, seed=0):
    v, f, ref = tube([Vector(a), (Vector(a) + Vector(b)) / 2 + Vector((.02, 0, .02)), Vector(b)], (r, r * .8), 8, tip=False, seed=seed)
    M.add(v, f, ref, lambda p, n: mix(STEM_LO, STEM_HI, n.z * .5 + .5), jit=.01, seed=seed)

def spot_fn(base, spots, spot_lo, spot_hi, center):
    """egg shell: base shading, round spots where the direction from the centre is close to a spot direction"""
    c = Vector(center); sp = [(Vector(d).normalized(), math.cos(rad)) for d, rad in spots]
    def f(p, n):
        d = (p - c).normalized()
        for s, cr in sp:
            if d.dot(s) > cr: return mix(spot_lo, spot_hi, n.z * .4 + .3)
        return base(p, n)
    return f

# =============================================================== V3 FOOD
def build_berry_blue():
    """blueberry trio with two leaves (icon: berry, blue); ~1.25 x 1.0 x 0.9"""
    M = SMesh()
    for i, (c, r) in enumerate([((-.28, -.05, .36), .36), ((.32, -.12, .33), .33), ((.04, .32, .38), .38)]):
        dent = lambda d: Vector((d.x, d.y, d.z * .9 - .22 * math.exp(-((d.x ** 2 + d.y ** 2) / .08)) * max(0, d.z)))
        v, f, ref = ball(c, r, 2, dent, seed=i)
        M.add(v, f, ref, lit(BLUE_LO, BLUE_MID, BLUE_HI, c), seed=i, smooth=True)
        # five-point crown on top (the blueberry star): a small dark ring of gems
        top = Vector(c) + Vector((0, 0, r * .78))
        for k in range(3):
            a = k * 2 * math.pi / 3 + i
            v, f, ref = G.gem(top + Vector((math.cos(a), math.sin(a), 0)) * r * .2, r * .09, .8)
            M.add(v, f, ref, lambda p, n: BLUE_LO * .8, jit=.0, seed=k)
    leaf(M, (.05, .1, .62), math.radians(40), math.radians(62), .55, .32, .34, seed=3)
    leaf(M, (.0, .12, .6), math.radians(150), math.radians(66), .5, .26, .3, seed=4)
    stem(M, (.02, .1, .55), (.03, .12, .74), .045)
    return M

def build_berry_rasp():
    """one plump raspberry from round drupelets, leaf crown (icon: red berry); ~1.0 x 1.0 x 1.1"""
    M = SMesh()
    for j, (bc, s, tilt) in enumerate([((0, 0, 0), 1.5, 0.0)]):
        bc = Vector(bc)
        rows = [(.18, 5, .5), (.42, 7, .58), (.68, 7, .52), (.9, 5, .36), (1.06, 1, .0)]
        for zi, (z, n, rad) in enumerate(rows):
            for k in range(n):
                a = k * 2 * math.pi / n + zi * .45
                c = bc + Vector((math.cos(a) * rad * .42 + tilt * z * .18, math.sin(a) * rad * .42, z * .5)) * s
                v, f, ref = ball(c, .13 * s, 1, seed=zi * 10 + k)
                M.add(v, f, ref, lit(RASP_LO, RASP_MID, RASP_HI, c, nzw=.6), seed=k + j, smooth=True)
        # inner core so no gaps show between drupelets
        v, f, ref = ball(bc + Vector((tilt * .08, 0, .3 * s)), .26 * s, 1, lambda d: Vector((d.x, d.y, d.z * 1.25)))
        M.add(v, f, ref, lambda p, n: RASP_LO, jit=.0)
        for k in range(4):
            leaf(M, tuple(bc + Vector((0, 0, .58 * s))), k * math.pi / 2 + .4 + j, math.radians(80), .26 * s, -.02, .16 * s, seed=10 + k)
    return M

def apple_shape(d):
    """apple: wide shoulders, dimples top and bottom"""
    r = 1.0 + .08 * max(0, d.z) - .06 * max(0, -d.z)
    p = Vector((d.x, d.y, d.z * .9)) * r
    w = math.exp(-((d.x ** 2 + d.y ** 2) / .06))
    p.z -= .3 * w * (1 if d.z > 0 else -.6)
    return p

def build_fruit_apple():
    """red apple, stem and one leaf (icon: apple); ~1.1 x 1.0 x 1.2"""
    M = SMesh(); c = (0, 0, .48)
    v, f, ref = ball(c, .5, 3, apple_shape, seed=1)
    M.add(v, f, ref, lit(APPLE_LO, APPLE_MID, APPLE_HI, c), smooth=True)
    stem(M, (0, 0, .7), (.06, .02, 1.0), .05)
    leaf(M, (.05, .02, .9), math.radians(20), math.radians(70), .46, .14, .3, seed=2)
    return M

def build_fruit_orange():
    """orange with a short stem and a leaf (icon: orange); ~1.1 x 1.0 x 1.05"""
    M = SMesh(); c = (0, 0, .47)
    pores = lambda d: Vector((d.x, d.y, d.z * .93)) * (1 + .018 * noise.noise(d * 6.0))
    v, f, ref = ball(c, .5, 3, pores, seed=2)
    M.add(v, f, ref, lit(ORANGE_LO, ORANGE_MID, ORANGE_HI, c), smooth=True)
    stem(M, (0, 0, .9), (.02, 0, 1.0), .05)
    leaf(M, (.02, 0, .97), math.radians(-30), math.radians(72), .44, .1, .28, seed=3)
    return M

def egg_shape(d):
    z = d.z * 1.28
    taper = 1 - .16 * (z / 1.28)
    return Vector((d.x * taper, d.y * taper, z))

def nest(M, r, h, seed=0):
    """straw nest ring: three twisted strands round a low bowl, plus a few loose straws"""
    for s in range(3):
        path = []
        for k in range(19):
            a = k * 2 * math.pi / 18 + s * .7
            rr = r * (1 + .06 * math.sin(a * 3 + s))
            path.append(Vector((math.cos(a) * rr, math.sin(a) * rr, h * (.32 + .3 * s) + .05 * math.sin(a * 4 + s))))
        v, f, ref = tube(path, [h * .36] * 19, 6, tip=False, seed=seed + s, wob=.08)
        M.add(v, f, ref, shade3(STRAW_LO, STRAW_MID, STRAW_HI, 0, h * 1.2, .65), seed=seed + s, smooth=True)
    rnd = random.Random(seed)
    for k in range(5):
        a = rnd.uniform(0, 2 * math.pi)
        p0 = Vector((math.cos(a) * r * 1.05, math.sin(a) * r * 1.05, h * .9))
        p1 = p0 + Vector((math.cos(a + 1.3) * .35, math.sin(a + 1.3) * .35, .08))
        v, f, ref = tube([p0, (p0 + p1) / 2 + Vector((0, 0, .05)), p1], (.035, .02), 4, tip=True, seed=k)
        M.add(v, f, ref, lambda p, n: mix(STRAW_MID, STRAW_HI, n.z * .5 + .5), jit=.03, seed=k)
    # bowl floor
    v, f, ref = cluster(Vector((0, 0, h * .25)), (r * .95, r * .95, h * .3), seed, amp=.04, flat_bottom=.5, subdiv=2)
    M.add(v, f, ref, shade3(STRAW_LO, STRAW_MID, STRAW_MID, 0, h * .5, .5), seed=seed, smooth=True)

def spot_disc(M, c, r_shell_fn, d, rad, col_lo, col_hi, seed=0):
    """one round spot: an 8-sided disc lying on the shell, raised a hair along the shell normal"""
    d = Vector(d).normalized()
    p0 = Vector(c) + r_shell_fn(d)
    up = d; t1 = up.cross(Vector((0, 0, 1)))
    if t1.length < .1: t1 = up.cross(Vector((1, 0, 0)))
    t1.normalize(); t2 = up.cross(t1)
    ring = []
    for k in range(12):
        a = k * 2 * math.pi / 12
        q = d + (t1 * math.cos(a) + t2 * math.sin(a)) * rad
        ring.append(Vector(c) + r_shell_fn(q.normalized()) * 1.006)
    verts = [p0 * 1.0 + up * .006] + ring
    faces = [(0, 1 + k, 1 + (k + 1) % 12) for k in range(12)]
    M.add(verts, faces, [Vector(c)], lambda p, n: mix(col_lo, col_hi, n.z * .35 + .35), seed=seed, smooth=True)

def build_egg(spots, spot_lo, spot_hi, seed):
    """spotted egg sitting in a straw nest (icon: egg); ~1.3 x 1.3 x 1.35"""
    M = SMesh()
    nest(M, .58, .34, seed)
    c = (0, 0, .62); R = .45
    v, f, ref = ball(c, R, 3, egg_shape, seed=seed)
    M.add(v, f, ref, lit(SHELL_LO, SHELL_MID, SHELL_HI, c, nzw=.65), seed=seed, smooth=True)
    for i, (d, rad) in enumerate(spots):
        spot_disc(M, c, lambda q: egg_shape(q) * R, d, rad * .85, spot_lo, spot_hi, seed=i)
    return M

SPOTS_A = [((.9, -.3, .3), .36), ((-.4, -.9, .1), .3), ((-.7, .5, .55), .33), ((.2, .5, .9), .26), ((.55, .75, -.1), .28), ((-.95, -.1, -.25), .24), ((.1, -.75, .75), .22)]
SPOTS_B = [((.7, -.6, .5), .3), ((-.6, -.7, .2), .34), ((-.5, .7, .7), .28), ((.8, .5, .0), .32), ((0, .2, 1.0), .2), ((.05, -.95, -.2), .26)]

STONE_LO, STONE_MID, STONE_HI = lin("#5E5A57"), lin("#85807A"), lin("#B3ADA4")
MOSS_LO, MOSS_HI = lin("#4E8A3A"), lin("#8CC45A")
def stone_fn(zlo, zhi, moss_above=None):
    def f(p, n):
        k = max(0.0, min(1.0, (n.z * .5 + .5) * .7 + (p.z - zlo) / max(zhi - zlo, 1e-6) * .3))
        c = mix(STONE_LO, STONE_MID, k * 2) if k < .5 else mix(STONE_MID, STONE_HI, (k - .5) * 2)
        if moss_above is not None and p.z > moss_above and n.z > .45: c = mix(MOSS_LO, MOSS_HI, n.z * .6 + .2 * noise.noise(p * 4))
        return c
    return f

def amber_lens_fn(L, a, b):
    """glowing amber: golden heart, deep orange rim, a bright glint top left (icon look)"""
    L = Vector(L)
    def f(p, n):
        q = p - L; r = min(1.0, math.sqrt((q.x / a) ** 2 + (q.z / b) ** 2))
        c = mix(AMBER_HI, AMBER_MID, r * 1.3) if r < .75 else mix(AMBER_MID, AMBER_LO, (r - .75) * 4)
        if n.dot(Vector((-.45, -.6, .65)).normalized()) > .965: c = mix(c, lin("#FFF4C8"), .6)
        return c
    return f

def lens_point(L, a, d, b, x, z, lift=.01):
    """point on the front (-Y) face of the amber lens at local x, z"""
    t = max(0.0, 1 - (x / a) ** 2 - (z / b) ** 2)
    return Vector(L) + Vector((x, -d * math.sqrt(t) - lift, z))

def fossil_fern(M, L, a, d, b, scale=1.0, seed=0, turn=.75):
    """a tiny fern fossil inside the amber, lying diagonally on the lens face (never a centre line), dark amber"""
    col = lambda p, n: FOSSIL
    c, s_ = math.cos(turn), math.sin(turn)
    rot = lambda x, z: (x * c - z * s_, x * s_ + z * c)
    sp = [(-.04, -.36), (.02, -.16), (.05, .04), (.03, .22), (-.02, .34)]
    path = [lens_point(L, a, d, b, *rot(x * scale, z * scale)) for x, z in sp]
    v, f, ref = tube(path, (.032 * scale, .018 * scale), 5, tip=True, seed=seed); M.add(v, f, ref, col, seed=seed, smooth=True)
    for k, (x, z) in enumerate(sp[1:4]):
        for side in (-1, 1):
            q = [lens_point(L, a, d, b, *rot((x + side * dx) * scale, (z + dz) * scale)) for dx, dz in ((0, 0), (.09, .06), (.17, .08))]
            v, f, ref = tube(q, (.028 * scale, .012 * scale), 4, tip=True, seed=k); M.add(v, f, ref, col, seed=k, smooth=True)

def build_amber(seed, variant):
    """amber in rock (icon): an upright, chiselled grey boulder with a glossy amber window high on its face (fossil fern inside),
    two small stones at its foot; ~1.5 x 1.1 x 1.6"""
    M = SMesh()
    up = (.66, .5, .8) if variant == "a" else (.72, .48, .72)
    cuts = [((0, 0, 1), .82), ((1, .2, .55), .72), ((-1, .3, .6), .7), ((.3, 1, .3), .78), ((.7, -.6, .25), .8), ((-.7, -.5, .3), .8),
            ((.4, .3, 1), .78), ((-.5, .2, 1), .76)]
    rc = Vector((0, .12, .78 if variant == 'a' else .7))
    v, f, ref = G.rock(rc, up, seed, 2, cuts, amp=.05, flat=.95, yaw=0.0, tol=math.radians(7))
    M.add(v, f, ref, stone_fn(0, 1.6, moss_above=1.18 if variant == 'b' else None), jit=.03, seed=seed)
    for k, (c, r) in enumerate([((-.62, -.18, .2), (.3, .28, .22)), ((.6, -.05, .16), (.24, .26, .18))]):
        v, f, ref = G.rock(Vector(c), r, seed + 3 + k, 1, [((0, 0, 1), .7), ((1, .2, .4), .8)], amp=.06, flat=.6, yaw=k)
        M.add(v, f, ref, stone_fn(0, .45), jit=.03, seed=k)
    # amber window: a domed slab set into the rock face, high up, slightly tilted to the sky
    a, d, b = (.48, .22, .52) if variant == "a" else (.52, .22, .42)
    L = Vector((.03, -.32, .84 if variant == "a" else .72))
    tilt = math.radians(14)
    def lens(u):
        q = Vector((u.x * a, u.y * d, u.z * b))
        return Vector((q.x, q.y * math.cos(tilt) - q.z * math.sin(tilt), q.y * math.sin(tilt) + q.z * math.cos(tilt)))
    v, f, ref = ball(L, 1.0, 3, lens)
    M.add(v, f, ref, amber_lens_fn(L, a, b), smooth=True)
    fossil_fern(M, L, a, d * 1.05, b, scale=.74 if variant == "a" else .6, seed=seed, turn=.8 if variant == 'a' else -.7)
    if variant == 'b':
        for i, (c, r) in enumerate([((.5, -.42, .09), .1), ((-.32, -.48, .07), .08)]):
            v, f, ref = ball(c, r, 2, lambda u: Vector((u.x, u.y, u.z * .7)), seed=i)
            M.add(v, f, ref, amber_lens_fn(c, r, r * .7), seed=i, smooth=True)
    return M

FOODS = {
    'berry_a': ('food_berry_v3_a', build_berry_blue),
    'berry_b': ('food_berry_v3_b', build_berry_rasp),
    'fruit_a': ('food_fruit_v3_a', build_fruit_apple),
    'fruit_b': ('food_fruit_v3_b', build_fruit_orange),
    'egg_a': ('food_egg_v3_a', lambda: build_egg(SPOTS_A, SPOT_PURPLE, SPOT_PURPLE_HI, 3)),
    'egg_b': ('food_egg_v3_b', lambda: build_egg(SPOTS_B, SPOT_GREEN, SPOT_GREEN_HI, 5)),
    'amber_a': ('food_amber_v3_a', lambda: build_amber(11, 'a')),
    'amber_b': ('food_amber_v3_b', lambda: build_amber(17, 'b')),
}
KIND_SIZE = {'berry': .7, 'fruit': 1.0, 'egg': 1.3, 'amber': 1.5}  # src/shared/ScaleLadder.luau Food (largest side in game)

# =============================================================== stages
def make_food(key):
    name, fn = FOODS[key]
    ob = fn().to_object(name, flat=True)
    ob.data.materials.append(vc_material())
    centre_xy(ob)
    return ob

def game_scale(ob, key, mult=1.0):
    s = KIND_SIZE[key.split('_')[0]] * mult / max(ob.dimensions)
    ob.scale = (s, s, s)

def stage_export():
    os.makedirs(FBX_V3, exist_ok=True)
    reset(); obs = []; x = 0
    for key in FOODS:
        ob = make_food(key); ob.location = (x, 0, 0); x += 3; obs.append(ob)
        d = ob.dimensions
        print("REPORT", ob.name, "tris", tri_count(ob), "verts", len(ob.data.vertices), "size", [round(d.x, 2), round(d.y, 2), round(d.z, 2)], "materials", len(ob.data.materials))
    for ob in obs:
        for o in bpy.context.selected_objects: o.select_set(False)
        loc = ob.location.copy(); ob.location = (0, 0, 0); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(FBX_V3, ob.name + ".fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, axis_forward="-Z", axis_up="Y", colors_type="SRGB", mesh_smooth_type="FACE",
                                 add_leaf_bones=False, bake_anim=False)
        ob.location = loc; ob.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "assets", "blender", "world", "WorldKitV3_Food.blend"))

def import_kit(fname):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX_V1, fname))
    ob = [o for o in bpy.data.objects if o not in before and o.type == 'MESH'][0]
    for o in list(bpy.data.objects):
        if o not in before and o.type != 'MESH': bpy.data.objects.remove(o)
    ob.rotation_euler = (0, 0, 0); ob.parent = None; ob.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    return ob

def stage_render(out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    res = (1600, 900)
    keys = list(FOODS)
    if not only or 'lineup' in only:
        # close lineup: top row = today's kit food, bottom row = V3; every item at 1.6x its game size so the shapes read
        sc = reset(); world_setup(sc, res); sc.cycles.samples = 64
        for ri, version in enumerate(('v1', 'v2')):
            for i, k in enumerate(keys):
                ob = import_kit(f"food_{k}.fbx") if version == 'v1' else make_food(k)
                if version == 'v1':
                    me = ob.data; zs = [v.co.z for v in me.vertices]
                game_scale(ob, k, 1.6)
                ob.location = (-8.4 + i * 2.4, 2.2 - ri * 3.6, 0)
                if version == 'v1':
                    bpy.context.view_layer.update()
                    lo = min((ob.matrix_world @ v.co).z for v in ob.data.vertices); ob.location.z -= lo
        camera(sc, (0, 0.3, .6), 15.5, 30, 0, fov=45, res=res)
        render(sc, os.path.join(out_dir, "food-lineup-v1-top-v3-bottom.png")); print("RENDERED lineup")
    if not only or 'hero' in only:
        sc = reset(); world_setup(sc, res); sc.cycles.samples = 64
        for i, k in enumerate(keys):
            ob = make_food(k); s = 1.0; ob.location = ((i % 4) * 2.2 - 3.3, -(i // 4) * 2.4 + 1.2, 0); ob.rotation_euler = (0, 0, .3)
        camera(sc, (0, -.4, .55), 7.2, 24, 0, fov=45, res=res)
        render(sc, os.path.join(out_dir, "food-v3-hero.png")); print("RENDERED hero")
    if not only or 'play' in only:
        # play height: spawn-size dino, food at true game size in a small patch beside a berry bush
        for version in ('v1', 'v2'):
            sc = reset(); world_setup(sc, res); sc.cycles.samples = 64
            rnd = random.Random(4)
            spots = [(-1.5, -2.0), (.4, -1.2), (1.8, -2.6), (-.4, -3.4), (2.6, -.6), (-2.6, -.4), (1.0, .6), (3.4, -2.0), (-1.0, .9), (.2, -4.6)]
            mix_keys = ['berry_a', 'berry_b', 'berry_a', 'fruit_a', 'berry_b', 'fruit_b', 'berry_a', 'egg_a', 'berry_b', 'amber_a']
            for (x, y), k in zip(spots, mix_keys):
                ob = import_kit(f"food_{k}.fbx") if version == 'v1' else make_food(k)
                game_scale(ob, k); ob.location = (x, y, 0); ob.rotation_euler = (0, 0, rnd.uniform(0, 6.3))
                if version == 'v1':
                    bpy.context.view_layer.update()
                    lo = min((ob.matrix_world @ v.co).z for v in ob.data.vertices); ob.location.z -= lo
            bush = G.make_prop('bush_berry'); bush.location = (-2.8, 3.2, 0)
            dino_stand_in((-6.5, -4.5, 0), math.radians(60), 1.0)
            camera(sc, (-.5, -1.5, 1.2), 17, 22, 20, res=res)
            render(sc, os.path.join(out_dir, f"food-play-{version}.png")); print("RENDERED play", version)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[0] if argv else "export"
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs", "evidence", "2026-11-15-food-v3")
    only = argv[2].split(",") if len(argv) > 2 else None
    if stage == "export": stage_export()
    elif stage == "render": stage_render(out, only)
