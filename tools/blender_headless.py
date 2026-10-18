"""Find Blender and run a script in a SEPARATE headless process (BD-641, docs/163). Shared by tools/animation_strip.py and
tools/check_model_for_roblox.py. It never talks to the live Blender MCP session (another agent may be using it).

    from blender_headless import find_blender, run_script
"""
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_blender():
    """Path of blender.exe (or blender), or None. Order: $BLENDER, PATH, C:/Program Files/Blender Foundation/Blender */ (newest)."""
    env = os.environ.get('BLENDER')
    if env and Path(env).exists():
        return env
    on_path = shutil.which('blender')
    if on_path:
        return on_path
    pattern = 'C:/Program Files/Blender Foundation/Blender */blender.exe'
    hits = sorted(glob.glob(pattern), key=lambda p: [int(x) if x.isdigit() else 0 for x in Path(p).parent.name.replace('Blender', '').strip().split('.')])
    return hits[-1] if hits else None


def run_script(script, args, blender=None, timeout=600):
    """Run `blender --background --factory-startup --python script -- args`. Returns (returncode, combined output text)."""
    exe = blender or find_blender()
    if not exe:
        raise FileNotFoundError('Blender was not found. Install it, put it on PATH or set the BLENDER environment variable.')
    cmd = [exe, '--background', '--factory-startup', '--python', str(script), '--'] + [str(a) for a in args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, (proc.stdout or '') + (proc.stderr or '')


if __name__ == '__main__':
    print(find_blender() or 'Blender not found', file=sys.stderr if not find_blender() else sys.stdout)
