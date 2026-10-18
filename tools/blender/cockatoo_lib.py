"""Cockatoo HQ model: shared helpers (BD-621 test model, docs/evidence/2026-10-18-cockatoo-blender).

Run inside Blender (MCP execute_blender_code): exec(open(path).read()). Units: 1 Blender unit = 1 stud. The creature faces +Y, Z up
(FBX export forward -Z, up Y puts +Y on Roblox -Z, the front).
"""
import bpy, bmesh, math, random, json, os
from mathutils import Vector, Matrix, Quaternion, Euler

ROOT = "C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-aa28642b94959e32b"
SP = "C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/"
PXS = 113.0  # reference pixels per stud (turnaround sheet: ground to crest tip = 7 studs)


def hexlin(h):
    """sRGB hex -> float tuple. NOTE: bmesh BYTE_COLOR layers store the sRGB-encoded value as is (no conversion), so we keep sRGB floats."""
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


# palette (sRGB hex read off the turnaround sheet)
CREAM = hexlin("#F8EFD8")
CREAM_SH = hexlin("#EBDDB8")
YELLOW = hexlin("#F6E65A")
YELLOW_PALE = hexlin("#F8EE95")
BEAK = hexlin("#4A4B50")
BEAK_TIP = hexlin("#2B2C30")
SCALE = hexlin("#6E655C")
SCALE_DK = hexlin("#4C4640")
CLAW = hexlin("#1B1B1E")
EYE_RIM = hexlin("#2A1A14")
EYE_IRIS = hexlin("#6B3A1E")
EYE_PUPIL = hexlin("#0A0A0A")
EYE_IRIS2 = hexlin("#7E4522")
EYE_IRIS3 = hexlin("#9A5A2C")
EYE_GLINT = hexlin("#FFFFFF")


class Part:
    """A bmesh with a corner colour layer; every added vertex carries a colour."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new("Col")

    def vert(self, co):
        return self.bm.verts.new(co)

    def face(self, vs, colors):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        for lo, c in zip(f.loops, colors):
            lo[self.col] = c
        return f

    def tri_count(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    def to_object(self, collection=None, origin=None):
        bm = self.bm
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(self.name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        for p in me.polygons:
            p.use_smooth = True
        return ob


def grid_strip(part, rows, cols_closed=False):
    """rows: list of lists of (co, color). Connect consecutive rows into quads (rows must have equal length or the last may be 1 vertex)."""
    vs = [[(part.vert(co), c) for co, c in r] for r in rows]
    for a, b in zip(vs[:-1], vs[1:]):
        if len(b) == 1:
            for i in range(len(a) - 1):
                part.face([a[i][0], a[i + 1][0], b[0][0]], [a[i][1], a[i + 1][1], b[0][1]])
        elif len(a) == 1:
            for i in range(len(b) - 1):
                part.face([a[0][0], b[i + 1][0], b[i][0]], [a[0][1], b[i + 1][1], b[i][1]])
        else:
            n = len(a)
            rng = range(n) if cols_closed else range(n - 1)
            for i in rng:
                j = (i + 1) % n
                part.face([a[i][0], a[j][0], b[j][0], b[i][0]], [a[i][1], a[j][1], b[j][1], b[i][1]])
    return vs


# feather profile: (t along length, half width factor). Rounded scallop tip (body feathers) or pointed blade (crest, tail, wing flights)
PROFILE_ROUND = [(0.0, 0.62), (0.32, 1.0), (0.62, 0.96), (0.86, 0.66), (1.0, 0.0)]
PROFILE_BLADE = [(0.0, 0.45), (0.25, 0.9), (0.55, 1.0), (0.82, 0.62), (1.0, 0.0)]
PROFILE_LEAF = [(0.0, 0.55), (0.3, 1.0), (0.6, 1.0), (0.82, 0.85), (0.94, 0.55), (1.0, 0.0)]
PROFILE_SHORT = [(0.0, 0.7), (0.45, 1.0), (0.8, 0.7), (1.0, 0.0)]


def feather(part, base, d, n, length, width, tilt=0.35, curl=0.0, cup=0.18, profile=PROFILE_ROUND, c0=CREAM, c1=CREAM, tip_from=0.0, roll=0.0, flick=None):
    """One feather: base point, flow direction d (unit), outward normal n (unit). tilt: radians lifting the tip away from the surface.
    curl: tip bend toward -n (positive) / +n (negative) as a fraction of length. cup: ridge height as a fraction of half-width."""
    d = Vector(d).normalized()
    n = Vector(n)
    n = (n - d * n.dot(d)).normalized()
    s = d.cross(n).normalized()
    if roll:
        q = Quaternion(d, roll)
        n = q @ n
        s = q @ s
    rows = []
    for t, wf in profile:
        # centreline: straight lifted line plus a curl that drops/raises the tip
        lift = math.sin(tilt) * t * length
        along = math.cos(tilt) * t * length
        drop = -curl * (t ** 2) * length
        centre = Vector(base) + d * along + n * (lift + drop)
        if flick is not None:
            centre = centre + Vector(flick) * (t ** 2) * length
        hw = width * 0.5 * wf
        col = mix(c0, c1, (t - tip_from) / max(1e-6, 1.0 - tip_from)) if t > tip_from else c0
        if wf == 0.0:
            rows.append([(centre, col)])
        else:
            rows.append([(centre - s * hw + n * (-0.05 * hw), col), (centre + n * (cup * hw), col), (centre + s * hw + n * (-0.05 * hw), col)])
    grid_strip(part, rows)


def catmull(pts, t):
    """Catmull-Rom through list of Vector, t in [0, len-1]."""
    n = len(pts)
    i = min(int(t), n - 2)
    u = t - i
    p0 = pts[max(i - 1, 0)]
    p1 = pts[i]
    p2 = pts[i + 1]
    p3 = pts[min(i + 2, n - 1)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def lerp_list(vals, t):
    n = len(vals)
    i = min(int(t), n - 2)
    u = t - i
    return vals[i] * (1 - u) + vals[i + 1] * u


class Tube:
    """Elliptical tube along a spine. spine: list of Vector; rx, ry: half sizes (side axis X-ish, forward axis F) at each spine point."""

    def __init__(self, spine, rx, ry, side=Vector((1, 0, 0)), samples=24):
        self.spine = [Vector(p) for p in spine]
        self.rxs = rx
        self.rys = ry
        self.side = Vector(side).normalized()
        self.samples = samples
        self.rings = []
        n = len(self.spine) - 1
        pos = [catmull(self.spine, n * k / samples) for k in range(samples + 1)]
        for k in range(samples + 1):
            u = n * k / samples
            p = pos[k]
            if k == 0:
                T = pos[1] - pos[0]
            elif k == samples:
                T = pos[k] - pos[k - 1]
            else:
                T = pos[k + 1] - pos[k - 1]
            T.normalize()
            F = T.cross(self.side).normalized()
            X = F.cross(T).normalized()
            self.rings.append((p, T, X, F, lerp_list(rx, u), lerp_list(ry, u)))
        # arc length
        self.arc = [0.0]
        for k in range(1, samples + 1):
            self.arc.append(self.arc[-1] + (self.rings[k][0] - self.rings[k - 1][0]).length)

    def at(self, s):
        """ring data at arc length s (0..total)."""
        s = max(0.0, min(self.arc[-1], s))
        k = 0
        while k < len(self.arc) - 2 and self.arc[k + 1] < s:
            k += 1
        u = (s - self.arc[k]) / max(1e-9, self.arc[k + 1] - self.arc[k])
        a, b = self.rings[k], self.rings[k + 1]
        p = a[0].lerp(b[0], u)
        T = a[1].lerp(b[1], u).normalized()
        X = a[2].lerp(b[2], u).normalized()
        F = a[3].lerp(b[3], u).normalized()
        return p, T, X, F, a[4] * (1 - u) + b[4] * u, a[5] * (1 - u) + b[5] * u

    def point(self, s, theta, scale=1.0):
        p, T, X, F, rx, ry = self.at(s)
        c, sn = math.cos(theta), math.sin(theta)
        pos = p + X * (rx * c * scale) + F * (ry * sn * scale)
        nrm = (X * (c / max(rx, 1e-6)) + F * (sn / max(ry, 1e-6))).normalized()
        return pos, nrm, T

    def total(self):
        return self.arc[-1]


def cap_ring(part, tube, s, segs, color, shrink, flip=False):
    pc, T, X, F, rx, ry = tube.at(s)
    cv = part.vert(pc)
    vs = [part.vert(tube.point(s, 2 * math.pi * j / segs, shrink)[0]) for j in range(segs)]
    for j in range(segs):
        a, b = vs[j], vs[(j + 1) % segs]
        if flip:
            part.face([cv, b, a], [color] * 3)
        else:
            part.face([cv, a, b], [color] * 3)


def tube_surface(part, tube, segs=10, rings=None, color=CREAM_SH, shrink=1.0, colorfn=None, cap_start=True, cap_end=True):
    rings = rings or max(4, len(tube.spine) * 2)
    tot = tube.total()
    rows = []
    for i in range(rings + 1):
        s = tot * i / rings
        row = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            pos, nrm, T = tube.point(s, th, shrink)
            row.append((pos, colorfn(s / tot, th) if colorfn else color))
        rows.append(row)
    grid_strip(part, rows, cols_closed=True)
    if cap_start:
        cap_ring(part, tube, 0.0, segs, color if not colorfn else colorfn(0, 0), shrink, flip=True)
    if cap_end:
        cap_ring(part, tube, tot, segs, color if not colorfn else colorfn(1, 0), shrink)


def feather_rows(part, tube, s0, s1, row_gap, width, length, flow=-1, around=(0.0, 2 * math.pi), tilt=0.32, curl=0.12, cup=0.18, jitter=0.0,
                 cfn=None, rng=None, stagger=True, skipfn=None, profile=PROFILE_ROUND, lenfn=None, wfn=None, tiltfn=None, lean=0.12, shrink=0.98):
    """Shingle rows of feathers over a tube from arc s0 to s1. flow=-1: feathers point toward the spine start (down/back); +1: toward the end.
    cfn(t, theta) -> (c0, c1, tip_from) colours of a feather."""
    rng = rng or random.Random(7)
    s = s0
    row = 0
    tot = tube.total()
    while s <= s1 + 1e-6:
        pc, T, X, F, rx, ry = tube.at(s)
        circ = math.pi * (3 * (rx + ry) - math.sqrt((3 * rx + ry) * (rx + 3 * ry)))
        w = (wfn(s / tot) if wfn else width)
        count = max(5, int(round(circ / (w * 0.86))))
        a0, a1 = around
        span = a1 - a0
        full = abs(span - 2 * math.pi) < 1e-6
        if not full:
            count = max(2, int(round(count * span / (2 * math.pi))))
        for k in range(count):
            u = (k + (0.5 if (stagger and row % 2) else 0.0)) / (count if full else max(1, count - 1))
            th = a0 + span * u
            pos, nrm, Tn = tube.point(s, th, shrink)
            if skipfn and skipfn(pos, nrm, s / tot, th):
                continue
            Lf = (lenfn(s / tot, th) if lenfn else length) * (1 + jitter * (rng.random() - 0.5))
            tl = tiltfn(s / tot, th) if tiltfn else tilt
            d = Tn * flow + X * (math.cos(th) * lean)
            c0, c1, tf = cfn(s / tot, th) if cfn else (CREAM, CREAM, 0.0)
            feather(part, pos, d, nrm, Lf, w, tilt=tl + 0.08 * (rng.random() - 0.5), curl=curl, cup=cup, profile=profile, c0=c0, c1=c1, tip_from=tf,
                    roll=jitter * (rng.random() - 0.5))
        s += row_gap
        row += 1


def eye_dome(part, centre, axis, radius, ring_deg, band_colors, segs=14):
    """Sphere cap/ball around `axis` with polar rings at ring_deg (degrees from the axis); every face band is ONE flat colour (crisp pupil / iris / rim)."""
    z = Vector(axis).normalized()
    x = Vector((0, 0, 1)).cross(z)
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x).normalized()
    rings = []
    for deg in ring_deg:
        th = math.radians(deg)
        if deg == 0:
            rings.append([part.vert(Vector(centre) + z * radius)])
        else:
            rings.append([part.vert(Vector(centre) + (x * math.cos(2 * math.pi * j / segs) * math.sin(th) + y * math.sin(2 * math.pi * j / segs) * math.sin(th) + z * math.cos(th)) * radius)
                          for j in range(segs)])
    for bi in range(len(rings) - 1):
        col = band_colors[bi]
        a, b = rings[bi], rings[bi + 1]
        for j in range(segs):
            k = (j + 1) % segs
            vs = [a[0], b[j], b[k]] if len(a) == 1 else [a[j], b[j], b[k], a[k]]
            face_out(part, vs, [col] * len(vs), centre)


def face_out(part, vs, cols, centre):
    """add a face wound so that its normal points away from `centre`."""
    n = (vs[1].co - vs[0].co).cross(vs[2].co - vs[0].co)
    cen = sum((v.co for v in vs), Vector()) / len(vs)
    if n.dot(cen - Vector(centre)) < 0:
        vs, cols = vs[::-1], cols[::-1]
    return part.face(vs, cols)


def pface(part, vs, cols):
    """face with reversed winding (sphere / claw builders are written inside-out)."""
    return part.face(vs[::-1], cols[::-1])


def sphere(part, centre, radii, colorfn, segs=10, rings=7, rot=None):
    """UV sphere (radii Vector), colorfn(direction_unit)->colour; rot a Matrix3 for orientation."""
    rot = rot or Matrix.Identity(3)
    rows = []
    for i in range(rings + 1):
        v = math.pi * i / rings
        row = []
        if i in (0, rings):
            d = Vector((0, 0, 1 if i == 0 else -1))
            row = [(centre + rot @ Vector((d.x * radii.x, d.y * radii.y, d.z * radii.z)), colorfn(rot @ d))]
        else:
            for j in range(segs):
                u = 2 * math.pi * j / segs
                d = Vector((math.sin(v) * math.cos(u), math.sin(v) * math.sin(u), math.cos(v)))
                row.append((centre + rot @ Vector((d.x * radii.x, d.y * radii.y, d.z * radii.z)), colorfn(rot @ d)))
        rows.append(row)
    # build, closing the ring dimension
    vs = [[(part.vert(co), c) for co, c in r] for r in rows]
    for a, b in zip(vs[:-1], vs[1:]):
        if len(b) == 1:
            for j in range(len(a)):
                k = (j + 1) % len(a)
                pface(part, [a[j][0], a[k][0], b[0][0]], [a[j][1], a[k][1], b[0][1]])
        elif len(a) == 1:
            for j in range(len(b)):
                k = (j + 1) % len(b)
                pface(part, [a[0][0], b[k][0], b[j][0]], [a[0][1], b[k][1], b[j][1]])
        else:
            n = len(a)
            for j in range(n):
                k = (j + 1) % n
                pface(part, [a[j][0], a[k][0], b[k][0], b[j][0]], [a[j][1], a[k][1], b[k][1], b[j][1]])


def cone_claw(part, base, direction, up, length, radius, curve, color=CLAW, segs=5, steps=4):
    """Curved cone claw: base centre, direction of growth, up = side the claw curves toward (curve fraction of length)."""
    d = Vector(direction).normalized()
    u = (Vector(up) - d * Vector(up).dot(d)).normalized()
    s = d.cross(u).normalized()
    rows = []
    for i in range(steps + 1):
        t = i / steps
        c = Vector(base) + d * (t * length) + u * (curve * length * t * t)
        r = radius * (1 - t) ** 0.85
        if i == steps:
            rows.append([(c, color)])
        else:
            rows.append([(c + (s * math.cos(2 * math.pi * j / segs) + u * math.sin(2 * math.pi * j / segs)) * r, color) for j in range(segs)])
    vs = [[(part.vert(co), c) for co, c in r] for r in rows]
    for a, b in zip(vs[:-1], vs[1:]):
        if len(b) == 1:
            for j in range(len(a)):
                k = (j + 1) % len(a)
                pface(part, [a[j][0], a[k][0], b[0][0]], [a[j][1], a[k][1], b[0][1]])
        else:
            n = len(a)
            for j in range(n):
                k = (j + 1) % n
                pface(part, [a[j][0], a[k][0], b[k][0], b[j][0]], [a[j][1], a[k][1], b[k][1], b[j][1]])
    # base cap
    cv = part.vert(Vector(base))
    a = vs[0]
    for j in range(len(a)):
        k = (j + 1) % len(a)
        pface(part, [cv, a[k][0], a[j][0]], [color] * 3)


# ---------------------------------------------------------------- scene / render helpers
def wipe_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.cameras, bpy.data.lights, bpy.data.materials, bpy.data.images):
        for x in list(coll):
            coll.remove(x)


def make_material():
    mat = bpy.data.materials.new("Cockatoo_VColor")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    a = nt.nodes.new("ShaderNodeVertexColor")
    a.layer_name = "Col"
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.85
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(b.outputs[0], o.inputs[0])
    return mat


def setup_render(res=(530, 840)):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    try:
        ev = sc.eevee
        ev.use_raytracing = True
        ev.use_fast_gi = True
        ev.fast_gi_method = "AMBIENT_OCCLUSION_ONLY"
        ev.taa_render_samples = 48
        ev.use_shadows = True
    except Exception as ex:  # older / newer builds
        print("eevee setup", ex)
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.9, 0.9, 0.92, 1)
    bg.inputs["Strength"].default_value = 0.55
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    def light(name, kind, energy, loc, rot, color=(1, 0.97, 0.92)):
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.color = color
        if kind == "SUN":
            ld.angle = math.radians(10)
        ob = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = [math.radians(a) for a in rot]
        return ob
    light("Key", "SUN", 2.6, (5, -5, 8), (50, 0, 35))
    light("Fill", "SUN", 0.4, (-5, 5, 4), (60, 0, -145), (0.85, 0.9, 1.0))


def ref_camera(view, res=(530, 840), cx=0.0, cz=3.5, scale=None):
    """Orthographic camera framed like the reference crop. view: front / side / back. Returns the camera object."""
    sc = bpy.context.scene
    cam = bpy.data.objects.get("RefCam")
    if cam is None:
        cd = bpy.data.cameras.new("RefCam")
        cam = bpy.data.objects.new("RefCam", cd)
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.data.ortho_scale = scale or (res[1] / PXS)
    cam.data.clip_start, cam.data.clip_end = 0.1, 100
    if view == "side":
        cam.location = (30, cx, cz)
        cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    elif view == "front":
        cam.location = (cx, 30, cz)
        cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    elif view == "back":
        cam.location = (cx, -30, cz)
        cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    return cam


# per-view crop centre (studs) derived from the reference crops: Y0 at sheet x=680 (side), X0 at sheet x=200 (front), 1280 (back)
VIEWS = {
    "side": dict(res=(530, 840), cx=(650 - 680) / PXS, cz=(915 - 520) / PXS),
    "front": dict(res=(380, 840), cx=-(230 - 200) / PXS, cz=(915 - 520) / PXS),
    "back": dict(res=(420, 840), cx=(1280 - 1280) / PXS + (1280 - 1280) / PXS, cz=(915 - 520) / PXS),
}


def aim_key(cam_dir):
    """point the Key sun from the camera side (up and a little to the left) so every review view is lit from the front."""
    key = bpy.data.objects.get("Key")
    if key is None:
        return
    cd = Vector(cam_dir).normalized()
    side = Vector((0, 0, 1)).cross(cd)
    travel = -(cd * 0.8 + Vector((0, 0, 0.62)) - side * 0.3)
    key.rotation_euler = travel.to_track_quat("-Z", "Y").to_euler()


def render_view(view, path, objects=None, cx_adj=0.0, cz_adj=0.0):
    v = VIEWS[view]
    cam = ref_camera(view, v["res"], v["cx"] + cx_adj, v["cz"] + cz_adj)
    aim_key({"side": (1, 0, 0), "front": (0, 1, 0), "back": (0, -1, 0)}[view])
    sc = bpy.context.scene
    if objects is not None:
        for ob in bpy.data.objects:
            if ob.type == "MESH":
                ob.hide_render = ob.name not in objects
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            ob.hide_render = False
    return path


def tri_total(objs):
    t = 0
    for ob in objs:
        t += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return t


def shot(loc, tgt, path, res=(900, 900), lens=60):
    """perspective review picture from `loc` looking at `tgt` (uses the RefCam object)."""
    sc = bpy.context.scene
    cam = ref_camera("side", res)
    cam.data.type = "PERSP"
    cam.data.lens = lens
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    aim_key(Vector(loc) - Vector(tgt))
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
