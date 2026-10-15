"""BD-146 structural verifier: one local visual per character; no stale old species when the new clone fails.
Source-level checks of src/client/ResourceVisuals.client.luau (no Luau runner needed)."""
from pathlib import Path
import sys

src = (Path(__file__).resolve().parents[1] / "src/client/ResourceVisuals.client.luau").read_text(encoding="utf-8")
body = src[src.index("local model = Resources.clone(id,realGenes)"):]
fail = body[:body.index("if not character.Parent")]
after = body[body.index("if not character.Parent"):]
checks = {
    "clone failure destroys stale previous visual": "previous:Destroy()" in fail and "return" in fail,
    "clone failure restores the server shell": "ShellTransparency" in fail and "LocalTransparencyModifier = 0" in fail,
    "every LocalMeshVisual destroyed before attaching": 'extra.Name == "LocalMeshVisual"' in after and "extra:Destroy()" in after,
    "shell hiding records original transparency": src.count('SetAttribute("ShellTransparency"') >= 2,
    "fallback shell hidden through hideShell": "hideShell(character)" in after,
}
bad = [k for k, v in checks.items() if not v]
print("verify_equip_visual:", "FAIL " + "; ".join(bad) if bad else "ok (%d checks)" % len(checks))
sys.exit(1 if bad else 0)
