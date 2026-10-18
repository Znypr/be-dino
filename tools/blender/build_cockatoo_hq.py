"""Cockatoo HQ test model builder (BD-621). exec() inside Blender. Creature faces +Y, Z up, 1 unit = 1 stud.
All dimensions come from the turnaround sheet (docs/reference/cockatoo-turnaround-chatgpt-v1.png) at 113 px per stud (read off a stud grid
laid over the sheet, see docs/evidence/2026-10-18-cockatoo-blender/README.md).
"""
exec(open(ROOT + "/tools/blender/cockatoo_lib.py", encoding="utf8").read())

V = Vector
HEAD_C = V((0, 0.72, 5.30))
EYE_C = V((0.64, 1.0, 5.20))
EYE_AXIS = V((0.62, 0.78, 0.05)).normalized()

# joints (model space, studs): the origin of every exported part
JOINTS = {
    "Body": V((0, 0.30, 1.9)),
    "Head": V((0, 0.62, 4.5)),
    "Crest": V((0, 0.20, 5.6)),
    "Tail": V((0, -0.65, 3.0)),
    "ArmR": V((1.0, 0.62, 3.4)),
    "ArmL": V((-1.0, 0.62, 3.4)),
    "LegR": V((0.55, 0.0, 1.55)),
    "LegL": V((-0.55, 0.0, 1.55)),
    "FootR": V((0.55, 0.0, 0.62)),
    "FootL": V((-0.55, 0.0, 0.62)),
}


def mirrored(part, name):
    """Return a new Part that is the X-mirror of `part` (faces re-wound)."""
    q = Part(name)
    vmap = {}
    part.bm.verts.index_update()
    for v in part.bm.verts:
        vmap[v.index] = q.vert(V((-v.co.x, v.co.y, v.co.z)))
    part.bm.verts.ensure_lookup_table()
    for f in part.bm.faces:
        vs = [vmap[v.index] for v in f.verts]
        cols = [lo[part.col] for lo in f.loops]
        q.face(vs[::-1], cols[::-1])
    return q


# ---------------------------------------------------------------- body (torso + neck)
def build_body(feathers=True):
    p = Part("Body")
    spine = [V((0, 0.15, 1.15)), V((0, 0.2, 1.8)), V((0, 0.32, 2.6)), V((0, 0.5, 3.4)), V((0, 0.62, 4.05)), V((0, 0.75, 4.75))]
    rx = [0.50, 0.76, 0.80, 0.76, 0.62, 0.58]
    ry = [0.56, 0.80, 0.92, 0.80, 0.60, 0.56]
    tube = Tube(spine, rx, ry, side=V((1, 0, 0)), samples=28)
    tube_surface(p, tube, segs=12, rings=12, color=CREAM_SH, shrink=0.94, cap_start=True, cap_end=True)
    if feathers:
        tot = tube.total()
        rng = random.Random(11)

        def cfn(t, th):
            sh = 0.45 + 0.55 * max(0.0, math.sin(th))  # chest/front brighter, back slightly darker
            c = mix(CREAM_SH, CREAM, sh)
            return (c, c, 0.0)

        def lenfn(t, th):
            return 0.46 - 0.12 * max(0.0, (t - 0.65) / 0.35)

        def wfn(t):
            return 0.34 - 0.06 * max(0.0, (t - 0.65) / 0.35)

        nrows = round((tot - 0.02) / 0.155)
        feather_rows(p, tube, 0.02, tot, (tot - 0.02) / nrows, 0.34, 0.46, flow=-1, tilt=0.4, curl=0.1, jitter=0.5, cfn=cfn, rng=rng, lenfn=lenfn, wfn=wfn)
    return p, tube


# ---------------------------------------------------------------- head, beak, eyes
def build_head(feathers=True):
    p = Part("Head")
    spine = [V((0, -0.42, 5.26)), V((0, -0.2, 5.28)), V((0, 0.45, 5.38)), V((0, 1.0, 5.34)), V((0, 1.42, 5.2)), V((0, 1.56, 5.12))]
    rx = [0.12, 0.6, 0.94, 0.90, 0.56, 0.2]
    ry = [0.12, 0.62, 0.92, 0.86, 0.56, 0.2]
    tube = Tube(spine, rx, ry, side=V((-1, 0, 0)), samples=20)
    tube_surface(p, tube, segs=12, rings=8, color=CREAM, shrink=0.95)
    eyes = [V((sx * EYE_C.x, EYE_C.y, EYE_C.z)) for sx in (1, -1)]
    if feathers:
        rng = random.Random(5)

        def skip(pos, nrm, t, th):
            for e in eyes:
                if (pos - e).length < 0.34:
                    return True
            return False

        def lenfn(t, th):
            return 0.42 - 0.2 * t

        def wfn(t):
            return 0.28 - 0.06 * t

        tot = tube.total()
        feather_rows(p, tube, 0.0, 0.66 * tot, 0.14, 0.28, 0.4, flow=-1, tilt=0.35, curl=0.12, jitter=0.4, cfn=lambda t, th: (CREAM, CREAM, 0.0), rng=rng,
                     skipfn=skip, lenfn=lenfn, wfn=wfn, profile=PROFILE_SHORT)
        # back of the head: small feathers laid forward over the rear dome (the crest hides the seam)
        feather_rows(p, tube, 0.04, 0.3, 0.1, 0.22, 0.26, flow=1, tilt=0.3, curl=0.1, jitter=0.3, cfn=lambda t, th: (CREAM, CREAM, 0.0), rng=rng, profile=PROFILE_SHORT)
        # face: small feathers close to the beak (denser, shorter), nothing on the eyelid area
        feather_rows(p, tube, 0.66 * tot + 0.1, tot - 0.03, 0.1, 0.2, 0.22, flow=-1, tilt=0.3, curl=0.1, jitter=0.3, cfn=lambda t, th: (CREAM, CREAM, 0.0), rng=rng,
                     skipfn=lambda pos, nrm, t, th: skip(pos, nrm, t, th), lenfn=lambda t, th: 0.2, wfn=lambda t: 0.19, profile=PROFILE_SHORT)
    # eyes: dark rim, brown iris, black pupil, white glints (real geometry, flat vertex colours per band)
    for sx in (1, -1):
        c = V((sx * EYE_C.x, EYE_C.y, EYE_C.z))
        ax = V((sx * EYE_AXIS.x, EYE_AXIS.y, EYE_AXIS.z))
        eye_dome(p, c, ax, 0.31, [0, 21, 34, 47, 58, 72, 90], [EYE_PUPIL, EYE_IRIS, EYE_IRIS2, EYE_IRIS3, EYE_RIM, EYE_RIM], segs=14)
        z = ax
        x = V((0, 0, 1)).cross(z).normalized()
        y = z.cross(x).normalized()
        g = c + ax * 0.255 + y * 0.12 + x * 0.09 * sx
        eye_dome(p, g, ax, 0.075, [0, 40, 90], [EYE_GLINT, EYE_GLINT], segs=6)
        g2 = c + ax * 0.285 - y * 0.10 - x * 0.08 * sx
        eye_dome(p, g2, ax, 0.04, [0, 40, 90], [EYE_GLINT, EYE_GLINT], segs=5)
    # beak: upper hook + small lower bill
    ub = Tube([V((0, 1.15, 5.10)), V((0, 1.50, 5.02)), V((0, 1.84, 4.78)), V((0, 2.00, 4.36))], [0.34, 0.31, 0.19, 0.03], [0.36, 0.36, 0.25, 0.03], side=V((1, 0, 0)), samples=14)
    tube_surface(p, ub, segs=8, rings=7, shrink=1.0, colorfn=lambda t, th: mix(BEAK, BEAK_TIP, (t - 0.6) / 0.4), cap_start=False)
    lb = Tube([V((0, 1.18, 4.90)), V((0, 1.50, 4.80)), V((0, 1.75, 4.64))], [0.26, 0.19, 0.05], [0.16, 0.14, 0.05], side=V((1, 0, 0)), samples=8)
    tube_surface(p, lb, segs=6, rings=4, shrink=1.0, colorfn=lambda t, th: BEAK, cap_start=False)
    return p


# ---------------------------------------------------------------- crest
def build_crest():
    """A ruff of long yellow blades radiating back from the nape (a halo seen from behind, a swept fan seen from the side) + a white forehead tuft."""
    p = Part("Crest")
    C = V((0, 0.05, 5.5))
    items = []
    for i, rho in enumerate(range(-110, 111, 20)):  # roll around the Y axis (0 = straight up, +-180 = down)
        L = 1.85 - 0.55 * abs(rho) / 110
        items.append((rho, 30 + 8 * (abs(rho) > 110), L, 0.52, 0, i))
    for i, rho in enumerate(range(-90, 91, 30)):
        items.append((rho + 10, 40, 1.45 - 0.35 * abs(rho) / 90, 0.48, 1, i))
    for rho, al, L, W, layer, i in items:
        r = math.radians(rho)
        a = math.radians(al)
        rad = V((math.sin(r), 0, math.cos(r)))
        d = V((rad.x * math.sin(a), -math.cos(a), rad.z * math.sin(a)))
        base = C + rad * (0.55 - 0.1 * layer) + V((0, -0.05 * layer, 0))
        nrm = V((0, 1, 0)) + d * 0.9 + V((0.35 * (1 if i % 2 else -1), 0, 0))
        feather(p, base, d, nrm, L, W, tilt=0.0, curl=0.0, cup=0.3, profile=PROFILE_LEAF, c0=mix(CREAM, YELLOW_PALE, 0.85), c1=YELLOW, tip_from=0.3,
                flick=V((rad.x * 0.12, 0.0, 0.2 * max(0.0, 1 - abs(rho) / 150))))
    # small white forehead tuft pointing up and back
    for i, (L, up) in enumerate(((0.75, 0.9), (0.6, 0.7), (0.5, 0.5))):
        d = V((0, -0.3 - 0.25 * i, up)).normalized()
        feather(p, V((0, 1.05 - 0.2 * i, 6.0 - 0.04 * i)), d, V((0, 1, 0.4)), L, 0.34, tilt=0.0, curl=-0.1, profile=PROFILE_BLADE, c0=CREAM, c1=CREAM)
    return p


# ---------------------------------------------------------------- arms / wings (right side, mirrored for left)
def build_arm_r(feathers=True):
    p = Part("ArmR")
    spine = [V((0.95, 0.62, 3.8)), V((1.0, 0.6, 3.55)), V((1.12, 0.48, 2.95)), V((1.12, 0.45, 2.5)), V((1.02, 0.85, 2.08)), V((0.98, 1.05, 1.96))]
    rx = [0.08, 0.32, 0.34, 0.30, 0.22, 0.13]
    ry = [0.08, 0.40, 0.44, 0.36, 0.26, 0.13]
    tube = Tube(spine, rx, ry, side=V((1, 0, 0)), samples=18)
    tube_surface(p, tube, segs=8, rings=8, color=CREAM_SH, shrink=0.93)
    tot = tube.total()
    rng = random.Random(21)

    def cfn(t, th):
        if t > 0.35:
            return (CREAM, YELLOW, 0.45)
        return (CREAM, CREAM, 0.0)

    feather_rows(p, tube, 0.04, tot - 0.1, 0.16, 0.32, 0.42, flow=1, tilt=0.4, curl=0.12, jitter=0.5, cfn=cfn, rng=rng,
                 lenfn=lambda t, th: 0.46 if t < 0.6 else 0.38, wfn=lambda t: 0.34)
    # three black claws from the hand, curving down
    hc = spine[-1]
    for i in range(3):
        base = hc + V((-0.13 + 0.13 * i, 0.04, -0.03))
        cone_claw(p, base, V((0.12 * (i - 1), 0.62, -0.5)), V((0, -0.2, -1)), 0.5, 0.08, 0.35)
    return p


# ---------------------------------------------------------------- tail (fan of cream blades with yellow tips)
def build_tail():
    p = Part("Tail")
    base = V((0, -0.7, 3.0))
    core = Tube([V((0, -0.4, 3.0)), V((0, -0.7, 2.98)), V((0, -0.95, 2.95))], [0.46, 0.36, 0.2], [0.42, 0.3, 0.16], side=V((1, 0, 0)), samples=6)
    tube_surface(p, core, segs=8, rings=4, color=CREAM, shrink=0.95)
    feather_rows(p, core, 0.0, core.total(), 0.16, 0.3, 0.4, flow=-1, tilt=0.35, curl=0.1, jitter=0.3, cfn=lambda t, th: (CREAM, CREAM, 0.0), rng=random.Random(2))
    rng = random.Random(8)
    # fan in the vertical plane (as in the side view of the sheet): elevation +8 .. -42 degrees; three yaw layers so it reads full from behind too
    for k, yaw0 in enumerate((0, -16, 16)):
        n = 8 if k == 0 else 6
        for i in range(n):
            u = i / (n - 1)
            e = math.radians(10 - 52 * u - (4 if k else 0))
            psi = math.radians(yaw0 + (u - 0.5) * 8)
            d = V((math.sin(psi) * math.cos(e), -math.cos(psi) * math.cos(e), math.sin(e)))
            Lb = (1.9 - 0.15 * abs(u - 0.4)) * (1 - 0.06 * k) * (1 + 0.05 * (rng.random() - 0.5))
            nrm = V((1 if yaw0 >= 0 else -1, 0, 0.25 * (1 if i % 2 else -1)))
            if yaw0 == 0:
                nrm = V((1 if i % 2 else -1, 0, 0.1))
            feather(p, base + V((yaw0 * 0.006, -0.02 * k, 0.0)), d, nrm, Lb, 0.5, tilt=0.0, curl=-0.14, cup=0.28, profile=PROFILE_LEAF, c0=CREAM, c1=YELLOW, tip_from=0.42)
    return p


# ---------------------------------------------------------------- legs (hip pivot) + feet (ankle pivot)
def build_leg_r(feathers=True):
    p = Part("LegR")
    hx = 0.55
    thigh = Tube([V((hx, 0.0, 1.95)), V((hx, 0.0, 1.55)), V((hx, 0.0, 1.2))], [0.46, 0.38, 0.28], [0.5, 0.42, 0.3], side=V((1, 0, 0)), samples=8)
    tube_surface(p, thigh, segs=8, rings=5, color=CREAM_SH, shrink=0.93)
    if feathers:
        feather_rows(p, thigh, 0.0, thigh.total() - 0.05, 0.16, 0.3, 0.38, flow=1, tilt=0.4, curl=0.1, jitter=0.4, cfn=lambda t, th: (CREAM, CREAM, 0.0), rng=random.Random(31),
                     profile=PROFILE_ROUND)
    # scaly tarsus: stacked rings with a bulge per scale plate
    zs = [1.22 - i * 0.056 for i in range(14)]
    rows = []
    for i, z in enumerate(zs):
        r = 0.2 - 0.02 * (i / 13) + (0.035 if i % 2 == 0 else 0.0)
        col = SCALE if i % 2 == 0 else SCALE_DK
        rows.append([(V((hx + r * math.cos(2 * math.pi * j / 8), 0.0 + r * 1.0 * math.sin(2 * math.pi * j / 8), z)), col) for j in range(8)])
    grid_strip(p, rows, cols_closed=True)
    return p


def build_foot_r():
    p = Part("FootR")
    hx = 0.55
    ank = V((hx, 0.0, 0.62))
    sphere(p, ank + V((0, 0, -0.04)), V((0.24, 0.26, 0.16)), lambda d: SCALE, segs=8, rings=4)
    toes = [(0.0, 1.30, 0.62), (math.radians(34), 1.05, 0.58), (-math.radians(34), 1.05, 0.58)]
    for yaw, L, claw in toes:
        d = V((-math.sin(yaw) * 1.0, math.cos(yaw), 0.0))
        pts = [ank + V((0, 0, -0.1)), ank + d * 0.35 + V((0, 0, -0.34)), ank + d * (L * 0.68) + V((0, 0, -0.42)), ank + d * L + V((0, 0, -0.43))]
        tb = Tube(pts, [0.25, 0.23, 0.19, 0.16], [0.21, 0.19, 0.16, 0.14], side=V((1, 0, 0)) if abs(d.x) < 0.8 else V((0, 1, 0)), samples=10)
        tube_surface(p, tb, segs=6, rings=6, colorfn=lambda t, th: SCALE if int(t * 6) % 2 == 0 else SCALE_DK, cap_start=False)
        tip = pts[-1]
        cone_claw(p, tip, d + V((0, 0, -0.25)), V((0, 0, -1)), claw * 0.65, 0.13, 0.4)
    d = V((0, -1, 0))
    pts = [ank + V((0, 0, -0.12)), ank + d * 0.22 + V((0, 0, -0.36)), ank + d * 0.5 + V((0, 0, -0.43))]
    tb = Tube(pts, [0.19, 0.17, 0.14], [0.16, 0.15, 0.13], side=V((1, 0, 0)), samples=6)
    tube_surface(p, tb, segs=6, rings=4, colorfn=lambda t, th: SCALE, cap_start=False)
    cone_claw(p, pts[-1], d + V((0, 0, -0.25)), V((0, 0, -1)), 0.42, 0.095, 0.4)
    return p


# ---------------------------------------------------------------- assembling
def set_pivot(ob, pivot):
    ob.data.transform(Matrix.Translation(-pivot))
    ob.location = pivot
    ob.data.update()


def build_all(feathers=True, finish=True):
    wipe_scene()
    setup_render()
    coll = bpy.data.collections.get("Cockatoo") or bpy.data.collections.new("Cockatoo")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    mat = make_material()
    parts = {}
    body, _ = build_body(feathers)
    parts["Body"] = body
    parts["Head"] = build_head(feathers)
    parts["Crest"] = build_crest()
    parts["Tail"] = build_tail()
    arm = build_arm_r(feathers)
    parts["ArmR"] = arm
    parts["ArmL"] = mirrored(arm, "ArmL")
    leg = build_leg_r(feathers)
    parts["LegR"] = leg
    parts["LegL"] = mirrored(leg, "LegL")
    foot = build_foot_r()
    parts["FootR"] = foot
    parts["FootL"] = mirrored(foot, "FootL")
    objs = {}
    for name, part in parts.items():
        ob = part.to_object(coll)
        ob.data.materials.append(mat)
        if finish:
            set_pivot(ob, JOINTS[name])
        objs[name] = ob
    return objs


def report(objs):
    tot = 0
    for n, ob in objs.items():
        t = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        tot += t
        print(n, t)
    print("TOTAL", tot)
