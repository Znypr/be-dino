"""BD-500 / BD-471 (docs/139 s7, docs/115 SZ1-SZ3): offline verifier for the species-aware default camera, src/shared/CameraFraming.luau.

It runs the REAL pure module in Luau and fails when:
  1. COMPY: a Compy is framed any differently from the old growth-only rule (minimum zoom 12 x growth scale, aim lift 2 x (scale - 1));
  2. NEVER CLOSER: any species (all 22 boxes below) is ever framed closer than 12 x growth scale, so small and flat bodies (fliers,
     swimmers, Raptor, Gallimimus) keep the old view, and a bigger or longer body only pushes the camera back (monotonic in the box);
  3. CAP: the minimum zoom stays at or below MaxDistance (75, under the CameraOcclusion range of 80) unless the old rule already exceeded it;
  4. STUDIO: the minimum zoom and the lift the module gives for every species at growth scale 1, 2, 4 match the numbers recorded in the
     Studio default-camera sweep (docs/evidence/2026-10-17-camfit/), and the recorded screen fill and top margin of that sweep are in the
     band (fill 25% to 56% of the screen height, dino top below the HUD banner). Change the module and these fail until the sweep is redone.
Not Studio evidence by itself: the Studio table is a copy of what the sweep measured (viewport 1140 x 785, FOV 70, pitch -15).
Usage: python tools/verify_camera_framing.py --runner luau.exe [--print]
"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_scale_ladder import MEASURED  # noqa: E402  (W, H, L at spawn of all 22 species, Studio-measured BD-471 / BD-500)

BASE = 12  # Config.CameraMinZoom
SCALES = (1, 2, 4)

# Studio sweep 2026-10-17 (own copy camfit.rbxlx, playtest build of this branch, Play, default zoom reset to the minimum, camera pitch -15,
# FOV 70, viewport 1140 x 785): species -> {growth scale: (min zoom, fill of screen height %, dino top px from the top of the screen)}.
STUDIO = {}  # filled by the sweep below

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
        if z > 75 + 1e-6 and z > BASE * s + 1e-6:
            problems.append('%s at %s: min zoom %.2f is past the 75 stud cap' % (species, s, z))
        if lift < -1e-9:
            problems.append('%s at %s: negative lift' % (species, s))
    if guard is None or abs(guard[0] - 24) > 1e-6 or abs(guard[1] - 12) > 1e-6 or abs(guard[2] - 24) > 1e-6 or abs(guard[3]) > 1e-9:
        problems.append('junk input does not fall back to the old rule: %s' % (guard,))
    # small and flat bodies keep the old view
    for species in ('raptor', 'gallimimus', 'dimorphodon', 'microraptor', 'archaeopteryx', 'pteranodon', 'ichthyosaurus', 'mosasaurus'):
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
            if top < 170:
                problems.append('%s at %s: Studio dino top %d px is inside the HUD banner (needs 170 or more)' % (species, s, top))
    missing = [sp for sp in MEASURED if sp not in STUDIO]
    if missing:
        problems.append('no Studio sweep row for: %s' % ', '.join(missing))
    if args.print:
        for sp in sorted(MEASURED):
            print(sp, ' '.join('s%s %.1f/%.1f' % (s, *rows[(sp, float(s))]) for s in (1, 2, 4)))
    if problems:
        print('camera framing FAILED:')
        for p in problems:
            print(' -', p)
        raise SystemExit(1)
    print('camera framing ok: Compy unchanged, 22 species never closer than 12 x scale, capped at 75, %d Studio sweep rows match' % sum(len(v) for v in STUDIO.values()))


if __name__ == '__main__':
    main()
