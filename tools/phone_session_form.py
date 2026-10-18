"""BD-1004: turn the owner's filled-in phone form into an evidence file with traffic lights (docs/175).

    python tools/phone_session_form.py --template > phone-form.txt          # the blank form (same text as docs/175 section 6)
    python tools/phone_session_form.py phone-form.txt                       # writes docs/evidence/<date>-phone-session/README.md
    python tools/phone_session_form.py phone-form.txt --out-dir DIR          # another folder
    python tools/phone_session_form.py phone-form.txt --qa-log phone.log    # also read [BD-QA] lines of a measurement build (docs/127)
    python tools/phone_session_form.py phone-form.txt --stdout              # print, write nothing

The form is plain `key: value` lines (a line starting with # is a hint and is ignored). Nothing on the phone needs developer tools:
every number is read off the screen (Roblox "Performance Stats", the chat command /console, the battery bar). Numbers may be
written with units ("28 fps", "1,050 MB", "35%"). A blank value means "not read" and shows as GREY, never as a pass.

Offline: reads the form (and optionally a log) only; reads tools/qa/phone_budgets.json when present and falls back to the same
numbers when it is not. Changes no game code and no flag. Every limit is PROVISIONAL until the real phone run (BD-085).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET_FILE = ROOT / "tools" / "qa" / "phone_budgets.json"

GREEN, YELLOW, RED, GREY = "GREEN", "YELLOW", "RED", "GREY"
ORDER = {RED: 0, YELLOW: 1, GREY: 2, GREEN: 3}

# Same numbers as tools/qa/phone_budgets.json "phone" (used when that file is not there, for example in a copy of this tool).
DEFAULT_BUDGETS = {"parts": 3000, "memMb": 1200}

# ---------------------------------------------------------------------------------------------------------------------------------
# THE THRESHOLD TABLE. One place. Every number is PROVISIONAL (docs/175 section 8); the owner or the lead may change any row.
#   kind "min"   : higher is better. GREEN when value >= green, YELLOW when value >= yellow, else RED.
#   kind "max"   : lower is better.  GREEN when value <= green, YELLOW when value <= yellow, else RED.
#   kind "band"  : a word. GREEN / YELLOW / RED are lists of accepted words.
# `budget` links a row to phone_budgets.json: GREEN = share * budget, YELLOW = budget.
# ---------------------------------------------------------------------------------------------------------------------------------
THRESHOLDS = {
    "fps_spawn": {"label": "Speed at the start (frames per second)", "kind": "min", "green": 30, "yellow": 24,
                  "why": "30 fps is the playable floor (docs/107, docs/146 s7 item 4); 24 is still playable but choppy"},
    "fps_food": {"label": "Speed while eating food", "kind": "min", "green": 30, "yellow": 24, "why": "same floor"},
    "fps_hatch": {"label": "Speed while eggs hatch", "kind": "min", "green": 30, "yellow": 24, "why": "same floor"},
    "fps_cave": {"label": "Speed in the cave", "kind": "min", "green": 30, "yellow": 24, "why": "same floor (docs/146 risk 3, BD-293)"},
    "fps_weather": {"label": "Speed in a weather event", "kind": "min", "green": 30, "yellow": 24, "why": "same floor (docs/146 risk 5)"},
    "memory_mb": {"label": "Most memory seen (MB)", "kind": "max", "budget": "memMb", "share": 0.75,
                  "why": "docs/107 s1: 1,200 MB on a 3 GB phone, crashes start near 1,500; GREEN up to 75% of that"},
    "memory_growth_mb": {"label": "Memory growth from the start to the end (MB)", "kind": "max", "green": 150, "yellow": 300,
                         "why": "PROPOSAL: a leak check over 10 minutes (docs/127 step 12)"},
    "join_seconds": {"label": "Time from Play to moving (seconds)", "kind": "max", "green": 60, "yellow": 120,
                     "why": "PROPOSAL: docs/146 risk 2 (8,600 parts replicate at join); first run in the friends report is 90 s"},
    "ping_ms": {"label": "Ping (ms)", "kind": "max", "green": 150, "yellow": 250, "why": "250 ms is the phone_report.py limit (PROVISIONAL)"},
    "parts_max": {"label": "Parts in the world (measurement build only)", "kind": "max", "budget": "parts", "share": 1.0,
                  "why": "docs/107 s1 and tools/qa/phone_budgets.json: 3,000 (the overlay counts the whole workspace, a strict reading)"},
    "freezes": {"label": "Freezes (the picture stopped for 2 s or more)", "kind": "max", "green": 0, "yellow": 2,
                "why": "PROPOSAL: none is fine, one or two is worth a look, more is a problem"},
    "crashed": {"label": "Game closed by itself", "kind": "band", "green": ["no"], "yellow": [], "red": ["yes"],
                "why": "a crash is always RED (docs/55 s3 Android checklist)"},
    "battery_drop_pct": {"label": "Battery used (percent points, about 10 minutes)", "kind": "max", "green": 5, "yellow": 10,
                         "why": "PROPOSAL: more than 10 points in 10 minutes is a hot, hungry game"},
    "temperature_feel": {"label": "How warm the phone felt", "kind": "band", "green": ["cool", "normal"], "yellow": ["warm"],
                         "red": ["hot"], "why": "docs/55 s3: note heat after the session"},
    "taps_ok": {"label": "Every button easy to tap and not covered", "kind": "band", "green": ["yes"], "yellow": ["some"],
                "red": ["no"], "why": "docs/127 s4 touch checklist (44 px buttons), BD-994"},
    "words_ok": {"label": "All words readable and not cut off", "kind": "band", "green": ["yes"], "yellow": ["some"],
                 "red": ["no"], "why": "docs/114 s8.2 (text at least 14 px), BD-994"},
}

# What the lead does next for a YELLOW or RED light. Plain text; the full table with the reasons is docs/175 section 7.
# NO game code or flag is changed by this tool or by this table: these are things to DECIDE (and for some a new kanban row).
ACTIONS = {
    "fps_spawn": "Turn the phone food radius down (FoodRadiusFactor is 1.25 for EVERY device class today, so a phone-only value needs a new row), "
                 "then the phone radius 190 -> 160 (docs/146 s1: -23% triangles). Plan BD-498 (food pooling) and the BD-502 streaming flip. Row BD-085.",
    "fps_food": "Same levers as the start: FoodRadiusFactor down, phone radius 160, BD-498 food pooling; check colliders (BD-496) and 12 players later. Row BD-322.",
    "fps_hatch": "Try Settings > Effects Lite or Off and note the gain; if Lite fixes it, a phone default of Lite is a decision. Pause weather during the reveal (docs/146 risk 5 b). Row BD-322.",
    "fps_cave": "Check the cave guards worked (12 lights, 4 beams, BD-495); then fewer lights or 0 shadow lights (docs/146 risk 3). Do not flip anything: BD-293 stays open. Row BD-293.",
    "fps_weather": "Weather is already a quarter of the drops on a phone (density 0.25, BD-497). If still low, lower it again or pause it in menus (docs/146 risk 5). Row BD-322.",
    "memory_mb": "Texture memory first (docs/146 risk 1): 512 px dino textures for phones, fewer species in view, shop tabs built on open. Then the BD-502 streaming flip (docs/147). Row BD-322.",
    "memory_growth_mb": "A leak. Repeat with a note of what was open (hatch, shops, Fusion). Look for textures that are never freed (docs/146 risk 1, docs/107 s5 item 3). Row BD-322.",
    "join_seconds": "Too many parts at join (docs/146 risk 2): BD-498 food pooling (join 7,061 -> 4,383) and the BD-502 streaming flip (about -50%). Check the load gate (BD-210).",
    "ping_ms": "Probably the network, not the game: repeat on another Wi-Fi or on mobile data. If it stays high only in the game, read docs/107 s4 (join replication).",
    "parts_max": "Over the 3,000 parts rule: BD-496 (colliders) is built; BD-498 food pooling and the BD-502 streaming flip are the next levers (docs/146 risk 2).",
    "freezes": "Note WHEN each freeze happened (hatch, shop, weather). A freeze at hatch = effects (BD-322); at the start = loading and memory (BD-502). Row BD-085.",
    "crashed": "A crash at JOIN: check memory first (docs/146 risk 1) and the BD-502 streaming experiment (docs/147; default streaming alone is worse, it needs the three BD-506 fixes). "
               "A crash LATER: read the memory growth line. Either way a P0 row, and the friends list stays desktop only (docs/125).",
    "battery_drop_pct": "Heat and battery are a cost of frame rate and particles: cap the frame rate or default phones to Effects Lite (a decision, new row). Row BD-322.",
    "temperature_feel": "Same as the battery: Effects Lite as the phone default, shorter test, a new row. Row BD-322.",
    "taps_ok": "Open the buttons list in docs/127 s4 and BD-994 (HUD overlap at 640 x 360); send the screenshot. A button hidden behind another is a P1.",
    "words_ok": "Send the screenshot to BD-994 and the kid-text list (docs/72); words must be at least 14 px.",
}

# Frame-speed rows: spot key -> (fps key in the form, frame-time key in the form).
SPOTS = (("spawn", "Start"), ("food", "Food"), ("hatch", "Hatch"), ("cave", "Cave"), ("weather", "Weather"))
SCREENSHOTS = (
    ("screenshot_1", "1. The start, with Performance Stats on"),
    ("screenshot_2", "2. Eating food in the field, with Performance Stats on"),
    ("screenshot_3", "3. The egg hatch, with Performance Stats on"),
    ("screenshot_4", "4. The Memory tab of the game console (type /console in chat)"),
)
FORM_KEYS = (
    "date", "tester", "device_model", "android_version", "ram_gb", "roblox_app_version", "build_label", "graphics_quality", "network",
    "battery_start_pct", "battery_end_pct", "minutes_played", "temperature_feel",
    "join_seconds", "ping_ms",
    "spawn_fps", "spawn_frame_ms", "food_fps", "food_frame_ms", "hatch_fps", "hatch_frame_ms",
    "cave_fps", "cave_frame_ms", "weather_fps", "weather_frame_ms",
    "memory_mb_spawn", "memory_mb_food", "memory_mb_hatch", "memory_mb_end",
    "freezes", "freeze_notes", "crashed", "crash_when",
    "taps_ok", "words_ok", "weather_seen", "opened_shop", "opened_fusion", "opened_objectives", "opened_dinos",
    "screenshot_1", "screenshot_2", "screenshot_3", "screenshot_4", "notes",
)

TEMPLATE = """\
# Be Dino! phone session form (docs/175). Fill in after the 10-minute script. Lines starting with # are hints.
# Write numbers only (units are fine). If you could not read something, leave it EMPTY. Never guess.
# Save as phone-form.txt and send it with the 4 screenshots.

# --- the phone ---
date:
tester:
device_model:
android_version:
# How much memory the phone has, in GB (Settings > About phone). Leave empty if you cannot find it.
ram_gb:
roblox_app_version:
# The small blue text at the top of the game screen that starts with BUILD.
build_label:
# Roblox Settings > Graphics: Automatic, or a number.
graphics_quality:
# Wi-Fi or mobile data.
network:
battery_start_pct:
battery_end_pct:
minutes_played:
# cool, warm or hot (how the back of the phone felt at the end).
temperature_feel:

# --- speed numbers (switch on Performance Stats first; write the LOWEST number you see for 10 seconds) ---
# Seconds from tapping Play until you can move the dino. Use a stopwatch.
join_seconds:
ping_ms:
# Frames per second at each spot. If your stats show milliseconds instead, use the _frame_ms line (the biggest ms number).
spawn_fps:
spawn_frame_ms:
food_fps:
food_frame_ms:
hatch_fps:
hatch_frame_ms:
cave_fps:
cave_frame_ms:
weather_fps:
weather_frame_ms:
# Memory in MB (Performance Stats memory number, or the Total on the console Memory tab).
memory_mb_spawn:
memory_mb_food:
memory_mb_hatch:
memory_mb_end:

# --- problems ---
# How many times did the picture stop for 2 seconds or more?
freezes:
freeze_notes:
# yes or no. Did the game close by itself, or throw you out?
crashed:
# join, run, hatch, menu, other (only if crashed is yes).
crash_when:
# yes, some or no.
taps_ok:
words_ok:

# --- what you did (yes or no) ---
weather_seen:
opened_shop:
opened_fusion:
opened_objectives:
opened_dinos:

# --- screenshots: write the file name of each one ---
screenshot_1:
screenshot_2:
screenshot_3:
screenshot_4:

# --- anything else, in your own words ---
notes:
"""


# ---------------------------------------------------------------------------------------------------------------------------------
# Reading the form
# ---------------------------------------------------------------------------------------------------------------------------------
def normal_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


def parse_form(text: str):
    """(values, unknown_keys). Hints (# lines) and blank lines are skipped; a later duplicate key wins; keys are forgiving."""
    values: dict[str, str] = {}
    unknown: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = normal_key(key)
        if key not in FORM_KEYS:
            if key and key not in unknown:
                unknown.append(key)
            continue
        values[key] = value.strip()
    return values, unknown


def number(text):
    """First number in the text ('1,050 MB' -> 1050, '35%' -> 35, '28 fps' -> 28); None when there is none."""
    if text is None:
        return None
    found = re.search(r"-?\d[\d,]*(?:\.\d+)?|-?\.\d+", str(text))
    if not found:
        return None
    try:
        return float(found.group(0).replace(",", ""))
    except ValueError:
        return None


def word(text):
    """yes/no/some/cool/warm/hot/normal from free text; None when blank or not understood."""
    t = (text or "").strip().lower()
    if not t:
        return None
    first = re.split(r"[^a-z]+", t)[0]
    table = {"yes": "yes", "y": "yes", "ja": "yes", "true": "yes", "no": "no", "n": "no", "nein": "no", "false": "no", "some": "some",
             "mostly": "some", "partly": "some", "cool": "cool", "cold": "cool", "normal": "normal", "ok": "normal", "warm": "warm",
             "hot": "hot", "very": "hot"}
    return table.get(first)


def load_budgets(path=BUDGET_FILE):
    budgets = dict(DEFAULT_BUDGETS)
    try:
        phone = json.loads(Path(path).read_text(encoding="utf-8")).get("phone", {})
    except (OSError, ValueError):
        return budgets
    for key in budgets:
        entry = phone.get(key)
        if isinstance(entry, dict) and isinstance(entry.get("value"), (int, float)):
            budgets[key] = entry["value"]
    return budgets


def derive(values: dict, qa_marks=None):
    """The numbers the checks need, taken from the form (and from [BD-QA] marks when the lead has them)."""
    out: dict = {}
    for spot, _label in SPOTS:
        fps = number(values.get(spot + "_fps"))
        if fps is None:
            ms = number(values.get(spot + "_frame_ms"))
            if ms and ms > 0:
                fps = round(1000.0 / ms, 1)
        out["fps_" + spot] = fps
    mems = [number(values.get(k)) for k in ("memory_mb_spawn", "memory_mb_food", "memory_mb_hatch", "memory_mb_end")]
    seen = [m for m in mems if m is not None]
    out["memory_mb"] = max(seen) if seen else None
    first, last = number(values.get("memory_mb_spawn")), number(values.get("memory_mb_end"))
    out["memory_growth_mb"] = (last - first) if first is not None and last is not None else None
    out["join_seconds"] = number(values.get("join_seconds"))
    out["ping_ms"] = number(values.get("ping_ms"))
    out["freezes"] = number(values.get("freezes"))
    start, end = number(values.get("battery_start_pct")), number(values.get("battery_end_pct"))
    out["battery_drop_pct"] = (start - end) if start is not None and end is not None else None
    out["crashed"] = word(values.get("crashed"))
    out["temperature_feel"] = word(values.get("temperature_feel"))
    out["taps_ok"] = word(values.get("taps_ok"))
    out["words_ok"] = word(values.get("words_ok"))
    out["parts_max"] = None
    if qa_marks:
        parts = [m.get("parts") for m in qa_marks if isinstance(m.get("parts"), (int, float))]
        out["parts_max"] = max(parts) if parts else None
        mem = [m.get("memMb") for m in qa_marks if isinstance(m.get("memMb"), (int, float))]
        if mem and (out["memory_mb"] is None or max(mem) > out["memory_mb"]):
            out["memory_mb"] = max(mem)
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
# The traffic lights
# ---------------------------------------------------------------------------------------------------------------------------------
def limits(key, budgets):
    row = THRESHOLDS[key]
    if "budget" in row:
        budget = budgets[row["budget"]]
        return budget * row.get("share", 1.0), budget
    return row.get("green"), row.get("yellow")


def light_for(key, value, budgets):
    """GREEN / YELLOW / RED / GREY for one value (None = not read)."""
    row = THRESHOLDS[key]
    if value is None:
        return GREY
    if row["kind"] == "band":
        if value in row.get("red", []):
            return RED
        if value in row.get("yellow", []):
            return YELLOW
        if value in row.get("green", []):
            return GREEN
        return GREY
    green, yellow = limits(key, budgets)
    if row["kind"] == "min":
        return GREEN if value >= green else (YELLOW if value >= yellow else RED)
    return GREEN if value <= green else (YELLOW if value <= yellow else RED)


def show(value):
    if value is None:
        return "not read"
    if isinstance(value, str):
        return value
    return "%d" % value if float(value).is_integer() else "%.1f" % value


def limit_text(key, budgets):
    row = THRESHOLDS[key]
    if row["kind"] == "band":
        return "green: %s; yellow: %s; red: %s" % (", ".join(row.get("green", [])) or "-", ", ".join(row.get("yellow", [])) or "-",
                                                  ", ".join(row.get("red", [])) or "-")
    green, yellow = limits(key, budgets)
    g, y = show(green), show(yellow)
    return ("green %s or more, yellow %s or more" if row["kind"] == "min" else "green %s or less, yellow %s or less") % (g, y)


def evaluate(values: dict, budgets=None, qa_marks=None):
    """Everything the evidence file says. Returns a dict (also used by the tests)."""
    budgets = budgets or load_budgets()
    numbers = derive(values, qa_marks)
    checks = []
    for key, row in THRESHOLDS.items():
        value = numbers.get(key)
        light = light_for(key, value, budgets)
        checks.append({"key": key, "label": row["label"], "value": value, "shown": show(value), "light": light,
                       "limit": limit_text(key, budgets), "why": row["why"], "action": ACTIONS.get(key, "")})
    shots = []
    for key, label in SCREENSHOTS:
        name = (values.get(key) or "").strip()
        shots.append({"key": key, "label": label, "file": name, "light": GREEN if name else GREY})
    core = [c for c in checks if c["key"].startswith("fps_") or c["key"] == "memory_mb"]
    read = [c for c in core if c["light"] != GREY]
    lights = [c["light"] for c in checks]
    if RED in lights:
        overall = RED
    elif YELLOW in lights:
        overall = YELLOW
    elif len(read) < 3:
        overall = GREY
    else:
        overall = GREEN
    notes = []
    if len(read) < 3:
        notes.append("Fewer than 3 of the 6 speed and memory readings were filled in: treat the result as a hint, not a result.")
    if numbers.get("crashed") == "yes":
        notes.append("The game crashed: this is a RED result whatever the other numbers say.")
    return {"overall": overall, "checks": checks, "screenshots": shots, "numbers": numbers, "notes": notes,
            "actions": [c for c in checks if c["light"] in (RED, YELLOW) and c["action"]]}


def counts_csv(values: dict) -> str:
    """Two numbers the friends report (tools/playtest_report.py) cannot see by itself: crashes and shop opens (docs/167 s10)."""
    rows = ["name,value,note"]
    crashed = word(values.get("crashed"))
    if crashed is not None:
        rows.append("crashes,%d,phone form %s" % (1 if crashed == "yes" else 0, values.get("date", "")))
    shop = word(values.get("opened_shop"))
    if shop is not None:
        rows.append("shop_opens,%d,phone form" % (1 if shop == "yes" else 0))
    return "\n".join(rows) + "\n"


# ---------------------------------------------------------------------------------------------------------------------------------
# The evidence file
# ---------------------------------------------------------------------------------------------------------------------------------
def render(values: dict, result: dict, unknown=None, qa_used=False) -> str:
    device = ", ".join(x for x in (values.get("device_model"), "Android " + values["android_version"] if values.get("android_version") else "",
                                    values["ram_gb"] + " GB RAM" if values.get("ram_gb") else "") if x) or "device not written down"
    date = values.get("date") or "date not written down"
    lines = [
        "# Phone session %s: %s" % (date, device),
        "",
        "Label: **MEASURED BY HAND on one real phone** (numbers read off the screen by the tester; not a developer-tool measurement). "
        "Made by `tools/phone_session_form.py` from the owner's form ([docs/175](../../175-phone-test-kit.md)). Every limit is PROVISIONAL "
        "until this very run settles it (BD-085, BD-322). No game code or flag was changed.",
        "",
        "## Verdict: %s" % result["overall"],
        "",
    ]
    for note in result["notes"]:
        lines.append("- " + note)
    if result["notes"]:
        lines.append("")
    lines += ["## The phone", "", "| Item | Value |", "| --- | --- |"]
    for key, label in (("tester", "Tester"), ("device_model", "Device"), ("android_version", "Android version"), ("ram_gb", "Memory (GB)"),
                       ("roblox_app_version", "Roblox app version"), ("build_label", "Game build label"),
                       ("graphics_quality", "Graphics quality"), ("network", "Network"), ("battery_start_pct", "Battery at start (%)"),
                       ("battery_end_pct", "Battery at end (%)"), ("minutes_played", "Minutes played")):
        lines.append("| %s | %s |" % (label, values.get(key) or "not written down"))
    lines += ["", "## Traffic lights", "", "GREEN fine, YELLOW look at it, RED fix before friends use a phone, GREY not read.", "",
              "| Check | Reading | Light | Limit (PROVISIONAL) |", "| --- | ---: | --- | --- |"]
    for c in result["checks"]:
        lines.append("| %s | %s | %s | %s |" % (c["label"], c["shown"], c["light"], c["limit"]))
    if qa_used:
        lines += ["", "The parts and some memory readings came from a measurement build (`[BD-QA]` lines, docs/127)."]
    lines += ["", "## What to do next (the lights that are not green)", ""]
    if result["actions"]:
        for c in result["actions"]:
            lines.append("- **%s (%s):** %s" % (c["label"], c["light"], c["action"]))
        lines.append("")
        lines.append("The full table of results and levers is [docs/175 section 7](../../175-phone-test-kit.md). Nothing above is switched on or off by this file: "
                     "the lead decides and writes a LEAD decision in docs/115.")
    else:
        lines.append("Nothing yellow or red.%s" % (" (But not everything was read: see the grey lines.)" if any(c["light"] == GREY for c in result["checks"]) else ""))
    grey = [c["label"] for c in result["checks"] if c["light"] == GREY]
    lines += ["", "## Not read (GREY)", ""]
    lines += ["- " + g for g in grey] if grey else ["- nothing"]
    lines += ["", "## Screenshots", "", "| Screen | File |", "| --- | --- |"]
    for s in result["screenshots"]:
        lines.append("| %s | %s |" % (s["label"], s["file"] or "MISSING"))
    done = [("Opened the shop", "opened_shop"), ("Opened Fusion", "opened_fusion"), ("Opened Objectives", "opened_objectives"),
            ("Opened the Dinos menu", "opened_dinos"), ("Saw a weather event", "weather_seen")]
    lines += ["", "## Script steps the tester says were done", "", "| Step | Done |", "| --- | --- |"]
    for label, key in done:
        lines.append("| %s | %s |" % (label, word(values.get(key)) or "not written down"))
    lines += ["", "## In the tester's words", ""]
    for label, key in (("Freezes", "freeze_notes"), ("Crash", "crash_when"), ("Notes", "notes")):
        if values.get(key):
            lines.append("- %s: %s" % (label, values[key]))
    if not any(values.get(k) for k in ("freeze_notes", "crash_when", "notes")):
        lines.append("- nothing written")
    if unknown:
        lines += ["", "## Lines in the form that were not understood", "", "Check the spelling of: " + ", ".join(unknown)]
    lines += ["", "## Server side", "",
              "The game cannot see a phone's speed. For the server numbers (runs, eggs per run, set-backs, errors, time to first food) "
              "copy the server log and run `python tools/playtest_report.py server.log counts.csv` ([docs/167](../../167-reference-and-playtest-tools.md)). "
              "The tool writes `counts.csv` next to this file with `crashes` and `shop_opens` from this form.", ""]
    return "\n".join(lines)


def output_dir(values: dict, root=ROOT, today=None) -> Path:
    date = (values.get("date") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        date = (today or datetime.date.today()).isoformat()
    return Path(root) / "docs" / "evidence" / ("%s-phone-session" % date)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("form", nargs="?", help="the filled-in form (key: value lines)")
    ap.add_argument("--template", action="store_true", help="print the blank form and exit")
    ap.add_argument("--out-dir", help="write README.md and counts.csv here (default docs/evidence/<date>-phone-session)")
    ap.add_argument("--qa-log", help="optional server log with [BD-QA] lines of a measurement build (docs/127)")
    ap.add_argument("--stdout", action="store_true", help="print the evidence file instead of writing it")
    args = ap.parse_args(argv)
    if args.template:
        sys.stdout.write(TEMPLATE)
        return 0
    if not args.form:
        ap.error("give the filled-in form, or --template")
    values, unknown = parse_form(Path(args.form).read_text(encoding="utf-8", errors="replace"))
    marks = None
    if args.qa_log:
        sys.path.insert(0, str(ROOT / "tools" / "qa"))
        import phone_report  # noqa: E402
        marks, _bad = phone_report.parse(Path(args.qa_log).read_text(encoding="utf-8", errors="replace"))
    result = evaluate(values, qa_marks=marks)
    text = render(values, result, unknown, qa_used=bool(marks))
    if args.stdout:
        sys.stdout.write(text)
        return 0
    out = Path(args.out_dir) if args.out_dir else output_dir(values)
    out.mkdir(parents=True, exist_ok=True)
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "counts.csv").write_text(counts_csv(values), encoding="utf-8")
    print("Verdict %s. Wrote %s" % (result["overall"], out / "README.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
