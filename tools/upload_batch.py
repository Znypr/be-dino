"""Prepare the one-shot image upload batch (lead tool; this script never uploads anything).

    python tools/upload_batch.py                 # list, check, copy into build/upload-batch/ and write manifest.json
    python tools/upload_batch.py --list          # list and check only, write nothing
    python tools/upload_batch.py --out DIR       # another folder (default build/upload-batch/, gitignored)

Collects every repo PNG whose slot (tools/asset_slots.json) is still EMPTY: the trail shop icons, the mutation badges,
the Crystal Shop tab icons, tiles and green-spotted egg (BD-047),
the Blender FX textures in resources/effects/fx-v2/, the three meadow-grass-v2 maps and the Eggs page art
(jungle stage JPG + five condition egg PNGs in resources/ui/v2/stage/), plus (BD-296) the seven Blender cave meshes
(6 wall rock forms and the gate arch frame, assets/blender/world/fbx_v3/cave_*_v3.fbx, slot kind `mesh`: uploaded as a Model, the
id is bound as bare digits). Each file is checked (under 20 MB, real PNG/JPEG, RGBA where the slot needs alpha; a binary FBX header
for meshes) and copied into ONE flat folder as <slot name>.<ext>, so a local
`python -m http.server` can serve it and the uploader can name each asset after its slot. manifest.json is
[{"file": <repo path>, "slot": <slot name>, "url_path": <flat file name>}]. After the uploader returns its
{"http://localhost:PORT/<file>": "rbxassetid://N"} map, bind everything in one go:

    python tools/bind_assets.py --batch uploaded.json --manifest build/upload-batch/manifest.json [--dry-run]

Exit code 1 if any file fails a check (nothing is copied then).
"""
import argparse
import json
import re
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_assets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / 'build/upload-batch'
MAX_BYTES = 20 * 1024 * 1024
PNG_SIG = b'\x89PNG\r\n\x1a\n'

# group name -> (folder, file name regex -> slot name builder, needs alpha). Every FX file whose derived slot does not
# exist (the superseded fx-v2 smoke / spark / flame sheets and starFour) is listed as "no slot, skipped".
GROUPS = [
    ('trail icons', 'resources/ui/v2/icons', r'trail-([a-z]+)-v1\.png', lambda m: 'trail_' + m.group(1), True),
    ('mutation badges', 'resources/ui/v2/icons', r'mutation-([a-z]+)-v1\.png', lambda m: 'mutation_' + m.group(1), True),
    ('shop icons and tiles', 'resources/ui/v2/icons', r'shop-(tab|tile)-([a-z]+)-v1\.png', lambda m: f'shop_{m.group(1)}_{m.group(2)}', True),
    ('green-spotted egg', 'resources/ui/v2/icons', r'egg-green-spotted-v1\.png', lambda m: 'egg_green_spotted', True),
    ('FX textures', 'resources/effects/fx-v2', r'([A-Za-z]+)(?:-([a-z]+))?\.png',
     lambda m: m.group(1) + (m.group(2).capitalize() if m.group(2) else ''), True),
    ('meadow grass maps', 'resources/materials/meadow-grass-v2', r'meadow-grass-v2-([a-z]+)\.png',
     lambda m: 'meadow_grass_v2_' + m.group(1), False),
    # BD-208 / BD-394: the Eggs page + Conditions shop jungle stage (opaque JPG, upload as is) and the five outlined condition eggs
    ('egg stage', 'resources/ui/v2/stage', r'egg-stage-jungle-v1\.jpg', lambda m: 'egg_stage', False),
    ('condition eggs', 'resources/ui/v2/stage/eggs', r'egg-0[1-5]_([a-z]+)\.png', lambda m: 'egg_cond_' + m.group(1), True),
]
# Mesh groups (BD-296): FBX files whose slot kind is `mesh` (WorldGeneratedMeshes.CaveForms). group name -> (folder, file name regex -> slot name builder).
MESH_GROUPS = [
    ('cave meshes', 'assets/blender/world/fbx_v3', r'(cave_(?:rockform|gate)_\w+_v3)\.fbx', lambda m: m.group(1)),
]
FBX_SIG = b'Kaydara FBX Binary  \x00'


def png_info(data):
    """(width, height, has_alpha) of a PNG, or None when it is not a well-formed PNG header."""
    if data[:8] != PNG_SIG or data[12:16] != b'IHDR':
        return None
    w, h, _depth, ctype = struct.unpack('>IIBB', data[16:26])
    alpha = ctype in (4, 6) or b'tRNS' in data[:4096]
    return w, h, alpha


def check_file(path, needs_alpha):
    problems = []
    size = path.stat().st_size
    if size == 0:
        problems.append('empty file')
    if size >= MAX_BYTES:
        problems.append(f'{size / 1048576:.1f} MB, over the 20 MB limit')
    head = path.read_bytes()[:4096] if size else b''
    if path.suffix.lower() == '.fbx':
        if not head.startswith(FBX_SIG):
            problems.append('not a binary FBX')
        return problems, size, None
    info = png_info(head)
    if info is None:
        if head[:3] == b'\xff\xd8\xff':
            if needs_alpha:
                problems.append('JPEG has no alpha')
        else:
            problems.append('not a valid PNG/JPEG')
    elif needs_alpha and not info[2]:
        problems.append('PNG has no alpha channel (RGBA needed)')
    return problems, size, info


def collect(slots):
    """Returns (items, skipped). item = dict(group, file, slot, ext, needs_alpha); skipped = [(file, why)]."""
    items, skipped = [], []
    for group, folder, pattern, slot_of, needs_alpha in GROUPS:
        d = ROOT / folder
        for f in sorted([*d.glob('*.png'), *d.glob('*.jpg')]) if d.is_dir() else []:
            m = re.fullmatch(pattern, f.name)
            if not m:
                continue
            slot = slot_of(m)
            rel = f.relative_to(ROOT).as_posix()
            if slot not in slots:
                skipped.append((rel, 'no slot (superseded or not registered)'))
                continue
            s = slots[slot]
            if s['kind'] != 'image':
                skipped.append((rel, f'slot {slot} is {s["kind"]}, not an image'))
                continue
            current = bind_assets.current_value(s, (ROOT / s['file']).read_text(encoding='utf-8'))
            if current:
                skipped.append((rel, f'slot {slot} already bound ({current})'))
                continue
            items.append({'group': group, 'file': rel, 'slot': slot, 'ext': f.suffix, 'needs_alpha': needs_alpha})
    for group, folder, pattern, slot_of in MESH_GROUPS:
        d = ROOT / folder
        for f in sorted(d.glob('*.fbx')) if d.is_dir() else []:
            m = re.fullmatch(pattern, f.name)
            if not m:
                continue
            slot = slot_of(m)
            rel = f.relative_to(ROOT).as_posix()
            if slot not in slots:
                skipped.append((rel, 'no slot (not registered)'))
                continue
            s = slots[slot]
            if s['kind'] != 'mesh':
                skipped.append((rel, f'slot {slot} is {s["kind"]}, not a mesh'))
                continue
            current = bind_assets.current_value(s, (ROOT / s['file']).read_text(encoding='utf-8'))
            if current:
                skipped.append((rel, f'slot {slot} already bound ({current})'))
                continue
            items.append({'group': group, 'file': rel, 'slot': slot, 'ext': f.suffix, 'needs_alpha': False})
    return items, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=str(DEFAULT_OUT), help='flat output folder (default build/upload-batch/)')
    ap.add_argument('--list', action='store_true', help='list and check only, write nothing')
    args = ap.parse_args(argv)
    slots = bind_assets.load_slots()
    items, skipped = collect(slots)

    failed, counts, total = False, {}, 0
    for it in items:
        problems, size, info = check_file(ROOT / it['file'], it['needs_alpha'])
        it['problems'] = problems
        failed |= bool(problems)
        counts[it['group']] = counts.get(it['group'], 0) + 1
        total += size
        dims = f'{info[0]}x{info[1]}' if info else ('FBX' if it['ext'] == '.fbx' else '?')
        print(f'{"FAIL" if problems else "ok  "} {it["slot"]:28s} {dims:>9s} {size / 1024:7.0f} KB  {it["file"]}'
              + (('  <- ' + '; '.join(problems)) if problems else ''))
    for rel, why in skipped:
        print(f'skip {rel}: {why}')
    print('\n' + ', '.join(f'{n} {g}' for g, n in counts.items()) + f' = {len(items)} files, {total / 1048576:.1f} MB total')
    if failed:
        print('REFUSED: fix the files marked FAIL; nothing copied.', file=sys.stderr)
        return 1
    if args.list:
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():  # a stale file from an earlier run must never be uploaded
        if old.is_file():
            old.unlink()
    manifest = []
    for it in items:
        flat = it['slot'] + it['ext']
        shutil.copyfile(ROOT / it['file'], out / flat)
        manifest.append({'file': it['file'], 'slot': it['slot'], 'url_path': flat})
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    try:
        shown = out.relative_to(ROOT).as_posix()
    except ValueError:
        shown = str(out)
    print(f'copied {len(manifest)} files + manifest.json to {shown}/')
    print(f'serve:  python -m http.server 8765 --directory {shown}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
