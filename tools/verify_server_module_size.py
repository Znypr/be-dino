#!/usr/bin/env python3
"""No single server module may grow past 120 KB (docs/150).

ProfileRepository.luau reached 142 KB because every new feature added its transactions to that one file. The offline harnesses embed
server modules as text (tools/verify_load.py MAX_EMBED_BYTES had to be raised twice in one day to keep loading it) and Luau has hard
limits per function (local registers, see tools/verify_local_budget.py), so a module that big is a problem long before the limit bites.
This check fails CI when any file under src/server is larger than LIMIT_BYTES (LF line endings), and warns above WARN_BYTES, so the
split into focused modules (ProfileFusion, ProfileEggs, ...) stays done. When a module nears the warning line, split it by feature.

    python tools/verify_server_module_size.py [--limit BYTES] [--top N] [--selftest]
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LIMIT_BYTES = 120_000
WARN_BYTES = 90_000


def size_of(path: Path) -> int:
    """Bytes with LF line endings, so a Windows checkout (CRLF) and CI (LF) measure the same."""
    return len(path.read_bytes().replace(b"\r\n", b"\n"))


def scan(folder: Path, limit: int = LIMIT_BYTES, warn: int = WARN_BYTES) -> tuple[list[tuple[int, str]], list[str], list[str]]:
    sizes = sorted(((size_of(p), p.name) for p in folder.glob("*.luau")), reverse=True)
    errors = [f"{name} is {size:,} bytes: over the {limit:,} byte limit for one server module (split it by feature, see docs/150)"
              for size, name in sizes if size > limit]
    warnings = [f"{name} is {size:,} bytes: past {warn:,}, plan a split before it reaches {limit:,}" for size, name in sizes if warn < size <= limit]
    return sizes, errors, warnings


def selftest() -> int:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        (root / "Small.luau").write_bytes(b"local x = 1\r\n" * 10)
        (root / "Big.luau").write_bytes(b"-- " + b"x" * 130_000 + b"\n")
        _, errors, _ = scan(root)
        if len(errors) != 1 or "Big.luau" not in errors[0]:
            print("selftest FAILED: an oversized module was not caught")
            return 1
        (root / "Big.luau").write_bytes(b"-- " + b"x" * 1000 + b"\n")
        _, errors, _ = scan(root)
        if errors:
            print("selftest FAILED: a small module was flagged")
            return 1
    print("selftest ok: an oversized module fails, small ones pass")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=LIMIT_BYTES, help=f"bytes per module (default {LIMIT_BYTES})")
    parser.add_argument("--top", type=int, default=5, help="list the N largest modules")
    parser.add_argument("--selftest", action="store_true", help="prove the check on synthetic files and exit")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    sizes, errors, warnings = scan(ROOT / "src" / "server", args.limit)
    for size, name in sizes[: args.top]:
        print(f"  {size:>9,}  {name}")
    for line in warnings:
        print("warning:", line)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Server module sizes ok: {len(sizes)} modules, largest {sizes[0][1]} at {sizes[0][0]:,} bytes (limit {args.limit:,}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
