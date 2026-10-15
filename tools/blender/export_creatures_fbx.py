# Converts the authored creature data (src/shared/CreatureData, extracted to JSON) into skinned FBX files for
# Roblox import, so dinos and the egg load as real uploaded meshes instead of being built at runtime (BD-219).
# This is a format conversion of existing authored geometry, not new modelling.
# Run inside Blender: exec(open(path).read()) with JSON_DIR and OUT_DIR set, or edit the two paths below.
import bpy, json, os, math
from mathutils import Vector, Matrix

JSON_DIR = globals().get('JSON_DIR', r'C:\Users\znypr\AppData\Local\Temp\creature_json')
OUT_DIR = globals().get('OUT_DIR', r'C:\Users\znypr\Documents\be-dino\assets\blender\creatures\fbx')


def rb(v):
    # Roblox (x, y up, z) -> Blender (x, -z, y up)
    return Vector((v[0], -v[2], v[1]))


def cf_matrix(c):
    # Roblox CFrame components: x, y, z, r00..r22 (row-major rotation)
    x, y, z, r00, r01, r02, r10, r11, r12, r20, r21, r22 = c
    rot = Matrix(((r00, r01, r02), (r10, r11, r12), (r20, r21, r22)))
    conv = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # Roblox -> Blender basis
    r = conv @ rot @ conv.transposed()
    m = r.to_4x4()
    m.translation = rb((x, y, z))
    return m


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for d in (bpy.data.meshes, bpy.data.armatures):
        for x in list(d):
            if x.users == 0:
                d.remove(x)


def build(data):
    name = data['id']
    verts = [rb(v) for v in data['vertices']]
    faces = [(f[0] - 1, f[2] - 1, f[1] - 1) for f in data['faces']]  # flip winding for the axis change
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    uvs = data['uvs']
    for i, poly in enumerate(me.polygons):
        n = i * 3
        order = (0, 2, 1)
        for k, li in enumerate(poly.loop_indices):
            u, v = uvs[n + order[k]]
            uvl.data[li].uv = (u, 1 - v)  # Roblox UV origin is top-left
    for p in me.polygons:
        p.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if not data['bones']:
        return obj
    arm = bpy.data.armatures.new(name + '_rig')
    rig = bpy.data.objects.new(name + '_rig', arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    with bpy.context.temp_override(active_object=rig, object=rig, selected_objects=[rig], selected_editable_objects=[rig]):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones(arm, data)
        bpy.ops.object.mode_set(mode='OBJECT')
    groups = [obj.vertex_groups.new(name=b['name']) for b in data['bones']]
    for vi, pairs in enumerate(data['weights']):
        for bone_index, w in pairs:
            groups[bone_index - 1].add([vi], w, 'REPLACE')
    obj.parent = rig
    mod = obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = rig
    return rig


def edit_bones(arm, data):
    ebones = []
    for b in data['bones']:
        m = cf_matrix(b['bind'])
        eb = arm.edit_bones.new(b['name'])
        eb.head = m.translation
        eb.tail = m.translation + (m.to_3x3() @ Vector((0, 0, 0.25)))
        eb.align_roll(m.to_3x3() @ Vector((0, 1, 0)))
        ebones.append(eb)
    for i, b in enumerate(data['bones']):
        if b['parent'] > 0:
            ebones[i].parent = ebones[b['parent'] - 1]


def export(name, root):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    root.select_set(True)
    for c in root.children:
        c.select_set(True)
    bpy.context.view_layer.objects.active = root
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT_DIR, 'creature_%s.fbx' % name), use_selection=True,
                             axis_forward='-Z', axis_up='Y', object_types={'MESH', 'ARMATURE'},
                             add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE')


results = []
for fn in sorted(os.listdir(JSON_DIR)):
    if not fn.endswith('.json'):
        continue
    data = json.load(open(os.path.join(JSON_DIR, fn)))
    clear()
    root = build(data)
    export(data['id'], root)
    results.append((data['id'], len(data['vertices']), data['triangles'], len(data['bones'])))
print(results)
