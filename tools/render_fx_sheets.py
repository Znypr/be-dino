"""Regenerate the BD-187 smoke flipbooks and BD-189 motif sheets end to end (headless Blender, then Pillow assembly).

    python tools/render_fx_sheets.py                    # everything (about 10 minutes on a many-core CPU)
    python tools/render_fx_sheets.py --only smoke       # or: --only motifs
    python tools/render_fx_sheets.py --samples 64 --step 4 --frames build/fx-preview --no-assemble    # quick look

1. Blender 5.1 (Cycles, CPU) renders 16 frames per sheet from tools/blender/build_fx_smoke.py and
   tools/blender/build_fx_motifs.py, and saves the scenes as tools/blender/fx_smoke_v1.blend and fx_motifs_v1.blend;
2. tools/assemble_fx_sheets.py pastes the finished frames into 512 x 512 grids in resources/effects/fx-v2/.
Then run tools/verify_fx_textures.py and tools/fx_contact_sheet.py.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
JOBS = {
    'smoke': ('tools/blender/build_fx_smoke.py', 'tools/blender/fx_smoke_v1.blend'),
    'motifs': ('tools/blender/build_fx_motifs.py', 'tools/blender/fx_motifs_v1.blend'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', choices=sorted(JOBS), default=None)
    ap.add_argument('--frames', default='build/fx-frames')
    ap.add_argument('--samples', type=int, default=None, help='override Cycles samples (quick previews)')
    ap.add_argument('--step', type=int, default=1, help='render every Nth frame (previews; the assembler needs all 16)')
    ap.add_argument('--no-assemble', action='store_true')
    ap.add_argument('--blender', default=str(BLENDER))
    a = ap.parse_args()
    frames = (ROOT / a.frames).resolve()
    for name, (script, blend) in JOBS.items():
        if a.only and a.only != name:
            continue
        cmd = [a.blender, '-b', '--factory-startup', '--python', str(ROOT / script), '--', '--frames', str(frames),
               '--step', str(a.step)]
        if a.step == 1 and a.samples is None:
            cmd += ['--blend', str(ROOT / blend)]
        if a.samples:
            cmd += ['--samples', str(a.samples)]
        print('+', ' '.join(cmd))
        subprocess.run(cmd, check=True, cwd=ROOT)
    if not a.no_assemble:
        subprocess.run([sys.executable, str(ROOT / 'tools/assemble_fx_sheets.py'), '--frames', str(frames)], check=True, cwd=ROOT)


if __name__ == '__main__':
    main()
