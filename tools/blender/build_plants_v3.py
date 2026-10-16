# Be Dino! BD-463 step 1: grass tufts, a jungle plant, flower clusters and a fern (V3 style, same look as the V3 trees and ground props).
# Run headless:  blender -b -P tools/blender/build_plants_v3.py -- <stage> [out_dir] [shots]
#   stages: export -> write assets/blender/world/fbx_v3/plant_*_v3.fbx + WorldKitV3_Plants.blend + tri report
#           render -> comparison renders (version 1 = the current kit grass / flowers / ferns, imported from assets/blender/world/fbx,
#                     version 2 = the new plants) into <out_dir>
# Every plant is shaped by hand from hand-placed blades, leaves, stalks and petals (no scatter, no generators): a blade or leaf is a
# CLOSED little prism (a raised midrib over two flanks plus a flat underside) bent along a hand-placed curve, so it has real width, is
# solid from every side (Roblox culls back faces) and shades in two facets like a folded leaf instead of a thin flat triangle.
# ONE vertex-colour material each (Col attribute), flat per-face colours. 1 unit = 1 stud, Z up, pivot at the bbox bottom centre
# (lowest point z=0), same FBX settings as fbx_v3 (tools/blender/build_trees_v3.py).
# Scoped owner decision 2026-10-16: Blender is allowed for world art; models must look hand-crafted, not like primitives.
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_trees_v3 as T
from build_trees_v3 import Mesh, tube, cluster, shade3, lin, mix, vc_material, tri_count, centre_xy
from build_trees_v3 import reset, world_setup, camera, place, dino_stand_in, render, ROOT

FBX_V3 = T.FBX_V3
FBX_V1 = os.path.join(ROOT, "assets", "blender", "world", "fbx")

# ---------------------------------------------------------------- palette (docs/114 s5.8: ground #84A644 = 132,166,68; foliage a little less
# saturated than the old neon greens, warm accents; tufts are darker at the root and lighter at the tip so they read against the ground)
GRASS_LO, GRASS_MID, GRASS_HI = lin("#3C7A3A"), lin("#69A94A"), lin("#A6CE5E")
DRY_LO, DRY_MID, DRY_HI = lin("#6A8B38"), lin("#9AAE45"), lin("#CDB653")
JUNGLE_LO, JUNGLE_MID, JUNGLE_HI = lin("#2D6B47"), lin("#47955A"), lin("#7DC06E")
JUNGLE_OLD_LO, JUNGLE_OLD_MID, JUNGLE_OLD_HI = lin("#285E45"), lin("#3C8454"), lin("#68AE66")
FERN_LO, FERN_MID, FERN_HI = lin("#3A7A3E"), lin("#62A64A"), lin("#94CC62")
STALK_LO, STALK_HI = lin("#3F8441"), lin("#6CAE4C")
LEAF_LO, LEAF_MID, LEAF_HI = lin("#33783F"), lin("#55A046"), lin("#86C65A")
WHITE, WHITE_SHADE = lin("#FFF8E6"), lin("#E9E2C8")
DAISY_EYE_LO, DAISY_EYE_HI = lin("#E8A92A"), lin("#F8D14A")
YEL, YEL_SHADE = lin("#F8CC3A"), lin("#E5A92A")
YEL_EYE_LO, YEL_EYE_HI = lin("#D98126"), lin("#F2A83A")
RED, RED_SHADE = lin("#E0503F"), lin("#B93A31")
RED_EYE_LO, RED_EYE_HI = lin("#4A2A27"), lin("#7A3C2F")

# ---------------------------------------------------------------- shape helpers
def bez(B, C, E, t): return (1 - t) ** 2 * B + 2 * (1 - t) * t * C + t * t * E

def blade(M, base, yaw, lean, reach, height, width, wp, colfn, thick=.2, bow=.6, flank=.28, seed=0, tipdrop=0.0):
    """One bent blade / leaf as a closed prism. base: root point; yaw: heading in the XY plane (radians); lean: start angle from
    vertical (radians); reach / height: tip offset (horizontal / up); width: widest width; wp: width factor per row (last 0 = pointed tip,
    one row per entry); thick: midrib raise as a fraction of the local width; bow: how far the control point is pushed along the start
    direction (higher = rounder arch); flank: how far the two flanks sit below the rib (fraction of the rib raise)."""
    B = Vector(base)
    out = Vector((math.cos(yaw), math.sin(yaw), 0)); side = Vector((-math.sin(yaw), math.cos(yaw), 0))
    E = B + out * reach + Vector((0, 0, height - tipdrop))
    d0 = out * math.sin(lean) + Vector((0, 0, math.cos(lean)))
    C = B + d0 * (E - B).length * bow
    n = len(wp)
    spine = [bez(B, C, E, k / (n - 1)) for k in range(n)]
    verts = []; rows = []; refs = []
    for k, P in enumerate(spine):
        Tn = (spine[min(k + 1, n - 1)] - spine[max(k - 1, 0)]).normalized()
        N = Tn.cross(side).normalized()
        w = width * wp[k]
        if k == n - 1 and wp[k] <= 0:
            tip = P + Tn * .04; verts.append(tip); rows.append(('tip', len(verts) - 1)); continue
        rib = P + N * (thick * w); L = P - side * (w / 2) - N * (thick * w * flank); R = P + side * (w / 2) - N * (thick * w * flank)
        for q in (rib, L, R): q.z = max(q.z, 0.0)
        i0 = len(verts); verts += [rib, L, R]; rows.append(('row', i0))
        refs.append((rib + L + R) / 3)
    faces = []
    for k in range(n - 1):
        a, b = rows[k], rows[k + 1]
        ra, la, rra = a[1], a[1] + 1, a[1] + 2
        if b[0] == 'tip':
            t = b[1]; faces += [(ra, la, t), (ra, t, rra), (la, rra, t)]
        else:
            rb, lb, rrb = b[1], b[1] + 1, b[1] + 2
            faces += [(ra, la, lb, rb), (ra, rb, rrb, rra), (la, rra, rrb, lb)]
    M.add(verts, faces, refs, colfn, jit=.025, seed=seed)

def leafcol(lo, mid, hi, zlo, zhi, nzw=.5, tint=1.0):
    f = shade3(lo, mid, hi, zlo, zhi, nzw)
    return lambda p, n: f(p, n) * tint

def flat_add(M, verts, faces, colfn, both=True, jit=.02, seed=0):
    """flat petal-like faces added as given plus (both=True) a reversed copy so they show from both sides. The copy gets its OWN
    vertices: faces that share all vertices with another face are dropped as duplicates by the FBX exporter / importer (found in the
    reimport check), which would silently turn the petals single-sided. No auto flipping."""
    base = len(M.v)
    n_v = len(verts)
    for fc in faces:
        pts = [verts[i] for i in fc]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if n.length < 1e-9: continue
        n.normalize()
        cen = sum(pts, Vector()) / len(pts)
        j = noise.noise(cen * 1.7 + Vector((seed, seed * .7, 0))) * jit
        M.f.append(tuple(base + i for i in fc)); M.c.append([colfn(verts[i], n) + Vector((j, j, j)) for i in fc])
        if both:
            M.f.append(tuple(base + n_v + i for i in reversed(fc))); M.c.append([colfn(verts[i], -n) + Vector((j, j, j)) for i in reversed(fc)])
    M.v.extend(verts)
    if both: M.v.extend([Vector(v) for v in verts])

def head(M, centre, normal, R, petals, cup, petal_col, shade_col, eye_lo, eye_hi, seed, hw=.9, spin=0.0):
    """flower head: `petals` broad five-point petals around a low faceted centre dome, cupped up by `cup` radians, facing `normal`"""
    c = Vector(centre); nz = Vector(normal).normalized()
    ax = nz.cross(Vector((0, 0, 1)))
    if ax.length < 1e-4: ax = Vector((1, 0, 0))
    ax.normalize(); ay = nz.cross(ax)
    rnd = random.Random(seed)
    def to_world(r, th, z): return c + ax * (math.cos(th) * r) + ay * (math.sin(th) * r) + nz * z
    verts = []; faces = []
    for i in range(petals):
        th = spin + 2 * math.pi * i / petals + rnd.uniform(-.06, .06)
        half = math.pi / petals * hw
        rl = R * rnd.uniform(.9, 1.06)
        base = len(verts)
        z = lambda r: r * math.sin(cup)
        pts = [(.1 * R, th, 0), (.5 * R, th - half, z(.5 * R) * .6), (.88 * rl, th - half * .72, z(rl * .88)), (rl, th, z(rl)),
               (.88 * rl, th + half * .72, z(rl * .88)), (.5 * R, th + half, z(.5 * R) * .6)]
        verts += [to_world(r, t, zz) for r, t, zz in pts]
        faces += [(base, base + 1, base + 2), (base, base + 2, base + 3), (base, base + 3, base + 4), (base, base + 4, base + 5)]
    def pc(p, n):
        k = max(0.0, min(1.0, (p - c).length / R))
        return mix(shade_col, petal_col, .35 + .65 * (n.dot(nz) * .5 + .5) * (.6 + .4 * k))
    flat_add(M, verts, faces, pc, both=True, jit=.015, seed=seed)
    # centre: five-sided faceted dome, slightly proud of the petals
    ring = []; apex = to_world(0, 0, R * .26)
    for i in range(5):
        th = spin + 2 * math.pi * (i + .5) / 5
        ring.append(to_world(R * .26, th, R * .09))
    ev = [apex] + ring; ef = [(0, 1 + i, 1 + (i + 1) % 5) for i in range(5)]
    M.add(ev, ef, [to_world(0, 0, -R * .1)], lambda p, n: mix(eye_lo, eye_hi, (n.dot(nz) * .5 + .5)), jit=.02, seed=seed)

def stalk(M, pts, r0, r1, seed):
    v, f, ref = tube([Vector(p) for p in pts], (r0, r1), 3, tip=False, seed=seed, wob=.05)
    zl, zh = min(p[2] for p in pts), max(p[2] for p in pts)
    M.add(v, f, ref, lambda p, n: mix(STALK_LO, STALK_HI, (p.z - zl) / max(zh - zl, 1e-6) * .8 + n.z * .2), jit=.02, seed=seed)

def basal_leaves(M, centre, specs, seed):
    """small broad leaves lying around the foot of a flower: (yaw deg, lean deg, reach, height, width)"""
    c = Vector(centre)
    for i, (yaw, lean, reach, h, w) in enumerate(specs):
        blade(M, c + Vector((math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0)) * .12, math.radians(yaw), math.radians(lean), reach, h, w,
              [.45, 1.0, 0], leafcol(LEAF_LO, LEAF_MID, LEAF_HI, 0, h + .1, .5, 1.0 - .04 * (i % 3)), thick=.18, bow=.55, seed=seed + i)

# =============================================================== GRASS TUFTS (3 shapes)
def tuft(M, specs, lo, mid, hi, zhi, seed, rows, wp=None, thick=.2):
    """specs: (yaw deg, lean deg, reach, height, width, tint); every tuft is one hand-placed fan of broad blades"""
    wp = wp or ([.42, 1.0, .88, 0] if rows == 4 else [.5, 1.0, 0])
    for i, (yaw, lean, reach, h, w, tint) in enumerate(specs):
        r = math.radians(yaw)
        base = (math.cos(r) * .12, math.sin(r) * .12, 0)
        blade(M, base, r, math.radians(lean), reach, h, w, wp, leafcol(lo, mid, hi, 0, zhi, .5, tint), thick=thick, bow=.55, seed=seed + i)

def build_tuft_broad():
    """grass_broad: upright fan of eight broad blades, one tall in the middle, arching out unevenly"""
    M = Mesh()
    S = [(8, 14, .55, 2.2, .85, 1.0), (62, 24, .95, 1.8, .78, .95), (118, 20, .8, 2.0, .82, 1.04), (172, 30, 1.15, 1.6, .74, .96),
         (214, 18, .7, 1.85, .8, 1.02), (262, 32, 1.2, 1.45, .74, .94), (308, 22, .85, 1.7, .8, 1.0), (346, 12, .45, 1.35, .68, 1.05)]
    tuft(M, S, GRASS_LO, GRASS_MID, GRASS_HI, 2.15, 100, 4)
    return M

def build_tuft_arch():
    """grass_arch: five long blades sweeping one way like a windswept tuft, with two short ones at the root"""
    M = Mesh()
    S = [(20, 20, 1.55, 1.9, .78, 1.0), (45, 30, 1.9, 1.5, .7, .96), (-10, 14, 1.2, 2.05, .82, 1.04), (80, 36, 1.15, 1.15, .66, .98),
         (-40, 24, 1.1, 1.55, .72, 1.02), (150, 38, .7, .9, .6, .94), (205, 34, .75, .8, .6, 1.0)]
    tuft(M, S, GRASS_LO, GRASS_MID, GRASS_HI, 2.0, 120, 4)
    return M

def build_tuft_low():
    """grass_low: short wide spreading clump of ten blades with golden tips, for meadow edges and tree bases"""
    M = Mesh()
    S = []
    R = random.Random(5)
    for i in range(10):
        yaw = i * 36 + R.uniform(-14, 14)
        S.append((yaw, R.uniform(38, 62), R.uniform(.7, 1.3), R.uniform(.75, 1.2), R.uniform(.72, .95), R.uniform(.94, 1.05)))
    tuft(M, S, DRY_LO, DRY_MID, DRY_HI, 1.2, 140, 3, thick=.26)
    return M

# =============================================================== JUNGLE PLANT
def build_jungle():
    """jungle_leaf: rosette of eight big broad pointed leaves in two heights (handbook 'improved' panel): tall centre pair, wide
    arching outer ring, two short young leaves. Lanceolate profile, arching, folded along the midrib."""
    M = Mesh()
    wp = [.3, .85, 1.0, .72, 0]
    L = [  # yaw, lean, reach, height, width, tint, old
        (30, 12, .7, 3.7, 1.15, 1.0, False), (205, 16, .9, 3.4, 1.1, 1.03, False),
        (85, 30, 1.9, 3.0, 1.25, .98, True), (150, 34, 2.1, 2.6, 1.2, 1.02, True), (265, 32, 2.0, 2.8, 1.2, .96, True), (335, 36, 2.2, 2.3, 1.15, 1.0, True),
        (120, 55, 1.6, 1.4, .95, 1.05, False), (300, 52, 1.5, 1.25, .9, 1.06, False),
    ]
    for i, (yaw, lean, reach, h, w, tint, old) in enumerate(L):
        r = math.radians(yaw)
        lo, mid, hi = (JUNGLE_OLD_LO, JUNGLE_OLD_MID, JUNGLE_OLD_HI) if old else (JUNGLE_LO, JUNGLE_MID, JUNGLE_HI)
        blade(M, (math.cos(r) * .15, math.sin(r) * .15, 0), r, math.radians(lean), reach, h, w, wp, leafcol(lo, mid, hi, 0, 3.8, .55, tint),
              thick=.22, bow=.62, seed=200 + i, tipdrop=.25 if h > 2.2 else .0)
    return M

# =============================================================== FLOWER CLUSTERS
def flower_cluster(M, heads, leaves, seed, petal_col, shade_col, eye_lo, eye_hi, petals, R_scale=1.3, cup=.45, hw=.9):
    """heads: (x, y, height, lean x, lean y, radius, tilt-out) hand placed; each head sits on a bent three-sided stalk"""
    for i, (x, y, h, lx, ly, R, tilt) in enumerate(heads):
        base = Vector((x, y, 0))
        top = Vector((x + lx, y + ly, h))
        mid = Vector((x + lx * .3, y + ly * .3, h * .55))
        stalk(M, [base + Vector((0, 0, -.0)), mid, top], .08, .06, seed + i)
        normal = Vector((lx * .5 + tilt[0], ly * .5 + tilt[1] * 1.6, 1.0))
        head(M, top + Vector((0, 0, .02)), normal, R * R_scale, petals, cup, petal_col, shade_col, eye_lo, eye_hi, seed + 10 * i, hw=hw, spin=i * .5)
    basal_leaves(M, (0, 0, 0), leaves, seed + 50)

def build_flowers_daisy():
    """flowers_daisy: three white daisies (seven narrow petals, yellow eye) of different height, a spare low one, basal leaves"""
    M = Mesh()
    flower_cluster(M, [(-.5, .1, 1.55, .1, .05, .62, (0, -.3)), (.45, .25, 1.15, -.05, -.05, .55, (.15, -.35)), (.05, -.55, 1.75, .1, -.1, .66, (-.1, -.3))],
                   [(10, 55, 1.0, .5, .42), (130, 52, 1.1, .45, .4), (245, 58, .95, .5, .4), (320, 50, 1.05, .42, .38)], 300,
                   WHITE, WHITE_SHADE, DAISY_EYE_LO, DAISY_EYE_HI, 7, hw=.78, cup=.3)
    return M

def build_flowers_yellow():
    """flowers_yellow: three buttercup-like golden flowers with five broad round petals and an orange eye"""
    M = Mesh()
    flower_cluster(M, [(-.4, -.1, 1.3, .05, .1, .6, (0, -.3)), (.5, .15, 1.65, -.1, 0, .64, (.1, -.3)), (.0, .55, .95, .05, -.1, .55, (0, -.4))],
                   [(35, 52, 1.05, .45, .44), (155, 56, .9, .4, .4), (270, 50, 1.1, .5, .42)], 400,
                   YEL, YEL_SHADE, YEL_EYE_LO, YEL_EYE_HI, 5, hw=1.0, cup=.5)
    return M

def build_flowers_red():
    """flowers_red: warm accent, three red cupped flowers with a dark eye, one bud-like closed one lower down"""
    M = Mesh()
    flower_cluster(M, [(-.45, .0, 1.45, -.05, .1, .6, (-.1, -.35)), (.5, .1, 1.1, .1, 0, .56, (.2, -.3)), (.05, -.5, 1.75, 0, -.05, .62, (0, -.35))],
                   [(60, 54, 1.0, .5, .44), (190, 52, 1.1, .45, .42), (300, 56, .95, .5, .4)], 500,
                   RED, RED_SHADE, RED_EYE_LO, RED_EYE_HI, 5, hw=.95, cup=.5)
    return M

# =============================================================== FERN
def build_fern():
    """fern_arch: seven arching fronds with a serrated outline (wide, narrow, wide, ...) that fall over towards the tips, vase shape"""
    M = Mesh()
    wp = [.25, .95, .55, .9, .45, 0]
    F = [(10, 38, 1.9, 2.2, .85, 1.0), (62, 50, 2.5, 1.7, .8, .96), (118, 42, 2.2, 2.0, .85, 1.04), (176, 54, 2.7, 1.5, .78, .98),
         (232, 40, 2.1, 2.1, .84, 1.02), (290, 52, 2.6, 1.6, .8, .95), (338, 28, 1.3, 2.35, .72, 1.05)]
    for i, (yaw, lean, reach, h, w, tint) in enumerate(F):
        r = math.radians(yaw)
        blade(M, (math.cos(r) * .12, math.sin(r) * .12, 0), r, math.radians(lean), reach, h, w, wp, leafcol(FERN_LO, FERN_MID, FERN_HI, 0, 2.4, .5, tint),
              thick=.2, bow=.75, seed=600 + i, tipdrop=.9 if reach > 2 else .3)
    return M

PLANTS = {
    'grass_broad': ('plant_grass_broad_v3', build_tuft_broad),
    'grass_arch': ('plant_grass_arch_v3', build_tuft_arch),
    'grass_low': ('plant_grass_low_v3', build_tuft_low),
    'jungle': ('plant_jungle_leaf_v3', build_jungle),
    'flowers_daisy': ('plant_flowers_daisy_v3', build_flowers_daisy),
    'flowers_yellow': ('plant_flowers_yellow_v3', build_flowers_yellow),
    'flowers_red': ('plant_flowers_red_v3', build_flowers_red),
    'fern': ('plant_fern_arch_v3', build_fern),
}

def make_plant(key):
    name, fn = PLANTS[key]
    ob = fn().to_object(name, flat=True)
    ob.data.materials.append(vc_material())
    centre_xy(ob)
    return ob

# =============================================================== CURRENT (version 1): the real kit meshes
KIT = {'cur_grass_a': 'world_grass_a.fbx', 'cur_grass_b': 'world_grass_b.fbx', 'cur_flowers': 'world_flowers_a.fbx',
       'cur_fern_a': 'world_fern_a.fbx', 'cur_fern_b': 'world_fern_b.fbx'}
def import_kit(fname):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX_V1, fname))
    ob = [o for o in bpy.data.objects if o not in before and o.type == 'MESH'][0]
    for o in list(bpy.data.objects):
        if o not in before and o.type != 'MESH': bpy.data.objects.remove(o)
    ob.data.materials.clear(); ob.data.materials.append(vc_material()); ob.rotation_euler = (0, 0, 0); ob.parent = None
    return ob

# =============================================================== stages
def stage_export():
    os.makedirs(FBX_V3, exist_ok=True)
    reset()
    obs = []; x = 0
    for key in PLANTS:
        ob = make_plant(key); ob.location = (x, 0, 0); x += 8; obs.append(ob)
        d = ob.dimensions
        zs = [v.co.z for v in ob.data.vertices]
        print("REPORT", ob.name, "tris", tri_count(ob), "verts", len(ob.data.vertices), "size", [round(d.x, 2), round(d.y, 2), round(d.z, 2)],
              "minz", round(min(zs), 3), "materials", len(ob.data.materials))
    for ob in obs:
        for o in bpy.context.selected_objects: o.select_set(False)
        loc = ob.location.copy(); ob.location = (0, 0, 0); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(FBX_V3, ob.name + ".fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, axis_forward="-Z", axis_up="Y", colors_type="SRGB", mesh_smooth_type="FACE",
                                 add_leaf_bones=False, bake_anim=False)
        ob.location = loc; ob.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "assets", "blender", "world", "WorldKitV3_Plants.blend"))

CAM_AZIM = 28.0
def screen_to_world(sx, sd):
    a = math.radians(CAM_AZIM)
    return (sx * math.cos(a) + sd * math.sin(a), sx * math.sin(a) - sd * math.cos(a))

DINO_SCREEN = (-10.2, 5.3)
def layout():
    """hand-seeded meadow patch in SCREEN coordinates (x right, depth towards the camera): the same slots for both versions.
    kinds: grass, flower, fern, big (the new jungle plant; the current game has nothing like it, so version 1 shows its biggest fern)."""
    R = random.Random(463)
    want = [('big', 2), ('fern', 5), ('flower', 9), ('grass', 34)]
    placed = []
    # two big ones fixed near the front and back of the patch so they read in every shot
    fixed = [('big', 7.5, 3.5), ('big', -3.0, -6.5)]
    for k, x, d in fixed: placed.append((k, x, d, R.uniform(0, 6.28), 1.0))
    for kind, n in want:
        if kind == 'big': continue
        tries = 0; cnt = 0
        while cnt < n and tries < 4000:
            tries += 1
            x = R.uniform(-24, 24); d = R.uniform(-18, 13)
            if math.hypot(x - DINO_SCREEN[0], d - DINO_SCREEN[1]) < 5.2: continue
            mind = {'fern': 5.0, 'flower': 3.6, 'grass': 2.5}[kind]
            if any(math.hypot(x - p[1], d - p[2]) < mind for p in placed): continue
            placed.append((kind, x, d, R.uniform(0, 6.28), R.uniform(.85, 1.2))); cnt += 1
    return placed

def build_patch(version):
    cache = {}; counter = {}; tris = 0; n = 0
    def get(key):
        if key not in cache:
            cache[key] = import_kit(KIT[key]) if key.startswith('cur_') else make_plant(key)
            first = True
        else: first = False
        return cache[key], first
    for kind, sx, sd, yaw, s in layout():
        i = counter.get(kind, 0); counter[kind] = i + 1
        if version == 'v1':
            key = {'grass': ['cur_grass_a', 'cur_grass_b'][i % 2], 'flower': 'cur_flowers', 'fern': ['cur_fern_a', 'cur_fern_b'][i % 2], 'big': 'cur_fern_b'}[kind]
        else:
            key = {'grass': ['grass_broad', 'grass_arch', 'grass_low'][i % 3], 'flower': ['flowers_daisy', 'flowers_yellow', 'flowers_red'][i % 3],
                   'fern': 'fern', 'big': 'jungle'}[kind]
        base, first = get(key)
        if first: o = base
        else:
            o = base.copy(); bpy.context.scene.collection.objects.link(o)
        wx, wy = screen_to_world(sx, sd)
        o.location = (wx, wy, 0); o.rotation_euler = (0, 0, yaw + math.radians(CAM_AZIM)); o.scale = (s, s, s)
        tris += tri_count(base); n += 1
    return tris, n

SHOTS = {'play25-spawn': (25, 1.0), 'play25-big': (25, 1.5), 'play40-spawn': (40, 1.0), 'play40-big': (40, 1.5)}
def stage_render(out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    res = (1600, 900)
    counts = {}
    for version in ('v1', 'v2'):
        for shot, (dist, ds) in SHOTS.items():
            if only and shot not in only: continue
            sc = reset(); world_setup(sc, res); sc.cycles.samples = 48
            tris, n = build_patch(version)
            dino_stand_in((-6.5, -9.5, 0), math.radians(35), ds)
            counts[version] = (tris, n)
            camera(sc, (0.5, -1.0, 2.6), dist, 17, CAM_AZIM, res=res)
            render(sc, os.path.join(out_dir, f"_{version}_{shot}.png"))
            print("RENDERED", version, shot, tris, n)
    if counts:
        open(os.path.join(out_dir, "tris.txt"), "w").write("".join(f"{k} {v[0]} {v[1]}" + chr(10) for k, v in counts.items()))
    if not only or 'lineup' in only:
        widths = {'grass_broad': 2.8, 'grass_arch': 3.2, 'grass_low': 2.9, 'jungle': 5.2, 'flowers_daisy': 3.2, 'flowers_yellow': 3.2, 'flowers_red': 3.2, 'fern': 5.5,
                  'cur_grass_a': .7, 'cur_grass_b': .7, 'cur_flowers': .7, 'cur_fern_a': 3.3, 'cur_fern_b': 3.5}
        rows = {'v2': [['grass_broad', 'grass_arch', 'grass_low', 'jungle'], ['flowers_daisy', 'flowers_yellow', 'flowers_red', 'fern']],
                'v1': [['cur_grass_a', 'cur_grass_b', 'cur_flowers', 'cur_fern_a', 'cur_fern_b']]}
        for version in ('v1', 'v2'):
            sc = reset(); world_setup(sc, res); sc.cycles.samples = 48
            for ri, row in enumerate(rows[version]):
                total = sum(widths[k] + 1.8 for k in row); x = -total / 2
                for k in row:
                    ob = import_kit(KIT[k]) if k.startswith('cur_') else make_plant(k)
                    w = widths[k]; ob.location = (x + w / 2, -ri * 7.0 + (3.5 if len(rows[version]) > 1 else 0), 0); x += w + 1.8
            # a spawn-size dino silhouette beside the lineup for scale (4.4 studs tall)
            dino_stand_in((-12.5 if version == 'v1' else -13.5, -1.5, 0), math.radians(90), 1.0)
            camera(sc, (0, 0, 1.2), 19, 20, 0, fov=45, res=res)
            render(sc, os.path.join(out_dir, f"_{version}_lineup.png"))
            print("RENDERED", version, "lineup")

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[0] if argv else "export"
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs", "evidence", "2026-10-17-plants")
    only = argv[2].split(",") if len(argv) > 2 else None
    if stage == "export": stage_export()
    elif stage == "render": stage_render(out, only)
