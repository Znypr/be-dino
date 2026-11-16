"""BD-1212 full-screen hatch: render the sunburst rays picture in Blender (headless). White soft rays on transparency, 1024 x 1024 RGBA;
the game tints it per rarity (ImageColor3) and turns it slowly.

    blender -b --factory-startup -P tools/blender/render_hatch_rays.py -- <out.png> [rays=18]
"""
import math
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "hatch-rays.png"
RAYS = int(argv[1]) if len(argv) > 1 else 18

scene = bpy.context.scene
for o in list(scene.objects):
    bpy.data.objects.remove(o, do_unlink=True)
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"

bpy.ops.mesh.primitive_plane_add(size=2)
plane = bpy.context.active_object
mat = bpy.data.materials.new("Rays")
mat.use_nodes = True
try:
    mat.blend_method = "BLEND"
except Exception:
    pass
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new("ShaderNodeOutputMaterial")
tex = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
# object coords: x, y in [-1, 1]; angle = atan2(y, x); radius = length
atan = nt.nodes.new("ShaderNodeMath"); atan.operation = "ARCTAN2"
mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = RAYS
sine = nt.nodes.new("ShaderNodeMath"); sine.operation = "SINE"
# soft stripes: (sin * 0.5 + 0.5) ^ 3 gives tapered bright rays with soft edges
half = nt.nodes.new("ShaderNodeMath"); half.operation = "MULTIPLY_ADD"; half.inputs[1].default_value = .5; half.inputs[2].default_value = .5
pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 0.9
length = nt.nodes.new("ShaderNodeVectorMath"); length.operation = "LENGTH"
# radial fade: bright near the centre, gone at the edge (1 - r) ^ 1.4, plus a hole-free centre
fade = nt.nodes.new("ShaderNodeMath"); fade.operation = "SUBTRACT"; fade.inputs[0].default_value = 1.0; fade.use_clamp = True
fadep = nt.nodes.new("ShaderNodeMath"); fadep.operation = "POWER"; fadep.inputs[1].default_value = 0.8
alpha = nt.nodes.new("ShaderNodeMath"); alpha.operation = "MULTIPLY"; alpha.use_clamp = True
emit = nt.nodes.new("ShaderNodeEmission"); emit.inputs[0].default_value = (1, 1, 1, 1)
transp = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader")
L = nt.links.new
L(tex.outputs["Object"], sep.inputs[0])
L(sep.outputs["Y"], atan.inputs[0]); L(sep.outputs["X"], atan.inputs[1])
L(atan.outputs[0], mul.inputs[0]); L(mul.outputs[0], sine.inputs[0])
L(sine.outputs[0], half.inputs[0]); L(half.outputs[0], pw.inputs[0])
L(tex.outputs["Object"], length.inputs[0]); L(length.outputs["Value"], fade.inputs[1]); L(fade.outputs[0], fadep.inputs[0])
L(pw.outputs[0], alpha.inputs[0]); L(fadep.outputs[0], alpha.inputs[1])
L(alpha.outputs[0], mix.inputs[0]); L(transp.outputs[0], mix.inputs[1]); L(emit.outputs[0], mix.inputs[2])
L(mix.outputs[0], out.inputs[0])
plane.data.materials.append(mat)

cam_data = bpy.data.cameras.new("Cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 2.0
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
cam.location = (0, 0, 3)
scene.camera = cam
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT, RAYS, "rays")
