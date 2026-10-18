"""Cockatoo HQ export helpers (BD-621 test model): FBX files for Roblox + a stats JSON. exec() after cockatoo_rig.py."""
FBX_DIR = ROOT + "/assets/blender/creatures/fbx/"


def _select(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def mesh_stats(objs):
    out = {}
    for n, ob in objs.items():
        me = ob.data
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        ws = [ob.matrix_world @ v.co for v in me.vertices]
        mn = [min(w[i] for w in ws) for i in range(3)]
        mx = [max(w[i] for w in ws) for i in range(3)]
        out[n] = {"tris": tris, "verts": len(me.vertices), "min": [round(x, 3) for x in mn], "max": [round(x, 3) for x in mx], "origin": [round(x, 3) for x in ob.matrix_world.translation]}
    return out


def export_fbx(path, objs, arm=None, anims=False):
    sel = list(objs.values()) + ([arm] if arm else [])
    _select(sel)
    kw = dict(filepath=path, use_selection=True, object_types={"MESH", "ARMATURE"} if arm else {"MESH"}, apply_unit_scale=True, axis_forward="-Z", axis_up="Y",
              colors_type="SRGB", mesh_smooth_type="OFF", add_leaf_bones=False, bake_anim=anims)
    if anims:
        kw.update(bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
    if arm:
        kw.update(primary_bone_axis="Y", secondary_bone_axis="X", use_armature_deform_only=False)
    bpy.ops.export_scene.fbx(**kw)
    return os.path.getsize(path)


def anim_frames(arm, anim, times, tag, view="side", res=(360, 560), cz=3.9, scale=8.4, cx=0.0, outdir=None):
    """render one picture per key time of an action (orthographic review camera, lit from the camera side)."""
    sc = bpy.context.scene
    arm.animation_data.action = bpy.data.actions[anim]
    ref_camera(view, res, cx, cz, scale)
    aim_key({"side": (1, 0, 0), "front": (0, 1, 0), "back": (0, -1, 0)}[view])
    for i, t in enumerate(times):
        sc.frame_set(round(1 + t * 30))
        sc.render.filepath = (outdir or SP) + "anim_%s_%s_%d.png" % (tag, anim, i)
        bpy.ops.render.render(write_still=True)
