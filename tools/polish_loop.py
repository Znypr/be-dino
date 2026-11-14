#!/usr/bin/env python3
"""Polish loop (BD-1191, docs/234): capture every screen -> role review -> ranked findings -> rows -> fix -> again.

    python tools/polish_loop.py screens                      # the screen list of the tour, and the Luau tour snippet for Studio MCP
    python tools/polish_loop.py ingest docs/evidence/<d>-polish-loop/findings.json [--scores scores.json]
    python tools/polish_loop.py top [-n 10]                  # the open findings, worst first
    python tools/polish_loop.py rows [-n 5] [--apply]        # turn the top open findings into kanban rows (dry run without --apply)
    python tools/polish_loop.py close <id> --note "PR #n"    # mark a finding fixed
    python tools/polish_loop.py queue                        # rewrite the polish section of docs/be-dino-queue.md

State lives in docs/polish/findings.json (one stable id per finding: screen + title) and docs/polish/scores.json
(history of screen scores per run, so a screen that gets worse shows). Rank = severity x reach, owner-taste items last.
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'docs/polish/findings.json'
SCORES = ROOT / 'docs/polish/scores.json'
QUEUE = ROOT / 'docs/be-dino-queue.md'
KIT = ROOT / 'src/shared/ToyboxKit.luau'
ROLES = {'kid', 'reviewer', 'art', 'ux', 'feel', 'qa', 'benchmark'}  # benchmark = docs/235 top-games comparison
START, END = '<!-- polish-loop:start -->', '<!-- polish-loop:end -->'

# Screens the tour opens (Bootstrap open(name)); the rest of ScreenPlace needs game state (a pending egg, a purchase).
TOUR = ['hud', 'collection', 'detail', 'eggs', 'auras', 'potions', 'fusion', 'settings', 'home']


def load(path: Path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def fid(f: dict) -> str:
    key = (f['screen'].strip().lower() + '|' + re.sub(r'\W+', ' ', f['title'].lower()).strip())
    return 'P-' + hashlib.sha1(key.encode()).hexdigest()[:6]


def rank(f: dict) -> int:
    return int(f.get('severity', 1)) * int(f.get('reach', 1)) * (0 if f.get('needs_owner') else 1) or -1


def validate(f: dict) -> list[str]:
    bad = [k for k in ('screen', 'role', 'title', 'detail', 'fix', 'severity', 'reach', 'kind') if k not in f]
    if 'role' in f and f['role'] not in ROLES:
        bad.append('role=' + str(f['role']))
    for k in ('severity', 'reach'):
        if k in f and int(f[k]) not in (1, 2, 3):
            bad.append(k + ' not 1..3')
    return bad


def cmd_screens(_):
    print('screens:', ', '.join(TOUR))
    print('\n-- Studio MCP, Client datamodel, one call per screen, then screen_capture:')
    print('local t = game.Players.LocalPlayer:WaitForChild("BeDinoScreenTour", 10)')
    print('return t:Invoke("<screen>")   -- "close" closes the window; "hud" = close')


def cmd_ingest(a):
    state = load(STATE, [])
    by_id = {f['id']: f for f in state}
    new = json.loads(Path(a.findings).read_text(encoding='utf-8'))
    added = reopened = 0
    for f in new:
        bad = validate(f)
        if bad:
            sys.exit(f'bad finding {f.get("title")!r}: {bad}')
        f['id'] = fid(f)
        old = by_id.get(f['id'])
        if old is None:
            f.update(state='open', first_seen=str(date.today()), seen=1)
            state.append(f)
            by_id[f['id']] = f
            added += 1
        else:
            old['seen'] = old.get('seen', 1) + 1
            old['last_seen'] = str(date.today())
            if old['state'] == 'fixed':
                old['state'] = 'open'
                old['note'] = 'came back ' + str(date.today())
                reopened += 1
    save(STATE, state)
    if a.scores:
        hist = load(SCORES, {})
        for screen, v in json.loads(Path(a.scores).read_text(encoding='utf-8')).items():
            hist.setdefault(screen, []).append({'date': str(date.today()), 'score': v['score'], 'line': v.get('one_line', '')})
        save(SCORES, hist)
    print(f'{added} new, {reopened} reopened, {len(new) - added - reopened} already known; {sum(f["state"] == "open" for f in state)} open')
    cmd_queue(a)


def open_sorted():
    return sorted((f for f in load(STATE, []) if f['state'] == 'open'), key=lambda f: (-rank(f), f['screen']))


def cmd_top(a):
    for f in open_sorted()[:a.n]:
        print(f"{f['id']}  r{rank(f):>2}  [{f['screen']}/{f['role']}] {f['title']} -> {f['fix']}")


def cmd_rows(a):
    picked = [f for f in open_sorted() if not f.get('row') and not f.get('needs_owner')][:a.n]
    state = load(STATE, [])
    for f in picked:
        title = f"Polish {f['id']} ({f['screen']}): {f['title']}. Fix: {f['fix']} (docs/234 loop)"
        if not a.apply:
            print('would add:', title)
            continue
        out = subprocess.run([sys.executable, str(ROOT / 'tools/kanban.py'), 'add', '--title', title, '--priority', 'P1'],
                             capture_output=True, text=True, cwd=ROOT)
        m = re.search(r'(BD-\d+) created', out.stdout)
        if not m:
            sys.exit('kanban add failed: ' + out.stdout + out.stderr)
        for s in state:
            if s['id'] == f['id']:
                s['row'] = m.group(1)
        print(m.group(1), title)
    if a.apply:
        save(STATE, state)
        cmd_queue(a)


def cmd_close(a):
    state = load(STATE, [])
    for f in state:
        if f['id'] == a.id:
            f['state'], f['note'], f['fixed'] = 'fixed', a.note, str(date.today())
            save(STATE, state)
            cmd_queue(a)
            return
    sys.exit('no finding ' + a.id)


def cmd_queue(_):
    rows = open_sorted()
    hist = load(SCORES, {})
    lines = [START, '## Polish loop (generated by tools/polish_loop.py, docs/234)', '',
             'Screen scores (latest, 10 = top Roblox game): ' +
             (', '.join(f"{s} {v[-1]['score']}" for s, v in sorted(hist.items())) or 'no run yet'), '',
             '| Rank | Id | Screen | Finding | Fix | Row |', '| ---: | --- | --- | --- | --- | --- |']
    for f in rows[:25]:
        r = 'owner' if f.get('needs_owner') else rank(f)
        lines.append(f"| {r} | {f['id']} | {f['screen']} | {f['title']} | {f['fix']} | {f.get('row', '')} |")
    lines.append(f'\n{len(rows)} open, {sum(1 for f in load(STATE, []) if f["state"] == "fixed")} fixed.')
    lines.append(END)
    text = QUEUE.read_text(encoding='utf-8') if QUEUE.exists() else '# Be Dino! idea and bug queue (ranked)\n'
    block = '\n'.join(lines)
    text = re.sub(re.escape(START) + '.*?' + re.escape(END), block, text, flags=re.S) if START in text else text.rstrip() + '\n\n' + block + '\n'
    QUEUE.write_text(text, encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('screens').set_defaults(func=cmd_screens)
    p = sub.add_parser('ingest'); p.add_argument('findings'); p.add_argument('--scores'); p.set_defaults(func=cmd_ingest)
    p = sub.add_parser('top'); p.add_argument('-n', type=int, default=10); p.set_defaults(func=cmd_top)
    p = sub.add_parser('rows'); p.add_argument('-n', type=int, default=5); p.add_argument('--apply', action='store_true'); p.set_defaults(func=cmd_rows)
    p = sub.add_parser('close'); p.add_argument('id'); p.add_argument('--note', required=True); p.set_defaults(func=cmd_close)
    sub.add_parser('queue').set_defaults(func=cmd_queue)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == '__main__':
    main()
