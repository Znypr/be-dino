#!/usr/bin/env python3
"""Work log and retrospectives (docs/168): record every agent task, see what costs time, learn from it.

  python tools/retro_log.py add --task "..." --agent-kind worker --pr 460 --duration-min 12 \\
      --tool-calls 50 --tokens-k 180 --verdict good --fact-check "checked against docs/114" \\
      --step "read brief" --step "wrote tool" --problem conflict --lesson "..." --action tool \\
      --action-ref tools/merge_main_into_pr.py --rework-cycles 1 --lost-min 3
  python tools/retro_log.py list [--last 10] [--kind lead]   # markdown table
  python tools/retro_log.py summary                           # totals, rework share, problem tags, top 3 time sinks
  python tools/retro_log.py render [--check]                  # rewrite the table in docs/168 (--check: only compare)

The log is docs/retro/work-log.jsonl, one JSON object per line, append only. Problems use a small tag
vocabulary (TAGS below), optionally followed by ": detail", for example "conflict: kanban row 612".
"""
import argparse
import datetime
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "retro" / "work-log.jsonl"
DOC = ROOT / "docs" / "168-work-log-and-retrospectives.md"
START = "<!-- retro-table:start -->"
END = "<!-- retro-table:end -->"

TAGS = ("conflict", "stacked-pr", "doc-number-collision", "stale-context", "studio-window",
        "tool-missing", "wrong-recipient", "ci-red", "scope-creep", "unverified-claim", "other")
VERDICTS = ("good", "ok", "rework")
ACTIONS = ("tool", "brief", "memory", "none")
KINDS = ("worker", "lead")
FIELDS = ("date", "task", "agent_kind", "pr", "duration_min", "tool_calls", "tokens_k", "quality_verdict",
          "fact_check", "steps", "problems", "lesson", "action", "action_ref", "rework_cycles", "lost_min")


def problem_tag(problem):
    return problem.split(":", 1)[0].strip()


def validate(e):
    """Return a list of complaints (empty when the entry is fine)."""
    bad = []
    for f in ("date", "task", "agent_kind", "quality_verdict"):
        if not e.get(f):
            bad.append("missing " + f)
    try:
        datetime.date.fromisoformat(str(e.get("date", "")))
    except ValueError:
        bad.append("date must be YYYY-MM-DD")
    if e.get("agent_kind") and e["agent_kind"] not in KINDS:
        bad.append("agent_kind must be one of " + "/".join(KINDS))
    if e.get("quality_verdict") and e["quality_verdict"] not in VERDICTS:
        bad.append("quality_verdict must be one of " + "/".join(VERDICTS))
    if e.get("action", "none") not in ACTIONS:
        bad.append("action must be one of " + "/".join(ACTIONS))
    for f in ("pr", "duration_min", "tool_calls", "tokens_k", "lost_min"):
        v = e.get(f)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0):
            bad.append(f + " must be a number >= 0 or null")
    if not isinstance(e.get("rework_cycles", 0), int) or e.get("rework_cycles", 0) < 0:
        bad.append("rework_cycles must be an integer >= 0")
    for f in ("steps", "problems"):
        if not isinstance(e.get(f, []), list):
            bad.append(f + " must be a list")
    for p in e.get("problems", []):
        if problem_tag(p) not in TAGS:
            bad.append("unknown problem tag %r (use one of %s)" % (problem_tag(p), ", ".join(TAGS)))
    if e.get("action", "none") != "none" and not e.get("action_ref"):
        bad.append("action_ref is needed when action is not none")
    if e.get("quality_verdict") == "rework" and not e.get("rework_cycles"):
        bad.append("verdict rework needs rework_cycles >= 1")
    return bad


def normalise(e):
    out = {f: e.get(f) for f in FIELDS}
    out["steps"] = list(e.get("steps") or [])
    out["problems"] = list(e.get("problems") or [])
    out["rework_cycles"] = int(e.get("rework_cycles") or 0)
    out["action"] = e.get("action") or "none"
    for f in ("fact_check", "lesson", "action_ref"):
        out[f] = e.get(f) or ""
    return out


def load(path=LOG):
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError as err:
                raise SystemExit("%s line %d is not JSON: %s" % (path, n, err))
    return out


def append(entry, path=LOG):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(normalise(entry), ensure_ascii=False) + "\n")


def cell(v):
    return str(v).replace("|", "/").replace("\n", " ") if v not in (None, "") else "-"


def table(entries):
    head = "| Date | Task | Who | PR | Min | Calls | Tokens (k) | Verdict | Redo | Problems | Lesson / action |"
    rows = [head, "|" + "---|" * 11]
    for e in entries:
        act = e.get("action") or "none"
        la = e.get("lesson") or ""
        if act != "none":
            la = "%s (%s: %s)" % (la, act, e.get("action_ref") or "-")
        rows.append("| " + " | ".join(cell(x) for x in (
            e.get("date"), e.get("task"), e.get("agent_kind"), ("#%s" % e["pr"]) if e.get("pr") else None,
            e.get("duration_min"), e.get("tool_calls"), e.get("tokens_k"), e.get("quality_verdict"),
            e.get("rework_cycles") or None, ", ".join(e.get("problems") or []), la)) + " |")
    return "\n".join(rows)


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def fmt(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


def summary(entries):
    if not entries:
        return "The work log is empty."
    out = []
    ws = [e for e in entries if e.get("agent_kind") == "worker"]
    durs = [_num(e.get("duration_min")) for e in ws if _num(e.get("duration_min")) is not None]
    out.append("Entries: %d (%d agent tasks, %d lead entries)" % (len(entries), len(ws), len(entries) - len(ws)))
    if durs:
        out.append("Agent task time: total %s min, median %s min, longest %s min"
                   % (fmt(sum(durs)), fmt(statistics.median(durs)), fmt(max(durs))))
    toks = [_num(e.get("tokens_k")) for e in ws if _num(e.get("tokens_k")) is not None]
    if toks:
        out.append("Agent tokens: total %sk, median %sk" % (fmt(sum(toks)), fmt(statistics.median(toks))))
    for label, group in (("agent tasks", ws), ("lead entries", [e for e in entries if e not in ws])):
        needed = [e for e in group if e.get("rework_cycles") or e.get("quality_verdict") == "rework"]
        if group:
            out.append("Needed a redo (merge, conflict, CI or a second run), %s: %d of %d (%d%%); redo rounds: %d"
                       % (label, len(needed), len(group), round(100 * len(needed) / len(group)),
                          sum(e.get("rework_cycles") or 0 for e in group)))
    v = Counter(e.get("quality_verdict") for e in entries)
    out.append("Verdicts: " + ", ".join("%s %d" % (k, v[k]) for k in VERDICTS if v[k]))
    tags = Counter()
    lost = defaultdict(float)
    for e in entries:
        mine = {problem_tag(p) for p in e.get("problems") or []}
        for t in mine:
            tags[t] += 1
        if e.get("problems") and _num(e.get("lost_min")):
            # the lost time is charged to the first problem listed: put the main cause first
            lost[problem_tag(e["problems"][0])] += e["lost_min"]
    out.append("")
    out.append("Most frequent problems:")
    for t, n in sorted(tags.items(), key=lambda kv: (-kv[1], kv[0]))[:6]:
        out.append("  %-22s %d task(s), about %s min lost" % (t, n, fmt(lost[t])))
    out.append("")
    out.append("Top 3 time sinks (minutes lost, estimates in the log):")
    sinks = sorted(lost.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    for t, m in sinks:
        out.append("  %-22s about %s min" % (t, fmt(m)))
    if not sinks:
        out.append("  none recorded (set lost_min on entries that lost time)")
    unfixed = [e for e in entries if e.get("problems") and (e.get("action") or "none") == "none"]
    if unfixed:
        out.append("")
        out.append("Problems with no fix yet (action none): %d  -> " % len(unfixed)
                   + "; ".join(cell(e.get("task"))[:50] for e in unfixed[:5]))
    return "\n".join(out)


def render(doc_path=DOC, log_path=LOG, check=False):
    """Rewrite the block between the marker comments. Returns True when the file is already current."""
    doc_path = Path(doc_path)
    text = doc_path.read_text(encoding="utf-8")
    a, b = text.find(START), text.find(END)
    if a < 0 or b < a:
        raise SystemExit("%s has no %s ... %s block" % (doc_path, START, END))
    new = text[:a + len(START)] + "\n" + table(load(log_path)) + "\n" + text[b:]
    if new == text:
        return True
    if not check:
        doc_path.write_text(new, encoding="utf-8", newline="\n")
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=str(LOG))
    ap.add_argument("--doc", default=str(DOC))
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="append one entry")
    a.add_argument("--date", default=datetime.date.today().isoformat())
    a.add_argument("--task", required=True)
    a.add_argument("--agent-kind", default="worker", choices=KINDS)
    a.add_argument("--pr", type=int)
    a.add_argument("--duration-min", type=float)
    a.add_argument("--tool-calls", type=int)
    a.add_argument("--tokens-k", type=float)
    a.add_argument("--verdict", required=True, choices=VERDICTS)
    a.add_argument("--fact-check", default="")
    a.add_argument("--step", action="append", default=[])
    a.add_argument("--problem", action="append", default=[], help="tag or 'tag: detail'; tags: " + ", ".join(TAGS))
    a.add_argument("--lesson", default="")
    a.add_argument("--action", default="none", choices=ACTIONS)
    a.add_argument("--action-ref", default="")
    a.add_argument("--rework-cycles", type=int, default=0)
    a.add_argument("--lost-min", type=float)
    ls = sub.add_parser("list", help="markdown table")
    ls.add_argument("--last", type=int)
    ls.add_argument("--kind", choices=KINDS)
    sub.add_parser("summary", help="totals, rework share, problem tags, top 3 time sinks")
    r = sub.add_parser("render", help="rewrite the table block in the doc")
    r.add_argument("--check", action="store_true", help="exit 1 when the doc table is stale")
    args = ap.parse_args(argv)

    if args.cmd == "add":
        e = {"date": args.date, "task": args.task, "agent_kind": args.agent_kind, "pr": args.pr,
             "duration_min": args.duration_min, "tool_calls": args.tool_calls, "tokens_k": args.tokens_k,
             "quality_verdict": args.verdict, "fact_check": args.fact_check, "steps": args.step,
             "problems": args.problem, "lesson": args.lesson, "action": args.action,
             "action_ref": args.action_ref, "rework_cycles": args.rework_cycles, "lost_min": args.lost_min}
        bad = validate(e)
        if bad:
            print("not added:\n  " + "\n  ".join(bad), file=sys.stderr)
            return 2
        append(e, args.log)
        print("added; now %d entries. Run: python tools/retro_log.py render" % len(load(args.log)))
    elif args.cmd == "list":
        es = load(args.log)
        if args.kind:
            es = [e for e in es if e.get("agent_kind") == args.kind]
        if args.last:
            es = es[-args.last:]
        print(table(es))
    elif args.cmd == "summary":
        print(summary(load(args.log)))
    elif args.cmd == "render":
        ok = render(args.doc, args.log, args.check)
        if args.check and not ok:
            print("%s table is stale: run python tools/retro_log.py render" % args.doc, file=sys.stderr)
            return 1
        print("table is current" if ok else "table rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
