#!/usr/bin/env python3
"""BD-1052 (docs/188): fail when docs/catalog/ is stale.

Rebuilds the team catalogue in memory (tools/build_catalog.py) and compares it with the files in docs/catalog/. A stale page, a
missing page or an extra page fails with the fix command. Also enforces the shape rules of the owner's answers: at most 8 pages and
no page for a single item.

    python tools/verify_catalog.py --runner /tmp/luau/luau
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_catalog  # noqa: E402

ROOT = build_catalog.ROOT
FIX = "python tools/build_catalog.py"


def problems(root: Path = ROOT, runner: str | None = None, folder: Path | None = None) -> list[str]:
    folder = folder or (root / build_catalog.DEFAULT_OUT)
    expected = build_catalog.build(root, runner, public=False)  # image links are relative to the canonical folder
    errors: list[str] = []
    if len(expected) > build_catalog.MAX_PAGES:
        errors.append("the catalogue would have %d pages; the hard cap is %d (docs/188)" % (len(expected), build_catalog.MAX_PAGES))
    if not folder.is_dir():
        return errors + [f"{folder} does not exist. Fix: {FIX}"]
    actual = {p.name: p.read_text(encoding="utf-8") for p in folder.glob("*.md")}
    for name in sorted(set(expected) | set(actual)):
        if name not in actual:
            errors.append(f"{name} is missing from docs/catalog/. Fix: {FIX}")
        elif name not in expected:
            errors.append(f"docs/catalog/{name} is not produced by the tool any more (extra page or a page for one item). Fix: {FIX}")
        elif actual[name].replace("\r\n", "\n") != expected[name]:
            diff = list(difflib.unified_diff(actual[name].replace("\r\n", "\n").splitlines(), expected[name].splitlines(), "docs/catalog/" + name, "rebuilt", lineterm="", n=0))
            shown = "\n    ".join(diff[:12])
            errors.append(f"docs/catalog/{name} is out of date ({max(0, len(diff) - 2)} differing lines). Fix: {FIX}\n    {shown}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", help="pinned Luau runner")
    args = parser.parse_args(argv)
    errors = problems(ROOT, args.runner)
    for error in errors:
        print("FAIL:", error)
    if errors:
        print(f"The team catalogue is stale or malformed. Run `{FIX}` and commit docs/catalog/.")
        return 1
    print("catalogue ok: docs/catalog matches the game code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
