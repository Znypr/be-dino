"""Render the VFX lab fire textures (docs/143): headless Blender renders every frame, then Pillow only pastes finished frames into sheets.

    python tools/render_vfx_lab_fire.py [--only fireTongueSheet] [--samples 48]
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BLENDER = Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
FRAMES = ROOT / "build" / "vfx-lab-frames"
OUT = ROOT / "resources" / "effects" / "vfx-lab"
SHEETS = {"fireTongueBig": (512, 2), "fireTongueSwirl": (512, 2), "fireTongueSheet": 256, "fireClusterSheet": 256, "fireSparkSheet": 128, "firePuffSheet": 256}


def main():
    args = sys.argv[1:]
    only = args[args.index("--only") + 1] if "--only" in args else None
    extra = ["--samples", args[args.index("--samples") + 1]] if "--samples" in args else []
    cmd = [str(BLENDER), "-b", "--factory-startup", "--python", str(ROOT / "tools/blender/build_vfx_lab_fire.py"), "--",
           "--frames", str(FRAMES), "--out", str(OUT), "--blend", str(ROOT / "tools/blender/vfx_lab_fire_v1.blend")] + (["--only", only] if only else []) + extra
    subprocess.run(cmd, check=True)
    for name, spec in SHEETS.items():
        if only and only != name:
            continue
        cell, grid = spec if isinstance(spec, tuple) else (spec, 4)
        img = Image.new("RGBA", (cell * grid, cell * grid), (0, 0, 0, 0))
        for i in range(grid * grid):
            fr = Image.open(FRAMES / name / f"f_{i + 1:04d}.png").convert("RGBA")
            img.paste(fr, ((i % grid) * cell, (i // grid) * cell))
        OUT.mkdir(parents=True, exist_ok=True)
        img.save(OUT / f"{name}.png", optimize=True)
        print("sheet", name)


if __name__ == "__main__":
    main()
