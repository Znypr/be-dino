"""Blender-side helper for tools/animation_strip.py (BD-641, docs/163). It runs INSIDE a headless Blender, never in the live MCP session:

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python tools/blender_animation_probe.py -- \
        INPUT.(blend|fbx|obj|glb) OUT.json [--frames-dir DIR --count 8 --size 256] [--view auto|x|-x|y|-y] [--action NAME] [--start N --end N]

It evaluates the animation frame by frame and writes plain numbers to OUT.json (the analysis lives in animation_strip.py, so it can be
tested without Blender): for every bone the world head and tail position and the local pose rotation (quaternion, relative to rest),
for every animated object its world position, the lowest and the box of the deformed meshes, and the key-frame interpolation types.
With --frames-dir it also renders `count` evenly spaced frames from the side (Workbench, orthographic, ground line and ticks).
Units are Blender units (the repo exports 1 unit = 1 stud for creatures). Z is up, the side camera looks along +Y (X goes right).
"""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    opts = {'input': argv[0], 'out': argv[1], 'frames_dir': None, 'count': 8, 'size': 256, 'action': None, 'start': None, 'end': None, 'view': 'auto'}
    i = 2
    while i < len(argv):
        key = argv[i]
        if key == '--frames-dir':
            opts['frames_dir'] = argv[i + 1]
        elif key == '--count':
            opts['count'] = int(argv[i + 1])
        elif key == '--size':
            opts['size'] = int(argv[i + 1])
        elif key == '--view':
            opts['view'] = argv[i + 1]
        elif key == '--action':
            opts['action'] = argv[i + 1]
        elif key == '--start':
            opts['start'] = int(argv[i + 1])
        elif key == '--end':
            opts['end'] = int(argv[i + 1])
        else:
            raise SystemExit('unknown option ' + key)
        i += 2
    return opts


def load(path):
    low = path.lower()
    if low.endswith('.blend'):
        bpy.ops.wm.open_mainfile(filepath=path)
        return 'blend'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if low.endswith('.fbx'):
        try:
            bpy.ops.import_scene.fbx(filepath=path)
        except Exception:
            bpy.ops.wm.fbx_import(filepath=path)
        return 'fbx'
    if low.endswith('.obj'):
        bpy.ops.wm.obj_import(filepath=path)
        return 'obj'
    if low.endswith('.glb') or low.endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=path)
        return 'gltf'
    raise SystemExit('unsupported file type: ' + path)


def iter_fcurves(action):
    """Blender 4.4+ slotted actions keep curves in layers/strips/channelbags; older ones in action.fcurves."""
    try:
        curves = action.fcurves
        if curves is not None:
            for fc in curves:
                yield fc
            return
    except AttributeError:
        pass
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', []):
                for fc in bag.fcurves:
                    yield fc


def pick_action(want):
    acts = list(bpy.data.actions)
    if want:
        for a in acts:
            if a.name == want:
                return a
        raise SystemExit('no action named ' + want + '; found: ' + ', '.join(a.name for a in acts))
    # the action already assigned to an armature wins, else the one with the most curves
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE' and ob.animation_data and ob.animation_data.action:
            return ob.animation_data.action
    best, best_n = None, 0
    for a in acts:
        n = sum(1 for _ in iter_fcurves(a))
        if n > best_n:
            best, best_n = a, n
    return best


def assign(action):
    """Make every armature play `action` (also when the file had another one playing: the one asked for wins)."""
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE':
            ad = ob.animation_data or ob.animation_data_create()
            if ad.action != action:
                ad.action = action
            try:
                if len(action.slots) and ad.action_slot not in list(action.slots):
                    ad.action_slot = action.slots[0]
            except (AttributeError, RuntimeError):
                pass


def mesh_objects():
    return [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_get() and o.visible_get()]


def mesh_box(depsgraph):
    """Box of all visible deformed meshes in world space: (minx, miny, minz, maxx, maxy, maxz) or None."""
    lo = np.array([1e30] * 3)
    hi = np.array([-1e30] * 3)
    seen = False
    for ob in mesh_objects():
        ev = ob.evaluated_get(depsgraph)
        me = ev.to_mesh()
        n = len(me.vertices)
        if n == 0:
            ev.to_mesh_clear()
            continue
        co = np.empty(n * 3, dtype=np.float64)
        me.vertices.foreach_get('co', co)
        co = co.reshape(n, 3)
        mw = np.array(ev.matrix_world)
        wc = co @ mw[:3, :3].T + mw[:3, 3]
        lo = np.minimum(lo, wc.min(axis=0))
        hi = np.maximum(hi, wc.max(axis=0))
        seen = True
        ev.to_mesh_clear()
    return [float(v) for v in list(lo) + list(hi)] if seen else None


def r5(v):
    return [round(float(x), 5) for x in v]


def main():
    opts = parse_args()
    kind = load(opts['input'])
    scene = bpy.context.scene
    action = pick_action(opts['action'])
    out = {'source': opts['input'], 'kind': kind, 'action': action.name if action else None, 'blender': bpy.app.version_string}
    if action is not None:
        assign(action)
    fps = scene.render.fps / (scene.render.fps_base or 1.0)
    out['fps'] = fps
    if action is not None and action.use_frame_range:
        f0, f1 = int(round(action.frame_start)), int(round(action.frame_end))
    elif action is not None:
        f0, f1 = int(round(action.frame_range[0])), int(round(action.frame_range[1]))
    else:
        f0 = f1 = scene.frame_start         # no action in the file: one frame is enough to draw the static pose
    if opts['start'] is not None:
        f0 = opts['start']
    if opts['end'] is not None:
        f1 = opts['end']
    out['frame_start'], out['frame_end'] = f0, f1
    out['scene_range'] = [scene.frame_start, scene.frame_end]

    armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    animated_objects = [o for o in bpy.data.objects if o.animation_data and o.animation_data.action and o.type != 'ARMATURE']
    out['armatures'] = [a.name for a in armatures]
    out['mesh_objects'] = [o.name for o in mesh_objects()]

    # key-frame interpolation types and which bones are keyed
    interp, easing, keyed, per_bone_keys, paths = {}, {}, set(), {}, set()
    if action is not None:
        for fc in iter_fcurves(action):
            paths.add(fc.data_path[:60])
            pts = fc.keyframe_points
            for kp in pts:
                interp[kp.interpolation] = interp.get(kp.interpolation, 0) + 1
                easing[kp.easing] = easing.get(kp.easing, 0) + 1
                keyed.add(round(kp.co[0], 3))
            if fc.data_path.startswith('pose.bones['):
                bone = fc.data_path.split('"')[1]
                per_bone_keys.setdefault(bone, set()).update(round(kp.co[0], 3) for kp in pts)
    out['keys'] = {
        'interpolation': interp, 'easing': easing, 'keyed_frames': sorted(keyed),
        'curve_count': sum(1 for _ in iter_fcurves(action)) if action is not None else 0,
        'bones_keyed': {b: len(v) for b, v in per_bone_keys.items()},
        'data_paths': sorted(paths)[:8],
    }

    # rest pose box: the standing size of the model
    rest_box = None
    if armatures:
        for a in armatures:
            a.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        rest_box = mesh_box(bpy.context.evaluated_depsgraph_get())
        for a in armatures:
            a.data.pose_position = 'POSE'
    else:
        bpy.context.view_layer.update()
    out['rest_box'] = rest_box
    rest_bones = {}
    for arm in armatures:
        for b in arm.data.bones:
            key = b.name if len(armatures) == 1 else arm.name + '/' + b.name
            rest_bones[key] = {'head': r5(arm.matrix_world @ b.head_local), 'tail': r5(arm.matrix_world @ b.tail_local)}
    out['rest_bones'] = rest_bones

    frames = list(range(f0, f1 + 1))
    out['frames'] = frames
    bones, objects, mesh_boxes = {}, {}, []
    for f in frames:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for arm in armatures:
            mw = arm.matrix_world
            for pb in arm.pose.bones:
                key = pb.name if len(armatures) == 1 else arm.name + '/' + pb.name
                rec = bones.setdefault(key, {'parent': (pb.parent.name if pb.parent else None), 'head': [], 'tail': [], 'quat': [], 'loc': []})
                rec['head'].append(r5(mw @ pb.head))
                rec['tail'].append(r5(mw @ pb.tail))
                q = pb.matrix_basis.to_quaternion()
                rec['quat'].append([round(q.w, 6), round(q.x, 6), round(q.y, 6), round(q.z, 6)])
                rec['loc'].append(r5(pb.matrix_basis.to_translation()))
        for ob in list(armatures) + animated_objects:
            e = ob.matrix_world.to_euler()
            rec = objects.setdefault(ob.name, {'loc': [], 'rot': []})
            rec['loc'].append(r5(ob.matrix_world.to_translation()))
            rec['rot'].append(r5([math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)]))
        mesh_boxes.append(mesh_box(dg))
    out['bones'] = bones
    out['objects'] = objects
    out['mesh_box'] = mesh_boxes if any(b is not None for b in mesh_boxes) else None

    if opts['frames_dir']:
        out['rendered'] = render_frames(opts, frames, rest_box, mesh_boxes, bones)
    with open(opts['out'], 'w') as fh:
        json.dump(out, fh)
    print('PROBE_OK frames=%d bones=%d objects=%d action=%s' % (len(frames), len(bones), len(objects), out['action']))


def render_frames(opts, frames, rest_box, mesh_boxes, bones):
    """Side-view Workbench renders of `count` evenly spaced frames. Returns [[frame, path], ...] (empty without any mesh)."""
    boxes = [b for b in mesh_boxes if b is not None]
    if not boxes:
        return []
    import os
    os.makedirs(opts['frames_dir'], exist_ok=True)
    scene = bpy.context.scene
    lo = [min(b[i] for b in boxes) for i in range(3)]
    hi = [max(b[i + 3] for b in boxes) for i in range(3)]
    ground = rest_box[2] if rest_box else lo[2]
    height = max(hi[2] - ground, 0.001)
    # which way is "right" on the picture: auto = the way the body travels (dominant horizontal axis), else -Y (the creatures face -Y,
    # so they face right); x / -x / y / -y force it
    view = opts['view']
    if view == 'auto':
        c0 = [(boxes[0][i] + boxes[0][i + 3]) / 2 for i in range(3)]
        c1 = [(boxes[-1][i] + boxes[-1][i + 3]) / 2 for i in range(3)]
        dx, dy = c1[0] - c0[0], c1[1] - c0[1]
        if max(abs(dx), abs(dy)) > 0.05 * height:
            view = ('x' if dx > 0 else '-x') if abs(dx) >= abs(dy) else ('y' if dy > 0 else '-y')
        else:
            view = '-y'
    ra = 0 if view in ('x', '-x') else 1
    da = 1 - ra
    sign = -1 if view.startswith('-') else 1
    right = Vector((sign, 0, 0)) if ra == 0 else Vector((0, sign, 0))
    up = Vector((0, 0, 1))
    toward = right.cross(up)                    # points at the viewer; the camera looks the other way
    x0, x1 = lo[ra] - height * 0.35, hi[ra] + height * 0.35
    thick = height * 0.012
    depth = max(hi[da] - lo[da], height * 0.2)
    mid_da = (lo[da] + hi[da]) / 2
    def add_box(along, cz, s_along, sz, color):
        loc = [0, 0, cz]
        loc[ra], loc[da] = along, mid_da
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        ob = bpy.context.active_object
        sc = [0, 0, sz]
        sc[ra], sc[da] = s_along, depth
        ob.scale = sc
        mat = bpy.data.materials.new('probe_ground')
        mat.diffuse_color = color
        ob.data.materials.append(mat)
        ca = ob.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')       # so the ground keeps its colour when the model is drawn with vertex colours
        ca.data.foreach_set('color', list(color) * len(ob.data.vertices))
        return ob
    # ground line + tick marks every half body height so foot sliding and travel are visible against the ground
    add_box((x0 + x1) / 2, ground - thick / 2, x1 - x0, thick, (0.25, 0.28, 0.3, 1))
    step = height / 2
    t = math.floor(x0 / step) * step
    while t <= x1:
        add_box(t, ground - thick * 1.6, thick * 1.2, thick * 2.4, (0.9, 0.3, 0.2, 1))
        t += step
    cam_data = bpy.data.cameras.new('probe_cam')
    cam_data.type = 'ORTHO'
    span = max(x1 - x0, height * 1.3)
    cam_data.ortho_scale = span * 1.05
    cam = bpy.data.objects.new('probe_cam', cam_data)
    scene.collection.objects.link(cam)
    centre = Vector((0, 0, ground + height * 0.5))
    centre[ra] = (lo[ra] + hi[ra]) / 2
    centre[da] = mid_da
    cam.location = centre + toward * (height * 6 + depth)
    cam.rotation_euler = Matrix(((right[0], up[0], toward[0]), (right[1], up[1], toward[1]), (right[2], up[2], toward[2]))).to_euler()
    scene.camera = cam
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = scene.render.resolution_y = opts['size']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.display.shading.light = 'STUDIO'
    has_vc = any(len(o.data.color_attributes) for o in mesh_objects() if not o.name.startswith('Cube'))
    scene.display.shading.color_type = 'VERTEX' if has_vc else 'MATERIAL'
    scene.display.shading.show_cavity = False
    world = bpy.data.worlds.new('probe_world')
    world.color = (0.86, 0.9, 0.93)
    scene.world = world
    scene.render.film_transparent = False
    n = max(2, opts['count'])
    picks = sorted(set(int(round(frames[0] + (frames[-1] - frames[0]) * i / (n - 1))) for i in range(n)))
    done = []
    for f in picks:
        scene.frame_set(f)
        path = os.path.join(opts['frames_dir'], 'frame_%05d.png' % f)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done.append([f, path])
    return done


main()
