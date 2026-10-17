"""BD-047: Crystal Shop art as real Blender renders (tab icons, the green-spotted egg and the five category tiles).

Run headless (no Studio, no MCP session):
    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python tools/blender/build_shop_tiles.py
Optional: `-- --samples 128` or `-- --only egg_green_spotted,tile_auras` (a comma list of the asset keys below). Outputs:
    resources/ui/v2/icons/shop-tab-<auras|trails|conditions|crystals>-v1.png   128 x 128 RGBA, the leading icon of a shop tab
    resources/ui/v2/icons/egg-green-spotted-v1.png                             256 x 256 RGBA, the Eggs tab icon AND the Eggs product art
    resources/ui/v2/icons/shop-tile-<auras|trails|eggs|conditions|crystals>-v1.png   256 x 256 RGBA, the landing page tiles
    tools/blender/shop_tiles.blend                                             the scene, one collection per asset
Then run `python tools/make_shop_tile_sheet.py` for the contact sheet and `python tools/verify_shop_tiles.py`.

Same look as the mutation badges and trail icons (tools/blender/build_mutation_badges.py BD-190, build_trail_icons.py BD-178; docs/114
handbook palette, docs/72 children and readable at 64 px): chunky soft-bevel matte 3D symbols, one soft key light, a white rim plus a
thin navy outer line around the whole silhouette so each one reads on light AND dark panels. The egg is a real revolved 3D egg with
green spots modelled as small domes. The tiles are little scenes: a rounded backdrop slab with a glow disc and a ground mound, the
symbol standing on it, each element with its own white rim like a sticker. Colours come from docs/114 s5 (UI colours, rarity, egg
colours, aura colours, crystals = amber). No text is baked into any image (docs/72). The 2D outlines are point lists; Blender is the
modelling and render tool and nothing is drawn per pixel. The helpers (colour, outline, plate and light helpers) are those of
build_trail_icons.py, kept in step on purpose; that script is not imported because it renders on import.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'resources/ui/v2/icons'
BLEND = ROOT / 'tools/blender/shop_tiles.blend'

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SAMPLES = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 128
ONLY = set(argv[argv.index('--only') + 1].split(',')) if '--only' in argv else None

RIM = (246, 250, 255)   # light rim: white with a hint of blue
LINE = (44, 50, 98)     # thin outer line: navy (the handbook outline family)
RIM_W = 0.075
LINE_W = 0.05
DEPTH = 0.34

# docs/114 s5 palette ------------------------------------------------------------------------------------------------------
GOLD = (255, 210, 43)       # gold / amber #FFD22B (crystals = amber everywhere, s5.3)
AMBER = (241, 160, 36)      # Amber egg colour #F1A024
GREEN = (93, 237, 31)       # accent green #5DED1F
BLUE = (46, 206, 255)       # blue #2ECEFF
PURPLE = (194, 86, 255)     # purple #C256FF
RED = (247, 57, 48)         # red #F73930
MEADOW = (98, 236, 112)     # aura Meadow #62EC70
TIDAL = (80, 214, 255)      # aura Tidal #50D6FF
ROYAL = (180, 106, 255)     # aura Royal #B46AFF
CREAM = (247, 234, 196)     # Cream egg #F7EAC4
EGG_GREEN = (29, 175, 75)   # Green egg #1DAF4B
PANEL = (42, 40, 53)        # panel #2A2835


# ---------------------------------------------------------------- colours
def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(rgb255, a=1.0):
    return (lin(rgb255[0]), lin(rgb255[1]), lin(rgb255[2]), a)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def lighter(c, t):
    return mix(c, (255, 255, 255), t)


def darker(c, t):
    return mix(c, (40, 24, 60), t)


# ---------------------------------------------------------------- 2D outline helpers
def area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))


def ccw(pts):
    return pts if area(pts) > 0 else pts[::-1]


def chaikin(pts, n):
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        pts = out
    return pts


def transform(pts, scale=1.0, dx=0.0, dy=0.0, rot=0.0, about=(0.0, 0.0)):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for x, y in pts:
        x, y = (x - about[0]) * scale, (y - about[1]) * scale
        out.append((x * c - y * s + about[0] + dx, x * s + y * c + about[1] + dy))
    return out


def circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def ellipse(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def capsule(x0, y0, x1, y1, half, seg=10):
    """Rounded bar from (x0,y0) to (x1,y1)."""
    ang = math.atan2(y1 - y0, x1 - x0)
    pts = []
    for i in range(seg + 1):
        a = ang - math.pi / 2 + math.pi * i / seg
        pts.append((x1 + half * math.cos(a), y1 + half * math.sin(a)))
    for i in range(seg + 1):
        a = ang + math.pi / 2 + math.pi * i / seg
        pts.append((x0 + half * math.cos(a), y0 + half * math.sin(a)))
    return pts


def rrect(hw, hh, r, n=10):
    """Rounded rectangle centred on the origin (counter-clockwise)."""
    pts = []
    for cx, cy, a0 in ((hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180), (hw - r, -hh + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def sparkle_points(cx, cy, R, r, pts=4, rot=0.0):
    out = []
    for i in range(pts * 2):
        a = math.pi / 2 + rot + i * math.pi / pts
        rad = R if i % 2 == 0 else r
        out.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return out


def ribbon(center, w0, w1, n=40):
    """A tapering band along a polyline `center` (list of points): width w0 at the start, w1 at the end."""
    left, right = [], []
    m = len(center)
    for i, (x, y) in enumerate(center):
        a = center[max(0, i - 1)]
        b = center[min(m - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        w = (w0 + (w1 - w0) * i / (m - 1)) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return left + right[::-1]


def bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def egg_profile(R, H, n=40, cut=None):
    """Right-to-left outline of an egg (pointed end up): x = R sin t (1 - 0.2 cos t), y = H cos t."""
    pts = []
    for i in range(n + 1):
        t = math.pi * i / n
        pts.append((R * math.sin(t) * (1 - 0.2 * math.cos(t)), H * math.cos(t)))
    return pts


# ---------------------------------------------------------------- Blender helpers
def material(name, rgb255, rough=0.55, emit=0.10):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = rgba(rgb255)
    p.inputs['Roughness'].default_value = rough
    for key, val in (('Specular IOR Level', 0.3), ('Emission Color', rgba(rgb255)), ('Emission Strength', emit)):
        if key in p.inputs:
            p.inputs[key].default_value = val
    return mat


def flat_material(name, rgb255):
    """Unlit rim / line plate."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emi = nt.nodes.new('ShaderNodeEmission')
    emi.inputs['Color'].default_value = rgba(rgb255)
    emi.inputs['Strength'].default_value = 1.0
    nt.links.new(emi.outputs[0], out.inputs['Surface'])
    return mat


def link(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def prism(name, pts, z0, depth, mat, coll, bevel=0.0, segments=5, smooth=True):
    """Extruded 2D outline as a mesh; optional soft bevel."""
    pts = ccw(pts)
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    ring = [bm.verts.new((x, y, z0)) for x, y in pts]
    face = bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=[face])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    for v in [v for v in ext['geom'] if isinstance(v, bmesh.types.BMVert)]:
        v.co.z += depth
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.data.materials.append(mat)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    if bevel > 0:
        mod = obj.modifiers.new('Bevel', 'BEVEL')
        mod.width, mod.segments, mod.profile = bevel, segments, 0.62
        mod.limit_method, mod.angle_limit = 'ANGLE', math.radians(35)
        mod.harden_normals = False
    return obj


def plate_mesh(name, polys, d, z, mat, coll):
    """Flat plate = the silhouette plus a capsule along every edge (a Minkowski grow by d), one unlit material."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    def add(pts):
        pts = ccw(pts)
        try:
            bm.faces.new([bm.verts.new((x, y, z)) for x, y in pts])
        except ValueError:
            pass
    for pts in polys:
        add(pts)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6:
                add(capsule(a[0], a[1], b[0], b[1], d, seg=8))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.data.materials.append(mat)
    obj.visible_shadow = False
    obj.visible_glossy = False
    return obj


def plate_set(name, polys, z, coll, k=1.0):
    """White rim + thin navy outer line behind the symbol (k scales the widths for a symbol that was shrunk)."""
    plate_mesh(f'{name}_line', polys, (RIM_W + LINE_W) * k, z - 0.02, flat_material('line', LINE), coll)
    plate_mesh(f'{name}_rim', polys, RIM_W * k, z - 0.01, flat_material('rim', RIM), coll)


def torus(name, cx, cy, R, r, mat, coll, z=None, tilt=0.0, squash=0.75, sx=1.0):
    """A chunky ring lying in the picture plane (half sunk so the back is flat); tilt (radians about X) shows it as an ellipse."""
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=64, minor_segments=24,
                                     location=(cx, cy, r * 0.75 if z is None else z))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale.z = squash
    obj.scale.x = sx
    obj.rotation_euler.x = tilt
    link(obj, coll)
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return obj


def sphere(name, loc, scale, mat, coll, rot=None, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if rot is not None:
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = rot
    link(obj, coll)
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return obj


def egg_mesh(name, R, H, mat, coll, loc):
    """A revolved 3D egg (pointed end up, axis = Y). Returns the object."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=56, v_segments=36, radius=1.0)
    for v in bm.verts:
        ux, uy, uz = v.co.x, v.co.y, v.co.z   # the sphere pole axis is Z
        k = 1 - 0.2 * uz
        v.co = Vector((R * k * ux, H * uz, R * k * uy))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    coll.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def egg_spots(parent_name, R, H, spots, mat, coll, loc, rot=0.0):
    """Little green domes on the front of the egg. spots = [(phi_deg: 0 faces the camera, +/- turns it sideways; t_deg: angle from the tip; radius)]."""
    objs = []
    for i, (phi, tdeg, rad) in enumerate(spots):
        t, p = math.radians(tdeg), math.radians(phi)
        k = 1 - 0.2 * math.cos(t)
        # p = 0 faces the camera (+Z); the sign of p turns the dome to the right or left; t is the angle from the tip (top)
        pos = Vector((R * k * math.sin(t) * math.sin(p), H * math.cos(t), R * k * math.sin(t) * math.cos(p)))
        nrm = Vector((pos.x / (R * k) ** 2, pos.y / H ** 2, pos.z / (R * k) ** 2)).normalized()
        quat = nrm.to_track_quat('Z', 'Y')
        d = sphere(f'{parent_name}_spot{i}', pos - nrm * rad * 0.10, (rad, rad, rad * 0.32), mat, coll, rot=quat, seg=20)
        objs.append(d)
    return objs


# ---------------------------------------------------------------- group helper: shrink / move one element of a scene
def group(coll, before, loc=(0.0, 0.0), scale=1.0, rot=0.0, pivot=(0.0, 0.0)):
    """Parent every object added to `coll` since `before` (a set of names) to an empty at `pivot`, then move / scale / rotate it."""
    new = [o for o in coll.objects if o.name not in before and o.parent is None]
    em = bpy.data.objects.new('grp', None)
    em.location = (pivot[0], pivot[1], 0.0)
    coll.objects.link(em)
    bpy.context.view_layer.update()
    inv = em.matrix_world.inverted()
    for o in new:
        o.parent = em
        o.matrix_parent_inverse = inv
    em.location = (loc[0], loc[1], 0.0)
    em.scale = (scale, scale, scale)
    em.rotation_euler.z = rot
    return em


def names(coll):
    return {o.name for o in coll.objects}


# ---------------------------------------------------------------- elements (each returns the 2D silhouette polygons at scale 1)
def el_aura_ring(coll, c=MEADOW):
    """Aura: a glowing halo ring (the shop's aura preview is a ring round a fossil) with a little spiral fossil inside and two
    sparkles. The ring is open in the middle, so its silhouette is a band, unlike the filled egg and rainbow shapes."""
    sx = 1.0
    torus('aura_ring', 0, 0, 0.8, 0.19, material('aura_ring', c), coll, sx=sx)
    torus('aura_ring_hi', 0, 0, 0.8, 0.07, material('aura_ring_hi', lighter(c, 0.6), rough=0.4, emit=0.35), coll, z=0.19 * 0.75 + 0.09, squash=0.6, sx=sx)
    shell = (226, 190, 120)
    prism('fossil_body', chaikin(circle(0, 0, 0.4, 40), 1), 0, 0.22, material('fossil_body', shell, rough=0.6, emit=0.05), coll, bevel=0.1)
    turns = 1.8
    pts = [(0.065 * math.cos(2 * math.pi * turns * t) * (1 + 5.2 * t), 0.065 * math.sin(2 * math.pi * turns * t) * (1 + 5.2 * t)) for t in [i / 60 for i in range(61)]]
    prism('fossil_spiral', chaikin(ribbon(pts, 0.09, 0.09), 1), 0.2, 0.07, material('fossil_spiral', darker(shell, 0.45), rough=0.6, emit=0.0), coll, bevel=0.025, segments=3)
    # the ring's silhouette is the band only (capsules along its centre line), so the hole stays open
    n = 36
    cl = [(0.8 * sx * math.cos(2 * math.pi * i / n), 0.8 * math.sin(2 * math.pi * i / n)) for i in range(n)]
    sil = [capsule(cl[i][0], cl[i][1], cl[(i + 1) % n][0], cl[(i + 1) % n][1], 0.16, 6) for i in range(n)] + [circle(0, 0, 0.4, 32)]
    for k, (cx, cy, R) in enumerate([(0.9, 0.62, 0.25), (-0.92, -0.58, 0.18)]):
        sp = chaikin(sparkle_points(cx, cy, R, R * 0.36), 2)
        prism(f'aura_sp{k}', sp, 0, DEPTH * 0.7, material('aura_sp', lighter(GOLD, 0.15), rough=0.5, emit=0.3), coll, bevel=0.04)
        sil.append(sp)
    return sil


def el_footprint(coll, c=PURPLE, acc=lighter(PURPLE, 0.55)):
    """A three-toe dino footprint: three separate toes with little claws fanning from a heel pad, pointing up."""
    sil = []
    toe_m = material('toe', c)
    claw_m = material('claw', acc, rough=0.5, emit=0.2)
    hc = (0.0, -0.22)   # the heel pad centre; the toes fan out from it
    for k, (ang, r0, r1, half) in enumerate(((-50, 0.40, 0.80, 0.2), (0, 0.46, 1.0, 0.23), (50, 0.40, 0.80, 0.2))):
        a = math.radians(ang)
        d = (math.sin(a), math.cos(a))
        s0 = (hc[0] + d[0] * r0, hc[1] + d[1] * r0)
        s1 = (hc[0] + d[0] * r1, hc[1] + d[1] * r1)
        toe = capsule(s0[0], s0[1], s1[0], s1[1], half)
        prism(f'toe{k}', toe, 0, DEPTH, toe_m, coll, bevel=0.1)
        tip = (s1[0] + d[0] * half, s1[1] + d[1] * half)
        n = (d[1], -d[0])
        claw = [(tip[0] - n[0] * 0.08, tip[1] - n[1] * 0.08), (tip[0] + d[0] * 0.2, tip[1] + d[1] * 0.2), (tip[0] + n[0] * 0.08, tip[1] + n[1] * 0.08)]
        prism(f'claw{k}', chaikin(claw, 2), 0, DEPTH * 0.8, claw_m, coll, bevel=0.03)
        sil += [toe, claw]
    heel = chaikin(ellipse(hc[0], hc[1], 0.42, 0.32, 36), 1)
    prism('heel', heel, 0, DEPTH, toe_m, coll, bevel=0.12)
    prism('heel_glint', chaikin(ellipse(-0.1, -0.14, 0.13, 0.08, 20), 1), DEPTH - 0.02, 0.06, material('heel_glint', acc, rough=0.45, emit=0.25), coll, bevel=0.02)
    sil.append(heel)
    return sil


def el_swoosh(coll, c=BLUE, acc=lighter(BLUE, 0.6), pts=None, w0=0.12, w1=0.46, depth=DEPTH * 0.7):
    """A soft tapering ribbon with a light core line (the trail)."""
    pts = pts or bezier((-1.0, -0.62), (-0.35, -1.0), (0.15, -0.25), (0.9, -0.2))
    band = chaikin(ribbon(pts, w0, w1), 1)
    prism('swoosh', band, 0, depth, material('swoosh', c), coll, bevel=min(0.1, depth * 0.45))
    core = chaikin(ribbon(pts, w0 * 0.3, w1 * 0.3), 1)
    prism('swoosh_core', core, depth - 0.03, 0.05, material('swoosh_core', acc, rough=0.45, emit=0.3), coll, bevel=0.015, segments=3)
    return [band]


def el_green_egg(coll, scale_tilt=math.radians(12)):
    """The green-spotted egg: a revolved cream egg with green domes. Returns the silhouette (the profile, tilted)."""
    R, H = 0.70, 0.93
    body = material('egg_body', CREAM, rough=0.42, emit=0.04)
    spot = material('egg_spot', EGG_GREEN, rough=0.42, emit=0.04)
    loc = (0.0, 0.0, R + 0.04)
    egg_mesh('egg', R, H, body, coll, loc)
    spots = [(8, 62, 0.19), (-62, 52, 0.12), (70, 96, 0.15), (-28, 112, 0.2), (18, 142, 0.14), (-72, 138, 0.1), (62, 38, 0.1), (-20, 78, 0.09), (54, 128, 0.09)]
    # dome centres are placed in object space; the objects are later rotated with the tilt by the caller via `group`
    for o in egg_spots('egg', R, H, spots, spot, coll, Vector(loc)):
        o.location += Vector(loc)
    prof = egg_profile(R, H, 48)
    return [prof + [(-x, y) for x, y in prof[::-1]][1:-1]]


def build_nest(coll):
    """A woven nest cup that stands in front of the egg's lower third: brown body, woven bands, a light lip and straw sticks."""
    straw = (176, 122, 63)
    bot = []
    for i in range(0, 41):
        a = math.pi + math.pi * i / 40          # from the left edge round the bottom to the right edge
        bot.append((1.0 * math.cos(a), 0.66 * math.sin(a)))
    top = [(1.0 - 2.0 * i / 16, 0.07 * math.cos(math.pi * (i / 16 - 0.5)) - 0.02) for i in range(17)]
    cup = bot + top[1:-1]
    prism('nest_cup', cup, 0.05, 1.3, material('nest_cup', straw, rough=0.8, emit=0.0), coll, bevel=0.14)
    weave = material('nest_weave', darker(straw, 0.4), rough=0.8, emit=0.0)
    for k, sc in enumerate((0.86, 0.62, 0.38)):
        line = [(x * sc, y * sc - 0.03) for x, y in bot[3:-3]]
        prism(f'nest_band{k}', ribbon(line, 0.06, 0.06), 1.3, 0.05, weave, coll, bevel=0.015, segments=2)
    lip = ribbon([(x, y + 0.02) for x, y in top[1:-1]], 0.2, 0.2)
    prism('nest_lip', chaikin(lip, 1), 1.3, 0.12, material('nest_lip', lighter(straw, 0.3), rough=0.8, emit=0.0), coll, bevel=0.05)
    sil = [cup]
    for k, (x0, y0, x1, y1) in enumerate([(-0.9, 0.0, -1.06, 0.34), (0.86, 0.0, 1.04, 0.3), (-0.55, 0.0, -0.66, 0.26)]):
        st = capsule(x0, y0, x1, y1, 0.05, 6)
        prism(f'nest_straw{k}', st, 0.4, 0.5, material('straw', lighter(straw, 0.45), rough=0.8, emit=0.0), coll, bevel=0.02, segments=3)
        sil.append(st)
    return sil


def el_crystal(coll, cx, by, w, h, tilt=0.0, name='cr', tones=None):
    """A faceted amber crystal (docs/114 s5.3: currency crystals are amber) built from four facet prisms; flat low-poly look."""
    tones = tones or [mix(GOLD, (160, 80, 10), 0.42), mix(GOLD, (200, 110, 10), 0.18), lighter(GOLD, 0.45), lighter(GOLD, 0.15)]
    bl, br = (cx - w / 2, by), (cx + w / 2, by)
    b = (cx, by - 0.04 * h)
    m = (cx, by + 0.70 * h)
    ls, rs = (cx - w / 2, by + 0.70 * h), (cx + w / 2, by + 0.70 * h)
    top = (cx - w * 0.04, by + h)
    facets = [[bl, b, m, ls], [b, br, rs, m], [ls, m, top], [m, rs, top]]
    pivot = (cx, by)
    out = []
    for k, f in enumerate(facets):
        pts = transform(f, rot=tilt, about=pivot)
        prism(f'{name}_f{k}', pts, 0, DEPTH * (0.78 + 0.07 * k), material(f'{name}{k}', tones[k], rough=0.38, emit=0.12), coll, bevel=0.035, segments=3, smooth=False)
    sil = transform([bl, br, rs, top, ls], rot=tilt, about=pivot)
    out.append(sil)
    return out


def el_crystals(coll):
    sil = []
    sil += el_crystal(coll, 0.0, -0.78, 0.62, 1.62, 0.0, 'cr_mid')
    sil += el_crystal(coll, -0.62, -0.78, 0.46, 1.0, math.radians(14), 'cr_left')
    sil += el_crystal(coll, 0.66, -0.78, 0.46, 0.88, math.radians(-16), 'cr_right')
    sp = chaikin(sparkle_points(0.62, 0.62, 0.26, 0.08), 2)
    prism('cr_spark', sp, 0, DEPTH * 0.7, material('cr_spark', lighter(GOLD, 0.35), rough=0.5, emit=0.35), coll, bevel=0.04)
    sil.append(sp)
    return sil


def el_rainbow_shell(coll):
    """Conditions: a cracked egg half-shell holding a rainbow arch, with a sparkle."""
    cx, cy = 0.0, -0.05
    bands = [(0.98, 0.78, RED), (0.78, 0.58, GOLD), (0.58, 0.38, GREEN), (0.38, 0.18, BLUE)]
    sil = []
    for k, (ro, ri, col) in enumerate(bands):
        a0, a1 = math.radians(-22), math.radians(202)
        n = 28
        outer = [(cx + ro * math.cos(a0 + (a1 - a0) * i / n), cy + ro * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        inner = [(cx + ri * math.cos(a0 + (a1 - a0) * i / n), cy + ri * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        pts = outer + inner[::-1]
        prism(f'rb{k}', pts, 0, DEPTH * 0.8, material(f'rb{k}', col, rough=0.5, emit=0.12), coll, bevel=0.05, segments=3)
        if k == 0:
            sil.append(pts)
    # the shell: the lower part of an egg with a zigzag crack along the top
    prof = egg_profile(0.78, 0.98, 48)
    ycut = -0.12
    right_side = [(x, y) for x, y in prof if y <= ycut]            # from the cut on the right down to the bottom
    left_side = [(-x, y) for x, y in right_side[::-1]]             # from the bottom up to the cut on the left
    xr, steps = right_side[0][0], 7
    zig_back = [(xr - 2 * xr * i / steps, ycut + (0.15 if i % 2 else -0.03)) for i in range(steps + 1)][::-1]  # left -> right
    shell = [(x, y - 0.22) for x, y in right_side + left_side + zig_back]
    prism('shell', shell, 0.06, DEPTH, material('shell', CREAM, rough=0.5, emit=0.05), coll, bevel=0.1)
    # a darker inner strip hugging the zigzag edge so the break reads
    prism('shell_edge', [(x, y - 0.22) for x, y in zig_back] + [(x, y - 0.42) for x, y in zig_back[::-1]], 0.06 + DEPTH - 0.04, 0.08,
          material('shell_edge', mix(CREAM, (200, 150, 90), 0.5), rough=0.5, emit=0.0), coll, bevel=0.02, segments=3)
    sil.append(shell)
    sp = chaikin(sparkle_points(0.78, 0.82, 0.24, 0.07), 2)
    prism('rb_spark', sp, 0, DEPTH * 0.7, material('rb_spark', lighter(GOLD, 0.3), rough=0.5, emit=0.35), coll, bevel=0.04)
    sil.append(sp)
    return sil


# ---------------------------------------------------------------- assets
# Each builder(coll) builds its meshes (no rim plate yet) and returns (silhouette polygons, z for the plates).
def tab_auras(coll):
    b = names(coll)
    sil = el_aura_ring(coll)
    group(coll, b, loc=(-0.02, 0.0), scale=0.9)   # the sparkles would touch the frame edge at full size
    return [transform(p, scale=0.9, dx=-0.02) for p in sil], 0.0


def tab_conditions(coll):
    b = names(coll)
    sil = el_rainbow_shell(coll)
    group(coll, b, loc=(0.0, 0.1), scale=0.9)   # the shell would touch the frame edge at full size
    return [transform(p, scale=0.9, dy=0.1) for p in sil], 0.0


def tab_crystals(coll):
    return el_crystals(coll), 0.0


def build_tab_trails(coll):
    """Trails: a footprint (purple) standing on a swoosh (blue)."""
    before = names(coll)
    s1 = el_swoosh(coll, BLUE, lighter(BLUE, 0.6), bezier((-1.0, -0.62), (-0.4, -1.25), (0.35, -0.2), (1.0, -0.82)), 0.08, 0.3)
    before2 = names(coll)
    s2 = el_footprint(coll, PURPLE)
    group(coll, before2, loc=(0.0, 0.22), scale=0.86, rot=math.radians(10))
    polys2 = [transform(p, scale=0.86, rot=math.radians(10), dx=0.0, dy=0.22) for p in s2]
    allp = s1 + polys2
    group(coll, set(), loc=(0.03, -0.1), scale=0.9)   # the top claw would touch the frame edge at full size
    return [transform(p, scale=0.9, dx=0.03, dy=-0.1) for p in allp], 0.0


def build_egg_icon(coll):
    sil = el_green_egg(coll)
    tilt = math.radians(10)
    group(coll, set(), loc=(0.0, 0.0), rot=tilt)   # everything in the collection tilts about the origin
    return [transform(p, rot=tilt) for p in sil], 0.0


# ---------------------------------------------------------------- tiles
def backdrop(coll, base, glow, name='tile'):
    """Rounded slab (the tile body) with a lighter glow disc, a darker ground mound and its own rim + line."""
    hw = 1.12
    slab = rrect(hw, hw, 0.42, 12)
    z0 = -0.50
    prism(f'{name}_slab', slab, z0, 0.36, material(f'{name}_slab', base, rough=0.7, emit=0.05), coll, bevel=0.06)
    prism(f'{name}_glow', ellipse(0, 0.12, 0.84, 0.82, 56), z0 + 0.34, 0.03, material(f'{name}_glow', glow, rough=0.9, emit=0.12), coll, bevel=0.015, segments=2)
    return z0, [slab]


def mound(coll, y, rx, ry, col, name='mound'):
    # sits on the glow disc (top at z = -0.50 + 0.37)
    prism(name, ellipse(0, y, rx, ry, 48), -0.12, 0.09, material(name, col, rough=0.9, emit=0.0), coll, bevel=0.035, segments=3)


def finish_tile(coll, z0, slab_polys, parts):
    """The slab gets the white rim + navy line; every standing element gets its own sticker rim above the backdrop."""
    plate_set('tile', slab_polys, z0, coll, k=1.15)
    for i, (polys, k) in enumerate(parts):
        plate_set(f'el{i}', polys, -0.07, coll, k=k)


def tile_auras(coll):
    z0, slab = backdrop(coll, (28, 120, 84), (86, 190, 130), 'ta')
    mound(coll, -0.78, 0.9, 0.22, (22, 96, 66), 'ta_m')
    b = names(coll)
    s = el_aura_ring(coll)
    sc = 0.86
    group(coll, b, loc=(0.0, 0.08), scale=sc)
    polys = [transform(p, scale=sc, dy=0.08) for p in s]
    parts = [(polys, sc)]
    # little scene: two small glowing orbs on the mound
    for k, (x, y, r) in enumerate([(-0.78, -0.72, 0.13), (0.82, -0.66, 0.1)]):
        orb = chaikin(circle(x, y, r, 24), 1)
        prism(f'ta_orb{k}', orb, -0.05, 0.16, material('ta_orb', lighter(MEADOW, 0.35), rough=0.4, emit=0.3), coll, bevel=0.06)
        parts.append(([orb], 0.5))
    finish_tile(coll, z0, slab, parts)


def tile_trails(coll):
    z0, slab = backdrop(coll, (52, 128, 214), (116, 180, 244), 'tt')
    path = bezier((-0.95, -0.72), (-0.45, -0.95), (0.05, -0.1), (0.78, 0.5))
    b = names(coll)
    s1 = el_swoosh(coll, lighter(BLUE, 0.15), lighter(BLUE, 0.75), path, 0.1, 0.42, depth=0.1)
    parts = [(s1, 0.9)]
    # three footprints walking up the ribbon, growing, each turned along the path
    for k, (u, sc) in enumerate(((0.16, 0.34), (0.5, 0.42), (0.86, 0.52))):
        i = int(u * (len(path) - 1))
        x, y = path[i]
        x2, y2 = path[min(len(path) - 1, i + 2)]
        rot = math.atan2(y2 - y, x2 - x) - math.pi / 2
        b2 = names(coll)
        fp = el_footprint(coll, PURPLE if k % 2 == 0 else lighter(PURPLE, 0.2))
        group(coll, b2, loc=(x, y + 0.04), scale=sc, rot=rot)
        parts.append(([transform(p, scale=sc, rot=rot, dx=x, dy=y + 0.04) for p in fp], sc))
    for k, (cx, cy, R) in enumerate([(0.82, 0.82, 0.24), (-0.74, 0.62, 0.17)]):
        sp = chaikin(sparkle_points(cx, cy, R, R * 0.36), 2)
        prism(f'tt_sp{k}', sp, -0.05, DEPTH * 0.7, material('tt_sp', lighter(GOLD, 0.2), rough=0.5, emit=0.3), coll, bevel=0.04)
        parts.append(([sp], 0.55))
    finish_tile(coll, z0, slab, parts)


def tile_eggs(coll):
    z0, slab = backdrop(coll, (226, 150, 62), (250, 200, 112), 'te')
    parts = []
    b = names(coll)
    nest = build_nest(coll)
    group(coll, b, loc=(0.0, -0.5), scale=0.9)
    parts.append(([transform(p, scale=0.9, dy=-0.5) for p in nest], 0.8))
    b2 = names(coll)
    sil = el_green_egg(coll)
    tilt = math.radians(8)
    group(coll, b2, loc=(0.0, 0.1), scale=0.85, rot=tilt)
    parts.insert(0, ([transform(p, scale=0.85, rot=tilt, dy=0.1) for p in sil], 0.85))
    for k, (cx, cy, R) in enumerate([(0.84, 0.62, 0.26), (-0.82, 0.74, 0.18)]):
        sp = chaikin(sparkle_points(cx, cy, R, R * 0.36), 2)
        prism(f'te_sp{k}', sp, -0.05, DEPTH * 0.7, material('te_sp', lighter(GOLD, 0.35), rough=0.5, emit=0.3), coll, bevel=0.04)
        parts.append(([sp], 0.55))
    finish_tile(coll, z0, slab, parts)


def tile_conditions(coll):
    z0, slab = backdrop(coll, (132, 78, 206), (186, 140, 240), 'tc')
    b = names(coll)
    s = el_rainbow_shell(coll)
    sc = 0.9
    group(coll, b, loc=(0.0, 0.06), scale=sc)
    finish_tile(coll, z0, slab, [([transform(p, scale=sc, dy=0.06) for p in s], sc)])


def tile_crystals(coll):
    z0, slab = backdrop(coll, (36, 62, 120), (86, 118, 196), 'tk')
    mound(coll, -0.80, 0.92, 0.2, (26, 44, 92), 'tk_m')
    b = names(coll)
    s = el_crystals(coll)
    sc = 0.85
    group(coll, b, loc=(0.0, -0.02), scale=sc)
    parts = [([transform(p, scale=sc, dy=-0.02) for p in s], sc)]
    for k, (cx, cy, R) in enumerate([(-0.8, 0.7, 0.2), (0.82, -0.2, 0.15)]):
        sp = chaikin(sparkle_points(cx, cy, R, R * 0.36), 2)
        prism(f'tk_sp{k}', sp, -0.05, DEPTH * 0.7, material('tk_sp', lighter(GOLD, 0.35), rough=0.5, emit=0.3), coll, bevel=0.04)
        parts.append(([sp], 0.55))
    finish_tile(coll, z0, slab, parts)


# ---------------------------------------------------------------- scene
def reset(size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    cy = scene.cycles
    cy.device = 'CPU'
    cy.samples = SAMPLES
    cy.use_denoising = True
    cy.filter_width = 1.5
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    world = bpy.data.worlds.new('soft fill')
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.86, 0.9, 1.0, 1)
    bg.inputs['Strength'].default_value = 0.55
    scene.world = world
    return scene


def lights(scene):
    key = bpy.data.lights.new('key', 'SUN')
    key.energy, key.angle = 2.4, math.radians(28)
    kobj = bpy.data.objects.new('key', key)
    kobj.rotation_euler = (math.radians(38), math.radians(-12), math.radians(-30))
    fill = bpy.data.lights.new('fill', 'SUN')
    fill.energy, fill.angle = 0.7, math.radians(60)
    fill.color = (0.78, 0.86, 1.0)
    fobj = bpy.data.objects.new('fill', fill)
    fobj.rotation_euler = (math.radians(50), math.radians(25), math.radians(140))
    rimlight = bpy.data.lights.new('rim', 'SUN')
    rimlight.energy, rimlight.angle = 0.6, math.radians(40)
    rimlight.color = (1.0, 0.95, 0.9)
    robj = bpy.data.objects.new('rimlight', rimlight)
    robj.rotation_euler = (math.radians(-55), math.radians(20), math.radians(150))
    for o in (kobj, fobj, robj):
        scene.collection.objects.link(o)


# key -> (file name, pixel size, ortho scale, builder, is_tile)
ASSETS = [
    ('tab_auras', 'shop-tab-auras-v1.png', 128, 2.42, 'icon', tab_auras),
    ('tab_trails', 'shop-tab-trails-v1.png', 128, 2.42, 'icon', build_tab_trails),
    ('tab_conditions', 'shop-tab-conditions-v1.png', 128, 2.42, 'icon', tab_conditions),
    ('tab_crystals', 'shop-tab-crystals-v1.png', 128, 2.42, 'icon', tab_crystals),
    ('egg_green_spotted', 'egg-green-spotted-v1.png', 256, 2.42, 'icon', build_egg_icon),
    ('tile_auras', 'shop-tile-auras-v1.png', 256, 2.74, 'tile', tile_auras),
    ('tile_trails', 'shop-tile-trails-v1.png', 256, 2.74, 'tile', tile_trails),
    ('tile_eggs', 'shop-tile-eggs-v1.png', 256, 2.74, 'tile', tile_eggs),
    ('tile_conditions', 'shop-tile-conditions-v1.png', 256, 2.74, 'tile', tile_conditions),
    ('tile_crystals', 'shop-tile-crystals-v1.png', 256, 2.74, 'tile', tile_crystals),
]


def main():
    scene = reset(128)
    lights(scene)
    OUT.mkdir(parents=True, exist_ok=True)
    cams, colls = {}, {}
    todo = [a for a in ASSETS if ONLY is None or a[0] in ONLY]
    for i, (key, _fn, _px, ortho, kind, builder) in enumerate(todo):
        coll = bpy.data.collections.new(key)
        scene.collection.children.link(coll)
        colls[key] = coll
        # build at the origin, then lift the whole collection to its own cell so the cameras never see each other
        result = builder(coll)
        if kind == 'icon':
            polys, z = result[0], result[1]
            plate_set(key, polys, z, coll)
        for o in list(coll.objects):
            if o.parent is None:
                o.location.x += i * 8.0
        cam_data = bpy.data.cameras.new(f'cam_{key}')
        cam_data.type, cam_data.ortho_scale = 'ORTHO', ortho
        cam = bpy.data.objects.new(f'cam_{key}', cam_data)
        cam.location = (i * 8.0, 0.0, 8.0)
        scene.collection.objects.link(cam)
        cams[key] = cam
    for key, fn, px, _ortho, _kind, _b in todo:
        for other, coll in colls.items():
            for o in coll.all_objects:
                o.hide_render = other != key
        scene.camera = cams[key]
        scene.render.resolution_x = scene.render.resolution_y = px
        path = OUT / fn
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print('rendered', path)
    for coll in colls.values():
        for o in coll.all_objects:
            o.hide_render = False
    if ONLY is None:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
        print('saved', BLEND)


main()
