"""Run tools/blender/test_cockatoo_animations.luau against assets/blender/creatures/CockatooAnimations.luau with plain Luau (BD-621 test model)."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
luau = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / ".cache/be-dino/luau-0.741/luau.exe")
mod = (ROOT / "assets/blender/creatures/CockatooAnimations.luau").read_text(encoding="utf8").replace("--!strict", "", 1)
assert mod.rstrip().endswith("return CockatooAnimations")
mod = mod.rstrip()[: -len("return CockatooAnimations")] + "local M = CockatooAnimations\n"
test = (ROOT / "tools/blender/test_cockatoo_animations.luau").read_text(encoding="utf8")
src = test.replace("--@MODULE@", mod, 1)
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / "cockatoo_test.luau"
    f.write_text(src, encoding="utf8")
    r = subprocess.run([luau, str(f)], capture_output=True, text=True)
print(r.stdout + r.stderr)
sys.exit(r.returncode)
