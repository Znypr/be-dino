"""Blender preview renders of the raptor tier coat v2 (docs/evidence/2026-10-17-gold/). Headless Blender:

  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b -P tools/blender/render_tier_coat_preview.py -- [obj] [tiers_dir] [out_dir]

Renders the red-and-purple striped raptor (the owner's reference look) with, for each of gold / emerald / diamond, the -v2 colour maps,
the shared crystal normal and the roughness map on an alpha-mapped shell slightly inflated over the stripes (the same "approach C" the
game builds). Gold is metal, Emerald and Diamond are non-metallic crystal with the lower gem roughness. The stripes are PREVIEW ONLY
(procedural, object space); the maps are the deliverable. Also renders "original" (no coat) for comparison, one 3/4 view each plus a side view.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OBJ = ARGS[0] if len(ARGS) > 0 else os.path.join(ROOT, "assets/blender/creatures/lowpoly/raptor.obj")
TIERS_DIR = ARGS[1] if len(ARGS) > 1 else os.path.join(ROOT, "resources/effects/tiers")
OUT = ARGS[2] if len(ARGS) > 2 else os.path.join(ROOT, "docs/evidence/2026-10-17-gold")
PARTS = ("body", "head", "tail", "leftarm", "rightarm", "leftleg", "rightleg")
SHELL = 1.015
RES = (900, 800)


def node(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def stripe_material():
    m = bpy.data.materials.new("stripes")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    bsdf = node(nt, "ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
    coord = node(nt, "ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1, 1, 1)
    sep = node(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
    # stripes across the body: a wave of z and a little y, hard-edged
    madd = node(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    nt.links.new(sep.outputs["Y"], madd.inputs[0])
    madd.inputs[1].default_value = 0.35
    nt.links.new(sep.outputs["Z"], madd.inputs[2])
    mul = node(nt, "ShaderNodeMath", operation="MULTIPLY")
    nt.links.new(madd.outputs[0], mul.inputs[0])
    mul.inputs[1].default_value = 5.0
    sine = node(nt, "ShaderNodeMath", operation="SINE")
    nt.links.new(mul.outputs[0], sine.inputs[0])
    ramp = node(nt, "ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.62, 0.09, 0.07, 1)   # red
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = (0.30, 0.07, 0.42, 1)   # purple
    # remap sine -1..1 to 0..1
    rm = node(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    nt.links.new(sine.outputs[0], rm.inputs[0])
    rm.inputs[1].default_value = 0.5
    rm.inputs[2].default_value = 0.5
    nt.links.new(rm.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def image(path, srgb):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    if srgb:
        im.alpha_mode = "STRAIGHT"
    return im


def shell_material(part, tier):
    m = bpy.data.materials.new("shell_%s_%s" % (part, tier))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    col = node(nt, "ShaderNodeTexImage")
    col.image = image(os.path.join(TIERS_DIR, "raptor-%s-%s-v2-color.png" % (part, tier)), True)
    col.interpolation = "Linear"
    nrm = node(nt, "ShaderNodeTexImage")
    nrm.image = image(os.path.join(TIERS_DIR, "tier-crystal-normal.png"), False)
    rgh = node(nt, "ShaderNodeTexImage")
    rgh.image = image(os.path.join(TIERS_DIR, "tier-crystal-roughness.png" if tier == "gold" else "tier-crystal-roughness-gem.png"), False)
    nmap = node(nt, "ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 1.0
    nt.links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    bsdf = node(nt, "ShaderNodeBsdfPrincipled")
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(rgh.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    if tier == "gold":
        bsdf.inputs["Metallic"].default_value = 1.0
    else:
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["IOR"].default_value = 1.58 if tier == "emerald" else 2.4
        bsdf.inputs["Specular IOR Level"].default_value = 0.8
    clear = node(nt, "ShaderNodeBsdfTransparent")
    mix = node(nt, "ShaderNodeMixShader")
    nt.links.new(col.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(clear.outputs["BSDF"], mix.inputs[1])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    # studio world: soft vertical gradient so the metal and the gems have something to reflect
    w = bpy.data.worlds.new("studio")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputWorld")
    bg = node(nt, "ShaderNodeBackground")
    coord = node(nt, "ShaderNodeTexCoord")
    sep = node(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    ramp = node(nt, "ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.10, 0.11, 0.15, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1.0, 0.99, 0.96, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.1
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    sc.world = w
    for name, loc, energy, size in (("key", (6, -8, 12), 900, 6), ("fill", (-9, -3, 5), 300, 8), ("rim", (-2, 9, 9), 500, 5)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        o = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(o)
        o.location = loc
        d = Vector((0, 0, 0)) - o.location + Vector((0, 0, 4))
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    # floor, matte, so the dino sits somewhere
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    fl = bpy.context.object
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.24, 0.26, 0.31, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    fl.data.materials.append(fm)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 55
    return cam


def aim(cam, loc, target=(0, 0.4, 4.2)):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=OBJ)
    parts = {o.name.replace("_geom", ""): o for o in bpy.data.objects if o.type == "MESH"}
    cam = setup_scene()
    sm = stripe_material()
    shells = {}
    for p in PARTS:
        o = parts[p]
        # the OBJ importer turns Y-up into Blender Z-up on the object transform; the head then faces +Y (world)
        o.data.materials.clear()
        o.data.materials.append(sm)
        for poly in o.data.polygons:
            poly.use_smooth = False
        s = o.copy()
        s.data = o.data.copy()
        bpy.context.scene.collection.objects.link(s)
        s.name = p + "_shell"
        # inflate along the vertex normals (same mesh, slightly larger, like the in-game shell)
        c = sum((v.co for v in s.data.vertices), Vector()) / len(s.data.vertices)
        for v in s.data.vertices:
            v.co = c + (v.co - c) * SHELL
        shells[p] = s
    views = {"threequarter": (-10.5, 12.5, 6.5), "side": (-17.0, 0.4, 4.6)}
    for tier in (None, "gold", "emerald", "diamond"):
        for p in PARTS:
            shells[p].hide_render = tier is None
            if tier:
                s = shells[p]
                s.data.materials.clear()
                s.data.materials.append(shell_material(p, tier))
        for vname, loc in views.items():
            aim(cam, loc)
            bpy.context.scene.render.filepath = os.path.join(OUT, "raptor-%s-%s.png" % (tier or "original", vname))
            bpy.ops.render.render(write_still=True)
            print("rendered", bpy.context.scene.render.filepath)


main()
