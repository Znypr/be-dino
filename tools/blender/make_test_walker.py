"""Test fixture for tools/animation_strip.py (BD-641, docs/163): a tiny box-limbed two-legged walker with a 24-frame walk cycle.
Run it in a headless Blender (never the live MCP session):

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python tools/blender/make_test_walker.py -- \
        OUT.blend [OUT.fbx] [--defects loop,jerk,sink,slide,phase,dup]
    ... -- --multi OUTDIR ok loop:loop dup:dup     (one Blender start, many files: NAME[:defect,defect] -> OUTDIR/walk_NAME.blend, plus .fbx when NAME contains fbx)

The clean walker has planted feet (a two-bone solver puts each foot on the ground and moves it backwards at exactly the body speed),
alternating legs (right leg half a cycle behind), smooth speed changes, and a loop that ends one frame before the first pose again.
Each defect breaks exactly one thing so the tests can check that the matching verdict turns to "check":
  loop   last frame is shifted 15% of a cycle (a pop at the loop point)
  dup    frame 25 repeats frame 1 (the loop plays the same pose twice)
  jerk   frame 9: the left foot flips up 0.35 for a single frame (an acceleration spike)
  sink   frames 14 to 16: both feet dip 0.1 below the floor (ground penetration)
  slide  the body moves at 60% of the foot speed (planted feet slide)
  phase  the right leg is 0.3 of a cycle behind instead of 0.5 (uneven left/right timing)
Size: the walker is 1.5 units tall (1 unit = 1 stud for the creature exports). Walk speed 1.2 units per cycle = 1.2 per second at 24 fps.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

LEG = 0.55         # thigh and shin length
HIP = 1.0          # hip height while walking (the rest pose is straight, hip at 1.1)
DIST = 1.2         # body travel per cycle
LIFT = 0.2         # foot lift in the swing
Y_OFF = 0.2        # legs sit this far left / right of the middle


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:]
    if argv and argv[0] == '--multi':
        jobs = []
        for spec in argv[2:]:
            name, _, d = spec.partition(':')
            blend = os.path.join(argv[1], 'walk_%s.blend' % name)
            jobs.append((blend, blend[:-6] + '.fbx' if 'fbx' in name else None, set(x for x in d.split(',') if x)))
        os.makedirs(argv[1], exist_ok=True)
        return jobs
    paths, defects = [], set()
    i = 0
    while i < len(argv):
        if argv[i] == '--defects':
            defects = set(x for x in (argv[i + 1] if i + 1 < len(argv) else '').split(',') if x)
            i += 2
        else:
            paths.append(argv[i])
            i += 1
    return [(paths[0], paths[1] if len(paths) > 1 else None, defects)]


def smooth_profile(defects):
    """Foot x (relative to the body) as a function of the cycle phase, from a velocity profile smoothed by a moving average."""
    n = 2400
    v = []
    for k in range(n):
        phi = k / n
        v.append(-DIST if phi < 0.5 else DIST)    # per cycle: back during the stance half, forward during the swing half
    width = int(0.14 * n)
    sm = []
    for k in range(n):
        sm.append(sum(v[(k + j) % n] for j in range(-width // 2, width // 2 + 1)) / (width + 1))
    x, acc = [], 0.0
    for k in range(n):
        x.append(acc)
        acc += sm[k] / n
    mean = sum(x) / n
    return [a - mean for a in x]


def two_bone(hip, foot, forward_knee=True):
    """Return (knee, thigh_dir, shin_dir) in the XZ plane for hip -> foot with two bones of length LEG."""
    d = foot - hip
    dist = min(d.length, 2 * LEG - 1e-4)
    gamma = math.acos(dist / (2 * LEG))
    base = math.atan2(d.z, d.x)                    # direction of hip -> foot
    ang = base + gamma if forward_knee else base - gamma
    thigh_dir = Vector((math.cos(ang), 0, math.sin(ang)))
    knee = hip + thigh_dir * LEG
    shin_dir = (foot - knee).normalized()
    return knee, thigh_dir, shin_dir


def bone_matrix(head, direction):
    y = Vector(direction).normalized()
    z = Vector((0, 1, 0))
    x = y.cross(z)
    return Matrix([[x[0], y[0], z[0], head[0]], [x[1], y[1], z[1], head[1]], [x[2], y[2], z[2], head[2]], [0, 0, 0, 1]])


def main():
    for blend_path, fbx_path, defects in parse():
        build(blend_path, fbx_path, defects)


def build(blend_path, fbx_path, defects):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    n_frames = 25 if 'dup' in defects else 24
    scene.frame_start, scene.frame_end = 1, n_frames

    arm_data = bpy.data.armatures.new('walker_rig')
    arm = bpy.data.objects.new('walker_rig', arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones

    def add(name, head, tail, parent=None):
        b = eb.new(name)
        b.head, b.tail = head, tail
        b.align_roll(Vector((0, 1, 0)))
        if parent:
            b.parent = eb[parent]
        return b

    add('root', (0, 0, 1.1), (0, 0, 1.4))
    for side, y in (('L', Y_OFF), ('R', -Y_OFF)):
        add('thigh.' + side, (0, y, 1.1), (0, y, 1.1 - LEG), 'root')
        add('shin.' + side, (0, y, 1.1 - LEG), (0, y, 0.0), 'thigh.' + side)
        add('foot.' + side, (0, y, 0.0), (0.25, y, 0.0), 'shin.' + side)
    bpy.ops.object.mode_set(mode='OBJECT')

    def box(name, center, size, bone, color):
        bpy.ops.mesh.primitive_cube_add(size=1, location=center)
        ob = bpy.context.active_object
        ob.name = name
        ob.scale = size
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = color
        ob.data.materials.append(mat)
        pb = arm.pose.bones[bone]
        inv = (arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))).inverted()
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = bone
        ob.matrix_parent_inverse = inv
        return ob

    box('body', (0, 0, 1.3), (0.6, 0.5, 0.4), 'root', (0.95, 0.55, 0.15, 1))
    for side, y, col in (('L', Y_OFF, (0.2, 0.45, 0.9, 1)), ('R', -Y_OFF, (0.2, 0.75, 0.35, 1))):
        box('thigh.' + side, (0, y, 1.1 - LEG / 2), (0.06, 0.06, LEG), 'thigh.' + side, col)
        box('shin.' + side, (0, y, LEG / 2), (0.06, 0.06, LEG), 'shin.' + side, col)
        box('foot.' + side, (0.125, y, 0.04), (0.25, 0.12, 0.08), 'foot.' + side, col)

    prof = smooth_profile(defects)
    nfine = len(prof)

    def foot_x(phi):
        pos = (phi % 1.0) * nfine
        k = int(pos)
        t = pos - k
        return prof[k % nfine] * (1 - t) + prof[(k + 1) % nfine] * t

    def foot_z(phi):
        phi %= 1.0
        if phi < 0.5:
            return 0.0
        psi = (phi - 0.5) / 0.5
        return LIFT * math.sin(math.pi * psi) ** 2

    body_speed = DIST * (0.6 if 'slide' in defects else 1.0)
    right_phase = 0.3 if 'phase' in defects else 0.5
    arm.animation_data_create()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for f in range(1, n_frames + 1):
        scene.frame_set(f)
        k = (f - 1) if not ('dup' in defects and f == n_frames) else 0
        phase = k / 24.0
        if 'loop' in defects and f == n_frames:
            phase += 0.15
        body_x = body_speed * (f - 1) / 24.0
        root = arm.pose.bones['root']
        rest = arm_data.bones['root'].matrix_local.copy()
        rest.translation = (body_x, 0, HIP)
        root.matrix = rest
        bpy.context.view_layer.update()
        for side, y, off in (('L', Y_OFF, 0.0), ('R', -Y_OFF, right_phase)):
            phi = phase - off
            hip = Vector((body_x, y, HIP))
            fx = body_x + foot_x(phi) + 0.0
            fz = foot_z(phi)
            if side == 'L' and 'jerk' in defects and f == 9:
                fz += 0.35
            if 'sink' in defects and 14 <= f <= 16:
                fz -= 0.1 * math.sin(math.pi * (f - 13) / 4)
            foot = Vector((fx, y, fz))
            hip2 = Vector((hip.x, y, hip.z))
            knee, td, sd = two_bone(Vector((hip2.x, 0, hip2.z)), Vector((foot.x, 0, foot.z)))
            th = arm.pose.bones['thigh.' + side]
            th.matrix = bone_matrix((hip.x, y, hip.z), td)
            bpy.context.view_layer.update()
            sh = arm.pose.bones['shin.' + side]
            sh.matrix = bone_matrix((knee.x, y, knee.z), sd)
            bpy.context.view_layer.update()
            ft = arm.pose.bones['foot.' + side]
            ft.matrix = bone_matrix((foot.x, y, foot.z), (1, 0, 0))
            bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            pb.keyframe_insert('location', frame=f)
            pb.keyframe_insert('rotation_quaternion', frame=f)
    arm.animation_data.action.name = 'walk'
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    if fbx_path:
        bpy.ops.export_scene.fbx(filepath=fbx_path, add_leaf_bones=False, bake_anim=True, object_types={'ARMATURE', 'MESH'})
    print('WALKER_OK', blend_path, sorted(defects))


main()
