"""Blender-side helper for tools/check_model_for_roblox.py (BD-642, docs/163). It runs INSIDE a headless Blender, never in the live MCP session:

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python tools/blender_model_probe.py -- INPUT.(blend|fbx|obj|glb) OUT.json
    ... -- --batch OUTDIR file1 file2 ...        (one Blender start for many files: OUTDIR/0.json, 1.json, ...)

It only MEASURES and writes plain numbers; the pass / warn / fail rules live in check_model_for_roblox.py (so they can be tested without
Blender). Per mesh object (modifiers applied, the way an exporter would write it): triangles, vertices, quads and n-gons, world box and
size, origin, unapplied scale and rotation, loose and duplicate vertices, inconsistent or inside-out faces, open edges, zero-area faces,
material slots, UV and vertex-colour layers, UV overlap, bone influences. Units are Blender units (1 unit = 1 stud in this repo).
"""
import json
import math
import os
import sys

import bpy
import numpy as np


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


def uv_overlap(uv, tris, res=256):
    """Raster the UV triangles on a res x res grid. Returns (overlap share of the painted area, share of triangles whose centre is outside 0..1)."""
    t = uv[tris]                                                # [T, 3, 2]
    centre = t.mean(axis=1)
    outside = float(np.mean((centre[:, 0] < 0) | (centre[:, 0] > 1) | (centre[:, 1] < 0) | (centre[:, 1] > 1)))
    grid = np.zeros((res, res), dtype=np.int32)
    px = t * res
    for tri in px:
        x0, y0 = np.floor(tri.min(axis=0)).astype(int)
        x1, y1 = np.ceil(tri.max(axis=0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, res - 1), min(y1, res - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a, b, c = tri
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        w1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        inside = (w1 >= 0) & (w2 >= 0) & (w1 + w2 <= 1)
        grid[y0:y1 + 1, x0:x1 + 1] += inside
    painted = int(grid.sum())
    if painted == 0:
        return 0.0, outside
    covered = int((grid > 0).sum())
    return float((painted - covered) / painted), outside


def mesh_stats(ob, depsgraph):
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    try:
        nv, ne, npoly, nl = len(me.vertices), len(me.edges), len(me.polygons), len(me.loops)
        rec = {'name': ob.name, 'mesh': ob.data.name, 'parent': ob.parent.name if ob.parent else None, 'parent_type': ob.parent_type if ob.parent else None,
               'hidden': bool(ob.hide_get() or ob.hide_viewport), 'modifiers': [m.type for m in ob.modifiers], 'verts': nv, 'edges': ne, 'polys': npoly}
        if nv == 0:
            rec.update({'tris': 0, 'quads': 0, 'ngons': 0, 'empty': True})
            return rec
        co = np.empty(nv * 3)
        me.vertices.foreach_get('co', co)
        co = co.reshape(nv, 3)
        mw = np.array(ev.matrix_world)
        wco = co @ mw[:3, :3].T + mw[:3, 3]
        lo, hi = wco.min(axis=0), wco.max(axis=0)
        rec['box_min'], rec['box_max'] = [float(x) for x in lo], [float(x) for x in hi]
        rec['size'] = [float(x) for x in hi - lo]
        origin = mw[:3, 3]
        rec['origin'] = [float(x) for x in origin]
        loc, rot, scl = ob.matrix_world.decompose()
        e = rot.to_euler()
        rec['scale'] = [float(x) for x in scl]
        rec['rotation_deg'] = [math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)]
        # the object's own transform (before the parent), what "apply scale / rotation" would clear
        rec['local_scale'] = [float(x) for x in ob.scale]
        rec['local_rotation_deg'] = [math.degrees(x) for x in ob.rotation_euler]
        # polygons
        sizes = np.empty(npoly, dtype=np.int32)
        starts = np.empty(npoly, dtype=np.int32)
        me.polygons.foreach_get('loop_total', sizes)
        me.polygons.foreach_get('loop_start', starts)
        rec['tris'] = int((sizes - 2).sum())
        rec['quads'] = int((sizes == 4).sum())
        rec['ngons'] = int((sizes > 4).sum())
        # loops, edges
        lv = np.empty(nl, dtype=np.int64)
        me.loops.foreach_get('vertex_index', lv)
        nxt = np.arange(nl) + 1
        last = starts + sizes - 1
        nxt[last] = starts
        a, b = lv, lv[nxt]
        key = np.minimum(a, b) * nv + np.maximum(a, b)
        uniq, inv, counts = np.unique(key, return_inverse=True, return_counts=True)
        rec['open_edges'] = int((counts == 1).sum())
        rec['nonmanifold_edges'] = int((counts > 2).sum())
        # inconsistent winding: an edge shared by exactly two faces that both walk it in the same direction
        two = counts[inv] == 2
        fwd = (a < b)
        inconsistent = 0
        if two.any():
            idx = np.where(two)[0]
            order = np.argsort(inv[idx], kind='stable')
            pairs = idx[order].reshape(-1, 2)
            inconsistent = int((fwd[pairs[:, 0]] == fwd[pairs[:, 1]]).sum())
        rec['inconsistent_edges'] = inconsistent
        # loose vertices and loose edges
        used = np.zeros(nv, dtype=bool)
        ev_idx = np.empty(ne * 2, dtype=np.int64)
        me.edges.foreach_get('vertices', ev_idx)
        ev_idx = ev_idx.reshape(-1, 2)
        used[ev_idx.ravel()] = True
        rec['loose_verts'] = int((~used).sum())
        ekey = np.minimum(ev_idx[:, 0], ev_idx[:, 1]) * nv + np.maximum(ev_idx[:, 0], ev_idx[:, 1])
        rec['loose_edges'] = int((~np.isin(ekey, uniq)).sum())
        # duplicate vertices (same place within 1e-5 of the part size)
        scale = max(float((hi - lo).max()), 1e-6) * 1e-5
        q = np.round(wco / scale).astype(np.int64)
        rec['duplicate_verts'] = int(nv - len(np.unique(q, axis=0)))
        # zero-area faces
        areas = np.empty(npoly)
        me.polygons.foreach_get('area', areas)
        rec['zero_area_faces'] = int((areas < 1e-10).sum())
        # signed volume (negative = inside out), only meaningful when the mesh is closed
        me.calc_loop_triangles()
        nt = len(me.loop_triangles)
        tv = np.empty(nt * 3, dtype=np.int64)
        me.loop_triangles.foreach_get('vertices', tv)
        tv = tv.reshape(-1, 3)
        p0, p1, p2 = wco[tv[:, 0]], wco[tv[:, 1]], wco[tv[:, 2]]
        rec['signed_volume'] = float(np.sum(np.einsum('ij,ij->i', p0, np.cross(p1, p2))) / 6.0)
        rec['closed'] = bool(rec['open_edges'] == 0 and rec['nonmanifold_edges'] == 0)
        # connected shells: a part can hold several (body, wings, eyes); each closed shell has its own inside / outside
        parent = np.arange(nv)

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for u, v in np.unique(np.stack([np.minimum(a, b), np.maximum(a, b)], axis=1), axis=0):
            ru, rv = find(int(u)), find(int(v))
            if ru != rv:
                parent[max(ru, rv)] = min(ru, rv)
        label = np.array([find(i) for i in range(nv)])
        tri_label = label[tv[:, 0]]
        tri_vol = np.einsum('ij,ij->i', p0, np.cross(p1, p2)) / 6.0
        boundary_labels = set(int(label[int(k // nv)]) for k in uniq[counts != 2])
        shells, inside = 0, 0
        inside_tris = 0
        for lab in np.unique(tri_label):
            shells += 1
            sel = tri_label == lab
            vol = float(tri_vol[sel].sum())
            verts = np.unique(tv[sel])
            box = wco[verts].max(axis=0) - wco[verts].min(axis=0)
            boxvol = max(float(box[0] * box[1] * box[2]), 1e-12)
            if int(lab) not in boundary_labels and vol < -0.05 * boxvol:
                inside += 1
                inside_tris += int(sel.sum())
        rec['shells'], rec['inside_out_shells'], rec['inside_out_tris'] = shells, inside, inside_tris
        # materials
        slots = list(ob.material_slots)
        rec['material_slots'] = len(slots)
        rec['empty_slots'] = sum(1 for s in slots if s.material is None)
        mi = np.empty(npoly, dtype=np.int32)
        me.polygons.foreach_get('material_index', mi)
        used_slots = sorted(set(int(x) for x in mi))
        rec['faces_on_empty_slot'] = int(sum(int((mi == k).sum()) for k in used_slots if k >= len(slots) or slots[k].material is None))
        mats, missing = [], []
        for s in slots:
            m = s.material
            if m is None:
                continue
            mats.append(m.name)
            if m.use_nodes and m.node_tree:
                for n in m.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image:
                        img = n.image
                        path = bpy.path.abspath(img.filepath) if img.filepath else ''
                        if not img.packed_file and (not path or not os.path.exists(path)) and img.source == 'FILE':
                            missing.append(img.name)
        rec['materials'] = mats
        rec['missing_images'] = sorted(set(missing))
        # uv and colour layers
        rec['uv_layers'] = [u.name for u in me.uv_layers]
        try:
            rec['color_attributes'] = [c.name for c in me.color_attributes]
        except AttributeError:
            rec['color_attributes'] = [c.name for c in me.vertex_colors]
        if me.uv_layers.active and nt:
            uvf = np.empty(nl * 2)
            me.uv_layers.active.uv.foreach_get('vector', uvf)
            uv = uvf.reshape(-1, 2)
            tl = np.empty(nt * 3, dtype=np.int64)
            me.loop_triangles.foreach_get('loops', tl)
            ov, out = uv_overlap(uv, tl.reshape(-1, 3))
            rec['uv_overlap'], rec['uv_outside'] = ov, out
        else:
            rec['uv_overlap'], rec['uv_outside'] = None, None
        # bone influences per vertex (the original mesh: weights are not kept on the evaluated copy)
        groups = ob.vertex_groups
        rec['vertex_groups'] = len(groups)
        if len(groups) and ob.type == 'MESH':
            worst, over4 = 0, 0
            for v in ob.data.vertices:
                k = sum(1 for g in v.groups if g.weight > 0.001)
                worst = max(worst, k)
                if k > 4:
                    over4 += 1
            rec['max_influences'], rec['verts_over_4_influences'] = worst, over4
        rec['armature_modifier'] = any(m.type == 'ARMATURE' for m in ob.modifiers)
        return rec
    finally:
        ev.to_mesh_clear()


def probe_one(path):
    kind = load(path)
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.users_scene]
    meshes = [mesh_stats(o, depsgraph) for o in objs if o.type == 'MESH']
    armatures = [{'name': o.name, 'bones': len(o.data.bones), 'bone_names': [b.name for b in o.data.bones][:200]} for o in objs if o.type == 'ARMATURE']
    actions = []
    for a in bpy.data.actions:
        actions.append({'name': a.name, 'frame_range': [float(a.frame_range[0]), float(a.frame_range[1])]})
    return {'source': path, 'kind': kind, 'file_bytes': os.path.getsize(path), 'blender': bpy.app.version_string,
            'unit_scale': scene.unit_settings.scale_length, 'unit_system': scene.unit_settings.system, 'meshes': meshes, 'armatures': armatures,
            'actions': actions, 'other_objects': sorted(set(o.type for o in objs if o.type not in ('MESH', 'ARMATURE'))),
            'object_names': [o.name for o in objs if o.type == 'MESH']}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    if argv[0] == '--batch':                 # --batch OUTDIR file1 file2 ...  ->  OUTDIR/0.json, 1.json, ...
        outdir = argv[1]
        os.makedirs(outdir, exist_ok=True)
        for i, path in enumerate(argv[2:]):
            rec = probe_one(path)
            with open(os.path.join(outdir, '%d.json' % i), 'w') as fh:
                json.dump(rec, fh)
        print('MODEL_PROBE_OK files=%d' % len(argv[2:]))
        return
    out = probe_one(argv[0])
    with open(argv[1], 'w') as fh:
        json.dump(out, fh)
    print('MODEL_PROBE_OK meshes=%d armatures=%d actions=%d' % (len(out['meshes']), len(out['armatures']), len(out['actions'])))


main()
