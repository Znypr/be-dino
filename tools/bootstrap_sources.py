#!/usr/bin/env python3
"""The text of src/client/Bootstrap.client.luau plus the client modules its screens moved to (BD-1020, docs/160 section 10).

Bootstrap's render function used to hold every screen. Cohesive blocks now live in their own modules (a screen builder, a state
holder, event wiring) so the main chunk stays under the local-register and size ceilings. Many verifiers search the text of the client
entry point for a wiring fragment; they call text() so a fragment is found whichever of the files holds it. Add a module to MODULES
when more code moves out of Bootstrap. Order: Bootstrap first, then the modules.

    python tools/bootstrap_sources.py        # prints the size of each file
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "src" / "client"
BOOTSTRAP = "Bootstrap.client.luau"
MODULES = ("ShopScreens.luau",)
# The ratchet for Bootstrap's own top-level `local` lines (every verifier that counts them reads this one number). Luau allows 200 locals per
# function; the main chunk had 188 such lines on 2026-10-18 and 174 after the shop screens moved out. Lower it when more code moves out,
# never raise it: new client features go into their own module (docs/160 section 10).
MAX_TOP_LOCALS = 176


def paths(root: Path | None = None) -> list[Path]:
    folder = (root or ROOT) / "src" / "client"
    return [folder / BOOTSTRAP] + [folder / name for name in MODULES]


def text(root: Path | None = None) -> str:
    """Bootstrap and the moved modules as one string (LF line ends)."""
    return "\n".join(p.read_text(encoding="utf-8") for p in paths(root))


if __name__ == "__main__":
    for p in paths():
        print(f"{len(p.read_bytes().replace(b'\r\n', b'\n')):>8,}  {p.relative_to(ROOT).as_posix()}")
