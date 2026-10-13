"""Revision 2: glossy, geometry-free fusion finishes in a daylight clearing.

Run in Blender: --background --python tools/blender/build_fusion_finish.py
"""
import importlib.util
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('foundation', HERE / 'build_fusion_visuals.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
OUT = base.OUT
EVIDENCE = base.EVIDENCE


def material(name, color, roughness=0.8):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    return mat


def environment():
    world = bpy.data.worlds.new('Daylight clearing')
    world.use_nodes = True
    bpy.context.scene.world = world
    sky = world.node_tree.nodes.new('ShaderNodeTexSky')
    types = {i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items}
    sky.sky_type = 'NISHITA' if 'NISHITA' in types else 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(42)
    sky.sun_rotation = math.radians(135)
    world.node_tree.links.new(sky.outputs['Color'], world.node_tree.nodes.get('Background').inputs['Color'])
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value = 0.06
    sun = bpy.data.lights.new('Afternoon sunlight', 'SUN')
    sun.energy = 1.5
    sun.angle = math.radians(12)
    obj = bpy.data.objects.new('Afternoon sunlight', sun)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (0.45, -0.6, -0.6)
    grass = material('Clearing grass', (0.16, 0.28, 0.055))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.025))
    bpy.context.object.name = 'Environment Grass'
    bpy.context.object.data.materials.append(grass)
    stone = material('Warm grey rocks', (0.24, 0.29, 0.25))
    leaves = material('Forest canopy', (0.05, 0.19, 0.075))
    bark = material('Tree bark', (0.17, 0.08, 0.035))
    for i, (x, y) in enumerate([(-6, -8), (-2, -11), (3, -10), (7, -8), (-8, -3)]):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.3, depth=4, location=(x, y, 2))
        bpy.context.object.data.materials.append(bark)
        for z, radius in [(3.4, 1.6), (4.5, 1.3), (5.3, 0.85)]:
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=(x, y, z))
            bpy.context.object.data.materials.append(leaves)
    for x, y, r in [(-4, -5, 0.8), (4, -6, 1.1), (-6, -1, 0.6), (7, -3, 0.7)]:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=(x, y, r * .45))
        bpy.context.object.scale = (1.4, 1, .65)
        bpy.context.object.data.materials.append(stone)


def finish_group():
    group = base.create_fusion_group()
    group.name = 'BD061_FusionFinish_v2'
    inp = next(n for n in group.nodes if n.type == 'GROUP_INPUT')
    p = next(n for n in group.nodes if n.type == 'BSDF_PRINCIPLED')
    mix = next(n for n in group.nodes if n.type == 'MIX_RGB' and n.location.x == 130)
    # Uniform translucent tint and continuous clearcoat: no mineral lattice,
    # surface relief, attached geometry or replacement of the genetic pattern.
    for input_socket in [mix.inputs[0], p.inputs['Metallic'], p.inputs['Roughness'], p.inputs['Normal']]:
        for link in list(input_socket.links):
            group.links.remove(link)
    tint = group.nodes.new('ShaderNodeMath')
    tint.operation = 'MULTIPLY'
    tint.inputs[1].default_value = .30
    group.links.new(inp.outputs['Intensity'], tint.inputs[0])
    group.links.new(tint.outputs[0], mix.inputs[0])
    group.links.new(inp.outputs['Metallic'], p.inputs['Metallic'])
    group.links.new(inp.outputs['Accent Roughness'], p.inputs['Roughness'])
    p.inputs['Coat Roughness'].default_value = .08
    # Remove disconnected experimental noise/facet nodes from the reusable group.
    needed = {p}
    def collect(node):
        for s in node.inputs:
            for link in s.links:
                if link.from_node not in needed:
                    needed.add(link.from_node)
                    collect(link.from_node)
    collect(p)
    needed.add(next(n for n in group.nodes if n.type == 'GROUP_OUTPUT'))
    for node in list(group.nodes):
        if node not in needed:
            group.nodes.remove(node)
    return group


def apply(obj, species, tier, intensity, group):
    base.apply_treatment(obj, species, tier, intensity, group)
    for mat in obj.data.materials:
        if not mat.use_nodes:
            continue
        gn = next((n for n in mat.node_tree.nodes if n.type == 'GROUP'), None)
        if gn is None:
            continue
        gn.inputs['Intensity'].default_value = intensity
        gn.inputs['Metallic'].default_value = (0 if tier == 'Base' else {'Gold': .28, 'Emerald': .08, 'Diamond': .04}[tier] * (1 if intensity > .5 else .5))
        gn.inputs['Accent Roughness'].default_value = .55 if tier == 'Base' else (.16 if intensity < .5 else .095)
        gn.inputs['Coat Weight'].default_value = 0 if tier == 'Base' else (.65 if intensity < .5 else 1.0)
        gn.inputs['Facet Strength'].default_value = 0


def label(camera, text):
    bpy.ops.object.text_add()
    obj = bpy.context.object
    obj.name = 'Panel caption'
    obj.data.body = text
    obj.data.size = .25
    obj.data.align_x = 'CENTER'
    obj.rotation_euler = camera.rotation_euler
    obj.location = camera.matrix_world @ Vector((0, -2.9, -8))
    mat = material('Caption ink', (.01, .025, .02))
    obj.data.materials.append(mat)
    return obj


def montage(paths, target):
    # Compose rendered pixels inside Blender, retaining linear-to-display conversion.
    result = np.ones((1280, 2560, 4), dtype=np.float32)
    result[:, :, :3] = .08
    for i, path in enumerate(paths):
        img = bpy.data.images.load(str(path), check_existing=False)
        pixels = np.empty(640 * 640 * 4, dtype=np.float32)
        img.pixels.foreach_get(pixels)
        row, col = divmod(i, 4)
        result[(1-row)*640:(2-row)*640, col*640:(col+1)*640] = pixels.reshape(640, 640, 4)
        bpy.data.images.remove(img)
    img = bpy.data.images.new('Comparison board', width=2560, height=1280)
    img.pixels.foreach_set(result.ravel())
    img.filepath_raw = str(target)
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def main():
    base.clear_scene()
    bpy.context.preferences.filepaths.save_version = 0
    base.setup_render(640, 640)
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 24
    bpy.context.scene.cycles.use_denoising = True
    bpy.context.scene.view_settings.look = 'AgX - Medium High Contrast'
    bpy.context.scene.view_settings.exposure = -0.8
    environment()
    group = finish_group()
    sources = {s: base.import_species(s) for s in base.GENETICS}
    for source in sources.values():
        source.hide_render = True
        source.hide_viewport = True
    camera = base.add_camera('Game view camera', (9, 12, 5.6), (0, .4, 1.8), 6.8)
    bpy.context.scene.camera = camera
    all_variants = []
    for species in sources:
        paths = []
        for name, tier, intensity in base.TREATMENTS:
            obj = base.duplicate_source(sources[species], species + '_' + name)
            obj.scale = (.72,)*3
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
            bpy.context.view_layer.update()
            base.ground_object(obj)
            apply(obj, species, tier, intensity, group)
            caption = label(camera, name.replace('_', ' '))
            path = EVIDENCE / f'v2-{species.lower()}-{name.lower()}.png'
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
            obj.hide_render = True
            caption.hide_render = True
            all_variants.append(obj)
        # Eighth panel repeats Base for direct comparison at the right edge.
        paths.append(paths[0])
        montage(paths, EVIDENCE / f'bd061-{species.lower()}-daylight-finish.png')
    all_variants[0].hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'BD061_FusionFinish_Daylight_v2.blend'))
    bpy.data.libraries.write(str(OUT / 'BD061_FusionFinish_Library_v2.blend'), set([group] + [m for m in bpy.data.materials if m.name.startswith('BD061_')]), fake_user=True)
    assert not any('AccentMesh' in o.name for o in bpy.data.objects)
    (OUT / 'fusion-finish-v2-manifest.json').write_text(json.dumps({'revision': 2, 'working_name': 'Fusion finish', 'additional_triangles': 0, 'additional_meshes': 0, 'fusion_particles': 0, 'node_group': group.name, 'comparison': 'fixed camera, pose, environment and genetics; daylight grass clearing', 'genetics_note': 'Procedural review patterns; stored color shares are fixture labels, not calibrated UV coverage.'}, indent=2))
    print('FINISH_V2_COMPLETE: six coating-only finishes, zero accessory meshes')


if __name__ == '__main__':
    main()
