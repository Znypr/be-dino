#!/usr/bin/env python3
"""Kid-text linter (BD-655, docs/162): checks player-visible strings against the owner rule
"children as audience: short, obvious text" (docs/72, docs/114).

It reads Luau files, finds the strings a player can see (Text = "...", notify("..."), label/button
helpers, copy tables, string.format templates) and flags:

  TIME_NOISE   "5m 0s", "2h 0m", "1:02:03"          (docs/72: write "5 min", "2 h")
  MULTIPLIER   "1.25x", "x2", "%gx"                  (write "Speed +25%")
  DECIMAL      "2.5", "%.1f"                         (no decimals unless the number is the point)
  RAW_ID       "rbxassetid", "BD-12", "save_failed", "CamelCaseThing", long digit runs
  SHOUTING     ALL CAPS beyond a short allowlist, "!!!"
  LONG_TEXT    too many words / characters / sentences for the UI slot (table LIMITS)
  JARGON       words in table JARGON ("server", "profile", "cooldown", ...)
  TECH_PUNCT   | { } [ ] < > _ \\ ~ ^ @ # $ = -> :: ;

Modes:
  python tools/lint_kid_text.py                        list every problem, exit 1 if any
  python tools/lint_kid_text.py --baseline             CI mode: exit 1 only for NEW problems
                                                       (compared with tools/lint_kid_text_baseline.json)
  python tools/lint_kid_text.py --write-baseline       record today's problems as the baseline
  python tools/lint_kid_text.py --report --top 20      worst files and worst texts, exit 0
  python tools/lint_kid_text.py --rules                print the rule and limit tables
  python tools/lint_kid_text.py --selftest             run the built-in examples

Allowlist: tools/lint_kid_text_allow.json, one reason per entry. Inline: add `-- kidtext-ok: reason`
to the end of the line. No game string is edited by this tool.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOW_FILE = ROOT / "tools" / "lint_kid_text_allow.json"
BASELINE_FILE = ROOT / "tools" / "lint_kid_text_baseline.json"
DEFAULT_PATHS = ["src/client", "src/shared"]

# ---------------------------------------------------------------------------------------------
# ONE place for every number and word list the rules use.
# ---------------------------------------------------------------------------------------------

# Per UI slot: (max characters, max words, max sentences). Format codes like %d count as 2 characters.
LIMITS = {
    "title": (24, 4, 1),     # headings, sign text, item names
    "button": (20, 3, 1),    # button faces
    "label": (40, 7, 1),     # small labels, chips, pills, status lines
    "toast": (60, 10, 2),    # notify / banner messages
    "body": (90, 16, 2),     # explanations, hints, descriptions
    "default": (90, 16, 2),  # any other visible text
}

# ALL CAPS is fine for short words. A string is "shouting" when it has 4+ capital letters, is all
# caps and is longer than CAPS_MAX_CHARS characters or has more than CAPS_MAX_WORDS words.
CAPS_MAX_CHARS = 12
CAPS_MAX_WORDS = 2
CAPS_MIN_LETTERS = 4
CAPS_OK_WORDS = {"HOME", "XP", "HP", "OK", "GO", "NEW", "MAX", "VIP", "FREE", "WASD", "PC", "UTC", "EXIT", "SOLD", "OUT", "YES", "NO", "ON", "OFF", "LVL", "MPH", "KG"}

# Words a child should not meet. Value = the plain-word hint shown in the report.
JARGON = {
    "server": "say 'game' or leave it out",
    "servers": "say 'game' or leave it out",
    "profile": "say 'your game' or 'your dinos'",
    "revision": "leave it out",
    "lease": "leave it out",
    "datastore": "leave it out",
    "database": "leave it out",
    "cooldown": "say 'wait' or 'ready in 5 s'",
    "rng": "say 'luck'",
    "probability": "say 'chance'",
    "probabilities": "say 'chances'",
    "multiplier": "say 'bonus' (Speed +20%)",
    "cache": "leave it out",
    "payload": "leave it out",
    "session": "say 'game' or 'visit'",
    "config": "leave it out",
    "instance": "leave it out",
    "parameter": "leave it out",
    "timeout": "say 'took too long'",
    "ledger": "docs/72 bans it",
    "transform": "docs/72 bans it",
    "idle": "docs/72 bans it",
    "window": "docs/72 bans it",
    "latency": "leave it out",
    "ping": "leave it out",
    "fps": "leave it out",
    "sync": "say 'saving'",
    "syncing": "say 'saving'",
    "request": "say 'try again'",
    "requests": "say 'try again'",
    "invalid": "say what to do instead",
    "null": "leave it out",
    "nil": "leave it out",
    "undefined": "leave it out",
    "exception": "leave it out",
    "backend": "leave it out",
    "rate-limited": "say 'slow down'",
    "retry": "say 'try again'",
    "retrying": "say 'trying again'",
    "catches": "docs/FtueCopy: say 'eggs'",
    "banked": "docs/FtueCopy: say 'saved'",
    "bank": "docs/FtueCopy: say 'save'",
    "telemetry": "leave it out",
    "diagnostics": "leave it out",
    "debug": "leave it out",
    "admin": "leave it out",
    "metadata": "leave it out",
    "token": "leave it out",
    "remote": "leave it out",
    "buffer": "leave it out",
    "flag": "leave it out",
}

# Characters and groups that look like code. "&", "•", "%", "!", "?", "...", "(", ")", ":" are fine.
TECH_PUNCT_CHARS = set("|{}[]<>\\~^@#$=;`")   # "_" is caught by RAW_ID (snake_case)
TECH_PUNCT_WORDS = ["->", "=>", "::", "//", "&&", "→"]

# Files that players never see (admin, QA, demo and debug tools). Value = why.
EXCLUDED_FILES = {
    "src/client/AdminPanel.client.luau": "admin tool, not for players",
    "src/client/AdminGiftPage.luau": "admin tool, not for players",
    "src/client/QaOverlay.client.luau": "QA overlay, off for players",
    "src/client/DemoDirector.client.luau": "demo tool, off for players",
    "src/client/UiScan.luau": "developer scan, off for players",
    "src/client/SoundLab.luau": "sound lab, developer tool",
    "src/shared/AdminGiftRules.luau": "admin tool, not for players",
    "src/shared/AdminRules.luau": "admin tool, not for players",
    "src/shared/QaOverlayRules.luau": "QA overlay, off for players",
    "src/shared/DemoShots.luau": "demo tool, off for players",
    "src/shared/SoundLabData.luau": "sound lab, developer tool",
    "src/shared/CaveHubProps.luau": "developer notes about props (note = ...), not shown",
    "src/shared/HatchV2Assets.luau": "developer notes about assets, not shown",
    "src/shared/AssetPalette.luau": "developer notes about assets, not shown",
}

# Files where every multi-word string is player copy.
COPY_FILE_PATTERN = re.compile(r"(Copy|Signs?|Text)\w*\.luau$|NotifyQueue\.luau$|OddsCopy\.luau$")

# Key names (a `key = "..."` assignment) that hold visible text, and the slot they belong to.
TEXT_KEY_SLOTS = {
    "text": "default", "placeholdertext": "default", "label": "label", "title": "title", "header": "title",
    "headline": "title", "sign": "title", "name": "title", "titleprefix": "title", "body": "body",
    "hint": "body", "caption": "body", "desc": "body", "description": "body", "subtitle": "body",
    "note": "body", "blurb": "body", "prompt": "body", "tooltip": "body", "tip": "body",
    "message": "toast", "msg": "toast", "status": "label", "line": "label", "buttontext": "button",
    "secretline": "label", "progress": "label", "lines": "body", "benefit": "body", "sub": "body",
    "tagline": "body", "failsub": "body",
}
TEXT_KEY_SUFFIXES = {"text": "default", "label": "label", "title": "title", "copy": "default", "line": "label",
                     "hint": "body", "caption": "body", "message": "toast", "msg": "toast", "blurb": "body",
                     "header": "title", "button": "button"}
# Instance property names that look like data keys but are NOT text.
NOT_TEXT_KEYS = {"Name", "ClassName", "Font", "Image", "Texture", "TextureId", "MeshId", "SoundId", "Material"}

# Calls whose string arguments are shown to the player: name fragment -> slot.
TEXT_CALL_SLOTS = [
    ("notify", "toast"), ("toast", "toast"), ("announce", "toast"), ("message", "toast"), ("banner", "toast"),
    ("button", "button"), ("btn", "button"),
    ("title", "title"), ("headline", "title"),
    ("hint", "body"), ("tooltip", "body"), ("caption", "body"), ("popup", "body"),
    ("label", "label"), ("chip", "label"), ("pill", "label"), ("status", "label"),
    ("text", "default"),
]
# Calls that pass strings through (look further back for the real owner of the text).
TRANSPARENT_CALLS = {"string.format", "format", "tostring", "tonumber", "string.rep", "string.upper", "string.lower",
                     "table.concat", "table.insert", "select", "math.floor", "math.max", "math.min", "if", "and", "or", "not",
                     "return", "setmetatable", "typeof", "type", "pcall", "ipairs", "pairs", "next"}
# Calls whose strings are never player text.
NON_TEXT_CALLS = {"warn", "print", "error", "assert", "require", "Instance.new", "FindFirstChild", "WaitForChild",
                  "FindFirstChildOfClass", "GetAttribute", "SetAttribute", "IsA", "GetService", "GetChildren", "tag",
                  "HasTag", "AddTag", "RemoveTag", "FindFirstDescendant", "GetDescendants", "Fire", "FireServer",
                  "FireClient", "FireAllClients", "InvokeServer", "Connect", "GetPropertyChangedSignal", "Create"}

# Rule hit patterns (regex, short plain detail). Format codes are still in the text when these run.
TIME_NOISE_PATTERNS = [
    (re.compile(r"(?<![\w.])(?:\d+|%\d*d)\s?[hms]\s+(?:\d+|%\d*d)\s?[hms]\b"), "write '5 min' or '2 h', not '5m 0s'"),
    (re.compile(r"(?<![\w.])(?:\d+|%\d*d):(?:\d\d|%0?2d):(?:\d\d|%0?2d)(?![\w])"), "no hours:minutes:seconds clocks"),
    (re.compile(r"(?<![\w.])0\s?[hms]\b"), "drop zero units"),
    (re.compile(r"(?<![\w.])(?:\d+|%\d*d)\s?ms\b"), "no milliseconds"),
]
MULTIPLIER_PATTERNS = [
    (re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s?[x×](?![\w])"), "write 'Speed +25%', not '1.25x'"),
    (re.compile(r"%[\d.]*[dgf]\s?[x×](?![\w])"), "write 'Speed +25%', not '1.25x'"),
    (re.compile(r"(?<![\w.])[x×]\s?(?:%[\d.]*[dgf]|\d+(?:\.\d+)?)(?![\w.])"), "write '+25%', not 'x2'"),
]
DECIMAL_PATTERNS = [
    (re.compile(r"(?<![\w.])\d+\.\d+(?![\d.]*\.)"), "round to a whole number"),
    (re.compile(r"%[-+ #0]*\d*\.\d+[fgeE]"), "round to a whole number (use %d)"),
    (re.compile(r"%[-+ #0]*\d*[fF]"), "round to a whole number (use %d)"),
]
RAW_ID_PATTERNS = [
    (re.compile(r"rbxasset", re.I), "never show an asset id"),
    (re.compile(r"\b[A-Z]{2,}-\d+\b"), "never show a task id"),
    (re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b"), "snake_case code word"),
    (re.compile(r"\b\d{7,}\b"), "long number: round or shorten"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}\b", re.I), "never show an id"),
    (re.compile(r"\bdocs/|\.(?:luau|lua|json|png|md|rbxl)\b"), "never show a file name"),
    (re.compile(r"\b[A-Z][a-z]+[A-Z][a-z]+[A-Za-z]*\b"), "CamelCase code name"),
]

RULES = ["TIME_NOISE", "MULTIPLIER", "DECIMAL", "RAW_ID", "SHOUTING", "LONG_TEXT", "JARGON", "TECH_PUNCT"]

FORMAT_SPEC = re.compile(r"%(?:%|[-+#0]*\d*(?:\.\d+)?[a-zA-Z])")
RICH_TAG = re.compile(r"</?(?:b|i|u|s|font|br|stroke|uppercase|smallcaps|mark)\b[^>]*>", re.I)


# ---------------------------------------------------------------------------------------------
# Luau string scanner
# ---------------------------------------------------------------------------------------------

class Lit:
    __slots__ = ("start", "end", "value", "line")

    def __init__(self, start, end, value, line):
        self.start, self.end, self.value, self.line = start, end, value, line


_ESC = {"n": "\n", "t": "\t", "r": "", "\\": "\\", '"': '"', "'": "'", "`": "`", "a": "", "b": "", "f": "", "v": "", "0": ""}


def scan(src: str):
    """Return (literals, masked). masked = the source with comments blanked and string bodies replaced by 'x'."""
    lits: list[Lit] = []
    out = list(src)
    n = len(src)
    i = 0
    line = 1

    def blank(a, b, ch=" "):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = ch

    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c == "-" and src.startswith("--", i):
            m = re.match(r"--\[(=*)\[", src[i:i + 40])
            if m:
                close = "]" + m.group(1) + "]"
                j = src.find(close, i + len(m.group(0)))
                j = n if j < 0 else j + len(close)
                line += src.count("\n", i, j)
                blank(i, j)
                i = j
            else:
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                i = j
            continue
        if c == "[":
            m = re.match(r"\[(=*)\[", src[i:i + 40])
            if m:
                close = "]" + m.group(1) + "]"
                body_start = i + len(m.group(0))
                j = src.find(close, body_start)
                j = n if j < 0 else j
                value = src[body_start:j].lstrip("\n")
                end = min(n, j + len(close))
                lits.append(Lit(i, end, value, line))
                line += src.count("\n", i, end)
                blank(body_start, j, "x")
                i = end
                continue
        if c in "\"'`":
            q = c
            j = i + 1
            buf = []
            depth = 0
            while j < n:
                d = src[j]
                if q == "`" and d == "{" and depth == 0:
                    depth = 1
                    buf.append("%s")
                    j += 1
                    continue
                if depth:
                    if d == "{":
                        depth += 1
                    elif d == "}":
                        depth -= 1
                    j += 1
                    continue
                if d == "\\" and j + 1 < n:
                    e = src[j + 1]
                    if e == "u" and src.startswith("{", j + 2):
                        k = src.find("}", j + 2)
                        try:
                            buf.append(chr(int(src[j + 3:k], 16)))
                        except ValueError:
                            pass
                        j = k + 1
                        continue
                    if e == "x":
                        try:
                            buf.append(chr(int(src[j + 2:j + 4], 16)))
                        except ValueError:
                            pass
                        j += 4
                        continue
                    if e.isdigit() and e != "0":
                        m = re.match(r"\d{1,3}", src[j + 1:j + 4])
                        buf.append(chr(min(255, int(m.group(0)))))
                        j += 1 + len(m.group(0))
                        continue
                    if e == "z":
                        j += 2
                        while j < n and src[j] in " \t\r\n":
                            j += 1
                        continue
                    buf.append("\n" if e == "\n" else _ESC.get(e, e))
                    j += 2
                    continue
                if d == q or d == "\n" and q != "`":
                    break
                buf.append(d)
                j += 1
            end = min(n, j + 1)
            lits.append(Lit(i, end, "".join(buf), line))
            line += src.count("\n", i, end)
            blank(i + 1, max(i + 1, end - 1), "x")
            i = end
            continue
        i += 1
    return lits, "".join(out)


# ---------------------------------------------------------------------------------------------
# Finding player-visible strings
# ---------------------------------------------------------------------------------------------

BINDER = re.compile(r"(?P<call>[A-Za-z_][\w.:]*)\s*\(|(?<![=~<>!])(?P<key>[A-Za-z_]\w*)\s*=(?![=])")
STATEMENT_WORDS = re.compile(r"\b(?:end|do|local|function|while|for|repeat|until)\b")
BRANCH_WORDS = re.compile(r"\b(?:then|else|elseif)\b")
IF_WORD = re.compile(r"\bif\b")


def _slot_for_key(key: str):
    k = key.lower()
    if key in NOT_TEXT_KEYS:
        return None
    if k in TEXT_KEY_SLOTS:
        return TEXT_KEY_SLOTS[k]
    for suf, slot in TEXT_KEY_SUFFIXES.items():
        if k.endswith(suf) and len(k) > len(suf):
            return slot
    return None


def _slot_for_call(call: str):
    last = call.replace(":", ".").split(".")[-1]
    if call in NON_TEXT_CALLS or last in NON_TEXT_CALLS:
        return None
    low = last.lower()
    for frag, slot in TEXT_CALL_SLOTS:
        if frag in low:
            return slot
    return None


def find_binder(masked: str, idx: int):
    """Look back from a string at `idx` for what it is given to. Returns ('key'|'call', name) or None."""
    ctx = masked[max(0, idx - 400):idx]
    # a comparison like  kind == "egg"  is never display text
    if re.search(r"(?:==|~=)\s*$", ctx):
        return ("compare", "")
    cands = list(BINDER.finditer(ctx))
    for m in reversed(cands):
        name = m.group("call") or m.group("key")
        kind = "call" if m.group("call") else "key"
        if kind == "call" and (name in TRANSPARENT_CALLS or name.split(".")[-1] in TRANSPARENT_CALLS):
            continue
        seg = ctx[m.end():]
        if STATEMENT_WORDS.search(seg):
            return None
        if BRANCH_WORDS.search(seg) and not IF_WORD.search(seg):
            return None                         # we left the statement:  if x then ... else <here>
        floor = 1 if kind == "call" else 0     # a call's "(" is already open; a key has no bracket
        depth = floor
        for ch in seg:
            if ch in "({":
                depth += 1
            elif ch in ")}":
                depth -= 1
                if depth < floor:
                    break
        if depth < floor:
            continue                            # that call/table already closed before our string
        if kind == "key" and _slot_for_key(name) is None:
            # multiple assignment:  heading.Text, header.BackgroundColor3 = "Shop", color
            lhs = re.search(r"((?:[\w.]+\s*,\s*)*)[\w.]*$", ctx[:m.start()])
            first = (lhs.group(1).split(",")[0].strip().split(".")[-1]) if lhs and lhs.group(1) else ""
            if first and _slot_for_key(first) is not None:
                top = 0
                for ch in seg:
                    if ch in "({":
                        top += 1
                    elif ch in ")}":
                        top -= 1
                    elif ch == "," and top == 0:
                        break
                else:
                    return ("key", first)
        return (kind, name)
    return None


def strip_format(s: str, repl: str = "00") -> str:
    s = RICH_TAG.sub("", s)
    return FORMAT_SPEC.sub(lambda m: "%" if m.group(0) == "%%" else repl, s)


def looks_like_prose(value: str, strong: bool) -> bool:
    s = strip_format(value, "0").strip()
    if not re.search(r"[A-Za-z]", s):
        return False
    if re.match(r"^(?:rbxasset|https?:)", s):
        return False
    if " " in s or "\n" in s:
        return True
    if not strong:
        return False
    if "_" in s or "/" in s or "." in s.strip(".!?") or ":" in s.strip(":"):
        return bool(re.search(r"[.!?]$", s)) and "_" not in s
    if re.fullmatch(r"[A-Z][a-z]+[!?.]*|[A-Z]{2,}[!?.]*", s):
        return True
    return False


def classify(lit: Lit, masked: str, is_copy_file: bool):
    """Return slot name if this literal is player-visible text, else None."""
    value = lit.value
    b = find_binder(masked, lit.start)
    if b and b[0] == "compare":
        return None
    slot = None
    strong = False
    weak = False
    if b:
        kind, name = b
        if kind == "key":
            slot = _slot_for_key(name)
            if slot is None and re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", name):
                slot = "toast"          # snake_case error/reason code -> message table
            if name == "name" and slot == "title" and " " not in value.strip():
                slot = None             # data name like "T1": only multi-word names are copy
        else:
            slot = _slot_for_call(name)
            # first-argument-only calls like  makeLabel(parent, "x")  keep the slot; ids in call args are filtered by prose
            if name in NON_TEXT_CALLS or name.split(".")[-1] in NON_TEXT_CALLS:
                return None
        strong = slot is not None
        if slot is None and b[0] == "key" and not is_copy_file:
            if name in NOT_TEXT_KEYS:
                return None
            weak = True                 # P.HomeToast = "Going home...": sentence-like text only
        if slot is None and b[0] == "call" and name == "table.insert":
            weak = True
        elif slot is None and b[0] == "call" and not is_copy_file:
            return None
    elif not is_copy_file:
        weak = True
    if weak:
        # no clear owner (return "Slots are full", table.insert(lines, "..."), a bare list entry):
        # accept only sentence-like text: starts with a capital letter and has a space
        if not (value[:1].isupper() and " " in value.strip()):
            return None
    if slot is None:
        slot = "default"
        strong = False
    if not looks_like_prose(value, strong):
        return None
    return slot


def collapse(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------------------------

def _first(patterns, text):
    for rx, hint in patterns:
        m = rx.search(text)
        if m:
            return m.group(0), hint
    return None


def check_text(value: str, slot: str):
    """Return a list of (rule, plain detail) for one visible string."""
    hits = []
    raw = RICH_TAG.sub("", value)
    base = raw.replace("%%", "\x00")      # keep literal percent signs away from format-code patterns

    r = _first(TIME_NOISE_PATTERNS, base)
    if r:
        hits.append(("TIME_NOISE", f"'{r[0]}': {r[1]}"))
    r = _first(MULTIPLIER_PATTERNS, base)
    if r:
        hits.append(("MULTIPLIER", f"'{r[0]}': {r[1]}"))
    r = _first(DECIMAL_PATTERNS, base)
    if r:
        hits.append(("DECIMAL", f"'{r[0]}': {r[1]}"))
    r = _first(RAW_ID_PATTERNS, FORMAT_SPEC.sub(" ", base))
    if r:
        hits.append(("RAW_ID", f"'{r[0]}': {r[1]}"))

    plain = strip_format(value)
    letters = re.findall(r"[A-Za-z]", plain)
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", plain)
    upper_words = [w for w in words if len(w) >= 3 and w.isupper()]
    if len(letters) >= CAPS_MIN_LETTERS and "".join(letters).isupper():
        phrase_words = re.findall(r"[A-Za-z]+", plain)
        if not all(w in CAPS_OK_WORDS or len(w) <= 2 for w in phrase_words):
            if len(plain) > CAPS_MAX_CHARS or len(phrase_words) > CAPS_MAX_WORDS:
                hits.append(("SHOUTING", f"all capitals: '{collapse(plain)[:40]}'"))
    elif len(upper_words) >= 2 and not all(w in CAPS_OK_WORDS for w in upper_words):
        hits.append(("SHOUTING", f"capital words: {', '.join(upper_words[:3])}"))
    if re.search(r"!{2,}|\?{2,}", plain):
        hits.append(("SHOUTING", "repeated ! or ?"))

    max_chars, max_words, max_sent = LIMITS.get(slot, LIMITS["default"])
    flat = collapse(plain)
    n_words = len(re.findall(r"\S+", flat))
    n_sent = len(re.findall(r"[.!?]+(?=\s+[A-Z0-9])", flat)) + 1
    problems = []
    if len(flat) > max_chars:
        problems.append(f"{len(flat)} characters (slot '{slot}' allows {max_chars})")
    if n_words > max_words:
        problems.append(f"{n_words} words (slot '{slot}' allows {max_words})")
    if n_sent > max_sent:
        problems.append(f"{n_sent} sentences (slot '{slot}' allows {max_sent})")
    if problems:
        hits.append(("LONG_TEXT", "; ".join(problems)))

    low = " " + re.sub(r"[^a-z\-]+", " ", plain.lower()) + " "
    found = [w for w in JARGON if f" {w} " in low]
    if found:
        hits.append(("JARGON", "; ".join(f"'{w}' ({JARGON[w]})" for w in found[:3])))

    pt = FORMAT_SPEC.sub("", raw)
    bad = sorted({ch for ch in pt if ch in TECH_PUNCT_CHARS})
    bad_words = [w for w in TECH_PUNCT_WORDS if w in pt]
    if bad or bad_words:
        hits.append(("TECH_PUNCT", "code-like marks: " + " ".join(bad + bad_words)))
    return hits


# ---------------------------------------------------------------------------------------------
# Files, allowlist, baseline
# ---------------------------------------------------------------------------------------------

class Violation:
    __slots__ = ("file", "line", "rule", "text", "detail", "slot")

    def __init__(self, file, line, rule, text, detail, slot):
        self.file, self.line, self.rule, self.text, self.detail, self.slot = file, line, rule, collapse(text), detail, slot

    def key(self):
        return f"{self.file}|{self.rule}|{self.text[:140]}"

    def show(self):
        return f"{self.file}:{self.line}: {self.rule} [{self.slot}] \"{self.text[:90]}\" - {self.detail}"


def lint_source(src: str, rel: str):
    is_copy = bool(COPY_FILE_PATTERN.search(rel))
    lits, masked = scan(src)
    lines = src.split("\n")
    out = []
    for lit in lits:
        slot = classify(lit, masked, is_copy)
        if slot is None:
            continue
        ln = lines[lit.line - 1] if lit.line - 1 < len(lines) else ""
        # a literal can span lines; the marker may sit on the line where it ends
        end_line = lit.line + src.count("\n", lit.start, lit.end)
        end_ln = lines[end_line - 1] if end_line - 1 < len(lines) else ln
        if "kidtext-ok" in ln or "kidtext-ok" in end_ln:
            continue
        for rule, detail in check_text(lit.value, slot):
            out.append(Violation(rel, lit.line, rule, lit.value, detail, slot))
    return out


def iter_files(paths):
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        if base.is_file():
            yield base
        elif base.is_dir():
            yield from sorted(base.rglob("*.luau"))
            yield from sorted(base.rglob("*.lua"))


def rel_of(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_allow(path=ALLOW_FILE):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    for i, e in enumerate(entries):
        if not str(e.get("reason", "")).strip():
            raise SystemExit(f"allowlist entry {i} ({e.get('file')}, {e.get('rule')}) has no reason")
        if not e.get("file") or not e.get("rule"):
            raise SystemExit(f"allowlist entry {i} needs 'file' and 'rule'")
    return entries


def allowed(v: Violation, entries, used):
    for i, e in enumerate(entries):
        if not fnmatch.fnmatch(v.file, e["file"]):
            continue
        if e["rule"] not in ("*", v.rule):
            continue
        t = e.get("text")
        if t not in (None, "*") and collapse(t) != v.text:
            continue
        used.add(i)
        return True
    return False


def run_lint(paths, entries):
    found = []
    used = set()
    n_files = 0
    for f in iter_files(paths):
        rel = rel_of(f)
        if rel in EXCLUDED_FILES:
            continue
        n_files += 1
        try:
            src = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for v in lint_source(src, rel):
            if not allowed(v, entries, used):
                found.append(v)
    unused = [e for i, e in enumerate(entries) if i not in used]
    return found, n_files, unused


def baseline_counts(violations):
    return Counter(v.key() for v in violations)


def load_baseline(path):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Counter(data.get("counts", {}))


def write_baseline(path, violations):
    counts = baseline_counts(violations)
    data = {
        "about": "Kid-text problems that existed when this file was written (BD-655, docs/162). CI fails only on problems NOT listed here. "
                 "Fix a text, then re-run: python tools/lint_kid_text.py --write-baseline. Never add new problems to it by hand.",
        "total": sum(counts.values()),
        "counts": dict(sorted(counts.items())),
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def new_violations(violations, base: Counter):
    seen = Counter()
    new = []
    for v in violations:
        k = v.key()
        seen[k] += 1
        if seen[k] > base.get(k, 0):
            new.append(v)
    return new


# ---------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------

def make_report(violations, n_files, top, markdown=False):
    by_file = defaultdict(Counter)
    for v in violations:
        by_file[v.file][v.rule] += 1
    ranked = sorted(by_file.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))[:top]
    by_rule = Counter(v.rule for v in violations)
    texts = defaultdict(list)
    for v in violations:
        texts[(v.file, v.text, v.line)].append(v)
    worst = sorted(texts.items(), key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][2]))[:top]
    L = []
    h = (lambda s: f"## {s}") if markdown else (lambda s: s)
    L.append(f"Kid-text report: {len(violations)} problems in {len(by_file)} of {n_files} files scanned.")
    L.append("")
    L.append(h("By rule"))
    L.extend(f"- {r}: {c}" if markdown else f"  {r:<11} {c}" for r, c in by_rule.most_common())
    L.append("")
    L.append(h(f"Top {top} files"))
    if markdown:
        L.append("| # | File | Problems | Mix |")
        L.append("| ---: | --- | ---: | --- |")
    for i, (f, c) in enumerate(ranked, 1):
        mix = ", ".join(f"{r} {n}" for r, n in c.most_common())
        L.append(f"| {i} | `{f}` | {sum(c.values())} | {mix} |" if markdown else f"{i:>3}. {f}  {sum(c.values())}  ({mix})")
    L.append("")
    L.append(h(f"Top {top} worst single texts (most rules broken at once)"))
    for (f, t, ln), vs in worst:
        rules = ", ".join(sorted({x.rule for x in vs}))
        L.append(f"- `{f}:{ln}` \"{t[:80]}\" - {rules}" if markdown else f"  {f}:{ln}  \"{t[:80]}\"  [{rules}]")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------
# Self test
# ---------------------------------------------------------------------------------------------

SELFTEST_CASES = [
    ('lbl.Text = "5m 0s left"', {"TIME_NOISE"}),
    ('lbl.Text = string.format("%dm %ds", m, s)', {"TIME_NOISE"}),
    ('lbl.Text = "Speed 1.25x"', {"MULTIPLIER", "DECIMAL"}),
    ('notify("Back in 40 s")', set()),
    ('notify("Speed +20%")', set()),
    ('lbl.Text = "EAT ALL THE FOOD NOW"', {"SHOUTING"}),
    ('lbl.Text = "HOME"', set()),
    ('notify("Your profile session is syncing with the server")', {"JARGON"}),
    ('lbl.Text = "Open the shop {now}"', {"TECH_PUNCT"}),
    ('Instance.new("TextLabel").Name = "DinoVisual"', set()),
    ('if kind == "egg" then x = 1 end', set()),
    ('local t = {title = "Go home?", body = "Your run ends and your eggs are saved."}', set()),
    ('notify("Error code save_failed")', {"RAW_ID"}),
]


def selftest():
    bad = 0
    for src, want in SELFTEST_CASES:
        got = {v.rule for v in lint_source(src + "\n", "src/client/Example.luau")}
        if got != want:
            bad += 1
            print(f"selftest FAIL: {src!r} wanted {sorted(want)} got {sorted(got)}")
    print("selftest ok" if not bad else f"selftest: {bad} failed")
    return 1 if bad else 0


def print_rules():
    print("Rules:", ", ".join(RULES))
    print("\nSlot limits (characters, words, sentences):")
    for k, v in LIMITS.items():
        print(f"  {k:<8} {v}")
    print(f"\nShouting: > {CAPS_MAX_CHARS} characters or > {CAPS_MAX_WORDS} words in all capitals (4+ letters). Short words allowed: {', '.join(sorted(CAPS_OK_WORDS))}")
    print(f"\nJargon words ({len(JARGON)}): {', '.join(sorted(JARGON))}")
    print(f"\nFiles skipped (players never see them): {len(EXCLUDED_FILES)}")
    for k, v in EXCLUDED_FILES.items():
        print(f"  {k}: {v}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", help="files or folders (default: src/client src/shared)")
    ap.add_argument("--baseline", nargs="?", const=str(BASELINE_FILE), metavar="FILE", help="CI mode: fail only on problems not in the baseline file")
    ap.add_argument("--write-baseline", nargs="?", const=str(BASELINE_FILE), metavar="FILE", help="record today's problems as the baseline")
    ap.add_argument("--allow", default=str(ALLOW_FILE), help="allowlist json (default tools/lint_kid_text_allow.json)")
    ap.add_argument("--report", action="store_true", help="list worst files and texts, exit 0")
    ap.add_argument("--top", type=int, default=20, help="how many rows in the report")
    ap.add_argument("--markdown", action="store_true", help="report as markdown")
    ap.add_argument("--rules", action="store_true", help="print the rule and limit tables")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="only print the summary line (and new problems in --baseline mode)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.selftest:
        return selftest()
    if args.rules:
        print_rules()
        return 0

    entries = load_allow(Path(args.allow))
    paths = args.paths or DEFAULT_PATHS
    violations, n_files, unused = run_lint(paths, entries)

    if args.write_baseline:
        write_baseline(Path(args.write_baseline), violations)
        print(f"Baseline written: {len(violations)} problems from {n_files} files -> {rel_of(Path(args.write_baseline))}")
        return 0

    if args.report:
        print(make_report(violations, n_files, args.top, args.markdown), end="")
        if unused:
            print(f"\n{len(unused)} allowlist entries matched nothing (clean them up).")
        return 0

    if args.baseline:
        base = load_baseline(Path(args.baseline))
        if base is None:
            print(f"No baseline file at {args.baseline}. Run with --write-baseline first.")
            return 2
        new = new_violations(violations, base)
        now = baseline_counts(violations)
        fixed = sum((base - now).values())
        print(f"Kid text: {len(violations)} old problems ({fixed} fixed since the baseline), {len(new)} NEW, {n_files} files scanned.")
        for v in new:
            print("NEW  " + v.show())
        if new:
            print("\nFix the new text (short, plain words; see docs/72 and docs/162), or add an entry with a reason to tools/lint_kid_text_allow.json,\n"
                  "or add `-- kidtext-ok: reason` to the end of the line.")
            return 1
        return 0

    if not args.quiet:
        for v in violations:
            print(v.show())
    print(f"Kid text: {len(violations)} problems in {n_files} files scanned.")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
