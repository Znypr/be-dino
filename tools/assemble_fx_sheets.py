"""Paste the finished Blender frames of the BD-187 / BD-189 flipbooks into 4 x 4 sheets (512 x 512 PNG).

Pillow only pastes whole finished renders into their grid cell (no drawing, no recolouring, alpha untouched):

    python tools/assemble_fx_sheets.py --frames build/fx-frames --out resources/effects/fx-v2

Frames come from tools/blender/build_fx_smoke.py and tools/blender/build_fx_motifs.py (f_0001.png ... f_0016.png per sheet,
128 px each). Frame 1 goes top-left, then row by row, which is how a Roblox ParticleEmitter reads a 4 x 4 flipbook.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image

SHEETS = ['smokeSoft', 'smokeDense', 'smokeWispy',
          'motifDroplets', 'motifSoftSparks', 'motifSnowCrystals', 'motifPebbles', 'motifEmbers', 'motifAurora', 'motifCrimson']
CELL, GRID = 128, 4


def assemble(frames_dir, out_dir, names=SHEETS):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        files = sorted((frames_dir / name).glob('f_*.png'))
        if len(files) != GRID * GRID:
            print(f'{name}: expected {GRID * GRID} frames in {frames_dir / name}, found {len(files)}; skipped')
            continue
        sheet = Image.new('RGBA', (CELL * GRID, CELL * GRID), (0, 0, 0, 0))
        for i, f in enumerate(files):
            im = Image.open(f).convert('RGBA')
            if im.size != (CELL, CELL):
                raise SystemExit(f'{f}: expected {CELL}x{CELL}, got {im.size}')
            sheet.paste(im, ((i % GRID) * CELL, (i // GRID) * CELL))
        dest = out_dir / f'{name}.png'
        sheet.save(dest, optimize=True)
        print('wrote', dest, sheet.size, dest.stat().st_size, 'bytes')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', default='build/fx-frames')
    ap.add_argument('--out', default='resources/effects/fx-v2')
    ap.add_argument('--only', default=None)
    a = ap.parse_args()
    assemble(Path(a.frames), Path(a.out), [a.only] if a.only else SHEETS)
    sys.exit(0)
