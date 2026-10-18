#!/usr/bin/env python3
"""Export a .blend to a Roblox-ready FBX with headless Blender (docs/169, BD-659). One file, two modes.

Outside Blender (normal use):
  python tools/blender_export_roblox.py assets/blender/creatures/Cockatoo_HQ.blend --out build/Cockatoo.fbx
  python tools/blender_export_roblox.py model.blend --out build/Cockatoo_rigged.fbx --rig --anim
  python tools/blender_export_roblox.py model.blend --out x.fbx --dry-run     # only print the Blender command

It finds Blender (env BLENDER_EXE, then PATH, then C:/Program Files/Blender Foundation/*/blender.exe), runs
`blender --background file.blend --python this_file -- <args>`, then (if present) runs tools/check_model_for_roblox.py.
Uses plain `blender --background`. It does NOT use the Blender MCP, so it never touches an open Blender window.

Inside Blender (this same file is the --python script): checks the scene and calls export_scene.fbx with the settings
that worked for the cockatoo test model (docs/evidence/2026-10-18-cockatoo-blender):
  * 1 Blender unit = 1 stud (global_scale 0.01), up Y. The FBX forward axis follows --faces (default +Y, like the cockatoo): a creature
    that faces +Y in Blender then faces -Z (the Roblox front). Measured 2026-10-18 (docs/169 section 6): with axis_forward -Z the
    cockatoo arrived turned 180 degrees (it faced +Z, left and right swapped), because Blender's own front is -Y.
  * the armature is put in its rest pose first (no action, bones reset): the saved .blend had a leftover pose (LegR 0.2 up, tail yaw 5),
    which the parts-only export baked in.
  * every part its own mesh object; part origins are kept (they become the joint pivots); scale 1, rotation 0 (checked, and
    fixed with --apply-transforms when there is no armature).
  * vertex colours exported as sRGB (the Roblox importer reads them when "use vertex colours" is on).
  * normals only (no edge/face smoothing data), no extra leaf bones, bone axis Y/X, optional baked actions.
A sidecar JSON (<out>.report.json) lists parts, triangles and size in studs.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
MAX_TRIS_PER_MESHPART = 21844  # Roblox MeshPart limit (docs/evidence/2026-10-18-cockatoo-blender)
CHECKER = ROOT / "tools" / "check_model_for_roblox.py"

try:  # only true inside Blender
    import bpy  # type: ignore
    INSIDE_BLENDER = True
except ImportError:
    bpy = None
    INSIDE_BLENDER = False


# =========================================================================== outside Blender

def find_blender(environ=None):
    environ = os.environ if environ is None else environ
    exe = environ.get("BLENDER_EXE")
    if exe and Path(exe).is_file():
        return exe
    found = shutil.which("blender")
    if found:
        return found
    pattern = "C:/Program Files/Blender Foundation/*/blender.exe"
    candidates = sorted(glob.glob(pattern))
    return candidates[-1] if candidates else None


FACING_TO_FBX_FORWARD = {"+Y": "Z", "-Y": "-Z"}  # direction the model faces in Blender -> FBX axis_forward (Roblox front is -Z)


def fbx_forward_axis(facing):
    """FBX axis_forward for a model that faces `facing` ('+Y' or '-Y') in Blender, so that it faces -Z (the front) in Roblox."""
    try:
        return FACING_TO_FBX_FORWARD[facing]
    except KeyError:
        raise ValueError("--faces must be +Y or -Y, got %r" % (facing,))


def blender_command(blender, blend, out, rig=False, anim=False, apply_transforms=False, report=None, faces="+Y"):
    cmd = [blender, "--background", "--factory-startup", str(blend), "--python", str(SELF), "--", "--out", str(out), "--faces", faces]
    if rig:
        cmd.append("--rig")
    if anim:
        cmd.append("--anim")
    if apply_transforms:
        cmd.append("--apply-transforms")
    if report:
        cmd += ["--report", str(report)]
    return cmd


def run_checker(fbx, runner=subprocess.run, checker=CHECKER, out=print):
    """Run tools/check_model_for_roblox.py if it exists. Its command line is not verified here (tool lives on another branch)."""
    if not Path(checker).is_file():
        out("NOTICE: tools/check_model_for_roblox.py is not in this tree (animation-strip-and-model-checker work, docs/163); skipped the model check.")
        return None
    res = runner([sys.executable, str(checker), str(fbx)], capture_output=True, text=True)
    out((res.stdout or "").rstrip())
    if res.returncode:
        out((res.stderr or "").rstrip())
    return res.returncode


def outer_main(argv, runner=subprocess.run, environ=None, out=print):
    ap = argparse.ArgumentParser(description="Headless Blender -> Roblox FBX.")
    ap.add_argument("blend", help=".blend file")
    ap.add_argument("--out", required=True, help="output .fbx path")
    ap.add_argument("--rig", action="store_true", help="include the armature (Motor6D rig)")
    ap.add_argument("--anim", action="store_true", help="bake all actions into the FBX (implies --rig)")
    ap.add_argument("--apply-transforms", action="store_true", help="apply rotation+scale to meshes (only when there is no armature)")
    ap.add_argument("--faces", default="+Y", choices=sorted(FACING_TO_FBX_FORWARD), help="direction the model faces in Blender (default +Y)")
    ap.add_argument("--dry-run", action="store_true", help="print the Blender command, run nothing")
    ap.add_argument("--no-check", action="store_true", help="skip tools/check_model_for_roblox.py")
    args = ap.parse_args(argv)
    blend = Path(args.blend)
    out_path = Path(args.out)
    if not blend.is_file():
        print("ERROR: %s not found" % blend, file=sys.stderr)
        return 2
    if out_path.suffix.lower() != ".fbx":
        print("ERROR: --out must end in .fbx", file=sys.stderr)
        return 2
    blender = find_blender(environ)
    if not blender:
        print("ERROR: Blender not found. Set BLENDER_EXE to blender.exe.", file=sys.stderr)
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = out_path.with_suffix(".report.json")
    cmd = blender_command(blender, blend, out_path, args.rig or args.anim, args.anim, args.apply_transforms, report, args.faces)
    out("Blender command: " + " ".join('"%s"' % c if " " in c else c for c in cmd))
    if args.dry_run:
        return 0
    res = runner(cmd, capture_output=True, text=True)
    tail = (res.stdout or "").strip().splitlines()[-25:]
    out("\n".join(tail))
    if res.returncode:
        print((res.stderr or "")[-1500:], file=sys.stderr)
        print("ERROR: Blender exited with %d" % res.returncode, file=sys.stderr)
        return res.returncode
    if not out_path.is_file():
        print("ERROR: Blender finished but %s was not written" % out_path, file=sys.stderr)
        return 3
    out("FBX written: %s (%.2f MB)" % (out_path, out_path.stat().st_size / 1048576))
    if not args.no_check:
        code = run_checker(out_path, runner, out=out)
        if code:
            return code
    return 0


# =========================================================================== inside Blender

def mesh_tris(ob):
    me = ob.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def scene_report(meshes, armatures):
    """Plain-data description of what will be exported; no bpy objects in the result."""
    from mathutils import Vector  # type: ignore
    parts, lo, hi = [], [1e9] * 3, [-1e9] * 3
    problems, warnings = [], []
    for ob in meshes:
        tris = mesh_tris(ob)
        corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        for c in corners:
            for i in range(3):
                lo[i], hi[i] = min(lo[i], c[i]), max(hi[i], c[i])
        scale_ok = all(abs(s - 1.0) < 1e-4 for s in ob.scale)
        rot_ok = all(abs(a) < 1e-4 for a in ob.rotation_euler)
        if tris > MAX_TRIS_PER_MESHPART:
            problems.append("%s has %d triangles (Roblox MeshPart limit %d): split it" % (ob.name, tris, MAX_TRIS_PER_MESHPART))
        if not (scale_ok and rot_ok):
            warnings.append("%s has object scale/rotation that is not 1/0 (use --apply-transforms if there is no armature)" % ob.name)
        if not ob.data.uv_layers and not ob.data.color_attributes:
            warnings.append("%s has neither UVs nor vertex colours: it will export plain grey" % ob.name)
        if ob.parent and ob.parent.type == "MESH":
            warnings.append("%s is parented to another mesh; Roblox flattens this, check pivots" % ob.name)
        parts.append({
            "name": ob.name, "tris": tris, "verts": len(ob.data.vertices),
            "origin": [round(x, 3) for x in ob.matrix_world.translation],
            "scale_is_1": scale_ok, "rotation_is_0": rot_ok,
            "vertex_colours": [a.name for a in ob.data.color_attributes],
            "uv_layers": [u.name for u in ob.data.uv_layers],
        })
    size = [round(hi[i] - lo[i], 3) for i in range(3)] if parts else [0, 0, 0]
    # Blender X (width), Y (depth), Z (height) in studs
    if parts and (max(size) > 200 or max(size) < 0.2):
        warnings.append("model is %s studs across: check the unit scale (1 Blender unit should be 1 stud)" % size)
    total = sum(p["tris"] for p in parts)
    return {
        "parts": parts, "part_count": len(parts), "total_tris": total,
        "size_studs_xyz_blender": size, "armatures": [a.name for a in armatures],
        "problems": problems, "warnings": warnings,
    }


def reset_to_rest_pose(armatures):
    """Drop any assigned action and reset every pose bone, so exports start from the rest pose (works on any object with
    .animation_data and .pose.bones, so it is testable with stand-ins). Returns the number of bones reset."""
    n = 0
    for ob in armatures:
        if getattr(ob, "animation_data", None) is not None:
            ob.animation_data.action = None
        for pb in ob.pose.bones:
            pb.location = (0.0, 0.0, 0.0)
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            pb.rotation_euler = (0.0, 0.0, 0.0)
            pb.scale = (1.0, 1.0, 1.0)
            n += 1
    return n


def inner_main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--faces", default="+Y")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rig", action="store_true")
    ap.add_argument("--anim", action="store_true")
    ap.add_argument("--apply-transforms", action="store_true")
    ap.add_argument("--report")
    args = ap.parse_args(argv)

    scene = bpy.context.scene
    meshes = [o for o in scene.objects if o.type == "MESH" and not o.hide_get() and o.visible_get()]
    armatures = [o for o in scene.objects if o.type == "ARMATURE"]
    use_rig = bool(args.rig or args.anim) and bool(armatures)
    if (args.rig or args.anim) and not armatures:
        print("WARNING: --rig asked for but the file has no armature; exporting parts only")
    if args.apply_transforms:
        if use_rig:
            print("WARNING: --apply-transforms ignored because an armature is exported (it would break the skin binding)")
        else:
            bpy.ops.object.select_all(action="DESELECT")
            for ob in meshes:
                ob.select_set(True)
            bpy.context.view_layer.objects.active = meshes[0]
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if armatures:
        print("Rest pose: reset %d pose bones, actions unassigned" % reset_to_rest_pose(armatures))
        bpy.context.view_layer.update()
    report = scene_report(meshes, armatures if use_rig else [])
    for p in report["problems"]:
        print("PROBLEM:", p)
    for w in report["warnings"]:
        print("WARNING:", w)
    if not meshes:
        print("ERROR: no visible mesh objects to export")
        sys.exit(4)
    if report["problems"]:
        sys.exit(5)

    bpy.ops.object.select_all(action="DESELECT")
    sel = meshes + (armatures if use_rig else [])
    for ob in sel:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = sel[0]
    kw = dict(
        filepath=args.out, use_selection=True,
        object_types={"MESH", "ARMATURE"} if use_rig else {"MESH"},
        # global_scale 0.01: Blender writes metres as centimetres (x100) and Roblox reads FBX units as studs, so without it a
        # 4-unit cube arrived as 400 studs (measured 2026-10-18 with the acceptance cube, asset 98358657150463).
        apply_unit_scale=True, global_scale=0.01, axis_forward=fbx_forward_axis(args.faces), axis_up="Y",
        colors_type="SRGB", mesh_smooth_type="OFF", add_leaf_bones=False, bake_anim=bool(args.anim and use_rig),
    )
    if use_rig:
        kw.update(primary_bone_axis="Y", secondary_bone_axis="X", use_armature_deform_only=False)
    if args.anim and use_rig:
        kw.update(bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                  bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
    bpy.ops.export_scene.fbx(**kw)
    report["fbx"] = os.path.basename(args.out)
    report["fbx_bytes"] = os.path.getsize(args.out)
    report["settings"] = {k: (sorted(v) if isinstance(v, set) else v) for k, v in kw.items() if k != "filepath"}
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    print("EXPORTED %s: %d parts, %d triangles, %.2f MB, size (studs, Blender xyz) %s" % (
        report["fbx"], report["part_count"], report["total_tris"], report["fbx_bytes"] / 1048576, report["size_studs_xyz_blender"]))


if __name__ == "__main__":
    if INSIDE_BLENDER:
        inner_main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    else:
        sys.exit(outer_main(sys.argv[1:]))
