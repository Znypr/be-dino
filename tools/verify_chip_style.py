#!/usr/bin/env python3
"""BD-1077 (docs/193 section 5): ONE tag style in the whole game. The owner said round pill-shaped tags exist nowhere else in the game's style;
the hatch screen got the chunky tag (src/shared/ChipStyle.luau: rounded rectangle, dark outline, flat palette fill, text 14 px or more). This check
keeps every other screen on it.

1. SCAN: every line in src/**/*.luau that makes a FULL-ROUND shape is found: a UICorner whose scale is 0.5 or more (UDim.new(.5, 0), UDim.new(1, 0)),
   a corner or Theme.decorate radius of 13 px or more (those turn a 26 px tag into a pill). Each one must be on the allowlist tools/targets/round_ok.json
   with a kind (button, bar, dot, circle, panel, art, effect, key) and a plain reason, so a NEW round tag cannot slip in; a TAG must use ChipStyle.
   An allowlist entry that matches no code any more is stale and fails too.
2. SOURCE: the converted tag builders still call ChipStyle (Chip.apply) and have no private corner.
3. PURE (needs --runner): the ChipStyle numbers, normal and small.
4. MUTANTS: each old defect put back must fail this check (a round pill in the Eggs screen, a new round tag, a removed allowlist line, a reason-less
   line, a stale line, a big-radius decorate, a ChipStyle that rounds fully).
Not Studio evidence: nothing here shows how a tag looks. Usage: python tools/verify_chip_style.py [--runner luau.exe]
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / 'tools' / 'targets' / 'round_ok.json'
KINDS = {'button', 'bar', 'dot', 'circle', 'panel', 'art', 'effect', 'key'}
BIG_OFFSET = 13  # px; a corner this big on a tag of 26 px high is a pill

# Files whose tag builders were converted (BD-1077) and what they must call.
CONVERTED = {
    'src/client/EggsScreen.luau': 'Chip.apply(frame, color, C.outline)',
    'src/client/DinoIndexPanels.luau': 'Chip.apply(p, color, nil, true)',
    'src/client/MutationBadge.luau': 'Chip.apply(chip, Look.color(look.badge)',
    'src/shared/ClassBadge.luau': 'Chip.apply(word, spec.color',
    'src/client/FusionMenu.luau': 'Chip.apply(badge, C.text, nil, true)',
    'src/client/ShopCards.luau': 'Chip.apply(c, color)',
    'src/client/ObjectivesPanel.luau': 'Chip.apply(chip, C.card)',
    'src/client/InspectView.luau': 'Chip.apply(hint,',
}


def strip_comment(line):
    """Drop a trailing -- comment (the string "--" does not occur in these sources before a comment)."""
    index = line.find('--')
    return line if index < 0 else line[:index]


def numbers(text):
    return [float(x) for x in re.findall(r'(?<![\w.])(\d*\.\d+|\d+)(?![\w])', text)]


def round_reason(line):
    """Why this line makes a full-round shape, or None."""
    code = strip_comment(line)
    deco = re.search(r'Theme\.decorate\(\s*[^,()]+,\s*(\d+)\s*\)', code)
    if deco and int(deco.group(1)) >= BIG_OFFSET:
        return 'decorate radius %s px' % deco.group(1)
    if 'CornerRadius' not in code:
        return None
    # a UDim.new( scale , offset ): look at the scale expression and at the offset
    for match in re.finditer(r'UDim\.new\(', code):
        depth, i, parts, current = 1, match.end(), [], ''
        while i < len(code) and depth:
            ch = code[i]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    break
            if ch == ',' and depth == 1:
                parts.append(current)
                current = ''
            else:
                current += ch
            i += 1
        parts.append(current)
        if len(parts) != 2:
            continue
        scale, offset = parts
        if any(n >= 0.5 for n in numbers(scale)):
            return 'scale radius'
        if any(n >= BIG_OFFSET for n in numbers(offset)):
            return 'radius %s px' % int(max(numbers(offset)))
    return None


def scan(files):
    """files: {relative path: text}. Returns [(path, line number, line text, reason)]."""
    found = []
    for path, text in sorted(files.items()):
        for number, line in enumerate(text.splitlines(), 1):
            why = round_reason(line)
            if why:
                found.append((path, number, line.strip(), why))
    return found


def load_files():
    return {p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8') for p in sorted((ROOT / 'src').rglob('*.luau'))}


def judge(files, allow):
    """Errors for a source set and an allowlist (a list of entries)."""
    errors = []
    for index, entry in enumerate(allow):
        if entry.get('kind') not in KINDS:
            errors.append('allowlist entry %d (%s): kind must be one of %s' % (index, entry.get('file'), sorted(KINDS)))
        if len(str(entry.get('why', '')).strip()) < 12:
            errors.append('allowlist entry %d (%s): it needs a plain reason (why this shape is round on purpose)' % (index, entry.get('file')))
        if not entry.get('file') or not entry.get('contains'):
            errors.append('allowlist entry %d: file and contains are required' % index)
    used = [0] * len(allow)
    for path, number, line, why in scan(files):
        hit = None
        for index, entry in enumerate(allow):
            if entry.get('file') == path and entry.get('contains') and entry['contains'] in line:
                hit = index
                break
        if hit is None:
            errors.append('%s:%d is a full-round shape (%s) that is not on the allowlist: %s\n    A TAG must use src/shared/ChipStyle.luau (Chip.apply / Chip.new); a button, bar, dot or effect '
                          'that must be round goes in tools/targets/round_ok.json with a kind and a reason.' % (path, number, why, line[:120]))
        else:
            used[hit] += 1
    for index, entry in enumerate(allow):
        if used[index] == 0:
            errors.append('allowlist entry %d (%s: %s) matches no code any more: remove it' % (index, entry.get('file'), str(entry.get('contains'))[:60]))
        elif 'count' in entry and used[index] != entry['count']:
            errors.append('allowlist entry %d (%s: %s) expects %d matching lines, found %d' % (index, entry.get('file'), str(entry.get('contains'))[:60], entry['count'], used[index]))
    return errors


def check_source(files):
    errors = []
    for path, needle in CONVERTED.items():
        text = files.get(path, '')
        if needle not in text:
            errors.append('%s: the tag builder no longer calls ChipStyle (%s)' % (path, needle))
        if 'require(Shared.ChipStyle)' not in text and 'require(Shared:WaitForChild("ChipStyle"))' not in text and 'require(script.Parent.ChipStyle)' not in text:
            errors.append('%s: ChipStyle is not required' % path)
    style = files.get('src/shared/ChipStyle.luau', '')
    if 'UDim.new(1' in style or 'UDim.new(.5' in style or 'UDim.new(0.5' in style:
        errors.append('ChipStyle makes a full-round corner')
    if 'Chip.Small = {radius = 6, outline = 2, minHeight = 17}' not in style:
        errors.append('ChipStyle.Small numbers changed (rounded 6 px corner, 2 px outline, 17 px high)')
    boot = files.get('src/client/Bootstrap.client.luau', '')
    if 'ChipStyle' in boot:
        errors.append('Bootstrap is at its byte ratchet: tags built there are reported as a follow-up, not changed here')
    return errors


PURE = r'''
local UDim = {new = function(scale, offset) return {Scale = scale, Offset = offset} end}
local Theme = {Colors = {}}
local script = {Parent = {UITheme = Theme}}
local function require(x) return x end
local Chip = (function()
@@CHIP@@
end)()
local S, M = Chip.Spec, Chip.Small
assert(S.outline == 3 and S.minText >= 14 and S.minHeight >= 28 and S.tapHeight >= 44, "normal chip numbers")
assert(M.radius > 0 and M.radius <= 8 and M.radius < S.radius, "small chip corner: a rounded rectangle, smaller than the normal one")
assert(M.outline >= 2 and M.outline <= S.outline, "small chip outline is 2 px or more")
assert(M.minHeight >= 17 and M.minHeight < S.minHeight, "small chip is high enough for 14 px text")
assert(Chip.radius().Offset == S.radius and Chip.radius().Scale == 0, "normal radius is an offset, never a scale")
assert(Chip.radius(true).Offset == M.radius and Chip.radius(true).Scale == 0, "small radius is an offset, never a scale")
assert(Chip.radius(false).Offset == S.radius, "small = false is the normal chip")
print("Chip style pure checks passed")
'''


def pure(runner, chip_source):
    source = PURE.replace('@@CHIP@@', chip_source.replace('Enum.Font.FredokaOne', '"FredokaOne"'))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'chip_style.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


def mutants(files, allow, runner):
    """Each old defect put back must produce errors."""
    def with_change(path, old, new, count=1):
        assert old in files[path], 'mutant target missing in %s: %s' % (path, old)
        copy = dict(files)
        copy[path] = files[path].replace(old, new, count)
        return copy

    cases = {
        'the Eggs screen tag is a round pill again': lambda: (judge(with_change('src/client/EggsScreen.luau', 'Chip.apply(frame, color, C.outline)',
                                                                              'Instance.new("UICorner").CornerRadius = UDim.new(.5, 0)'), allow)
                                                               + check_source(with_change('src/client/EggsScreen.luau', 'Chip.apply(frame, color, C.outline)', 'local x = 1'))),
        'a new round tag with a full-scale corner': lambda: judge({**files, 'src/client/NewTag.luau': 'local c = Instance.new("UICorner") c.CornerRadius = UDim.new(1, 0) c.Parent = tag\n'}, allow),
        'a new round tag with a half-scale corner in an old file': lambda: judge(with_change('src/client/ShopCards.luau', 'Chip.apply(c, color)',
                                                                                         'local k = Instance.new("UICorner") k.CornerRadius = UDim.new(0.5, 0) k.Parent = c'), allow),
        'a fusion tag with a big decorate radius': lambda: judge(with_change('src/client/FusionMenu.luau', 'Chip.apply(c, color)', 'Theme.decorate(c, 18)'), allow),
        'a tag with a big pixel corner': lambda: judge({**files, 'src/client/NewTag.luau': 'corner.CornerRadius = UDim.new(0, 20)\n'}, allow),
        'an allowlist line is removed': lambda: judge(files, allow[1:]),
        'an allowlist line has no reason': lambda: judge(files, [dict(allow[0], why='')] + allow[1:]),
        'an allowlist line has a wrong kind': lambda: judge(files, [dict(allow[0], kind='pill')] + allow[1:]),
        'an allowlist line is stale': lambda: judge(files, allow + [{'file': 'src/client/EggsScreen.luau', 'contains': 'UDim.new(.5, 0)', 'kind': 'dot', 'why': 'a stale line that matches nothing'}]),
        'ChipStyle rounds fully': lambda: check_source(with_change('src/shared/ChipStyle.luau', 'corner.CornerRadius = Chip.radius(small)', 'corner.CornerRadius = UDim.new(1, 0)')),
        'a converted builder drops ChipStyle': lambda: check_source(with_change('src/client/MutationBadge.luau', 'Chip.apply(chip, Look.color(look.badge)', 'local gone = (look.badge')),
    }
    if runner:
        cases['the small chip becomes huge'] = lambda: (['ran'] if pure(runner, files['src/shared/ChipStyle.luau'].replace('Chip.Small = {radius = 6,', 'Chip.Small = {radius = 40,')).returncode else [])
    for name, make in cases.items():
        assert make(), 'MUTANT SURVIVED (the check did not notice): ' + name
        print('  mutant caught: ' + name)
    return len(cases)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner')
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    files = load_files()
    allow = json.loads(ALLOW.read_text(encoding='utf-8'))['allow']
    errors = judge(files, allow) + check_source(files)
    if errors:
        print('Chip style check FAILED:')
        for error in errors:
            print(' - ' + error)
        sys.exit(1)
    if args.runner:
        result = pure(args.runner, files['src/shared/ChipStyle.luau'])
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            sys.exit(1)
    count = 0 if args.no_mutants else mutants(files, allow, args.runner)
    print('Chip style passed: %d round shapes, all on the allowlist with a reason; %d tag builders use ChipStyle; %d mutants caught'
          % (len(scan(files)), len(CONVERTED), count))


if __name__ == '__main__':
    main()
