"""BD-190: the 7 mutation badge icons (drop, bolt, snowflake, pebble, flame, ribbon, moon) as real Blender renders.

Run headless (no Studio, no MCP session):
    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python tools/blender/build_mutation_badges.py
Optional: add `-- --size 128` or `-- --samples 128`. Outputs:
    resources/ui/v2/icons/mutation-<id>-v1.png   128 x 128 RGBA, transparent background (the files to upload)
    tools/blender/mutation_badges.blend           the scene, one collection per icon, so the shapes can be edited
Then run `python tools/make_mutation_badge_sheet.py` for the contact sheet and `python tools/verify_mutation_badges.py`.

Look (docs/114 handbook: calm, bubbly, matte, vibrant; docs/72: children, readable at 64 px):
  * each icon is a chunky soft-bevel 3D symbol in its MutationLook badge colour (read from src/shared/MutationLook.luau, so the
    two cannot drift), one soft key light, a soft fill, matte plastic;
  * a white rim plus a thin soft navy outer line around the silhouette so it reads on light AND dark panels;
  * every icon has its own SILHOUETTE (never colour-only); the pebble is deliberately faceted low-poly, the rest are soft pillows.
The 2D outlines are authored as point lists below (Blender is only the modelling and render tool). Nothing is drawn per pixel.
"""
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'resources/ui/v2/icons'
BLEND = ROOT / 'tools/blender/mutation_badges.blend'
LOOK = ROOT / 'src/shared/MutationLook.luau'

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SIZE = int(argv[argv.index('--size') + 1]) if '--size' in argv else 128
SAMPLES = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 128

ORDER = ['dewdrop', 'charged', 'frost', 'seismic', 'ember', 'aurora', 'bloodmoon']
RIM = (246, 250, 255)   # light rim: white with a hint of blue
LINE = (44, 50, 98)     # thin outer line: navy (the handbook outline family), opaque so overlapping plates never double up
RIM_W = 0.075
LINE_W = 0.05


# ---------------------------------------------------------------- colours
def badge_colours():
    text = LOOK.read_text(encoding='utf-8')
    found = {m.group(1): tuple(int(m.group(i)) for i in (2, 3, 4))
             for m in re.finditer(r'\{id = "(\w+)".*?badge = \{(\d+), (\d+), (\d+)\}', text, re.S)}
    missing = [i for i in ORDER if i not in found]
    if missing:
        raise SystemExit(f'MutationLook.luau has no badge colour for {missing}')
    return found


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


def offset(pts, d):
    """Polygon offset (d > 0 grows). Mitred per vertex with a clamp; the outlines are rounded first, so this stays tidy."""
    pts = ccw(pts)
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*e1) or 1, math.hypot(*e2) or 1
        n1 = (e1[1] / l1, -e1[0] / l1)
        n2 = (e2[1] / l2, -e2[0] / l2)
        m = (n1[0] + n2[0], n1[1] + n2[1])
        lm = math.hypot(*m) or 1
        m = (m[0] / lm, m[1] / lm)
        k = max(0.55, m[0] * n1[0] + m[1] * n1[1])
        out.append((p1[0] + m[0] * d / k, p1[1] + m[1] * d / k))
    return out


def transform(pts, scale=1.0, dx=0.0, dy=0.0, rot=0.0, about=(0.0, 0.0)):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for x, y in pts:
        x, y = (x - about[0]) * scale, (y - about[1]) * scale
        out.append((x * c - y * s + about[0] + dx, x * s + y * c + about[1] + dy))
    return out


def circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


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


def flat_material(name, rgb255, alpha=1.0):
    """Unlit rim / line plate: emission, optionally mixed with transparency for the soft outer line."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emi = nt.nodes.new('ShaderNodeEmission')
    emi.inputs['Color'].default_value = rgba(rgb255)
    emi.inputs['Strength'].default_value = 1.0
    if alpha < 1.0:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        mx.inputs['Fac'].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(emi.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs['Surface'])
    else:
        nt.links.new(emi.outputs[0], out.inputs['Surface'])
    return mat


def link(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def prism(name, pts, z0, depth, mat, coll, bevel=0.0, segments=5, smooth=True, origin=(0, 0)):
    """Extruded 2D outline as a mesh; optional soft bevel (harden normals keep the faces calm)."""
    pts = ccw(pts)
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    ring = [bm.verts.new((x + origin[0], y + origin[1], z0)) for x, y in pts]
    face = bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=[face])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [v for v in ext['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in top:
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


def plate_mesh(name, polys, d, z, mat, coll, origin):
    """Flat plate = the silhouette plus a capsule along every edge (a Minkowski grow by d). Robust in concave notches, where a
    plain polygon offset folds over itself. Everything is one mesh of overlapping coplanar faces in ONE unlit material."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    def add(pts):
        pts = ccw(pts)
        try:
            bm.faces.new([bm.verts.new((x + origin[0], y + origin[1], z)) for x, y in pts])
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


def plate_set(name, polys, z, coll, origin=(0, 0)):
    """White rim + thin navy outer line behind the symbol. Flat unlit plates, placed under the body."""
    plate_mesh(f'{name}_line', polys, RIM_W + LINE_W, z - 0.02, flat_material('line', LINE), coll, origin)
    plate_mesh(f'{name}_rim', polys, RIM_W, z - 0.01, flat_material('rim', RIM), coll, origin)


# ---------------------------------------------------------------- the seven symbols
# Each builder returns the polygons of the silhouette (for rim + line) after adding its meshes.
DEPTH = 0.34


def build_drop(coll, col, origin):
    r, cy, tip = 0.66, -0.26, 1.0
    d = tip - cy
    phi = math.acos(r / d)
    pts = [(0.0, tip)]
    steps = 40
    a0, a1 = phi, 2 * math.pi - phi
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        pts.append((r * math.sin(a), cy + r * math.cos(a)))
    pts = chaikin(pts, 1)
    body = material('drop', col)
    prism('drop_body', pts, 0, DEPTH, body, coll, bevel=0.2, origin=origin)
    # soft highlight: a curved glint plus a small bead, lighter than the body
    glint = material('drop_glint', lighter(col, 0.78), rough=0.4, emit=0.3)
    arc = []
    for i in range(14):
        a = math.radians(205 - i * 6.0)
        arc.append((0.42 * math.cos(a) , cy + 0.1 + 0.42 * math.sin(a)))
    thick = [(x * 0.82, (y - cy - 0.1) * 0.82 + cy + 0.1) for x, y in arc[::-1]]
    glint_pts = chaikin(arc + thick, 2)
    prism('drop_glint', glint_pts, DEPTH - 0.04, 0.09, glint, coll, bevel=0.035, origin=origin)
    bead = circle(-0.40, cy - 0.28, 0.07, 18)
    prism('drop_bead', bead, DEPTH - 0.04, 0.09, glint, coll, bevel=0.03, origin=origin)
    return [pts]


def build_bolt(coll, col, origin):
    raw = [(-0.24, 1.0), (0.66, 1.0), (0.32, 0.26), (0.74, 0.26), (-0.34, -1.04), (-0.14, -0.08), (-0.70, -0.08)]
    pts = chaikin(raw, 1)
    body = material('bolt', col)
    prism('bolt_body', pts, 0, DEPTH, body, coll, bevel=0.11, origin=origin)
    core = material('bolt_core', lighter(col, 0.45), rough=0.5, emit=0.1)
    inner = chaikin(transform(raw, scale=0.46, dx=0.02, dy=0.02, about=(0.0, -0.02)), 1)
    prism('bolt_core', inner, DEPTH - 0.04, 0.08, core, coll, bevel=0.03, origin=origin)
    return [pts]


def build_frost(coll, col, origin):
    """Six chunky arms with two side branches each and a hexagon hub. Parts overlap (same colour, branches a hair lower than the
    arms, hub a hair higher) so no boolean is needed and the crossings read as a stepped crystal."""
    body = material('frost', col)
    hub_m = material('frost_hub', lighter(col, 0.35), rough=0.45, emit=0.14)
    core_m = material('frost_core', lighter(col, 0.8), rough=0.4, emit=0.2)
    sil = []
    for k in range(6):
        ang = math.radians(90 + 60 * k)
        ca, sa = math.cos(ang), math.sin(ang)
        arm = capsule(0, 0, 0.90 * ca, 0.90 * sa, 0.115)
        prism(f'frost_arm{k}', arm, 0, DEPTH, body, coll, bevel=0.08, segments=4, origin=origin)
        sil.append(arm)
        bx, by = 0.50 * ca, 0.50 * sa
        for sgn in (-1, 1):
            b = ang + sgn * math.radians(55)
            br = capsule(bx, by, bx + 0.31 * math.cos(b), by + 0.31 * math.sin(b), 0.085)
            prism(f'frost_branch{k}{sgn}', br, 0, DEPTH - 0.07, body, coll, bevel=0.06, segments=4, origin=origin)
            sil.append(br)
    hexa = chaikin(circle(0, 0, 0.32, 6), 2)
    prism('frost_hub', hexa, 0, DEPTH + 0.06, hub_m, coll, bevel=0.1, segments=5, origin=origin)
    prism('frost_core', chaikin(circle(0, 0, 0.15, 6), 2), DEPTH + 0.02, 0.08, core_m, coll, bevel=0.035, origin=origin)
    sil.append(hexa)
    return sil


def build_pebble(coll, col, origin):
    """Faceted low-poly stones (flat shaded, almost no bevel): a big pebble and a small one."""
    sil = []

    def stone(tag, cx, cy, rx, ry, height, seed, colour):
        n = 9
        jit = [1.0, 0.92, 1.06, 0.95, 1.04, 0.9, 1.05, 0.96, 1.02]
        rot = seed * 0.7
        mesh = bpy.data.meshes.new(tag)
        bm = bmesh.new()

        def ring(scale, z, j=0.0):
            vs = []
            for i in range(n):
                a = rot + 2 * math.pi * i / n
                k = jit[(i + seed) % n]
                f = scale * (1 + (k - 1) * (1 + j))
                vs.append(bm.verts.new((origin[0] + cx + rx * f * math.cos(a), origin[1] + cy + ry * f * math.sin(a), z)))
            return vs
        bottom = ring(1.0, 0.0)
        side = ring(1.0, height * 0.30)
        shoulder = ring(0.84, height * 0.72, 0.4)
        crown = ring(0.46, height * 0.95, 1.0)
        top = bm.verts.new((origin[0] + cx + rx * 0.04, origin[1] + cy + ry * 0.05, height * 1.05))
        bm.faces.new(bottom[::-1])
        for a, b in ((bottom, side), (side, shoulder), (shoulder, crown)):
            for i in range(n):
                bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
        for i in range(n):
            bm.faces.new((crown[i], crown[(i + 1) % n], top))
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(tag, mesh)
        coll.objects.link(obj)
        obj.data.materials.append(material(tag, colour, rough=0.8, emit=0.14))
        sil.append([(cx + rx * 1.0 * (1 + (jit[(i + seed) % n] - 1)) * math.cos(rot + 2 * math.pi * i / n),
                     cy + ry * (1 + (jit[(i + seed) % n] - 1)) * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)])
        return obj
    stone('pebble_small', 0.56, -0.50, 0.38, 0.32, 0.42, 3, darker(col, 0.18))
    stone('pebble_big', -0.20, 0.10, 0.74, 0.64, 0.62, 0, col)
    return sil


def build_flame(coll, col, origin):
    raw = [(0.08, 1.05), (0.34, 0.60), (0.66, 0.16), (0.74, -0.30), (0.52, -0.76), (0.02, -0.98), (-0.50, -0.80),
           (-0.76, -0.36), (-0.66, 0.12), (-0.46, 0.52), (-0.32, 0.18), (-0.16, 0.62)]
    pts = chaikin(raw, 3)
    body = material('flame', col)
    prism('flame_body', pts, 0, DEPTH, body, coll, bevel=0.2, origin=origin)
    core = material('flame_core', (255, 214, 96), rough=0.5, emit=0.35)
    inner_raw = transform(raw, scale=0.5, dy=-0.02, about=(0.0, -0.78))
    inner = chaikin(inner_raw, 3)
    prism('flame_core', inner, DEPTH - 0.04, 0.10, core, coll, bevel=0.04, origin=origin)
    return [pts]


def build_ribbon(coll, col, origin):
    def band(ycentre, amp, wmax, x0=-0.96, x1=0.96, n=40):
        top, bot = [], []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            u = (x - x0) / (x1 - x0)
            c = ycentre + amp * math.sin(2 * math.pi * u)
            w = 0.08 + wmax * math.sin(math.pi * u) ** 0.6
            top.append((x, c + w / 2))
            bot.append((x, c - w / 2))
        return top + bot[::-1]
    violet = (178, 130, 255)
    back = chaikin(band(-0.40, 0.28, 0.44, x0=-0.90, x1=0.92), 1)
    front = chaikin(band(0.30, 0.28, 0.50), 1)
    prism('ribbon_back', back, 0, DEPTH, material('ribbon_back', violet), coll, bevel=0.17, origin=origin)
    prism('ribbon_front', front, 0, DEPTH, material('ribbon', col), coll, bevel=0.17, origin=origin)
    return [back, front]


def build_moon(coll, col, origin):
    R, r = 0.94, 0.78
    cx, cy = 0.40, 0.26     # the bite: a smaller circle pushed to the upper right
    dist = math.hypot(cx, cy)
    ang_c = math.atan2(cy, cx)
    # circle-circle intersection angles on the outer circle
    cosv = (R * R + dist * dist - r * r) / (2 * R * dist)
    da = math.acos(max(-1, min(1, cosv)))
    a_start, a_end = ang_c + da, ang_c - da + 2 * math.pi
    outer = [(R * math.cos(a_start + (a_end - a_start) * i / 48), R * math.sin(a_start + (a_end - a_start) * i / 48)) for i in range(49)]
    # inner arc back along the bite circle
    p_end = outer[-1]
    p_start = outer[0]
    b_end = math.atan2(p_start[1] - cy, p_start[0] - cx)
    b_start = math.atan2(p_end[1] - cy, p_end[0] - cx)
    while b_end < b_start:
        b_end += 2 * math.pi
    # take the arc that lies inside the outer circle
    inner = [(cx + r * math.cos(b_start + (b_end - b_start) * i / 40), cy + r * math.sin(b_start + (b_end - b_start) * i / 40)) for i in range(41)]
    if math.hypot(*inner[20]) > R:
        inner = [(cx + r * math.cos(b_start - (2 * math.pi - (b_end - b_start)) * i / 40), cy + r * math.sin(b_start - (2 * math.pi - (b_end - b_start)) * i / 40)) for i in range(41)]
    pts = chaikin(outer + inner[1:-1], 1)
    prism('moon_body', pts, 0, DEPTH, material('moon', col), coll, bevel=0.2, origin=origin)
    # little star in the bite
    star = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rad = 0.30 if i % 2 == 0 else 0.145
        star.append((0.34 + rad * math.cos(a), 0.30 + rad * math.sin(a)))
    star = chaikin(star, 2)
    prism('moon_star', star, 0, DEPTH * 0.8, material('moon_star', lighter(col, 0.42), rough=0.45, emit=0.25), coll, bevel=0.07, origin=origin)
    return [pts, star]


BUILDERS = {'dewdrop': build_drop, 'charged': build_bolt, 'frost': build_frost, 'seismic': build_pebble,
            'ember': build_flame, 'aurora': build_ribbon, 'bloodmoon': build_moon}
SHAPES = {'dewdrop': 'drop', 'charged': 'bolt', 'frost': 'snowflake', 'seismic': 'pebble', 'ember': 'flame', 'aurora': 'ribbon', 'bloodmoon': 'moon'}


# ---------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    cy = scene.cycles
    cy.device = 'CPU'
    cy.samples = SAMPLES
    cy.use_denoising = True
    cy.filter_width = 1.5
    scene.render.resolution_x = scene.render.resolution_y = SIZE
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
    kobj.rotation_euler = (math.radians(38), math.radians(-12), math.radians(-30))  # from upper left, mostly front
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


def main():
    colours = badge_colours()
    scene = reset()
    lights(scene)
    OUT.mkdir(parents=True, exist_ok=True)
    cams, colls = {}, {}
    for i, mid in enumerate(ORDER):
        coll = bpy.data.collections.new(f'badge_{SHAPES[mid]}')
        scene.collection.children.link(coll)
        colls[mid] = coll
        origin = (i * 4.0, 0.0)
        polys = BUILDERS[mid](coll, colours[mid], origin)
        plate_set(SHAPES[mid], polys, 0.0, coll, origin=origin)
        cam_data = bpy.data.cameras.new(f'cam_{mid}')
        cam_data.type, cam_data.ortho_scale = 'ORTHO', 2.42
        cam = bpy.data.objects.new(f'cam_{mid}', cam_data)
        cam.location = (origin[0], origin[1], 6.0)
        scene.collection.objects.link(cam)
        cams[mid] = cam
    for mid in ORDER:
        for other, coll in colls.items():
            for o in coll.all_objects:
                o.hide_render = other != mid
        scene.camera = cams[mid]
        path = OUT / f'mutation-{mid}-v1.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print('rendered', path)
    for coll in colls.values():
        for o in coll.all_objects:
            o.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    print('saved', BLEND)


main()
