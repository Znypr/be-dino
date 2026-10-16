"""Fail if a docs/120 pending-upload item has no config slot, or a slot is unread / malformed.

Checks (tools/asset_slots.json is the slot manifest used by tools/bind_assets.py):
  1. every row of the docs/120 tables has a 'Bind in' cell, unless it says 'n/a (reuses ...)';
  2. every `file:group` token in that cell resolves to at least one manifest slot, and every manifest slot is named by a row;
  3. every slot's line really exists in its file with an EMPTY or valid id (never an invented-looking one) and the slot name
     is unique;
  4. every slot is READ: it names a reader file that contains its needle, or is marked pending with the task that will read it
     (pending slots are still safe: empty = native fallback or silence).
Also self-tests tools/bind_assets.py on an in-memory copy (nothing is written).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_assets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/120-pending-owner-uploads-checklist.md'
errors = []


def err(msg):
    errors.append(msg)


slots = json.loads((ROOT / 'tools/asset_slots.json').read_text(encoding='utf-8'))['slots']
names = [s['name'] for s in slots]
if len(set(names)) != len(names):
    err('duplicate slot names: ' + ', '.join(sorted({n for n in names if names.count(n) > 1})))
by_name = {s['name']: s for s in slots}

# 3 + 4: slot exists, id valid, and is read
for s in slots:
    path = ROOT / s['file']
    if not path.exists():
        err(f'{s["name"]}: file missing {s["file"]}')
        continue
    text = path.read_text(encoding='utf-8')
    try:
        value = bind_assets.current_value(s, text)
    except ValueError as e:
        err(f'{s["name"]}: {e}')
        continue
    if s['target'] == 'table' and not re.search(rf'-- bind:begin {s["table"]}', text):
        err(f'{s["name"]}: bind markers for {s["table"]} missing')
    if s['target'] != 'table':
        # the line must exist at all (an empty id is fine); current_value returns '' for both missing and empty, so probe write
        try:
            bind_assets.write_slot(s, text, '12345')
        except ValueError as e:
            err(f'{s["name"]}: slot line missing ({e})')
    if value and not re.fullmatch(r'(rbxassetid://)?[1-9][0-9]{4,18}', value):
        err(f'{s["name"]}: malformed id {value!r}')
    reader = s.get('reader')
    if reader:
        rf, needle = reader
        rp = ROOT / rf
        if not rp.exists() or needle not in rp.read_text(encoding='utf-8'):
            err(f'{s["name"]}: slot is unread: {rf} does not contain {needle!r}')
    elif not s.get('pending'):
        err(f'{s["name"]}: needs a reader or a pending task id')

# 1 + 2: docs rows <-> slots
token_re = re.compile(r'`([^`]+):([^`:]+)`')
used = set()
header_seen = False
for line in DOC.read_text(encoding='utf-8').split('\n'):
    if not line.startswith('|'):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if cells[0] in ('Asset', 'Sound'):
        header_seen = cells[-1].startswith('Bind in')
        if not header_seen:
            err('docs/120 table without a "Bind in" last column: ' + line[:60])
        continue
    if set(cells[0]) <= set('-') or not header_seen:
        continue
    cell = cells[-1]
    if cell.startswith('n/a (reuses'):
        continue
    toks = token_re.findall(cell)
    if not toks:
        err(f'docs/120 row has no "Bind in" slot: {cells[0][:60]}')
    for f, g in toks:
        hit = [s for s in slots if s['file'] == f and (s['group'] == g or s['key'] == g or s.get('table') == g)]
        if not hit:
            err(f'docs/120 row {cells[0][:40]!r}: no slot for {f}:{g}')
        used.update(s['name'] for s in hit)
for n in names:
    if n not in used:
        err(f'slot {n} is not named by any docs/120 row (add it to the Bind in column)')

# self-test of the binder, in memory
try:
    pairs = bind_assets.parse_input('ribbonSoft = rbxassetid://123456789\ntrail_fern: 223456789 # c\n')
    plan, texts = bind_assets.bind(pairs, by_name)
    ea = texts[ROOT / 'src/shared/EffectAssets.luau']
    assert 'ribbonSoft = {id = "rbxassetid://123456789"' in ea
    assert 'fern = "rbxassetid://223456789",' in texts[ROOT / 'src/shared/ProgressionConfig.luau']
    for bad in ('nope=123456', 'ribbonSoft=abc', 'ribbonSoft=', 'ribbonSoft=0', 'ribbonSoft=1\nribbonSoft=2'):
        try:
            bind_assets.bind(bind_assets.parse_input(bad), by_name)
        except ValueError:
            continue
        err('binder accepted bad input: ' + repr(bad))
except Exception as e:  # noqa: BLE001
    err(f'bind_assets self-test failed: {e!r}')

if errors:
    print('Asset slot check FAILED:\n  ' + '\n  '.join(errors))
    sys.exit(1)
pending = sum(1 for s in slots if s.get('pending'))
print(f'Asset slots OK: {len(slots)} slots ({pending} waiting on consumer code), all docs/120 rows bound.')
