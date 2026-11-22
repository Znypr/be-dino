"""BD-1292 (docs/247): the Be Dino Desk catalog. Prints one JSON object: tabs -> groups -> items (repo-relative image paths).

    python tools/desk_catalog.py            # the catalog the app shows
    python tools/desk_catalog.py --counts   # one line per group (for a quick look)

Adding a source = one entry in SOURCES (a glob) or a keyword in EVIDENCE. Pure stdlib; reads the file system only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = {".png", ".jpg", ".jpeg", ".webp"}

# (tab, group, glob relative to the repo, note shown under the group title)
SOURCES = [
    ("Dinos", "Portraits (uniform capture)", "build/hatch-mock/portraits/*-v2.png",
     "Every V3 species from the same camera: 3/4 front, 22 degrees up, 20 degree lens (portrait tool, 2026-11-22)."),
    ("Dinos", "Old cutouts (resources)", "resources/ui/v2/dinos/v3/*.png", "The 256 px cutouts the UI used before."),
    ("UI kit", "Shop kit 2", "resources/ui/v2/shopkit2/*.png", "Cards, buttons, headers of the approved Aura Shop look (BD-1287)."),
    ("UI kit", "Toybox kit", "resources/ui/v2/toybox/final/*.png", "Owner's Toybox kit pieces."),
    ("UI kit", "Hatch kit (proposal)", "build/hatch-mock/art/*.png", "Pieces of the hatch mock on the Design Board (not in the game yet)."),
    ("UI kit", "Components", "resources/ui/v2/components/*.png", "Older code-era components."),
    ("UI kit", "Icons", "resources/ui/v2/icons/*.png", "Class, rarity, mutation, shop, station, HUD icons."),
    ("UI kit", "Items", "resources/ui/v2/items/*.png", "Auras, food, potions."),
    ("UI kit", "Hatch art", "resources/ui/v2/hatch/*.png", "Rays, paint pail and can."),
    ("UI kit", "Eggs", "resources/ui/v2/stage/eggs/*.png", "Condition egg renders."),
]

# docs/evidence folders -> (tab, group) by keyword; newest folders first, at most MAX_FOLDERS per group
EVIDENCE = [
    ("World", "Vegetation", ("vegetation", "trees", "plants", "grass")),
    ("World", "Decoration and statues", ("props", "landmark", "plaza", "world-fill", "statue", "decor")),
    ("World", "Food", ("food",)),
    ("World", "Cave", ("cave",)),
    ("World", "Map and world look", ("world-look", "world-art", "-world", "map", "ui-world")),
    ("Screens", "HUD", ("hud",)),
    ("Screens", "Menus and shops", ("menu", "shop", "sae")),
    ("Screens", "Hatching", ("hatch", "egg-reveal", "egg-preview")),
]
MAX_FOLDERS = 6
MAX_PER_FOLDER = 24
TAB_ORDER = ["Dinos", "World", "UI kit", "Screens", "Text and buttons"]


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def title_of(p: Path) -> str:
    t = re.sub(r"-v2$", "", p.stem)
    return t.replace("_", " ").replace("-", " ")


def items_for(files):
    out = []
    for f in files:
        if f.suffix.lower() in IMG and f.is_file() and not f.name.startswith("."):
            out.append({"id": rel(f), "title": title_of(f), "src": rel(f)})
    return out


def catalog():
    tabs = {}

    def group(tab, name, note, items):
        if items:
            tabs.setdefault(tab, []).append({"id": tab + "/" + name, "name": name, "note": note, "items": items})

    for tab, name, pattern, note in SOURCES:
        group(tab, name, note, items_for(sorted(ROOT.glob(pattern))))
    ev = ROOT / "docs" / "evidence"
    folders = sorted([d for d in ev.iterdir() if d.is_dir()], key=lambda d: d.name, reverse=True) if ev.is_dir() else []
    loose = sorted([f for f in ev.iterdir() if f.is_file()], key=lambda f: f.name, reverse=True) if ev.is_dir() else []
    for tab, name, keys in EVIDENCE:
        hits = [d for d in folders if any(k in d.name.lower() for k in keys)][:MAX_FOLDERS]
        items = []
        for d in hits:
            for it in items_for(sorted(d.rglob("*"))[:MAX_PER_FOLDER * 3])[:MAX_PER_FOLDER]:
                it["title"] = d.name[:10] + " " + it["title"]
                items.append(it)
        items += [it for it in items_for(loose) if any(k in it["id"].lower() for k in keys)][:MAX_PER_FOLDER]
        group(tab, name, "Newest evidence folders: " + ", ".join(d.name for d in hits), items)
    tabs["Text and buttons"] = [{"id": "Text and buttons/specimens", "name": "Specimens", "note": "Drawn live in the app with the game font.",
                                  "items": [], "kind": "specimens"}]
    return {"root": str(ROOT), "tabs": [{"name": t, "groups": tabs[t]} for t in TAB_ORDER if t in tabs]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--root", help="the checkout to list (default: this one); the desk app passes the owner's main checkout")
    a = ap.parse_args(argv)
    global ROOT
    if a.root:
        ROOT = Path(a.root).resolve()
    c = catalog()
    if a.counts:
        for t in c["tabs"]:
            for g in t["groups"]:
                print(f"{t['name']:<18} {g['name']:<32} {len(g['items'])}")
        return 0
    sys.stdout.write(json.dumps(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
