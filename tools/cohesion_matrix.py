#!/usr/bin/env python3
"""Cohesion matrix (BD-1206, docs/240): every surface of the game against the style-tile rules, from one JSON file.

    python tools/cohesion_matrix.py                       # render docs/polish/cohesion.json -> picture + markdown table
    python tools/cohesion_matrix.py --json other.json --out-dir docs/evidence/<date>-cohesion

The JSON: {"rules": [{"id": "R1", "short": "...", "text": "..."}], "surfaces": [{"name": "...", "group": "...",
"shot": "path/to/current.jpg" | null, "marks": {"R1": "P" | "F" | "-" | "?"}, "note": "..."}]}
P = passes the rule today, F = fails, - = rule does not apply, ? = not checked yet. A surface passes only with no F and no ?.
Writes <out-dir>/cohesion-matrix.jpg (thumbnails + coloured marks) and <out-dir>/cohesion-matrix.md, and prints the totals.
Pillow only. The polish loop (docs/234) re-renders it after every UI change; the target is every surface green.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
COL = {"P": (93, 200, 60), "F": (230, 70, 60), "-": (205, 200, 190), "?": (245, 190, 60)}


def font(size):
    for f in ("C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def verdict(marks: dict) -> str:
    vals = list(marks.values())
    return "F" if "F" in vals else ("?" if "?" in vals else "P")


def render(data: dict, out_dir: Path) -> tuple[int, int, int]:
    rules, surfaces = data["rules"], data["surfaces"]
    thumb_w, thumb_h, cell, name_w = 220, 92, 64, 330
    head_h = 120
    W = thumb_w + name_w + cell * (len(rules) + 1) + 40
    H = head_h + (thumb_h + 10) * len(surfaces) + 30
    img = Image.new("RGB", (W, H), (246, 241, 230))
    d = ImageDraw.Draw(img)
    f_big, f, f_s = font(28), font(18), font(14)
    d.text((16, 12), "Be Dino! cohesion matrix: every surface vs the style tile", font=f_big, fill=(30, 30, 30))
    x0 = 16 + thumb_w + name_w
    for i, r in enumerate(rules):
        x = x0 + i * cell
        d.text((x + 6, 60), r["id"], font=f, fill=(30, 30, 30))
        d.text((x + 2, 86), r["short"][:9], font=f_s, fill=(90, 80, 60))
    d.text((x0 + len(rules) * cell + 2, 60), "now", font=f, fill=(30, 30, 30))
    counts = {"P": 0, "F": 0, "?": 0}
    for j, s in enumerate(surfaces):
        y = head_h + j * (thumb_h + 10)
        if s.get("shot") and (ROOT / s["shot"]).exists():
            t = Image.open(ROOT / s["shot"]).convert("RGB")
            t.thumbnail((thumb_w, thumb_h))
            img.paste(t, (16, y))
        else:
            d.rectangle((16, y, 16 + thumb_w, y + thumb_h), outline=(150, 150, 150))
            d.text((26, y + 34), "no picture yet", font=f_s, fill=(120, 120, 120))
        d.text((16 + thumb_w + 12, y + 8), s["name"], font=f, fill=(30, 30, 30))
        d.text((16 + thumb_w + 12, y + 34), s.get("group", ""), font=f_s, fill=(110, 100, 80))
        d.text((16 + thumb_w + 12, y + 54), s.get("note", "")[:44], font=f_s, fill=(110, 100, 80))
        for i, r in enumerate(rules):
            m = s["marks"].get(r["id"], "?")
            x = x0 + i * cell
            d.rounded_rectangle((x + 4, y + 22, x + cell - 8, y + 70), radius=10, fill=COL[m], outline=(30, 30, 30), width=2)
            d.text((x + cell // 2 - 8, y + 34), m, font=f, fill=(255, 255, 255) if m in "PF" else (60, 50, 30))
        v = verdict(s["marks"])
        counts[v] += 1
        x = x0 + len(rules) * cell
        d.rounded_rectangle((x + 4, y + 22, x + cell + 4, y + 70), radius=10, fill=COL[v], outline=(30, 30, 30), width=3)
        d.text((x + 16, y + 34), {"P": "OK", "F": "NO", "?": "?"}[v], font=f, fill=(255, 255, 255))
    out_dir.mkdir(parents=True, exist_ok=True)
    img.save(out_dir / "cohesion-matrix.jpg", quality=88)
    lines = ["| Surface | Group | " + " | ".join(r["id"] for r in rules) + " | Now | Note |",
             "| --- | --- | " + " | ".join("---" for _ in rules) + " | --- | --- |"]
    for s in surfaces:
        lines.append(f"| {s['name']} | {s.get('group', '')} | " + " | ".join(s["marks"].get(r["id"], "?") for r in rules)
                     + f" | {verdict(s['marks'])} | {s.get('note', '')} |")
    legend = "\n".join(f"- **{r['id']} {r['short']}**: {r['text']}" for r in rules)
    (out_dir / "cohesion-matrix.md").write_text(legend + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return counts["P"], counts["F"], counts["?"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=str(ROOT / "docs/polish/cohesion.json"))
    ap.add_argument("--out-dir", default=str(ROOT / "docs/evidence/2026-11-15-cohesion"))
    a = ap.parse_args(argv)
    p, f, q = render(json.loads(Path(a.json).read_text(encoding="utf-8")), Path(a.out_dir))
    print(f"cohesion: {p} surfaces pass, {f} fail, {q} not checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
