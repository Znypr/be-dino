"""BD-596: every SurfaceAppearance and MaterialVariant the build emits carries only cloud texture maps.

Studio packs the maps of these objects into a "TexturePack" asset when a place is played or saved (the 2026-10-17 re-walk
logged about 40 "Failed to upload TexturePack ... HTTP 429" lines at each Play, one per SurfaceAppearance under
ReplicatedStorage.Resources). A map that is empty, a local path or an `rbxasset://` file cannot be packed or fetched and would
add errors of its own, so the build must never emit one. This verifier builds the place in memory (plain profile) and checks:

* every `<Content>` map of a SurfaceAppearance / MaterialVariant is `rbxassetid://<positive integer>` (no empty url, no `null`,
  no `rbxasset://`, no file path, no http);
* a SurfaceAppearance has a ColorMap (the neutral gene textures are ColorMap-only; a template with no map at all is dead weight
  that Studio still tries to pack);
* the count is reported, so a change (for example the tier coat templates of PR #291, 21 more) is visible in the log.

It does NOT prove why Studio answers 429 (that is the Roblox upload limit for many packs at once) and does not need Studio.
Self-test: mutants of each rule must fail.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402

KINDS = ("SurfaceAppearance", "MaterialVariant")
VALID = re.compile(r"^rbxassetid://([1-9][0-9]*)$")
MAP_SUFFIX = "Map"


def problems(xml_bytes):
    """Return (list of problem strings, {class: count}) for a place / model XML."""
    root = ET.fromstring(xml_bytes)
    out, counts = [], {k: 0 for k in KINDS}
    for node in root.iter("Item"):
        cls = node.attrib.get("class")
        if cls not in KINDS:
            continue
        counts[cls] += 1
        name = (node.findtext("Properties/string[@name='Name']") or "?")
        maps = [c for c in node.findall("Properties/Content") if c.attrib.get("name", "").endswith(MAP_SUFFIX)]
        for c in maps:
            url = (c.findtext("url") or "").strip()
            if not VALID.match(url):
                out.append(f"{cls} {name} {c.attrib.get('name')}: '{url or c.findtext('null') or 'empty'}' is not rbxassetid://<positive id>")
        if cls == "SurfaceAppearance" and not any(c.attrib.get("name") == "ColorMap" for c in maps):
            out.append(f"{cls} {name}: no ColorMap")
    return out, counts


def mutate(good, find, repl):
    assert find in good, find
    return good.replace(find, repl, 1)


def main():
    xml, _ = build.build()
    bad, counts = problems(xml)
    print("SurfaceAppearance", counts["SurfaceAppearance"], "MaterialVariant", counts["MaterialVariant"])
    for line in bad[:20]:
        print("FAIL", line)
    assert not bad, f"{len(bad)} map problem(s)"
    assert counts["SurfaceAppearance"] >= 1 and counts["MaterialVariant"] >= 1, "the scan found nothing: wrong XML shape"

    sample = (b'<roblox><Item class="SurfaceAppearance"><Properties><string name="Name">a</string>'
              b'<Content name="ColorMap"><url>rbxassetid://123</url></Content></Properties></Item></roblox>')
    assert problems(sample)[0] == [], "the good sample must pass"
    cases = {
        "empty url": mutate(sample, b"rbxassetid://123", b""),
        "zero id": mutate(sample, b"rbxassetid://123", b"rbxassetid://0"),
        "leading zero": mutate(sample, b"rbxassetid://123", b"rbxassetid://0123"),
        "local file": mutate(sample, b"rbxassetid://123", b"rbxasset://textures/a.png"),
        "http": mutate(sample, b"rbxassetid://123", b"http://x/a.png"),
        "no ColorMap": mutate(sample, b'name="ColorMap"', b'name="NormalMap"'),
        "unbound template (null url)": mutate(sample, b"<url>rbxassetid://123</url>", b"<null></null>"),
        "no maps": mutate(sample, b'<Content name="ColorMap"><url>rbxassetid://123</url></Content>', b""),
    }
    for label, data in cases.items():
        assert problems(data)[0], f"mutant not caught: {label}"
    mv = sample.replace(b"SurfaceAppearance", b"MaterialVariant")
    assert problems(mv)[0] == [], "a MaterialVariant needs no ColorMap rule"
    assert problems(mutate(mv, b"rbxassetid://123", b"rbxasset://a.png"))[0], "MaterialVariant maps are checked too"
    print(f"Surface map checks passed ({len(cases) + 2} mutants caught)")


if __name__ == "__main__":
    main()
