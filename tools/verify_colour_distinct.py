"""BD-1037: unit tests of tools/colour_distinct.py and the real egg colour table. No Luau runner needed.

Proves: the distance maths is right (published CIEDE2000 test pairs), colour-blindness simulation keeps greys and white, the blend is the
game's own Lerp, and the REAL table in ProgressionConfig.luau obeys the limits in the tool: no new pair is closer than the documented
limits (pairs made only of the nine pre-BD-1037 colours are LEGACY and listed, never rewritten), every tier has 2 to 4 colours (Legendary
1 to 2), ids are unique and the nine old ones are untouched.
Run: python tools/verify_colour_distinct.py
"""
from pathlib import Path
import math, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import colour_distinct as cd

# Frozen on 2026-10-18: ids, names, tiers and rgb of the nine colours that shipped before BD-1037. They must never change.
LEGACY = {
    'white': ('Cream', 'Common', (247, 234, 196)), 'blue': ('Blue', 'Common', (36, 132, 211)), 'green': ('Green', 'Uncommon', (29, 175, 75)),
    'teal': ('Teal', 'Rare', (22, 170, 151)), 'pink': ('Pink', 'Rare', (215, 72, 147)), 'gold': ('Amber', 'Epic', (241, 160, 36)),
    'violet': ('Purple', 'Legendary', (158, 80, 203)), 'red': ('Red', 'Mythic', (237, 44, 33)), 'black': ('Black', 'Mythic', (29, 34, 41)),
}
# tier -> (fewest, most) colours (the owner's ladder of 2026-10-18, docs/186 section 5)
PER_TIER = {'Common': (2, 4), 'Uncommon': (2, 3), 'Rare': (2, 3), 'Epic': (2, 2), 'Legendary': (1, 2), 'Mythic': (2, 2)}
failed = []

def check(ok, what):
    if not ok:
        failed.append(what)
        print('FAIL', what)

def near(a, b, eps, what):
    check(abs(a - b) <= eps, f'{what}: {a} vs {b}')

# 1. CIEDE2000: pairs from the Sharma, Wu and Dalal 2005 test data.
for lab1, lab2, want in [((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425), ((50, 3.1571, -77.2803), (50, 0, -82.7485), 2.8615),
                         ((50, -1.3802, -84.2814), (50, 0, -82.7485), 1.0000), ((50, 2.5, 0), (73, 25, -18), 27.1492),
                         ((50, 2.5, 0), (61, -5, 29), 22.8977), ((50, 2.5, 0), (56, -27, -3), 31.9030),
                         ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644), ((50, 2.5, 0), (50, 0, -2.5), 4.3065)]:
    near(cd.ciede2000(lab1, lab2), want, 5e-4, 'CIEDE2000 test pair')
    near(cd.ciede2000(lab2, lab1), want, 5e-4, 'CIEDE2000 is symmetric')
check(cd.ciede2000((50, 10, 10), (50, 10, 10)) == 0, 'same colour is 0')
check(abs(cd.ciede2000(cd.rgb_to_lab((255, 255, 255)), cd.rgb_to_lab((0, 0, 0))) - 100) < 1, 'white against black is about 100')

# 2. Lab and colour-blindness simulation.
w = cd.rgb_to_lab((255, 255, 255))
near(w[0], 100, 0.01, 'white L*')
check(abs(w[1]) < 0.01 and abs(w[2]) < 0.01, 'white has no chroma')
for kind in cd.CVD:
    for grey in [(0, 0, 0), (128, 128, 128), (255, 255, 255)]:
        out = cd.simulate(grey, kind)
        check(all(abs(out[i] - grey[i]) < 1.0 for i in range(3)), f'{kind} keeps grey {grey}: {out}')
check(cd.de((237, 44, 33), (29, 175, 75), 'deutan') < cd.de((237, 44, 33), (29, 175, 75)) / 2, 'red against green gets much closer for a deuteranope')
check(cd.de((237, 44, 33), (29, 175, 75), 'protan') < cd.de((237, 44, 33), (29, 175, 75)) / 2, 'red against green gets much closer for a protanope')

# 3. blend = the game's Color3:Lerp (plain sRGB values)
check(cd.blend((0, 0, 0), (100, 200, 50)) == (50.0, 100.0, 25.0), 'middle blend')
check(cd.blend((10, 20, 30), (110, 120, 130), 0.25) == (35.0, 45.0, 55.0), 'quarter blend')
check(cd.hex_of((247, 234, 196)) == '#F7EAC4' and cd.rgb_of_hex('#F7EAC4') == (247, 234, 196), 'hex round trip')

# 4. the real table
rows = cd.load_colours()
ids = [r[0] for r in rows]
check(len(set(ids)) == len(ids), 'colour ids are unique')
check(len({r[1] for r in rows}) == len(rows), 'colour names are unique')
check(len({tuple(r[4]) for r in rows}) == len(rows), 'colour rgb values are unique')
for cid, (name, tier, rgb) in LEGACY.items():
    row = next((r for r in rows if r[0] == cid), None)
    check(row is not None and row[1] == name and row[2] == tier and tuple(row[4]) == rgb, f'legacy colour {cid} is untouched')
check(all(cid in ids for cid in cd.LEGACY_IDS) and set(cd.LEGACY_IDS) == set(LEGACY), 'the tool knows the legacy ids')
tiers = {}
for r in rows: tiers.setdefault(r[2], []).append(r[1])
for tier, (lo, hi) in PER_TIER.items():
    n = len(tiers.get(tier, []))
    check(lo <= n <= hi, f'{tier} has {n} colours, wanted {lo} to {hi}')
check(12 <= len(rows) <= 18, f'{len(rows)} colours in total')
for name in (r[1] for r in rows): check(3 <= len(name) <= 8 and name.isalpha(), f'kid name {name}')

# 5. no NEW pair is too close (legacy pairs are listed, not failed)
legacy_pairs = set()
bad = []
for p in cd.pair_table(rows):
    if p['score'] >= 1.0: continue
    if p['a_id'] in cd.LEGACY_IDS and p['b_id'] in cd.LEGACY_IDS:
        legacy_pairs.add((p['a'], p['b']))
    else:
        bad.append(p)
for p in bad: check(False, f"too close: {p['a']} / {p['b']}: normal {p['normal']:.1f}, colour-blind {p['worst_cvd']:.1f}")
check(len(legacy_pairs) <= 7, f'legacy weak pairs only shrink (now {len(legacy_pairs)})')
new_rows = [r for r in rows if r[0] not in cd.LEGACY_IDS]
for r in new_rows:
    lab = cd.rgb_to_lab(r[4])
    check(cd.L_MIN <= lab[0] <= cd.L_MAX, f'{r[1]} lightness {lab[0]:.0f}')
    check(cd.lab_chroma(lab) <= cd.CHROMA_MAX, f'{r[1]} chroma')
closest_new = min((p['normal'] for p in cd.pair_table(rows) if not (p['a_id'] in cd.LEGACY_IDS and p['b_id'] in cd.LEGACY_IDS)), default=999)
check(closest_new >= cd.NORMAL_MIN, f'closest new pair {closest_new:.1f}')

# 6. blends: a 50/50 mix of two colours that sits on top of a THIRD single colour is listed. A mix that involves a new colour fails only
# when it is likely (a pair chance 2 * p1 * p2 of 0.05 percent or more) and the look-alike is not a neutral (Stone and Clay are mixing results by
# nature: any two opposite colours mix to grey or brown). Mixes made only of the nine legacy colours are left as they are.
scale = sum(r[3] for r in rows)
chance = {r[1]: r[3] / scale for r in rows}
legacy_names = {v[0] for v in LEGACY.values()}
listed = 0
for b in cd.blend_table(rows):
    if b['dist'] >= cd.BLEND_MIN: continue
    if {b['a'], b['b'], b['nearest']} <= legacy_names: continue
    listed += 1
    p = 2 * chance[b['a']] * chance[b['b']]
    check(p < 0.0005 or b['nearest'] in ('Stone', 'Clay'), f"{b['a']} + {b['b']} ({100 * p:.3f}%) looks like {b['nearest']} ({b['dist']:.1f})")

# 7. where the colour is shown: a NEW swatch is at least as far from the chip card as Black (the weakest swatch that already ships) and the
# contrast maths equals TextStyle.luminance (white 1.0, black 0)
near(cd.wcag_luminance((255, 255, 255)), 1.0, 1e-9, 'white luminance')
near(cd.wcag_luminance((0, 0, 0)), 0.0, 1e-9, 'black luminance')
near(cd.wcag_contrast((255, 255, 255), (0, 0, 0)), 21.0, 1e-9, 'white on black contrast')
black_de = next(r['de_card'] for r in cd.surface_table(rows) if r['id'] == 'black')
for r in cd.surface_table(rows):
    if r['id'] not in cd.LEGACY_IDS:
        check(r['de_card'] >= cd.SWATCH_DE_MIN and r['de_card'] > black_de, f"{r['name']} swatch is too close to the chip card ({r['de_card']:.0f})")

# 8. the contact sheet is drawn without error (review only, never game art)
import tempfile
with tempfile.TemporaryDirectory() as d:
    out = Path(d) / 'sheet.png'
    cd.sheet(rows, str(out))
    check(out.exists() and out.stat().st_size > 5000, 'the contact sheet is written')

print('Colour distance checks passed:' if not failed else f'{len(failed)} FAILED', f'{len(rows)} colours, closest pair {min(p["normal"] for p in cd.pair_table(rows)):.1f},',
      f'closest NEW pair {closest_new:.1f}, {len(legacy_pairs)} legacy weak pairs left as they are')
sys.exit(1 if failed else 0)
