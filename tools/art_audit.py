"""BD art audit (2026-11-23): which art files are the newest of their family and which ones the game or a tool still uses.

    python tools/art_audit.py                     # writes docs/evidence/2026-11-23-art-audit/audit.csv, prints counts
    python tools/art_audit.py --out FILE.csv      # elsewhere
    python tools/art_audit.py --no-archive        # leave resources/archive/** and assets/archive/** out

Family = same folder (generation folders such as fbx_v2, fx-v3, ui/v2 folded) + file name without a version suffix
(-v1, _V2, -old, -2026-11-22, the -512 upload copy). Candidate sheets (-A..-D, -A1..-D4, files in candidates/ folders)
are their own kind: "candidate". Newest = highest version; an owner pick recorded in docs/77 wins (column "pick").

Used by game = one of the file's Roblox ids (docs/evidence/roblox-uploads.json by sha256 or name, *bindings*.json,
image-ids.txt / decal-ids.txt, docs/77 rows) appears in src/**, or src/** / default.project.json names the file.
Read by tool = tools/**, tests/**, .github/** or a resources json names the file (path, name or an f-string pattern).
Pure stdlib; reads the file system and git ls-files only.
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = "docs/evidence/2026-11-23-art-audit/audit.csv"
ART = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".obj", ".fbx", ".blend", ".rbxmx", ".rbxm", ".mp3", ".ogg", ".wav",
       ".glb", ".tga", ".mtl"}
ARCHIVE = ("resources/archive/", "assets/archive/")
VERSION = re.compile(r"(?:[-_ ][vV](\d+)|[-_](old)|[-_](\d{4}-\d{2}-\d{2})|-(512))$")
CANDIDATE = re.compile(r"-([A-D])(\d?)$")
SELF = "tools/art_audit.py"


# Lead decisions the version rule cannot make on its own (path prefix -> action, reason). The first match wins.
DECISIONS = [
    ("resources/ui/v2/candidates/", "archive",
     "candidate sheet: the owner's picks were promoted to icons/ and items/ (BD-1265, 2026-11-17; potion rail icons BD-1298); "
     "groups without a promoted file stay pickable in resources/archive/ui/v2/candidates/"),
    ("resources/ui/v2/components/", "archive",
     "code-era kit (docs/72 placeholder); superseded by the owner's Toybox kit (resources/ui/v2/toybox/final) and shop kit 2"),
    ("resources/patterns/candidates", "keep",
     "pattern tile candidates: owner pick still open (BD-1034 part 2), read by tools/pattern_similarity.py and tile_seam_check.py"),
    ("resources/ui/icons/", "keep",
     "v1 icons: compiled into src/shared/IconRaster.luau by tools/compile_resources.py (no game script reads that module), "
     "listed in resources/manifest.json (tests/test_resources.py); the game uses the resources/ui/v2/icons uploads"),
    ("resources/ui/components/", "keep", "v1 kit listed in resources/manifest.json (tests/test_resources.py checks every source exists)"),
    ("resources/ui/previews/", "keep", "v1 previews listed in resources/manifest.json"),
    ("assets/blender/world/fbx/", "keep", "older world kit exports; read by world-kit-manifest.json and the Blender build scripts (not on the Desk)"),
    ("assets/blender/world/fbx_v2/", "keep", "older world kit exports; read by the Blender build scripts (not on the Desk)"),
    ("assets/blender/creatures/", "keep", "Blender sources: read by tools/blender/build_compy_v*.py (not on the Desk)"),
]


# Folders a game module is generated from with a glob (no file name in any source): prefix -> where it ends up.
GLOB_READERS = [
    ("resources/models/", "src/shared/ResourceGeometry.luau (tools/compile_resources.py globs resources/models/*.obj)"),
    ("assets/blender/world/fbx_v3/", "src/shared/WorldGeneratedMeshes.luau (meshes exported from assets/blender/world/fbx_v3/*.fbx)"),
]


def unarchived(rel):
    for a in ARCHIVE:
        if rel.startswith(a):
            return rel.split("/", 1)[0] + "/" + rel[len(a):]
    return rel


def decision(rel):
    return next(((act, why) for pre, act, why in DECISIONS if unarchived(rel).startswith(pre)), None)


def tracked():
    out = subprocess.run(["git", "ls-files", "resources", "assets"], cwd=ROOT, capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if Path(f).suffix.lower() in ART]


def split_name(rel):
    """-> (family key, version tuple, kind)."""
    p = Path(unarchived(rel))
    dir_ver, segs = 1, []
    for s in p.parent.parts:
        m = re.fullmatch(r"(.*?)[-_]?[vV](\d+)", s)
        if m:
            dir_ver = max(dir_ver, int(m.group(2)))
            if m.group(1):
                segs.append(m.group(1))
        else:
            segs.append(s)
    stem, file_ver, kind = p.stem, 0, "final"
    inner = re.findall(r"[-_][vV](\d+)(?=[-_])", stem)
    if inner:
        file_ver = max(int(v) for v in inner)
        stem = re.sub(r"[-_][vV]\d+(?=[-_])", "", stem)
    while True:
        m = VERSION.search(stem)
        if not m:
            break
        if m.group(1):
            file_ver = max(file_ver, int(m.group(1)))
        elif m.group(2):
            file_ver = min(file_ver, -1)
        elif m.group(4):
            kind = "upload-copy"
        stem = stem[: m.start()]
    if "candidates" in "/".join(p.parent.parts) or CANDIDATE.search(stem):
        kind = "candidate"
        stem = CANDIDATE.sub("", stem)
    fam = "/".join(segs) + "/" + stem.lower().replace("_", "-") + p.suffix.lower()
    return fam, (dir_ver, file_ver), kind


def corpus(paths):
    text = {}
    for base in paths:
        b = ROOT / base
        files = [b] if b.is_file() else [f for f in b.rglob("*") if f.is_file()] if b.exists() else []
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            if rel == SELF or f.suffix.lower() not in {".py", ".luau", ".lua", ".json", ".yml", ".yaml", ".txt", ".js", ".ts", ".html", ".cjs", ".mjs"}:
                continue
            try:
                text[rel] = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
    return text


EXT = re.compile(r"\.(?:" + "|".join(e[1:] for e in sorted(ART)) + r")\b", re.I)
PATH_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./-{}" + "\\")


def token_index(text):
    """basename -> {(path-like token, source file)} for every art file name a text mentions (linear scan)."""
    idx = defaultdict(set)
    for src, t in text.items():
        for m in EXT.finditer(t):
            i = m.start()
            while i > 0 and m.start() - i < 240 and t[i - 1] in PATH_CHARS:
                i -= 1
            tok = t[i:m.end()].replace("\\", "/").lower().lstrip("./")
            if tok and "{" not in tok:
                idx[tok.rsplit("/", 1)[-1]].add((tok, src))
            elif "{" in tok:
                idx["{pattern}"].add((tok, src))
    return idx


def name_patterns(idx):
    """f-string / format patterns naming art files (trail-{tid}-v1.png) -> [(regex, source file)]."""
    pats = []
    for tok, src in idx.get("{pattern}", ()):
        base = tok.rsplit("/", 1)[-1]
        if len(re.sub(r"\{.*?\}", "", base.rsplit(".", 1)[0])) < 3:
            continue  # "{name}.png" names every file: too vague to count as a read
        rx = re.sub(r"\\{.*?\\}", r"[^/]+", re.escape(base))
        pats.append((re.compile(r"(?:^|/)" + rx + "$", re.I), src))
    return pats


def ids_by_file(files):
    sha = {}
    for f in files:
        try:
            sha[hashlib.sha256((ROOT / f).read_bytes()).hexdigest()] = f
        except OSError:
            pass
    by_name = defaultdict(list)
    for f in files:
        by_name[Path(f).name.lower()].append(f)
    ids = defaultdict(set)

    def add(f, *vals):
        for v in vals:
            v = re.sub(r"\D", "", str(v or ""))
            if len(v) >= 8:
                ids[f].add(v)

    up = ROOT / "docs/evidence/roblox-uploads.json"
    if up.exists():
        for r in json.loads(up.read_text(encoding="utf-8")):
            f = sha.get(r.get("sha256", ""))
            cands = [f] if f else by_name.get(Path(r.get("file", "")).name.lower(), [])
            for f in cands:
                add(f, r.get("assetId"), r.get("imageId"))
    for bj in list(ROOT.glob("resources/**/*bindings*.json")) + list(ROOT.glob("resources/**/*-ids.txt")):
        base = bj.parent
        if bj.suffix == ".txt":
            for line in bj.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].split("_", 1)[-1].replace("_", "-")
                    for f in files:
                        if Path(f).parent == base.relative_to(ROOT) and Path(f).stem.lower() == key:
                            add(f, parts[1])
            continue

        def walk(o):
            if isinstance(o, dict):
                srcs = [o.get(k) for k in ("source", "file", "path", "image", "png") if isinstance(o.get(k), str)]
                vals = [o.get(k) for k in o if re.search(r"(?i)asset.?id|image.?id|decal|mesh.?id|^id$", k)]
                for s in srcs:
                    for cand in (base / s, ROOT / s):
                        rel = cand.resolve().relative_to(ROOT.resolve()).as_posix() if cand.resolve().is_relative_to(ROOT.resolve()) else None
                        if rel in files:
                            add(rel, *vals)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        try:
            walk(json.loads(bj.read_text(encoding="utf-8")))
        except ValueError:
            pass
    reg = ROOT / "docs/77-asset-registry.md"
    if reg.exists():
        for line in reg.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = line.split("|")
            paths = [f for f in files if f in line]
            if paths and len(cells) > 4:
                for f in paths:
                    add(f, *re.findall(r"\b\d{9,16}\b", cells[4]))
    return ids


def owner_picks():
    """Files docs/77 marks as picked / approved by the owner."""
    reg = ROOT / "docs/77-asset-registry.md"
    picks = {}
    if reg.exists():
        for line in reg.read_text(encoding="utf-8").splitlines():
            if line.startswith("|") and re.search(r"(?i)picked by the owner|owner pick|owner-approved|owner approved|owner kept", line):
                for p in re.findall(r"(?:resources|assets)/[\w./\-]+\.\w+", line):
                    picks[p] = line.split("|")[1].strip()
    return picks


def audit(include_archive=True):
    files = tracked()
    if not include_archive:
        files = [f for f in files if not f.startswith(ARCHIVE)]
    game_text = corpus(["src", "default.project.json"])
    tool_text = corpus(["tools", "tests", ".github", "resources", "assets", "desk"])
    game_ids = set()
    for t in game_text.values():
        game_ids |= set(re.findall(r"\b\d{8,16}\b", t))
    game_idx, tool_idx = token_index(game_text), token_index(tool_text)
    pats = name_patterns(tool_idx) + name_patterns(game_idx)
    fid = ids_by_file(set(files))
    picks = owner_picks()
    fams = defaultdict(list)
    for f in files:
        fam, ver, kind = split_name(f)
        fams[fam].append((f, ver, kind))
    rows = []
    for fam, members in sorted(fams.items()):
        finals = [m for m in members if m[2] == "final"] or [m for m in members if m[2] == "upload-copy"] or members
        newest_ver = max(m[1] for m in finals)
        picked = [m for m in members if m[0] in picks or unarchived(m[0]) in picks]
        newest_pick = max((m[1] for m in picked), default=None)
        def refs(f):
            name, tail = Path(f).name.lower(), "/".join(Path(unarchived(f)).parts[-2:]).lower()

            def hits(index):
                out = set()
                for tok, src in index.get(name, ()):
                    if tok == f.lower() or tok.endswith("/" + tail) or tok == tail or (tok == name and len(Path(f).stem) > 6):
                        out.add(src)
                return out
            g = sorted(hits(game_idx)) + [f"id {i}" for i in sorted(fid.get(f, ())) if i in game_ids]
            g += [why for pre, why in GLOB_READERS if unarchived(f).startswith(pre) and not f.startswith(ARCHIVE)]
            t = sorted({s for s in hits(tool_idx) if not s.endswith(("bindings.json", "-ids.txt"))})
            t += sorted({s for rx, s in pats if rx.search(f)})
            return g, t
        fam_refs = {m[0]: refs(m[0]) for m in members}
        for f, ver, kind in sorted(members):
            in_game, in_tool = list(fam_refs[f][0]), fam_refs[f][1]
            if kind == "upload-copy":
                in_game += [f"upload copy of {Path(o).name}: {g}" for o, _, k in members if k != "upload-copy" for g in fam_refs[o][0]]
            if picked and kind != "candidate":
                newest = ver == newest_ver or (ver == newest_pick and (f in picks or unarchived(f) in picks))
            elif kind == "candidate":
                newest = len(finals) == len(members) and ver == newest_ver
            elif kind == "upload-copy":
                newest = True
            else:
                newest = ver == newest_ver
            dec = decision(f)
            note = dec[1] if dec else ""
            if f.startswith(ARCHIVE):
                action = "archived"
                note = note or ("superseded by " + ", ".join(Path(m[0]).name for m in members if m[1] == newest_ver and not m[0].startswith(ARCHIVE)))
            elif newest or kind == "upload-copy":
                action = "keep"
            elif in_game:
                action = "switch-to-newest"
            elif dec:
                action = dec[0]
            elif in_tool:
                action = "keep (tool reads)"
            else:
                action = "archive"
            if dec and newest and not f.startswith(ARCHIVE):
                action = dec[0] if not in_game else "keep"
            rows.append({
                "family": fam, "file": f, "kind": kind, "version": f"{ver[0]}.{ver[1]}",
                "newest": "yes" if newest else "no", "owner_pick": picks.get(f, ""),
                "used_by_game": "; ".join(sorted(set(in_game)))[:300], "read_by_tool": "; ".join(sorted(set(in_tool)))[:300],
                "asset_ids": " ".join(sorted(fid.get(f, ()))), "action": action, "note": note,
            })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--no-archive", action="store_true", help="leave resources/archive/** and assets/archive/** out")
    a = ap.parse_args(argv)
    rows = audit(not a.no_archive)
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    fams = {r["family"] for r in rows}
    multi = {f for f in fams if sum(1 for r in rows if r["family"] == f) > 1}
    count = defaultdict(int)
    for r in rows:
        count[r["action"]] += 1
    print(f"{len(rows)} files, {len(fams)} families ({len(multi)} with more than one file): "
          + ", ".join(f"{k} {v}" for k, v in sorted(count.items())) + f" -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
