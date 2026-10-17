"""BD-178: the 10 trail shop icons (one per trail in ProgressionConfig.Trails) as real Blender renders.

Run headless (no Studio, no MCP session):
    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python tools/blender/build_trail_icons.py
Optional: add `-- --size 128` or `-- --samples 128`. Outputs:
    resources/ui/v2/icons/trail-<id>-v1.png   128 x 128 RGBA, transparent background (the files to upload)
    tools/blender/trail_icons.blend           the scene, one collection per icon, so the shapes can be edited
Then run `python tools/make_trail_icon_sheet.py` for the contact sheet and `python tools/verify_trail_icons.py`.

Same look as the mutation badges (tools/blender/build_mutation_badges.py, BD-190; docs/114 handbook, docs/72 children and
readable at 64 px): chunky soft-bevel matte 3D symbol, one soft key light, a white rim plus a thin soft navy outer line so it reads
on light AND dark panels. The colours are read from ProgressionConfig.luau (`color` = the body, `accent` = the highlight), so the
icon always matches the ribbon the player sees. Every icon has its own silhouette (never colour only):
    white puff cloud | fern leaf | tidal bubbles | ember flame | violet pulse rings | electric arc between two nodes
    frost comet | solar sun | nova four-point sparkle | astra five-point star
The 2D outlines are authored as point lists below (Blender is only the modelling and render tool). Nothing is drawn per pixel.
The shared helpers (colour, outline and plate helpers, scene, lights) are the ones of build_mutation_badges.py, kept in step on
purpose; that script is not imported because it renders on import.
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
BLEND = ROOT / 'tools/blender/trail_icons.blend'
CONFIG = ROOT / 'src/shared/ProgressionConfig.luau'

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SIZE = int(argv[argv.index('--size') + 1]) if '--size' in argv else 128
SAMPLES = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 128

ORDER = ['white', 'fern', 'tidal', 'ember', 'violet', 'electric', 'frost', 'solar', 'nova', 'astra']
SHAPES = {'white': 'puff', 'fern': 'leaf', 'tidal': 'bubbles', 'ember': 'flame', 'violet': 'pulse', 'electric': 'arc',
          'frost': 'comet', 'solar': 'sun', 'nova': 'sparkle', 'astra': 'star'}
RIM = (246, 250, 255)   # light rim: white with a hint of blue
LINE = (44, 50, 98)     # thin outer line: navy (the handbook outline family), opaque so overlapping plates never double up
RIM_W = 0.075
LINE_W = 0.05


# ---------------------------------------------------------------- colours
def trail_colours():
    """{id: (color, accent)} from the Trails table of ProgressionConfig.luau."""
    text = CONFIG.read_text(encoding='utf-8')
    found = {m.group(1): (tuple(int(m.group(i)) for i in (2, 3, 4)), tuple(int(m.group(i)) for i in (5, 6, 7)))
             for m in re.finditer(r'\{id="(\w+)",name="[^"]*",rarity="\w+",price=\d+,level=\d+,speed=[\d.]+,'
                                  r'color=\{(\d+),(\d+),(\d+)\},accent=\{(\d+),(\d+),(\d+)\}', text)}
    missing = [i for i in ORDER if i not in found]
    if missing:
        raise SystemExit(f'ProgressionConfig.luau has no trail colours for {missing}')
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


# ---------------------------------------------------------------- the ten symbols
# Each builder returns the polygons of the silhouette (for rim + line) after adding its meshes.
DEPTH = 0.34


def soft(col, t=0.5):
    """An accent pulled toward white, so a highlight never fights the silhouette."""
    return mix(col, (255, 255, 255), t)


def sparkle_points(cx, cy, R, r, pts=4, rot=0.0):
    out = []
    for i in range(pts * 2):
        a = math.pi / 2 + rot + i * math.pi / pts
        rad = R if i % 2 == 0 else r
        out.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return out


def build_puff(coll, col, acc, origin):
    """White: a plump dust puff (the plain trail) with two little motes trailing behind."""
    blobs = [(-0.50, -0.20, 0.44), (0.0, 0.10, 0.58), (0.52, -0.18, 0.46), (-0.12, -0.46, 0.40), (0.26, -0.46, 0.38)]
    shade = mix(col, (150, 170, 215), 0.30)   # cool grey-blue shade: a white body on a white rim needs form shading to read
    body = mix(col, (150, 170, 215), 0.10)
    sil = []
    for k, (cx, cy, r) in enumerate(blobs):
        pts = chaikin(circle(cx, cy, r, 30), 1)
        prism(f'puff_{k}', pts, 0, DEPTH - 0.02 * k, material(f'puff{k}', body if k in (1, 2) else shade, emit=0.0), coll, bevel=0.16, origin=origin)
        sil.append(pts)
    glint = chaikin(circle(-0.10, 0.34, 0.16, 20), 1)
    prism('puff_glint', glint, DEPTH, 0.08, material('puff_glint', (255, 255, 255), rough=0.4, emit=0.2), coll, bevel=0.04, origin=origin)
    for k, (cx, cy, r) in enumerate([(-0.86, 0.34, 0.1), (-0.96, 0.02, 0.07)]):
        m = chaikin(circle(cx, cy, r, 16), 1)
        prism(f'puff_mote{k}', m, 0, DEPTH * 0.7, material('mote', shade), coll, bevel=0.04, origin=origin)
        sil.append(m)
    return sil


def build_leaf(coll, col, acc, origin):
    """Fern: one plump leaf on a diagonal with a raised midrib, side veins and a little stem."""
    n = 28
    half = []
    for i in range(n + 1):
        u = i / n
        half.append((-0.92 + 1.84 * u, 0.62 * math.sin(math.pi * u) ** 0.8 * (1 - 0.25 * u)))
    outline = chaikin(half + [(x, -w) for x, w in half[::-1][1:-1]], 1)
    tilt = math.radians(32)
    outline = transform(outline, rot=tilt)
    prism('leaf_body', outline, 0, DEPTH, material('leaf', col), coll, bevel=0.17, origin=origin)
    vein_m = material('vein', soft(acc, 0.1), rough=0.5, emit=0.2)
    prism('leaf_rib', transform(capsule(-0.70, 0.0, 0.68, 0.0, 0.07), rot=tilt), DEPTH - 0.04, 0.1, vein_m, coll, bevel=0.035, origin=origin)
    for k, u in enumerate((-0.30, 0.08, 0.44)):
        for sgn in (-1, 1):
            vein = transform(capsule(u, 0.0, u + 0.26, sgn * 0.30, 0.045), rot=tilt)
            prism(f'leaf_vein{k}{sgn}', vein, DEPTH - 0.04, 0.08, vein_m, coll, bevel=0.025, origin=origin)
    stem = transform(capsule(-1.05, 0.0, -0.80, 0.0, 0.065), rot=tilt)
    prism('leaf_stem', stem, 0, DEPTH * 0.6, material('stem', darker(col, 0.25)), coll, bevel=0.03, origin=origin)
    return [outline, stem]


def build_bubbles(coll, col, acc, origin):
    """Tidal: three bubbles of different sizes, each with a lighter inner disc and a glint."""
    specs = [(-0.28, -0.22, 0.60), (0.52, 0.42, 0.40), (0.56, -0.58, 0.26)]
    sil = []
    for k, (cx, cy, r) in enumerate(specs):
        pts = chaikin(circle(cx, cy, r, 40), 1)
        prism(f'bub_{k}', pts, 0, DEPTH * (0.9 + 0.1 * k), material(f'bub{k}', col), coll, bevel=min(0.2, r * 0.38), origin=origin)
        inner = chaikin(circle(cx + r * 0.05, cy - r * 0.04, r * 0.62, 32), 1)
        prism(f'bub_in_{k}', inner, DEPTH - 0.06, 0.05, material('bub_in', soft(acc, 0.45), rough=0.45, emit=0.22), coll, bevel=0.03, origin=origin)
        arc = [(cx + r * 0.55 * math.cos(math.radians(160 - i * 7.0)), cy + r * 0.55 * math.sin(math.radians(160 - i * 7.0))) for i in range(12)]
        thick = [(cx + (x - cx) * 0.78, cy + (y - cy) * 0.78) for x, y in arc[::-1]]
        prism(f'bub_glint_{k}', chaikin(arc + thick, 2), DEPTH, 0.08, material('glint', (255, 255, 255), rough=0.4, emit=0.4), coll, bevel=0.025, origin=origin)
        sil.append(pts)
    return sil


def build_flame(coll, col, acc, origin):
    """Ember: a plump two-tongue flame with a golden core."""
    raw = [(0.10, 1.05), (0.30, 0.56), (0.60, 0.18), (0.72, -0.30), (0.50, -0.78), (0.0, -1.0), (-0.52, -0.80),
           (-0.74, -0.34), (-0.62, 0.10), (-0.50, 0.46), (-0.22, 0.24), (-0.12, 0.62)]
    pts = chaikin(raw, 3)
    prism('flame_body', pts, 0, DEPTH, material('flame', col), coll, bevel=0.2, origin=origin)
    inner = chaikin(transform(raw, scale=0.5, dy=-0.02, about=(0.0, -0.8)), 3)
    prism('flame_core', inner, DEPTH - 0.04, 0.1, material('flame_core', acc, rough=0.5, emit=0.35), coll, bevel=0.04, origin=origin)
    return [pts]


def torus(name, cx, cy, R, r, mat, coll, origin):
    """A chunky ring lying in the picture plane (half sunk so the back is flat)."""
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=48, minor_segments=20,
                                     location=(origin[0] + cx, origin[1] + cy, r * 0.75))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale.z = 0.75
    link(obj, coll)
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return obj


def build_pulse(coll, col, acc, origin):
    """Violet: a bright core dot inside two separate pulse rings, on a soft lilac disc."""
    prism('pulse_disc', chaikin(circle(0, 0, 0.70, 44), 1), 0, 0.12, material('pulse_disc', soft(col, 0.62), emit=0.12), coll, bevel=0.04, origin=origin)
    torus('pulse_ring_out', 0, 0, 0.78, 0.125, material('ring_out', col), coll, origin)
    torus('pulse_ring_mid', 0, 0, 0.40, 0.12, material('ring_mid', mix(col, acc, 0.35)), coll, origin)
    prism('pulse_core', chaikin(circle(0, 0, 0.14, 28), 1), 0, DEPTH, material('pulse_core', acc, rough=0.5, emit=0.3), coll, bevel=0.07, origin=origin)
    return [circle(0, 0, 0.90, 48)]


def build_arc(coll, col, acc, origin):
    """Electric: two round nodes joined by a jagged chunky arc, with a spark above the middle."""
    zig = [(-0.60, -0.10), (-0.34, 0.50), (-0.10, -0.50), (0.16, 0.50), (0.40, -0.50), (0.62, 0.10)]
    sil = []
    core_m = material('arc_core', soft(acc, 0.25), rough=0.45, emit=0.4)
    for k in range(len(zig) - 1):
        a, b = zig[k], zig[k + 1]
        seg = capsule(a[0], a[1], b[0], b[1], 0.17)
        prism(f'arc_seg{k}', seg, 0, DEPTH, material('arc', col), coll, bevel=0.08, segments=4, origin=origin)
        prism(f'arc_core{k}', capsule(a[0], a[1], b[0], b[1], 0.065), DEPTH - 0.03, 0.08, core_m, coll, bevel=0.025, segments=3, origin=origin)
        sil.append(seg)
    for k, (cx, cy) in enumerate([(-0.74, -0.12), (0.76, 0.12)]):
        node = chaikin(circle(cx, cy, 0.28, 28), 1)
        prism(f'arc_node{k}', node, 0, DEPTH + 0.06, material('node', mix(col, acc, 0.45)), coll, bevel=0.1, origin=origin)
        prism(f'arc_node_core{k}', circle(cx, cy, 0.12, 16), DEPTH + 0.05, 0.07, material('node_core', acc, rough=0.5, emit=0.4), coll, bevel=0.03, origin=origin)
        sil.append(node)
    star = chaikin(sparkle_points(0.0, 0.80, 0.30, 0.09), 2)
    prism('arc_spark', star, 0, DEPTH * 0.8, material('spark', acc, rough=0.5, emit=0.35), coll, bevel=0.05, origin=origin)
    sil.append(star)
    return sil


def build_comet(coll, col, acc, origin):
    """Frost: an icy comet flying up and to the right, with a tapering tail and two flakes."""
    head_c = (0.40, 0.34)
    tail = chaikin([(0.18, 0.66), (-0.20, 0.32), (-0.60, -0.16), (-0.96, -0.78), (-0.30, -0.62), (0.02, -0.34), (0.40, -0.20), (0.62, 0.0)], 3)
    prism('comet_tail', tail, 0, DEPTH * 0.85, material('comet_tail', col), coll, bevel=0.14, origin=origin)
    core = chaikin(transform([(0.10, 0.50), (-0.20, 0.24), (-0.58, -0.14), (-0.80, -0.56), (-0.30, -0.46), (0.0, -0.22), (0.34, -0.10), (0.50, 0.06)],
                             scale=0.62, dx=0.02, dy=0.03), 3)
    prism('comet_tail_core', core, DEPTH * 0.85 - 0.03, 0.07, material('comet_tail_core', soft(acc, 0.2), rough=0.5, emit=0.22), coll, bevel=0.03, origin=origin)
    head = chaikin(circle(head_c[0], head_c[1], 0.40, 40), 1)
    prism('comet_head', head, 0, DEPTH + 0.06, material('comet_head', mix(col, (255, 255, 255), 0.25), rough=0.45, emit=0.14), coll, bevel=0.16, origin=origin)
    prism('comet_glint', chaikin(circle(head_c[0] - 0.1, head_c[1] + 0.12, 0.13, 20), 1), DEPTH + 0.04, 0.08,
          material('glint', (255, 255, 255), rough=0.4, emit=0.5), coll, bevel=0.03, origin=origin)
    sil = [tail, head]
    for k, (cx, cy, R) in enumerate([(0.74, -0.52, 0.22), (-0.58, 0.60, 0.17)]):
        fl = chaikin(sparkle_points(cx, cy, R, R * 0.38), 2)
        prism(f'comet_flake{k}', fl, 0, DEPTH * 0.7, material('flake', mix(col, (255, 255, 255), 0.4)), coll, bevel=0.04, origin=origin)
        sil.append(fl)
    return sil


def build_sun(coll, col, acc, origin):
    """Solar: a round sun with eight plump rays and a bright centre."""
    sil = []
    ray_m = material('ray', mix(col, (255, 150, 60), 0.35))
    for k in range(8):
        a = math.radians(90 + 45 * k)
        ca, sa = math.cos(a), math.sin(a)
        ray = chaikin([(0.62 * ca - 0.17 * sa, 0.62 * sa + 0.17 * ca), (1.0 * ca - 0.04 * sa, 1.0 * sa + 0.04 * ca),
                       (1.0 * ca + 0.04 * sa, 1.0 * sa - 0.04 * ca), (0.62 * ca + 0.17 * sa, 0.62 * sa - 0.17 * ca)], 2)
        prism(f'sun_ray{k}', ray, 0, DEPTH - 0.06, ray_m, coll, bevel=0.07, segments=4, origin=origin)
        sil.append(ray)
    disc = chaikin(circle(0, 0, 0.58, 44), 1)
    prism('sun_disc', disc, 0, DEPTH + 0.04, material('sun', col), coll, bevel=0.18, origin=origin)
    prism('sun_core', chaikin(circle(0, 0, 0.34, 32), 1), DEPTH, 0.1, material('sun_core', acc, rough=0.5, emit=0.35), coll, bevel=0.06, origin=origin)
    sil.append(disc)
    return sil


def build_sparkle(coll, col, acc, origin):
    """Nova: a big four-point sparkle with a golden core, one small sparkle and a dot."""
    big = chaikin(sparkle_points(-0.12, -0.04, 1.0, 0.24), 2)
    prism('nova_big', big, 0, DEPTH, material('nova', col), coll, bevel=0.12, origin=origin)
    prism('nova_core', chaikin(sparkle_points(-0.12, -0.04, 0.58, 0.14), 2), DEPTH - 0.04, 0.1,
          material('nova_core', acc, rough=0.5, emit=0.3), coll, bevel=0.04, origin=origin)
    small = chaikin(sparkle_points(0.70, 0.64, 0.34, 0.09), 2)
    prism('nova_small', small, 0, DEPTH * 0.85, material('nova_small', acc, rough=0.5, emit=0.3), coll, bevel=0.06, origin=origin)
    dot = chaikin(circle(0.66, -0.58, 0.11, 18), 1)
    prism('nova_dot', dot, 0, DEPTH * 0.7, material('nova_dot', acc, rough=0.5, emit=0.3), coll, bevel=0.04, origin=origin)
    return [big, small, dot]


def build_star(coll, col, acc, origin):
    """Astra: a plump five-point star with a pink heart of light and two tiny pink sparkles."""
    outer = chaikin(sparkle_points(0.0, 0.0, 1.0, 0.50, pts=5), 2)
    prism('astra_star', outer, 0, DEPTH, material('astra', col), coll, bevel=0.17, origin=origin)
    prism('astra_core', chaikin(sparkle_points(0.0, 0.0, 0.52, 0.27, pts=5), 2), DEPTH - 0.04, 0.1,
          material('astra_core', acc, rough=0.5, emit=0.3), coll, bevel=0.05, origin=origin)
    sil = [outer]
    for k, (cx, cy, R) in enumerate([(0.82, 0.74, 0.2), (-0.84, 0.70, 0.15)]):
        sp = chaikin(sparkle_points(cx, cy, R, R * 0.36), 2)
        prism(f'astra_sp{k}', sp, 0, DEPTH * 0.7, material('astra_sp', acc, rough=0.5, emit=0.3), coll, bevel=0.04, origin=origin)
        sil.append(sp)
    return sil


BUILDERS = {'white': build_puff, 'fern': build_leaf, 'tidal': build_bubbles, 'ember': build_flame, 'violet': build_pulse,
            'electric': build_arc, 'frost': build_comet, 'solar': build_sun, 'nova': build_sparkle, 'astra': build_star}


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
    colours = trail_colours()
    scene = reset()
    lights(scene)
    OUT.mkdir(parents=True, exist_ok=True)
    cams, colls = {}, {}
    for i, tid in enumerate(ORDER):
        coll = bpy.data.collections.new(f'trail_{tid}_{SHAPES[tid]}')
        scene.collection.children.link(coll)
        colls[tid] = coll
        origin = (i * 4.0, 0.0)
        col, acc = colours[tid]
        polys = BUILDERS[tid](coll, col, acc, origin)
        plate_set(SHAPES[tid], polys, 0.0, coll, origin=origin)
        cam_data = bpy.data.cameras.new(f'cam_{tid}')
        cam_data.type, cam_data.ortho_scale = 'ORTHO', 2.42
        cam = bpy.data.objects.new(f'cam_{tid}', cam_data)
        cam.location = (origin[0], origin[1], 6.0)
        scene.collection.objects.link(cam)
        cams[tid] = cam
    for tid in ORDER:
        for other, coll in colls.items():
            for o in coll.all_objects:
                o.hide_render = other != tid
        scene.camera = cams[tid]
        path = OUT / f'trail-{tid}-v1.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print('rendered', path)
    for coll in colls.values():
        for o in coll.all_objects:
            o.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    print('saved', BLEND)


main()
