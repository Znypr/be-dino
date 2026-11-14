#!/usr/bin/env python3
"""Resolve the usual merge conflicts between two branches that each bound asset ids (run inside the conflicted checkout).

    python tools/resolve_asset_binding_conflicts.py            # resolve and `git add` the three files
    python tools/resolve_asset_binding_conflicts.py --check    # only say what it would do

  * src/shared/AssetSlots.luau: per slot line, the bound value wins over "" (two different ids for one slot = stop, a human decides).
  * docs/77-asset-registry.md and docs/115-decisions-log.md (append-only logs): both sides' lines are kept (ours first).
  * docs/evidence/roblox-uploads.json: union of both sides by assetId (fields merged).
  * docs/kanban/rows/BD-*.md (one row per file): the side whose status is further along wins (Backlog < In progress < Review < Review / test < Done).
Any other conflicted file is left alone and named. Standard library only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

BLOCK = re.compile(r'<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n', re.S)
SLOTS, REG, UPLOADS = 'src/shared/AssetSlots.luau', 'docs/77-asset-registry.md', 'docs/evidence/roblox-uploads.json'
APPEND_ONLY = {REG, 'docs/115-decisions-log.md'}  # logs where both branches only add lines: keep both, ours first


def git(*args) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def slots(text: str) -> str:
    def one(m):
        a, b = m.group(1).splitlines(True), m.group(2).splitlines(True)
        if len(a) != len(b):
            sys.exit(f'{SLOTS}: conflict sides have different line counts; resolve by hand')
        out = []
        for la, lb in zip(a, b):
            if la.split('=')[0].strip() != lb.split('=')[0].strip():
                sys.exit(f'{SLOTS}: lines do not pair up ({la.strip()} / {lb.strip()}); resolve by hand')
            if '""' in la:
                out.append(lb)
            elif '""' in lb or la == lb:
                out.append(la)
            else:
                sys.exit(f'{SLOTS}: two different ids for one slot: {la.strip()} vs {lb.strip()}')
        return ''.join(out)
    return BLOCK.sub(one, text)


def uploads() -> str:
    seen, out = {}, []
    for stage in (2, 3):
        for e in json.loads(git('show', f':{stage}:{UPLOADS}')):
            k = e.get('assetId')
            if k in seen:
                seen[k].update({x: y for x, y in e.items() if x not in seen[k]})
            else:
                seen[k] = e
                out.append(e)
    return json.dumps(out, indent=2, ensure_ascii=False) + '\n'


ORDER = ['Backlog', 'Blocked', 'In progress', 'In review', 'Review', 'Review / test', 'Done']


def row_stage(text: str) -> int:
    parts = text.split('|')
    status = parts[2].strip() if len(parts) > 2 else ''
    return ORDER.index(status) if status in ORDER else -1


def kanban_row(path: str) -> str:
    ours, theirs = git('show', f':2:{path}'), git('show', f':3:{path}')
    return theirs if row_stage(theirs) > row_stage(ours) else ours


def main(argv=None) -> int:
    check = '--check' in (argv or sys.argv[1:])
    conflicted = git('diff', '--name-only', '--diff-filter=U').split()
    done = []
    for path in conflicted:
        if path == SLOTS:
            new = slots(open(path, encoding='utf-8').read())
        elif path in APPEND_ONLY:
            new = BLOCK.sub(lambda m: m.group(1) + m.group(2), open(path, encoding='utf-8').read())
        elif path == UPLOADS:
            new = uploads()
        elif path.startswith('docs/kanban/rows/BD-') and path.endswith('.md'):
            new = kanban_row(path)
        else:
            print('left for a human:', path)
            continue
        done.append(path)
        if not check:
            open(path, 'w', encoding='utf-8', newline='\n').write(new)
            git('add', path)
    print(('would resolve: ' if check else 'resolved: ') + (', '.join(done) or 'nothing'))
    return 0 if len(done) == len(conflicted) else 1


if __name__ == '__main__':
    sys.exit(main())
