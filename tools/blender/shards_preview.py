"""Render an exploded preview of the egg shards FBX (decision aid). blender -b --factory-startup -P tools/blender/shards_preview.py -- <in.fbx> <out.png>"""
import math
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.fbx(filepath=argv[0])
mat = bpy.data.materials.new("Orange")
mat.use_nodes = True
p = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
p.inputs["Base Color"].default_value = (1, .45, .08, 1)
p.inputs["Roughness"].default_value = .25
for ob in bpy.context.scene.objects:
    if ob.type == "MESH":
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        d = ob.location.copy()
        if d.length > 0:
            ob.location = d * 1.6
        ob.rotation_euler = (d.x * .6, d.y * .6, d.z * .3)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.scene.collection.objects.link(cam)
cam.location = (0, -9, 1.5)
cam.rotation_euler = (math.radians(82), 0, 0)
bpy.context.scene.camera = cam
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
bpy.context.scene.collection.objects.link(sun)
try:
    bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 512
bpy.context.scene.render.filepath = argv[1]
bpy.ops.render.render(write_still=True)
