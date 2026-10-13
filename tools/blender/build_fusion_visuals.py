"""Build the BD-061 reusable fusion-material prototype and comparison renders.

Run with Blender 5.x:
  blender --background --python tools/blender/build_fusion_visuals.py

The script imports the repository's real Compy and Triceratops OBJ sources,
creates one shared procedural fusion shader group, and saves packed editable
Blender files plus review PNGs. It does not upload or alter Roblox assets.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "blender" / "fusion"
EVIDENCE = ROOT / "docs" / "evidence" / "2026-10-12-bd061-fusion-visuals"
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

TREATMENTS = [
    ("Base", "Base", 0.0),
    ("Gold_Subtle", "Gold", 0.34),
    ("Gold_Medium", "Gold", 0.62),
    ("Emerald_Subtle", "Emerald", 0.34),
    ("Emerald_Medium", "Emerald", 0.62),
    ("Diamond_Subtle", "Diamond", 0.34),
    ("Diamond_Medium", "Diamond", 0.62),
]

TIER = {
    "Base": dict(accent=(0.18, 0.22, 0.20, 1), metallic=0.0, roughness=0.46, facet=0.0, coat=0.15),
    "Gold": dict(accent=(1.0, 0.48, 0.045, 1), metallic=0.88, roughness=0.16, facet=0.15, coat=0.38),
    "Emerald": dict(accent=(0.015, 0.72, 0.22, 1), metallic=0.22, roughness=0.12, facet=0.58, coat=0.55),
    "Diamond": dict(accent=(0.70, 0.94, 1.0, 1), metallic=0.34, roughness=0.075, facet=1.0, coat=0.72),
}

GENETICS = {
    "Compy": dict(primary=(0.025, 0.42, 0.13, 1), secondary=(0.02, 0.22, 0.82, 1), pattern=0.0, pattern_name="Wavy stripes", blend="20/80 green/blue"),
    "Triceratops": dict(primary=(0.82, 0.035, 0.025, 1), secondary=(0.91, 0.68, 0.28, 1), pattern=1.0, pattern_name="Spots", blend="55/45 red/amber"),
}


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for item in list(datablocks):
            datablocks.remove(item)


def socket(node, name):
    return node.inputs.get(name)


def add_group_socket(group, name, in_out, socket_type, default=None, minimum=None, maximum=None):
    s = group.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    if default is not None:
        s.default_value = default
    if minimum is not None:
        s.min_value = minimum
    if maximum is not None:
        s.max_value = maximum
    return s


def create_fusion_group():
    group = bpy.data.node_groups.new("BD061_FusionOverlay_v1", "ShaderNodeTree")
    add_group_socket(group, "Shader", "OUTPUT", "NodeSocketShader")
    add_group_socket(group, "Vector", "INPUT", "NodeSocketVector")
    add_group_socket(group, "Primary", "INPUT", "NodeSocketColor", (0.05, 0.4, 0.12, 1))
    add_group_socket(group, "Secondary", "INPUT", "NodeSocketColor", (0.02, 0.2, 0.8, 1))
    add_group_socket(group, "Accent", "INPUT", "NodeSocketColor", (1.0, 0.5, 0.05, 1))
    add_group_socket(group, "Pattern Kind", "INPUT", "NodeSocketFloat", 0.0, 0.0, 1.0)
    add_group_socket(group, "Intensity", "INPUT", "NodeSocketFloat", 0.35, 0.0, 1.0)
    add_group_socket(group, "Metallic", "INPUT", "NodeSocketFloat", 0.8, 0.0, 1.0)
    add_group_socket(group, "Accent Roughness", "INPUT", "NodeSocketFloat", 0.15, 0.0, 1.0)
    add_group_socket(group, "Facet Strength", "INPUT", "NodeSocketFloat", 0.2, 0.0, 1.0)
    add_group_socket(group, "Coat Weight", "INPUT", "NodeSocketFloat", 0.4, 0.0, 1.0)

    n = group.nodes
    l = group.links
    inp = n.new("NodeGroupInput")
    inp.location = (-1000, 80)
    out = n.new("NodeGroupOutput")
    out.location = (760, 80)

    wave = n.new("ShaderNodeTexWave")
    wave.location = (-760, 320)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 3.4
    wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 4.0
    wave.inputs["Detail Scale"].default_value = 1.8
    l.new(inp.outputs["Vector"], wave.inputs["Vector"])

    spots = n.new("ShaderNodeTexVoronoi")
    spots.location = (-760, 100)
    spots.distance = "EUCLIDEAN"
    spots.feature = "F1"
    spots.inputs["Scale"].default_value = 6.0
    l.new(inp.outputs["Vector"], spots.inputs["Vector"])

    spots_ramp = n.new("ShaderNodeValToRGB")
    spots_ramp.location = (-550, 80)
    spots_ramp.color_ramp.elements[0].position = 0.28
    spots_ramp.color_ramp.elements[1].position = 0.47
    spots_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    spots_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    l.new(spots.outputs["Distance"], spots_ramp.inputs["Fac"])

    pattern_mix = n.new("ShaderNodeMixRGB")
    pattern_mix.location = (-320, 270)
    l.new(inp.outputs["Pattern Kind"], pattern_mix.inputs["Fac"])
    l.new(wave.outputs["Color"], pattern_mix.inputs[1])
    l.new(spots_ramp.outputs["Color"], pattern_mix.inputs[2])

    gene_mix = n.new("ShaderNodeMixRGB")
    gene_mix.location = (-100, 360)
    l.new(pattern_mix.outputs["Color"], gene_mix.inputs["Fac"])
    l.new(inp.outputs["Primary"], gene_mix.inputs[1])
    l.new(inp.outputs["Secondary"], gene_mix.inputs[2])

    noise = n.new("ShaderNodeTexNoise")
    noise.location = (-760, -180)
    noise.noise_dimensions = "3D"
    noise.inputs["Scale"].default_value = 5.6
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.62
    l.new(inp.outputs["Vector"], noise.inputs["Vector"])

    select = n.new("ShaderNodeValToRGB")
    select.location = (-520, -170)
    select.color_ramp.elements[0].position = 0.51
    select.color_ramp.elements[1].position = 0.70
    l.new(noise.outputs["Fac"], select.inputs["Fac"])

    vor = n.new("ShaderNodeTexVoronoi")
    vor.location = (-760, -420)
    vor.distance = "EUCLIDEAN"
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 7.5
    l.new(inp.outputs["Vector"], vor.inputs["Vector"])

    facet_ramp = n.new("ShaderNodeValToRGB")
    facet_ramp.location = (-520, -400)
    facet_ramp.color_ramp.elements[0].position = 0.025
    facet_ramp.color_ramp.elements[1].position = 0.13
    facet_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    facet_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    l.new(vor.outputs["Distance"], facet_ramp.inputs["Fac"])

    facet_mult = n.new("ShaderNodeMath")
    facet_mult.operation = "MULTIPLY"
    facet_mult.location = (-270, -380)
    l.new(facet_ramp.outputs["Color"], facet_mult.inputs[0])
    l.new(inp.outputs["Facet Strength"], facet_mult.inputs[1])

    overlay_add = n.new("ShaderNodeMath")
    overlay_add.operation = "MAXIMUM"
    overlay_add.location = (-70, -150)
    l.new(select.outputs["Color"], overlay_add.inputs[0])
    l.new(facet_mult.outputs[0], overlay_add.inputs[1])

    overlay_amount = n.new("ShaderNodeMath")
    overlay_amount.operation = "MULTIPLY"
    overlay_amount.location = (100, -120)
    l.new(overlay_add.outputs[0], overlay_amount.inputs[0])
    l.new(inp.outputs["Intensity"], overlay_amount.inputs[1])

    accent_mix = n.new("ShaderNodeMixRGB")
    accent_mix.blend_type = "MIX"
    accent_mix.location = (130, 320)
    l.new(overlay_amount.outputs[0], accent_mix.inputs["Fac"])
    l.new(gene_mix.outputs["Color"], accent_mix.inputs[1])
    l.new(inp.outputs["Accent"], accent_mix.inputs[2])

    metal_mult = n.new("ShaderNodeMath")
    metal_mult.operation = "MULTIPLY"
    metal_mult.location = (300, -100)
    l.new(overlay_amount.outputs[0], metal_mult.inputs[0])
    l.new(inp.outputs["Metallic"], metal_mult.inputs[1])

    rough_mix = n.new("ShaderNodeMapRange")
    rough_mix.location = (300, -260)
    rough_mix.inputs["From Min"].default_value = 0.0
    rough_mix.inputs["From Max"].default_value = 1.0
    rough_mix.inputs["To Min"].default_value = 0.48
    l.new(overlay_amount.outputs[0], rough_mix.inputs["Value"])
    l.new(inp.outputs["Accent Roughness"], rough_mix.inputs["To Max"])

    bump = n.new("ShaderNodeBump")
    bump.location = (300, -430)
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.08
    l.new(facet_mult.outputs[0], bump.inputs["Height"])

    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (540, 100)
    l.new(accent_mix.outputs["Color"], socket(bsdf, "Base Color"))
    l.new(metal_mult.outputs[0], socket(bsdf, "Metallic"))
    l.new(rough_mix.outputs["Result"], socket(bsdf, "Roughness"))
    l.new(inp.outputs["Coat Weight"], socket(bsdf, "Coat Weight"))
    l.new(bump.outputs["Normal"], socket(bsdf, "Normal"))
    if socket(bsdf, "Coat Roughness"):
        socket(bsdf, "Coat Roughness").default_value = 0.10
    l.new(bsdf.outputs["BSDF"], out.inputs["Shader"])
    return group


def create_material(group, species, tier, intensity, suffix="Body"):
    genes = GENETICS[species]
    spec = TIER[tier]
    mat = bpy.data.materials.new(f"BD061_{species}_{tier}_{'Base' if intensity == 0 else ('Subtle' if intensity < 0.5 else 'Medium')}_{suffix}")
    mat.use_nodes = True
    mat.diffuse_color = genes["primary"]
    nodes = mat.node_tree.nodes
    nodes.clear()
    tex = nodes.new("ShaderNodeTexCoord")
    tex.location = (-360, 0)
    gn = nodes.new("ShaderNodeGroup")
    gn.node_tree = group
    gn.location = (-80, 0)
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (220, 0)
    mat.node_tree.links.new(tex.outputs["Generated"], gn.inputs["Vector"])
    mat.node_tree.links.new(gn.outputs["Shader"], out.inputs["Surface"])
    primary = list(genes["primary"])
    secondary = list(genes["secondary"])
    if suffix == "Detail":
        primary = [min(1.0, c * 1.25) for c in primary[:3]] + [1]
        secondary = [min(1.0, c * 1.18) for c in secondary[:3]] + [1]
    gn.inputs["Primary"].default_value = primary
    gn.inputs["Secondary"].default_value = secondary
    gn.inputs["Accent"].default_value = spec["accent"]
    gn.inputs["Pattern Kind"].default_value = genes["pattern"]
    gn.inputs["Intensity"].default_value = intensity
    gn.inputs["Metallic"].default_value = spec["metallic"]
    gn.inputs["Accent Roughness"].default_value = spec["roughness"]
    gn.inputs["Facet Strength"].default_value = spec["facet"]
    gn.inputs["Coat Weight"].default_value = spec["coat"]
    return mat


def import_species(species):
    path = ROOT / "resources" / "models" / f"{species.lower()}.obj"
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path))
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"OBJ import produced no mesh: {path}")
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = meshes[0]
    obj.name = f"SOURCE_{species}"
    obj.data.name = f"SOURCE_{species}_Mesh"
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def apply_treatment(obj, species, tier, intensity, group):
    body = create_material(group, species, tier, intensity, "Body")
    detail = create_material(group, species, tier, min(1.0, intensity * 1.15), "Detail")
    fixed = {}
    for index, old in enumerate(list(obj.data.materials)):
        name = old.name.upper() if old else ""
        # Preserve original eye whites/pupils. The other slots are anatomy and
        # receive the same gene shader, with lighter detail on belly/horns.
        if name in {"M142E35", "MFFFFFF"}:
            fixed[index] = old
        elif name in {"MF0E3BF", "MFCF4D9"}:
            fixed[index] = detail
        else:
            fixed[index] = body
    obj.data.materials.clear()
    for index in range(max(fixed) + 1):
        obj.data.materials.append(fixed[index])


def duplicate_source(source, name):
    obj = source.copy()
    obj.data = source.data.copy()
    obj.animation_data_clear()
    obj.name = name
    bpy.context.collection.objects.link(obj)
    obj.hide_render = False
    obj.hide_viewport = False
    obj.hide_set(False)
    return obj


def bounds_world(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


def ground_object(obj):
    minimum = min(v.z for v in bounds_world(obj))
    obj.location.z -= minimum


def add_crystal_accents(obj, tier, intensity):
    if tier == "Base" or intensity < 0.5:
        return []
    spec = TIER[tier]
    b = bounds_world(obj)
    minx, maxx = min(v.x for v in b), max(v.x for v in b)
    miny, maxy = min(v.y for v in b), max(v.y for v in b)
    minz, maxz = min(v.z for v in b), max(v.z for v in b)
    size = max(maxx - minx, maxy - miny, maxz - minz)
    positions = [
        (minx + (maxx-minx)*0.50, miny + (maxy-miny)*0.52, minz + (maxz-minz)*0.82),
        (minx + (maxx-minx)*0.50, miny + (maxy-miny)*0.66, minz + (maxz-minz)*0.72),
        (minx + (maxx-minx)*0.50, miny + (maxy-miny)*0.38, minz + (maxz-minz)*0.70),
    ]
    mat = bpy.data.materials.get(f"BD061_{tier}_AccentMesh")
    if mat is None:
        mat = bpy.data.materials.new(f"BD061_{tier}_AccentMesh")
        mat.use_nodes = True
        p = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        p.inputs["Base Color"].default_value = spec["accent"]
        p.inputs["Metallic"].default_value = spec["metallic"]
        p.inputs["Roughness"].default_value = spec["roughness"]
        p.inputs["Coat Weight"].default_value = spec["coat"]
    made = []
    for i, pos in enumerate(positions):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size * (0.025 + i * 0.002), location=pos)
        crystal = bpy.context.object
        crystal.name = f"{obj.name}_Accent_{i+1}"
        crystal.scale.z = 2.2
        crystal.data.materials.append(mat)
        made.append(crystal)
    # Export the three details as one accessory mesh. This keeps Medium at one
    # optional extra MeshPart/draw call rather than three, while retaining 60
    # triangles total (3 x 20-triangle icospheres).
    bpy.ops.object.select_all(action="DESELECT")
    for crystal in made:
        crystal.select_set(True)
    bpy.context.view_layer.objects.active = made[0]
    bpy.ops.object.join()
    combined = made[0]
    combined.name = f"{obj.name}_AccentMesh"
    combined.parent = obj
    combined.matrix_parent_inverse = obj.matrix_world.inverted()
    return [combined]


def add_text(text, location, size=0.48, color=(0.82, 0.9, 0.82, 1), align="CENTER"):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.data.body = text
    obj.data.align_x = align
    obj.data.size = size
    obj.data.extrude = 0.008
    mat = bpy.data.materials.get("BD061_Label")
    if mat is None:
        mat = bpy.data.materials.new("BD061_Label")
        mat.diffuse_color = color
        mat.use_nodes = True
        p = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        p.inputs["Base Color"].default_value = color
        p.inputs["Emission Color"].default_value = tuple(color[:3]) + (1,)
        p.inputs["Emission Strength"].default_value = 0.15
        p.inputs["Roughness"].default_value = 0.5
    obj.data.materials.append(mat)
    return obj


def add_floor():
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.03))
    floor = bpy.context.object
    floor.name = "Review Floor"
    mat = bpy.data.materials.new("BD061_Floor")
    mat.use_nodes = True
    p = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (0.018, 0.028, 0.024, 1)
    p.inputs["Roughness"].default_value = 0.32
    floor.data.materials.append(mat)


def add_camera(name, location, target, ortho_scale):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(cam)
    cam.location = location
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    data.type = "ORTHO"
    data.ortho_scale = ortho_scale
    return cam


def setup_world():
    world = bpy.data.worlds.new("BD061 Review World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.012, 0.02, 0.016, 1)
    bg.inputs["Strength"].default_value = 0.38
    for name, loc, energy, size, color in [
        ("Key", (-7, -10, 12), 1600, 7.0, (1.0, 0.79, 0.58)),
        ("Fill", (9, -2, 8), 1200, 6.0, (0.45, 0.77, 1.0)),
        ("Rim", (0, 9, 10), 1850, 5.0, (0.45, 1.0, 0.72)),
        ("Front", (0, -16, 10), 1050, 15.0, (0.72, 0.86, 1.0)),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = loc
        light.rotation_euler = (Vector((0, 0, 2.0)) - light.location).to_track_quat("-Z", "Y").to_euler()


def setup_render(width=2400, height=1200, samples=48):
    scene = bpy.context.scene
    # Blender 5.1 reports the Eevee identifier as BLENDER_EEVEE; older 4.x
    # builds may expose BLENDER_EEVEE_NEXT instead.
    engines = {item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_percentage = 100
    scene.render.image_settings.compression = 28
    scene.render.fps = 24
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.filepath = str(EVIDENCE / "bd061-fusion-side-by-side.png")
    # Blender 5 Eevee sampling location can change; set only when present.
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples


def build_comparison(group, sources):
    spacing_x = 4.9
    y_rows = {"Compy": 2.7, "Triceratops": -3.1}
    rows = {"Compy": [], "Triceratops": []}
    for species, y in y_rows.items():
        source = sources[species]
        for col, (label, tier, intensity) in enumerate(TREATMENTS):
            obj = duplicate_source(source, f"{species}_{label}")
            obj.location = ((col - 3) * spacing_x, y, 0)
            obj.rotation_euler[2] = math.radians(-12)
            # The legacy six-species OBJ sources are authored much larger than
            # the newer FBX candidates; normalize them for a seven-column plate.
            scale = 0.68 if species == "Compy" else 0.55
            obj.scale = (scale, scale, scale)
            bpy.context.view_layer.update()
            ground_object(obj)
            apply_treatment(obj, species, tier, intensity, group)
            accents = add_crystal_accents(obj, tier, intensity)
            rows[species].extend([obj, *accents])
            rows[species].append(add_text(label.replace("_", "\n"), (obj.location.x, y - 2.0, 0.32), size=0.34))
        genes = GENETICS[species]
        rows[species].append(add_text(f"{species} — {genes['pattern_name']} — {genes['blend']}", (-16.4, y + 0.2, 5.8), size=0.43, align="LEFT"))
    title = add_text("BD-061  •  SAME GENETICS  •  BASE → GOLD → EMERALD → DIAMOND", (0, 0, 7.0), size=0.52)
    return rows, title


def add_effect_material(name, color, emission=2.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = color
    p.inputs["Emission Color"].default_value = color
    p.inputs["Emission Strength"].default_value = emission
    p.inputs["Roughness"].default_value = 0.22
    p.inputs["Alpha"].default_value = alpha
    return mat


def effect_orbit(center, radius, mat, name, tilt=0.0):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.035
    curve.bevel_resolution = 2
    spline = curve.splines.new("NURBS")
    spline.points.add(15)
    for i, p in enumerate(spline.points):
        a = 2 * math.pi * i / 15
        p.co = (center.x + math.cos(a) * radius, center.y + math.sin(a) * radius * 0.42, center.z + math.sin(a * 2) * 0.14 + tilt, 1)
    spline.use_cyclic_u = True
    spline.order_u = 3
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    curve.materials.append(mat)
    return obj


def build_stack_scene(group, sources):
    # Hide the comparison objects and create four isolated combinations. Each
    # layer is in its own collection so artists can toggle it independently.
    for obj in list(bpy.context.scene.objects):
        if obj.type not in {"CAMERA", "LIGHT"} and obj.name != "Review Floor":
            obj.hide_render = True
    stage = bpy.data.collections.new("STACK TESTS — toggle child collections")
    bpy.context.scene.collection.children.link(stage)
    labels = [
        ("Gold Medium\nBIG + Shiny", "Compy", "Gold", 0.62, 1.2),
        ("Emerald Medium\nFrost mutation", "Triceratops", "Emerald", 0.62, 1.0),
        ("Diamond Medium\nAura separate", "Compy", "Diamond", 0.62, 1.0),
        ("Diamond Subtle\nTrail separate", "Triceratops", "Diamond", 0.34, 1.0),
    ]
    x_positions = [-7.3, -2.45, 2.45, 7.3]
    warm = add_effect_material("FX_Shiny", (1.0, 0.84, 0.32, 1), 4.0)
    frost = add_effect_material("FX_Frost", (0.18, 0.68, 1.0, 1), 3.0)
    aura = add_effect_material("FX_Aura", (0.12, 1.0, 0.46, 1), 2.5)
    trail = add_effect_material("FX_Trail", (0.66, 0.26, 1.0, 1), 2.8)
    for idx, (label, species, tier, intensity, scale_boost) in enumerate(labels):
        obj = duplicate_source(sources[species], f"Stack_{species}_{idx+1}")
        obj.hide_render = False
        obj.location = (x_positions[idx], 0, 0)
        s = (0.42 if species == "Compy" else 0.35) * scale_boost
        obj.scale = (s, s, s)
        obj.rotation_euler[2] = math.radians(-12)
        bpy.context.view_layer.update()
        ground_object(obj)
        apply_treatment(obj, species, tier, intensity, group)
        for a in add_crystal_accents(obj, tier, intensity):
            a.hide_render = False
        b = bounds_world(obj)
        center = sum(b, Vector()) / 8
        width = max(max(v.x for v in b) - min(v.x for v in b), 1.0)
        height = max(v.z for v in b) - min(v.z for v in b)
        if idx == 0:  # Shiny: four sparse, static glints for layer readability.
            for j, offset in enumerate(((-.25, .15, .72), (.22, -.12, .58), (.1, .2, .9), (-.18, -.15, .4))):
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.075 * scale_boost, location=(center.x + offset[0]*width, center.y + offset[1]*width, min(v.z for v in b)+offset[2]*height))
                glint = bpy.context.object
                glint.name = f"Shiny_Layer_{j+1}"
                glint.data.materials.append(warm)
        elif idx == 1:  # Event mutation layer, represented as separate icy crystals/wisps.
            for j in range(5):
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.07 + 0.015*j, location=(center.x + math.cos(j*1.25)*width*.55, center.y + math.sin(j*1.25)*width*.28, min(v.z for v in b)+height*(.25+.12*j)))
                fx = bpy.context.object
                fx.name = f"Frost_Mutation_Layer_{j+1}"
                fx.scale.z = 2.4
                fx.data.materials.append(frost)
        elif idx == 2:
            effect_orbit(center, width * 0.72, aura, "Aura_Layer_Orbit")
        else:
            for j in range(3):
                curve = bpy.data.curves.new(f"Trail_Layer_{j+1}", "CURVE")
                curve.dimensions = "3D"
                curve.bevel_depth = 0.028
                curve.bevel_resolution = 2
                sp = curve.splines.new("BEZIER")
                sp.bezier_points.add(2)
                for k, p in enumerate(sp.bezier_points):
                    p.co = (min(v.x for v in b)-k*1.25-j*.14, center.y+(j-1)*.18, min(v.z for v in b)+height*(.25+j*.12))
                    p.handle_left_type = p.handle_right_type = "AUTO"
                o = bpy.data.objects.new(f"Trail_Layer_{j+1}", curve)
                bpy.context.collection.objects.link(o)
                curve.materials.append(trail)
        txt = add_text(label, (x_positions[idx], -2.25, 0.02), size=0.34)
        txt.hide_render = False
    title = add_text("STACK TESTS  •  FUSION SURFACE + OPTIONAL INDEPENDENT LAYERS", (0, 0, 6.2), size=0.43)
    title.hide_render = False


def write_manifest(sources):
    metrics = {}
    for species, obj in sources.items():
        metrics[species] = {
            "source": f"resources/models/{species.lower()}.obj",
            "triangles": sum(len(p.vertices) - 2 for p in obj.data.polygons),
            "vertices": len(obj.data.vertices),
            "material_slots": len(obj.data.materials),
            "genetics": GENETICS[species],
        }
    manifest = {
        "task": "BD-061",
        "status": "Blender prototype; Roblox Studio and physical-device verification pending",
        "source_models": metrics,
        "treatments": [name for name, _, _ in TREATMENTS if name != "Base"],
        "shared_node_group": "BD061_FusionOverlay_v1",
        "medium_accessories": {
            "detail_count": 3,
            "mesh_objects_per_model": 1,
            "triangles_total": 60,
            "source": "three joined icospheres, subdivision 1",
        },
        "render_layers": ["fusion surface", "BIG scale", "Shiny", "event mutation", "aura", "trail"],
        "roblox_note": "Bake stage masks to Color/Metalness/Roughness/Normal maps or use authored SurfaceAppearance templates; preserve runtime gene ColorMap and keep cosmetic particles separate.",
    }
    (OUT / "bd061-fusion-material-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main():
    clear_scene()
    setup_world()
    setup_render()
    add_floor()
    group = create_fusion_group()
    sources = {name: import_species(name) for name in GENETICS}
    for source in sources.values():
        source.hide_render = True
        source.hide_viewport = True
    rows, comparison_title = build_comparison(group, sources)
    cam = add_camera("Comparison Camera", (0, -30, 11), (0, 0.3, 1.7), 20.5)
    bpy.context.scene.camera = cam
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "BD061_FusionVisualPrototype.blend"))
    # Produce two clean, identical-camera comparison rows. They are easier to
    # review than a crowded 14-model contact sheet while retaining the same
    # lighting, camera, genetics and tier order.
    bpy.context.scene.render.resolution_x = 2400
    bpy.context.scene.render.resolution_y = 900
    # Blender's orthographic scale is the camera width for this landscape
    # framing, so include all seven columns plus silhouette breathing room.
    cam.data.ortho_scale = 36.0
    for species, y in (("Compy", 2.7), ("Triceratops", -3.1)):
        for row_species, objects in rows.items():
            for obj in objects:
                obj.hide_render = row_species != species
        comparison_title.hide_render = False
        cam.location = (0, -30, 8.2)
        cam.rotation_euler = (Vector((0, y, 2.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.render.filepath = str(EVIDENCE / f"bd061-{species.lower()}-side-by-side.png")
        bpy.ops.render.render(write_still=True)

    # Stack-test render lives in the same editable master as a second authored
    # scene state, then is saved separately for convenient inspection.
    build_stack_scene(group, sources)
    cam.location = (0, -27, 8.8)
    cam.rotation_euler = (Vector((0, 0, 1.6)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = 20.0
    bpy.context.scene.render.resolution_x = 2200
    bpy.context.scene.render.resolution_y = 900
    bpy.context.scene.render.filepath = str(EVIDENCE / "bd061-stack-tests.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "BD061_FusionStackTests.blend"))
    bpy.ops.render.render(write_still=True)

    # Save a compact material library with only shader-bearing datablocks and
    # preview geometry. This remains editable and appendable in Blender.
    library_path = OUT / "BD061_FusionMaterialLibrary.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(library_path))
    write_manifest(sources)
    print(json.dumps({
        "prototype": str(OUT / "BD061_FusionVisualPrototype.blend"),
        "stack_tests": str(OUT / "BD061_FusionStackTests.blend"),
        "library": str(library_path),
        "compy_side_by_side": str(EVIDENCE / "bd061-compy-side-by-side.png"),
        "triceratops_side_by_side": str(EVIDENCE / "bd061-triceratops-side-by-side.png"),
        "stack_render": str(EVIDENCE / "bd061-stack-tests.png"),
    }, indent=2))


if __name__ == "__main__":
    main()
