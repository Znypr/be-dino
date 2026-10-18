"""BD-647: build a labelled contact sheet and a references.md from a small folder of reference pictures (docs/167).

    python tools/reference_sheet.py docs/reference/cockatoo
    python tools/reference_sheet.py docs/reference/cockatoo --check      # only check sources.json, write nothing

The folder holds at most about 8 SMALL images and a `sources.json` that says where each one came from. An agent fills the folder
by hand in the owner's browser (docs/167 section 2); this tool never goes on the internet and never downloads anything.

sources.json (a list, or an object with "creature" and "images"):

    {"creature": "cockatoo",
     "images": [
       {"file": "side-photo.jpg", "kind": "photo", "title": "Sulphur-crested cockatoo, side",
        "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg", "license": "CC BY-SA 4.0, Jane Doe",
        "date_read": "2026-10-18", "copy": "crest swept back, hooked beak, round eye ring"}]}

`kind` is photo, cartoon, 3d, owner or ai. `date_read` defaults to today. `copy` is the anatomy / shape note: what to copy.
Writes `contact-sheet.png` (numbered tiles, one caption each) and `references.md` next to the images. Pillow is only used to
tile and label finished pictures for review; it draws no art (AGENTS.md art rule). The pictures are REFERENCE ONLY.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
KINDS = ("photo", "cartoon", "3d", "owner", "ai")
SHEET_NAME = "contact-sheet.png"
MD_NAME = "references.md"
SOURCES_NAME = "sources.json"
MAX_IMAGES = 8
BIG_BYTES = 1_500_000
BIG_SIDE = 2400
WARNING = ("REFERENCE ONLY. These pictures are for looking at, not for use as final art, textures or icons (AGENTS.md art rule: "
           "final art is made in Blender or by the owner). Every picture keeps its own licence: do not republish it, keep the "
           "source link, and do not copy it into the game.")
# A licence note that contains one of these means "look, do not reuse" (and the warning line is repeated for that picture).
RESTRICTED_WORDS = ("all rights reserved", "copyright", "unknown", "unspecified", "not free", "editorial", "no licence", "no license")
FREE_WORDS = ("cc0", "cc-0", "public domain", "cc by", "cc-by", "pexels licen", "pixabay licen", "unsplash licen", "owner")
SENTINEL_OWNER = "owner"


def today():
    return datetime.date.today().isoformat()


def load_sources(folder):
    """Returns (creature, entries). Raises ValueError with a plain message when the file is missing or broken."""
    path = Path(folder) / SOURCES_NAME
    if not path.is_file():
        raise ValueError(f"{path} is missing: record the source URL and licence of every picture there")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as err:
        raise ValueError(f"{path} is not valid JSON: {err}") from err
    creature = None
    if isinstance(data, dict):
        creature = data.get("creature")
        data = data.get("images")
    if not isinstance(data, list):
        raise ValueError(f"{path} must be a list of images, or an object with an \"images\" list")
    entries = [e for e in data if isinstance(e, dict)]
    if len(entries) != len(data):
        raise ValueError(f"{path}: every image entry must be an object")
    return creature, entries


def validate(folder, entries, max_images=MAX_IMAGES):
    """Returns (errors, warnings), both lists of plain sentences. Errors stop the build; warnings are printed."""
    folder = Path(folder)
    errors, warnings = [], []
    if not entries:
        errors.append("sources.json lists no images")
    if len(entries) > max_images:
        errors.append(f"{len(entries)} images listed; keep a small set (at most {max_images})")
    seen = set()
    for number, entry in enumerate(entries, 1):
        name = entry.get("file")
        tag = f"image {number} ({name})"
        if not isinstance(name, str) or not name:
            errors.append(f"image {number}: no \"file\"")
            continue
        if name in seen:
            errors.append(f"{tag}: listed twice")
        seen.add(name)
        path = folder / name
        if Path(name).name != name:
            errors.append(f"{tag}: the file must sit directly in the folder")
        elif not path.is_file():
            errors.append(f"{tag}: file not found in {folder}")
        else:
            if path.stat().st_size > BIG_BYTES:
                warnings.append(f"{tag}: {path.stat().st_size // 1000} KB; save a smaller copy (reference pictures stay small)")
        kind = entry.get("kind", "photo")
        if kind not in KINDS:
            errors.append(f"{tag}: kind must be one of {', '.join(KINDS)}")
        url = entry.get("source_url")
        if kind == "owner":
            pass  # the owner's own picture: no URL needed
        elif not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
            errors.append(f"{tag}: source_url must be the real web address the picture came from")
        if not isinstance(entry.get("license"), str) or not entry["license"].strip():
            errors.append(f"{tag}: license is empty; write the licence and the author, or \"unknown\" if the page does not say")
        if not isinstance(entry.get("copy"), str) or not entry["copy"].strip():
            warnings.append(f"{tag}: no \"copy\" note; say what to take from this picture (shape, colours, pose)")
        date = entry.get("date_read")
        if date is not None:
            try:
                datetime.date.fromisoformat(str(date))
            except ValueError:
                errors.append(f"{tag}: date_read must look like 2026-10-18")
    listed = {e.get("file") for e in entries}
    for path in sorted(folder.iterdir()) if folder.is_dir() else []:
        if path.suffix.lower() in IMAGE_SUFFIXES and path.name != SHEET_NAME and path.name not in listed:
            warnings.append(f"{path.name} is in the folder but not in sources.json (it is left out of the sheet)")
    return errors, warnings


def licence_class(text):
    low = (text or "").lower()
    if any(w in low for w in RESTRICTED_WORDS) and not any(w in low for w in ("cc0", "public domain")):
        return "restricted"
    if any(w in low for w in FREE_WORDS):
        return "free"
    return "check"


# ----------------------------------------------------------------------------------------------------- contact sheet
def _font(size):
    from PIL import ImageFont
    for candidate in ("arial.ttf", "C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _fit(text, font, draw, width):
    if draw.textlength(text, font=font) <= width:
        return text
    while len(text) > 1 and draw.textlength(text + "...", font=font) > width:
        text = text[:-1]
    return text + "..."


def build_sheet(folder, entries, out_path, cell=320, columns=4):
    from PIL import Image, ImageDraw, ImageOps
    folder = Path(folder)
    count = len(entries)
    columns = max(1, min(columns, count))
    rows = (count + columns - 1) // columns
    pad, caption_h, head_h, foot_h = 10, 58, 34, 30
    width = columns * (cell + pad) + pad
    height = head_h + rows * (cell + caption_h + pad) + pad + foot_h
    sheet = Image.new("RGB", (width, height), (226, 226, 230))
    draw = ImageDraw.Draw(sheet)
    big, small = _font(18), _font(14)
    draw.text((pad, 8), "Reference sheet", fill=(40, 40, 46), font=big)
    for index, entry in enumerate(entries):
        col, row = index % columns, index // columns
        x = pad + col * (cell + pad)
        y = head_h + row * (cell + caption_h + pad)
        tile = Image.new("RGB", (cell, cell), (246, 246, 248))
        image = ImageOps.exif_transpose(Image.open(folder / entry["file"]))
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            backing = Image.new("RGBA", image.size, (246, 246, 248, 255))
            backing.alpha_composite(image)
            image = backing
        image = image.convert("RGB")
        image.thumbnail((cell, cell), Image.LANCZOS)
        tile.paste(image, ((cell - image.width) // 2, (cell - image.height) // 2))
        sheet.paste(tile, (x, y))
        kind = entry.get("kind", "photo")
        draw.rectangle([x, y + cell, x + cell, y + cell + caption_h], fill=(255, 255, 255))
        draw.text((x + 6, y + cell + 4), _fit(f"{index + 1}. {entry.get('title') or entry['file']}", small, draw, cell - 12),
                  fill=(20, 20, 26), font=small)
        draw.text((x + 6, y + cell + 22), _fit(f"{kind} | {entry.get('license') or 'licence?'}", small, draw, cell - 12),
                  fill=(90, 90, 100), font=small)
        draw.text((x + 6, y + cell + 39), _fit(Path(entry["file"]).name, small, draw, cell - 12), fill=(120, 120, 130), font=small)
    draw.text((pad, height - foot_h + 6), "REFERENCE ONLY - not final art (AGENTS.md art rule). Sources and licences: references.md",
              fill=(150, 30, 30), font=small)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, optimize=True)
    return sheet.size


# ----------------------------------------------------------------------------------------------------- references.md
def build_markdown(creature, entries, sheet_name=SHEET_NAME, default_date=None):
    default_date = default_date or today()
    lines = [
        f"# References: {creature}",
        "",
        f"> **{WARNING}**",
        "",
        f"![contact sheet]({sheet_name})",
        "",
        f"{len(entries)} pictures. Numbers match the labels on the sheet.",
        "",
    ]
    for number, entry in enumerate(entries, 1):
        kind = entry.get("kind", "photo")
        source = entry.get("source_url") or ("the owner's own picture" if kind == "owner" else "MISSING")
        licence = (entry.get("license") or "").strip() or "not recorded"
        lines += [
            f"## {number}. {entry.get('title') or entry['file']}",
            "",
            f"- File: `{entry['file']}` ({kind})",
            f"- Source: {source}",
            f"- Licence / author: {licence}",
            f"- Date read: {entry.get('date_read') or default_date}",
            f"- What to copy: {(entry.get('copy') or '').strip() or 'not written yet'}",
        ]
        if licence_class(licence) != "free":
            lines.append("- Licence warning: this picture may not be free to reuse. Look at it only. Do not put it in the game.")
        lines.append("")
    lines += [
        "## Rules for using this set",
        "",
        "- Reference only. Model from the notes above, in Blender or with the generator, and compare against these pictures.",
        "- Never trace, import or re-upload a picture here as a texture, icon or sprite.",
        "- Add the creature's line to docs/77-asset-registry.md when a model made from this set is added.",
        "",
    ]
    return "\n".join(lines)


def run(folder, name=None, check=False, max_images=MAX_IMAGES, cell=320, columns=4, date=None):
    """Returns (exit_code, messages). Writes the sheet and references.md unless check is true."""
    folder = Path(folder)
    messages = []
    if not folder.is_dir():
        return 1, [f"{folder} is not a folder"]
    try:
        creature, entries = load_sources(folder)
    except ValueError as err:
        return 1, [str(err)]
    errors, warnings = validate(folder, entries, max_images)
    messages += [f"WARNING: {w}" for w in warnings]
    if errors:
        return 1, messages + [f"ERROR: {e}" for e in errors]
    if check:
        return 0, messages + [f"ok: {len(entries)} pictures, sources recorded"]
    creature = name or creature or folder.name
    size = build_sheet(folder, entries, folder / SHEET_NAME, cell=cell, columns=columns)
    (folder / MD_NAME).write_text(build_markdown(creature, entries, SHEET_NAME, date), encoding="utf-8", newline="\n")
    return 0, messages + [f"wrote {folder / SHEET_NAME} {size[0]}x{size[1]}", f"wrote {folder / MD_NAME}"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", help="folder with the images and sources.json")
    ap.add_argument("--name", help="creature name for the title (default: from sources.json, else the folder name)")
    ap.add_argument("--check", action="store_true", help="only check sources.json and the files")
    ap.add_argument("--max", type=int, default=MAX_IMAGES, help="most pictures allowed (default 8)")
    ap.add_argument("--cell", type=int, default=320, help="tile size in pixels (default 320)")
    ap.add_argument("--columns", type=int, default=4)
    ap.add_argument("--date", help="date to print for pictures without date_read (default today)")
    args = ap.parse_args(argv)
    code, messages = run(args.folder, args.name, args.check, args.max, args.cell, args.columns, args.date)
    print("\n".join(messages))
    return code


if __name__ == "__main__":
    sys.exit(main())
