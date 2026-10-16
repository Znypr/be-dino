"""Regenerate the BD-131 weather particle textures: headless Blender renders every texture, then Pillow only pastes the finished
128 px frames of each flipbook into a 4 x 4 sheet (512 x 512). No pixel is drawn or edited in Python.

    python tools/render_weather_textures.py                  # everything (about 3 minutes)
    python tools/render_weather_textures.py --only dustSand  # one texture (others are rebuilt but not rendered)
    python tools/render_weather_textures.py --assemble-only  # re-paste existing frames from build/fx-weather-frames

Outputs: resources/effects/fx-v2/<name>.png (see the table in tools/blender/build_fx_weather.py) and the catalogue
tools/blender/fx_weather_v1.blend. Frame 1 goes top-left, then row by row, which is how a Roblox ParticleEmitter reads a 4 x 4 flipbook.
"""
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
SHEETS = ['snowFlakeSheet', 'ashFlake', 'emberSpark', 'dustSand', 'auroraCurtain', 'bloodMoonMotes']
CELL, GRID = 128, 4


def assemble(frames_dir, out_dir, names):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', default=str(ROOT / 'build/fx-weather-frames'))
    ap.add_argument('--out', default=str(ROOT / 'resources/effects/fx-v2'))
    ap.add_argument('--blend', default=str(ROOT / 'tools/blender/fx_weather_v1.blend'))
    ap.add_argument('--only', default=None)
    ap.add_argument('--samples', default=None)
    ap.add_argument('--assemble-only', action='store_true')
    a = ap.parse_args()
    frames, out = Path(a.frames), Path(a.out)
    if not a.assemble_only:
        cmd = [str(BLENDER), '-b', '--factory-startup', '--python', str(ROOT / 'tools/blender/build_fx_weather.py'), '--',
               '--frames', str(frames), '--out', str(out)]
        if a.only:
            cmd += ['--only', a.only]
        else:
            cmd += ['--blend', a.blend]
        if a.samples:
            cmd += ['--samples', a.samples]
        subprocess.run(cmd, check=True)
    assemble(frames, out, [a.only] if a.only in SHEETS else ([] if a.only else SHEETS))
    sys.exit(0)


if __name__ == '__main__':
    main()
