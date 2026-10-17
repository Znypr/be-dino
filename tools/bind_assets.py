"""Bind owner uploads: paste 'name=rbxassetid' lines (or a small JSON) and the ids land in the right config keys.

    python tools/bind_assets.py ids.txt          # file with lines  name=rbxassetid://123  or  name: 123
    python tools/bind_assets.py - < ids.txt       # same, from stdin
    python tools/bind_assets.py ids.json          # {"ribbonSoft": "rbxassetid://123", "trail_fern": 456}
    python tools/bind_assets.py --list            # every slot name, kind and whether it is bound
    python tools/bind_assets.py --batch uploaded.json --manifest build/upload-batch/manifest.json   # one-shot batch (tools/upload_batch.py)
    python tools/bind_assets.py --dry-run ids.txt # validate and show, write nothing

Slots come from tools/asset_slots.json (checked against docs/120 by tools/verify_asset_slots.py). Unknown names, malformed
ids and duplicate names are refused and NOTHING is written. Ids are never invented: empty values are refused too.
Audio ids must be Audio uploads, images must be Image (not Decal) uploads (docs/120 upload flow).
"""
import argparse
import datetime
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'tools/asset_slots.json'
ID_RE = re.compile(r'^(?:rbxassetid://)?([1-9][0-9]{4,18})$')


def load_slots():
    return {s['name']: s for s in json.loads(MANIFEST.read_text(encoding='utf-8'))['slots']}


def parse_id(raw):
    m = ID_RE.match(str(raw).strip())
    if not m:
        raise ValueError(f'not a Roblox asset id: {raw!r} (expected rbxassetid://12345 or digits)')
    return m.group(1)


def parse_input(text):
    text = text.strip()
    pairs = []
    if text.startswith('{'):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError('JSON must be an object of name: id')
        pairs = [(k, v) for k, v in data.items()]
    else:
        for n, line in enumerate(text.splitlines(), 1):
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            m = re.match(r'^([A-Za-z0-9_.]+)\s*[=:]\s*(.+)$', line)
            if not m:
                raise ValueError(f'line {n}: expected name=rbxassetid://N, got {line!r}')
            pairs.append((m.group(1), m.group(2)))
    seen = set()
    for name, _ in pairs:
        if name in seen:
            raise ValueError(f'duplicate name: {name}')
        seen.add(name)
    return pairs


def batch_pairs(upload_map, manifest):
    """{"http://localhost:PORT/<file>": "rbxassetid://N"} + upload_batch manifest [{file, slot, url_path}] -> [(slot, id)].
    A URL matches a manifest entry by its last path segment, so the host and port do not matter. Every URL must match
    exactly one entry; an entry with no URL is simply not bound (partial uploads are fine)."""
    by_path = {e['url_path'].lstrip('/'): e['slot'] for e in manifest}
    pairs, errors = [], []
    for url, ident in upload_map.items():
        tail = re.split(r'[?#]', str(url))[0].rstrip('/').rsplit('/', 1)[-1]
        slot = by_path.get(tail)
        if slot is None:
            errors.append(f'{url}: not in the manifest (expected one of the url_path names, e.g. {next(iter(by_path), "?")})')
        else:
            pairs.append((slot, ident))
    if errors:
        raise ValueError('\n'.join(errors))
    return pairs


def changed_lines(old, new):
    """(old line, new line) pairs that differ ('' for a pure insert), for the dry-run report."""
    a, b = old.splitlines(), new.splitlines()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        old_l, new_l = [x.strip() for x in a[i1:i2]], [x.strip() for x in b[j1:j2]]
        for k in range(max(len(old_l), len(new_l))):
            out.append((old_l[k] if k < len(old_l) else '', new_l[k] if k < len(new_l) else ''))
    return out


def rep_one(text, pattern, value, what):
    new, count = re.subn(pattern, lambda m: m.group(1) + value + m.group(3), text, count=1)
    if count != 1:
        raise ValueError(f'slot line not found for {what}')
    return new


def current_value(slot, text):
    """The id currently written for a slot ('' when empty/unbound)."""
    key = re.escape(slot['key'])
    target = slot['target']
    if target in ('effect', 'sfx'):
        m = re.search(rf'\n\s+{key} = \{{id = "([^"]*)"', text)
    elif target == 'weather':
        m = re.search(rf'\n\s+{key}=\{{id="([^"]*)"', text)
    elif target == 'slot':
        m = re.search(rf'\n\s+{key} = "([^"]*)",', text)
    elif target == 'worldmesh':
        m = re.search(rf'\n\s+{key} = \{{assetId = "([^"]*)"', text)
    elif target == 'cavebed':
        m = re.search(r'Rules\.Bed = \{id = "([^"]*)"', text)
    elif target == 'hatchbucket':
        m = re.search(r'bucket = \{assetId = "([^"]*)"', text)
        return m.group(1) if m and slot_is_bound_bucket(text) else ''
    elif target == 'table':
        block = table_block(text, slot['table'])
        m = re.search(rf'\n\s+{key} = "([^"]*)",', block)
    elif target == 'matvar':  # a worldMaterials entry of resources/visual-upgrade-bindings.json (bare digits; `bound` is never touched)
        m = re.search(matvar_pattern(slot), text, re.S)
        return m.group(2) if m else ''
    else:
        raise ValueError(f'unknown target {target}')
    return m.group(1) if m else ''


def matvar_pattern(slot):
    return rf'("name": "{re.escape(slot["material"])}",(?:(?!\n    \}}).)*?"{re.escape(slot["key"])}": ")([^"]*)(")'


def slot_is_bound_bucket(text):
    return 'Assets.Placeholder = {bucket = false}' in text


def table_block(text, table):
    m = re.search(rf'-- bind:begin {table}[^\n]*\n(.*?)[ \t]*-- bind:end {table}', text, re.S)
    if not m:
        raise ValueError(f'bind markers for {table} not found')
    return '\n' + m.group(1)


def write_slot(slot, text, digits):
    key = re.escape(slot['key'])
    target = slot['target']
    uri = f'rbxassetid://{digits}'
    if target in ('effect', 'sfx'):
        return rep_one(text, rf'(\n\s+{key} = \{{id = ")([^"]*)(")', uri, slot['name'])
    if target == 'weather':
        return rep_one(text, rf'(\n\s+{key}=\{{id=")([^"]*)(")', uri, slot['name'])
    if target == 'slot':
        new, count = re.subn(rf'(\n\s+{key} = ")[^"]*(",)', lambda m: m.group(1) + uri + m.group(2), text, count=1)
        if count != 1:
            raise ValueError(f'slot line not found for {slot["name"]}')
        return new
    if target == 'worldmesh':  # WorldGeneratedMeshes stores bare digits (no rbxassetid:// prefix)
        return rep_one(text, rf'(\n\s+{key} = \{{assetId = ")([^"]*)(")', digits, slot['name'])
    if target == 'cavebed':
        return rep_one(text, r'(Rules\.Bed = \{id = ")([^"]*)(")', uri, slot['name'])
    if target == 'hatchbucket':
        text = rep_one(text, r'(bucket = \{assetId = ")([^"]*)(")', digits, slot['name'])
        text = re.sub(r'(bucket = \{assetId = "[^"]*"[^\n]*?note = ")[^"]*(")',
                      lambda m: m.group(1) + 'paint bucket mesh (owner upload)' + m.group(2), text, count=1)
        return text.replace('Assets.Placeholder = {bucket = true}', 'Assets.Placeholder = {bucket = false}')
    if target == 'matvar':  # bare digits; the entry stays "bound": false until a Studio A/B passes
        new, count = re.subn(matvar_pattern(slot), lambda m: m.group(1) + digits + m.group(3), text, count=1, flags=re.S)
        if count != 1:
            raise ValueError(f'slot line not found for {slot["name"]}')
        return new
    if target == 'table':
        table = slot['table']
        pat = re.compile(rf'(-- bind:begin {table}[^\n]*\n)(.*?)([ \t]*)(-- bind:end {table})', re.S)
        m = pat.search(text)
        if not m:
            raise ValueError(f'bind markers for {table} not found')
        indent = m.group(3)
        lines = [l for l in m.group(2).split('\n') if l.strip()]
        lines = [l for l in lines if not re.match(rf'\s*{key} = ', l)]
        lines.append(f'{indent}{slot["key"]} = "{uri}",')
        lines.sort(key=lambda l: l.strip())
        return text[:m.start(2)] + '\n'.join(lines) + '\n' + text[m.start(3):]
    raise ValueError(f'unknown target {target}')


def bind(pairs, slots):
    errors, plan = [], {}
    for name, raw in pairs:
        if name not in slots:
            errors.append(f'unknown name {name!r} (run --list; refusing to guess)')
            continue
        try:
            plan[name] = parse_id(raw)
        except ValueError as e:
            errors.append(f'{name}: {e}')
    if errors:
        raise ValueError('\n'.join(errors))
    texts = {}
    for name, digits in plan.items():
        slot = slots[name]
        path = ROOT / slot['file']
        if path not in texts:
            texts[path] = path.read_text(encoding='utf-8')
        texts[path] = write_slot(slot, texts[path], digits)
    return plan, texts


REG = ROOT / 'docs/77-asset-registry.md'
REG_HEAD = ['Name', 'Type', 'Repo file', 'Roblox asset ID', 'Used by', 'Status']


def bd_ids():
    """slot name -> BD id(s), read from the docs/120 rows whose 'Bind in' cell names the slot's file:group."""
    out = {}
    slots = load_slots()
    bd_col = None
    for line in (ROOT / 'docs/120-pending-owner-uploads-checklist.md').read_text(encoding='utf-8').split('\n'):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if cells[0] in ('Asset', 'Sound'):
            bd_col = cells.index('BD') if 'BD' in cells else None
            continue
        if bd_col is None or len(cells) <= bd_col:
            continue
        for f, g in re.findall(r'`([^`]+):([^`:]+)`', cells[-1]):
            for s in slots.values():
                if s['file'] == f and (s['group'] == g or s['key'] == g or s.get('table') == g):
                    out.setdefault(s['name'], cells[bd_col])
    return out


def registry_rows(plan, slots, today):
    bds = bd_ids()
    rows = []
    for name, digits in plan.items():
        s = slots[name]
        rows.append([name, f'{s["kind"]}, owner upload', '-', digits, f'{s["file"]}:{s["group"]} ({bds.get(name, "BD-?")})',
                     f'uploaded {today}, source owner upload, bound (Studio check pending)'])
    return rows


def update_registry(rows):
    """Upsert rows into the first table of docs/77. Returns (new_text, None), or (None, reason) if the format is unknown."""
    raw = REG.read_text(encoding='utf-8')
    eol = '\r\n' if '\r\n' in raw else '\n'
    lines = raw.replace('\r\n', '\n').split('\n')
    head = next((i for i, l in enumerate(lines) if l.startswith('| Name |')), None)
    if head is None or [c.strip() for c in lines[head].strip().strip('|').split('|')] != REG_HEAD \
            or not re.fullmatch(r'\|(-+\|){6}', lines[head + 1].replace(' ', '')):
        return None, 'docs/77 table header is not the 6-column Name|Type|Repo file|Roblox asset ID|Used by|Status'
    end = head + 2
    while end < len(lines) and lines[end].startswith('|'):
        end += 1
    for r in rows:
        new = '| ' + ' | '.join(r) + ' |'
        idx = next((i for i in range(head + 2, end) if lines[i].split('|')[1].strip() == r[0]), None)
        if idx is None:
            lines.insert(end, new)
            end += 1
        else:
            lines[idx] = new
    return eol.join(lines), None


def list_slots(slots):
    bound = 0
    for name, slot in slots.items():
        text = (ROOT / slot['file']).read_text(encoding='utf-8')
        value = current_value(slot, text)
        bound += bool(value)
        print(f'{"BOUND  " if value else "pending"} {name:32s} {slot["kind"]:6s} {slot["file"]}:{slot["group"]}')
    print(f'{bound}/{len(slots)} bound')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input', nargs='?', help="file of name=id lines or JSON, or '-' for stdin")
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--batch', metavar='MAP.json', help='uploader output {"http://localhost:PORT/<file>": "rbxassetid://N"}')
    ap.add_argument('--manifest', metavar='manifest.json', help='manifest written by tools/upload_batch.py (needed with --batch)')
    args = ap.parse_args(argv)
    slots = load_slots()
    if args.list:
        list_slots(slots)
        return 0
    if args.batch:
        if not args.manifest or args.input:
            ap.error('--batch needs --manifest and no positional input')
    elif not args.input:
        ap.error('give an input file (or - for stdin), --batch MAP.json --manifest M.json, or --list')
    try:
        if args.batch:
            upload_map = json.loads(Path(args.batch).read_text(encoding='utf-8'))
            if not isinstance(upload_map, dict):
                raise ValueError('--batch JSON must be an object of url: rbxassetid')
            pairs = batch_pairs(upload_map, json.loads(Path(args.manifest).read_text(encoding='utf-8')))
        else:
            raw = sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8')
            pairs = parse_input(raw)
        plan, texts = bind(pairs, slots)
    except ValueError as e:
        print('REFUSED, nothing written:\n' + str(e), file=sys.stderr)
        return 1
    for name, digits in plan.items():
        print(f'{name} -> rbxassetid://{digits}  ({slots[name]["file"]}:{slots[name]["group"]})')
    if args.dry_run:
        for path, text in texts.items():
            diff = changed_lines(path.read_text(encoding='utf-8'), text)
            print(f'{path.relative_to(ROOT).as_posix()}: {len(diff)} line(s) would change')
            for old, new in diff:
                if old:
                    print(f'  - {old}')
                print(f'  + {new}')
        print('dry run: nothing written')
        return 0
    for path, text in texts.items():
        path.write_text(text, encoding='utf-8', newline='')
    rows = registry_rows(plan, slots, datetime.date.today().isoformat())
    reg, why = update_registry(rows)
    if reg is None:
        print(f'docs/77 NOT written ({why}). Add these lines by hand:')
        for r in rows:
            print('| ' + ' | '.join(r) + ' |')
    else:
        REG.write_text(reg, encoding='utf-8', newline='')
        print(f'docs/77 updated ({len(rows)} line(s)).')
    print(f'{len(plan)} id(s) written. Now: run python tools/verify_asset_slots.py, then the matching verifier and a Studio check.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
