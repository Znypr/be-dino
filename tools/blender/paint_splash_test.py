"""BD-1212 hatch paint test (owner OK 2026-11-16 'Yes, run it'): thick cartoon paint pours from a bucket and splashes over an egg,
simulated with Blender's liquid (Mantaflow) and rendered to frames. Decision aid: the owner judges the motion before any game art.

    blender -b --factory-startup -P tools/blender/paint_splash_test.py -- <out_dir> [resolution=72] [frames=56]
"""
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "paint-test"
RES = int(argv[1]) if len(argv) > 1 else 72
FRAMES = int(argv[2]) if len(argv) > 2 else 56
os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(OUT, "cache")

scene = bpy.context.scene
for o in list(scene.objects):
    bpy.data.objects.remove(o, do_unlink=True)
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 30


def material(name, rgb, rough=.35, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    try:
        p.inputs["Coat Weight"].default_value = .6
    except KeyError:
        pass
    return m


# egg: a sphere stretched into an egg (wider at the bottom), smooth
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=1, location=(0, 0, 1.25))
egg = bpy.context.active_object
egg.name = "Egg"
for v in egg.data.vertices:
    z = v.co.z
    k = 1.0 - .18 * z  # narrower towards the top
    v.co.x *= .82 * k
    v.co.y *= .82 * k
    v.co.z *= 1.18
bpy.ops.object.shade_smooth()
egg.data.materials.append(material("EggCream", (0.96, 0.92, 0.80), .45))

# bucket: an open cylinder tilted over the egg, upper left (the inflow sits at its mouth)
bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=.42, depth=.62, location=(-1.25, 0, 3.05), rotation=(0, math.radians(-118), 0))
bucket = bpy.context.active_object
bucket.name = "Bucket"
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
# remove the top cap (the face whose normal points along the cylinder's +Z) so it is a pail
top = max(bucket.data.polygons, key=lambda f: f.center.z)
bucket.data.polygons[top.index].select = True
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.delete(type="FACE")
bpy.ops.object.mode_set(mode="OBJECT")
sol = bucket.modifiers.new("Wall", "SOLIDIFY")
sol.thickness = .04
bucket.data.materials.append(material("BucketMetal", (0.78, 0.80, 0.84), .25))

# ground (collision, out of frame)
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# liquid domain around the egg
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.9))
domain = bpy.context.active_object
domain.name = "Domain"
domain.scale = (3.6, 2.4, 3.8)
bpy.ops.object.transform_apply(scale=True)
mod = domain.modifiers.new("Fluid", "FLUID")
mod.fluid_type = "DOMAIN"
ds = mod.domain_settings
ds.domain_type = "LIQUID"
ds.resolution_max = RES
ds.cache_directory = CACHE
ds.cache_type = "ALL"
ds.cache_frame_start, ds.cache_frame_end = 1, FRAMES
ds.use_mesh = True
ds.mesh_scale = 1
ds.use_viscosity = False  # run 1: viscosity 0.03 kept the paint stuck at the bucket mouth
try:
    ds.use_diffusion = True
except Exception:
    pass
ds.mesh_smoothen_pos, ds.mesh_smoothen_neg = 3, 3
for side in ("use_collision_border_bottom", "use_collision_border_front", "use_collision_border_back", "use_collision_border_left", "use_collision_border_right"):
    try:
        setattr(ds, side, False)  # run 2: paint piled up on the walls; now it leaves the domain
    except AttributeError:
        pass
paint = material("Paint", (1.0, 0.36, 0.02), .12)  # run 2 read washed out: deeper, glossier
domain.data.materials.append(paint)

# inflow: a small sphere at the bucket mouth shooting paint at the egg, only for the first ~18 frames
bpy.ops.mesh.primitive_uv_sphere_add(radius=.22, location=(-0.95, 0, 2.85))
inflow = bpy.context.active_object
inflow.name = "Inflow"
fm = inflow.modifiers.new("Fluid", "FLUID")
fm.fluid_type = "FLOW"
fs = fm.flow_settings
fs.flow_type = "LIQUID"
fs.flow_behavior = "INFLOW"
fs.use_initial_velocity = True
fs.velocity_coord = (5.5, 0, -1.5)
fs.use_inflow = True
fs.keyframe_insert("use_inflow", frame=1)
fs.use_inflow = False
fs.keyframe_insert("use_inflow", frame=11)  # run 2: 24 frames flooded the scene
inflow.hide_render = True

for obj in (egg, bucket):  # run 2: no ground, the paint falls away
    em = obj.modifiers.new("Fluid", "FLUID")
    em.fluid_type = "EFFECTOR"
ground.hide_render = True

# bake
bpy.ops.object.select_all(action="DESELECT")
domain.select_set(True)
bpy.context.view_layer.objects.active = domain
print("baking liquid at resolution", RES, "frames", FRAMES, flush=True)
bpy.ops.fluid.bake_all()
print("bake done", flush=True)

# camera + light, transparent film, eevee
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
cam.location = (-0.35, -6.4, 2.1)
cam.rotation_euler = (math.radians(88), 0, 0)
cam.data.lens = 46
scene.camera = cam
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(20))
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("W")
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.75, 0.82, 0.9, 1)
bg.inputs[1].default_value = .9
scene.world = world
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.render.filepath = os.path.join(OUT, "frame_")
bpy.ops.render.render(animation=True)
print("rendered", FRAMES, "frames to", OUT, flush=True)
