"""Dependency-free packager for this project's deliberately small Rojo subset.

Python 3.10+; creates a textual Roblox place. Not a general Rojo replacement.
Unsupported project fields fail rather than silently changing the build.
"""
from pathlib import Path
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def build(project_path=ROOT / "default.project.json"):
    project_path = Path(project_path)
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if set(project) != {"name", "tree"}:
        raise ValueError("Unsupported top-level project field")
    root = ET.Element("roblox", {"version": "4"})
    ET.SubElement(root, "External").text = "null"
    ET.SubElement(root, "External").text = "nil"
    sources = {}
    counter = 0

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
            child = item(parent, name, kind, source)
            if entry.is_dir():
                directory(child, entry)
            else:
                sources[entry.relative_to(project_path.parent).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

    def descend(parent, name, spec):
        unknown = [k for k in spec if k.startswith("$") and k not in {"$className", "$path"}]
        if unknown:
            raise ValueError(f"Unsupported project properties: {unknown}")
        node = item(parent, name, spec.get("$className", "Folder"))
        if "$path" in spec:
            if any(not k.startswith("$") for k in spec):
                raise ValueError("Mixed path and child mapping is unsupported")
            path = (project_path.parent / spec["$path"]).resolve()
            if not path.is_relative_to(project_path.parent.resolve()):
                raise ValueError("Source path escapes project")
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
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), sources


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/BeDino-Prototype.rbxlx")
    args = parser.parse_args()
    data, sources = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    manifest = {"format": 1, "place_sha256": hashlib.sha256(data).hexdigest(), "sources": sources}
    args.output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Built {args.output.name}: {len(sources)} scripts, {len(data)} bytes")
