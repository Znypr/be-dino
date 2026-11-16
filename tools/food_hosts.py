#!/usr/bin/env python3
"""BD-1238 (docs/241 W6 + W7, part of BD-1208): the V3 food map with every food kind sitting at a MATCHING HOST that already stands in the world.

Input: the committed V3 food map (tools/food_layer_data_v3.py, made by tools/generate_food_layer.py --world v3) and the real World V3 placements in the
playtest profile with the BD-1224 round-bush swap (tools/world_colliders.py dump(world='v3', toon=True): the same pure BiomePlacement grammar Arena.build runs).
Output (only with --write): src/shared/FoodLayerDataV3Hosts.luau + tools/food_layer_data_v3_hosts.py, read by src/shared/FoodLayer.luau instead of
FoodLayerDataV3 while Config.FoodHostsEnabled, WorldV3Enabled and ToonWorldEnabled are all on (the bushes only stand where this map expects them with the
toon swap).

Rules (the same 3,600 foods and kind counts; NO new parts: the hosts are the bushes, trees and rocks the island already has):
  * berries sit round the foot of a round bush (world_bush_a / world_bush_b), just outside its edge so the dome never hides them;
  * fruit lies under a tree crown (canopy, conifer, cycad; not the dead trees), between the trunk and the crown edge, like fallen fruit;
  * amber sits right against a rock (the boulders and the two kit landmarks), so it reads as found in the rock (W7: the rare food near rocks);
  * eggs (the V3 egg mesh is an egg in its own twig nest) nest against a rock or at the foot of a tree trunk: sheltered spots, a find (W7);
  * FAIRNESS: a food only moves to a host in its own zone (the five WorldV3 zone sectors by plain angle around the plaza) and at most REACH studs, so every
    zone keeps exactly its V3 count of every kind and no area empties; a food with no free matching host in reach stays where the V3 map put it;
  * the two starter patches and the four lone hill-top ambers stay exactly where they are (FoodLayer reads the same starter centres);
  * every food stays on valid V3 food ground (GroundV3.ok: dry, not steep, not the plaza, a path or a landmark disc, OBSTACLE_MARGIN clear of every solid
    collider) and at least MIN_SPACING studs from every other food, one food per layer cell; deterministic (no dice at all).

    python tools/food_hosts.py --runner <luau.exe>            # build, print the host shares, compare with the committed files
    python tools/food_hosts.py --runner <luau.exe> --write    # also (re)write the two data files
"""
from pathlib import Path
import argparse
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_food_layers as cmp  # noqa: E402
import food_layer_data_v3  # noqa: E402
import generate_food_layer as gen  # noqa: E402
import worldlayer  # noqa: E402

VERSION = 'bd1238-foodhosts-v3-1'
REACH = {'berry': 30.0, 'fruit': 30.0, 'egg': 45.0, 'amber': 80.0}   # studs: the farthest a food moves to reach its host (the rare kinds travel further to a rock)
MIN_SPACING = 2.8       # studs between two foods (the V3 map rule)
SLOT_STEP = 3.1         # studs between neighbouring slots on one host ring
LONE_CLEAR = 18.0       # a V3 amber with no other food this close is a lone hill-top amber (fixed)
# Hosts per food kind, and how many foods one host carries at most (a bush full of berries, a few fruits under a tree, one or two finds at a rock).
BUSH_IDS = ('world_bush_a', 'world_bush_b')
TREE_PREFIXES = ('world_tree_canopy', 'world_tree_conifer', 'world_tree_cycad')
# (host, food kind): a host takes that food while it carries fewer foods than this (a rock with up to 4 finds, eggs only while it has fewer than 2)
CAP = {('bush', 'berry'): 7, ('tree', 'fruit'): 5, ('rock', 'amber'): 4, ('rock', 'egg'): 2, ('treefoot', 'egg'): 2, ('landmark', 'amber'): 6, ('landmark', 'egg'): 4}
GAP_LIMIT = 23.0        # studs: no walkable spot farther than this from food after the moves (the written V3 rule is 25; the V3 map itself reaches 22.2)
GAP_STEP = 4.0          # studs: the lattice the gap guard checks
GAP_ROUNDS = 400
BUSH_OUT = 0.9          # berries: studs outside the bush footprint (Studio 2026-11-16: inside the rim the dome hid most of them)
TREE_RINGS = (0.38, 0.62)   # fruit: rings at these shares of the crown radius (under the crown)
TREE_FOOT = 2.2         # eggs at a tree: studs outside the trunk collider
ROCK_GAP = 1.7          # amber and eggs at a rock: studs outside the rock footprint
KIND_HOSTS = {'berry': ('bush',), 'fruit': ('tree',), 'amber': ('rock', 'landmark'), 'egg': ('rock', 'treefoot', 'landmark')}
LANDMARK_GAP = 2.5      # studs outside a WorldV3 landmark keep-out disc: the ring of finds round a landmark (W7)
ORDER = ('amber', 'egg', 'fruit', 'berry')   # the rare kinds pick their hosts first
# WorldV3.Zones (src/shared/WorldV3.luau) by plain angle around the plaza; tests check the numbers match.
ZONES = (('meadow', -60.0, 30.0), ('forest', 30.0, 110.0), ('pine', 110.0, 180.0), ('beach', 180.0, 250.0), ('volcano', 250.0, 300.0))

LUAU_PATH = ROOT / 'src' / 'shared' / 'FoodLayerDataV3Hosts.luau'
PY_PATH = ROOT / 'tools' / 'food_layer_data_v3_hosts.py'


def zone_of(centre, x, z):
    a = math.degrees(math.atan2(z - centre[1], x - centre[0]))
    for name, lo, hi in ZONES:
        for shift in (0.0, 360.0, -360.0):
            if lo <= a + shift < hi:
                return name
    return 'meadow'


class Host:
    __slots__ = ('kind', 'x', 'z', 'slots', 'used', 'label')

    def __init__(self, kind, x, z, slots, label):
        self.kind, self.x, self.z, self.slots, self.used, self.label = kind, x, z, slots, 0, label


def ring(cx, cz, rx, rz, yaw, start=0.0):
    """Points on an ellipse (half axes rx, rz in the prop's own frame, turned by yaw like CFrame.Angles(0, yaw, 0)) about SLOT_STEP apart."""
    perimeter = math.pi * (3 * (rx + rz) - math.sqrt((3 * rx + rz) * (rx + 3 * rz)))
    n = max(3, int(perimeter / SLOT_STEP))
    c, s = math.cos(yaw), math.sin(yaw)
    out = []
    for k in range(n):
        t = start + 2 * math.pi * k / n
        lx, lz = math.cos(t) * rx, math.sin(t) * rz
        out.append((cx + c * lx + s * lz, cz - s * lx + c * lz))
    return out


def hosts_from(props, cols, ext, info):
    """Host list from the world_colliders dump (props, kit colliders, kit extents) and the WorldV3 landmark sites (info of GroundV3)."""
    out = []
    for name, lx, lz in info['landmarks']:
        radius = max((r for x, z, r, every in info['keepouts'] if every and math.hypot(x - lx, z - lz) < 0.5), default=34.0) + LANDMARK_GAP
        out.append(Host('landmark', lx, lz, ring(lx, lz, radius, radius, 0.0), name))
    for p in props:
        pid, s = p['id'], p['scale']
        if p['layer'] == 'shrub' and pid in BUSH_IDS:
            e = ext[pid]
            out.append(Host('bush', p['x'], p['z'], ring(p['x'], p['z'], e[1] * s / 2 + BUSH_OUT, e[3] * s / 2 + BUSH_OUT, p['yaw']), pid))
        elif p['layer'] in ('tree', 'colossal') and pid.startswith(TREE_PREFIXES):
            e, trunk = ext[pid], cols.get(pid, [(0, 0, 0, 1, 1, 1, 0)])[0]
            crown = min(e[1], e[3]) * s / 2
            trunk_r = max(trunk[3], trunk[5]) * s / 2
            # the trunk collider is off the pivot a little: rings round the trunk centre
            c, sn = math.cos(p['yaw']), math.sin(p['yaw'])
            tx, tz = p['x'] + c * trunk[0] * s + sn * trunk[2] * s, p['z'] - sn * trunk[0] * s + c * trunk[2] * s
            slots = []
            for k, share in enumerate(TREE_RINGS):
                r = max(trunk_r + gen.OBSTACLE_MARGIN + 0.6, crown * share)
                slots += ring(tx, tz, r, r, 0.0, start=k * 0.5)
            out.append(Host('tree', tx, tz, slots, pid))
            r = trunk_r + TREE_FOOT
            out.append(Host('treefoot', tx, tz, ring(tx, tz, r, r, 0.0, start=0.25), pid))
        elif p['layer'] in ('rock', 'landmark'):
            e = ext[pid]
            out.append(Host('rock', p['x'], p['z'], ring(p['x'], p['z'], e[1] * s / 2 + ROCK_GAP, e[3] * s / 2 + ROCK_GAP, p['yaw']), pid))
    return out


class Spacing:
    def __init__(self):
        self.h = gen.Hash(6.0)

    def free(self, x, z):
        return self.h.nearest(x, z, MIN_SPACING) >= MIN_SPACING

    def add(self, x, z):
        self.h.add(x, z)

    def remove(self, x, z):
        self.h.remove(x, z)


def anchor(v3_points, hosts, ground, layer, info):
    """[(x, z, kind, host kind or None)] in the order of v3_points, plus the moves."""
    centre = info['centre']
    starters = food_layer_data_v3.STARTER_CENTRES
    radius = food_layer_data_v3.STARTER_RADIUS
    fixed = set()
    for i, (x, z, kind) in enumerate(v3_points):
        if any(math.hypot(x - cx, z - cz) <= radius for cx, cz in starters):
            fixed.add(i)
        elif kind == 'amber' and sum(1 for j, (a, b, _) in enumerate(v3_points) if j != i and math.hypot(a - x, b - z) <= LONE_CLEAR) == 0:
            fixed.add(i)
    space = Spacing()
    for i in fixed:
        space.add(*v3_points[i][:2])
    lone = [v3_points[i][:2] for i in fixed if v3_points[i][2] == 'amber' and not any(math.hypot(v3_points[i][0] - cx, v3_points[i][1] - cz) <= radius
                                                                                       for cx, cz in starters)]

    def kept_clear(x, z):
        """No moved food inside a starter patch (or right at its edge) or near a lone hill-top amber: both stay exactly as in the V3 map."""
        return (all(math.hypot(x - cx, z - cz) > radius + MIN_SPACING for cx, cz in starters)
                and all(math.hypot(x - lx, z - lz) > LONE_CLEAR + 0.5 for lx, lz in lone))
    # every slot, snapped to its layer cell, that is valid food ground
    slot_of = {}
    for h_index, host in enumerate(hosts):
        for x, z in host.slots:
            sx, sz = gen.snap(layer, x, z)
            if ground.ok(sx, sz) and kept_clear(sx, sz):
                slot_of.setdefault((host.kind, zone_of(centre, sx, sz)), []).append((sx, sz, h_index))
    out = [None] * len(v3_points)
    host_of = [None] * len(v3_points)
    for i in fixed:
        x, z, kind = v3_points[i]
        out[i] = (x, z, kind, None)
    taken = set()
    for kind in ORDER:
        pairs = []
        for i, (x, z, k) in enumerate(v3_points):
            if k != kind or i in fixed:
                continue
            zone = zone_of(centre, x, z)
            for host_kind in KIND_HOSTS[kind]:
                for sx, sz, h_index in slot_of.get((host_kind, zone), ()):
                    d = math.hypot(sx - x, sz - z)
                    if d <= REACH[kind]:
                        pairs.append((d, i, sx, sz, h_index))
        pairs.sort()
        for d, i, sx, sz, h_index in pairs:
            host = hosts[h_index]
            if out[i] is not None or (sx, sz) in taken or host.used >= CAP[(host.kind, kind)] or not space.free(sx, sz):
                continue
            out[i] = (sx, sz, kind, host.kind)
            host_of[i] = h_index
            taken.add((sx, sz))
            host.used += 1
            space.add(sx, sz)
    # the rest stay at their V3 spot when it is still free, else the nearest free cell of a small fixed spiral round it
    stayed, nudged = 0, 0
    for i, (x, z, kind) in enumerate(v3_points):
        if out[i] is not None:
            continue
        spot = free_near(x, z, space, ground, layer, centre, kept_clear)
        if spot is None:
            raise SystemExit('no free spot near the V3 food at (%.1f, %.1f)' % (x, z))
        out[i] = (spot[0], spot[1], kind, None)
        space.add(*spot)
        stayed += spot == (x, z)
        nudged += spot != (x, z)
    # gap guard: where moving food to its hosts opened a hole (a walkable spot farther than GAP_LIMIT from any food), the moved food that came from
    # nearest that spot goes back to its V3 spot (nearest moved first, worst hole first, until no hole is left)
    reverted = 0
    lattice = ground.lattice(GAP_STEP, 408.0)
    import layer_stats
    for _ in range(GAP_ROUNDS):
        search = layer_stats.Buckets([(p[0], p[1]) for p in out])
        worst = max(((search.nearest(x, z), x, z) for x, z in lattice), default=(0.0, 0.0, 0.0))
        if worst[0] <= GAP_LIMIT:
            break
        _, gx, gz = worst
        movers = sorted((math.hypot(v3_points[i][0] - gx, v3_points[i][1] - gz), i) for i in range(len(out)) if host_of[i] is not None)
        for _, i in movers:
            x, z, kind = v3_points[i]
            space.remove(out[i][0], out[i][1])
            spot = free_near(x, z, space, ground, layer, centre, kept_clear)
            if spot is None:
                space.add(out[i][0], out[i][1])
                continue
            hosts[host_of[i]].used -= 1
            taken.discard((out[i][0], out[i][1]))
            host_of[i] = None
            out[i] = (spot[0], spot[1], kind, None)
            space.add(*spot)
            reverted += 1
            break
        else:
            raise SystemExit('the gap at (%.1f, %.1f) cannot be closed' % (gx, gz))
    else:
        raise SystemExit('the gap guard did not finish in %d rounds' % GAP_ROUNDS)
    return out, {'fixed': len(fixed), 'stayed': stayed, 'nudged': nudged, 'reverted': reverted}


def free_near(x, z, space, ground, layer, centre, kept_clear):
    """(x, z) itself when no food is closer than MIN_SPACING, else the first free valid cell of a fixed spiral round it (same zone), else None."""
    if space.free(x, z):
        return (x, z)
    for k in range(1, 200):
        r = 0.5 + 0.06 * k
        a = k * 2.399963229728653
        nx, nz = gen.snap(layer, x + math.cos(a) * r, z + math.sin(a) * r)
        if zone_of(centre, nx, nz) == zone_of(centre, x, z) and ground.ok(nx, nz) and space.free(nx, nz) and kept_clear(nx, nz):
            return (nx, nz)
    return None


def load_hosts(runner):
    import world_colliders
    props, cols, ext, _hub = world_colliders.dump(runner, world='v3', toon=True)
    obstacles = world_colliders.Obstacles(world_colliders.prop_obstacles(props, cols, ext))
    return props, cols, ext, obstacles


def build(runner):
    import dump_food_layout
    props, cols, ext, obstacles = load_hosts(runner)
    model = dump_food_layout.ground_model(runner, 1.0, 4.0, world='v3')
    ground = gen.GroundV3(model)
    hosts = hosts_from(props, cols, ext, ground.info)
    ground.obstacles = obstacles
    layer0 = worldlayer.decode(food_layer_data_v3.TEXT)
    v3_points = cmp.layer_points(layer0)
    layer = worldlayer.WorldLayer(gen.WIDTH, gen.WIDTH, gen.ARENA)
    points, stats = anchor(v3_points, hosts, ground, layer, ground.info)
    for x, z, kind, _ in points:
        if not layer.set(x, z, gen.KIND_IDS[kind]):
            raise SystemExit('food outside the layer: %r' % ((x, z),))
    if layer.count() != len(points):
        raise SystemExit('two foods share a cell: %d cells for %d foods' % (layer.count(), len(points)))
    return {'layer': layer, 'points': points, 'v3_points': v3_points, 'stats': stats, 'ground': ground, 'hosts': hosts, 'obstacles': obstacles,
            'props': props}


def shares(points):
    out = {}
    for kind in gen.COUNTS:
        sel = [p for p in points if p[2] == kind]
        out[kind] = sum(1 for p in sel if p[3] is not None) / len(sel)
    return out


def gap(points, ground, step=4.0):
    import layer_stats
    search = layer_stats.Buckets([(p[0], p[1]) for p in points])
    dist = sorted(search.nearest(x, z) for x, z in ground.lattice(step, 408.0))
    return dist[-1], dist[int(0.95 * (len(dist) - 1))]


def zone_counts(points, centre):
    out = {}
    for p in points:
        key = (zone_of(centre, p[0], p[1]), p[2])
        out[key] = out.get(key, 0) + 1
    return out


def measure(result):
    ground = result['ground']
    g, p95 = gap(result['points'], ground)
    vg, vp95 = gap(result['v3_points'], ground)
    centre = ground.info['centre']
    zones = {z: sum(v for (zz, _), v in zone_counts(result['points'], centre).items() if zz == z) for z, _, _ in ZONES}
    return {'gap_max': g, 'gap_p95': p95, 'v3_gap_max': vg, 'v3_gap_p95': vp95, 'zones': zones}


def luau_source(layer):
    counts = {k: layer.count(v) for k, v in gen.KIND_IDS.items()}
    return ('--!strict\n'
            '-- GENERATED by tools/food_hosts.py (BD-1238, docs/241 W6 + W7). Do not edit by hand: change the generator, run it with --write and commit both outputs.\n'
            '-- The V3 food map (FoodLayerDataV3) with every food at a matching host that already stands on the island: berries at the rim of the round bushes,\n'
            '-- fruit under the tree crowns, amber against the rocks, eggs (in their own twig nest) against a rock or at a tree foot. Same format (a WorldLayer,\n'
            '-- %d x %d cells, 1 berry, 2 fruit, 3 egg, 4 amber), the same %d foods (%s), the same count of every kind in every zone, the same starter patches.\n'
            '-- Read by src/shared/FoodLayer.luau while Config.FoodHostsEnabled, WorldV3Enabled and ToonWorldEnabled are all true.\n'
            'return table.freeze({\n'
            '    Version = "%s",\n'
            '    Map = [==[\n%s\n]==],\n'
            '})\n') % (gen.WIDTH, gen.WIDTH, sum(counts.values()), ', '.join('%s %d' % kv for kv in counts.items()), VERSION, gen.wrap(layer.encode()))


def python_source(layer):
    text = layer.encode()
    body = '\n'.join('    %r' % text[i:i + 110] for i in range(0, len(text), 110))
    return ('"""GENERATED by tools/food_hosts.py (BD-1238). Do not edit by hand. The same map as src/shared/FoodLayerDataV3Hosts.luau for the Python tools."""\n'
            'VERSION = %r\nTEXT = (\n%s\n)\n') % (VERSION, body)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    ap.add_argument('--write', action='store_true', help='write src/shared/FoodLayerDataV3Hosts.luau and tools/food_layer_data_v3_hosts.py')
    args = ap.parse_args()
    result = build(args.runner)
    pts = result['points']
    moved = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pts, result['v3_points'])]
    print('hosts: %s' % {k: sum(1 for h in result['hosts'] if h.kind == k) for k in ('bush', 'tree', 'treefoot', 'rock', 'landmark')})
    print('at a host: %s' % {k: '%.0f%%' % (v * 100) for k, v in shares(pts).items()})
    print('kept fixed %d, stayed %d, nudged %d, sent back by the gap guard %d; farthest move %.1f studs' % (result['stats']['fixed'], result['stats']['stayed'], result['stats']['nudged'], result['stats']['reverted'], max(moved)))
    m = measure(result)
    print('gap: farthest walkable spot %.1f studs (V3 map %.1f), 95th percentile %.1f (V3 map %.1f)' % (m['gap_max'], m['v3_gap_max'], m['gap_p95'], m['v3_gap_p95']))
    print('per zone: %s' % m['zones'])
    text = result['layer'].encode()
    old = gen.committed_text(LUAU_PATH)
    print('committed map: %s' % ('missing' if old is None else ('identical' if old == text else 'DIFFERENT')))
    if args.write:
        LUAU_PATH.write_text(luau_source(result['layer']), encoding='utf-8', newline='\n')
        PY_PATH.write_text(python_source(result['layer']), encoding='utf-8', newline='\n')
        print('wrote', LUAU_PATH.relative_to(ROOT), 'and', PY_PATH.relative_to(ROOT))
    return 0 if (old == text or args.write) else 1


if __name__ == '__main__':
    sys.exit(main())
