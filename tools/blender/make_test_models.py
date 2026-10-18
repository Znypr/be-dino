"""Test fixtures for tools/check_model_for_roblox.py (BD-642, docs/163). Run it in a headless Blender (never the live MCP session):

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python tools/blender/make_test_models.py -- OUTDIR

Writes one small .blend per case into OUTDIR (all use bottom-centre pivots and 1 unit = 1 stud unless the case breaks that):
  good.blend       one closed, UV-mapped, textured-material box on the ground, about Compy size: everything passes
  flipped.blend    the same box turned inside out
  scaled.blend     object scale 2 and a 30 degree turn left on the object (not applied)
  ngon.blend       a face with 6 corners
  loose.blend      a stray vertex that belongs to no face
  doubles.blend    vertices doubled in place
  nomat.blend      no material at all
  emptyslot.blend  a material slot with nothing in it
  uvoverlap.blend  every face on the same UV spot
  nouv.blend       no UV map
  names.blend      names "Leg", "Leg.001" (a renamed duplicate), "my part" (not usable as part.Name) and a 120 character name
  heavy.blend      a sphere with more than 21,844 triangles
  huge.blend       a box 3000 studs wide
  centre.blend     pivot in the middle of the body, not at the feet
  rigged.blend     the good box with a 2-bone armature, bone weights, and a 2-frame action
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    return ob


def material(name='Body'):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (0.8, 0.4, 0.2, 1)
    return m


def box_mesh(name, w=3.5, d=7.7, h=6.6, bottom=True, uv=True):
    """A closed box w (X) x d (Y) x h (Z) with its pivot at the bottom centre (or the centre)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= d
        v.co.z = (v.co.z + (0.5 if bottom else 0.0)) * h
    if uv:
        uvl = bm.loops.layers.uv.new('UVMap')
        faces = list(bm.faces)
        for i, f in enumerate(faces):
            cx, cy = (i % 3) / 3.0, (i // 3) / 2.0
            for k, loop in enumerate(f.loops):
                loop[uvl].uv = (cx + 0.02 + 0.28 * (k in (1, 2)), cy + 0.02 + 0.46 * (k in (2, 3)))
    bm.to_mesh(me)
    bm.free()
    return me


def add_box(name, **kw):
    me = box_mesh(name, **kw)
    ob = link(bpy.data.objects.new(name, me))
    ob.data.materials.append(material())
    return ob


def save(outdir, name):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, name + '.blend'))


def main():
    outdir = sys.argv[sys.argv.index('--') + 1]
    os.makedirs(outdir, exist_ok=True)

    fresh(); add_box('Body'); save(outdir, 'good')

    fresh(); ob = add_box('Body')
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
    save(outdir, 'flipped')

    fresh(); ob = add_box('Body'); ob.scale = (2, 2, 2); ob.rotation_euler = (0, 0, math.radians(30)); save(outdir, 'scaled')

    fresh()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=1.5, radius2=1.5, depth=3)
    for v in bm.verts:
        v.co.z += 1.5
    me = bpy.data.meshes.new('Body'); bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new('Body', me)); ob.data.materials.append(material()); me.uv_layers.new(name='UVMap')
    save(outdir, 'ngon')

    fresh(); ob = add_box('Body')
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.new((9, 9, 9)); bm.to_mesh(ob.data); bm.free(); save(outdir, 'loose')

    fresh(); ob = add_box('Body')
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for v in list(bm.verts):
        bm.verts.new(v.co)
    bm.to_mesh(ob.data); bm.free(); save(outdir, 'doubles')

    fresh(); me = box_mesh('Body'); ob = link(bpy.data.objects.new('Body', me)); save(outdir, 'nomat')

    fresh(); ob = add_box('Body'); ob.data.materials.append(None); save(outdir, 'emptyslot')

    fresh(); ob = add_box('Body')
    corners = [(0.1, 0.1), (0.6, 0.1), (0.6, 0.6), (0.1, 0.6)]
    for poly in ob.data.polygons:
        for k, li in enumerate(poly.loop_indices):
            ob.data.uv_layers.active.data[li].uv = corners[k]
    save(outdir, 'uvoverlap')

    fresh(); me = box_mesh('Body', uv=False); ob = link(bpy.data.objects.new('Body', me)); ob.data.materials.append(material()); save(outdir, 'nouv')

    fresh()
    for nm in ('Leg', 'Leg', 'my part', 'x' * 120):
        o = add_box(nm); o.location.x += len(bpy.data.objects) * 5
    save(outdir, 'names')

    fresh(); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=200, v_segments=120, radius=3)
    for v in bm.verts:
        v.co.z += 3
    me = bpy.data.meshes.new('Body'); bm.to_mesh(me); bm.free(); ob = link(bpy.data.objects.new('Body', me)); ob.data.materials.append(material())
    me.uv_layers.new(name='UVMap')
    save(outdir, 'heavy')

    fresh(); add_box('Body', w=3000, d=10, h=10); save(outdir, 'huge')

    fresh(); add_box('Body', bottom=False); save(outdir, 'centre')

    fresh(); ob = add_box('Body')
    arm_data = bpy.data.armatures.new('Rig'); arm = link(bpy.data.objects.new('Rig', arm_data))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    b1 = arm_data.edit_bones.new('Lower'); b1.head, b1.tail = (0, 0, 0), (0, 0, 3)
    b2 = arm_data.edit_bones.new('Upper'); b2.head, b2.tail = (0, 0, 3), (0, 0, 6.6); b2.parent = b1
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.parent = arm
    low = ob.vertex_groups.new(name='Lower'); up = ob.vertex_groups.new(name='Upper')
    for v in ob.data.vertices:
        (low if v.co.z < 3.3 else up).add([v.index], 1.0, 'REPLACE')
    mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
    arm.animation_data_create()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm.pose.bones['Upper']; pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (0, 0, 0); pb.keyframe_insert('rotation_euler', frame=1)
    pb.rotation_euler = (0.3, 0, 0); pb.keyframe_insert('rotation_euler', frame=12)
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.animation_data.action.name = 'wave'
    save(outdir, 'rigged')
    print('MODELS_OK')


main()
