"""Regenerate the BD-430 / BD-431 anime FX P0 + P1 assets end to end (headless Blender, then Pillow assembly of finished frames).

    python tools/render_fx_anime.py                      # everything (about a minute)
    python tools/render_fx_anime.py --only flameTongue   # one scene (a flipbook, a gradient, speedStreaks, or `meshes`)
    python tools/render_fx_anime.py --samples 32         # quick look (do not commit)
    python tools/render_fx_anime.py --assemble-only      # re-paste existing frames from build/fx-anime-frames

1. Blender 5.1 (Cycles, CPU) runs tools/blender/build_fx_anime.py: renders the flipbook frames (flameTongue, starPop),
   the four single images (domeGradient, shaftGradient, shellEdge, speedStreaks) straight into resources/effects/fx-v2/,
   exports the three FX meshes to assets/blender/fx/ (shock-dome, shaft-cone, aura-shell FBX + fx-meshes.json),
   renders the three mesh preview shots, and saves the catalogue tools/blender/fx_anime_v1.blend;
2. tools/assemble_fx_sheets.py pastes the 16 finished 128 px frames of each flipbook into a 512 x 512 grid. Pillow never draws.
Then run tools/verify_fx_textures.py and `python tools/fx_contact_sheet.py --anime`.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from assemble_fx_sheets import assemble  # noqa: E402

BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
SHEETS = ['flameTongue', 'starPop']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    ap.add_argument('--frames', default='build/fx-anime-frames')
    ap.add_argument('--out', default='resources/effects/fx-v2')
    ap.add_argument('--meshes', default='assets/blender/fx')
    ap.add_argument('--shots', default='docs/evidence/2026-10-17-vfx')
    ap.add_argument('--blend', default='tools/blender/fx_anime_v1.blend')
    ap.add_argument('--samples', type=int, default=None)
    ap.add_argument('--assemble-only', action='store_true')
    ap.add_argument('--blender', default=str(BLENDER))
    a = ap.parse_args()
    frames, out = (ROOT / a.frames).resolve(), (ROOT / a.out).resolve()
    if not a.assemble_only:
        cmd = [a.blender, '-b', '--factory-startup', '--python', str(ROOT / 'tools/blender/build_fx_anime.py'), '--',
               '--frames', str(frames), '--out', str(out), '--meshes', str(ROOT / a.meshes), '--shots', str(ROOT / a.shots)]
        if a.only:
            cmd += ['--only', a.only]
        elif a.samples is None:
            cmd += ['--blend', str(ROOT / a.blend)]
        if a.samples:
            cmd += ['--samples', str(a.samples)]
        print('+', ' '.join(cmd))
        subprocess.run(cmd, check=True, cwd=ROOT)
    names = [a.only] if a.only in SHEETS else ([] if a.only else SHEETS)
    assemble(frames, out, names)


if __name__ == '__main__':
    main()
