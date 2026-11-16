"""BD-1217: build assets/blender/anim/DinoClips.blend, a proxy dino rig (one block and one bone per body role) with one Blender action per clip
of tools/blender/dino_clips.py (eat, happy, look, jump, land) and one looping action per locomotion loop (loop_idle, loop_walk, loop_run;
BD-1217 rig follow-up). Headless, a separate process; never the live Blender MCP session:

    blender --background --factory-startup --python tools/blender/build_dino_clips.py
    python tools/animation_strip.py assets/blender/anim/DinoClips.blend --action happy --out build/anim   # contact sheet + numbers

The blocks are a stand-in to see timing and spacing: the game plays the same keys on the real V3 parts (src/shared/LowPolyClips.luau).
Frame: the proxy faces -Y, Z up. Bones point up, so bone X = pitch (sign flipped), bone Y = yaw (about up), bone Z = roll (along forward).
Every block is skinned 100% to one bone (Armature modifier): rigid parts, like the V3 MeshParts on their welds.
"""
import math
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ns = {}
exec(open(os.path.join(ROOT, "tools", "blender", "dino_clips.py"), encoding="utf8").read(), ns)
CLIPS, FPS, NECK_SHARE = ns["CLIPS"], ns["FPS"], ns["NECK_SHARE"]
GAIT = ns.get("GAIT", {})  # BD-1217 rig follow-up: idle / walk / run loops (Config.DinoRigClipsEnabled)
STRIDE_SECONDS = {"walk": 1.0, "run": 0.55}  # a stride loop shown at about the game's stride rate (LowPolyPose.stepRate at walk / run speed)
SIDE_ROLL = {"wing", "flipper", "arm"}
HEIGHT = 4.0  # proxy height in Blender units: bob and fwd are fractions of it

# role -> (block centre, block size, joint) in the proxy frame (faces -Y); side roles are mirrored on X
BODY = ((0, 0, 1.9), (1.4, 2.4, 1.4))
BLOCKS = {
    "neck": ((0, -1.2, 2.7), (0.6, 0.6, 0.9), (0, -1.0, 2.3)),
    "head": ((0, -1.6, 3.4), (0.9, 1.1, 0.8), (0, -1.3, 3.0)),
    "tail": ((0, 2.1, 1.8), (0.6, 2.0, 0.5), (0, 1.1, 1.9)),
    "arm": ((0.55, -1.0, 1.4), (0.25, 0.25, 0.7), (0.55, -1.0, 1.75)),
    "leg": ((0.45, 0.1, 0.6), (0.4, 0.5, 1.2), (0.45, 0.1, 1.2)),
    "wing": ((1.4, 0, 2.3), (1.6, 1.0, 0.1), (0.7, 0, 2.3)),
}
SIDED = {"arm", "leg", "wing"}


def clear():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials):
        for item in list(coll):
            coll.remove(item)


def block(name, centre, size, colour, rig, bone):
    """one box skinned 100% to `bone` (rigid part, like a V3 MeshPart on its weld)"""
    mesh = bpy.data.meshes.new(name)
    hx, hy, hz = (s / 2 for s in size)
    cx, cy, cz = centre
    verts = [(cx + x * hx, cy + y * hy, cz + z * hz) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    mat = bpy.data.materials.new(name + "_mat")
    mat.diffuse_color = colour
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(8)), 1.0, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    obj.parent = rig
    return obj


def build():
    clear()
    arm_data = bpy.data.armatures.new("DinoRig")
    rig = bpy.data.objects.new("DinoRig", arm_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    root = arm_data.edit_bones.new("root")
    root.head, root.tail = (0, 0, 0), (0, 0, 0.5)
    bones = {}
    for role, (centre, size, joint) in BLOCKS.items():
        for side in ((-1, 1) if role in SIDED else (0,)):
            name = role if side == 0 else "%s_%s" % (role, "L" if side < 0 else "R")
            jx = joint[0] * (side if side else 1)
            b = arm_data.edit_bones.new(name)
            b.head, b.tail = (jx, joint[1], joint[2]), (jx, joint[1], joint[2] + 0.4)
            b.parent = root
            bones[name] = (role, side, centre, size)
    bpy.ops.object.mode_set(mode="OBJECT")
    green, cream = (0.2, 0.6, 0.25, 1), (0.9, 0.85, 0.6, 1)
    for name, (role, side, centre, size) in bones.items():
        c = (centre[0] * (side if side else 1), centre[1], centre[2])
        block("P_" + name, c, size, cream if role in ("arm", "wing") else green, rig, name)
    block("P_body", BODY[0], BODY[1], green, rig, "root")
    return rig, bones


def key_clip(rig, bones, name, clip):
    act = bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action = act
    tracks = clip["tracks"]
    frames = sorted({round(t * FPS) for track in tracks.values() for keys in track.values() for t, _ in keys})

    def value(keys, t):  # linear between keys at the key frames only (the keys themselves are what we store)
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                return v0 + (v1 - v0) * ((t - t0) / (t1 - t0) if t1 > t0 else 0)
        return 0

    pr = rig.pose.bones["root"]
    pr.rotation_mode = "XYZ"
    for bone_name, (role, side, _, _) in bones.items():
        pb = rig.pose.bones[bone_name]
        pb.rotation_mode = "XYZ"
        track, k = tracks.get(role), 1.0
        if track is None and role == "neck":
            track, k = tracks.get("head"), NECK_SHARE
        if not track:
            continue
        times = sorted({t for ch in ("pitch", "yaw", "roll") for t, _ in track.get(ch, [])})
        sroll = (-1 if side < 0 else 1) if role in SIDE_ROLL else 1
        for t in times:
            pb.rotation_euler = (-math.radians(value(track.get("pitch", [(0, 0)]), t) * k),  # bone +X turns the nose DOWN; game pitch > 0 = up
                                 math.radians(value(track.get("yaw", [(0, 0)]), t) * k),
                                 math.radians(value(track.get("roll", [(0, 0)]), t) * k * sroll))
            pb.keyframe_insert("rotation_euler", frame=1 + round(t * FPS), group=bone_name)
            if role == "head" and "fwd" in track:
                pb.location = (0, 0, value(track["fwd"], t) * HEIGHT)  # bone Z = -Y in the proxy frame = forward
                pb.keyframe_insert("location", frame=1 + round(t * FPS), group=bone_name)
    if "root" in tracks and "bob" in tracks["root"]:
        for t, v in tracks["root"]["bob"]:
            pr.location = (0, v * HEIGHT, 0)  # bone Y = up
            pr.keyframe_insert("location", frame=1 + round(t * FPS), group="root")
    act["clip_length_s"] = clip["length"]
    act.use_fake_user = True
    return act, frames


def key_loop(rig, bones, name, cyc):
    """one cyclic action per loop, sampled every frame (the game samples the same keys with wrapped monotone Hermite; the stored frames
    are dense, so Blender's interpolation between them is close). The right side runs half a stride later (LowPolyGait.offset)."""
    act = bpy.data.actions.new("loop_" + name)
    rig.animation_data_create()
    rig.animation_data.action = act
    tracks, length = cyc["tracks"], cyc["length"]
    seconds = length if cyc["clock"] == "time" else STRIDE_SECONDS[name]
    frames = max(2, round(seconds * FPS))

    def value(keys, u):  # u in loop units, wrapped; linear between the keys (dense frames)
        u = u % length
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= u <= t1:
                return v0 + (v1 - v0) * ((u - t0) / (t1 - t0) if t1 > t0 else 0)
        return keys[0][1]

    pr = rig.pose.bones["root"]
    for f in range(frames + 1):
        u = f / frames * length
        for bone_name, (role, side, _, _) in bones.items():
            track, k = tracks.get(role), 1.0
            if track is None and role == "neck":
                track, k = tracks.get("head"), NECK_SHARE
            if not track:
                continue
            off = 0.5 * length if (role in ("leg", "arm") and side > 0 and cyc["clock"] == "stride") else 0
            pb = rig.pose.bones[bone_name]
            pb.rotation_mode = "XYZ"
            sroll = (-1 if side < 0 else 1) if role in SIDE_ROLL else 1
            pb.rotation_euler = (-math.radians(value(track.get("pitch", [(0, 0), (length, 0)]), u + off) * k),
                                 math.radians(value(track.get("yaw", [(0, 0), (length, 0)]), u + off) * k),
                                 math.radians(value(track.get("roll", [(0, 0), (length, 0)]), u + off) * k * sroll))
            pb.keyframe_insert("rotation_euler", frame=1 + f, group=bone_name)
        if "root" in tracks and "bob" in tracks["root"]:
            pr.location = (0, value(tracks["root"]["bob"], u) * HEIGHT, 0)
            pr.keyframe_insert("location", frame=1 + f, group="root")
    act["clip_length_s"] = seconds
    act["loop"] = True
    act.use_frame_range = True  # the last keyed frame equals the first: the loop plays frames 1..frames, not that pose twice
    act.frame_start, act.frame_end = 1, frames
    act.use_fake_user = True
    return act


def main():
    rig, bones = build()
    actions = {}
    for name, clip in CLIPS.items():
        actions[name], _ = key_clip(rig, bones, name, clip)
    for name, cyc in GAIT.items():
        actions["loop_" + name] = key_loop(rig, bones, name, cyc)
    scene = bpy.context.scene
    scene.render.fps = FPS
    rig.animation_data.action = actions["happy"]
    scene.frame_start, scene.frame_end = 1, 1 + round(CLIPS["happy"]["length"] * FPS)
    for pb in rig.pose.bones:
        pb.location, pb.rotation_euler = (0, 0, 0), (0, 0, 0)
    out = os.path.join(ROOT, "assets", "blender", "anim", "DinoClips.blend")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("saved", out, "actions:", ", ".join(actions))


main()
