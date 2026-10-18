"""Cockatoo HQ rig + actions (BD-621 test model). exec() after build_cockatoo_hq.py has built the parts (objs dict).
One bone per part (rigid parts, pivot at the joint) so the same rig maps 1:1 onto Roblox Motor6Ds."""
exec(open(ROOT + "/tools/blender/cockatoo_anim.py", encoding="utf8").read())

BONE_TAIL = {  # tail direction (unit) and length for display; the bone HEAD is the joint
    "Body": (V((0, 0.0, 1)), 0.9), "Head": (V((0, 0.3, 1)), 0.8), "Crest": (V((0, -1, 0.5)), 0.8), "Tail": (V((0, -1, 0)), 0.9),
    "ArmR": (V((0, 0.3, -1)), 1.3), "ArmL": (V((0, 0.3, -1)), 1.3), "LegR": (V((0, 0, -1)), 0.93), "LegL": (V((0, 0, -1)), 0.93),
    "FootR": (V((0, 1, -0.3)), 0.8), "FootL": (V((0, 1, -0.3)), 0.8),
}
FPS = 30


def build_rig(objs):
    for ob in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    ad = bpy.data.armatures.new("CockatooRig")
    arm = bpy.data.objects.new("CockatooRig", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for name in PARTS:
        b = ad.edit_bones.new(name)
        d, L = BONE_TAIL[name]
        b.head = JOINTS[name]
        b.tail = JOINTS[name] + d.normalized() * L
        b.roll = 0.0
        eb[name] = b
    for name in PARTS:
        if PARENT[name]:
            eb[name].parent = eb[PARENT[name]]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.show_in_front = True
    # rigid skinning: every mesh is a child of its bone (parent inverse keeps the rest pose)
    for name, ob in objs.items():
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = name
        bone = ad.bones[name]
        ob.matrix_parent_inverse = (arm.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))).inverted()
    return arm


def _conj(arm, name):
    return arm.data.bones[name].matrix_local.to_3x3()


def _interp_note():
    return None


def make_actions(arm):
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    if arm.animation_data is None:
        arm.animation_data_create()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    actions = {}
    for an, spec in ANIMS.items():
        act = bpy.data.actions.new(an)
        act.use_fake_user = True
        arm.animation_data.action = act
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
        for name, tr in spec["tracks"].items():
            pb = arm.pose.bones[name]
            Mr = _conj(arm, name)
            Mi = Mr.inverted()
            for (t, x, y, z) in tr.get("pos", []):
                pb.location = Mi @ Vector((x, y, z))
                pb.keyframe_insert("location", frame=round(1 + t * FPS), group=name)
            prev = None
            for (t, p, r, w) in tr.get("rot", []):
                Rw = Euler((math.radians(p), math.radians(r), math.radians(w)), "XYZ").to_matrix()
                q = (Mi @ Rw @ Mr).to_quaternion()
                if prev is not None and q.dot(prev) < 0:
                    q = -q
                prev = q
                pb.rotation_quaternion = q
                pb.keyframe_insert("rotation_quaternion", frame=round(1 + t * FPS), group=name)
        act.use_frame_range = True
        act.frame_start = 1
        act.frame_end = round(1 + spec["length"] * FPS)
        act.use_cyclic = bool(spec["loop"])
        actions[an] = act
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.animation_data.action = actions["Idle"]
    return actions


def set_action(arm, name, frame):
    arm.animation_data.action = bpy.data.actions[name]
    bpy.context.scene.frame_set(int(frame))
