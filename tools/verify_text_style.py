"""BD-390 readable text style: offline Luau tests for Shared/TextStyle plus a source scan.

The scan fails on a text construct that draws a visible black-ish outline around a DARK or low-contrast fill (owner playtest 2026-10-16:
black-only outlines were barely readable). It reads every `.luau` under src/, finds statements that set TextStrokeTransparency (< 1) or a
TextStrokeColor3, resolves the TextColor3 set in the same statement or within two lines, and requires contrast(fill, stroke) >= 4.5.
Unknown fills (variables) are not judged. Usage: python tools/verify_text_style.py --runner luau.exe [--no-mutants]

BD-1119 / BD-1117 (docs/202 R2 and R4) added the SIZE floors of the one outlined text style (Shared/TextStyle: title 22 px, card 16 px, note 14 px) and the window chrome
(PhoneScale / ModalCompact: a window title of at least 22 px on screen, a red square X of at least 48 px inside the header). On top of the colour checks above this verifier
  1. runs the pure TextStyle floor tests,
  2. runs tools/text_floor_smoke.luau: the REAL ModalCompact, PhoneScale, ShopScreens (all pages) and EggsScreen in the geometry mock of tools/menu_layout_smoke.luau at the
     11 window sizes of the small-window check, with mouse and touch: title >= 22 px, X >= 48 px square inside the header and clear of the title, every card text >= 16 px on a
     desktop window (a small, phone-sized window keeps the docs/72 floor of 14 px until the Studio re-check), notes (TextKind "note") >= 14 px,
  3. reads tools/text_style_allow.json (every exception has a reason; a stale entry fails; the count of small literal label sizes can only go down),
  4. puts each old defect back (mutants) and requires the checks to fail.
NOT Studio evidence: the mock has no font, so it proves the size asked for, not how the text draws.
"""
from pathlib import Path
import argparse, json, re, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parent.parent
NAMES = {  # UITheme.Colors (and the WHITE / BLACK aliases the client files use)
    'text': (255, 255, 255), 'accent': (93, 237, 31), 'gold': (255, 210, 43), 'blue': (46, 206, 255), 'purple': (194, 86, 255),
    'red': (247, 57, 48), 'panel': (42, 40, 53), 'card': (61, 58, 73), 'outline': (13, 15, 20), 'WHITE': (255, 255, 255),
}
DEFAULT_STROKE = (0, 0, 0)  # TextStrokeColor3 defaults to black


def lum(rgb):
    def ch(v):
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def color_of(expr):
    e = expr.strip()
    m = re.fullmatch(r'Color3\.fromRGB\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', e)
    if m:
        return tuple(int(x) for x in m.groups())
    if re.fullmatch(r'Color3\.new\(\s*1\s*,\s*1\s*,\s*1\s*\)', e):
        return (255, 255, 255)
    if re.fullmatch(r'Color3\.new\(\s*0\s*,\s*0\s*,\s*0\s*\)', e):
        return (0, 0, 0)
    m = re.fullmatch(r'(?:[A-Za-z_]*\.)?(?:Colors\.)?([A-Za-z]+)', e)
    if m and m.group(1) in NAMES:
        return NAMES[m.group(1)]
    return None


def split_top(text):
    parts, depth, cur = [], 0, ''
    for ch in text:
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


def assignments(line):
    """Yield (property, rhs expression) for plain and tuple assignments on one line (first top-level single '=')."""
    code = line.split('--')[0]
    depth, pos = 0, -1
    for i, ch in enumerate(code):
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == '=' and depth == 0:
            prev, nxt = code[i - 1] if i else '', code[i + 1] if i + 1 < len(code) else ''
            if prev not in '=<>~!' and nxt != '=':
                pos = i
                break
    if pos < 0:
        return
    lhs, rhs = split_top(code[:pos]), split_top(code[pos + 1:])
    if len(lhs) != len(rhs) and len(rhs) != 1:
        return
    for i, name in enumerate(lhs):
        name = name.strip().split()[-1] if name.strip() else ''
        if name:
            yield name.split('.')[-1], (rhs[i] if len(rhs) == len(lhs) else rhs[0])


def scan(files):
    bad = []
    for path in files:
        lines = path.read_text(encoding='utf-8').splitlines()
        for i, line in enumerate(lines):
            props = dict(assignments(line))
            if 'TextStrokeTransparency' not in props and 'TextStrokeColor3' not in props:
                continue
            visible = True
            if 'TextStrokeTransparency' in props:
                t = re.match(r'\s*([0-9.]+)', props['TextStrokeTransparency'])
                visible = t is not None and float(t.group(1)) < 0.5
            if not visible:
                continue
            stroke = color_of(props['TextStrokeColor3']) if 'TextStrokeColor3' in props else DEFAULT_STROKE
            if stroke is None or lum(stroke) > 0.1:
                continue  # light or unknown stroke is another style: not judged here
            fill = None
            for j in range(max(0, i - 2), min(len(lines), i + 3)):
                d = dict(assignments(lines[j]))
                if 'TextColor3' in d:
                    fill = color_of(d['TextColor3'])
                    break
            if fill is not None and contrast(fill, stroke) < 4.5:
                bad.append(f'{path.relative_to(ROOT)}:{i + 1}: dark outline on low-contrast fill {fill} (contrast {contrast(fill, stroke):.1f}): use Theme.TextStyle.apply')
    return bad


BODY = r'''
local T = (function()
@SRC@
end)()
assert(T.contrast(T.Light, T.Dark) > 15, "white on the dark outline")
assert(math.abs(T.contrast({0,0,0},{255,255,255}) - 21) < 1e-6)
assert(T.thickness(14) == 2 and T.thickness(20) == 2 and T.thickness(28) == 3 and T.thickness(60) == 3 and T.thickness(0/0) == 2, "thickness scales 2..3")
for size = 1, 120 do local t = T.thickness(size) assert(t >= 2 and t <= 3) end
local function pair(rgb) return T.pair(rgb) end
-- white, accent green, gold, blue, red, purple keep their fill with a dark stroke at 4.5:1
for _, rgb in {{255,255,255},{93,237,31},{255,210,43},{46,206,255},{247,57,48},{194,86,255}} do
    local f, s = pair(rgb)
    assert(f[1] == rgb[1] and f[2] == rgb[2] and f[3] == rgb[3] and T.contrast(f, s) >= 4.5 and T.readable(f, s, 3), "keeps " .. table.concat(rgb, ","))
end
-- a dark or mid-dark fill is replaced by white (never dark-on-dark)
for _, rgb in {{0,0,0},{42,40,53},{70,40,28},{40,28,70},{61,58,73}} do
    local f, s = pair(rgb)
    assert(f[1] == 255 and T.contrast(f, s) >= 4.5, "white replaces " .. table.concat(rgb, ","))
end
assert(not T.readable({13,15,20}, {13,15,20}, 3) and not T.readable({255,255,255}, {13,15,20}, 1), "bad combinations rejected")
assert(not T.readable({70,40,28}, {13,15,20}, 3) and T.readable({13,15,20}, nil, nil), "dark text only without a stroke")
assert(T.readable({255,255,255}, nil, nil) == false, "white text with no stroke is not readable on a light panel")
print("TextStyle passed: contrast, thickness 2..3, fill/stroke pairs, rejects dark-on-dark")
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--no-mutants', action='store_true')
    args = ap.parse_args()
    src = (ROOT / 'src/shared/TextStyle.luau').read_text(encoding='utf-8').replace('--!strict', '')
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'text_style.luau'
        f.write_text(BODY.replace('@SRC@', src), encoding='utf-8')
        r = subprocess.run([args.runner, str(f)], capture_output=True, text=True)
        print(r.stdout, end='')
        print(r.stderr, end='')
        if r.returncode:
            raise SystemExit(r.returncode)
    theme = (ROOT / 'src/shared/UITheme.luau').read_text(encoding='utf-8')
    assert 'Theme.TextStyle = require(script.Parent.TextStyle)' in theme, 'UITheme must expose TextStyle'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert 'Theme.TextStyle.apply(popLabel,Color3.new(1,1,1))' in boot and 'Theme.TextStyle.outlined(t,"card")' in boot, 'pickup pop and label() use the shared style'
    bad = scan(sorted((ROOT / 'src').rglob('*.luau')))
    for b in bad:
        print('FAIL', b)
    if bad:
        raise SystemExit(f'{len(bad)} low-contrast outlined text construct(s)')
    print('Text style scan passed: no black outline on a dark or low-contrast fill')
    floors(args)


def floors(args):
    """BD-1119 / BD-1117: size floors (title 22, card 16, note 14), the window X, the allowlist, the mutants."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import text_style_floors as tf
    allow = tf.load_allow()
    # the source wiring the mock cannot see
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert 'Theme.TextStyle.outlined(heading,"title")' in boot, 'the window title must go through TextStyle.outlined(heading, "title")'
    modal = (ROOT / 'src/client/ModalCompact.luau').read_text(encoding='utf-8')
    assert 'PhoneScale.titleSize(' in modal and 'PhoneScale.closeSide(' in modal, 'ModalCompact sizes the title and the X with PhoneScale.titleSize / closeSide'
    ok, out = tf.pure_floor_tests(args.runner)
    print(out, end='')
    if not ok:
        raise SystemExit('TextStyle floor tests failed')
    problems = tf.check_small_literals(allow)
    for line in problems:
        print('FAIL', line)
    if problems:
        raise SystemExit('%d small-text allowance problem(s)' % len(problems))
    print('Small text allowance passed: %s' % ', '.join('%s %d' % (k, v['count']) for k, v in sorted(allow['small_literals'].items())))
    for price in (False, True):  # BD-1144: the second run draws the shop card with the price on the button
        ok, out = tf.run_smoke(args.runner, None, allow['entries'], price=price)
        tail = [l for l in out.splitlines() if l.startswith(('FAIL', 'ALLOWSTALE', 'Text floor'))]
        print('\n'.join(('[price on the button] ' if price else '') + l for l in tail[:40]))
        if not ok or any(l.startswith('ALLOWSTALE') for l in tail):
            print(out[-1500:])
            raise SystemExit('text-floor smoke failed (a stale allow entry also fails)')
    if args.no_mutants:
        return
    from concurrent.futures import ThreadPoolExecutor  # each mutant is its own luau process: run them side by side
    names = list(tf.MUTANTS)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda n: tf.run_smoke(args.runner, tf.MUTANTS[n], allow['entries']), names))
    for name, (passed, _out) in zip(names, results):
        assert not passed, 'MUTANT SURVIVED (the text-floor smoke did not notice): ' + name
        print('  mutant caught: ' + name)
    for name, replacements in tf.PURE_MUTANTS.items():
        passed, _out = tf.pure_floor_tests(args.runner, replacements)
        assert not passed, 'MUTANT SURVIVED (the TextStyle floor tests did not notice): ' + name
        print('  mutant caught: ' + name)
    # the allowance itself: a new small label, a stale entry, an entry without a reason and a stale mock entry all fail
    fake = {'small_literals': {'a.luau': {'count': 1, 'reason': 'x'}}}
    assert tf.check_small_literals(fake, {'a.luau': 2}) and tf.check_small_literals(fake, {'a.luau': 0}) and tf.check_small_literals(fake, {}) and tf.check_small_literals(fake, {'b.luau': 1}), 'allowance rules'
    assert not tf.check_small_literals(fake, {'a.luau': 1}), 'allowance rules (exact count passes)'
    sample = chr(10).join(['local a = label(card, "x", 1, 2, 3, 4, 14, C.text)', 'local b = label(card, "y", 1, 2, 3, 4, 14):SetAttribute("TextKind", "note")', 'local c = label(card, "z", 1, 2, 3, 4, 16)', 'local d = uiLabel(card, fmt("a,b", 1), 1, 2, 3, 4, 12)', 'label(card, "e", 1, 2, 3, 4, if compact then 14 else 15)', 'label(card, "f", 1, 2, 3, 4, if compact then 14 else 16)'])
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / 'src' / 'client').mkdir(parents=True)
        (Path(d) / 'src' / 'client' / 'S.luau').write_text(sample, encoding='utf-8')
        assert tf.small_literals(d) == {'src/client/S.luau': 3}, 'the scan counts a 14, a 12 and a desktop 15, not the note, the 16 and a compact-only 14'
    stale = tf.run_smoke(args.runner, None, [{'screen': 'Nowhere/', 'minPx': 10, 'reason': 'stale on purpose'}])
    assert 'ALLOWSTALE' in stale[1], 'a stale mock allow entry must be reported'
    print('  allowance rules caught: new small label, stale entry, wrong count; scan counts what it should; a stale mock entry is reported')
    print('Text floors passed: title 22 / X 48 / card 16 (14 on a small window) at 11 window sizes, %d mutants caught' % (len(tf.MUTANTS) + len(tf.PURE_MUTANTS)))


if __name__ == '__main__':
    main()
