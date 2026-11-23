"""BD-1292 (docs/247): the Be Dino Desk catalog. Prints one JSON object: tabs -> groups -> items (repo-relative image paths).

    python tools/desk_catalog.py            # the catalog the app shows
    python tools/desk_catalog.py --counts   # one line per group (for a quick look)

Adding a source = one entry in SOURCES (a glob) or a keyword in EVIDENCE. Pure stdlib; reads the file system only.
"""
import argparse
import json
import re
import struct
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = {".png", ".jpg", ".jpeg", ".webp"}

# (tab, group, glob relative to the repo, note shown under the group title)
SOURCES = [
    ("Dinos", "Portraits (uniform capture)", "build/hatch-mock/portraits/*-v2.png",
     "Every V3 species from the same camera: 3/4 front, 22 degrees up, 20 degree lens (portrait tool, 2026-11-22)."),
    ("Dinos", "Old cutouts (resources)", "resources/ui/v2/dinos/v3/*.png", "The 256 px cutouts the UI used before."),
    ("World", "Vegetation (in game)", "build/hatch-mock/world/cut/veg2_*.png",
     "Every vegetation model the game places, same capture: scaled to one size, 3/4 view, 18 degrees up (world_pairs.luau, 2026-11-22)."),
    ("World", "Trees and rocks (world kit)", "build/hatch-mock/world/cut/tree_*.png|build/hatch-mock/world/cut/rock_*.png|build/hatch-mock/world/cut/bush.png",
     "WorldGeneratedMeshes trees, rocks and bush."),
    ("World", "Landmarks and statues", "build/hatch-mock/world/cut/landmark_*.png|build/hatch-mock/world/cut/hub_statue_*.png", "Landmarks and the cave hub statues."),
    ("World", "Food pickups", "build/hatch-mock/world/cut/food_*.png", "Food v3 pickups."),
    ("World", "Cave", "build/hatch-mock/world/cut/cave_*.png", "Cave rocks, stalagmites, moss, lava."),
    ("World", "Cave hub props", "build/hatch-mock/world/cut/hub_*.png", "Stalls, furniture, lanterns, crystals in the cave hub (statues are under Landmarks)."),
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
    ("World", "Vegetation (screenshots)", ("vegetation", "trees", "plants", "grass")),
    ("World", "Decoration and statues (screenshots)", ("props", "landmark", "plaza", "world-fill", "statue", "decor")),
    ("World", "Food (screenshots)", ("food",)),
    ("World", "Cave (screenshots)", ("cave",)),
    ("World", "Map and world look", ("world-look", "world-art", "-world", "map", "ui-world")),
    ("Screens", "HUD", ("hud",)),
    ("Screens", "Menus and shops", ("menu", "shop", "sae")),
    ("Screens", "Hatching", ("hatch", "egg-reveal", "egg-preview")),
]
MAX_FOLDERS = 6
MAX_PER_FOLDER = 24
TAB_ORDER = ["Dinos", "World", "UI kit", "Screens", "Text and buttons"]

# Menus tab (BD-1301): one screen per docs/menu-specs/<screen>/spec.json; its newest check = the newest report.json of
# tools/menu_spec_check.py found by these globs ({screen} = folder name, {key} = its first word: potion-shop -> potion).
# Adding a source = one line.
MENU_SPECS = "docs/menu-specs/*/spec.json"
MENU_REPORTS = [
    "build/menu-check/{screen}/**/report.json",
    "docs/evidence/*{key}*/**/report.json",
]
# A screen with no check yet can still show a Studio picture of its build on the BUILD side (no boxes): screen -> glob, newest file wins.
MENU_SAMPLE_BUILDS = {
    "dino-index": "docs/evidence/2026-11-23-index-proposal/1-*.jpg",
}


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
        files = sorted({f for pat in pattern.split("|") for f in ROOT.glob(pat)})
        if name == "Cave hub props":
            files = [f for f in files if not f.name.startswith("hub_statue_")]
        group(tab, name, note, items_for(files))
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
    return {"root": str(ROOT), "tabs": [{"name": t, "groups": tabs[t]} for t in TAB_ORDER if t in tabs], "menus": menus()}


# ---------- Menus tab (BD-1301) ----------

def image_size(p: Path):
    """(w, h) of a PNG or JPEG from its header (stdlib only); None if unknown."""
    try:
        with open(p, "rb") as f:
            head = f.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return list(struct.unpack(">II", head[16:24]))
            if head[:2] != b"\xff\xd8":
                return None
            f.seek(2)
            while True:
                m = f.read(2)
                if len(m) < 2 or m[0] != 0xFF:
                    return None
                if m[1] in (0xD8, 0x01) or 0xD0 <= m[1] <= 0xD7:
                    continue
                n = struct.unpack(">H", f.read(2))[0]
                if 0xC0 <= m[1] <= 0xCF and m[1] not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">xHH", f.read(5))
                    return [w, h]
                f.seek(n - 2, 1)
    except (OSError, struct.error):
        return None


def spec_elements(spec: dict, size):
    """Spec elements (card* templates expanded) with their box in % of the proposal PICTURE (what the desk draws)."""
    cards = spec.get("cards") or ("card1", "card2", "card3")   # the screen's own card list (Dino Index has 8)
    raw = {}
    for k, e in spec.get("elements", {}).items():
        if k.startswith("card*."):
            for c in cards:
                if c in spec["elements"]:
                    raw[c + k[5:]] = dict(e, parent=c)
        else:
            raw[k] = {kk: vv for kk, vv in e.items() if kk != "parent"}
    wx, wy, ww, wh = spec.get("proposal_window_px", [0, 0, 1, 1])

    def px(k):
        b = raw[k]["box"]
        if raw[k].get("parent"):
            x, y, w, h = px(raw[k]["parent"])
            return x + b[0] / 100 * w, y + b[1] / 100 * h, b[2] / 100 * w, b[3] / 100 * h
        return wx + b[0] / 100 * ww, wy + b[1] / 100 * wh, b[2] / 100 * ww, b[3] / 100 * wh

    out = []
    for k, e in raw.items():
        x, y, w, h = px(k)
        pct = [x / size[0] * 100, y / size[1] * 100, w / size[0] * 100, h / size[1] * 100] if size else None
        out.append({"id": k, "kind": e.get("kind", "box"), "parent": e.get("parent"), "pct": pct,
                    **{f: e[f] for f in ("fill", "color", "text", "words", "words_text", "font", "note") if f in e}})
    return out


def geom_pcts(folder: Path):
    """Build boxes in % of the capture from a geom json next to an older report (before reports carried pct_game)."""
    for g in sorted(folder.glob("*.json")):
        if g.name == "report.json":
            continue
        try:
            d = json.loads(g.read_text(encoding="utf-8"))
            vw, vh = d["viewport"]
            ix, iy = (0, 0) if d.get("ignoreInset", True) else d.get("inset", [0, 0])
            return {k: [(v["rect"][0] + ix) / vw * 100, (v["rect"][1] + iy) / vh * 100, v["rect"][2] / vw * 100, v["rect"][3] / vh * 100]
                    for k, v in d["elements"].items()}
        except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
            continue
    return {}


def read_report(p: Path, screen: str, elems: dict):
    try:
        r = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(r, dict) or not isinstance(r.get("rows"), list) or r.get("screen", screen) != screen:
        return None
    at = r.get("at") or datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
    dated = bool(r.get("at"))  # a report that records its own time; file dates change on every git checkout
    misses = [m for m in r.get("misses", []) if isinstance(m, str)]
    ids = {row.get("id") for row in r["rows"]}
    shot = r.get("shot")
    if not shot or not (ROOT / shot).is_file():   # older reports: the capture saved next to it
        pics = [f for f in sorted(p.parent.iterdir()) if f.suffix.lower() in IMG and f.stem not in ids]
        pics.sort(key=lambda f: not any(w in f.stem.lower() for w in ("capture", "shot", "studio", "build")))
        shot = rel(pics[0]) if pics else None
    gp = None
    rows = []
    for row in r["rows"]:
        k = row.get("id")
        row = dict(row)
        row.setdefault("misses", [m for m in misses if m.startswith(f"{k}:")])
        row.setdefault("status", "missing" if row.get("missing") else ("miss" if row["misses"] else "pass"))
        if "pct_ref" not in row and elems.get(k):
            row["pct_ref"] = elems[k]["pct"]
        if "pct_game" not in row and not row.get("missing"):
            gp = geom_pcts(p.parent) if gp is None else gp
            if k in gp:
                row["pct_game"] = gp[k]
        crop_pair = p.parent / f"{k}.png"
        if crop_pair.is_file():
            row["pair"] = rel(crop_pair)
        rows.append(row)
    return {"report": rel(p), "at": at, "dated": dated, "step": r.get("step"), "self_test": bool(r.get("self_test")), "misses": misses,
            "shot": shot, "shot_size": r.get("shot_size") or (image_size(ROOT / shot) if shot else None),
            "owner_pins": r.get("owner_pins", []), "rows": rows}


def menus():
    out = []
    for sp in sorted(ROOT.glob(MENU_SPECS)):
        try:
            spec = json.loads(sp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        screen = sp.parent.name
        prop = spec.get("proposal") or rel(sp.parent / "proposal.jpg")
        size = image_size(ROOT / prop)
        elems = spec_elements(spec, size)
        by_id = {e["id"]: e for e in elems}
        found = {f for pat in MENU_REPORTS for f in ROOT.glob(pat.format(screen=screen, key=screen.split("-")[0]))}
        checks = [c for c in (read_report(f, screen, by_id) for f in found) if c]
        # newest first by the time each report records inside itself; reports without one (older format: only a file date, which a git
        # checkout resets) rank after every dated report, and a full check (no step) beats a single step at the same time
        checks.sort(key=lambda c: (c.get("dated", False), c["at"], c.get("step") is None), reverse=True)
        sample = None
        if not checks and screen in MENU_SAMPLE_BUILDS:
            pics = sorted(ROOT.glob(MENU_SAMPLE_BUILDS[screen]), key=lambda f: f.stat().st_mtime, reverse=True)
            if pics:
                sample = {"report": None, "at": datetime.fromtimestamp(pics[0].stat().st_mtime).isoformat(timespec="seconds"),
                          "step": None, "self_test": False, "sample": True, "misses": [], "shot": rel(pics[0]),
                          "shot_size": image_size(pics[0]), "owner_pins": [], "rows": []}
        out.append({"screen": screen, "spec": rel(sp), "proposal": prop, "proposal_size": size,
                    "window_px": spec.get("proposal_window_px"), "tolerance_pct": spec.get("tolerance_pct", 1.5),
                    "steps": spec.get("steps", []), "elements": elems,
                    "latest": checks[0] if checks else sample,
                    "history": [{"report": c["report"], "at": c["at"], "step": c["step"], "misses": len(c["misses"])} for c in checks[:20]]})
    return out


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
        for m in c["menus"]:
            last = m["latest"]
            print(f"{'Menus':<18} {m['screen']:<32} {len(m['elements'])} elements, "
                  + (f"{len(last['misses'])} misses ({last['at']})" if last else "no check yet"))
        return 0
    sys.stdout.write(json.dumps(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
