"""Dependency-free packager for this project's deliberately small Rojo subset.

Python 3.10+; creates a textual Roblox place. Not a general Rojo replacement.
Unsupported project fields fail rather than silently changing the build.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tier_coat  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Roblox Technology enum: Compatibility/Legacy=0, Voxel=1, Future=2, ShadowMap=3. Compatibility is sunset, so an unset
# value triggers Studio's "Lighting Technology Migration" dialog on every open. Write Voxel (what Studio migrates to).
LIGHTING_TECHNOLOGY = 1


def build(project_path=ROOT / "default.project.json", transform=None, workspace_properties=None):
    """Package the project. `transform(relative_path, source) -> source` lets a
    release profile rewrite generated sources; `src/` itself is never modified.
    `workspace_properties` is a list of (xml tag, property name, text) written onto the Workspace item (BD-502 gate 4:
    StreamingEnabled and its radii are not scriptable at runtime, so the build writes them)."""
    project_path = Path(project_path)
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if set(project) != {"name", "tree"}:
        raise ValueError("Unsupported top-level project field")
    root = ET.Element("roblox", {"version": "4"})
    ET.SubElement(root, "External").text = "null"
    ET.SubElement(root, "External").text = "nil"
    sources = {}
    counter = 0
    written_workspace = []

    def item(parent, name, class_name, source=None):
        nonlocal counter
        counter += 1
        node = ET.SubElement(parent, "Item", {"class": class_name, "referent": f"RBX{counter}"})
        props = ET.SubElement(node, "Properties")
        ET.SubElement(props, "string", {"name": "Name"}).text = name
        if source is not None:
            ET.SubElement(props, "ProtectedString", {"name": "Source"}).text = source
        return node

    def directory(parent, path):
        if not path.is_dir():
            raise ValueError(f"Missing source directory: {path}")
        names = set()
        for entry in sorted(path.iterdir()):
            if entry.is_dir():
                name, kind = entry.name, "Folder"
            elif entry.suffix == ".rbxmx":
                imported = ET.parse(entry).getroot().findall("Item")
                if len(imported) != 1 or imported[0].attrib["class"] != "Model":
                    raise ValueError("Expected one native resource Model")
                node = imported[0]
                for nested in node.iter("Item"):
                    counter_id = nested.attrib.get("referent", "")
                    nested.attrib["referent"] = "RESOURCE_" + entry.stem + "_" + counter_id
                parent.append(node)
                continue
            elif entry.suffix == ".luau":
                name, kind = entry.stem, "ModuleScript"
                if name.endswith(".server"):
                    name, kind = name[:-7], "Script"
                elif name.endswith(".client"):
                    name, kind = name[:-7], "LocalScript"
            else:
                raise ValueError(f"Unsupported source file: {entry}")
            if name in names:
                raise ValueError(f"Duplicate instance name: {name}")
            names.add(name)
            source = None if entry.is_dir() else entry.read_text(encoding="utf-8")
            if source is not None and transform is not None:
                source = transform(entry.relative_to(project_path.parent).as_posix(), source)
            child = item(parent, name, kind, source)
            if entry.is_dir():
                directory(child, entry)
            else:
                sources[entry.relative_to(project_path.parent).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

    def descend(parent, name, spec):
        nonlocal counter
        unknown = [k for k in spec if k.startswith("$") and k not in {"$className", "$path"}]
        if unknown:
            raise ValueError(f"Unsupported project properties: {unknown}")
        node = item(parent, name, spec.get("$className", "Folder"))
        if spec.get("$className") == "Workspace":
            for tag, prop, text in workspace_properties or []:
                ET.SubElement(node.find("Properties"), tag, {"name": prop}).text = text
            written_workspace.append(name)
        if spec.get("$className") == "Lighting":
            ET.SubElement(node.find("Properties"), "token", {"name": "Technology"}).text = str(LIGHTING_TECHNOLOGY)
        if "$path" in spec:
            if any(not k.startswith("$") for k in spec):
                raise ValueError("Mixed path and child mapping is unsupported")
            path = (project_path.parent / spec["$path"]).resolve()
            if not path.is_relative_to(project_path.parent.resolve()):
                raise ValueError("Source path escapes project")
            if path.is_file() and path.suffix == ".rbxmx" and node.attrib["class"] == "MaterialService":
                imported = ET.parse(path).getroot().findall("Item")
                if len(imported) != 1 or imported[0].attrib["class"] != "MaterialService":
                    raise ValueError("Expected one authored MaterialService")
                for nested in imported[0].iter("Item"):
                    counter += 1
                    nested.attrib["referent"] = f"RBX{counter}"
                parent.remove(node)
                parent.append(imported[0])
            else:
                directory(node, path)
        for child_name, child_spec in sorted(spec.items()):
            if not child_name.startswith("$"):
                descend(node, child_name, child_spec)

    tree = project["tree"]
    if tree.get("$className") != "DataModel" or any(k.startswith("$") and k != "$className" for k in tree):
        raise ValueError("Root must be a plain DataModel")
    for name, spec in sorted(tree.items()):
        if not name.startswith("$"):
            descend(root, name, spec)
    if workspace_properties and len(written_workspace) != 1:
        raise ValueError(f"Workspace properties requested but the project has {len(written_workspace)} Workspace items")
    add_tier_coat_templates(root, item, project_path.parent)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), sources


def add_tier_coat_templates(root, item, project_root):
    """ReplicatedStorage.TierCoatTemplates: one SurfaceAppearance per (species, part, tier) with a ColorMap id in Tier.Maps (LowPolyTier.luau).
    A SurfaceAppearance created by a script at runtime does not render in Roblox, so it is authored here, at build time, and only cloned by
    LowPolyDinos. No ids yet (or no LowPolyTier / ReplicatedStorage in a test project) = an empty folder / nothing."""
    storage = next((n for n in root.findall("Item") if n.attrib["class"] == "ReplicatedStorage"), None)
    if storage is None or not (project_root / tier_coat.TIER_SOURCE).exists():
        return
    folder = item(storage, tier_coat.FOLDER, "Folder")
    for t in tier_coat.load_templates(project_root):
        node = item(folder, t["name"], "SurfaceAppearance")
        props = node.find("Properties")
        for key in ("ColorMap", "NormalMap", "RoughnessMap", "MetalnessMap"):
            if t[key]:
                content = ET.SubElement(props, "Content", {"name": key})
                ET.SubElement(content, "url").text = t[key]
        ET.SubElement(props, "token", {"name": "AlphaMode"}).text = str(tier_coat.ALPHA_MODE_TRANSPARENCY)
        tint = tier_coat.COAT_TINT.get(t["name"].rsplit("_", 1)[-1])
        if tint:
            color = ET.SubElement(props, "Color3", {"name": "Color"})
            for channel, value in zip("RGB", tint):
                ET.SubElement(color, channel).text = repr(value / 255)


CONFIG_PATH = "src/shared/Config.luau"


def build_version(root=ROOT):
    return re.search(r'Build = "redesign-(\d+)"', (Path(root) / CONFIG_PATH).read_text(encoding="utf-8")).group(1)


def git_state(root=ROOT):
    """(commit, dirty) for the build manifest; (None, None) outside a git checkout."""
    import subprocess
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--", "src", "default.project.json", "resources", "tools"],
                                cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        return commit, bool(status)
    except (OSError, subprocess.CalledProcessError):
        return None, None


STAMPED_PROFILES = ("playtest",)  # BD-1043: only the playtest build shows the commit on screen; default output is byte-for-byte unchanged
_BUILD_LINE = re.compile(r'^(    Build = "redesign-\d+)(",)', re.MULTILINE)


def short_commit(commit, dirty=False):
    """The id shown on screen: 8 hex characters, plus * when the build had uncommitted changes. Empty-safe (no git -> '')."""
    if not commit or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        return ""
    return commit[:8] + ("*" if dirty else "")


def stamp_build_label(source, stamp):
    """Append ' <stamp>' to Config.Build so the existing on-screen 'BUILD ...' label shows the commit. Empty stamp = source unchanged."""
    if not stamp:
        return source
    if not re.fullmatch(r"[0-9a-f]{7,40}\*?", stamp):
        raise ValueError(f"Unsafe build stamp {stamp!r}")
    stamped, count = _BUILD_LINE.subn(lambda m: f"{m.group(1)} {stamp}{m.group(2)}", source)
    if count != 1:
        raise ValueError(f"Expected exactly one 'Build = \"redesign-NNN\"' line in Config, found {count}")
    return stamped


def build_profile(profile, project_path=ROOT / "default.project.json", stamp=""):
    """Build with a release profile applied to Config. Returns (data, sources, report).
    `stamp` (short git id, see short_commit) is written into Config.Build for the profiles in STAMPED_PROFILES only."""
    import sys
    tools = str(Path(__file__).resolve().parent)
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import release_profiles
    reports = []

    def transform(relative, source):
        if relative != CONFIG_PATH:
            return source
        rewritten, report = release_profiles.apply_profile(source, profile)
        reports.append(report)
        if profile in STAMPED_PROFILES:
            rewritten = stamp_build_label(rewritten, stamp)
        return rewritten

    data, sources = build(project_path, transform, release_profiles.workspace_properties(profile))
    if len(reports) != 1:
        raise ValueError(f"Release profile {profile!r}: expected exactly one {CONFIG_PATH}, found {len(reports)}")
    return data, sources, reports[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--profile", default=None,
                        help="release profile from tools/release_profiles.py (e.g. playtest); default build is unchanged")
    args = parser.parse_args()
    suffix = "" if args.profile in (None, "default") else "-" + args.profile
    output = args.output or ROOT / ("build/BeDino-Build" + build_version() + suffix + ".rbxlx")
    stamp = ""
    if suffix:
        commit, dirty = git_state()
        stamp = short_commit(commit, dirty)
        data, sources, report = build_profile(args.profile, stamp=stamp)
        import release_profiles  # build_profile put tools/ on sys.path
        for streaming_error in release_profiles.streaming_config_errors(args.profile):
            report.errors.append(streaming_error)
        setting = release_profiles.streaming_for(args.profile)
        if setting.enabled:
            print(f"STREAMING: Workspace.StreamingEnabled = true, target {setting.target_radius}, min {setting.min_radius}, "
                  f"integrity {setting.integrity_mode}" + (" (SCRATCH profile: never publish this place)" if setting.scratch else ""))
        for warning in report.warnings:
            print(f"WARNING: {warning}")
        if args.profile in STAMPED_PROFILES and commit:  # BD-1043: playtest files are built from a fresh origin/main (local ref, no network)
            try:
                import playtest_freshness
                missed, _ = playtest_freshness.behind(commit)
                if missed:
                    print(f"WARNING: this checkout is {missed} commits behind origin/main; run `git fetch origin` and merge before building a playtest")
            except Exception:  # best effort only, never blocks a build
                pass
        if not report.ok:
            for error in report.errors:
                print(f"ERROR: {error}")
            raise SystemExit(f"Release profile {args.profile!r} failed; no place was written.")
    else:
        data, sources = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    manifest = {"format": 1, "place_sha256": hashlib.sha256(data).hexdigest(), "sources": sources}
    if suffix:
        manifest.update({"profile": args.profile, "build": "redesign-" + build_version(),
                         "git_commit": commit, "git_dirty": dirty, "config_overrides": report.applied,
                         "build_label": "BUILD redesign-" + build_version() + (" " + stamp if stamp and args.profile in STAMPED_PROFILES else ""),
                         "warnings": report.warnings})
        setting = release_profiles.streaming_for(args.profile)
        manifest["streaming"] = {"enabled": setting.enabled, "target_radius": setting.target_radius, "min_radius": setting.min_radius,
                                 "integrity_mode": setting.integrity_mode, "gate": setting.gate, "scratch": setting.scratch}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Built {output.name}: {len(sources)} scripts, {len(data)} bytes")
