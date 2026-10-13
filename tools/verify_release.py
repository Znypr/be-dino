"""Fail when a release-critical Config value is wrong in source or a generated place.

    python tools/verify_release.py                      # default profile: src + current build/ delivery
    python tools/verify_release.py --profile playtest   # builds the playtest place in memory and verifies it
    python tools/verify_release.py --profile playtest --place build/BeDino-Build020-playtest.rbxlx

Rules live in tools/release_profiles.py. Studio-only flags may stay true only while
the server still guards them with RunService:IsStudio() and game.GameId == 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as packager  # noqa: E402
import release_profiles as profiles  # noqa: E402


def config_from_place(data: bytes) -> str:
    """Return the packaged ReplicatedStorage.Shared.Config source from .rbxlx bytes."""
    root = ET.fromstring(data)

    def name(node):
        found = node.find("Properties/string[@name='Name']")
        return found.text if found is not None else None

    def child(parent, wanted):
        matches = [n for n in parent.findall("Item") if name(n) == wanted]
        if len(matches) != 1:
            raise ValueError(f"Expected one {wanted!r} instance in generated place, found {len(matches)}")
        return matches[0]

    config = child(child(child(root, "ReplicatedStorage"), "Shared"), "Config")
    if config.attrib.get("class") != "ModuleScript":
        raise ValueError("Generated Config is not a ModuleScript")
    return config.find("Properties/ProtectedString[@name='Source']").text or ""


def studio_guard_errors(server_dir: Path = ROOT / "src/server") -> list[str]:
    """Studio-local flags must only be read behind the unpublished-Studio guard."""
    errors = []
    guard = re.compile(r"IsStudio\(\)\s+and\s+game\.GameId\s*==\s*0")
    for path in sorted(server_dir.glob("**/*.luau")):
        lines = path.read_text(encoding="utf-8").splitlines()
        defines = [line for line in lines if re.match(r"\s*local\s+localPreview\s*=", line)]
        for line in defines:
            if not guard.search(line):
                errors.append(f"{path.name}: localPreview is no longer limited to unpublished Studio: {line.strip()}")
        for number, line in enumerate(lines, 1):
            for flag in profiles.STUDIO_LOCAL_FLAGS:
                if f"Config.{flag}" in line and not (guard.search(line) or ("localPreview" in line and defines)):
                    errors.append(f"{path.name}:{number}: Config.{flag} read without the unpublished-Studio guard")
    return errors


def verify_place(data: bytes, profile: str, manifest: dict | None = None, allow_dirty: bool = False):
    report = profiles.verify_source(config_from_place(data), profile)
    if manifest is not None:
        if manifest.get("place_sha256") != hashlib.sha256(data).hexdigest():
            report.errors.append("manifest place_sha256 does not match the place bytes")
        if profile != "default" and manifest.get("profile") != profile:
            report.errors.append(f"manifest profile is {manifest.get('profile')!r}, expected {profile!r}")
        if profile != "default" and manifest.get("git_dirty") is not False:
            message = (f"manifest git_dirty={manifest.get('git_dirty')!r} (commit {manifest.get('git_commit')}): "
                       "publish only a place built from a clean, tagged commit")
            (report.warnings if allow_dirty else report.errors).append(message)
    return report


def run(profile: str, place: Path | None = None, root: Path = ROOT, allow_dirty: bool = False) -> tuple[list[str], list[str]]:
    errors, warnings = [], []

    seen = set()

    def merge(label, report):
        for error in report.errors:
            if error not in seen:
                seen.add(error)
                errors.append(f"[{label}] {error}")
        for warning in report.warnings:
            if warning not in seen:
                seen.add(warning)
                warnings.append(f"[{label}] {warning}")

    errors.extend(f"[guards] {e}" for e in studio_guard_errors(root / "src/server"))
    source = (root / packager.CONFIG_PATH).read_text(encoding="utf-8")
    if profile == "default":
        merge("source", profiles.verify_source(source, "default"))
        place = place or root / f"build/BeDino-Build{packager.build_version(root)}.rbxlx"
    else:
        # The source itself must already satisfy every profile-independent invariant.
        merge("source", profiles.verify_source(source, "default"))
    if place is not None:
        manifest_path = place.with_suffix(".manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
        if manifest is None:
            errors.append(f"[place] missing {manifest_path.name}")
        merge(place.name, verify_place(place.read_bytes(), profile, manifest, allow_dirty))
    elif profile != "default":
        data, _, build_report = packager.build_profile(profile, root / "default.project.json")
        merge(f"{profile} build", build_report)
        merge(f"{profile} place", verify_place(data, profile))
    return errors, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default="default", choices=sorted(profiles.PROFILES))
    parser.add_argument("--place", type=Path, help="verify this generated .rbxlx instead of building")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="rehearsal only: accept a --place whose manifest records uncommitted changes")
    args = parser.parse_args(argv)
    errors, warnings = run(args.profile, args.place, allow_dirty=args.allow_dirty)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    enforced = sorted({rule.key for rule in profiles.rules_for(args.profile)})
    if errors:
        print(f"Release verification FAILED for profile {args.profile!r}: {len(errors)} error(s).")
        return 1
    print(f"Release verification passed for profile {args.profile!r}: {len(enforced)} keys enforced "
          f"({', '.join(enforced)}); Studio-only guards intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
