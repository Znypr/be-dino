#!/usr/bin/env python3
"""No single Luau module under src/ (server, client, shared) may grow past 120 KB (docs/150).

ProfileRepository.luau reached 142 KB because every new feature added its transactions to that one file. The offline harnesses embed
modules as text (tools/verify_load.py MAX_EMBED_BYTES had to be raised twice in one day to keep loading it) and Luau has hard limits
per function (local registers, see tools/verify_local_budget.py, which already covers all of src/ with a fail line of 185 of 200), so
a module that big is a problem long before the limit bites. This check fails CI when any hand-written file under src/ is larger than
LIMIT_BYTES (LF line endings), and warns above WARN_BYTES, so the split into focused modules stays done. When a module nears the
warning line, split it by feature (docs/150 section "Size guard audit").

Not counted: generated data tables (src/shared/IconRaster, ResourceGeometry, IconTiles and everything under CreatureGenes/Chunks and CreatureData/Chunks).
They are exempt only while they stay data: a file on that list with more than GENERATED_MAX_LINES lines is hand-written code and
is checked like any other module.

KNOWN_OVER is a ratchet for modules that were already past the limit when the check was extended to the client (Bootstrap.client.luau,
126 KB, wrapped HUD function; 46 verifiers read its text, see docs/150). They fail above their own ceiling, so they can no longer
grow; new client features go into their own module. Lower the ceiling when code moves out. The entry stays after the file drops below the
limit (BD-1088: Bootstrap 123,680 -> 94,500) so freed room cannot be spent again.

    python tools/verify_server_module_size.py [--limit BYTES] [--top N] [--selftest]
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LIMIT_BYTES = 120_000
WARN_BYTES = 90_000
GENERATED_MAX_LINES = 5
GENERATED_NAMES = {"IconRaster.luau", "ResourceGeometry.luau", "IconTiles.luau"}
GENERATED_DIRS = ("CreatureGenes/Chunks/", "CreatureData/Chunks/")
# path under src/ -> ceiling in bytes (LF). Bootstrap was over LIMIT_BYTES on 2026-10-18 (126,160); its ceiling now sits just above its real size so freed room cannot be spent again (BD-1088).
KNOWN_OVER = {"client/Bootstrap.client.luau": 89_600}  # was 127,000, 123,900 (BD-617), 123,680 (BD-1019); BD-1088 moved the shop screens to ShopScreens.luau (94,500) and the toast stack to Toasts.luau: 89,478. A ratchet below the limit too: lower it when code moves out


def size_of(path: Path) -> int:
    """Bytes with LF line endings, so a Windows checkout (CRLF) and CI (LF) measure the same."""
    return len(path.read_bytes().replace(b"\r\n", b"\n"))


def is_generated(rel: str, data: bytes) -> bool:
    listed = rel.rsplit("/", 1)[-1] in GENERATED_NAMES or any(part in rel for part in GENERATED_DIRS)
    return listed and data.count(b"\n") <= GENERATED_MAX_LINES


def scan(folder: Path, limit: int = LIMIT_BYTES, warn: int = WARN_BYTES, known_over: dict[str, int] | None = None):
    """Returns (sizes sorted largest first as (bytes, rel), errors, warnings, skipped generated count)."""
    known_over = KNOWN_OVER if known_over is None else known_over
    sizes: list[tuple[int, str]] = []
    skipped = 0
    for path in folder.rglob("*.luau"):
        rel = path.relative_to(folder).as_posix()
        data = path.read_bytes().replace(b"\r\n", b"\n")
        if is_generated(rel, data):
            skipped += 1
            continue
        sizes.append((len(data), rel))
    sizes.sort(reverse=True)
    errors, warnings = [], []
    for size, rel in sizes:
        ceiling = known_over.get(rel)
        if ceiling is not None:
            if size > ceiling:
                errors.append(f"{rel} is {size:,} bytes: over its ratchet ceiling of {ceiling:,} (it was already past the {limit:,} limit and may not grow; "
                              f"put new code in its own module, see docs/150)")
            elif size > limit:
                warnings.append(f"{rel} is {size:,} bytes: known to be over {limit:,} (ceiling {ceiling:,}); move code out and lower the ceiling")
            continue
        if size > limit:
            errors.append(f"{rel} is {size:,} bytes: over the {limit:,} byte limit for one module (split it by feature, see docs/150)")
        elif size > warn:
            warnings.append(f"{rel} is {size:,} bytes: past {warn:,}, plan a split before it reaches {limit:,}")
    return sizes, errors, warnings, skipped


def selftest() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for sub in ("server", "client", "shared/CreatureGenes/Chunks"):
            (root / sub).mkdir(parents=True)
        (root / "server/Small.luau").write_bytes(b"local x = 1\r\n" * 10)
        # an oversized module fails in every one of the three folders
        for sub in ("server", "client", "shared"):
            (root / sub / "Big.luau").write_bytes(b"-- " + b"x" * 130_000 + b"\n")
            _, errors, _, _ = scan(root, known_over={})
            if len([e for e in errors if e.startswith(f"{sub}/Big.luau")]) != 1:
                failures.append(f"an oversized {sub} module was not caught: {errors}")
            (root / sub / "Big.luau").unlink()
        _, errors, _, _ = scan(root, known_over={})
        if errors:
            failures.append(f"small modules were flagged: {errors}")
        # generated data is skipped only while it is data (few lines)
        (root / "shared/IconRaster.luau").write_bytes(b"--!strict\nreturn {" + b"1," * 200_000 + b"}\n")
        (root / "shared/CreatureGenes/Chunks/a_1.luau").write_bytes(b"return [==[" + b"f" * 150_000 + b"]==]")
        _, errors, _, skipped = scan(root, known_over={})
        if errors or skipped != 2:
            failures.append(f"generated tables were not exempt: errors={errors} skipped={skipped}")
        (root / "shared/IconRaster.luau").write_bytes((b"local x = 1\n" * 12_000) + b"return x\n")
        _, errors, _, _ = scan(root, known_over={})
        if len(errors) != 1 or "IconRaster.luau" not in errors[0]:
            failures.append(f"hand-written code hiding behind a generated name was not caught: {errors}")
        (root / "shared/IconRaster.luau").unlink()
        # ratchet: a known-over module may sit at its size, may not grow past the ceiling
        (root / "client/Boot.luau").write_bytes(b"-- " + b"x" * 125_000 + b"\n")
        _, errors, warnings, _ = scan(root, known_over={"client/Boot.luau": 126_000})
        if errors or not warnings:
            failures.append(f"a known-over module at its ceiling should only warn: {errors} {warnings}")
        (root / "client/Boot.luau").write_bytes(b"-- " + b"x" * 127_000 + b"\n")
        _, errors, _, _ = scan(root, known_over={"client/Boot.luau": 126_000})
        if len(errors) != 1 or "ratchet" not in errors[0]:
            failures.append(f"a known-over module growing past its ceiling was not caught: {errors}")
    for failure in failures:
        print("selftest FAILED:", failure)
    if failures:
        return 1
    print("selftest ok: an oversized server/client/shared module fails, generated tables are exempt only as data, the ratchet blocks growth")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=LIMIT_BYTES, help=f"bytes per module (default {LIMIT_BYTES})")
    parser.add_argument("--top", type=int, default=8, help="list the N largest modules")
    parser.add_argument("--selftest", action="store_true", help="prove the check on synthetic files and exit")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    sizes, errors, warnings, skipped = scan(SRC, args.limit)
    for size, rel in sizes[: args.top]:
        print(f"  {size:>9,}  {rel}")
    for line in warnings:
        print("warning:", line)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Module sizes ok: {len(sizes)} modules under src/ ({skipped} generated data tables skipped), "
          f"largest {sizes[0][1]} at {sizes[0][0]:,} bytes (limit {args.limit:,}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
