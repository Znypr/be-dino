"""Make the 1-cube acceptance model for the Blender -> Roblox pipeline (docs/169, BD-659).

  blender --background --factory-startup --python tools/blender/make_acceptance_cube.py -- build/pipeline-test/cube.blend

A 4-stud cube (origin at its centre, scale 1, rotation 0) with one vertex-colour layer (a different colour per face).
Not game art: it exists only to prove the upload and insert steps work. Delete the result from Place 1 afterwards.
"""
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "cube.blend"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=4.0, location=(0, 0, 2.0))
ob = bpy.context.active_object
ob.name = "AcceptanceCube"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
me = ob.data
attr = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
palette = [(0.9, 0.35, 0.3, 1), (0.95, 0.75, 0.3, 1), (0.5, 0.8, 0.4, 1), (0.35, 0.7, 0.85, 1), (0.6, 0.45, 0.85, 1), (0.9, 0.9, 0.9, 1)]
for poly in me.polygons:
    for li in poly.loop_indices:
        attr.data[li].color = palette[poly.index % len(palette)]
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out)
