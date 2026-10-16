"""Offline mobile load estimate (BD-321, docs/107). No phone needed; NOT a measurement.

Runs the real placement grammar (IslandLayout + BiomeMap + BiomePlacement, same harness as verify_world_art.py) for the
default and playtest profiles, then does the arithmetic in Python: props/colliders/triangles per biome and kind, the
distance-culling effect (Config.WorldCulling, docs/89) at spawn and at the worst spot of the arena, peak dinos x parts per
dino (legacy vs low-poly), EditableImage MiB (docs/105), particle budgets and combat replication bytes (CombatConfig).
Every constant is tagged in a comment: measured (docs/evidence or a verifier), derived (placement output / source
constants) or ESTIMATE (a stated assumption). Usage: python tools/estimate_world_budget.py --runner luau.exe [--json out.json]
"""
from pathlib import Path
import argparse, json, math, re, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles, verify_world_art as vwa
ROOT = Path(__file__).resolve().parents[1]

# Rules of thumb for a low-end Android phone (NOT Roblox-published limits; tune after the BD-085 measurements).
GUIDANCE = {
    'attached_parts': (3000, 'parts parented and in range'),
    'triangles': (250_000, 'triangles in the scene'),
    'client_memory_mb': (1200, 'total client memory MB on a 3 GB phone'),
    'network_kbs': (30, 'sustained receive KB/s'),
    'particles_live': (300, 'live particles on screen'),
    'lights': (16, 'dynamic lights'),
}
GEN_LOW, GEN_HIGH = 500, 3000  # ESTIMATE: sensitivity range for the generated-mesh triangle count
GEN_TRIS = 1630      # ESTIMATE: a Roblox generate_mesh prop; CaveHubLayout's own provisional average (410,800 tris / 252 props)
WEDGE_TRIS = 8       # ESTIMATE: a WedgePart draws about 8 triangles; legacy dino models are wedge builds
LOWPOLY_PARTS = 7    # docs/105: one MeshPart per body part
LOWPOLY_FACES = 154_660 / 22  # measured, docs/105 s3: 22 species total 154,660 faces
IMG_MIB_PER_DINO = 0.8  # measured, docs/105 s3 (12 distinct dinos = 9.75 MiB)
PLAYERS, SPAWN, HALF = 12, (0, 30), 416  # HALF = Config.ArenaHalfWidth (260 x 1.6), asserted by verify_world_art
HP_UPDATE_BYTES = 24  # ESTIMATE: one SetAttribute("HpByte") replication (name + byte + instance ref + framing)


def num(text, key):
    return float(re.search(r'\b' + re.escape(key) + r'\s*=\s*([0-9.]+)', text).group(1))


DUMP = r'''
for _,p in a do print(string.format("P %s %s %.2f %.2f %s",p.layer,p.id,p.x,p.z,p.biome)) end
for id,d in Kit do
 local gen=(Generated.KitMap[id]~=nil or Generated.BareIds[id]~=nil)
 print(string.format("K %s %d %d %d",id,d.triangles,#d.colliders,if gen then 1 else 0))
end
'''


def luau_script(cfg_text, density_from_config):
    head = vwa.script(False, cfg_text, False)
    pre = head[:head.index('local PLAYTEST=')]
    pre += 'local Generated=' + vwa.wrapped('src/shared/WorldGeneratedMeshes.luau') + '\n'
    pre += 'local DENSITY=%s\n' % ('Config.WorldArtDensity' if density_from_config else '1')
    pre += ('local a=Biome.generate({seed=Config.WorldArtSeed,density=DENSITY,extent=Config.ArenaHalfWidth,height=Layout.height,'
            'kit=Kit,meshes=Meshes,map=BiomeMap,layout=Layout})\n')
    return pre + DUMP


def run_profile(runner, name):
    text = (ROOT / 'src/shared/Config.luau').read_text()
    cfg = release_profiles.apply_profile(text, 'playtest')[0] if name == 'playtest' else text
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'est.luau'
        p.write_text(luau_script(cfg, name == 'playtest'))
        out = subprocess.run([runner, str(p)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-1500:] + out.stderr)
    props, kit = [], {}
    for l in out.stdout.splitlines():
        f = l.split()
        if not f:
            continue
        if f[0] == 'P':
            props.append(dict(layer=f[1], id=f[2], x=float(f[3]), z=float(f[4]), biome=f[5]))
        elif f[0] == 'K':
            kit[f[1]] = dict(tris=int(f[2]), colliders=int(f[3]), gen=f[4] == '1')
    return props, kit, cfg


def tris_of(p, kit):
    k = kit[p['id']]
    return GEN_TRIS if k['gen'] else k['tris']  # all kit ids are MeshParts now (verify_world_art asserts it)


def culling(props, kit, radius, budget, hyst, centre):
    """(props in the keep radius, kept after the part budget, triangles at GEN_TRIS, generated-mesh props kept, non-generated tris)."""
    r2 = (radius * hyst) ** 2
    order = sorted((((p['x'] - centre[0]) ** 2 + (p['z'] - centre[1]) ** 2), i) for i, p in enumerate(props))
    inside = [i for d, i in order if d <= r2]
    within, kept = len(inside), inside[:budget]
    gen = sum(1 for i in kept if kit[props[i]['id']]['gen'])
    fixed = sum(kit[props[i]['id']]['tris'] for i in kept if not kit[props[i]['id']]['gen'])  # measured kit meshes
    return within, len(kept), fixed + gen * GEN_TRIS, gen, fixed


def estimate(runner):
    ctext = (ROOT / 'src/shared/Config.luau').read_text()
    cull = {}
    for c in ('Phone', 'Tablet', 'Desktop'):
        seg = ctext[ctext.index(c + ' = {radius'):]
        cull[c] = dict(radius=int(num(seg, 'radius')), budget=int(num(seg, 'budget')))
    hyst, food_factor = num(ctext, 'Hysteresis'), num(ctext, 'FoodRadiusFactor')
    food_parts = int(num(ctext, 'FoodSectorCount')) ** 2 * int(num(ctext, 'FoodClusterItems'))
    area = (2 * HALF) ** 2
    res = dict(guidance={k: v[0] for k, v in GUIDANCE.items()}, cull=cull, hysteresis=hyst, food_parts=food_parts, profiles={})
    for name in ('default', 'playtest'):
        props, kit, cfg = run_profile(runner, name)
        P = dict(kit_on='WorldArtMode = "BiomeKit"' in cfg, placements=len(props), by_kind={}, by_biome={})
        for p in props:
            for key, d in (('by_kind', p['layer']), ('by_biome', p['biome'])):
                row = P[key].setdefault(d, dict(props=0, colliders=0, tris=0, gen=0))
                row['props'] += 1
                row['colliders'] += kit[p['id']]['colliders']
                row['tris'] += tris_of(p, kit)
                row['gen'] += kit[p['id']]['gen']
        P['mesh_parts'] = len(props)
        P['collider_parts'] = sum(r['colliders'] for r in P['by_kind'].values())
        P['tris_total'] = sum(r['tris'] for r in P['by_kind'].values())
        P['gen_props'] = sum(r['gen'] for r in P['by_kind'].values())
        P['kit_parts_total'] = P['mesh_parts'] + P['collider_parts']
        P['cull'] = {}
        for cls, c in cull.items():
            spawn = culling(props, kit, c['radius'], c['budget'], hyst, SPAWN)
            worst, wc = (0, 0, 0), SPAWN
            for gx in range(-HALF, HALF + 1, 64):
                for gz in range(-HALF, HALF + 1, 64):
                    r = culling(props, kit, c['radius'], c['budget'], hyst, (gx, gz))
                    if r[1] > worst[1]:
                        worst, wc = r, (gx, gz)
            food_in = min(food_parts, round(food_parts * math.pi * (c['radius'] * food_factor) ** 2 / area))
            P['cull'][cls] = dict(spawn=spawn, worst=worst, worst_at=wc, food_visible=food_in)
        if not P['kit_on']:
            lw, lf, per = vwa.legacy_parts()
            P['legacy_props_parts'], P['legacy_food_parts'], P['legacy_per'] = lw, lf, per
        res['profiles'][name] = P
    legacy = {n: len(re.findall(r'<Item class="(?:Wedge|Mesh)?Part"', (ROOT / 'resources/roblox' / (n + '.rbxmx')).read_text(errors='ignore')))
              for n in ('compy', 'raptor', 'stegosaurus', 'ankylosaurus', 'triceratops', 'tyrannosaurus')}
    nt = (ROOT / 'src/shared/NpcPredatorRules.luau').read_text()
    npcs = min(int(num(nt, 'MaxNpcs')), int(num(nt, 'MinNpcs')) + (PLAYERS - 1) // int(num(nt, 'PlayersPerExtraNpc')))
    dinos = PLAYERS + npcs
    lt = (ROOT / 'src/shared/LowPolyTexture.luau').read_text()
    big, small = int(num(lt, 'Texture.BigCap')), int(num(lt, 'Texture.SmallCap'))
    distinct = min(big // 2, small // 5)
    res['dinos'] = dict(players=PLAYERS, npcs=npcs, dinos=dinos, legacy_parts_per=legacy,
                        legacy_parts_peak=[min(legacy.values()) * dinos, max(legacy.values()) * dinos],
                        legacy_tris_peak=[min(legacy.values()) * dinos * WEDGE_TRIS, max(legacy.values()) * dinos * WEDGE_TRIS],
                        low_parts_peak=LOWPOLY_PARTS * dinos, low_tris_peak=round(LOWPOLY_FACES * dinos),
                        distinct_cap=distinct, img_mib_cap=round(distinct * IMG_MIB_PER_DINO, 2), img_mib_12=round(12 * IMG_MIB_PER_DINO, 2))
    # per second: cave docs/104 (25 desktop / 10 phone); cosmetics = ESTIMATE (aura 8..12/s from CosmeticEffects, trail guessed 20/s)
    res['particles'] = dict(cave_desktop=25, cave_phone=10, aura_per_dino=12, trail_per_dino=20, cosmetics_peak=dinos * 32,
                            weather_concurrent_cap=6000, weather_phone_density=.5)
    # whole phone scene at the worst arena spot (Phone class): culled props + all colliders + visible food + dinos + the rest
    RESIDUAL = 600  # derived: verify_world_art RESIDUAL_PARTS (hub, boundary, arch, spring, rigs)
    for n, P in res['profiles'].items():
        w = P['cull']['Phone']
        kit_parts = w['worst'][1] + P['collider_parts'] if P['kit_on'] else None
        P['join_parts'] = (P['kit_parts_total'] if P['kit_on'] else P['legacy_props_parts']) + (food_parts if P['kit_on'] else P['legacy_food_parts']) + RESIDUAL
        P['phone_scene'] = dict(
            world_parts_lowpoly=(w['worst'][1] + P['collider_parts'] + w['food_visible'] + RESIDUAL + res['dinos']['low_parts_peak']) if P['kit_on'] else None,
            world_tris_low=(w['worst'][4] + w['worst'][3] * GEN_LOW) if P['kit_on'] else None,
            world_tris_mid=w['worst'][2] if P['kit_on'] else None,
            world_tris_high=(w['worst'][4] + w['worst'][3] * GEN_HIGH) if P['kit_on'] else None)
    cc = (ROOT / 'src/shared/CombatConfig.luau').read_text()
    hz = num(cc, 'HpSendHz')
    res['combat'] = dict(hz=hz, tick=num(cc, 'TickHz'), bytes_per_update=HP_UPDATE_BYTES, combatants=dinos,
                         worst_kbs=round(dinos * hz * HP_UPDATE_BYTES / 1000, 2), typical_kbs=round(6 * hz * HP_UPDATE_BYTES / 1000, 2))
    return res


def table(res):
    L = ['| Profile / biome | props | colliders | tris (est) |', '|---|---:|---:|---:|']
    for prof in ('default', 'playtest'):
        P = res['profiles'][prof]
        for b, r in sorted(P['by_biome'].items()):
            L.append(f"| {prof} / {b} | {r['props']} | {r['colliders']} | {r['tris']:,} |")
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    vwa.static_checks()
    res = estimate(a.runner)
    print(table(res))
    for n, P in res['profiles'].items():
        print(f"\n[{n}] kit_on={P['kit_on']} mesh_parts={P['mesh_parts']} colliders={P['collider_parts']} tris~{P['tris_total']:,} generated-mesh props={P['gen_props']}")
        for k, r in sorted(P['by_kind'].items()):
            print(f"   {k:12s} props {r['props']:5d} colliders {r['colliders']:4d} tris {r['tris']:,}")
        for c, r in P['cull'].items():
            print(f"   cull {c:8s} spawn(within,kept,tris)={r['spawn']} worst={r['worst']} at {r['worst_at']} food visible ~{r['food_visible']}")
        if not P['kit_on']:
            print(f"   legacy world props ~{P['legacy_props_parts']:,} parts, legacy food ~{P['legacy_food_parts']:,}")
    for n, P in res['profiles'].items():
        print(f"[{n}] parts loaded at join ~{P['join_parts']:,}; phone worst-spot scene {P['phone_scene']}")
    for k in ('dinos', 'particles', 'combat'):
        print(k, json.dumps(res[k]))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
