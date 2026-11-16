"""BD-1212 3D egg break (owner 2026-11-16 'Yes, 3D shards'): an egg shell cut into ~10 chunky jagged shards with real thickness, exported
as one FBX (one mesh per shard, origin at each shard's centre so it can spin in place). Headless, a few seconds.

    blender -b --factory-startup -P tools/blender/egg_shards.py -- <out.fbx> [pieces=10] [seed=7]
"""
import math
import random
import sys

import bmesh
import bpy
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "egg_shards.fbx"
PIECES = int(argv[1]) if len(argv) > 1 else 10
SEED = int(argv[2]) if len(argv) > 2 else 7
random.seed(SEED)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# egg: a dense icosphere pulled into an egg (wider at the bottom), 2.4 units tall like the game egg
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1)
egg = bpy.context.active_object
for v in egg.data.vertices:
    z = v.co.z
    k = 1.0 - .16 * z
    v.co.x *= .84 * k
    v.co.y *= .84 * k
    v.co.z *= 1.2
egg.scale = (1, 1, 1)

# seeds spread over the shell (fibonacci sphere + jitter) so every shard is a similar size
seeds = []
for i in range(PIECES):
    y = 1 - 2 * (i + .5) / PIECES
    r = math.sqrt(1 - y * y)
    t = i * math.pi * (3 - math.sqrt(5)) + random.uniform(-.3, .3)
    seeds.append(Vector((math.cos(t) * r * .84, math.sin(t) * r * .84, y * 1.2)))

# each face goes to its nearest seed; noise on the distance makes the crack lines jagged instead of straight
bm = bmesh.new()
bm.from_mesh(egg.data)
groups = {i: [] for i in range(PIECES)}
for f in bm.faces:
    c = f.calc_center_median()
    best, bd = 0, 1e9
    for i, sd in enumerate(seeds):
        d = (c - sd).length + .12 * noise.noise(c * 3.1 + Vector((i * 1.7, 0, 0)))
        if d < bd:
            best, bd = i, d
    groups[best].append(f)

mat = bpy.data.materials.new("Shell")
mat.use_nodes = True
pieces = []
for i, faces in groups.items():
    if len(faces) < 3:
        continue
    nbm = bmesh.new()
    vmap = {}
    for f in faces:
        verts = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = nbm.verts.new(v.co)
            verts.append(vmap[v])
        nbm.faces.new(verts)
    me = bpy.data.meshes.new(f"Shard{i + 1:02d}")
    nbm.to_mesh(me)
    nbm.free()
    ob = bpy.data.objects.new(f"Shard{i + 1:02d}", me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    # shell thickness, inwards
    sol = ob.modifiers.new("Shell", "SOLIDIFY")
    sol.thickness = .09
    sol.offset = -1
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier="Shell")
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    ob.select_set(False)
    pieces.append(ob)
bm.free()
bpy.data.objects.remove(egg, do_unlink=True)

for ob in pieces:
    ob.select_set(True)
bpy.ops.object.shade_smooth()  # with a 3-level ico egg the crack edges are bold zigzags
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, apply_scale_options="FBX_SCALE_ALL", object_types={"MESH"}, mesh_smooth_type="FACE")
print("exported", len(pieces), "shards to", OUT, flush=True)
