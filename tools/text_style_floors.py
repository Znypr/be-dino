"""BD-1119 / BD-1117: the size-floor half of tools/verify_text_style.py (docs/202 R2 and R4).

Kept in its own file so verify_text_style.py stays short. Functions:
  build(replacements, allow)      the Luau source of tools/text_floor_smoke.luau behind the head of tools/menu_layout_smoke.luau, real modules inside
  run_smoke(runner, ...)          run it; returns (ok, output)
  pure_floor_tests(runner, text)  the pure TextStyle floor tests (no geometry)
  small_literals(root)            the count of label(...) calls with a literal text size under 16 that are not marked as notes, per file
  load_allow()                    tools/text_style_allow.json, checked: every exception has a reason
MUTANTS / PURE_MUTANTS put each old defect back; the checks must fail.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_menu_layout as ml  # noqa: E402
import verify_small_window as sw  # noqa: E402

ALLOW_PATH = ROOT / 'tools' / 'text_style_allow.json'
HEAD_END = '-- ===== 1. BD-1101'
PREFIX_NOTE = '-- @@PREFIX@@ is already replaced by the head of menu_layout_smoke.'
MODULES = dict(ml.MODULES)
MODULES['TextStyle'] = 'src/shared/TextStyle.luau'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def load_allow():
    data = json.loads(ALLOW_PATH.read_text(encoding='utf-8'))
    for key in ('compact', 'entries', 'small_literals'):
        assert key in data, 'text_style_allow.json lost its "%s" section' % key
    assert data['compact'].get('reason'), 'the compact-window tier needs a reason'
    for i, entry in enumerate(data['entries']):
        assert entry.get('reason'), 'allow entry %d has no reason' % i
        assert entry.get('screen') and isinstance(entry.get('minPx'), (int, float)), 'allow entry %d needs "screen" and "minPx"' % i
    for path, item in data['small_literals'].items():
        assert item.get('reason') and isinstance(item.get('count'), int), 'small_literals entry %s needs "count" and a reason' % path
    return data


def lua_string(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def allow_literal(entries):
    rows = []
    for entry in entries:
        fields = ['screen = ' + lua_string(entry['screen']), 'minPx = %s' % entry['minPx']]
        if entry.get('name'):
            fields.append('name = ' + lua_string(entry['name']))
        if entry.get('text'):
            fields.append('text = ' + lua_string(entry['text']))
        rows.append('{' + ', '.join(fields) + '}')
    return '{' + ', '.join(rows) + '}'


def build(replacements=None, allow=None, body_path='tools/text_floor_smoke.luau', extra_modules=None):
    menu = read('tools/menu_layout_smoke.luau')
    assert HEAD_END in menu, 'menu_layout_smoke.luau lost the marker the text-floor smoke is spliced behind'
    head = menu[:menu.index(HEAD_END)]
    body = read(body_path)
    assert PREFIX_NOTE in body
    body = body.replace(PREFIX_NOTE, '').replace('@@ALLOW@@', allow_literal(allow or []))
    parts = []
    modules = dict(MODULES)
    modules.update(extra_modules or {})
    for name, path in modules.items():
        source = read(path)
        for old, new in (replacements or {}).get(name, []):
            assert old in source, 'mutant target missing in %s: %s' % (name, old)
            source = source.replace(old, new)
        parts.append(name + '=function(script, require)\n' + source + '\nend,\n')
    smoke = read('tools/close_paths_smoke.luau')
    marker = '-- ===== modules: REAL pure ones'
    prefix = smoke[:smoke.index(marker)]
    combined = (head + body).replace('-- @@PREFIX@@', prefix)
    assert 'local sources = MODULE_SOURCES' in combined
    return combined.replace('local sources = MODULE_SOURCES', 'local sources = {\n' + ''.join(parts) + '}')


def run_smoke(runner, replacements=None, allow=None, body_path='tools/text_floor_smoke.luau', extra_modules=None):
    result = sw.run(runner, build(replacements, allow, body_path, extra_modules))
    return result.returncode == 0 and 'passed' in result.stdout, result.stdout + result.stderr


PURE = r'''
local T = (function()
@SRC@
end)()
assert(T.Floors.title == 22 and T.Floors.card == 16 and T.Floors.note == 14, "the three floors")
assert(T.floorOf("title") == 22 and T.floorOf("card") == 16 and T.floorOf("note") == 14 and T.floorOf("nonsense") == 14, "floorOf")
assert(T.fit("title", 18) == 22 and T.fit("title", 40) == 40 and T.fit("card", 15) == 16 and T.fit("card", 19) == 19 and T.fit("note", 10) == 14, "fit raises, never lowers")
assert(T.thicknessFor("title", 22) == 3 and T.thicknessFor("title", 40) == 3 and T.thicknessFor("card", 14) == 2 and T.thicknessFor("card", 30) == 3, "outline thickness")
-- a title needs 22 px on every window, a card 16 px on a desktop window and 14 px on a small one, a note 14 px
assert(T.onScreenOk("title", 22, false) and T.onScreenOk("title", 22, true) and not T.onScreenOk("title", 21.9, false) and not T.onScreenOk("title", 21.9, true), "title 22 everywhere")
assert(T.onScreenOk("card", 16, false) and not T.onScreenOk("card", 15, false) and not T.onScreenOk("card", 15.9, false), "card 16 on a desktop window")
assert(T.onScreenOk("card", 14, true) and not T.onScreenOk("card", 13.9, true), "card 14 on a small window")
assert(T.onScreenOk("note", 14, false) and T.onScreenOk("note", 14, true) and not T.onScreenOk("note", 13, false), "note 14")
assert(T.Floors.title > T.Floors.card and T.Floors.card > T.Floors.note, "titles are bigger than cards, cards bigger than notes")
print("TextStyle floors passed: title 22, card 16 (14 on a small window), note 14, outline 3 for titles")
'''


def pure_floor_tests(runner, replacements=None):
    source = read('src/shared/TextStyle.luau').replace('--!strict', '')
    for old, new in (replacements or []):
        assert old in source, 'mutant target missing in TextStyle: ' + old
        source = source.replace(old, new)
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'text_floors.luau'
        f.write_text(PURE.replace('@SRC@', source), encoding='utf-8')
        r = subprocess.run([runner, str(f)], capture_output=True, text=True, encoding='utf-8')
        return r.returncode == 0 and 'passed' in r.stdout, r.stdout + r.stderr


# --- the count of small literal label sizes -------------------------------------------------------------------------------
def split_top(text):
    parts, depth, cur, quote = [], 0, '', None
    for ch in text:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in '"\'':
            quote = ch
            cur += ch
            continue
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    return parts


def label_calls(text):
    """Yield (line number, argument list, the source line and the next two) of every label( / uiLabel( call."""
    lines = text.splitlines()
    for m in re.finditer(r'(?<![\w.:])(?:label|uiLabel)\(', text):
        i = m.end()
        depth, j, quote = 1, i, None
        while j < len(text) and depth:
            c = text[j]
            if quote:
                if c == quote:
                    quote = None
            elif c in '"\'':
                quote = c
            elif c in '([{':
                depth += 1
            elif c in ')]}':
                depth -= 1
            j += 1
        line = text.count('\n', 0, m.start()) + 1
        context = [lines[line - 1]]
        for extra in lines[line:line + 2]:  # the note mark may sit on the next two lines, never past the next label
            if re.search(r'(?<![\w.:])(?:label|uiLabel)\(', extra):
                break
            context.append(extra)
        yield line, split_top(text[i:j - 1]), ' '.join(context)


def small_literals(root=None, floor=16):
    """{relative path: count} of label( calls whose literal size (7th argument) is under `floor` and that carry no TextKind note mark."""
    base = Path(root or ROOT)
    found = {}
    for path in sorted((base / 'src' / 'client').glob('*.luau')):
        count = 0
        for _line, args, context in label_calls(path.read_text(encoding='utf-8')):
            if len(args) < 7:
                continue
            expr = args[6]
            m = re.fullmatch(r'\s*(\d+)\s*', expr) or re.fullmatch(r'\s*if\s+.+?\s+then\s+\d+\s+else\s+(\d+)\s*', expr)  # "if compact then 14 else 16": the desktop value counts
            if m and int(m.group(1)) < floor and '"TextKind"' not in context:
                count += 1
        if count:
            found[path.relative_to(base).as_posix()] = count
    return found


def check_small_literals(allow, found=None):
    found = small_literals() if found is None else found
    problems = []
    declared = allow['small_literals']
    for path, count in sorted(found.items()):
        if path not in declared:
            problems.append('%s has %d label(s) with a text size under 16 and no entry in tools/text_style_allow.json (raise them to 16, mark fine print with TextKind "note", or add an entry with a reason)' % (path, count))
        elif declared[path]['count'] < count:
            problems.append('%s has %d small label(s), the allowance says %d: do not add new small card text' % (path, count, declared[path]['count']))
        elif declared[path]['count'] > count:
            problems.append('%s has only %d small label(s), the allowance still says %d: lower it in tools/text_style_allow.json (the number only goes down)' % (path, count, declared[path]['count']))
    for path in declared:
        if path not in found:
            problems.append('tools/text_style_allow.json lists %s but it has no small label any more: remove the entry' % path)
    return problems


MUTANTS = {
    # BD-1119: the window title
    'the compact window title is 14 px': {
        'ModalCompact': [('PhoneScale.titleSize(32, m.scale, m.headerH - 8)', '14')],
    },
    'the desktop window title is 18 px': {
        'ModalCompact': [('PhoneScale.titleSize(40, m.scale, 68)', '18')],
    },
    'the window title is not marked as a title': {
        'ModalCompact': [('c.heading:SetAttribute("TextKind", "title")\n', '')],
    },
    # BD-1117: the red X
    'the X is only asked for 44 px': {
        'PhoneScale': [('PhoneScale.MinClose = 48', 'PhoneScale.MinClose = 44')],
    },
    'the X is not raised to 48 px on a scaled-down window': {
        'PhoneScale': [('math.max(base, math.ceil(PhoneScale.MinClose / math.max(scale, 0.05)))', 'base')],
    },
    'the compact header keeps its old height (the 48 px X hangs out of it)': {
        'PhoneScale': [('return math.max(PhoneScale.HeaderH, math.ceil(PhoneScale.MinClose / math.max(scale, 0.05)) + 2)', 'return PhoneScale.HeaderH')],
    },
    'the title box runs under the X': {
        'ModalCompact': [('UDim2.fromOffset(m.panelW - side - 38, m.headerH - 8)', 'UDim2.fromOffset(m.panelW - 20, m.headerH - 8)')],
    },
    'the X is a wide bar again (80 px wide)': {
        'ModalCompact': [('c.closeButton.Size, c.closeButton.TextSize = UDim2.fromOffset(side, side), math.max(28, math.floor(side * 0.55))\n    c.heading:SetAttribute', 'c.closeButton.Size, c.closeButton.TextSize = UDim2.fromOffset(side + 40, side), math.max(28, math.floor(side * 0.55))\n    c.heading:SetAttribute')],
    },
    # BD-1153 (docs/217): a hatch tag pops in from UIScale 0
    'every UIScale is multiplied into the floor, a pop-in from 0 included (TextSize 100)': {
        'ModalCompact': [('if u.Scale >= 0.999 then total *= u.Scale end', 'total *= u.Scale')],
    },
    'only a pop-in under half is ignored (a card at 0.6 still grows its words)': {
        'ModalCompact': [('if u.Scale >= 0.999 then total *= u.Scale end', 'if u.Scale >= 0.5 then total *= u.Scale end')],
    },
    'the floor has no cap': {
        'ModalCompact': [('    return math.max(base, math.min(want, math.max(limit, 2 * base)))', '    return want')],
    },
    'the raised size is stored as the design size': {
        'ModalCompact': [('d:SetAttribute("CmBaseText", base) -- the size the screen asked for: never the engine\'s clamped answer', 'd:SetAttribute("CmBaseText", object.TextSize)')],
    },
    # BD-1119: card text
    'potion card text is 15 px again': {
        'ShopScreens': [('label(card,UIFormat.potion(item.kind,item.multiplier,item.duration),74,2+nameH,186,descH,16)', 'label(card,UIFormat.potion(item.kind,item.multiplier,item.duration),74,2+nameH,186,descH,15)')],
    },
    'the "left" line of a potion card is 15 px again': {
        'ShopScreens': [('74,2+nameH+descH,186,leftH,16,ShopCard.captionColor(look))', '74,2+nameH+descH,186,leftH,15,ShopCard.captionColor(look))')],
    },
    'the Eggs captions are 14 px without being marked as notes': {
        'EggsScreen': [('        typeCaption:SetAttribute("TextKind", "note")', '        typeCaption:SetAttribute("TextKind", "card")')],
    },
}

PURE_MUTANTS = {
    'the card floor is 14': [('TextStyle.Floors = {title = 22, card = 16, note = 14}', 'TextStyle.Floors = {title = 22, card = 14, note = 14}')],
    'the title floor is 18': [('TextStyle.Floors = {title = 22, card = 16, note = 14}', 'TextStyle.Floors = {title = 18, card = 16, note = 14}')],
    'a card passes at 15 px on a desktop window': [('if kind == "card" and not compact then return px >= TextStyle.Floors.card - 0.01 end', 'if kind == "card" and not compact then return px >= 15 end')],
    'a title on a small window only needs the card floor': [('if kind == "title" then return px >= TextStyle.Floors.title - 0.01 end', 'if kind == "title" and not compact then return px >= TextStyle.Floors.title - 0.01 end')],
    'fit can make text smaller': [('return math.max(size, TextStyle.floorOf(kind))', 'return TextStyle.floorOf(kind)')],
    'a title outline is not thick': [('if kind == "title" then return TextStyle.MaxThickness end', 'if kind == "title" then return TextStyle.MinThickness end')],
}
