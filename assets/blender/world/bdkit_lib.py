# Be Dino! world kit v2 modelling helpers (run inside Blender: exec(open(path).read())).
# Geometry is built shape by shape (lathe profiles, tubes, blobs) and painted with smooth vertex colours.
import bpy, bmesh, math, random
from mathutils import Vector, noise

def lin(h):
    h = h.lstrip('#'); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    return (f(r), f(g), f(b))

def vc_material():
    m = bpy.data.materials.get('BD2_vc') or bpy.data.materials.new('BD2_vc'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    a = nt.nodes.new('ShaderNodeVertexColor'); a.layer_name = 'Col'
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = .8
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(a.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], o.inputs[0]); return m
M = vc_material()

def lathe(profile, seg=12, amp=0, seed=0, squash=(1, 1, 1), close=True):
    bm = bmesh.new(); rows = []
    for (r, z) in profile:
        rows.append([bm.verts.new((math.cos(2 * math.pi * i / seg) * r * squash[0], math.sin(2 * math.pi * i / seg) * r * squash[1], z * squash[2])) for i in range(seg)])
    for k in range(len(rows) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            try: bm.faces.new((rows[k][i], rows[k][j], rows[k + 1][j], rows[k + 1][i]))
            except ValueError: pass
    if close:
        for idx in (0, -1):
            if profile[idx][0] > 1e-4:
                try: bm.faces.new(rows[idx] if idx == 0 else rows[idx][::-1])
                except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    if amp:
        for v in bm.verts:
            n = noise.noise(v.co * 2.3 + Vector((seed, seed * 1.7, seed * .3))); d = Vector((v.co.x, v.co.y, 0))
            if d.length > 1e-4: v.co += d.normalized() * n * amp
    return bm

def blob(r, loc, seg=10, ring=7, squash=(1, 1, 1), amp=.02, seed=0, dimple=0.0):
    prof = [(0, -r)]
    for k in range(1, ring):
        a = math.pi * k / ring; rr = r * math.sin(a); zz = -r * math.cos(a)
        if k == ring - 1 and dimple: zz -= dimple * .6
        prof.append((rr, zz))
    prof.append((0, r - dimple))
    bm = lathe(prof, seg, amp, seed, squash); bmesh.ops.translate(bm, vec=loc, verts=bm.verts); return bm

def tube(pts, r0, r1, seg=6):
    bm = bmesh.new(); rows = []
    for k, p in enumerate(pts):
        t = k / (len(pts) - 1); r = r0 + (r1 - r0) * t
        rows.append([bm.verts.new((p[0] + math.cos(2 * math.pi * i / seg) * r, p[1] + math.sin(2 * math.pi * i / seg) * r, p[2])) for i in range(seg)])
    for k in range(len(rows) - 1):
        for i in range(seg):
            j = (i + 1) % seg; bm.faces.new((rows[k][i], rows[k][j], rows[k + 1][j], rows[k + 1][i]))
    bm.faces.new(rows[-1][::-1]); return bm

def leaf_blade(l, w, droop=0.0, curl=0.0):
    """pointed leaf lying in XY, tip along +Y, optional droop (tip down) and curl (edges up)"""
    bm = bmesh.new()
    P = [(0, 0, 0), (-w, l * .3, curl), (w, l * .3, curl), (-w * .8, l * .65, curl * .6 - droop * .4), (w * .8, l * .65, curl * .6 - droop * .4), (0, l, -droop), (0, l * .35, -curl * .5)]
    v = [bm.verts.new(p) for p in P]
    bm.faces.new((v[0], v[6], v[1])); bm.faces.new((v[0], v[2], v[6]))
    bm.faces.new((v[6], v[3], v[1])); bm.faces.new((v[6], v[2], v[4])); bm.faces.new((v[6], v[4], v[3]))
    bm.faces.new((v[3], v[4], v[5]))
    return bm

def obj(col, bm, name, loc=(0, 0, 0), rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); o.location = loc; o.rotation_euler = rot
    for p in me.polygons: p.use_smooth = True
    me.materials.append(M); return o

def shade(o, top, bottom, jit=.05, seed=0, hi=None):
    me = o.data; ca = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    t, b = lin(top), lin(bottom)
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]; n = v.normal
            k = max(0, min(1, n.z * .5 + .5)) ** 1.15; k = k * .88 + .06
            nn = noise.noise(v.co * 2.2 + Vector((seed, 0, 0))) * jit
            c = [b[i] + (t[i] - b[i]) * k + nn for i in range(3)]
            if hi:
                d = (v.co - Vector(hi[0])).length
                if d < hi[1]:
                    kk = ((1 - d / hi[1]) ** 1.5) * .55; h = lin(hi[2]); c = [c[i] + (h[i] - c[i]) * kk for i in range(3)]
            ca.data[li].color = (*[max(0, min(1, x)) for x in c], 1)

def join(objs, name, loc):
    for s in bpy.context.selected_objects: s.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join()
    o = bpy.context.active_object; o.name = name; o.data.name = name; o.location = loc; return o

def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

def surface_z(prof, r):
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if r0 <= r <= r1: return z0 + (z1 - z0) * (r - r0) / (r1 - r0 + 1e-9)
    return prof[-1][1]
