#!/usr/bin/env python3
"""Element-by-element menu check: the owner's PROPOSED picture vs the Studio build (owner 2026-11-23: "we need a better
comparison system ... build menus step by step", "more accurate, more specific per element, like texts, outlines, boxes").

A spec (docs/menu-specs/<screen>/spec.json) names every element of the proposal with its box in % of the WINDOW (card children in
% of their card). The build marks the same elements with the attribute SpecId (e.g. "card2.price"); tools/studio/dump_menu_geometry.luau
reads their real screen rects and GUI properties in Play mode. This tool then measures BOTH pictures the same way, per element:

  box      x, y, w, h                      (% of window; card children % of card)
  fill     median colour + hex, dE to the proposal
  border   dark edge thickness              (% of window height, px at 720p window height 500)
  corner   rounding                          (% of the element's short side, from where the fill starts on the diagonal)
  text     letter height (cap), fill colour, outline (stroke) thickness and colour, measured from the pixels
  image    drawn size inside the box (non-background pixels), aspect

and lists every miss over the tolerance, step by step (--step), with side-by-side crops of each element in report.html.

    python tools/menu_spec_check.py docs/menu-specs/potion-shop/spec.json --geom geom.json --shot studio.jpg --out build/menu-check/potion
    python tools/menu_spec_check.py SPEC --geom GEOM --shot SHOT --step 2          # only step 2's elements
    python tools/menu_spec_check.py SPEC --self-test                              # proposal vs itself: every value must match
    python tools/menu_spec_check.py SPEC --geom GEOM --shot SHOT --owner-notes    # every open owner note counts as a miss

Owner notes (BD-1301): the Be Dino Desk "Menus" tab saves the owner's per-element notes and free pins to
docs/feedback/menu-feedback.json. Every report lists the open notes per element ("owner (must fix): Outline - 'too thin'");
an element with an open MUST-FIX note never passes; --owner-notes also turns nice-to-have notes and pins into misses.

geom.json (from the Luau dump): {"capture": [w, h] (optional), "viewport": [w, h], "inset": [x, y], "ignoreInset": bool,
"elements": {"window": {"rect": [x, y, w, h], ...gui props}, "card1": {...}, "card1.name": {...}}}
Exit 0 = every checked element within tolerance, 1 = misses (listed), 2 = bad input. Pillow + numpy only.
"""
from __future__ import annotations

import argparse
import fnmatch
import html
import json
import re
import sys
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CARDS = ("card1", "card2", "card3")
REF_WINDOW_H = 500  # px of window height used to express thickness in "px at a 720p phone" terms
FEEDBACK = ROOT / "docs" / "feedback" / "menu-feedback.json"


# ---------- owner notes (Be Dino Desk, docs/247) ----------

def load_owner_notes(path, screen: str):
    """Open owner notes for one screen: ({spec id: [note, ...]}, [pin, ...]). A missing or broken file = no notes."""
    if not path or not Path(path).is_file():
        return {}, []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, []
    scr = (data.get("screens") or {}).get(screen) or {}

    def is_open(n):
        return isinstance(n, dict) and n.get("status", "open") == "open"
    elems = {k: [n for n in v if is_open(n)] for k, v in (scr.get("elements") or {}).items() if isinstance(v, list)}
    return {k: v for k, v in elems.items() if v}, [n for n in (scr.get("pins") or []) if is_open(n)]


def is_must(note: dict) -> bool:
    return note.get("severity", "must") != "nice"


def note_line(note: dict) -> str:
    """owner (must fix): Outline, Colour - 'outline too thin, like proposal' (should be: 3 px dark)"""
    s = f"owner ({'must fix' if is_must(note) else 'nice to have'}): " + (", ".join(note.get("tags") or []) or "Note")
    if note.get("note"):
        s += f" - '{note['note']}'"
    if note.get("should"):
        s += f" (should be: {note['should']})"
    return s


def pin_line(i: int, pin: dict) -> str:
    return (f"pin {i} ({pin.get('side', 'build')} {float(pin.get('x', 0)):.0f} %, {float(pin.get('y', 0)):.0f} % of window): "
            + note_line(pin))


def repo_rel(p) -> str | None:
    try:
        return Path(p).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None


# ---------- geometry ----------

def expand(spec: dict) -> dict:
    """Spec elements with card* templates expanded per card; boxes stay in their own frame (window or card)."""
    out = {}
    for key, e in spec["elements"].items():
        if key.startswith("card*."):
            for c in spec.get("cards", CARDS):  # the screen's own card list (Dino Index has 8), else card1-3
                if c in spec["elements"]:
                    out[c + key[5:]] = dict(e, parent=c)
        else:
            out[key] = dict(e)
    return out


def abs_box(elems: dict, key: str, window_px) -> tuple[float, float, float, float]:
    """Pixel box of an element in the proposal picture."""
    wx, wy, ww, wh = window_px
    e = elems[key]
    b = e["box"]
    if e.get("parent"):
        px, py, pw, ph = abs_box(elems, e["parent"], window_px)
        return px + b[0] / 100 * pw, py + b[1] / 100 * ph, b[2] / 100 * pw, b[3] / 100 * ph
    return wx + b[0] / 100 * ww, wy + b[1] / 100 * wh, b[2] / 100 * ww, b[3] / 100 * wh


def rel_box(rect, frame) -> list[float]:
    fx, fy, fw, fh = frame
    x, y, w, h = rect
    return [(x - fx) / fw * 100, (y - fy) / fh * 100, w / fw * 100, h / fh * 100]


def selected(keys, step_patterns):
    if not step_patterns:
        return list(keys)
    return [k for k in keys if any(fnmatch.fnmatch(k, p.replace("card*", "card?")) or k == p for p in step_patterns)]


# ---------- pixel measures (same code for both pictures) ----------

def lum(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def hexcol(c) -> str:
    return "#%02X%02X%02X" % tuple(int(max(0, min(255, v))) for v in c)


def delta_e(c1, c2) -> float:
    if c1 is None or c2 is None:
        return 0.0
    return float(np.linalg.norm(np.array(c1, float) - np.array(c2, float)))


def crop(img: np.ndarray, box) -> np.ndarray:
    x, y, w, h = [int(round(v)) for v in box]
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + max(1, w)), min(H, y + max(1, h))
    return img[y0:y1, x0:x1]


def measure_fill(c: np.ndarray):
    if c.size == 0:
        return None
    h, w = c.shape[:2]
    inner = c[int(h * .2):int(h * .8) or 1, int(w * .2):int(w * .8) or 1].reshape(-1, 3)
    L = lum(inner)
    keep = inner[(L > 55) & (L < 235)]  # not outline, not white text
    if len(keep) < 10:
        keep = inner
    return [float(v) for v in np.median(keep, axis=0)]


def measure_border(c: np.ndarray, win_h_px: float):
    """Average dark run from each side's middle inward (px), as % of window height."""
    if c.size == 0 or min(c.shape[:2]) < 6:
        return None
    L = lum(c.astype(float))
    h, w = L.shape
    runs = []
    for line in (L[h // 2, :], L[h // 2, ::-1], L[:, w // 2], L[::-1, w // 2]):
        n = 0
        for v in line[: max(3, len(line) // 4)]:
            if v < 70:
                n += 1
            elif n:
                break
        runs.append(n)
    px = float(np.median(runs))
    return {"px": px, "pct_h": px / win_h_px * 100}


def measure_corner(c: np.ndarray):
    """Rounding: how far along the top-left diagonal the fill starts, as % of the short side."""
    if c.size == 0 or min(c.shape[:2]) < 8:
        return None
    L = lum(c.astype(float))
    fill = measure_fill(c)
    if fill is None:
        return None
    target = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
    n = min(L.shape) // 2
    for i in range(n):
        if abs(L[i, i] - target) < 40:
            return {"pct": i / min(L.shape) * 100}
    return {"pct": None}


def measure_text(c: np.ndarray, win_h_px: float, color_hint=None):
    """Letters = bright or hint-coloured pixels with a dark ring; returns letter height, fill colour, stroke width and colour."""
    if c.size == 0:
        return None
    a = c.astype(float)
    L = lum(a)
    if color_hint:
        hc = np.array([int(color_hint[i:i + 2], 16) for i in (1, 3, 5)], float)
        letters = np.linalg.norm(a - hc, axis=2) < 70
    else:
        letters = L > 215
    dark = L < 60
    if letters.sum() < 15:
        return None
    ys = np.where(letters.any(axis=1))[0]
    # stroke thickness: grow the letter mask one px at a time while the new ring is mostly dark
    grown, stroke = letters.copy(), 0
    for _ in range(12):
        nxt = grown.copy()
        nxt[1:, :] |= grown[:-1, :]
        nxt[:-1, :] |= grown[1:, :]
        nxt[:, 1:] |= grown[:, :-1]
        nxt[:, :-1] |= grown[:, 1:]
        ring = nxt & ~grown
        if ring.sum() == 0 or (dark & ring).sum() / ring.sum() < 0.55:
            break
        stroke += 1
        grown = nxt
    ring_px = grown & ~letters
    stroke_col = [float(v) for v in np.median(a[ring_px], axis=0)] if ring_px.sum() else None
    return {
        "cap_pct_h": (ys.max() - ys.min() + 1) / win_h_px * 100,
        "fill": [float(v) for v in np.median(a[letters], axis=0)],
        "stroke_px": stroke, "stroke_pct_h": stroke / win_h_px * 100,
        "stroke_col": stroke_col,
    }


def measure_image(c: np.ndarray, frame_w: float, frame_h: float):
    """Drawn art inside the box: pixels that differ from the box's own edge colour."""
    if c.size == 0:
        return None
    a = c.astype(float)
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(edge, axis=0)
    mask = np.linalg.norm(a - bg, axis=2) > 45
    if mask.sum() < 20:
        return None
    ys, xs = np.where(mask)
    return {"w_pct": (xs.max() - xs.min() + 1) / frame_w * 100, "h_pct": (ys.max() - ys.min() + 1) / frame_h * 100,
            "aspect": (xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1)}


def measure_all(img: np.ndarray, box, e: dict, win_h_px: float, frame):
    c = crop(img, box)
    out = {}
    kind = e.get("kind", "box")
    if kind == "text":
        out["text"] = measure_text(c, win_h_px, e.get("color"))
    elif kind == "image":
        out["image"] = measure_image(c, frame[2], frame[3])
    else:
        out["fill"] = measure_fill(c)
        out["border"] = measure_border(c, win_h_px)
        out["corner"] = measure_corner(c)
    return out


# ---------- compare ----------

def compare(spec_path: Path, geom_path: Path | None, shot_path: Path | None, out: Path, step: int | None, self_test: bool,
            feedback: Path | None = None, owner_flag: bool = False):
    """feedback = docs/feedback/menu-feedback.json (None = ignore owner notes); owner_flag = every open note is a miss."""
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    owner, pins = load_owner_notes(feedback, spec["screen"])
    elems = expand(spec)
    tol = float(spec.get("tolerance_pct", 1.5))
    prop_img = np.asarray(Image.open(ROOT / spec["proposal"] if not Path(spec["proposal"]).is_absolute() else spec["proposal"]).convert("RGB"))
    wpx = spec["proposal_window_px"]
    steps = spec.get("steps", [])
    patterns = steps[step - 1]["elements"] if step else None
    keys = selected(elems.keys(), patterns)

    if self_test:
        game_img, gboxes, gwin = prop_img, {k: abs_box(elems, k, wpx) for k in elems}, wpx
        gprops = {}
    else:
        g = json.loads(geom_path.read_text(encoding="utf-8"))
        game_img = np.asarray(Image.open(shot_path).convert("RGB"))
        vw, vh = g["viewport"]
        sx, sy = game_img.shape[1] / vw, game_img.shape[0] / vh
        ix, iy = (0, 0) if g.get("ignoreInset", True) else g.get("inset", [0, 0])
        gboxes, gprops = {}, {}
        for k, v in g["elements"].items():
            x, y, w, h = v["rect"]
            gboxes[k] = ((x + ix) * sx, (y + iy) * sy, w * sx, h * sy)
            gprops[k] = {kk: vv for kk, vv in v.items() if kk != "rect"}
        if "window" not in gboxes:
            print("geom has no 'window' element", file=sys.stderr)
            return 2
        gwin = gboxes["window"]

    rows, misses = [], []
    out.mkdir(parents=True, exist_ok=True)
    PH, PW = prop_img.shape[:2]
    GH, GW = game_img.shape[:2]

    def pct(b, W, H):
        return [b[0] / W * 100, b[1] / H * 100, b[2] / W * 100, b[3] / H * 100]

    def finish(row, k, start):
        """Owner notes on this element, then the row's own misses and its status (pass / miss / missing)."""
        notes = owner.get(k, [])
        if notes:
            row["owner"] = [note_line(n) for n in notes]
            row["owner_notes"] = notes
            for n in notes:
                if is_must(n) or owner_flag:
                    misses.append(f"{k}: {note_line(n)}")
        row["misses"] = misses[start:]
        row["status"] = "missing" if row.get("missing") else ("miss" if row["misses"] else "pass")
        rows.append(row)

    for k in keys:
        e = elems[k]
        start = len(misses)
        pbox = abs_box(elems, k, wpx)
        pframe = abs_box(elems, e["parent"], wpx) if e.get("parent") else wpx
        row = {"id": k, "kind": e.get("kind", "box"), "pct_ref": pct(pbox, PW, PH)}
        if k not in gboxes:
            row["missing"] = True
            misses.append(f"{k}: MISSING in the build (no SpecId)")
            finish(row, k, start)
            continue
        gbox = gboxes[k]
        row["pct_game"] = pct(gbox, GW, GH)
        gframe = gboxes.get(e["parent"]) if e.get("parent") else gwin
        pb, gb = rel_box(pbox, pframe), rel_box(gbox, gframe)
        row["box_ref"], row["box_game"] = pb, gb
        for i, n in enumerate(("x", "y", "w", "h")):
            d = gb[i] - pb[i]
            if abs(d) > tol:
                misses.append(f"{k}: {n} {pb[i]:.1f} -> {gb[i]:.1f} % (build {'+' if d > 0 else ''}{d:.1f})")
        pm = measure_all(prop_img, pbox, e, wpx[3], pframe)
        gm = measure_all(game_img, gbox, e, gwin[3], gframe)
        row["ref"], row["game"], row["gui"] = pm, gm, gprops.get(k, {})
        if "fill" in pm and pm["fill"] and gm.get("fill"):
            de = delta_e(pm["fill"], gm["fill"])
            row["fill_dE"] = de
            if de > 40:
                misses.append(f"{k}: fill {hexcol(pm['fill'])} -> {hexcol(gm['fill'])} (dE {de:.0f})")
        if pm.get("border") and gm.get("border"):
            d = gm["border"]["pct_h"] - pm["border"]["pct_h"]
            if abs(d) > 0.4:
                misses.append(f"{k}: border {pm['border']['pct_h']:.2f} -> {gm['border']['pct_h']:.2f} % h")
        if pm.get("corner") and gm.get("corner") and pm["corner"]["pct"] is not None and gm["corner"]["pct"] is not None:
            d = gm["corner"]["pct"] - pm["corner"]["pct"]
            if abs(d) > 4:
                misses.append(f"{k}: corner {pm['corner']['pct']:.0f} -> {gm['corner']['pct']:.0f} % of short side")
        pt, gt = pm.get("text"), gm.get("text")
        if pt and gt:
            if abs(gt["cap_pct_h"] - pt["cap_pct_h"]) > tol / 2:
                misses.append(f"{k}: letter height {pt['cap_pct_h']:.1f} -> {gt['cap_pct_h']:.1f} % h")
            if abs(gt["stroke_px"] * REF_WINDOW_H / gwin[3] - pt["stroke_px"] * REF_WINDOW_H / wpx[3]) > 1.0:
                misses.append(f"{k}: text outline {pt['stroke_pct_h']:.2f} -> {gt['stroke_pct_h']:.2f} % h")
            de = delta_e(pt["fill"], gt["fill"])
            if de > 45:
                misses.append(f"{k}: text colour {hexcol(pt['fill'])} -> {hexcol(gt['fill'])} (dE {de:.0f})")
        elif pt and not gt:
            misses.append(f"{k}: no readable text found in the build crop")
        pi, gi = pm.get("image"), gm.get("image")
        if pi and gi:
            for n in ("w_pct", "h_pct"):
                if abs(gi[n] - pi[n]) > tol:
                    misses.append(f"{k}: art {n[0]} {pi[n]:.1f} -> {gi[n]:.1f} % of {'card' if e.get('parent') else 'window'}")
        # words + font, read from the live GUI (Studio dump): the element's own Text, or the text label inside it
        gui = gprops.get(k, {})
        for field, src in (("words", "text"), ("words_text", "innerText")):
            pat = e.get(field)
            if pat and not self_test:
                got = gui.get(src)
                row.setdefault("words", {})[field] = got
                if got is None:
                    misses.append(f"{k}: no text found (expected /{pat}/)")
                elif not re.search(pat, str(got).strip()):
                    misses.append(f"{k}: words '{got}' do not match /{pat}/")
        if e.get("font") and not self_test:
            got = gui.get("font")
            if got is not None and e["font"].lower() not in str(got).lower():
                misses.append(f"{k}: font {got} -> expected {e['font']}")
        # side-by-side crop
        pc, gc = Image.fromarray(crop(prop_img, pbox)), Image.fromarray(crop(game_img, gbox))
        H = 120
        if pc.height and gc.height:
            pc = pc.resize((max(1, int(pc.width * H / pc.height)), H))
            gc = gc.resize((max(1, int(gc.width * H / gc.height)), H))
            pair = Image.new("RGB", (pc.width + gc.width + 8, H), (255, 0, 255))
            pair.paste(pc, (0, 0))
            pair.paste(gc, (pc.width + 8, 0))
            pair.save(out / f"{k}.png")
        finish(row, k, start)

    pin_lines = [pin_line(i + 1, p) for i, p in enumerate(pins)]
    if owner_flag:
        misses += pin_lines
    # where the two pictures are, for the desk's compare view: repo-relative when inside the repo, else a copy next to the report
    shot_rel = None
    if self_test:
        shot_rel = spec["proposal"]
    elif shot_path:
        shot_rel = repo_rel(shot_path)
        if shot_rel is None:
            copy = out / ("shot" + Path(shot_path).suffix.lower())
            shutil.copyfile(shot_path, copy)
            shot_rel = repo_rel(copy) or str(copy)
    report = {"screen": spec["screen"], "spec": repo_rel(spec_path) or str(spec_path), "step": step,
              "at": datetime.now().isoformat(timespec="seconds"), "self_test": self_test,
              "proposal": spec["proposal"], "proposal_size": [PW, PH], "shot": shot_rel, "shot_size": [GW, GH],
              "misses": misses, "owner_pins": [dict(p, line=ln) for p, ln in zip(pins, pin_lines)], "rows": rows}
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    write_html(out, spec, rows, misses, step, pin_lines)
    label = f"step {step} ({steps[step - 1]['name']})" if step else "all elements"
    print(f"{spec['screen']} {label}: {len(keys)} elements, {len(misses)} misses (tolerance {tol} %)")
    for m in misses:
        print("  - " + m)
    nice = [f"{r['id']}: {ln}" for r in rows for n, ln in zip(r.get("owner_notes", []), r.get("owner", [])) if not is_must(n)]
    if (nice or pin_lines) and not owner_flag:
        print(f"owner notes not counted as misses ({len(nice)} nice to have, {len(pin_lines)} pins; --owner-notes counts them):")
        for m in nice + pin_lines:
            print("  . " + m)
    print("report:", out / "report.html")
    return 0 if not misses else 1


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, list) and len(v) == 3:
        return hexcol(v)
    if isinstance(v, list):
        return ", ".join(f"{x:.1f}" for x in v)
    if isinstance(v, float):
        return f"{v:.2f}"
    return html.escape(str(v))


def write_html(out: Path, spec, rows, misses, step, pin_lines=()):
    parts = [f"<h1>{html.escape(spec['screen'])}: proposal vs build{' step ' + str(step) if step else ''}</h1>",
             f"<p>{len(misses)} misses</p><ul>" + "".join(f"<li>{html.escape(m)}</li>" for m in misses) + "</ul>"]
    if pin_lines:
        parts.append("<h2>Owner pins</h2><ul>" + "".join(f"<li>{html.escape(m)}</li>" for m in pin_lines) + "</ul>")
    for r in rows:
        parts.append(f"<h3>{html.escape(r['id'])}</h3>")
        if r.get("owner"):
            parts.append("<ul style='color:#b00'>" + "".join(f"<li>{html.escape(m)}</li>" for m in r["owner"]) + "</ul>")
        if r.get("missing"):
            parts.append("<p><b>missing in the build</b></p>")
            continue
        parts.append(f"<img src='{html.escape(r['id'])}.png'><table border=1 cellpadding=3><tr><th></th><th>proposal</th><th>build</th></tr>")
        parts.append(f"<tr><td>box x,y,w,h %</td><td>{fmt(r['box_ref'])}</td><td>{fmt(r['box_game'])}</td></tr>")
        for sec in ("fill", "border", "corner", "text", "image"):
            a, b = r["ref"].get(sec), r["game"].get(sec)
            if a is None and b is None:
                continue
            if isinstance(a, dict) or isinstance(b, dict):
                for kk in sorted(set((a or {}).keys()) | set((b or {}).keys())):
                    parts.append(f"<tr><td>{sec}.{kk}</td><td>{fmt((a or {}).get(kk))}</td><td>{fmt((b or {}).get(kk))}</td></tr>")
            else:
                parts.append(f"<tr><td>{sec}</td><td>{fmt(a)}</td><td>{fmt(b)}</td></tr>")
        if r.get("gui"):
            parts.append(f"<tr><td>GUI (Studio)</td><td></td><td>{html.escape(json.dumps(r['gui']))}</td></tr>")
        parts.append("</table>")
    (out / "report.html").write_text("<meta charset=utf-8><body style='font-family:sans-serif'>" + "".join(parts), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--geom", type=Path)
    ap.add_argument("--shot", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--step", type=int)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--owner-notes", action="store_true", help="every open owner note (and pin) from the Be Dino Desk counts as a miss")
    ap.add_argument("--feedback", type=Path, default=FEEDBACK, help="owner notes file (default docs/feedback/menu-feedback.json)")
    a = ap.parse_args(argv)
    if not a.spec.exists():
        print("no spec", a.spec, file=sys.stderr)
        return 2
    if not a.self_test and (not a.geom or not a.shot):
        print("need --geom and --shot (or --self-test)", file=sys.stderr)
        return 2
    out = a.out or ROOT / "build" / "menu-check" / json.loads(a.spec.read_text(encoding="utf-8"))["screen"]
    return compare(a.spec, a.geom, a.shot, out, a.step, a.self_test,
                   feedback=None if a.self_test else a.feedback, owner_flag=a.owner_notes)


if __name__ == "__main__":
    sys.exit(main())
