"""Be Dino! anime FX P0 + P1 renders and meshes (BD-430, BD-431; docs/123 section 3). Real Blender renders, headless, Cycles.

Regenerate everything (renders, exports the three FX shell meshes, then Pillow only pastes the finished 128 px frames into 4 x 4 sheets):

    python tools/render_fx_anime.py

or by hand:

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup \
        --python tools/blender/build_fx_anime.py -- --frames build/fx-anime-frames --out resources/effects/fx-v2 \
        --meshes assets/blender/fx --blend tools/blender/fx_anime_v1.blend [--only flameTongue] [--samples 64]

One Blender scene per texture (the .blend opens as a small catalogue), plus a "fxMeshes" scene that holds the three meshes and a
"preview_*" scene per mesh. Everything is white on straight alpha (the runtime tints with Color / Color3); nothing is coloured.

  slot (EffectAssets key)  scene          size              what is rendered
  flameTongue (BD-430)     flameTongue    4x4 of 128        16 frames: a calm cluster of three soft flame tongues (bent, tapered tubes
                                                            with a facing-soft emission), sway only, no flicker
  starPop (BD-430)         starPop        4x4 of 128        16 frames: a four-point twinkle (concave superellipse star + diagonal star +
                                                            soft halo) that pops with a small overshoot, rests, twists a little and fades
  domeGradient (BD-430)    domeGradient   512x512           UV texture of the shock dome: bright thin rim at the base, soft body, empty apex,
                                                            gentle vertical streaks that tile around the dome (u wraps)
  shaftGradient (BD-431)   shaftGradient  256x512           UV texture of the light shaft cone: bright at the source (top), fading down, soft ray streaks
  shellEdge (BD-431)       shellEdge      512x512           UV texture of the aura shell: a soft band that is empty at both poles, wisps that tile around
  speedStreaks (BD-431)    speedStreaks   512x512           four soft streaks (modelled tapered ellipsoids): head right, tail fading left

Meshes (FBX, 1 unit = 1 stud, Z up in Blender = Y up in Roblox, UV: u around, v = 0 at the base / bottom, 1 at the top):
  shock_dome   16 segments hemisphere, open at the base, pivot at the base centre, radius 2        (112 tris)
  shaft_cone   20 segments truncated cone, open both ends, pivot at the top (the light source)       (80 tris)
  aura_shell   12 x 8 slightly egg-shaped inflated shell, pivot at the centre, radius 2               (144 tris)
These are FX shells, not world models. The gradient textures above are what they are meant to wear.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fx_common import (Graph, all_fcurves, blur_compositor, hide_except, link, new_scene, parse_args)  # noqa: E402

CELL = 128
FRAMES = 16


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def clamp01(x):
    return max(0.0, min(1.0, x))


# --------------------------------------------------------------------------- geometry helpers
def uv_plane(sc, name, mat, hx, hy, z=0.0, cx=0.0, cy=0.0):
    """A flat quad with a full 0..1 UV square (v = 0 at the bottom edge)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(cx - hx, cy - hy, z), (cx + hx, cy - hy, z), (cx + hx, cy + hy, z), (cx - hx, cy + hy, z)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, co in zip(me.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop.index].uv = co
    me.materials.append(mat)
    return link(sc, bpy.data.objects.new(name, me))


def poly_obj(sc, name, pts, mat, z=0.0):
    """Convex-or-star polygon filled as a fan around its centroid (pts in the XY plane)."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    verts = [(cx, cy, z)] + [(x, y, z) for x, y in pts]
    faces = [(0, 1 + i, 1 + (i + 1) % len(pts)) for i in range(len(pts))]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    return link(sc, bpy.data.objects.new(name, me))


def const_mat(name, alpha):
    mat = bpy.data.materials.new(name)
    G = Graph(mat)
    G.emit(alpha)
    return mat


def disc_mat(name, alpha, power):
    """Radial soft disc: alpha * (1 - r)^power on a plane that spans the whole UV square."""
    mat = bpy.data.materials.new(name)
    G = Graph(mat)
    r = G.uv_radius()
    fall = G.ramp(r, 1.0, 0.0)
    G.emit(G.op("MULTIPLY", G.op("POWER", fall, power), alpha))
    return mat


def facing_mat(name, alpha, power):
    mat = bpy.data.materials.new(name)
    G = Graph(mat)
    G.emit(G.op("MULTIPLY", G.facing(power), alpha))
    return mat


# --------------------------------------------------------------------------- FLAME TONGUE (BD-430)
def tongue_obj(sc, name, mat, base, height, rmax, lean, curl, rings=30, segs=20):
    """One flame tongue: a tapered tube whose centre line leans and curls. Radius r(s) ~ s^0.5 (1 - s)^0.85: a round bottom, the
    widest point about a third up, then a taper to a soft point. The tube is a real 3D surface, so its facing-based alpha
    falls to zero at the silhouette: a soft body with an opaque core."""
    p1, p2 = 0.5, 0.85
    sm = p1 / (p1 + p2)
    peak = sm ** p1 * (1 - sm) ** p2
    centre = []
    for i in range(rings + 1):
        s = i / rings
        x = base[0] + lean * s ** 1.7 + curl * s ** 2.6
        y = base[1] + height * s
        centre.append((x, y))
    verts, faces = [], []
    pole0 = (centre[0][0], centre[0][1], 0.0)
    verts.append(pole0)
    ring_index = []
    for i in range(1, rings):
        s = i / rings
        r = rmax * (s ** p1 * (1 - s) ** p2) / peak
        tx, ty = centre[i + 1][0] - centre[i - 1][0], centre[i + 1][1] - centre[i - 1][1]
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln                      # in-plane normal of the centre line
        idx = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            verts.append((centre[i][0] + nx * r * math.cos(a), centre[i][1] + ny * r * math.cos(a), r * 0.9 * math.sin(a)))
            idx.append(len(verts) - 1)
        ring_index.append(idx)
    verts.append((centre[rings][0], centre[rings][1], 0.0))
    top = len(verts) - 1
    first, last = ring_index[0], ring_index[-1]
    for j in range(segs):
        faces.append((0, first[(j + 1) % segs], first[j]))
        faces.append((top, last[j], last[(j + 1) % segs]))
    for a, b in zip(ring_index, ring_index[1:]):
        for j in range(segs):
            faces.append((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    return link(sc, bpy.data.objects.new(name, me))


def build_flame(opts):
    sc = new_scene("flameTongue", CELL, frames=FRAMES, samples=opts["samples"] or 192, ortho=2.0)
    sc.cycles.transparent_max_bounces = 32
    body = facing_mat("flame_body", 0.5, 0.9)    # soft translucent outer body
    core = facing_mat("flame_core", 0.95, 0.8)       # opaque heart
    # three tongues: (dx, height factor, width factor, lean factor, phase). The side licks are shorter and lean away.
    tongues = [(0.0, 1.00, 1.00, 1.0, 0.00), (-0.25, 0.58, 0.62, -1.3, 0.35), (0.26, 0.44, 0.52, 1.5, 0.62)]
    base_y = -0.74
    for f in range(1, FRAMES + 1):
        u = (f - 1) / (FRAMES - 1)
        grow = 0.30 + 0.70 * ease(u / 0.30)                        # bud -> full height over the first third
        tail = ease((u - 0.70) / 0.30)                             # shrinks and thins at the end
        for k, (dx, hf, wf, lf, ph) in enumerate(tongues):
            lag = ease((u - 0.06 * k) / 0.30)                      # the side licks start a little later
            g = 0.30 + 0.70 * lag if k else grow
            h = 1.34 * hf * g * (1.0 - 0.78 * tail) * (1.0 + 0.025 * math.sin(2 * math.pi * (u + ph)))
            r = 0.27 * wf * (0.55 + 0.45 * g) * (1.0 - 0.45 * tail)
            lean = 0.22 * lf * math.sin(2 * math.pi * (u * 1.0 + ph)) + 0.06 * lf
            curl = 0.12 * lf * math.sin(2 * math.pi * (u * 2.0 + ph + 0.2))
            x = dx * (0.7 + 0.3 * g)
            ob = tongue_obj(sc, f"tongue{k}_f{f}", body, (x, base_y + 0.012 * k), h, r, lean, curl)
            hide_except(ob, f, FRAMES)
            if k == 0:
                inner = tongue_obj(sc, f"core_f{f}", core, (x, base_y + 0.03), h * 0.64, r * 0.55, lean * 0.45, curl * 0.35)
                hide_except(inner, f, FRAMES)
    blur_compositor(sc, [(2.4, 1.0)])
    return {"flameTongue": sc}


# --------------------------------------------------------------------------- STAR POP (BD-430)
def star_pts(L, n=0.72, count=96, rot=0.0):
    """Four-point twinkle: |x/L|^n + |y/L|^n = 1 (n < 1 pinches the four points), turned by `rot`."""
    pts = []
    for i in range(count):
        a = 2 * math.pi * i / count
        c, s = math.cos(a), math.sin(a)
        x = L * math.copysign(abs(c) ** (2 / n), c)
        y = L * math.copysign(abs(s) ** (2 / n), s)
        pts.append((x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)))
    return pts


def build_star(opts):
    sc = new_scene("starPop", CELL, frames=FRAMES, samples=opts["samples"] or 192, ortho=2.0)
    sc.cycles.transparent_max_bounces = 32
    for f in range(1, FRAMES + 1):
        u = (f - 1) / (FRAMES - 1)
        # size: a dot, a soft pop with a small overshoot (0.32), settle (0.48), rest, then shrink away
        if u < 0.32:
            s = 0.16 + 0.98 * ease(u / 0.32)
        elif u < 0.48:
            s = 1.14 - 0.14 * ease((u - 0.32) / 0.16)
        elif u < 0.70:
            s = 1.0 - 0.06 * ease((u - 0.48) / 0.22)
        else:
            s = 0.94 * (1.0 - 0.82 * ease((u - 0.70) / 0.30))
        fade = 1.0 - 0.55 * ease((u - 0.72) / 0.28)
        rot = math.radians(24) * ease(u)                           # a slow twist over the whole pop
        L = 0.66 * s
        halo = disc_mat(f"halo_f{f}", 0.50 * fade, 1.8)
        hr = 0.82 * (0.45 + 0.55 * s)
        o = uv_plane(sc, f"halo_f{f}", halo, hr, hr, z=0.0)
        hide_except(o, f, FRAMES)
        body = const_mat(f"star_f{f}", 0.95 * fade)
        o = poly_obj(sc, f"star_f{f}", star_pts(L, 0.50, rot=rot), body, z=0.01)
        hide_except(o, f, FRAMES)
        diag = const_mat(f"diag_f{f}", 0.72 * fade)
        o = poly_obj(sc, f"diag_f{f}", star_pts(L * 0.55, 0.52, rot=rot + math.radians(45)), diag, z=0.02)
        hide_except(o, f, FRAMES)
        heart = disc_mat(f"heart_f{f}", 1.0 * fade, 0.9)
        hr2 = 0.26 * (0.5 + 0.5 * s)
        o = uv_plane(sc, f"heart_f{f}", heart, hr2, hr2, z=0.03)
        hide_except(o, f, FRAMES)
    blur_compositor(sc, [(5.0, 1.0), (1.4, 0.7)])
    return {"starPop": sc}


# --------------------------------------------------------------------------- GRADIENT TEXTURES (analytic shader nodes on a UV plane)
def streaks(G, u, freq, wobble, depth, phase=0.0):
    """Soft vertical streaks that tile around (integer frequencies only): 1 - depth .. 1."""
    w = G.op("MULTIPLY", G.op("SINE", G.op("MULTIPLY", u, 2 * math.pi * 3)), wobble)
    wave = G.op("SINE", G.op("ADD", G.op("MULTIPLY", u, 2 * math.pi * freq), G.op("ADD", w, phase)))
    return G.op("ADD", 1.0 - depth, G.op("MULTIPLY", G.op("MULTIPLY", G.op("ADD", wave, 1.0), 0.5), depth))


def gradient_scene(name, w, h, samples, alpha_fn):
    sc = new_scene(name, (w, h), frames=1, samples=samples, ortho=2.0)
    # the camera covers the longer side with ortho_scale; make the plane exactly the frame
    scale = sc.camera.data.ortho_scale
    hx, hy = scale * (w / max(w, h)) / 2.0, scale * (h / max(w, h)) / 2.0
    mat = bpy.data.materials.new(name + "_mat")
    G = Graph(mat)
    u, v = G.uv()
    G.emit(alpha_fn(G, u, v))
    uv_plane(sc, name + "_plane", mat, hx, hy)
    return sc


def dome_alpha(G, u, v):
    # v: 0 at the base rim .. 1 at the apex. A thin bright rim just above the base, a soft body, nothing near the apex.
    rim_up = G.ramp(v, 0.012, 0.075)
    rim_down = G.ramp(v, 0.15, 0.075)
    rim = G.op("MULTIPLY", rim_up, rim_down)
    body_in = G.ramp(v, 0.01, 0.10)
    body_out = G.ramp(v, 0.78, 0.10)
    body = G.op("MULTIPLY", G.op("POWER", body_out, 1.5), G.op("MULTIPLY", body_in, 0.52))
    st = streaks(G, u, 12, 0.35, 0.22)
    soft = G.op("MAXIMUM", G.op("MULTIPLY", rim, 0.95), G.op("MULTIPLY", body, st))
    return soft


def shaft_alpha(G, u, v):
    # v: 0 at the wide bottom .. 1 at the source (top). Bright at the source, fading down; both ends are empty rows.
    top_in = G.ramp(v, 1.0, 0.93)                       # empty top row, brightens immediately
    along = G.op("POWER", G.ramp(v, 0.08, 0.98), 1.25)  # brighter towards the source
    ray = streaks(G, u, 7, 0.55, 0.30)
    return G.op("MULTIPLY", G.op("MULTIPLY", along, top_in), G.op("MULTIPLY", ray, 0.9))


def shell_alpha(G, u, v):
    # v: 0 at the south pole .. 1 at the north pole. A soft band peaking a little below the middle, empty at both poles.
    up = G.ramp(v, 0.0, 0.40)
    down = G.ramp(v, 0.98, 0.40)
    band = G.op("POWER", G.op("MULTIPLY", up, down), 0.9)
    wisp = G.op("MULTIPLY", streaks(G, u, 5, 0.6, 0.4), streaks(G, u, 9, 0.3, 0.25, 1.3))
    return G.op("MULTIPLY", G.op("MULTIPLY", band, 0.62), wisp)


def build_gradients(opts):
    s = opts["samples"] or 96
    return {
        "domeGradient": gradient_scene("domeGradient", 512, 512, s, dome_alpha),
        "shaftGradient": gradient_scene("shaftGradient", 256, 512, s, shaft_alpha),
        "shellEdge": gradient_scene("shellEdge", 512, 512, s, shell_alpha),
    }


# --------------------------------------------------------------------------- SPEED STREAKS (BD-431): four modelled tapered ellipsoids
def build_streaks(opts):
    sc = new_scene("speedStreaks", 512, frames=1, samples=opts["samples"] or 192, ortho=2.0)
    sc.cycles.transparent_max_bounces = 32
    px = 2.0 / 512.0
    # (row centre px from the top, length px, half thickness px, head power)
    rows = [(64, 452, 7.0, 1.0), (192, 372, 5.0, 0.9), (320, 306, 9.0, 1.1), (448, 214, 4.0, 0.85)]
    for k, (cy, length, half, power) in enumerate(rows):
        mat = bpy.data.materials.new(f"streak{k}_mat")
        G = Graph(mat)
        geo = G.N.n("ShaderNodeTexCoord")
        sep = G.N.n("ShaderNodeSeparateXYZ")
        G.t.links.new(geo.outputs["Object"], sep.inputs[0])
        # object x runs -1 (tail) .. +1 (head): the head stays solid, the tail dissolves
        fade = G.ramp(sep.outputs[0], -1.0, 0.45)
        G.emit(G.op("MULTIPLY", G.facing(power), G.op("MULTIPLY", G.op("POWER", fade, 1.3), 0.96)))
        me = bpy.data.meshes.new(f"streak{k}")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=1.0)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mat)
        ob = link(sc, bpy.data.objects.new(f"streak{k}", me))
        ob.scale = (length / 2 * px, half * px, half * px)
        ob.location = (0.0, (256 - cy) * px, 0.0)
    blur_compositor(sc, [(1.8, 1.0)])
    return {"speedStreaks": sc}


# --------------------------------------------------------------------------- MESHES (FBX): shock dome, light shaft cone, aura shell
def lathe(name, profile, segs, tilt=None):
    """Surface of revolution about Z. profile = [(radius, z, v), ...] from bottom to top; a radius of 0 is a pole (a fan of triangles).
    UV: u = segment / segs (the seam gets its own u = 1 column), v from the profile. Faces point outward; quads are triangulated."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for r, z, v in profile:
        if r == 0:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), z)) for j in range(segs)])

    def vert(ri, j):
        ring = rings[ri]
        return ring[0] if len(ring) == 1 else ring[j % segs]

    def face(items):
        f = bm.faces.new([it[0] for it in items])
        for loop, it in zip(f.loops, items):
            loop[uvl].uv = (it[1], it[2])
    for ri in range(len(profile) - 1):
        v0, v1 = profile[ri][2], profile[ri + 1][2]
        for j in range(segs):
            u0, u1, um = j / segs, (j + 1) / segs, (j + 0.5) / segs
            a0, a1, b0, b1 = vert(ri, j), vert(ri, j + 1), vert(ri + 1, j), vert(ri + 1, j + 1)
            if profile[ri][0] == 0:
                face([(a0, um, v0), (b1, u1, v1), (b0, u0, v1)])
            elif profile[ri + 1][0] == 0:
                face([(a0, u0, v0), (a1, u1, v0), (b0, um, v1)])
            else:
                face([(a0, u0, v0), (a1, u1, v0), (b1, u1, v1), (b0, u0, v1)])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    if tilt:
        for v in bm.verts:
            tilt(v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return bpy.data.objects.new(name, me)


def build_meshes():
    R = 2.0
    dome_profile = [(R * math.cos(math.radians(a)), R * math.sin(math.radians(a)), a / 90.0) for a in (0, 20, 42, 66)] + [(0.0, R, 1.0)]
    dome = lathe("fx_shock_dome", dome_profile, 16)
    H = 8.0
    cone = lathe("fx_shaft_cone", [(2.2, -H, 0.0), (1.45, -H / 2, 0.5), (0.7, 0.0, 1.0)], 20)
    shell_profile = [(0.0, -R, 0.0)]
    for k in range(1, 7):
        lat = -90.0 + 180.0 * k / 7
        shell_profile.append((R * math.cos(math.radians(lat)), R * math.sin(math.radians(lat)), k / 7))
    shell_profile.append((0.0, R, 1.0))

    def egg(v):                      # a little narrower at the top and rounder at the bottom: an egg, not a ball
        k = 1.0 - 0.11 * max(0.0, v.co.z / R) + 0.04 * max(0.0, -v.co.z / R)
        v.co.x *= k
        v.co.y *= k
    shell = lathe("fx_aura_shell", shell_profile, 12, tilt=egg)
    return [dome, cone, shell]


def tri_count(ob):
    me = ob.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def export_meshes(objs, out_dir):
    """Export each mesh on its own as FBX (1 unit = 1 stud, Z up -> Y up) and write the tri / size manifest the verifier reads."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    files = {"fx_shock_dome": "shock-dome.fbx", "fx_shaft_cone": "shaft-cone.fbx", "fx_aura_shell": "aura-shell.fbx"}
    home = bpy.context.scene
    for ob in objs:
        home.collection.objects.link(ob)
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = out_dir / files[ob.name]
        bpy.ops.export_scene.fbx(filepath=str(path.resolve()), use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                                 axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False)
        ob.select_set(False)
        home.collection.objects.unlink(ob)
        bb = [Vector(c) for c in ob.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]
        mx = [max(v[i] for v in bb) for i in range(3)]
        manifest[files[ob.name]] = {"tris": tri_count(ob), "verts": len(ob.data.vertices), "size_studs": [round(mx[i] - mn[i], 3) for i in range(3)],
                                    "min": [round(x, 3) for x in mn], "max": [round(x, 3) for x in mx]}
        print("exported", path, manifest[files[ob.name]])
    (out_dir / "fx-meshes.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")


def mesh_scene(objs):
    sc = bpy.data.scenes.new("fxMeshes")
    for k, ob in enumerate(objs):
        ob.location = (k * 6.0, 0.0, 0.0)
        link(sc, ob)
    return sc


# --------------------------------------------------------------------------- mesh previews (evidence renders: each mesh wearing its own texture, tinted)
def preview(name, ob, tex_path, tint, cam_loc, cam_target, floor_z, stand_in=False, size=384):
    """One evidence render: the mesh with its gradient texture (white on alpha, tinted amber / cream / mint here) over a dark floor.
    Cycles, emission only, so it shows exactly what the UV + texture look like; this is NOT what Roblox will draw pixel for pixel."""
    sc = bpy.data.scenes.new("preview_" + name)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x = r.resolution_y = size
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = False
    sc.cycles.transparent_max_bounces = 24
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("preview_" + name + "_world")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.09, 1)
    sc.world = w
    cam = bpy.data.cameras.new("preview_" + name + "_cam")
    cam.lens = 45
    cob = bpy.data.objects.new("preview_" + name + "_cam", cam)
    cob.location = cam_loc
    cob.rotation_euler = (Vector(cam_target) - Vector(cam_loc)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cob)
    sc.camera = cob
    mat = bpy.data.materials.new("preview_" + name + "_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    img = bpy.data.images.load(str(Path(tex_path).resolve()))
    img.alpha_mode = "STRAIGHT"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "REPEAT"
    emis = nt.nodes.new("ShaderNodeEmission")
    emis.inputs["Color"].default_value = (*tint, 1)
    emis.inputs["Strength"].default_value = 1.5
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(clear.outputs[0], mix.inputs[1])
    nt.links.new(emis.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    shell = ob.copy()
    shell.data = ob.data.copy()
    shell.data.materials.clear()
    shell.data.materials.append(mat)
    shell.location = (0, 0, 0)
    sc.collection.objects.link(shell)
    # matte floor disc (and a plain stand-in body for the shell): reference only, never exported
    matte = bpy.data.materials.new("preview_" + name + "_matte")
    matte.use_nodes = True
    pb = next(n for n in matte.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    pb.inputs["Base Color"].default_value = (0.12, 0.13, 0.2, 1)
    n = 48
    fme = bpy.data.meshes.new("preview_" + name + "_floor")
    fme.from_pydata([(9 * math.cos(2 * math.pi * i / n), 9 * math.sin(2 * math.pi * i / n), floor_z) for i in range(n)], [], [tuple(range(n))])
    fme.materials.append(matte)
    sc.collection.objects.link(bpy.data.objects.new("preview_" + name + "_floor", fme))
    if stand_in:
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
        sme = bpy.data.meshes.new("preview_stand_in")
        bm.to_mesh(sme)
        bm.free()
        sme.materials.append(matte)
        so = bpy.data.objects.new("preview_stand_in", sme)
        so.scale = (1.0, 1.35, 0.9)
        so.location = (0, 0, -0.45)
        sc.collection.objects.link(so)
        lamp = bpy.data.lights.new("preview_lamp", "SUN")
        lamp.energy = 3.0
        lo = bpy.data.objects.new("preview_lamp", lamp)
        lo.rotation_euler = (math.radians(50), 0, math.radians(30))
        sc.collection.objects.link(lo)
    return sc


def build_previews(mesh_objs, out):
    by = {o.name: o for o in mesh_objs}
    return {
        "shock_dome": preview("shock_dome", by["fx_shock_dome"], out / "domeGradient.png", (1.0, 0.62, 0.34), (8.5, -8.5, 4.6), (0, 0, 0.7), -0.01),
        "shaft_cone": preview("shaft_cone", by["fx_shaft_cone"], out / "shaftGradient.png", (1.0, 0.9, 0.6), (13.0, -13.0, -2.5), (0, 0, -3.8), -8.0),
        "aura_shell": preview("aura_shell", by["fx_aura_shell"], out / "shellEdge.png", (0.5, 1.0, 0.8), (6.5, -6.5, 2.4), (0, 0, 0.0), -2.05, stand_in=True),
    }


# --------------------------------------------------------------------------- main
FLIPBOOKS = {"flameTongue", "starPop"}
SINGLES = {"domeGradient", "shaftGradient", "shellEdge", "speedStreaks"}


def main():
    opts = parse_args()
    out = (opts["out"] or Path("resources/effects/fx-v2")).resolve()
    meshes_dir = (opts["meshes"] or Path("assets/blender/fx")).resolve()
    scenes = {}
    scenes.update(build_flame(opts))
    scenes.update(build_star(opts))
    scenes.update(build_gradients(opts))
    scenes.update(build_streaks(opts))
    mesh_objs = build_meshes()
    only = opts["only"]
    for name, sc in scenes.items():
        if only and name != only:
            continue
        if name in FLIPBOOKS:
            d = (opts["frames"] / name).resolve()
            d.mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str(d) + "/f_"
            sc.frame_step = opts["step"]
            bpy.ops.render.render(animation=True, scene=name)
        else:
            out.mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str(out / f"{name}.png")
            bpy.ops.render.render(write_still=True, scene=name)
        print("rendered", name)
    if not only or only == "meshes":
        export_meshes(mesh_objs, meshes_dir)
    if opts["shots"] and (not only or only == "meshes"):
        opts["shots"].mkdir(parents=True, exist_ok=True)
        for pname, psc in build_previews(mesh_objs, out).items():
            psc.render.filepath = str((opts["shots"] / f"mesh-{pname}.png").resolve())
            bpy.ops.render.render(write_still=True, scene=psc.name)
            print("preview", pname)
    mesh_scene(mesh_objs)
    if opts["blend"]:
        opts["blend"].parent.mkdir(parents=True, exist_ok=True)
        old = bpy.data.scenes.get("Scene")
        if old is not None and len(bpy.data.scenes) > 1:
            bpy.data.scenes.remove(old)
        bpy.ops.wm.save_as_mainfile(filepath=str(opts["blend"].resolve()), compress=True)
        print("saved", opts["blend"])


main()
