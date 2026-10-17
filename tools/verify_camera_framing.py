"""BD-500 / BD-471 (docs/139 s7, docs/115 SZ1-SZ3): offline verifier for the species-aware default camera, src/shared/CameraFraming.luau.

It runs the REAL pure module in Luau and fails when:
  1. COMPY: a Compy is framed any differently from the old growth-only rule (minimum zoom 12 x growth scale, aim lift 2 x (scale - 1));
  2. NEVER CLOSER: any species (all 22 boxes below) is ever framed closer than 12 x growth scale, so small and flat bodies (fliers,
     swimmers, Raptor, Gallimimus) keep the old view, and a bigger or longer body only pushes the camera back (monotonic in the box);
  3. CAP: the minimum zoom stays at or below MaxDistance (90, BD-513; was 75) unless the old rule already exceeded it, the cap is at least what
     the widest body needs at the BIG maximum growth scale 4.8 (89.2, Ankylosaurus), and CameraOcclusion.MaxRange stays above it by 10 or more;
  4. STUDIO: the minimum zoom and the lift the module gives for every species at growth scale 1, 2, 4 match the numbers recorded in the
     Studio default-camera sweep (docs/evidence/2026-10-17-camfit/), and the recorded screen fill and top margin of that sweep are in the
     band (fill 25% to 56% of the screen height, dino top at 160 px or more from the top, i.e. clear of the HUD title, SIZE bar and hint). Change the module and these fail until the sweep is redone.
Not Studio evidence by itself: the Studio table is a copy of what the sweep measured (viewport 1140 x 785, FOV 70, pitch -15).
Usage: python tools/verify_camera_framing.py --runner luau.exe [--print]
"""
from pathlib import Path
import argparse
import subprocess
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_scale_ladder import MEASURED  # noqa: E402  (W, H, L at spawn of all 22 species, Studio-measured BD-471 / BD-500)

BASE = 12  # Config.CameraMinZoom
CAP = 90  # CameraFraming.MaxDistance (BD-513)
SCALES = (1, 2, 4)

# Studio sweep 2026-10-17 (own copy camfit.rbxlx, playtest build of this branch, Play, default zoom reset to the minimum, camera pitch -15,
# FOV 70, viewport 1140 x 785): species -> {growth scale: (min zoom, fill of screen height %, dino top px from the top of the screen)}.
# NOT in this table (cap 75 binds, open question BD-513): BIG at growth scale 4.8: Spinosaurus fill 72%, top 64 px (sail behind the HUD banner),
# T-Rex fill 51%, top 150 px (head touches the hint line).
STUDIO = {
    'ankylosaurus': {1: (18.84, 44, 266), 2: (37.68, 42, 241), 4: (75.0, 41, 222)},
    'archaeopteryx': {1: (12.0, 38, 366), 2: (24.0, 35, 297), 4: (48.0, 35, 272)},
    'baryonyx': {1: (14.72, 40, 268), 2: (29.45, 41, 221), 4: (58.89, 41, 195)},
    'brachiosaurus': {1: (14.36, 46, 261), 2: (28.72, 45, 216), 4: (57.43, 45, 193)},
    'compy': {1: (12.04, 40, 278), 2: (24.08, 41, 224), 4: (48.15, 43, 184)},
    'dimorphodon': {1: (12.0, 36, 336), 2: (24.0, 34, 272), 4: (48.0, 34, 249)},
    'elasmosaurus': {1: (16.51, 47, 260), 2: (33.02, 46, 219), 4: (66.05, 46, 196)},
    'gallimimus': {1: (12.13, 43, 282), 2: (24.27, 42, 231), 4: (48.54, 41, 201)},
    'microraptor': {1: (12.0, 31, 416), 2: (24.0, 26, 372), 4: (48.0, 27, 373)},
    'pachycephalosaurus': {1: (13.41, 45, 267), 2: (26.82, 44, 226), 4: (53.64, 44, 198)},
    'parasaurolophus': {1: (13.57, 43, 267), 2: (27.13, 42, 223), 4: (54.27, 42, 201)},
    'pteranodon': {1: (12.0, 37, 352), 2: (24.0, 35, 290), 4: (48.0, 39, 266)},
    'quetzalcoatlus': {1: (12.0, 46, 302), 2: (24.0, 44, 247), 4: (48.0, 44, 220)},
    'raptor': {1: (12.02, 39, 277), 2: (24.04, 39, 229), 4: (48.09, 39, 202)},
    'spinosaurus': {1: (18.03, 53, 255), 2: (36.07, 54, 199), 4: (72.13, 56, 165)},
    'stegosaurus': {1: (15.27, 46, 285), 2: (30.55, 44, 247), 4: (61.09, 45, 211)},
    'therizinosaurus': {1: (16.07, 42, 258), 2: (32.14, 42, 209), 4: (64.29, 44, 178)},
    'triceratops': {1: (14.42, 47, 259), 2: (28.84, 47, 211), 4: (57.68, 46, 190)},
    'tyrannosaurus': {1: (17.28, 46, 242), 2: (34.57, 45, 204), 4: (69.14, 45, 184)},
}

# C-39 (BD-537, docs/116): the three Water species were resized from length to bulk, so their old sweep rows (ichthyosaurus, mosasaurus,
# plesiosaurus) no longer describe the game. They are removed until the Studio sweep is redone (docs/evidence/2026-10-17-water-bulk/); until
# then only checks 1 to 3 (the module's own rules) apply to them, not check 4.
PENDING_SWEEP = ('ichthyosaurus', 'mosasaurus', 'plesiosaurus')

BODY = r'''
local sizes = {SIZES}
local ids = {}
for id in sizes do ids[#ids + 1] = id end
table.sort(ids)
for _, id in ids do
    local b = sizes[id]
    for _, s in {1, 1.5, 2, 3, 4, 4.8} do
        local z = M.minZoom(12, s, b[2] * s, b[3] * s)
        local l = M.lift(b[2] * s)
        print(string.format("R\t%s\t%s\t%.4f\t%.4f", id, tostring(s), z, l))
    end
end
-- guards: junk numbers fall back to the old rule
print(string.format("G\t%.4f\t%.4f\t%.4f\t%.4f", M.minZoom(12, 2, nil, nil), M.minZoom(12, 0 / 0, nil, nil), M.minZoom(12, 2, -3, 8), M.lift(nil)))
-- monotonic in height and in length
local prev = 0
for h = 4, 80, 4 do local z = M.minZoom(12, 1, h, 10) assert(z >= prev, "monotonic in height") prev = z end
prev = 0
for l = 4, 120, 4 do local z = M.minZoom(12, 1, 8, l) assert(z >= prev, "monotonic in length") prev = z end
print("OK")
'''


def run(runner):
    sizes = ', '.join('%s = {%s, %s, %s}' % (k, *v) for k, v in MEASURED.items())
    source = 'local M = (function()\n' + (ROOT / 'src/shared/CameraFraming.luau').read_text(encoding='utf-8') + '\nend)()\n' + BODY.replace('{SIZES}', '{' + sizes + '}')
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'camera_framing.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if result.returncode or 'OK' not in result.stdout:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode or 1)
    return result.stdout.splitlines()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--print', action='store_true')
    args = parser.parse_args()
    rows = {}
    guard = None
    for line in run(args.runner):
        parts = line.split('\t')
        if parts[0] == 'R':
            rows[(parts[1], float(parts[2]))] = (float(parts[3]), float(parts[4]))
        elif parts[0] == 'G':
            guard = [float(x) for x in parts[1:]]
    problems = []
    # 1 COMPY
    for s in (1, 1.5, 2, 3, 4, 4.8):
        z, lift = rows[('compy', s)]
        if abs(z - BASE * s) > 0.01 * BASE * s:
            problems.append('compy minZoom at %s is %.2f, the old rule gives %.2f' % (s, z, BASE * s))
        if abs(lift - 2 * (s - 1)) > 0.02 + 0.01 * 2 * (s - 1):
            problems.append('compy lift at %s is %.3f, the old rule gives %.3f' % (s, lift, 2 * (s - 1)))
    # 2 NEVER CLOSER, 3 CAP
    for (species, s), (z, lift) in rows.items():
        if z < BASE * s - 1e-6:
            problems.append('%s at %s: min zoom %.2f is closer than the old %.2f' % (species, s, z, BASE * s))
        if z > CAP + 1e-6 and z > BASE * s + 1e-6:
            problems.append('%s at %s: min zoom %.2f is past the %d stud cap' % (species, s, z, CAP))
        if lift < -1e-9:
            problems.append('%s at %s: negative lift' % (species, s))
    if guard is None or abs(guard[0] - 24) > 1e-6 or abs(guard[1] - 12) > 1e-6 or abs(guard[2] - 24) > 1e-6 or abs(guard[3]) > 1e-9:
        problems.append('junk input does not fall back to the old rule: %s' % (guard,))
    # small and flat bodies keep the old view
    for species in ('raptor', 'gallimimus', 'dimorphodon', 'microraptor', 'archaeopteryx', 'pteranodon'):  # C-39: swimmers are bulk-sized, no longer small
        for s in (1, 2, 4):
            z, _ = rows[(species, s)]
            if z > BASE * s * 1.02:
                problems.append('%s at %s is pushed back (%.2f > %.2f) although its body is not bigger than a Compy' % (species, s, z, BASE * s))
    # long and big bodies are pushed back, in order
    order = [rows[(sp, 1)][0] for sp in ('compy', 'triceratops', 'tyrannosaurus', 'ankylosaurus', 'spinosaurus')]
    if not (order[0] < order[1] < order[2] < order[4] and order[1] < order[3]):
        problems.append('framing order at scale 1 is not Compy < Triceratops < T-Rex < Spinosaurus: %s' % order)
    # 4 STUDIO
    for species, per in STUDIO.items():
        for s, (zoom, fill, top) in per.items():
            z, _ = rows[(species, float(s))]
            if abs(z - zoom) > 0.02 * zoom + 0.3:
                problems.append('%s at %s: module min zoom %.2f, Studio sweep measured %.2f (redo the sweep)' % (species, s, z, zoom))
            if not 25 <= fill <= 56:
                problems.append('%s at %s: Studio fill %d%% is outside 25 to 56%% of the screen height' % (species, s, fill))
            if top < 160:
                problems.append('%s at %s: Studio dino top %d px is inside the HUD banner (needs 160 or more)' % (species, s, top))
    missing = [sp for sp in MEASURED if sp not in STUDIO and sp not in PENDING_SWEEP]
    if missing:
        problems.append('no Studio sweep row for: %s' % ', '.join(missing))
    # BD-513 BIG: at the BIG maximum growth scale 4.8 no species is held back by the cap: the camera distance is the size rule's own number
    # (12 x max(scale, size ratio), never below 12 x 4.8), so the screen share is the same ratio as at scale 4 (<= 56%) and not the old 72%.
    for species in MEASURED:
        z, _ = rows[(species, 4.8)]
        h, l = MEASURED[species][1] * 4.8, MEASURED[species][2] * 4.8
        wanted = max(BASE * 4.8, BASE * ((h * h + (0.65 * l) ** 2) ** 0.5) / 8.2831)
        if z < BASE * 4.8 - 1e-6 or abs(z - wanted) > 0.02 * wanted:
            problems.append('%s at 4.8: min zoom %.2f is not the size rule (%.2f): the cap still binds' % (species, z, wanted))
    widest = max(rows[(sp, 4.8)][0] for sp in MEASURED)
    if widest > CAP:
        problems.append('the widest body at 4.8 needs %.1f, past the cap %d' % (widest, CAP))
    occlusion = (ROOT / 'src/shared/CameraOcclusion.luau').read_text(encoding='utf-8')
    found = re.search(r'M\.MaxRange = (\d+)', occlusion)
    if not found or int(found.group(1)) < CAP + 10:
        problems.append('CameraOcclusion.MaxRange (%s) must be at least the cap %d + 10, else props stop fading for a BIG dino' % (found and found.group(1), CAP))
    if not re.search(r'CameraFraming\.MaxDistance = %d' % CAP, (ROOT / 'src/shared/CameraFraming.luau').read_text(encoding='utf-8')):
        problems.append('CameraFraming.MaxDistance is not %d' % CAP)
    if args.print:
        for sp in sorted(MEASURED):
            print(sp, ' '.join('s%s %.1f/%.1f' % (s, *rows[(sp, float(s))]) for s in (1, 2, 4)))
    if problems:
        print('camera framing FAILED:')
        for p in problems:
            print(' -', p)
        raise SystemExit(1)
    print('camera framing ok: Compy unchanged, 22 species never closer than 12 x scale, capped at 90 and never capped at 4.8, %d Studio sweep rows match' % sum(len(v) for v in STUDIO.values()))


if __name__ == '__main__':
    main()
