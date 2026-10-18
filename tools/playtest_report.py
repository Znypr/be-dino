"""BD-648: one-page friends-playtest report with traffic lights, from the game's own numbers (docs/167).

    python tools/playtest_report.py server.log [more.log ...] [counts.csv] [--out report.md] [--json]

Input files (any mix, docs/167 section 7):
  * server logs exported from Studio Output or Creator Hub (lines with "[BD-TELEMETRY] {json}" and "[BD-FEEDBACK] {json}"; all other
    lines are ignored), or
  * JSON lines: one JSON object per line, with an "event" (run_end, session_end, visit, count, script_error, feedback, funnel, meta), or
  * a .csv with the header `name,value[,note]` for numbers the game does not record yet (script_errors, crashes, ...).
It builds on tools/telemetry_report.py and tools/feedback_report.py (same numbers, same 15-eggs-per-5-minutes target) and adds the
checks those two do not have: traffic lights, drop-off, plain-word problems, and a list of what the game still does not record.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import feedback_report  # noqa: E402
import telemetry_report  # noqa: E402

PREFIXES = (telemetry_report.PREFIX, feedback_report.PREFIX)
GREEN, YELLOW, RED, GREY = "GREEN", "YELLOW", "RED", "GREY"
ORDER = {RED: 0, YELLOW: 1, GREY: 2, GREEN: 3}
TARGET_EGGS = telemetry_report.TARGET_EGGS            # about 15 run eggs in a normal 5-minute run (docs/119)
TARGET_SECONDS = telemetry_report.TARGET_SECONDS

# PROVISIONAL limits. One place, so the owner can overrule a limit without touching the checks (docs/167 section 9).
LIMITS = {
    "eggs_ratio_green": (0.8, 1.25), "eggs_ratio_yellow": (0.5, 2.0),   # eggs per 5 min divided by 15
    "run_minutes_green": (3.0, 8.0), "run_minutes_yellow": (1.5, 12.0),  # owner vision: runs of about 5 minutes
    "runs_per_session_green": 2.0, "runs_per_session_yellow": 1.0,
    "no_run_share_green": 0.2, "no_run_share_yellow": 0.4,                # sessions that never finished a run
    "disconnect_share_green": 0.15, "disconnect_share_yellow": 0.3,       # run ended by leaving the game
    "hub_share_green": 0.5, "hub_share_yellow": 0.7,                       # time in the cave instead of in a run
    "rejects_per_session_green": 0.5, "rejects_per_session_yellow": 2.0,
    "rate_limited_per_session_green": 1.0, "rate_limited_per_session_yellow": 5.0,
    "first_food_s_green": 60, "first_food_s_yellow": 120,                  # median seconds from joining to the first food (BD-653)
    "first_run_s_green": 90, "first_run_s_yellow": 180,                     # median seconds from joining to the start of the first run
    "script_errors_green": 0, "script_errors_yellow": 3,
    "fun_green": 2.4, "fun_yellow": 1.8,                                   # 1 sad, 2 ok, 3 happy
    "level_green": (1.7, 2.3), "level_yellow": (1.4, 2.6),                 # 2 = just right
    "min_feedback": 3, "min_sessions": 4,
    "eggs_per_500_green": (9.0, 18.0), "eggs_per_500_yellow": (6.0, 30.0),
}

# What the game does not record on its own: name -> (plain words, kanban row). A `count` line (or CSV row) fills the number by hand.
# BD-649 to BD-653 added server counters (docs/167 section 5): a log with a `visit` line comes from a game that counts
# GAME_COUNTED itself, so a missing count line there means zero. Crashes, shop opens and the hand funnel stay manual.
GAPS = {
    "movement_rejects": ("Movement rejects (the anti-cheat set a player back)", "BD-649"),
    "rate_limited": ("Rate limited (the server said \"too fast\" to a button)", "BD-650"),
    "script_errors": ("Script errors on the server", "BD-651"),
    "crashes": ("Crashes (players kicked or the app closed): read the Creator Hub list", "BD-651"),
    "shop_opens": ("Shop opened (no server event exists; purchases are counted instead)", "BD-652"),
    "shop_purchases": ("Shop things bought", "BD-652"),
    "hatches": ("Eggs hatched by players", "BD-652"),
    "fusions": ("Fusions made", "BD-652"),
    "funnel": ("Steps before the first run (first food, first egg, first hatch)", "BD-653"),
}
GAME_COUNTED = ("movement_rejects", "rate_limited", "script_errors", "shop_purchases", "hatches", "fusions")
COUNT_NAMES = tuple(n for n in GAPS if n != "funnel")
STEPS = (("first_run_s", "Started a run"), ("first_food_s", "Ate food"), ("first_egg_s", "Earned an egg"),
         ("first_hatch_s", "Hatched an egg"), ("first_shop_s", "Bought in a shop"))
MAX_ERROR_TEXTS = 50


def current_rate(root=ROOT):
    """FoodCatchRate as (eggs, food) read from src/shared/Config.luau, else the documented 12/500 (docs/119)."""
    try:
        text = (Path(root) / "src/shared/Config.luau").read_text(encoding="utf-8")
        found = re.search(r"^\s*FoodCatchRate\s*=\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text, re.M)
        if found:
            return float(found.group(1)), float(found.group(2))
    except OSError:
        pass
    return 12.0, 500.0


# ----------------------------------------------------------------------------------------------------- reading
def _num(value, default=0):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value else default


def _normalise_run(e):
    out = dict(e)
    for key in ("duration_s", "eggs", "food", "nests", "crystals"):
        out[key] = _num(e.get(key))
    out["reason"] = e.get("reason") if isinstance(e.get("reason"), str) else "Other"
    return out


def _normalise_session(e):
    out = dict(e)
    for key in ("total_s", "runs", "hub_s", "run_s"):
        out[key] = _num(e.get(key))
    for key, _ in STEPS:                       # BD-653: seconds since joining; absent in older lines
        out[key] = _num(e.get(key), None)
    return out


def new_data():
    return {"runs": [], "sessions": [], "feedback": [], "counts": {}, "counts_by": {}, "funnel": [], "meta": {}, "bad_lines": 0,
            "unknown_events": 0, "visits": 0, "servers": set(), "errors": []}


def _take(data, event):
    kind = event.get("event")
    if kind == "run_end":
        data["runs"].append(_normalise_run(event))
    elif kind == "session_end":
        data["sessions"].append(_normalise_session(event))
        if isinstance(event.get("server"), str):
            data["servers"].add(event["server"])
    elif kind == "feedback":
        data["feedback"].append(event)
    elif kind == "count":
        name, value = event.get("name"), _num(event.get("value"), None)
        if isinstance(name, str) and value is not None:
            data["counts"][name] = data["counts"].get(name, 0) + value
            service = event.get("service")
            if isinstance(service, str) and service:      # BD-650: the game says which service answered "too fast"
                by = data["counts_by"].setdefault(name, {})
                by[service] = by.get(service, 0) + value
        else:
            data["bad_lines"] += 1
    elif kind == "funnel":
        step, players = event.get("step"), _num(event.get("players"), None)
        if isinstance(step, str) and players is not None:
            data["funnel"].append((step, players))
        else:
            data["bad_lines"] += 1
    elif kind == "visit":                      # BD-653: logged when a player joins
        data["visits"] += 1
        if isinstance(event.get("server"), str):
            data["servers"].add(event["server"])
    elif kind == "script_error":               # BD-651: scrubbed text, one line per distinct error per server
        text, name = event.get("text"), event.get("script")
        if isinstance(text, str) and len(data["errors"]) < MAX_ERROR_TEXTS:
            data["errors"].append({"script": name if isinstance(name, str) else "Other", "text": text})
    elif kind == "meta":
        data["meta"].update({k: v for k, v in event.items() if k != "event"})
    else:
        data["unknown_events"] += 1


def read_lines(lines, data=None):
    data = data or new_data()
    for line in lines:
        text = line.strip()
        if not text:
            continue
        payload = None
        for prefix in PREFIXES:
            at = text.find(prefix)
            if at >= 0:
                payload = text[at + len(prefix):]
                break
        if payload is None:
            if not text.startswith("{"):
                continue  # ordinary log noise
            payload = text
        try:
            event = json.loads(payload)
        except ValueError:
            data["bad_lines"] += 1
            continue
        if isinstance(event, dict):
            _take(data, event)
        else:
            data["bad_lines"] += 1
    return data


def read_csv(text, data=None):
    data = data or new_data()
    for row in csv.DictReader(io.StringIO(text)):
        name = (row.get("name") or "").strip()
        try:
            value = float((row.get("value") or "").strip())
        except ValueError:
            data["bad_lines"] += 1
            continue
        if name:
            data["counts"][name] = data["counts"].get(name, 0) + value
        else:
            data["bad_lines"] += 1
    return data


def read_files(paths):
    data = new_data()
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if str(path).lower().endswith(".csv"):
            read_csv(text, data)
        else:
            read_lines(text.splitlines(), data)
    return data


# ----------------------------------------------------------------------------------------------------- judging
def _band(value, green, yellow):
    """Green if value is inside the green (lo, hi), yellow inside the yellow (lo, hi), else red."""
    if green[0] <= value <= green[1]:
        return GREEN
    return YELLOW if yellow[0] <= value <= yellow[1] else RED


def _high_bad(value, green, yellow):
    """For numbers where higher is worse: at or under green is green, at or under yellow is yellow, else red."""
    return GREEN if value <= green else YELLOW if value <= yellow else RED


def check(name, status, number, words, gap=None):
    return {"name": name, "status": status, "number": number, "words": words, "gap": gap}


def _fmt(value, spec="{:g}"):
    return "no data" if value is None else spec.format(value)


def analyse(data, rate=None, limits=None):
    """Returns {"checks": [...], "summary": {...}, "funnel": [...], "gaps": [...], "comments": [...]}."""
    L = limits or LIMITS
    rate = rate or current_rate()
    summary = telemetry_report.summarize(data["runs"], data["sessions"])
    feedback = feedback_report.summarize(data["feedback"])
    sessions = data["sessions"]
    # A visit is logged when the player JOINS (BD-653), a session when the player LEAVES: per-visit rates use the joins.
    n_sessions = data["visits"] or len(sessions) or data["meta"].get("sessions") or 0
    game_recorded = data["visits"] > 0            # the log comes from a game that counts GAME_COUNTED itself: a missing count is zero
    counts = dict(data["counts"])
    if game_recorded:
        for key in GAME_COUNTED:
            counts.setdefault(key, 0)
    counts_by = data["counts_by"]
    checks = []

    # 1. eggs per 5 minutes against the target
    per5, ratio = summary["eggs_per_5min"], summary["vs_target"]
    if ratio is None:
        checks.append(check("Eggs in a 5-minute run", GREY, "no data", "No finished run of 20 seconds or more."))
    else:
        status = _band(ratio, L["eggs_ratio_green"], L["eggs_ratio_yellow"])
        words = (f"Players earn about {per5:g} eggs in 5 minutes. The goal is about {TARGET_EGGS}." if status == GREEN else
                 f"Players earn about {per5:g} eggs in 5 minutes, the goal is about {TARGET_EGGS}: "
                 + ("too few, runs feel empty." if ratio < 1 else "too many, the hatch party gets long."))
        checks.append(check("Eggs in a 5-minute run", status, f"{per5:g} (goal {TARGET_EGGS})", words))

    # 2. egg rate against FoodCatchRate
    e500 = summary["eggs_per_500_food"]
    expected = rate[0] / rate[1] * 500
    if e500 is None:
        checks.append(check("Eggs for 500 food", GREY, "no data", "No food numbers in the log."))
    else:
        lo, hi = (x * expected / 12 for x in L["eggs_per_500_green"])
        ylo, yhi = (x * expected / 12 for x in L["eggs_per_500_yellow"])
        status = _band(e500, (lo, hi), (ylo, yhi))
        note = "" if summary["food_source"] == "real" else " (food is guessed from eggs in older log lines)"
        checks.append(check("Eggs for 500 food", status, f"{e500:g} (setting {expected:g})",
                            f"500 food gave {e500:g} eggs; the game setting gives {expected:g} before weather bonuses.{note}"))

    # 3. run length
    med = summary["median_run_s"]
    if med is None:
        checks.append(check("Run length", GREY, "no data", "No finished runs."))
    else:
        minutes = med / 60
        status = _band(minutes, L["run_minutes_green"], L["run_minutes_yellow"])
        words = f"The middle run lasts {minutes:.1f} minutes (we want about 5)."
        if status != GREEN:
            words += " Runs are too short, players die or quit early." if minutes < 3 else " Runs are very long, players may be bored."
        checks.append(check("Run length", status, f"{minutes:.1f} min", words))

    # 4. runs per session and drop-off
    if not sessions:
        checks.append(check("Runs per visit", GREY, "no data", "No finished visits (a visit is logged when the player leaves)."))
        checks.append(check("Left before a first run", GREY, "no data", "No finished visits."))
    else:
        rps = summary["runs_per_session"]
        s = GREEN if rps >= L["runs_per_session_green"] else YELLOW if rps >= L["runs_per_session_yellow"] else RED
        checks.append(check("Runs per visit", s, f"{rps:g}", f"A visit has {rps:g} runs on average (we want 2 or more)."
                            + ("" if s == GREEN else " Players leave after too few runs.")))
        none = sum(1 for x in sessions if x["runs"] < 1)
        share = none / len(sessions)
        s = _high_bad(share, L["no_run_share_green"], L["no_run_share_yellow"])
        checks.append(check("Left before a first run", s, f"{none} of {len(sessions)}",
                            f"{none} of {len(sessions)} visits ended without one finished run."
                            + ("" if s == GREEN else " Check the start: it may be confusing or too slow.")))

    # 5. how runs end
    if summary["runs"]:
        quits = summary["end_reasons"].get("Disconnect", 0)
        share = quits / summary["runs"]
        s = _high_bad(share, L["disconnect_share_green"], L["disconnect_share_yellow"])
        checks.append(check("Quit in the middle of a run", s, f"{quits} of {summary['runs']}",
                            f"{quits} of {summary['runs']} runs ended because the player left the game."
                            + ("" if s == GREEN else " Players give up during a run: look at what happens just before.")))
    else:
        checks.append(check("Quit in the middle of a run", GREY, "no data", "No finished runs."))

    # 6. time in the hub
    hub = summary["hub_share"]
    if hub is None:
        checks.append(check("Time in the cave", GREY, "no data", "No visit times."))
    else:
        s = _high_bad(hub, L["hub_share_green"], L["hub_share_yellow"])
        checks.append(check("Time in the cave", s, f"{hub * 100:.0f}%",
                            f"Players spend {hub * 100:.0f}% of the time in the cave and the rest in runs."
                            + ("" if s == GREEN else " Too much waiting or menu time between runs.")))

    # 7. numbers the game cannot record yet (filled by hand with count lines or a CSV)
    def top_services(key):
        by = counts_by.get(key) or {}
        best = sorted(by.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        return (" Most: " + ", ".join(f"{name} {value:g}" for name, value in best) + ".") if best else ""

    def per_visit(key, label, green, yellow, unit):
        name, gap = GAPS[key]
        if key not in counts:
            checks.append(check(label, GREY, "not recorded", f"The game does not count this yet ({gap}). Add a count line by hand.", gap))
            return
        total = counts[key]
        if not n_sessions:
            checks.append(check(label, YELLOW if total else GREEN, f"{total:g} total", f"{total:g} in total; visits unknown.", gap))
            return
        per = total / n_sessions
        s = _high_bad(per, green, yellow)
        checks.append(check(label, s, f"{total:g} ({per:.1f} per visit)", f"{total:g} {unit} in {n_sessions} visits."
                            + ("" if s == GREEN else " Players hit this often.") + top_services(key), gap))

    per_visit("movement_rejects", "Set back by the anti-cheat", L["rejects_per_session_green"], L["rejects_per_session_yellow"],
              "set-backs")
    per_visit("rate_limited", "Told \"too fast\"", L["rate_limited_per_session_green"], L["rate_limited_per_session_yellow"],
              "\"too fast\" answers")
    gap_errors = GAPS["script_errors"][1]
    if "script_errors" not in counts and "crashes" not in counts:
        checks.append(check("Errors and crashes", GREY, "not recorded",
                            f"The game does not count errors or crashes yet ({gap_errors}). Read the Creator Hub error list by hand.", gap_errors))
    else:
        errs, crashes = counts.get("script_errors", 0), counts.get("crashes", 0)
        s = RED if crashes > 0 else _high_bad(errs, L["script_errors_green"], L["script_errors_yellow"])
        note = "" if "crashes" in counts else " Crashes are not counted by the game: look at the Creator Hub list."
        checks.append(check("Errors and crashes", s, f"{errs:g} errors, {crashes:g} crashes",
                            ("No script errors." if s == GREEN else
                             f"{errs:g} script errors and {crashes:g} crashes were reported. "
                             + ("Crashes first: open the log and find them." if crashes > 0 else "Open the error list and fix them."))
                            + note, gap_errors))
    # shop: the server cannot see a shop being opened (no event exists), so "opens" is a hand count and purchases come from the game
    shop_key = "shop_opens" if "shop_opens" in counts else "shop_purchases"
    for key, label in ((shop_key, "Shop use"), ("hatches", "Hatching")):
        gap = GAPS[key][1]
        if key not in counts:
            checks.append(check(label, GREY, "not recorded", f"The game does not count this yet ({gap}). Add a count line by hand.", gap))
        else:
            total = counts[key]
            per = total / n_sessions if n_sessions else None
            s = GREEN if total > 0 else YELLOW
            what = {"shop_opens": "opened", "shop_purchases": "bought"}.get(key, "")
            checks.append(check(label, s, f"{total:g}" + (f" ({per:.1f} per visit)" if per is not None else ""),
                                ((f"{total:g} things {what}." if what == "bought" else f"{total:g} times.") if total > 0
                                 else "Nobody used it. Is the door or button easy to find?") + top_services(key), gap))
    if counts.get("fusions"):
        checks.append(check("Fusion", GREEN, f"{counts['fusions']:g}", f"{counts['fusions']:g} made in the test.", GAPS["fusions"][1]))

    # time to the first food and the first run (BD-653), median over the visits that have the number
    def median_step(key):
        values = [x[key] for x in sessions if x.get(key) is not None]
        return (statistics.median(values), len(values)) if values else (None, 0)

    for key, label, words in (("first_food_s", "Time to first food", "to eat the first food"),
                              ("first_run_s", "Time to first run", "to start the first run")):
        med, n = median_step(key)
        if med is None:
            continue   # an older log: nothing to judge, and no gap line (the funnel gap covers it)
        s = _high_bad(med, L[key + "_green"], L[key + "_yellow"])
        checks.append(check(label, s, f"{med:g} s", f"The middle player needs {med:g} seconds {words} ({n} visits)."
                            + ("" if s == GREEN else " The start is slow: look at the first minute.")))

    # 8. feedback
    def rating(key, label, good):
        info = feedback[key]
        if info["answered"] < L["min_feedback"]:
            checks.append(check(label, GREY, f"{info['answered']} answers", "Too few answers to judge (we need 3 or more)."))
            return
        avg = info["average"]
        status = good(avg)
        checks.append(check(label, status, f"{avg:g} of 3", FEEDBACK_WORDS[key][status](avg)))

    FEEDBACK_WORDS = {
        "fun": {s: (lambda a, s=s: {GREEN: "Players say it is fun.", YELLOW: "Fun is only so-so.", RED: "Players say it is not fun."}[s]) for s in (GREEN, YELLOW, RED)},
        "looks": {s: (lambda a, s=s: {GREEN: "Players like how it looks.", YELLOW: "Looks are only so-so.", RED: "Players do not like how it looks."}[s]) for s in (GREEN, YELLOW, RED)},
        "level": {s: (lambda a, s=s: {GREEN: "The difficulty feels just right.",
                                      YELLOW: "Slightly too easy." if a < 2 else "Slightly too hard.",
                                      RED: "Far too easy." if a < 2 else "Far too hard."}[s]) for s in (GREEN, YELLOW, RED)},
    }
    rating("fun", "Players: fun", lambda a: GREEN if a >= L["fun_green"] else YELLOW if a >= L["fun_yellow"] else RED)
    rating("looks", "Players: looks", lambda a: GREEN if a >= L["fun_green"] else YELLOW if a >= L["fun_yellow"] else RED)
    rating("level", "Players: difficulty", lambda a: _band(a, L["level_green"], L["level_yellow"]))

    # funnel from the visits we have, then any hand-written steps
    funnel = []
    if sessions:
        total = len(sessions)
        funnel.append(("Came into the game", total))
        for n, label in ((1, "Finished 1 run"), (2, "Finished 2 runs"), (3, "Finished 3 runs")):
            funnel.append((label, sum(1 for x in sessions if x["runs"] >= n)))
    if any(x.get(key) is not None for x in sessions for key, _ in STEPS):
        have = {key: sum(1 for x in sessions if x.get(key) is not None) for key, _ in STEPS}
        labels = dict(STEPS)
        before = [(labels[k], have[k]) for k in ("first_run_s", "first_food_s")]
        after = [(labels[k], have[k]) for k in ("first_egg_s", "first_hatch_s")]
        funnel = funnel[:1] + before + funnel[1:2] + after + funnel[2:]
    funnel.extend((step, players) for step, players in data["funnel"])
    drop = None
    for (a, av), (b, bv) in zip(funnel, funnel[1:]):
        if av and bv <= av:
            loss = (av - bv) / av
            if drop is None or loss > drop[0]:
                drop = (loss, a, b)
    problems = [c for c in checks if c["status"] in (RED, YELLOW)]
    problems.sort(key=lambda c: ORDER[c["status"]])
    gaps = [c for c in checks if c["status"] == GREY and c["gap"]]
    has_steps = any(x.get(key) is not None for x in sessions for key, _ in STEPS)
    gaps_open = sorted({(GAPS[k][0], GAPS[k][1]) for k in GAPS
                        if k not in counts and (k != "funnel" or not (data["funnel"] or has_steps))})
    comments = [c for c in feedback["comments"]]
    return {"checks": checks, "summary": summary, "feedback": feedback, "funnel": funnel, "worst_drop": drop, "problems": problems,
            "gaps": gaps_open, "comments": comments, "sessions": n_sessions, "rate": rate, "visits": data["visits"],
            "servers": len(data["servers"]), "leave_lines": len(sessions), "errors": data["errors"], "game_recorded": game_recorded,
            "counts_by": counts_by, "step_times": step_times(sessions),
            "small_sample": bool(n_sessions) and n_sessions < L["min_sessions"], "bad_lines": data["bad_lines"],
            "unknown_events": data["unknown_events"], "meta": data["meta"], "overall": overall(checks)}


def step_times(sessions):
    """Median seconds from joining to each funnel step, and how many visits reached it (BD-653)."""
    out = []
    for key, label in STEPS:
        values = [x[key] for x in sessions if x.get(key) is not None]
        if values:
            out.append({"step": label, "median_s": statistics.median(values), "visits": len(values)})
    return out


def overall(checks):
    statuses = [c["status"] for c in checks]
    if RED in statuses:
        return RED
    if YELLOW in statuses:
        return YELLOW
    return GREEN if GREEN in statuses else GREY


# ----------------------------------------------------------------------------------------------------- output
def _bar(count, total, width=24):
    filled = round(width * count / total) if total else 0
    return "#" * filled + "." * (width - filled)


def render(report):
    meta, rate = report["meta"], report["rate"]
    title = "Playtest report" + (f": {meta['build']}" if isinstance(meta.get("build"), str) else "") + (
        f" ({meta['date']})" if isinstance(meta.get("date"), str) else "")
    s = report["summary"]
    lines = [f"# {title}", ""]
    testers = meta.get("testers")
    lines.append(f"Overall: **{report['overall']}**. {report['sessions']} visits, {s['runs']} runs"
                 + (f", {report['servers']} servers" if report["servers"] else "")
                 + (f", {testers:g} testers" if isinstance(testers, (int, float)) else "") + ".")
    if report["visits"] and report["visits"] > report["leave_lines"]:
        lines.append(f"{report['visits'] - report['leave_lines']} of {report['visits']} visits have no leave line (the server closed first "
                     f"or the log was copied too early): their run and time numbers are missing.")
    if report["small_sample"]:
        lines.append(f"Only {report['sessions']} visits: treat every light as a hint, not a result.")
    lines += ["", "| Light | Check | Number | In plain words |", "| --- | --- | --- | --- |"]
    for c in sorted(report["checks"], key=lambda c: ORDER[c["status"]]):
        lines.append(f"| {c['status']} | {c['name']} | {c['number']} | {c['words']} |")
    lines += ["", "## Where players drop off", ""]
    if report["funnel"]:
        top = report["funnel"][0][1]
        for label, count in report["funnel"]:
            share = f"{count / top * 100:.0f}%" if top else "n/a"
            lines.append(f"    {label:<28} {count:>4g}  {share:>5}  {_bar(count, top)}")
        drop = report["worst_drop"]
        if drop and drop[0] > 0:
            lines += ["", f"Biggest loss: {drop[0] * 100:.0f}% of players are gone between \"{drop[1]}\" and \"{drop[2]}\"."]
    else:
        lines.append("No finished visits, so no funnel.")
    if report["step_times"]:
        lines += ["", "## How fast players got there (median, from joining)", ""]
        for item in report["step_times"]:
            lines.append(f"    {item['step']:<20} {item['median_s']:>6g} s   ({item['visits']} visit{'s' if item['visits'] != 1 else ''})")
    lines += ["", "## Problems in plain words", ""]
    if report["problems"]:
        for c in report["problems"]:
            lines.append(f"- {c['status']}: {c['name']}. {c['words']}")
    else:
        lines.append("- Nothing flagged.")
    lines += ["", "## What players wrote", ""]
    f = report["feedback"]
    lines.append(f"{f['count']} feedback entries.")
    for c in report["comments"][:10]:
        lines.append(f"- [{c.get('location')}, {c.get('species')}] {c['text']}")
    if len(report["comments"]) > 10:
        lines.append(f"- ... and {len(report['comments']) - 10} more in the log.")
    if report["errors"]:
        lines += ["", "## Script errors seen (scrubbed text, one line per kind)", ""]
        for item in report["errors"][:10]:
            lines.append(f"- {item['script']}: {item['text']}")
        if len(report["errors"]) > 10:
            lines.append(f"- ... and {len(report['errors']) - 10} more kinds in the log.")
    lines += ["", "## The game does not record these yet", ""]
    if report["gaps"]:
        for label, row in report["gaps"]:
            lines.append(f"- {label} ({row}). Fill in by hand: a `count` line or a CSV row.")
    else:
        lines.append("- Nothing missing.")
    lines += ["", "---",
              f"Target: about {TARGET_EGGS} eggs in a 5-minute run. Egg setting: FoodCatchRate {rate[0]:g}/{rate[1]:g} "
              f"(docs/119, current; 40/500, 15/150 and 4/500 are historical). Limits are provisional (docs/167 section 9)."]
    if report["bad_lines"]:
        lines.append(f"{report['bad_lines']} lines looked like data but could not be read.")
    if report["unknown_events"]:
        lines.append(f"{report['unknown_events']} lines had an event this report does not know; they were skipped.")
    return "\n".join(lines) + "\n"


def to_json(report):
    out = {k: report[k] for k in ("overall", "sessions", "funnel", "gaps", "small_sample", "bad_lines", "unknown_events", "meta",
                                  "visits", "servers", "errors", "counts_by", "step_times", "game_recorded")}
    out["checks"] = report["checks"]
    out["summary"] = {k: v for k, v in report["summary"].items() if k != "per_run"}
    out["feedback"] = report["feedback"]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", help="server logs, JSON-lines files or .csv files")
    ap.add_argument("--out", help="write the markdown report here as well as printing it")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the report")
    args = ap.parse_args(argv)
    report = analyse(read_files(args.inputs))
    text = json.dumps(to_json(report), indent=2, ensure_ascii=False) if args.json else render(report)
    if args.out:
        Path(args.out).write_text(render(report), encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
