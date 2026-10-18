"""Bind one secret species' REAL generated model into the game (BD-606, docs/173, docs/149 section 3).

One command does the five edits that must agree (the verifiers fail if any one is missing):
  1. src/shared/SecretSpeciesConfig.luau       the species row `assetId = <id>`
  2. src/shared/LowPolyDinoAssets.luau          the registry entry (id, version, scale, tier 1, class)
  3. src/shared/ScaleLadder.luau                Dino.secret.species row: scale, spawn box, snout, head length, measured = true
  4. tools/verify_scale_ladder.py               SECRET_BOXES (the box the camera / hit-size / mouth-reach verifiers read)
  5. tools/verify_secret_species.py             BOUND_IDS (the ids that are allowed to be bound)
and, with --runner, regenerates the docs/114 size table (`verify_scale_ladder.py --write-doc`).

Inputs are facts, never guesses: the asset id of a published `generate_mesh` Model of the owner's account, and the MEASURED bounding box of that
model at growth scale 1 (Studio: Model:GetBoundingBox, width x height x length in studs; see docs/173 section 5 for the snippet). The tool
refuses an id that is not a plain whole number of 10 to 16 digits, a species that is not in the secret roster, a box that is not positive, a
slot that is already bound (unless --replace), and a size that cannot land within 2% of the SZ1 size rule. It never touches a Config flag, a
release profile or a save. Dry run by default; --write applies.

  python tools/bind_secret_species.py --species budgiesaurus --asset-id 107910518074360 --box 4.0 8.0 9.0
  python tools/bind_secret_species.py --species budgiesaurus --asset-id 107910518074360 --box 4.0 8.0 9.0 --write --runner C:/path/luau.exe

The head length is a rule of thumb (22% of the body length) unless you pass the measured one with --head-length (the length of the head part's
bounding box at scale 1); the tool says which one it used. After --write: add the species to docs/173 and docs/77, then run the verifiers.
"""
from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'src/shared/SecretSpeciesConfig.luau'
REGISTRY = 'src/shared/LowPolyDinoAssets.luau'
LADDER = 'src/shared/ScaleLadder.luau'
BOXES = 'tools/verify_scale_ladder.py'
BOUND = 'tools/verify_secret_species.py'

HEIGHT_TARGET = 6.60   # SZ1 Ground, size tier 1 (Compy-sized; docs/115 SS8)
BULK_TARGET = 5.55     # SZ1 Fly and Water, size tier 1: 8.12 / 1.1 ** 4
TOLERANCE = 0.02       # ScaleLadder.Sizing.tolerance
HEAD_SHARE = 0.22      # head length / body length when the head part was not measured
SLOT = r'(\{ id = "%s", name = "[^"]+", secret = true, class = "(\w+)", weight = \d+, assetId = )(\d+)( \})'


def read(path: str, root: Path) -> str:
    return (root / path).read_text(encoding='utf-8')


def write(path: str, text: str, root: Path) -> None:
    (root / path).write_text(text, encoding='utf-8', newline='')


def basis_for(cls: str) -> tuple[str, float]:
    return ('bulk', BULK_TARGET) if cls in ('Fly', 'Water') else ('height', HEIGHT_TARGET)


def size_of(basis: str, box: tuple[float, float, float]) -> float:
    return box[1] if basis == 'height' else (box[0] * box[1] * box[2]) ** (1 / 3)


def plan(cls: str, box: tuple[float, float, float], head_length: float | None = None) -> dict:
    """Pure: the registry scale and the ladder row for a MEASURED box at scale 1. Raises ValueError when it cannot meet the size rule."""
    if len(box) != 3 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in box):
        raise ValueError(f'the box must be three positive numbers, got {box!r}')
    basis, target = basis_for(cls)
    scale = round(target / size_of(basis, box), 2)
    if not 0.5 <= scale <= 6:
        raise ValueError(f'scale {scale} is outside the sane range 0.5 to 6: check the box (it must be the real model at scale 1)')
    row = tuple(round(v * scale, 2) for v in box)
    got = size_of(basis, row)
    if abs(got - target) > TOLERANCE * target:
        raise ValueError(f'size {got:.2f} is more than {TOLERANCE:.0%} from the rule {target} ({basis}); the scale {scale} cannot fix this box')
    length = row[2]
    measured_head = head_length is not None
    head = round(head_length * scale, 2) if measured_head else round(HEAD_SHARE * length, 2)
    if not 0 < head <= length:
        raise ValueError(f'head length {head} does not fit a body {length} long')
    return {'basis': basis, 'target': target, 'scale': scale, 'row': row, 'snout': round(length / 2, 2), 'head': head, 'head_measured': measured_head}


def fmt(v: float) -> str:
    return f'{v:.2f}'


def apply(species: str, asset_id: int, box: tuple[float, float, float], head_length: float | None, version: str, replace: bool, root: Path = ROOT) -> dict:
    if not re.fullmatch(r'[1-9]\d{9,15}', str(asset_id)):
        raise ValueError(f'asset id {asset_id!r} must be a plain whole number of 10 to 16 digits (never invent one)')
    config = read(CONFIG, root)
    match = re.search(SLOT % re.escape(species), config)
    if not match:
        raise ValueError(f'{species!r} is not a secret species in {CONFIG}')
    cls, current = match.group(2), int(match.group(3))
    if current and not replace:
        raise ValueError(f'{species} is already bound to {current}; pass --replace to change it')
    others = [int(m.group(1)) for m in re.finditer(r'assetId = (\d+) \}', config) if int(m.group(1)) and int(m.group(1)) != current]
    if asset_id in others:
        raise ValueError(f'asset id {asset_id} is already bound to another secret species')
    result = plan(cls, box, head_length)
    scale = result['scale']
    row = result['row']
    # 1. the slot
    config = config[:match.start()] + match.group(1) + str(asset_id) + match.group(4) + config[match.end():]
    # 2. the registry entry (replace the line when it exists, else append before the closing brace)
    registry = read(REGISTRY, root)
    entry = f'    {species} = {{assetId = {asset_id}, version = "{version}", scale = {scale}, tier = 1, class = "{cls}"}},\n'
    existing = re.search(rf'^    {species} = \{{assetId = \d+, [^\n]*\n', registry, re.M)
    if existing:
        registry = registry[:existing.start()] + entry + registry[existing.end():]
    else:
        stripped = registry.rstrip()
        if not stripped.endswith('}'):
            raise ValueError(f'{REGISTRY} does not end with a closing brace')
        registry = stripped[:-1] + entry + '}\n'
    # 3. the ladder row
    ladder = read(LADDER, root)
    pattern = re.compile(rf'(            {species} = )\{{scale = [\d.]+, tier = 1, basis = "(\w+)", target = [\d.]+, width = [\d.]+, height = [\d.]+, length = [\d.]+, snout = [\d.]+, headLength = [\d.]+, measured = (?:true|false)\}},')
    found = pattern.search(ladder)
    if not found:
        raise ValueError(f'the Dino.secret.species row of {species} in {LADDER} has an unexpected shape')
    new_row = (f'{{scale = {scale}, tier = 1, basis = "{result["basis"]}", target = {fmt(result["target"])}, width = {fmt(row[0])}, height = {fmt(row[1])}, '
               f'length = {fmt(row[2])}, snout = {fmt(result["snout"])}, headLength = {fmt(result["head"])}, measured = true}},')
    ladder = ladder[:found.start()] + found.group(1) + new_row + ladder[found.end():]
    # 4. SECRET_BOXES
    boxes = read(BOXES, root)
    box_line = re.search(rf"^    '{species}': \([^\n]*\),[^\n]*$", boxes, re.M)
    if not box_line:
        raise ValueError(f'SECRET_BOXES in {BOXES} has no line for {species}')
    boxes = (boxes[:box_line.start()] + f"    '{species}': ({fmt(row[0])}, {fmt(row[1])}, {fmt(row[2])}),  # MEASURED at scale 1 {box[0]:g} x {box[1]:g} x {box[2]:g} (docs/173) x {scale}"
             + boxes[box_line.end():])
    # 5. BOUND_IDS
    bound = read(BOUND, root)
    bound_line = re.search(r'^BOUND_IDS = \{([^\n]*)\}$', bound, re.M)
    if not bound_line:
        raise ValueError(f'BOUND_IDS not found in {BOUND}')
    ids = {k: int(v) for k, v in re.findall(r"'(\w+)': (\d+)", bound_line.group(1))}
    ids[species] = asset_id
    bound = bound[:bound_line.start()] + 'BOUND_IDS = {' + ', '.join(f"'{k}': {v}" for k, v in sorted(ids.items())) + '}' + bound[bound_line.end():]
    write(CONFIG, config, root)
    write(REGISTRY, registry, root)
    write(LADDER, ladder, root)
    write(BOXES, boxes, root)
    write(BOUND, bound, root)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--species', required=True)
    parser.add_argument('--asset-id', type=int, required=True, help='published generate_mesh Model id (the one InsertService:LoadAsset takes)')
    parser.add_argument('--box', type=float, nargs=3, required=True, metavar=('W', 'H', 'L'), help='MEASURED bounding box at growth scale 1, studs')
    parser.add_argument('--head-length', type=float, help='measured head part length at scale 1 (default: 22%% of the body length, an estimate)')
    parser.add_argument('--version', default='v1', help='registry version label (v1 first model, v2 second generation ...)')
    parser.add_argument('--replace', action='store_true', help='allow replacing an already bound slot')
    parser.add_argument('--write', action='store_true', help='apply the edits (default: dry run)')
    parser.add_argument('--runner', help='luau.exe: regenerate the docs/114 size table after --write')
    args = parser.parse_args()
    box = tuple(args.box)
    try:
        if args.write:
            result = apply(args.species, args.asset_id, box, args.head_length, args.version, args.replace)
        else:
            config = read(CONFIG, ROOT)
            match = re.search(SLOT % re.escape(args.species), config)
            if not match:
                raise ValueError(f'{args.species!r} is not a secret species in {CONFIG}')
            if not re.fullmatch(r'[1-9]\d{9,15}', str(args.asset_id)):
                raise ValueError('asset id must be a plain whole number of 10 to 16 digits')
            result = plan(match.group(2), box, args.head_length)
    except ValueError as error:
        print('REFUSED:', error)
        return 1
    print(('WROTE' if args.write else 'DRY RUN'), args.species, args.asset_id)
    print(f"  basis {result['basis']} target {result['target']}  scale {result['scale']}  box at spawn {result['row']}  snout {result['snout']}  "
          f"head {result['head']} ({'measured' if result['head_measured'] else 'ESTIMATE: 22% of the length, pass --head-length once measured'})")
    if not args.write:
        print('  nothing changed; add --write to apply')
        return 0
    if args.runner:
        done = subprocess.run([sys.executable, str(ROOT / 'tools/verify_scale_ladder.py'), '--runner', args.runner, '--write-doc'], capture_output=True, text=True)
        print(done.stdout.strip() or done.stderr.strip())
    print('  next: add the species to docs/173 and docs/77, run verify_secret_species / verify_scale_ladder / verify_lowpoly_dinos / verify_hit_sizes / verify_mouth_reach / verify_camera_framing')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
