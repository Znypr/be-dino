#!/usr/bin/env python3
"""BD-408: automated handbook checks (docs/114). Static, no Luau runner and no Studio needed.

Fails (exit 1, one line per problem: `file:line [rule] message`) when:
  (a) ui-floor   a shared UI rule constant allows text under 14 px or a tap target under 44 px, or a literal TextSize /
                 MinTextSize / MaxTextSize / button Size in src/ falls under the floors (counted baseline of known offenders in UI_KNOWN);
  (b) sfx        a cue in `Sfx.Sounds` (or an alias / layer made from one) is louder than the handbook cap 0.9, or a cue name that is
                 played / listed anywhere in src/ is not registered in `Sfx.Sounds`;
  (c) palette    a colour in docs/114 section 5 (and the colour numbers in section 6) differs from the code table that owns it.
                 BOTH sides are parsed; no expected value is written in this file, only the NAME mapping between doc labels and code keys;
  (d) pr-template .github/pull_request_template.md is missing or lost its handbook checklist.

Run: python tools/verify_handbook.py [--root PATH]   (CI: .github/workflows/build-generated-place.yml)
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------------------------------------------------
# (a) KNOWN OFFENDERS (baseline, docs/116 C-37). EMPTY since BD-501: the 18 literals that pre-dated the check were raised to the floors
# (text 14 px, tap target 44 px) with their layouts adjusted and checked in Studio. Key = (file, kind) -> (how many offenders are known, reason).
# kind: "text-literal" (a TextSize / helper size under 14), "text-min" (a UITextSizeConstraint Min/Max under 14), "button" (a size under 44).
# A NEW offender fails with every line listed; a fixed one (count goes down) fails until the number is lowered, so the list can only
# shrink. Do not add entries: fix the code instead.
# --------------------------------------------------------------------------------------------------------------------
UI_KNOWN: dict = {}

# --------------------------------------------------------------------------------------------------------------------
# (c) NAME mappings only (doc label -> code key). Values are always parsed from the files.
# --------------------------------------------------------------------------------------------------------------------
UI_COLOR_LABELS = {  # docs/114 5.1 label -> UITheme Theme.Colors key
    "panel": "panel", "card": "card", "outline/dark text": "outline", "text": "text", "accent green": "accent",
    "gold/amber": "gold", "blue": "blue", "purple": "purple", "red": "red",
}
CAVE_COLOR_LABELS = {  # docs/114 5.10 label -> (module, field)
    "warm cream shafts": ("CaveLightingRules", "BeamColor"),
    "fill lamp": ("CaveLightingRules", "FillColor"),
    "lava": ("CaveLightingRules", "LavaColor"),
    "crystal light": ("CaveLightingRules", "CrystalColor"),
    "forge": ("CaveLightingRules", "ForgeColor"),
    "gate glow": ("CaveLightingRules", "GateGlow.color"),
}


# ====================================================================================================================
# plumbing
# ====================================================================================================================
class Report:
    def __init__(self):
        self.fails = []
        self.checked = {}

    def fail(self, where, rule, msg):
        self.fails.append("FAIL %s [%s] %s" % (where, rule, msg))

    def ok(self, rule, n=1):
        self.checked[rule] = self.checked.get(rule, 0) + n


def strip_comments(src):
    """Blank out Luau comments but keep every newline, so offsets still give the right line number."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("--", i):
            m = re.match(r"--\[(=*)\[", src[i:])
            if m:
                end = src.find("]" + m.group(1) + "]", i)
                end = n if end < 0 else end + len(m.group(1)) + 2
                out.append(re.sub(r"[^\n]", " ", src[i:end]))
                i = end
            else:
                j = src.find("\n", i)
                j = n if j < 0 else j
                out.append(" " * (j - i))
                i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


class Src:
    """A comment-stripped Luau (or markdown) file with offset -> line helpers."""

    def __init__(self, root, rel, luau=True):
        self.rel = rel
        self.path = root / rel
        self.exists = self.path.exists()
        raw = self.path.read_bytes().decode("utf-8").replace(chr(13) + chr(10), chr(10)) if self.exists else ""
        self.text = strip_comments(raw) if luau else raw
        self.lines = self.text.split("\n")

    def line_of(self, pos):
        return self.text.count("\n", 0, pos) + 1


def balanced(text, open_idx):
    """Index just past the bracket that matches text[open_idx] ({ ( [)."""
    pairs = {"{": "}", "(": ")", "[": "]"}
    stack = []
    i, n = open_idx, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            i = j
        elif c in pairs:
            stack.append(pairs[c])
        elif stack and c == stack[-1]:
            stack.pop()
            if not stack:
                return i + 1
        i += 1
    return n


def find_block(src, pattern, flags=0):
    """(start offset of the content, content) of the {...} that follows the first match of `pattern` (which must end before '{')."""
    m = re.search(pattern, src.text, flags)
    if not m:
        return None
    o = src.text.index("{", m.end() - 1 if src.text[m.end() - 1] == "{" else m.end())
    e = balanced(src.text, o)
    return o + 1, src.text[o + 1:e - 1]


def split_top(s):
    """Split on commas that are not inside (), {} or []. Strings are respected."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(s):
        c = s[i]
        if c in "\"'":
            j = i + 1
            while j < len(s) and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            cur.append(s[i:j + 1])
            i = j + 1
            continue
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def top_level_only(block):
    """The block with the inside of nested {...} blanked, so scalar fields at depth 1 can be matched without nested look-alikes."""
    out, depth = [], 0
    for c in block:
        if c == "{":
            depth += 1
            out.append(c)
        elif c == "}":
            depth -= 1
            out.append(c)
        else:
            out.append(c if depth == 0 or c == "\n" else " ")
    return "".join(out)


NUM = r"-?\d*\.?\d+"
RGB3 = r"(%s)\s*,\s*(%s)\s*,\s*(%s)" % (NUM, NUM, NUM)


def rgb_of(expr, colors=None):
    """(r,g,b) ints from Color3.fromRGB(..), {r,g,b}, rgb(..), Color3.new(1,1,1) or a Theme.Colors.x reference."""
    m = re.search(r"Color3\.fromRGB\(\s*" + RGB3 + r"\s*\)", expr) or re.search(r"\brgb\(\s*" + RGB3 + r"\s*\)", expr) \
        or re.search(r"^\s*\{\s*" + RGB3 + r"\s*\}", expr)
    if m:
        return tuple(int(round(float(m.group(i)))) for i in (1, 2, 3))
    m = re.search(r"Color3\.new\(\s*" + RGB3 + r"\s*\)", expr)
    if m:
        return tuple(int(round(float(m.group(i)) * 255)) for i in (1, 2, 3))
    m = re.search(r"Theme\.Colors\.(\w+)", expr)
    if m and colors and m.group(1) in colors:
        return colors[m.group(1)][0]
    return None


def hexs(rgb):
    return "#%02X%02X%02X" % rgb


def fmt(rgb):
    return "%s (%d,%d,%d)" % (hexs(rgb), *rgb)


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def assignments(src):
    """Yield (line, [lhs names], [rhs item strings]) for every `a.X, b.Y = v1, v2` (also `{Field = v}` table fields); several
    statements per line are fine. The last rhs item may carry trailing statements; callers only read a leading literal from it."""
    tok = re.compile(r"[\w.\[\]\"]+$")
    for ln, line in enumerate(src.lines, 1):
        for i, c in enumerate(line):
            if c != "=" or (i + 1 < len(line) and line[i + 1] == "=") or (i > 0 and line[i - 1] in "=~<>!+-*/%^.:"):
                continue
            lhs, j = [], i
            while True:
                head = line[:j].rstrip()
                m = tok.search(head)
                if not m:
                    break
                lhs.insert(0, m.group(0))
                head = head[:m.start()].rstrip()
                if head.endswith(","):
                    j = len(head) - 1
                    continue
                break
            if lhs:
                yield ln, lhs, split_top(line[i + 1:])


def leading_numbers(item):
    """Numeric literals this rhs item can evaluate to: a plain number, or both branches of `if c then N else M`.
    Anything else (a variable, math.max(..), a call) is not a literal -> []."""
    item = item.strip()
    m = re.match(r"^(" + NUM + r")(?![\w.])\s*(?![+\-*/^%(\[.\w]|$)", item) or re.match(r"^(" + NUM + r")\s*$", item)
    if m and not re.match(r"^" + NUM + r"\s*[+\-*/^%]", item):
        return [float(m.group(1))]
    if item.startswith("if "):
        found = re.findall(r"\b(?:then|else)\s+(" + NUM + r")(?![\w.(])", item)
        return [float(x) for x in found]
    return []


# ====================================================================================================================
# docs/114 loading
# ====================================================================================================================
class Doc(Src):
    def section(self, heading_regex):
        """[(lineno, text)] of the lines under the first heading matching `heading_regex`, up to the next heading."""
        out, inside = [], False
        for ln, line in enumerate(self.lines, 1):
            if re.match(r"^#{2,4} ", line):
                if inside:
                    break
                inside = bool(re.match(heading_regex, line))
                continue
            if inside:
                out.append((ln, line))
        return out


DOC_PAIR = re.compile(r"(?P<label>[A-Za-z][A-Za-z/ ]*?)\s*(?:\*\*)?\s+#(?P<hex>[0-9A-Fa-f]{6})\b(?:\*\*)?(?:\s*\((?P<rgb>" + RGB3 + r"))?")


def doc_pairs(lines):
    """[(lineno, label, hex, rgb-in-parens or None)] for 'Label #HEX (r,g,b' items; the label is lower-cased as written."""
    out = []
    for ln, line in lines:
        clean = line.replace("**", "")
        for m in DOC_PAIR.finditer(clean):
            label = m.group("label").strip()
            if label.lower() in ("was", "to", "and"):
                continue
            rgb = None
            if m.group("rgb"):
                nums = re.findall(NUM, m.group("rgb"))
                rgb = tuple(int(float(x)) for x in nums[:3])
            out.append((ln, label, m.group("hex").upper(), rgb))
    return out


# ====================================================================================================================
# (c) palette
# ====================================================================================================================
def compare(rep, doc, ln, label, doc_rgb, code_src, code_ln, code_rgb, what):
    rep.ok("palette")
    if code_rgb is None:
        rep.fail("%s:%d" % (doc.rel, ln), "palette", "%s: handbook lists %s but %s has no value for it" % (label, fmt(doc_rgb), code_src.rel))
    elif tuple(doc_rgb) != tuple(code_rgb):
        rep.fail("%s:%d" % (doc.rel, ln), "palette", "%s: handbook says %s but %s:%d (%s) has %s"
                 % (label, fmt(doc_rgb), code_src.rel, code_ln, what, fmt(code_rgb)))


def keysets(rep, doc, ln, section_name, doc_keys, code_src, code_keys, ignore_code=()):
    for k in sorted(set(doc_keys) - set(code_keys)):
        rep.fail("%s:%d" % (doc.rel, ln), "palette", "%s lists '%s' but %s has no such entry" % (section_name, k, code_src.rel))
    for k in sorted(set(code_keys) - set(doc_keys) - set(ignore_code)):
        rep.fail("%s:%d" % (code_src.rel, 1), "palette", "%s has '%s' which handbook %s does not list" % (code_src.rel, k, section_name))


def check_palette(rep, root):
    doc = Doc(root, "docs/114-handbook.md", luau=False)
    if not doc.exists:
        rep.fail("docs/114-handbook.md:1", "palette", "handbook file is missing")
        return

    # --- doc internal consistency: every '#HEX (r,g,b' pair in section 5 must agree with itself
    s5 = []
    inside = False
    for ln, line in enumerate(doc.lines, 1):
        if re.match(r"^## 5\. ", line):
            inside = True
            continue
        if inside and re.match(r"^## ", line):
            break
        if inside:
            s5.append((ln, line))
    if not s5:
        rep.fail("%s:1" % doc.rel, "palette", "section '## 5. Colour palette' not found")
        return
    for ln, label, h, rgb in doc_pairs(s5):
        rep.ok("palette")
        if rgb and hex_rgb(h) != rgb:
            rep.fail("%s:%d" % (doc.rel, ln), "palette", "%s: #%s and (%d,%d,%d) in the handbook disagree with each other" % (label, h, *rgb))

    # --- 5.1 UI colours (UITheme Theme.Colors)
    ui = Src(root, "src/shared/UITheme.luau")
    colors = {}
    blk = find_block(ui, r"Theme\.Colors\s*=\s*\{")
    if blk:
        base = blk[0]
        for m in re.finditer(r"(\w+)\s*=\s*(Color3\.\w+\([^)]*\))", blk[1]):
            colors[m.group(1)] = (rgb_of(m.group(2)), ui.line_of(base + m.start()))
    sec = doc.section(r"^### 5\.1 ")
    seen = {}
    for ln, label, h, rgb in doc_pairs(sec):
        key = UI_COLOR_LABELS.get(label.lower())
        if key is None:
            rep.fail("%s:%d" % (doc.rel, ln), "palette", "5.1 label '%s' is not in the verifier's UI_COLOR_LABELS name map" % label)
            continue
        seen[key] = ln
        c = colors.get(key)
        compare(rep, doc, ln, "UITheme.Colors.%s" % key, hex_rgb(h), ui, c[1] if c else 0, c[0] if c else None, "Theme.Colors")
    if sec:
        keysets(rep, doc, sec[0][0], "5.1", seen.keys(), ui, colors.keys())

    # --- 5.2 Rarity colours (UITheme Theme.RarityColors, listed by position + the name loop)
    sec = doc.section(r"^### 5\.2 ")
    rar_blk = find_block(ui, r"Theme\.RarityColors\s*=\s*\{")
    names = re.search(r"for\s+index\s*,\s*name\s+in\s*\{([^}]*)\}\s*do\s+Theme\.RarityColors", ui.text)
    rarity = {}
    if rar_blk and names:
        order = re.findall(r'"(\w+)"', names.group(1))
        for i, item in enumerate(split_top(rar_blk[1])):
            if i < len(order):
                rarity[order[i]] = (rgb_of(item, colors), ui.line_of(rar_blk[0]))
    else:
        rep.fail("src/shared/UITheme.luau:1", "palette", "cannot parse Theme.RarityColors / its name loop")
    seen = {}
    for ln, label, h, rgb in doc_pairs(sec):
        if label not in rarity and label.lower() in ("tier",):
            continue
        seen[label] = ln
        c = rarity.get(label)
        compare(rep, doc, ln, "RarityColors.%s" % label, hex_rgb(h), ui, c[1] if c else 0, c[0] if c else None, "Theme.RarityColors")
    if sec:
        keysets(rep, doc, sec[0][0], "5.2", seen.keys(), ui, rarity.keys())

    # --- 5.4 Egg colours (ProgressionConfig.EggColors)
    pc = Src(root, "src/shared/ProgressionConfig.luau")
    sec = doc.section(r"^### 5\.4 ")
    eggs = {}
    blk = find_block(pc, r"EggColors\s*=\s*\{")
    if blk:
        for m in re.finditer(r'name="(\w+)".*?rgb=\{([^}]*)\}', blk[1]):
            eggs[m.group(1)] = (rgb_of("{" + m.group(2) + "}"), pc.line_of(blk[0] + m.start()))
    seen = {}
    for ln, label, h, rgb in doc_pairs(sec):
        seen[label] = ln
        c = eggs.get(label)
        compare(rep, doc, ln, "EggColors.%s" % label, hex_rgb(h), pc, c[1] if c else 0, c[0] if c else None, "ProgressionConfig.EggColors")
    if sec:
        keysets(rep, doc, sec[0][0], "5.4", seen.keys(), pc, eggs.keys())

    # --- 5.6 Event mutations (MutationLook: tint / rim / badge)
    ml = Src(root, "src/shared/MutationLook.luau")
    sec = doc.section(r"^### 5\.6 ")
    muts = {}
    blk = find_block(ml, r"Look\.Entries\s*=\s*\{")
    if blk:
        starts = [m.start() for m in re.finditer(r'\bid = "(\w+)"', blk[1])]
        for i, st in enumerate(starts):
            chunk = blk[1][st:(starts[i + 1] if i + 1 < len(starts) else len(blk[1]))]
            mid = re.match(r'id = "(\w+)"', chunk).group(1)
            vals = {}
            for field in ("tint", "rim", "badge"):
                m = re.search(r"\b%s = (\{[^}]*\})" % field, chunk)
                vals[field] = rgb_of(m.group(1)) if m else None
            muts[mid] = (vals, ml.line_of(blk[0] + st))
    mut_re = re.compile(r"(?P<n>[A-Z][A-Za-z ]*?)\s+#(?P<a>[0-9A-Fa-f]{6})\s*/\s*#(?P<b>[0-9A-Fa-f]{6})\s*/\s*#(?P<c>[0-9A-Fa-f]{6})")
    seen = {}
    for ln, line in sec:
        for m in mut_re.finditer(line):
            mid = m.group("n").replace(" ", "").lower()
            seen[mid] = ln
            entry = muts.get(mid)
            for field, g in (("tint", "a"), ("rim", "b"), ("badge", "c")):
                compare(rep, doc, ln, "MutationLook.%s.%s" % (mid, field), hex_rgb(m.group(g).upper()), ml, entry[1] if entry else 0,
                        entry[0][field] if entry else None, "MutationLook.Entries")
    if sec:
        keysets(rep, doc, sec[0][0], "5.6", seen.keys(), ml, muts.keys())

    # --- 5.7 Auras and trails (ProgressionConfig.Auras / Trails: color)
    sec = doc.section(r"^### 5\.7 ")
    for kind, head in (("Auras", r"Auras:"), ("Trails", r"Trails:")):
        code = {}
        blk = find_block(pc, r"\b%s\s*=\s*\{" % kind)
        if blk:
            for m in re.finditer(r'id="(\w+)".*?\bcolor=(\{[^}]*\})', blk[1]):
                code[m.group(1)] = (rgb_of(m.group(2)), pc.line_of(blk[0] + m.start()))
        seen = {}
        for ln, line in sec:
            m = re.search(head + r"(.*?)(?:\.\s|$|\bTrails:|\bAuras:)", line)
            if not m:
                continue
            for ln2, label, h, rgb in doc_pairs([(ln, m.group(1))]):
                seen[label.lower()] = ln
                c = code.get(label.lower())
                compare(rep, doc, ln, "%s.%s" % (kind, label), hex_rgb(h), pc, c[1] if c else 0, c[0] if c else None, "ProgressionConfig." + kind)
        if sec:
            keysets(rep, doc, sec[0][0], "5.7 " + kind, seen.keys(), pc, code.keys())

    # --- 5.8 Biomes (BiomeMap.Colors)
    bm = Src(root, "src/shared/BiomeMap.luau")
    sec = doc.section(r"^### 5\.8 ")
    biomes = {}
    blk = find_block(bm, r"BiomeMap\.Colors\s*=\s*\{")
    if blk:
        for m in re.finditer(r"(\w+)\s*=\s*(\{[^}]*\})", blk[1]):
            biomes[m.group(1)] = (rgb_of(m.group(2)), bm.line_of(blk[0] + m.start()))
    seen = {}
    for ln, label, h, rgb in doc_pairs(sec):
        seen[label] = ln
        c = biomes.get(label)
        compare(rep, doc, ln, "BiomeMap.Colors.%s" % label, hex_rgb(h), bm, c[1] if c else 0, c[0] if c else None, "BiomeMap.Colors")
    if sec:
        keysets(rep, doc, sec[0][0], "5.8", seen.keys(), bm, biomes.keys())

    # --- 5.9 Weather looks (WeatherLooks: tint / fog / glow)
    wl = Src(root, "src/shared/WeatherLooks.luau")
    sec = doc.section(r"^### 5\.9 ")
    looks = {}
    blk = find_block(wl, r"Weather\.Looks\s*=\s*\{")
    if blk:
        starts = [(m.start(), m.group(1)) for m in re.finditer(r"^\s*(\w+)=look\(\{", blk[1], re.M)]
        for i, (st, lid) in enumerate(starts):
            chunk = blk[1][st:(starts[i + 1][0] if i + 1 < len(starts) else len(blk[1]))]
            vals = {}
            for field in ("tint", "fog", "glow"):
                m = re.search(r"\b%s=(rgb\([^)]*\))" % field, chunk)
                vals[field] = rgb_of(m.group(1)) if m else None
            looks[lid] = (vals, wl.line_of(blk[0] + st))
    seen = {}
    for ln, line in sec:
        for seg in re.split(r";|\.\s", line):
            m = re.match(r"\s*(?P<n>[A-Z][A-Za-z ]*?)\s+#(?P<t>[0-9A-Fa-f]{6})\s*/\s*#(?P<f>[0-9A-Fa-f]{6})(?P<rest>.*)", seg)
            if not m:
                continue
            lid = m.group("n").replace(" ", "").lower()
            seen[lid] = ln
            entry = looks.get(lid)
            wanted = [("tint", m.group("t")), ("fog", m.group("f"))]
            g = re.search(r"glow\s+#([0-9A-Fa-f]{6})", m.group("rest"))
            if g:
                wanted.append(("glow", g.group(1)))
            for field, h in wanted:
                compare(rep, doc, ln, "WeatherLooks.%s.%s" % (lid, field), hex_rgb(h.upper()), wl, entry[1] if entry else 0,
                        entry[0][field] if entry else None, "Weather.Looks")
    if sec:
        keysets(rep, doc, sec[0][0], "5.9", seen.keys(), wl, looks.keys(), ignore_code=("clear",))

    # --- 5.10 Cave (CaveLightingRules, CaveLavaRules.Glow, CaveTerrainRules.Colors)
    cave = Src(root, "src/shared/CaveLightingRules.luau")
    lava = Src(root, "src/shared/CaveLavaRules.luau")
    terrain = Src(root, "src/shared/CaveTerrainRules.luau")
    sec = doc.section(r"^### 5\.10 ")
    cave_vals = {}
    for ln, lhs, rhs in assignments(cave):
        for name, item in zip(lhs, rhs):
            if name.startswith("Rules.") and "." not in name[6:] and rgb_of(item) is not None and name[6:] in ("BeamColor", "FillColor", "LavaColor", "CrystalColor", "ForgeColor"):
                cave_vals[name[6:]] = (rgb_of(item), ln)
    m = re.search(r"Rules\.GateGlow\s*=\s*\{[^\n]*?\bcolor\s*=\s*(\{[^}]*\})", cave.text)
    if m:
        cave_vals["GateGlow.color"] = (rgb_of(m.group(1)), cave.line_of(m.start()))
    look = find_block(cave, r"Rules\.Look\s*=\s*\{")
    look_vals = {}
    if look:
        flat = top_level_only(look[1])
        for field in ("ambient", "fogColor"):
            m = re.search(r"\b%s = (\{[^}]*\})" % field, look[1])
            if m:
                look_vals[field] = (rgb_of(m.group(1)), cave.line_of(look[0] + m.start()))
        m = re.search(r"\bgrade = \{.*?\btint = (\{[^}]*\})", look[1])
        if m:
            look_vals["grade.tint"] = (rgb_of(m.group(1)), cave.line_of(look[0] + m.start()))
        for field in ("brightness", "exposure"):
            m = re.search(r"\b%s = (%s)" % (field, NUM), flat)
            if m:
                look_vals[field] = (float(m.group(1)), cave.line_of(look[0] + m.start()))
    glow = []
    gblk = find_block(lava, r"Rules\.Glow\s*=\s*\{")
    if gblk:
        for m in re.finditer(r"color = (\{[^}]*\})", gblk[1]):
            glow.append((rgb_of(m.group(1)), lava.line_of(gblk[0] + m.start())))
    tcol = {}
    tm = re.search(r"Rules\.Colors\s*=\s*\{([^\n]*)\}", terrain.text)
    if tm:
        for m in re.finditer(r"(\w+)\s*=\s*(\{[^}]*\})", tm.group(1)):
            tcol[m.group(1)] = (rgb_of(m.group(2)), terrain.line_of(tm.start()))
    for ln, line in sec:
        clean = line.replace("**", "")
        for label, (_, field) in CAVE_COLOR_LABELS.items():
            m = re.search(re.escape(label) + r"\s+#([0-9A-Fa-f]{6})", clean, re.I)
            if m:
                c = cave_vals.get(field)
                compare(rep, doc, ln, "CaveLightingRules.%s" % field, hex_rgb(m.group(1).upper()), cave, c[1] if c else 0, c[0] if c else None, label)
        m = re.search(r"sheet layers\s+((?:#[0-9A-Fa-f]{6}(?:,\s*)?)+)", clean) or re.search(r"glow layers\s+((?:#[0-9A-Fa-f]{6}(?:,\s*)?)+)", clean)
        if m:
            for i, h in enumerate(re.findall(r"#([0-9A-Fa-f]{6})", m.group(1))):
                c = glow[i] if i < len(glow) else None
                compare(rep, doc, ln, "CaveLavaRules.Glow[%d].color" % (i + 1), hex_rgb(h.upper()), lava, c[1] if c else 0, c[0] if c else None, "Rules.Glow")
        m = re.search(r"look:\s*ambient\s*\((" + RGB3 + r")\),\s*fog colour\s*\((" + RGB3 + r")\),\s*grade tint\s*\((" + RGB3 + r")\)", clean)
        if m:
            nums = [tuple(int(float(x)) for x in re.findall(NUM, m.group(i))) for i in (1, 5, 9)]
            for (field, label), want in zip((("ambient", "look ambient"), ("fogColor", "look fog colour"), ("grade.tint", "look grade tint")), nums):
                c = look_vals.get(field)
                compare(rep, doc, ln, "CaveLightingRules.Look.%s" % field, want, cave, c[1] if c else 0, c[0] if c else None, label)
        for label, key in (("Concrete", "Concrete"), ("Cobblestone", "Cobblestone")):
            m = re.search(label + r"\s*\(\s*(" + RGB3 + r")", clean)
            if m:
                want = tuple(int(float(x)) for x in re.findall(NUM, m.group(1)))
                c = tcol.get(key)
                compare(rep, doc, ln, "CaveTerrainRules.Colors.%s" % key, want, terrain, c[1] if c else 0, c[0] if c else None, "Rules.Colors")

    # --- 5.11 Classes (ClassInfo.Colors): table rows | Ground | green | #2F9E44 | 47,158,68 |
    ci = Src(root, "src/shared/ClassInfo.luau")
    sec = doc.section(r"^### 5\.11 ")
    classes = {}
    blk = find_block(ci, r"ClassInfo\.Colors\s*=\s*(?:table\.freeze\()?\s*\{")
    if blk:
        for m in re.finditer(r"(\w+)\s*=\s*(Color3\.fromRGB\([^)]*\))", blk[1]):
            classes[m.group(1)] = (rgb_of(m.group(2)), ci.line_of(blk[0] + m.start()))
    seen = {}
    for ln, line in sec:
        m = re.match(r"\|\s*(\w+)\s*\|[^|]*\|\s*#([0-9A-Fa-f]{6})\s*\|\s*(" + RGB3 + r")\s*\|", line)
        if m and m.group(1) != "Class":
            cname = m.group(1)
            seen[cname] = ln
            c = classes.get(cname)
            compare(rep, doc, ln, "ClassInfo.Colors.%s" % cname, hex_rgb(m.group(2).upper()), ci, c[1] if c else 0, c[0] if c else None, "ClassInfo.Colors")
            rgb = tuple(int(float(x)) for x in re.findall(NUM, m.group(3)))
            if rgb != hex_rgb(m.group(2).upper()):
                rep.fail("%s:%d" % (doc.rel, ln), "palette", "ClassInfo.Colors.%s: #%s and %s in the same table row disagree" % (cname, m.group(2), m.group(3)))
    if sec:
        keysets(rep, doc, sec[0][0], "5.11", seen.keys(), ci, classes.keys())

    # --- 6 lighting rows: island light and the cave look numbers (colours and exposure live in code, so they must match)
    cfg = Src(root, "src/shared/Config.luau")
    island = {}
    m = re.search(r"IslandLight\s*=\s*\{([^\n]*)\}", cfg.text)
    if m:
        mb = re.search(r"Brightness\s*=\s*(%s)" % NUM, m.group(1))
        ma = re.search(r"\bAmbient\s*=\s*(\{[^}]*\})", m.group(1))
        mo = re.search(r"OutdoorAmbient\s*=\s*(\{[^}]*\})", m.group(1))
        island = {"Brightness": float(mb.group(1)) if mb else None, "Ambient": rgb_of(ma.group(1)) if ma else None,
                  "OutdoorAmbient": rgb_of(mo.group(1)) if mo else None, "_ln": cfg.line_of(m.start())}
    for ln, line in enumerate(doc.lines, 1):
        if line.startswith("| Island (default)"):
            m = re.search(r"Brightness ([\d.]+), Ambient \((" + RGB3 + r")\), OutdoorAmbient \((" + RGB3 + r")\)", line)
            if not m:
                rep.fail("%s:%d" % (doc.rel, ln), "palette", "cannot find 'Brightness x, Ambient (r,g,b), OutdoorAmbient (r,g,b)' in the island row of section 6")
                continue
            rep.ok("palette")
            if island.get("Brightness") is None or abs(float(m.group(1)) - island["Brightness"]) > 1e-9:
                rep.fail("%s:%d" % (doc.rel, ln), "palette", "island Brightness: handbook says %s but %s:%d has %s"
                         % (m.group(1), cfg.rel, island.get("_ln", 0), island.get("Brightness")))
            compare(rep, doc, ln, "Config.IslandLight.Ambient", tuple(int(float(x)) for x in re.findall(NUM, m.group(2))), cfg, island.get("_ln", 0), island.get("Ambient"), "IslandLight")
            compare(rep, doc, ln, "Config.IslandLight.OutdoorAmbient", tuple(int(float(x)) for x in re.findall(NUM, m.group(6))), cfg, island.get("_ln", 0), island.get("OutdoorAmbient"), "IslandLight")
        if line.startswith("| Cave hub (Sanctuary)"):
            m = re.search(r"ambient \((" + RGB3 + r")\), Brightness ([\d.]+), exposure (%s)" % NUM, line)
            if not m:
                rep.fail("%s:%d" % (doc.rel, ln), "palette", "cannot find 'ambient (r,g,b), Brightness x, exposure y' in the cave row of section 6")
                continue
            compare(rep, doc, ln, "CaveLightingRules.Look.ambient (s6)", tuple(int(float(x)) for x in re.findall(NUM, m.group(1))), cave,
                    look_vals.get("ambient", (0, 0))[1], look_vals.get("ambient", (None, 0))[0], "Rules.Look")
            for field, val in (("brightness", m.group(5)), ("exposure", m.group(6))):
                rep.ok("palette")
                c = look_vals.get(field)
                if c is None or abs(float(val) - c[0]) > 1e-9:
                    rep.fail("%s:%d" % (doc.rel, ln), "palette", "CaveLightingRules.Look.%s: handbook s6 says %s but %s:%d has %s"
                             % (field, val, cave.rel, c[1] if c else 0, c[0] if c else "nothing"))


# ====================================================================================================================
# (b) sound
# ====================================================================================================================
def check_sound(rep, root):
    sfx = Src(root, "src/shared/Sfx.luau")
    rules = Src(root, "src/shared/SfxRules.luau")
    doc = Doc(root, "docs/114-handbook.md", luau=False)
    cap = None
    for ln, line in enumerate(doc.lines, 1):
        m = re.search(r"`Sfx\.MaxCueVolume`\s+([\d.]+)", line)
        if m:
            cap = float(m.group(1))
            break
    if cap is None:
        rep.fail("docs/114-handbook.md:1", "sfx", "section 7 no longer states the hard clamp as '`Sfx.MaxCueVolume` <number>'")
        cap = 0.9
    m = re.search(r"Sfx\.MaxCueVolume\s*=\s*(%s)" % NUM, sfx.text)
    if not m or float(m.group(1)) > cap + 1e-9:
        rep.fail("%s:%d" % (sfx.rel, sfx.line_of(m.start()) if m else 1), "sfx", "Sfx.MaxCueVolume is %s, handbook cap is %s" % (m.group(1) if m else "missing", cap))
    rep.ok("sfx")

    registered, volumes = {}, {}
    blk = find_block(sfx, r"Sfx\.Sounds\s*=\s*\{")
    if not blk:
        rep.fail("%s:1" % sfx.rel, "sfx", "cannot find the Sfx.Sounds table")
        return
    for m in re.finditer(r"^\s*(\w+)\s*=\s*\{([^\n]*)\}\s*,?\s*$", blk[1], re.M):
        name, body = m.group(1), m.group(2)
        ln = sfx.line_of(blk[0] + m.start(1))
        registered[name] = ln
        v = re.search(r"\bvolume\s*=\s*(%s)" % NUM, body)
        rep.ok("sfx")
        if not v:
            rep.fail("%s:%d" % (sfx.rel, ln), "sfx", "cue '%s' has no volume" % name)
            continue
        volumes[name] = float(v.group(1))
        if volumes[name] > cap + 1e-9:
            rep.fail("%s:%d" % (sfx.rel, ln), "sfx", "cue '%s' volume %s is above the cap %s (docs/114 s7)" % (name, v.group(1), cap))

    def need(where_rel, where_ln, kind, name):
        rep.ok("sfx")
        if name not in registered:
            rep.fail("%s:%d" % (where_rel, where_ln), "sfx", "%s '%s' is not registered in Sfx.Sounds (%s)" % (kind, name, sfx.rel))

    # literal calls anywhere in src/
    for path in sorted((root / "src").rglob("*.luau")):
        rel = path.relative_to(root).as_posix()
        s = Src(root, rel)
        for m in re.finditer(r'\bSfx\.(play|playCue)\(\s*"([^"]+)"|\bSfx\.play\s*,\s*"([^"]+)"', s.text):
            need(rel, s.line_of(m.start()), "played cue", m.group(2) or m.group(3))
        for m in re.finditer(r'\bSfx\.playAlias\(\s*"([^"]+)"', s.text):
            rep.ok("sfx")
            if not re.search(r"\b%s\s*=\s*\{cue\s*=" % re.escape(m.group(1)), rules.text):
                rep.fail("%s:%d" % (rel, s.line_of(m.start())), "sfx", "alias '%s' is not in SfxRules.Aliases" % m.group(1))

    # data-driven names
    ht = Src(root, "src/shared/HatchTimeline.luau")
    for m in re.finditer(r'table\.insert\(cues,[^\n]*?\bname\s*=\s*"([^"]+)"', ht.text):
        need(ht.rel, ht.line_of(m.start()), "hatch timeline cue", m.group(1))
    rh = Src(root, "src/shared/RareHatch.luau")
    for m in re.finditer(r'\bsound\s*=\s*"([^"]+)"', rh.text):
        need(rh.rel, rh.line_of(m.start()), "rare-hatch cue", m.group(1))
    for m in re.finditer(r'Sfx\.RevealNames\s*=\s*\{([^}]*)\}', sfx.text):
        for n in re.findall(r'"(\w+)"', m.group(1)):
            need(sfx.rel, sfx.line_of(m.start()), "reveal sting", n)
    hn = re.search(r"function Sfx\.hatchName.*?\nend", sfx.text, re.S)
    if hn:
        for n in re.findall(r'"(\w+)"', hn.group(0)):
            need(sfx.rel, sfx.line_of(hn.start()), "hatchName result", n)
    pr = find_block(rules, r"R\.Priority\s*=\s*\{")
    if pr:
        for m in re.finditer(r"\b([a-z][a-z_0-9]*)\s*=\s*\d+", pr[1]):
            need(rules.rel, rules.line_of(pr[0] + m.start()), "SfxRules.Priority key", m.group(1))
    for table, label in (("R.JitterNames", "SfxRules.JitterNames key"),):
        jb = find_block(rules, re.escape(table) + r"\s*=\s*\{")
        if jb:
            for m in re.finditer(r"\b([a-z][a-z_0-9]*)\s*=\s*true", jb[1]):
                need(rules.rel, rules.line_of(jb[0] + m.start()), label, m.group(1))
    rn = re.search(r"Sfx\.RapidNames\s*=\s*\{([^}]*)\}", sfx.text)
    if rn:
        for n in re.findall(r"\b([a-z][a-z_0-9]*)\s*=\s*true", rn.group(1)):
            need(sfx.rel, sfx.line_of(rn.start()), "Sfx.RapidNames key", n)
    # aliases: must reuse a registered cue and may only turn it DOWN
    al = re.search(r"R\.Aliases\s*=\s*\{", rules.text)
    if al:
        end = balanced(rules.text, rules.text.index("{", al.start()))
        for m in re.finditer(r"(\w+)\s*=\s*\{cue\s*=\s*\"(\w+)\",\s*volume\s*=\s*(%s)" % NUM, rules.text[al.start():end]):
            ln = rules.line_of(al.start() + m.start())
            need(rules.rel, ln, "alias '%s' cue" % m.group(1), m.group(2))
            if m.group(2) in volumes and volumes[m.group(2)] * float(m.group(3)) > cap + 1e-9:
                rep.fail("%s:%d" % (rules.rel, ln), "sfx", "alias '%s' plays '%s' at %.3f, above the cap %s" % (m.group(1), m.group(2), volumes[m.group(2)] * float(m.group(3)), cap))
    ft = Src(root, "src/shared/FtueRules.luau")
    for m in re.finditer(r'Rules\.SoundAlias\s*=\s*"(\w+)"', ft.text):
        rep.ok("sfx")
        if not re.search(r"\b%s\s*=\s*\{cue\s*=" % re.escape(m.group(1)), rules.text):
            rep.fail("%s:%d" % (ft.rel, ft.line_of(m.start())), "sfx", "FTUE sound alias '%s' is not in SfxRules.Aliases" % m.group(1))
    # reveal layers: second registered cue under a sting, multipliers may only turn it down
    rl = re.search(r"R\.RevealLayers\s*=\s*\{", rules.text)
    if rl:
        end = balanced(rules.text, rules.text.index("{", rl.start()))
        for m in re.finditer(r'cue\s*=\s*"(\w+)",\s*volume\s*=\s*(%s)' % NUM, rules.text[rl.start():end]):
            ln = rules.line_of(rl.start() + m.start())
            need(rules.rel, ln, "reveal layer cue", m.group(1))
            if m.group(1) in volumes and volumes[m.group(1)] * float(m.group(2)) > cap + 1e-9:
                rep.fail("%s:%d" % (rules.rel, ln), "sfx", "reveal layer '%s' plays at %.3f, above the cap %s" % (m.group(1), volumes[m.group(1)] * float(m.group(2)), cap))
    # other volume tables
    ws = Src(root, "src/shared/WeatherSounds.luau")
    wb = find_block(ws, r"Sounds\.Sounds\s*=\s*\{")
    if wb:
        for m in re.finditer(r"(\w+)=\{id=\"[^\"]*\",volume=(%s)" % NUM, wb[1]):
            rep.ok("sfx")
            if float(m.group(2)) > cap + 1e-9:
                rep.fail("%s:%d" % (ws.rel, ws.line_of(wb[0] + m.start())), "sfx", "weather sound '%s' volume %s is above the cap %s" % (m.group(1), m.group(2), cap))
    sl = Src(root, "src/shared/SoundLabData.luau")
    for m in re.finditer(r'\{name = "(\w+)", id = "[^"]*", volume = (%s)\}' % NUM, sl.text):
        rep.ok("sfx")
        if float(m.group(2)) > cap + 1e-9:
            rep.fail("%s:%d" % (sl.rel, sl.line_of(m.start())), "sfx", "raw sound '%s' volume %s is above the cap %s" % (m.group(1), m.group(2), cap))
    hp = Src(root, "src/shared/HatchPresentation.luau")
    for m in re.finditer(r"=\s*sound\(\s*\w+\s*,\s*(%s)\s*," % NUM, hp.text):
        rep.ok("sfx")
        if float(m.group(1)) > cap + 1e-9:
            rep.fail("%s:%d" % (hp.rel, hp.line_of(m.start())), "sfx", "hatch presentation sound volume %s is above the cap %s" % (m.group(1), cap))


# ====================================================================================================================
# (a) UI floors
# ====================================================================================================================
BUTTON_NEW = r"Instance\.new\(\s*[\"'](?:TextButton|ImageButton)[\"']\s*\)"
UI_KEYWORDS = ("TextSize", "TextButton", "ImageButton", "MinText", "MinTarget", "MinButton", "minText", "minButton", "MinTap")
TEXT_FIELDS = ("TextSize", "MinTextSize", "MaxTextSize")
TEXT_CONST = re.compile(r"\b((?:\w+\.)?(?:Min(?:Text|TextSize)|minText))\s*=\s*(%s)\b(?!\s*[+\-*/.\w(])" % NUM)
TARGET_CONST = re.compile(r"\b((?:\w+\.)?(?:MinTarget|MinButton|MinTap\w*|minButton))\s*=\s*(%s)\b(?!\s*[+\-*/.\w(])" % NUM)


def param_names(sig):
    return [re.split(r"\s*[:=]", p.strip())[0].strip() for p in split_top(sig) if p.strip()]


def function_defs(s):
    """[(name, params, first line, last line)] for `local function name(...)` and `local name = function(...)`."""
    defs = []
    for m in re.finditer(r"^([ \t]*)(?:local\s+)?function\s+([\w.:]+)\s*\(([^)]*)\)|^([ \t]*)local\s+(\w+)\s*=\s*function\s*\(([^)]*)\)", s.text, re.M):
        indent = m.group(1) if m.group(2) else m.group(4)
        name = m.group(2) or m.group(5)
        params = param_names(m.group(3) if m.group(2) else m.group(6))
        first = s.line_of(m.start())
        last = first
        for i in range(first, len(s.lines)):
            if re.match(r"^" + re.escape(indent) + r"end\b", s.lines[i]):
                last = i + 1
                break
        else:
            last = min(len(s.lines), first + 40)
        # one-line functions end on their own line
        if re.search(r"\bend\s*\)?\s*$", s.lines[first - 1]) and "function" in s.lines[first - 1] and not s.lines[first - 1].rstrip().endswith("do"):
            last = first
        defs.append((name, params, first, last))
    return defs


def call_args(s, name):
    """[(line, [arg strings])] for every call `name(...)` in the file that is not its definition."""
    out = []
    for m in re.finditer(r"(?<![\w.:])%s\s*\(" % re.escape(name), s.text):
        line = s.lines[s.line_of(m.start()) - 1]
        if re.search(r"function\s+%s\b" % re.escape(name), line) or re.search(r"local\s+%s\s*=\s*function" % re.escape(name), line):
            continue
        o = m.end() - 1
        e = balanced(s.text, o)
        out.append((s.line_of(m.start()), split_top(s.text[o + 1:e - 1])))
    return out


def size_dims(expr):
    """(width expr or None, height expr or None) for a UDim2 constructor that is pure pixels on that axis, else (None, None)."""
    m = re.match(r"^\s*UDim2\.fromOffset\((.*)\)\s*$", expr, re.S)
    if m:
        a = split_top(m.group(1))
        if len(a) == 2:
            return a[0], a[1]
    m = re.match(r"^\s*UDim2\.new\((.*)\)\s*$", expr, re.S)
    if m:
        a = split_top(m.group(1))
        if len(a) == 4:
            return (a[1] if a[0].strip() in ("0", "0.0") else None), (a[3] if a[2].strip() in ("0", "0.0") else None)
    return None, None


def check_ui(rep, root, args):
    found = {}  # (file, kind) -> [(line, message)]

    def viol(rel, kind, ln, msg):
        found.setdefault((rel, kind), []).append((ln, msg))

    phone = Src(root, "src/shared/PhoneScale.luau")
    doc = Doc(root, "docs/114-handbook.md", luau=False)

    min_text = min_btn = None
    for line in doc.lines:
        m = re.search(r"Minimum text (\d+) px on screen, minimum button/target (\d+) px", line)
        if m:
            min_text, min_btn = int(m.group(1)), int(m.group(2))
            break
    if min_text is None:
        rep.fail("docs/114-handbook.md:1", "ui-floor", "section 4.4 no longer states 'Minimum text N px on screen, minimum button/target N px'")
        min_text, min_btn = 14, 44

    # shared rule constants
    needed = {"MinText": ("PhoneScale", phone, min_text), "MinButton": ("PhoneScale", phone, min_btn)}
    for const, (mod, s, floor) in needed.items():
        m = re.search(r"\b%s\.%s\s*=\s*(%s)" % (mod, const, NUM), s.text)
        rep.ok("ui-floor")
        if not m:
            rep.fail("%s:1" % s.rel, "ui-floor", "%s.%s is missing (docs/114 s4.4 names it as the shared floor)" % (mod, const))
        elif float(m.group(1)) < floor:
            rep.fail("%s:%d" % (s.rel, s.line_of(m.start())), "ui-floor", "%s.%s = %s is under the handbook floor %d px" % (mod, const, m.group(1), floor))
    files = sorted(p for p in (root / "src").rglob("*.luau") if "server" not in p.relative_to(root / "src").parts)
    for path in files:
        rel = path.relative_to(root).as_posix()
        if not any(k in path.read_text(encoding="utf-8") for k in UI_KEYWORDS):  # skips the big generated data files cheaply
            continue
        s = Src(root, rel)
        for rx, floor, kind in ((TEXT_CONST, min_text, "text"), (TARGET_CONST, min_btn, "tap target")):
            for m in rx.finditer(s.text):
                rep.ok("ui-floor")
                if float(m.group(2)) < floor:
                    rep.fail("%s:%d" % (rel, s.line_of(m.start())), "ui-floor", "rule constant %s = %s allows a %s under %d px (docs/114 s4.4)" % (m.group(1), m.group(2), kind, floor))

        # literal TextSize / MinTextSize / MaxTextSize
        assigns = list(assignments(s))
        by_line = {}
        for a in assigns:
            by_line.setdefault(a[0], []).append(a)
        text_params = {}  # helper name -> param index feeding TextSize
        button_params = {}  # helper name -> (width idx, height idx, size idx)
        defs = function_defs(s)
        for name, params, first, last in defs:
            body_assigns = [a for ln in range(first, last + 1) for a in by_line.get(ln, [])]
            for ln, lhs, rhs in body_assigns:
                for l, r in zip(lhs, rhs):
                    base = r.strip()
                    if l.split(".")[-1] == "TextSize" and base in params:
                        text_params[name] = params.index(base)
            btn_body = "\n".join(s.lines[first - 1:last])
            if re.search(BUTTON_NEW, btn_body):
                for ln, lhs, rhs in body_assigns:
                    for l, r in zip(lhs, rhs):
                        if l.split(".")[-1] != "Size":
                            continue
                        r = r.strip()
                        if r in params:
                            button_params[name] = (None, None, params.index(r))
                        else:
                            w, h = size_dims(r)
                            wi = params.index(w.strip()) if w and w.strip() in params else None
                            hi = params.index(h.strip()) if h and h.strip() in params else None
                            if wi is not None or hi is not None:
                                button_params[name] = (wi, hi, None)
        for ln, lhs, rhs in assigns:
            for l, r in zip(lhs, rhs):
                field = l.split(".")[-1]
                if field in TEXT_FIELDS:
                    for v in leading_numbers(r):
                        rep.ok("ui-floor")
                        if v < min_text:
                            viol(rel, "text-min" if field != "TextSize" else "text-literal", ln, "%s = %g allows text under %d px (docs/114 s4.4, docs/72)" % (l, v, min_text))
        for hname, idx in text_params.items():
            for ln, args in call_args(s, hname):
                if idx < len(args):
                    for v in leading_numbers(args[idx]):
                        rep.ok("ui-floor")
                        if v < min_text:
                            viol(rel, "text-literal", ln, "%s(...) passes text size %g (under %d px, docs/114 s4.4)" % (hname, v, min_text))

        # button sizes: helper calls and directly built buttons
        def check_dim(ln, label, expr):
            for v in leading_numbers(expr):
                rep.ok("ui-floor")
                if v < min_btn:
                    viol(rel, "button", ln, "%s is %g px, under the %d px tap-target floor (docs/114 s4.4)" % (label, v, min_btn))
        for hname, (wi, hi, si) in button_params.items():
            for ln, a in call_args(s, hname):
                if wi is not None and wi < len(a):
                    check_dim(ln, "%s(...) button width" % hname, a[wi])
                if hi is not None and hi < len(a):
                    check_dim(ln, "%s(...) button height" % hname, a[hi])
                if si is not None and si < len(a):
                    w, h = size_dims(a[si])
                    if w:
                        check_dim(ln, "%s(...) button width" % hname, w)
                    if h:
                        check_dim(ln, "%s(...) button height" % hname, h)
        for m in re.finditer(r"(?:local\s+)?(\w+)\s*=\s*" + BUTTON_NEW, s.text):
            var, start = m.group(1), s.line_of(m.start())
            if any(first <= start <= last and name in button_params for name, _, first, last in defs):
                continue  # inside a helper: judged at its call sites
            for ln, lhs, rhs in [a for k in range(start, start + 31) for a in by_line.get(k, [])]:
                for l, r in zip(lhs, rhs):
                    if l == var + ".Size":
                        w, h = size_dims(r)
                        if w:
                            check_dim(ln, "button '%s' width" % var, w)
                        if h:
                            check_dim(ln, "button '%s' height" % var, h)

    for key in sorted(set(found) | set(UI_KNOWN)):
        hits = sorted(found.get(key, []))
        known = UI_KNOWN.get(key, (0, ""))[0]
        if len(hits) > known:
            for ln, msg in hits:
                rep.fail("%s:%d" % (key[0], ln), "ui-floor", "%s%s" % (msg, " [baseline allows %d of this kind in this file, found %d: a NEW offender]" % (known, len(hits)) if known else ""))
        elif len(hits) < known:
            rep.fail("tools/verify_handbook.py:1", "ui-floor", "%s '%s': baseline says %d known offenders but only %d are left; lower UI_KNOWN (the list only shrinks)" % (key[0], key[1], known, len(hits)))
        else:
            rep.ok("ui-floor-known", len(hits))


# ====================================================================================================================
# (d) PR template
# ====================================================================================================================
def check_template(rep, root):
    candidates = [".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.md", "pull_request_template.md"]
    path = next((root / c for c in candidates if (root / c).exists()), None)
    rep.ok("pr-template")
    if path is None:
        rep.fail(".github/pull_request_template.md:1", "pr-template", "the PR template is missing (docs/114 s13: every PR body carries the handbook checklist)")
        return
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(root).as_posix()
    for needle in ("Handbook check", "docs/114"):
        if needle not in text:
            rep.fail("%s:1" % rel, "pr-template", "the PR template lost its '%s' section" % needle)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="repository root (default: this checkout)")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    rep = Report()
    check_ui(rep, root, args)
    check_sound(rep, root)
    check_palette(rep, root)
    check_template(rep, root)
    for line in rep.fails:
        print(line)
    summary = ", ".join("%s %d" % (k, v) for k, v in sorted(rep.checked.items()))
    if rep.fails:
        print("\nhandbook check FAILED: %d problem(s). Rules: docs/114 s4.4, s5, s7, s13. Fix the code, or fix the handbook when the code is the newer owner-approved value (docs/115)." % len(rep.fails))
        print("checked: " + summary)
        return 1
    print("handbook ok (%s)" % summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
